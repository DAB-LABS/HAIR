"""Chamberlain Security+ 1.0: reading the two half-words of a press.

A Security+ 1.0 remote (Chamberlain, LiftMaster and Craftsman garage
openers with a red, orange, purple, brown or blue learn button, 1997 to
2014) sends a word of 40 three-level symbols as two frames of a sync
symbol and 20 data symbols, about 58 ms apart, and repeats the pair at
least four times per press. Each symbol is a space then a mark, about
2 ms together; the mark is about a quarter, a half or three quarters of
it (symbols 0, 1 and 2). The sync is a 0 on the first frame and a 2 on
the second.

HAIR READS, NEVER SENDS. The word carries a fixed code (the remote and
its button) and a rolling code that rises with every press. HAIR keys
the row on the fixed code and never sends the word (``rf_family``'s
rolling guard).

WHERE THE HALVES MEET. A frame's fingerprint is its own, so a capture or
a burst votes on one half at a time, and the two halves of one press
have to be put back together:

- ``pair_in_capture``: a capture that holds the whole press (a receiver
  whose idle is longer than the 58 ms gap) is read half by half before
  the vote, and its two halves become one word;
- ``HalfHolder``: a receiver that ends a capture at every gap delivers
  each half as its own voted burst; the first waits for the other.

Either way the word goes on as ONE press, its frame the first half, the
gap, then the second half, so the stored row holds the whole word.

Written from the published description (US patent 6,980,655 and public
write-ups); no code, tables or vectors are taken from any other project.
"""
from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from statistics import median
from typing import Any

FAMILY = "secplus_v1"
DATA_SYMBOLS = 20
# The silence after each frame, about 58 ms. Anything this long or more
# ends a frame.
_FRAME_GAP_MIN_US = 10_000
_WORD_GAP_US = 58_000
# A symbol's mark against its own quarter-period unit: 1, 2 or 3 units,
# within this much.
_MARK_TOLERANCE = 0.35
# A symbol's space plus mark against the frame's own period.
_PERIOD_TOLERANCE = 0.30
# The unit the frame's period must give (500 us on the air).
_UNIT_RANGE_US = (250, 1_000)
# How long the first voted half of a press waits for the other.
HALF_WAIT_S = 1.0


@dataclass(frozen=True)
class Half:
    """One frame of a word: which one (1 or 2) and its 20 data symbols."""

    frame_no: int
    symbols: tuple[int, ...]


def _strip(edges: list[int] | tuple[int, ...]) -> list[int]:
    """A frame's widths from its first mark, the gap after it dropped.

    Accepts HAIR's signed convention or bare widths, mark first.
    """
    values = [abs(int(v)) for v in edges]
    if values and values[-1] >= _FRAME_GAP_MIN_US:
        values = values[:-1]
    return values


def read_half(edges: list[int] | tuple[int, ...] | None) -> Half | None:
    """A Security+ 1.0 half-word, or None for anything else.

    ``edges`` is one frame from its sync mark (a piece's own edges, not
    its two-level body: the sync is the third mark width). The unit comes
    from the frame itself.
    """
    if not edges:
        return None
    values = _strip(edges)
    if len(values) != 1 + 2 * DATA_SYMBOLS:
        return None
    sync = values[0]
    pairs = [(values[1 + 2 * i], values[2 + 2 * i]) for i in range(DATA_SYMBOLS)]
    period = median(space + mark for space, mark in pairs)
    unit = period / 4
    if not _UNIT_RANGE_US[0] <= unit <= _UNIT_RANGE_US[1]:
        return None
    symbols = []
    for space, mark in pairs:
        if abs(space + mark - period) > _PERIOD_TOLERANCE * period:
            return None
        symbol = _symbol(mark, unit)
        if symbol is None:
            return None
        symbols.append(symbol)
    sync_symbol = _symbol(sync, unit)
    if sync_symbol == 0:
        return Half(1, tuple(symbols))
    if sync_symbol == 2:
        return Half(2, tuple(symbols))
    return None


def _symbol(mark: float, unit: float) -> int | None:
    units = mark / unit
    nearest = round(units)
    if not 1 <= nearest <= 3 or abs(units - nearest) > _MARK_TOLERANCE:
        return None
    return nearest - 1


def read_word(frame: list[int] | tuple[int, ...] | None) -> tuple[Half, Half] | None:
    """A whole word as HAIR stores it (first half, gap, second half), or
    None."""
    if not frame:
        return None
    values = [abs(int(v)) for v in frame]
    cuts = [i for i, v in enumerate(values) if i % 2 == 1 and v >= _FRAME_GAP_MIN_US]
    if not cuts:
        return None
    first = read_half(values[: cuts[0]])
    second = read_half(values[cuts[0] + 1:])
    if first is None or second is None or (first.frame_no, second.frame_no) != (1, 2):
        return None
    return first, second


def word_frame(first: list[int], second: list[int], gap_us: int | None) -> list[int]:
    """One stored frame for a word: the first half, the gap, the second
    half and its own gap, in HAIR's signed convention."""
    one = _strip(first)
    two = _strip(second)
    gap = gap_us if gap_us and gap_us >= _FRAME_GAP_MIN_US else _WORD_GAP_US
    signed = [v if i % 2 == 0 else -v for i, v in enumerate(one)]
    signed.append(-gap)
    signed.extend(v if i % 2 == 0 else -v for i, v in enumerate(two))
    signed.append(-gap)
    return signed


def _combined(a: str, b: str) -> str:
    return hashlib.sha256(f"{a}|{b}".encode()).hexdigest()[: max(len(a), 8)]


