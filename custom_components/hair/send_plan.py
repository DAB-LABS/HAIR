"""How one send reaches one emitter, when the row carries a spacing.

A row with ``send_spacing_ms`` set wants its whole-frame repeats to
land on an exact cadence. The only way to get one is to put every
repeat into a single timing list and hand that to the emitter in a
single call: a per-frame loop is paced by the scheduler and the
emitter queue, which the bench measured at plus or minus 60ms with a
floor of about 175ms, so it can never honour a number a user typed.

Not every emitter can take that list. ESPHome and Broadlink can;
Zigbee-behind-MQTT blasters and anything HAIR cannot identify cannot,
and for those the plan falls back to exactly today's per-frame calls
with today's pause between them. The editor refuses to store a value
for a device with no capable emitter at all, so the fallback only ever
runs on a MIXED device, beside a capable emitter that got the bundle.

A row with no spacing value never reaches this module. ``plan_send``
returns None for it and the caller runs the old path untouched.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from .const import (
    BROADLINK_MAX_PACKET_BYTES,
    DOMAIN,
    PIPELINE_MS,
    SEND_AIR_TIME_MAX_MS,
    SEND_REPEAT_GAP,
    SEND_SILENCE_FLOOR_US,
    SEND_SPACING_MAX_MS,
    SEND_SPACING_MIN_MS,
    SINGLE_LIST_MAX_ENTRIES,
)
from .ir_command import (
    TERMINATOR_SPACE_US,
    RepeatedCommand,
    block_duration_us,
    carrier_or_default,
)

_LOGGER = logging.getLogger(__name__)

# Emitter platforms that accept one long raw timing list in one call.
# Everything else -- mqtt, and any entity HAIR cannot resolve to a
# platform -- is "incapable" and takes the old per-frame loop.
EXACT_PLATFORMS = {"esphome", "broadlink"}

# Emitter platforms known to transmit a code with NO CARRIER, for a
# Pronto ``0100`` code (item 6). EMPTY, deliberately, and a platform
# joins it only once somebody has read that integration's infrared
# entity and can say what it does with a modulation of zero. What the
# 2026.7 implementations do today:
#
# - ``broadlink`` never reads ``command.modulation`` at all. Its packet
#   has no carrier field and the hardware modulates at its own fixed
#   rate, so a zero-carrier code would go out modulated. It cannot
#   qualify.
# - ``esphome`` passes ``carrier_frequency=command.modulation`` to the
#   device API unchanged, and ``smlight`` passes it as ``freq``. Both
#   hand a zero onward rather than rejecting it, and neither says what
#   the firmware at the other end does with it. Passing a value on is
#   not evidence that it is honoured, so neither is listed on the
#   strength of a read of the integration alone; a bench capture of a
#   zero-carrier send is what would move them.
# - ``mqtt`` ships no infrared entity at that tag, so there was nothing
#   to read.
#
# The consequence is deliberate and is the honest one: HAIR refuses to
# transmit a non-modulated code rather than sending it modulated and
# calling that a send.
CARRIERLESS_PLATFORMS: set[str] = set()


def can_send_unmodulated(platform: str | None) -> bool:
    """Can this emitter platform transmit a code with no carrier?

    ``None`` means HAIR could not resolve the platform, which reads as
    incapable for the same reason it does in ``emitter_platform``: an
    emitter nobody has checked is not an emitter to send an unusual
    waveform through.
    """
    return platform in CARRIERLESS_PLATFORMS


#: Why an emitter was passed over for a code with no carrier. One
#: string, because the device broadcast path shows it in the skipped
#: list and the Test button shows it in its own result, and two
#: spellings of the same refusal read as two different rules.
NO_CARRIER_REASON = "cannot send a code with no carrier"


def refuse_unmodulated(command: Any, platform: str | None) -> str | None:
    """The reason this emitter may not have this code, or ``None``.

    THE ONE DOOR BOTH SEND PATHS ASK. ``device_manager`` asks it per
    emitter while building its attempt list, and ``test_signal`` asks
    it for the single emitter the Test button names. They asked
    separately once, and only one of them was asking at all, which is
    how a ``0100`` code reached a blaster that modulates everything it
    is handed.
    """
    if not is_unmodulated(command):
        return None
    if can_send_unmodulated(platform):
        return None
    return NO_CARRIER_REASON


def is_unmodulated(command: Any) -> bool:
    """Does this built command carry no carrier?

    Read off the BUILT command rather than off the row, so the refusal
    and the bytes that would go out can never disagree about which one
    of them is non-modulated. ``modulation`` is 0 for exactly the codes
    ``raw_to_pronto`` wrote a ``0100`` header on.
    """
    try:
        return int(getattr(command, "modulation", 38000) or 0) == 0
    except (TypeError, ValueError):
        return False


# The Broadlink packet encoder (python-broadlink's pulses_to_data)
# writes one byte per value under 256 ticks and three bytes above,
# after a four-byte header. The tick is the library default, 32.84us:
# core's broadlink emitter calls pulses_to_data with no tick argument
# and does not pin the library, so this is the value in use today.
# 256 x 32.84 = 8407.04us, verified against the installed library.
_BROADLINK_TICK_US = 32.84
_BROADLINK_HEADER_BYTES = 4

# Stored beside the entry ids on hass.data[DOMAIN], the way
# "_panel_registered" already is. _get_first_entry_data skips it
# because it carries no "device_manager".
_CACHE_KEY = "_send_plan_platform_cache"


@dataclass(frozen=True)
class PlannedCall:
    """One transmit call, with what the call site needs to make it."""

    command: Any
    # False on a chunk that ends on its own seam silence. Wrapping such
    # a chunk would clamp that silence to the 50ms terminator and cut
    # the seam; only the last chunk of a burst is terminated.
    terminate: bool
    air_s: float


@dataclass(frozen=True)
class SendPlan:
    """Everything one emitter needs for one send."""

    calls: list[PlannedCall] = field(default_factory=list)
    # Pause between calls to the SAME emitter. Zero on the bundled
    # path (there is nothing to pace, the list carries its own gaps);
    # SEND_REPEAT_GAP on the incapable path, which is today's loop.
    sleep_s: float = 0.0
    air_s: float = 0.0
    exact: bool = True
    chunks: int = 1


def emitter_platform(hass: Any, entity_id: str) -> str | None:
    """The integration that owns ``entity_id``, or None.

    None means "HAIR cannot tell", and the caller must read that as
    incapable rather than as a default: unit fixtures use bare ids like
    "infrared.a" with no registry entry at all, and guessing capable
    for those would bundle a burst at an emitter nobody has checked.

    Cached per id on the config entry's data, because this is asked
    once per emitter per send. The cache is dropped whenever the entity
    registry changes and when the entry unloads (see
    ``register_platform_cache_invalidation``).
    """
    if hass is None or not entity_id:
        return None
    cache = _cache(hass)
    if cache is not None and entity_id in cache:
        return cache[entity_id]
    platform: str | None = None
    try:
        from homeassistant.helpers import entity_registry as er

        entry = er.async_get(hass).async_get(entity_id)
        platform = entry.platform if entry is not None else None
    except Exception:  # a lookup must never break a send
        platform = None
    if not isinstance(platform, str):
        # Anything that is not a plain platform name is "cannot tell",
        # and cannot tell means incapable. Belt and braces for a
        # registry that hands back something unexpected.
        platform = None
    if cache is not None:
        cache[entity_id] = platform
    return platform


def _cache(hass: Any) -> dict[str, str | None] | None:
    """The per-id platform cache, or None when there is nowhere to put it."""
    data = getattr(hass, "data", None)
    if not isinstance(data, dict):
        return None
    domain_data = data.get(DOMAIN)
    if not isinstance(domain_data, dict):
        return None
    cache = domain_data.get(_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
        domain_data[_CACHE_KEY] = cache
    return cache


def clear_platform_cache(hass: Any) -> None:
    """Forget every cached platform. Cheap; it refills on demand."""
    cache = _cache(hass)
    if cache is not None:
        cache.clear()


def register_platform_cache_invalidation(hass: Any) -> Any:
    """Drop the cache whenever the entity registry moves.

    Always returns an unsubscribe callable, so the config entry can
    hand it straight to async_on_unload. That is the other half of the
    invalidation: unload also clears the cache outright, because an
    entry reload can repoint an emitter at a different integration.
    """
    def _noop() -> None:
        """Nothing was subscribed, so there is nothing to undo."""

    try:
        from homeassistant.helpers.entity_registry import (
            EVENT_ENTITY_REGISTRY_UPDATED,
        )
    except Exception:  # pragma: no cover - HA always provides this
        return _noop

    def _on_registry_update(_event: Any) -> None:
        clear_platform_cache(hass)

    try:
        return hass.bus.async_listen(
            EVENT_ENTITY_REGISTRY_UPDATED, _on_registry_update
        ) or _noop
    except Exception:  # a bus that will not listen must not block setup
        return _noop


def capability(platform: str | None) -> Literal["exact", "incapable"]:
    """Whether ``platform`` can deliver an exact spacing."""
    return "exact" if platform in EXACT_PLATFORMS else "incapable"


def silence_us(block_us: int, spacing_ms: int) -> int:
    """Quiet between two blocks, floored.

    A spacing shorter than the block is not an error, it is a code
    longer than the number asked for. The blocks go out as close
    together as the floor allows and the editor says so.
    """
    return max(SEND_SILENCE_FLOOR_US, int(spacing_ms) * 1000 - int(block_us))


def realised_air_ms(inner: Any, count: int, spacing_ms: int) -> int:
    """Milliseconds of air one send really occupies.

    THE one air-time function: mint, the save doors, the echo ticket
    and the transmit gate all ask this, so a cap, a window and a
    stagger can never disagree about how long a burst is. Ditto frames
    are inside the block, so they are counted here without anything
    having to know they exist.
    """
    count = max(1, int(count))
    block_us = block_duration_us(inner.get_raw_timings())
    gap_us = silence_us(block_us, spacing_ms)
    total_us = count * block_us + (count - 1) * gap_us
    return round(total_us / 1000)


def estimate_spacing_ms(inner: Any) -> int:
    """What this code's repeats are spaced at TODAY, near enough to show.

    Block plus the 50ms terminator plus the measured pipeline mean.
    Rounded to 5ms because the underlying figure has about 60ms of
    spread and a single-millisecond estimate would claim a precision
    the bench does not support.

    Clamped into the stored range. A block over about 940ms clamps to
    the maximum, which is BELOW the block, so the silence floor bites
    immediately; that combination is exactly what mint's air-time check
    refuses, and the editor's floor note explains it when a user gets
    there by hand.
    """
    block_ms = block_duration_us(inner.get_raw_timings()) / 1000
    raw = block_ms + TERMINATOR_SPACE_US / 1000 + PIPELINE_MS
    rounded = round(raw / 5.0) * 5
    return max(SEND_SPACING_MIN_MS, min(SEND_SPACING_MAX_MS, rounded))


# A recorded block may differ from today's by this much before the
# spacing is re-based on it. Two builds of one row agree exactly; this
# only absorbs rounding between two ways of measuring the same bytes.
SPACING_BLOCK_DRIFT_US = 2_000


def _largest_fitting_spacing_ms(block_us: int, count: int) -> int | None:
    """The longest spacing whose burst still fits the air-time cap.

    The largest whole millisecond in the stored range for which
    ``realised_air_ms`` stays within the cap, by that function's own
    arithmetic and rounding, so the answer can never stop short of a
    spacing the cap would accept. None when not even the shortest
    spacing fits, which is a burst the cap refuses whatever the spacing.
    Air time never falls as the spacing grows, so a bisection finds it.
    """
    if count <= 1:
        return SEND_SPACING_MAX_MS

    def fits(spacing: int) -> bool:
        total_us = count * block_us + (count - 1) * silence_us(block_us, spacing)
        return round(total_us / 1000) <= SEND_AIR_TIME_MAX_MS

    if not fits(SEND_SPACING_MIN_MS):
        return None
    low, high = SEND_SPACING_MIN_MS, SEND_SPACING_MAX_MS
    while low < high:
        middle = (low + high + 1) // 2
        if fits(middle):
            low = middle
        else:
            high = middle - 1
    return low


def effective_spacing_ms(
    spacing_ms: int | None,
    inner: Any,
    send_count: int,
    recorded_block_us: int | None,
) -> int | None:
    """The spacing a send actually uses, for the block it actually sends.

    A stored spacing was decided against the block the row built when
    it was minted or saved. When the block has changed since (a tier
    moving between rebuild and replay, a decoder arriving, the carrier
    rule, the raw pin, a ditto count), the number alone no longer means
    what it meant, and the three rules below decide what it means now.
    They never touch the stored value; this is computed at the point of
    use, by both send sites and by the editor, so all three agree.

    1. A row that recorded its block keeps its SILENCE: the spacing
       moves by exactly as much as the block did. That holds whether
       the number was estimated or typed, since the store cannot tell
       the two apart.
    2. A row with no record (older than this field, and not filled at
       load because of the next clause) has only one safe signal: a
       send that would be clamped to the minimum gap, meaning the
       stored spacing is no longer than block plus 10 ms. No one set
       that for this block, so the estimate for this block is used. A
       row squeezed but not down to the floor is left alone.
    3. The count is never changed. When the new spacing would push the
       burst over the air-time cap, it is cut to the largest spacing
       that fits, and never below the stored value: no row is sent
       tighter than it was.
    """
    if spacing_ms is None:
        return None
    stored = int(spacing_ms)
    count = max(1, int(send_count or 1))
    if count <= 1:
        return stored
    block_us = block_duration_us(inner.get_raw_timings())
    if recorded_block_us is not None:
        delta_us = block_us - int(recorded_block_us)
        if abs(delta_us) <= SPACING_BLOCK_DRIFT_US:
            return stored
        wanted = stored + round(delta_us / 1000)
    elif silence_us(block_us, stored) == SEND_SILENCE_FLOOR_US:
        wanted = estimate_spacing_ms(inner)
    else:
        return stored
    wanted = max(SEND_SPACING_MIN_MS, min(SEND_SPACING_MAX_MS, wanted))
    if wanted > stored and realised_air_ms(inner, count, wanted) > (
        SEND_AIR_TIME_MAX_MS
    ):
        fits = _largest_fitting_spacing_ms(block_us, count)
        wanted = stored if fits is None else max(stored, min(wanted, fits))
    return wanted


def record_spacing_block(row: Any) -> None:
    """Write the block ``row``'s spacing is being set against, or None.

    Called by every door that mints or saves a spacing, after the row's
    other knobs are in place, so the block measured is the one the send
    path will build for exactly this row. A row that sends once, or has
    no spacing, records nothing.
    """
    spacing = getattr(row, "send_spacing_ms", None)
    if spacing is None or int(getattr(row, "send_count", 1) or 1) <= 1:
        row.send_spacing_block_us = None
        return
    try:
        row.send_spacing_block_us = block_duration_us(
            build_like_send_path(row).get_raw_timings()
        )
    except Exception:  # a code that will not build has no block to record
        row.send_spacing_block_us = None


def plausible_block_us(value: Any) -> int | None:
    """A length a client says its spacing was worked out against, or None.

    Taken only as a positive whole number of microseconds no longer than
    the air-time cap, since one send longer than the cap could never go
    out. Anything else (a string, a bool, a float, zero, a negative, an
    impossible length) is unknown, never trusted.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value <= 0 or value > SEND_AIR_TIME_MAX_MS * 1000:
        return None
    return value


