"""PANASONIC216, and the three-way separation it forced.

The family arrived from the AC census as the largest labelled cluster
with no map: 38 public files, 14,242 cells. What makes it worth its own
module is not the derivation, which is ordinary, but what it collided
with on the way in.

DAIKIN216 DECLARES THE SAME FRAME LAYOUT. Two frames, 64 bits then 152,
the same pulse alphabet to within the quantisation of a Broadlink
capture. Before this map existed, 4,468 Panasonic codes and 60
Mitsubishi Heavy codes passed DAIKIN216's ``_matches_layout`` and were
refused one step later by its identity bytes. Nothing was misread, but
the receipt said unreadable-frame where the truth was a family nobody
had mapped, so the tests below pin BOTH halves: that this map claims its
own family, and that DAIKIN216 no longer claims any of it.

WHAT SEPARATES THEM IS THE FRAME GAP, not the identity bytes and not the
pulse widths. Panasonic's inter-frame gap runs 9,861 to 10,439 us and
Daikin's 24,324 to 29,767, with nothing in between. That is the only
axis in the schema's timing block on which the two families do not
overlap, so it is the one DAIKIN216 was tightened on.

Everything here is Sniffer-side reading. No transmit path is touched.
"""
from __future__ import annotations

import json
from pathlib import Path

from custom_components.hair import field_readers as fr
from custom_components.hair.wig_adapters import _broadlink_b64_to_pronto
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_INTEGRITY,
    comb_wig,
)
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, Wig

PACKS = Path(__file__).parent / "fixtures" / "field-packs"

#: The vendor prefix every code in the family carries on its payload
#: frame. Five bytes, which is what separates this map from DAIKIN216
#: once the layout no longer does.
PREFIX = (0x02, 0x20, 0xE0, 0x04, 0x00)


def _map(protocol: str):
    return next(m for m in fr.load_maps() if m.protocol_id == protocol)


def _pack_wig(name: str) -> Wig:
    raw = json.loads((PACKS / name).read_text())
    cells = [
        ClimateCell(mode=mode, fan=fan, temp=float(temp),
                    pronto=_broadlink_b64_to_pronto(code) or "")
        for mode, by_fan in raw["commands"].items()
        for fan, by_temp in by_fan.items()
        for temp, code in by_temp.items()
    ]
    return Wig(name=name, signals=[], climate=ClimateMatrix(
        min_temp=float(raw["minTemperature"]),
        max_temp=float(raw["maxTemperature"]),
        precision=1.0, off=cells[0].pronto, cells=cells))


def _findings(wig: Wig, check: str) -> list:
    return [f for f in comb_wig(wig).findings if f.check == check]


class TestTheMapIsWellFormed:
    def test_it_loads_and_declares_what_the_schema_needs(self):
        m = _map("PANASONIC216")
        assert m.frame_layout == [64, 152]
        assert m.payload_frame == 1
        assert m.bit_order == "lsb_first"

    def test_the_identity_is_the_five_byte_vendor_prefix(self):
        m = _map("PANASONIC216")
        assert [v for _f, _b, v in m.identity_bytes] == list(PREFIX)
        assert {f for f, _b, _v in m.identity_bytes} == {1}

    def test_only_the_fields_the_family_agreed_on_are_ratified(self):
        """fan_speed and power are provisional, and that is the finding.

        Three files write the auto value for every fan label on part of
        their lattice, and no file in the corpus varies power at all,
        because every cell of a SmartIR climate lattice is an on-state.
        Ratifying either would file a finding on every one of those
        cells and say nothing true about the wig carrying them.
        """
        m = _map("PANASONIC216")
        ratified = {f.name for f in m.fields if f.ratified}
        assert ratified == {"temperature", "mode"}
        assert {f.name for f in m.fields} - ratified == {"fan_speed", "power"}

    def test_both_checksums_are_ratified(self):
        rules = _map("PANASONIC216").integrity
        assert [r.type for r in rules] == ["checksum_sum", "checksum_sum"]
        assert all(r.ratified for r in rules)
        assert {r.params["frame"] for r in rules} == {0, 1}


class TestTheCleanPack:
    def test_every_code_identifies_as_this_family(self):
        wig = _pack_wig("PANASONIC216.json")
        cov = comb_wig(wig).coverage.to_dict()["protocol"]
        assert cov["id"] == "PANASONIC216"
        assert cov["readable"] == cov["codes"]

    def test_it_produces_no_findings_at_all(self):
        wig = _pack_wig("PANASONIC216.json")
        assert _findings(wig, CHECK_FIELD_MISMATCH) == []
        assert _findings(wig, CHECK_FRAME_INTEGRITY) == []

    def test_fan_only_is_temperature_invariant_and_counted_as_coverage(self):
        """The map says fan_only holds one setpoint whatever the label.

        So those cells are not checked, and they are not silently
        counted as checked either.
        """
        fields = comb_wig(_pack_wig("PANASONIC216.json")).coverage.to_dict()["fields"]
        assert fields["temperature"]["declined"][fr.TEMP_INVARIANT] > 0
        assert fields["temperature"]["checked"] > 0

    def test_provisional_fields_are_not_swept(self):
        fields = comb_wig(_pack_wig("PANASONIC216.json")).coverage.to_dict()["fields"]
        assert fields["fan_speed"]["checked"] == 0
        assert fields["power"]["checked"] == 0


