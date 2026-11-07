"""Sending a radio row: the wire frame, the frequency, the transmit.

The design is ``rf-in-hair-plan.md`` 5.5, 5.7 and 5.8; the names are
the send round's doors (``rf-send-doors.md``). Infrared is not touched
here: a radio row goes only to ``radio_frequency`` transmitters, through
core's ``radio_frequency.async_send_command``, as an ``OOKCommand``.

THE WIRE FRAME. A row holds one frame, header, body and trailer, in
HAIR's signed convention (mark positive), with the gap that closed it as
its last value when one was measured. What goes on the air is that frame
with the row's inter-frame gap as its final space, repeated: core's
transmitters repeat a command back to back (ESPHome passes the repeat
count as send times with no wait between; a trailing negative value
plays as silence of exactly that length), so the gap between repeats is
the frame's own last space and nothing else. Never the trailing edge of
a split capture, which is the receiver's idle, not the remote's gap.

THE FREQUENCY. Core refuses a command whose exact Hz is outside the
transmitter's declared ranges, and a fixed-frequency ESPHome transmitter
declares a range of one value. A row learned at a measured 433.84 MHz
would never pass an Athom declared at 433.92, although its radio is
fixed there and works. So a fixed transmitter within
``RF_SEND_SUBSTITUTE_TOLERANCE_HZ`` sends at its own value and says so;
a range that holds the row's Hz sends it; everything else is refused
before core is asked. A row with no frequency is never sent at a
default.

THE COUNT. A send is ``send_count`` frames, bounded by the air-time cap.
Core's ``repeat_count`` is the repeats after the first, so it is
``send_count - 1``, for every platform that repeats a command itself.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from .const import (
    ASSIGN_SERVICE_TIMEOUT_S,
    MAX_SEND_COUNT,
    RF_ASSUMED_FRAME_GAP_US,
    RF_DEFAULT_SEND_COUNT,
    RF_FREQUENCY_UNSUPPORTED,
    RF_MIN_SEND_COUNT,
    RF_NO_FREQUENCY,
    RF_NO_RANGES,
    RF_PLATFORM_NOT_LOADED,
    RF_SEND_SUBSTITUTE_TOLERANCE_HZ,
    SEND_AIR_TIME_MAX_MS,
)

_LOGGER = logging.getLogger(__name__)

RADIO_FREQUENCY_DOMAIN = "radio_frequency"

# Whether a transmitter platform repeats a command itself, by the
# integration that owns the entity. Measured on the bench, not assumed:
# see the send round's report. A platform that is not listed is trusted
# to honour ``repeat_count``, which is what core's contract says.
NATIVE_REPEAT: dict[str, bool] = {
    "esphome": True,
    "broadlink": True,
}


class SendRefusedError(RuntimeError):
    """A send HAIR will not make, with the reason as a code.

    The panel says it from ``code``; the message is English, for the log.
    Raised before anything is transmitted, so a refusal never leaves a
    half-sent burst behind.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TransmitterFit:
    """Whether one transmitter can send a carrier, and at what."""

    ok: bool
    send_hz: int | None
    substituted: bool
    code: str | None


# ---------------------------------------------------------------------------
# Pure rules
# ---------------------------------------------------------------------------


def is_radio_entity(entity_id: str | None) -> bool:
    return bool(entity_id) and entity_id.startswith(f"{RADIO_FREQUENCY_DOMAIN}.")


def gap_us(row: Any) -> int:
    """The row's inter-frame gap, or the assumed one."""
    value = getattr(row, "rf_frame_gap_us", None)
    return int(value) if value else RF_ASSUMED_FRAME_GAP_US


def wire_frame(row: Any) -> list[int]:
    """One frame as it goes on the air: the frame with its gap last.

    The doors' rule, word for word: ``raw_timings`` with its last value
    replaced by ``-gap`` when that value is negative, otherwise with
    ``-gap`` appended.
    """
    frame = [int(v) for v in (getattr(row, "raw_timings", None) or [])]
    if not frame:
        return []
    gap = -abs(gap_us(row))
    if frame[-1] < 0:
        frame[-1] = gap
    else:
        frame.append(gap)
    return frame


def frame_air_us(timings: list[int]) -> int:
    return sum(abs(int(v)) for v in timings)


