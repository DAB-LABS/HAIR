"""Tasmota IR codes in the Closet and the paste box (import phase 2).

Tasmota has no export, so fixtures/adapters/tasmota_codes.txt is
written in the shapes its users keep: one code per line, an optional
leading name, a markdown table, console lines with their MQTT topic. Its
values are chosen for the fixture or rendered by HAIR's own encoders.
The compressed notation is tested first against the worked example in
Tasmota's documentation.

WHAT ANCHORS EACH PROTOCOL. A test that rendered a code and then decoded
it with the same assumptions would prove only that the reader agrees
with itself. So each mapping is checked against something stated
outside it: for the pulse-distance families, Tasmota's own ``DataLSB``
convention (the bytes in the order sent, each least significant bit
first); for the others, the field layout IRremoteESP8266 documents for
its encoders, read back through HAIR's decoder classes.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.rc6 import RC6Command
from custom_components.hair.decoders.sharp import SharpCommand
from custom_components.hair.decoders.sony import SonyCommand
from custom_components.hair.pasted_code import (
    CARRIER_NOTE,
    SOURCE_TASMOTA,
    SOURCE_TASMOTA_RAW,
    coerce_pasted_code,
)
from custom_components.hair.tasmota_ir import (
    TasmotaError,
    find_code,
    parse_raw,
    render,
)
from custom_components.hair.tests.wire_bits import (
    frame_bytes,
    frames,
    timings,
)
from custom_components.hair.websocket_api import (
    ws_clip_validate_pronto,
    ws_wigs_upload,
)
from custom_components.hair.wig_adapters import convert, sniff

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"
CODES = "tasmota_codes.txt"
AMBIGUOUS = "ambiguous_globalcache_and_tasmota.txt"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _wig():
    result = convert(_read(CODES), CODES)
    return result, {s.alias: s for s in result.wigs[0].signals}


def _wire(pronto: str) -> list[list[int]]:
    return [frame_bytes(bits) for bits in frames(timings(pronto))]


def _lines() -> dict[str, str]:
    """name -> code, for every named code line in the fixture."""
    out = {}
    for line in _read(CODES).splitlines():
        found = find_code(line)
        if found and found[0]:
            out[found[0]] = found[1]
    return out


class TestCompressedNotation:
    def test_the_vendor_worked_example(self):
        """Tasmota's documentation decodes this string by hand; the
        reader must give exactly its answer."""
        assert parse_raw("+8570-4240+550-1580C-510+565-1565F-505Fh") == [
            8570, -4240, 550, -1580, 550, -510, 565, -1565, 565, -505,
            565, -505,
        ]

    def test_letter_case_is_checked_against_position(self):
        """MUTATION CHECK: a capital letter is a mark, a small one a
        space. A reader that ignored the case, or read it backwards,
        would take this damaged string as a code."""
        with pytest.raises(TasmotaError, match="out of order"):
            parse_raw("+8570-4240+550-1580c-510+565-1565F-505Fh")
        with pytest.raises(TasmotaError, match="out of order"):
            parse_raw("+8570-4240+550-1580C-510+565-1565F-505FH")

    def test_signs_are_checked_against_position(self):
        with pytest.raises(TasmotaError, match="out of order"):
            parse_raw("+8570+4240+550-1580")

    def test_a_letter_before_its_value(self):
        with pytest.raises(TasmotaError, match="not given yet"):
            parse_raw("+8570-4240+550-1580E-510")

    def test_a_bare_hex_value_as_tasmota_prints_it(self):
        """Tasmota's parser takes ``"Data":0x...`` unquoted, which is not
        JSON; the reader takes it too, and as hex, not as a 0."""
        quoted = render('IRsend {"Protocol":"NEC","Bits":32,"Data":"0x48B7807F"}')
        bare = render('IRsend {"Protocol":"NEC","Bits":32,"Data":0x48B7807F}')
        assert bare.pronto == quoted.pronto

    def test_a_documentation_style_capture(self):
        """``"RawData":[+...]`` is not JSON either; the timings still read."""
        line = (
            '{"IrReceived":{"Protocol":"LG","Bits":28,"Data":"0x1",'
            '"RawData":[+9000-4500+560-560C-1690C-560C],"RawDataInfo":[8,8,0]}}'
        )
        code = render(line)
        assert code.carrier_source == "assumed"
        assert code.notes == [
            "used the raw timings (protocol LG has no encoder in HAIR yet)"
        ]

    def test_a_plain_list(self):
        assert parse_raw("926,844,958,832") == [926, -844, 958, -832]


class TestCarrier:
    @pytest.mark.parametrize("head,hz,source", [
        ("0", 38000, "assumed"),
        ("36000", 36000, "declared"),
        ("40", 40000, "declared"),
    ])
    def test_raw_frequency(self, head, hz, source):
        code = render(f"IRsend {head},9000,4500,560,560,560,1690")
        assert (code.carrier_hz, code.carrier_source) == (hz, source)

    def test_a_bare_compressed_string_is_assumed(self):
        code = render("+9000-4500+560-560C-1690")
        assert (code.carrier_hz, code.carrier_source) == (38000, "assumed")

    def test_the_file_records_where_each_carrier_came_from(self):
        _, signals = _wig()
        carrier = {a: s.extra["carrier"] for a, s in signals.items()}
        assert carrier["Power"] == {"hz": 38000, "source": "protocol"}
        assert carrier["Fan"] == {"hz": 38000, "source": "assumed"}
        assert carrier["Light"] == {"hz": 38000, "source": "declared"}
        assert carrier["Raw Bits"] == {"hz": 38000, "source": "assumed"}
        assert carrier["Global"] == {"hz": 38000, "source": "declared"}
        assert carrier["Input"] == {"hz": 40000, "source": "protocol"}


class TestTheFile:
    def test_sniffs_as_tasmota(self):
        assert sniff(_read(CODES), CODES).format == "tasmota"
        payload = "tasmota_irsend_payload.json"
        assert sniff(_read(payload), payload).format == "tasmota"

    def test_every_code_lands_or_is_receipted(self):
        result, signals = _wig()
        assert sorted(signals) == sorted([
            "Power", "Volume Up", "Volume Down", "Mute", "Input", "Menu",
            "Guide", "Panel", "Panel Old", "Sharp Power", "Pioneer Power",
            "Fan", "Light", "Raw Bits", "Global", "Signal 18", "Signal 19",
            "Signal 20",
        ])
        assert result.skipped == [
            "LG TV: protocol LG has no encoder in HAIR yet",
            "Climate: climate state (IRhvac), not a code",
            "Signal 20: used the raw timings (protocol LG has no encoder "
            "in HAIR yet)",
        ]
        assert result.folds == [
            "Mute: Tasmota sends this 2 times; HAIR stores it once (set the "
            "send count to match)",
        ]
        wig = result.wigs[0]
        assert wig.origin == "converted:tasmota"
        assert wig.notes == (
            "Imported from Tasmota IR codes. 5 lines without a code passed "
            "over."
        )
        assert {s.send_count for s in signals.values()} == {1}

    def test_a_single_payload_file(self):
        result = convert(
            _read("tasmota_irsend_payload.json"), "tasmota_irsend_payload.json"
        )
        assert [s.alias for s in result.wigs[0].signals] == ["Signal 1"]
        assert _wire(result.wigs[0].signals[0].pronto) == [
            [0x12, 0xED, 0x01, 0xFE],
        ]

    def test_nothing_usable_is_refused(self):
        result = convert('Climate: IRhvac {"Vendor":"DAIKIN"}\n', "x.txt")
        assert not result.wigs
        assert "climate state" in result.error


class TestProtocolsOnTheWire:
    """Each protocol checked against a statement outside the reader."""

    @pytest.mark.parametrize("alias,wire", [
        ("Power", [[0x12, 0xED, 0x01, 0xFE]]),          # DataLSB 0x12ED01FE
        ("Volume Up", [[0x12, 0xED, 0x02, 0xFD]]),
        ("Volume Down", [[0x12, 0xED, 0x03, 0xFC]]),    # given as DataLSB
        ("Signal 18", [[0x12, 0xED, 0x10, 0xEF]]),      # its own DataLSB
        ("Fan", [[0x12, 0xED, 0x20, 0xDF]]),
        ("Light", [[0x12, 0xED, 0x21, 0xDE]]),
        ("Raw Bits", [[0x12, 0xED, 0x22, 0xDD]]),
        ("Global", [[0x12, 0xED, 0x23, 0xDC]]),
        ("Mute", [[0x0B, 0x0B, 0x0F, 0xF0]]),           # SAMSUNG 0xD0D0F00F
        ("Pioneer Power", [[0xA6, 0x59, 0x1C, 0xE3]] * 2),
    ])
    def test_pulse_distance_bytes_are_the_datalsb_bytes(self, alias, wire):
        _, signals = _wig()
        assert _wire(signals[alias].pronto) == wire

    def test_panasonic_both_ways_of_writing_bits(self):
        """MUTATION CHECK: the PANASONIC trap. Today's firmware writes
        Bits 48 and the whole frame; the old driver wrote the vendor
        address 0x4004 (16388) in Bits. Both are one code."""
        _, signals = _wig()
        assert signals["Panel"].pronto == signals["Panel Old"].pronto
        assert _wire(signals["Panel"].pronto) == [
            [0x02, 0x20, 0x80, 0x00, 0x39, 0xB9],
        ]

    def test_a_bits_count_is_not_an_address(self):
        with pytest.raises(TasmotaError, match="48"):
            render('IRsend {"Protocol":"PANASONIC","Bits":40,"Data":"0x1"}')

    def test_sony_fields(self):
        # IRremoteESP8266 sends SIRC data most significant bit first, so
        # the 12 bits of 0x6B4 reversed are command 0x56, address 0x05.
        _, signals = _wig()
        decoded = SonyCommand.from_raw_timings(timings(signals["Input"].pronto))
        assert (decoded.address, decoded.command) == (0x05, 0x56)

    def test_rc5_fields(self):
        # encodeRC5: toggle in bit 11, address in bits 10-6, command 5-0.
        _, signals = _wig()
        decoded = RC5Command.from_raw_timings(timings(signals["Menu"].pronto))
        assert (decoded.address, decoded.command, decoded.toggle) == (
            0x10, 0x0C, 0,
        )

    def test_rc5x_puts_the_field_bit_in_command_bit_6(self):
        code = render('IRsend {"Protocol":"RC5X","Bits":13,"Data":"0x140C"}')
        decoded = RC5Command.from_raw_timings(timings(code.pronto))
        assert (decoded.address, decoded.command) == (0x10, 0x4C)

    def test_rc6_fields(self):
        # encodeRC6 mode 0: address << 8 | command; the toggle is bit 16.
        _, signals = _wig()
        decoded = RC6Command.from_raw_timings(timings(signals["Guide"].pronto))
        assert (decoded.mode, decoded.address, decoded.command) == (0, 0, 0x2A)
        assert decoded.toggle == 1

    def test_sharp_fields(self):
        # encodeSharp writes address << 10 | command << 2 | expansion << 1
        # | check, each field most significant bit first; HAIR's fields
        # are least significant bit first, so they read reversed.
        _, signals = _wig()
        decoded = SharpCommand.from_raw_timings(
            timings(signals["Sharp Power"].pronto)
        )
        assert (decoded.address, decoded.command, decoded.extension) == (
            0x01, 0x16, 1,
        )

    @pytest.mark.parametrize("code,reason", [
        ('{"Protocol":"NEC","Bits":32,"Data":"0xFFFFFFFFFFFFFFFF"}',
         "NEC repeat code"),
        ('{"Protocol":"SAMSUNG","Bits":32,"Data":"0xD0D0F0F0"}',
         "complement disagree"),
        ('{"Protocol":"PIONEER","Bits":64,"Data":"0x659A38C7659A39C6"}',
         "two different Pioneer codes"),
        ('{"Protocol":"SHARP","Bits":15,"Data":"0x41A3"}', "inverted frame"),
        ('{"Protocol":"SONY","Bits":14,"Data":"0x1"}', "SONY with 14 bits"),
        ('{"Protocol":"UNKNOWN","Bits":32,"Data":"0x8F21A3C4"}',
         "only a hash"),
        ('{"Protocol":"DAIKIN","Bits":280,"Data":"0x11"}',
         "DAIKIN has no encoder"),
    ])
    def test_refusals(self, code, reason):
        with pytest.raises(TasmotaError, match=reason):
            render(f"IRsend {code}")

    def test_an_overflowed_capture_is_refused(self):
        line = (
            '{"IrReceived":{"Protocol":"LG","Bits":28,"Data":"0x1",'
            '"RawData":"+9000-4500+560-560C-1690","RawDataInfo":[5,5,1]}}'
        )
        with pytest.raises(TasmotaError, match="overflowed"):
            render(line)


def _close(got: list[int], want: list[int]) -> bool:
    """Equal to within one Pronto period (about 26 us at 38 kHz)."""
    return len(got) >= len(want) and all(
        abs(a - b) <= 30 for a, b in zip(got, want, strict=False)
    )


class TestRawForms:
    def test_parametric_with_five_timings(self):
        code = render("IRsend raw,0,9000,4500,560,560,1690,0110")
        assert _close(
            timings(code.pronto), [9000, -4500, 560, -560, 560, -1690]
        )

    @pytest.mark.parametrize("params,durations", [
        ("889", [889, -889, 1778, -889]),
        ("889,2", [889, -889, 1778, -889]),
        ("889,1600", [889, -889, 1600, -889]),
    ])
    def test_parametric_with_one_or_two_timings(self, params, durations):
        """Every character is one duration, as the firmware sends it."""
        code = render(f"IRsend raw,0,{params},00100")
        assert _close(timings(code.pronto), durations)

    def test_three_or_four_timings_are_refused(self):
        with pytest.raises(TasmotaError, match="1, 2 or 5"):
            render("IRsend raw,0,9000,4500,560,0110")

    def test_gc_form_reads_through_sendir(self):
        code = render("IRsend gc,38000,1,1,38,19,38,19,38,19")
        assert _close(timings(code.pronto), [1000, -500, 1000, -500])


class TestPasteDoor:
    def test_paste_parity_with_the_file(self):
        _, signals = _wig()
        for name, code in _lines().items():
            if name in ("LG TV", "Climate"):
                continue
            pasted = coerce_pasted_code(code)
            assert pasted.error is None, name
            assert pasted.pronto == signals[name].pronto, name

    def test_a_console_line_pastes(self):
        line = next(
            line for line in _read(CODES).splitlines()
            if '"Protocol":"NEC"' in line and "IrReceived" in line
        )
        pasted = coerce_pasted_code(line)
        assert pasted.source == SOURCE_TASMOTA
        assert _wire(pasted.pronto) == [[0x12, 0xED, 0x10, 0xEF]]

    def test_raw_is_the_assumed_source(self):
        pasted = coerce_pasted_code(_lines()["Fan"])
        assert pasted.source == SOURCE_TASMOTA_RAW
        assert "38 kHz assumed" in CARRIER_NOTE[SOURCE_TASMOTA_RAW]

    def test_a_pretty_printed_payload_pastes(self):
        pasted = coerce_pasted_code(_read("tasmota_irsend_payload.json"))
        assert pasted.source == SOURCE_TASMOTA
        assert _wire(pasted.pronto) == [[0x12, 0xED, 0x01, 0xFE]]

    def test_repeats_are_named(self):
        pasted = coerce_pasted_code(_lines()["Mute"])
        assert pasted.notes == (
            "Tasmota sends this code 2 times; HAIR stores it once. Set the "
            "send count to match.",
        )

    def test_two_codes_are_refused(self):
        lines = _lines()
        pasted = coerce_pasted_code(lines["Power"] + "\n" + lines["Mute"])
        assert pasted.error.startswith("This paste holds 2 Tasmota codes.")

    def test_a_climate_state_is_refused_with_the_reason(self):
        pasted = coerce_pasted_code(_lines()["Climate"])
        assert pasted.error == (
            "This Tasmota code cannot be used: climate state (IRhvac), not "
            "a code."
        )

    def test_prose_is_not_a_tasmota_paste(self):
        assert coerce_pasted_code("IRsend is a command").error is None


class TestTheTie:
    """Two text formats at one rank: a file holding both is refused."""

    def test_both_text_formats_claim_it_and_it_is_refused(self):
        result = sniff(_read(AMBIGUOUS), AMBIGUOUS)
        assert result.format is None
        assert set(result.candidates) == {"globalcache", "tasmota"}
        converted = convert(_read(AMBIGUOUS), AMBIGUOUS)
        assert not converted.wigs
        assert converted.error == (
            "this file matches both globalcache and tasmota, and HAIR will "
            "not guess"
        )

    def test_a_csv_name_settles_it(self):
        result = sniff(_read(AMBIGUOUS), "codes.csv")
        assert result.format == "globalcache"

    def test_each_half_alone_is_one_format(self):
        gc, _, tas = _read(AMBIGUOUS).partition("\n\n")
        assert sniff(gc).format == "globalcache"
        assert sniff(tas).format == "tasmota"


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = "dab"
    return conn


def _wire_hass(fake_hass, tmp_path):
    (tmp_path / "hair" / "wigs").mkdir(parents=True)
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(), "fitting_manager": None, "store": None,
    }}


class TestWebsocket:
    @pytest.mark.asyncio
    async def test_the_upload_door_says_why_it_refused_a_tie(
        self, fake_hass, tmp_path
    ):
        _wire_hass(fake_hass, tmp_path)
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload", "text": _read(AMBIGUOUS),
            "filename": AMBIGUOUS,
        })
        payload = conn.send_result.call_args.args[1]
        assert payload == {
            "success": False,
            "errors": [
                "this file matches both globalcache and tasmota, and HAIR "
                "will not guess"
            ],
        }

    @pytest.mark.asyncio
    async def test_a_dropped_file_files_one_wig(self, fake_hass, tmp_path):
        _wire_hass(fake_hass, tmp_path)
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload", "text": _read(CODES),
            "filename": CODES,
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["success"], payload
        assert payload["format"] == "tasmota"
        assert len(payload["skipped"]) == 3

    @pytest.mark.asyncio
    async def test_validate_names_the_raw_source(self, fake_hass):
        conn = _conn()
        await ws_clip_validate_pronto(fake_hass, conn, {
            "id": 1, "type": "hair/clip/validate-pronto",
            "pronto": _lines()["Fan"],
        })
        payload = conn.send_result.call_args[0][1]
        assert payload["valid"] is True
        assert payload["source_format"] == SOURCE_TASMOTA_RAW
        assert payload["warnings"][0] == CARRIER_NOTE[SOURCE_TASMOTA_RAW]


def test_a_payload_without_protocol_or_timings():
    with pytest.raises(TasmotaError, match="no protocol and no raw timings"):
        render(json.dumps({"IrReceived": {"Bits": 32}}))
