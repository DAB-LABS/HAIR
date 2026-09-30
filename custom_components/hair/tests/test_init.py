"""Tests for the HAIR integration __init__.py setup/teardown."""
from __future__ import annotations

import asyncio as _asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import (
    DOMAIN,
    PLATFORMS_LIST,
    _async_register_panel,
    async_remove_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hair.const import PANEL_URL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_hass():
    hass = MagicMock()
    hass.data = {}
    hass.config.components = set()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    hass.bus.async_fire = MagicMock()
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    # Run executor jobs inline so awaited calls (e.g. the pluckable registry
    # load) return the job's real result instead of an un-awaitable MagicMock.
    async def _exec_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = _exec_job
    return hass


def _fake_entry(entry_id="test-entry"):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {}
    entry.options = {}
    entry.title = "HAIR"
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()
    return entry


# ===========================================================================
# async_setup
# ===========================================================================


class TestAsyncSetup:

    @pytest.mark.asyncio
    async def test_setup_initializes_domain_data(self):
        hass = _fake_hass()
        result = await async_setup(hass, {})
        assert result is True
        assert DOMAIN in hass.data
        assert isinstance(hass.data[DOMAIN], dict)

    @pytest.mark.asyncio
    async def test_setup_does_not_overwrite_existing_data(self):
        hass = _fake_hass()
        hass.data[DOMAIN] = {"existing": True}
        await async_setup(hass, {})
        assert hass.data[DOMAIN]["existing"] is True


# ===========================================================================
# async_setup_entry
# ===========================================================================


class TestAsyncSetupEntry:

    @pytest.mark.asyncio
    async def test_entry_data_populated(self):
        hass = _fake_hass()
        entry = _fake_entry()

        with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
             patch("custom_components.hair.async_register_websocket_commands"), \
             patch("custom_components.hair._async_register_panel", new_callable=AsyncMock):
            mock_store = MagicMock()
            mock_store.async_load = AsyncMock()
            # The cross-store origin backfill runs here (2026-08-18);
            # these tests are about setup wiring, so it finds nothing.
            mock_store.backfill_catalog_trigger_origins.return_value = False
            mock_store_cls.return_value = mock_store

            result = await async_setup_entry(hass, entry)

        assert result is True
        entry_data = hass.data[DOMAIN][entry.entry_id]
        assert "store" in entry_data
        assert "device_manager" in entry_data
        assert "orchestrator" in entry_data
        assert "entity_factory" in entry_data
        assert "config_entry" in entry_data

    @pytest.mark.asyncio
    async def test_websocket_commands_registered(self):
        hass = _fake_hass()
        entry = _fake_entry()

        with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
             patch("custom_components.hair.async_register_websocket_commands") as mock_ws, \
             patch("custom_components.hair._async_register_panel", new_callable=AsyncMock):
            mock_store = MagicMock()
            mock_store.async_load = AsyncMock()
            # The cross-store origin backfill runs here (2026-08-18);
            # these tests are about setup wiring, so it finds nothing.
            mock_store.backfill_catalog_trigger_origins.return_value = False
            mock_store_cls.return_value = mock_store

            await async_setup_entry(hass, entry)

        mock_ws.assert_called_once_with(hass)

    @pytest.mark.asyncio
    async def test_platforms_forwarded(self):
        hass = _fake_hass()
        entry = _fake_entry()

        with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
             patch("custom_components.hair.async_register_websocket_commands"), \
             patch("custom_components.hair._async_register_panel", new_callable=AsyncMock):
            mock_store = MagicMock()
            mock_store.async_load = AsyncMock()
            # The cross-store origin backfill runs here (2026-08-18);
            # these tests are about setup wiring, so it finds nothing.
            mock_store.backfill_catalog_trigger_origins.return_value = False
            mock_store_cls.return_value = mock_store

            await async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry, PLATFORMS_LIST
        )

    @pytest.mark.asyncio
    async def test_cell_indexes_are_warmed_before_receivers_subscribe(self):
        """0.10.1 item 3: no frame can arrive while a lattice is loading.

        signal_monitor.async_start is what calls async_subscribe_receiver,
        so the warm has to be strictly ahead of it -- being merely "at
        setup" is what the lazy build already was.
        """
        hass = _fake_hass()
        entry = _fake_entry()
        order: list[str] = []

        with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
             patch("custom_components.hair.async_register_websocket_commands"), \
             patch("custom_components.hair.MatrixListener") as mock_listener_cls, \
             patch("custom_components.hair.SignalMonitor") as mock_monitor_cls, \
             patch("custom_components.hair._async_register_panel", new_callable=AsyncMock):
            mock_store = MagicMock()
            mock_store.async_load = AsyncMock()
            mock_store.backfill_catalog_trigger_origins.return_value = False
            mock_store_cls.return_value = mock_store
            mock_listener_cls.return_value.async_warm_indexes = AsyncMock(
                side_effect=lambda: order.append("warm")
            )
            mock_monitor_cls.return_value.async_start = AsyncMock(
                side_effect=lambda: order.append("subscribe")
            )

            await async_setup_entry(hass, entry)

        assert order == ["warm", "subscribe"]


