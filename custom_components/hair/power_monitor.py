"""Power-sensor based state correction for HAIR entities.

IR is one-way: a HAIR entity's on/off state is an ASSUMPTION based on the
last command sent. A configured power sensor is the first real feedback
loop -- somebody turns a device off with its physical remote, the sensed
draw goes away, and this module tells the entity to correct itself
instead of lying until the next HAIR send.

Owns one ``async_track_state_change_event`` subscription per device that
has ``power_sensor_entity_id`` configured. On each reading it classifies
the value against the device's two thresholds and, on a threshold
crossing, dispatches a verdict that platform entities apply to their
assumed state. This module knows nothing about platforms -- see
``climate.py`` / ``media_player.py`` / ``fan.py`` / ``light.py`` /
``switch.py`` for the entity-side correction (commit 3 of the device
settings + power sensor plan, ``docs/internal/plans/
device-settings-power-sensor-coding-plan.md``).

State model (owner-confirmed 2026-08-08, full detail in the design doc):
a threshold crossing OVERRIDES both the last-sent assumption and any
restored (post-reboot) state -- the sensor is evidence, assumed state is
just belief. Readings inside the hysteresis band, or an unavailable/
unknown/non-numeric sensor, hold: no correction fires either way, so a
dead plug can never turn the house off. On (re)subscribe -- startup,
reload, or the sensor setting changing -- the current reading is
evaluated immediately rather than waiting for the next state-change
event, so a device switched off while HA was down reads off within
seconds of restart.
"""
from __future__ import annotations

import logging
from typing import Literal

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .models import IRDevice
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)

# Dispatched as (device_id, verdict). One signal, not a signal-per-device
# family, mirroring SIGNAL_ADD_ENTITY's shape in entity_factory.py --
# subscribers filter on the device_id argument themselves.
SIGNAL_POWER_VERDICT = f"{DOMAIN}_power_verdict"

PowerVerdict = Literal["on", "off"]


def classify_power_reading(
    state: State | None,
    off_below_w: float | None,
    on_above_w: float | None,
) -> PowerVerdict | None:
    """Classify a power-sensor reading against a device's thresholds.

    Returns ``"off"`` at or below ``off_below_w``, ``"on"`` at or above
    ``on_above_w``, or ``None`` to hold (no correction) -- covering the
    hysteresis band itself, an unset/incomplete threshold pair,
    unavailable/unknown state, and a non-numeric reading. A ``kW``
    reading is converted to watts first so both thresholds and callers
    only ever compare in watts.
    """
    if off_below_w is None or on_above_w is None:
        return None
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None
    if state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfPower.KILO_WATT:
        value *= 1000
    if value <= off_below_w:
        return "off"
    if value >= on_above_w:
        return "on"
    return None


class PowerMonitor:
    """Tracks per-device power sensors and dispatches on/off verdicts."""

    def __init__(self, hass: HomeAssistant, store: HAIRStore) -> None:
        self._hass = hass
        self._store = store
        self._unsub: dict[str, CALLBACK_TYPE] = {}

    def start(self) -> None:
        """Subscribe every stored device that has a sensor configured.

        Must be called AFTER platform entities are set up (i.e. after
        ``async_forward_entry_setups``), since subscribing immediately
        evaluates and dispatches the sensor's current reading (the
        startup seed) -- an entity that isn't listening yet would miss
        it. ``__init__.py`` calls this right alongside
        ``SignalMonitor.async_start()``, in the same order.
        """
        for device in self._store.get_all_devices():
            self._subscribe(device)

    def stop(self) -> None:
        for unsub in self._unsub.values():
            unsub()
        self._unsub.clear()

    def rebuild_device(self, device: IRDevice) -> None:
        """Re-subscribe a single device after create/update.

        Called from ``DeviceManager`` so a sensor picked, changed, or
        cleared in the settings dialog takes effect immediately -- no
        integration reload needed. Safe to call for a device with no
        sensor configured; it simply tears down any prior subscription.
        """
        self._unsubscribe(device.id)
        self._subscribe(device)

    def remove_device(self, device_id: str) -> None:
        """Tear down a device's subscription after it is deleted."""
        self._unsubscribe(device_id)

    # -- internals ---------------------------------------------------

    def _subscribe(self, device: IRDevice) -> None:
        sensor_id = device.power_sensor_entity_id
        if not sensor_id:
            return
        device_id = device.id

        @callback
        def _on_state_change(event: Event) -> None:
            self._evaluate(device_id, event.data.get("new_state"))

        self._unsub[device_id] = async_track_state_change_event(
            self._hass, [sensor_id], _on_state_change
        )
        # Startup seed (state-model rule 4): evaluate the CURRENT
        # reading now rather than waiting for the next state change.
        self._evaluate(device_id, self._hass.states.get(sensor_id))

    def _unsubscribe(self, device_id: str) -> None:
        unsub = self._unsub.pop(device_id, None)
        if unsub is not None:
            unsub()

    def _evaluate(self, device_id: str, state: State | None) -> None:
        device = self._store.get_device(device_id)
        if device is None:
            return
        verdict = classify_power_reading(
            state, device.power_off_below_w, device.power_on_above_w
        )
        if verdict is None:
            return
        async_dispatcher_send(self._hass, SIGNAL_POWER_VERDICT, device_id, verdict)
