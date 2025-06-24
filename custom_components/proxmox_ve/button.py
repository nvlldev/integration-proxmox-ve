"""Button platform for Proxmox VE integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_client import ProxmoxVEAPIClient
from .button_descriptions import (
    CONTAINER_BUTTONS,
    ProxmoxButtonEntityDescription,
    VM_BUTTONS,
)
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import ProxmoxVEDataUpdateCoordinator
from .entity import ProxmoxVEEntity
from .exceptions import ProxmoxVEError
from .models import ProxmoxContainer, ProxmoxData, ProxmoxVM

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE button platform."""
    coordinator: ProxmoxVEDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]
    
    entities: list[ButtonEntity] = []
    
    if coordinator.data:
        data: ProxmoxData = coordinator.data
        
        # Add VM buttons
        for vm in data.vms:
            for description in VM_BUTTONS:
                entities.append(
                    ProxmoxVMButton(
                        coordinator=coordinator,
                        resource_id=str(vm.vmid),
                        description=description,
                    )
                )
        
        # Add container buttons
        for container in data.containers:
            for description in CONTAINER_BUTTONS:
                entities.append(
                    ProxmoxContainerButton(
                        coordinator=coordinator,
                        resource_id=str(container.vmid),
                        description=description,
                    )
                )
    
    if entities:
        _LOGGER.info("Adding %d Proxmox VE button entities", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.warning("No Proxmox VE button entities found to create")


class ProxmoxButton(ProxmoxVEEntity, ButtonEntity):
    """Base class for Proxmox VE buttons."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        resource_type: str,
        description: ProxmoxButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, resource_id, resource_type)
        self.entity_description = description
        self._attr_translation_key = description.key
        
        # Build unique ID
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{resource_type}_{resource_id}_button_{description.key}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        
        resource = self._get_resource()
        if resource is None:
            return False
        
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(resource)
        
        return True

    async def async_press(self) -> None:
        """Handle the button press."""
        resource = self._get_resource()
        if resource is None:
            raise HomeAssistantError("Resource not found")
        
        try:
            # Get API client from coordinator
            client = ProxmoxVEAPIClient(self.hass, self.coordinator.config_entry.data)
            
            # Execute the control action
            await self._execute_action(client, resource)
            
            # Clean up client
            await client.async_close()
            
            # Request coordinator refresh after action
            await self.coordinator.async_request_refresh()
            
        except ProxmoxVEError as err:
            _LOGGER.error("Failed to execute %s action: %s", self.entity_description.key, err)
            raise HomeAssistantError(f"Failed to {self.entity_description.key} {self._resource_type}: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error executing %s action: %s", self.entity_description.key, err)
            raise HomeAssistantError(f"Unexpected error: {err}") from err

    async def _execute_action(self, client: ProxmoxVEAPIClient, resource: ProxmoxVM | ProxmoxContainer) -> None:
        """Execute the specific action - to be implemented by subclasses."""
        raise NotImplementedError


class ProxmoxVMButton(ProxmoxButton):
    """Button for Proxmox VE VMs."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        description: ProxmoxButtonEntityDescription,
    ) -> None:
        """Initialize the VM button."""
        super().__init__(coordinator, resource_id, "vm", description)

    def _get_resource(self) -> ProxmoxVM | None:
        """Get the VM resource."""
        resource = super()._get_resource()
        return resource if isinstance(resource, ProxmoxVM) else None

    async def _execute_action(self, client: ProxmoxVEAPIClient, resource: ProxmoxVM) -> None:
        """Execute VM control action."""
        action = self.entity_description.key
        node = resource.node
        vmid = resource.vmid
        
        _LOGGER.info("Executing %s action for VM %d on node %s", action, vmid, node)
        
        if action == "start":
            await client.async_vm_start(node, vmid)
        elif action == "stop":
            await client.async_vm_stop(node, vmid)
        elif action == "shutdown":
            await client.async_vm_shutdown(node, vmid)
        elif action == "reboot":
            await client.async_vm_reboot(node, vmid)
        elif action == "reset":
            await client.async_vm_reset(node, vmid)
        elif action == "suspend":
            await client.async_vm_suspend(node, vmid)
        elif action == "resume":
            await client.async_vm_resume(node, vmid)
        else:
            raise HomeAssistantError(f"Unknown VM action: {action}")


class ProxmoxContainerButton(ProxmoxButton):
    """Button for Proxmox VE containers."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        description: ProxmoxButtonEntityDescription,
    ) -> None:
        """Initialize the container button."""
        super().__init__(coordinator, resource_id, "container", description)

    def _get_resource(self) -> ProxmoxContainer | None:
        """Get the container resource."""
        resource = super()._get_resource()
        return resource if isinstance(resource, ProxmoxContainer) else None

    async def _execute_action(self, client: ProxmoxVEAPIClient, resource: ProxmoxContainer) -> None:
        """Execute container control action."""
        action = self.entity_description.key
        node = resource.node
        vmid = resource.vmid
        
        _LOGGER.info("Executing %s action for container %d on node %s", action, vmid, node)
        
        if action == "start":
            await client.async_container_start(node, vmid)
        elif action == "stop":
            await client.async_container_stop(node, vmid)
        elif action == "shutdown":
            await client.async_container_shutdown(node, vmid)
        elif action == "reboot":
            await client.async_container_reboot(node, vmid)
        elif action == "suspend":
            await client.async_container_suspend(node, vmid)
        elif action == "resume":
            await client.async_container_resume(node, vmid)
        else:
            raise HomeAssistantError(f"Unknown container action: {action}")