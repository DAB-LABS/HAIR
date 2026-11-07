"""RF hear fix round 1 (owner's desktop bench, 2026-11-06): the backend
pieces behind the Sniffer's receiver row.

Item 6: every receiver gets a pill, so ``hair/receivers/capture`` takes
``include_always_on`` and adds a status row per always-on infrared
receiver (HAIR's own observer left out); pills bloom only when HAIR
takes a code from their receiver, which ``_note_heard`` now tells the
panel (``hair_receiver_heard``), at most once per receiver per 0.3 s.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import receiver_window as rw
from custom_components.hair.const import EVENT_RECEIVER_HEARD, TWEEZER_OBSERVER_ATTR
from custom_components.hair.tests.test_receiver_window import (  # noqa: F401
    ATHOM_RX,
    OFFICE_RX,
    RX,
    _entries,
    _fresh,
    _Hass,
    _infrared,
    _loaded_store,
    _Registry,
    _registry,
    _state,
    v020,
)

OBSERVER = "infrared.hair_tweezer"


def _hass():
    return _Hass({
        RX: v020(),
        ATHOM_RX: _state(),  # always on: no capture attributes at all
        OFFICE_RX: _state("unavailable"),
        OBSERVER: _state(**{TWEEZER_OBSERVER_ATTR: True}),
    })


class TestEveryReceiverOnTheRow:
    @pytest.mark.asyncio
    async def test_always_on_infrared_rows_only_when_asked(self):
        hass = _hass()
        store = await _loaded_store(hass)
        receivers = (RX, OFFICE_RX, ATHOM_RX, OBSERVER)
        with _registry(_Registry(_entries())), _infrared(hass, receivers):
            plain = rw.capture_receivers(hass, store)
            every = rw.capture_receivers(hass, store, include_always_on=True)
        assert [r["receiver_entity_id"] for r in plain] == [RX]
        ids = [r["receiver_entity_id"] for r in every]
        assert RX in ids and ATHOM_RX in ids and OFFICE_RX in ids
        assert OBSERVER not in ids

    @pytest.mark.asyncio
    async def test_a_status_row_has_nothing_to_open_or_set(self):
        hass = _hass()
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())), _infrared(hass):
            rows = rw.capture_receivers(hass, store, include_always_on=True)
        athom = next(r for r in rows if r["receiver_entity_id"] == ATHOM_RX)
        assert athom["always_on"] is True
        assert (athom["medium"], athom["capture_device"], athom["software_window"]) == (
            "ir", False, False,
        )
        assert athom["switch_entity_id"] is None and athom["device_switches"] == []
        assert athom["frequency_select"] is None and athom["window_length"] is None
        assert athom["capturing"] is False and athom["available"] is True
        office = next(r for r in rows if r["receiver_entity_id"] == OFFICE_RX)
        assert office["available"] is False
        capture = next(r for r in rows if r["receiver_entity_id"] == RX)
        assert "always_on" not in capture

    @pytest.mark.asyncio
    async def test_rows_are_ordered_by_device_name(self):
        hass = _hass()
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())), _infrared(hass):
            rows = rw.capture_receivers(hass, store, include_always_on=True)
        names = [r["name"].casefold() for r in rows]
        assert names == sorted(names)

    def test_the_door_passes_the_flag(self):
        from custom_components.hair.websocket_api import ws_capture_receivers

        conn = MagicMock()
        with patch(
            "custom_components.hair.websocket_api.capture_receivers", return_value=[]
        ) as rows:
            ws_capture_receivers(MagicMock(), conn, {"id": 1, "include_always_on": True})
            ws_capture_receivers(MagicMock(), conn, {"id": 2})
        assert rows.call_args_list[0].kwargs == {"include_always_on": True}
        assert rows.call_args_list[1].kwargs == {"include_always_on": False}


class TestTheHeardEvent:
    def _monitor(self):
        from custom_components.hair.signal_monitor import SignalMonitor

        monitor = SignalMonitor.__new__(SignalMonitor)
        monitor._last_heard_at = {}
        monitor._hass = MagicMock()
        return monitor

    def test_heard_tells_the_panel_once_per_burst_per_receiver(self):
        monitor = self._monitor()
        clock = [0.0, 0.1, 0.2, 0.5]
        with patch("custom_components.hair.signal_monitor.monotonic", side_effect=clock):
            monitor._note_heard("infrared.a")
            monitor._note_heard("infrared.a")  # same press: no second bloom
            monitor._note_heard("radio_frequency.b")
            monitor._note_heard("infrared.a")  # a later press
        fired = monitor._hass.bus.async_fire.call_args_list
        assert [(c.args[0], c.args[1]["receiver_entity_id"]) for c in fired] == [
            (EVENT_RECEIVER_HEARD, "infrared.a"),
            (EVENT_RECEIVER_HEARD, "radio_frequency.b"),
            (EVENT_RECEIVER_HEARD, "infrared.a"),
        ]

    def test_nothing_for_no_receiver(self):
        monitor = self._monitor()
        monitor._note_heard(None)
        monitor._hass.bus.async_fire.assert_not_called()

    def test_the_event_name(self):
        assert EVENT_RECEIVER_HEARD == "hair_receiver_heard"


class TestThePickerMenu:
    """Owner bench, 19:27: the pickers' menus painted under the pills and
    rows after them (each pill is its own stacking context). The menu is
    a manual popover, in the browser's top layer."""

    def test_the_menu_is_a_popover_shown_on_render(self):
        from pathlib import Path

        src = (
            Path(__file__).parent.parent / "frontend" / "src" / "ir-pill-picker.ts"
        ).read_text(encoding="utf-8")
        flat = " ".join(src.split())
        assert 'class="menu" role="menu" popover="manual"' in flat
        assert 'typeof menu.showPopover === "function" && !menu.matches(":popover-open")' in flat
        menu = flat.split(".menu {", 1)[1].split("}", 1)[0]
        assert "inset: auto;" in menu and "margin: 0;" in menu


