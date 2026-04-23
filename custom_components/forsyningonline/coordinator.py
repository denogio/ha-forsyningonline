"""Data update coordinator for ForsyningOnline."""

import logging
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
            self._import_hourly_statistics(hourly)

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

    def _import_hourly_statistics(self, hourly: list[dict]) -> None:
        """Import hourly consumption data as HA statistics."""
        if not hourly:
            return

        from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
        from homeassistant.components.recorder.statistics import (
            async_import_statistics,
        )

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="ForsyningOnline Water Consumption",
            source=const.DOMAIN,
            statistic_id=f"{const.DOMAIN}:water_consumption_{self._entry.entry_id}",
            unit_of_measurement="m³",
        )

        today = datetime.now().replace(minute=0, second=0, microsecond=0)
        stats: list[StatisticData] = []
        cumsum = 0.0

        for hour_data in hourly:
            cumsum += hour_data["value"]
            hour_start = today.replace(hour=hour_data["hour"])
            stats.append(StatisticData(
                start=hour_start,
                state=cumsum,
                sum=cumsum,
            ))

        async_import_statistics(self.hass, metadata, stats)
