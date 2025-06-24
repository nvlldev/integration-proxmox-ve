"""The Proxmox VE integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN, PLATFORMS
from .coordinator import ProxmoxVEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Proxmox VE from a config entry."""
    _LOGGER.debug("Setting up Proxmox VE integration")
    
    coordinator = ProxmoxVEDataUpdateCoordinator(
        hass=hass,
        config=entry.data,
        entry=entry,
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Proxmox VE integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Proxmox VE integration")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok