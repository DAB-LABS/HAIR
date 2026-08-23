"""RCA IR command with decode support.

The RCA-brand protocol of the JP1/DecodeIR world, carried by RCA
televisions and by TCL's Google TV remotes (TCL licenses the RCA
brand). Canonical IRP, from the DecodeIR protocol reference:

    {58k,460,msb}<1,-2|1,-4>(8,-8,D:4,F:8,~D:4,~F:8,1,-16)+

- Pulse-distance modulation, MSB first, 460us base unit.
- Header: 8 units mark, 8 units space (sbprojects gives this as a
  flat 4 ms / 4 ms AGC pair; captures read ~4077/4077).
- 24 bits: D:4 then F:8, then the same twelve bits INVERTED. The
  complement half is the protocol's only integrity check and this
  decoder requires it exactly -- there is no salvage tier.
- Each bit is a 1-unit mark plus a 2-unit (zero) or 4-unit (one)
  space. Captures read 500us marks with ~1000us / ~2050us spaces,
  which is sbprojects' 1.5 ms / 2.5 ms bit total.
- Lead-out: a trailer mark, then a 16-unit space. A held key
  re-sends the WHOLE frame; there is no repeat code, no toggle and
  no rolling counter, so identity is device + function and the
  frame count is press length, never identity.

The frame duration is CONSTANT, which is a useful sanity check: the
complement half guarantees exactly twelve one-bits and twelve
zero-bits per frame, so every frame runs 8000 + 12*1500 + 12*2500 +
500 = 56.5 ms. Add the observed ~8.7 ms inter-frame space and the
period is ~65 ms, which is sbprojects' "repeated every 64 ms
measured from start to start".

CARRIER. DecodeIR documents 58 kHz for RCA and sbprojects 56 kHz,
but it ALSO documents RCA-38 / RCA-38(Old) at 38.7 kHz -- "recently
discovered variants ... differ from RCA and RCA(Old) only in the
frequency". The TCL captures that motivated this decoder read
~38 kHz, which is therefore either a genuine RCA-38 handset or a
38 kHz demodulator reporting its own centre; the capture cannot
tell the two apart and neither can this module. So the canonical
re-encode uses the CAPTURED carrier and never snaps to the
documented 56/58 kHz on the strength of a spec sheet; the default
below is the capture's 38 kHz, matching the rest of this package.
Raw replay (tx_force_raw) stays available either way.

SCOPE. Only the witnessed 24-bit shape. RCA(Old) (32-unit lead-in,
double-length trailer) and any other bit count reject cleanly
rather than half-decoding: the header check kills the former and
the exact-24-pairs check the latter.

Protocol research: the sbprojects RCA page and the DecodeIR
protocol reference (hifi-remote.com/johnsfine/DecodeIR.html),
prose only -- no GPL/LGPL implementation was consulted.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command

# Nominal wire timings. The two sources disagree by ~10% (JP1's 460us
# unit gives 3680/920/1840; sbprojects gives 4000/1000/2000) and the
# captures sit on sbprojects' numbers, so those are the nominals and
# the tolerance below is what has to swallow the difference.
_HEADER_MARK_US = 4000
_HEADER_SPACE_US = 4000
_BIT_MARK_US = 500
_ZERO_SPACE_US = 1000
_ONE_SPACE_US = 2000
# Lead-out space (16 units at JP1's 460us; captures read ~8700us).
_TRAILER_SPACE_US = 8700
_MODULATION_HZ = 38000

# Three tolerances, because the three checks are doing three different
# jobs. Each is set by what it has to separate, not by taste.
#
# SPACES classify into two symbols, so their bands must not touch. The
# two nominals are a factor of two apart, and the package default 0.4
# would run zero up to 1400us and one down to 1200us -- a ~1300us space
# would match both. 0.3 keeps them disjoint (zero 700..1300, one
# 1400..2600) while still accepting both documented timing sets, JP1's
# 920/1840 and sbprojects' 1000/2000, and the captured 1026/2050.
_TOLERANCE = 0.3
# MARKS classify into nothing -- the check is purely structural, so
# there is no disjointness to protect and the band should be set by the
# observed spread of real captures. The Flipper-IRDB sweep measured
# 47,825 bit marks in complement-valid RCA frames: p1 462us, p50 504us,
# p99 905us, and a clean EMPTY GAP between 681us and 834us. Below the
# gap is genuine RCA stretched by receiver AGC (a live Thomson capture
# reaches 681us; Thomson owns the RCA brand). Above it is a different
# protocol family sharing this frame architecture at a ~845us unit
# (Hitachi MX421, Panasonic, Uniden, Funai, DMX), which plan section 8
# puts out of scope and which must reject. 0.4 -- the package default
# -- puts the ceiling at 700us, inside that gap: it admits every real
# RCA mark the corpus contains and stops 1.19x short of the nearest
# foreign one. Measured: 0.3 loses 18 real Thomson signals, 0.5 gains
# nothing over 0.4, and 0.8 lets 154 foreign signals in.
_MARK_TOLERANCE = 0.4
# The HEADER gets the tightest band of the three, and has to: the header
# space and the inter-frame gap are exactly what the frame splitter
# tells apart, and at 0.3 the header space would reach 5200us and crowd
# the gap threshold below. 0.2 accepts 3200..4800, which still covers
# both documented headers (JP1's 3680, sbprojects' 4000) and the
# captured 4050..4102 with room to spare.
_HEADER_TOLERANCE = 0.2

_DATA_BITS = 12       # D:4 + F:8
_FRAME_BITS = 24      # ...followed by the same twelve inverted
_DATA_MASK = 0xFFF

# header pair (2) + 24 bit pairs (48) + trailer mark (1)
_FRAME_LEN = 2 + _FRAME_BITS * 2 + 1

# Frame-splitting margin. Unusually for this package the gap threshold
# is squeezed from BOTH sides, because RCA's header space is long:
#
#   widest space that is still a BIT     2000 * 1.3 = 2600us
#   widest space that is still a HEADER  4000 * 1.2 = 4800us
#   -> threshold must sit above 4800us
#   narrowest space that is a GAP        16 * 460   = 7360us  (JP1 IRP)
#   observed gap                                      ~8700us
#   -> threshold must sit below 7360us
#
# 6000us takes the middle: 1.25x above the widest header space, 1.23x
# below the narrowest documented lead-out, 1.45x below the observed
# one. The 8000us constant the other decoders in this package use would
# be WRONG here -- it lands ABOVE the 7360us lead-out and would fuse
# every RCA frame in the capture into one unreadable run.
_FRAME_GAP_US = 6000


class RCACommand(Command):
    """RCA IR command with decode support."""

    device: int
    function: int

    def __init__(
        self,
        *,
        device: int,
        function: int,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the RCA IR command.

        :param device: device/address code D (4 bits)
        :param function: button code F (8 bits)
        :param modulation: carrier in Hz. Defaults to the captured
            38 kHz, not the documented 56/58 kHz -- see the module
            docstring; DecodeIR documents both as real variants.
        """
        if not 0 <= device <= 0xF:
            raise ValueError(f"device must be in range 0-15, got {device}")
        if not 0 <= function <= 0xFF:
            raise ValueError(f"function must be in range 0-255, got {function}")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.function = function

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the RCA command.

        Positive values are mark durations in microseconds, negative
        values are spaces. One frame: header pair, twenty-four MSB-first
        bits (D:4, F:8, then those twelve inverted), trailer mark, and
        the lead-out space -- so the frame is self-terminating and the
        ordinary send machinery can re-send it for a repeat without
        gluing two frames together.
        """
        data = (self.device << 8) | self.function
        word = (data << _DATA_BITS) | (~data & _DATA_MASK)

        frame: list[int] = [_HEADER_MARK_US, -_HEADER_SPACE_US]
        for index in range(_FRAME_BITS - 1, -1, -1):  # MSB first
            frame.append(_BIT_MARK_US)
            bit = (word >> index) & 1
            frame.append(-(_ONE_SPACE_US if bit else _ZERO_SPACE_US))
        frame.extend([_BIT_MARK_US, -_TRAILER_SPACE_US])

        timings = list(frame)
        for _ in range(self.repeat_count):
            timings.extend(frame)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into an RCACommand, or None.

        The capture is split at the inter-frame gap and every frame
        decodes independently; the majority vote across them is the
        identity. A held button produces however many frames it
        produces, and because the payload never changes -- no toggle,
        no counter -- three frames, four frames and five frames all
        yield the SAME (device, function). Frame count rides in
        ``repeat_count``, which is press length and is deliberately
        not part of identity.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (device, function), votes = result
        return cls(device=device, function=function, repeat_count=votes - 1)

    @classmethod
    def _decode_frame(cls, frame: Sequence[int]) -> tuple[int, int] | None:
        """Decode one RCA frame to ``(device, function)``, or None.

        Header pair in tolerance, exactly twenty-four bit pairs, a
        trailer mark, and bits 12..23 the EXACT bitwise complement of
        bits 0..11. The complement is the whole integrity story here,
        so it is checked without slack: a single flipped bit rejects
        the frame rather than being repaired.
        """
        if len(frame) < _FRAME_LEN:
            return None
        if not is_close(frame[0], _HEADER_MARK_US, _HEADER_TOLERANCE):
            return None
        if not is_close(-frame[1], _HEADER_SPACE_US, _HEADER_TOLERANCE):
            return None

        word = 0
        for index in range(_FRAME_BITS):
            mark = frame[2 + 2 * index]
            space = -frame[3 + 2 * index]
            if not is_close(mark, _BIT_MARK_US, _MARK_TOLERANCE):
                return None
            bit = cls._classify_space(space)
            if bit is None:
                return None
            word = (word << 1) | bit  # MSB first

        trailer = frame[2 + 2 * _FRAME_BITS]
        if not is_close(trailer, _BIT_MARK_US, _MARK_TOLERANCE):
            return None
        # Nothing but the lead-out may follow the trailer mark; a
        # further mark means split_frames did not separate something,
        # so reject rather than decode half a capture.
        if any(value > 0 for value in frame[_FRAME_LEN:]):
            return None

        data = (word >> _DATA_BITS) & _DATA_MASK
        check = word & _DATA_MASK
        if check != (~data & _DATA_MASK):
            return None
        return ((data >> 8) & 0xF, data & 0xFF)

    @staticmethod
    def _classify_space(space_us: int) -> int | None:
        """Classify a bit space as 0 (~1000us) or 1 (~2000us), or None."""
        if is_close(space_us, _ZERO_SPACE_US, _TOLERANCE):
            return 0
        if is_close(space_us, _ONE_SPACE_US, _TOLERANCE):
            return 1
        return None
