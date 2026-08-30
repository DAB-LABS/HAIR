"""Tests for the HAIR WebSocket API handlers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    DOMAIN,
    DeviceType,
)
from custom_components.hair.models import (
    IRDevice,
    IRTrigger,
    TriggerRemote,
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
    ws_create_trigger_remote,
    ws_delete_command,
    ws_delete_device,
    ws_delete_signal,
    ws_delete_trigger_remote,
    ws_device_make_remote,
    ws_device_matrix_cells,
    ws_dismiss_unknown,
    ws_duplicate_device,
    ws_duplicate_trigger_remote,
    ws_get_capture_providers,
    ws_get_command_templates,
    ws_get_device,
    ws_get_devices,
    ws_get_receivers,
    ws_get_sniffer_status,
    ws_get_trigger_drawer,
    ws_get_triggers,
    ws_get_unknown_device,
    ws_get_unknown_devices,
    ws_list_trigger_remotes,
    ws_pin_trigger_remote_device,
    ws_rename_trigger_drawer,
    ws_reorder_commands,
    ws_reorder_devices,
    ws_reorder_triggers,
    ws_reorder_unknown_devices,
    ws_reorder_unknown_signals,
    ws_save_captured_command,
    ws_send_command,
    ws_set_command_tx_force_raw,
    ws_set_signal_alias,
    ws_start_capture,
    ws_test_signal,
    ws_trigger_remote_make_device,
    ws_trigger_remote_matrix_cell,
    ws_trigger_remote_matrix_cells,
    ws_undismiss_unknown,
    ws_unknown_signal_snap_preview,
    ws_unpin_trigger_remote_device,
    ws_update_device,
    ws_wig_make_remote,
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
    if manager is None:
        manager = MagicMock()
        # The assign handlers await these post-assign (auto-map + persist).
        manager.async_apply_auto_map = AsyncMock()
        manager._store.async_save = AsyncMock()
    entry_data = {
        "device_manager": manager,
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


def _wire_triggers(hass, store=None):
    """Set up hass.data[DOMAIN] with a store + config_entry, the shape the
    trigger/trigger-drawer handlers read (``_get_first_entry_data`` only
    requires "device_manager" to be present to recognize the entry)."""
    if store is None:
        store = MagicMock()
        store.async_save = AsyncMock()
    entry_data = {
        "device_manager": MagicMock(),
        "store": store,
        "config_entry": SimpleNamespace(entry_id="entry-1"),
    }
    hass.data[DOMAIN] = {"entry-1": entry_data}
    return store


def _mock_device_registry(ha_device_id: str | None):
    """Patch websocket_api's dr.async_get the same way
    test_device_manager.py patches device_manager's -- registered
    devices resolve to a MagicMock HA device carrying ha_device_id;
    None reproduces the unregistered case _ha_device_id() must also
    handle."""
    resolved = MagicMock(id=ha_device_id) if ha_device_id is not None else None
    return patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=MagicMock(async_get_device=MagicMock(return_value=resolved)),
    )


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


@pytest.mark.asyncio
async def test_get_devices_summary_carries_ha_device_id_when_registered(
    fake_hass, mock_device
):
    """Exit-to-entity link (exit-to-entity-link.md): a device with a
    matching HA registry entry surfaces that entry's id on the list
    payload, not just the full one -- the Closet/device-list surfaces
    read summaries, not full payloads."""
    manager = MagicMock()
    manager.get_all_devices.return_value = [mock_device]
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    with _mock_device_registry("ha-dev-42"):
        await ws_get_devices(fake_hass, conn, {"id": 1, "type": "hair/devices"})

    result = conn.send_result.call_args[0][1]
    assert result[0]["ha_device_id"] == "ha-dev-42"


@pytest.mark.asyncio
async def test_get_devices_summary_ha_device_id_none_when_unregistered(
    fake_hass, mock_device
):
    """No matching HA registry entry -> None, not a missing key or a
    raised error. The frontend's guard (no glyph without an id) relies
    on this being an honest null, the same shape the matrix field
    already uses for its own "nothing here" case."""
    manager = MagicMock()
    manager.get_all_devices.return_value = [mock_device]
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_get_devices(fake_hass, conn, {"id": 1, "type": "hair/devices"})

    result = conn.send_result.call_args[0][1]
    assert result[0]["ha_device_id"] is None


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
async def test_get_device_full_carries_ha_device_id_when_registered(
    fake_hass, mock_device
):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    with _mock_device_registry("ha-dev-42"):
        await ws_get_device(
            fake_hass,
            conn,
            {"id": 2, "type": "hair/device", "device_id": mock_device.id},
        )
    result = conn.send_result.call_args[0][1]
    assert result["ha_device_id"] == "ha-dev-42"


@pytest.mark.asyncio
async def test_get_device_full_ha_device_id_none_when_unregistered(
    fake_hass, mock_device
):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    _wire_hass(fake_hass, manager=manager)

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_get_device(
            fake_hass,
            conn,
            {"id": 2, "type": "hair/device", "device_id": mock_device.id},
        )
    result = conn.send_result.call_args[0][1]
    assert result["ha_device_id"] is None


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


@pytest.mark.asyncio
async def test_update_device_sets_power_sensor(fake_hass, mock_device):
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
            "power_sensor_entity_id": "sensor.ac_plug_power",
            "power_off_below_w": 5,
            "power_on_above_w": 10,
        },
    )
    conn.send_result.assert_called_once()
    assert mock_device.power_sensor_entity_id == "sensor.ac_plug_power"
    assert mock_device.power_off_below_w == 5
    assert mock_device.power_on_above_w == 10


@pytest.mark.asyncio
async def test_update_device_power_sensor_rejects_non_sensor_domain(
    fake_hass, mock_device
):
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
            "power_sensor_entity_id": "light.not_a_sensor",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    manager.async_update_device.assert_not_called()
    assert mock_device.power_sensor_entity_id is None


@pytest.mark.asyncio
async def test_update_device_power_sensor_rejects_bad_threshold_order(
    fake_hass, mock_device
):
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
            "power_sensor_entity_id": "sensor.ac_plug_power",
            "power_off_below_w": 10,
            "power_on_above_w": 5,
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    manager.async_update_device.assert_not_called()
    assert mock_device.power_sensor_entity_id is None


@pytest.mark.asyncio
async def test_update_device_clearing_sensor_clears_thresholds(
    fake_hass, mock_device
):
    mock_device.power_sensor_entity_id = "sensor.ac_plug_power"
    mock_device.power_off_below_w = 5
    mock_device.power_on_above_w = 10
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
            "power_sensor_entity_id": None,
        },
    )
    conn.send_result.assert_called_once()
    assert mock_device.power_sensor_entity_id is None
    assert mock_device.power_off_below_w is None
    assert mock_device.power_on_above_w is None


@pytest.mark.asyncio
async def test_update_device_sets_climate_sensors(fake_hass, mock_device):
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
            "temperature_sensor_entity_id": "sensor.living_room_temp",
            "humidity_sensor_entity_id": "sensor.living_room_humidity",
        },
    )
    conn.send_result.assert_called_once()
    assert (
        mock_device.temperature_sensor_entity_id
        == "sensor.living_room_temp"
    )
    assert (
        mock_device.humidity_sensor_entity_id
        == "sensor.living_room_humidity"
    )


@pytest.mark.asyncio
async def test_update_device_climate_sensor_rejects_non_sensor_domain(
    fake_hass, mock_device
):
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
            "temperature_sensor_entity_id": "climate.not_a_sensor",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    manager.async_update_device.assert_not_called()
    assert mock_device.temperature_sensor_entity_id is None


@pytest.mark.asyncio
async def test_update_device_climate_sensors_are_independent(
    fake_hass, mock_device
):
    # Unlike the power trio, setting one climate sensor must not touch
    # the other -- no coupled clearing.
    mock_device.temperature_sensor_entity_id = "sensor.living_room_temp"
    mock_device.humidity_sensor_entity_id = "sensor.living_room_humidity"
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
            "temperature_sensor_entity_id": None,
        },
    )
    conn.send_result.assert_called_once()
    assert mock_device.temperature_sensor_entity_id is None
    assert (
        mock_device.humidity_sensor_entity_id
        == "sensor.living_room_humidity"
    )


@pytest.mark.asyncio
async def test_update_device_climate_sensors_leave_power_untouched(
    fake_hass, mock_device
):
    mock_device.power_sensor_entity_id = "sensor.ac_plug_power"
    mock_device.power_off_below_w = 5
    mock_device.power_on_above_w = 10
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
            "temperature_sensor_entity_id": "sensor.living_room_temp",
        },
    )
    conn.send_result.assert_called_once()
    assert mock_device.temperature_sensor_entity_id == "sensor.living_room_temp"
    assert mock_device.power_sensor_entity_id == "sensor.ac_plug_power"
    assert mock_device.power_off_below_w == 5
    assert mock_device.power_on_above_w == 10


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
    # Nothing echoed back through a mocked manager, so heard is false
    # after the wait. A send nothing hears is still a send: heard is a
    # bonus fact the TEST button reads, never a condition on success.
    conn.send_result.assert_called_once_with(
        6, {"sent": True, "heard": False, "receiver": None}
    )


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
    # The delete path now asks whether the row is a lattice porthole.
    manager.get_device = MagicMock(return_value=None)
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
    manager.get_device = MagicMock(return_value=None)
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
async def test_get_receivers_uses_device_name_not_friendly_name(fake_hass):
    """Owner bench catch 2026-08-14: the receiver picker was showing
    HA's auto-composed "<device> <entity>" friendly_name instead of
    just the device's own name."""
    entity_id = "infrared.anthem_receiver"
    fake_hass.states.get = MagicMock(
        return_value=MagicMock(
            attributes={
                "friendly_name": "Anthem RF IR remote 1 IR Proxy Receiver"
            }
        )
    )
    entity_entry = MagicMock(device_id="dev1")
    # MagicMock's own constructor reserves the ``name`` kwarg for its
    # internal repr name, not an attribute -- must be set after
    # construction to actually stick as device_entry.name.
    device_entry = MagicMock(name_by_user=None)
    device_entry.name = "Anthem RF IR remote 1"
    entity_registry = MagicMock()
    entity_registry.async_get = MagicMock(return_value=entity_entry)
    device_registry = MagicMock()
    device_registry.async_get = MagicMock(return_value=device_entry)

    conn = _make_connection()
    with patch(
        "homeassistant.components.infrared.async_get_receivers",
        return_value=[entity_id],
        create=True,
    ), patch(
        "custom_components.hair.receiver_filter.er.async_get",
        return_value=MagicMock(async_get=MagicMock(return_value=None)),
    ), patch(
        "custom_components.hair.websocket_api.er.async_get",
        return_value=entity_registry,
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=device_registry,
    ):
        await ws_get_receivers(
            fake_hass, conn, {"id": 12, "type": "hair/receivers"}
        )

    conn.send_result.assert_called_once_with(
        12,
        [{"entity_id": entity_id, "name": "Anthem RF IR remote 1"}],
    )


