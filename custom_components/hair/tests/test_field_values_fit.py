"""A value the field's bits cannot carry is not an expected value.

Corpus 2041 is a TCL112 remote labelled 62 to 88 F. The map's
temperature is ``31 - T`` in the low nibble, so 62 F computes to -31,
which no nibble holds. The comb filed that as a finding (expected
``0x-1F``), the listing could not parse its own finding, and Needs
attention would not open for the remote at all. On a Fahrenheit Gree
remote the arithmetic overflows upward instead (61 F computes to 45),
the listing opened, and every temperature cell was a wrong temperature
no code could clear.

A check nobody can compute is coverage, never a finding. The answer is
checked once, at the one exit of ``expected_value``, so every encoding
is covered without being named, and the comb says why: the map
computed a value its bits cannot carry (``out-of-domain``), which is a
different fact from a label the map does not know.
"""
from __future__ import annotations

import copy
import dataclasses
from pathlib import Path

from custom_components.hair import field_readers as fr
from custom_components.hair.models import IRDevice
from custom_components.hair.tangles import (
    _cause_of,
    _stamp_mismatch_labels,
    cluster_rows,
    list_tangles,
    read_lattice,
    rewrite_field,
)
from custom_components.hair.wig_comb import CHECK_FIELD_MISMATCH, comb_wig
from custom_components.hair.wig_format import Wig, parse_wig

from .test_field_sweep import _pack_wig

