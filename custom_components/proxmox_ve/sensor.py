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
        _LOGGER.debug("=== COORDINATOR UPDATE DATA FUNCTION CALLED ===")
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
                                    lambda tf=timeframe: client.proxmox.nodes(node["node"]).rrddata.get(timeframe=tf)
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
            _LOGGER.debug("=== RETURNING DATA TO COORDINATOR ===")
            _LOGGER.debug("Sample node data: %s", nodes[0] if nodes else "No nodes")
            _LOGGER.debug("Sample VM data: %s", all_vms[0] if all_vms else "No VMs")
            _LOGGER.debug("=== COORDINATOR UPDATE DATA FUNCTION COMPLETED ===")
            
            # Workaround: Manually notify entities after data update
            # This is needed because the Home Assistant DataUpdateCoordinator is not properly notifying entities
            coordinator_key = f"{entry.entry_id}_coordinator"
            coordinator = hass.data[DOMAIN].get(coordinator_key)
            if coordinator and hasattr(coordinator, '_listeners') and coordinator._listeners:
                _LOGGER.debug("Manually notifying %s entities after data update", len(coordinator._listeners))
                for i, listener in enumerate(coordinator._listeners):
                    try:
                        _LOGGER.debug("Manually notifying entity %s", i+1)
                        listener()
                        _LOGGER.debug("Successfully manually notified entity %s", i+1)
                    except Exception as e:
                        _LOGGER.error("Error manually notifying entity %s: %s", i+1, e)
            
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
        update_interval_seconds = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        _LOGGER.debug("Creating new coordinator with update interval: %s seconds", update_interval_seconds)
        
        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="proxmox",
            update_method=async_update_data,
            update_interval=timedelta(seconds=update_interval_seconds),
        )
        # Store coordinator in hass data
        hass.data[DOMAIN][coordinator_key] = coordinator
        _LOGGER.debug("Created new coordinator with interval: %s seconds", coordinator.update_interval.total_seconds())
        _LOGGER.debug("Coordinator name: %s", coordinator.name)
        _LOGGER.debug("Coordinator update method: %s", coordinator.update_method.__name__)
        
        # Verify coordinator configuration
        if coordinator.update_interval.total_seconds() <= 0:
            _LOGGER.warning("Coordinator update interval is invalid: %s seconds", coordinator.update_interval.total_seconds())
        else:
            _LOGGER.debug("Coordinator update interval is valid: %s seconds", coordinator.update_interval.total_seconds())
        
        # Ensure coordinator is properly configured
        _LOGGER.debug("Coordinator configuration:")
        _LOGGER.debug("  - Name: %s", coordinator.name)
        _LOGGER.debug("  - Update interval: %s seconds", coordinator.update_interval.total_seconds())
        _LOGGER.debug("  - Update method: %s", coordinator.update_method.__name__)
        _LOGGER.debug("  - Has listeners: %s", hasattr(coordinator, '_listeners'))
        if hasattr(coordinator, '_listeners'):
            _LOGGER.debug("  - Listener count: %s", len(coordinator._listeners))

    # Wait for the first data fetch only if this is a new coordinator
    if not existing_coordinator:
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.debug("Initial data fetch completed successfully")
            _LOGGER.debug("Coordinator data after first refresh: %s", coordinator.data is not None)
            if coordinator.data:
                _LOGGER.debug("Coordinator data keys: %s", list(coordinator.data.keys()))
        except Exception as e:
            _LOGGER.error("Failed to fetch initial data: %s", e)
            # Still try to create entities with whatever data we have
    else:
        _LOGGER.debug("Using existing coordinator, skipping first refresh")

    # Create entities based on available data
    entities = []
    _LOGGER.debug("Coordinator data keys: %s", list(coordinator.data.keys()) if coordinator.data else "None")
    _LOGGER.debug("Coordinator update interval: %s seconds", coordinator.update_interval.total_seconds())
    _LOGGER.debug("Coordinator name: %s", coordinator.name)
    try:
        if coordinator.data and "nodes" in coordinator.data:
            _LOGGER.debug("Creating node attribute sensors")
            for node in coordinator.data["nodes"]:
                node_name = node.get("node", "unknown")
                node_id = node_name
                host = entry.data["host"]
                _LOGGER.debug("Creating node entity with ID: %s (type: %s)", node_id, type(node_id))
                
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
                    _LOGGER.debug("Creating node sensor: type=Node, id=%s, attr=%s, value=%s", node_id, attr, value)
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
                _LOGGER.debug("Creating VM entity with ID: %s (type: %s)", vmid, type(vmid))
                
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
                    _LOGGER.debug("Creating VM sensor: type=VM, id=%s, attr=%s, value=%s", vmid, attr, value)
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
                _LOGGER.debug("Creating container entity with ID: %s (type: %s)", container_id, type(container_id))
                
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
                    _LOGGER.debug("Creating container sensor: type=Container, id=%s, attr=%s, value=%s", container_id, attr, value)
                    entities.append(ProxmoxBaseAttributeSensor(
                        coordinator, entry.entry_id, host, "Container", container_id, container_name, attr, value, container_device_info
                    ))
    except Exception as e:
        _LOGGER.error("Error creating attribute entities: %s", e)

    if entities:
        _LOGGER.info("Creating %s Proxmox VE entities", len(entities))
        _LOGGER.debug("Entity details:")
        for i, entity in enumerate(entities[:5]):  # Log first 5 entities
            _LOGGER.debug("  Entity %d: %s (ID: %s, Type: %s)", i+1, entity._attr_name, entity._device_id, entity._device_type)
        if len(entities) > 5:
            _LOGGER.debug("  ... and %d more entities", len(entities) - 5)
        
        try:
            async_add_entities(entities)
            _LOGGER.info("Successfully added %s Proxmox VE entities", len(entities))
            _LOGGER.debug("Coordinator listeners count: %s", len(coordinator._listeners) if hasattr(coordinator, '_listeners') else 'Unknown')
            
            # Test coordinator update to see if entities are notified
            _LOGGER.debug("Testing coordinator update to verify entity notifications...")
            try:
                await coordinator.async_request_refresh()
                _LOGGER.debug("Coordinator refresh test completed")
                
                # Check if entities were notified
                if hasattr(coordinator, '_listeners'):
                    _LOGGER.debug("Coordinator has %s listeners after refresh", len(coordinator._listeners))
                else:
                    _LOGGER.warning("Coordinator does not have _listeners attribute")
                    
                # Wait a moment and test again to see if entities are updated
                import asyncio
                await asyncio.sleep(1)
                _LOGGER.debug("Testing second coordinator refresh...")
                await coordinator.async_request_refresh()
                _LOGGER.debug("Second coordinator refresh test completed")
                
                # Manually notify entities if they weren't notified automatically
                if hasattr(coordinator, '_listeners') and coordinator._listeners:
                    _LOGGER.debug("Manually notifying %s entities", len(coordinator._listeners))
                    for i, listener in enumerate(coordinator._listeners):
                        try:
                            _LOGGER.debug("Manually notifying entity %s", i+1)
                            listener()
                            _LOGGER.debug("Successfully manually notified entity %s", i+1)
                        except Exception as e:
                            _LOGGER.error("Error manually notifying entity %s: %s", i+1, e)
                
                # Store the coordinator for manual updates
                hass.data[DOMAIN][f"{entry.entry_id}_manual_update_coordinator"] = coordinator
                _LOGGER.debug("Stored coordinator for manual updates")
                
            except Exception as e:
                _LOGGER.error("Error testing coordinator refresh: %s", e)
                
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
        _LOGGER.debug("Creating sensor entity: %s (type: %s, id: %s, attr: %s)", device_name, device_type, device_id, attr_name)
        
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

        _LOGGER.debug("Sensor entity created: %s with initial value: %s", self._attr_name, self._attr_native_value)
        _LOGGER.debug("Coordinator listeners count after entity creation: %s", len(coordinator._listeners) if hasattr(coordinator, '_listeners') else 'Unknown')

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
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def native_value(self):
        # Just return the cached value
        _LOGGER.debug("Getting native_value for %s: %s", self._attr_name, self._attr_native_value)
        return self._attr_native_value

    async def async_handle_coordinator_update(self) -> None:
        _LOGGER.debug("=== COORDINATOR UPDATE TRIGGERED FOR %s ===", self._attr_name)
        _LOGGER.debug("Coordinator data available: %s", self.coordinator.data is not None)
        _LOGGER.debug("Coordinator data keys: %s", list(self.coordinator.data.keys()) if self.coordinator.data else "None")
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available for sensor %s", self._attr_name)
            return

        _LOGGER.debug("[ASYNC] Updating sensor %s with new coordinator data", self._attr_name)
        _LOGGER.debug("Device type: %s, Device ID: %s", self._device_type, self._device_id)
        _LOGGER.debug("Raw attr name: %s", self._raw_attr_name)

        # Find the relevant data based on device type
        if self._device_type == "Node":
            _LOGGER.debug("Looking for node with device ID: %s (type: %s)", self._device_id, type(self._device_id))
            _LOGGER.debug("Available nodes: %s", [(n.get("node"), type(n.get("node"))) for n in self.coordinator.data.get("nodes", [])])
            
            for node in self.coordinator.data.get("nodes", []):
                node_id = node.get("node")
                _LOGGER.debug("Comparing node ID: %s (type: %s) with device ID: %s (type: %s)", 
                             node_id, type(node_id), self._device_id, type(self._device_id))
                
                if node_id == self._device_id:
                    _LOGGER.debug("Found matching node: %s", node.get("node"))
                    old_value = self._attr_native_value
                    self._update_node_value(node)
                    _LOGGER.debug("[ASYNC] Updated node sensor %s: %s -> %s", self._attr_name, old_value, self._attr_native_value)
                    break
            else:
                _LOGGER.warning("No matching node found for device ID: %s", self._device_id)
                _LOGGER.debug("Available nodes: %s", [n.get("node") for n in self.coordinator.data.get("nodes", [])])
        elif self._device_type == "VM":
            _LOGGER.debug("Looking for VM with device ID: %s (type: %s)", self._device_id, type(self._device_id))
            _LOGGER.debug("Available VMs: %s", [(v.get("vmid"), type(v.get("vmid"))) for v in self.coordinator.data.get("vms", [])])
            
            for vm in self.coordinator.data.get("vms", []):
                vm_id = vm.get("vmid")
                _LOGGER.debug("Comparing VM ID: %s (type: %s) with device ID: %s (type: %s)", 
                             vm_id, type(vm_id), self._device_id, type(self._device_id))
                
                if vm_id == self._device_id:
                    _LOGGER.debug("Found matching VM: %s", vm.get("vmid"))
                    old_value = self._attr_native_value
                    self._update_vm_value(vm)
                    _LOGGER.debug("[ASYNC] Updated VM sensor %s: %s -> %s", self._attr_name, old_value, self._attr_native_value)
                    break
            else:
                _LOGGER.warning("No matching VM found for device ID: %s", self._device_id)
                _LOGGER.debug("Available VMs: %s", [v.get("vmid") for v in self.coordinator.data.get("vms", [])])
        elif self._device_type == "Container":
            _LOGGER.debug("Looking for container with device ID: %s (type: %s)", self._device_id, type(self._device_id))
            _LOGGER.debug("Available containers: %s", [((c.get("id") or c.get("vmid")), type(c.get("id") or c.get("vmid"))) for c in self.coordinator.data.get("containers", [])])
            
            for container in self.coordinator.data.get("containers", []):
                container_id = container.get("id") or container.get("vmid")
                _LOGGER.debug("Comparing container ID: %s (type: %s) with device ID: %s (type: %s)", 
                             container_id, type(container_id), self._device_id, type(self._device_id))
                
                if container_id == self._device_id:
                    _LOGGER.debug("Found matching container: %s", container_id)
                    old_value = self._attr_native_value
                    self._update_container_value(container)
                    _LOGGER.debug("[ASYNC] Updated container sensor %s: %s -> %s", self._attr_name, old_value, self._attr_native_value)
                    break
            else:
                _LOGGER.warning("No matching container found for device ID: %s", self._device_id)
                _LOGGER.debug("Available containers: %s", [(c.get("id") or c.get("vmid")) for c in self.coordinator.data.get("containers", [])])

        # Notify Home Assistant of the new state
        _LOGGER.debug("Calling super().async_handle_coordinator_update() for %s", self._attr_name)
        await super().async_handle_coordinator_update()
        _LOGGER.debug("=== COORDINATOR UPDATE COMPLETED FOR %s ===", self._attr_name)

    def _update_node_value(self, node_data):
        """Update sensor value from node data."""
        _LOGGER.debug("=== UPDATING NODE VALUE FOR %s ===", self._attr_name)
        _LOGGER.debug("Raw attr name: %s", self._raw_attr_name)
        _LOGGER.debug("Node data: %s", node_data)
        _LOGGER.debug("Current value: %s", self._attr_native_value)
        
        if self._raw_attr_name == "cpu_usage_percent":
            cpu_value = node_data.get("cpu", 0)
            new_value = float(cpu_value) * 100
            _LOGGER.debug("CPU value from data: %s, calculated: %s", cpu_value, new_value)
            self._attr_native_value = new_value
        elif self._raw_attr_name == "memory_used_bytes":
            mem_value = node_data.get("mem", 0)
            _LOGGER.debug("Memory value from data: %s", mem_value)
            self._attr_native_value = mem_value
        elif self._raw_attr_name == "memory_total_bytes":
            maxmem_value = node_data.get("maxmem", 0)
            _LOGGER.debug("Max memory value from data: %s", maxmem_value)
            self._attr_native_value = maxmem_value
        elif self._raw_attr_name == "disk_used_bytes":
            disk_value = node_data.get("disk", 0)
            _LOGGER.debug("Disk value from data: %s", disk_value)
            self._attr_native_value = disk_value
        elif self._raw_attr_name == "disk_total_bytes":
            maxdisk_value = node_data.get("maxdisk", 0)
            _LOGGER.debug("Max disk value from data: %s", maxdisk_value)
            self._attr_native_value = maxdisk_value
        elif self._raw_attr_name == "uptime_seconds":
            uptime_value = node_data.get("uptime", 0)
            _LOGGER.debug("Uptime value from data: %s", uptime_value)
            self._attr_native_value = uptime_value
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(node_data.get("mem", 0))
            maxmem = float(node_data.get("maxmem", 1))
            new_value = (mem / maxmem * 100) if maxmem > 0 else 0.0
            _LOGGER.debug("Memory usage calculation: mem=%s, maxmem=%s, result=%s", mem, maxmem, new_value)
            self._attr_native_value = new_value
        elif self._raw_attr_name.startswith("load_average_"):
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            _LOGGER.debug("Node load data for device %s: %s", self._device_id, node_load_data)
            if self._raw_attr_name == "load_average_1min":
                load_value = node_load_data.get("loadavg_1min", 0)
                _LOGGER.debug("Load average 1min value: %s", load_value)
                self._attr_native_value = float(load_value)
            elif self._raw_attr_name == "load_average_5min":
                load_value = node_load_data.get("loadavg_5min", 0)
                _LOGGER.debug("Load average 5min value: %s", load_value)
                self._attr_native_value = float(load_value)
            elif self._raw_attr_name == "load_average_15min":
                load_value = node_load_data.get("loadavg_15min", 0)
                _LOGGER.debug("Load average 15min value: %s", load_value)
                self._attr_native_value = float(load_value)
        elif self._raw_attr_name == "cpu_frequency_mhz":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            freq_value = node_load_data.get("cpu_frequency", 0)
            _LOGGER.debug("CPU frequency value: %s", freq_value)
            self._attr_native_value = int(freq_value)
        elif self._raw_attr_name == "cpu_cores":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            cores_value = node_load_data.get("cpu_cores", 0)
            _LOGGER.debug("CPU cores value: %s", cores_value)
            self._attr_native_value = int(cores_value)
        elif self._raw_attr_name == "cpu_sockets":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            sockets_value = node_load_data.get("cpu_sockets", 0)
            _LOGGER.debug("CPU sockets value: %s", sockets_value)
            self._attr_native_value = int(sockets_value)
        elif self._raw_attr_name == "cpu_total_logical":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            total_value = node_load_data.get("cpu_total", 0)
            _LOGGER.debug("CPU total value: %s", total_value)
            self._attr_native_value = int(total_value)
        elif self._raw_attr_name == "cpu_model":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            model_value = node_load_data.get("cpu_model", "Unknown")
            _LOGGER.debug("CPU model value: %s", model_value)
            self._attr_native_value = model_value
        else:
            _LOGGER.warning("Unknown attribute name: %s", self._raw_attr_name)
        
        _LOGGER.debug("Final updated value: %s", self._attr_native_value)
        _LOGGER.debug("=== NODE VALUE UPDATE COMPLETED ===")

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

    async def async_refresh(self) -> None:
        """Manually trigger a refresh for testing."""
        _LOGGER.debug("Manual refresh triggered for %s", self._attr_name)
        await self.async_handle_coordinator_update()

    async def test_coordinator_update(self) -> None:
        """Test method to manually trigger coordinator update."""
        _LOGGER.debug("=== TESTING COORDINATOR UPDATE FOR %s ===", self._attr_name)
        _LOGGER.debug("Current value: %s", self._attr_native_value)
        _LOGGER.debug("Coordinator data available: %s", self.coordinator.data is not None)
        
        if self.coordinator.data:
            _LOGGER.debug("Coordinator data keys: %s", list(self.coordinator.data.keys()))
            _LOGGER.debug("Coordinator data sample: %s", self.coordinator.data.get("nodes", [])[:1])
        
        # Manually call the update method
        await self.async_handle_coordinator_update()
        
        _LOGGER.debug("Updated value: %s", self._attr_native_value)
        _LOGGER.debug("=== COORDINATOR UPDATE TEST COMPLETED ===")

    async def force_update(self) -> None:
        """Force an update of this entity."""
        _LOGGER.debug("=== FORCING UPDATE FOR %s ===", self._attr_name)
        _LOGGER.debug("Current value: %s", self._attr_native_value)
        
        # Manually call the update method
        await self.async_handle_coordinator_update()
        
        _LOGGER.debug("Updated value: %s", self._attr_native_value)
        _LOGGER.debug("=== FORCE UPDATE COMPLETED ===")

