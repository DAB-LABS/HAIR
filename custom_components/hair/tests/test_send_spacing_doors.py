"""The save doors are where a spacing is judged (send spacing, GH #151).

Every door that can write a row's ``send_spacing_ms`` asks the same
three questions in the same order, so a value can never reach the store
by coming in through a quieter entrance. Each refusal has its own code,
because "that number is too big" and "this device cannot do that at all"
are different problems with different fixes.
"""
from __future__ import annotations

import importlib.util
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    DOMAIN,
    SEND_AIR_TIME_MAX_MS,
    SEND_SPACING_MAX_MS,
    SEND_SPACING_MIN_MS,
)
from custom_components.hair.models import IRCommand, IRDevice, UnknownSignal
from custom_components.hair.websocket_api import (
    ws_assign_new_device,
    ws_assign_signal,
    ws_clip_create_signal,
    ws_command_update,
    ws_send_spacing_info,
    ws_unknown_signal_edit_pronto,
)

# 10ms of block. A 34-pair NEC frame at 8 sends is the reporter's shape;
# these three words keep the arithmetic visible instead.
BLOCK = [4000, -2000, 4000]
PRONTO_10MS = "0000 006D 0002 0000 0098 004C 0098 0000"
# 400ms of block: ten sends of it cannot fit the air-time cap at any
# spacing at all.
LONG_BLOCK = [200_000, -100_000, 200_000]
# A real 34-pair NEC frame: the reporter's own shape (GH #151), and the
# only kind of code whose ditto count changes the block.
NEC_PRONTO = (
    "0000 006D 0022 0000 014A 00A6 0013 0016 0013 0016 0013 0016 "
    "0013 0016 0013 0016 0013 0016 0013 0016 0013 0016 0013 003F "
    "0013 003F 0013 003F 0013 003F 0013 003F 0013 003F 0013 003F "
    "0013 003F 0013 003F 0013 0016 0013 003F 0013 0016 0013 0016 "
    "0013 0016 0013 003F 0013 0016 0013 0016 0013 003F 0013 0016 "
    "0013 003F 0013 003F 0013 003F 0013 0016 0013 003F 0013 017C"
)


_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None

# The five tests below build a DECODED block, which only exists when the
# encoder does. Without the library `build_decoded_command` answers None,
# the block falls back to the raw Pronto frame, and the whole point of
# those tests (that a ditto count changes the block) cannot be observed.
# Same decorator the decoder suites use.
_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _wire(hass, *, emitters=("infrared.a",), signal=None, command=None):
    """hass.data shaped as the doors read it, with one device each side."""
    device = IRDevice(
        id="dev-1", name="Amplificateur Pioneer",
        emitter_entity_ids=list(emitters),
        commands=[command] if command is not None else [],
    )
    store = MagicMock()
    store.get_device = MagicMock(
        side_effect=lambda did: device if did == "dev-1" else None
    )
    store.async_save = AsyncMock()

    unknown = SimpleNamespace(
        get_signal_by_id=lambda sid: signal if sid == "sig-1" else None
    )
    signal_store = MagicMock()
    signal_store.get_device = MagicMock(
        side_effect=lambda did: unknown if did == "cat-1" else None
    )

    monitor = MagicMock()
    monitor.assign_signal = AsyncMock(
        return_value={"success": True, "command_id": "c1"}
    )
    monitor.assign_to_new_device = AsyncMock(
        return_value={
            "success": True, "command_id": "c1", "device_id": "dev-2",
            "device": IRDevice(id="dev-2", name="New"),
        }
    )
    monitor.create_manual_signal = AsyncMock(
        return_value={"success": True, "signal": {}}
    )
    monitor.edit_signal_pronto = AsyncMock(
        return_value={"success": True, "signal": {}, "triggers": {}}
    )
    manager = MagicMock()
    manager.async_apply_auto_map = AsyncMock()
    manager._store = store
    manager._store.async_save = AsyncMock()
    manager._entity_factory.async_create_entities = AsyncMock()
    manager.async_update_command = AsyncMock(
        return_value={
            "success": True, "command": {}, "triggers": {},
            "mappings_updated": 0,
        }
    )
    manager.async_get_matrix = AsyncMock(return_value=None)
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager,
        "store": store,
        "signal_store": signal_store,
        "signal_monitor": monitor,
        "trigger_manager": MagicMock(),
    }}
    return SimpleNamespace(
        device=device, store=store, monitor=monitor, manager=manager,
    )


