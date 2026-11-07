"""The band a radio carrier reads as: one rule for the panel and the wig.

Ruling 2026-11-06 (fix round 1, item 8, on rf-send-doors-addendum-c): a
carrier within ``RF_BAND_SNAP_HZ`` of a preset band centre reads as that
centre; any other carrier is rounded to the nearest ``RF_BAND_STEP_HZ``,
half up. The panel's band label, a row record's ``band`` and a radio
wig row's identity (``hair-wig/5``) all come from ``band_hz``, so the
label and the identity never disagree. ``frontend/src/rf-band.ts`` is
the same rule for the panel and is pinned to the same cases
(``tests/fixtures/rf/band_cases.json``). WigShop must reproduce it
exactly, so it is written down in ``docs/wig-format.md``.
"""
from __future__ import annotations

# The bands real radio remotes cluster on (rf-in-hair-plan 5.1, the
# editor's preset list), in Hz. Part of the wig digest contract.
RF_BAND_CENTRES_HZ = (
    303_875_000, 310_000_000, 315_000_000, 318_000_000, 350_000_000,
    390_000_000, 418_000_000, 433_420_000, 433_920_000, 868_350_000,
    915_000_000,
)
# How far from a centre a carrier still reads as that band. Wide enough
# for one handset's spread across receivers (an RM4 Pro reports 433.92
# and 433.84 MHz for the same keyfob), narrow enough to keep Somfy's
# 433.42 apart from 433.92.
RF_BAND_SNAP_HZ = 150_000
# A carrier near no centre is rounded to this step.
RF_BAND_STEP_HZ = 100_000


def band_hz(frequency_hz: int) -> int:
    """The band a carrier reads as, in Hz.

    The nearest preset centre when within ``RF_BAND_SNAP_HZ`` of it (the
    lower centre on a tie), else the carrier rounded half up to
    ``RF_BAND_STEP_HZ``. Integer arithmetic only, so every reader gets
    the same answer.
    """
    hz = int(frequency_hz)
    best = None
    for centre in RF_BAND_CENTRES_HZ:
        if abs(centre - hz) <= RF_BAND_SNAP_HZ and (
            best is None or abs(centre - hz) < abs(best - hz)
        ):
            best = centre
    if best is not None:
        return best
    return (hz + RF_BAND_STEP_HZ // 2) // RF_BAND_STEP_HZ * RF_BAND_STEP_HZ


def band_key(frequency_hz: int) -> str:
    """The band as the wig row identity writes it: MHz, one decimal.

    ``band_hz`` rounded half up to 100 kHz: 433.92 and 433.84 MHz are
    both ``"433.9"``, 433.42 MHz is ``"433.4"``, 315 MHz is ``"315.0"``.
    """
    tenths = (band_hz(frequency_hz) + 50_000) // 100_000
    return f"{tenths // 10}.{tenths % 10}"


def band_label(frequency_hz: int) -> str:
    """The band as the panel shows it: ``band_hz`` in MHz, no trailing
    zeros ("433.92", "315", "303.875", "433.6")."""
    hz = band_hz(frequency_hz)
    whole, frac = divmod(hz, 1_000_000)
    digits = f"{frac:06d}".rstrip("0")
    return f"{whole}.{digits}" if digits else str(whole)
