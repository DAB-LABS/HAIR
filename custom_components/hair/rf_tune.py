"""Tuning a radio receiver's listening frequency.

A receiver that can be retuned, a CC1101 board among them, has a
``number`` entity on its own Home Assistant device that holds the
frequency it listens at, in MHz. HAIR finds that number, reads it when a
capture arrives so the code is stamped with the band it was really heard
on, and sets it from the Sniffer's receiver chip.

WHICH NUMBER. The receiver's declared ``frequency_number``, when it
passes the safety rule (a ``number`` on the receiver's own device,
enabled, whose unit is MHz, kHz or Hz). Otherwise, for a receiver that
declares no frequency select either, the one enabled ``number`` on its
device whose unit is a frequency: the convention a CC1101 board on
ESPHome needs, since ESPHome cannot declare the number. None, or more
than one, and the number is not HAIR's to set. A receiver that declares
a select and no number is set through its presets only.

THE SELECT. A declared ``frequency_select`` with its ``frequency_options``
sets the presets. When the receiver also declares
``frequency_number_option``, that option is the one the number feeds:
the number is in force only while the select is on it, and the other
options are presets.

THE STAMP, ``tuned``. Between the open capture window's frequency and the
receiver's declared fixed one (``rf_receive.frequency_of``): what the
receiver says it listens at now, in this order: an always-on receiver's
declared ``frequency_hz``; the select's preset while one is in force
(a sweep is band unknown); the number's value. Read when the capture
arrives, not cached. For a press delivered one frame per capture,
the reading of its FIRST frame stamps the whole press, so a retune during
the burst hold does not move a press heard before it (``rf_burst``). A
tuning number that is unavailable gives "band unknown", never the
declared value: the declared value is what mislabelled every capture
before this. So does a reading in the first ``RF_TUNE_SETTLE_S`` after
HAIR itself set the number: a receiver can deliver a capture heard on the
old frequency after the new one is set, and a set can make a stray
pulse of its own.

SETTING IT (``async_set_frequency``). A value one of the presets
carries picks that preset; any other value sets the number (and, when
the number feeds an option, picks that option too); a preset can also be
picked by name, the only way to pick a sweep. A number is set with
``number.set_value`` in its own unit, then a wait of up to
``RF_TUNE_CONFIRM_S`` for its state to read the asked value, compared
after rounding to its step; a select the same way, until it reads the
asked option. ``confirmed`` means
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

from .receiver_window import (
    ATTR_CAPTURE_PHASE,
    ATTR_FREQUENCY_HZ,
    ATTR_FREQUENCY_NUMBER,
    ATTR_FREQUENCY_NUMBER_OPTION,
    ATTR_FREQUENCY_OPTIONS,
    ATTR_FREQUENCY_SELECT,
    PHASE_SWEEPING,
    declared_settings,
    says_capture,
)

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
    _refused.clear()


def _unit_factor(state: Any) -> int | None:
    if state is None:
        return None
    return _UNITS.get(state.attributes.get("unit_of_measurement"))


SOURCE_DECLARED = "declared"
SOURCE_FOUND = "found"


@dataclass(frozen=True)
class Declared:
    """A receiver's frequency declarations that pass the safety rule."""

    select: str | None = None
    # (option, Hz or None for a sweep), in the select's order.
    options: tuple[tuple[str, int | None], ...] = ()
    number: str | None = None
    number_option: str | None = None


NOTHING_DECLARED = Declared()

# Declared numbers already logged as refused, so each is said once.
_refused: set[tuple[str, str]] = set()


def declared(
    hass: HomeAssistant, receiver_entity_id: str, state: Any = None
) -> Declared:
    """What the receiver declares about its frequency. Never raises.

    Read on every capture, so a receiver that declares neither a select
    nor a number costs no registry read.
    """
    try:
        if state is None:
            state = hass.states.get(receiver_entity_id)
        if state is None:
            return NOTHING_DECLARED
        attributes = state.attributes
        if not isinstance(attributes.get(ATTR_FREQUENCY_SELECT), str) and not isinstance(
            attributes.get(ATTR_FREQUENCY_NUMBER), str
        ):
            return NOTHING_DECLARED
        registry = er.async_get(hass)
        entry = registry.async_get(receiver_entity_id)
        settings = declared_settings(registry, state, getattr(entry, "device_id", None))
        number = settings.get(ATTR_FREQUENCY_NUMBER)
        if number is not None and not _usable_number(hass, registry, number):
            if (receiver_entity_id, number) not in _refused:
                _refused.add((receiver_entity_id, number))
                _LOGGER.debug(
                    "%s declares %s as its frequency number, which is disabled "
                    "or not in MHz, kHz or Hz; ignored", receiver_entity_id, number,
                )
            number = None
        return Declared(
            select=settings.get(ATTR_FREQUENCY_SELECT),
            options=tuple(
                (o["option"], o["hz"]) for o in settings.get(ATTR_FREQUENCY_OPTIONS, [])
            ),
            number=number,
            number_option=settings.get(ATTR_FREQUENCY_NUMBER_OPTION) if number else None,
        )
    except Exception:
        _LOGGER.debug("Could not read %s's declarations", receiver_entity_id, exc_info=True)
        return NOTHING_DECLARED


