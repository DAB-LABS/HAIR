"""Radio frequency captures: frames, bodies, identity and the vote.

A radio remote says everything several times. One press is a burst of
identical frames, and a receiver reports them either whole (an RM4 pro
capture window hands back the burst in one packet) or one frame per
capture (a receiver whose idle ends a capture at every gap). Either way
the unit of identity is the FRAME, and a press counts only when its
frames agree.

THE PIECES OF A CAPTURE. ``canonical_edges`` drops the capture's last
value when it is a space, so whatever a receiver appends after the last
pulse (its own idle, a device's fixed tail) never reaches anything here.
The remaining edges are cut at every space long enough to be an
inter-frame gap, by the rule ``identity.first_frame`` uses: three times
the 90th-percentile space. Each piece keeps the gap that ended it as its
last edge.

WHOLE FRAMES. A piece is a frame only if it has a BODY: its marks form
at least two width levels and so do its spaces. Receiver noise repeats
itself only in pieces of a handful of edges with no body, so a body is
what separates a press from noise (measured on the bench: about 12,000
noise captures an hour, none with a body ever repeating). Of the pieces
with a body, the frames are those of the most common edge count. That one
rule drops the partial frames a capture starts and ends with, and a frame
a receiver damaged mid-capture (the RM4 pro stretches one duration every
250, so one frame per packet splits in two), with no constant to tune.

HEADER, BODY, TRAILER. Every fixed-code family HAIR targets has exactly
two data widths per polarity. The body is the edges whose width level is
one of the two most populated levels of their polarity; the header and
the trailer are the runs at either end outside them (a leading sync
pair, a trailing sync mark, the gap).

IDENTITY. The fingerprint is the body's two-level labels
(``identity._level_labels``, marks and spaces apart) with the body's
edge count and the header shape. The frame hash, the discriminator, uses
the body's multi-level labels (``identity._value_levels``) instead. No
absolute width enters either: a receiver reads marks a little wider than
spaces, and receivers differ, so a width bucket would be a cliff where
one button mints two rows. Neither runs an infrared decoder, and nothing
here calls ``identity_frame`` or ``norm_fingerprint``, which do.

Band is in no key. The carrier lives on the row and is compared only
where both sides know it, so a band learned later never moves a row or
orphans a trigger.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from statistics import median

from .const import (
    RF_ADDRESS_FIRST_BODY_EDGES,
    RF_ADDRESS_HEAD_EDGES,
    RF_ASSUMED_FRAME_GAP_US,
    RF_GAP_ASSUMED,
    RF_GAP_MEASURED,
    RF_MIN_FRAMES,
)
from .identity import (
    NORM_FRAME_GAP_FACTOR,
    NORM_LEVEL_MIN_RATIO,
    _level_labels,
    _value_levels,
    canonical_edges,
)


@dataclass(frozen=True)
class FramePiece:
    """One piece of a capture: its edges (absolute) and how it ended.

    ``edges`` end with the gap that closed the piece when ``gap`` is set;
    the capture's last piece ends on a mark and has no gap.
    """

    edges: tuple[int, ...]
    gap: int | None


@dataclass(frozen=True)
class FrameParts:
    """A piece split into header, body and trailer (absolute widths)."""

    header: tuple[int, ...]
    body: tuple[int, ...]
    trailer: tuple[int, ...]
    # Whether ``body`` starts on a mark. A header of odd length leaves
    # the body starting on a space.
    body_starts_on_mark: bool


@dataclass(frozen=True)
class RfCapture:
    """What one capture says, once its frames have voted.

    ``frame`` is the canonical frame in HAIR's signed convention (mark
    positive), header, body and trailer, with the measured gap last when
    there is one. ``votes`` is how many whole frames agreed.
    """

    frame: list[int]
    fingerprint: str
    frame_hash: str
    device_key: str
    header_shape: str
    body_edges: int
    votes: int
    gap_us: int
    gap_source: str
    short_mark_us: int | None
    sl_pattern: str


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------


def split_frames(timings: list[int] | None) -> list[FramePiece]:
    """Cut a capture into pieces at every inter-frame gap.

    ``identity.first_frame``'s rule over every space rather than the
    first: a space at least ``NORM_FRAME_GAP_FACTOR`` times the capture's
    90th-percentile space is a gap. A capture with too few spaces to say
    is one piece.
    """
    edges = canonical_edges(timings)
    if not edges:
        return []
    spaces = [s for s in edges[1::2] if s > 0]
    if len(spaces) < 4:
        return [FramePiece(tuple(edges), None)]
    ordered = sorted(spaces)
    floor = ordered[int(0.9 * (len(ordered) - 1))] * NORM_FRAME_GAP_FACTOR
    pieces: list[FramePiece] = []
    start = 0
    for index in range(1, len(edges), 2):
        if edges[index] >= floor:
            pieces.append(FramePiece(tuple(edges[start:index + 1]), edges[index]))
            start = index + 1
    if start < len(edges):
        pieces.append(FramePiece(tuple(edges[start:]), None))
    return pieces


def _body_mask(edges: tuple[int, ...]) -> list[bool]:
    """Which edges sit on one of their polarity's two most populated levels."""
    mask = [False] * len(edges)
    for parity in (0, 1):
        values = list(edges[parity::2])
        if not values:
            continue
        levels = _value_levels(values, NORM_LEVEL_MIN_RATIO)
        counts = Counter(levels)
        # Most populated first; the level number (its width order) breaks
        # a tie, so the choice never depends on dict order.
        kept = {
            level for level, _ in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )[:2]
        }
        for position, level in enumerate(levels):
            mask[parity + 2 * position] = level in kept
    return mask


