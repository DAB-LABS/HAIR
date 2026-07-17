"""SONY SIRC IR command with decode support.

Encode side mirrors ``infrared_protocols.commands.sony.SonyCommand``
byte-for-byte (asserted by round-trip tests) and adds ``repeat_count``
support: SIRC has no dedicated repeat code, a held button re-sends the
full frame every 45ms, so repeats append whole frames.

Decode side is new (upstream is encode-only as of 7.5.0). SIRC timing:

- Unit T = 600us. Leader: 4T mark. Bit: 1T space, then 1T mark (0) or
  2T mark (1). Data LSB first: 7-bit command, then 5/8/13-bit address
  (SIRC-12/15/20). Trailer: space padding the frame to 45ms.

Real receivers wobble mark widths across the 1T/2T midpoint's
neighborhood (the exact failure that motivated this decoder: HAIR's
generic quantizers fragmented one button into many identities). The
decoder therefore classifies marks by midpoint (900us) inside generous
absolute bounds rather than by narrow per-nominal windows, splits the
capture into frames at the trailer gaps, decodes every frame, and lets
the majority vote decide -- a capture holding two frames and a truncated
third still decodes cleanly, and its identity is byte-identical to a
single-frame capture of the same button.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command

_UNIT_US = 600
_LEADER_US = 4 * _UNIT_US
# Midpoint between the 1T (600us) and 2T (1200us) mark widths.
_MARK_MIDPOINT_US = 900
# Sanity bounds for any data mark / space; outside these the frame is
# rejected rather than classified.
_MARK_MIN_US = 240
_MARK_MAX_US = 2100
_SPACE_MIN_US = 240
_SPACE_MAX_US = 1200
# A space at least this long separates SIRC frames (bit spaces are 1T).
_FRAME_GAP_US = 4000
_FRAME_PERIOD_US = 45000

_TOTAL_BITS_TO_ADDRESS_BITS = {12: 5, 15: 8, 20: 13}


class SonyCommand(Command):
    """SONY SIRC IR command (12/15/20-bit) with decode support."""

    address: int
    address_bits: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        address_bits: int,
        command: int,
        modulation: int = 40000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the SONY SIRC IR command."""
        if address_bits not in (5, 8, 13):
            raise ValueError("SONY SIRC address_bits must be one of 5, 8, or 13")
        if not 0 <= address < (1 << address_bits):
            raise ValueError("SONY SIRC address is out of range for address_bits")
        if not 0 <= command <= 0x7F:
            raise ValueError("SONY SIRC command must be in range 0x00..0x7F")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.address_bits = address_bits
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the SONY SIRC command.

        SIRC has no repeat code; ``repeat_count`` re-sends the same frame,
        each frame occupying the full 45ms period (trailer space pads).
        """
        total_bits = 7 + self.address_bits
        data = self.command | (self.address << 7)

        frame: list[int] = [_LEADER_US]
        bits = data
        for _ in range(total_bits):
            bit = bits & 1
            frame.append(-_UNIT_US)
            frame.append(2 * _UNIT_US if bit else _UNIT_US)
            bits >>= 1

        # Trailer pads each frame to the 45ms period. With repeat_count == 0
        # this matches the upstream encoder byte-for-byte (asserted in
        # tests); repeats re-send the identical frame, per the SIRC spec.
        trailer_low = _FRAME_PERIOD_US - sum(abs(t) for t in frame)
        timings: list[int] = []
        for _ in range(self.repeat_count + 1):
            timings.extend(frame)
            timings.append(-trailer_low)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SonyCommand.

        Splits the capture into frames at trailer gaps, decodes each frame
        independently, and returns the majority identity with
        ``repeat_count`` set to the number of extra agreeing frames.
        Returns None if no frame decodes as SIRC.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (address, address_bits, command), votes = result
        return cls(
            address=address,
            address_bits=address_bits,
            command=command,
            repeat_count=votes - 1,
        )

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> tuple[int, int, int] | None:
        """Decode one SIRC frame to ``(address, address_bits, command)``."""
        # Leader mark, then (space, mark) per bit.
        if len(frame) < 1 + 2 * 12:
            return None
        if not is_close(frame[0], _LEADER_US):
            return None

        bits: list[int] = []
        i = 1
        while i + 1 < len(frame) and len(bits) < 20:
            space = -frame[i]
            mark = frame[i + 1]
            if not _SPACE_MIN_US <= space <= _SPACE_MAX_US:
                return None
            if not _MARK_MIN_US <= mark <= _MARK_MAX_US:
                return None
            bits.append(1 if mark > _MARK_MIDPOINT_US else 0)
            i += 2

        total_bits = len(bits)
        address_bits = _TOTAL_BITS_TO_ADDRESS_BITS.get(total_bits)
        if address_bits is None:
            return None
        # Any mark left inside the frame means it held more pairs than a
        # valid SIRC bit count; reject rather than truncate.
        if any(value > 0 for value in frame[i:]):
            return None

        data = 0
        for index, bit in enumerate(bits):
            data |= bit << index
        command = data & 0x7F
        address = data >> 7
        return (address, address_bits, command)
