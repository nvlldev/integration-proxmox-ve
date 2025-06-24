"""DataUpdateCoordinator for Proxmox VE."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ProxmoxVEClient
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ProxmoxVEDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Proxmox VE data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.client = ProxmoxVEClient(config)
        self.config = config
        self.entry = entry
        self._last_successful_data = None
        self._consecutive_failures = 0
        
        update_interval = timedelta(
            seconds=config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            # Enable always_update=False for better performance if data doesn't change
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Proxmox VE with error resilience."""
        _LOGGER.debug("Fetching data from Proxmox VE (attempt %d)", self._consecutive_failures + 1)
        
        try:
            data = await self.hass.async_add_executor_job(
                self.client.async_get_data
            )
            
            # Success - reset failure counter and cache the data
            self._consecutive_failures = 0
            self._last_successful_data = data
            
            _LOGGER.debug(
                "Successfully fetched data: %d nodes, %d VMs, %d containers",
                len(data.get("nodes", [])),
                len(data.get("vms", [])),
                len(data.get("containers", [])),
            )
            return data
            
        except Exception as err:
            self._consecutive_failures += 1
            
            # If we have recent successful data and this is just a temporary failure,
            # return the cached data instead of failing completely
            if self._last_successful_data and self._consecutive_failures <= 3:
                _LOGGER.warning(
                    "Error fetching Proxmox VE data (failure %d/3), using cached data: %s", 
                    self._consecutive_failures, err
                )
                return self._last_successful_data
            
            # Too many consecutive failures or no cached data - fail the update
            _LOGGER.error(
                "Error fetching Proxmox VE data after %d consecutive failures: %s", 
                self._consecutive_failures, err
            )
            raise UpdateFailed(f"Error communicating with Proxmox VE: {err}") from err