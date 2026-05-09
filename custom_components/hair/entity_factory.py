"""Factory for creating HA entities from IR device profiles."""
from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


DEVICE_TYPE_TO_PLATFORM: dict[str, str] = {
    DeviceType.TV: "media_player",
    DeviceType.SOUNDBAR: "media_player",
    DeviceType.AC: "climate",
    DeviceType.FAN: "fan",
    DeviceType.PROJECTOR: "media_player",
    DeviceType.OTHER: "remote",
}


SIGNAL_ADD_ENTITY = f"{DOMAIN}_add_entity"
SIGNAL_REMOVE_ENTITY = f"{DOMAIN}_remove_entity"
SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_update_entity"


class EntityFactory:
    """Create and manage HA entities for IR devices.

    Platforms register their ``async_add_entities`` callback at setup
    time. When a device is created/removed/updated, the factory dispatches
    to the matching platform.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._add_entity_callbacks: dict[str, AddEntitiesCallback] = {}
        self._entities: dict[str, str] = {}
        # Hooks platforms install so they can react to per-device add/remove/update.
        self._platform_hooks: dict[
            str, dict[str, Callable[[IRDevice], None]]
        ] = {}

    def register_platform(
        self,
        platform: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._add_entity_callbacks[platform] = async_add_entities

    def register_platform_hooks(
        self,
        platform: str,
        on_add: Callable[[IRDevice], None] | None = None,
        on_remove: Callable[[IRDevice], None] | None = None,
        on_update: Callable[[IRDevice], None] | None = None,
    ) -> None:
        hooks = self._platform_hooks.setdefault(platform, {})
        if on_add is not None:
            hooks["on_add"] = on_add
        if on_remove is not None:
            hooks["on_remove"] = on_remove
        if on_update is not None:
            hooks["on_update"] = on_update

    def get_platform_for_device(self, device: IRDevice) -> str:
        return DEVICE_TYPE_TO_PLATFORM.get(
            str(device.device_type), "remote"
        )

    async def async_create_entities(self, device: IRDevice) -> None:
        platform = self.get_platform_for_device(device)
        device.entity_config.platform = platform
        self._entities[device.id] = platform

        hooks = self._platform_hooks.get(platform, {})
        on_add = hooks.get("on_add")
        if on_add is not None:
            on_add(device)
        else:
            # Platform not yet set up — dispatch a signal and let the
            # platform's setup_entry handler pick it up on registration.
            async_dispatcher_send(self._hass, SIGNAL_ADD_ENTITY, device)

    async def async_remove_entities(self, device_id: str) -> None:
        platform = self._entities.pop(device_id, None)
        if platform is None:
            return
        hooks = self._platform_hooks.get(platform, {})
        on_remove = hooks.get("on_remove")
        if on_remove is not None:
            on_remove_device = on_remove
            on_remove_device(device_id)  # type: ignore[arg-type]

    async def async_update_entities(self, device: IRDevice) -> None:
        platform = self._entities.get(device.id) or self.get_platform_for_device(
            device
        )
        hooks = self._platform_hooks.get(platform, {})
        on_update = hooks.get("on_update")
        if on_update is not None:
            on_update(device)
