"""Tests for the HAIR WebSocket API handlers."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    DOMAIN,
    CaptureProviderType,
    CaptureState,
    CommandCategory,
    DeviceType,
)
from custom_components.hair.models import (
    CaptureResult,
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    async_register_websocket_commands,
    ws_assign_signal,
    ws_cancel_capture,
    ws_clear_unknowns,
    ws_create_device,
    ws_delete_command,
    ws_delete_device,
    ws_dismiss_unknown,
    ws_get_capture_providers,
    ws_get_command_templates,
    ws_get_device,
    ws_get_devices,
    ws_get_unknown_device,
    ws_get_unknown_devices,
    ws_save_captured_command,
    ws_send_command,
    ws_start_capture,
    ws_test_signal,
    ws_undismiss_unknown,
    ws_update_device,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connection():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.send_event = MagicMock()
    conn.subscriptions = {}
    return conn


def _wire_hass(hass, manager=None, orchestrator=None, signal_monitor=None):
    """Set up hass.data[DOMAIN] with a fake entry data dict."""
    entry_data = {
        "device_manager": manager or MagicMock(),
        "orchestrator": orchestrator or MagicMock(),
        "signal_monitor": signal_monitor or MagicMock(),
    }
    hass.data[DOMAIN] = {"entry-1": entry_data}


def _make_signal_monitor(hass):
    """Create a real SignalMonitor with in-memory stores for testing."""
    signal_store = SignalStore(hass)
    signal_store._loaded = True
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    return SignalMonitor(hass, signal_store, hair_store)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


def test_ws_commands_registered_once(fake_hass):
    """Idempotent guard: WS commands registered only once."""
    async_register_websocket_commands(fake_hass)
    async_register_websocket_commands(fake_hass)
    assert fake_hass.data[f"{DOMAIN}_ws_registered"] is True


# ---------------------------------------------------------------------------
# ws_get_devices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_devices_empty(fake_hass):
    """No HAIR entry -> empty list."""
    conn = _make_connection()
    await ws_get_devices(fake_hass, conn, {"id": 1, "type": "hair/devices"})
    conn.send_result.assert_called_once_with(1, [])


@pytest.mark.asyncio
async def test_get_devices_returns_summaries(fake_hass, mock_device):
    manager = MagicMock()
    manager.get_all_devices.return_value = [mock_device]
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_get_devices(fake_hass, conn, {"id": 1, "type": "hair/devices"})

    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert len(result) == 1
    assert result[0]["id"] == mock_device.id
    assert result[0]["command_count"] == len(mock_device.commands)


# ---------------------------------------------------------------------------
# ws_get_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_device_found(fake_hass, mock_device):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_get_device(
        fake_hass, conn, {"id": 2, "type": "hair/device", "device_id": mock_device.id}
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["id"] == mock_device.id
    assert result["command_count"] == 1


@pytest.mark.asyncio
async def test_get_device_not_found(fake_hass):
    manager = MagicMock()
    manager.get_device.return_value = None
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_get_device(
        fake_hass, conn, {"id": 2, "type": "hair/device", "device_id": "missing"}
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


# ---------------------------------------------------------------------------
# ws_create_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_device_success(fake_hass):
    manager = MagicMock()
    manager.async_create_device = AsyncMock(side_effect=lambda d: d)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_create_device(
        fake_hass,
        conn,
        {
            "id": 3,
            "type": "hair/device/create",
            "name": "Living Room TV",
            "device_type": "tv",
            "emitter_entity_id": "infrared.test",
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["name"] == "Living Room TV"
    assert result["device_type"] == "tv"


@pytest.mark.asyncio
async def test_create_device_invalid_type(fake_hass):
    manager = MagicMock()
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_create_device(
        fake_hass,
        conn,
        {
            "id": 3,
            "type": "hair/device/create",
            "name": "X",
            "device_type": "NOT_REAL",
            "emitter_entity_id": "infrared.test",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


# ---------------------------------------------------------------------------
# ws_update_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_device(fake_hass, mock_device):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    manager.async_update_device = AsyncMock(side_effect=lambda d: d)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_update_device(
        fake_hass,
        conn,
        {
            "id": 4,
            "type": "hair/device/update",
            "device_id": mock_device.id,
            "name": "Updated TV",
        },
    )
    conn.send_result.assert_called_once()
    assert mock_device.name == "Updated TV"


@pytest.mark.asyncio
async def test_update_device_not_found(fake_hass):
    manager = MagicMock()
    manager.get_device.return_value = None
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_update_device(
        fake_hass,
        conn,
        {"id": 4, "type": "hair/device/update", "device_id": "missing"},
    )
    conn.send_error.assert_called_once()


# ---------------------------------------------------------------------------
# ws_delete_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_device_success(fake_hass):
    manager = MagicMock()
    manager.async_remove_device = AsyncMock(return_value=True)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_delete_device(
        fake_hass, conn, {"id": 5, "type": "hair/device/delete", "device_id": "d1"}
    )
    conn.send_result.assert_called_once_with(5, {"removed": True})


@pytest.mark.asyncio
async def test_delete_device_not_found(fake_hass):
    manager = MagicMock()
    manager.async_remove_device = AsyncMock(return_value=False)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_delete_device(
        fake_hass, conn, {"id": 5, "type": "hair/device/delete", "device_id": "missing"}
    )
    conn.send_error.assert_called_once()


# ---------------------------------------------------------------------------
# ws_send_command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_command_success(fake_hass):
    manager = MagicMock()
    manager.async_send_command = AsyncMock()
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_send_command(
        fake_hass,
        conn,
        {"id": 6, "type": "hair/command/send", "device_id": "d1", "command_id": "c1"},
    )
    conn.send_result.assert_called_once_with(6, {"sent": True})


@pytest.mark.asyncio
async def test_send_command_not_found(fake_hass):
    manager = MagicMock()
    manager.async_send_command = AsyncMock(side_effect=KeyError("not found"))
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_send_command(
        fake_hass,
        conn,
        {"id": 6, "type": "hair/command/send", "device_id": "d1", "command_id": "bad"},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


# ---------------------------------------------------------------------------
# ws_delete_command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_command_success(fake_hass):
    manager = MagicMock()
    manager.async_remove_command = AsyncMock(return_value=True)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_delete_command(
        fake_hass,
        conn,
        {"id": 7, "type": "hair/command/delete", "device_id": "d1", "command_id": "c1"},
    )
    conn.send_result.assert_called_once_with(7, {"removed": True})


@pytest.mark.asyncio
async def test_delete_command_not_found(fake_hass):
    manager = MagicMock()
    manager.async_remove_command = AsyncMock(return_value=False)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_delete_command(
        fake_hass,
        conn,
        {"id": 7, "type": "hair/command/delete", "device_id": "d1", "command_id": "bad"},
    )
    conn.send_error.assert_called_once()


# ---------------------------------------------------------------------------
# ws_start_capture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_capture_no_device(fake_hass):
    manager = MagicMock()
    manager.get_device.return_value = None
    orchestrator = MagicMock()
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)

    conn = _make_connection()
    await ws_start_capture(
        fake_hass,
        conn,
        {"id": 8, "type": "hair/capture/start", "device_id": "missing"},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_start_capture_no_capture_device(fake_hass):
    device = IRDevice(
        name="TV",
        device_type=DeviceType.TV,
        emitter_entity_id="infrared.a",
        capture_device_id=None,
    )
    manager = MagicMock()
    manager.get_device.return_value = device
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_start_capture(
        fake_hass,
        conn,
        {"id": 8, "type": "hair/capture/start", "device_id": device.id},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "no_capture_device"


@pytest.mark.asyncio
async def test_start_capture_provider_unavailable(fake_hass):
    device = IRDevice(
        name="TV",
        device_type=DeviceType.TV,
        emitter_entity_id="infrared.a",
        capture_device_id="cap-1",
    )
    manager = MagicMock()
    manager.get_device.return_value = device
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.get_capture_provider_for_device",
        new_callable=AsyncMock,
        return_value=None,
    ):
        await ws_start_capture(
            fake_hass,
            conn,
            {"id": 8, "type": "hair/capture/start", "device_id": device.id},
        )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "provider_unavailable"


@pytest.mark.asyncio
async def test_start_capture_success(fake_hass, mock_capture_provider, capture_result):
    from custom_components.hair.models import CaptureSession

    device = IRDevice(
        name="TV",
        device_type=DeviceType.TV,
        emitter_entity_id="infrared.a",
        capture_device_id="cap-1",
    )
    session = CaptureSession(device_id=device.id)

    manager = MagicMock()
    manager.get_device.return_value = device
    orchestrator = MagicMock()
    orchestrator.start_capture = AsyncMock(return_value=session)
    orchestrator.subscribe = MagicMock(return_value=lambda: None)
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.get_capture_provider_for_device",
        new_callable=AsyncMock,
        return_value=mock_capture_provider,
    ):
        await ws_start_capture(
            fake_hass,
            conn,
            {"id": 8, "type": "hair/capture/start", "device_id": device.id},
        )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["session_id"] == session.session_id
    assert result["device_id"] == device.id
    # Should also send initial capture_listening event
    conn.send_event.assert_called()


@pytest.mark.asyncio
async def test_start_capture_already_in_progress(fake_hass, mock_capture_provider):
    from custom_components.hair.capture_orchestrator import CaptureInProgressError

    device = IRDevice(
        name="TV",
        device_type=DeviceType.TV,
        emitter_entity_id="infrared.a",
        capture_device_id="cap-1",
    )
    manager = MagicMock()
    manager.get_device.return_value = device
    orchestrator = MagicMock()
    orchestrator.start_capture = AsyncMock(
        side_effect=CaptureInProgressError("busy")
    )
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.get_capture_provider_for_device",
        new_callable=AsyncMock,
        return_value=mock_capture_provider,
    ):
        await ws_start_capture(
            fake_hass,
            conn,
            {"id": 8, "type": "hair/capture/start", "device_id": device.id},
        )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "in_progress"


# ---------------------------------------------------------------------------
# ws_cancel_capture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_capture(fake_hass):
    orchestrator = MagicMock()
    orchestrator.cancel_capture = AsyncMock()
    _wire_hass(fake_hass, orchestrator=orchestrator)

    conn = _make_connection()
    await ws_cancel_capture(
        fake_hass,
        conn,
        {"id": 9, "type": "hair/capture/cancel", "session_id": "sess-1"},
    )
    orchestrator.cancel_capture.assert_awaited_once_with("sess-1")
    conn.send_result.assert_called_once_with(9, {"cancelled": True})


# ---------------------------------------------------------------------------
# ws_save_captured_command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_captured_command(fake_hass, mock_device, capture_result):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    manager.async_add_command = AsyncMock(side_effect=lambda did, cmd: cmd)
    orchestrator = MagicMock()
    orchestrator.get_session_result.return_value = capture_result
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)

    conn = _make_connection()
    await ws_save_captured_command(
        fake_hass,
        conn,
        {
            "id": 10,
            "type": "hair/capture/save",
            "device_id": mock_device.id,
            "session_id": "sess-1",
            "command_name": "Volume Up",
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["name"] == "Volume Up"
    assert result["protocol"] == "NEC"


@pytest.mark.asyncio
async def test_save_captured_command_no_result(fake_hass, mock_device):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    orchestrator = MagicMock()
    orchestrator.get_session_result.return_value = None
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)

    conn = _make_connection()
    await ws_save_captured_command(
        fake_hass,
        conn,
        {
            "id": 10,
            "type": "hair/capture/save",
            "device_id": mock_device.id,
            "session_id": "missing-session",
            "command_name": "Power",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "no_capture"


@pytest.mark.asyncio
async def test_save_captured_command_with_explicit_category(
    fake_hass, mock_device, capture_result
):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    manager.async_add_command = AsyncMock(side_effect=lambda did, cmd: cmd)
    orchestrator = MagicMock()
    orchestrator.get_session_result.return_value = capture_result
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)

    conn = _make_connection()
    await ws_save_captured_command(
        fake_hass,
        conn,
        {
            "id": 10,
            "type": "hair/capture/save",
            "device_id": mock_device.id,
            "session_id": "sess-1",
            "command_name": "Custom Button",
            "command_category": "volume",
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["category"] == "volume"


# ---------------------------------------------------------------------------
# ws_get_command_templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_command_templates(fake_hass):
    conn = _make_connection()
    await ws_get_command_templates(
        fake_hass,
        conn,
        {"id": 11, "type": "hair/templates", "device_type": "tv"},
    )
    conn.send_result.assert_called_once()
    templates = conn.send_result.call_args[0][1]
    assert isinstance(templates, list)
    assert len(templates) > 0
    names = {t["name"] for t in templates}
    assert "Power" in names
    assert "Volume Up" in names


# ---------------------------------------------------------------------------
# ws_get_capture_providers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_capture_providers_empty(fake_hass):
    """No capture hardware -> empty list."""
    fake_hass.config.components = set()
    fake_hass.config_entries.async_entries = MagicMock(return_value=[])

    conn = _make_connection()
    await ws_get_capture_providers(
        fake_hass,
        conn,
        {"id": 12, "type": "hair/capture/providers"},
    )
    conn.send_result.assert_called_once_with(12, [])


# ---------------------------------------------------------------------------
# Edge: no HAIR entry configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handlers_graceful_when_not_configured(fake_hass):
    """All device/command handlers should send an error when HAIR is not set up."""
    conn = _make_connection()

    await ws_get_device(fake_hass, conn, {"id": 1, "device_id": "x"})
    conn.send_error.assert_called()

    conn.reset_mock()
    await ws_create_device(
        fake_hass,
        conn,
        {"id": 2, "name": "X", "device_type": "tv", "emitter_entity_id": "ir.a"},
    )
    conn.send_error.assert_called()

    conn.reset_mock()
    await ws_delete_device(fake_hass, conn, {"id": 3, "device_id": "x"})
    conn.send_error.assert_called()

    conn.reset_mock()
    await ws_send_command(
        fake_hass, conn, {"id": 4, "device_id": "x", "command_id": "c"}
    )
    conn.send_error.assert_called()


# ---------------------------------------------------------------------------
# Signal Monitor WS API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_unknown_devices_empty(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_get_unknown_devices(
        fake_hass, conn, {"id": 100, "type": "hair/unknown/devices"}
    )
    conn.send_result.assert_called_once_with(100, [])


@pytest.mark.asyncio
async def test_get_unknown_devices_returns_sorted(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    d1 = UnknownDevice(id="d1", fingerprint="fp1", hit_count=5)
    d2 = UnknownDevice(id="d2", fingerprint="fp2", hit_count=20)
    monitor._signal_store.add_device(d1)
    monitor._signal_store.add_device(d2)

    conn = _make_connection()
    await ws_get_unknown_devices(
        fake_hass, conn,
        {"id": 101, "type": "hair/unknown/devices", "min_hits": 0},
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert len(result) == 2
    assert result[0]["id"] == "d2"  # Higher hit count first.


@pytest.mark.asyncio
async def test_get_unknown_device_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    d = UnknownDevice(id="d1", fingerprint="fp1", hit_count=10)
    monitor._signal_store.add_device(d)

    conn = _make_connection()
    await ws_get_unknown_device(
        fake_hass, conn,
        {"id": 102, "type": "hair/unknown/device", "device_id": "d1"},
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["id"] == "d1"


@pytest.mark.asyncio
async def test_get_unknown_device_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_get_unknown_device(
        fake_hass, conn,
        {"id": 103, "type": "hair/unknown/device", "device_id": "nope"},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_dismiss_unknown_device(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    d = UnknownDevice(id="d1", fingerprint="fp1", hit_count=5)
    monitor._signal_store.add_device(d)

    conn = _make_connection()
    await ws_dismiss_unknown(
        fake_hass, conn,
        {"id": 104, "type": "hair/unknown/dismiss", "device_id": "d1"},
    )
    conn.send_result.assert_called_once()
    assert d.dismissed


@pytest.mark.asyncio
async def test_dismiss_unknown_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_dismiss_unknown(
        fake_hass, conn,
        {"id": 105, "type": "hair/unknown/dismiss", "device_id": "nope"},
    )
    conn.send_error.assert_called_once()


@pytest.mark.asyncio
async def test_undismiss_unknown_device(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    d = UnknownDevice(id="d1", fingerprint="fp1", dismissed=True)
    monitor._signal_store.add_device(d)
    monitor._signal_store.add_dismissed("fp1")

    conn = _make_connection()
    await ws_undismiss_unknown(
        fake_hass, conn,
        {"id": 106, "type": "hair/unknown/undismiss", "device_id": "d1"},
    )
    conn.send_result.assert_called_once()
    assert not d.dismissed


@pytest.mark.asyncio
async def test_assign_signal_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sig = UnknownSignal(fingerprint="sig_fp", protocol="NEC", code="0x1234")
    device = UnknownDevice(id="ud1", fingerprint="dev_fp", signals=[sig])
    monitor._signal_store.add_device(device)

    hair_device = IRDevice(id="hd1", name="TV")
    monitor._hair_store.get_device.return_value = hair_device

    conn = _make_connection()
    await ws_assign_signal(
        fake_hass, conn,
        {
            "id": 107,
            "type": "hair/unknown/assign",
            "device_id": "ud1",
            "signal_fingerprint": "sig_fp",
            "hair_device_id": "hd1",
            "command_name": "Power",
            "command_category": "custom",
        },
    )
    conn.send_result.assert_called_once()
    assert len(hair_device.commands) == 1


@pytest.mark.asyncio
async def test_assign_signal_failure(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_assign_signal(
        fake_hass, conn,
        {
            "id": 108,
            "type": "hair/unknown/assign",
            "device_id": "nope",
            "signal_fingerprint": "x",
            "hair_device_id": "y",
            "command_name": "Power",
            "command_category": "custom",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "assign_failed"


@pytest.mark.asyncio
async def test_test_signal_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sig = UnknownSignal(fingerprint="sig_fp", protocol="NEC", code="0x1234")
    device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_test_signal(
        fake_hass, conn,
        {
            "id": 109,
            "type": "hair/unknown/test",
            "signal_fingerprint": "sig_fp",
            "emitter_entity_id": "remote.ir",
        },
    )
    conn.send_result.assert_called_once()
    fake_hass.services.async_call.assert_called_once()


@pytest.mark.asyncio
async def test_test_signal_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_test_signal(
        fake_hass, conn,
        {
            "id": 110,
            "type": "hair/unknown/test",
            "signal_fingerprint": "nope",
            "emitter_entity_id": "remote.ir",
        },
    )
    conn.send_error.assert_called_once()


@pytest.mark.asyncio
async def test_clear_unknowns(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    monitor._signal_store.add_device(
        UnknownDevice(id="d1", fingerprint="fp1")
    )

    conn = _make_connection()
    await ws_clear_unknowns(
        fake_hass, conn, {"id": 111, "type": "hair/unknown/clear"},
    )
    conn.send_result.assert_called_once()
    assert monitor._signal_store.device_count == 0


@pytest.mark.asyncio
async def test_unknown_ws_not_configured(fake_hass):
    """All unknown/* endpoints return gracefully when HAIR not configured."""
    fake_hass.data[DOMAIN] = {}

    conn = _make_connection()
    await ws_get_unknown_devices(
        fake_hass, conn, {"id": 200, "type": "hair/unknown/devices"}
    )
    # get_unknown_devices returns empty list, not error.
    conn.send_result.assert_called_once_with(200, [])

    conn.reset_mock()
    await ws_get_unknown_device(
        fake_hass, conn,
        {"id": 201, "type": "hair/unknown/device", "device_id": "x"},
    )
    conn.send_error.assert_called_once()
