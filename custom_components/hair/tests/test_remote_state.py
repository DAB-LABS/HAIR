"""A typed Remote keeps its own state (heard state, round 2a, GH #172).

The owner's model (2026-10-21): two devices, each with its own state,
neither synced to the other. A Remote given a type gets a state entity
of that type, named as the remote, which follows its own handset presses
and whose controls change its own state only and never send IR. The
contracts under test:

- per type, a confirmed press of a mapped button moves the entity the
  way the Device class's own rules would (``send_follow`` and the
  platform's ``_apply_keys``); an unmapped button, another Remote's
  button, a press below ``min_hits`` and an echo move nothing;
- every control changes state and sends nothing;
- features come from the mapping, trackable keys only (no dead
  controls);
- restore per type, round 1's media rule included;
- lifecycle through the real handlers: set, change and clear the type
  (the old row forgotten), map and unmap buttons, delete a button or the
  Remote, Duplicate, Make a Remote, Make a Device; an AC Remote takes no
  type;
- the orphan sweep keeps a Remote's rows while it exists and cleans them
  up once it is gone;
- a pinned Remote's entity follows its press while the press still
  drives the pinned Device.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.media_player import MediaPlayerState

from custom_components.hair import remote_state
from custom_components.hair.const import DOMAIN, DeviceType
from custom_components.hair.cover import HAIRCoverEntity, HAIRRemoteCoverEntity
from custom_components.hair.entity_factory import (
    classify_unique_id,
    reconcile_orphan_entities,
    remote_last_pressed_unique_id,
    remote_state_unique_id,
)
from custom_components.hair.fan import HAIRFanEntity, HAIRRemoteFanEntity
from custom_components.hair.light import HAIRLightEntity, HAIRRemoteLightEntity
from custom_components.hair.media_player import (
    HAIRMediaPlayerEntity,
    HAIRRemoteMediaPlayerEntity,
)
from custom_components.hair.models import (
    EntityConfig,
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
)
from custom_components.hair.remote_state import (
    REMOTE_PLATFORMS,
    SIGNAL_REMOTE_PRESSED,
    RemotePressed,
    register_remote_platform,
    remote_action_options,
    remote_entity_config,
)
from custom_components.hair.switch import HAIRRemoteSwitchEntity, HAIRSwitchEntity

from .test_last_pressed import ENTRY_ID, _Bench, _conn, _dr, _store_with
from .test_orphan_entities import FakeRegistry, _registry_patch

REMOTE_CLASSES = {
    "media_player": HAIRRemoteMediaPlayerEntity,
    "fan": HAIRRemoteFanEntity,
    "light": HAIRRemoteLightEntity,
    "switch": HAIRRemoteSwitchEntity,
    "cover": HAIRRemoteCoverEntity,
}
DEVICE_CLASSES = {
    "media_player": HAIRMediaPlayerEntity,
    "fan": HAIRFanEntity,
    "light": HAIRLightEntity,
    "switch": HAIRSwitchEntity,
    "cover": HAIRCoverEntity,
}
TYPE_FOR = {
    "media_player": DeviceType.MEDIA_PLAYER,
    "fan": DeviceType.FAN,
    "light": DeviceType.LIGHT,
    "switch": DeviceType.SWITCH,
    "cover": DeviceType.SCREEN,
}


def _remote(
    device_type: str | None,
    mapping: dict[str, str] | None = None,
    remote_id: str = "rem1",
    name: str = "Living Room TV Remote",
) -> TriggerRemote:
    return TriggerRemote(
        id=remote_id,
        name=name,
        device_type=device_type,
        entity_config=EntityConfig(command_mapping=dict(mapping or {})),
    )


def _trigger(tid, name, remote_id="rem1", min_hits=1):
    return IRTrigger(
        id=tid, name=name, trigger_remote_id=remote_id, min_hits=min_hits,
        signal_fingerprint=f"fp-{tid}", created_at="2026-10-22T00:00:00",
    )


class _Live:
    """One Remote entity, added: writes recorded, its press handler kept."""

    def __init__(self, entity):
        self.entity = entity
        entity.hass = MagicMock()
        entity.entity_id = f"x.{entity._attr_unique_id}"
        self.writes = 0

        def _write():
            self.writes += 1

        entity.async_write_ha_state = MagicMock(side_effect=_write)
        self.handler = None

    async def add(self, last_state=None):
        self.entity.async_get_last_state = AsyncMock(return_value=last_state)

        def _connect(hass, signal, fn):
            assert signal == SIGNAL_REMOTE_PRESSED
            self.handler = fn
            return MagicMock()

        with patch.object(remote_state, "async_dispatcher_connect", side_effect=_connect):
            await self.entity.async_added_to_hass()
        return self

    def press(self, trigger_id, remote_id="rem1"):
        self.handler(RemotePressed(remote_id, trigger_id))


async def _live(platform, mapping, device_type=None, last_state=None):
    remote = _remote(device_type or TYPE_FOR[platform], mapping)
    return await _Live(REMOTE_CLASSES[platform](remote)).add(last_state)


# ---------------------------------------------------------------------------
# Following presses, per type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_media_player_follows_each_mapped_button():
    live = await _live("media_player", {
        "power_toggle": "t-power", "volume_up": "t-up", "volume_down": "t-down",
        "mute": "t-mute", "play": "t-play", "pause": "t-pause", "stop": "t-stop",
    })
    e = live.entity
    assert e.state == MediaPlayerState.OFF
    live.press("t-power")
    assert e.state == MediaPlayerState.ON
    live.press("t-up")
    assert e.volume_level == pytest.approx(0.55)
    live.press("t-down")
    live.press("t-down")
    assert e.volume_level == pytest.approx(0.45)
    live.press("t-mute")
    assert e.is_volume_muted is True
    live.press("t-play")
    assert e.state == MediaPlayerState.PLAYING
    live.press("t-pause")
    assert e.state == MediaPlayerState.PAUSED
    live.press("t-stop")
    assert e.state == MediaPlayerState.IDLE
    live.press("t-power")
    assert e.state == MediaPlayerState.OFF


@pytest.mark.asyncio
async def test_media_player_discrete_power_and_a_shared_play_pause_button():
    live = await _live("media_player", {
        "turn_on": "t-on", "turn_off": "t-off", "play": "t-pp", "pause": "t-pp",
    })
    e = live.entity
    live.press("t-on")
    live.press("t-on")
    assert e.state == MediaPlayerState.ON
    live.press("t-pp")
    assert e.state == MediaPlayerState.PLAYING
    live.press("t-pp")
    assert e.state == MediaPlayerState.PAUSED
    live.press("t-off")
    assert e.state == MediaPlayerState.OFF


@pytest.mark.asyncio
async def test_fan_follows_speeds_steps_oscillation_and_power():
    live = await _live("fan", {
        "power_toggle": "t-power", "speed_1": "t-s1", "speed_2": "t-s2",
        "speed_3": "t-s3", "oscillate": "t-swing",
    })
    e = live.entity
    live.press("t-s2")
    assert e.is_on is True
    assert e.percentage == 66
    live.press("t-swing")
    assert e.oscillating is True
    live.press("t-power")
    assert e.is_on is False
    assert e.speed_count == 3


@pytest.mark.asyncio
async def test_fan_speed_up_and_down_step_by_25():
    live = await _live("fan", {"speed_up": "t-up", "speed_down": "t-down"})
    live.press("t-up")
    live.press("t-up")
    assert live.entity.percentage == 50
    live.press("t-down")
    assert live.entity.percentage == 25


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["light", "switch"])
async def test_light_and_switch_follow_on_and_off(platform):
    live = await _live(platform, {"turn_on": "t-on", "turn_off": "t-off"})
    live.press("t-on")
    assert live.entity.is_on is True
    live.press("t-off")
    assert live.entity.is_on is False


@pytest.mark.asyncio
async def test_screen_follows_open_close_and_stop_moves_nothing():
    live = await _live("cover", {
        "open_cover": "t-open", "close_cover": "t-close", "stop_cover": "t-stop",
    })
    live.press("t-close")
    assert live.entity.is_closed is True
    live.press("t-open")
    assert live.entity.is_closed is False
    writes = live.writes
    live.press("t-stop")
    assert live.entity.is_closed is False
    assert live.writes == writes


@pytest.mark.asyncio
async def test_an_unmapped_button_or_another_remotes_press_moves_nothing():
    live = await _live("switch", {"turn_on": "t-on"})
    live.press("t-other")
    live.press("t-on", remote_id="rem2")
    assert live.entity.is_on is False
    assert live.writes == 0


@pytest.mark.asyncio
async def test_the_toggle_and_contradiction_rules_are_round_ones():
    """One button mapped to two keys: the shared rules decide."""
    live = await _live("media_player", {
        "volume_up": "t-both", "volume_down": "t-both", "turn_on": "t-on",
    })
    live.press("t-on")
    live.press("t-both")
    assert live.entity.volume_level == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Controls change state only
# ---------------------------------------------------------------------------


def _armed_with_a_device(entity):
    """Give the entity everything the Device's own send path needs, so a
    Remote that ever delegated to it would reach the recorder."""
    recorder = MagicMock(async_send_command=AsyncMock())
    entity._manager = recorder
    entity._device = SimpleNamespace(
        id="dev-x", name="X",
        get_command_by_name=lambda name: SimpleNamespace(id="c-x", name=name),
    )
    return recorder


@pytest.mark.asyncio
async def test_media_player_controls_change_state_and_send_nothing():
    live = await _live("media_player", {
        "power_toggle": "t1", "volume_up": "t2", "volume_down": "t3",
        "mute": "t4", "play": "t5", "pause": "t6", "stop": "t7",
    })
    e = live.entity
    recorder = _armed_with_a_device(e)
    await e.async_turn_on()
    assert e.state == MediaPlayerState.ON
    await e.async_volume_up()
    assert e.volume_level == pytest.approx(0.55)
    await e.async_volume_down()
    await e.async_mute_volume(True)
    assert e.is_volume_muted is True
    await e.async_media_play()
    assert e.state == MediaPlayerState.PLAYING
    await e.async_media_pause()
    await e.async_media_stop()
    assert e.state == MediaPlayerState.IDLE
    await e.async_turn_off()
    assert e.state == MediaPlayerState.OFF
    recorder.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_fan_controls_change_state_and_send_nothing():
    live = await _live("fan", {
        "power_toggle": "t1", "speed_up": "t2", "speed_down": "t3",
        "oscillate": "t4",
    })
    e = live.entity
    recorder = _armed_with_a_device(e)
    await e.async_turn_on()
    await e.async_set_percentage(75)
    assert (e.is_on, e.percentage) == (True, 75)
    await e.async_oscillate(True)
    assert e.oscillating is True
    await e.async_turn_off()
    assert e.is_on is False
    recorder.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_fan_speed_steps_set_from_a_percentage_and_send_nothing():
    live = await _live("fan", {"speed_1": "t1", "speed_2": "t2"})
    e = live.entity
    recorder = _armed_with_a_device(e)
    await e.async_set_percentage(100)
    assert e.percentage == 100
    recorder.async_send_command.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["light", "switch"])
async def test_light_and_switch_controls_send_nothing(platform):
    live = await _live(platform, {"turn_on": "t1", "turn_off": "t2"})
    e = live.entity
    recorder = _armed_with_a_device(e)
    await e.async_turn_on()
    assert e.is_on is True
    await e.async_turn_off()
    assert e.is_on is False
    recorder.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_screen_controls_send_nothing():
    live = await _live("cover", {
        "open_cover": "t1", "close_cover": "t2", "stop_cover": "t3",
    })
    e = live.entity
    recorder = _armed_with_a_device(e)
    await e.async_close_cover()
    assert e.is_closed is True
    await e.async_open_cover()
    await e.async_stop_cover()
    assert e.is_closed is False
    recorder.async_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_a_control_changes_state_even_with_nothing_mapped():
    """A user corrects drift by hand: the switch flips with no mapping."""
    live = await _live("switch", {})
    await live.entity.async_turn_on()
    assert live.entity.is_on is True


# ---------------------------------------------------------------------------
# Features and identity
# ---------------------------------------------------------------------------


def test_features_come_from_the_trackable_mapping_only():
    from homeassistant.components.light import ColorMode
    from homeassistant.components.media_player import MediaPlayerEntityFeature

    media = HAIRRemoteMediaPlayerEntity(_remote("media_player", {
        "turn_on": "t1", "select_source": "t2", "volume_up": "t3",
    }))
    features = int(media.supported_features)
    assert not features & MediaPlayerEntityFeature.SELECT_SOURCE
    assert features & MediaPlayerEntityFeature.VOLUME_STEP
    assert features & MediaPlayerEntityFeature.TURN_ON

    light = HAIRRemoteLightEntity(_remote("light", {
        "turn_on": "t1", "brightness_up": "t2",
    }))
    assert light.color_mode == ColorMode.ONOFF


def test_the_action_list_offers_only_what_the_entity_tracks():
    keys = [o["key"] for o in remote_action_options("media_player")]
    assert keys == [
        "turn_on", "turn_off", "power_toggle", "volume_up", "volume_down",
        "mute", "play", "pause", "stop",
    ]
    assert [o["key"] for o in remote_action_options("light")] == ["turn_on", "turn_off"]
    assert remote_action_options("ac") == []
    assert remote_action_options(None) == []


def test_the_entity_config_is_a_filtered_copy():
    remote = _remote("light", {"turn_on": "t1", "brightness_up": "t2"})
    config = remote_entity_config(remote)
    assert config.command_mapping == {"turn_on": "t1"}
    assert config.platform == "light"
    config.command_mapping["turn_off"] = "t3"
    assert "turn_off" not in remote.entity_config.command_mapping


@pytest.mark.parametrize("platform", REMOTE_PLATFORMS)
def test_identity_name_and_device(platform):
    entity = REMOTE_CLASSES[platform](_remote(TYPE_FOR[platform], {}))
    assert entity._attr_unique_id == f"hair_remote_rem1_{platform}"
    assert entity._attr_unique_id == remote_state_unique_id("rem1", platform)
    assert entity._attr_name is None
    assert entity._attr_has_entity_name is True
    assert entity._attr_assumed_state is True
    assert entity.device_info == {
        "identifiers": {(DOMAIN, "rem1")},
        "name": "Living Room TV Remote",
        "manufacturer": "HAIR",
        "model": "IR Triggers",
    }
    assert isinstance(entity, DEVICE_CLASSES[platform])


def test_the_device_info_matches_the_last_pressed_entity():
    from custom_components.hair.event import HAIRRemoteLastPressedEntity

    remote = _remote("switch")
    assert HAIRRemoteSwitchEntity(remote).device_info == (
        HAIRRemoteLastPressedEntity(remote, {}).device_info
    )


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


def _state(state, **attributes):
    return SimpleNamespace(state=state, attributes=attributes)


@pytest.mark.asyncio
@pytest.mark.parametrize("stored,expected", [
    ("playing", MediaPlayerState.ON),
    ("paused", MediaPlayerState.ON),
    ("idle", MediaPlayerState.ON),
    ("on", MediaPlayerState.ON),
    ("off", MediaPlayerState.OFF),
    ("unavailable", MediaPlayerState.OFF),
])
async def test_media_player_restores_with_round_ones_rule(stored, expected):
    live = await _live(
        "media_player", {}, last_state=_state(
            stored, volume_level=0.3, is_volume_muted=True,
        ),
    )
    assert live.entity.state == expected
    assert live.entity.volume_level == pytest.approx(0.3)
    assert live.entity.is_volume_muted is True


@pytest.mark.asyncio
async def test_fan_restores_power_speed_and_oscillation():
    live = await _live("fan", {}, last_state=_state(
        "on", percentage=50, oscillating=True,
    ))
    e = live.entity
    assert (e.is_on, e.percentage, e.oscillating) == (True, 50, True)


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["light", "switch"])
async def test_light_and_switch_restore_on(platform):
    live = await _live(platform, {}, last_state=_state("on"))
    assert live.entity.is_on is True


@pytest.mark.asyncio
async def test_screen_restores_closed():
    live = await _live("cover", {}, last_state=_state("closed"))
    assert live.entity.is_closed is True


# ---------------------------------------------------------------------------
# The fire path: confirmed presses only, echoes never
# ---------------------------------------------------------------------------


class _Dispatcher:
    """The two dispatcher calls this path makes, wired to each other."""

    def __init__(self):
        self.handlers: dict[str, list] = {}

    def connect(self, hass, signal, fn):
        self.handlers.setdefault(signal, []).append(fn)
        return MagicMock()

    def send(self, hass, signal, *args):
        for fn in list(self.handlers.get(signal, [])):
            fn(*args)

    def patches(self):
        return (
            patch.object(remote_state, "async_dispatcher_connect", side_effect=self.connect),
            patch(
                "custom_components.hair.trigger_manager.async_dispatcher_send",
                side_effect=self.send,
            ),
        )


async def _fire_path_bench(fake_hass, min_hits=1):
    from custom_components.hair.trigger_manager import TriggerManager

    bench = _Bench(fake_hass)
    _store_with(bench, [_remote("switch", {"turn_on": "t1"})], [
        _trigger("t1", "Power", min_hits=min_hits),
    ])
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    tm._dispatch_retransmits = MagicMock()
    dispatcher = _Dispatcher()
    entity = HAIRRemoteSwitchEntity(bench.store.get_trigger_remote("rem1"))
    live = _Live(entity)
    connect, send = dispatcher.patches()
    with connect:
        entity.async_get_last_state = AsyncMock(return_value=None)
        await entity.async_added_to_hass()
    return tm, live, send


@pytest.mark.asyncio
async def test_a_confirmed_fire_moves_the_remote_entity(fake_hass):
    tm, live, send = await _fire_path_bench(fake_hass)
    with send:
        assert tm.on_signal_captured("fp-t1", None, None) == ["t1"]
    assert live.entity.is_on is True


@pytest.mark.asyncio
async def test_below_min_hits_nothing_moves(fake_hass):
    tm, live, send = await _fire_path_bench(fake_hass, min_hits=2)
    with send:
        assert tm.on_signal_captured("fp-t1", None, None) == []
    assert live.entity.is_on is False


@pytest.mark.asyncio
async def test_a_drawer_trigger_sends_no_remote_press(fake_hass):
    from custom_components.hair.trigger_manager import TriggerManager

    bench = _Bench(fake_hass)
    _store_with(bench, [], [_trigger("t9", "Doorbell", remote_id=None)])
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    with patch(
        "custom_components.hair.trigger_manager.async_dispatcher_send"
    ) as send:
        tm.on_signal_captured("fp-t9", None, None)
    assert not any(
        c.args[1] == SIGNAL_REMOTE_PRESSED for c in send.call_args_list
    )


def test_a_failing_remote_entity_never_costs_the_bus_event_or_the_retransmit(fake_hass):
    from custom_components.hair.const import EVENT_TRIGGER_FIRED
    from custom_components.hair.trigger_manager import TriggerManager

    bench = _Bench(fake_hass)
    _store_with(bench, [_remote("switch")], [_trigger("t1", "Power")])
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    tm._dispatch_retransmits = MagicMock()
    with patch(
        "custom_components.hair.trigger_manager.async_dispatcher_send",
        side_effect=RuntimeError("boom"),
    ):
        assert tm.on_signal_captured("fp-t1", None, None) == ["t1"]
    events = [c.args[0] for c in fake_hass.bus.async_fire.call_args_list]
    assert EVENT_TRIGGER_FIRED in events
    tm._dispatch_retransmits.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("echo", [False, True])
async def test_an_echo_moves_nothing(fake_hass, echo):
    """Through a real SignalMonitor and TriggerManager: HAIR's own send
    coming back is claimed before any trigger matches, so the Remote's
    entity never hears it; the same capture with no send behind it is a
    press and moves it."""
    from custom_components.hair import signal_monitor as sm
    from custom_components.hair.signal_monitor import SignalMonitor
    from custom_components.hair.trigger_manager import TriggerManager

    from .test_signal_monitor import _make_event, _make_signal_store, _nec_event

    parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
    n = sm.normalize(parsed)
    bench = _Bench(fake_hass)
    trigger = _trigger("t1", "Power")
    trigger.signal_fingerprint = n.sig_fp
    trigger.decoded_fingerprint = n.decoded_fingerprint
    _store_with(bench, [_remote("switch", {"turn_on": "t1"})], [trigger])
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    tm._dispatch_retransmits = MagicMock()
    monitor = SignalMonitor(fake_hass, _make_signal_store(fake_hass), bench.store, tm)
    if echo:
        with patch.object(sm, "normalize_command", lambda _c: n):
            monitor.record_send(
                object(), "TV / Power", ["infrared.e"],
                decoded_fingerprint=n.decoded_fingerprint, send_count=1,
            )
        monitor._echo_expectations[0]["armed_at"] = 0.0
        monitor._echo_expectations[0]["guard_until"] = 10**12

    dispatcher = _Dispatcher()
    entity = HAIRRemoteSwitchEntity(bench.store.get_trigger_remote("rem1"))
    live = _Live(entity)
    connect, send = dispatcher.patches()
    with connect:
        entity.async_get_last_state = AsyncMock(return_value=None)
        await entity.async_added_to_hass()
    with send:
        await monitor._process_parsed_signal(parsed, receiver_entity_id="infrared.athom_rx")
    assert live.entity.is_on is (not echo)


@pytest.mark.asyncio
async def test_a_pinned_remote_follows_its_press_and_still_drives_its_device(fake_hass):
    """Pinning does not disable, rename or retype it: the Remote's entity
    follows the press, and the same fire still retransmits to the pinned
    Device, whose entity follows that send (round 1)."""
    from custom_components.hair.trigger_manager import TriggerManager

    bench = _Bench(fake_hass)
    remote = _remote("media_player", {"power_toggle": "t1"})
    remote.pinned_device_ids = ["dev1"]
    remote.bindings = {"dev1": {"t1": "c1"}}
    _store_with(bench, [remote], [_trigger("t1", "Power")])
    bench.store.add_device(IRDevice(
        id="dev1", name="Living Room TV", device_type=DeviceType.MEDIA_PLAYER,
        commands=[IRCommand(id="c1", name="Power", protocol="PRONTO", code="x")],
    ))
    retransmit = MagicMock()
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    tm._retransmit = retransmit
    dispatcher = _Dispatcher()
    entity = HAIRRemoteMediaPlayerEntity(remote)
    live = _Live(entity)
    connect, send = dispatcher.patches()
    with connect:
        entity.async_get_last_state = AsyncMock(return_value=None)
        await entity.async_added_to_hass()
    with send:
        tm.on_signal_captured("fp-t1", None, None)
    assert live.entity.state == MediaPlayerState.ON
    targets = [c.args[0] for c in retransmit.dispatch.call_args_list]
    assert targets == [("rem1", "dev1", "c1")]


# ---------------------------------------------------------------------------
# Lifecycle, through the real handlers
# ---------------------------------------------------------------------------


class _RBench(_Bench):
    """The Last pressed bench plus the five Remote state platforms."""

    def __init__(self, fake_hass):
        super().__init__(fake_hass)
        self.state_added: list = []

    def _state_adder(self, platform):
        def _add(entities):
            for entity in entities:
                entity.hass = self.hass
                entity.entity_id = f"{platform}.{entity.remote_id}_state"
                entity.async_write_ha_state = MagicMock()
                entity.async_remove = AsyncMock(
                    side_effect=lambda e=entity: self.removed.append(e)
                )
                self.registry.rows[entity.entity_id] = SimpleNamespace(
                    entity_id=entity.entity_id, domain=platform,
                    platform=DOMAIN, unique_id=entity._attr_unique_id,
                    config_entry_id=ENTRY_ID,
                )
            self.state_added.extend(entities)
        return _add

    async def setup(self):
        await super().setup()
        with _registry_patch(self.registry):
            for platform, cls in REMOTE_CLASSES.items():
                register_remote_platform(
                    self.hass, ENTRY_ID, platform, self._state_adder(platform), cls
                )
        return self

    def state_entity(self, remote_id):
        return remote_state.remote_state_entity(self.hass, ENTRY_ID, remote_id)

    async def ws(self, handler, **msg):
        conn = _conn()
        with _dr(), _registry_patch(self.registry):
            await handler(self.hass, conn, {"id": 1, **msg})
        return conn


async def _bench_with(fake_hass, remotes=(), triggers=()):
    bench = _RBench(fake_hass)
    _store_with(bench, remotes, triggers)
    return await bench.setup()


@pytest.mark.asyncio
async def test_setup_builds_an_entity_for_each_typed_remote_only(fake_hass):
    bench = await _bench_with(fake_hass, [
        _remote("fan", remote_id="rem1"),
        _remote(None, remote_id="rem2"),
        _remote("switch", remote_id="rem3"),
    ])
    assert isinstance(bench.state_entity("rem1"), HAIRRemoteFanEntity)
    assert bench.state_entity("rem2") is None
    assert isinstance(bench.state_entity("rem3"), HAIRRemoteSwitchEntity)


@pytest.mark.asyncio
async def test_an_ac_remote_has_no_state_entity_whatever_it_stores(fake_hass):
    remote = _remote("fan")
    remote.climate_matrix = True
    bench = await _bench_with(fake_hass, [remote])
    assert bench.state_entity("rem1") is None


@pytest.mark.asyncio
async def test_setting_changing_and_clearing_the_type(fake_hass):
    from custom_components.hair.websocket_api import ws_set_trigger_remote_type

    bench = await _bench_with(fake_hass, [_remote(None)])
    conn = await bench.ws(
        ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
        remote_id="rem1", device_type="media_player",
    )
    conn.send_error.assert_not_called()
    result = conn.send_result.call_args[0][1]
    assert result["removed_entity_id"] is None
    assert result["state_entity_id"] == "media_player.rem1_state"
    first = bench.state_entity("rem1")
    assert isinstance(first, HAIRRemoteMediaPlayerEntity)

    conn = await bench.ws(
        ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
        remote_id="rem1", device_type="fan",
    )
    result = conn.send_result.call_args[0][1]
    assert result["removed_entity_id"] == "media_player.rem1_state"
    assert "media_player.rem1_state" in bench.registry.removed
    first.async_remove.assert_called_once()
    assert isinstance(bench.state_entity("rem1"), HAIRRemoteFanEntity)

    conn = await bench.ws(
        ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
        remote_id="rem1", device_type=None,
    )
    result = conn.send_result.call_args[0][1]
    assert result["removed_entity_id"] == "fan.rem1_state"
    assert "fan.rem1_state" in bench.registry.removed
    assert bench.state_entity("rem1") is None
    assert bench.store.get_trigger_remote("rem1").device_type is None


@pytest.mark.asyncio
async def test_clearing_the_type_keeps_the_mapping_for_setting_it_back(fake_hass):
    from custom_components.hair.websocket_api import ws_set_trigger_remote_type

    bench = await _bench_with(
        fake_hass, [_remote("switch", {"turn_on": "t1"})], [_trigger("t1", "On")],
    )
    for device_type in (None, "switch"):
        await bench.ws(
            ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
            remote_id="rem1", device_type=device_type,
        )
    entity = bench.state_entity("rem1")
    assert entity._entity_config.command_mapping == {"turn_on": "t1"}


@pytest.mark.asyncio
@pytest.mark.parametrize("device_type", ["ac", "other", "climate", "remote"])
async def test_a_type_a_remote_cannot_take_is_refused(fake_hass, device_type):
    from custom_components.hair.websocket_api import ws_set_trigger_remote_type

    bench = await _bench_with(fake_hass, [_remote(None)])
    conn = await bench.ws(
        ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
        remote_id="rem1", device_type=device_type,
    )
    conn.send_error.assert_called_once()
    assert bench.store.get_trigger_remote("rem1").device_type is None


@pytest.mark.asyncio
async def test_an_ac_remote_refuses_a_type(fake_hass):
    from custom_components.hair.websocket_api import ws_set_trigger_remote_type

    remote = _remote(None)
    remote.climate_matrix = True
    bench = await _bench_with(fake_hass, [remote])
    conn = await bench.ws(
        ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
        remote_id="rem1", device_type="media_player",
    )
    conn.send_error.assert_called_once()


@pytest.mark.asyncio
async def test_mapping_a_button_follows_the_device_rules(fake_hass):
    from custom_components.hair.websocket_api import ws_update_trigger_remote_mapping

    bench = await _bench_with(
        fake_hass, [_remote("media_player")],
        [_trigger("t1", "Power"), _trigger("t2", "Vol+")],
    )

    async def _map(trigger_id, key):
        return await bench.ws(
            ws_update_trigger_remote_mapping,
            type="hair/trigger-remote/update-mapping",
            remote_id="rem1", trigger_id=trigger_id, action_key=key,
        )

    conn = await _map("t1", "power_toggle")
    conn.send_error.assert_not_called()
    assert conn.send_result.call_args[0][1]["command_mapping"] == {"power_toggle": "t1"}
    # One key per button: a new key replaces the button's old one.
    await _map("t1", "turn_on")
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        "turn_on": "t1",
    }
    # A key reassigned to another button moves.
    await _map("t2", "turn_on")
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        "turn_on": "t2",
    }
    await _map("t2", None)
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {}
    # The live entity took each change.
    bench.state_entity("rem1").async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_a_key_the_entity_cannot_track_or_a_foreign_button_is_refused(fake_hass):
    from custom_components.hair.websocket_api import ws_update_trigger_remote_mapping

    bench = await _bench_with(
        fake_hass, [_remote("media_player"), _remote("switch", remote_id="rem2")],
        [_trigger("t1", "Input"), _trigger("t2", "Power", remote_id="rem2")],
    )
    for trigger_id, key in (("t1", "select_source"), ("t2", "turn_on")):
        conn = await bench.ws(
            ws_update_trigger_remote_mapping,
            type="hair/trigger-remote/update-mapping",
            remote_id="rem1", trigger_id=trigger_id, action_key=key,
        )
        conn.send_error.assert_called_once()
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {}


@pytest.mark.asyncio
async def test_deleting_a_button_takes_its_keys(fake_hass):
    from custom_components.hair.websocket_api import ws_delete_trigger

    bench = await _bench_with(
        fake_hass, [_remote("switch", {"turn_on": "t1", "turn_off": "t2"})],
        [_trigger("t1", "On"), _trigger("t2", "Off")],
    )
    await bench.ws(ws_delete_trigger, type="hair/trigger/delete", trigger_id="t1")
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        "turn_off": "t2",
    }


@pytest.mark.asyncio
async def test_deleting_a_remote_removes_its_state_entity_and_row(fake_hass):
    from custom_components.hair.websocket_api import ws_delete_trigger_remote

    bench = await _bench_with(fake_hass, [_remote("light")], [_trigger("t1", "On")])
    entity = bench.state_entity("rem1")
    await bench.ws(
        ws_delete_trigger_remote, type="hair/trigger-remote/delete", remote_id="rem1",
    )
    assert bench.state_entity("rem1") is None
    entity.async_remove.assert_called_once()
    assert "light.rem1_state" in bench.registry.removed


@pytest.mark.asyncio
async def test_a_rename_reaches_the_entity_through_its_device(fake_hass):
    from custom_components.hair.websocket_api import ws_rename_trigger_remote

    bench = await _bench_with(fake_hass, [_remote("switch")])
    await bench.ws(
        ws_rename_trigger_remote, type="hair/trigger-remote/rename",
        remote_id="rem1", name="Bedroom Fan Remote",
    )
    entity = bench.state_entity("rem1")
    assert entity.device_info["name"] == "Bedroom Fan Remote"
    entity.async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_duplicate_keeps_the_type_and_moves_the_mapping_to_the_new_buttons(fake_hass):
    from custom_components.hair.websocket_api import ws_duplicate_trigger_remote

    bench = await _bench_with(
        fake_hass, [_remote("switch", {"turn_on": "t1", "turn_off": "t2"})],
        [_trigger("t1", "On"), _trigger("t2", "Off")],
    )
    conn = await bench.ws(
        ws_duplicate_trigger_remote, type="hair/trigger-remote/duplicate",
        remote_id="rem1", new_name="Copy",
    )
    conn.send_error.assert_not_called()
    clone = bench.store.get_trigger_remote(conn.send_result.call_args[0][1]["id"])
    assert clone.device_type == "switch"
    by_name = {t.name: t.id for t in bench.store.get_triggers_for_remote(clone.id)}
    assert clone.entity_config.command_mapping == {
        "turn_on": by_name["On"], "turn_off": by_name["Off"],
    }
    assert isinstance(bench.state_entity(clone.id), HAIRRemoteSwitchEntity)
    # The source is untouched.
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        "turn_on": "t1", "turn_off": "t2",
    }


PRONTO = "0000 006D 0002 0000 0020 0020 0040 0040"


def _tv_device(device_type=DeviceType.MEDIA_PLAYER):
    return IRDevice(
        id="dev1", name="Living Room TV", device_type=device_type,
        commands=[
            IRCommand(id="c1", name="Power", protocol="PRONTO", code=PRONTO),
            IRCommand(id="c2", name="Vol Up", protocol="PRONTO", code=PRONTO),
            IRCommand(id="c3", name="Input", protocol="PRONTO", code=PRONTO),
        ],
        entity_config=EntityConfig(command_mapping={
            "power_toggle": "Power", "volume_up": "Vol Up",
            "select_source": "Input", "mute": "Gone",
        }),
    )


@pytest.mark.asyncio
async def test_make_a_remote_takes_the_devices_type_and_mapping(fake_hass):
    from custom_components.hair.websocket_api import ws_device_make_remote

    bench = await _bench_with(fake_hass)
    bench.store.add_device(_tv_device())
    bench.data["device_manager"] = MagicMock(get_device=bench.store.get_device)
    conn = await bench.ws(
        ws_device_make_remote, type="hair/device/make-remote",
        device_id="dev1", name="Living Room TV Remote",
    )
    conn.send_error.assert_not_called()
    remote = bench.store.get_trigger_remote(conn.send_result.call_args[0][1]["id"])
    by_command = {
        t.source_command_id: t.id for t in bench.store.get_triggers_for_remote(remote.id)
    }
    assert remote.device_type == "media_player"
    # Untrackable select_source and the dangling mute are dropped.
    assert remote.entity_config.command_mapping == {
        "power_toggle": by_command["c1"], "volume_up": by_command["c2"],
    }
    assert isinstance(bench.state_entity(remote.id), HAIRRemoteMediaPlayerEntity)


@pytest.mark.asyncio
async def test_make_a_remote_from_an_ac_or_other_device_starts_untyped(fake_hass):
    from custom_components.hair.websocket_api import ws_device_make_remote

    bench = await _bench_with(fake_hass)
    bench.store.add_device(_tv_device(DeviceType.OTHER))
    bench.data["device_manager"] = MagicMock(get_device=bench.store.get_device)
    conn = await bench.ws(
        ws_device_make_remote, type="hair/device/make-remote",
        device_id="dev1", name="Remote",
    )
    remote = bench.store.get_trigger_remote(conn.send_result.call_args[0][1]["id"])
    assert remote.device_type is None
    assert bench.state_entity(remote.id) is None


async def _make_device(fake_hass, chosen_type):
    from custom_components.hair.websocket_api import ws_trigger_remote_make_device

    remote = _remote("fan", {"power_toggle": "t1", "oscillate": "t2"})
    bench = await _bench_with(fake_hass, [remote], [
        IRTrigger(id="t1", name="Power", trigger_remote_id="rem1",
                  protocol="PRONTO", code=PRONTO, signal_fingerprint="fp1"),
        IRTrigger(id="t2", name="Swing", trigger_remote_id="rem1",
                  protocol="PRONTO", code=PRONTO, signal_fingerprint="fp2"),
    ])
    created: list[IRDevice] = []
    manager = MagicMock()
    manager.async_create_device = AsyncMock(side_effect=created.append)
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    bench.data["device_manager"] = manager
    with patch(
        "custom_components.hair.websocket_api._device_full",
        AsyncMock(return_value={}),
    ):
        conn = await bench.ws(
            ws_trigger_remote_make_device, type="hair/trigger-remote/make-device",
            remote_id="rem1", name="Bedroom Fan", device_type=chosen_type,
            emitter_entity_ids=[],
        )
    conn.send_error.assert_not_called()
    return created[0], manager


@pytest.mark.asyncio
async def test_make_a_device_from_a_typed_remote_copies_its_mapping(fake_hass):
    device, manager = await _make_device(fake_hass, "fan")
    assert device.device_type == DeviceType.FAN
    assert device.entity_config.command_mapping == {
        "power_toggle": "Power", "oscillate": "Swing",
    }
    manager._auto_map_command.assert_not_called()


@pytest.mark.asyncio
async def test_make_a_device_of_another_type_auto_maps_as_before(fake_hass):
    device, manager = await _make_device(fake_hass, "light")
    assert device.entity_config.command_mapping == {}
    assert manager._auto_map_command.call_count == 2


@pytest.mark.asyncio
async def test_the_list_payload_carries_the_type(fake_hass):
    from custom_components.hair.websocket_api import ws_list_trigger_remotes

    bench = await _bench_with(
        fake_hass, [_remote("light", {"turn_on": "t1", "brightness_up": "t2"})],
    )
    conn = await bench.ws(ws_list_trigger_remotes, type="hair/trigger-remotes/list")
    row = conn.send_result.call_args[0][1][0]
    assert row["device_type"] == "light"
    assert row["command_mapping"] == {"turn_on": "t1"}
    assert row["state_entity_id"] == "light.rem1_state"
    assert [o["key"] for o in row["action_options"]] == ["turn_on", "turn_off"]


def test_every_handler_that_changes_a_remote_still_syncs_state():
    """The state entities ride ``sync_remote_entities``: pinned so a
    refactor cannot drop the hook that every handler relies on."""
    import inspect

    from custom_components.hair import event

    assert "sync_remote_state_entities" in inspect.getsource(event.sync_remote_entities)


@pytest.mark.asyncio
async def test_each_platform_setup_registers_its_remote_class(fake_hass):
    import importlib

    for platform, cls in REMOTE_CLASSES.items():
        module = importlib.import_module(f"custom_components.hair.{platform}")
        bench = _RBench(fake_hass)
        _store_with(bench, [_remote(TYPE_FOR[platform])])
        bench.data["entity_factory"] = MagicMock()
        bench.data["device_manager"] = MagicMock(get_all_devices=MagicMock(return_value=[]))
        added: list = []
        with _registry_patch(bench.registry):
            await module.async_setup_entry(
                fake_hass, SimpleNamespace(entry_id=ENTRY_ID), added.extend,
            )
        assert [type(e) for e in added] == [cls]


# ---------------------------------------------------------------------------
# The orphan sweep
# ---------------------------------------------------------------------------


def test_classify_reads_both_remote_rows_as_the_remotes():
    for unique_id in (
        remote_state_unique_id("abc-1", "media_player"),
        remote_state_unique_id("abc-1", "fan"),
        remote_last_pressed_unique_id("abc-1"),
    ):
        row = classify_unique_id(unique_id)
        assert (row.family, row.remote_id) == ("remote", "abc-1")
    assert classify_unique_id("hair_remote_") is None
    assert classify_unique_id("hair_remote_abc") is None


class _SweepStore:
    loaded = True

    def __init__(self, remotes, devices=()):
        self._remotes = list(remotes)
        self._devices = list(devices)

    def get_all_devices(self):
        return list(self._devices)

    def get_all_triggers(self):
        return [_trigger("t1", "Power")]

    def get_all_trigger_remotes(self):
        return list(self._remotes)


def test_a_living_remotes_rows_survive_and_an_orphans_go(fake_hass):
    registry = FakeRegistry([
        ("media_player.living", remote_state_unique_id("live-1", "media_player")),
        ("event.living_last_pressed", remote_last_pressed_unique_id("live-1")),
        ("fan.gone", remote_state_unique_id("gone-1", "fan")),
        ("event.gone_last_pressed", remote_last_pressed_unique_id("gone-1")),
    ])
    store = _SweepStore([_remote("media_player", remote_id="live-1")])
    with _registry_patch(registry):
        result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
    assert result.removed == 2
    assert sorted(registry.removed) == ["event.gone_last_pressed", "fan.gone"]
    assert "media_player.living" in registry.rows
    assert "event.living_last_pressed" in registry.rows


def test_a_remote_row_is_never_read_as_a_device_platform_row(fake_hass):
    """The bug the plan caught: the platform family would read
    ``hair_remote_<id>_media_player`` as a Device ``remote_<id>``."""
    registry = FakeRegistry([
        ("media_player.living", remote_state_unique_id("live-1", "media_player")),
    ])
    store = _SweepStore([_remote("media_player", remote_id="live-1")], devices=[
        IRDevice(id="dev1", name="TV"),
    ])
    with _registry_patch(registry):
        reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
    assert registry.removed == []


# ---------------------------------------------------------------------------
# The fan speed cycle on a Remote (rebased onto the speed cycle round)
# ---------------------------------------------------------------------------


def _cycle_remote(steps=3, includes_off=False, extra=None):
    mapping = {"speed_cycle": "t-cycle", **(extra or {})}
    remote = _remote("fan", mapping)
    remote.entity_config.fan_speed_steps = steps
    remote.entity_config.speed_cycle_includes_off = includes_off
    return remote


async def _live_remote(remote, last_state=None):
    return await _Live(HAIRRemoteFanEntity(remote)).add(last_state)


@pytest.mark.asyncio
async def test_a_heard_cycle_press_moves_the_remotes_count_and_wraps():
    from homeassistant.components.fan import FanEntityFeature

    live = await _live_remote(_cycle_remote(steps=3))
    e = live.entity
    assert int(e.supported_features) & FanEntityFeature.SET_SPEED
    assert e.speed_count == 3
    # Off, off not in the cycle: the press wakes it on its turn-on
    # choice without stepping (the speed cycle round's ruling).
    live.press("t-cycle")
    assert (e.is_on, e.percentage) == (True, 33)
    live.press("t-cycle")
    assert e.percentage == 66
    live.press("t-cycle")
    assert e.percentage == 100
    live.press("t-cycle")
    assert e.percentage == 33


@pytest.mark.asyncio
async def test_with_off_in_the_cycle_a_press_wraps_through_off():
    live = await _live_remote(_cycle_remote(steps=2, includes_off=True))
    e = live.entity
    live.press("t-cycle")
    assert (e.is_on, e.percentage) == (True, 50)
    live.press("t-cycle")
    assert (e.is_on, e.percentage) == (True, 100)
    live.press("t-cycle")
    assert e.is_on is False


@pytest.mark.asyncio
async def test_without_a_speed_count_a_remote_fan_offers_no_speed_control():
    from homeassistant.components.fan import FanEntityFeature

    remote = _cycle_remote()
    remote.entity_config.fan_speed_steps = None
    live = await _live_remote(remote)
    e = live.entity
    assert not int(e.supported_features) & FanEntityFeature.SET_SPEED
    live.press("t-cycle")
    assert e.percentage is None


@pytest.mark.asyncio
async def test_setting_a_cycle_speed_sends_nothing_and_waits_for_nothing():
    live = await _live_remote(_cycle_remote(steps=3, extra={"power_toggle": "t-p"}))
    e = live.entity
    recorder = _armed_with_a_device(e)
    with patch("custom_components.hair.fan.asyncio.sleep", AsyncMock()) as sleep:
        await e.async_turn_on()
        await e.async_set_percentage(100)
        assert (e.is_on, e.percentage) == (True, 100)
        await e.async_set_percentage(33)
        assert e.percentage == 33
        await e.async_turn_off()
        assert e.is_on is False
    recorder.async_send_command.assert_not_called()
    sleep.assert_not_called()


def test_a_remote_fan_can_be_mapped_to_the_speed_cycle():
    keys = [o["key"] for o in remote_action_options("fan")]
    assert "speed_cycle" in keys


@pytest.mark.asyncio
async def test_make_a_remote_from_a_cycle_fan_takes_its_cycle_settings(fake_hass):
    from custom_components.hair.websocket_api import ws_device_make_remote

    bench = await _bench_with(fake_hass)
    device = IRDevice(
        id="dev1", name="Bedroom Fan", device_type=DeviceType.FAN,
        commands=[IRCommand(id="c1", name="Speed", protocol="PRONTO", code=PRONTO)],
        entity_config=EntityConfig(command_mapping={"speed_cycle": "Speed"}),
    )
    device.entity_config.fan_speed_steps = 3
    device.entity_config.speed_cycle_includes_off = True
    bench.store.add_device(device)
    bench.data["device_manager"] = MagicMock(get_device=bench.store.get_device)
    conn = await bench.ws(
        ws_device_make_remote, type="hair/device/make-remote",
        device_id="dev1", name="Bedroom Fan Remote",
    )
    remote = bench.store.get_trigger_remote(conn.send_result.call_args[0][1]["id"])
    (trigger,) = bench.store.get_triggers_for_remote(remote.id)
    assert remote.entity_config.command_mapping == {"speed_cycle": trigger.id}
    assert remote.entity_config.fan_speed_steps == 3
    assert remote.entity_config.speed_cycle_includes_off is True
    assert bench.state_entity(remote.id).speed_count == 3


@pytest.mark.asyncio
async def test_make_a_device_from_a_cycle_remote_copies_its_cycle_settings(fake_hass):
    from custom_components.hair.websocket_api import ws_trigger_remote_make_device

    remote = _cycle_remote(steps=4, includes_off=True)
    remote.entity_config.command_mapping = {"speed_cycle": "t1"}
    bench = await _bench_with(fake_hass, [remote], [
        IRTrigger(id="t1", name="Speed", trigger_remote_id="rem1",
                  protocol="PRONTO", code=PRONTO, signal_fingerprint="fp1"),
    ])
    created: list[IRDevice] = []
    manager = MagicMock()
    manager.async_create_device = AsyncMock(side_effect=created.append)
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    bench.data["device_manager"] = manager
    with patch(
        "custom_components.hair.websocket_api._device_full",
        AsyncMock(return_value={}),
    ):
        await bench.ws(
            ws_trigger_remote_make_device, type="hair/trigger-remote/make-device",
            remote_id="rem1", name="Bedroom Fan", device_type="fan",
            emitter_entity_ids=[],
        )
    config = created[0].entity_config
    assert config.command_mapping == {"speed_cycle": "Speed"}
    assert (config.fan_speed_steps, config.speed_cycle_includes_off) == (4, True)


# ---------------------------------------------------------------------------
# Filling the buttons when a type is picked (owner bench, 2026-10-22)
# ---------------------------------------------------------------------------

TV_COMMANDS = [
    ("c-power", "Power", "power_toggle"),
    ("c-on", "Power On", "turn_on"),
    ("c-off", "Power Off", "turn_off"),
    ("c-mute", "Mute", "mute"),
    ("c-vup", "Vol Up", "volume_up"),
    ("c-vdn", "Vol Down", "volume_down"),
    ("c-chup", "Ch Up", "channel_up"),
    ("c-chdn", "Ch Down", "channel_down"),
    ("c-play", "Play", "play"),
    ("c-ff", "FF", "fast_forward"),
    ("c-rew", "Rewind", "rewind"),
    ("c-pause", "Pause", "pause"),
]


def _samsung_test_tv(device_id="dev-tv", device_type=DeviceType.MEDIA_PLAYER):
    return IRDevice(
        id=device_id, name="Samsung Test TV", device_type=device_type,
        commands=[
            IRCommand(id=cid, name=name, protocol="PRONTO", code=PRONTO)
            for cid, name, _ in TV_COMMANDS
        ],
        entity_config=EntityConfig(command_mapping={
            key: name for _, name, key in TV_COMMANDS
        }),
    )


def _samsung_remote(pinned=("dev-tv",), mapping=None):
    """The Samsung TV Remote: buttons named as the handset learned them
    (so names alone would not map them), bound by the pin to the TV's
    commands. A second button is bound to Power; Pause is bound to none."""
    remote = _remote(None, mapping)
    remote.pinned_device_ids = list(pinned)
    bound = {
        "b-power": "c-power", "b-on": "c-on", "b-off": "c-off",
        "b-mute": "c-mute", "b-vup": "c-vup", "b-vdn": "c-vdn",
        "b-chup": "c-chup", "b-chdn": "c-chdn", "b-play": "c-play",
        "b-ff": "c-ff", "b-rew": "c-rew", "b-power2": "c-power",
    }
    remote.bindings = {device_id: dict(bound) for device_id in pinned}
    triggers = [
        IRTrigger(
            id=tid, name=f"KEY_{i}", trigger_remote_id="rem1", order=i,
            signal_fingerprint=f"fp-{tid}",
        )
        for i, tid in enumerate(bound)
    ]
    return remote, triggers


async def _set_type(bench, device_type, dry_run=False):
    from custom_components.hair.websocket_api import ws_set_trigger_remote_type

    conn = await bench.ws(
        ws_set_trigger_remote_type, type="hair/trigger-remote/set-type",
        remote_id="rem1", device_type=device_type, dry_run=dry_run,
    )
    conn.send_error.assert_not_called()
    return conn.send_result.call_args[0][1]


async def _named_bench(fake_hass, names, remote=None, devices=()):
    remote = remote or _remote(None)
    triggers = [
        IRTrigger(id=f"t{i}", name=name, trigger_remote_id="rem1", order=i,
                  signal_fingerprint=f"fp{i}")
        for i, name in enumerate(names)
    ]
    bench = await _bench_with(fake_hass, [remote], triggers)
    for device in devices:
        bench.store.add_device(device)
    return bench


@pytest.mark.asyncio
async def test_a_type_pick_fills_from_the_one_pinned_device(fake_hass):
    remote, triggers = _samsung_remote()
    bench = await _bench_with(fake_hass, [remote], triggers)
    bench.store.add_device(_samsung_test_tv())
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "pin"
    assert result["fill_device_name"] == "Samsung Test TV"
    # Channel, fast forward and rewind cannot be tracked; Pause has no
    # bound button; Power goes to the FIRST button bound to it.
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        "power_toggle": "b-power", "turn_on": "b-on", "turn_off": "b-off",
        "mute": "b-mute", "volume_up": "b-vup", "volume_down": "b-vdn",
        "play": "b-play",
    }
    assert result["fill_count"] == 7
    assert result["command_mapping"]["power_toggle"] == "b-power"
    # The entity follows the handset straight away.
    entity = bench.state_entity("rem1")
    assert entity._entity_config.command_mapping["power_toggle"] == "b-power"


@pytest.mark.asyncio
async def test_a_pin_fill_takes_the_devices_settings(fake_hass):
    remote, triggers = _samsung_remote()
    fan = _samsung_test_tv(device_type=DeviceType.FAN)
    fan.entity_config.command_mapping = {"speed_cycle": "Power"}
    fan.entity_config.fan_speed_steps = 3
    bench = await _bench_with(fake_hass, [remote], triggers)
    bench.store.add_device(fan)
    result = await _set_type(bench, "fan")
    assert result["fill_source"] == "pin"
    config = bench.store.get_trigger_remote("rem1").entity_config
    assert config.command_mapping == {"speed_cycle": "b-power"}
    assert config.fan_speed_steps == 3
    assert bench.state_entity("rem1").speed_count == 3


NAMES = ["Power", "Volume Up", "Mute", "Input", "KEY_42", "Power"]
BY_NAME = {"power_toggle": "t0", "volume_up": "t1", "mute": "t2"}


@pytest.mark.asyncio
async def test_with_no_pin_buttons_are_mapped_by_name(fake_hass):
    bench = await _named_bench(fake_hass, NAMES)
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "names"
    # Input is a source picker (untracked); the second Power loses to
    # the first.
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == BY_NAME
    assert result["fill_count"] == 3


@pytest.mark.asyncio
async def test_two_pinned_devices_of_the_type_fall_back_to_names(fake_hass):
    remote = _remote(None)
    remote.pinned_device_ids = ["dev-a", "dev-b"]
    remote.bindings = {"dev-a": {"t0": "c-power"}, "dev-b": {"t0": "c-power"}}
    bench = await _named_bench(fake_hass, NAMES, remote, [
        _samsung_test_tv("dev-a"), _samsung_test_tv("dev-b"),
    ])
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "names"
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == BY_NAME


@pytest.mark.asyncio
async def test_a_pinned_device_of_another_type_falls_back_to_names(fake_hass):
    remote = _remote(None)
    remote.pinned_device_ids = ["dev-a"]
    remote.bindings = {"dev-a": {"t0": "c-power"}}
    bench = await _named_bench(fake_hass, NAMES, remote, [
        _samsung_test_tv("dev-a", DeviceType.LIGHT),
    ])
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "names"


@pytest.mark.asyncio
async def test_names_in_another_language_map_through_the_synonyms(fake_hass):
    """German template names (vocab.mute "Stumm", vocab.volume_up
    "Lautstärke +"): the Device's localized auto-map, shared."""
    bench = await _named_bench(fake_hass, ["Stumm", "Lautstärke +"])
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "names"
    assert result["command_mapping"] == {"mute": "t0", "volume_up": "t1"}


