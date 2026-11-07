"""Per-mode fan, swing and temperature for a matrix climate (GH #168).

A matrix device's fan and swing lists, and its dial, follow the current
mode: a mode offers only the fans, swings and temperatures its own
cells carry, and only where choosing differently changes the code.
The temperature range stays one range for every mode, taken from the
cells that remain. A mode switch shows the cell that actually went out
and keeps the person's last choice to go back to when a mode offers it
again. The supported features never change. A preset (non-matrix)
device is untouched.

Every matrix here is written by hand; readable tags stand in for Pronto
text so a test can name which cell went out.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.core import State

from custom_components.hair.climate import HAIRClimateEntity, _ClimateExtraStoredData
from custom_components.hair.const import DeviceType
from custom_components.hair.models import EntityConfig, IRDevice
from custom_components.hair.send_signal import DeviceSent
from custom_components.hair.wig_climate import (
    _axis_changes_code,
    combined_temperature_range,
    matrix_capabilities,
    mode_capabilities,
)
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

P_OFF = "P-OFF"


def _cells() -> list[ClimateCell]:
    cells: list[ClimateCell] = []
    # Cool: three fans, two swings, three temperatures, a code each.
    for fan in ("auto", "low", "high"):
        for swing in ("off", "vertical"):
            for temp in (18, 22, 26):
                cells.append(ClimateCell(
                    mode="cool", fan=fan, swing=swing, temp=float(temp),
                    pronto=f"P-COOL-{fan}-{swing}-{temp}",
                ))
    # Dry: stored at every temperature with one code, one fan, one
    # swing. Nothing to choose: no fan, no swing, no dial.
    for temp in range(18, 27):
        cells.append(ClimateCell(
            mode="dry", fan="low", swing="off", temp=float(temp),
            pronto="P-DRY",
        ))
    # Fan only: fans and swings, no temperature at all.
    for fan in ("auto", "low", "high"):
        for swing in ("off", "vertical"):
            cells.append(ClimateCell(
                mode="fan_only", fan=fan, swing=swing,
                pronto=f"P-FAN-{fan}-{swing}",
            ))
    # Heat: two fans, one swing, two temperatures.
    for fan in ("auto", "high"):
        for temp in (20, 24):
            cells.append(ClimateCell(
                mode="heat", fan=fan, swing="off", temp=float(temp),
                pronto=f"P-HEAT-{fan}-{temp}",
            ))
    return cells


def _matrix() -> ClimateMatrix:
    # The frame says 16-32, as a thinned wig's frame still does; the
    # cells say 18-26.
    return ClimateMatrix(
        min_temp=16.0, max_temp=32.0, precision=1.0,
        modes=["cool", "dry", "fan_only", "heat"],
        fan_modes=["auto", "low", "medium", "high"],
        swing_modes=["off", "vertical"],
        off=P_OFF, on=None, cells=_cells(),
    )


def _device() -> IRDevice:
    return IRDevice(
        id="dev-1", name="Office AC", device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"], climate_matrix=True,
    )


async def _entity(matrix=None, *, last_state=None, extra=None):
    matrix = _matrix() if matrix is None else matrix
    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=matrix)
    entity = HAIRClimateEntity(_device(), mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.hass.config.units.temperature_unit = "°C"
    entity.async_get_last_state = AsyncMock(return_value=last_state)
    entity.async_get_last_extra_data = AsyncMock(return_value=extra)
    await entity.async_added_to_hass()
    return entity, mgr


def _sent(mgr) -> str:
    """The Pronto tag of the last cell sent."""
    return mgr.async_send_matrix_cell.await_args.args[2]


async def _cool_low_vertical_22(entity, mgr) -> None:
    entity._hvac_mode = HVACMode.COOL
    await entity.async_set_fan_mode("low")
    await entity.async_set_swing_mode("vertical")
    await entity.async_set_temperature(temperature=22)
    assert _sent(mgr) == "P-COOL-low-vertical-22"
    mgr.async_send_matrix_cell.reset_mock()


class TestTheListsFollowTheMode:
    @pytest.mark.asyncio
    async def test_cool_offers_its_own_fans_and_swings(self):
        entity, _ = await _entity()
        entity._hvac_mode = HVACMode.COOL
        # "medium" is in the file's vocabulary and in no cell.
        assert entity.fan_modes == ["auto", "low", "high"]
        assert entity.swing_modes == ["off", "vertical"]
        assert entity.target_temperature is not None

    @pytest.mark.asyncio
    async def test_heat_offers_two_fans_and_no_swing(self):
        entity, _ = await _entity()
        entity._hvac_mode = HVACMode.HEAT
        assert entity.fan_modes == ["auto", "high"]
        assert entity.swing_modes is None

    @pytest.mark.asyncio
    async def test_a_static_dry_offers_nothing(self):
        """One code at every temperature, one fan, one swing."""
        entity, _ = await _entity()
        entity._hvac_mode = HVACMode.DRY
        entity._fan_mode, entity._swing_mode = "low", "off"
        entity._target_temperature = 22.0
        assert entity.fan_modes is None
        assert entity.swing_modes is None
        assert entity.fan_mode is None
        assert entity.swing_mode is None
        assert entity.target_temperature is None
        # Kept, for the next mode that has a dial.
        assert entity._target_temperature == 22.0

    @pytest.mark.asyncio
    async def test_fan_only_offers_fans_and_no_dial(self):
        entity, _ = await _entity()
        entity._hvac_mode = HVACMode.FAN_ONLY
        assert entity.fan_modes == ["auto", "low", "high"]
        assert entity.swing_modes == ["off", "vertical"]
        assert entity.target_temperature is None

    @pytest.mark.asyncio
    async def test_off_offers_the_lists_of_the_mode_it_turns_on_into(self):
        entity, _ = await _entity()
        # Never on yet: the file's first mode.
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.fan_modes == ["auto", "low", "high"]
        # Off from heat: heat's.
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_turn_off()
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.fan_modes == ["auto", "high"]
        assert entity.swing_modes is None


class TestWhatNeverChanges:
    @pytest.mark.asyncio
    async def test_range_and_features_are_the_same_in_every_mode(self):
        """Home Assistant checks a temperature call against the range
        before the call's own hvac_mode applies, and a missing feature
        bit refuses the call outright, so neither may move with the
        mode."""
        entity, _ = await _entity()
        seen = set()
        for mode in (HVACMode.OFF, HVACMode.COOL, HVACMode.DRY,
                     HVACMode.FAN_ONLY, HVACMode.HEAT):
            entity._hvac_mode = mode
            seen.add((entity.min_temp, entity.max_temp,
                      entity.supported_features))
        assert len(seen) == 1
        (low, high, features), = seen
        # From the cells, not the frame's 16-32.
        assert (low, high) == (18.0, 26.0)
        for bit in (ClimateEntityFeature.FAN_MODE,
                    ClimateEntityFeature.SWING_MODE,
                    ClimateEntityFeature.TARGET_TEMPERATURE):
            assert features & bit

    @pytest.mark.asyncio
    async def test_a_static_mode_cannot_widen_the_range(self):
        """Dry stored at 10-35 with one code says nothing about what the
        unit can be set to."""
        matrix = _matrix()
        matrix.cells += [
            ClimateCell(mode="dry", fan="low", swing="off", temp=float(t),
                        pronto="P-DRY")
            for t in (10, 35)
        ]
        entity, _ = await _entity(matrix)
        assert (entity.min_temp, entity.max_temp) == (18.0, 26.0)

    @pytest.mark.asyncio
    async def test_a_thinned_matrix_narrows_the_range_and_the_lists(self):
        matrix = _matrix()
        entity, _ = await _entity(matrix)
        assert (entity.min_temp, entity.max_temp) == (18.0, 26.0)
        # Thinning keeps the frame and drops cells: cool keeps 22 and
        # loses its low fan.
        matrix.cells = [
            c for c in matrix.cells
            if not (c.mode == "cool" and (c.temp != 22.0 or c.fan == "low"))
        ]
        await entity._async_load_matrix()  # what SIGNAL_MATRIX_CHANGED runs
        entity._hvac_mode = HVACMode.COOL
        assert (entity.min_temp, entity.max_temp) == (20.0, 24.0)
        assert entity.fan_modes == ["auto", "high"]
        # Cool now has one temperature: no dial in cool.
        assert entity.target_temperature is None


class TestAModeSwitch:
    @pytest.mark.asyncio
    async def test_shows_what_went_out_and_comes_back_to_the_choice(self):
        entity, mgr = await _entity()
        await _cool_low_vertical_22(entity, mgr)

        await entity.async_set_hvac_mode(HVACMode.HEAT)

        # Heat has no low fan and no vertical swing.
        sent = _sent(mgr)
        assert sent in ("P-HEAT-auto-20", "P-HEAT-auto-24")
        assert entity.fan_mode == "auto"  # what went out, not "low"
        assert entity.swing_mode is None  # heat has no swing to choose
        assert entity._swing_mode == "off"
        assert entity.target_temperature == float(sent.rsplit("-", 1)[1])
        assert entity.extra_state_attributes["matrix_cell"].startswith(
            "heat / fan: auto"
        )

        await entity.async_set_hvac_mode(HVACMode.COOL)

        # The person's fan, swing and temperature, valid again.
        assert _sent(mgr) == "P-COOL-low-vertical-22"
        assert (entity.fan_mode, entity.swing_mode,
                entity.target_temperature) == ("low", "vertical", 22.0)

    @pytest.mark.asyncio
    async def test_a_static_dry_and_back(self):
        entity, mgr = await _entity()
        await _cool_low_vertical_22(entity, mgr)

        await entity.async_set_hvac_mode(HVACMode.DRY)

        assert _sent(mgr) == "P-DRY"
        assert entity.target_temperature is None
        assert entity._target_temperature == 22.0

        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert _sent(mgr) == "P-COOL-low-vertical-22"

    @pytest.mark.asyncio
    async def test_a_new_choice_in_a_mode_replaces_the_old_one(self):
        entity, mgr = await _entity()
        await _cool_low_vertical_22(entity, mgr)
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_fan_mode("high")
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert _sent(mgr) == "P-COOL-high-vertical-22"


class TestATemperatureWithNoDial:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", [HVACMode.DRY, HVACMode.FAN_ONLY])
    async def test_is_stored_and_nothing_is_sent(self, mode):
        entity, mgr = await _entity()
        await _cool_low_vertical_22(entity, mgr)
        await entity.async_set_hvac_mode(mode)
        mgr.async_send_matrix_cell.reset_mock()

        await entity.async_set_temperature(temperature=25)

        mgr.async_send_matrix_cell.assert_not_awaited()
        assert entity.target_temperature is None
        assert entity._target_temperature == 25.0

        # It goes out in the next mode with a dial, snapped there.
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert _sent(mgr) == "P-COOL-low-vertical-26"

    @pytest.mark.asyncio
    async def test_with_a_mode_it_goes_out_in_that_mode(self):
        """The call's hvac_mode (1.1.1) still wins: one send, in cool."""
        entity, mgr = await _entity()
        await _cool_low_vertical_22(entity, mgr)
        await entity.async_set_hvac_mode(HVACMode.DRY)
        mgr.async_send_matrix_cell.reset_mock()

        await entity.async_set_temperature(temperature=18,
                                           hvac_mode=HVACMode.COOL)

        mgr.async_send_matrix_cell.assert_awaited_once()
        assert _sent(mgr) == "P-COOL-low-vertical-18"


