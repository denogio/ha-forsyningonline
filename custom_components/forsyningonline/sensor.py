"""Sensor platform for ForsyningOnline integration."""

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const

_LOGGER = logging.getLogger(const.DOMAIN)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ForsyningOnline sensors from a config entry."""
    coord = hass.data[const.DOMAIN][entry.entry_id]

    entities = [
        ForsyningOnlineTotalWaterSensor(coord, entry),
        ForsyningOnlineDailyWaterSensor(coord, entry),
    ]

    async_add_entities(entities)


class ForsyningOnlineSensor(CoordinatorEntity, SensorEntity):
    """Base class for ForsyningOnline sensors."""

    _attr_has_entity_name = True

    def __init__(self, coord, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coord)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(const.DOMAIN, entry.entry_id)},
            "name": entry.data.get(const.ATTR_UTILITY_NAME, "ForsyningOnline"),
            "manufacturer": "ForsyningOnline",
            "model": "Water Meter",
        }


class ForsyningOnlineTotalWaterSensor(ForsyningOnlineSensor):
    """Sensor for total cumulative water consumption."""

    def __init__(self, coord, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_water_total"
        self._attr_translation_key = "water_total"
        self._attr_icon = "mdi:water"
        self._attr_native_unit_of_measurement = "m³"
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 3

    @property
    def native_value(self):
        """Return the current meter reading (cumulative total)."""
        if self.coordinator.data and "total_consumption" in self.coordinator.data:
            return round(self.coordinator.data["total_consumption"], 3)
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        attrs = {}
        if self.coordinator.data:
            attrs["location"] = self._entry.data.get(const.ATTR_LOCATION, "Unknown")
            attrs["utility_name"] = self._entry.data.get(const.ATTR_UTILITY_NAME, "Unknown")
            attrs["last_update"] = self.coordinator.data.get("last_update")
        return attrs


class ForsyningOnlineDailyWaterSensor(ForsyningOnlineSensor):
    """Sensor for daily water consumption."""

    def __init__(self, coord, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_water_today"
        self._attr_translation_key = "water_today"
        self._attr_icon = "mdi:water-pump"
        self._attr_native_unit_of_measurement = "m³"
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_suggested_display_precision = 3

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and "today_total" in self.coordinator.data:
            return round(self.coordinator.data["today_total"], 3)
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        attrs = {}
        if self.coordinator.data:
            attrs["hourly_breakdown"] = self.coordinator.data.get("hourly", [])
            attrs["date"] = datetime.now().strftime("%Y-%m-%d")
        return attrs

    @property
    def last_reset(self):
        """Return the last reset time (start of today)."""
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
