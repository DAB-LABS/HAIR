"""Source guards for the 2026-08-02 bench pass.

Every assertion here stands for a defect found on the bench that the
type checker cannot see: a control with no way to close it, a tooltip
promising a click the surface refuses, a reserved slot that was never
reserved. They read the TypeScript rather than run it, which is the
same tactic test_locales.py already uses for the panel source -- cheap,
and enough to catch a regression that would otherwise only show up in
a screenshot months later.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "frontend" / "src"
LOCALES = SRC / "locales"
LOCALE_NAMES = (
    "en", "de", "es", "fr", "it", "ja", "nl", "pl", "pt", "ru",
)


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


class TestDittoIsNecOnly:
    """Measured against infrared-protocols, not assumed: NEC appends a
    4-entry repeat frame, Samsung32 and RC-5 duplicate the whole frame,
    Sharp and Sony ignore repeat_count entirely. Only the first is a
    ditto, so only NEC gets the knob."""

    def test_the_predicate_names_nec(self):
        text = _read("ir-tx-knobs.ts")
        assert 'DITTO_PROTOCOL = "NEC"' in text
        assert "export function isDittoable" in text

    def test_bypassed_rows_are_refused_before_the_protocol_check(self):
        text = _read("ir-tx-knobs.ts")
        body = text.split("export function isDittoable", 1)[1]
        body = body.split("}", 1)[0]
        assert "if (bypassed) return false;" in body

    @pytest.mark.parametrize(
        "module", ["ir-fitting-dialog.ts", "ir-signal-editor.ts"],
    )
    def test_both_edit_surfaces_use_the_shared_predicate(self, module):
        """Not a hand-rolled copy in each file: two gates that can
        drift apart is how the fitting came to offer dittos on
        protocols the editor already refused."""
        text = _read(module)
        assert 'from "./ir-tx-knobs.js"' in text
        assert "isDittoable(" in text

    def test_the_fitting_no_longer_gates_on_bare_truthiness(self):
        """The old gate was `!!row.protocol && !row.bypass_protocol`,
        which admitted every decoded protocol."""
        text = _read("ir-fitting-dialog.ts")
        assert "!!row.protocol && !row.bypass_protocol" not in text

    def test_the_display_glyph_is_deliberately_not_gated(self):
        """A stored value hidden is a value nobody can find and
        correct, so the read-only knob still reports what a row
        carries even if it should never have carried it."""
        text = _read("ir-tx-knobs.ts")
        render = text.split("render()", 1)[1]
        assert "const showDittos = dittos > 1 && this.decoded" in render


class TestTuneChipCloses:
    """The FT5 build opened a stepper and had no way back: no
    click-away, no toggle, no Escape. _openChip was assigned in exactly
    one place and cleared in none."""

    def test_click_away_and_escape_are_bound(self):
        text = _read("ir-fitting-dialog.ts")
        assert "_onHostClick" in text
        assert "_onHostKey" in text
        assert 'this.addEventListener("click", this._onHostClick' in text
        assert "removeEventListener" in text

    def test_the_open_chip_is_cleared_somewhere(self):
        text = _read("ir-fitting-dialog.ts")
        assert text.count("_openChip = null") >= 3

    def test_the_stepper_wears_no_pill(self):
        """Expanded, the control is already unmistakably one control;
        the capsule only made a row look permanently edited."""
        text = _read("ir-fitting-dialog.ts")
        block = text.split(".tstep {", 1)[1].split("}", 1)[0]
        assert "background" not in block


class TestRowControlsCannotStagger:
    """Anything variable in the row's flex run moves the fixed controls
    that follow it, and REPLACE drew a staircase down the list."""

    def test_the_result_rides_the_button_that_produced_it(self):
        """Inline it shoved the controls; on a line below it read as
        orphaned, and matrix rows never rendered that line at all. It
        lives on TEST now, and TEST is its own component (owner ruling
        2026-08-02) ahead of the fitting dialog's removal."""
        text = _read("ir-test-button.ts")
        assert "_renderFactsLine" not in _read("ir-fitting-dialog.ts")
        assert 'color="grey"' in text
        assert "testbtn.sent" in text and "testbtn.heard" in text

    def test_the_host_no_longer_owns_the_flash(self):
        """The extraction is only real if the state went with it."""
        host = _read("ir-fitting-dialog.ts")
        for leftover in ("FLASH_HOLD_MS", "_flashTimers", "_flashResult"):
            assert leftover not in host
        assert "<ir-test-button" in host

    def test_the_button_cannot_change_width_when_the_label_changes(self):
        """All three labels laid out in one grid cell, only the active
        one visible. A button that resized would recreate the exact
        staggering this pass removed."""
        text = _read("ir-test-button.ts")
        stack = text.split("\n        .stack {", 1)[1].split("}", 1)[0]
        assert "display: grid" in stack
        lay = text.split("\n        .lay {", 1)[1].split("}", 1)[0]
        assert "grid-area: 1 / 1" in lay
        assert "visibility: hidden" in lay

    def test_the_hold_is_five_seconds_and_the_timer_is_cleaned_up(self):
        text = _read("ir-test-button.ts")
        assert "FLASH_HOLD_MS = 5000" in text
        disconnect = text.split("disconnectedCallback", 1)[1]
        disconnect = disconnect.split("\n    private", 1)[0]
        assert "_clearTimer()" in disconnect

    def test_the_flash_reports_this_press_not_the_history(self):
        """A row heard once and missed twice must not keep claiming
        HEARD."""
        text = _read("ir-test-button.ts")
        assert 'this._show(heard ? "heard" : "sent");' in text

    def test_the_button_never_claims_the_device_responded(self):
        """Heard means the code went over the air, not that the fan
        spun. The check stays the human's act -- that line is what
        keeps this button from quietly rebuilding the fitting room."""
        text = _read("ir-test-button.ts")
        assert "STATELESS ABOUT PROOF" in text
        # Assert the CONTRACT, not vocabulary: prose about verdicts is
        # fine, an API for recording one is not. Its whole public
        # surface is send / disabledReason / count, and the only event
        # it raises is a failure report.
        props = set(re.findall(r"public (\w+)", text))
        assert props == {"send", "disabledReason", "count"}, props
        body = text.split("*/", 1)[1]
        assert body.count("dispatchEvent") == 1
        assert '"test-failed"' in body

    def test_facts_are_gone_from_the_control_run(self):
        text = _read("ir-fitting-dialog.ts")
        controls = text.split("_renderRowControls", 1)[1]
        controls = controls.split("_rowStateInstruction", 1)[0]
        assert '<span class="facts"' not in controls

    def test_the_tail_is_anchored_right(self):
        text = _read("ir-fitting-dialog.ts")
        assert 'class="row-tail"' in text
        tail = text.split(".row-tail {", 1)[1].split("}", 1)[0]
        assert "margin-left: auto" in tail

    def test_every_row_gets_thumbs(self):
        """A matrix checklist samples 31 of 288 cells, so the other 48
        the comb flagged were rows you could send and repair but never
        tick. No reserved gap is needed any more because no row is
        missing its thumbs (owner ruling 2026-08-02)."""
        text = _read("ir-fitting-dialog.ts")
        assert "thumb-gap" not in text
        body = text.split(
            "private _renderRowControls(i: number) {", 1,
        )[1].split("\n    private ", 1)[0]
        # The suspect CHIP still keys off advisory, correctly -- it is
        # the warning marker. What must not come back is a branch that
        # withholds the verdict buttons.
        assert "advisory" not in body.split("return html", 1)[1]

    def test_the_dialog_widened(self):
        text = _read("ir-fitting-dialog.ts")
        block = text.split(".fit-dialog {", 1)[1].split("}", 1)[0]
        assert "max-width: 680px" in block


