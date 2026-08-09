"""Climate room sensors (climate-sensors.md, commit 2/3, riding 0.9.8).

Entity-side, display-only mirror of a configured temperature/humidity
sensor -- no verdicts, no thresholds, nothing here changes assumed
on/off state or sends IR. The contracts under test:

- One subscription over whichever sensor ids are configured (skipping
  Nones); mirrors on every state-change event.
- Startup seed: the current reading is evaluated immediately at
  subscribe time, same rule as the power monitor's.
- Unavailable / unknown / non-numeric readings mirror to None and
  recover on the next good reading.
- Temperature converts from the sensor's own unit to this entity's
  declared unit (F->C, C->F, K->C); humidity passes through as a raw
  percentage.
- A device with no sensors configured subscribes to nothing.
- Clearing a sensor unsubscribes and drops the mirrored reading back
  to None.
- update_device() re-derives the subscription on every settings save
  (the resubscribe-on-change hook), and power verdict handling is
  untouched by any of this.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.models import IRDevice
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

TRACK = "custom_components.hair.climate.async_track_state_change_event"


def _matrix(unit: str = "C") -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        unit=unit,
        modes=["cool", "auto"],
        fan_modes=[],
        swing_modes=[],
        off="P-OFF",
        on="P-ON",
        cells=[
            ClimateCell(mode="cool", fan=None, temp=22.0, pronto="P-C-22"),
        ],
    )


def _device(**overrides) -> IRDevice:
    defaults = dict(
        id="dev-1",
        name="Bedroom AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        climate_matrix=True,
    )
    defaults.update(overrides)
    return IRDevice(**defaults)


def _state(value, unit=None, entity_id="sensor.x") -> State:
    attrs = {ATTR_UNIT_OF_MEASUREMENT: unit} if unit else {}
    return State(entity_id, str(value), attrs)


def _hass():
    hass = MagicMock()
    hass.states.get.return_value = None
    return hass


async def _entity(device=None, matrix=None, hass=None):
    """A matrix-mode entity, manager mocked, matrix pre-loaded, added
    to a (mock) hass -- mirrors test_climate_entity_matrix.py's helper,
    plus a controllable hass so sensor subscription can be inspected.
    """
    device = device or _device()
    mtx = matrix if matrix is not None else _matrix()
    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=mtx)
    entity = HAIRClimateEntity(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = hass or _hass()
    await entity.async_added_to_hass()
    return entity, mgr


class TestSubscriptionLifecycle:
    @pytest.mark.asyncio
    async def test_no_sensors_configured_subscribes_to_nothing(self):
        with patch(TRACK) as track:
            await _entity()
        track.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscribes_to_both_configured_sensors(self):
        device = _device(
            temperature_sensor_entity_id="sensor.temp",
            humidity_sensor_entity_id="sensor.humidity",
        )
        with patch(TRACK) as track:
            await _entity(device=device)
        track.assert_called_once()
        args, _kwargs = track.call_args
        assert args[1] == ["sensor.temp", "sensor.humidity"]

    @pytest.mark.asyncio
    async def test_subscribes_to_only_the_configured_one(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        with patch(TRACK) as track:
            await _entity(device=device)
        args, _kwargs = track.call_args
        assert args[1] == ["sensor.temp"]

    @pytest.mark.asyncio
    async def test_remove_from_hass_unsubscribes(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        unsub = MagicMock()
        with patch(TRACK, return_value=unsub):
            entity, _mgr = await _entity(device=device)
        await entity.async_will_remove_from_hass()
        unsub.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_device_resubscribes_on_sensor_change(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        old_unsub = MagicMock()
        with patch(TRACK, return_value=old_unsub) as track:
            entity, _mgr = await _entity(device=device)
        assert track.call_count == 1

        new_unsub = MagicMock()
        new_device = _device(temperature_sensor_entity_id="sensor.other_temp")
        with patch(TRACK, return_value=new_unsub) as track:
            entity.update_device(new_device)

        old_unsub.assert_called_once()
        args, _kwargs = track.call_args
        assert args[1] == ["sensor.other_temp"]

    @pytest.mark.asyncio
    async def test_update_device_with_sensor_cleared_only_unsubscribes(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        unsub = MagicMock()
        with patch(TRACK, return_value=unsub):
            entity, _mgr = await _entity(device=device)

        new_device = _device(temperature_sensor_entity_id=None)
        with patch(TRACK) as track:
            entity.update_device(new_device)

        unsub.assert_called_once()
        track.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_device_leaves_a_device_with_no_sensors_alone(self):
        with patch(TRACK) as track:
            entity, _mgr = await _entity()
        entity.update_device(_device(name="Renamed"))
        track.assert_not_called()

    @pytest.mark.asyncio
    async def test_power_verdict_handling_untouched(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        with patch(TRACK):
            entity, _mgr = await _entity(device=device)
        assert entity.hvac_mode.value == "off"
        entity._handle_power_verdict("dev-1", "on")
        assert entity.hvac_mode.value != "off"


class TestStartupSeed:
    @pytest.mark.asyncio
    async def test_seeds_current_readings_at_subscribe_time(self):
        device = _device(
            temperature_sensor_entity_id="sensor.temp",
            humidity_sensor_entity_id="sensor.humidity",
        )
        hass = _hass()

        def _states_get(entity_id):
            if entity_id == "sensor.temp":
                return _state(22.0, unit="°C", entity_id="sensor.temp")
            if entity_id == "sensor.humidity":
                return _state(48, entity_id="sensor.humidity")
            return None

        hass.states.get.side_effect = _states_get
        with patch(TRACK):
            entity, _mgr = await _entity(device=device, hass=hass)

        assert entity.current_temperature == 22.0
        assert entity.current_humidity == 48.0

    @pytest.mark.asyncio
    async def test_no_reading_yet_seeds_none(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        with patch(TRACK):
            entity, _mgr = await _entity(device=device)
        assert entity.current_temperature is None


class TestReadingUpdates:
    @pytest.mark.asyncio
    async def test_mirrors_on_state_change_event(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        captured = {}

        def _fake_track(hass_arg, ids, action):
            captured["fn"] = action
            return MagicMock()

        with patch(TRACK, side_effect=_fake_track):
            entity, _mgr = await _entity(device=device)

        event = MagicMock()
        event.data = {
            "entity_id": "sensor.temp",
            "new_state": _state(21.0, unit="°C", entity_id="sensor.temp"),
        }
        captured["fn"](event)
        assert entity.current_temperature == 21.0

    @pytest.mark.asyncio
    async def test_unavailable_reading_mirrors_to_none_and_recovers(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        captured = {}

        def _fake_track(hass_arg, ids, action):
            captured["fn"] = action
            return MagicMock()

        with patch(TRACK, side_effect=_fake_track):
            entity, _mgr = await _entity(device=device)

        event = MagicMock()
        event.data = {
            "entity_id": "sensor.temp",
            "new_state": State("sensor.temp", "unavailable", {}),
        }
        captured["fn"](event)
        assert entity.current_temperature is None

        event.data = {
            "entity_id": "sensor.temp",
            "new_state": _state(19.5, unit="°C", entity_id="sensor.temp"),
        }
        captured["fn"](event)
        assert entity.current_temperature == 19.5

    @pytest.mark.asyncio
    async def test_non_numeric_reading_mirrors_to_none(self):
        device = _device(humidity_sensor_entity_id="sensor.humidity")
        captured = {}

        def _fake_track(hass_arg, ids, action):
            captured["fn"] = action
            return MagicMock()

        with patch(TRACK, side_effect=_fake_track):
            entity, _mgr = await _entity(device=device)

        event = MagicMock()
        event.data = {
            "entity_id": "sensor.humidity",
            "new_state": State("sensor.humidity", "unknown", {}),
        }
        captured["fn"](event)
        assert entity.current_humidity is None

    @pytest.mark.asyncio
    async def test_humidity_passes_through_without_conversion(self):
        device = _device(humidity_sensor_entity_id="sensor.humidity")
        captured = {}

        def _fake_track(hass_arg, ids, action):
            captured["fn"] = action
            return MagicMock()

        with patch(TRACK, side_effect=_fake_track):
            entity, _mgr = await _entity(device=device)

        event = MagicMock()
        event.data = {
            "entity_id": "sensor.humidity",
            "new_state": _state(63, unit="%", entity_id="sensor.humidity"),
        }
        captured["fn"](event)
        assert entity.current_humidity == 63.0


class TestTemperatureConversion:
    async def _fahrenheit_entity(self, temp_reading):
        """A Fahrenheit-native matrix entity fed a reading in `unit`."""
        device = _device(temperature_sensor_entity_id="sensor.temp")
        captured = {}

        def _fake_track(hass_arg, ids, action):
            captured["fn"] = action
            return MagicMock()

        with patch(TRACK, side_effect=_fake_track):
            entity, _mgr = await _entity(device=device, matrix=_matrix(unit="F"))

        event = MagicMock()
        event.data = {"entity_id": "sensor.temp", "new_state": temp_reading}
        captured["fn"](event)
        return entity

    @pytest.mark.asyncio
    async def test_celsius_sensor_into_fahrenheit_entity_converts(self):
        entity = await self._fahrenheit_entity(
            _state(22.5, unit="°C", entity_id="sensor.temp")
        )
        assert entity.current_temperature == pytest.approx(72.5)

    @pytest.mark.asyncio
    async def test_fahrenheit_sensor_into_celsius_entity_converts(self):
        device = _device(temperature_sensor_entity_id="sensor.temp")
        captured = {}

        def _fake_track(hass_arg, ids, action):
            captured["fn"] = action
            return MagicMock()

        with patch(TRACK, side_effect=_fake_track):
            entity, _mgr = await _entity(device=device, matrix=_matrix(unit="C"))

        event = MagicMock()
        event.data = {
            "entity_id": "sensor.temp",
            "new_state": _state(72.5, unit="°F", entity_id="sensor.temp"),
        }
        captured["fn"](event)
        assert entity.current_temperature == pytest.approx(22.5)

    @pytest.mark.asyncio
    async def test_kelvin_sensor_converts(self):
        entity = await self._fahrenheit_entity(
            _state(295.65, unit="K", entity_id="sensor.temp")
        )
        assert entity.current_temperature == pytest.approx(72.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_matching_unit_needs_no_conversion(self):
        entity = await self._fahrenheit_entity(
            _state(72.5, unit="°F", entity_id="sensor.temp")
        )
        assert entity.current_temperature == pytest.approx(72.5)
