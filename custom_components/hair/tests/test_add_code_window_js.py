"""The Clipper's one add window for infrared and radio codes.

- One "+ Add Signal" button opens one window (ir-add-code-dialog.ts).
  Inside it the infrared or the radio editor is shown, whichever the
  server says the paste is (``medium`` on both validate doors), and the
  text moves with it.
- The empty box shows a hint drawn from one table of formats per medium
  (paste-formats.ts), the table ``paste_medium.PASTE_FORMATS`` also
  holds; test_paste_medium.py checks the two agree.
- The empty clipped remote points at that button and lists the same
  format lines (``formatLines``), so a new format shows in both.
- In the window the editors use its words: "Code: Infrared or Radio",
  "Valid IR" and "Valid RF", "Not a code HAIR reads.", and
  their medium's fields only once the code is read.

The rules run under node; the wiring is pinned in the source.
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


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


def _locale(lang: str) -> dict:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rules(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("addcode")
    (out / "rule.ts").write_text((SRC / "paste-formats.ts").read_text(encoding="utf-8"),
                                 encoding="utf-8")
    subprocess.run(
        [str(TSC), str(out / "rule.ts"), "--module", "esnext", "--target", "es2022",
         "--skipLibCheck", "--outDir", str(out)],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    words = {lang: _locale(lang) for lang in ("en", "fr")}
    driver = (
        'import { editorFor, formatLines, hintLines } from "./rule.js";\n'
        f"const WORDS = {json.dumps(words, ensure_ascii=False)};\n"
        "const tr = (lang) => (key, subs) => {\n"
        "  let s = WORDS[lang][key] ?? key;\n"
        "  for (const [k, v] of Object.entries(subs ?? {})) s = s.split('{' + k + '}').join(v);\n"
        "  return s;\n"
        "};\n"
        "console.log(JSON.stringify({\n"
        "  editor: [\n"
        "    editorFor('ir', 'rf'), editorFor('ir', 'either'), editorFor('ir', 'ir'),\n"
        "    editorFor('ir', null), editorFor('rf', 'ir'), editorFor('rf', null),\n"
        "    editorFor('rf', undefined), editorFor('rf', 'either'),\n"
        "  ],\n"
        "  en: hintLines(tr('en')),\n"
        "  fr: hintLines(tr('fr')),\n"
        "  lines: formatLines(tr('en')),\n"
        "}));\n"
    )
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheRules:
    def test_the_editor_follows_the_server(self, rules):
        # Radio for "rf" and for a list of timings; infrared for "ir";
        # text that is no code stays where it is.
        assert rules["editor"] == ["rf", "rf", "ir", "ir", "ir", "rf", "rf", "rf"]

    def test_the_hint_is_one_line_per_medium(self, rules):
        assert rules["en"] == [
            "Paste a code here. HAIR reads:",
            "Infrared: Pronto, Broadlink, Tuya, Global Cache, Tasmota",
            "Radio: Flipper .sub, Broadlink, raw timings",
        ]

    def test_only_the_words_are_translated(self, rules):
        assert rules["fr"][1] == (
            "Infrarouge : Pronto, Broadlink, Tuya, Global Cache, Tasmota"
        )
        # Format names, "raw timings" among them, are not translated.
        assert rules["fr"][2] == "Radio : Flipper .sub, Broadlink, raw timings"


    def test_the_empty_remote_lists_the_same_lines(self, rules):
        assert rules["lines"] == rules["en"][1:]


class TestTheWiring:
    def test_one_button_opens_the_window(self):
        clips = _flat("ir-clips.ts")
        assert clips.count('class="create-signal-btn"') == 1
        assert "clips.add_rf_signal" not in clips
        assert "html`<ir-add-code-dialog" in clips

    def test_the_empty_remote_points_at_the_button(self):
        clips = _flat("ir-clips.ts")
        assert '${t("clips.no_signals")}' in clips
        assert "${formatLines(t).map(" in clips
        en = _locale("en")
        assert en["clips.no_signals"] == (
            'No signals yet. Click "+ Add Signal" to paste a code. HAIR reads:'
        )

    def test_the_window_swaps_on_the_servers_word(self):
        window = _flat("ir-add-code-dialog.ts")
        assert "const next = editorFor(this._medium, e.detail.medium);" in window
        assert "html`<ir-signal-editor embedded" in window
        assert "html`<ir-rf-editor embedded" in window
        assert ".initialPronto=${this._text}" in window
        assert ".initialCode=${this._text}" in window
        # The name typed before the paste goes along too.
        assert ".initialAlias=${this._alias}" in window
        # Only the editor shown now may hand over.
        assert "if (e.target !== shown) return;" in window
        # No title bar: the window looks as the editors do. Its one child
        # never changes; only the editor inside it does.
        assert (
            '<ha-dialog open scrimClickAction="" @closed=${this._close}> '
            '<div class="body">${keyed('
        ) in window

    @pytest.mark.parametrize("name,reader", [
        ("ir-signal-editor.ts", 'editorFor("ir", v?.medium) !== "ir"'),
        ("ir-rf-editor.ts", 'editorFor("rf", result.medium) !== "rf"'),
    ])
    def test_each_editor_hands_the_other_medium_back(self, name, reader):
        editor = _flat(name)
        assert reader in editor
        assert 'new CustomEvent("medium-changed"' in editor
        assert "alias: this._alias }" in editor
        assert "if (this.embedded) return body;" in editor

    def test_the_windows_words(self):
        ir = _flat("ir-signal-editor.ts")
        rf = _flat("ir-rf-editor.ts")
        assert 't(this.embedded ? "addcode.valid_ir" : "editor.valid")' in ir
        assert 't(this.embedded ? "addcode.valid_rf" : "rfedit.valid")' in rf
        for editor in (ir, rf):
            assert '"addcode.code_label"' in editor
            assert 't("addcode.unreadable")' in editor


class TestTheStrings:
    KEYS = (
        "addcode.code_label", "addcode.valid_ir", "addcode.valid_rf",
        "addcode.unreadable", "addcode.hint_lead", "addcode.hint_line",
        "addcode.medium_ir", "addcode.medium_rf",
        "clips.add_signal", "clips.add_signal_title", "clips.no_signals",
    )

    def test_the_english_words(self):
        en = _locale("en")
        assert en["addcode.code_label"] == "Code: Infrared or Radio"
        assert (en["addcode.valid_ir"], en["addcode.valid_rf"]) == (
            "Valid IR", "Valid RF",
        )
        assert en["addcode.unreadable"] == "Not a code HAIR reads."
        assert en["clips.add_signal"] == "+ Add Signal"

    def test_in_every_language_and_the_radio_button_is_gone(self):
        for path in LOCALES.glob("*.json"):
            words = json.loads(path.read_text(encoding="utf-8"))
            for key in self.KEYS:
                assert words.get(key), (path.name, key)
                assert "—" not in words[key], (path.name, key)
            assert "{medium}" in words["addcode.hint_line"], path.name
            assert "{formats}" in words["addcode.hint_line"], path.name
            assert "clips.add_rf_signal" not in words, path.name
            assert "addcode.format_timings" not in words, path.name
            assert "clips.add_rf_signal_title" not in words, path.name
