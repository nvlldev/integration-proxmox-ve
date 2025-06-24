"""Data models for Proxmox VE integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProxmoxResource:
    """Base class for Proxmox resources."""

    name: str
    node: str
    cpu_usage: float = 0.0
    memory_bytes: int = 0
    memory_max_bytes: int = 0
    disk_bytes: int = 0
    disk_max_bytes: int = 0
    uptime_seconds: int = 0
    status: str = "unknown"

    @property
    def memory_usage_percent(self) -> float:
        """Calculate memory usage percentage."""
        return (self.memory_bytes / self.memory_max_bytes * 100) if self.memory_max_bytes > 0 else 0.0

    @property
    def disk_usage_percent(self) -> float:
        """Calculate disk usage percentage."""
        return (self.disk_bytes / self.disk_max_bytes * 100) if self.disk_max_bytes > 0 else 0.0

    @property
    def disk_free_percent(self) -> float:
        """Calculate disk free percentage."""
        if self.disk_max_bytes <= 0:
            return 0.0
        return ((self.disk_max_bytes - self.disk_bytes) / self.disk_max_bytes * 100)

    @property
    def cpu_usage_percent(self) -> float:
        """Get CPU usage as percentage."""
        return self.cpu_usage * 100


@dataclass
class ProxmoxNode(ProxmoxResource):
    """Represents a Proxmox VE node."""

    node_id: str = ""
    available: bool = True
    load_average_1min: float = 0.0
    load_average_5min: float = 0.0
    load_average_15min: float = 0.0
    cpu_frequency_mhz: int = 0
    cpu_cores: int = 0
    cpu_sockets: int = 0
    cpu_model: str = "Unknown"

    @property
    def cpu_total_logical(self) -> int:
        """Calculate total logical CPUs."""
        return self.cpu_cores * self.cpu_sockets if self.cpu_cores > 0 and self.cpu_sockets > 0 else 0

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> ProxmoxNode:
        """Create ProxmoxNode from API data."""
        node_name = data.get("node", "unknown")
        
        # Extract load averages
        load_avg = data.get("loadavg", [0.0, 0.0, 0.0])
        if not isinstance(load_avg, list) or len(load_avg) < 3:
            load_avg = [0.0, 0.0, 0.0]

        # Extract CPU info
        cpu_info = data.get("cpuinfo", {})
        cpu_freq = data.get("cpu_freq", 0)

        return cls(
            node_id=node_name,
            name=node_name,
            node=node_name,
            cpu_usage=float(data.get("cpu", 0)),
            memory_bytes=data.get("mem", 0),
            memory_max_bytes=data.get("maxmem", 0),
            disk_bytes=data.get("disk", 0),
            disk_max_bytes=data.get("maxdisk", 0),
            uptime_seconds=data.get("uptime", 0),
            status=data.get("status", "unknown"),
            available=data.get("available", True),
            load_average_1min=load_avg[0],
            load_average_5min=load_avg[1],
            load_average_15min=load_avg[2],
            cpu_frequency_mhz=cpu_freq,
            cpu_cores=cpu_info.get("cores", 0),
            cpu_sockets=cpu_info.get("sockets", 0),
            cpu_model=cpu_info.get("model", "Unknown"),
        )


@dataclass
class ProxmoxVM(ProxmoxResource):
    """Represents a Proxmox VE virtual machine."""

    vmid: int = 0
    vm_type: str = "qemu"

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> ProxmoxVM:
        """Create ProxmoxVM from API data."""
        vmid = data.get("vmid", 0)
        name = data.get("name", f"VM {vmid}")
        
        return cls(
            vmid=vmid,
            name=name,
            node=data.get("node", "unknown"),
            cpu_usage=float(data.get("cpu", 0)),
            memory_bytes=data.get("mem", 0),
            memory_max_bytes=data.get("maxmem", 0),
            disk_bytes=data.get("disk", 0),
            disk_max_bytes=data.get("maxdisk", 0),
            uptime_seconds=data.get("uptime", 0),
            status=data.get("status", "unknown"),
            vm_type=data.get("type", "qemu"),
        )


@dataclass
class ProxmoxContainer(ProxmoxResource):
    """Represents a Proxmox VE LXC container."""

    vmid: int = 0
    container_type: str = "lxc"

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> ProxmoxContainer:
        """Create ProxmoxContainer from API data."""
        vmid = data.get("vmid", 0) or data.get("id", 0)
        name = data.get("name", f"Container {vmid}")
        
        return cls(
            vmid=vmid,
            name=name,
            node=data.get("node", "unknown"),
            cpu_usage=float(data.get("cpu", 0)),
            memory_bytes=data.get("mem", 0),
            memory_max_bytes=data.get("maxmem", 0),
            disk_bytes=data.get("disk", 0),
            disk_max_bytes=data.get("maxdisk", 0),
            uptime_seconds=data.get("uptime", 0),
            status=data.get("status", "unknown"),
            container_type=data.get("type", "lxc"),
        )


@dataclass
class ProxmoxStorage:
    """Represents a Proxmox VE storage pool."""

    storage_id: str
    storage: str
    node: str
    type: str = "unknown"
    content: str = ""
    shared: bool = False
    enabled: bool = True
    used_bytes: int = 0
    total_bytes: int = 0
    available_bytes: int = 0

    @property
    def usage_percent(self) -> float:
        """Calculate storage usage percentage."""
        return (self.used_bytes / self.total_bytes * 100) if self.total_bytes > 0 else 0.0

    @property
    def free_percent(self) -> float:
        """Calculate storage free percentage."""
        if self.total_bytes <= 0:
            return 0.0
        return (self.available_bytes / self.total_bytes * 100)

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> ProxmoxStorage:
        """Create ProxmoxStorage from API data."""
        storage_name = data.get("storage", "unknown")
        node_name = data.get("node", "unknown")
        storage_id = data.get("storage_id", f"{node_name}_{storage_name}")
        
        return cls(
            storage_id=storage_id,
            storage=storage_name,
            node=node_name,
            type=data.get("type", "unknown"),
            content=data.get("content", ""),
            shared=bool(data.get("shared", False)),
            enabled=bool(data.get("enabled", True)),
            used_bytes=data.get("used", 0),
            total_bytes=data.get("total", 0),
            available_bytes=data.get("avail", 0),
        )


@dataclass
class ProxmoxData:
    """Container for all Proxmox VE data."""

    nodes: list[ProxmoxNode]
    vms: list[ProxmoxVM]
    containers: list[ProxmoxContainer]
    storages: list[ProxmoxStorage]
    cluster_status: list[dict[str, Any]]

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> ProxmoxData:
        """Create ProxmoxData from raw API data."""
        nodes = [ProxmoxNode.from_api_data(node) for node in data.get("nodes", [])]
        vms = [ProxmoxVM.from_api_data(vm) for vm in data.get("vms", [])]
        containers = [ProxmoxContainer.from_api_data(container) for container in data.get("containers", [])]
        storages = [ProxmoxStorage.from_api_data(storage) for storage in data.get("storages", [])]
        cluster_status = data.get("cluster_status", [])

        return cls(
            nodes=nodes,
            vms=vms,
            containers=containers,
            storages=storages,
            cluster_status=cluster_status,
        )

    def get_node_by_id(self, node_id: str) -> ProxmoxNode | None:
        """Get node by ID."""
        return next((node for node in self.nodes if node.node_id == node_id), None)

    def get_vm_by_id(self, vmid: int) -> ProxmoxVM | None:
        """Get VM by ID."""
        return next((vm for vm in self.vms if vm.vmid == vmid), None)

    def get_container_by_id(self, vmid: int) -> ProxmoxContainer | None:
        """Get container by ID."""
        return next((container for container in self.containers if container.vmid == vmid), None)

    def get_storage_by_id(self, storage_id: str) -> ProxmoxStorage | None:
        """Get storage by ID."""
        return next((storage for storage in self.storages if storage.storage_id == storage_id), None)