def store_spacing_block(
    row: Any,
    previous_spacing_ms: int | None,
    *,
    block_us: Any = None,
    block_given: bool = False,
) -> None:
    """Record the length for a spacing a save door has just stored.

    The length belongs with the number it was worked out against, so a
    door never measures it again behind the editor's back:

    - A row that sends once, or has no spacing, records nothing.
    - ``block_given``: the caller's word. A plausible length is recorded.
      Null, or anything implausible, means the caller does not know, and
      nothing is recorded: a number saved before the editor's first
      answer is never stamped with today's length, and rule 2 still
      reaches the row at send time.
    - Not given, spacing unchanged: the record stays, so a save that only
      moved another knob leaves rule 1 to keep the gap at send time.
    - Not given, spacing changed (an API caller, or a panel from before
      the editor carried the length): measured on the row as this save
      leaves it.
    """
    spacing = getattr(row, "send_spacing_ms", None)
    if spacing is None or int(getattr(row, "send_count", 1) or 1) <= 1:
        row.send_spacing_block_us = None
        return
    if block_given:
        row.send_spacing_block_us = plausible_block_us(block_us)
        return
    if previous_spacing_ms is not None and int(spacing) == int(
        previous_spacing_ms
    ):
        return
    record_spacing_block(row)


def clear_block_for_single_send(row: Any) -> None:
    """A row that sends once, or has no spacing, records no length."""
    if (
        getattr(row, "send_spacing_ms", None) is None
        or int(getattr(row, "send_count", 1) or 1) <= 1
    ):
        row.send_spacing_block_us = None


