"""Pinned remotes: Track only (GH #294).

A pin can now do one of three things with the presses its remote hears:
send every press, send every press but Power (GH #183, toggle-power
devices only), or track only: send nothing and let the device's state
follow every press, for a device that hears the remote itself.

What is pinned here:

- the third list on the remote: saved only when not empty, Track only
  wins over the follow list on load, pruned with its pin, dropped on
  unpin and on device delete;
- a flat pin that tracks only follows every command, power or not, and
  sends nothing; a matrix pin that tracks only follows a settings state
  and a power state, and a Daikin64 Power press as Off at any state
  its frame carries;
- the door writes both lists together, refuses leaving out Power on a
  device without one-button power, and refuses an unpinned device;
- a tracked press moves a fan's speed cycle once and a media player's
  volume one step (the same single signal a landed send gives);
- a pin never binds a remote's button to a grouped command, so Track
  only never has a group to follow.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hair.models import (
    GroupStep,
    IRCommand,
    IRDevice,
    TriggerRemote,
)
from custom_components.hair.send_signal import ORIGIN_MANAGER, DeviceSent

from .test_toggle_power_matrix import (
    POWER,
    _device,
    _flat_device,
    _hear,
    _lattice,
    _ListenerManager,
    _Manager,
    _pronto,
    _ws,
)

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class TestStorage:
    def test_the_list_round_trips_and_is_absent_when_empty(self):
        remote = TriggerRemote(id="r", pinned_device_ids=["d"],
                               track_only_device_ids=["d"])
        data = remote.to_dict()
        assert data["track_only_device_ids"] == ["d"]
        assert TriggerRemote.from_dict(data).track_only_device_ids == ["d"]
        assert "track_only_device_ids" not in TriggerRemote(id="r").to_dict()
        assert TriggerRemote.from_dict(
            {"id": "r", "pinned_device_ids": ["d"]}
        ).track_only_device_ids == []

    def test_track_only_wins_over_the_follow_list_on_load(self):
        loaded = TriggerRemote.from_dict({
            "id": "r", "pinned_device_ids": ["d", "e"],
            "follow_only_device_ids": ["d", "e"],
            "track_only_device_ids": ["d"],
        })
        assert loaded.track_only_device_ids == ["d"]
        assert loaded.follow_only_device_ids == ["e"]
        assert loaded.pin_mode("d") == "track"
        assert loaded.pin_mode("e") == "except_power"
        assert loaded.pin_mode("f") == "send"

    def test_setting_a_mode_writes_both_lists(self):
        remote = TriggerRemote(id="r", pinned_device_ids=["d"],
                               follow_only_device_ids=["d"])
        assert remote.set_pin_mode("d", "track") is True
        assert (remote.track_only_device_ids, remote.follow_only_device_ids) == (["d"], [])
        assert remote.set_pin_mode("d", "track") is False
        remote.set_pin_mode("d", "except_power")
        assert (remote.track_only_device_ids, remote.follow_only_device_ids) == ([], ["d"])
        remote.set_pin_mode("d", "send")
        assert (remote.track_only_device_ids, remote.follow_only_device_ids) == ([], [])

    def test_a_track_mark_without_its_pin_is_pruned_at_load(self, fake_hass):
        from custom_components.hair.storage import HAIRStore

        store = HAIRStore(fake_hass)
        store.add_device(_device())
        remote = TriggerRemote(id="r", pinned_device_ids=["dev-1"],
                               track_only_device_ids=["dev-1", "gone"])
        store.add_trigger_remote(remote)
        assert store._prune_dangling_pins(remote) is True
        assert remote.track_only_device_ids == ["dev-1"]

    @pytest.mark.asyncio
    async def test_unpinning_drops_it(self, fake_hass):
        from custom_components.hair.websocket_api import (
            ws_unpin_trigger_remote_device,
        )

        remote = TriggerRemote(id="tr1", name="Handset",
                               pinned_device_ids=["dev-1"],
                               track_only_device_ids=["dev-1"])
        _store, conn = _ws(fake_hass, remote, _device())
        await ws_unpin_trigger_remote_device(fake_hass, conn, {
            "id": 5, "type": "hair/trigger-remote/unpin",
            "remote_id": "tr1", "device_id": "dev-1",
        })
        assert remote.track_only_device_ids == []

    def test_deleting_the_device_drops_it(self):
        from custom_components.hair.device_manager import DeviceManager

        remote = TriggerRemote(id="r", pinned_device_ids=["dev-1", "other"],
                               track_only_device_ids=["dev-1", "other"],
                               follow_only_device_ids=[])
        store = MagicMock()
        store.get_all_trigger_remotes = MagicMock(return_value=[remote])
        manager = DeviceManager(MagicMock(), store, MagicMock(), "entry-1")
        manager._unpin_deleted_device("dev-1")
        assert remote.track_only_device_ids == ["other"]
        assert remote.pinned_device_ids == ["other"]


# ---------------------------------------------------------------------------
# A flat pin
# ---------------------------------------------------------------------------


def _fire(fake_hass, mapping, *, mode: str):
    from custom_components.hair.models import IRTrigger
    from custom_components.hair.pin_bindings import rederive_remote
    from custom_components.hair.storage import HAIRStore
    from custom_components.hair.trigger_manager import TriggerManager

    from .test_pin_retransmit import _TaskHass

    store = HAIRStore(fake_hass)
    store.add_device(_flat_device(mapping))
    remote = TriggerRemote(id="rem1", name="Handset", pinned_device_ids=["dev1"])
    remote.set_pin_mode("dev1", mode)
    store.add_trigger_remote(remote)
    store.add_trigger(IRTrigger(
        id="trg1", name="Power", trigger_remote_id="rem1",
        signal_fingerprint="fp-power", decoded_fingerprint="NEC:0x1:0x1",
        min_hits=1,
    ))
    rederive_remote(store, remote)
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    manager = _Manager()
    tm = TriggerManager(hass, store, manager)
    tm.on_signal_captured("fp-power", None, None, decoded_fingerprint="NEC:0x1:0x1")
    return hass, manager


class TestAFlatPin:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mapping", [
        {"power_toggle": "Power"},
        {"mute": "Power"},
        {},
    ])
    async def test_track_only_follows_every_press_and_sends_nothing(
        self, fake_hass, mapping,
    ):
        hass, manager = _fire(fake_hass, mapping, mode="track")
        await hass.drain()
        assert manager.sent == []
        assert manager.followed == [("dev1", "cmd1")]

    @pytest.mark.asyncio
    async def test_send_and_except_power_are_unchanged(self, fake_hass):
        hass, manager = _fire(fake_hass, {"mute": "Power"}, mode="except_power")
        await hass.drain()
        assert (manager.sent, manager.followed) == ([("dev1", "cmd1")], [])
        hass, manager = _fire(fake_hass, {"power_toggle": "Power"}, mode="send")
        await hass.drain()
        assert (manager.sent, manager.followed) == ([("dev1", "cmd1")], [])


# ---------------------------------------------------------------------------
# A matrix pin
# ---------------------------------------------------------------------------


def _matrix_pair(*, mode: str, toggles: bool = True):
    from custom_components.hair.matrix_listener import (
        MatrixListener,
        build_cell_index,
    )

    from .test_matrix_listener import _hass, _store_with

    remote_matrix = _lattice()
    device_matrix = _lattice()
    remote = TriggerRemote(
        id="r1", name="Daikin handset", climate_matrix=True,
        pinned_device_ids=["dev-1"],
    )
    remote.set_pin_mode("dev-1", mode)
    store = _store_with(remote)
    store.get_device = MagicMock(return_value=_device(toggles=toggles))
    hass = _hass(store)
    tasks: list = []
    hass.async_create_task = MagicMock(side_effect=tasks.append)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=(None, None))
    tm.dispatch_cell_retransmit = MagicMock(return_value=True)
    dm = _ListenerManager(device_matrix)
    listener = MatrixListener(hass, store, tm, dm)
    listener._matrix_cache["r1"] = remote_matrix
    listener._index_cache["r1"] = build_cell_index(remote_matrix)
    listener._index_cache["dev-1"] = build_cell_index(device_matrix)
    return listener, tm, dm, tasks, remote_matrix


class TestAMatrixPin:
    @pytest.mark.asyncio
    async def test_track_only_follows_a_settings_state(self):
        listener, tm, dm, tasks, remote_matrix = _matrix_pair(mode="track")
        await _hear(listener, tasks, _pronto(remote_matrix, "cool", "low", 26.0))

        args, kwargs = tm.dispatch_cell_retransmit.call_args
        assert args[:3] == ("r1", "dev-1", "cool/low/26")
        assert kwargs == {"follow": True}

        await listener.async_follow_pinned_cell("dev-1", "cool/low/26")
        assert dm.sends == []
        assert dm.follows[-1].matrix_cell is not None
        assert dm.follows[-1].power is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("toggles", [True, False])
    async def test_track_only_follows_a_power_state(self, toggles):
        listener, tm, dm, tasks, _ = _matrix_pair(mode="track", toggles=toggles)
        await _hear(listener, tasks, POWER)

        assert tm.dispatch_cell_retransmit.call_args.kwargs == {"follow": True}
        await listener.async_follow_pinned_cell("dev-1", "off")
        assert dm.sends == []
        assert [s.power for s in dm.follows] == ["off"]

    @pytest.mark.asyncio
    async def test_send_still_sends_a_settings_state(self):
        listener, tm, _dm, tasks, remote_matrix = _matrix_pair(mode="send")
        await _hear(listener, tasks, _pronto(remote_matrix, "cool", "low", 26.0))
        assert tm.dispatch_cell_retransmit.call_args.kwargs == {}


class TestADaikin64Pin:
    """A Daikin64 Power press keys as the power role at any state it
    carries (field-map schema v0.7), so a Track only pin follows it as
    Off, never as the state in the rest of its frame."""

    @staticmethod
    def _pair(listener_matrix, mode: str):
        from custom_components.hair.matrix_listener import (
            MatrixListener,
            build_cell_index,
        )

        from .test_matrix_listener import _hass, _store_with

        remote = TriggerRemote(
            id="r1", name="Daikin handset", climate_matrix=True,
            pinned_device_ids=["dev-1"],
        )
        remote.set_pin_mode("dev-1", mode)
        store = _store_with(remote)
        store.get_device = MagicMock(return_value=_device(toggles=True))
        hass = _hass(store)
        tasks: list = []
        hass.async_create_task = MagicMock(side_effect=tasks.append)
        tm = MagicMock()
        tm.resolve_receiver_area = MagicMock(return_value=(None, None))
        tm.dispatch_cell_retransmit = MagicMock(return_value=True)
        dm = _ListenerManager(listener_matrix)
        listener = MatrixListener(hass, store, tm, dm)
        listener._matrix_cache["r1"] = listener_matrix
        listener._index_cache["r1"] = build_cell_index(listener_matrix)
        listener._index_cache["dev-1"] = build_cell_index(listener_matrix)
        return listener, tm, dm, tasks

    @staticmethod
    async def _press(listener, tasks, data):
        from custom_components.hair.wig_identity import wig_signal_identity

        from .test_daikin64_map import _pronto as d64_pronto
        from .test_daikin64_map import _train

        identity = wig_signal_identity(d64_pronto(data))
        await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, None, capture=_train(data),
        )
        while tasks:
            batch, tasks[:] = list(tasks), []
            for coro in batch:
                await coro

    @pytest.mark.asyncio
    async def test_track_only_follows_a_power_press_as_off_at_any_state(self):
        from .test_daikin64_map import _pack, _state

        listener, tm, dm, tasks = self._pair(_pack(), "track")
        # cool / low / 25 is a cell of the pack; the press carries it.
        await self._press(
            listener, tasks, _state(0x2, 0x8, 25, power=True, clock=362))

        args, kwargs = tm.dispatch_cell_retransmit.call_args
        assert args[:3] == ("r1", "dev-1", "off")
        assert kwargs == {"follow": True}
        await listener.async_follow_pinned_cell("dev-1", "off")
        assert dm.sends == []
        assert [s.power for s in dm.follows] == ["off"]

    @pytest.mark.asyncio
    async def test_the_same_frame_without_the_bit_is_its_state(self):
        from .test_daikin64_map import _pack, _state

        listener, tm, _dm, tasks = self._pair(_pack(), "track")
        await self._press(
            listener, tasks, _state(0x2, 0x8, 25, power=False, clock=362))

        args, kwargs = tm.dispatch_cell_retransmit.call_args
        assert args[:3] == ("r1", "dev-1", "cool/low/25")
        assert kwargs == {"follow": True}


# ---------------------------------------------------------------------------
# The door
# ---------------------------------------------------------------------------


class TestTheDoor:
    @pytest.mark.asyncio
    async def test_each_mode_writes_both_lists(self, fake_hass):
        from custom_components.hair.websocket_api import ws_set_pin_mode

        remote = TriggerRemote(id="tr1", name="Handset", pinned_device_ids=["dev-1"])
        store, conn = _ws(fake_hass, remote, _device(toggles=True))
        msg = {"id": 3, "type": "hair/trigger-remote/pin-mode",
               "remote_id": "tr1", "device_id": "dev-1"}
        for mode, track, follow in (
            ("track", ["dev-1"], []),
            ("except_power", [], ["dev-1"]),
            ("send", [], []),
        ):
            await ws_set_pin_mode(fake_hass, conn, {**msg, "mode": mode})
            assert remote.track_only_device_ids == track
            assert remote.follow_only_device_ids == follow
            assert conn.send_result.call_args.args[1] == {
                "follow_only_device_ids": follow,
                "track_only_device_ids": track,
            }
        assert store.async_save.await_count == 3

    @pytest.mark.asyncio
    async def test_leaving_out_power_needs_one_button_power(self, fake_hass):
        from custom_components.hair.websocket_api import ws_set_pin_mode

        remote = TriggerRemote(id="tr1", name="Handset", pinned_device_ids=["dev1"])
        store, conn = _ws(fake_hass, remote, _flat_device({"turn_on": "Power"}))
        await ws_set_pin_mode(fake_hass, conn, {
            "id": 4, "type": "hair/trigger-remote/pin-mode",
            "remote_id": "tr1", "device_id": "dev1", "mode": "except_power",
        })
        assert conn.send_error.call_args.args[1] == "invalid_mode"
        assert remote.follow_only_device_ids == []
        store.async_save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_track_only_is_offered_on_any_device(self, fake_hass):
        from custom_components.hair.websocket_api import ws_set_pin_mode

        remote = TriggerRemote(id="tr1", name="Handset", pinned_device_ids=["dev1"])
        _store, conn = _ws(fake_hass, remote, _flat_device({"turn_on": "Power"}))
        await ws_set_pin_mode(fake_hass, conn, {
            "id": 5, "type": "hair/trigger-remote/pin-mode",
            "remote_id": "tr1", "device_id": "dev1", "mode": "track",
        })
        assert remote.track_only_device_ids == ["dev1"]

    def test_an_unknown_mode_is_refused_by_the_schema(self):
        import voluptuous as vol

        from custom_components.hair.const import PIN_MODES

        assert PIN_MODES == ("send", "except_power", "track")
        with pytest.raises(vol.Invalid):
            vol.In(PIN_MODES)("relay")

    def test_the_old_door_is_gone(self):
        from custom_components.hair import websocket_api

        assert not hasattr(websocket_api, "ws_set_pin_relay")


# ---------------------------------------------------------------------------
# What a tracked press does to an entity
# ---------------------------------------------------------------------------


def _heard(device_id: str, command_id: str, name: str) -> DeviceSent:
    return DeviceSent(
        device_id=device_id, command_id=command_id, command_name=name,
        origin=ORIGIN_MANAGER, heard=True,
    )


class TestATrackedPress:
    @pytest.mark.asyncio
    async def test_steps_a_speed_cycle_fan_once(self):
        from custom_components.hair.send_signal import SIGNAL_DEVICE_SENT

        from .test_fan_speed_cycle import DEVICE_ID, _cid, _Fan
        from .test_fan_speed_cycle import _device as fan_device

        fan = await _Fan(fan_device(steps=3)).add()
        fan.at(1)
        fan.handlers[SIGNAL_DEVICE_SENT](
            _heard(DEVICE_ID, _cid("Speed Cycle"), "Speed Cycle")
        )
        assert fan.entity._cycle_pos == 2
        assert fan.sent == []

    @pytest.mark.asyncio
    async def test_moves_a_media_players_volume_one_step(self):
        from custom_components.hair.send_signal import SIGNAL_DEVICE_SENT

        from .test_send_follow import DEVICE_ID, _cid, _media

        w = await _media({"volume_up": "Vol Up", "volume_down": "Vol Down"})
        w.handlers[SIGNAL_DEVICE_SENT](_heard(DEVICE_ID, _cid("Vol Up"), "Vol Up"))
        assert w.entity._volume_level == pytest.approx(0.55)
        w.manager.async_send_command.assert_not_awaited()


# ---------------------------------------------------------------------------
# Grouped commands
# ---------------------------------------------------------------------------


class TestGroupedCommands:
    def test_a_pin_never_binds_a_button_to_a_group(self):
        """A group has no code of its own, so a remote's button can never
        match it, and a Track only pin never has a group to follow."""
        from custom_components.hair.models import GROUP_PROTOCOL
        from custom_components.hair.pin_bindings import build_device_index

        device = IRDevice(
            id="dev1", name="TV",
            commands=[
                IRCommand(id="cmd1", name="Power", decoded_fingerprint="NEC:0x1:0x1"),
                IRCommand(id="grp1", name="Movie night", protocol=GROUP_PROTOCOL,
                          code=None, steps=[GroupStep("dev1", "cmd1", 500)]),
            ],
        )
        index = build_device_index(device)
        assert "grp1" not in index.decoded.values()
        assert all("grp1" not in str(v) for v in vars(index).values())
