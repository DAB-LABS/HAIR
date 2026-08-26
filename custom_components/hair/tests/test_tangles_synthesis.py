"""One press, N codes -- and the wall that keeps it honest.

Four Komeco cells claim 19 degrees and no code anywhere in that wig
reads as 19, so no donor exists and none can be invented. What CAN
happen is this: the person sets their own remote to 19, presses it once,
and that capture witnesses what 19 looks like on their hardware. Every
remaining cell is then built from its own healthy sibling with only the
witnessed field rewritten.

The map could compute that byte on its own and is deliberately not
allowed to. A value nobody demonstrated is a value nobody checked, and
unreadable-never-guessed does not bend because the arithmetic happens to
be easy. The witness is the authorization, not the arithmetic.

Two walls hold this up. The map must vouch for BOTH the field being
rewritten and every rule that proves the frame, or the whole run
declines. And every candidate is put back through the same reader that
judged the cell in the first place -- a candidate that fails its own
read-back raises, because that is a defect in the synthesis and not a
result to hand anybody.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from custom_components.hair import field_readers
from custom_components.hair.models import IRDevice
from custom_components.hair.tangles import (
    ORIGIN_CAPTURE,
    ORIGIN_SYNTHESIZED,
    SYNTH_FIELD_PROVISIONAL,
    SYNTH_NO_WITNESS,
    SYNTH_RULE_PROVISIONAL,
    SYNTH_UNREADABLE,
    SynthesisBug,
    list_tangles,
    pre_read,
    read_lattice,
    rewrite_field,
    synthesize,
)
from custom_components.hair.wig_comb import comb_wig
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

AIMED = "cell:heat_cool/medium/off/19"


def _fresh() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture
def komeco() -> Wig:
    return _fresh()


def _cells(wig: Wig) -> dict:
    return {cell_key(cell): cell for cell in wig.climate.cells}


def _witness(lattice, wig: Wig, degrees: float = 19.0) -> str:
    """A capture that reads as ``degrees`` on this device's hardware.

    Stands in for the press. Built from a healthy cell of the same
    column so it carries this remote's own timings, which is exactly
    what a real capture would carry.
    """
    spec = lattice.spec_for("temperature")
    source = _cells(wig)["heat_cool/medium/off/16"]
    built = rewrite_field(
        lattice.field_map, source.pronto, spec,
        field_readers.expected_value(spec, degrees),
    )
    assert built is not None
    return built


def _witness_card(wig: Wig):
    device = IRDevice(name="Komeco", climate_matrix=True)
    listing = list_tangles(device, wig.climate)
    card = next(c for c in listing.clusters if c.mechanic == "witness")
    return [row for row in listing.rows if row.id in card.members]


class TestRewritingOneFieldInPlace:
    def test_the_rewrite_reads_back_as_what_was_asked_for(self, komeco):
        lattice = read_lattice(komeco.climate)
        built = _witness(lattice, komeco, 19.0)
        assert pre_read(lattice, built).reads_as["temperature"] == 19.0

    def test_the_checksum_is_recomputed_not_left_stale(self, komeco):
        """A frame carries its own proof. Rewriting a field and leaving
        the complement bytes behind would produce a frame most receivers
        throw away."""
        lattice = read_lattice(komeco.climate)
        built = _witness(lattice, komeco, 19.0)
        assert pre_read(lattice, built).integrity == {"complement_pairs": True}

    def test_everything_it_does_not_change_is_untouched(self, komeco):
        """Not a rendering. The pulses this does not touch are the words
        that arrived from the device, identical down to the hex."""
        lattice = read_lattice(komeco.climate)
        source = _cells(komeco)["heat_cool/medium/off/16"]
        built = _witness(lattice, komeco, 19.0)
        before = source.pronto.split()
        after = built.split()
        assert len(before) == len(after)
        assert before[:4] == after[:4]
        changed = [i for i, (a, b) in enumerate(zip(before, after,
                                                    strict=True)) if a != b]
        assert changed
        assert len(changed) < len(before) // 4

    def test_the_changed_pulses_look_like_the_ones_beside_them(self, komeco):
        """Widths come from this code's own median zero and one, so a
        synthesized frame stays a member of the family it came from."""
        lattice = read_lattice(komeco.climate)
        source = _cells(komeco)["heat_cool/medium/off/16"]
        built = _witness(lattice, komeco, 19.0)
        original = {int(w, 16) for w in source.pronto.split()[4:]}
        assert all(int(w, 16) in original for w in built.split()[4:])

    def test_a_recomputed_rule_satisfies_the_reader_that_checks_it(
            self, komeco):
        """THE coupling pin. The repair mirrors check_integrity's
        arithmetic rather than importing it, because one asks and the
        other answers. If they ever drift, this fails."""
        lattice = read_lattice(komeco.climate)
        built = _witness(lattice, komeco, 19.0)
        reading = field_readers.read_code(
            built, [lattice.field_map], prefer=lattice.field_map.protocol_id)
        for rule in lattice.field_map.integrity:
            if rule.ratified:
                assert field_readers.check_integrity(reading, rule) is True


class TestTheWitnessedCard:
    def test_one_press_completes_all_four(self, komeco):
        lattice = read_lattice(komeco.climate)
        rows = _witness_card(komeco)
        assert len(rows) == 4
        result = synthesize(
            lattice, rows, _witness(lattice, komeco), "temperature",
            witness_target=AIMED,
        )
        assert result.refused is None
        assert result.declined == {}
        assert len(result.candidates) == 4

    def test_only_the_aimed_cell_gets_the_capture(self, komeco):
        """The bug this rule exists for, pinned.

        Four cells needing 19 differ by SWING, and ZHLT01 marks swing
        provisional. Handing all four the captured frame produced four
        candidates that passed their own read-back while three carried
        the wrong swing: the reader can only check what the map
        ratifies. So every cell nobody aimed at is built from its own
        sibling, which is right on every axis by construction.
        """
        lattice = read_lattice(komeco.climate)
        rows = _witness_card(komeco)
        result = synthesize(
            lattice, rows, _witness(lattice, komeco), "temperature",
            witness_target=AIMED,
        )
        assert result.candidates[AIMED]["origin"] == ORIGIN_CAPTURE
        others = [c for rid, c in result.candidates.items() if rid != AIMED]
        assert len(others) == 3
        assert {c["origin"] for c in others} == {ORIGIN_SYNTHESIZED}
        assert len({c["pronto"] for c in result.candidates.values()}) == 4

    def test_each_cell_is_built_from_its_own_swing(self, komeco):
        lattice = read_lattice(komeco.climate)
        rows = _witness_card(komeco)
        result = synthesize(
            lattice, rows, _witness(lattice, komeco), "temperature",
            witness_target=AIMED,
        )
        for row_id, candidate in result.candidates.items():
            if candidate["origin"] != ORIGIN_SYNTHESIZED:
                continue
            swing = row_id.rsplit("/", 2)[-2]
            assert candidate["sibling"].split("/")[2] == swing

    def test_the_provenance_names_the_witness_and_the_sibling(self, komeco):
        lattice = read_lattice(komeco.climate)
        rows = _witness_card(komeco)
        witness = _witness(lattice, komeco)
        result = synthesize(
            lattice, rows, witness, "temperature", witness_target=AIMED)
        assert result.witness["reads_as"] == 19.0
        assert result.witness["field"] == "temperature"
        for candidate in result.candidates.values():
            assert candidate["witness_digest"] == result.witness["digest"]
            assert candidate["witness_field"] == "temperature"

    def test_every_candidate_reads_back_as_its_own_cell(self, komeco):
        lattice = read_lattice(komeco.climate)
        rows = _witness_card(komeco)
        result = synthesize(
            lattice, rows, _witness(lattice, komeco), "temperature",
            witness_target=AIMED)
        for row in rows:
            verdict = result.candidates[row.id]["verdict"]
            assert verdict["matches"] is True
            assert verdict["reads_as"]["temperature"] == 19.0


class TestTheWall:
    def test_a_provisional_field_declines_the_whole_run(self, komeco):
        """The Galanz class stays untouchable. A field the map will not
        vouch for cannot decide what a frame should carry."""
        lattice = read_lattice(komeco.climate)
        spec = lattice.spec_for("temperature")
        demoted = replace(spec, confidence="provisional")
        lattice.field_map = replace(
            lattice.field_map,
            fields=[demoted if f.name == "temperature" else f
                    for f in lattice.field_map.fields],
        )
        result = synthesize(
            lattice, _witness_card(komeco), "0000 006D", "temperature")
        assert result.refused == SYNTH_FIELD_PROVISIONAL
        assert result.candidates == {}

    def test_the_class_this_protects_is_real(self):
        """Not a hypothetical gate. OEM112 ships with a provisional
        temperature over 970 disagreeing cells in five corpus files, and
        that is precisely the family synthesis must not touch."""
        oem = next(m for m in field_readers.library()
                   if m.protocol_id == "OEM112")
        assert oem.field_named("temperature").ratified is False

    def test_a_provisional_integrity_rule_declines_the_whole_run(
            self, komeco):
        """A recomputed frame whose proof the map doubts is a guess
        wearing a checksum."""
        lattice = read_lattice(komeco.climate)
        lattice.field_map = replace(
            lattice.field_map,
            integrity=[replace(rule, confidence="provisional")
                       for rule in lattice.field_map.integrity],
        )
        result = synthesize(
            lattice, _witness_card(komeco), "0000 006D", "temperature")
        assert result.refused == SYNTH_RULE_PROVISIONAL

    def test_the_families_that_rule_protects_are_real(self):
        provisional = {
            m.protocol_id for m in field_readers.library()
            if any(not rule.ratified for rule in m.integrity)
        }
        assert {"GREE", "MHI48", "MHI160"} <= provisional

    def test_a_capture_that_reads_as_something_else_witnesses_nothing(
            self, komeco):
        """The user pressed 18 when we asked for 19. Nothing is
        synthesized from a value nobody demonstrated."""
        lattice = read_lattice(komeco.climate)
        result = synthesize(
            lattice, _witness_card(komeco),
            _witness(lattice, komeco, 24.0), "temperature",
            witness_target=AIMED,
        )
        assert result.refused == SYNTH_NO_WITNESS
        assert result.candidates == {}

    def test_an_unreadable_capture_witnesses_nothing(self, komeco):
        lattice = read_lattice(komeco.climate)
        result = synthesize(
            lattice, _witness_card(komeco),
            "0000 006D 0002 0000 0060 0020 0020 0060", "temperature",
        )
        assert result.refused == SYNTH_NO_WITNESS

    def test_no_lattice_refuses(self, komeco):
        result = synthesize(
            read_lattice(None), _witness_card(komeco), "x", "temperature")
        assert result.refused == SYNTH_UNREADABLE

    def test_a_candidate_that_fails_its_own_read_back_raises(
            self, komeco, monkeypatch):
        """Raised, never returned. A synthesized frame that does not read
        as the cell it was built for is a defect in this module, and
        handing it back as a result would put it in front of somebody as
        a repair."""
        lattice = read_lattice(komeco.climate)
        wrong = _cells(komeco)["heat_cool/medium/off/28"].pronto
        monkeypatch.setattr(
            "custom_components.hair.tangles.rewrite_field",
            lambda *args, **kwargs: wrong,
        )
        with pytest.raises(SynthesisBug):
            synthesize(
                lattice, _witness_card(komeco), _witness(lattice, komeco),
                "temperature", witness_target=AIMED,
            )


class TestTheWholeRepair:
    def test_donors_plus_one_witness_leave_the_lattice_clean(self, komeco):
        """The owner's loop, proven on the real file.

        Every donor resolved against the lattice as it stands, the four
        witnessed cells synthesized from one press, all 52 written at
        once -- and the comb comes back with nothing at all. Neither
        half gets there alone: donors leave the bottom of the range
        untouched and twinned against it, and the witness alone leaves
        the other 48 lying.
        """
        lattice = read_lattice(komeco.climate)
        device = IRDevice(name="Komeco", climate_matrix=True)
        listing = list_tangles(device, komeco.climate)
        rows = _witness_card(komeco)
        result = synthesize(
            lattice, rows, _witness(lattice, komeco), "temperature",
            witness_target=AIMED)

        plan = {row.target.key: row.donor["pronto"]
                for row in listing.rows if row.has_donor}
        for row_id, candidate in result.candidates.items():
            plan[row_id.split(":", 1)[1]] = candidate["pronto"]
        assert len(plan) == 52

        cells = _cells(komeco)
        for key, pronto in plan.items():
            cells[key].pronto = pronto

        assert comb_wig(komeco).findings == []
        assert list_tangles(device, komeco.climate).rows == []
