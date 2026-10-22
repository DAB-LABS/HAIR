"""Cover entity platform for HAIR."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_CLOSED, STATE_OPEN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DeviceType
from .models import EntityConfig, IRDevice
from .remote_state import RemoteStateMixin, register_remote_platform
from .send_follow import mapped_keys, one_of
from .send_signal import ORIGIN_ENTITY, SIGNAL_DEVICE_SENT, DeviceSent

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRCoverEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.SCREEN:
            return
        if device.id in entities:
            return
        entity = HAIRCoverEntity(device, device_manager)
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
        "cover", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("cover", async_add_entities)
    # A typed Remote's own screen (heard state, round 2a).
    register_remote_platform(
        hass, entry.entry_id, "cover", async_add_entities, HAIRRemoteCoverEntity
    )

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRCoverEntity(RestoreEntity, CoverEntity):
    """IR-controlled cover (projector screen, shade, etc.)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_device_class = CoverDeviceClass.SHADE

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_cover"
        self._attr_name = None
        self._init_state()
        # What HAIR sends from anywhere else (heard state, round 1).
        self._device_sent_unsub: CALLBACK_TYPE | None = None

    def _init_state(self) -> None:
        """The assumed state before any restore or press."""
        self._is_closed: bool | None = None

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
            "model": self._device.model or "Screen / Shade",
        }

    @property
    def supported_features(self) -> CoverEntityFeature:
        features = CoverEntityFeature(0)
        mapping = self._entity_config.command_mapping
        if "open_cover" in mapping:
            features |= CoverEntityFeature.OPEN
        if "close_cover" in mapping:
            features |= CoverEntityFeature.CLOSE
        if "stop_cover" in mapping:
            features |= CoverEntityFeature.STOP
        return features

    @property
    def is_closed(self) -> bool | None:
        return self._is_closed

    async def async_added_to_hass(self) -> None:
        await self._async_restore_state()
        # The entity follows what HAIR sends, as climate has since GH
        # #105. There is still no power-verdict subscription here (see
        # the restore docstring below); this is the send side only.
        self._device_sent_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_SENT, self._handle_device_sent
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._device_sent_unsub is not None:
            self._device_sent_unsub()
            self._device_sent_unsub = None

    async def _async_restore_state(self) -> None:
        """Reboot survival (restore completeness, 2026-08-23).

        Cover was the one platform the 0.9.8 scoping rule missed
        outright. That rule said "on/off platforms restore is_on", which
        reads as though it covers the field; a cover has `is_closed`
        rather than `is_on` and is not climate, so it fell through and
        never got `RestoreEntity` at all. The audit
        (`state-restore-audit.md`, section 2a) found the hole from both
        ends: the entity came back `unknown` from both closed AND open,
        and `core.restore_state` held no entry for it, because a
        non-RestoreEntity never writes one.

        Unknown is worse than stale here. A stale cover still draws on a
        dashboard and still templates; an unknown one shows nothing and
        breaks any automation reading `is_closed`.

        Only the two states this platform can actually be in are
        restored. Anything else -- `unknown`, `unavailable`, a state
        from some other integration's history -- leaves `_is_closed`
        None, which is the honest reading of "no evidence".

        NO POWER-VERDICT SUBSCRIPTION, deliberately (owner ruling
        2026-08-23). The other five platforms subscribe to
        SIGNAL_POWER_VERDICT so a configured sensor can correct their
        assumed state; cover does not, because a screen wired to a power
        sensor is a corner case not worth the wiring. The asymmetry is a
        decision, not the same oversight repeating.
        """
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        if last_state.state == STATE_CLOSED:
            self._is_closed = True
        elif last_state.state == STATE_OPEN:
            self._is_closed = False

    @callback
    def _handle_device_sent(self, sent: DeviceSent) -> None:
        """Follow a landed send from anywhere in HAIR but this entity:
        open or closed, as this entity's own setters land. ``stop_cover``
        moves nothing, and a command mapped to both open and close is a
        contradiction that moves nothing either."""
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
        move = one_of(keys, "open_cover", "close_cover")
        if move is None:
            return
        closed = move == "close_cover"
        if self._is_closed != closed:
            self._is_closed = closed
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._send("open_cover")
        self._is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._send("close_cover")
        self._is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._send("stop_cover")
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
                # send-follow handler must skip this send.
                await self._manager.async_send_command(
                    self._device.id, command.id, origin=ORIGIN_ENTITY
                )
                return
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )


class HAIRRemoteCoverEntity(RemoteStateMixin, HAIRCoverEntity):
    """A typed Remote's screen (heard state, round 2a).

    Every state rule, setter, feature and restore is HAIRCoverEntity's; the
    mixin makes it read the Remote's own mapping, follow the Remote's
    own presses, and send nothing.
    """

    _remote_platform = "cover"
