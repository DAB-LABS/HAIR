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
