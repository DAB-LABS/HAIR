"""Pinned remotes in Device Settings: one menu per pin (GH #294).

The rules live in ``pin-mode.ts``, which this transpiles with the repo's
own TypeScript and runs under node, in the house pattern of
``test_speed_cycle_settings_js.py``. The dialog is a lit component node
cannot render, so its wiring is checked by reading the source.

The node half is SKIPPED when the frontend toolchain is not installed;
the source half always runs.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
SRC = FRONTEND / "src"
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

toolchain = pytest.mark.skipif(
    not TSC.exists() or shutil.which("node") is None,
    reason="frontend toolchain not installed (node_modules / node)",
)

DRIVER = """
import { pinModeChoices, pinModeOf, pinModeShown } from "./pin-mode.js";

const remote = {
    follow_only_device_ids: ["a", "b"],
    track_only_device_ids: ["b", "c"],
};
console.log(JSON.stringify({
    modes: ["a", "b", "c", "d"].map((id) => pinModeOf(remote, id)),
    bare: pinModeOf({}, "a"),
    toggle_choices: pinModeChoices(true),
    other_choices: pinModeChoices(false),
    shown: [
        pinModeShown("except_power", true),
        pinModeShown("except_power", false),
        pinModeShown("track", false),
        pinModeShown("send", false),
    ],
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("pinmodejs")
    subprocess.run(
        [
            str(TSC), "src/pin-mode.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


def _locale(lang: str) -> dict:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


@toolchain
class TestTheRules:
    def test_each_stored_pin_loads_as_its_mode(self, run):
        # Track only wins when a device is somehow in both lists.
        assert run["modes"] == ["except_power", "track", "track", "send"]
        assert run["bare"] == "send"

    def test_three_choices_on_a_toggle_device_two_on_any_other(self, run):
        assert run["toggle_choices"] == ["send", "except_power", "track"]
        assert run["other_choices"] == ["send", "track"]

    def test_leaving_out_power_reads_as_send_where_there_is_none(self, run):
        assert run["shown"] == ["except_power", "send", "track", "send"]


class TestTheDialog:
    def test_the_section_shows_on_every_device_with_a_pin(self):
        dialog = _flat("ir-device-settings-dialog.ts")
        assert "return this._pinningRemotes().length > 0;" in dialog

    def test_one_menu_per_pin_and_the_line_follows_the_choice(self):
        dialog = _flat("ir-device-settings-dialog.ts")
        assert "const choices = pinModeChoices(toggles);" in dialog
        assert '${t(`devsettings.pin_mode_${choice}`)}' in dialog
        assert '${t(`devsettings.pin_mode_${mode}_desc`)}' in dialog
        assert 'type="checkbox"' not in dialog.split("_renderRelaySection")[2].split(
            "_renderSpeedCycleSection"
        )[0]

    def test_saving_writes_each_changed_pin_after_the_device(self):
        dialog = _flat("ir-device-settings-dialog.ts")
        assert "const relayChanged = await this._savePinModes();" in dialog
        assert "await this.api.setPinMode(remote.id, this.device.id, mode);" in dialog
        assert "setPinRelay" not in dialog
        api = _flat("api.ts")
        assert 'type: "hair/trigger-remote/pin-mode",' in api
        assert "pin-relay" not in api


class TestTheWords:
    KEYS = (
        "devsettings.pin_remote_label",
        "devsettings.pin_mode_send",
        "devsettings.pin_mode_except_power",
        "devsettings.pin_mode_track",
        "devsettings.pin_mode_send_desc",
        "devsettings.pin_mode_except_power_desc",
        "devsettings.pin_mode_track_desc",
    )

    def test_the_approved_english(self):
        en = _locale("en")
        assert en["devsettings.pin_mode_send"] == "Send every press"
        assert en["devsettings.pin_mode_except_power"] == "Send every press except Power"
        assert en["devsettings.pin_mode_track"] == "Track only, send nothing"
        assert en["devsettings.pin_mode_track_desc"] == (
            "The device hears this remote itself. "
            "HAIR updates the device's state and sends nothing."
        )
        # The internal shorthand is gone from both Make cards.
        assert en["devsettings.make_remote_desc"] == "Make a Remote from this device's commands."
        assert en["devsettings.make_device_desc"] == "Make a Device from this remote's triggers."

    def test_every_locale_has_every_key_and_no_old_ones(self):
        for path in LOCALES.glob("*.json"):
            words = json.loads(path.read_text(encoding="utf-8"))
            for key in self.KEYS:
                assert words.get(key), (path.name, key)
                assert "—" not in words[key], (path.name, key)
            assert "devsettings.relay_intro" not in words, path.name
            assert "devsettings.relay_label" not in words, path.name
            assert "Matrix" not in words["devsettings.make_remote_desc"], path.name
