"""Media player entity platform for HAIR."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


MEDIA_PLAYER_DEVICE_TYPES: set[DeviceType] = {
    DeviceType.TV,
    DeviceType.SOUNDBAR,
    DeviceType.PROJECTOR,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRMediaPlayerEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type not in MEDIA_PLAYER_DEVICE_TYPES:
            return
        if device.id in entities:
            return
        entity = HAIRMediaPlayerEntity(device, device_manager)
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
        "media_player",
        on_add=_on_add,
        on_remove=_on_remove,
        on_update=_on_update,
    )
    factory.register_platform("media_player", async_add_entities)

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRMediaPlayerEntity(MediaPlayerEntity):
    """IR-controlled media player."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_media_player"
        self._attr_name = None
        self._state = MediaPlayerState.OFF
        self._volume_level = 0.5
        self._is_muted = False

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Media Player",
        }

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        features = MediaPlayerEntityFeature(0)
        mapping = self._device.entity_config.command_mapping

        if "turn_on" in mapping or "power_toggle" in mapping:
            features |= MediaPlayerEntityFeature.TURN_ON
        if "turn_off" in mapping or "power_toggle" in mapping:
            features |= MediaPlayerEntityFeature.TURN_OFF
        if "volume_up" in mapping or "volume_down" in mapping:
            features |= MediaPlayerEntityFeature.VOLUME_STEP
        if "mute" in mapping:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE
        if "select_source" in mapping:
            features |= MediaPlayerEntityFeature.SELECT_SOURCE

        return features

    @property
    def state(self) -> MediaPlayerState:
        return self._state

    @property
    def volume_level(self) -> float | None:
        return self._volume_level

    @property
    def is_volume_muted(self) -> bool | None:
        return self._is_muted

    async def async_turn_on(self) -> None:
        await self._send("turn_on", "power_toggle")
        self._state = MediaPlayerState.ON
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        await self._send("turn_off", "power_toggle")
        self._state = MediaPlayerState.OFF
        self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        await self._send("volume_up")
        if self._volume_level is not None:
            self._volume_level = min(1.0, self._volume_level + 0.05)
        self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        await self._send("volume_down")
        if self._volume_level is not None:
            self._volume_level = max(0.0, self._volume_level - 0.05)
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        await self._send("mute")
        self._is_muted = mute
        self.async_write_ha_state()

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        self.async_write_ha_state()

    async def _send(self, *feature_keys: str) -> None:
        mapping = self._device.entity_config.command_mapping
        for key in feature_keys:
            command_name = mapping.get(key)
            if command_name is None:
                continue
            command = self._device.get_command_by_name(command_name)
            if command is not None:
                await self._manager.async_send_command(
                    self._device.id, command.id
                )
                return
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
