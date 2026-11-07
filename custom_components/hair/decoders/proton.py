"""Proton IR command with decode support, and the unit that tells it from GE-AC.

Proton is the format of NEC Display projectors and televisions, Proton
and Audiovox equipment, and some set-top boxes (the Futarque remote in
this repo's LIRC fixtures). The public IRP is::

    {38k,500}<1,-1|1,-3>(16,-8,D:8,1,-8,F:8,1,^63m)+

So a frame is an 8000us mark and a 4000us space, then D (8 bits), a
500us stop mark and a 4000us gap, then F (8 bits), then a 500us stop
mark, all on a 500us unit, with bits LSB first: a 500us mark and a 500us
(0) or 1500us (1) space. There is no checksum. A held button repeats the
whole frame on a 63ms period.

THE UNIT IS WHAT MAKES IT PROTON. GE-AC (the library's ``GEACCommand``,
from 6.1.0) is the same layout on a 562.5us unit: its 9000/4500 leader
is 16 and 8 units, its 562/1687 bits are 1 and 3, and its 562/4500 gap
is 1 and 8. The two units are 12.5% apart, and both decoders allow 40%
per timing, so on timings alone each reads the other's frames: the
library's Proton decoder takes GE-AC frames, and its GE-AC decoder takes
Proton's. What separates them is the frame's unit, estimated from the
whole frame rather than from one timing:

    unit = (sum of the frame's 37 timings) / (66 + 2 * ones)

The layout is 16 + 8 (leader), 2 per 0 bit, 4 per 1 bit, 1 + 8 (gap)
and 1 (stop): 66 units plus 2 for every 1 bit. A receiver's systematic
distortion (marks short, spaces long) mostly cancels in the sum, which
is why the whole frame measures the unit better than any one timing.

THE WINDOWS. ``PROTON_UNIT_MAX_US`` is 525 (500 + 5%) and
``GEAC_UNIT_MIN_US`` is 535 (562.5 - 4.9%); a frame whose unit falls
between them is read by neither. Measured over 5,000 random codes of
each (scratch work, in the 1.2.0 report): under a TSOP-like receiver
(marks +0..150us, spaces -0..150us) Proton spans 488..512 and GE-AC
552..575; under the AGC signature measured on the air path (marks
x0.83..0.95, spaces x1.00..1.12) Proton spans 478..511 and GE-AC
537..572; quantized to a Broadlink's 32.8us tick, 494..497 and 555..558.
The Futarque remote's own timings give 498.

SENDING. ``repeat_count`` whole frames follow the first on the 63ms
period. With ``repeat_count`` 0 the encoder is byte-identical to the
library's ``ProtonCommand`` (9.1.0 and later), including its 38.5kHz
carrier, as the package rule asks.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames, stamp_census
from ._base import Command

_UNIT_US = 500
_LEADER_MARK_US = 16 * _UNIT_US
_LEADER_SPACE_US = 8 * _UNIT_US
_BIT_MARK_US = _UNIT_US
_ZERO_SPACE_US = _UNIT_US
_ONE_SPACE_US = 3 * _UNIT_US
_GAP_SPACE_US = 8 * _UNIT_US
_FRAME_PERIOD_US = 63000
# The library's ProtonCommand carrier; the IRP says 38k.
_MODULATION_HZ = 38500

#: Leader (2), eight D pairs (16), stop and gap (2), eight F pairs (16),
#: stop (1).
FRAME_TIMINGS = 37
#: The frame's length in units with no 1 bits; each 1 bit adds two.
_BASE_UNITS = 66

#: The largest frame unit that is still Proton (500us + 5%).
PROTON_UNIT_MAX_US = 525.0
#: The smallest frame unit that is GE-AC (562.5us - 4.9%).
GEAC_UNIT_MIN_US = 535.0

# Inside a frame no space exceeds the 4000us leader space or gap; the
# frame period is 63ms. Any space of 10ms or more is a frame boundary.
_FRAME_GAP_US = 10000


def frame_unit_us(frame: Sequence[int], ones: int) -> float:
    """The unit a Proton-layout frame is drawn on, from its whole length.

    ``frame`` is the 37 timings of one frame and ``ones`` the number of
    1 bits it carries. Shared with the GE-AC check in ``protocol_decode``
    because the two protocols are this one layout on different units.
    """
    total = sum(abs(int(v)) for v in frame[:FRAME_TIMINGS])
    return total / (_BASE_UNITS + 2 * ones)


def _frame(address: int, command: int) -> list[int]:
    def bits(value: int) -> list[int]:
        out: list[int] = []
        for i in range(8):
            bit = (value >> i) & 1
            out += [_BIT_MARK_US, -(_ONE_SPACE_US if bit else _ZERO_SPACE_US)]
        return out

    return [
        _LEADER_MARK_US, -_LEADER_SPACE_US,
        *bits(address),
        _BIT_MARK_US, -_GAP_SPACE_US,
        *bits(command),
        _BIT_MARK_US,
    ]


class ProtonCommand(Command):
    """Proton IR command (8-bit device, 8-bit function) with decode support."""

    #: The frame gap this protocol splits captures at, for the coverage
    #: accounting in ``protocol_decode``.
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
        """Initialize the Proton IR command.

        :param address: the device code D (8 bits)
        :param command: the function code F (8 bits)
        :param repeat_count: whole frames sent after the first
        """
        if not 0 <= address <= 0xFF:
            raise ValueError(f"address must be 0-255, got {address}")
        if not 0 <= command <= 0xFF:
            raise ValueError(f"command must be 0-255, got {command}")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings: one frame, then ``repeat_count`` more."""
        frame = _frame(self.address, self.command)
        timings = list(frame)
        padding = _FRAME_PERIOD_US - sum(abs(v) for v in frame)
        for _ in range(self.repeat_count):
            timings.append(-padding)
            timings.extend(frame)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a ProtonCommand, or None.

        Each frame between gaps of 10ms or more is decoded on its own and
        the majority wins; ``repeat_count`` is the number of extra
        agreeing frames.
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
        """Decode one frame to ``(address, command)``, or None.

        Every timing must be within the family tolerance of its Proton
        nominal, and then the frame's unit must be Proton's, not GE-AC's.
        """
        if len(frame) != FRAME_TIMINGS:
            return None
        if not (
            is_close(frame[0], _LEADER_MARK_US)
            and is_close(-frame[1], _LEADER_SPACE_US)
            and is_close(frame[18], _BIT_MARK_US)
            and is_close(-frame[19], _GAP_SPACE_US)
            and is_close(frame[36], _BIT_MARK_US)
        ):
            return None
        values = []
        ones = 0
        for start in (2, 20):
            value = 0
            for i in range(8):
                mark, space = frame[start + 2 * i], -frame[start + 2 * i + 1]
                if not is_close(mark, _BIT_MARK_US):
                    return None
                if is_close(space, _ZERO_SPACE_US):
                    bit = 0
                elif is_close(space, _ONE_SPACE_US):
                    bit = 1
                else:
                    return None
                value |= bit << i
                ones += bit
            values.append(value)
        if frame_unit_us(frame, ones) > PROTON_UNIT_MAX_US:
            return None
        return (values[0], values[1])
