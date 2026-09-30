"""DAIKIN152's traits round: powerful and economy are flags, not fan speeds.

The map read ``powerful`` as fan 0xA. Every source says otherwise: a
powerful cell sets frame 3 byte 13 bit 0 and leaves the fan nibble at
whatever speed was chosen (0xA in some files, 0x7 in others). Read as a
fan value, every powerful cell whose fan was not auto was a finding,
which is what put 84 rows in the GH #183 remote's Needs attention. Read
as its own flag, each cell reads what it sends.

The same round:

- makes fan_only carry the labelled speed (only dry forces it),
- adds ``quiet`` to the fan vocabulary beside night, nature and breeze,
- locates swing (bytes 8 and 9, low nibbles), economy (byte 16 bit 2)
  and sleep (byte 13 bit 2) as PROVISIONAL fields, read but never
  judged, because one rendered source varies them and no handset pair
  does yet,
- and lets ``tangles.rewrite_field`` build from a cell that left out its
  optional leader.

Every code here is synthetic, built by the test-side encoder that the
leader pins already use. The one exception is the committed ARC486A1
field capture, which the map's fan vocabulary is checked against by
name; nothing from the #183 wig is in this file.
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair import wig_comb
from custom_components.hair.tangles import rewrite_field
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, Wig

from .test_daikin152_optional_leader import _press, _with_sum

MAPS = {m.protocol_id: m for m in fr.library()}
DAIKIN = MAPS["DAIKIN152"]
FIELD = {spec.name: spec for spec in DAIKIN.fields}

_MODE = {"cool": 0x3, "heat": 0x4, "dry": 0x2, "fan_only": 0x6}
_FAN = {"auto": 0xA, "low": 0x3, "medium": 0x5, "high": 0x7, "quiet": 0xB}
_SWING = {"off": (0x0, 0x0), "vertical": (0xF, 0x0),
          "horizontal": (0x0, 0xF), "both": (0xF, 0xF)}

CAPTURE = (
    Path(__file__).parent / "fixtures" / "field-captures"
    / "arc486a1-orthobot.pronto"
).read_text(encoding="utf-8").strip()


def _settings(mode: str, fan: int, temp: int, *, powerful: bool = False,
              economy: bool = False, sleep: bool = False, swing: str = "off",
              power: int = 1) -> list[int]:
    """The 19-byte settings frame, from the map's positions only."""
    data = [0x11, 0xDA, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x06, 0x60, 0x00, 0x00, 0xC1, 0x00, 0x00]
    data[5] = (_MODE[mode] << 4) | power
    if mode == "dry":
        data[6] = 0xC0
    elif mode == "fan_only":
        data[6] = 0x32
    else:
        data[6] = temp * 2
    vertical, horizontal = _SWING[swing]
    data[8] = (fan << 4) | vertical
    data[9] = horizontal
    if powerful:
        data[13] |= 0x01
    if economy:
        data[16] |= 0x04
    if sleep:
        data[13] |= 0x04
    return _with_sum(data)


def _read(settings: list[int], leader: bool = False) -> fr.Reading:
    reading = fr.read_code(_press(settings, leader=leader))
    assert reading.protocol_id == "DAIKIN152"
    return reading


def _lattice(cells: list[tuple[str, str, str, int, list[int]]]) -> Wig:
    """A leaderless lattice, as the #183 wig renders it."""
    climate = ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0,
        modes=sorted({c[0] for c in cells}),
        fan_modes=sorted({c[1] for c in cells}),
        swing_modes=sorted({c[2] for c in cells}),
        off=_press(_settings("cool", 0xA, 22, power=0), leader=True),
        cells=[
            ClimateCell(mode=mode, fan=fan, swing=swing, temp=float(temp),
                        pronto=_press(settings, leader=False))
            for mode, fan, swing, temp, settings in cells
        ],
    )
    return Wig(name="AC", signals=[], climate=climate)


def _field_findings(wig: Wig) -> list:
    return [f for f in wig_comb.comb_wig(wig).findings
            if f.check == wig_comb.CHECK_FIELD_MISMATCH]