class TestARestart:
    @pytest.mark.asyncio
    async def test_shows_the_resolved_cell_and_keeps_the_choice(self):
        last = State("climate.x", "heat", {
            "fan_mode": "auto", "swing_mode": None, "temperature": 20.0,
        })
        extra = _ClimateExtraStoredData(
            native_target_temperature=22.0,
            wanted_fan="low", wanted_swing="vertical",
        )
        entity, mgr = await _entity(last_state=last, extra=extra)

        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.fan_mode == "auto"
        mgr.async_send_matrix_cell.assert_not_awaited()

        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert _sent(mgr) == "P-COOL-low-vertical-22"

    @pytest.mark.asyncio
    async def test_in_a_mode_with_no_dial_keeps_the_setpoint(self):
        last = State("climate.x", "dry", {"fan_mode": None})
        extra = _ClimateExtraStoredData(native_target_temperature=24.0)
        entity, _ = await _entity(last_state=last, extra=extra)

        assert entity.hvac_mode == HVACMode.DRY
        assert entity.target_temperature is None
        assert entity._target_temperature == 24.0

    @pytest.mark.asyncio
    async def test_the_choice_round_trips(self):
        entity, mgr = await _entity()
        await _cool_low_vertical_22(entity, mgr)
        await entity.async_set_hvac_mode(HVACMode.HEAT)

        stored = _ClimateExtraStoredData.from_dict(
            entity.extra_restore_state_data.as_dict()
        )
        assert (stored.wanted_fan, stored.wanted_swing,
                stored.native_target_temperature) == ("low", "vertical", 22.0)

    def test_a_payload_from_before_still_reads(self):
        stored = _ClimateExtraStoredData.from_dict(
            {"native_target_temperature": 21.0}
        )
        assert (stored.native_target_temperature, stored.wanted_fan,
                stored.wanted_swing) == (21.0, None, None)


