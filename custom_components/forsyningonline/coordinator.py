"""Data update coordinator for ForsyningOnline."""

import logging
import re
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import const
from .api import ForsyningOnlineClient, ForsyningOnlineApiError

_LOGGER = logging.getLogger(const.DOMAIN)


class ForsyningOnlineUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates for ForsyningOnline."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ForsyningOnlineClient,
        entry: ConfigEntry,
        location_guid: str,
        relation_id: str,
    ) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(
            "scan_interval", const.SCAN_INTERVAL_DAILY.total_seconds()
        )
        super().__init__(
            hass,
            _LOGGER,
            name=const.DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.location_guid = location_guid
        self.relation_id = relation_id
        self._entry = entry
        self._initial_import_done = False

    async def _async_update_data(self) -> dict:
        """Fetch data from ForsyningOnline."""
        try:
            # Set location before fetching data
            await self.hass.async_add_executor_job(
                self.client.set_location, self.location_guid, self.relation_id
            )

            # Get hourly data for today
            hourly = await self.hass.async_add_executor_job(
                self.client.get_hourly_consumption
            )

            # Get daily data (today's total)
            today_total = sum(h["value"] for h in hourly)

            # Get yearly data
            yearly = await self.hass.async_add_executor_job(
                self.client.get_yearly_consumption
            )

            # Calculate total consumption (sum of all years)
            total_consumption = sum(y["value"] for y in yearly)

            # Import hourly statistics for Energy dashboard
            await self._async_import_hourly_statistics(total_consumption)

            return {
                "hourly": hourly,
                "today_total": today_total,
                "yearly": yearly,
                "total_consumption": total_consumption,
                "last_update": datetime.now().isoformat(),
            }

        except ForsyningOnlineApiError as err:
            raise UpdateFailed(f"Error fetching ForsyningOnline data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _get_initial_days_back(self) -> int:
        """Get number of days to import on first run from options.

        Returns 0 for 'all available data'.
        """
        history_key = self._entry.options.get(
            "history_days", const.DEFAULT_HISTORY_DAYS
        )
        return const.HISTORY_DAYS_OPTIONS.get(history_key, 30)

    async def _async_import_hourly_statistics(self, total_consumption: float) -> None:
        """Import hourly consumption data as HA statistics.

        On first run, imports historical data based on the history_days
        option. Subsequent runs import the last 2 days to catch delayed
        API data.
        """
        from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
        from homeassistant.components.recorder.statistics import (
            async_import_statistics,
        )

        now = datetime.now()

        if self._initial_import_done:
            days_back = 2
        else:
            days_back = self._get_initial_days_back()
            if days_back == 0:
                # "all" — calculate from yearly data
                yearly = await self.hass.async_add_executor_job(
                    self.client.get_yearly_consumption
                )
                if yearly:
                    earliest_year = min(y["year"] for y in yearly)
                    start_of_earliest = datetime(earliest_year, 1, 1)
                    days_back = (now - start_of_earliest).days + 1
                else:
                    days_back = 365

        _LOGGER.debug(
            "Importing hourly statistics for %d days (initial=%s)",
            days_back,
            not self._initial_import_done,
        )

        # Fetch hourly data for each day (oldest first)
        daily_hourly: dict[datetime, list[dict]] = {}
        for days_ago in range(days_back - 1, -1, -1):
            target = now - timedelta(days=days_ago)
            date_str = target.strftime("%d-%m-%Y")
            try:
                hourly = await self.hass.async_add_executor_job(
                    self.client.get_hourly_consumption, date_str
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Failed to fetch hourly data for %s", date_str)
                continue
            if hourly:
                day_start = target.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                daily_hourly[day_start] = hourly

        if not daily_hourly:
            return

        # base = total meter reading before the imported period
        imported_total = sum(
            sum(h["value"] for h in hours)
            for hours in daily_hourly.values()
        )
        base = total_consumption - imported_total

        # Build statistics with correct cumulative sum
        all_stats: list[StatisticData] = []
        running_sum = base
        for day_start in sorted(daily_hourly.keys()):
            for h in daily_hourly[day_start]:
                running_sum += h["value"]
                all_stats.append(
                    StatisticData(
                        start=day_start.replace(hour=h["hour"]),
                        state=h["value"],
                        sum=running_sum,
                    )
                )

        entry_slug = re.sub(r"[^a-z0-9_]", "_", self._entry.entry_id.lower())
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="ForsyningOnline Water",
            source=const.DOMAIN,
            statistic_id=f"{const.DOMAIN}:water_consumption_{entry_slug}",
            unit_of_measurement="m³",
        )

        try:
            async_import_statistics(self.hass, metadata, all_stats)
            self._initial_import_done = True
            _LOGGER.debug(
                "Imported %d hourly statistics entries (%d days)",
                len(all_stats),
                len(daily_hourly),
            )
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to import hourly statistics", exc_info=True
            )
