"""Chip and dot colours, one home (chip and dot audit, owner 2026-11-14
19:15 PT, "Go with the recommendations").

1. Bright means picked: an unpicked dot, or one on a row with nothing to
   pick, is dull; hollow always means offline, in ember.
2. One picked green: the dialog pickers take the header rows' #43a047.
3. The signal editor's closed receiver line is bright, its menu dull;
   the state source field the same.
4. No Home Assistant object: the grey dot stays.
6. A capture device's card icon follows its Sniffer row again: grey with
   no switch, gold ready, green listening, ember offline.

The rules run under node with the repo's TypeScript (skipped without the
toolchain); the source pins run everywhere.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _block(text: str, selector: str) -> str:
    """One CSS rule's body: up to its closing brace on a line of its own,
    so a ``${...}`` inside it does not end it."""
    start = text.index(selector + " {")
    return text[start: re.compile(r"\n\s*\}").search(text, start).start()]


def _row(rx: str, switch: str | None, **kw) -> dict:
    return {
        "receiver_entity_id": rx,
        "switch_entity_id": switch,
        "software_window": False,
        "always_on": False,
        **kw,
    }


DRIVER = r"""
import { dotClass, PICKED_GREEN, HAIR_GOLD, REST_GREY, DEEP_GREEN, ONLINE_GREEN, EMBER, DULL_GRAY }
    from "./hair-colors.js";
import { cardCaptureState } from "./ir-listen-state.js";
import { cardGlyph } from "./entity-health.js";