def _usable_number(hass: HomeAssistant, registry: Any, entity_id: str) -> bool:
    entry = registry.async_get(entity_id)
    return (
        entry is not None
        and getattr(entry, "disabled_by", None) is None
        and _unit_factor(hass.states.get(entity_id)) is not None
    )


def _found_number(hass: HomeAssistant, receiver_entity_id: str) -> str | None:
    """The convention: the one frequency number on the receiver's device."""
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


def tuning_source(
    hass: HomeAssistant, receiver_entity_id: str, decl: Declared | None = None
) -> tuple[str | None, str | None]:
    """The receiver's tuning number and how HAIR knows it (declared or
    found), or (None, None)."""
    decl = declared(hass, receiver_entity_id) if decl is None else decl
    if decl.number is not None:
        return decl.number, SOURCE_DECLARED
    if decl.select is not None:
        # It declares how it is set, and no number: presets only.
        return None, None
    found = _found_number(hass, receiver_entity_id)
    return (found, SOURCE_FOUND) if found else (None, None)


def tuning_number(hass: HomeAssistant, receiver_entity_id: str) -> str | None:
    """The receiver's tuning number, or None (no device, none, or several)."""
    return tuning_source(hass, receiver_entity_id)[0]


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


# Where a receiver listens now, as ``listening_now`` says it.
NOW_HZ = "hz"
NOW_SWEEP = "sweep"
NOW_UNKNOWN = "unknown"  # there is a way to set it, but no value now
NOW_NONE = "none"        # nothing says, and nothing sets it

NOW_SOURCE_RECEIVER = "receiver"
NOW_SOURCE_NUMBER = "number"
NOW_SOURCE_SELECT = "select"


def trusted(receiver_entity_id: str) -> bool:
    """False in the first ``RF_TUNE_SETTLE_S`` after HAIR set the receiver."""
    set_at = _last_set.get(receiver_entity_id)
    return set_at is None or time.monotonic() - set_at >= RF_TUNE_SETTLE_S


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def listening_now(
    hass: HomeAssistant,
    receiver_entity_id: str,
    decl: Declared | None = None,
    number: str | None = None,
) -> tuple[str, int | None, str | None]:
    """What the receiver says it listens at now, outside an open window:
    ``(kind, hz, source)``.

    An always-on receiver's declared ``frequency_hz`` first (not while it
    says it is sweeping); then the
    select's preset while one is in force (a windowed receiver's next
    window listens there); then the number's value. A fixed range is
    not read here (``rf_receive.frequency_of`` and the row read it).
    """
    state = hass.states.get(receiver_entity_id)
    if decl is None:
        decl = declared(hass, receiver_entity_id, state)
        number = tuning_source(hass, receiver_entity_id, decl)[0]
    if (
        state is not None
        and not says_capture(state)
        and state.attributes.get(ATTR_CAPTURE_PHASE) != PHASE_SWEEPING
    ):
        hz = state.attributes.get(ATTR_FREQUENCY_HZ)
        if _positive_int(hz):
            return NOW_HZ, hz, NOW_SOURCE_RECEIVER
    if decl.select is not None:
        select_state = hass.states.get(decl.select)
        current = getattr(select_state, "state", None)
        if not (number is not None and current == decl.number_option):
            options = dict(decl.options)
            if current in options:
                hz = options[current]
                if hz is None:
                    return NOW_SWEEP, None, NOW_SOURCE_SELECT
                return NOW_HZ, hz, NOW_SOURCE_SELECT
            if number is None:
                return NOW_UNKNOWN, None, None
    if number is not None:
        hz = number_hz(hass, number)
        if hz:
            return NOW_HZ, hz, NOW_SOURCE_NUMBER
        return NOW_UNKNOWN, None, None
    return NOW_NONE, None, None