@pytest.mark.asyncio
async def test_nothing_mappable_reports_none_and_maps_nothing(fake_hass):
    bench = await _named_bench(fake_hass, ["KEY_1", "KEY_2"])
    result = await _set_type(bench, "switch")
    assert (result["fill_source"], result["fill_count"]) == ("none", 0)
    assert result["command_mapping"] == {}


@pytest.mark.asyncio
async def test_a_mapping_that_is_there_is_never_touched(fake_hass):
    remote, triggers = _samsung_remote(mapping={"mute": "b-power"})
    bench = await _bench_with(fake_hass, [remote], triggers)
    bench.store.add_device(_samsung_test_tv())
    result = await _set_type(bench, "media_player")
    assert (result["fill_source"], result["fill_count"]) == ("kept", 1)
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        "mute": "b-power",
    }


@pytest.mark.asyncio
async def test_a_mapping_kept_across_a_clear_comes_back_untouched(fake_hass):
    remote, triggers = _samsung_remote()
    bench = await _bench_with(fake_hass, [remote], triggers)
    bench.store.add_device(_samsung_test_tv())
    await _set_type(bench, "media_player")
    from custom_components.hair.websocket_api import ws_update_trigger_remote_mapping

    await bench.ws(
        ws_update_trigger_remote_mapping, type="hair/trigger-remote/update-mapping",
        remote_id="rem1", trigger_id="b-mute", action_key=None,
    )
    edited = dict(bench.store.get_trigger_remote("rem1").entity_config.command_mapping)
    await _set_type(bench, None)
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "kept"
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == edited


