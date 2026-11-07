"""Toggle power, piece 1 (GH #229 point 1).

An entity's on and off setters fall back from ``turn_on`` / ``turn_off``
to ``power_toggle``. With only the toggle mapped, ``turn_off`` on a
device HAIR already believes is off sent the toggle and turned it on,
and automations call ``turn_off`` defensively. Now a setter sends
nothing when the command it would send is a toggle and the believed
state already matches. A discrete on or off code always sends, as it
always has.
"""
from __future__ import annotations

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.components.media_player import MediaPlayerState

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.fan import HAIRFanEntity
from custom_components.hair.light import HAIRLightEntity
from custom_components.hair.media_player import HAIRMediaPlayerEntity
from custom_components.hair.models import EntityConfig
from custom_components.hair.send_follow import is_toggle, toggle_already_there
from custom_components.hair.switch import HAIRSwitchEntity

from .test_entities import _cmd, _device, _manager, _patch_write_state
from .test_fan_speed_cycle import _device as _cycle_device
from .test_fan_speed_cycle import _fan, no_wait  # noqa: F401

COMMANDS = [_cmd("c-power", "Power"), _cmd("c-on", "On"), _cmd("c-off", "Off")]
TOGGLE_ONLY = {"power_toggle": "Power"}
DISCRETE = {"turn_on": "On", "turn_off": "Off"}
# One command mapped to both: the code demonstrably goes both ways.
BOTH_ON_ONE = {"turn_on": "Power", "turn_off": "Power"}


def _sent(mgr) -> list[str]:
    return [c.args[1] for c in mgr.async_send_command.await_args_list]


class _Platform:
    """How to make one platform's entity and set what HAIR believes."""

    def __init__(self, cls, device_type, platform, set_on, read_on):
        self.cls = cls
        self.device_type = device_type
        self.platform = platform
        self.set_on = set_on
        self.read_on = read_on

    def make(self, mapping, *, on: bool):
        config = EntityConfig(platform=self.platform, command_mapping=dict(mapping))
        device = _device(
            device_type=self.device_type, commands=list(COMMANDS),
            entity_config=config,
        )
        mgr = _manager()
        entity = self.cls(device, mgr)
        _patch_write_state(entity)
        self.set_on(entity, on)
        return entity, mgr


def _set_attr(entity, on):
    entity._is_on = on


PLATFORMS = {
    "fan": _Platform(HAIRFanEntity, DeviceType.FAN, "fan", _set_attr,
                     lambda e: e._is_on),
    "light": _Platform(HAIRLightEntity, DeviceType.LIGHT, "light", _set_attr,
                       lambda e: e._is_on),
    "switch": _Platform(HAIRSwitchEntity, DeviceType.SWITCH, "switch", _set_attr,
                        lambda e: e._is_on),
    "media_player": _Platform(
        HAIRMediaPlayerEntity, DeviceType.MEDIA_PLAYER, "media_player",
        lambda e, on: setattr(
            e, "_state", MediaPlayerState.ON if on else MediaPlayerState.OFF
        ),
        lambda e: e._state != MediaPlayerState.OFF,
    ),
    "climate": _Platform(
        HAIRClimateEntity, DeviceType.AC, "climate",
        lambda e, on: setattr(e, "_hvac_mode", HVACMode.COOL if on else HVACMode.OFF),
        lambda e: e._hvac_mode != HVACMode.OFF,
    ),
}


@pytest.fixture(params=sorted(PLATFORMS))
def platform(request) -> _Platform:
    return PLATFORMS[request.param]


class TestTheToggleIsGuarded:
    @pytest.mark.asyncio
    async def test_off_while_believed_off_sends_nothing(self, platform):
        entity, mgr = platform.make(TOGGLE_ONLY, on=False)
        await entity.async_turn_off()
        assert _sent(mgr) == []
        assert platform.read_on(entity) is False

    @pytest.mark.asyncio
    async def test_on_while_believed_on_sends_nothing(self, platform):
        entity, mgr = platform.make(TOGGLE_ONLY, on=True)
        await entity.async_turn_on()
        assert _sent(mgr) == []
        assert platform.read_on(entity) is True

    @pytest.mark.asyncio
    async def test_off_while_believed_on_sends_the_toggle_once(self, platform):
        entity, mgr = platform.make(TOGGLE_ONLY, on=True)
        await entity.async_turn_off()
        assert _sent(mgr) == ["c-power"]
        assert platform.read_on(entity) is False

    @pytest.mark.asyncio
    async def test_on_while_believed_off_sends_the_toggle_once(self, platform):
        entity, mgr = platform.make(TOGGLE_ONLY, on=False)
        await entity.async_turn_on()
        assert _sent(mgr) == ["c-power"]
        assert platform.read_on(entity) is True

    @pytest.mark.asyncio
    async def test_one_command_on_both_keys_is_a_toggle(self, platform):
        entity, mgr = platform.make(BOTH_ON_ONE, on=False)
        await entity.async_turn_off()
        assert _sent(mgr) == []


