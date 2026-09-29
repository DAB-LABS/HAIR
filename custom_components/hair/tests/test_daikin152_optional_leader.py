"""Schema v0.6: DAIKIN152's leader block is optional (GH #183).

A Daikin ARC-series handset sends a short leader block, then an 8-byte
constant frame, an 8-byte frame carrying the remote's clock, and the
19-byte frame that carries the settings. The map has always described
all four, and so a lattice rendered without the leader -- three frames,
which is what an encoder may well send -- met a four-frame layout and
read as nothing at all. Its Off, captured from a handset, carried the
leader and read fine, so one remote was split down the middle.

``frame.optional_leader`` says frame 0 may be absent. The reader lays
the frames that did arrive on indices 1..3 when it is, so every index
the map states names the same frame either way and nothing renumbers.

EVERY CODE IN THIS FILE IS SYNTHETIC. They are built here, from the
protocol's constant frame and the map's own timing nominals, by a small
encoder that lives in this test file and nowhere else (the reader tier
is forbidden one, and ``test_field_readers`` says so). None of them is a
code from the #183 wig or from any other contributed file.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from custom_components.hair import field_readers as fr
from custom_components.hair import wig_comb
from custom_components.hair.identity import (
    TIER_BYTE_HASH,
    setting_frame_spans,
    setting_identity_edges,
)
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    cell_key,
)
from custom_components.hair.wig_identity import wig_signal_identity

from .test_cell_index_shared_keys import _match

MAPS_DIR = Path(fr.__file__).parent / "field_maps"
MAPS = {m.protocol_id: m for m in fr.library()}
DAIKIN = MAPS["DAIKIN152"]


# ---------------------------------------------------------------------------
# A synthetic encoder, test-side only
# ---------------------------------------------------------------------------

#: 38 kHz. The word Pronto writes for it, and the microseconds per unit.
_CARRIER_WORD = 0x006D
_UNIT_US = _CARRIER_WORD * 0.241246

#: The map's own nominals (DAIKIN152.yaml, frame.timing).
_HEADER = (3448, 1740)
_MARK = 427
_ZERO = 458
_ONE = 1312
#: After the leader: short of a receiver's split threshold, the way a
#: handset sends it, so the leader rides into frame 0's capture.
_LEADER_GAP = 25000
#: Between frames: long enough that a receiver splits there.
_FRAME_GAP = 35000

#: The constant frame, and the clock frame's constant head.
_CONSTANT = [0x11, 0xDA, 0x27, 0x00, 0xC5, 0x00, 0x00, 0xD7]
_CLOCK_HEAD = [0x11, 0xDA, 0x27, 0x00, 0x42]

_MODES = {"cool": 0x3, "heat": 0x4, "dry": 0x2}
_FANS = {"auto": 0xA, "low": 0x3, "high": 0x7}


def _with_sum(data: list[int]) -> list[int]:
    return [*data, sum(data) & 0xFF]


def _clock(minutes: int) -> list[int]:
    return _with_sum([*_CLOCK_HEAD, minutes & 0xFF, (minutes >> 8) & 0x07])


def _settings(mode: str, fan: str, temp: int, power: int = 1) -> list[int]:
    data = [0x11, 0xDA, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x06, 0x60, 0x00, 0x00, 0xC1, 0x00, 0x00]
    data[5] = (_MODES[mode] << 4) | power
    data[6] = temp * 2
    data[8] = _FANS[fan] << 4
    return _with_sum(data)


def _frame_pairs(data: list[int], gap: int) -> list[tuple[int, int]]:
    pairs = [_HEADER]
    for byte in data:
        for bit in range(8):
            pairs.append((_MARK, _ONE if (byte >> bit) & 1 else _ZERO))
    pairs.append((_MARK, gap))
    return pairs


def _leader_pairs(bits: int = 5) -> list[tuple[int, int]]:
    return [(_MARK, _ZERO)] * bits + [(_MARK, _LEADER_GAP)]


def _pronto(pairs: list[tuple[int, int]]) -> str:
    words = []
    for mark, space in pairs:
        words.append(max(1, round(mark / _UNIT_US)))
        words.append(max(1, round(space / _UNIT_US)))
    head = [0x0000, _CARRIER_WORD, len(pairs), 0x0000]
    return " ".join(f"{word:04X}" for word in [*head, *words])


def _press(settings: list[int], *, clock: int = 600, leader: bool,
           leader_bits: int = 5) -> str:
    pairs = _leader_pairs(leader_bits) if leader else []
    pairs += _frame_pairs(_CONSTANT, _FRAME_GAP)
    pairs += _frame_pairs(_clock(clock), _FRAME_GAP)
    pairs += _frame_pairs(settings, _FRAME_GAP)
    return _pronto(pairs)


#: The rendered lattice's clock, and a handset's, which never agree.
_STORED_CLOCK = 1353
_HANDSET_CLOCK = 622

_STATES = [
    (mode, fan, temp)
    for mode in ("cool", "heat")
    for fan in ("auto", "low", "high")
    for temp in (18, 22, 26, 30)
]


def _lattice() -> ClimateMatrix:
    """Leaderless states, as rendered; an Off with the leader, as captured."""
    cells = [
        ClimateCell(mode=mode, fan=fan, temp=float(temp), pronto=_press(
            _settings(mode, fan, temp), clock=_STORED_CLOCK, leader=False))
        for mode, fan, temp in _STATES
    ]
    off = _press(_settings("cool", "auto", 22, power=0),
                 clock=_STORED_CLOCK, leader=True)
    return ClimateMatrix(
        min_temp=18.0, max_temp=30.0, precision=1.0, modes=["cool", "heat"],
        fan_modes=["auto", "high", "low"], swing_modes=[], off=off,
        cells=cells,
    )


def _map_without_the_key() -> fr.FieldMap:
    raw = yaml.safe_load((MAPS_DIR / "DAIKIN152.yaml").read_text("utf-8"))
    del raw["frame"]["optional_leader"]
    parsed = fr.parse_map(raw)
    assert parsed is not None
    return parsed


# ---------------------------------------------------------------------------
# The premise: the encoder builds what the map describes
# ---------------------------------------------------------------------------


class TestTheSyntheticCodesAreWhatTheySayTheyAre:

    def test_the_map_declares_it(self):
        assert DAIKIN.optional_leader is True
        assert DAIKIN.frame_layout == [5, 64, 64, 152]
        assert DAIKIN.setting_frames == [3]

    def test_with_the_leader_the_press_is_four_frames(self):
        frames, failed = fr.read_frames(
            DAIKIN.timing, fr.pronto_microseconds(
                _press(_settings("cool", "auto", 22), leader=True)))
        assert not failed
        assert [len(f) for f in frames] == [5, 64, 64, 152]

    def test_without_it_the_press_is_three(self):
        frames, failed = fr.read_frames(
            DAIKIN.timing, fr.pronto_microseconds(
                _press(_settings("cool", "auto", 22), leader=False)))
        assert not failed
        assert [len(f) for f in frames] == [64, 64, 152]

    def test_a_leaderless_press_read_as_nothing_without_the_key(self):
        """What #183 was: the same map, less the key, refuses it."""
        bare = _map_without_the_key()
        code = _press(_settings("cool", "auto", 22), leader=False)
        assert not fr.read_code(code, [bare]).identified
        assert fr.read_code(code, [DAIKIN]).identified


