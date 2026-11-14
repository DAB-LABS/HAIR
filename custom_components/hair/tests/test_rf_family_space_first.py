"""The space-first 1:2 shape: HT12E (second decoder round).

Frames are built from the HT12E datasheet (Rev. 1.20): a 1 T sync mark,
then 12 bits of a space and a mark, one = 2 T low and 1 T high, zero =
1 T low and 2 T high, then the next word's 36 T pilot as the gap. Then
they are distorted the way our receivers distort real frames.
"""
from __future__ import annotations

import random

import pytest

from custom_components.hair import rf_family
from custom_components.hair.rf_family import CERTAINTY_DECODED, family_of
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame

ADDRESS = "10100011"
DATA = "1110"


def _sf_frame(
    bits: str,
    *,
    unit: float = 333.0,
    mark_widening: float = 0.0,
    short_spread: float = 0.0,
    long_spread: float = 0.0,
    ratio: float = 2.0,
    start: bool = True,
    start_units: float = 1.0,
    gap_units: float | None = 36.0,
    seed: int = 0,
) -> list[int]:
    """A space-first frame as a row stores it: the start mark, then for
    each bit a space and a mark, then the gap when measured."""
    rng = random.Random(seed)

    def width(units: float, spread: float) -> float:
        return units * unit * (1 + rng.uniform(-spread, spread))

    out: list[int] = []
    if start:
        out.append(round(width(start_units, short_spread) + mark_widening))
    for bit in bits:
        if bit == "1":
            space = width(ratio, long_spread) - mark_widening
            mark = width(1, short_spread) + mark_widening
        else:
            space = width(1, short_spread) - mark_widening
            mark = width(ratio, long_spread) + mark_widening
        out += [-round(max(space, 1)), round(mark)]
    if gap_units is not None:
        out.append(-round(gap_units * unit))
    return out


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestDatasheetFrames:
    def test_an_ht12e_word(self):
        result = family_of(_sf_frame(ADDRESS + DATA))
        assert result.label == "HT12E"
        assert result.family == "ht12e"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {
            "address": ADDRESS, "data": DATA, "code": f"{int(ADDRESS + DATA, 2):03X}",
        }
        assert result.unit_us == 333

    def test_an_open_pin_is_a_one(self):
        """Pins pull high: no address switch set, and the pressed data
        button pulls its pin low."""
        result = family_of(_sf_frame("1" * 8 + "0111"))
        assert _fields(result)["address"] == "11111111"
        assert _fields(result)["data"] == "0111"

    def test_a_word_with_one_mark_width_reads_as_nothing(self):
        """All ones (no button pressed, so never sent) has no second mark
        width to tell a one from a zero, as all-0 on the 1:3 shape."""
        assert family_of(_sf_frame("1" * 12)) is None

    @pytest.mark.parametrize("unit", [150.0, 250.0, 333.0, 500.0, 700.0, 1000.0])
    def test_any_oscillator(self, unit):
        assert family_of(_sf_frame(ADDRESS + DATA, unit=unit)).label == "HT12E"

    def test_no_measured_gap(self):
        result = family_of(_sf_frame(ADDRESS + DATA, gap_units=None))
        assert _fields(result)["address"] == ADDRESS


class TestMeasuredReceivers:
    @pytest.mark.parametrize("seed", range(5))
    def test_the_rm4_pros_mark_widening(self, seed):
        frame = _sf_frame(ADDRESS + DATA, mark_widening=60, seed=seed)
        assert _fields(family_of(frame))["data"] == DATA

    @pytest.mark.parametrize("seed", range(20))
    def test_the_athoms_spread(self, seed):
        frame = _sf_frame(ADDRESS + DATA, short_spread=0.3, long_spread=0.1, seed=seed)
        assert _fields(family_of(frame))["address"] == ADDRESS

    def test_widening_at_a_fast_oscillator(self):
        frame = _sf_frame(ADDRESS + DATA, unit=150, mark_widening=60)
        assert family_of(frame).label == "HT12E"


class TestRefusals:
    def test_a_1_to_3_frame(self):
        assert family_of(_sf_frame(ADDRESS + DATA, ratio=3.0)) is None

    def test_a_1_to_1_5_frame(self):
        assert family_of(_sf_frame(ADDRESS + DATA, ratio=1.5)) is None

    @pytest.mark.parametrize("bits", [11, 13])
    def test_another_length(self, bits):
        assert family_of(_sf_frame((ADDRESS + DATA + "0")[:bits].ljust(bits, "1"))) is None

    def test_no_start_mark(self):
        assert family_of(_sf_frame(ADDRESS + DATA, start=False)) is None

    def test_a_long_start_mark(self):
        assert family_of(_sf_frame(ADDRESS + DATA, start_units=2.0)) is None

    def test_a_gap_far_from_a_pilot(self):
        assert family_of(_sf_frame(ADDRESS + DATA, gap_units=6.0)) is None

    def test_a_corrupt_pair(self):
        frame = _sf_frame(ADDRESS + DATA)
        frame[5] = frame[5] * 3
        assert family_of(frame) is None

    def test_all_one_width(self):
        """A frame whose marks are all one width has no data at all."""
        assert family_of(_sf_frame("1" * 12, ratio=1.0)) is None


class TestEveryShapeRefusesTheOthers:
    """Each fixture is read by its own shape and by no other."""

    @pytest.mark.parametrize("seed", range(5))
    def test_a_1_3_frame_is_not_space_first(self, seed):
        frame = tuple(_pt_frame(0x950E49, seed=seed, short_spread=0.2))
        assert rf_family._space_first_1_2(frame) is None
        assert rf_family._pt2262_ev1527(frame) is not None

    @pytest.mark.parametrize("seed", range(5))
    def test_a_space_first_frame_is_not_1_3(self, seed):
        frame = tuple(_sf_frame(ADDRESS + DATA, seed=seed, short_spread=0.2))
        assert rf_family._pt2262_ev1527(frame) is None
        assert rf_family._space_first_1_2(frame) is not None