@pytest.mark.asyncio
async def test_a_fill_keeps_another_types_keys_unless_they_clash(fake_hass):
    remote = _remote(None, {"speed_up": "t3", "oscillate": "t0"})
    bench = await _named_bench(fake_hass, NAMES, remote)
    await _set_type(bench, "media_player")
    # t0 is now power_toggle, so oscillate on t0 goes; speed_up on t3
    # (a button the fill left alone) stays for a later switch back.
    assert bench.store.get_trigger_remote("rem1").entity_config.command_mapping == {
        **BY_NAME, "speed_up": "t3",
    }


@pytest.mark.asyncio
async def test_a_pin_walk_that_maps_nothing_falls_back_to_names(fake_hass):
    remote = _remote(None)
    remote.pinned_device_ids = ["dev-a"]
    remote.bindings = {"dev-a": {}}
    bench = await _named_bench(fake_hass, NAMES, remote, [_samsung_test_tv("dev-a")])
    result = await _set_type(bench, "media_player")
    assert result["fill_source"] == "names"


@pytest.mark.asyncio
async def test_dry_run_reports_and_changes_nothing(fake_hass):
    remote, triggers = _samsung_remote()
    remote.device_type = "switch"
    bench = await _bench_with(fake_hass, [remote], triggers)
    bench.store.add_device(_samsung_test_tv())
    before = bench.store.get_trigger_remote("rem1").to_dict()
    saves = bench.store.async_save.await_count
    result = await _set_type(bench, "media_player", dry_run=True)
    assert result["dry_run"] is True
    assert (result["fill_source"], result["fill_count"]) == ("pin", 7)
    assert result["fill_device_name"] == "Samsung Test TV"
    assert result["removed_entity_id"] == "switch.rem1_state"
    assert bench.store.get_trigger_remote("rem1").to_dict() == before
    assert bench.store.async_save.await_count == saves
    assert bench.registry.removed == []
    assert isinstance(bench.state_entity("rem1"), HAIRRemoteSwitchEntity)


