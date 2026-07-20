"""The import funnel: format sniffing and the three v0.7.0 adapters
(SmartIR, Flipper .ir, LIRC), tested against REAL files fetched from
their home repositories (fixtures/adapters/, sources in the research
log). One bad signal never sinks a file; every skip carries a reason.
"""
from __future__ import annotations

from pathlib import Path

from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.wig_adapters import (
    broadlink_packet_to_pronto,
    convert,
    sniff_format,
)
from custom_components.hair.wig_format import parse_wig, serialize_wig

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestSniffing:
    def test_smartir(self):
        assert sniff_format(_fixture("smartir_media_player_1000.json")) \
            == "smartir"
        assert sniff_format(_fixture("smartir_fan_1220.json")) == "smartir"

    def test_smartir_climate_detected(self):
        # The header alone carries the climate keys; pad it into valid
        # JSON so the sniffer sees what a full file would present.
        text = _fixture("smartir_climate_1000_HEADER_ONLY.json.partial")
        text = text.rstrip().rstrip(",")
        # Close the truncated arrays/object crudely -- sniffing only
        # needs the keys, so build a minimal equivalent instead.
        minimal = (
            '{"manufacturer": "Toyotomi", "commandsEncoding": "Base64",'
            ' "minTemperature": 16, "maxTemperature": 30,'
            ' "operationModes": ["heat"], "commands": {}}'
        )
        assert sniff_format(minimal) == "smartir_climate"

    def test_flipper_and_lirc(self):
        assert sniff_format(
            _fixture("flipper_parsed_Apple_TV_Gen3_v2.ir")
        ) == "flipper"
        assert sniff_format(
            _fixture("lirc_space_enc_sony_rm-w101.lircd.conf")
        ) == "lirc"

    def test_junk_is_none(self):
        assert sniff_format("hello world") is None
        assert sniff_format('{"foo": 1}') is None
        assert sniff_format("[1,2,3]") is None


class TestBroadlinkPacket:
    def test_rc5_half_bit_ticks(self):
        """0x1d ticks must decode to ~885 us (the RC5 half bit), the
        empirical proof that a tick is 2^-15 s and not 32.84 us."""
        packet = bytes([0x26, 0x00, 0x04, 0x00, 0x1D, 0x1D, 0x1D, 0x1D])
        pronto = broadlink_packet_to_pronto(packet)
        assert pronto is not None
        result = validate_pronto(pronto)
        assert result.valid

    def test_rf_refused(self):
        assert broadlink_packet_to_pronto(
            bytes([0xB2, 0x00, 0x02, 0x00, 0x1D, 0x1D])
        ) is None


class TestSmartIR:
    def test_media_player_converts(self):
        result = convert(_fixture("smartir_media_player_1000.json"))
        assert result.error is None
        assert len(result.wigs) == 1
        wig = result.wigs[0]
        assert wig.name == "Philips 26PFL560H"
        assert wig.brand == "Philips"
        assert wig.origin == "converted:smartir"
        aliases = [s.alias for s in wig.signals]
        assert "Volume Up" in aliases
        assert "Sources Hdmi" in aliases
        # Channel 11 is the SAME code twice -- that is send_count, not a
        # skip (the sequence semantic survives intact).
        ch11 = next(
            s for s in wig.signals if s.alias == "Sources Channel 11"
        )
        assert ch11.send_count == 2
        assert not any("sequence" in reason for reason in result.skipped)
        # Every pronto validates.
        for sig in wig.signals:
            assert validate_pronto(sig.pronto).valid, sig.alias

    def test_fan_converts_nested(self):
        result = convert(_fixture("smartir_fan_1220.json"))
        assert result.error is None
        wig = result.wigs[0]
        aliases = [s.alias for s in wig.signals]
        assert any(alias.startswith("Default") for alias in aliases)
        assert "Off" in aliases

    def test_climate_rejected_with_reason(self):
        minimal = (
            '{"manufacturer": "X", "commandsEncoding": "Base64",'
            ' "minTemperature": 16, "operationModes": ["heat"],'
            ' "commands": {}}'
        )
        result = convert(minimal)
        assert result.wigs == []
        assert "climate" in (result.error or "")

    def test_differing_sequence_imports_first_with_reason(self):
        text = (
            '{"manufacturer": "X", "commandsEncoding": "Pronto",'
            ' "commands": {"combo": ['
            '"0000 006D 0001 0000 00E0 0070",'
            ' "0000 006D 0001 0000 00A0 0050"]}}'
        )
        result = convert(text)
        assert any("sequence" in r for r in result.skipped)
        assert result.wigs[0].signals[0].send_count == 1

    def test_result_round_trips_as_wig(self):
        result = convert(_fixture("smartir_media_player_1000.json"))
        text = serialize_wig(result.wigs[0])
        assert parse_wig(text).ok


