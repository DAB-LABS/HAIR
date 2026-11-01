"""The Candy Drawer's text layout, actually executed.

``candy-text.ts`` is the pure half of the drawer: the block a person reads
and Copy all hands over, the opened marker with its time zone, the order
blocks go in, the cap and the RX / TX filter. This transpiles it with the
repo's own TypeScript and runs it under node, the way
``test_landed_notice_js.py`` does for its helpers.

The node-driven tests are SKIPPED when the frontend toolchain is not
installed (CI runs pytest without node_modules). The source-level tests
at the bottom (the wiring, the locale keys, the fixed English labels) run
everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
SRC = FRONTEND / "src"
LOCALES = SRC / "locales"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

# 2026-10-31 19:04:31.218 UTC (still daylight time in Los Angeles).
TS = 1793473471.218

DRIVER = """
import {
    clockTime, zoneOffset, openedLine, formatBlock, echoLabel,
    insertIndex, overflow, isVisible, copyText, CANDY_CAP,
} from "./candy-text.js";

const TS = %(ts)s;
const nec = {
    ts: TS, dir: "rx", entity_id: "infrared.living_ir", name: "Living room IR",
    protocol: "NEC", address: "0x0004", command: "0x08",
    fingerprint: "NEC:0x0004:0x08", covers: true, carrier_hz: 38000,
    frames: 3, pronto: "0000 006D 0022 0000 015B 00AA",
    raw: [8990, -4480, 560, -560, 560, -1690], ditto: false,
    echo: null, echo_of: null, echo_via: null,
};
const out = {
    utc: clockTime(TS, "UTC"),
    rounding: clockTime(1793473471.818, "UTC"),
    nextSecond: clockTime(1793473471.9996, "UTC"),
    la: clockTime(TS, "America/Los_Angeles"),
    offsets: {
        utc: zoneOffset(TS, "UTC"),
        la: zoneOffset(TS, "America/Los_Angeles"),
        kolkata: zoneOffset(TS, "Asia/Kolkata"),
        kathmandu: zoneOffset(TS, "Asia/Kathmandu"),
        tokyo: zoneOffset(TS, "Asia/Tokyo"),
    },
    opened: openedLine("--- Candy Drawer opened {time} ({zone}) ---", TS, "America/Los_Angeles"),
    rx: formatBlock(nec, "UTC"),
    partial: formatBlock({ ...nec, covers: false }, "UTC"),
    nodecode: formatBlock({ ...nec, protocol: null, address: null, command: null,
                            fingerprint: null, covers: null, carrier_hz: 38029,
                            frames: 1, pronto: null }, "UTC"),
    ditto: formatBlock({ ...nec, ditto: true, protocol: null, raw: [9000, -2250, 560],
                         frames: 1 }, "UTC"),
    legacy: formatBlock({ ...nec, entity_id: null, name: "esphome.remote_received" }, "UTC"),
    tx: formatBlock({
        ts: TS, dir: "tx", seq: 4, label: "TV / Power", sends: 2, origin: "manager",
        device: "TV", command_name: "Power",
        emitters: [{ entity_id: "infrared.rm4_living", name: "RM4 living" },
                   { entity_id: "infrared.athom", name: "Athom" }],
        protocol: "NEC", address: "0x0004", command: "0x08",
        fingerprint: "NEC:0x0004:0x08", covers: null, carrier_hz: 38000,
        frames: 1, pronto: "0000 006D", raw: [8990, -4480],
    }, "UTC"),
    txOnce: formatBlock({
        ts: TS, dir: "tx", seq: 5, label: "Manual test send", sends: 1,
        emitters: [{ entity_id: "infrared.rm4_living", name: "RM4 living" }],
        protocol: null, address: null, command: null, fingerprint: null,
        covers: null, carrier_hz: 38000, frames: 1, pronto: "0000 006D", raw: [1, -2],
    }, "UTC"),
    echoes: {
        send: echoLabel({ ...nec, echo: "send", echo_of: 4 }),
        guard: echoLabel({ ...nec, echo: "guard", echo_of: 4 }),
        unseen: echoLabel({ ...nec, echo: "send", echo_of: null }),
        garbled: echoLabel({ ...nec, echo: "garbled", echo_of: 4 }),
        garbledUnseen: echoLabel({ ...nec, echo: "garbled", echo_of: null }),
        foreign: echoLabel({ ...nec, echo: "foreign", echo_via: "Tuya hub" }),
        none: echoLabel(nec),
    },
    echoBlock: formatBlock({ ...nec, echo: "send", echo_of: 4 }, "UTC"),
    insert: {
        end: insertIndex([1, 2, 3], 4),
        middle: insertIndex([1, 2, 4], 3),
        start: insertIndex([2, 3], 1),
        tie: insertIndex([1, 2, 2], 2),
    },
    overflow: [overflow(1999, 0), overflow(2000, 1), overflow(1990, 20), CANDY_CAP],
    visible: [isVisible("rx", { rx: false, tx: true }), isVisible("tx", { rx: false, tx: true })],
    copy: copyText("--- opened ---", null,
                   [{ dir: "rx", text: "A" }, { dir: "tx", text: "B" }, { dir: "rx", text: "C" }],
                   { rx: true, tx: false }),
    copyDropped: copyText("--- opened ---", "--- dropped: 3 ---",
                          [{ dir: "tx", text: "B" }], { rx: true, tx: true }),
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def text(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("candyjs")
    subprocess.run(
        [
            str(TSC), "src/candy-text.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER % {"ts": TS}, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestTime:
    def test_clock_time_has_milliseconds_in_the_zone(self, text):
        assert text["utc"] == "19:04:31.218"
        assert text["la"] == "12:04:31.218"
        # Floating point never shaves a millisecond or splits a second.
        assert text["rounding"] == "19:04:31.818"
        assert text["nextSecond"] == "19:04:32.000"

    def test_offsets(self, text):
        assert text["offsets"] == {
            "utc": "UTC", "la": "UTC-7", "kolkata": "UTC+5:30",
            "kathmandu": "UTC+5:45", "tokyo": "UTC+9",
        }

    def test_the_opened_marker_carries_its_zone(self, text):
        assert text["opened"] == "--- Candy Drawer opened 12:04:31 (UTC-7) ---"


class TestBlocks:
    def test_a_received_frame(self, text):
        assert text["rx"].split("\n") == [
            "19:04:31.218  RX  Living room IR (infrared.living_ir)",
            "NEC  address=0x0004  command=0x08  NEC:0x0004:0x08   38 kHz   3 frames",
            "Pronto: 0000 006D 0022 0000 015B 00AA",
            "Raw: 8990 -4480 560 -560 560 -1690",
        ]

    def test_a_partial_decode_says_so(self, text):
        assert text["partial"].split("\n")[1] == (
            "NEC  address=0x0004  command=0x08  NEC:0x0004:0x08   "
            "decode covers part   38 kHz   3 frames"
        )

    def test_no_decode(self, text):
        lines = text["nodecode"].split("\n")
        assert lines[1] == "no decode   38.0 kHz   1 frame"
        assert lines[2] == "Pronto: none"

    def test_a_repeat_frame_is_its_header_and_its_raw(self, text):
        assert text["ditto"].split("\n") == [
            "19:04:31.218  RX  Living room IR (infrared.living_ir)   repeat frame (ditto)",
            "Raw: 9000 -2250 560",
        ]

    def test_the_legacy_bridge_names_itself(self, text):
        assert text["legacy"].split("\n")[0] == "19:04:31.218  RX  esphome.remote_received"

    def test_a_send_names_its_emitters_and_its_count(self, text):
        assert text["tx"].split("\n")[0] == (
            "19:04:31.218  TX  RM4 living (infrared.rm4_living), "
            "Athom (infrared.athom)   TV / Power   x2 sends"
        )
        assert text["txOnce"].split("\n")[0] == (
            "19:04:31.218  TX  RM4 living (infrared.rm4_living)   Manual test send"
        )

    def test_echo_labels(self, text):
        assert text["echoes"] == {
            "send": "echo of the TX above",
            "guard": "echo of the TX above",
            "unseen": "echo of a HAIR send",
            "garbled": "echo of the TX above (garbled)",
            "garbledUnseen": "echo of a HAIR send (garbled)",
            "foreign": "echo of a send by another integration via Tuya hub",
            "none": None,
        }
        assert text["echoBlock"].split("\n")[0].endswith("   echo of the TX above")

    def test_numbers_are_separated_by_plain_single_spaces(self, text):
        """The wrap points: the dialog wraps at spaces only, so every
        number stays whole if nothing but a plain space sits between."""
        for block in (text["rx"], text["tx"], text["ditto"]):
            for line in block.split("\n"):
                if line.startswith(("Raw: ", "Pronto: ")):
                    body = line.split(": ", 1)[1]
                    assert "  " not in body
                    assert all(ch.isascii() for ch in body)
                    assert "\t" not in body and "\u00a0" not in body


class TestWindow:
    def test_blocks_go_in_by_time(self, text):
        assert text["insert"] == {"end": 3, "middle": 2, "start": 0, "tie": 3}

    def test_the_cap_counts_the_queue(self, text):
        assert text["overflow"] == [0, 1, 10, 2000]

    def test_filters_hide(self, text):
        assert text["visible"] == [False, True]

    def test_copy_all_is_what_is_shown(self, text):
        assert text["copy"] == "--- opened ---\n\nA\n\nC\n"
        assert text["copyDropped"] == "--- opened ---\n\n--- dropped: 3 ---\n\nB\n"


# --- source level, runs everywhere ------------------------------------------


KEYS = {
    "candy.title", "candy.pause", "candy.resume", "candy.queued",
    "candy.clear", "candy.copy", "candy.rx", "candy.tx",
    "candy.jump_latest", "candy.opened", "candy.capped", "candy.closed",
}


class TestSource:
    def test_every_locale_has_every_key(self):
        for path in sorted(LOCALES.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert set(data) >= KEYS, path.name
            assert data["candy.title"] == "Candy Drawer", path.name
            assert "{time}" in data["candy.opened"], path.name
            assert "{zone}" in data["candy.opened"], path.name

    def test_the_glyph_sits_in_the_title_row(self):
        mirror = (SRC / "ir-mirror.ts").read_text(encoding="utf-8")
        toolbar = mirror[mirror.index('<div class="toolbar">'):]
        toolbar = toolbar[: toolbar.index("${this._error")]
        assert 'class="candy-btn"' in toolbar
        stats = mirror[mirror.index("private _renderStats("):]
        stats = stats[: stats.index("private _renderToolbar(")]
        assert "candy" not in stats

    def test_the_drawer_is_rendered_outside_the_rows_branch(self):
        mirror = (SRC / "ir-mirror.ts").read_text(encoding="utf-8")
        render = mirror[mirror.index("    render() {"):mirror.index("private _renderStats(")]
        assert render.index("<ir-candy-drawer") > render.index("this._renderDialogs()")

    def test_the_block_labels_are_fixed_english(self):
        source = (SRC / "candy-text.ts").read_text(encoding="utf-8")
        assert "./localize" not in source
        for label in (
            "repeat frame (ditto)", "echo of the TX above", "(garbled)",
            "echo of a HAIR send", "echo of a send by another integration via",
            "decode covers part", "no decode", "Pronto: ", "Raw: ",
        ):
            assert label in source

    def test_the_drawer_batches_per_animation_frame(self):
        source = (SRC / "candy-console.ts").read_text(encoding="utf-8")
        assert "requestAnimationFrame" in source
        assert "localStorage" not in source and "sessionStorage" not in source
