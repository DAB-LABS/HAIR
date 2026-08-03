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


class TestTheRawPinFollowsTheBytes:
    """RULED 2026-08-03, one of the two questions v0.9.5 parked.

    A pin is a claim a SPECIFIC capture earned -- "these bytes break
    when re-encoded". New bytes have not earned it, so replacing a
    command's code clears the pin and the chip re-derives from the live
    decode. The person re-pins deliberately.

    The old ruling (2026-08-01) said REPLACE STARTS FRESH for the same
    reason, inside the fitting dialog, where bytes and the decision
    about them were written in one hash roll. That dialog is gone and
    the hazard it named went with it -- per-row digests carry the
    binding now -- but the reasoning survived the machinery.
    """

    def test_the_reset_is_keyed_on_the_code_differing(self):
        """Not on the input event firing. Typing a character and
        deleting it again must leave the pin alone, or an undo destroys
        a setting nobody meant to touch."""
        text = _read("ir-signal-editor.ts")
        body = text.split("private _syncPinToPronto()", 1)[1]
        body = body.split("\n    private ", 1)[0]
        assert "this.initialPronto.trim()" in body
        assert "this.initialTxForceRaw" in body

    def test_both_real_change_paths_call_it(self):
        """Paste and Listen. A path that changes the code without
        syncing leaves a pin attached to bytes that never earned it."""
        text = _read("ir-signal-editor.ts")
        for fn in ("_onProntoInput", "_onCaptured"):
            body = text.split(f"private {fn}", 1)[1]
            body = body.split("\n    private ", 1)[0]
            assert "_syncPinToPronto()" in body, fn

    def test_the_carrier_snap_does_not_clear_it(self):
        """Snapping re-times the SAME waveform to a standard frequency.
        It is a normalisation of the capture that earned the pin, not a
        replacement for it."""
        text = _read("ir-signal-editor.ts")
        body = text.split("private async _snap(", 1)[1]
        body = body.split("\n    private ", 1)[0]
        assert "_syncPinToPronto()" not in body


class TestProvenanceMarkersAreGone:
    """RULED 2026-08-03, the second parked question.

    ``captured`` / ``pasted`` / ``tuned`` recorded how a row's bytes got
    there. That was load-bearing exactly once: a marker implied a hash
    roll, which was how a Changed Codes row could count toward
    completeness. Per-row digests carry that binding directly now, the
    device is the only place codes change hands, and nothing has
    rendered a marker since the fitting dialog's chips went.

    Asserted by NAME rather than by behaviour because the constants no
    longer exist: a reintroduction would be unread freight written into
    a file somebody signs.
    """

    @pytest.mark.parametrize("module", ["wig_save.py", "wig_fitting.py"])
    def test_no_backend_module_writes_a_marker(self, module):
        text = (Path(__file__).parent.parent / module).read_text(
            encoding="utf-8"
        )
        # The docstring in wig_fitting explains the retirement, so the
        # check is for the CONSTANT, not the English word.
        assert "PROVENANCE_KEY" not in text
        assert "PROVENANCE_POWER_KEY" not in text

    def test_the_dead_writer_went_with_them(self):
        """``_write_row_code`` had no callers left at all: its flat
        replace caller died with the fitting dialog and nothing
        replaced it."""
        text = (
            Path(__file__).parent.parent / "wig_fitting.py"
        ).read_text(encoding="utf-8")
        assert "_write_row_code" not in text.split('"""', 2)[2]
        assert "_merge_provenance" not in text.split('"""', 2)[2]


class TestTheFooterIsOneRow:
    """DELETE DEVICE moved up beside the add buttons (owner 2026-08-03).

    It sat on its own full-width line, which was right when SAVE TO
    CLOSET was stacked above it; SAVE moved to the header in FR5 and
    left one button alone under a mostly empty row.

    The pin has to be margin-left:auto and NOT the container's
    justify-content. space-between distributes per WRAPPED LINE, so a
    card narrow enough to break the four buttons 2-and-2 would spread
    the second line to both edges with a hole in the middle.
    """

    def test_the_full_width_break_is_gone(self):
        text = _read("ir-device-detail.ts")
        # The class may survive in a comment explaining its removal;
        # what must not survive is a rule or an element using it.
        assert ".delete-row {" not in text
        assert 'class="delete-row"' not in text

    def test_the_button_is_pinned_not_distributed(self):
        text = _read("ir-device-detail.ts")
        pin = text.split(".footer-actions > .delete-btn {", 1)[1]
        assert "margin-left: auto" in pin.split("}", 1)[0]
        foot = text.split("\n        .footer-actions {", 1)[1]
        assert "space-between" not in foot.split("}", 1)[0]

    def test_the_dead_label_rule_went(self):
        """.add-label was styled and never rendered."""
        assert ".add-label" not in _read("ir-device-detail.ts")