class TestRowButtonsAcknowledgeTheMouse:
    """TEST was already gated on an emitter being picked but looked
    identical either way, and nothing in the row answered a hover or a
    press."""

    @pytest.mark.parametrize(
        "selector",
        [".vbtn:hover:not(:disabled)", ".vbtn:active:not(:disabled)",
         ".vbtn:disabled", ".apply-btn:hover:not(:disabled)",
         ".discard-btn:hover:not(:disabled)", ".discard-btn:disabled"],
    )
    def test_state_rule_exists(self, selector):
        assert selector in _read("ir-fitting-dialog.ts")

    def test_discard_is_red_when_it_can_act(self):
        text = _read("ir-fitting-dialog.ts")
        block = text.split(".discard-btn {", 1)[1].split("}", 1)[0]
        assert "--error-color" in block

    def test_apply_is_subordinate_to_the_number_it_acts_on(self):
        """Smaller and tighter than the row's other buttons, or it
        reads as a peer of TEST and REPLACE."""
        text = _read("ir-fitting-dialog.ts")
        apply_block = text.split(".apply-btn {", 1)[1].split("}", 1)[0]
        vbtn_block = text.split("\n            .vbtn {", 1)[1]
        vbtn_block = vbtn_block.split("}", 1)[0]

        def size(block: str) -> float:
            return float(
                re.search(r"font-size:\s*([\d.]+)px", block).group(1)
            )

        assert size(apply_block) < size(vbtn_block)