@pytest.mark.asyncio
async def test_get_receivers_falls_back_to_friendly_name_without_device(
    fake_hass,
):
    """No entity-registry entry (or no linked device) -- falls back to
    the old friendly_name behavior rather than dropping the receiver."""
    entity_id = "infrared.unregistered_receiver"
    fake_hass.states.get = MagicMock(
        return_value=MagicMock(attributes={"friendly_name": "Some Receiver"})
    )
    entity_registry = MagicMock()
    entity_registry.async_get = MagicMock(return_value=None)

    conn = _make_connection()
    with patch(
        "homeassistant.components.infrared.async_get_receivers",
        return_value=[entity_id],
        create=True,
    ), patch(
        "custom_components.hair.receiver_filter.er.async_get",
        return_value=MagicMock(async_get=MagicMock(return_value=None)),
    ), patch(
        "custom_components.hair.websocket_api.er.async_get",
        return_value=entity_registry,
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=MagicMock(),
    ):
        await ws_get_receivers(
            fake_hass, conn, {"id": 13, "type": "hair/receivers"}
        )

    conn.send_result.assert_called_once_with(
        13,
        [{"entity_id": entity_id, "name": "Some Receiver"}],
    )


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
    monitor.import_manual_remote.assert_awaited_once_with(
        "LG TV", entries, merge_existing=False, source_wig=None
    )
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
    manager.async_add_command = AsyncMock(
        side_effect=lambda did, cmd, placement="append": cmd
    )
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
    manager.async_add_command = AsyncMock(
        side_effect=lambda did, cmd, placement="append": cmd
    )
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
    # The handler now auto-maps the new command and persists before creating
    # entities -- async_save is awaited.
    manager._store.async_save = AsyncMock()
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


# An off-standard (~41.9 kHz) Pronto: carrier word 0063, two burst pairs.
_OFF_STANDARD_PRONTO = "0000 0063 0002 0000 0010 0010 0010 0010"


@pytest.mark.asyncio
async def test_snap_preview_valid(fake_hass):
    """Snap an off-standard code to a standard carrier (no save)."""
    conn = _make_connection()
    await ws_unknown_signal_snap_preview(
        fake_hass, conn,
        {"id": 210, "type": "hair/unknown/signal/snap-preview",
         "pronto": _OFF_STANDARD_PRONTO, "target_frequency": 40000},
    )
    conn.send_result.assert_called_once()
    payload = conn.send_result.call_args[0][1]
    assert payload["frequency_khz"] == 40.0
    # The carrier word should have moved off the off-standard source value.
    assert payload["pronto"].split()[1] != _OFF_STANDARD_PRONTO.split()[1]


