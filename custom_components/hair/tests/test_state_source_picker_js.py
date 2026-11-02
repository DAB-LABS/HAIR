"""The Power state picker's closed field and floating list (GH #232).

The field starts closed, showing the chosen source; a click, Enter,
Space or Arrow Down opens a list that floats under it (or over it, near
the bottom of the window) with a search on top. How the two answer
clicks and keys is ``pickerStep`` in ``state-source.ts``, and where the
list goes is ``placePanel``: this transpiles that module with the
repo's own TypeScript and runs both under node, in the house pattern of
``test_state_source_js.py``. The dialog only carries out what a step
asks, which is checked by reading its source.

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

DRIVER = r"""
import {
    OPEN_KEYS, PANEL_EDGE, PANEL_GAP, PANEL_MAX_HEIGHT, PICKER_CLOSED,
    filterSourceGroups, pickerOptions, pickerStep, placePanel,
    settleOnPick, stateSourceCandidates,
} from "./state-source.js";

const st = (name, attrs = {}, state = "on") => ({
    state, attributes: { friendly_name: name, ...attrs },
});
const states = {
    "sensor.tv_plug_power": st("TV plug power", { device_class: "power" }, "42"),
    "sensor.amp_watts": st("Amp watts", { unit_of_measurement: "W" }, "3"),
    "binary_sensor.tv_on": st("TV on"),
    "switch.amp_plug": st("Amp plug"),
    "device_tracker.living_room_tv": st("Living room TV", {}, "home"),
    "switch.hair_bench_fan": st("Bench fan"),
};
const entities = { "switch.hair_bench_fan": { platform: "hair" } };
const groups = stateSourceCandidates(states, entities, null);

/** A dialog in miniature: the picker state, the chosen source and the
 * settle field, moved by events exactly as the dialog moves them. */
function session(chosen, settle = "20") {
    let state = PICKER_CLOSED;
    const log = [];
    const optionsFor = (query, keep = true) =>
        pickerOptions(filterSourceGroups(groups, query, keep ? chosen || null : null));
    return {
        get state() { return state; },
        get chosen() { return chosen; },
        get settle() { return settle; },
        log,
        send(event) {
            const step = pickerStep(state, event, chosen, optionsFor);
            state = step.state;
            if (step.pick !== undefined && step.pick !== chosen) {
                chosen = step.pick;
                if (chosen) settle = settleOnPick(chosen, settle);
            }
            const entry = {
                open: state.open, query: state.query, active: state.active,
                pick: step.pick ?? null, focusField: !!step.focusField,
                focusSearch: !!step.focusSearch, handled: !!step.handled,
                chosen, settle,
            };
            log.push(entry);
            return entry;
        },
    };
}
const key = (k) => ({ kind: "panel-key", key: k });
const fieldKey = (k) => ({ kind: "field-key", key: k });

const out = {};
out.options = pickerOptions(groups);
out.openKeys = OPEN_KEYS;
out.closed = PICKER_CLOSED;

// Opening.
out.click = session("device_tracker.living_room_tv").send({ kind: "field-click" });
out.fieldKeys = {};
for (const k of ["Enter", " ", "ArrowDown", "ArrowUp", "Escape", "Tab", "a", "Home"]) {
    out.fieldKeys[k] = session("").send(fieldKey(k));
}
out.closedIgnores = {};
for (const ev of [key("ArrowDown"), key("Enter"), key("Escape"), { kind: "outside" },
                  { kind: "row", entityId: "switch.amp_plug" }, { kind: "query", value: "tv" }]) {
    out.closedIgnores[JSON.stringify(ev)] = session("").send(ev);
}

// Closing with no change.
const closing = {};
for (const [name, ev] of [
    ["escape", key("Escape")], ["tab", key("Tab")],
    ["outside", { kind: "outside" }], ["field-click", { kind: "field-click" }],
    ["escape-on-field", fieldKey("Escape")],
]) {
    const s = session("sensor.tv_plug_power");
    s.send({ kind: "field-click" });
    s.send(key("ArrowDown"));
    closing[name] = s.send(ev);
}
out.closing = closing;

// Picking.
const byRow = session("sensor.tv_plug_power", "20");
byRow.send({ kind: "field-click" });
out.rowTracker = byRow.send({ kind: "row", entityId: "device_tracker.living_room_tv" });
byRow.send({ kind: "field-click" });
out.rowPlug = byRow.send({ kind: "row", entityId: "sensor.amp_watts" });
byRow.send({ kind: "field-click" });
out.rowNone = byRow.send({ kind: "row", entityId: "" });

