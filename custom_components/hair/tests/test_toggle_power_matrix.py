"""Toggle power, piece 2: matrix climate and pinned toggles (GH #183).

Some air conditioners have one Power button: the code turns the unit on
when it is off and off when it is on. orthobots' file for such a unit
stores that code as its ``off``, and the code is a full state frame (cool
/ fan auto / 16) with the power bit set, while every other cell has the
bit clear. Sending ``off`` to a unit that is already off turned it on.

With the device's "power button toggles" setting:

- turn off sends the power code only while HAIR believes the unit is on;
- turn on sends the power code, waits ``TOGGLE_POWER_ON_GAP_S``, then the
  wanted cell, so the unit ends in the cell's state;
- a mode from off is a turn on; settings while off are stored, not sent;
- a power code from any other door flips the card, never sets it.

A pinned remote that hears a power toggle relays it, as every pin did,
unless the pin follows: then the device's card flips and nothing is
sent. A new pin on a toggle-power device follows; an existing one keeps
relaying.

The frames are written here from the DAIKIN64 layout (header 0x16, mode
and fan nibbles, a clock, BCD temperature, power bit, nibble checksum),
with invented clock values. None of orthobots' bytes is used.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import TOGGLE_POWER_ON_GAP_S, DeviceType
from custom_components.hair.models import (
    EntityConfig,
    IRCommand,
    IRDevice,
    TriggerRemote,
)
from custom_components.hair.pin_retransmit import (
    CELL_TARGET_PREFIX,
    FOLLOW_TARGET_PREFIX,
)
from custom_components.hair.power_monitor import expected_power_state
from custom_components.hair.send_follow import (
    command_toggles_power,
    device_toggles_power,
)
from custom_components.hair.send_signal import (
    ORIGIN_ENTITY,
    ORIGIN_MANAGER,
    DeviceSent,
)
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# ---------------------------------------------------------------------------
# A DAIKIN64-shaped lattice
# ---------------------------------------------------------------------------

_MODE = {"dry": 0x1, "cool": 0x2, "fan_only": 0x4, "heat": 0x8}
_FAN = {"auto": 0x1, "high": 0x2, "low": 0x8}
# Pronto 0x006D: one unit is 109 carrier periods' worth of 0.241246 us.
_UNIT_US = 109 * 0.241246


def _bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def _daikin64(mode: str, fan: str, temp: int, *, power: bool, clock: int) -> str:
    """One frame: eight bytes, least significant bit first."""
    data = [
        0x16,
        _MODE[mode] | (_FAN[fan] << 4),
        _bcd(clock % 60),
        _bcd((clock // 60) % 24),
        0x00,
        0x00,
        _bcd(temp),
        0x08 if power else 0x00,
    ]
    nibbles = [n for byte in data for n in (byte & 0xF, byte >> 4)][:15]
    data[7] |= (sum(nibbles) & 0xF) << 4
    timings = [9800, 9800, 9800, 9800, 4600, 2500]
    for byte in data:
        for bit in range(8):
            timings += [350, 954 if byte >> bit & 1 else 382]
    timings += [350, 20000]
    units = [max(1, round(t / _UNIT_US)) for t in timings]
    words = ["0000", "006D", f"{len(units) // 2:04X}", "0000"]
    return " ".join(words + [f"{u:04X}" for u in units])


def _lattice() -> ClimateMatrix:
    cells = []
    clock = 17 * 60 + 3
    for mode in ("cool", "dry"):
        for fan in ("auto", "low"):
            for temp in (18, 22, 26):
                clock += 7  # the handset writes the time into every press
                cells.append(ClimateCell(
                    mode=mode, fan=fan, temp=float(temp),
                    pronto=_daikin64(mode, fan, temp, power=False, clock=clock),
                ))
    return ClimateMatrix(
        min_temp=18.0, max_temp=26.0, precision=1.0,
        modes=["cool", "dry"], fan_modes=["auto", "low"], swing_modes=[],
        # The power code: a full cool / auto / 16 frame with the bit set.
        off=_daikin64("cool", "auto", 16, power=True, clock=17 * 60),
        on=None, cells=cells,
    )


POWER = _lattice().off


def _pronto(matrix: ClimateMatrix, mode: str, fan: str, temp: float) -> str:
    for cell in matrix.cells:
        if (cell.mode, cell.fan, cell.temp) == (mode, fan, temp):
            return cell.pronto
    raise KeyError((mode, fan, temp))


def _bytes(pronto: str) -> list[int]:
    """The eight bytes back out of a frame: a long space is a one."""
    units = [int(word, 16) for word in pronto.split()[4:]]
    spaces = units[7:7 + 2 * 64:2]  # past the three leader pairs
    bits = [1 if space * _UNIT_US > 700 else 0 for space in spaces]
    return [sum(bits[8 * i + b] << b for b in range(8)) for i in range(8)]


def test_the_fixture_has_the_shape_of_the_file():
    """Every frame carries header 0x16 and a checksum that verifies; the
    power bit is set on the power code and on no cell."""
    matrix = _lattice()
    for pronto in [matrix.off, *(cell.pronto for cell in matrix.cells)]:
        data = _bytes(pronto)
        assert data[0] == 0x16
        nibbles = [n for byte in data for n in (byte & 0xF, byte >> 4)]
        assert sum(nibbles[:15]) & 0xF == nibbles[15]
    assert _bytes(matrix.off)[7] & 0x08
    assert not any(_bytes(cell.pronto)[7] & 0x08 for cell in matrix.cells)
    assert len({cell.pronto for cell in matrix.cells}) == len(matrix.cells)


# ---------------------------------------------------------------------------
# The entity
# ---------------------------------------------------------------------------


def _device(*, toggles: bool = True) -> IRDevice:
    return IRDevice(
        id="dev-1", name="Daikin", device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"], climate_matrix=True,
        power_toggles=toggles,
    )


async def _entity(*, toggles: bool = True, on: HVACMode | None = None):
    matrix = _lattice()
    log: list[tuple] = []

    async def _send(device_id, name, pronto, send_count=1, **kw):
        log.append(("send", pronto, kw.get("power"), kw.get("cell")))

    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock(side_effect=_send)
    mgr.async_get_matrix = AsyncMock(return_value=matrix)
    entity = HAIRClimateEntity(_device(toggles=toggles), mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.hass.config.units.temperature_unit = "°C"
    entity.async_get_last_state = AsyncMock(return_value=None)
    entity.async_get_last_extra_data = AsyncMock(return_value=None)
    await entity.async_added_to_hass()
    entity._fan_mode, entity._target_temperature = "auto", 22.0
    if on is not None:
        entity._hvac_mode = on
    return entity, matrix, log


@pytest.fixture
def gap():
    """asyncio.sleep in climate, recorded into the same log as the sends."""
    holder: dict = {}

    async def _sleep(seconds):
        holder["log"].append(("sleep", seconds))

    with patch("custom_components.hair.climate.asyncio.sleep", new=_sleep):
        yield holder


class TestTurningOff:
    @pytest.mark.asyncio
    async def test_off_when_already_off_sends_nothing(self):
        entity, _, log = await _entity()
        assert entity.hvac_mode == HVACMode.OFF
        await entity.async_turn_off()
        await entity.async_set_hvac_mode(HVACMode.OFF)
        assert log == []
        assert entity.hvac_mode == HVACMode.OFF

    @pytest.mark.asyncio
    async def test_off_when_on_sends_the_power_code_once(self):
        entity, _, log = await _entity(on=HVACMode.COOL)
        await entity.async_turn_off()
        assert log == [("send", POWER, "off", None)]
        assert entity.hvac_mode == HVACMode.OFF
        assert entity._last_active_hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_a_temperature_call_with_off_sends_nothing_to_an_off_unit(self):
        entity, _, log = await _entity()
        await entity.async_set_temperature(temperature=24, hvac_mode=HVACMode.OFF)
        assert log == []
        assert entity._target_temperature == 24.0


class TestTurningOn:
    @pytest.mark.asyncio
    async def test_on_from_off_sends_power_then_the_cell_after_the_gap(self, gap):
        entity, matrix, log = await _entity()
        gap["log"] = log
        entity._last_active_hvac_mode = HVACMode.DRY

        await entity.async_turn_on()

        assert log == [
            ("send", POWER, "on", None),
            ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("send", _pronto(matrix, "dry", "auto", 22.0), None,
             {"mode": "dry", "fan": "auto", "swing": None, "temp": 22.0}),
        ]
        assert TOGGLE_POWER_ON_GAP_S == 0.8
        assert entity.hvac_mode == HVACMode.DRY

    @pytest.mark.asyncio
    async def test_a_mode_from_off_is_a_turn_on(self, gap):
        entity, matrix, log = await _entity()
        gap["log"] = log

        await entity.async_set_hvac_mode(HVACMode.COOL)

        assert [entry[:2] for entry in log] == [
            ("send", POWER), ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("send", _pronto(matrix, "cool", "auto", 22.0)),
        ]
        assert entity.hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_a_temperature_call_with_a_mode_from_off_too(self, gap):
        entity, matrix, log = await _entity()
        gap["log"] = log

        await entity.async_set_temperature(temperature=26, hvac_mode=HVACMode.COOL)

        assert [entry[:2] for entry in log] == [
            ("send", POWER), ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("send", _pronto(matrix, "cool", "auto", 26.0)),
        ]

    @pytest.mark.asyncio
    async def test_on_while_on_sends_only_the_cell(self, gap):
        entity, matrix, log = await _entity(on=HVACMode.COOL)
        gap["log"] = log

        await entity.async_turn_on()
        await entity.async_set_hvac_mode(HVACMode.DRY)

        assert [entry[:2] for entry in log] == [
            ("send", _pronto(matrix, "cool", "auto", 22.0)),
            ("send", _pronto(matrix, "dry", "auto", 22.0)),
        ]


class TestWhileOff:
    @pytest.mark.asyncio
    async def test_a_setting_change_while_off_sends_nothing(self):
        entity, _, log = await _entity()
        await entity.async_set_fan_mode("low")
        await entity.async_set_temperature(temperature=26)
        assert log == []
        assert entity.hvac_mode == HVACMode.OFF
        assert (entity._wanted_fan, entity._target_temperature) == ("low", 26.0)

    @pytest.mark.asyncio
    async def test_and_the_next_on_goes_out_with_them(self, gap):
        entity, matrix, log = await _entity()
        gap["log"] = log
        await entity.async_set_fan_mode("low")
        await entity.async_set_temperature(temperature=26)
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert log[-1][1] == _pronto(matrix, "cool", "low", 26.0)


class TestFollowing:
    """A send from any other door, or a heard toggle a pin followed."""

    @staticmethod
    def _power(**kw) -> DeviceSent:
        return DeviceSent(device_id="dev-1", command_name="Off", power="off", **kw)

    @pytest.mark.asyncio
    async def test_a_heard_toggle_flips_off_to_on_and_back(self):
        entity, _, log = await _entity()
        entity._last_active_hvac_mode = HVACMode.DRY

        entity._handle_device_sent(self._power(heard=True))
        assert entity.hvac_mode == HVACMode.DRY

        entity._handle_device_sent(self._power(heard=True))
        assert entity.hvac_mode == HVACMode.OFF
        assert log == []

    @pytest.mark.asyncio
    async def test_a_power_code_named_on_flips_too(self):
        entity, _, _ = await _entity(on=HVACMode.COOL)
        entity._handle_device_sent(DeviceSent(
            device_id="dev-1", command_name="On", power="on",
        ))
        assert entity.hvac_mode == HVACMode.OFF

    @pytest.mark.asyncio
    async def test_a_cell_while_off_sets_the_settings_and_stays_off(self):
        entity, _, _ = await _entity()
        entity._handle_device_sent(DeviceSent(
            device_id="dev-1", command_name="dry / fan: low / 26",
            matrix_cell={"mode": "dry", "fan": "low", "swing": None, "temp": 26.0},
        ))
        assert entity.hvac_mode == HVACMode.OFF
        assert entity._last_active_hvac_mode == HVACMode.DRY
        assert (entity._fan_mode, entity._target_temperature) == ("low", 26.0)

    @pytest.mark.asyncio
    async def test_a_cell_while_on_moves_the_card_as_always(self):
        entity, _, _ = await _entity(on=HVACMode.COOL)
        entity._handle_device_sent(DeviceSent(
            device_id="dev-1", command_name="dry / fan: low / 26",
            matrix_cell={"mode": "dry", "fan": "low", "swing": None, "temp": 26.0},
        ))
        assert entity.hvac_mode == HVACMode.DRY


class TestWithoutTheSetting:
    @pytest.mark.asyncio
    async def test_off_while_off_still_sends_the_off_code(self):
        entity, _, log = await _entity(toggles=False)
        await entity.async_turn_off()
        assert log == [("send", POWER, "off", None)]

    @pytest.mark.asyncio
    async def test_on_sends_the_first_modes_cell_alone(self, gap):
        entity, matrix, log = await _entity(toggles=False)
        gap["log"] = log
        await entity.async_turn_on()
        assert [entry[:2] for entry in log] == [
            ("send", _pronto(matrix, "cool", "auto", 22.0)),
        ]

    @pytest.mark.asyncio
    async def test_a_followed_off_sets_off(self):
        entity, _, _ = await _entity(toggles=False)
        entity._handle_device_sent(DeviceSent(
            device_id="dev-1", command_name="Off", power="off",
        ))
        assert entity.hvac_mode == HVACMode.OFF
        entity._handle_device_sent(DeviceSent(
            device_id="dev-1", command_name="Off", power="off",
        ))
        assert entity.hvac_mode == HVACMode.OFF


class TestThePowerMonitor:
    def test_a_toggle_from_another_door_expects_nothing(self):
        device = _device()
        assert expected_power_state(device, DeviceSent(
            device_id="dev-1", power="off", origin=ORIGIN_MANAGER,
        )) is None

    def test_the_entitys_own_toggle_says_where_it_goes(self):
        device = _device()
        assert expected_power_state(device, DeviceSent(
            device_id="dev-1", power="on", origin=ORIGIN_ENTITY,
        )) == "on"

    def test_an_absolute_off_is_still_off(self):
        device = _device(toggles=False)
        assert expected_power_state(device, DeviceSent(
            device_id="dev-1", power="off", origin=ORIGIN_MANAGER,
        )) == "off"


class TestPresetClimateFollowsAToggle:
    """Owner ruling: flip, one rule everywhere (GH #183 note, call 4)."""

    @pytest.mark.asyncio
    async def test_a_followed_toggle_flips_both_ways(self):
        device = IRDevice(
            id="dev-flat", name="Den AC", device_type=DeviceType.AC,
            emitter_entity_ids=["infrared.e"],
            commands=[IRCommand(id="c-power", name="Power", code="P")],
            entity_config=EntityConfig(
                platform="climate", command_mapping={"power_toggle": "Power"},
            ),
        )
        entity = HAIRClimateEntity(device, MagicMock())
        entity.async_write_ha_state = MagicMock()
        entity.hass = MagicMock()
        sent = DeviceSent(device_id="dev-flat", command_id="c-power",
                          command_name="Power")

        entity._handle_device_sent(sent)
        assert entity.hvac_mode == HVACMode.AUTO
        entity._hvac_mode = HVACMode.COOL
        entity._handle_device_sent(sent)
        assert entity.hvac_mode == HVACMode.OFF
        entity._handle_device_sent(sent)
        assert entity.hvac_mode == HVACMode.COOL


# ---------------------------------------------------------------------------
# Pins: relay or follow
# ---------------------------------------------------------------------------


def _flat_device(mapping: dict[str, str]) -> IRDevice:
    return IRDevice(
        id="dev1", name="TV",
        commands=[
            IRCommand(id="cmd1", name="Power",
                      decoded_fingerprint="NEC:0x1:0x1"),
        ],
        entity_config=EntityConfig(platform="media_player",
                                   command_mapping=mapping),
    )


class TestWhichDevicesToggle:
    def test_a_flat_device_says_so_through_its_mapping(self):
        assert device_toggles_power(_flat_device({"power_toggle": "Power"}))
        assert device_toggles_power(
            _flat_device({"turn_on": "Power", "turn_off": "Power"})
        )
        assert not device_toggles_power(
            _flat_device({"turn_on": "On", "turn_off": "Off"})
        )
        assert command_toggles_power(_flat_device({"power_toggle": "Power"}), "cmd1")
        assert not command_toggles_power(_flat_device({"mute": "Power"}), "cmd1")

    def test_a_matrix_device_says_so_in_its_settings(self):
        assert device_toggles_power(_device(toggles=True))
        assert not device_toggles_power(_device(toggles=False))


class _Manager:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.followed: list[tuple[str, str]] = []

    async def async_send_command(self, device_id, command_id, heard_future=None,
                                 pinned=False):
        self.sent.append((device_id, command_id))

    async def async_follow_command(self, device_id, command_id):
        self.followed.append((device_id, command_id))


def _fire(fake_hass, mapping, *, follow: bool):
    from custom_components.hair.models import IRTrigger
    from custom_components.hair.pin_bindings import rederive_remote
    from custom_components.hair.storage import HAIRStore
    from custom_components.hair.trigger_manager import TriggerManager

    from .test_pin_retransmit import _TaskHass

    store = HAIRStore(fake_hass)
    store.add_device(_flat_device(mapping))
    remote = TriggerRemote(
        id="rem1", name="Handset", pinned_device_ids=["dev1"],
        follow_only_device_ids=["dev1"] if follow else [],
    )
    store.add_trigger_remote(remote)
    store.add_trigger(IRTrigger(
        id="trg1", name="Power", trigger_remote_id="rem1",
        signal_fingerprint="fp-power", decoded_fingerprint="NEC:0x1:0x1",
        min_hits=1,
    ))
    rederive_remote(store, remote)
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    manager = _Manager()
    tm = TriggerManager(hass, store, manager)
    tm.on_signal_captured("fp-power", None, None, decoded_fingerprint="NEC:0x1:0x1")
    return hass, manager


class TestAFlatPin:
    @pytest.mark.asyncio
    async def test_an_existing_pin_keeps_relaying_the_toggle(self, fake_hass):
        hass, manager = _fire(fake_hass, {"power_toggle": "Power"}, follow=False)
        await hass.drain()
        assert manager.sent == [("dev1", "cmd1")]
        assert manager.followed == []

    @pytest.mark.asyncio
    async def test_a_following_pin_follows_the_toggle_and_sends_nothing(
        self, fake_hass,
    ):
        hass, manager = _fire(fake_hass, {"power_toggle": "Power"}, follow=True)
        await hass.drain()
        assert manager.sent == []
        assert manager.followed == [("dev1", "cmd1")]

    @pytest.mark.asyncio
    async def test_a_following_pin_still_relays_any_other_button(self, fake_hass):
        hass, manager = _fire(fake_hass, {"mute": "Power"}, follow=True)
        await hass.drain()
        assert manager.sent == [("dev1", "cmd1")]
        assert manager.followed == []


class TestTheFollowIsAnnounced:
    @pytest.mark.asyncio
    async def test_as_the_send_it_replaces_with_heard_set(self):
        from custom_components.hair.device_manager import DeviceManager

        manager = DeviceManager(MagicMock(), MagicMock(), MagicMock(), "entry-1")
        device = _flat_device({"power_toggle": "Power"})
        manager._store.get_device = MagicMock(return_value=device)
        with patch(
            "custom_components.hair.device_manager.async_dispatcher_send"
        ) as dispatch:
            await manager.async_follow_command("dev1", "cmd1")
        sent = dispatch.call_args.args[2]
        assert (sent.device_id, sent.command_id, sent.heard) == (
            "dev1", "cmd1", True,
        )
        assert sent.origin == ORIGIN_MANAGER


# ---------------------------------------------------------------------------
# Pins on a matrix device: the listener's half
# ---------------------------------------------------------------------------


class _ListenerManager:
    def __init__(self, matrix):
        self.matrix = matrix
        self.sends: list = []
        self.follows: list[DeviceSent] = []

    async def async_get_matrix(self, device_id):
        return self.matrix

    async def async_send_matrix_cell(self, device_id, name, pronto, send_count=1,
                                     **kw):
        self.sends.append((device_id, name, pronto))

    def async_follow_heard(self, sent):
        self.follows.append(sent)

    def climate_state(self, device_id):
        return None


def _matrix_pair(*, follow: bool, toggles: bool = True):
    from custom_components.hair.matrix_listener import (
        MatrixListener,
        build_cell_index,
    )

    from .test_matrix_listener import _hass, _store_with

    remote_matrix = _lattice()
    device_matrix = _lattice()
    remote = TriggerRemote(
        id="r1", name="Daikin handset", climate_matrix=True,
        pinned_device_ids=["dev-1"],
        follow_only_device_ids=["dev-1"] if follow else [],
    )
    store = _store_with(remote)
    store.get_device = MagicMock(return_value=_device(toggles=toggles))
    hass = _hass(store)
    tasks: list = []
    hass.async_create_task = MagicMock(side_effect=tasks.append)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=(None, None))
    tm.dispatch_cell_retransmit = MagicMock(return_value=True)
    dm = _ListenerManager(device_matrix)
    listener = MatrixListener(hass, store, tm, dm)
    listener._matrix_cache["r1"] = remote_matrix
    listener._index_cache["r1"] = build_cell_index(remote_matrix)
    listener._index_cache["dev-1"] = build_cell_index(device_matrix)
    return listener, tm, dm, tasks, remote_matrix


