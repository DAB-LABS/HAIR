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
  problems: ['299', '300', '60000', '60001', '1.5', '', 'abc', ' 500 ']
    .map(g.delayProblem),
  about: [4400, 0, 61000, 125500].map(g.aboutSeconds),
  move: g.moveStep(['a', 'b', 'c', 'd'], 3, 1),
  closed: view('', []),
  two_open: view('', ['tv', 'avr']),
  power: view('power', []),
  by_device: view('fan', []),
  none: view('zzz', ['tv']),
  count: g.countInGroup('avr', [{device_id: 'avr'}, {device_id: 'tv'}, {device_id: 'avr'}]),
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
    def test_the_floor_and_the_ceiling(self, rules):
        assert rules["problems"] == [
            "floor", None, None, "ceiling", "number", "number", "number", None,
        ]

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

    def test_counts_and_the_test(self, rules):
        assert rules["count"] == 2
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
        # A delay saves only when it is one the server takes.
        assert "if (draft === undefined || delayProblem(draft)) return;" in steps
        assert 'handle: ".grip",' in steps

    def test_the_picker(self):
        picker = _flat("ir-group-picker.ts")
        assert "pickerView(this._devices, this._query, this._open)" in picker
        assert "countInGroup(device.id, this.steps)" in picker
        assert 'if (this.replace) this._close();' in picker
        assert 't("group.reason_no_blaster")' in picker

    def test_the_api(self):
        api = _flat("api.ts")
        for door in ("group/create", "group/steps", "group/candidates", "group/used-by"):
            assert f'type: "hair/command/{door}"' in api


class TestTheStrings:
    def test_every_locale_has_every_key_with_its_placeholders(self):
        en = _locale("en")
        keys = [k for k in en if k.startswith("group.")]
        assert len(keys) >= 50
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
        assert en["group.delay_floor"].startswith("{ms} ms or more. HAIR waits")
        assert en["group.reason_rolling"] == "Rolling code, never sent"
        assert en["group.reason_no_blaster"] == "No blaster set"