@pytest.mark.asyncio
async def test_dry_run_of_a_clear_reports_only_the_removal(fake_hass):
    bench = await _bench_with(fake_hass, [_remote("light")])
    result = await _set_type(bench, None, dry_run=True)
    assert result["removed_entity_id"] == "light.rem1_state"
    assert (result["fill_source"], result["fill_count"]) == (None, 0)
    assert bench.store.get_trigger_remote("rem1").device_type == "light"


def test_the_device_auto_map_uses_the_shared_lookup():
    """One lookup for commands and buttons: the Device's auto-map still
    maps, temperature presets included, through ``auto_map_feature``."""
    from custom_components.hair.device_manager import DeviceManager, auto_map_feature

    assert auto_map_feature("Volume Up", "media_player") == "volume_up"
    assert auto_map_feature("Temp 24", DeviceType.AC) == "temp_24"
    assert auto_map_feature("Temp 24", "media_player") is None
    device = IRDevice(name="AC", device_type=DeviceType.AC)
    command = IRCommand(name="Temp 24")
    DeviceManager._auto_map_command(MagicMock(), device, command)
    assert device.entity_config.command_mapping == {"temp_24": "Temp 24"}
    assert device.entity_config.temperature_presets == [24]


# ---------------------------------------------------------------------------
# Pinning a typed Remote that maps nothing fills it (owner bench, 2026-10-27)
# ---------------------------------------------------------------------------


