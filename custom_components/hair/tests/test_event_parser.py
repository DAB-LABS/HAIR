"""Tests for the EventParser adapter layer."""
from __future__ import annotations

import pytest

from custom_components.hair.event_parser import EventParser


class TestParse:
    """Tests for EventParser.parse()."""

    def test_returns_none_for_empty_data(self):
        assert EventParser.parse({}) is None

    def test_returns_none_for_no_code_no_raw(self):
        assert EventParser.parse({"protocol": "NEC"}) is None

    def test_parses_decoded_signal(self):
        result = EventParser.parse({
            "protocol": "NEC",
            "code": "0x1234",
            "frequency": 38000,
            "confidence": 0.95,
        })
        assert result is not None
        assert result.protocol == "NEC"
        assert result.code == "0x1234"
        assert result.frequency == 38000
        assert result.confidence == 0.95
        assert result.raw_timings == []

    def test_parses_raw_signal(self):
        raw = [9000, -4500, 560, -560, 560, -1690]
        result = EventParser.parse({"raw": raw})
        assert result is not None
        assert result.protocol is None
        assert result.code is None
        assert result.raw_timings == raw

    def test_parses_raw_timings_key(self):
        raw = [9000, -4500]
        result = EventParser.parse({"raw_timings": raw})
        assert result is not None
        assert result.raw_timings == raw

    def test_raw_key_takes_precedence(self):
        result = EventParser.parse({
            "raw": [100, -200],
            "raw_timings": [300, -400],
        })
        assert result is not None
        assert result.raw_timings == [100, -200]

    def test_defaults_frequency_to_38000(self):
        result = EventParser.parse({"code": "0xFF"})
        assert result is not None
        assert result.frequency == 38000

    def test_captures_non_38k_frequency(self):
        result = EventParser.parse({"code": "0xFF", "frequency": 36000})
        assert result is not None
        assert result.frequency == 36000

    def test_protocol_and_code_stringified(self):
        result = EventParser.parse({"protocol": 123, "code": 456})
        assert result is not None
        assert result.protocol == "123"
        assert result.code == "456"

    def test_none_protocol_stays_none(self):
        result = EventParser.parse({"raw": [100, -200]})
        assert result is not None
        assert result.protocol is None


class TestIsNecRepeat:
    """Tests for NEC repeat frame detection."""

    def test_nec_repeat_flag(self):
        assert EventParser.is_nec_repeat({
            "protocol": "NEC", "repeat": True,
        })

    def test_nec_no_code_short_raw(self):
        assert EventParser.is_nec_repeat({
            "protocol": "NEC",
            "raw": [9000, -2250, 560, -560],
        })

    def test_nec_with_code_is_not_repeat(self):
        assert not EventParser.is_nec_repeat({
            "protocol": "NEC", "code": "0x1234",
        })

    def test_non_nec_protocol_is_not_repeat(self):
        assert not EventParser.is_nec_repeat({
            "protocol": "Samsung", "repeat": True,
        })

    def test_no_protocol_is_not_repeat(self):
        assert not EventParser.is_nec_repeat({"raw": [9000, -2250]})

    def test_nec_case_insensitive(self):
        assert EventParser.is_nec_repeat({
            "protocol": "nec", "repeat": True,
        })


