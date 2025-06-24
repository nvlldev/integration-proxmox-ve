"""Proxmox VE API client."""
from __future__ import annotations

import logging
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
            if self.auth_method == "password":
                self._api = ProxmoxAPI(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    verify_ssl=self.verify_ssl,
                )
            else:
                self._api = ProxmoxAPI(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    token_name=self.token_name,
                    token_value=self.token_value,
                    verify_ssl=self.verify_ssl,
                )
        return self._api

    def async_get_data(self) -> dict[str, Any]:
        """Get data from Proxmox VE API."""
        try:
            # Get cluster information
            cluster_status = self.api.cluster.status.get()
            
            # Get all nodes
            nodes = self.api.nodes.get()
            
            # Get VMs and containers from all nodes
            all_vms = []
            all_containers = []
            
            for node in nodes:
                node_name = node["node"]
                
                try:
                    # Get VMs (QEMU)
                    vms = self.api.nodes(node_name).qemu.get()
                    for vm in vms:
                        vm["node"] = node_name
                        vm["type"] = "qemu"
                    all_vms.extend(vms)
                except Exception as e:
                    _LOGGER.warning("Failed to get VMs from node %s: %s", node_name, e)
                
                try:
                    # Get containers (LXC)
                    containers = self.api.nodes(node_name).lxc.get()
                    for container in containers:
                        container["node"] = node_name
                        container["type"] = "lxc"
                    all_containers.extend(containers)
                except Exception as e:
                    _LOGGER.warning("Failed to get containers from node %s: %s", node_name, e)
            
            return {
                "cluster_status": cluster_status,
                "nodes": nodes,
                "vms": all_vms,
                "containers": all_containers,
            }
            
        except AuthenticationError as e:
            _LOGGER.error("Authentication failed: %s", e)
            raise
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("Connection failed: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error: %s", e)
            raise