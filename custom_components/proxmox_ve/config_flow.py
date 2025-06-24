"""Config flow for Proxmox VE integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_TOKEN_NAME,
    CONF_TOKEN_VALUE,
    CONF_UPDATE_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)
from .coordinator import ProxmoxVEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_TOKEN_NAME): str,
        vol.Optional(CONF_TOKEN_VALUE): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(
            CONF_UPDATE_INTERVAL,
            default=DEFAULT_UPDATE_INTERVAL
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    coordinator = ProxmoxVEDataUpdateCoordinator(hass, data)
    await coordinator.async_config_entry_first_refresh()
    
    # If we get here, the connection was successful
    info = {
        "title": f"Proxmox VE {data[CONF_HOST]}",
        "unique_id": f"proxmox_ve_{data[CONF_HOST]}_{data[CONF_USERNAME]}",
    }
    return info


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Proxmox VE."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        # Validate authentication
        if user_input.get(CONF_PASSWORD) and (
            user_input.get(CONF_TOKEN_NAME) or user_input.get(CONF_TOKEN_VALUE)
        ):
            errors["base"] = "auth_method_conflict"
        elif not user_input.get(CONF_PASSWORD) and not (
            user_input.get(CONF_TOKEN_NAME) and user_input.get(CONF_TOKEN_VALUE)
        ):
            errors["base"] = "auth_method_missing"

        if not errors:
            try:
                info = await validate_input(self.hass, user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )