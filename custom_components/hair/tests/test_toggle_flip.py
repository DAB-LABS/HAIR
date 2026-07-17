"""Tests for RC-5-family toggle handling and decoded_extras flow (v0.6.0).

The toggle bit alternates between distinct key presses on RC-5 and
Marantz remotes. HAIR models it as press STATE in ``decoded_extras``:
excluded from identity (test_protocol_registry covers that), threaded
into the decoded TX rebuild, and flipped exactly once per successful
send-command / Test call -- after the full emitter loop, never
per-emitter and never per send_count frame (plan finding N1).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import (
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

_PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


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
        factory.async_update_entities = AsyncMock()
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="ha-dev-1")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            return DeviceManager(hass, store, factory, "entry-1")


def _rc5_command(toggle: int = 0) -> IRCommand:
    return IRCommand(
        id="c1",
        name="Volume Up",
        protocol="PRONTO",
        code=_PRONTO,
        frequency=36000,
        decoded_protocol="RC5",
        decoded_address=5,
        decoded_command=0x10,
        decoded_fingerprint="RC5:0x0005:0x10",
        decoded_extras={"toggle": toggle},
    )


def _rc5_device(command: IRCommand) -> IRDevice:
    return IRDevice(
        id="d1",
        name="Amp",
        commands=[command],
        emitter_entity_ids=["infrared.e1", "infrared.e2"],
    )


@pytest.mark.asyncio
async def test_send_flips_toggle_once_after_full_emitter_loop(fake_hass):
    manager = _make_device_manager(fake_hass)
    command = _rc5_command(toggle=0)
    manager._store.add_device(_rc5_device(command))
    manager._store.async_save = AsyncMock()

    with patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send:
        await manager.async_send_command("d1", "c1")

    # Two emitters, one send: toggle flipped exactly once.
    assert ir_send.await_count == 2
    assert command.decoded_extras["toggle"] == 1
    manager._store.async_save.assert_awaited_once()
    # The transmitted command carried the PRE-flip toggle.
    sent = ir_send.call_args[0][2]
    assert getattr(sent, "toggle", None) == 0

    # A second send flips back -- alternation, not latching.
    with patch.object(_infrared_mod, "async_send_command", AsyncMock()):
        await manager.async_send_command("d1", "c1")
    assert command.decoded_extras["toggle"] == 0


@pytest.mark.asyncio
async def test_send_count_repeats_same_toggle(fake_hass):
    """send_count > 1 is one logical press: same toggle N times, one flip."""
    manager = _make_device_manager(fake_hass)
    command = _rc5_command(toggle=1)
    command.send_count = 3
    manager._store.add_device(_rc5_device(command))
    manager._store.async_save = AsyncMock()

    sent_toggles = []

    async def _capture(hass, emitter, cmd):
        sent_toggles.append(getattr(cmd, "toggle", None))

    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock(side_effect=_capture)),
        patch("custom_components.hair.device_manager.asyncio.sleep", AsyncMock()),
    ):
        await manager.async_send_command("d1", "c1")

    assert sent_toggles == [1] * 6  # 3 frames x 2 emitters, all pre-flip
    assert command.decoded_extras["toggle"] == 0


@pytest.mark.asyncio
async def test_failed_send_does_not_flip(fake_hass):
    manager = _make_device_manager(fake_hass)
    command = _rc5_command(toggle=0)
    manager._store.add_device(_rc5_device(command))
    manager._store.async_save = AsyncMock()

    with (
        patch.object(
            _infrared_mod,
            "async_send_command",
            AsyncMock(side_effect=RuntimeError("emitter offline")),
        ),
        pytest.raises(RuntimeError),
    ):
        await manager.async_send_command("d1", "c1")

    assert command.decoded_extras["toggle"] == 0
    manager._store.async_save.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_toggle_protocol_never_saves(fake_hass):
    """A decoded NEC send has no toggle state and must not touch storage."""
    manager = _make_device_manager(fake_hass)
    command = IRCommand(
        id="c1",
        name="Power",
        protocol="PRONTO",
        code=_PRONTO,
        decoded_protocol="NEC",
        decoded_address=0x04,
        decoded_command=0x08,
        decoded_fingerprint="NEC:0x0004:0x08",
    )
    manager._store.add_device(_rc5_device(command))
    manager._store.async_save = AsyncMock()

    with patch.object(_infrared_mod, "async_send_command", AsyncMock()):
        await manager.async_send_command("d1", "c1")

    manager._store.async_save.assert_not_awaited()


@pytest.mark.asyncio
async def test_catalog_test_flips_signal_toggle(fake_hass):
    store = SignalStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    monitor = SignalMonitor(fake_hass, store, MagicMock())
    signal = UnknownSignal(
        id="s1",
        fingerprint="s1",
        protocol="PRONTO",
        code=_PRONTO,
        frequency=36000,
        decoded_protocol="RC5",
        decoded_address=5,
        decoded_command=0x10,
        decoded_fingerprint="RC5:0x0005:0x10",
        decoded_extras={"toggle": 0},
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[signal]))

    with patch.object(_infrared_mod, "async_send_command", AsyncMock()):
        result = await monitor.test_signal("s1", "infrared.e")

    assert result["success"] is True
    assert signal.decoded_extras["toggle"] == 1
    store.async_save.assert_awaited_once()


def test_provenance_copies_decoded_extras():
    """Assign carries extras onto the command as an independent copy."""
    signal = UnknownSignal(
        id="s1",
        fingerprint="s1",
        decoded_protocol="RC5",
        decoded_fingerprint="RC5:0x0005:0x10",
        decoded_extras={"toggle": 1},
    )
    command = IRCommand(name="Volume Up")
    _apply_signal_provenance(command, signal)
    assert command.decoded_extras == {"toggle": 1}
    command.decoded_extras["toggle"] = 0
    assert signal.decoded_extras["toggle"] == 1  # no shared dict

    bare = UnknownSignal(id="s2", fingerprint="s2")
    command2 = IRCommand(name="Mute")
    _apply_signal_provenance(command2, bare)
    assert command2.decoded_extras is None


def test_models_serialize_decoded_extras_round_trip():
    command = _rc5_command(toggle=1)
    assert IRCommand.from_dict(command.to_dict()).decoded_extras == {"toggle": 1}
    signal = UnknownSignal(
        id="s1", fingerprint="s1", decoded_extras={"extension": 1}
    )
    assert (
        UnknownSignal.from_dict(signal.to_dict()).decoded_extras
        == {"extension": 1}
    )
    plain = UnknownSignal(id="s2", fingerprint="s2")
    assert UnknownSignal.from_dict(plain.to_dict()).decoded_extras is None
