"""What the send path does with a row that carries a spacing.

Two arms, chosen by the field alone. An absent value runs the code
that has always run (test_device_manager.py pins that, and those
expectations are untouched); a present value builds one plan per
emitter and transmits it (send spacing, GH #151).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.const import (
    DOMAIN,
    SEND_REPEAT_GAP,
    SINGLE_LIST_MAX_ENTRIES,
)
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.storage import HAIRStore

# Exactly 10ms of block, so every gap below reads at a glance.
BLOCK_10MS = [4000, -2000, 4000]
# 1200 entries: four of these cannot share one call under the
# 2000-entry cap, so a burst of them has to chunk.
LONG_BLOCK = [400, -400] * 600
PRONTO_ANY = "0000 006D 0002 0000 0096 004B 0096 0258"


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
                async_get_or_create=MagicMock(
                    return_value=MagicMock(id="ha-dev-1")
                ),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


def _device(manager, *, spacing, send_count=4, emitters=("infrared.a",),
            block=None):
    command = IRCommand(
        id="c1", name="Power", raw_timings=list(block or BLOCK_10MS),
        send_count=send_count, send_spacing_ms=spacing,
    )
    device = IRDevice(
        name="Amplificateur Pioneer",
        emitter_entity_ids=list(emitters),
        commands=[command],
    )
    manager._store.add_device(device)
    return device


def _platforms(mapping):
    """Pretend each emitter id belongs to the named integration."""
    return patch(
        "custom_components.hair.send_plan.emitter_platform",
        side_effect=lambda hass, entity_id: mapping.get(entity_id),
    )


def _sent_timings(ir_send):
    """The timing list handed to each transmit call, in order."""
    return [
        call.args[2].get_raw_timings() for call in ir_send.await_args_list
    ]


class TestTheExactArm:
    @pytest.mark.asyncio
    async def test_one_emitter_gets_one_call(self, manager):
        device = _device(manager, spacing=135)
        with _platforms({"infrared.a": "esphome"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            await manager.async_send_command(device.id, "c1")
        assert ir_send.await_count == 1

    @pytest.mark.asyncio
    async def test_the_one_list_carries_every_repeat(self, manager):
        device = _device(manager, spacing=135, send_count=4)
        with _platforms({"infrared.a": "broadlink"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            await manager.async_send_command(device.id, "c1")
        timings = _sent_timings(ir_send)[0]
        # Three seams of 125ms (135 asked, 10 of block), then the
        # bounded terminator the wire copy always ends on.
        assert timings.count(-125_000) == 3
        assert timings[-1] == -50_000

    @pytest.mark.asyncio
    async def test_each_emitter_gets_its_own_bundle(self, manager):
        device = _device(
            manager, spacing=135, emitters=("infrared.a", "infrared.b")
        )
        with _platforms(
            {"infrared.a": "esphome", "infrared.b": "broadlink"}
        ), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            await manager.async_send_command(device.id, "c1")
        assert ir_send.await_count == 2
        assert [c.args[1] for c in ir_send.await_args_list] == [
            "infrared.a", "infrared.b"
        ]

    @pytest.mark.asyncio
    async def test_no_repeat_gap_is_slept_on_this_arm(self, manager):
        # The list carries its own quiet. A sleep here would be the old
        # pacing bug wearing the new path's clothes.
        device = _device(manager, spacing=135)
        with _platforms({"infrared.a": "esphome"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ), patch(
            "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
        ) as sleep:
            await manager.async_send_command(device.id, "c1")
        assert SEND_REPEAT_GAP not in [
            c.args[0] for c in sleep.await_args_list
        ]


class TestChunking:
    @pytest.mark.asyncio
    async def test_only_the_last_chunk_is_terminated(self, manager):
        # 479.6ms of block at 600ms spacing: a 120.4ms seam, which is
        # longer than the terminator and would be clamped down to it if
        # a chunk that ends on one were ever wrapped.
        device = _device(
            manager, spacing=600, send_count=4, block=LONG_BLOCK
        )
        with _platforms({"infrared.a": "esphome"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            await manager.async_send_command(device.id, "c1")
        lists = _sent_timings(ir_send)
        assert len(lists) > 1
        # Every chunk but the last ends on its own seam silence; only
        # the last one wears the bounded terminator.
        for timings in lists[:-1]:
            assert timings[-1] == -120_400
            assert len(timings) <= SINGLE_LIST_MAX_ENTRIES
        assert lists[-1][-1] == -50_000


class TestTheIncapableArm:
    @pytest.mark.asyncio
    async def test_it_is_todays_loop(self, manager):
        device = _device(manager, spacing=135, send_count=4)
        with _platforms({"infrared.a": "mqtt"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send, patch(
            "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
        ) as sleep:
            await manager.async_send_command(device.id, "c1")
        assert ir_send.await_count == 4
        gaps = [c.args[0] for c in sleep.await_args_list]
        assert gaps.count(SEND_REPEAT_GAP) == 3

    @pytest.mark.asyncio
    async def test_a_mixed_device_bundles_only_where_it_can(self, manager):
        device = _device(
            manager, spacing=135, send_count=4,
            emitters=("infrared.a", "infrared.b"),
        )
        with _platforms(
            {"infrared.a": "esphome", "infrared.b": "mqtt"}
        ), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send, patch(
            "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
        ):
            await manager.async_send_command(device.id, "c1")
        per_emitter = [c.args[1] for c in ir_send.await_args_list]
        assert per_emitter.count("infrared.a") == 1
        assert per_emitter.count("infrared.b") == 4


class TestFailureSemantics:
    @pytest.mark.asyncio
    async def test_a_failing_emitter_is_dropped_from_its_remaining_calls(
        self, manager
    ):
        device = _device(
            manager, spacing=135, send_count=4,
            emitters=("infrared.a", "infrared.b"),
        )

        async def flaky(hass, entity_id, ir_cmd):
            if entity_id == "infrared.b":
                raise RuntimeError("emitter offline")

        with _platforms(
            {"infrared.a": "esphome", "infrared.b": "mqtt"}
        ), patch.object(
            _infrared_mod, "async_send_command", AsyncMock(side_effect=flaky)
        ) as ir_send, patch(
            "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
        ):
            await manager.async_send_command(device.id, "c1")
        # b fails its first frame and is not asked for the other three.
        per_emitter = [c.args[1] for c in ir_send.await_args_list]
        assert per_emitter.count("infrared.b") == 1

    @pytest.mark.asyncio
    async def test_every_emitter_failing_raises(self, manager):
        device = _device(manager, spacing=135)
        with _platforms({"infrared.a": "esphome"}), patch.object(
            _infrared_mod, "async_send_command",
            AsyncMock(side_effect=RuntimeError("nope")),
        ), pytest.raises(RuntimeError):
            await manager.async_send_command(device.id, "c1")


class TestWhatTheMirrorIsTold:
    def _monitor(self, manager):
        monitor = MagicMock()
        monitor.record_send = MagicMock()
        manager._hass.data[DOMAIN] = {"entry-1": {"signal_monitor": monitor}}
        return monitor

    @pytest.mark.asyncio
    async def test_it_gets_the_inner_command_and_the_burst(self, manager):
        device = _device(manager, spacing=135, send_count=4)
        monitor = self._monitor(manager)
        with _platforms({"infrared.a": "esphome"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ):
            await manager.async_send_command(device.id, "c1")
        kwargs = monitor.record_send.call_args.kwargs
        # The audited command is the single frame, never the bundle:
        # the Mirror matches identity, and the bundle is delivery.
        recorded = monitor.record_send.call_args.args[0]
        assert len(recorded.get_raw_timings()) < 20
        assert kwargs["burst"] == (4, 125_000)
        # 4 blocks, 3 gaps, one terminator.
        assert kwargs["air_s"] == pytest.approx(0.465, abs=0.001)

    @pytest.mark.asyncio
    async def test_an_old_row_reports_no_burst(self, manager):
        device = _device(manager, spacing=None, send_count=4)
        monitor = self._monitor(manager)
        with patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ), patch(
            "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
        ):
            await manager.async_send_command(device.id, "c1")
        kwargs = monitor.record_send.call_args.kwargs
        assert kwargs["burst"] is None
        # 4 x (10ms block + 50ms terminator) + 3 x SEND_REPEAT_GAP.
        assert kwargs["air_s"] == pytest.approx(0.54, abs=0.001)


class TestTheOtherTwoCallers:
    @pytest.mark.asyncio
    async def test_a_test_send_stays_on_the_old_path(self, manager):
        # No stored row exists yet, so there is no spacing to honour.
        device = _device(manager, spacing=135)
        seen = {}

        async def _capture(self_, dev, ir_cmd, name, **kwargs):
            seen.update(kwargs)
            return {"infrared.a"}

        with patch.object(
            DeviceManager, "_async_broadcast", _capture
        ):
            await manager.async_test_send(device.id, PRONTO_ANY)
        assert seen["send_spacing_ms"] is None

    @pytest.mark.asyncio
    async def test_a_matrix_cell_stays_on_the_old_path(self, manager):
        device = _device(manager, spacing=135)
        seen = {}

        async def _capture(self_, dev, ir_cmd, name, **kwargs):
            seen.update(kwargs)
            return {"infrared.a"}

        with patch.object(DeviceManager, "_async_broadcast", _capture):
            await manager.async_send_matrix_cell(
                device.id, "cool/auto/23", PRONTO_ANY
            )
        assert seen["send_spacing_ms"] is None

    @pytest.mark.asyncio
    async def test_a_stored_row_passes_its_own_value(self, manager):
        device = _device(manager, spacing=135)
        seen = {}

        async def _capture(self_, dev, ir_cmd, name, **kwargs):
            seen.update(kwargs)
            return {"infrared.a"}

        with patch.object(DeviceManager, "_async_broadcast", _capture):
            await manager.async_send_command(device.id, "c1")
        assert seen["send_spacing_ms"] == 135


class TestTheCatalogTestPath:
    """signal_monitor.test_signal takes the same two arms."""

    def _monitor(self, fake_hass, signal):
        from unittest.mock import AsyncMock as _AsyncMock

        from custom_components.hair.models import UnknownDevice
        from custom_components.hair.signal_monitor import SignalMonitor
        from custom_components.hair.signal_store import SignalStore

        store = SignalStore(fake_hass)
        store._loaded = True
        store.schedule_save = MagicMock()
        store.async_save = _AsyncMock()
        hair = MagicMock()
        hair.get_all_devices = MagicMock(return_value=[])
        hair.get_device = MagicMock(return_value=None)
        hair.async_save = _AsyncMock()
        hair.match_command = MagicMock(return_value=None)
        store.add_device(UnknownDevice(
            id="ud0", fingerprint="d0", source="manual", signals=[signal],
        ))
        return SignalMonitor(fake_hass, store, hair)

    def _signal(self, **overrides):
        from custom_components.hair.models import UnknownSignal

        fields = {
            "id": "s1", "fingerprint": "s1", "frequency": 38000,
            "raw_timings": list(BLOCK_10MS), "send_count": 4,
        }
        fields.update(overrides)
        return UnknownSignal(**fields)

    @pytest.mark.asyncio
    async def test_an_old_signal_runs_todays_loop(self, fake_hass):
        monitor = self._monitor(fake_hass, self._signal())
        with _platforms({"infrared.e": "esphome"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send, patch(
            "custom_components.hair.signal_monitor.asyncio.sleep", AsyncMock()
        ) as sleep:
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"]
        assert ir_send.await_count == 4
        assert [c.args[0] for c in sleep.await_args_list].count(
            SEND_REPEAT_GAP
        ) == 3

    @pytest.mark.asyncio
    async def test_a_spaced_signal_goes_out_as_one_call(self, fake_hass):
        monitor = self._monitor(fake_hass, self._signal(send_spacing_ms=135))
        with _platforms({"infrared.e": "esphome"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"]
        assert ir_send.await_count == 1
        timings = ir_send.await_args_list[0].args[2].get_raw_timings()
        assert timings.count(-125_000) == 3

    @pytest.mark.asyncio
    async def test_an_incapable_emitter_still_gets_todays_loop(
        self, fake_hass
    ):
        monitor = self._monitor(fake_hass, self._signal(send_spacing_ms=135))
        with _platforms({"infrared.e": "mqtt"}), patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send, patch(
            "custom_components.hair.signal_monitor.asyncio.sleep", AsyncMock()
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"]
        assert ir_send.await_count == 4

    @pytest.mark.asyncio
    async def test_a_dead_emitter_still_returns_the_typed_code(
        self, fake_hass
    ):
        monitor = self._monitor(fake_hass, self._signal(send_spacing_ms=135))
        with _platforms({"infrared.e": "esphome"}), patch.object(
            _infrared_mod, "async_send_command",
            AsyncMock(side_effect=RuntimeError("offline")),
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"] is False
        assert result["code"] == "send_failed"
