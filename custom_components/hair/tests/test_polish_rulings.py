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
    it on opposite sides of a gutter (owner bench 2026-08-02).

    The two-column grid that replaced it is itself gone now: a class
    opens into findings GROUPED BY DIAGNOSIS, so the sentence is a
    heading printed once and the keys are chips beneath it. There is no
    gutter left to be ragged, which is the strongest form of the fix.
    The invariant survives its mechanism: a coordinate and the words
    about it are never separated by dead space.
    """

    def test_the_fixed_column_is_gone(self):
        text = _read("ir-comb-report.ts")
        assert "grid-template-columns: 200px 1fr" not in text
        assert "grid-template-columns: max-content" not in text

    def test_the_diagnosis_is_a_heading_over_its_own_keys(self):
        text = _read("ir-comb-report.ts")
        assert ".dh {" in text and ".keys {" in text
        # The heading owns the sentence; the chips sit under it.
        assert 'class="dh"' in text and 'class="keys"' in text

    def test_the_chips_wrap_rather_than_column(self):
        """Ninety coordinates in a fixed column is the wall this whole
        pass exists to remove."""
        block = _read("ir-comb-report.ts").split("\n            .keys {", 1)[1]
        block = block.split("}", 1)[0]
        assert "flex-wrap: wrap" in block


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
    sat 64px right of a local one and the download icons never lined up
    down the list (owner bench 2026-08-02).

    The ghost that used to hold DELETE's place rendered the real
    localized label, so the reservation stayed correct in any language.
    That was sound reasoning right up until the polish pass made DELETE
    an icon: a text-width ghost against an 18px can would have re-broken
    the very alignment it was added to fix, inverted. A fixed 30px slot
    is locale-proof by construction, so the ghost is gone and the trash
    is the fourth slot. The invariant is unchanged; only the mechanism.
    """

    def test_the_ghost_is_gone(self):
        assert "delete-ghost" not in _read("ir-wigs.ts")

    def test_delete_is_the_fourth_glyph_slot(self):
        """Edit, comb, download, trash. The row renders all four
        whether or not it has a wig to put in them."""
        text = _read("ir-wigs.ts")
        row = text.split("_renderRow(row: ClosetRow)", 1)[1]
        row = row.split("_renderEditor", 1)[0]
        assert row.count('<span class="glyph-slot">') == 4

    def test_the_slot_is_a_fixed_width(self):
        text = _read("ir-wigs.ts")
        block = text.split(".glyph-slot {", 1)[1].split("}", 1)[0]
        assert "width: 30px" in block
        assert "flex: none" in block


TRASH_MODULES = (
    "ir-command-row.ts",
    "ir-mirror.ts",
    "ir-signal-monitor.ts",
    "ir-clips.ts",
    "ir-pluck.ts",
    "ir-wigs.ts",
)


class TestOneTrashCanInTheTree:
    """ICON_TRASH lived in ir-device-list.ts, which was fine while
    exactly one surface drew a can. Nine more is how two definitions
    drift: one gets a tweak, the other does not, and the panel quietly
    ships two cans.
    """

    def test_the_path_has_exactly_one_home(self):
        assert "export const ICON_TRASH" in _read("ir-icons.ts")
        assert "const ICON_TRASH =" not in _read("ir-device-list.ts")

    def test_every_consumer_imports_it(self):
        for module in (*TRASH_MODULES, "ir-device-list.ts"):
            assert 'from "./ir-icons.js"' in _read(module), module

    def test_the_fifty_by_fifty_viewbox_travels_with_it(self):
        """It is the owner's own drawing, not MDI's delete-outline, so
        it is not in MDI's 24x24 box. A consumer that forgets renders a
        speck in the corner."""
        assert 'TRASH_VIEWBOX = "0 0 50 50"' in _read("ir-icons.ts")
        for module in (*TRASH_MODULES, "ir-device-list.ts"):
            text = _read(module)
            assert text.count("ICON_TRASH") == text.count("TRASH_VIEWBOX"), (
                module
            )

    def test_it_is_drawn_at_eighteen_not_sixteen(self):
        """The argyle pattern fills in below about 17px, and that
        detail is what makes it the house can rather than any can."""
        block = _read("ir-icons.ts").split(".trash-btn ha-svg-icon {", 1)[1]
        assert "--mdc-icon-size: 18px" in block.split("}", 1)[0]


