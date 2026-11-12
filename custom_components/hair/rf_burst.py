"""Bursts: a press that arrives one frame per capture, put back together.

A radio remote repeats its frame several times per press. A receiver
whose idle is shorter than the remote's inter-frame gap (an ESPHome
board on a fixed 433 MHz module, for one) ends a capture at every gap,
so a press arrives as one capture per frame. A single capture then
never holds the two agreeing frames ``rf_frames.analyze`` needs, and
the press has to be collected across captures before it can vote.

KEYED BY FINGERPRINT, NOT BY TIME ALONE. Such a receiver also reports
noise continuously, three to five captures a second with nobody
pressing anything, so the silence between captures rarely reaches even
a fifth of a second. A burst that took every capture would almost
never end. A burst is therefore the frames of ONE fingerprint: each
bodied frame joins the open burst of its own fingerprint, and noise of
any other fingerprint neither joins nor extends it. Noise with no body
never gets here.

A burst ends when no frame of its fingerprint has arrived for
``RF_BURST_SILENCE_S``, or ``RF_BURST_HOLD_S`` after it began, so a key
held for several seconds becomes a burst every ``RF_BURST_HOLD_S``. At
most ``RF_PENDING_MAX`` bursts are open at once; opening one more ends
the oldest first. An ended burst goes to the vote
(``rf_frames.vote``) when it holds at least ``RF_MIN_FRAMES`` frames,
and is counted as a lone frame otherwise. The gate is the one a whole capture
passes: enough agreeing frames, each with a body.

ONE TIMER per assembler, re-armed to the earliest deadline, so a busy
receiver costs no timer per capture. The clock and the timer are passed
in, so the tests replay recorded captures at their real spacing.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .const import (
    RF_BURST_HOLD_S,
    RF_BURST_SILENCE_S,
    RF_MIN_FRAMES,
    RF_PENDING_MAX,
)
from .rf_frames import FrameParts, FramePiece, RfCapture, vote


@dataclass
class _Burst:
    fingerprint: str
    opened_at: float
    last_at: float
    frames: list[tuple[FramePiece, FrameParts]] = field(default_factory=list)
    # The last signal that fed the burst: what the frequency ladder reads
    # when the burst is handed on.
    signal: Any = None

    @property
    def deadline(self) -> float:
        return min(self.last_at + RF_BURST_SILENCE_S, self.opened_at + RF_BURST_HOLD_S)


class BurstAssembler:
    """Collects one receiver's split-delivered frames into presses.

    ``on_burst(analysis, signal, frames, fingerprint)`` receives each
    burst that passed the vote, with the last signal object that fed it,
    how many frames the burst held and the fingerprint it was keyed by;
    ``on_lone(fingerprint)`` is called for each burst that ended without
    a vote (a lone frame).
    ``call_at(when, fn)`` schedules ``fn`` at the clock's ``when`` and
    returns a handle with ``cancel()``; ``now()`` reads that clock.
    """

    def __init__(
        self,
        *,
        on_burst: Callable[[RfCapture, Any, int, str], None],
        on_lone: Callable[[str], None],
        call_at: Callable[[float, Callable[[], None]], Any],
        now: Callable[[], float],
    ) -> None:
        self._on_burst = on_burst
        self._on_lone = on_lone
        self._call_at = call_at
        self._now = now
        self._open: dict[str, _Burst] = {}
        self._timer: Any = None
        self._timer_at: float | None = None

    @property
    def open_count(self) -> int:
        return len(self._open)

    def add(
        self,
        fingerprint: str,
        frame: tuple[FramePiece, FrameParts],
        signal: Any = None,
    ) -> None:
        """One bodied frame from one capture."""
        now = self._now()
        burst = self._open.get(fingerprint)
        if burst is not None and now >= burst.deadline:
            # Its deadline passed before the timer ran: it is over, and
            # this frame begins the next press.
            self._end(burst)
            burst = None
        if burst is None:
            if len(self._open) >= RF_PENDING_MAX:
                self._end(min(self._open.values(), key=lambda b: b.opened_at))
            burst = _Burst(fingerprint, now, now)
            self._open[fingerprint] = burst
        burst.frames.append(frame)
        burst.last_at = now
        burst.signal = signal
        self._arm()

    def flush(self) -> None:
        """End every open burst now, voting each."""
        for burst in list(self._open.values()):
            self._end(burst)
        self._cancel()

    def discard(self) -> None:
        """Drop every open burst unvoted (the receiver is going away, or
        HAIR is stopping): half a press is not worth a row."""
        self._open.clear()
        self._cancel()

    def _end(self, burst: _Burst) -> None:
        if self._open.get(burst.fingerprint) is burst:
            del self._open[burst.fingerprint]
        analysis = vote(burst.frames) if len(burst.frames) >= RF_MIN_FRAMES else None
        if analysis is None:
            self._on_lone(burst.fingerprint)
        else:
            self._on_burst(
                analysis, burst.signal, len(burst.frames), burst.fingerprint
            )

    def _cancel(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = None
        self._timer_at = None

    def _arm(self) -> None:
        if not self._open:
            self._cancel()
            return
        earliest = min(burst.deadline for burst in self._open.values())
        if self._timer_at is not None and self._timer_at <= earliest:
            return  # the timer already set will run first and re-arm
        self._cancel()
        self._timer_at = earliest
        self._timer = self._call_at(earliest, self._on_timer)

    def _on_timer(self) -> None:
        self._timer = None
        self._timer_at = None
        now = self._now()
        for burst in [b for b in self._open.values() if now >= b.deadline]:
            self._end(burst)
        self._arm()
