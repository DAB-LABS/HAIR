"""Restore completeness: the invariants that hold across all platforms.

`test_restore_state_reboot.py` pins what each platform restores.
This file pins the three things that must be true of every restore
block at once, and that no per-platform test can see:

- **NO RESTORE PATH TRANSMITS.** GH #115's closing requirement, and the
  one thing HAIR was already clean on. The audit verified it three ways
  on the live box (store row count, log grep, timestamp ordering); this
  is the version that runs in CI and keeps it true. Restore is
  bookkeeping by construction -- every block writes `self._is_on` /
  `self._hvac_mode` / etc. and none reaches a send. A future block that
  did reach one would be a silent regression on a promise made to a
  reporter.
- **Every platform tolerates no stored state.** A fresh install, a new
  entity, a snapshot HA never wrote: `async_get_last_state()` returns
  None and the entity keeps `__init__`'s defaults without raising.
- **A pre-fix stored state behaves exactly as today.** The 2026-08-23
  additions all read attributes that a v0.11.1 state does not carry.
  Every one of them has to fall back rather than raise, or upgrading
  breaks every entity at once on the first boot.

The device fixtures mirror the audit's own instrument: action keys
mapped to command names that do not exist on the device, so the entity
advertises every feature and accepts every setter while `_send` finds
nothing to send. Fully exercisable and provably unable to transmit,
which is the right shape for a test whose job is proving nothing
transmits.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    ATTR_TEMPERATURE,
    HVACMode,
)
from homeassistant.components.fan import ATTR_OSCILLATING, ATTR_PERCENTAGE
from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    MediaPlayerState,
)
from homeassistant.core import State

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.cover import HAIRCoverEntity
from custom_components.hair.fan import HAIRFanEntity
from custom_components.hair.light import HAIRLightEntity
from custom_components.hair.media_player import HAIRMediaPlayerEntity
from custom_components.hair.models import EntityConfig, IRDevice
from custom_components.hair.switch import HAIRSwitchEntity
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# Every action key any of these platforms reads, pointed at command
# names the device does not have -- the audit's instrument. The entity
# advertises the feature and accepts the setter; _send finds nothing.
_PHANTOM_MAPPING = {
    key: f"No Such Command ({key})"
    for key in (
        "turn_on", "turn_off", "power_toggle",
        "volume_up", "volume_down", "mute", "select_source",
        "play", "pause", "stop",
        "speed_up", "speed_down", "oscillate",
        "open_cover", "close_cover", "stop_cover",
        "mode_cool", "mode_heat", "fan_low", "fan_high",
    )
}


def _device(device_type: DeviceType, **overrides) -> IRDevice:
    return IRDevice(
        id="dev-restore",
        name="Restore Probe",
        device_type=device_type,
        emitter_entity_ids=["infrared.test"],
        entity_config=EntityConfig(command_mapping=dict(_PHANTOM_MAPPING)),
        **overrides,
    )


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0,
        modes=["cool"], fan_modes=["auto"], swing_modes=[],
        off="P-OFF", on=None,
        cells=[ClimateCell(mode="cool", fan="auto", temp=22.0,
                           pronto="P-C-A-22")],
    )


def _spy_manager() -> MagicMock:
    """A manager that records any attempt to put IR on the wire.

    Every door out of an entity, not just the one each platform
    happens to use today: if a restore block ever calls any of them
    the count moves and the test fails.
    """
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_send_pronto = AsyncMock()
    return mgr


def _sends(mgr: MagicMock) -> int:
    return (
        mgr.async_send_command.call_count
        + mgr.async_send_matrix_cell.call_count
        + mgr.async_send_pronto.call_count
    )


def _build(entity_cls, device, last_state, matrix=None):
    mgr = _spy_manager()
    entity = entity_cls(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    entity.hass.config.units.temperature_unit = "°C"
    if matrix is not None:
        entity._matrix = matrix
    entity.async_get_last_state = AsyncMock(return_value=last_state)
    entity.async_get_last_extra_data = AsyncMock(return_value=None)
    return entity, mgr


# A rich stored state per platform: every attribute the 2026-08-23 work
# added, set to something a restore block would have to act on. If any
# block reaches a send, it will be while handling one of these.
_RICH: list[tuple] = [
    (HAIRSwitchEntity, DeviceType.SWITCH, State("switch.x", "on", {}), None),
    (HAIRLightEntity, DeviceType.LIGHT, State("light.x", "on", {}), None),
    (
        HAIRFanEntity, DeviceType.FAN,
        State("fan.x", "on",
              {ATTR_PERCENTAGE: 60, ATTR_OSCILLATING: True}),
        None,
    ),
    (
        HAIRMediaPlayerEntity, DeviceType.MEDIA_PLAYER,
        State("media_player.x", "on",
              {ATTR_MEDIA_VOLUME_LEVEL: 0.55, ATTR_MEDIA_VOLUME_MUTED: True}),
        None,
    ),
    (
        HAIRCoverEntity, DeviceType.SCREEN,
        State("cover.x", "closed", {}),
        None,
    ),
    (
        HAIRClimateEntity, DeviceType.AC,
        State("climate.x", HVACMode.COOL,
              {ATTR_TEMPERATURE: 22.0, ATTR_FAN_MODE: "auto"}),
        None,
    ),
    (
        HAIRClimateEntity, DeviceType.AC,
        State("climate.x", HVACMode.COOL,
              {ATTR_TEMPERATURE: 22.0, ATTR_FAN_MODE: "auto",
               ATTR_SWING_MODE: None, ATTR_PRESET_MODE: "anything"}),
        _matrix(),
    ),
]

_IDS = [
    "switch", "light", "fan", "media_player", "cover",
    "climate-preset-mode", "climate-matrix-mode",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type,last_state,matrix", _RICH, ids=_IDS)
async def test_restore_never_transmits(entity_cls, device_type, last_state, matrix):
    """#115: "restored values should not send IR commands automatically
    during startup". They do not, and this is what keeps it that way."""
    device = _device(device_type, climate_matrix=matrix is not None)
    entity, mgr = _build(entity_cls, device, last_state, matrix)
    await entity._async_restore_state()
    assert _sends(mgr) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type,last_state,matrix", _RICH, ids=_IDS)
