"""WebSocket API for HAIR frontend communication."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

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
    EVENT_SIGNAL_UPDATED,
    FITTING_LISTEN_TIMEOUT_S,
    MAX_DITTO_COUNT,
    MAX_SEND_COUNT,
    MIRROR_DEVICE_FP,
    WS_PREFIX,
    CaptureState,
    CommandCategory,
    CommandSource,
    DeviceType,
)
from .device_manager import DeviceManager, category_for_command_name
from .frequency_standards import IR_CARRIER_STANDARDS_HZ
from .identity import (
    SignalIdentity,
    canonical_byte_hash,
    canonical_fingerprint,
)
from .models import IRDevice, IRTrigger, TriggerRemote
from .pronto_validator import validate_pronto
from .signal_monitor import SignalMonitor
from .signal_store import SignalStore
from .trigger_manager import TriggerManager
from .wig_format import VERDICTS

_LOGGER = logging.getLogger(__name__)


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket commands.

    Idempotent -- registering the same command twice is harmless because
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

    # Matrix device detail (Cold Cuts second half)
    websocket_api.async_register_command(hass, ws_device_matrix_cells)
    websocket_api.async_register_command(hass, ws_device_matrix_send)
    websocket_api.async_register_command(hass, ws_device_matrix_command)
    # The hear side of the same lattice (signpost 4, Track M)
    websocket_api.async_register_command(hass, ws_trigger_remote_matrix_cells)
    websocket_api.async_register_command(hass, ws_trigger_remote_matrix_cell)

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
    websocket_api.async_register_command(hass, ws_pluck_create_blaster)
    websocket_api.async_register_command(hass, ws_pluck_create_signal)
    websocket_api.async_register_command(hass, ws_pluck_delete_blaster)
    websocket_api.async_register_command(hass, ws_pluck_stores_list)
    websocket_api.async_register_command(hass, ws_pluck_stores_import)
    websocket_api.async_register_command(hass, ws_pluck_stores_forget)
    websocket_api.async_register_command(hass, ws_clip_create_signal)
    websocket_api.async_register_command(hass, ws_signal_set_tx_force_raw)
    websocket_api.async_register_command(hass, ws_unknown_signal_edit_pronto)
    websocket_api.async_register_command(hass, ws_unknown_signal_snap_preview)
    websocket_api.async_register_command(hass, ws_clip_validate_pronto)
    websocket_api.async_register_command(hass, ws_clip_delete_remote)
    websocket_api.async_register_command(hass, ws_delete_sniffed_remote)

    # Code database picker (Add Remote)
    websocket_api.async_register_command(hass, ws_codes_get_brands)
    websocket_api.async_register_command(hass, ws_codes_import_remote)

    # Wigs (the closet)
    websocket_api.async_register_command(hass, ws_wigs_list)
    websocket_api.async_register_command(hass, ws_wigs_upload)
    websocket_api.async_register_command(hass, ws_wigs_delete)
    websocket_api.async_register_command(hass, ws_wigs_supersede)
    websocket_api.async_register_command(hass, ws_wigs_get)
    websocket_api.async_register_command(hass, ws_wigs_claims)
    websocket_api.async_register_command(hass, ws_wigs_update)
    websocket_api.async_register_command(hass, ws_command_listen)
    websocket_api.async_register_command(hass, ws_wigs_save_plan)
    websocket_api.async_register_command(hass, ws_wigs_save)
    websocket_api.async_register_command(hass, ws_wigs_comb)
    # Add Popups signpost 2, Track 3: Closet-tab signal identities
    # for the Add Trigger Remote dialog's seeding loop.
    websocket_api.async_register_command(hass, ws_wig_signals)

    # Fitting (Perfect Fit)
    websocket_api.async_register_command(hass, ws_wig_make_device)
    websocket_api.async_register_command(hass, ws_trigger_remote_make_device)
    websocket_api.async_register_command(hass, ws_wig_snapshot)
    websocket_api.async_register_command(hass, ws_wig_render)

    # Action mapping
    websocket_api.async_register_command(hass, ws_get_action_options)
    websocket_api.async_register_command(hass, ws_update_mapping)
    websocket_api.async_register_command(hass, ws_device_star)

    # Triggers
    websocket_api.async_register_command(hass, ws_get_triggers)
    websocket_api.async_register_command(hass, ws_create_trigger)
    websocket_api.async_register_command(hass, ws_update_trigger)
    websocket_api.async_register_command(hass, ws_delete_trigger)
    websocket_api.async_register_command(hass, ws_subscribe_triggers)
    websocket_api.async_register_command(hass, ws_reorder_triggers)
    websocket_api.async_register_command(hass, ws_get_trigger_drawer)
    websocket_api.async_register_command(hass, ws_rename_trigger_drawer)

    # Trigger Remotes (Add Popups signpost 2, Track 1B-B2/B3)
    websocket_api.async_register_command(hass, ws_list_trigger_remotes)
    websocket_api.async_register_command(hass, ws_create_trigger_remote)
    websocket_api.async_register_command(hass, ws_wig_make_remote)
    websocket_api.async_register_command(hass, ws_device_make_remote)
    websocket_api.async_register_command(hass, ws_rename_trigger_remote)
    websocket_api.async_register_command(hass, ws_delete_trigger_remote)
    websocket_api.async_register_command(hass, ws_duplicate_trigger_remote)
    websocket_api.async_register_command(hass, ws_pin_trigger_remote_device)
    websocket_api.async_register_command(hass, ws_unpin_trigger_remote_device)
    websocket_api.async_register_command(hass, ws_set_trigger_remote_receiver_scope)


def _get_first_entry_data(hass: HomeAssistant) -> dict[str, Any] | None:
    """Return the first entry's hass.data for HAIR.

    HAIR is a hub integration with at most one entry per HA instance.
    """
    entries = hass.data.get(DOMAIN, {})
    for value in entries.values():
        if isinstance(value, dict) and "device_manager" in value:
            return value
    return None


def _ha_device_id(hass: HomeAssistant, device: IRDevice) -> str | None:
    """Resolve this IR device's HA device-registry id, if it has one.

    Feeds the exit-to-entity link (docs/internal/plans/exit-to-entity-
    link.md): the frontend renders no glyph at all when this is None,
    since there is nowhere in HA to send the user. Same identifier
    tuple every entity platform's own device_info already registers
    under -- (DOMAIN, device.id), see e.g. switch.py's device_info.
    """
    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(identifiers={(DOMAIN, device.id)})
    return ha_device.id if ha_device is not None else None


def _device_summary(device: IRDevice, hass: HomeAssistant) -> dict[str, Any]:
    return {
        "id": device.id,
        "name": device.name,
        "device_type": str(device.device_type),
        "manufacturer": device.manufacturer,
        "model": device.model,
        "emitter_entity_ids": list(device.emitter_entity_ids),
        "power_sensor_entity_id": device.power_sensor_entity_id,
        "power_off_below_w": device.power_off_below_w,
        "power_on_above_w": device.power_on_above_w,
        "temperature_sensor_entity_id": device.temperature_sensor_entity_id,
        "humidity_sensor_entity_id": device.humidity_sensor_entity_id,
        "command_count": len(device.commands),
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        "ha_device_id": _ha_device_id(hass, device),
    }


async def _device_full(
    hass: HomeAssistant, device: IRDevice
) -> dict[str, Any]:
    full = device.to_dict()
    full["command_count"] = len(device.commands)
    full["ha_device_id"] = _ha_device_id(hass, device)
    # The matrix summary rides the full payload (owner ruling
    # 2026-07-28) so the device page renders its state-matrix card
    # without a second round trip. Loading goes through the manager's
    # cache exactly like the climate entity's own load; any miss
    # (no manager, no file, unreadable file) is an honest null, the
    # same shape non-matrix devices carry.
    full["matrix"] = None
    if device.climate_matrix:
        data = _get_first_entry_data(hass)
        manager = data.get("device_manager") if data else None
        if manager is not None:
            matrix = await manager.async_get_matrix(device.id)
            if matrix is not None:
                from .wig_climate import matrix_summary

                full["matrix"] = matrix_summary(matrix)
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
    connection.send_result(msg["id"], await _device_full(hass, device))


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
    vol.Optional("promoted_from_unknown_id"): vol.Any(str, None),
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

    # Make HAIR Device (v0.7.0): the whole remote becomes the device.
    # Copy every catalog signal in as a command (owner ruling -- promote
    # no longer creates an empty shell), auto-map the lot so entity
    # features light up, and stamp the identity link so the linked chip
    # survives renames on either side.
    source_unknown = msg.get("promoted_from_unknown_id")
    if source_unknown:
        monitor: SignalMonitor = data["signal_monitor"]
        copy = await monitor.copy_signals_to_device(
            source_unknown, device.id
        )
        if copy.get("success") and copy.get("copied"):
            for command in device.commands:
                manager._auto_map_command(device, command)
            await manager.async_update_device(device)
        await monitor.mark_promoted(source_unknown, device.id)

    connection.send_result(msg["id"], await _device_full(hass, device))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/update",
    vol.Required("device_id"): str,
    vol.Optional("name"): str,
    vol.Optional("manufacturer"): vol.Any(str, None),
    vol.Optional("model"): vol.Any(str, None),
    vol.Optional("emitter_entity_ids"): [str],
    vol.Optional("device_type"): str,
    vol.Optional("power_sensor_entity_id"): vol.Any(str, None),
    vol.Optional("power_off_below_w"): vol.Any(vol.Coerce(float), None),
    vol.Optional("power_on_above_w"): vol.Any(vol.Coerce(float), None),
    vol.Optional("temperature_sensor_entity_id"): vol.Any(str, None),
    vol.Optional("humidity_sensor_entity_id"): vol.Any(str, None),
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
        # TYPE LOCK (matrix-power-row.md item 4, ruled 2026-08-08): the
        # type is load-bearing wiring on a matrix device, not a label --
        # entity_factory.DEVICE_TYPE_TO_PLATFORM is what mints the
        # climate entity the lattice exists to drive, keyed off exactly
        # this field. Flipping an air conditioner to "fan" here would
        # tear that entity down mid-automation and orphan the cells; no
        # legitimate journey ends there, since a matrix only ever
        # arrives through a climate import or capture. The frontend
        # already replaces the type dropdown with a static label on a
        # matrix device (item 4); this is the belt to that belt's
        # braces, so a stale client can't do what the current UI no
        # longer offers.
        if device.climate_matrix:
            connection.send_error(
                msg["id"],
                "invalid_format",
                "Device type is fixed by its state matrix",
            )
            return
        device.device_type = DeviceType(msg["device_type"])

    # Power monitoring fields validate together before anything is
    # written to ``device``: a bad sensor id or a bad threshold
    # ordering must not leave the live object half-mutated.
    if any(
        key in msg
        for key in (
            "power_sensor_entity_id",
            "power_off_below_w",
            "power_on_above_w",
        )
    ):
        new_sensor = msg.get(
            "power_sensor_entity_id", device.power_sensor_entity_id
        )
        if new_sensor is not None and not new_sensor.startswith("sensor."):
            connection.send_error(
                msg["id"],
                "invalid_format",
                "power_sensor_entity_id must be a sensor entity",
            )
            return
        if new_sensor is None:
            # Thresholds without a sensor are meaningless.
            new_off_below = None
            new_on_above = None
        else:
            new_off_below = msg.get(
                "power_off_below_w", device.power_off_below_w
            )
            new_on_above = msg.get(
                "power_on_above_w", device.power_on_above_w
            )
        if (
            new_off_below is not None
            and new_on_above is not None
            and new_on_above < new_off_below
        ):
            connection.send_error(
                msg["id"],
                "invalid_format",
                "power_on_above_w must be at or above power_off_below_w",
            )
            return
        device.power_sensor_entity_id = new_sensor
        device.power_off_below_w = new_off_below
        device.power_on_above_w = new_on_above

    # Climate room sensors validate together too, same "nothing
    # half-mutated on a rejected request" reasoning as the power
    # block above -- but unlike power, the two are NOT a coupled
    # group: each keeps whatever value it already had when the other
    # one is the only key present in msg, so setting or clearing one
    # never disturbs the other.
    if any(
        key in msg
        for key in (
            "temperature_sensor_entity_id",
            "humidity_sensor_entity_id",
        )
    ):
        new_temp_sensor = msg.get(
            "temperature_sensor_entity_id",
            device.temperature_sensor_entity_id,
        )
        new_humidity_sensor = msg.get(
            "humidity_sensor_entity_id", device.humidity_sensor_entity_id
        )
        if new_temp_sensor is not None and not new_temp_sensor.startswith(
            "sensor."
        ):
            connection.send_error(
                msg["id"],
                "invalid_format",
                "temperature_sensor_entity_id must be a sensor entity",
            )
            return
        if new_humidity_sensor is not None and not new_humidity_sensor.startswith(
            "sensor."
        ):
            connection.send_error(
                msg["id"],
                "invalid_format",
                "humidity_sensor_entity_id must be a sensor entity",
            )
            return
        device.temperature_sensor_entity_id = new_temp_sensor
        device.humidity_sensor_entity_id = new_humidity_sensor

    await manager.async_update_device(device)
    connection.send_result(msg["id"], await _device_full(hass, device))


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
    # The echo hook behind the TEST button's SENT . HEARD reading. The
    # Mirror already attributes this send's own loopback; waiting on it
    # briefly turns that into an answer the button can show. A send that
    # nothing hears is still a send -- heard is a bonus fact, never a
    # condition -- so a timeout reports heard=false rather than failing.
    import asyncio

    from .wig_fitting import FITTING_HEARD_WAIT_S

    heard_future: asyncio.Future[str | None] = (
        asyncio.get_running_loop().create_future()
    )
    try:
        await manager.async_send_command(
            msg["device_id"], msg["command_id"], heard_future=heard_future,
        )
    except KeyError as err:
        heard_future.cancel()
        connection.send_error(msg["id"], "not_found", str(err))
        return
    except Exception as err:
        heard_future.cancel()
        _LOGGER.error("Send command failed: %s", err, exc_info=True)
        connection.send_error(msg["id"], "send_failed", str(err))
        return

    receiver: str | None = None
    try:
        receiver = await asyncio.wait_for(
            heard_future, FITTING_HEARD_WAIT_S
        )
        heard = True
    except (TimeoutError, asyncio.CancelledError):
        heard_future.cancel()
        heard = False
    connection.send_result(
        msg["id"], {"sent": True, "heard": heard, "receiver": receiver}
    )


def _porthole_cell(
    manager: DeviceManager, device_id: str, command_id: str
) -> dict[str, Any] | None:
    """The lattice coordinates behind a command row, or None.

    None means an ordinary command, which is every row on a device that
    is not a matrix and every row on a matrix device except the handful
    the comb doubted.
    """
    device = manager.get_device(device_id)
    if device is None:
        return None
    command = device.get_command(command_id)
    if command is None:
        return None
    return command.matrix_cell or None


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
    # Capture the removed command's signal fingerprint before deletion so we
    # can notify other browser tabs that this signal's assignment set changed
    # (v0.5.7 hair_signal_updated: refreshes the green Assign badge live).

    sig_fp: str | None = None
    device = manager.get_device(msg["device_id"])
    if device is not None:
        cmd = device.get_command(msg["command_id"])
        if cmd is not None:
            sig_fp = canonical_fingerprint(
                cmd.protocol, cmd.code, cmd.raw_timings
            )
    # The row is a porthole, so deleting it deletes the CELL. Sparse
    # lattices are already legal, so what is left is a working matrix
    # that simply stops offering that state.
    cell = _porthole_cell(manager, msg["device_id"], msg["command_id"])
    if cell is not None:
        await manager.async_delete_cell(msg["device_id"], cell)

    removed = await manager.async_remove_command(
        msg["device_id"], msg["command_id"]
    )
    if not removed:
        connection.send_error(msg["id"], "not_found", "Command not found")
        return
    if sig_fp:
        hass.bus.async_fire(EVENT_SIGNAL_UPDATED, {"signal_fingerprint": sig_fp})
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
    if source.climate_matrix:
        # The matrix file rides along under the clone's id (Cold Cuts)
        # BEFORE the device exists, so the climate entity created below
        # never races a missing file. A failed copy clears the flag:
        # a device claiming a matrix it does not have would leave the
        # entity permanently refusing sends with no visible reason.
        from .matrix_store import copy_matrix

        copied = await hass.async_add_executor_job(
            copy_matrix, hass.config.config_dir, source.id, clone.id
        )
        if not copied:
            clone.climate_matrix = False
    await manager.async_create_device(clone)
    connection.send_result(msg["id"], await _device_full(hass, clone))


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
    connection.send_result(msg["id"], await _device_full(hass, device))


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
    # Decode at save so a captured NEC command transmits canonical timings on
    # the first press (mirrors the catalog-signal capture pipeline). Also sets
    # byte_hash at creation: the matcher's reverse index keys on
    # (fingerprint, byte_hash), and since v0.5.8 the hash is identity, not
    # just a tiebreaker. (A load-time backfill exists for pre-0.3.4 records,
    # but a freshly captured command should not need it.) Both fields default
    # to None on undecodable / non-Pronto captures.
    from .protocol_decode import try_decode_identity

    identity = try_decode_identity(result.raw_timings)
    command.decoded_protocol = identity.protocol if identity else None
    command.decoded_address = identity.address if identity else None
    command.decoded_command = identity.command if identity else None
    command.decoded_fingerprint = identity.fingerprint if identity else None
    command.decoded_extras = (
        dict(identity.extras) if identity and identity.extras else None
    )
    command.byte_hash = canonical_byte_hash(result.code)
    await manager.async_add_command(device.id, command)
    # Notify other tabs this signal now has an assignment (v0.5.7).
    save_fp = canonical_fingerprint(
        command.protocol, command.code, command.raw_timings
    )
    if save_fp:
        hass.bus.async_fire(EVENT_SIGNAL_UPDATED, {"signal_fingerprint": save_fp})
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

        from .receiver_filter import is_rf_receiver

        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        entity_ids = async_get_receivers(hass)
        for entity_id in entity_ids:
            if is_rf_receiver(hass, entity_id):
                # GH #72: never subscribed, so never offered in the
                # receiver picker either.
                continue
            state = hass.states.get(entity_id)
            name = entity_id
            if state is not None:
                name = state.attributes.get("friendly_name", entity_id)
            # Prefer the owning device's own name over the entity's
            # friendly_name, which HA auto-composes as "<device name>
            # <entity name>" (e.g. "Anthem RF IR remote 1 IR Proxy
            # Receiver") -- accurate, but not what a user picking a
            # receiver from a short list wants to read (owner bench
            # catch 2026-08-14).
            entry = entity_registry.async_get(entity_id)
            if entry is not None and entry.device_id is not None:
                device = device_registry.async_get(entry.device_id)
                if device is not None:
                    name = device.name_by_user or device.name or name
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

    ``has_receivers`` is False when no native receiver is currently
    subscribed and no ESPHome bridge has fired this session, which means
    "no receiver is set up" rather than "no signals seen yet". Receivers
    are tracked dynamically (v0.5.8 hot-plug), so this can flip to True
    without a reload; known cosmetic limitation: the frontend fetches it
    on load only, so after a hot-plug the empty state persists until a
    tab refresh -- and once a signal actually arrives, the device-count
    gate bypasses the empty state anyway.
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
    """Return the picker tree (brand -> codebook -> function): installed
    infrared-protocols codebooks intermixed with local wigs from the
    closet, each codebook tagged ``source: "library" | "local"`` so the
    picker can dot provenance without splitting the alphabet."""
    from .code_library import get_combined_tree

    # Walks the codebook package on disk, imports modules, and scans the
    # wig folder, so it is offloaded to the executor.
    tree = await hass.async_add_executor_job(
        get_combined_tree, hass.config.config_dir
    )
    connection.send_result(msg["id"], tree)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/codes/import-remote",
    vol.Required("codebook_id"): vol.All(str, vol.Length(max=200)),
    vol.Optional("name"): vol.All(str, vol.Length(max=200)),
    vol.Optional("function_ids"): [vol.All(str, vol.Length(max=200))],
    # Cold Cuts second half (2026-07-29): the gated matrix clip. Only
    # meaningful for wig ids whose wig carries a climate block; the
    # gate defaults closed so 2,689 Clipper rows are always an explicit
    # choice.
    vol.Optional("include_matrix", default=False): bool,
})
@websocket_api.async_response
async def ws_codes_import_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Materialize a codebook OR a local wig into a clipped remote, one
    signal per function, each aliased to its function name and (when the
    code decodes) pre-populated with its protocol identity for canonical
    transmit. Wig imports decode FRESH here (raw-first contract) and
    collapse onto an existing same-named clipped remote instead of
    minting a twin (wigs.md section 6). With ``include_matrix`` a
    matrix wig's cells and power codes come along, named by the display
    grammar, and the remote is stamped with wig provenance for the
    adopt signpost (owner ruling CC5)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    from .code_library import (
        codebook_label,
        materialize_codebook,
        materialize_wig,
        parse_wig_id,
    )

    source_wig: dict[str, Any] | None = None
    wig_filename = parse_wig_id(msg["codebook_id"])
    if wig_filename is not None:
        from .wig_store import load_wig

        include_matrix = msg.get("include_matrix", False)
        # Mint-time naming (unit ruling 2026-07-29): clipped cell
        # names freeze in the install's unit as of THIS moment.
        from .wig_climate import unit_letter

        display_unit = unit_letter(hass.config.units.temperature_unit)
        # Both calls do file I/O and fresh decode; off the event loop.
        entries = await hass.async_add_executor_job(
            materialize_wig,
            hass.config.config_dir,
            msg["codebook_id"],
            msg.get("function_ids"),
            include_matrix,
            display_unit,
        )
        wig = await hass.async_add_executor_job(
            load_wig, hass.config.config_dir, wig_filename
        )
        default_name = wig.name if wig else "Imported Remote"
        merge = True
        if include_matrix and wig is not None and wig.climate is not None:
            from .wig_format import cells_content_hash

            # The stamp the adopt signpost resolves at list time
            # (owner ruling CC5): filename for the cheap check, cells
            # hash for the rename-safe fallback. Hashing a worst-case
            # matrix serializes megabytes; executor, not loop.
            cells_hash = await hass.async_add_executor_job(
                cells_content_hash, wig.climate
            )
            source_wig = {
                "filename": wig_filename,
                "cells_hash": cells_hash,
            }
    else:
        # materialize_codebook imports library modules from disk; keep it
        # off the event loop.
        entries = await hass.async_add_executor_job(
            materialize_codebook, msg["codebook_id"], msg.get("function_ids")
        )
        default_name = codebook_label(msg["codebook_id"]) or "Imported Remote"
        merge = False
    if not entries:
        connection.send_error(
            msg["id"], "no_codes", "No usable codes for that selection"
        )
        return
    monitor: SignalMonitor = data["signal_monitor"]
    name = msg.get("name") or default_name
    result = await monitor.import_manual_remote(
        name, entries, merge_existing=merge, source_wig=source_wig
    )
    connection.send_result(msg["id"], result)


# --- Signal Monitor (Unknown Devices) ---


def _assignment_index(
    hair_devices: list[IRDevice],
) -> list[tuple[SignalIdentity, dict[str, str]]]:
    """List every HAIR command as ``(identity, assignment payload)``.

    A catalog signal is "assigned" when a HAIR device command re-encodes to
    the same identity. ``IRCommand`` carries no stored fingerprint, so it is
    computed here exactly as ``storage._rebuild_command_index`` does. The
    payload is structured (v0.6.6, assigned popover): ``device_id`` and
    ``command_id`` give the frontend a click-through navigation target,
    ``device_name`` / ``command_name`` render the popover rows. (Pre-0.6.6
    this was a bare ``"<device>.<command>"`` tooltip string.)

    Tiered identity (v0.5.8 unified identity): matching is the exact
    pairwise rule via ``SignalIdentity.same_as`` in
    ``_augment_signals_with_assignments`` -- a linear scan rather than a
    dict, because the deciding tier depends on which layers BOTH sides
    carry, which no single-key index expresses (a hash-only capture must
    still reach a decoded command at tier 2 across a Sony fingerprint
    flip). Command counts are small and this runs on the per-device fetch,
    so the scan is cheap; correctness of the dot beats micro-optimization.
    """

    entries: list[tuple[SignalIdentity, dict[str, str]]] = []
    for device in hair_devices:
        for command in device.commands:
            # Per-command resilience (GH #108): one unreadable command
            # used to abort this walk, and with it the Sniffer list, the
            # wig list and every page that shows an assignment dot.
            try:
                fp = canonical_fingerprint(
                    command.protocol, command.code, command.raw_timings
                )
            except Exception:
                _LOGGER.warning(
                    "Skipping command '%s' (%s) on device '%s' (%s) while "
                    "building the assignment index: its identity could not "
                    "be computed from its stored code",
                    getattr(command, "name", "?"),
                    getattr(command, "id", "?"),
                    getattr(device, "name", "?"),
                    getattr(device, "id", "?"),
                )
                continue
            if not fp:
                continue
            entries.append((
                SignalIdentity(
                    command.decoded_fingerprint, command.byte_hash, fp
                ),
                {
                    "device_id": device.id,
                    "device_name": device.name,
                    "command_id": command.id,
                    "command_name": command.name,
                },
            ))
    return entries


def _augment_signals_with_assignments(
    device_dict: dict[str, Any],
    assignment_index: list[tuple[SignalIdentity, dict[str, str]]],
) -> None:
    """Annotate each serialized signal with its assignment count + list.

    Mutates ``device_dict['signals']`` in place, adding ``assignment_count``
    and ``assigned_to`` (dots polish, v0.5.7; structured payloads for the
    assigned popover as of v0.6.6). Matching is the tiered
    identity rule (v0.5.8 unified identity, ``SignalIdentity.same_as``):
    assigning one sub-threshold button (Sony et al) lights the green dot
    on that row only, and the dot survives the row's coarse fingerprint
    flipping across the classification boundary, matching the trigger and
    known-command matchers.
    """
    from .identity import SignalIdentity

    for sig in device_dict.get("signals", []):
        ident = SignalIdentity(
            sig.get("decoded_fingerprint"),
            sig.get("byte_hash"),
            sig.get("fingerprint") or "",
        )
        assigned = [
            label
            for cmd_ident, label in assignment_index
            if ident.same_as(cmd_ident)
        ]
        sig["assignment_count"] = len(assigned)
        sig["assigned_to"] = assigned


def _linked_hair_devices(
    device,
    assignment_index: list[tuple[SignalIdentity, dict[str, str]]],
    hair_by_id: dict[str, Any],
) -> list[dict[str, str]]:
    """The HAIR devices this catalog remote feeds, by identity.

    Union of the stored promote link (resolved live by id, so renames
    on either side never break it -- the GH promote-rename anomaly) and
    every device any of the remote's signals is assigned into (the
    many-to-many truth: one universal remote can feed several HAIR
    devices). Deleted devices drop out naturally because resolution
    fails.
    """
    linked: dict[str, str] = {}
    if device.promoted_to:
        target = hair_by_id.get(device.promoted_to)
        if target is not None:
            linked[target.id] = target.name
    for sig in device.signals:
        identity = SignalIdentity(
            sig.decoded_fingerprint, sig.byte_hash, sig.fingerprint
        )
        for entry_identity, payload in assignment_index:
            if identity.same_as(entry_identity):
                linked[payload["device_id"]] = payload["device_name"]
    return [
        {"device_id": did, "device_name": name}
        for did, name in linked.items()
    ]


def _trigger_assignment_index(
    triggers: list[IRTrigger],
    remotes_by_id: dict[str, TriggerRemote],
) -> list[tuple[SignalIdentity, dict[str, str]]]:
    """List every named-remote trigger as ``(identity, remote payload)``.

    The trigger-side sibling of ``_assignment_index`` (signpost 3,
    Track 2 item 4 / item 0.1's "remote half" of the combined USE-dot
    count). Unlike ``IRCommand``, ``IRTrigger`` already stores its
    identity fields (``signal_fingerprint`` / ``byte_hash`` /
    ``decoded_fingerprint``) at creation, so no ``EventParser`` recompute
    is needed here. Drawer-owned triggers (``trigger_remote_id is None``)
    are excluded -- the HAIR Triggers drawer is not a Remote, and a
    catalog remote or wig already showing linked there would otherwise
    double-count it under the combined dot.
    """
    entries: list[tuple[SignalIdentity, dict[str, str]]] = []
    for trig in triggers:
        if not trig.trigger_remote_id:
            continue
        remote = remotes_by_id.get(trig.trigger_remote_id)
        if remote is None:
            continue
        entries.append((
            SignalIdentity(
                trig.decoded_fingerprint, trig.byte_hash,
                trig.signal_fingerprint,
            ),
            {"remote_id": remote.id, "remote_name": remote.name},
        ))
    return entries


def _linked_hair_remotes(
    device,
    trigger_index: list[tuple[SignalIdentity, dict[str, str]]],
    remotes_by_id: dict[str, TriggerRemote],
) -> list[dict[str, str]]:
    """The named Remotes this catalog remote feeds, by identity.

    The remote-side sibling of ``_linked_hair_devices`` (signpost 3,
    Track 2 item 4). Same union shape: the stored promote link
    (``UnknownDevice.promoted_to_remote``, resolved live by id so a
    rename on either side never breaks it -- the GH promote-rename
    anomaly, remote half) plus every named Remote any of this catalog
    remote's signals is assigned into as a trigger.
    """
    linked: dict[str, str] = {}
    if device.promoted_to_remote:
        target = remotes_by_id.get(device.promoted_to_remote)
        if target is not None:
            linked[target.id] = target.name
    for sig in device.signals:
        identity = SignalIdentity(
            sig.decoded_fingerprint, sig.byte_hash, sig.fingerprint
        )
        for entry_identity, payload in trigger_index:
            if identity.same_as(entry_identity):
                linked[payload["remote_id"]] = payload["remote_name"]
    return [
        {"remote_id": rid, "remote_name": name}
        for rid, name in linked.items()
    ]


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
        "source_wig": dict(device.source_wig) if device.source_wig else None,
    }


def _resolve_source_wig_states(
    config_dir: str, stamps: list[dict[str, Any]]
) -> list[tuple[str, str | None]]:
    """Resolve clip stamps against the closet: present/renamed/gone.

    The adopt signpost's live check (owner ruling CC5, 2026-07-29),
    rename-safe by design: filename first (one cheap directory glob,
    no parsing), then ``cells_content_hash`` over the closet's PARSED
    matrix wigs -- a wig the user renamed still points home because
    its cells did not change. Anything else is honestly "gone".

    Blocking file I/O; callers run this on the executor. The hash
    index is built lazily and at most once per call, so a list where
    every stamped file still exists never parses a single wig.
    """
    from .wig_format import WIG_SUFFIX, cells_content_hash
    from .wig_store import scan_wigs, wigs_dir

    directory = wigs_dir(config_dir)
    names: set[str] = set()
    if directory.is_dir():
        names = {p.name for p in directory.glob(f"*{WIG_SUFFIX}")}
    hash_index: dict[str, str] | None = None
    out: list[tuple[str, str | None]] = []
    for stamp in stamps:
        filename = stamp.get("filename")
        if filename and filename in names:
            out.append(("present", filename))
            continue
        if hash_index is None:
            hash_index = {}
            for loaded in scan_wigs(config_dir).wigs:
                if loaded.wig.climate is None:
                    continue
                # setdefault: on a hash tie the name-sorted scan's
                # first file wins, deterministically.
                hash_index.setdefault(
                    cells_content_hash(loaded.wig.climate),
                    loaded.path.name,
                )
        renamed = hash_index.get(stamp.get("cells_hash") or "")
        if renamed is not None:
            out.append(("renamed", renamed))
        else:
            out.append(("gone", None))
    return out


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/devices",
    vol.Optional("include_dismissed", default=False): bool,
    vol.Optional("min_hits"): vol.Any(int, None),
    # "echo" serves the Mirror tab its synthetic device (v0.6.6). The
    # clear and reorder commands deliberately do NOT accept "echo": the
    # Mirror is a log -- it has no clear-all and no manual order.
    vol.Optional("source"): vol.Any(
        "sniffed", "manual", "plucked", "echo", None
    ),
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
    store = data.get("store")
    hair_devices = store.get_all_devices() if store else []
    index = _assignment_index(hair_devices)
    hair_by_id = {d.id: d for d in hair_devices}
    # Item 0.1's remote half: same shape, trigger-remote side.
    trigger_remotes = store.get_all_trigger_remotes() if store else []
    remotes_by_id = {r.id: r for r in trigger_remotes}
    all_triggers = store.get_all_triggers() if store else []
    trigger_index = _trigger_assignment_index(all_triggers, remotes_by_id)
    summaries = []
    for d in devices:
        summary = _unknown_device_summary(d)
        # ONE combined, kind-tagged list (owner ruling, coding-plan.md
        # section 0 item 1): no per-kind split in the payload shape for
        # the UI to un-merge.
        summary["linked_devices"] = [
            {**entry, "kind": "device"}
            for entry in _linked_hair_devices(d, index, hair_by_id)
        ] + [
            {**entry, "kind": "remote"}
            for entry in _linked_hair_remotes(d, trigger_index, remotes_by_id)
        ]
        summaries.append(summary)
    # Adopt signpost (Cold Cuts second half, owner ruling CC5):
    # resolve wig provenance ONLY for remotes carrying the clip stamp,
    # so the everyday list call pays nothing. File I/O on the executor.
    stamped = [
        (i, d.source_wig)
        for i, d in enumerate(devices)
        if d.source_wig
    ]
    if stamped:
        states = await hass.async_add_executor_job(
            _resolve_source_wig_states,
            hass.config.config_dir,
            [stamp for _i, stamp in stamped],
        )
        for (i, _stamp), (state, filename) in zip(
            stamped, states, strict=True
        ):
            summaries[i]["source_wig_state"] = state
            if filename is not None:
                summaries[i]["source_wig_filename"] = filename
    connection.send_result(msg["id"], summaries)


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
    result = device.to_dict()
    # Annotate each signal with its HAIR-command assignment count for the green
    # Assign dot (dots polish, v0.5.7). Non-critical enrichment: if the HAIR
    # store is not wired, the signals simply carry no assignment info.
    store = data.get("store")
    if store is not None:
        _augment_signals_with_assignments(
            result, _assignment_index(store.get_all_devices())
        )
    connection.send_result(msg["id"], result)


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
    vol.Optional("send_count"): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
    vol.Optional("repeat_count"): vol.All(
        int, vol.Range(min=0, max=MAX_DITTO_COUNT)
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
        send_count=msg.get("send_count"),
        repeat_count=msg.get("repeat_count"),
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
    vol.Optional("send_count"): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
    vol.Optional("repeat_count"): vol.All(
        int, vol.Range(min=0, max=MAX_DITTO_COUNT)
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
        send_count=msg.get("send_count"),
        repeat_count=msg.get("repeat_count"),
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
    vol.Optional("source"): vol.Any("sniffed", "manual", "plucked", None),
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
    vol.Required("source"): vol.Any("sniffed", "manual", "plucked"),
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
    # The Devices tab's Blasters section shows both kinds of source: the
    # replay-capable hardware discovered above, and the learned-code
    # stores this install has actually plucked. The second half is a
    # record, not a device, so it comes from the catalog store rather
    # than from discovery.
    signal_store: SignalStore = data["signal_store"]
    connection.send_result(
        msg["id"],
        {
            "vendors": vendors,
            "plucked_stores": signal_store.get_plucked_stores(),
        },
    )


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


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/create-blaster",
    vol.Required("vendor_entity_id"): str,
    vol.Required("appliance"): str,
    vol.Required("name"): str,
})
@websocket_api.async_response
async def ws_pluck_create_blaster(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a plucked blaster (vendor entity + appliance, both required)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    vendor_entity_id = msg["vendor_entity_id"].strip()
    appliance = msg["appliance"].strip()
    name = msg["name"].strip()
    if not vendor_entity_id or not appliance:
        connection.send_error(
            msg["id"], "invalid_input", "Vendor entity and appliance are required"
        )
        return
    monitor: SignalMonitor = data["signal_monitor"]
    device = await monitor.create_plucked_blaster(vendor_entity_id, appliance, name)
    connection.send_result(msg["id"], device.to_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/create-signal",
    vol.Required("device_id"): str,
    vol.Required("pronto"): str,
    vol.Required("command_name"): str,
    vol.Optional("alias", default=""): str,
})
@websocket_api.async_response
async def ws_pluck_create_signal(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Persist a plucked signal onto a named plucked blaster."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    command_name = msg["command_name"].strip()
    if not command_name:
        connection.send_error(msg["id"], "invalid_name", "Command name is required")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.create_plucked_signal(
        msg["device_id"], msg["pronto"], command_name, msg.get("alias", "")
    )
    if not result["success"]:
        connection.send_error(
            msg["id"],
            result.get("code", "create_failed"),
            result.get("error", "Failed to create signal"),
        )
        return
    connection.send_result(msg["id"], result["signal"])


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/delete-blaster",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_pluck_delete_blaster(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a plucked blaster and its signals (delete-and-recreate model)."""
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
            result.get("error", "Failed to delete blaster"),
        )
        return
    connection.send_result(msg["id"], {"deleted": True})