@pytest.mark.asyncio
async def test_snap_preview_invalid_pronto(fake_hass):
    conn = _make_connection()
    await ws_unknown_signal_snap_preview(
        fake_hass, conn,
        {"id": 211, "type": "hair/unknown/signal/snap-preview",
         "pronto": "0100 zz", "target_frequency": 40000},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_pronto"


@pytest.mark.asyncio
async def test_snap_preview_non_standard_target(fake_hass):
    conn = _make_connection()
    await ws_unknown_signal_snap_preview(
        fake_hass, conn,
        {"id": 212, "type": "hair/unknown/signal/snap-preview",
         "pronto": _OFF_STANDARD_PRONTO, "target_frequency": 41000},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_target"


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


# ---------------------------------------------------------------------------
# ws_get_triggers / ws_reorder_triggers / trigger drawer (Trigger Remotes
# signpost 1, Track B)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_triggers_uses_ordered(fake_hass):
    """The drawer's row list renders in persisted order, not dict order."""
    store = _wire_triggers(fake_hass)
    trig = MagicMock()
    trig.to_dict.return_value = {"id": "t1", "name": "Power"}
    store.get_all_triggers_ordered = MagicMock(return_value=[trig])
    store.get_all_triggers = MagicMock(
        side_effect=AssertionError("should call the ordered variant")
    )

    conn = _make_connection()
    await ws_get_triggers(fake_hass, conn, {"id": 1, "type": "hair/triggers"})

    store.get_all_triggers_ordered.assert_called_once()
    conn.send_result.assert_called_once_with(1, [{"id": "t1", "name": "Power"}])


@pytest.mark.asyncio
async def test_reorder_triggers_success(fake_hass):
    store = _wire_triggers(fake_hass)
    store.reorder_triggers = MagicMock()

    conn = _make_connection()
    await ws_reorder_triggers(
        fake_hass, conn,
        {"id": 400, "type": "hair/trigger/reorder", "trigger_ids": ["b", "a"]},
    )
    store.reorder_triggers.assert_called_once_with(["b", "a"])
    store.async_save.assert_awaited_once()
    conn.send_result.assert_called_once_with(400, {"reordered": True})


@pytest.mark.asyncio
async def test_reorder_triggers_invalid_format(fake_hass):
    store = _wire_triggers(fake_hass)
    store.reorder_triggers = MagicMock(
        side_effect=ValueError("Reorder list does not match current triggers")
    )

    conn = _make_connection()
    await ws_reorder_triggers(
        fake_hass, conn,
        {"id": 401, "type": "hair/trigger/reorder", "trigger_ids": ["ghost"]},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    store.async_save.assert_not_awaited()


@pytest.mark.asyncio
async def test_reorder_triggers_not_configured(fake_hass):
    conn = _make_connection()
    await ws_reorder_triggers(
        fake_hass, conn,
        {"id": 402, "type": "hair/trigger/reorder", "trigger_ids": []},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_configured"


@pytest.mark.asyncio
async def test_get_trigger_drawer_no_registry_entry(fake_hass):
    """Empty state: no device registered until the first trigger lands."""
    store = _wire_triggers(fake_hass)
    store.get_trigger_drawer_name = MagicMock(return_value="HAIR Triggers")

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_get_trigger_drawer(
            fake_hass, conn, {"id": 500, "type": "hair/trigger-drawer"},
        )
    conn.send_result.assert_called_once_with(
        500, {"name": "HAIR Triggers", "ha_device_id": None},
    )


@pytest.mark.asyncio
async def test_get_trigger_drawer_with_registry_entry(fake_hass):
    store = _wire_triggers(fake_hass)
    store.get_trigger_drawer_name = MagicMock(return_value="Living Room Remotes")

    conn = _make_connection()
    with _mock_device_registry("ha-dev-99"):
        await ws_get_trigger_drawer(
            fake_hass, conn, {"id": 501, "type": "hair/trigger-drawer"},
        )
    conn.send_result.assert_called_once_with(
        501, {"name": "Living Room Remotes", "ha_device_id": "ha-dev-99"},
    )


@pytest.mark.asyncio
async def test_rename_trigger_drawer_success(fake_hass):
    store = _wire_triggers(fake_hass)
    store.set_trigger_drawer_name = MagicMock()

    conn = _make_connection()
    with _mock_device_registry(None), patch(
        "custom_components.hair.event.resync_drawer_name"
    ) as resync:
        await ws_rename_trigger_drawer(
            fake_hass, conn,
            {"id": 502, "type": "hair/trigger-drawer/rename", "name": "Den Remotes"},
        )
    store.set_trigger_drawer_name.assert_called_once_with("Den Remotes")
    store.async_save.assert_awaited_once()
    resync.assert_called_once_with(fake_hass, "entry-1", "Den Remotes")
    conn.send_result.assert_called_once_with(
        502, {"name": "Den Remotes", "ha_device_id": None},
    )


@pytest.mark.asyncio
async def test_rename_trigger_drawer_updates_registry_entry(fake_hass):
    """When the drawer already has a live HA device, the rename must also
    reach the registry directly -- device_info alone only syncs at entity
    ADD time, not on every state write."""
    _wire_triggers(fake_hass)

    conn = _make_connection()
    registry = MagicMock()
    ha_device = MagicMock(id="ha-dev-7")
    registry.async_get_device.return_value = ha_device
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch("custom_components.hair.event.resync_drawer_name"):
        await ws_rename_trigger_drawer(
            fake_hass, conn,
            {"id": 503, "type": "hair/trigger-drawer/rename", "name": "New Name"},
        )
    registry.async_update_device.assert_called_once_with(
        "ha-dev-7", name="New Name",
    )
    conn.send_result.assert_called_once_with(
        503, {"name": "New Name", "ha_device_id": "ha-dev-7"},
    )


@pytest.mark.asyncio
async def test_rename_trigger_drawer_rejects_blank_name(fake_hass):
    store = _wire_triggers(fake_hass)
    store.set_trigger_drawer_name = MagicMock()

    conn = _make_connection()
    await ws_rename_trigger_drawer(
        fake_hass, conn,
        {"id": 504, "type": "hair/trigger-drawer/rename", "name": "   "},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    store.set_trigger_drawer_name.assert_not_called()


@pytest.mark.asyncio
async def test_create_trigger_remote_registers_ha_device_eagerly(fake_hass):
    """Signpost 3, Track 2 item 1 (brief 7b): creating a named remote
    must register its HA device immediately, not wait for a first
    trigger -- a brand new, still-empty remote gets a real device id
    back in the same response."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()

    ha_device = MagicMock(id="ha-dev-new-1")
    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=ha_device)

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_create_trigger_remote(
            fake_hass, conn,
            {"id": 600, "type": "hair/trigger-remote/create", "name": "Bedroom Remote"},
        )

    store.add_trigger_remote.assert_called_once()
    created = store.add_trigger_remote.call_args[0][0]
    assert isinstance(created, TriggerRemote)
    assert created.name == "Bedroom Remote"

    registry.async_get_or_create.assert_called_once_with(
        config_entry_id="entry-1",
        identifiers={(DOMAIN, created.id)},
        name="Bedroom Remote",
        manufacturer="HAIR",
        model="IR Triggers",
    )
    store.async_save.assert_awaited_once()
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["ha_device_id"] == "ha-dev-new-1"
    assert result["trigger_count"] == 0


@pytest.mark.asyncio
async def test_create_trigger_remote_rejects_blank_name(fake_hass):
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()

    conn = _make_connection()
    await ws_create_trigger_remote(
        fake_hass, conn,
        {"id": 601, "type": "hair/trigger-remote/create", "name": "   "},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"
    store.add_trigger_remote.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_registers_ha_device_eagerly_when_empty(
    fake_hass,
):
    """A duplicate of a currently-empty remote used to return
    ha_device_id: None forever -- no trigger ever copies over to
    register one the old lazy way. Eager registration fixes that the
    same way create does."""
    store = _wire_triggers(fake_hass)
    source = TriggerRemote(id="src-1", name="Source Remote")
    store.get_trigger_remote = MagicMock(return_value=source)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    store.add_trigger_remote = MagicMock()

    ha_device = MagicMock(id="ha-dev-clone-1")
    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=ha_device)

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_duplicate_trigger_remote(
            fake_hass, conn,
            {
                "id": 602,
                "type": "hair/trigger-remote/duplicate",
                "remote_id": "src-1",
                "new_name": "Source Remote copy",
            },
        )

    store.add_trigger_remote.assert_called_once()
    clone = store.add_trigger_remote.call_args[0][0]
    registry.async_get_or_create.assert_called_once_with(
        config_entry_id="entry-1",
        identifiers={(DOMAIN, clone.id)},
        name="Source Remote copy",
        manufacturer="HAIR",
        model="IR Triggers",
    )
    conn.send_result.assert_called_once()
    result = conn.send_result.call_args[0][1]
    assert result["ha_device_id"] == "ha-dev-clone-1"
    assert result["trigger_count"] == 0


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=None)

    conn = _make_connection()
    await ws_duplicate_trigger_remote(
        fake_hass, conn,
        {
            "id": 603,
            "type": "hair/trigger-remote/duplicate",
            "remote_id": "ghost",
            "new_name": "Copy",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_inherits_scope_when_omitted(fake_hass):
    """Signpost 3, Track 2 item 6: stored semantics unchanged when the
    footer picker's field is omitted entirely -- the clone still
    inherits the source's receiver_scope exactly as before item 6."""
    store = _wire_triggers(fake_hass)
    source = TriggerRemote(
        id="src-1", name="Source Remote",
        receiver_scope=["infrared.living_room"],
    )
    store.get_trigger_remote = MagicMock(return_value=source)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    store.add_trigger_remote = MagicMock()

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-1")
    )
    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_duplicate_trigger_remote(
            fake_hass, conn,
            {
                "id": 610, "type": "hair/trigger-remote/duplicate",
                "remote_id": "src-1", "new_name": "Copy",
            },
        )
    clone = store.add_trigger_remote.call_args[0][0]
    assert clone.receiver_scope == ["infrared.living_room"]


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_scope_override(fake_hass):
    """The footer picker's override: an explicit (possibly empty)
    receiver_scope replaces the inherited one."""
    store = _wire_triggers(fake_hass)
    source = TriggerRemote(
        id="src-1", name="Source Remote",
        receiver_scope=["infrared.living_room"],
    )
    store.get_trigger_remote = MagicMock(return_value=source)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    store.add_trigger_remote = MagicMock()

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-1")
    )
    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_duplicate_trigger_remote(
            fake_hass, conn,
            {
                "id": 611, "type": "hair/trigger-remote/duplicate",
                "remote_id": "src-1", "new_name": "Copy",
                "receiver_scope": ["infrared.bedroom", "infrared.den"],
            },
        )
    clone = store.add_trigger_remote.call_args[0][0]
    assert clone.receiver_scope == ["infrared.bedroom", "infrared.den"]


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_scope_override_can_clear(fake_hass):
    """An explicit empty list is a real override (unscoped), not
    "no opinion" -- distinct from omitting the field entirely."""
    store = _wire_triggers(fake_hass)
    source = TriggerRemote(
        id="src-1", name="Source Remote",
        receiver_scope=["infrared.living_room"],
    )
    store.get_trigger_remote = MagicMock(return_value=source)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    store.add_trigger_remote = MagicMock()

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-1")
    )
    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_duplicate_trigger_remote(
            fake_hass, conn,
            {
                "id": 612, "type": "hair/trigger-remote/duplicate",
                "remote_id": "src-1", "new_name": "Copy",
                "receiver_scope": [],
            },
        )
    clone = store.add_trigger_remote.call_args[0][0]
    assert clone.receiver_scope == []


def _manager_for_device_creation():
    """The manager-mocking shape ws_trigger_remote_make_device's
    create-empty-then-fill path needs -- same three methods
    test_adopt_comb_suspects.py's own _manager() helper mocks for
    ws_wig_make_device, since both commands share that shape."""
    manager = MagicMock()
    manager.async_create_device = AsyncMock()
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    return manager


def _wire_triggers_with_monitor(hass):
    """_wire_triggers plus a signal_monitor mock, the shape
    ws_create_trigger_remote's promoted_from_unknown_id path reads."""
    store = _wire_triggers(hass)
    monitor = MagicMock()
    monitor.copy_signals_to_trigger_remote = AsyncMock()
    monitor.mark_promoted_remote = AsyncMock()
    hass.data[DOMAIN]["entry-1"]["signal_monitor"] = monitor
    return store, monitor


@pytest.mark.asyncio
async def test_create_trigger_remote_from_promoted_source(fake_hass):
    """Signpost 3, Track 2 item 2: the USE-as-a-Remote fork's Sniffer/
    Clipper/Plucker tabs pass promoted_from_unknown_id -- every signal
    on the source becomes a named trigger, the catalog remote is
    stamped with the link, origin defaults to "remote" when the
    caller omits it."""
    store, monitor = _wire_triggers_with_monitor(fake_hass)
    store.add_trigger_remote = MagicMock()

    trig1 = MagicMock(id="t1")
    trig2 = MagicMock(id="t2")
    monitor.copy_signals_to_trigger_remote.return_value = {
        "success": True, "triggers": [trig1, trig2],
    }

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-promoted-1")
    )

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ) as sync_entities:
        await ws_create_trigger_remote(
            fake_hass, conn,
            {
                "id": 700,
                "type": "hair/trigger-remote/create",
                "name": "Samsung TV",
                "promoted_from_unknown_id": "unk-1",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.origin == "remote"
    monitor.copy_signals_to_trigger_remote.assert_awaited_once_with(
        "unk-1", created.id
    )
    monitor.mark_promoted_remote.assert_awaited_once_with(
        "unk-1", created.id
    )
    assert sync_entities.call_count == 2
    result = conn.send_result.call_args[0][1]
    assert result["trigger_count"] == 2
    assert result["ha_device_id"] == "ha-dev-promoted-1"


@pytest.mark.asyncio
async def test_wig_make_remote_requires_source(fake_hass):
    _wire_triggers(fake_hass)
    conn = _make_connection()
    await ws_wig_make_remote(
        fake_hass, conn,
        {"id": 701, "type": "hair/wigs/make-remote", "name": "Living Room AC"},
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_wig_make_remote_rejects_blank_name(fake_hass):
    _wire_triggers(fake_hass)
    conn = _make_connection()
    await ws_wig_make_remote(
        fake_hass, conn,
        {
            "id": 702, "type": "hair/wigs/make-remote", "name": "   ",
            "filename": "living-room-ac.hairwig",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_wig_make_remote_wig_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()

    conn = _make_connection()
    with patch(
        "custom_components.hair.wig_store.load_wig", return_value=None
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 703, "type": "hair/wigs/make-remote", "name": "Living Room AC",
                "filename": "ghost.hairwig",
            },
        )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"
    store.add_trigger_remote.assert_not_called()


@pytest.mark.asyncio
async def test_wig_make_remote_happy_path(fake_hass):
    """A closet wig mints a Remote with one trigger per signal whose
    Pronto validates; origin "closet"."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    wig_signal_ok = MagicMock(alias="Power")
    wig_signal_bad = MagicMock(alias="Glitch")
    # climate=None says this is a FLAT wig: as of signpost 4 Track M
    # the make-remote door copies wig.climate when there is one, so a
    # bare MagicMock would read as a matrix wig.
    wig = MagicMock(signals=[wig_signal_ok, wig_signal_bad], climate=None)

    ident_ok = MagicMock(
        fingerprint="S1L2", pronto="0000 006D 0001 0000 00E0 0070",
        byte_hash="bh1", decoded_fingerprint="df1",
    )

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-wig-1")
    )

    conn = _make_connection()
    with patch(
        "custom_components.hair.wig_store.load_wig", return_value=wig
    ), patch(
        "custom_components.hair.wig_identity.wig_signal_identities",
        return_value=[ident_ok, None],
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 704, "type": "hair/wigs/make-remote", "name": "Living Room AC",
                "filename": "living-room-ac.hairwig",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.origin == "closet"
    store.add_trigger.assert_called_once()
    trigger = store.add_trigger.call_args[0][0]
    assert trigger.name == "Power"
    assert trigger.signal_fingerprint == "S1L2"
    assert trigger.origin == "closet"
    assert trigger.trigger_remote_id == created.id
    result = conn.send_result.call_args[0][1]
    assert result["trigger_count"] == 1
    assert result["ha_device_id"] == "ha-dev-wig-1"


@pytest.mark.asyncio
async def test_wig_make_remote_backfills_source_wig_id(fake_hass):
    """Signpost 3, Track 2 item 4: the filename door stamps the
    remote-side twin of IRDevice.source_wig_id, so the combined
    linked-count dot can chip a matrix wig's remote by pointer even
    when it has no flat signals to identity-match with. The codebook
    door (no filename) must leave it None -- a transient wig was never
    in the closet and has nothing to inherit."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    wig = MagicMock(signals=[], climate=None)
    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-wig-2")
    )

    conn = _make_connection()
    with patch(
        "custom_components.hair.wig_store.load_wig", return_value=wig
    ), patch(
        "custom_components.hair.wig_identity.wig_signal_identities",
        return_value=[],
    ), patch(
        "custom_components.hair.wig_store.backfill_wig_id",
        return_value="wig-42",
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 705, "type": "hair/wigs/make-remote", "name": "AC",
                "filename": "ac.hairwig",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.source_wig_id == "wig-42"


@pytest.mark.asyncio
async def test_wig_make_remote_codebook_door_leaves_source_wig_id_none(
    fake_hass,
):
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    wig = MagicMock(signals=[], climate=None)
    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-wig-3")
    )

    conn = _make_connection()
    with patch(
        "custom_components.hair.code_library.build_wig_from_codebook",
        return_value=wig,
    ), patch(
        "custom_components.hair.wig_identity.wig_signal_identities",
        return_value=[],
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 706, "type": "hair/wigs/make-remote", "name": "AC",
                "codebook_id": "brand/ac-1",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.source_wig_id is None


# ---------------------------------------------------------------------------
# Mirror-door mints (signpost 3, Track 3.5, owner-directed 2026-08-15):
# ws_device_make_remote (Device -> Remote) and ws_trigger_remote_make_device
# (Remote -> Device). Same shape as the wig_make_remote suite above --
# not-found / happy-path / matrix-exclusion / origin+source assertions --
# plus test_adopt_comb_suspects.py's manager-mocking pattern for the
# device-creation-path command.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_device_make_remote_rejects_blank_name(fake_hass):
    _wire_triggers(fake_hass)
    conn = _make_connection()
    await ws_device_make_remote(
        fake_hass, conn,
        {
            "id": 801, "type": "hair/device/make-remote", "name": "   ",
            "device_id": "dev-1",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_device_make_remote_device_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"].get_device = MagicMock(
        return_value=None
    )

    conn = _make_connection()
    await ws_device_make_remote(
        fake_hass, conn,
        {
            "id": 802, "type": "hair/device/make-remote", "name": "Living Room",
            "device_id": "ghost",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"
    store.add_trigger_remote.assert_not_called()


@pytest.mark.asyncio
async def test_device_make_remote_happy_path(fake_hass):
    """A live device mints a Remote with one trigger per non-matrix
    command; THE MATRIX RULE skips any command with matrix_cell set
    (a porthole row, not a real discrete press); origin "device"."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    from custom_components.hair.models import IRCommand

    cmd_power = IRCommand(
        name="Power", protocol="NEC", code="0x20DF10EF",
        raw_timings=[9000, -4500, 560, -560],
        byte_hash="bh-power", decoded_fingerprint="df-power",
    )
    cmd_cell = IRCommand(
        name="Cool 24", protocol="NEC", code="0x1", matrix_cell="cool-24",
    )
    device = IRDevice(
        id="dev-live-1", name="Living Room TV",
        device_type=DeviceType.MEDIA_PLAYER,
        commands=[cmd_power, cmd_cell],
    )
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"].get_device = MagicMock(
        return_value=device
    )

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(
        return_value=MagicMock(id="ha-dev-remote-1")
    )

    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_device_make_remote(
            fake_hass, conn,
            {
                "id": 803, "type": "hair/device/make-remote",
                "name": "Living Room TV Remote", "device_id": "dev-live-1",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.origin == "device"
    assert created.source_device_id == "dev-live-1"
    store.add_trigger.assert_called_once()
    trigger = store.add_trigger.call_args[0][0]
    assert trigger.name == "Power"
    assert trigger.origin == "device"
    assert trigger.source_device_id == "dev-live-1"
    assert trigger.source_command_id == cmd_power.id
    assert trigger.trigger_remote_id == created.id
    from custom_components.hair.event_parser import EventParser

    assert trigger.signal_fingerprint == EventParser.signal_fingerprint(
        "NEC", "0x20DF10EF", [9000, -4500, 560, -560]
    )
    result = conn.send_result.call_args[0][1]
    assert result["trigger_count"] == 1
    assert result["ha_device_id"] == "ha-dev-remote-1"


@pytest.mark.asyncio
async def test_trigger_remote_make_device_rejects_bad_device_type(fake_hass):
    _wire_triggers(fake_hass)
    conn = _make_connection()
    await ws_trigger_remote_make_device(
        fake_hass, conn,
        {
            "id": 811, "type": "hair/trigger-remote/make-device",
            "name": "Living Room TV", "remote_id": "rem-1",
            "device_type": "not-a-real-type", "emitter_entity_ids": [],
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_trigger_remote_make_device_remote_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=None)
    manager = _manager_for_device_creation()
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"] = manager

    conn = _make_connection()
    await ws_trigger_remote_make_device(
        fake_hass, conn,
        {
            "id": 812, "type": "hair/trigger-remote/make-device",
            "name": "Living Room TV", "remote_id": "ghost",
            "device_type": "media_player", "emitter_entity_ids": ["infrared.e"],
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"
    manager.async_create_device.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_remote_make_device_happy_path(fake_hass):
    """A named Remote's triggers mint one IRCommand each; raw_timings
    is backfilled from the trigger's Pronto code (IRTrigger never
    stores it itself), and a trigger with no code leaves raw_timings
    None rather than raising. Origin "remote"."""
    remote = TriggerRemote(id="rem-live-1", name="Living Room Remote")
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)

    pronto_house = "0000 006D 0002 0000 0020 0040 0020 0040"
    # MagicMock(name=...) sets the mock's own repr name, not a `.name`
    # attribute -- set that separately on each, matching the pattern
    # test_wig_make_remote_happy_path already uses for wig_signal_ok.
    trig_power = MagicMock(
        protocol="PRONTO", code=pronto_house,
        byte_hash="bh1", decoded_fingerprint="df1",
    )
    trig_power.name = "Power"
    trig_blank = MagicMock(
        protocol="PRONTO", code=None, byte_hash=None, decoded_fingerprint=None,
    )
    trig_blank.name = ""
    store.get_triggers_for_remote = MagicMock(
        return_value=[trig_power, trig_blank]
    )

    manager = _manager_for_device_creation()
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"] = manager

    conn = _make_connection()
    await ws_trigger_remote_make_device(
        fake_hass, conn,
        {
            "id": 813, "type": "hair/trigger-remote/make-device",
            "name": "Living Room TV", "remote_id": "rem-live-1",
            "device_type": "media_player", "emitter_entity_ids": ["infrared.e"],
        },
    )

    manager.async_create_device.assert_awaited_once()
    device = manager.async_create_device.call_args[0][0]
    assert device.origin == "remote"
    assert device.source_remote_id == "rem-live-1"
    assert [c.name for c in device.commands] == ["Power", "Trigger 2"]
    assert device.commands[0].raw_timings  # backfilled, non-empty
    assert device.commands[1].raw_timings is None  # no code, no backfill
    assert manager._auto_map_command.call_count == 2
    manager.async_update_device.assert_awaited_once_with(device)
    conn.send_error.assert_not_called()
    result = conn.send_result.call_args[0][1]
    assert result["copied"] == 2


@pytest.mark.asyncio
async def test_trigger_remote_make_device_tolerates_bad_pronto_code(fake_hass):
    """A malformed code must not blow up the whole mint -- the
    ProntoCommand(...).get_raw_timings() backfill is try/except-
    wrapped, same tolerance DeviceManager.async_update_command's own
    Pronto-edit path has for a bad code; the command just will not TX
    until a later edit fixes it."""
    remote = TriggerRemote(id="rem-live-2", name="Odd Remote")
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)

    trig_bad = MagicMock(
        protocol="PRONTO", code="not a pronto code",
        byte_hash=None, decoded_fingerprint=None,
    )
    trig_bad.name = "Weird"
    store.get_triggers_for_remote = MagicMock(return_value=[trig_bad])

    manager = _manager_for_device_creation()
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"] = manager

    conn = _make_connection()
    await ws_trigger_remote_make_device(
        fake_hass, conn,
        {
            "id": 814, "type": "hair/trigger-remote/make-device",
            "name": "Odd Device", "remote_id": "rem-live-2",
            "device_type": "media_player", "emitter_entity_ids": ["infrared.e"],
        },
    )

    conn.send_error.assert_not_called()
    device = manager.async_create_device.call_args[0][0]
    assert device.commands[0].raw_timings is None
    result = conn.send_result.call_args[0][1]
    assert result["copied"] == 1


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


class TestLinkedHairDevices:
    """The v0.7.0 identity-based promote linkage (promote-rename fix)."""

    def _remote(self, **kw):
        from custom_components.hair.models import UnknownDevice

        return UnknownDevice(label="Remote 1", source="sniffed", **kw)

    def test_promoted_to_resolves_live_name(self):
        from custom_components.hair.websocket_api import _linked_hair_devices

        target = MagicMock()
        target.id = "hd1"
        target.name = "Renamed Later"
        remote = self._remote(promoted_to="hd1")
        linked = _linked_hair_devices(remote, [], {"hd1": target})
        assert linked == [
            {"device_id": "hd1", "device_name": "Renamed Later"}
        ]

    def test_deleted_target_drops_out(self):
        from custom_components.hair.websocket_api import _linked_hair_devices

        remote = self._remote(promoted_to="gone")
        assert _linked_hair_devices(remote, [], {}) == []

    def test_assignment_targets_union_and_dedupe(self):
        from custom_components.hair.identity import SignalIdentity
        from custom_components.hair.models import UnknownSignal
        from custom_components.hair.websocket_api import _linked_hair_devices

        target = MagicMock()
        target.id = "hd1"
        target.name = "TV"
        remote = self._remote(promoted_to="hd1")
        remote.signals.append(UnknownSignal(fingerprint="S1L2"))
        index = [
            (
                SignalIdentity(None, None, "S1L2"),
                {
                    "device_id": "hd2",
                    "device_name": "Soundbar",
                    "command_id": "c",
                    "command_name": "Vol Up",
                },
            ),
            (
                SignalIdentity(None, None, "S1L2"),
                {
                    "device_id": "hd1",
                    "device_name": "TV (stale name ok)",
                    "command_id": "c2",
                    "command_name": "Power",
                },
            ),
        ]
        linked = _linked_hair_devices(remote, index, {"hd1": target})
        ids = {entry["device_id"] for entry in linked}
        assert ids == {"hd1", "hd2"}


class TestLinkedHairRemotes:
    """Signpost 3, Track 2 item 4 (item 0.1): the remote-side sibling
    of TestLinkedHairDevices -- same union shape (stored promote link
    plus identity match), trigger-remote side."""

    def _remote(self, **kw):
        from custom_components.hair.models import UnknownDevice

        return UnknownDevice(label="Remote 1", source="sniffed", **kw)

    def test_promoted_to_remote_resolves_live_name(self):
        from custom_components.hair.websocket_api import _linked_hair_remotes

        target = MagicMock()
        target.id = "tr1"
        target.name = "Renamed Later"
        remote = self._remote(promoted_to_remote="tr1")
        linked = _linked_hair_remotes(remote, [], {"tr1": target})
        assert linked == [
            {"remote_id": "tr1", "remote_name": "Renamed Later"}
        ]

    def test_deleted_target_drops_out(self):
        from custom_components.hair.websocket_api import _linked_hair_remotes

        remote = self._remote(promoted_to_remote="gone")
        assert _linked_hair_remotes(remote, [], {}) == []

    def test_assignment_targets_union_and_dedupe(self):
        from custom_components.hair.identity import SignalIdentity
        from custom_components.hair.models import UnknownSignal
        from custom_components.hair.websocket_api import _linked_hair_remotes

        target = MagicMock()
        target.id = "tr1"
        target.name = "Living Room Remote"
        remote = self._remote(promoted_to_remote="tr1")
        remote.signals.append(UnknownSignal(fingerprint="S1L2"))
        index = [
            (
                SignalIdentity(None, None, "S1L2"),
                {"remote_id": "tr2", "remote_name": "Bedroom Remote"},
            ),
            (
                SignalIdentity(None, None, "S1L2"),
                {"remote_id": "tr1", "remote_name": "Living Room (stale ok)"},
            ),
        ]
        linked = _linked_hair_remotes(remote, index, {"tr1": target})
        ids = {entry["remote_id"] for entry in linked}
        assert ids == {"tr1", "tr2"}


class TestTriggerAssignmentIndex:
    """_trigger_assignment_index: IRTrigger already stores its own
    identity fields, so this is a plain filter + lookup, not a
    recompute like _assignment_index needs for IRCommand."""

    def test_drawer_owned_triggers_excluded(self):
        from custom_components.hair.websocket_api import (
            _trigger_assignment_index,
        )

        trig = IRTrigger(
            id="t1", trigger_remote_id=None, signal_fingerprint="S1L2",
        )
        assert _trigger_assignment_index([trig], {}) == []

    def test_unresolvable_remote_id_excluded(self):
        from custom_components.hair.websocket_api import (
            _trigger_assignment_index,
        )

        trig = IRTrigger(
            id="t1", trigger_remote_id="ghost", signal_fingerprint="S1L2",
        )
        assert _trigger_assignment_index([trig], {}) == []

    def test_resolved_trigger_yields_one_entry(self):
        from custom_components.hair.identity import SignalIdentity
        from custom_components.hair.websocket_api import (
            _trigger_assignment_index,
        )

        remote = TriggerRemote(id="tr1", name="Living Room Remote")
        trig = IRTrigger(
            id="t1", trigger_remote_id="tr1", signal_fingerprint="S1L2",
            byte_hash="bh1", decoded_fingerprint="df1",
        )
        entries = _trigger_assignment_index([trig], {"tr1": remote})
        assert entries == [
            (
                SignalIdentity("df1", "bh1", "S1L2"),
                {"remote_id": "tr1", "remote_name": "Living Room Remote"},
            )
        ]


@pytest.mark.asyncio
async def test_get_unknown_devices_combined_linked_count(fake_hass):
    """Signpost 3, Track 2 item 4 (item 0.1): the USE dot's
    linked_devices payload unions minted devices AND named Remotes,
    each row kind-tagged -- ONE list, no per-kind split for the UI to
    un-merge (owner ruling, coding-plan.md section 0 item 1)."""
    monitor = _make_signal_monitor(fake_hass)
    store = MagicMock()
    hair_device = MagicMock(id="hd1", name="Living Room TV", commands=[])
    store.get_all_devices = MagicMock(return_value=[hair_device])
    remote = TriggerRemote(id="tr1", name="Living Room Remote")
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.get_all_triggers = MagicMock(return_value=[])
    fake_hass.data[DOMAIN] = {
        "entry-1": {
            "device_manager": MagicMock(),
            "signal_monitor": monitor,
            "store": store,
        }
    }
    d = UnknownDevice(
        id="d1", fingerprint="fp1", hit_count=5,
        promoted_to="hd1", promoted_to_remote="tr1",
    )
    monitor._signal_store.add_device(d)

    conn = _make_connection()
    await ws_get_unknown_devices(
        fake_hass, conn,
        {"id": 710, "type": "hair/unknown/devices", "min_hits": 0},
    )
    result = conn.send_result.call_args[0][1]
    linked = result[0]["linked_devices"]
    seen = {
        (entry["kind"], entry.get("device_id") or entry.get("remote_id"))
        for entry in linked
    }
    assert seen == {("device", "hd1"), ("remote", "tr1")}


# Signpost 3, Track 2 item 4b (item 0.6): the s11 Remote-card ON:/OFF:
# badges render from this one list call, no per-remote follow-up --
# trigger_count stays as-is, enabled_count/disabled_count are new and
# always sum back to it.


@pytest.mark.asyncio
async def test_list_trigger_remotes_mixed_enabled_states(fake_hass):
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Living Room Remote")
    triggers = [
        IRTrigger(id="t1", trigger_remote_id="tr1", enabled=True),
        IRTrigger(id="t2", trigger_remote_id="tr1", enabled=True),
        IRTrigger(id="t3", trigger_remote_id="tr1", enabled=False),
    ]
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.get_triggers_for_remote = MagicMock(return_value=triggers)

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_list_trigger_remotes(
            fake_hass, conn, {"id": 720, "type": "hair/trigger-remotes"},
        )
    result = conn.send_result.call_args[0][1]
    assert len(result) == 1
    row = result[0]
    assert row["trigger_count"] == 3
    assert row["enabled_count"] == 2
    assert row["disabled_count"] == 1


@pytest.mark.asyncio
async def test_list_trigger_remotes_all_triggers_off(fake_hass):
    """The bench gate's own wording (coding-plan.md section 5): "one
    with all triggers off"."""
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Idle Remote")
    triggers = [
        IRTrigger(id="t1", trigger_remote_id="tr1", enabled=False),
        IRTrigger(id="t2", trigger_remote_id="tr1", enabled=False),
    ]
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.get_triggers_for_remote = MagicMock(return_value=triggers)

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_list_trigger_remotes(
            fake_hass, conn, {"id": 721, "type": "hair/trigger-remotes"},
        )
    row = conn.send_result.call_args[0][1][0]
    assert row["trigger_count"] == 2
    assert row["enabled_count"] == 0
    assert row["disabled_count"] == 2


@pytest.mark.asyncio
async def test_list_trigger_remotes_zero_triggers(fake_hass):
    """Item 0.6's own note (mockup-s11.html): the badge row is always
    present, even at zero -- so a freshly minted, empty remote must
    still carry 0/0, not omit the fields."""
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Fresh Remote")
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.get_triggers_for_remote = MagicMock(return_value=[])

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_list_trigger_remotes(
            fake_hass, conn, {"id": 722, "type": "hair/trigger-remotes"},
        )
    row = conn.send_result.call_args[0][1][0]
    assert row["trigger_count"] == 0
    assert row["enabled_count"] == 0
    assert row["disabled_count"] == 0


# ---------------------------------------------------------------------------
# ws_pin_trigger_remote_device / ws_unpin_trigger_remote_device
# (signpost 3, Track 2 item 5 / section 0b): storage only, no
# retransmit or derivation -- see TriggerRemote.pinned_device_ids.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pin_device_adds_and_saves(fake_hass):
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Living Room Remote")
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.update_trigger_remote = MagicMock()

    conn = _make_connection()
    await ws_pin_trigger_remote_device(
        fake_hass, conn,
        {
            "id": 730, "type": "hair/trigger-remote/pin",
            "remote_id": "tr1", "device_id": "hd1",
        },
    )
    assert remote.pinned_device_ids == ["hd1"]
    store.update_trigger_remote.assert_called_once_with(remote)
    store.async_save.assert_awaited_once()
    result = conn.send_result.call_args[0][1]
    assert result["pinned_device_ids"] == ["hd1"]


@pytest.mark.asyncio
async def test_pin_device_idempotent(fake_hass):
    """Pinning an already-pinned device is a no-op: no duplicate in
    the list, and no wasted save."""
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Living Room Remote",
                            pinned_device_ids=["hd1"])
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.update_trigger_remote = MagicMock()

    conn = _make_connection()
    await ws_pin_trigger_remote_device(
        fake_hass, conn,
        {
            "id": 731, "type": "hair/trigger-remote/pin",
            "remote_id": "tr1", "device_id": "hd1",
        },
    )
    assert remote.pinned_device_ids == ["hd1"]
    store.update_trigger_remote.assert_not_called()
    store.async_save.assert_not_awaited()


@pytest.mark.asyncio
async def test_pin_device_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=None)

    conn = _make_connection()
    await ws_pin_trigger_remote_device(
        fake_hass, conn,
        {
            "id": 732, "type": "hair/trigger-remote/pin",
            "remote_id": "ghost", "device_id": "hd1",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_unpin_device_removes_and_saves(fake_hass):
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Living Room Remote",
                            pinned_device_ids=["hd1", "hd2"])
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.update_trigger_remote = MagicMock()

    conn = _make_connection()
    await ws_unpin_trigger_remote_device(
        fake_hass, conn,
        {
            "id": 733, "type": "hair/trigger-remote/unpin",
            "remote_id": "tr1", "device_id": "hd1",
        },
    )
    assert remote.pinned_device_ids == ["hd2"]
    store.update_trigger_remote.assert_called_once_with(remote)
    store.async_save.assert_awaited_once()
    result = conn.send_result.call_args[0][1]
    assert result["pinned_device_ids"] == ["hd2"]


@pytest.mark.asyncio
async def test_unpin_device_idempotent_when_not_pinned(fake_hass):
    store = _wire_triggers(fake_hass)
    remote = TriggerRemote(id="tr1", name="Living Room Remote")
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.update_trigger_remote = MagicMock()

    conn = _make_connection()
    await ws_unpin_trigger_remote_device(
        fake_hass, conn,
        {
            "id": 734, "type": "hair/trigger-remote/unpin",
            "remote_id": "tr1", "device_id": "ghost-device",
        },
    )
    assert remote.pinned_device_ids == []
    store.update_trigger_remote.assert_not_called()
    store.async_save.assert_not_awaited()
    result = conn.send_result.call_args[0][1]
    assert result["pinned_device_ids"] == []


@pytest.mark.asyncio
async def test_unpin_device_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=None)

    conn = _make_connection()
    await ws_unpin_trigger_remote_device(
        fake_hass, conn,
        {
            "id": 735, "type": "hair/trigger-remote/unpin",
            "remote_id": "ghost", "device_id": "hd1",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"



# ---------------------------------------------------------------------------
# ws_wigs_upload: closet duplicate receipt
# ---------------------------------------------------------------------------


class TestWigsUploadDuplicateReceipt:
    """The duplicate receipt hashes whole wigs, not flat signal lists
    (owner bench, 2026-07-28): matrix wigs carry empty/near-empty flat
    signals, so hashing only ``wig.signals`` collided EVERY matrix wig
    on the empty-list hash -- dropping a Mitsubishi SmartIR file read
    "an identical device was already in Toyotomi". ``wig_content_hash``
    is cells-aware for matrix wigs and byte-identical to the old
    signals hash for signal wigs."""

    @staticmethod
    def _b64(seed: int) -> str:
        """A minimal valid Broadlink packet, varied by seed."""
        import base64

        payload = bytes([seed, 0x24, 0x12, 0x12, 0x12, 0x24, 0x12,
                         0x12, 0x12, 0x24])
        packet = bytes([0x26, 0x00, len(payload), 0x00]) + payload
        return base64.b64encode(packet).decode()

    def _smartir(self, name: str, seed: int) -> str:
        """A minimal SmartIR climate file: matrix only, no depth-0
        extras, so the converted wig's flat signal list is empty."""
        import json

        return json.dumps({
            "manufacturer": name,
            "supportedModels": [f"{name}-100"],
            "supportedController": "Broadlink",
            "commandsEncoding": "Base64",
            "minTemperature": 16.0,
            "maxTemperature": 30.0,
            "precision": 1,
            "operationModes": ["cool"],
            "fanModes": ["auto"],
            "commands": {
                "off": self._b64(seed),
                "cool": {"auto": {"22": self._b64(seed + 1)}},
            },
        })

    async def _upload(self, fake_hass, text: str) -> dict:
        from custom_components.hair.websocket_api import ws_wigs_upload

        conn = _make_connection()
        await ws_wigs_upload(
            fake_hass, conn,
            {"id": 1, "type": "hair/wigs/upload", "text": text},
        )
        conn.send_result.assert_called_once()
        return conn.send_result.call_args[0][1]

    @pytest.mark.asyncio
    async def test_different_matrix_wigs_do_not_false_match(
        self, fake_hass, tmp_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        first = await self._upload(
            fake_hass, self._smartir("Toyotomi", 0x30)
        )
        assert first["success"] is True
        assert first["files"][0]["duplicate_of"] is None

        second = await self._upload(
            fake_hass, self._smartir("Mitsubishi", 0x60)
        )
        assert second["success"] is True
        assert second["files"][0]["duplicate_of"] is None
        assert second["files"][0]["duplicates"] == []

    @pytest.mark.asyncio
    async def test_identical_matrix_reupload_gets_the_receipt(
        self, fake_hass, tmp_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        text = self._smartir("Toyotomi", 0x30)
        first = await self._upload(fake_hass, text)
        assert first["files"][0]["duplicate_of"] is None

        again = await self._upload(fake_hass, text)
        assert again["success"] is True
        assert again["files"][0]["duplicate_of"] == first["filename"]


# ---------------------------------------------------------------------------
# ws_wigs_upload: reverse-direction import check
# ---------------------------------------------------------------------------


class TestReverseSupersession:
    """Amendment v2 section 3 (owner bench find): ancestry only ever
    points backward, so a re-dropped ORIGINAL, once its successor
    already exists in this closet, would otherwise file as a silent
    twin -- the forward check never looks at it, because the forward
    check asks what the ARRIVAL supersedes, not who supersedes the
    arrival. The reverse lookup catches it before anything touches
    disk: Cancel here means nothing files at all, unlike the forward
    doorway's CANCEL, which deletes an arrival already written.
    """

    @staticmethod
    def _original_text(wig_id: str = "wig-original-id") -> str:
        import json

        from custom_components.hair.wig_format import WIG_FORMAT_V1

        pronto = "0000 006D 0002 0000 0020 0040 0020 0040"
        return json.dumps({
            "format": WIG_FORMAT_V1,
            "name": "Fable Ceiling Fan",
            "wig_id": wig_id,
            "signals": [{"alias": "Power", "pronto": pronto}],
        })

    @staticmethod
    def _write_successor(
        tmp_path, supersedes: list[str], signal_count: int = 3,
        name: str = "Fable Ceiling Fan (2)",
    ) -> None:
        import json

        from custom_components.hair.wig_format import WIG_FORMAT_V1
        from custom_components.hair.wig_store import (
            ensure_wigs_dir,
            wigs_dir,
        )

        pronto = "0000 006D 0002 0000 0020 0040 0020 0040"
        ensure_wigs_dir(tmp_path)
        text = json.dumps({
            "format": WIG_FORMAT_V1,
            "name": name,
            "wig_id": "wig-successor-id",
            "supersedes": supersedes,
            "signals": [
                {"alias": f"Signal {i}", "pronto": pronto}
                for i in range(signal_count)
            ],
        })
        (wigs_dir(tmp_path) / "successor.wig.json").write_text(
            text, encoding="utf-8"
        )

    @staticmethod
    async def _upload(fake_hass, text: str, confirmed: bool = False) -> dict:
        from custom_components.hair.websocket_api import ws_wigs_upload

        conn = _make_connection()
        msg = {"id": 1, "type": "hair/wigs/upload", "text": text}
        if confirmed:
            msg["confirmed"] = True
        await ws_wigs_upload(fake_hass, conn, msg)
        conn.send_result.assert_called_once()
        return conn.send_result.call_args[0][1]

    @pytest.mark.asyncio
    async def test_a_newer_local_wig_blocks_the_write_until_confirmed(
        self, fake_hass, tmp_path
    ):
        from custom_components.hair.wig_store import wigs_dir

        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(
            tmp_path, supersedes=["wig-original-id"], signal_count=3,
            name="Fable Ceiling Fan (2)",
        )

        result = await self._upload(fake_hass, self._original_text())

        assert result["success"] is True
        assert result["filenames"] == []
        assert result["files"] == []
        block = result["reverse_supersession"]
        # The two fields the Wigs tab's re-confirm has always read keep
        # their names and their meaning; R2 only widened the block
        # around them, and this dialog reads exactly what it did.
        assert block["name"] == "Fable Ceiling Fan (2)"
        assert block["signal_count"] == 3
        # Nothing files: the closet holds only the successor already
        # planted there, never a copy of the arrival.
        names = {p.name for p in wigs_dir(tmp_path).glob("*.wig.json")}
        assert names == {"successor.wig.json"}

    @pytest.mark.asyncio
    async def test_import_anyway_resends_confirmed_and_files_it(
        self, fake_hass, tmp_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path, supersedes=["wig-original-id"])
        text = self._original_text()

        blocked = await self._upload(fake_hass, text)
        assert "reverse_supersession" in blocked

        confirmed = await self._upload(fake_hass, text, confirmed=True)
        assert confirmed["success"] is True
        assert "reverse_supersession" not in confirmed
        assert len(confirmed["filenames"]) == 1

    @pytest.mark.asyncio
    async def test_no_local_successor_uploads_without_a_hitch(
        self, fake_hass, tmp_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        result = await self._upload(fake_hass, self._original_text())
        assert result["success"] is True
        assert "reverse_supersession" not in result

    @pytest.mark.asyncio
    async def test_an_unrelated_supersedes_chain_does_not_false_match(
        self, fake_hass, tmp_path
    ):
        """The successor's chain must actually name THIS wig, not just
        exist -- a wig that supersedes some other ancestor is no signal
        about this one."""
        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path, supersedes=["some-other-wig-id"])
        result = await self._upload(fake_hass, self._original_text())
        assert result["success"] is True
        assert "reverse_supersession" not in result


class TestTheReverseAnswerCarriesTheSuccessorsRow:
    """R2 (issue 11, owner ruled 2026-08-30). The drop that lands on a
    device's ghost tile is somebody trying to CREATE A DEVICE, so the
    useful answer to "your closet already has a newer version of this"
    is the newer version itself, ready to build from. That needs the
    successor's picker row in the same answer -- otherwise the offer
    costs a whole second round trip through wigs/list, which is the
    exact re-scan B4 was written to stop doing.

    The row is the same shape a landed file's entry carries, out of the
    same function, so the two answers cannot drift into describing a
    wig differently. Nothing else about the block moved: the Wigs tab's
    own re-confirm dialog reads name and signal_count and is untouched.
    """

    PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"

    def _write_successor(self, tmp_path, **extra) -> None:
        import json

        from custom_components.hair.wig_format import WIG_FORMAT_V1
        from custom_components.hair.wig_store import (
            ensure_wigs_dir,
            wigs_dir,
        )

        ensure_wigs_dir(tmp_path)
        payload = {
            "format": WIG_FORMAT_V1,
            "name": "Fable Ceiling Fan (2)",
            "wig_id": "wig-successor-id",
            "supersedes": ["wig-original-id"],
            "brand": "Fable",
            "model": "FCF-9",
            "kind": "ceiling fan",
            "signals": [
                {"alias": f"Signal {i}", "pronto": self.PRONTO}
                for i in range(3)
            ],
        }
        payload.update(extra)
        (wigs_dir(tmp_path) / "successor.wig.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def _original_text(self) -> str:
        import json

        from custom_components.hair.wig_format import WIG_FORMAT_V1

        return json.dumps({
            "format": WIG_FORMAT_V1,
            "name": "Fable Ceiling Fan",
            "wig_id": "wig-original-id",
            "signals": [{"alias": "Power", "pronto": self.PRONTO}],
        })

    async def _upload(self, fake_hass) -> dict:
        from custom_components.hair.websocket_api import ws_wigs_upload

        conn = _make_connection()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload",
            "text": self._original_text(),
        })
        conn.send_result.assert_called_once()
        return conn.send_result.call_args[0][1]

    @pytest.mark.asyncio
    async def test_the_block_names_the_file_the_offer_would_build_from(
        self, fake_hass, tmp_path
    ):
        """Without the filename there is nothing to build from: every
        create path downstream keys on it."""
        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path)

        block = (await self._upload(fake_hass))["reverse_supersession"]

        assert block["filename"] == "successor.wig.json"

    @pytest.mark.asyncio
    async def test_the_block_carries_the_row_a_picker_renders(
        self, fake_hass, tmp_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path)

        block = (await self._upload(fake_hass))["reverse_supersession"]

        assert block["name"] == "Fable Ceiling Fan (2)"
        assert block["brand"] == "Fable"
        assert block["model"] == "FCF-9"
        assert block["kind"] == "ceiling fan"
        assert block["signal_count"] == 3
        assert block["matrix"] is None

    @pytest.mark.asyncio
    async def test_a_matrix_successor_carries_its_matrix_summary(
        self, fake_hass, tmp_path
    ):
        """A climate successor is the case that matters most here: its
        signal list is near-empty and the states live in the lattice,
        so a row without the matrix summary would offer the person a
        wig that looks like it carries nothing."""
        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path, climate={
            "min_temp": 16, "max_temp": 30, "precision": 1,
            "unit": "C", "off": self.PRONTO,
            "modes": ["cool"], "fan_modes": ["auto"],
            "cells": [{
                "mode": "cool", "fan": "auto", "temp": 24,
                "pronto": self.PRONTO,
            }],
        })

        block = (await self._upload(fake_hass))["reverse_supersession"]

        assert block["matrix"] is not None
        assert block["matrix"]["cells"] == 1

    @pytest.mark.asyncio
    async def test_the_block_reports_the_successors_own_comb_receipt(
        self, fake_hass, tmp_path
    ):
        """The receipt this wig already carries, read, not re-derived.
        Combing here would stamp a fresh receipt onto a closet wig that
        nothing writes back to disk, which is a lie with a short life
        and no author. A successor nobody has combed reports None,
        which the closet already renders as its own distinct state.
        """
        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path)

        block = (await self._upload(fake_hass))["reverse_supersession"]

        assert "comb" in block
        assert block["comb"] is None

    @pytest.mark.asyncio
    async def test_nothing_files_and_the_closet_is_unchanged(
        self, fake_hass, tmp_path
    ):
        """The whole point of answering rather than writing: this path
        still holds the arrival off disk. R2 added fields to the
        answer, not a write to it."""
        from custom_components.hair.wig_store import wigs_dir

        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path)

        result = await self._upload(fake_hass)

        assert result["files"] == []
        assert result["filenames"] == []
        names = {p.name for p in wigs_dir(tmp_path).glob("*.wig.json")}
        assert names == {"successor.wig.json"}

    @pytest.mark.asyncio
    async def test_a_landed_entry_and_this_block_describe_a_wig_alike(
        self, fake_hass, tmp_path
    ):
        """One definition of the row, checked from both ends. Upload the
        successor's own bytes into an empty closet and the entry it
        files carries the same field set this block does, so a future
        edit to one cannot quietly leave the other behind.
        """
        import json

        from custom_components.hair.websocket_api import ws_wigs_upload
        from custom_components.hair.wig_format import WIG_FORMAT_V1

        fake_hass.config.config_dir = str(tmp_path)
        self._write_successor(tmp_path)
        block = (await self._upload(fake_hass))["reverse_supersession"]

        fresh = json.dumps({
            "format": WIG_FORMAT_V1,
            "name": "Fable Ceiling Fan (2)",
            "wig_id": "wig-successor-id",
            "brand": "Fable",
            "model": "FCF-9",
            "kind": "ceiling fan",
            "signals": [
                {"alias": f"Signal {i}", "pronto": self.PRONTO}
                for i in range(3)
            ],
        })
        conn = _make_connection()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 2, "type": "hair/wigs/upload", "text": fresh,
            "confirmed": True,
        })
        entry = conn.send_result.call_args[0][1]["files"][0]

        row = ("filename", "name", "brand", "model", "kind",
               "signal_count", "matrix")
        assert set(row) <= set(block)
        for key in row:
            if key == "filename":
                continue
            assert block[key] == entry[key]


class TestEveryRegisteredCommandIsDecorated:
    """Every handler registered with HA must carry the
    ``@websocket_api.websocket_command`` decorator in the source.

    This exists because of a real outage on the test box. A helper
    function was inserted BETWEEN a decorator stack and the handler it
    belonged to, so the decorators landed on the helper and the handler
    was left bare. Home Assistant raises ``AttributeError: 'function'
    object has no attribute '_ws_command'`` at registration,
    ``async_setup_entry`` fails, and the ENTIRE INTEGRATION does not
    load. One misplaced insert took HAIR off the box completely.

    Nothing in this suite could see it. Every other test calls the
    handlers directly, where an undecorated function behaves exactly the
    same, and ``homeassistant`` is stubbed here so the decorator is a
    no-op at test time. Only real registration cares. So the check is
    STATIC: read the source, not the runtime.
    """

    @staticmethod
    def _parse():
        import ast
        import pathlib

        src = (
            pathlib.Path(__file__).resolve().parent.parent
            / "websocket_api.py"
        ).read_text(encoding="utf-8")
        return ast.parse(src)

    @staticmethod
    def _is_ws_command(dec) -> bool:
        import ast

        func = dec.func if isinstance(dec, ast.Call) else dec
        return (
            isinstance(func, ast.Attribute)
            and func.attr == "websocket_command"
        )

    def _decorated_names(self) -> set[str]:
        import ast

        tree = self._parse()
        names = set()
        for node in ast.walk(tree):
            if isinstance(
                node, ast.AsyncFunctionDef | ast.FunctionDef
            ) and any(
                self._is_ws_command(d) for d in node.decorator_list
            ):
                names.add(node.name)
        return names

    def _registered_names(self) -> list[str]:
        import ast

        tree = self._parse()
        found: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "async_register_command"
                and len(node.args) == 2
                and isinstance(node.args[1], ast.Name)
            ):
                found.append(node.args[1].id)
        return found

    def test_every_registered_handler_is_decorated(self):
        registered = self._registered_names()
        assert registered, "no registrations found; the parse is wrong"
        decorated = self._decorated_names()
        bare = sorted(set(registered) - decorated)
        assert not bare, (
            "these handlers are registered but carry no "
            "@websocket_api.websocket_command decorator, which makes "
            f"async_setup_entry fail and the integration not load: {bare}"
        )

    def test_no_decorator_stack_landed_on_a_helper(self):
        """The other half of the same accident. A decorated function
        whose name does not look like a handler means a stack came to
        rest on the wrong def, which also leaves a real handler bare."""
        odd = sorted(
            n for n in self._decorated_names() if not n.startswith("ws_")
        )
        assert not odd, (
            "these are decorated as WebSocket commands but are not named "
            f"like handlers; a decorator stack likely slipped: {odd}"
        )