async def _hear(listener, tasks, pronto):
    from .test_matrix_listener import _hear as hear

    await hear(listener, tasks, pronto)


class TestAMatrixPin:
    @pytest.mark.asyncio
    async def test_a_following_pin_follows_a_heard_power_toggle(self):
        listener, tm, dm, tasks, _ = _matrix_pair(follow=True)
        await _hear(listener, tasks, POWER)

        args, kwargs = tm.dispatch_cell_retransmit.call_args
        assert args[:3] == ("r1", "dev-1", "off")
        assert kwargs == {"follow": True}

        await listener.async_follow_pinned_cell("dev-1", "off")
        assert dm.sends == []
        assert [(s.power, s.heard) for s in dm.follows] == [("off", False)]

    @pytest.mark.asyncio
    async def test_an_existing_pin_relays_it(self):
        listener, tm, dm, tasks, _ = _matrix_pair(follow=False)
        await _hear(listener, tasks, POWER)

        assert tm.dispatch_cell_retransmit.call_args.kwargs == {}
        await listener.async_send_pinned_cell("dev-1", "off")
        assert [send[2] for send in dm.sends] == [POWER]

    @pytest.mark.asyncio
    async def test_a_settings_press_is_relayed_even_on_a_following_pin(self):
        listener, tm, _dm, tasks, remote_matrix = _matrix_pair(follow=True)
        pressed = _pronto(remote_matrix, "cool", "low", 26.0)
        await _hear(listener, tasks, pressed)

        assert tm.dispatch_cell_retransmit.call_args.kwargs == {}
        assert tm.dispatch_cell_retransmit.call_args.args[2] == "cool/low/26"

    @pytest.mark.asyncio
    async def test_a_device_without_the_setting_is_relayed(self):
        listener, tm, _dm, tasks, _ = _matrix_pair(follow=True, toggles=False)
        await _hear(listener, tasks, POWER)
        assert tm.dispatch_cell_retransmit.call_args.kwargs == {}


