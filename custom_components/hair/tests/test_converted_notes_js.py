"""A converted paste keeps its conversion notes on screen.

The editor validates a converted code twice: once as pasted, when the
server reads it into Pronto and answers with the carrier note and any
notes the conversion asks to be said (a Tasmota or Global Cache repeat
count), and once as the Pronto it put in the box. The second answer
carries only the validator's warnings, so ``_validate`` puts the first
answer's notes back in front of them with ``keepConversionNotes``
(``converted-notes.ts``).

The answers fed to the helper here are the validate door's own, for
real pastes. The helper is transpiled with the repo's TypeScript and
run under node, the way ``test_landed_notice_js.py`` runs its helpers.
The node-driven tests are SKIPPED when the frontend toolchain is not
installed (CI runs pytest without node_modules); the source-level tests
at the bottom run everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.hair.pasted_code import CARRIER_NOTE
from custom_components.hair.websocket_api import ws_clip_validate_pronto

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
SRC = FRONTEND / "src"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = """
import { keepConversionNotes } from "./converted-notes.js";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const pairs = JSON.parse(input);
console.log(JSON.stringify(pairs.map(([first, second]) => keepConversionNotes(first, second))));
"""

TASMOTA_REPEAT = 'IRsend {"Protocol":"NEC","Bits":32,"Data":"0x20DF10EF","Repeat":2}'
SENDIR_REPEAT = "sendir,1:1,1,38000,3,1,341,170,21,21,21,64,21,1517"


@pytest.fixture(scope="module")
def keep(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("convertednotesjs")
    subprocess.run(
        [
            str(TSC), "src/converted-notes.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")

    def run(*pairs):
        result = subprocess.run(
            ["node", str(out / "driver.mjs")],
            input=json.dumps(pairs), check=True, capture_output=True,
            text=True, timeout=60,
        )
        return json.loads(result.stdout)

    return run


async def _answer(hass, text):
    conn = MagicMock()
    await ws_clip_validate_pronto(
        hass, conn, {"id": 1, "type": "hair/clip/validate-pronto", "pronto": text},
    )
    return conn.send_result.call_args[0][1]


async def _both(hass, text):
    """The editor's two answers: the paste as pasted, then its Pronto."""
    first = await _answer(hass, text)
    assert first["valid"] is True and first.get("source_format")
    second = await _answer(hass, first["normalized"])
    assert "source_format" not in second
    return first, second


class TestRepeatNotes:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("text,source,needle", [
        (TASMOTA_REPEAT, "tasmota", "Tasmota sends this code 3 times"),
        (SENDIR_REPEAT, "globalcache", "Global Cache sent this code 3 times"),
    ], ids=["tasmota", "globalcache"])
    async def test_the_repeat_note_survives_the_second_validation(
        self, fake_hass, keep, text, source, needle,
    ):
        first, second = await _both(fake_hass, text)
        assert first["source_format"] == source
        assert first["warnings"][0] == CARRIER_NOTE[source]
        note = next(w for w in first["warnings"] if w.startswith(needle))
        # Without the fix, the second answer is what the editor shows.
        assert note not in second["warnings"]
        (shown,) = keep((first["warnings"], second["warnings"]))
        assert shown[0] == note
        assert CARRIER_NOTE[source] not in shown
        assert shown[len(shown) - len(second["warnings"]):] == second["warnings"]

    @pytest.mark.asyncio
    async def test_a_conversion_with_no_notes_shows_the_second_answer(self, fake_hass, keep):
        from .test_paste_base64 import BROADLINK_CODE

        first, second = await _both(fake_hass, BROADLINK_CODE)
        (shown,) = keep((first["warnings"], second["warnings"]))
        assert shown == second["warnings"]


class TestHelper:
    def test_order_and_no_repeats(self, keep):
        assert keep(
            (["carrier", "note A", "note B", "warn"], ["warn"]),
            (["carrier"], ["warn 1", "warn 2"]),
            (["carrier", "note"], []),
            ([], ["warn"]),
        ) == [
            ["note A", "note B", "warn"],
            ["warn 1", "warn 2"],
            ["note"],
            ["warn"],
        ]


class TestEditorSource:
    SRC = (SRC / "ir-signal-editor.ts").read_text()

    def test_validate_keeps_the_notes_after_the_second_call(self):
        start = self.SRC.index("private async _validate(")
        body = self.SRC[start:self.SRC.index("\n    }\n", start)]
        inner = body.index("await this._validate();")
        kept = body.index("keepConversionNotes(v.warnings, again.warnings)")
        assert inner < kept
        assert "again.normalized === v.normalized" in body
        assert "this._pronto === v.normalized" in body

    def test_the_helper_is_used_only_in_validate(self):
        assert self.SRC.count("keepConversionNotes(") == 1
        for path in SRC.glob("*.ts"):
            if path.name in ("converted-notes.ts", "ir-signal-editor.ts"):
                continue
            assert "keepConversionNotes" not in path.read_text(), path.name
