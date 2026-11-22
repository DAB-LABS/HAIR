"""A capture receiver's own badge on the Devices page takes its Sniffer
pill's colour.

Before, each Receivers row's badge carried health only, so an RM4 Pro's
card icon was gold while its ``IR-RX`` and ``RF-RX`` badges were green.
Now a capture receiver's badge is grey with no switch, gold ready and
green listening, per row, so the two windows of one device read on
their own. Unavailable stays ember, by health. An always-on receiver
and every transmitter keep the health colours.

The rule runs under node with the repo's TypeScript (skipped without
the toolchain); the source, CSS and string pins run everywhere.
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
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_read(name).split())


def _block(text: str, selector: str) -> str:
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
import { badgeCaptureState, cardCaptureState } from "./ir-listen-state.js";
const ROWS = __ROWS__;
const S = __STATES__;
const b = (id) => badgeCaptureState(S, ROWS, id);
// One device with an infrared and a radio receiver, each with its own
// capture switch: [infrared window open, radio window open].
const PRO = ["infrared.pro_ir", "radio_frequency.pro_rf"];
const RM4 = {
    closed: [false, false], ir_open: [true, false], rf_open: [false, true], both: [true, true],
};
console.log(JSON.stringify({
    ready: b("infrared.rm4_ir"),
    listening: b("radio_frequency.rm4_rf"),
    waiting: b("infrared.no_switch"),
    offline: b("infrared.down"),
    switch_down: b("infrared.switch_down"),
    software: b("radio_frequency.software"),
    always_on: b("infrared.always_on"),
    unknown: b("infrared.not_listed"),
    card: cardCaptureState(S, ROWS, ["infrared.rm4_ir", "radio_frequency.rm4_rf"]),
    rm4: Object.fromEntries(Object.entries(RM4).map(([k, ir_rf]) => {
        const s = { ...S,
            "infrared.pro_ir": { state: "idle", attributes: { capturing: ir_rf[0] } },
            "radio_frequency.pro_rf": { state: "idle", attributes: { capturing: ir_rf[1] } } };
        return [k, { ir: badgeCaptureState(s, ROWS, "infrared.pro_ir"),
                     rf: badgeCaptureState(s, ROWS, "radio_frequency.pro_rf"),
                     icon: cardCaptureState(s, ROWS, PRO) }];
    })),
}));
"""