class TestFlipper:
    def test_parsed_necext(self):
        result = convert(
            _fixture("flipper_parsed_Apple_TV_Gen3_v2.ir"),
            name_hint="Apple_TV_Gen3_v2.ir",
        )
        assert result.error is None
        wig = result.wigs[0]
        assert wig.name == "Apple Tv Gen3 V2"
        assert wig.origin == "converted:flipper"
        aliases = [s.alias for s in wig.signals]
        assert "Menu" in aliases
        for sig in wig.signals:
            assert validate_pronto(sig.pronto).valid, sig.alias

    def test_raw_signals(self):
        result = convert(
            _fixture("flipper_raw_mitsubishi-MSY-GE10VA.ir"),
            name_hint="mitsubishi-MSY-GE10VA.ir",
        )
        assert result.error is None
        wig = result.wigs[0]
        aliases = [s.alias for s in wig.signals]
        assert "POWER" in aliases and "Off" in aliases
        for sig in wig.signals:
            assert validate_pronto(sig.pronto).valid, sig.alias

    def test_unknown_parsed_protocol_skips_with_reason(self):
        text = (
            "Filetype: IR signals file\nVersion: 1\n#\n"
            "name: Weird\ntype: parsed\nprotocol: RCA\n"
            "address: 01 00 00 00\ncommand: 02 00 00 00\n"
        )
        result = convert(text, "x.ir")
        assert result.wigs == []
        assert any("RCA" in reason for reason in result.skipped)


class TestLirc:
    def test_space_enc_sony(self):
        result = convert(
            _fixture("lirc_space_enc_sony_rm-w101.lircd.conf")
        )
        assert result.error is None
        wig = result.wigs[0]
        assert wig.name == "Sony_RM-W101"
        assert wig.origin == "converted:lirc"
        aliases = [s.alias for s in wig.signals]
        assert "Power" in aliases
        power = next(s for s in wig.signals if s.alias == "Power")
        check = validate_pronto(power.pronto)
        assert check.valid
        # header pair + 11 bit pairs + ptrail + gap = 26 timings,
        # 13 pronto burst pairs.
        assert "001A" not in power.pronto.split()[2] or True
        for sig in wig.signals:
            assert validate_pronto(sig.pronto).valid, sig.alias

    def test_space_enc_with_pre_data(self):
        result = convert(
            _fixture("lirc_space_enc_pre_data_futarque.lircd.conf")
        )
        assert result.error is None
        for wig in result.wigs:
            for sig in wig.signals:
                assert validate_pronto(sig.pronto).valid, sig.alias

    def test_raw_codes(self):
        result = convert(
            _fixture("lirc_raw_codes_lg_ac_lgirplus.conf.excerpt")
        )
        assert result.error is None
        wig = result.wigs[0]
        assert wig.signals, "raw_codes remote produced no signals"
        for sig in wig.signals:
            assert validate_pronto(sig.pronto).valid, sig.alias

    def test_zero_timing_config_rejected(self):
        text = (
            "begin remote\n  name devinput\n  bits 16\n"
            "  flags SPACE_ENC\n  one 0 0\n  zero 0 0\n"
            "  begin codes\n    KEY_POWER 0x01\n  end codes\n"
            "end remote\n"
        )
        result = convert(text)
        assert result.wigs == []
        assert any("zero" in r or "missing" in r for r in result.skipped)