def split_body(piece: FramePiece | tuple[int, ...]) -> FrameParts:
    """Split a piece into header, body and trailer.

    The body is the edges on the two most populated width levels of
    their polarity; header and trailer are the runs outside them at
    either end. A piece's gap is always outside (nothing in a frame is as
    wide), so it always lands in the trailer.
    """
    edges = piece.edges if isinstance(piece, FramePiece) else tuple(piece)
    mask = _body_mask(edges)
    start = 0
    while start < len(edges) and not mask[start]:
        start += 1
    end = len(edges)
    while end > start and not mask[end - 1]:
        end -= 1
    return FrameParts(
        header=edges[:start],
        body=edges[start:end],
        trailer=edges[end:],
        body_starts_on_mark=start % 2 == 0,
    )


def _polarities(parts: FrameParts) -> tuple[list[int], list[int]]:
    first = list(parts.body[0::2])
    second = list(parts.body[1::2])
    return (first, second) if parts.body_starts_on_mark else (second, first)


def has_body(parts: FrameParts) -> bool:
    """A body: marks on at least two width levels, and spaces too.

    Noise repeats itself only in pieces without one (a lone mark, one
    mark-space-mark), which is what makes this the gate's structural
    half. It is a shape test, not a length: a long run of one width has
    no body however many edges it has.
    """
    marks, spaces = _polarities(parts)
    for values in (marks, spaces):
        if len(set(_value_levels(values, NORM_LEVEL_MIN_RATIO))) < 2:
            return False
    return True


def whole_frames(pieces: list[FramePiece]) -> list[tuple[FramePiece, FrameParts]]:
    """The pieces that are whole frames: a body, and the common length.

    Of the pieces with a body, those of the most common edge count; a
    tie goes to the longer count, since a cut frame is shorter than a
    whole one, never longer.
    """
    candidates = []
    for piece in pieces:
        parts = split_body(piece)
        if parts.body and has_body(parts):
            candidates.append((piece, parts))
    if not candidates:
        return []
    counts = Counter(len(piece.edges) for piece, _ in candidates)
    modal = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
    return [(piece, parts) for piece, parts in candidates if len(piece.edges) == modal]


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def header_shape(parts: FrameParts) -> str:
    """How many edges precede the body: ``h0`` for none."""
    return f"h{len(parts.header)}"


def body_labels(parts: FrameParts) -> list[int]:
    """The body's two-level labels, marks and spaces labelled apart."""
    marks, spaces = _polarities(parts)
    mark_labels = _level_labels(marks)
    space_labels = _level_labels(spaces)
    out: list[int] = []
    on_mark = parts.body_starts_on_mark
    m = s = 0
    for _ in parts.body:
        if on_mark:
            out.append(mark_labels[m])
            m += 1
        else:
            out.append(space_labels[s])
            s += 1
        on_mark = not on_mark
    return out


def _value_level_sequence(parts: FrameParts) -> list[int]:
    marks, spaces = _polarities(parts)
    mark_levels = _value_levels(marks, NORM_LEVEL_MIN_RATIO)
    space_levels = _value_levels(spaces, NORM_LEVEL_MIN_RATIO)
    out: list[int] = []
    on_mark = parts.body_starts_on_mark
    m = s = 0
    for _ in parts.body:
        if on_mark:
            out.append(mark_levels[m])
            m += 1
        else:
            out.append(space_levels[s])
            s += 1
        on_mark = not on_mark
    return out


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def frame_fingerprint(parts: FrameParts) -> str:
    """Tier 3 for radio: edge count, header shape and two-level body labels."""
    labels = "".join(str(label) for label in body_labels(parts))
    return _digest(f"RF:{len(parts.body)}:{header_shape(parts)}:{labels}")


def frame_hash(parts: FrameParts) -> str:
    """Tier 2 for radio, the twin of ``byte_hash``: multi-level body labels.

    Edge count, header shape and the body's ``_value_levels`` labels.
    No scale token: a receiver's mark widening differs between receivers
    and no width bucket is safe until it is measured on both.
    """
    levels = ",".join(str(level) for level in _value_level_sequence(parts))
    return _digest(f"RFH:{len(parts.body)}:{header_shape(parts)}:{levels}")


