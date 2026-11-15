"""Dooya blind remotes, held off (second decoder round).

Frames are built from the facts the three sources agree on: a 5000 us
mark and 1500 us space header, then 40 bits MSB first, a zero 350 us
mark and 750 us space, a one 750 and 350, the last bit a mark only. No
source gives the gap between repeats; the gapped press uses 8 ms, and
the back-to-back press pins what HAIR does today.
"""
from __future__ import annotations

import dataclasses
import random

import pytest

from custom_components.hair import rf_family, rf_frames
from custom_components.hair.rf_family import CERTAINTY_DECODED, family_of, family_payload
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _word as _kl_word
from custom_components.hair.tests.test_rf_family_somfy import _frame as _somfy_frame
from custom_components.hair.tests.test_rf_family_space_first import _sf_frame

REMOTE = 0xB51C1B
CODE = 0xD133


def _bits(remote: int = REMOTE, code: int = CODE) -> str:
    return f"{remote:024b}{code:016b}"


def _word(
    bits: str | None = None,
    *,
    short: float = 350.0,
    long: float = 750.0,
    header: tuple[float, float] = (5000.0, 1500.0),
    mark_widening: float = 0.0,
    spread: float = 0.0,
    seed: int = 0,
    gap: int | None = 8000,
) -> list[int]:
    """One word as HAIR files it: the header pair, the bits, the gap."""
    rng = random.Random(seed)

    def width(us: float) -> float:
        return us * (1 + rng.uniform(-spread, spread))

    out = [round(width(header[0]) + mark_widening),
           -round(width(header[1]) - mark_widening)]
    for bit in bits if bits is not None else _bits():
        mark, space = (long, short) if bit == "1" else (short, long)
        out += [round(width(mark) + mark_widening),
                -round(max(width(space) - mark_widening, 1))]
    out.pop()
    if gap is not None:
        out.append(-gap)
    return out


@pytest.fixture
def shown(monkeypatch):
    spec = dataclasses.replace(rf_family.FAMILIES["dooya"], shown=True)
    monkeypatch.setitem(rf_family.FAMILIES, "dooya", spec)
    rf_family._family_of.cache_clear()
    yield
    rf_family._family_of.cache_clear()


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestHeldOff:
    def test_it_is_off(self):
        assert rf_family.FAMILIES["dooya"].shown is False

    def test_a_word_reads_as_nothing_while_off(self):
        rf_family._family_of.cache_clear()
        assert family_of(_word()) is None

    def test_it_is_read_with_the_hidden_families(self):
        result = family_of(_word(), include_hidden=True)
        assert result.label == "Dooya"
        assert result.certainty == CERTAINTY_DECODED


class TestSourceWords:
    def test_a_word(self, shown):
        result = family_of(_word())
        assert result.label == "Dooya"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"remote": "B51C1B", "code": "D133"}
        assert result.unit_us == 367
        assert result.aliases == ()

    def test_no_channel_or_button_split(self, shown):
        """Two sources place the 8-bit field differently (ruling)."""
        payload = family_payload(_word())
        assert [f["name"] for f in payload["fields"]] == ["remote", "code"]

    @pytest.mark.parametrize("remote,code", [
        (0x000001, 0xFFFE), (0x800000, 0x0001), (0x123456, 0x1E3C),
    ])
    def test_msb_first(self, shown, remote, code):
        assert _fields(family_of(_word(_bits(remote, code)))) == {
            "remote": f"{remote:06X}", "code": f"{code:04X}",
        }

    @pytest.mark.parametrize("short,long,header", [
        (350.0, 720.0, (4800.0, 1500.0)),   # Flipper forum
        (385.0, 670.0, (4812.0, 1479.0)),   # MySensors, a zero
        (325.0, 730.0, (4812.0, 1479.0)),   # MySensors, a one
    ])
    def test_the_measured_timings(self, shown, short, long, header):
        frame = _word(short=short, long=long, header=header)
        assert _fields(family_of(frame))["remote"] == "B51C1B"

    def test_one_level_of_marks_is_unreadable(self, shown):
        """All ones or all zeros: no second mark width to tell them by."""
        assert family_of(_word("0" * 40)) is None


class TestMeasuredReceivers:
    @pytest.mark.parametrize("seed", range(10))
    def test_the_rm4_pros_mark_widening(self, shown, seed):
        assert _fields(family_of(_word(mark_widening=60, seed=seed)))["remote"] == "B51C1B"

    @pytest.mark.parametrize("seed", range(10))
    def test_a_receivers_spread(self, shown, seed):
        assert _fields(family_of(_word(spread=0.15, seed=seed)))["remote"] == "B51C1B"


class TestHairFilesThePress:
    def test_a_gapped_press_votes_a_word_that_reads_as_dooya(self, shown):
        capture = rf_frames.analyze(_word() * 6)
        assert capture is not None
        assert family_of(capture.frame).label == "Dooya"

    def test_a_back_to_back_press_gives_no_frame_today(self, shown):
        """Words sent with no long space between them are one piece to
        HAIR. A cut before a long header mark waits for a real capture
        (ruling 2026-11-14); when it lands, this test changes."""
        words = []
        for _ in range(6):
            words += [*_word(gap=None), -750]
        words[-1] = -50000
        assert rf_frames.analyze(words) is None


class TestRefusals:
    @pytest.mark.parametrize("n", [39, 41])
    def test_another_length(self, shown, n):
        assert family_of(_word((_bits() * 2)[:n])) is None

    @pytest.mark.parametrize("header", [
        (2500.0, 1500.0), (8000.0, 1500.0), (5000.0, 700.0), (5000.0, 2500.0),
    ])
    def test_another_header(self, shown, header):
        assert family_of(_word(header=header)) is None

    def test_a_1_to_3_word(self, shown):
        assert family_of(_word(short=275.0, long=825.0)) is None

    def test_a_1_to_1_5_word(self, shown):
        assert family_of(_word(short=440.0, long=660.0)) is None

    def test_a_corrupt_pair(self, shown):
        frame = _word()
        frame[21] = frame[21] * 3
        assert family_of(frame) is None


class TestEveryShapeRefusesTheOthers:
    @pytest.mark.parametrize("seed", range(5))
    def test_dooya_is_read_by_its_shape_only(self, seed):
        frame = tuple(_word(spread=0.1, seed=seed))
        assert rf_family._header_mark_first_1_2(frame) is not None
        assert rf_family._pt2262_ev1527(frame) is None
        assert rf_family._space_first_1_2(frame) is None
        assert rf_family._mark_first_1_2(frame) is None
        assert rf_family._manchester_somfy(frame) is None

    @pytest.mark.parametrize("seed", range(5))
    def test_the_other_shapes_are_not_dooya(self, seed):
        for frame in (
            _pt_frame(0x950E49, seed=seed, short_spread=0.2),
            _sf_frame("101000111110", seed=seed, short_spread=0.2),
            _sf_frame("1011001110001111000011010101", unit=400, gap_units=23,
                      seed=seed, short_spread=0.2),
            _kl_word(_kl_bits(), seed=seed, short_spread=0.2),
            _somfy_frame(spread=0.1, seed=seed),
        ):
            assert rf_family._header_mark_first_1_2(tuple(frame)) is None