def fill_spacing_block(row: Any) -> bool:
    """The load-time fill for one older row. True when it wrote.

    Only a row with a spacing, a count above one and no record. The
    block recorded is the one THIS release builds, so a change shipping
    in the same release is caught by rule 2, not rule 1. A row whose
    spacing already leaves only the minimum gap is skipped and stays on
    rule 2: recording today's block for it would make today's clamp
    look intended. Never writes ``send_spacing_ms``.
    """
    if getattr(row, "send_spacing_block_us", None) is not None:
        return False
    spacing = getattr(row, "send_spacing_ms", None)
    if spacing is None or int(getattr(row, "send_count", 1) or 1) <= 1:
        return False
    try:
        block_us = block_duration_us(
            build_like_send_path(row).get_raw_timings()
        )
    except Exception:
        return False
    if silence_us(block_us, int(spacing)) == SEND_SILENCE_FLOOR_US:
        return False
    row.send_spacing_block_us = block_us
    return True


def would_send_decoded(row: Any) -> bool:
    """Whether the send path would re-encode this row from its decode.

    device_manager's four-clause test, copied so that mint and the
    editor's read helper build the same block the emitter will get.
    Copied rather than shared on purpose: the two send sites are hot
    and stay exactly as they are (signal_monitor's test path carries
    three of these clauses because a catalog signal cannot be a matrix
    row).
    """
    from .models import CommandSource

    if not getattr(row, "decoded_fingerprint", None):
        return False
    if getattr(row, "tx_force_raw", False):
        return False
    if (
        getattr(row, "matrix_cell", None) is not None
        or getattr(row, "source", None) == CommandSource.MATRIX
    ):
        return False
    if getattr(row, "decode_covers", None) is False:
        return False
    from .protocol_decode import carrier_allows_rebuild

    return carrier_allows_rebuild(
        getattr(row, "decoded_protocol", None), getattr(row, "frequency", None)
    )


