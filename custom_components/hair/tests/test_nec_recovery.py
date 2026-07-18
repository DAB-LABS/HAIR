"""NEC leader-seek and checksum salvage (v0.6.1, hot-towel-finish).

The two real captures below are blalor's Previous Track button, posted
on the HA community launch thread (post #109, 2026-07-17) after the
v0.6.0 release. Capture 2 is textbook clean and decodes strictly.
Capture 1 was rejected by the strict decoder over a single data space
measuring ~815us, in the dead zone between NEC's two legal spaces,
while the frame's command checksum held. Both are the same button:
NEC address 0xC7EA, command 0x34. These fixtures pin that forever.
"""

from __future__ import annotations

import pytest

from custom_components.hair.decoders import nec_recovery
from custom_components.hair.protocol_decode import try_decode_identity

# --- fixtures: blalor's Previous Track captures (Pronto, 006D carrier) ------

BLALOR_JITTERED = (
    "0158 00AB 0017 0014 0018 003D 0017 0015 0015 0040 0015 0017 0014 003F"
    " 0017 003F 0015 003F 0016 0040 0016 003F 0016 0040 0014 0017 0014 0016"
    " 0015 0016 0015 0041 0016 003F 0015 0015 0015 0016 0015 0041 0014 0017"
    " 0014 0046 000F 0040 0015 0016 0015 0016 0015 0043 0012 0049 000C 0019"
    " 0012 0043 0013 0015 0015 001F 000C 0042 0013 0041 0014 017C"
)

BLALOR_CLEAN = (
    "0157 00AB 0016 0015 0016 003F 0016 0015 0016 003F 0016 0015 0016 003F"
    " 0016 003F 0016 003F 0016 003F 0016 003F 0016 003F 0016 0015 0016 0015"
    " 0016 0015 0016 003F 0016 003F 0016 0015 0016 0015 0016 003F 0016 0015"
    " 0016 003F 0016 003F 0016 0015 0016 0015 0016 003F 0016 003F 0016 0015"
    " 0016 003F 0016 0015 0016 0015 0016 003F 0016 003F 0016 017C"
)

BLALOR_FINGERPRINT = "NEC:0xc7ea:0x34"

# Pronto unit for frequency code 0x006D, microseconds per unit.
_PRONTO_UNIT_US = 0x6D * 0.241246


def pronto_pairs_to_timings(pairs_hex: str) -> list[int]:
    """Convert Pronto burst pairs (hex words) to signed microseconds."""
    words = [int(word, 16) for word in pairs_hex.split()]
    timings: list[int] = []
    for index, word in enumerate(words):
        value = round(word * _PRONTO_UNIT_US)
        timings.append(value if index % 2 == 0 else -value)
    return timings


def _clean_nec_timings(address: int = 0xC7EA, command: int = 0x34) -> list[int]:
    """Encode a clean NEC frame via the upstream library."""
    nec = pytest.importorskip("infrared_protocols.commands.nec")
    return nec.NECCommand(address=address, command=command).get_raw_timings()


# --- the real captures -------------------------------------------------------


def test_blalor_clean_capture_decodes_strictly() -> None:
    pytest.importorskip("infrared_protocols.commands.nec")
    identity = try_decode_identity(pronto_pairs_to_timings(BLALOR_CLEAN))
    assert identity is not None
    assert identity.protocol == "NEC"
    assert identity.fingerprint == BLALOR_FINGERPRINT


def test_blalor_jittered_capture_salvages_to_same_identity() -> None:
    """One dead-zone pulse must no longer split a button into two rows."""
    pytest.importorskip("infrared_protocols.commands.nec")
    identity = try_decode_identity(pronto_pairs_to_timings(BLALOR_JITTERED))
    assert identity is not None
    assert identity.protocol == "NEC"
    assert (identity.address, identity.command) == (0xC7EA, 0x34)
    assert identity.fingerprint == BLALOR_FINGERPRINT


def test_both_blalor_captures_unify() -> None:
    pytest.importorskip("infrared_protocols.commands.nec")
    first = try_decode_identity(pronto_pairs_to_timings(BLALOR_JITTERED))
    second = try_decode_identity(pronto_pairs_to_timings(BLALOR_CLEAN))
    assert first is not None and second is not None
    assert first.fingerprint == second.fingerprint


# --- salvage honesty: the checksum is the gate -------------------------------


def test_salvage_rejects_broken_checksum() -> None:
    """Flip one decoded bit's worth of space width: salvage must refuse."""
    timings = pronto_pairs_to_timings(BLALOR_JITTERED)
    # Data pulse pairs start at index 2 (leader mark, leader space first).
    # Pair n occupies indices (2 + 2n, 3 + 2n); flip bit 16 (first command
    # bit) from its current classification by swapping its space width.
    space_index = 3 + 2 * 16
    timings[space_index] = -1600 if timings[space_index] > -1125 else -560
    assert nec_recovery.salvage_decode(timings) is None
    assert try_decode_identity(timings) is None


def test_salvage_rejects_non_nec_shapes() -> None:
    assert nec_recovery.salvage_decode([]) is None
    assert nec_recovery.salvage_decode([9000, -4500, 560]) is None
    # Sony-shaped leader: not an NEC main leader.
    assert nec_recovery.salvage_decode([2400, -600] + [600, -600] * 40) is None


def test_salvage_does_not_fire_when_strict_succeeds() -> None:
    """A clean frame is upstream's to decode; extract path unchanged."""
    identity = try_decode_identity(_clean_nec_timings())
    assert identity is not None
    assert identity.fingerprint == BLALOR_FINGERPRINT


# --- leader-seek: repeat-prefix and junk-prefix captures ---------------------


def test_seek_passes_through_clean_capture() -> None:
    timings = _clean_nec_timings()
    assert nec_recovery.seek_main_leader(timings) == timings


def test_repeat_prefix_capture_decodes_after_seek() -> None:
    """A stray repeat marker ahead of the main frame no longer blocks it."""
    prefix = [9000, -2250, 560, -40000]  # previous press's repeat marker
    timings = prefix + _clean_nec_timings()
    identity = try_decode_identity(timings)
    assert identity is not None
    assert identity.fingerprint == BLALOR_FINGERPRINT


def test_junk_prefix_capture_decodes_after_seek() -> None:
    """Partial-burst noise ahead of the leader is skipped, not fatal."""
    prefix = [420, -380, 560, -1700, 430, -12000]
    timings = prefix + _clean_nec_timings()
    identity = try_decode_identity(timings)
    assert identity is not None
    assert identity.fingerprint == BLALOR_FINGERPRINT


def test_seek_without_any_leader_changes_nothing() -> None:
    junk = [420, -380, 560, -1700, 430, -12000]
    assert nec_recovery.seek_main_leader(junk) == junk
    assert try_decode_identity(junk) is None


def test_repeat_marker_alone_is_not_salvaged() -> None:
    """A lone repeat frame has no data payload; it must stay undecoded."""
    marker = [9000, -2250, 560, -96000]
    assert try_decode_identity(marker) is None


# --- the other protocols keep their lanes ------------------------------------


def test_sony_capture_still_decodes_as_sony() -> None:
    """The NEC seek/salvage hooks must not siphon other protocols."""
    real_sony = [
        2446, -579, 1210, -605, 1210, -605, 1236, -579, 605, -605,
        605, -605, 1210, -605, 631, -579, 1210, -605, 1210, -605,
        1236, -579, 605, -605, 1210, -605, 605, -605, 631, -579,
        1210, -10124,
    ]
    identity = try_decode_identity(real_sony)
    assert identity is not None
    assert identity.protocol == "SONY15"