def _platforms(mapping):
    return patch(
        "custom_components.hair.send_plan.emitter_platform",
        side_effect=lambda hass, entity_id: mapping.get(entity_id),
    )


def _signal(**overrides):
    fields = {
        "id": "sig-1", "fingerprint": "fp", "raw_timings": list(BLOCK),
        "frequency": 38000, "send_count": 4,
    }
    fields.update(overrides)
    return UnknownSignal(**fields)


class TestTheAssignDoor:
    @pytest.mark.asyncio
    async def test_a_value_inside_the_rules_is_stored(self, fake_hass):
        wired = _wire(fake_hass, signal=_signal())
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 4, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        kwargs = wired.monitor.assign_signal.call_args.kwargs
        assert kwargs["send_spacing_ms"] == 135
        assert kwargs["set_send_spacing"] is True

    @pytest.mark.asyncio
    async def test_an_omitted_field_leaves_the_signals_value_alone(
        self, fake_hass
    ):
        wired = _wire(fake_hass, signal=_signal())
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
            })
        assert wired.monitor.assign_signal.call_args.kwargs[
            "set_send_spacing"
        ] is False

    @pytest.mark.asyncio
    async def test_an_explicit_null_clears_it(self, fake_hass):
        wired = _wire(fake_hass, signal=_signal())
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 4, "send_spacing_ms": None,
            })
        kwargs = wired.monitor.assign_signal.call_args.kwargs
        assert kwargs["send_spacing_ms"] is None
        assert kwargs["set_send_spacing"] is True

    @pytest.mark.asyncio
    async def test_a_send_count_of_one_stores_nothing(self, fake_hass):
        """A burst of one has nothing to space, so the row must not be
        put on the bundled path for it."""
        wired = _wire(fake_hass, signal=_signal(send_count=1))
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 1, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        assert wired.monitor.assign_signal.call_args.kwargs[
            "send_spacing_ms"
        ] is None

    @pytest.mark.parametrize(
        "bad", [SEND_SPACING_MIN_MS - 1, SEND_SPACING_MAX_MS + 1, 0, -5]
    )
    @pytest.mark.asyncio
    async def test_out_of_range_is_refused_by_name(self, fake_hass, bad):
        _wire(fake_hass, signal=_signal())
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 4, "send_spacing_ms": bad,
            })
        assert conn.send_error.call_args[0][1] == "spacing_out_of_range"

    @pytest.mark.asyncio
    async def test_an_over_cap_combination_is_refused_by_name(
        self, fake_hass
    ):
        _wire(fake_hass, signal=_signal(raw_timings=LONG_BLOCK, send_count=10))
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 10, "send_spacing_ms": 20,
            })
        assert conn.send_error.call_args[0][1] == "spacing_air_time"
        # The numbers ride in the message, because a websocket error
        # frame carries a code and a string and nothing else.
        message = conn.send_error.call_args[0][2]
        assert str(SEND_AIR_TIME_MAX_MS) in message

    @pytest.mark.asyncio
    async def test_a_device_that_cannot_do_it_is_refused_by_name(
        self, fake_hass
    ):
        _wire(fake_hass, emitters=("infrared.a", "infrared.b"),
              signal=_signal())
        conn = _conn()
        with _platforms({"infrared.a": "mqtt", "infrared.b": None}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 4, "send_spacing_ms": 135,
            })
        assert conn.send_error.call_args[0][1] == "spacing_unsupported"
        assert "infrared.a" in conn.send_error.call_args[0][2]

    @pytest.mark.asyncio
    async def test_one_capable_emitter_on_a_mixed_device_is_enough(
        self, fake_hass
    ):
        wired = _wire(fake_hass, emitters=("infrared.a", "infrared.b"),
                      signal=_signal())
        conn = _conn()
        with _platforms({"infrared.a": "mqtt", "infrared.b": "broadlink"}):
            await ws_assign_signal(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign",
                "device_id": "cat-1", "signal_id": "sig-1",
                "hair_device_id": "dev-1", "command_name": "Power",
                "send_count": 4, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        assert wired.monitor.assign_signal.call_args.kwargs[
            "send_spacing_ms"
        ] == 135


class TestTheAssignToNewDeviceDoor:
    @pytest.mark.asyncio
    async def test_it_judges_the_emitters_the_payload_names(self, fake_hass):
        """The device does not exist yet, so the only emitters to ask
        about are the ones the dialog just picked."""
        _wire(fake_hass, signal=_signal())
        conn = _conn()
        with _platforms({"infrared.new": "mqtt"}):
            await ws_assign_new_device(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign-new-device",
                "device_id": "cat-1", "signal_id": "sig-1",
                "device_name": "Amp", "device_type": "media_player",
                "emitter_entity_ids": ["infrared.new"],
                "command_name": "Power",
                "send_count": 4, "send_spacing_ms": 135,
            })
        assert conn.send_error.call_args[0][1] == "spacing_unsupported"

    @pytest.mark.asyncio
    async def test_a_capable_pick_goes_through(self, fake_hass):
        wired = _wire(fake_hass, signal=_signal())
        conn = _conn()
        with _platforms({"infrared.new": "esphome"}):
            await ws_assign_new_device(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/assign-new-device",
                "device_id": "cat-1", "signal_id": "sig-1",
                "device_name": "Amp", "device_type": "media_player",
                "emitter_entity_ids": ["infrared.new"],
                "command_name": "Power",
                "send_count": 4, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        assert wired.monitor.assign_to_new_device.call_args.kwargs[
            "send_spacing_ms"
        ] == 135


class TestTheClipperDoor:
    """A clipped remote has no emitters of its own, so the question
    widens to whether the install has one that could ever honour the
    value. The door does not skip the check."""

    @pytest.mark.asyncio
    async def test_it_applies_the_capability_check(self, fake_hass):
        _wire(fake_hass)
        fake_hass.states.async_all = MagicMock(return_value=[
            SimpleNamespace(entity_id="infrared.a", attributes={}),
        ])
        conn = _conn()
        with _platforms({"infrared.a": "mqtt"}):
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 1, "type": "hair/clip/create-signal",
                "device_id": "cat-1", "pronto": PRONTO_10MS,
                "send_count": 4, "send_spacing_ms": 135,
            })
        assert conn.send_error.call_args[0][1] == "spacing_unsupported"

    @pytest.mark.asyncio
    async def test_an_install_with_a_capable_emitter_accepts(self, fake_hass):
        wired = _wire(fake_hass)
        fake_hass.states.async_all = MagicMock(return_value=[
            SimpleNamespace(entity_id="infrared.a", attributes={}),
        ])
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 1, "type": "hair/clip/create-signal",
                "device_id": "cat-1", "pronto": PRONTO_10MS,
                "send_count": 4, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        assert wired.monitor.create_manual_signal.call_args.kwargs[
            "send_spacing_ms"
        ] == 135

    @pytest.mark.asyncio
    async def test_a_lookup_that_finds_nothing_does_not_refuse(
        self, fake_hass
    ):
        """An empty list is "cannot tell", not "no". Refusing on it
        would make an install whose emitters have not come up yet
        unable to save a cadence at all."""
        wired = _wire(fake_hass)
        fake_hass.states.async_all = MagicMock(return_value=[])
        conn = _conn()
        with _platforms({}):
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 1, "type": "hair/clip/create-signal",
                "device_id": "cat-1", "pronto": PRONTO_10MS,
                "send_count": 4, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        assert wired.monitor.create_manual_signal.call_args.kwargs[
            "send_spacing_ms"
        ] == 135


