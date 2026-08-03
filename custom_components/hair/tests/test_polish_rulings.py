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

    def test_the_edit_surface_uses_the_shared_predicate(self):
        """Not a hand-rolled copy: two gates that could drift apart is
        how the fitting dialog came to offer dittos on protocols the
        editor already refused. That dialog was the second surface and
        it is gone (v0.9.5); the shared predicate stays, because the
        next surface to grow a ditto knob must reach for it rather
        than write the gate again."""
        text = _read("ir-signal-editor.ts")
        assert 'from "./ir-tx-knobs.js"' in text
        assert "isDittoable(" in text

    def test_the_display_glyph_is_deliberately_not_gated(self):
        """A stored value hidden is a value nobody can find and
        correct, so the read-only knob still reports what a row
        carries even if it should never have carried it."""
        text = _read("ir-tx-knobs.ts")
        render = text.split("render()", 1)[1]
        assert "const showDittos = dittos > 1 && this.decoded" in render


class TestRowControlsCannotStagger:
    """Anything variable in a row's flex run moves the fixed controls
    that follow it, and REPLACE drew a staircase down the list.

    The dialog those staircases appeared in is gone (v0.9.5). What the
    pass produced that outlived it is ir-test-button: the send result
    was extracted onto the button that produced it, as its own
    component, and the save dialog inherited it. These guards follow
    the component.
    """

    def test_the_result_rides_the_button_that_produced_it(self):
        """Inline it shoved the controls; on a line below it read as
        orphaned, and matrix rows never rendered that line at all. It
        lives on TEST now, and TEST is its own component (owner ruling
        2026-08-02), which is why it survived the dialog."""
        text = _read("ir-test-button.ts")
        assert 'color="grey"' in text
        assert "testbtn.sent" in text and "testbtn.heard" in text

    def test_the_host_does_not_own_the_flash(self):
        """The extraction is only real if the state went with it: the
        surface that USES the button holds none of the flash's."""
        host = _read("ir-save-wig-dialog.ts")
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


class TestRowButtonsAcknowledgeTheMouse:
    """TEST was already gated on an emitter being picked but looked
    identical either way, and nothing in the row answered a hover or a
    press.

    The verdict buttons, APPLY and DISCARD that carried the rest of
    these guards were the fitting session's, and went with it. What the
    ruling is really about -- a control that can act says so under the
    mouse, and a control that cannot says THAT -- outlived them, so it
    is asserted here against the button every surface now shares and
    against the save dialog that replaced the row run.
    """

    @pytest.mark.parametrize(
        "selector",
        [".tbtn:hover:not(:disabled)", ".tbtn:active:not(:disabled)"],
    )
    def test_the_shared_test_button_answers_the_mouse(self, selector):
        assert selector in _read("ir-test-button.ts")

    def test_a_disabled_test_says_why(self):
        """The gate that started this: a TEST with no emitter behind it
        looked exactly like one that would fire."""
        text = _read("ir-test-button.ts")
        assert "disabledReason" in text
        assert "title=" in text

    def test_the_save_dialogs_actions_answer_the_mouse(self):
        text = _read("ir-save-wig-dialog.ts")
        for selector in (
            ".save-wig-btn:hover:not(:disabled)",
            ".as-new-btn:hover:not(:disabled)",
            ".reason-btn:hover",
        ):
            assert selector in text, selector


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
