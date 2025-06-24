"""Base entity for Proxmox VE integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxVEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ProxmoxVEEntity(CoordinatorEntity[ProxmoxVEDataUpdateCoordinator]):
    """Base entity for Proxmox VE."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        device_type: str,
        device_id: str,
        device_name: str,
        attribute_name: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        
        self.device_type = device_type
        self.device_id = device_id
        self.device_name = device_name
        self.attribute_name = attribute_name
        
        # Create unique entity ID
        self._attr_unique_id = f"{DOMAIN}_{device_type}_{device_id}_{attribute_name}"
        
        # Set entity name
        self._attr_name = f"{device_name} {attribute_name.replace('_', ' ').title()}"
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{device_type}_{device_id}")},
            name=device_name,
            manufacturer="Proxmox",
            model=device_type,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        if not self.coordinator.data:
            return None
            
        # Find the device in coordinator data
        devices_key = f"{self.device_type.lower()}s"
        if self.device_type.lower() == "node":
            devices_key = "nodes"
        elif self.device_type.lower() == "vm":
            devices_key = "vms"
        elif self.device_type.lower() == "container":
            devices_key = "containers"
            
        devices = self.coordinator.data.get(devices_key, [])
        
        for device in devices:
            if self.device_type.lower() == "node":
                if device.get("node") == self.device_id:
                    return device
            else:
                if str(device.get("vmid")) == str(self.device_id):
                    return device
                    
        return None