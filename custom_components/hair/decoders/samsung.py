"""Samsung32 IR command with decode support.

Encode side mirrors ``infrared_protocols.commands.samsung.Samsung32Command``
byte-for-byte (asserted by round-trip tests). Decode side is new
(upstream is encode-only as of 7.5.0).

Samsung32 is NEC-shaped with a different leader (4500/4500 instead of
9000/4500) and full-frame repeats instead of dedicated repeat codes:

- Leader: 4500us mark, 4500us space. Bit: 560us mark, then 560us space
  (0) or 1690us space (1). End pulse: 560us mark. 32 data bits LSB
  first: address low, address high, command, inverted command. Standard
  addresses send the same byte twice; extended addresses split 16 bits.
- Held buttons re-send the whole frame, padded to a 108ms period.

The inverted-command checksum makes single frames trustworthy; repeats
still majority-vote so a capture holding three re-sends decodes to one
identity with the repeat count preserved.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command

_LEADER_MARK_US = 4500
_LEADER_SPACE_US = 4500
_BIT_MARK_US = 560
_ZERO_SPACE_US = 560
_ONE_SPACE_US = 1690
# Midpoint between the 0-space (560us) and 1-space (1690us).
_SPACE_MIDPOINT_US = 1125
_MARK_MIN_US = 220
_MARK_MAX_US = 1000
_SPACE_MIN_US = 220
_SPACE_MAX_US = 2400
_FRAME_PERIOD_US = 108000
# Bit spaces top out at 1690us; the pad to 108ms separates frames.
_FRAME_GAP_US = 8000


class Samsung32Command(Command):
    """Samsung32 IR command with decode support."""

    address: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Samsung32 IR command."""
        if not 0 <= address <= 0xFFFF:
            raise ValueError("Samsung32 address must be in range 0x00..0xFFFF")
        if not 0 <= command <= 0xFF:
            raise ValueError("Samsung32 command must be in range 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung32 command."""
        timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]

        if self.address <= 0xFF:
            address_low = self.address & 0xFF
            address_high = self.address & 0xFF
        else:
            address_low = self.address & 0xFF
            address_high = (self.address >> 8) & 0xFF

        command_byte = self.command & 0xFF
        command_inverted = (~self.command) & 0xFF

        data = (
            address_low
            | (address_high << 8)
            | (command_byte << 16)
            | (command_inverted << 24)
        )

        for _ in range(32):
            bit = data & 1
            timings.append(_BIT_MARK_US)
            timings.append(-_ONE_SPACE_US if bit else -_ZERO_SPACE_US)
            data >>= 1

        timings.append(_BIT_MARK_US)

        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in timings)
            gap = _FRAME_PERIOD_US - frame_duration
            base_frame = timings.copy()
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(base_frame)

        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a Samsung32Command.

        Returns the majority identity across the capture's frames with
        ``repeat_count`` preserved, or None when nothing decodes.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (address, command), votes = result
        return cls(address=address, command=command, repeat_count=votes - 1)

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> tuple[int, int] | None:
        """Decode one Samsung32 frame to ``(address, command)``."""
        # Leader pair + 32 bit pairs + end pulse.
        if len(frame) < 2 + 64 + 1:
            return None
        if not is_close(frame[0], _LEADER_MARK_US) or not is_close(
            -frame[1], _LEADER_SPACE_US
        ):
            return None

        data = 0
        for i in range(32):
            mark = frame[2 + 2 * i]
            space = -frame[3 + 2 * i]
            if not _MARK_MIN_US <= mark <= _MARK_MAX_US:
                return None
            if not _SPACE_MIN_US <= space <= _SPACE_MAX_US:
                return None
            if space > _SPACE_MIDPOINT_US:
                data |= 1 << i

        # End pulse. Nominally 560us, but real emitters that replay the
        # packet for repeats can butt the replay directly against it
        # with no junction gap, fusing the end mark with whatever comes
        # next into one long mark (v0.6.1 bench: Broadlink TX honors
        # the command's repeat_count on top of the timings' baked
        # repeat frames; observed fusions of ~4900us and ~7000us). So
        # the end pulse has NO upper bound: once fusion is possible its
        # length carries no information, and the 32 data pairs plus the
        # inverted-command checksum already gate the decode.
        if frame[66] < _MARK_MIN_US:
            return None
        if any(value > 0 for value in frame[67:]):
            return None

        address_low = data & 0xFF
        address_high = (data >> 8) & 0xFF
        command_byte = (data >> 16) & 0xFF
        command_inverted = (data >> 24) & 0xFF
        if command_byte ^ command_inverted != 0xFF:
            return None

        # Standard Samsung32 duplicates the address byte; collapse it so
        # the decoded address round-trips through the encoder unchanged.
        address = (
            address_low
            if address_high == address_low
            else address_low | (address_high << 8)
        )
        return (address, command_byte)
