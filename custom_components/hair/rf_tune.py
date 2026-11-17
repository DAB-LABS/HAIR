"""Tuning a radio receiver's listening frequency (listening PR 1).

A receiver that can be retuned, the owner's CC1101 among them, has a
``number`` entity on its own Home Assistant device that holds the
frequency it listens at, in MHz. HAIR finds that number, reads it when a
capture arrives so the code is stamped with the band it was really heard
on, and sets it from the Sniffer's receiver chip.

WHICH NUMBER. The one enabled ``number`` on the receiver's device whose
unit is a frequency (MHz, kHz or Hz). None, or more than one, and the
receiver is not tunable from HAIR: it then listens where its hardware
does, and HAIR says so. A user-chosen link for the ambiguous case is a
later step.

THE STAMP, ``tuned``. Between the open capture window's frequency and the
receiver's declared fixed one (``rf_receive.frequency_of``). Read when the
capture arrives, not cached. For a press delivered one frame per capture,
the reading of its FIRST frame stamps the whole press, so a retune during
the burst hold does not move a press heard before it (``rf_burst``). A
tuning number that is unavailable gives "band unknown", never the
declared value: the declared value is what mislabelled every capture
before this. So does a reading in the first ``RF_TUNE_SETTLE_S`` after
HAIR itself set the number: a receiver can deliver a capture heard on the
old frequency after the new one is set, and every set makes a stray
pulse of its own (Proxie, 2026-11-16).

SETTING IT. ``number.set_value`` in the number's own unit, then a wait
of up to ``RF_TUNE_CONFIRM_S`` for the number's state to read the asked
value, compared after rounding to the number's step. ``confirmed`` means
the request reached the device; it does not prove the chip tuned (an
optimistic number reads back what it was given). ``did_not_change`` gives
the value the number still holds, which is what a receiver that refuses a
value in its chip's gaps does.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)

# A HAIR set's captures are not trusted for this long (see the docstring).
RF_TUNE_SETTLE_S = 2.0
# How long a set waits for the number to read the asked value.
RF_TUNE_CONFIRM_S = 3.0

# The units a frequency number may carry, as Hz per unit.
_UNITS = {"MHz": 1_000_000, "kHz": 1_000, "Hz": 1}

TUNE_CONFIRMED = "confirmed"
TUNE_DID_NOT_CHANGE = "did_not_change"
TUNE_CANNOT = "cannot_tune"

# What a reading at a capture's arrival can be.
READING_NONE = "none"        # the receiver has no tuning number
READING_UNKNOWN = "unknown"  # it has one, but the band cannot be trusted now
READING_HZ = "hz"            # the band the number holds


@dataclass(frozen=True)
class Reading:
    """The tuning number's word on one capture."""

    kind: str
    hz: int | None = None


NO_TUNING = Reading(READING_NONE)
UNKNOWN_BAND = Reading(READING_UNKNOWN)

# When HAIR last set each receiver's number, by receiver entity id, on the
# monotonic clock. Module-level, like the platform caches: it is a few
# floats, and it must outlive any one call.
_last_set: dict[str, float] = {}


def reset_for_test() -> None:
    _last_set.clear()


def _unit_factor(state: Any) -> int | None:
    if state is None:
        return None
    return _UNITS.get(state.attributes.get("unit_of_measurement"))


def tuning_number(hass: HomeAssistant, receiver_entity_id: str) -> str | None:
    """The receiver's tuning number, or None (no device, none, or several)."""
    try:
        registry = er.async_get(hass)
        entry = registry.async_get(receiver_entity_id)
        device_id = getattr(entry, "device_id", None)
        if not device_id:
            return None
        found = [
            e.entity_id
            for e in er.async_entries_for_device(registry, device_id)
            if e.entity_id.startswith("number.")
            and getattr(e, "disabled_by", None) is None
            and _unit_factor(hass.states.get(e.entity_id)) is not None
        ]
    except Exception:
        _LOGGER.debug("Could not look for %s's tuning number", receiver_entity_id, exc_info=True)
        return None
    return found[0] if len(found) == 1 else None


def number_hz(hass: HomeAssistant, number_entity_id: str) -> int | None:
    """The frequency a tuning number holds now, in Hz, or None."""
    state = hass.states.get(number_entity_id)
    factor = _unit_factor(state)
    if factor is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, None, ""):
        return None
    try:
        return round(float(state.state) * factor)
    except (TypeError, ValueError):
        return None


