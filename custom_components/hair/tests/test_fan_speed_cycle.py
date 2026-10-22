"""A fan with one button that steps round its speeds (GH Discussion #201).

``speed_cycle`` is one command that moves the fan to its next speed,
wrapping from the last back to the first (or to off, when off is one of
its positions). HAIR keeps its own count of where the fan is; nothing
reads the real speed back, so the entity stays ``assumed_state``.

The contracts under test:

- the key, its template and auto-map, and that a bare "Speed" maps
  nothing;
- the three settings, through the device editor's websocket door and
  the store, with refusals that change nothing;
- features and ``speed_count`` with and without the settings, and
  discrete ``speed_N`` keys winning when both are mapped;
- the press count for every start and target, with and without off,
  and the gap between separate presses;
- one burst at a time, a new target redirecting the running one;
- turn-on landing both ways, and off (or a sensor's "off") re-zeroing;
- a cycle press sent from anywhere else moving the count one step,
  including through a pinned Remote;
- restore.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.fan import FanEntityFeature
from homeassistant.util.percentage import ordered_list_item_to_percentage

from custom_components.hair.command_templates import (
    ACTION_OPTIONS,
    COMMAND_TEMPLATES,
)
from custom_components.hair.const import DeviceType
from custom_components.hair.device_manager import AUTO_MAP_RULES, DeviceManager
from custom_components.hair.fan import (
    SPEED_CYCLE_PRESS_GAP_S,
    HAIRFanEntity,
    cycle_presses,
)
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.power_monitor import SIGNAL_POWER_VERDICT
from custom_components.hair.send_follow import cycle_step
from custom_components.hair.send_signal import (
    ORIGIN_ENTITY,
    ORIGIN_MANAGER,
    SIGNAL_DEVICE_SENT,
    DeviceSent,
)
from custom_components.hair.vocabulary import localized_auto_map
from custom_components.hair.websocket_api import ws_update_device

DEVICE_ID = "fan-1"
MODULE = "custom_components.hair.fan"
COMMANDS = ["Power", "Power Off", "Speed Cycle", "Speed 1", "Speed 2", "Oscillate"]
CYCLE = "c-speed-cycle"
POWER = "c-power"
REAL_SLEEP = asyncio.sleep


def _cid(name: str) -> str:
    return "c-" + name.lower().replace(" ", "-")


def _device(
    mapping: dict[str, str] | None = None,
    steps: int | None = 3,
    off: bool = False,
    turn_on: str = "resume",
) -> IRDevice:
    if mapping is None:
        mapping = {"power_toggle": "Power", "speed_cycle": "Speed Cycle"}
    return IRDevice(
        id=DEVICE_ID,
        name="Bedroom Fan",
        device_type=DeviceType.FAN,
        emitter_entity_ids=["infrared.e"],
        commands=[
            IRCommand(id=_cid(n), name=n, protocol="PRONTO", code="x")
            for n in COMMANDS
        ],
        entity_config=EntityConfig(
            command_mapping=dict(mapping),
            fan_speed_steps=steps,
            speed_cycle_includes_off=off,
            speed_cycle_turn_on=turn_on,
        ),
    )


class _Fan:
    """A fan entity with its sends, gaps and dispatcher handlers caught."""

    def __init__(self, device: IRDevice, manager=None) -> None:
        self.sent: list[str] = []
        self.gaps: list[float] = []
        if manager is None:
            manager = MagicMock()

            async def _send(device_id, command_id, **kwargs):
                self.sent.append(command_id)

            manager.async_send_command = AsyncMock(side_effect=_send)
        self.manager = manager
        self.entity = HAIRFanEntity(device, manager)
        self.entity.hass = MagicMock()
        self.writes = 0

        def _write():
            self.writes += 1

        self.entity.async_write_ha_state = MagicMock(side_effect=_write)
        self.handlers: dict[str, object] = {}
        self.gate: asyncio.Event | None = None

    async def fake_sleep(self, seconds: float) -> None:
        self.gaps.append(seconds)
        if self.gate is not None:
            await self.gate.wait()

    async def add(self, last_state=None) -> _Fan:
        def _connect(hass, signal, fn):
            self.handlers[signal] = fn
            return MagicMock()

        self.entity.async_get_last_state = AsyncMock(return_value=last_state)
        with patch(f"{MODULE}.async_dispatcher_connect", side_effect=_connect):
            await self.entity.async_added_to_hass()
        return self

    def at(self, position: int, is_on: bool = True) -> _Fan:
        """Put the count at ``position`` with the display to match."""
        e = self.entity
        e._cycle_pos = position
        e._is_on = is_on
        e._show_cycle_pos(position)
        e._is_on = is_on if not (e._cycle_has_off() and position == 0) else False
        return self

    def send(self, name: str, origin=ORIGIN_MANAGER) -> None:
        self.handlers[SIGNAL_DEVICE_SENT](DeviceSent(
            device_id=DEVICE_ID,
            command_id=_cid(name),
            command_name=name,
            origin=origin,
        ))

    def verdict(self, verdict: str) -> None:
        self.handlers[SIGNAL_POWER_VERDICT](DEVICE_ID, verdict)


def _pct(speed: int, speeds: int) -> int:
    return ordered_list_item_to_percentage(list(range(1, speeds + 1)), speed)


@pytest.fixture
def no_wait():
    """Gaps are recorded, not slept."""
    holder: dict[str, _Fan] = {}

    async def _sleep(seconds):
        fan = holder.get("fan")
        if fan is not None:
            await fan.fake_sleep(seconds)

    with patch(f"{MODULE}.asyncio.sleep", side_effect=_sleep):
        yield holder


async def _fan(no_wait, device=None, last_state=None) -> _Fan:
    fan = await _Fan(device or _device()).add(last_state)
    no_wait["fan"] = fan
    return fan


# ---------------------------------------------------------------------------
# The key
# ---------------------------------------------------------------------------


def test_speed_cycle_is_a_fan_action_and_template():
    assert ("speed_cycle", "Speed Cycle") in ACTION_OPTIONS[DeviceType.FAN]
    names = [t.name for t in COMMAND_TEMPLATES[DeviceType.FAN]]
    assert "Speed Cycle" in names


def test_speed_cycle_auto_maps_but_a_bare_speed_does_not():
    assert AUTO_MAP_RULES["speed cycle"] == "speed_cycle"
    assert "speed" not in AUTO_MAP_RULES
    assert "speed" not in localized_auto_map(AUTO_MAP_RULES)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Speed Cycle", "speed_cycle"),
        ("speed cycle", "speed_cycle"),
        ("Geschwindigkeit durchschalten", "speed_cycle"),
        ("Speed", None),
    ],
)
def test_assigning_a_command_maps_it(name, expected):
    manager = DeviceManager.__new__(DeviceManager)
    device = _device(mapping={}, steps=None)
    command = IRCommand(id="new", name=name, protocol="PRONTO", code="x")
    manager._auto_map_command(device, command)
    mapping = device.entity_config.command_mapping
    if expected is None:
        assert mapping == {}
    else:
        assert mapping == {expected: name}


# ---------------------------------------------------------------------------
# Settings: the store and the device editor's websocket door
# ---------------------------------------------------------------------------


def test_unset_settings_are_left_out_of_the_record():
    record = EntityConfig().to_dict()
    for key in ("fan_speed_steps", "speed_cycle_includes_off", "speed_cycle_turn_on"):
        assert key not in record


def test_settings_round_trip_through_the_record():
    config = EntityConfig(
        fan_speed_steps=4, speed_cycle_includes_off=True, speed_cycle_turn_on="speed_1"
    )
    back = EntityConfig.from_dict(config.to_dict())
    assert back.fan_speed_steps == 4
    assert back.speed_cycle_includes_off is True
    assert back.speed_cycle_turn_on == "speed_1"
    assert "fan_speed_steps" not in back._extra


@pytest.mark.parametrize("bad", [1, 11, True, "3", 2.5])
def test_an_unusable_stored_count_reads_as_unset(bad):
    config = EntityConfig.from_dict(
        {"fan_speed_steps": bad, "speed_cycle_turn_on": "sideways"}
    )
    assert config.fan_speed_steps is None
    assert config.speed_cycle_turn_on == "resume"


def _ws(device: IRDevice):
    manager = MagicMock()
    manager.get_device.return_value = device
    manager.async_update_device = AsyncMock(side_effect=lambda d: d)
    hass = MagicMock()
    connection = MagicMock()
    return hass, manager, connection


async def _update(device: IRDevice, **fields):
    hass, manager, connection = _ws(device)
    with patch(
        "custom_components.hair.websocket_api._get_first_entry_data",
        return_value={"device_manager": manager},
    ), patch(
        "custom_components.hair.websocket_api._device_full",
        AsyncMock(side_effect=lambda hass, d: d.to_dict()),
    ):
        await ws_update_device(hass, connection, {
            "id": 7, "type": "hair/device/update", "device_id": device.id, **fields,
        })
    return manager, connection


async def test_the_editor_saves_and_loads_the_settings():
    device = _device(steps=None)
    manager, connection = await _update(
        device,
        fan_speed_steps=4,
        speed_cycle_includes_off=True,
        speed_cycle_turn_on="speed_1",
    )
    manager.async_update_device.assert_awaited_once_with(device)
    payload = connection.send_result.call_args.args[1]
    assert payload["entity_config"]["fan_speed_steps"] == 4
    assert payload["entity_config"]["speed_cycle_includes_off"] is True
    assert payload["entity_config"]["speed_cycle_turn_on"] == "speed_1"


async def test_the_editor_clears_the_count_and_keeps_the_rest():
    device = _device(steps=3, off=True)
    await _update(device, fan_speed_steps=None)
    assert device.entity_config.fan_speed_steps is None
    assert device.entity_config.speed_cycle_includes_off is True


@pytest.mark.parametrize(
    "fields",
    [
        {"fan_speed_steps": 1},
        {"fan_speed_steps": 11},
        {"fan_speed_steps": True},
        {"speed_cycle_turn_on": "last"},
    ],
)
async def test_a_refused_setting_changes_nothing(fields):
    device = _device(steps=3)
    before = device.to_dict()
    manager, connection = await _update(device, name="Renamed", **fields)
    connection.send_error.assert_called_once()
    assert connection.send_error.call_args.args[1] == "invalid_format"
    manager.async_update_device.assert_not_awaited()
    assert device.to_dict() == before


# ---------------------------------------------------------------------------
# Features and speed_count
# ---------------------------------------------------------------------------


async def test_no_count_means_no_speed_control(no_wait):
    fan = await _fan(no_wait, _device(steps=None))
    assert not fan.entity.supported_features & FanEntityFeature.SET_SPEED
    assert fan.entity.speed_count == 10


async def test_a_count_without_the_key_means_no_speed_control(no_wait):
    fan = await _fan(no_wait, _device(mapping={"power_toggle": "Power"}, steps=3))
    assert not fan.entity.supported_features & FanEntityFeature.SET_SPEED


@pytest.mark.parametrize("steps", [2, 3, 5, 10])
async def test_the_key_and_a_count_give_speed_control(no_wait, steps):
    fan = await _fan(no_wait, _device(steps=steps))
    assert fan.entity.supported_features & FanEntityFeature.SET_SPEED
    assert fan.entity.speed_count == steps
    assert fan.entity._attr_assumed_state is True


async def test_discrete_speed_keys_win(no_wait):
    device = _device(
        mapping={
            "power_toggle": "Power",
            "speed_cycle": "Speed Cycle",
            "speed_1": "Speed 1",
            "speed_2": "Speed 2",
        },
        steps=4,
    )
    fan = await _fan(no_wait, device)
    assert fan.entity.speed_count == 2
    fan.entity._is_on = True
    await fan.entity.async_set_percentage(100)
    assert fan.sent == ["c-speed-2"]


# ---------------------------------------------------------------------------
# Pressing: the count, the presses and the gaps
# ---------------------------------------------------------------------------


def _cases():
    for steps in (2, 3, 4):
        for off in (False, True):
            length = steps + 1 if off else steps
            for start in range(length):
                for target in range(length):
                    yield steps, off, start, target


@pytest.mark.parametrize(("steps", "off", "start", "target"), list(_cases()))
async def test_every_start_and_target(no_wait, steps, off, start, target):
    fan = await _fan(no_wait, _device(steps=steps, off=off))
    fan.at(start)
    speed = target if off else target + 1
    percentage = _pct(speed, steps) if speed else 0
    await fan.entity.async_set_percentage(percentage)

    length = steps + 1 if off else steps
    presses = (target - start) % length
    assert fan.sent == [CYCLE] * presses
    # A gap between separate presses, none before the first.
    assert len(fan.gaps) == max(0, presses - 1)
    assert all(g == pytest.approx(SPEED_CYCLE_PRESS_GAP_S, abs=0.05) for g in fan.gaps)
    assert fan.entity._cycle_pos == target
    if speed:
        assert fan.entity.is_on is True
        assert fan.entity.percentage == percentage
    else:
        assert fan.entity.is_on is False


def test_cycle_presses_and_step():
    assert cycle_presses(0, 2, 3) == 2
    assert cycle_presses(2, 0, 3) == 1
    assert cycle_presses(1, 1, 3) == 0
    assert cycle_presses(3, 1, 4) == 2
    assert cycle_step(2, 3) == 0
    assert cycle_step(3, 4) == 0
    assert cycle_step(0, 4) == 1


async def test_zero_without_off_turns_the_fan_off_with_its_power_key(no_wait):
    fan = await _fan(no_wait)
    fan.at(2)
    await fan.entity.async_set_percentage(0)
    assert fan.sent == [POWER]
    assert fan.entity.is_on is False


async def test_the_believed_speed_is_written_before_the_presses(no_wait):
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    shown = []

    async def _send(device_id, command_id, **kwargs):
        shown.append(fan.entity.percentage)
        fan.sent.append(command_id)

    fan.manager.async_send_command = AsyncMock(side_effect=_send)
    await fan.entity.async_set_percentage(100)
    assert shown == [100, 100, 100]


async def test_a_failed_press_stops_the_burst_where_it_got(no_wait):
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    calls = []

    async def _send(device_id, command_id, **kwargs):
        calls.append(command_id)
        if len(calls) == 2:
            raise RuntimeError("emitter offline")

    fan.manager.async_send_command = AsyncMock(side_effect=_send)
    with pytest.raises(RuntimeError):
        await fan.entity.async_set_percentage(100)
    assert len(calls) == 2
    assert fan.entity._cycle_pos == 1
    assert fan.entity.percentage == _pct(2, 4)


async def test_waking_without_off_presses_power_then_the_cycle(no_wait):
    fan = await _fan(no_wait, _device(steps=3))
    fan.at(0, is_on=False)
    await fan.entity.async_set_percentage(100)
    assert fan.sent == [POWER, CYCLE, CYCLE]
    assert len(fan.gaps) == 2
    assert fan.entity.is_on is True
    assert fan.entity.percentage == 100


async def test_a_failed_wake_leaves_the_fan_off(no_wait):
    fan = await _fan(no_wait, _device(steps=3))
    fan.at(0, is_on=False)
    fan.manager.async_send_command = AsyncMock(side_effect=RuntimeError("no"))
    with pytest.raises(RuntimeError):
        await fan.entity.async_set_percentage(100)
    assert fan.entity.is_on is False
    assert fan.entity._cycle_pos == 0


# ---------------------------------------------------------------------------
# One burst at a time
# ---------------------------------------------------------------------------


async def _start_burst(fan: _Fan, percentage: int) -> asyncio.Task:
    fan.gate = asyncio.Event()
    task = asyncio.create_task(fan.entity.async_set_percentage(percentage))
    for _ in range(5):
        await REAL_SLEEP(0)
    return task


async def test_a_new_target_mid_burst_replaces_the_pending_one(no_wait):
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    first = await _start_burst(fan, 100)  # speed 4: three presses
    assert fan.sent == [CYCLE]  # the first press, then waiting the gap
    second = asyncio.create_task(fan.entity.async_set_percentage(50))  # speed 2
    for _ in range(5):
        await REAL_SLEEP(0)
    assert fan.entity.percentage == 50  # shown at once
    fan.gate.set()
    await asyncio.gather(first, second)
    assert fan.sent == [CYCLE]  # already at speed 2: nothing more
    assert fan.entity._cycle_pos == 1
    assert fan.entity.percentage == 50


async def test_a_redirect_behind_the_count_goes_round(no_wait):
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    first = await _start_burst(fan, 75)  # speed 3: two presses
    second = asyncio.create_task(fan.entity.async_set_percentage(25))  # speed 1
    for _ in range(5):
        await REAL_SLEEP(0)
    fan.gate.set()
    await asyncio.gather(first, second)
    # One press to speed 2, then round to speed 1: three more. The
    # second call queued no burst of its own.
    assert fan.sent == [CYCLE] * 4
    assert fan.entity._cycle_pos == 0
    assert fan.entity.percentage == 25


async def test_two_calls_never_press_at_once(no_wait):
    """Real sends take time. Without the lock, a second call would press
    while the first one's press is still going out, and both would count
    from the same position: the fan would overshoot."""
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    in_flight = 0
    most = 0

    async def _send(device_id, command_id, **kwargs):
        nonlocal in_flight, most
        in_flight += 1
        most = max(most, in_flight)
        for _ in range(3):
            await REAL_SLEEP(0)
        fan.sent.append(command_id)
        in_flight -= 1

    fan.manager.async_send_command = AsyncMock(side_effect=_send)
    await asyncio.gather(
        fan.entity.async_set_percentage(75),
        fan.entity.async_set_percentage(100),
    )
    assert most == 1
    assert fan.sent == [CYCLE] * 3
    assert fan.entity._cycle_pos == 3
    assert fan.entity.percentage == 100


async def test_turning_off_mid_burst_stops_it(no_wait):
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    first = await _start_burst(fan, 100)
    off = asyncio.create_task(fan.entity.async_turn_off())
    for _ in range(5):
        await REAL_SLEEP(0)
    fan.gate.set()
    await asyncio.gather(first, off)
    assert fan.sent == [CYCLE, POWER]
    assert fan.entity.is_on is False
    assert fan.entity._cycle_pos == 1  # resume: kept where it got


# ---------------------------------------------------------------------------
# Turn-on landing and re-zero
# ---------------------------------------------------------------------------


async def test_resume_keeps_the_speed_across_off_and_on(no_wait):
    fan = await _fan(no_wait, _device(steps=3, turn_on="resume"))
    fan.at(2)
    await fan.entity.async_turn_off()
    assert fan.entity._cycle_pos == 2
    await fan.entity.async_turn_on()
    assert fan.sent == [POWER, POWER]
    assert fan.entity.is_on is True
    assert fan.entity.percentage == 100


async def test_speed_1_lands_on_speed_1_after_off(no_wait):
    fan = await _fan(no_wait, _device(steps=3, turn_on="speed_1"))
    fan.at(2)
    await fan.entity.async_turn_off()
    assert fan.entity._cycle_pos == 0
    await fan.entity.async_turn_on()
    assert fan.entity.percentage == _pct(1, 3)
    await fan.entity.async_set_percentage(100)
    assert fan.sent == [POWER, POWER, CYCLE, CYCLE]


async def test_a_sensor_off_re_zeroes_the_count(no_wait):
    fan = await _fan(no_wait, _device(steps=3, turn_on="speed_1"))
    fan.at(2)
    fan.verdict("off")
    assert fan.entity.is_on is False
    assert fan.entity._cycle_pos == 0
    fan.verdict("on")
    assert fan.entity.percentage == _pct(1, 3)


async def test_with_off_in_the_cycle_off_is_position_zero(no_wait):
    mapping = {"speed_cycle": "Speed Cycle"}
    fan = await _fan(no_wait, _device(mapping=mapping, steps=3, off=True))
    fan.at(2)
    await fan.entity.async_turn_off()  # no power key: round to off
    assert fan.sent == [CYCLE, CYCLE]
    assert fan.entity.is_on is False
    await fan.entity.async_turn_on()  # one press: speed 1
    assert fan.sent == [CYCLE] * 3
    assert fan.entity.percentage == _pct(1, 3)


async def test_with_off_in_the_cycle_the_power_key_lands_on_speed_1(no_wait):
    fan = await _fan(no_wait, _device(steps=3, off=True))
    fan.at(3)
    await fan.entity.async_turn_off()
    assert fan.sent == [POWER]
    assert fan.entity._cycle_pos == 0
    await fan.entity.async_turn_on()
    assert fan.sent == [POWER, POWER]
    assert fan.entity._cycle_pos == 1
    assert fan.entity.percentage == _pct(1, 3)


async def test_without_a_power_key_the_cycle_button_wakes_the_fan(no_wait):
    mapping = {"speed_cycle": "Speed Cycle"}
    fan = await _fan(no_wait, _device(mapping=mapping, steps=3))
    fan.at(1, is_on=False)
    await fan.entity.async_turn_on()
    assert fan.sent == [CYCLE]
    assert fan.entity._cycle_pos == 1  # woke on its choice, no step
    assert fan.entity.is_on is True


async def test_turn_on_with_a_speed(no_wait):
    fan = await _fan(no_wait, _device(steps=3, turn_on="speed_1"))
    fan.at(0, is_on=False)
    await fan.entity.async_turn_on(percentage=_pct(2, 3))
    assert fan.sent == [POWER, CYCLE]
    assert fan.entity.percentage == _pct(2, 3)


async def test_turn_on_while_on_presses_nothing(no_wait):
    fan = await _fan(no_wait)
    fan.at(1)
    await fan.entity.async_turn_on()
    assert fan.sent == []


# ---------------------------------------------------------------------------
# Presses sent from anywhere else
# ---------------------------------------------------------------------------


async def test_a_cycle_press_moves_the_count_one_step(no_wait):
    fan = await _fan(no_wait)
    fan.at(0)
    fan.send("Speed Cycle")
    assert fan.entity._cycle_pos == 1
    assert fan.entity.percentage == _pct(2, 3)
    assert fan.writes == 1


async def test_a_cycle_press_wraps_to_the_first_speed(no_wait):
    fan = await _fan(no_wait)
    fan.at(2)
    fan.send("Speed Cycle")
    assert fan.entity._cycle_pos == 0
    assert fan.entity.percentage == _pct(1, 3)
    assert fan.entity.is_on is True


async def test_with_off_a_cycle_press_wraps_to_off_and_back_on(no_wait):
    fan = await _fan(no_wait, _device(steps=3, off=True))
    fan.at(3)
    fan.send("Speed Cycle")
    assert fan.entity._cycle_pos == 0
    assert fan.entity.is_on is False
    fan.send("Speed Cycle")
    assert fan.entity._cycle_pos == 1
    assert fan.entity.is_on is True
    assert fan.entity.percentage == _pct(1, 3)


@pytest.mark.parametrize(("turn_on", "landing"), [("resume", 2), ("speed_1", 0)])
async def test_from_off_without_off_a_press_wakes_on_the_choice(
    no_wait, turn_on, landing
):
    fan = await _fan(no_wait, _device(steps=3, turn_on=turn_on))
    fan.at(2)
    await fan.entity.async_turn_off()
    fan.send("Speed Cycle")
    assert fan.entity.is_on is True
    assert fan.entity._cycle_pos == landing


async def test_the_entitys_own_press_is_not_counted_twice(no_wait):
    fan = await _fan(no_wait)
    fan.at(0)
    fan.send("Speed Cycle", origin=ORIGIN_ENTITY)
    assert fan.entity._cycle_pos == 0
    assert fan.writes == 0


async def test_without_a_count_a_cycle_press_moves_nothing(no_wait):
    fan = await _fan(no_wait, _device(steps=None))
    fan.entity._is_on = True
    fan.send("Speed Cycle")
    assert fan.entity._cycle_pos == 0
    assert fan.writes == 0


async def test_a_press_mid_burst_is_counted_and_the_burst_adjusts(no_wait):
    fan = await _fan(no_wait, _device(steps=4))
    fan.at(0)
    burst = await _start_burst(fan, 100)  # three presses wanted
    fan.send("Speed Cycle")  # the handset, pinned
    fan.gate.set()
    await burst
    assert fan.sent == [CYCLE, CYCLE]
    assert fan.entity._cycle_pos == 3


async def test_a_pinned_retransmit_steps_the_fan(fake_hass, no_wait):
    """A handset press on a pinned Remote: the trigger fires, the
    retransmit goes through the real device manager's choke point, and
    the fan's count moves one step."""
    from custom_components.hair.entity_factory import EntityFactory
    from custom_components.hair.models import IRTrigger, TriggerRemote
    from custom_components.hair.pin_bindings import rederive_remote
    from custom_components.hair.storage import HAIRStore
    from custom_components.hair.trigger_manager import TriggerManager

    from .test_device_sent import _FakeStore, _landing_manager

    tasks: list = []
    fake_hass.async_create_task = MagicMock(
        side_effect=lambda coro: tasks.append(asyncio.ensure_future(coro)) or tasks[-1]
    )
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    pronto = "0000 006D 0002 0000 0020 0020 0040 0040"
    device = IRDevice(
        id=DEVICE_ID, name="Bedroom Fan", device_type=DeviceType.FAN,
        emitter_entity_ids=["infrared.e"],
        commands=[IRCommand(id=CYCLE, name="Speed Cycle", protocol="PRONTO",
                            code=pronto, decoded_fingerprint="NEC:0x1:0x9")],
        entity_config=EntityConfig(
            command_mapping={"speed_cycle": "Speed Cycle"}, fan_speed_steps=3,
        ),
    )
    store.add_device(device)
    remote = TriggerRemote(id="rem1", name="Fan Handset", pinned_device_ids=[DEVICE_ID])
    store.add_trigger_remote(remote)
    store.add_trigger(IRTrigger(
        id="trg1", name="Speed Cycle", trigger_remote_id="rem1",
        signal_fingerprint="fp-cycle", decoded_fingerprint="NEC:0x1:0x9",
    ))
    rederive_remote(store, remote)
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(),
    ):
        manager = DeviceManager(fake_hass, store, EntityFactory(fake_hass), "entry-1")
    fan = await _Fan(device, manager).add()
    fan.at(2)
    tm = TriggerManager(fake_hass, store, manager)

    def _dispatch(hass, signal, payload):
        if signal == SIGNAL_DEVICE_SENT:
            fan.handlers[SIGNAL_DEVICE_SENT](payload)

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=_dispatch,
    ):
        fired = tm.on_signal_captured(
            "fp-cycle", None, None, decoded_fingerprint="NEC:0x1:0x9"
        )
        while tasks:
            batch, tasks[:] = list(tasks), []
            await asyncio.gather(*batch)

    assert fired == ["trg1"]
    assert fan.entity._cycle_pos == 0  # wrapped from speed 3 to speed 1
    assert fan.entity.percentage == _pct(1, 3)