const ROWS = __ROWS__;
const S = __STATES__;
const state = (ids) => cardCaptureState(S, ROWS, ids);
const glyph = (ids) => cardGlyph("online", state(ids));
console.log(JSON.stringify({
    dot: [dotClass(true), dotClass(false), dotClass(true, true), dotClass(false, true)],
    palette: { PICKED_GREEN, HAIR_GOLD, REST_GREY, DEEP_GREEN, ONLINE_GREEN, EMBER, DULL_GRAY },
    state: {
        ready: state(["infrared.ready_rx"]),
        none: state(["infrared.plain_rx"]),
        software: state(["radio_frequency.always"]),
        windowed: state(["radio_frequency.windowed"]),
    },
    glyph: {
        ready: glyph(["infrared.ready_rx"]),
        listening: glyph(["infrared.listening_rx"]),
        waiting: glyph(["infrared.waiting_rx"]),
        offline: glyph(["infrared.down_rx"]),
        switch_down: glyph(["infrared.switch_down_rx"]),
        none: glyph(["infrared.plain_rx"]),
        mixed: glyph(["infrared.ready_rx", "infrared.listening_rx"]),
        half_waiting: glyph(["infrared.ready_rx", "infrared.waiting_rx"]),
    },
}));
"""

ROWS = [
    _row("infrared.ready_rx", "switch.ready"),
    _row("infrared.listening_rx", "switch.listening"),
    _row("infrared.waiting_rx", None),
    _row("infrared.down_rx", "switch.down"),
    _row("infrared.switch_down_rx", "switch.gone"),
    _row("radio_frequency.always", None, software_window=True, always_on=True),
    _row("radio_frequency.windowed", None, software_window=True),
]
STATES = {
    "infrared.ready_rx": {"state": "idle", "attributes": {"capturing": False}},
    "infrared.listening_rx": {"state": "idle", "attributes": {"capturing": True}},
    "infrared.waiting_rx": {"state": "idle", "attributes": {}},
    "infrared.down_rx": {"state": "unavailable", "attributes": {}},
    "infrared.switch_down_rx": {"state": "idle", "attributes": {}},
    "infrared.plain_rx": {"state": "idle", "attributes": {}},
    "radio_frequency.always": {"state": "idle", "attributes": {}},
    "radio_frequency.windowed": {"state": "idle", "attributes": {}},
    "switch.ready": {"state": "off"},
    "switch.listening": {"state": "on"},
    "switch.down": {"state": "off"},
    "switch.gone": {"state": "unavailable"},
}


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("chipcolors")
    subprocess.run(
        [
            str(TSC), "src/hair-colors.ts", "src/ir-listen-state.ts", "src/entity-health.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule", "--skipLibCheck",
            "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    driver = DRIVER.replace("__ROWS__", json.dumps(ROWS)).replace(
        "__STATES__", json.dumps(STATES)
    )
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestThePalette:
    def test_one_value_per_meaning(self, run):
        assert run["palette"] == {
            "PICKED_GREEN": "#43a047",
            "HAIR_GOLD": "#f5a623",
            "REST_GREY": "#4d5359",
            "DEEP_GREEN": "#2e7d32",
            "ONLINE_GREEN": "#6cbf78",
            "EMBER": "#e65100",
            "DULL_GRAY": "#7a7f85",
        }

    def test_every_value_is_a_token_on_the_panel_host(self):
        styles = _read("ir-header-chip-styles.ts")
        tokens = styles.split("export const hairTokens = css`", 1)[1].split("`;", 1)[0]
        for prop, name in (
            ("--hair-picked", "PICKED_GREEN"),
            ("--hair-gold", "HAIR_GOLD"),
            ("--hair-grey", "REST_GREY"),
            ("--hair-deep-green", "DEEP_GREEN"),
            ("--hair-dull-gray", "DULL_GRAY"),
        ):
            assert f"{prop}: ${{unsafeCSS({name})}};" in tokens, prop

    def test_the_old_names_read_the_palette(self):
        origin = _read("ir-origin-colors.ts")
        assert "export const GREEN_PEAK = PICKED_GREEN;" in origin
        assert "remote: HAIR_GOLD," in origin


class TestTheDotRule:
    def test_dull_unless_bright(self, run):
        assert run["dot"] == ["online", "offline", "online bright", "offline bright"]

    def test_bright_is_full_colour_without_a_glow(self):
        styles = _read("ir-header-chip-styles.ts")
        health = styles.split("export const healthDotStyles = css`", 1)[1].split("`;", 1)[0]
        assert "background: ${ONLINE_VAR};" in _block(health, ".dot.bright.online")
        assert "border-color: ${EMBER_VAR};" in _block(health, ".dot.bright.offline")
        assert "box-shadow" not in _block(health, ".dot.bright.online")
        # Unpicked stays dull, offline stays a ring (82be226, kept).
        assert "background: ${ONLINE_DULL};" in _block(health, ".dot.online")
        assert "background: transparent;" in _block(health, ".dot.offline")

    def test_the_closed_lines_are_bright_the_lists_dull(self):
        editor = _read("ir-signal-editor.ts")
        assert "${this._rxDot(current.entityId, true)}" in editor
        assert "${this._rxDot(c.entityId)}" in editor
        settings = _read("ir-device-settings-dialog.ts")
        assert "this._renderSourceDot(id, true)" in settings
        assert "this._renderSourceDot(entityId)" in settings

    def test_the_readout_dot_is_the_online_green(self):
        settings = _read("ir-device-settings-dialog.ts")
        assert "background: ${ONLINE_VAR};" in _block(settings, ".readout-live")
        assert "#66bb6a" not in settings


class TestOnePickerChip:
    @pytest.mark.parametrize(
        ("name", "chip"),
        [
            ("ir-emitter-picker.ts", 'class="pchip em ${cls}'),
            ("ir-receiver-picker.ts", 'class="pchip rx ${cls}"'),
        ],
    )
    def test_both_pickers_wear_it(self, name, chip):
        text = _read(name)
        assert chip in text
        assert "static styles = [pickerChipStyles, css`" in text
        assert "`, healthDotStyles];" in text
        # Their own copies are gone, and with them the old picked green.
        assert "rgba(79, 158, 90" not in text
        assert ".em {" not in text and ".rx {" not in text

    def test_the_picked_green_is_the_header_rows(self):
        styles = _read("ir-header-chip-styles.ts")
        chip = styles.split("export const pickerChipStyles = css`", 1)[1].split("`;", 1)[0]
        on = _block(chip, ".pchip.on")
        # The header row's picked chip exactly: full edge, 14% wash.
        assert "border-color: ${PICKED_VAR};" in on
        assert "background: color-mix(in srgb, ${PICKED_VAR} 14%, transparent);" in on
        header = _block(styles, ".chip.on")
        assert "border-color: var(--tone);" in header
        assert "background: color-mix(in srgb, var(--tone) 14%, transparent);" in header
        assert "outline: 2px solid #4dabf7;" in _block(chip, ".pchip:focus-visible")
        assert "background: ${GREY_VAR};" in _block(chip, ".pchip .dot")

    def test_no_hass_keeps_the_grey_dot(self):
        picker = _read("ir-receiver-picker.ts")
        assert "const health = this.hass !== undefined;" in picker
        assert '<span class="dot ${health ? healthDotClass(online) : ""}"></span>' in picker


class TestTheCaptureCard:
    def test_the_states(self, run):
        g = run["glyph"]
        assert g["ready"] == "ready"
        assert g["listening"] == "listening"
        assert g["waiting"] == "waiting"
        assert g["offline"] == "offline"
        assert g["switch_down"] == "offline"
        assert g["none"] == "online"

    def test_several_on_one_card(self, run):
        assert run["glyph"]["mixed"] == "listening"
        assert run["glyph"]["half_waiting"] == "ready"

    def test_only_capture_devices_count(self, run):
        assert run["state"]["none"] is None
        assert run["state"]["software"] is None
        # A software window is HAIR's, not a capture device's: no gold.
        assert run["state"]["windowed"] is None
        assert run["state"]["ready"] == {"online": True, "listening": False, "waiting": False}