# --- Plucker: learned-code stores (0.10.3, mechanism two) ---
#
# Two commands, and they are deliberately lopsided. Listing is CHEAP and
# happens every time the dialog opens: counts only, no decoding, one
# file read per store. Importing is the expensive one and only happens
# when someone clicks a card.
#
# Per-item resilience throughout (the 0.10.2 rule): one unreadable store
# comes back carrying its receipt and never removes its siblings from
# the list, because a dialog that blanks tells the user nothing about
# what it could not read.


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/stores/list",
})
@websocket_api.async_response
async def ws_pluck_stores_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Discovered learned-code stores, counted but not decoded.

    Each entry carries store_id, integration, friendly_name (resolved
    from the config entry and, for Broadlink, the device registry, so a
    MAC is a lookup key and never something the user reads), the
    subdevice and code counts, the IR/RF split, and ``error``: null, or
    the receipt for a store that would not parse.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    registry = data.get("pluckable_registry", [])
    stores = await pluck.list_stores(hass, registry)
    connection.send_result(msg["id"], {"stores": stores})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/stores/import",
    vol.Required("store_id"): str,
})
@websocket_api.async_response
async def ws_pluck_stores_import(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Import one whole store and return the landing numbers.

    Import-all by owner ruling: no subdevice picker, and pruning is a
    delete afterwards. The result is the summary the dialog renders as
    its landing sentence, so every clause it can print has a counter
    here (remotes, signals, washed, kept_raw, toggle_pairs,
    rf_receipted, no_timings, already_present).
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    registry = data.get("pluckable_registry", [])
    result = await pluck.run_store_pluck(
        hass,
        entry_data=data,
        registry=registry,
        store_id=msg["store_id"].strip(),
    )
    if "error" in result:
        connection.send_error(
            msg["id"], result["error"], result.get("message", "Pluck failed")
        )
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/pluck/stores/forget",
    vol.Required("record_id"): str,
})
@websocket_api.async_response
async def ws_pluck_stores_forget(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Remove a plucked store's Devices-tab row. The remotes stay.

    Deleting the record forgets where a set of remotes came from and
    nothing else, which is the existing blaster-delete semantics applied
    to a source that has no entity behind it. Re-plucking the same store
    brings the row back and, thanks to the tiered duplicate guard, adds
    no signals.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    signal_store: SignalStore = data["signal_store"]
    if not signal_store.remove_plucked_store(msg["record_id"]):
        connection.send_error(
            msg["id"], "not_found", "That plucked store record is already gone"
        )
        return
    await signal_store.async_save()
    connection.send_result(msg["id"], {"forgotten": True})


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
    vol.Optional("repeat_count"): vol.All(
        int, vol.Range(min=0, max=MAX_DITTO_COUNT)
    ),
    vol.Optional("send_count"): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
    vol.Optional("tx_force_raw"): bool,
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
        msg["device_id"], msg["pronto"], msg.get("alias", ""),
        repeat_count=msg.get("repeat_count"),
        send_count=msg.get("send_count"),
        tx_force_raw=msg.get("tx_force_raw"),
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
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/set-tx-force-raw",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
    vol.Required("tx_force_raw"): bool,
})
@websocket_api.async_response
async def ws_signal_set_tx_force_raw(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Pin a catalog signal to raw replay, or unpin it.

    The Sniffer / Clipper twin of the device command's toggle. Setting it
    here is what lets the intent survive assign, export and adopt rather
    than dying on the clipped remote where the user found the problem.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(
            msg["id"], "not_configured", "HAIR not configured"
        )
        return
    monitor: SignalMonitor = data["signal_monitor"]
    ok = await monitor.set_signal_tx_force_raw(
        msg["device_id"], msg["signal_id"], msg["tx_force_raw"]
    )
    if not ok:
        connection.send_error(
            msg["id"], "not_found", "Signal not found"
        )
        return
    connection.send_result(msg["id"], {"tx_force_raw": msg["tx_force_raw"]})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/signal/edit-pronto",
    vol.Required("device_id"): str,
    vol.Required("signal_id"): str,
    vol.Required("pronto"): str,
    vol.Optional("alias"): vol.Any(str, None),
    vol.Optional("repeat_count"): vol.All(
        int, vol.Range(min=0, max=MAX_DITTO_COUNT)
    ),
    vol.Optional("send_count"): vol.All(
        int, vol.Range(min=1, max=MAX_SEND_COUNT)
    ),
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
        msg["device_id"], msg["signal_id"], msg["pronto"], msg.get("alias"),
        repeat_count=msg.get("repeat_count"),
        send_count=msg.get("send_count"),
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
    vol.Optional("repeat_count"): vol.All(
        int, vol.Range(min=0, max=MAX_DITTO_COUNT)
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

    # A porthole row edits the LATTICE, not just this record. Written
    # first: if the cell is gone the row is stale, and updating the
    # command anyway would leave a row claiming bytes no cell carries.
    cell = _porthole_cell(device_manager, msg["device_id"], msg["command_id"])
    if (
        cell is not None
        and msg.get("pronto")
        and not await device_manager.async_replace_cell(
            msg["device_id"], cell, msg["pronto"]
        )
    ):
        connection.send_error(
            msg["id"], "cell_missing",
            "That cell is no longer in the device's matrix",
        )
        return

    result = await device_manager.async_update_command(
        msg["device_id"],
        msg["command_id"],
        name=msg.get("name"),
        pronto=msg.get("pronto"),
        send_count=msg.get("send_count"),
        repeat_count=msg.get("repeat_count"),
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


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/unknown/delete-remote",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_delete_sniffed_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a sniffed remote and all its signals (resurrects on
    re-hearing, same semantics as per-row delete)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor: SignalMonitor = data["signal_monitor"]
    result = await monitor.delete_sniffed_remote(msg["device_id"])
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


# --- Climate presets: the star ---


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/star",
    vol.Required("device_id"): str,
    vol.Required("command_name"): str,
    vol.Required("starred"): bool,
})
@websocket_api.async_response
async def ws_device_star(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Star or unstar a command (climate-presets-star.md).

    A starred command becomes a Home Assistant preset on the device's
    climate entity, named exactly what the command is named. Returns
    the resulting ``starred`` list so the caller can repaint the row
    without a second round trip; the same list also rides
    ``entity_config`` on any later full device payload.

    Deliberately NOT part of ``device/update-mapping``: that handler
    enforces one mapping key per command, and a command can be both
    mapped and starred.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    manager: DeviceManager = data["device_manager"]
    starred = await manager.async_set_starred(
        msg["device_id"], msg["command_name"], msg["starred"]
    )
    if starred is None:
        connection.send_error(
            msg["id"], "not_found", "Device or command not found"
        )
        return
    connection.send_result(msg["id"], {"starred": starred})


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
    """Return all triggers, ordered (Trigger Remotes signpost 1, Track B:
    the drawer's row list renders in the persisted ``order``, not
    insertion/dict order -- the same field the automation-editor
    dropdown (Track A, device_trigger.py) already sorts by)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_result(msg["id"], [])
        return
    store = data["store"]
    triggers = store.get_all_triggers_ordered()
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
    vol.Optional("receiver_entity_ids"): [str],
    vol.Optional("byte_hash"): vol.Any(str, None),
    vol.Optional("decoded_fingerprint"): vol.Any(str, None),
    # Add Popups signpost 2, Track 3: owning remote + creation-door
    # provenance. Both default to None/absent, matching the pre-Track-3
    # behavior exactly (drawer-owned, no origin) -- the drawer's own
    # "+ Add Trigger" dialog never sends either and is unaffected.
    vol.Optional("trigger_remote_id"): vol.Any(str, None),
    vol.Optional("origin"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_create_trigger(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new trigger."""

    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]

    sig_fp = msg.get("signal_fingerprint", "")
    protocol = msg.get("protocol")
    code = msg.get("code")
    # Byte-level identity (v0.5.8). Honored only when the client sends it
    # explicitly (or derived from a source command below); the protocol+code
    # auto-derive branch deliberately does NOT compute one server-side, so a
    # stale cached frontend degrades to a legacy-broad trigger, which is the
    # pre-0.5.8 behavior.
    byte_hash = msg.get("byte_hash")
    # Decoded identity (v0.5.8 unified identity). Unlike byte_hash, this IS
    # server-derived from the code when the client did not send it: decode
    # is checksum-validated, so a derived value can only be the code's true
    # identity or None -- it cannot mis-scope the trigger the way a
    # recomputed (bin-quantized, snap-fragile) hash could. Mirrors what the
    # load-time backfill would do at next restart anyway; deriving here
    # just activates tier-1 matching immediately.
    decoded_fingerprint = msg.get("decoded_fingerprint")

    # Auto-compute fingerprint from protocol+code when not provided.
    if not sig_fp and (protocol or code):
        # Canonical (wire) identity: a trigger created from a pasted or
        # wig-supplied code has to match the real press, which arrives
        # rebuilt from raw timings (identity.py's canonical-form block).
        sig_fp = canonical_fingerprint(protocol, code, None)

    # Resolve the source command when one was given. Two jobs, independently
    # gated: fill a missing fingerprint, and (v0.5.8) derive the byte_hash.
    # The hash derive must NOT hang off `not sig_fp` -- the device-detail
    # trigger dialog always sends protocol+code, so the fingerprint is
    # already resolved by here and a gated derive would never run, leaving
    # every trigger created from a command row legacy-broad. That is the
    # exact bug this release exists to fix, on the path a user hits right
    # after assigning a signal.
    if msg.get("source_command_id") and msg.get("source_device_id"):
        dm = data.get("device_manager")
        if dm:
            device = dm.get_device(msg["source_device_id"])
            if device:
                cmd = device.get_command(msg["source_command_id"])
                if cmd:
                    if not sig_fp:
                        sig_fp = canonical_fingerprint(
                            cmd.protocol, cmd.code, cmd.raw_timings,
                        )
                    if not protocol:
                        protocol = cmd.protocol
                    if not code:
                        code = cmd.code
                    # NOTE: a hash inherited from a snapped or re-encoded
                    # command code may differ from what live captures of the
                    # same button hash to (snap rescales timing words).
                    # Accepted trade-off; the command's own identity is
                    # still the most precise thing we know here. Under
                    # tiered matching, the command's decoded identity
                    # (below) additionally rescues exactly that mismatch
                    # for decodable protocols.
                    if byte_hash is None:
                        byte_hash = cmd.byte_hash
                    if decoded_fingerprint is None:
                        decoded_fingerprint = cmd.decoded_fingerprint

    if not sig_fp:
        connection.send_error(
            msg["id"], "missing_fingerprint",
            "Cannot compute signal fingerprint. Provide signal_fingerprint, "
            "protocol+code, or source_device_id+source_command_id."
        )
        return

    # v0.5.7: multiple triggers per fingerprint are legal -- users create
    # per-receiver-scoped triggers on the same signal (different rooms). The
    # frontend routes through the trigger popover's explicit "+ new trigger"
    # action, so a second trigger on a known fingerprint is intentional. No
    # duplicate rejection.
    trigger = IRTrigger(
        name=msg["name"],
        signal_fingerprint=sig_fp,
        protocol=protocol,
        code=code,
        min_hits=msg.get("min_hits", 1),
        source_device_id=msg.get("source_device_id"),
        source_command_id=msg.get("source_command_id"),
        receiver_entity_ids=list(msg.get("receiver_entity_ids") or []),
        byte_hash=byte_hash,
        decoded_fingerprint=decoded_fingerprint,
        # Add Popups signpost 2, Track 3.
        trigger_remote_id=msg.get("trigger_remote_id"),
        origin=msg.get("origin"),
    )
    if trigger.decoded_fingerprint is None and trigger.code:
        # Safe server-side derive (see the comment at the top of the
        # handler); same computation as the load-time trigger backfill.
        from .ir_command import ProntoCommand
        from .protocol_decode import decode_to_fields

        try:
            _raw = ProntoCommand(trigger.code).get_raw_timings()
        except (ValueError, IndexError):
            _raw = None
        _, _, _, derived = decode_to_fields(_raw)
        trigger.decoded_fingerprint = derived
    store.add_trigger(trigger)
    # Signpost 4, Track 1: a new trigger may map onto commands of
    # devices already pinned to its remote, so the map is recomputed
    # before the save rather than waiting for the next restart.
    from .pin_bindings import rederive_all_pinned

    rederive_all_pinned(store)
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
    vol.Optional("receiver_entity_ids"): [str],
    vol.Optional("byte_hash"): vol.Any(str, None),
    vol.Optional("decoded_fingerprint"): vol.Any(str, None),
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
        # Trigger Remotes signpost 1: retire the old name into alias
        # history rather than overwriting it, so a device trigger built
        # against the old name keeps resolving (device_trigger.py).
        trigger.rename(msg["name"])
    if "min_hits" in msg:
        trigger.min_hits = max(1, msg["min_hits"])
    if "enabled" in msg:
        trigger.enabled = msg["enabled"]
    if "receiver_entity_ids" in msg:
        # Receiver scope (v0.5.7). Empty list = any receiver (backward compat).
        trigger.receiver_entity_ids = list(msg["receiver_entity_ids"] or [])
    if "byte_hash" in msg:
        # Byte-level identity (v0.5.8). None = legacy-broad matching.
        trigger.byte_hash = msg["byte_hash"]
    if "decoded_fingerprint" in msg:
        # Decoded identity (v0.5.8 unified identity). None = no tier-1.
        trigger.decoded_fingerprint = msg["decoded_fingerprint"]
    trigger.updated_at = datetime.now(UTC).isoformat()

    store.update_trigger(trigger)
    # An edit can change the trigger's identity (byte_hash, decoded
    # fingerprint, a re-snapped code), which is exactly what the map is
    # keyed on -- so the map is stale the moment this returns unless it
    # is rebuilt here.
    from .pin_bindings import rederive_all_pinned

    rederive_all_pinned(store)
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
    from .pin_bindings import rederive_all_pinned

    rederive_all_pinned(store)
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


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger/reorder",
    vol.Required("trigger_ids"): [str],
})
@websocket_api.async_response
async def ws_reorder_triggers(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Reorder the HAIR Triggers drawer's row list.

    Mirrors ``hair/devices/reorder`` and ``hair/device/reorder-commands``
    (Trigger Remotes signpost 1, Track B: ir-trigger-row.ts drag reorder).
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    try:
        store.reorder_triggers(list(msg["trigger_ids"]))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await store.async_save()
    connection.send_result(msg["id"], {"reordered": True})


def _trigger_drawer_ha_device_id(hass: HomeAssistant) -> str | None:
    """Resolve the HAIR Triggers drawer's HA device-registry id, if any.

    None until the first trigger's event entity registers the device
    (empty-state ruling, design brief section "Empty state": "No HA
    device link yet -- there's nothing registered until the first
    trigger lands"). Mirrors ``_ha_device_id`` above, keyed on the
    drawer's own fixed identifier instead of a per-device id.
    """
    from .event import TRIGGER_DEVICE_ID

    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(identifiers={(DOMAIN, TRIGGER_DEVICE_ID)})
    return ha_device.id if ha_device is not None else None


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-drawer",
})
@websocket_api.async_response
async def ws_get_trigger_drawer(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the HAIR Triggers drawer's identity (name + HA device link).

    Trigger Remotes signpost 1, Track B header: name (rename-in-place),
    the exit-to-entity glyph (only rendered by the frontend when
    ``ha_device_id`` is not None). Trigger count is not included here --
    the frontend already holds the full trigger list via
    ``hair/triggers`` and can just take its length, so this stays a
    two-field payload instead of a second source of truth for a count.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    connection.send_result(msg["id"], {
        "name": store.get_trigger_drawer_name(),
        "ha_device_id": _trigger_drawer_ha_device_id(hass),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-drawer/rename",
    vol.Required("name"): str,
})
@websocket_api.async_response
async def ws_rename_trigger_drawer(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Rename the HAIR Triggers drawer.

    Updates the stored name (the single source of truth new entities
    register under, see event.py) and, when the drawer already has a
    live HA device-registry entry, that entry's own ``name`` directly --
    HA only syncs an entity's ``device_info`` into the registry at
    entity-add time, not on every state write, so a bare
    ``async_write_ha_state()`` after the rename would not reach the
    registry on its own. ``name`` (the integration-owned base name),
    not ``name_by_user`` (HA's own "user overrode this via Settings"
    field) -- this rename comes from HAIR's own panel and IS the new
    canonical name, the same relationship every other HAIR device's
    name already has to its own registry entry (no device carries a
    manual dr.async_update_device call for its own rename either; see
    ws_update_device).
    """
    name = msg["name"].strip()
    if not name:
        connection.send_error(msg["id"], "invalid_format", "Name is required")
        return
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    store.set_trigger_drawer_name(name)
    await store.async_save()

    from .event import TRIGGER_DEVICE_ID, resync_drawer_name

    entry_id = data["config_entry"].entry_id
    resync_drawer_name(hass, entry_id, name)

    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(identifiers={(DOMAIN, TRIGGER_DEVICE_ID)})
    if ha_device is not None:
        registry.async_update_device(ha_device.id, name=name)

    connection.send_result(msg["id"], {
        "name": name,
        "ha_device_id": ha_device.id if ha_device is not None else None,
    })


# --- Trigger Remotes (Add Popups signpost 2, Track 1B-B2/B3;
#     eager registration added signpost 3, Track 2 item 1) ---
#
# A named remote is a real HA device, same as a controlled device.
# Signpost 3 (brief 7b, owner-ruled 2026-08-14): the registry entry is
# created EAGERLY at remote creation via _register_trigger_remote_ha_device
# below, not lazily at first trigger -- an empty remote is a real,
# honestly-empty HA device from second one, so the exit-to-entity glyph
# works immediately and nobody dead-ends. Rename/delete already
# sync/remove the entry defensively (``if ha_device is not None``),
# which keeps working unchanged for both newly-eager remotes (always
# found now) and any pre-existing empty remote from before this patch.


def _trigger_remote_ha_device_id(hass: HomeAssistant, remote_id: str) -> str | None:
    """Resolve a named remote's HA device-registry id, if any.

    Always populated for a remote created after signpost 3's eager
    registration; may still be None for an empty remote created before
    that change shipped, until its first trigger lands and an event
    entity registers the device the old lazy way (event.py's
    ``_device_identity_for_trigger``) -- mirrors
    ``_trigger_drawer_ha_device_id`` above, keyed on the remote's own
    id instead of the drawer's fixed identifier.
    """
    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(identifiers={(DOMAIN, remote_id)})
    return ha_device.id if ha_device is not None else None


def _invalidate_remote_matrix(data: dict[str, Any], remote_id: str) -> None:
    """Drop the listener's cached matrix for one remote.

    Called by every door that writes, copies or deletes a remote's
    matrix file (signpost 4, Track M). The cache is held for the
    install's lifetime on the argument that nothing changes a matrix
    behind our back, so every door that DOES change one has to say so
    here. A no-op when no listener is registered, which is the shape
    hand-built test entry data carries.
    """
    listener = data.get("matrix_listener")
    if listener is not None:
        listener.invalidate(remote_id)


def _warm_remote_matrix(data: dict[str, Any], remote_id: str) -> None:
    """Build the index for a lattice that was just written (0.10.1 item 3).

    Called by the MINT doors only, never by the delete one. Setup warms
    every lattice the store already knows about, so this is what keeps a
    remote created mid-run from paying the first-frame miss the setup
    warm exists to remove.
    """
    listener = data.get("matrix_listener")
    if listener is not None:
        listener.warm_index(remote_id)


async def _remote_matrix(
    hass: HomeAssistant, data: dict[str, Any], remote: TriggerRemote
) -> Any | None:
    """One remote's parsed matrix, or None when it has none.

    Goes through the listener's cache when there is one; falls back to
    a direct executor load otherwise, so a caller assembled without a
    listener reads the truth off disk rather than reporting a matrix
    remote as flat.
    """
    if not remote.climate_matrix:
        return None
    listener = data.get("matrix_listener")
    if listener is not None:
        return await listener.async_get_matrix(remote.id)
    from .matrix_store import load_matrix

    return await hass.async_add_executor_job(
        load_matrix, hass.config.config_dir, remote.id
    )


def _register_trigger_remote_ha_device(
    hass: HomeAssistant, config_entry_id: str, remote: TriggerRemote
) -> str:
    """Eagerly register a named remote's HA device-registry entry.

    Signpost 3 (brief 7b): called at remote creation (and duplication,
    which mints a new remote the same way) instead of waiting for the
    first trigger's event entity to register it. Field shape matches
    ``HAIRTriggerEventEntity.device_info`` in event.py exactly
    (manufacturer "HAIR", model "IR Triggers") so the eager write here
    and any later entity-driven write agree byte for byte -- HA's
    registry merge is then a no-op either way, never two device rows.
    Returns the HA device id.
    """
    registry = dr.async_get(hass)
    ha_device = registry.async_get_or_create(
        config_entry_id=config_entry_id,
        identifiers={(DOMAIN, remote.id)},
        name=remote.name,
        manufacturer="HAIR",
        model="IR Triggers",
    )
    return ha_device.id


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remotes",
})
@websocket_api.async_response
async def ws_list_trigger_remotes(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return every named trigger remote, each carrying its HA device
    link (if any) and owned-trigger count -- the Trigger Remotes
    section renders one card per row from this alone, no per-remote
    follow-up call. The drawer itself is never in this list; it is not
    a TriggerRemote row (see ``TriggerRemote`` in models.py)."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_result(msg["id"], [])
        return
    store = data["store"]
    remotes = store.get_all_trigger_remotes()
    result = []
    for remote in remotes:
        # Item 0.6: the s11 Remote-card ON:/OFF: badges (mockup-s11.html
        # section 0a) read straight off this list call -- no per-remote
        # follow-up, the same one-call rule the list has carried since
        # Track 1B.
        triggers = store.get_triggers_for_remote(remote.id)
        enabled_count = sum(1 for t in triggers if t.enabled)
        # Signpost 4, Track 4: what each trigger actually drives, named.
        # remote.bindings stores ids, and a trigger row needs words, so
        # the resolution happens here rather than making the frontend
        # fetch every pinned device just to read command names. Same
        # one-call rule the ON:/OFF: badges follow. Triggers with no
        # mapping are simply absent -- the UI says "unmapped" only when
        # the remote has pins at all, so an unpinned remote stays quiet.
        pin_map: dict[str, list[dict[str, str]]] = {}
        for pinned_id in remote.pinned_device_ids:
            pinned_device = store.get_device(pinned_id)
            if pinned_device is None:
                continue
            command_names = {c.id: c.name for c in pinned_device.commands}
            for trigger_id, command_id in (
                remote.bindings.get(pinned_id) or {}
            ).items():
                name = command_names.get(command_id)
                if name is None:
                    continue
                pin_map.setdefault(trigger_id, []).append({
                    "device_name": pinned_device.name,
                    "command_name": name,
                })
        # Signpost 4, Track M: the hear-side lattice summary, the same
        # shape and the same helper _device_full puts on a device.
        # This list IS the detail payload (the one-call rule), so the
        # card renders without a follow-up; the listener's cache is
        # what keeps a per-refresh summary off the disk.
        matrix_summary_block = None
        matrix = await _remote_matrix(hass, data, remote)
        if matrix is not None:
            from .wig_climate import matrix_summary

            matrix_summary_block = matrix_summary(matrix)
        result.append({
            **remote.to_dict(),
            "ha_device_id": _trigger_remote_ha_device_id(hass, remote.id),
            "trigger_count": len(triggers),
            "enabled_count": enabled_count,
            "disabled_count": len(triggers) - enabled_count,
            "pin_map": pin_map,
            "matrix": matrix_summary_block,
        })
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/create",
    vol.Required("name"): str,
    vol.Optional("receiver_scope"): [str],
    vol.Optional("origin"): vol.Any(str, None),
    vol.Optional("promoted_from_unknown_id"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_create_trigger_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a named remote (Manual tab of the Add Trigger Remote
    dialog, Track 3), OR mint one from a Sniffer/Clipper/Plucker
    catalog remote when ``promoted_from_unknown_id`` is set (signpost
    3, Track 2 item 2 -- the "USE as a Remote" fork's non-Manual
    tabs). Same field name and shape as ws_create_device's
    ``promoted_from_unknown_id``, covering all three catalog sources
    at once since they differ only by UnknownDevice.source, not by
    shape. Closet-wig-sourced creation is its own command,
    ws_wig_make_remote, mirroring how ws_wig_make_device is separate
    from ws_create_device's promote path."""
    name = msg["name"].strip()
    if not name:
        connection.send_error(msg["id"], "invalid_format", "Name is required")
        return
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    source_unknown = msg.get("promoted_from_unknown_id")
    remote = TriggerRemote(
        name=name,
        receiver_scope=list(msg.get("receiver_scope") or []),
        origin=msg.get("origin") or ("remote" if source_unknown else None),
    )
    store.add_trigger_remote(remote)
    await store.async_save()

    ha_device_id = _register_trigger_remote_ha_device(
        hass, data["config_entry"].entry_id, remote
    )

    # Sniffer promote / Clipper / Plucker (signpost 3, Track 2 item 2):
    # every signal on the source catalog remote becomes a named trigger
    # in capture order. No matrix guard needed -- catalog remotes are
    # always flat signal lists, see this patch's module docstring.
    trigger_count = 0
    if source_unknown:
        monitor: SignalMonitor = data["signal_monitor"]
        copy = await monitor.copy_signals_to_trigger_remote(
            source_unknown, remote.id
        )
        if copy.get("success"):
            from .event import sync_trigger_entities

            entry_id = data["config_entry"].entry_id
            for trig in copy.get("triggers", []):
                sync_trigger_entities(hass, entry_id, trigger=trig)
            trigger_count = len(copy.get("triggers", []))
        await monitor.mark_promoted_remote(source_unknown, remote.id)

    connection.send_result(msg["id"], {
        **remote.to_dict(),
        "ha_device_id": ha_device_id,
        "trigger_count": trigger_count,
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/rename",
    vol.Required("remote_id"): str,
    vol.Required("name"): str,
})
@websocket_api.async_response
async def ws_rename_trigger_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Rename a named remote.

    Mirrors ``ws_rename_trigger_drawer``: updates the stored row (the
    source new entities register under), pushes the new name onto any
    already-live event entities (``event.resync_remote_name``), and --
    same registry-sync-only-at-entity-add-time reasoning as the drawer
    -- updates the HA device registry entry directly when one already
    exists.
    """
    name = msg["name"].strip()
    if not name:
        connection.send_error(msg["id"], "invalid_format", "Name is required")
        return
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Trigger remote not found")
        return

    from datetime import UTC, datetime

    remote.name = name
    remote.updated_at = datetime.now(UTC).isoformat()
    store.update_trigger_remote(remote)
    await store.async_save()

    from .event import resync_remote_name

    entry_id = data["config_entry"].entry_id
    resync_remote_name(hass, entry_id, remote.id, name)

    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(identifiers={(DOMAIN, remote.id)})
    if ha_device is not None:
        registry.async_update_device(ha_device.id, name=name)

    connection.send_result(msg["id"], {
        **remote.to_dict(),
        "ha_device_id": ha_device.id if ha_device is not None else None,
        "trigger_count": len(store.get_triggers_for_remote(remote.id)),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/set-receiver-scope",
    vol.Required("remote_id"): str,
    vol.Required("receiver_scope"): [str],
})
@websocket_api.async_response
async def ws_set_trigger_remote_receiver_scope(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set a named remote's receiver_scope after creation.

    Add Popups signpost 2, Track 5 follow-up (owner bench request,
    2026-08-14): the Add Trigger Remote dialog's footer picker was the
    only way to set this before now -- nothing let a user change it on
    an existing remote. Remote-level only, same field
    ir-add-trigger-remote-dialog.ts already writes at creation; this
    does not touch any trigger's own receiver_entity_ids (the
    2026-08-10 ruling keeps those two concepts separate -- no
    per-trigger receiver UI on a named remote's rows, only this one
    remote-wide scope).
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Trigger remote not found")
        return

    from datetime import UTC, datetime

    remote.receiver_scope = list(msg["receiver_scope"])
    remote.updated_at = datetime.now(UTC).isoformat()
    store.update_trigger_remote(remote)
    await store.async_save()

    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(identifiers={(DOMAIN, remote.id)})
    connection.send_result(msg["id"], {
        **remote.to_dict(),
        "ha_device_id": ha_device.id if ha_device is not None else None,
        "trigger_count": len(store.get_triggers_for_remote(remote.id)),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/delete",
    vol.Required("remote_id"): str,
})
@websocket_api.async_response
async def ws_delete_trigger_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a named remote AND every trigger it owns
    (delete-takes-its-triggers, Release A ruling).

    Mirrors ``DeviceManager.async_remove_device``'s ordering: remove
    the owned event entities first, then explicitly remove the HA
    device-registry entry (entity removal alone does not clean up an
    otherwise-orphaned device), then commit the store change. Its
    matrix file (signpost 4, Track M) goes the same way that method
    disposes of a device's: best-effort, AFTER the store commit, so a
    full disk or a bad permission can never resurrect a remote the
    user already deleted. An orphaned matrix file is inert -- nothing
    reads one without the id that names it.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    # Read before removal: the flag lives on the remote row, and
    # remove_trigger_remote returns its triggers, not the remote.
    doomed = store.get_trigger_remote(msg["remote_id"])
    had_matrix = doomed is not None and doomed.climate_matrix
    removed = store.remove_trigger_remote(msg["remote_id"])
    if removed is None:
        connection.send_error(msg["id"], "not_found", "Trigger remote not found")
        return
    await store.async_save()

    _invalidate_remote_matrix(data, msg["remote_id"])
    if had_matrix:
        from .matrix_store import delete_matrix

        try:
            await hass.async_add_executor_job(
                delete_matrix, hass.config.config_dir, msg["remote_id"]
            )
        except Exception:
            _LOGGER.warning(
                "Could not delete matrix file for remote %s",
                msg["remote_id"], exc_info=True,
            )

    from .event import sync_trigger_entities

    entry_id = data["config_entry"].entry_id
    for trigger in removed:
        sync_trigger_entities(hass, entry_id, removed_id=trigger.id)

    registry = dr.async_get(hass)
    ha_device = registry.async_get_device(
        identifiers={(DOMAIN, msg["remote_id"])}
    )
    if ha_device is not None:
        registry.async_remove_device(ha_device.id)

    connection.send_result(msg["id"], {
        "removed": True,
        "removed_trigger_ids": [t.id for t in removed],
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/pin",
    vol.Required("remote_id"): str,
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_pin_trigger_remote_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a device to a remote's pin list (signpost 3, Track 2 item 5
    / section 0b). Storage only -- no retransmit, no derivation, no
    live behavior; see TriggerRemote.pinned_device_ids's docstring.
    Idempotent: pinning an already-pinned device is a no-op, not an
    error, matching the set semantics of the header Pin: chip group
    it feeds (signpost 4).
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Trigger remote not found")
        return
    device_id = msg["device_id"]
    if device_id not in remote.pinned_device_ids:
        from datetime import UTC, datetime

        remote.pinned_device_ids.append(device_id)
        remote.updated_at = datetime.now(UTC).isoformat()
        # Signpost 4, Track 1: a pin with no derived button map drives
        # nothing, so derivation is part of pinning rather than a
        # follow-up call a caller could forget to make.
        from .pin_bindings import rederive_remote

        rederive_remote(store, remote)
        store.update_trigger_remote(remote)
        await store.async_save()
    connection.send_result(msg["id"], {
        "pinned_device_ids": list(remote.pinned_device_ids),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/unpin",
    vol.Required("remote_id"): str,
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_unpin_trigger_remote_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Remove a device from a remote's pin list. Storage only, same
    scope as ws_pin_trigger_remote_device. Idempotent: unpinning a
    device that was never pinned is a no-op, not an error.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Trigger remote not found")
        return
    device_id = msg["device_id"]
    if device_id in remote.pinned_device_ids:
        from datetime import UTC, datetime

        remote.pinned_device_ids.remove(device_id)
        remote.updated_at = datetime.now(UTC).isoformat()
        # The unpinned device's map goes with it: derive_bindings walks
        # pinned devices only, so re-deriving here drops the stale entry
        # in the same write that drops the pin. No orphan can outlive
        # the pin and drive a device the user just detached.
        from .pin_bindings import rederive_remote

        rederive_remote(store, remote)
        store.update_trigger_remote(remote)
        await store.async_save()
    connection.send_result(msg["id"], {
        "pinned_device_ids": list(remote.pinned_device_ids),
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/duplicate",
    vol.Required("remote_id"): str,
    vol.Required("new_name"): str,
    # Track 2 item 6: the duplicate dialog footer's receiver-chip
    # picker, defaulting to the source's scope but overridable before
    # Create. Omitted entirely (not just empty) means "inherit the
    # source's scope unchanged" -- the pre-item-6 behavior, preserved
    # for any other caller of this endpoint. An explicit empty list is
    # a real override (unscoped), not "no opinion".
    vol.Optional("receiver_scope"): [str],
})
@websocket_api.async_response
async def ws_duplicate_trigger_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Clone a named trigger remote AND its triggers under a new name.

    Add Popups signpost 2, Track 5 (owner ruling 2026-08-14): unlike
    ``ws_duplicate_device``, which explicitly excludes triggers (see
    ``IRDevice.clone``'s own docstring), a trigger remote's triggers
    are its entire content -- an empty duplicate would just be a
    second empty shell, which ``ws_create_trigger_remote`` already
    covers. Every trigger is copied with a fresh id, the source's
    enabled state carried over as-is (owner-accepted trade-off: if the
    source remote is still receiving real signals, both it and the
    copy fire until the user turns off or deletes the ones they do
    not want live -- ir-duplicate-trigger-remote-dialog.ts's own hint
    text says this plainly), fire_count/last_fired_at/alias_history
    reset to a clean slate, and receiver_entity_ids forced empty --
    named-remote rows never carry per-trigger receiver scope
    (2026-08-10 ruling), only the remote-level receiver_scope, which
    the clone already inherited via ``TriggerRemote.clone``.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    source = store.get_trigger_remote(msg["remote_id"])
    if source is None:
        connection.send_error(msg["id"], "not_found", "Trigger remote not found")
        return

    new_name = msg["new_name"].strip()
    if not new_name:
        connection.send_error(
            msg["id"], "invalid_format", "Name cannot be empty"
        )
        return

    clone = source.clone(new_name)
    if "receiver_scope" in msg:
        clone.receiver_scope = list(msg["receiver_scope"])
    if clone.climate_matrix:
        # Same shape as ws_duplicate_device: the file rides along under
        # the copy's id, and a failed copy clears the flag rather than
        # leaving a remote that claims a lattice it cannot read.
        from .matrix_store import copy_matrix

        copied_matrix = await hass.async_add_executor_job(
            copy_matrix, hass.config.config_dir, source.id, clone.id
        )
        if copied_matrix:
            _invalidate_remote_matrix(data, clone.id)
            _warm_remote_matrix(data, clone.id)
        else:
            clone.climate_matrix = False
    store.add_trigger_remote(clone)

    from .event import sync_trigger_entities

    entry_id = data["config_entry"].entry_id
    copied: list[IRTrigger] = []
    for trig in store.get_triggers_for_remote(source.id):
        new_trigger = IRTrigger(
            name=trig.name,
            signal_fingerprint=trig.signal_fingerprint,
            protocol=trig.protocol,
            code=trig.code,
            min_hits=trig.min_hits,
            enabled=trig.enabled,
            source_device_id=trig.source_device_id,
            source_command_id=trig.source_command_id,
            receiver_entity_ids=[],
            byte_hash=trig.byte_hash,
            decoded_fingerprint=trig.decoded_fingerprint,
            trigger_remote_id=clone.id,
            # The CODE's provenance, not the click's. Duplicating is a
            # manual action and the clone's own origin says so, but a
            # copied trigger still holds the bytes its source got from
            # wherever it got them -- stamping "manual" here told the
            # identity rules a wig-minted row had been typed by hand
            # (2026-08-18, receiver-tolerant identity).
            origin=trig.origin,
        )
        store.add_trigger(new_trigger)
        sync_trigger_entities(hass, entry_id, trigger=new_trigger)
        copied.append(new_trigger)

    await store.async_save()

    ha_device_id = _register_trigger_remote_ha_device(
        hass, entry_id, clone
    )

    connection.send_result(msg["id"], {
        **clone.to_dict(),
        "ha_device_id": ha_device_id,
        "trigger_count": len(copied),
    })


# --- Wigs (v0.7.0 Big Wig): the closet over WebSocket ---
#
# All closet I/O is blocking file work and runs in the executor. Filename
# inputs are guarded by safe_wig_filename inside wig_store; upload text is
# schema-validated BEFORE anything touches disk (wigs.md section 4).


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/list",
})
@websocket_api.async_response
async def ws_wigs_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """The Wigs tab payload: local wigs with metadata, invalid files
    with their validation reasons, library codebooks for the brand rows,
    and the library version stamp for the toolbar. Each wig carries its
    fitting summary so the fitted / not fitted filter and the row
    markers never recompute from raw fittings (fitting-flow.md 5.2)."""
    # Second Fitting v3 punch list item 8: "yours" is keyed on this
    # install's public signing key, not the typed handle against the
    # HA username -- see claims_summary's install_key parameter.
    from .fitting_signing import async_get_public_key

    install_key = await async_get_public_key(hass)

    entry_data = _get_first_entry_data(hass)

    def _scan() -> dict[str, Any]:
        from .code_library import get_tree, library_available
        from .wig_climate import matrix_summary
        from .wig_comb import receipt_summary
        from .wig_fitting import claims_summary
        from .wig_store import scan_wigs

        scan = scan_wigs(hass.config.config_dir)
        # Adopt Device (v0.8.1): which HAIR devices already carry this
        # wig's codes, by the same tiered identity match the catalog
        # rows use. Identities come content-hash cached.
        store = entry_data.get("store") if entry_data else None
        hair_devices = store.get_all_devices() if store else []
        index = _assignment_index(hair_devices)
        # Item 0.1's remote half: same shape, trigger-remote side.
        trigger_remotes = store.get_all_trigger_remotes() if store else []
        all_triggers = store.get_all_triggers() if store else []
        remotes_by_id = {r.id: r for r in trigger_remotes}
        trigger_index = _trigger_assignment_index(
            all_triggers, remotes_by_id
        )
        library = get_tree() if library_available() else []
        try:
            from importlib.metadata import version

            lib_version = version("infrared-protocols")
        except Exception:
            lib_version = None
        return {
            "wigs": [
                {
                    "filename": loaded.path.name,
                    "name": loaded.wig.name,
                    "brand": loaded.wig.brand,
                    "model": loaded.wig.model,
                    "notes": loaded.wig.notes,
                    "origin": loaded.wig.origin,
                    "signal_count": len(loaded.wig.signals),
                    "signals": [
                        sig.alias for sig in loaded.wig.signals
                    ],
                    "kind": loaded.wig.kind,
                    "identifiers": loaded.wig.identifiers,
                    # The closet's matrix summary (owner ruling
                    # 2026-07-28): state count, vocabularies, and temp
                    # bounds so matrix rows render their "N states"
                    # chip and peek summary without loading cells.
                    "matrix": (
                        matrix_summary(loaded.wig.climate)
                        if loaded.wig.climate is not None else None
                    ),
                    "fitting": claims_summary(loaded.wig, install_key),
                    # The comb glyph's state. None means NO RECEIPT --
                    # nobody has combed this wig -- which is deliberately
                    # not the same as clean, and the row draws the same
                    # plain grey for both with the tooltip telling them
                    # apart (owner ruling CG3).
                    "comb": receipt_summary(loaded.wig),
                    "linked_devices": [
                        {**entry, "kind": "device"}
                        for entry in _wig_linked_devices(
                            loaded.wig, index, hair_devices
                        )
                    ] + [
                        {**entry, "kind": "remote"}
                        for entry in _wig_linked_remotes(
                            loaded.wig, trigger_index, trigger_remotes
                        )
                    ],
                }
                for loaded in scan.wigs
            ],
            "invalid": [
                {"filename": bad.path.name, "errors": bad.errors}
                for bad in scan.invalid
            ],
            "library": library,
            "library_version": lib_version,
        }

    connection.send_result(
        msg["id"], await hass.async_add_executor_job(_scan)
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/upload",
    # 4 MB, raised from 1 MB (Smart Perm). The old cap was well under the
    # format's own 16 MB ceiling, so the two largest wigs in a real closet
    # could not be re-dropped -- and those are exactly the big SmartIR
    # lattices combing exists to examine. 4 MB rather than the full 16
    # deliberately: aiohttp's WebSocket frame limit defaults to 4 MiB, so a
    # larger schema cap would move the failure from a message we can
    # explain to a connection drop we cannot. Anything bigger goes in
    # through the wigs folder, which never touches a WS frame; the drop
    # zone says so rather than just refusing.
    vol.Required("text"): vol.All(str, vol.Length(min=2, max=4_000_000)),
    vol.Optional("filename"): vol.All(str, vol.Length(max=300)),
    # The reverse-supersession re-confirm (v0.9.7 Second Fitting,
    # amendment v2 section 3): set once the owner has seen the "a newer
    # wig here supersedes this one" dialog and chosen Import Anyway, so
    # the second call skips straight past the check that would
    # otherwise fire again on the identical text.
    vol.Optional("confirmed", default=False): bool,
})
@websocket_api.async_response
async def ws_wigs_upload(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """The import funnel (wigs.md section 8): a native wig writes
    straight to the closet; a recognized foreign format (SmartIR,
    Flipper .ir, LIRC) converts to wigs first, stamped
    ``converted:<format>``. Either way, validation happens BEFORE
    anything touches disk, and per-signal conversion skips come back
    as reasons instead of vanishing.

    Ancestry only ever points backward -- a successor names the wig it
    replaced, never the reverse -- so a re-dropped ORIGINAL, once its
    successor already exists in this closet, would otherwise file as a
    silent twin nothing else ever looks at (owner bench find, amendment
    v2 section 3). The reverse lookup catches it here, before anything
    touches disk: unlike the forward doorway's CANCEL, which deletes an
    arrival already written, Cancel on THIS dialog means the upload
    never happened at all.
    """

    def _upload() -> dict[str, Any]:
        from datetime import UTC, datetime

        from .wig_adapters import convert, sniff_format
        from .wig_comb import comb_wig, receipt_summary, stamp_receipt
        from .wig_format import (
            drop_legacy_fittings,
            parse_wig,
            serialize_wig,
            wig_content_hash,
        )
        from .wig_store import scan_wigs, write_wig_text

        text = msg["text"]
        today = datetime.now(UTC).date().isoformat()

        def _combed(wig) -> dict[str, Any] | None:
            """Comb before the file lands, and stamp what was found.

            Import is the cheapest moment in a wig's life to look: no
            fittings, no signatures, no shop copies, and it is precisely
            the moment you know a converter was involved. The receipt
            rides in wig extra, outside every canonical hash, so this
            never changes what the wig IS -- only what is known about it.
            """
            stamp_receipt(wig, comb_wig(wig), today)
            return receipt_summary(wig)

        # Content hashes of everything already hanging, so a re-dropped
        # file gets a duplicate receipt (yellow, owner ruling) instead
        # of silently minting -2, -3, ... twins. The file still writes:
        # keeping it is the user's call, the receipt just tells them.
        # wig_content_hash, not signals_content_hash (2026-07-28):
        # matrix wigs carry empty/near-empty flat signal lists, so
        # hashing only the signals made EVERY matrix wig collide on the
        # empty-list hash (owner bench: a Mitsubishi drop got "already
        # in Toyotomi"). wig_content_hash is cells-aware for matrix
        # wigs and byte-identical to the old hash for signal wigs.
        scanned = scan_wigs(hass.config.config_dir).wigs
        existing: dict[str, list[dict[str, Any]]] = {}
        for loaded in scanned:
            existing.setdefault(
                wig_content_hash(loaded.wig), []
            ).append({
                "filename": loaded.path.name,
                "brand": loaded.wig.brand,
            })

        def _entry(wig, filename: str) -> dict[str, Any]:
            matches = existing.get(
                wig_content_hash(wig), []
            )
            return {
                "filename": filename,
                "name": wig.name,
                "brand": wig.brand,
                "duplicate_of": (
                    matches[0]["filename"] if matches else None
                ),
                "duplicates": matches,
            }

        result = parse_wig(text)
        if result.ok:
            # REVERSE SUPERSESSION (v0.9.7 Second Fitting, amendment v2
            # section 3, owner bench find). The forward check below
            # asks what THIS wig supersedes; this asks who supersedes
            # THIS wig -- a closet wig whose own supersedes chain
            # already names the arrival's id outranks it, and nothing
            # else in the funnel would ever notice. Checked against the
            # id the file itself carries, before anything touches disk,
            # so Cancel here can mean "nothing filed" rather than the
            # forward doorway's "delete what just filed".
            if not msg.get("confirmed") and result.wig.wig_id:
                for loaded in scanned:
                    if result.wig.wig_id in loaded.wig.supersedes:
                        return {
                            "success": True,
                            "filenames": [],
                            "files": [],
                            "reverse_supersession": {
                                "name": loaded.wig.name,
                                "signal_count": len(loaded.wig.signals),
                            },
                        }

            # Pre-claims fittings are DROPPED on import (hard rule 6),
            # keyed on the SHAPE of each entry rather than the file's
            # major -- this branch itself wrote /3 files carrying the
            # old whole-wig shape before claims landed, so the stamp
            # cannot be trusted to describe the block. They cannot
            # become claims: a whole-file hash says "all these bytes"
            # and carries no information about which rows anybody
            # actually proved, so converting one would manufacture
            # evidence nobody gave.
            dropped = drop_legacy_fittings(result.wig)
            comb = _combed(result.wig)
            # The receipt means the file written is no longer byte-for-byte
            # what was dropped, so it goes out through the serializer -- the
            # same shape every edit re-saves in.
            filename = write_wig_text(
                hass.config.config_dir, serialize_wig(result.wig),
                result.wig.name,
            )
            if filename is None:
                return {"success": False, "errors": ["could not write file"]}
            entry = _entry(result.wig, filename)
            entry["comb"] = comb
            entry["dropped_fittings"] = dropped
            out: dict[str, Any] = {
                "success": True,
                "filename": filename,
                "filenames": [filename],
                "files": [entry],
                "format": "wig",
                "skipped": [],
                "folds": [],
                "dropped_fittings": dropped,
            }
            # SUPERSESSION (v0.9.7 Second Fitting). The file is written --
            # it arrived, it files. When it names an ancestor still in
            # this closet, the response also carries the replace-flow
            # invitation. The block is an invitation, not a hold.
            from .wig_save import detect_supersession

            supersession = detect_supersession(
                hass.config.config_dir, result.wig, devices
            )
            if supersession is not None:
                out["supersession"] = supersession
            return out

        # Not a wig: sniff for a foreign format before reporting the
        # wig-schema errors (a SmartIR file failing wig validation is
        # noise; the real answer is "convert it").
        if sniff_format(text) is None:
            return {"success": False, "errors": result.errors}
        converted = convert(text, msg.get("filename", ""))
        if converted.error and not converted.wigs:
            return {"success": False, "errors": [converted.error]}
        # The flash promises "see the wig notes" for skipped signals, so
        # the reasons genuinely go into the notes (owner catch: the
        # pointer used to point at nothing).
        if converted.skipped:
            summary = "; ".join(converted.skipped[:8])
            if len(converted.skipped) > 8:
                summary += f"; and {len(converted.skipped) - 8} more"
            for wig in converted.wigs:
                base = (wig.notes or "").rstrip(". ")
                wig.notes = f"{base}. Import notes: {summary}"[:1900]
        filenames: list[str] = []
        files: list[dict[str, Any]] = []
        for wig in converted.wigs:
            comb = _combed(wig)
            filename = write_wig_text(
                hass.config.config_dir, serialize_wig(wig), wig.name
            )
            if filename is not None:
                filenames.append(filename)
                entry = _entry(wig, filename)
                entry["comb"] = comb
                files.append(entry)
        if not filenames:
            return {"success": False, "errors": ["could not write files"]}
        return {
            "success": True,
            "filename": filenames[0],
            "filenames": filenames,
            "files": files,
            "format": converted.format,
            "skipped": converted.skipped,
            # Named, not silent: the one place import transforms rather
            # than transcodes.
            "folds": converted.folds,
        }

    # Fetched on the loop and handed to the executor job: the arriving
    # wig's ancestry is matched against the devices this closet holds.
    data = _get_first_entry_data(hass)
    store = data.get("store") if data else None
    devices = list(store.get_all_devices()) if store is not None else []
    connection.send_result(
        msg["id"], await hass.async_add_executor_job(_upload)
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/comb",
    vol.Required("filename"): vol.All(str, vol.Length(max=300)),
})
@websocket_api.async_response
async def ws_wigs_comb(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Comb one wig on demand and refresh its receipt.

    Import is where combing pays off most, but a wig is not static: a
    REPLACE changes its codes, and a receipt written before that describes
    codes which no longer exist. This is how the receipt catches up -- and
    how the wigs that predate combing entirely get looked at at all.

    Runs in the executor. A 2,689-cell Mitsubishi is real, the checks walk
    every cell several times, and none of that belongs on the event loop.
    """
    def _comb() -> dict[str, Any] | None:
        from datetime import UTC, datetime

        from .wig_comb import comb_wig, stamp_receipt
        from .wig_format import serialize_wig
        from .wig_store import load_wig, safe_wig_filename, wigs_dir

        filename = msg["filename"]
        if not safe_wig_filename(filename):
            return None
        wig = load_wig(hass.config.config_dir, filename)
        if wig is None:
            return None
        report = comb_wig(wig)
        stamp_receipt(
            wig, report, datetime.now(UTC).date().isoformat()
        )
        path = wigs_dir(hass.config.config_dir) / filename
        if path.is_file():
            path.write_text(serialize_wig(wig), encoding="utf-8")
        return {
            "filename": filename,
            "name": wig.name,
            "matrix": wig.climate is not None,
            **wig.extra["comb"],
        }

    result = await hass.async_add_executor_job(_comb)
    if result is None:
        connection.send_error(msg["id"], "not_found", "Wig not found")
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/delete",
    vol.Required("filename"): vol.All(str, vol.Length(max=300)),
})
@websocket_api.async_response
async def ws_wigs_delete(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a local wig file (user wigs only by construction; library
    codebooks are not files in the closet).

    Bench report (2026-08-06): deleting a wig left every device that
    pointed at it holding a dead ``source_wig_id`` -- UPDATE CLOSET
    WIG kept offering itself on a file that no longer existed, "From:"
    read blank, and the summary line claimed a match it had no file
    left to check. The supersede/replace path already relinks
    affected devices to the successor when a file goes away; a plain
    delete has no successor to relink to, so it clears the pointer
    instead.
    """
    from .wig_store import delete_wig, load_wig

    def _load_id() -> str | None:
        wig = load_wig(hass.config.config_dir, msg["filename"])
        return wig.wig_id if wig is not None else None

    wig_id = await hass.async_add_executor_job(_load_id)

    deleted = await hass.async_add_executor_job(
        delete_wig, hass.config.config_dir, msg["filename"]
    )

    cleared: list[str] = []
    if deleted and wig_id:
        data = _get_first_entry_data(hass)
        if data is not None:
            store = data["store"]
            manager: DeviceManager = data["device_manager"]
            for device in store.get_all_devices():
                if device.source_wig_id == wig_id:
                    device.source_wig_id = None
                    await manager.async_update_device(device)
                    cleared.append(device.id)

    connection.send_result(
        msg["id"], {"deleted": deleted, "devices_cleared": cleared}
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/supersede",
    vol.Required("new_filename"): vol.All(str, vol.Length(max=300)),
    vol.Optional("old_filename", default=""): vol.All(
        str, vol.Length(max=300)
    ),
    vol.Optional("relink", default=True): bool,
    vol.Optional("topup_device_ids", default=list): [
        vol.All(str, vol.Length(max=100))
    ],
    # Second Fitting v3, Commit 5: a diverged, sourced Perfect Fit save
    # already deletes and relinks inside hair/wigs/save's own write
    # (Commit 2's replace: true). The closing screen's top-up offer
    # reaches this same endpoint afterward for the delta alone, no
    # pair, no delete.
    vol.Optional("topup_only", default=False): bool,
})
@websocket_api.async_response
async def ws_wigs_supersede(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Perform the replace a superseding wig invites (v0.9.7), or, with
    ``topup_only`` set (Second Fitting v3, Commit 5), just the topup
    half alone.

    The full path: delete the superseded file, repoint its devices to
    the successor, and top up each chosen device with the arrival's
    rows it lacks. The pair is RE-VERIFIED first -- the old file's id
    must still appear in the new file's ancestry -- because the closet
    can change while the dialog is open, and a stale confirm must
    refuse rather than delete the wrong file. Rows a device already
    has (by digest) are never touched.

    The topup-only path exists because Commit 2's ``replace: true`` on
    ``hair/wigs/save`` already does the delete-and-relink half of this
    inside the SAME write a diverged, sourced Perfect Fit save
    performs -- calling this endpoint's full path afterward would try
    to re-verify and delete a file that is already gone. ``topup_only``
    skips straight to the topup loop against the wig ``new_filename``
    already names: no pair, no delete.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    manager: DeviceManager = data["device_manager"]

    topup_only = bool(msg.get("topup_only", False))
    old_filename = msg.get("old_filename") or ""

    if topup_only:

        def _load_new() -> Any:
            from .wig_store import load_wig

            return load_wig(hass.config.config_dir, msg["new_filename"])

        new_wig = await hass.async_add_executor_job(_load_new)
        if new_wig is None:
            connection.send_error(msg["id"], "not_found", "Wig not found")
            return
        old_id = None
        new_id = new_wig.wig_id
        deleted = False
        relink = False
    else:
        if not old_filename:
            connection.send_error(
                msg["id"], "old_filename_required",
                "old_filename is required unless topup_only is set",
            )
            return

        def _load() -> tuple[Any, Any]:
            from .wig_store import load_wig

            return (
                load_wig(hass.config.config_dir, msg["new_filename"]),
                load_wig(hass.config.config_dir, old_filename),
            )

        new_wig, old_wig = await hass.async_add_executor_job(_load)
        if new_wig is None or old_wig is None:
            connection.send_error(msg["id"], "not_found", "Wig not found")
            return

        old_id = old_wig.wig_id
        new_id = new_wig.wig_id
        # The pair re-verify: the old file's id must still be in the new
        # file's ancestry, or the closet changed under the dialog and this
        # confirm is stale. Refuse cleanly rather than delete the wrong file.
        if not old_id or old_id not in new_wig.supersedes:
            connection.send_error(
                msg["id"], "pair_changed",
                "These wigs are no longer a supersession pair",
            )
            return

        def _delete() -> bool:
            from .wig_store import delete_wig

            return delete_wig(hass.config.config_dir, old_filename)

        deleted = await hass.async_add_executor_job(_delete)
        relink = bool(msg.get("relink", True))

    from .wig_format import signal_row_digest, wig_row_digests

    topup_ids = set(msg.get("topup_device_ids") or [])

    identities: list[Any] | None = None
    findings: dict[str, Any] = {}
    suspects: set[str] = set()
    if topup_ids:
        from .wig_comb import suspect_findings
        from .wig_identity import wig_signal_identities

        identities = await hass.async_add_executor_job(
            wig_signal_identities, new_wig
        )
        findings = suspect_findings(new_wig)
        suspects = set(findings)

    receipts: list[dict[str, Any]] = []
    for device in store.get_all_devices():
        do_relink = (
            relink and old_id is not None and device.source_wig_id == old_id
        )
        do_topup = device.id in topup_ids
        if not (do_relink or do_topup):
            continue
        relinked = False
        if do_relink:
            device.source_wig_id = new_id
            relinked = True
        added = 0
        if do_topup and identities is not None:
            from .wig_export import build_wig_from_device

            build = build_wig_from_device(device)
            have = (
                set(wig_row_digests(build.wig))
                if build.wig is not None else set()
            )
            for i, (sig, ident) in enumerate(
                zip(new_wig.signals, identities, strict=True), start=1
            ):
                # Only the delta: a row the device already has, by digest,
                # is never re-minted (no twin commands on a top-up).
                if ident is None or signal_row_digest(sig) in have:
                    continue
                command = _command_from_wig_signal(
                    sig, ident, suspects, findings, i
                )
                device.add_command(command)
                manager._auto_map_command(device, command)
                added += 1
        await manager.async_update_device(device)
        receipts.append({
            "id": device.id,
            "name": device.name,
            "relinked": relinked,
            "commands_added": added,
        })

    connection.send_result(msg["id"], {
        "deleted": deleted,
        "old_filename": old_filename,
        "new_filename": msg["new_filename"],
        "devices": receipts,
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/claims",
    vol.Required("filename"): vol.All(str, vol.Length(max=300)),
})
@websocket_api.async_response
async def ws_wigs_claims(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """The ledger: who attested what about this wig, in full detail.

    A pure read. It replaced a tab inside the fitting dialog, which
    could reach the rows it was reporting on; this cannot, and there is
    deliberately no companion write command to pair it with. Everything
    in the payload is derived at read time from the claims on the file,
    so an edited row shows up as orphaned the moment it is edited
    rather than whenever somebody remembers to invalidate something.
    """
    # Second Fitting v3 punch list item 8: same key-based "mine" as
    # the Wigs tab summary -- see claims_summary's install_key.
    from .fitting_signing import async_get_public_key

    install_key = await async_get_public_key(hass)

    def _read() -> dict[str, Any] | None:
        from .wig_fitting import claims_ledger
        from .wig_format import parse_wig
        from .wig_store import read_wig_text

        text = read_wig_text(hass.config.config_dir, msg["filename"])
        if text is None:
            return None
        parsed = parse_wig(text)
        if not parsed.ok or parsed.wig is None:
            return None
        return claims_ledger(parsed.wig, install_key)

    ledger = await hass.async_add_executor_job(_read)
    if ledger is None:
        connection.send_error(msg["id"], "not_found", "Wig not found")
        return
    connection.send_result(
        msg["id"], {"filename": msg["filename"], **ledger}
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/get",
    vol.Required("filename"): vol.All(str, vol.Length(max=300)),
})
@websocket_api.async_response
async def ws_wigs_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Raw file text for the editor popover's download / copy-JSON.

    These are the SHARE paths, and they hand back the file BYTE FOR
    BYTE. They used to strip first: while a fitting was a session, a
    file could carry a draft or a half-walked checklist, and shipping
    one of those to a stranger would have shared progress dressed as an
    attestation. v0.9.5 deleted the state that made stripping necessary
    -- a fitting is now a bundle of claims written once at save, so
    nothing on disk is ever mid-flight, and every claim on the file is
    already something somebody signed and meant. Handing back the
    original bytes is therefore both simpler and more honest, and it
    keeps hand-authored formatting intact on an ordinary download."""
    def _read() -> tuple[str | None, str | None]:
        from .wig_format import download_filename, parse_wig
        from .wig_store import read_wig_text

        text = read_wig_text(hass.config.config_dir, msg["filename"])
        if text is None:
            return None, None
        # The download name comes from the wig's own fields (v0.9.7), so
        # it needs the parsed wig. A file that will not parse still
        # downloads under its on-disk name rather than failing the share.
        result = parse_wig(text)
        dl = (
            download_filename(result.wig)
            if result.wig is not None else msg["filename"]
        )
        return text, dl

    text, dl = await hass.async_add_executor_job(_read)
    if text is None:
        connection.send_error(msg["id"], "not_found", "Wig not found")
        return

    connection.send_result(
        msg["id"],
        {
            "filename": msg["filename"],
            "text": text,
            "download_filename": dl,
        },
    )


# Identifier keys editable through the update/export dialogs. UI
# sends single strings; commas split into the format's list form
# (rebadged families carry several UPCs -- wig_format rationale).
_WS_IDENTIFIER_KEYS = ("fcc_id", "upc", "asin", "oem")


def _parse_identifier_input(value: str) -> str | list[str] | None:
    """Dialog input -> identifiers value: None / single / comma list."""
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else parts


def _apply_identifier_edits(wig: Any, msg: dict[str, Any]) -> None:
    """Fold the dialog's identifier fields into ``wig.identifiers``.

    A field absent from the message is untouched; present-but-empty
    clears the key; the block drops entirely when nothing remains
    (absent stays absent -- wig_format contract). Keys outside the
    blessed set (hand-authored) are preserved untouched.
    """
    if not any(key in msg for key in _WS_IDENTIFIER_KEYS):
        return
    identifiers = dict(wig.identifiers or {})
    for key in _WS_IDENTIFIER_KEYS:
        if key not in msg:
            continue
        parsed = _parse_identifier_input(msg[key])
        if parsed is None:
            identifiers.pop(key, None)
        else:
            identifiers[key] = parsed
    wig.identifiers = identifiers or None


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/update",
    vol.Required("filename"): vol.All(str, vol.Length(max=300)),
    vol.Optional("name"): vol.All(str, vol.Length(min=1, max=200)),
    vol.Optional("brand"): vol.All(str, vol.Length(max=200)),
    vol.Optional("model"): vol.All(str, vol.Length(max=200)),
    vol.Optional("notes"): vol.All(str, vol.Length(max=2000)),
    vol.Optional("kind"): vol.All(str, vol.Length(max=100)),
    vol.Optional("fcc_id"): vol.All(str, vol.Length(max=200)),
    vol.Optional("upc"): vol.All(str, vol.Length(max=200)),
    vol.Optional("asin"): vol.All(str, vol.Length(max=200)),
    vol.Optional("oem"): vol.All(str, vol.Length(max=200)),
})
@websocket_api.async_response
async def ws_wigs_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Editor popover SAVE: update name/brand/model/notes in place.

    The file keeps its filename (renaming on every name edit would break
    anything the user points at the path); signals and unknown keys ride
    through untouched via the parser's preservation contract. An empty
    string clears an optional field."""
    def _update() -> dict[str, Any]:
        from .wig_format import serialize_wig
        from .wig_store import (
            load_wig,
            safe_wig_filename,
            wigs_dir,
        )

        filename = msg["filename"]
        wig = load_wig(hass.config.config_dir, filename)
        if wig is None or not safe_wig_filename(filename):
            return {"success": False, "errors": ["wig not found"]}
        if "name" in msg:
            wig.name = msg["name"].strip() or wig.name
        for key in ("brand", "model", "notes"):
            if key in msg:
                setattr(wig, key, msg[key].strip() or None)
        if "kind" in msg:
            from .wig_format import kind_slug

            wig.kind = kind_slug(msg["kind"]) or None
        _apply_identifier_edits(wig, msg)
        path = wigs_dir(hass.config.config_dir) / filename
        path.write_text(serialize_wig(wig), encoding="utf-8")
        return {"success": True, "filename": filename}

    connection.send_result(
        msg["id"], await hass.async_add_executor_job(_update)
    )


# ---------------------------------------------------------------------------
# SAVE TO CLOSET (v0.9.5 Fitting Room): plan, then save
# ---------------------------------------------------------------------------
# Two commands, replacing the fitting family. ``save_plan`` answers what
# the dialog should draw -- CREATE or UPDATE, which rows matched, which
# wig rows nothing covers, what metadata to prefill. ``save`` performs
# it with the person's explicit answers. Nothing is remembered between
# the two: the plan is a photograph, not a session, and a save that
# disagrees with a stale plan simply reports what it actually did.


def _resolve_source(
    hass: HomeAssistant, device: IRDevice
) -> tuple[Any | None, str | None]:
    """The closet wig this device was adopted from, and its filename.

    Resolves by ``wig_id``, never by filename, so renaming a closet file
    does not orphan a device. (None, None) when the device has no source
    or the file is gone; the caller degrades to CREATE and says so.
    """
    if not device.source_wig_id:
        return None, None
    from .wig_store import find_wig_by_id, load_wig

    filename = find_wig_by_id(hass.config.config_dir, device.source_wig_id)
    if filename is None:
        return None, None
    return load_wig(hass.config.config_dir, filename), filename


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/save_plan",
    vol.Required("device_id"): vol.All(str, vol.Length(max=100)),
})
@websocket_api.async_response
async def ws_wigs_save_plan(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """What SAVE TO CLOSET is about to do, for the dialog to draw."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    device = data["store"].get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "HAIR device not found")
        return


    manager: DeviceManager = data["device_manager"]
    matrix = (
        await manager.async_get_matrix(device.id)
        if device.climate_matrix else None
    )
    # This install's public key, for the same-key re-sign notice
    # (Second Fitting v3 punch list, item 1). Fetched here, on the loop,
    # because the storage read is async; handed to the executor job
    # below rather than looked up from inside it.
    from .fitting_signing import async_get_public_key

    signing_key_b64 = await async_get_public_key(hass)
    # Off the loop: resolving the source scans the closet and the
    # checklist decodes a dozen or two prontos. Bounded, but not free,
    # and this runs on a human's click rather than a timer.
    plan = await hass.async_add_executor_job(
        _build_plan, hass, device, matrix, signing_key_b64
    )
    connection.send_result(msg["id"], plan.as_dict())