# ---------------------------------------------------------------------------
# Signpost 4, Track M: the hear-side lattice rides through every door.
#
# A Remote minted from a matrix wig (or through either mirror door)
# carries a COPY of the matrix, keyed by its own id in the same
# hair/matrices/ folder. These cover the five doors that create, copy
# or destroy one, plus the two read paths (the list payload's summary
# and the remote cell browser).
# ---------------------------------------------------------------------------


def _tiny_matrix():
    """A two-cell lattice, enough to assert identity and counts."""
    from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

    return ClimateMatrix(
        min_temp=16, max_temp=30, off="0000 006D 0001 0000 0060 0060",
        modes=["cool"], fan_modes=["auto"],
        cells=[
            ClimateCell(
                mode="cool", fan="auto", temp=22,
                pronto="0000 006D 0001 0000 00C0 00C0",
            ),
            ClimateCell(
                mode="cool", fan="auto", temp=23,
                pronto="0000 006D 0001 0000 00D0 00D0",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_wig_make_remote_matrix_wig_copies_the_lattice(fake_hass):
    """A matrix wig's lattice is written under the NEW REMOTE's id
    before the remote exists, and the remote is flagged. The matrix
    rule still holds: no trigger is minted per cell."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    matrix = _tiny_matrix()
    wig = MagicMock(signals=[], climate=matrix)

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-1"))

    conn = _make_connection()
    with patch(
        "custom_components.hair.wig_store.load_wig", return_value=wig
    ), patch(
        "custom_components.hair.wig_identity.wig_signal_identities",
        return_value=[],
    ), patch(
        "custom_components.hair.matrix_store.write_matrix"
    ) as write_matrix, patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 901, "type": "hair/wigs/make-remote", "name": "Bedroom AC",
                "filename": "bedroom-ac.hairwig",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.climate_matrix is True
    write_matrix.assert_called_once()
    _cfg, written_id, written_matrix = write_matrix.call_args[0]
    assert written_id == created.id
    assert written_matrix is matrix
    store.add_trigger.assert_not_called()
    result = conn.send_result.call_args[0][1]
    assert result["matrix_cells"] == 2
    assert result["climate_matrix"] is True


@pytest.mark.asyncio
async def test_wig_make_remote_flat_wig_writes_no_matrix(fake_hass):
    """A flat wig leaves the flag false and never touches the folder."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-1"))

    conn = _make_connection()
    with patch(
        "custom_components.hair.wig_store.load_wig",
        return_value=MagicMock(signals=[], climate=None),
    ), patch(
        "custom_components.hair.wig_identity.wig_signal_identities",
        return_value=[],
    ), patch(
        "custom_components.hair.matrix_store.write_matrix"
    ) as write_matrix, patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 902, "type": "hair/wigs/make-remote", "name": "TV Remote",
                "filename": "tv.hairwig",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.climate_matrix is False
    write_matrix.assert_not_called()
    assert conn.send_result.call_args[0][1]["matrix_cells"] == 0


@pytest.mark.asyncio
async def test_wig_make_remote_matrix_write_failure_refuses_the_mint(
    fake_hass,
):
    """Same refusal the device door makes: a remote that claims a
    lattice it does not have would render a card with nothing behind
    it, so nothing is created at all."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    conn = _make_connection()
    with patch(
        "custom_components.hair.wig_store.load_wig",
        return_value=MagicMock(signals=[], climate=_tiny_matrix()),
    ), patch(
        "custom_components.hair.wig_identity.wig_signal_identities",
        return_value=[],
    ), patch(
        "custom_components.hair.matrix_store.write_matrix",
        side_effect=OSError("disk full"),
    ):
        await ws_wig_make_remote(
            fake_hass, conn,
            {
                "id": 903, "type": "hair/wigs/make-remote", "name": "Bedroom AC",
                "filename": "bedroom-ac.hairwig",
            },
        )

    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "write_failed"
    store.add_trigger_remote.assert_not_called()
    store.add_trigger.assert_not_called()


@pytest.mark.asyncio
async def test_device_make_remote_copies_the_matrix(fake_hass):
    """The mirror door byte-copies the device's matrix under the new
    remote's id, so the remote hears exactly what the device sends."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    device = IRDevice(
        id="dev-ac-1", name="Bedroom AC", device_type=DeviceType.AC,
        climate_matrix=True,
    )
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"].get_device = MagicMock(
        return_value=device
    )

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-1"))

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.copy_matrix", return_value=True
    ) as copy_matrix, patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_device_make_remote(
            fake_hass, conn,
            {
                "id": 904, "type": "hair/device/make-remote",
                "name": "Bedroom AC Handset", "device_id": "dev-ac-1",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.climate_matrix is True
    copy_matrix.assert_called_once()
    _cfg, src_id, dst_id = copy_matrix.call_args[0]
    assert (src_id, dst_id) == ("dev-ac-1", created.id)
    assert conn.send_result.call_args[0][1]["matrix_copied"] is True


@pytest.mark.asyncio
async def test_device_make_remote_copy_failure_degrades_not_refuses(
    fake_hass,
):
    """The triggers are the user's actual ask on this door, so a failed
    copy yields a flat Remote that says so rather than no Remote."""
    store = _wire_triggers(fake_hass)
    store.add_trigger_remote = MagicMock()
    store.add_trigger = MagicMock()

    device = IRDevice(
        id="dev-ac-2", name="Bedroom AC", device_type=DeviceType.AC,
        climate_matrix=True,
    )
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"].get_device = MagicMock(
        return_value=device
    )

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-1"))

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.copy_matrix", return_value=False
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ), patch(
        "custom_components.hair.event.sync_trigger_entities"
    ):
        await ws_device_make_remote(
            fake_hass, conn,
            {
                "id": 905, "type": "hair/device/make-remote",
                "name": "Bedroom AC Handset", "device_id": "dev-ac-2",
            },
        )

    created = store.add_trigger_remote.call_args[0][0]
    assert created.climate_matrix is False
    conn.send_error.assert_not_called()
    assert conn.send_result.call_args[0][1]["matrix_copied"] is False


