"""Adapter bridging HAIR's stored IR data to infrared_protocols.Command.

As of infrared-protocols v2.0.0 (HA 2026.5), ``get_raw_timings()`` returns
``list[int]`` with signed microsecond values (positive = mark, negative =
space).  Earlier versions (v1.x, HA 2026.4) used a ``Timing`` dataclass.
This module targets the v2.0 contract so it works on HA 2026.5+ and remains
forward-compatible.  The v1.x ESPHome emitter flattened ``Timing`` objects
to signed ints at the call site, so flat ints also work there.
"""
from __future__ import annotations

import logging

try:
    from infrared_protocols import Command
except ImportError:  # test environment without infrared_protocols
    import abc

    class Command(abc.ABC):  # type: ignore[no-redef]
        """Minimal stand-in for infrared_protocols.Command."""

        repeat_count: int
        modulation: int

        def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
            self.modulation = modulation
            self.repeat_count = repeat_count

        @abc.abstractmethod
        def get_raw_timings(self) -> list[int]:
            """Get raw timings as signed microsecond integers."""

_LOGGER = logging.getLogger(__name__)

# Pronto hex word 0 == 0x0000 means "learned / raw" format.
_PRONTO_LEARNED = 0x0000
# Pronto frequency is encoded as 1_000_000 / (word[1] * 0.241246).
_PRONTO_FREQ_FACTOR = 0.241246


# The transmit-side trailing terminator (GH #93 -> GH #98). Two
# hardware constraints meet at the emitter: 16-bit formats (Tuya and
# ZoSung blasters behind Zigbee2MQTT) reject any timing value over
# 65,535us, so a captured Broadlink RM's ~102ms learning-timeout gap
# cannot ride out as-is (GH #93) -- while Broadlink RM4 Pro firmware
# garbles a pulse stream that does not END on a space, because every
# packet the device ever produces itself ends with that same capture
# timeout (GH #98: dead commands, one transmitting a bogus ~8ms
# trailing mark the source never contained; the RM4 Mini tolerated
# the identical stream). 0.9.8's constructor strip satisfied the
# first constraint and violated the second. A BOUNDED terminator,
# added ONLY at the transmit boundary, satisfies both: 50ms fits
# uint16 with margin, exceeds the largest interior frame gap in the
# SmartIR corpus (the Daikin 35ms), and is dead air to any receiver.
TERMINATOR_SPACE_US = 50_000


def _normalize_trailing_space(timings: list[int]) -> None:
    """End the array on a bounded space, in place.

    Oversized trailing space -> clamped to TERMINATOR_SPACE_US.
    Ends on a mark (every stripped replay, and gapless 0.9.8-era
    imports) -> a terminator space is appended. A small trailing
    space passes untouched. Empty -> no-op.
    """
    if not timings:
        return
    if timings[-1] < 0:
        if -timings[-1] > TERMINATOR_SPACE_US:
            timings[-1] = -TERMINATOR_SPACE_US
        return
    timings.append(-TERMINATOR_SPACE_US)


class TerminatedCommand(Command):
    """Transmit-boundary wrapper adding the bounded terminator.

    Wraps the command actually handed to an emitter (gated_send in
    device_manager._async_broadcast and signal_monitor's test path)
    so its timing array ends on a bounded space. Parse-side consumers
    (identity, triggers, decode, storage) construct ProntoCommand /
    RawTimingsCommand directly and are NEVER wrapped: the constructor
    strip below has been part of signal identity since 0.9.8 and must
    stay byte-stable, or every stored identity splits again.
    """

    def __init__(self, inner: Command) -> None:
        # Deliberately no super().__init__: modulation and
        # repeat_count delegate through __getattr__ below, so the
        # wrapper never has to introspect (or get ahead of) whatever
        # the inner command carries.
        self._inner = inner

    def get_raw_timings(self) -> list[int]:
        timings = list(self._inner.get_raw_timings())
        _normalize_trailing_space(timings)
        return timings

    def __getattr__(self, name: str):
        # Transparent for everything else (decoded fields, toggle
        # counters, whatever the platform or the Mirror inspects):
        # only the timing array differs from the inner command.
        return getattr(self._inner, name)


