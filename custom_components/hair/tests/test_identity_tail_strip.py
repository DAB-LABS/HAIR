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
import logging
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


# ---------------------------------------------------------------------------
# The migration: every holder of an identity re-keys on the same load
# ---------------------------------------------------------------------------


FILE_FORM = "0000 006D 0002 0000 0020 0040 0020 0000"
"""How a file writes it: raw_to_pronto padded the final space with zero."""

AIR_FORM = "0000 006D 0002 0000 0020 0040 0020 017C"
"""How philippegu56's receiver writes it: its own measure of the silence.

Sub-threshold, so the gap break never saw it and the old walk hashed it
as a timing. 380 carrier cycles is about 10 ms; the gap threshold is
1024 cycles, about 27 ms, which is why a real trailing silence can sit
either side of the cliff depending on the receiver.
"""

CLASS_E = (
    "0000 006C 0022 0002 015B 00AD 0016 0016 0016 0041 0016 0016 "
    "0016 0041 0016 0041"
)
"""A code that hashes but does not canonicalize.

The header declares 34 intro pairs plus 2 repeat pairs, so 72 timing
words, while the body carries 12: the burst-2 repeat sequence was
truncated somewhere upstream, as a copy out of an IRDB or Girr entry
easily does. ``ProntoCommand`` refuses it and ``canonical_pronto``
answers None, while both hash walks read it without complaint. This is
the class the migration used to skip, and its hash moves like any
other, so skipping it left the row behind.
"""


def _capture(code: str):
    """One capture of ``code``, normalized as the Sniffer normalizes it.

    Rebuilt from raw timings, which is what every receive path does, so
    the identity is the wire form rather than the text.
    """
    from custom_components.hair.models import CaptureResult
    from custom_components.hair.signal_monitor import normalize

    command = ProntoCommand(code)
    raw = command.get_raw_timings()
    return normalize(
        CaptureResult(
            protocol="PRONTO",
            code=raw_to_pronto(raw, frequency=command.modulation),
            raw_timings=raw,
            frequency=command.modulation,
        )
    )


@pytest.fixture
def store():
    from custom_components.hair.storage import HAIRStore

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    built = HAIRStore(hass)
    built._data = {}
    built._triggers = {}
    built._trigger_remotes = {}
    return built


def test_the_two_tails_were_two_identities_and_are_now_one():
    """The premise of every test below, stated once."""
    assert _legacy_byte_hash(FILE_FORM) != _legacy_byte_hash(AIR_FORM)
    assert _legacy_fingerprint(FILE_FORM) != _legacy_fingerprint(AIR_FORM)
    assert EventParser.pronto_byte_hash(FILE_FORM) == (
        EventParser.pronto_byte_hash(AIR_FORM)
    )
    assert EventParser.signal_fingerprint("PRONTO", FILE_FORM, None) == (
        EventParser.signal_fingerprint("PRONTO", AIR_FORM, None)
    )


