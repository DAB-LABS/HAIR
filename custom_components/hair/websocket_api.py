"""WebSocket API for HAIR frontend communication."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import pluck
from .capture import (
    CaptureProviderType,
    get_available_capture_providers,
    get_capture_provider_for_device,
)
from .capture_orchestrator import (
    CaptureInProgressError,
    CaptureOrchestrator,
)
from .command_templates import get_action_options, get_templates_for_device_type
from .const import (
    DEFAULT_CAPTURE_TIMEOUT,
    DOMAIN,
    MAX_SEND_COUNT,
    WS_PREFIX,
    CaptureState,
    CommandCategory,
    DeviceType,
)
from .device_manager import DeviceManager, category_for_command_name
from .frequency_standards import IR_CARRIER_STANDARDS_HZ
from .models import IRDevice, IRTrigger
from .pronto_validator import validate_pronto
from .signal_monitor import SignalMonitor
from .signal_store import SignalStore
from .trigger_manager import TriggerManager

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket commands.

    Idempotent — registering the same command twice is harmless because
    we guard with a hass.data flag.
    """
    if hass.data.get(f"{DOMAIN}_ws_registered"):
        return
    hass.data[f"{DOMAIN}_ws_registered"] = True

    websocket_api.async_register_command(hass, ws_get_devices)
    websocket_api.async_register_command(hass, ws_get_device)
    websocket_api.async_register_command(hass, ws_create_device)
    websocket_api.async_register_command(hass, ws_update_device)
    websocket_api.async_register_command(hass, ws_delete_device)
    websocket_api.async_register_command(hass, ws_duplicate_device)
    websocket_api.async_register_command(hass, ws_delete_command)
    websocket_api.async_register_command(hass, ws_command_update)
    websocket_api.async_register_command(hass, ws_set_command_tx_force_raw)
    websocket_api.async_register_command(hass, ws_reorder_commands)
    websocket_api.async_register_command(hass, ws_reorder_devices)
    websocket_api.async_register_command(hass, ws_send_command)
    websocket_api.async_register_command(hass, ws_start_capture)
    websocket_api.async_register_command(hass, ws_cancel_capture)
    websocket_api.async_register_command(hass, ws_save_captured_command)
    websocket_api.async_register_command(hass, ws_get_command_templates)
    websocket_api.async_register_command(hass, ws_get_capture_providers)
    websocket_api.async_register_command(hass, ws_get_receivers)
    websocket_api.async_register_command(hass, ws_get_sniffer_status)

    # Signal Monitor (unknown devices)
    websocket_api.async_register_command(hass, ws_get_unknown_devices)
    websocket_api.async_register_command(hass, ws_get_unknown_device)
    websocket_api.async_register_command(hass, ws_dismiss_unknown)
    websocket_api.async_register_command(hass, ws_undismiss_unknown)
    websocket_api.async_register_command(hass, ws_assign_signal)
    websocket_api.async_register_command(hass, ws_assign_new_device)
    websocket_api.async_register_command(hass, ws_delete_signal)
    websocket_api.async_register_command(hass, ws_test_signal)
    websocket_api.async_register_command(hass, ws_rename_unknown)
    websocket_api.async_register_command(hass, ws_clear_unknowns)
    websocket_api.async_register_command(hass, ws_set_signal_alias)
    websocket_api.async_register_command(hass, ws_reorder_unknown_devices)
    websocket_api.async_register_command(hass, ws_reorder_unknown_signals)

    # Clips (manual remotes / signals)
    websocket_api.async_register_command(hass, ws_clip_create_remote)
    websocket_api.async_register_command(hass, ws_pluck_list_vendors)
    websocket_api.async_register_command(hass, ws_pluck_run)
    websocket_api.async_register_command(hass, ws_clip_create_signal)
    websocket_api.async_register_command(hass, ws_unknown_signal_edit_pronto)
    websocket_api.async_register_command(hass, ws_unknown_signal_snap_preview)
    websocket_api.async_register_command(hass, ws_clip_validate_pronto)
    websocket_api.async_register_command(hass, ws_clip_delete_remote)

    # Code database picker (Add Remote)
    websocket_api.async_register_command(hass, ws_codes_get_brands)
    websocket_api.async_register_command(hass, ws_codes_import_remote)

    # Action mapping
    websocket_api.async_register_command(hass, ws_get_action_options)
    websocket_api.async_register_command(hass, ws_update_mapping)

    # Triggers
    websocket_api.async_register_command(hass, ws_get_triggers)
    websocket_api.async_register_command(hass, ws_create_trigger)
    websocket_api.async_register_command(hass, ws_update_trigger)
    websocket_api.async_register_command(hass, ws_delete_trigger)
    websocket_api.async_register_command(hass, ws_subscribe_triggers)


