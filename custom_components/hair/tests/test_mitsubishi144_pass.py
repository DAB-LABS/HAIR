"""MITSUBISHI144's measurement pass: what the map now reads, and why.

The pass measured the map against every SmartIR file that reads as this
family (19 distinct files across both repositories) and found three
things wrong and one thing missing:

- **The mode mask dropped bit 5.** Byte 6 carries the mode in bits 3-5
  (heat 1, dry 2, cool 3, auto 4, fan 7). Read through ``mask:0x1F``,
  fan_only (0x38) read as cool (0x18) and auto (0x20) as 0x00, so the
  two pairs were one reading each: on the read-bytes key, cool and
  fan_only collided in 11 files. The mask is now 0x3F.
- **Fahrenheit labels were judged as Celsius.** The two Fahrenheit
  sources label 61..88; the linear temperature field expected 45..72 in
  a nibble and failed every one of their cells (396 comb findings, all
  false). The temperature field no longer applies to those labels, and
  a new PROVISIONAL field, ``temperature_fahrenheit``, reads them from
  the remote's own table: low nibble the whole Celsius degree minus 16,
  bit 4 the half degree.
- **ifeel was said to carry a setpoint.** Its only source freezes the
  temperature nibble at 0x8, as dry and fan_only do; the trait is now
  ``invariant``.
- **Bit 4 of byte 7 was unread.** Fahrenheit states 61 and 62 differ
  only there. ``temperature_fahrenheit`` reads it, so they key apart.

MITSUBISHI144 does NOT join the read-bytes list in this round; the
pins at the end say what blocks it.

Every code here is synthetic, built by a test-local encoder from the
map's own timing nominals. Nothing from the corpus is in this file.
"""
from __future__ import annotations

import dataclasses
from collections import defaultdict

import pytest

import custom_components.hair.identity as idm
from custom_components.hair import field_readers as fr
from custom_components.hair import wig_comb
from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import (
    READ_BYTES_VERIFIED,
    SETTING_IDENTITY_VERIFIED,
    read_bytes_key,
)
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, Wig, cell_key

MAPS = {m.protocol_id: m for m in fr.library()}
M144 = MAPS["MITSUBISHI144"]
FIELD = {spec.name: spec for spec in M144.fields}

MODE = {"heat": 0x08, "dry": 0x10, "cool": 0x18, "auto": 0x20,
        "fan_only": 0x38, "ifeel": 0x00}
FAN = {"auto": 0x0, "low": 0x1, "mid": 0x2, "high": 0x3, "highest": 0x4,
       "quiet": 0x5}
VANE = {"auto": 0x0, "top": 0x1, "high": 0x2, "mid": 0x3, "low": 0x4,
        "bottom": 0x5, "swing": 0x7}
#: The remote's Fahrenheit table as the map states it, re-derived here
#: from its rule rather than copied: whole Celsius degree minus 16 in the
#: low nibble, bit 4 for the half degree.
F_TABLE = {61: 16.0, 62: 16.5, 63: 17.0, 64: 17.5, 65: 18.0, 66: 18.5,
           67: 19.0, 68: 20.0, 69: 21.0, 70: 21.5, 71: 22.0, 72: 22.5,
           73: 23.0, 74: 23.5, 75: 24.0, 76: 24.5, 77: 25.0, 78: 25.5,
           79: 26.0, 80: 26.5, 81: 27.0, 82: 27.5, 83: 28.0, 84: 28.5,
           85: 29.0, 86: 29.5, 87: 30.0, 88: 31.0}


def _temp_byte(celsius: float) -> int:
    whole = int(celsius)
    return (whole - 16) | (0x10 if celsius - whole else 0)


# ---------------------------------------------------------------------------
# A MITSUBISHI144 code from bytes. Test-local: the reader tier must never
# gain an encoder (test_field_readers).
# ---------------------------------------------------------------------------

_UNIT_US = 0x6D * 0.241246
#: The map states only a floor for the gap between the two frames
#: (frame_gap_us.min); any space well above it closes the frame.
_GAP_US = 6 * M144.timing.gap_min
_TAIL_US = 80000


def _frame(mode: str = "cool", temp: float = 24, fan: str = "auto",
           vane: str = "auto", *, power: bool = True, clock: int = 0x00,
           b6_bit6: bool = False, b8_high: int = 0x3, b9_high: int = 0x40,
           raw_temp: int | None = None) -> list[int]:
    """One 18-byte frame from the map's positions; checksum last."""
    data = [0x23, 0xCB, 0x26, 0x01, 0x00] + [0x00] * 12
    data[5] = 0x20 if power else 0x00
    data[6] = MODE[mode] | (0x40 if b6_bit6 else 0)
    data[7] = raw_temp if raw_temp is not None else _temp_byte(temp)
    data[8] = (b8_high << 4) | {"cool": 6, "auto": 6, "ifeel": 6, "dry": 2}.get(mode, 0)
    data[9] = b9_high | (VANE[vane] << 3) | FAN[fan]
    data[10] = clock
    return [*data, sum(data) & 0xFF]


