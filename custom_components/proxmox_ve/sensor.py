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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from proxmoxer.core import AuthenticationError
from requests.exceptions import ConnectionError

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL
from .api import ProxmoxClient

_LOGGER = logging.getLogger(__name__)


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
            
            return {"nodes": nodes, "vms": all_vms, "containers": all_containers, "node_load_data": node_load_data}
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

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="proxmox",
        update_method=async_update_data,
        update_interval=timedelta(seconds=entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))),
    )

    # Store coordinator in hass data
    hass.data[DOMAIN][f"{entry.entry_id}_coordinator"] = coordinator

    # Wait for the first data fetch
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
            _LOGGER.debug("Creating %s node sensors", len(coordinator.data["nodes"]))
            for node in coordinator.data["nodes"]:
                _LOGGER.debug("Creating node sensor for: %s", node.get("node", "unknown"))
                entities.append(ProxmoxNodeSensor(coordinator, node, entry.entry_id, entry.data["host"]))
        
        if coordinator.data and "vms" in coordinator.data:
            _LOGGER.debug("Creating %s VM sensors", len(coordinator.data["vms"]))
            for vm in coordinator.data["vms"]:
                _LOGGER.debug("Creating VM sensor for: %s (ID: %s)", vm.get("name", "unknown"), vm.get("vmid", "unknown"))
                entities.append(ProxmoxVmSensor(coordinator, vm, entry.entry_id, entry.data["host"]))
        
        if coordinator.data and "containers" in coordinator.data:
            _LOGGER.debug("Creating %s container sensors", len(coordinator.data["containers"]))
            for container in coordinator.data["containers"]:
                container_id = container.get("id") or container.get("vmid")
                _LOGGER.debug("Creating container sensor for: %s (ID: %s)", container.get("name", "unknown"), container_id)
                _LOGGER.debug("Container data: %s", container)
                entities.append(ProxmoxContainerSensor(coordinator, container, entry.entry_id, entry.data["host"]))
    except Exception as e:
        _LOGGER.error("Error creating entities: %s", e)

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


