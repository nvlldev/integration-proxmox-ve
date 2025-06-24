"""Sensor platform for Proxmox VE integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTime, UnitOfFrequency
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import ProxmoxVEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Backward compatibility: Use exact same abbreviation map as old integration
_ABBREVIATION_MAP = {
    'cpu': 'CPU',
    'vm': 'VM',
    'lxc': 'LXC',
    'id': 'ID',
    'mhz': 'MHz',
    'gb': 'GB',
    'mb': 'MB',
    'kb': 'KB',
    'io': 'IO',
    'api': 'API',
    've': 'VE',
    'ssd': 'SSD',
    'hdd': 'HDD',
    'os': 'OS',
    'ram': 'RAM',
    'ip': 'IP',
    'mac': 'MAC',
    'lvm': 'LVM',
    'nvme': 'NVMe',
    'sata': 'SATA',
    'scsi': 'SCSI',
    'uuid': 'UUID',
    'vmid': 'VMID',
    'qemu': 'QEMU',
    'lxc': 'LXC',
    'proxmox': 'Proxmox',
    've': 'VE',
}

def _prettify_attr_name(attr_name: str) -> str:
    """Prettify attribute name - exact same function as old integration."""
    # Split by underscores, capitalize each part, but use abbreviation map if present
    parts = attr_name.split('_')
    pretty = []
    for part in parts:
        lower = part.lower()
        pretty.append(_ABBREVIATION_MAP.get(lower, part.capitalize()))
    return ' '.join(pretty)

# Exact same sensor definitions as old integration
NODE_SENSORS = [
    "cpu_usage_percent",
    "memory_used_bytes", 
    "memory_total_bytes",
    "disk_used_bytes",
    "disk_total_bytes", 
    "uptime_seconds",
    "memory_usage_percent",
    "load_average_1min",
    "load_average_5min", 
    "load_average_15min",
    "cpu_frequency_mhz",
    "cpu_cores",
    "cpu_sockets",
    "cpu_total_logical",
    "cpu_model",
]

VM_SENSORS = [
    "cpu_usage_percent",
    "memory_used_bytes",
    "memory_total_bytes", 
    "disk_used_bytes",
    "disk_total_bytes",
    "uptime_seconds",
    "node_name",
    "memory_usage_percent",
]

CONTAINER_SENSORS = [
    "cpu_usage_percent",
    "memory_used_bytes",
    "memory_total_bytes",
    "disk_used_bytes", 
    "disk_total_bytes",
    "uptime_seconds",
    "node_name",
    "memory_usage_percent",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE sensor platform."""
    coordinator: ProxmoxVEDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    
    entities = []
    
    if coordinator.data:
        host = entry.data["host"]
        port = entry.data.get("port", 8006)
        
        # Add node sensors - exact same logic as old integration
        for node in coordinator.data.get("nodes", []):
            node_name = node.get("node", "unknown")
            node_id = node_name
            
            # Device info for node - exact same as old integration
            node_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"node_{host}_{node_name}")},
                name=f"Proxmox VE Node {node_name}",
                manufacturer="Proxmox",
                model="Node",
                configuration_url=f"https://{host}:{port}/"
            )
            
            for attr_name in NODE_SENSORS:
                entities.append(
                    ProxmoxVEBackwardCompatibleSensor(
                        coordinator=coordinator,
                        entry_id=entry.entry_id,
                        host=host,
                        device_type="Node",
                        device_id=node_id,
                        device_name=node_name,
                        attr_name=attr_name,
                        device_info=node_device_info,
                    )
                )
        
        # Add VM sensors - exact same logic as old integration
        for vm in coordinator.data.get("vms", []):
            vmid = vm["vmid"]
            vm_name = vm.get("name", f"VM {vmid}")
            node_name = vm.get("node", "unknown")
            
            # Device info for VM - exact same as old integration
            vm_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"vm_{host}_{node_name}_{vmid}")},
                name=f"Proxmox VE VM {vm_name}",
                manufacturer="Proxmox",
                model="VM",
                via_device=(DOMAIN, f"node_{host}_{node_name}"),
                configuration_url=f"https://{host}:{port}/"
            )
            
            for attr_name in VM_SENSORS:
                entities.append(
                    ProxmoxVEBackwardCompatibleSensor(
                        coordinator=coordinator,
                        entry_id=entry.entry_id,
                        host=host,
                        device_type="VM",
                        device_id=vmid,
                        device_name=vm_name,
                        attr_name=attr_name,
                        device_info=vm_device_info,
                    )
                )
        
        # Add container sensors - exact same logic as old integration
        for container in coordinator.data.get("containers", []):
            container_id = container.get("id") or container.get("vmid")
            container_name = container.get("name", f"Container {container_id}")
            node_name = container.get("node", "unknown")
            
            # Device info for container - exact same as old integration
            container_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"container_{host}_{node_name}_{container_id}")},
                name=f"Proxmox VE Container {container_name}",
                manufacturer="Proxmox",
                model="Container",
                via_device=(DOMAIN, f"node_{host}_{node_name}"),
                configuration_url=f"https://{host}:{port}/"
            )
            
            for attr_name in CONTAINER_SENSORS:
                entities.append(
                    ProxmoxVEBackwardCompatibleSensor(
                        coordinator=coordinator,
                        entry_id=entry.entry_id,
                        host=host,
                        device_type="Container",
                        device_id=container_id,
                        device_name=container_name,
                        attr_name=attr_name,
                        device_info=container_device_info,
                    )
                )
    
    if entities:
        _LOGGER.info("Adding %d Proxmox VE sensor entities", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.warning("No Proxmox VE entities found to create")


class ProxmoxVEBackwardCompatibleSensor(CoordinatorEntity[ProxmoxVEDataUpdateCoordinator], SensorEntity):
    """Backward compatible Proxmox VE sensor - exact same as old integration."""
    
    def __init__(
        self,
        coordinator: ProxmoxVEDataUpdateCoordinator,
        entry_id: str,
        host: str,
        device_type: str,
        device_id: str,
        device_name: str,
        attr_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._host = host
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name
        self._raw_attr_name = attr_name
        self._attr_device_info = device_info
        
        # Create entity name exactly like old integration
        pretty_device_type = _ABBREVIATION_MAP.get(device_type.lower(), device_type)
        pretty_attr_name = _prettify_attr_name(attr_name)
        self._attr_name = f"Proxmox VE {pretty_device_type} {device_name} {pretty_attr_name}"
        
        # Create unique ID exactly like old integration
        self._attr_unique_id = f"proxmox_ve_{device_type.lower()}_{device_id}_{attr_name}_{entry_id}"
        
        # Set attributes based on sensor type
        self._set_sensor_attributes()
        
        _LOGGER.debug("Created backward compatible sensor: %s", self._attr_name)
    
    def _set_sensor_attributes(self):
        """Set sensor attributes based on the attribute name."""
        # Set defaults
        self._attr_state_class = None
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_icon = None
        
        # Set attributes based on type - exact same logic as old integration
        if "percent" in self._raw_attr_name:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_device_class = SensorDeviceClass.POWER_FACTOR
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:percent"
        elif "memory" in self._raw_attr_name and "bytes" in self._raw_attr_name:
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:memory"
        elif "disk" in self._raw_attr_name and "bytes" in self._raw_attr_name:
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:harddisk"
        elif "uptime" in self._raw_attr_name:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:timer-sand"
        elif "frequency" in self._raw_attr_name:
            self._attr_device_class = SensorDeviceClass.FREQUENCY
            self._attr_native_unit_of_measurement = UnitOfFrequency.MEGAHERTZ
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:chip"
        elif "load_average" in self._raw_attr_name:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:chip"
        elif self._raw_attr_name in ("cpu_cores", "cpu_sockets", "cpu_total_logical"):
            self._attr_icon = "mdi:chip"
        elif self._raw_attr_name == "node_name":
            self._attr_icon = "mdi:server"
        elif self._raw_attr_name == "cpu_model":
            self._attr_icon = "mdi:chip"

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        device_data = self._get_device_data()
        
        if device_data is None:
            return None
            
        # Get value using exact same logic as old integration
        if self._device_type == "Node":
            return self._get_node_value(device_data)
        elif self._device_type == "VM":
            return self._get_vm_value(device_data)
        elif self._device_type == "Container":
            return self._get_container_value(device_data)
            
        return None
    
    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        if not self.coordinator.data:
            return None
            
        # Find the device in coordinator data
        if self._device_type == "Node":
            for node in self.coordinator.data.get("nodes", []):
                if str(node.get("node")) == str(self._device_id):
                    return node
        elif self._device_type == "VM":
            for vm in self.coordinator.data.get("vms", []):
                if str(vm.get("vmid")) == str(self._device_id):
                    return vm
        elif self._device_type == "Container":
            for container in self.coordinator.data.get("containers", []):
                container_id = container.get("id") or container.get("vmid")
                if str(container_id) == str(self._device_id):
                    return container
                    
        return None
    
    def _get_node_value(self, node_data: dict[str, Any]) -> Any:
        """Get node value - exact same logic as old integration."""
        if self._raw_attr_name == "cpu_usage_percent":
            return float(node_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            return node_data.get("mem", 0)
        elif self._raw_attr_name == "memory_total_bytes":
            return node_data.get("maxmem", 0)
        elif self._raw_attr_name == "disk_used_bytes":
            return node_data.get("disk", 0)
        elif self._raw_attr_name == "disk_total_bytes":
            return node_data.get("maxdisk", 0)
        elif self._raw_attr_name == "uptime_seconds":
            return node_data.get("uptime", 0)
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(node_data.get("mem", 0))
            maxmem = float(node_data.get("maxmem", 1))
            return (mem / maxmem * 100) if maxmem > 0 else 0.0
        elif self._raw_attr_name.startswith("load_average_"):
            # These would come from node_load_data in the old integration
            # For now, return 0 as the new integration doesn't fetch this data yet
            return 0.0
        elif self._raw_attr_name == "cpu_frequency_mhz":
            return 0
        elif self._raw_attr_name == "cpu_cores":
            return 0
        elif self._raw_attr_name == "cpu_sockets":
            return 0
        elif self._raw_attr_name == "cpu_total_logical":
            return 0
        elif self._raw_attr_name == "cpu_model":
            return "Unknown"
        return None
    
    def _get_vm_value(self, vm_data: dict[str, Any]) -> Any:
        """Get VM value - exact same logic as old integration."""
        if self._raw_attr_name == "cpu_usage_percent":
            return float(vm_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            return vm_data.get("mem", 0)
        elif self._raw_attr_name == "memory_total_bytes":
            return vm_data.get("maxmem", 0)
        elif self._raw_attr_name == "disk_used_bytes":
            return vm_data.get("disk", 0)
        elif self._raw_attr_name == "disk_total_bytes":
            return vm_data.get("maxdisk", 0)
        elif self._raw_attr_name == "uptime_seconds":
            return vm_data.get("uptime", 0)
        elif self._raw_attr_name == "node_name":
            return vm_data.get("node", "unknown")
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(vm_data.get("mem", 0))
            maxmem = float(vm_data.get("maxmem", 1))
            return (mem / maxmem * 100) if maxmem > 0 else 0.0
        return None
    
    def _get_container_value(self, container_data: dict[str, Any]) -> Any:
        """Get container value - exact same logic as old integration."""
        if self._raw_attr_name == "cpu_usage_percent":
            return float(container_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            return container_data.get("mem", 0)
        elif self._raw_attr_name == "memory_total_bytes":
            return container_data.get("maxmem", 0)
        elif self._raw_attr_name == "disk_used_bytes":
            return container_data.get("disk", 0)
        elif self._raw_attr_name == "disk_total_bytes":
            return container_data.get("maxdisk", 0)
        elif self._raw_attr_name == "uptime_seconds":
            return container_data.get("uptime", 0)
        elif self._raw_attr_name == "node_name":
            return container_data.get("node", "unknown")
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(container_data.get("mem", 0))
            maxmem = float(container_data.get("maxmem", 1))
            return (mem / maxmem * 100) if maxmem > 0 else 0.0
        return None

