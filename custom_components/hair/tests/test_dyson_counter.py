"""The Dyson rolling counter: one per device, three values (GH #33).

Every frame here is written by hand from the table channafam posted on
GH #33: eight presses of an AM07 (device 9) handset, alternating
buttons, the wire bits as ``D:7 fn:6 counter:2``, sent as two identical
frames per press, on the handset's own measured timings (2300/885
leader, 770 marks, 870 and 1700 spaces).
"""
from __future__ import annotations

from itertools import pairwise
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.decoders.dyson import DysonCommand
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.dyson_counter import (
    counter_for_send,
    counter_key,
    last_frame_counter,
    next_counter,
    observe_heard_press,
)
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.storage import HAIRStore

#: (button, wire bits as posted, HAIR function, HAIR counter)
TABLE = [
    ("Power", "1001000" "000000" "00", 0x00, 0),
    ("Power", "1001000" "000000" "01", 0x00, 2),
    ("Speed +", "1001000" "010101" "10", 0x2A, 1),
    ("Speed +", "1001000" "010101" "00", 0x2A, 0),
    ("Speed -", "1001000" "111111" "01", 0x3F, 2),
    ("Speed -", "1001000" "111111" "10", 0x3F, 1),
    ("Swing", "1001000" "101010" "00", 0x15, 0),
    ("Swing", "1001000" "101010" "01", 0x15, 2),
]
FRAME_GAP = -107000


def _frame(wire: str) -> list[int]:
    """One frame on the handset's measured timings, bits as sent."""
    out = [2300, -885]
    for bit in wire:
        out.extend((770, -(1700 if bit == "1" else 870)))
    out.append(770)
    return out


def _press(wire: str) -> list[int]:
    """A handset press: two identical frames."""
    return [*_frame(wire), FRAME_GAP, *_frame(wire)]


def _sent_counter(command) -> int:
    """The counter a built command carries on the wire."""
    decoded = DysonCommand.from_raw_timings(list(command.get_raw_timings()))
    return decoded.counter


# ---------------------------------------------------------------------------
# 1. The captures read as the table says
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("button,wire,function,counter", TABLE)
def test_each_posted_press_decodes_to_its_row(button, wire, function, counter):
    identity = try_decode_identity(_press(wire))
    assert identity.protocol == "DYSON"
    assert (identity.address, identity.command) == (9, function)
    assert identity.extras == {"counter": counter}
    # The counter is press state, never identity.
    assert identity.fingerprint == f"DYSON:0x0009:{function:#04x}"


def test_the_handset_never_sends_three_and_runs_0_2_1():
    counters = [counter for *_rest, counter in TABLE]
    assert 3 not in counters
    assert all(next_counter(a) == b for a, b in pairwise(counters))


# ---------------------------------------------------------------------------
# 2. The order
# ---------------------------------------------------------------------------


def test_the_cycle_is_the_handsets():
    assert [next_counter(c) for c in (0, 2, 1)] == [2, 1, 0]


def test_three_is_never_next():
    assert {next_counter(c) for c in range(4)} == {0, 1, 2}
    assert next_counter(3) == 0


def test_a_device_with_no_counter_starts_from_the_row_but_never_at_three():
    device = IRDevice(name="Fan")
    assert counter_for_send(device, 9, {"counter": 1}) == 1
    assert counter_for_send(device, 9, {"counter": 3}) == 0
    assert counter_for_send(device, 9, None) == 0
    device.press_counters[counter_key(9)] = 1
    assert counter_for_send(device, 9, {"counter": 2}) == 0


def test_a_held_press_takes_its_last_frame():
    held = [*_frame(TABLE[0][1]), FRAME_GAP, *_frame(TABLE[0][1]),
            FRAME_GAP, *_frame(TABLE[1][1]), FRAME_GAP, *_frame(TABLE[1][1])]
    assert last_frame_counter(held) == 2
    assert last_frame_counter(_press(TABLE[2][1])) == 1
    assert last_frame_counter([100, -100, 100]) is None


# ---------------------------------------------------------------------------
# 3. Sends
# ---------------------------------------------------------------------------


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