def _build_plan(
    hass: HomeAssistant,
    device: IRDevice,
    matrix: Any,
    signing_key_b64: str | None = None,
) -> Any:
    from .wig_save import build_save_plan
    from .wig_store import scan_wigs

    source_wig, filename = _resolve_source(hass, device)
    # Bench addendum (2026-08-05): the shelf, for a SUCCESSION's
    # differentiated default name to count past. Already off the loop
    # (see the executor-job comment on the caller below), so one more
    # directory scan alongside the source-wig resolve is the same
    # tradeoff already made there, not a new one.
    existing_names = [
        loaded.wig.name for loaded in scan_wigs(hass.config.config_dir).wigs
    ]
    return build_save_plan(
        device, source_wig, filename, matrix, existing_names,
        signing_key_b64,
    )


_CLAIM_SCHEMA = vol.Schema({
    vol.Required("digest"): vol.All(str, vol.Length(max=64)),
    vol.Required("verdict"): vol.In(list(VERDICTS)),
})

_RENAME_SCHEMA = vol.Schema({
    vol.Required("digest"): vol.All(str, vol.Length(max=64)),
    vol.Required("alias_at_claim"): vol.All(str, vol.Length(max=200)),
    vol.Required("alias"): vol.All(str, vol.Length(max=200)),
})