class TestTheDispatcherRoutes:
    @pytest.mark.asyncio
    async def test_a_follow_target_never_reaches_the_send(self):
        from custom_components.hair.trigger_manager import TriggerManager

        manager = MagicMock()
        manager.async_send_command = AsyncMock()
        manager.async_follow_command = AsyncMock()
        tm = TriggerManager(MagicMock(), MagicMock(), manager)
        listener = MagicMock()
        listener.async_send_pinned_cell = AsyncMock()
        listener.async_follow_pinned_cell = AsyncMock()
        tm.set_matrix_listener(listener)

        await tm._send_bound_command(
            "dev-1", FOLLOW_TARGET_PREFIX + CELL_TARGET_PREFIX + "off"
        )
        await tm._send_bound_command("dev1", FOLLOW_TARGET_PREFIX + "cmd1")

        listener.async_follow_pinned_cell.assert_awaited_once_with("dev-1", "off")
        manager.async_follow_command.assert_awaited_once_with("dev1", "cmd1")
        listener.async_send_pinned_cell.assert_not_awaited()
        manager.async_send_command.assert_not_awaited()


# ---------------------------------------------------------------------------
# Pinning, the relay choice, storage
# ---------------------------------------------------------------------------


def _ws(fake_hass, remote, device):
    from .test_websocket_api import _make_connection, _wire_triggers

    store = _wire_triggers(fake_hass)
    store.get_trigger_remote = MagicMock(return_value=remote)
    store.update_trigger_remote = MagicMock()
    store.get_device = MagicMock(return_value=device)
    return store, _make_connection()