class ProntoCommand(Command):
    """Wrap a Pronto hex string as an infrared_protocols.Command."""

    def __init__(
        self,
        pronto_hex: str,
        *,
        repeat_count: int = 0,
    ) -> None:
        words = [int(w, 16) for w in pronto_hex.split()]
        if len(words) < 4:
            raise ValueError("Pronto hex too short (need at least 4 words)")

        freq_word = words[1]
        if freq_word == 0:
            raise ValueError("Pronto frequency word is zero")

        self._frequency = round(1_000_000 / (freq_word * _PRONTO_FREQ_FACTOR))
        self._period_us = freq_word * _PRONTO_FREQ_FACTOR  # microseconds per period

        burst1_pairs = words[2]
        burst2_pairs = words[3]
        total_pairs = burst1_pairs + burst2_pairs
        timing_words = words[4:]

        if len(timing_words) < total_pairs * 2:
            raise ValueError(
                f"Pronto hex declares {total_pairs} pairs but only "
                f"{len(timing_words)} timing words remain"
            )

        self._timings: list[int] = []
        for i in range(total_pairs):
            mark_periods = timing_words[i * 2]
            space_periods = timing_words[i * 2 + 1]
            mark_us = round(mark_periods * self._period_us)
            space_us = round(space_periods * self._period_us)
            self._timings.append(mark_us)
            if space_us > 0:
                self._timings.append(-space_us)

        # SmartIR trailing gap (smartir-trailing-gap.md, 4a): drop a
        # trailing space of any size before it reaches an emitter. This
        # is safe because (1) a transmitter stops at the end of the
        # timings array regardless of what the final value is -- the
        # source formats themselves say a trailing silence is
        # meaningless on transmit -- and (2) whole-frame send_count
        # spacing never came from this value; it's produced by
        # device_manager._async_broadcast's own SEND_REPEAT_GAP sleep
        # between frames. Left in place, this same value is a captured
        # Broadlink RM's ~102ms learning-mode timeout, which 16-bit
        # emitters (Tuya/ZoSung) reject outright (GH #93). A trailing
        # MARK is left untouched -- that would be a malformed code, a
        # different problem for the comb, not this strip. The transmit
        # boundary re-adds a BOUNDED trailing space after this strip
        # (GH #98, TerminatedCommand above): the strip is part of
        # signal identity and stays; the wire gets its terminator.
        if self._timings and self._timings[-1] < 0:
            self._timings.pop()

        super().__init__(
            modulation=self._frequency,
            repeat_count=repeat_count,
        )

    def get_raw_timings(self) -> list[int]:
        """Return signed microsecond timings (positive=mark, negative=space)."""
        return list(self._timings)