@pytest.mark.asyncio
async def test_trigger_remote_make_device_copies_matrix_and_forces_ac(
    fake_hass,
):
    """The reverse door: the lattice lands under the DEVICE's id before
    the device exists (the climate entity's load would race a later
    write), and the type is forced to AC no matter what the caller
    asked for."""
    remote = TriggerRemote(
        id="rem-ac-1", name="Bedroom AC Handset", climate_matrix=True
    )
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.get_triggers_for_remote = MagicMock(return_value=[])

    matrix = _tiny_matrix()
    manager = _manager_for_device_creation()
    # The minted device IS a matrix device now, so _device_full reads
    # its lattice back through the manager's cache on the way out.
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"] = manager

    order: list[str] = []
    manager.async_create_device = AsyncMock(
        side_effect=lambda _d: order.append("create")
    )

    def _copy(_cfg, _src, _dst):
        order.append("copy")
        return True

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.copy_matrix", side_effect=_copy
    ) as copy_matrix:
        await ws_trigger_remote_make_device(
            fake_hass, conn,
            {
                "id": 906, "type": "hair/trigger-remote/make-device",
                "name": "Bedroom AC", "remote_id": "rem-ac-1",
                "device_type": "media_player",
                "emitter_entity_ids": ["infrared.e"],
            },
        )

    device = manager.async_create_device.call_args[0][0]
    assert device.climate_matrix is True
    assert device.device_type == DeviceType.AC
    assert order == ["copy", "create"]
    _cfg, src_id, dst_id = copy_matrix.call_args[0]
    assert (src_id, dst_id) == ("rem-ac-1", device.id)
    result = conn.send_result.call_args[0][1]
    assert result["matrix_copied"] is True
    assert result["forced_ac"] is True
    assert result["matrix"]["cells"] == 2


