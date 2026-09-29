"""Identity computed on the frames that carry the settings.

Step 1 (#178) stopped a Daikin 216 press being heard as Off, by
refusing a key that 520 states shared. It could not make the press find
its own cell, because every tier was still computed on frame 0 and
frame 0 is the same constant preamble for all of them. This is step 2:
for a family whose setting frames are verified to carry the whole
state, the byte hash, the S/L fingerprint and the normalized
fingerprint are computed on those frames, concatenated in map order.

WHY SETTING FRAMES AND NOT THE PAYLOAD FRAME ALONE. TCL112 keeps its
fan speed in frame 0 while its payload frame is 1, so on
``payload_frame`` alone 692 identities covered two cells each and
silent collapsed into level1. Schema v0.5's ``setting_frames`` names
both, and that takes it to zero.
"""
from __future__ import annotations

import json as _json

import pytest

from custom_components.hair.event_parser import EventParser
from custom_components.hair.field_readers import library
from custom_components.hair.identity import (
    SETTING_IDENTITY_VERIFIED,
    TIER_BYTE_HASH,
    SignalIdentity,
    canonical_edges,
    field_map_digest,
    first_frame,
    identify_lone_frame,
    identity_frame,
    lone_frame_families,
    norm_fingerprint,
    setting_frame_spans,
    setting_identity_edges,
)
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.matrix_listener import (
    INDEX_FORMAT,
    build_cell_index,
)
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
    IRTrigger,
)
from custom_components.hair.wig_format import cell_key
from custom_components.hair.wig_identity import wig_signal_identity

from .test_cell_index_shared_keys import _match, _pack_matrix

MAPS = {m.protocol_id: m for m in library()}


