"""Identity ends at the last real pulse: the unified strip (GH #125).

THE DEFECT. One waveform reaches HAIR wearing three different tails. A
file writes the inter-frame gap it was authored with; a receiver writes
its own measure of the trailing silence; ``raw_to_pronto`` pads the
missing final space with a zero. Both Pronto hash walks read the
rendered text, so the same physical button could carry up to three
identities, and the load-time migration kept moving stored rows onto a
form the air would never reproduce -- philippegu56's rows re-minted on
every reload, triggers going quiet with them.

THE FIX. ``EventParser._pronto_identity_timings`` applies
``identity.canonical_edges``'s rule inside both walks, so the tail is
never hashed and the three forms converge by construction.

WHAT THIS FILE PINS. The corpus invariant nobody pinned (wire and
canonical agree on every fixture code), the blast radius as counts, and
the edge classes the strip deliberately does not change. Every corpus
test reads the fixture tree at run time: no baked code lists, so a
fixture added tomorrow is measured tomorrow.

The legacy helpers below are verbatim copies of the pre-strip walks.
They are the only honest way to assert "this moved and that did not"
without checking in 841 hashes, and they follow the parity-pin pattern
``test_signal_flood.py`` uses for the GH #72 heal.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

import pytest

from custom_components.hair.const import (
    PRONTO_BYTE_HASH_BIN,
    PRONTO_DEVICE_PREAMBLE_PAIRS,
    PRONTO_GAP_THRESHOLD,
    PRONTO_NEC_ADDRESS_PAIRS,
    PRONTO_SL_THRESHOLD,
)
from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
    canonical_pronto,
    is_multi_frame_code,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto

FIXTURES = Path(__file__).parent / "fixtures"

_WORD = re.compile(r"^[0-9A-Fa-f]{4}$")


# ---------------------------------------------------------------------------
# The corpus, read from the fixture tree at run time
# ---------------------------------------------------------------------------


def _looks_pronto(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split()
    return len(parts) >= 5 and all(_WORD.match(p) for p in parts)


def _walk(node, sink: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if _looks_pronto(key):
                sink.append(key)
            _walk(value, sink)
    elif isinstance(node, list):
        for item in node:
            _walk(item, sink)
    elif _looks_pronto(node):
        sink.append(node)


def _dedupe(codes: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for code in codes:
        seen.setdefault(" ".join(code.split()).upper(), None)
    return list(seen)


def _json_corpus() -> list[str]:
    """Every Pronto in ``fixtures/**/*.json``. 853 unique as of v0.12.0."""
    found: list[str] = []
    for path in sorted(FIXTURES.rglob("*.json")):
        try:
            _walk(json.loads(path.read_text()), found)
        except (ValueError, UnicodeDecodeError):
            continue
    return _dedupe(found)


def _ext_corpus() -> list[str]:
    """The Prontos that do not live in plain JSON.

    ``.pronto`` files, the ``<ccf>`` elements of the Girr adapters (which
    are line-wrapped in the source and must be whitespace-joined before
    they parse), and the gzipped air-path captures. 79 unique, and mostly
    gap-tailed where the JSON corpus is mostly zero-tailed -- which is
    exactly why both are measured.
    """
    found: list[str] = []
    for path in sorted(FIXTURES.rglob("*.pronto")):
        text = " ".join(path.read_text().split())
        if _looks_pronto(text):
            found.append(text)
    for path in sorted(FIXTURES.rglob("*.girr")):
        for body in re.findall(
            r"<ccf[^>]*>(.*?)</ccf>", path.read_text(), re.S
        ):
            joined = " ".join(body.split())
            if _looks_pronto(joined):
                found.append(joined)
    for path in sorted(FIXTURES.rglob("*.json.gz")):
        try:
            with gzip.open(path, "rt") as handle:
                _walk(json.load(handle), found)
        except (OSError, ValueError, UnicodeDecodeError):
            continue
    seen = set(_json_corpus())
    return [c for c in _dedupe(found) if c not in seen]


JSON_CORPUS = _json_corpus()
EXT_CORPUS = _ext_corpus()
UNION_CORPUS = JSON_CORPUS + EXT_CORPUS


def _tail_class(code: str) -> str:
    """Which of the three tails this code was written with."""
    words = EventParser._parse_pronto_words(code)
    assert words is not None
    last = words[-1]
    if last == 0:
        return "zero"
    if last >= PRONTO_GAP_THRESHOLD:
        return "gap"
    return "sub"


# ---------------------------------------------------------------------------
# The pre-strip walks, copied verbatim so movement can be measured
# ---------------------------------------------------------------------------


def _legacy_sl_pattern(code: str | None) -> str | None:
    words = EventParser._parse_pronto_words(code)
    if words is None:
        return None
    pattern = []
    for t in words[4:]:
        if t >= PRONTO_GAP_THRESHOLD:
            break
        pattern.append("S" if t < PRONTO_SL_THRESHOLD else "L")
    if not pattern:
        return None
    return "".join(pattern)


def _legacy_byte_hash(code: str | None) -> str | None:
    words = EventParser._parse_pronto_words(code)
    if words is None:
        return None
    quantized: list[str] = []
    for t in words[4:]:
        if t >= PRONTO_GAP_THRESHOLD:
            break
        quantized.append(str(round(t / PRONTO_BYTE_HASH_BIN) * PRONTO_BYTE_HASH_BIN))
    if not quantized:
        return None
    return hashlib.sha256(",".join(quantized).encode()).hexdigest()[:16]


def _legacy_fingerprint(code: str | None) -> str | None:
    sl = _legacy_sl_pattern(code)
    if sl is None:
        return None
    return hashlib.sha256(f"PRONTO:{sl}".encode()).hexdigest()[:16]


def _legacy_device_fingerprint(code: str) -> str | None:
    words = EventParser._parse_pronto_words(code)
    sl = _legacy_sl_pattern(code)
    if words is None or sl is None:
        return None
    timings = words[4:]
    if timings and timings[0] >= 0x100:
        preamble = sl[2 : 2 + PRONTO_NEC_ADDRESS_PAIRS * 2]
    else:
        preamble = sl[: PRONTO_DEVICE_PREAMBLE_PAIRS * 2]
    payload = f"DEV:PRONTO:{words[1]:04X}:{preamble}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Idempotence, pinned corpus-wide (the invariant nobody pinned)
# ---------------------------------------------------------------------------


def test_the_corpus_is_the_one_the_measurement_was_taken_on():
    """A guard on the guards: if extraction breaks, the counts below
    would pass vacuously. 853 + 79 as measured at v0.12.0."""
    assert len(JSON_CORPUS) == 853
    assert len(EXT_CORPUS) == 79


def test_every_fixture_pronto_hashes_the_same_wire_or_canonical():
    """A1 and A2. The invariant the store's comment asserted and nothing
    checked, which is why the suite stayed green on a broken store."""
    bad_hash = [
        c for c in JSON_CORPUS
        if canonical_byte_hash(c) != EventParser.pronto_byte_hash(c)
    ]
    bad_fp = [
        c for c in JSON_CORPUS
        if canonical_fingerprint("PRONTO", c, None)
        != EventParser.signal_fingerprint("PRONTO", c, None)
    ]
    assert bad_hash == []
    assert bad_fp == []


def test_the_extended_corpus_agrees_too():
    """A3. The gap-tailed half of the fixture tree, where the JSON
    corpus is almost entirely zero-tailed."""
    for code in EXT_CORPUS:
        assert canonical_byte_hash(code) == EventParser.pronto_byte_hash(code)
        assert canonical_fingerprint("PRONTO", code, None) == (
            EventParser.signal_fingerprint("PRONTO", code, None)
        )


def test_the_three_tail_shapes_of_one_code_share_one_identity():
    """The test that would have caught the bug, and the first one to
    fail if the strip is ever removed.

    One waveform, three tails: the inter-frame gap a file writes, the
    zero ``raw_to_pronto`` pads, and the sub-threshold silence a
    receiver measures.
    """
    body = "0000 006D 0002 0000 0020 0040 0020"
    gap, padded, heard = f"{body} 09BC", f"{body} 0000", f"{body} 017C"

    hashes = {EventParser.pronto_byte_hash(c) for c in (gap, padded, heard)}
    prints = {
        EventParser.signal_fingerprint("PRONTO", c, None)
        for c in (gap, padded, heard)
    }
    canon = {canonical_byte_hash(c) for c in (gap, padded, heard)}

    assert len(hashes) == 1
    assert len(prints) == 1
    assert len(canon) == 1
    assert hashes == canon
    # The surviving value is the one the gap tail already had: the other
    # two move onto it, not the other way round.
    assert hashes == {_legacy_byte_hash(gap)}


def test_canonicalization_is_idempotent_on_identity_not_only_text():
    """The existing ``test_canonicalization_is_idempotent`` pins TEXT
    idempotence, which was true all along. This pins the identity kind,
    which was not, and whose name is why the false store comment stood.
    """
    for code in JSON_CORPUS[:50] + EXT_CORPUS[:20]:
        once = canonical_pronto(code)
        if once is None:
            continue
        assert canonical_byte_hash(once) == canonical_byte_hash(code)
        assert canonical_fingerprint("PRONTO", once, None) == (
            canonical_fingerprint("PRONTO", code, None)
        )


def test_a_real_receiver_tail_is_not_simulated_by_raw_to_pronto():
    """``test_canonical_identity._off_the_air`` renders through
    ``raw_to_pronto``, which zero-pads -- so the suite never saw the
    shape philippegu56's hardware actually produces. A genuine
    sub-threshold tail must now agree with it."""
    filed = "0000 006D 0002 0000 0020 0040 0020 09BC"
    command = ProntoCommand(filed)
    simulated = raw_to_pronto(
        command.get_raw_timings(), frequency=command.modulation
    )
    genuine = "0000 006D 0002 0000 0020 0040 0020 017C"

    assert EventParser.pronto_byte_hash(simulated) == (
        EventParser.pronto_byte_hash(genuine)
    )
    assert EventParser.signal_fingerprint("PRONTO", simulated, None) == (
        EventParser.signal_fingerprint("PRONTO", genuine, None)
    )


# ---------------------------------------------------------------------------
# Blast radius, pinned as counts
# ---------------------------------------------------------------------------


def test_only_the_tail_class_moves():
    """A4 and A5. Exactly 841 of the 853 move; the 12 that do not are
    exactly the gap-tailed ones, whose tails the gap break already
    excluded. A moved value on a gap-tail code means the strip is
    reaching past the tail and is wrong."""
    moved = [
        c for c in JSON_CORPUS
        if _legacy_byte_hash(c) != EventParser.pronto_byte_hash(c)
    ]
    still = [
        c for c in JSON_CORPUS
        if _legacy_byte_hash(c) == EventParser.pronto_byte_hash(c)
    ]

    assert len(moved) == 841
    assert len(still) == 12
    assert {_tail_class(c) for c in still} == {"gap"}
    assert sorted(_tail_class(c) for c in set(moved)) == (
        sorted(["zero"] * 838 + ["sub"] * 3)
    )
    # Every mover lands on the value canonicalization already computed:
    # the two layers converge, they do not both drift somewhere new.
    for code in moved:
        assert EventParser.pronto_byte_hash(code) == canonical_byte_hash(code)


def test_the_extended_corpus_moves_seven():
    """The mirror of A4/A5 on the gap-tailed corpus: 7 move, 72 hold."""
    moved = [
        c for c in EXT_CORPUS
        if _legacy_byte_hash(c) != EventParser.pronto_byte_hash(c)
    ]
    assert len(moved) == 7
    assert {_tail_class(c) for c in moved} == {"sub", "zero"}


def test_device_fingerprint_does_not_move():
    """A6. The grouping key is persisted and never recomputed at load,
    so if it moved, every catalog remote would split in two. The strip
    removes at most one S/L character and the preamble slice is 18
    characters at most, so it cannot reach: measured 0 of 932."""
    for code in UNION_CORPUS:
        assert _legacy_device_fingerprint(code) == (
            EventParser.device_fingerprint("PRONTO", None, None, code)
        )


def test_the_strip_removes_at_most_one_character():
    """Why A6 holds rather than happening to hold. One tail word, so one
    S/L character, against a shortest corpus pattern of 23."""
    deltas = set()
    shortest = min(
        len(EventParser._pronto_sl_pattern(c) or "") for c in UNION_CORPUS
    )
    for code in UNION_CORPUS:
        before = len(_legacy_sl_pattern(code) or "")
        after = len(EventParser._pronto_sl_pattern(code) or "")
        deltas.add(before - after)
    assert deltas <= {0, 1}
    assert shortest > PRONTO_NEC_ADDRESS_PAIRS * 2 + 2


# ---------------------------------------------------------------------------
# Edge classes
# ---------------------------------------------------------------------------


def test_degenerate_code_has_no_byte_hash_on_either_layer():
    """GH #108, converged for free. An all-zero code strips away to
    nothing, so the wire walk now answers ``None`` -- which is what
    ``canonical_byte_hash`` has answered since GH #108 shipped. This is
    a CHANGE in the wire walk: it used to return a hash of a signal that
    transmits nothing and can match nothing."""
    degenerate = "0000 006D 0002 0000 0000 0000 0000 0000"

    assert _legacy_byte_hash(degenerate) is not None
    assert EventParser.pronto_byte_hash(degenerate) is None
    assert EventParser._pronto_sl_pattern(degenerate) is None
    assert canonical_byte_hash(degenerate) is None


def test_a_burst2_repeat_frame_never_reaches_the_hash():
    """A ditto sequence sits behind a gap word, so both walks stop
    before it -- before this change and after. Its identity does not
    move, which is why the Girr Onkyo class is in the unchanged 72."""
    onkyo = next(
        (c for c in UNION_CORPUS
         if _tail_class(c) == "gap" and is_multi_frame_code(c)),
        None,
    )
    assert onkyo is not None
    assert _legacy_byte_hash(onkyo) == EventParser.pronto_byte_hash(onkyo)


def test_a_multi_frame_code_with_a_sub_threshold_gap_still_hashes_all_frames():
    """THE KNOWN LIMIT, pinned so nobody reads more into the strip than
    is there. An AC state code's inter-frame gaps sit below the
    threshold, so both walks hash every frame while a receiver delivers
    one frame per capture. The strip does not close that; the
    receiver-tolerant tier is the designed answer and stays necessary.
    """
    multi = [c for c in JSON_CORPUS if is_multi_frame_code(c)]
    assert multi, "the corpus is supposed to be mostly multi-frame"
    code = multi[0]
    words = EventParser._parse_pronto_words(code)
    assert words is not None
    hashed = EventParser._pronto_identity_timings(code)
    assert hashed is not None
    # Everything but the header and the stripped tail reaches the hash.
    assert len(hashed) >= len(words) - 4 - 1


def test_an_unreadable_code_still_answers_none():
    assert EventParser._pronto_identity_timings(None) is None
    assert EventParser._pronto_identity_timings("not a pronto") is None
    assert EventParser._pronto_identity_timings("0000 006D") is None
    assert EventParser.pronto_byte_hash("0000 006D") is None
    assert EventParser._pronto_sl_pattern("0000 006D") is None


@pytest.mark.parametrize(
    "code",
    [
        "0000 006D 0002 0000 0020 0040 0020 0000",
        "0000 006D 0002 0000 0020 0040 0020 09BC",
    ],
)
def test_the_walk_ends_on_a_mark(code: str):
    """The whole rule in one assertion: odd length means the last word
    is a mark, whatever tail the code was written with."""
    timings = EventParser._pronto_identity_timings(code)
    assert timings is not None
    assert len(timings) % 2 == 1