class ProxmoxNodeSensor(CoordinatorEntity, SensorEntity):
    """A sensor for a Proxmox VE node."""

    def __init__(self, coordinator, node, entry_id, host):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._node_name = node["node"]
        self._attr_name = f"Proxmox VE Node {self._node_name}"
        self._attr_unique_id = f"proxmox_ve_node_{self._node_name}_{entry_id}"
        self._host = host

    @property
    def node(self):
        """Return the node data."""
        if not self.coordinator.data or "nodes" not in self.coordinator.data:
            return None
        return next(
            (
                node
                for node in self.coordinator.data["nodes"]
                if node["node"] == self._node_name
            ),
            None,
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        node_data = self.node
        if not node_data:
            return "unknown"
        return node_data.get("status", "unknown")

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the node."""
        if not self.node:
            return {}
        
        # Get load data for this node
        load_data = {}
        if (self.coordinator.data and 
            "node_load_data" in self.coordinator.data and 
            self._node_name in self.coordinator.data["node_load_data"]):
            load_data = self.coordinator.data["node_load_data"][self._node_name]
            _LOGGER.debug("Found load data for node %s: %s", self._node_name, load_data)
        else:
            _LOGGER.debug("No load data found for node %s", self._node_name)
        
        # Ensure loadavg values are numbers
        loadavg_1min = float(load_data.get("loadavg_1min", 0))
        loadavg_5min = float(load_data.get("loadavg_5min", 0))
        loadavg_15min = float(load_data.get("loadavg_15min", 0))
        
        attributes = {
            "cpu_usage_percent": self.node.get("cpu", 0),
            "memory_used_bytes": self.node.get("mem", 0),
            "memory_total_bytes": self.node.get("maxmem", 0),
            "disk_used_bytes": self.node.get("disk", 0),
            "disk_total_bytes": self.node.get("maxdisk", 0),
            "uptime_seconds": self.node.get("uptime", 0),
            "load_average_1min": loadavg_1min,
            "load_average_5min": loadavg_5min,
            "load_average_15min": loadavg_15min,
            "cpu_frequency_mhz": int(load_data.get("cpu_frequency", 0)),
            "cpu_cores": int(load_data.get("cpu_cores", 0)),
            "cpu_sockets": int(load_data.get("cpu_sockets", 0)),
            "cpu_total_logical": int(load_data.get("cpu_total", 0)),
            "cpu_model": load_data.get("cpu_model", "Unknown"),
        }
        
        _LOGGER.debug("Node %s attributes: %s", self._node_name, attributes)
        return attributes


class ProxmoxVmSensor(CoordinatorEntity, SensorEntity):
    """A sensor for a Proxmox VE VM."""

    def __init__(self, coordinator, vm, entry_id, host):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._vmid = vm["vmid"]
        self._vm_name = vm.get("name", f"VM {self._vmid}")
        self._attr_name = f"Proxmox VE VM {self._vm_name}"
        self._attr_unique_id = f"proxmox_ve_vm_{self._vmid}_{entry_id}"
        self._host = host

    @property
    def vm(self):
        """Return the vm data."""
        if not self.coordinator.data or "vms" not in self.coordinator.data:
            return None
        return next(
            (vm for vm in self.coordinator.data["vms"] if vm["vmid"] == self._vmid),
            None,
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        vm_data = self.vm
        if not vm_data:
            return "unknown"
        return vm_data.get("status", "unknown")

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the vm."""
        if not self.vm:
            return {}
        
        return {
            "cpu_usage_percent": self.vm.get("cpu", 0),
            "memory_used_bytes": self.vm.get("mem", 0),
            "memory_total_bytes": self.vm.get("maxmem", 0),
            "disk_used_bytes": self.vm.get("disk", 0),
            "disk_total_bytes": self.vm.get("maxdisk", 0),
            "uptime_seconds": self.vm.get("uptime", 0),
            "node_name": self.vm.get("node", "unknown"),
        }


class ProxmoxContainerSensor(CoordinatorEntity, SensorEntity):
    """A sensor for a Proxmox VE container."""

    def __init__(self, coordinator, container, entry_id, host):
        """Initialize the sensor."""
        super().__init__(coordinator)
        # Handle both 'id' and 'vmid' field names for container ID
        self._container_id = container.get("id") or container.get("vmid")
        if self._container_id is None:
            _LOGGER.error("Container missing both 'id' and 'vmid' fields: %s", container)
            self._container_id = "unknown"
        
        self._container_name = container.get("name", f"Container {self._container_id}")
        self._attr_name = f"Proxmox VE Container {self._container_name}"
        self._attr_unique_id = f"proxmox_ve_container_{self._container_id}_{entry_id}"
        self._host = host
        _LOGGER.debug("Initialized container sensor: ID=%s, Name=%s, UniqueID=%s", 
                     self._container_id, self._container_name, self._attr_unique_id)

    @property
    def container(self):
        """Return the container data."""
        if not self.coordinator.data or "containers" not in self.coordinator.data:
            _LOGGER.debug("No container data available for container ID %s", self._container_id)
            return None
        
        container_data = next(
            (
                container
                for container in self.coordinator.data["containers"]
                if (container.get("id") or container.get("vmid")) == self._container_id
            ),
            None,
        )
        
        if container_data is None:
            _LOGGER.debug("Container with ID %s not found in coordinator data", self._container_id)
            _LOGGER.debug("Available container IDs: %s", 
                         [(c.get("id") or c.get("vmid"), "unknown") for c in self.coordinator.data["containers"]])
        
        return container_data

    @property
    def native_value(self):
        """Return the state of the sensor."""
        container_data = self.container
        if not container_data:
            return "unknown"
        return container_data.get("status", "unknown")

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the container."""
        if not self.container:
            return {}
        
        return {
            "cpu_usage_percent": self.container.get("cpu", 0),
            "memory_used_bytes": self.container.get("mem", 0),
            "memory_total_bytes": self.container.get("maxmem", 0),
            "disk_used_bytes": self.container.get("disk", 0),
            "disk_total_bytes": self.container.get("maxdisk", 0),
            "uptime_seconds": self.container.get("uptime", 0),
            "node_name": self.container.get("node", "unknown"),
        }
