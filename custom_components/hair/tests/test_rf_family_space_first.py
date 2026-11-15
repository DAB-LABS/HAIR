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
from custom_components.hair.rf_family import (
    CERTAINTY_AMBIGUOUS,
    CERTAINTY_DECODED,
    family_of,
)
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame

ADDRESS = "10100011"
DATA = "1110"
CODE = f"{int(ADDRESS + DATA, 2):03X}"


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
        # 333 us is also CAME's unit: CAME is held off but still fits, so
        # the word is ambiguous (ruling 2026-11-14, answer 1) and carries
        # the shape's shared fields, not HT12E's address/data split
        # (ruling 2026-11-15).
        assert result.certainty == CERTAINTY_AMBIGUOUS
        assert _fields(result) == {"bits": ADDRESS + DATA, "code": CODE}
        assert result.unit_us == 333

    def test_an_open_pin_is_a_one(self):
        """Pins pull high: no address switch set, and the pressed data
        button pulls its pin low."""
        result = family_of(_sf_frame("1" * 8 + "0111", unit=1000.0))
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
        assert _fields(result)["code"] == CODE


class TestMeasuredReceivers:
    @pytest.mark.parametrize("seed", range(5))
    def test_the_rm4_pros_mark_widening(self, seed):
        frame = _sf_frame(ADDRESS + DATA, mark_widening=60, seed=seed)
        assert _fields(family_of(frame))["code"] == CODE

    @pytest.mark.parametrize("seed", range(20))
    def test_the_athoms_spread(self, seed):
        frame = _sf_frame(ADDRESS + DATA, short_spread=0.3, long_spread=0.1, seed=seed)
        assert _fields(family_of(frame))["code"] == CODE

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


# HT6P20B2/D2/F2 (Rev 1.10): the same bits as HT12E, lambda about 400 us,
# 24 address and data bits then the end code 0101, after a 23 lambda pilot.
HT6P20_DATA = "101100111000111100001101"
END_CODE = "0101"


def _ht6p20(data: str = HT6P20_DATA, end: str = END_CODE, **kw) -> list[int]:
    kw.setdefault("unit", 400.0)
    kw.setdefault("gap_units", 23.0)
    return _sf_frame(data + end, **kw)


class TestHT6P20:
    def test_a_code_word(self):
        result = family_of(_ht6p20())
        assert result.label == "HT6P20"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"code": f"{int(HT6P20_DATA, 2):06X}"}
        assert "HT6P20D2" in result.aliases
        assert "HT6P20B" not in result.aliases
        assert "HT6P20D" not in result.aliases

    @pytest.mark.parametrize("unit", [360.0, 400.0, 440.0, 250.0, 600.0])
    def test_the_datasheets_range_and_an_old_parts_resistor(self, unit):
        assert family_of(_ht6p20(unit=unit)).label == "HT6P20"

    @pytest.mark.parametrize("seed", range(10))
    def test_both_receivers(self, seed):
        assert family_of(_ht6p20(mark_widening=60, seed=seed)).label == "HT6P20"
        frame = _ht6p20(short_spread=0.3, long_spread=0.1, seed=seed)
        assert _fields(family_of(frame))["code"] == f"{int(HT6P20_DATA, 2):06X}"

    @pytest.mark.parametrize("end", ["0000", "1111", "1010", "0100"])
    def test_another_end_code_is_not_an_ht6p20(self, end):
        assert family_of(_ht6p20(end=end)) is None

    @pytest.mark.parametrize("bits", [27, 29])
    def test_one_bit_more_or_less(self, bits):
        word = (HT6P20_DATA + END_CODE)
        word = word[:bits] if bits < 28 else word + "0"
        assert family_of(_sf_frame(word, unit=400.0, gap_units=23.0)) is None

    def test_a_1_to_3_word_is_refused(self):
        assert family_of(_ht6p20(ratio=3.0)) is None

    def test_no_measured_gap(self):
        assert family_of(_ht6p20(gap_units=None)).label == "HT6P20"

    def test_it_is_not_read_by_the_1_3_shape(self):
        assert rf_family._pt2262_ev1527(tuple(_ht6p20())) is None


# CAME (held off): the HT12E shape at about 320 us, 12 or 24 bits.
CAME_24 = "101100111000111100001101"


