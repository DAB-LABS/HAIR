"""Remote entity platform for HAIR."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAIR remote entities for ``entry``.

    The remote platform is a fallback. We create a remote for any device
    whose preferred platform is "remote", and ALSO for every other device
    so users always have a generic command-sender alongside the typed
    entity. Typed entities (media_player/climate/fan) handle their own
    platform-specific behavior on top.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRRemoteEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.id in entities:
            return
        entity = HAIRRemoteEntity(device, device_manager)
        entities[device.id] = entity
        async_add_entities([entity])

    @callback
    def _on_remove(device_id: str) -> None:
        entity = entities.pop(device_id, None)
        if entity is not None:
            hass.async_create_task(entity.async_remove())

    @callback
    def _on_update(device: IRDevice) -> None:
        entity = entities.get(device.id)
        if entity is not None:
            entity.update_device(device)

    factory.register_platform_hooks(
        "remote", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("remote", async_add_entities)

    # Add a remote for every existing device.
    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRRemoteEntity(RemoteEntity):
    """IR remote entity managed by HAIR."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_remote"
        self._attr_name = "Remote"
        self._is_on = True

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or _humanise_device_type(
                self._device.device_type
            ),
        }

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send_named("Power On", "Power")
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_named("Power Off", "Power")
        self._is_on = False
        self.async_write_ha_state()

    async def async_send_command(
        self, command: list[str], **kwargs: Any
    ) -> None:
        for name in command:
            await self._send_named(name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "device_id": self._device.id,
            "available_commands": [c.name for c in self._device.commands],
            "device_type": str(self._device.device_type),
        }

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        self.async_write_ha_state()

    async def _send_named(self, *candidates: str) -> None:
        for name in candidates:
            command = self._device.get_command_by_name(name)
            if command is not None:
                await self._manager.async_send_command(
                    self._device.id, command.id
                )
                return
        _LOGGER.warning(
            "No matching IR command on %s for %s",
            self._device.name,
            ", ".join(candidates),
        )


def _humanise_device_type(device_type: DeviceType) -> str:
    return {
        DeviceType.TV: "TV",
        DeviceType.AC: "Air Conditioner",
        DeviceType.FAN: "Fan",
        DeviceType.SOUNDBAR: "Soundbar",
        DeviceType.PROJECTOR: "Projector",
        DeviceType.OTHER: "IR Device",
    }.get(device_type, "IR Device")
