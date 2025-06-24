"""Sensor platform for Proxmox VE integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import ProxmoxVEDataUpdateCoordinator
from .entity import ProxmoxVEEntity
from .entity_descriptions import (
    CONTAINER_SENSORS,
    NODE_SENSORS,
    NODE_SPECIFIC_SENSORS,
    ProxmoxSensorEntityDescription,
    STORAGE_SENSORS,
    VM_SENSORS,
)
from .models import ProxmoxContainer, ProxmoxData, ProxmoxNode, ProxmoxResource, ProxmoxStorage, ProxmoxVM

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE sensor platform."""
    coordinator: ProxmoxVEDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]
    
    entities: list[SensorEntity] = []
    
    if coordinator.data:
        data: ProxmoxData = coordinator.data
        
        # Add node sensors
        for node in data.nodes:
            # Add common sensors
            for description in NODE_SENSORS:
                entities.append(
                    ProxmoxNodeSensor(
                        coordinator=coordinator,
                        resource_id=node.node_id,
                        description=description,
                    )
                )
            
            # Add node-specific sensors
            for description in NODE_SPECIFIC_SENSORS:
                entities.append(
                    ProxmoxNodeSensor(
                        coordinator=coordinator,
                        resource_id=node.node_id,
                        description=description,
                    )
                )
        
        # Add VM sensors
        for vm in data.vms:
            for description in VM_SENSORS:
                entities.append(
                    ProxmoxVMSensor(
                        coordinator=coordinator,
                        resource_id=str(vm.vmid),
                        description=description,
                    )
                )
        
        # Add container sensors
        for container in data.containers:
            for description in CONTAINER_SENSORS:
                entities.append(
                    ProxmoxContainerSensor(
                        coordinator=coordinator,
                        resource_id=str(container.vmid),
                        description=description,
                    )
                )
        
        # Add storage sensors
        for storage in data.storages:
            for description in STORAGE_SENSORS:
                entities.append(
                    ProxmoxStorageSensor(
                        coordinator=coordinator,
                        resource_id=storage.storage_id,
                        description=description,
                    )
                )
    
    if entities:
        _LOGGER.info("Adding %d Proxmox VE sensor entities", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.warning("No Proxmox VE entities found to create")


class ProxmoxSensor(ProxmoxVEEntity, SensorEntity):
    """Base class for Proxmox VE sensors."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        resource_type: str,
        description: ProxmoxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, resource_id, resource_type)
        self.entity_description = description
        self._attr_translation_key = description.key
        
        # Build unique ID
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{resource_type}_{resource_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        resource = self._get_resource()
        if resource is None:
            return None
        
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(resource)
        
        return None

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


class ProxmoxNodeSensor(ProxmoxSensor):
    """Sensor for Proxmox VE nodes."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        description: ProxmoxSensorEntityDescription,
    ) -> None:
        """Initialize the node sensor."""
        super().__init__(coordinator, resource_id, "node", description)

    def _get_resource(self) -> ProxmoxNode | None:
        """Get the node resource."""
        resource = super()._get_resource()
        return resource if isinstance(resource, ProxmoxNode) else None


class ProxmoxVMSensor(ProxmoxSensor):
    """Sensor for Proxmox VE VMs."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        description: ProxmoxSensorEntityDescription,
    ) -> None:
        """Initialize the VM sensor."""
        super().__init__(coordinator, resource_id, "vm", description)

    def _get_resource(self) -> ProxmoxVM | None:
        """Get the VM resource."""
        resource = super()._get_resource()
        return resource if isinstance(resource, ProxmoxVM) else None


class ProxmoxContainerSensor(ProxmoxSensor):
    """Sensor for Proxmox VE containers."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        description: ProxmoxSensorEntityDescription,
    ) -> None:
        """Initialize the container sensor."""
        super().__init__(coordinator, resource_id, "container", description)

    def _get_resource(self) -> ProxmoxContainer | None:
        """Get the container resource."""
        resource = super()._get_resource()
        return resource if isinstance(resource, ProxmoxContainer) else None


class ProxmoxStorageSensor(ProxmoxSensor):
    """Sensor for Proxmox VE storage pools."""

    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        resource_id: str,
        description: ProxmoxSensorEntityDescription,
    ) -> None:
        """Initialize the storage sensor."""
        super().__init__(coordinator, resource_id, "storage", description)

    def _get_resource(self) -> ProxmoxStorage | None:
        """Get the storage resource."""
        resource = super()._get_resource()
        return resource if isinstance(resource, ProxmoxStorage) else None