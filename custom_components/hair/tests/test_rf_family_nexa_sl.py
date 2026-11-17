"""Nexa self-learning, held off (second decoder round).

Frames are built from the two descriptions' shared facts: T about 260
to 275 us; a wire bit is 1 T high then 1 T or 5 T low; a logical 0 is
wire short then long, a 1 long then short; the start is T high and 10 T
low, the stop T high and about 40 T low; 26-bit id, group, on/off, a
4-bit unit; the dim variant puts two short wire bits in the on/off slot
and adds 4 dim bits. Every mark is one width; HAIR's receive path hears
such a frame as a pulse-distance body (rf_frames).
"""
from __future__ import annotations

import dataclasses
import random

import pytest

from custom_components.hair import rf_family, rf_frames
from custom_components.hair.rf_family import CERTAINTY_DECODED, family_of, family_payload
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_dooya import _word as _dooya_word
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _word as _kl_word
from custom_components.hair.tests.test_rf_family_somfy import _frame as _somfy_frame
from custom_components.hair.tests.test_rf_family_space_first import _sf_frame

ID = 0x0E1C502  # RFLink-ESP's example address


def _logical(
    *, ident: int = ID, group: int = 0, off: int = 0, unit: int = 3,
    dim: int | None = None,
) -> list[int | None]:
    bits: list[int | None] = [(ident >> (25 - i)) & 1 for i in range(26)]
    bits += [group, None if dim is not None else off]
    bits += [(unit >> (3 - i)) & 1 for i in range(4)]
    if dim is not None:
        bits += [(dim >> (3 - i)) & 1 for i in range(4)]
    return bits


def _frame(
    bits: list[int | None] | None = None,
    *,
    t: float = 260.0,
    long_t: float = 5.0,
    start_t: float = 10.0,
    mark: float | None = None,
    short_space: float | None = None,
    long_space: float | None = None,
    spread: float = 0.0,
    seed: int = 0,
    gap: int | None = None,
) -> list[int]:
    """One word as HAIR would file it: start pair, wire bits, stop mark,
    the stop's low as the gap."""
    rng = random.Random(seed)
    mark = t if mark is None else mark
    short_space = t if short_space is None else short_space
    long_space = long_t * t if long_space is None else long_space

    def width(us: float) -> int:
        return round(us * (1 + rng.uniform(-spread, spread)))

    wire: list[int] = []
    for bit in bits if bits is not None else _logical():
        wire += [0, 0] if bit is None else ([1, 0] if bit else [0, 1])
    out = [width(mark), -width(start_t * t)]
    for w in wire:
        out += [width(mark), -width(long_space if w else short_space)]
    out.append(width(mark))
    out.append(-(gap if gap is not None else round(40 * t)))
    return out


@pytest.fixture
def shown(monkeypatch):
    spec = dataclasses.replace(rf_family.FAMILIES["nexa_sl"], shown=True)
    monkeypatch.setitem(rf_family.FAMILIES, "nexa_sl", spec)
    rf_family._family_of.cache_clear()
    yield
    rf_family._family_of.cache_clear()


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestHeldOff:
    def test_it_is_off(self):
        assert rf_family.FAMILIES["nexa_sl"].shown is False

    def test_a_word_reads_as_nothing_while_off(self):
        rf_family._family_of.cache_clear()
        assert family_of(_frame()) is None

    def test_it_is_read_with_the_hidden_families(self):
        result = family_of(_frame(), include_hidden=True)
        assert result.label == "Nexa"
        assert result.certainty == CERTAINTY_DECODED


class TestDescribedWords:
    def test_a_word(self, shown):
        result = family_of(_frame())
        assert result.label == "Nexa"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {
            "id": "0E1C502", "group": "0", "state": "on", "unit": "3",
        }
        assert result.unit_us == 260
        assert result.aliases == ("Proove", "KlikAanKlikUit", "COCO")

    def test_the_state_follows_elektronikforumet(self, shown):
        """0 is on there (RFLink says on is 1); recorded until a capture."""
        assert _fields(family_of(_frame(_logical(off=1))))["state"] == "off"

    def test_the_group_bit(self, shown):
        assert _fields(family_of(_frame(_logical(group=1))))["group"] == "1"

    @pytest.mark.parametrize("unit", [0, 1, 2, 10, 11, 15])
    def test_the_unit_as_its_4_bit_number(self, shown, unit):
        assert _fields(family_of(_frame(_logical(unit=unit))))["unit"] == str(unit)

    @pytest.mark.parametrize("ident", [0x0000001, 0x2000000, 0x3FFFFFF, 0x1555555])
    def test_the_id_msb_first(self, shown, ident):
        assert _fields(family_of(_frame(_logical(ident=ident))))["id"] == f"{ident:07X}"

    @pytest.mark.parametrize("level", [0, 7, 15])
    def test_a_dim_word(self, shown, level):
        fields = _fields(family_of(_frame(_logical(dim=level, unit=5))))
        assert fields == {
            "id": "0E1C502", "group": "0", "state": "dim", "unit": "5",
            "dim": str(level),
        }

    def test_no_dim_field_without_the_dim_symbol(self, shown):
        payload = family_payload(_frame())
        assert [f["name"] for f in payload["fields"]] == ["id", "group", "state", "unit"]

    @pytest.mark.parametrize("t,long_t,start_t", [
        (250.0, 5.0, 10.0), (262.0, 5.0, 11.2), (275.0, 5.0, 9.0),
        (375.0, 5.0, 10.0), (275.0, 3.4, 10.0),
    ])
    def test_the_described_timings(self, shown, t, long_t, start_t):
        frame = _frame(t=t, long_t=long_t, start_t=start_t)
        assert _fields(family_of(frame))["id"] == "0E1C502"


