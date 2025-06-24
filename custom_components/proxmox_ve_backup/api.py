"""Proxmox API."""
from __future__ import annotations

import logging

from proxmoxer import ProxmoxAPI
from requests.exceptions import ConnectionError
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

_LOGGER = logging.getLogger(__name__)


class ProxmoxClient:
    """Proxmox client."""

    def __init__(
        self,
        host,
        username,
        password=None,
        token_name=None,
        token_value=None,
        verify_ssl=True,
    ):
        """Initialize the Proxmox client."""
        self.host = host
        self.username = username
        self.password = password
        self.token_name = token_name
        self.token_value = token_value
        self.verify_ssl = verify_ssl
        self.proxmox = None

    def authenticate(self) -> ProxmoxAPI:
        """Authenticate with Proxmox."""
        try:
            _LOGGER.debug("Attempting to authenticate with Proxmox at %s using user: %s", self.host, self.username)
            
            if self.password:
                _LOGGER.debug("Using password authentication")
                self.proxmox = ProxmoxAPI(
                    self.host,
                    user=self.username,
                    password=self.password,
                    verify_ssl=self.verify_ssl,
                )
            else:
                _LOGGER.debug("Using token authentication with token: %s", self.token_name)
                # For token authentication, we need to construct the token properly
                # The format should be: username@realm!token_name
                if '@' in self.username:
                    # Username already has realm, use as is
                    token_id = f"{self.username}!{self.token_name}"
                else:
                    # Username doesn't have realm, assume @pam
                    token_id = f"{self.username}@pam!{self.token_name}"
                
                _LOGGER.debug("Constructed token ID: %s", token_id)
                
                # For token authentication, we need to pass the token_id as the user parameter
                # and the token_value as the password parameter
                self.proxmox = ProxmoxAPI(
                    self.host,
                    user=token_id,
                    password=self.token_value,
                    verify_ssl=self.verify_ssl,
                )
            
            _LOGGER.debug("ProxmoxAPI object created successfully")
            
        except ConnectionError as error:
            _LOGGER.error("Failed to connect to Proxmox: %s", error)
            raise
        except Exception as error:
            _LOGGER.error("Unexpected error during authentication: %s", error)
            _LOGGER.error("Host: %s, Username: %s, Verify SSL: %s", self.host, self.username, self.verify_ssl)
            if self.token_name:
                _LOGGER.error("Token name: %s", self.token_name)
            raise

        return self.proxmox 