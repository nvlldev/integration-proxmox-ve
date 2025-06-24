"""Entity descriptions for Proxmox VE integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTime, UnitOfFrequency

from .models import ProxmoxResource


@dataclass
class ProxmoxSensorEntityDescription(SensorEntityDescription):
    """Describes Proxmox sensor entity."""

    value_fn: Callable[[ProxmoxResource], float | int | str | None] | None = None
    available_fn: Callable[[ProxmoxResource], bool] | None = None


@dataclass
class ProxmoxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Proxmox binary sensor entity."""

    value_fn: Callable[[ProxmoxResource], bool | None] | None = None
    available_fn: Callable[[ProxmoxResource], bool] | None = None


# Node sensor descriptions
NODE_SENSORS: tuple[ProxmoxSensorEntityDescription, ...] = (
    ProxmoxSensorEntityDescription(
        key="cpu_usage_percent",
        name="CPU Usage",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:cpu-64-bit",
        value_fn=lambda resource: resource.cpu_usage_percent,
    ),
    ProxmoxSensorEntityDescription(
        key="memory_used_bytes",
        name="Memory Used",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:memory",
        value_fn=lambda resource: resource.memory_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="memory_total_bytes",
        name="Memory Total",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:memory",
        value_fn=lambda resource: resource.memory_max_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="memory_usage_percent",
        name="Memory Usage",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:memory",
        value_fn=lambda resource: resource.memory_usage_percent,
    ),
    ProxmoxSensorEntityDescription(
        key="disk_used_bytes",
        name="Disk Used",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:harddisk",
        value_fn=lambda resource: resource.disk_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="disk_total_bytes",
        name="Disk Total",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:harddisk",
        value_fn=lambda resource: resource.disk_max_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="disk_usage_percent",
        name="Disk Usage",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:harddisk",
        value_fn=lambda resource: resource.disk_usage_percent,
    ),
    ProxmoxSensorEntityDescription(
        key="disk_free_percent",
        name="Disk Free",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:harddisk",
        value_fn=lambda resource: resource.disk_free_percent,
    ),
    ProxmoxSensorEntityDescription(
        key="uptime_seconds",
        name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:timer-sand",
        value_fn=lambda resource: resource.uptime_seconds,
    ),
)

# Additional node-specific sensors
NODE_SPECIFIC_SENSORS: tuple[ProxmoxSensorEntityDescription, ...] = (
    ProxmoxSensorEntityDescription(
        key="load_average_1min",
        name="Load Average 1min",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "load_average_1min", 0.0),
    ),
    ProxmoxSensorEntityDescription(
        key="load_average_5min",
        name="Load Average 5min",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "load_average_5min", 0.0),
    ),
    ProxmoxSensorEntityDescription(
        key="load_average_15min",
        name="Load Average 15min",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "load_average_15min", 0.0),
    ),
    ProxmoxSensorEntityDescription(
        key="cpu_frequency_mhz",
        name="CPU Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "cpu_frequency_mhz", 0),
    ),
    ProxmoxSensorEntityDescription(
        key="cpu_cores",
        name="CPU Cores",
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "cpu_cores", 0),
    ),
    ProxmoxSensorEntityDescription(
        key="cpu_sockets",
        name="CPU Sockets",
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "cpu_sockets", 0),
    ),
    ProxmoxSensorEntityDescription(
        key="cpu_total_logical",
        name="CPU Total Logical",
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "cpu_total_logical", 0),
    ),
    ProxmoxSensorEntityDescription(
        key="cpu_model",
        name="CPU Model",
        icon="mdi:chip",
        value_fn=lambda node: getattr(node, "cpu_model", "Unknown"),
    ),
)

# VM sensor descriptions (same base sensors without node-specific ones)
VM_SENSORS: tuple[ProxmoxSensorEntityDescription, ...] = NODE_SENSORS + (
    ProxmoxSensorEntityDescription(
        key="node_name",
        name="Node",
        icon="mdi:server",
        value_fn=lambda resource: resource.node,
    ),
)

# Container sensor descriptions (same as VM sensors)
CONTAINER_SENSORS: tuple[ProxmoxSensorEntityDescription, ...] = VM_SENSORS

# Storage sensor descriptions
STORAGE_SENSORS: tuple[ProxmoxSensorEntityDescription, ...] = (
    ProxmoxSensorEntityDescription(
        key="storage_used_bytes",
        name="Storage Used",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:database",
        value_fn=lambda storage: storage.used_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="storage_total_bytes",
        name="Storage Total",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:database",
        value_fn=lambda storage: storage.total_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="storage_available_bytes",
        name="Storage Available",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        icon="mdi:database",
        value_fn=lambda storage: storage.available_bytes,
    ),
    ProxmoxSensorEntityDescription(
        key="storage_usage_percent",
        name="Storage Usage",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:database",
        value_fn=lambda storage: storage.usage_percent,
    ),
    ProxmoxSensorEntityDescription(
        key="storage_free_percent",
        name="Storage Free",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:database",
        value_fn=lambda storage: storage.free_percent,
    ),
    ProxmoxSensorEntityDescription(
        key="storage_type",
        name="Storage Type",
        icon="mdi:database-settings",
        value_fn=lambda storage: storage.type,
    ),
    ProxmoxSensorEntityDescription(
        key="storage_content",
        name="Storage Content Types",
        icon="mdi:database-settings",
        value_fn=lambda storage: storage.content,
    ),
)

# Node binary sensor descriptions
NODE_BINARY_SENSORS: tuple[ProxmoxBinarySensorEntityDescription, ...] = (
    ProxmoxBinarySensorEntityDescription(
        key="node_available",
        name="Node Available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:server-network",
        value_fn=lambda node: node.available,
    ),
)

# VM binary sensor descriptions
VM_BINARY_SENSORS: tuple[ProxmoxBinarySensorEntityDescription, ...] = (
    ProxmoxBinarySensorEntityDescription(
        key="vm_running",
        name="VM Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:desktop-tower",
        value_fn=lambda vm: vm.status == "running",
    ),
    ProxmoxBinarySensorEntityDescription(
        key="vm_available",
        name="VM Available",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:desktop-tower-monitor",
        value_fn=lambda vm: vm.status is not None and vm.status != "unknown",
    ),
)

# Container binary sensor descriptions
CONTAINER_BINARY_SENSORS: tuple[ProxmoxBinarySensorEntityDescription, ...] = (
    ProxmoxBinarySensorEntityDescription(
        key="container_running",
        name="Container Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:package-variant",
        value_fn=lambda container: container.status == "running",
    ),
    ProxmoxBinarySensorEntityDescription(
        key="container_available",
        name="Container Available",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:package-variant-closed",
        value_fn=lambda container: container.status is not None and container.status != "unknown",
    ),
)

# Storage binary sensor descriptions
STORAGE_BINARY_SENSORS: tuple[ProxmoxBinarySensorEntityDescription, ...] = (
    ProxmoxBinarySensorEntityDescription(
        key="storage_enabled",
        name="Storage Enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:database-check",
        value_fn=lambda storage: storage.enabled,
    ),
    ProxmoxBinarySensorEntityDescription(
        key="storage_shared",
        name="Storage Shared",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:database-sync",
        value_fn=lambda storage: storage.shared,
    ),
)