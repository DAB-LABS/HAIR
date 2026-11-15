"""KeeLoq HCS200/300/301, detection only (second decoder round).

Frames are built from the HCS301 datasheet (DS21143B): 66 bits sent LSb
first, a one is 1 TE high then 2 TE low, a zero 2 TE high then 1 TE low;
the encrypted 32 bits, the 28-bit serial, the buttons as S3 S0 S1 S2,
VLOW and RPT; then the 39 TE guard. A whole capture adds the 23 TE
preamble and the 10 TE header, and goes through HAIR's own frame vote.
"""
from __future__ import annotations

import json
import random

import pytest

from custom_components.hair import rf_family, rf_frames
from custom_components.hair.rf_family import CERTAINTY_DECODED, family_of, family_payload
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_space_first import _sf_frame

SERIAL = 0x1A2B3C4
HOPPING = 0xDEADBEEF


def _bits(
    *,
    hopping: int = HOPPING,
    serial: int = SERIAL,
    buttons: tuple[str, ...] = ("S1",),
    vlow: int = 0,
    rpt: int = 0,
) -> list[int]:
    """The 66 bits in the order sent (HCS301 Figure 8-5)."""
    out = [(hopping >> i) & 1 for i in range(32)]
    out += [(serial >> i) & 1 for i in range(28)]
    out += [1 if name in buttons else 0 for name in ("S3", "S0", "S1", "S2")]
    out += [vlow, rpt]
    return out


def _word(
    bits: list[int],
    *,
    te: float = 400.0,
    mark_widening: float = 0.0,
    short_spread: float = 0.0,
    long_spread: float = 0.0,
    ratio: float = 2.0,
    guard_te: float | None = 39.0,
    seed: int = 0,
) -> list[int]:
    """The data part as HAIR files it: the marks and spaces of each bit,
    the last bit's low running into the guard (the gap)."""
    rng = random.Random(seed)

    def width(units: float, spread: float) -> float:
        return units * te * (1 + rng.uniform(-spread, spread))

    out: list[int] = []
    for bit in bits:
        if bit:
            mark, space = width(1, short_spread), width(ratio, long_spread)
        else:
            mark, space = width(ratio, long_spread), width(1, short_spread)
        out += [round(mark + mark_widening), -round(max(space - mark_widening, 1))]
    last_low = -out.pop()
    if guard_te is not None:
        out.append(-round(last_low + guard_te * te))
    return out


def _capture(bits: list[int], *, te: float = 400.0, words: int = 3) -> list[int]:
    """A whole press: preamble, header, data and guard, several times."""
    preamble: list[int] = []
    for _ in range(12):
        preamble += [round(te), -round(te)]
    preamble[-1] = -round(10 * te)  # the header follows the last pulse
    return (preamble + _word(bits, te=te)) * words


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestDatasheetWords:
    def test_a_code_word(self):
        result = family_of(_word(_bits()))
        assert result.label == "KeeLoq"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {
            "serial": f"{SERIAL:07X}", "buttons": "S1", "low battery": "no",
        }
        assert result.unit_us == 400
        assert set(result.aliases) == {"HCS200", "HCS300", "HCS301"}

    @pytest.mark.parametrize("buttons,shown", [
        (("S0",), "S0"), (("S0", "S2"), "S0+S2"), (("S3",), "S3"),
        (("S0", "S1", "S2", "S3"), "all (seed)"),
    ])
    def test_the_buttons(self, buttons, shown):
        assert _fields(family_of(_word(_bits(buttons=buttons))))["buttons"] == shown

    def test_low_battery(self):
        assert _fields(family_of(_word(_bits(vlow=1))))["low battery"] == "yes"

    @pytest.mark.parametrize("te", [65.0, 100.0, 200.0, 260.0, 400.0, 660.0])
    def test_every_baud_rate_and_the_oscillators_spread(self, te):
        assert _fields(family_of(_word(_bits(), te=te)))["serial"] == f"{SERIAL:07X}"

    def test_the_last_bits_lost(self):
        """Decoders accept 64 and 65 bits: a receiver often drops the
        last ones. Without bit 64 there is no low battery to say."""
        result = family_of(_word(_bits()[:64], guard_te=None))
        assert _fields(result) == {"serial": f"{SERIAL:07X}", "buttons": "S1"}
        assert "low battery" in _fields(family_of(_word(_bits()[:65])))


class TestTheEncryptedPart:
    """The ruling: the fixed part only; the 32 encrypted bits are never
    shown, logged or carried."""

    def test_no_field_carries_it(self):
        payload = family_payload(_word(_bits()))
        assert {f["name"] for f in payload["fields"]} == {
            "serial", "buttons", "low battery",
        }
        text = json.dumps(payload).upper()
        for form in (f"{HOPPING:08X}", f"{HOPPING:032b}", str(HOPPING)):
            assert form not in text

    def test_a_new_hopping_code_changes_no_field(self):
        one = family_payload(_word(_bits(hopping=HOPPING)))
        two = family_payload(_word(_bits(hopping=0x12345678)))
        assert one == two


class TestMeasuredReceivers:
    @pytest.mark.parametrize("seed", range(10))
    def test_the_rm4_pros_mark_widening(self, seed):
        frame = _word(_bits(), mark_widening=60, seed=seed)
        assert _fields(family_of(frame))["serial"] == f"{SERIAL:07X}"

    @pytest.mark.parametrize("seed", range(10))
    def test_a_receivers_spread(self, seed):
        frame = _word(_bits(), short_spread=0.3, long_spread=0.1, seed=seed)
        assert _fields(family_of(frame))["serial"] == f"{SERIAL:07X}"


class TestHairFilesTheDataPart:
    def test_a_whole_press_votes_the_data_part_and_reads_as_keeloq(self):
        capture = rf_frames.analyze(_capture(_bits()))
        assert capture is not None
        assert family_of(capture.frame).label == "KeeLoq"

    def test_the_preamble_alone_is_not_a_frame(self):
        preamble = [400, -400] * 11 + [400, -4000]
        assert family_of(preamble) is None


class TestRefusals:
    @pytest.mark.parametrize("n", [63, 67])
    def test_another_length(self, n):
        bits = (_bits() * 2)[:n]
        assert family_of(_word(bits)) is None

    def test_a_1_to_3_word(self):
        assert family_of(_word(_bits(), ratio=3.0)) is None

    def test_a_guard_far_from_39_te(self):
        assert family_of(_word(_bits(), guard_te=8.0)) is None

    def test_a_corrupt_pair(self):
        frame = _word(_bits())
        frame[41] = frame[41] * 3
        assert family_of(frame) is None


class TestEveryShapeRefusesTheOthers:
    @pytest.mark.parametrize("seed", range(5))
    def test_keeloq_is_read_by_its_shape_only(self, seed):
        frame = tuple(_word(_bits(), short_spread=0.2, seed=seed))
        assert rf_family._mark_first_1_2(frame) is not None
        assert rf_family._pt2262_ev1527(frame) is None
        assert rf_family._space_first_1_2(frame) is None

    @pytest.mark.parametrize("seed", range(5))
    def test_the_other_shapes_are_not_keeloq(self, seed):
        for frame in (
            _pt_frame(0x950E49, seed=seed, short_spread=0.2),
            _sf_frame("101000111110", seed=seed, short_spread=0.2),
            _sf_frame("1011001110001111000011010101", unit=400, gap_units=23,
                      seed=seed, short_spread=0.2),
        ):
            assert rf_family._mark_first_1_2(tuple(frame)) is None