def reading(hass: HomeAssistant, receiver_entity_id: str) -> Reading:
    """What the receiver's tuning number says about a capture arriving now.

    Never raises: a failure reads as "no tuning number", which is how HAIR
    stamped captures before this existed.
    """
    try:
        number = tuning_number(hass, receiver_entity_id)
        if number is None:
            return NO_TUNING
        set_at = _last_set.get(receiver_entity_id)
        if set_at is not None and time.monotonic() - set_at < RF_TUNE_SETTLE_S:
            return UNKNOWN_BAND
        hz = number_hz(hass, number)
        return Reading(READING_HZ, hz) if hz else UNKNOWN_BAND
    except Exception:
        _LOGGER.debug("Could not read %s's tuning", receiver_entity_id, exc_info=True)
        return NO_TUNING


class Stamped:
    """A received signal with its tuning reading taken on arrival.

    Everything else reads through to the signal, so the capture path is
    unchanged; ``rf_receive.frequency_of`` reads ``hair_tuned``.
    """

    __slots__ = ("hair_tuned", "inner")

    def __init__(self, inner: Any, tuned: Reading) -> None:
        self.inner = inner
        self.hair_tuned = tuned

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def stamp(hass: HomeAssistant, receiver_entity_id: str, signal: Any) -> Stamped:
    return Stamped(signal, reading(hass, receiver_entity_id))


def restamp(signal: Any, tuned: Reading | None) -> Any:
    """``signal`` carrying ``tuned`` instead of its own reading (a burst's
    last signal, stamped with its first frame's reading)."""
    if tuned is None:
        return signal
    inner = signal.inner if isinstance(signal, Stamped) else signal
    return Stamped(inner, tuned)


def _rounded(value_hz: float, step: Any, factor: int) -> int:
    try:
        step_hz = float(step) * factor
    except (TypeError, ValueError):
        step_hz = 0.0
    if step_hz <= 0:
        return round(value_hz)
    return round(round(value_hz / step_hz) * step_hz)


def describe(hass: HomeAssistant, receiver_entity_id: str) -> dict[str, Any]:
    """The receiver's tuning for the panel."""
    from .rf_receive import supported_ranges

    number = tuning_number(hass, receiver_entity_id)
    state = hass.states.get(number) if number else None
    factor = _unit_factor(state) or _UNITS["MHz"]

    def mhz(value: Any) -> float | None:
        try:
            return round(float(value) * factor / 1_000_000, 6)
        except (TypeError, ValueError):
            return None

    hz = number_hz(hass, number) if number else None
    return {
        "receiver_entity_id": receiver_entity_id,
        "tunable": number is not None,
        "number_entity": number,
        "available": hz is not None,
        "current_mhz": round(hz / 1_000_000, 6) if hz else None,
        "min_mhz": mhz(state.attributes.get("min")) if state else None,
        "max_mhz": mhz(state.attributes.get("max")) if state else None,
        "declared": [list(r) for r in supported_ranges(hass, receiver_entity_id) or []],
    }


async def async_tune(
    hass: HomeAssistant, receiver_entity_id: str, frequency_hz: int
) -> dict[str, Any]:
    """Set the receiver's listening frequency and say what it did."""
    number = tuning_number(hass, receiver_entity_id)
    if number is None:
        return {"result": TUNE_CANNOT, "current_mhz": None}
    state = hass.states.get(number)
    factor = _unit_factor(state) or _UNITS["MHz"]
    step = state.attributes.get("step") if state is not None else None
    asked = _rounded(frequency_hz, step, factor)

    def matches() -> bool:
        hz = number_hz(hass, number)
        return hz is not None and _rounded(hz, step, factor) == asked

    changed = asyncio.Event()

    @callback
    def _on_change(_event: Any) -> None:
        if matches():
            changed.set()

    unsub = async_track_state_change_event(hass, [number], _on_change)
    try:
        _last_set[receiver_entity_id] = time.monotonic()
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": number, "value": asked / factor},
            blocking=True,
        )
        if not matches():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(changed.wait(), RF_TUNE_CONFIRM_S)
    finally:
        unsub()
    # The settle window starts when the new value is in force.
    _last_set[receiver_entity_id] = time.monotonic()
    hz = number_hz(hass, number)
    current = round(hz / 1_000_000, 6) if hz else None
    return {
        "result": TUNE_CONFIRMED if matches() else TUNE_DID_NOT_CHANGE,
        "current_mhz": current,
    }