def _pronto(frame: list[int]) -> str:
    t = M144.timing
    pairs: list[tuple[float, float]] = []
    for n in range(2):  # the frame is sent twice (frame_repeat)
        pairs.append((t.header_mark.nominal, t.header_space.nominal))
        for byte in frame:
            for bit in range(8):
                one = (byte >> bit) & 1
                pairs.append((t.unit.nominal,
                              t.one.nominal if one else t.zero.nominal))
        pairs.append((t.unit.nominal, _GAP_US if n == 0 else _TAIL_US))
    words = [0, 0x6D, len(pairs), 0]
    for mark, space in pairs:
        words += [max(1, round(mark / _UNIT_US)),
                  max(1, round(space / _UNIT_US))]
    return " ".join(f"{w:04X}" for w in words)


def _read(frame: list[int]) -> fr.Reading:
    reading = fr.read_code(_pronto(frame))
    assert reading.protocol_id == "MITSUBISHI144"
    return reading


def _key(frame: list[int], field_map: fr.FieldMap = M144) -> str | None:
    return read_bytes_key(field_map, _read(frame).frames)


def _wig(cells: list[tuple[str, str, str | None, float, list[int]]]) -> Wig:
    climate = ClimateMatrix(
        min_temp=min(c[3] for c in cells), max_temp=max(c[3] for c in cells),
        precision=1.0, modes=sorted({c[0] for c in cells}),
        fan_modes=sorted({c[1] for c in cells}),
        swing_modes=sorted({c[2] for c in cells if c[2]}),
        off=_pronto(_frame(power=False)),
        cells=[ClimateCell(mode=m, fan=f, swing=s, temp=float(t),
                           pronto=_pronto(frame))
               for m, f, s, t, frame in cells],
    )
    return Wig(name="AC", signals=[], climate=climate)


def _field_findings(wig: Wig) -> list[tuple[str, str]]:
    return sorted(
        (f.keys[0], f.params.get("field"))
        for f in wig_comb.comb_wig(wig).findings
        if f.check == wig_comb.CHECK_FIELD_MISMATCH
    )


# ---------------------------------------------------------------------------
# The encoder is only trusted because the reader reads it back
# ---------------------------------------------------------------------------


class TestTheEncoder:

    def test_it_reads_as_the_family_with_both_rules_holding(self):
        reading = _read(_frame())
        assert [len(f) for f in reading.frames] == [18, 18]
        for rule in M144.integrity:
            assert fr.check_integrity(reading, rule) is True, rule.type

    @pytest.mark.parametrize("mode", sorted(MODE))
    def test_every_mode_reads_back(self, mode):
        assert fr.read_field(_read(_frame(mode)), FIELD["mode"]) == MODE[mode]


# ---------------------------------------------------------------------------
# What the map now says
# ---------------------------------------------------------------------------