def _decoded_tv(device_id="dev-tv", device_type=DeviceType.MEDIA_PLAYER):
    """The Samsung Test TV with decoded identities, so pinning derives
    real bindings (decoded tier first, as pin_bindings matches)."""
    tv = _samsung_test_tv(device_id, device_type)
    for command in tv.commands:
        command.decoded_fingerprint = f"dfp-{command.id}"
    return tv


#: The handset's buttons and the TV command each one carries, as the
#: Samsung TV Remote learned them: names that map nothing by name, a
#: second Power, and no Pause.
HANDSET = [
    ("b-power", "c-power"), ("b-on", "c-on"), ("b-off", "c-off"),
    ("b-mute", "c-mute"), ("b-vup", "c-vup"), ("b-vdn", "c-vdn"),
    ("b-chup", "c-chup"), ("b-chdn", "c-chdn"), ("b-play", "c-play"),
    ("b-ff", "c-ff"), ("b-rew", "c-rew"), ("b-power2", "c-power"),
]
FROM_TV = {
    "power_toggle": "b-power", "turn_on": "b-on", "turn_off": "b-off",
    "mute": "b-mute", "volume_up": "b-vup", "volume_down": "b-vdn",
    "play": "b-play",
}


async def _pin_bench(fake_hass, device_type="media_player", mapping=None,
                     devices=(), pinned=(), climate_matrix=False):
    remote = _remote(device_type, mapping)
    remote.climate_matrix = climate_matrix
    remote.pinned_device_ids = list(pinned)
    triggers = [
        IRTrigger(
            id=tid, name=f"KEY_{i}", trigger_remote_id="rem1", order=i,
            signal_fingerprint=f"fp-{tid}", decoded_fingerprint=f"dfp-{cid}",
        )
        for i, (tid, cid) in enumerate(HANDSET)
    ]
    bench = await _bench_with(fake_hass, [remote], triggers)
    for device in devices:
        bench.store.add_device(device)
    if pinned:
        from custom_components.hair.pin_bindings import rederive_remote

        rederive_remote(bench.store, bench.store.get_trigger_remote("rem1"))
    return bench


