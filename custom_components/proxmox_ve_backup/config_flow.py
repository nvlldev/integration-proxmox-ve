"""Config flow for Proxmox VE."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from proxmoxer.core import AuthenticationError
from requests.exceptions import ConnectionError

from .api import ProxmoxClient
from .const import (
    CONF_TOKEN_NAME,
    CONF_TOKEN_VALUE,
    CONF_UPDATE_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host", description={"suggested_value": "192.168.1.100:8006"}): str,
        vol.Optional("username", default="root", description={"suggested_value": "root"}): str,
        vol.Required("auth_method", description={"suggested_value": "password"}): vol.In(["password", "token"]),
        vol.Optional("verify_ssl", default=True): bool,
        vol.Optional("update_interval", default=DEFAULT_UPDATE_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=3600)
        ),
    }
)

STEP_PASSWORD_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("password"): str,
    }
)

STEP_TOKEN_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("token_name", description={"suggested_value": "homeassistant"}): str,
        vol.Required("token_value"): str,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Proxmox VE."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self.data = {}

    def _validate_username(self, username: str) -> str:
        """Validate and format username for Proxmox VE."""
        # If username doesn't contain @, assume it's a local user and add @pam
        if '@' not in username:
            username = f"{username}@pam"
            _LOGGER.debug("Username format corrected to: %s", username)
        return username

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Set default username if not provided
            if not user_input.get("username"):
                user_input["username"] = "root"
            
            # Validate and format username
            user_input["username"] = self._validate_username(user_input["username"])
            
            # Map field names to constants
            self.data[CONF_HOST] = user_input["host"]
            self.data[CONF_USERNAME] = user_input["username"]
            self.data["auth_method"] = user_input["auth_method"]
            self.data[CONF_VERIFY_SSL] = user_input["verify_ssl"]
            self.data[CONF_UPDATE_INTERVAL] = user_input["update_interval"]
            
            if user_input["auth_method"] == "password":
                return await self.async_step_password()
            return await self.async_step_token()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={
                "username_format": "e.g., 'root' or 'root@pam' (will be auto-formatted if needed)"
            }
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the password step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data[CONF_PASSWORD] = user_input["password"]
            try:
                _LOGGER.debug("Testing connection with username: %s", self.data[CONF_USERNAME])
                client = ProxmoxClient(
                    host=self.data[CONF_HOST],
                    username=self.data[CONF_USERNAME],
                    password=self.data[CONF_PASSWORD],
                    verify_ssl=self.data[CONF_VERIFY_SSL],
                )
                await self.hass.async_add_executor_job(client.authenticate)
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except AuthenticationError as exc:
                _LOGGER.error("Authentication failed: %s", exc)
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=self.data[CONF_HOST], data=self.data
                )
        return self.async_show_form(
            step_id="password", data_schema=STEP_PASSWORD_DATA_SCHEMA, errors=errors
        )

    async def async_step_token(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the token step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data[CONF_TOKEN_NAME] = user_input["token_name"]
            self.data[CONF_TOKEN_VALUE] = user_input["token_value"]
            try:
                _LOGGER.debug("Testing connection with username: %s", self.data[CONF_USERNAME])
                client = ProxmoxClient(
                    host=self.data[CONF_HOST],
                    username=self.data[CONF_USERNAME],
                    token_name=self.data[CONF_TOKEN_NAME],
                    token_value=self.data[CONF_TOKEN_VALUE],
                    verify_ssl=self.data[CONF_VERIFY_SSL],
                )
                await self.hass.async_add_executor_job(client.authenticate)
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except AuthenticationError as exc:
                _LOGGER.error("Authentication failed: %s", exc)
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=self.data[CONF_HOST], data=self.data
                )
        return self.async_show_form(
            step_id="token", data_schema=STEP_TOKEN_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug("Options flow received user input: %s", user_input)
            # Convert the user input to use the correct constant names
            options_data = {
                CONF_UPDATE_INTERVAL: user_input["update_interval"]
            }
            _LOGGER.debug("Saving options data: %s", options_data)
            return self.async_create_entry(title="", data=options_data)

        # Define the options schema using the translation system
        options_schema = vol.Schema(
            {
                vol.Optional(
                    "update_interval",
                    default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        ) 