def join(first: Any, second: Any) -> Any:
    """Two voted halves (``rf_frames.RfCapture``) as one voted word.

    The word's fingerprint and hash stand for both halves; its rows are
    keyed on the decoded fixed code anyway (``rf_family``).
    """
    frame = word_frame(first.frame, second.frame, first.gap_us)
    return dataclasses.replace(
        first,
        frame=frame,
        fingerprint=_combined(first.fingerprint, second.fingerprint),
        frame_hash=_combined(first.frame_hash, second.frame_hash),
        body_edges=first.body_edges + second.body_edges,
        votes=min(first.votes, second.votes),
        gap_us=second.gap_us,
        gap_source=second.gap_source,
        sl_pattern=first.sl_pattern + second.sl_pattern,
    )


def pair_in_capture(
    bodied: list[tuple[Any, Any]], vote: Callable[[list[tuple[Any, Any]]], Any],
    min_frames: int,
) -> Any | None:
    """The word of a capture that holds a whole press, or None.

    Each half votes on its own (``min_frames`` agreeing frames). When a
    half can't (a weak press can bring only one clean copy of each), its
    best copy still counts if the two halves read as a word (``decode``:
    a rolling value of 2 ** 31 or more is not one). Otherwise the
    capture goes on as any other.
    """
    halves: dict[int, list[tuple[Any, Any]]] = {1: [], 2: []}
    for piece, parts in bodied:
        half = read_half(piece.edges)
        if half is not None:
            halves[half.frame_no].append((piece, parts))
    if not halves[1] or not halves[2]:
        return None
    if len(halves[1]) >= min_frames and len(halves[2]) >= min_frames:
        first, second = vote(halves[1]), vote(halves[2])
        if first is not None and second is not None:
            return join(first, second)
    first, second = vote(halves[1], 1), vote(halves[2], 1)
    if first is None or second is None:
        return None
    one, two = read_half(first.frame), read_half(second.frame)
    if one is None or two is None or decode(one, two) is None:
        return None
    return join(first, second)


class HalfHolder:
    """Per receiver: a voted half waiting for the other half of its press.

    ``offer`` takes a voted capture and what came with it. It returns
    ``(word, word_extra, None)`` when the capture completes a word (the
    extra is the first half's), ``(None, None, None)`` when it is a half
    now held, and ``(None, None, capture)`` when it is no half at all (it
    goes on as any other). A held half that waited too long, or that a
    newer copy of the same half replaced, goes to ``on_dropped``.
    """

    def __init__(self, on_dropped: Callable[[str, Any], None]) -> None:
        self._held: dict[str, tuple[int, Any, Any, float]] = {}
        self._on_dropped = on_dropped

    def offer(
        self, receiver: str, analysis: Any, extra: Any, now: float
    ) -> tuple[Any | None, Any | None, Any | None]:
        """``(word, word_extra, passthrough)``: see the class docstring."""
        half = read_half(analysis.frame)
        if half is None:
            return None, None, analysis
        self.expire(now)
        held = self._held.pop(receiver, None)
        if held is not None and held[0] != half.frame_no:
            other_no, other, other_extra, _at = held
            first, second = (other, analysis) if other_no == 1 else (analysis, other)
            first_extra = other_extra if other_no == 1 else extra
            return join(first, second), first_extra, None
        if held is not None:
            # The same half again before its partner: the newer one waits.
            self._on_dropped(receiver, held[1])
        self._held[receiver] = (half.frame_no, analysis, extra, now)
        return None, None, None

    def expire(self, now: float) -> None:
        for receiver, (_no, analysis, _extra, at) in list(self._held.items()):
            if now - at > HALF_WAIT_S:
                del self._held[receiver]
                self._on_dropped(receiver, analysis)

    def forget(self, receiver: str) -> None:
        self._held.pop(receiver, None)


_ROLLING_LIMIT = 1 << 31


def decode(first: Half, second: Half) -> tuple[int, int] | None:
    """The word's fixed code and rolling code, or None.

    Each frame carries ten pairs of symbols: a rolling digit, then a fixed
    digit sent as (fixed + running sum) mod 3, where the running sum
    starts at 0 on each frame and adds every rolling digit and every
    fixed digit (not the symbol sent) as it goes. Both codes are read most
    significant digit first, base 3, frame 1 then frame 2. The rolling
    code is sent with its 32 bits in reverse order and its top bit
    cleared, so a value of 2 ** 31 or more is not a word.

    Where the fixed code's third digit from the bottom is 2, the lowest
    digit names the button and the digits above the third name the
    remote, so ``rf_family`` gives the remote one card with a row per
    button. Any other layout isn't known, so the whole fixed code keys a
    card and a row of its own, one per button.
    """
    rolling_digits: list[int] = []
    fixed_digits: list[int] = []
    for half in (first, second):
        running = 0
        for i in range(0, DATA_SYMBOLS, 2):
            rolling = half.symbols[i]
            rolling_digits.append(rolling)
            running += rolling
            fixed = (half.symbols[i + 1] - running) % 3
            fixed_digits.append(fixed)
            running += fixed
    mirrored = 0
    for digit in rolling_digits:
        mirrored = mirrored * 3 + digit
    if mirrored >= _ROLLING_LIMIT:
        return None
    rolling_code = int(f"{mirrored:032b}"[::-1], 2)
    fixed_code = 0
    for digit in fixed_digits:
        fixed_code = fixed_code * 3 + digit
    return fixed_code, rolling_code