def build_like_send_path(row: Any) -> Any:
    """The Command the send path would build for ``row``.

    Used by mint and by the editor's read helper so an estimate and a
    cap are measured against the bytes that will actually go out, not
    against whichever form happened to be convenient.
    """
    from .ir_command import build_command, build_decoded_command

    repeat_count = getattr(row, "repeat_count", 0) or 0
    if would_send_decoded(row):
        cmd = build_decoded_command(
            getattr(row, "decoded_protocol", None),
            getattr(row, "decoded_address", None),
            getattr(row, "decoded_command", None),
            repeat_count=repeat_count,
            decoded_extras=getattr(row, "decoded_extras", None),
        )
        if cmd is not None:
            return cmd
    return build_command(
        protocol=getattr(row, "protocol", None),
        code=getattr(row, "code", None),
        raw_timings=getattr(row, "raw_timings", None),
        frequency=carrier_or_default(getattr(row, "frequency", None)),
        repeat_count=repeat_count,
    )


def broadlink_packet_bytes(timings: list[int]) -> int:
    """Bytes ``pulses_to_data`` would produce for ``timings``.

    One byte per value, three for a value of 256 ticks or more, after a
    four-byte header. The threshold is on the tick-quantized value, so
    8407us is still one byte and 8408us is three.
    """
    total = _BROADLINK_HEADER_BYTES
    for value in timings:
        total += 3 if abs(value) // _BROADLINK_TICK_US >= 256 else 1
    return total


