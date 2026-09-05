"""NEC capture recovery: leader-seek and checksum-backed salvage.

These are NOT a decoder. The upstream ``NECCommand.from_raw_timings``
remains the only strict NEC decoder HAIR uses. This module recovers two
classes of real-world capture that the strict decoder rightly rejects,
without loosening it:

Leader-seek (v0.6.1, bench Remotes 9-12): real receivers sometimes
deliver a capture that starts with junk ahead of the NEC main frame,
typically the tail of a previous press's repeat chatter (a 9000/2250
repeat marker) or a partial burst. The strict decoder requires the
capture to OPEN with the 9000/4500 main leader, so it gives up. The
seek scans forward to the first true main leader and hands the strict
decoder the capture from there. Trailing repeat markers are untouched;
upstream counts those as dittos.

Checksum salvage (v0.6.1, blalor's Previous Track case): a capture can
be one jittery pulse away from valid, e.g. a single data space
measuring ~815us, in the dead zone between the two legal NEC spaces
(~562 and ~1687), while every other pulse is in bounds and the frame's
own integrity check holds. The salvage re-classifies data pulses by
midpoint inside wide sanity bounds and accepts the result ONLY if
NEC's built-in check passes: command XOR command_inverse == 0xFF.
Extended NEC addresses are allowed (no address-inverse requirement),
matching the upstream decoder's behavior. The checksum is what makes
the leniency honest -- the same philosophy as the Sony decoder's
midpoint classification, except NEC hands us a checksum where Sony
needed majority voting.

License note: written from the public NEC format description only, no
third-party decoder code consulted, per the package licensing rule.
"""

from __future__ import annotations

# Main-frame leader nominals (microseconds) with the library's usual
# 40% tolerance. The repeat-marker space (2250us nominal, upper bound
# 3150 at +40%) stays clear of the leader-space lower bound (2700), so
# a repeat marker can never be mistaken for a main leader.
_LEADER_MARK = 9000
_LEADER_SPACE = 4500
_TOLERANCE = 0.4

# Sanity bounds for salvage classification. Deliberately wide: the
# whole point is admitting pulses outside the strict windows, with the
# checksum as the gate. A data mark is nominally 562us; a data space is
# 562 (zero) or 1687 (one). The midpoint between the two legal spaces
# separates bit values.
_MARK_MIN = 200
_MARK_MAX = 1200
_SPACE_MIN = 250
_SPACE_MAX = 2400
_SPACE_MIDPOINT = 1125

_DATA_BITS = 32

# The NEC repeat marker: 9000us mark, 2250us space, one short end pulse.
# It is the only thing that may legally follow a main frame's trailer,
# and telling it apart from more data is what lets the end-of-frame
# check below reject a longer frame without rejecting a held button.
_REPEAT_SPACE = 2250

# What separates one NEC frame from the next. The main frame is padded
# to a 110ms period and the largest space inside a frame is the 4500us
# leader, so any space above this is between frames rather than in one.
FRAME_GAP_US = 8000


def _within(value: int, nominal: int) -> bool:
    margin = nominal * _TOLERANCE
    return nominal - margin <= value <= nominal + margin


def seek_main_leader(timings: list[int]) -> list[int]:
    """Return ``timings`` from the first NEC main leader onward.

    Scans for the first mark/space pair matching the 9000/4500 main
    leader and returns the capture sliced to start there. When the
    capture already starts on the leader, or no leader exists anywhere,
    the input is returned unchanged (the strict decoder then judges it
    exactly as it would have before this pass existed).
    """
    for index in range(len(timings) - 1):
        mark = timings[index]
        space = -timings[index + 1]
        if mark > 0 and _within(mark, _LEADER_MARK) and _within(
            space, _LEADER_SPACE
        ):
            return timings if index == 0 else timings[index:]
    return timings


def is_repeat_marker(frame: list[int]) -> bool:
    """Is this frame the NEC 9000/2250/pulse repeat marker?

    A held NEC button sends the main frame once and then repeats this
    three-element shape. It carries no payload, so it is not data the
    decode has to explain -- but it IS part of the capture, and the
    coverage accounting has to count it as accounted for rather than as
    a frame nobody read.
    """
    if len(frame) != 3:
        return False
    return (
        frame[0] > 0
        and _within(frame[0], _LEADER_MARK)
        and _within(-frame[1], _REPEAT_SPACE)
        and _MARK_MIN <= frame[2] <= _MARK_MAX
    )


