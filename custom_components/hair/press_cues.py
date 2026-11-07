"""Press cues: where the frame itself says a new press began (GH #237).

HAIR counts a press by three timing windows: the Sniffer's, the
trigger's and the matrix listener's (const.py). A quick double press of
one button lands inside them, so its second press reads as a repeat of
the first. Some protocols carry their own answer in the frame, and this
module reads it before the windows do:

- **Rule N** (NEC, Apple, NEC42, NEC42EXT). A held button sends one full
  frame and then dittos, and the dittos never reach here (they are
  dropped as repeats before decode). So a second full frame of the same
  button on the same receiver, more than one repeat period after the
  first, is a new press. A full frame inside one period is a remote that
  repeats whole frames instead (a Pioneer decodes as NEC); the button is
  remembered as such and left to the windows from then on.
- **Rule T** (RC5, RC6, Marantz, Nokia32). The toggle bit flips on every
  press. A frame whose toggle differs from the previous frame of the same
  button is a new press.
- **Rule J** (JVC). Only a press's first frame carries the leader, and a
  capture decodes as JVC only when it has one, so a second decoded JVC
  capture is a new press.

THE SAFETY PROPERTY. A cue says "new press" or nothing. "Nothing" leaves
every window exactly as it was, so a capture that counts today still
counts; a cue can only let through a press the windows would have
swallowed. And no cue fires sooner than ``PRESS_CUE_REPEAT_FACTOR``
repeat periods after the previous frame, faster than any hand presses
twice.

Everything is per receiver: a button's first frame on a receiver has
nothing to compare with and gives no cue, so the same press reaching a
second receiver is folded by the windows as before. Echoes never get
here; the caller asks only after the echo check has passed.

Pure Python with no Home Assistant import, so the rules can be tested on
their own. Frames inside one merged capture are not counted here; that
needs the decoders' per-frame census and belongs to the full press
detector.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .const import (
    PRESS_CUE_DITTO_PROTOCOLS,
    PRESS_CUE_LEADER_PROTOCOLS,
    PRESS_CUE_REPEAT_FACTOR,
    PRESS_CUE_REPEAT_PERIOD_S,
    PRESS_CUE_TOGGLE_PROTOCOLS,
    PRESS_CUE_TTL_S,
)

RULE_DITTO = "N"
RULE_TOGGLE = "T"
RULE_LEADER = "J"

#: How often ``observe`` sweeps out entries older than the time-to-live.
_PRUNE_EVERY = 200


@dataclass(frozen=True)
class PressCue:
    """A capture the frame itself marks as a new press.

    There is no "same press" cue on purpose: the absence of a cue is
    what leaves the timing windows in charge.
    """

    rule: str
    #: Seconds since the previous frame of this button on this receiver.
    gap_s: float


@dataclass
class _Seen:
    """The last frame of one button on one receiver."""

    at: float
    toggle: int | None
    #: Rule N learned that this button repeats whole frames.
    repeats_full: bool = False


def cue_rule(protocol: str | None) -> str | None:
    """Which rule reads this decoded protocol, if any."""
    if protocol in PRESS_CUE_DITTO_PROTOCOLS:
        return RULE_DITTO
    if protocol in PRESS_CUE_TOGGLE_PROTOCOLS:
        return RULE_TOGGLE
    if protocol in PRESS_CUE_LEADER_PROTOCOLS:
        return RULE_LEADER
    return None


def min_gap_s(protocol: str) -> float:
    """The soonest a new press can follow the previous frame."""
    return PRESS_CUE_REPEAT_FACTOR * PRESS_CUE_REPEAT_PERIOD_S[protocol]


class PressCueTracker:
    """Per (receiver, button) memory of the last frame, and the verdict.

    Keyed by the decoded fingerprint, which excludes toggle bits, so the
    two toggle states of one button share an entry. Entries expire
    ``PRESS_CUE_TTL_S`` after the button was last heard on that receiver.
    """

    def __init__(
        self,
        ttl_s: float = PRESS_CUE_TTL_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_s = ttl_s
        self._clock = clock
        self._seen: dict[tuple[str, str], _Seen] = {}
        self._calls = 0

    def observe(
        self,
        receiver_key: str,
        protocol: str | None,
        fingerprint: str | None,
        extras: Mapping[str, int] | None = None,
    ) -> PressCue | None:
        """Record a decoded capture and say whether it opens a new press.

        Call once per capture that passed the echo check and carries a
        decoded identity that covers it. Returns a ``PressCue`` when the
        frame itself proves a new press, None otherwise.
        """
        rule = cue_rule(protocol)
        if rule is None or not fingerprint:
            return None
        now = self._clock()
        self._calls += 1
        if self._calls % _PRUNE_EVERY == 0:
            self._prune(now)

        key = (receiver_key, fingerprint)
        toggle = None
        if extras is not None and "toggle" in extras:
            toggle = int(extras["toggle"])
        prev = self._seen.get(key)
        if prev is None or now - prev.at > self._ttl_s:
            self._seen[key] = _Seen(at=now, toggle=toggle)
            return None

        gap = now - prev.at
        soonest = min_gap_s(protocol)  # protocol is known: rule is not None
        cue: PressCue | None = None
        if rule == RULE_DITTO:
            if gap <= soonest:
                # Too soon to be a hand: this button repeats whole frames.
                prev.repeats_full = True
            elif not prev.repeats_full:
                cue = PressCue(rule, gap)
        elif rule == RULE_TOGGLE:
            if (
                gap > soonest
                and toggle is not None
                and prev.toggle is not None
                and toggle != prev.toggle
            ):
                cue = PressCue(rule, gap)
        elif gap > soonest:  # RULE_LEADER
            cue = PressCue(rule, gap)

        prev.at = now
        prev.toggle = toggle
        return cue

    def forget_receiver(self, receiver_key: str) -> None:
        """Drop everything learned on a receiver that went away."""
        for key in [k for k in self._seen if k[0] == receiver_key]:
            del self._seen[key]

    def _prune(self, now: float) -> None:
        stale = [k for k, v in self._seen.items() if now - v.at > self._ttl_s]
        for key in stale:
            del self._seen[key]

    def __len__(self) -> int:
        return len(self._seen)