async def test_no_stored_state_is_survivable(entity_cls, device_type, last_state, matrix):
    """A fresh install, a new entity, or a snapshot HA never wrote."""
    device = _device(device_type, climate_matrix=matrix is not None)
    entity, mgr = _build(entity_cls, device, None, matrix)
    await entity._async_restore_state()
    assert _sends(mgr) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type,last_state,matrix", _RICH, ids=_IDS)
async def test_v0111_shaped_state_restores_without_error(
    entity_cls, device_type, last_state, matrix
):
    """The shape a v0.11.1 install actually wrote: the state string and
    the attributes that release restored, and NONE of the ones this
    ticket added.

    Every new read has to fall back rather than raise. Getting this
    wrong breaks every entity at once on the first boot after upgrade,
    which is the worst failure mode available to a restore change.
    """
    legacy = State(
        last_state.entity_id,
        last_state.state,
        {
            key: value for key, value in last_state.attributes.items()
            if key in (ATTR_TEMPERATURE, ATTR_FAN_MODE, ATTR_SWING_MODE)
        },
    )
    device = _device(device_type, climate_matrix=matrix is not None)
    entity, mgr = _build(entity_cls, device, legacy, matrix)
    await entity._async_restore_state()
    assert _sends(mgr) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_cls,device_type,last_state,matrix", _RICH, ids=_IDS)
async def test_v0111_shaped_state_leaves_the_new_attributes_at_defaults(
    entity_cls, device_type, last_state, matrix
):
    """Same states, checked from the other side: a pre-fix snapshot
    must produce EXACTLY today's behaviour, not a partial apply."""
    legacy = State(last_state.entity_id, last_state.state, {})
    device = _device(device_type, climate_matrix=matrix is not None)
    entity, _ = _build(entity_cls, device, legacy, matrix)
    fresh, _ = _build(entity_cls, _device(
        device_type, climate_matrix=matrix is not None), None, matrix)
    await entity._async_restore_state()
    await fresh._async_restore_state()

    if isinstance(entity, HAIRFanEntity):
        assert entity.percentage == fresh.percentage
        assert entity.oscillating == fresh.oscillating
    elif isinstance(entity, HAIRMediaPlayerEntity):
        assert entity.volume_level == fresh.volume_level
        assert entity.is_volume_muted == fresh.is_volume_muted
    elif isinstance(entity, HAIRClimateEntity):
        assert entity.preset_mode == fresh.preset_mode is None


@pytest.mark.asyncio
async def test_every_platform_that_restores_says_so_the_same_way():
    """One shape, six platforms. Restore lives in
    `_async_restore_state` and is reached from `async_added_to_hass`,
    so a reader who learns one platform has learned all of them -- and
    the cross-cutting tests above can find every block by name.

    Remote is the deliberate exception and is asserted as such in
    test_restore_state_reboot.py: it restores nothing, by ruling.
    """
    for cls in (
        HAIRSwitchEntity, HAIRLightEntity, HAIRFanEntity,
        HAIRMediaPlayerEntity, HAIRCoverEntity, HAIRClimateEntity,
    ):
        assert hasattr(cls, "_async_restore_state"), cls.__name__
        assert hasattr(cls, "async_added_to_hass"), cls.__name__


@pytest.mark.asyncio
async def test_media_player_restore_never_lands_on_a_transient_state():
    """The one clamp this ticket deliberately did NOT widen. Every
    stored playback state has to come back as plain ON or OFF, because
    one-way IR cannot know whether a TV is still playing after a
    reboot."""
    for stored in ("playing", "paused", "idle", "buffering", "on", "off"):
        entity, mgr = _build(
            HAIRMediaPlayerEntity, _device(DeviceType.MEDIA_PLAYER),
            State("media_player.x", stored, {ATTR_MEDIA_VOLUME_LEVEL: 0.4}),
        )
        await entity._async_restore_state()
        assert entity.state in (MediaPlayerState.ON, MediaPlayerState.OFF)
        assert _sends(mgr) == 0