def test_trigger_rekeys_and_fires_on_the_surviving_row(store):
    """The mandatory acceptance surface: the fragment pair collapses and
    the trigger lands on what is left.

    A remote holding a pasted row and its own capture of the same
    button. Two rows, because the tails gave them two identities. One
    load collapses them, re-keys the trigger, and a fresh press of the
    same button matches the row that survived.
    """
    from custom_components.hair.models import (
        IRTrigger,
        UnknownDevice,
        UnknownSignal,
    )
    from custom_components.hair.signal_store import _transform_loaded

    device = UnknownDevice(label="Arris")
    device.signals = [
        UnknownSignal(
            id="pasted", protocol="PRONTO", code=FILE_FORM, hit_count=3,
            fingerprint=_legacy_fingerprint(FILE_FORM),
            byte_hash=_legacy_byte_hash(FILE_FORM),
            alias="Power", first_seen="2026-08-01T00:00:00+00:00",
        ),
        UnknownSignal(
            id="heard", protocol="PRONTO", code=AIR_FORM, hit_count=5,
            fingerprint=_legacy_fingerprint(AIR_FORM),
            byte_hash=_legacy_byte_hash(AIR_FORM),
            first_seen="2026-08-02T00:00:00+00:00",
        ),
    ]

    devices, _dismissed, dirty = _transform_loaded(
        {"devices": [device.to_dict()], "dismissed": []}
    )

    rows = next(iter(devices.values())).signals
    assert dirty is True
    assert len(rows) == 1
    survivor = rows[0]
    assert survivor.id == "pasted"
    assert survivor.hit_count == 8
    assert survivor.alias == "Power"

    store._triggers = {
        "t1": IRTrigger(
            id="t1", name="Power", protocol="PRONTO", code=FILE_FORM,
            signal_fingerprint=_legacy_fingerprint(FILE_FORM),
            byte_hash=_legacy_byte_hash(FILE_FORM),
        )
    }
    assert store._backfill_canonical_identity() is True
    trigger = store._triggers["t1"]
    assert trigger.signal_fingerprint == survivor.fingerprint
    assert trigger.byte_hash == survivor.byte_hash

    heard = _capture(AIR_FORM)
    assert trigger.matches_signal(
        heard.sig_fp, heard.byte_hash, heard.decoded_fingerprint
    )


def test_the_healed_row_still_carries_its_trigger_badge(store):
    """The v0.6.1 orphan class, guarded.

    Firing and the yellow badge are different questions: in v0.6.1 a
    heal-merged row kept firing while the badge went dark, because the
    survivor carried a different fingerprint from the trigger. Under
    this migration both sides converge on the same load, so the badge
    sits on the survivor.
    """
    from custom_components.hair.models import (
        IRTrigger,
        UnknownDevice,
        UnknownSignal,
    )
    from custom_components.hair.signal_store import _transform_loaded

    device = UnknownDevice(label="Arris")
    device.signals = [
        UnknownSignal(
            id="pasted", protocol="PRONTO", code=FILE_FORM,
            fingerprint=_legacy_fingerprint(FILE_FORM),
            byte_hash=_legacy_byte_hash(FILE_FORM),
        ),
        UnknownSignal(
            id="heard", protocol="PRONTO", code=AIR_FORM,
            fingerprint=_legacy_fingerprint(AIR_FORM),
            byte_hash=_legacy_byte_hash(AIR_FORM),
        ),
    ]
    devices, _dismissed, _dirty = _transform_loaded(
        {"devices": [device.to_dict()], "dismissed": []}
    )
    survivor = next(iter(devices.values())).signals[0]

    store._triggers = {
        "t1": IRTrigger(
            id="t1", name="Power", protocol="PRONTO", code=AIR_FORM,
            signal_fingerprint=_legacy_fingerprint(AIR_FORM),
            byte_hash=_legacy_byte_hash(AIR_FORM),
        )
    }
    store._backfill_canonical_identity()

    assert store._triggers["t1"].matches_signal(
        survivor.fingerprint, survivor.byte_hash, survivor.decoded_fingerprint
    )


def test_a_trigger_whose_code_does_not_canonicalize_is_still_rekeyed(store):
    """The skip hole, closed.

    The migration used to require ``canonical_pronto`` to succeed before
    it would touch a row. A class-E code hashes and does not
    canonicalize, so the guard skipped exactly the rows whose hash this
    release moves, and the trigger would have gone quiet with no way to
    tell why.
    """
    from custom_components.hair.models import IRTrigger

    assert canonical_pronto(CLASS_E) is None
    assert EventParser.pronto_byte_hash(CLASS_E) is not None
    stale = _legacy_byte_hash(CLASS_E)
    fresh = EventParser.pronto_byte_hash(CLASS_E)
    assert stale != fresh

    store._triggers = {
        "t1": IRTrigger(
            id="t1", name="Power", protocol="PRONTO", code=CLASS_E,
            signal_fingerprint=_legacy_fingerprint(CLASS_E),
            byte_hash=stale,
        )
    }

    assert store._backfill_canonical_identity() is True
    trigger = store._triggers["t1"]
    assert trigger.byte_hash == fresh
    assert trigger.signal_fingerprint == (
        EventParser.signal_fingerprint("PRONTO", CLASS_E, None)
    )


