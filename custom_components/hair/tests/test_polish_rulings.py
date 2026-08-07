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
        host = _read("ir-save-perfect-dialog.ts")
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
        """Second Fitting amendment v2 retires the Save-as-new toggle
        (``.as-new-btn``) along with it -- the verb is derived, nobody
        picks it, so there is no longer a footer control to switch."""
        text = _read("ir-save-perfect-dialog.ts")
        for selector in (
            ".save-wig-btn:hover:not(:disabled)",
            ".reason-btn:hover",
        ):
            assert selector in text, selector
        assert ".as-new-btn" not in text


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
        text = _read("ir-save-perfect-dialog.ts")
        rest = text.split("\n            .fit-block {", 1)[1].split("}", 1)[0]
        assert "dashed" in rest
        armed = text.split(".fit-block.on {", 1)[1].split("}", 1)[0]
        assert "border-style: solid" in armed

    def test_it_arms_without_a_click(self):
        """Second Fitting v3 punch list item 3 (owner bench,
        2026-08-06): choosing VALIDATE FOR PERFECT FIT at the decision
        window fork IS the arming -- there is no click-to-arm control
        left inside this dialog for a stray click to disarm."""
        text = _read("ir-save-perfect-dialog.ts")
        assert "_onHeadClick" not in text
        assert "_togglePerfect" not in text
        assert "_setPerfect" not in text
        head = text.split('<div class="fit-head">', 1)[1].split(
            "</div>", 1
        )[0]
        assert "@click" not in head

    def test_the_check_line_is_not_a_control(self):
        """The checkbox is gone from this route entirely (spec section
        4) -- the line under `.fit-check` states what is happening, it
        is not something to click, so there is nothing left to guard
        against a bubbled label click."""
        text = _read("ir-save-perfect-dialog.ts")
        block = text.split('<div class="fit-check">', 1)[1].split(
            "</div>", 1
        )[0]
        assert "<input" not in block

    def test_the_gray_limbo_state_is_gone(self):
        """The lattice gate is the only refusal left in this block, and
        it explains why attestation is disabled -- there is no manual
        arm/disarm toggle left for a gray unarmed state to sit under."""
        text = _read("ir-save-perfect-dialog.ts")
        rendering = text.split("private _renderFitting()", 1)[1]
        rendering = rendering.split("\n    private", 1)[0]
        assert "lattice_blocks_attestation" in rendering
        assert "this._armed" in rendering


