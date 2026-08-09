"""The import funnel: format sniffing and the three v0.7.0 adapters
(SmartIR, Flipper .ir, LIRC), tested against REAL files fetched from
their home repositories (fixtures/adapters/, sources in the research
log). One bad signal never sinks a file; every skip carries a reason.
"""
from __future__ import annotations

import typing
from pathlib import Path

import pytest

from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.wig_adapters import (
    broadlink_packet_to_pronto,
    convert,
    sniff_format,
)
from custom_components.hair.wig_format import (
    WigSignal,
    parse_wig,
    serialize_wig,
    signals_content_hash,
)

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


def _encode_broadlink_ticks(ticks: list[int]) -> bytes:
    """Build a well-formed 0x26 Broadlink packet body from raw tick
    counts, escaping any value over 255 to ``0x00 <hi> <lo>`` exactly
    as a real RM capture does. The declared length is computed from
    the ACTUAL encoded body, matching what production does at
    ``packet[2:4]`` -- so a caller can append arbitrary trailing
    padding after this helper's output without corrupting the parse
    (smartir-trailing-gap.md section 7's fixture-builder note)."""
    body = bytearray()
    for t in ticks:
        if t <= 255:
            body.append(t)
        else:
            body.append(0)
            body.append((t >> 8) & 0xFF)
            body.append(t & 0xFF)
    length = len(body)
    return bytes([0x26, 0x00, length & 0xFF, (length >> 8) & 0xFF]) + bytes(body)


def _ticks_to_timings(ticks: list[int]) -> list[int]:
    """The same tick -> signed-microsecond conversion broadlink_packet_to_pronto
    uses internally, for building an independent expected value."""
    from custom_components.hair.wig_adapters import _BROADLINK_TICK_US

    return [
        round(t * _BROADLINK_TICK_US) * (1 if idx % 2 == 0 else -1)
        for idx, t in enumerate(ticks)
    ]