class TestPinning:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("device", "follows"), [
        (_device(toggles=True), True),
        (_device(toggles=False), False),
        (_flat_device({"power_toggle": "Power"}), True),
        (_flat_device({"turn_on": "On", "turn_off": "Off"}), False),
    ])
    async def test_a_new_pin_follows_on_a_toggle_power_device(
        self, fake_hass, device, follows,
    ):
        from custom_components.hair.websocket_api import ws_pin_trigger_remote_device

        remote = TriggerRemote(id="tr1", name="Handset")
        _store, conn = _ws(fake_hass, remote, device)
        await ws_pin_trigger_remote_device(fake_hass, conn, {
            "id": 1, "type": "hair/trigger-remote/pin",
            "remote_id": "tr1", "device_id": device.id,
        })
        assert remote.pinned_device_ids == [device.id]
        assert (device.id in remote.follow_only_device_ids) is follows
        result = conn.send_result.call_args.args[1]
        assert result["follow_only_device_ids"] == remote.follow_only_device_ids

    @pytest.mark.asyncio
    async def test_pinning_again_leaves_an_existing_pin_relaying(self, fake_hass):
        from custom_components.hair.websocket_api import ws_pin_trigger_remote_device

        device = _device(toggles=True)
        remote = TriggerRemote(id="tr1", name="Handset",
                               pinned_device_ids=[device.id])
        _store, conn = _ws(fake_hass, remote, device)
        await ws_pin_trigger_remote_device(fake_hass, conn, {
            "id": 2, "type": "hair/trigger-remote/pin",
            "remote_id": "tr1", "device_id": device.id,
        })
        assert remote.follow_only_device_ids == []

    @pytest.mark.asyncio
    async def test_the_relay_choice_is_set_and_cleared(self, fake_hass):
        from custom_components.hair.websocket_api import ws_set_pin_relay

        remote = TriggerRemote(id="tr1", name="Handset",
                               pinned_device_ids=["dev-1"])
        store, conn = _ws(fake_hass, remote, _device())
        msg = {"id": 3, "type": "hair/trigger-remote/pin-relay",
               "remote_id": "tr1", "device_id": "dev-1"}
        await ws_set_pin_relay(fake_hass, conn, {**msg, "relay": False})
        assert remote.follow_only_device_ids == ["dev-1"]
        await ws_set_pin_relay(fake_hass, conn, {**msg, "relay": True})
        assert remote.follow_only_device_ids == []
        assert store.async_save.await_count == 2

    @pytest.mark.asyncio
    async def test_the_relay_choice_needs_a_pin(self, fake_hass):
        from custom_components.hair.websocket_api import ws_set_pin_relay

        remote = TriggerRemote(id="tr1", name="Handset")
        _store, conn = _ws(fake_hass, remote, _device())
        await ws_set_pin_relay(fake_hass, conn, {
            "id": 4, "type": "hair/trigger-remote/pin-relay",
            "remote_id": "tr1", "device_id": "dev-1", "relay": False,
        })
        assert conn.send_error.call_args.args[1] == "not_found"

    @pytest.mark.asyncio
    async def test_unpinning_drops_the_choice(self, fake_hass):
        from custom_components.hair.websocket_api import (
            ws_unpin_trigger_remote_device,
        )

        remote = TriggerRemote(id="tr1", name="Handset",
                               pinned_device_ids=["dev-1"],
                               follow_only_device_ids=["dev-1"])
        _store, conn = _ws(fake_hass, remote, _device())
        await ws_unpin_trigger_remote_device(fake_hass, conn, {
            "id": 5, "type": "hair/trigger-remote/unpin",
            "remote_id": "tr1", "device_id": "dev-1",
        })
        assert remote.follow_only_device_ids == []