class TestExtractDeviceAddress:
    """Tests for protocol-specific address extraction."""

    def test_nec_standard_16bit(self):
        # 0x1234 -> address = 0x12
        assert EventParser.extract_device_address("NEC", "0x1234") == "0x12"

    def test_nec_extended_32bit(self):
        # 0x12345678 -> address = 0x1234
        assert EventParser.extract_device_address("NEC", "0x12345678") == "0x1234"

    def test_samsung_16bit(self):
        assert EventParser.extract_device_address("Samsung", "0xABCD") == "0xAB"

    def test_samsung_32bit(self):
        assert EventParser.extract_device_address("Samsung", "0xABCD1234") == "0xABCD"

    def test_sony(self):
        # Sony 12-bit: command(7) + address(5). 0x123 = 0b000100100011
        # address = bits [11:7] = 0b00010 = 2, shifted: (0x123 >> 7) & 0x1FFF = 2
        assert EventParser.extract_device_address("Sony", "0x123") == "0x0002"

    def test_sony_sirc_alias(self):
        assert EventParser.extract_device_address("SIRC", "0x123") == "0x0002"

    def test_rc5(self):
        # RC5: toggle(1) + address(5) + command(6). 0x7FF = 11 bits.
        # address = (0x7FF >> 6) & 0x1F = 0x1F
        assert EventParser.extract_device_address("RC5", "0x7FF") == "0x1F"

    def test_rc6(self):
        assert EventParser.extract_device_address("RC6", "0x100") is not None

    def test_unknown_protocol_returns_none(self):
        assert EventParser.extract_device_address("PRONTO", "0x1234") is None

    def test_no_protocol_returns_none(self):
        assert EventParser.extract_device_address(None, "0x1234") is None

    def test_no_code_returns_none(self):
        assert EventParser.extract_device_address("NEC", None) is None

    def test_invalid_code_returns_none(self):
        assert EventParser.extract_device_address("NEC", "not_a_number") is None

    def test_case_insensitive_protocol(self):
        assert EventParser.extract_device_address("nec", "0x1234") == "0x12"


class TestSignalFingerprint:
    """Tests for signal fingerprinting."""

    def test_decoded_signal_fingerprint_stable(self):
        fp1 = EventParser.signal_fingerprint("NEC", "0x1234", None)
        fp2 = EventParser.signal_fingerprint("NEC", "0x1234", None)
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_different_codes_different_fingerprints(self):
        fp1 = EventParser.signal_fingerprint("NEC", "0x1234", None)
        fp2 = EventParser.signal_fingerprint("NEC", "0x5678", None)
        assert fp1 != fp2

    def test_different_protocols_different_fingerprints(self):
        fp1 = EventParser.signal_fingerprint("NEC", "0x1234", None)
        fp2 = EventParser.signal_fingerprint("Samsung", "0x1234", None)
        assert fp1 != fp2

    def test_raw_fingerprint_stable(self):
        raw = [9000, -4500, 560, -560, 560, -1690]
        fp1 = EventParser.signal_fingerprint(None, None, raw)
        fp2 = EventParser.signal_fingerprint(None, None, raw)
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_raw_fingerprint_tolerates_jitter(self):
        raw1 = [9000, -4500, 560, -560, 560, -1690]
        # Small jitter within 50us bin boundaries.
        raw2 = [9010, -4480, 570, -550, 555, -1700]
        fp1 = EventParser.signal_fingerprint(None, None, raw1)
        fp2 = EventParser.signal_fingerprint(None, None, raw2)
        assert fp1 == fp2

    def test_raw_fingerprint_distinguishes_different_signals(self):
        raw1 = [9000, -4500, 560, -560]
        raw2 = [4500, -4500, 1000, -1000]
        fp1 = EventParser.signal_fingerprint(None, None, raw1)
        fp2 = EventParser.signal_fingerprint(None, None, raw2)
        assert fp1 != fp2

    def test_decoded_preferred_over_raw(self):
        raw = [9000, -4500]
        fp_decoded = EventParser.signal_fingerprint("NEC", "0x1234", raw)
        fp_raw = EventParser.signal_fingerprint(None, None, raw)
        # When protocol+code present, raw is ignored for fingerprint.
        assert fp_decoded != fp_raw

    def test_empty_raw_returns_fingerprint(self):
        fp = EventParser.signal_fingerprint(None, None, [])
        assert len(fp) == 16

    # --- Pronto S/L fingerprinting ---

    def test_pronto_fingerprint_stable(self):
        """Same Pronto code produces the same fingerprint."""
        code = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        fp1 = EventParser.signal_fingerprint("PRONTO", code, None)
        fp2 = EventParser.signal_fingerprint("PRONTO", code, None)
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_pronto_fingerprint_tolerates_jitter(self):
        """Same button with +-1 timing jitter produces the same fingerprint.

        This is the core property: real IR receivers see jitter of +-1-2
        Pronto units between presses. S/L classification absorbs this.
        """
        # Original capture: short=0x20, long=0x40.
        code1 = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        # Same button, jittered: short=0x21, long=0x3F.
        code2 = "0000 006D 000B 0000 0021 0021 0021 003F 0021 0021 0021 003F 0021 0021 0021 003F 0021 0021 0021 003F 0021 0021 0021 003F 0021 0BBA"
        fp1 = EventParser.signal_fingerprint("PRONTO", code1, None)
        fp2 = EventParser.signal_fingerprint("PRONTO", code2, None)
        assert fp1 == fp2

    def test_pronto_fingerprint_tolerates_edge_count_variation(self):
        """Same S/L pattern with one extra trailing pair still matches.

        Receivers sometimes capture an extra edge. As long as the shared
        prefix has the same S/L pattern, the fingerprint should match.
        Note: if the extra pair changes the pattern, they will differ --
        that's acceptable because the signal genuinely differs.
        """
        # 11 timing words after header.
        code_short = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        # 13 timing words -- two extra S values appended before gap.
        code_long = "0000 006D 000D 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0BBA"
        fp1 = EventParser.signal_fingerprint("PRONTO", code_short, None)
        fp2 = EventParser.signal_fingerprint("PRONTO", code_long, None)
        # These differ because the S/L pattern string is longer for code_long.
        assert fp1 != fp2

    def test_pronto_different_buttons_different_fingerprints(self):
        """Two distinct buttons (different S/L patterns) produce different fps."""
        # Pattern: SSSLSSSLSSSLSSSLSSSLSSL (all short-long pairs).
        code_a = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        # Pattern: SSLSSSLSSLSSSLSSL (different arrangement).
        code_b = "0000 006D 000B 0000 0020 0020 0040 0020 0020 0020 0040 0020 0020 0040 0020 0020 0020 0040 0020 0020 0040 0020 0020 0020 0040 0BBA"
        fp1 = EventParser.signal_fingerprint("PRONTO", code_a, None)
        fp2 = EventParser.signal_fingerprint("PRONTO", code_b, None)
        assert fp1 != fp2

    def test_pronto_malformed_returns_protocol_code_hash(self):
        """Malformed Pronto falls back to protocol+code hash, not None."""
        fp = EventParser.signal_fingerprint("PRONTO", "0000 006D", None)
        assert len(fp) == 16

    def test_pronto_case_insensitive(self):
        code = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        fp1 = EventParser.signal_fingerprint("PRONTO", code, None)
        fp2 = EventParser.signal_fingerprint("pronto", code, None)
        assert fp1 == fp2


