"""The device editor's speed-cycle section (GH Discussion #201).

A fan with a Speed Cycle command mapped gets a section in its settings
dialog: the number of speeds, whether off is one of the steps, where
turning it on lands, and one line saying the speed is HAIR's own count
and can drift. The rules live in ``speed-cycle-settings.ts``, which
this transpiles with the repo's own TypeScript and runs under node, in
the house pattern of ``test_entity_health_js.py``. The dialog is a lit
component node cannot render, so its wiring is checked by reading the
source.

The node half is SKIPPED when the frontend toolchain is not installed;
the source half always runs.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

toolchain = pytest.mark.skipif(
    not TSC.exists() or shutil.which("node") is None,
    reason="frontend toolchain not installed (node_modules / node)",
)

DRIVER = """
import {
    MAX_SPEED_STEPS, MIN_SPEED_STEPS, hasSpeedCycle, speedStepsForSave,
} from "./speed-cycle-settings.js";

const fan = (mapping) => ({
    device_type: "fan", entity_config: { platform: "fan", command_mapping: mapping },
});
const sections = {
    mapped: hasSpeedCycle(fan({ speed_cycle: "Speed Cycle" })),
    unmapped: hasSpeedCycle(fan({ speed_up: "Faster" })),
    empty_mapping: hasSpeedCycle(fan({ speed_cycle: "" })),
    no_config: hasSpeedCycle({ device_type: "fan" }),
    not_a_fan: hasSpeedCycle({
        device_type: "light",
        entity_config: { platform: "light", command_mapping: { speed_cycle: "X" } },
    }),
};
const saves = {};
for (const raw of ["", "  ", "1", "2", "3", " 4 ", "10", "11", "2.5", "x", "-3"]) {
    const value = speedStepsForSave(raw);
    saves[raw] = Number.isNaN(value) ? "refused" : value;
}
console.log(JSON.stringify({
    sections, saves, range: [MIN_SPEED_STEPS, MAX_SPEED_STEPS],
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("speedcyclejs")
    subprocess.run(
        [
            str(TSC), "src/speed-cycle-settings.ts",
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


def _dialog() -> str:
    return (SRC / "ir-device-settings-dialog.ts").read_text(encoding="utf-8")


@toolchain
class TestTheRules:
    def test_only_a_fan_with_the_key_mapped_gets_the_section(self, run):
        assert run["sections"] == {
            "mapped": True,
            "unmapped": False,
            "empty_mapping": False,
            "no_config": False,
            "not_a_fan": False,
        }

    def test_the_range_matches_the_backend(self, run):
        from custom_components.hair.models import (
            FAN_SPEED_STEPS_MAX,
            FAN_SPEED_STEPS_MIN,
        )

        assert run["range"] == [FAN_SPEED_STEPS_MIN, FAN_SPEED_STEPS_MAX]

    def test_what_the_field_saves_as(self, run):
        assert run["saves"] == {
            "": None, "  ": None,
            "1": "refused", "2": 2, "3": 3, " 4 ": 4, "10": 10,
            "11": "refused", "2.5": "refused", "x": "refused", "-3": "refused",
        }


class TestTheDialog:
    def test_the_section_is_decided_in_settings_sections(self):
        text = _dialog()
        body = text[text.index("export function settingsSections"):]
        body = body[: body.index("return sections;")]
        assert "hasSpeedCycle(device)" in body
        assert 'sections.push("speed_cycle")' in body

    def test_the_section_follows_the_power_section(self):
        text = _dialog()
        render = text[text.index("private _renderBody()"):]
        assert (
            render.index("_renderPowerSection()")
            < render.index("_renderSpeedCycleSection()")
            < render.index("_renderConvertSection()")
        )

    def test_it_saves_all_three_settings_through_the_device_update(self):
        text = _dialog()
        save = text[text.index("private async _save()"):]
        save = save[: save.index("try {")]
        for field in (
            "fan_speed_steps",
            "speed_cycle_includes_off",
            "speed_cycle_turn_on",
        ):
            assert re.search(rf"patch\.{field}\s*=", save), field
        assert 'sections.includes("speed_cycle")' in save

    def test_it_says_the_speed_is_hairs_own_count(self):
        text = _dialog()
        section = text[text.index("private _renderSpeedCycleSection()"):]
        section = section[: section.index("</section>")]
        assert 't("devsettings.speed_cycle_drift")' in section
        # The turn-on choice only shows when off is not a step.
        assert "this._cycleIncludesOff" in section

    def test_the_drift_line_reads_as_reviewed(self):
        en = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        assert en["devsettings.speed_cycle_drift"] == (
            "The speed is HAIR's own count of presses and can drift if the fan "
            "misses one. Turn the fan off and on to line it up again."
        )
        assert en["vocab.speed_cycle"] == "Speed Cycle"