# ---------------------------------------------------------------------------
# One state, both shapes, one reading
# ---------------------------------------------------------------------------


class TestBothShapesReadAlike:

    @pytest.mark.parametrize("mode,fan,temp", _STATES)
    def test_the_readings_are_identical(self, mode, fan, temp):
        settings = _settings(mode, fan, temp)
        bare = fr.read_code(_press(settings, leader=False))
        led = fr.read_code(_press(settings, leader=True))
        assert bare.protocol_id == led.protocol_id == "DAIKIN152"
        assert bare.frames == led.frames
        assert len(bare.frames) == len(DAIKIN.frame_layout)

    def test_every_index_names_the_same_frame(self):
        """No renumbering: frame 3 is the settings frame either way."""
        settings = _settings("heat", "high", 26)
        for leader in (False, True):
            reading = fr.read_code(_press(settings, leader=leader))
            assert reading.frames[0] == ()
            assert list(reading.frames[3]) == settings
            for spec in DAIKIN.fields:
                assert fr.read_field(reading, spec) is not None, spec.name

    def test_every_rule_is_judged_on_both(self):
        settings = _settings("cool", "low", 18)
        for leader in (False, True):
            reading = fr.read_code(_press(settings, leader=leader))
            for rule in DAIKIN.integrity:
                assert fr.check_integrity(reading, rule) is True

    def test_a_six_bit_leader_is_still_the_leader(self):
        """Some handsets and some renderings send one more pulse in it."""
        settings = _settings("cool", "auto", 22)
        six = fr.read_code(_press(settings, leader=True, leader_bits=6))
        assert six.frames == fr.read_code(_press(settings, leader=False)).frames

    @pytest.mark.parametrize("mode,fan,temp", _STATES)
    def test_the_settings_frame_identity_is_the_same(self, mode, fan, temp):
        settings = _settings(mode, fan, temp)
        bare = _press(settings, leader=False)
        led = _press(settings, leader=True)
        spans_bare = setting_frame_spans(fr.pronto_microseconds(bare))
        spans_led = setting_frame_spans(fr.pronto_microseconds(led))
        assert spans_bare is not None and spans_led is not None
        assert len(spans_bare) == len(spans_led) == 1
        assert setting_identity_edges(fr.pronto_microseconds(bare)) == \
            setting_identity_edges(fr.pronto_microseconds(led))
        assert wig_signal_identity(bare).byte_hash == \
            wig_signal_identity(led).byte_hash

    def test_the_clock_frame_stays_out_of_it(self):
        settings = _settings("cool", "high", 22)
        one = _press(settings, clock=10, leader=False)
        other = _press(settings, clock=1000, leader=True)
        assert wig_signal_identity(one).byte_hash == \
            wig_signal_identity(other).byte_hash


