"""JVC IR command with decode support.

JVC is the 16-bit pulse-distance format of JVC's own televisions, video
recorders and audio equipment. The public IRP is::

    {38k,525}<1,-1|1,-3>(16,-8,(D:8,F:8,1,-45)+)

So a press opens with an 8400us mark and a 4200us space, then sends D
(8 bits) and F (8 bits), least significant bit first, each bit a 525us
mark followed by a 525us space (0) or a 1575us space (1), then a 525us
stop mark and a 23.6ms leadout. While the button is held the frame
repeats WITHOUT the leader: the leader marks the first frame of a
press, so a headerless frame is JVC's repeat, its ditto. There is no
checksum. Raw timings carry no carrier, so the decoder reads a frame at
any carrier; the encoder sends at 38kHz.

THE LEADER IS REQUIRED. A capture decodes only when at least one of its
frames carries the leader. Headerless frames that agree with it count
as its repeats; a capture of headerless frames alone, a learned copy
missing its first frame, decodes to nothing and keeps the identity it
has without a decoder. Without a leader, sixteen pulse-distance bits
with no check are too easy to find by accident (Mitsubishi's 16-bit
frame is the documented near neighbour).

THE WINDOWS. The leader mark is 6300..10500us and its space
3150..5250us. Every bit mark and the stop mark are 250..850us. A 0 space
is 250..850us, a 1 space 1150..2200us, and a space in the 850..1150us
dead zone fails the frame. A frame is exactly sixteen bits and the stop
mark, with or without the leader in front; anything longer or shorter
fails. Captures are split into frames at spaces of 10ms or more.

THE NEC1 FRAME IS THE SAME SHAPE. Its timings are JVC's scaled by about
1.07 (9000/4500, 560/560/1690), well inside these windows, and no
tolerance that survives receiver jitter tells the two leaders apart.
What separates them is the bit count: an NEC1 frame carries 32 bits and
is refused here. Two shapes do read as JVC: a 16-bit frame sent on NEC
timing, which is JVC-shaped, and an NEC1 capture that ends exactly
after its sixteenth bit.

THE CUT FINAL FRAME. A held press heard through a fixed learn window
often ends partway through a repeat. The value comes from whole frames
only, and a cut frame never votes. But the final frame of a capture,
and only that one, counts as explained when it is shorter than a whole
frame, every bit it reads agrees with the winning frame across at
least the full D byte, and its last timing, where the window closed, is
no longer than a 1 space. That timing is bounded but not read.

SENDING. ``repeat_count`` is the number of headerless frames sent after
the leader frame, the ditto count. ``send_count`` sends that whole
block again, so every send opens with a leader and reads as a new press.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import majority, split_frames, stamp_census
from ._base import Command

_UNIT_US = 525
_LEADER_MARK_US = 16 * _UNIT_US
_LEADER_SPACE_US = 8 * _UNIT_US
_BIT_MARK_US = _UNIT_US
_ZERO_SPACE_US = _UNIT_US
_ONE_SPACE_US = 3 * _UNIT_US
_LEADOUT_US = 45 * _UNIT_US
_MODULATION_HZ = 38000

# Decode windows (see the module docstring), inclusive.
_LEADER_MARK_MIN_US = 6300
_LEADER_MARK_MAX_US = 10500
_LEADER_SPACE_MIN_US = 3150
_LEADER_SPACE_MAX_US = 5250
_MARK_MIN_US = 250
_MARK_MAX_US = 850
_ZERO_MIN_US = 250
_ZERO_MAX_US = 850
_ONE_MIN_US = 1150
_ONE_MAX_US = 2200

# Inside a frame no space exceeds the 4200us leader space; the leadout
# is 23.6ms.
_FRAME_GAP_US = 10000

_DATA_BITS = 16
_BODY_TIMINGS = 2 * _DATA_BITS + 1  # sixteen bits and the stop mark
# A cut final frame must read at least this many bits (the D byte).
_MIN_CUT_BITS = 8


def _bit_frame(address: int, command: int) -> list[int]:
    """One frame's bits and stop mark, without the leader."""
    value = address | (command << 8)
    timings: list[int] = []
    for i in range(_DATA_BITS):
        timings.append(_BIT_MARK_US)
        timings.append(-(_ONE_SPACE_US if (value >> i) & 1 else _ZERO_SPACE_US))
    timings.append(_BIT_MARK_US)
    return timings


