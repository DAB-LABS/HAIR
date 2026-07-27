"""Tests for the shared wig-signal identity helper.

The contract under test: identity derived from a wig's Pronto is
byte-identical to what the capture pipeline computes for the same
signal, because both route through ``signal_monitor.normalize()``.
"""
from __future__ import annotations

import pytest

from custom_components.hair.event_parser import EventParser
from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.wig_identity import wig_signal_identity

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"

# A real NEC frame (address 0x04, command 0x08) as Pronto, so the
# decoded tier exercises when infrared_protocols is installed.
NEC_PRONTO = (
    "0000 006D 0022 0000 0157 00AC 0016 0016 0016 0016 0016 0041 0016 "
    "0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0041 0016 0041 "
    "0016 0016 0016 0041 0016 0041 0016 0041 0016 0041 0016 0041 0016 "
    "0016 0016 0016 0016 0016 0016 0041 0016 0016 0016 0016 0016 0016 "
    "0016 0016 0016 0041 0016 0041 0016 0041 0016 0016 0016 0041 0016 "
    "0041 0016 0041 0016 0041 0016 0640"
)


class TestWigSignalIdentity:
    def test_matches_event_parser_fingerprints(self):
        ident = wig_signal_identity(PRONTO)
        assert ident is not None
        normalized = validate_pronto(PRONTO).normalized
        assert ident.pronto == normalized
        assert ident.fingerprint == EventParser.signal_fingerprint(
            "PRONTO", normalized, None
        )
        assert ident.byte_hash == EventParser.pronto_byte_hash(normalized)
        assert ident.raw_timings
        assert ident.frequency > 0

    def test_invalid_pronto_returns_none(self):
        assert wig_signal_identity("not pronto at all") is None
        assert wig_signal_identity("") is None
        # Header only, no timing words.
        assert wig_signal_identity("0000 006D 0000 0000") is None

    def test_nec_frame_decodes(self):
        pytest.importorskip("infrared_protocols")
        ident = wig_signal_identity(NEC_PRONTO)
        assert ident is not None
        assert ident.decoded_protocol == "NEC"
        assert ident.decoded_fingerprint is not None

    def test_identity_stable_across_formatting(self):
        """Whitespace / case variants of the same code agree."""
        messy = PRONTO.lower().replace("  ", " ")
        a = wig_signal_identity(PRONTO)
        b = wig_signal_identity(messy)
        assert a is not None and b is not None
        assert a.fingerprint == b.fingerprint
        assert a.byte_hash == b.byte_hash