def is_address_first_24_symbol(parts: FrameParts) -> bool:
    """An EV1527 or PT2262 class frame: 24 two-width symbols and a sync mark.

    No header, a body of ``RF_ADDRESS_FIRST_BODY_EDGES`` edges starting
    on a mark. These families send the address first and the button
    last, which is what makes a head of the body an address.
    """
    return (
        not parts.header
        and parts.body_starts_on_mark
        and len(parts.body) == RF_ADDRESS_FIRST_BODY_EDGES
    )


def device_key(parts: FrameParts) -> str:
    """The Sniffer card a frame files under when nothing has heard it before.

    An address-first 24-symbol frame groups on its first
    ``RF_ADDRESS_HEAD_EDGES`` body labels: one remote's buttons on one
    card, two remotes on two. Every other shape groups on its edge count
    and header shape alone, one card per shape, until a family reader
    can read its address. Grouping is presentation: a row is never moved
    by it.
    """
    shape = f"DEV:RF:{len(parts.body)}:{header_shape(parts)}"
    if is_address_first_24_symbol(parts):
        head = "".join(
            str(label) for label in body_labels(parts)[:RF_ADDRESS_HEAD_EDGES]
        )
        return f"{shape}:{_digest(head)[:12]}"
    return shape


def sl_pattern(parts: FrameParts) -> str:
    """The diamonds: S and L over the body's two-level labels."""
    return "".join("L" if label else "S" for label in body_labels(parts))


# ---------------------------------------------------------------------------
# The vote
# ---------------------------------------------------------------------------


def _signed(edges: list[int]) -> list[int]:
    return [value if index % 2 == 0 else -abs(value) for index, value in enumerate(edges)]


def analyze(timings: list[int] | None) -> RfCapture | None:
    """One capture to one canonical frame, or None when it says nothing.

    None when no whole frame has a body, or when fewer than
    ``RF_MIN_FRAMES`` whole frames agree on one fingerprint. The winner
    is the fingerprint most whole frames share; the canonical frame is
    the per-position median of the winning frames (a receiver's jitter
    averages out, its widths stay real). The gap is the median of the
    gaps that closed winning frames, so a damaged duration in one frame
    cannot become the gap. When no winning frame was closed by a gap
    inside the capture (one frame per capture), the gap is assumed.
    """
    frames = whole_frames(split_frames(timings))
    if not frames:
        return None
    by_print: dict[str, list[tuple[FramePiece, FrameParts]]] = {}
    for piece, parts in frames:
        by_print.setdefault(frame_fingerprint(parts), []).append((piece, parts))
    # Most votes wins; the earliest fingerprint breaks a tie.
    winner_print, winners = max(by_print.items(), key=lambda item: len(item[1]))
    if len(winners) < RF_MIN_FRAMES:
        return None

    first_parts = winners[0][1]
    gaps = [piece.gap for piece, _ in winners if piece.gap is not None]
    width = len(winners[0][0].edges) - (1 if winners[0][0].gap is not None else 0)
    body_edges = [
        round(median(piece.edges[index] for piece, _ in winners))
        for index in range(width)
    ]
    if gaps:
        gap_us = round(median(gaps))
        gap_source = RF_GAP_MEASURED
        frame = [*_signed(body_edges), -gap_us]
    else:
        gap_us = RF_ASSUMED_FRAME_GAP_US
        gap_source = RF_GAP_ASSUMED
        frame = _signed(body_edges)

    labels = body_labels(first_parts)
    marks, _ = _polarities(first_parts)
    short_marks = [
        value for value, label in zip(marks, _level_labels(marks), strict=True)
        if label == 0
    ]
    return RfCapture(
        frame=frame,
        fingerprint=winner_print,
        frame_hash=frame_hash(first_parts),
        device_key=device_key(first_parts),
        header_shape=header_shape(first_parts),
        body_edges=len(first_parts.body),
        votes=len(winners),
        gap_us=gap_us,
        gap_source=gap_source,
        short_mark_us=round(median(short_marks)) if short_marks else None,
        sl_pattern="".join("L" if label else "S" for label in labels),
    )


def identity_of_frame(frame: list[int] | None) -> RfCapture | None:
    """The identity of one stored canonical frame (an RF row's timings).

    A stored frame is a single frame, so it is read as one whole frame
    with no vote: the fingerprint and hash it gives are the ones the
    capture that minted it gave.
    """
    pieces = split_frames(frame)
    candidates = [
        (piece, split_body(piece)) for piece in pieces
    ]
    candidates = [(p, parts) for p, parts in candidates if parts.body and has_body(parts)]
    if not candidates:
        return None
    piece, parts = max(candidates, key=lambda item: len(item[0].edges))
    labels = body_labels(parts)
    return RfCapture(
        frame=list(frame or []),
        fingerprint=frame_fingerprint(parts),
        frame_hash=frame_hash(parts),
        device_key=device_key(parts),
        header_shape=header_shape(parts),
        body_edges=len(parts.body),
        votes=1,
        gap_us=piece.gap or RF_ASSUMED_FRAME_GAP_US,
        gap_source=RF_GAP_MEASURED if piece.gap else RF_GAP_ASSUMED,
        short_mark_us=None,
        sl_pattern="".join("L" if label else "S" for label in labels),
    )
