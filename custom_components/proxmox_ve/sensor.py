"""Platform for sensor integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfTime,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.device_registry import DeviceInfo
from proxmoxer.core import AuthenticationError
from requests.exceptions import ConnectionError

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL
from .api import ProxmoxClient

_LOGGER = logging.getLogger(__name__)

# Add a mapping for proper capitalization of known abbreviations
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
    # Split by underscores, capitalize each part, but use abbreviation map if present
    parts = attr_name.split('_')
    pretty = []
    for part in parts:
        lower = part.lower()
        pretty.append(_ABBREVIATION_MAP.get(lower, part.capitalize()))
    return ' '.join(pretty)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            _LOGGER.debug("Fetching Proxmox VE data...")
            _LOGGER.debug("Using client with host: %s, username: %s", client.host, client.username)
            
            nodes = await hass.async_add_executor_job(client.proxmox.nodes.get)
            
            # Get VMs and containers from all nodes
            all_vms = []
            all_containers = []
            node_load_data = {}  # Store load data for each node
            
            for node in nodes:
                try:
                    # Get system load data for the node
                    try:
                        _LOGGER.debug("Attempting to fetch load data for node %s", node["node"])
                        
                        # Try multiple approaches to get load data
                        load_data = None
                        
                        # Approach 1: Try RRD data with different timeframes
                        for timeframe in ["hour", "day", "week"]:
                            try:
                                load_data = await hass.async_add_executor_job(
                                    client.proxmox.nodes(node["node"]).rrddata.get,
                                    timeframe=timeframe
                                )
                                if load_data:
                                    _LOGGER.debug("Got RRD data with timeframe '%s' for node %s", timeframe, node["node"])
                                    break
                            except Exception as e:
                                _LOGGER.debug("Failed to get RRD data with timeframe '%s' for node %s: %s", timeframe, node["node"], e)
                        
                        # Approach 2: Try to get load data from node status
                        if not load_data:
                            try:
                                status_data = await hass.async_add_executor_job(
                                    client.proxmox.nodes(node["node"]).status.get
                                )
                                _LOGGER.debug("Status data for node %s: %s", node["node"], status_data)
                                
                                # Check if load average is in status data
                                if status_data and "loadavg" in status_data:
                                    load_data = [{"loadavg": status_data["loadavg"]}]
                                    _LOGGER.debug("Found load data in status for node %s: %s", node["node"], load_data)
                            except Exception as e:
                                _LOGGER.debug("Failed to get status data for node %s: %s", node["node"], e)
                        
                        _LOGGER.debug("Final load data for node %s: %s", node["node"], load_data)
                        
                        if load_data:
                            # Get the most recent data point
                            latest_load = load_data[-1] if load_data else {}
                            _LOGGER.debug("Latest load data for node %s: %s", node["node"], latest_load)
                            
                            # Check if loadavg field exists and has the expected format
                            loadavg = latest_load.get("loadavg")
                            _LOGGER.debug("Load average data for node %s: %s", node["node"], loadavg)
                            
                            if loadavg and isinstance(loadavg, list) and len(loadavg) >= 3:
                                # Convert loadavg values to numbers to ensure they're not strings
                                try:
                                    loadavg_1min = float(loadavg[0]) if loadavg[0] is not None else 0.0
                                    loadavg_5min = float(loadavg[1]) if loadavg[1] is not None else 0.0
                                    loadavg_15min = float(loadavg[2]) if loadavg[2] is not None else 0.0
                                except (ValueError, TypeError):
                                    loadavg_1min = 0.0
                                    loadavg_5min = 0.0
                                    loadavg_15min = 0.0
                                
                                node_load_data[node["node"]] = {
                                    "loadavg_1min": loadavg_1min,
                                    "loadavg_5min": loadavg_5min,
                                    "loadavg_15min": loadavg_15min,
                                }
                                _LOGGER.debug("Successfully parsed load data for node %s: %s", node["node"], node_load_data[node["node"]])
                            else:
                                _LOGGER.warning("Load average data for node %s is not in expected format: %s", node["node"], loadavg)
                                node_load_data[node["node"]] = {"loadavg_1min": 0.0, "loadavg_5min": 0.0, "loadavg_15min": 0.0}
                        else:
                            _LOGGER.warning("No load data returned for node %s", node["node"])
                            node_load_data[node["node"]] = {"loadavg_1min": 0.0, "loadavg_5min": 0.0, "loadavg_15min": 0.0}
                        
                    except Exception as e:
                        _LOGGER.warning("Failed to fetch load data from node %s: %s", node["node"], e)
                        _LOGGER.debug("Exception details: %s", str(e))
                        node_load_data[node["node"]] = {"loadavg_1min": 0.0, "loadavg_5min": 0.0, "loadavg_15min": 0.0}
                    
                    # Try to get additional system information (CPU data)
                    try:
                        _LOGGER.debug("=== STARTING CPU DATA COLLECTION FOR NODE %s ===", node["node"])
                        _LOGGER.debug("Attempting to fetch system info for node %s", node["node"])
                        
                        # Try multiple approaches to get CPU information
                        cpu_frequency = 0
                        cpu_cores = 0
                        cpu_sockets = 0
                        cpu_total = 0
                        cpu_model = "Unknown"
                        
                        _LOGGER.debug("Initial CPU values: freq=%s, cores=%s, sockets=%s, total=%s, model=%s", 
                                     cpu_frequency, cpu_cores, cpu_sockets, cpu_total, cpu_model)
                        
                        # Approach 1: Try to get CPU info from status endpoint (primary for older Proxmox VE versions)
                        try:
                            _LOGGER.debug("Trying status endpoint for node %s", node["node"])
                            status_info = await hass.async_add_executor_job(
                                client.proxmox.nodes(node["node"]).status.get
                            )
                            _LOGGER.debug("Status info for node %s: %s", node["node"], status_info)
                            
                            if status_info and "cpuinfo" in status_info:
                                cpuinfo = status_info["cpuinfo"]
                                _LOGGER.debug("CPU info from status for node %s: %s", node["node"], cpuinfo)
                                
                                # Extract CPU information from cpuinfo
                                cpu_model = cpuinfo.get("model", "Unknown")
                                # Convert frequency to float, then to int if it's a number
                                freq_raw = cpuinfo.get("mhz", 0)
                                try:
                                    cpu_frequency = int(float(freq_raw)) if freq_raw else 0
                                except (ValueError, TypeError):
                                    cpu_frequency = 0
                                # Ensure CPU counts are integers
                                try:
                                    cpu_cores = int(cpuinfo.get("cores", 0)) if cpuinfo.get("cores") else 0
                                except (ValueError, TypeError):
                                    cpu_cores = 0
                                try:
                                    cpu_sockets = int(cpuinfo.get("sockets", 0)) if cpuinfo.get("sockets") else 0
                                except (ValueError, TypeError):
                                    cpu_sockets = 0
                                try:
                                    cpu_total = int(cpuinfo.get("cpus", 0)) if cpuinfo.get("cpus") else 0  # Total logical processors
                                except (ValueError, TypeError):
                                    cpu_total = 0
                                _LOGGER.debug("Parsed CPU info from status: model=%s, freq=%s, cores=%s, sockets=%s, total=%s", 
                                             cpu_model, cpu_frequency, cpu_cores, cpu_sockets, cpu_total)
                        except Exception as e:
                            _LOGGER.debug("Failed to get CPU info from status for node %s: %s", node["node"], e)
                        
                        # Approach 2: Try to get CPU info from hardware endpoint (fallback)
                        if cpu_model == "Unknown" or cpu_frequency == 0:
                            try:
                                _LOGGER.debug("Trying hardware endpoint for node %s", node["node"])
                                hardware_info = await hass.async_add_executor_job(
                                    client.proxmox.nodes(node["node"]).hardware.get
                                )
                                _LOGGER.debug("Hardware info for node %s: %s", node["node"], hardware_info)
                                
                                if hardware_info:
                                    # Look for CPU information in hardware info
                                    for item in hardware_info:
                                        if item.get("type") == "cpu":
                                            cpu_data = item.get("data", {})
                                            cpu_model = cpu_data.get("model name", cpu_model)
                                            freq_raw = cpu_data.get("cpu MHz", cpu_frequency)
                                            try:
                                                cpu_frequency = int(float(freq_raw)) if freq_raw else cpu_frequency
                                            except (ValueError, TypeError):
                                                pass
                                            # Ensure CPU counts are integers
                                            try:
                                                cpu_cores = int(cpu_data.get("cpu cores", cpu_cores)) if cpu_data.get("cpu cores") else cpu_cores
                                            except (ValueError, TypeError):
                                                pass
                                            try:
                                                cpu_sockets = int(cpu_data.get("cpu sockets", cpu_sockets)) if cpu_data.get("cpu sockets") else cpu_sockets
                                            except (ValueError, TypeError):
                                                pass
                                            try:
                                                cpu_total = int(cpu_data.get("cpu total", cpu_total)) if cpu_data.get("cpu total") else cpu_total
                                            except (ValueError, TypeError):
                                                pass
                                            _LOGGER.debug("Parsed CPU info from hardware: model=%s, freq=%s, cores=%s, sockets=%s, total=%s", 
                                                         cpu_model, cpu_frequency, cpu_cores, cpu_sockets, cpu_total)
                                            break
                            except Exception as e:
                                _LOGGER.debug("Failed to get hardware info for node %s: %s", node["node"], e)
                        
                        # Update the node load data with CPU information
                        node_load_data[node["node"]].update({
                            "cpu_frequency": cpu_frequency,
                            "cpu_cores": cpu_cores,
                            "cpu_sockets": cpu_sockets,
                            "cpu_total": cpu_total,
                            "cpu_model": cpu_model,
                        })
                        _LOGGER.debug("Final CPU data for node %s: freq=%s, cores=%s, sockets=%s, total=%s, model=%s", 
                                     node["node"], cpu_frequency, cpu_cores, cpu_sockets, cpu_total, cpu_model)
                        _LOGGER.debug("Updated node_load_data for %s: %s", node["node"], node_load_data[node["node"]])
                        _LOGGER.debug("=== COMPLETED CPU DATA COLLECTION FOR NODE %s ===", node["node"])
                        
                    except Exception as e:
                        _LOGGER.debug("Failed to fetch additional system info from node %s: %s", node["node"], e)
                        _LOGGER.debug("Exception type: %s", type(e).__name__)
                        _LOGGER.debug("Exception details: %s", str(e))
                        # Set default values if we couldn't get CPU info
                        node_load_data[node["node"]].update({
                            "cpu_frequency": 0,
                            "cpu_cores": 0,
                            "cpu_sockets": 0,
                            "cpu_total": 0,
                            "cpu_model": "Unknown",
                        })
                        _LOGGER.debug("Set default CPU values for node %s due to error", node["node"])
                    
                    # Get VMs (QEMU)
                    node_vms = await hass.async_add_executor_job(
                        client.proxmox.nodes(node["node"]).qemu.get
                    )
                    # Add node information to each VM
                    for vm in node_vms:
                        vm["node"] = node["node"]
                        vm["type"] = "VM"
                    all_vms.extend(node_vms)
                    
                    # Get containers (LXC)
                    try:
                        node_containers = await hass.async_add_executor_job(
                            client.proxmox.nodes(node["node"]).lxc.get
                        )
                        _LOGGER.debug("Fetched %s containers from node %s", len(node_containers), node["node"])
                        if node_containers:
                            _LOGGER.debug("First container data: %s", node_containers[0])
                        # Add node information to each container
                        for container in node_containers:
                            container["node"] = node["node"]
                            container["type"] = "Container"
                        all_containers.extend(node_containers)
                    except Exception as e:
                        _LOGGER.warning("Failed to fetch LXC containers from node %s: %s", node["node"], e)
                        _LOGGER.debug("This might be due to missing permissions or no LXC containers on this node")
                    
                except Exception as e:
                    _LOGGER.warning("Failed to fetch data from node %s: %s", node["node"], e)
            
            _LOGGER.debug("Proxmox VE data fetched - Nodes: %s, VMs: %s, Containers: %s", 
                         len(nodes), len(all_vms), len(all_containers))
            
            # Debug: Show container details if any found
            if all_containers:
                _LOGGER.debug("Container details:")
                for container in all_containers:
                    container_id = container.get("id") or container.get("vmid")
                    _LOGGER.debug("  - %s (ID: %s, Status: %s)", 
                                 container.get("name", "unknown"), 
                                 container_id, 
                                 container.get("status", "unknown"))
            
            # Debug: Show load data summary
            _LOGGER.debug("Load data collected for nodes: %s", list(node_load_data.keys()))
            for node_name, load_info in node_load_data.items():
                _LOGGER.debug("  Node %s load data: %s", node_name, load_info)
            
            result_data = {"nodes": nodes, "vms": all_vms, "containers": all_containers, "node_load_data": node_load_data}
            _LOGGER.debug("Coordinator update completed successfully with %s nodes, %s VMs, %s containers", 
                         len(nodes), len(all_vms), len(all_containers))
            return result_data
        except AuthenticationError as error:
            _LOGGER.error("Authentication error fetching Proxmox VE data: %s", error)
            _LOGGER.error("Please check your username and password/token credentials")
            _LOGGER.error("Username should be in format 'username@realm' (e.g., 'root@pam')")
            raise UpdateFailed(f"Authentication failed: {error}") from error
        except ConnectionError as error:
            _LOGGER.error("Connection error fetching Proxmox VE data: %s", error)
            _LOGGER.error("Please check your host address and network connectivity")
            raise UpdateFailed(f"Connection failed: {error}") from error
        except Exception as error:
            _LOGGER.error("Unexpected error fetching Proxmox VE data: %s", error)
            _LOGGER.error("Error type: %s", type(error).__name__)
            raise UpdateFailed(f"Unexpected error: {error}") from error

    # Check if coordinator already exists
    coordinator_key = f"{entry.entry_id}_coordinator"
    existing_coordinator = hass.data[DOMAIN].get(coordinator_key)
    
    if existing_coordinator:
        # If coordinator exists, use it (this happens during initial setup)
        _LOGGER.debug("Using existing coordinator with interval: %s seconds", existing_coordinator.update_interval.total_seconds())
        coordinator = existing_coordinator
    else:
        # Create new coordinator
        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="proxmox",
            update_method=async_update_data,
            update_interval=timedelta(seconds=entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))),
        )
        # Store coordinator in hass data
        hass.data[DOMAIN][coordinator_key] = coordinator
        _LOGGER.debug("Created new coordinator with interval: %s seconds", coordinator.update_interval.total_seconds())

    # Wait for the first data fetch only if this is a new coordinator
    if not existing_coordinator:
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.debug("Initial data fetch completed successfully")
        except Exception as e:
            _LOGGER.error("Failed to fetch initial data: %s", e)
            # Still try to create entities with whatever data we have

    # Create entities based on available data
    entities = []
    _LOGGER.debug("Coordinator data keys: %s", list(coordinator.data.keys()) if coordinator.data else "None")
    try:
        if coordinator.data and "nodes" in coordinator.data:
            _LOGGER.debug("Creating node attribute sensors")
            for node in coordinator.data["nodes"]:
                node_name = node.get("node", "unknown")
                node_id = node_name
                host = entry.data["host"]
                # Device info for node
                node_device_info = DeviceInfo(
                    identifiers={(DOMAIN, f"node_{host}_{node_name}")},
                    name=f"Proxmox VE Node {node_name}",
                    manufacturer="Proxmox",
                    model="Node",
                    configuration_url=f"https://{host}/"
                )
                # Node attributes
                node_attrs = {
                    "cpu_usage_percent": float(node.get("cpu", 0)) * 100,
                    "memory_used_bytes": node.get("mem", 0),
                    "memory_total_bytes": node.get("maxmem", 0),
                    "disk_used_bytes": node.get("disk", 0),
                    "disk_total_bytes": node.get("maxdisk", 0),
                    "uptime_seconds": node.get("uptime", 0),
                    "memory_usage_percent": (float(node.get("mem", 0)) / float(node.get("maxmem", 1)) * 100) if node.get("maxmem", 0) else 0.0,
                }
                # Add load/cpu info if available
                node_load_data = coordinator.data.get("node_load_data", {}).get(node_name, {})
                node_attrs.update({
                    "load_average_1min": float(node_load_data.get("loadavg_1min", 0)),
                    "load_average_5min": float(node_load_data.get("loadavg_5min", 0)),
                    "load_average_15min": float(node_load_data.get("loadavg_15min", 0)),
                    "cpu_frequency_mhz": int(node_load_data.get("cpu_frequency", 0)),
                    "cpu_cores": int(node_load_data.get("cpu_cores", 0)),
                    "cpu_sockets": int(node_load_data.get("cpu_sockets", 0)),
                    "cpu_total_logical": int(node_load_data.get("cpu_total", 0)),
                    "cpu_model": node_load_data.get("cpu_model", "Unknown"),
                })
                for attr, value in node_attrs.items():
                    entities.append(ProxmoxBaseAttributeSensor(
                        coordinator, entry.entry_id, host, "Node", node_id, node_name, attr, value, node_device_info
                    ))
        if coordinator.data and "vms" in coordinator.data:
            _LOGGER.debug("Creating VM attribute sensors")
            for vm in coordinator.data["vms"]:
                vmid = vm["vmid"]
                vm_name = vm.get("name", f"VM {vmid}")
                node_name = vm.get("node", "unknown")
                host = entry.data["host"]
                # Device info for VM
                vm_device_info = DeviceInfo(
                    identifiers={(DOMAIN, f"vm_{host}_{node_name}_{vmid}")},
                    name=f"Proxmox VE VM {vm_name}",
                    manufacturer="Proxmox",
                    model="VM",
                    via_device=(DOMAIN, f"node_{host}_{node_name}"),
                    configuration_url=f"https://{host}/"
                )
                vm_attrs = {
                    "cpu_usage_percent": float(vm.get("cpu", 0)) * 100,
                    "memory_used_bytes": vm.get("mem", 0),
                    "memory_total_bytes": vm.get("maxmem", 0),
                    "disk_used_bytes": vm.get("disk", 0),
                    "disk_total_bytes": vm.get("maxdisk", 0),
                    "uptime_seconds": vm.get("uptime", 0),
                    "node_name": node_name,
                    "memory_usage_percent": (float(vm.get("mem", 0)) / float(vm.get("maxmem", 1)) * 100) if vm.get("maxmem", 0) else 0.0,
                }
                for attr, value in vm_attrs.items():
                    entities.append(ProxmoxBaseAttributeSensor(
                        coordinator, entry.entry_id, host, "VM", vmid, vm_name, attr, value, vm_device_info
                    ))
        if coordinator.data and "containers" in coordinator.data:
            _LOGGER.debug("Creating container attribute sensors")
            for container in coordinator.data["containers"]:
                container_id = container.get("id") or container.get("vmid")
                container_name = container.get("name", f"Container {container_id}")
                node_name = container.get("node", "unknown")
                host = entry.data["host"]
                # Device info for container
                container_device_info = DeviceInfo(
                    identifiers={(DOMAIN, f"container_{host}_{node_name}_{container_id}")},
                    name=f"Proxmox VE Container {container_name}",
                    manufacturer="Proxmox",
                    model="Container",
                    via_device=(DOMAIN, f"node_{host}_{node_name}"),
                    configuration_url=f"https://{host}/"
                )
                container_attrs = {
                    "cpu_usage_percent": float(container.get("cpu", 0)) * 100,
                    "memory_used_bytes": container.get("mem", 0),
                    "memory_total_bytes": container.get("maxmem", 0),
                    "disk_used_bytes": container.get("disk", 0),
                    "disk_total_bytes": container.get("maxdisk", 0),
                    "uptime_seconds": container.get("uptime", 0),
                    "node_name": node_name,
                    "memory_usage_percent": (float(container.get("mem", 0)) / float(container.get("maxmem", 1)) * 100) if container.get("maxmem", 0) else 0.0,
                }
                for attr, value in container_attrs.items():
                    entities.append(ProxmoxBaseAttributeSensor(
                        coordinator, entry.entry_id, host, "Container", container_id, container_name, attr, value, container_device_info
                    ))
    except Exception as e:
        _LOGGER.error("Error creating attribute entities: %s", e)

    if entities:
        _LOGGER.info("Creating %s Proxmox VE entities", len(entities))
        try:
            async_add_entities(entities)
            _LOGGER.info("Successfully added %s Proxmox VE entities", len(entities))
        except Exception as e:
            _LOGGER.error("Error adding entities: %s", e)
    else:
        _LOGGER.warning("No Proxmox VE entities found to create - this might indicate a connection issue or no resources available")
        _LOGGER.debug("Coordinator data: %s", coordinator.data)
        
        # If no entities were created, log more details for debugging
        if coordinator.data:
            _LOGGER.debug("Available data summary:")
            if "nodes" in coordinator.data:
                _LOGGER.debug("  Nodes: %s", len(coordinator.data["nodes"]))
            if "vms" in coordinator.data:
                _LOGGER.debug("  VMs: %s", len(coordinator.data["vms"]))
            if "containers" in coordinator.data:
                _LOGGER.debug("  Containers: %s", len(coordinator.data["containers"]))
        else:
            _LOGGER.error("No data available from coordinator - check API connection")


class ProxmoxBaseAttributeSensor(CoordinatorEntity, SensorEntity):
    """A generic sensor for a Proxmox VE device attribute."""
    def __init__(self, coordinator, entry_id, host, device_type, device_id, device_name, attr_name, attr_value, device_info):
        super().__init__(coordinator)
        # Prettify device_type and attr_name
        pretty_device_type = _ABBREVIATION_MAP.get(device_type.lower(), device_type)
        pretty_attr_name = _prettify_attr_name(attr_name)
        self._attr_name = f"Proxmox VE {pretty_device_type} {device_name} {pretty_attr_name}"
        self._attr_unique_id = f"proxmox_ve_{device_type.lower()}_{device_id}_{attr_name}_{entry_id}"
        self._attr_native_value = attr_value
        self._attr_device_info = device_info
        self._raw_attr_name = attr_name
        self._entry_id = entry_id
        self._host = host
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name

        # Set state_class, device_class, unit_of_measurement, and icon
        self._attr_state_class = None
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_icon = None

        if "percent" in attr_name:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_device_class = SensorDeviceClass.POWER_FACTOR
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:percent"
        elif "memory" in attr_name and "bytes" in attr_name:
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:memory"
        elif "disk" in attr_name and "bytes" in attr_name:
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:harddisk"
        elif "uptime" in attr_name:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:timer-sand"
        elif "frequency" in attr_name:
            self._attr_device_class = SensorDeviceClass.FREQUENCY
            self._attr_native_unit_of_measurement = UnitOfFrequency.MEGAHERTZ
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:chip"
        elif "load_average" in attr_name:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:chip"
        elif attr_name in ("cpu_cores", "cpu_sockets", "cpu_total_logical"):
            self._attr_icon = "mdi:chip"

    @property
    def native_value(self):
        # Just return the cached value
        return self._attr_native_value

    def handle_coordinator_update(self) -> None:
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available for sensor %s", self._attr_name)
            return

        _LOGGER.debug("Updating sensor %s with new coordinator data", self._attr_name)

        # Find the relevant data based on device type
        if self._device_type == "Node":
            for node in self.coordinator.data.get("nodes", []):
                if node.get("node") == self._device_id:
                    self._update_node_value(node)
                    _LOGGER.debug("Updated node sensor %s with value: %s", self._attr_name, self._attr_native_value)
                    break
        elif self._device_type == "VM":
            for vm in self.coordinator.data.get("vms", []):
                if vm.get("vmid") == self._device_id:
                    self._update_vm_value(vm)
                    _LOGGER.debug("Updated VM sensor %s with value: %s", self._attr_name, self._attr_native_value)
                    break
        elif self._device_type == "Container":
            for container in self.coordinator.data.get("containers", []):
                container_id = container.get("id") or container.get("vmid")
                if container_id == self._device_id:
                    self._update_container_value(container)
                    _LOGGER.debug("Updated container sensor %s with value: %s", self._attr_name, self._attr_native_value)
                    break

        # Notify Home Assistant of the new state
        super().handle_coordinator_update()

    def _update_node_value(self, node_data):
        """Update sensor value from node data."""
        if self._raw_attr_name == "cpu_usage_percent":
            self._attr_native_value = float(node_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            self._attr_native_value = node_data.get("mem", 0)
        elif self._raw_attr_name == "memory_total_bytes":
            self._attr_native_value = node_data.get("maxmem", 0)
        elif self._raw_attr_name == "disk_used_bytes":
            self._attr_native_value = node_data.get("disk", 0)
        elif self._raw_attr_name == "disk_total_bytes":
            self._attr_native_value = node_data.get("maxdisk", 0)
        elif self._raw_attr_name == "uptime_seconds":
            self._attr_native_value = node_data.get("uptime", 0)
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(node_data.get("mem", 0))
            maxmem = float(node_data.get("maxmem", 1))
            self._attr_native_value = (mem / maxmem * 100) if maxmem > 0 else 0.0
        elif self._raw_attr_name.startswith("load_average_"):
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            if self._raw_attr_name == "load_average_1min":
                self._attr_native_value = float(node_load_data.get("loadavg_1min", 0))
            elif self._raw_attr_name == "load_average_5min":
                self._attr_native_value = float(node_load_data.get("loadavg_5min", 0))
            elif self._raw_attr_name == "load_average_15min":
                self._attr_native_value = float(node_load_data.get("loadavg_15min", 0))
        elif self._raw_attr_name == "cpu_frequency_mhz":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            self._attr_native_value = int(node_load_data.get("cpu_frequency", 0))
        elif self._raw_attr_name == "cpu_cores":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            self._attr_native_value = int(node_load_data.get("cpu_cores", 0))
        elif self._raw_attr_name == "cpu_sockets":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            self._attr_native_value = int(node_load_data.get("cpu_sockets", 0))
        elif self._raw_attr_name == "cpu_total_logical":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            self._attr_native_value = int(node_load_data.get("cpu_total", 0))
        elif self._raw_attr_name == "cpu_model":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            self._attr_native_value = node_load_data.get("cpu_model", "Unknown")

    def _update_vm_value(self, vm_data):
        """Update sensor value from VM data."""
        if self._raw_attr_name == "cpu_usage_percent":
            self._attr_native_value = float(vm_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            self._attr_native_value = vm_data.get("mem", 0)
        elif self._raw_attr_name == "memory_total_bytes":
            self._attr_native_value = vm_data.get("maxmem", 0)
        elif self._raw_attr_name == "disk_used_bytes":
            self._attr_native_value = vm_data.get("disk", 0)
        elif self._raw_attr_name == "disk_total_bytes":
            self._attr_native_value = vm_data.get("maxdisk", 0)
        elif self._raw_attr_name == "uptime_seconds":
            self._attr_native_value = vm_data.get("uptime", 0)
        elif self._raw_attr_name == "node_name":
            self._attr_native_value = vm_data.get("node", "unknown")
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(vm_data.get("mem", 0))
            maxmem = float(vm_data.get("maxmem", 1))
            self._attr_native_value = (mem / maxmem * 100) if maxmem > 0 else 0.0

    def _update_container_value(self, container_data):
        """Update sensor value from container data."""
        if self._raw_attr_name == "cpu_usage_percent":
            self._attr_native_value = float(container_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            self._attr_native_value = container_data.get("mem", 0)
        elif self._raw_attr_name == "memory_total_bytes":
            self._attr_native_value = container_data.get("maxmem", 0)
        elif self._raw_attr_name == "disk_used_bytes":
            self._attr_native_value = container_data.get("disk", 0)
        elif self._raw_attr_name == "disk_total_bytes":
            self._attr_native_value = container_data.get("maxdisk", 0)
        elif self._raw_attr_name == "uptime_seconds":
            self._attr_native_value = container_data.get("uptime", 0)
        elif self._raw_attr_name == "node_name":
            self._attr_native_value = container_data.get("node", "unknown")
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(container_data.get("mem", 0))
            maxmem = float(container_data.get("maxmem", 1))
            self._attr_native_value = (mem / maxmem * 100) if maxmem > 0 else 0.0