def test_a_command_whose_code_does_not_canonicalize_is_still_rekeyed(store):
    """The same hole on the command loop, which the matcher indexes."""
    from custom_components.hair.models import IRCommand, IRDevice

    device = IRDevice(id="dev-1", name="Adopted")
    device.commands = [
        IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=CLASS_E,
            byte_hash=_legacy_byte_hash(CLASS_E),
        )
    ]
    store._data = {"dev-1": device}

    assert store._backfill_canonical_identity() is True
    assert device.commands[0].byte_hash == (
        EventParser.pronto_byte_hash(CLASS_E)
    )


def test_a_legacy_trigger_keeps_its_hashless_broad_match(store):
    """The v0.5.8 rule, unchanged: repoint a hash, never add one.

    A pre-0.5.8 trigger matches broadly on its fingerprint. Narrowing it
    at load could mismatch a live capture and silence it, and a tier-2
    miss is fatal, so the migration leaves the hash absent.
    """
    from custom_components.hair.models import IRTrigger

    store._triggers = {
        "t1": IRTrigger(
            id="t1", name="Power", protocol="PRONTO", code=FILE_FORM,
            signal_fingerprint=_legacy_fingerprint(FILE_FORM),
            byte_hash=None,
        )
    }

    store._backfill_canonical_identity()
    trigger = store._triggers["t1"]
    assert trigger.byte_hash is None
    # The fingerprint still moves: that half was always recomputed.
    assert trigger.signal_fingerprint == (
        EventParser.signal_fingerprint("PRONTO", FILE_FORM, None)
    )


def test_pin_bindings_rederive_across_the_move(store):
    """A pinned Remote drives the same command after the identities move.

    Bindings hold ids, not identity values, and are rederived at every
    load from whatever the identities currently are. This proves the
    order holds: the identity backfill runs before the rederive, so the
    map is built on the new values and not the old.
    """
    from custom_components.hair.models import (
        IRCommand,
        IRDevice,
        IRTrigger,
        TriggerRemote,
    )
    from custom_components.hair.pin_bindings import derive_bindings

    device = IRDevice(id="dev-1", name="Adopted")
    device.commands = [
        IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=FILE_FORM,
            byte_hash=_legacy_byte_hash(FILE_FORM),
        )
    ]
    store._data = {"dev-1": device}

    remote = TriggerRemote(
        name="Arris", origin="closet", pinned_device_ids=["dev-1"]
    )
    store._trigger_remotes[remote.id] = remote
    trigger = IRTrigger(
        id="t1", name="Power", protocol="PRONTO", code=AIR_FORM,
        signal_fingerprint=_legacy_fingerprint(AIR_FORM),
        byte_hash=_legacy_byte_hash(AIR_FORM),
        trigger_remote_id=remote.id, origin="closet",
    )
    store._triggers = {"t1": trigger}

    # Before: the two tails gave the pair two identities and no binding.
    assert derive_bindings(store, remote) == {"dev-1": {}}

    store._backfill_canonical_identity()
    store._rebuild_command_index()

    assert derive_bindings(store, remote) == {"dev-1": {"t1": "c1"}}


def test_protocolless_pronto_rows_do_not_collapse():
    """Two different unstamped codes must get two fingerprints.

    ``protocol`` defaults to None on UnknownSignal, IRCommand and
    IRTrigger, and both load-time migrations call canonical_fingerprint
    with raw_timings=None. Before the widening, such a row fell through
    to the fingerprint of an EMPTY raw timing list: one constant, shared
    by every protocol-less row in the store, written in at load.
    """
    a = "0000 006D 0002 0000 0020 0040 0020 0000"
    b = "0000 006D 0002 0000 0040 0020 0040 0000"
    empty_raw = EventParser.signal_fingerprint(None, None, None)

    fp_a = canonical_fingerprint(None, a, None)
    fp_b = canonical_fingerprint(None, b, None)

    assert fp_a != fp_b
    assert fp_a != empty_raw
    assert fp_b != empty_raw
    # And an unstamped row now agrees with the stamped answer, which is
    # the whole point: one code, one identity, whichever door minted it.
    assert fp_a == canonical_fingerprint("PRONTO", a, None)
    assert fp_b == canonical_fingerprint("PRONTO", b, None)


