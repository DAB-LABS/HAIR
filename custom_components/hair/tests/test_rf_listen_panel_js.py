"""The listening panel: where a radio receiver listens, on its Sniffer
pill (per receiver, only there); the "did not change" and "can't tune"
lines; and where a capture's frequency came from, in the row's tooltip.

The server half is test_rf_tune.py. The box's rules (what it reads, its
menu, its lines) are in test_rf_one_frequency_control_js.py; these are
source pins and strings.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
LOCALES = SRC / "locales"

KEYS = (
    "listen.tune_heading", "listen.tune_title", "listen.tune_setting", "listen.tune_refused",
    "listen.tune_band_refused", "listen.tune_range",
    "listen.tune_did_not_change", "listen.tune_cannot", "listen.src_signal",
    "listen.src_window", "listen.src_tuned", "listen.src_receiver", "listen.src_unknown",
    "listen.src_join",
)

def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


class TestWhereItLives:
    def test_on_every_radio_pill(self):
        chip = _read("ir-listen-chip.ts")
        block = chip.split("// Where a radio receiver listens", 1)[1]
        block = block.split("const lengths = lengthChoices(", 1)[0]
        assert 'if (row.medium === "rf" && this.tuning) {' in block
        assert "<ir-listen-tune" in block
        assert "?inactive=${!active}" in block

    def test_the_row_reads_the_tuning_and_again_after_a_set(self):
        row = _read("ir-listen-row.ts")
        assert "const { receivers } = await this.api.receiverTuning();" in row
        assert ".tuning=${this._tuning[row.receiver_entity_id] ?? null}" in row
        assert "@tuned=${() => void this._readTuning()}" in row

    def test_it_uses_the_shared_frequency_control(self):
        tune = _read("ir-listen-tune.ts")
        assert 'from "./rf-frequency-control.js";' in tune
        assert "<hair-frequency-control" in tune
        assert "@frequency-pick=" in tune

    def test_the_server_answers_and_nothing_guesses(self):
        tune = _read("ir-listen-tune.ts")
        assert "await this.api.receiverTune(this.receiverEntityId, pick);" in tune
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
        # A value the receiver doesn't accept is refused; nothing is
        # tried anyway any more.
        assert "listen.tune_outside" not in en
        assert en["listen.tune_refused"] == (
            "This receiver doesn't take {mhz} MHz. It takes {ranges} MHz."
        )
        assert en["listen.tune_band_refused"] == "This receiver doesn't take {mhz} MHz."
        assert en["listen.tune_range"] == "{low} to {high}"
