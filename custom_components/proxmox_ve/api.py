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
            try:
                if self.auth_method == "password":
                    self._api = ProxmoxAPI(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        verify_ssl=self.verify_ssl,
                        backend='https',
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
                    )
            except AuthenticationError as e:
                _LOGGER.error("Authentication failed for user %s@%s: %s", self.username, self.host, e)
                raise
            except Exception as e:
                _LOGGER.error("Failed to create Proxmox API client: %s", e)
                raise
        return self._api

    def async_get_data(self) -> dict[str, Any]:
        """Get data from Proxmox VE API."""
        try:
            _LOGGER.debug("Fetching data from Proxmox VE at %s:%s", self.host, self.port)
            
            # Test authentication first by getting cluster status
            try:
                cluster_status = self.api.cluster.status.get()
                _LOGGER.debug("Successfully authenticated and got cluster status")
            except Exception as e:
                _LOGGER.error("Failed to get cluster status (authentication test): %s", e)
                # Try to get version info as fallback authentication test
                version = self.api.version.get()
                _LOGGER.debug("Authentication successful via version check: %s", version)
                cluster_status = []
            
            # Get all nodes
            nodes = self.api.nodes.get()
            _LOGGER.debug("Found %d nodes", len(nodes))
            
            # Get VMs and containers from all nodes
            all_vms = []
            all_containers = []
            
            for node in nodes:
                node_name = node["node"]
                _LOGGER.debug("Processing node: %s", node_name)
                
                try:
                    # Get VMs (QEMU)
                    vms = self.api.nodes(node_name).qemu.get()
                    for vm in vms:
                        vm["node"] = node_name
                        vm["type"] = "qemu"
                    all_vms.extend(vms)
                    _LOGGER.debug("Found %d VMs on node %s", len(vms), node_name)
                except Exception as e:
                    _LOGGER.warning("Failed to get VMs from node %s: %s", node_name, e)
                
                try:
                    # Get containers (LXC)
                    containers = self.api.nodes(node_name).lxc.get()
                    for container in containers:
                        container["node"] = node_name
                        container["type"] = "lxc"
                    all_containers.extend(containers)
                    _LOGGER.debug("Found %d containers on node %s", len(containers), node_name)
                except Exception as e:
                    _LOGGER.warning("Failed to get containers from node %s: %s", node_name, e)
            
            result = {
                "cluster_status": cluster_status,
                "nodes": nodes,
                "vms": all_vms,
                "containers": all_containers,
            }
            
            _LOGGER.info("Successfully fetched Proxmox VE data: %d nodes, %d VMs, %d containers", 
                        len(nodes), len(all_vms), len(all_containers))
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