def _manager(hass) -> DeviceManager:
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(hass)
        store._loaded = True
        factory = EntityFactory(hass)
        factory.async_update_entities = AsyncMock()
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="ha-1")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            manager = DeviceManager(hass, store, factory, "entry-1")
    manager._store.async_save = AsyncMock()
    return manager


def _row(command_id: str, wire: str, **extra) -> IRCommand:
    """A command stored from a handset press, the way capture stores it."""
    timings = _press(wire)
    identity = try_decode_identity(timings)
    return IRCommand(
        id=command_id,
        name=command_id,
        protocol="PRONTO",
        code=raw_to_pronto([*timings, -107000], frequency=38000),
        frequency=38000,
        decoded_protocol=identity.protocol,
        decoded_address=identity.address,
        decoded_command=identity.command,
        decoded_fingerprint=identity.fingerprint,
        decoded_extras=dict(identity.extras),
        decode_covers=identity.covers_capture,
        **extra,
    )


def _fan(device_id: str = "fan", rows=None, emitters=None) -> IRDevice:
    return IRDevice(
        id=device_id,
        name="AM07",
        emitter_entity_ids=emitters or ["infrared.e1"],
        commands=rows if rows is not None else [
            _row("power", TABLE[0][1]),    # stored at counter 0
            _row("speed_up", TABLE[3][1]),  # stored at counter 0 too
            _row("swing", TABLE[6][1]),
        ],
    )


async def _send(manager, device_id: str, command_id: str):
    with patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send:
        await manager.async_send_command(device_id, command_id)
    return ir_send


@pytest.mark.asyncio
async def test_two_buttons_share_one_counter(fake_hass):
    """Power then Speed +: under the old per-row counter both went out
    with 0 and the fan dropped the second."""
    manager = _manager(fake_hass)
    fan = _fan()
    manager._store.add_device(fan)

    sent = []
    for command_id in ("power", "speed_up", "power", "swing", "speed_up",
                       "speed_up", "power"):
        ir_send = await _send(manager, "fan", command_id)
        sent.append(_sent_counter(ir_send.call_args[0][2]))
    assert sent == [0, 2, 1, 0, 2, 1, 0]
    assert all(next_counter(a) == b for a, b in pairwise(sent))
    assert fan.press_counters == {"DYSON:9": 0}


@pytest.mark.asyncio
async def test_no_send_ever_carries_three(fake_hass):
    manager = _manager(fake_hass)
    rows = [_row("power", TABLE[0][1])]
    rows[0].decoded_extras["counter"] = 3  # what the old mod-4 left behind
    manager._store.add_device(_fan(rows=rows))
    sent = []
    for _ in range(9):
        ir_send = await _send(manager, "fan", "power")
        sent.append(_sent_counter(ir_send.call_args[0][2]))
    assert 3 not in sent
    assert sent[:4] == [0, 2, 1, 0]


@pytest.mark.asyncio
async def test_the_fingerprint_does_not_move(fake_hass):
    manager = _manager(fake_hass)
    fan = _fan()
    manager._store.add_device(fan)
    before = [c.decoded_fingerprint for c in fan.commands]
    for command_id in ("power", "speed_up", "swing"):
        await _send(manager, "fan", command_id)
    assert [c.decoded_fingerprint for c in fan.commands] == before


@pytest.mark.asyncio
async def test_a_failed_send_does_not_advance(fake_hass):
    manager = _manager(fake_hass)
    fan = _fan()
    fan.press_counters[counter_key(9)] = 2
    manager._store.add_device(fan)
    row_before = dict(fan.commands[0].decoded_extras)
    dead = AsyncMock(side_effect=RuntimeError("emitter down"))
    with patch.object(_infrared_mod, "async_send_command", dead), \
            pytest.raises(RuntimeError):
        await manager.async_send_command("fan", "power")
    assert fan.press_counters == {"DYSON:9": 2}
    assert fan.commands[0].decoded_extras == row_before
    manager._store.async_save.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_count_two_repeats_one_counter_and_advances_once(fake_hass):
    """Like the handset's two identical frames."""
    manager = _manager(fake_hass)
    rows = [_row("power", TABLE[0][1], send_count=2)]
    fan = _fan(rows=rows)
    manager._store.add_device(fan)
    ir_send = await _send(manager, "fan", "power")
    counters = {_sent_counter(call.args[2]) for call in ir_send.call_args_list}
    assert ir_send.await_count == 2
    assert counters == {0}
    assert fan.press_counters == {"DYSON:9": 0}


