"""Dyson fan/purifier IR command with decode support.

The "Dysan" protocol of the JP1 world (hifi-remote.com t=101540),
carried by Dyson AM/TP/HP-family fans. Canonical IRP:

    {780,38k}<1,-1|1,-2>(3,-1,D:7,F:8,1,-104m)

- 38 kHz carrier, 780us base unit, space-length encoding.
- Leader: 2340us mark (3 units), 780us space.
- 15 payload bits, LSB-first per field: D:7 then F:8. Bit 0 is
  780us mark + 780us space; bit 1 is 780us mark + 1560us space.
- Single 780us trailer mark, then a ~104ms frame period.
- NO checksum of any kind.

The F byte is really two fields: the button (upper 6 bits) and a
mod-4 ROLLING COUNTER in the low 2 bits that increments on every
press -- and on every second frame while a button is held. The fan
tracks the last counter it accepted and rejects a frame that reuses
it: true anti-replay rotation, and the root cause of the ~33%
replay-reliability symptom (GH #33, Esp32-zapper). HAIR therefore
treats device+function as identity and the counter as press state,
exactly like an RC-5 toggle: it rides in ``decoded_extras`` and the
transmit path advances it after every logical press.

Device values seen in the wild: 5 (AM02/AM03 towers), 9 (AM04/AM07/
AM09 -- the ``0b1001000`` preamble of upstream's encoder is this same
value in MSB form). Purifier-family device codes exist but are
undocumented; the decoder reads whatever 7-bit value arrives rather
than pinning a known list.

Upstream ``infrared_protocols`` ships an encode-only DysonCoolCommand
(v7.3.0+) whose enum freezes three counter values of the same power
button as distinct codes; it has no decoder and no counter handling,
so this local class serves both directions and is NOT registered with
an upstream fallback (revisit if upstream grows a real decoder).

Protocol research: JP1 forum (3FG/The Robman), the 2013 AM02
reverse-engineering writeup, and upstream PR #60 -- survey logged in
docs/internal/research/dyson-ir-protocol.md.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command

_UNIT_US = 780
_LEADER_MARK_US = 3 * _UNIT_US  # 2340
_LEADER_SPACE_US = _UNIT_US
_BIT_MARK_US = _UNIT_US
_ZERO_SPACE_US = _UNIT_US       # 780
_ONE_SPACE_US = 2 * _UNIT_US    # 1560
# The two bit spaces are one unit apart; the default 0.4 band would
# let a ~1000us space match both nominals. 0.3 keeps them disjoint.
_TOLERANCE = 0.3

_DATA_BITS = 15  # D:7 + F:8 (F = function:6 + counter:2)
# leader pair (2) + 15 bit pairs (30) + trailer mark (1)
_MIN_FRAME_LEN = 2 + _DATA_BITS * 2 + 1
# Largest intra-frame space is 1560us; the inter-frame period is
# ~104ms. Any space of 8ms+ is a frame boundary, never a bit.
_FRAME_GAP_US = 8000


class DysonCommand(Command):
    """Dyson IR command with decode support."""

    device: int
    function: int
    counter: int

    def __init__(
        self,
        *,
        device: int,
        function: int,
        counter: int = 0,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Dyson IR command.

        :param device: fan family code D (7 bits; 5=AM02/03, 9=AM04/07/09)
        :param function: button code (6 bits)
        :param counter: mod-4 rolling press counter (2 bits; press
            state, not identity -- the fan rejects a reused value)
        """
        super().__init__(modulation=modulation)
        self.device = device & 0x7F
        self.function = function & 0x3F
        self.counter = counter & 0x3

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Dyson command.

        Positive values are mark (high) durations in microseconds;
        negative values are space (low) durations. One frame: leader,
        fifteen LSB-first bits (D:7 then F:8 with the counter in F's
        low two bits), trailer mark.
        """
        f_byte = ((self.function & 0x3F) << 2) | (self.counter & 0x3)
        timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        for field, width in ((self.device, 7), (f_byte, 8)):
            for bit_index in range(width):  # LSB first
                bit = (field >> bit_index) & 1
                timings.append(_BIT_MARK_US)
                timings.append(
                    -_ONE_SPACE_US if bit else -_ZERO_SPACE_US
                )
        timings.append(_BIT_MARK_US)  # trailer
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a DysonCommand, or None.

        The capture is split into frames at the ~104ms period and each
        frame decodes independently. A held button re-sends the frame
        with the counter advancing every second frame, so the majority
        vote runs on the full (device, function, counter) tuple; ties
        resolve to the earliest frame, and either way the device and
        function -- the identity half -- are unanimous.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (device, function, counter), _votes = result
        return cls(device=device, function=function, counter=counter)

    @classmethod
    def _decode_frame(
        cls, frame: Sequence[int]
    ) -> tuple[int, int, int] | None:
        """Decode one frame to (device, function, counter), or None.

        Leader, fifteen classified bits, trailer mark; any timing
        outside tolerance rejects the frame. The protocol has no
        checksum, so this strictness is the only thing keeping a
        foreign frame from decoding as Dyson.
        """
        if len(frame) < _MIN_FRAME_LEN:
            return None
        if not is_close(frame[0], _LEADER_MARK_US, _TOLERANCE):
            return None
        if not is_close(-frame[1], _LEADER_SPACE_US, _TOLERANCE):
            return None

        bits: list[int] = []
        for i in range(_DATA_BITS):
            mark = frame[2 + 2 * i]
            space = -frame[3 + 2 * i]
            if not is_close(mark, _BIT_MARK_US, _TOLERANCE):
                return None
            bit = cls._classify_space(space)
            if bit is None:
                return None
            bits.append(bit)

        trailer = frame[2 + 2 * _DATA_BITS]
        if not is_close(trailer, _BIT_MARK_US, _TOLERANCE):
            return None
        # Only the inter-frame gap (or a truncated capture) may follow
        # the trailer; a further mark means split_frames failed to
        # separate something -- reject to be safe.
        if any(value_after > 0 for value_after in frame[_MIN_FRAME_LEN:]):
            return None

        device = 0
        for bit_index in range(7):  # LSB first
            device |= bits[bit_index] << bit_index
        f_byte = 0
        for bit_index in range(8):
            f_byte |= bits[7 + bit_index] << bit_index
        return (device, (f_byte >> 2) & 0x3F, f_byte & 0x3)

    @staticmethod
    def _classify_space(space_us: int) -> int | None:
        """Classify a bit space as 0 (780us) or 1 (1560us), or None."""
        if is_close(space_us, _ZERO_SPACE_US, _TOLERANCE):
            return 0
        if is_close(space_us, _ONE_SPACE_US, _TOLERANCE):
            return 1
        return None