async def _pin(bench, device_id, unpin=False):
    from custom_components.hair.websocket_api import (
        ws_pin_trigger_remote_device,
        ws_unpin_trigger_remote_device,
    )

    handler = ws_unpin_trigger_remote_device if unpin else ws_pin_trigger_remote_device
    conn = await bench.ws(
        handler,
        type=f"hair/trigger-remote/{'unpin' if unpin else 'pin'}",
        remote_id="rem1", device_id=device_id,
    )
    conn.send_error.assert_not_called()
    return conn.send_result.call_args[0][1]


def _mapping(bench):
    return bench.store.get_trigger_remote("rem1").entity_config.command_mapping


@pytest.mark.asyncio
async def test_pinning_a_typed_remote_that_maps_nothing_fills_it(fake_hass):
    bench = await _pin_bench(fake_hass, devices=[_decoded_tv()])
    result = await _pin(bench, "dev-tv")
    assert _mapping(bench) == FROM_TV
    assert (result["fill_source"], result["fill_count"]) == ("pin", 7)
    assert result["fill_device_name"] == "Samsung Test TV"
    assert result["pinned_device_ids"] == ["dev-tv"]
    # The live entity follows the handset straight away.
    assert bench.state_entity("rem1")._entity_config.command_mapping == FROM_TV


