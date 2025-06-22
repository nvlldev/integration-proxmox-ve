"""The Proxmox VE integration."""
from __future__ import annotations

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

PLATFORMS: list[Platform] = [Platform.SENSOR]


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
