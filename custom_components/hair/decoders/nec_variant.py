"""NEC1 frames whose fourth byte is not the third's complement.

NOT A DECODER, AND DELIBERATELY NOT REGISTERED. This module builds and
reads the frame; ``protocol_decode`` never probes it and no capture ever
mints a ``NECNC`` identity. Read the ruling before adding a registry
entry, because the ruling is the whole point of the module.

WHY THERE IS NO AIR DECODER. The only gate such a decoder could have is
"the command complement does not hold", which is the absence of the one
error check the NEC frame carries. Every NEC capture corrupted in its
third or fourth byte passes that gate, and counting settles that no
cheaper gate rescues it: all fifty-six non-complement Yamaha frames
measured sit at Hamming distance exactly one from a legal NEC frame, so
a genuine Yamaha press and a one-bit-corrupted NEC press are the same
shape and no distance rule separates them. A decoder here would turn every marginal NEC capture
into a confident wrong identity, and because a held press leaves NEC
repeat markers behind it, the frame accounting would mark that identity
as covering its capture and transmit from it. A raw row is better: it
replays exactly what was heard.

So off the air a non-complement frame stays what it is today, a raw row
carrying a fingerprint identity, which is what the frame census called
HAIR's design for this case.

WHAT THIS CLASS IS FOR. A FILE is a different matter. When a Flipper
``NECext`` line or a LIRC block states four bytes,
HAIR should transmit those four bytes rather than recompute the fourth
from the third. The Flipper builder in ``wig_adapters`` routes through
this class for exactly that reason: before it did, an Apple remote's
pairing id was thrown away and replaced with the complement of the
command byte, so the stored Pronto was HAIR's invention rather than the
file's frame. The row's identity still comes from re-decoding the
rendered Pronto, which lands on ``APPLE`` for an Apple frame and stays
raw for other non-complement frames. That division is the correct one:
the file told us the bytes, the air did not.

TIMING CONSTANTS ARE UPSTREAM'S, DELIBERATELY. The numbers below are
the ones ``infrared_protocols``' NEC encoder uses, not the slightly
different NEC timing set also in circulation (8990/-4490, 568,
552/1662). That is load-bearing rather than lazy: a file whose fourth
byte IS the complement must keep producing the Pronto it produces
today, byte for byte, and the stored Pronto is a function of these
constants. A round-trip test asserts it.

ONE CASE DOES CHANGE, and it is named rather than absorbed. Upstream's
encoder treats an address of 0xFF or less as a standard 8-bit NEC
address and emits its complement as the second byte. A file that says
``NECext`` and gives a low address means the two bytes it wrote, so
this class emits them verbatim. Such a file's Pronto changes, and so
does its identity (``NEC:0x0004:...`` where the complemented rendering
read ``NEC:0xfb04:...``). The Pronto alone would not have put those
bytes on the air, because the send path rebuilds a decodable row from
its triple through the upstream encoder; the importer therefore checks
every rendered row against that rebuild and stores the ones it cannot
reproduce with the protocol bypass set (``wig_adapters._triple_reproduces``).

License rule (package docstring): written from the public NEC frame
description. No third-party decoder implementation was consulted.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames, stamp_census
from ._base import Command
from .nec_recovery import is_repeat_marker

# Upstream's NEC encode constants. See the docstring: these are matched
# on purpose so a complement-valid file keeps its exact stored Pronto.
_LEADER_MARK_US = 9000
_LEADER_SPACE_US = 4500
_BIT_MARK_US = 562
_ZERO_SPACE_US = 562
_ONE_SPACE_US = 1687
_REPEAT_SPACE_US = 2250
_INITIAL_GAP_US = 41_000
_REPEAT_GAP_US = 96_000
_MODULATION_HZ = 38000
_TOLERANCE = 0.4
_MIN_MARK_US = 200

_DATA_BITS = 32
_FRAME_GAP_US = 8000

#: The label this class carries in the Flipper builder receipts and in
#: its own tests. It is NOT a decoded-protocol label: nothing registers
#: it, so no stored fingerprint ever reads ``NECNC``.
LABEL = "NECNC"


class NECNoComplementCommand(Command):
    """An NEC1 frame with both payload bytes taken verbatim.

    ``address`` is the 16-bit little-endian address exactly as written,
    ``command`` is the 16-bit little-endian pair of payload bytes
    exactly as written: byte3 is the low half, byte4 the high half.
    Neither is derived from the other.
    """

    #: Declared for symmetry with the registered decoders and so a
    #: future reader can split frames the way this class does. The
    #: coverage accounting never reads it, because nothing registers
    #: this class.
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
        """Initialize the verbatim NEC-shaped command."""
        if not 0 <= address <= 0xFFFF:
            raise ValueError("NECNC address must be in range 0x0000..0xFFFF")
        if not 0 <= command <= 0xFFFF:
            raise ValueError("NECNC command must be in range 0x0000..0xFFFF")
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

    @property
    def complement_holds(self) -> bool:
        """Would the strict NEC decoder accept this frame?

        True means the two payload bytes happen to be complements, so
        this frame is an ordinary NEC frame and an air capture of it
        decodes as ``NEC``. Used by the builder tests to pick the rows
        whose Pronto must not move.
        """
        _, _, byte3, byte4 = self.wire_bytes
        return byte3 ^ byte4 == 0xFF

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings: NEC1 frame, real repeat markers for dittos."""
        timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        for byte in self.wire_bytes:
            for bit_index in range(8):
                timings.append(_BIT_MARK_US)
                timings.append(
                    -_ONE_SPACE_US
                    if (byte >> bit_index) & 1
                    else -_ZERO_SPACE_US
                )
        timings.append(_BIT_MARK_US)

        gap = _INITIAL_GAP_US
        for _ in range(self.repeat_count):
            timings.extend(
                [-gap, _LEADER_MARK_US, -_REPEAT_SPACE_US, _BIT_MARK_US]
            )
            gap = _REPEAT_GAP_US
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Read an NEC1-shaped frame verbatim, or None.

        Reads whatever four bytes are there, complement or not, because
        the callers are file readers and round-trip tests rather than
        the capture path. ``protocol_decode`` must never call this: see
        the module docstring for why a verbatim air decoder is refused.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (address, command), votes = result
        markers = sum(1 for frame in frames if is_repeat_marker(list(frame)))
        return stamp_census(
            cls(address=address, command=command, repeat_count=markers),
            votes + markers,
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
