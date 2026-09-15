"""DAIKIN216: the family whose swing needs two fields, and the schema
key that lets a map say so.

Everything here is Sniffer-side reading, not transmit. The map arrived
from a different direction to the other twelve -- one WigShop wig
fitted on a physical unit, rather than a family of SmartIR files read
together -- and two of its properties are worth pinning for that reason
alone:

- It shares its three identity bytes with DAIKIN152, which is expected
  from one manufacturer and one remote generation, and is told apart
  from it by frame count. Both directions are pinned, because an
  identity collision that starts reading the wrong map is the failure
  mode `identity_bytes` exists to prevent and this is the first pair in
  the directory close enough to test it.
- Its swing is two independent nibbles answering one wig dimension, and
  that is what schema v0.3's `coordinate` key is for. A field the comb
  cannot match to a coordinate is not a loud failure: it is counted as
  coverage with a `no-coordinate` receipt, which reads like the wig
  lacking a dimension rather than the map lacking a word. So the pin is
  a planted defect that must be FOUND, not an absence that must not.
"""
from __future__ import annotations

import json
import os
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
    parse_wig,
)

PACKS = Path(__file__).parent / "fixtures" / "field-packs"

#: The real 521-code wig this map was derived from, when a local copy is
#: available. CI never has one: the file is CC0 but it is not vendored,
#: so the acceptance test below skips rather than downloads.
WIG_ENV = "HAIR_DAIKIN216_WIG"


def _map():
    return next(m for m in fr.load_maps() if m.protocol_id == "DAIKIN216")


def _pack(name: str) -> dict:
    return json.loads((PACKS / name).read_text())


def _pronto(pack: dict, mode: str, fan: str, swing: str, temp: str) -> str:
    return _broadlink_b64_to_pronto(pack["commands"][mode][fan][swing][temp])


def _matrix_wig(pack: dict) -> Wig:
    """The pack as a matrix wig, off slot included.

    The shared helper in test_field_sweep.py borrows a state cell for
    the off slot, because the other packs carry no off code. This one
    does, and the off code is where the power defect lives, so this
    builds the matrix with the real one instead of changing a helper
    twelve other families depend on.
    """
    cells: list[ClimateCell] = []
    for mode, by_fan in pack["commands"].items():
        if not isinstance(by_fan, dict):
            continue
        for fan, by_swing in by_fan.items():
            for swing, by_temp in by_swing.items():
                for temp, code in by_temp.items():
                    cells.append(ClimateCell(
                        mode=mode, fan=fan, swing=swing, temp=float(temp),
                        pronto=_broadlink_b64_to_pronto(code) or ""))
    return Wig(name="DAIKIN216", signals=[], climate=ClimateMatrix(
        min_temp=18.0, max_temp=30.0, precision=1.0,
        off=_broadlink_b64_to_pronto(pack["commands"]["off"]) or "",
        cells=cells,
    ))


class TestTheMapReadsItsOwnFrames:
    def test_a_clean_code_identifies_and_decodes(self):
        reading = fr.read_code(
            _pronto(_pack("DAIKIN216.json"), "cool", "low", "off", "22"))
        assert reading.protocol_id == "DAIKIN216"
        assert [len(f) for f in reading.frames] == [8, 19]

    def test_frame_zero_is_the_constant_the_map_declares(self):
        reading = fr.read_code(
            _pronto(_pack("DAIKIN216.json"), "heat", "high", "both", "30"))
        assert reading.frames[0] == (0x11, 0xDA, 0x27, 0xF0, 0, 0, 0, 0x02)

    def test_the_payload_frame_is_nineteen_bytes_ending_in_its_checksum(self):
        reading = fr.read_code(
            _pronto(_pack("DAIKIN216.json"), "cool", "low", "off", "22"))
        payload = reading.frames[1]
        assert len(payload) == 19
        assert payload[18] == sum(payload[:18]) % 256


class TestItIsNotTheOtherDaikin:
    """Same three identity bytes, different frame count.

    DAIKIN152 carries 11 DA 27 on its frame 2 and DAIKIN216 carries them
    on its frame 1. Nothing in the byte values separates the families;
    the layout does, and a map that leaned on identity bytes alone would
    read one as the other and report its fields against the wrong
    offsets.
    """

    def test_a_daikin216_code_is_not_read_as_daikin152(self):
        reading = fr.read_code(
            _pronto(_pack("DAIKIN216.json"), "cool", "low", "off", "22"))
        assert reading.protocol_id == "DAIKIN216"

    def test_a_daikin152_code_is_not_read_as_daikin216(self):
        pack = _pack("DAIKIN152.json")
        pronto = _broadlink_b64_to_pronto(
            pack["commands"]["cool"]["auto"]["22"])
        assert fr.read_code(pronto).protocol_id == "DAIKIN152"

    def test_the_two_maps_differ_only_in_layout_on_their_identity(self):
        daikin216 = {(b, v) for _f, b, v in _map().identity_bytes}
        daikin152 = {
            (b, v) for _f, b, v in next(
                m for m in fr.load_maps() if m.protocol_id == "DAIKIN152"
            ).identity_bytes
        }
        assert daikin216 == daikin152
        assert _map().frame_layout == [64, 152]