class TestAnExtrasSend:
    @pytest.mark.asyncio
    async def test_leaves_the_lists_alone(self):
        entity, _ = await _entity()
        entity._hvac_mode = HVACMode.COOL
        before = (entity.fan_modes, entity.swing_modes, entity.fan_mode,
                  entity.target_temperature)
        entity._apply_sent(DeviceSent(
            device_id="dev-1", command_id="c2",
            command_name="(eco) heat / fan: high / 24",
            matrix_cell={
                "mode": "heat", "fan": "high", "swing": "off", "temp": 24.0,
                "axis": "preset", "lattice": "eco",
            },
            power=None, starred=False, origin="card",
        ))
        assert entity.hvac_mode == HVACMode.COOL
        assert (entity.fan_modes, entity.swing_modes, entity.fan_mode,
                entity.target_temperature) == before


class TestAPresetDevice:
    def _entity(self):
        device = IRDevice(
            id="dev-flat", name="Den AC", device_type=DeviceType.AC,
            emitter_entity_ids=["infrared.e"],
            entity_config=EntityConfig(
                platform="climate",
                command_mapping={"mode_cool": "Cool", "mode_dry": "Dry"},
                fan_modes=["Low", "High"],
                temperature_presets=[18, 24],
            ),
        )
        entity = HAIRClimateEntity(device, MagicMock())
        entity.async_write_ha_state = MagicMock()
        entity.hass = MagicMock()
        return entity

    def test_is_unchanged_in_every_mode(self):
        entity = self._entity()
        for mode in (HVACMode.OFF, HVACMode.COOL, HVACMode.DRY):
            entity._hvac_mode = mode
            entity._fan_mode = "High"
            entity._target_temperature = 24.0
            assert entity.fan_modes == ["Low", "High"]
            assert entity.fan_mode == "High"
            assert entity.swing_modes is None
            assert (entity.min_temp, entity.max_temp) == (18.0, 24.0)
            assert entity.target_temperature == 24.0
        assert entity._capabilities() == {}


