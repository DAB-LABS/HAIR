"""The radio editor takes the infrared editor's look (owner, 2026-11-15;
docs/internal/plans/radio-editor-matches-ir-editor.md and the kickoff
ir-2026-11-15-kickoff-gertrude-radio-editor.md).

- One shared code box (ir-code-box-styles.ts): the copper focus edge,
  the fit-to-content height, and the copy icon in a strip above the
  text, so a box long enough to scroll never puts its scrollbar under
  the icon.
- The radio editor's order: the code label and box, the strip, the pill
  row, then Frequency, Name and Send times. No "Radio" glyph line.
- The strip always shown: the saved code is read once on open.
- The diamonds, in the strip and on command and trigger rows, from the
  server's ``sl_pattern``, in the shared diamond tokens.

The infrared editor's own tests are untouched: that is the proof only
its styles moved. The sizing rule runs under node; the rest are source
pins.
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


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_read(name).split())


@pytest.fixture(scope="module")
def heights(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("codebox")
    # The module imports lit for its styles; compile only the pure rule.
    src = _read("ir-code-box-styles.ts")
    rule = src[src.index("/** What the wrapper adds around the textarea"):]
    dom = rule[rule.index("/** Fit a code box"):rule.index("/** The textarea's height")]
    rule = rule.replace(dom, "")
    (out / "rule.ts").write_text(rule, encoding="utf-8")
    subprocess.run(
        [str(TSC), str(out / "rule.ts"), "--module", "esnext", "--target", "es2022",
         "--skipLibCheck", "--outDir", str(out)],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    driver = (
        'import { codeBoxHeight } from "./rule.js";\n'
        "console.log(JSON.stringify(["
        "codeBoxHeight(10, 64, 400), codeBoxHeight(200, 64, 400), "
        "codeBoxHeight(900, 64, 400), codeBoxHeight(300, 40, 96)]));\n"
    )
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheSharedCodeBox:
    def test_the_fit_is_the_infrared_rule(self, heights):
        # The whole box (strip and border included) between the floor and
        # the ceiling, as tall as before; the textarea is that less 26.
        assert heights == [38, 200, 374, 70]

    def test_both_editors_load_it_first(self):
        for name in ("ir-signal-editor.ts", "ir-rf-editor.ts"):
            flat = _flat(name)
            assert "codeBoxStyles, feedbackStyles, diamondStyles, css`" in flat, name
            assert "fitCodeBox(ta," in flat, name

    def test_the_infrared_sizing_keeps_its_clamp(self):
        text = _read("ir-signal-editor.ts")
        sizing = text.split("updated(): void {", 1)[1].split("\n    }", 1)[0]
        assert "const maxPx = held ? 96 : Math.round(window.innerHeight * 0.45);" in sizing
        assert "fitCodeBox(ta, minPx, maxPx);" in sizing

    def test_the_icon_has_its_own_strip(self):
        css = _read("ir-code-box-styles.ts")
        wrap = css.split(".code-wrap {", 1)[1].split("}", 1)[0]
        assert "padding-top: 24px;" in wrap
        assert "border: 1px solid var(--divider-color);" in wrap
        box = css.split(".code-wrap textarea {", 1)[1].split("}", 1)[0]
        assert "border: none;" in box and "overflow-y: auto;" in box
        assert "padding: 0 8px 8px;" in box
        assert ".code-wrap:focus-within {" in css

    def test_the_editors_carry_no_copy_of_it(self):
        for name in ("ir-signal-editor.ts", "ir-rf-editor.ts"):
            text = _read(name)
            styles = text.split("static styles", 1)[1]
            assert ".copy-icon {" not in styles, name
            assert ".code-wrap {" not in styles, name
            assert ".diamond.long {" not in styles, name

    def test_the_held_and_flash_looks_reach_the_wrapper(self):
        text = _read("ir-signal-editor.ts")
        assert ".code-wrap:has(> textarea.held) {" in text
        assert ".code-wrap:has(> textarea.snap-flash) {" in text


class TestTheRadioOrder:
    def test_box_strip_then_frequency_name_count(self):
        # The pill is inside the strip now (owner, 2026-11-16), so the
        # strip is followed directly by Frequency.
        render = _read("ir-rf-editor.ts").split("    render() {", 1)[1]
        order = [
            'id="rf-code"',
            "this._renderFeedback()",
            "this._renderFrequency()",
            'id="rf-name"',
            'id="rf-count"',
        ]
        at = [render.index(mark) for mark in order]
        assert at == sorted(at)
        between = render[
            render.index("this._renderFeedback()"):render.index("this._renderFrequency()")
        ]
        assert "_renderFamily" not in between and "pill" not in between

    def test_the_radio_glyph_line_is_gone(self):
        text = _read("ir-rf-editor.ts")
        assert 'class="medium"' not in text
        assert "rfedit.radio" not in text
        assert "renderProtoGlyph" not in text

    def test_the_label(self):
        assert 't("rfedit.code")' in _read("ir-rf-editor.ts")


class TestTheStrip:
    def test_the_saved_code_is_read_on_open(self):
        text = _read("ir-rf-editor.ts")
        first = text.split("firstUpdated(): void {", 1)[1].split("\n    }", 1)[0]
        assert "if (!this._creating && this._code.trim()) {" in first
        assert "void this._validate();" in first

    def test_reading_on_open_changes_nothing_of_the_row(self):
        text = _read("ir-rf-editor.ts")
        validate = text.split("private async _validate()", 1)[1].split("\n    private", 1)[0]
        guard = validate.index("if (!this._codeChanged) {")
        bring = validate.index("if (result.ok && result.frequency_hz && !this._frequencyChanged)")
        assert guard < bring
        assert "this._initialValidation = result;" in validate

    def test_undoing_an_edit_brings_the_strip_back(self):
        text = _read("ir-rf-editor.ts")
        on_code = text.split("private _onCode(e: Event): void {", 1)[1].split("\n    }", 1)[0]
        assert "this._validation = this._initialValidation;" in on_code

    def test_an_edit_drops_any_read_in_flight(self):
        # The open-read must never land on an edited code (review).
        text = _read("ir-rf-editor.ts")
        on_code = text.split("private _onCode(e: Event): void {", 1)[1].split("\n    }\n", 1)[0]
        assert on_code.index("this._asked++;") < on_code.index("if (!this._codeChanged) {")
        # Undo before the open-read came back asks again.
        assert "void this._validate();" in on_code

    def test_a_band_button_moves_the_strip_too(self):
        text = _read("ir-rf-editor.ts")
        follows = text.split("private _codeFollows(hz: number): void {", 1)[1]
        follows = follows.split("\n    private", 1)[0]
        unedited = follows.split("if (!pasted) {", 1)[1].split("return;", 2)
        body = unedited[0] + unedited[1]
        assert "{ ...this._validation, frequency_hz: hz }" in body
        assert "{ ...this._initialValidation, frequency_hz: hz }" in body
        assert "this._asked++;" in body

    def test_valid_and_refused(self):
        flat = _flat("ir-rf-editor.ts")
        strip = flat.split("private _renderFeedback() {", 1)[1]
        strip = strip.split("private _renderFrequency()", 1)[0]
        ok = '<div class="status ok"><span class="mark">✓</span>${t("rfedit.valid")}</div>'
        bad = '<div class="status bad"><span class="mark">✗</span>${t("editor.not_valid")}</div>'
        assert ok in strip and bad in strip
        assert 't("rfedit.mhz", { mhz: hzToMhz(v.frequency_hz) })' in strip
        assert 't("rfedit.one_frame")' in strip and 't("rfedit.frames_agree"' in strip
        assert "v.sl_pattern" in strip and 'class="diamond long"' in strip


def _identity(text: str) -> str:
    start = text.index("private _renderIdentity(v: ProntoValidation)")
    return text[start:text.index("private _renderFeedback()")]


class TestTheIdentityInTheBox:
    """Owner, 2026-11-16, at #274's look on VM999: the code's identity
    lives inside the validation box, once, in both editors. No "Recognized
    as" sentence and no second pill under the box."""

    def _ir(self) -> str:
        return _read("ir-signal-editor.ts")

    def test_the_infrared_pill_is_on_the_info_line(self):
        text = self._ir()
        feedback = text[text.index("private _renderFeedback() {"):]
        metrics = feedback[feedback.index('<div class="metrics">'):]
        metrics = metrics[:metrics.index("</div>")]
        assert "${this._renderIdentity(v)}" in metrics

    def test_no_sentence_and_no_second_pill(self):
        text = self._ir()
        assert 'class="recognized"' not in text
        assert "_renderPill" not in text
        assert 'class="pill-row"' not in text
        # One pill in the whole editor: the one inside the box.
        assert text.count("<ir-protocol-chip") == 1

    def test_the_command_pill_stays_live(self):
        # The NEC/PRONTO send toggle on a device command keeps working,
        # with the chip's own tooltip.
        text = self._ir()
        body = _identity(text)
        assert "?interactive=${this._isCommand}" in body
        assert "?bypass=${this._isCommand && this._bypass}" in body
        assert "@toggle-bypass=" in body
        assert "this._bypass = e.detail.bypass;" in body
        assert "void this._refreshSpacingInfo();" in body
        assert "(v.recognized_protocol ?? this.initialDecodedProtocol)" in body

    def test_a_screen_reader_still_hears_the_sentence(self):
        text = self._ir()
        body = _identity(text)
        assert 'role="group"' in body
        assert 'aria-label=${t("editor.recognized_as", { protocol })}' in body

    def test_unrecognized_shows_no_pill(self):
        text = self._ir()
        body = _identity(text)
        assert 'if (!protocol) return "";' in body

    def test_the_radio_pill_stays_read_only(self):
        rf = _read("ir-rf-editor.ts")
        body = rf.split("private _renderFamily() {", 1)[1].split("\n    }", 1)[0]
        assert "interactive" not in body

    def test_the_line_wraps_as_one_piece(self):
        css = _read("ir-code-box-styles.ts")
        metrics = css.split("    .metrics {", 1)[1].split("}", 1)[0]
        assert "flex-wrap: wrap;" in metrics and "align-items: center;" in metrics
        identity = css.split("    .identity {", 1)[1].split("}", 1)[0]
        assert "display: inline-flex;" in identity and "flex-wrap: wrap;" in identity


