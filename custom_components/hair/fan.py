"""Fan entity platform for HAIR."""
from __future__ import annotations

import contextlib
import logging
from typing import Any

from homeassistant.components.fan import (
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, DeviceType
from .models import IRDevice
from .power_monitor import SIGNAL_POWER_VERDICT, PowerVerdict

_LOGGER = logging.getLogger(__name__)

SPEED_COUNT = 10
SPEED_KEYS = [f"speed_{i}" for i in range(1, SPEED_COUNT + 1)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRFanEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.FAN:
            return
        if device.id in entities:
            return
        entity = HAIRFanEntity(device, device_manager)
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
        "fan", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("fan", async_add_entities)

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRFanEntity(RestoreEntity, FanEntity):
    """IR-controlled fan."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_fan"
        self._attr_name = None
        self._is_on = False
        self._percentage: int | None = None
        self._oscillating: bool = False
        # Power monitoring (Device Settings, 0.9.8). None until
        # async_added_to_hass connects; None again after removal.
        self._power_verdict_unsub: CALLBACK_TYPE | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Fan",
        }

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        mapping = self._device.entity_config.command_mapping
        if "speed_up" in mapping or "speed_down" in mapping or self._mapped_speed_steps(mapping):
            features |= FanEntityFeature.SET_SPEED
        if "oscillate" in mapping:
            features |= FanEntityFeature.OSCILLATE
        return features

    @property
    def speed_count(self) -> int:
        mapping = self._device.entity_config.command_mapping
        return len(self._mapped_speed_steps(mapping)) or SPEED_COUNT

    @staticmethod
    def _mapped_speed_steps(mapping: dict[str, str]) -> list[str]:
        return [key for key in SPEED_KEYS if key in mapping]

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def percentage(self) -> int | None:
        return self._percentage

    @property
    def oscillating(self) -> bool:
        return self._oscillating

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
        """Reboot survival (Device Settings, 0.9.8). Seeds assumed
        state from the entity's state before this restart -- the power
        monitor's STARTUP SEED (power_monitor.py, commit 2) corrects it
        immediately after if a sensor is configured, so restore only
        has to get close.

        SCOPE WIDENED 2026-08-23 (state-restore-audit.md, GH #115).
        Percentage and oscillation used to be scoped out here, citing
        the 0.9.8 coding plan's "on/off platforms restore is_on". That
        was a real decision for a release whose only job was making
        power survive, and it is stale: a fan that comes back on at no
        speed and not oscillating looks broken in a way "off" does not,
        which is exactly what #115 reported.

        Two things settle it beyond the user report. Both values are
        already sitting in ``last_state.attributes`` -- this is a read,
        not new bookkeeping, and it is the same shape climate.py has
        always used for fan and swing. And the power-verdict handler
        below already assumes they survive, in as many words: it says
        an "on" verdict restores speed and oscillation for free. That
        was only ever true mid-session; now it is true after a restart
        too, and the file agrees with itself.

        Type-tolerant on purpose. A missing attribute, a None, or
        anything that will not convert falls back to __init__'s default
        rather than raising: a pre-fix stored state carries neither
        attribute, and a restore block that raises on a stale snapshot
        takes the whole entity down with it.
        """
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        self._is_on = last_state.state == STATE_ON

        percentage = last_state.attributes.get(ATTR_PERCENTAGE)
        if percentage is not None:
            with contextlib.suppress(TypeError, ValueError):
                self._percentage = max(0, min(100, int(percentage)))

        oscillating = last_state.attributes.get(ATTR_OSCILLATING)
        if oscillating is not None:
            self._oscillating = bool(oscillating)

    @callback
    def _handle_power_verdict(self, device_id: str, verdict: PowerVerdict) -> None:
        """Apply a power_monitor.py verdict to assumed state.

        Bookkeeping only -- NEVER sends IR. "off" catches up with a
        physical-remote-off; "on" catches up with a physical-remote-on,
        restoring speed and oscillation for free since neither is ever
        cleared on off (they're just not displayed as active).
        """
        if device_id != self._device.id:
            return
        self._is_on = verdict == "on"
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self._send("turn_on", "power_toggle")
        self._is_on = True
        if percentage is not None:
            self._percentage = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off", "power_toggle")
        self._is_on = False
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        mapping = self._device.entity_config.command_mapping
        speed_steps = self._mapped_speed_steps(mapping)
        if speed_steps:
            if percentage == 0:
                await self.async_turn_off()
                return
            step = percentage_to_ordered_list_item(speed_steps, percentage)
            await self._send(step)
            self._percentage = ordered_list_item_to_percentage(speed_steps, step)
            self.async_write_ha_state()
            return

        target = percentage
        current = self._percentage or 0
        # Step toward target using speed_up / speed_down.
        delta = target - current
        if delta > 0:
            steps = max(1, delta // 25)
            for _ in range(steps):
                if not await self._send("speed_up"):
                    break
        elif delta < 0:
            steps = max(1, abs(delta) // 25)
            for _ in range(steps):
                if not await self._send("speed_down"):
                    break
        self._percentage = target
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        await self._send("oscillate")
        self._oscillating = oscillating
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

    async def _send(self, *feature_keys: str) -> bool:
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
                return True
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
        return False