class TestJudgingSuspectsDoesNotMoveTheArithmetic:
    """Suspects became judgeable, and that is the ONLY thing that
    changed. Combing stamps a receipt without rolling the content hash,
    so a suspect counting toward completeness would let one person's
    comb retroactively demote somebody else's signed PERFECT FIT with
    no code having changed anywhere."""

    def test_the_counter_skips_advisory_verdicts(self):
        """total comes from signals.length, which the backend builds
        with advisory rows already excluded. Counting their verdicts
        gave '35 of 31 tested' and fired PERFECT FIT early."""
        text = _read("ir-fitting-dialog.ts")
        block = text.split("private get _counts()", 1)[1]
        block = block.split("\n    render()", 1)[0]
        assert "advisory" in block
        assert "continue" in block

    def test_the_backend_still_excludes_them_from_the_row_list(self):
        api = (
            SRC.parent.parent / "websocket_api.py"
        ).read_text(encoding="utf-8")
        assert 'row["key"] for row in rows if not row["advisory"]' in api

    def test_advisory_verdicts_are_never_signed(self):
        """The fitting attests the checklist. A signed confirmed list
        naming rows outside it would make the entry's own coverage line
        read past its total."""
        fitting = (
            SRC.parent.parent / "wig_fitting.py"
        ).read_text(encoding="utf-8")
        block = fitting.split("async def async_finish", 1)[1]
        assert "checklist = {spec.key for spec in fitting_row_specs(wig)}" in block
        assert "if k in checklist" in block


class TestMatrixBypassIsRefusedNotDropped:
    """A cell's canonical form is exactly mode/fan/swing/temp/pronto,
    so there is nowhere to put a bypass flag. The write path used to
    accept the argument and drop it: the fitter set the toggle, the
    replace succeeded, and the chip came back still naming the decoded
    protocol."""

    def test_the_api_says_no(self):
        fitting = (
            SRC.parent.parent / "wig_fitting.py"
        ).read_text(encoding="utf-8")
        assert '"code": "bypass_not_supported"' in fitting

    def test_the_dialog_does_not_offer_it_on_a_matrix(self):
        text = _read("ir-fitting-dialog.ts")
        assert "?interactive=${!this._fit?.matrix}" in text