# ---------------------------------------------------------------------------
# The #183 shape: a handset press against a rendered lattice
# ---------------------------------------------------------------------------


class TestAHandsetPressFindsTheRenderedState:

    def test_the_premise_off_carries_the_leader_the_states_do_not(self):
        matrix = _lattice()
        assert fr.optional_leader_pairs(matrix.off) > 0
        assert all(fr.optional_leader_pairs(c.pronto) == 0
                   for c in matrix.cells)

    @pytest.mark.parametrize("mode,fan,temp", _STATES)
    def test_a_press_with_the_leader_and_a_new_clock_matches_its_cell(
            self, mode, fan, temp):
        matrix = _lattice()
        index = build_cell_index(matrix)
        press = _press(_settings(mode, fan, temp), clock=_HANDSET_CLOCK,
                       leader=True)
        assert _match(index, press) == (
            f"{mode}/{fan}/{temp}", None, TIER_BYTE_HASH)

    def test_the_stored_states_match_themselves(self):
        matrix = _lattice()
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            assert _match(index, cell.pronto) == (
                cell_key(cell), None, TIER_BYTE_HASH)


class TestOffStillMatchesOnlyOff:

    def test_the_stored_off_matches_off(self):
        matrix = _lattice()
        index = build_cell_index(matrix)
        hit = _match(index, matrix.off)
        assert hit is not None and hit[1] == "off"

    def test_a_handset_off_with_a_new_clock_matches_off(self):
        matrix = _lattice()
        index = build_cell_index(matrix)
        press = _press(_settings("cool", "auto", 22, power=0),
                       clock=_HANDSET_CLOCK, leader=True)
        hit = _match(index, press)
        assert hit is not None and hit[1] == "off"

    def test_so_does_one_sent_without_the_leader(self):
        matrix = _lattice()
        index = build_cell_index(matrix)
        press = _press(_settings("cool", "auto", 22, power=0),
                       clock=_HANDSET_CLOCK, leader=False)
        hit = _match(index, press)
        assert hit is not None and hit[1] == "off"

    @pytest.mark.parametrize("leader", [False, True])
    def test_no_state_press_matches_off(self, leader):
        matrix = _lattice()
        index = build_cell_index(matrix)
        for mode, fan, temp in _STATES:
            press = _press(_settings(mode, fan, temp),
                           clock=_HANDSET_CLOCK, leader=leader)
            hit = _match(index, press)
            assert hit is not None, (mode, fan, temp)
            assert hit[1] != "off", (mode, fan, temp)

    def test_off_matches_no_state(self):
        matrix = _lattice()
        index = build_cell_index(matrix)
        hit = _match(index, matrix.off)
        assert hit is not None and hit[0] not in {
            cell_key(cell) for cell in matrix.cells}


# ---------------------------------------------------------------------------
# The comb
# ---------------------------------------------------------------------------