@pytest.mark.asyncio
async def test_trigger_remote_make_device_copy_failure_stays_flat(fake_hass):
    """No lattice, no climate entity: the device keeps the type the
    caller asked for rather than becoming an AC that refuses every
    send."""
    remote = TriggerRemote(
        id="rem-ac-2", name="Bedroom AC Handset", climate_matrix=True
    )
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.get_triggers_for_remote = MagicMock(return_value=[])

    manager = _manager_for_device_creation()
    fake_hass.data[DOMAIN]["entry-1"]["device_manager"] = manager

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.copy_matrix", return_value=False
    ):
        await ws_trigger_remote_make_device(
            fake_hass, conn,
            {
                "id": 907, "type": "hair/trigger-remote/make-device",
                "name": "Bedroom AC", "remote_id": "rem-ac-2",
                "device_type": "media_player",
                "emitter_entity_ids": ["infrared.e"],
            },
        )

    device = manager.async_create_device.call_args[0][0]
    assert device.climate_matrix is False
    assert device.device_type == DeviceType.MEDIA_PLAYER
    result = conn.send_result.call_args[0][1]
    assert result["matrix_copied"] is False
    assert result["forced_ac"] is False


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_copies_the_matrix(fake_hass):
    """ws_duplicate_device's shape exactly: the file rides along, and a
    failed copy clears the flag instead of leaving a broken claim."""
    source = TriggerRemote(id="src-m", name="Bedroom AC", climate_matrix=True)
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=source)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    store.add_trigger_remote = MagicMock()

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-1"))

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.copy_matrix", return_value=True
    ) as copy_matrix, patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_duplicate_trigger_remote(
            fake_hass, conn,
            {
                "id": 908, "type": "hair/trigger-remote/duplicate",
                "remote_id": "src-m", "new_name": "Bedroom AC copy",
            },
        )

    clone = store.add_trigger_remote.call_args[0][0]
    assert clone.climate_matrix is True
    _cfg, src_id, dst_id = copy_matrix.call_args[0]
    assert (src_id, dst_id) == ("src-m", clone.id)


