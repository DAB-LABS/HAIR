"""Tests for ``protocol_decode.try_decode`` against real NEC captures.

The decoder needs the ``infrared-protocols`` library, which the runtime
consumes via HA core and the test suite pulls in through the ``test``
extra. The whole module skips cleanly when the library is absent so a
bare ``pytest`` run does not fail collection.

Fixtures are the 13 real Remote-4 NEC captures plus the reconstructed
frafall (GH #14) case, copied from
``docs/internal/research/09-nec-test-fixtures.json`` into the committed
test tree (the docs path is gitignored, so it is unavailable in CI).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("infrared_protocols")

from custom_components.hair import protocol_decode
from custom_components.hair.const import DECODED_PROTOCOL_NEC

_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "nec_test_fixtures.json").read_text()
)
_REAL_CAPTURES = _FIXTURES["nec_real_captures"]
_FRAFALL = _FIXTURES["frafall_reconstructed"]


def test_library_available():
    """With the test extra installed, the decoder reports itself usable."""
    assert protocol_decode.library_available() is True


@pytest.mark.parametrize(
    "capture",
    _REAL_CAPTURES,
    ids=[f"cmd_{c['decoded_command']:#04x}" for c in _REAL_CAPTURES],
)
def test_real_nec_captures_decode(capture):
    """Every real Remote-4 capture decodes to its recorded tuple."""
    result = protocol_decode.try_decode(capture["raw_timings_captured"])
    assert result is not None
    protocol, address, command = result
    assert protocol == DECODED_PROTOCOL_NEC == capture["decoded_protocol"]
    assert address == capture["decoded_address"]
    assert command == capture["decoded_command"]


def test_frafall_tsop_distorted_decodes():
    """The reconstructed frafall capture decodes through TSOP distortion."""
    result = protocol_decode.try_decode(_FRAFALL["captured_raw_timings"])
    assert result == (
        _FRAFALL["expected_decoded_protocol"],
        _FRAFALL["expected_decoded_address"],
        _FRAFALL["expected_decoded_command"],
    )


def test_command_is_data_byte_not_wire_packed():
    """Decoded command is the 8-bit data byte, not ``(cmd << 8) | ~cmd``.

    frafall's ESPHome ``transmit_nec`` reported command 0x6B94; the
    library returns the data byte 0x94 (0x94 ^ 0x6B == 0xFF). Storing the
    data byte is what lets the TX path rebuild the same wire bytes.
    """
    decoded = protocol_decode.try_decode(_FRAFALL["captured_raw_timings"])
    assert decoded is not None
    _, _, command = decoded
    assert command == 0x94
    assert command <= 0xFF


def test_non_nec_timings_return_none():
    """Sony-like leader timings are rejected, not guessed."""
    sony_like = [2400, -600, 1200, -600, 600, -600, 1200, -600]
    assert protocol_decode.try_decode(sony_like) is None


def test_empty_and_none_return_none():
    assert protocol_decode.try_decode(None) is None
    assert protocol_decode.try_decode([]) is None


def test_truncated_nec_returns_none():
    """A too-short NEC buffer short-circuits to None without raising."""
    full = _REAL_CAPTURES[0]["raw_timings_captured"]
    assert protocol_decode.try_decode(full[:20]) is None
