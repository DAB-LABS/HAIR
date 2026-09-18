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


def test_the_unmodulated_header_is_accepted_and_says_so():
    """Item 6: ``0100`` is a learned code with no carrier.

    It was refused here until import phase 1, with the message that
    named ``0000``. The layout is the same and the second word is still
    the time base; what the header says is that nothing modulates it,
    which the result now carries as ``modulated``.
    """
    r = validate_pronto("0100 006D 0002 0000 0010 0010 0010 0010")
    assert r.valid is True
    assert r.modulated is False
    assert r.frequency_khz is None
    assert r.warnings == []


def test_a_modulated_code_still_reports_its_carrier():
    r = validate_pronto("0000 006D 0002 0000 0010 0010 0010 0010")
    assert r.valid is True
    assert r.modulated is True
    assert r.frequency_khz == 38.0


def test_a_parameter_header_is_still_refused_by_name():
    """``5000`` and its kin name a code rather than a waveform."""
    r = validate_pronto("5000 006D 0002 0000 0010 0010 0010 0010")
    assert r.valid is False
    assert any("0000 or 0100" in e for e in r.errors)
    assert any("5000" in e for e in r.errors)


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