class TestTheEditProntoDoor:
    @pytest.mark.asyncio
    async def test_it_measures_the_new_code_not_the_old_one(self, fake_hass):
        """The code is being replaced, so the cap has to be applied to
        what the row is about to become."""
        _wire(fake_hass, signal=_signal())
        fake_hass.states.async_all = MagicMock(return_value=[
            SimpleNamespace(entity_id="infrared.a", attributes={}),
        ])
        long_pronto = "0000 006D 0002 0000 1D4C 0EA6 1D4C 0000"
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_unknown_signal_edit_pronto(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/signal/edit-pronto",
                "device_id": "cat-1", "signal_id": "sig-1",
                "pronto": long_pronto,
                "send_count": 10, "send_spacing_ms": 20,
            })
        assert conn.send_error.call_args[0][1] == "spacing_air_time"


class TestTheCommandUpdateDoor:
    @pytest.mark.asyncio
    async def test_a_value_reaches_the_manager_with_its_flag(self, fake_hass):
        command = IRCommand(
            id="c1", name="Power", raw_timings=list(BLOCK), send_count=4,
        )
        wired = _wire(fake_hass, command=command)
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_command_update(fake_hass, conn, {
                "id": 1, "type": "hair/command/update",
                "device_id": "dev-1", "command_id": "c1",
                "send_count": 4, "send_spacing_ms": 135,
            })
        conn.send_error.assert_not_called()
        kwargs = wired.manager.async_update_command.call_args.kwargs
        assert kwargs["send_spacing_ms"] == 135
        assert kwargs["set_send_spacing"] is True

    @pytest.mark.asyncio
    async def test_an_untouched_edit_does_not_clear_the_value(
        self, fake_hass
    ):
        command = IRCommand(
            id="c1", name="Power", raw_timings=list(BLOCK),
            send_count=4, send_spacing_ms=135,
        )
        wired = _wire(fake_hass, command=command)
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_command_update(fake_hass, conn, {
                "id": 1, "type": "hair/command/update",
                "device_id": "dev-1", "command_id": "c1", "name": "Power On",
            })
        assert wired.manager.async_update_command.call_args.kwargs[
            "set_send_spacing"
        ] is False

    @pytest.mark.asyncio
    async def test_the_stored_count_is_used_when_the_payload_omits_it(
        self, fake_hass
    ):
        """A rename that carries a spacing but no count must be judged
        against the count the row actually has."""
        command = IRCommand(
            id="c1", name="Blast", raw_timings=list(LONG_BLOCK),
            send_count=10,
        )
        _wire(fake_hass, command=command)
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_command_update(fake_hass, conn, {
                "id": 1, "type": "hair/command/update",
                "device_id": "dev-1", "command_id": "c1",
                "send_spacing_ms": 20,
            })
        assert conn.send_error.call_args[0][1] == "spacing_air_time"