class TestTheCoordinateKey:
    """Schema v0.3, and the only map in the directory that uses it."""

    def test_the_reader_parses_it_onto_the_field(self):
        specs = {f.name: f for f in _map().fields}
        assert specs["swing_vertical"].coordinate == "swing"
        assert specs["swing_horizontal"].coordinate == "swing"

    def test_a_field_without_it_still_answers_none(self):
        """Every other map relies on the name table, so the default has
        to stay None rather than becoming a guess at the name."""
        specs = {f.name: f for f in _map().fields}
        assert specs["temperature"].coordinate is None
        for field_map in fr.load_maps():
            if field_map.protocol_id == "DAIKIN216":
                continue
            for spec in field_map.fields:
                assert spec.coordinate is None, field_map.protocol_id

    def test_both_swing_fields_are_checked_not_declined(self):
        """The receipt a missing coordinate would leave is silent, so
        this asserts the positive: the comb judged both fields on every
        cell of the lattice.

        The one decline each is the off code, which carries a power
        coordinate and no others. Every state field declines there for
        the same reason, so it is the shape of an off row rather than
        anything to do with swing.
        """
        coverage = comb_wig(_matrix_wig(_pack("DAIKIN216.json"))).coverage
        fields = coverage.to_dict()["fields"]
        lattice = 2 * 5 * 4 * 5
        for name in ("swing_vertical", "swing_horizontal", "temperature"):
            assert fields[name]["checked"] == lattice, name
            assert fields[name]["declined"] == {"no-coordinate": 1}, name

    def test_a_planted_horizontal_nibble_is_found_and_named(self):
        findings = [
            f for f in comb_wig(
                _matrix_wig(_pack("DAIKIN216.defects.json"))).findings
            if f.check == CHECK_FIELD_MISMATCH
            and f.params["field"] == "comb.field.swing_horizontal"
        ]
        assert len(findings) == 1
        assert findings[0].keys == ["cool/low/horizontal/22"]
        assert findings[0].params["expected"] == "0x0F"
        assert findings[0].params["read"] == "0x00"

    def test_the_vertical_nibble_is_found_separately(self):
        findings = [
            f for f in comb_wig(
                _matrix_wig(_pack("DAIKIN216.defects.json"))).findings
            if f.check == CHECK_FIELD_MISMATCH
            and f.params["field"] == "comb.field.swing_vertical"
        ]
        assert len(findings) == 1
        assert findings[0].keys == ["cool/low/vertical/22"]


class TestTheOffCode:
    """The one code the lattice does not hold.

    The off frame is the last state the remote was in with the power bit
    cleared, so every other field still reads as heat, 24 C, fan high.
    Only the power bit tells it apart, which makes it the one place a
    power defect can be planted and seen.
    """

    def test_the_clean_off_code_reads_power_off(self):
        pack = _pack("DAIKIN216.json")
        reading = fr.read_code(
            _broadlink_b64_to_pronto(pack["commands"]["off"]))
        spec = next(f for f in _map().fields if f.name == "power")
        assert fr.read_field(reading, spec) == 0

    def test_a_power_bit_set_on_the_off_code_is_found(self):
        manifest = _pack("DAIKIN216.defects-manifest.json")
        assert manifest["off_code_defect"]["field"] == "power"
        findings = [
            f for f in comb_wig(
                _matrix_wig(_pack("DAIKIN216.defects.json"))).findings
            if f.check == CHECK_FIELD_MISMATCH and f.keys == ["off"]
        ]
        assert len(findings) == 1
        assert findings[0].params["field"] == "comb.field.power"
        assert findings[0].params["expected"] == "0x00"
        assert findings[0].params["read"] == "0x01"

    def test_the_clean_pack_says_nothing_about_its_off_code(self):
        findings = [
            f for f in comb_wig(_matrix_wig(_pack("DAIKIN216.json"))).findings
            if f.keys == ["off"]
        ]
        assert findings == []


class TestBothChecksumsAreRatified:
    def test_the_planted_breaks_are_found_one_per_frame(self):
        findings = {
            f.keys[0] for f in comb_wig(
                _matrix_wig(_pack("DAIKIN216.defects.json"))).findings
            if f.check == CHECK_FRAME_INTEGRITY
        }
        assert findings == {"cool/low/off/28", "cool/low/off/30"}

    def test_the_clean_pack_breaks_neither(self):
        findings = [
            f for f in comb_wig(_matrix_wig(_pack("DAIKIN216.json"))).findings
            if f.check == CHECK_FRAME_INTEGRITY
        ]
        assert findings == []


@pytest.mark.skipif(
    not os.environ.get(WIG_ENV),
    reason=f"set {WIG_ENV} to the DAIKIN216 corpus wig to run acceptance",
)
class TestAcceptanceOnTheCorpusWig:
    """The file the map was derived from, read back through the map.

    Skipped unless the wig is on disk, because it is not vendored: it is
    CC0 and freely fetchable, but a 1.2 MB corpus file has no business
    in the repository when synthesized packs cover the same ground for
    CI. Run it with the real file before claiming the map works.
    """

    def _receipt(self):
        parsed = parse_wig(Path(os.environ[WIG_ENV]).read_text())
        assert parsed.wig is not None, parsed.errors
        return comb_wig(parsed.wig)

    def test_every_code_is_identified_and_readable(self):
        protocol = self._receipt().coverage.to_dict()["protocol"]
        assert protocol["id"] == "DAIKIN216"
        assert protocol["codes"] == 521
        assert protocol["readable"] == 521
        assert protocol["declined"] == {}

    def test_both_sweeps_check_every_code_and_find_nothing(self):
        receipt = self._receipt()
        checks = receipt.coverage.to_dict()["checks"]
        for name in ("field-mismatch", "frame-integrity"):
            assert checks[name]["checked"] == 521, name
            assert checks[name]["declined"] == {}, name
        assert [f for f in receipt.findings
                if f.check in (CHECK_FIELD_MISMATCH,
                               CHECK_FRAME_INTEGRITY)] == []