class TestTheCombSeesOneShape:

    def test_frame_shape_does_not_report_the_leader(self):
        """A lattice holding both shapes. Without the leader's pairs
        dropped, every leader-bearing cell reads as a different frame 0."""
        rows = []
        for number, (mode, fan, temp) in enumerate(_STATES):
            rows.append((f"{mode}/{fan}/{temp}", _press(
                _settings(mode, fan, temp), leader=number % 3 == 0)))
        assert wig_comb._shape_findings(rows, strict=True) == []

    def test_a_lattice_that_does_not_mix_is_compared_as_before(self, monkeypatch):
        """Every handset-captured lattice carries the leader on every
        code. Its shape findings, including those on codes no map can
        read, are exactly what they were without the rule."""
        from .test_cell_index_shared_keys import _pack_matrix

        matrix = _pack_matrix("DAIKIN152.json")
        rows = [(cell_key(cell), cell.pronto) for cell in matrix.cells]
        assert any(fr.optional_leader_pairs(p) for _k, p in rows)
        assert 0 not in {fr.optional_leader_pairs(p) for _k, p in rows}
        with_rule = wig_comb._shape_findings(rows, strict=True)
        monkeypatch.setattr(fr, "optional_leader_pairs", lambda _p: None)
        assert wig_comb._shape_findings(rows, strict=True) == with_rule

    def test_an_unreadable_code_in_a_lattice_that_does_not_mix(self):
        """Every code carries the leader, and one has a pulse outside the
        map's windows, so no map reads it and nothing can say where its
        leader ends. Setting the others' leaders aside would leave that
        one looking a leader longer than all of them. Not mixing, nobody
        is set aside, and the shapes are all alike."""
        rows = [(f"{m}/{f}/{t}", _press(_settings(m, f, t), leader=True))
                for m, f, t in _STATES]
        pairs = (_leader_pairs()
                 + _frame_pairs(_CONSTANT, _FRAME_GAP)
                 + _frame_pairs(_clock(600), _FRAME_GAP)
                 + _frame_pairs(_settings("cool", "low", 23), _FRAME_GAP))
        index = len(_leader_pairs()) + 20
        pairs[index] = (1100, pairs[index][1])  # a mark no window holds
        odd = _pronto(pairs)
        assert fr.optional_leader_pairs(odd) is None
        assert not fr.read_code(odd).identified
        rows.append(("cool/low/23", odd))
        assert wig_comb._shape_findings(rows, strict=True) == []

    def test_a_real_shape_fault_is_still_reported(self):
        rows = [(f"{m}/{f}/{t}", _press(_settings(m, f, t), leader=False))
                for m, f, t in _STATES]
        damaged = _pronto(
            _leader_pairs()
            + _frame_pairs(_CONSTANT, _FRAME_GAP)
            + _frame_pairs(_clock(600)[:-1], _FRAME_GAP)  # a byte short
            + _frame_pairs(_settings("cool", "low", 22), _FRAME_GAP))
        rows.append(("cool/low/22", damaged))
        findings = wig_comb._shape_findings(rows, strict=True)
        assert [f.keys for f in findings] == [["cool/low/22"]]

    def test_frame_disagreement_says_the_same_about_both_shapes(self):
        """The repeat check compares a press with its own repeats, and
        one press has none either way. It needs no leader rule: the pin
        is that the leader does not change its answer."""
        for mode, fan, temp in _STATES:
            settings = _settings(mode, fan, temp)
            bare = wig_comb._repeat_reading(_press(settings, leader=False))
            led = wig_comb._repeat_reading(_press(settings, leader=True))
            assert bare == led == (wig_comb.DECLINE_TOO_FEW_FRAMES, None)

    def test_the_field_checks_now_run_on_a_leaderless_lattice(self):
        matrix = _lattice()
        report = wig_comb.comb_wig(Wig(name="AC", signals=[], climate=matrix))
        coverage = report.coverage.to_dict()
        assert coverage["protocol"]["id"] == "DAIKIN152"
        assert coverage["protocol"]["readable"] == len(matrix.cells) + 1
        assert coverage["checks"]["field-mismatch"]["checked"] > 0
        assert not [f for f in report.findings
                    if f.check in (wig_comb.CHECK_FIELD_MISMATCH,
                                   wig_comb.CHECK_FRAME_INTEGRITY)]


# ---------------------------------------------------------------------------
# Nobody else
# ---------------------------------------------------------------------------


OTHERS = [m for m in fr.library() if m.protocol_id != "DAIKIN152"]


