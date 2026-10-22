"""Light entity platform for HAIR."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
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
from .send_follow import mapped_keys, power_after
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

    entities: dict[str, HAIRLightEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.LIGHT:
            return
        if device.id in entities:
            return
        entity = HAIRLightEntity(device, device_manager)
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
        "light", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("light", async_add_entities)
    # A typed Remote's own light (heard state, round 2a).
    register_remote_platform(
        hass, entry.entry_id, "light", async_add_entities, HAIRRemoteLightEntity
    )

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRLightEntity(RestoreEntity, LightEntity):
    """IR-controlled light."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_light"
        self._attr_name = None
        self._init_state()
        # Power monitoring (Device Settings, 0.9.8). None until
        # async_added_to_hass connects; None again after removal.
        self._power_verdict_unsub: CALLBACK_TYPE | None = None
        # What HAIR sends from anywhere else (heard state, round 1).
        self._device_sent_unsub: CALLBACK_TYPE | None = None

    def _init_state(self) -> None:
        """The assumed state before any restore or press."""
        self._is_on = False

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
            "model": self._device.model or "Light",
        }

    @property
    def color_mode(self) -> ColorMode:
        mapping = self._entity_config.command_mapping
        if "brightness_up" in mapping or "brightness_down" in mapping:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        return {self.color_mode}

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_added_to_hass(self) -> None:
        await self._async_restore_state()
        self._power_verdict_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_POWER_VERDICT, self._handle_power_verdict
        )
        # The entity follows what HAIR sends, as climate has since GH
        # #105, layered UNDER the power verdict above.
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
        """
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

    @callback
    def _handle_power_verdict(self, device_id: str, verdict: PowerVerdict) -> None:
        """Apply a power_monitor.py verdict to assumed state.

        Bookkeeping only -- NEVER sends IR. "off" catches up with a
        physical-remote-off; "on" catches up with a physical-remote-on.
        A plain on/off light has nothing else to restore.
        """
        if device_id != self._device.id:
            return
        self._is_on = verdict == "on"
        self.async_write_ha_state()

    @callback
    def _handle_device_sent(self, sent: DeviceSent) -> None:
        """Follow a landed send from anywhere in HAIR but this entity:
        on, off or flipped, as ``send_follow.power_after`` decides.
        This entity tracks no brightness, so a brightness key moves
        nothing."""
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
        power = power_after(keys, self._is_on)
        if power is not None and power != self._is_on:
            self._is_on = power
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send("turn_on", "power_toggle")
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off", "power_toggle")
        self._is_on = False
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
                # send-follow handler must skip this send, or a
                # power_toggle would apply twice and undo itself.
                await self._manager.async_send_command(
                    self._device.id, command.id, origin=ORIGIN_ENTITY
                )
                return
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )


class HAIRRemoteLightEntity(RemoteStateMixin, HAIRLightEntity):
    """A typed Remote's light (heard state, round 2a).

    Every state rule, setter, feature and restore is HAIRLightEntity's; the
    mixin makes it read the Remote's own mapping, follow the Remote's
    own presses, and send nothing.
    """

    _remote_platform = "light"
