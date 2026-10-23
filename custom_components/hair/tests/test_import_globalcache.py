"""Global Cache: Control Tower code sets in the Closet, sendir in the paste box.

The fixtures under fixtures/adapters/globalcache_* have the shape of
the Control Tower mail bodies: the code-set CSV with its quoted cells and
empty code2 columns, the single-code email's labelled lines, and a
pasted copy's curly quotes with text around the rows. Their codes are
NEC frames from HAIR's own encoder written as carrier counts the way
Global Cache writes them, so every test knows the bytes that must reach
the wire.
"""
from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.pasted_code import (
    CARRIER_NOTE,
    SOURCE_GLOBALCACHE,
    coerce_pasted_code,
)
from custom_components.hair.sendir import (
    MAX_PAIRS,
    SendirError,
    parse_sendir,
    parse_sendir_body,
)
from custom_components.hair.tests.wire_bits import first_frame_bytes
from custom_components.hair.websocket_api import (
    ws_clip_validate_pronto,
    ws_wigs_upload,
)
from custom_components.hair.wig_adapters import _gc_hex, convert, sniff

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"
CSV_FILE = "globalcache_codeset.csv"
PASTED = "globalcache_codeset_curly_quotes.txt"
EMAIL = "globalcache_single_code_email.txt"

#: alias -> NEC command byte, address 0x20, as the generator wrote them.
COMMANDS = {
    "Power": 0x01, "Volume Up": 0x02, "Volume Down": 0x03, "Mute": 0x04,
    "Channel Up": 0x05, "Channel Down": 0x06, "Digit 1": 0x11,
    "Digit 2": 0x12, "Guide": 0x20, "Menu Main": 0x21,
}


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _rows() -> list[dict[str, str]]:
    return list(csv.DictReader(_read(CSV_FILE).splitlines()))


def _signals(name: str) -> dict[str, str]:
    result = convert(_read(name), name)
    return {s.alias: s.pronto for w in result.wigs for s in w.signals}


def _words(pronto: str) -> list[int]:
    return [int(w, 16) for w in pronto.split()]


class TestSendirParser:
    def test_counts_become_microseconds_at_the_codes_own_carrier(self):
        """MUTATION CHECK: counts are carrier periods, not microseconds.

        38 periods of a 38 kHz carrier is 1 ms; the same 38 at 40 kHz is
        950 us. A reader that took counts as microseconds, or divided the
        wrong way, fails both lines.
        """
        assert parse_sendir("sendir,1:1,1,38000,1,1,38,19").timings() == [
            1000, -500,
        ]
        assert parse_sendir("sendir,1:1,1,40000,1,1,38,19").timings() == [
            950, -475,
        ]

    def test_the_pronto_carries_the_declared_carrier(self):
        code = parse_sendir("sendir,1:1,1,40000,1,1,40,20,40,800")
        assert round(ProntoCommand(code.pronto()).modulation / 1000) == 40

    def test_the_compressed_form_is_the_same_code(self):
        # Global Cache's own example (iTach API 1.5, section 5.4.6).
        plain = parse_sendir("sendir,1:2,2445,40000,1,1,4,5,4,5,8,9,4,5,8,9,8,9")
        packed = parse_sendir("sendir,1:2,2445,40000,1,1,4,5A8,9ABB")
        assert packed.counts == plain.counts

    def test_only_fifteen_letters_are_assigned(self):
        pairs = [(10 + i, 20 + i) for i in range(16)]
        body = ",".join(f"{a},{b}" for a, b in pairs)
        code = parse_sendir(f"sendir,1:1,1,38000,1,1,{body}O")
        assert code.counts[-2:] == pairs[14]
        with pytest.raises(SendirError, match="has not given yet"):
            parse_sendir("sendir,1:1,1,38000,1,1,4,5B")

    def test_the_pair_limit_receipts_rather_than_truncates(self):
        assert MAX_PAIRS == 259
        ok = ",".join(["20,20"] * 259)
        assert parse_sendir(f"sendir,1:1,1,38000,1,1,{ok}").pairs == 259
        over = ",".join(["20,20"] * 260)
        with pytest.raises(SendirError) as raised:
            parse_sendir(f"sendir,1:1,1,38000,1,1,{over}")
        assert str(raised.value) == (
            "too long for sendir (260 pairs, the limit is 259)"
        )

    @pytest.mark.parametrize("code,reason", [
        ("sendir,1:1,1,38000,1,1,20,20,20", "odd number of on/off values"),
        ("sendir,1:1,1,38000,1,1,20,0", "a count of 0 is not valid"),
        ("sendir,1:1,1,14000,1,1,20,20", "outside 15000-500000 Hz"),
        ("sendir,1:1,1,38000,1,2,20,20", "not an odd number"),
        ("sendir,1:1,1,38000,1,5,20,20", "points past the last"),
        ("sendir,1:1,1,38000,0,1,20,20", "a repeat of 0 sends nothing"),
        ("sendir,1:1,1,38000,1,1,20,A", "interrupts an on/off pair"),
        ("sendir,1:1,1,38000,1,1", "no on/off counts"),
        ("sendir,1,1,38000,1,1,20,20", "not module:port"),
        ("sendir,1:1,1,38000,1,1,20,70000", "above 65535"),
    ])
    def test_codes_the_hardware_refuses_are_refused_with_the_reason(
        self, code, reason
    ):
        with pytest.raises(SendirError, match=reason):
            parse_sendir(code)

    def test_the_body_alone_is_the_tasmota_gc_form(self):
        assert parse_sendir_body("38000,1,1,38,19").timings() == [1000, -500]


