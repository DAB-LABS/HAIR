"""Cold Cuts (v0.8.8): the climate entity's matrix mode.

The contracts under test:

- Bounds, step, modes, fans, and swings all come from the matrix file
  (vocabulary verbatim); features light up only for dimensions the
  matrix actually carries.
- Every action resolves the full target state to ONE cell and sends
  its complete-state Pronto via the manager's matrix send path, named
  by the DISPLAY grammar ("cool / fan: auto / 22", owner ruling
  2026-07-29 mockup CC4); temperature snaps to what actually went out.
- OFF sends the file's off code (named "Off") and setters while OFF
  store state locally without transmitting (no surprise blasts).
- Sparse matrices miss honestly: a warning, no send, no raise.
- The matrix_cell attribute tracks the last transmitted cell by its
  display name -- the machine cell_key never surfaces here.
- Matrix mode never reads entity_config.command_mapping (the Map
  door stays shut; preset modes are the documented way back in).

Preset-mode behavior is pinned by the existing suite in
test_entities.py and deliberately untouched here.
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.models import IRDevice
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# Entity tests never validate or transmit codes, so readable tags
# beat real Pronto hex for pinning which cell went out.
P_OFF = "P-OFF"
P_ON = "P-ON"


def _matrix(on: str | None = P_ON, swing: bool = False) -> ClimateMatrix:
    swing_kw = {"swing": "swing"} if swing else {}
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        # "auto" is declared with NO cells: the census sparse-matrix
        # case (158 nulls) the resolve path must survive.
        modes=["cool", "dry", "heat", "auto"],
        fan_modes=["auto", "low"],
        swing_modes=["swing", "fixed"] if swing else [],
        off=P_OFF,
        on=on,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=16.0,
                        pronto="P-C-A-16", **swing_kw),
            ClimateCell(mode="cool", fan="auto", temp=22.0,
                        pronto="P-C-A-22", **swing_kw),
            ClimateCell(mode="cool", fan="auto", temp=30.0,
                        pronto="P-C-A-30", **swing_kw),
            ClimateCell(mode="cool", fan="low", temp=22.0,
                        pronto="P-C-L-22", **swing_kw),
            ClimateCell(mode="dry", fan="auto", pronto="P-D-A"),
            ClimateCell(mode="heat", fan="auto", temp=22.0,
                        pronto="P-H-A-22", send_count=2),
        ],
    )


def _device() -> IRDevice:
    return IRDevice(
        id="dev-1",
        name="Bedroom AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        climate_matrix=True,
    )


async def _entity(matrix=..., **device_over):
    """A matrix-mode entity with the manager mocked and matrix loaded."""
    if matrix is ...:
        matrix = _matrix()
    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=matrix)
    entity = HAIRClimateEntity(_device(), mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    await entity.async_added_to_hass()
    return entity, mgr


class TestMatrixProperties:
    @pytest.mark.asyncio
    async def test_bounds_and_step_from_file(self):
        entity, _ = await _entity()
        assert entity.min_temp == 16.0
        assert entity.max_temp == 30.0
        assert entity.target_temperature_step == 1.0

    @pytest.mark.asyncio
    async def test_hvac_modes_alias_mapped_in_file_order(self):
        entity, _ = await _entity()
        assert entity.hvac_modes == [
            HVACMode.OFF, HVACMode.COOL, HVACMode.DRY, HVACMode.HEAT,
            HVACMode.AUTO,
        ]

    @pytest.mark.asyncio
    async def test_fan_modes_verbatim(self):
        entity, _ = await _entity()
        assert entity.fan_modes == ["auto", "low"]

    @pytest.mark.asyncio
    async def test_swing_modes_verbatim_with_feature(self):
        entity, _ = await _entity(matrix=_matrix(swing=True))
        assert entity.swing_modes == ["swing", "fixed"]
        f = int(entity.supported_features)
        assert f & ClimateEntityFeature.SWING_MODE

    @pytest.mark.asyncio
    async def test_features_track_matrix_dimensions(self):
        entity, _ = await _entity()
        f = int(entity.supported_features)
        assert f & ClimateEntityFeature.TARGET_TEMPERATURE
        assert f & ClimateEntityFeature.FAN_MODE
        assert not (f & ClimateEntityFeature.SWING_MODE)
        assert entity.swing_modes is None

    @pytest.mark.asyncio
    async def test_no_temp_cells_no_temperature_feature(self):
        m = _matrix()
        m.cells = [ClimateCell(mode="dry", fan="auto", pronto="P-D-A")]
        entity, _ = await _entity(matrix=m)
        f = int(entity.supported_features)
        assert not (f & ClimateEntityFeature.TARGET_TEMPERATURE)

    @pytest.mark.asyncio
    async def test_target_seeded_to_snapped_midpoint(self):
        entity, _ = await _entity()
        assert entity.target_temperature == 23.0

    @pytest.mark.asyncio
    async def test_matrix_cell_attribute_starts_none(self):
        entity, _ = await _entity()
        assert entity.extra_state_attributes == {"matrix_cell": None}


class TestMatrixActions:
    @pytest.mark.asyncio
    async def test_set_hvac_mode_resolves_and_sends_cell(self):
        entity, mgr = await _entity()
        await entity.async_set_hvac_mode(HVACMode.COOL)
        # Seeded target 23 snaps to the branch's 22.
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: auto / 22", "P-C-A-22", 1
        )
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.target_temperature == 22.0
        assert entity.extra_state_attributes == {
            "matrix_cell": "cool / fan: auto / 22"
        }

    @pytest.mark.asyncio
    async def test_cell_send_count_rides(self):
        entity, mgr = await _entity()
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "heat / fan: auto / 22", "P-H-A-22", 2
        )

    @pytest.mark.asyncio
    async def test_set_temperature_snaps_to_available_cell(self):
        entity, mgr = await _entity()
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_temperature(temperature=27)
        # 27 snaps to 30 (nearest of 16/22/30).
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: auto / 30", "P-C-A-30", 1
        )
        assert entity.target_temperature == 30.0

    @pytest.mark.asyncio
    async def test_set_temperature_while_off_stores_without_sending(self):
        """No surprise blasts: OFF setters are local state only."""
        entity, mgr = await _entity()
        await entity.async_set_temperature(temperature=18)
        mgr.async_send_matrix_cell.assert_not_awaited()
        assert entity.target_temperature == 18.0
        # The stored state rides out on the next mode action.
        await entity.async_set_hvac_mode(HVACMode.COOL)
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: auto / 16", "P-C-A-16", 1
        )

    @pytest.mark.asyncio
    async def test_set_fan_mode_resolves_in_current_mode(self):
        entity, mgr = await _entity()
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_fan_mode("low")
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: low / 22", "P-C-L-22", 1
        )
        assert entity.fan_mode == "low"

    @pytest.mark.asyncio
    async def test_set_fan_mode_while_off_is_local(self):
        entity, mgr = await _entity()
        await entity.async_set_fan_mode("low")
        mgr.async_send_matrix_cell.assert_not_awaited()
        assert entity.fan_mode == "low"

    @pytest.mark.asyncio
    async def test_set_swing_mode_resolves_and_sends(self):
        entity, mgr = await _entity(matrix=_matrix(swing=True))
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_swing_mode("swing")
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: auto / swing: swing / 22", "P-C-A-22", 1
        )
        assert entity.swing_mode == "swing"

    @pytest.mark.asyncio
    async def test_off_sends_the_off_code(self):
        entity, mgr = await _entity()
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_hvac_mode(HVACMode.OFF)
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "Off", P_OFF
        )
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.extra_state_attributes == {"matrix_cell": "Off"}

    @pytest.mark.asyncio
    async def test_turn_off_matches_off_mode(self):
        entity, mgr = await _entity()
        await entity.async_turn_off()
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "Off", P_OFF
        )

    @pytest.mark.asyncio
    async def test_turn_on_uses_the_on_code_when_present(self):
        entity, mgr = await _entity()
        await entity.async_turn_on()
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "On", P_ON
        )
        # Displays the file's first mode as the assumed on-state.
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.extra_state_attributes == {"matrix_cell": "On"}

    @pytest.mark.asyncio
    async def test_turn_on_without_on_code_resolves_first_mode(self):
        entity, mgr = await _entity(matrix=_matrix(on=None))
        await entity.async_turn_on()
        mgr.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: auto / 22", "P-C-A-22", 1
        )
        assert entity.hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_sparse_miss_warns_and_sends_nothing(self, caplog):
        """Mode "auto" is declared but has no cells (census: sparse
        matrices are corpus fact). Warn, skip, never raise."""
        entity, mgr = await _entity()
        with caplog.at_level(logging.WARNING):
            await entity.async_set_hvac_mode(HVACMode.AUTO)
        mgr.async_send_matrix_cell.assert_not_awaited()
        assert "no cell" in caplog.text
        # The attribute stays honest: nothing new went out.
        assert entity.extra_state_attributes == {"matrix_cell": None}

    @pytest.mark.asyncio
    async def test_matrix_mode_never_reads_command_mapping(self):
        """The Map door stays shut (Cold Cuts second half, 2026-07-29):
        every matrix send resolves from the matrix file, so a mapping
        left over from any past life must be inert -- the frontend
        hides the Map action and the backend needs no enforcement
        because these paths never consult it. Documented door: preset
        modes on matrix devices may one day revive the mapping through
        _send; until then this test pins the wall."""
        entity, mgr = await _entity()
        entity._device.entity_config.command_mapping = {
            "turn_on": "Trap", "turn_off": "Trap", "power_toggle": "Trap",
            "mode_cool": "Trap", "fan_auto": "Trap", "temp_22": "Trap",
        }
        mgr.async_send_command = AsyncMock()
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_temperature(temperature=22)
        await entity.async_set_fan_mode("low")
        await entity.async_turn_on()
        await entity.async_turn_off()
        mgr.async_send_command.assert_not_awaited()
        # Everything above went out through the matrix path instead.
        assert mgr.async_send_matrix_cell.await_count == 5

    @pytest.mark.asyncio
    async def test_unloaded_matrix_refuses_gracefully(self, caplog):
        """A missing/unreadable matrix file: the entity exists but
        refuses to send, with a receipt in the log."""
        entity, mgr = await _entity(matrix=None)
        assert entity.hvac_modes == [HVACMode.OFF]
        assert entity.fan_modes is None
        with caplog.at_level(logging.WARNING):
            await entity.async_set_hvac_mode(HVACMode.COOL)
            await entity.async_set_hvac_mode(HVACMode.OFF)
        mgr.async_send_matrix_cell.assert_not_awaited()
        assert "not loaded" in caplog.text


class TestUnits:
    """Unit ruling 2026-07-29: matrix temps are data-native file
    numbers. The entity declares the FILE's unit so HA core converts
    the thermostat display and inbound set-temperatures both ways
    dynamically; preset mode keeps the installation-unit behavior
    byte-for-byte (the mirror image, GH #45). The matrix_cell
    attribute converts its temperature part to the INSTALL's unit at
    send time -- a live surface, never a frozen name.
    """

    @pytest.mark.asyncio
    async def test_matrix_mode_declares_the_file_unit(self):
        from homeassistant.const import UnitOfTemperature

        entity, _ = await _entity()
        # Whatever the install runs, a C file is a C entity.
        entity.hass.config.units.temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
        )
        assert entity.temperature_unit == UnitOfTemperature.CELSIUS

        f_matrix = _matrix()
        f_matrix.unit = "F"
        entity, _ = await _entity(matrix=f_matrix)
        entity.hass.config.units.temperature_unit = (
            UnitOfTemperature.CELSIUS
        )
        assert entity.temperature_unit == UnitOfTemperature.FAHRENHEIT

    @pytest.mark.asyncio
    async def test_preset_mode_keeps_the_install_unit(self):
        from homeassistant.const import UnitOfTemperature

        entity, _ = await _entity()
        entity._device.climate_matrix = False
        entity.hass.config.units.temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
        )
        assert entity.temperature_unit == UnitOfTemperature.FAHRENHEIT

    @pytest.mark.asyncio
    async def test_matrix_cell_attribute_converts_at_send_time(self):
        from homeassistant.const import UnitOfTemperature

        entity, mgr = await _entity()
        entity.hass.config.units.temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
        )
        entity._target_temperature = 22.0
        await entity.async_set_hvac_mode(HVACMode.COOL)
        name = mgr.async_send_matrix_cell.await_args.args[1]
        assert name == "cool / fan: auto / 72"
        assert entity.extra_state_attributes["matrix_cell"] == name
        # The dial itself stays NATIVE (HA core converts it): the
        # transmitted cell's own 22, never 72.
        assert entity.target_temperature == 22.0
