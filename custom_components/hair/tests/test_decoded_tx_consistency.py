"""Tests for the decoded-TX consistency pass.

Covers the three command-creation entry points that must carry the decoded
protocol identity through to the persisted ``IRCommand`` (and the catalog
Test path that must transmit the canonical decoded form):

- ``_apply_signal_provenance`` -- the single source of truth for the
  ``UnknownSignal -> IRCommand`` field copy.
- ``assign_signal`` / ``assign_to_new_device`` -- carry decoded_* live.
- ``test_signal`` -- prefer encode-from-decoded for Sniffer / Clipper /
  Plucker Test, falling back to raw replay.
- ``ws_save_captured_command`` -- decode at save (no source signal to copy).
- End-to-end: a freshly-assigned NEC command transmits canonical timings via
  ``device_manager.async_send_command`` without a reload.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import (
    CaptureResult,
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.signal_monitor import (
    SignalMonitor,
    _apply_signal_provenance,
)
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.storage import HAIRStore
from custom_components.hair.websocket_api import ws_save_captured_command

# A short, valid Pronto code used where only fingerprint / byte_hash matter.
_PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


# ---------------------------------------------------------------------------
# Helpers (self-contained; mirror the patterns in the sibling test modules)
# ---------------------------------------------------------------------------


def _make_signal_store(hass) -> SignalStore:
    store = SignalStore(hass)
    store._loaded = True
    return store


def _make_hair_store():
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    hair_store.match_command = MagicMock(return_value=None)
    return hair_store


def _make_connection():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.send_event = MagicMock()
    conn.subscriptions = {}
    return conn


def _wire_hass(hass, manager=None, orchestrator=None):
    entry_data = {
        "device_manager": manager or MagicMock(),
        "orchestrator": orchestrator or MagicMock(),
        "signal_monitor": MagicMock(),
    }
    hass.data[DOMAIN] = {"entry-1": entry_data}


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


def _make_device_manager(hass) -> DeviceManager:
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(hass)
        store._loaded = True
        factory = EntityFactory(hass)
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="ha-dev-1")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            return DeviceManager(hass, store, factory, "entry-1")


def _decoded_signal(**overrides) -> UnknownSignal:
    fields = {
        "id": "s1",
        "fingerprint": "s1",
        "protocol": "PRONTO",
        "code": _PRONTO,
        "frequency": 38000,
        "decoded_protocol": "NEC",
        "decoded_address": 0x1000,
        "decoded_command": 0x18,
        "decoded_fingerprint": "NEC:0x1000:0x18",
    }
    fields.update(overrides)
    return UnknownSignal(**fields)


# ---------------------------------------------------------------------------
# Edit 1 -- the provenance helper
# ---------------------------------------------------------------------------


def test_apply_signal_provenance_copies_all_fields():
    """The single copy site sets every field. This is the assertion the
    duplicated inline blocks used to dodge -- extend it when a field is added."""
    sig = _decoded_signal(
        byte_hash="bh", plucked_command_name="pwr_on", repeat_count=7
    )
    cmd = IRCommand(name="Power")

    _apply_signal_provenance(cmd, sig, send_count=3)

    assert cmd.byte_hash == "bh"
    assert cmd.decoded_protocol == "NEC"
    assert cmd.decoded_address == 0x1000
    assert cmd.decoded_command == 0x18
    assert cmd.decoded_fingerprint == "NEC:0x1000:0x18"
    assert cmd.send_count == 3
    assert cmd.repeat_count == 7
    assert cmd.plucked_command_name == "pwr_on"


# ---------------------------------------------------------------------------
# Edits 2 / 3 -- assign carries decoded_*
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_signal_carries_decoded_fields(fake_hass):
    store = _make_signal_store(fake_hass)
    hair_store = _make_hair_store()
    monitor = SignalMonitor(fake_hass, store, hair_store)

    store.add_device(
        UnknownDevice(id="ud1", fingerprint="d", signals=[_decoded_signal()])
    )
    hair_device = IRDevice(id="hd1", name="TV")
    hair_store.get_device.return_value = hair_device

    result = await monitor.assign_signal("ud1", "s1", "hd1", "Power", "custom")
    assert result["success"] is True

    cmd = hair_device.commands[0]
    assert cmd.decoded_protocol == "NEC"
    assert cmd.decoded_address == 0x1000
    assert cmd.decoded_command == 0x18
    assert cmd.decoded_fingerprint == "NEC:0x1000:0x18"
    assert cmd.tx_force_raw is False


@pytest.mark.asyncio
async def test_assign_signal_no_decoded_stays_none(fake_hass):
    """Regression guard for non-decoded signals (Sony, raw RC-5, etc.)."""
    store = _make_signal_store(fake_hass)
    hair_store = _make_hair_store()
    monitor = SignalMonitor(fake_hass, store, hair_store)

    sig = UnknownSignal(
        id="s1", fingerprint="s1", protocol="PRONTO", code=_PRONTO, frequency=38000,
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[sig]))
    hair_device = IRDevice(id="hd1", name="TV")
    hair_store.get_device.return_value = hair_device

    result = await monitor.assign_signal("ud1", "s1", "hd1", "Power", "custom")
    assert result["success"] is True

    cmd = hair_device.commands[0]
    assert cmd.decoded_protocol is None
    assert cmd.decoded_address is None
    assert cmd.decoded_command is None
    assert cmd.decoded_fingerprint is None


@pytest.mark.asyncio
async def test_assign_to_new_device_carries_decoded_fields(fake_hass):
    store = _make_signal_store(fake_hass)
    hair_store = _make_hair_store()
    monitor = SignalMonitor(fake_hass, store, hair_store)

    store.add_device(
        UnknownDevice(id="ud1", fingerprint="d", signals=[_decoded_signal()])
    )

    result = await monitor.assign_to_new_device(
        device_id="ud1",
        signal_id="s1",
        device_name="Living Room TV",
        device_type="media_player",
        emitter_entity_ids=["infrared.e"],
        command_name="Power",
        command_category="power",
    )
    assert result["success"] is True

    cmd = result["device"].commands[0]
    assert cmd.decoded_protocol == "NEC"
    assert cmd.decoded_address == 0x1000
    assert cmd.decoded_command == 0x18
    assert cmd.decoded_fingerprint == "NEC:0x1000:0x18"


# ---------------------------------------------------------------------------
# Edit 4 -- catalog-signal Test prefers encode-from-decoded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_catalog_test_uses_decoded_when_available(fake_hass):
    store = _make_signal_store(fake_hass)
    monitor = SignalMonitor(fake_hass, store, _make_hair_store())
    store.add_device(
        UnknownDevice(id="ud1", fingerprint="d", signals=[_decoded_signal()])
    )

    sentinel = object()
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch(
            "custom_components.hair.ir_command.build_decoded_command",
            return_value=sentinel,
        ) as bdc,
        patch("custom_components.hair.ir_command.build_command") as bc,
    ):
        result = await monitor.test_signal("s1", "infrared.e")

    assert result["success"] is True
    # test_signal now forwards the signal's repeat_count (default 1) to the
    # decoded build (v0.5.5 ditto-honoring Test path).
    bdc.assert_called_once_with("NEC", 0x1000, 0x18, repeat_count=1)
    bc.assert_not_called()
    ir_send.assert_awaited_once()
    assert ir_send.call_args[0][2] is sentinel


@pytest.mark.asyncio
async def test_catalog_test_falls_back_to_raw_when_no_decoded(fake_hass):
    store = _make_signal_store(fake_hass)
    monitor = SignalMonitor(fake_hass, store, _make_hair_store())
    sig = UnknownSignal(
        id="s1", fingerprint="s1", protocol="PRONTO", code=_PRONTO, frequency=38000,
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[sig]))

    sentinel = object()
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch("custom_components.hair.ir_command.build_decoded_command") as bdc,
        patch(
            "custom_components.hair.ir_command.build_command",
            return_value=sentinel,
        ) as bc,
    ):
        result = await monitor.test_signal("s1", "infrared.e")

    assert result["success"] is True
    bdc.assert_not_called()
    bc.assert_called_once()
    assert ir_send.call_args[0][2] is sentinel


@pytest.mark.asyncio
async def test_catalog_test_falls_back_to_raw_when_decoded_unsupported(fake_hass):
    """A decoded fingerprint for a protocol build_decoded_command cannot encode
    (anything but NEC today) falls through to raw replay. Forward-compat guard."""
    store = _make_signal_store(fake_hass)
    monitor = SignalMonitor(fake_hass, store, _make_hair_store())
    sig = _decoded_signal(
        decoded_protocol="SOMETHING_FUTURE",
        decoded_address=0x1,
        decoded_command=0x2,
        decoded_fingerprint="SOMETHING_FUTURE:0x1:0x2",
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[sig]))

    sentinel = object()
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch(
            "custom_components.hair.ir_command.build_decoded_command",
            return_value=None,
        ) as bdc,
        patch(
            "custom_components.hair.ir_command.build_command",
            return_value=sentinel,
        ) as bc,
    ):
        result = await monitor.test_signal("s1", "infrared.e")

    assert result["success"] is True
    bdc.assert_called_once()
    bc.assert_called_once()
    assert ir_send.call_args[0][2] is sentinel


# ---------------------------------------------------------------------------
# Edit 5 -- ws_save_captured_command decodes at save
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_captured_command_decodes_at_save(fake_hass):
    device = IRDevice(id="hd1", name="TV")
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_add_command = AsyncMock()
    result = CaptureResult(
        protocol="PRONTO", code=_PRONTO, raw_timings=[560, -560, 560, -1690],
        frequency=38000,
    )
    orchestrator = MagicMock()
    orchestrator.get_session_result = MagicMock(return_value=result)
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)
    conn = _make_connection()

    with patch(
        "custom_components.hair.protocol_decode.decode_to_fields",
        return_value=("NEC", 0x1000, 0x18, "NEC:0x1000:0x18"),
    ):
        await ws_save_captured_command(
            fake_hass,
            conn,
            {
                "id": 1,
                "type": "hair/capture/save",
                "device_id": "hd1",
                "session_id": "sess-1",
                "command_name": "On",
            },
        )

    cmd = manager.async_add_command.call_args[0][1]
    assert cmd.decoded_protocol == "NEC"
    assert cmd.decoded_address == 0x1000
    assert cmd.decoded_command == 0x18
    assert cmd.decoded_fingerprint == "NEC:0x1000:0x18"
    assert cmd.byte_hash is not None


@pytest.mark.asyncio
async def test_save_captured_command_non_nec_leaves_fields_none(fake_hass):
    """A raw / undecodable capture leaves decoded_* and byte_hash None."""
    device = IRDevice(id="hd1", name="TV")
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_add_command = AsyncMock()
    result = CaptureResult(
        protocol=None, code=None, raw_timings=[100, -100, 100, -100], frequency=38000,
    )
    orchestrator = MagicMock()
    orchestrator.get_session_result = MagicMock(return_value=result)
    _wire_hass(fake_hass, manager=manager, orchestrator=orchestrator)
    conn = _make_connection()

    with patch(
        "custom_components.hair.protocol_decode.decode_to_fields",
        return_value=(None, None, None, None),
    ):
        await ws_save_captured_command(
            fake_hass,
            conn,
            {
                "id": 1,
                "type": "hair/capture/save",
                "device_id": "hd1",
                "session_id": "sess-1",
                "command_name": "On",
            },
        )

    cmd = manager.async_add_command.call_args[0][1]
    assert cmd.decoded_protocol is None
    assert cmd.decoded_fingerprint is None
    assert cmd.byte_hash is None


# ---------------------------------------------------------------------------
# End-to-end -- canonical on the first press, no reload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assigned_command_transmits_canonical_without_reload(fake_hass):
    """Assign a decoded NEC signal, then transmit it device-side and assert the
    encode-from-decoded path is taken -- the user-visible 'canonical on the
    first press' behavior that motivates the fix, proven without a backfill."""
    manager = _make_device_manager(fake_hass)
    hair_device = IRDevice(name="TV", emitter_entity_ids=["infrared.e"])
    manager._store.add_device(hair_device)

    sstore = _make_signal_store(fake_hass)
    monitor = SignalMonitor(fake_hass, sstore, manager._store)
    sstore.add_device(
        UnknownDevice(id="ud1", fingerprint="d", signals=[_decoded_signal()])
    )

    res = await monitor.assign_signal("ud1", "s1", hair_device.id, "Power", "custom")
    assert res["success"] is True
    cmd_id = res["command_id"]
    assert hair_device.get_command(cmd_id).decoded_fingerprint == "NEC:0x1000:0x18"

    sentinel = object()
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch(
            "custom_components.hair.ir_command.build_decoded_command",
            return_value=sentinel,
        ) as bdc,
        patch("custom_components.hair.ir_command.build_command") as bc,
    ):
        await manager.async_send_command(hair_device.id, cmd_id)

    bdc.assert_called_once()
    bc.assert_not_called()
    ir_send.assert_awaited_once()
    assert ir_send.call_args[0][2] is sentinel
