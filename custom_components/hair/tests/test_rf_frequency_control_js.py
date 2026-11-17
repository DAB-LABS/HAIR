"""The shared radio frequency control.

- One control for every place HAIR asks for a radio frequency: the band
  pills, then an Other field with "e.g. 433.92" and a list of common
  bands, typing anything still allowed.
- The Other field wears the picked blue when it holds the frequency.
- A click on the band already picked, or typing the value already held,
  is no change, so a row's frequency source never flips to the user's
  for nothing.
- "Set by you." is gone; the other "where it came from" lines stay.

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
import { mhzToHz, sourceKey } from "./rf-code.js";
import { RF_SUGGESTIONS_MHZ, frequencyChange, otherHolds, typedFor } from "./rule.js";

console.log(JSON.stringify({
    change: [
        frequencyChange(433920000, 433920000),
        frequencyChange(433920000, 315000000),
        frequencyChange(null, 433920000),
        frequencyChange(433920000, null),
        frequencyChange(418000000, mhzToHz("418")),
        frequencyChange(418000000, mhzToHz("418.0")),
    ],
    holds: [otherHolds(433920000), otherHolds(315000000), otherHolds(418000000), otherHolds(null)],
    typed: [
        typedFor(418000000, ""),
        typedFor(433920000, "418"),
        typedFor(433900000, "433.9"),
        typedFor(null, "43x"),
        typedFor(null, "433.92"),
    ],
    suggestions: RF_SUGGESTIONS_MHZ,
    suggestionsRead: RF_SUGGESTIONS_MHZ.map((m) => mhzToHz(m)),
    sources: ["signal", "window", "receiver", "user", "assumed"].map(sourceKey),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("freqcontrol")
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


class TestNoChangeIsNoChange:
    def test_the_band_already_picked_is_no_change(self, run):
        same, other, first, nothing, typed_same, typed_same_again = run["change"]
        assert same is None
        assert other == 315_000_000
        assert first == 433_920_000
        assert nothing is None
        # Typing the value already held, however it is written.
        assert typed_same is None and typed_same_again is None


class TestTheOtherField:
    def test_it_holds_the_frequency_only_off_the_band_pills(self, run):
        assert run["holds"] == [False, False, True, False]

    def test_what_it_shows(self, run):
        # An odd band shows its MHz; a band pill empties the field; what
        # is being typed stays while it means the frequency; half-typed
        # text stays until something sets the frequency.
        assert run["typed"] == ["418", "", "433.9", "43x", ""]

    def test_the_suggestions_are_the_ruled_list_and_all_read(self, run):
        assert run["suggestions"] == [
            "300", "303.875", "310", "315", "390", "418", "433.42", "433.92", "868.35", "915",
        ]
        assert all(isinstance(hz, int) for hz in run["suggestionsRead"])

    def test_the_picked_look_is_the_band_pills_blue(self):
        css = " ".join(_read("rf-frequency-control.ts").split())
        assert ".preset.on, .other input.on { border-color: #03a9f4;" in css
        assert 'class="${this._invalid ? "invalid" : ""} ${holds ? "on" : ""}"' in css

    def test_the_list_and_the_placeholder(self):
        text = _read("rf-frequency-control.ts")
        assert 'list="rf-bands"' in text and '<datalist id="rf-bands">' in text
        assert 'placeholder=${t("rfedit.other_placeholder")}' in text


class TestTheLineUnderFrequency:
    def test_set_by_you_is_gone_the_rest_stay(self, run):
        assert run["sources"] == [
            "rfedit.source_signal", "rfedit.source_window", "rfedit.source_receiver",
            None, "rfedit.source_assumed",
        ]

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "rfedit.source_user" not in data, path.name
        placeholder = data.get("rfedit.other_placeholder")
        assert placeholder and "433.92" in placeholder, path.name
        assert "—" not in placeholder, path.name


class TestTheRadioEditorUsesIt:
    def test_the_frequency_block_is_the_control(self):
        text = _read("ir-rf-editor.ts")
        block = text.split("private _renderFrequency() {", 1)[1].split("\n    }\n", 1)[0]
        assert "<hair-frequency-control" in block
        assert ".valueHz=${this._frequencyHz}" in block
        assert '<div class="freq-note' in block
        assert "RF_PRESETS_HZ" not in text and "_onTyped" not in text and "_pick(" not in text

    def test_one_change_handler_marks_the_users(self):
        text = _read("ir-rf-editor.ts")
        on = text.split("private _onFrequency(hz: number): void {", 1)[1].split("\n    }", 1)[0]
        for line in (
            'this._frequencySource = "user";',
            "this._frequencyChanged = true;",
            "this._codeFollows(hz);",
        ):
            assert line in on, line

    def test_save_still_waits_for_a_readable_frequency(self):
        text = _read("ir-rf-editor.ts")
        assert "@state() private _typedInvalid = false;" in text
        assert "(this._typedInvalid = e.detail.invalid)" in text
        assert "if (this._busy || this._validating || this._typedInvalid) return false;" in text