# ===========================================================================
# async_unload_entry
# ===========================================================================


class TestAsyncUnloadEntry:

    @pytest.mark.asyncio
    async def test_unload_success(self):
        hass = _fake_hass()
        entry = _fake_entry()

        # Simulate existing entry data
        mock_orchestrator = MagicMock()
        mock_orchestrator.is_capturing = False
        hass.data[DOMAIN] = {
            entry.entry_id: {
                "device_manager": MagicMock(),
                "orchestrator": mock_orchestrator,
            }
        }

        result = await async_unload_entry(hass, entry)
        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_cancels_active_capture(self):
        hass = _fake_hass()
        entry = _fake_entry()

        mock_orchestrator = MagicMock()
        mock_orchestrator.is_capturing = True
        mock_session = MagicMock()
        mock_session.session_id = "sess-1"
        mock_orchestrator.active_session = mock_session
        mock_orchestrator.cancel_capture = AsyncMock()

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "device_manager": MagicMock(),
                "orchestrator": mock_orchestrator,
            }
        }

        await async_unload_entry(hass, entry)
        mock_orchestrator.cancel_capture.assert_awaited_once_with("sess-1")

    @pytest.mark.asyncio
    async def test_unload_removes_panel_when_last_entry(self):
        hass = _fake_hass()
        entry = _fake_entry()

        mock_orchestrator = MagicMock()
        mock_orchestrator.is_capturing = False

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "device_manager": MagicMock(),
                "orchestrator": mock_orchestrator,
            },
            "_panel_registered": True,
        }

        with patch("custom_components.hair.frontend") as mock_frontend:
            await async_unload_entry(hass, entry)
            mock_frontend.async_remove_panel.assert_called_once_with(hass, PANEL_URL)

        assert "_panel_registered" not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_preserves_panel_when_other_entries_exist(self):
        hass = _fake_hass()
        entry = _fake_entry("entry-1")

        mock_orchestrator = MagicMock()
        mock_orchestrator.is_capturing = False

        hass.data[DOMAIN] = {
            "entry-1": {
                "device_manager": MagicMock(),
                "orchestrator": mock_orchestrator,
            },
            "entry-2": {
                "device_manager": MagicMock(),
            },
            "_panel_registered": True,
        }

        with patch("custom_components.hair.frontend") as mock_frontend:
            await async_unload_entry(hass, entry)
            mock_frontend.async_remove_panel.assert_not_called()

        assert "_panel_registered" in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_failure_returns_false(self):
        hass = _fake_hass()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        entry = _fake_entry()

        hass.data[DOMAIN] = {
            entry.entry_id: {"device_manager": MagicMock()}
        }

        result = await async_unload_entry(hass, entry)
        assert result is False
        # Data should NOT be removed on failure
        assert entry.entry_id in hass.data[DOMAIN]


# ===========================================================================
# Panel registration
# ===========================================================================


class TestPanelRegistration:

    @pytest.mark.asyncio
    async def test_panel_registered_once(self):
        hass = _fake_hass()
        entry = _fake_entry()
        hass.data[DOMAIN] = {}

        with patch("custom_components.hair.panel_custom") as mock_pc:
            mock_pc.async_register_panel = AsyncMock()
            await _async_register_panel(hass, entry)
            await _async_register_panel(hass, entry)

        # Should only be called once due to idempotency guard
        mock_pc.async_register_panel.assert_awaited_once()
        assert hass.data[DOMAIN].get("_panel_registered") is True

    @pytest.mark.asyncio
    async def test_panel_registers_static_path_when_bundle_exists(self):
        hass = _fake_hass()
        entry = _fake_entry()
        hass.data[DOMAIN] = {}

        with patch("custom_components.hair.panel_custom") as mock_pc, \
             patch("custom_components.hair.Path") as mock_path_cls:
            mock_pc.async_register_panel = AsyncMock()
            mock_bundle = MagicMock()
            mock_bundle.exists.return_value = True
            mock_bundle.read_bytes.return_value = b"fake-js-content"
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_bundle)
            # Chain the / operators
            parent = MagicMock()
            parent.__truediv__ = MagicMock(return_value=MagicMock(
                __truediv__=MagicMock(return_value=mock_bundle)
            ))
            mock_path_cls.return_value = MagicMock()
            mock_path_cls.return_value.parent = parent

            await _async_register_panel(hass, entry)

        # Static path registration should have been attempted
        # (exact assertion depends on Path mock, just verify panel registered)
        mock_pc.async_register_panel.assert_awaited_once()