class TestDiscreteCodesAlwaysSend:
    @pytest.mark.asyncio
    async def test_a_real_off_is_sent_even_when_believed_off(self, platform):
        entity, mgr = platform.make(DISCRETE, on=False)
        await entity.async_turn_off()
        assert _sent(mgr) == ["c-off"]

    @pytest.mark.asyncio
    async def test_a_real_on_is_sent_even_when_believed_on(self, platform):
        entity, mgr = platform.make(DISCRETE, on=True)
        await entity.async_turn_on()
        assert _sent(mgr) == ["c-on"]

    @pytest.mark.asyncio
    async def test_a_real_off_beside_the_toggle_still_sends(self, platform):
        mapping = {"turn_off": "Off", "power_toggle": "Power"}
        entity, mgr = platform.make(mapping, on=False)
        await entity.async_turn_off()
        assert _sent(mgr) == ["c-off"]

    @pytest.mark.asyncio
    async def test_a_turn_off_mapped_to_the_toggle_code_is_guarded(self, platform):
        mapping = {"turn_off": "Power", "power_toggle": "Power"}
        entity, mgr = platform.make(mapping, on=False)
        await entity.async_turn_off()
        assert _sent(mgr) == []


class TestThePowerSensorDecides:
    @pytest.mark.asyncio
    async def test_an_on_verdict_makes_the_off_send(self):
        """The verdict corrects the belief, and the guard reads it."""
        entity, mgr = PLATFORMS["fan"].make(TOGGLE_ONLY, on=False)
        entity._handle_power_verdict(entity._device.id, "on")
        await entity.async_turn_off()
        assert _sent(mgr) == ["c-power"]


class TestPresetClimate:
    @pytest.mark.asyncio
    async def test_set_hvac_mode_off_while_off_sends_nothing(self):
        entity, mgr = PLATFORMS["climate"].make(TOGGLE_ONLY, on=False)
        await entity.async_set_hvac_mode(HVACMode.OFF)
        assert _sent(mgr) == []

    @pytest.mark.asyncio
    async def test_an_unmapped_mode_while_on_does_not_toggle_the_unit_off(self):
        entity, mgr = PLATFORMS["climate"].make(TOGGLE_ONLY, on=True)
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert _sent(mgr) == []
        assert entity.hvac_mode == HVACMode.COOL

    @pytest.mark.asyncio
    async def test_an_unmapped_mode_while_off_still_powers_on(self):
        entity, mgr = PLATFORMS["climate"].make(TOGGLE_ONLY, on=False)
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert _sent(mgr) == ["c-power"]
        assert entity.hvac_mode == HVACMode.HEAT

    @pytest.mark.asyncio
    async def test_set_temperature_with_off_on_an_off_unit_sends_nothing(self):
        entity, mgr = PLATFORMS["climate"].make(TOGGLE_ONLY, on=False)
        await entity.async_set_temperature(temperature=24, hvac_mode=HVACMode.OFF)
        assert _sent(mgr) == []


class TestTheSpeedCyclePath:
    @pytest.mark.asyncio
    async def test_off_while_believed_off_presses_nothing(self, no_wait):  # noqa: F811
        fan = await _fan(no_wait, _cycle_device(steps=3))
        fan.at(1, is_on=False)
        await fan.entity.async_turn_off()
        assert fan.sent == []

    @pytest.mark.asyncio
    async def test_off_while_on_presses_power_once(self, no_wait):  # noqa: F811
        fan = await _fan(no_wait, _cycle_device(steps=3))
        fan.at(2, is_on=True)
        await fan.entity.async_turn_off()
        assert fan.sent == ["c-power"]
        assert fan.entity.is_on is False


class TestTheHelper:
    def test_is_toggle(self):
        assert is_toggle({}, "power_toggle", "Power")
        assert is_toggle({"power_toggle": "power"}, "turn_off", "Power")
        assert is_toggle(BOTH_ON_ONE, "turn_on", "Power")
        assert not is_toggle(DISCRETE, "turn_off", "Off")

    def test_a_typed_remote_never_skips(self):
        """A Remote's entity has no device and never sends anyway."""
        assert toggle_already_there(None, TOGGLE_ONLY, ("power_toggle",), False, False) is False

    def test_a_mapped_command_the_device_lacks_falls_through(self):
        device = _device(commands=[_cmd("c-power", "Power")])
        mapping = {"turn_off": "Gone", "power_toggle": "Power"}
        assert toggle_already_there(
            device, mapping, ("turn_off", "power_toggle"), False, False
        )