# ---------------------------------------------------------------------------
# Restore, and settings changing under a live entity
# ---------------------------------------------------------------------------


def _last(state: str, percentage=None):
    attributes = {} if percentage is None else {"percentage": percentage}
    return SimpleNamespace(state=state, attributes=attributes)


@pytest.mark.parametrize(
    ("device", "last", "position"),
    [
        (_device(steps=3), _last("on", 66), 1),
        (_device(steps=3), _last("on", 100), 2),
        (_device(steps=3), _last("off", 100), 2),
        (_device(steps=3, turn_on="speed_1"), _last("off", 100), 0),
        (_device(steps=3, off=True), _last("on", 66), 2),
        (_device(steps=3, off=True), _last("off", 100), 0),
        (_device(steps=3), _last("on"), 0),
        (_device(steps=3), None, 0),
    ],
)
async def test_restore_puts_the_count_back(no_wait, device, last, position):
    fan = await _fan(no_wait, device, last_state=last)
    assert fan.entity._cycle_pos == position


async def test_after_restore_the_presses_count_from_the_restored_speed(no_wait):
    fan = await _fan(no_wait, _device(steps=3), last_state=_last("on", 100))
    await fan.entity.async_set_percentage(_pct(2, 3))
    assert fan.sent == [CYCLE, CYCLE]


async def test_new_settings_re_read_the_count(no_wait):
    fan = await _fan(no_wait, _device(steps=None))
    fan.entity._is_on = True
    fan.entity._percentage = 100
    fan.entity.update_device(_device(steps=4))
    assert fan.entity._cycle_pos == 3
    # A save that changes nothing about the cycle leaves the count be.
    fan.entity._cycle_pos = 1
    fan.entity.update_device(_device(steps=4))
    assert fan.entity._cycle_pos == 1
