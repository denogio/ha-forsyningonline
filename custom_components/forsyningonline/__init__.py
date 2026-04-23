"""The ForsyningOnline integration."""

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from . import const, coordinator
from .api import ForsyningOnlineAuthError, ForsyningOnlineClient

_LOGGER = logging.getLogger(const.DOMAIN)

PLATFORMS: Final = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ForsyningOnline from a config entry."""
    username = entry.data.get("username")
    password = entry.data.get("password")
    location_guid = entry.data.get("location_guid")
    relation_id = entry.data.get("relation_id")

    if not all([username, password, location_guid, relation_id]):
        _LOGGER.error("Missing required configuration data")
        return False

    # Create API client
    client = ForsyningOnlineClient(username, password)

    # Login
    try:
        await hass.async_add_executor_job(client.login)
    except ForsyningOnlineAuthError as err:
        _LOGGER.error("Invalid credentials: %s", err)
        return False
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to connect: {err}") from err

    # Create coordinator
    coord = coordinator.ForsyningOnlineUpdateCoordinator(
        hass, client, entry, location_guid, relation_id
    )

    # Fetch initial data
    await coord.async_config_entry_first_refresh()

    hass.data.setdefault(const.DOMAIN, {})[entry.entry_id] = coord

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload when options change
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[const.DOMAIN].pop(entry.entry_id)

    return unload_ok