@pytest.mark.asyncio
async def test_a_pin_fill_brings_the_devices_settings(fake_hass):
    fan = _decoded_tv(device_type=DeviceType.FAN)
    fan.entity_config.command_mapping = {"speed_cycle": "Power"}
    fan.entity_config.fan_speed_steps = 4
    bench = await _pin_bench(fake_hass, device_type="fan", devices=[fan])
    await _pin(bench, "dev-tv")
    config = bench.store.get_trigger_remote("rem1").entity_config
    assert config.command_mapping == {"speed_cycle": "b-power"}
    assert config.fan_speed_steps == 4
    assert bench.state_entity("rem1").speed_count == 4


@pytest.mark.asyncio
async def test_pinning_again_fills_a_remote_typed_before_the_fill(fake_hass):
    """The owner's bench: already pinned, typed, nothing mapped. Unpin
    and pin again fills it; so does pinning the same Device again."""
    bench = await _pin_bench(
        fake_hass, devices=[_decoded_tv()], pinned=["dev-tv"],
    )
    assert _mapping(bench) == {}
    await _pin(bench, "dev-tv")
    assert _mapping(bench) == FROM_TV


@pytest.mark.asyncio
async def test_unpin_then_pin_fills_it(fake_hass):
    bench = await _pin_bench(
        fake_hass, devices=[_decoded_tv()], pinned=["dev-tv"],
    )
    await _pin(bench, "dev-tv", unpin=True)
    assert _mapping(bench) == {}
    await _pin(bench, "dev-tv")
    assert _mapping(bench) == FROM_TV


