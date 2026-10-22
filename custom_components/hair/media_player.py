"""Media player entity platform for HAIR."""
from __future__ import annotations

import contextlib
import logging
from typing import Any

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
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
from .models import EntityConfig, IRDevice
from .power_monitor import SIGNAL_POWER_VERDICT, PowerVerdict
from .remote_state import RemoteStateMixin, register_remote_platform
from .send_follow import mapped_keys, one_of, power_after
from .send_signal import ORIGIN_ENTITY, SIGNAL_DEVICE_SENT, DeviceSent

_LOGGER = logging.getLogger(__name__)

#: The stored states that mean the set was on. Playback itself is not
#: restored (HAIR cannot know it still holds), only that it was on.
# The stored states that restore as ON. These are MediaPlayerState's
# string values (a StrEnum, so a stored state compares equal to them).
_RESTORES_ON = frozenset({STATE_ON, "playing", "paused", "idle", "buffering"})


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
    # A typed Remote's own media player (heard state, round 2a).
    register_remote_platform(
        hass, entry.entry_id, "media_player", async_add_entities, HAIRRemoteMediaPlayerEntity
    )

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
        self._init_state()
        # Power monitoring (Device Settings, 0.9.8). None until
        # async_added_to_hass connects; None again after removal.
        self._power_verdict_unsub: CALLBACK_TYPE | None = None
        # What HAIR sends from anywhere else (heard state, round 1).
        self._device_sent_unsub: CALLBACK_TYPE | None = None

    def _init_state(self) -> None:
        """The assumed state before any restore or press."""
        self._state = MediaPlayerState.OFF
        self._volume_level = 0.5
        self._is_muted = False

    @property
    def _entity_config(self) -> EntityConfig:
        """Where this entity reads its mapping and settings (round 2a).

        A typed Remote's entity subclasses this class and answers with
        the Remote's own config (``remote_state.RemoteStateMixin``).
        """
        return self._device.entity_config

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
        mapping = self._entity_config.command_mapping

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
        # The entity follows what HAIR sends, as climate has since GH
        # #105: a button entity, remote.send_command, a panel send or a
        # pinned Remote's retransmit. Layered UNDER the power verdict
        # above: a send is belief, the plug is evidence.
        self._device_sent_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_SENT, self._handle_device_sent
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._power_verdict_unsub is not None:
            self._power_verdict_unsub()
            self._power_verdict_unsub = None
        if self._device_sent_unsub is not None:
            self._device_sent_unsub()
            self._device_sent_unsub = None

    async def _async_restore_state(self) -> None:
        """Reboot survival (Device Settings, 0.9.8). Seeds assumed
        state from the entity's state before this restart -- the power
        monitor's STARTUP SEED (power_monitor.py, commit 2) corrects it
        immediately after if a sensor is configured, so restore only
        has to get close.

        PLAYBACK STATE STAYS CLAMPED to plain ON/OFF, like the verdict
        handler: HAIR has no way to know whether a restored PLAYING/
        PAUSED/IDLE state still holds, so it isn't restored. But every
        one of those says the set was ON, so it restores as ON (owner
        ruling 2026-10-21, heard state round 1). Before, only a literal
        "on" did, and once sends moved the entity into PLAYING or
        PAUSED, a restart turned a playing TV "off". Off, standby,
        unknown and unavailable restore as OFF, as before.

        VOLUME AND MUTE ADDED 2026-08-23 (state-restore-audit.md, GH
        #115). They were dropped by the same 0.9.8 scoping rule that
        caught fan's percentage -- "on/off platforms restore is_on" --
        without a comment naming it here.

        The reasoning is not the same as playback's, which is why they
        move and playback does not. A stepped IR volume is a guess
        either way, but 0.5 is a WORSE guess than the last value this
        entity actually held: the default is a number nobody chose,
        while the stored one is at least where the user left it. Mute
        is worse still -- flipping silently to false across a restart
        is the kind of thing that gets blamed on the TV.

        Same type tolerance as fan: a missing, None or unconvertible
        value falls back to __init__'s default rather than raising, so
        a pre-fix stored state behaves exactly as it does today.
        """
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        self._state = (
            MediaPlayerState.ON
            if last_state.state in _RESTORES_ON
            else MediaPlayerState.OFF
        )

        volume = last_state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)
        if volume is not None:
            with contextlib.suppress(TypeError, ValueError):
                self._volume_level = max(0.0, min(1.0, float(volume)))

        muted = last_state.attributes.get(ATTR_MEDIA_VOLUME_MUTED)
        if muted is not None:
            self._is_muted = bool(muted)

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

    @callback
    def _handle_device_sent(self, sent: DeviceSent) -> None:
        """Follow a landed send from anywhere in HAIR but this entity.

        Lands where this entity's own setter for the same key would
        have: on, off, a 0.05 volume step, mute flipped, PLAYING,
        PAUSED or IDLE. Rules for a command mapped to several keys are
        in ``send_follow``.
        """
        if sent.device_id != self._device.id or sent.origin == ORIGIN_ENTITY:
            return
        keys = mapped_keys(self._device, sent)
        if keys:
            self._apply_keys(keys)

    @callback
    def _apply_keys(self, keys: frozenset[str]) -> None:
        """Apply the keys one command carries, and write if anything moved.

        Shared by a Device's sends and a typed Remote's presses.
        """
        before = (self._state, self._volume_level, self._is_muted)
        power = power_after(keys, self._state != MediaPlayerState.OFF)
        if power is not None:
            self._state = MediaPlayerState.ON if power else MediaPlayerState.OFF
        if self._state != MediaPlayerState.OFF:
            if "play" in keys and "pause" in keys and "stop" not in keys:
                # One Play/Pause button.
                self._state = (
                    MediaPlayerState.PAUSED
                    if self._state == MediaPlayerState.PLAYING
                    else MediaPlayerState.PLAYING
                )
            else:
                playback = one_of(keys, "play", "pause", "stop")
                if playback is not None:
                    self._state = {
                        "play": MediaPlayerState.PLAYING,
                        "pause": MediaPlayerState.PAUSED,
                        "stop": MediaPlayerState.IDLE,
                    }[playback]
        step = one_of(keys, "volume_up", "volume_down")
        if step is not None and self._volume_level is not None:
            delta = 0.05 if step == "volume_up" else -0.05
            self._volume_level = max(0.0, min(1.0, self._volume_level + delta))
        if "mute" in keys:
            self._is_muted = not self._is_muted
        if (self._state, self._volume_level, self._is_muted) != before:
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
        mapping = self._entity_config.command_mapping
        for key in feature_keys:
            command_name = mapping.get(key)
            if command_name is None:
                continue
            command = self._device.get_command_by_name(command_name)
            if command is not None:
                # ORIGIN_ENTITY: the setter writes its own state, so the
                # send-follow handler above must skip this send, or a
                # power_toggle would turn the TV on and straight off.
                await self._manager.async_send_command(
                    self._device.id, command.id, origin=ORIGIN_ENTITY
                )
                return
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )


class HAIRRemoteMediaPlayerEntity(RemoteStateMixin, HAIRMediaPlayerEntity):
    """A typed Remote's media player (heard state, round 2a).

    Every state rule, setter, feature and restore is HAIRMediaPlayerEntity's; the
    mixin makes it read the Remote's own mapping, follow the Remote's
    own presses, and send nothing.
    """

    _remote_platform = "media_player"