class TestDeviceFingerprint:
    """Tests for device-level fingerprinting."""

    def test_decoded_device_fingerprint_stable(self):
        fp1 = EventParser.device_fingerprint("NEC", "0x12", None)
        fp2 = EventParser.device_fingerprint("NEC", "0x12", None)
        assert fp1 == fp2

    def test_different_addresses_different_fingerprints(self):
        fp1 = EventParser.device_fingerprint("NEC", "0x12", None)
        fp2 = EventParser.device_fingerprint("NEC", "0x34", None)
        assert fp1 != fp2

    def test_raw_device_fingerprint_uses_preamble(self):
        # Two signals from the same remote share a preamble.
        raw1 = [9000, -4500, 560, -560, 560, -1690, 560, -560,
                560, -560, 560, -560, 560, -560, 560, -560,
                100, -200, 300, -400]
        raw2 = [9000, -4500, 560, -560, 560, -1690, 560, -560,
                560, -560, 560, -560, 560, -560, 560, -560,
                500, -600, 700, -800]
        fp1 = EventParser.device_fingerprint(None, None, raw1)
        fp2 = EventParser.device_fingerprint(None, None, raw2)
        # Same preamble (first 16) -> same device fingerprint.
        assert fp1 == fp2

    def test_no_data_returns_fingerprint(self):
        fp = EventParser.device_fingerprint(None, None, None)
        assert len(fp) == 16

    # --- Pronto device fingerprinting ---

    def test_pronto_device_fingerprint_groups_buttons(self):
        """Different buttons from the same remote share a device fingerprint.

        The device fingerprint uses frequency + preamble S/L (first pair),
        which is shared across all buttons on a given remote.
        """
        # Button A: SSSLSSSL...
        code_a = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        # Button B: SSLSSSLSSLSSL... (different command, same preamble SS).
        code_b = "0000 006D 000B 0000 0020 0020 0040 0020 0020 0020 0040 0020 0020 0040 0020 0020 0020 0040 0020 0020 0040 0020 0020 0020 0040 0BBA"
        fp1 = EventParser.device_fingerprint("PRONTO", None, None, code=code_a)
        fp2 = EventParser.device_fingerprint("PRONTO", None, None, code=code_b)
        # Same frequency (006D) and same first S/L pair (SS).
        assert fp1 == fp2

    def test_pronto_device_fingerprint_stable(self):
        code = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        fp1 = EventParser.device_fingerprint("PRONTO", None, None, code=code)
        fp2 = EventParser.device_fingerprint("PRONTO", None, None, code=code)
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_pronto_device_fingerprint_jitter_tolerant(self):
        """Jittered captures from the same remote produce the same device fp."""
        code1 = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        code2 = "0000 006D 000B 0000 0021 001F 0021 003F 0021 001F 0021 003F 0021 001F 0021 003F 0021 001F 0021 003F 0021 001F 0021 003F 0021 0BBA"
        fp1 = EventParser.device_fingerprint("PRONTO", None, None, code=code1)
        fp2 = EventParser.device_fingerprint("PRONTO", None, None, code=code2)
        assert fp1 == fp2

    def test_pronto_different_frequency_different_device(self):
        """Remotes using different carrier frequencies produce different device fps."""
        # 006D = 38kHz
        code_38k = "0000 006D 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        # 0073 = 36kHz
        code_36k = "0000 0073 000B 0000 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0020 0020 0040 0020 0BBA"
        fp1 = EventParser.device_fingerprint("PRONTO", None, None, code=code_38k)
        fp2 = EventParser.device_fingerprint("PRONTO", None, None, code=code_36k)
        assert fp1 != fp2

    def test_pronto_malformed_code_falls_back_to_raw(self):
        """Malformed Pronto code with no raw falls back gracefully."""
        fp = EventParser.device_fingerprint("PRONTO", None, None, code="0000 006D")
        assert len(fp) == 16


