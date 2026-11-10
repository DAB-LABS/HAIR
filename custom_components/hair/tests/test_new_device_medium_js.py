"""The Assign dialog's New Device tab, per medium (bench, 2026-11-10).

On a radio row the tab lists radio transmitters only, yet an empty
choice was refused with "Select at least one IR emitter.", and the row
header read "38kHz" from the radio row's stored infrared default. Now a
radio row is refused with "Select at least one radio transmitter." and
shows its band; an infrared row keeps its sentence and its kHz.

The rules run under node with the repo's TypeScript (skipped without
the toolchain); the source and locale pins run everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

RF_ROW = {"medium": "rf", "rf_frequency_hz": 433_920_000, "frequency": 38_000}
IR_ROW = {"medium": "ir", "frequency": 38_000}

DRIVER = r"""
import { emitterRequiredKey, newDeviceRefusalKey } from "./assign-new-device.js";
import { carrierParts } from "./sniffer-filter.js";

const RF_ROW = __RF__;
const IR_ROW = __IR__;
const TX = ["radio_frequency.athom_rf_transmitter"];
const IR = ["infrared.den_blaster"];

console.log(JSON.stringify({
    key: [emitterRequiredKey("rf"), emitterRequiredKey("ir"), emitterRequiredKey(undefined)],
    rf: {
        none: newDeviceRefusalKey("rf", "Bench plug 2", []),
        chosen: newDeviceRefusalKey("rf", "Bench plug 2", TX),
        noName: newDeviceRefusalKey("rf", "  ", TX),
        header: carrierParts(RF_ROW),
    },
    ir: {
        none: newDeviceRefusalKey("ir", "Den TV", []),
        chosen: newDeviceRefusalKey("ir", "Den TV", IR),
        noName: newDeviceRefusalKey("ir", "", IR),
        header: carrierParts(IR_ROW),
    },
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("newdevicejs")
    subprocess.run(
        [
            str(TSC), "src/assign-new-device.ts", "src/sniffer-filter.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    driver = DRIVER.replace("__RF__", json.dumps(RF_ROW)).replace("__IR__", json.dumps(IR_ROW))
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestARadioRow:
    def test_no_transmitter_asks_for_a_radio_transmitter(self, run):
        assert run["rf"]["none"] == "assign.transmitter_required"

    def test_a_chosen_transmitter_creates(self, run):
        assert run["rf"]["chosen"] is None

    def test_the_name_is_asked_for_first(self, run):
        assert run["rf"]["noName"] == "promote.device_name_required"

    def test_the_header_shows_the_band_not_the_stored_38khz(self, run):
        assert run["rf"]["header"] == {"band": "433.92"}


class TestAnInfraredRow:
    def test_no_emitter_asks_for_an_ir_emitter(self, run):
        assert run["ir"]["none"] == "promote.emitter_required"

    def test_a_chosen_emitter_creates(self, run):
        assert run["ir"]["chosen"] is None

    def test_the_name_is_asked_for_first(self, run):
        assert run["ir"]["noName"] == "promote.device_name_required"

    def test_the_header_keeps_its_carrier(self, run):
        assert run["ir"]["header"] == {"khz": 38}


def test_a_row_with_no_medium_reads_as_infrared(run):
    assert run["key"] == [
        "assign.transmitter_required", "promote.emitter_required", "promote.emitter_required",
    ]


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


class TestTheDialog:
    def test_create_asks_by_the_rows_medium(self):
        flat = _flat("ir-assign-signal-dialog.ts")
        assert (
            "const refusal = newDeviceRefusalKey( this.signal?.medium, "
            "this._newName, this._newEmitterIds, );"
        ) in flat
        assert 't("promote.emitter_required")' not in flat

    def test_the_picker_lists_the_rows_medium(self):
        flat = _flat("ir-assign-signal-dialog.ts")
        assert '.media=${[this.signal?.medium ?? "ir"]}' in flat

    def test_the_header_reads_the_carrier_by_medium(self):
        flat = _flat("ir-assign-signal-dialog.ts")
        assert "const parts = carrierParts(this.signal);" in flat
        assert 't("listen.band", { band: parts.band })' in flat
        assert "Math.round(this.signal.frequency / 1000)" not in flat


class TestTheSentence:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["assign.transmitter_required"] == "Select at least one radio transmitter."
        assert en["promote.emitter_required"] == "Select at least one IR emitter."

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale_has_it(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        text = data.get("assign.transmitter_required", "")
        assert text and text != data["promote.emitter_required"]