class TestEverythingThatDeletesIsEmber:
    """Three delete colours were in play: ember on the text chips,
    material red on the two trash icons that already shipped, crimson in
    the wig dialogs. Choosing ember for the can collapsed the first two,
    which left the two shipped icons as the odd ones out. Two
    conventions for the same act is the exact failure the ruling avoids.

    (The crimson in the wig dialogs is pre-existing drift, out of this
    pass's scope, and now the only delete colour that is not ember.)
    """

    def test_the_shared_button_hovers_ember(self):
        block = _read("ir-icons.ts").split(
            ".trash-btn:hover:not(:disabled) {", 1
        )[1].split("}", 1)[0]
        assert "#e65100" in block
        assert "rgba(230, 81, 0, 0.12)" in block

    def test_material_red_is_gone_from_the_shipped_icons(self):
        text = _read("ir-device-list.ts")
        assert "#f44336" not in text
        assert "244, 67, 54" not in text


class TestEveryTrashIsNamed:
    """Nine buttons lost their text label. A button whose accessible
    name WAS its text content is anonymous the moment the text goes.
    """

    @pytest.mark.parametrize("module", TRASH_MODULES)
    def test_each_trash_button_is_titled_and_labelled(self, module):
        text = _read(module)
        for block in text.split('class="trash-btn"')[1:]:
            head = block.split(">", 1)[0]
            assert "title=" in head, module
            assert "aria-label=" in head, module

    def test_the_trigger_trash_became_focusable(self):
        """It shipped as a bare ha-svg-icon with a click handler, so it
        was unreachable by keyboard for as long as it has existed."""
        text = _read("ir-device-list.ts")
        before, block = text.split('class="trigger-trash"', 1)
        assert "aria-label=" in block.split(">", 1)[0]
        # The tag it opens now, not the tag it used to open.
        assert before.rstrip().endswith("<button")


