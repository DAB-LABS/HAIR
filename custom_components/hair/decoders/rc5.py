"""RC-5 IR command (Philips) with decode support.

Encode side mirrors ``infrared_protocols.commands.rc5.RC5Command``
byte-for-byte (asserted by round-trip tests), including the RC5X
extension where a command with bit 6 set re-purposes the second start
bit. Decode side is new (upstream is encode-only as of 7.5.0).

RC-5 is Manchester coded: 14 bits of 1778us each, split into two 889us
half-bits. Logic '1' is space-then-mark, logic '0' is mark-then-space,
and adjacent same-sign halves merge on the wire. Frame layout MSB first:
S1 (always 1), S2 (or inverted command bit 6 for RC5X), toggle, 5
address bits, 6 command bits. The toggle bit flips per key press and is
therefore press state, not signal identity -- callers must exclude it
from identity comparisons.

Decoding reverses the Manchester merge: quantize every timing to one or
two half-bit units, rebuild the half-bit lattice (restoring the leading
idle space that S1's first half loses on the wire and the trailing space
the encoder strips), and read bit i from lattice positions 2i/2i+1. A
held key re-sends the frame every 114ms with the toggle constant, so
multi-frame captures majority-vote like every decoder in this package.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, split_frames
from ._base import Command

_HALF_BIT_US = 889
_MODULATION_HZ = 36000
_REPEAT_PERIOD_US = 114000
# Midpoint between one half-bit (889us) and two merged half-bits (1778us).
_HALF_MIDPOINT_US = 1334
_HALF_MIN_US = 400
_HALF_MAX_US = 2500
# Bit-internal spaces top out at 1778us; the inter-frame idle is ~89ms.
_FRAME_GAP_US = 8000

_FRAME_BITS = 14
_FRAME_HALVES = 2 * _FRAME_BITS


def _append_signed_us(timings: list[int], value: int) -> None:
    """Append a microsecond duration, merging into the last entry if same sign."""
    if timings and (timings[-1] > 0) == (value > 0):
        timings[-1] += value
    else:
        timings.append(value)


def _manchester_encode_bit(timings: list[int], bit: int, half_bit_us: int) -> None:
    """Append the two Manchester half-bits for ``bit`` to ``timings``."""
    if bit:
        _append_signed_us(timings, -half_bit_us)
        _append_signed_us(timings, half_bit_us)
    else:
        _append_signed_us(timings, half_bit_us)
        _append_signed_us(timings, -half_bit_us)


def _strip_idle_edges(timings: list[int]) -> None:
    """Drop any leading and trailing space (negative) entries in place."""
    if timings and timings[0] < 0:
        timings.pop(0)
    if timings and timings[-1] < 0:
        timings.pop()


class RC5Command(Command):
    """RC-5 IR command (Philips and derivatives) with decode support."""

    address: int
    command: int
    toggle: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        toggle: int = 0,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the RC-5 IR command."""
        if not 0 <= address <= 0x1F:
            raise ValueError("RC-5 address must be in range 0x00..0x1F")
        if not 0 <= command <= 0x7F:
            raise ValueError("RC-5 command must be in range 0x00..0x7F")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.toggle = toggle

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the RC-5 command (14 bits, Manchester)."""
        start_bit_2 = 0 if self.command & 0x40 else 1
        command_bits = self.command & 0x3F

        bits: list[int] = [1, start_bit_2, self.toggle & 1]
        for i in range(4, -1, -1):
            bits.append((self.address >> i) & 1)
        for i in range(5, -1, -1):
            bits.append((command_bits >> i) & 1)

        frame: list[int] = []
        for bit in bits:
            _manchester_encode_bit(frame, bit, _HALF_BIT_US)
        _strip_idle_edges(frame)

        timings = list(frame)
        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in frame)
            gap = _REPEAT_PERIOD_US - frame_duration
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(frame)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into an RC5Command.

        Returns the majority identity across the frames in the capture,
        with ``repeat_count`` set to the number of extra agreeing frames,
        or None when no frame decodes as RC-5.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (address, command, toggle), votes = result
        return cls(
            address=address,
            command=command,
            toggle=toggle,
            repeat_count=votes - 1,
        )

    @classmethod
    def _decode_frame(cls, frame: Sequence[int]) -> tuple[int, int, int] | None:
        """Decode one RC-5 frame to ``(address, command, toggle)``."""
        halves = cls._to_half_bits(frame, expected_halves=_FRAME_HALVES)
        if halves is None or len(halves) != _FRAME_HALVES:
            return None

        bits: list[int] = []
        for i in range(_FRAME_BITS):
            first, second = halves[2 * i], halves[2 * i + 1]
            if first < 0 and second > 0:
                bits.append(1)
            elif first > 0 and second < 0:
                bits.append(0)
            else:
                return None

        if bits[0] != 1:  # S1 is always 1
            return None
        start_bit_2 = bits[1]
        toggle = bits[2]
        address = 0
        for bit in bits[3:8]:
            address = (address << 1) | bit
        command = 0
        for bit in bits[8:14]:
            command = (command << 1) | bit
        if start_bit_2 == 0:  # RC5X: S2 carries inverted command bit 6
            command |= 0x40
        return (address, command, toggle)

    @staticmethod
    def _to_half_bits(
        frame: Sequence[int], *, expected_halves: int
    ) -> list[int] | None:
        """Expand merged wire timings into a +/-1 half-bit lattice.

        Restores the implicit leading space (S1 transmits space-then-mark
        and the wire strips the leading idle) and, when the frame's last
        bit ends on a stripped space, the implicit trailing space.
        """
        halves: list[int] = [-1]  # implicit first half of S1
        for value in frame:
            magnitude = abs(value)
            if not _HALF_MIN_US <= magnitude <= _HALF_MAX_US:
                return None
            units = 1 if magnitude < _HALF_MIDPOINT_US else 2
            sign = 1 if value > 0 else -1
            halves.extend([sign] * units)
            if len(halves) > expected_halves:
                return None
        if len(halves) == expected_halves - 1:
            halves.append(-1)  # implicit stripped trailing space
        return halves
