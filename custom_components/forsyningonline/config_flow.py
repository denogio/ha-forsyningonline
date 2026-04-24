"""Config flow for ForsyningOnline integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from . import const
from .api import ForsyningOnlineClient, ForsyningOnlineAuthError, ForsyningOnlineApiError

_LOGGER = logging.getLogger(const.DOMAIN)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = ForsyningOnlineClient(data["username"], data["password"])

    try:
        await hass.async_add_executor_job(client.login)
    except ForsyningOnlineAuthError as err:
        raise ValueError("invalid_auth") from err
    except Exception as err:
        raise ValueError("cannot_connect") from err

    # Get locations
    try:
        locations = await hass.async_add_executor_job(client.get_locations)
    except ForsyningOnlineApiError as err:
        _LOGGER.error("Failed to get locations: %s", err)
        locations = []

    if not locations:
        raise ValueError("no_locations")

    # Return info for the first location (can be changed in options flow later)
    first_location = locations[0]

    return {
        "title": f"{first_location.get('utilityName', 'ForsyningOnline')} - {first_location.get('description', 'Unknown')}",
        "locations": locations,
        "selected_location": first_location,
    }


class ForsyningOnlineConfigFlow(config_entries.ConfigFlow, domain=const.DOMAIN):
    """Handle a config flow for ForsyningOnline."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.locations: list = []
        self.username: str = ""
        self.password: str = ""
        self._entry_data: Dict[str, Any] = {}
        self._entry_title: str = ""

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.username = user_input["username"]
            self.password = user_input["password"]

            try:
                info = await validate_input(self.hass, user_input)
                self.locations = info["locations"]

                # If only one location, auto-select it
                if len(self.locations) == 1:
                    self._entry_title = info["title"]
                    self._entry_data = {
                        "username": self.username,
                        "password": self.password,
                        const.ATTR_LOCATION: self.locations[0].get("description", "Unknown"),
                        const.ATTR_UTILITY_NAME: self.locations[0].get("utilityName", "Unknown"),
                        "location_guid": self.locations[0]["locationGuid"],
                        "relation_id": self.locations[0]["relationId"],
                    }
                    return await self.async_step_history()

                # Multiple locations - show selection step
                return await self.async_step_select_location()

            except ValueError as err:
                if str(err) == "invalid_auth":
                    errors["base"] = "invalid_auth"
                elif str(err) == "cannot_connect":
                    errors["base"] = "cannot_connect"
                elif str(err) == "no_locations":
                    errors["base"] = "no_locations"
                else:
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_location(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle location selection step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            location_index = int(user_input["location"])
            selected_location = self.locations[location_index]

            self._entry_title = f"{selected_location.get('utilityName', 'ForsyningOnline')} - {selected_location.get('description', 'Unknown')}"
            self._entry_data = {
                "username": self.username,
                "password": self.password,
                const.ATTR_LOCATION: selected_location.get("description", "Unknown"),
                const.ATTR_UTILITY_NAME: selected_location.get("utilityName", "Unknown"),
                "location_guid": selected_location["locationGuid"],
                "relation_id": selected_location["relationId"],
            }
            return await self.async_step_history()

        # Build location options
        location_schema = vol.Schema(
            {
                vol.Required("location"): vol.In(
                    {
                        str(i): f"{loc.get('utilityName', 'Unknown')} - {loc.get('description', 'Unknown')}"
                        for i, loc in enumerate(self.locations)
                    }
                )
            }
        )

        return self.async_show_form(
            step_id="select_location",
            data_schema=location_schema,
            errors=errors,
        )

    async def async_step_history(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle history import selection step."""
        if user_input is not None:
            self._entry_data["history_days"] = user_input["history_days"]
            return self.async_create_entry(
                title=self._entry_title,
                data=self._entry_data,
            )

        history_schema = vol.Schema(
            {
                vol.Required(
                    "history_days", default=const.DEFAULT_HISTORY_DAYS
                ): vol.In(
                    {
                        "7": "7 dage",
                        "30": "30 dage",
                        "90": "3 måneder",
                        "180": "6 måneder",
                        "365": "1 år",
                        "all": "Al tilgængelig data",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="history",
            data_schema=history_schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ForsyningOnlineOptionsFlow(config_entry)


class ForsyningOnlineOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ForsyningOnline."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                "scan_interval",
                default=self.config_entry.options.get("scan_interval", 3600),
            ): vol.All(vol.Coerce(int), vol.Range(min=300, max=86400)),
            vol.Optional(
                "history_days",
                default=self.config_entry.options.get(
                    "history_days", const.DEFAULT_HISTORY_DAYS
                ),
            ): vol.In(
                {
                    "7": "7 dage",
                    "30": "30 dage",
                    "90": "3 måneder",
                    "180": "6 måneder",
                    "365": "1 år",
                    "all": "Al tilgængelig data",
                }
            ),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
