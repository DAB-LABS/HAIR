"""Tests for the v0.5.7 dots polish backend + hair_signal_updated event.

Covers:
- ``_assignment_index`` / ``_augment_signals_with_assignments`` count math
  (dots plan acceptance #10: 0, 1, and 3 assignments across 2 devices),
- the ``hair_signal_updated`` bus event firing on assign and command delete.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN, EVENT_SIGNAL_UPDATED
from custom_components.hair.event_parser import EventParser
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    _assignment_index,
    _augment_signals_with_assignments,
    ws_delete_command,
)

_CODE_A = "0000 006D 0002 0000 0020 0040 0020 0040"
_CODE_B = "0000 006D 0002 0000 0030 0050 0030 0050"


def _fp(code: str) -> str:
    return EventParser.signal_fingerprint("PRONTO", code, None)


def _cmd(name: str, code: str) -> IRCommand:
    return IRCommand(name=name, protocol="PRONTO", code=code)


# ---------------------------------------------------------------------------
# Assignment-count math
# ---------------------------------------------------------------------------


class TestAssignmentIndex:
    def test_zero_assignments(self):
        assert _assignment_index([]) == {}

    def test_single_assignment(self):
        d = IRDevice(id="d1", name="TV", commands=[_cmd("Power", _CODE_A)])
        idx = _assignment_index([d])
        assert idx[_fp(_CODE_A)] == ["TV.Power"]

    def test_three_assignments_across_two_devices(self):
        d1 = IRDevice(
            id="d1",
            name="TV",
            commands=[_cmd("Power", _CODE_A), _cmd("Mute", _CODE_A)],
        )
        d2 = IRDevice(id="d2", name="AVR", commands=[_cmd("Power", _CODE_A)])
        idx = _assignment_index([d1, d2])
        assert idx[_fp(_CODE_A)] == ["TV.Power", "TV.Mute", "AVR.Power"]

    def test_distinct_codes_indexed_separately(self):
        d = IRDevice(
            id="d1",
            name="TV",
            commands=[_cmd("Power", _CODE_A), _cmd("Vol", _CODE_B)],
        )
        idx = _assignment_index([d])
        assert idx[_fp(_CODE_A)] == ["TV.Power"]
        assert idx[_fp(_CODE_B)] == ["TV.Vol"]


class TestAugmentSignals:
    def test_augments_count_and_list(self):
        fp = _fp(_CODE_A)
        device_dict = {
            "signals": [
                {"fingerprint": fp},
                {"fingerprint": "unassigned_fp"},
            ]
        }
        _augment_signals_with_assignments(device_dict, {fp: ["TV.Power", "AVR.Power"]})
        assert device_dict["signals"][0]["assignment_count"] == 2
        assert device_dict["signals"][0]["assigned_to"] == ["TV.Power", "AVR.Power"]
        assert device_dict["signals"][1]["assignment_count"] == 0
        assert device_dict["signals"][1]["assigned_to"] == []

    def test_no_signals_key_is_safe(self):
        d: dict = {}
        _augment_signals_with_assignments(d, {})
        assert d == {}


# ---------------------------------------------------------------------------
# hair_signal_updated bus event
# ---------------------------------------------------------------------------


def _signal(sig_id: str = "s1", code: str = _CODE_A) -> UnknownSignal:
    return UnknownSignal(
        id=sig_id, fingerprint=sig_id, protocol="PRONTO", code=code
    )


def _monitor_with_signal(fake_hass, signal: UnknownSignal):
    store = SignalStore(fake_hass)
    store._loaded = True
    store.schedule_save = MagicMock()
    store.async_save = AsyncMock()
    hair = MagicMock()
    hair.get_device = MagicMock(return_value=None)
    hair.async_save = AsyncMock()
    hair.match_command = MagicMock(return_value=None)
    monitor = SignalMonitor(fake_hass, store, hair)
    store.add_device(
        UnknownDevice(
            id="ud0", fingerprint="d0", source="manual", signals=[signal]
        )
    )
    return monitor, store, hair


@pytest.mark.asyncio
async def test_assign_to_new_device_fires_signal_updated(fake_hass):
    sig = _signal("s1")
    monitor, _store, _hair = _monitor_with_signal(fake_hass, sig)
    res = await monitor.assign_to_new_device(
        device_id="ud0",
        signal_id="s1",
        device_name="TV",
        device_type="media_player",
        emitter_entity_ids=["infrared.e"],
        command_name="Power",
        command_category="custom",
    )
    assert res["success"]
    fired = [
        c.args
        for c in fake_hass.bus.async_fire.call_args_list
        if c.args and c.args[0] == EVENT_SIGNAL_UPDATED
    ]
    assert fired, "expected a hair_signal_updated event"
    assert fired[-1][1] == {"signal_fingerprint": sig.fingerprint}


@pytest.mark.asyncio
async def test_ws_delete_command_fires_signal_updated(fake_hass):
    code = _CODE_A
    device = IRDevice(
        id="hd1", name="TV", commands=[IRCommand(id="c1", name="Power",
                                                 protocol="PRONTO", code=code)]
    )
    dm = MagicMock()
    dm.get_device = MagicMock(return_value=device)
    dm.async_remove_command = AsyncMock(return_value=True)
    fake_hass.data[DOMAIN] = {
        "e1": {
            "device_manager": dm,
            "config_entry": MagicMock(),
        }
    }
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    await ws_delete_command(
        fake_hass,
        conn,
        {
            "id": 1,
            "type": "hair/command/delete",
            "device_id": "hd1",
            "command_id": "c1",
        },
    )
    conn.send_error.assert_not_called()
    fired = [
        c.args
        for c in fake_hass.bus.async_fire.call_args_list
        if c.args and c.args[0] == EVENT_SIGNAL_UPDATED
    ]
    assert fired, "expected a hair_signal_updated event on command delete"
    assert fired[-1][1] == {"signal_fingerprint": _fp(code)}
