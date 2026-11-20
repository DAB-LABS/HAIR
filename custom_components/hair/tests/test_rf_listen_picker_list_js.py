"""The listening picker as a list, and the menu that holds on to it.

- A click on the number on a radio receiver's pill opens a list of the
  common bands in order, the current one marked, values outside the
  receiver's range greyed but still a pick. One click picks and closes.
- The last row, "Other...", turns into a field in place. Nothing is set
  while typing; Enter sets it, Escape goes back to the row. Typing a
  digit used to set a frequency at once, which disabled the field under
  the cursor and lost it.
- The menu follows its box when the page scrolls or the window resizes
  (a phone's keyboard), and the Sniffer's pills are keyed by receiver.
- A receiver with one fixed frequency shows it; a pick says HAIR can't
  tune it.
- The radio editor keeps its band pills and Other field.

The rules run under node (skipped without the toolchain); the source
pins run everywhere.
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

DRIVER = r"""
import { listBands, outsideRange } from "./rule.js";

console.log(JSON.stringify({
    bands: [listBands(null), listBands(433920000), listBands(345000000)],
    outside: [
        outsideRange(915000000, 300000000, 400000000),
        outsideRange(310000000, 300000000, 400000000),
        outsideRange(250000000, 300000000, null),
        outsideRange(915000000, null, null),
    ],
}));
"""

ALL = [
    300000000, 303875000, 310000000, 315000000, 390000000, 418000000,
    433420000, 433920000, 868350000, 915000000,
]


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("pickerlist")
    src = _read("rf-frequency-control.ts")
    rules = src[src.index("/** The bands the Other field offers"):src.index("@customElement(")]
    head = 'import { hzToMhz, mhzToHz, presetOf } from "./rf-code.js";\n'
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


class TestTheList:
    def test_every_common_band_in_order(self, run):
        none, held, _odd = run["bands"]
        assert none == ALL and held == ALL

    def test_an_odd_current_band_takes_its_place(self, run):
        assert run["bands"][2] == sorted([*ALL, 345000000])

    def test_outside_the_range_is_greyed_only_when_known(self, run):
        assert run["outside"] == [True, False, True, False]

    def test_the_list_form(self):
        control = _read("rf-frequency-control.ts")
        assert '@property() public form: "pills" | "list" = "pills";' in control
        assert 'return this.form === "list" ? this._renderList() : this._renderPills();' in control
        assert 'class="list" role="listbox"' in control
        assert 'class="row ${on ? "on" : ""} ${dim ? "dim" : ""}"' in control
        assert 'this._fire("frequency-done", {});' in control


class TestOther:
    def _control(self) -> str:
        return _read("rf-frequency-control.ts")

    def test_typing_sets_nothing(self):
        body = self._control().split("private _onListInput(e: Event): void {", 1)[1]
        body = body.split("\n    }\n", 1)[0]
        assert "frequency-changed" not in body and "_pick(" not in body

    def test_enter_sets_it_and_escape_goes_back(self):
        body = self._control().split("private _onListKey(e: KeyboardEvent): void {", 1)[1]
        body = body.split("\n    }\n", 1)[0]
        assert 'if (e.key === "Enter") {' in body and "this._pick(hz);" in body
        assert 'e.key === "Escape"' in body and "e.stopPropagation();" in body

    def test_the_row_opens_the_field_in_place(self):
        control = self._control()
        assert '<button class="row other-row"' in control
        assert '${t("listen.tune_other")}' in control
        assert '.row.other-field input")?.focus()' in control


class TestTheMenu:
    def _tune(self) -> str:
        return _read("ir-listen-tune.ts")

    def test_it_uses_the_list_form(self):
        tune = self._tune()
        assert 'form="list"' in tune
        # The rows come from the receiver's own description.
        assert ".rows=${menu.rows}" in tune

    def test_a_pick_closes_it(self):
        tune = self._tune()
        assert "@frequency-done=${() => {" in tune
        body = tune.split("private async _tune(pick: TunePick): Promise<void> {", 1)[1]
        body = body.split("\n    }\n", 1)[0]
        assert "if (this._pendingOutside) this._open(\"note\");" in body
        assert "else this._close();" in body
        assert "if (tuneNote(false, result)) this._showNote();" in body

    def test_scroll_and_resize_follow_the_box(self):
        body = self._tune().split("private _away = () => {", 1)[1].split("\n    };\n", 1)[0]
        assert "this._panel = this._placeFor(box);" in body
        assert "box.bottom < 0 || box.top > window.innerHeight" in body

    def test_the_pills_are_keyed_by_receiver(self):
        row = _read("ir-listen-row.ts")
        assert 'import { repeat } from "lit/directives/repeat.js";' in row
        assert "(row) => row.receiver_entity_id," in row

    def test_a_fixed_receiver(self):
        types = _read("types.ts")
        block = types.split("export interface ReceiverTuning {", 1)[1].split("\n}\n", 1)[0]
        assert "fixed?: boolean;" in block


class TestTheEditorKeepsItsPills:
    def test_no_form_given(self):
        editor = _read("ir-rf-editor.ts")
        block = editor.split("<hair-frequency-control", 1)[1]
        block = block.split("></hair-frequency-control>", 1)[0]
        assert "form=" not in block


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("listen.tune_other"), path.name
        assert data["listen.tune_other"].endswith("…"), path.name

    def test_the_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.tune_other"] == "Other…"