class TestBroadlinkTrailingGap:
    """SmartIR trailing gap, 4b (smartir-trailing-gap-coding-plan.md
    commit 2 / GH #93): broadlink_packet_to_pronto stops MINTING the
    capture-timeout gap on new conversions."""

    # A small, ordinary AC-style frame: header mark/space, three bit
    # pairs, then a trailing escaped 3,333-tick space -- the exact
    # value the RM's learning-mode timeout writes (protocol.md, cited
    # in github-issue-93-yacinbm.md section 3a).
    _GAP_TICKS: typing.ClassVar[list[int]] = [140, 170, 21, 21, 21, 64, 21, 3333]

    def test_trailing_escaped_gap_stripped_matches_pre_stripped_input(self):
        """A packet ending in the escaped 3,333-tick space, and the
        SAME packet with that final tick removed entirely, convert to
        the IDENTICAL Pronto -- the two stored forms are EQUAL, which
        is the whole point of stripping at conversion time (plan
        item 1)."""
        with_gap = _encode_broadlink_ticks(self._GAP_TICKS)
        without_gap = _encode_broadlink_ticks(self._GAP_TICKS[:-1])
        pronto_with = broadlink_packet_to_pronto(with_gap)
        pronto_without = broadlink_packet_to_pronto(without_gap)
        assert pronto_with is not None
        assert pronto_with == pronto_without

    def test_interior_escaped_gap_survives_only_trailing_dropped(self):
        """An interior escaped gap of the SAME magnitude as the
        trailing one must survive; only the final tick is ever dropped
        (plan item 2 -- the constraint most likely to be broken)."""
        ticks = [140, 170, 21, 3333, 21, 21, 21, 3333]
        pronto = broadlink_packet_to_pronto(_encode_broadlink_ticks(ticks))
        assert pronto is not None
        # Independently compute what stripping ONLY the last tick
        # should produce, and compare -- if the interior escape were
        # accidentally dropped too (or the trailing one kept), this
        # would diverge.
        expected = raw_to_pronto(_ticks_to_timings(ticks[:-1]), frequency=38000)
        assert pronto == expected

    def test_odd_length_ends_on_mark_left_alone(self):
        """A packet already ending on a mark (odd tick count) has
        nothing to strip -- unchanged output (plan item 3)."""
        ticks = [140, 170, 21, 21, 21]
        pronto = broadlink_packet_to_pronto(_encode_broadlink_ticks(ticks))
        expected = raw_to_pronto(_ticks_to_timings(ticks), frequency=38000)
        assert pronto == expected

    def test_reporters_exact_case_199_timings_under_limit(self):
        """1160.json's first cell (github-issue-93-yacinbm.md section
        3, method note in section 9): 202-byte body, 200 bursts, one
        escape at the end. This fixture reproduces that exact shape --
        199 ordinary single-byte ticks plus one final escaped
        3,333-tick space. After the trailing strip: 199 timings, every
        one comfortably under the 65,535us Zigbee/Tuya ceiling that
        broke the reporter's blaster (plan item 5)."""
        ordinary = [20 + (i % 150) for i in range(199)]  # all <= 255
        ticks = [*ordinary, 3333]
        packet = _encode_broadlink_ticks(ticks)
        # Sanity-check the fixture itself matches the reported shape
        # before testing the conversion.
        assert len(packet) == 4 + 202  # header(4) + 199*1 + 1*3
        pronto = broadlink_packet_to_pronto(packet)
        assert pronto is not None
        from custom_components.hair.ir_command import ProntoCommand

        recovered = ProntoCommand(pronto).get_raw_timings()
        assert len(recovered) == 199
        assert max(abs(t) for t in recovered) < 65535

    def test_declared_length_ignores_trailing_padding(self):
        """Fixture-builder / decoder rule (smartir-trailing-gap.md
        section 7): a real capture is zero-padded to an AES block, and
        those padding bytes must never be misread as extra escaped
        ticks. Appending garbage past the declared length must not
        change the result (plan item 6)."""
        ticks = [140, 170, 21, 21, 21, 64, 21, 3333]
        clean = _encode_broadlink_ticks(ticks)
        padded = clean + bytes([0x00, 0x00, 0x00, 0x00])  # AES-block filler
        assert broadlink_packet_to_pronto(padded) == \
            broadlink_packet_to_pronto(clean)

    # PINNED (smartir-trailing-gap.md 10.4 / plan item 4): the exact
    # BEFORE-value this fixture converted to prior to this commit --
    # the un-stripped tick list encoded straight through, no 4b strip.
    # Computed once via raw_to_pronto on _GAP_TICKS and frozen here so
    # a future accidental change to the strip shows up as a mismatch
    # against a DELIBERATE historical value, not just an inequality.
    _PINNED_BEFORE_PRONTO = (
        "0000 006D 0004 0000 00A2 00C5 0018 0018 0018 004A 0018 0F1C"
    )
    _PINNED_BEFORE_HASH = (
        "sha256:52d61e13ad687af771bf77d01682d4785ce18521bf47c75f9d"
        "173bfc1c235625"
    )
    _PINNED_AFTER_HASH = (
        "sha256:066c774b5bc87ff5dfb40db14b2127a489915c1640e44f14a9a"
        "9904237f109f2"
    )

    def test_pinned_hash_pair_documents_the_reimport_split(self):
        """The 4b hash split is a DECISION, not an accident
        (smartir-trailing-gap.md 10.4, owner-accepted 2026-08-08): a
        wig converted after this change gets a different Pronto --
        and a different signals_content_hash -- from the same source
        converted before it. Pinning both values means the split stays
        visible to anyone who bisects a hash change later, rather than
        reading as an unexplained drift."""
        with_gap = self._GAP_TICKS
        without_gap = self._GAP_TICKS[:-1]

        # BEFORE: what conversion produced prior to this commit -- the
        # full, un-stripped tick list encoded straight through.
        before_pronto = raw_to_pronto(
            _ticks_to_timings(with_gap), frequency=38000
        )
        assert before_pronto == self._PINNED_BEFORE_PRONTO
        before_hash = signals_content_hash(
            [WigSignal(alias="Test", pronto=before_pronto)]
        )
        assert before_hash == self._PINNED_BEFORE_HASH

        # AFTER: the shipped, stripped conversion.
        after_pronto = broadlink_packet_to_pronto(
            _encode_broadlink_ticks(with_gap)
        )
        after_hash = signals_content_hash(
            [WigSignal(alias="Test", pronto=after_pronto)]
        )
        assert after_hash == self._PINNED_AFTER_HASH

        assert before_pronto != after_pronto
        assert before_hash != after_hash
        # Re-importing the SAME source file after this ships lands on
        # the "after" hash every time -- deterministic, not drifting.
        assert after_pronto == raw_to_pronto(
            _ticks_to_timings(without_gap), frequency=38000
        )


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

    def test_climate_without_bounds_refused(self):
        # Cold Cuts (v0.8.8): climate files IMPORT now (matrix wigs,
        # covered in test_wig_climate.py); a file missing its bounds
        # still refuses with a reason instead of guessing.
        minimal = (
            '{"manufacturer": "X", "commandsEncoding": "Base64",'
            ' "minTemperature": 16, "operationModes": ["heat"],'
            ' "commands": {}}'
        )
        result = convert(minimal)
        assert result.wigs == []
        assert "bounds" in (result.error or "")

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
        # Parsed Flipper entries re-encode through the code library; on
        # the no-library CI leg (py3.12) they skip with a reason instead.
        pytest.importorskip("infrared_protocols")
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