def test_an_unstamped_class_e_row_is_still_hashed_as_pronto():
    """Hashable but not canonicalizable, and unstamped: the case that
    would otherwise slip past the widening and onto the constant."""
    empty_raw = EventParser.signal_fingerprint(None, None, None)

    assert canonical_pronto(CLASS_E) is None
    assert canonical_fingerprint(None, CLASS_E, None) != empty_raw
    assert canonical_fingerprint(None, CLASS_E, None) == (
        EventParser.signal_fingerprint("PRONTO", CLASS_E, None)
    )


def test_an_unreadable_code_with_no_timings_gets_no_fingerprint():
    """The collapse, one step further out than the Pronto widening.

    A row with no protocol stamp, a code that is not Pronto at all, and
    no raw timings has nothing to hash. signal_fingerprint would hand
    back the empty-raw constant and the migration would write it onto
    every such row in the store, which is how three junk rows collapse
    into one. The empty string is the honest answer and every caller
    already skips it.
    """
    empty_raw = EventParser.signal_fingerprint(None, None, None)
    for code in ("not a pronto code", "0000 006D", "AAAA"):
        assert canonical_fingerprint(None, code, None) == ""
        assert canonical_fingerprint(None, code, None) != empty_raw
    # An empty code was never the problem: there is no row to collapse.
    assert canonical_fingerprint(None, "", None) == (
        EventParser.signal_fingerprint(None, "", None)
    )


def test_an_unreadable_code_with_timings_still_hashes_them():
    """Only the nothing-to-hash case answers empty. Real timings are
    real identity, whatever the code field says."""
    raw = [500, -500, 1000, -1000]
    assert canonical_fingerprint(None, "AAAA", raw) == (
        EventParser.signal_fingerprint(None, "AAAA", raw)
    )
    assert canonical_fingerprint(None, "AAAA", raw) != ""


def test_a_stamped_non_pronto_protocol_still_passes_through():
    assert canonical_fingerprint("NEC", "0x20DF10EF", None) == (
        EventParser.signal_fingerprint("NEC", "0x20DF10EF", None)
    )


def test_a_non_string_code_costs_one_row_not_the_catalog(caplog):
    """One unreadable row must not take the whole Sniffer catalog.

    The canonical block runs inside the single executor job that loads
    every remote the user has, and canonical_pronto on a non-string code
    raises AttributeError out of pronto_hex.split(), which is not in the
    ValueError family the identity helpers catch. GH #108's lesson,
    applied to the row that GH #125's widening now lets through.
    """
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import _transform_loaded

    device = UnknownDevice(label="Clipped")
    device.signals = [
        UnknownSignal(
            id="ok", protocol="PRONTO", code=FILE_FORM,
            fingerprint=_legacy_fingerprint(FILE_FORM),
            byte_hash=_legacy_byte_hash(FILE_FORM),
        )
    ]
    raw = {"devices": [device.to_dict()], "dismissed": []}
    rows = raw["devices"][0]["signals"]
    rows.append(
        {**rows[0], "id": "bad", "code": 123, "fingerprint": "",
         "byte_hash": None}
    )

    with caplog.at_level(logging.WARNING):
        devices, _dismissed, _dirty = _transform_loaded(raw)

    loaded = {s.id: s for s in next(iter(devices.values())).signals}
    # The catalog came back, and the good row was repointed as normal.
    assert "ok" in loaded
    assert loaded["ok"].byte_hash == EventParser.pronto_byte_hash(FILE_FORM)
    assert loaded["ok"].fingerprint == (
        EventParser.signal_fingerprint("PRONTO", FILE_FORM, None)
    )
    # The bad row survives untouched, and says so once.
    assert "bad" in loaded
    assert any(
        "bad" in record.getMessage() for record in caplog.records
    ), [r.getMessage() for r in caplog.records]


