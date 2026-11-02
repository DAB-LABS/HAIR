"""The device settings dialog's state source picker (GH #232).

The rules live in ``state-source.ts``: which entities the picker
offers and in which group, what a search leaves, how long the settle
time may be, what the settle field is set to when a source is picked,
and what a save sends. This transpiles it
with the repo's own TypeScript and runs it under node, in the house
pattern of ``test_speed_cycle_settings_js.py``. The dialog is a lit
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
    MAX_ON_OFF_SETTLE_S, MAX_POWER_SETTLE_S, TRACKER_SETTLE_PRESET_S,
    filterSourceGroups, isOnOffEntity, settleCapFor, settleOnPick,
    stateSourceCandidates, stateSourcePatch,
} from "./state-source.js";

const st = (name, attrs = {}, state = "on") => ({
    state, attributes: { friendly_name: name, ...attrs },
});
const states = {
    "sensor.tv_plug_power": st("TV plug power", { device_class: "power" }, "42"),
    "sensor.amp_watts": st("Amp watts", { unit_of_measurement: "W" }, "3"),
    "sensor.heater_kw": st("Heater", { unit_of_measurement: "kW" }, "1.2"),
    "sensor.outdoor_temp": st("Outdoor temp", { unit_of_measurement: "°C" }, "9"),
    "binary_sensor.tv_on": st("TV on"),
    "switch.amp_plug": st("Amp plug"),
    "input_boolean.tv_on": st("A TV helper", {}, "off"),
    "device_tracker.living_room_tv": st("Living room TV", {}, "home"),
    "light.tv_backlight": st("Backlight"),
    "media_player.tv": st("Media TV"),
    "switch.hair_bench_fan": st("Bench fan"),
    "binary_sensor.no_name": { state: "off", attributes: {} },
};
const entities = {
    "switch.hair_bench_fan": { platform: "hair" },
    "switch.amp_plug": { platform: "shelly" },
};
const ids = (g) => ({
    power: g.power.map((c) => c.entityId),
    onOff: g.onOff.map((c) => c.entityId),
});
const groups = {
    plain: ids(stateSourceCandidates(states, entities, null)),
    saved_on_off_gone: ids(
        stateSourceCandidates(states, entities, "device_tracker.old_tv"),
    ),
    saved_sensor_gone: ids(
        stateSourceCandidates(states, entities, "sensor.old_plug"),
    ),
    saved_present: ids(
        stateSourceCandidates(states, entities, "switch.amp_plug"),
    ),
    saved_hair: ids(
        stateSourceCandidates(states, entities, "switch.hair_bench_fan"),
    ),
    empty: ids(stateSourceCandidates({}, {}, null)),
};
const kinds = {};
for (const id of [
    "binary_sensor.x", "switch.x", "input_boolean.x", "device_tracker.x",
    "sensor.x", "light.x", "media_player.x", "remote.x", "switch", ".x", "",
]) {
    kinds[id] = isOnOffEntity(id);
}
kinds["null"] = isOnOffEntity(null);
const patches = {
    none: stateSourcePatch(null, "2", "10", null),
    sensor: stateSourcePatch("sensor.tv_plug_power", "2", "10", 20),
    tracker: stateSourcePatch("device_tracker.living_room_tv", "2", "10", 120),
    switch_no_settle: stateSourcePatch("switch.amp_plug", "", "", null),
};
const caps = {};
for (const id of [
    "sensor.tv_plug_power", "binary_sensor.tv_on", "switch.amp_plug",
    "input_boolean.tv_on", "device_tracker.living_room_tv", "", "null",
]) {
    caps[id] = settleCapFor(id === "null" ? null : id);
}
const picks = {};
for (const [id, field] of [
    ["device_tracker.living_room_tv", "20"],
    ["device_tracker.living_room_tv", ""],
    ["device_tracker.living_room_tv", "0"],
    ["device_tracker.living_room_tv", "600"],
    ["binary_sensor.tv_on", "300"],
    ["binary_sensor.tv_on", "600"],
    ["binary_sensor.tv_on", "900"],
    ["switch.amp_plug", "20"],
    ["sensor.tv_plug_power", "300"],
    ["sensor.tv_plug_power", "120"],
    ["sensor.tv_plug_power", "20"],
    ["sensor.tv_plug_power", ""],
    ["sensor.tv_plug_power", "0"],
]) {
    picks[`${id} ${field}`] = settleOnPick(id, field);
}
const all = stateSourceCandidates(states, entities, null);
const search = {};
for (const [query, current] of [
    ["", null], ["   ", null], ["tv", null], ["TV", null], [" Tv ", null],
    ["power", null], ["device_tracker.", null], ["living", null],
    ["helper", null], ["plug", null], ["no_name", null], ["zzz", null],
    ["zzz", "switch.amp_plug"], ["tv", "sensor.amp_watts"], ["zzz", ""],
]) {
    search[`${query}|${current}`] = ids(filterSourceGroups(all, query, current));
}
const same = filterSourceGroups(all, "", null) === all;
const twins = ids(stateSourceCandidates({
    "binary_sensor.b": st("TV"), "binary_sensor.a": st("TV"),
}, {}, null));
const settle = {
    power: MAX_POWER_SETTLE_S, onOff: MAX_ON_OFF_SETTLE_S,
    preset: TRACKER_SETTLE_PRESET_S,
};
console.log(JSON.stringify({
    groups, kinds, patches, caps, picks, settle, search, same, twins,
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("statesourcejs")
    subprocess.run(
        [
            str(TSC), "src/state-source.ts",
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


def _panel() -> str:
    text = _dialog()
    body = text[text.index("private _renderSourcePanel"):]
    return body[: body.index("\n    }\n")]


def _power_section() -> str:
    text = _dialog()
    body = text[text.index("private _renderPowerSection()"):]
    return body[: body.index("private _renderSpeedCycleSection()")]


POWER = ["sensor.amp_watts", "sensor.heater_kw", "sensor.tv_plug_power"]
ON_OFF = [
    "input_boolean.tv_on",          # A TV helper
    "switch.amp_plug",              # Amp plug
    "binary_sensor.no_name",        # no friendly name: sorted by its id
    "device_tracker.living_room_tv",  # Living room TV
    "binary_sensor.tv_on",          # TV on
]


@toolchain
class TestThePicker:
    def test_two_groups_each_sorted_by_name(self, run):
        assert run["groups"]["plain"] == {"power": POWER, "onOff": ON_OFF}

    def test_hair_entities_and_other_domains_are_left_out(self, run):
        everything = (
            run["groups"]["plain"]["power"] + run["groups"]["plain"]["onOff"]
        )
        assert "switch.hair_bench_fan" not in everything
        assert "light.tv_backlight" not in everything
        assert "media_player.tv" not in everything
        assert "sensor.outdoor_temp" not in everything

    def test_a_saved_source_that_is_gone_stays_in_its_group(self, run):
        on_off_gone = run["groups"]["saved_on_off_gone"]
        assert on_off_gone["power"] == POWER
        assert "device_tracker.old_tv" in on_off_gone["onOff"]
        sensor_gone = run["groups"]["saved_sensor_gone"]
        assert sensor_gone["onOff"] == ON_OFF
        assert "sensor.old_plug" in sensor_gone["power"]

    def test_a_saved_source_present_is_listed_once(self, run):
        assert run["groups"]["saved_present"] == {
            "power": POWER, "onOff": ON_OFF,
        }

    def test_a_saved_hair_entity_stays_selectable(self, run):
        # The websocket refuses one now; one saved before still shows,
        # so reopening the dialog does not silently change the source.
        assert "switch.hair_bench_fan" in run["groups"]["saved_hair"]["onOff"]

    def test_no_states(self, run):
        assert run["groups"]["empty"] == {"power": [], "onOff": []}

    def test_which_entities_are_on_off(self, run):
        assert run["kinds"] == {
            "binary_sensor.x": True, "switch.x": True,
            "input_boolean.x": True, "device_tracker.x": True,
            "sensor.x": False, "light.x": False, "media_player.x": False,
            "remote.x": False, "switch": False, ".x": False, "": False,
            "null": False,
        }


@toolchain
class TestTheSave:
    def test_no_source_clears_everything(self, run):
        assert run["patches"]["none"] == {
            "power_sensor_entity_id": None,
            "power_off_below_w": None,
            "power_on_above_w": None,
            "power_settle_s": None,
        }

    def test_a_power_sensor_sends_its_thresholds(self, run):
        assert run["patches"]["sensor"] == {
            "power_sensor_entity_id": "sensor.tv_plug_power",
            "power_off_below_w": 2,
            "power_on_above_w": 10,
            "power_settle_s": 20,
        }

    def test_an_on_off_source_sends_no_thresholds(self, run):
        assert run["patches"]["tracker"] == {
            "power_sensor_entity_id": "device_tracker.living_room_tv",
            "power_off_below_w": None,
            "power_on_above_w": None,
            "power_settle_s": 120,
        }
        assert run["patches"]["switch_no_settle"]["power_off_below_w"] is None
        assert run["patches"]["switch_no_settle"]["power_on_above_w"] is None


@toolchain
class TestTheSearch:
    def test_an_empty_query_leaves_both_groups_whole(self, run):
        whole = {"power": POWER, "onOff": ON_OFF}
        assert run["search"]["|null"] == whole
        assert run["search"]["   |null"] == whole
        assert run["same"] is True

    def test_it_matches_the_name_ignoring_case(self, run):
        expected = {
            "power": ["sensor.tv_plug_power"],
            "onOff": [
                "input_boolean.tv_on",
                "device_tracker.living_room_tv",
                "binary_sensor.tv_on",
            ],
        }
        for query in ("tv", "TV", " Tv "):
            assert run["search"][f"{query}|null"] == expected, query
        assert run["search"]["helper|null"] == {
            "power": [], "onOff": ["input_boolean.tv_on"],
        }
        assert run["search"]["plug|null"] == {
            "power": ["sensor.tv_plug_power"], "onOff": ["switch.amp_plug"],
        }

    def test_it_matches_the_entity_id(self, run):
        assert run["search"]["power|null"]["power"] == ["sensor.tv_plug_power"]
        assert run["search"]["device_tracker.|null"] == {
            "power": [], "onOff": ["device_tracker.living_room_tv"],
        }
        # No friendly name: the entity id is the name and the match.
        assert run["search"]["no_name|null"] == {
            "power": [], "onOff": ["binary_sensor.no_name"],
        }

    def test_nothing_matches(self, run):
        assert run["search"]["zzz|null"] == {"power": [], "onOff": []}
        # None ("") is not an entity: nothing is kept for it.
        assert run["search"]["zzz|"] == {"power": [], "onOff": []}

    def test_the_current_source_stays_whatever_the_query(self, run):
        assert run["search"]["zzz|switch.amp_plug"] == {
            "power": [], "onOff": ["switch.amp_plug"],
        }
        # Kept in its place in the sorted group, not moved to the top.
        assert run["search"]["tv|sensor.amp_watts"] == {
            "power": ["sensor.amp_watts", "sensor.tv_plug_power"],
            "onOff": [
                "input_boolean.tv_on",
                "device_tracker.living_room_tv",
                "binary_sensor.tv_on",
            ],
        }

    def test_equal_names_sort_by_entity_id(self, run):
        assert run["twins"]["onOff"] == ["binary_sensor.a", "binary_sensor.b"]


@toolchain
class TestTheSettleTime:
    def test_the_caps_match_the_backend(self, run):
        from custom_components.hair.models import (
            MAX_ON_OFF_SETTLE_S,
            MAX_POWER_SETTLE_S,
        )

        assert run["settle"]["power"] == MAX_POWER_SETTLE_S == 120
        assert run["settle"]["onOff"] == MAX_ON_OFF_SETTLE_S == 600

    def test_the_cap_follows_the_source(self, run):
        assert run["caps"] == {
            "sensor.tv_plug_power": 120,
            "binary_sensor.tv_on": 600,
            "switch.amp_plug": 600,
            "input_boolean.tv_on": 600,
            "device_tracker.living_room_tv": 600,
            "": 120,
            "null": 120,
        }

    def test_a_device_tracker_presets_300(self, run):
        assert run["settle"]["preset"] == 300
        for field in ("20", "", "0", "600"):
            assert run["picks"][f"device_tracker.living_room_tv {field}"] == "300"

    def test_other_sources_keep_the_field_within_their_cap(self, run):
        picks = run["picks"]
        assert picks["binary_sensor.tv_on 300"] == "300"
        assert picks["binary_sensor.tv_on 600"] == "600"
        assert picks["binary_sensor.tv_on 900"] == "600"
        assert picks["switch.amp_plug 20"] == "20"
        assert picks["sensor.tv_plug_power 300"] == "120"
        assert picks["sensor.tv_plug_power 120"] == "120"
        assert picks["sensor.tv_plug_power 20"] == "20"
        assert picks["sensor.tv_plug_power "] == ""
        assert picks["sensor.tv_plug_power 0"] == "0"


class TestTheDialog:
    def test_the_picker_uses_the_shared_rules(self):
        text = _dialog()
        groups = text[text.index("private _sourceGroups"):]
        groups = groups[: groups.index("\n    }\n")]
        assert "stateSourceCandidates(" in groups
        assert "this.hass?.entities" in groups
        assert "this._sourceGroups()" in _power_section()
        assert "_candidateSensors" not in text

    def test_the_search_filters_the_list(self):
        section = _power_section()
        assert "<select" not in section
        call = section[section.index("filterSourceGroups("):]
        call = re.sub(r"\s+", "", call[: call.index(");")])
        assert call == (
            "filterSourceGroups(groups,this._picker.query,"
            "this._sensorChoice||null,"
        )
        panel = _panel()
        assert 'class="source-search"' in panel
        assert 't("devsettings.source_search")' in panel
        assert 't("devsettings.source_no_match")' in panel

    def test_none_then_power_sensors_then_on_off(self):
        panel = _panel()
        search = panel.index('class="source-search"')
        none = panel.index('t("devsettings.sensor_none")')
        power = panel.index('t("devsettings.power_group_label")')
        on_off = panel.index('t("devsettings.onoff_group_label")')
        hint = panel.index('t("devsettings.onoff_group_hint")')
        assert search < none < power < on_off < hint
        assert "shown.power.map(" in panel[power:on_off]
        assert "shown.onOff.map(" in panel[on_off:]

    def test_a_heading_shows_only_over_rows(self):
        panel = _panel()
        assert "${shown.power.length\n" in panel
        assert "${shown.onOff.length\n" in panel

    def test_rows_take_the_capture_switch_shape(self):
        text = _dialog()
        row = text[text.index("private _renderSourceRow"):]
        row = row[: row.index("\n    }\n")]
        assert 'role="option"' in row
        assert "aria-selected=" in row
        assert "this._renderSourceDot(entityId)" in row
        assert 'class="iname"' in row and 'class="iid"' in row
        dot = text[text.index("private _renderSourceDot"):]
        dot = dot[: dot.index("\n    }\n")]
        assert "healthDotClass(" in dot and "isEntityOnline(" in dot
        assert "healthDotStyles," in text

    def test_the_wattage_fields_hide_for_an_on_off_source(self):
        section = _power_section()
        grid = section.index('class="pair-grid field"')
        gate = section.rindex("${sensorPicked", 0, grid)
        assert section[gate:grid].startswith("${sensorPicked && !onOff")

    def test_the_readout_and_settle_stay_with_their_on_off_text(self):
        section = _power_section()
        assert "this._renderLiveReadout(liveState, onOff)" in section
        assert '"devsettings.onoff_explainer"' in section
        assert '"devsettings.power_explainer"' in section
        assert '"devsettings.settle_help_onoff"' in section
        assert '"devsettings.settle_help"' in section

    def test_validation_skips_the_thresholds_for_an_on_off_source(self):
        text = _dialog()
        body = text[text.index("private get _validationError()"):]
        body = body[: body.index("\n    }\n")]
        assert "if (isOnOffEntity(this._sensorChoice)) return null;" in body

    def test_the_settle_field_follows_the_source(self):
        text = _dialog()
        assert "MAX_SETTLE_S" not in text
        assert "_onSensorChoiceChanged" not in text
        pick = text[text.index("private _pickSource"):]
        pick = pick[: pick.index("\n    }\n")]
        assert "this._sensorChoice = entityId;" in pick
        assert "settleOnPick(entityId, this._settle)" in pick
        save = text[text.index("private _settleForSave"):]
        save = save[: save.index("\n    }\n")]
        assert "settleCapFor(this._sensorChoice)" in save
        assert "max=${settleCapFor(this._sensorChoice)}" in _power_section()

    def test_the_save_uses_the_shared_patch(self):
        text = _dialog()
        body = text[text.index("private async _save"):]
        body = body[: body.index("\n    }\n")]
        assert "stateSourcePatch(" in body
