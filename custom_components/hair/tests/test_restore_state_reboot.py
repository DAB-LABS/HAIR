"""Device Settings + power sensor (v0.9.9), commit 4/6: restore on reboot.

Tests the RestoreEntity mixin wired into the five entity platforms that
mirror IR device state (switch, light, fan, media_player, climate).
Contracts under test (docs/internal/plans/device-settings-power-sensor-coding-plan.md,
"Commit 4 -- restore on reboot"):

- No prior state (fresh install, or the platform never restored
  anything before) leaves __init__'s defaults untouched.
- A prior state seeds assumed state: boolean platforms restore
  is_on; media_player clamps to plain ON/OFF (never a transient
  PLAYING/PAUSED/IDLE); climate restores mode, setpoint, fan, and
  swing.
- Matrix-mode climate re-validates the restored combination against
  the CURRENT matrix via resolve_cell. A combination that no longer
  resolves (a stale attribute set from before a re-fit/re-adopt) is
  discarded WHOLESALE -- the entity falls back to the blank state
  __init__ already set, not a partial apply and not an exception.
- A garbage/unknown hvac_mode string does not raise; it's treated
  like "no usable state" and discarded.
- Restore never sends IR (no manager call) -- it is pure bookkeeping,
  same contract as the power-verdict handlers in commit 3.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
    ATTR_TEMPERATURE,
    HVACMode,
)
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.core import State

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.fan import HAIRFanEntity
from custom_components.hair.light import HAIRLightEntity
from custom_components.hair.media_player import HAIRMediaPlayerEntity
from custom_components.hair.models import EntityConfig, IRDevice
from custom_components.hair.switch import HAIRSwitchEntity
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _device(
    device_type: DeviceType,
    device_id: str = "dev-1",
    entity_config: EntityConfig | None = None,
    **overrides,
) -> IRDevice:
    return IRDevice(
        id=device_id,
        name="Test Device",
        device_type=device_type,
        manufacturer="TestCo",
        model="X100",
        emitter_entity_ids=["infrared.test"],
        entity_config=entity_config or EntityConfig(),
        **overrides,
    )


def _manager() -> MagicMock:
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    return mgr


async def _restored_entity(entity_cls, device, last_state, manager=None):
    """Construct an entity, stub async_get_last_state, and run
    _async_restore_state() directly -- no dispatcher wiring needed
    since restore doesn't touch it.
    """
    mgr = manager if manager is not None else _manager()
    entity = entity_cls(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.async_get_last_state = AsyncMock(return_value=last_state)
    await entity._async_restore_state()
    return entity, mgr


# ---------------------------------------------------------------------------
# Boolean platforms: switch, light, fan (all use self._is_on)
# ---------------------------------------------------------------------------

BOOLEAN_PLATFORMS = [
    pytest.param(HAIRSwitchEntity, DeviceType.SWITCH, id="switch"),
    pytest.param(HAIRLightEntity, DeviceType.LIGHT, id="light"),
    pytest.param(HAIRFanEntity, DeviceType.FAN, id="fan"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_no_last_state_leaves_default(entity_cls, device_type):
    entity, mgr = await _restored_entity(entity_cls, _device(device_type), None)
    assert entity.is_on is False
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_restores_on(entity_cls, device_type):
    last = State("switch.x", "on", {})
    entity, mgr = await _restored_entity(entity_cls, _device(device_type), last)
    assert entity.is_on is True
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_restores_off(entity_cls, device_type):
    last = State("switch.x", "off", {})
    entity, _ = await _restored_entity(entity_cls, _device(device_type), last)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# media_player: clamped to plain ON/OFF only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_media_player_no_last_state_leaves_default():
    entity, _ = await _restored_entity(
        HAIRMediaPlayerEntity, _device(DeviceType.MEDIA_PLAYER), None
    )
    assert entity.state == MediaPlayerState.OFF


@pytest.mark.asyncio
async def test_media_player_restores_on():
    last = State("media_player.x", "on", {})
    entity, _ = await _restored_entity(
        HAIRMediaPlayerEntity, _device(DeviceType.MEDIA_PLAYER), last
    )
    assert entity.state == MediaPlayerState.ON


@pytest.mark.asyncio
async def test_media_player_playing_clamps_to_off():
    # HAIR has no way to know whether a restored PLAYING state still
    # holds, so anything other than literal "on" clamps to OFF.
    last = State("media_player.x", "playing", {})
    entity, _ = await _restored_entity(
        HAIRMediaPlayerEntity, _device(DeviceType.MEDIA_PLAYER), last
    )
    assert entity.state == MediaPlayerState.OFF


# ---------------------------------------------------------------------------
# climate: preset mode
# ---------------------------------------------------------------------------


def _preset_climate_device(device_id: str = "dev-1") -> IRDevice:
    return _device(
        DeviceType.AC,
        device_id=device_id,
        entity_config=EntityConfig(hvac_modes=["cool", "heat"]),
    )


@pytest.mark.asyncio
async def test_preset_climate_no_last_state_leaves_default():
    entity, _ = await _restored_entity(
        HAIRClimateEntity, _preset_climate_device(), None
    )
    assert entity.hvac_mode == HVACMode.OFF
    assert entity._last_active_hvac_mode is None


@pytest.mark.asyncio
async def test_preset_climate_restores_mode_setpoint_and_fan():
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 21.0, ATTR_FAN_MODE: "low"},
    )
    entity, mgr = await _restored_entity(HAIRClimateEntity, _preset_climate_device(), last)
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.target_temperature == 21.0
    assert entity.fan_mode == "low"
    assert entity._last_active_hvac_mode == HVACMode.COOL
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_preset_climate_restores_off_does_not_set_last_active():
    last = State("climate.x", "off", {})
    entity, _ = await _restored_entity(HAIRClimateEntity, _preset_climate_device(), last)
    assert entity.hvac_mode == HVACMode.OFF
    assert entity._last_active_hvac_mode is None


@pytest.mark.asyncio
async def test_preset_climate_garbage_mode_does_not_raise():
    last = State("climate.x", "not-a-real-mode", {})
    entity, _ = await _restored_entity(HAIRClimateEntity, _preset_climate_device(), last)
    # Discarded like "no usable state" -- __init__'s defaults stand.
    assert entity.hvac_mode == HVACMode.OFF
    assert entity._last_active_hvac_mode is None


# ---------------------------------------------------------------------------
# climate: matrix mode
# ---------------------------------------------------------------------------

P_OFF = "P-OFF"


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "heat"],
        fan_modes=["auto", "low"],
        swing_modes=["swing", "fixed"],
        off=P_OFF,
        on=None,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, swing="swing",
                        pronto="P-C-A-22-S"),
        ],
    )


def _matrix_climate_device(device_id: str = "dev-1") -> IRDevice:
    return _device(DeviceType.AC, device_id=device_id, climate_matrix=True)


async def _restored_matrix_entity(last_state, matrix=None):
    mgr = _manager()
    entity = HAIRClimateEntity(_matrix_climate_device(), mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity._matrix = matrix if matrix is not None else _matrix()
    entity.async_get_last_state = AsyncMock(return_value=last_state)
    await entity._async_restore_state()
    return entity, mgr


@pytest.mark.asyncio
async def test_matrix_climate_no_last_state_leaves_default():
    entity, _ = await _restored_matrix_entity(None)
    assert entity.hvac_mode == HVACMode.OFF
    assert entity._swing_mode is None


@pytest.mark.asyncio
async def test_matrix_climate_restores_combination_that_resolves():
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 22.0, ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity, mgr = await _restored_matrix_entity(last)
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "auto"
    assert entity._swing_mode == "swing"
    assert entity.target_temperature == 22.0
    assert entity._last_active_hvac_mode == HVACMode.COOL
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_matrix_climate_stale_mode_falls_back_to_blank():
    # The restored state is "cool", but the CURRENT matrix (as if a
    # re-fit/re-adopt just ran) no longer declares a "cool" branch --
    # resolve_cell always falls back for fan/swing/temp within an
    # existing mode subtree, so the only real "no longer resolves"
    # case is a mode that dropped out of the file entirely. Must
    # discard wholesale, not partially apply, and must not raise.
    stale_matrix = _matrix()
    stale_matrix.modes = ["heat"]
    stale_matrix.cells = [
        ClimateCell(mode="heat", fan="auto", temp=22.0, pronto="P-H-A-22"),
    ]
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 22.0, ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity, _ = await _restored_matrix_entity(last, matrix=stale_matrix)
    assert entity.hvac_mode == HVACMode.OFF
    assert entity.fan_mode is None
    assert entity._swing_mode is None
    assert entity._last_active_hvac_mode is None


@pytest.mark.asyncio
async def test_matrix_climate_restores_off_without_resolve_check():
    last = State("climate.x", "off", {})
    entity, _ = await _restored_matrix_entity(last)
    assert entity.hvac_mode == HVACMode.OFF
    assert entity._last_active_hvac_mode is None


# ---------------------------------------------------------------------------
# async_added_to_hass ordering: restore runs, then dispatcher connects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_added_to_hass_restores_before_dispatcher_connects(monkeypatch):
    """Simulated restart through the real lifecycle entry point.

    Confirms _async_restore_state actually runs as part of
    async_added_to_hass (not just when called directly, as the tests
    above do for isolation) and that it completes before the power
    verdict subscription is wired up -- the ordering the coding plan
    calls for, so a startup verdict corrects what restore just set
    rather than racing it.
    """
    last = State("switch.x", "on", {})
    mgr = _manager()
    device = _device(DeviceType.SWITCH)
    entity = HAIRSwitchEntity(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.async_get_last_state = AsyncMock(return_value=last)

    calls: list[str] = []
    orig_restore = entity._async_restore_state

    async def _tracked_restore():
        calls.append("restore")
        await orig_restore()

    entity._async_restore_state = _tracked_restore

    import custom_components.hair.switch as switch_module

    def _fake_connect(hass_arg, signal, callback_fn):
        calls.append("dispatcher_connect")
        return MagicMock()

    monkeypatch.setattr(switch_module, "async_dispatcher_connect", _fake_connect)

    await entity.async_added_to_hass()

    assert calls == ["restore", "dispatcher_connect"]
    assert entity.is_on is True