def _is_mark(value: int) -> bool:
    return value > 0 and _MARK_MIN_US <= value <= _MARK_MAX_US


def _space_bit(value: int) -> int | None:
    """0 or 1 for a bit space, or None outside both windows."""
    if value >= 0:
        return None
    magnitude = -value
    if _ZERO_MIN_US <= magnitude <= _ZERO_MAX_US:
        return 0
    if _ONE_MIN_US <= magnitude <= _ONE_MAX_US:
        return 1
    return None


def _read_bits(body: Sequence[int]) -> list[int] | None:
    """Read (mark, space) pairs as bits, or None on any timing off-window."""
    bits: list[int] = []
    for index in range(0, len(body) - 1, 2):
        if not _is_mark(body[index]):
            return None
        bit = _space_bit(body[index + 1])
        if bit is None:
            return None
        bits.append(bit)
    return bits


def _has_leader(frame: Sequence[int]) -> bool:
    return (
        len(frame) >= 2
        and _LEADER_MARK_MIN_US <= frame[0] <= _LEADER_MARK_MAX_US
        and _LEADER_SPACE_MIN_US <= -frame[1] <= _LEADER_SPACE_MAX_US
    )


class JVCCommand(Command):
    """JVC 16-bit IR command with decode support."""

    #: The frame gap this protocol splits captures at, exposed so the
    #: coverage accounting in ``protocol_decode`` counts frames the way
    #: this decoder does.
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
        """Initialize the JVC IR command.

        :param address: the device code D (8 bits)
        :param command: the function code F (8 bits)
        :param repeat_count: headerless repeat frames sent after the first
        """
        if not 0 <= address <= 0xFF:
            raise ValueError("JVC address must be in range 0x00..0xFF")
        if not 0 <= command <= 0xFF:
            raise ValueError("JVC command must be in range 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings: the leader frame, then the headerless repeats."""
        frame = _bit_frame(self.address, self.command)
        timings = [_LEADER_MARK_US, -_LEADER_SPACE_US, *frame]
        for _ in range(self.repeat_count):
            timings.append(-_LEADOUT_US)
            timings.extend(frame)
        # The final leadout is idle, not signal, so it is not emitted.
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a JVCCommand.

        Returns the majority value across the whole frames of the
        capture, with ``repeat_count`` set to the number of extra
        agreeing frames, or None when no frame with a leader decodes.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        decoded = [cls._decode_frame(frame) for frame in frames]
        led = [value for value, leader in filter(None, decoded) if leader]
        if not led:
            return None
        top = majority([value for value, _ in filter(None, decoded)])
        if top is None:
            return None
        (address, command), votes = top
        explained = votes
        if (
            len(frames) > 1
            and decoded[-1] is None
            and cls._is_cut_copy(frames[-1], _bit_frame(address, command))
        ):
            explained += 1
        return stamp_census(
            cls(address=address, command=command, repeat_count=votes - 1),
            explained,
        )

    @classmethod
    def _decode_frame(
        cls, frame: Sequence[int]
    ) -> tuple[tuple[int, int], bool] | None:
        """``((address, command), has_leader)`` for one whole frame."""
        leader = _has_leader(frame)
        body = frame[2:] if leader else frame
        if len(body) != _BODY_TIMINGS or not _is_mark(body[-1]):
            return None
        bits = _read_bits(body[:-1])
        if bits is None:
            return None
        value = 0
        for index, bit in enumerate(bits):
            value |= bit << index
        return ((value & 0xFF, value >> 8), leader)

    @staticmethod
    def _is_cut_copy(frame: Sequence[int], winner: Sequence[int]) -> bool:
        """Is this final, headerless frame the winning frame, cut short?

        Its last timing is where the capture stopped: bounded, not read.
        Every timing before it must read, the frame must be shorter than
        a whole one, and every bit it reads must match the winner's.
        """
        if len(frame) < 2 or len(frame) >= _BODY_TIMINGS:
            return False
        if abs(frame[-1]) > _ONE_MAX_US:
            return False
        read = frame[:-1]
        read = read[: len(read) - len(read) % 2]
        bits = _read_bits(read)
        if bits is None or len(bits) < _MIN_CUT_BITS:
            return False
        winner_bits = [
            0 if -winner[i + 1] == _ZERO_SPACE_US else 1
            for i in range(0, 2 * len(bits), 2)
        ]
        return bits == winner_bits
