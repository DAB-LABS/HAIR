"""Kaseikyo format IR command with decode support.

Encode side mirrors ``infrared_protocols.commands.kaseikyo.KaseikyoCommand``
byte-for-byte (asserted by round-trip tests). Decode side is new
(upstream is encode-only as of 7.5.0).

Kaseikyo is the 16-bit-vendor family (Panasonic, Denon, JVC-48, Sharp-48
and friends). Timing in base units T = 1e6 * 16 / 38000 ~= 421us:

- Leader: 8T mark, 4T space. Bit: 1T mark, then 1T space (0) or 3T
  space (1). End pulse: 1T mark. Repeat code: 8T mark, 8T space, 1T end
  pulse, NEC-style.
- Payload LSB first per byte: vendor address (16 bits), then a byte
  whose low nibble is the vendor parity (address_lo ^ address_hi,
  nibble-folded) and whose high nibble is data, then the remaining data
  bytes. Standard frames are 48 bits (6 bytes) total; the decoder
  accepts any whole-byte payload of 4+ bytes and validates the parity
  nibble, which is the family's integrity check.

The decoded ``data`` reconstructs the constructor's argument: byte 0
carries the genuine high nibble with a zero low nibble (the wire's low
nibble is the parity, which the encoder re-derives), followed by the
remaining payload bytes verbatim -- so encode(decode(x)) reproduces x.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command

# Base unit at the family-standard 16-pulse burst / 38kHz carrier.
_UNIT_US = round(1_000_000 * 16 / 38000)  # 421
_LEADER_MARK_US = 8 * _UNIT_US
_LEADER_SPACE_US = 4 * _UNIT_US
_REPEAT_SPACE_US = 8 * _UNIT_US
# Midpoint between the 0-space (1T) and 1-space (3T).
_SPACE_MIDPOINT_US = 2 * _UNIT_US
_MARK_MIN_US = 150
_MARK_MAX_US = 800
_SPACE_MIN_US = 150
_SPACE_MAX_US = 2200
# Bit spaces top out at 3T (~1263us); leader space is ~1684us. The
# inter-frame trailer is at least 8ms per the family convention.
_FRAME_GAP_US = 6000

_FRAME_TIME_US = 130000
_TRAILER_MIN_US = 8000
_MIN_PAYLOAD_BYTES = 4
_MAX_PAYLOAD_BYTES = 12


class KaseikyoCommand(Command):
    """Kaseikyo format IR command with decode support."""

    address: int
    data: bytes
    error_correction: Callable[[bytes], bytes] | None
    base_unit: float

    def __init__(
        self,
        *,
        address: int,
        data: bytes,
        error_correction: Callable[[bytes], bytes] | None = None,
        modulation: int = 38000,
        burst_pulse: int = 16,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Kaseikyo IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.data = data
        self.error_correction = error_correction
        self.base_unit = 1000000 * burst_pulse / modulation

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Kaseikyo command."""
        leader_high = round(8 * self.base_unit)
        leader_low = round(4 * self.base_unit)
        repeat_low = round(8 * self.base_unit)
        bit_high = round(1 * self.base_unit)
        zero_low = round(1 * self.base_unit)
        one_low = round(3 * self.base_unit)
        repeat_frame_gap = max(
            _FRAME_TIME_US - (leader_high + repeat_low + bit_high), _TRAILER_MIN_US
        )

        timings = [leader_high, -leader_low]

        parity = self.address & 0xFFFF
        parity ^= parity >> 8
        parity ^= parity >> 4
        parity &= 0x0F

        data_bytes = [
            self.address & 0xFF,
            (self.address >> 8) & 0xFF,
            (self.data[0] & 0xF0) | parity,
            *self.data[1:],
        ]
        if self.error_correction:
            data_bytes.extend(self.error_correction(bytes(data_bytes)))

        for byte in data_bytes:
            for _ in range(8):
                bit = byte & 1
                timings.append(bit_high)
                timings.append(-one_low if bit else -zero_low)
                byte >>= 1

        timings.append(bit_high)

        gap = max(_FRAME_TIME_US - sum(abs(t) for t in timings), _TRAILER_MIN_US)
        for _ in range(self.repeat_count):
            timings.extend([-gap, leader_high, -repeat_low, bit_high])
            gap = repeat_frame_gap

        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a KaseikyoCommand.

        Majority-votes across full frames; NEC-style repeat markers after
        the winning frame add to ``repeat_count``. Returns None when no
        frame decodes with a valid vendor parity nibble.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        repeat_markers = sum(1 for frame in frames if cls._is_repeat_marker(frame))
        data_frames = [f for f in frames if not cls._is_repeat_marker(f)]
        result = decode_frames_majority(data_frames, cls._decode_frame)
        if result is None:
            return None
        (address, payload), votes = result
        return cls(
            address=address,
            data=bytes(payload),
            repeat_count=votes - 1 + repeat_markers,
        )

    @staticmethod
    def _is_repeat_marker(frame: Sequence[int]) -> bool:
        """Return True for the 8T/8T/1T NEC-style repeat frame."""
        if len(frame) != 3:
            return False
        return (
            is_close(frame[0], _LEADER_MARK_US)
            and is_close(-frame[1], _REPEAT_SPACE_US)
            and _MARK_MIN_US <= frame[2] <= _MARK_MAX_US
        )

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> tuple[int, tuple[int, ...]] | None:
        """Decode one Kaseikyo frame to ``(address, payload_bytes)``."""
        # Leader pair + at least 4 byte-pairs + end pulse.
        if len(frame) < 2 + 2 * 8 * _MIN_PAYLOAD_BYTES + 1:
            return None
        if not is_close(frame[0], _LEADER_MARK_US) or not is_close(
            -frame[1], _LEADER_SPACE_US
        ):
            return None

        # The frame's LAST mark is the end pulse; everything between the
        # leader and it is bit pairs. Anchoring on the last mark (rather
        # than greedily consuming pairs) keeps a trailing sub-gap space
        # after the end pulse from being misread as a final bit's space.
        end_index = None
        for j in range(len(frame) - 1, 1, -1):
            if frame[j] > 0:
                end_index = j
                break
        if end_index is None or (end_index - 2) % 2 != 0:
            return None
        if not _MARK_MIN_US <= frame[end_index] <= _MARK_MAX_US:
            return None

        bits: list[int] = []
        for i in range(2, end_index, 2):
            mark = frame[i]
            space = -frame[i + 1]
            if not _MARK_MIN_US <= mark <= _MARK_MAX_US:
                return None
            if not _SPACE_MIN_US <= space <= _SPACE_MAX_US:
                return None
            bits.append(1 if space > _SPACE_MIDPOINT_US else 0)
            if len(bits) > 8 * _MAX_PAYLOAD_BYTES:
                return None

        if len(bits) % 8 != 0 or len(bits) < 8 * _MIN_PAYLOAD_BYTES:
            return None

        wire_bytes: list[int] = []
        for byte_index in range(len(bits) // 8):
            byte = 0
            for bit_index in range(8):
                byte |= bits[byte_index * 8 + bit_index] << bit_index
            wire_bytes.append(byte)

        address = wire_bytes[0] | (wire_bytes[1] << 8)
        parity = address ^ (address >> 8)
        parity ^= parity >> 4
        parity &= 0x0F
        if wire_bytes[2] & 0x0F != parity:
            return None

        payload = (wire_bytes[2] & 0xF0, *wire_bytes[3:])
        return (address, payload)
