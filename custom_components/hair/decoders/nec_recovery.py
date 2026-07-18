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

    data = [0, 0, 0, 0]
    for bit_index, bit in enumerate(bits):
        data[bit_index // 8] |= bit << (bit_index % 8)

    # NEC's built-in integrity check: the fourth byte is the bitwise
    # inverse of the command byte. Without it, no salvage.
    if data[2] ^ data[3] != 0xFF:
        return None

    address = data[0] | (data[1] << 8)
    return (address, data[2])