class TestEveryOtherFamilyIsUnchanged:

    def test_only_daikin152_declares_it(self):
        assert [m.protocol_id for m in fr.library() if m.optional_leader] \
            == ["DAIKIN152"]

    @pytest.mark.parametrize("field_map", OTHERS,
                             ids=[m.protocol_id for m in OTHERS])
    def test_alignment_is_the_old_layout_test(self, field_map):
        """Whole layout or nothing: the frames come back untouched when
        they fit, and a code one frame short is still refused."""
        layout = field_map.frame_layout
        whole = [[0] * bits for bits in layout]
        assert fr.aligned_frames(field_map, whole) == whole
        assert fr._matches_layout(field_map, whole)
        if len(layout) > 1:
            short = [[0] * bits for bits in layout[1:]]
            assert fr.aligned_frames(field_map, short) is None
            assert not fr._matches_layout(field_map, short)

    @pytest.mark.parametrize("field_map", OTHERS,
                             ids=[m.protocol_id for m in OTHERS])
    def test_their_codes_carry_no_optional_leader(self, field_map):
        from .test_cell_index_shared_keys import _pack_matrix

        matrix = _pack_matrix(f"{field_map.protocol_id}.json")
        for cell in matrix.cells[:200]:
            assert fr.optional_leader_pairs(cell.pronto) is None

    def test_daikin152s_own_codes_read_as_they_did(self):
        """The field pack is leader-bearing, like every handset capture
        measured. With the key or without it, each code reads the same."""
        from .test_cell_index_shared_keys import _pack_matrix

        bare = _map_without_the_key()
        matrix = _pack_matrix("DAIKIN152.json")
        for cell in matrix.cells:
            with_key = fr.read_code(cell.pronto, [DAIKIN])
            without = fr.read_code(cell.pronto, [bare])
            assert with_key.frames == without.frames
            assert with_key.declined == without.declined


# ---------------------------------------------------------------------------
# What the parser accepts
# ---------------------------------------------------------------------------


class TestOnlyAnUnreadFrameCanBeOptional:

    def _raw(self) -> dict:
        return copy.deepcopy(yaml.safe_load(
            (MAPS_DIR / "DAIKIN152.yaml").read_text("utf-8")))

    def test_the_document_declares_it(self):
        assert self._raw()["frame"]["optional_leader"] is True

    def test_only_true_declares_it(self):
        raw = self._raw()
        raw["frame"]["optional_leader"] = "yes"
        assert fr.parse_map(raw).optional_leader is False

    def test_not_when_frame_0_is_a_setting_frame(self):
        raw = self._raw()
        raw["frame"]["setting_frames"] = [3, 0]
        assert fr.parse_map(raw).optional_leader is False

    def test_not_when_an_identity_byte_is_on_it(self):
        raw = self._raw()
        raw["frame"]["identity_bytes"].append([0, 0, 0x00])
        assert fr.parse_map(raw).optional_leader is False

    def test_not_when_a_rule_reads_it(self):
        raw = self._raw()
        raw["integrity"].append({
            "type": "checksum_sum",
            "params": {"frame": 0, "range": [0, 0], "target_byte": 0},
            "confidence": "ratified",
        })
        assert fr.parse_map(raw).optional_leader is False

    def test_not_when_a_field_reads_it(self):
        raw = self._raw()
        raw["fields"][0]["frame"] = 0
        assert fr.parse_map(raw).optional_leader is False

    def test_not_when_frame_0_carries_a_byte(self):
        raw = self._raw()
        raw["frame"]["frame_layout"] = [8, 64, 64, 152]
        assert fr.parse_map(raw).optional_leader is False

    def test_not_on_a_single_frame_layout(self):
        raw = self._raw()
        raw["frame"]["frame_layout"] = [152]
        raw["frame"]["payload_frame"] = 0
        raw["frame"]["setting_frames"] = [0]
        assert fr.parse_map(raw).optional_leader is False


class TestTheMapVersion:

    def test_declaring_it_moves_daikin152s_version(self):
        assert _map_without_the_key().version != DAIKIN.version

    def test_writing_false_is_the_same_as_leaving_it_off(self):
        raw = yaml.safe_load((MAPS_DIR / "TCL112.yaml").read_text("utf-8"))
        before = fr.parse_map(raw).version
        raw["frame"]["optional_leader"] = False
        assert fr.parse_map(raw).version == before