class TestTheReadHelper:
    def _ask(self, fake_hass, **payload):
        conn = _conn()
        msg = {"id": 1, "type": "hair/send_spacing_info"}
        msg.update(payload)
        ws_send_spacing_info(fake_hass, conn, msg)
        return conn.send_result.call_args[0][1]

    def test_it_answers_with_the_bounds_and_an_estimate(self, fake_hass):
        _wire(fake_hass)
        result = self._ask(
            fake_hass, pronto=PRONTO_10MS, send_count=4, repeat_count=0
        )
        assert result["min_ms"] == SEND_SPACING_MIN_MS
        assert result["max_ms"] == SEND_SPACING_MAX_MS
        assert result["block_ms"] == 10
        # Block + terminator + pipeline, rounded to 5.
        assert result["estimate_ms"] == 120

    def test_a_long_ac_block_does_not_show_the_short_answer(self, fake_hass):
        _wire(fake_hass)
        result = self._ask(
            fake_hass, raw_timings=list(LONG_BLOCK), send_count=2,
            repeat_count=0,
        )
        assert result["estimate_ms"] > 400

    def test_it_echoes_the_stored_value_and_costs_it(self, fake_hass):
        _wire(fake_hass)
        result = self._ask(
            fake_hass, pronto=PRONTO_10MS, send_count=4, repeat_count=0,
            send_spacing_ms=135,
        )
        assert result["send_spacing_ms"] == 135
        # 4 blocks and 3 gaps of 125ms.
        assert result["air_ms"] == 4 * 10 + 3 * 125
        assert result["air_limit_ms"] == SEND_AIR_TIME_MAX_MS

    def test_it_says_when_the_floor_bites(self, fake_hass):
        _wire(fake_hass)
        result = self._ask(
            fake_hass, raw_timings=list(LONG_BLOCK), send_count=2,
            repeat_count=0, send_spacing_ms=20,
        )
        assert result["floor_hit"] is True

    def test_a_device_id_brings_the_emitter_list(self, fake_hass):
        _wire(fake_hass, emitters=("infrared.a", "infrared.b"))
        with _platforms({"infrared.a": "esphome", "infrared.b": "mqtt"}):
            result = self._ask(
                fake_hass, pronto=PRONTO_10MS, send_count=4, repeat_count=0,
                device_id="dev-1",
            )
        assert [e["capability"] for e in result["emitters"]] == [
            "exact", "incapable"
        ]

    def test_no_device_id_means_no_emitter_list(self, fake_hass):
        _wire(fake_hass)
        result = self._ask(
            fake_hass, pronto=PRONTO_10MS, send_count=4, repeat_count=0
        )
        assert result["emitters"] == []


