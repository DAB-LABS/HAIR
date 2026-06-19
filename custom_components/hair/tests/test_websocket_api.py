"""Tests for the HAIR WebSocket API handlers."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    DOMAIN,
    DeviceType,
)
from custom_components.hair.models import (
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    async_register_websocket_commands,
    ws_assign_new_device,
    ws_assign_signal,
    ws_cancel_capture,
    ws_clear_unknowns,
    ws_clip_create_remote,
    ws_clip_create_signal,
    ws_clip_delete_remote,
    ws_clip_validate_pronto,
    ws_codes_get_brands,
    ws_codes_import_remote,
    ws_create_device,
    ws_delete_command,
    ws_delete_device,
    ws_delete_signal,
    ws_dismiss_unknown,
    ws_duplicate_device,
    ws_get_capture_providers,
    ws_get_command_templates,
    ws_get_device,
    ws_get_devices,
    ws_get_sniffer_status,
    ws_get_unknown_device,
    ws_get_unknown_devices,
    ws_reorder_commands,
    ws_reorder_devices,
    ws_reorder_unknown_devices,
    ws_reorder_unknown_signals,
    ws_save_captured_command,
    ws_send_command,
    ws_set_command_tx_force_raw,
    ws_set_signal_alias,
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
            "device_type": "media_player",
            "emitter_entity_ids": ["infrared.test"],
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["name"] == "Living Room TV"
    assert result["device_type"] == "media_player"


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
            "emitter_entity_ids": ["infrared.test"],
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
# ws_duplicate_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_device_success(fake_hass):
    source = IRDevice(
        id="src-1",
        name="Living Room TV",
        device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.tx"],
    )
    manager = MagicMock()
    manager.get_device.return_value = source
    manager.async_create_device = AsyncMock(side_effect=lambda d: d)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_duplicate_device(
        fake_hass,
        conn,
        {
            "id": 11,
            "type": "hair/device/duplicate",
            "device_id": "src-1",
            "new_name": "Bedroom TV",
        },
    )

    # Source untouched; create called once with the clone.
    manager.async_create_device.assert_awaited_once()
    clone_arg = manager.async_create_device.await_args.args[0]
    assert clone_arg.name == "Bedroom TV"
    assert clone_arg.id != source.id
    assert clone_arg.emitter_entity_ids == ["infrared.tx"]

    # Result payload describes the new device, not the source.
    conn.send_result.assert_called_once()
    payload = conn.send_result.call_args[0][1]
    assert payload["id"] == clone_arg.id
    assert payload["name"] == "Bedroom TV"


@pytest.mark.asyncio
async def test_duplicate_device_source_not_found(fake_hass):
    manager = MagicMock()
    manager.get_device.return_value = None
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_duplicate_device(
        fake_hass,
        conn,
        {
            "id": 11,
            "type": "hair/device/duplicate",
            "device_id": "missing",
            "new_name": "Bedroom TV",
        },
    )

    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_duplicate_device_empty_name(fake_hass):
    source = IRDevice(
        id="src-1",
        name="Living Room TV",
        device_type=DeviceType.MEDIA_PLAYER,
    )
    manager = MagicMock()
    manager.get_device.return_value = source
    manager.async_create_device = AsyncMock()
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_duplicate_device(
        fake_hass,
        conn,
        {
            "id": 11,
            "type": "hair/device/duplicate",
            "device_id": "src-1",
            "new_name": "   ",
        },
    )

    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    manager.async_create_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_device_not_configured(fake_hass):
    conn = _make_connection()
    await ws_duplicate_device(
        fake_hass,
        conn,
        {
            "id": 11,
            "type": "hair/device/duplicate",
            "device_id": "src-1",
            "new_name": "Bedroom TV",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_configured"


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
# ws_set_command_tx_force_raw
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_tx_force_raw_success(fake_hass):
    manager = MagicMock()
    manager.async_set_command_tx_force_raw = AsyncMock(return_value=True)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_set_command_tx_force_raw(
        fake_hass,
        conn,
        {
            "id": 9,
            "type": "hair/command/set-tx-force-raw",
            "device_id": "d1",
            "command_id": "c1",
            "tx_force_raw": True,
        },
    )
    manager.async_set_command_tx_force_raw.assert_awaited_once_with("d1", "c1", True)
    conn.send_result.assert_called_once_with(9, {"tx_force_raw": True})


@pytest.mark.asyncio
async def test_set_tx_force_raw_not_found(fake_hass):
    manager = MagicMock()
    manager.async_set_command_tx_force_raw = AsyncMock(return_value=False)
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_set_command_tx_force_raw(
        fake_hass,
        conn,
        {
            "id": 9,
            "type": "hair/command/set-tx-force-raw",
            "device_id": "d1",
            "command_id": "bad",
            "tx_force_raw": False,
        },
    )
    conn.send_error.assert_called_once()


@pytest.mark.asyncio
async def test_get_sniffer_status_reports_has_receivers(fake_hass):
    monitor = MagicMock()
    monitor.has_receivers = True
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_get_sniffer_status(
        fake_hass, conn, {"id": 11, "type": "hair/sniffer/status"}
    )
    conn.send_result.assert_called_once_with(11, {"has_receivers": True})


# ---------------------------------------------------------------------------
# Code database picker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_codes_get_brands(fake_hass):
    conn = _make_connection()
    tree = [{"brand": "lg", "label": "LG", "codebooks": []}]
    with patch("custom_components.hair.code_library.get_tree", return_value=tree):
        await ws_codes_get_brands(
            fake_hass, conn, {"id": 1, "type": "hair/codes/brands"}
        )
    conn.send_result.assert_called_once_with(1, tree)


@pytest.mark.asyncio
async def test_codes_import_remote_success(fake_hass):
    monitor = MagicMock()
    monitor.import_manual_remote = AsyncMock(
        return_value={"device": {"id": "d1"}, "imported": 3, "skipped": 0}
    )
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    entries = [{"name": "Power", "code": "0000 006D 0002 0000 0020 0040 0020 0040"}]
    with patch(
        "custom_components.hair.code_library.materialize_codebook",
        return_value=entries,
    ), patch(
        "custom_components.hair.code_library.codebook_label", return_value="LG TV"
    ):
        await ws_codes_import_remote(
            fake_hass,
            conn,
            {
                "id": 2,
                "type": "hair/codes/import-remote",
                "codebook_id": "mod:LGTVCode",
            },
        )
    monitor.import_manual_remote.assert_awaited_once_with("LG TV", entries)
    conn.send_result.assert_called_once()
    assert conn.send_result.call_args[0][1]["imported"] == 3


@pytest.mark.asyncio
async def test_codes_import_remote_no_codes_errors(fake_hass):
    _wire_hass(fake_hass, signal_monitor=MagicMock())
    conn = _make_connection()
    with patch(
        "custom_components.hair.code_library.materialize_codebook", return_value=[]
    ):
        await ws_codes_import_remote(
            fake_hass,
            conn,
            {
                "id": 2,
                "type": "hair/codes/import-remote",
                "codebook_id": "mod:LGTVCode",
            },
        )
    conn.send_error.assert_called_once()


# ---------------------------------------------------------------------------
# ws_reorder_commands
# ---------------------------------------------------------------------------


def _make_device_with_commands(*command_specs: tuple[str, str]) -> IRDevice:
    """Build an IRDevice with the given (id, name) command tuples."""
    from custom_components.hair.models import IRCommand

    device = IRDevice(id="d1", name="x", device_type=DeviceType.MEDIA_PLAYER)
    for cmd_id, cmd_name in command_specs:
        device.commands.append(
            IRCommand(id=cmd_id, name=cmd_name, protocol="NEC", code="0x1")
        )
    return device


@pytest.mark.asyncio
async def test_reorder_commands_success(fake_hass):
    device = _make_device_with_commands(("c1", "A"), ("c2", "B"), ("c3", "C"))
    manager = MagicMock()
    manager.get_device.return_value = device
    manager.async_update_device = AsyncMock()
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_reorder_commands(
        fake_hass,
        conn,
        {
            "id": 9,
            "type": "hair/device/reorder-commands",
            "device_id": "d1",
            "command_ids": ["c3", "c1", "c2"],
        },
    )

    assert [c.id for c in device.commands] == ["c3", "c1", "c2"]
    manager.async_update_device.assert_awaited_once_with(device)
    conn.send_result.assert_called_once()
    # Returned payload is the full canonical device.
    result_payload = conn.send_result.call_args[0][1]
    assert result_payload["id"] == "d1"
    assert [c["id"] for c in result_payload["commands"]] == ["c3", "c1", "c2"]


@pytest.mark.asyncio
async def test_reorder_commands_device_not_found(fake_hass):
    manager = MagicMock()
    manager.get_device.return_value = None
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_reorder_commands(
        fake_hass,
        conn,
        {
            "id": 9,
            "type": "hair/device/reorder-commands",
            "device_id": "missing",
            "command_ids": [],
        },
    )

    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_reorder_commands_invalid_format(fake_hass):
    device = _make_device_with_commands(("c1", "A"), ("c2", "B"))
    manager = MagicMock()
    manager.get_device.return_value = device
    manager.async_update_device = AsyncMock()
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_reorder_commands(
        fake_hass,
        conn,
        {
            "id": 9,
            "type": "hair/device/reorder-commands",
            "device_id": "d1",
            "command_ids": ["c1", "ghost"],  # unknown ID
        },
    )

    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    # Failed validation must not persist.
    manager.async_update_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_reorder_commands_not_configured(fake_hass):
    # No HAIR entry data wired into hass.data.
    conn = _make_connection()
    await ws_reorder_commands(
        fake_hass,
        conn,
        {
            "id": 9,
            "type": "hair/device/reorder-commands",
            "device_id": "d1",
            "command_ids": [],
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_configured"


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
        device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.a"],
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
        device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.a"],
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
        device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.a"],
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
        device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.a"],
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
        {"id": 11, "type": "hair/templates", "device_type": "media_player"},
    )
    conn.send_result.assert_called_once()
    templates = conn.send_result.call_args[0][1]
    assert isinstance(templates, list)
    assert len(templates) > 0
    names = {t["name"] for t in templates}
    assert "Power On" in names
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
        {"id": 2, "name": "X", "device_type": "media_player", "emitter_entity_ids": ["ir.a"]},
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
    # Manual order (v0.3.2): the most recently added remote is on top.
    assert result[0]["id"] == "d2"


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

    sig = UnknownSignal(id="sig_fp", fingerprint="sig_fp", protocol="NEC", code="0x1234")
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
            "signal_id": "sig_fp",
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
            "signal_id": "x",
            "hair_device_id": "y",
            "command_name": "Power",
            "command_category": "custom",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "device_not_found"


@pytest.mark.asyncio
async def test_test_signal_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sig = UnknownSignal(
        id="sig_fp", fingerprint="sig_fp", protocol="NEC", code="0x1234",
        raw_timings=[9000, -4500, 560, -560],
    )
    device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
    monitor._signal_store.add_device(device)

    import sys
    ir_mod = sys.modules["homeassistant.components.infrared"]
    mock_ir_send = AsyncMock()
    orig = ir_mod.async_send_command
    ir_mod.async_send_command = mock_ir_send
    conn = _make_connection()
    try:
        await ws_test_signal(
            fake_hass, conn,
            {
                "id": 109,
                "type": "hair/unknown/test",
                "signal_id": "sig_fp",
                "emitter_entity_id": "remote.ir",
            },
        )
    finally:
        ir_mod.async_send_command = orig
    conn.send_result.assert_called_once()
    mock_ir_send.assert_awaited_once()


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
            "signal_id": "nope",
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


# ---------------------------------------------------------------------------
# ws_delete_signal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_signal_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sig1 = UnknownSignal(id="sig1", fingerprint="sig1", protocol="NEC", code="0x1")
    sig2 = UnknownSignal(id="sig2", fingerprint="sig2", protocol="NEC", code="0x2")
    device = UnknownDevice(
        id="ud1", fingerprint="fp", signals=[sig1, sig2],
    )
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_delete_signal(
        fake_hass, conn,
        {
            "id": 120,
            "type": "hair/unknown/signal/delete",
            "device_id": "ud1",
            "signal_id": "sig1",
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["deleted"] is True
    assert result["device_removed"] is False
    # Verify signal was actually removed.
    remaining = monitor._signal_store.get_device("ud1")
    assert remaining is not None
    assert len(remaining.signals) == 1


@pytest.mark.asyncio
async def test_delete_signal_last_removes_device(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sig = UnknownSignal(id="sig1", fingerprint="sig1", protocol="NEC", code="0x1")
    device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_delete_signal(
        fake_hass, conn,
        {
            "id": 121,
            "type": "hair/unknown/signal/delete",
            "device_id": "ud1",
            "signal_id": "sig1",
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["device_removed"] is True
    assert monitor._signal_store.get_device("ud1") is None


@pytest.mark.asyncio
async def test_delete_signal_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_delete_signal(
        fake_hass, conn,
        {
            "id": 122,
            "type": "hair/unknown/signal/delete",
            "device_id": "nope",
            "signal_id": "x",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "device_not_found"


# ---------------------------------------------------------------------------
# ws_assign_new_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_new_device_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    manager = MagicMock()
    manager._register_ha_device = MagicMock()
    manager._entity_factory = MagicMock()
    manager._entity_factory.async_create_entities = AsyncMock()
    _wire_hass(fake_hass, manager=manager, signal_monitor=monitor)

    sig = UnknownSignal(
        id="sig_fp", fingerprint="sig_fp", protocol="NEC", code="0x1234",
        frequency=38000, hit_count=5,
    )
    device = UnknownDevice(
        id="ud1", fingerprint="dev_fp", signals=[sig], hit_count=5,
    )
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_assign_new_device(
        fake_hass, conn,
        {
            "id": 130,
            "type": "hair/unknown/assign-new-device",
            "device_id": "ud1",
            "signal_id": "sig_fp",
            "device_name": "Living Room TV",
            "device_type": "media_player",
            "emitter_entity_ids": ["remote.ir_blaster"],
            "command_name": "Power",
            "command_category": "power",
        },
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["assigned"] is True
    assert "device_id" in result
    assert "command_id" in result

    # HA device registration should have been called.
    manager._register_ha_device.assert_called_once()
    manager._entity_factory.async_create_entities.assert_called_once()

    # Unknown signal persists -- copied into the new device, not consumed.
    remaining = monitor._signal_store.get_device("ud1")
    assert remaining is not None
    assert remaining.get_signal("sig_fp") is not None


@pytest.mark.asyncio
async def test_assign_new_device_invalid_type(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sig = UnknownSignal(id="sig_fp", fingerprint="sig_fp", protocol="NEC", code="0x1")
    device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_assign_new_device(
        fake_hass, conn,
        {
            "id": 131,
            "type": "hair/unknown/assign-new-device",
            "device_id": "ud1",
            "signal_id": "sig_fp",
            "device_name": "Test",
            "device_type": "invalid_type",
            "emitter_entity_ids": ["remote.ir"],
            "command_name": "Power",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_device_type"

    # Signal should NOT have been removed.
    assert monitor._signal_store.get_device("ud1") is not None


@pytest.mark.asyncio
async def test_assign_new_device_signal_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    device = UnknownDevice(id="ud1", fingerprint="fp")
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_assign_new_device(
        fake_hass, conn,
        {
            "id": 132,
            "type": "hair/unknown/assign-new-device",
            "device_id": "ud1",
            "signal_id": "nonexistent",
            "device_name": "Test",
            "device_type": "media_player",
            "emitter_entity_ids": ["remote.ir"],
            "command_name": "Power",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "signal_not_found"


# ---------------------------------------------------------------------------
# Clips: create-remote / create-signal / validate-pronto / set-alias / source
# ---------------------------------------------------------------------------

# A minimal, structurally valid learned Pronto code.
_VALID_PRONTO = "0000 006D 0002 0000 0010 0010 0010 0010"


@pytest.mark.asyncio
async def test_clip_create_remote_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_clip_create_remote(
        fake_hass, conn,
        {"id": 200, "type": "hair/clip/create-remote", "name": "Living Room"},
    )
    conn.send_result.assert_called_once()
    payload = conn.send_result.call_args[0][1]
    assert payload["label"] == "Living Room"
    assert payload["source"] == "manual"
    # The created device is in the store and tagged manual.
    devices = monitor._signal_store.get_all_devices()
    assert len(devices) == 1
    assert devices[0].source == "manual"


@pytest.mark.asyncio
async def test_clip_create_remote_empty_name_errors(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_clip_create_remote(
        fake_hass, conn,
        {"id": 201, "type": "hair/clip/create-remote", "name": "   "},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_name"


@pytest.mark.asyncio
async def test_clip_create_signal_happy_path(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    remote = await monitor.create_manual_remote("Clip A")

    conn = _make_connection()
    await ws_clip_create_signal(
        fake_hass, conn,
        {
            "id": 202,
            "type": "hair/clip/create-signal",
            "device_id": remote.id,
            "pronto": _VALID_PRONTO,
            "alias": "Power",
        },
    )
    conn.send_result.assert_called_once()
    sig = conn.send_result.call_args[0][1]["signal"]
    assert sig["protocol"] == "PRONTO"
    assert sig["source"] == "manual"
    assert sig["alias"] == "Power"
    assert len(monitor._signal_store.get_device(remote.id).signals) == 1


@pytest.mark.asyncio
async def test_clip_create_signal_invalid_pronto_errors(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    remote = await monitor.create_manual_remote("Clip A")

    conn = _make_connection()
    await ws_clip_create_signal(
        fake_hass, conn,
        {
            "id": 203,
            "type": "hair/clip/create-signal",
            "device_id": remote.id,
            "pronto": "not hex",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_pronto"


@pytest.mark.asyncio
async def test_clip_create_signal_unknown_device_errors(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    conn = _make_connection()
    await ws_clip_create_signal(
        fake_hass, conn,
        {
            "id": 204,
            "type": "hair/clip/create-signal",
            "device_id": "nope",
            "pronto": _VALID_PRONTO,
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "device_not_found"


@pytest.mark.asyncio
async def test_clip_validate_pronto_valid(fake_hass):
    conn = _make_connection()
    await ws_clip_validate_pronto(
        fake_hass, conn,
        {"id": 205, "type": "hair/clip/validate-pronto", "pronto": _VALID_PRONTO},
    )
    conn.send_result.assert_called_once()
    payload = conn.send_result.call_args[0][1]
    assert payload["valid"] is True
    assert payload["burst_pair_count"] == 2


@pytest.mark.asyncio
async def test_clip_validate_pronto_invalid(fake_hass):
    conn = _make_connection()
    await ws_clip_validate_pronto(
        fake_hass, conn,
        {"id": 206, "type": "hair/clip/validate-pronto", "pronto": "0100 zz"},
    )
    conn.send_result.assert_called_once()
    payload = conn.send_result.call_args[0][1]
    assert payload["valid"] is False
    assert payload["errors"]
    assert payload["recognized_protocol"] is None


@pytest.mark.asyncio
async def test_clip_validate_pronto_recognized(fake_hass):
    """A valid Pronto that decodes surfaces its recognized protocol."""
    conn = _make_connection()
    with patch(
        "custom_components.hair.protocol_decode.decode_to_fields",
        return_value=("NEC", 0xFB04, 0x08, "NEC:0xfb04:0x08"),
    ):
        await ws_clip_validate_pronto(
            fake_hass, conn,
            {"id": 207, "type": "hair/clip/validate-pronto", "pronto": _VALID_PRONTO},
        )
    payload = conn.send_result.call_args[0][1]
    assert payload["recognized_protocol"] == "NEC"


@pytest.mark.asyncio
async def test_set_signal_alias_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    remote = await monitor.create_manual_remote("Clip A")
    await monitor.create_manual_signal(remote.id, _VALID_PRONTO)
    sid = monitor._signal_store.get_device(remote.id).signals[0].id

    conn = _make_connection()
    await ws_set_signal_alias(
        fake_hass, conn,
        {
            "id": 207,
            "type": "hair/unknown/signal/set-alias",
            "device_id": remote.id,
            "signal_id": sid,
            "alias": "  Mute  ",
        },
    )
    conn.send_result.assert_called_once_with(207, {"alias": "Mute"})
    assert monitor._signal_store.get_device(remote.id).signals[0].alias == "Mute"


@pytest.mark.asyncio
async def test_set_signal_alias_signal_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    remote = await monitor.create_manual_remote("Clip A")

    conn = _make_connection()
    await ws_set_signal_alias(
        fake_hass, conn,
        {
            "id": 208,
            "type": "hair/unknown/signal/set-alias",
            "device_id": remote.id,
            "signal_id": "missing",
            "alias": "x",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "signal_not_found"


@pytest.mark.asyncio
async def test_get_unknown_devices_source_filter(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sniffed = UnknownDevice(id="s1", fingerprint="fp1", hit_count=5)
    monitor._signal_store.add_device(sniffed)
    await monitor.create_manual_remote("Clip A")

    conn = _make_connection()
    await ws_get_unknown_devices(
        fake_hass, conn,
        {
            "id": 209,
            "type": "hair/unknown/devices",
            "min_hits": 0,
            "source": "manual",
        },
    )
    result = conn.send_result.call_args[0][1]
    assert len(result) == 1
    assert result[0]["source"] == "manual"


@pytest.mark.asyncio
async def test_clear_unknowns_source_scoped(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)

    sniffed = UnknownDevice(id="s1", fingerprint="fp1", hit_count=5)
    monitor._signal_store.add_device(sniffed)
    await monitor.create_manual_remote("Clip A")

    conn = _make_connection()
    await ws_clear_unknowns(
        fake_hass, conn,
        {"id": 210, "type": "hair/unknown/clear", "source": "manual"},
    )
    conn.send_result.assert_called_once_with(210, {"cleared": True})
    remaining = monitor._signal_store.get_all_devices()
    assert len(remaining) == 1
    assert remaining[0].source == "sniffed"


@pytest.mark.asyncio
async def test_clip_delete_remote_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    remote = await monitor.create_manual_remote("Empty clip")

    conn = _make_connection()
    await ws_clip_delete_remote(
        fake_hass, conn,
        {"id": 211, "type": "hair/clip/delete-remote", "device_id": remote.id},
    )
    conn.send_result.assert_called_once_with(211, {"deleted": True})
    assert monitor._signal_store.get_device(remote.id) is None


@pytest.mark.asyncio
async def test_clip_delete_remote_rejects_sniffed(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    sniffed = UnknownDevice(id="s1", fingerprint="fp1", hit_count=5)
    monitor._signal_store.add_device(sniffed)

    conn = _make_connection()
    await ws_clip_delete_remote(
        fake_hass, conn,
        {"id": 212, "type": "hair/clip/delete-remote", "device_id": "s1"},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_manual"
    # Sniffed device is untouched.
    assert monitor._signal_store.get_device("s1") is not None


# ---------------------------------------------------------------------------
# Drag-to-reorder WS endpoints (v0.3.2)
# ---------------------------------------------------------------------------


def _wire_signal_store(fake_hass, monitor):
    """Expose the monitor's signal store in entry data and stub its save."""
    monitor._signal_store.async_save = AsyncMock()
    fake_hass.data[DOMAIN]["entry-1"]["signal_store"] = monitor._signal_store