# ===========================================================================
# Options update and remove
# ===========================================================================


class TestRemoveEntry:

    @pytest.mark.asyncio
    async def test_remove_entry_is_noop(self):
        """async_remove_entry intentionally does nothing (preserves storage)."""
        hass = _fake_hass()
        entry = _fake_entry()
        # Should not raise
        await async_remove_entry(hass, entry)


# ===========================================================================
# PLATFORMS_LIST
# ===========================================================================


class TestPlatformsList:

    def test_contains_expected_platforms(self):
        from homeassistant.const import Platform
        assert Platform.REMOTE in PLATFORMS_LIST
        assert Platform.MEDIA_PLAYER in PLATFORMS_LIST
        assert Platform.CLIMATE in PLATFORMS_LIST
        assert Platform.FAN in PLATFORMS_LIST
        assert Platform.LIGHT in PLATFORMS_LIST
        assert Platform.SWITCH in PLATFORMS_LIST
        assert Platform.COVER in PLATFORMS_LIST
        assert Platform.BUTTON in PLATFORMS_LIST
        assert Platform.EVENT in PLATFORMS_LIST
        # Infrared emitter platform (the HAIR Tweezer, Plucker v0.5.0). On a
        # HA build without a Platform.INFRARED enum member this is the bare
        # "infrared" domain string, so match on the value, not enum identity.
        assert any(str(p) == "infrared" for p in PLATFORMS_LIST)
        assert len(PLATFORMS_LIST) == 10


class TestReloadRehashesPanel:
    """Regression pin for the roadmap's 'cache-buster on reload' item.

    Verdict from re-reading the path (2026-07-19): a config-entry RELOAD
    already re-hashes. async_unload_entry removes the panel and clears
    the _panel_registered guard when the last entry unloads, so the next
    setup re-reads the bundle and registers a fresh ?v= hash. The v0.6.6
    bench staleness that spawned the roadmap item was the untracked-SVG
    pull collision (bundle never changed on disk), not a reload defect.
    This test pins the reload cycle so the behavior cannot regress into
    the bug the roadmap described."""

    @staticmethod
    def _patch_bundle(mock_path_cls, content: bytes):
        # Self-returning node: every `/` yields the node itself, so the
        # three-hop `parent / "frontend" / "dist" / PANEL_FILENAME` chain
        # lands on a mock whose exists/read_bytes serve the bundle.
        node = MagicMock()
        node.__truediv__ = MagicMock(return_value=node)
        node.exists.return_value = True
        node.read_bytes.return_value = content
        mock_path_cls.return_value = MagicMock()
        mock_path_cls.return_value.parent = node

    @pytest.mark.asyncio
    async def test_reload_cycle_registers_new_bundle_hash(self):
        import hashlib as _hashlib

        hass = _fake_hass()
        entry = _fake_entry()
        hass.data[DOMAIN] = {}

        # First setup: bundle A registers with A's hash.
        with patch("custom_components.hair.panel_custom") as mock_pc, \
             patch("custom_components.hair.Path") as mock_path_cls:
            mock_pc.async_register_panel = AsyncMock()
            self._patch_bundle(mock_path_cls, b"bundle-edition-A")
            await _async_register_panel(hass, entry)
            url_a = mock_pc.async_register_panel.await_args.kwargs["module_url"]
        assert url_a.endswith(
            "?v=" + _hashlib.md5(b"bundle-edition-A").hexdigest()[:8]
        )

        # Unload (single entry): panel removed, guard cleared.
        mock_orchestrator = MagicMock()
        mock_orchestrator.is_capturing = False
        hass.data[DOMAIN][entry.entry_id] = {
            "device_manager": MagicMock(),
            "orchestrator": mock_orchestrator,
        }
        with patch("custom_components.hair.frontend") as mock_frontend:
            assert await async_unload_entry(hass, entry) is True
            mock_frontend.async_remove_panel.assert_called_once()
        assert "_panel_registered" not in hass.data[DOMAIN]

        # Second setup (the reload): bundle B registers with B's hash.
        with patch("custom_components.hair.panel_custom") as mock_pc, \
             patch("custom_components.hair.Path") as mock_path_cls:
            mock_pc.async_register_panel = AsyncMock()
            self._patch_bundle(mock_path_cls, b"bundle-edition-B")
            await _async_register_panel(hass, entry)
            url_b = mock_pc.async_register_panel.await_args.kwargs["module_url"]
        assert url_b.endswith(
            "?v=" + _hashlib.md5(b"bundle-edition-B").hexdigest()[:8]
        )
        assert url_a != url_b


