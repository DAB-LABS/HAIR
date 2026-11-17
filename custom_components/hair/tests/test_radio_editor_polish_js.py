"""The code editors' polish: one-click copy, the frames line, the Send times note.

- Copy: the corner icon of both code boxes copies in one click. The
  clipboard API where the page allows it, then the browser's copy
  command inside the same click, and only when both fail the old
  select-all with its Cmd/Ctrl+C hint. The rule runs under node with a
  stub DOM (skipped without the toolchain); the source pins run
  everywhere.
- The frames line: "6 of 8 frames agree; the code was read from those 6."
- The Send times note: two short notes with no number, beside the field
  in the radio editor and under it in the Assign dialog.
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

# A stub DOM just big enough for copy-text.ts: a code box inside its
# container, a document whose copy command answers as each case says,
# and a log of what happened.
DRIVER = r"""
import { copyCodeBox } from "./copy-text.js";

function world({ secure, clipboard, command }) {
    const log = [];
    const doc = {
        activeElement: null,
        createElement(tag) {
            const el = {
                tag, value: "", style: {}, attrs: {},
                setAttribute(k, v) { this.attrs[k] = v; },
                focus() { doc.activeElement = this; log.push("scratch.focus"); },
                select() { log.push("scratch.select:" + this.value); },
                setSelectionRange(a, b) { log.push(`scratch.range:${a}-${b}`); },
                remove() { log.push("scratch.remove"); container.children.pop(); },
            };
            return el;
        },
        execCommand(name) {
            log.push("execCommand:" + name);
            if (command === "throws") throw new Error("not allowed");
            return command;
        },
    };
    const button = { focus() { log.push("button.focus"); } };
    doc.activeElement = button;
    const container = {
        ownerDocument: doc,
        children: [],
        getRootNode() { return doc; },
        appendChild(el) { this.children.push(el); log.push("append:" + el.tag); },
    };
    const box = {
        parentElement: container,
        focus() { log.push("box.focus"); },
        select() { log.push("box.select"); },
    };
    globalThis.window = { isSecureContext: secure };
    let nav = {};
    if (clipboard === "ok") {
        nav = { clipboard: { writeText: async (t) => { log.push("writeText:" + t); } } };
    } else if (clipboard === "refused") {
        nav = { clipboard: { writeText: async (t) => {
            log.push("writeText:" + t); throw new Error("NotAllowedError");
        } } };
    }
    Object.defineProperty(globalThis, "navigator", { value: nav, configurable: true });
    return { log, box, container };
}

async function run(opts) {
    const w = world(opts);
    const copied = await copyCodeBox("Filetype: Flipper SubGhz", w.box);
    return { copied, log: w.log, left: w.container.children.length };
}

