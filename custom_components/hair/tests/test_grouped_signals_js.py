"""Grouped commands in the panel (grouped-signals.md).

The rules in ``group-steps.ts`` run under node; the wiring is pinned in
the source; the bounds are checked against ``const.py``.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from custom_components.hair import const

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


def _locale(lang: str) -> dict:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


DRIVER = """
const t = (key, subs) => {
  let s = EN[key] ?? key;
  for (const [k, v] of Object.entries(subs ?? {})) s = s.split('{' + k + '}').join(v);
  return s;
};
const devices = [
  {id: 'tv', name: 'Living Room TV',
   commands: [{id: 'a', name: 'Power On'}, {id: 'b', name: 'Mute'}]},
  {id: 'avr', name: 'AV Receiver',
   commands: [{id: 'c', name: 'Power On'}, {id: 'd', name: 'Input'}]},
  {id: 'fan', name: 'Ceiling Fan', commands: [{id: 'e', name: 'Light Off'}]},
];
const view = (q, open) => g.pickerView(devices, q, new Set(open))
  .map(r => [r.device.id, r.open, r.commands.map(c => c.id)]);
const used = (...names) => names.map(n => ({command_name: n, device_name: 'TV'}));
console.log(JSON.stringify({
  grid: [0, 299, 300, 301, 450, 500, 59950, 60000, 99999].map(g.delayOnGrid),
  down: [300, 400, 1000, 451].map(ms => g.stepDelay(ms, -1)),
  up: [300, 950, 59900, 60000, 451].map(ms => g.stepDelay(ms, 1)),
  text: [300, 999, 1000, 1500, 12300, 60000].map(g.delayText),
  about: [4400, 0, 61000, 125500].map(g.aboutSeconds),
  move: g.moveStep(['a', 'b', 'c', 'd'], 3, 1),
  closed: view('', []),
  two_open: view('', ['tv', 'avr']),
  power: view('power', []),
  by_device: view('fan', []),
  none: view('zzz', ['tv']),
  count: g.commandsInGroup('avr', [
    {device_id: 'avr', command_id: 'c'}, {device_id: 'tv', command_id: 'a'},
    {device_id: 'avr', command_id: 'c'}, {device_id: 'avr', command_id: 'd'},
  ]),
  count_pending: g.commandsInGroup('avr', [{device_id: 'avr', command_id: 'c'}],
    ['avr/d', 'avr/c', 'tv/a']),
  blocked: [
    {blaster: false, matrix: false, commands: [{reason: 'no_blaster'}]},
    {blaster: true, matrix: true, commands: [{reason: 'lattice'}, {reason: 'lattice'}]},
    {blaster: true, matrix: true, commands: []},
    {blaster: true, matrix: true, commands: [{reason: 'lattice'}, {reason: null}]},
    {blaster: true, matrix: false, commands: []},
    {blaster: true, matrix: false, commands: [{reason: 'rolling'}]},
    {blaster: true, commands: [{reason: null}]},
  ].map(g.deviceBlocked),
  group: [g.isGroup({protocol: 'GROUP'}), g.isGroup({protocol: 'PRONTO'}), g.isGroup(null)],
  note_one: g.groupsNote(t, used('Movie night')),
  note_two: g.groupsNote(t, used('Movie night', 'Game time')),
  note_none: g.groupsNote(t, []),
  bounds: [g.GROUP_DELAY_MIN_MS, g.GROUP_DELAY_MAX_MS, g.GROUP_DELAY_DEFAULT_MS,
           g.GROUP_MAX_STEPS, g.GROUP_RUN_MAX_MS, g.GROUP_PROTOCOL],
}));
"""


@pytest.fixture(scope="module")
def rules(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("groups")
    (out / "rule.ts").write_text(
        (SRC / "group-steps.ts").read_text(encoding="utf-8"), encoding="utf-8"
    )
    subprocess.run(
        [str(TSC), str(out / "rule.ts"), "--module", "esnext", "--target", "es2022",
         "--skipLibCheck", "--outDir", str(out)],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    en = _locale("en")
    driver = (
        'import * as g from "./rule.js";\n'
        f"const EN = {json.dumps(en, ensure_ascii=False)};\n" + DRIVER
    )
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheRules:
    def test_the_stepper_stays_on_the_grid(self, rules):
        # 100 ms steps between the server's floor and its most; a stored
        # delay off the grid rounds up.
        assert rules["grid"] == [300, 300, 300, 400, 500, 500, 60000, 60000, 60000]
        assert rules["down"] == [300, 300, 900, 400]
        assert rules["up"] == [400, 1100, 60000, 60000, 600]
        assert rules["text"] == ["300 ms", "999 ms", "1 s", "1.5 s", "12.3 s", "60 s"]

    def test_the_bounds_are_the_servers(self, rules):
        from custom_components.hair.models import GROUP_PROTOCOL

        assert rules["bounds"] == [
            const.GROUP_DELAY_MIN_MS, const.GROUP_DELAY_MAX_MS,
            const.GROUP_DELAY_DEFAULT_MS, const.GROUP_MAX_STEPS,
            const.GROUP_RUN_MAX_MS, GROUP_PROTOCOL,
        ]

    def test_run_times(self, rules):
        assert rules["about"] == ["4.4 s", "0.0 s", "1 min 1 s", "2 min 6 s"]

    def test_a_drag_moves_one_step(self, rules):
        assert rules["move"] == ["a", "d", "b", "c"]

    def test_devices_come_up_closed_and_open_together(self, rules):
        assert [r[1] for r in rules["closed"]] == [False, False, False]
        assert [r[1] for r in rules["two_open"]] == [True, True, False]

    def test_search_opens_matches_and_shows_only_them(self, rules):
        assert rules["power"] == [["tv", True, ["a"]], ["avr", True, ["c"]]]
        # A device name match shows all its commands.
        assert rules["by_device"] == [["fan", True, ["e"]]]
        assert rules["none"] == []

    def test_a_device_with_nothing_to_add_is_greyed(self, rules):
        # A matrix device with a saved state is offered; one without is
        # greyed with the pointer to saving a state.
        assert rules["blocked"] == [
            "no_blaster", "matrix", "matrix", None, "empty", "nothing", None,
        ]

    def test_counts_and_the_test(self, rules):
        # Each command once, however many steps send it; ADDs in flight
        # count before the save comes back.
        assert rules["count"] == 2
        assert rules["count_pending"] == 2
        assert rules["group"] == [True, False, False]

    def test_the_delete_note(self, rules):
        assert rules["note_one"] == (
            " It's a step in the grouped signal Movie night (TV), which will "
            "show it as missing."
        )
        assert rules["note_two"].startswith(
            " It's a step in 2 grouped signals: Movie night (TV), Game time (TV)."
        )
        assert rules["note_none"] == ""


class TestTheWiring:
    def test_the_row(self):
        row = _flat("ir-command-row.ts")
        assert 'const group = isGroup(this.command);' in row
        assert 'html`<span class="group-chip">${t("group.chip")}</span>`' in row
        # The chevron takes the edit pencil's place; TRIGGER's space is held.
        assert '@click=${() => this._emit("toggle-open")}' in row
        assert 'class="action-btn trigger-btn reserve"' in row
        assert '${group && this.open ? html`<slot name="group"></slot>` : ""}' in row
        assert "? this._groupSummary()" in row

    def test_the_device_page(self):
        page = _flat("ir-device-detail.ts")
        assert '@click=${this._addGroup}' in page
        assert '>${t("group.add")}</button>' in page
        assert 'html`<ir-group-steps slot="group"' in page
        assert '+ groupsNote(t, this._deleteGroups)' in page
        assert 'this._groupTestLine(command, result.group)' in page
        lst = _flat("ir-device-list.ts")
        assert 'groupsNote(t, this._deleteDeviceGroups)' in lst

    def test_the_steps_save_as_made(self):
        steps = _flat("ir-group-steps.ts")
        assert "this.api.groupSetSteps(" in steps
        assert 'new CustomEvent("device-updated"' in steps
        # The delay is a stepper: - greys at the floor, + at the most,
        # and a held press saves once, on release.
        assert '?disabled=${this._busy || delay <= GROUP_DELAY_MIN_MS}' in steps
        assert '?disabled=${this._busy || delay >= GROUP_DELAY_MAX_MS}' in steps
        assert "@pointerup=${() => this._endHold(index)}" in steps
        assert '<span class="ms" aria-live="polite">${delayText(delay)}</span>' in steps
        # The band: a clock in the grip's column, no word, keys with no
        # fill of their own; the hover says what it is.
        assert '<div class="wait" title=${t("group.delay_title")}>' in steps
        assert '<svg class="clock" viewBox="0 0 24 24"' in steps
        assert "background: transparent;" in steps
        assert "border-radius: 11px" not in steps
        assert "<input" not in steps and "floor_hint" not in steps
        assert 'handle: ".grip",' in steps

    def test_the_picker(self):
        picker = _flat("ir-group-picker.ts")
        assert "pickerView(shown, this._query, this._open)" in picker
        assert "commandsInGroup(device.id, this.steps, this._staged.keys())" in picker
        assert 'no_blaster: "group.reason_no_blaster",' in picker

    def test_the_picker_rows_add_with_a_count(self):
        picker = _flat("ir-group-picker.ts")
        # A green ADD chip on the left of every sendable row, with the
        # shared count dot: a command can be added more than once.
        assert 'class="action-btn assign-btn add-btn"' in picker
        assert '<ir-count-dot color="green" .count=${this._countOf(device.id, c.id)}' in picker
        # No protocol chip, no tick and no band: the right of a row is
        # empty, or a greyed row's reason.
        assert "ir-protocol-chip" not in picker
        assert "✓" not in picker
        assert "bandText(full)" not in picker
        # The dot goes up on the click: the pick is staged.
        assert "staged.set(key, (staged.get(key) ?? 0) + 1);" in picker

    def test_the_picker_devices_say_their_media_and_filter(self):
        picker = _flat("ir-group-picker.ts")
        # The Devices page's glyphs, left of the name.
        assert "(device.media ?? []).map((m) => renderProtoGlyph(m, 16))" in picker
        # The filter is not remembered, and search runs inside it.
        assert "@state() private _show: MediaShow = { ir: true, rf: true };" in picker
        assert "loadMediaShow" not in picker and "saveMediaShow" not in picker
        assert "mediaShows(this._show, d.media)" in picker
        # A device with nothing to add is greyed at its row, no chevron.
        assert "const blocked = deviceBlocked(device);" in picker
        assert "${t(BLOCKED_KEY[blocked])}" in picker

    def test_device_rows_end_with_the_counts(self):
        picker = _flat("ir-group-picker.ts")
        # "3 / 12": green in this group, grey total; the total alone at
        # none. The words are gone, so the pair carries a title.
        assert '<span class="cnt">${inGroup}</span><span class="slash">/</span>' in picker
        assert '<span class="tot">${total}</span>' in picker
        assert 't("group.count_title", { count: String(inGroup), total: String(total) })' in picker
        assert "font-variant-numeric: tabular-nums;" in picker
        en = _locale("en")
        assert en["group.count_title"] == "{count} of {total} commands in this group"
        assert "group.in_this_group" not in en
        assert en["group.reason_empty"] == "Empty"
        assert en["group.reason_nothing"] == "No groupable signals"

    def test_add_stages_and_the_green_button_adds(self):
        picker = _flat("ir-group-picker.ts")
        # ADD stages: no event per click outside Pick again.
        assert (
            "this._picks = [...this._picks, { device_id: deviceId, command_id: commandId }];"
        ) in picker
        assert 'new CustomEvent("add", { detail: { picks: this._picks } })' in picker
        # The call to action says what it does; nothing staged, a plain Close.
        assert 'class="action-btn create-btn" @click=${this._commit}' in picker
        assert 't("group.add_n_signals", { count: String(this._picks.length) })' in picker
        assert 't(this.replace ? "common.cancel" : "common.close")' in picker
        assert "background: #2e7d32; color: #fff; border-color: #2e7d32;" in picker
        # X and Escape drop the staged picks; a click outside is ignored
        # while something is staged.
        assert 'if (e.key === "Escape") this._close();' in picker
        assert "if (!this._picks.length) this._close();" in picker
        # Pick again still takes one pick and closes.
        assert 'if (this.replace) { this.dispatchEvent( new CustomEvent("pick",' in picker
        # The group's cap counts what is staged.
        assert "return this.steps.length + this._picks.length >= GROUP_MAX_STEPS;" in picker
        en = _locale("en")
        assert en["group.add_one_signal"] == "Add 1 signal"
        assert en["group.add_n_signals"] == "Add {count} signals"
        assert "group.done" not in en and "group.added" not in en
        steps = _flat("ir-group-steps.ts")
        assert "@add=${this._onAdd}" in steps
        assert "if (this._steps.length + picks.length > GROUP_MAX_STEPS) {" in steps

    def test_the_picker_top_edge_stays_put(self):
        picker = _flat("ir-group-picker.ts")
        assert "if (this._top !== null || this._devices === null) return;" in picker
        assert "margin-top:${this._top}px;max-height:calc(100vh - ${this._top}px - 16px)" in picker
        assert ".overlay.anchored { align-items: flex-start; }" in picker
        # Border-box, so the bottom edge holds 16px above the window's.
        assert ".dialog.picker { box-sizing: border-box;" in picker

    def test_the_opened_view(self):
        steps = _flat("ir-group-steps.ts")
        # No left line; each step its own block; the wait between them.
        assert "border-left" not in steps
        assert (
            "background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);"
        ) in steps
        # The run time and "No steps yet" are said once, on the row.
        assert "group.runs_about" not in steps and "group.no_steps" not in steps
        # The x takes a step out, never the command: red on hover.
        assert "color: var(--error-color, #db4437); }" in steps
        assert _locale("en")["group.remove_step"] == "Remove from this group"

    def test_the_group_colour_is_avocado_per_theme(self):
        rules = _flat("group-steps.ts")
        assert 'export const GROUP_HUE = "#86a83f";' in rules
        assert 'export const GROUP_HUE_LIGHT = "#55722a";' in rules
        # The device page picks the tone; the chip and the badge follow.
        page = _flat("ir-device-detail.ts")
        assert 'this.toggleAttribute("dark", Boolean(this.hass?.themes?.darkMode));' in page
        assert ":host { --hair-group-hue: ${unsafeCSS(GROUP_HUE_LIGHT)}; }" in page
        assert ":host([dark]) { --hair-group-hue: ${unsafeCSS(GROUP_HUE)}; }" in page
        row = _flat("ir-command-row.ts")
        assert "color: var(--hair-group-hue, ${unsafeCSS(GROUP_HUE)});" in row
        picker = _flat("ir-group-picker.ts")
        assert "color: var(--hair-group-hue, ${unsafeCSS(GROUP_HUE)});" in picker
        assert "#c9a3e6" not in row and "#c9a3e6" not in picker

    def test_the_chevron_is_the_pencils_width(self):
        # 26 put a group's TEST 2px left of the rows around it.
        row = _flat("ir-command-row.ts")
        assert ".expand-btn { background: none; border: none;" in row
        assert "box-sizing: border-box; width: 24px; height: 30px;" in row

    def test_the_api(self):
        api = _flat("api.ts")
        for door in ("group/create", "group/steps", "group/candidates", "group/used-by"):
            assert f'type: "hair/command/{door}"' in api


class TestTheStrings:
    def test_every_locale_has_every_key_with_its_placeholders(self):
        en = _locale("en")
        keys = [k for k in en if k.startswith("group.")]
        assert len(keys) >= 45
        for path in LOCALES.glob("*.json"):
            words = json.loads(path.read_text(encoding="utf-8"))
            for key in keys:
                assert words.get(key), (path.name, key)
                assert "—" not in words[key], (path.name, key)
                assert sorted(re.findall(r"\{(\w+)\}", words[key])) == sorted(
                    re.findall(r"\{(\w+)\}", en[key])
                ), (path.name, key)

    def test_the_english_words(self):
        en = _locale("en")
        assert en["group.add"] == "+ Grouped Signals"
        assert en["group.chip"] == "Group"
        assert en["group.delay_title"] == "Delay before the next step"
        assert "group.delay" not in en
        assert "group.then_wait" not in en and "group.floor_hint" not in en
        assert en["group.reason_rolling"] == "Rolling code, never sent"
        assert en["group.reason_no_blaster"] == "No blaster set"
        assert en["group.reason_matrix_empty"] == "Save a state as a command to use it"