@pytest.mark.asyncio
async def test_reorder_devices_success(fake_hass):
    manager = MagicMock()
    manager.async_reorder_devices = AsyncMock()
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_reorder_devices(
        fake_hass, conn,
        {"id": 300, "type": "hair/devices/reorder",
         "device_ids": ["b", "a"]},
    )
    manager.async_reorder_devices.assert_awaited_once_with(["b", "a"])
    conn.send_result.assert_called_once_with(300, {"reordered": True})


@pytest.mark.asyncio
async def test_reorder_devices_invalid_format(fake_hass):
    manager = MagicMock()
    manager.async_reorder_devices = AsyncMock(
        side_effect=ValueError("Reorder list does not match current devices")
    )
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    await ws_reorder_devices(
        fake_hass, conn,
        {"id": 301, "type": "hair/devices/reorder", "device_ids": ["ghost"]},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_reorder_unknown_devices_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    _wire_signal_store(fake_hass, monitor)
    m1 = UnknownDevice(id="m1", fingerprint="m1", source="manual")
    m2 = UnknownDevice(id="m2", fingerprint="m2", source="manual")
    monitor._signal_store.add_device(m1)
    monitor._signal_store.add_device(m2)

    conn = _make_connection()
    await ws_reorder_unknown_devices(
        fake_hass, conn,
        {"id": 302, "type": "hair/unknown/reorder",
         "source": "manual", "device_ids": ["m2", "m1"]},
    )
    conn.send_result.assert_called_once_with(302, {"reordered": True})
    assert (m2.order, m1.order) == (0, 1)
    monitor._signal_store.async_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_reorder_unknown_devices_invalid_format(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    _wire_signal_store(fake_hass, monitor)
    monitor._signal_store.add_device(
        UnknownDevice(id="s1", fingerprint="s1", source="sniffed")
    )

    conn = _make_connection()
    await ws_reorder_unknown_devices(
        fake_hass, conn,
        {"id": 303, "type": "hair/unknown/reorder",
         "source": "sniffed", "device_ids": ["s1", "ghost"]},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_reorder_unknown_signals_success(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    _wire_signal_store(fake_hass, monitor)
    device = UnknownDevice(id="d1", fingerprint="d1", source="manual")
    device.signals = [
        UnknownSignal(id="a", fingerprint="a"),
        UnknownSignal(id="b", fingerprint="b"),
    ]
    monitor._signal_store.add_device(device)

    conn = _make_connection()
    await ws_reorder_unknown_signals(
        fake_hass, conn,
        {"id": 304, "type": "hair/unknown/signal/reorder",
         "device_id": "d1", "signal_ids": ["b", "a"]},
    )
    conn.send_result.assert_called_once_with(304, {"reordered": True})
    assert [s.id for s in device.signals] == ["b", "a"]


@pytest.mark.asyncio
async def test_reorder_unknown_signals_device_not_found(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    _wire_hass(fake_hass, signal_monitor=monitor)
    _wire_signal_store(fake_hass, monitor)

    conn = _make_connection()
    await ws_reorder_unknown_signals(
        fake_hass, conn,
        {"id": 305, "type": "hair/unknown/signal/reorder",
         "device_id": "missing", "signal_ids": []},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"