const out = {
    https: await run({ secure: true, clipboard: "ok", command: true }),
    http: await run({ secure: false, clipboard: "none", command: true }),
    httpWithApi: await run({ secure: false, clipboard: "ok", command: true }),
    refusedThenCommand: await run({ secure: true, clipboard: "refused", command: true }),
    neither: await run({ secure: false, clipboard: "none", command: false }),
    commandThrows: await run({ secure: false, clipboard: "none", command: "throws" }),
    refusedAndNoCommand: await run({ secure: true, clipboard: "refused", command: false }),
};
console.log(JSON.stringify(out));
"""

TEXT = "Filetype: Flipper SubGhz"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("radioeditorpolishjs")
    subprocess.run(
        [
            str(TSC), "src/copy-text.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--lib", "es2022,dom",
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


# --- copy -------------------------------------------------------------------


class TestOneClickCopy:
    def test_https_uses_the_clipboard_and_selects_nothing(self, run):
        case = run["https"]
        assert case["copied"] is True
        assert case["log"] == [f"writeText:{TEXT}"]

    def test_http_has_no_clipboard_and_uses_the_copy_command(self, run):
        """Plain http: no navigator.clipboard, so the copy command runs at
        once, on a temporary textarea holding the text, inside the box's
        container; it is removed and focus goes back to the button."""
        case = run["http"]
        assert case["copied"] is True
        assert case["log"] == [
            "append:textarea",
            "scratch.focus",
            f"scratch.select:{TEXT}",
            f"scratch.range:0-{len(TEXT)}",
            "execCommand:copy",
            "scratch.remove",
            "button.focus",
        ]
        assert case["left"] == 0

    def test_an_insecure_page_never_calls_the_clipboard_api(self, run):
        case = run["httpWithApi"]
        assert case["copied"] is True
        assert not any(step.startswith("writeText") for step in case["log"])

    def test_a_refused_clipboard_falls_to_the_copy_command(self, run):
        case = run["refusedThenCommand"]
        assert case["copied"] is True
        assert case["log"][0] == f"writeText:{TEXT}"
        assert "execCommand:copy" in case["log"]
        assert "box.select" not in case["log"]

    @pytest.mark.parametrize("name", ["neither", "commandThrows", "refusedAndNoCommand"])
    def test_when_both_fail_the_box_is_selected(self, run, name):
        case = run[name]
        assert case["copied"] is False
        assert case["log"][-2:] == ["box.focus", "box.select"]
        assert case["left"] == 0

    def test_copied_shows_only_on_a_real_copy(self, run):
        assert [run[k]["copied"] for k in sorted(run)] == [
            False, True, True, True, False, False, True,
        ]


class TestBothEditorsUseIt:
    def test_the_radio_editor(self):
        flat = _flat("ir-rf-editor.ts")
        assert 'import { copyCodeBox } from "./copy-text.js";' in flat
        copy = flat.split("private async _copy(): Promise<void> {", 1)[1]
        copy = copy.split("private _requestDelete", 1)[0]
        assert "const copied = await copyCodeBox(text, ta);" in copy
        assert "navigator.clipboard" not in flat and "execCommand" not in flat

    def test_the_infrared_editor(self):
        flat = _flat("ir-signal-editor.ts")
        assert 'import { copyCodeBox } from "./copy-text.js";' in flat
        assert "const copied = await copyCodeBox(this._pronto, ta);" in flat
        assert "@click=${this._copyCode}" in flat
        assert "_selectCode" not in flat
        assert "navigator.clipboard" not in flat and "execCommand" not in flat

    @pytest.mark.parametrize("name", ["ir-rf-editor.ts", "ir-signal-editor.ts"])
    def test_the_icon_says_copy(self, name):
        flat = _flat(name)
        assert 'title=${t("editor.copy_code")} aria-label=${t("editor.copy_code")}' in flat
        assert 't("editor.copied") : t("editor.press_copy")' in flat

    def test_select_all_is_gone_from_the_panel(self):
        for path in SRC.rglob("*.ts"):
            assert "editor.select_all" not in path.read_text(encoding="utf-8"), path.name

    def test_the_scratch_textarea_goes_inside_the_dialog(self):
        """Outside a modal dialog everything is inert, so the temporary
        textarea is appended to the code box's own container."""
        flat = _flat("copy-text.ts")
        assert "const container = box?.parentElement;" in flat
        assert "container.appendChild(scratch);" in flat
        assert "document.body" not in flat


# --- the frames line and the Send times note --------------------------------


class TestTheRadioEditorLines:
    def test_the_frames_line_names_the_count_twice(self):
        flat = _flat("ir-rf-editor.ts")
        assert (
            '${t("rfedit.frames_agree", { agreeing: String(agreeing), found: String(found) })}'
        ) in flat

    def test_the_note_sits_beside_the_field_and_wraps(self):
        flat = _flat("ir-rf-editor.ts")
        row = flat.split('<div class="knob-row">', 1)[1].split("${this.hasTrigger", 1)[0]
        assert row.index('<input id="rf-count"') < row.index("${this._countNote()}")
        assert (
            ".knob-row { display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap; }"
        ) in flat
        assert "count-hint" not in flat

    def test_no_note_once_the_number_changes(self):
        flat = _flat("ir-rf-editor.ts")
        assert 'const key = sendTimesHint("rf", this.repeatsObserved, this._sendCount);' in flat
        assert 'return key ? html`<span class="count-note">${t(key)}</span>` : nothing;' in flat


NEW_KEYS = ("rfedit.send_times_note_measured", "rfedit.send_times_note_usual", "editor.copy_code")
OLD_KEYS = ("rfedit.send_times_measured", "rfedit.send_times_usual", "editor.select_all")


class TestTheWords:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["rfedit.frames_agree"] == (
            "{agreeing} of {found} frames agree; the code was read from those {agreeing}."
        )
        assert en["rfedit.send_times_note_measured"] == "As the remote sent it"
        assert en["rfedit.send_times_note_usual"] == "Usual for this kind of remote"
        assert en["editor.copy_code"] == "Copy"

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        frames = data["rfedit.frames_agree"]
        assert frames.count("{agreeing}") == 2 and frames.count("{found}") == 1
        for key in NEW_KEYS:
            assert data.get(key), key
            assert "{" not in data[key], key
        for key in (*NEW_KEYS, "rfedit.frames_agree"):
            assert "\u2014" not in data[key], key
        for key in OLD_KEYS:
            assert key not in data, key

    def test_eleven_locales(self):
        assert len(list(LOCALES.glob("*.json"))) == 11
