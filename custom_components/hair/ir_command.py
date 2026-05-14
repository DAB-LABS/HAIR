"""Adapter bridging HAIR's stored IR data to infrared_protocols.Command."""
from __future__ import annotations

import logging

try:
    from infrared_protocols import Command, Timing
except ImportError:  # test environment without infrared_protocols
    import abc
    from dataclasses import dataclass

    class Command(abc.ABC):  # type: ignore[no-redef]
        """Minimal stand-in for infrared_protocols.Command."""

        repeat_count: int
        modulation: int

        def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
            self.modulation = modulation
            self.repeat_count = repeat_count

        @abc.abstractmethod
        def get_raw_timings(self) -> list:
            """Get raw timings."""

    @dataclass(frozen=True)
    class Timing:  # type: ignore[no-redef]
        """Minimal stand-in for infrared_protocols.Timing."""

        high_us: int
        low_us: int

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

        self._timings: list[Timing] = []
        for i in range(total_pairs):
            mark_periods = timing_words[i * 2]
            space_periods = timing_words[i * 2 + 1]
            high_us = round(mark_periods * self._period_us)
            low_us = round(space_periods * self._period_us)
            self._timings.append(Timing(high_us=high_us, low_us=low_us))

        super().__init__(
            modulation=self._frequency,
            repeat_count=repeat_count,
        )

    def get_raw_timings(self) -> list[Timing]:
        """Return mark/space pairs as Timing objects."""
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
        # raw_timings is [mark, -space, mark, -space, ...] or [mark, space, ...]
        # Normalise: take absolute values, pair them up.
        absolutes = [abs(t) for t in raw_timings]
        self._timings: list[Timing] = []
        for i in range(0, len(absolutes) - 1, 2):
            self._timings.append(
                Timing(high_us=absolutes[i], low_us=absolutes[i + 1])
            )
        # If odd number of timings, last mark has no trailing space.
        if len(absolutes) % 2 == 1:
            self._timings.append(
                Timing(high_us=absolutes[-1], low_us=0)
            )

        super().__init__(
            modulation=frequency,
            repeat_count=repeat_count,
        )

    def get_raw_timings(self) -> list[Timing]:
        return list(self._timings)


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