class TestTheHiddenGlyph:
    """Owner bench, 19:35: the hidden glyph glowed once and never again,
    and its dot sat off in the button's corner."""

    def _flat(self):
        from pathlib import Path

        src = (
            Path(__file__).parent.parent / "frontend" / "src" / "ir-signal-monitor.ts"
        ).read_text(encoding="utf-8")
        return " ".join(src.split())

    def test_every_press_restarts_the_glow(self):
        body = self._flat().split("private _onHiddenActivity(): void {", 1)[1]
        body = body.split("// --- Inline rename ---", 1)[0]
        assert body.index("this._hiddenGlow = false;") < body.index("requestAnimationFrame(")
        assert body.count("requestAnimationFrame(") == 2
        assert "this._hiddenGlow = true;" in body

    def test_the_eye_itself_glows_and_the_dot_sits_on_it(self):
        flat = self._flat()
        assert (
            ".show-glyph.hidden-glow ha-svg-icon { animation: hidden-eye 3.8s ease-out; }"
        ) in flat
        assert "@keyframes hidden-eye" in flat and "drop-shadow(0 0 6px" in flat
        dot = flat.split(".hidden-dot {", 1)[1].split("}", 1)[0]
        assert "top: 2px;" in dot and "right: 4px;" in dot
        glyph = flat.split(".show-glyph {", 1)[1].split("}", 1)[0]
        assert "opacity:" not in glyph


class TestGrabOnlyOnTheGlyph:
    """Item 9 (owner, 20:13 PT): the grip and the grab cursor only while
    the pointer is over the glyph in the handle slot, never the row."""

    def _css(self):
        from pathlib import Path

        src = (
            Path(__file__).parent.parent / "frontend" / "src" / "ir-signal-monitor.ts"
        ).read_text(encoding="utf-8")
        return " ".join(src.split())

    def test_the_swap_follows_the_handle_not_the_row(self):
        css = self._css()
        assert ".device-row:hover .remote-handle" not in css
        assert ".remote-handle:hover .handle-glyph," in css
        assert ".remote-handle:hover .remote-grip," in css

    def test_only_the_handle_grabs_and_drags(self):
        css = self._css()
        assert 'handle: ".remote-handle",' in css
        row = css.split(".device-row {", 1)[1].split("}", 1)[0]
        assert "cursor: grab" not in row


class TestTheFilterGlyphs:
    """Owner, 20:46 and 20:54 PT: the glyphs sit just above the remotes,
    lit in the remote cards' stroke blue."""

    def test_bottom_and_stroke_blue(self):
        from pathlib import Path

        src = (
            Path(__file__).parent.parent / "frontend" / "src" / "ir-signal-monitor.ts"
        ).read_text(encoding="utf-8")
        flat = " ".join(src.split())
        glyphs = flat.split(".show-glyphs {", 1)[1].split("}", 1)[0]
        assert "margin-bottom: -9px;" in glyphs
        lit = flat.split(".show-glyph.on {", 1)[1].split("}", 1)[0]
        stroke = "color-mix(in srgb, var(--primary-color) 30%, transparent);"
        assert stroke in lit
        assert f"border-color: {stroke}" in flat
