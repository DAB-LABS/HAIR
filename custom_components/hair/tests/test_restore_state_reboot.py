"""Device Settings + power sensor (0.9.8), commit 4/6: restore on reboot.

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
from homeassistant.components.fan import ATTR_OSCILLATING, ATTR_PERCENTAGE
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.const import UnitOfTemperature
from homeassistant.core import State

from custom_components.hair.climate import HAIRClimateEntity, _ClimateExtraStoredData
from custom_components.hair.const import DeviceType
from custom_components.hair.cover import HAIRCoverEntity
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

    async_get_last_extra_data defaults to None -- "no entity has ever
    written this payload yet", the realistic default for every
    platform except climate (098-final-review.md's fix), and for
    climate itself the realistic default for the one restart right
    after that fix ships. Individual tests override it to exercise
    the extra-data path.
    """
    mgr = manager if manager is not None else _manager()
    entity = entity_cls(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.async_get_last_state = AsyncMock(return_value=last_state)
    entity.async_get_last_extra_data = AsyncMock(return_value=None)
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


async def _restored_matrix_entity(
    last_state, matrix=None, display_unit=UnitOfTemperature.CELSIUS,
    extra_data=None,
):
    """display_unit defaults to Celsius, matching _matrix()'s own
    default "C" file unit -- so a bare fixture (no display_unit
    override) exercises the fallback conversion path as a real,
    honest no-op (equal units) rather than skipping it. Tests that
    care about the actual bug (098-final-review.md) pass a differing
    display_unit explicitly. extra_data defaults to None -- see
    _restored_entity's docstring for why.
    """
    mgr = _manager()
    entity = HAIRClimateEntity(_matrix_climate_device(), mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.hass.config.units.temperature_unit = display_unit
    entity._matrix = matrix if matrix is not None else _matrix()
    entity.async_get_last_state = AsyncMock(return_value=last_state)
    entity.async_get_last_extra_data = AsyncMock(return_value=extra_data)
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
# climate: matrix mode, native-unit temperature restore
# (098-final-review.md, "THE REQUIRED FIX: restore re-reads display-unit
# temperature as native")
#
# The bug: HA core reports a climate entity's temperature attributes in
# the INSTALL's display unit, but the old restore path stored
# last_state.attributes[ATTR_TEMPERATURE] straight into
# self._target_temperature as if it were already native. Matrix mode is
# the only mode where those two units can actually differ (preset
# mode's native unit already IS the install's display unit by design),
# so every restart compounded one uncompensated conversion: 23C ->
# 73.4 -> 164 -> 327 -> ... The fix persists the native value itself
# via extra_restore_state_data, converts on the one-time fallback path
# for an entity that has never written that payload yet, and clamps to
# the matrix's own range as a backstop regardless of source.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_matrix_climate_extra_data_wins_over_display_unit_attribute():
    # The stored attribute is deliberately impossible (999) so the
    # assertion only passes if extra data was actually used instead of
    # falling through to the attribute.
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 999, ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity, _ = await _restored_matrix_entity(
        last,
        display_unit=UnitOfTemperature.FAHRENHEIT,
        extra_data=_ClimateExtraStoredData(native_target_temperature=22.0),
    )
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.target_temperature == 22.0


@pytest.mark.asyncio
async def test_matrix_climate_no_extra_data_converts_display_to_native():
    # 71.6F is exactly 22.0C -- the matrix's one real cell. An
    # F-display install's state machine would have written exactly
    # this attribute for a native 22.0C setpoint.
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 71.6, ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity, _ = await _restored_matrix_entity(
        last, display_unit=UnitOfTemperature.FAHRENHEIT, extra_data=None,
    )
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.target_temperature == pytest.approx(22.0)


@pytest.mark.asyncio
async def test_matrix_climate_restore_idempotent_across_two_restarts():
    # Restart 1: no extra data yet (pre-fix entity, or first boot after
    # the fix ships) -- falls back to the converted attribute read.
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 71.6, ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity1, _ = await _restored_matrix_entity(
        last, display_unit=UnitOfTemperature.FAHRENHEIT, extra_data=None,
    )
    assert entity1.target_temperature == pytest.approx(22.0)

    # Restart 2: this entity now HAS extra data -- exactly what entity1
    # would have persisted before its own shutdown. No conversion
    # should apply a second time.
    carried_over = entity1.extra_restore_state_data
    entity2, _ = await _restored_matrix_entity(
        last, display_unit=UnitOfTemperature.FAHRENHEIT, extra_data=carried_over,
    )
    assert entity2.target_temperature == pytest.approx(22.0)
    assert entity2.target_temperature == entity1.target_temperature


@pytest.mark.asyncio
async def test_matrix_climate_absurd_fallback_temperature_clamps_high():
    # The live bug's exact shape: no extra data yet, and the stored
    # attribute is already the product of several compounded
    # conversions (73893, per 098-final-review.md's real numbers).
    # Converting it further is still garbage; the clamp is what
    # actually saves the entity.
    last = State(
        "climate.x", "cool",
        {ATTR_TEMPERATURE: 73893, ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity, _ = await _restored_matrix_entity(
        last, display_unit=UnitOfTemperature.FAHRENHEIT, extra_data=None,
    )
    assert entity.target_temperature is not None
    assert 16.0 <= entity.target_temperature <= 30.0
    assert entity.target_temperature == 30.0  # matrix.max_temp


@pytest.mark.asyncio
async def test_matrix_climate_absurd_extra_data_temperature_clamps_low():
    # The clamp is a backstop regardless of which path produced the
    # value -- corrupt extra data (should never happen, but "either
    # way" per the review) clamps exactly like a corrupt fallback read.
    last = State(
        "climate.x", "cool",
        {ATTR_FAN_MODE: "auto", ATTR_SWING_MODE: "swing"},
    )
    entity, _ = await _restored_matrix_entity(
        last,
        extra_data=_ClimateExtraStoredData(native_target_temperature=-50000.0),
    )
    assert entity.target_temperature == 16.0  # matrix.min_temp


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


# ---------------------------------------------------------------------------
# cover: the platform the 0.9.8 scoping rule missed (restore completeness,
# 2026-08-23). Not "on/off" and not climate, so the rule's sentence read as
# though it covered the field while nothing actually did.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cover_no_last_state_stays_unknown():
    """No stored state is the ONLY case that may still read unknown.

    A fresh install has no evidence about the screen and should say so.
    The bug was that a restart also produced this, which is a different
    thing wearing the same face.
    """
    entity, mgr = await _restored_entity(
        HAIRCoverEntity, _device(DeviceType.SCREEN), None
    )
    assert entity.is_closed is None
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_cover_restores_closed():
    last = State("cover.x", "closed", {})
    entity, mgr = await _restored_entity(
        HAIRCoverEntity, _device(DeviceType.SCREEN), last
    )
    assert entity.is_closed is True
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_cover_restores_open():
    """Both directions, because the audit set closed before restart A
    and OPEN before restart B and got `unknown` back from both -- which
    is what proved the attribute was being dropped rather than one
    particular value being mishandled."""
    last = State("cover.x", "open", {})
    entity, _ = await _restored_entity(
        HAIRCoverEntity, _device(DeviceType.SCREEN), last
    )
    assert entity.is_closed is False


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["unknown", "unavailable", "opening", "garbage"])
async def test_cover_unusable_state_stays_unknown(state):
    """Anything that is not one of this platform's two real states is
    no evidence, and no evidence stays None rather than guessing a
    direction."""
    entity, _ = await _restored_entity(
        HAIRCoverEntity, _device(DeviceType.SCREEN), State("cover.x", state, {})
    )
    assert entity.is_closed is None


@pytest.mark.asyncio
async def test_cover_has_no_power_verdict_subscription():
    """Ruled 2026-08-23: cover deliberately does not subscribe, so the
    asymmetry against the other five platforms is a decision rather
    than the same oversight repeating. Pinned so a later sweep adding
    it has to change this test and read the ruling.
    """
    entity = HAIRCoverEntity(_device(DeviceType.SCREEN), _manager())
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.async_get_last_state = AsyncMock(return_value=None)
    await entity.async_added_to_hass()
    assert not hasattr(entity, "_power_verdict_unsub")


# ---------------------------------------------------------------------------
# fan: percentage and oscillating (restore completeness, 2026-08-23).
# GH #115's actual report. The 0.9.8 scope was a real decision; it is stale.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("percentage,oscillating", [(60, True), (80, False)])
async def test_fan_restores_percentage_and_oscillating(percentage, oscillating):
    """Two distinct values, the way the audit ran it: a result that
    only holds for one particular value is an artefact, not a fix."""
    last = State(
        "fan.x", "on",
        {ATTR_PERCENTAGE: percentage, ATTR_OSCILLATING: oscillating},
    )
    entity, mgr = await _restored_entity(HAIRFanEntity, _device(DeviceType.FAN), last)
    assert entity.is_on is True
    assert entity.percentage == percentage
    assert entity.oscillating is oscillating
    mgr.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_fan_legacy_stored_state_behaves_exactly_as_today():
    """A state written before this fix carries neither attribute. It
    must restore is_on and leave the other two at __init__'s defaults,
    which is precisely what today's code does -- no crash, no guess."""
    last = State("fan.x", "on", {})
    entity, _ = await _restored_entity(HAIRFanEntity, _device(DeviceType.FAN), last)
    assert entity.is_on is True
    assert entity.percentage is None
    assert entity.oscillating is False


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["not-a-number", None, [], {}])
async def test_fan_malformed_percentage_falls_back(bad):
    """A restore block that raises on a stale snapshot takes the whole
    entity down with it. Anything unconvertible is treated as absent."""
    last = State("fan.x", "on", {ATTR_PERCENTAGE: bad})
    entity, _ = await _restored_entity(HAIRFanEntity, _device(DeviceType.FAN), last)
    assert entity.percentage is None


@pytest.mark.asyncio
@pytest.mark.parametrize("stored,expected", [(-20, 0), (250, 100)])
async def test_fan_out_of_range_percentage_clamps(stored, expected):
    """Percentage is a 0..100 contract with HA. A corrupted snapshot
    self-heals to a legal value rather than resurrecting forever, the
    same reasoning 098-final-review applied to the climate setpoint."""
    last = State("fan.x", "on", {ATTR_PERCENTAGE: stored})
    entity, _ = await _restored_entity(HAIRFanEntity, _device(DeviceType.FAN), last)
    assert entity.percentage == expected


@pytest.mark.asyncio
async def test_fan_off_still_carries_its_speed_back():
    """The power-verdict handler says an "on" verdict restores speed
    and oscillation for free, because neither is cleared on off. That
    is only true if a stored OFF state keeps them, so it does."""
    last = State(
        "fan.x", "off", {ATTR_PERCENTAGE: 40, ATTR_OSCILLATING: True}
    )
    entity, _ = await _restored_entity(HAIRFanEntity, _device(DeviceType.FAN), last)
    assert entity.is_on is False
    assert entity.percentage == 40
    assert entity.oscillating is True