class TestThePerfectFitBanner:
    """The one control that turns a save into a signed claim was a bare
    checkbox under a hairline rule, at the same weight as the form
    labels above it. Nothing marked the boundary between DESCRIBING a
    wig and MAKING A CLAIM about it, and those are different acts.
    """

    def test_it_is_dashed_at_rest_and_solid_when_armed(self):
        text = _read("ir-save-wig-dialog.ts")
        rest = text.split("\n            .fit-block {", 1)[1].split("}", 1)[0]
        assert "dashed" in rest
        armed = text.split(".fit-block.on {", 1)[1].split("}", 1)[0]
        assert "border-style: solid" in armed

    def test_only_the_head_is_clickable(self):
        """Once armed this block holds thirty ticks and a signature
        form. A stray click in that region disarming it would throw
        away work somebody just did."""
        text = _read("ir-save-wig-dialog.ts")
        assert '@click=${this._onHeadClick}' in text
        head = text.split("\n            .fit-head {", 1)[1].split("}", 1)[0]
        assert "cursor: pointer" in head

    def test_the_label_stops_its_own_bubble(self):
        """A click on the label toggles the checkbox natively and would
        then bubble to the head handler, which toggles it back. Every
        label click would net to nothing."""
        text = _read("ir-save-wig-dialog.ts")
        block = text.split('class="fit-check"', 1)[1].split("</label>", 1)[0]
        assert "stopPropagation" in block

    def test_the_refusal_sits_with_the_control_it_refuses(self):
        """The lattice gate explains why the tick is disabled. It used
        to live under the propose control, which is where the REMEDY
        is; the question it answers is asked at the tick."""
        text = _read("ir-save-wig-dialog.ts")
        head = text.split('@click=${this._onHeadClick}', 1)[1]
        head = head.split("_renderJoining()", 1)[0]
        assert "lattice_blocks_attestation" in head


class TestTheFittingsLineIsADoor:
    """Closes the item parked during v0.9.5. The count was grey text
    under a grey paragraph and the people behind it were unreachable.
    """

    def test_it_opens_the_ledger(self):
        text = _read("ir-save-wig-dialog.ts")
        assert "ir-claims-ledger" in text
        assert "_ledgerOpen" in text

    def test_the_copy_is_cardinal_not_ordinal(self):
        """The first draft read "you would be the {n}rd person", which
        is right for 3 and wrong for 2, 4 and 21. Fixing it properly
        needs an ordinal plural ruleset tp() does not have, and ja/ru/pl
        have no such construction at all."""
        text = _read("ir-save-wig-dialog.ts")
        assert "joining_ordinal" not in text
        assert "joining_proven" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_no_locale_bakes_an_ordinal_suffix(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key, value in data.items():
            if key.startswith("wigs.save.joining_proven"):
                assert "{count}rd" not in value
                assert "{count}th" not in value
                assert "{n}rd" not in value


class TestTheLedgerClearsTheTopLayer:
    """The door opened and nothing appeared to happen.

    As of HA 2026.7 <ha-dialog> wraps <wa-dialog>, which opens a real
    <dialog> with showModal(). That promotes it to the browser's TOP
    LAYER, which sits above the entire z-index scale and makes
    everything outside it inert. The ledger's overlay carried
    z-index 100 from the shared dialog styles and was both invisible
    and unclickable behind the save dialog (bench 2026-08-03).

    Only another modal dialog stacks above a modal dialog, so the
    ledger opens one of its own. Verified in the live frontend: with a
    modal ha-dialog open, the element at the viewport centre is the
    ledger.
    """

    def test_the_ledger_opens_a_native_modal(self):
        text = _read("ir-claims-ledger.ts")
        assert "showModal()" in text
        assert "<dialog" in text

    def test_the_carrier_keeps_the_panel_cosmetics(self):
        """The native element buys the top layer and draws nothing:
        every visible pixel still comes from .overlay and .dialog, so
        the ledger matches the panel's other pop-ups."""
        text = _read("ir-claims-ledger.ts")
        assert "dialog.top-layer" in text
        assert "dialog.top-layer::backdrop" in text
        assert 'class="overlay"' in text

    def test_escape_and_the_backdrop_close_it(self):
        """A native dialog closes itself on Escape without telling the
        parent, which would leave _ledgerOpen true and the door dead."""
        text = _read("ir-claims-ledger.ts")
        assert "@cancel=" in text

    def test_the_checklist_does_not_touch_the_door(self):
        """Two bordered objects butted together read as one control."""
        text = _read("ir-save-wig-dialog.ts")
        assert ".fit-head + .fit-list" in text