class TestTheSetting:
    @pytest.mark.asyncio
    async def test_is_refused_on_a_device_without_a_matrix(self, fake_hass):
        from custom_components.hair.websocket_api import ws_update_device

        from .test_websocket_api import _make_connection

        device = _flat_device({"power_toggle": "Power"})
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_update_device = AsyncMock()
        fake_hass.data = {"hair": {"entry-1": {"device_manager": manager}}}
        conn = _make_connection()
        await ws_update_device(fake_hass, conn, {
            "id": 6, "type": "hair/device/update", "device_id": "dev1",
            "power_toggles": True,
        })
        assert conn.send_error.call_args.args[1] == "invalid_format"
        manager.async_update_device.assert_not_awaited()


class TestStorage:
    def test_the_device_setting_round_trips_and_is_absent_when_off(self):
        on = _device(toggles=True).to_dict()
        assert on["power_toggles"] is True
        assert IRDevice.from_dict(on).power_toggles is True
        off = _device(toggles=False).to_dict()
        assert "power_toggles" not in off
        assert IRDevice.from_dict(off).power_toggles is False

    def test_a_clone_keeps_the_setting(self):
        assert _device(toggles=True).clone("Copy").power_toggles is True

    def test_the_follow_list_round_trips_and_is_absent_when_empty(self):
        remote = TriggerRemote(id="r", pinned_device_ids=["d"],
                               follow_only_device_ids=["d"])
        data = remote.to_dict()
        assert TriggerRemote.from_dict(data).follow_only_device_ids == ["d"]
        assert "follow_only_device_ids" not in TriggerRemote(id="r").to_dict()
        assert TriggerRemote.from_dict(
            {"id": "r", "pinned_device_ids": ["d"]}
        ).follow_only_device_ids == []

    def test_a_follow_mark_without_its_pin_is_pruned_at_load(self, fake_hass):
        from custom_components.hair.storage import HAIRStore

        store = HAIRStore(fake_hass)
        store.add_device(_device())
        remote = TriggerRemote(id="r", pinned_device_ids=["dev-1"],
                               follow_only_device_ids=["dev-1", "gone"])
        store.add_trigger_remote(remote)
        assert store._prune_dangling_pins(remote) is True
        assert remote.follow_only_device_ids == ["dev-1"]
