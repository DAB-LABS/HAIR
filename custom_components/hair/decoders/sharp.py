"""Sharp IR command with decode support.

Encode side mirrors ``infrared_protocols.commands.sharp.SharpCommand``
byte-for-byte (asserted by round-trip tests) and adds ``repeat_count``
support (Sharp has no repeat code; held buttons re-send the full
double-frame transmission). Decode side is new (upstream is encode-only
as of 7.5.0).

Sharp transmits every command twice -- a data frame and a bit-inverted
frame -- as its integrity check:

- No leader. Bit: 320us mark, then 680us space (0) or 1680us space (1).
  15 bits LSB first: 5 address bits, 8 command bits, 1 extension bit,
  1 check bit (0 in the data frame). Trailer: 320us mark + 40ms space.
- Second frame repeats the address bits and inverts command, extension,
  and check (XOR 0x7FE0).

The decoder requires the frame pair: a lone 15-bit frame's single check
bit is far too weak to accept, and real Sharp hardware always sends the
pair. Captures holding multiple pairs majority-vote as usual.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, split_frames
from ._base import Command

_BIT_MARK_US = 320
_ZERO_SPACE_US = 680
_ONE_SPACE_US = 1680
_TRAILER_SPACE_US = 40000
# Midpoint between the 0-space (680us) and 1-space (1680us).
_SPACE_MIDPOINT_US = 1180
_MARK_MIN_US = 120
_MARK_MAX_US = 700
_SPACE_MIN_US = 300
_SPACE_MAX_US = 2400
# Bit spaces top out at 1680us; the 40ms trailer separates frames.
_FRAME_GAP_US = 8000

_FRAME_BITS = 15
_INVERT_MASK = 0x7FE0


class SharpCommand(Command):
    """Sharp IR command with decode support."""

    address: int
    command: int
    extension: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        extension: int = 0,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Sharp IR command.

        :param address: The IR address for the Sharp command. (5 bits)
        :param command: The IR command for the Sharp command. (8 bits)
        :param extension: The extension bit for the Sharp command. (1 bit)
        """
        if not 0 <= address <= 0x1F:
            raise ValueError(f"address must be in range 0-31, got {address}")
        if not 0 <= command <= 0xFF:
            raise ValueError(f"command must be in range 0-255, got {command}")
        if extension not in (0, 1):
            raise ValueError(f"extension must be 0 or 1, got {extension}")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.extension = extension

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Sharp command (data + inverted frame)."""
        data = self.address | (self.command << 5) | (self.extension << 13)
        idata = data ^ _INVERT_MASK

        pair: list[int] = []

        def _encode_bits(value: int) -> None:
            for _ in range(_FRAME_BITS):
                bit = value & 1
                pair.append(_BIT_MARK_US)
                pair.append(-(_ONE_SPACE_US if bit else _ZERO_SPACE_US))
                value >>= 1
            pair.extend([_BIT_MARK_US, -_TRAILER_SPACE_US])

        _encode_bits(data)
        _encode_bits(idata)

        timings = list(pair)
        for _ in range(self.repeat_count):
            timings.extend(pair)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SharpCommand.

        Frames pair up as (data, inverted); the decoder validates each
        pair and majority-votes across pairs. Returns None when no valid
        pair exists in the capture.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        words = [cls._decode_frame(frame) for frame in frames]

        pairs: list[tuple[int, int, int]] = []
        i = 0
        while i + 1 < len(words):
            first, second = words[i], words[i + 1]
            if first is None or second is None:
                i += 1
                continue
            decoded = cls._validate_pair(first, second)
            if decoded is None:
                i += 1
                continue
            pairs.append(decoded)
            i += 2

        result = decode_frames_majority(pairs, lambda pair: pair)
        if result is None:
            return None
        (address, command, extension), votes = result
        return cls(
            address=address,
            command=command,
            extension=extension,
            repeat_count=votes - 1,
        )

    @staticmethod
    def _validate_pair(data: int, idata: int) -> tuple[int, int, int] | None:
        """Validate a (data, inverted) frame pair; extract the fields."""
        if data ^ idata != _INVERT_MASK:
            return None
        if (data >> 14) & 1 != 0:  # check bit: 0 in the data frame
            return None
        address = data & 0x1F
        command = (data >> 5) & 0xFF
        extension = (data >> 13) & 1
        return (address, command, extension)

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> int | None:
        """Decode one 15-bit Sharp frame to its raw data word."""
        # 15 bit pairs + trailer mark; the trailer space is the frame gap.
        if len(frame) < 2 * _FRAME_BITS + 1:
            return None

        data = 0
        for i in range(_FRAME_BITS):
            mark = frame[2 * i]
            space = -frame[2 * i + 1]
            if not _MARK_MIN_US <= mark <= _MARK_MAX_US:
                return None
            if not _SPACE_MIN_US <= space <= _SPACE_MAX_US:
                return None
            if space > _SPACE_MIDPOINT_US:
                data |= 1 << i

        if not _MARK_MIN_US <= frame[2 * _FRAME_BITS] <= _MARK_MAX_US:
            return None
        if any(value > 0 for value in frame[2 * _FRAME_BITS + 1 :]):
            return None
        return data
