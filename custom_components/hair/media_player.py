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
from homeassistant.const import STATE_ON
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DeviceType
from .models import IRDevice
from .power_monitor import SIGNAL_POWER_VERDICT, PowerVerdict

_LOGGER = logging.getLogger(__name__)


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
        if device.device_type != DeviceType.MEDIA_PLAYER:
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


class HAIRMediaPlayerEntity(RestoreEntity, MediaPlayerEntity):
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
        # Power monitoring (Device Settings, v0.9.9). None until
        # async_added_to_hass connects; None again after removal.
        self._power_verdict_unsub: CALLBACK_TYPE | None = None

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
        if "play" in mapping:
            features |= MediaPlayerEntityFeature.PLAY
        if "pause" in mapping:
            features |= MediaPlayerEntityFeature.PAUSE
        if "stop" in mapping:
            features |= MediaPlayerEntityFeature.STOP

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

    async def async_added_to_hass(self) -> None:
        await self._async_restore_state()
        self._power_verdict_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_POWER_VERDICT, self._handle_power_verdict
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._power_verdict_unsub is not None:
            self._power_verdict_unsub()
            self._power_verdict_unsub = None

    async def _async_restore_state(self) -> None:
        """Reboot survival (Device Settings, v0.9.9). Seeds assumed
        state from the entity's state before this restart -- the power
        monitor's STARTUP SEED (power_monitor.py, commit 2) corrects it
        immediately after if a sensor is configured, so restore only
        has to get close. Clamped to plain ON/OFF like the verdict
        handler: HAIR has no way to know whether a restored PLAYING/
        PAUSED/IDLE state still holds, so it isn't restored.
        """
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._state = (
                MediaPlayerState.ON
                if last_state.state == STATE_ON
                else MediaPlayerState.OFF
            )

    @callback
    def _handle_power_verdict(self, device_id: str, verdict: PowerVerdict) -> None:
        """Apply a power_monitor.py verdict to assumed state.

        Bookkeeping only -- NEVER sends IR. Lands on the plain ON/OFF
        states (design doc: "media_player: on"), not a guess at
        playing/paused -- HAIR has no way to know what the physical
        remote resumed.
        """
        if device_id != self._device.id:
            return
        self._state = MediaPlayerState.ON if verdict == "on" else MediaPlayerState.OFF
        self.async_write_ha_state()

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

    async def async_media_play(self) -> None:
        await self._send("play")
        self._state = MediaPlayerState.PLAYING
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        await self._send("pause")
        self._state = MediaPlayerState.PAUSED
        self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        await self._send("stop")
        self._state = MediaPlayerState.IDLE
        self.async_write_ha_state()

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        if self.hass is None:
            # Race: entity instantiated and tracked in the platform's local
            # dict but not yet registered with HA via async_add_entities.
            # The state from __init__ is correct; HA writes it once the
            # registration coroutine completes.
            return
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