async def async_trigger_manual_update(hass: HomeAssistant, entry_id: str) -> None:
    """Manually trigger an update for all entities."""
    _LOGGER.debug("=== MANUAL UPDATE TRIGGERED FOR ENTRY %s ===", entry_id)
    
    coordinator_key = f"{entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)
    
    if not coordinator:
        _LOGGER.error("No coordinator found for entry %s", entry_id)
        return
    
    try:
        _LOGGER.debug("Triggering manual coordinator refresh...")
        await coordinator.async_request_refresh()
        _LOGGER.debug("Manual coordinator refresh completed")
        
        # Manually notify all entities
        if hasattr(coordinator, '_listeners') and coordinator._listeners:
            _LOGGER.debug("Manually notifying %s entities", len(coordinator._listeners))
            for i, listener in enumerate(coordinator._listeners):
                try:
                    _LOGGER.debug("Manually notifying entity %s", i+1)
                    listener()
                    _LOGGER.debug("Successfully manually notified entity %s", i+1)
                except Exception as e:
                    _LOGGER.error("Error manually notifying entity %s: %s", i+1, e)
        else:
            _LOGGER.warning("No listeners found on coordinator")
            
    except Exception as e:
        _LOGGER.error("Error during manual update: %s", e)
    
    _LOGGER.debug("=== MANUAL UPDATE COMPLETED ===")