class TestCAME:
    @pytest.fixture
    def only(self, monkeypatch):
        import dataclasses

        def show(*keys: str) -> None:
            table = {
                k: dataclasses.replace(v, shown=k in keys)
                for k, v in rf_family.FAMILIES.items()
            }
            monkeypatch.setattr(rf_family, "FAMILIES", table)
            rf_family._family_of.cache_clear()

        yield show
        rf_family._family_of.cache_clear()

    def test_it_is_off(self):
        assert rf_family.FAMILIES["came"].shown is False

    def test_a_24_bit_came_word_reads_as_nothing_while_off(self):
        assert family_of(_sf_frame(CAME_24, unit=320.0, gap_units=76.0)) is None

    def test_on_a_24_bit_word_is_came_alone(self, only):
        only("came")
        result = family_of(_sf_frame(CAME_24, unit=320.0, gap_units=76.0))
        assert result.label == "CAME"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"code": f"{int(CAME_24, 2):06X}"}

    def test_on_a_12_bit_word_is_came_or_ht12e(self, only):
        only("came", "ht12e")
        result = family_of(_sf_frame(ADDRESS + DATA, unit=320.0, gap_units=47.0))
        assert result.label == "HT12E or CAME"
        assert result.certainty == CERTAINTY_AMBIGUOUS
        assert _fields(result) == {
            "bits": ADDRESS + DATA, "code": f"{int(ADDRESS + DATA, 2):03X}",
        }

    @pytest.mark.parametrize("unit", [250.0, 320.0, 343.0, 440.0])
    def test_the_measured_units(self, only, unit):
        only("came")
        assert family_of(_sf_frame(CAME_24, unit=unit, gap_units=76.0)).label == "CAME"

    @pytest.mark.parametrize("unit", [180.0, 500.0])
    def test_outside_the_band_is_not_came(self, only, unit):
        only("came")
        assert family_of(_sf_frame(CAME_24, unit=unit, gap_units=76.0)) is None

    @pytest.mark.parametrize("seed", range(10))
    def test_both_receivers(self, only, seed):
        only("came")
        frame = _sf_frame(CAME_24, unit=320.0, mark_widening=60, seed=seed)
        assert family_of(frame).label == "CAME"
        frame = _sf_frame(CAME_24, unit=320.0, short_spread=0.3, long_spread=0.1, seed=seed)
        assert _fields(family_of(frame))["code"] == f"{int(CAME_24, 2):06X}"

    def test_an_ht12e_outside_both_brands_is_decoded(self):
        """Decoded, so HT12E's own address/data split (ruling 2026-11-15)."""
        result = family_of(_sf_frame(ADDRESS + DATA, unit=1000.0))
        assert result.label == "HT12E"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"address": ADDRESS, "data": DATA, "code": CODE}

    @pytest.mark.parametrize("seed", range(5))
    def test_a_24_bit_word_is_not_a_1_3_frame(self, seed):
        frame = tuple(_sf_frame(CAME_24, unit=320.0, seed=seed, short_spread=0.2))
        assert rf_family._pt2262_ev1527(frame) is None
        assert rf_family._mark_first_1_2(frame) is None

    def test_a_12_bit_came_code_reads_as_its_switches(self, only):
        only("came")
        result = family_of(_sf_frame(ADDRESS + DATA, unit=320.0, gap_units=47.0))
        assert _fields(result) == {
            "bits": ADDRESS + DATA, "code": f"{int(ADDRESS + DATA, 2):03X}",
        }


class TestNiceFLO:
    @pytest.fixture
    def only(self, monkeypatch):
        import dataclasses

        def show(*keys: str) -> None:
            table = {
                k: dataclasses.replace(v, shown=k in keys)
                for k, v in rf_family.FAMILIES.items()
            }
            monkeypatch.setattr(rf_family, "FAMILIES", table)
            rf_family._family_of.cache_clear()

        yield show
        rf_family._family_of.cache_clear()

    def test_it_is_off(self):
        assert rf_family.FAMILIES["nice_flo"].shown is False

    def test_a_24_bit_word_reads_as_nothing_while_off(self):
        assert family_of(_sf_frame(CAME_24, unit=700.0)) is None

    def test_on_a_24_bit_word_is_nice_flo_alone(self, only):
        only("nice_flo")
        result = family_of(_sf_frame(CAME_24, unit=700.0))
        assert result.label == "Nice FLO"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"code": f"{int(CAME_24, 2):06X}"}

    def test_on_a_12_bit_word_is_nice_flo_or_ht12e(self, only):
        only("nice_flo", "ht12e")
        result = family_of(_sf_frame(ADDRESS + DATA, unit=700.0))
        assert result.label == "HT12E or Nice FLO"
        assert result.certainty == CERTAINTY_AMBIGUOUS

    def test_a_12_bit_code_reads_as_its_switches(self, only):
        only("nice_flo")
        result = family_of(_sf_frame(ADDRESS + DATA, unit=700.0))
        assert _fields(result) == {
            "bits": ADDRESS + DATA, "code": f"{int(ADDRESS + DATA, 2):03X}",
        }

    @pytest.mark.parametrize("unit", [520.0, 700.0, 880.0])
    def test_the_band(self, only, unit):
        only("nice_flo")
        assert family_of(_sf_frame(CAME_24, unit=unit)).label == "Nice FLO"

    @pytest.mark.parametrize("unit", [460.0, 950.0])
    def test_outside_the_band_is_not_nice_flo(self, only, unit):
        only("nice_flo")
        assert family_of(_sf_frame(CAME_24, unit=unit)) is None

    def test_came_and_nice_flo_never_both_fit(self):
        """The two bands do not meet, so one word is never both brands."""
        assert rf_family._CAME_T_US[1] < rf_family._NICE_FLO_T_US[0]

    @pytest.mark.parametrize("seed", range(10))
    def test_both_receivers(self, only, seed):
        only("nice_flo")
        frame = _sf_frame(CAME_24, unit=700.0, mark_widening=60, seed=seed)
        assert family_of(frame).label == "Nice FLO"
        frame = _sf_frame(CAME_24, unit=700.0, short_spread=0.3, long_spread=0.1, seed=seed)
        assert _fields(family_of(frame))["code"] == f"{int(CAME_24, 2):06X}"
