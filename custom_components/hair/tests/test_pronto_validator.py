"""Tests for the manual Pronto validator (HAIR Clips)."""
from __future__ import annotations

from custom_components.hair.pronto_validator import validate_pronto

# A minimal, structurally valid learned Pronto code:
# header 0000, freq 006D (~38 kHz), burst1=2, burst2=0, then 4 timing words.
VALID = "0000 006D 0002 0000 0010 0010 0010 0010"


def test_valid_code_passes():
    r = validate_pronto(VALID)
    assert r.valid is True
    assert r.errors == []
    assert r.burst_pair_count == 2
    assert r.normalized == VALID


def test_valid_code_reports_frequency_near_38khz():
    r = validate_pronto(VALID)
    assert r.frequency_khz is not None
    assert 37.0 <= r.frequency_khz <= 39.0
    assert r.warnings == []


def test_normalizes_surrounding_quotes_and_whitespace():
    r = validate_pronto('  "0000 006D 0002 0000 0010 0010 0010 0010"  \n')
    assert r.valid is True
    assert r.normalized == VALID


def test_collapses_internal_whitespace():
    r = validate_pronto("0000   006D  0002 0000 0010 0010 0010 0010")
    assert r.valid is True
    assert r.normalized == VALID


def test_empty_input_errors():
    r = validate_pronto("   ")
    assert r.valid is False
    assert "Paste a Pronto hex code." in r.errors


def test_non_hex_characters_error():
    r = validate_pronto("abcg xyz0")
    assert r.valid is False
    assert any("hex digits only" in e for e in r.errors)


def test_wrong_word_length_errors():
    r = validate_pronto("0000 06D 0002 0000")
    assert r.valid is False
    assert any("4 hex digits" in e for e in r.errors)


def test_wrong_header_errors():
    r = validate_pronto("0100 006D 0002 0000 0010 0010 0010 0010")
    assert r.valid is False
    assert any("starting with 0000" in e for e in r.errors)


def test_header_only_is_length_error():
    r = validate_pronto("0000")
    assert r.valid is False
    assert any("burst pair count" in e for e in r.errors)


def test_truncated_body_is_length_error_and_reports_declared_pairs():
    # Declares burst1=2 (expects 8 words) but only 5 present.
    r = validate_pronto("0000 006D 0002 0000 0010")
    assert r.valid is False
    assert any("burst pair count" in e for e in r.errors)
    assert r.burst_pair_count == 2


def test_low_frequency_warns_but_stays_valid():
    # freq word 00D0 (208) -> ~19.9 kHz, below the 20 kHz floor.
    r = validate_pronto("0000 00D0 0001 0000 0010 0010")
    assert r.valid is True
    assert r.warnings
    assert any("Carrier frequency" in w for w in r.warnings)


def test_high_frequency_warns_but_stays_valid():
    # freq word 0040 (64) -> ~64.8 kHz, above the 60 kHz ceiling.
    r = validate_pronto("0000 0040 0001 0000 0010 0010")
    assert r.valid is True
    assert any("Carrier frequency" in w for w in r.warnings)