_ATTEST_SCHEMA = vol.Schema({
    vol.Required("claims"): [_CLAIM_SCHEMA],
    vol.Optional("handle"): vol.All(str, vol.Length(max=200)),
    vol.Optional("github"): vol.All(str, vol.Length(max=200)),
    vol.Optional("note"): vol.All(str, vol.Length(max=2000)),
    vol.Optional("renames"): [_RENAME_SCHEMA],
})


def _attestation_from(msg: dict[str, Any]) -> Any | None:
    raw = msg.get("attest")
    if not raw:
        return None
    from .wig_claims import RenameProposal
    from .wig_save import Attestation

    return Attestation(
        # Later claims about the same row win. A dialog cannot produce
        # two verdicts for one digest, so this only bites a hand-rolled
        # caller, and last-one-wins is the least surprising of the ways
        # to resolve it.
        claims={c["digest"]: c["verdict"] for c in raw["claims"]},
        handle=(raw.get("handle") or "").strip() or None,
        github=(raw.get("github") or "").strip() or None,
        note=(raw.get("note") or "").strip() or None,
        renames=[
            RenameProposal(
                digest=r["digest"],
                alias_at_claim=r["alias_at_claim"],
                alias=r["alias"].strip(),
            )
            for r in raw.get("renames") or []
            if r["alias"].strip()
        ],
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/save",
    vol.Required("device_id"): vol.All(str, vol.Length(max=100)),
    #: Second Fitting v3 punch list item 2: the one explicit route
    #: signal from the caller. The verb (CREATE / UPDATE /
    #: SUCCESSION) is still derived server-side from device-vs-source
    #: digest comparison for every route except this one -- "create"
    #: means the caller chose SAVE AS NEW at the decision window
    #: fork, which mints unconditionally regardless of what the
    #: fresh derivation says, and never auto-replaces the source wig
    #: even when "replace" rides along in the same payload. Any
    #: other value, or absent, is ignored; the derivation still
    #: governs.
    vol.Optional("mode"): vol.In(["create", "update"]),
    vol.Optional("name"): vol.All(str, vol.Length(max=200)),
    vol.Optional("brand"): vol.All(str, vol.Length(max=200)),
    vol.Optional("model"): vol.All(str, vol.Length(max=200)),
    vol.Optional("notes"): vol.All(str, vol.Length(max=2000)),
    vol.Optional("kind"): vol.All(str, vol.Length(max=100)),
    vol.Optional("fcc_id"): vol.All(str, vol.Length(max=200)),
    vol.Optional("upc"): vol.All(str, vol.Length(max=200)),
    vol.Optional("asin"): vol.All(str, vol.Length(max=200)),
    vol.Optional("oem"): vol.All(str, vol.Length(max=200)),
    vol.Optional("attest"): _ATTEST_SCHEMA,
    #: MATRIX UPDATE: send the repaired lattice upstream. Explicit,
    #: because a content proposal is a different act from attesting.
    vol.Optional("propose_lattice"): bool,
    #: Second Fitting v3: the decision window's UPDATE CLOSET WIG route
    #: sets this when its own fetched plan says the device has diverged
    #: -- the caller declaring "I mean to override", not a literal
    #: instruction taken on faith. The server re-derives the plan fresh
    #: (below) and only acts on this when that fresh check still agrees;
    #: see ws_wigs_save's docstring.
    vol.Optional("replace"): bool,
})
@websocket_api.async_response
async def ws_wigs_save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Save a device to the closet: a new wig, its own successor, or
    claims onto its source.

    THE VERB IS DERIVED (Second Fitting amendment v2, owner-ruled on
    the bench 2026-08-04), not taken from the caller. UPDATE only when
    the device's commands still match its source wig's rows by digest;
    any addition or removal is SUCCESSION, which mints a successor
    instead of attesting a row set the device has outgrown; no source
    is CREATE. Deriving it fresh here -- the same computation the
    save_plan preview just showed the dialog -- means a stale client
    cannot steer a save down a verb the device no longer supports, and
    a race where the device changed while the dialog sat open resolves
    exactly as a fresh preview would.

    Second Fitting v3 adds ``replace`` (below): the decision window's
    UPDATE CLOSET WIG route sets it when the plan it already fetched
    says the device has diverged, meaning the click means "mint the
    successor and immediately override" rather than the old two-step
    of minting, then confirming a supersede separately. The verb is
    still derived fresh right here, never taken from ``replace``
    itself -- a stale ``replace: true`` against a device that turns out
    to match its source (changed while the dialog sat open) refuses
    rather than silently doing an unintended plain update.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    device = data["store"].get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "HAIR device not found")
        return

    from .fitting_signing import async_get_private_key

    attestation = _attestation_from(msg)
    key = await async_get_private_key(hass) if attestation else None

    manager: DeviceManager = data["device_manager"]
    matrix = (
        await manager.async_get_matrix(device.id)
        if device.climate_matrix else None
    )

    # A matrix bundle binds the lattice as a set, because a sampled
    # checklist vouches for the set rather than for the rows it walked.
    # STAMPED HERE, from the matrix this server just read -- never
    # carried back from the dialog. A claim about a lattice must bind
    # the lattice that exists, not one the caller says it saw.
    if attestation is not None and matrix is not None:
        from .wig_format import cells_content_hash

        attestation.cells_hash = cells_content_hash(matrix)

    # Off the loop, same as the save_plan preview: resolving the source
    # scans the closet and the plan decodes the checklist.
    plan = await hass.async_add_executor_job(_build_plan, hass, device, matrix)

    from .wig_save import VARIANT_UPDATE

    replace = bool(msg.get("replace", False))

    # Second Fitting v3 punch list item 2: "create" is the caller
    # saying SAVE AS NEW was the route chosen at the decision window
    # fork. That route always mints, never replaces -- so it skips
    # the UPDATE branch below entirely, and any "replace" riding
    # along in the same payload is dropped rather than honored, since
    # Save As New leaves the existing wig untouched by ruling.
    force_create = msg.get("mode") == "create"
    if force_create:
        replace = False

    if plan.variant == VARIANT_UPDATE and not force_create:
        if replace:
            # The caller's plan said SUCCESSION when the dialog opened;
            # this server's fresh derivation says the device now
            # matches its source. Something changed underneath the
            # dialog -- refuse rather than guess which the caller meant.
            connection.send_error(
                msg["id"], "not_diverged",
                "This device now matches its source wig; there is "
                "nothing to replace. Close and reopen to see the "
                "current state.",
            )
            return
        await _do_update(hass, connection, msg, device, attestation, key)
    else:
        # CREATE and SUCCESSION are the same act at this layer: mint a
        # wig from the device's current commands and attest against
        # its own rows. What makes SUCCESSION a succession -- the
        # ancestry stamp, the supersession detection -- is entirely a
        # function of device.source_wig_id, which _do_create already
        # reads (Commits 2 and 5). Nothing here needs to say which one
        # this is. ``replace`` rides along and only fires when the
        # mint actually names a local ancestor to supersede -- a
        # from-scratch device has none, so it is inert there.
        # Also reached whenever force_create routed this here
        # instead of the UPDATE branch above -- replace is already
        # forced False in that case, so this call never
        # auto-supersedes on the Save As New route (item 2:
        # existing wig untouched).
        await _do_create(
            hass, connection, msg, device, attestation, key, replace=replace,
        )


