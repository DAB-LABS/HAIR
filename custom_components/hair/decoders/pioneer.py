"""Pioneer: a 40 kHz NEC-shaped frame HAIR cannot tell from NEC on air.

NOT REGISTERED, ON PURPOSE. This module encodes and reads the frame, and
``protocol_decode`` never probes it. No capture ever mints a ``PIONEER``
identity.

THE RULING, WITH THE NUMBERS. HAIR decodes from raw timings, and a
demodulating receiver hands it no carrier at all, so the one thing that
genuinely separates Pioneer from NEC -- 40 kHz against 38 kHz -- is gone
before any decoder sees the capture. Everything that survives is inside
NEC's tolerance. Against NEC's nominals at the 40 percent band the
package uses::

    axis          NEC nominal   NEC window     Pioneer 548  Pioneer 532
    leader mark        9000     5400..12600       8470          8510
    leader space       4500     2700..6300        4230          4256
    bit mark            562      337..787          548           532
    zero space          562      337..787          500           532
    one space          1687     1012..2362        1570          1596

Two Pioneer timing sets are in circulation, named above by their bit
mark. Every value of both is inside every NEC window. Separating them
would need a tolerance under 2.55 percent for the 548 set (its 548 us
bit mark against NEC's 562) or 5.64 percent for the 532 set (532
against 562). Both are an order of magnitude tighter than any real
receiver delivers, and the looser of the two is still a fifth of what
this package's tightest decoder uses.

A discriminator does exist and HAIR throws it away before a decoder
could use it: the frame period. A Pioneer repetition runs about 89 ms
against NEC's fixed 107.87 ms, seventeen percent apart and well outside
jitter. ``split_frames`` drops the gap spaces, so no decoder in this
package ever sees an inter-frame period. Reaching for it would be a
different change to a different layer, and it is recorded here so the
ruling is not mistaken for "nothing could ever tell them apart".

Registering ahead of ``nec`` would therefore re-label every Pioneer
frame that decodes as NEC today, which the pack's must-not-change list
forbids; registering after ``nec`` would claim almost nothing. HAIR
cannot honestly tell the two apart on air and does not pretend to.

THREE OUTCOMES, NOT TWO. A Pioneer frame can reach HAIR three ways and
the pin test asserts all three: an air capture decodes as ``NEC`` when
its payload bytes complement and stays raw when they do not, and a
Flipper ``Pioneer`` line builds through this class and is stored as
40 kHz Pronto whose re-decode lands on ``NEC``. ``PIONEER`` never
appears as a decoded label anywhere.

The constants below are the 532 set's, the tighter of the two. Some
Pioneer remotes send two different 32-bit codes per press; HAIR's
identity triple cannot carry a pair, so those are receipted as
unsupported at the import door and a wig can still hold them as raw
Pronto.

License rule (package docstring): written from the public frame
description and the timing numbers above. No third-party implementation
consulted.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames, stamp_census
from ._base import Command

_LEADER_MARK_US = 8510
_LEADER_SPACE_US = 4256
_BIT_MARK_US = 532
_ZERO_SPACE_US = 532
_ONE_SPACE_US = 1596
_TRAILING_SPACE_US = 35_500

#: 40 kHz, the one fact about this protocol HAIR can carry but not
#: hear. It survives into the stored Pronto through ``raw_to_pronto``.
_MODULATION_HZ = 40000

_TOLERANCE = 0.4
_MIN_MARK_US = 200
_DATA_BITS = 32
_FRAME_GAP_US = 8000


class PioneerCommand(Command):
    """Pioneer 32-bit IR command: a real encoder, never registered."""

    #: Declared for symmetry with the registered decoders. The coverage
    #: accounting never reads it, because nothing registers this class.
    FRAME_GAP_US = _FRAME_GAP_US

    address: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Pioneer command.

        :param address: 16-bit little-endian address, bytes 1 and 2
        :param command: 16-bit little-endian payload, bytes 3 and 4
        """
        if not 0 <= address <= 0xFFFF:
            raise ValueError("Pioneer address must be in range 0x0000..0xFFFF")
        if not 0 <= command <= 0xFFFF:
            raise ValueError("Pioneer command must be in range 0x0000..0xFFFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @property
    def wire_bytes(self) -> tuple[int, int, int, int]:
        """The four bytes in transmission order."""
        return (
            self.address & 0xFF,
            (self.address >> 8) & 0xFF,
            self.command & 0xFF,
            (self.command >> 8) & 0xFF,
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings: leader, 32 LSB-first bits, trailer mark.

        Repeats re-send the whole frame, which is what both single-frame
        definitions do: neither carries a repeat group, so there is no
        marker form to emit.
        """
        frame: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        for byte in self.wire_bytes:
            for bit_index in range(8):
                frame.append(_BIT_MARK_US)
                frame.append(
                    -_ONE_SPACE_US
                    if (byte >> bit_index) & 1
                    else -_ZERO_SPACE_US
                )
        frame.append(_BIT_MARK_US)

        timings = list(frame)
        for _ in range(self.repeat_count):
            timings.append(-_TRAILING_SPACE_US)
            timings.extend(frame)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Read a Pioneer-shaped frame, or None.

        Exercised by this module's own tests and by file readers. Never
        called by ``protocol_decode``: an air capture of this frame is
        indistinguishable from NEC, so it decodes as ``NEC`` or stays
        raw. See the module docstring.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (address, command), votes = result
        return stamp_census(
            cls(address=address, command=command, repeat_count=votes - 1),
            votes,
        )

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> tuple[int, int] | None:
        """One frame to ``(address, command)``, or None."""
        needed = 2 + 2 * _DATA_BITS + 1
        if len(frame) < needed:
            return None
        if not is_close(frame[0], _LEADER_MARK_US, _TOLERANCE):
            return None
        if not is_close(-frame[1], _LEADER_SPACE_US, _TOLERANCE):
            return None

        data = [0, 0, 0, 0]
        index = 2
        for bit_index in range(_DATA_BITS):
            mark = frame[index]
            space = -frame[index + 1]
            if not is_close(mark, _BIT_MARK_US, _TOLERANCE):
                return None
            if is_close(space, _ONE_SPACE_US, _TOLERANCE):
                data[bit_index // 8] |= 1 << (bit_index % 8)
            elif not is_close(space, _ZERO_SPACE_US, _TOLERANCE):
                return None
            index += 2

        if index >= len(frame) or frame[index] < _MIN_MARK_US:
            return None
        return (data[0] | (data[1] << 8), data[2] | (data[3] << 8))