def _fits(platform: str | None, timings: list[int]) -> bool:
    """Whether one call carrying ``timings`` fits the platform's cap."""
    if platform == "broadlink":
        return broadlink_packet_bytes(timings) <= BROADLINK_MAX_PACKET_BYTES
    return len(timings) <= SINGLE_LIST_MAX_ENTRIES


def _chunk_counts(inner: Any, count: int, gap_us: int, platform: str) -> list[int]:
    """How many blocks each call carries, fewest calls first.

    Grows one candidate chunk until it stops fitting, which gives the
    fewest chunks for a uniform block. A single block that does not fit
    on its own still goes out alone: refusing to send at all would be
    worse than one oversized call the emitter may still accept.
    """
    counts: list[int] = []
    remaining = count
    while remaining > 0:
        taken = 0
        for candidate in range(1, remaining + 1):
            trailing = candidate < remaining
            probe = RepeatedCommand(
                inner, candidate, gap_us, trailing_silence=trailing
            ).get_raw_timings()
            if not _fits(platform, probe):
                break
            taken = candidate
        if taken == 0:
            taken = 1
        counts.append(taken)
        remaining -= taken
    return counts


def plan_send(
    inner: Any,
    send_count: int,
    spacing_ms: int | None,
    platform: str | None,
) -> SendPlan | None:
    """The calls one emitter needs, or None for an old row.

    None is the whole two-path split: a row with no stored spacing
    never gets a plan and its caller runs the code it always ran.
    """
    if spacing_ms is None:
        return None

    count = max(1, int(send_count or 1))
    block_us = block_duration_us(inner.get_raw_timings())
    gap_us = silence_us(block_us, spacing_ms)

    if capability(platform) == "incapable":
        # Today's loop, for this emitter only. The frames go out one
        # per call with today's pause between them, which is what the
        # editor's "approximate on this emitter" line is warning about.
        air_s = (count * block_us + (count - 1) * gap_us) / 1_000_000
        per_call = (block_us + TERMINATOR_SPACE_US) / 1_000_000
        return SendPlan(
            calls=[
                PlannedCall(command=inner, terminate=True, air_s=per_call)
                for _ in range(count)
            ],
            sleep_s=SEND_REPEAT_GAP,
            air_s=air_s,
            exact=False,
            chunks=count,
        )

    counts = _chunk_counts(inner, count, gap_us, platform or "")
    calls: list[PlannedCall] = []
    total_us = 0
    for index, chunk_count in enumerate(counts):
        last = index == len(counts) - 1
        command = RepeatedCommand(
            inner, chunk_count, gap_us, trailing_silence=not last
        )
        air_us = command.planned_air_us
        if last:
            air_us += TERMINATOR_SPACE_US
        total_us += air_us
        calls.append(
            PlannedCall(
                command=command,
                terminate=last,
                air_s=air_us / 1_000_000,
            )
        )
    return SendPlan(
        calls=calls,
        sleep_s=0.0,
        air_s=total_us / 1_000_000,
        exact=True,
        chunks=len(counts),
    )


def spacing_air_time_ok(inner: Any, count: int, spacing_ms: int) -> bool:
    """Whether this combination fits SEND_AIR_TIME_MAX_MS."""
    return realised_air_ms(inner, count, spacing_ms) <= SEND_AIR_TIME_MAX_MS