# ---------------------------------------------------------------------------
# What the map now says
# ---------------------------------------------------------------------------


class TestTheMap:

    def test_powerful_is_not_a_fan_speed(self):
        vocabulary = FIELD["fan_speed"].params["vocabulary"]
        assert "powerful" not in vocabulary

    def test_powerful_is_a_ratified_flag_on_the_fan_axis(self):
        spec = FIELD["powerful"]
        assert (spec.frame, spec.byte, spec.bits) == (3, 13, "bit:0")
        assert spec.coordinate == "fan"
        assert spec.ratified
        assert fr.expected_value(spec, "powerful") == 1
        for label in ("auto", "low", "high", "night", "quiet", "economy"):
            assert fr.expected_value(spec, label) == 0, label

    @pytest.mark.parametrize("name,byte,bits", [
        ("economy", 16, "bit:2"), ("sleep", 13, "bit:2")])
    def test_economy_and_sleep_are_provisional_flags(self, name, byte, bits):
        spec = FIELD[name]
        assert (spec.frame, spec.byte, spec.bits) == (3, byte, bits)
        assert spec.coordinate == "fan"
        assert not spec.ratified
        assert fr.expected_value(spec, name) == 1
        assert fr.expected_value(spec, "high") == 0

    def test_swing_is_located_and_provisional(self):
        vertical, horizontal = FIELD["swing_vertical"], FIELD["swing_horizontal"]
        assert (vertical.byte, vertical.bits) == (8, "low_nibble")
        assert (horizontal.byte, horizontal.bits) == (9, "low_nibble")
        assert vertical.coordinate == horizontal.coordinate == "swing"
        assert not vertical.ratified and not horizontal.ratified
        for label, (v, h) in _SWING.items():
            assert fr.expected_value(vertical, label) == v, label
            assert fr.expected_value(horizontal, label) == h, label

    @pytest.mark.parametrize("label", ["high", "level5", "5"])
    def test_0x7_is_the_highest_fixed_level(self, label):
        assert fr.expected_value(FIELD["fan_speed"], label) == 0x7

    def test_quiet_sits_with_night(self):
        spec = FIELD["fan_speed"]
        assert fr.expected_value(spec, "quiet") == 0xB
        assert fr.expected_value(spec, "night") == 0xB

    def test_only_dry_forces_the_fan(self):
        mode = FIELD["mode"]
        assert fr.mode_trait(mode, "dry", "fan") == "forced"
        assert fr.mode_trait(mode, "fan_only", "fan") == "free"
        assert fr.applies(FIELD["fan_speed"], {"mode": "fan_only"})
        assert not fr.applies(FIELD["fan_speed"], {"mode": "dry"})


# ---------------------------------------------------------------------------
# Powerful on and off
# ---------------------------------------------------------------------------


