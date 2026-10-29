"""The climate entity's temperature names on both Home Assistant shapes.

Home Assistant 2026.11 serves the climate temperature members as
``native_temperature_unit``, ``native_current_temperature`` and
``native_target_temperature``. It warns when an entity class provides one
of the older names (``temperature_unit``, ``current_temperature``,
``target_temperature``, ``target_temperature_high``/``_low``) and again on
every read of one. Earlier versions have only the older names. climate.py
picks one set at import, from whether the base class has
``native_temperature_unit``.

These tests load climate.py against two hand-built base classes, one
shaped like each version, and check:

- the class provides exactly one set of names, never both;
- on the 2026.11 shape nothing warns, at class creation or on any read,
  including HAIR's own reads during set-temperature, the room sensor and
  restore;
- the declared unit, a set-temperature and a sensor reading come out the
  same on both shapes, for matrix mode with a C file and an F file and
  for preset mode, each on a metric and an imperial install;
- restore lands the same setpoint on both shapes.

The rest of the suite runs against conftest's climate stub, which has the
older shape, so it keeps covering that branch as it always has.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import ATTR_TEMPERATURE
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature
from homeassistant.core import State
from homeassistant.util.unit_conversion import TemperatureConverter

from custom_components.hair import climate as climate_module
from custom_components.hair.const import CommandCategory, CommandSource, DeviceType
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

C = UnitOfTemperature.CELSIUS
F = UnitOfTemperature.FAHRENHEIT

NATIVE = frozenset({
    "native_temperature_unit",
    "native_current_temperature",
    "native_target_temperature",
    "native_target_temperature_high",
    "native_target_temperature_low",
})
LEGACY = frozenset({
    "temperature_unit",
    "current_temperature",
    "target_temperature",
    "target_temperature_high",
    "target_temperature_low",
})
_LEGACY_TO_NATIVE = {name: f"native_{name}" for name in LEGACY}
_LEGACY_TO_NATIVE["temperature_unit"] = "native_temperature_unit"


# --- the two base shapes ----------------------------------------------------


class _Deprecated:
    """An older name on the 2026.11 shape: warns on every read, then
    serves the native member, as Home Assistant's deprecated entity
    members do."""

    def __init__(self, replacement: str) -> None:
        self.replacement = replacement

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        logging.getLogger(type(instance).__module__).warning(
            "Detected code that reads the deprecated %s.%s, use %s instead",
            type(instance).__name__, self.name, self.replacement,
        )
        return getattr(instance, self.replacement)


class _Ha2611ClimateEntity:
    """Shaped like Home Assistant 2026.11's ClimateEntity."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _enable_turn_on_off_backwards_compatibility = False

    _attr_native_current_temperature = None
    _attr_native_target_temperature = None
    _attr_native_target_temperature_high = None
    _attr_native_target_temperature_low = None

    @property
    def native_temperature_unit(self) -> str:
        return self._attr_native_temperature_unit

    @property
    def native_current_temperature(self):
        return self._attr_native_current_temperature

    @property
    def native_target_temperature(self):
        return self._attr_native_target_temperature

    @property
    def native_target_temperature_high(self):
        return self._attr_native_target_temperature_high

    @property
    def native_target_temperature_low(self):
        return self._attr_native_target_temperature_low

    temperature_unit = _Deprecated("native_temperature_unit")
    current_temperature = _Deprecated("native_current_temperature")
    target_temperature = _Deprecated("native_target_temperature")
    target_temperature_high = _Deprecated("native_target_temperature_high")
    target_temperature_low = _Deprecated("native_target_temperature_low")

    def __init_subclass__(cls, **kwargs) -> None:
        """Warn for each older name a subclass provides without the
        native one, as Home Assistant 2026.11 does at class creation."""
        super().__init_subclass__(**kwargs)
        base = _Ha2611ClimateEntity
        for name, alias in vars(base).items():
            if not isinstance(alias, _Deprecated):
                continue
            provider = next(
                klass for klass in cls.__mro__
                if name in vars(klass) or alias.replacement in vars(klass)
            )
            if provider is base or alias.replacement in vars(provider):
                continue
            logging.getLogger(cls.__module__).warning(
                "%s provides the deprecated %s, use %s instead",
                cls.__qualname__, name, alias.replacement,
            )


