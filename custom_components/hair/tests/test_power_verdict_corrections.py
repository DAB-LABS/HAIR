"""Device Settings + power sensor (v0.9.9), commit 3/6: entity corrections.

Tests SIGNAL_POWER_VERDICT handling wired into the five entity platforms
that mirror IR device state (switch, light, fan, media_player, climate).
Contracts under test (docs/internal/plans/device-settings-power-sensor.md):

- A verdict is bookkeeping only -- it NEVER sends IR (no manager call),
  only corrects assumed state and calls async_write_ha_state.
- "off" always sets the entity to its off state.
- "on" while already off restores prior state: plain on for the
  boolean platforms (switch/light/fan) and the ON state for
  media_player; climate restores the last non-off hvac_mode, falling
  back to AUTO if the entity has never been on (non-matrix climate;
  matrix-mode fallback is covered separately in
  test_climate_entity_matrix.py's own suite).
- A verdict for a different device_id is ignored (no state change, no
  write).
- async_will_remove_from_hass disconnects the dispatcher subscription.
- A verdict arriving after a HAIR-initiated send always applies --
  there is no additional "send wins" guard in the entity handler
  itself; power_monitor.py is what decides when to dispatch.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.components.media_player import MediaPlayerState

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.fan import HAIRFanEntity
from custom_components.hair.light import HAIRLightEntity
from custom_components.hair.media_player import HAIRMediaPlayerEntity
from custom_components.hair.models import EntityConfig, IRDevice
from custom_components.hair.switch import HAIRSwitchEntity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _device(
    device_type: DeviceType,
    device_id: str = "dev-1",
    entity_config: EntityConfig | None = None,
) -> IRDevice:
    return IRDevice(
        id=device_id,
        name="Test Device",
        device_type=device_type,
        manufacturer="TestCo",
        model="X100",
        emitter_entity_ids=["infrared.test"],
        entity_config=entity_config or EntityConfig(),
    )


def _climate_device(device_id: str = "dev-1") -> IRDevice:
    # Preset-mode climate (climate_matrix defaults to False): two
    # discrete modes so hvac_modes offers something besides OFF/AUTO.
    return _device(
        DeviceType.AC,
        device_id=device_id,
        entity_config=EntityConfig(hvac_modes=["cool", "heat"]),
    )


def _manager() -> MagicMock:
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    return mgr


async def _wired_entity(entity_cls, module_path, device, manager=None):
    """Construct an entity and run async_added_to_hass, capturing the
    SIGNAL_POWER_VERDICT callback it registered.

    Mirrors test_power_monitor.py's ``_fake_track`` technique: patch the
    platform module's ``async_dispatcher_connect`` with a side_effect
    that stashes the callback instead of conftest's bare MagicMock, so
    the test can invoke it directly the way power_monitor.py would.
    """
    mgr = manager if manager is not None else _manager()
    entity = entity_cls(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    captured: dict[str, object] = {}

    def _fake_connect(hass_arg, signal, callback_fn):
        captured["callback"] = callback_fn
        return MagicMock()

    with patch(f"{module_path}.async_dispatcher_connect", side_effect=_fake_connect):
        await entity.async_added_to_hass()
    return entity, captured["callback"], mgr


# ---------------------------------------------------------------------------
# Boolean platforms: switch, light, fan (all use self._is_on)
# ---------------------------------------------------------------------------

BOOLEAN_PLATFORMS = [
    pytest.param(HAIRSwitchEntity, "custom_components.hair.switch",
                 DeviceType.SWITCH, id="switch"),
    pytest.param(HAIRLightEntity, "custom_components.hair.light",
                 DeviceType.LIGHT, id="light"),
    pytest.param(HAIRFanEntity, "custom_components.hair.fan",
                 DeviceType.FAN, id="fan"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,module_path,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_off_verdict_sets_assumed_off(entity_cls, module_path, device_type):
    entity, callback, mgr = await _wired_entity(
        entity_cls, module_path, _device(device_type)
    )
    entity._is_on = True
    callback("dev-1", "off")
    assert entity.is_on is False
    entity.async_write_ha_state.assert_called()
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,module_path,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_on_verdict_restores_assumed_on(entity_cls, module_path, device_type):
    entity, callback, mgr = await _wired_entity(
        entity_cls, module_path, _device(device_type)
    )
    entity._is_on = False
    callback("dev-1", "on")
    assert entity.is_on is True
    entity.async_write_ha_state.assert_called()
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,module_path,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_verdict_for_other_device_ignored(entity_cls, module_path, device_type):
    entity, callback, _ = await _wired_entity(
        entity_cls, module_path, _device(device_type)
    )
    entity._is_on = True
    entity.async_write_ha_state.reset_mock()
    callback("some-other-device", "off")
    assert entity.is_on is True
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,module_path,device_type", BOOLEAN_PLATFORMS)
async def test_boolean_will_remove_disconnects(entity_cls, module_path, device_type):
    entity, _callback, _ = await _wired_entity(
        entity_cls, module_path, _device(device_type)
    )
    unsub = entity._power_verdict_unsub
    assert unsub is not None
    await entity.async_will_remove_from_hass()
    unsub.assert_called_once()
    assert entity._power_verdict_unsub is None


@pytest.mark.asyncio
async def test_switch_verdict_overrides_prior_send_state():
    """A verdict arriving after a HAIR send always applies: there is no
    "send wins" guard in the handler, power_monitor.py owns timing."""
    entity, callback, _ = await _wired_entity(
        HAIRSwitchEntity, "custom_components.hair.switch", _device(DeviceType.SWITCH)
    )
    entity._is_on = True  # as if a HAIR turn_on just landed
    callback("dev-1", "off")
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Media player (ON/OFF states, not a bare bool)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_media_player_off_verdict_sets_state_off():
    entity, callback, mgr = await _wired_entity(
        HAIRMediaPlayerEntity,
        "custom_components.hair.media_player",
        _device(DeviceType.MEDIA_PLAYER),
    )
    entity._state = MediaPlayerState.PLAYING
    callback("dev-1", "off")
    assert entity.state == MediaPlayerState.OFF
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_media_player_on_verdict_sets_state_on():
    entity, callback, mgr = await _wired_entity(
        HAIRMediaPlayerEntity,
        "custom_components.hair.media_player",
        _device(DeviceType.MEDIA_PLAYER),
    )
    entity._state = MediaPlayerState.OFF
    callback("dev-1", "on")
    assert entity.state == MediaPlayerState.ON
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_media_player_verdict_for_other_device_ignored():
    entity, callback, _ = await _wired_entity(
        HAIRMediaPlayerEntity,
        "custom_components.hair.media_player",
        _device(DeviceType.MEDIA_PLAYER),
    )
    entity._state = MediaPlayerState.PLAYING
    entity.async_write_ha_state.reset_mock()
    callback("other-device", "off")
    assert entity.state == MediaPlayerState.PLAYING
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_media_player_will_remove_disconnects():
    entity, _callback, _ = await _wired_entity(
        HAIRMediaPlayerEntity,
        "custom_components.hair.media_player",
        _device(DeviceType.MEDIA_PLAYER),
    )
    unsub = entity._power_verdict_unsub
    assert unsub is not None
    await entity.async_will_remove_from_hass()
    unsub.assert_called_once()
    assert entity._power_verdict_unsub is None


# ---------------------------------------------------------------------------
# Climate (hvac_mode, with _last_active_hvac_mode bookkeeping)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_climate_off_verdict_captures_active_mode_and_sets_off():
    entity, callback, mgr = await _wired_entity(
        HAIRClimateEntity, "custom_components.hair.climate", _climate_device()
    )
    entity._hvac_mode = HVACMode.COOL
    callback("dev-1", "off")
    assert entity.hvac_mode == HVACMode.OFF
    assert entity._last_active_hvac_mode == HVACMode.COOL
    entity.async_write_ha_state.assert_called()
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_climate_on_verdict_restores_last_active_mode():
    entity, callback, _ = await _wired_entity(
        HAIRClimateEntity, "custom_components.hair.climate", _climate_device()
    )
    entity._hvac_mode = HVACMode.OFF
    entity._last_active_hvac_mode = HVACMode.COOL
    callback("dev-1", "on")
    assert entity.hvac_mode == HVACMode.COOL


@pytest.mark.asyncio
async def test_climate_on_verdict_never_been_on_falls_back_to_auto():
    entity, callback, _ = await _wired_entity(
        HAIRClimateEntity, "custom_components.hair.climate", _climate_device()
    )
    assert entity._hvac_mode == HVACMode.OFF
    assert entity._last_active_hvac_mode is None
    callback("dev-1", "on")
    assert entity.hvac_mode == HVACMode.AUTO


@pytest.mark.asyncio
async def test_climate_on_verdict_while_already_on_is_noop_for_mode():
    entity, callback, _ = await _wired_entity(
        HAIRClimateEntity, "custom_components.hair.climate", _climate_device()
    )
    entity._hvac_mode = HVACMode.HEAT
    callback("dev-1", "on")
    assert entity.hvac_mode == HVACMode.HEAT


@pytest.mark.asyncio
async def test_climate_verdict_for_other_device_ignored():
    entity, callback, _ = await _wired_entity(
        HAIRClimateEntity, "custom_components.hair.climate", _climate_device()
    )
    entity._hvac_mode = HVACMode.COOL
    entity.async_write_ha_state.reset_mock()
    callback("some-other-device", "off")
    assert entity.hvac_mode == HVACMode.COOL
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_climate_will_remove_disconnects():
    entity, _callback, _ = await _wired_entity(
        HAIRClimateEntity, "custom_components.hair.climate", _climate_device()
    )
    unsub = entity._power_verdict_unsub
    assert unsub is not None
    await entity.async_will_remove_from_hass()
    unsub.assert_called_once()
    assert entity._power_verdict_unsub is None