class TestMeasuredReceivers:
    def test_a_stretched_receiver(self, shown):
        """A cheap receiver's reading: 319 mark, 140 and 1000 spaces."""
        frame = _frame(t=250.0, mark=319, short_space=140, long_space=1000)
        assert _fields(family_of(frame))["id"] == "0E1C502"

    @pytest.mark.parametrize("seed", range(10))
    def test_a_receivers_spread(self, shown, seed):
        assert _fields(family_of(_frame(spread=0.15, seed=seed)))["id"] == "0E1C502"


class TestHairHearsIt:
    def test_a_whole_press_votes_a_frame_the_decoder_reads(self, shown):
        """One mark width, heard as a pulse-distance body: a whole press
        votes, and the voted frame is read as self-learning Nexa."""
        capture = rf_frames.analyze(_frame() * 4)
        assert capture is not None
        assert _fields(family_of(capture.frame))["id"] == "0E1C502"

    def test_held_off_it_shows_no_label(self):
        rf_family._family_of.cache_clear()
        capture = rf_frames.analyze(_frame() * 4)
        assert capture is not None
        assert family_of(capture.frame) is None


class TestItsDiamonds:
    """The diamonds of a one-mark-width code (radio diamonds, item 5): every
    mark reads S, and only the spaces carry the code. The 10 T start space
    sits inside the body and reads L."""

    def test_marks_are_all_short_and_the_spaces_carry_the_code(self):
        word = _frame()
        read = rf_frames.identity_of_frame(word)
        assert read is not None
        parts = rf_frames.split_body(max(rf_frames.split_frames(word), key=lambda p: len(p.edges)))
        assert parts.body_starts_on_mark
        marks, spaces = read.sl_pattern[0::2], read.sl_pattern[1::2]
        assert set(marks) == {"S"}
        wire = []
        for bit in _logical():
            wire += [0, 0] if bit is None else ([1, 0] if bit else [0, 1])
        assert spaces == "L" + "".join("L" if w else "S" for w in wire)

    def test_a_voted_press_draws_the_same_diamonds(self):
        """What the Sniffer row draws (the vote) and what a stored row
        draws (``identity_of_frame``) agree."""
        capture = rf_frames.analyze(_frame() * 4)
        assert capture is not None
        assert capture.sl_pattern == rf_frames.identity_of_frame(capture.frame).sl_pattern


class TestRefusals:
    @pytest.mark.parametrize("n", [31, 33])
    def test_another_length(self, shown, n):
        bits = (_logical() * 2)[:n]
        bits = [0 if b is None else b for b in bits]
        assert family_of(_frame(bits)) is None

    def test_a_long_long_pair(self, shown):
        frame = _frame()
        # wire bits 0 and 1 are logical bit 0; make both long.
        frame[3] = frame[5] = -1300
        assert family_of(frame) is None

    def test_the_dim_symbol_elsewhere(self, shown):
        bits = _logical()
        bits[10] = None
        assert family_of(_frame(bits)) is None

    def test_32_bits_with_four_more_but_no_dim_symbol(self, shown):
        bits = [*_logical(), 1, 0, 1, 0]
        assert family_of(_frame(bits)) is None

    def test_two_mark_widths(self, shown):
        frame = _frame()
        for index in range(2, len(frame) - 2, 8):
            frame[index] = 700
        assert family_of(frame) is None

    @pytest.mark.parametrize("start_t", [5.0, 16.0])
    def test_another_start(self, shown, start_t):
        assert family_of(_frame(start_t=start_t)) is None

    @pytest.mark.parametrize("long_t", [1.8, 7.0])
    def test_another_long_space(self, shown, long_t):
        assert family_of(_frame(long_t=long_t)) is None


class TestEveryShapeRefusesTheOthers:
    @pytest.mark.parametrize("seed", range(5))
    def test_nexa_is_read_by_its_shape_only(self, seed):
        frame = tuple(_frame(spread=0.1, seed=seed))
        assert rf_family._distance_1_5(frame) is not None
        for other in (
            rf_family._pt2262_ev1527, rf_family._space_first_1_2,
            rf_family._mark_first_1_2, rf_family._manchester_somfy,
            rf_family._header_mark_first_1_2,
        ):
            assert other(frame) is None

    @pytest.mark.parametrize("seed", range(5))
    def test_the_other_shapes_are_not_nexa(self, seed):
        for frame in (
            _pt_frame(0x950E49, seed=seed, short_spread=0.2),
            _sf_frame("101000111110", seed=seed, short_spread=0.2),
            _kl_word(_kl_bits(), seed=seed, short_spread=0.2),
            _somfy_frame(spread=0.1, seed=seed),
            _dooya_word(spread=0.1, seed=seed),
        ):
            assert rf_family._distance_1_5(tuple(frame)) is None
