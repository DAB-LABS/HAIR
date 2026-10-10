"""TDC-38 IR command with decode support.

TDC-38 is the 17-bit Manchester format of set-top boxes such as the
Telekom Media Receivers (MR401) and Magenta boxes. The public IRP is::

    {38k,315,msb}<-1,1|1,-1>(1,-1,D:5,S:5,F:7,-89m)*[D:0..31,S:0..31,F:0..127]

So one frame is a start cell and then D (5 bits), S (5) and F (7), most
significant bit first, on a 315us half-bit. A 1 is mark-then-space, a 0
is space-then-mark, and the start cell is a mark-then-space, so it reads
as a 1. Frames repeat while the button is held, 89ms apart, with no
toggle bit. Raw timings carry no carrier, so the decoder reads a frame at
any carrier; the encoder sends at 38kHz.

Decoding quantizes every timing to one or two half-bits, rebuilds the
36-half lattice (restoring the trailing space a final 1 loses to the
gap), and reads cell i from lattice positions 2i and 2i+1.

THE WINDOWS. One half-bit is 230..420us, two are 480..800us, and a
timing in the 420..480us dead zone or outside both windows fails the
frame. The captures this was measured on span 289..342us and 605..657us.
Under the air-path signature (marks x0.85, spaces x1.12) a frame on any
half-bit from about 285us to 355us still reads. TDC-56 is the same frame
on a 213us half-bit: as sent, its single half-bits fall below the 230us
floor and its double ones in the dead zone, so it is refused, but a
TDC-56 capture stretched by 13 percent or more reads as TDC-38. This
class does not try to tell the two apart. RC-5 (889us halves, 14 cells),
RC-6 (2664us leader) and the 23-cell 250/320us Manchester formats are
refused by the windows or by the exact 18-cell count.

THE LEADING MARK. The first mark of every frame is the start cell's
mark, so it is always exactly one half-bit: nothing comes before it to
merge with. Receivers often stretch it (a bench Broadlink-to-Athom run
delivered it at up to 474us, above the 420us top of the short window,
while every other edge stayed inside), so it alone is read as one
half-bit anywhere from 230us up to, but not including, 800us. Every other
edge, and both windows and the dead zone, are unchanged.

THE START CELL. A frame always opens on a mark, because the frame
splitter drops leading silence, so a first cell that reads at all reads
1, and there is nothing to check. TDC-38 never sends a 0 start cell.

THE CUT FINAL FRAME. A held press heard through a fixed learn window
often ends partway through a frame. The value comes from whole frames
only, and a cut frame never votes, so a capture whose only frame is cut
decodes to nothing. But the final frame of a capture, and only that one,
is counted as explained when it is shorter than a whole frame by at
least one cell and every cell it reads agrees with the winning frame,
across at least six cells counting the start cell. The capture's last
timing, where the window closed, is not read, but it must not be longer
than two half-bits: a frame that ends in a long silence was not cut.
Without this rule, such a press would read as a decode that does not
cover its capture, and for this protocol the identity a capture falls
back to then is shared by every button whose code has the same length.

A cut frame of 11 cells or fewer reads only the start cell, D and S, so
it confirms the remote, not the button; one that reaches into F confirms
only the bits of F it reads. The value still comes from whole frames.

SENDING A DECODED ROW. ``REBUILD_CARRIER_HZ`` tells the send path that a
row is rebuilt from its decode only when its stored carrier is about
38kHz. A capture stored at another carrier decodes like any other, but
is sent as captured, because the rebuild would change its carrier and
its half-bit.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import majority, split_frames, stamp_census
from ._base import Command

_HALF_BIT_US = 315
_MODULATION_HZ = 38000
# The IRP's trailing space after every frame.
_TRAILING_GAP_US = 89000

# Quantization windows (see the module docstring).
_ONE_HALF_MIN_US = 230
_ONE_HALF_MAX_US = 420
_TWO_HALF_MIN_US = 480
_TWO_HALF_MAX_US = 800
# The first mark of a frame is always one half-bit, so it is read as one
# across a wider range (see THE LEADING MARK).
_LEAD_MARK_MAX_US = _TWO_HALF_MAX_US  # exclusive

# Inside a frame no space exceeds two half-bits; the gap is ~89ms.
_FRAME_GAP_US = 8000

_FRAME_CELLS = 18  # start cell + 17 data bits
_FRAME_HALVES = 2 * _FRAME_CELLS
# A cut final frame must read at least this many cells, start included.
_MIN_CUT_CELLS = 6

_DEVICE_BITS = 5
_SUBDEVICE_BITS = 5
_FUNCTION_BITS = 7


def _append_signed_us(timings: list[int], value: int) -> None:
    """Append a microsecond duration, merging into the last entry if same sign."""
    if timings and (timings[-1] > 0) == (value > 0):
        timings[-1] += value
    else:
        timings.append(value)


def _lattice(frame: Sequence[int]) -> list[int] | None:
    """Expand timings into a +/-1 half-bit lattice, or None off-window.

    The frame's first timing is a mark (the frame splitter drops leading
    silence) and is the start cell's single half-bit, read with the
    wider leading-mark bound; every other timing uses the two windows.
    """
    halves: list[int] = []
    for index, value in enumerate(frame):
        magnitude = abs(value)
        if index == 0 and value > 0 and (
            _ONE_HALF_MIN_US <= magnitude < _LEAD_MARK_MAX_US
        ):
            units: int | None = 1
        else:
            units = _units(magnitude)
        if units is None:
            return None
        halves.extend([1 if value > 0 else -1] * units)
        if len(halves) > _FRAME_HALVES:
            return None
    return halves


def _units(magnitude: int) -> int | None:
    """How many half-bits one timing spans, or None outside both windows."""
    if _ONE_HALF_MIN_US <= magnitude <= _ONE_HALF_MAX_US:
        return 1
    if _TWO_HALF_MIN_US <= magnitude <= _TWO_HALF_MAX_US:
        return 2
    return None


def _cells(halves: Sequence[int]) -> list[int] | None:
    """Read Manchester cells from a +/-1 half-bit lattice (even length)."""
    bits: list[int] = []
    for i in range(0, len(halves) - 1, 2):
        first, second = halves[i], halves[i + 1]
        if first > 0 and second < 0:
            bits.append(1)
        elif first < 0 and second > 0:
            bits.append(0)
        else:
            return None
    return bits


def _frame_bits(device: int, subdevice: int, function: int) -> list[int]:
    """The 18 cells of one frame: the start cell, then D, S, F MSB first."""
    bits = [1]
    for value, width in (
        (device, _DEVICE_BITS),
        (subdevice, _SUBDEVICE_BITS),
        (function, _FUNCTION_BITS),
    ):
        bits.extend((value >> i) & 1 for i in range(width - 1, -1, -1))
    return bits


class TDC38Command(Command):
    """TDC-38 IR command (Telekom Media Receivers, Magenta) with decode support."""

    #: The frame gap this protocol splits captures at, exposed so the
    #: coverage accounting in ``protocol_decode`` counts frames the way
    #: this decoder does.
    FRAME_GAP_US = _FRAME_GAP_US

    #: Rebuild a decoded row only when its stored carrier is about this
    #: (see ``protocol_decode.carrier_allows_rebuild``). The encoder only
    #: knows one carrier and one half-bit, so a row captured at another
    #: carrier is replayed as captured instead.
    REBUILD_CARRIER_HZ = _MODULATION_HZ

    device: int
    subdevice: int
    function: int

    def __init__(
        self,
        *,
        device: int,
        subdevice: int,
        function: int,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the TDC-38 IR command."""
        if not 0 <= device <= 0x1F:
            raise ValueError("TDC-38 device must be in range 0..31")
        if not 0 <= subdevice <= 0x1F:
            raise ValueError("TDC-38 subdevice must be in range 0..31")
        if not 0 <= function <= 0x7F:
            raise ValueError("TDC-38 function must be in range 0..127")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.subdevice = subdevice
        self.function = function

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the TDC-38 command (18 Manchester cells)."""
        frame: list[int] = []
        for bit in _frame_bits(self.device, self.subdevice, self.function):
            if bit:
                _append_signed_us(frame, _HALF_BIT_US)
                _append_signed_us(frame, -_HALF_BIT_US)
            else:
                _append_signed_us(frame, -_HALF_BIT_US)
                _append_signed_us(frame, _HALF_BIT_US)

        timings: list[int] = []
        for index in range(self.repeat_count + 1):
            for value in frame:
                _append_signed_us(timings, value)
            if index < self.repeat_count:
                _append_signed_us(timings, -_TRAILING_GAP_US)
        if timings and timings[-1] < 0:
            timings.pop()  # the final trailing space is idle, not signal
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a TDC38Command.

        Returns the majority identity across the whole frames of the
        capture, with ``repeat_count`` set to the number of extra agreeing
        frames, or None when no whole frame decodes as TDC-38.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        decoded = [cls._decode_frame(frame) for frame in frames]
        top = majority([value for value in decoded if value is not None])
        if top is None:
            return None
        (device, subdevice, function), votes = top
        explained = votes
        if (
            len(frames) > 1
            and decoded[-1] is None
            and cls._is_cut_copy(
                frames[-1], _frame_bits(device, subdevice, function)
            )
        ):
            explained += 1
        return stamp_census(
            cls(
                device=device,
                subdevice=subdevice,
                function=function,
                repeat_count=votes - 1,
            ),
            explained,
        )

    @classmethod
    def _decode_frame(cls, frame: Sequence[int]) -> tuple[int, int, int] | None:
        """Decode one whole frame to ``(device, subdevice, function)``."""
        halves = _lattice(frame)
        if halves is None:
            return None
        if len(halves) == _FRAME_HALVES - 1:
            halves.append(-1)  # a final 1's space, swallowed by the gap
        if len(halves) != _FRAME_HALVES:
            return None
        bits = _cells(halves)
        if bits is None:
            return None
        value = 0
        for bit in bits[1:]:
            value = (value << 1) | bit
        function = value & 0x7F
        subdevice = (value >> _FUNCTION_BITS) & 0x1F
        device = value >> (_FUNCTION_BITS + _SUBDEVICE_BITS)
        return (device, subdevice, function)

    @staticmethod
    def _is_cut_copy(frame: Sequence[int], winner: Sequence[int]) -> bool:
        """Is this final frame the winning frame, cut short?

        The last timing is where the capture stopped, so it may itself be
        cut: it is bounded but not read. Every timing before it must fit
        a window, the frame must be at least one cell short of a whole
        one, and every cell it reads must match the winner's prefix.
        """
        if len(frame) < 2 or abs(frame[-1]) > _TWO_HALF_MAX_US:
            return False
        halves = _lattice(frame[:-1])
        if halves is None:
            return False
        # At most two more halves sit in the unread final timing.
        if len(halves) + 2 > _FRAME_HALVES - 2:
            return False
        read = halves[: len(halves) - len(halves) % 2]
        bits = _cells(read)
        if bits is None or len(bits) < _MIN_CUT_CELLS:
            return False
        return list(winner[: len(bits)]) == bits
