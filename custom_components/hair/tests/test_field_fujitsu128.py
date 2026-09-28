"""FUJITSU128, the seven-byte identity, and the first negative checksum.

Two things in this map are new to the directory and both are pinned
here.

THE CHECK BYTE FALLS AS THE PAYLOAD RISES. Fujitsu closes its frame with
`0xD0 - sum(bytes 8..14)`, not with a sum. The `checksum_sum` rule could
only ever add, so this map is the reason schema v0.4 gives that rule an
optional `scale`. It defaults to 1, so every map written before it
computes exactly what it did; the tests below check both halves of that
claim, because a rule parameter that silently changed an existing map
would be worse than no parameter at all.

TEMPERATURE IS DELIBERATELY ABSENT. The setpoint is in byte 8's high
nibble and steps by one per degree in every file, but it counts from the
REMOTE'S OWN minimum rather than from a fixed temperature, so the same
nibble means 16 C in one file and 18 C in another. No encoding in the
closed set can say `T minus this file's minimum`. Leaving the field out
is the honest answer and the test here pins that it stays out, so nobody
adds it later with a guessed offset and files a finding on every cell of
half the family.

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

#: The seven bytes every code in the family opens with.
PREFIX = (0x14, 0x63, 0x00, 0x10, 0x10, 0xFE, 0x09)


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


class TestTheMap:
    def test_one_frame_of_128_bits(self):
        m = _map("FUJITSU128")
        assert m.frame_layout == [128]
        assert m.payload_frame == 0

    def test_the_identity_is_seven_constant_bytes(self):
        m = _map("FUJITSU128")
        assert [v for _f, _b, v in m.identity_bytes] == list(PREFIX)
        assert {f for f, _b, _v in m.identity_bytes} == {0}

    def test_mode_and_swing_are_ratified_and_fan_is_not(self):
        m = _map("FUJITSU128")
        assert {f.name for f in m.fields if f.ratified} == {"mode", "swing"}
        assert {f.name for f in m.fields if not f.ratified} == {"fan_speed"}

    def test_temperature_is_not_a_field(self):
        """See the module docstring. Absence here is a decision."""
        assert _map("FUJITSU128").field_named("temperature") is None


class TestTheNegativeChecksum:
    def test_the_rule_declares_a_negative_scale(self):
        rule = _map("FUJITSU128").integrity[0]
        assert rule.type == fr.RULE_CHECKSUM_SUM
        assert rule.params["scale"] == -1
        assert rule.params["offset"] == 0xD0
        assert rule.ratified

    def test_it_holds_on_the_clean_pack(self):
        assert _findings(_pack_wig("FUJITSU128.json"),
                         CHECK_FRAME_INTEGRITY) == []

    def test_scale_defaults_to_one_so_older_maps_are_unchanged(self):
        """The additive maps must compute what they always did.

        PANASONIC216 states no `scale` and its rule is a plain sum, so if
        the default ever stopped being 1 its clean pack would start
        failing integrity. That is the cheapest possible canary and it is
        worth having, because this parameter reaches every map in the
        directory that uses a sum.
        """
        panasonic = _map("PANASONIC216")
        for rule in panasonic.integrity:
            assert "scale" not in rule.params
        assert _findings(_pack_wig("PANASONIC216.json"),
                         CHECK_FRAME_INTEGRITY) == []


class TestThePacks:
    def test_the_clean_pack_identifies_and_says_nothing(self):
        wig = _pack_wig("FUJITSU128.json")
        cov = comb_wig(wig).coverage.to_dict()["protocol"]
        assert cov["id"] == "FUJITSU128"
        assert cov["readable"] == cov["codes"]
        assert _findings(wig, CHECK_FIELD_MISMATCH) == []
        assert _findings(wig, CHECK_FRAME_INTEGRITY) == []

    def test_the_defects_pack_yields_exactly_what_was_planted(self):
        planted = json.loads(
            (PACKS / "FUJITSU128.defects-manifest.json").read_text())["defects"]
        wig = _pack_wig("FUJITSU128.defects.json")
        field_defects = [d for d in planted if d["field"]]
        assert len(_findings(wig, CHECK_FIELD_MISMATCH)) == len(field_defects)
        assert len(_findings(wig, CHECK_FRAME_INTEGRITY)) == \
            len(planted) - len(field_defects)

    def test_the_planted_field_defect_names_the_right_field(self):
        planted = json.loads(
            (PACKS / "FUJITSU128.defects-manifest.json").read_text())["defects"]
        wig = _pack_wig("FUJITSU128.defects.json")
        found = {f.params["field"].rsplit(".", 1)[-1]
                 for f in _findings(wig, CHECK_FIELD_MISMATCH)}
        assert found == {d["field"] for d in planted if d["field"]}

    def test_provisional_fan_is_not_swept(self):
        fields = comb_wig(
            _pack_wig("FUJITSU128.json")).coverage.to_dict()["fields"]
        assert fields["fan_speed"]["checked"] == 0


class TestItStaysOffOtherFamilies:
    def test_a_panasonic_code_is_not_read_as_fujitsu(self):
        pronto = _pack_wig("PANASONIC216.json").climate.cells[0].pronto
        assert fr.read_code(pronto, [_map("FUJITSU128")]).protocol_id is None

    def test_a_fujitsu_code_is_not_read_as_panasonic_or_daikin(self):
        pronto = _pack_wig("FUJITSU128.json").climate.cells[0].pronto
        for other in ("PANASONIC216", "DAIKIN216", "DAIKIN152"):
            assert fr.read_code(pronto, [_map(other)]).protocol_id is None
