"""A matrix AC whose file has its own "on" code wakes with it (GH #323).

Some units ignore a state frame while they are off: a SmartIR file for
one carries ``on`` and ``off`` beside its states, and SmartIR sends
``on``, waits, then the state. HAIR sent the state alone, so from off
the unit never turned on.

With the device's setting (on unless unticked, stored only when off):
from off, a mode, a temperature with a mode in the same call, or a
starred state sends ``on``, waits ``TOGGLE_POWER_ON_GAP_S``, then the
cell. From on, the cell alone. Off sends ``off`` alone. A file with no
``on`` behaves as before, and so does a one-Power-button device, whose
own path already sends its power code first.

The lattice is synthetic, shaped like the reporter's: two modes, ``on``
and ``off``. None of his codes is used.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import (
    TOGGLE_POWER_ON_GAP_S,
    CommandSource,
    DeviceType,
)
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.power_monitor import expected_power_state
from custom_components.hair.send_signal import ORIGIN_ENTITY, DeviceSent
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

ON = "0000 006D 0002 0000 0010 0020 0010 0400"
OFF = "0000 006D 0002 0000 0010 0030 0010 0400"


def _cell_code(mode: str, temp: int) -> str:
    return f"0000 006D 0002 0000 00{temp:02X} 00{len(mode):02X} 0010 0400"


def _lattice(*, with_on: bool = True) -> ClimateMatrix:
    cells = [
        ClimateCell(mode=mode, fan="auto", temp=float(temp),
                    pronto=_cell_code(mode, temp))
        for mode in ("cool", "heat")
        for temp in (18, 22, 26)
    ]
    return ClimateMatrix(
        min_temp=18.0, max_temp=26.0, precision=1.0,
        modes=["cool", "heat"], fan_modes=["auto"], swing_modes=[],
        off=OFF, on=ON if with_on else None, cells=cells,
    )


def _device(*, wake: bool | None = None, toggles: bool = False) -> IRDevice:
    config = EntityConfig(platform="climate")
    if wake is not None:
        config.wake_with_on = wake
    return IRDevice(
        id="dev-1", name="Fujitsu", device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"], climate_matrix=True,
        power_toggles=toggles, entity_config=config,
    )


async def _entity(
    *, wake: bool | None = None, toggles: bool = False, with_on: bool = True,
    on: HVACMode | None = None, commands: list[IRCommand] | None = None,
):
    matrix = _lattice(with_on=with_on)
    log: list[tuple] = []

    async def _send(device_id, name, pronto, send_count=1, **kw):
        log.append(("send", pronto, kw.get("power")))

    async def _send_command(device_id, command_id, **kw):
        log.append(("command", command_id))

    device = _device(wake=wake, toggles=toggles)
    for command in commands or []:
        device.commands.append(command)
    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock(side_effect=_send)
    mgr.async_send_command = AsyncMock(side_effect=_send_command)
    mgr.async_get_matrix = AsyncMock(return_value=matrix)
    entity = HAIRClimateEntity(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.hass.config.units.temperature_unit = "°C"
    entity.async_get_last_state = AsyncMock(return_value=None)
    entity.async_get_last_extra_data = AsyncMock(return_value=None)
    await entity.async_added_to_hass()
    entity._fan_mode, entity._target_temperature = "auto", 22.0
    if on is not None:
        entity._hvac_mode = on
    return entity, log


@pytest.fixture
def gap():
    """asyncio.sleep in climate, recorded into the same log as the sends."""
    holder: dict = {}

    async def _sleep(seconds):
        holder["log"].append(("sleep", seconds))

    with patch("custom_components.hair.climate.asyncio.sleep", new=_sleep):
        yield holder


class TestFromOff:
    @pytest.mark.asyncio
    async def test_a_mode_sends_on_then_the_cell_after_the_gap(self, gap):
        entity, log = await _entity()
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert log == [
            ("send", ON, "on"),
            ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("send", _cell_code("cool", 22), None),
        ]
        assert entity.hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_a_temperature_with_a_mode_wakes_it_too(self, gap):
        entity, log = await _entity()
        gap["log"] = log
        await entity.async_set_temperature(temperature=26, hvac_mode=HVACMode.HEAT)
        assert log == [
            ("send", ON, "on"),
            ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("send", _cell_code("heat", 26), None),
        ]

    @pytest.mark.asyncio
    async def test_a_bare_temperature_still_waits_for_the_mode(self, gap):
        entity, log = await _entity()
        gap["log"] = log
        await entity.async_set_temperature(temperature=26)
        await entity.async_set_fan_mode("auto")
        assert log == []
        assert entity._target_temperature == 26.0

    @pytest.mark.asyncio
    async def test_a_starred_state_wakes_it_first(self, gap):
        star = IRCommand(
            id="c-heat", name="Heat 26", source=CommandSource.MATRIX,
            sent_state={"mode": "heat", "fan": "auto", "temp": 26.0},
        )
        entity, log = await _entity(commands=[star])
        entity._device.entity_config.starred = ["Heat 26"]
        gap["log"] = log
        await entity.async_set_preset_mode("Heat 26")
        assert log == [
            ("send", ON, "on"),
            ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("command", "c-heat"),
        ]


    @pytest.mark.asyncio
    async def test_a_mode_the_file_lacks_sends_nothing_not_a_bare_on(self, gap):
        entity, log = await _entity()
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.DRY)
        assert log == []


class TestFromOn:
    @pytest.mark.asyncio
    async def test_a_mode_sends_the_cell_alone(self, gap):
        entity, log = await _entity(on=HVACMode.COOL)
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert log == [("send", _cell_code("heat", 22), None)]

    @pytest.mark.asyncio
    async def test_off_sends_off_alone(self, gap):
        entity, log = await _entity(on=HVACMode.COOL)
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.OFF)
        assert log == [("send", OFF, "off")]


class TestWhenItDoesNotApply:
    @pytest.mark.asyncio
    async def test_unticked_sends_the_cell_alone(self, gap):
        entity, log = await _entity(wake=False)
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert log == [("send", _cell_code("cool", 22), None)]

    @pytest.mark.asyncio
    async def test_a_file_with_no_on_code_behaves_as_before(self, gap):
        entity, log = await _entity(with_on=False)
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert log == [("send", _cell_code("cool", 22), None)]

    @pytest.mark.asyncio
    async def test_a_one_power_button_device_is_unchanged(self, gap):
        """Its own path sends its power code first; nothing doubles it."""
        entity, log = await _entity(toggles=True)
        gap["log"] = log
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert log == [
            ("send", ON, "on"),
            ("sleep", TOGGLE_POWER_ON_GAP_S),
            ("send", _cell_code("cool", 22), None),
        ]
        assert not entity._wake_with_on

    @pytest.mark.asyncio
    async def test_turn_on_still_sends_on_alone(self, gap):
        entity, log = await _entity()
        gap["log"] = log
        await entity.async_turn_on()
        assert log == [("send", ON, "on")]


class TestTheSetting:
    def test_absent_reads_as_ticked_and_ticked_is_not_stored(self):
        assert EntityConfig.from_dict({}).wake_with_on is True
        assert "wake_with_on" not in EntityConfig().to_dict()

    def test_unticked_is_stored_and_read_back(self):
        config = EntityConfig(wake_with_on=False)
        stored = config.to_dict()
        assert stored["wake_with_on"] is False
        assert EntityConfig.from_dict(stored).wake_with_on is False


def test_the_power_monitor_reads_both_frames_as_on():
    """One window in effect: the second send replaces the first's, and
    both expect the unit on."""
    device = _device()
    first = DeviceSent(device_id="dev-1", command_id=None, command_name="On",
                       matrix_cell=None, power="on", origin=ORIGIN_ENTITY)
    second = DeviceSent(device_id="dev-1", command_id=None, command_name="Cool",
                        matrix_cell={"mode": "cool"}, power=None,
                        origin=ORIGIN_ENTITY)
    assert expected_power_state(device, first) == "on"
    assert expected_power_state(device, second) == "on"