class TestTheRule:
    """``_axis_changes_code``: does choosing differently change the code?"""

    def _c(self, fan, temp, pronto, swing=None):
        return ClimateCell(mode="cool", fan=fan, swing=swing, temp=temp,
                           pronto=pronto)

    def test_one_value_never_does(self):
        cells = [self._c("auto", 22.0, "A")]
        assert _axis_changes_code(cells, "temp") is False
        assert _axis_changes_code(cells, "fan") is False

    def test_one_code_across_the_axis_does_not(self):
        cells = [self._c("auto", t, "A") for t in (18.0, 22.0)]
        assert _axis_changes_code(cells, "temp") is False

    def test_one_group_that_differs_is_enough(self):
        cells = [
            self._c("auto", 18.0, "A"), self._c("auto", 22.0, "A"),
            self._c("low", 18.0, "L18"), self._c("low", 22.0, "L22"),
        ]
        assert _axis_changes_code(cells, "temp") is True

    def test_spacing_and_case_are_the_same_code(self):
        cells = [
            self._c("auto", 18.0, "0000 006d 0002"),
            self._c("auto", 22.0, "0000  006D 0002 "),
        ]
        assert _axis_changes_code(cells, "temp") is False

    def test_nothing_to_compare_keeps_the_setting(self):
        """Two temperatures that never share a fan cannot be compared:
        shown rather than hidden on no evidence."""
        cells = [self._c("auto", 18.0, "A"), self._c("low", 22.0, "L")]
        assert _axis_changes_code(cells, "temp") is True

    def test_capabilities_of_the_fixture(self):
        caps = matrix_capabilities(_matrix())
        assert set(caps) == {"cool", "dry", "fan_only", "heat"}
        assert caps["dry"].fans == () and caps["dry"].swings == ()
        assert caps["dry"].has_temperature is False
        assert caps["fan_only"].temps == ()
        assert caps["heat"].temps == (20.0, 24.0)
        assert mode_capabilities(_matrix(), "auto") is None
        assert combined_temperature_range(_matrix()) == (18.0, 26.0)

    def test_a_matrix_with_no_temperature_keeps_its_frame(self):
        matrix = _matrix()
        matrix.cells = [c for c in matrix.cells if c.mode == "fan_only"]
        assert combined_temperature_range(matrix) == (16.0, 32.0)
