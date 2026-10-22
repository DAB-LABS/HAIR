"""Fan entity platform for HAIR."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
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
from .models import SPEED_CYCLE_TURN_ON_SPEED_1, EntityConfig, IRDevice, TriggerRemote
from .power_monitor import SIGNAL_POWER_VERDICT, PowerVerdict
from .remote_state import RemoteStateMixin, register_remote_platform
from .send_follow import SPEED_CYCLE, cycle_step, mapped_keys, one_of, power_after
from .send_signal import ORIGIN_ENTITY, SIGNAL_DEVICE_SENT, DeviceSent

_LOGGER = logging.getLogger(__name__)

SPEED_COUNT = 10
SPEED_KEYS = [f"speed_{i}" for i in range(1, SPEED_COUNT + 1)]

# Fan speed cycle (GH Discussion #201): the pause between two separate
# presses of the cycle button, so the fan reads two presses rather than
# one held button. Not IRCommand.send_spacing_ms, which spaces the
# repeats INSIDE one send. Half a second is a brisk human pace.
SPEED_CYCLE_PRESS_GAP_S = 0.5
_POWER_ON_KEYS = ("turn_on", "power_toggle")
_POWER_OFF_KEYS = ("turn_off", "power_toggle")


def cycle_presses(position: int, target: int, length: int) -> int:
    """Presses of the cycle button from ``position`` to ``target`` on a
    cycle of ``length`` positions. The button only goes forward."""
    return (target - position) % length


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
    # A typed Remote's own fan (heard state, round 2a).
    register_remote_platform(
        hass, entry.entry_id, "fan", async_add_entities, HAIRRemoteFanEntity
    )

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
        self._init_state()
        # Power monitoring (Device Settings, 0.9.8). None until
        # async_added_to_hass connects; None again after removal.
        self._power_verdict_unsub: CALLBACK_TYPE | None = None
        # What HAIR sends from anywhere else (heard state, round 1).
        self._device_sent_unsub: CALLBACK_TYPE | None = None

    def _init_state(self) -> None:
        """The assumed state before any restore or press.

        The speed cycle's bookkeeping lives here too, so a typed Remote's
        fan (which builds itself through ``RemoteStateMixin`` rather
        than this ``__init__``) counts its cycle presses the same way.
        """
        self._is_on = False
        self._percentage: int | None = None
        self._oscillating: bool = False
        # Speed cycle (GH Discussion #201). ``_cycle_pos`` is HAIR's own
        # count of where the fan is: 0 = off when off is in the cycle,
        # else 0 = speed 1. It is derived from on/off and the
        # percentage, so the existing restore carries it. The target
        # is re-read before every press, so a new one arriving
        # mid-burst redirects the burst instead of queuing another.
        self._cycle_pos = 0
        self._cycle_target: int | None = None
        self._cycle_lock = asyncio.Lock()
        self._last_press_at: float | None = None
        self._cycle_shape = self._current_cycle_shape()

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Fan",
        }

    @property
    def _entity_config(self) -> EntityConfig:
        """The settings this entity runs on. Every read goes through
        here, so a Remote typed as a fan can supply its own."""
        return self._device.entity_config

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        mapping = self._entity_config.command_mapping
        if (
            "speed_up" in mapping
            or "speed_down" in mapping
            or self._mapped_speed_steps(mapping)
            or self._cycle_speeds() is not None
        ):
            features |= FanEntityFeature.SET_SPEED
        if "oscillate" in mapping:
            features |= FanEntityFeature.OSCILLATE
        return features

    @property
    def speed_count(self) -> int:
        mapping = self._entity_config.command_mapping
        return (
            len(self._mapped_speed_steps(mapping))
            or self._cycle_speeds()
            or SPEED_COUNT
        )

    @staticmethod
    def _mapped_speed_steps(mapping: dict[str, str]) -> list[str]:
        return [key for key in SPEED_KEYS if key in mapping]

    # --- Speed cycle: the count -------------------------------------

    def _cycle_speeds(self) -> int | None:
        """N, the number of speeds, when the cycle drives the speed:
        ``speed_cycle`` mapped, ``fan_speed_steps`` set, and no
        discrete ``speed_N`` key mapped (those win). Else None."""
        config = self._entity_config
        mapping = config.command_mapping
        if not mapping.get(SPEED_CYCLE) or self._mapped_speed_steps(mapping):
            return None
        return config.fan_speed_steps

    def _cycle_has_off(self) -> bool:
        return self._entity_config.speed_cycle_includes_off

    def _cycle_length(self, speeds: int) -> int:
        """M: the positions the button steps through."""
        return speeds + 1 if self._cycle_has_off() else speeds

    def _current_cycle_shape(self) -> tuple:
        config = self._entity_config
        return (
            self._cycle_speeds(),
            config.speed_cycle_includes_off,
            config.speed_cycle_turn_on,
        )

    def _derive_cycle_pos(self) -> int:
        """The position on/off and the percentage describe. Off lands
        on the turn-on choice, the same as turning the fan off does."""
        speeds = self._cycle_speeds()
        if speeds is None:
            return 0
        has_off = self._cycle_has_off()
        if has_off and not self._is_on:
            return 0
        speed = 1
        if self._percentage:
            speed = percentage_to_ordered_list_item(
                list(range(1, speeds + 1)), self._percentage
            )
        if (
            not self._is_on
            and self._entity_config.speed_cycle_turn_on
            == SPEED_CYCLE_TURN_ON_SPEED_1
        ):
            speed = 1
        return speed if has_off else speed - 1

    def _show_cycle_pos(self, position: int) -> None:
        """Write on/off and the percentage for a cycle position."""
        speeds = self._cycle_speeds()
        if speeds is None:
            return
        position %= self._cycle_length(speeds)
        speed = position if self._cycle_has_off() else position + 1
        if speed == 0:
            self._is_on = False
            return
        self._is_on = True
        self._percentage = ordered_list_item_to_percentage(
            list(range(1, speeds + 1)), speed
        )

    def _cycle_rezero(self) -> None:
        """The fan went off: the count goes where it will be when the
        fan comes back on. That is what makes off-then-on a resync."""
        speeds = self._cycle_speeds()
        if speeds is None:
            return
        if self._cycle_has_off():
            self._cycle_pos = 0
        elif self._entity_config.speed_cycle_turn_on == SPEED_CYCLE_TURN_ON_SPEED_1:
            self._cycle_pos = 0
            self._percentage = ordered_list_item_to_percentage(
                list(range(1, speeds + 1)), 1
            )

    def _cycle_powered_on(self) -> None:
        """The fan came on by something other than the cycle button (a
        power key sent elsewhere, a sensor's "on"). Without off in the
        cycle the count already sits on the turn-on choice; with it, a
        count still on off moves to the speed the percentage shows."""
        if self._cycle_has_off() and self._cycle_pos == 0:
            self._cycle_pos = self._derive_cycle_pos()

    def _follow_cycle(self, keys: frozenset[str]) -> bool:
        """A cycle press sent from anywhere else: a HAIR button,
        ``remote.send_command``, a pinned Remote's re-send. One step on,
        wrapping. From off, without off in the cycle, the fan wakes on
        its turn-on choice without stepping (owner, 2026-10-22).
        Returns whether the press moved anything."""
        if SPEED_CYCLE not in keys:
            return False
        speeds = self._cycle_speeds()
        if speeds is None:
            return False
        if not self._is_on and not self._cycle_has_off():
            self._show_cycle_pos(self._cycle_pos)
            return True
        self._cycle_pos = cycle_step(self._cycle_pos, self._cycle_length(speeds))
        self._show_cycle_pos(self._cycle_pos)
        return True

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

        # The speed cycle's count rides the percentage.
        self._cycle_pos = self._derive_cycle_pos()

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
        if self._is_on:
            self._cycle_powered_on()
        else:
            self._cycle_rezero()
        self.async_write_ha_state()

    @callback
    def _handle_device_sent(self, sent: DeviceSent) -> None:
        """Follow a landed send from anywhere in HAIR but this entity.

        Lands where this entity's own setter for the same key would
        have: on, off, a ``speed_N`` step's percentage (and on), a 25
        step up or down, oscillation flipped. Rules for a command mapped
        to several keys are in ``send_follow``.
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
        before = (self._is_on, self._percentage, self._oscillating)
        moved = False
        power = power_after(keys, self._is_on)
        if power is not None:
            self._is_on = power
            if power:
                self._cycle_powered_on()
            else:
                self._cycle_rezero()
        mapping = self._entity_config.command_mapping
        steps = self._mapped_speed_steps(mapping)
        speed = one_of(keys, *steps) if steps else None
        if speed is not None and power is not False:
            self._percentage = ordered_list_item_to_percentage(steps, speed)
            self._is_on = True
        step = one_of(keys, "speed_up", "speed_down")
        if step is not None:
            delta = 25 if step == "speed_up" else -25
            self._percentage = max(0, min(100, (self._percentage or 0) + delta))
        if "oscillate" in keys:
            self._oscillating = not self._oscillating
        if power is not False:
            moved = self._follow_cycle(keys)
        if moved or (self._is_on, self._percentage, self._oscillating) != before:
            self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        speeds = self._cycle_speeds()
        if speeds is not None:
            await self._cycle_turn_on(percentage, speeds)
            return
        await self._send("turn_on", "power_toggle")
        self._is_on = True
        if percentage is not None:
            self._percentage = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._cycle_speeds() is not None:
            await self._cycle_turn_off()
            return
        await self._send("turn_off", "power_toggle")
        self._is_on = False
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        speeds = self._cycle_speeds()
        if speeds is not None:
            await self._cycle_set_percentage(percentage, speeds)
            return
        mapping = self._entity_config.command_mapping
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

    # --- Speed cycle: pressing ------------------------------------------

    def _has_mapped(self, keys: tuple[str, ...]) -> bool:
        mapping = self._entity_config.command_mapping
        return any(mapping.get(key) for key in keys)

    async def _cycle_set_percentage(self, percentage: int, speeds: int) -> None:
        has_off = self._cycle_has_off()
        if percentage <= 0:
            if has_off:
                await self._cycle_run(0, wake=False)
            else:
                await self._cycle_turn_off()
            return
        speed = percentage_to_ordered_list_item(
            list(range(1, speeds + 1)), percentage
        )
        target = speed if has_off else speed - 1
        # Without off in the cycle, an off fan is woken first, by its
        # power key or one press of the cycle button, onto its turn-on
        # choice; with off in it, the presses from 0 wake it.
        wake = not self._is_on and not has_off
        await self._cycle_run(target, wake=wake)

    async def _cycle_turn_on(self, percentage: int | None, speeds: int) -> None:
        if percentage is not None:
            await self._cycle_set_percentage(percentage, speeds)
            return
        if self._is_on:
            self.async_write_ha_state()
            return
        if self._cycle_has_off() and not self._has_mapped(_POWER_ON_KEYS):
            await self._cycle_run(1, wake=False)
            return
        await self._cycle_run(None, wake=True)

    async def _cycle_turn_off(self) -> None:
        if not self._has_mapped(_POWER_OFF_KEYS) and self._cycle_has_off():
            await self._cycle_run(0, wake=False)
            return
        # Stops a running burst at its next press.
        self._cycle_target = None
        async with self._cycle_lock:
            await self._press(*_POWER_OFF_KEYS)
            self._is_on = False
            self._cycle_rezero()
            self.async_write_ha_state()

    async def _cycle_run(self, target: int | None, *, wake: bool) -> None:
        """Drive the cycle to ``target`` (None: only wake the fan).

        The believed speed is written at once; the presses follow one
        at a time under the lock. A caller arriving mid-burst sets the
        target and waits: the running burst picks the new target up at
        its next press, and the waiter finds nothing left to do.
        """
        if target is not None:
            self._cycle_target = target
            self._show_cycle_pos(target)
        if wake:
            self._is_on = True
        self.async_write_ha_state()
        async with self._cycle_lock:
            awake = not wake
            try:
                if wake:
                    awake = await self._cycle_wake()
                if awake:
                    await self._press_to_target()
            finally:
                # Whatever happened, show where the presses really got.
                self._show_cycle_pos(self._cycle_pos)
                if not awake:
                    self._is_on = False
                self.async_write_ha_state()

    async def _cycle_wake(self) -> bool:
        """Turn an off fan on, landing where the count says. With off
        in the cycle the power key lands on speed 1, which is where the
        cycle button's next press would go."""
        if self._has_mapped(_POWER_ON_KEYS):
            sent = await self._press(*_POWER_ON_KEYS)
            if sent and self._cycle_has_off():
                self._cycle_pos = 1
        else:
            sent = await self._press(SPEED_CYCLE)
        if sent:
            self._is_on = True
        return sent

    def _presses_left(self) -> int:
        speeds = self._cycle_speeds()
        target = self._cycle_target
        if speeds is None or target is None:
            return 0
        return cycle_presses(self._cycle_pos, target, self._cycle_length(speeds))

    async def _press_to_target(self) -> None:
        """Press until the count reaches the target. The target is read
        again after each gap, so the press that follows is always for
        the newest one."""
        while self._presses_left():
            await self._press_gap()
            if not self._presses_left():
                return
            speeds = self._cycle_speeds()
            if not await self._send_press(SPEED_CYCLE):
                return
            self._cycle_pos = cycle_step(self._cycle_pos, self._cycle_length(speeds))

    async def _press(self, *feature_keys: str) -> bool:
        """One separate press, at least the gap after the last one."""
        await self._press_gap()
        return await self._send_press(*feature_keys)

    async def _press_gap(self) -> None:
        if self._last_press_at is None:
            return
        wait = self._last_press_at + SPEED_CYCLE_PRESS_GAP_S - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)

    async def _send_press(self, *feature_keys: str) -> bool:
        try:
            return await self._send(*feature_keys)
        finally:
            self._last_press_at = time.monotonic()

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        shape = self._current_cycle_shape()
        if shape != self._cycle_shape:
            # New cycle settings: re-read the count from what is shown.
            self._cycle_shape = shape
            self._cycle_pos = self._derive_cycle_pos()
        if self.hass is None:
            # Race: entity instantiated and tracked in the platform's local
            # dict but not yet registered with HA via async_add_entities.
            # The state from __init__ is correct; HA writes it once the
            # registration coroutine completes.
            return
        self.async_write_ha_state()

    async def _send(self, *feature_keys: str) -> bool:
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
                return True
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
        return False


class HAIRRemoteFanEntity(RemoteStateMixin, HAIRFanEntity):
    """A typed Remote's fan (heard state, round 2a).

    Every state rule, setter, feature and restore is HAIRFanEntity's; the
    mixin makes it read the Remote's own mapping and settings, follow the
    Remote's own presses, and send nothing. The speed cycle comes with
    it: a heard cycle press steps the Remote's own count, and with the
    Remote's own ``fan_speed_steps`` set the speed can be set by hand.
    """

    _remote_platform = "fan"

    async def _press_gap(self) -> None:
        """No gap: a Remote's presses go nowhere, so there is no fan to
        give time between them. Setting a speed lands at once."""

    @callback
    def update_remote(self, remote: TriggerRemote) -> None:
        """New cycle settings re-read the count from what is shown, as a
        Device's ``update_device`` does."""
        self._remote = remote
        shape = self._current_cycle_shape()
        if shape != self._cycle_shape:
            self._cycle_shape = shape
            self._cycle_pos = self._derive_cycle_pos()
        super().update_remote(remote)