class TestADittoIsPartOfTheBlock:
    """A decodable row transmits its dittos INSIDE the block, so the
    block a door measures has to be the re-encoded one.

    The defect QA found on VM999 (2026-09-12): a Clipper row, decoded
    NEC, ditto 8, send 8, was saved at spacing 175 because every number
    in the dialog and at the door was taken from the bare 64.6 ms frame.
    On the air each send was the frame plus eight ditto frames, the
    silence floor bit, and the press held the air for far longer than
    the cap exists to allow.
    """

    def _info(self, fake_hass, **payload):
        conn = _conn()
        msg = {"id": 1, "type": "hair/send_spacing_info"}
        msg.update(payload)
        ws_send_spacing_info(fake_hass, conn, msg)
        return conn.send_result.call_args[0][1]

    @_needs_library
    def test_the_dittos_are_in_the_block_the_helper_reports(
        self, fake_hass
    ):
        _wire(fake_hass)
        plain = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=8, repeat_count=0
        )
        stormy = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=8, repeat_count=8,
            send_spacing_ms=175,
        )
        # Eight ditto frames on a NEC frame is an order of magnitude,
        # not a rounding difference.
        assert stormy["block_ms"] > 10 * plain["block_ms"]
        # 175 is now far under the block, so the floor decides the gap.
        assert stormy["floor_hit"] is True
        # And the press is over the cap, which is what the door reads.
        assert stormy["air_ms"] > SEND_AIR_TIME_MAX_MS

    def test_without_dittos_the_block_is_the_decoded_frame(
        self, fake_hass
    ):
        _wire(fake_hass)
        info = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=8, repeat_count=0
        )
        # The re-encoded NEC frame, not the captured Pronto's timings:
        # a few milliseconds apart, which is what the base patch's note
        # about the two blocks claimed for every case. It holds here,
        # and only here.
        assert 60 <= info["block_ms"] <= 80
        assert info["air_ms"] <= SEND_AIR_TIME_MAX_MS
        # Block plus terminator plus pipeline, rounded to 5.
        assert info["estimate_ms"] == round(
            (info["block_ms"] + 50 + 60) / 5
        ) * 5

    def test_a_pinned_row_keeps_its_captured_bytes(self, fake_hass):
        """A raw pin transmits the code as captured, so its dittos never
        reach the wire and must not reach the block either. The
        reporter's own rows are this shape: bypass, ditto 0."""
        _wire(fake_hass)
        plain = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=8, repeat_count=0,
            tx_force_raw=True,
        )
        stormy = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=8, repeat_count=8,
            tx_force_raw=True,
        )
        assert plain["block_ms"] == stormy["block_ms"]
        assert plain["estimate_ms"] == stormy["estimate_ms"]
        assert plain["floor_hit"] is False

    @pytest.mark.parametrize("send_count", [4, 8])
    def test_the_reporters_rows_are_unchanged(self, fake_hass, send_count):
        """Bypass, ditto 0, send 4 and 8: the shape that arrived on
        GH #151. Nothing about this fix may move them."""
        _wire(fake_hass)
        info = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=send_count,
            repeat_count=0, tx_force_raw=True,
        )
        assert info["estimate_ms"] == 175
        assert info["floor_hit"] is False
        assert info["air_ms"] <= SEND_AIR_TIME_MAX_MS

    @_needs_library
    def test_an_explicit_identity_is_believed_rather_than_re_decoded(
        self, fake_hass
    ):
        """A caller that already knows what the row is says so, and the
        helper does not spend a decode to reach the same answer."""
        _wire(fake_hass)
        info = self._info(
            fake_hass, pronto=NEC_PRONTO, send_count=8, repeat_count=8,
            decoded_protocol="NEC", decoded_address=0xFF00,
            decoded_command=0x45, decoded_fingerprint="NEC:0xff00:0x45",
        )
        assert info["block_ms"] > 800

    @pytest.mark.asyncio
    @_needs_library
    async def test_the_edit_door_refuses_the_ditto_storm(self, fake_hass):
        _wire(fake_hass, signal=_signal())
        fake_hass.states.async_all = MagicMock(return_value=[
            SimpleNamespace(entity_id="infrared.a", attributes={}),
        ])
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_unknown_signal_edit_pronto(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/signal/edit-pronto",
                "device_id": "cat-1", "signal_id": "sig-1",
                "pronto": NEC_PRONTO,
                "send_count": 8, "repeat_count": 8, "send_spacing_ms": 175,
            })
        assert conn.send_error.call_args[0][1] == "spacing_air_time"

    @pytest.mark.asyncio
    async def test_the_same_row_without_dittos_is_accepted(self, fake_hass):
        wired = _wire(fake_hass, signal=_signal())
        fake_hass.states.async_all = MagicMock(return_value=[
            SimpleNamespace(entity_id="infrared.a", attributes={}),
        ])
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_unknown_signal_edit_pronto(fake_hass, conn, {
                "id": 1, "type": "hair/unknown/signal/edit-pronto",
                "device_id": "cat-1", "signal_id": "sig-1",
                "pronto": NEC_PRONTO,
                "send_count": 8, "repeat_count": 0, "send_spacing_ms": 175,
            })
        conn.send_error.assert_not_called()
        assert wired.monitor.edit_signal_pronto.call_args.kwargs[
            "send_spacing_ms"
        ] == 175

    @pytest.mark.asyncio
    @_needs_library
    async def test_the_clipper_door_refuses_it_too(self, fake_hass):
        """No stored row exists there, so the code in the payload is
        what gets decoded. Same answer, same refusal."""
        _wire(fake_hass)
        fake_hass.states.async_all = MagicMock(return_value=[
            SimpleNamespace(entity_id="infrared.a", attributes={}),
        ])
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 1, "type": "hair/clip/create-signal",
                "device_id": "cat-1", "pronto": NEC_PRONTO,
                "send_count": 8, "repeat_count": 8, "send_spacing_ms": 175,
            })
        assert conn.send_error.call_args[0][1] == "spacing_air_time"

    @pytest.mark.asyncio
    @_needs_library
    async def test_a_knob_only_command_edit_is_judged_on_the_new_knob(
        self, fake_hass
    ):
        """No code in the payload, only a ditto count. The block the
        door measures has to be the one the row is about to have."""
        command = IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=NEC_PRONTO,
            decoded_protocol="NEC", decoded_address=0xFF00,
            decoded_command=0x45, decoded_fingerprint="NEC:0xff00:0x45",
            send_count=8,
        )
        _wire(fake_hass, command=command)
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_command_update(fake_hass, conn, {
                "id": 1, "type": "hair/command/update",
                "device_id": "dev-1", "command_id": "c1",
                "repeat_count": 8, "send_spacing_ms": 175,
            })
        assert conn.send_error.call_args[0][1] == "spacing_air_time"

    @pytest.mark.asyncio
    async def test_the_same_edit_without_the_storm_goes_through(
        self, fake_hass
    ):
        command = IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=NEC_PRONTO,
            decoded_protocol="NEC", decoded_address=0xFF00,
            decoded_command=0x45, decoded_fingerprint="NEC:0xff00:0x45",
            send_count=8,
        )
        wired = _wire(fake_hass, command=command)
        conn = _conn()
        with _platforms({"infrared.a": "esphome"}):
            await ws_command_update(fake_hass, conn, {
                "id": 1, "type": "hair/command/update",
                "device_id": "dev-1", "command_id": "c1",
                "repeat_count": 0, "send_spacing_ms": 175,
            })
        conn.send_error.assert_not_called()
        assert wired.manager.async_update_command.call_args.kwargs[
            "send_spacing_ms"
        ] == 175
