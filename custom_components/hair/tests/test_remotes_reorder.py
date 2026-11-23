"""The Remotes section of the Devices tab: drag a Remote card to reorder.

The order is the store's own: named Remotes are kept in insertion order,
written that way and read back that way, as the device list is. A
reorder rebuilds that order from a complete id list, through the
``hair/trigger-remotes/reorder`` door, so every list of Remotes in the
panel follows it. A new Remote is still added at the end, beside the
"+" tile.

The panel side is the device grid's drag, on the Remotes grid: only
Remote cards drag, the HAIR Triggers drawer stays first, dragging waits
while the IR/RF glyphs filter the section, and the save is debounced and
followed by a refresh of the list. The panel is a Lit element with no
node driver, so its wiring is checked by reading the source.
"""
from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import websocket_api
from custom_components.hair.models import TriggerRemote
from custom_components.hair.storage import HAIRStore
from custom_components.hair.tests.test_storage import _FakeStore
from custom_components.hair.tests.test_websocket_api import (
    _make_connection,
    _wire_triggers,
)
from custom_components.hair.websocket_api import ws_reorder_trigger_remotes

SRC = Path(__file__).parent.parent / "frontend" / "src"


def _remote(name: str) -> TriggerRemote:
    return TriggerRemote(name=name)


async def _store_with(fake_hass, *names):
    store = HAIRStore(fake_hass)
    await store.async_load()
    remotes = [_remote(n) for n in names]
    for remote in remotes:
        store.add_trigger_remote(remote)
    return store, remotes


def _ids(store):
    return [r.id for r in store.get_all_trigger_remotes()]


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------


