"""A built capture whose frames genuinely disagree.

0.14.1 A1 stood one of the Dreo wig's two flagged captures down: Speed
Down is a Symphony capture the decoder reads whole, so its frames
differing is the protocol working rather than a bad capture, and it no
longer reaches the work list. The field data now supplies ONE open row.

Several tests are about what happens to two of them: a pair being
settled in one answer, a retire sweep releasing an untouched twin, two
noisy captures staying two separate cards. Those need a second open row,
so they build one here rather than borrowing a second accident that no
longer exists.

What this builds is the case A1 deliberately leaves flagged: a
pulse-width capture, frames that differ, and no repeat-voting protocol
willing to accept it. It combs as ``frame-disagreement`` on its own.
"""
from __future__ import annotations

MARK_SHORT = 0x0010
MARK_LONG = 0x002E
SPACE = 0x0010
#: A repeat gap in the Dreo's own idiom, well under PRONTO_GAP_THRESHOLD
#: so the frame splitter has to find it by shape rather than by a cut.
GAP = 0x0140
TRAILER = 0x09C4


def disagreeing_capture(patterns: list[str]) -> str:
    """A Pronto code carrying one frame per pattern, gaps between them.

    Each character of a pattern is one bit, written as a long or short
    mark against a constant space.
    """
    pairs: list[tuple[int, int]] = []
    for index, bits in enumerate(patterns):
        closer = TRAILER if index == len(patterns) - 1 else GAP
        last = len(bits) - 1
        for position, bit in enumerate(bits):
            mark = MARK_LONG if bit == "1" else MARK_SHORT
            pairs.append((mark, closer if position == last else SPACE))
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


#: Four frames, two of which differ from the other two in one bit each.
#: No majority survives, so the check has nothing to defer to.
SECOND_OPEN_ROW = disagreeing_capture([
    "110100100101",
    "110100100100",
    "110100100101",
    "110100100110",
])