class TestPowerfulIsAFlag:

    @pytest.mark.parametrize("fan", [0x3, 0x5, 0x7, 0xA])
    @pytest.mark.parametrize("leader", [False, True])
    def test_on_and_off_read_the_same_fan(self, fan, leader):
        plain = _read(_settings("cool", fan, 22), leader)
        boosted = _read(_settings("cool", fan, 22, powerful=True), leader)
        assert fr.read_field(plain, FIELD["fan_speed"]) == fan
        assert fr.read_field(boosted, FIELD["fan_speed"]) == fan
        assert fr.read_field(plain, FIELD["powerful"]) == 0
        assert fr.read_field(boosted, FIELD["powerful"]) == 1

    def test_nothing_else_moves(self):
        plain = _read(_settings("cool", 0x7, 22))
        boosted = _read(_settings("cool", 0x7, 22, powerful=True))
        for spec in DAIKIN.fields:
            if spec.name == "powerful":
                continue
            assert fr.read_field(plain, spec) == fr.read_field(boosted, spec), \
                spec.name

    def test_a_lattice_shaped_like_183_reads_clean(self):
        """Powerful rendered as fan high plus the flag, as the #183 wig
        does it: under the old vocabulary every one of these was a
        fan_speed finding. Now there are none."""
        cells = []
        for fan in ("auto", "low", "medium", "high", "quiet", "powerful"):
            nibble = _FAN["high"] if fan == "powerful" else _FAN[fan]
            for swing in _SWING:
                for temp in (18, 22, 26):
                    cells.append(("cool", fan, swing, temp, _settings(
                        "cool", nibble, temp, powerful=fan == "powerful",
                        swing=swing)))
        assert _field_findings(_lattice(cells)) == []

    def test_the_old_vocabulary_is_what_raised_them(self):
        """The same lattice against the map as it stood: every powerful
        cell is a fan_speed finding. This is the count the round clears."""
        spec = FIELD["fan_speed"]
        old = dict(spec.params["vocabulary"], powerful=0xA)
        reading = _read(_settings("cool", 0x7, 22, powerful=True))
        assert fr.read_field(reading, spec) != old["powerful"]

    def test_a_powerful_label_without_the_flag_is_still_a_finding(self):
        """The flag is judged, so the check has teeth both ways."""
        cells = [("cool", "high", "off", t, _settings("cool", 0x7, t))
                 for t in (18, 22, 26)]
        cells += [("cool", "powerful", "off", 22, _settings("cool", 0x7, 22))]
        findings = _field_findings(_lattice(cells))
        assert [(f.keys, f.params.get("field")) for f in findings] == [
            (["cool/powerful/off/22"], "comb.field.powerful")]

    def test_the_flag_without_the_label_is_a_finding(self):
        cells = [("cool", "high", "off", t, _settings("cool", 0x7, t))
                 for t in (18, 26)]
        cells += [("cool", "high", "off", 22,
                   _settings("cool", 0x7, 22, powerful=True))]
        findings = _field_findings(_lattice(cells))
        assert [(f.keys, f.params.get("field")) for f in findings] == [
            (["cool/high/off/22"], "comb.field.powerful")]


# ---------------------------------------------------------------------------
# Everything that shares fan 0x7 reads apart
# ---------------------------------------------------------------------------


def _reads(settings: list[int]) -> tuple:
    reading = _read(settings)
    return tuple(fr.read_field(reading, spec) for spec in DAIKIN.fields)


class TestTheFanSevenFamilyReadsApart:
    """High, powerful, economy and sleep all send fan 0x7 in the #183
    shape and differ only in a flag each; times four swing positions,
    that is sixteen states. Every one must read differently from the
    other fifteen, because identity built from what the map reads cannot
    separate what the map does not read. Provisional fields count: they
    are read, only never judged."""

    VARIANTS: ClassVar[dict[str, dict[str, bool]]] = {
        "high": {}, "powerful": {"powerful": True},
        "economy": {"economy": True}, "sleep": {"sleep": True},
    }

    def test_sixteen_states_sixteen_readings(self):
        seen = {}
        for label, flags in self.VARIANTS.items():
            for swing in _SWING:
                values = _reads(_settings("cool", 0x7, 24, swing=swing, **flags))
                assert values not in seen, (label, swing, seen.get(values))
                seen[values] = (label, swing)
        assert len(seen) == 16

    def test_a_plain_high_press_reads_as_high_only(self):
        press = _reads(_settings("cool", 0x7, 24, swing="vertical"))
        matches = [
            (label, swing)
            for label, flags in self.VARIANTS.items() for swing in _SWING
            if _reads(_settings("cool", 0x7, 24, swing=swing, **flags)) == press
        ]
        assert matches == [("high", "vertical")]


# ---------------------------------------------------------------------------
# fan_only and dry
# ---------------------------------------------------------------------------