const byEnter = session("", "20");
byEnter.send(fieldKey("Enter"));
const walk = [];
for (const k of ["Home", "ArrowDown", "ArrowDown", "ArrowDown", "ArrowDown",
                 "ArrowDown", "ArrowDown", "ArrowDown", "ArrowUp", "End", "ArrowUp",
                 "Home", "ArrowUp"]) {
    walk.push(byEnter.send(key(k)).active);
}
out.walk = walk;
byEnter.send(key("End"));
out.enterPick = byEnter.send(key("Enter"));

// The search.
const searching = session("sensor.tv_plug_power");
searching.send({ kind: "field-click" });
out.typeLiving = searching.send({ kind: "query", value: "living" });
out.typeTv = searching.send({ kind: "query", value: "tv" });
out.tvWalk = [key("ArrowDown"), key("ArrowDown"), key("ArrowDown"), key("End"), key("Home")]
    .map((ev) => searching.send(ev).active);
out.typeZzz = searching.send({ kind: "query", value: "zzz" });
out.typeBlank = searching.send({ kind: "query", value: "   " });
searching.send({ kind: "query", value: "Living" });
out.enterFound = searching.send(key("Enter"));
out.reopen = searching.send({ kind: "field-click" });
searching.send({ kind: "query", value: "amp" });
searching.send(key("Escape"));
out.reopenAfterEscape = searching.send(fieldKey("ArrowDown"));

// Typing a space in the search is text, not a key the list takes.
out.spaceInSearch = searching.send(key(" "));

// Placement.
const vp = { width: 600, height: 560 };
out.place = {
    high: placePanel({ top: 100, bottom: 138, left: 56, width: 488 }, vp),
    low: placePanel({ top: 470, bottom: 508, left: 56, width: 488 }, vp),
    middleLow: placePanel({ top: 300, bottom: 338, left: 56, width: 488 }, vp),
    tiny: placePanel({ top: 60, bottom: 98, left: 10, width: 300 }, { width: 320, height: 200 }),
    wide: placePanel({ top: 100, bottom: 138, left: -40, width: 900 }, vp),
    right: placePanel({ top: 100, bottom: 138, left: 400, width: 300 }, vp),
};
out.constants = { PANEL_EDGE, PANEL_GAP, PANEL_MAX_HEIGHT };
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("sourcepickerjs")
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


TRACKER = "device_tracker.living_room_tv"
OPTIONS = [
    "",
    "sensor.amp_watts",          # Amp watts
    "sensor.tv_plug_power",      # TV plug power
    "switch.amp_plug",           # Amp plug
    TRACKER,                     # Living room TV
    "binary_sensor.tv_on",       # TV on
]


@toolchain
class TestOpening:
    def test_it_starts_closed(self, run):
        assert run["closed"] == {"open": False, "query": "", "active": None}

    def test_the_options_are_none_then_the_groups_and_no_headings(self, run):
        assert run["options"] == OPTIONS

    def test_a_click_opens_on_the_chosen_source_with_focus_in_the_search(
        self, run
    ):
        assert run["click"] == {
            "open": True, "query": "", "active": TRACKER, "pick": None,
            "focusField": False, "focusSearch": True, "handled": False,
            "chosen": TRACKER, "settle": "20",
        }

    def test_enter_space_and_arrow_down_open_the_closed_field(self, run):
        assert run["openKeys"] == ["Enter", " ", "ArrowDown"]
        for k in ("Enter", " ", "ArrowDown"):
            step = run["fieldKeys"][k]
            assert step["open"] and step["handled"] and step["focusSearch"], k
            assert step["active"] == "", k

    def test_other_keys_leave_it_closed_and_pass_through(self, run):
        for k in ("ArrowUp", "Escape", "Tab", "a", "Home"):
            step = run["fieldKeys"][k]
            assert not step["open"] and not step["handled"], k

    def test_while_closed_nothing_else_moves_it(self, run):
        for name, step in run["closedIgnores"].items():
            assert not step["open"], name
            assert step["pick"] is None and not step["handled"], name


@toolchain
class TestClosing:
    @pytest.mark.parametrize("how", ["escape", "tab", "escape-on-field"])
    def test_escape_and_tab_close_with_no_change_and_are_handled(self, run, how):
        step = run["closing"][how]
        assert not step["open"]
        assert step["pick"] is None
        assert step["chosen"] == "sensor.tv_plug_power"
        assert step["focusField"] is True
        # Handled: the dialog cancels and stops the key, so Escape never
        # reaches the dialog around the picker.
        assert step["handled"] is True

    @pytest.mark.parametrize("how", ["outside", "field-click"])
    def test_a_click_outside_or_on_the_field_closes_with_no_change(self, run, how):
        step = run["closing"][how]
        assert not step["open"]
        assert step["pick"] is None
        assert step["chosen"] == "sensor.tv_plug_power"
        assert step["focusField"] is True
        assert step["query"] == "" and step["active"] is None


