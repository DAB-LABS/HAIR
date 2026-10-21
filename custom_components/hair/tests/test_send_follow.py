"""Every Device follows what HAIR sends (heard state round 1, GH #172).

Since 0.10.1 (GH #105) every send fires ``SIGNAL_DEVICE_SENT`` from the
device manager's choke point, and until this round only climate followed
it. A pinned Remote's retransmit, a HAIR button entity, a panel send or
``remote.send_command`` reached a TV or a fan and its entity stayed put.

The contracts under test, per platform:

- a manager-origin send moves state for each mapped key, the way that
  platform's own setter would;
- an entity-origin send, a send for another device and an unmapped
  command move nothing;
- a power verdict after a send still wins (a send is belief);
- the entity's own service call ends where its setter put it and writes
  state once: its sends are marked ``ORIGIN_ENTITY``, so the handler
  skips them (without that, a volume step would land twice);
- one command mapped to several keys follows ``send_follow``'s rules:
  a toggle wins, contradicting pairs move nothing, power first.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.media_player import MediaPlayerState

from custom_components.hair.const import DeviceType
from custom_components.hair.cover import HAIRCoverEntity
from custom_components.hair.fan import HAIRFanEntity
from custom_components.hair.light import HAIRLightEntity
from custom_components.hair.media_player import HAIRMediaPlayerEntity
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.power_monitor import SIGNAL_POWER_VERDICT
from custom_components.hair.send_follow import mapped_keys, one_of, power_after
from custom_components.hair.send_signal import (
    ORIGIN_ENTITY,
    ORIGIN_MANAGER,
    SIGNAL_DEVICE_SENT,
    DeviceSent,
)
from custom_components.hair.switch import HAIRSwitchEntity

DEVICE_ID = "dev-1"
COMMANDS = [
    "Power", "Power On", "Power Off", "Vol Up", "Vol Down", "Mute",
    "Play", "Pause", "Stop", "Play Pause", "Speed 1", "Speed 2",
    "Speed 3", "Faster", "Slower", "Swing", "Open", "Close", "Halt",
    "Input", "Both",
]


def _cid(name: str) -> str:
    return "c-" + name.lower().replace(" ", "-")


def _device(device_type: DeviceType, mapping: dict[str, str]) -> IRDevice:
    return IRDevice(
        id=DEVICE_ID,
        name="Living Room",
        device_type=device_type,
        emitter_entity_ids=["infrared.e"],
        commands=[
            IRCommand(id=_cid(n), name=n, protocol="PRONTO", code="x")
            for n in COMMANDS
        ],
        entity_config=EntityConfig(command_mapping=dict(mapping)),
    )


class _Wired:
    """An entity with its dispatcher handlers captured by signal."""

    def __init__(self, entity_cls, module, device, manager=None):
        self.manager = manager or MagicMock(async_send_command=AsyncMock())
        self.entity = entity_cls(device, self.manager)
        self.entity.hass = MagicMock()
        self.writes: list[tuple] = []
        self.entity.async_write_ha_state = MagicMock(
            side_effect=lambda: self.writes.append(self.snapshot())
        )
        self.handlers: dict[str, object] = {}
        self.module = module

    def snapshot(self) -> tuple:
        e = self.entity
        return tuple(
            getattr(e, attr, None) for attr in (
                "_state", "_is_on", "_volume_level", "_is_muted",
                "_percentage", "_oscillating", "_is_closed",
            )
        )

    async def add(self) -> _Wired:
        def _connect(hass, signal, fn):
            self.handlers[signal] = fn
            return MagicMock()

        with patch(f"{self.module}.async_dispatcher_connect", side_effect=_connect):
            await self.entity.async_added_to_hass()
        return self

    def send(self, name: str | None, origin=ORIGIN_MANAGER, device_id=DEVICE_ID):
        self.handlers[SIGNAL_DEVICE_SENT](DeviceSent(
            device_id=device_id,
            command_id=_cid(name) if name else None,
            command_name=name or "",
            origin=origin,
        ))

    def verdict(self, verdict: str) -> None:
        self.handlers[SIGNAL_POWER_VERDICT](DEVICE_ID, verdict)


async def _wire(entity_cls, module, device_type, mapping, manager=None):
    return await _Wired(
        entity_cls, module, _device(device_type, mapping), manager
    ).add()


# ---------------------------------------------------------------------------
# The rules themselves (send_follow)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keys,is_on,expected", [
    ({"turn_on"}, False, True),
    ({"turn_on"}, True, True),
    ({"turn_off"}, True, False),
    ({"power_toggle"}, False, True),
    ({"power_toggle"}, True, False),
    ({"turn_on", "turn_off"}, True, False),
    ({"turn_on", "turn_off"}, False, True),
    ({"turn_on", "power_toggle"}, True, False),
    ({"turn_off", "power_toggle"}, False, True),
    ({"mute"}, True, None),
    (set(), False, None),
])
def test_power_after(keys, is_on, expected):
    assert power_after(frozenset(keys), is_on) is expected


def test_one_of_refuses_a_contradiction():
    assert one_of(frozenset({"volume_up"}), "volume_up", "volume_down") == "volume_up"
    assert one_of(frozenset({"volume_up", "volume_down"}), "volume_up", "volume_down") is None
    assert one_of(frozenset({"mute"}), "volume_up", "volume_down") is None


def test_mapped_keys_finds_every_key_naming_the_command_casefolded():
    device = _device(DeviceType.MEDIA_PLAYER, {
        "turn_on": "POWER", "power_toggle": "power", "mute": "Mute",
    })
    sent = DeviceSent(device_id=DEVICE_ID, command_id=_cid("Power"))
    assert mapped_keys(device, sent) == {"turn_on", "power_toggle"}


def test_mapped_keys_follows_the_command_by_id_after_a_rename():
    device = _device(DeviceType.SWITCH, {"turn_on": "Power On"})
    sent = DeviceSent(
        device_id=DEVICE_ID, command_id=_cid("Power On"), command_name="Old name",
    )
    assert mapped_keys(device, sent) == {"turn_on"}


def test_mapped_keys_falls_back_to_the_sent_name_when_the_command_is_gone():
    device = _device(DeviceType.SWITCH, {"turn_on": "Power On"})
    sent = DeviceSent(
        device_id=DEVICE_ID, command_id="c-deleted", command_name="power on",
    )
    assert mapped_keys(device, sent) == {"turn_on"}


# ---------------------------------------------------------------------------
# Power, on every platform that has it
# ---------------------------------------------------------------------------

POWER_PLATFORMS = [
    pytest.param(HAIRMediaPlayerEntity, "custom_components.hair.media_player",
                 DeviceType.MEDIA_PLAYER, id="media_player"),
    pytest.param(HAIRFanEntity, "custom_components.hair.fan",
                 DeviceType.FAN, id="fan"),
    pytest.param(HAIRLightEntity, "custom_components.hair.light",
                 DeviceType.LIGHT, id="light"),
    pytest.param(HAIRSwitchEntity, "custom_components.hair.switch",
                 DeviceType.SWITCH, id="switch"),
]
DISCRETE = {"turn_on": "Power On", "turn_off": "Power Off"}
TOGGLE = {"power_toggle": "Power"}


def _is_on(entity) -> bool:
    if isinstance(entity, HAIRMediaPlayerEntity):
        return entity._state != MediaPlayerState.OFF
    return entity._is_on


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_discrete_power_sends_set_state(cls, module, dtype):
    w = await _wire(cls, module, dtype, DISCRETE)
    w.send("Power On")
    assert _is_on(w.entity)
    w.send("Power On")
    assert _is_on(w.entity)
    w.send("Power Off")
    assert not _is_on(w.entity)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_a_toggle_send_flips(cls, module, dtype):
    w = await _wire(cls, module, dtype, TOGGLE)
    w.send("Power")
    assert _is_on(w.entity)
    w.send("Power")
    assert not _is_on(w.entity)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_one_command_mapped_to_on_and_off_flips(cls, module, dtype):
    w = await _wire(cls, module, dtype, {"turn_on": "Power", "turn_off": "Power"})
    w.send("Power")
    assert _is_on(w.entity)
    w.send("Power")
    assert not _is_on(w.entity)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_turn_on_and_power_toggle_on_one_command_flip(cls, module, dtype):
    """A toggle wins: the code goes both ways, so "on" would be wrong
    every second press."""
    w = await _wire(cls, module, dtype, {"turn_on": "Power", "power_toggle": "Power"})
    w.send("Power")
    assert _is_on(w.entity)
    w.send("Power")
    assert not _is_on(w.entity)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_an_entity_origin_send_moves_nothing(cls, module, dtype):
    w = await _wire(cls, module, dtype, DISCRETE)
    w.send("Power On", origin=ORIGIN_ENTITY)
    assert not _is_on(w.entity)
    assert w.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_a_send_for_another_device_moves_nothing(cls, module, dtype):
    w = await _wire(cls, module, dtype, DISCRETE)
    w.send("Power On", device_id="dev-other")
    assert not _is_on(w.entity)
    assert w.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_an_unmapped_command_moves_nothing(cls, module, dtype):
    w = await _wire(cls, module, dtype, DISCRETE)
    w.send("Input")
    w.send(None)
    assert not _is_on(w.entity)
    assert w.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_a_power_verdict_after_a_send_wins(cls, module, dtype):
    w = await _wire(cls, module, dtype, DISCRETE)
    w.send("Power On")
    assert _is_on(w.entity)
    w.verdict("off")
    assert not _is_on(w.entity)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
async def test_the_subscription_is_dropped_on_removal(cls, module, dtype):
    w = await _wire(cls, module, dtype, DISCRETE)
    unsub = w.entity._device_sent_unsub
    await w.entity.async_will_remove_from_hass()
    unsub.assert_called_once()
    assert w.entity._device_sent_unsub is None


# ---------------------------------------------------------------------------
# The origin fix: an entity's own service call writes its state once
# ---------------------------------------------------------------------------


def _echoing_manager(holder: dict) -> MagicMock:
    """A manager that raises SIGNAL_DEVICE_SENT for every send, with the
    origin it was handed, the way the real choke point does. Without
    ``origin=ORIGIN_ENTITY`` the entity's own send would come back
    through its handler and apply a second time."""
    manager = MagicMock()

    async def _send(device_id, command_id, heard_future=None, pinned=False,
                    origin=None):
        holder["wired"].handlers[SIGNAL_DEVICE_SENT](DeviceSent(
            device_id=device_id, command_id=command_id,
            origin=origin or ORIGIN_MANAGER,
        ))

    manager.async_send_command = AsyncMock(side_effect=_send)
    return manager


async def _own_call(cls, module, dtype, mapping):
    holder: dict = {}
    w = await _wire(cls, module, dtype, mapping, _echoing_manager(holder))
    holder["wired"] = w
    return w


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,module,dtype", POWER_PLATFORMS)
@pytest.mark.parametrize("mapping", [DISCRETE, TOGGLE], ids=["discrete", "toggle"])
async def test_own_power_calls_land_once_where_the_setter_put_them(
    cls, module, dtype, mapping,
):
    w = await _own_call(cls, module, dtype, mapping)
    await w.entity.async_turn_on()
    assert _is_on(w.entity)
    assert len(w.writes) == 1
    await w.entity.async_turn_off()
    assert not _is_on(w.entity)
    assert len(w.writes) == 2
    for call in w.manager.async_send_command.await_args_list:
        assert call.kwargs.get("origin") == ORIGIN_ENTITY


@pytest.mark.asyncio
async def test_own_media_calls_land_once():
    w = await _own_call(
        HAIRMediaPlayerEntity, "custom_components.hair.media_player",
        DeviceType.MEDIA_PLAYER,
        {**TOGGLE, "volume_up": "Vol Up", "volume_down": "Vol Down",
         "mute": "Mute", "play": "Play", "pause": "Pause", "stop": "Stop"},
    )
    await w.entity.async_turn_on()
    await w.entity.async_volume_up()
    assert w.entity._volume_level == pytest.approx(0.55)
    await w.entity.async_volume_down()
    assert w.entity._volume_level == pytest.approx(0.5)
    await w.entity.async_mute_volume(True)
    assert w.entity._is_muted is True
    await w.entity.async_media_play()
    assert w.entity._state == MediaPlayerState.PLAYING
    await w.entity.async_media_pause()
    assert w.entity._state == MediaPlayerState.PAUSED
    await w.entity.async_media_stop()
    assert w.entity._state == MediaPlayerState.IDLE
    assert len(w.writes) == 7


@pytest.mark.asyncio
async def test_own_fan_calls_land_once():
    w = await _own_call(
        HAIRFanEntity, "custom_components.hair.fan", DeviceType.FAN,
        {**DISCRETE, "speed_1": "Speed 1", "speed_2": "Speed 2",
         "speed_3": "Speed 3", "oscillate": "Swing"},
    )
    await w.entity.async_set_percentage(60)
    assert w.entity._percentage == 66  # the setter snaps to speed_2
    await w.entity.async_oscillate(True)
    assert w.entity._oscillating is True
    assert len(w.writes) == 2


@pytest.mark.asyncio
async def test_own_fan_stepped_speed_lands_once():
    w = await _own_call(
        HAIRFanEntity, "custom_components.hair.fan", DeviceType.FAN,
        {**DISCRETE, "speed_up": "Faster", "speed_down": "Slower"},
    )
    await w.entity.async_set_percentage(50)
    assert w.entity._percentage == 50
    assert len(w.writes) == 1


@pytest.mark.asyncio
async def test_own_cover_calls_land_once():
    w = await _own_call(
        HAIRCoverEntity, "custom_components.hair.cover", DeviceType.SCREEN,
        {"open_cover": "Open", "close_cover": "Close", "stop_cover": "Halt"},
    )
    await w.entity.async_open_cover()
    assert w.entity._is_closed is False
    await w.entity.async_close_cover()
    assert w.entity._is_closed is True
    assert len(w.writes) == 2


# ---------------------------------------------------------------------------
# Media player
# ---------------------------------------------------------------------------

MEDIA = ("custom_components.hair.media_player", DeviceType.MEDIA_PLAYER)


async def _media(mapping):
    return await _wire(HAIRMediaPlayerEntity, *MEDIA, mapping)


@pytest.mark.asyncio
async def test_media_volume_steps_within_bounds():
    w = await _media({"volume_up": "Vol Up", "volume_down": "Vol Down"})
    w.send("Vol Up")
    assert w.entity._volume_level == pytest.approx(0.55)
    w.entity._volume_level = 0.98
    w.send("Vol Up")
    assert w.entity._volume_level == 1.0
    w.entity._volume_level = 0.02
    w.send("Vol Down")
    assert w.entity._volume_level == 0.0


@pytest.mark.asyncio
async def test_media_mute_flips():
    w = await _media({"mute": "Mute"})
    w.send("Mute")
    assert w.entity._is_muted is True
    w.send("Mute")
    assert w.entity._is_muted is False


@pytest.mark.asyncio
async def test_media_playback_keys_set_their_states():
    w = await _media({"play": "Play", "pause": "Pause", "stop": "Stop"})
    w.entity._state = MediaPlayerState.ON
    w.send("Play")
    assert w.entity._state == MediaPlayerState.PLAYING
    w.send("Pause")
    assert w.entity._state == MediaPlayerState.PAUSED
    w.send("Stop")
    assert w.entity._state == MediaPlayerState.IDLE


@pytest.mark.asyncio
async def test_media_one_play_pause_button_flips():
    w = await _media({"play": "Play Pause", "pause": "Play Pause"})
    w.entity._state = MediaPlayerState.ON
    w.send("Play Pause")
    assert w.entity._state == MediaPlayerState.PLAYING
    w.send("Play Pause")
    assert w.entity._state == MediaPlayerState.PAUSED
    w.send("Play Pause")
    assert w.entity._state == MediaPlayerState.PLAYING


@pytest.mark.asyncio
async def test_media_contradicting_volume_keys_move_nothing():
    w = await _media({"volume_up": "Both", "volume_down": "Both"})
    w.send("Both")
    assert w.entity._volume_level == 0.5
    assert w.writes == []


@pytest.mark.asyncio
async def test_media_power_comes_first():
    """Off wins over playback on one command; on then play is PLAYING."""
    w = await _media({"turn_off": "Both", "stop": "Both"})
    w.entity._state = MediaPlayerState.PLAYING
    w.send("Both")
    assert w.entity._state == MediaPlayerState.OFF

    w = await _media({"turn_on": "Both", "play": "Both"})
    w.send("Both")
    assert w.entity._state == MediaPlayerState.PLAYING

    w = await _media({"power_toggle": "Both", "play": "Both"})
    w.entity._state = MediaPlayerState.PLAYING
    w.send("Both")
    assert w.entity._state == MediaPlayerState.OFF


@pytest.mark.asyncio
async def test_media_toggle_from_any_playing_state_turns_it_off():
    w = await _media(TOGGLE)
    w.entity._state = MediaPlayerState.PAUSED
    w.send("Power")
    assert w.entity._state == MediaPlayerState.OFF


# ---------------------------------------------------------------------------
# Fan
# ---------------------------------------------------------------------------

FAN = ("custom_components.hair.fan", DeviceType.FAN)


async def _fan(mapping):
    return await _wire(HAIRFanEntity, *FAN, mapping)


@pytest.mark.asyncio
async def test_fan_speed_keys_set_the_setters_percentage_and_turn_it_on():
    w = await _fan({"speed_1": "Speed 1", "speed_2": "Speed 2", "speed_3": "Speed 3"})
    w.send("Speed 2")
    assert w.entity._percentage == 66
    assert w.entity._is_on is True
    w.send("Speed 3")
    assert w.entity._percentage == 100
    w.send("Speed 1")
    assert w.entity._percentage == 33


@pytest.mark.asyncio
async def test_fan_speed_up_and_down_step_25_within_bounds():
    w = await _fan({"speed_up": "Faster", "speed_down": "Slower"})
    w.send("Faster")
    assert w.entity._percentage == 25
    w.entity._percentage = 90
    w.send("Faster")
    assert w.entity._percentage == 100
    w.entity._percentage = 10
    w.send("Slower")
    assert w.entity._percentage == 0


@pytest.mark.asyncio
async def test_fan_oscillate_flips():
    w = await _fan({"oscillate": "Swing"})
    w.send("Swing")
    assert w.entity._oscillating is True
    w.send("Swing")
    assert w.entity._oscillating is False


@pytest.mark.asyncio
async def test_fan_contradicting_speed_keys_move_nothing():
    w = await _fan({"speed_1": "Both", "speed_2": "Both"})
    w.send("Both")
    assert w.entity._percentage is None
    assert w.entity._is_on is False
    w = await _fan({"speed_up": "Both", "speed_down": "Both"})
    w.send("Both")
    assert w.entity._percentage is None
    assert w.writes == []


@pytest.mark.asyncio
async def test_fan_off_on_the_same_command_keeps_the_speed_from_turning_it_on():
    w = await _fan({"turn_off": "Both", "speed_1": "Both"})
    w.entity._is_on = True
    w.send("Both")
    assert w.entity._is_on is False


# ---------------------------------------------------------------------------
# Light and cover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_light_brightness_key_moves_nothing():
    w = await _wire(
        HAIRLightEntity, "custom_components.hair.light", DeviceType.LIGHT,
        {"brightness_up": "Vol Up"},
    )
    w.send("Vol Up")
    assert w.writes == []


COVER = ("custom_components.hair.cover", DeviceType.SCREEN)


async def _cover(mapping):
    return await _wire(HAIRCoverEntity, *COVER, mapping)


@pytest.mark.asyncio
async def test_cover_open_and_close_sends_set_state():
    w = await _cover({"open_cover": "Open", "close_cover": "Close", "stop_cover": "Halt"})
    w.send("Close")
    assert w.entity._is_closed is True
    w.send("Halt")
    assert w.entity._is_closed is True
    w.send("Open")
    assert w.entity._is_closed is False


@pytest.mark.asyncio
async def test_cover_ignores_entity_origin_other_devices_and_contradictions():
    w = await _cover({"open_cover": "Both", "close_cover": "Both", "stop_cover": "Halt"})
    w.send("Both")
    w.send("Halt")
    w.send("Both", origin=ORIGIN_ENTITY)
    w.send("Both", device_id="dev-other")
    assert w.entity._is_closed is None
    assert w.writes == []


@pytest.mark.asyncio
async def test_cover_still_has_no_power_subscription():
    w = await _cover({"open_cover": "Open"})
    assert set(w.handlers) == {SIGNAL_DEVICE_SENT}
    unsub = w.entity._device_sent_unsub
    await w.entity.async_will_remove_from_hass()
    unsub.assert_called_once()


# ---------------------------------------------------------------------------
# End to end: the GH #172 path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_pinned_retransmit_moves_a_media_player_device(fake_hass):
    """A handset press on a pinned Remote: the trigger fires, the
    retransmit dispatcher drives ``_send_bound_command``, the real
    device manager sends it through its choke point, and the TV's
    entity follows. Before this round the entity stayed OFF."""
    from custom_components.hair.device_manager import DeviceManager
    from custom_components.hair.entity_factory import EntityFactory
    from custom_components.hair.models import IRTrigger, TriggerRemote
    from custom_components.hair.pin_bindings import rederive_remote
    from custom_components.hair.storage import HAIRStore
    from custom_components.hair.trigger_manager import TriggerManager

    from .test_device_sent import _FakeStore, _landing_manager

    tasks: list = []
    fake_hass.async_create_task = MagicMock(
        side_effect=lambda coro: tasks.append(asyncio.ensure_future(coro)) or tasks[-1]
    )
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    pronto = "0000 006D 0002 0000 0020 0020 0040 0040"
    tv = IRDevice(
        id=DEVICE_ID, name="Office TV", device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.e"],
        commands=[IRCommand(id="c-power", name="Power", protocol="PRONTO",
                            code=pronto, decoded_fingerprint="NEC:0x1:0x1")],
        entity_config=EntityConfig(command_mapping={"power_toggle": "Power"}),
    )
    store.add_device(tv)
    remote = TriggerRemote(id="rem1", name="Office TV Triggers",
                           pinned_device_ids=[DEVICE_ID])
    store.add_trigger_remote(remote)
    store.add_trigger(IRTrigger(
        id="trg1", name="Power", trigger_remote_id="rem1",
        signal_fingerprint="fp-power", decoded_fingerprint="NEC:0x1:0x1",
    ))
    rederive_remote(store, remote)

    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(),
    ):
        manager = DeviceManager(fake_hass, store, EntityFactory(fake_hass), "entry-1")
    w = await _Wired(
        HAIRMediaPlayerEntity, "custom_components.hair.media_player", tv, manager,
    ).add()
    tm = TriggerManager(fake_hass, store, manager)

    def _dispatch(hass, signal, payload):
        if signal == SIGNAL_DEVICE_SENT:
            w.handlers[SIGNAL_DEVICE_SENT](payload)

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=_dispatch,
    ):
        fired = tm.on_signal_captured(
            "fp-power", None, None, decoded_fingerprint="NEC:0x1:0x1"
        )
        while tasks:
            batch, tasks[:] = list(tasks), []
            await asyncio.gather(*batch)

    assert fired == ["trg1"]
    assert w.entity._state == MediaPlayerState.ON