def _tail_is_spaces_and_repeats(rest: list[int]) -> bool:
    """Is everything after the trailer mark idle time or repeat markers?

    Marks are what matter. A space of any length is idle time between
    frames; a mark is more signal, and the only signal allowed to
    follow a complete NEC frame is a repeat marker. A capture cut
    partway through a trailing marker is accepted -- captures truncate
    routinely, and the frame this function is judging already ended.
    """
    index = 0
    while index < len(rest):
        value = rest[index]
        if value < 0:
            index += 1
            continue
        if not _within(value, _LEADER_MARK):
            return False
        if index + 1 >= len(rest):
            return True
        if not _within(-rest[index + 1], _REPEAT_SPACE):
            return False
        if index + 2 >= len(rest):
            return True
        if not _MARK_MIN <= rest[index + 2] <= _MARK_MAX:
            return False
        index += 3
    return True


def salvaged_frame_census(timings: list[int]) -> tuple[int, int]:
    """``(frames_total, frames_explained)`` for a salvaged NEC capture.

    The salvage reads ONE main frame. That frame is explained, and so
    is every repeat marker after it; anything else in the capture is a
    frame nobody accounted for and counts against the verdict.
    """
    from . import split_frames

    frames = split_frames(timings, FRAME_GAP_US)
    if not frames:
        return (0, 0)
    explained = 1 + sum(1 for frame in frames[1:] if is_repeat_marker(frame))
    return (len(frames), explained)


def salvage_decode(timings: list[int]) -> tuple[int, int] | None:
    """Midpoint-decode one NEC frame, gated on the protocol checksum.

    Expects a capture that opens on a main leader (run
    :func:`seek_main_leader` first). Returns ``(address, command)``
    with the address in the same 16-bit little-endian packing the
    upstream decoder reports, or ``None`` when the frame cannot be
    salvaged honestly.
    """
    if len(timings) < 2 + 2 * _DATA_BITS:
        return None
    if not (timings[0] > 0 and _within(timings[0], _LEADER_MARK)):
        return None
    if not _within(-timings[1], _LEADER_SPACE):
        return None

    bits: list[int] = []
    index = 2
    for _ in range(_DATA_BITS):
        if index + 1 >= len(timings):
            return None
        mark = timings[index]
        space = -timings[index + 1]
        if not _MARK_MIN <= mark <= _MARK_MAX:
            return None
        if not _SPACE_MIN <= space <= _SPACE_MAX:
            return None
        bits.append(1 if space > _SPACE_MIDPOINT else 0)
        index += 2

    # THE FRAME HAS TO END HERE (GH #134). Without this the 32 pairs
    # above are only a PREFIX: a 68-bit air conditioner state frame
    # offers a perfectly good first 32 bits, and one in 256 of them
    # satisfies the complement check by chance, which is a fake NEC
    # identity minted from a state blob and then re-encoded over it.
    # The strict local decoders all refuse a frame that keeps going
    # (samsung.py, rca.py); the salvage was the one lenient reader that
    # never looked, and leniency without a boundary is not leniency, it
    # is guessing.
    #
    # The trailer mark has no upper bound, for the reason samsung.py
    # gives at its own end pulse: an emitter replaying the packet can
    # fuse the trailer into whatever follows, and once fusion is
    # possible the length carries no information. The bound that
    # matters is what comes AFTER it.
    if index >= len(timings):
        return None
    if timings[index] < _MARK_MIN:
        return None
    if not _tail_is_spaces_and_repeats(timings[index + 1:]):
        return None

    data = [0, 0, 0, 0]
    for bit_index, bit in enumerate(bits):
        data[bit_index // 8] |= bit << (bit_index % 8)

    # NEC's built-in integrity check: the fourth byte is the bitwise
    # inverse of the command byte. Without it, no salvage.
    if data[2] ^ data[3] != 0xFF:
        return None

    address = data[0] | (data[1] << 8)
    return (address, data[2])
