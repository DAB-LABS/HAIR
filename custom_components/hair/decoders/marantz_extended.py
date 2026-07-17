"""Marantz extended IR command with decode support.

Encode side mirrors
``infrared_protocols.commands.marantz_extended.MarantzExtendedCommand``
byte-for-byte (asserted by round-trip tests). Decode side is new
(upstream is encode-only as of 7.5.0).

Marantz extended is RC-5 with a fixed mid-frame pause and six extension
bits: 8 leader bits (S1, S2/field, toggle, 5 address bits), a pause of
exactly four RC-5 half-bit units of space, then 12 trailing bits (6
command + 6 extension), all Manchester coded at the RC-5 rate. On the
wire the pause merges with any adjacent space half-bits, so the decoder
works on the reconstructed half-bit lattice: 16 leader halves, 4 pause
halves (all space), 24 trailing halves -- 44 in total, with the same
implicit leading/trailing space restoration RC-5 needs. The toggle bit
is press state, not identity, exactly as in RC-5.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, split_frames
from ._base import Command
from .rc5 import (
    _append_signed_us,
    _manchester_encode_bit,
    _strip_idle_edges,
)

_HALF_BIT_US = 889
_MODULATION_HZ = 36000
_REPEAT_PERIOD_US = 114000
_PAUSE_US = 4 * _HALF_BIT_US
# The longest legitimate run is the pause plus a space half-bit on each
# side: six half-bit units (~5334us). Larger spaces separate frames.
_FRAME_GAP_US = 8000
_MAX_RUN_UNITS = 6
_UNIT_TOLERANCE_US = 400

_LEADER_HALVES = 16  # S1, S2, T, A4..A0
_PAUSE_HALVES = 4
_TRAILING_HALVES = 24  # C5..C0, E5..E0
_FRAME_HALVES = _LEADER_HALVES + _PAUSE_HALVES + _TRAILING_HALVES


class MarantzExtendedCommand(Command):
    """Marantz extended IR command with decode support."""

    address: int
    command: int
    extension: int
    toggle: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        extension: int,
        toggle: int = 0,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Marantz extended IR command."""
        if not 0 <= address <= 0x1F:
            raise ValueError("Marantz address must be in range 0x00..0x1F")
        if not 0 <= command <= 0x7F:
            raise ValueError("Marantz command must be in range 0x00..0x7F")
        if not 0 <= extension <= 0x3F:
            raise ValueError("Marantz extension must be in range 0x00..0x3F")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.extension = extension
        self.toggle = toggle

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Marantz extended command."""
        start_bit_2 = 0 if self.command & 0x40 else 1
        command_bits = self.command & 0x3F

        leader_bits: list[int] = [1, start_bit_2, self.toggle & 1]
        for i in range(4, -1, -1):
            leader_bits.append((self.address >> i) & 1)

        trailing_bits: list[int] = []
        for i in range(5, -1, -1):
            trailing_bits.append((command_bits >> i) & 1)
        for i in range(5, -1, -1):
            trailing_bits.append((self.extension >> i) & 1)

        frame: list[int] = []
        for bit in leader_bits:
            _manchester_encode_bit(frame, bit, _HALF_BIT_US)
        _append_signed_us(frame, -_PAUSE_US)
        for bit in trailing_bits:
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
        """Decode raw IR timings into a MarantzExtendedCommand.

        Returns the majority identity across the capture's frames, or
        None when no frame decodes as Marantz extended.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (address, command, extension, toggle), votes = result
        return cls(
            address=address,
            command=command,
            extension=extension,
            toggle=toggle,
            repeat_count=votes - 1,
        )

    @classmethod
    def _decode_frame(
        cls, frame: Sequence[int]
    ) -> tuple[int, int, int, int] | None:
        """Decode one frame to ``(address, command, extension, toggle)``."""
        halves = cls._to_half_bits(frame)
        if halves is None:
            return None

        # The pause occupies four space halves between the leader and
        # trailing sections.
        if any(h > 0 for h in halves[_LEADER_HALVES : _LEADER_HALVES + _PAUSE_HALVES]):
            return None

        def _read_bits(section: Sequence[int]) -> list[int] | None:
            bits: list[int] = []
            for i in range(len(section) // 2):
                first, second = section[2 * i], section[2 * i + 1]
                if first < 0 and second > 0:
                    bits.append(1)
                elif first > 0 and second < 0:
                    bits.append(0)
                else:
                    return None
            return bits

        leader = _read_bits(halves[:_LEADER_HALVES])
        trailing = _read_bits(halves[_LEADER_HALVES + _PAUSE_HALVES :])
        if leader is None or trailing is None:
            return None
        if leader[0] != 1:  # S1 is always 1
            return None

        start_bit_2 = leader[1]
        toggle = leader[2]
        address = 0
        for bit in leader[3:8]:
            address = (address << 1) | bit
        command = 0
        for bit in trailing[0:6]:
            command = (command << 1) | bit
        extension = 0
        for bit in trailing[6:12]:
            extension = (extension << 1) | bit
        if start_bit_2 == 0:  # field bit carries inverted command bit 6
            command |= 0x40
        return (address, command, extension, toggle)

    @staticmethod
    def _to_half_bits(frame: Sequence[int]) -> list[int] | None:
        """Expand merged wire timings into the 44-entry half-bit lattice."""
        halves: list[int] = [-1]  # implicit first half of S1
        for value in frame:
            magnitude = abs(value)
            units = max(1, round(magnitude / _HALF_BIT_US))
            if units > _MAX_RUN_UNITS:
                return None
            if abs(magnitude - units * _HALF_BIT_US) > _UNIT_TOLERANCE_US * units:
                return None
            sign = 1 if value > 0 else -1
            halves.extend([sign] * units)
            if len(halves) > _FRAME_HALVES:
                return None
        if len(halves) == _FRAME_HALVES - 1:
            halves.append(-1)  # implicit stripped trailing space
        if len(halves) != _FRAME_HALVES:
            return None
        return halves
