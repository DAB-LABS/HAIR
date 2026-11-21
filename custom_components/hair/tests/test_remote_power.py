"""A typed Remote's state source: power tracking for Remotes.

A typed Remote whose type has power (media player, fan, light, switch)
can have what a Device has: a power sensor in watts with two thresholds,
or an on/off entity, and the settle window. Every rule is the Device's:

- the four fields, stored on the Remote under the Device's names, only
  while a source is set, and kept by an older build (``_extra``);
- one power monitor for both, so the classification, the seed, the
  window and the handback are the Device's code;
- what opens a Remote's window is a heard press that changes power,
  since a Remote sends nothing: on says on, off says off, a toggle
  promises nothing, and any other press opens none;
- its verdicts go out on their own signal and reach only that Remote's
  entity, through the platform's own ``_apply_power_verdict``;
- ``trigger-remote/set-power`` takes the four keys with the Device
  door's checks, for a Remote whose type has power only.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

from custom_components.hair import models, remote_state
from custom_components.hair import power_monitor as pm
from custom_components.hair.const import DOMAIN, DeviceType
from custom_components.hair.models import EntityConfig, IRDevice, TriggerRemote
from custom_components.hair.power_monitor import (
    SIGNAL_POWER_VERDICT,
    PowerMonitor,
    expected_press_state,
)
from custom_components.hair.remote_state import (
    REMOTE_POWER_TYPES,
    SIGNAL_REMOTE_POWER_RESEED,
    SIGNAL_REMOTE_POWER_VERDICT,
    SIGNAL_REMOTE_PRESSED,
    RemotePressed,
    remote_power_eligible,
)
from custom_components.hair.send_signal import SIGNAL_DEVICE_SENT
from custom_components.hair.tests.test_power_settle_window import (
    SENT_WALL,
    _FakeLoop,
)
from custom_components.hair.tests.test_websocket_api import _make_connection
from custom_components.hair.websocket_api import ws_set_trigger_remote_power

PLUG = "sensor.tv_plug_power"
PRESENCE = "input_boolean.bench_tv_presence"


def _remote(device_type="switch", **overrides) -> TriggerRemote:
    values = dict(
        id="rem-1",
        name="Bench Remote",
        device_type=device_type,
        entity_config=EntityConfig(
            command_mapping={
                "turn_on": "t-on",
                "turn_off": "t-off",
                "power_toggle": "t-tog",
                "volume_up": "t-vol",
            },
        ),
        power_sensor_entity_id=PLUG,
        power_off_below_w=2,
        power_on_above_w=10,
    )
    values.update(overrides)
    return TriggerRemote(**values)


def _watts(value, entity_id=PLUG, reported=None) -> State:
    state = State(entity_id, str(value), {ATTR_UNIT_OF_MEASUREMENT: "W"})
    if reported is not None:
        object.__setattr__(state, "last_reported", reported)
    return state


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class TestStorage:
    def test_the_four_fields_round_trip(self):
        remote = _remote(power_settle_s=45.0)
        data = remote.to_dict()
        assert data["power_sensor_entity_id"] == PLUG
        assert data["power_off_below_w"] == 2
        assert data["power_on_above_w"] == 10
        assert data["power_settle_s"] == 45.0
        back = TriggerRemote.from_dict(data)
        assert (
            back.power_sensor_entity_id,
            back.power_off_below_w,
            back.power_on_above_w,
            back.power_settle_s,
        ) == (PLUG, 2, 10, 45.0)

    def test_a_remote_without_a_source_stores_what_it_stored_before(self):
        data = _remote(power_sensor_entity_id=None).to_dict()
        for key in (
            "power_sensor_entity_id",
            "power_off_below_w",
            "power_on_above_w",
            "power_settle_s",
        ):
            assert key not in data

    def test_an_older_build_keeps_them(self):
        """A build that does not know the fields carries them in _extra
        and writes them back untouched."""
        data = _remote(power_settle_s=30.0).to_dict()
        older = models._KNOWN_REMOTE - {
            "power_sensor_entity_id",
            "power_off_below_w",
            "power_on_above_w",
            "power_settle_s",
        }
        with patch.object(models, "_KNOWN_REMOTE", older):
            parsed = TriggerRemote.from_dict(data)
            assert parsed._extra["power_sensor_entity_id"] == PLUG
            written = parsed.to_dict()
        assert written["power_sensor_entity_id"] == PLUG
        assert written["power_settle_s"] == 30.0

    def test_a_damaged_settle_reads_as_the_default(self):
        data = _remote().to_dict()
        data["power_settle_s"] = "soon"
        assert TriggerRemote.from_dict(data).power_settle_s is None

    def test_a_duplicate_keeps_the_source(self):
        copy = _remote(power_settle_s=12.0).clone("Copy")
        assert copy.power_sensor_entity_id == PLUG
        assert copy.power_settle_s == 12.0

    def test_the_settle_window_reads_a_remote_as_a_device(self):
        assert models.power_settle_seconds(_remote()) == models.DEFAULT_POWER_SETTLE_S
        assert models.power_settle_seconds(_remote(power_settle_s=0.0)) == 0


# ---------------------------------------------------------------------------
# Which Remotes
# ---------------------------------------------------------------------------


class TestWhichRemotes:
    @pytest.mark.parametrize("device_type", REMOTE_POWER_TYPES)
    def test_a_type_with_power(self, device_type):
        assert remote_power_eligible(_remote(device_type))

    @pytest.mark.parametrize("device_type", [None, DeviceType.SCREEN, DeviceType.AC])
    def test_no_type_a_screen_or_an_ac_does_not(self, device_type):
        assert not remote_power_eligible(_remote(device_type))

    def test_a_matrix_remote_does_not_whatever_its_type_says(self):
        assert not remote_power_eligible(_remote("switch", climate_matrix=True))

    def test_the_types_are_the_devices_less_ac(self):
        assert set(REMOTE_POWER_TYPES) == {
            DeviceType.MEDIA_PLAYER,
            DeviceType.FAN,
            DeviceType.LIGHT,
            DeviceType.SWITCH,
        }


# ---------------------------------------------------------------------------
# The monitor
# ---------------------------------------------------------------------------


class _Rig:
    """A PowerMonitor over Devices and Remotes, every HA touch captured."""

    def __init__(self, *remotes, devices=()):
        self.loop = _FakeLoop()
        self.hass = MagicMock()
        self.hass.loop = self.loop
        self.readings: dict[str, State | None] = {}
        self.hass.states.get.side_effect = self.readings.get
        self.remotes = {r.id: r for r in remotes}
        self.devices = {d.id: d for d in devices}
        self.store = MagicMock()
        self.store.get_all_devices.side_effect = lambda: list(self.devices.values())
        self.store.get_device.side_effect = self.devices.get
        self.store.get_all_trigger_remotes.side_effect = lambda: list(self.remotes.values())
        self.store.get_trigger_remote.side_effect = self.remotes.get
        self.callbacks: dict[str, object] = {}
        self.tracked: list[str] = []
        self.unsubs: dict[str, MagicMock] = {}
        self.handlers: dict[str, object] = {}
        self.sent: list[tuple] = []

        def _track(hass, entity_ids, fn):
            unsub = MagicMock()
            for entity_id in entity_ids:
                self.callbacks[entity_id] = fn
                self.tracked.append(entity_id)
                self.unsubs[entity_id] = unsub
            return unsub

        def _connect(hass, signal, fn):
            self.handlers[signal] = fn
            return MagicMock()

        def _send(hass, signal, *args):
            self.sent.append((signal, *args))

        self._patches = [
            patch.object(pm, "async_track_state_change_event", side_effect=_track),
            patch.object(pm, "async_dispatcher_connect", side_effect=_connect),
            patch.object(pm, "async_dispatcher_send", side_effect=_send),
            patch.object(pm, "_monotonic", side_effect=self.loop.time),
            patch.object(pm, "_utcnow", return_value=SENT_WALL),
        ]
        for p in self._patches:
            p.start()
        self.monitor = PowerMonitor(self.hass, self.store)

    def close(self):
        for p in self._patches:
            p.stop()

    def report(self, value, entity_id=PLUG, after_press=True):
        reported = SENT_WALL + timedelta(seconds=1 if after_press else -1)
        state = _watts(value, entity_id, reported)
        self.readings[entity_id] = state
        event = MagicMock()
        event.data = {"new_state": state}
        self.callbacks[entity_id](event)

    def press(self, trigger_id, remote_id="rem-1"):
        self.handlers[SIGNAL_REMOTE_PRESSED](RemotePressed(remote_id, trigger_id))

    def take(self):
        out, self.sent = self.sent, []
        return out


@pytest.fixture
def rig_for():
    rigs = []

    def make(*remotes, devices=()):
        rig = _Rig(*remotes, devices=devices)
        rigs.append(rig)
        return rig

    yield make
    for rig in rigs:
        rig.close()


class TestTheSeed:
    def test_a_remote_is_watched_and_seeded_on_its_own_signal(self, rig_for):
        rig = rig_for(_remote())
        rig.readings[PLUG] = _watts(40)
        rig.monitor.start()
        assert rig.tracked == [PLUG]
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "on")]

    def test_the_monitor_listens_for_presses_and_reseeds(self, rig_for):
        rig = rig_for()
        rig.monitor.start()
        assert {SIGNAL_DEVICE_SENT, SIGNAL_REMOTE_PRESSED, SIGNAL_REMOTE_POWER_RESEED} <= set(
            rig.handlers
        )

    @pytest.mark.parametrize("device_type", [None, DeviceType.SCREEN])
    def test_a_remote_whose_type_has_no_power_is_not_watched(self, rig_for, device_type):
        rig = rig_for(_remote(device_type))
        rig.readings[PLUG] = _watts(40)
        rig.monitor.start()
        assert rig.tracked == []
        assert rig.take() == []

    def test_a_device_and_a_remote_on_one_plug_each_get_their_own(self, rig_for):
        device = IRDevice(
            id="dev-1", name="TV", device_type=DeviceType.SWITCH,
            power_sensor_entity_id=PLUG, power_off_below_w=2, power_on_above_w=10,
        )
        rig = rig_for(_remote(), devices=[device])
        rig.readings[PLUG] = _watts(0)
        rig.monitor.start()
        assert sorted(rig.take()) == sorted([
            (SIGNAL_POWER_VERDICT, "dev-1", "off"),
            (SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "off"),
        ])

    def test_an_on_off_source_is_read_by_its_state(self, rig_for):
        rig = rig_for(_remote(
            power_sensor_entity_id=PRESENCE,
            power_off_below_w=None, power_on_above_w=None,
        ))
        rig.readings[PRESENCE] = State(PRESENCE, "on")
        rig.monitor.start()
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "on")]

    def test_the_reseed_evaluates_the_current_reading(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.start()
        rig.take()
        rig.readings[PLUG] = _watts(0)
        rig.handlers[SIGNAL_REMOTE_POWER_RESEED]("rem-1")
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "off")]
        rig.handlers[SIGNAL_REMOTE_POWER_RESEED]("rem-unknown")
        assert rig.take() == []


class TestTheWindow:
    def test_a_power_press_holds_a_stale_reading_and_an_agreeing_one_clears(
        self, rig_for
    ):
        rig = rig_for(_remote())
        rig.readings[PLUG] = _watts(0)
        rig.monitor.start()
        rig.take()
        rig.press("t-on")
        assert "remote:rem-1" in rig.monitor._windows
        rig.report(0)  # the plug has not caught up
        assert rig.take() == []
        rig.report(40)  # it agrees with the press
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "on")]
        assert rig.monitor._windows == {}

    def test_off_says_off(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.start()
        rig.press("t-off")
        rig.report(40)
        assert rig.take() == []
        rig.report(0)
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "off")]

    def test_a_toggle_promises_nothing_and_the_end_hands_back(self, rig_for):
        # A media player Remote tracks a Power toggle; a switch tracks
        # on and off only.
        rig = rig_for(_remote(DeviceType.MEDIA_PLAYER))
        rig.monitor.start()
        rig.press("t-tog")
        rig.report(40)
        rig.report(0)
        assert rig.take() == []
        rig.loop.advance(models.DEFAULT_POWER_SETTLE_S + 1)
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "off")]
        assert rig.monitor._windows == {}

    def test_any_other_press_opens_no_window(self, rig_for):
        rig = rig_for(_remote(DeviceType.MEDIA_PLAYER))
        rig.monitor.start()
        rig.press("t-vol")
        rig.press("t-unmapped")
        assert rig.monitor._windows == {}
        rig.report(0)
        assert rig.take() == [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", "off")]

    def test_a_settle_of_zero_is_no_window(self, rig_for):
        rig = rig_for(_remote(power_settle_s=0.0))
        rig.monitor.start()
        rig.press("t-on")
        assert rig.monitor._windows == {}

    def test_another_remotes_press_opens_nothing_here(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.start()
        rig.press("t-on", remote_id="rem-2")
        assert rig.monitor._windows == {}

    def test_a_devices_send_never_opens_a_remotes_window(self, rig_for):
        from custom_components.hair.send_signal import DeviceSent

        rig = rig_for(_remote())
        rig.monitor.start()
        rig.handlers[SIGNAL_DEVICE_SENT](DeviceSent(device_id="rem-1", power="on"))
        assert rig.monitor._windows == {}

    @pytest.mark.parametrize(
        ("keys", "expected"),
        [
            ({"turn_on"}, "on"),
            ({"turn_off"}, "off"),
            ({"power_toggle"}, None),
            ({"turn_on", "power_toggle"}, None),
            ({"turn_on", "turn_off"}, None),
        ],
    )
    def test_what_a_press_says(self, keys, expected):
        assert expected_press_state(frozenset(keys)) == expected

    def test_a_key_the_remotes_type_cannot_track_opens_nothing(self, rig_for):
        """A switch Remote tracks on and off only, so its button mapped
        to a Power toggle is no power press."""
        rig = rig_for(_remote(DeviceType.SWITCH))
        rig.monitor.start()
        rig.press("t-tog")
        assert rig.monitor._windows == {}


class TestKeepingInStep:
    def test_a_retype_to_a_screen_stops_watching(self, rig_for):
        remote = _remote()
        rig = rig_for(remote)
        rig.monitor.start()
        remote.device_type = DeviceType.SCREEN
        rig.monitor.sync_remotes()
        rig.unsubs[PLUG].assert_called_once()
        assert "remote:rem-1" not in rig.monitor._unsub

    def test_a_reading_for_a_remote_retyped_before_the_sync_is_held(self, rig_for):
        """Between a retype and the sync that follows it, a report finds
        a Remote whose type cannot show power and dispatches nothing."""
        remote = _remote()
        rig = rig_for(remote)
        rig.monitor.start()
        rig.take()
        remote.device_type = DeviceType.SCREEN
        rig.report(40)
        assert rig.take() == []

    def test_a_type_set_later_starts_watching(self, rig_for):
        remote = _remote(None)
        rig = rig_for(remote)
        rig.monitor.start()
        assert rig.tracked == []
        remote.device_type = DeviceType.FAN
        rig.monitor.sync_remotes()
        assert rig.tracked == [PLUG]

    def test_a_deleted_remote_is_dropped(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.start()
        rig.press("t-on")
        del rig.remotes["rem-1"]
        rig.monitor.sync_remotes()
        assert rig.monitor._windows == {}
        assert rig.monitor._unsub == {}

    def test_an_unchanged_remote_is_left_alone(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.start()
        rig.press("t-on")
        rig.monitor.sync_remotes()
        assert rig.tracked == [PLUG]
        assert "remote:rem-1" in rig.monitor._windows

    def test_nothing_before_start(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.sync_remotes()
        assert rig.tracked == []

    def test_rebuild_keeps_an_open_window(self, rig_for):
        remote = _remote()
        rig = rig_for(remote)
        rig.monitor.start()
        rig.press("t-on")
        remote.power_on_above_w = 20
        rig.monitor.rebuild_remote(remote)
        assert "remote:rem-1" in rig.monitor._windows

    def test_stop_lets_go_of_everything(self, rig_for):
        rig = rig_for(_remote())
        rig.monitor.start()
        rig.press("t-on")
        rig.monitor.stop()
        assert rig.monitor._windows == {}
        assert rig.monitor._unsub == {}
        assert rig.monitor._remote_sources == {}


# ---------------------------------------------------------------------------
# The door
# ---------------------------------------------------------------------------


def _wire(fake_hass, remote):
    store = MagicMock()
    store.get_trigger_remote.side_effect = lambda rid: remote if rid == remote.id else None
    store.async_save = AsyncMock()
    monitor = MagicMock()
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "store": store,
        "power_monitor": monitor,
    }}
    return store, monitor


async def _set(fake_hass, remote, **fields):
    store, monitor = _wire(fake_hass, remote)
    conn = _make_connection()
    with patch(
        "custom_components.hair.websocket_api.er.async_get",
        return_value=MagicMock(async_get=MagicMock(return_value=None)),
    ), patch(
        "custom_components.hair.remote_state.remote_state_entity_id",
        return_value=None,
    ):
        await ws_set_trigger_remote_power(fake_hass, conn, {
            "id": 7, "type": "hair/trigger-remote/set-power",
            "remote_id": remote.id, **fields,
        })
    return conn, store, monitor


class TestTheDoor:
    @pytest.mark.asyncio
    async def test_a_source_is_written_saved_and_watched(self, fake_hass):
        remote = _remote(power_sensor_entity_id=None, power_off_below_w=None,
                         power_on_above_w=None)
        conn, store, monitor = await _set(
            fake_hass, remote,
            power_sensor_entity_id=PLUG, power_off_below_w=3, power_on_above_w=12,
            power_settle_s=30,
        )
        conn.send_result.assert_called_once()
        result = conn.send_result.call_args[0][1]
        assert result["power_eligible"] is True
        assert result["power_sensor_entity_id"] == PLUG
        assert (remote.power_off_below_w, remote.power_on_above_w) == (3, 12)
        assert remote.power_settle_s == 30
        store.update_trigger_remote.assert_called_once_with(remote)
        store.async_save.assert_awaited_once()
        monitor.rebuild_remote.assert_called_once_with(remote)

    @pytest.mark.asyncio
    async def test_an_on_off_source_clears_the_thresholds(self, fake_hass):
        remote = _remote()
        conn, _store, _monitor = await _set(
            fake_hass, remote, power_sensor_entity_id=PRESENCE, power_settle_s=300,
        )
        conn.send_result.assert_called_once()
        assert remote.power_sensor_entity_id == PRESENCE
        assert remote.power_off_below_w is None and remote.power_on_above_w is None
        assert remote.power_settle_s == 300

    @pytest.mark.asyncio
    async def test_clearing_the_source_clears_all_four(self, fake_hass):
        remote = _remote(power_settle_s=40.0)
        conn, _store, _monitor = await _set(
            fake_hass, remote, power_sensor_entity_id=None,
        )
        conn.send_result.assert_called_once()
        assert (
            remote.power_sensor_entity_id,
            remote.power_off_below_w,
            remote.power_on_above_w,
            remote.power_settle_s,
        ) == (None, None, None, None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("fields", "message"),
        [
            ({"power_sensor_entity_id": "light.tv"}, "sensor entity or an on/off"),
            ({"power_off_below_w": 20, "power_on_above_w": 5}, "at or above"),
            ({"power_settle_s": 500}, "from 0 to 120 seconds"),
        ],
    )
    async def test_the_device_doors_refusals(self, fake_hass, fields, message):
        remote = _remote()
        before = remote.to_dict()
        conn, store, monitor = await _set(fake_hass, remote, **fields)
        conn.send_error.assert_called_once()
        assert message in conn.send_error.call_args[0][2]
        assert remote.to_dict() == before
        store.async_save.assert_not_awaited()
        monitor.rebuild_remote.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_hair_entity_is_refused_and_names_the_remote(self, fake_hass):
        remote = _remote()
        store, _monitor = _wire(fake_hass, remote)
        conn = _make_connection()
        registry = MagicMock()
        registry.async_get.return_value = MagicMock(platform=DOMAIN)
        with patch(
            "custom_components.hair.websocket_api.er.async_get", return_value=registry
        ):
            await ws_set_trigger_remote_power(fake_hass, conn, {
                "id": 8, "type": "hair/trigger-remote/set-power",
                "remote_id": remote.id, "power_sensor_entity_id": "switch.hair_fan",
            })
        conn.send_error.assert_called_once()
        assert "a HAIR entity cannot be a Remote's state source" in conn.send_error.call_args[0][2]
        store.async_save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("device_type", [None, DeviceType.SCREEN])
    async def test_a_remote_that_cannot_show_power_is_refused(
        self, fake_hass, device_type
    ):
        remote = _remote(device_type, power_sensor_entity_id=None)
        conn, store, _monitor = await _set(
            fake_hass, remote, power_sensor_entity_id=PLUG,
        )
        conn.send_error.assert_called_once()
        assert "can have a state source" in conn.send_error.call_args[0][2]
        assert remote.power_sensor_entity_id is None
        store.async_save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unknown_remote(self, fake_hass):
        _wire(fake_hass, _remote())
        conn = _make_connection()
        await ws_set_trigger_remote_power(fake_hass, conn, {
            "id": 9, "type": "hair/trigger-remote/set-power", "remote_id": "nope",
        })
        assert conn.send_error.call_args[0][1] == "not_found"


# ---------------------------------------------------------------------------
# The entities
# ---------------------------------------------------------------------------


def _entity(platform: str, remote: TriggerRemote):
    from custom_components.hair.tests.test_remote_state import REMOTE_CLASSES

    entity = REMOTE_CLASSES[platform](remote)
    entity.hass = MagicMock()
    entity.entity_id = f"{platform}.bench_remote"
    entity.async_write_ha_state = MagicMock()
    entity.async_get_last_state = AsyncMock(return_value=None)
    return entity


async def _added(entity):
    handlers: dict[str, object] = {}
    reseeds: list[str] = []

    def _connect(hass, signal, fn):
        handlers[signal] = fn
        return MagicMock()

    def _send(hass, signal, *args):
        if signal == SIGNAL_REMOTE_POWER_RESEED:
            reseeds.append(args[0])

    with (
        patch.object(remote_state, "async_dispatcher_connect", side_effect=_connect),
        patch.object(remote_state, "async_dispatcher_send", side_effect=_send),
    ):
        await entity.async_added_to_hass()
    return handlers, reseeds


ON_STATE = {
    "switch": lambda e: e.is_on,
    "light": lambda e: e.is_on,
    "fan": lambda e: e.is_on,
    "media_player": lambda e: e.state == "on",
}


class TestTheEntities:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("platform", sorted(ON_STATE))
    async def test_a_verdict_moves_the_remotes_entity(self, platform):
        entity = _entity(platform, _remote(platform))
        handlers, reseeds = await _added(entity)
        assert reseeds == ["rem-1"]
        verdict = handlers[SIGNAL_REMOTE_POWER_VERDICT]
        verdict("rem-1", "on")
        assert ON_STATE[platform](entity)
        verdict("rem-1", "off")
        assert not ON_STATE[platform](entity)
        verdict("rem-other", "on")
        assert not ON_STATE[platform](entity)

    @pytest.mark.asyncio
    async def test_a_remote_never_listens_to_a_devices_verdict(self):
        entity = _entity("switch", _remote())
        handlers, _reseeds = await _added(entity)
        assert SIGNAL_POWER_VERDICT not in handlers

    @pytest.mark.asyncio
    async def test_a_screen_remote_does_not_listen_at_all(self):
        entity = _entity("cover", _remote(DeviceType.SCREEN))
        handlers, reseeds = await _added(entity)
        assert SIGNAL_REMOTE_POWER_VERDICT not in handlers
        assert reseeds == []

    @pytest.mark.parametrize("platform", sorted(ON_STATE))
    def test_the_device_handler_checks_the_id_then_applies(self, platform):
        """A Device's entity keeps its id check, then the shared effect."""
        import importlib
        import inspect

        module = importlib.import_module(f"custom_components.hair.{platform}")
        source = inspect.getsource(module)
        handler = source.split("def _handle_power_verdict(", 1)[1].split("@callback", 1)[0]
        assert "if device_id != self._device.id:" in handler
        assert "self._apply_power_verdict(verdict)" in handler
        assert "def _apply_power_verdict(self, verdict: PowerVerdict)" in source
