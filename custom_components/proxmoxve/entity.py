"""Base entity for Proxmox VE integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxVEDataUpdateCoordinator
from .models import ProxmoxData, ProxmoxResource, ProxmoxStorage


class ProxmoxVEEntity(CoordinatorEntity[ProxmoxVEDataUpdateCoordinator]):
    """Base entity for Proxmox VE integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        resource_type: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._resource_id = resource_id
        self._resource_type = resource_type
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{resource_type}_{resource_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # Proper capitalization for resource types
        resource_type_names = {
            "node": "Node",
            "vm": "VM", 
            "container": "Container",
            "storage": "Storage",
        }
        
        display_name = resource_type_names.get(self._resource_type, self._resource_type.title())
        
        resource = self._get_resource()
        if resource is None:
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self._resource_type}_{self._resource_id}")},
                name=f"Proxmox VE {display_name} {self._resource_id}",
                manufacturer="Proxmox",
                model=display_name,
            )

        host = self.coordinator.config_entry.data["host"]
        port = self.coordinator.config_entry.data.get("port", 8006)

        # Get the appropriate name attribute based on resource type
        if isinstance(resource, ProxmoxStorage):
            resource_name = resource.storage
        else:
            resource_name = resource.name

        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._resource_type}_{self._resource_id}")},
            name=f"Proxmox VE {display_name} {resource_name}",
            manufacturer="Proxmox",
            model=display_name,
            configuration_url=f"https://{host}:{port}/",
        )

        # Add parent device for VMs, containers, and storage
        if self._resource_type in ("vm", "container", "storage"):
            device_info["via_device"] = (DOMAIN, f"node_{resource.node}")

        return device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        resource = self._get_resource()
        if resource is None:
            return False

        # For nodes, check availability status
        if self._resource_type == "node" and hasattr(resource, "available"):
            return resource.available

        return True

    def _get_resource(self) -> ProxmoxResource | ProxmoxStorage | None:
        """Get the resource data from coordinator."""
        if not self.coordinator.data:
            return None

        data: ProxmoxData = self.coordinator.data

        if self._resource_type == "node":
            return data.get_node_by_id(self._resource_id)
        elif self._resource_type == "vm":
            return data.get_vm_by_id(int(self._resource_id))
        elif self._resource_type == "container":
            return data.get_container_by_id(int(self._resource_id))
        elif self._resource_type == "storage":
            return data.get_storage_by_id(self._resource_id)

        return None