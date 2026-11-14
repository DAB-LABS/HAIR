"""Radio trigger fix, the panel's part (answer 5).

"Make a Device" from a radio Remote: the transmitter picker offers the
Remote's own kinds, the dialog names the buttons that still need a
press, and the server's ``rf_no_frame`` refusal is said in a sentence.

Pinned in the source, the house style for panel wiring; the emitter
picker's media rule itself runs under node in ``test_rf_send_js.py``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

COMPONENT = Path(__file__).parent.parent
SRC = COMPONENT / "frontend" / "src"
LOCALES = SRC / "locales"


def _src(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_src(name).split())


def _method(source: str, name: str) -> str:
    """The body of one class method, from its signature to the next
    member, which is any line indented exactly four spaces that is not
    the method's own closing brace."""
    start = re.search(rf"\n    (?:\w+ )*{re.escape(name)}\(", source)
    assert start, name
    rest = source[start.end():]
    end = re.search(r"\n    [^\s}]", rest)
    return rest[: end.start()] if end else rest


def _locale(lang: str) -> dict[str, str]:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


class TestThePickerTakesTheRemotesKinds:
    def test_the_devices_page_passes_the_remotes_media(self):
        # An empty list (a Remote with no triggers yet) would offer no
        # kind at all, so it reads as both, like a missing one.
        assert (
            ".media=${this._makeDeviceSource.media?.length ? this._makeDeviceSource.media : null}"
        ) in _flat("ir-device-list.ts")

    def test_the_dialog_hands_it_to_the_picker(self):
        flat = _flat("ir-promote-dialog.ts")
        assert "public media: Medium[] | null = null;" in flat
        picker = "<ir-emitter-picker .hass=${this.hass} .api=${this.api} .media=${this.media}"
        assert picker in flat

    def test_every_other_door_keeps_both_kinds(self):
        # Only the Remote door sets media; a wig, a codebook or a
        # Sniffer row leaves it null, which the picker reads as both.
        assert _src("ir-device-list.ts").count("<ir-promote-dialog") == 1
        for name in ("ir-clips.ts", "ir-wigs.ts", "ir-signal-monitor.ts", "ir-pluck.ts"):
            src = _src(name)
            assert "<ir-promote-dialog" in src, name
            for block in src.split("<ir-promote-dialog")[1:]:
                assert ".media=" not in block.split("</ir-promote-dialog>", 1)[0], name


class TestTheWaitingButtonsAreNamed:
    def test_the_result_type_carries_them(self):
        types = _flat("types.ts")
        assert "export interface RemoteNeedsPress { command_id: string; name: string; }" in types
        assert "needs_press?: RemoteNeedsPress[]" in _flat("api.ts")

    def test_a_waiting_list_holds_the_dialog_open(self):
        create = " ".join(_method(_src("ir-promote-dialog.ts"), "_create").split())
        assert (
            "if (made.needs_press?.length) { this._minted = made; "
            "this._needsPress = made.needs_press; return; }"
        ) in create

    def test_the_list_shows_only_the_names(self):
        src = _src("ir-promote-dialog.ts")
        view = " ".join(_method(src, "_renderNeedsPress").split())
        assert '${t("promote.needs_press")}' in view
        assert "${names.map((n) => html`<li>${n.name}</li>`)}" in view

    def test_one_dialog_two_wrappers(self):
        # Since HA 2026.7 an <ha-dialog> swapped for another
        # mid-transition aborts and leaves the screen
        # (ir-save-new-dialog.ts), so both views live in one dialog.
        src = _src("ir-promote-dialog.ts")
        assert len(re.findall(r"<ha-dialog\s", src)) == 1
        render = " ".join(_method(src, "render").split())
        assert "<div ?hidden=${!!this._needsPress}>${this._renderForm()}</div>" in render
        assert "<div ?hidden=${!this._needsPress}>" in render
        assert "this._renderNeedsPress(this._needsPress)" in render
        assert "@closed=${this._onClosed}" in render

    def test_closing_the_list_announces_the_device(self):
        # The device exists once the list shows: Escape and the button
        # both announce it, so the Devices page clears the dialog and
        # the pin prompt still follows.
        src = _src("ir-promote-dialog.ts")
        closed = " ".join(_method(src, "_onClosed").split())
        assert "if (this._minted) this._finish(); else this._close();" in closed
        view = " ".join(_method(src, "_renderNeedsPress").split())
        assert "@click=${this._finish}" in view
        finish = " ".join(_method(src, "_finish").split())
        assert "this._minted = null; if (minted) this._announce(minted);" in finish
        # No step back to the form before the page removes the dialog.
        assert "this._needsPress =" not in finish

    def test_focus_moves_to_close_when_the_list_shows(self):
        updated = " ".join(_method(_src("ir-promote-dialog.ts"), "updated").split())
        assert 'if (changed.has("_needsPress") && this._needsPress) {' in updated
        assert '.querySelector<HTMLButtonElement>(".done-btn")?.focus();' in updated

    def test_a_second_enter_makes_no_second_device(self):
        create = " ".join(_method(_src("ir-promote-dialog.ts"), "_create").split())
        assert create.index("if (this._busy) return;") < create.index("this._busy = true;")

    def test_device_created_has_one_sender(self):
        src = _src("ir-promote-dialog.ts")
        assert src.count('"device-created"') == 1
        assert '"device-created"' in _method(src, "_announce")

    def test_with_nothing_waiting_it_closes_as_before(self):
        create = " ".join(_method(_src("ir-promote-dialog.ts"), "_create").split())
        assert "minted = made;" in create
        assert "this._announce(minted);" in create


class TestTheNoFrameRefusal:
    def test_the_code_has_a_sentence(self):
        from custom_components.hair.const import RF_NO_FRAME

        flat = _flat("rf-errors.ts")
        assert f'export const RF_NO_FRAME = "{RF_NO_FRAME}";' in flat
        assert '[RF_NO_FRAME]: "errors.rf_no_frame",' in flat

    def test_the_english_is_the_servers(self):
        from custom_components.hair.const import RF_NO_FRAME_MESSAGE

        assert _locale("en")["errors.rf_no_frame"] == RF_NO_FRAME_MESSAGE

    def test_both_strings_are_in_every_language(self):
        langs = sorted(p.stem for p in LOCALES.glob("*.json") if p.stem != "xx")
        assert len(langs) == 11
        en = _locale("en")
        for lang in langs:
            d = _locale(lang)
            for key in ("errors.rf_no_frame", "promote.needs_press"):
                assert d.get(key), (lang, key)
                # Not left as the English: every one is translated today.
                if lang != "en":
                    assert d[key] != en[key], (lang, key)
