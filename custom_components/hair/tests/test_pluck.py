"""Tests for the Plucker Phase 1 foundations.

Covers the extracted ``normalize()`` / ``normalize_command()`` helpers, the
HAIR Tweezer observer emitter's capture API, a hardware-free recording
emitter for TX assertions, and the plucked model round-trips.
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import pluck
from custom_components.hair.const import TWEEZER_OBSERVER_ATTR
from custom_components.hair.event_parser import EventParser
from custom_components.hair.infrared import HAIRTweezer
from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.models import (
    CaptureResult,
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.pluckable_loader import validate_pluckable
from custom_components.hair.protocol_decode import decode_to_fields
from custom_components.hair.signal_monitor import (
    NormalizedSignal,
    SignalMonitor,
    normalize,
    normalize_command,
)
from custom_components.hair.signal_store import SignalStore

# --- fakes ----------------------------------------------------------------


class _FakeCommand:
    """Minimal stand-in for an infrared Command at the Tweezer boundary."""

    def __init__(self, timings: list[int], modulation: int | None = 38000) -> None:
        self._timings = timings
        self.modulation = modulation

    def get_raw_timings(self) -> list[int]:
        return self._timings


class RecordingEmitter:
    """Hardware-free emitter that records dispatched Commands.

    The pure-Python counterpart to the HAIR Tweezer for TX assertions: feed
    it Commands and inspect exactly what was dispatched, no hardware needed.
    """

    def __init__(self) -> None:
        self.commands: list[object] = []

    async def async_send_command(self, command: object) -> None:
        self.commands.append(command)


_NEC = CaptureResult(
    protocol="NEC",
    code="0x20DF10EF",
    raw_timings=[9000, -4500, 560, -560, 560, -1690, 560, -560],
    frequency=38000,
)


# --- normalize() ----------------------------------------------------------


def test_normalize_matches_direct_helper_calls():
    """normalize() must reproduce the exact values the inline pipeline
    computed, so the extraction is behavior-preserving for the Sniffer.
    """
    parsed = _NEC
    n = normalize(parsed)
    assert isinstance(n, NormalizedSignal)
    assert n.sig_fp == EventParser.signal_fingerprint(
        parsed.protocol, parsed.code, parsed.raw_timings
    )
    assert n.device_address == EventParser.extract_device_address(
        parsed.protocol, parsed.code
    )
    assert n.dev_fp == EventParser.device_fingerprint(
        parsed.protocol, n.device_address, parsed.raw_timings,
        code=parsed.code,
    )
    assert n.byte_hash == EventParser.pronto_byte_hash(parsed.code)
    assert (
        n.decoded_protocol,
        n.decoded_address,
        n.decoded_command,
        n.decoded_fingerprint,
    ) == decode_to_fields(parsed.raw_timings)
    assert n.protocol == "NEC"
    assert n.code == "0x20DF10EF"
    assert n.raw_timings == list(parsed.raw_timings)
    assert n.frequency == 38000


def test_normalize_frequency_default_when_absent():
    parsed = CaptureResult(protocol="NEC", code="0x1", raw_timings=[100, -100])
    n = normalize(parsed)
    assert n.frequency == 38000  # DEFAULT_CARRIER_FREQUENCY


# --- normalize_command() --------------------------------------------------


def test_normalize_command_builds_pronto_capture():
    timings = [9000, -4500, 560, -560, 560, -1690]
    cmd = _FakeCommand(timings, modulation=38000)
    n = normalize_command(cmd)
    assert n.protocol == "PRONTO"
    assert n.raw_timings == timings
    assert n.frequency == 38000
    # Equivalent to normalizing a hand-built CaptureResult.
    expected = normalize(
        CaptureResult(
            protocol="PRONTO",
            code=raw_to_pronto(timings, frequency=38000),
            raw_timings=timings,
            frequency=38000,
        )
    )
    assert n.code == expected.code
    assert n.sig_fp == expected.sig_fp
    assert n.byte_hash == expected.byte_hash


def test_normalize_command_falls_back_to_default_modulation():
    cmd = _FakeCommand([100, -100], modulation=None)
    n = normalize_command(cmd)
    assert n.frequency == 38000


# --- HAIR Tweezer ---------------------------------------------------------


def test_tweezer_marker_and_unique_id():
    t = HAIRTweezer("entry-123")
    assert t._attr_unique_id == "entry-123_hair_tweezer"
    assert t.extra_state_attributes == {TWEEZER_OBSERVER_ATTR: True}
    assert t._attr_name == "HAIR Tweezer"


async def test_tweezer_captures_into_active_session():
    t = HAIRTweezer("e")
    t.open_session("s1")
    cmd = object()
    await t.async_send_command(cmd)
    assert t.pop_captures("s1") == [cmd]
    # Popping closes the session; a second pop is empty.
    assert t.pop_captures("s1") == []


async def test_tweezer_multi_code_session_keeps_order():
    t = HAIRTweezer("e")
    t.open_session("s")
    a, b, c = object(), object(), object()
    await t.async_send_command(a)
    await t.async_send_command(b)
    await t.async_send_command(c)
    assert t.pop_captures("s") == [a, b, c]


async def test_tweezer_drops_command_with_no_open_session():
    t = HAIRTweezer("e")
    await t.async_send_command(object())
    assert t.pop_captures("anything") == []


# --- recording emitter (hardware-free TX capture) -------------------------


async def test_recording_emitter_records_dispatched_commands():
    emitter = RecordingEmitter()
    a, b = object(), object()
    await emitter.async_send_command(a)
    await emitter.async_send_command(b)
    assert emitter.commands == [a, b]


# --- model round-trips ----------------------------------------------------


def test_plucked_device_and_signal_round_trip():
    sig = UnknownSignal(
        fingerprint="fp", source="plucked", plucked_command_name="pwr_on"
    )
    dev = UnknownDevice(
        fingerprint="fp",
        source="plucked",
        vendor_entity_id="remote.ir_remote_garage",
        appliance="candles",
        signals=[sig],
    )
    d = dev.to_dict()
    assert d["source"] == "plucked"
    assert d["vendor_entity_id"] == "remote.ir_remote_garage"
    assert d["appliance"] == "candles"
    assert d["signals"][0]["plucked_command_name"] == "pwr_on"

    back = UnknownDevice.from_dict(d)
    assert back.source == "plucked"
    assert back.vendor_entity_id == "remote.ir_remote_garage"
    assert back.appliance == "candles"
    assert back.signals[0].plucked_command_name == "pwr_on"
    assert back.signals[0].source == "plucked"


def test_ircommand_plucked_command_name_round_trip():
    cmd = IRCommand(name="Power", plucked_command_name="pwr_on")
    back = IRCommand.from_dict(cmd.to_dict())
    assert back.plucked_command_name == "pwr_on"


def test_legacy_dicts_without_new_fields_still_load():
    """A v0.4.20 record lacking the new keys decodes with safe defaults."""
    legacy = {
        "id": "d1",
        "fingerprint": "fp",
        "source": "sniffed",
        "signals": [{"id": "s1", "fingerprint": "fp", "source": "sniffed"}],
    }
    dev = UnknownDevice.from_dict(legacy)
    assert dev.vendor_entity_id is None
    assert dev.appliance is None
    assert dev.signals[0].plucked_command_name is None

    cmd = IRCommand.from_dict({"id": "c1", "name": "Power"})
    assert cmd.plucked_command_name is None


# --- pluck orchestrator ---------------------------------------------------

_TUYA = validate_pluckable(
    {
        "schema_version": 1,
        "name": "Tuya Local",
        "integration": "tuya_local",
        "remote_feature_filter": "LEARN_COMMAND",
        "service": {
            "domain": "tuya_local",
            "name": "send_learned_ir_command",
            "target_param": "entity_id",
            "data": {
                "command": "{command_name}",
                "device": "{appliance}",
                "emitter_entity_id": "{tweezer}",
            },
        },
        "error_map": {"device must be specified": "Set an appliance on this blaster."},
    }
)


class _Services:
    def __init__(self, on_call=None, raises=None, has=True):
        self._on_call = on_call
        self._raises = raises
        self._has = has

    def has_service(self, domain, name):
        return self._has

    async def async_call(
        self, domain, name, target=None, service_data=None, blocking=False
    ):
        if self._raises is not None:
            raise self._raises
        if self._on_call is not None:
            await self._on_call(domain, name, target, service_data)


class _Hass:
    def __init__(self, services):
        self.services = services
        self.data = {}


def _ready_tweezer():
    t = HAIRTweezer("e")
    t.entity_id = "infrared.hair_tweezer"
    return t


async def test_run_pluck_happy_path():
    t = _ready_tweezer()
    seen = {}

    async def on_call(domain, name, target, service_data):
        seen["domain"] = domain
        seen["name"] = name
        seen["target"] = target
        seen["service_data"] = service_data
        await t.async_send_command(_FakeCommand([9000, -4500, 560, -560], 38000))

    hass = _Hass(_Services(on_call=on_call))
    result = await pluck.run_pluck(
        hass,
        entry_data={"tweezer": t},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.ir_remote_garage",
        appliance="candles",
        command_name="pwr_on",
    )
    assert seen["domain"] == "tuya_local"
    assert seen["name"] == "send_learned_ir_command"
    assert seen["target"] == {"entity_id": "remote.ir_remote_garage"}
    assert seen["service_data"] == {
        "command": "pwr_on",
        "device": "candles",
        "emitter_entity_id": "infrared.hair_tweezer",
    }
    assert len(result["signals"]) == 1
    sig = result["signals"][0]
    assert sig["protocol"] == "PRONTO"
    assert sig["plucked_command_name"] == "pwr_on"
    assert sig["suggested_alias"] == "pwr_on"


async def test_run_pluck_multi_code_suffixes_aliases():
    t = _ready_tweezer()

    async def on_call(domain, name, target, service_data):
        await t.async_send_command(_FakeCommand([9000, -4500, 560, -560], 38000))
        await t.async_send_command(_FakeCommand([8000, -4000, 500, -500], 38000))

    hass = _Hass(_Services(on_call=on_call))
    result = await pluck.run_pluck(
        hass,
        entry_data={"tweezer": t},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.x",
        appliance="candles",
        command_name="pwr",
    )
    assert [s["suggested_alias"] for s in result["signals"]] == ["pwr_1", "pwr_2"]


async def test_run_pluck_no_captures_is_no_response():
    t = _ready_tweezer()

    async def on_call(domain, name, target, service_data):
        return  # vendor returns but dispatches nothing

    hass = _Hass(_Services(on_call=on_call))
    result = await pluck.run_pluck(
        hass,
        entry_data={"tweezer": t},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.x",
        appliance="candles",
        command_name="nope",
    )
    assert result["error"] == "no_response"


async def test_run_pluck_value_error_passes_through_prefixed():
    t = _ready_tweezer()
    hass = _Hass(_Services(raises=ValueError("Command 'x' not found for candles")))
    result = await pluck.run_pluck(
        hass,
        entry_data={"tweezer": t},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.x",
        appliance="candles",
        command_name="x",
    )
    assert result["error"] == "vendor_error"
    assert result["message"] == "Tuya Local: Command 'x' not found for candles"


async def test_run_pluck_error_map_friendly_message():
    t = _ready_tweezer()
    hass = _Hass(_Services(raises=ValueError("device must be specified")))
    result = await pluck.run_pluck(
        hass,
        entry_data={"tweezer": t},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.x",
        appliance="",
        command_name="x",
    )
    assert result["error"] == "vendor_error"
    assert result["message"] == "Set an appliance on this blaster."


async def test_run_pluck_no_tweezer():
    hass = _Hass(_Services())
    result = await pluck.run_pluck(
        hass,
        entry_data={},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.x",
        appliance="candles",
        command_name="x",
    )
    assert result["error"] == "no_tweezer"


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio.wait_for raises asyncio.TimeoutError (not the builtin) on 3.10",
)
async def test_run_pluck_timeout(monkeypatch):
    t = _ready_tweezer()

    async def slow(domain, name, target, service_data):
        await asyncio.sleep(0.2)

    monkeypatch.setattr(pluck, "PLUCK_TIMEOUT_S", 0.01)
    hass = _Hass(_Services(on_call=slow))
    result = await pluck.run_pluck(
        hass,
        entry_data={"tweezer": t},
        vendor_entry=_TUYA,
        vendor_entity_id="remote.x",
        appliance="candles",
        command_name="x",
    )
    assert result["error"] == "no_response"


async def test_run_pluck_serializes_two_sessions():
    """Two concurrent plucks must not cross-contaminate captures."""
    t = _ready_tweezer()

    def make_on_call(tag):
        async def on_call(domain, name, target, service_data):
            await asyncio.sleep(0.01)
            await t.async_send_command(_FakeCommand([100, -100], 38000))

        return on_call

    async def one(command_name):
        hass = _Hass(_Services(on_call=make_on_call(command_name)))
        return await pluck.run_pluck(
            hass,
            entry_data=entry_data,
            vendor_entry=_TUYA,
            vendor_entity_id="remote.x",
            appliance="candles",
            command_name=command_name,
        )

    entry_data = {"tweezer": t}
    results = await asyncio.gather(one("a"), one("b"))
    # Each pluck gets exactly one capture; the lock prevents interleaving.
    assert all(len(r["signals"]) == 1 for r in results)


# --- vendor discovery -----------------------------------------------------


class _RegEntry:
    def __init__(
        self,
        entity_id,
        platform,
        supported_features=0,
        disabled_by=None,
        name=None,
    ):
        self.entity_id = entity_id
        self.platform = platform
        self.supported_features = supported_features
        self.disabled_by = disabled_by
        self.name = name
        self.original_name = None


class _EntReg:
    def __init__(self, entries):
        self.entities = {e.entity_id: e for e in entries}


def _patch_entreg(monkeypatch, entries):
    monkeypatch.setattr(pluck.er, "async_get", lambda hass: _EntReg(entries))


def test_list_vendors_returns_blaster(monkeypatch):
    _patch_entreg(
        monkeypatch,
        [
            _RegEntry(
                "remote.ir_remote_garage",
                "tuya_local",
                supported_features=1,
                name="IR Remote Garage",
            )
        ],
    )
    hass = _Hass(_Services(has=True))
    vendors = pluck.list_vendors(hass, [_TUYA])
    assert len(vendors) == 1
    assert vendors[0]["integration"] == "tuya_local"
    assert vendors[0]["blasters"][0]["entity_id"] == "remote.ir_remote_garage"
    assert vendors[0]["blasters"][0]["name"] == "IR Remote Garage"


def test_list_vendors_empty_when_service_absent(monkeypatch):
    _patch_entreg(
        monkeypatch,
        [_RegEntry("remote.ir_remote_garage", "tuya_local", supported_features=1)],
    )
    hass = _Hass(_Services(has=False))
    assert pluck.list_vendors(hass, [_TUYA]) == []


def test_list_vendors_feature_filter_excludes_non_learners(monkeypatch):
    _patch_entreg(
        monkeypatch,
        [_RegEntry("remote.no_learn", "tuya_local", supported_features=0)],
    )
    hass = _Hass(_Services(has=True))
    assert pluck.list_vendors(hass, [_TUYA]) == []


def test_list_vendors_skips_other_integrations(monkeypatch):
    _patch_entreg(
        monkeypatch,
        [_RegEntry("remote.broadlink_x", "broadlink", supported_features=1)],
    )
    hass = _Hass(_Services(has=True))
    assert pluck.list_vendors(hass, [_TUYA]) == []


# --- Phase 3: plucked create paths + assign propagation -------------------

_PRONTO_A = "0000 006D 0002 0000 0010 0010 0010 0010"
_PRONTO_B = "0000 006D 0002 0000 0010 0010 0010 0040"


def _monitor():
    hass = MagicMock()
    store = SignalStore(hass)
    store._loaded = True
    hair_store = MagicMock()
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    return SignalMonitor(hass, store, hair_store), store, hair_store


async def test_create_plucked_blaster_round_trip():
    monitor, store, _ = _monitor()
    device = await monitor.create_plucked_blaster(
        "remote.ir_remote_garage", "candles", "Tuya candles"
    )
    assert device.source == "plucked"
    assert device.vendor_entity_id == "remote.ir_remote_garage"
    assert device.appliance == "candles"
    assert device.fingerprint.startswith("plucked:")
    assert store.get_device(device.id) is device


async def test_create_plucked_signal_lands_on_named_blaster():
    monitor, store, _ = _monitor()
    blaster = await monitor.create_plucked_blaster("remote.x", "candles", "B")
    result = await monitor.create_plucked_signal(
        blaster.id, _PRONTO_A, "pwr_on", alias="Power On"
    )
    assert result["success"] is True
    stored = store.get_device(blaster.id)
    assert len(stored.signals) == 1
    sig = stored.signals[0]
    assert sig.source == "plucked"
    assert sig.plucked_command_name == "pwr_on"
    assert sig.alias == "Power On"
    # On the named blaster, not a fingerprint-grouped sniffed device.
    assert stored.source == "plucked"


async def test_create_plucked_signal_rejects_non_plucked_device():
    monitor, _, _ = _monitor()
    manual = await monitor.create_manual_remote("Clip")
    result = await monitor.create_plucked_signal(manual.id, _PRONTO_A, "x")
    assert result["success"] is False
    assert result["code"] == "not_plucked"


async def test_create_plucked_signal_duplicate_rejected():
    monitor, _, _ = _monitor()
    blaster = await monitor.create_plucked_blaster("remote.x", "candles", "B")
    first = await monitor.create_plucked_signal(blaster.id, _PRONTO_A, "a")
    assert first["success"] is True
    dup = await monitor.create_plucked_signal(blaster.id, _PRONTO_A, "a-again")
    assert dup["success"] is False
    assert dup["code"] == "duplicate_signal"


async def test_create_plucked_signal_distinct_codes_both_kept():
    monitor, store, _ = _monitor()
    blaster = await monitor.create_plucked_blaster("remote.x", "candles", "B")
    await monitor.create_plucked_signal(blaster.id, _PRONTO_A, "a")
    await monitor.create_plucked_signal(blaster.id, _PRONTO_B, "b")
    assert len(store.get_device(blaster.id).signals) == 2


async def test_create_plucked_signal_invalid_pronto():
    monitor, _, _ = _monitor()
    blaster = await monitor.create_plucked_blaster("remote.x", "candles", "B")
    result = await monitor.create_plucked_signal(blaster.id, "not pronto", "x")
    assert result["success"] is False
    assert result["code"] == "invalid_pronto"


async def test_create_plucked_signal_missing_blaster():
    monitor, _, _ = _monitor()
    result = await monitor.create_plucked_signal("nope", _PRONTO_A, "x")
    assert result["success"] is False
    assert result["code"] == "device_not_found"


async def test_assign_signal_propagates_plucked_command_name():
    monitor, store, hair_store = _monitor()
    sig = UnknownSignal(
        id="sig1",
        fingerprint="sig1",
        protocol="NEC",
        code="0x1234",
        frequency=38000,
        source="plucked",
        plucked_command_name="pwr_on",
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="dev", signals=[sig]))
    hair_device = IRDevice(id="hd1", name="TV")
    hair_store.get_device.return_value = hair_device
    result = await monitor.assign_signal("ud1", "sig1", "hd1", "Power", "custom")
    assert result["success"] is True
    assert hair_device.commands[0].plucked_command_name == "pwr_on"


async def test_assign_to_new_device_propagates_plucked_command_name():
    monitor, store, _ = _monitor()
    sig = UnknownSignal(
        id="sig1",
        fingerprint="sig1",
        protocol="NEC",
        code="0x1234",
        frequency=38000,
        source="plucked",
        plucked_command_name="pwr_off",
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="dev", signals=[sig]))
    result = await monitor.assign_to_new_device(
        "ud1", "sig1", "New TV", "media_player", ["infrared.x"], "Power", "custom"
    )
    assert result["success"] is True
    assert result["device"].commands[0].plucked_command_name == "pwr_off"