class TestTheFittingsLineIsADoor:
    """Closes the item parked during v0.9.5. The count was grey text
    under a grey paragraph and the people behind it were unreachable.
    """

    def test_it_opens_the_ledger(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert "ir-claims-ledger" in text
        assert "_ledgerOpen" in text

    def test_the_copy_is_cardinal_not_ordinal(self):
        """The first draft read "you would be the {n}rd person", which
        is right for 3 and wrong for 2, 4 and 21. Fixing it properly
        needs an ordinal plural ruleset tp() does not have, and ja/ru/pl
        have no such construction at all."""
        text = _read("ir-save-perfect-dialog.ts")
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


class TestSavingRefreshesTheDeviceCard:
    """Bug (bench 2026-08-06): after Save as New / Update / Perfect
    Fit succeeds, the device card never refetched, so
    this.device.source_wig_id stayed stale and UPDATE CLOSET WIG kept
    missing on the very next Save to Closet open -- only a hard page
    refresh forced the refetch that made it appear. All three save
    dialogs already dispatch a bubbling, composed "wig-saved"
    CustomEvent on success; the fix wires it to the same _refresh()
    helper every other mutating action in this file already uses."""

    def test_all_three_save_dialogs_trigger_a_refresh(self):
        text = _read("ir-device-detail.ts")
        assert text.count("@wig-saved=${this._refresh}") == 3

    def test_the_dialogs_actually_dispatch_what_this_listens_for(self):
        assert 'new CustomEvent("wig-saved"' in _read(
            "ir-save-new-dialog.ts"
        )
        assert 'new CustomEvent("wig-saved"' in _read(
            "ir-save-update-dialog.ts"
        )
        assert 'new CustomEvent("wig-saved"' in _read(
            "ir-save-perfect-dialog.ts"
        )


class TestThePerfectFitExplainerAlignsWithItsLabel:
    """Bench feedback 2026-08-06: the description and the joining box
    under "Make this a perfect fit" sat indented 24px right of the
    label -- a checkbox-row indent convention (skipping past the
    checkbox glyph on the propose/oath rows) that does not apply
    here, since this particular .fit-check is a bare label with no
    checkbox. Flushed left to the label's own edge; the joining box
    widened to fill the freed space."""

    def test_the_gate_and_explainer_are_flush_left(self):
        text = _read("ir-save-perfect-dialog.ts")
        gate = text.split(".fit-gate {", 1)[1].split("}", 1)[0]
        assert "margin: 6px 0 0 0;" in gate
        explainer = text.split(".fit-explainer {", 1)[1].split("}", 1)[0]
        assert "margin: 6px 0 8px 0;" in explainer

    def test_the_joining_box_is_flush_left_and_full_width(self):
        text = _read("ir-save-perfect-dialog.ts")
        block = text.split(".joining {", 1)[1].split("}", 1)[0]
        assert "width: 100%;" in block
        assert "margin: 11px 0 0 0;" in block
        assert "box-sizing: border-box;" in block


class TestTheJoiningBoxIsOneLine:
    """Bench feedback (2026-08-07): "See the fitting it already
    carries" used to be forced onto its own line below the notice
    sentence by ``display: block`` on both spans. Both now fall back
    to inline, so the two run together and wrap as one paragraph."""

    def test_neither_span_forces_its_own_line(self):
        text = _read("ir-save-perfect-dialog.ts")
        j_line = text.split(".joining .j-line {", 1)[1].split("}", 1)[0]
        assert "display: block" not in j_line
        j_see = text.split(".joining .j-see {", 1)[1].split("}", 1)[0]
        assert "display: block" not in j_see
        assert "margin-top" not in j_see


class TestTheSelfCaseJoiningBoxIsFinal:
    """Second Fitting v3 punch list round three, item 11 (completing
    round two): the self case is one box, house amber, no handle --
    it can only ever be your own key."""

    def test_the_self_case_drops_the_handle_param(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert "handle: self.handle" not in text
        assert 'date: self!.date ?? ""' in text
        assert 'class="joining ${isSelf ? "joining-self" : ""}"' in text

    def test_the_self_case_wears_house_amber_not_blue(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert ".joining-self {" in text
        block = text.split(".joining-self {", 1)[1].split("}", 1)[0]
        assert "217, 164, 65" in block

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_drops_the_handle_token(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "{handle}" not in data["wigs.save.joining_self_notice"]


class TestTheRenameHelperNamesTheFile:
    """Second Fitting v3 punch list round three, item 16: terser,
    names the actual file being renamed, not the wig."""

    def test_perfect_dialog_interpolates_the_filename(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert (
            'filename: this._plan?.source_filename ?? ""' in text
        )

    def test_update_dialog_interpolates_the_filename(self):
        text = _read("ir-save-update-dialog.ts")
        assert 'filename: this.plan.source_filename ?? ""' in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_uses_the_filename_token(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "{filename}" in data["wigs.save.rename_wig_warning"]
        assert "{name}" not in data["wigs.save.rename_wig_warning"]


class TestTheUpdateDialogsTwoChipsShowTheDelta:
    """Second Fitting v3 punch list round three, item 17: the wig
    name anchors the top chip in bold house-link blue; the bottom
    chip names the actual remove/add delta instead of a bare
    count."""

    def test_the_top_chip_uses_its_own_key_not_the_shared_one(self):
        text = _read("ir-save-update-dialog.ts")
        graded = text.split("private get _gradedLine()", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "supersede.update_fitted_perfect" in graded
        assert "supersede.fitted_scoped" in graded

    def test_the_top_chip_name_is_bold_and_blue(self):
        text = _read("ir-save-update-dialog.ts")
        assert text.count("_renderGradedPerfectLine(") == 2
        assert '<b class="replaced-name">${name}</b>' in text

    def test_the_add_side_reads_the_unmatched_device_rows(self):
        text = _read("ir-save-update-dialog.ts")
        added = text.split("private get _addedRowsLine()", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "if (!this._diverged) return null;" in added
        assert "!r.matched" in added
        assert "supersede.added" in added

    def test_names_truncate_past_four(self):
        text = _read("ir-save-update-dialog.ts")
        names = text.split("private _formatNames(", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "MAX = 4" in names
        assert "supersede.topup_more" in names

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_added_side_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "supersede.update_fitted_perfect" in data, (
            f"{locale} missing key"
        )
        assert "supersede.added.one" in data, f"{locale} missing key"
        assert "supersede.added.other" in data, f"{locale} missing key"


class TestTheWiglessChipIsGreenNotYellow:
    """Second Fitting v3 punch list round three, item 18: creating a
    wig is information, not danger."""

    def test_the_source_missing_chip_uses_the_wig_icon_not_a_warning(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert '<div class="source-missing-info">' in text
        assert 'import { ICON_WIG } from "./ir-wigs.js";' in text
        chip = text.split(
            '<div class="source-missing-info">', 1
        )[1].split("</div>`", 1)[0]
        assert "ha-svg-icon" in chip
        assert "wigs.save.source_missing" in chip

    def test_the_chip_wears_house_green(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert ".source-missing-info {" in text
        block = text.split(".source-missing-info {", 1)[1].split(
            ".fitted-line {", 1
        )[0]
        assert "79, 158, 90" in block


class TestTheCompactPanelHeader:
    """Second Fitting v3 punch list round three, item 19: the banner
    image is gone, replaced by a slim left-aligned brand block on the
    content column's own edge, not the viewport corner."""

    def test_the_banner_image_is_gone(self):
        text = _read("ha-panel-ir-devices.ts")
        assert "header-banner" not in text
        assert "hair-header.png" not in text

    def test_the_brand_block_uses_the_content_column_edge(self):
        text = _read("ha-panel-ir-devices.ts")
        assert '<div class="brand-block">' in text
        assert "hair-brand-mark.png" in text
        block = text.split(".brand-block {", 1)[1].split("}", 1)[0]
        assert "max-width: 1100px" in block
        assert "margin: 0 auto" in block

    def test_the_mark_is_58px_tall(self):
        text = _read("ha-panel-ir-devices.ts")
        block = text.split(".brand-mark {", 1)[1].split("}", 1)[0]
        assert "height: 58px" in block

    def test_the_tab_row_and_tagline_are_untouched(self):
        """The two parked extensions -- folding the tab row onto this
        line, retiring the tagline row -- are NOT built this round."""
        text = _read("ha-panel-ir-devices.ts")
        assert ".tab-tagline {" in text
        assert '<div class="tab-bar">' in text


class TestTheCombReportAnchorsNearCenter:
    """Second Fitting v3 punch list round three, item 20: the top
    edge itself moves to a computed near-center instead of a flat
    5vh, with a documented TYPICAL REPORT HEIGHT constant and a
    mobile-safe dvh repeat."""

    def test_the_padding_is_computed_not_flat(self):
        text = _read("ir-comb-report.ts")
        assert "padding: 5vh 0;" not in text
        overlay = text.split(".overlay {", 1)[1].split("}", 1)[0]
        assert "max(6vh, calc((100vh - 620px) / 2))" in overlay
        assert "max(6vh, calc((100dvh - 620px) / 2))" in overlay
        assert "padding-bottom: 6vh;" in overlay

    def test_the_constant_is_documented(self):
        text = _read("ir-comb-report.ts")
        assert "TYPICAL REPORT HEIGHT" in text

    def test_the_top_anchoring_rationale_survives(self):
        """The two-paint growth and tall-report scroll reasoning from
        the 2026-08-03 bench stays -- only the anchor position
        moved."""
        text = _read("ir-comb-report.ts")
        assert "TOP-ANCHORED, not centred" in text
        assert "align-items: flex-start" in text


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
        text = _read("ir-save-perfect-dialog.ts")
        assert ".fit-head + .fit-list" in text


class TestClosingTheLedgerKeepsTheSaveDialog:
    """One event name, two owners, one level apart.

    The device page mounts <ir-save-perfect-dialog @closed=...> and unmounts
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
        assert "@closed=" in _read("ir-save-perfect-dialog.ts")
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


class TestTheChecklistLearnsWhatChanged:
    """Second Fitting amendment v2 (owner-ruled on the bench
    2026-08-04), replacing the v0.9.7 device-only-row guard this class
    used to pin. The owner's ruling on missing rows was "option 2,
    deliberately": a wig row the device no longer covers always
    diverges the save to SUCCESSION now, never feeding a per-row
    exclusion picker. The verb stops being a toggle the person sets and
    becomes something ``build_save_plan`` derives from digest
    divergence, proven server-side in test_supersession /
    test_ws_wig_save; this class pins what the dialog does with that
    derived variant. The retirement is the point as much as the
    addition: the marker chip, its note, the nudge, and the Save-as-new
    toggle they pointed at all leave with this ruling, so half of what
    follows asserts they are GONE, not just that something replaced
    them.
    """

    def test_the_old_exclusion_picker_is_gone(self):
        text = _read("ir-save-perfect-dialog.ts")
        for dead in (
            "_isDeviceOnly",
            "_renderDeviceOnlyRow",
            "_renderNudge",
            "_saveAsNew",
            "_confirmNew",
            "device-only",
            "nudge-line",
        ):
            assert dead not in text, dead

    def test_the_verb_is_derived_not_sent(self):
        """The perfect-fit dialog still never tells the server which
        verb it is -- ``build_save_plan`` derives CREATE / UPDATE /
        SUCCESSION from the device's own digests there, so a stale
        dialog cannot steer a save down a verb the device has
        outgrown. Second Fitting v3 punch list item 2 carves out
        exactly one exception at the wire level: Save As New sends
        `mode: "create"` to force a mint regardless of the derivation,
        since choosing that route IS the signal -- but the field is
        typed to the single literal "create", not a general verb the
        caller could otherwise steer with."""
        text = _read("ir-save-perfect-dialog.ts")
        assert 'this._plan?.variant === "succession"' in text
        save_device = text.split("private async _saveDevice()", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "mode:" not in save_device
        # Scoped to the wigsSave payload: matrixSend has its own
        # unrelated "mode" (an HVAC mode string), elsewhere in this
        # file, that a bare substring check would false-match.
        wigs_save_payload = _read("api.ts").split(
            "wigsSave(payload: {", 1
        )[1].split("}): Promise<SaveResult>", 1)[0]
        assert 'mode?: "create";' in wigs_save_payload
        assert "mode?: string" not in wigs_save_payload

    def test_missing_rows_always_diverge_now(self):
        """Owner ruling on missing rows, option 2: no per-row
        disposition, no memory needed -- a missing row is a removal,
        full stop."""
        text = _read("ir-save-perfect-dialog.ts")
        assert "SavePlanMissingRow" in text
        assert "_renderRemovalRow" in text

    def test_the_changes_section_titles_the_delta(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert "wigs.save.changes_title" in text
        assert "changes-divider" in text

    def test_additions_are_ordinary_attestable_rows(self):
        """An addition is a command on the device with no row in the
        source wig. Second Fitting amendment v2: it travels in the
        successor and attests exactly like a matched row -- it is
        never excluded from the perfect-fit denominator the way the
        retired device-only treatment excluded it."""
        text = _read("ir-save-perfect-dialog.ts")
        assert "isAddition" in text
        assert "delta-mark add" in text
        # No filter narrows attestableRows below allRows any more.
        attestable = text.split(
            "private get _attestableRows()", 1
        )[1].split("\n    private", 1)[0]
        assert "filter" not in attestable

    def test_removals_are_struck_and_cannot_be_checked(self):
        """A removal renders for column rhythm but the checkbox is
        DISABLED -- nobody can vouch for a command that is not there
        -- and there is no TEST, since there is nothing on the device
        left to send."""
        text = _read("ir-save-perfect-dialog.ts")
        block = text.split("private _renderRemovalRow", 1)[1].split(
            "\n    private", 1
        )[0]
        assert 'type="checkbox" disabled' in block
        assert "ir-test-button" not in block
        assert "delta-mark remove" in block
        assert "wigs.save.row_leaves_wig" in block

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_changes_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "wigs.save.changes_title" in data, locale
        assert "wigs.save.row_leaves_wig" in data, locale

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_no_locale_still_carries_the_retired_keys(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for dead in (
            "wigs.save.save_as_new",
            "wigs.save.row_not_in_wig",
            "wigs.save.row_not_in_wig_note",
            "wigs.save.back_to_saved",
            "wigs.save.new_confirm_heading",
            "wigs.save.new_confirm_body",
            "wigs.save.new_confirm_yes",
        ):
            assert dead not in data, f"{locale} still has {dead}"
        assert not any(
            k.startswith("wigs.save.not_in_wig_nudge") for k in data
        ), locale


class TestSupersedeDialog:
    """v0.9.7 Second Fitting: the drop bar's replace-flow invitation --
    an arriving Wig that names a local ancestor. Second Fitting v3,
    Commit 5 retires this component's other caller (Save as new's
    self-supersession confirm): a diverged, sourced Perfect Fit save
    now mints its successor and retires the ancestor in the same
    write, so there is no second decision dialog left to open. The
    component itself, and everything below, still describes the drop
    bar exactly as before.

    Two states off one block: friendly when the local copy carries
    forward whole, guarded when it holds a row the successor lacks. The
    guard informs; REPLACE stays the primary either way (owner ruling
    2026-08-03: unfilled in the guarded state, never demoted out of the
    slot).
    """

    def test_the_drop_bar_hosts_the_component(self):
        """Second Fitting v3, Commit 5: the self-supersession caller
        (Save as new's post-save confirm) retired, so the drop bar is
        this component's only remaining live caller."""
        assert 'import "./ir-supersede-dialog.js"' in _read("ir-wigs.ts")
        assert "<ir-supersede-dialog" in _read("ir-wigs.ts")

    def test_the_state_is_derived_from_the_block_not_a_flag(self):
        """friendly vs guarded is a fact about the data -- whether the
        local copy loses a row -- not a mode the host sets. A boolean the
        caller passes could disagree with lost_digests; the derived
        getter cannot."""
        text = _read("ir-supersede-dialog.ts")
        assert "private get _guarded()" in text
        assert "lost_digests?.length" in text

    def test_the_friendly_state_reads_as_an_invitation(self):
        text = _read("ir-supersede-dialog.ts")
        assert "supersede.carried_all" in text

    def test_the_guarded_state_names_what_is_lost_in_amber(self):
        """Amber, and only here: the one place a row does not carry."""
        text = _read("ir-supersede-dialog.ts")
        assert "supersede.lost" in text
        assert ".lost-callout" in text

    def test_replace_keeps_the_primary_slot_when_guarded(self):
        """Owner ruling 2026-08-03: the guard informs, it does not
        demote. REPLACE is one button with a modifier class -- not a
        second button, not a reordering of the action row -- and it goes
        unfilled rather than trading places with KEEP BOTH."""
        joined = " ".join(_read("ir-supersede-dialog.ts").split())
        assert 'replace ${this._guarded' in joined
        guarded = _read("ir-supersede-dialog.ts").split(
            ".replace.guarded {", 1
        )[1].split("}", 1)[0]
        assert "background: none" in guarded

    def test_replace_is_disabled_until_the_host_answers(self):
        """The host re-verifies the pair server-side; REPLACE waits on
        that call. A second press mid-flight would fire a second
        supersede against a file the first already deleted."""
        text = _read("ir-supersede-dialog.ts")
        assert "?disabled=${this._busy}" in text
        replace = text.split("private _replace()", 1)[1].split(
            "private ", 1
        )[0]
        assert "if (this._busy) return;" in replace
        assert "this._busy = true;" in replace

    def test_keep_both_sends_no_supersede_call(self):
        """KEEP BOTH is the null action: both files stand, nothing is
        deleted or relinked. The doorway's handler may not reach the
        supersede endpoint."""
        wigs = _read("ir-wigs.ts")
        kb = wigs.split("private _onSupersedeKeepBoth", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "wigsSupersede" not in kb

    def test_replace_is_the_call_the_doorway_makes(self):
        """REPLACE's handler reaches the endpoint, so the button is
        wired, not inert."""
        wigs = _read("ir-wigs.ts")
        rep = wigs.split("private async _onSupersedeReplace", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "this.api.wigsSupersede(" in rep

    def test_the_top_up_choices_default_on(self):
        """A device that came from the ancestor should follow by
        default; the checkboxes let the fitter opt a device out, not have
        to opt every one in."""
        seed = _read("ir-supersede-dialog.ts").split("updated()", 1)[1].split(
            "}", 1
        )[0]
        assert "new Set(this.block.devices.map" in seed

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_supersede_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key in (
            "supersede.title",
            "supersede.body",
            "supersede.carried_all",
            "supersede.refit_note",
            "supersede.replace",
            "supersede.keep_both",
            "supersede.receipt_replaced",
            "supersede.receipt_kept",
            # Amendment v2 section 2.
            "supersede.receipt_cancelled",
            "supersede.topup_names",
            "supersede.topup_none",
            "supersede.list_and",
            "supersede.fitted_perfect",
            # Second Fitting v3 punch list round three, item 17: the
            # Update dialog's own top-chip key, not the drop-bar
            # import confirm's shared supersede.fitted_perfect above.
            "supersede.update_fitted_perfect",
            # Amendment v2 section 3: the reverse-direction import check.
            "supersede.reverse_title",
            "supersede.reverse_message",
            "supersede.reverse_import_anyway",
        ):
            assert key in data, f"{locale} missing {key}"
        for key in (
            "supersede.lost",
            # Second Fitting v3 punch list round three, item 17: the
            # add side of the same delta supersede.lost names for
            # removals.
            "supersede.added",
            "supersede.device_follows",
            # Amendment v2 section 2: names, not counts -- the old
            # count-only "supersede.topup" pair retires with it.
            "supersede.topup_more",
            "supersede.fitted_scoped",
        ):
            assert f"{key}.one" in data, f"{locale} missing {key}.one"
            assert f"{key}.other" in data, f"{locale} missing {key}.other"
        assert "supersede.topup.one" not in data, locale
        assert "supersede.topup.other" not in data, locale

    def test_cancel_is_the_drop_bar_doorways_own_button(self):
        """Owner ruling: "Cancel means undo this import." The
        self-supersession caller this component used to also serve
        (Save as new's now-retired confirm, Second Fitting v3 Commit 5)
        is gone, and with it the only reason CANCEL was ever
        conditional (Commit 6) -- it renders unconditionally now."""
        dialog = _read("ir-supersede-dialog.ts")
        assert "cancel-import" in dialog
        assert "private _cancel()" in dialog
        actions = dialog.split('<div class="dialog-actions">', 1)[1].split(
            "</div>", 1
        )[0]
        assert "this.self" not in actions
        assert "@click=${this._cancel}" in actions
        assert "common.cancel" in actions

    def test_cancel_deletes_the_arrival_and_receipts_it(self):
        """CANCEL is not Keep Both with extra steps -- it undoes the
        import outright, so the just-written file goes away."""
        wigs = _read("ir-wigs.ts")
        assert "@cancel-import=${this._onSupersedeCancelImport}" in wigs
        handler = wigs.split(
            "private async _onSupersedeCancelImport", 1
        )[1].split("\n    private", 1)[0]
        assert "this.api.wigsDelete(s.newFilename)" in handler
        assert "supersede.receipt_cancelled" in handler

    def test_cancel_guards_against_a_second_press(self):
        """Mirrors REPLACE's own guard: the host call is in flight once,
        never twice."""
        cancel = _read("ir-supersede-dialog.ts").split(
            "private _cancel()", 1
        )[1].split("\n    private", 1)[0]
        assert "if (this._busy) return;" in cancel
        assert "this._busy = true;" in cancel

    def test_top_up_names_the_missing_commands_not_just_counts(self):
        """Amendment v2 section 2: "Add Timer and Breeze Mode to
        {device}", not a bare count -- the old ``missing_commands``
        pluralization is gone from the row."""
        text = _read("ir-supersede-dialog.ts")
        assert "d.missing_aliases" in text
        assert "supersede.topup_names" in text
        assert "supersede.topup_none" in text
        assert '"supersede.topup"' not in text
        names = text.split("private _formatNames", 1)[1].split(
            "\n    render()", 1
        )[0]
        assert "MAX = 4" in names
        assert "supersede.topup_more" in names

    def test_the_graded_ceremony_reads_old_fittings(self):
        """Amendment v2 section 2: no claims is light (nothing extra
        renders); scoped names who tried; a PERFECT FIT gets the same
        amber-family weight as a lost row."""
        text = _read("ir-supersede-dialog.ts")
        assert "block?.old_fittings" in text
        assert "supersede.fitted_scoped" in text
        assert "supersede.fitted_perfect" in text
        assert ".fitted-line" in text
        assert ".fitted-callout" in text

    def test_the_self_doorway_support_is_retired(self):
        """Second Fitting v3, Commit 6: the self-supersession caller
        (Save as new's post-save confirm) has been gone since Commit 5,
        and nothing left calling this component ever sets self or
        viewerHandle -- the drop bar (this component's sole remaining
        caller) never did. The dead props and the branching they drove
        do not ride along. The equivalent filtering rule lives on where
        it is actually used, ported inline in ir-save-perfect-dialog.ts's
        own closing screen (Commit 5), covered separately in
        TestThePerfectFitDialog."""
        text = _read("ir-supersede-dialog.ts")
        assert "public self" not in text
        assert "public viewerHandle" not in text
        assert "this.self" not in text
        assert "this.viewerHandle" not in text
        fitted = text.split("private get _fitted()", 1)[1].split(
            "\n    updated()", 1
        )[0]
        # Nobody left to credit is nobody left to credit -- an anonymous
        # fitting with no handle at all still empties the list.
        assert "if (!who.length) return null;" in fitted


class TestReverseImportCheck:
    """Amendment v2 section 3 (owner bench find): ancestry only ever
    points backward, so a re-dropped ORIGINAL wig, once its successor
    already exists in this closet, would otherwise file as a silent
    twin nothing else in the funnel ever notices. The dialog fires
    BEFORE filing -- unlike the forward doorway's CANCEL, which deletes
    an arrival already written, Cancel here means the upload never
    happened at all."""

    def test_the_dialog_reuses_the_plain_confirm_not_the_doorway(self):
        """Only one decision here -- Import Anyway or Cancel -- so the
        elaborate replace/keep-both/cancel component would be the wrong
        anatomy. The plain two-action ir-confirm-dialog, already used
        for the clip-matrix confirm, is the right size."""
        wigs = _read("ir-wigs.ts")
        render = wigs.split(
            "private _renderReverseSupersede()", 1
        )[1].split("\n    private", 1)[0]
        assert "<ir-confirm-dialog" in render
        assert "<ir-supersede-dialog" not in render
        assert "supersede.reverse_title" in render
        assert "supersede.reverse_message" in render
        assert "supersede.reverse_import_anyway" in render

    def test_import_anyway_resends_the_same_upload_confirmed(self):
        """Cancel just drops the held state; Import Anyway is the one
        path that actually resends -- with the SAME text and filename
        the first call held onto, and confirmed set so the check does
        not fire a second time on the identical text."""
        wigs = _read("ir-wigs.ts")
        render = wigs.split(
            "private _renderReverseSupersede()", 1
        )[1].split("\n    private", 1)[0]
        assert "@confirmed=" in render
        assert (
            "this._uploadText(target.text, target.filename, true)"
            in render
        )
        assert (
            "@closed=${() => (this._reverseSupersede = null)}" in render
        )

    def test_cancel_deletes_nothing_unlike_the_forward_doorway(self):
        """Nothing has filed yet while this dialog is open, so its
        Cancel is a pure state drop -- no wigsDelete call anywhere near
        it, unlike the forward doorway's own CANCEL button."""
        wigs = _read("ir-wigs.ts")
        render = wigs.split(
            "private _renderReverseSupersede()", 1
        )[1].split("\n    private", 1)[0]
        assert "wigsDelete" not in render

    def test_the_check_is_read_before_the_generic_failure_branch(self):
        """A blocked reverse-supersession response is NOT a failure --
        result.success is still true -- so the generic
        ``!result.success`` branch must never see it first, or a normal
        drop-bar arrival would flash a false "upload failed" line before
        the dialog ever had a chance to render."""
        wigs = _read("ir-wigs.ts")
        body = wigs.split(
            "private async _uploadText", 1
        )[1].split("\n    private", 1)[0]
        assert "result.reverse_supersession" in body
        assert "!result.success" in body
        assert body.index("result.reverse_supersession") < body.index(
            "!result.success"
        )

    def test_the_held_state_carries_what_a_resend_needs(self):
        """Import Anyway has to resend the identical text against the
        identical filename -- both have to survive from the first call
        to the confirm, since nothing else in the component remembers
        them."""
        text = _read("ir-wigs.ts")
        assert "_reverseSupersede:" in text
        state = text.split("_reverseSupersede:", 1)[1].split(
            "| null = null;", 1
        )[0]
        assert "text: string;" in state
        assert "filename: string;" in state

    def test_the_api_call_only_sends_confirmed_when_true(self):
        """A bare always-present flag would put ``confirmed: false`` on
        every ordinary drop; the guard is that a fresh upload's message
        never carries the key at all, matching the optional-filename
        convention already on this call."""
        api = _read("api.ts")
        wu = api.split("wigsUpload(", 1)[1].split(
            "\n    wigsSupersede", 1
        )[0]
        assert "confirmed?: boolean" in wu
        assert "reverse_supersession?: ReverseSupersessionBlock" in wu
        assert "if (confirmed) msg.confirmed = true;" in wu


class TestTheSaveDialogsStopSwappingHaDialog:
    """Bench fix (2026-08-07): "Saving a new wig, perfect fitting a
    wig, or updating a wig no longer pops up the confirmation that the
    wig was created." Reproduced live: the form and the receipt were
    two separate ``<ha-dialog>`` elements, swapped on save. As of HA
    2026.7, ``<ha-dialog>`` opens a real native ``<dialog>`` under the
    hood (``showModal()``); removing one mid-transition to open the
    other raced the outgoing ``close()`` against the incoming
    ``showModal()`` -- an uncaught ``InvalidStateError: Transition was
    aborted``, seen in the browser console, that took the whole dialog
    off-screen before the receipt ever painted. The save itself always
    succeeded; only the confirmation was crashing invisibly.

    This retires ``TestTheConfirmThatKilledItself``'s guard along with
    the swap it protected against: the shadow-containment check in
    ``_close`` existed only because the form's ``<ha-dialog>`` could be
    swapped out from under a still-firing event. One ``<ha-dialog>``
    now stays open for each dialog's whole life -- there is nothing
    left to swap, and nothing left for ``_close`` to guard against.
    """

    @pytest.mark.parametrize(
        "component",
        (
            "ir-save-new-dialog.ts",
            "ir-save-update-dialog.ts",
            "ir-save-perfect-dialog.ts",
        ),
    )
    def test_exactly_one_ha_dialog_opens_per_component(self, component):
        """Scoped to render()'s own body, not the whole file -- the
        bench-fix doc comments above it mention <ha-dialog> in prose
        too, and counting those would make this test lie."""
        text = _read(component)
        body = text.split("render() {", 1)[1].split("\n    }", 1)[0]
        assert body.count("<ha-dialog") == 1

    @pytest.mark.parametrize(
        "component",
        (
            "ir-save-new-dialog.ts",
            "ir-save-update-dialog.ts",
            "ir-save-perfect-dialog.ts",
        ),
    )
    def test_close_no_longer_checks_shadow_containment(self, component):
        """The guard protected against a stale event from a REMOVED
        dialog. With nothing removed and re-added anymore, a plain
        dispatch is both sufficient and honest about why."""
        text = _read(component)
        body = text.split("private _close(): void {", 1)[1]
        body = body.split("\n    }", 1)[0]
        assert "shadowRoot" not in body
        assert 'new CustomEvent("closed"' in body

    @pytest.mark.parametrize(
        "component",
        (
            "ir-save-new-dialog.ts",
            "ir-save-update-dialog.ts",
            "ir-save-perfect-dialog.ts",
        ),
    )
    def test_done_content_no_longer_wraps_its_own_dialog(self, component):
        """``_renderDone`` used to open a second ``<ha-dialog>``; it now
        returns bare content that the one persistent dialog wraps."""
        text = _read(component)
        done = text.split("private _renderDone()", 1)[1]
        done = done.split("\n    private", 1)[0]
        assert "<ha-dialog" not in done


class TestNoSuccessionSaveIsSilent:
    """Bench addendum ruling (2026-08-05): v2 hung the whole checklist
    inside the perfect-fit box, so an unfitted SUCCESSION save showed
    nothing -- no checklist, no delta, no hint that saving was about
    to mint a successor. The changes section now renders on any
    succession, armed or not; CREATE and plain UPDATE are untouched,
    since only a diverged digest set ever set ``_isSuccession`` true."""

    def test_the_list_renders_on_any_succession_not_just_when_armed(self):
        text = _read("ir-save-perfect-dialog.ts")
        body = text.split("private _renderFitting()", 1)[1]
        body = body.split("\n    private", 1)[0]
        assert "this._isSuccession" in body
        # The attestation block is a separate condition and stays
        # perfect-fit only -- unarmed, nothing is being signed, so
        # there is nothing there to show regardless of the verb.
        # Second Fitting v3 punch list item 3: "armed" is now a
        # computed getter (route choice IS the arming), not a
        # manually-ticked field -- same gate, new name.
        attest_call = body.split("this._renderAttestation()", 1)[0]
        assert "this._armed ? " in attest_call.rsplit("${", 1)[1]

    def test_the_list_computes_read_only_for_an_unarmed_succession(self):
        text = _read("ir-save-perfect-dialog.ts")
        body = text.split("private _renderList()", 1)[1]
        body = body.split("\n    private", 1)[0]
        assert "const readOnly = succession && !this._armed;" in body
        assert "this._renderRow(row, false, readOnly)" in body
        assert "this._renderRow(row, true, readOnly)" in body
        # The "N of M checked" downgrade line reads as a partial
        # attestation -- wrong message entirely for a preview where
        # nothing is checkable at all.
        assert "readOnly || this._isPerfectFit" in body

    def test_a_read_only_row_disables_and_unchecks_the_box(self):
        text = _read("ir-save-perfect-dialog.ts")
        body = text.split("private _renderRow(", 1)[1]
        body = body.split("\n    private", 1)[0]
        assert "readOnly = false" in body.split(")", 1)[0]
        assert "const checked = readOnly ? false" in body
        assert "?disabled=${readOnly}" in body
        # Nobody can decline a row they cannot check.
        assert '${checked || readOnly ? "" : this._renderReasons(row)}' in body

    def test_create_and_plain_update_stay_silent_unarmed(self):
        """The clause is ``this._armed || this._isSuccession``
        specifically -- not a blanket drop of the perfect-fit gate,
        which would have put the checklist in front of every CREATE
        and UPDATE whether anything diverged or not. Second Fitting v3
        punch list item 3: ``_armed`` is the computed getter (route
        choice IS the arming) that replaced the old manually-ticked
        ``_perfect`` field."""
        text = _read("ir-save-perfect-dialog.ts")
        body = text.split("private _renderFitting()", 1)[1]
        body = body.split("\n    private", 1)[0]
        list_call = body.split("this._renderList()", 1)[0]
        assert "this._armed || this._isSuccession" in list_call
        assert "this._isSuccession" in list_call.rsplit("||", 1)[1]


class TestTheDecisionWindow:
    """Second Fitting v3: SAVE TO CLOSET opens a small decision window
    first, always, instead of deriving a verb silently and asking the
    replace question after the save. Three routes -- SAVE AS NEW,
    UPDATE CLOSET WIG, VALIDATE FOR PERFECT FIT -- each meant to open
    its own dialog with no morphing between them (owner: "each of
    those dialogs is their own"). Commit 3 builds and wires the window
    itself; Commits 4-5 give two of its three routes their own real
    destination -- until then every route opens the one save dialog
    that exists today, carrying the plan the window already fetched.
    """

    def test_three_routes_render_in_the_route_list(self):
        text = _read("ir-save-route-dialog.ts")
        route_list = text.split('<div class="route-list">', 1)[1].split(
            "</div>", 1
        )[0]
        for key in (
            "wigs.route.save_as_new",
            "wigs.route.update_closet_wig",
            "wigs.route.validate_perfect_fit",
        ):
            assert key in route_list, key

    def test_update_is_gated_on_a_source_wig(self):
        """Owner: "if somebody created a device that doesn't have a
        wig, there is nothing to update." Second Fitting v3 punch list
        item 6: the gate is now a public ``hasSource`` property the
        host sets synchronously from the device's own
        ``source_wig_id`` -- known before the plan fetch even starts,
        so the route list is correct on first paint and never shifts
        once the plan streams in."""
        text = _read("ir-save-route-dialog.ts")
        assert "@property({ type: Boolean }) public hasSource = false;" in text
        route_list = text.split('<div class="route-list">', 1)[1].split(
            "</div>", 1
        )[0]
        idx = route_list.index("wigs.route.update_closet_wig")
        assert "this.hasSource" in route_list[max(0, idx - 300):idx]
        # SAVE AS NEW and VALIDATE FOR PERFECT FIT stay offered
        # regardless of divergence (spec section 1) -- only UPDATE is
        # conditional in this list.
        new_idx = route_list.index("wigs.route.save_as_new")
        assert "this.hasSource" not in route_list[max(0, new_idx - 80):new_idx]

    def test_the_summary_covers_matching_diverged_and_from_scratch(self):
        text = _read("ir-save-route-dialog.ts")
        summary = text.split("private get _summaryLine()", 1)[1].split(
            "\n    private", 1
        )[0]
        # From-scratch: no source to compare against, no line at all.
        # Also null while the plan is still in flight (item 6) --
        # the skeleton placeholder covers that case in render().
        assert "if (!this.plan || !this.hasSource) return null;" in summary
        # Matching: the plan's own derived verb decides it, never a
        # second comparison done here.
        assert 'this.plan.variant !== "succession"' in summary
        assert "wigs.route.summary_matches" in summary
        # Diverged: counted off the same rows / missing_rows the
        # checklist below already draws its own list from.
        assert "r.matched" in summary
        assert "this.plan.missing_rows.length" in summary
        assert "wigs.route.summary_diverged" in summary

    def test_cancel_closes_the_window_and_fires_no_route(self):
        text = _read("ir-save-route-dialog.ts")
        close = text.split("private _close(): void", 1)[1].split(
            "\n    private", 1
        )[0]
        assert '"closed"' in close
        assert '"route"' not in close
        actions = text.split('<div class="dialog-actions">', 1)[1].split(
            "</div>", 1
        )[0]
        assert "this._close" in actions
        assert "common.cancel" in actions
        # The overlay's own click-outside is the same close, not a
        # second, silently-different exit.
        assert '<div class="overlay" @click=${this._close}>' in text

    def test_save_to_closet_opens_the_window_not_the_old_dialog_directly(
        self,
    ):
        detail = _read("ir-device-detail.ts")
        assert "@click=${this._openSaveRoute}" in detail
        assert "@click=${() => (this._saveWigOpen = true)}" not in detail
        opener = detail.split(
            "private async _openSaveRoute()", 1
        )[1].split("\n    private", 1)[0]
        assert "this.api.wigsSavePlan(" in opener
        assert "this._saveRoutePlan =" in opener
        # A failed fetch still gets the person to a working dialog
        # rather than a dead button -- Commit 4 renamed the flag but
        # kept the same fallback: land on the interim Perfect-Fit-route
        # dialog, which retries the fetch itself.
        assert 'this._saveRoute = "perfect";' in opener

    def test_the_window_and_the_next_dialog_never_show_together(self):
        """Second Fitting v3 punch list item 6: the window's own
        visibility now gates on ``_saveRouteOpen`` (set synchronously
        the moment SAVE TO CLOSET is chosen) rather than waiting on
        the plan fetch to land -- but the mutual-exclusion with
        whichever dialog the chosen route opens next is unchanged."""
        joined = " ".join(_read("ir-device-detail.ts").split())
        assert (
            "this._saveRouteOpen && !this._saveRoute ? html`<ir-save-route-dialog"
            in joined
        )

    def test_the_fetched_plan_rides_into_the_next_dialog_unrefetched(self):
        """The window fetches the plan once; whichever dialog the
        chosen route opens next reads that same object, never calling
        wigsSavePlan a second time for the same click."""
        detail = _read("ir-device-detail.ts")
        assert ".plan=${this._saveRoutePlan}" in detail
        save = _read("ir-save-perfect-dialog.ts")
        assert "public plan: SavePlan | null = null;" in save
        first_updated = save.split("async firstUpdated()", 1)[1].split(
            "\n    /**", 1
        )[0]
        assert "this.plan ??" in first_updated

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_route_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key in (
            "wigs.route.source_from",
            "wigs.route.source_none",
            "wigs.route.summary_matches",
            "wigs.route.summary_diverged",
            "wigs.route.save_as_new",
            "wigs.route.update_closet_wig",
            "wigs.route.validate_perfect_fit",
        ):
            assert key in data, f"{locale} missing {key}"
        for key in ("wigs.route.added", "wigs.route.removed"):
            assert f"{key}.one" in data, f"{locale} missing {key}.one"
            assert f"{key}.other" in data, f"{locale} missing {key}.other"


class TestTheStrippedSaveDialogs:
    """Second Fitting v3, Commit 4: Save as New and Update Closet Wig
    are their own dialogs now, both built off the metadata form alone
    -- no perfect-fit checkbox, no checklist, no attestation. That
    ceremony stays exclusive to Validate for Perfect Fit (Commit 5).
    """

    @pytest.mark.parametrize(
        "component", ("ir-save-new-dialog.ts", "ir-save-update-dialog.ts"),
    )
    def test_neither_stripped_dialog_carries_the_old_ceremony(
        self, component,
    ):
        text = _read(component)
        for token in (
            "perfect_label", "_renderList(", "_renderRow(",
            "_renderAttestation", "fit-check", "ir-tx-knobs",
            "ir-test-button",
        ):
            assert token not in text, f"{component} still has {token}"

    def test_both_stripped_dialogs_share_the_metadata_fields_module(self):
        for component in (
            "ir-save-new-dialog.ts", "ir-save-update-dialog.ts",
        ):
            text = _read(component)
            assert 'from "./ir-save-metadata-fields.js"' in text
            assert "renderMetadataFields(" in text

    def test_save_as_new_never_reads_the_supersession_block(self):
        """Spec section 2 / section 6: the post-save self-doorway
        confirm retires as a decision point. Save as New's receipt
        never opens ir-supersede-dialog, whatever the result carries."""
        text = _read("ir-save-new-dialog.ts")
        assert "supersession" not in text
        assert "ir-supersede-dialog" not in text

    def test_save_as_new_never_sends_replace(self):
        save = _read("ir-save-new-dialog.ts").split(
            "private async _save()", 1,
        )[1].split("\n    render()", 1)[0]
        assert "replace" not in save

    def test_update_sends_replace_only_when_diverged(self):
        text = _read("ir-save-update-dialog.ts")
        save = text.split("private async _save()", 1)[1].split(
            "\n    render()", 1
        )[0]
        assert "this._diverged ? { replace: true }" in " ".join(
            save.split()
        )

    def test_the_graded_and_lost_rows_lines_are_diverged_only(self):
        text = _read("ir-save-update-dialog.ts")
        graded = text.split("private get _gradedLine()", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "if (!this._diverged) return null;" in graded
        assert "supersede.update_fitted_perfect" in graded
        assert "supersede.fitted_scoped" in graded
        lost = text.split("private get _lostRowsLine()", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "if (!this._diverged) return null;" in lost
        assert "supersede.lost" in lost
        assert "this.plan.missing_rows" in lost

    def test_a_stale_replace_refusal_reopens_the_window_not_an_error(self):
        """Coding plan Commit 4: the not_diverged refusal from Commit 2
        surfaces as a plain re-open of the decision window with a
        fresh plan, not a banner the person has to dismiss by hand."""
        dialog = _read("ir-save-update-dialog.ts")
        save = dialog.split("private async _save()", 1)[1].split(
            "\n    render()", 1
        )[0]
        assert 'code === "not_diverged"' in save
        assert '"stale-replace"' in save
        detail = _read("ir-device-detail.ts")
        assert "@stale-replace=${this._onStaleReplace}" in detail
        handler = detail.split(
            "private _onStaleReplace = async ()", 1
        )[1].split("\n    private", 1)[0]
        assert "this._saveRoute = null;" in handler
        assert "this._openSaveRoute()" in handler

    def test_the_window_routes_new_and_update_to_their_own_dialogs(self):
        detail = _read("ir-device-detail.ts")
        joined = " ".join(detail.split())
        assert (
            'this._saveRoute === "new" && this._saveRoutePlan ? html`<ir-save-new-dialog'
            in joined
        )
        assert (
            'this._saveRoute === "update" && this._saveRoutePlan ? html`<ir-save-update-dialog'
            in joined
        )
        assert (
            'this._saveRoute === "perfect" ? html`<ir-save-perfect-dialog'
            in joined
        )

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_receipt_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key in (
            "wigs.route.replaced_receipt", "wigs.route.updated_metadata",
        ):
            assert key in data, f"{locale} missing {key}"


class TestThePerfectFitDialog:
    """Second Fitting v3, coding plan Commit 5: the perfect-fit section
    of the old combined dialog promoted to its own dialog and its own
    route, retiring ir-save-wig-dialog.ts -- the file every other
    stripped dialog was already extracted out of. The checklist, TEST,
    the changes section, and the signing rules ride over unchanged
    (pinned by the renamed classes above); what this class pins is new:
    the always-replaces rule, the retirement of the post-save confirm,
    and the routing that points here instead of the retired combined
    dialog.
    """

    def test_the_old_combined_dialog_is_retired(self):
        assert not (SRC / "ir-save-wig-dialog.ts").exists()

    def test_diverged_sourced_saves_always_replace(self):
        """Owner ruling: "ALWAYS replaces." Picking this route and
        signing the oath already was the decision, so the mint and the
        retirement happen in the same write -- no second confirm left
        to ask it again."""
        text = _read("ir-save-perfect-dialog.ts")
        save_device = text.split("private async _saveDevice()", 1)[1]
        save_device = save_device.split("\n    private", 1)[0]
        assert (
            "this._isSuccession ? { replace: true }" in " ".join(
                save_device.split()
            )
        )

    def test_replace_never_fires_without_a_diverged_source(self):
        """A from-scratch mint or a plain matching UPDATE has nothing
        to replace -- the same ternary that arms replace on succession
        is the only thing that could ever send it, and it is gated on
        _isSuccession alone, never a blanket true."""
        text = _read("ir-save-perfect-dialog.ts")
        save_device = text.split("private async _saveDevice()", 1)[1]
        save_device = save_device.split("\n    private", 1)[0]
        assert save_device.count("replace: true") == 1

    def test_no_keep_both_anywhere_in_this_flow(self):
        """Spec acceptance item 5: no Keep Both anywhere in this flow.
        The retired self-supersede machinery -- the second confirm's
        import, its markup, and its state -- carries none of it
        forward. The component itself is still named in an explanatory
        comment (the top-up seed mirrors its `updated()` pattern), so
        this checks USAGE, not the bare name."""
        text = _read("ir-save-perfect-dialog.ts")
        assert '<ir-supersede-dialog' not in text
        assert 'ir-supersede-dialog.js' not in text
        for dead in (
            "_selfSupersede",
            "_closeAll",
            "_renderSelfSupersede",
            "keep-both",
            "KeepBoth",
        ):
            assert dead not in text, dead

    def test_the_closing_screen_is_a_pure_notification_on_a_replace(self):
        """Second Fitting v3 punch list item 13 (supersedes round one
        item 5's anatomy above): no REPLACE / KEEP BOTH choice on the
        closing screen, and no top-up offer either -- the decision
        already happened, and a device wanting the successor's new
        commands picks them up through the adopt path instead. The
        receipt is a pure notification: both names bold and blue, one
        CLOSE button, nothing else."""
        text = _read("ir-save-perfect-dialog.ts")
        render_done = text.split("private _renderDone()", 1)[1]
        render_done = render_done.split("\n    private", 1)[0]
        replaced_branch = render_done.split("if (replaced) {", 1)[1]
        replaced_branch = replaced_branch.split("const line =", 1)[0]
        assert "this._renderReplacedLine(" in replaced_branch
        assert "wigs.route.replaced_receipt" not in replaced_branch
        assert "_renderTopup" not in replaced_branch
        assert "topupCandidates" not in replaced_branch
        assert replaced_branch.count('t("common.close")') == 1
        assert "common.cancel" not in replaced_branch

    def test_the_top_up_machinery_is_retired_from_this_dialog(self):
        """Second Fitting v3 punch list item 13: the top-up offer that
        used to live on this dialog's closing screen -- state, getters,
        methods, the updated() seeding hook, the CSS, the
        SupersedeDevice import -- is gone with the receipt it used to
        sit under. A device wanting the successor's new commands picks
        them up through the adopt path instead, not a second act
        bolted onto the receipt."""
        text = _read("ir-save-perfect-dialog.ts")
        for dead in (
            "_sendTopup",
            "_saveAndClose",
            "_formatTopupNames",
            "_toggleTopup",
            "_topupCandidates",
            "_topupDevices",
            "wigsTopUp",
            "_renderTopup",
            "SupersedeDevice",
        ):
            assert dead not in text, dead

    def test_the_graded_line_filters_the_signers_own_handle(self):
        """Ported from ir-supersede-dialog's self doorway, and renamed
        by Second Fitting v3 punch list item 13 when the line moved
        from the closing screen to before the click: replacing a wig
        you yourself just fitted needs no warning about yourself."""
        text = _read("ir-save-perfect-dialog.ts")
        graded = text.split("private get _gradedLine()", 1)[1]
        graded = graded.split("\n    private", 1)[0]
        assert "this._handle.trim().toLowerCase()" in graded
        assert "if (!who.length) return null;" in graded

    def test_the_dialog_wears_one_heading(self):
        """No morphing (spec section 1): the route's dialog wears one
        name, form or done, CREATE or UPDATE or SUCCESSION alike.
        Bench fix (2026-08-07) folded the done screen's two branches
        back into the one <ha-dialog> that now stays open for the
        component's whole life (TestTheSaveDialogsStopSwappingHaDialog),
        so there is exactly one heading site left to name, not three."""
        text = _read("ir-save-perfect-dialog.ts")
        headings = re.findall(
            r'heading=\$\{t\("([^"]+)"\)\}', text
        )
        assert headings == ["wigs.route.validate_perfect_fit"]

    def test_the_form_uses_the_shared_metadata_module(self):
        """Consistent with Save as New and Update Closet Wig
        (TestTheStrippedSaveDialogs): one metadata form, one module."""
        text = _read("ir-save-perfect-dialog.ts")
        assert 'from "./ir-save-metadata-fields.js"' in text
        assert "renderMetadataFields(" in text

    def test_the_route_wires_to_the_new_dialog(self):
        detail = _read("ir-device-detail.ts")
        assert 'import "./ir-save-perfect-dialog.js";' in detail
        assert 'import "./ir-save-wig-dialog.js";' not in detail

    def test_the_top_up_only_endpoint_call_is_retired_from_the_api(self):
        """Second Fitting v3 punch list item 13: wigsTopUp() had
        exactly one caller in the whole frontend -- this dialog's own
        _sendTopup(), itself retired above -- and is removed with it.
        The underlying ws_wigs_supersede endpoint and its topup_only
        branch stay in service for wigsSupersede(), ir-wigs.ts's own
        adopt path."""
        text = _read("api.ts")
        assert "wigsTopUp(" not in text
        assert "wigsSupersede(" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_perfect_fit_vocabulary(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        # Second Fitting v3 punch list item 5: the checklist's own
        # "N of M checked" line and the standard Save/Cancel anatomy
        # replaced the old dedicated top-up confirm button and its
        # "sent" receipt -- wigs.route.send_topup and
        # wigs.route.topup_sent are retired, see
        # TestTheSweepThatClosedTheSecondFork below.
        assert "wigs.route.topup_offer" in data, f"{locale} missing key"

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_same_key_notice_vocabulary(self, locale):
        """Second Fitting v3 punch list item 1: the same-fitter
        re-sign notice named up front, before the click."""
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "wigs.save.same_key_notice" in data, f"{locale} missing key"


class TestTheSweepThatClosedTheSecondFork:
    """Second Fitting v3 punch list, item 5: the closing confirm lost
    its dedicated top-up button and "sent" receipt when the block
    collapsed to standard Save/Cancel anatomy with an inline checklist
    -- these two keys outlived the markup that read them, the same
    shape as TestTheSweepThatClosedTheFork above for Commit 6."""

    def test_the_retired_topup_keys_are_gone_from_the_dialog(self):
        text = _read("ir-save-perfect-dialog.ts")
        assert "wigs.route.send_topup" not in text
        assert "wigs.route.topup_sent" not in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_dead_topup_keys_carry_no_locale_entry(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "wigs.route.send_topup" not in data
        assert "wigs.route.topup_sent" not in data


class TestTheSweepThatClosedTheFork:
    """Second Fitting v3, coding plan Commit 6: the sweep. Nothing new
    for the user to see -- this class pins the two loose ends the build
    order deliberately left for last: a locale key that outlived the
    dialog that used it, and a plural gap the delta summary shipped
    with in Commit 3 (Polish and Russian resolve counts of 2-4 and 5+
    to "few"/"many" categories that were never filled, so those counts
    silently fell back to the "other" string instead)."""

    def test_the_retired_dialogs_own_heading_key_is_gone(self):
        """wigs.save.update_heading belonged to the single shared
        heading the old combined dialog toggled between CREATE and
        UPDATE. Commits 3-5 gave every routed dialog its own dedicated
        heading key instead (wigs.route.save_as_new,
        wigs.route.update_closet_wig, wigs.route.validate_perfect_fit),
        so nothing has read this key since the combined dialog was
        retired in Commit 5."""
        assert "wigs.save.update_heading" not in _read("ir-device-detail.ts")
        for name in (
            "ir-save-route-dialog.ts",
            "ir-save-new-dialog.ts",
            "ir-save-update-dialog.ts",
            "ir-save-perfect-dialog.ts",
        ):
            assert "wigs.save.update_heading" not in _read(name)

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_dead_heading_key_carries_no_locale_entry(self, locale):
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert "wigs.save.update_heading" not in data

    @pytest.mark.parametrize("locale", ("pl", "ru"))
    @pytest.mark.parametrize("base", ("wigs.route.added", "wigs.route.removed"))
    def test_the_delta_summary_carries_every_slavic_plural_category(
        self, locale, base
    ):
        """Commit 3 shipped one/other for the delta summary's added/
        removed counts but left few/many missing on the two locales
        whose plural rules actually have those categories -- every
        other pluralized key in pl.json and ru.json carries all four
        (see e.g. wigs.signals, comb.diag_count), so a count of 2-4 or
        5+ was silently falling back to the "other" string's grammar
        instead of the correct one."""
        data = json.loads(
            (LOCALES / f"{locale}.json").read_text(encoding="utf-8")
        )
        for category in ("one", "few", "many", "other"):
            key = f"{base}.{category}"
            assert key in data, f"{locale} missing {key}"
