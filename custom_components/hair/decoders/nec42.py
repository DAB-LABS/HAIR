"""NEC42: the 42-bit NEC1 frame, in its two readings.

One wire format, two readings of it. The frame is an ordinary NEC1
frame -- 9 ms leader, 4.5 ms leader space, LSB-first data bits at
562/562 and 562/1687, one trailer mark -- carrying **forty-two** data
bits instead of thirty-two. Remotes in the Aiwa and Samsung families
send this shape, and the two readings below are the two splits in
circulation for it.

``NEC42Command`` reads wire bits 0-12 as the address, 13-25 as its
complement, 26-33 as the command and 34-41 as its complement, and
claims a frame only when both complements hold. That is a real
checksum: twenty-one of the forty-two bits are redundant, so a frame
reaching this class by accident is a 1-in-2^21 event on top of the
frame-shape gate.

``NEC42ExtCommand`` reads the same forty-two bits as a 26-bit address
and a 16-bit command and checks nothing. It exists because a file can
state those fields verbatim and because a real 42-bit frame whose
complements do not hold still has to land somewhere. Its only gate is
structural, and that gate is the whole of its honesty: exactly
forty-two bits, then a trailer, then nothing but idle time and NEC
repeat markers. A longer payload -- an air conditioner state blob, the
false-positive class GH #134 was opened for -- offers a perfectly good
first forty-two bits and is refused because the frame keeps going.

A DISAGREEMENT ABOUT FIELD ORDER, SETTLED BY COUNTING. The ``Aiwa``
name belongs elsewhere to a field order of
``D:8, S:5, F:8, ~D:8, ~S:5, ~F:8``, which puts the command between the
address and its complement. Forty-two bits on their own cannot choose
between that and the 13/13/8/8 split above, but a body of frames can,
because the 8/5/8/8/5/8 order fails the 13/13/8/8 complement test on
EVERY frame: under that order, wire bits 13-25 are ``F:8`` plus five
bits of ``~D``, which is not the complement of bits 0-12. Measured over
8,660 readable frames of this shape, **8,653** satisfy both 13-bit
complements and 7 are genuine non-complement 42-bit codes. That is not
consistent with the 8/5/8/8/5/8 order and is what the 13/13/8/8 split
predicts. The acceptance test reports the observed division and the
reassembled forty-two-bit value, which holds under either reading.

THE ORDER AGAINST STRICT NEC IS DELIBERATE AND IMPERFECT. These classes
probe AFTER ``nec``, so the roughly one in a hundred 42-bit frames
whose bits 16-31 happen to satisfy NEC's command complement keep
decoding as 32-bit NEC, as they do today. Upstream's decoder reads
thirty-two bits at fixed offsets and checks the mark at index 66, which
in a 42-bit frame is the mark of bit 32 and passes, so it never notices
the frame continues. Probing ahead of ``nec`` would fix that and would
move every such stored identity, which the pack's must-not-change list
forbids; the wart is named here rather than fixed silently.

License rule (package docstring): written from the public NEC frame
description and the timing numbers stated above. No third-party
decoder implementation was consulted.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames, stamp_census
from ._base import Command
from .nec_recovery import is_repeat_marker

_LEADER_MARK_US = 9000
_LEADER_SPACE_US = 4500
_BIT_MARK_US = 562
_ZERO_SPACE_US = 562
_ONE_SPACE_US = 1687
_MODULATION_HZ = 38000
_TOLERANCE = 0.4

# Sanity floor for the trailer mark. The mark has no upper bound, for
# the reason samsung.py gives at its own end pulse: an emitter replaying
# a packet can fuse the trailer into whatever follows, and once fusion
# is possible the length carries no information. What bounds the frame
# is what comes AFTER the trailer, checked below.
_MIN_MARK_US = 200

_DATA_BITS = 42
_ADDRESS_BITS = 13
_COMMAND_BITS = 8
_EXT_ADDRESS_BITS = 26
_EXT_COMMAND_BITS = 16

_ADDRESS_MASK = (1 << _ADDRESS_BITS) - 1
_COMMAND_MASK = (1 << _COMMAND_BITS) - 1
_EXT_ADDRESS_MASK = (1 << _EXT_ADDRESS_BITS) - 1
_EXT_COMMAND_MASK = (1 << _EXT_COMMAND_BITS) - 1

# Remotes sending this shape pad to a 23 ms trailing space, well
# under the 110 ms an NEC1 main frame is padded to; either way any space
# above 8 ms is between frames rather than inside one, which is the same
# figure nec_recovery uses for the 32-bit frame.
_FRAME_GAP_US = 8000

# The repeat period an encoded repeat is spaced to. Only used to place
# encoded repeats; never a decode constraint.
_REPEAT_PERIOD_US = 108_000


def _tail_is_idle_or_repeats(frame: Sequence[int], index: int) -> bool:
    """Is everything after the trailer mark idle time or repeat markers?

    Marks are what matter. A space of any length is idle; a mark is more
    signal, and the only signal allowed after a complete NEC-family
    frame is a repeat marker. A capture cut partway through a trailing
    marker is accepted, because captures truncate routinely and the
    frame being judged has already ended.
    """
    rest = list(frame[index:])
    position = 0
    while position < len(rest):
        value = rest[position]
        if value < 0:
            position += 1
            continue
        if not is_close(value, _LEADER_MARK_US, _TOLERANCE):
            return False
        if position + 1 >= len(rest):
            return True
        if not is_close(-rest[position + 1], 2250, _TOLERANCE):
            return False
        if position + 2 >= len(rest):
            return True
        if not _MIN_MARK_US <= rest[position + 2] <= 1200:
            return False
        position += 3
    return True


def _read_frame(frame: Sequence[int]) -> int | None:
    """One frame to its 42-bit LSB-first wire value, or None.

    The bit count is exact and the frame has to end where it says it
    does. Both halves matter: without the count a 32-bit NEC frame is a
    prefix of nothing, and without the termination a 104-bit state blob
    is a 42-bit frame with something after it.
    """
    needed = 2 + 2 * _DATA_BITS + 1
    if len(frame) < needed:
        return None
    if not is_close(frame[0], _LEADER_MARK_US, _TOLERANCE):
        return None
    if not is_close(-frame[1], _LEADER_SPACE_US, _TOLERANCE):
        return None

    value = 0
    index = 2
    for bit_index in range(_DATA_BITS):
        mark = frame[index]
        space = -frame[index + 1]
        if not is_close(mark, _BIT_MARK_US, _TOLERANCE):
            return None
        if is_close(space, _ONE_SPACE_US, _TOLERANCE):
            value |= 1 << bit_index
        elif not is_close(space, _ZERO_SPACE_US, _TOLERANCE):
            return None
        index += 2

    if index >= len(frame) or frame[index] < _MIN_MARK_US:
        return None
    if not _tail_is_idle_or_repeats(frame, index + 1):
        return None
    return value


def _explained(frames: Sequence[Sequence[int]], votes: int) -> int:
    """Frames this decode accounted for: the votes plus repeat markers.

    Not ``repeat_count + 1``. A held NEC-family button sends the payload
    once and then floods 9000/2250 markers, and those are part of the
    capture even though they carry nothing to read.
    """
    return votes + sum(1 for frame in frames if is_repeat_marker(list(frame)))


def _encode(value: int) -> list[int]:
    """The 42-bit wire, LSB first, as a signed microsecond list."""
    timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
    for bit_index in range(_DATA_BITS):
        timings.append(_BIT_MARK_US)
        timings.append(
            -_ONE_SPACE_US if (value >> bit_index) & 1 else -_ZERO_SPACE_US
        )
    timings.append(_BIT_MARK_US)
    return timings


class NEC42ExtCommand(Command):
    """The 42-bit NEC1 frame read as a 26-bit address and 16-bit command.

    THE SINGLE WIRE BUILDER for the family. ``NEC42Command`` expands its
    checked fields into the same forty-two bits and delegates here, so
    the two readings can never drift into two waveforms.
    """

    #: The frame gap this protocol splits captures at, exposed so the
    #: coverage accounting in ``protocol_decode`` can count frames the
    #: way this decoder does.
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
        """Initialize the 42-bit verbatim NEC command."""
        if not 0 <= address <= _EXT_ADDRESS_MASK:
            raise ValueError(
                "NEC42ext address must be in range 0x0000000..0x3FFFFFF"
            )
        if not 0 <= command <= _EXT_COMMAND_MASK:
            raise ValueError("NEC42ext command must be in range 0x0000..0xFFFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @property
    def wire_value(self) -> int:
        """The 42-bit LSB-first value this command puts on the wire."""
        return (self.address & _EXT_ADDRESS_MASK) | (
            (self.command & _EXT_COMMAND_MASK) << _EXT_ADDRESS_BITS
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings: leader, 42 LSB-first bits, trailer mark."""
        frame = _encode(self.wire_value)
        timings = list(frame)
        if self.repeat_count > 0:
            gap = _REPEAT_PERIOD_US - sum(abs(value) for value in frame)
            for _ in range(self.repeat_count):
                timings.append(-max(gap, _FRAME_GAP_US))
                timings.extend(frame)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a NEC42ExtCommand, or None."""
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, _read_frame)
        if result is None:
            return None
        value, votes = result
        return stamp_census(
            cls(
                address=value & _EXT_ADDRESS_MASK,
                command=(value >> _EXT_ADDRESS_BITS) & _EXT_COMMAND_MASK,
                repeat_count=votes - 1,
            ),
            _explained(frames, votes),
        )


class NEC42Command(Command):
    """The 42-bit NEC1 frame read as 13/13/8/8 with both complements."""

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
        """Initialize the 42-bit checked NEC command."""
        if not 0 <= address <= _ADDRESS_MASK:
            raise ValueError("NEC42 address must be in range 0x0000..0x1FFF")
        if not 0 <= command <= _COMMAND_MASK:
            raise ValueError("NEC42 command must be in range 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @property
    def wire_value(self) -> int:
        """The 42-bit LSB-first value, complements expanded."""
        address = self.address & _ADDRESS_MASK
        command = self.command & _COMMAND_MASK
        return (
            address
            | ((~address & _ADDRESS_MASK) << _ADDRESS_BITS)
            | (command << (2 * _ADDRESS_BITS))
            | ((~command & _COMMAND_MASK) << (2 * _ADDRESS_BITS + _COMMAND_BITS))
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings by delegating to the single wire builder."""
        return NEC42ExtCommand(
            address=self.wire_value & _EXT_ADDRESS_MASK,
            command=(self.wire_value >> _EXT_ADDRESS_BITS) & _EXT_COMMAND_MASK,
            modulation=self.modulation,
            repeat_count=self.repeat_count,
        ).get_raw_timings()

    @classmethod
    def split_value(cls, value: int) -> tuple[int, int] | None:
        """``(address, command)`` when both complements hold, else None."""
        address = value & _ADDRESS_MASK
        address_inverse = (value >> _ADDRESS_BITS) & _ADDRESS_MASK
        command = (value >> (2 * _ADDRESS_BITS)) & _COMMAND_MASK
        command_inverse = (
            value >> (2 * _ADDRESS_BITS + _COMMAND_BITS)
        ) & _COMMAND_MASK
        if address ^ address_inverse != _ADDRESS_MASK:
            return None
        if command ^ command_inverse != _COMMAND_MASK:
            return None
        return (address, command)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a NEC42Command, or None."""
        frames = split_frames(timings, _FRAME_GAP_US)

        def decode_frame(frame: Sequence[int]) -> tuple[int, int] | None:
            value = _read_frame(frame)
            return None if value is None else cls.split_value(value)

        result = decode_frames_majority(frames, decode_frame)
        if result is None:
            return None
        (address, command), votes = result
        return stamp_census(
            cls(address=address, command=command, repeat_count=votes - 1),
            _explained(frames, votes),
        )