@pytest.mark.asyncio
async def test_duplicate_trigger_remote_matrix_copy_failure_clears_flag(
    fake_hass,
):
    source = TriggerRemote(id="src-m2", name="Bedroom AC", climate_matrix=True)
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=source)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    store.add_trigger_remote = MagicMock()

    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-1"))

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.copy_matrix", return_value=False
    ), patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=registry,
    ):
        await ws_duplicate_trigger_remote(
            fake_hass, conn,
            {
                "id": 909, "type": "hair/trigger-remote/duplicate",
                "remote_id": "src-m2", "new_name": "Bedroom AC copy",
            },
        )

    clone = store.add_trigger_remote.call_args[0][0]
    assert clone.climate_matrix is False


@pytest.mark.asyncio
async def test_delete_trigger_remote_deletes_its_matrix_file(fake_hass):
    """Delete takes the lattice with it, AFTER the store commit."""
    remote = TriggerRemote(id="rem-del", name="Bedroom AC", climate_matrix=True)
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.remove_trigger_remote = MagicMock(return_value=[])

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.delete_matrix", return_value=True
    ) as delete_matrix, patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=MagicMock(
            async_get_device=MagicMock(return_value=None)
        ),
    ):
        await ws_delete_trigger_remote(
            fake_hass, conn,
            {
                "id": 910, "type": "hair/trigger-remote/delete",
                "remote_id": "rem-del",
            },
        )

    delete_matrix.assert_called_once()
    assert delete_matrix.call_args[0][1] == "rem-del"
    assert conn.send_result.call_args[0][1]["removed"] is True