class TestFanOnlyCarriesItsSpeed:

    def _cells(self, mode, wrong=None):
        cells = []
        for fan in ("auto", "low", "medium", "high"):
            nibble = _FAN[fan]
            if wrong == fan:
                nibble = _FAN["low"]
            cells.append((mode, fan, "off", 25,
                          _settings(mode, nibble, 25)))
        return cells

    def test_fan_only_is_judged_and_reads_clean(self):
        wig = _lattice(self._cells("fan_only"))
        coverage = wig_comb.comb_wig(wig).coverage.to_dict()
        assert coverage["fields"]["fan_speed"]["checked"] == 4
        assert _field_findings(wig) == []

    def test_a_wrong_fan_only_speed_is_a_finding(self):
        findings = _field_findings(_lattice(self._cells("fan_only", "high")))
        assert [f.keys for f in findings] == [["fan_only/high/off/25"]]

    def test_dry_is_still_not_judged_on_fan(self):
        """Dry forces auto in every handset source; a rendered file that
        writes the labelled speed there is not flagged for it."""
        wig = _lattice(self._cells("dry", "high"))
        coverage = wig_comb.comb_wig(wig).coverage.to_dict()
        assert coverage["fields"]["fan_speed"]["checked"] == 0
        assert _field_findings(wig) == []


# ---------------------------------------------------------------------------
# The handset
# ---------------------------------------------------------------------------


class TestTheHandsetCaptureReads:
    """The committed ARC486A1 press, read field by field, as the report
    states it: cool, 24 C, fan high, vertical swing on, not powerful."""

    def test_it_is_daikin152_with_its_leader(self):
        reading = fr.read_code(CAPTURE)
        assert reading.protocol_id == "DAIKIN152"
        assert fr.optional_leader_pairs(CAPTURE) > 0

    def test_its_settings(self):
        reading = fr.read_code(CAPTURE)
        read = {spec.name: fr.read_field(reading, spec) for spec in DAIKIN.fields}
        assert read["mode"] == _MODE["cool"]
        assert read["temperature"] == 48
        assert read["fan_speed"] == 0x7
        assert read["power"] == 1
        assert read["powerful"] == 0
        assert read["economy"] == 0
        assert read["sleep"] == 0
        assert read["swing_vertical"] == 0xF
        assert read["swing_horizontal"] == 0x0

    def test_its_fan_reads_as_high(self):
        reading = fr.read_code(CAPTURE)
        value = fr.read_field(reading, FIELD["fan_speed"])
        assert fr.expected_value(FIELD["fan_speed"], "high") == value


# ---------------------------------------------------------------------------
# rewrite_field
# ---------------------------------------------------------------------------


class TestRewriteBuildsFromBothForms:

    @pytest.mark.parametrize("name,value", [
        ("temperature", 52), ("fan_speed", 0x5), ("powerful", 1),
        ("swing_vertical", 0xF),
    ])
    def test_both_forms_build_and_agree(self, name, value):
        spec = FIELD[name]
        settings = _settings("cool", 0x3, 22)
        built = {}
        for leader in (False, True):
            code = _press(settings, leader=leader)
            out = rewrite_field(DAIKIN, code, spec, value)
            assert out is not None, leader
            reading = fr.read_code(out)
            assert reading.protocol_id == "DAIKIN152"
            assert fr.read_field(reading, spec) == value
            for rule in DAIKIN.integrity:
                assert fr.check_integrity(reading, rule) is True
            built[leader] = reading
        assert built[False].frames == built[True].frames

    def test_each_keeps_its_own_form(self):
        spec = FIELD["temperature"]
        settings = _settings("cool", 0x3, 22)
        bare = rewrite_field(DAIKIN, _press(settings, leader=False), spec, 52)
        led = rewrite_field(DAIKIN, _press(settings, leader=True), spec, 52)
        assert fr.optional_leader_pairs(bare) == 0
        assert fr.optional_leader_pairs(led) > 0

    def test_only_the_field_moves(self):
        spec = FIELD["temperature"]
        settings = _settings("heat", 0x7, 22)
        before = fr.read_code(_press(settings, leader=False))
        after = fr.read_code(rewrite_field(
            DAIKIN, _press(settings, leader=False), spec, 52))
        for other in DAIKIN.fields:
            if other.name == "temperature":
                continue
            assert fr.read_field(before, other) == fr.read_field(after, other)