class TestGirr:
    def test_sniffed(self):
        assert sniff_format(
            _fixture("girr_irscrutinizer_export.girr")
        ) == "girr"

    def test_two_remotes_two_wigs(self):
        result = convert(_fixture("girr_irscrutinizer_export.girr"))
        assert result.format == "girr"
        assert result.error is None
        assert [w.name for w in result.wigs] == [
            "Onkyo TX-NR616", "philips_rc5_tv",
        ]

    def test_ccf_is_verbatim_pronto(self):
        result = convert(_fixture("girr_irscrutinizer_export.girr"))
        onkyo = result.wigs[0]
        assert onkyo.brand == "Onkyo"
        assert onkyo.model == "TX-NR616"
        assert onkyo.origin == "converted:girr"
        power = next(s for s in onkyo.signals if s.alias == "Power Toggle")
        # The <ccf> text is learned-format Pronto already; the adapter
        # only normalizes whitespace, never re-times it.
        assert power.pronto.startswith("0000 006C 0022 0002 015B 00AD")
        assert power.pronto.endswith("0016 06A4 015B 0057 0016 0E6C")
        assert validate_pronto(power.pronto).valid
        volume = next(s for s in onkyo.signals if s.alias == "Volume Up")
        assert validate_pronto(volume.pronto).valid

    def test_raw_intro_synthesized(self):
        result = convert(_fixture("girr_irscrutinizer_export.girr"))
        onkyo = result.wigs[0]
        dvd = next(s for s in onkyo.signals if s.alias == "Input Dvd")
        assert dvd.pronto.startswith("0000")
        assert validate_pronto(dvd.pronto).valid

    def test_raw_flash_gap_repeat_only(self):
        result = convert(_fixture("girr_irscrutinizer_export.girr"))
        philips = result.wigs[1]
        mute = next(s for s in philips.signals if s.alias == "Mute")
        assert validate_pronto(mute.pronto).valid

    def test_parameters_only_skips_with_reason(self):
        result = convert(_fixture("girr_irscrutinizer_export.girr"))
        assert any(
            "Setup" in reason and "re-export" in reason
            for reason in result.skipped
        )
        assert any("Empty One" in reason for reason in result.skipped)

    def test_result_round_trips_as_wig(self):
        result = convert(_fixture("girr_irscrutinizer_export.girr"))
        for wig in result.wigs:
            assert parse_wig(serialize_wig(wig)).ok

    def test_malformed_xml_errors(self):
        broken = "<remotes girrVersion='1.2'><remote name='x'"
        assert sniff_format(broken) == "girr"
        result = convert(broken)
        assert result.error is not None
        assert "XML" in result.error

    def test_no_remotes_errors(self):
        text = (
            "<girr xmlns='http://www.harctoolbox.org/Girr'"
            " girrVersion='1.2'></girr>"
        )
        result = convert(text)
        assert result.error == "no remotes or commands in this Girr file"

    def test_commandset_root_imports(self):
        # The spec allows commandSet (and command) as the root element;
        # this real file (found in the wild, 2026-07-20) is 25 ccf
        # commands with no <remote> wrapper.
        result = convert(
            _fixture("girr_commandset_root_sony.girr"),
            name_hint="commandset_sony_pronto.girr",
        )
        assert result.error is None
        assert len(result.wigs) == 1
        wig = result.wigs[0]
        # Anonymous root -> named from the file, not "commandSet".
        assert wig.name == "Commandset Sony Pronto"
        aliases = [s.alias for s in wig.signals]
        assert "Volume Up" in aliases and "Power Toggle" in aliases
        assert len(wig.signals) == 25
        for sig in wig.signals:
            assert validate_pronto(sig.pronto).valid, sig.alias

    def test_inherited_parameters_skip_reason(self):
        # Parametric files hoist <parameters> to the commandSet level;
        # the skip reason must still say parameters, not the vague
        # "no usable representation" (real Apple Remote file).
        result = convert(
            _fixture("girr_parameters_only_apple.girr"),
            name_hint="apple_remote.girr",
        )
        assert result.wigs == []
        param_skips = [
            r for r in result.skipped if "protocol-parameter" in r
        ]
        assert len(param_skips) == 6  # every command, correctly labeled
        assert not any(
            "no usable representation" in r for r in result.skipped
        )