@toolchain
class TestPicking:
    def test_a_row_closes_it_and_sets_the_source_and_settle(self, run):
        tracker = run["rowTracker"]
        assert not tracker["open"] and tracker["focusField"]
        assert (tracker["pick"], tracker["chosen"], tracker["settle"]) == (
            TRACKER, TRACKER, "300",
        )
        plug = run["rowPlug"]
        assert (plug["chosen"], plug["settle"]) == ("sensor.amp_watts", "120")
        none = run["rowNone"]
        assert (none["pick"], none["chosen"]) == ("", "")
        assert not none["open"]

    def test_the_arrows_walk_the_options_and_skip_the_headings(self, run):
        assert run["walk"] == [
            "",                          # Home
            "sensor.amp_watts",          # down: into Power sensors
            "sensor.tv_plug_power",
            "switch.amp_plug",           # down: past the On/off heading
            TRACKER,
            "binary_sensor.tv_on",
            "binary_sensor.tv_on",       # down at the end stays
            "binary_sensor.tv_on",
            TRACKER,                     # up
            "binary_sensor.tv_on",       # End
            TRACKER,                     # up
            "",                          # Home
            "",                          # up at the top stays
        ]

    def test_enter_picks_the_active_option(self, run):
        step = run["enterPick"]
        assert not step["open"] and step["handled"] and step["focusField"]
        assert (step["pick"], step["chosen"]) == ("binary_sensor.tv_on",) * 2


@toolchain
class TestTheSearchInTheList:
    def test_typing_moves_to_the_first_entity_found(self, run):
        assert run["typeLiving"]["active"] == TRACKER
        assert run["typeTv"]["active"] == "sensor.tv_plug_power"

    def test_the_arrows_walk_only_what_the_search_left(self, run):
        # "tv" leaves None, TV plug power (also the chosen source), Living
        # room TV and TV on.
        assert run["tvWalk"] == [
            TRACKER, "binary_sensor.tv_on", "binary_sensor.tv_on",
            "binary_sensor.tv_on", "",
        ]

    def test_nothing_found_or_a_blank_query_goes_back_to_the_chosen(self, run):
        assert run["typeZzz"]["active"] == "sensor.tv_plug_power"
        assert run["typeBlank"]["active"] == "sensor.tv_plug_power"

    def test_enter_picks_what_was_found(self, run):
        step = run["enterFound"]
        assert (step["pick"], step["chosen"], step["settle"]) == (
            TRACKER, TRACKER, "300",
        )

    def test_the_search_is_cleared_each_time_it_opens(self, run):
        assert run["reopen"]["open"] and run["reopen"]["query"] == ""
        assert run["reopen"]["active"] == TRACKER
        again = run["reopenAfterEscape"]
        assert again["open"] and again["query"] == ""

    def test_a_space_in_the_search_is_text(self, run):
        step = run["spaceInSearch"]
        assert step["open"] and not step["handled"] and step["pick"] is None


@toolchain
class TestPlacement:
    def test_the_constants(self, run):
        assert run["constants"] == {
            "PANEL_EDGE": 8, "PANEL_GAP": 4, "PANEL_MAX_HEIGHT": 320,
        }

    def test_room_below_opens_downward_under_the_field(self, run):
        place = run["place"]["high"]
        assert place["up"] is False
        assert place["top"] == 138 + 4
        assert (place["left"], place["width"]) == (56, 488)
        assert place["maxHeight"] == 320

    def test_near_the_bottom_it_opens_upward_over_the_field(self, run):
        place = run["place"]["low"]
        assert place["up"] is True
        # Placed by its bottom edge, 4px above the field's top.
        assert place["bottom"] == 560 - 470 + 4
        assert place["maxHeight"] == 320

    def test_upward_only_when_there_is_more_room_above(self, run):
        # 210px below, 288px above: up, and capped to the room above.
        place = run["place"]["middleLow"]
        assert place["up"] is True
        assert place["maxHeight"] == 300 - 4 - 8

    def test_no_room_either_way_takes_the_larger_side(self, run):
        place = run["place"]["tiny"]
        assert place["up"] is False
        assert place["maxHeight"] == 200 - 98 - 4 - 8
        assert place["left"] == 10 and place["width"] == 300

    def test_it_never_passes_the_window_edges(self, run):
        wide = run["place"]["wide"]
        assert (wide["left"], wide["width"]) == (8, 600 - 16)
        right = run["place"]["right"]
        assert right["left"] + right["width"] == 600 - 8


