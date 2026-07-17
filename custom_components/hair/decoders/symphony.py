"""Symphony IR command (encode + decode).

Symphony is the rc_switch-family protocol used by ceiling fans, coolers,
and similar RF-heritage remotes (GH #38, mvdwetering's fan). Not present
in ``infrared_protocols`` as of 7.5.0 -- this module is fresh territory
and the upstream donation candidate is the whole file.

Protocol (timing constants per the ESPHome receiver that decodes these
devices in the field; the code below is written fresh from the spec):

- No header. Bit: 1260us mark + 460us space (1), 460us mark + 1260us
  space (0). MSB first. Valid frame lengths: 8, 12, or 16 bits.
- A transmission is the frame re-sent many times while the button is
  held; frames are separated by a footer gap (~6.9ms) or longer idle.
- No checksum of any kind.

The missing checksum drives two decode rules. First, a capture must
contain at least two agreeing frames before it is accepted -- a single
1260/460-shaped frame is not enough evidence that this is Symphony
rather than line noise. Second, the majority vote across frames decides
the identity: several Symphony remotes transmit vendor preamble frames
(all-zeros, then all-ones) before the button code repeats, and majority
naturally discards them along with truncated tail frames.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, split_frames
from ._base import Command

_SHORT_US = 460
_LONG_US = 1260
# Midpoint between the short (460us) and long (1260us) pulse widths.
_PULSE_MIDPOINT_US = 860
_PULSE_MIN_US = 180
_PULSE_MAX_US = 2200
# Footer gap between repeated frames: 4 * (460 + 1260).
_FOOTER_GAP_US = 4 * (_SHORT_US + _LONG_US)
# Bit spaces top out at 1260us; anything past this separates frames.
_FRAME_GAP_US = 4000

_VALID_NBITS = (8, 12, 16)


class SymphonyCommand(Command):
    """Symphony IR command (8/12/16-bit, rc_switch family)."""

    data: int
    nbits: int

    def __init__(
        self,
        *,
        data: int,
        nbits: int = 12,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Symphony IR command."""
        if nbits not in _VALID_NBITS:
            raise ValueError("Symphony nbits must be one of 8, 12, or 16")
        if not 0 <= data < (1 << nbits):
            raise ValueError("Symphony data is out of range for nbits")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.data = data
        self.nbits = nbits

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Symphony command.

        Symphony receivers lock onto a single frame; ``repeat_count``
        re-sends the frame with the footer gap between repeats, matching
        how the hardware remotes pad for reliability.
        """
        frame: list[int] = []
        for i in range(self.nbits - 1, -1, -1):
            bit = (self.data >> i) & 1
            if bit:
                frame.extend([_LONG_US, -_SHORT_US])
            else:
                frame.extend([_SHORT_US, -_LONG_US])

        timings: list[int] = []
        for _ in range(self.repeat_count + 1):
            timings.extend(frame)
            timings.append(-_FOOTER_GAP_US)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SymphonyCommand.

        Requires at least two agreeing frames (the protocol has no
        checksum; repetition is the only integrity evidence). Preamble
        frames and truncated tails lose the majority vote and are
        discarded. Returns None otherwise.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame, min_votes=2)
        if result is None:
            return None
        (data, nbits), votes = result
        return cls(data=data, nbits=nbits, repeat_count=votes - 1)

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> tuple[int, int] | None:
        """Decode one Symphony frame to ``(data, nbits)``."""
        # Each bit is a (mark, space) pair; the final space may be the
        # (stripped) footer gap, so a frame ending on a mark is valid.
        marks = frame[0::2]
        spaces = frame[1::2]
        if len(marks) not in _VALID_NBITS:
            return None

        bits: list[int] = []
        for index, mark in enumerate(marks):
            if mark <= 0 or not _PULSE_MIN_US <= mark <= _PULSE_MAX_US:
                return None
            long_mark = mark > _PULSE_MIDPOINT_US
            if index < len(spaces):
                space = -spaces[index]
                if not _PULSE_MIN_US <= space <= _PULSE_MAX_US:
                    return None
                # Mark and space widths must disagree (one long, one
                # short); equal-width pairs are not Symphony bits.
                if (space > _PULSE_MIDPOINT_US) == long_mark:
                    return None
            bits.append(1 if long_mark else 0)

        data = 0
        for bit in bits:
            data = (data << 1) | bit
        return (data, len(bits))