def reading(hass: HomeAssistant, receiver_entity_id: str) -> Reading:
    """What the receiver's tuning number says about a capture arriving now.

    Never raises: a failure reads as "no tuning number", which is how HAIR
    stamped captures before this existed.
    """
    try:
        kind, hz, _source = listening_now(hass, receiver_entity_id)
        if kind == NOW_NONE:
            return NO_TUNING
        if not trusted(receiver_entity_id):
            return UNKNOWN_BAND
        return Reading(READING_HZ, hz) if kind == NOW_HZ and hz else UNKNOWN_BAND
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
    """The receiver's tuning for the panel.

    A receiver HAIR cannot tune that declares one single frequency (one
    range with min == max) listens there: ``current_mhz`` is that value
    and ``fixed`` is True, the same value its captures are stamped with.
    ``fixed`` is False for a tunable receiver and for one whose band is
    unknown.
    """
    from .rf_receive import fixed_frequency, supported_ranges

    ranges = supported_ranges(hass, receiver_entity_id) or []
    number = tuning_number(hass, receiver_entity_id)
    state = hass.states.get(number) if number else None
    factor = _unit_factor(state) or _UNITS["MHz"]

    def mhz(value: Any) -> float | None:
        try:
            return round(float(value) * factor / 1_000_000, 6)
        except (TypeError, ValueError):
            return None

    hz = number_hz(hass, number) if number else None
    fixed_hz = None if number else fixed_frequency(ranges)
    if fixed_hz:
        hz = fixed_hz
    return {
        "receiver_entity_id": receiver_entity_id,
        "tunable": number is not None,
        "number_entity": number,
        "available": hz is not None,
        "current_mhz": round(hz / 1_000_000, 6) if hz else None,
        "fixed": fixed_hz is not None,
        "min_mhz": mhz(state.attributes.get("min")) if state else None,
        "max_mhz": mhz(state.attributes.get("max")) if state else None,
        "declared": [list(r) for r in ranges],
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


async def _async_pick(
    hass: HomeAssistant, receiver_entity_id: str, select: str, option: str
) -> str:
    """Pick one of the frequency select's options; confirmed or not."""

    def matches() -> bool:
        return getattr(hass.states.get(select), "state", None) == option

    changed = asyncio.Event()

    @callback
    def _on_change(_event: Any) -> None:
        if matches():
            changed.set()

    unsub = async_track_state_change_event(hass, [select], _on_change)
    try:
        _last_set[receiver_entity_id] = time.monotonic()
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": select, "option": option},
            blocking=True,
        )
        if not matches():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(changed.wait(), RF_TUNE_CONFIRM_S)
    finally:
        unsub()
    _last_set[receiver_entity_id] = time.monotonic()
    return TUNE_CONFIRMED if matches() else TUNE_DID_NOT_CHANGE


# A value this close to a preset's carrier picks the preset.
_PRESET_MATCH_HZ = 500


async def async_set_frequency(
    hass: HomeAssistant,
    receiver_entity_id: str,
    *,
    frequency_hz: int | None = None,
    option: str | None = None,
) -> dict[str, Any]:
    """Set where the receiver listens: a value, or a preset by name.

    The one set path for every receiver (see the module docstring). The
    answer says what it came to, and ``current_mhz`` is where the
    receiver says it listens afterwards.
    """
    decl = declared(hass, receiver_entity_id)
    number, _source = tuning_source(hass, receiver_entity_id, decl)
    presets = dict(decl.options)
    if option is not None:
        if decl.select is None or option not in presets:
            return _answer(hass, receiver_entity_id, TUNE_CANNOT)
        result = await _async_pick(hass, receiver_entity_id, decl.select, option)
        return _answer(hass, receiver_entity_id, result)
    if frequency_hz is None:
        return _answer(hass, receiver_entity_id, TUNE_CANNOT)
    if decl.select is not None:
        for name, hz in decl.options:
            if (
                hz is not None
                and name != decl.number_option
                and abs(hz - frequency_hz) <= _PRESET_MATCH_HZ
            ):
                result = await _async_pick(hass, receiver_entity_id, decl.select, name)
                return _answer(hass, receiver_entity_id, result)
    if number is None:
        return _answer(hass, receiver_entity_id, TUNE_CANNOT)
    tuned = await async_tune(hass, receiver_entity_id, frequency_hz)
    result = tuned["result"]
    if decl.select is not None and decl.number_option is not None:
        picked = await _async_pick(
            hass, receiver_entity_id, decl.select, decl.number_option
        )
        if picked != TUNE_CONFIRMED:
            result = picked
    return _answer(hass, receiver_entity_id, result)


def _answer(hass: HomeAssistant, receiver_entity_id: str, result: str) -> dict[str, Any]:
    kind, hz, _source = listening_now(hass, receiver_entity_id)
    current = round(hz / 1_000_000, 6) if kind == NOW_HZ and hz else None
    return {"result": result, "current_mhz": current}