class _Ha2610ClimateEntity:
    """Shaped like Home Assistant 2026.4 to 2026.10's ClimateEntity."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _enable_turn_on_off_backwards_compatibility = False

    _attr_current_temperature = None
    _attr_target_temperature = None
    _attr_target_temperature_high = None
    _attr_target_temperature_low = None

    @property
    def temperature_unit(self) -> str:
        return self._attr_temperature_unit

    @property
    def current_temperature(self):
        return self._attr_current_temperature

    @property
    def target_temperature(self):
        return self._attr_target_temperature

    @property
    def target_temperature_high(self):
        return self._attr_target_temperature_high

    @property
    def target_temperature_low(self):
        return self._attr_target_temperature_low


@dataclass
class _Shape:
    module: ModuleType
    base: type
    native: bool

    @property
    def entity_cls(self) -> type:
        return self.module.HAIRClimateEntity

    def name(self, legacy: str) -> str:
        """The name Home Assistant reads on this shape."""
        return _LEGACY_TO_NATIVE[legacy] if self.native else legacy

    def read(self, entity, legacy: str):
        return getattr(entity, self.name(legacy))


SHAPES = [
    pytest.param("ha2611", id="ha2611"),
    pytest.param("ha2610", id="ha2610"),
]


def _load(shape: str) -> _Shape:
    """A fresh copy of climate.py, built on the given base shape."""
    base = _Ha2611ClimateEntity if shape == "ha2611" else _Ha2610ClimateEntity
    stub = sys.modules["homeassistant.components.climate"]
    name = f"custom_components.hair._climate_{shape}"
    spec = importlib.util.spec_from_file_location(name, climate_module.__file__)
    module = importlib.util.module_from_spec(spec)
    saved = stub.ClimateEntity
    stub.ClimateEntity = base
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        stub.ClimateEntity = saved
        sys.modules.pop(name, None)
    return _Shape(module=module, base=base, native=shape == "ha2611")


def _provided(shape: _Shape) -> set[str]:
    """Every name HAIR's own classes define, above the base."""
    return {
        name
        for klass in shape.entity_cls.__mro__
        if klass not in shape.base.__mro__
        for name in vars(klass)
    }


def _assert_quiet(caplog) -> None:
    noisy = [r.getMessage() for r in caplog.records if "deprecated" in r.getMessage()]
    assert noisy == []


# --- entity builders ------------------------------------------------------


def _hass(install_unit: str) -> MagicMock:
    hass = MagicMock()
    hass.config.units.temperature_unit = install_unit
    hass.states.get.return_value = None
    return hass


def _matrix(unit: str) -> ClimateMatrix:
    low, high, mid = (60.0, 86.0, 72.0) if unit == "F" else (16.0, 30.0, 22.0)
    return ClimateMatrix(
        min_temp=low,
        max_temp=high,
        precision=1.0,
        unit=unit,
        modes=["cool"],
        fan_modes=[],
        swing_modes=[],
        off="P-OFF",
        on="P-ON",
        cells=[ClimateCell(mode="cool", fan=None, temp=mid, pronto="P-C")],
    )