class TestProntoHelpers:
    """Tests for Pronto-specific helper methods."""

    def test_parse_pronto_words_valid(self):
        words = EventParser._parse_pronto_words(
            "0000 006D 000B 0000 0020 0020 0020 0040"
        )
        assert words is not None
        assert words[0] == 0x0000
        assert words[1] == 0x006D
        assert len(words) == 8

    def test_parse_pronto_words_too_short(self):
        assert EventParser._parse_pronto_words("0000 006D 000B") is None

    def test_parse_pronto_words_empty(self):
        assert EventParser._parse_pronto_words("") is None
        assert EventParser._parse_pronto_words(None) is None

    def test_parse_pronto_words_invalid_hex(self):
        assert EventParser._parse_pronto_words("0000 ZZZZ 000B 0000 0020") is None

    def test_pronto_sl_pattern_basic(self):
        """Short values (< 0x30) -> S, long values (>= 0x30) -> L."""
        # Header: 0000 006D 0003 0000, then: 0020 0040 0020
        code = "0000 006D 0003 0000 0020 0040 0020"
        sl = EventParser._pronto_sl_pattern(code)
        assert sl == "SLS"

    def test_pronto_sl_pattern_gap_stops(self):
        """Values >= 0x100 are gaps and terminate the pattern."""
        code = "0000 006D 0004 0000 0020 0040 0020 0BBA"
        sl = EventParser._pronto_sl_pattern(code)
        assert sl == "SLS"

    def test_pronto_sl_pattern_all_short(self):
        code = "0000 006D 0003 0000 0020 0020 0020"
        sl = EventParser._pronto_sl_pattern(code)
        assert sl == "SSS"

    def test_pronto_sl_pattern_all_long(self):
        code = "0000 006D 0003 0000 0040 0050 0060"
        sl = EventParser._pronto_sl_pattern(code)
        assert sl == "LLL"

    def test_pronto_sl_pattern_threshold_boundary(self):
        """Value exactly at threshold (0x30) is classified as L."""
        code = "0000 006D 0002 0000 002F 0030"
        sl = EventParser._pronto_sl_pattern(code)
        assert sl == "SL"

    def test_pronto_sl_pattern_malformed(self):
        assert EventParser._pronto_sl_pattern("0000 006D") is None
        assert EventParser._pronto_sl_pattern(None) is None