@pytest.mark.asyncio
async def test_a_remote_that_already_maps_buttons_is_unchanged_by_a_pin(fake_hass):
    bench = await _pin_bench(
        fake_hass, mapping={"mute": "b-power"}, devices=[_decoded_tv()],
    )
    result = await _pin(bench, "dev-tv")
    assert _mapping(bench) == {"mute": "b-power"}
    assert (result["fill_source"], result["fill_count"]) == (None, 0)


@pytest.mark.asyncio
async def test_an_untyped_remote_is_unchanged_by_a_pin(fake_hass):
    bench = await _pin_bench(fake_hass, device_type=None, devices=[_decoded_tv()])
    await _pin(bench, "dev-tv")
    assert _mapping(bench) == {}
    assert bench.store.get_trigger_remote("rem1").device_type is None


@pytest.mark.asyncio
async def test_a_lattice_remote_is_unchanged_by_a_pin(fake_hass):
    bench = await _pin_bench(
        fake_hass, devices=[_decoded_tv()], climate_matrix=True,
    )
    await _pin(bench, "dev-tv")
    assert _mapping(bench) == {}


@pytest.mark.asyncio
async def test_pinning_a_device_of_another_type_changes_nothing(fake_hass):
    bench = await _pin_bench(
        fake_hass, devices=[_decoded_tv(device_type=DeviceType.LIGHT)],
    )
    result = await _pin(bench, "dev-tv")
    assert _mapping(bench) == {}
    assert result["fill_source"] is None


@pytest.mark.asyncio
async def test_a_second_pinned_device_of_the_type_changes_nothing(fake_hass):
    bench = await _pin_bench(
        fake_hass, devices=[_decoded_tv("dev-a"), _decoded_tv("dev-b")],
        pinned=["dev-a"],
    )
    # One pinned already, nothing mapped (typed before the fill): pinning
    # a second of the same type leaves two candidates, so no fill.
    await _pin(bench, "dev-b")
    assert _mapping(bench) == {}


@pytest.mark.asyncio
async def test_a_pin_never_fills_by_name(fake_hass):
    """Buttons that would map by name, a pinned Device whose bindings
    carry nothing trackable: the pin fills nothing (names are the type
    pick's job)."""
    tv = _decoded_tv()
    for command in tv.commands:
        command.decoded_fingerprint = None
    remote = _remote("media_player")
    triggers = [
        IRTrigger(id="t0", name="Power", trigger_remote_id="rem1", order=0,
                  signal_fingerprint="fp-x"),
    ]
    bench = await _bench_with(fake_hass, [remote], triggers)
    bench.store.add_device(tv)
    result = await _pin(bench, "dev-tv")
    assert _mapping(bench) == {}
    assert result["fill_source"] is None


@pytest.mark.asyncio
async def test_unpinning_never_clears_a_mapping(fake_hass):
    bench = await _pin_bench(fake_hass, devices=[_decoded_tv()])
    await _pin(bench, "dev-tv")
    await _pin(bench, "dev-tv", unpin=True)
    assert _mapping(bench) == FROM_TV


@pytest.mark.asyncio
async def test_pinning_another_type_never_fills_from_an_earlier_pin(fake_hass):
    """Already pinned to the TV but typed before the fill existed:
    pinning a light fills nothing from the TV. Only the Device just
    pinned can be the source."""
    bench = await _pin_bench(
        fake_hass,
        devices=[_decoded_tv(), _decoded_tv("dev-lamp", DeviceType.LIGHT)],
        pinned=["dev-tv"],
    )
    result = await _pin(bench, "dev-lamp")
    assert _mapping(bench) == {}
    assert result["fill_source"] is None
