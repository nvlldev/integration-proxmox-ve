"""Async Proxmox VE API client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKEN_NAME, CONF_TOKEN_VALUE, CONF_VERIFY_SSL
from .exceptions import (
    ProxmoxVEAPIError,
    ProxmoxVEAuthenticationError,
    ProxmoxVEConnectionError,
    ProxmoxVETimeoutError,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3


class ProxmoxVEAPIClient:
    """Async Proxmox VE API client."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._host = config[CONF_HOST]  
        self._port = config[CONF_PORT]
        self._username = config[CONF_USERNAME]
        self._verify_ssl = config[CONF_VERIFY_SSL]
        
        # Build base URL
        self._base_url = f"https://{self._host}:{self._port}/api2/json"
        
        # Determine authentication
        if config.get(CONF_PASSWORD):
            self._auth_data = {
                "username": self._username,
                "password": config[CONF_PASSWORD],
            }
        else:
            self._auth_data = {
                "username": self._username,
                "token_name": config[CONF_TOKEN_NAME],
                "token_value": config[CONF_TOKEN_VALUE],
            }
        
        self._session: aiohttp.ClientSession | None = None
        self._auth_ticket: str | None = None
        self._csrf_token: str | None = None

    async def async_authenticate(self) -> None:
        """Authenticate with Proxmox VE API."""
        if not self._session:
            self._session = async_get_clientsession(
                self._hass, 
                verify_ssl=self._verify_ssl
            )

        auth_url = f"{self._base_url}/access/ticket"
        
        try:
            timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            async with self._session.post(
                auth_url,
                data=self._auth_data,
                timeout=timeout,
            ) as response:
                if response.status == 401:
                    raise ProxmoxVEAuthenticationError("Invalid credentials")
                elif response.status != 200:
                    raise ProxmoxVEAPIError(f"Authentication failed with status {response.status}")
                
                data = await response.json()
                ticket_data = data.get("data", {})
                self._auth_ticket = ticket_data.get("ticket")
                self._csrf_token = ticket_data.get("CSRFPreventionToken")
                
                if not self._auth_ticket:
                    raise ProxmoxVEAuthenticationError("No ticket received from authentication")
                    
                _LOGGER.debug("Successfully authenticated with Proxmox VE")
                
        except aiohttp.ClientError as err:
            raise ProxmoxVEConnectionError(f"Connection failed during authentication: {err}") from err
        except asyncio.TimeoutError as err:
            raise ProxmoxVETimeoutError("Authentication request timed out") from err

    async def async_request(
        self,
        method: str,
        endpoint: str,
        retries: int = DEFAULT_RETRIES,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request with retry logic."""
        if not self._auth_ticket:
            await self.async_authenticate()

        url = f"{self._base_url}{endpoint}"
        headers = {
            "Cookie": f"PVEAuthCookie={self._auth_ticket}",
        }
        
        # Add CSRF token for non-GET requests
        if method.upper() != "GET" and self._csrf_token:
            headers["CSRFPreventionToken"] = self._csrf_token

        for attempt in range(retries):
            try:
                timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                ) as response:
                    if response.status == 401:
                        # Re-authenticate and retry
                        _LOGGER.debug("Received 401, re-authenticating")
                        await self.async_authenticate()
                        headers["Cookie"] = f"PVEAuthCookie={self._auth_ticket}"
                        if self._csrf_token:
                            headers["CSRFPreventionToken"] = self._csrf_token
                        continue
                    elif response.status >= 400:
                        error_text = await response.text()
                        raise ProxmoxVEAPIError(
                            f"API request failed with status {response.status}: {error_text}"
                        )
                    
                    data = await response.json()
                    return data.get("data", {})
                    
            except aiohttp.ClientError as err:
                if attempt == retries - 1:
                    raise ProxmoxVEConnectionError(f"Request failed after {retries} attempts: {err}") from err
                
                _LOGGER.warning("Request attempt %d failed: %s", attempt + 1, err)
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except asyncio.TimeoutError as err:
                if attempt == retries - 1:
                    raise ProxmoxVETimeoutError(f"Request timed out after {retries} attempts") from err
                
                _LOGGER.warning("Request attempt %d timed out", attempt + 1)
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise ProxmoxVEAPIError(f"Request failed after {retries} attempts")

    async def async_get_nodes(self) -> list[dict[str, Any]]:
        """Get list of nodes."""
        return await self.async_request("GET", "/nodes")

    async def async_get_node_status(self, node: str) -> dict[str, Any]:
        """Get node status."""
        return await self.async_request("GET", f"/nodes/{node}/status")

    async def async_get_node_vms(self, node: str) -> list[dict[str, Any]]:
        """Get VMs for a node."""
        return await self.async_request("GET", f"/nodes/{node}/qemu")

    async def async_get_node_containers(self, node: str) -> list[dict[str, Any]]:
        """Get containers for a node."""
        return await self.async_request("GET", f"/nodes/{node}/lxc")

    async def async_get_cluster_status(self) -> list[dict[str, Any]]:
        """Get cluster status."""
        try:
            return await self.async_request("GET", "/cluster/status")
        except ProxmoxVEAPIError:
            # Cluster might not be configured, return empty list
            _LOGGER.debug("Cluster status not available (single node setup?)")
            return []

    async def async_get_version(self) -> dict[str, Any]:
        """Get Proxmox VE version."""
        return await self.async_request("GET", "/version")

    async def async_get_storages(self) -> list[dict[str, Any]]:
        """Get list of storage pools."""
        return await self.async_request("GET", "/storage")

    async def async_get_node_storage_status(self, node: str, storage: str) -> dict[str, Any]:
        """Get storage status for a specific node and storage."""
        return await self.async_request("GET", f"/nodes/{node}/storage/{storage}/status")

    async def async_get_all_data(self) -> dict[str, Any]:
        """Get all data from Proxmox VE API concurrently."""
        _LOGGER.debug("Fetching all data from Proxmox VE API")
        
        try:
            # Get nodes first
            nodes_data = await self.async_get_nodes()
            
            if not nodes_data:
                _LOGGER.warning("No nodes found")
                return {
                    "nodes": [],
                    "vms": [],
                    "containers": [],
                    "cluster_status": [],
                    "storages": [],
                }

            # Prepare tasks for concurrent execution
            tasks = []
            
            # Add cluster status task
            tasks.append(self.async_get_cluster_status())
            
            # Add storage list task
            tasks.append(self.async_get_storages())
            
            # Add node-specific tasks
            for node_data in nodes_data:
                node_name = node_data["node"]
                tasks.extend([
                    self.async_get_node_status(node_name),
                    self.async_get_node_vms(node_name),
                    self.async_get_node_containers(node_name),
                ])

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            cluster_status = results[0] if not isinstance(results[0], Exception) else []
            storages_list = results[1] if not isinstance(results[1], Exception) else []
            
            # Merge node data with status
            enhanced_nodes = []
            all_vms = []
            all_containers = []
            all_storages = []
            
            result_index = 2  # Skip cluster status and storage list results
            for node_data in nodes_data:
                node_name = node_data["node"]
                
                # Get results for this node
                status_result = results[result_index]
                vms_result = results[result_index + 1]
                containers_result = results[result_index + 2]
                result_index += 3
                
                # Merge node status
                enhanced_node = node_data.copy()
                if not isinstance(status_result, Exception):
                    enhanced_node.update(status_result)
                    enhanced_node["available"] = True
                else:
                    _LOGGER.warning("Failed to get status for node %s: %s", node_name, status_result)
                    enhanced_node["available"] = False
                
                enhanced_nodes.append(enhanced_node)
                
                # Add VMs
                if not isinstance(vms_result, Exception):
                    for vm in vms_result:
                        vm["node"] = node_name
                        vm["type"] = "qemu"
                    all_vms.extend(vms_result)
                else:
                    _LOGGER.warning("Failed to get VMs for node %s: %s", node_name, vms_result)
                
                # Add containers
                if not isinstance(containers_result, Exception):
                    for container in containers_result:
                        container["node"] = node_name
                        container["type"] = "lxc"
                    all_containers.extend(containers_result)
                else:
                    _LOGGER.warning("Failed to get containers for node %s: %s", node_name, containers_result)

            # Process storage data if we have it
            if storages_list:
                # Get detailed storage status for each storage on each node
                storage_tasks = []
                for node_data in enhanced_nodes:
                    node_name = node_data["node"]
                    for storage_data in storages_list:
                        storage_name = storage_data.get("storage", "")
                        if storage_name:
                            storage_tasks.append(
                                self.async_get_node_storage_status(node_name, storage_name)
                            )
                
                if storage_tasks:
                    storage_results = await asyncio.gather(*storage_tasks, return_exceptions=True)
                    
                    # Process storage results
                    storage_index = 0
                    for storage_data in storages_list:
                        storage_name = storage_data.get("storage", "")
                        if not storage_name:
                            continue
                            
                        for node_data in enhanced_nodes:
                            node_name = node_data["node"]
                            
                            if storage_index < len(storage_results):
                                status_result = storage_results[storage_index]
                                storage_index += 1
                                
                                if not isinstance(status_result, Exception) and status_result:
                                    # Create enhanced storage entry
                                    enhanced_storage = storage_data.copy()
                                    enhanced_storage.update(status_result)
                                    enhanced_storage["node"] = node_name
                                    enhanced_storage["storage_id"] = f"{node_name}_{storage_name}"
                                    all_storages.append(enhanced_storage)
                                else:
                                    _LOGGER.debug("No storage status for %s on %s", storage_name, node_name)

            result = {
                "nodes": enhanced_nodes,
                "vms": all_vms,
                "containers": all_containers,
                "cluster_status": cluster_status,
                "storages": all_storages,
            }
            
            _LOGGER.info(
                "Successfully fetched data: %d nodes, %d VMs, %d containers, %d storages",
                len(enhanced_nodes),
                len(all_vms),
                len(all_containers),
                len(all_storages),
            )
            
            return result
            
        except Exception as err:
            _LOGGER.error("Failed to fetch data from Proxmox VE API: %s", err)
            raise

    # VM Control Methods
    async def async_vm_start(self, node: str, vmid: int) -> dict[str, Any]:
        """Start a VM."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/start")

    async def async_vm_stop(self, node: str, vmid: int) -> dict[str, Any]:
        """Stop a VM."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/stop")

    async def async_vm_shutdown(self, node: str, vmid: int) -> dict[str, Any]:
        """Shutdown a VM gracefully."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/shutdown")

    async def async_vm_reboot(self, node: str, vmid: int) -> dict[str, Any]:
        """Reboot a VM."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/reboot")

    async def async_vm_reset(self, node: str, vmid: int) -> dict[str, Any]:
        """Reset a VM (hard reset)."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/reset")

    async def async_vm_suspend(self, node: str, vmid: int) -> dict[str, Any]:
        """Suspend a VM."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/suspend")

    async def async_vm_resume(self, node: str, vmid: int) -> dict[str, Any]:
        """Resume a suspended VM."""
        return await self.async_request("POST", f"/nodes/{node}/qemu/{vmid}/status/resume")

    # Container Control Methods
    async def async_container_start(self, node: str, vmid: int) -> dict[str, Any]:
        """Start a container."""
        return await self.async_request("POST", f"/nodes/{node}/lxc/{vmid}/status/start")

    async def async_container_stop(self, node: str, vmid: int) -> dict[str, Any]:
        """Stop a container."""
        return await self.async_request("POST", f"/nodes/{node}/lxc/{vmid}/status/stop")

    async def async_container_shutdown(self, node: str, vmid: int) -> dict[str, Any]:
        """Shutdown a container gracefully."""
        return await self.async_request("POST", f"/nodes/{node}/lxc/{vmid}/status/shutdown")

    async def async_container_reboot(self, node: str, vmid: int) -> dict[str, Any]:
        """Reboot a container."""
        return await self.async_request("POST", f"/nodes/{node}/lxc/{vmid}/status/reboot")

    async def async_container_suspend(self, node: str, vmid: int) -> dict[str, Any]:
        """Suspend a container."""
        return await self.async_request("POST", f"/nodes/{node}/lxc/{vmid}/status/suspend")

    async def async_container_resume(self, node: str, vmid: int) -> dict[str, Any]:
        """Resume a suspended container."""
        return await self.async_request("POST", f"/nodes/{node}/lxc/{vmid}/status/resume")

    async def async_close(self) -> None:
        """Close the API client."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        self._auth_ticket = None
        self._csrf_token = None