async def _do_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    device: IRDevice,
    attestation: Any | None,
    key: str | None,
) -> None:
    manager: DeviceManager = _get_first_entry_data(hass)["device_manager"]
    device_matrix = (
        await manager.async_get_matrix(device.id)
        if device.climate_matrix else None
    )

    def _write() -> dict[str, Any] | str:
        from .wig_save import lattice_diff, reject_flat_exclusions, update_text
        from .wig_store import (
            find_wig_by_id,
            load_wig,
            read_wig_text,
            wigs_dir,
        )

        filename = find_wig_by_id(
            hass.config.config_dir, device.source_wig_id or ""
        )
        if filename is None:
            return "source_missing"
        text = read_wig_text(hass.config.config_dir, filename)
        wig = load_wig(hass.config.config_dir, filename)
        if text is None or wig is None:
            return "source_missing"

        if reject_flat_exclusions(attestation, wig):
            return "exclusion_on_flat_row"

        # Metadata edits are a legitimate content PR (plan Section 4:
        # they ride the PR as reviewed changes), so an update carries
        # them even with no fitting attached. What hard rule 3 protects
        # is the SIGNALS block; a brand correction touches none of it.
        changes = lattice_diff(device_matrix, wig.climate)
        propose = bool(msg.get("propose_lattice")) and bool(changes)

        # THE GATE. A checklist bundle binds cells_hash, which is a
        # SET, so a lattice that has moved away from the wig's cannot
        # be attested as-is: signing would bind bytes the fitter never
        # tested. Proposing the repair resolves it, because then the
        # lattice being bound is the one going into the file.
        if attestation is not None and changes and not propose:
            return "lattice_diverged"

        edits = _metadata_edits(wig, msg)
        if attestation is None and not propose and not edits:
            # NOW the refusal is honest: nothing was attested and
            # nothing was changed, so writing would produce a shop PR
            # that says nothing.
            return "nothing_to_update"

        written = update_text(
            text, wig, attestation, key,
            mutate=(lambda w: _apply_metadata(w, edits)) if edits else None,
            device_matrix=device_matrix,
            cell_changes=changes if propose else None,
        )
        if written is None:
            return "source_missing"
        new_text, result = written
        (wigs_dir(hass.config.config_dir) / filename).write_text(
            new_text, encoding="utf-8"
        )
        result.filename = filename
        result.notes = [*result.notes, *(
            [f"metadata: {', '.join(sorted(edits))}"] if edits else []
        )]
        return result.as_dict()

    result = await hass.async_add_executor_job(_write)
    if isinstance(result, str):
        connection.send_error(
            msg["id"], result,
            _UPDATE_REFUSALS.get(
                result, "Nothing to write: no fitting, and nothing changed"
            ),
        )
        return
    connection.send_result(msg["id"], result)


