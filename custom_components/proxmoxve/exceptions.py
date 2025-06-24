"""Exceptions for Proxmox VE integration."""
from homeassistant.exceptions import HomeAssistantError


class ProxmoxVEError(HomeAssistantError):
    """Base exception for Proxmox VE integration."""


class ProxmoxVEConnectionError(ProxmoxVEError):
    """Exception raised when connection to Proxmox VE fails."""


class ProxmoxVEAuthenticationError(ProxmoxVEError):
    """Exception raised when authentication with Proxmox VE fails."""


class ProxmoxVEAPIError(ProxmoxVEError):
    """Exception raised when Proxmox VE API returns an error."""


class ProxmoxVETimeoutError(ProxmoxVEError):
    """Exception raised when Proxmox VE API request times out."""


class ProxmoxVEConfigurationError(ProxmoxVEError):
    """Exception raised when Proxmox VE configuration is invalid."""