# ---------------------------------------------------------------------------
# Nothing that leaves the install carries an identity
# ---------------------------------------------------------------------------
#
# The RM4 Pro question, asked of this fix. The 0.9.8 trailing-pause trim
# broke a Broadlink RM4 Pro because something downstream consumed the
# thing that was removed. The hashed tail is a constant and carries no
# information, so the equivalent blind spot here is not a CONSUMER but a
# HOLDER: an artifact that leaves the install carrying an old identity
# value and is later read back against a new one. These prove there is
# no such holder, rather than asserting it in a comment.


WIGS = FIXTURES / "wigs"


def test_claim_digests_do_not_move():
    """A wig's claims bind the code TEXT, over the whole corpus.

    row_digest is what every signed fitting is signed over, so if it
    moved with identity, this release would invalidate every signature
    ever written. It hashes normalized_pronto plus the ditto count and
    the bypass flag, and identity is not in it. Asserted here across the
    fixture tree rather than on the single code test_canonical_identity
    uses, and asserted as a property: computing every identity a code
    has leaves its digest byte-identical.
    """
    from custom_components.hair.wig_format import row_digest

    before = {code: row_digest(code, 0, False) for code in UNION_CORPUS}
    for code in UNION_CORPUS:
        canonical_byte_hash(code)
        canonical_fingerprint("PRONTO", code, None)
        EventParser.pronto_byte_hash(code)
        EventParser.signal_fingerprint("PRONTO", code, None)
    after = {code: row_digest(code, 0, False) for code in UNION_CORPUS}

    assert before == after
    # And the digest does move when the TEXT moves, so the assertion
    # above is not passing because row_digest ignores its argument.
    a, b = UNION_CORPUS[0], UNION_CORPUS[1]
    assert row_digest(a, 0, False) != row_digest(b, 0, False)


@pytest.mark.parametrize(
    "name",
    [
        "dreo-fan-dr-haf004s-perfect-fit.wig.json",
        "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json",
    ],
)
def test_an_existing_signed_fitting_still_verifies(name: str):
    """No ed25519 signature covers an identity value.

    Both certified fixtures were signed before this release. If any
    signature bound a byte_hash or a fingerprint, moving 841 of them
    would show up right here.
    """
    pytest.importorskip("cryptography")
    from custom_components.hair.fitting_signing import verify_fitting

    wig = json.loads((WIGS / name).read_text())
    fittings = wig.get("fittings") or []
    assert fittings, "the fixture is supposed to be a signed one"
    for entry in fittings:
        assert verify_fitting(entry) == "valid"