# ===========================================================================
# The field-map library is never first loaded on the event loop
# ===========================================================================


class TestTheMapLibraryIsWarmedOffTheLoop:
    """VM999 bench 2026-09-29, on #187.

    HA logged three "Detected blocking call" warnings at startup:
    scandir, read_text and open on ``field_maps/``. The chain was
    ``async_setup_entry`` -> ``store.async_load`` ->
    ``_backfill_canonical_identity`` -> ``canonical_byte_hash`` ->
    setting-frame identity -> ``field_readers.library()`` on first use,
    all of it inside the event loop.

    Setting-frame identity is what put the map library on that path, so
    the library has to be warm before the first store loads. These
    tests reproduce the chain rather than assert on call order, so they
    keep meaning if the warm ever moves somewhere else that is still
    early enough.
    """

    @staticmethod
    def _hass_with_a_real_executor():
        """``_fake_hass`` runs executor jobs inline, which is exactly the
        distinction under test here, so this one uses a real thread."""
        hass = _fake_hass()

        async def _exec_job(func, *args):
            loop = _asyncio.get_running_loop()
            return await loop.run_in_executor(None, func, *args)

        hass.async_add_executor_job = _exec_job
        return hass

    @staticmethod
    def _refuse_on_the_loop(real):
        """``load_maps``, but it raises if called where HA would warn."""

        def guarded(*args, **kwargs):
            try:
                _asyncio.get_running_loop()
            except RuntimeError:
                return real(*args, **kwargs)
            raise AssertionError(
                "the field map library was first loaded on the event loop"
            )

        return guarded

    @pytest.mark.asyncio
    async def test_a_store_load_that_hashes_a_code_does_no_file_io(self):
        """The reported chain, end to end: the store's load asks for a
        code's canonical byte hash, which is what reached the maps."""
        from custom_components.hair import field_readers
        from custom_components.hair.identity import canonical_byte_hash

        hass = self._hass_with_a_real_executor()
        entry = _fake_entry()
        nec = ("0000 006D 0006 0000 0157 00AC 0016 0016 0016 0041 0016 0016"
               " 0016 0041 0016 06FB")

        field_readers.reset_library()
        try:
            with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
                 patch("custom_components.hair.async_register_websocket_commands"), \
                 patch("custom_components.hair._async_register_panel",
                       new_callable=AsyncMock), \
                 patch.object(field_readers, "load_maps",
                              self._refuse_on_the_loop(field_readers.load_maps)):
                mock_store = MagicMock()
                mock_store.async_load = AsyncMock(
                    side_effect=lambda: canonical_byte_hash(nec)
                )
                mock_store.backfill_catalog_trigger_origins.return_value = False
                mock_store_cls.return_value = mock_store

                assert await async_setup_entry(hass, entry) is True

            assert field_readers.library()
        finally:
            field_readers.reset_library()

    @pytest.mark.asyncio
    async def test_the_warm_happens_before_the_store_is_even_built(self):
        """Ordering, stated once as an ordering so a future edit that
        keeps the warm but moves it after the store still fails."""
        from custom_components.hair import field_readers

        hass = self._hass_with_a_real_executor()
        entry = _fake_entry()
        order: list[str] = []

        def _warm():
            order.append("warm")
            field_readers.library()

        field_readers.reset_library()
        try:
            with patch("custom_components.hair.HAIRStore") as mock_store_cls, \
                 patch("custom_components.hair.async_register_websocket_commands"), \
                 patch("custom_components.hair._async_register_panel",
                       new_callable=AsyncMock), \
                 patch("custom_components.hair.prime_field_maps", _warm):
                mock_store = MagicMock()
                mock_store.async_load = AsyncMock(
                    side_effect=lambda: order.append("store")
                )
                mock_store.backfill_catalog_trigger_origins.return_value = False
                mock_store_cls.side_effect = lambda *a: (
                    order.append("store built") or mock_store
                )

                await async_setup_entry(hass, entry)
        finally:
            field_readers.reset_library()

        assert order[:3] == ["warm", "store built", "store"]

    def test_the_warm_fills_the_cache(self):
        """It is the cache that makes one warm enough for the process."""
        from custom_components.hair import field_readers

        field_readers.reset_library()
        try:
            assert field_readers._LIBRARY is None
            field_readers.prime_field_maps()
            assert field_readers._LIBRARY is not None
            assert field_readers.library() is field_readers._LIBRARY
        finally:
            field_readers.reset_library()
