"""Apple remote: an NEC1 frame whose last two bytes are not a checksum.

An Apple remote sends a textbook NEC1 frame -- 9 ms leader, 4.5 ms
leader space, 32 LSB-first data bits, one trailer mark -- and then
spends the last two bytes on something NEC does not have a slot for, so
the strict decoder rejects every press. The wire bytes are::

    byte1 0xEE  byte2 0x87   -> HAIR address 0x87EE
    byte3 = (command << 1) | parity
    byte4 = the remote's pairing id

There is no command complement. What stands in for it is a single
parity bit in byte3's low position, chosen so that
**popcount(byte3) + popcount(byte4) is odd**.

WHY THE PARITY RULE IS SAFE AGAINST STRICT NEC, as a proof rather than
an observation. A complement-valid NEC frame has byte4 = ~byte3, and
for any byte ``popcount(x) + popcount(~x) == 8``, which is even. The
rule here demands odd. So no frame can satisfy both, whatever the probe
order, and this class can never take a frame the strict decoder would
have claimed. That is what makes the gate affordable.

WHAT THE GATE ACTUALLY IS: a 16-bit address pinned to 0x87EE plus the
parity bit, seventeen bits of structure, on top of the NEC1 frame shape
and an exact 32-bit termination. A random NEC1-shaped frame reaches a
false Apple identity at about one in 131,072.

EVIDENCE, as measured counts. The rule was read off the frame layout
and then measured over a corpus of rendered commands. It holds on all
**432** frames at address 0x87EE and fails on **33** frames at that
same address, which are not remote presses. It fails on every frame at
the neighbouring 0x87E5 and 0x87E0, which belong to other Apple
products rather than to the remote, so the address pin and the parity
bit refuse those independently. Exactly one frame at 0x87EE is
complement-valid: its parity is even, so this class refuses it and the
strict decoder claims it, which is the proof above with a live case.

Two pairing ids are represented, 0x01 alongside the 0x2E and 0x37 of
``tests/fixtures/adapters/flipper_parsed_Apple_TV_Gen3_v2.ir``, so what
is exercised is the two-byte rule rather than a one-byte proxy for it.
The command split is confirmed across both on six buttons that appear
in each: Menu 0x01, Up 0x05, Down 0x06, Left 0x04, Right 0x03 and
Reboot 0x0C, read from different byte3 values because the parity
differs with the pairing id.

THE PAIRING ID IS IDENTITY and rides the fingerprint suffix ``:p<xx>``.
It is on the wire in every frame, it never changes between presses, and
a paired Apple TV acts on it. The honest cost, stated because a review
argued the other side: two remotes paired to two boxes produce two
identities for one button, and re-pairing a remote produces a new one.
Both of those are two different signals on the air, which is what an
identity is for, but a person who re-pairs will have to re-point any
trigger built on the old id.

License rule (package docstring): written from the public NEC frame
description plus values derived here from the frame layout and from
HAIR's own fixture. No third-party decoder implementation was consulted.
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
_REPEAT_SPACE_US = 2250
_MODULATION_HZ = 38000
_TOLERANCE = 0.4
_MIN_MARK_US = 200

_DATA_BITS = 32
_FRAME_GAP_US = 8000

# The NEC1 main frame is padded to ~108 ms and a ditto to ~96 ms after
# it. Used only to place encoded repeats; never a decode constraint.
_INITIAL_GAP_US = 41_000
_REPEAT_GAP_US = 96_000

#: The only address an Apple remote sends. Pinning it is most of the
#: gate: the codeset's other two addresses (0x87E5, 0x87E0) belong to
#: different Apple products and must not mint an APPLE identity.
APPLE_ADDRESS = 0x87EE

_COMMAND_MASK = 0x7F
_PAIR_MASK = 0xFF


def _parity_holds(byte3: int, byte4: int) -> bool:
    """The integrity rule: the two bytes carry an odd number of ones."""
    return (bin(byte3 & 0xFF).count("1") + bin(byte4 & 0xFF).count("1")) % 2 == 1


def _byte3_for(command: int, pair_id: int) -> int:
    """``(command << 1) | parity``, parity derived, never stored.

    Derived on encode so a stored identity cannot carry a stale or
    hand-edited parity bit into a transmitted frame.
    """
    body = (command & _COMMAND_MASK) << 1
    return body if _parity_holds(body, pair_id) else body | 1


def _decode_frame(frame: Sequence[int]) -> tuple[int, int] | None:
    """One frame to ``(command, pair_id)``, or None.

    Gates in order: NEC1 leader, exactly thirty-two bits, the frame ends
    after them, the address is Apple's, the parity rule holds.
    """
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

    # THE FRAME HAS TO END HERE. Without this the thirty-two pairs above
    # are only a prefix, and a long state frame offers a perfectly good
    # first thirty-two bits (GH #134). The trailer mark has no upper
    # bound because an emitter can fuse it into what follows; what is
    # bounded is what comes after it.
    if index >= len(frame) or frame[index] < _MIN_MARK_US:
        return None
    rest = list(frame[index + 1:])
    position = 0
    while position < len(rest):
        value = rest[position]
        if value < 0:
            position += 1
            continue
        if not is_close(value, _LEADER_MARK_US, _TOLERANCE):
            return None
        if position + 1 >= len(rest):
            break
        if not is_close(-rest[position + 1], _REPEAT_SPACE_US, _TOLERANCE):
            return None
        if position + 2 >= len(rest):
            break
        if not _MIN_MARK_US <= rest[position + 2] <= 1200:
            return None
        position += 3

    if data[0] | (data[1] << 8) != APPLE_ADDRESS:
        return None
    if not _parity_holds(data[2], data[3]):
        return None
    return (data[2] >> 1, data[3])


class AppleCommand(Command):
    """Apple remote IR command with decode support."""

    #: The frame gap this protocol splits captures at, exposed so the
    #: coverage accounting in ``protocol_decode`` can count frames the
    #: way this decoder does.
    FRAME_GAP_US = _FRAME_GAP_US

    address: int
    command: int
    pair_id: int

    def __init__(
        self,
        *,
        command: int,
        pair_id: int,
        address: int = APPLE_ADDRESS,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Apple remote command.

        :param command: 7-bit button code (byte3 without its parity bit)
        :param pair_id: the remote's pairing id, byte4 verbatim
        :param address: pinned to 0x87EE; any other value is refused
        """
        if address != APPLE_ADDRESS:
            raise ValueError("Apple address must be 0x87EE")
        if not 0 <= command <= _COMMAND_MASK:
            raise ValueError("Apple command must be in range 0x00..0x7F")
        if not 0 <= pair_id <= _PAIR_MASK:
            raise ValueError("Apple pair_id must be in range 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.pair_id = pair_id

    @property
    def byte3(self) -> int:
        """The third wire byte: the command with its parity bit."""
        return _byte3_for(self.command, self.pair_id)

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings: NEC1 frame, then real dittos for repeats.

        ``repeat_count`` emits 9000/-2250/562 repeat markers, NOT copies
        of the whole frame. The distinction is what makes the ditto knob
        honest for this family: a duplicated frame is a second press,
        and a marker is the same press still held.
        """
        data = [
            self.address & 0xFF,
            (self.address >> 8) & 0xFF,
            self.byte3,
            self.pair_id & 0xFF,
        ]
        timings: list[int] = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        for byte in data:
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
        """Decode raw IR timings into an AppleCommand, or None."""
        frames = split_frames(timings, _FRAME_GAP_US)
        result = decode_frames_majority(frames, _decode_frame)
        if result is None:
            return None
        (command, pair_id), votes = result
        markers = sum(1 for frame in frames if is_repeat_marker(list(frame)))
        return stamp_census(
            cls(command=command, pair_id=pair_id, repeat_count=markers),
            votes + markers,
        )
