"""DataUpdateCoordinator for Proxmox VE."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import ProxmoxVEAPIClient
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .exceptions import ProxmoxVEError
from .models import ProxmoxData

_LOGGER = logging.getLogger(__name__)


class ProxmoxVEDataUpdateCoordinator(DataUpdateCoordinator[ProxmoxData]):
    """Class to manage fetching Proxmox VE data from API.
    
    This coordinator handles:
    - Concurrent API calls for better performance
    - Proper error handling with specific exceptions
    - Data model transformation from raw API responses
    - Connection lifecycle management
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self._client = ProxmoxVEAPIClient(hass, config_entry.data)
        
        update_interval = timedelta(
            seconds=config_entry.options.get(
                CONF_UPDATE_INTERVAL, 
                config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            )
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> ProxmoxData:
        """Fetch data from Proxmox VE API.
        
        Returns:
            ProxmoxData: Structured data containing nodes, VMs, and containers.
            
        Raises:
            UpdateFailed: When API calls fail or data cannot be retrieved.
        """
        _LOGGER.debug("Fetching data from Proxmox VE API")
        
        try:
            # Use the async API client to get all data concurrently
            raw_data = await self._client.async_get_all_data()
            
            # Transform raw API data into structured models
            data = ProxmoxData.from_api_data(raw_data)
            
            _LOGGER.debug(
                "Successfully fetched data: %d nodes, %d VMs, %d containers",
                len(data.nodes),
                len(data.vms),
                len(data.containers),
            )
            
            return data
            
        except ProxmoxVEError as err:
            _LOGGER.error("Proxmox VE API error: %s", err)
            raise UpdateFailed(f"Proxmox VE API error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error fetching Proxmox VE data: %s", err)
            raise UpdateFailed(f"Error communicating with Proxmox VE: {err}") from err
    
    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and clean up resources."""
        _LOGGER.debug("Shutting down Proxmox VE coordinator")
        await self._client.async_close()