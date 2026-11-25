""""Other..." takes only what the receiver accepts.

A typed frequency outside the receiver's ``accepts`` (its declared ranges,
or else its number's own limits) is refused in the box before anything is
sent: it stays there, outlined red, and the line under it says what the
receiver takes. A common band it doesn't accept is greyed and can't be
picked. The empty box's hint is what it accepts.

The rule runs under node with the repo's TypeScript (skipped without the
toolchain); the source pins run everywhere.
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
import { acceptedHz } from "./control.js";
const rm4 = [[305000000, 335000000], [433420000, 438000000]];
console.log(JSON.stringify({
    rm4: [390000000, 315000000, 433920000, 335000000, 305000000, 340000000].map(
        (hz) => acceptedHz(rm4, hz)),
    none: acceptedHz([], 1),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_read(name).split())


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("otheronly")
    src = _read("rf-frequency-control.ts")
    rules = src[src.index("/** The bands the Other field offers"):src.index("@customElement(")]
    (out / "control.ts").write_text(
        'import { hzToMhz, mhzToHz, presetOf } from "./rf-code.js";\n' + rules, encoding="utf-8"
    )
    shutil.copy(SRC / "rf-code.ts", out / "rf-code.ts")
    subprocess.run(
        [
            str(TSC), str(out / "control.ts"), str(out / "rf-code.ts"),
            "--module", "esnext", "--target", "es2022", "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheRule:
    def test_in_and_out_of_two_ranges(self, run):
        # 390 sits between the RM4 Pro's two ranges; the ends count.
        assert run["rm4"] == [False, True, True, True, True, False]

    def test_no_ranges_is_no_check(self, run):
        assert run["none"] is True


class TestTheBox:
    def test_enter_refuses_and_keeps_the_value(self):
        body = _flat("rf-frequency-control.ts").split("private _onListKey(", 1)[1]
        body = body.split("} else if (e.key === \"Escape\")", 1)[0]
        assert (
            "if (!acceptedHz(this.accepts, hz)) { // Refused before anything is sent: the value "
            "stays, red, // and the host says what the receiver takes. this._listInvalid = true; "
            'this._fire("frequency-refused", { hz }); return; }'
        ) in body
        # Refused before frequency-pick, and the typed text is not cleared.
        assert body.index("frequency-refused") < body.index('this._fire("frequency-pick"')

    def test_red_as_you_type(self):
        body = _flat("rf-frequency-control.ts").split("private _onListInput(", 1)[1]
        body = body.split("private _onListKey(", 1)[0]
        assert "const refused = hz !== null && !acceptedHz(this.accepts, hz);" in body
        assert 'if (!refused) this._fire("frequency-refused", { hz: null });' in body

    def test_the_hint_is_what_it_accepts(self):
        control = _flat("rf-frequency-control.ts")
        assert 'placeholder=${this.otherHint || t("rfedit.other_placeholder")}' in control
        tune = _flat("ir-listen-tune.ts")
        assert '.otherHint=${rangesText(accepts, "or", lang)}' in tune
        assert "width:${Math.min(this.otherHint.length + 1, 30)}ch" in control

    def test_a_blocked_band_cannot_be_picked_or_reached(self):
        control = _flat("rf-frequency-control.ts")
        assert "?disabled=${this.disabled || row.blocked === true}" in control
        assert 'aria-disabled=${row.blocked ? "true" : "false"}' in control
        assert 'querySelectorAll<HTMLElement>(".row:not(:disabled)")' in control

    def test_the_refused_line_shows_under_the_box(self):
        tune = _flat("ir-listen-tune.ts")
        assert "const note = tuneNote(this._refused, this._result, lang);" in tune
        assert "@frequency-refused=${(e: CustomEvent<{ hz: number | null }>) => {" in tune

    def test_the_door_refusing_says_the_same(self):
        tune = _flat("ir-listen-tune.ts")
        assert 'if (result.result === "not_accepted") {' in tune
        # A typed value, or the number's own option by what it holds.
        assert (
            '"hz" in pick ? pick.hz : (this.tuning?.presets.find((p) => p.option === pick.option)'
            "?.hz ?? null);"
        ) in tune

    def test_sending_frequencies_are_untouched(self):
        # The radio editor's pills form has no accepts and no refusal.
        pills = _flat("rf-frequency-control.ts").split("private _renderPills()", 1)[1]
        assert "accepts" not in pills and "frequency-refused" not in pills


class TestTheWords:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.tune_refused"] == (
            "This receiver doesn't take {mhz} MHz. It takes {ranges} MHz."
        )
        assert en["listen.tune_band_refused"] == "This receiver doesn't take {mhz} MHz."
        assert en["listen.tune_range"] == "{low} to {high}"

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("listen.tune_refused", "listen.tune_band_refused",
                    "listen.tune_range"):
            assert data.get(key), (path.name, key)
            assert "\u2014" not in data[key], (path.name, key)
        assert "{mhz}" in data["listen.tune_refused"] and "{ranges}" in data["listen.tune_refused"]
        assert "{low}" in data["listen.tune_range"] and "{high}" in data["listen.tune_range"]
        assert "listen.tune_outside" not in data