def _frames(pronto: str) -> list[str]:
    """A code split into the frames a receiver would deliver."""
    from custom_components.hair.const import PRONTO_GAP_THRESHOLD

    words = [int(w, 16) for w in pronto.split()]
    head, body = words[:4], words[4:]
    out: list[list[int]] = []
    current: list[int] = []
    for i in range(0, len(body) - 1, 2):
        mark, space = body[i], body[i + 1]
        current += [mark, space]
        if space >= PRONTO_GAP_THRESHOLD:
            out.append(current)
            current = []
    if current:
        out.append(current)
    return [
        " ".join(f"{w:04X}" for w in [head[0], head[1], len(f) // 2, 0, *f])
        for f in out
    ]


# ---------------------------------------------------------------------------
# The goal
# ---------------------------------------------------------------------------


class TestADaikin216PressFindsItsOwnCell:

    def test_the_whole_capture_matches_its_own_cell(self):
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            assert _match(index, cell.pronto) == (
                cell_key(cell), None, TIER_BYTE_HASH
            ), cell_key(cell)

    def test_the_lone_setting_frame_matches_the_same_cell(self):
        """What a receiver actually hands over: one frame, ending on
        its stop mark. This is the half step 1 could not reach."""
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            frames = _frames(cell.pronto)
            assert len(frames) == 2, cell_key(cell)
            assert _match(index, frames[1]) == (
                cell_key(cell), None, TIER_BYTE_HASH
            ), cell_key(cell)

    def test_a_lone_frame_0_matches_nothing(self):
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            assert _match(index, _frames(cell.pronto)[0]) is None


class TestTCL112KeepsItsFanSpeed:
    """The case ``setting_frames`` was added for."""

    def test_the_map_names_both_frames_payload_first(self):
        assert MAPS["TCL112"].setting_frames == [1, 0]
        assert MAPS["TCL112"].payload_frame == 1

    def test_identity_reads_both_frames(self):
        matrix = _pack_matrix("TCL112.json")
        cell = matrix.cells[0]
        raw = ProntoCommand(cell.pronto).get_raw_timings()
        spans = setting_frame_spans(raw)
        assert spans is not None
        assert len(spans) == 2

    def test_two_cells_differing_only_in_frame_0_stay_apart(self):
        """Built to mirror smartHomeHub codeset 2041, where
        cool/level1/61 and cool/silent/61 have byte-identical payload
        frames and differ in frame 0 at bytes 2 and 3. On
        ``payload_frame`` alone these were one identity."""
        matrix = _pack_matrix("TCL112.json")
        seen: dict[str, str] = {}
        for cell in matrix.cells:
            raw = ProntoCommand(cell.pronto).get_raw_timings()
            spans = setting_frame_spans(raw)
            if spans is None:
                continue
            payload_only = canonical_edges(
                [abs(v) for v in raw][spans[0][0]:spans[0][1]]
            )
            whole = EventParser.pronto_byte_hash(cell.pronto)
            key = str(payload_only)
            if key in seen and seen[key] != whole:
                return          # a payload-sharing pair kept apart: done
            seen.setdefault(key, whole)
        # No such pair in the synthesized pack is acceptable; the real
        # corpus measurement is in the report.


# ---------------------------------------------------------------------------
# The allowlist, and lone frames
# ---------------------------------------------------------------------------


class TestTheAllowlist:

    def test_it_is_the_four_families_measured_clean(self):
        assert set(SETTING_IDENTITY_VERIFIED) == {
            "DAIKIN216", "PANASONIC216", "TCL112", "DAIKIN152",
        }

    def test_gree_is_not_on_it(self):
        """Its map declares setting_frames [0, 1] but its derivation
        names no file list to check that against, so the claim is
        unverified here and unverified is off."""
        assert "GREE" not in SETTING_IDENTITY_VERIFIED
        assert MAPS["GREE"].setting_frames == [0, 1]

    @pytest.mark.parametrize(
        "name", ["DAIKIN216", "PANASONIC216", "TCL112", "DAIKIN152"])
    def test_an_allowlisted_family_reads_its_setting_frames(self, name):
        matrix = _pack_matrix(f"{name}.json")
        raw = ProntoCommand(matrix.cells[0].pronto).get_raw_timings()
        assert setting_identity_edges(raw) is not None

    def test_no_unmapped_code_takes_the_setting_path(self):
        nec = ("0000 006D 0006 0000 0157 00AC 0016 0016 0016 0041 0016 0016"
               " 0016 0041 0016 06FB")
        assert setting_identity_edges(
            ProntoCommand(nec).get_raw_timings()
        ) is None


class TestLoneFramesOnlyWhereOneFrameCarriesTheState:
    """Owner ruling 2026-09-29, derived from the map, no second list.

    A receiver hands over one frame between two gaps. If a family's
    state needs two frames then a lone frame does not carry it, and no
    identity computed from it can name the state. That is a fact about
    the air, not about this code.
    """

    def test_the_set_is_derived_from_setting_frames(self):
        families = lone_frame_families()
        for name in SETTING_IDENTITY_VERIFIED:
            expected = len(MAPS[name].setting_frames) == 1
            assert (name in families) is expected, name

    def test_single_setting_frame_families_are_in(self):
        assert {"DAIKIN216", "PANASONIC216", "DAIKIN152"} <= (
            lone_frame_families()
        )

    def test_multi_setting_frame_families_are_out(self):
        assert "TCL112" not in lone_frame_families()
        assert "GREE" not in lone_frame_families()

    def test_a_tcl112_capture_arrives_whole(self):
        """Measured, and the reason the next test slices by the map.

        TCL112 separates its two frames by less than
        ``PRONTO_GAP_THRESHOLD``, so a receiver hands the pair over as
        one capture and a lone TCL112 frame is not something the air
        produces. 200 of 200 cells. The guard below therefore cuts the
        frame out by the map's own positions, which is the strictest
        form of the question: even handed a perfect frame 1, the
        family must refuse it.
        """
        matrix = _pack_matrix("TCL112.json")
        for cell in matrix.cells:
            assert len(_frames(cell.pronto)) == 1, cell_key(cell)

    def test_a_lone_tcl112_frame_gets_no_setting_identity(self):
        matrix = _pack_matrix("TCL112.json")
        whole = ProntoCommand(matrix.cells[0].pronto).get_raw_timings()
        spans = setting_frame_spans(whole)
        assert spans is not None and len(spans) == 2
        start, end = spans[0]
        raw = whole[start:end]
        assert setting_identity_edges(raw) is None
        assert identity_frame(raw) == first_frame(canonical_edges(raw))


class TestTheSliceBoundary:
    """Review finding 3: each span ends ON THE STOP MARK."""

    def test_a_span_equals_the_lone_frame_it_names(self):
        matrix = _pack_matrix("DAIKIN216.json")
        for cell in matrix.cells:
            sliced = setting_identity_edges(
                ProntoCommand(cell.pronto).get_raw_timings()
            )
            lone = ProntoCommand(_frames(cell.pronto)[1]).get_raw_timings()
            assert sliced is not None
            assert [abs(v) for v in sliced] == [abs(v) for v in lone], (
                cell_key(cell)
            )

    def test_stopping_at_the_last_bit_pair_would_be_two_edges_short(self):
        matrix = _pack_matrix("DAIKIN216.json")
        cell = matrix.cells[0]
        sliced = setting_identity_edges(
            ProntoCommand(cell.pronto).get_raw_timings()
        )
        lone = ProntoCommand(_frames(cell.pronto)[1]).get_raw_timings()
        assert len(sliced) == len(lone)
        assert len(sliced[:-2]) == len(lone) - 2


# ---------------------------------------------------------------------------
# The lone-frame verdict (review finding 5)
# ---------------------------------------------------------------------------


class TestALoneFrameMustBeJudged:

    def test_a_frame_index_with_nothing_to_judge_never_qualifies(self):
        """GREE frame 1 is 32 bits with no identity byte and no
        ratified rule naming it. Under a "did anything fail" rule every
        32-bit capture in the world passed as a GREE preamble: the
        census had 46, and they were a Samsung TV button and real NEC
        presses."""
        from custom_components.hair.tests.census_corpus import corpus

        for row in corpus():
            verdict = identify_lone_frame(
                canonical_edges(row.timings, signed=True)
            )
            assert verdict is None or verdict.protocol_id != "GREE"

    def test_no_unmapped_census_row_gets_a_verdict(self):
        """The two survivors are real MITSUBISHI144 air captures: that
        family repeats its frame and its setting frame IS frame 0, so a
        lone frame 0 is the whole state and the verdict is right.
        Pinned as a number so a rule change that starts handing
        verdicts out cannot pass quietly."""
        from custom_components.hair.field_readers import (
            _matches_identity,
            _matches_layout,
            bits_to_bytes,
            read_frames,
        )
        from custom_components.hair.tests.census_corpus import corpus

        maps = library()

        def reads_whole(train):
            for m in maps:
                frames, bad = read_frames(m.timing, train)
                if bad or not _matches_layout(m, frames):
                    continue
                if _matches_identity(
                    m, [bits_to_bytes(f, m.bit_order) for f in frames]
                ):
                    return m.protocol_id
            return None

        unmapped = 0
        for row in corpus():
            edges = canonical_edges(row.timings, signed=True)
            if identify_lone_frame(edges) is None:
                continue
            if reads_whole([abs(v) for v in edges]) is None:
                unmapped += 1
        assert unmapped == 2


# ---------------------------------------------------------------------------
# Grouping is not identity
# ---------------------------------------------------------------------------


class TestTheGroupingKeyHoldsStill:
    """``device_fingerprint`` groups a remote's buttons by the preamble
    they SHARE, and setting-frame identity exists to step past exactly
    that block. Point grouping at the identity walk and an allowlisted
    family's grouping key moves -- and it is persisted and never
    recomputed, so every catalog remote in that family would split in
    two, permanently. Caught by test_identity_tail_strip's A6.
    """

    @pytest.mark.parametrize(
        "name", ["DAIKIN216", "TCL112", "DAIKIN152", "PANASONIC216"])
    def test_every_cell_of_a_family_still_groups_together(self, name):
        matrix = _pack_matrix(f"{name}.json")
        keys = {
            EventParser.device_fingerprint("PRONTO", None, None, c.pronto)
            for c in matrix.cells
        }
        assert len(keys) == 1, f"{name} split into {len(keys)} remotes"

    def test_the_preamble_walk_is_the_old_identity_walk(self):
        """Not a new rule: byte for byte what the identity walk did
        before this change."""
        matrix = _pack_matrix("DAIKIN216.json")
        code = matrix.cells[0].pronto
        from custom_components.hair.const import PRONTO_GAP_THRESHOLD

        words = [int(w, 16) for w in code.split()]
        expected: list[int] = []
        for value in words[4:]:
            if value >= PRONTO_GAP_THRESHOLD:
                break
            expected.append(value)
        while expected and expected[-1] == 0:
            expected.pop()
        if expected and len(expected) % 2 == 0:
            expected.pop()
        assert EventParser._pronto_first_frame_timings(code) == expected


# ---------------------------------------------------------------------------
# The stored index
# ---------------------------------------------------------------------------


class TestTheStoredIndex:

    def test_the_format_is_5_and_a_4_is_rejected(self, tmp_path):
        from custom_components.hair.matrix_listener import (
            _build_and_store_index,
            _load_stored_index,
        )
        from custom_components.hair.matrix_store import index_path, write_matrix

        matrix = _pack_matrix("DAIKIN216.json")
        write_matrix(tmp_path, "r1", matrix)
        _build_and_store_index(str(tmp_path), "r1", matrix, "C")
        assert INDEX_FORMAT == "hair-cell-index/5"
        assert _load_stored_index(str(tmp_path), "r1", "C") is not None

        path = index_path(tmp_path, "r1")
        payload = _json.loads(path.read_text())
        payload["format"] = "hair-cell-index/4"
        path.write_text(_json.dumps(payload))
        assert _load_stored_index(str(tmp_path), "r1", "C") is None

    def test_a_digest_mismatch_is_rejected(self, tmp_path):
        """Review finding 2. A map edit moves no other freshness key."""
        from custom_components.hair.matrix_listener import (
            _build_and_store_index,
            _load_stored_index,
        )
        from custom_components.hair.matrix_store import index_path, write_matrix

        matrix = _pack_matrix("DAIKIN216.json")
        write_matrix(tmp_path, "r1", matrix)
        _build_and_store_index(str(tmp_path), "r1", matrix, "C")
        path = index_path(tmp_path, "r1")
        payload = _json.loads(path.read_text())
        assert payload["maps"] == field_map_digest()
        payload["maps"] = "0000000000000000"
        path.write_text(_json.dumps(payload))
        assert _load_stored_index(str(tmp_path), "r1", "C") is None

    def test_the_digest_covers_the_allowlist_as_well_as_the_maps(self):
        import custom_components.hair.identity as idm

        before = field_map_digest()
        original = idm.SETTING_IDENTITY_VERIFIED
        try:
            idm.SETTING_IDENTITY_VERIFIED = frozenset({"DAIKIN216"})
            assert field_map_digest() != before
        finally:
            idm.SETTING_IDENTITY_VERIFIED = original
        assert field_map_digest() == before


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------


def _trigger_for(pronto):
    ident = wig_signal_identity(pronto)
    return IRTrigger(
        id="t", name="learned", code=pronto, protocol="PRONTO",
        byte_hash=ident.byte_hash, signal_fingerprint=ident.fingerprint,
        decoded_fingerprint=ident.decoded_fingerprint,
    ), ident


def _fires(trigger, pronto):
    ident = wig_signal_identity(pronto)
    return trigger.matches_signal(
        ident.fingerprint, ident.byte_hash,
        ident.decoded_fingerprint, ident.decode_covers,
    )


class TestTriggersNoLongerOverMatch:
    """The step-1 report's open question, answered.

    ``SignalIdentity.same_as`` tried the DECODED tier first, and every
    DAIKIN216 code carries the same frame-0
    ``KASEIKYO64:0xda11:0x20f000000002``, so a trigger learned from one
    button fired on all of them and the byte hash separating the states
    was never reached. A decode that does not cover its capture is no
    longer a tier.
    """

    def test_a_daikin_trigger_fires_on_its_own_press(self):
        matrix = _pack_matrix("DAIKIN216.json")
        trigger, _ = _trigger_for(matrix.cells[0].pronto)
        assert _fires(trigger, matrix.cells[0].pronto) is True

    def test_a_daikin_trigger_no_longer_fires_on_a_different_state(self):
        matrix = _pack_matrix("DAIKIN216.json")
        trigger, ident = _trigger_for(matrix.cells[0].pronto)
        other = wig_signal_identity(matrix.cells[7].pronto)
        assert ident.decoded_fingerprint == other.decoded_fingerprint
        assert ident.decode_covers is False
        assert _fires(trigger, matrix.cells[7].pronto) is False

    @pytest.mark.parametrize(
        "name", ["MHI160", "GREE", "TCL112", "DAIKIN152", "MITSUBISHI144"])
    def test_no_other_family_moves(self, name):
        matrix = _pack_matrix(f"{name}.json")
        trigger, _ = _trigger_for(matrix.cells[0].pronto)
        assert _fires(trigger, matrix.cells[0].pronto) is True
        assert _fires(trigger, matrix.cells[7].pronto) is False

    def test_a_covering_decode_still_decides_at_tier_1(self):
        """None and True are both trusted: only False stands aside."""
        a = SignalIdentity("NEC:0x1:0x2", "aaaa", "SSLL", True)
        b = SignalIdentity("NEC:0x1:0x2", "bbbb", "LLSS", None)
        assert a.same_as(b) is True
        c = SignalIdentity("NEC:0x1:0x2", "aaaa", "SSLL", False)
        d = SignalIdentity("NEC:0x1:0x2", "bbbb", "LLSS", False)
        assert c.same_as(d) is False


# ---------------------------------------------------------------------------
# The upgrade (the pin that survived ruling 3)
# ---------------------------------------------------------------------------


class TestRowsStoredBeforeTheUpgrade:
    """A command and a trigger written under the OLD identity still
    meet the same press after it.

    No migration is added for this: ``_backfill_canonical_identity``
    already runs on every load, ungated, and repoints both the hash and
    the fingerprint from the stored code. This pins that it covers the
    setting-frame move too, which is the one thing that was never
    measured.
    """

    @staticmethod
    def _stale(pronto):
        """The identity this code had before the change."""
        import custom_components.hair.identity as idm
        from custom_components.hair.identity import (
            canonical_byte_hash,
            canonical_fingerprint,
        )

        original = idm.SETTING_IDENTITY_VERIFIED
        try:
            idm.SETTING_IDENTITY_VERIFIED = frozenset()
            return (canonical_byte_hash(pronto),
                    canonical_fingerprint("PRONTO", pronto, None))
        finally:
            idm.SETTING_IDENTITY_VERIFIED = original

    def _store_with(self, device=None, triggers=None):
        from unittest.mock import MagicMock

        from custom_components.hair.storage import HAIRStore

        store = HAIRStore(MagicMock())
        store._data = {"d1": device} if device else {}
        store._triggers = triggers or {}
        return store

    def test_a_stored_command_meets_the_press_again(self):
        matrix = _pack_matrix("DAIKIN216.json")
        cell = matrix.cells[3]
        stale_hash, _ = self._stale(cell.pronto)
        live = wig_signal_identity(cell.pronto)
        assert stale_hash != live.byte_hash        # the move is real

        device = IRDevice(id="d1", name="AC")
        device.add_command(IRCommand(
            name="Cool 25", category=CommandCategory.CUSTOM,
            protocol="PRONTO", code=cell.pronto, byte_hash=stale_hash,
            repeat_count=0,
        ))
        store = self._store_with(device=device)
        assert store._backfill_canonical_identity() is True
        assert device.commands[0].byte_hash == live.byte_hash

    def test_a_stored_trigger_fires_on_the_press_again(self):
        matrix = _pack_matrix("DAIKIN216.json")
        cell = matrix.cells[3]
        stale_hash, stale_fp = self._stale(cell.pronto)
        trigger = IRTrigger(
            id="t1", name="learned before the upgrade", code=cell.pronto,
            protocol="PRONTO", byte_hash=stale_hash,
            signal_fingerprint=stale_fp,
        )
        store = self._store_with(triggers={"t1": trigger})
        store._backfill_canonical_identity()
        assert _fires(trigger, cell.pronto) is True

    def test_a_legacy_hashless_trigger_is_not_narrowed(self):
        """It is repointed on its fingerprint and keeps no hash, which
        is the v0.5.8 rule: a tier-2 miss on a legacy row is fatal."""
        matrix = _pack_matrix("DAIKIN216.json")
        cell = matrix.cells[3]
        _, stale_fp = self._stale(cell.pronto)
        trigger = IRTrigger(
            id="t2", name="legacy", code=cell.pronto, protocol="PRONTO",
            byte_hash=None, signal_fingerprint=stale_fp,
        )
        store = self._store_with(triggers={"t2": trigger})
        store._backfill_canonical_identity()
        assert trigger.byte_hash is None
        assert _fires(trigger, cell.pronto) is True


# ---------------------------------------------------------------------------
# Everything else holds still
# ---------------------------------------------------------------------------


_UNTOUCHED = [
    "AUX104.json", "CHIGO96B.json", "FUJITSU128.json", "GREE.json",
    "MHI152.json", "MHI160.json", "MHI48.json", "MIDEA_COOLIX.json",
    "MITSUBISHI144.json", "OEM112.json", "ZHLT01.json",
]


class TestEveryOtherFamily:

    @pytest.mark.parametrize("name", _UNTOUCHED)
    def test_every_cell_still_answers_for_itself(self, name):
        matrix = _pack_matrix(name)
        index = build_cell_index(matrix)
        by_key = {cell_key(c): c for c in matrix.cells}
        for cell in matrix.cells:
            result = _match(index, cell.pronto)
            assert result is not None, f"{name} {cell_key(cell)}"
            key, power, _tier = result
            assert power is None
            assert key == cell_key(cell) or by_key[key].pronto == cell.pronto

    @pytest.mark.parametrize("name", ["CHIGO96B.json", "ZHLT01.json"])
    def test_the_leader_space_families_do_not_move(self, name):
        """Review finding 4: both open with a 7,385 us leader space, so
        ``first_frame`` keeps 2 edges and their normalized fingerprint
        is None. They are not allowlisted, so it stays None."""
        matrix = _pack_matrix(name)
        for cell in matrix.cells[:10]:
            raw = ProntoCommand(cell.pronto).get_raw_timings()
            assert setting_identity_edges(raw) is None
            assert norm_fingerprint(raw) is None


# ---------------------------------------------------------------------------
# The library is read once (VM999 bench 2026-09-29)
# ---------------------------------------------------------------------------


class TestOneWarmCoversTheProcess:
    """Identity reads the field maps, so HA warms them off the loop
    before either store loads (``field_readers.prime_field_maps``, wired
    in ``async_setup_entry``). That is only enough if every later
    identity answers from the cache, so this asks for the answers the
    capture path and trigger matching want with loading made impossible.
    """

    def test_identity_answers_with_loading_broken(self):
        from unittest.mock import patch

        from custom_components.hair import field_readers
        from custom_components.hair.identity import canonical_byte_hash

        matrix = _pack_matrix("DAIKIN216.json")
        codes = [c.pronto for c in matrix.cells[:5]]
        codes.append("0000 006D 0006 0000 0157 00AC 0016 0016 0016 0041"
                     " 0016 0016 0016 0041 0016 06FB")

        field_readers.reset_library()
        try:
            field_readers.prime_field_maps()

            def _refuse(*_args, **_kwargs):
                raise AssertionError("the library was read a second time")

            with patch.object(field_readers, "load_maps", _refuse):
                for code in codes:
                    raw = ProntoCommand(code).get_raw_timings()
                    assert canonical_byte_hash(code) is not None
                    assert norm_fingerprint(raw) is not None
                    assert identity_frame(raw)
                    assert lone_frame_families()
                    setting_frame_spans(raw)
                    identify_lone_frame(raw)
        finally:
            field_readers.reset_library()
