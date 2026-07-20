"""Nokia32 (Philips RC-MM / NRC17 family) IR command with decode support.

Encode side mirrors ``infrared_protocols.commands.nokia32.Nokia32Command``
byte-for-byte (asserted by round-trip tests). Decode side follows the
upstream ``from_raw_timings`` conventions, wrapped in HAIR's frame-split +
majority-vote so a held button (Nokia32 re-sends the whole frame on a
~100ms period, it has no distinct repeat frame) collapses to one identity.

Nokia32 is a 32-bit, 36 kHz, MSB-first protocol used by RC-MM set-top
boxes -- Foxtel (AU), Sky/Digibox (Pace/Amstrad, UK/IE), Nokia
Mediamaster / d-box (EU):

- Leader: 412us mark, 276us space.
- Payload ``D:8 S:8 T:1 X:7 F:8`` sent MSB-first as sixteen 2-bit symbols.
  Every symbol is a 164us mark followed by one of four spaces encoding the
  symbol value 0..3: 276, 445, 614, 783us.
- Closing 164us mark, then the ~100ms inter-frame period.

``device``/``subdevice`` address the box, ``extension`` (X) is the 7-bit
system/OEM code that separates Foxtel from Sky from Mediamaster on the
same protocol, ``function`` is the button, ``toggle`` flips between
distinct presses (press state, not identity).

Protocol work and the Foxtel iQ capture set: @rohrsh (HAIR #52).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command

_LEADER_MARK_US = 412
_LEADER_SPACE_US = 276
_BIT_MARK_US = 164
# 2-bit symbol value (0..3) -> trailing space duration in microseconds.
_SYMBOL_SPACE_US = (276, 445, 614, 783)
# Nokia32's tolerance is tighter than the NEC default; the four symbol
# spaces are only ~170us apart, so keep the upstream 0.3 band.
_TOLERANCE = 0.3

_DATA_SYMBOLS = 16  # 32 payload bits, 2 bits per symbol
# leader pair (2) + 16 symbol pairs (32) + closing mark (1)
_MIN_FRAME_LEN = 2 + _DATA_SYMBOLS * 2 + 1
# Largest intra-frame space is 783us; the inter-frame period is ~100ms.
# Any space of 8ms+ is a frame boundary, never a symbol.
_FRAME_GAP_US = 8000


class Nokia32Command(Command):
    """Nokia32 IR command with decode support."""

    device: int
    subdevice: int
    toggle: int
    extension: int
    function: int

    def __init__(
        self,
        *,
        device: int,
        subdevice: int,
        function: int,
        extension: int = 0,
        toggle: int = 0,
        modulation: int = 36000,
    ) -> None:
        """Initialize the Nokia32 IR command.

        :param device: box device code D (8 bits)
        :param subdevice: box subdevice code S (8 bits)
        :param function: button code F (8 bits)
        :param extension: system/OEM code X (7 bits)
        :param toggle: press-state toggle T (1 bit)
        """
        super().__init__(modulation=modulation)
        self.device = device & 0xFF
        self.subdevice = subdevice & 0xFF
        self.toggle = toggle & 0x1
        self.extension = extension & 0x7F
        self.function = function & 0xFF

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Nokia32 command.

        Positive values are mark (high) durations in microseconds; negative
        values are space (low) durations. Byte-identical to the upstream
        encoder: a single frame, no repeat (Nokia32 has no repeat frame).
        """
        third = (self.toggle << 7) | self.extension
        value = (
            (self.device << 24)
            | (self.subdevice << 16)
            | (third << 8)
            | self.function
        )
        timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        for shift in range(2 * (_DATA_SYMBOLS - 1), -1, -2):  # MSB-first
            symbol = (value >> shift) & 0b11
            timings.append(_BIT_MARK_US)
            timings.append(-_SYMBOL_SPACE_US[symbol])
        timings.append(_BIT_MARK_US)  # closing mark
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a Nokia32Command, or None if no match.

        The capture is split into frames at the ~100ms inter-frame period;
        each frame decodes independently and the majority vote wins, so a
        single tap and a jittery multi-frame hold of one button yield the
        same identity. Toggle is recovered for transmit but does not split
        the vote (a held button keeps one toggle value).
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (device, subdevice, toggle, extension, function), _votes = result
        return cls(
            device=device,
            subdevice=subdevice,
            function=function,
            extension=extension,
            toggle=toggle,
        )

    @classmethod
    def _decode_frame(
        cls, frame: Sequence[int]
    ) -> tuple[int, int, int, int, int] | None:
        """Decode one Nokia32 frame to (device, subdevice, toggle, ext, fn).

        Mirrors the upstream per-symbol checks: leader, then sixteen
        164us-mark / classified-space symbols, then the closing mark. Any
        timing outside tolerance rejects the frame (this is what keeps a
        clean frame of another protocol from decoding as Nokia32).
        """
        if len(frame) < _MIN_FRAME_LEN:
            return None
        if not is_close(frame[0], _LEADER_MARK_US, _TOLERANCE):
            return None
        if not is_close(-frame[1], _LEADER_SPACE_US, _TOLERANCE):
            return None

        value = 0
        for i in range(_DATA_SYMBOLS):
            mark = frame[2 + 2 * i]
            space = -frame[3 + 2 * i]
            if not is_close(mark, _BIT_MARK_US, _TOLERANCE):
                return None
            symbol = cls._classify_symbol(space)
            if symbol is None:
                return None
            value = (value << 2) | symbol

        closing = frame[2 + 2 * _DATA_SYMBOLS]
        if not is_close(closing, _BIT_MARK_US, _TOLERANCE):
            return None
        # Only spaces may follow the closing mark (a truncated trailer or
        # the start of the inter-frame gap); a further mark is another frame
        # that split_frames should have separated -- reject to be safe.
        if any(value_after > 0 for value_after in frame[_MIN_FRAME_LEN:]):
            return None

        third = (value >> 8) & 0xFF
        return (
            (value >> 24) & 0xFF,  # device
            (value >> 16) & 0xFF,  # subdevice
            (third >> 7) & 0x1,    # toggle
            third & 0x7F,          # extension
            value & 0xFF,          # function
        )

    @staticmethod
    def _classify_symbol(space_us: int) -> int | None:
        """Classify a trailing space into a 2-bit symbol value, or None."""
        best = min(
            range(4), key=lambda i: abs(space_us - _SYMBOL_SPACE_US[i])
        )
        if is_close(space_us, _SYMBOL_SPACE_US[best], _TOLERANCE):
            return best
        return None