def _get_first_entry_data(hass: HomeAssistant) -> dict[str, Any] | None:
    """Return the first entry's hass.data for HAIR.

    HAIR is a hub integration with at most one entry per HA instance.
    """
    entries = hass.data.get(DOMAIN, {})
    for value in entries.values():
        if isinstance(value, dict) and "device_manager" in value:
            return value
    return None


def _device_summary(device: IRDevice, hass: HomeAssistant) -> dict[str, Any]:
    return {
        "id": device.id,
        "name": device.name,
        "device_type": str(device.device_type),
        "manufacturer": device.manufacturer,
        "model": device.model,
        "emitter_entity_ids": list(device.emitter_entity_ids),
        "command_count": len(device.commands),
        "created_at": device.created_at,
        "updated_at": device.updated_at,
    }


def _device_full(device: IRDevice) -> dict[str, Any]:
    full = device.to_dict()
    full["command_count"] = len(device.commands)
    return full


# --- Device Operations ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/devices",
})
@websocket_api.async_response
async def ws_get_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_result(msg["id"], [])
        return
    manager: DeviceManager = data["device_manager"]
    devices = [_device_summary(d, hass) for d in manager.get_all_devices()]
    connection.send_result(msg["id"], devices)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_get_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_found", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return
    connection.send_result(msg["id"], _device_full(device))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/create",
    vol.Required("name"): str,
    vol.Required("device_type"): str,
    vol.Required("emitter_entity_ids"): [str],
    vol.Optional("manufacturer"): vol.Any(str, None),
    vol.Optional("model"): vol.Any(str, None),
    vol.Optional("capture_device_id"): vol.Any(str, None),
    vol.Optional("capture_provider_type"): str,
})
@websocket_api.async_response
async def ws_create_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]

    try:
        device_type = DeviceType(msg["device_type"])
    except ValueError:
        connection.send_error(msg["id"], "invalid_format", "Unknown device_type")
        return

    provider_value = msg.get("capture_provider_type") or CaptureProviderType.ESPHOME
    try:
        provider_type = CaptureProviderType(provider_value)
    except ValueError:
        connection.send_error(
            msg["id"], "invalid_format", "Unknown capture_provider_type"
        )
        return

    device = IRDevice(
        name=msg["name"],
        device_type=device_type,
        manufacturer=msg.get("manufacturer"),
        model=msg.get("model"),
        emitter_entity_ids=list(msg["emitter_entity_ids"]),
        capture_device_id=msg.get("capture_device_id"),
        capture_provider_type=provider_type,
    )
    await manager.async_create_device(device)
    connection.send_result(msg["id"], _device_full(device))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/update",
    vol.Required("device_id"): str,
    vol.Optional("name"): str,
    vol.Optional("manufacturer"): vol.Any(str, None),
    vol.Optional("model"): vol.Any(str, None),
    vol.Optional("emitter_entity_ids"): [str],
    vol.Optional("device_type"): str,
})
@websocket_api.async_response
async def ws_update_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    if "name" in msg:
        device.name = msg["name"]
    if "manufacturer" in msg:
        device.manufacturer = msg["manufacturer"]
    if "model" in msg:
        device.model = msg["model"]
    if "emitter_entity_ids" in msg:
        device.emitter_entity_ids = list(msg["emitter_entity_ids"])
    if "device_type" in msg:
        device.device_type = DeviceType(msg["device_type"])

    await manager.async_update_device(device)
    connection.send_result(msg["id"], _device_full(device))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/delete",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_delete_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    removed = await manager.async_remove_device(msg["device_id"])
    if not removed:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return
    connection.send_result(msg["id"], {"removed": True})


