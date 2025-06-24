"""Proxmox VE API client."""
from __future__ import annotations

import logging
import time
from typing import Any

from proxmoxer import ProxmoxAPI
from proxmoxer.core import AuthenticationError
import requests

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import CONF_TOKEN_NAME, CONF_TOKEN_VALUE, CONF_VERIFY_SSL

_LOGGER = logging.getLogger(__name__)


class ProxmoxVEClient:
    """Proxmox VE API client."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Proxmox VE client."""
        self.host = config[CONF_HOST]
        self.port = config[CONF_PORT]
        self.username = config[CONF_USERNAME]
        self.verify_ssl = config[CONF_VERIFY_SSL]
        
        # Determine authentication method
        if config.get(CONF_PASSWORD):
            self.auth_method = "password"
            self.password = config[CONF_PASSWORD]
            self.token_name = None
            self.token_value = None
        else:
            self.auth_method = "token"
            self.password = None
            self.token_name = config[CONF_TOKEN_NAME]
            self.token_value = config[CONF_TOKEN_VALUE]
        
        self._api = None

    @property
    def api(self) -> ProxmoxAPI:
        """Get the Proxmox API instance."""
        if self._api is None:
            try:
                if self.auth_method == "password":
                    self._api = ProxmoxAPI(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        verify_ssl=self.verify_ssl,
                        backend='https',
                        timeout=3,  # 3 second timeout for faster failures
                    )
                else:
                    self._api = ProxmoxAPI(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        token_name=self.token_name,
                        token_value=self.token_value,
                        verify_ssl=self.verify_ssl,
                        backend='https',
                        timeout=3,  # 3 second timeout for faster failures
                    )
            except AuthenticationError as e:
                _LOGGER.error("Authentication failed for user %s@%s: %s", self.username, self.host, e)
                raise
            except Exception as e:
                _LOGGER.error("Failed to create Proxmox API client: %s", e)
                raise
        return self._api

    def _fetch_node_data(self, node_name: str) -> dict[str, Any]:
        """Fetch data for a specific node with fast timeout handling."""
        node_data = {
            "name": node_name,
            "vms": [],
            "containers": [],
            "load_average": [0.0, 0.0, 0.0],
            "cpu_info": {},
        }
        
        _LOGGER.debug("Fetching data for node %s", node_name)
        
        # Get VMs (QEMU) for this node
        try:
            vms = self.api.nodes(node_name).qemu.get()
            for vm in vms:
                vm["node"] = node_name
                vm["type"] = "qemu"
            node_data["vms"] = vms
            _LOGGER.debug("Fetched %d VMs from node %s", len(vms), node_name)
        except Exception as e:
            _LOGGER.warning("Failed to get VMs from node %s: %s", node_name, e)
        
        # Get containers (LXC) for this node  
        try:
            containers = self.api.nodes(node_name).lxc.get()
            for container in containers:
                container["node"] = node_name
                container["type"] = "lxc"
            node_data["containers"] = containers
            _LOGGER.debug("Fetched %d containers from node %s", len(containers), node_name)
        except Exception as e:
            _LOGGER.warning("Failed to get containers from node %s: %s", node_name, e)
        
        # Get node status for load averages and CPU info
        try:
            status = self.api.nodes(node_name).status.get()
            if status:
                # Extract load averages if available
                load_avg = status.get("loadavg", [0.0, 0.0, 0.0])
                if isinstance(load_avg, list) and len(load_avg) >= 3:
                    node_data["load_average"] = load_avg[:3]
                
                # Extract CPU info
                node_data["cpu_info"] = {
                    "cpuinfo": status.get("cpuinfo", {}),
                    "cpu_freq": status.get("cpu_freq", 0),
                }
                _LOGGER.debug("Fetched status data for node %s", node_name)
        except Exception as e:
            _LOGGER.warning("Failed to get status from node %s: %s", node_name, e)
        
        return node_data

    def async_get_data(self) -> dict[str, Any]:
        """Get data from Proxmox VE API with optimized performance."""
        start_time = time.time()
        
        try:
            _LOGGER.debug("Starting data fetch from Proxmox VE at %s:%s", self.host, self.port)
            
            # Get basic cluster info and nodes first (sequential, required for further calls)
            try:
                nodes = self.api.nodes.get()
                _LOGGER.debug("Fetched %d nodes", len(nodes))
            except Exception as e:
                _LOGGER.error("Failed to get nodes list: %s", e)
                # Try version check as fallback to verify connection
                version = self.api.version.get()
                _LOGGER.debug("Connection verified via version check: %s", version)
                nodes = []
            
            if not nodes:
                _LOGGER.warning("No nodes found or accessible")
                return {
                    "cluster_status": [],
                    "nodes": [],
                    "vms": [],
                    "containers": [],
                }
            
            # Get cluster status (optional, don't fail if it doesn't work)
            cluster_status = []
            try:
                cluster_status = self.api.cluster.status.get()
                _LOGGER.debug("Fetched cluster status")
            except Exception as e:
                _LOGGER.debug("Cluster status not available (single node setup?): %s", e)
            
            # Fetch data from all nodes sequentially to avoid threading issues
            all_vms = []
            all_containers = []
            nodes_with_data = []
            
            for node in nodes:
                node_name = node["node"]
                try:
                    node_data = self._fetch_node_data(node_name)
                    all_vms.extend(node_data["vms"])
                    all_containers.extend(node_data["containers"])
                    
                    # Merge additional node data back into the node info
                    enhanced_node = node.copy()
                    enhanced_node["load_average"] = node_data["load_average"]
                    enhanced_node["cpu_info"] = node_data["cpu_info"]
                    nodes_with_data.append(enhanced_node)
                    
                except Exception as e:
                    _LOGGER.error("Failed to fetch data from node %s: %s", node_name, e)
                    # Still add the node even if data fetch failed
                    enhanced_node = node.copy()
                    enhanced_node["load_average"] = [0.0, 0.0, 0.0]
                    enhanced_node["cpu_info"] = {}
                    nodes_with_data.append(enhanced_node)
            
            result = {
                "cluster_status": cluster_status,
                "nodes": nodes_with_data,
                "vms": all_vms,
                "containers": all_containers,
            }
            
            # Performance logging
            end_time = time.time()
            duration = end_time - start_time
            _LOGGER.info(
                "Proxmox VE data fetch completed in %.2fs: %d nodes, %d VMs, %d containers", 
                duration, len(nodes), len(all_vms), len(all_containers)
            )
            
            return result
            
        except AuthenticationError as e:
            _LOGGER.error("Authentication failed for %s@%s:%s - %s", self.username, self.host, self.port, e)
            raise
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("Connection failed to %s:%s - %s", self.host, self.port, e)
            raise
        except requests.exceptions.Timeout as e:
            _LOGGER.error("Request timeout to %s:%s - %s", self.host, self.port, e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error while fetching data from %s:%s - %s", self.host, self.port, e)
            raise