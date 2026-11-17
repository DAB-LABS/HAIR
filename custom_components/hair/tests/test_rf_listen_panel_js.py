"""Listening PR 1, the panel half: where a radio receiver listens, on its
Sniffer pill (owner, 2026-11-16 13:50 PT: in the Sniffer, on the
receiver's chip, per receiver, only there; the "did not change" and
"can't tune" lines; where a capture's frequency came from in the row's
tooltip, kept simple).

The server half is test_rf_tune.py. The rules run under node (skipped
without the toolchain); the source pins run everywhere.
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

KEYS = (
    "listen.tune_heading", "listen.tune_title", "listen.tune_setting", "listen.tune_outside",
    "listen.tune_did_not_change", "listen.tune_cannot", "listen.src_signal",
    "listen.src_window", "listen.src_tuned", "listen.src_receiver", "listen.src_unknown",
    "listen.src_join",
)

DRIVER = r"""
import { tuneLabel, outsideLimits, tuneNote } from "./rule.js";

const cc1101 = { receiver_entity_id: "r", tunable: true, number_entity: "n", available: true,
    current_mhz: 433.92, min_mhz: 300, max_mhz: 928, declared: [] };
const athom = { receiver_entity_id: "a", tunable: false, number_entity: null, available: true,
    current_mhz: null, min_mhz: null, max_mhz: null, declared: [] };
console.log(JSON.stringify({
    label: [tuneLabel(cc1101, null), tuneLabel(cc1101, 433000000), tuneLabel(athom, null),
            tuneLabel(null, null)],
    outside: [outsideLimits(cc1101, 433000000), outsideLimits(cc1101, 1000000000),
              outsideLimits(cc1101, 200000000), outsideLimits(athom, 1000000000),
              outsideLimits(null, 1)],
    note: [
        tuneNote(true, null),
        tuneNote(false, null),
        tuneNote(false, { result: "confirmed", current_mhz: 433.0 }),
        tuneNote(false, { result: "did_not_change", current_mhz: 433.92 }),
        tuneNote(false, { result: "cannot_tune", current_mhz: null }),
    ],
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("listenpanel")
    src = _read("ir-listen-tune.ts")
    rules = src[src.index("/** What the box reads:"):src.index("@customElement(")]
    head = (
        'import { hzToMhz } from "./rf-code.js";\n'
        "type ReceiverTuning = any; type ReceiverTuneResult = any;\n"
        "function t(key: string, subs?: Record<string, string>): string {\n"
        "  return subs ? key + JSON.stringify(subs) : key;\n}\n"
    )
    (out / "rule.ts").write_text(head + rules, encoding="utf-8")
    shutil.copy(SRC / "rf-code.ts", out / "rf-code.ts")
    subprocess.run(
        [
            str(TSC), str(out / "rule.ts"), str(out / "rf-code.ts"),
            "--module", "esnext", "--target", "es2022", "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheBox:
    def test_it_reads_what_the_receiver_holds_or_is_being_set_to(self, run):
        assert run["label"] == [
            "433.92",
            'listen.tune_setting{"mhz":"433"}',
            "listen.band_unknown",
            "listen.band_unknown",
        ]

    def test_outside_the_limits_is_tried_anyway(self, run):
        assert run["outside"] == [False, True, True, False, False]

    def test_the_lines(self, run):
        outside, quiet, confirmed, unchanged, cannot = run["note"]
        assert outside == {"key": "listen.tune_outside"}
        assert quiet is None and confirmed is None
        assert unchanged == {"key": "listen.tune_did_not_change", "params": {"mhz": "433.92"}}
        assert cannot == {"key": "listen.tune_cannot"}


class TestWhereItLives:
    def test_only_on_a_radio_pill_without_its_own_frequency_picker(self):
        chip = _read("ir-listen-chip.ts")
        block = chip.split("// Where a radio receiver listens (listening PR 1)", 1)[1]
        block = block.split("const lengths = lengthChoices(", 1)[0]
        assert 'if (row.medium === "rf" && freqs.length === 0 && this.tuning) {' in block
        assert "<ir-listen-tune" in block
        assert "?inactive=${!active}" in block

    def test_the_row_reads_the_tuning_and_again_after_a_set(self):
        row = _read("ir-listen-row.ts")
        assert "const { receivers } = await this.api.receiverTuning();" in row
        assert ".tuning=${this._tuning[row.receiver_entity_id] ?? null}" in row
        assert "@tuned=${() => void this._readTuning()}" in row

    def test_it_uses_the_shared_frequency_control(self):
        tune = _read("ir-listen-tune.ts")
        assert 'import "./rf-frequency-control.js";' in tune
        assert "<hair-frequency-control" in tune
        assert "void this._tune(e.detail.hz)" in tune

    def test_the_server_answers_and_nothing_guesses(self):
        tune = _read("ir-listen-tune.ts")
        assert "await this.api.receiverTune(this.receiverEntityId, hz);" in tune
        api = _read("api.ts")
        assert 'type: "hair/rf/receiver_tuning"' in api
        assert 'type: "hair/rf/receiver_tune"' in api


class TestTheRowTooltip:
    def test_each_source_has_its_phrase(self):
        monitor = _read("ir-signal-monitor.ts")
        body = monitor.split("export function carrierSourceKey(", 1)[1].split("\n}\n", 1)[0]
        for source, key in (
            ("signal", "listen.src_signal"), ("window", "listen.src_window"),
            ("tuned", "listen.src_tuned"), ("receiver", "listen.src_receiver"),
        ):
            assert f'case "{source}":\n            return "{key}";' in body
        assert 'if (!sig.rf_frequency_hz) return "listen.src_unknown";' in body

    def test_a_radio_row_with_no_band_says_so(self):
        monitor = _read("ir-signal-monitor.ts")
        assert '<span class="meta-freq" title=${carrierTitle(sig)}' in monitor
        assert '(sig.medium === "rf" ? t("listen.band_unknown") : "")' in monitor


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in KEYS:
            assert data.get(key), (path.name, key)
            assert "—" not in data[key], (path.name, key)
        assert "{mhz}" in data["listen.tune_setting"]
        assert "{mhz}" in data["listen.tune_did_not_change"]
        assert "{carrier}" in data["listen.src_join"] and "{source}" in data["listen.src_join"]

    def test_the_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.tune_did_not_change"] == (
            "This receiver did not change; it is still listening at {mhz} MHz."
        )
        assert en["listen.tune_cannot"] == (
            "HAIR can't tune this receiver; it listens where its hardware does."
        )
        assert en["listen.tune_outside"] == "Outside what this receiver supports; trying anyway."