@pytest.mark.parametrize(
    "name",
    [
        "dreo-fan-dr-haf004s-perfect-fit.wig.json",
        "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json",
    ],
)
def test_no_wig_format_field_carries_an_identity(name: str):
    """A structural guard, so a future field cannot quietly re-couple
    the file format to identity.

    The wig format cannot carry this defect because it cannot carry an
    identity at all. The only ``fingerprint`` anywhere in the wig layer
    is a signing key digest, which is a property of the signer and not
    of any signal.
    """
    from custom_components.hair.wig_format import parse_wig, serialize_wig

    parsed = parse_wig((WIGS / name).read_text())
    assert parsed.wig is not None, parsed.errors
    out = json.loads(serialize_wig(parsed.wig))

    found: list[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{path}.{key}"
                if key == "byte_hash" or key.endswith("fingerprint"):
                    found.append(here)
                walk(value, here)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(out)
    assert found == [], found


def test_comb_receipt_holds_no_identity():
    """The comb's receipt keys on cell and row keys, deliberately
    outside every canonical hash. Nothing in it moves with identity."""
    from custom_components.hair.wig_format import parse_wig, serialize_wig

    parsed = parse_wig(
        (WIGS / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
        .read_text()
    )
    assert parsed.wig is not None, parsed.errors
    out = json.loads(serialize_wig(parsed.wig))
    receipt = out.get("comb")
    assert receipt is not None, "the fixture is supposed to carry a comb"

    text = json.dumps(receipt)
    assert "byte_hash" not in text
    assert "fingerprint" not in text
    # And no bare 16-hex identity value rode along under another name.
    assert not re.search(r'"[0-9a-f]{16}"', text), text[:400]


@pytest.mark.asyncio
async def test_a_migrating_load_saves_once_and_a_clean_one_never_saves():
    """The load-time catalog migration has to reach disk.

    Setting the dirty flag arms nothing -- schedule_save is what starts
    the debounce -- so before this the migration lived in memory until
    some unrelated write flushed it, and every boot re-ran it. Measured
    on the bench box before the fix: 495 of 552 rows moved in memory, 0
    reached the file, and the file's mtime never changed across the
    restart.

    Both halves are asserted, because a save at every boot would be its
    own defect on a flooded store: a stale catalog saves exactly once,
    and the payload it wrote loads back clean with no save at all.
    """
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import SignalStore

    def _hass():
        hass = MagicMock()
        hass.loop = MagicMock()
        hass.loop.call_later = MagicMock(return_value=MagicMock())
        hass.async_create_task = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        return hass

    device = UnknownDevice(label="Clipped")
    device.signals = [
        UnknownSignal(
            id="s1", protocol="PRONTO", code=FILE_FORM,
            fingerprint=_legacy_fingerprint(FILE_FORM),
            byte_hash=_legacy_byte_hash(FILE_FORM),
        ),
        # A row no load can ever repair, beside the ones this load
        # moves. Found on every boot, changed by none. It must not keep
        # the store dirty, or the second boot rewrites the whole catalog
        # to say nothing -- which is what one such row did to the bench
        # store, at 1.4 MB a time.
        UnknownSignal(
            id="unrepairable", protocol="PRONTO", code=None,
            fingerprint="", byte_hash=None,
        ),
    ]
    stale = {
        "devices": [device.to_dict()],
        "dismissed": [],
        "plucked_stores": [{"integration": "broadlink", "store_id": "x"}],
    }

    written: dict = {}
    store = SignalStore(_hass())
    with patch.object(store, "_store") as mock_store:
        mock_store.async_load = AsyncMock(return_value=stale)
        mock_store.async_save = AsyncMock(
            side_effect=lambda payload: written.update(payload)
        )
        await store.async_load()

    assert mock_store.async_save.await_count == 1, "a stale catalog must persist"
    rows = {s["id"]: s for s in written["devices"][0]["signals"]}
    row = rows["s1"]
    assert row["byte_hash"] == EventParser.pronto_byte_hash(FILE_FORM)
    assert row["fingerprint"] == (
        EventParser.signal_fingerprint("PRONTO", FILE_FORM, None)
    )
    assert row["code"] == FILE_FORM, "the stored code text is never rewritten"
    # The Plucker's records survive the save: _serialize reads them, so a
    # save placed any earlier in async_load would have dropped them.
    assert written["plucked_stores"] == stale["plucked_stores"]

    # Second boot, on exactly what the first one wrote.
    again = SignalStore(_hass())
    with patch.object(again, "_store") as mock_again:
        mock_again.async_load = AsyncMock(
            return_value=json.loads(json.dumps(written))
        )
        mock_again.async_save = AsyncMock()
        await again.async_load()

    assert mock_again.async_save.await_count == 0, "a clean boot writes nothing"
    assert again._dirty is False
    # The unrepairable row is still there on the second boot. Its
    # silence is the acceptance: present, re-read, and not a reason to
    # write.
    kept = {s.id: s for s in next(iter(again._devices.values())).signals}
    assert "unrepairable" in kept
    assert kept["unrepairable"].byte_hash is None
    assert "s1" in kept
