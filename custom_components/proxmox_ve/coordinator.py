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
        self._consecutive_failures = 0
        self._known_nodes = set()  # Track nodes we've seen before
        
        update_interval = timedelta(
            seconds=config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            # Enable always_update=True to ensure entities update on schedule
            always_update=True,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Proxmox VE with error resilience."""
        import time
        start_time = time.time()
        _LOGGER.info("Starting coordinator data fetch (attempt %d)", self._consecutive_failures + 1)
        
        try:
            data = await self.hass.async_add_executor_job(
                self.client.async_get_data
            )
            
            # Success - reset failure counter
            self._consecutive_failures = 0
            
            # Track nodes we've seen for future reference
            for node in data.get("nodes", []):
                node_name = node.get("node")
                if node_name:
                    self._known_nodes.add(node_name)
            
            # Add any previously known nodes that aren't in current data as unavailable
            current_node_names = {node.get("node") for node in data.get("nodes", [])}
            for known_node in self._known_nodes:
                if known_node not in current_node_names:
                    _LOGGER.info("Adding previously known node %s as unavailable", known_node)
                    data["nodes"].append({
                        "node": known_node,
                        "available": False,
                        "load_average": [0.0, 0.0, 0.0],
                        "cpu_info": {},
                        "cpu": 0,
                        "mem": 0,
                        "maxmem": 1,
                        "disk": 0,
                        "maxdisk": 1,
                        "uptime": 0,
                        "status": "unknown"
                    })
            
            fetch_duration = time.time() - start_time
            _LOGGER.info(
                "Coordinator fetch completed in %.2fs: %d nodes, %d VMs, %d containers",
                fetch_duration,
                len(data.get("nodes", [])),
                len(data.get("vms", [])),
                len(data.get("containers", [])),
            )
            return data
            
        except Exception as err:
            self._consecutive_failures += 1
            
            _LOGGER.error(
                "Error fetching Proxmox VE data after %d consecutive failures: %s", 
                self._consecutive_failures, err
            )
            raise UpdateFailed(f"Error communicating with Proxmox VE: {err}") from err