class TestTheStore:
    @pytest.mark.asyncio
    async def test_a_new_remote_goes_at_the_end(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store, (a, b) = await _store_with(fake_hass, "A", "B")
            c = _remote("C")
            store.add_trigger_remote(c)
            assert _ids(store) == [a.id, b.id, c.id]

    @pytest.mark.asyncio
    async def test_a_reorder_takes_the_given_order(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store, (a, b, c) = await _store_with(fake_hass, "A", "B", "C")
            store.reorder_trigger_remotes([c.id, a.id, b.id])
            assert _ids(store) == [c.id, a.id, b.id]

    @pytest.mark.asyncio
    async def test_the_order_survives_a_save_and_a_reload(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store, (a, b, c) = await _store_with(fake_hass, "A", "B", "C")
            store.reorder_trigger_remotes([b.id, c.id, a.id])
            await store.async_save()

            again = HAIRStore(fake_hass)
            again._store = store._store  # type: ignore[attr-defined]
            await again.async_load()
            assert _ids(again) == [b.id, c.id, a.id]

    @pytest.mark.asyncio
    async def test_a_reorder_keeps_every_remote_whole(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store, (a, b) = await _store_with(fake_hass, "A", "B")
            store.reorder_trigger_remotes([b.id, a.id])
            assert store.get_trigger_remote(a.id) is a
            assert store.get_trigger_remote(b.id) is b

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("make", "message"),
        [
            (lambda a, b: [a, a, b], "Duplicate"),
            (lambda a, b: [a, b, "ghost"], "unknown"),
            (lambda a, b: [a], "missing"),
        ],
        ids=["duplicate", "unknown", "missing"],
    )
    async def test_a_stale_list_is_refused_and_changes_nothing(
        self, fake_hass, make, message
    ):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store, (a, b) = await _store_with(fake_hass, "A", "B")
            before = _ids(store)
            with pytest.raises(ValueError, match=message):
                store.reorder_trigger_remotes(make(a.id, b.id))
            assert _ids(store) == before

    @pytest.mark.asyncio
    async def test_no_remotes_and_an_empty_list(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store, _ = await _store_with(fake_hass)
            store.reorder_trigger_remotes([])
            assert _ids(store) == []


# ---------------------------------------------------------------------------
# The door
# ---------------------------------------------------------------------------


class TestTheDoor:
    @pytest.mark.asyncio
    async def test_it_reorders_and_saves(self, fake_hass):
        store = _wire_triggers(fake_hass)
        store.reorder_trigger_remotes = MagicMock()
        conn = _make_connection()
        await ws_reorder_trigger_remotes(
            fake_hass, conn,
            {"id": 1, "type": "hair/trigger-remotes/reorder", "remote_ids": ["b", "a"]},
        )
        store.reorder_trigger_remotes.assert_called_once_with(["b", "a"])
        store.async_save.assert_awaited_once()
        conn.send_result.assert_called_once_with(1, {"reordered": True})

    @pytest.mark.asyncio
    async def test_a_stale_list_is_refused_unsaved(self, fake_hass):
        store = _wire_triggers(fake_hass)
        store.reorder_trigger_remotes = MagicMock(
            side_effect=ValueError("Reorder list does not match current remotes")
        )
        conn = _make_connection()
        await ws_reorder_trigger_remotes(
            fake_hass, conn,
            {"id": 2, "type": "hair/trigger-remotes/reorder", "remote_ids": ["ghost"]},
        )
        assert conn.send_error.call_args[0][1] == "invalid_format"
        store.async_save.assert_not_awaited()
        conn.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_configured(self, fake_hass):
        conn = _make_connection()
        await ws_reorder_trigger_remotes(
            fake_hass, conn,
            {"id": 3, "type": "hair/trigger-remotes/reorder", "remote_ids": []},
        )
        assert conn.send_error.call_args[0][1] == "not_configured"

    def test_it_is_registered_for_admins(self):
        source = inspect.getsource(websocket_api)
        assert "async_register_command(hass, ws_reorder_trigger_remotes)" in source
        head = source[: source.index("async def ws_reorder_trigger_remotes(")]
        head = head[head.rindex("@websocket_api.require_admin"):]
        assert 'f"{WS_PREFIX}/trigger-remotes/reorder"' in head
        assert 'vol.Required("remote_ids"): [str]' in head


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _method(text: str, name: str) -> str:
    body = text[text.index(name):]
    return body[: body.index("\n    }\n")]


class TestThePanel:
    def test_the_api_call(self):
        call = _method(_read("api.ts"), "reorderTriggerRemotes(")
        assert '"hair/trigger-remotes/reorder"' in call
        assert "remote_ids: remoteIds" in call

    def test_only_remote_cards_drag_and_the_drawer_stays_first(self):
        attach = _method(_read("ir-device-list.ts"), "private _attachRemotesSortable")
        assert 'draggable: ".trigger-remote-card"' in attach
        assert 'filter: ".card-action"' in attach
        assert 'classList.contains("trigger-remote-card")' in attach
        assert 'ghostClass: "sortable-ghost"' in attach

    def test_the_grid_and_the_cards(self):
        text = _read("ir-device-list.ts")
        grid = text[text.index('<div class="grid remote-grid">'):]
        drawer = grid.index("trigger-drawer-card")
        cards = grid.index("trigger-remote-card")
        assert drawer < cards
        assert "keyed(\n                    this._remotesVersion," in grid
        assert "(this._localRemotes ?? this.triggerRemotes).filter" in grid
        card = grid[cards: grid.index("tabindex", cards)]
        assert "data-id=${remote.id}" in card

    def test_dragging_waits_while_the_glyphs_filter(self):
        text = _read("ir-device-list.ts")
        assert "disabled: !mediaShowsEverything(this._mediaShow.remotes)," in _method(
            text, "private _attachRemotesSortable"
        )
        assert (
            'this._remotesSortable?.option("disabled", '
            "!mediaShowsEverything(this._mediaShow.remotes));"
        ) in text

    def test_the_drop_reads_the_cards_and_saves_later(self):
        text = _read("ir-device-list.ts")
        attach = _method(text, "private _attachRemotesSortable")
        assert 'grid.querySelectorAll(".trigger-remote-card")' in attach
        assert "if (reordered.length !== base.length) return;" in attach
        assert "this._remotesVersion++;" in attach
        save = _method(text, "private _scheduleRemotesSave")
        assert "REORDER_DEBOUNCE_MS" in save
        assert "this.api.reorderTriggerRemotes(remoteIds)" in save
        assert 'new CustomEvent("remotes-reordered"' in save

    def test_a_fresh_list_drops_the_local_order(self):
        text = _read("ir-device-list.ts")
        will = _method(text, "protected willUpdate(")
        assert (
            'if (changed.has("triggerRemotes")) {\n'
            "            this._localRemotes = null;"
        ) in will
        assert "this._syncRemotesSortable();" in _method(text, "updated(changed")

    def test_the_panel_refreshes_after_a_reorder(self):
        assert "@remotes-reordered=${this._onRemoteChanged}" in _read(
            "ha-panel-ir-devices.ts"
        )

    def test_it_is_let_go_of(self):
        text = _read("ir-device-list.ts")
        gone = text.index(
            "this._remotesSortable?.destroy();\n"
            "        this._remotesSortable = null;\n"
            "        if (this._pendingRemotesSave"
        )
        assert "clearTimeout(this._pendingRemotesSave)" in text[gone: gone + 300]
