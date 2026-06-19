"""IR carrier-frequency standards and helpers for snap-to-standard.

The six consumer-IR carrier standards plus a small tolerance band. Used by
the snap-preview endpoint (re-encode an off-standard signal to the nearest
standard) and mirrored in the frontend editor for the off-standard notice.
"""

from __future__ import annotations

# The consumer IR carrier standards, in Hz. Six bins cover essentially every
# consumer remote ever built. Nearest-wins is used rather than fixed windows
# because the gap between 36 and 38 kHz is only 2 kHz.
IR_CARRIER_STANDARDS_HZ: tuple[int, ...] = (
    30_000,
    33_000,
    36_000,
    38_000,
    40_000,
    56_000,
)

# A carrier within this many Hz of a standard reads as on-standard. Tight
# enough that real drift surfaces, loose enough that Pronto round-trip
# rounding does not false-flag a 38 kHz signal as off-standard.
ON_STANDARD_TOLERANCE_HZ = 500


def nearest_standard(frequency_hz: int) -> int:
    """Return the closest standard carrier in Hz.

    On a tie (equidistant from two standards) the lower standard wins, since
    ``min`` returns the first minimum in declaration order.
    """
    return min(IR_CARRIER_STANDARDS_HZ, key=lambda s: abs(s - frequency_hz))


def is_on_standard(frequency_hz: int) -> bool:
    """True when the carrier is within tolerance of a standard."""
    return (
        abs(frequency_hz - nearest_standard(frequency_hz))
        <= ON_STANDARD_TOLERANCE_HZ
    )
