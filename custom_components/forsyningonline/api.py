"""API client for ForsyningOnline."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

API_BASE = "https://api-forsyningonline.azurewebsites.net/api"
WATER_CONSUMPTION_PAGE_ID = "1F8F82F6-3352-454E-A25C-17E94051681A"

_LOGGER = logging.getLogger(__name__)


class ForsyningOnlineApiError(Exception):
    """Exception raised for API errors."""


class ForsyningOnlineAuthError(ForsyningOnlineApiError):
    """Exception raised for authentication errors."""


class ForsyningOnlineClient:
    """Client for ForsyningOnline API."""

    def __init__(
        self,
        username: str,
        password: str,
        session: Optional[requests.Session] = None,
    ):
        """Initialize the API client.

        Args:
            username: ForsyningOnline username
            password: ForsyningOnline password
            session: Optional requests.Session to use
        """
        self.username = username
        self.password = password
        self.session = session or requests.Session()
        self._auth_data: Optional[Dict[str, Any]] = None
        self._current_location: Optional[Dict[str, str]] = None
        self._locations: List[Dict[str, Any]] = []

        # Set default headers
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://forsyningonline.dk",
                "Referer": "https://forsyningonline.dk/",
            }
        )

    def login(self) -> bool:
        """Login to ForsyningOnline.

        Returns:
            True if login successful

        Raises:
            ForsyningOnlineAuthError: If login fails
        """
        try:
            response = self.session.post(
                f"{API_BASE}/auth/token",
                json={"username": self.username, "password": self.password},
                timeout=10,
            )
        except requests.RequestException as err:
            raise ForsyningOnlineAuthError(f"Connection error: {err}") from err

        if response.status_code != 200:
            raise ForsyningOnlineAuthError(
                f"Login failed: {response.status_code} - {response.text}"
            )

        self._auth_data = response.json()
        token = self._auth_data.get("token")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

        _LOGGER.info("Logged in as: %s", self._auth_data.get("urlRoute", "unknown"))
        return True

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an API request with automatic 401 retry.

        Args:
            method: HTTP method ("get" or "post")
            url: Full URL to request
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            ForsyningOnlineApiError: If request fails after retry
        """
        kwargs.setdefault("timeout", 10)
        response = self.session.request(method, url, **kwargs)

        if response.status_code == 401:
            _LOGGER.warning("Got 401, trying to re-login")
            self.login()
            response = self.session.request(method, url, **kwargs)

        if response.status_code != 200:
            raise ForsyningOnlineApiError(
                f"Request failed: {method.upper()} {url} - {response.status_code}"
            )

        return response

    def get_locations(self) -> List[Dict[str, Any]]:
        """Get all locations for the user.

        Returns:
            List of locations with utilityName, description, locationGuid, relationId

        Raises:
            ForsyningOnlineApiError: If request fails
        """
        response = self._request_with_retry("get", f"{API_BASE}/Location/all")
        self._locations = response.json()
        return self._locations

    def set_location(self, location_guid: str, relation_id: str) -> bool:
        """Set the active location.

        Args:
            location_guid: Location GUID
            relation_id: Relation ID

        Returns:
            True if successful

        Raises:
            ForsyningOnlineApiError: If request fails
        """
        self._request_with_retry(
            "post",
            f"{API_BASE}/relay/Location/set",
            json={"locationGuid": location_guid, "relationId": relation_id},
        )

        self._current_location = {
            "locationGuid": location_guid,
            "relationId": relation_id,
        }
        return True

    def get_consumption(
        self,
        date: Optional[str] = None,
        view_scope: str = "day",
        meter: str = "total",
    ) -> Dict[str, Any]:
        """Get consumption data.

        Args:
            date: Date in "DD-MM-YYYY" format, defaults to today
            view_scope: One of "year", "month", "day", "hour"
            meter: "total" or specific meter ID

        Returns:
            Dict with consumption data including period, unit, and values

        Raises:
            ForsyningOnlineApiError: If request fails
        """
        if date is None:
            date = datetime.now().strftime("%d-%m-%Y")

        payload = {
            "pageId": WATER_CONSUMPTION_PAGE_ID,
            "option": {
                "getAnswer": "YES",
                "form": {
                    "selectedMeter": meter,
                    "selectedDate": date,
                    "selectedViewscope": view_scope,
                },
            },
        }

        response = self._request_with_retry(
            "post", f"{API_BASE}/relay/page", json=payload
        )

        return self._parse_consumption_data(response.json(), view_scope)

    def _parse_consumption_data(
        self, data: Dict[str, Any], view_scope: str
    ) -> Dict[str, Any]:
        """Parse consumption data from API response.

        Args:
            data: Raw API response
            view_scope: The view scope used for the request

        Returns:
            Parsed consumption data
        """
        result = {
            "title": data.get("title", "Vandforbrug"),
            "period": "",
            "unit": "m³",
            "values": [],
            "view_scope": view_scope,
        }

        for section in data.get("sections", []):
            # Find period header
            if "header" in section and "Forbrug for perioden:" in section["header"]:
                result["period"] = section["header"]

            # Find chart data
            for content in section.get("content", []):
                if content.get("elementType") == 6:  # Chart element
                    chart_data = content.get("data", [])
                    result["values"] = [
                        {"label": item.get("name", ""), "value": item.get("value", 0)}
                        for item in chart_data
                    ]

        return result

    def get_daily_consumption(self, date: Optional[str] = None) -> float:
        """Get total consumption for a day.

        Args:
            date: Date in "DD-MM-YYYY" format, defaults to today

        Returns:
            Total consumption in m³
        """
        data = self.get_consumption(date, view_scope="day")
        return sum(v["value"] for v in data.get("values", []))

    def get_hourly_consumption(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get hourly consumption for a day.

        Args:
            date: Date in "DD-MM-YYYY" format, defaults to today

        Returns:
            List of dicts with 'hour' and 'value' keys
        """
        data = self.get_consumption(date, view_scope="hour")
        hourly_data: List[Dict[str, Any]] = []

        for entry in data.get("values", []):
            hour = self._parse_hour_label(entry.get("label", ""))
            if hour is None:
                _LOGGER.warning(
                    "Skipping hourly entry with unparseable label: %s",
                    entry.get("label"),
                )
                continue
            hourly_data.append({"hour": hour, "value": entry["value"]})

        return hourly_data

    def get_yearly_consumption(self) -> List[Dict[str, Any]]:
        """Get yearly consumption data.

        Returns:
            List of dicts with 'year' and 'value' keys
        """
        data = self.get_consumption(view_scope="year")
        yearly_data: List[Dict[str, Any]] = []

        for entry in data.get("values", []):
            year = self._parse_int_from_label(entry.get("label", ""))
            if year is None:
                _LOGGER.warning(
                    "Skipping yearly entry with unparseable label: %s",
                    entry.get("label"),
                )
                continue
            yearly_data.append({"year": year, "value": entry["value"]})

        return yearly_data

    def get_monthly_consumption(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get monthly consumption data.

        Args:
            date: Date in "DD-MM-YYYY" format to specify the month

        Returns:
            List of dicts with 'day' and 'value' keys
        """
        if date is None:
            date = datetime.now().strftime("%d-%m-%Y")
        data = self.get_consumption(date, view_scope="month")
        monthly_data: List[Dict[str, Any]] = []

        for entry in data.get("values", []):
            day = self._parse_int_from_label(entry.get("label", ""))
            if day is None:
                _LOGGER.warning(
                    "Skipping monthly entry with unparseable label: %s",
                    entry.get("label"),
                )
                continue
            monthly_data.append({"day": day, "value": entry["value"]})

        return monthly_data

    def _parse_hour_label(self, label: str) -> Optional[int]:
        """Parse hour labels from API responses.

        Supported formats include:
        - "0" / "00"
        - "00:00"
        - "00:00 - 01:00"
        """
        # Prefer start-hour in time/range format if present.
        match = re.search(r"(\d{1,2}):\d{2}", label)
        if match:
            hour = int(match.group(1))
            return hour if 0 <= hour <= 23 else None

        hour = self._parse_int_from_label(label)
        if hour is None:
            return None
        return hour if 0 <= hour <= 23 else None

    def _parse_int_from_label(self, label: str) -> Optional[int]:
        """Extract the first integer from a label."""
        match = re.search(r"\d+", label)
        if not match:
            return None
        return int(match.group(0))