class TestTheMap:

    def test_mode_reads_bits_0_to_5(self):
        spec = FIELD["mode"]
        assert (spec.frame, spec.byte, spec.bits) == (0, 6, "mask:0x3F")
        assert spec.ratified

    @pytest.mark.parametrize("label,value", [
        ("heat", 0x08), ("dry", 0x10), ("cool", 0x18), ("auto", 0x20),
        ("heat_cool", 0x20), ("fan_only", 0x38), ("ifeel", 0x00)])
    def test_the_mode_vocabulary(self, label, value):
        assert fr.expected_value(FIELD["mode"], label) == value

    def test_fan_only_and_auto_are_not_cool_and_ifeel_any_more(self):
        spec = FIELD["mode"]
        assert fr.expected_value(spec, "fan_only") != fr.expected_value(spec, "cool")
        assert fr.expected_value(spec, "auto") != fr.expected_value(spec, "ifeel")

    def test_bit_6_is_not_mode(self):
        """Set on every cell of one file and most of another, named by no
        label anywhere: it must not turn a cool press into another mode."""
        plain = _read(_frame("cool"))
        flagged = _read(_frame("cool", b6_bit6=True))
        assert fr.read_field(flagged, FIELD["mode"]) == 0x18
        assert fr.read_field(plain, FIELD["mode"]) == 0x18

    @pytest.mark.parametrize("mode", ["dry", "fan_only", "ifeel"])
    def test_temperature_is_frozen_in(self, mode):
        assert fr.mode_trait(FIELD["mode"], mode, "temp") == "invariant"
        assert not fr.applies(FIELD["temperature"], {"mode": mode, "temp": 24.0})

    def test_temperature_leaves_fahrenheit_labels_alone(self):
        spec = FIELD["temperature"]
        for label in F_TABLE:
            assert not fr.applies(spec, {"mode": "heat", "temp": float(label)}), label
        for label in range(16, 32):
            assert fr.applies(spec, {"mode": "heat", "temp": float(label)}), label

    def test_fahrenheit_is_located_and_provisional(self):
        spec = FIELD["temperature_fahrenheit"]
        assert (spec.frame, spec.byte, spec.bits) == (0, 7, "mask:0x1F")
        assert spec.coordinate == "temp"
        assert not spec.ratified
        assert spec.encoding == fr.ENCODING_ENUM_BYTE

    @pytest.mark.parametrize("label", sorted(F_TABLE))
    def test_the_fahrenheit_table(self, label):
        assert fr.expected_value(FIELD["temperature_fahrenheit"], float(label)) == (
            _temp_byte(F_TABLE[label])
        )

    def test_fahrenheit_applies_to_fahrenheit_labels_only(self):
        spec = FIELD["temperature_fahrenheit"]
        assert fr.applies(spec, {"mode": "cool", "temp": 70.0})
        assert not fr.applies(spec, {"mode": "cool", "temp": 24.0})
        assert not fr.applies(spec, {"mode": "dry", "temp": 70.0})

    def test_every_other_field_is_where_it_was(self):
        assert [(s.name, s.byte, s.bits, s.confidence) for s in M144.fields] == [
            ("temperature", 7, "low_nibble", "ratified"),
            ("mode", 6, "mask:0x3F", "ratified"),
            ("fan_speed", 9, "mask:0x07", "ratified"),
            ("swing", 9, "mask:0x38", "provisional"),
            ("power", 5, "full_byte", "ratified"),
            ("temperature_fahrenheit", 7, "mask:0x1F", "provisional"),
        ]


# ---------------------------------------------------------------------------
# The collisions the pass resolved
# ---------------------------------------------------------------------------


def _old_mode_map() -> fr.FieldMap:
    """The map as it stood for mode: mask 0x1F and no Fahrenheit field."""
    fields = [
        dataclasses.replace(s, bits="mask:0x1F") if s.name == "mode" else s
        for s in M144.fields if s.name != "temperature_fahrenheit"
    ]
    return dataclasses.replace(M144, fields=fields)


class TestTheCollisionsItResolved:

    @pytest.mark.parametrize("fan", ["auto", "low", "high"])
    def test_cool_and_fan_only_read_apart(self, fan):
        """The files send cool and fan_only with the same nibbles apart
        from mode (and byte 8's mode-tracking nibble, which no field
        reads). Under the old mask the two were one key."""
        cool = _frame("cool", 24, fan)
        fan_only = _frame("fan_only", 24, fan)
        fan_only[8] = cool[8]
        fan_only[17] = sum(fan_only[:17]) & 0xFF
        assert _key(cool, _old_mode_map()) == _key(fan_only, _old_mode_map())
        assert _key(cool) != _key(fan_only)

    def test_auto_and_ifeel_read_apart(self):
        auto = _frame("auto", 24)
        ifeel = _frame("ifeel", 24)
        assert _key(auto, _old_mode_map()) == _key(ifeel, _old_mode_map())
        assert _key(auto) != _key(ifeel)

    def test_61_and_62_fahrenheit_read_apart(self):
        """Bit 4 of byte 7 is the only difference between them."""
        low = _frame("heat", F_TABLE[61])
        high = _frame("heat", F_TABLE[62])
        assert [a ^ b for a, b in zip(low[:17], high[:17], strict=True)] == (
            [0] * 7 + [0x10] + [0] * 9
        )
        assert _key(low, _old_mode_map()) == _key(high, _old_mode_map())
        assert _key(low) != _key(high)

    def test_every_fahrenheit_label_has_a_key_of_its_own(self):
        keys = {_key(_frame("cool", F_TABLE[label])) for label in F_TABLE}
        assert len(keys) == len(F_TABLE)


# ---------------------------------------------------------------------------
# What stays out of identity, on purpose
# ---------------------------------------------------------------------------