# --- Command Operations ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/send",
    vol.Required("device_id"): str,
    vol.Required("command_id"): str,
})
@websocket_api.async_response
async def ws_send_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    try:
        await manager.async_send_command(msg["device_id"], msg["command_id"])
    except KeyError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    except Exception as err:
        _LOGGER.error("Send command failed: %s", err, exc_info=True)
        connection.send_error(msg["id"], "send_failed", str(err))
        return
    connection.send_result(msg["id"], {"sent": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/delete",
    vol.Required("device_id"): str,
    vol.Required("command_id"): str,
})
@websocket_api.async_response
async def ws_delete_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    removed = await manager.async_remove_command(
        msg["device_id"], msg["command_id"]
    )
    if not removed:
        connection.send_error(msg["id"], "not_found", "Command not found")
        return
    connection.send_result(msg["id"], {"removed": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/set-tx-force-raw",
    vol.Required("device_id"): str,
    vol.Required("command_id"): str,
    vol.Required("tx_force_raw"): bool,
})
@websocket_api.async_response
async def ws_set_command_tx_force_raw(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Toggle a command's ``tx_force_raw`` (use captured timings) flag.

    When True, transmit replays the captured Pronto/raw timings rather
    than re-encoding from the decoded value. The per-command escape hatch
    for the rare destination that wants the captured timings.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    updated = await manager.async_set_command_tx_force_raw(
        msg["device_id"], msg["command_id"], msg["tx_force_raw"]
    )
    if not updated:
        connection.send_error(msg["id"], "not_found", "Command not found")
        return
    connection.send_result(msg["id"], {"tx_force_raw": msg["tx_force_raw"]})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/duplicate",
    vol.Required("device_id"): str,
    vol.Required("new_name"): str,
})
@websocket_api.async_response
async def ws_duplicate_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Clone an existing HAIR device under a new name.

    Every command and the entity_config come along; triggers and ids do
    not. See ``IRDevice.clone`` for the field-by-field copy semantics.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    source = manager.get_device(msg["device_id"])
    if source is None:
        connection.send_error(msg["id"], "not_found", "Source device not found")
        return

    new_name = msg["new_name"].strip()
    if not new_name:
        connection.send_error(
            msg["id"], "invalid_format", "Name cannot be empty"
        )
        return

    clone = source.clone(new_name)
    await manager.async_create_device(clone)
    connection.send_result(msg["id"], _device_full(clone))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/reorder-commands",
    vol.Required("device_id"): str,
    vol.Required("command_ids"): [str],
})
@websocket_api.async_response
async def ws_reorder_commands(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Reorder a device's commands to match the given ID list.

    The full canonical device is returned so the frontend can reconcile
    its view if it drifted from server state (e.g. another tab added a
    command mid-drag).
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    try:
        device.reorder_commands(list(msg["command_ids"]))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return

    await manager.async_update_device(device)
    connection.send_result(msg["id"], _device_full(device))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/devices/reorder",
    vol.Required("device_ids"): [str],
})
@websocket_api.async_response
async def ws_reorder_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Reorder the HAIR device list to match the given id list."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    try:
        await manager.async_reorder_devices(list(msg["device_ids"]))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], {"reordered": True})