class RawTimingsCommand(Command):
    """Wrap raw microsecond timings (alternating mark/space ints)."""

    def __init__(
        self,
        raw_timings: list[int],
        *,
        frequency: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        # Normalise to signed convention: positive=mark, negative=space.
        # Input may be [mark, space, mark, space] (all positive) or
        # [mark, -space, mark, -space] (already signed).
        self._timings: list[int] = []
        for i, val in enumerate(raw_timings):
            if i % 2 == 0:
                # Mark (odd index in 0-based = even position = mark)
                self._timings.append(abs(val))
            else:
                # Space
                self._timings.append(-abs(val))

        # SmartIR trailing gap (smartir-trailing-gap.md, 4a): same strip
        # as ProntoCommand above -- sniffed raw rows carry their own
        # receiver-side trailing gaps, and the same transmit-safety
        # reasoning applies (see the comment there for the full case).
        if self._timings and self._timings[-1] < 0:
            self._timings.pop()

        super().__init__(
            modulation=frequency,
            repeat_count=repeat_count,
        )

    def get_raw_timings(self) -> list[int]:
        """Return signed microsecond timings (positive=mark, negative=space)."""
        return list(self._timings)


def raw_to_pronto(
    timings: list[int],
    frequency: int = 38000,
) -> str:
    """Convert signed microsecond timings to a Pronto hex string.

    This is the inverse of ``ProntoCommand``: given raw mark/space
    microsecond values and a carrier frequency, produce a Pronto hex
    string suitable for storage and fingerprinting.

    Args:
        timings: Signed microsecond values (positive=mark, negative=space).
            May also be unsigned alternating mark/space.
        frequency: Carrier frequency in Hz (default 38 kHz).

    Returns:
        Pronto hex string (e.g. "0000 006D 0016 0000 ...").
    """
    if not timings:
        raise ValueError("Cannot encode empty timings to Pronto hex")
    if frequency <= 0:
        raise ValueError(f"Invalid carrier frequency: {frequency}")

    # Pronto frequency word: freq_word = 1_000_000 / (frequency * 0.241246)
    freq_word = round(1_000_000 / (frequency * _PRONTO_FREQ_FACTOR))
    period_us = freq_word * _PRONTO_FREQ_FACTOR  # microseconds per period

    # Build mark/space pairs from raw timings.
    pairs: list[tuple[int, int]] = []
    i = 0
    while i < len(timings):
        mark_us = abs(timings[i])
        space_us = abs(timings[i + 1]) if i + 1 < len(timings) else 0
        mark_periods = round(mark_us / period_us)
        space_periods = round(space_us / period_us)
        pairs.append((mark_periods, space_periods))
        i += 2

    # Pronto format: type(0000) freq burst1_count burst2_count timing_words...
    # All pairs go into burst sequence 1; burst sequence 2 is empty.
    words: list[int] = [_PRONTO_LEARNED, freq_word, len(pairs), 0]
    for mark, space in pairs:
        words.extend([mark, space])

    return " ".join(f"{w:04X}" for w in words)


def snap_pronto(pronto: str, target_frequency: int) -> str:
    """Re-encode a normalized Pronto string at a standard carrier.

    Derives the raw mark/space timings from the Pronto and re-encodes them at
    ``target_frequency`` via :func:`raw_to_pronto`, preserving the burst
    timings while correcting the carrier. The caller validates ``pronto`` and
    that ``target_frequency`` is a known standard.
    """
    raw = ProntoCommand(pronto).get_raw_timings()
    return raw_to_pronto(raw, frequency=target_frequency)


def build_decoded_command(
    decoded_protocol: str | None,
    decoded_address: int | None,
    decoded_command: int | None,
    *,
    repeat_count: int = 0,
    decoded_extras: dict[str, int] | None = None,
) -> Command | None:
    """Build a protocol-native Command from decoded fields, or ``None``.

    Returns a canonical-timing Command when the decoded protocol is
    registered on the rebuild tier, so transmit re-encodes clean timings
    instead of replaying captured (receiver-distorted) ones -- the
    frafall (GH #14) fix, generalized to every registered protocol in
    v0.6.0. ``decoded_extras`` carries protocol state the re-encode
    needs (RC-5/Marantz toggle, Sharp extension). Returns ``None`` when
    the protocol is unregistered, identity-only, a field is missing, or
    the library is unavailable, so the caller falls back to Pronto/raw
    replay.
    """
    from .protocol_decode import build_protocol_command

    cmd = build_protocol_command(
        decoded_protocol,
        decoded_address,
        decoded_command,
        extras=decoded_extras,
    )
    if cmd is None:
        return None
    if repeat_count:
        cmd.repeat_count = repeat_count
    return cmd


def build_command(
    *,
    protocol: str | None = None,
    code: str | None = None,
    raw_timings: list[int] | None = None,
    frequency: int = 38000,
    repeat_count: int = 0,
) -> Command:
    """Factory: build the right Command subclass from HAIR's stored data.

    Pronto hex is identified by ``protocol`` being "PRONTO" (case-insensitive)
    or by ``code`` starting with "0000 " (Pronto learned format marker).

    Falls back to RawTimingsCommand when raw timing ints are available.

    Raises ValueError if neither Pronto hex nor raw timings are usable.
    """
    is_pronto = False
    if (protocol and protocol.upper() == "PRONTO") or (code and code.startswith("0000 ")):
        is_pronto = True

    if is_pronto and code:
        return ProntoCommand(code, repeat_count=repeat_count)

    if raw_timings:
        return RawTimingsCommand(
            raw_timings,
            frequency=frequency,
            repeat_count=repeat_count,
        )

    raise ValueError(
        "Cannot build IR command: no Pronto hex code and no raw timings"
    )
