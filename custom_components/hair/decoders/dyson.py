"""Dyson fan/purifier IR command with decode support.

The "Dysan" protocol of the JP1 world (hifi-remote.com t=101540),
carried by Dyson AM/TP/HP-family fans. Canonical IRP:

    {780,38k}<1,-1|1,-2>(3,-1,D:7,F:8,1,-104m)

- 38 kHz carrier, 780us base unit, space-length encoding.
- Leader: 2340us mark (3 units), 780us space.
- 15 payload bits, LSB-first per field: D:7 then F:8, where F carries
  the function in bits 0-5 and the rolling counter in bits 6-7. Bit 0 is
  780us mark + 780us space; bit 1 is 780us mark + 1560us space.
- Single 780us trailer mark, then a ~104ms frame period.
- NO checksum of any kind.

The F byte is really two fields: the button (**low 6 bits**) and a
ROLLING COUNTER in the **high 2 bits**, which are the last two bits on
the wire. The counter advances on every press -- and on every second
frame while a button is held. The fan tracks the last counter it
accepted and rejects a frame that reuses it: true anti-replay rotation,
and the root cause of the ~33% replay-reliability symptom (GH #33,
Esp32-zapper). HAIR therefore treats device+function as identity and
the counter as press state, exactly like an RC-5 toggle: it rides in
``decoded_extras`` and the transmit path advances it after every
logical press.

WHERE THE COUNTER ACTUALLY LIVES, corrected 2026-09-16. Until then this
module read the counter from F's LOW two bits, which are wire bits 7
and 8, immediately after the seven device bits. That was wrong, and
three independent lines of evidence say so:

- The frame layout is thirteen payload bits and then TWO toggle bits
  at the end, each under a bitspec of opposite polarity, so a toggle of
  0 goes out as the wire pair ``1,0``. The rotating bits are wire bits
  13 and 14, the last two.
- Upstream's own Dyson enum freezes three codes for one power button
  (0x00, 0x01, 0x02) that differ only in the last two bits of an
  MSB-first byte, which are the same two wire bits.
- Reading a corpus of rendered AM07 commands under the corrected split
  gives the same counter value on every one, as it must when they are
  all rendered with the toggle at zero; under the old split it
  scattered across all four values, which is the signature of a counter
  field eating two function bits.

Recomputed under the corrected split, with device 9 throughout:

    button        wire (15 bits)   F byte   old reading    corrected
    PowerToggle   100100000000010   0x40     0x10, ctr 0    0x00, ctr 1
    FanSpeedUp    100100001010110   0x6A     0x1A, ctr 2    0x2A, ctr 1
    FanSpeedDown  100100011111110   0x7F     0x1F, ctr 3    0x3F, ctr 1
    Oscillate     100100010101010   0x55     0x15, ctr 1    0x15, ctr 1
    TimerUp       100100001111010   0x5E     0x17, ctr 2    0x1E, ctr 1
    TimerDown     100100011001110   0x73     0x1C, ctr 3    0x33, ctr 1

The corrected PowerToggle function is 0, which is what this package's
own round-trip test already called AM04/07/09 power.

THE VALUES OF EVERY STORED DYSON ROW THEREFORE MOVED, and a stored row
transmits from its decoded triple, so a migration recomputes them
through the F byte rather than leaving them to re-encode as a different
button. ``storage._backfill_dyson_counter_split`` does it, gated on the
store's minor version because the remap is a bijection and not
idempotent.

WHETHER THE COUNTER ROTATES OVER FOUR VALUES IS STILL OPEN. The
definition can only ever emit the pairs ``10`` and ``01``, because its
two toggle bits are one field rendered twice with opposite polarity,
and upstream's enum shows 00, 01 and 10 but never 11. Nothing available
settles whether the fourth value is legal, so the mod-4 advance in the
transmit path is deliberately unchanged; the GH #33 hardware capture
has to answer it before that moves.

Device values seen in the wild: 5 (AM02/AM03 towers), 9 (AM04/AM07/
AM09 -- the ``0b1001000`` preamble of upstream's encoder is this same
value in MSB form). Purifier-family device codes exist but are
undocumented; the decoder reads whatever 7-bit value arrives rather
than pinning a known list.

Upstream ``infrared_protocols`` ships an encode-only DysonCoolCommand
(v7.3.0+) whose enum freezes three counter values of the same power
button as distinct codes; it has no decoder and no counter handling,
so this local class serves both directions and is NOT registered with
an upstream fallback (revisit if upstream grows a real decoder).

Protocol research: JP1 forum (3FG/The Robman), the 2013 AM02
reverse-engineering writeup, and upstream PR #60 -- survey logged in
docs/internal/research/dyson-ir-protocol.md.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Self, override

from . import decode_frames_majority, is_close, split_frames, stamp_census
from ._base import Command

_UNIT_US = 780
_LEADER_MARK_US = 3 * _UNIT_US  # 2340
_LEADER_SPACE_US = _UNIT_US
_BIT_MARK_US = _UNIT_US
_ZERO_SPACE_US = _UNIT_US       # 780
_ONE_SPACE_US = 2 * _UNIT_US    # 1560
# The two bit spaces are one unit apart; the default 0.4 band would
# let a ~1000us space match both nominals. 0.3 keeps them disjoint.
_TOLERANCE = 0.3

_DATA_BITS = 15  # D:7 + F:8 (F = function in bits 0-5, counter in 6-7)
# leader pair (2) + 15 bit pairs (30) + trailer mark (1)
_MIN_FRAME_LEN = 2 + _DATA_BITS * 2 + 1
# Largest intra-frame space is 1560us; the inter-frame period is
# ~104ms. Any space of 8ms+ is a frame boundary, never a bit.
_FRAME_GAP_US = 8000


class DysonCommand(Command):
    """Dyson IR command with decode support."""

    #: The frame gap this protocol splits captures at, exposed so the
    #: coverage accounting in ``protocol_decode`` can count frames the
    #: way this decoder does. A generic gap is wrong: RCA's header space
    #: is 4000us and would shred at a 4000us split.
    FRAME_GAP_US = _FRAME_GAP_US

    device: int
    function: int
    counter: int

    def __init__(
        self,
        *,
        device: int,
        function: int,
        counter: int = 0,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Dyson IR command.

        :param device: fan family code D (7 bits; 5=AM02/03, 9=AM04/07/09)
        :param function: button code (6 bits)
        :param counter: mod-4 rolling press counter (2 bits; press
            state, not identity -- the fan rejects a reused value)
        """
        super().__init__(modulation=modulation)
        self.device = device & 0x7F
        self.function = function & 0x3F
        self.counter = counter & 0x3

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Dyson command.

        Positive values are mark (high) durations in microseconds;
        negative values are space (low) durations. One frame: leader,
        fifteen LSB-first bits (D:7 then F:8 with the function in F's
        low six bits and the counter in its high two, which are the last
        two bits on the wire), trailer mark.
        """
        f_byte = ((self.counter & 0x3) << 6) | (self.function & 0x3F)
        timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        for field, width in ((self.device, 7), (f_byte, 8)):
            for bit_index in range(width):  # LSB first
                bit = (field >> bit_index) & 1
                timings.append(_BIT_MARK_US)
                timings.append(
                    -_ONE_SPACE_US if bit else -_ZERO_SPACE_US
                )
        timings.append(_BIT_MARK_US)  # trailer
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a DysonCommand, or None.

        The capture is split into frames at the ~104ms period and each
        frame decodes independently. A held button re-sends the frame
        with the counter advancing every second frame, so the majority
        vote runs on the full (device, function, counter) tuple; ties
        resolve to the earliest frame, and either way the device and
        function -- the identity half -- are unanimous.
        """
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, cls._decode_frame)
        if result is None:
            return None
        (device, function, counter), votes = result
        # The vote count is discarded for repeat_count on purpose (a
        # Dyson counter advances per frame, so frames are not
        # dittos), but it is still what this decode explained.
        return stamp_census(
            cls(device=device, function=function, counter=counter),
            votes,
        )

    @classmethod
    def _decode_frame(
        cls, frame: Sequence[int]
    ) -> tuple[int, int, int] | None:
        """Decode one frame to (device, function, counter), or None.

        Leader, fifteen classified bits, trailer mark; any timing
        outside tolerance rejects the frame. The protocol has no
        checksum, so this strictness is the only thing keeping a
        foreign frame from decoding as Dyson.
        """
        if len(frame) < _MIN_FRAME_LEN:
            return None
        if not is_close(frame[0], _LEADER_MARK_US, _TOLERANCE):
            return None
        if not is_close(-frame[1], _LEADER_SPACE_US, _TOLERANCE):
            return None

        bits: list[int] = []
        for i in range(_DATA_BITS):
            mark = frame[2 + 2 * i]
            space = -frame[3 + 2 * i]
            if not is_close(mark, _BIT_MARK_US, _TOLERANCE):
                return None
            bit = cls._classify_space(space)
            if bit is None:
                return None
            bits.append(bit)

        trailer = frame[2 + 2 * _DATA_BITS]
        if not is_close(trailer, _BIT_MARK_US, _TOLERANCE):
            return None
        # Only the inter-frame gap (or a truncated capture) may follow
        # the trailer; a further mark means split_frames failed to
        # separate something -- reject to be safe.
        if any(value_after > 0 for value_after in frame[_MIN_FRAME_LEN:]):
            return None

        device = 0
        for bit_index in range(7):  # LSB first
            device |= bits[bit_index] << bit_index
        f_byte = 0
        for bit_index in range(8):
            f_byte |= bits[7 + bit_index] << bit_index
        return (device, f_byte & 0x3F, (f_byte >> 6) & 0x3)

    @staticmethod
    def _classify_space(space_us: int) -> int | None:
        """Classify a bit space as 0 (780us) or 1 (1560us), or None."""
        if is_close(space_us, _ZERO_SPACE_US, _TOLERANCE):
            return 0
        if is_close(space_us, _ONE_SPACE_US, _TOLERANCE):
            return 1
        return None
