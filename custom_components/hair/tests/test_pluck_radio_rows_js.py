"""A plucked radio row looks and opens like a Clipper radio row.

A Broadlink store can now be plucked for radio, so a plucked remote can
hold radio rows, or only radio rows. The Plucker drew every row as
infrared: the stored ``frequency`` (the infrared field's default, 38 kHz)
as its carrier, the infrared protocol pill, and no edit button (that was
gated on ``code``, which a radio row does not carry). These tests read
the tab's source, the house tactic for render code, and pin it to the
Clipper's radio row: the family pill, the band, the radio editor, and the
Test dialog offering radio transmitters with a refusal said as a toast.
"""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).parent.parent / "frontend" / "src"


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _row() -> str:
    body = _read("ir-pluck.ts")
    return body.split("private _renderSignal(deviceId", 1)[1].split(
        "private _renderDialogs(", 1
    )[0]


class TestTheRow:
    def test_a_radio_row_gets_its_family_pill(self):
        row = _row()
        assert 'sig.medium === "rf"' in row
        assert "<ir-protocol-chip .family=${sig.rf_family ?? null}>" in row

    def test_an_infrared_row_keeps_its_interactive_pill(self):
        row = _row()
        assert "@toggle-bypass=" in row
        assert "interactive" in row

    def test_the_carrier_is_the_band_for_radio(self):
        """Not the stored 38 kHz a radio row carries by default."""
        body = _read("ir-pluck.ts")
        row = _row()
        assert "${pluckCarrier(sig)}" in row
        assert "Math.round(sig.frequency / 1000)" not in row
        helper = body.split("function pluckCarrier(", 1)[1].split("\n}\n", 1)[0]
        assert "carrierParts(sig)" in helper
        assert 't("listen.band", { band: parts.band })' in helper

    def test_a_radio_row_has_the_edit_button(self):
        row = _row()
        assert 'sig.code || sig.medium === "rf"' in row


class TestTheEditor:
    def test_a_radio_row_opens_the_radio_editor(self):
        body = _read("ir-pluck.ts")
        dialogs = body.split("private _renderDialogs(", 1)[1]
        rf = dialogs.index('this._editSignal?.signal.medium === "rf"')
        assert rf < dialogs.index("<ir-rf-editor")
        assert dialogs.index("<ir-rf-editor") < dialogs.index("<ir-signal-editor")
        assert 'import "./ir-rf-editor.js";' in body

    def test_the_radio_editor_gets_the_row_as_the_clipper_passes_it(self):
        dialogs = _read("ir-pluck.ts").split("private _renderDialogs(", 1)[1]
        editor = dialogs.split("<ir-rf-editor", 1)[1].split("</ir-rf-editor>", 1)[0]
        for prop in (
            ".initialFrame=",
            ".initialFrequencyHz=",
            ".initialGapUs=",
            ".initialAlias=",
            ".initialSendCount=${assignSendCount(",
            ".initialFamily=",
            "@signal-edited=${this._onSignalEdited}",
        ):
            assert prop in editor, prop


class TestTheTest:
    def test_the_dialog_offers_the_rows_medium(self):
        dialogs = _read("ir-pluck.ts").split("private _renderDialogs(", 1)[1]
        test = dialogs.split("<ir-test-emitter-dialog", 1)[1].split(
            "</ir-test-emitter-dialog>", 1
        )[0]
        assert '.media=${[this._testDialog.signal.medium ?? "ir"]}' in test
        assert ".rfFrequencyHz=" in test

    def test_a_refusal_is_said_as_a_toast(self):
        """A rolling code is never sent: the server refuses it, and the
        tab says why, as the Clipper does."""
        body = _read("ir-pluck.ts")
        send = body.split("private async _sendTest(", 1)[1].split(
            "private _hasTrigger(", 1
        )[0]
        assert "testRefusal(r.reason, this._emitterName(emitters[i]), band)" in send
        assert "this._showToast(refused)" in send