_UPDATE_REFUSALS = {
    "source_missing":
        "The wig this device came from is not in the closet",
    "lattice_diverged":
        "This device's states no longer match the wig's. Propose the "
        "changes, save as a new wig, or save without attesting.",
    "nothing_to_update":
        "Nothing to write: no fitting, and nothing changed",
    "exclusion_on_flat_row":
        "An exclusion reason can only be given on a matrix checklist "
        "cell.",
}


#: Metadata the save dialog may edit on an UPDATE. Identifiers ride
#: separately through _apply_identifier_edits, which owns the
#: comma-to-list parsing every other surface already uses.
_META_FIELDS = ("name", "brand", "model", "notes", "kind")
_IDENT_FIELDS = _WS_IDENTIFIER_KEYS


def _metadata_edits(wig: Any, msg: dict[str, Any]) -> dict[str, str]:
    """Which submitted metadata fields DIFFER from what the wig says.

    Compared rather than assumed, because the dialog prefills from the
    wig and sends every field back. Treating "present" as "changed"
    would make an untouched dialog claim a metadata change, and the one
    thing an attestation PR must not look like is a content change.
    """
    edits: dict[str, str] = {}
    for key in _META_FIELDS:
        if key not in msg:
            continue
        value = msg[key].strip()
        current = getattr(wig, key, None) or ""
        if key == "name" and not value:
            # A wig with no name is not a thing the format allows, so a
            # cleared box means "leave it", not "erase it".
            continue
        if value != current:
            edits[key] = value
    identifiers = wig.identifiers or {}
    for key in _IDENT_FIELDS:
        if key not in msg:
            continue
        value = msg[key].strip()
        current = identifiers.get(key)
        current = ", ".join(current) if isinstance(current, list) else (
            current or ""
        )
        if value != current:
            edits[key] = value
    return edits


def _apply_metadata(wig: Any, edits: dict[str, str]) -> None:
    for key in _META_FIELDS:
        if key not in edits:
            continue
        if key == "kind":
            from .wig_format import kind_slug

            wig.kind = kind_slug(edits[key]) or None
        else:
            setattr(wig, key, edits[key] or None)
    if any(key in edits for key in _IDENT_FIELDS):
        _apply_identifier_edits(wig, edits)


async def _do_create(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    device: IRDevice,
    attestation: Any | None,
    key: str | None,
    replace: bool = False,
) -> None:
    """Mint the wig (CREATE or SUCCESSION); optionally auto-replace.

    ``replace`` (Second Fitting v3) asks that, when this mint names a
    local ancestor to supersede, the supersede runs immediately after
    the write -- the same act ``ws_wigs_supersede`` performs, folded
    into this one round trip instead of a second confirm. It is inert
    whenever the mint does not turn out to be a supersession: a
    from-scratch device stamps no ancestry, so ``detect_supersession``
    finds nothing to replace, and ``replace`` simply does nothing.
    """
    from .wig_export import build_wig_from_device

    data = _get_first_entry_data(hass)
    manager: DeviceManager = data["device_manager"]
    store = data.get("store")
    devices = list(store.get_all_devices()) if store is not None else []
    matrix = (
        await manager.async_get_matrix(device.id)
        if device.climate_matrix else None
    )
    build = build_wig_from_device(device, matrix)
    if build.wig is None:
        connection.send_error(
            msg["id"], "no_signals", "No exportable signals on that device"
        )
        return
    from .wig_save import reject_flat_exclusions

    if reject_flat_exclusions(attestation, build.wig):
        connection.send_error(
            msg["id"], "exclusion_on_flat_row",
            "An exclusion reason can only be given on a matrix "
            "checklist cell.",
        )
        return
    if msg.get("name", "").strip():
        build.wig.name = msg["name"].strip()
    for field_name in ("brand", "model", "notes"):
        if msg.get(field_name, "").strip():
            setattr(build.wig, field_name, msg[field_name].strip())
    if msg.get("kind", "").strip():
        from .wig_format import kind_slug

        build.wig.kind = kind_slug(msg["kind"]) or build.wig.kind
    _apply_identifier_edits(build.wig, msg)

    def _write() -> dict[str, Any] | None:
        from .wig_format import compose_supersedes
        from .wig_save import create_text
        from .wig_store import write_wig_text

        # SUPERSESSION STAMP (v0.9.7 Second Fitting). A sourced device
        # saved as new is a successor: its ancestry is the source id,
        # then the source file's own ancestry when that file still
        # resolves locally (the chain extends), or the source id alone
        # when it does not (source_missing -- the one link still known to
        # be true). A from-scratch device (no source) stamps nothing. The
        # head is the DEVICE's source id, never the resolved file's
        # current id: the two differ once the closet copy is itself
        # replaced, and the device's pointer is the honest parent.
        if device.source_wig_id:
            source_wig, _ = _resolve_source(hass, device)
            build.wig.supersedes = compose_supersedes(
                device.source_wig_id,
                source_wig.supersedes if source_wig is not None else None,
            )

        text, result = create_text(build, attestation, key)
        filename = write_wig_text(
            hass.config.config_dir, text, build.wig.name
        )
        if filename is None:
            return None
        result.filename = filename
        out = result.as_dict()
        # SUPERSESSION second doorway (v0.9.7 Second Fitting). A
        # self-superseded wig is born in the closet without ever touching
        # the drop bar -- the person who adds an eighth button to their
        # own perfect-fitted wig and saves as new. When the wig just
        # written names an ancestor still local, the response carries the
        # SAME block the upload path returns, so the same dialog fires.
        from .wig_save import detect_supersession

        supersession = detect_supersession(
            hass.config.config_dir, build.wig, devices
        )
        if supersession is not None:
            out["supersession"] = supersession
            if replace:
                # Second Fitting v3: UPDATE CLOSET WIG on diverged
                # content auto-replaces -- the user already chose this
                # by picking that route, so there is no second confirm
                # to wait for. Same pair re-verify ws_wigs_supersede
                # does: the old file's id must still be in the new
                # file's ancestry, belt-and-suspenders against a race
                # inside this same write.
                from .wig_store import delete_wig, load_wig

                old_filename = supersession["old_filename"]
                old_wig = load_wig(hass.config.config_dir, old_filename)
                old_id = old_wig.wig_id if old_wig is not None else None
                if old_id and old_id in build.wig.supersedes:
                    deleted = delete_wig(hass.config.config_dir, old_filename)
                    out["replaced"] = {
                        "old_filename": old_filename,
                        "old_name": supersession["old_name"],
                        "deleted": deleted,
                        # Relinking touches HA's device registry, which
                        # needs the event loop -- collected here, acted
                        # on by the caller once this executor job
                        # returns.
                        "device_ids": [
                            d.id for d in devices if d.source_wig_id == old_id
                        ],
                    }
        return out

    result = await hass.async_add_executor_job(_write)
    if result is None:
        connection.send_error(
            msg["id"], "write_failed", "Could not write the wig file"
        )
        return

    # The device now has a wig in the closet, so it remembers it: the
    # next SAVE TO CLOSET offers UPDATE instead of minting a second copy
    # of something that already exists. Saving as new later is still
    # available, behind the confirm, which is where that decision
    # belongs.
    if result.get("wig_id"):
        device.source_wig_id = result["wig_id"]
        await manager.async_update_device(device)

    replaced = result.get("replaced")
    if replaced:
        receipts: list[dict[str, Any]] = []
        for device_id in replaced.pop("device_ids", []):
            relinked_device = store.get_device(device_id) if store else None
            if relinked_device is None:
                continue
            relinked_device.source_wig_id = result["wig_id"]
            await manager.async_update_device(relinked_device)
            receipts.append({
                "id": relinked_device.id, "name": relinked_device.name,
            })
        replaced["devices"] = receipts

    connection.send_result(msg["id"], result)


# ---------------------------------------------------------------------------
# Fitting (Perfect Fit): the closet's proving ground
# ---------------------------------------------------------------------------
# Session state lives in the wig file itself (fitting-flow.md 13.3);
# these four commands are thin delegates to FittingManager. The user's
# HA username keys the draft, so two admins fitting the same wig hold
# independent drafts.



def _fitting_username(connection: websocket_api.ActiveConnection) -> str:
    user = getattr(connection, "user", None)
    name = getattr(user, "name", None)
    # Stripped: HA display names can carry stray whitespace ("David "
    # on the live test box), and the finish path strips handles -- an
    # unstripped username here would fork resume-matching.
    return (name or "").strip() or "user"



def _arm_listen(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    capture_event: str,
    timeout_event: str,
) -> None:
    """Arm the Sniffer for one capture into a Replace box.

    A subscription, not a one-shot: the window has to be cancellable
    from the dialog (Cancel, or simply closing it), and the house
    already listens this way for capture sessions. Emits exactly one
    capture event or one timeout event, then stops.

    It rides ``signal_monitor``'s existing subscriber feed rather than
    opening a second capture path. That feed also carries MIRROR rows,
    which matters more than it sounds: every send HAIR makes echoes
    back through it, so without the Mirror filter below, pressing SEND
    on the row being replaced would land HAIR's own transmission in the
    box and present it as the remote's.

    The event NAMES are the only thing that differs between callers,
    because listening is genuinely context-free: it hears whatever the
    room emits and hands back one Pronto. What the caller does with it
    -- fill a fitting row, fill a command-edit box -- is the caller's
    business, and pretending the subscription knew would be inventing a
    scope it does not have.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    monitor = data["signal_monitor"]
    signal_store = data["signal_store"]
    msg_id = msg["id"]
    state: dict[str, Any] = {"done": False, "timer": None}

    def _finish() -> None:
        state["done"] = True
        monitor.unsubscribe(_on_signal)
        timer = state.pop("timer", None)
        if timer is not None:
            timer.cancel()
        connection.subscriptions.pop(msg_id, None)

    @callback
    def _on_signal(summary: dict[str, Any]) -> None:
        if state["done"]:
            return
        # HAIR's own transmissions, and the foreign ones it audits: the
        # Mirror logs what was SENT, never what a remote pressed.
        if summary.get("device_fingerprint") == MIRROR_DEVICE_FP:
            return
        device = signal_store.get_device(summary.get("device_id") or "")
        signal = (
            device.get_signal_by_id(summary.get("signal_id") or "")
            if device is not None else None
        )
        pronto = getattr(signal, "code", None)
        if (
            signal is None
            or getattr(signal, "protocol", None) != "PRONTO"
            or not pronto
        ):
            # Raw timings that would not encode to Pronto: nothing to
            # put in the box, so keep listening rather than closing the
            # window with nothing in it.
            return
        heard = getattr(signal, "heard_by", None) or []
        _finish()
        connection.send_event(msg_id, {
            "type": capture_event,
            "pronto": pronto,
            "decoded": bool(getattr(signal, "decoded_fingerprint", None)),
            "protocol": getattr(signal, "decoded_protocol", None),
            "receiver": heard[-1] if heard else None,
        })

    @callback
    def _on_timeout() -> None:
        if state["done"]:
            return
        _finish()
        connection.send_event(msg_id, {"type": timeout_event})

    monitor.subscribe(_on_signal)
    state["timer"] = hass.loop.call_later(
        FITTING_LISTEN_TIMEOUT_S, _on_timeout
    )
    connection.subscriptions[msg_id] = _finish
    connection.send_result(msg_id, {"listening": True})



@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/listen",
})
@callback
def ws_command_listen(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Arm the Sniffer for one capture into the command editor.

    Replace moved to where it always belonged: editing a command on
    device detail. Grab a code live from the air or paste one, in place.
    A heard code populates the Pronto box directly -- there is no accept
    step, because the box IS the accept: the validation line and the
    protocol pill re-evaluate against it, listening again re-captures,
    and nothing commits until Save.
    """
    _arm_listen(
        hass, connection, msg, "command_capture", "command_listen_timeout"
    )


def _row_protocol(pronto: str) -> str | None:
    """Decode one fitting row's protocol name, or None.

    Wigs carry no decoded fields by design, so the name has to be
    derived on read. Bounded work: a signal wig runs tens of rows and a
    matrix wig runs the 12-to-20-row dimension checklist, never the full
    lattice. Runs inside the executor read.
    """
    from .ir_command import ProntoCommand
    from .protocol_decode import try_decode_identity

    try:
        timings = ProntoCommand(pronto).get_raw_timings()
    except Exception:
        return None
    identity = try_decode_identity(timings)
    return identity.protocol if identity else None



# ---------------------------------------------------------------------------
# Adopt Device (v0.8.1): a wig becomes a HAIR device in one step
# ---------------------------------------------------------------------------


def _wig_linked_devices(
    wig: Any,
    assignment_index: list[tuple[SignalIdentity, dict[str, str]]],
    hair_devices: list[IRDevice] | None = None,
) -> list[dict[str, str]]:
    """The HAIR devices this wig's codes already live in.

    The wig-side sibling of ``_linked_hair_devices``. Two ways in, and
    a matrix wig needs the second one:

    IDENTITY. Every flat signal in the wig, matched pairwise against
    every HAIR command. Many-to-many falls out of this for free -- adopt
    one wig twice, living room and bedroom, and both devices chip up.

    THE STORED POINTER. ``IRDevice.source_wig_id`` is the wig's UUID,
    written at adopt and never by hand. This used to say there was no
    such pointer, which stopped being true in v0.9.5.

    Adding it is not a nicety. A MATRIX WIG HAS NO FLAT SIGNALS -- its
    codes are lattice cells, and cells are not commands, so neither side
    of the identity match has anything to compare (Samsung AR: 0
    signals, 750 cells). Every matrix wig therefore read as adopted by
    nobody, forever: the closet's linked chip stayed dark, the adopt
    popover never appeared, and the comb report went on offering ADOPT
    to a wig already sitting on a device (bench 2026-08-03).

    Matching the lattice by identity instead would mean deriving an
    identity for several hundred cells on both sides of a pairwise scan,
    on a call that runs every time the closet lists. The pointer is
    exact, already written, and costs one comparison per device.

    THE POINTER WINS (Second Fitting v3 punch list item 7). A device
    that already carries a ``source_wig_id`` chips ONLY the wig it
    points to. Identity matching is a fallback for devices with no
    pointer at all -- it must never ALSO chip a pointed device onto
    some other wig just because a signal happens to still content-match
    there (e.g. a Save as New repoint where the untouched flat rows
    still identity-match the retired ancestor). Without this, a moved
    device double-chipped both its old and new wig forever.
    """
    linked: dict[str, str] = {}
    wig_id = getattr(wig, "wig_id", None)
    pointed_device_ids: set[str] = set()
    for device in hair_devices or []:
        if device.source_wig_id:
            pointed_device_ids.add(device.id)
        if wig_id and device.source_wig_id == wig_id:
            linked[device.id] = device.name

    from .wig_identity import wig_signal_identities

    for ident in wig_signal_identities(wig):
        if ident is None:
            continue
        identity = SignalIdentity(
            ident.decoded_fingerprint, ident.byte_hash, ident.fingerprint
        )
        for entry_identity, payload in assignment_index:
            if payload["device_id"] in pointed_device_ids:
                continue
            if identity.same_as(entry_identity):
                linked[payload["device_id"]] = payload["device_name"]
    return [
        {"device_id": did, "device_name": name}
        for did, name in linked.items()
    ]


def _wig_linked_remotes(
    wig: Any,
    trigger_index: list[tuple[SignalIdentity, dict[str, str]]],
    trigger_remotes: list[TriggerRemote] | None = None,
) -> list[dict[str, str]]:
    """The named Remotes this wig's codes already live in.

    The wig-side sibling of ``_linked_hair_remotes``, mirroring
    ``_wig_linked_devices``'s pointer-wins design exactly (signpost 3,
    Track 2 item 4). ``TriggerRemote.source_wig_id`` is the remote-side
    twin of ``IRDevice.source_wig_id``: a remote carrying the pointer
    chips ONLY the wig it points to, and identity matching is the
    fallback for remotes with no pointer at all (codebook-made remotes,
    or ones made before this field existed) -- same reasoning as the
    device side's matrix-wig fix (a matrix wig's cells are not flat
    signals, so a remote made from one may have nothing to identity-
    match with).
    """
    linked: dict[str, str] = {}
    wig_id = getattr(wig, "wig_id", None)
    pointed_remote_ids: set[str] = set()
    for remote in trigger_remotes or []:
        if remote.source_wig_id:
            pointed_remote_ids.add(remote.id)
        if wig_id and remote.source_wig_id == wig_id:
            linked[remote.id] = remote.name

    from .wig_identity import wig_signal_identities

    for ident in wig_signal_identities(wig):
        if ident is None:
            continue
        identity = SignalIdentity(
            ident.decoded_fingerprint, ident.byte_hash, ident.fingerprint
        )
        for entry_identity, payload in trigger_index:
            if payload["remote_id"] in pointed_remote_ids:
                continue
            if identity.same_as(entry_identity):
                linked[payload["remote_id"]] = payload["remote_name"]
    return [
        {"remote_id": rid, "remote_name": name}
        for rid, name in linked.items()
    ]