# ---------------------------------------------------------------------------
# The dialog carries out each step
# ---------------------------------------------------------------------------


def _dialog() -> str:
    return (SRC / "ir-device-settings-dialog.ts").read_text(encoding="utf-8")


def _method(name: str) -> str:
    text = _dialog()
    body = text[text.index(name):]
    return body[: body.index("\n    }\n")]


def _arrow(name: str) -> str:
    text = _dialog()
    body = text[text.index(name):]
    return body[: body.index("\n    };\n")]


class TestTheDialogWiring:
    def test_the_closed_field_is_a_combobox(self):
        field = _method("private _renderSourceField")
        for attr in (
            'role="combobox"',
            'aria-haspopup="listbox"',
            'aria-expanded=${open ? "true" : "false"}',
            'aria-controls="source-listbox"',
            'aria-labelledby="source-label"',
            'tabindex=${this._busy ? "-1" : "0"}',
            'class="select-chevron"',
        ):
            assert attr in field, attr
        assert '{ kind: "field-click" }' in field
        assert 'kind: "field-key", key: e.key' in field
        # The chosen source as a row shows it, or None.
        assert 't("devsettings.sensor_none")' in field
        assert 'class="iname"' in field and 'class="iid"' in field
        assert "this._renderSourceDot(id)" in field

    def test_the_list_renders_only_while_open(self):
        text = _dialog()
        assert (
            "${this._picker.open ? this._renderSourcePanel(shown) : \"\"}"
            in text
        )
        assert '<input\n                        class="source-search"' not in text

    def test_the_list_floats_with_the_popover_styles(self):
        panel = _method("private _renderSourcePanel")
        assert 'class="action-popover source-panel' in panel
        assert "popoverStyles," in _dialog()
        assert 'id="source-listbox"' in panel and 'role="listbox"' in panel
        assert "aria-activedescendant=" in panel
        assert '{ kind: "panel-key", key: e.key }' in panel
        assert 'kind: "query"' in panel

    def test_headings_are_not_options(self):
        panel = _method("private _renderSourcePanel")
        for heading in re.findall(r'<div class="source-group"[^>]*>', panel):
            assert 'aria-hidden="true"' in heading
            assert "option" not in heading
        assert panel.count('role="group"') == 2

    def test_rows_are_options_that_do_not_take_focus(self):
        row = _method("private _renderSourceRow")
        assert 'role="option"' in row and "aria-selected=" in row
        assert "<button" not in row
        assert "@pointerdown=${(e: Event) => e.preventDefault()}" in row
        assert '{ kind: "row", entityId }' in row

    def test_every_event_goes_through_picker_step(self):
        body = _method("private _pickerEvent")
        assert "pickerStep(this._picker, event, chosen," in body
        assert "dom.preventDefault();" in body and "dom.stopPropagation();" in body
        assert "if (step.pick !== undefined) this._pickSource(step.pick);" in body
        assert ".source-search\")?.focus()" in body
        assert ".source-field\")?.focus()" in body

    def test_it_is_placed_before_its_first_render(self):
        body = _method("private _pickerEvent")
        opening = body[body.index("if (!wasOpen && step.state.open)"):]
        assert opening.index("this._panel = placePanel(") < opening.index(
            "this._startPanelTracking()"
        )

    def test_an_outside_press_closes_it(self):
        start = _method("private _startPanelTracking")
        assert (
            'document.addEventListener("pointerdown", this._onOutsidePointer, true)'
            in start
        )
        assert "requestAnimationFrame(tick)" in start
        stop = _method("private _stopPanelTracking")
        assert (
            'document.removeEventListener("pointerdown", this._onOutsidePointer, true)'
            in stop
        )
        assert "cancelAnimationFrame(this._trackFrame)" in stop
        outside = _arrow("private _onOutsidePointer")
        assert '{ kind: "outside" }' in outside
        assert "e.composedPath()" in outside
        assert "focusIsOnAControl()" in outside

    def test_it_follows_the_field(self):
        place = _method("private async _placePanel")
        assert "placePanel(r, {" in place
        assert "this._panelShift" in place
        assert "_stopPanelTracking();" in _method("disconnectedCallback")