@pytest.mark.asyncio
async def test_two_fans_on_different_addresses_keep_their_own(fake_hass):
    manager = _manager(fake_hass)
    am07 = _fan("am07")
    am02_wire = "1010000" "000000" "00"  # device 5, the AM02/AM03 towers
    am02 = _fan("am02", rows=[_row("power", am02_wire)])
    manager._store.add_device(am07)
    manager._store.add_device(am02)

    await _send(manager, "am07", "power")
    await _send(manager, "am07", "speed_up")
    ir_send = await _send(manager, "am02", "power")
    assert _sent_counter(ir_send.call_args[0][2]) == 0
    assert am07.press_counters == {"DYSON:9": 2}
    assert am02.press_counters == {"DYSON:5": 0}


@pytest.mark.asyncio
async def test_the_counter_survives_a_reload(fake_hass):
    manager = _manager(fake_hass)
    manager._store.add_device(_fan())
    await _send(manager, "fan", "power")
    await _send(manager, "fan", "speed_up")  # sent 2

    reloaded = IRDevice.from_dict(manager._store.get_device("fan").to_dict())
    assert reloaded.press_counters == {"DYSON:9": 2}

    fresh = _manager(fake_hass)
    fresh._store.add_device(reloaded)
    ir_send = await _send(fresh, "fan", "swing")
    assert _sent_counter(ir_send.call_args[0][2]) == 1


@pytest.mark.asyncio
async def test_the_counter_survives_the_store_on_disk(fake_hass):
    backing = _FakeStore()
    fan = _fan()
    fan.press_counters[counter_key(9)] = 1
    backing._data = {"devices": [fan.to_dict()], "triggers": []}
    with patch(
        "custom_components.hair.storage._HAIRDeviceStore",
        lambda *a, **k: backing,
    ):
        store = HAIRStore(fake_hass)
        await store.async_load()
    assert store.get_device("fan").press_counters == {"DYSON:9": 1}


def test_a_device_that_never_pressed_writes_no_key():
    assert "press_counters" not in IRDevice(name="TV").to_dict()
    assert IRDevice.from_dict({"name": "TV"}).press_counters == {}


def test_malformed_counters_are_dropped_on_load():
    loaded = IRDevice.from_dict({
        "name": "Fan",
        "press_counters": {"DYSON:9": 2, "DYSON:5": "x", 7: 1, "DYSON:4": True},
    })
    assert loaded.press_counters == {"DYSON:9": 2}


def test_a_clone_starts_from_the_same_counter():
    fan = _fan()
    fan.press_counters[counter_key(9)] = 2
    clone = fan.clone("AM07 copy")
    assert clone.press_counters == {"DYSON:9": 2}
    clone.press_counters[counter_key(9)] = 0
    assert fan.press_counters == {"DYSON:9": 2}


# ---------------------------------------------------------------------------
# 4. Hearing the handset
# ---------------------------------------------------------------------------


def test_a_heard_press_sets_the_device_counter():
    fan = _fan()
    moved = observe_heard_press([fan], 9, 1)
    assert moved is fan
    assert fan.press_counters == {"DYSON:9": 1}
    assert counter_for_send(fan, 9, {"counter": 0}) == 0


def test_a_heard_press_for_another_address_moves_nothing():
    fan = _fan()
    assert observe_heard_press([fan], 5, 1) is None
    assert fan.press_counters == {}


def test_two_devices_on_one_address_are_left_alone():
    """HAIR cannot tell which fan the handset was pointed at."""
    one, two = _fan("one"), _fan("two")
    assert observe_heard_press([one, two], 9, 1) is None
    assert one.press_counters == two.press_counters == {}


def _monitor(hair_store):
    from custom_components.hair.signal_monitor import SignalMonitor
    from custom_components.hair.signal_store import SignalStore

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    monitor = SignalMonitor(hass, SignalStore(hass), hair_store)
    return monitor


def _store_with(*devices):
    store = MagicMock()
    store.get_all_devices = MagicMock(return_value=list(devices))
    store.update_device = MagicMock()
    store.async_save = AsyncMock()
    return store


