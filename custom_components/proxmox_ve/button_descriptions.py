"""Button entity descriptions for Proxmox VE integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.button import ButtonEntityDescription
from homeassistant.helpers.entity import EntityCategory

from .models import ProxmoxContainer, ProxmoxVM


@dataclass
class ProxmoxButtonEntityDescription(ButtonEntityDescription):
    """Describes Proxmox button entity."""

    press_fn: Callable[[ProxmoxVM | ProxmoxContainer, object], Awaitable[None]] | None = None
    available_fn: Callable[[ProxmoxVM | ProxmoxContainer], bool] | None = None


# VM button descriptions
VM_BUTTONS: tuple[ProxmoxButtonEntityDescription, ...] = (
    ProxmoxButtonEntityDescription(
        key="start",
        name="Start",
        icon="mdi:play",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status in ("stopped", "shutdown"),
    ),
    ProxmoxButtonEntityDescription(
        key="stop",
        name="Stop",
        icon="mdi:stop",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="shutdown",
        name="Shutdown",
        icon="mdi:power",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="reboot",
        name="Reboot",
        icon="mdi:restart",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="reset",
        name="Reset",
        icon="mdi:restart-alert",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="suspend",
        name="Suspend",
        icon="mdi:pause",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="resume",
        name="Resume",
        icon="mdi:play-pause",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda vm: vm.status in ("suspended", "paused"),
    ),
)

# Container button descriptions
CONTAINER_BUTTONS: tuple[ProxmoxButtonEntityDescription, ...] = (
    ProxmoxButtonEntityDescription(
        key="start",
        name="Start",
        icon="mdi:play",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda container: container.status in ("stopped", "shutdown"),
    ),
    ProxmoxButtonEntityDescription(
        key="stop",
        name="Stop",
        icon="mdi:stop",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda container: container.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="shutdown",
        name="Shutdown",
        icon="mdi:power",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda container: container.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="reboot",
        name="Reboot",
        icon="mdi:restart",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda container: container.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="suspend",
        name="Suspend",
        icon="mdi:pause",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda container: container.status == "running",
    ),
    ProxmoxButtonEntityDescription(
        key="resume",
        name="Resume",
        icon="mdi:play-pause",
        entity_category=EntityCategory.CONFIG,
        available_fn=lambda container: container.status in ("suspended", "paused"),
    ),
)