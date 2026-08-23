"""The field sweep: what the lattice claims against what it sends.

Release two, and the answer to the WigShop's second case. The Komeco
file is the acceptance fixture and the number is not negotiable: 52
cells, the `heat_cool` column at fan `medium`, sending T+1 from 19
through 31 on all four swing modes. Structurally flawless, semantically
wrong, and invisible to every check HAIR had.

The three rules that decide what the sweep may say, each pinned below:

- **Ratified fields only.** ZHLT01's mode vocabulary is provisional
  because its own family disagrees about it, and the Komeco lattice
  follows the minority reading. Sweeping it would bury the 52 real
  findings under 1,156 false ones.
- **`mode_traits` is three-state**, and the third state is decided per
  WIG. `heat_cool` is `file_dependent`: frozen in some files of the
  family, a real setpoint in others. Here it moves, so it is checked,
  and that is what surfaces the column.
- **Anything the map cannot express is coverage.** A label outside the
  vocabulary, a temperature outside the domain, a protocol no map
  claims: all of them are counted and named, never guessed and never
  quietly passed.

The synthesized packs under `fixtures/field-packs/` are the breadth
test: twelve families, each with a clean lattice that must produce
nothing and a defects lattice that must produce exactly what was
planted in it and nothing else.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair.wig_adapters import _broadlink_b64_to_pronto
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_INTEGRITY,
    comb_wig,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    parse_wig,
)

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
PACKS = FIXTURES / "field-packs"

# The Komeco defect, as the WigShop brief describes it: heat_cool at fan
# medium, 19 through 31, on all four swing modes.
KOMECO_DEFECT_MODE = "heat_cool"
KOMECO_DEFECT_FAN = "medium"


def _komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


def _pack_wig(name: str) -> Wig:
    """A matrix wig from a synthesized fixture pack.

    Built here rather than through the SmartIR adapter because the packs
    carry no "off" command: they are field-map fixtures, not remotes,
    and HAIR's importer rightly refuses a climate file without one. The
    matrix borrows a cell's code for the off slot, so tests below ignore
    the row keyed "off".
    """
    raw = json.loads((PACKS / name).read_text())
    cells: list[ClimateCell] = []
    for mode, by_fan in raw["commands"].items():
        if not isinstance(by_fan, dict):
            continue
        for fan, level in by_fan.items():
            if isinstance(level, str):
                cells.append(ClimateCell(
                    mode=mode, fan=fan,
                    pronto=_broadlink_b64_to_pronto(level) or ""))
                continue
            for key, value in level.items():
                if isinstance(value, str):
                    cells.append(ClimateCell(
                        mode=mode, fan=fan, temp=float(key),
                        pronto=_broadlink_b64_to_pronto(value) or ""))
                    continue
                for temp, code in value.items():
                    cells.append(ClimateCell(
                        mode=mode, fan=fan, swing=key, temp=float(temp),
                        pronto=_broadlink_b64_to_pronto(code) or ""))
    matrix = ClimateMatrix(
        min_temp=float(raw.get("minTemperature", 16)),
        max_temp=float(raw.get("maxTemperature", 30)),
        precision=float(raw.get("precision", 1)),
        off=cells[0].pronto,
        cells=cells,
    )
    return Wig(name=name, signals=[], climate=matrix)


def _findings(wig: Wig, check: str) -> list:
    return [f for f in comb_wig(wig).findings
            if f.check == check and f.keys[:1] != ["off"]]


def _coverage(wig: Wig) -> dict:
    return comb_wig(wig).coverage.to_dict()


# ---------------------------------------------------------------------------
# The acceptance fixture
# ---------------------------------------------------------------------------


class TestTheKomecoLattice:
    def test_it_finds_exactly_the_fifty_two(self):
        assert len(_findings(_komeco(), CHECK_FIELD_MISMATCH)) == 52

    def test_and_they_are_the_column_the_brief_names(self):
        for finding in _findings(_komeco(), CHECK_FIELD_MISMATCH):
            mode, fan, _swing, temp = finding.keys[0].split("/")
            assert mode == KOMECO_DEFECT_MODE
            assert fan == KOMECO_DEFECT_FAN
            assert 19 <= float(temp) <= 31

    def test_every_finding_shows_its_vote(self):
        """Expected against read, in the field the map names, with the
        protocol that read it. A finding nobody can check is not worth
        filing (the brief's show-the-reasoning constraint)."""
        finding = _findings(_komeco(), CHECK_FIELD_MISMATCH)[0]
        assert finding.params["protocol"] == "ZHLT01"
        assert finding.params["field"] == "comb.field.temperature"
        assert finding.params["expected"] != finding.params["read"]

    def test_the_lattice_is_identified_and_read_whole(self):
        protocol = _coverage(_komeco())["protocol"]
        assert protocol["id"] == "ZHLT01"
        assert protocol["readable"] == protocol["codes"] == 1157

    def test_its_integrity_rule_holds_on_every_cell(self):
        """The contributor's file passes ZHLT01's six complement pairs
        on all 1,156 cells and the off code. The sweep must agree: this
        defect is semantic, and a structural finding here would mean the
        reader was wrong rather than the file."""
        report = comb_wig(_komeco())
        assert not [f for f in report.findings
                    if f.check == CHECK_FRAME_INTEGRITY]
        checks = report.coverage.to_dict()["checks"]
        assert checks[CHECK_FRAME_INTEGRITY]["checked"] == 1157

    def test_the_provisional_mode_vocabulary_is_not_swept(self):
        """ZHLT01's own family disagrees about `fan_only` and
        `heat_cool`, so the map marks mode provisional and the Komeco
        file follows the minority reading. Sweeping it would file over a
        thousand findings that say nothing about this wig."""
        fields = _coverage(_komeco())["fields"]
        assert fields["mode"]["checked"] == 0
        assert fields["mode"]["declined"][fr.NOT_RATIFIED] == 1156

    def test_the_ratified_fields_are_swept(self):
        fields = _coverage(_komeco())["fields"]
        assert fields["temperature"]["checked"] > 0
        assert fields["power"]["checked"] == 1157


# ---------------------------------------------------------------------------
# The three-state temperature rule
# ---------------------------------------------------------------------------


class TestFileDependentModes:
    """`file_dependent` is decided per wig, by looking at the wig.

    ZHLT01 marks `dry`, `fan_only` and `heat_cool` file_dependent:
    frozen in some files of the family, a real setpoint in others. The
    map cannot say which a given wig does, and guessing either way costs
    something real -- skip and miss a shifted column, check and invent
    one. `cool` and `heat` are not in that state: the map says they vary
    in every file it was derived from, so a frozen column there is a
    defect rather than a dialect.
    """

    def test_a_moving_file_dependent_mode_is_checked(self):
        """Komeco's `heat_cool` column moves, so the sweep reads it --
        and that decision is the whole reason the 52 are visible."""
        fields = _coverage(_komeco())["fields"]
        # 272 cool + 272 heat + 272 heat_cool.
        assert fields["temperature"]["checked"] == 816
        assert {f.keys[0].split("/")[0]
                for f in _findings(_komeco(), CHECK_FIELD_MISMATCH)} == {
            KOMECO_DEFECT_MODE}

    def test_a_frozen_file_dependent_mode_becomes_coverage(self):
        """The same file's `dry` (68 cells) and `fan_only` (272) hold
        one setpoint whatever the label says. Neither is a finding, and
        neither is silently counted as checked."""
        fields = _coverage(_komeco())["fields"]
        assert fields["temperature"]["declined"][fr.TEMP_FROZEN] == 340

    def test_freezing_one_mode_does_not_silence_the_others(self):
        """The decision is per mode, not per wig: 340 frozen cells sit
        beside 816 checked ones in the same lattice, and the checked
        ones are what produce the findings."""
        wig = _pack_wig("ZHLT01.json")
        fields = _coverage(wig)["fields"]
        # This pack freezes `dry` (40 cells) and moves cool and heat.
        assert fields["temperature"]["declined"][fr.TEMP_FROZEN] == 40
        assert fields["temperature"]["checked"] == 80
        assert _findings(wig, CHECK_FIELD_MISMATCH) == []

    def test_a_mode_the_map_says_varies_is_checked_even_when_frozen(self):
        """`file_dependent` is a licence the map grants field by field.
        Freezing `cool`, which the map says varies in every derivation
        file, is a defect and must read as one -- otherwise a wig could
        mute the sweep by flattening a column."""
        wig = _pack_wig("ZHLT01.json")
        frozen = next(c.pronto for c in wig.climate.cells if c.mode == "cool")
        for cell in wig.climate.cells:
            if cell.mode == "cool":
                cell.pronto = frozen
        modes = {f.keys[0].split("/")[0]
                 for f in _findings(wig, CHECK_FIELD_MISMATCH)}
        assert modes == {"cool"}
        assert _coverage(wig)["fields"]["temperature"]["declined"][
            fr.TEMP_FROZEN] == 40


# ---------------------------------------------------------------------------
# Coverage, when there is nothing to check
# ---------------------------------------------------------------------------


class TestCoverageIsHonest:
    def _unmapped(self) -> Wig:
        """A lattice in a protocol no map claims."""
        cells = []
        for index, temp in enumerate(range(16, 31)):
            pairs = [(0x0154, 0x00AA)]
            bits = f"{index:016b}"
            for bit in bits:
                pairs.append((0x0015, 0x003F if bit == "1" else 0x0015))
            pairs.append((0x0015, 0x09C4))
            words = [0x0000, 0x006D, len(pairs), 0x0000]
            for mark, space in pairs:
                words += [mark, space]
            cells.append(ClimateCell(
                mode="cool", fan="auto", temp=float(temp),
                pronto=" ".join(f"{w:04X}" for w in words)))
        matrix = ClimateMatrix(min_temp=16.0, max_temp=30.0,
                               off=cells[0].pronto, cells=cells)
        return Wig(name="Unknown AC", signals=[], climate=matrix)

    def test_an_unmapped_protocol_files_nothing(self):
        assert comb_wig(self._unmapped()).findings == []

    def test_and_says_so_loudly(self):
        """"Protocol unmapped, 0 of N cells verified" is the line the
        brief asked for by name. A silent pass here would have told the
        shop the Komeco file was fine."""
        coverage = _coverage(self._unmapped())
        assert coverage["protocol"]["id"] is None
        assert coverage["protocol"]["readable"] == 0
        assert coverage["protocol"]["codes"] == 16
        declined = coverage["checks"][CHECK_FIELD_MISMATCH]["declined"]
        assert declined[fr.NO_MAP] == 16

    def test_a_flat_wig_gets_the_integrity_rules_but_not_the_sweep(self):
        """Integrity needs no labels, so a flat wig whose codes identify
        gets checked on its protocol's own terms. The field-versus-label
        sweep stays matrix-only: a flat row carries a free-form name,
        not a coordinate."""
        cells = _komeco().climate.cells[:20]
        wig = Wig(name="Flat", signals=[
            WigSignal(alias=f"State {i}", pronto=cell.pronto)
            for i, cell in enumerate(cells)
        ])
        coverage = _coverage(wig)
        assert coverage["protocol"]["id"] == "ZHLT01"
        assert coverage["checks"][CHECK_FRAME_INTEGRITY]["checked"] == 20
        assert coverage["checks"][CHECK_FIELD_MISMATCH]["declined"][
            fr.NO_LABELS] == 20

    def test_a_wig_with_no_maps_at_all_still_combs(self, monkeypatch):
        monkeypatch.setattr(fr, "library", list)
        wig = _komeco()
        report = comb_wig(wig)
        assert [f for f in report.findings
                if f.check == CHECK_FIELD_MISMATCH] == []
        assert report.coverage.to_dict()["protocol"]["id"] is None


# ---------------------------------------------------------------------------
# Twelve families, clean and planted
# ---------------------------------------------------------------------------


PACK_NAMES = [
    "AUX104", "CHIGO96B", "DAIKIN152", "GREE", "MHI152", "MHI160", "MHI48",
    "MIDEA_COOLIX", "MITSUBISHI144", "OEM112", "TCL112", "ZHLT01",
]


class TestTheSynthesizedPacks:
    """Constructed from each map and decoded back through it.

    A pack is built by writing fields INTO a frame with the same map the
    sweep reads them OUT with, so a clean pack that produces a finding
    means the engine disagrees with the map it is executing. That is a
    sharper test than any real file can be, and the packs carry no
    licensing question at all.
    """

    @pytest.mark.parametrize("protocol", PACK_NAMES)
    def test_a_clean_pack_produces_nothing(self, protocol):
        wig = _pack_wig(f"{protocol}.json")
        assert _findings(wig, CHECK_FIELD_MISMATCH) == []
        assert _findings(wig, CHECK_FRAME_INTEGRITY) == []

    @pytest.mark.parametrize("protocol", PACK_NAMES)
    def test_a_clean_pack_is_identified_whole(self, protocol):
        coverage = _coverage(_pack_wig(f"{protocol}.json"))
        assert coverage["protocol"]["id"] == protocol
        assert coverage["protocol"]["readable"] == coverage["protocol"]["codes"]

    @pytest.mark.parametrize("protocol", PACK_NAMES)
    def test_a_defects_pack_produces_exactly_what_was_planted(self, protocol):
        """Exactly, on both sides: every planted defect a RATIFIED field
        can see is found, and nothing else is. A defect planted in a
        provisional field is deliberately invisible -- that is the
        confidence gate working, not the sweep missing."""
        manifest = json.loads(
            (PACKS / f"{protocol}.defects-manifest.json").read_text())
        wig = _pack_wig(f"{protocol}.defects.json")
        field_map = next(m for m in fr.load_maps()
                         if m.protocol_id == protocol)
        expected = set()
        for defect in manifest["defects"]:
            name = defect.get("field")
            if name is None:
                continue  # the integrity defect, asserted separately
            spec = field_map.field_named(name)
            if spec is None or not spec.ratified:
                continue
            expected.add((_coordinate(defect), name))
        found = {
            (f.keys[0], f.params["field"].removeprefix("comb.field."))
            for f in _findings(wig, CHECK_FIELD_MISMATCH)
        }
        assert found == expected

    @pytest.mark.parametrize("protocol", PACK_NAMES)
    def test_the_planted_integrity_break_is_found_when_it_is_ratified(
        self, protocol
    ):
        manifest = json.loads(
            (PACKS / f"{protocol}.defects-manifest.json").read_text())
        planted = [d for d in manifest["defects"] if d.get("field") is None]
        field_map = next(m for m in fr.load_maps()
                         if m.protocol_id == protocol)
        ratified = any(rule.ratified for rule in field_map.integrity)
        found = {f.keys[0]
                 for f in _findings(_pack_wig(f"{protocol}.defects.json"),
                                    CHECK_FRAME_INTEGRITY)}
        if not planted or not ratified:
            assert found == set()
            return
        assert found == {_coordinate(defect) for defect in planted}


def _coordinate(defect: dict) -> str:
    parts = [defect["mode"]]
    for key in ("fan", "swing"):
        if defect.get(key) is not None:
            parts.append(str(defect[key]))
    temp = defect.get("temp")
    if temp is not None:
        parts.append(str(int(temp)) if float(temp).is_integer()
                     else str(temp))
    return "/".join(parts)