ROWS = [
    _row("infrared.rm4_ir", "switch.rm4_ir"),
    _row("radio_frequency.rm4_rf", "switch.rm4_rf"),
    _row("infrared.no_switch", None),
    _row("infrared.down", "switch.down"),
    _row("infrared.switch_down", "switch.gone"),
    _row("radio_frequency.software", None, software_window=True),
    _row("infrared.always_on", None, always_on=True),
    _row("infrared.pro_ir", "switch.pro_ir"),
    _row("radio_frequency.pro_rf", "switch.pro_rf"),
]
STATES = {
    "infrared.rm4_ir": {"state": "idle", "attributes": {"capturing": False}},
    "radio_frequency.rm4_rf": {"state": "idle", "attributes": {"capturing": True}},
    "infrared.no_switch": {"state": "idle", "attributes": {}},
    "infrared.down": {"state": "unavailable", "attributes": {}},
    "infrared.switch_down": {"state": "idle", "attributes": {}},
    "radio_frequency.software": {"state": "idle", "attributes": {"capturing": True}},
    "infrared.always_on": {"state": "idle", "attributes": {}},
    "switch.rm4_ir": {"state": "off"},
    "switch.rm4_rf": {"state": "on"},
    "switch.down": {"state": "off"},
    "switch.gone": {"state": "unavailable"},
    "switch.pro_ir": {"state": "off"},
    "switch.pro_rf": {"state": "off"},
}


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("capturebadge")
    subprocess.run(
        [
            str(TSC), "src/ir-listen-state.ts",
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


class TestTheRule:
    def test_each_receiver_reads_its_own_window(self, run):
        # One RM4 Pro: its infrared window closed, its radio window open.
        assert run["ready"] == "ready"
        assert run["listening"] == "listening"

    def test_no_switch_is_grey_and_down_is_offline(self, run):
        assert run["waiting"] == "waiting"
        assert run["offline"] == "offline"
        assert run["switch_down"] == "offline"

    def test_only_a_pressed_capture_device_gets_a_state(self, run):
        assert run["software"] is None
        assert run["always_on"] is None
        assert run["unknown"] is None

    def test_one_device_two_windows(self, run):
        """An RM4 Pro: each badge follows only its own receiver's window."""
        rm4 = run["rm4"]
        assert (rm4["closed"]["ir"], rm4["closed"]["rf"]) == ("ready", "ready")
        assert (rm4["rf_open"]["ir"], rm4["rf_open"]["rf"]) == ("ready", "listening")
        assert (rm4["ir_open"]["ir"], rm4["ir_open"]["rf"]) == ("listening", "ready")
        assert (rm4["both"]["ir"], rm4["both"]["rf"]) == ("listening", "listening")

    def test_the_card_icon_listens_when_either_window_is_open(self, run):
        rm4 = run["rm4"]
        assert rm4["closed"]["icon"]["listening"] is False
        for case in ("rf_open", "ir_open", "both"):
            assert rm4[case]["icon"]["listening"] is True, case

    def test_the_card_icon_is_unchanged(self, run):
        assert run["card"] == {"online": True, "listening": True, "waiting": False}


class TestTheSource:
    def test_both_pick_their_rows_in_one_place(self):
        state = _flat("ir-listen-state.ts")
        card = state.split("export function cardCaptureState(", 1)[1].split("export ", 1)[0]
        assert "const mine = captureRowsFor(rows, receiverIds);" in card
        badge = state.split("export function badgeCaptureState(", 1)[1]
        assert "captureRowsFor(rows, [receiverId])[0];" in badge

    def test_the_row_reads_it_only_for_an_available_capture_receiver(self):
        text = _flat("ir-device-list.ts")
        row = text.split("private _renderCapabilityRow(", 1)[1].split("private ", 1)[0]
        assert (
            'row.capture_device && row.direction === "rx" && row.available '
            "? badgeCaptureState(this.hass?.states, this._listenRows, row.entity_id) : null;"
        ) in row
        assert 'const look = capture === "offline" ? null : capture;' in row
        assert "this._badgeTitle(row, look)" in row

    def test_the_hover_says_the_state(self):
        text = _flat("ir-device-list.ts")
        title = text.split("private _badgeTitle(", 1)[1].split("private ", 1)[0]
        assert "return look ? `${base}. ${t(`hw.badge.capture_${look}`)}` : base;" in title


class TestTheColours:
    CSS = _read("ir-device-list.ts")

    def test_gold_ready_infrared_solid_radio_wash(self):
        solid = _block(self.CSS, ".badge.cap-badge.capture-ready:not(.rf)")
        assert "background: ${GOLD_VAR};" in solid
        wash = _block(self.CSS, ".badge.cap-badge.capture-ready.rf")
        assert "color-mix(in srgb, ${GOLD_VAR} 16%, transparent)" in wash
        # Darker gold letters on a light card, so they read on white.
        assert "color: color-mix(in srgb, ${GOLD_VAR} 60%, #000);" in wash
        dark = _block(self.CSS, ":host([dark]) .badge.cap-badge.capture-ready.rf")
        assert "color: ${GOLD_VAR};" in dark

    def test_grey_with_no_switch(self):
        solid = _block(self.CSS, ".badge.cap-badge.capture-waiting:not(.rf)")
        assert "background: ${GREY_VAR};" in solid
        assert ".badge.cap-badge.capture-waiting.rf {" in self.CSS
        assert ":host([dark]) .badge.cap-badge.capture-waiting.rf {" in self.CSS

    def test_listening_keeps_the_health_green(self):
        assert "capture-listening" not in self.CSS

    def test_no_new_hex(self):
        start = self.CSS.index(".badge.cap-badge.capture-ready:not(.rf) {")
        end = self.CSS.index(":host([dark]) .badge.cap-badge.capture-waiting.rf {")
        body = self.CSS[start:end + 400]
        assert set(re.findall(r"#[0-9a-fA-F]{3,6}\b", body)) <= {"#000", "#fff"}


class TestTheStrings:
    KEYS = ("hw.badge.capture_ready", "hw.badge.capture_listening", "hw.badge.capture_waiting")

    def test_every_locale_has_them(self):
        for path in sorted(LOCALES.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in self.KEYS:
                assert data.get(key), f"{path.name}: {key}"

    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["hw.badge.capture_ready"] == (
            "Ready: open its window from its pill in the Sniffer."
        )
        assert en["hw.badge.capture_listening"] == "Listening now."
        # The pill's own words for the same state.
        assert en["hw.badge.capture_waiting"] == en["listen.no_switch_title"]