# --- Capture Operations (with event streaming) ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/start",
    vol.Required("device_id"): str,
    vol.Optional("timeout", default=DEFAULT_CAPTURE_TIMEOUT): int,
})
@websocket_api.async_response
async def ws_start_capture(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Start IR capture and stream events to the client.

    The handler responds with the session_id immediately and then sends
    further messages as ``event``-typed pushes:
    - capture_listening
    - capture_received   { result, duplicate_of? }
    - capture_timeout
    - capture_error      { error }
    - capture_cancelled
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return

    manager: DeviceManager = data["device_manager"]
    orchestrator: CaptureOrchestrator = data["orchestrator"]
    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    capture_device_id = device.capture_device_id
    if capture_device_id is None:
        connection.send_error(
            msg["id"],
            "no_capture_device",
            "Device has no capture hardware configured",
        )
        return

    provider = await get_capture_provider_for_device(
        hass, device.capture_provider_type, capture_device_id
    )
    if provider is None:
        connection.send_error(
            msg["id"],
            "provider_unavailable",
            "Capture provider not available",
        )
        return

    msg_id = msg["id"]
    timeout = msg.get("timeout", DEFAULT_CAPTURE_TIMEOUT)

    try:
        session = await orchestrator.start_capture(
            provider, device.id, timeout=timeout
        )
    except CaptureInProgressError as err:
        connection.send_error(msg_id, "in_progress", str(err))
        return
    except Exception as err:
        connection.send_error(msg_id, "capture_failed", str(err))
        return

    # Subscribe to capture events and forward them as pushed events.
    @callback
    def _on_event(state: CaptureState, result) -> None:
        payload: dict[str, Any]
        if state == CaptureState.LISTENING:
            payload = {"type": "capture_listening"}
        elif state == CaptureState.CAPTURED and result is not None:
            duplicate = orchestrator.check_duplicate(device, result)
            payload = {
                "type": "capture_received",
                "result": result.to_dict(),
            }
            if duplicate is not None:
                payload["duplicate_of"] = {
                    "id": duplicate.id,
                    "name": duplicate.name,
                }
        elif state == CaptureState.TIMEOUT:
            payload = {"type": "capture_timeout"}
        elif state == CaptureState.ERROR:
            payload = {"type": "capture_error", "error": "Capture failed"}
        elif state == CaptureState.CANCELLED:
            payload = {"type": "capture_cancelled"}
        else:
            return
        connection.send_event(msg_id, payload)

    unsubscribe = orchestrator.subscribe(session.session_id, _on_event)
    connection.subscriptions[msg_id] = unsubscribe

    # Acknowledge the subscription with the session id so the client
    # can later cancel/save against it.
    connection.send_result(
        msg_id,
        {
            "session_id": session.session_id,
            "device_id": device.id,
            "timeout": timeout,
        },
    )

    # Re-emit the listening state so clients that subscribed after the
    # initial dispatch still see it.
    connection.send_event(msg_id, {"type": "capture_listening"})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/cancel",
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_cancel_capture(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    orchestrator: CaptureOrchestrator = data["orchestrator"]
    await orchestrator.cancel_capture(msg["session_id"])
    connection.send_result(msg["id"], {"cancelled": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/save",
    vol.Required("device_id"): str,
    vol.Required("session_id"): str,
    vol.Required("command_name"): str,
    vol.Optional("command_category"): str,
})
@websocket_api.async_response
async def ws_save_captured_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    orchestrator: CaptureOrchestrator = data["orchestrator"]

    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    result = orchestrator.get_session_result(msg["session_id"])
    if result is None:
        connection.send_error(
            msg["id"], "no_capture", "No captured signal for that session"
        )
        return

    category_value = msg.get("command_category")
    if category_value:
        try:
            category = CommandCategory(category_value)
        except ValueError:
            category = category_for_command_name(msg["command_name"])
    else:
        category = category_for_command_name(msg["command_name"])

    command = result.to_command(msg["command_name"], category)
    await manager.async_add_command(device.id, command)
    connection.send_result(msg["id"], command.to_dict())


# --- Template & Provider Info ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/templates",
    vol.Required("device_type"): str,
})
@websocket_api.async_response
async def ws_get_command_templates(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    templates = get_templates_for_device_type(msg["device_type"])
    connection.send_result(
        msg["id"], [t.to_dict() for t in templates]
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/providers",
})
@websocket_api.async_response
async def ws_get_capture_providers(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    providers = await get_available_capture_providers(hass)
    connection.send_result(msg["id"], providers)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/receivers",
})
@websocket_api.async_response
async def ws_get_receivers(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return native IR receiver entities (HA 2026.6+).

    Returns an empty list on older HA versions.
    """
    receivers: list[dict[str, Any]] = []
    try:
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
        )

        entity_ids = async_get_receivers(hass)
        for entity_id in entity_ids:
            state = hass.states.get(entity_id)
            name = entity_id
            if state is not None:
                name = state.attributes.get("friendly_name", entity_id)
            receivers.append({
                "entity_id": entity_id,
                "name": str(name),
            })
    except (ImportError, AttributeError):
        pass  # Pre-2026.6: no native receiver API.

    connection.send_result(msg["id"], receivers)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/sniffer/status",
})
@websocket_api.async_response
async def ws_get_sniffer_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return Sniffer status so the empty state can explain itself.

    ``has_receivers`` is False when no native receiver is subscribed and
    no ESPHome bridge has fired this session, which means "no receiver is
    set up" rather than "no signals seen yet".
    """
    data = _get_first_entry_data(hass)
    has_receivers = False
    if data is not None:
        monitor: SignalMonitor = data["signal_monitor"]
        has_receivers = monitor.has_receivers
    connection.send_result(msg["id"], {"has_receivers": has_receivers})


# --- Code database picker ---


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/codes/brands",
})
@websocket_api.async_response
async def ws_codes_get_brands(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the picker tree (brand -> codebook -> function) from the
    installed infrared-protocols codebooks. Empty when the library is
    missing or exposes no codebooks."""
    from .code_library import get_tree

    # get_tree walks the codebook package on disk and imports modules, so it
    # is offloaded to the executor rather than run on the event loop.
    tree = await hass.async_add_executor_job(get_tree)
    connection.send_result(msg["id"], tree)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/codes/import-remote",
    vol.Required("codebook_id"): vol.All(str, vol.Length(max=200)),
    vol.Optional("name"): vol.All(str, vol.Length(max=200)),
    vol.Optional("function_ids"): [vol.All(str, vol.Length(max=200))],
})
@websocket_api.async_response
async def ws_codes_import_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Materialize a codebook into a new clipped remote, one signal per
    function, each aliased to its function name and pre-populated with its
    decoded protocol identity for canonical transmit."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    from .code_library import codebook_label, materialize_codebook

    # materialize_codebook imports library modules from disk; keep it off the
    # event loop.
    entries = await hass.async_add_executor_job(
        materialize_codebook, msg["codebook_id"], msg.get("function_ids")
    )
    if not entries:
        connection.send_error(
            msg["id"], "no_codes", "No usable codes for that selection"
        )
        return
    monitor: SignalMonitor = data["signal_monitor"]
    name = (
        msg.get("name")
        or codebook_label(msg["codebook_id"])
        or "Imported Remote"
    )
    result = await monitor.import_manual_remote(name, entries)
    connection.send_result(msg["id"], result)


# --- Signal Monitor (Unknown Devices) ---


def _unknown_device_summary(device) -> dict[str, Any]:
    """Build a summary dict for an unknown device."""
    return {
        "id": device.id,
        "fingerprint": device.fingerprint,
        "protocol": device.protocol,
        "device_address": device.device_address,
        "label": device.label,
        "signal_count": len(device.signals),
        "hit_count": device.hit_count,
        "first_seen": device.first_seen,
        "last_seen": device.last_seen,
        "dismissed": device.dismissed,
        "source": device.source,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/devices",
    vol.Optional("include_dismissed", default=False): bool,
    vol.Optional("min_hits"): vol.Any(int, None),
    vol.Optional("source"): vol.Any("sniffed", "manual", None),
})
@websocket_api.async_response
async def ws_get_unknown_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return unknown devices sorted by activity."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_result(msg["id"], [])
        return
    monitor: SignalMonitor = data["signal_monitor"]
    devices = monitor.get_unknown_devices(
        include_dismissed=msg.get("include_dismissed", False),
        min_hits=msg.get("min_hits"),
        source=msg.get("source"),
    )
    connection.send_result(
        msg["id"], [_unknown_device_summary(d) for d in devices]
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/device",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_get_unknown_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return a single unknown device with all its signals."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    device = monitor.get_unknown_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Unknown device not found")
        return
    connection.send_result(msg["id"], device.to_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/dismiss",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_dismiss_unknown(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Dismiss an unknown device (hide from list)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    if not monitor.dismiss_device(msg["device_id"]):
        connection.send_error(msg["id"], "not_found", "Unknown device not found")
        return
    connection.send_result(msg["id"], {"dismissed": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/undismiss",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_undismiss_unknown(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Restore a dismissed unknown device."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    if not monitor.undismiss_device(msg["device_id"]):
        connection.send_error(msg["id"], "not_found", "Unknown device not found")
        return
    connection.send_result(msg["id"], {"undismissed": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/assign",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
    vol.Required("hair_device_id"): str,
    vol.Required("command_name"): str,
    vol.Optional("command_category", default="custom"): str,
    vol.Optional("send_count", default=1): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
})
@websocket_api.async_response
async def ws_assign_signal(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Assign an unknown signal as a named command on a HAIR device."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.assign_signal(
        msg["device_id"],
        msg["signal_id"],
        msg["hair_device_id"],
        msg["command_name"],
        msg.get("command_category", "custom"),
        send_count=msg.get("send_count", 1),
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "assign_failed"),
            result.get("error", "Assign failed"),
        )
        return
    # The assign path does not run the action auto-map the learn path does;
    # apply it now so a standard-action command (Fan: Auto, etc.) maps and
    # the device's entities refresh.
    device_manager: DeviceManager = data["device_manager"]
    await device_manager.async_apply_auto_map(
        msg["hair_device_id"], result["command_id"]
    )
    connection.send_result(msg["id"], {
        "assigned": True,
        "command_id": result["command_id"],
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/test",
    vol.Required("signal_id"): str,
    vol.Optional("emitter_entity_id"): str,
})
@websocket_api.async_response
async def ws_test_signal(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send an unknown signal through an emitter for verification."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return

    emitter_id = msg.get("emitter_entity_id")
    if not emitter_id:
        # Default to the first emitter configured on any HAIR device.
        store = data["store"]
        for dev in store.get_all_devices():
            if dev.emitter_entity_ids:
                emitter_id = dev.emitter_entity_ids[0]
                break
    if not emitter_id:
        connection.send_error(msg["id"], "no_emitter", "No emitter entity configured")
        return

    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.test_signal(
        msg["signal_id"], emitter_id
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "test_failed"),
            result.get("error", "Test failed"),
        )
        return
    connection.send_result(msg["id"], {"sent": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/rename",
    vol.Required("device_id"): str,
    vol.Required("label"): str,
})
@websocket_api.async_response
async def ws_rename_unknown(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Rename an unknown device with a user-friendly label."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    signal_store: SignalStore = data["signal_store"]
    device = signal_store.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Unknown device not found")
        return
    label = msg["label"].strip()
    device.label = label if label else None
    await signal_store.async_save()
    connection.send_result(msg["id"], {"label": device.label})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/assign-new-device",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
    vol.Required("device_name"): str,
    vol.Required("device_type"): str,
    vol.Required("emitter_entity_ids"): [str],
    vol.Required("command_name"): str,
    vol.Optional("command_category", default="custom"): str,
    vol.Optional("send_count", default=1): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
})
@websocket_api.async_response
async def ws_assign_new_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new HAIR device and assign an unknown signal atomically."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.assign_to_new_device(
        msg["device_id"],
        msg["signal_id"],
        msg["device_name"],
        msg["device_type"],
        list(msg["emitter_entity_ids"]),
        msg["command_name"],
        msg.get("command_category", "custom"),
        send_count=msg.get("send_count", 1),
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "assign_failed"),
            result.get("error", "Assign failed"),
        )
        return

    # Register HA device + entities now that both stores are persisted.
    device_mgr = data["device_manager"]
    new_device = result["device"]
    # Apply the action auto-map before creating entities, so the new device's
    # feature entities (e.g. an AC's fan/hvac modes) come up already mapped.
    command = new_device.get_command(result["command_id"])
    if command is not None:
        device_mgr._auto_map_command(new_device, command)
        device_mgr._store.update_device(new_device)
        await device_mgr._store.async_save()
    device_mgr._register_ha_device(new_device)
    await device_mgr._entity_factory.async_create_entities(new_device)

    connection.send_result(msg["id"], {
        "assigned": True,
        "device_id": result["device_id"],
        "command_id": result["command_id"],
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/delete",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
})
@websocket_api.async_response
async def ws_delete_signal(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a single unknown signal."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.delete_signal(
        msg["device_id"], msg["signal_id"]
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "delete_failed"),
            result.get("error", "Delete failed"),
        )
        return
    connection.send_result(msg["id"], {
        "deleted": True,
        "device_removed": result.get("device_removed", False),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/clear",
    vol.Optional("source"): vol.Any("sniffed", "manual", None),
})
@websocket_api.async_response
async def ws_clear_unknowns(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Wipe unknown signals. Optional ``source`` scopes it to one tab."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    monitor.clear_all(msg.get("source"))
    connection.send_result(msg["id"], {"cleared": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/set-alias",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
    vol.Required("alias"): str,
})
@websocket_api.async_response
async def ws_set_signal_alias(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set or clear the alias on a signal (Clips). Empty clears it."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.set_signal_alias(
        msg["device_id"], msg["signal_id"], msg["alias"]
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "set_alias_failed"),
            result.get("error", "Failed to set alias"),
        )
        return
    connection.send_result(msg["id"], {"alias": result["alias"]})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/reorder",
    vol.Required("source"): vol.Any("sniffed", "manual"),
    vol.Required("device_ids"): [str],
})
@websocket_api.async_response
async def ws_reorder_unknown_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Reorder one tab's remotes (Sniffer or Clipper) to match the list."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    signal_store: SignalStore = data["signal_store"]
    try:
        signal_store.reorder_devices(msg["source"], list(msg["device_ids"]))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await signal_store.async_save()
    connection.send_result(msg["id"], {"reordered": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/reorder",
    vol.Required("device_id"): str,
    vol.Required("signal_ids"): [str],
})
@websocket_api.async_response
async def ws_reorder_unknown_signals(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Reorder the signals within one remote to match the id list."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    signal_store: SignalStore = data["signal_store"]
    device = signal_store.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Unknown device not found")
        return
    try:
        device.reorder_signals(list(msg["signal_ids"]))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await signal_store.async_save()
    connection.send_result(msg["id"], {"reordered": True})


# --- Plucker (vendor code import) ---


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/list-vendors",
})
@websocket_api.async_response
async def ws_pluck_list_vendors(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return candidate pluckable blasters per the two-stage discovery."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    registry = data.get("pluckable_registry", [])
    vendors = pluck.list_vendors(hass, registry)
    connection.send_result(msg["id"], {"vendors": vendors})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/run",
    vol.Required("integration"): str,
    vol.Required("vendor_entity_id"): str,
    vol.Required("appliance"): str,
    vol.Required("command_name"): str,
})
@websocket_api.async_response
async def ws_pluck_run(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Fire a vendor send service at the HAIR Tweezer and return captures.

    The payload is either ``{"signals": [...]}`` or
    ``{"error": code, "message": text}``; both go back as a normal result so
    the Pluck dialog can render the inline error states (vendor_error,
    no_response, unknown).
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    registry = data.get("pluckable_registry", [])
    vendor_entry = next(
        (e for e in registry if e.get("integration") == msg["integration"]),
        None,
    )
    if vendor_entry is None:
        connection.send_error(
            msg["id"],
            "unknown_vendor",
            "No pluckable is registered for that integration",
        )
        return
    result = await pluck.run_pluck(
        hass,
        entry_data=data,
        vendor_entry=vendor_entry,
        vendor_entity_id=msg["vendor_entity_id"],
        appliance=msg["appliance"].strip(),
        command_name=msg["command_name"].strip(),
    )
    connection.send_result(msg["id"], result)


# --- Clips (manual remotes / signals) ---


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/clip/create-remote",
    vol.Required("name"): str,
})
@websocket_api.async_response
async def ws_clip_create_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new clipped (manual) remote."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    name = msg["name"].strip()
    if not name:
        connection.send_error(msg["id"], "invalid_name", "Remote name is required")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    device = await monitor.create_manual_remote(name)
    connection.send_result(msg["id"], device.to_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/clip/create-signal",
    vol.Required("device_id"): str,
    vol.Required("pronto"): str,
    vol.Optional("alias", default=""): str,
})
@websocket_api.async_response
async def ws_clip_create_signal(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate and add a pasted Pronto signal to a clipped remote."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.create_manual_signal(
        msg["device_id"], msg["pronto"], msg.get("alias", "")
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "create_failed"),
            result.get("error", "Failed to create signal"),
        )
        return
    connection.send_result(msg["id"], {"signal": result["signal"]})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/edit-pronto",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
    vol.Required("pronto"): str,
    vol.Optional("alias"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_unknown_signal_edit_pronto(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Edit a stored signal's Pronto in place, re-evaluated as a capture."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.edit_signal_pronto(
        msg["device_id"], msg["signal_id"], msg["pronto"], msg.get("alias")
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "edit_failed"),
            result.get("error", "Failed to edit signal"),
        )
        return
    connection.send_result(
        msg["id"],
        {"signal": result["signal"], "triggers": result["triggers"]},
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/clip/validate-pronto",
    vol.Required("pronto"): str,
})
@websocket_api.async_response
async def ws_clip_validate_pronto(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate a Pronto string and return live feedback (no save)."""
    result = validate_pronto(msg["pronto"])
    # Surface the recognized protocol (NEC today) during the paste scan, so
    # the dialog can show "Recognized as NEC". Decode lives here, not in the
    # pure validator. infrared-protocols is imported once at setup, so this
    # is CPU-only on an already-loaded module.
    recognized: str | None = None
    if result.valid:
        from .ir_command import ProntoCommand
        from .protocol_decode import decode_to_fields

        try:
            raw = ProntoCommand(result.normalized).get_raw_timings()
        except Exception:
            raw = None
        recognized = decode_to_fields(raw)[0]
    connection.send_result(msg["id"], {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "frequency_khz": result.frequency_khz,
        "burst_pair_count": result.burst_pair_count,
        "normalized": result.normalized,
        "recognized_protocol": recognized,
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/update",
    vol.Required("device_id"): str,
    vol.Required("command_id"): str,
    vol.Optional("name"): str,
    vol.Optional("pronto"): str,
    vol.Optional("send_count"): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
})
@websocket_api.async_response
async def ws_command_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Edit a device command's name and/or Pronto in place.

    Persists through ``async_update_device`` so the known-command index
    rebuilds and entity hooks fire; rewires a bound trigger on an S/L
    fingerprint change and cascades action mappings on a rename.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    device_manager: DeviceManager = data["device_manager"]
    trigger_manager: TriggerManager = data["trigger_manager"]
    result = await device_manager.async_update_command(
        msg["device_id"],
        msg["command_id"],
        name=msg.get("name"),
        pronto=msg.get("pronto"),
        send_count=msg.get("send_count"),
        trigger_manager=trigger_manager,
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "update_failed"),
            result.get("error", "Failed to update command"),
        )
        return
    connection.send_result(msg["id"], {
        "command": result["command"],
        "triggers": result["triggers"],
        "mappings_updated": result["mappings_updated"],
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/snap-preview",
    vol.Required("pronto"): str,
    vol.Required("target_frequency"): int,
})
@websocket_api.async_response
async def ws_unknown_signal_snap_preview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Re-encode a Pronto at a standard carrier and return it (no save).

    Pure transform behind the editor's snap-to-standard action: validate the
    code, re-derive its timings, and re-encode at the requested standard. The
    user commits the staged result through the normal edit-pronto path.
    """
    result = validate_pronto(msg["pronto"])
    if not result.valid:
        connection.send_error(
            msg["id"],
            "invalid_pronto",
            result.errors[0] if result.errors else "Invalid Pronto code",
        )
        return
    target = msg["target_frequency"]
    if target not in IR_CARRIER_STANDARDS_HZ:
        connection.send_error(
            msg["id"], "invalid_target", "Target is not a standard carrier"
        )
        return

    from .ir_command import snap_pronto

    try:
        snapped = snap_pronto(result.normalized, target)
    except Exception as err:  # defensive: never leak a stack trace to the WS
        connection.send_error(msg["id"], "snap_failed", str(err))
        return
    connection.send_result(msg["id"], {
        "pronto": snapped,
        "frequency_khz": round(target / 1000, 1),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/clip/delete-remote",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_clip_delete_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a clipped (manual) remote."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.delete_manual_remote(msg["device_id"])
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "delete_failed"),
            result.get("error", "Failed to delete remote"),
        )
        return
    connection.send_result(msg["id"], {"deleted": True})


# --- Action Mapping ---


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/action-options",
    vol.Required("device_type"): str,
})
@websocket_api.async_response
async def ws_get_action_options(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the canonical action options for a device type."""
    options = get_action_options(msg["device_type"])
    connection.send_result(msg["id"], options)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/update-mapping",
    vol.Required("device_id"): str,
    vol.Required("command_name"): str,
    vol.Optional("action_key"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_update_mapping(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set or clear the action mapping for a command on a device.

    If ``action_key`` is provided, maps the command to that action.
    If ``action_key`` is None or absent, clears any existing mapping
    for that command.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    command_name = msg["command_name"]
    action_key = msg.get("action_key")
    mapping = device.entity_config.command_mapping

    # Clear any existing mapping that points to this command.
    for key, value in list(mapping.items()):
        if value.casefold() == command_name.casefold():
            del mapping[key]

    # If a new action_key is provided, also clear whatever was
    # previously mapped to that key (reassignment).
    if action_key:
        mapping.pop(action_key, None)
        mapping[action_key] = command_name

    await manager.async_update_device(device)
    connection.send_result(msg["id"], {
        "mapping": dict(mapping),
    })


# --- Triggers ---


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/triggers",
})
@websocket_api.async_response
async def ws_get_triggers(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return all triggers."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_result(msg["id"], [])
        return
    store = data["store"]
    triggers = store.get_all_triggers()
    connection.send_result(msg["id"], [t.to_dict() for t in triggers])


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger/create",
    vol.Required("name"): str,
    vol.Optional("signal_fingerprint", default=""): str,
    vol.Optional("protocol"): vol.Any(str, None),
    vol.Optional("code"): vol.Any(str, None),
    vol.Optional("min_hits", default=1): int,
    vol.Optional("source_device_id"): vol.Any(str, None),
    vol.Optional("source_command_id"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_create_trigger(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new trigger."""
    from .event_parser import EventParser

    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]

    sig_fp = msg.get("signal_fingerprint", "")
    protocol = msg.get("protocol")
    code = msg.get("code")

    # Auto-compute fingerprint from protocol+code when not provided.
    if not sig_fp and (protocol or code):
        sig_fp = EventParser.signal_fingerprint(protocol, code, None)

    # If a source command was given, derive fingerprint from that command.
    if not sig_fp and msg.get("source_command_id") and msg.get("source_device_id"):
        dm = data.get("device_manager")
        if dm:
            device = dm.get_device(msg["source_device_id"])
            if device:
                cmd = device.get_command(msg["source_command_id"])
                if cmd:
                    sig_fp = EventParser.signal_fingerprint(
                        cmd.protocol, cmd.code, cmd.raw_timings,
                    )
                    if not protocol:
                        protocol = cmd.protocol
                    if not code:
                        code = cmd.code

    if not sig_fp:
        connection.send_error(
            msg["id"], "missing_fingerprint",
            "Cannot compute signal fingerprint. Provide signal_fingerprint, "
            "protocol+code, or source_device_id+source_command_id."
        )
        return

    # Reject duplicate fingerprint.
    existing = store.get_trigger_by_fingerprint(sig_fp)
    if existing is not None:
        connection.send_error(
            msg["id"], "duplicate",
            f"A trigger already exists for this signal: {existing.name}"
        )
        return

    trigger = IRTrigger(
        name=msg["name"],
        signal_fingerprint=sig_fp,
        protocol=protocol,
        code=code,
        min_hits=msg.get("min_hits", 1),
        source_device_id=msg.get("source_device_id"),
        source_command_id=msg.get("source_command_id"),
    )
    store.add_trigger(trigger)
    await store.async_save()

    # Create the event entity.
    from .event import sync_trigger_entities

    entry_id = data["config_entry"].entry_id
    sync_trigger_entities(hass, entry_id, trigger=trigger)

    connection.send_result(msg["id"], trigger.to_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger/update",
    vol.Required("trigger_id"): str,
    vol.Optional("name"): str,
    vol.Optional("min_hits"): int,
    vol.Optional("enabled"): bool,
})
@websocket_api.async_response
async def ws_update_trigger(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update a trigger's name, min_hits, or enabled state."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    trigger = store.get_trigger(msg["trigger_id"])
    if trigger is None:
        connection.send_error(msg["id"], "not_found", "Trigger not found")
        return

    from datetime import UTC, datetime

    if "name" in msg:
        trigger.name = msg["name"]
    if "min_hits" in msg:
        trigger.min_hits = max(1, msg["min_hits"])
    if "enabled" in msg:
        trigger.enabled = msg["enabled"]
    trigger.updated_at = datetime.now(UTC).isoformat()

    store.update_trigger(trigger)
    await store.async_save()

    # Update event entity name if changed.
    entities = data.get("_trigger_entities", {})
    entity = entities.get(trigger.id)
    if entity is not None:
        entity.update_trigger(trigger)

    connection.send_result(msg["id"], trigger.to_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger/delete",
    vol.Required("trigger_id"): str,
})
@websocket_api.async_response
async def ws_delete_trigger(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a trigger."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    removed = store.remove_trigger(msg["trigger_id"])
    if not removed:
        connection.send_error(msg["id"], "not_found", "Trigger not found")
        return
    await store.async_save()

    # Remove the event entity.
    from .event import sync_trigger_entities

    entry_id = data["config_entry"].entry_id
    sync_trigger_entities(hass, entry_id, removed_id=msg["trigger_id"])

    connection.send_result(msg["id"], {"removed": True})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger/subscribe",
})
@websocket_api.async_response
async def ws_subscribe_triggers(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to real-time trigger fire events (for card glow)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return

    trigger_manager: TriggerManager = data["trigger_manager"]

    @callback
    def _on_trigger_fired(event_data: dict[str, Any]) -> None:
        connection.send_event(msg["id"], {
            "type": "trigger_fired",
            **event_data,
        })

    trigger_manager.subscribe(_on_trigger_fired)

    @callback
    def _on_disconnect() -> None:
        trigger_manager.unsubscribe(_on_trigger_fired)

    connection.subscriptions[msg["id"]] = _on_disconnect
    connection.send_result(msg["id"], {"subscribed": True})