def _command_from_wig_signal(
    sig: Any, ident: Any, suspects: set[str], findings: dict[str, Any],
    index: int,
) -> Any:
    """Mint one device command from a wig signal + its decoded identity.

    THE adopt machinery for turning a wig row into a command, shared by
    Adopt Device and the supersession top-up so the two can never drift:
    same naming, same decoded fields, same send/ditto/bypass carriage,
    same comb flags. The wig STATES what each row needs, so the catalog
    defaults never overrule it.
    """
    from .models import CaptureResult, CommandCategory

    capture = CaptureResult(
        protocol="PRONTO",
        code=ident.pronto,
        raw_timings=list(ident.raw_timings),
        frequency=ident.frequency,
    )
    name = sig.alias.strip() or f"Signal {index}"
    command = capture.to_command(name, CommandCategory.CUSTOM)
    # WHERE THE BYTES CAME FROM (2026-08-18). ``to_command`` stamps
    # CAPTURED for every caller, which is true of a sniffed row and of
    # nothing here: this command came out of a wig file and never
    # crossed the air. The receiver-tolerant identity tier reads this
    # field, and IMPORTED is the value the enum already has for it (the
    # panel renders no chip for it; the STATE chip is gated on "matrix"
    # alone).
    command.source = CommandSource.IMPORTED
    command.byte_hash = ident.byte_hash
    command.decoded_protocol = ident.decoded_protocol
    command.decoded_address = ident.decoded_address
    command.decoded_command = ident.decoded_command
    command.decoded_fingerprint = ident.decoded_fingerprint
    command.decoded_extras = (
        dict(ident.decoded_extras) if ident.decoded_extras else None
    )
    # The wig states what a row needs, per signal, so that is what the
    # device gets -- explicit 0 ditto included, or the catalog default
    # would resurrect a repeat the wig says nothing about.
    command.send_count = max(1, sig.send_count or 1)
    command.tx_force_raw = sig.bypass_protocol
    command.repeat_count = sig.ditto_count
    # Keyed by the wig's alias, which is what the comb recorded and what
    # this command was just named after; a later rename does not clear it.
    command.comb_suspect = sig.alias in suspects
    command.comb_finding = findings.get(sig.alias)
    return command


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/make-device",
    vol.Exclusive("filename", "wig_source"): vol.All(
        str, vol.Length(max=300)
    ),
    vol.Exclusive("codebook_id", "wig_source"): vol.All(
        str, vol.Length(max=300)
    ),
    vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)),
    vol.Required("device_type"): str,
    vol.Required("emitter_entity_ids"): [str],
})
@websocket_api.async_response
async def ws_wig_make_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Adopt Device: create a HAIR device straight from a closet wig.

    Direct copy, NO Clipper residue (owner ruling 2026-07-21): every
    wig signal becomes a command named by its alias, identities stamped
    fresh from the wig's Pronto, auto-mapped so entity features light
    up. Brand and model ride over from the wig. A cancelled dialog
    calls nothing, so there is never an orphan to clean up.

    Source is EITHER a closet ``filename`` or a library ``codebook_id``
    (v0.8.1 library rows): the codebook path renders a transient wig
    through the snapshot primitive and adopts it identically, writing
    nothing to the closet.

    Matrix wigs (hair-wig/2, Cold Cuts) adopt as AC devices only: the
    matrix writes to its own ``hair/matrices/`` file keyed by the new
    device id, ``climate_matrix`` flags the device, and the flat
    signals (the depth-0 extras) still copy as ordinary commands with
    auto-map running over THEM only -- the cells are the climate
    entity's, not the command list's.
    """
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

    filename = msg.get("filename")
    codebook_id = msg.get("codebook_id")
    if filename is None and codebook_id is None:
        connection.send_error(
            msg["id"], "invalid_format",
            "Provide filename or codebook_id",
        )
        return

    if filename is not None:
        from .wig_store import load_wig

        wig = await hass.async_add_executor_job(
            load_wig, hass.config.config_dir, filename
        )
    else:
        from .code_library import build_wig_from_codebook

        wig = await hass.async_add_executor_job(
            build_wig_from_codebook, codebook_id
        )
    if wig is None:
        connection.send_error(msg["id"], "not_found", "Wig not found")
        return

    matrix = wig.climate
    if matrix is not None and device_type != DeviceType.AC:
        # The matrix IS a thermostat lattice; adopting it as anything
        # else would strand the cells (only the climate entity reads
        # them). The frontend seeds "ac" from kind, so this only fires
        # on a stale or hand-rolled caller.
        connection.send_error(
            msg["id"], "invalid_format",
            "matrix wigs adopt as AC devices",
        )
        return

    from .wig_comb import suspect_findings
    from .wig_identity import wig_signal_identities

    identities = await hass.async_add_executor_job(
        wig_signal_identities, wig
    )

    # What the comb doubted rides onto the device (v0.9.5). Read from
    # the stored receipt, so adopting never re-combs; a wig nobody has
    # combed simply carries no doubts. Matrix wigs bring their depth-0
    # extras through the same loop, which is how suspect extras end up
    # visible in the commands area rather than lost behind the lattice.
    findings = suspect_findings(wig)
    suspects = set(findings)

    # A closet wig written before v0.9.5 has no identity yet. Backfill
    # it in the file, not just in memory, so the device and the wig
    # agree from here on. Codebook adopts render a transient wig that
    # was never in the closet, so there is nothing to backfill and
    # nothing to inherit.
    adopted_wig_id: str | None = None
    if filename:
        from .wig_store import backfill_wig_id

        adopted_wig_id = await hass.async_add_executor_job(
            backfill_wig_id, hass.config.config_dir, filename
        )

    device = IRDevice(
        name=msg["name"],
        device_type=device_type,
        manufacturer=wig.brand,
        model=wig.model,
        emitter_entity_ids=list(msg["emitter_entity_ids"]),
        climate_matrix=matrix is not None,
        # WHERE IT CAME FROM (v0.9.5). Adopting a closet wig records
        # that wig's identity, and the PRESENCE of it is what later
        # makes SAVE TO CLOSET offer "update <wig>" instead of minting
        # a second copy of something the closet already has.
        #
        # Only the FILE path carries one. A codebook adopt renders a
        # transient wig that was never in the closet and has no
        # identity to inherit, so it stays None and saves as a new wig,
        # which is the truth about it.
        source_wig_id=adopted_wig_id,
    )
    if matrix is not None:
        # The matrix file lands BEFORE the device exists (Cold Cuts):
        # async_create_device spins up the climate entity, whose
        # added-to-hass hook loads the matrix -- writing after would
        # race it. A write failure refuses the whole adopt, so a
        # cancelled or failed dialog still never leaves an orphan.
        # Cell seeding therefore happens HERE, before the write: the
        # cells never reach the signal loop below, and raising them
        # after the device exists would race the same hook.
        from .matrix_store import write_matrix

        try:
            await hass.async_add_executor_job(
                write_matrix, hass.config.config_dir, device.id, matrix
            )
        except OSError as err:
            connection.send_error(
                msg["id"], "write_failed",
                f"Could not write the matrix file: {err}",
            )
            return
    await manager.async_create_device(device)

    copied = 0
    skipped = 0
    for i, (sig, ident) in enumerate(
        zip(wig.signals, identities, strict=True), start=1
    ):
        if ident is None:
            skipped += 1
            continue
        command = _command_from_wig_signal(sig, ident, suspects, findings, i)
        device.add_command(command)
        manager._auto_map_command(device, command)
        copied += 1

    # THE PORTHOLE ROWS (v0.9.5). A flagged lattice cell gets a
    # coordinate-named command row so the full command toolset reaches
    # it: TEST sends it, edit rewrites it, delete removes it. ONLY
    # flagged cells -- the healthy thousands stay in the lattice where
    # they belong, and a commands area listing them all would be
    # useless. Without this the release would regress v0.9.1, whose
    # fitting dialog could replace a defective cell.
    cell_rows = 0
    if matrix is not None:
        cell_rows = _mint_cell_rows(device, matrix, findings)

    await manager.async_update_device(device)
    result = await _device_full(hass, device)
    result["copied"] = copied
    result["skipped"] = skipped
    result["cell_rows"] = cell_rows
    result["matrix_cells"] = len(matrix.cells) if matrix is not None else 0
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/make-device",
    vol.Required("remote_id"): str,
    vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)),
    vol.Required("device_type"): str,
    vol.Required("emitter_entity_ids"): [str],
})
@websocket_api.async_response
async def ws_trigger_remote_make_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """"Make a Device" mirror-door mint (signpost 3, Track 3.5, owner-
    directed 2026-08-15): create a HAIR device straight from a live
    Remote's own triggers -- ws_wig_make_device's twin, sourced from a
    named Remote instead of a closet wig, and the reverse direction of
    ws_device_make_remote above.

    Mirrors ws_wig_make_device's own create-empty-then-fill shape
    (async_create_device on an empty device, then add_command +
    _auto_map_command per row, then one async_update_device) rather
    than building the command list up front, so this stays a drop-in
    sibling of that established loop.

    A Remote's triggers never store raw_timings -- IRTrigger only ever
    needed enough identity to MATCH an incoming signal, not enough to
    TRANSMIT one. Rebuilding it from the trigger's Pronto ``code`` via
    ``ProntoCommand(code).get_raw_timings()`` is the exact backfill
    DeviceManager.async_update_command already runs on a manual Pronto
    edit; wrapped the same way, a bad or absent code yields a command
    with no raw_timings rather than refusing the whole mint (that
    command just will not TX until a later edit fixes it, same
    tolerance the Pronto-edit path itself has for a bad code).

    A Remote's TRIGGERS are always flat, so the loop below never mints
    a cell row. The Remote itself may still carry a lattice, though
    (signpost 4, Track M): when it does, the matrix file is byte-copied
    under the new device's id BEFORE the device exists -- the climate
    entity's added-to-hass hook loads it, so writing afterwards would
    race it, the same ordering ws_wig_make_device keeps -- the device
    is flagged ``climate_matrix``, and its type is FORCED to AC
    regardless of what the caller asked for. Forcing rather than
    refusing (ws_wig_make_device's answer to the same situation) is
    deliberate on this door: the closet dialog seeds its type from the
    wig's kind and can only send a wrong one when hand-rolled, while
    this door's dialog offers the user a free choice and would
    otherwise dead-end a mint they legitimately asked for. The result
    carries ``forced_ac`` so the caller can say what happened. A failed
    copy leaves the device flat and says so in ``matrix_copied``,
    rather than minting a climate entity with no lattice to send.

    Origin recorded "remote", source recorded as the remote's id
    (IRDevice.source_remote_id) -- the Track 3.5 pin prompt's trivial
    "content match", mirroring the other direction above.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    manager: DeviceManager = data["device_manager"]

    try:
        device_type = DeviceType(msg["device_type"])
    except ValueError:
        connection.send_error(msg["id"], "invalid_format", "Unknown device_type")
        return

    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Remote not found")
        return

    matrix_copied = False
    forced_ac = False
    if remote.climate_matrix:
        forced_ac = device_type != DeviceType.AC
        device_type = DeviceType.AC

    device = IRDevice(
        name=msg["name"],
        device_type=device_type,
        emitter_entity_ids=list(msg["emitter_entity_ids"]),
        origin="remote",
        source_remote_id=remote.id,
    )
    if remote.climate_matrix:
        from .matrix_store import copy_matrix

        matrix_copied = await hass.async_add_executor_job(
            copy_matrix, hass.config.config_dir, remote.id, device.id
        )
        if matrix_copied:
            device.climate_matrix = True
        else:
            # Nothing to send from: an AC device with no lattice would
            # spin up a climate entity that refuses every command with
            # no visible reason. Stay flat and report it.
            forced_ac = False
            device.device_type = DeviceType(msg["device_type"])
    await manager.async_create_device(device)

    from .identity import file_sourced_trigger
    from .ir_command import ProntoCommand
    from .models import IRCommand

    copied = 0
    triggers = store.get_triggers_for_remote(remote.id)
    for i, trig in enumerate(triggers, start=1):
        raw_timings = None
        if trig.code:
            try:
                raw_timings = ProntoCommand(trig.code).get_raw_timings()
            except Exception:  # bad code: command just will not TX yet
                raw_timings = None
        command = IRCommand(
            name=trig.name.strip() or f"Trigger {i}",
            protocol=trig.protocol,
            code=trig.code,
            raw_timings=raw_timings,
            byte_hash=trig.byte_hash,
            decoded_fingerprint=trig.decoded_fingerprint,
            # The trigger's provenance carries over with its bytes: a
            # Remote minted from a wig gives a device whose commands
            # came from that file (2026-08-18).
            source=(
                CommandSource.IMPORTED
                if file_sourced_trigger(trig, store)
                else CommandSource.CAPTURED
            ),
        )
        device.add_command(command)
        manager._auto_map_command(device, command)
        copied += 1

    await manager.async_update_device(device)
    result = await _device_full(hass, device)
    result["copied"] = copied
    result["matrix_copied"] = matrix_copied
    result["forced_ac"] = forced_ac
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/make-remote",
    vol.Exclusive("filename", "wig_source"): vol.All(
        str, vol.Length(max=300)
    ),
    vol.Exclusive("codebook_id", "wig_source"): vol.All(
        str, vol.Length(max=300)
    ),
    vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)),
    vol.Optional("receiver_scope"): [str],
})
@websocket_api.async_response
async def ws_wig_make_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """USE as a Remote: create a named Remote straight from a closet
    wig (signpost 3, Track 2 item 2 -- the Closet door of "three
    doors, one machinery").

    Mirrors ws_wig_make_device's source resolution (EITHER a closet
    ``filename`` or a library ``codebook_id``) and identity resolution
    exactly, but mints IRTrigger rows instead of IRCommand rows and
    skips everything device-only: no emitter picker, no
    climate_matrix flag, no porthole/cell_rows minting. THE MATRIX
    RULE (trigger-remotes-release-a.md): a matrix wig's lattice cells
    live in ``wig.climate.cells``, never in ``wig.signals`` -- the same
    flat-signal loop ws_wig_make_device already runs for a matrix wig's
    depth-0 extras is naturally matrix-rule-compliant here too, with no
    separate guard needed, and no AC-device-type restriction applies
    since a Remote has no device type at all. Origin recorded "closet".

    THE LATTICE NOW RIDES ALONG (signpost 4, Track M). The matrix rule
    is unchanged -- no trigger is minted per cell, the depth-0 extras
    are still the only rows -- but the lattice itself is COPIED to
    ``hair/matrices/<remote_id>.matrix.json`` so the remote can HEAR
    its own states. Written BEFORE the remote exists, and a write
    failure refuses the whole mint: the device door's argument (never
    leave something claiming a matrix it does not have) holds here even
    though no entity races the file, because the remote's card, its
    listener and its LAST HEARD row all read the flag.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]

    name = msg["name"].strip()
    if not name:
        connection.send_error(msg["id"], "invalid_format", "Name is required")
        return

    filename = msg.get("filename")
    codebook_id = msg.get("codebook_id")
    if filename is None and codebook_id is None:
        connection.send_error(
            msg["id"], "invalid_format",
            "Provide filename or codebook_id",
        )
        return

    if filename is not None:
        from .wig_store import load_wig

        wig = await hass.async_add_executor_job(
            load_wig, hass.config.config_dir, filename
        )
    else:
        from .code_library import build_wig_from_codebook

        wig = await hass.async_add_executor_job(
            build_wig_from_codebook, codebook_id
        )
    if wig is None:
        connection.send_error(msg["id"], "not_found", "Wig not found")
        return

    from .wig_identity import wig_signal_identities

    identities = await hass.async_add_executor_job(
        wig_signal_identities, wig
    )

    # WHERE IT CAME FROM (signpost 3, Track 2 item 4), the remote-side
    # twin of ws_wig_make_device's adopted_wig_id: only the FILE path
    # carries a pointer for the combined linked-count dot to read back
    # (_wig_linked_remotes). A codebook make renders a transient wig
    # that was never in the closet, so it stays None, same as the
    # device side.
    source_wig_id: str | None = None
    if filename:
        from .wig_store import backfill_wig_id

        source_wig_id = await hass.async_add_executor_job(
            backfill_wig_id, hass.config.config_dir, filename
        )

    matrix = wig.climate
    remote = TriggerRemote(
        name=name,
        receiver_scope=list(msg.get("receiver_scope") or []),
        origin="closet",
        source_wig_id=source_wig_id,
        climate_matrix=matrix is not None,
    )
    if matrix is not None:
        from .matrix_store import write_matrix

        try:
            await hass.async_add_executor_job(
                write_matrix, hass.config.config_dir, remote.id, matrix
            )
        except OSError as err:
            connection.send_error(
                msg["id"], "write_failed",
                f"Could not write the matrix file: {err}",
            )
            return
        _invalidate_remote_matrix(data, remote.id)
        _warm_remote_matrix(data, remote.id)
    store.add_trigger_remote(remote)

    triggers: list[IRTrigger] = []
    for i, (sig, ident) in enumerate(
        zip(wig.signals, identities, strict=True), start=1
    ):
        if ident is None:
            continue
        trig_name = sig.alias.strip() or f"Signal {i}"
        trigger = IRTrigger(
            name=trig_name,
            signal_fingerprint=ident.fingerprint,
            protocol="PRONTO",
            code=ident.pronto,
            byte_hash=ident.byte_hash,
            decoded_fingerprint=ident.decoded_fingerprint,
            trigger_remote_id=remote.id,
            origin="closet",
        )
        store.add_trigger(trigger)
        triggers.append(trigger)

    await store.async_save()

    ha_device_id = _register_trigger_remote_ha_device(
        hass, data["config_entry"].entry_id, remote
    )

    from .event import sync_trigger_entities

    entry_id = data["config_entry"].entry_id
    for trig in triggers:
        sync_trigger_entities(hass, entry_id, trigger=trig)

    result = {
        **remote.to_dict(),
        "ha_device_id": ha_device_id,
        "trigger_count": len(triggers),
        "matrix_cells": len(matrix.cells) if matrix is not None else 0,
    }
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/make-remote",
    vol.Required("device_id"): str,
    vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)),
    vol.Optional("receiver_scope"): [str],
})
@websocket_api.async_response
async def ws_device_make_remote(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """"Make a Remote" mirror-door mint (signpost 3, Track 3.5, owner-
    directed 2026-08-15): create a named Remote straight from a live
    Device's own commands -- ws_wig_make_remote's twin, sourced from a
    device instead of a closet wig.

    Mints one IRTrigger per eligible command, reading identity straight
    off the already-live IRCommand (protocol/code/byte_hash/
    decoded_fingerprint are same-named on both dataclasses, near-direct
    copy) rather than through wig_identity's decode-a-signal detour --
    the device's commands already carry that identity from whatever
    door created them. Only signal_fingerprint needs deriving, via
    EventParser.signal_fingerprint, the same helper
    DeviceManager.async_update_command's own Pronto-edit path uses to
    recompute it.

    THE MATRIX RULE (trigger-remotes-release-a.md): any command with
    matrix_cell set is a porthole view into a lattice cell (v0.9.5,
    ``_mint_cell_rows``), not a real discrete press, and is skipped --
    the same discrete-press subset the device picker already applies
    elsewhere in HAIR. A matrix device may legitimately mint zero
    triggers this way (a climate card with no assigned buttons); that
    is not an error, it just yields an unusually thin Remote, same as
    a matrix wig with no depth-0 extras on the wig-sourced door.

    THE LATTICE COMES WITH IT (signpost 4, Track M). A matrix device's
    matrix file is byte-copied under the new remote's id, so the
    remote hears exactly what the device sends. Unlike the closet
    door, a failed copy does NOT refuse the mint: the triggers above
    are the user's actual ask and a device with an unreadable matrix
    file is already broken on its own page. The flag stays false and
    the result says ``matrix_copied: false`` so the caller can tell
    the user the lattice did not come across.

    Origin recorded "device", source recorded as the device's id
    (TriggerRemote.source_device_id) -- the Track 3.5 pin prompt's
    trivial "content match".
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    manager: DeviceManager = data["device_manager"]

    name = msg["name"].strip()
    if not name:
        connection.send_error(msg["id"], "invalid_format", "Name is required")
        return

    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    from .identity import canonical_fingerprint

    remote = TriggerRemote(
        name=name,
        receiver_scope=list(msg.get("receiver_scope") or []),
        origin="device",
        source_device_id=device.id,
    )
    matrix_copied = False
    if device.climate_matrix:
        from .matrix_store import copy_matrix

        matrix_copied = await hass.async_add_executor_job(
            copy_matrix, hass.config.config_dir, device.id, remote.id
        )
        remote.climate_matrix = matrix_copied
        if matrix_copied:
            _invalidate_remote_matrix(data, remote.id)
            _warm_remote_matrix(data, remote.id)
    store.add_trigger_remote(remote)

    triggers: list[IRTrigger] = []
    for i, command in enumerate(device.commands, start=1):
        if command.matrix_cell is not None:
            continue
        trig_name = command.name.strip() or f"Command {i}"
        trigger = IRTrigger(
            name=trig_name,
            # Canonical (wire) identity, so the minted trigger matches
            # the real handset press (identity.py's canonical-form
            # block); the command's own code text is untouched.
            signal_fingerprint=canonical_fingerprint(
                command.protocol, command.code, command.raw_timings
            ),
            protocol=command.protocol,
            code=command.code,
            byte_hash=command.byte_hash,
            decoded_fingerprint=command.decoded_fingerprint,
            source_device_id=device.id,
            source_command_id=command.id,
            trigger_remote_id=remote.id,
            origin="device",
        )
        store.add_trigger(trigger)
        triggers.append(trigger)

    await store.async_save()

    ha_device_id = _register_trigger_remote_ha_device(
        hass, data["config_entry"].entry_id, remote
    )

    from .event import sync_trigger_entities

    entry_id = data["config_entry"].entry_id
    for trig in triggers:
        sync_trigger_entities(hass, entry_id, trigger=trig)

    result = {
        **remote.to_dict(),
        "ha_device_id": ha_device_id,
        "trigger_count": len(triggers),
        "matrix_copied": matrix_copied,
    }
    connection.send_result(msg["id"], result)


def _cell_row_name(cell: Any, others: list[Any]) -> str:
    """A flagged cell's row name: "Cool 24", coordinates only as needed.

    Mode and temperature read as a state a person can set on their
    remote, which is the whole point -- the row's name IS the
    set-your-remote-to-this instruction. Fan and swing join only when
    two flagged cells would otherwise wear the same name, because a
    lattice usually carries several fan speeds per temperature and two
    identical rows help nobody.
    """
    base = [cell.mode.capitalize() if cell.mode else "Cell"]
    if cell.temp is not None:
        base.append(_temp_label(cell.temp))
    short = " ".join(base)
    clashes = [
        c for c in others
        if c is not cell
        and c.mode == cell.mode
        and (c.temp is None) == (cell.temp is None)
        and (c.temp is None or abs(float(c.temp) - float(cell.temp)) < 1e-6)
    ]
    if not clashes:
        return short
    extra = [v for v in (cell.fan, cell.swing) if v]
    return " ".join([*base, *extra]) if extra else short


def _temp_label(temp: float) -> str:
    return str(int(temp)) if float(temp).is_integer() else str(temp)


def _mint_cell_rows(
    device: IRDevice, matrix: Any, findings: dict[str, str]
) -> int:
    """Give every comb-flagged cell a command row. Returns how many.

    Keyed off the same suspect set the flat rows use, matched to cells
    by ``cell_key`` -- the comb records cell findings under exactly that
    key, so no second vocabulary is invented here.
    """
    if not findings:
        return 0
    from .models import CommandCategory, CommandSource, IRCommand
    from .wig_format import cell_key

    flagged = [c for c in matrix.cells if cell_key(c) in findings]
    minted = 0
    for cell in flagged:
        command = IRCommand(
            name=_cell_row_name(cell, flagged),
            category=CommandCategory.CUSTOM,
            source=CommandSource.MATRIX,
            protocol="PRONTO",
            code=cell.pronto,
            send_count=max(1, cell.send_count or 1),
            # Cells carry no dittos (plan 5.5), and an inherited catalog
            # default would invent one.
            repeat_count=0,
            matrix_cell={
                "mode": cell.mode, "fan": cell.fan,
                "swing": cell.swing, "temp": cell.temp,
            },
            comb_suspect=True,
            comb_finding=findings.get(cell_key(cell)),
        )
        # Deliberately NOT auto-mapped: these are repair portholes, not
        # buttons the entity should start offering as features.
        device.add_command(command)
        minted += 1
    return minted



