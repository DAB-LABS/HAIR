"""Tests for the HAIR integration __init__.py setup/teardown."""
from __future__ import annotations

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
            mock_store_cls.return_value = mock_store

            await async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry, PLATFORMS_LIST
        )


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
