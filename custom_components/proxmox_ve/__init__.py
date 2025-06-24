"""The Proxmox VE integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from proxmoxer.core import AuthenticationError
from requests.exceptions import ConnectionError

from .api import ProxmoxClient
from .const import (
    CONF_TOKEN_NAME,
    CONF_TOKEN_VALUE,
    CONF_UPDATE_INTERVAL,
    CONF_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_restart_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Restart the coordinator with updated configuration."""
    # Get the coordinator key
    coordinator_key = f"{entry.entry_id}_coordinator"
    
    # Check if coordinator exists
    if coordinator_key in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][coordinator_key]
        
        # Update the coordinator's update interval
        from datetime import timedelta
        from .const import DEFAULT_UPDATE_INTERVAL
        
        new_interval = timedelta(seconds=entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)))
        coordinator.update_interval = new_interval
        
        # Trigger an immediate update
        await coordinator.async_request_refresh()
        
        _LOGGER.debug("Updated coordinator with new interval: %s seconds", new_interval.total_seconds())


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Proxmox VE from a config entry."""
    if entry.data.get(CONF_PASSWORD):
        client = ProxmoxClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            verify_ssl=entry.data[CONF_VERIFY_SSL],
        )
    else:
        client = ProxmoxClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            token_name=entry.data[CONF_TOKEN_NAME],
            token_value=entry.data[CONF_TOKEN_VALUE],
            verify_ssl=entry.data[CONF_VERIFY_SSL],
        )

    try:
        await hass.async_add_executor_job(client.authenticate)
    except AuthenticationError as exc:
        raise ConfigEntryAuthFailed from exc
    except ConnectionError as exc:
        raise ConfigEntryNotReady from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    # Set up a listener for config entry updates
    entry.async_on_unload(
        entry.add_update_listener(async_restart_coordinator)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Clean up coordinator
        coordinator_key = f"{entry.entry_id}_coordinator"
        if coordinator_key in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][coordinator_key]
            if hasattr(coordinator, 'async_shutdown'):
                await coordinator.async_shutdown()
            hass.data[DOMAIN].pop(coordinator_key)
        
        # Clean up client
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
