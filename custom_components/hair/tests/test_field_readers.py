"""The field-reader tier: reading a frame the way its map says to.

Release two of fitting integrity. Every test here is about the ENGINE --
identification, the timing procedure, the closed sets -- and none of it
about what a lattice means; that is `test_field_sweep.py`.

Two properties are pinned before anything else, because both are
promises rather than behaviours:

- **Hard isolation.** Nothing on the transmit side imports this module
  and this module imports nothing from the transmit side. HAIR replays
  AC state frames raw on purpose, and a reader that could re-encode is
  one refactor away from doing it.
- **No inferred thresholds.** The tier reads what the map states. It
  does not reuse the S/L constants the fingerprinter is tuned with, and
  there is no adaptive rule anywhere in it: Mitsubishi Heavy's 48-bit
  family writes a one as 3601 us and closes its frame at 7629 us, a
  ratio of 2.1, and no constant reads that family and Gree's 20 ms gap
  at once (derivation report three, section 2d).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hair import field_readers as fr

MODULE = Path(fr.__file__)
MAPS = fr.maps_dir()

# One Pronto unit at 38 kHz, the carrier every fixture below is written
# at. Used to state test vectors in microseconds and convert once.
US_PER_UNIT = 1_000_000 / 38000.0


def _pronto(pairs: list[tuple[int, int]]) -> str:
    """A Pronto code from (mark us, space us) pairs at 38 kHz."""
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [max(1, round(mark / US_PER_UNIT)),
                  max(0, round(space / US_PER_UNIT))]
    return " ".join(f"{word:04X}" for word in words)


def _map(protocol_id: str) -> fr.FieldMap:
    for candidate in fr.load_maps():
        if candidate.protocol_id == protocol_id:
            return candidate
    raise AssertionError(f"{protocol_id} is not vendored")


# ---------------------------------------------------------------------------
# The promises
# ---------------------------------------------------------------------------


class TestHardIsolation:
    """Read-only forever, pinned in both directions."""

    TX_MODULES = (
        "device_manager", "ir_command", "infrared", "signal_monitor",
        "tx_gate", "send_signal", "pin_retransmit",
    )

    def test_the_reader_imports_no_transmit_module(self):
        source = MODULE.read_text(encoding="utf-8")
        for name in self.TX_MODULES:
            assert f"from .{name}" not in source, name
            assert f"import {name}" not in source, name

    def test_no_transmit_module_imports_the_reader(self):
        for name in self.TX_MODULES:
            path = MODULE.parent / f"{name}.py"
            if not path.is_file():
                continue
            assert "field_readers" not in path.read_text(encoding="utf-8"), \
                name

    def test_nothing_in_the_tier_encodes(self):
        """A reader that can build a frame will eventually be asked to.
        The words are absent because the capability is."""
        source = MODULE.read_text(encoding="utf-8").lower()
        for forbidden in ("def encode", "async_send", "to_pronto",
                          "get_raw_timings", "build_decoded_command"):
            assert forbidden not in source, forbidden

    def test_it_does_not_borrow_the_fingerprinter_constants(self):
        """The S/L threshold is tuned for NEC-family lead-in marks and
        means nothing to a state frame's timing alphabet. Sharing it
        would put a heuristic back in a tier that exists to have none."""
        source = MODULE.read_text(encoding="utf-8")
        assert "PRONTO_SL_THRESHOLD" not in source
        assert "PRONTO_GAP_THRESHOLD" not in source


# ---------------------------------------------------------------------------
# The vendored library
# ---------------------------------------------------------------------------


class TestTheVendoredMaps:
    def test_every_map_loads_and_is_executable(self):
        loaded = {m.protocol_id for m in fr.load_maps()}
        assert loaded == {
            "AUX104", "CHIGO96B", "DAIKIN152", "GREE", "MHI152", "MHI160",
            "MHI48", "MIDEA_COOLIX", "MITSUBISHI144", "OEM112", "TCL112",
            "ZHLT01",
        }

    def test_every_map_states_its_timing_alphabet(self):
        """A map without one cannot be executed and is skipped at load,
        so this also proves none of the twelve was silently dropped."""
        for field_map in fr.load_maps():
            timing = field_map.timing
            assert timing.gap_min > 0, field_map.protocol_id
            assert timing.zero.maximum < timing.one.minimum, \
                field_map.protocol_id

    def test_zero_and_one_windows_leave_no_dead_zone(self):
        """Adjacent by construction (schema v0.2). A gap between them
        costs real coverage: an early cut at these numbers had TCL112
        abstaining on 4.25 percent of its cells for falling between."""
        for field_map in fr.load_maps():
            assert field_map.timing.one.minimum - \
                field_map.timing.zero.maximum <= 1, field_map.protocol_id

    def test_every_named_encoding_is_implemented(self):
        for field_map in fr.load_maps():
            for spec in field_map.fields:
                assert spec.encoding is None or spec.encoding in fr.ENCODINGS

    def test_every_named_rule_is_implemented(self):
        for field_map in fr.load_maps():
            for rule in field_map.integrity:
                assert rule.type in fr.INTEGRITY_RULES

    def test_the_maps_keep_their_confidence_markings(self):
        """Vendored as they stand. If a ratified marking went missing in
        transit the sweep would quietly stop checking a field."""
        zhlt01 = _map("ZHLT01")
        assert zhlt01.field_named("temperature").ratified
        assert not zhlt01.field_named("mode").ratified
        assert _map("OEM112").field_named("temperature").confidence \
            == "provisional"

    def test_a_map_directory_that_is_not_there_is_not_a_crash(self, tmp_path):
        assert fr.load_maps(tmp_path / "nothing") == []

    def test_a_broken_map_is_skipped_not_fatal(self, tmp_path):
        (tmp_path / "broken.yaml").write_text("not: [a, map", encoding="utf-8")
        (tmp_path / "thin.yaml").write_text(
            "protocol_id: THIN\nframe: {total_bits: 8}\n", encoding="utf-8")
        assert fr.load_maps(tmp_path) == []


# ---------------------------------------------------------------------------
# The five-rule decision procedure
# ---------------------------------------------------------------------------


class TestTheTimingProcedure:
    """Schema v0.2, in order: header, gap, zero, one, otherwise stop."""

    def _timing(self) -> fr.FrameTiming:
        return fr.FrameTiming(
            classify="space",
            unit=fr.Window(200, 900, 550),
            zero=fr.Window(250, 1000, 580),
            one=fr.Window(1001, 2300, 1650),
            header_mark=fr.Window(3900, 9500, 6000),
            header_space=fr.Window(4800, 11500, 7400),
            gap_min=2495,
        )

    def _code(self, bits: str, header: bool = True,
              trailer: int = 20000) -> str:
        pairs = [(6000, 7400)] if header else []
        for bit in bits:
            pairs.append((550, 1650 if bit == "1" else 580))
        pairs.append((550, trailer))
        return _pronto(pairs)

    def test_the_header_carries_no_bit(self):
        frames, unreadable = fr.read_frames(
            self._timing(), fr.pronto_microseconds(self._code("1011")))
        assert not unreadable
        assert frames == [[1, 0, 1, 1]]

    def test_a_gap_closes_the_frame(self):
        pairs = [(6000, 7400)]
        for bit in "1011":
            pairs.append((550, 1650 if bit == "1" else 580))
        pairs.append((550, 3000))          # a gap, not a bit
        for bit in "0110":
            pairs.append((550, 1650 if bit == "1" else 580))
        pairs.append((550, 20000))
        frames, unreadable = fr.read_frames(
            self._timing(), fr.pronto_microseconds(_pronto(pairs)))
        assert not unreadable
        assert frames == [[1, 0, 1, 1], [0, 1, 1, 0]]

    def test_a_pulse_outside_every_window_makes_it_unreadable(self):
        """Not skipped and not guessed. Dropping one pulse shifts every
        bit after it, which is how a reader ends up confidently wrong."""
        # 2400 us sits above the one window and below the gap floor:
        # the map states no meaning for it, so neither does the tier.
        pairs = [(6000, 7400), (550, 580), (550, 2400), (550, 20000)]
        frames, unreadable = fr.read_frames(
            self._timing(), fr.pronto_microseconds(_pronto(pairs)))
        assert unreadable
        assert frames == []

    def test_a_mark_outside_its_window_is_unreadable_too(self):
        pairs = [(6000, 7400), (550, 580), (2200, 580), (550, 20000)]
        _frames, unreadable = fr.read_frames(
            self._timing(), fr.pronto_microseconds(_pronto(pairs)))
        assert unreadable

    def test_a_trailing_zero_is_not_a_pulse(self):
        """Pronto writes a zero to mean nothing more. Reading it as a
        timing failed every ZHLT01 cell in the Komeco lattice."""
        code = self._code("1011", trailer=0)
        frames, unreadable = fr.read_frames(
            self._timing(), fr.pronto_microseconds(code))
        assert not unreadable
        assert frames == [[1, 0, 1, 1]]

    def test_header_first_is_what_saves_mitsubishi_heavy(self):
        """MHI48's header space is 7629 us and its frame gap starts at
        5250 us, so the header space IS above the gap floor. Testing the
        gap first would end the frame before its first bit; the schema
        orders the header test first for exactly this family."""
        timing = _map("MHI48").timing
        assert timing.header_space.minimum < timing.gap_min
        pairs = [(5829, 7629)]
        for bit in "10110010":
            pairs.append((549, 3601 if bit == "1" else 1556))
        pairs.append((549, 20000))
        frames, unreadable = fr.read_frames(
            timing, fr.pronto_microseconds(_pronto(pairs)))
        assert not unreadable
        assert frames == [[1, 0, 1, 1, 0, 0, 1, 0]]

    def test_the_bit_order_is_the_map_s_to_state(self):
        bits = [1, 0, 1, 1, 0, 0, 1, 0]
        assert fr.bits_to_bytes(bits, "msb_first") == (0b10110010,)
        assert fr.bits_to_bytes(bits, "lsb_first") == (0b01001101,)

    def test_partial_bytes_are_not_invented(self):
        assert fr.bits_to_bytes([1, 0, 1], "msb_first") == ()

    def test_an_unparseable_code_reads_as_nothing(self):
        assert fr.pronto_microseconds("nonsense") is None
        assert fr.pronto_microseconds("0000 0000 0002 0000 0020") is None


# ---------------------------------------------------------------------------
# Identification
# ---------------------------------------------------------------------------


class TestIdentification:
    def test_signature_and_identity_bytes_together(self):
        """`23 CB 26 01` is MITSUBISHI144 AND OEM112, and `23 CB 26 02`
        is TCL112. A prefix is not an identity, which is why the map
        states a frame signature as well (report three, section 3)."""
        mitsubishi = _map("MITSUBISHI144")
        oem = _map("OEM112")
        assert mitsubishi.identity_bytes == oem.identity_bytes
        assert mitsubishi.frame_layout != oem.frame_layout

    def test_a_code_no_map_claims_says_so(self):
        pairs = [(9000, 4500)]
        for _ in range(32):
            pairs.append((560, 560))
        pairs.append((560, 40000))
        reading = fr.read_code(_pronto(pairs))
        assert not reading.identified
        assert reading.declined in (fr.NO_MAP, fr.UNREADABLE)

    def test_an_empty_library_declines_rather_than_crashes(self):
        assert fr.read_code("0000 006D 0002 0000 0020 0040", []).declined \
            == fr.NO_MAP


# ---------------------------------------------------------------------------
# The closed sets
# ---------------------------------------------------------------------------


def _spec(encoding: str, params: dict, name: str = "x") -> fr.FieldSpec:
    return fr.FieldSpec(
        name=name, frame=0, byte=0, bits="full_byte", encoding=encoding,
        params=params, applies_in={}, applies_not_in={},
        confidence="ratified", mode_traits={},
    )


class TestEncodings:
    def test_linear(self):
        spec = _spec(fr.ENCODING_LINEAR, {"offset": -16, "round": "floor"})
        assert fr.expected_value(spec, 24) == 8
        assert fr.expected_value(spec, 24.5) == 8

    def test_offset_linear(self):
        spec = _spec(fr.ENCODING_OFFSET_LINEAR,
                     {"scale": -1, "offset": 32, "round": "floor"})
        assert fr.expected_value(spec, 25) == 7

    def test_round_nearest_and_floor_differ(self):
        """AUX104 labels half degrees that floor onto one integer field,
        which is why the parameter exists at all."""
        floor = _spec(fr.ENCODING_LINEAR, {"offset": 0, "round": "floor"})
        nearest = _spec(fr.ENCODING_LINEAR, {"offset": 0})
        assert fr.expected_value(floor, 16.5) == 16
        assert fr.expected_value(nearest, 16.5) == 16
        assert fr.expected_value(floor, 16.9) == 16
        assert fr.expected_value(nearest, 16.9) == 17

    def test_reverse_bits4_31_minus_t(self):
        spec = _spec(fr.ENCODING_REVERSE_BITS4, {"special": {32: 0xF}})
        assert fr.expected_value(spec, 16) == 0xF
        assert fr.expected_value(spec, 31) == 0x0
        assert fr.expected_value(spec, 32) == 0xF
        assert fr.expected_value(spec, 40) is None

    def test_enum_nibble_and_enum_byte(self):
        nibble = _spec(fr.ENCODING_ENUM_NIBBLE,
                       {"vocabulary": {"cool": 0x3, "heat": 0x6}})
        wide = _spec(fr.ENCODING_ENUM_BYTE,
                     {"vocabulary": {"on": 0x20, "off": 0x00}})
        assert fr.expected_value(nibble, "cool") == 3
        assert fr.expected_value(wide, "on") == 0x20

    def test_an_enum_reads_numeric_coordinates_too(self):
        """MIDEA_COOLIX's Gray-coded temperature is an enum over the
        integers 17..30, which is how the set stays at six names."""
        spec = _spec(fr.ENCODING_ENUM_NIBBLE, {"vocabulary": {17: 0x0,
                                                              18: 0x1}})
        assert fr.expected_value(spec, 18.0) == 0x1

    def test_a_label_the_vocabulary_does_not_know_is_not_guessed(self):
        spec = _spec(fr.ENCODING_ENUM_NIBBLE, {"vocabulary": {"cool": 0x3}})
        assert fr.expected_value(spec, "turbo") is None

    def test_bitflag(self):
        spec = _spec(fr.ENCODING_BITFLAG, {"true_values": ["off"]})
        assert fr.expected_value(spec, "off") == 1
        assert fr.expected_value(spec, "on") == 0


class TestBitSelectors:
    def _reading(self, *bytes_: int) -> fr.Reading:
        return fr.Reading(protocol_id="X", frames=(tuple(bytes_),))

    @pytest.mark.parametrize(("bits", "expected"), [
        ("full_byte", 0xAB),
        ("high_nibble", 0xA),
        ("low_nibble", 0xB),
        ("bit:0", 1),
        ("bit:6", 0),
        ("mask:0x38", 0x5),
        ("[4,4]", 0xA),
    ])
    def test_selectors(self, bits, expected):
        spec = fr.FieldSpec(
            name="x", frame=0, byte=0, bits=bits, encoding=None, params={},
            applies_in={}, applies_not_in={}, confidence="ratified",
            mode_traits={})
        assert fr.read_field(self._reading(0xAB), spec) == expected

    def test_a_byte_the_frame_does_not_have_reads_as_nothing(self):
        spec = fr.FieldSpec(
            name="x", frame=0, byte=9, bits="full_byte", encoding=None,
            params={}, applies_in={}, applies_not_in={},
            confidence="ratified", mode_traits={})
        assert fr.read_field(self._reading(0xAB), spec) is None


class TestIntegrityRules:
    def _reading(self, *frames: tuple[int, ...]) -> fr.Reading:
        return fr.Reading(protocol_id="X", frames=tuple(frames))

    def _rule(self, kind: str, params: dict) -> fr.IntegrityRule:
        return fr.IntegrityRule(type=kind, params=params,
                                confidence="ratified", description="")

    def test_complement_pairs(self):
        rule = self._rule(fr.RULE_COMPLEMENT_PAIRS,
                          {"frame": 0, "start": 0, "count": 2})
        good = self._reading((0x12, 0xED, 0x34, 0xCB))
        bad = self._reading((0x12, 0xED, 0x34, 0xCC))
        assert fr.check_integrity(good, rule) is True
        assert fr.check_integrity(bad, rule) is False

    def test_checksum_sum(self):
        rule = self._rule(fr.RULE_CHECKSUM_SUM,
                          {"frame": 0, "range": [0, 2], "target_byte": 3,
                           "mod": 256, "offset": 0})
        assert fr.check_integrity(self._reading((1, 2, 3, 6)), rule) is True
        assert fr.check_integrity(self._reading((1, 2, 3, 7)), rule) is False

    def test_nibble_sum(self):
        rule = self._rule(fr.RULE_NIBBLE_SUM, {
            "frame": 0, "nibbles": [[0, "low"], [1, "high"]],
            "target_byte": 2, "bits": "high_nibble", "mod": 16})
        assert fr.check_integrity(self._reading((0x03, 0x40, 0x70)),
                                  rule) is True
        assert fr.check_integrity(self._reading((0x03, 0x40, 0x10)),
                                  rule) is False

    def test_frame_repeat_is_the_same_check_release_one_makes(self):
        """MIDEA_COOLIX and MITSUBISHI144 both state it, and it is the
        byte-level form of CHECK_FRAME_DISAGREEMENT: one press, one
        reading. Shared rather than reimplemented."""
        rule = self._rule(fr.RULE_FRAME_REPEAT, {"frame": 1, "equals": 0})
        same = self._reading((1, 2, 3), (1, 2, 3))
        different = self._reading((1, 2, 3), (1, 2, 4))
        assert fr.check_integrity(same, rule) is True
        assert fr.check_integrity(different, rule) is False

    def test_a_rule_that_cannot_be_evaluated_is_not_a_pass(self):
        """None, not True. A rule addressing a byte the frame does not
        have has not held; saying it did is the same lie as a silent
        field check."""
        rule = self._rule(fr.RULE_CHECKSUM_SUM,
                          {"frame": 0, "range": [0, 9], "target_byte": 9})
        assert fr.check_integrity(self._reading((1, 2)), rule) is None


class TestAppliesWhen:
    def test_not_in_excludes(self):
        spec = fr.FieldSpec(
            name="fan_speed", frame=0, byte=0, bits="full_byte",
            encoding=None, params={}, applies_in={},
            applies_not_in={"mode": ["dry"]}, confidence="ratified",
            mode_traits={})
        assert fr.applies(spec, {"mode": "cool"})
        assert not fr.applies(spec, {"mode": "dry"})

    def test_in_restricts(self):
        spec = fr.FieldSpec(
            name="x", frame=0, byte=0, bits="full_byte", encoding=None,
            params={}, applies_in={"mode": ["cool"]}, applies_not_in={},
            confidence="ratified", mode_traits={})
        assert fr.applies(spec, {"mode": "cool"})
        assert not fr.applies(spec, {"mode": "heat"})


class TestModeTraits:
    def test_the_three_states_are_carried_verbatim(self):
        mode = _map("ZHLT01").field_named("mode")
        assert fr.mode_trait(mode, "cool", "temp") == "varies"
        assert fr.mode_trait(mode, "heat_cool", "temp") == "file_dependent"
        assert fr.mode_trait(mode, "dry", "fan") == "forced"

    def test_a_mode_the_map_never_named_states_nothing(self):
        mode = _map("ZHLT01").field_named("mode")
        assert fr.mode_trait(mode, "turbo", "temp") is None