class TestTheChipHasThreeWords:
    """It had two, captured and pasted, chosen with a single ternary
    off `replaced`. A tuned marker has no `replaced` key at all, so it
    fell into the else branch and announced PASTED about a code nobody
    had pasted."""

    def test_the_ternary_is_gone(self):
        text = _read("ir-fitting-dialog.ts")
        chip = text.split("private _renderChip(i: number) {", 1)[1]
        chip = chip.split("\n    private ", 1)[0]
        assert "const tuned = typeof marker.tuned" in chip
        assert "fitting.chip_tuned" in chip

    def test_replaced_is_matched_explicitly_not_by_fallthrough(self):
        text = _read("ir-fitting-dialog.ts")
        chip = text.split("private _renderChip(i: number) {", 1)[1]
        chip = chip.split("\n    private ", 1)[0]
        assert 'marker.replaced === "pasted"' in chip

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_third_word_is_translated(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert data["fitting.chip_tuned"]
        assert "{count}" in data["fitting.chip_tuned_title"]


class TestApplySaysWhyItIsOff:
    """APPLY is deliberately unavailable on a state matrix -- writing a
    send count from a checklist that samples 31 of 288 cells would edit
    cells nothing proved. The hint under it went on describing what it
    would do anyway."""

    def test_the_matrix_hint_replaces_the_normal_one(self):
        text = _read("ir-fitting-dialog.ts")
        assert "fitting.apply_matrix_hint" in text
        assert text.count("fitting.apply_matrix_hint") >= 2

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_it_is_translated(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert data["fitting.apply_matrix_hint"]


class TestReadOnlyChipsDoNotInviteClicks:
    """The decoded tooltip ended "Click to send the captured code
    as-is" on every surface, including the fitting rows, where toggling
    would roll the content hash mid-attestation and is deliberately
    impossible."""

    def test_the_action_half_is_conditional_on_being_live(self):
        text = _read("ir-protocol-chip.ts")
        assert "const live = this.interactive && !this.disabled;" in text
        assert "chip.decoded_action" in text
        assert "chip.bypass_action" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_no_locale_still_bakes_the_click_into_the_description(
        self, locale,
    ):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "chip.decoded_action" in data
        assert "chip.bypass_action" in data
        # The description must not carry a second sentence telling the
        # reader to click; that is what the action key is for.
        assert data["chip.decoded_tip"].count(".") <= 1


class TestCombKeysAbutTheirDiagnosis:
    """A fixed 200px key column left a name and the sentence explaining
    it on opposite sides of a gutter."""

    def test_the_grid_moved_to_the_list(self):
        text = _read("ir-comb-report.ts")
        assert "grid-template-columns: max-content" in text
        block = text.split(".find {\n                display: contents;", 1)
        assert len(block) == 2, "the finding rows must join the list grid"

    def test_the_fixed_column_is_gone(self):
        text = _read("ir-comb-report.ts")
        assert "grid-template-columns: 200px 1fr" not in text

    def test_show_all_spans_both_tracks(self):
        """A grid child with no span lands in the key column."""
        text = _read("ir-comb-report.ts")
        block = text.split("\n            .more {", 1)[1].split("}", 1)[0]
        assert "grid-column: 1 / -1" in block


class TestCombOpensOnArrival:
    """An arriving wig's codes have never been checked against each
    other on this install, and the moment to learn that 48 of them
    disagree is before the fitting, not after."""

    def test_upload_opens_the_ledger(self):
        text = _read("ir-wigs.ts")
        assert "_combAfterUpload" in text
        upload = text.split("_uploadText", 1)[1].split("_renderReceiptLine", 1)[0]
        assert "_combAfterUpload" in upload

    def test_only_when_exactly_one_wig_landed(self):
        """A foreign format converts to as many wigs as the file holds,
        and five stacked dialogs is not a report."""
        text = _read("ir-wigs.ts")
        assert "fresh.length === 1" in text

    def test_duplicates_do_not_reopen_it(self):
        text = _read("ir-wigs.ts")
        assert "files.filter((f) => !f.duplicate_of)" in text

    def test_adopt_opens_the_ledger_for_wigs_only(self):
        """Adopting from the library builds a device from catalog
        entries; there is no file to comb."""
        text = _read("ir-wigs.ts")
        block = text.split(
            "private async _onWigAdopted(", 1,
        )[1].split("\n    private", 1)[0]
        assert "this._adoptWig?.filename" in block
        assert "_combAfterUpload(adopted)" in block


class TestClosetTakesOneFile:
    """The loop hung every dropped file but wrote the receipt fresh
    each time, so a five-file drop reported the fifth and the other
    four landed with no trace."""

    def test_browse_no_longer_offers_multiple(self):
        assert "input.multiple = true" not in _read("ir-wigs.ts")

    def test_both_entry_points_share_one_guard(self):
        text = _read("ir-wigs.ts")
        assert text.count("_acceptsOne(") >= 3

    def test_a_refused_drop_hangs_nothing(self):
        text = _read("ir-wigs.ts")
        drop = text.split("_onDrop", 1)[1].split("_browse", 1)[0]
        assert "for (const file of" not in drop

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_refusal_is_translated(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "{count}" in data["wigs.upload_one_at_a_time"]


class TestClosetRowsLineUp:
    """.row-actions is margin-left:auto, so anything missing at the end
    drags everything before it sideways: a library row with no DELETE
    sat 64px right of a local one and the download icons never lined
    up down the list."""

    def test_delete_keeps_its_place_on_rows_that_have_none(self):
        text = _read("ir-wigs.ts")
        assert 'class="action-btn delete-ghost"' in text
        block = text.split(".delete-ghost {", 1)[1].split("}", 1)[0]
        assert "visibility: hidden" in block
        assert "pointer-events: none" in block

    def test_the_ghost_carries_the_real_label(self):
        """A fixed pixel width would be wrong the moment common.delete
        is LOSCHEN or a Cyrillic string."""
        text = _read("ir-wigs.ts")
        ghost = text.split("delete-ghost", 1)[1].split("</span", 1)[0]
        assert 'common.delete' in ghost

    def test_every_glyph_slot_is_unconditional(self):
        """Three slots -- edit, comb, download -- and the row must
        render all three whether or not it has a wig to put in them."""
        text = _read("ir-wigs.ts")
        row = text.split("_renderRow(row: ClosetRow)", 1)[1]
        row = row.split("_renderEditor", 1)[0]
        assert row.count('<span class="glyph-slot">') == 3