class TestTheDiamondsEverywhere:
    def test_command_and_trigger_rows_read_the_server_pattern_first(self):
        row = _read("ir-command-row.ts").split("private _renderDiamonds()", 1)[1]
        pronto = 'cmd.protocol?.toUpperCase() !== "PRONTO"'
        assert row.index("if (cmd.sl_pattern)") < row.index(pronto)
        trig = _read("ir-trigger-row.ts").split("private _renderDiamonds()", 1)[1]
        assert trig.index("if (sl_pattern)") < trig.index('protocol?.toUpperCase() !== "PRONTO"')

    def test_the_trigger_dialog_reads_it_in_edit_mode(self):
        assert (
            "const patternStr = isEdit ? (this.trigger!.sl_pattern ?? null) : this.slPattern;"
            in _read("ir-trigger-dialog.ts")
        )

    @pytest.mark.parametrize(
        "name",
        [
            "ir-command-row.ts", "ir-signal-alias.ts", "ir-trigger-dialog.ts",
            "ir-trigger-row-styles.ts", "ir-assign-signal-dialog.ts", "ir-signal-monitor.ts",
            "ir-code-box-styles.ts",
        ],
    )
    def test_one_pair_of_diamond_colours(self, name):
        text = _flat(name)
        assert ".diamond.long { color: ${DIAMOND_LONG_VAR}; }" in text, name
        assert ".diamond.short { color: ${DIAMOND_SHORT_VAR}; }" in text, name

    def test_the_tokens_keep_the_infrared_colours(self):
        colors = _read("hair-colors.ts")
        assert 'export const DIAMOND_LONG = "var(--primary-color)";' in colors
        assert 'export const DIAMOND_SHORT = "var(--warning-color, #ff9800)";' in colors
        tokens = _read("ir-header-chip-styles.ts").split("export const hairTokens = css`", 1)[1]
        assert "--hair-diamond-long: ${unsafeCSS(DIAMOND_LONG)};" in tokens
        assert "--hair-diamond-short: ${unsafeCSS(DIAMOND_SHORT)};" in tokens


class TestTheStrings:
    def test_eleven_locales(self):
        for path in sorted(LOCALES.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data.get("rfedit.valid"), path.name
            assert ".sub" in data["rfedit.code"] and "Broadlink" in data["rfedit.code"], path.name
            assert "rfedit.radio" not in data, path.name
            for key in ("rfedit.valid", "rfedit.code"):
                assert "—" not in data[key], (path.name, key)
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["rfedit.code"] == "Code: Flipper .sub, timings or Broadlink"
        assert en["rfedit.valid"] == "Valid radio code"