@pytest.mark.asyncio
async def test_delete_flat_trigger_remote_touches_no_matrix_file(fake_hass):
    remote = TriggerRemote(id="rem-flat", name="TV Remote")
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.remove_trigger_remote = MagicMock(return_value=[])

    conn = _make_connection()
    with patch(
        "custom_components.hair.matrix_store.delete_matrix"
    ) as delete_matrix, patch(
        "custom_components.hair.websocket_api.dr.async_get",
        return_value=MagicMock(
            async_get_device=MagicMock(return_value=None)
        ),
    ):
        await ws_delete_trigger_remote(
            fake_hass, conn,
            {
                "id": 911, "type": "hair/trigger-remote/delete",
                "remote_id": "rem-flat",
            },
        )

    delete_matrix.assert_not_called()


@pytest.mark.asyncio
async def test_list_trigger_remotes_carries_matrix_and_last_heard(fake_hass):
    """The one-call rule: the card renders its lattice summary and its
    heard state off the list payload alone."""
    heard = {
        "cell_key": "cool/auto/23", "cell_name": "Cool 23 Auto",
        "power": None, "at": "2026-08-17T10:00:00+00:00",
        "sl_pattern": "SLLS", "receiver_entity_id": "infrared.lr",
        "receiver_area_name": "Living Room",
    }
    remote = TriggerRemote(
        id="tr-m", name="Bedroom AC", climate_matrix=True, last_heard=heard
    )
    store = _wire_triggers(fake_hass)
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.get_triggers_for_remote = MagicMock(return_value=[])

    listener = MagicMock()
    listener.async_get_matrix = AsyncMock(return_value=_tiny_matrix())
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_list_trigger_remotes(
            fake_hass, conn, {"id": 912, "type": "hair/trigger-remotes"},
        )

    row = conn.send_result.call_args[0][1][0]
    assert row["climate_matrix"] is True
    assert row["matrix"]["cells"] == 2
    assert row["matrix"]["modes"] == ["cool"]
    assert row["last_heard"] == heard
    listener.async_get_matrix.assert_awaited_once_with("tr-m")


@pytest.mark.asyncio
async def test_list_trigger_remotes_flat_remote_reads_no_file(fake_hass):
    """A flat remote must not cost a matrix load per list call."""
    remote = TriggerRemote(id="tr-f", name="TV Remote")
    store = _wire_triggers(fake_hass)
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.get_triggers_for_remote = MagicMock(return_value=[])

    listener = MagicMock()
    listener.async_get_matrix = AsyncMock(return_value=None)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener

    conn = _make_connection()
    with _mock_device_registry(None):
        await ws_list_trigger_remotes(
            fake_hass, conn, {"id": 913, "type": "hair/trigger-remotes"},
        )

    row = conn.send_result.call_args[0][1][0]
    assert row["matrix"] is None
    assert row["last_heard"] is None
    listener.async_get_matrix.assert_not_awaited()


@pytest.mark.asyncio
async def test_remote_matrix_cells_matches_the_device_endpoint(fake_hass):
    """One body, two endpoints: the remote's card is the device's card
    in hear mode, so the same lattice must serialize byte for byte."""
    matrix = _tiny_matrix()
    remote = TriggerRemote(id="tr-cells", name="Bedroom AC", climate_matrix=True)
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)

    listener = MagicMock()
    listener.async_get_matrix = AsyncMock(return_value=matrix)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener

    device = IRDevice(
        id="dev-cells", name="Bedroom AC", device_type=DeviceType.AC,
        climate_matrix=True,
    )
    manager = fake_hass.data[DOMAIN]["entry-1"]["device_manager"]
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)

    remote_conn = _make_connection()
    await ws_trigger_remote_matrix_cells(
        fake_hass, remote_conn,
        {
            "id": 914, "type": "hair/trigger-remote/matrix-cells",
            "remote_id": "tr-cells",
        },
    )
    device_conn = _make_connection()
    await ws_device_matrix_cells(
        fake_hass, device_conn,
        {
            "id": 915, "type": "hair/devices/matrix-cells",
            "device_id": "dev-cells",
        },
    )

    remote_payload = remote_conn.send_result.call_args[0][1]
    assert remote_payload == device_conn.send_result.call_args[0][1]
    assert remote_payload["cells"] == [
        {"m": "cool", "f": "auto", "t": 22},
        {"m": "cool", "f": "auto", "t": 23},
    ]


@pytest.mark.asyncio
async def test_remote_matrix_cells_flat_remote_is_not_found(fake_hass):
    remote = TriggerRemote(id="tr-flat2", name="TV Remote")
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)

    conn = _make_connection()
    await ws_trigger_remote_matrix_cells(
        fake_hass, conn,
        {
            "id": 916, "type": "hair/trigger-remote/matrix-cells",
            "remote_id": "tr-flat2",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


# ---------------------------------------------------------------------------
# hair/trigger-remote/matrix-cell -- ONE cell, with the bytes the cell
# browser deliberately omits (signpost 4, Track M, the three doors).
# ---------------------------------------------------------------------------


def _wire_matrix_remote(fake_hass, matrix, remote=None):
    """A matrix Remote whose lattice the listener serves."""
    remote = remote or TriggerRemote(
        id="tr-cell", name="Bedroom AC", climate_matrix=True,
    )
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)
    listener = MagicMock()
    listener.async_get_matrix = AsyncMock(return_value=matrix)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener
    return store, remote


@pytest.mark.asyncio
async def test_matrix_cell_returns_pronto_name_and_identity(fake_hass):
    """The door's whole purpose: coordinates in, the one cell's code,
    display name and identity out. Identity is DERIVED here rather than
    read off the file -- a wig carries raw Pronto and no decoded fields
    -- which is what makes a trigger minted through this door match the
    same frame heard off the air."""
    _wire_matrix_remote(fake_hass, _tiny_matrix())
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 920, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell", "mode": "cool", "fan": "auto",
            "temp": 22,
        },
    )
    conn.send_error.assert_not_called()
    payload = conn.send_result.call_args[0][1]
    assert payload["pronto"] == "0000 006D 0001 0000 00C0 00C0"
    # The owner-ruled display grammar (2026-07-29): spaced slashes,
    # mode bare first, fan and swing LABELED, temperature a bare
    # number last. Same string the device side freezes into a saved
    # command, so a state trigger and a state command minted off the
    # same cell start from the same name.
    assert payload["name"] == "cool / fan: auto / 22"
    identity = payload["identity"]
    # The fingerprint is what the matcher keys on; it must be present
    # and non-empty or the minted trigger can never fire.
    assert identity["signal_fingerprint"]
    assert set(identity) == {
        "signal_fingerprint",
        "byte_hash",
        "decoded_fingerprint",
        "decoded_protocol",
    }


@pytest.mark.asyncio
async def test_matrix_cell_is_the_other_half_of_the_no_bytes_contract(
    fake_hass,
):
    """The lattice endpoint ships not one byte of Pronto, on purpose.
    This endpoint is why that is affordable: a door about to mint one
    trigger asks for the one cell it needs."""
    matrix = _tiny_matrix()
    _wire_matrix_remote(fake_hass, matrix)

    cells_conn = _make_connection()
    await ws_trigger_remote_matrix_cells(
        fake_hass, cells_conn,
        {
            "id": 921, "type": "hair/trigger-remote/matrix-cells",
            "remote_id": "tr-cell",
        },
    )
    assert "00C0" not in repr(cells_conn.send_result.call_args[0][1])

    cell_conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, cell_conn,
        {
            "id": 922, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell", "mode": "cool", "fan": "auto",
            "temp": 22,
        },
    )
    assert "00C0" in cell_conn.send_result.call_args[0][1]["pronto"]


@pytest.mark.asyncio
async def test_matrix_cell_power_resolves_the_off_code(fake_hass):
    _wire_matrix_remote(fake_hass, _tiny_matrix())
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 923, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell", "power": "off",
        },
    )
    conn.send_error.assert_not_called()
    payload = conn.send_result.call_args[0][1]
    assert payload["pronto"] == "0000 006D 0001 0000 0060 0060"
    assert payload["name"] == "Off"


@pytest.mark.asyncio
async def test_matrix_cell_power_on_without_an_on_code_is_not_found(
    fake_hass,
):
    """_tiny_matrix has an off code and no on code, the common shape."""
    _wire_matrix_remote(fake_hass, _tiny_matrix())
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 924, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell", "power": "on",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_matrix_cell_power_and_mode_together_is_invalid(fake_hass):
    """EXCLUSIVE here, unlike matrix-send where power deliberately wins:
    this caller is minting something that gets kept, so an ambiguous
    request is a client bug worth reporting rather than papering over."""
    _wire_matrix_remote(fake_hass, _tiny_matrix())
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 925, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell", "power": "off", "mode": "cool",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_matrix_cell_neither_power_nor_mode_is_invalid(fake_hass):
    _wire_matrix_remote(fake_hass, _tiny_matrix())
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 926, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "invalid_format"


@pytest.mark.asyncio
async def test_matrix_cell_never_snaps(fake_hass):
    """Matrices are sparse. The frontend round-trips coordinates read
    off matrix-cells, so a miss means a stale client, and snapping
    would only paper over it -- the same contract the device endpoints
    hold."""
    _wire_matrix_remote(fake_hass, _tiny_matrix())
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 927, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-cell", "mode": "cool", "fan": "auto",
            "temp": 24,
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_matrix_cell_flat_remote_is_not_found(fake_hass):
    remote = TriggerRemote(id="tr-flat3", name="TV Remote")
    _wire_matrix_remote(fake_hass, None, remote=remote)
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 928, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "tr-flat3", "mode": "cool",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_matrix_cell_unknown_remote_is_not_found(fake_hass):
    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=None)
    conn = _make_connection()
    await ws_trigger_remote_matrix_cell(
        fake_hass, conn,
        {
            "id": 929, "type": "hair/trigger-remote/matrix-cell",
            "remote_id": "nope", "mode": "cool",
        },
    )
    conn.send_error.assert_called_once()
    assert conn.send_error.call_args[0][1] == "not_found"