class TestCodeSetFile:
    def test_sniffs_and_the_csv_extension_names_it(self):
        assert sniff(_read(CSV_FILE), CSV_FILE).format == "globalcache"
        assert sniff(_read(PASTED), PASTED).format == "globalcache"
        assert sniff(_read(EMAIL), EMAIL).format == "globalcache"

    def test_an_unrelated_csv_is_not_claimed(self):
        assert sniff("name,code\nPower,1234\n", "x.csv").format is None

    def test_every_row_lands_or_is_receipted(self):
        result = convert(_read(CSV_FILE), CSV_FILE)
        assert result.error is None
        wig = result.wigs[0]
        assert wig.name == "Globalcache Codeset"
        assert wig.origin == "converted:globalcache"
        assert sorted(s.alias for s in wig.signals) == sorted(COMMANDS)
        assert result.skipped == [
            "Power: a second code (code2) was not imported; HAIR keeps "
            "one code per button",
            "Menu Main: the sendir code is unusable (an odd number of "
            "on/off values); used the Pronto from the same row",
            "Too Long: too long for sendir (261 pairs, the limit is 259)",
        ]
        assert result.folds == [
            "Guide: Global Cache sent this 3 times; HAIR stores it once "
            "(set the send count to match)",
        ]
        assert {s.send_count for s in wig.signals} == {1}

    def test_the_codes_on_the_wire_are_the_files(self):
        for alias, pronto in _signals(CSV_FILE).items():
            command = COMMANDS[alias]
            assert first_frame_bytes(pronto) == [
                0x20, 0xDF, command, command ^ 0xFF,
            ], alias

    def test_conversion_matches_global_caches_own_pronto(self):
        """Every duration within 0.1% of the hexcode1 Global Cache wrote.

        Global Cache writes its counts straight into the Pronto words at
        its 0x6D period; HAIR converts through microseconds at the
        declared 38 kHz, so the two may differ by a unit on a long gap.
        """
        converted = _signals(CSV_FILE)
        for row in _rows():
            alias = row["function"].title()
            if alias not in converted or not row["hexcode1"]:
                continue
            mine = _words(converted[alias])[4:]
            theirs = _words(row["hexcode1"])[4:]
            assert len(mine) == len(theirs), alias
            for a, b in zip(mine, theirs, strict=True):
                assert abs(a - b) <= max(1, b * 0.001), (alias, a, b)

    def test_a_damaged_sendir_falls_back_to_the_rows_pronto(self):
        row = next(r for r in _rows() if r["function"] == "MENU MAIN")
        assert _signals(CSV_FILE)["Menu Main"] == row["hexcode1"]

    def test_carrier_is_declared(self):
        wig = convert(_read(CSV_FILE), CSV_FILE).wigs[0]
        assert {
            (s.extra["carrier"]["hz"], s.extra["carrier"]["source"])
            for s in wig.signals
        } == {(38029, "declared")}

    def test_a_pasted_copy_reads_as_the_same_codes(self):
        """Curly quotes, a spaced header and text around the rows."""
        straight = _signals(CSV_FILE)
        pasted = convert(_read(PASTED), PASTED)
        assert pasted.skipped == []
        got = {s.alias: s.pronto for s in pasted.wigs[0].signals}
        assert got == {alias: straight[alias] for alias in got}
        assert len(got) == 4

    def test_a_hexcode_that_lost_its_spaces_is_split_back(self):
        assert _gc_hex("0000 006D 0002 0000 00150015 0015 05EF") == (
            "0000 006D 0002 0000 0015 0015 0015 05EF"
        )
        assert _gc_hex("0000 006D 0002 0000 0015 0015 0015") is None

    def test_the_single_code_email(self):
        result = convert(_read(EMAIL), EMAIL)
        wig = result.wigs[0]
        assert [s.alias for s in wig.signals] == ["Power"]
        assert wig.notes == (
            "Imported from a Global Cache code set (Control Tower code set "
            "9901)."
        )
        assert wig.signals[0].pronto == _signals(CSV_FILE)["Power"]

    def test_bare_sendir_lines(self):
        rows = _rows()
        text = "\n".join(r["code1"] for r in rows[:3]) + "\n"
        result = convert(text, "codes.txt")
        assert [s.alias for s in result.wigs[0].signals] == [
            "Signal 1", "Signal 2", "Signal 3",
        ]

    def test_a_file_with_nothing_usable_is_refused(self):
        text = (
            "function,code1,hexcode1,code2,hexcode2\n"
            '"POWER","sendir,1:1,1,38000,1,1,20,20,20,20,20",,,\n'
        )
        result = convert(text, "x.csv")
        assert not result.wigs
        assert "no convertible codes" in result.error
        assert "odd number" in result.error


