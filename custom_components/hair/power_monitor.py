"""Power-sensor based state correction for HAIR entities.

IR is one-way: a HAIR entity's on/off state is an ASSUMPTION based on the
last command sent. A configured power sensor is the first real feedback
loop -- somebody turns a device off with its physical remote, the sensed
draw goes away, and this module tells the entity to correct itself
instead of lying until the next HAIR send.

Owns one ``async_track_state_change_event`` subscription per device that
has ``power_sensor_entity_id`` configured. On each reading it classifies
the value against the device's two thresholds and dispatches a verdict
that platform entities apply to their assumed state. A verdict is EVERY
reading outside the hysteresis gap, not only a threshold crossing: the
monitor keeps no last verdict, so a HAIR send the device never received
is still corrected by the next report. This module knows nothing about
platforms -- see ``climate.py`` / ``media_player.py`` / ``fan.py`` /
``light.py`` / ``switch.py`` for the entity-side correction (commit 3 of
the device settings + power sensor plan, ``docs/internal/plans/
device-settings-power-sensor-coding-plan.md``).

State model (owner-confirmed 2026-08-08, full detail in the design doc):
a verdict OVERRIDES both the last-sent assumption and any restored
(post-reboot) state -- the sensor is evidence, assumed state is just
belief. Readings inside the hysteresis band, or an unavailable/
unknown/non-numeric sensor, hold: no correction fires either way, so a
dead plug can never turn the house off. On (re)subscribe -- startup,
reload, or the sensor setting changing -- the current reading is
evaluated immediately rather than waiting for the next state-change
event, so a device switched off while HA was down reads off within
seconds of restart.

THE SETTLE WINDOW (0.17.2). Evidence wins, but not mid-spin-up. A plug
reports every 10 to 30 seconds, so the first report after a HAIR send is
usually the OLD draw: without a guard it flips the entity back to its
old state and the report after that flips it forward again. Every send
HAIR makes to a watched device (``SIGNAL_DEVICE_SENT``, whoever asked
for it) therefore opens a window of ``power_settle_seconds(device)``.
Inside the window readings are classified as before but not dispatched,
with one exception: when the send's expected state is known, a verdict
that agrees with it closes the window at once and is dispatched (the
early clear). When the window runs out, the handback evaluates the
current reading the way the seed does, with one difference: it
dispatches only a reading the plug reported after the send. A plug that
reports less often than the settle time still holds the pre-send reading
when the window closes, and that reading is not evidence about the send;
dispatching it would bring the flicker back at the end of the window.
The window is closed either way, so the plug's next real report is
dispatched as usual: a device that never got the IR is corrected at the
end of the window when the plug has reported since the send, and at its
next report otherwise. The latest send wins; a window is
never persisted, so after a restart there is none and the seed behaves
as it always has. ``power_settle_s = 0`` is no window at all, which is
the old behaviour exactly. ``docs/internal/plans/power-bands.md``
section 2 and ``power-fed-state.md`` section 4 are the design.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .models import IRDevice, power_settle_seconds
from .send_signal import SIGNAL_DEVICE_SENT, DeviceSent
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


# The window's clock. Monotonic, so a wall-clock jump cannot stretch or
# end a window; a module attribute so tests can move it.
_monotonic = time.monotonic


def _utcnow() -> datetime:
    """Wall-clock now, to compare with a state's ``last_reported``.

    Home Assistant stamps ``last_reported`` in UTC wall-clock time, so
    the send has to be stamped on the same clock (the monotonic one
    above cannot be compared with it). Same value as
    ``homeassistant.util.dt.utcnow``; a module attribute so tests can
    move it.
    """
    return datetime.now(UTC)

# Mapped actions whose send says which way the device should end up. A
# toggle, or a command mapped to anything else, says nothing.
_EXPECTED_BY_ACTION: tuple[tuple[str, PowerVerdict], ...] = (
    ("turn_on", "on"),
    ("turn_off", "off"),
)


def expected_power_state(
    device: IRDevice, sent: DeviceSent
) -> PowerVerdict | None:
    """The on/off state a send should leave the device in, if known.

    Taken from the send's structure and the device's own mapping, never
    from a command name: the matrix's power codes say it outright, any
    lattice cell is a running state, and a flat command says it only
    when it is the one mapped to turn on or turn off.
    """
    if sent.power in ("on", "off"):
        return sent.power  # type: ignore[return-value]
    if sent.matrix_cell:
        return "on"
    if sent.command_id is None:
        return None
    command = device.get_command(sent.command_id)
    if command is None:
        return None
    name = command.name.casefold()
    mapping = device.entity_config.command_mapping
    # A command that is the device's toggle promises nothing, whatever
    # else it is mapped to: with turn_on and power_toggle on one button,
    # a turn_off falls back to that button, and reading it as "on" would
    # let a stale running-draw report clear the window early.
    if str(mapping.get("power_toggle") or "").casefold() == name:
        return None
    hits = {
        verdict
        for action, verdict in _EXPECTED_BY_ACTION
        if str(mapping.get(action) or "").casefold() == name
    }
    return hits.pop() if len(hits) == 1 else None


@dataclass(slots=True, eq=False)
class _SettleWindow:
    """One open window. Compared by identity, never by value.

    The timer carries the window object itself, and fires only if that
    same object is still the device's window. A window replaced by a
    later send, cancelled by a removal, or belonging to a device that
    was deleted and re-created under the same id is therefore inert
    even if its timer somehow ran.
    """

    sent_at: float
    # The same moment on the wall clock, for the handback's test of
    # ``State.last_reported`` (see the module docstring).
    sent_wall: datetime
    expected: PowerVerdict | None
    handle: Any = None


class PowerMonitor:
    """Tracks per-device power sensors and dispatches on/off verdicts."""

    def __init__(self, hass: HomeAssistant, store: HAIRStore) -> None:
        self._hass = hass
        self._store = store
        self._unsub: dict[str, CALLBACK_TYPE] = {}
        self._windows: dict[str, _SettleWindow] = {}
        self._unsub_sent: CALLBACK_TYPE | None = None

    def start(self) -> None:
        """Subscribe every stored device that has a sensor configured.

        Must be called AFTER platform entities are set up (i.e. after
        ``async_forward_entry_setups``), since subscribing immediately
        evaluates and dispatches the sensor's current reading (the
        startup seed) -- an entity that isn't listening yet would miss
        it. ``__init__.py`` calls this right alongside
        ``SignalMonitor.async_start()``, in the same order.
        """
        if self._unsub_sent is None:
            self._unsub_sent = async_dispatcher_connect(
                self._hass, SIGNAL_DEVICE_SENT, self._on_device_sent
            )
        for device in self._store.get_all_devices():
            self._subscribe(device)

    def stop(self) -> None:
        if self._unsub_sent is not None:
            self._unsub_sent()
            self._unsub_sent = None
        for device_id in list(self._windows):
            self._cancel_window(device_id)
        for unsub in self._unsub.values():
            unsub()
        self._unsub.clear()

    def rebuild_device(self, device: IRDevice) -> None:
        """Re-subscribe a single device after create/update.

        Called from ``DeviceManager`` so a sensor picked, changed, or
        cleared in the settings dialog takes effect immediately -- no
        integration reload needed. Safe to call for a device with no
        sensor configured; it simply tears down any prior subscription.

        An open settle window survives the rebuild with its deadline
        unchanged: its timer is cancelled and a fresh one armed for what
        is left, under the device's new settle value. Almost every edit
        lands here (a rename, a mapping, a command saved), so dropping
        the window would let the re-subscribe seed dispatch the stale
        reading the window was holding back, and the edit would flicker
        the entity. With the sensor cleared or the value set to 0 the
        window simply ends.
        """
        window = self._windows.get(device.id)
        self._cancel_window(device.id)
        self._unsubscribe(device.id)
        if window is not None and device.power_sensor_entity_id:
            remaining = (
                window.sent_at + power_settle_seconds(device) - _monotonic()
            )
            if remaining > 0:
                self._open_window(
                    device.id,
                    window.sent_at,
                    window.sent_wall,
                    window.expected,
                    remaining,
                )
        self._subscribe(device)

    def remove_device(self, device_id: str) -> None:
        """Tear down a device's subscription and window after it is deleted."""
        self._cancel_window(device_id)
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
        # The gate. Every path to a dispatch comes through here: a live
        # report, the seed at (re)subscribe, and the handback when a
        # window runs out.
        window = self._windows.get(device_id)
        if window is not None:
            if window.expected is None or verdict != window.expected:
                return
            # The early clear: the plug agrees with the send.
            self._cancel_window(device_id)
        async_dispatcher_send(self._hass, SIGNAL_POWER_VERDICT, device_id, verdict)

    # -- the settle window ---------------------------------------------

    @callback
    def _on_device_sent(self, sent: DeviceSent) -> None:
        """Open a window for a landed send to a watched device."""
        device_id = sent.device_id
        if device_id not in self._unsub:
            # No sensor, so nothing to hold back.
            return
        device = self._store.get_device(device_id)
        if device is None:
            return
        # The latest send wins: whatever window was open is replaced,
        # expected state and all.
        self._cancel_window(device_id)
        settle = power_settle_seconds(device)
        if settle <= 0:
            return
        self._open_window(
            device_id,
            _monotonic(),
            _utcnow(),
            expected_power_state(device, sent),
            settle,
        )

    def _open_window(
        self,
        device_id: str,
        sent_at: float,
        sent_wall: datetime,
        expected: PowerVerdict | None,
        delay: float,
    ) -> None:
        window = _SettleWindow(
            sent_at=sent_at, sent_wall=sent_wall, expected=expected
        )
        window.handle = self._hass.loop.call_later(
            delay, self._on_window_closed, device_id, window
        )
        self._windows[device_id] = window

    def _cancel_window(self, device_id: str) -> None:
        window = self._windows.pop(device_id, None)
        if window is not None and window.handle is not None:
            window.handle.cancel()

    def _on_window_closed(self, device_id: str, window: _SettleWindow) -> None:
        """The window ran out: hand the last word back to the sensor."""
        if self._windows.get(device_id) is not window:
            return
        del self._windows[device_id]
        device = self._store.get_device(device_id)
        if device is None or device_id not in self._unsub:
            return
        sensor_id = device.power_sensor_entity_id
        if not sensor_id:
            return
        # The seed, with one difference: a reading the plug reported
        # before the send is not evidence about it. On a plug slower
        # than the settle time that reading is the pre-send draw, and
        # dispatching it would flicker the entity here instead of at the
        # plug's next report. Hold it; the window is closed, so that
        # next report is dispatched as usual.
        state = self._hass.states.get(sensor_id)
        reported = getattr(state, "last_reported", None)
        if reported is None or reported < window.sent_wall:
            return
        self._evaluate(device_id, state)