async def _matrix_entity(shape: _Shape, file_unit: str, install_unit: str):
    device = IRDevice(
        id="dev-1",
        name="Bedroom AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        climate_matrix=True,
        temperature_sensor_entity_id="sensor.temp",
    )
    mgr = MagicMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=_matrix(file_unit))
    entity = shape.entity_cls(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = _hass(install_unit)
    await entity._async_load_matrix()
    return entity, mgr


def _preset_entity(shape: _Shape, install_unit: str):
    presets = [68, 72, 76] if install_unit == F else [18, 20, 22, 24]
    commands = [
        IRCommand(
            id=f"c{t}", name=f"Temp {t}", category=CommandCategory.CUSTOM,
            source=CommandSource.CAPTURED, protocol="NEC", code="0x1234",
        )
        for t in presets
    ]
    config = EntityConfig(
        platform="climate",
        command_mapping={f"temp_{t}": f"Temp {t}" for t in presets},
        temperature_presets=presets,
    )
    device = IRDevice(
        id="dev-2",
        name="Office AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        commands=commands,
        entity_config=config,
        temperature_sensor_entity_id="sensor.temp",
    )
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    entity = shape.entity_cls(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = _hass(install_unit)
    return entity, mgr


async def _ha_set_temperature(shape: _Shape, entity, value: float) -> None:
    """What Home Assistant's climate.set_temperature does with a value
    typed in the install's unit: convert it to the unit the entity
    declares (read under this shape's name), then hand it over."""
    declared = shape.read(entity, "temperature_unit")
    install = entity.hass.config.units.temperature_unit
    converted = TemperatureConverter.convert(value, install, declared)
    await entity.async_set_temperature(**{ATTR_TEMPERATURE: converted})


def _read_everything(shape: _Shape, entity) -> dict:
    """Every temperature member Home Assistant reads, under this
    shape's names, plus the ones that never changed name."""
    values = {legacy: shape.read(entity, legacy) for legacy in sorted(LEGACY)}
    values.update(
        min_temp=entity.min_temp,
        max_temp=entity.max_temp,
        target_temperature_step=entity.target_temperature_step,
    )
    return values


def _sensor(value: float, unit: str) -> State:
    return State("sensor.temp", str(value), {ATTR_UNIT_OF_MEASUREMENT: unit})


# --- the switch -------------------------------------------------------------


@pytest.mark.parametrize("shape_name", SHAPES)
def test_never_both_name_sets(shape_name):
    """However the switch is written, HAIR's class never carries an
    older name and its native counterpart together."""
    provided = _provided(_load(shape_name))
    both = {
        legacy for legacy, native in _LEGACY_TO_NATIVE.items()
        if legacy in provided and native in provided
    }
    assert both == set()
    assert not (provided & NATIVE and provided & LEGACY)


@pytest.mark.parametrize("shape_name", SHAPES)
def test_the_switch_picks_the_shape_names(shape_name):
    shape = _load(shape_name)
    assert shape.module._NATIVE_TEMPERATURE is shape.native
    expected = {
        "temperature_unit", "current_temperature", "target_temperature",
    }
    if shape.native:
        expected = {_LEGACY_TO_NATIVE[n] for n in expected}
    assert _provided(shape) & (NATIVE | LEGACY) == expected


def test_the_suite_stub_is_the_older_shape():
    """The rest of the suite exercises the older names; this pins it."""
    assert climate_module._NATIVE_TEMPERATURE is False
    assert "temperature_unit" in vars(climate_module.HAIRClimateEntity)


def test_ha2611_class_creation_is_quiet(caplog):
    with caplog.at_level(logging.WARNING):
        _load("ha2611")
    _assert_quiet(caplog)


def test_the_ha2611_base_does_warn(caplog):
    """The hand-built base catches both kinds of use, so the quiet
    assertions above have teeth."""
    with caplog.at_level(logging.WARNING):

        class _Old(_Ha2611ClimateEntity):
            @property
            def temperature_unit(self):
                return C

        class _New(_Ha2611ClimateEntity):
            _attr_native_temperature_unit = C

        _ = _New().temperature_unit
    messages = [r.getMessage() for r in caplog.records]
    assert any("provides the deprecated temperature_unit" in m for m in messages)
    assert any("reads the deprecated _New.temperature_unit" in m for m in messages)


# --- unit, set-temperature and sensor, both shapes ----------------------------


# (file unit, install unit, typed value, setpoint in the declared unit)
MATRIX_CASES = [
    pytest.param("C", C, 22.0, 22.0, id="C-file-metric"),
    pytest.param("C", F, 71.6, 22.0, id="C-file-imperial"),
    pytest.param("F", C, 22.0, 71.6, id="F-file-metric"),
    pytest.param("F", F, 72.0, 72.0, id="F-file-imperial"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("shape_name", SHAPES)
@pytest.mark.parametrize("file_unit,install,typed,setpoint", MATRIX_CASES)
async def test_matrix_mode(shape_name, file_unit, install, typed, setpoint, caplog):
    shape = _load(shape_name)
    with caplog.at_level(logging.WARNING):
        entity, mgr = await _matrix_entity(shape, file_unit, install)
        declared = F if file_unit == "F" else C
        assert shape.read(entity, "temperature_unit") == declared

        # OFF: the setpoint is stored, nothing transmits.
        await _ha_set_temperature(shape, entity, typed)
        assert shape.read(entity, "target_temperature") == pytest.approx(setpoint)
        mgr.async_send_matrix_cell.assert_not_awaited()

        # A Celsius room sensor arrives in the declared unit.
        entity._apply_sensor_reading("sensor.temp", _sensor(22.5, C))
        expected = TemperatureConverter.convert(22.5, C, declared)
        assert shape.read(entity, "current_temperature") == pytest.approx(expected)

        values = _read_everything(shape, entity)
    assert values["target_temperature_high"] is None
    assert values["target_temperature_low"] is None
    assert values["target_temperature_step"] == 1.0
    _assert_quiet(caplog)


# (install unit, typed value, preset it snaps to)
PRESET_CASES = [
    pytest.param(C, 21.6, 22.0, id="metric"),
    pytest.param(F, 71.0, 72.0, id="imperial"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("shape_name", SHAPES)
@pytest.mark.parametrize("install,typed,snapped", PRESET_CASES)
async def test_preset_mode(shape_name, install, typed, snapped, caplog):
    shape = _load(shape_name)
    with caplog.at_level(logging.WARNING):
        entity, mgr = _preset_entity(shape, install)
        assert shape.read(entity, "temperature_unit") == install

        await _ha_set_temperature(shape, entity, typed)
        assert shape.read(entity, "target_temperature") == snapped
        mgr.async_send_command.assert_awaited_once()
        assert mgr.async_send_command.await_args.args[1] == f"c{int(snapped)}"

        entity._apply_sensor_reading("sensor.temp", _sensor(22.5, C))
        expected = TemperatureConverter.convert(22.5, C, install)
        assert shape.read(entity, "current_temperature") == pytest.approx(expected)

        _read_everything(shape, entity)
    _assert_quiet(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("file_unit,install", [("C", C), ("C", F), ("F", C), ("F", F)])
async def test_matrix_values_match_across_shapes(file_unit, install):
    """Same inputs, same numbers, whichever shape HA has."""
    results = []
    for shape_name in ("ha2611", "ha2610"):
        shape = _load(shape_name)
        entity, _ = await _matrix_entity(shape, file_unit, install)
        await _ha_set_temperature(shape, entity, 22.0 if install == C else 72.0)
        entity._apply_sensor_reading("sensor.temp", _sensor(21.0, C))
        results.append(_read_everything(shape, entity))
    assert results[0] == results[1]


# --- restore, both shapes ---------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("shape_name", SHAPES)
async def test_restore_matrix_fallback_converts_display_to_file_unit(shape_name, caplog):
    """No payload yet: the last state's temperature is in the install's
    display unit (22C) and lands in the F file's unit (71.6F)."""
    shape = _load(shape_name)
    with caplog.at_level(logging.WARNING):
        entity, _ = await _matrix_entity(shape, "F", C)
        entity.async_get_last_state = AsyncMock(
            return_value=State("climate.x", "off", {ATTR_TEMPERATURE: 22.0})
        )
        entity.async_get_last_extra_data = AsyncMock(return_value=None)
        await entity._async_restore_state()
        assert shape.read(entity, "target_temperature") == pytest.approx(71.6)
    _assert_quiet(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("shape_name", SHAPES)
async def test_restore_matrix_payload_wins(shape_name, caplog):
    shape = _load(shape_name)
    with caplog.at_level(logging.WARNING):
        entity, _ = await _matrix_entity(shape, "C", F)
        entity.async_get_last_state = AsyncMock(
            return_value=State("climate.x", "off", {ATTR_TEMPERATURE: 999})
        )
        payload = shape.module._ClimateExtraStoredData(native_target_temperature=23.0)
        entity.async_get_last_extra_data = AsyncMock(return_value=payload)
        await entity._async_restore_state()
        assert shape.read(entity, "target_temperature") == 23.0
        # What the next shutdown stores is the same native number.
        assert entity.extra_restore_state_data.native_target_temperature == 23.0
    _assert_quiet(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("shape_name", SHAPES)
@pytest.mark.parametrize("install,stored", [(C, 22.0), (F, 72.0)])
async def test_restore_preset_fallback_is_a_straight_read(shape_name, install, stored, caplog):
    shape = _load(shape_name)
    with caplog.at_level(logging.WARNING):
        entity, _ = _preset_entity(shape, install)
        entity.async_get_last_state = AsyncMock(
            return_value=State("climate.x", "off", {ATTR_TEMPERATURE: stored})
        )
        entity.async_get_last_extra_data = AsyncMock(return_value=None)
        await entity._async_restore_state()
        assert shape.read(entity, "target_temperature") == stored
    _assert_quiet(caplog)
