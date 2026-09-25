"""The Sniffer catalog reaches disk when Home Assistant stops.

WigFactory bench 2026-09-23: four sends made in the seconds before a
graceful restart never appeared in ``hair_unknown_signals``; the two
after it did. Every capture only calls ``schedule_save``, which arms a
``SIGNAL_SAVE_DEBOUNCE_S`` debounce under a ``SIGNAL_SAVE_MAX_DELAY_S``
ceiling, and nothing wrote a dirty store at shutdown, so the last
thirty seconds of a session died with the loop.

The unload half was never broken: ``async_unload_entry`` stops the
monitor, and ``SignalMonitor.async_stop`` ends in the store's own
``async_shutdown``, which has always flushed. What was missing is that
A GRACEFUL SHUTDOWN DOES NOT UNLOAD CONFIG ENTRIES, so on a restart
none of that runs. Hence the final-write listener.

These tests write to a real file rather than asserting that a save was
scheduled or that a mock was called: the bug was that nothing reached
disk, so nothing short of reading the file back proves it fixed.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import (
    DOMAIN,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hair.const import (
    SIGNAL_SAVE_DEBOUNCE_S,
    SIGNAL_SAVE_MAX_DELAY_S,
)
from custom_components.hair.models import UnknownDevice
from custom_components.hair.signal_store import SignalStore

FINAL_WRITE = "homeassistant_final_write"


# ---------------------------------------------------------------------------
# A store that really writes, and a bus that really fires
# ---------------------------------------------------------------------------


class _FileStore:
    """Stands in for HA's ``Store``, writing JSON to a real path.

    The suite's own stub keeps the payload in memory, which cannot tell
    "the catalog was saved" apart from "the catalog reached disk" -- and
    that distinction IS this bug.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.writes = 0

    async def async_save(self, data) -> None:
        self.writes += 1
        self.path.write_text(json.dumps(data), encoding="utf-8")

    async def async_load(self):
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def on_disk(self):
        """What a fresh process would read, or None if never written."""
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))


class _Bus:
    """The event bus as core drives it on shutdown: fire, then wait.

    ``fake_hass``'s bus is a disconnected MagicMock, so a test using it
    can only prove a listener was registered. Core fires FINAL_WRITE and
    then blocks on the pending tasks, so an async listener is awaited
    rather than raced -- ``async_fire`` here does the same.
    """

    def __init__(self) -> None:
        self.listeners: dict[str, list] = {}

    def async_listen(self, event_type, handler):
        self.listeners.setdefault(event_type, []).append(handler)

        def _unsub() -> None:
            handlers = self.listeners.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

        return _unsub

    def async_listen_once(self, event_type, handler):
        return self.async_listen(event_type, handler)

    async def async_fire(self, event_type, event=None):
        for handler in list(self.listeners.get(event_type, [])):
            result = handler(event or MagicMock())
            if asyncio.iscoroutine(result):
                await result


def _store_on(tmp_path: Path, hass) -> tuple[SignalStore, _FileStore]:
    """A real SignalStore writing to a real file."""
    store = SignalStore(hass)
    backing = _FileStore(tmp_path / "hair_unknown_signals.json")
    store._store = backing
    return store, backing


def _hass_with_timers():
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_later = MagicMock(return_value=MagicMock())
    hass.async_create_task = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    return hass


def _a_capture(store: SignalStore, device_id: str = "d1") -> None:
    """Put a row in memory and arm the debounce, as a capture does."""
    store._devices[device_id] = UnknownDevice(
        id=device_id, fingerprint=f"fp-{device_id}"
    )
    store._loaded = True
    store.schedule_save()


# ---------------------------------------------------------------------------
# The flush itself
# ---------------------------------------------------------------------------