@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/signals",
    vol.Exclusive("filename", "wig_source"): vol.All(
        str, vol.Length(max=300)
    ),
    vol.Exclusive("codebook_id", "wig_source"): vol.All(
        str, vol.Length(max=300)
    ),
})
@websocket_api.async_response
async def ws_wig_signals(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add Popups signpost 2, Track 3: a wig's discrete signals with
    identity already derived, for the Add Trigger Remote dialog's
    Closet tab to seed one hair/trigger/create call per signal.

    Deliberately read-only and narrow -- it does not create anything,
    it just hands back what ws_wig_make_device already computes for
    itself when adopting a wig as a device: each signal's fingerprint,
    byte_hash, and decoded_fingerprint, via the exact same
    wig_signal_identity() helper. Matrix cells are never included --
    ``wig.signals`` is the flat/depth-0 list already, the matrix lives
    in its own structure (see ws_wig_make_device's docstring) -- so a
    pure-matrix wig legitimately returns an empty list, not an error.

    Same source resolution as ws_wig_make_device: EITHER a closet
    ``filename`` or a library ``codebook_id`` (the codebook path
    renders a transient wig, nothing written to the closet). A signal
    whose Pronto fails to validate is skipped, same as
    wig_signal_identities() does for its other caller.
    """
    filename = msg.get("filename")
    codebook_id = msg.get("codebook_id")
    if filename is None and codebook_id is None:
        connection.send_error(
            msg["id"], "invalid_format",
            "Provide filename or codebook_id",
        )
        return

    if filename is not None:
        from .wig_store import load_wig

        wig = await hass.async_add_executor_job(
            load_wig, hass.config.config_dir, filename
        )
    else:
        from .code_library import build_wig_from_codebook

        wig = await hass.async_add_executor_job(
            build_wig_from_codebook, codebook_id
        )
    if wig is None:
        connection.send_error(msg["id"], "not_found", "Wig not found")
        return

    from .wig_identity import wig_signal_identities

    identities = await hass.async_add_executor_job(
        wig_signal_identities, wig
    )

    signals = []
    for index, (sig, identity) in enumerate(
        zip(wig.signals, identities, strict=True)
    ):
        if identity is None:
            continue
        signals.append({
            "name": sig.alias.strip() or f"Signal {index}",
            "signal_fingerprint": identity.fingerprint,
            "code": identity.pronto,
            "byte_hash": identity.byte_hash,
            "decoded_fingerprint": identity.decoded_fingerprint,
        })

    connection.send_result(msg["id"], {"signals": signals})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/snapshot",
    vol.Required("codebook_id"): vol.All(str, vol.Length(max=300)),
})
@websocket_api.async_response
async def ws_wig_snapshot(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Snapshot a library codebook into the closet (v0.8.1).

    The FIT road for library rows: fittings live in wig files, so
    fitting a codebook first materializes it as a wig. Dedup is by
    signals content hash -- fitting the same codebook twice (or after
    a manual Download-and-upload) lands in the ONE existing file
    instead of minting a twin, which is what keeps every fitting of a
    given render accumulating in the same ledger.
    """

    def _snapshot() -> dict[str, Any] | None:
        from .code_library import build_wig_from_codebook
        from .wig_format import serialize_wig, wig_content_hash
        from .wig_store import scan_wigs, write_wig_text

        wig = build_wig_from_codebook(msg["codebook_id"])
        if wig is None:
            return None
        # wig_content_hash on the scan side too (2026-07-28): the closet
        # scan includes matrix wigs, and hashing their near-empty flat
        # signal lists is the same collision class the upload dedup hit.
        # Codebook wigs carry no climate block, so the incoming side is
        # byte-identical to the old signals hash.
        content = wig_content_hash(wig)
        for loaded in scan_wigs(hass.config.config_dir).wigs:
            if wig_content_hash(loaded.wig) == content:
                return {
                    "filename": loaded.path.name,
                    "name": loaded.wig.name,
                    "existed": True,
                }
        filename = write_wig_text(
            hass.config.config_dir, serialize_wig(wig), wig.name
        )
        if filename is None:
            return None
        return {"filename": filename, "name": wig.name, "existed": False}

    result = await hass.async_add_executor_job(_snapshot)
    if result is None:
        connection.send_error(msg["id"], "not_found", "Codebook not found")
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/wigs/render",
    vol.Required("codebook_id"): vol.All(str, vol.Length(max=300)),
})
@websocket_api.async_response
async def ws_wig_render(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Render a library codebook as downloadable wig text (v0.8.1).

    The Download road for library rows: same snapshot primitive, but
    nothing touches the closet -- the text goes straight out as a file.
    The suggested filename slugifies the wig name with no collision
    dodging (it is a browser download, not a closet write).
    """

    def _render() -> dict[str, Any] | None:
        from .code_library import build_wig_from_codebook
        from .wig_format import serialize_wig, wig_filename

        wig = build_wig_from_codebook(msg["codebook_id"])
        if wig is None:
            return None
        return {
            "text": serialize_wig(wig),
            "name": wig.name,
            "filename": wig_filename(wig.name),
        }

    result = await hass.async_add_executor_job(_render)
    if result is None:
        connection.send_error(msg["id"], "not_found", "Codebook not found")
        return
    connection.send_result(msg["id"], result)


# --- Matrix device detail (Cold Cuts second half, 2026-07-29) ---
#
# The device page's cell browser rides three commands: matrix-cells
# lists the lattice without a byte of Pronto, matrix-send fires one
# exact cell (or a power code), and matrix-command saves one exact cell
# as a stored command. All three resolve EXACTLY -- the frontend sends
# coordinates read off matrix-cells, so snapping here would only paper
# over a stale client. The entity's resolve_cell keeps its snapping;
# these are different callers with different contracts.


async def _matrix_for_request(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> tuple[Any, Any, Any] | None:
    """Shared entry: (data, device, matrix), or None after send_error."""
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return None
    manager: DeviceManager = data["device_manager"]
    device = manager.get_device(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return None
    matrix = None
    if device.climate_matrix:
        matrix = await manager.async_get_matrix(device.id)
    if matrix is None:
        # Covers both a non-matrix device and an unreadable matrix
        # file; matrix_store already logged the reason for the latter.
        connection.send_error(
            msg["id"], "not_found", "Device has no readable climate matrix"
        )
        return None
    return data, device, matrix


def _matrix_cells_payload(matrix: Any) -> dict[str, Any]:
    """The cell-browser payload for one lattice, device or remote.

    One body, two endpoints (signpost 4, Track M): the remote's card is
    the device card in hear mode and must read byte-identical bytes, so
    the shape lives here rather than being copied into a sibling
    handler that would drift by the second change.
    """
    from .wig_climate import matrix_summary

    summary = matrix_summary(matrix)
    cells: list[dict[str, Any]] = []
    for c in matrix.cells:
        cell: dict[str, Any] = {"m": c.mode}
        if c.fan is not None:
            cell["f"] = c.fan
        if c.swing is not None:
            cell["s"] = c.swing
        if c.temp is not None:
            cell["t"] = c.temp
        cells.append(cell)
    return {
        # Native bounds plus the native unit (unit ruling 2026-07-29):
        # the frontend converts for display per render and computes
        # absent tiles from these native numbers, never the converse.
        "min_temp": matrix.min_temp,
        "max_temp": matrix.max_temp,
        "precision": matrix.precision,
        "unit": matrix.unit,
        "modes": summary["modes"],
        "fan_modes": summary["fan_modes"],
        "swing_modes": summary["swing_modes"],
        "has_on": matrix.on is not None,
        "cells": cells,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/devices/matrix-cells",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_device_matrix_cells(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """The cell browser payload: the whole lattice WITHOUT prontos.

    The census worst case is 2,689 cells, so cells carry single-letter
    keys and OMIT dimensions the cell does not have -- three spelled
    nulls per cell would cost tens of kilobytes for pure padding. The
    vocabulary lists follow the matrix_summary ordering rule (declared
    order first, observed strays after, never-observed dropped). The
    frontend round-trips these coordinates verbatim into matrix-send
    and matrix-command.
    """
    resolved = await _matrix_for_request(hass, connection, msg)
    if resolved is None:
        return
    _data, _device, matrix = resolved
    connection.send_result(msg["id"], _matrix_cells_payload(matrix))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/matrix-cells",
    vol.Required("remote_id"): str,
})
@websocket_api.async_response
async def ws_trigger_remote_matrix_cells(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """The same cell browser, for a Remote's heard-side lattice.

    Identical bytes to the device endpoint above (shared body), because
    the remote's card is the device's card in hear mode. No send
    sibling and no command sibling: nothing transmits from a Remote.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Remote not found")
        return
    matrix = await _remote_matrix(hass, data, remote)
    if matrix is None:
        # Covers both a flat remote and an unreadable matrix file;
        # matrix_store already logged the reason for the latter.
        connection.send_error(
            msg["id"], "not_found", "Remote has no readable climate matrix"
        )
        return
    connection.send_result(msg["id"], _matrix_cells_payload(matrix))


class _MatrixPickError(Exception):
    """One lattice coordinate set that did not resolve.

    Carries the websocket error code alongside the message so a caller
    can hand both straight to ``send_error`` without re-deciding which
    failure it was.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _matrix_pick(
    hass: HomeAssistant, matrix: Any, msg: dict[str, Any]
) -> tuple[str, str, int, dict[str, Any]]:
    """Resolve coordinates to ``(name, Pronto, send count, state)``.

    ``state`` (0.10.1 item 7) is the coordinates themselves, handed back
    rather than thrown away: a STATE row minted here has to remember
    which state it transmits, and the display name it also returns is
    grammar, not data -- it converts units live and freezes at mint
    time, so it can never be parsed back into coordinates later.

    ``power`` and ``mode`` are EXCLUSIVE here, unlike matrix-send where
    power deliberately wins over stale cell coordinates: the callers
    below are minting something that gets kept (a stored command, a
    trigger), so an ambiguous request is a client bug worth reporting
    rather than papering over.

    The name is built at call time in the install's unit (unit ruling
    2026-07-29). What each caller then does with it differs -- a stored
    command freezes it, a trigger's name is the user's to edit in the
    dialog -- but the string they start from is the same one the card's
    Set-state line previewed.
    """
    from .wig_climate import (
        cell_display_name,
        exact_cell,
        state_display_name,
        unit_letter,
    )

    power = msg.get("power")
    mode = msg.get("mode")
    if power is not None and mode is not None:
        raise _MatrixPickError("invalid_format", "Provide power or mode")
    if power is not None:
        pronto = matrix.off if power == "off" else matrix.on
        if pronto is None:
            raise _MatrixPickError("not_found", "This matrix has no on code")
        return state_display_name(power), pronto, 1, {"power": power}
    if mode is None:
        raise _MatrixPickError("invalid_format", "Provide power or mode")
    cell = exact_cell(
        matrix, mode, msg.get("fan"), msg.get("swing"), msg.get("temp"),
    )
    if cell is None:
        raise _MatrixPickError("not_found", "No cell at those coordinates")
    name = cell_display_name(
        cell,
        unit=matrix.unit,
        display_unit=unit_letter(hass.config.units.temperature_unit),
        precision=matrix.precision,
    )
    return name, cell.pronto, cell.send_count, {
        "mode": cell.mode, "fan": cell.fan,
        "swing": cell.swing, "temp": cell.temp,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/trigger-remote/matrix-cell",
    vol.Required("remote_id"): str,
    vol.Optional("mode"): str,
    vol.Optional("fan"): vol.Any(str, None),
    vol.Optional("swing"): vol.Any(str, None),
    vol.Optional("temp"): vol.Any(int, float, None),
    vol.Optional("power"): vol.Any("on", "off"),
})
@websocket_api.async_response
async def ws_trigger_remote_matrix_cell(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """ONE cell, with the bytes the cell browser deliberately omits.

    matrix-cells ships the whole lattice without a byte of Pronto, and
    that no-bytes contract is the point: the census worst case is 2,689
    cells and the browser needs coordinates, not codes. But the three
    doors that mint a trigger off the lattice -- the LAST HEARD row,
    the action bar on a heard cell, the action bar on a never-heard one
    -- each need exactly one cell's code and identity to pre-fill the
    dialog with. So they ask for the one, by the coordinates they
    already hold.

    Identity is derived here rather than shipped from the file because
    a wig carries raw Pronto and no decoded fields, and because a
    trigger minted off a cell must match the same frame heard off the
    air. ``wig_signal_identity`` is the same derivation the matrix
    listener's own cell index uses, so the trigger created through this
    door and the state that fires it agree by construction.

    Read-only: nothing is stored and nothing transmits. The remote is a
    listener.
    """
    data = _get_first_entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_configured", "HAIR not configured")
        return
    store = data["store"]
    remote = store.get_trigger_remote(msg["remote_id"])
    if remote is None:
        connection.send_error(msg["id"], "not_found", "Remote not found")
        return
    matrix = await _remote_matrix(hass, data, remote)
    if matrix is None:
        connection.send_error(
            msg["id"], "not_found", "Remote has no readable climate matrix"
        )
        return
    try:
        name, pronto, _send_count, _state = _matrix_pick(hass, matrix, msg)
    except _MatrixPickError as err:
        connection.send_error(msg["id"], err.code, err.message)
        return

    from .wig_identity import wig_signal_identity

    ident = await hass.async_add_executor_job(wig_signal_identity, pronto)
    if ident is None:
        # Possible only for a hand-edited matrix file whose code no
        # longer validates; refuse honestly rather than hand the dialog
        # a code it cannot mint a matching trigger from.
        connection.send_error(
            msg["id"], "invalid_format", "The code does not validate"
        )
        return
    connection.send_result(msg["id"], {
        # The file text, which is what a trigger stores as its code --
        # the canonical form is an identity detail, not a payload one.
        "pronto": ident.pronto,
        "name": name,
        "identity": {
            "signal_fingerprint": ident.fingerprint,
            "byte_hash": ident.byte_hash,
            "decoded_fingerprint": ident.decoded_fingerprint,
            # For the dialog's protocol line. Null for every AC lattice
            # frame in the corpus so far, which is why the LAST HEARD
            # row draws no protocol chip yet.
            "decoded_protocol": ident.decoded_protocol,
        },
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/devices/matrix-send",
    vol.Required("device_id"): str,
    vol.Optional("mode"): str,
    vol.Optional("fan"): vol.Any(str, None),
    vol.Optional("swing"): vol.Any(str, None),
    vol.Optional("temp"): vol.Any(int, float, None),
    vol.Optional("power"): vol.Any("on", "off"),
})
@websocket_api.async_response
async def ws_device_matrix_send(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send one exact cell, or a power code, from the cell browser.

    ``power`` sends the matrix's off/on code and wins over any cell
    coordinates; otherwise the exact cell resolves or errors
    ``not_found`` (matrices are sparse -- an absent combination is
    file fact and the browser shows it as such). Sends ride
    ``async_send_matrix_cell`` under the display-grammar name, so the
    Mirror row reads exactly like the entity's own sends.
    """
    resolved = await _matrix_for_request(hass, connection, msg)
    if resolved is None:
        return
    data, _device, matrix = resolved
    from .wig_climate import (
        cell_display_name,
        exact_cell,
        state_display_name,
        unit_letter,
    )

    manager: DeviceManager = data["device_manager"]
    power = msg.get("power")
    if power is not None:
        pronto = matrix.off if power == "off" else matrix.on
        if pronto is None:
            connection.send_error(
                msg["id"], "not_found", "This matrix has no on code"
            )
            return
        name = state_display_name(power)
        send_count = 1
        cell_state: dict[str, Any] | None = None
    else:
        mode = msg.get("mode")
        if mode is None:
            connection.send_error(
                msg["id"], "invalid_format", "Provide power or mode"
            )
            return
        cell = exact_cell(
            matrix, mode, msg.get("fan"), msg.get("swing"), msg.get("temp")
        )
        if cell is None:
            connection.send_error(
                msg["id"], "not_found", "No cell at those coordinates"
            )
            return
        # The Mirror label converts to the install's unit LIVE (unit
        # ruling 2026-07-29): nothing persists here, so nothing
        # freezes -- switch the install's unit tomorrow and tomorrow's
        # sends read in tomorrow's unit.
        name = cell_display_name(
            cell,
            unit=matrix.unit,
            display_unit=unit_letter(hass.config.units.temperature_unit),
            precision=matrix.precision,
        )
        pronto = cell.pronto
        send_count = cell.send_count
        # The card follows this send (0.10.1 item 7): the coordinates
        # go with it structurally, since ``name`` above is display
        # grammar and converts units live.
        cell_state = {
            "mode": cell.mode, "fan": cell.fan,
            "swing": cell.swing, "temp": cell.temp,
        }
    # The echo hook behind the TEST button's SENT . HEARD reading
    # (Second Fitting v3 punch list item 14): a cell send rides the
    # exact same Mirror hook a stored command's TEST does via
    # _async_broadcast, so the same wait-and-report pattern
    # ws_send_command already uses applies here unchanged.
    import asyncio

    from .wig_fitting import FITTING_HEARD_WAIT_S

    heard_future: asyncio.Future[str | None] = (
        asyncio.get_running_loop().create_future()
    )
    try:
        await manager.async_send_matrix_cell(
            msg["device_id"], name, pronto, send_count,
            heard_future=heard_future,
            cell=cell_state,
            power=power,
        )
    except Exception as err:
        heard_future.cancel()
        _LOGGER.error("Matrix send failed: %s", err, exc_info=True)
        connection.send_error(msg["id"], "send_failed", str(err))
        return

    receiver: str | None = None
    try:
        receiver = await asyncio.wait_for(heard_future, FITTING_HEARD_WAIT_S)
        heard = True
    except (TimeoutError, asyncio.CancelledError):
        heard_future.cancel()
        heard = False
    connection.send_result(
        msg["id"], {"sent": name, "heard": heard, "receiver": receiver}
    )


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/devices/matrix-command",
    vol.Required("device_id"): str,
    vol.Optional("mode"): str,
    vol.Optional("fan"): vol.Any(str, None),
    vol.Optional("swing"): vol.Any(str, None),
    vol.Optional("temp"): vol.Any(int, float, None),
    vol.Optional("power"): vol.Any("on", "off"),
})
@websocket_api.async_response
async def ws_device_matrix_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Save one exact cell, or a power code, as a stored command
    (save-state-as-command).

    ``power`` promotes the matrix's off/on code the same way
    matrix-send's power path does -- it wins over any cell
    coordinates, and mode is required only when power is absent
    (matrix-power-row.md item 2). Either path becomes an IRCommand
    named by the display grammar, identity stamped fresh from its
    Pronto -- the same per-signal stamping ws_wig_make_device does, so
    a saved state matches its off-the-air twin everywhere identities
    are compared. The command's ``source`` is CommandSource.MATRIX,
    which is the whole origin mechanism: the frontend renders the
    STATE origin chip off ``command.source == "matrix"`` with no extra
    payload key. ``add_command`` replaces by name, so saving the same
    state twice refreshes the one command instead of stacking twins.
    No auto-map runs on either path: matrix-mode climate never reads
    command_mapping (see climate.py), and a display-grammar name
    matches no standard action anyway -- the stored "Power Off"
    command exists for dashboards, buttons, and automations, which is
    exactly what the LG R09AWN report (matrix-power-row.md) was
    missing.
    """
    resolved = await _matrix_for_request(hass, connection, msg)
    if resolved is None:
        return
    data, device, matrix = resolved
    from .models import CaptureResult
    from .wig_identity import wig_signal_identity

    # Mint-time naming (unit ruling 2026-07-29): the saved command's
    # name freezes in the install's unit as of NOW and never rewrites,
    # even if the install later changes units. The frontend's Set-state
    # line previews this exact string. The resolution itself is shared
    # with the remote side's matrix-cell door, which mints a trigger
    # off the same coordinates under the same power-or-mode rule.
    try:
        name, pronto, send_count, state = _matrix_pick(hass, matrix, msg)
    except _MatrixPickError as err:
        connection.send_error(msg["id"], err.code, err.message)
        return

    ident = await hass.async_add_executor_job(wig_signal_identity, pronto)
    if ident is None:
        # Possible only for a hand-edited matrix file whose cell (or
        # off/on code) no longer validates; refuse honestly rather
        # than store a command that cannot transmit.
        connection.send_error(
            msg["id"], "invalid_format", "The code does not validate"
        )
        return
    capture = CaptureResult(
        protocol="PRONTO",
        code=ident.pronto,
        raw_timings=list(ident.raw_timings),
        frequency=ident.frequency,
    )
    command = capture.to_command(name, CommandCategory.CUSTOM)
    command.source = CommandSource.MATRIX
    command.byte_hash = ident.byte_hash
    command.decoded_protocol = ident.decoded_protocol
    command.decoded_address = ident.decoded_address
    command.decoded_command = ident.decoded_command
    command.decoded_fingerprint = ident.decoded_fingerprint
    command.decoded_extras = (
        dict(ident.decoded_extras) if ident.decoded_extras else None
    )
    command.send_count = max(1, send_count or 1)
    # WHICH STATE THIS ROW IS (0.10.1 item 7). Stamped at mint from the
    # coordinates the pick already resolved, so sending the row later
    # moves the climate card exactly as the card's own SEND does -- and
    # so a preset, which IS a starred STATE row, moves the dial rather
    # than only the readout. NOT ``matrix_cell``: that field marks a
    # porthole, and deleting a porthole deletes the lattice cell.
    command.sent_state = dict(state)
    device.add_command(command)
    manager: DeviceManager = data["device_manager"]
    await manager.async_update_device(device)
    connection.send_result(msg["id"], await _device_full(hass, device))