def choose_frequency(
    frequency_hz: int | None, ranges: list[tuple[int, int]] | None
) -> TransmitterFit:
    """What a transmitter with ``ranges`` sends a ``frequency_hz`` row at."""
    if not frequency_hz:
        return TransmitterFit(False, None, False, RF_NO_FREQUENCY)
    usable = [
        (int(low), int(high)) for low, high in (ranges or [])
        if not (int(low) == 0 and int(high) == 0)
    ]
    if not usable:
        return TransmitterFit(False, None, False, RF_NO_RANGES)
    hz = int(frequency_hz)
    if any(low <= hz <= high for low, high in usable):
        return TransmitterFit(True, hz, False, None)
    if len(usable) == 1 and usable[0][0] == usable[0][1]:
        fixed = usable[0][0]
        if abs(fixed - hz) <= RF_SEND_SUBSTITUTE_TOLERANCE_HZ:
            return TransmitterFit(True, fixed, True, None)
    return TransmitterFit(False, None, False, RF_FREQUENCY_UNSUPPORTED)


def seed_send_count(repeats_observed: int | None) -> int:
    """A radio row's sends when nobody chose: what one press carried."""
    if not repeats_observed:
        return RF_DEFAULT_SEND_COUNT
    return max(RF_MIN_SEND_COUNT, min(int(repeats_observed), MAX_SEND_COUNT))


def seed_stored_send_counts(data: dict[str, Any]) -> int:
    """Seed the count of radio commands stored before HAIR sent radio.

    A command assigned from a radio row under the hearing round kept the
    stored default of 1, which plays one frame where the remote sent
    several. Runs once, from the device store's v1.3 migration, so a 1 a
    person sets afterwards is never touched again. Returns how many
    commands it seeded.
    """
    seeded = 0
    for device in data.get("devices") or []:
        if not isinstance(device, dict):
            continue
        for command in device.get("commands") or []:
            if not isinstance(command, dict) or command.get("medium") != "rf":
                continue
            if (command.get("send_count") or 1) > 1:
                continue
            command["send_count"] = seed_send_count(command.get("rf_repeats_observed"))
            seeded += 1
    if seeded:
        _LOGGER.info(
            "Radio send: seeded the send count of %d stored radio command(s)", seeded
        )
    return seeded


