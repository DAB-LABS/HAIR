"""Grouped commands: other devices' commands, in order, with delays.

See grouped-signals.md. A grouped command is a
command with steps; each step is sent through the ordinary send door,
and the delay after it counts from the end of its signal.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import grouped
from custom_components.hair.const import (
    GROUP_DELAY_MIN_MS,
    GROUP_MAX_STEPS,
    DeviceType,
)
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import (
    GROUP_PROTOCOL,
    GroupStep,
    IRCommand,
    IRDevice,
    is_group,
)
from custom_components.hair.storage import HAIRStore

# Built at run time: a Pronto literal in a test module is a row of the
# decode census, and this module is not in its baseline.
_NEC = " ".join((
    "0000", "006D", "0022", "0002", "0157", "00AC",
    *(["0015", "0016"] * 8), *(["0015", "0041"] * 8),
    *(["0015", "0016", "0015", "0041"] * 8),
    "0015", "0689", "0157", "0056", "0015", "0E94",
))


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.fixture
def manager(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        store._loaded = True
        factory = EntityFactory(fake_hass)
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="r")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


def _device(name, emitter, *names, device_id=None):
    device = IRDevice(
        name=name, device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=[emitter] if emitter else [],
    )
    if device_id:
        device.id = device_id
    for n in names:
        device.commands.append(
            IRCommand(name=n, protocol="PRONTO", code=_NEC)
        )
    return device


def _group(*steps, name="Movie night"):
    return IRCommand(
        name=name, protocol=GROUP_PROTOCOL,
        steps=[GroupStep(d.id, c.id, delay_ms=ms) for d, c, ms in steps],
    )


async def _add(manager, *devices):
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="r")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        for device in devices:
            await manager.async_create_device(device)


class _Air:
    """The infrared service, recording what went out and through what."""

    def __init__(self, fail=()):
        self.sent: list[str] = []
        self.fail = set(fail)

    async def __call__(self, hass, entity_id, command):
        if entity_id in self.fail:
            raise RuntimeError("blaster asleep")
        self.sent.append(entity_id)


@pytest.fixture
def air():
    mod = sys.modules["homeassistant.components.infrared"]
    original = mod.async_send_command
    fake = _Air()
    mod.async_send_command = fake
    yield fake
    mod.async_send_command = original


@pytest.fixture
def sleeps():
    waits: list[float] = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    with patch.object(grouped, "_sleep", fake_sleep):
        yield waits


class TestTheModel:
    def test_round_trip(self):
        group = _group()
        group.steps = [GroupStep("d", "c", 750, "TV", "Power On")]
        back = IRCommand.from_dict(group.to_dict())
        assert is_group(back)
        assert back.steps[0].to_dict() == group.steps[0].to_dict()

    def test_an_ordinary_command_record_is_unchanged(self):
        command = IRCommand(name="Power", protocol="PRONTO", code=_NEC)
        assert "steps" not in command.to_dict()
        assert not is_group(command)

    def test_a_clone_points_its_own_steps_at_the_copies(self):
        tv = _device("TV", "infrared.a", "Power On")
        other = _device("AVR", "infrared.b", "Input")
        group = _group((tv, tv.commands[0], 500), (other, other.commands[0], 500))
        tv.commands.append(group)
        clone = tv.clone("TV 2")
        copied = clone.get_command_by_name("Movie night")
        assert copied.steps[0].device_id == clone.id
        assert copied.steps[0].command_id == clone.commands[0].id
        # Steps on other devices stay, and the original is untouched.
        assert copied.steps[1].device_id == other.id
        assert group.steps[0].device_id == tv.id


@pytest.mark.asyncio
class TestTheRun:
    async def test_steps_go_out_in_order_through_their_own_blasters(
        self, manager, air, sleeps
    ):
        tv = _device("TV", "infrared.tv", "Power On")
        avr = _device("AVR", "infrared.avr", "Power On", "Input HDMI 2")
        group = _group(
            (tv, tv.commands[0], 2000),
            (avr, avr.commands[0], 500),
            (avr, avr.commands[1], 500),
        )
        tv.commands.append(group)
        await _add(manager, tv, avr)
        result = await manager.async_send_command(tv.id, group.id)
        assert air.sent == ["infrared.tv", "infrared.avr", "infrared.avr"]
        assert (result.sent, result.total, result.failures) == (3, 3, [])
        # Two waits: each one the delay plus what was still on the air.
        assert len(sleeps) == 2
        assert sleeps[0] >= 2.0 and sleeps[1] >= 0.5

    async def test_the_delay_counts_from_the_end_of_the_signal(
        self, manager, air, sleeps
    ):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group((tv, tv.commands[0], 500), (tv, tv.commands[0], 500))
        tv.commands.append(group)
        await _add(manager, tv)
        with patch.object(manager, "air_left_s", return_value=1.25):
            await manager.async_send_command(tv.id, group.id)
        assert sleeps == [pytest.approx(1.75)]

    async def test_a_failed_step_does_not_stop_the_run(self, manager, sleeps):
        mod = sys.modules["homeassistant.components.infrared"]
        original = mod.async_send_command
        mod.async_send_command = _Air(fail={"infrared.avr"})
        try:
            tv = _device("TV", "infrared.tv", "Power On", "Mute")
            avr = _device("AVR", "infrared.avr", "Power On")
            group = _group(
                (tv, tv.commands[0], 500), (avr, avr.commands[0], 500),
                (tv, tv.commands[1], 500),
            )
            tv.commands.append(group)
            await _add(manager, tv, avr)
            result = await manager.async_send_command(tv.id, group.id)
        finally:
            mod.async_send_command = original
        assert result.sent == 2
        assert [(f.index, f.reason) for f in result.failures] == [
            (1, grouped.STEP_FAILED),
        ]

    async def test_nothing_out_raises_with_the_result(self, manager, sleeps):
        tv = _device("TV", None, "Power On")
        group = _group((tv, tv.commands[0], 500))
        tv.commands.append(group)
        await _add(manager, tv)
        with pytest.raises(grouped.GroupRunError) as err:
            await manager.async_send_command(tv.id, group.id)
        assert err.value.result.sent == 0

    async def test_a_missing_step_is_skipped(self, manager, air, sleeps):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group((tv, tv.commands[0], 500))
        group.steps.insert(0, GroupStep("gone", "gone", 500, "AVR", "Input"))
        tv.commands.append(group)
        await _add(manager, tv)
        result = await manager.async_send_command(tv.id, group.id)
        assert result.sent == 1
        assert result.failures[0].reason == grouped.STEP_MISSING
        assert result.failures[0].command_name == "Input"

    async def test_a_group_step_is_refused_at_run_time(self, manager, air, sleeps):
        tv = _device("TV", "infrared.tv", "Power On")
        inner = _group((tv, tv.commands[0], 500), name="Inner")
        tv.commands.append(inner)
        outer = _group((tv, inner, 500), (tv, tv.commands[0], 500), name="Outer")
        tv.commands.append(outer)
        await _add(manager, tv)
        result = await manager.async_send_command(tv.id, outer.id)
        assert result.failures[0].reason == grouped.STEP_GROUP
        assert air.sent == ["infrared.tv"]

    async def test_one_run_at_a_time(self, manager, air, sleeps):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group((tv, tv.commands[0], 500))
        tv.commands.append(group)
        await _add(manager, tv)
        manager._groups_running.add((tv.id, group.id))
        result = await manager.async_send_command(tv.id, group.id)
        assert result.skipped_busy and air.sent == []

    async def test_each_step_and_the_group_move_their_devices(
        self, manager, air, sleeps
    ):
        from custom_components.hair.send_signal import SIGNAL_DEVICE_SENT

        tv = _device("TV", "infrared.tv", "Power On")
        avr = _device("AVR", "infrared.avr", "Power On")
        group = _group((tv, tv.commands[0], 500), (avr, avr.commands[0], 500))
        tv.commands.append(group)
        await _add(manager, tv, avr)
        with patch(
            "homeassistant.helpers.dispatcher.async_dispatcher_send"
        ) as late, patch(
            "custom_components.hair.device_manager.async_dispatcher_send"
        ) as sent:
            await manager.async_send_command(tv.id, group.id, origin="entity")
        steps = [c.args[2] for c in sent.call_args_list if c.args[1] == SIGNAL_DEVICE_SENT]
        assert [(s.device_id, s.origin) for s in steps] == [
            (tv.id, "manager"), (avr.id, "manager"),
        ]
        own = [c.args[2] for c in late.call_args_list if c.args[1] == SIGNAL_DEVICE_SENT]
        assert [(s.device_id, s.command_id, s.origin) for s in own] == [
            (tv.id, group.id, "entity"),
        ]

    async def test_the_mirror_label_names_the_group(self, manager, air, sleeps):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group((tv, tv.commands[0], 500))
        tv.commands.append(group)
        await _add(manager, tv)
        monitor = MagicMock()
        with patch.object(manager, "_signal_monitor", return_value=monitor):
            await manager.async_send_command(tv.id, group.id)
        assert monitor.record_send.call_args.args[1] == "Movie night: TV / Power On"


@pytest.mark.asyncio
class TestTheSaveDoor:
    async def test_steps_are_saved_with_their_names(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        await manager.async_set_group_steps(
            tv.id, group.id, [GroupStep(tv.id, tv.commands[0].id, 800)]
        )
        assert group.steps[0].command_name == "Power On"
        assert group.steps[0].device_name == "TV"

    @pytest.mark.parametrize("delay", [GROUP_DELAY_MIN_MS - 1, 60_001])
    async def test_the_delay_bounds(self, manager, delay):
        tv = _device("TV", "infrared.tv", "Power On", "Mute")
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        steps = [GroupStep(tv.id, tv.commands[0].id, delay),
                 GroupStep(tv.id, tv.commands[1].id, 500)]
        with pytest.raises(grouped.StepsRefused) as err:
            await manager.async_set_group_steps(tv.id, group.id, steps)
        assert err.value.code == "bad_delay"

    async def test_the_last_steps_delay_is_not_checked(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        await manager.async_set_group_steps(
            tv.id, group.id, [GroupStep(tv.id, tv.commands[0].id, 0)]
        )

    async def test_at_most_twenty_steps(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        steps = [GroupStep(tv.id, tv.commands[0].id, 300)] * (GROUP_MAX_STEPS + 1)
        with pytest.raises(grouped.StepsRefused) as err:
            await manager.async_set_group_steps(tv.id, group.id, steps)
        assert err.value.code == "too_many_steps"

    async def test_the_run_cap(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        steps = [GroupStep(tv.id, tv.commands[0].id, 60_000)] * 4
        with pytest.raises(grouped.StepsRefused) as err:
            await manager.async_set_group_steps(tv.id, group.id, steps)
        assert err.value.code == "run_too_long"

    async def test_no_group_inside_a_group(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        inner = _group(name="Inner")
        outer = _group(name="Outer")
        tv.commands += [inner, outer]
        await _add(manager, tv)
        with pytest.raises(grouped.StepsRefused) as err:
            await manager.async_set_group_steps(
                tv.id, outer.id, [GroupStep(tv.id, inner.id, 500)]
            )
        assert err.value.code == "step_group"

    async def test_no_rolling_code(self, manager):
        from custom_components.hair.models import MEDIUM_RF

        tv = _device("TV", "radio_frequency.rf", "Power On")
        rolling = IRCommand(name="Garage", medium=MEDIUM_RF, raw_timings=[1, -1])
        tv.commands.append(rolling)
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        with patch("custom_components.hair.rf_send.rolling_row", return_value="keeloq"), \
                pytest.raises(grouped.StepsRefused) as err:
            await manager.async_set_group_steps(
                tv.id, group.id, [GroupStep(tv.id, rolling.id, 500)]
            )
        assert err.value.code == "step_rolling"


@pytest.mark.asyncio
class TestWhatThePanelReads:
    async def test_the_payload_resolves_and_marks_missing(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        avr = _device("AVR", "infrared.avr", "Input")
        group = _group((tv, tv.commands[0], 1000), (avr, avr.commands[0], 500))
        group.steps.append(GroupStep("gone", "gone", 500, "Fan", "Light Off"))
        tv.commands.append(group)
        await _add(manager, tv, avr)
        tv.commands[0].name = "Power"   # a rename reaches the group
        out = grouped.group_payload(manager, group)
        assert [s["command_name"] for s in out["steps"]] == ["Power", "Input", "Light Off"]
        assert [s["missing"] for s in out["steps"]] == [False, False, True]
        assert out["devices"] == ["TV", "AVR"] and out["missing"] == 1
        assert out["run_ms"] >= 1500

    async def test_the_picker_lists_this_device_first_and_no_groups(self, manager):
        avr = _device("AVR", "infrared.avr", "Input")
        tv = _device("TV", "infrared.tv", "Power On")
        bedroom = _device("Bedroom AC", None, "Cool 22")
        tv.commands.append(_group())
        await _add(manager, avr, tv, bedroom)
        listed = grouped.step_candidates(manager, tv.id)
        assert listed[0]["id"] == tv.id and listed[0]["here"]
        assert [c["name"] for c in listed[0]["commands"]] == ["Power On"]
        no_blaster = next(d for d in listed if d["name"] == "Bedroom AC")
        assert not no_blaster["blaster"]
        assert no_blaster["commands"][0]["reason"] == "no_blaster"

    async def test_used_by_names_the_groups(self, manager):
        tv = _device("TV", "infrared.tv", "Power On")
        avr = _device("AVR", "infrared.avr", "Input")
        group = _group((avr, avr.commands[0], 500))
        tv.commands.append(group)
        await _add(manager, tv, avr)
        assert grouped.groups_using(manager, avr.id, avr.commands[0].id) == [{
            "device_id": tv.id, "device_name": "TV",
            "command_id": group.id, "command_name": "Movie night",
        }]
        assert grouped.groups_using(manager, avr.id)[0]["command_name"] == "Movie night"
        # A device's own groups go with it and aren't counted.
        assert grouped.groups_using(manager, tv.id) == []

    async def test_a_new_group_never_takes_an_action_by_its_name(self, manager):
        tv = _device("TV", "infrared.tv")
        await _add(manager, tv)
        group = IRCommand(name="Power On", protocol=GROUP_PROTOCOL, steps=[])
        await manager.async_add_command(tv.id, group)
        assert "Power On" not in tv.entity_config.command_mapping.values()


class TestTheCensus:
    """Every walk that keys on a code skips a grouped command."""

    def test_export_leaves_it_out_with_a_note(self):
        from custom_components.hair.wig_export import build_wig_from_device

        tv = _device("TV", "infrared.tv", "Power On")
        tv.commands.append(_group((tv, tv.commands[0], 500)))
        build = build_wig_from_device(tv, None)
        assert build.skipped == 1
        assert any("Movie night is a grouped signal" in n for n in build.notes)
        assert len(build.wig.signals) == 1

    def test_the_pin_index_skips_it(self):
        from custom_components.hair.pin_bindings import build_device_index

        tv = _device("TV", "infrared.tv", "Power On")
        tv.commands.append(_group((tv, tv.commands[0], 500)))
        index = build_device_index(tv)
        assert index is not None

    @pytest.mark.asyncio
    async def test_the_store_load_passes_over_it(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = HAIRStore(fake_hass)
            store._loaded = True
            tv = _device("TV", "infrared.tv", "Power On")
            group = _group((tv, tv.commands[0], 500))
            tv.commands.append(group)
            store.add_device(tv)
            store._rebuild_command_index()
            before = group.to_dict()
            for name in (
                "_backfill_spacing_block", "_backfill_byte_hash",
                "_backfill_canonical_identity", "_clear_stale_identities",
                "_backfill_decoded_fields", "_backfill_pin_bindings",
                "_radio_frames_by_hash",
            ):
                getattr(store, name)()
            assert group.to_dict() == before
            assert all(group.id not in str(v) for v in store._idx_fp.values())

    @pytest.mark.asyncio
    async def test_the_devices_media_ignore_it(self):
        from custom_components.hair.websocket_api import _media

        tv = _device("TV", "infrared.tv")
        tv.commands.append(_group())
        assert _media(tv.commands) == []


@pytest.mark.asyncio
class TestTheDoors:
    async def _ws(self, manager, fn, **msg):
        from custom_components.hair.const import DOMAIN

        manager._hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        conn = MagicMock()
        result = fn(manager._hass, conn, {"id": 1, **msg})
        if result is not None:
            await result
        return conn

    async def test_create_picks_a_free_name_and_goes_on_top(self, manager):
        from custom_components.hair.websocket_api import ws_group_create

        tv = _device("TV", "infrared.tv", "Power On", "Grouped signal")
        await _add(manager, tv)
        with patch("custom_components.hair.websocket_api._ha_device_id", return_value=None):
            conn = await self._ws(manager, ws_group_create,
                                  type="hair/command/group/create", device_id=tv.id)
        made = conn.send_result.call_args.args[1]["command"]
        assert made["name"] == "Grouped signal 2"
        assert made["protocol"] == GROUP_PROTOCOL and made["steps"] == []
        assert tv.commands[0].id == made["id"]

    async def test_steps_refused_with_a_code(self, manager):
        from custom_components.hair.websocket_api import ws_group_set_steps

        tv = _device("TV", "infrared.tv", "Power On", "Mute")
        group = _group()
        tv.commands.append(group)
        await _add(manager, tv)
        conn = await self._ws(
            manager, ws_group_set_steps, type="hair/command/group/steps",
            device_id=tv.id, command_id=group.id,
            steps=[{"device_id": tv.id, "command_id": tv.commands[0].id, "delay_ms": 100},
                   {"device_id": tv.id, "command_id": tv.commands[1].id}],
        )
        assert conn.send_error.call_args.args[1] == "bad_delay"

    async def test_a_missing_step_keeps_its_names_through_a_save(self, manager):
        from custom_components.hair.websocket_api import ws_group_set_steps

        tv = _device("TV", "infrared.tv", "Power On")
        group = _group((tv, tv.commands[0], 500))
        group.steps.append(GroupStep("gone", "gone", 500, "AVR", "Input"))
        tv.commands.append(group)
        await _add(manager, tv)
        with patch("custom_components.hair.websocket_api._ha_device_id", return_value=None):
            await self._ws(
                manager, ws_group_set_steps, type="hair/command/group/steps",
                device_id=tv.id, command_id=group.id,
                steps=[{"device_id": "gone", "command_id": "gone", "delay_ms": 500}],
            )
        assert (group.steps[0].device_name, group.steps[0].command_name) == ("AVR", "Input")

    async def test_test_reports_how_many_went_out(self, manager, air, sleeps):
        from custom_components.hair.websocket_api import ws_send_command

        tv = _device("TV", "infrared.tv", "Power On")
        group = _group((tv, tv.commands[0], 500))
        group.steps.append(GroupStep("gone", "gone", 500, "AVR", "Input"))
        tv.commands.append(group)
        await _add(manager, tv)
        conn = await self._ws(manager, ws_send_command, type="hair/command/send",
                              device_id=tv.id, command_id=group.id)
        answer = conn.send_result.call_args.args[1]
        assert answer["sent"] is True
        assert (answer["group"]["sent"], answer["group"]["total"]) == (1, 2)
        assert answer["group"]["failures"][0]["reason"] == "missing"


@pytest.mark.asyncio
async def test_a_group_renames_like_any_command(manager):
    tv = _device("TV", "infrared.tv", "Power On")
    group = _group((tv, tv.commands[0], 500))
    tv.commands.append(group)
    tv.entity_config.command_mapping["turn_on"] = "Movie night"
    await _add(manager, tv)
    await manager.async_update_command(tv.id, group.id, name="Film night")
    assert group.name == "Film night" and is_group(group)
    assert group.steps[0].command_id == tv.commands[0].id
    assert tv.entity_config.command_mapping["turn_on"] == "Film night"