class TestTheDefectsPack:
    """Exactly what was planted, and nothing else."""

    def _planted(self) -> list[dict]:
        return json.loads(
            (PACKS / "PANASONIC216.defects-manifest.json").read_text())["defects"]

    def test_the_manifest_plants_one_defect_of_each_kind(self):
        kinds = {d["defect"] for d in self._planted()}
        assert kinds == {"temperature_wrong_value", "mode_wrong_value",
                         "checksum_broken"}

    def test_every_planted_field_defect_is_found(self):
        wig = _pack_wig("PANASONIC216.defects.json")
        found = {
            f.params["field"].rsplit(".", 1)[-1]
            for f in _findings(wig, CHECK_FIELD_MISMATCH)
        }
        planted = {d["field"] for d in self._planted() if d["field"]}
        assert found == planted

    def test_each_one_is_found_at_the_coordinate_it_was_planted_at(self):
        wig = _pack_wig("PANASONIC216.defects.json")
        at = {
            f.params["field"].rsplit(".", 1)[-1]: f.keys[0]
            for f in _findings(wig, CHECK_FIELD_MISMATCH)
        }
        for d in self._planted():
            if not d["field"]:
                continue
            # The key is mode/fan/temp when the wig has no swing axis.
            parts = at[d["field"]].split("/")
            mode, fan, temp = parts[0], parts[1], parts[-1]
            assert mode == d["mode"] and fan == d["fan"]
            assert float(temp) == d["temp"]

    def test_the_broken_checksum_is_found_and_is_the_only_one(self):
        wig = _pack_wig("PANASONIC216.defects.json")
        integrity = _findings(wig, CHECK_FRAME_INTEGRITY)
        assert len(integrity) == 1

    def test_nothing_beyond_the_manifest_is_reported(self):
        wig = _pack_wig("PANASONIC216.defects.json")
        planted_fields = [d for d in self._planted() if d["field"]]
        assert len(_findings(wig, CHECK_FIELD_MISMATCH)) == len(planted_fields)


class TestItDoesNotCollideWithDaikin:
    """The reason this module exists, pinned in both directions."""

    def _daikin_shaped(self) -> str:
        """A DAIKIN216 code, built from DAIKIN216's own clean pack."""
        raw = json.loads((PACKS / "DAIKIN216.json").read_text())
        for _mode, by_fan in raw["commands"].items():
            for _fan, level in by_fan.items():
                if isinstance(level, dict):
                    for value in level.values():
                        if isinstance(value, str):
                            return _broadlink_b64_to_pronto(value) or ""
                        for code in value.values():
                            if isinstance(code, str):
                                return _broadlink_b64_to_pronto(code) or ""
        raise AssertionError("no code in the DAIKIN216 pack")

    def test_a_daikin_code_is_not_read_as_panasonic(self):
        reading = fr.read_code(self._daikin_shaped(), [_map("PANASONIC216")])
        assert reading.protocol_id != "PANASONIC216"

    def test_a_panasonic_code_is_not_read_as_daikin(self):
        wig = _pack_wig("PANASONIC216.json")
        pronto = wig.climate.cells[0].pronto
        assert fr.read_code(pronto, [_map("DAIKIN216")]).protocol_id != "DAIKIN216"

    def test_daikin_no_longer_even_claims_the_layout(self):
        """The tightening, stated as the thing it was for.

        Before it, a Panasonic code split into two frames under
        DAIKIN216's timing and matched its declared layout, so the
        refusal came from the identity bytes and the receipt said
        unreadable-frame. After it, the code does not split there at
        all, so the layout refuses it first.
        """
        daikin = _map("DAIKIN216")
        pronto = _pack_wig("PANASONIC216.json").climate.cells[0].pronto
        timings = fr.pronto_microseconds(pronto) or []
        frames, failed = fr.read_frames(daikin.timing, timings)
        # Either outcome is a refusal BEFORE identity: with the gap at
        # 11,000 the Panasonic inter-frame space is no longer a gap and
        # no longer a legal bit space either, so this map now reads the
        # code as noise rather than splitting it into a layout it
        # recognises. What must not happen is the layout matching.
        assert failed or not fr._matches_layout(daikin, frames)

    def test_the_gap_is_what_separates_them(self):
        """Not the identity bytes, and not the pulse widths."""
        pan, dai = _map("PANASONIC216"), _map("DAIKIN216")
        assert pan.timing.gap_min < dai.timing.gap_min
        for axis in ("unit", "zero", "one"):
            p, d = getattr(pan.timing, axis), getattr(dai.timing, axis)
            assert p.minimum <= d.maximum and d.minimum <= p.maximum, axis


class TestDaikin152WasRepaired:
    """The leader block the map knew about and did not declare."""

    def test_it_now_declares_four_frames(self):
        m = _map("DAIKIN152")
        assert m.frame_layout == [5, 64, 64, 152]
        assert m.payload_frame == 3

    def test_its_identity_bytes_moved_with_the_payload_frame(self):
        m = _map("DAIKIN152")
        assert {f for f, _b, _v in m.identity_bytes} == {3}
        assert [v for _f, _b, v in m.identity_bytes] == [0x11, 0xDA, 0x27]

    def test_its_own_pack_still_reads(self):
        wig = _pack_wig("DAIKIN152.json")
        cov = comb_wig(wig).coverage.to_dict()["protocol"]
        assert cov["id"] == "DAIKIN152"
