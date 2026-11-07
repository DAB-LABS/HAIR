"""Fix round 1, item 8 (ruling 2026-11-06 on rf-send-doors-addendum-c):
one band rule for the panel, a row record's ``band`` and a radio wig
row's identity.

A carrier within 150 kHz of a preset centre reads as that centre; any
other is rounded half up to 100 kHz. ``frontend/src/rf-band.ts`` is the
same rule, pinned to the same cases in ``test_rf_frontend_js``.
"""
from __future__ import annotations

import json
import re
from itertools import pairwise
from pathlib import Path

import pytest

from custom_components.hair import rf_band
from custom_components.hair.models import band_mhz

HERE = Path(__file__).parent
CASES = json.loads((HERE / "fixtures" / "rf" / "band_cases.json").read_text(encoding="utf-8"))
TS = (HERE.parent / "frontend" / "src" / "rf-band.ts").read_text(encoding="utf-8")


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: str(c["hz"]))
def test_every_case(case):
    hz = case["hz"]
    assert rf_band.band_hz(hz) == case["band_hz"]
    assert rf_band.band_key(hz) == case["key"]
    assert rf_band.band_label(hz) == case["label"]


def test_one_keyfob_is_one_band():
    """The bench: an RM4 Pro reports 433.92 and 433.84 MHz for one fob."""
    assert rf_band.band_label(433_840_000) == rf_band.band_label(433_920_000) == "433.92"
    assert rf_band.band_key(433_840_000) == rf_band.band_key(433_920_000) == "433.9"
    assert rf_band.band_label(433_420_000) == "433.42"


def test_off_preset_carriers_round_half_up():
    assert rf_band.band_hz(400_050_000) == 400_100_000
    assert rf_band.band_hz(400_049_999) == 400_000_000
    assert rf_band.band_label(433_580_000) == "433.6"


def test_the_record_band_is_the_identity_band():
    for case in CASES["cases"]:
        assert band_mhz(case["hz"]) == case["key"]
    assert band_mhz(None) is None and band_mhz(0) is None


def _ts_number(name):
    return int(re.search(rf"{name} = ([\d_]+);", TS).group(1).replace("_", ""))


def test_the_frontend_uses_the_same_numbers():
    centres = re.search(r"RF_BAND_CENTRES_HZ: readonly number\[\] = \[(.*?)\];", TS, re.S)
    ts_centres = tuple(int(x.replace("_", "")) for x in re.findall(r"[\d_]{6,}", centres.group(1)))
    assert ts_centres == rf_band.RF_BAND_CENTRES_HZ
    assert _ts_number("RF_BAND_SNAP_HZ") == rf_band.RF_BAND_SNAP_HZ
    assert _ts_number("RF_BAND_STEP_HZ") == rf_band.RF_BAND_STEP_HZ


def test_the_presets_never_overlap():
    """Snap windows are disjoint, so no carrier is near two centres."""
    centres = rf_band.RF_BAND_CENTRES_HZ
    gaps = [b - a for a, b in pairwise(centres)]
    assert min(gaps) > 2 * rf_band.RF_BAND_SNAP_HZ
