"""RC-6 IR command (Philips) with decode support.

Upstream ``infrared_protocols`` ships no RC-6 module at all (verified
against the CI-parity venv), so this class serves both directions. It is
written to the same shape as every module in this package so the donation
stays a near-file-copy.

IRP-style summary of the two forms this module handles::

    mode 0   {36k,444,msb}<-1,1|1,-1>(6,-2,1:1,0:3,<-2,2|2,-2>(T:1),D:8,F:8,^107m)
    mode 6A  {36k,444,msb}<-1,1|1,-1>(6,-2,1:1,6:3,-2,2,C:8|16,T:1,D:7,F:8,^107m)

RC-6 is Manchester coded like RC-5 but with INVERTED polarity: a logic 1
is mark-then-space, a logic 0 is space-then-mark. Adjacent same-sign
halves merge on the wire exactly as they do in ``rc5``. The unit time t is
444us, sixteen periods of the 36 kHz nominal carrier; real captures
routinely measure nearer 38 kHz, which is receiver measurement spread and
not a different protocol (the same spread shows on NEC).

Frame layout: a 6t mark + 2t space leader (RC-5 has no leader at all --
this is the structural discriminator between the two), then a start bit
which is always 1, then three mode bits, then the TRAILER BIT AT DOUBLE
WIDTH -- its two halves are 2t each where every other half-bit is 1t.
That mid-stream symbol-width change is the classic RC-6 implementation
trap: a uniform half-bit quantizer misaligns every bit after the trailer.
It also means a legal RC-6 waveform contains runs of 1t, 2t AND 3t (a 2t
trailer half abutting a same-sign 1t neighbour), so a two-bucket
short/long classifier cannot slice this protocol. The lattice walk below
therefore reads each symbol at its own declared width rather than
quantizing the frame uniformly up front.

WHERE THE TOGGLE LIVES, which differs by mode:

- Mode 0 spends the trailer bit on its traditional job: it is the toggle,
  flipping once per key press, and address and command are 8 bits each.
- Mode 6 does NOT. In mode 6 the trailer is the SUBMODE bit (0 = mode 6A,
  the command form; 1 = mode 6B, reserved for pointing devices), so it
  reads as permanently constant and the toggle has to live somewhere
  else. It moved into the payload: the first data bit after the customer
  field is the toggle, leaving 7 bits of address and 8 of command. This
  is documented for the Microsoft Media Center variant (customer 0x800F,
  described as RC6-6-32 with the standard toggle bit zero and a
  nonstandard toggle added) and it is what MaxRower's VU+ set-top-box
  captures do as well (customer 0x8052, GH #33): across two presses of
  one button the trailer stayed 0 and exactly one bit alternated, the
  most significant bit of what would otherwise be the address byte.
  Two independent OEMs, same structure. This module applies the T:1,
  D:7, F:8 split to every mode 6 frame; the documented anchor is MCE and
  the second witness is the VU+ capture set, so treat a third OEM that
  contradicts it as a finding, not as a reason to widen the rule here.

Mode 6 also carries a customer/OEM field whose LENGTH is signalled by its
own first bit: a leading 0 means an 8-bit field holding a 7-bit value,
a leading 1 means a 16-bit field holding a 15-bit value. The value is
quoted inclusive of that flag bit throughout this module, which is the
universal convention for the family (MCE is always written 0x800F, never
0x000F). Mode and customer are IDENTITY -- they separate two remotes that
share an address and command -- and are folded into the fingerprint
suffix by the registry. The toggle is press state and is excluded from
identity, exactly as in RC-5.

Mode 6A does not encode its own payload length; the spec leaves the width
to the OEM and offers only the signal-free time as a terminator. Rather
than guess, this decoder accepts a 16-bit remainder after the customer
field (either customer width) and refuses anything else, so an unknown
variant stays undecoded and matches on the raw tiers instead of being
handed a wrong identity.

The known deferral is RC6-6-20: mode 6 with an 8-bit customer and a
12-bit remainder, 241 signals in Flipper-IRDB, concentrated in Sky,
Amstrad, Thomson and Philips set-top boxes. Its leaders measure clean, so
these are real RC-6 -- but how those 12 bits split into toggle, address
and command is not in any open source consulted here, and a guessed split
would mint wrong identities for a whole device family. They stay
undecoded until somebody has captures that settle it.

Held keys re-send the frame with the toggle constant, so multi-frame
captures majority-vote like every decoder in this package, and a lone
frame decodes standalone.

License rule (package docstring): written from open protocol
documentation and validated against real captures. No GPL/LGPL-derived
implementation was consulted.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames
from ._base import Command
from .rc5 import _append_signed_us, _strip_idle_edges

_UNIT_US = 444
_MODULATION_HZ = 36000
# RC-6 pads the frame to a ~107ms period the way RC-5 pads to 114ms. The
# figure is well attested in protocol references but not in a primary
# specification, and reference versions disagree over whether mode 6
# carries it at all, so it is used ONLY to space encoded repeats and is
# never a decode constraint.
_REPEAT_PERIOD_US = 107000

_LEADER_MARK_UNITS = 6
_LEADER_SPACE_UNITS = 2
_TRAILER_HALF_UNITS = 2

# The longest legitimate run inside a frame is 3t: a 2t trailer half
# abutting a same-sign 1t neighbour half. Doubling that for receiver
# spread gives ~2664us, while a repeating RC-6 remote leaves tens of
# milliseconds between frames (a ~107ms period around a ~47ms frame).
# 5000us sits with roughly 2x headroom above the worst legitimate
# internal run and an order of magnitude below the real inter-frame
# silence, so it can neither split a frame nor fuse two.
_FRAME_GAP_US = 5000

_MAX_RUN_UNITS = 3
# Half-bit widths are classified by rounding to whole units and then
# bounds-checking, so a run has to land within half a unit of a legal
# width. 0.4 matches the package tolerance used everywhere else.
#
# The leader is checked at the same tolerance, and deliberately is NOT
# tightened to make it a better filter. Measured over the 1670 Flipper-
# IRDB signals this decoder accepts, real leader spaces run from 0.77 to
# 1.06 of nominal, while a Sony SIRC frame opens 2400/600 -- 0.68 of
# nominal. The two populations are only ~13 percent apart, so no
# tolerance separates them without dropping real captures. The leader is
# therefore the discriminator against RC-5 (which has no leader at all),
# and what actually rejects a Sony frame is the structure behind it: the
# fixed start bit, the mode gate, the exact payload width, and the
# Manchester consistency of every symbol. That combination rejected all
# 129,772 non-RC6 raw signals in the archive with no false positive.
_UNIT_TOLERANCE = 0.4

_MODE_0 = 0
_MODE_6 = 6
_SUBMODE_6A = 0

_MODE_0_DATA_BITS = 16
_MODE_6_REMAINDER_BITS = 16
_SCC_FIELD_BITS = 8
_LCC_FIELD_BITS = 16


def _bits_to_int(bits: Sequence[int]) -> int:
    """Fold MSB-first bits into an integer."""
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def _customer_field_bits(customer: int) -> int:
    """Return the on-wire width of ``customer``, or 0 when unrepresentable.

    The field's own first bit signals its length, so only two ranges are
    encodable: 0x00..0x7F rides an 8-bit field behind a leading 0, and
    0x8000..0xFFFF rides a 16-bit field behind a leading 1. A value
    between the two has no wire form.
    """
    if 0 <= customer <= 0x7F:
        return _SCC_FIELD_BITS
    if 0x8000 <= customer <= 0xFFFF:
        return _LCC_FIELD_BITS
    return 0


class RC6Command(Command):
    """RC-6 IR command (Philips and derivatives) with decode support."""

    address: int
    command: int
    toggle: int
    mode: int
    customer: int | None

    def __init__(
        self,
        *,
        address: int,
        command: int,
        toggle: int = 0,
        mode: int = _MODE_0,
        customer: int | None = None,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the RC-6 IR command."""
        if mode not in (_MODE_0, _MODE_6):
            raise ValueError("RC-6 mode must be 0 or 6")
        if mode == _MODE_0:
            if customer is not None:
                raise ValueError("RC-6 mode 0 carries no customer field")
            if not 0 <= address <= 0xFF:
                raise ValueError("RC-6 mode 0 address must be in range 0x00..0xFF")
        else:
            if customer is None:
                raise ValueError("RC-6 mode 6 requires a customer field")
            if not _customer_field_bits(customer):
                raise ValueError(
                    "RC-6 customer must be 0x00..0x7F (8-bit field) or "
                    "0x8000..0xFFFF (16-bit field)"
                )
            if not 0 <= address <= 0x7F:
                raise ValueError("RC-6 mode 6 address must be in range 0x00..0x7F")
        if not 0 <= command <= 0xFF:
            raise ValueError("RC-6 command must be in range 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.toggle = toggle & 1
        self.mode = mode
        self.customer = customer

    # -- encode ------------------------------------------------------------

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the RC-6 command (leader + Manchester body)."""
        frame: list[int] = []
        _append_signed_us(frame, _LEADER_MARK_UNITS * _UNIT_US)
        _append_signed_us(frame, -_LEADER_SPACE_UNITS * _UNIT_US)

        self._encode_bit(frame, 1, 1)  # start bit, always 1
        for shift in (2, 1, 0):
            self._encode_bit(frame, (self.mode >> shift) & 1, 1)

        # Mode 0 spends the trailer on the toggle; mode 6 spends it on
        # the submode flag and moves the toggle into the payload.
        trailer = self.toggle if self.mode == _MODE_0 else _SUBMODE_6A
        self._encode_bit(frame, trailer, _TRAILER_HALF_UNITS)

        for bit in self._payload_bits():
            self._encode_bit(frame, bit, 1)
        _strip_idle_edges(frame)

        timings = list(frame)
        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in frame)
            gap = _REPEAT_PERIOD_US - frame_duration
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(frame)
        return timings

    def _payload_bits(self) -> list[int]:
        """Build the MSB-first payload bits that follow the trailer."""
        bits: list[int] = []
        if self.mode == _MODE_0:
            for shift in range(7, -1, -1):
                bits.append((self.address >> shift) & 1)
        else:
            customer = self.customer or 0
            width = _customer_field_bits(customer)
            for shift in range(width - 1, -1, -1):
                bits.append((customer >> shift) & 1)
            bits.append(self.toggle)
            for shift in range(6, -1, -1):
                bits.append((self.address >> shift) & 1)
        for shift in range(7, -1, -1):
            bits.append((self.command >> shift) & 1)
        return bits

    @staticmethod
    def _encode_bit(timings: list[int], bit: int, half_units: int) -> None:
        """Append one Manchester symbol of ``half_units`` per half.

        RC-6 polarity: logic 1 is mark-then-space, logic 0 is
        space-then-mark -- the opposite of RC-5.
        """
        half_us = half_units * _UNIT_US
        if bit:
            _append_signed_us(timings, half_us)
            _append_signed_us(timings, -half_us)
        else:
            _append_signed_us(timings, -half_us)
            _append_signed_us(timings, half_us)

    # -- decode ------------------------------------------------------------

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into an RC6Command.

        Returns the majority identity across the frames in the capture,
        with ``repeat_count`` set to the number of extra agreeing frames,
        or None when no frame decodes as RC-6.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (mode, customer, address, command, toggle), votes = result
        return cls(
            address=address,
            command=command,
            toggle=toggle,
            mode=mode,
            customer=customer,
            repeat_count=votes - 1,
        )

    @classmethod
    def _decode_frame(
        cls, frame: Sequence[int]
    ) -> tuple[int, int | None, int, int, int] | None:
        """Decode one frame to ``(mode, customer, address, command, toggle)``."""
        halves = cls._to_half_bits(frame)
        if halves is None:
            return None

        walk = _LatticeWalk(halves)
        start = walk.read(1)
        if start != 1:  # the start bit is always 1
            return None
        mode_bits = [walk.read(1) for _ in range(3)]
        if any(bit is None for bit in mode_bits):
            return None
        mode = _bits_to_int([b for b in mode_bits if b is not None])
        trailer = walk.read(_TRAILER_HALF_UNITS)
        if trailer is None:
            return None

        data = walk.read_rest()
        if data is None:
            return None

        if mode == _MODE_0:
            if len(data) != _MODE_0_DATA_BITS:
                return None
            address = _bits_to_int(data[:8])
            command = _bits_to_int(data[8:])
            return (mode, None, address, command, trailer)

        if mode == _MODE_6:
            # In mode 6 the trailer is the submode bit, not a toggle.
            # 6B is the pointing-device form and is not a command frame.
            if trailer != _SUBMODE_6A:
                return None
            if not data:
                return None
            width = _LCC_FIELD_BITS if data[0] else _SCC_FIELD_BITS
            if len(data) != width + _MODE_6_REMAINDER_BITS:
                return None
            customer = _bits_to_int(data[:width])
            rest = data[width:]
            toggle = rest[0]
            address = _bits_to_int(rest[1:8])
            command = _bits_to_int(rest[8:])
            return (mode, customer, address, command, toggle)

        return None

    @staticmethod
    def _to_half_bits(frame: Sequence[int]) -> list[int] | None:
        """Expand a leader-bearing frame into +/-1 half-bit units.

        The leader is verified and consumed; everything after it becomes
        one entry per unit, so a 2t run contributes two entries and the
        double-width trailer occupies four. A trailing space longer than
        any legal run is the signal-free time and is dropped.
        """
        if len(frame) < 4:
            return None
        if frame[0] <= 0 or frame[1] >= 0:
            return None
        if not is_close(frame[0], _LEADER_MARK_UNITS * _UNIT_US, _UNIT_TOLERANCE):
            return None
        if not is_close(-frame[1], _LEADER_SPACE_UNITS * _UNIT_US, _UNIT_TOLERANCE):
            return None

        body = list(frame[2:])
        if body and body[-1] < 0:
            units = round(-body[-1] / _UNIT_US)
            if units > _MAX_RUN_UNITS:
                body.pop()  # signal-free time, not a half-bit
        if not body:
            return None

        halves: list[int] = []
        for value in body:
            magnitude = abs(value)
            units = round(magnitude / _UNIT_US)
            if not 1 <= units <= _MAX_RUN_UNITS:
                return None
            if not is_close(magnitude, units * _UNIT_US, _UNIT_TOLERANCE):
                return None
            halves.extend([1 if value > 0 else -1] * units)
        return halves


class _LatticeWalk:
    """Cursor over a half-bit lattice that reads symbols at their own width.

    RC-6 changes symbol width mid-frame (the double-width trailer), so the
    walk cannot pre-slice the lattice into fixed-size bits. Each read
    consumes ``2 * width`` halves and checks that the two halves are
    uniform and opposite, which is what makes a misaligned frame fail
    loudly instead of decoding to a plausible wrong value.
    """

    def __init__(self, halves: Sequence[int]) -> None:
        self._halves = list(halves)
        self._pos = 0

    def read(self, width: int) -> int | None:
        """Read one Manchester symbol whose halves are ``width`` units each."""
        need = 2 * width
        remaining = len(self._halves) - self._pos
        if remaining < need:
            # A frame ending on a logic 1 loses its trailing space to the
            # signal-free time, so a mark-only tail of the right width is
            # a complete symbol.
            if remaining == width and all(
                h > 0 for h in self._halves[self._pos :]
            ):
                self._pos = len(self._halves)
                return 1
            return None
        first = self._halves[self._pos : self._pos + width]
        second = self._halves[self._pos + width : self._pos + need]
        self._pos += need
        if all(h > 0 for h in first) and all(h < 0 for h in second):
            return 1  # RC-6: mark-then-space is logic 1
        if all(h < 0 for h in first) and all(h > 0 for h in second):
            return 0
        return None

    def read_rest(self) -> list[int] | None:
        """Read single-width symbols until the lattice is exhausted."""
        bits: list[int] = []
        while self._pos < len(self._halves):
            bit = self.read(1)
            if bit is None:
                return None
            bits.append(bit)
        return bits