def _heard(wire_presses: list[str]):
    from custom_components.hair.signal_monitor import CaptureResult, normalize

    timings: list[int] = []
    for wire in wire_presses:
        if timings:
            timings.append(FRAME_GAP)
        timings.extend(_press(wire))
    return normalize(CaptureResult(
        protocol="PRONTO",
        code=raw_to_pronto([*timings, -107000], frequency=38000),
        raw_timings=timings,
        frequency=38000,
    ))


@pytest.mark.asyncio
async def test_the_receive_path_moves_the_counter_on_a_handset_press():
    fan = _fan()
    store = _store_with(fan)
    monitor = _monitor(store)
    await monitor._observe_dyson_press(_heard([TABLE[4][1]]))  # Speed -, 2
    assert fan.press_counters == {"DYSON:9": 2}
    store.update_device.assert_called_once_with(fan)
    store.async_save.assert_awaited_once()

    # Hearing the same value again writes nothing.
    await monitor._observe_dyson_press(_heard([TABLE[4][1]]))
    store.async_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_hairs_own_echo_does_not_move_it():
    """The echo claim returns before any consumer sees the capture."""
    fan = _fan()
    fan.press_counters[counter_key(9)] = 0
    store = _store_with(fan)
    monitor = _monitor(store)
    monitor._match_echo = AsyncMock(return_value=True)
    trigger_manager = MagicMock()
    monitor._trigger_manager = trigger_manager

    n = _heard([TABLE[5][1]])  # a frame carrying counter 1
    with patch("custom_components.hair.signal_monitor.normalize", return_value=n):
        await monitor._process_parsed_signal(MagicMock(), "infrared.rx")
    assert fan.press_counters == {"DYSON:9": 0}
    trigger_manager.on_signal_captured.assert_not_called()


@pytest.mark.asyncio
async def test_a_human_press_moves_it_before_the_triggers_run():
    """A trigger that starts a send already sees the heard counter."""
    fan = _fan()
    store = _store_with(fan)
    monitor = _monitor(store)
    monitor._match_echo = AsyncMock(return_value=None)
    seen = []
    trigger_manager = MagicMock()
    trigger_manager.on_signal_captured = MagicMock(
        side_effect=lambda *a, **k: seen.append(dict(fan.press_counters))
    )
    monitor._trigger_manager = trigger_manager

    n = _heard([TABLE[2][1]])  # Speed +, counter 1
    with patch("custom_components.hair.signal_monitor.normalize", return_value=n):
        await monitor._process_parsed_signal(MagicMock(), "infrared.rx")
    assert seen == [{"DYSON:9": 1}]


@pytest.mark.asyncio
async def test_after_a_heard_press_the_next_send_follows_it(fake_hass):
    manager = _manager(fake_hass)
    fan = _fan()
    manager._store.add_device(fan)
    await _send(manager, "fan", "power")          # HAIR sends 0
    observe_heard_press([fan], 9, 2)               # the handset sent 2
    ir_send = await _send(manager, "fan", "power")
    assert _sent_counter(ir_send.call_args[0][2]) == 1


@pytest.mark.asyncio
async def test_a_catalog_test_press_steps_in_the_handsets_order(fake_hass):
    """A Sniffer row belongs to no device, so it keeps its own counter,
    but it steps 0, 2, 1 and never sends 3."""
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_monitor import SignalMonitor
    from custom_components.hair.signal_store import SignalStore

    store = SignalStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    monitor = SignalMonitor(fake_hass, store, MagicMock())
    row = _row("power", TABLE[0][1])
    signal = UnknownSignal(
        id="s1", fingerprint="s1", protocol="PRONTO", code=row.code,
        frequency=38000, decoded_protocol="DYSON", decoded_address=9,
        decoded_command=0, decoded_fingerprint=row.decoded_fingerprint,
        decoded_extras={"counter": 3},
    )
    store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[signal]))

    sent = []
    for _ in range(4):
        with patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"] is True
        sent.append(_sent_counter(ir_send.call_args[0][2]))
    # A stored 3 is never sent: the cycle starts again at 0.
    assert sent == [0, 2, 1, 0]