class TestTheFlush:

    @pytest.mark.asyncio
    async def test_a_scheduled_capture_is_on_disk_after_a_flush(
        self, tmp_path,
    ):
        hass = _hass_with_timers()
        store, backing = _store_on(tmp_path, hass)
        _a_capture(store)

        # The debounce has not fired: this is the window the bench lost.
        assert backing.on_disk() is None

        assert await store.async_flush() is True

        payload = backing.on_disk()
        assert payload is not None
        assert [d["id"] for d in payload["devices"]] == ["d1"]

    @pytest.mark.asyncio
    async def test_a_clean_store_writes_nothing(self, tmp_path):
        hass = _hass_with_timers()
        store, backing = _store_on(tmp_path, hass)
        store._loaded = True

        assert await store.async_flush() is False
        assert backing.writes == 0
        assert backing.on_disk() is None

    @pytest.mark.asyncio
    async def test_a_flush_cancels_both_timers(self, tmp_path):
        hass = _hass_with_timers()
        debounce, ceiling = MagicMock(), MagicMock()
        hass.loop.call_later = MagicMock(side_effect=[debounce, ceiling])
        store, _backing = _store_on(tmp_path, hass)
        _a_capture(store)

        await store.async_flush()

        debounce.cancel.assert_called()
        ceiling.cancel.assert_called()
        assert store._debounce_handle is None
        assert store._ceiling_handle is None

    @pytest.mark.asyncio
    async def test_flushing_twice_writes_once(self, tmp_path):
        """Both shutdown paths can reach it; neither may assume it is
        the only one."""
        hass = _hass_with_timers()
        store, backing = _store_on(tmp_path, hass)
        _a_capture(store)

        assert await store.async_flush() is True
        assert await store.async_flush() is False
        assert backing.writes == 1

    @pytest.mark.asyncio
    async def test_shutdown_still_flushes_through_the_same_door(
        self, tmp_path,
    ):
        """``async_shutdown`` is now a name for ``async_flush``. It is
        what ``SignalMonitor.async_stop`` calls, so it has to keep
        working exactly as it did."""
        hass = _hass_with_timers()
        store, backing = _store_on(tmp_path, hass)
        _a_capture(store)

        await store.async_shutdown()

        assert backing.on_disk() is not None
        assert store._dirty is False


# ---------------------------------------------------------------------------
# The debounce and the ceiling are untouched
# ---------------------------------------------------------------------------


class TestNormalOperationIsUnchanged:

    def test_the_debounce_is_armed_at_its_own_delay(self, tmp_path):
        hass = _hass_with_timers()
        store, _backing = _store_on(tmp_path, hass)
        _a_capture(store)

        delays = [c.args[0] for c in hass.loop.call_later.call_args_list]
        assert delays[0] == SIGNAL_SAVE_DEBOUNCE_S

    def test_the_ceiling_is_armed_once_and_not_reset(self, tmp_path):
        """The reason HA's own ``Store.async_delay_save`` was not used:
        it is a pure debounce that resets on every call, and the capture
        path is exactly the busy environment this ceiling exists for."""
        hass = _hass_with_timers()
        store, _backing = _store_on(tmp_path, hass)
        _a_capture(store)
        first_ceiling = store._ceiling_handle

        for n in range(2, 6):
            _a_capture(store, f"d{n}")

        assert store._ceiling_handle is first_ceiling
        ceiling_delays = [
            c.args[0] for c in hass.loop.call_later.call_args_list
            if c.args[0] != SIGNAL_SAVE_DEBOUNCE_S
        ]
        assert ceiling_delays == [SIGNAL_SAVE_MAX_DELAY_S]

    def test_a_capture_past_the_ceiling_saves_at_once(self, tmp_path):
        hass = _hass_with_timers()
        store, _backing = _store_on(tmp_path, hass)
        _a_capture(store)
        store._first_dirty_time -= SIGNAL_SAVE_MAX_DELAY_S + 1

        hass.async_create_task.reset_mock()
        store.schedule_save()

        hass.async_create_task.assert_called_once()
        for coro in [c.args[0] for c in
                     hass.async_create_task.call_args_list]:
            coro.close()


# ---------------------------------------------------------------------------
# The owner's path: a restart, and an unload
# ---------------------------------------------------------------------------


def _wired_hass():
    """``_fake_hass`` from test_init, with a bus that really fires."""
    hass = MagicMock()
    hass.data = {}
    hass.config.components = set()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    hass.bus = _Bus()
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.loop = MagicMock()
    hass.loop.call_later = MagicMock(return_value=MagicMock())

    async def _exec_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = _exec_job
    return hass