class TestPasteDoor:
    def test_paste_parity_with_the_file(self):
        """A code pasted alone is the code the file gives."""
        converted = _signals(CSV_FILE)
        for row in _rows():
            alias = row["function"].title()
            if alias in ("Menu Main", "Too Long"):
                continue
            pasted = coerce_pasted_code(row["code1"])
            assert pasted.source == SOURCE_GLOBALCACHE, alias
            assert pasted.pronto == converted[alias], alias

    def test_the_whole_email_pastes_as_its_one_code(self):
        pasted = coerce_pasted_code(_read(EMAIL))
        assert pasted.source == SOURCE_GLOBALCACHE
        assert pasted.pronto == _signals(CSV_FILE)["Power"]

    def test_a_repeat_is_named(self):
        row = next(r for r in _rows() if r["function"] == "GUIDE")
        pasted = coerce_pasted_code(row["code1"])
        assert pasted.notes == (
            "Global Cache sent this code 3 times; HAIR stores it once. Set "
            "the send count to match.",
        )

    def test_two_codes_are_refused(self):
        rows = _rows()
        pasted = coerce_pasted_code(rows[0]["code1"] + "\n" + rows[1]["code1"])
        assert pasted.error.startswith(
            "This paste holds 2 Global Cache sendir codes."
        )

    def test_an_unusable_code_is_refused_with_the_reason(self):
        pasted = coerce_pasted_code("sendir,1:1,1,38000,1,1,20,20,20")
        assert pasted.source is None
        assert pasted.error == (
            "This Global Cache code cannot be used: an odd number of on/off "
            "values."
        )

    def test_prose_is_not_a_sendir_paste(self):
        assert coerce_pasted_code("send sendir,1:1 later").source is None


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = "dab"
    return conn


class TestWebsocket:
    @pytest.mark.asyncio
    async def test_validate_names_the_source_and_the_repeat(self, fake_hass):
        row = next(r for r in _rows() if r["function"] == "GUIDE")
        conn = _conn()
        await ws_clip_validate_pronto(fake_hass, conn, {
            "id": 1, "type": "hair/clip/validate-pronto", "pronto": row["code1"],
        })
        payload = conn.send_result.call_args[0][1]
        assert payload["valid"] is True
        assert payload["source_format"] == SOURCE_GLOBALCACHE
        assert payload["warnings"][:2] == [
            CARRIER_NOTE[SOURCE_GLOBALCACHE],
            "Global Cache sent this code 3 times; HAIR stores it once. Set "
            "the send count to match.",
        ]

    @pytest.mark.asyncio
    async def test_a_dropped_code_set_files_one_wig(self, fake_hass, tmp_path):
        (tmp_path / "hair" / "wigs").mkdir(parents=True)
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": MagicMock(), "fitting_manager": None,
            "store": None,
        }}
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload", "text": _read(CSV_FILE),
            "filename": CSV_FILE,
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["success"], payload
        assert payload["format"] == "globalcache"
        assert len(payload["filenames"]) == 1
        assert len(payload["skipped"]) == 3
        assert len(payload["folds"]) == 1
