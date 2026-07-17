"""Local IR protocol decoders (the shave-and-a-haircut package).

HAIR's local-first decoder strategy (multi-protocol decoder plan, Section
6): each module in this package defines a Command class shaped exactly like
an ``infrared_protocols`` module -- same base class, same keyword-only
constructor, same ``get_raw_timings`` / ``from_raw_timings`` contract -- so
the module can be donated upstream as a near-file-copy. The registry in
``protocol_decode`` prefers the upstream class whenever the bundled library
ships a decoder for the protocol (feature-detected via
``from_raw_timings``); these local classes are the polyfill until then.

Rules for this package (do not break them):

- No code derived from GPL/LGPL implementations (IRremoteESP8266, ESPHome
  C++, LIRC). Timing constants are protocol facts and are fine; code
  structure is not. Everything here is written fresh from the protocol
  specs and validated against captures. This keeps the upstream donation
  (Apache-2.0) unencumbered.
- Encoders must be behavior-identical to the upstream library's encoder
  when upstream ships one (asserted by round-trip tests), so swapping the
  registry to the upstream class can never change what is transmitted.
- Decoders follow the upstream ``NECCommand.from_raw_timings`` conventions:
  classmethod, ``list[int]`` signed microsecond timings in (positive=mark,
  negative=space) form, return ``Self | None``, never raise on malformed
  input by construction (bounds-checked indexing only).

Shared helpers below implement the two ideas every decoder needs: tolerant
timing classification and frame splitting. Real captures arrive with
receiver jitter (marks stretched by AGC, spaces shortened) and often
contain several complete frames per capture (a held button, or a remote
that always re-sends). Decoders therefore split the capture into frames,
decode each frame independently, and let the majority vote decide -- a
trailing partial frame or a vendor preamble frame cannot poison the
result.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence

# Default fractional tolerance for matching a timing against its nominal
# value. Matches the convention the upstream NEC decoder established (0.4).
TOLERANCE = 0.4


def is_close(actual: int, expected: int, tolerance: float = TOLERANCE) -> bool:
    """Return True if ``actual`` is within ``tolerance`` of ``expected``.

    Both values are treated as magnitudes; callers negate spaces before
    passing them in, mirroring the upstream NEC decoder's convention.
    """
    if expected <= 0:
        return False
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def split_frames(timings: Sequence[int], min_gap_us: int) -> list[list[int]]:
    """Split signed timings into frames at spaces of at least ``min_gap_us``.

    The gap spaces themselves are dropped; each returned frame is a signed
    timing list that starts on a mark. Frames that end the capture without
    a trailing gap are returned as-is (captures routinely truncate the
    final trailer space). Empty input returns no frames.
    """
    frames: list[list[int]] = []
    current: list[int] = []
    for value in timings:
        if value < 0 and -value >= min_gap_us:
            if current:
                frames.append(current)
                current = []
            continue
        if not current and value < 0:
            # A frame never starts on a space; drop leading idle.
            continue
        current.append(value)
    if current:
        frames.append(current)
    return frames


def majority[T](values: Sequence[T]) -> tuple[T, int] | None:
    """Return the most common value and its count, or None if empty.

    Ties resolve to the value seen first, which for IR captures means the
    earliest decoded frame of the tied set -- deterministic and stable.
    """
    if not values:
        return None
    counted = Counter(values).most_common()
    return counted[0]


def decode_frames_majority[T](
    frames: Sequence[Sequence[int]],
    decode_frame: Callable[[Sequence[int]], T | None],
    *,
    min_votes: int = 1,
) -> tuple[T, int] | None:
    """Decode every frame, majority-vote the results.

    Returns ``(winner, vote_count)`` or None when no frame decodes or the
    winner has fewer than ``min_votes`` votes. ``min_votes`` exists for
    checksum-free protocols (Symphony) where a single decoded frame is not
    enough evidence to accept the capture.
    """
    decoded = [d for d in (decode_frame(f) for f in frames) if d is not None]
    top = majority(decoded)
    if top is None or top[1] < min_votes:
        return None
    return top
