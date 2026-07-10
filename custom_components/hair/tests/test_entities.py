"""Tests for HAIR entity platforms (remote, media_player, climate, fan)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.fan import FanEntityFeature
from homeassistant.components.light import ColorMode
from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

from custom_components.hair.climate import (
    HAIRClimateEntity,
)
from custom_components.hair.const import (
    DOMAIN,
    CommandCategory,
    CommandSource,
    DeviceType,
)
from custom_components.hair.cover import HAIRCoverEntity
from custom_components.hair.fan import HAIRFanEntity
from custom_components.hair.light import HAIRLightEntity
from custom_components.hair.media_player import HAIRMediaPlayerEntity
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.remote import HAIRRemoteEntity, _humanise_device_type
from custom_components.hair.switch import HAIRSwitchEntity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cmd(cmd_id: str, name: str, category=CommandCategory.CUSTOM) -> IRCommand:
    """Create a minimal IRCommand."""
    return IRCommand(
        id=cmd_id,
        name=name,
        category=category,
        source=CommandSource.CAPTURED,
        protocol="NEC",
        code="0x1234",
    )


def _device(
    device_id: str = "dev-1",
    name: str = "Test Device",
    device_type: DeviceType = DeviceType.MEDIA_PLAYER,
    commands: list[IRCommand] | None = None,
    entity_config: EntityConfig | None = None,
) -> IRDevice:
    """Create a test IRDevice."""
    return IRDevice(
        id=device_id,
        name=name,
        device_type=device_type,
        manufacturer="TestCo",
        model="X100",
        emitter_entity_ids=["infrared.test"],
        commands=commands or [],
        entity_config=entity_config or EntityConfig(),
    )


def _manager() -> MagicMock:
    """Create a mock device manager with async_send_command."""
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    return mgr


def _patch_write_state(entity):
    """Patch async_write_ha_state on an entity instance (stub base has no impl).

    Also sets ``entity.hass`` to a sentinel so the v0.3.3 hass-None guard in
    ``update_device`` (which mirrors the real HA Entity lifecycle) doesn't
    short-circuit the call.  Tests that want to exercise the pre-registration
    race should construct the entity without ``_patch_write_state`` (see
    ``test_entity_lifecycle_race.py``).
    """
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()


# ===========================================================================
# Remote entity tests
# ===========================================================================


class TestHAIRRemoteEntity:

    def test_unique_id_and_device_info(self):
        device = _device()
        entity = HAIRRemoteEntity(device, _manager())
        assert entity._attr_unique_id == "hair_dev-1_remote"
        info = entity.device_info
        assert (DOMAIN, "dev-1") in info["identifiers"]
        assert info["name"] == "Test Device"
        assert info["manufacturer"] == "TestCo"
        assert info["model"] == "X100"

    def test_device_info_fallback_model(self):
        device = _device(device_type=DeviceType.AC)
        device.manufacturer = None
        device.model = None
        entity = HAIRRemoteEntity(device, _manager())
        info = entity.device_info
        assert info["manufacturer"] == "HAIR"
        assert info["model"] == "Air Conditioner"

    def test_is_on_default_true(self):
        entity = HAIRRemoteEntity(_device(), _manager())
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_on_sends_power_on(self):
        power_cmd = _cmd("c1", "Power On", CommandCategory.POWER)
        device = _device(commands=[power_cmd])
        mgr = _manager()
        entity = HAIRRemoteEntity(device, mgr)
        _patch_write_state(entity)

        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_on is True
        entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_sends_power_off(self):
        power_cmd = _cmd("c2", "Power Off", CommandCategory.POWER)
        device = _device(commands=[power_cmd])
        mgr = _manager()
        entity = HAIRRemoteEntity(device, mgr)
        _patch_write_state(entity)

        await entity.async_turn_off()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c2")
        assert entity._is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_falls_back_to_power(self):
        """If no 'Power On' exists, falls back to 'Power'."""
        power_cmd = _cmd("c3", "Power", CommandCategory.POWER)
        device = _device(commands=[power_cmd])
        mgr = _manager()
        entity = HAIRRemoteEntity(device, mgr)
        _patch_write_state(entity)

        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c3")

    @pytest.mark.asyncio
    async def test_send_command_list(self):
        cmds = [
            _cmd("c1", "Volume Up"),
            _cmd("c2", "Volume Down"),
        ]
        device = _device(commands=cmds)
        mgr = _manager()
        entity = HAIRRemoteEntity(device, mgr)

        await entity.async_send_command(["Volume Up", "Volume Down"])
        assert mgr.async_send_command.await_count == 2
        mgr.async_send_command.assert_any_await("dev-1", "c1")
        mgr.async_send_command.assert_any_await("dev-1", "c2")

    @pytest.mark.asyncio
    async def test_send_named_missing_command_logs_warning(self):
        device = _device(commands=[])
        mgr = _manager()
        entity = HAIRRemoteEntity(device, mgr)

        with patch("custom_components.hair.remote._LOGGER") as mock_log:
            await entity._send_named("Nonexistent")
            mock_log.warning.assert_called_once()
        mgr.async_send_command.assert_not_awaited()

    def test_extra_state_attributes(self):
        cmds = [_cmd("c1", "Power"), _cmd("c2", "Mute")]
        device = _device(commands=cmds)
        entity = HAIRRemoteEntity(device, _manager())
        attrs = entity.extra_state_attributes
        assert attrs["device_id"] == "dev-1"
        assert set(attrs["available_commands"]) == {"Power", "Mute"}
        assert attrs["device_type"] == "media_player"

    def test_update_device(self):
        device = _device()
        entity = HAIRRemoteEntity(device, _manager())
        _patch_write_state(entity)

        new_device = _device(name="Renamed TV")
        entity.update_device(new_device)
        assert entity._device.name == "Renamed TV"
        entity.async_write_ha_state.assert_called_once()

    def test_humanise_device_type(self):
        assert _humanise_device_type(DeviceType.MEDIA_PLAYER) == "Media Player"
        assert _humanise_device_type(DeviceType.AC) == "Air Conditioner"
        assert _humanise_device_type(DeviceType.FAN) == "Fan"
        assert _humanise_device_type(DeviceType.LIGHT) == "Light"
        assert _humanise_device_type(DeviceType.SWITCH) == "Switch"
        assert _humanise_device_type(DeviceType.SCREEN) == "Screen / Shade"
        assert _humanise_device_type(DeviceType.OTHER) == "IR Device"


# ===========================================================================
# Media player entity tests
# ===========================================================================


class TestHAIRMediaPlayerEntity:

    def _make(self, command_mapping=None, commands=None, device_type=DeviceType.MEDIA_PLAYER):
        """Build a media player entity with the given mapping and commands."""
        mapping = command_mapping or {}
        cmds = commands or []
        config = EntityConfig(platform="media_player", command_mapping=mapping)
        device = _device(
            device_type=device_type,
            commands=cmds,
            entity_config=config,
        )
        mgr = _manager()
        entity = HAIRMediaPlayerEntity(device, mgr)
        _patch_write_state(entity)
        return entity, mgr

    def test_unique_id_and_name(self):
        entity, _ = self._make()
        assert entity._attr_unique_id == "hair_dev-1_media_player"
        assert entity._attr_name is None  # inherits device name

    def test_device_info(self):
        entity, _ = self._make()
        info = entity.device_info
        assert (DOMAIN, "dev-1") in info["identifiers"]
        assert info["model"] == "X100"

    def test_supported_features_empty_mapping(self):
        entity, _ = self._make(command_mapping={})
        features = entity.supported_features
        assert int(features) == 0

    def test_supported_features_full_mapping(self):
        entity, _ = self._make(command_mapping={
            "turn_on": "Power On",
            "turn_off": "Power Off",
            "volume_up": "Vol+",
            "volume_down": "Vol-",
            "mute": "Mute",
            "select_source": "Source",
        })
        f = entity.supported_features
        assert int(f) & MediaPlayerEntityFeature.TURN_ON
        assert int(f) & MediaPlayerEntityFeature.TURN_OFF
        assert int(f) & MediaPlayerEntityFeature.VOLUME_STEP
        assert int(f) & MediaPlayerEntityFeature.VOLUME_MUTE
        assert int(f) & MediaPlayerEntityFeature.SELECT_SOURCE

    def test_supported_features_power_toggle(self):
        """power_toggle alone should enable both TURN_ON and TURN_OFF."""
        entity, _ = self._make(command_mapping={"power_toggle": "Power"})
        f = entity.supported_features
        assert int(f) & MediaPlayerEntityFeature.TURN_ON
        assert int(f) & MediaPlayerEntityFeature.TURN_OFF

    def test_initial_state(self):
        entity, _ = self._make()
        assert entity.state == MediaPlayerState.OFF
        assert entity.volume_level == 0.5
        assert entity.is_volume_muted is False

    @pytest.mark.asyncio
    async def test_turn_on(self):
        power_cmd = _cmd("c1", "Power On")
        entity, mgr = self._make(
            command_mapping={"turn_on": "Power On"},
            commands=[power_cmd],
        )
        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._state == MediaPlayerState.ON

    @pytest.mark.asyncio
    async def test_turn_off(self):
        power_cmd = _cmd("c1", "Power Off")
        entity, mgr = self._make(
            command_mapping={"turn_off": "Power Off"},
            commands=[power_cmd],
        )
        await entity.async_turn_off()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._state == MediaPlayerState.OFF

    @pytest.mark.asyncio
    async def test_volume_up(self):
        vol_cmd = _cmd("c1", "Vol+")
        entity, mgr = self._make(
            command_mapping={"volume_up": "Vol+"},
            commands=[vol_cmd],
        )
        entity._volume_level = 0.5
        await entity.async_volume_up()
        mgr.async_send_command.assert_awaited_once()
        assert entity._volume_level == pytest.approx(0.55)

    @pytest.mark.asyncio
    async def test_volume_down(self):
        vol_cmd = _cmd("c1", "Vol-")
        entity, _mgr = self._make(
            command_mapping={"volume_down": "Vol-"},
            commands=[vol_cmd],
        )
        entity._volume_level = 0.5
        await entity.async_volume_down()
        assert entity._volume_level == pytest.approx(0.45)

    @pytest.mark.asyncio
    async def test_volume_clamps(self):
        vol_up_cmd = _cmd("c1", "Vol+")
        vol_down_cmd = _cmd("c2", "Vol-")
        entity, _ = self._make(
            command_mapping={"volume_up": "Vol+", "volume_down": "Vol-"},
            commands=[vol_up_cmd, vol_down_cmd],
        )
        entity._volume_level = 1.0
        await entity.async_volume_up()
        assert entity._volume_level == 1.0

        entity._volume_level = 0.0
        await entity.async_volume_down()
        assert entity._volume_level == 0.0

    @pytest.mark.asyncio
    async def test_mute_volume(self):
        mute_cmd = _cmd("c1", "Mute")
        entity, mgr = self._make(
            command_mapping={"mute": "Mute"},
            commands=[mute_cmd],
        )
        await entity.async_mute_volume(True)
        mgr.async_send_command.assert_awaited_once()
        assert entity._is_muted is True

    def test_supported_features_play_pause_stop(self):
        entity, _ = self._make(command_mapping={
            "play": "Play",
            "pause": "Pause",
            "stop": "Stop",
        })
        f = entity.supported_features
        assert int(f) & MediaPlayerEntityFeature.PLAY
        assert int(f) & MediaPlayerEntityFeature.PAUSE
        assert int(f) & MediaPlayerEntityFeature.STOP

    @pytest.mark.asyncio
    async def test_media_play(self):
        play_cmd = _cmd("c1", "Play")
        entity, mgr = self._make(
            command_mapping={"play": "Play"},
            commands=[play_cmd],
        )
        await entity.async_media_play()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._state == MediaPlayerState.PLAYING

    @pytest.mark.asyncio
    async def test_media_pause(self):
        pause_cmd = _cmd("c1", "Pause")
        entity, mgr = self._make(
            command_mapping={"pause": "Pause"},
            commands=[pause_cmd],
        )
        await entity.async_media_pause()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._state == MediaPlayerState.PAUSED

    @pytest.mark.asyncio
    async def test_media_stop(self):
        stop_cmd = _cmd("c1", "Stop")
        entity, mgr = self._make(
            command_mapping={"stop": "Stop"},
            commands=[stop_cmd],
        )
        await entity.async_media_stop()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._state == MediaPlayerState.IDLE

    def test_update_device(self):
        entity, _ = self._make()
        new_device = _device(name="Updated Media Player")
        entity.update_device(new_device)
        assert entity._device.name == "Updated Media Player"
        entity.async_write_ha_state.assert_called()


# ===========================================================================
# Climate entity tests
# ===========================================================================


class TestHAIRClimateEntity:

    def _make(
        self,
        command_mapping=None,
        commands=None,
        temperature_presets=None,
        hvac_modes=None,
        fan_modes=None,
    ):
        mapping = command_mapping or {}
        cmds = commands or []
        config = EntityConfig(
            platform="climate",
            command_mapping=mapping,
            temperature_presets=temperature_presets,
            hvac_modes=hvac_modes,
            fan_modes=fan_modes,
        )
        device = _device(
            device_type=DeviceType.AC,
            commands=cmds,
            entity_config=config,
        )
        mgr = _manager()
        entity = HAIRClimateEntity(device, mgr)
        _patch_write_state(entity)
        return entity, mgr

    def test_unique_id(self):
        entity, _ = self._make()
        assert entity._attr_unique_id == "hair_dev-1_climate"

    def test_device_info_fallback(self):
        entity, _ = self._make()
        info = entity.device_info
        assert info["model"] == "X100"

    def test_supported_features_base(self):
        """All climate entities get TURN_ON and TURN_OFF."""
        entity, _ = self._make()
        f = int(entity.supported_features)
        assert f & ClimateEntityFeature.TURN_ON
        assert f & ClimateEntityFeature.TURN_OFF

    def test_supported_features_with_fan_modes(self):
        entity, _ = self._make(fan_modes=["low", "high"])
        f = int(entity.supported_features)
        assert f & ClimateEntityFeature.FAN_MODE

    def test_supported_features_with_temp_presets(self):
        entity, _ = self._make(temperature_presets=[68, 72, 76])
        f = int(entity.supported_features)
        assert f & ClimateEntityFeature.TARGET_TEMPERATURE

    def test_hvac_modes_always_includes_off(self):
        entity, _ = self._make(hvac_modes=["cool", "heat"])
        modes = entity.hvac_modes
        assert modes[0] == HVACMode.OFF
        assert HVACMode.COOL in modes
        assert HVACMode.HEAT in modes

    def test_hvac_modes_skips_invalid(self):
        entity, _ = self._make(hvac_modes=["cool", "bogus_mode"])
        modes = entity.hvac_modes
        assert HVACMode.COOL in modes
        assert len(modes) == 2  # OFF + cool

    def test_min_max_temp_from_presets(self):
        entity, _ = self._make(temperature_presets=[60, 68, 72, 80])
        assert entity.min_temp == 60.0
        assert entity.max_temp == 80.0

    def test_min_max_temp_defaults(self):
        entity, _ = self._make()
        assert entity.min_temp == 60.0
        assert entity.max_temp == 86.0

    def test_fan_modes_property(self):
        entity, _ = self._make(fan_modes=["low", "medium", "high"])
        assert entity.fan_modes == ["low", "medium", "high"]

    def test_fan_modes_none_when_empty(self):
        entity, _ = self._make()
        assert entity.fan_modes is None

    def test_initial_state(self):
        entity, _ = self._make()
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.target_temperature is None
        assert entity.fan_mode is None

    @pytest.mark.asyncio
    async def test_set_hvac_mode_off(self):
        off_cmd = _cmd("c1", "Power Off")
        entity, mgr = self._make(
            command_mapping={"turn_off": "Power Off"},
            commands=[off_cmd],
        )
        entity._hvac_mode = HVACMode.COOL
        await entity.async_set_hvac_mode(HVACMode.OFF)
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._hvac_mode == HVACMode.OFF

    @pytest.mark.asyncio
    async def test_set_hvac_mode_cool(self):
        cool_cmd = _cmd("c1", "Mode Cool")
        entity, mgr = self._make(
            command_mapping={"mode_cool": "Mode Cool"},
            commands=[cool_cmd],
        )
        await entity.async_set_hvac_mode(HVACMode.COOL)
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_set_hvac_mode_fallback_to_power_on(self):
        """If no mode-specific command, falls back to turn_on/power_toggle."""
        power_cmd = _cmd("c1", "Power On")
        entity, mgr = self._make(
            command_mapping={"turn_on": "Power On"},
            commands=[power_cmd],
        )
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._hvac_mode == HVACMode.HEAT

    @pytest.mark.asyncio
    async def test_set_temperature_snaps_to_preset(self):
        cmds = [_cmd("c72", "Temp 72"), _cmd("c76", "Temp 76")]
        entity, mgr = self._make(
            command_mapping={"temp_72": "Temp 72", "temp_76": "Temp 76"},
            commands=cmds,
            temperature_presets=[72, 76],
        )
        await entity.async_set_temperature(temperature=73)
        # Should snap to 72 (nearest)
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c72")
        assert entity._target_temperature == 72.0

    @pytest.mark.asyncio
    async def test_set_temperature_no_target_noop(self):
        entity, mgr = self._make()
        await entity.async_set_temperature()
        mgr.async_send_command.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_set_fan_mode(self):
        fan_cmd = _cmd("c1", "Fan Low")
        entity, mgr = self._make(
            command_mapping={"fan_low": "Fan Low"},
            commands=[fan_cmd],
            fan_modes=["low", "high"],
        )
        await entity.async_set_fan_mode("low")
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._fan_mode == "low"

    @pytest.mark.asyncio
    async def test_turn_on_sets_auto_when_off(self):
        power_cmd = _cmd("c1", "Power On")
        entity, mgr = self._make(
            command_mapping={"turn_on": "Power On"},
            commands=[power_cmd],
        )
        assert entity._hvac_mode == HVACMode.OFF
        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once()
        assert entity._hvac_mode == HVACMode.AUTO

    @pytest.mark.asyncio
    async def test_turn_on_preserves_existing_mode(self):
        power_cmd = _cmd("c1", "Power On")
        entity, _mgr = self._make(
            command_mapping={"turn_on": "Power On"},
            commands=[power_cmd],
        )
        entity._hvac_mode = HVACMode.COOL
        await entity.async_turn_on()
        assert entity._hvac_mode == HVACMode.COOL  # not overwritten

    @pytest.mark.asyncio
    async def test_turn_off(self):
        off_cmd = _cmd("c1", "Power Off")
        entity, _mgr = self._make(
            command_mapping={"turn_off": "Power Off"},
            commands=[off_cmd],
        )
        entity._hvac_mode = HVACMode.COOL
        await entity.async_turn_off()
        assert entity._hvac_mode == HVACMode.OFF

    def test_update_device(self):
        entity, _ = self._make()
        new_device = _device(name="Updated AC", device_type=DeviceType.AC)
        entity.update_device(new_device)
        assert entity._device.name == "Updated AC"
        entity.async_write_ha_state.assert_called()


# ===========================================================================
# Fan entity tests
# ===========================================================================


class TestHAIRFanEntity:

    def _make(self, command_mapping=None, commands=None):
        mapping = command_mapping or {}
        cmds = commands or []
        config = EntityConfig(platform="fan", command_mapping=mapping)
        device = _device(
            device_type=DeviceType.FAN,
            commands=cmds,
            entity_config=config,
        )
        mgr = _manager()
        entity = HAIRFanEntity(device, mgr)
        _patch_write_state(entity)
        return entity, mgr

    def test_unique_id(self):
        entity, _ = self._make()
        assert entity._attr_unique_id == "hair_dev-1_fan"

    def test_device_info(self):
        entity, _ = self._make()
        info = entity.device_info
        assert (DOMAIN, "dev-1") in info["identifiers"]

    def test_supported_features_base(self):
        """Always has TURN_ON and TURN_OFF."""
        entity, _ = self._make()
        f = int(entity.supported_features)
        assert f & FanEntityFeature.TURN_ON
        assert f & FanEntityFeature.TURN_OFF

    def test_supported_features_speed(self):
        entity, _ = self._make(command_mapping={"speed_up": "Speed+"})
        f = int(entity.supported_features)
        assert f & FanEntityFeature.SET_SPEED

    def test_supported_features_oscillate(self):
        entity, _ = self._make(command_mapping={"oscillate": "Oscillate"})
        f = int(entity.supported_features)
        assert f & FanEntityFeature.OSCILLATE

    def test_initial_state(self):
        entity, _ = self._make()
        assert entity.is_on is False
        assert entity.percentage is None
        assert entity.oscillating is False

    @pytest.mark.asyncio
    async def test_turn_on(self):
        power_cmd = _cmd("c1", "Power On")
        entity, mgr = self._make(
            command_mapping={"turn_on": "Power On"},
            commands=[power_cmd],
        )
        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_on is True

    @pytest.mark.asyncio
    async def test_turn_on_with_percentage(self):
        power_cmd = _cmd("c1", "Power On")
        entity, _ = self._make(
            command_mapping={"turn_on": "Power On"},
            commands=[power_cmd],
        )
        await entity.async_turn_on(percentage=75)
        assert entity._percentage == 75

    @pytest.mark.asyncio
    async def test_turn_off(self):
        off_cmd = _cmd("c1", "Power Off")
        entity, mgr = self._make(
            command_mapping={"turn_off": "Power Off"},
            commands=[off_cmd],
        )
        entity._is_on = True
        await entity.async_turn_off()
        mgr.async_send_command.assert_awaited_once()
        assert entity._is_on is False

    @pytest.mark.asyncio
    async def test_set_percentage_steps_up(self):
        speed_cmd = _cmd("c1", "Speed+")
        entity, mgr = self._make(
            command_mapping={"speed_up": "Speed+"},
            commands=[speed_cmd],
        )
        entity._percentage = 25
        await entity.async_set_percentage(75)
        # delta=50, steps = 50//25 = 2
        assert mgr.async_send_command.await_count == 2
        assert entity._percentage == 75

    @pytest.mark.asyncio
    async def test_set_percentage_steps_down(self):
        speed_cmd = _cmd("c1", "Speed-")
        entity, mgr = self._make(
            command_mapping={"speed_down": "Speed-"},
            commands=[speed_cmd],
        )
        entity._percentage = 75
        await entity.async_set_percentage(25)
        # delta=-50, steps = 50//25 = 2
        assert mgr.async_send_command.await_count == 2
        assert entity._percentage == 25

    @pytest.mark.asyncio
    async def test_set_percentage_no_change(self):
        entity, mgr = self._make(command_mapping={"speed_up": "Speed+"})
        entity._percentage = 50
        await entity.async_set_percentage(50)
        mgr.async_send_command.assert_not_awaited()
        assert entity._percentage == 50

    @pytest.mark.asyncio
    async def test_oscillate(self):
        osc_cmd = _cmd("c1", "Oscillate")
        entity, mgr = self._make(
            command_mapping={"oscillate": "Oscillate"},
            commands=[osc_cmd],
        )
        await entity.async_oscillate(True)
        mgr.async_send_command.assert_awaited_once()
        assert entity._oscillating is True

    def test_update_device(self):
        entity, _ = self._make()
        new_device = _device(name="Updated Fan", device_type=DeviceType.FAN)
        entity.update_device(new_device)
        assert entity._device.name == "Updated Fan"
        entity.async_write_ha_state.assert_called()


# ===========================================================================
# Light entity tests
# ===========================================================================


class TestHAIRLightEntity:

    def _make(self, command_mapping=None, commands=None):
        mapping = command_mapping or {}
        cmds = commands or []
        config = EntityConfig(platform="light", command_mapping=mapping)
        device = _device(
            device_type=DeviceType.LIGHT,
            commands=cmds,
            entity_config=config,
        )
        mgr = _manager()
        entity = HAIRLightEntity(device, mgr)
        _patch_write_state(entity)
        return entity, mgr

    def test_unique_id(self):
        entity, _ = self._make()
        assert entity._attr_unique_id == "hair_dev-1_light"

    def test_device_info(self):
        entity, _ = self._make()
        info = entity.device_info
        assert (DOMAIN, "dev-1") in info["identifiers"]

    def test_color_mode_onoff(self):
        entity, _ = self._make()
        assert entity.color_mode == ColorMode.ONOFF
        assert entity.supported_color_modes == {ColorMode.ONOFF}

    def test_color_mode_brightness(self):
        entity, _ = self._make(command_mapping={"brightness_up": "Bright+"})
        assert entity.color_mode == ColorMode.BRIGHTNESS
        assert entity.supported_color_modes == {ColorMode.BRIGHTNESS}

    def test_initial_state(self):
        entity, _ = self._make()
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on(self):
        on_cmd = _cmd("c1", "On")
        entity, mgr = self._make(
            command_mapping={"turn_on": "On"},
            commands=[on_cmd],
        )
        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_on is True

    @pytest.mark.asyncio
    async def test_turn_off(self):
        off_cmd = _cmd("c1", "Off")
        entity, mgr = self._make(
            command_mapping={"turn_off": "Off"},
            commands=[off_cmd],
        )
        await entity.async_turn_off()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_on is False

    def test_update_device(self):
        entity, _ = self._make()
        new_device = _device(name="Updated Light", device_type=DeviceType.LIGHT)
        entity.update_device(new_device)
        assert entity._device.name == "Updated Light"
        entity.async_write_ha_state.assert_called()


# ===========================================================================
# Switch entity tests
# ===========================================================================


class TestHAIRSwitchEntity:

    def _make(self, command_mapping=None, commands=None):
        mapping = command_mapping or {}
        cmds = commands or []
        config = EntityConfig(platform="switch", command_mapping=mapping)
        device = _device(
            device_type=DeviceType.SWITCH,
            commands=cmds,
            entity_config=config,
        )
        mgr = _manager()
        entity = HAIRSwitchEntity(device, mgr)
        _patch_write_state(entity)
        return entity, mgr

    def test_unique_id(self):
        entity, _ = self._make()
        assert entity._attr_unique_id == "hair_dev-1_switch"

    def test_device_info(self):
        entity, _ = self._make()
        info = entity.device_info
        assert (DOMAIN, "dev-1") in info["identifiers"]

    def test_initial_state(self):
        entity, _ = self._make()
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on(self):
        on_cmd = _cmd("c1", "On")
        entity, mgr = self._make(
            command_mapping={"turn_on": "On"},
            commands=[on_cmd],
        )
        await entity.async_turn_on()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_on is True

    @pytest.mark.asyncio
    async def test_turn_off(self):
        off_cmd = _cmd("c1", "Off")
        entity, mgr = self._make(
            command_mapping={"turn_off": "Off"},
            commands=[off_cmd],
        )
        await entity.async_turn_off()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_on is False

    def test_update_device(self):
        entity, _ = self._make()
        new_device = _device(name="Updated Switch", device_type=DeviceType.SWITCH)
        entity.update_device(new_device)
        assert entity._device.name == "Updated Switch"
        entity.async_write_ha_state.assert_called()


# ===========================================================================
# Cover entity tests
# ===========================================================================


class TestHAIRCoverEntity:

    def _make(self, command_mapping=None, commands=None):
        mapping = command_mapping or {}
        cmds = commands or []
        config = EntityConfig(platform="cover", command_mapping=mapping)
        device = _device(
            device_type=DeviceType.SCREEN,
            commands=cmds,
            entity_config=config,
        )
        mgr = _manager()
        entity = HAIRCoverEntity(device, mgr)
        _patch_write_state(entity)
        return entity, mgr

    def test_unique_id(self):
        entity, _ = self._make()
        assert entity._attr_unique_id == "hair_dev-1_cover"

    def test_device_info(self):
        entity, _ = self._make()
        info = entity.device_info
        assert (DOMAIN, "dev-1") in info["identifiers"]

    def test_supported_features(self):
        entity, _ = self._make(command_mapping={
            "open_cover": "Open",
            "close_cover": "Close",
            "stop_cover": "Stop",
        })
        f = entity.supported_features
        assert int(f) & CoverEntityFeature.OPEN
        assert int(f) & CoverEntityFeature.CLOSE
        assert int(f) & CoverEntityFeature.STOP

    def test_supported_features_empty(self):
        entity, _ = self._make()
        assert int(entity.supported_features) == 0

    def test_initial_state(self):
        entity, _ = self._make()
        assert entity.is_closed is None

    @pytest.mark.asyncio
    async def test_open_cover(self):
        open_cmd = _cmd("c1", "Open")
        entity, mgr = self._make(
            command_mapping={"open_cover": "Open"},
            commands=[open_cmd],
        )
        await entity.async_open_cover()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_closed is False

    @pytest.mark.asyncio
    async def test_close_cover(self):
        close_cmd = _cmd("c1", "Close")
        entity, mgr = self._make(
            command_mapping={"close_cover": "Close"},
            commands=[close_cmd],
        )
        await entity.async_close_cover()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")
        assert entity._is_closed is True

    @pytest.mark.asyncio
    async def test_stop_cover(self):
        stop_cmd = _cmd("c1", "Stop")
        entity, mgr = self._make(
            command_mapping={"stop_cover": "Stop"},
            commands=[stop_cmd],
        )
        await entity.async_stop_cover()
        mgr.async_send_command.assert_awaited_once_with("dev-1", "c1")

    def test_update_device(self):
        entity, _ = self._make()
        new_device = _device(name="Updated Screen", device_type=DeviceType.SCREEN)
        entity.update_device(new_device)
        assert entity._device.name == "Updated Screen"
        entity.async_write_ha_state.assert_called()
