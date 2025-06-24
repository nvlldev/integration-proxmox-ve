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
        
        update_interval = timedelta(
            seconds=config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Proxmox VE."""
        _LOGGER.debug("Fetching data from Proxmox VE")
        
        try:
            data = await self.hass.async_add_executor_job(
                self.client.async_get_data
            )
            _LOGGER.debug(
                "Successfully fetched data: %d nodes, %d VMs, %d containers",
                len(data.get("nodes", [])),
                len(data.get("vms", [])),
                len(data.get("containers", [])),
            )
            return data
            
        except Exception as err:
            _LOGGER.error("Error fetching Proxmox VE data: %s", err)
            raise UpdateFailed(f"Error communicating with Proxmox VE: {err}") from err