def _wired_entry():
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.data = {}
    entry.options = {}
    entry.title = "HAIR"
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    # The real thing: hold the unsubs so a test can run them.
    entry.unloads = []
    entry.async_on_unload = MagicMock(side_effect=entry.unloads.append)
    return entry


async def _set_up(hass, entry, signal_store):
    with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
         patch("custom_components.hair.SignalStore",
               return_value=signal_store), \
         patch("custom_components.hair.async_register_websocket_commands"), \
         patch("custom_components.hair._async_register_panel",
               new_callable=AsyncMock):
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock()
        mock_store.backfill_catalog_trigger_origins.return_value = False
        mock_store_cls.return_value = mock_store
        assert await async_setup_entry(hass, entry) is True


class TestTheBenchPath:
    """A capture, then a graceful restart."""

    @pytest.mark.asyncio
    async def test_a_capture_is_on_disk_after_the_final_write_event(
        self, tmp_path,
    ):
        hass = _wired_hass()
        entry = _wired_entry()
        store, backing = _store_on(tmp_path, hass)
        store.async_load = AsyncMock()
        await _set_up(hass, entry, store)

        # Somebody presses a button. The debounce is armed and nothing
        # is on disk yet: this is the window the bench lost.
        _a_capture(store)
        assert backing.on_disk() is None

        await hass.bus.async_fire(FINAL_WRITE)

        payload = backing.on_disk()
        assert payload is not None
        assert [d["id"] for d in payload["devices"]] == ["d1"]

    @pytest.mark.asyncio
    async def test_a_quiet_restart_rewrites_nothing(self, tmp_path):
        hass = _wired_hass()
        entry = _wired_entry()
        store, backing = _store_on(tmp_path, hass)
        store.async_load = AsyncMock()
        await _set_up(hass, entry, store)

        await hass.bus.async_fire(FINAL_WRITE)

        assert backing.writes == 0
        assert backing.on_disk() is None

    @pytest.mark.asyncio
    async def test_the_listener_goes_away_with_the_entry(self, tmp_path):
        """A reload must not leave a listener holding the old store."""
        hass = _wired_hass()
        entry = _wired_entry()
        store, backing = _store_on(tmp_path, hass)
        store.async_load = AsyncMock()
        await _set_up(hass, entry, store)
        assert hass.bus.listeners.get(FINAL_WRITE)

        for unsub in entry.unloads:
            unsub()

        assert not hass.bus.listeners.get(FINAL_WRITE)

        _a_capture(store)
        await hass.bus.async_fire(FINAL_WRITE)
        assert backing.on_disk() is None


class TestUnload:

    @pytest.mark.asyncio
    async def test_unload_flushes_through_the_monitor(self, tmp_path):
        """The half that already worked, pinned so it keeps working."""
        hass = _wired_hass()
        entry = _wired_entry()
        store, backing = _store_on(tmp_path, hass)
        monitor = MagicMock()

        async def _stop() -> None:
            # What the real SignalMonitor.async_stop ends with.
            await store.async_shutdown()

        monitor.async_stop = AsyncMock(side_effect=_stop)
        hass.data[DOMAIN] = {entry.entry_id: {
            "signal_store": store,
            "signal_monitor": monitor,
            "orchestrator": MagicMock(is_capturing=False, active_session=None),
        }}
        _a_capture(store)

        assert await async_unload_entry(hass, entry) is True

        monitor.async_stop.assert_awaited_once()
        assert backing.on_disk() is not None
        assert backing.writes == 1

    @pytest.mark.asyncio
    async def test_unload_flushes_with_no_monitor_in_the_entry(
        self, tmp_path,
    ):
        """A setup that failed part way leaves no monitor to flush
        through, and the catalog still has to be written."""
        hass = _wired_hass()
        entry = _wired_entry()
        store, backing = _store_on(tmp_path, hass)
        hass.data[DOMAIN] = {entry.entry_id: {
            "signal_store": store,
            "orchestrator": MagicMock(is_capturing=False, active_session=None),
        }}
        _a_capture(store)

        assert await async_unload_entry(hass, entry) is True

        assert backing.on_disk() is not None