class TestTwoBugsFoundInTheSweepPath:
    """Neither is polish. Both were found by reading every delete
    control in the panel in one sitting, which is the only reason they
    surfaced at all.
    """

    def test_plucks_clear_all_is_translatable(self):
        """It shipped a hardcoded English string where both its
        siblings call t(), so it has never been translated in nine
        languages."""
        text = _read("ir-pluck.ts")
        assert "\n                              Clear All\n" not in text
        assert 't("sniffer.clear_all")' in text

    def test_the_device_page_has_its_own_delete_label(self):
        """It wore devlist.del_device_title, which is a dialog HEADING
        elsewhere. One key across two surfaces means neither can ever
        be worded for where it sits."""
        assert 'devlist.del_device_title' not in _read("ir-device-detail.ts")
        assert 'devdetail.delete_device' in _read("ir-device-detail.ts")

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_both_new_keys_exist_everywhere(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "devdetail.delete_device" in data
        assert "sniffer.clear_all" in data


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


class TestClosingTheLedgerKeepsTheSaveDialog:
    """One event name, two owners, one level apart.

    The device page mounts <ir-save-wig-dialog @closed=...> and unmounts
    it on that event. The save dialog mounts <ir-claims-ledger
    @closed=...> and does the same. A COMPOSED event crosses shadow
    boundaries, so closing the ledger reached the device page as well
    and took the half-filled save form down with it (bench 2026-08-03).
    """

    def test_the_ledger_close_does_not_escape_its_shadow_root(self):
        text = _read("ir-claims-ledger.ts")
        assert 'new CustomEvent("closed", { bubbles: true, composed: false })' in (
            " ".join(text.split())
        )

    def test_both_owners_still_listen_for_the_same_name(self):
        """If either handler is ever renamed, the pairing this test
        protects stops existing and the assertion should be revisited
        rather than deleted."""
        assert "@closed=" in _read("ir-save-wig-dialog.ts")
        assert "@closed=" in _read("ir-device-detail.ts")


class TestTheLedgerRowIsABox:
    """The alias and its verdict came apart on the bench.

    The row list was a three-column grid and each row rendered two
    cells, because the third column existed for the orphan note that
    most rows do not have. Every row therefore started one column
    further along than the last. A row that owns its own children
    cannot drift however many of them it has.
    """

    def test_the_row_is_no_longer_loose_cells(self):
        text = _read("ir-claims-ledger.ts")
        rows = text.split(".rows {", 1)[1]
        assert "display: contents" not in rows
        assert "grid-template-columns: 1fr 1fr" in rows

    def test_the_row_carries_a_leader_to_its_verdict(self):
        """A short alias and a long verdict with a hole between them
        read as two unrelated words."""
        text = _read("ir-claims-ledger.ts")
        assert 'class="leader"' in text
        assert ".leader {" in text

    def test_it_falls_to_one_column_when_narrow(self):
        text = _read("ir-claims-ledger.ts")
        assert "max-width: 560px" in text


class TestEveryFittingIsADisclosure:
    """A wig that travels collects fittings, and four people at twelve
    rows each is a wall. The closed head keeps who, signature, tier and
    counts, which is everything anybody scans a ledger for; opening it
    is what buys the row by row detail.
    """

    def test_the_head_is_a_button_not_a_div(self):
        """A chevron alone is a 15px target beside 500px of dead text
        that looks just as pressable."""
        text = _read("ir-claims-ledger.ts")
        assert 'class="ehead"' in text
        assert "aria-expanded=" in text

    def test_a_lone_fitting_opens_itself(self):
        """One collapsed row is a chevron hiding the whole dialog."""
        text = " ".join(_read("ir-claims-ledger.ts").split())
        assert "if (entries.length === 1) return new Set([0]);" in text

    def test_your_own_fitting_is_the_one_that_opens(self):
        text = " ".join(_read("ir-claims-ledger.ts").split())
        assert "entries.findIndex((e) => e.mine)" in text

    def test_opening_one_does_not_shut_another(self):
        """Free rather than accordion: the question people bring here is
        who disagreed with whom about which row, and that needs two
        entries on screen at once."""
        text = " ".join(_read("ir-claims-ledger.ts").split())
        assert "_flip(this._open, index)" in text

    def test_the_row_cap_rose_with_the_pairing(self):
        """Two rows per line, so 24 is twelve lines. It was 6 when the
        rows ran one per line."""
        text = _read("ir-claims-ledger.ts")
        assert "const PREVIEW_ROWS = 24;" in text

    def test_show_all_uses_the_plural_helper(self):
        """claims.show_all only exists as .one and .other, so the plain
        t() call it used to make could never resolve."""
        text = _read("ir-claims-ledger.ts")
        assert 'tp("claims.show_all"' in text
        assert 't("claims.show_all"' not in text


class TestEmittersHaveThreeStates:
    """Assigned-and-reachable, off, and assigned-but-down.

    The third one is the whole point. HA knows, device_manager skips
    unavailable and unknown emitters at send time, and the picker was
    reading that very state object for the friendly name and throwing
    the rest away. A device could list a blaster unplugged for a week
    with nothing on screen to say so.
    """

    def test_the_picker_reads_availability(self):
        text = _read("ir-emitter-picker.ts")
        assert "available" in text
        # GH #83: "unknown" means never-used, not down. The dead set
        # must contain exactly "unavailable" -- painting a brand-new
        # emitter amber told every fresh install its hardware was
        # broken.
        dead = text.split("const DEAD_STATES = new Set(", 1)[1]
        dead = dead.split(")", 1)[0]
        assert '"unavailable"' in dead
        assert '"unknown"' not in dead

    def test_all_three_states_are_rendered(self):
        text = _read("ir-emitter-picker.ts")
        for key in (
            "picker.state_on",
            "picker.state_off",
            "picker.state_unavailable",
        ):
            assert key in text, key

    def test_only_an_assigned_emitter_reports_being_down(self):
        """An unassigned emitter that happens to be unreachable is
        simply off. Nothing is expected of it, so it has nothing to
        complain about."""
        text = " ".join(_read("ir-emitter-picker.ts").split())
        assert "const down = on && !em.available;" in text

    def test_the_state_word_is_not_printed_beside_the_name(self):
        """The dot is the state. A word spelled out beside every chip
        turns a row of three emitters into a row of six things to read,
        which is the opposite of what the capsule is for."""
        text = _read("ir-emitter-picker.ts")
        assert 'class="st"' not in text
        # It still reaches anyone who needs it.
        assert "aria-label=" in text and "title=" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_four_new_keys(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key in (
            "picker.state_on",
            "picker.state_off",
            "picker.state_unavailable",
        ):
            assert key in data, f"{locale} missing {key}"

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_dropdown_keys_are_gone(self, locale):
        """There is no dropdown to add from and no all-selected state,
        because every emitter is always on screen. The broadcast note
        went with them: the rule is true, but a permanent line of prose
        under a control nobody asked a question of is furniture."""
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "picker.add_emitter" not in data
        assert "picker.all_emitters_selected" not in data
        assert "picker.broadcast_note" not in data


class TestTheMetadataRowIsTwoColumns:
    """An 80px column reserved for two words, with the controls left
    floating in what remained. Each label sits above its own control
    now and each control gets the full width of its own column.
    """

    def test_the_label_gutter_is_gone(self):
        text = _read("ir-device-detail.ts")
        assert "grid-template-columns: 80px 1fr" not in text
        assert ".meta-label" not in text
        assert ".meta-value" not in text

    def test_the_picker_gets_its_label_back(self):
        """It was suppressed because the gutter already carried one.
        There is no gutter."""
        assert "--picker-label-display: none" not in _read(
            "ir-device-detail.ts"
        )

    def test_type_is_capped_and_emitters_take_the_rest(self):
        """A seven-item dropdown never needed 900px."""
        text = _read("ir-device-detail.ts")
        assert "grid-template-columns: 200px minmax(0, 1fr)" in text

    def test_the_label_sits_above_its_control(self):
        text = _read("ir-device-detail.ts")
        assert 'class="sl"' in text and ".stack .sl {" in text
        picker = _read("ir-emitter-picker.ts")
        assert "<label>" in picker
        assert 'class="capsule"' not in picker

    def test_the_columns_stack_when_narrow(self):
        text = _read("ir-device-detail.ts")
        assert "max-width: 700px" in text

    def test_the_toggle_kept_the_event_contract(self):
        """Add and remove collapsed into one toggle, but the event the
        three embedding dialogs listen for is byte-identical, which is
        why none of them needed touching."""
        text = _read("ir-emitter-picker.ts")
        assert 'new CustomEvent("emitters-changed"' in text
        assert "_onAdd" not in text and "_onRemove" not in text


class TestTheCombReportLeadsWithConsequence:
    """It used to group by check class and give every class an identical
    card, which is the backend's ordering rendered faithfully and made a
    wig with nine cosmetic artefacts look exactly as alarming as one
    carrying a code that answers a press and sets the wrong state. The
    ranking existed; it was not visible in the first two seconds, which
    is the only part most people read.
    """

    def test_every_suspect_class_has_a_bucket(self):
        """A class with no bucket renders NOWHERE AT ALL, so a check
        added server-side must fail here until the frontend places it.
        That is the point of reading the backend's own tuple."""
        from custom_components.hair.wig_comb import (
            ADVISORY_CHECKS,
            SEVERITY_ORDER,
        )

        block = _read("ir-comb-report.ts").split("const CONSEQUENCE", 1)[1]
        block = block.split("};", 1)[0]
        for check in SEVERITY_ORDER:
            if check in ADVISORY_CHECKS:
                continue
            assert check in block, check

    def test_the_buckets_are_worst_first(self):
        text = _read("ir-comb-report.ts")
        assert 'BUCKETS = ["wrong", "ignored", "cosmetic"]' in text

    def test_an_empty_bucket_is_omitted_not_shown_at_zero(self):
        """A card reading "0 will do the wrong thing" is reassurance
        wearing the costume of a warning."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "if (classes.length) out.push([bucket, classes]);" in text

    def test_the_tally_carries_a_denominator(self):
        """48 findings is catastrophic on a seven-button remote and
        unremarkable on a 288-cell lattice, and it is the same 48."""
        text = _read("ir-comb-report.ts")
        assert "comb.tally" in text
        assert "private get _total()" in text

    def test_the_tally_is_what_the_buckets_add_up_to(self):
        """It is deliberately NOT report.suspects. duplicate-labels is
        advisory server-side so it never counts as a suspect, a correct
        call, but it still earns a cosmetic bucket here. A report that
        lists a finding and leaves it out of its own total is arguing
        with itself in front of the reader."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "const total = this._flagged(buckets);" in text
        assert "this._report.suspects" not in text

    def test_the_classes_inside_a_bucket_still_use_the_backend_order(self):
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "SEVERITY_ORDER.filter(" in text


class TestTheCombReportOpensOnAChevron:
    """Today every group gets a Show all whether it has three findings
    or twenty-two, and opening one closes nothing but reveals the same
    sentence printed nineteen times."""

    def test_a_single_finding_gets_no_chevron(self):
        """Its summary line already IS the finding. There is nothing
        behind the chevron to show."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "const openable = findings.length > 1;" in text

    def test_several_classes_can_be_open_at_once(self):
        """Comparing frame shape against malformed frame should not
        mean shutting one of them."""
        text = _read("ir-comb-report.ts")
        assert "_expanded = new Set<string>()" in text

    def test_the_whole_row_is_the_target(self):
        """Not a 16px chevron beside 500px of text that looks just as
        pressable."""
        text = _read("ir-comb-report.ts")
        assert ".srow.can {" in text
        assert "cursor: pointer" in text.split(".srow.can {", 1)[1]

    def test_the_retired_preview_keys_are_gone(self):
        text = _read("ir-comb-report.ts")
        assert "comb.show_all" not in text
        assert "comb.showing" not in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_no_locale_still_carries_them(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "comb.show_all" not in data
        assert "comb.showing" not in data


class TestFindingsGroupByDiagnosis:
    """Frame shape on the Samsung has twenty-two findings and two facts
    in it: nineteen codes send one burst pair too many, three send two
    too many. Printing the same sentence nineteen times was never
    nineteen facts.
    """

    def test_the_key_is_an_array_not_a_concatenation(self):
        """Joining the message key and the params with a separator
        means picking a character that cannot appear in either, and
        getting that wrong silently merges two different facts."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "JSON.stringify([f.message, sorted])" in text

    def test_param_keys_are_sorted(self):
        """JSON.stringify follows insertion order, and two findings
        carrying the same params in a different order are the same
        fact."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "Object.keys(params) .sort()" in text or (
            "Object.keys(params).sort()" in text
        )

    def test_row_identity_never_rides_in_params(self):
        """The whole merge depends on it: identity lives in Finding.keys
        and params carries only the diagnostic substitutions. If a check
        ever puts a row key in params, every finding becomes its own
        group and this degrades silently rather than loudly."""
        src = (
            Path(__file__).parent.parent / "wig_comb.py"
        ).read_text(encoding="utf-8")
        for line in src.splitlines():
            if "params={" in line or "params = {" in line:
                assert "keys" not in line.split("params", 1)[1], line


class TestTheCombReportHandsOff:
    """The footer says only a fitting proves them ON THE DEVICE. The
    handoff is the way to the device, so the two read as one thought.
    It is also the only place the panel says that a comb suspect
    surfaces as an ordinary command row wearing a comb glyph, which is
    the thing nobody would guess.
    """

    def test_it_can_reach_the_device(self):
        text = _read("ir-comb-report.ts")
        assert "navigate-device" in text

    def test_the_navigate_event_matches_the_existing_contract(self):
        """A bare device_id detail, the same shape ir-wigs already
        dispatches and the panel already handles. Zero new plumbing."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert "detail: device.device_id," in text

    def test_the_adopt_offer_reaches_the_closets_own_dialog(self):
        """One adopt path, not two."""
        assert "adopt-wig" in _read("ir-comb-report.ts")
        assert "@adopt-wig=" in _read("ir-wigs.ts")

    def test_a_clean_comb_offers_nothing(self):
        """There is nothing to go and fix."""
        text = " ".join(_read("ir-comb-report.ts").split())
        assert (
            "if (!this._report || !this._buckets().length) return nothing;"
            in text
        )

    def test_the_glyph_appears_once_and_it_is_in_the_explainer(self):
        """It used to decorate a heading that already says Combing."""
        text = _read("ir-comb-report.ts")
        assert "combmark" not in text
        assert 'class="explain"' in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_new_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key in (
            "comb.explain_lead",
            "comb.explain_lint",
            "comb.tally",
            "comb.bucket_wrong",
            "comb.bucket_ignored",
            "comb.bucket_cosmetic",
            "comb.sev_wrong",
            "comb.sev_ignored",
            "comb.sev_cosmetic",
            "comb.handoff_adopt",
            "comb.handoff_adopt_body",
            "comb.handoff_open_body",
            "comb.open_device",
        ):
            assert key in data, f"{locale} missing {key}"

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_lead_keeps_its_placeholder(self, locale):
        """The render splits on {lint} to bold the joke. A translation
        that drops it loses the bold and half the sentence."""
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "{lint}" in data["comb.explain_lead"], locale


class TestDownloadsCarryTheTier:
    """The download filename now comes from the SERVER, composed from the
    wig's own fields (v0.9.7 Second Fitting). The client no longer builds
    a name at all: ``_tieredFilename`` is gone and ``_download`` uses the
    server's ``download_filename`` verbatim. A row and a filename still
    can never disagree, because both read the same claims -- and the
    dotted suffix that failed the shop's upload is gone with the client
    composer. The field-derived naming logic is proven against the pure
    function in test_supersession.py."""

    def test_the_client_no_longer_composes_a_name(self):
        text = _read("ir-wigs.ts")
        assert "_tieredFilename" not in text
        # The dotted suffixes went with it.
        assert '".perfect-fit"' not in text
        assert '".fitted"' not in text

    def test_the_download_uses_the_server_name(self):
        text = _read("ir-wigs.ts")
        download = text.split("private async _download(", 1)[1]
        download = download.split("private async _downloadLibrary", 1)[0]
        assert "download_filename" in download
        assert "_tieredFilename" not in download


class TestTheLegacyDropIsAnnounced:
    """Import sets pre-claims fittings aside (hard rule 6) and the
    backend has always reported the count; the receipt now says it.
    A drop nobody is told about reads as silent data loss to the one
    person it happens to."""

    def test_the_receipt_counts_dropped_fittings(self):
        text = _read("ir-wigs.ts")
        assert "dropped_fittings" in text
        assert "wigs.upload_dropped_fittings" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_notice(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "wigs.upload_dropped_fittings.one" in data, locale
        assert "wigs.upload_dropped_fittings.other" in data, locale


class TestDeviceOnlyRowStopsGhostClaims:
    """v0.9.7 Second Fitting: a device command not in the current Wig
    renders as a marked, uncheckable row and is excluded from the
    perfect-fit denominator, so a tick can never be born orphaned. The
    server-side belt-and-suspenders is proven in test_supersession /
    test_ws_wig_save."""

    def test_device_only_rows_are_detected_on_update(self):
        text = _read("ir-save-wig-dialog.ts")
        assert "_isDeviceOnly" in text
        # Keyed on the wig_index the backend leaves unset for such rows.
        assert "wig_index == null" in text

    def test_device_only_row_has_no_checkbox(self):
        text = _read("ir-save-wig-dialog.ts")
        block = text.split("private _renderDeviceOnlyRow", 1)[1].split(
            "private _renderRow", 1
        )[0]
        assert "no-check" in block
        assert 'type="checkbox"' not in block
        # TEST stays live: the command is real on the device.
        assert "ir-test-button" in block

    def test_perfect_fit_excludes_device_only_rows(self):
        text = _read("ir-save-wig-dialog.ts")
        assert "_attestableRows" in text
        # The attestable subset filters device-only rows out.
        assert "!this._isDeviceOnly" in text

    def test_the_nudge_points_at_save_as_new(self):
        text = _read("ir-save-wig-dialog.ts")
        assert "not_in_wig_nudge" in text
        nudge = text.split("_renderNudge", 1)[1].split(
            "_renderDeviceOnlyRow", 1
        )[0]
        # The whole line arms Save as new.
        assert "_saveAsNew = true" in nudge