class TestWhatIsNotRead:
    """Bits that vary in the files without any label explaining them. A
    key that read them would split one labelled state into several and a
    real press would miss its cell; see the pass report, section 3."""

    @pytest.mark.parametrize("change", [
        {"clock": 0x8F},          # byte 10, the capture-time clock
        {"b9_high": 0x80},        # byte 9 bits 6-7, 0x40 or 0x80
        {"b8_high": 0xC},         # byte 8 high nibble, constant per file
        {"b6_bit6": True},        # byte 6 bit 6
    ])
    def test_it_does_not_move_the_key(self, change):
        assert _key(_frame("cool", 22, "low", "mid", **change)) == (
            _key(_frame("cool", 22, "low", "mid"))
        )

    @pytest.mark.parametrize("change", [
        {"temp": 23}, {"mode": "heat"}, {"fan": "high"}, {"vane": "swing"},
        {"power": False}, {"temp": 22.5},
    ])
    def test_every_field_the_map_reads_does(self, change):
        base = {"mode": "cool", "temp": 22, "fan": "low", "vane": "mid"}
        assert _key(_frame(**{**base, **change})) != _key(_frame(**base))


# ---------------------------------------------------------------------------
# applies_when, through the comb
# ---------------------------------------------------------------------------


class TestTheCombReadsWhatTheLabelsSay:

    def test_a_fahrenheit_lattice_is_clean(self):
        """Before the pass every cell here was a temperature finding."""
        cells = [(mode, "auto", "auto", label, _frame(mode, F_TABLE[label]))
                 for mode in ("heat", "cool") for label in F_TABLE]
        assert _field_findings(_wig(cells)) == []

    def test_a_wrong_half_degree_is_read_but_not_judged(self):
        """Provisional: part of identity, never a finding."""
        cells = [("heat", "auto", "auto", label, _frame("heat", F_TABLE[label]))
                 for label in F_TABLE]
        cells[1] = ("heat", "auto", "auto", 62, _frame("heat", F_TABLE[61]))
        assert _field_findings(_wig(cells)) == []

    def test_a_celsius_lattice_still_finds_a_shifted_cell(self):
        cells = [("cool", "low", "mid", t, _frame("cool", t, "low", "mid"))
                 for t in range(16, 32)]
        cells[4] = ("cool", "low", "mid", 20, _frame("cool", 21, "low", "mid"))
        assert _field_findings(_wig(cells)) == [
            ("cool/low/mid/20", "comb.field.temperature")]

    def test_fan_only_reads_as_itself(self):
        cells = [("fan_only", fan, "auto", t, _frame("fan_only", 24, fan))
                 for fan in ("auto", "low", "high") for t in (18, 24, 30)]
        cells += [("cool", fan, "auto", t, _frame("cool", t, fan))
                  for fan in ("auto", "low", "high") for t in (18, 24, 30)]
        assert _field_findings(_wig(cells)) == []

    def test_a_fan_only_label_on_cool_bytes_is_now_a_finding(self):
        """Invisible under the old mask: cool and fan_only read alike."""
        cells = [("cool", "low", "auto", t, _frame("cool", t, "low"))
                 for t in (18, 24, 30)]
        cells += [("fan_only", "low", "auto", t, _frame("fan_only", 24, "low"))
                  for t in (18, 24)]
        cells += [("fan_only", "low", "auto", 30, _frame("cool", 24, "low"))]
        assert _field_findings(_wig(cells)) == [
            ("fan_only/low/auto/30", "comb.field.mode")]


# ---------------------------------------------------------------------------
# The list, and what keeps the family off it
# ---------------------------------------------------------------------------


class TestNotOnTheListYet:

    def test_it_is_on_neither_list(self):
        assert "MITSUBISHI144" not in READ_BYTES_VERIFIED
        assert "MITSUBISHI144" not in SETTING_IDENTITY_VERIFIED

    def test_so_its_byte_hash_is_still_the_timing_hash(self):
        code = _pronto(_frame())
        assert EventParser.pronto_read_key(code) is None

    def test_the_blocker_a_frozen_mode_is_one_press_under_many_labels(
            self, monkeypatch):
        """Why it does not join. dry, fan_only and ifeel carry no setpoint,
        so a remote sends one reading for every labelled temperature there,
        and the files store that one reading under every temperature label
        of the mode (347 of the 357 read-key collisions the pass counted on
        the family's files are exactly this). The read key is then shared
        by cells with different keys, which the index refuses and the
        distinctness sweep counts as a collision, so on the list every dry
        press would name nothing.
        Pinned so the engine round that teaches both about applies_when
        sees this flip."""
        monkeypatch.setattr(
            idm, "READ_BYTES_VERIFIED",
            frozenset({*READ_BYTES_VERIFIED, "MITSUBISHI144"}))
        by_key: dict[str | None, set[str]] = defaultdict(set)
        for temp in (18, 24, 30):
            cell = ClimateCell(mode="dry", fan="low", swing="auto",
                               temp=float(temp),
                               pronto=_pronto(_frame("dry", 24, "low")))
            by_key[EventParser.pronto_read_key(cell.pronto)].add(cell_key(cell))
        assert None not in by_key
        assert [len(v) for v in by_key.values()] == [3]
