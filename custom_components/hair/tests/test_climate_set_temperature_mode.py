"""climate.set_temperature with an hvac_mode in the same call.

Home Assistant checks the temperature's range and then hands the whole
call, ``hvac_mode`` included, to the entity's ``async_set_temperature``.
It never calls ``set_hvac_mode`` for a set_temperature, so the entity
has to apply the mode itself, together with the temperature.

- Matrix device: one send, the cell for the new mode and temperature.
  ``hvac_mode: off`` turns the unit off and keeps the temperature.
- Preset device: the mode command, then the temperature command.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.models import EntityConfig, IRDevice
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

from .test_entities import _cmd, _device, _manager, _patch_write_state


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "heat"],
        fan_modes=["auto"],
        off="P-OFF",
        on=None,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto="P-C-22"),
            ClimateCell(mode="cool", fan="auto", temp=26.0, pronto="P-C-26"),
            ClimateCell(mode="heat", fan="auto", temp=22.0, pronto="P-H-22"),
            ClimateCell(mode="heat", fan="auto", temp=26.0, pronto="P-H-26"),
        ],
    )


async def _matrix_entity():
    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=_matrix())
    device = IRDevice(
        id="dev-1", name="Bedroom AC", device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"], climate_matrix=True,
    )
    entity = HAIRClimateEntity(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    await entity.async_added_to_hass()
    return entity, mgr


def _sent_prontos(mgr) -> list[str]:
    return [c.args[2] for c in mgr.async_send_matrix_cell.await_args_list]


class TestMatrix:
    @pytest.mark.asyncio
    async def test_a_mode_in_the_call_sends_that_modes_cell(self):
        entity, mgr = await _matrix_entity()
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_temperature(temperature=26, hvac_mode=HVACMode.HEAT)
        assert _sent_prontos(mgr) == ["P-H-26"]
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.target_temperature == 26.0

    @pytest.mark.asyncio
    async def test_an_off_unit_turns_on_in_the_called_mode(self):
        entity, mgr = await _matrix_entity()
        assert entity.hvac_mode == HVACMode.OFF
        await entity.async_set_temperature(temperature=22, hvac_mode=HVACMode.COOL)
        assert _sent_prontos(mgr) == ["P-C-22"]
        assert entity.hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_the_mode_as_a_plain_string_is_read_too(self):
        entity, mgr = await _matrix_entity()
        await entity.async_set_temperature(temperature=22, hvac_mode="heat")
        assert _sent_prontos(mgr) == ["P-H-22"]
        assert entity.hvac_mode == HVACMode.HEAT

    @pytest.mark.asyncio
    async def test_off_with_a_temperature_turns_off_and_keeps_it(self):
        entity, mgr = await _matrix_entity()
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_temperature(temperature=26, hvac_mode=HVACMode.OFF)
        assert _sent_prontos(mgr) == ["P-OFF"]
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.target_temperature == 26.0
        # The kept temperature rides out on the next mode.
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert _sent_prontos(mgr)[-1] == "P-H-26"

    @pytest.mark.asyncio
    async def test_without_a_mode_nothing_changes(self):
        entity, mgr = await _matrix_entity()
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_temperature(temperature=26)
        assert _sent_prontos(mgr) == ["P-C-26"]
        assert entity.hvac_mode == HVACMode.COOL


def _preset_entity(*, starting_mode=HVACMode.COOL):
    commands = [
        _cmd("c-off", "Off"), _cmd("c-on", "On"),
        _cmd("c-cool", "Cool"), _cmd("c-heat", "Heat"),
        _cmd("c-22", "Temp 22"), _cmd("c-26", "Temp 26"),
    ]
    config = EntityConfig(
        platform="climate",
        command_mapping={
            "turn_off": "Off", "turn_on": "On",
            "mode_cool": "Cool", "mode_heat": "Heat",
            "temp_22": "Temp 22", "temp_26": "Temp 26",
        },
        temperature_presets=[22, 26],
        hvac_modes=["cool", "heat"],
    )
    device = _device(
        device_type=DeviceType.AC, commands=commands, entity_config=config,
    )
    mgr = _manager()
    entity = HAIRClimateEntity(device, mgr)
    _patch_write_state(entity)
    entity._hvac_mode = starting_mode
    return entity, mgr


def _sent_ids(mgr) -> list[str]:
    return [c.args[1] for c in mgr.async_send_command.await_args_list]


class TestPresetDevice:
    @pytest.mark.asyncio
    async def test_mode_then_temperature(self):
        entity, mgr = _preset_entity()
        await entity.async_set_temperature(temperature=26, hvac_mode=HVACMode.HEAT)
        assert _sent_ids(mgr) == ["c-heat", "c-26"]
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.target_temperature == 26.0

    @pytest.mark.asyncio
    async def test_the_mode_already_shown_is_not_pressed_again(self):
        entity, mgr = _preset_entity()
        await entity.async_set_temperature(temperature=22, hvac_mode=HVACMode.COOL)
        assert _sent_ids(mgr) == ["c-22"]

    @pytest.mark.asyncio
    async def test_off_with_a_temperature_turns_off_and_keeps_it(self):
        entity, mgr = _preset_entity()
        await entity.async_set_temperature(temperature=25, hvac_mode=HVACMode.OFF)
        # No temperature command to a unit being turned off; 25 snaps to
        # the nearest preset, 26, as a temperature call always has.
        assert _sent_ids(mgr) == ["c-off"]
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.target_temperature == 26.0

    @pytest.mark.asyncio
    async def test_without_a_mode_only_the_temperature_goes(self):
        entity, mgr = _preset_entity()
        await entity.async_set_temperature(temperature=26)
        assert _sent_ids(mgr) == ["c-26"]
        assert entity.hvac_mode == HVACMode.COOL
