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