KOMECO = (Path(__file__).parent / "fixtures" / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")


def _map(protocol_id: str) -> fr.FieldMap:
    for candidate in fr.library():
        if candidate.protocol_id == protocol_id:
            return candidate
    raise AssertionError(f"{protocol_id} is not vendored")


def _spec(protocol_id: str, name: str) -> fr.FieldSpec:
    spec = _map(protocol_id).field_named(name)
    assert spec is not None, (protocol_id, name)
    return spec


def _relabelled(wig: Wig, relabel) -> Wig:
    """The same codes under other temperature labels."""
    matrix = wig.climate
    cells = [dataclasses.replace(cell, temp=relabel(cell))
             for cell in matrix.cells]
    temps = [cell.temp for cell in cells if cell.temp is not None]
    return Wig(name=wig.name, signals=[], climate=dataclasses.replace(
        matrix, cells=cells, min_temp=min(temps), max_temp=max(temps)))


def _temperature_findings(wig: Wig) -> list:
    return [finding for finding in comb_wig(wig).findings
            if finding.check == CHECK_FIELD_MISMATCH
            and finding.params.get("field") == "comb.field.temperature"]


# ---------------------------------------------------------------------------
# T1: one exit, every encoding
# ---------------------------------------------------------------------------


class TestExpectedValueAnswersOnlyWhatTheBitsCarry:
    def test_tcl112_inside_and_outside_its_nibble(self):
        spec = _spec("TCL112", "temperature")
        assert fr.expected_value(spec, 16) == 15
        assert fr.expected_value(spec, 31) == 0
        assert fr.expected_value(spec, 15.5) == 15
        for label in (15, 31.5, 62, 88):
            assert fr.expected_value(spec, label) is None, label

    def test_gree_overflows_upward_and_is_none_too(self):
        """``linear``: the other direction. 61 F computes to 45, which
        no nibble holds either."""
        spec = _spec("GREE", "temperature")
        assert spec.encoding == fr.ENCODING_LINEAR
        assert fr.expected_value(spec, 31.5) == 15
        assert fr.expected_value(spec, 32) is None
        assert fr.expected_value(spec, 61) is None

    def test_a_special_value_its_nibble_cannot_carry(self):
        """``reverse_bits4`` already declines a label outside 16..31 on
        its own; only a ``special`` entry reaches the exit unchecked."""
        spec = dataclasses.replace(
            _spec("ZHLT01", "temperature"), params={"special": {33: 16}})
        assert fr.expected_value(spec, 33) is None

    def test_a_vocabulary_value_its_selector_cannot_carry(self):
        spec = dataclasses.replace(
            _spec("ZHLT01", "temperature"),
            encoding=fr.ENCODING_ENUM_NIBBLE, bits="mask:0x07",
            params={"vocabulary": {"wide": 8, "narrow": 7}})
        assert fr.expected_value(spec, "wide") is None
        assert fr.expected_value(spec, "narrow") == 7

    def test_every_answer_of_every_shipped_field_fits(self):
        """The sweep that keeps the exit honest: every field of every
        map, every label from 0 to 120 in half steps and every key it
        names, answers None or a value its own bits carry."""
        swept = 0
        for field_map in fr.library():
            for spec in field_map.fields:
                labels: list = [step / 2 for step in range(241)]
                for name in ("vocabulary", "special"):
                    table = spec.params.get(name)
                    if isinstance(table, dict):
                        labels += list(table)
                labels += list(spec.params.get("true_values") or [])
                for label in labels:
                    value = fr.expected_value(spec, label)
                    if value is None:
                        continue
                    assert fr.fits(spec, value), (
                        field_map.protocol_id, spec.name, label, value)
                    swept += 1
        assert swept > 1000

    def test_the_reason_names_which_none_it_is(self):
        spec = _spec("TCL112", "temperature")
        assert fr.uncomputable_reason(spec, 62) == fr.OUT_OF_DOMAIN
        mode = _spec("TCL112", "mode")
        assert fr.uncomputable_reason(mode, "nonsense") == fr.UNKNOWN_LABEL
        # ZHLT01's own range check computes nothing, so its None stays
        # a label the map does not know, and no stored receipt moves.
        zhlt = _spec("ZHLT01", "temperature")
        assert fr.expected_value(zhlt, 40) is None
        assert fr.uncomputable_reason(zhlt, 40) == fr.UNKNOWN_LABEL


# ---------------------------------------------------------------------------
# T2: the comb and the listing on a remote the map cannot encode
# ---------------------------------------------------------------------------


class TestAFahrenheitLatticeIsCoverage:
    """The 2041 shape, built from the TCL112 pack relabelled 62 to 77
    F, and the 1684 shape, one MHI152 cell labelled 16 C, which the
    family's ``32 - T`` nibble cannot say. Both fail on the code before
    this change: the first raises in the listing, the second files a
    finding expecting 0x10."""

    def test_tcl112_in_fahrenheit_files_no_temperature_finding(self):
        celsius = _pack_wig("TCL112.json")
        fahrenheit = _relabelled(celsius, lambda cell: cell.temp + 46)
        assert _temperature_findings(fahrenheit) == []

    def test_and_counts_every_judged_cell_as_out_of_domain(self):
        celsius = _pack_wig("TCL112.json")
        fahrenheit = _relabelled(celsius, lambda cell: cell.temp + 46)
        judged = comb_wig(celsius).coverage.to_dict()[
            "fields"]["temperature"]["checked"]
        assert judged > 0
        after = comb_wig(fahrenheit).coverage.to_dict()[
            "fields"]["temperature"]
        assert after["checked"] == 0
        assert after["declined"][fr.OUT_OF_DOMAIN] == judged
        assert fr.UNKNOWN_LABEL not in after["declined"]

    def test_and_needs_attention_opens(self):
        fahrenheit = _relabelled(
            _pack_wig("TCL112.json"), lambda cell: cell.temp + 46)
        device = IRDevice(name="TCL in Fahrenheit", climate_matrix=True)
        listing = list_tangles(device, fahrenheit.climate)
        for row in listing.rows:
            for finding in row.findings:
                assert finding.get("params", {}).get("field") != (
                    "comb.field.temperature")

    def test_one_mhi152_cell_below_the_floor(self):
        wig = _pack_wig("MHI152.json")
        cool = sorted((cell for cell in wig.climate.cells
                       if cell.mode == "cool"), key=lambda cell: cell.temp)
        low = cool[0]
        relabelled = _relabelled(
            wig, lambda cell: 16.0 if cell is low else cell.temp)
        assert _temperature_findings(relabelled) == []
        declined = comb_wig(relabelled).coverage.to_dict()[
            "fields"]["temperature"]["declined"]
        assert declined[fr.OUT_OF_DOMAIN] == 1


# ---------------------------------------------------------------------------
# T3: the map lint
# ---------------------------------------------------------------------------


class TestEveryStatedValueFitsItsSelector:
    """A vocabulary value its selector cannot carry is a map typo. Before
    the exit check that typo made every cell on its label a finding no
    code could clear, which is loud; now it would be quiet coverage. So
    the typo is caught here instead, where it costs nothing."""

    def test_vocabulary_and_special_values(self):
        checked = 0
        for field_map in fr.library():
            for spec in field_map.fields:
                for name in ("vocabulary", "special"):
                    table = spec.params.get(name)
                    if not isinstance(table, dict):
                        continue
                    for label, raw in table.items():
                        value = fr._as_int(raw)
                        where = (field_map.protocol_id, spec.name, name,
                                 label, raw)
                        assert value is not None, where
                        assert fr.fits(spec, value), where
                        checked += 1
        assert checked > 50


# ---------------------------------------------------------------------------
# T4: both readers of a comb byte, on a byte the comb should never write
# ---------------------------------------------------------------------------


class TestABadCombByteCostsALabelNotTheListing:
    """The source fix means the comb never writes ``0x-1F`` again, and
    T2 pins that on its own. This is for the day it regresses: two
    functions parse the comb's bytes, and guarding one of them moves
    the crash one function down rather than removing it."""

    def _rows(self):
        wig = parse_wig(KOMECO.read_text()).wig
        assert wig is not None
        listing = list_tangles(
            IRDevice(name="Komeco", climate_matrix=True), wig.climate)
        lattice = read_lattice(wig.climate)
        row = next(row for row in listing.rows
                   if CHECK_FIELD_MISMATCH in row.classes)
        row = copy.deepcopy(row)
        for finding in row.findings:
            if finding.get("check") != CHECK_FIELD_MISMATCH:
                continue
            params = dict(finding.get("params") or {})
            params.pop("claimed", None)
            params.pop("reads_as", None)
            params["expected"] = "0x-1F"
            finding["params"] = params
        return row, lattice

    def test_the_labels_are_skipped_without_a_raise(self):
        row, lattice = self._rows()
        _stamp_mismatch_labels([row], lattice)
        for finding in row.findings:
            if finding.get("check") == CHECK_FIELD_MISMATCH:
                assert "claimed" not in finding["params"]
                assert "reads_as" not in finding["params"]

    def test_the_cause_falls_back_to_the_raw_text(self):
        row, lattice = self._rows()
        _rule, _key, field, detail = _cause_of(row, lattice)
        assert field == "temperature"
        assert detail.get("expected") == "0x-1F"

    def test_and_the_row_still_gets_a_card(self):
        row, lattice = self._rows()
        clusters = cluster_rows([row], lattice)
        assert any(row.id in cluster.members for cluster in clusters)


# ---------------------------------------------------------------------------
# T5: the writer behind every synthesized cell
# ---------------------------------------------------------------------------


class TestRewriteFieldWritesOnlyWhatFits:
    def test_a_value_the_nibble_cannot_carry_is_refused(self):
        field_map = _map("TCL112")
        spec = field_map.field_named("temperature")
        code = _pack_wig("TCL112.json").climate.cells[0].pronto
        assert rewrite_field(field_map, code, spec, 5) is not None
        for value in (-31, 16, 45):
            assert rewrite_field(field_map, code, spec, value) is None, value