def send_count_for(row: Any, timings: list[int]) -> int:
    """The row's ``send_count``, clamped, then held to the air-time cap."""
    count = max(1, min(int(getattr(row, "send_count", None) or 1), MAX_SEND_COUNT))
    per_frame_us = frame_air_us(timings)
    if per_frame_us > 0:
        fits = max(1, (SEND_AIR_TIME_MAX_MS * 1000) // per_frame_us)
        count = min(count, int(fits))
    return count


def burst_air_s(timings: list[int], count: int) -> float:
    return frame_air_us(timings) * max(1, count) / 1_000_000


def native_repeat(platform: str | None) -> bool:
    return NATIVE_REPEAT.get(platform or "", True)


# ---------------------------------------------------------------------------
# What Home Assistant says about a transmitter
# ---------------------------------------------------------------------------


def _component(hass: Any) -> Any:
    try:
        from homeassistant.components.radio_frequency.const import DATA_COMPONENT
    except ImportError:
        return None
    data = getattr(hass, "data", None)
    return data.get(DATA_COMPONENT) if data is not None else None


def transmitter_ranges(hass: Any, entity_id: str) -> list[tuple[int, int]] | None:
    """The transmitter's declared ranges; None when radio is not loaded.

    An entity the component does not know (removed, or not a
    transmitter) declares nothing: an empty list.
    """
    component = _component(hass)
    if component is None:
        return None
    entity = component.get_entity(entity_id)
    if entity is None:
        return []
    try:
        ranges = entity.supported_frequency_ranges
    except Exception:  # a platform bug must not break the picker
        _LOGGER.debug("No frequency ranges from %s", entity_id, exc_info=True)
        return []
    return [(int(low), int(high)) for low, high in (ranges or [])]


def transmitter_fit(
    hass: Any, entity_id: str, frequency_hz: int | None
) -> TransmitterFit:
    """The send path's own rule, for one transmitter (the picker asks too)."""
    return choose_frequency(frequency_hz, transmitter_ranges(hass, entity_id))


def _ook_command(timings: list[int], hz: int, repeat_count: int) -> Any:
    try:
        from rf_protocols.commands.ook import OOKCommand
    except ImportError as err:
        raise SendRefusedError(
            RF_PLATFORM_NOT_LOADED, "No radio frequency transmitter is loaded"
        ) from err
    return OOKCommand(frequency=hz, timings=list(timings), repeat_count=repeat_count)


# ---------------------------------------------------------------------------
# The send
# ---------------------------------------------------------------------------


@dataclass
class RadioSend:
    """What one radio send did, transmitter by transmitter."""

    timings: list[int]
    count: int
    air_s: float
    attempted: list[str] = field(default_factory=list)
    landed: set[str] = field(default_factory=set)
    skipped: dict[str, str] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    fits: dict[str, TransmitterFit] = field(default_factory=dict)

    @property
    def on_air_hz(self) -> int | None:
        """The carrier that went out: the first attempted transmitter's."""
        for entity_id in self.attempted:
            fit = self.fits.get(entity_id)
            if fit is not None and fit.send_hz:
                return fit.send_hz
        return None

    @property
    def substituted(self) -> bool:
        return any(
            self.fits[e].substituted for e in self.attempted if e in self.fits
        )


def plan_radio_send(
    hass: Any, row: Any, transmitter_ids: list[str], owner: str
) -> RadioSend:
    """Check everything before the air: refusals raise, skips are kept.

    ``owner`` names the device (or the Sniffer row) for the messages.
    Raises ``SendRefusedError`` when no transmitter can send at all for a
    reason the user can act on (no transmitter of this medium, no
    frequency, none takes it, radio not loaded); returns a plan with no
    attempted transmitter when they are merely unavailable, which the
    caller reports as today's "all unavailable".
    """
    from .rf_band import band_label

    radio_ids = [e for e in transmitter_ids if is_radio_entity(e)]
    if not radio_ids:
        raise SendRefusedError(
            "no_emitter_for_medium", f"{owner} has no radio transmitter"
        )
    frequency_hz = getattr(row, "rf_frequency_hz", None)
    if not frequency_hz:
        raise SendRefusedError(
            RF_NO_FREQUENCY,
            f"{getattr(row, 'name', None) or 'This radio code'} has no frequency; "
            "set its frequency in the editor",
        )
    if _component(hass) is None:
        raise SendRefusedError(
            RF_PLATFORM_NOT_LOADED, "No radio frequency transmitter is loaded"
        )
    timings = wire_frame(row)
    count = send_count_for(row, timings)
    plan = RadioSend(timings=timings, count=count, air_s=burst_air_s(timings, count))
    unfit = 0
    for entity_id in radio_ids:
        state = hass.states.get(entity_id)
        if state is not None and state.state == "unavailable":
            plan.skipped[entity_id] = "unavailable"
            continue
        fit = transmitter_fit(hass, entity_id, frequency_hz)
        plan.fits[entity_id] = fit
        if not fit.ok:
            unfit += 1
            plan.skipped[entity_id] = (
                "declares no frequency; add frequency: to its YAML"
                if fit.code == RF_NO_RANGES
                else f"does not take {band_label(frequency_hz)} MHz"
            )
            continue
        plan.attempted.append(entity_id)
    if not plan.attempted and unfit:
        # Nothing can go out, and at least one transmitter that is up
        # cannot take the carrier. Name the reason the user can act on: a
        # transmitter that declares no frequency is a YAML fix, not a band
        # mismatch; and a transmitter that is merely down may well take it.
        down = sorted(e for e, why in plan.skipped.items() if why == "unavailable")
        no_ranges = all(
            plan.fits[e].code == RF_NO_RANGES
            for e in plan.fits if not plan.fits[e].ok
        )
        if no_ranges:
            message = (
                f"The radio transmitter on {owner} declares no frequency; "
                "add frequency: to its YAML"
            )
        else:
            message = (
                f"No radio transmitter on {owner} that is up takes "
                f"{band_label(frequency_hz)} MHz"
            )
        if down:
            message += f" ({', '.join(down)} unavailable)"
        raise SendRefusedError(RF_FREQUENCY_UNSUPPORTED, message)
    return plan


async def async_transmit(hass: Any, plan: RadioSend) -> RadioSend:
    """Put ``plan`` on the air through each attempted transmitter.

    Per-transmitter guard, as the infrared broadcast has: a timeout or an
    error drops that transmitter and the send goes on; the caller decides
    what a send with nothing landed means.
    """
    from homeassistant.components.radio_frequency import async_send_command

    from .send_plan import emitter_platform
    from .tx_gate import gated_send

    for entity_id in plan.attempted:
        fit = plan.fits[entity_id]
        native = native_repeat(emitter_platform(hass, entity_id))
        command = _ook_command(
            plan.timings, int(fit.send_hz), plan.count - 1 if native else 0
        )
        calls = 1 if native else plan.count
        per_call_air = plan.air_s if native else plan.air_s / plan.count
        for _ in range(calls):
            try:
                await asyncio.wait_for(
                    gated_send(
                        hass, entity_id, command, async_send_command,
                        air_s=per_call_air, medium="rf",
                    ),
                    timeout=ASSIGN_SERVICE_TIMEOUT_S,
                )
                plan.landed.add(entity_id)
            except TimeoutError:
                plan.failures[entity_id] = "timed out"
                break
            except Exception as err:
                plan.failures[entity_id] = str(err) or type(err).__name__
                break
    return plan
