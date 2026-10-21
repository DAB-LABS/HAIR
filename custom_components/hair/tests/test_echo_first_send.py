"""The first send through an emitter whose state is "unknown" (0.18.1).

An infrared emitter's state is the timestamp of its last send, and
"unknown" until the first one. Core restores anything but "unavailable",
so an emitter that was offline when Home Assistant stopped comes back
"unknown" too, and stays so until it sends.

HAIR arms a send's echo ticket from the emitter's beacon (Track 3a).
The beacon handler used to read every transition FROM "unknown" as a
restore and return before arming, so the first send through such an
emitter left its ticket unarmed. The echo a receiver handed back about
180 ms later was read as a real press: on VM999 (2026-10-21) the Samsung
TV Remote's trigger fired, its pin re-sent Power On, and Last pressed
fired. The arm fallback (1.5 s) comes far too late for that.

Owner ruling: HAIR's own send arms from "unknown"; a foreign beacon from
"unknown" keeps the old restore rule (``test_reconnect_restore_ignored``
in test_mirror.py stays).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair import signal_monitor as sm
from custom_components.hair.const import DOMAIN
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.storage import HAIRStore

from .test_signal_monitor import (
    _make_event,
    _make_hair_store,
    _make_hass,
    _make_signal_store,
    _nec_event,
)

RM4 = "infrared.wi_fi_universal_remote_ir_emitter"
ATHOM = "infrared.athom_rx"
LAST_SEND = "2026-10-20T18:30:29.751+00:00"
THIS_SEND = "2026-10-21T03:34:27.690+00:00"


def _beacon(old: str, new: str = THIS_SEND):
    """The state write core makes when a platform send returns."""
    attrs = {"device_class": "emitter", "friendly_name": "RM4 Pro"}
    return SimpleNamespace(
        data={
            "entity_id": RM4,
            "new_state": SimpleNamespace(state=new, attributes=attrs),
            "old_state": SimpleNamespace(state=old, attributes=attrs),
        },
        context=SimpleNamespace(parent_id=None),
    )


def _monitor():
    hass = _make_hass()
    # record_send schedules the Mirror upsert; these tests are about the
    # ticket, so the coroutine is closed rather than left un-awaited.
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
    trigger_manager = MagicMock()
    monitor = SignalMonitor(
        hass, _make_signal_store(hass), _make_hair_store(), trigger_manager
    )
    return monitor, trigger_manager


def _capture():
    parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
    return parsed, sm.normalize(parsed)


def _send_then_beacon(old_state: str):
    """HAIR sends through the RM4, then core writes its state."""
    monitor, tm = _monitor()
    parsed, n = _capture()
    with patch.object(sm, "normalize_command", lambda _c: n):
        monitor.record_send(
            object(), "Samsung TV / Power On", [RM4],
            decoded_fingerprint=n.decoded_fingerprint, send_count=1,
        )
    monitor._on_emitter_beacon(_beacon(old_state))
    return monitor, tm, parsed


class TestHairsOwnSend:
    @pytest.mark.asyncio
    async def test_an_emitter_that_has_sent_before_arms_and_claims(self):
        """The control: the case that always worked."""
        monitor, tm, parsed = _send_then_beacon(LAST_SEND)
        assert monitor._echo_expectations[0]["armed_at"] is not None
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_emitter_whose_state_is_unknown_arms_and_claims(self):
        """THE bug. The first send through an emitter that had never
        sent, or was offline when Home Assistant last stopped: the echo
        is HAIR's own and reaches no trigger."""
        monitor, tm, parsed = _send_then_beacon("unknown")
        assert monitor._echo_expectations[0]["armed_at"] is not None
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_send_from_unknown_still_marks_the_mirror_heard(self):
        """The claim is a real claim: the receiver spends its budget,
        as it would for any other send."""
        monitor, _, parsed = _send_then_beacon("unknown")
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
        assert monitor._echo_expectations[0]["claims_left"] == {ATHOM: 0}

    def test_coming_back_from_unavailable_still_arms_nothing(self):
        """A reconnect inside a send window is not when IR left; the
        fallback arms that ticket, as before."""
        monitor, _, _ = _send_then_beacon("unavailable")
        assert monitor._echo_expectations[0]["armed_at"] is None

    @pytest.mark.asyncio
    async def test_a_capture_before_the_beacon_is_still_a_press(self):
        """Track 3a holds: until IR has left, nothing claims."""
        monitor, tm = _monitor()
        parsed, n = _capture()
        with patch.object(sm, "normalize_command", lambda _c: n):
            monitor.record_send(
                object(), "Samsung TV / Power On", [RM4],
                decoded_fingerprint=n.decoded_fingerprint, send_count=1,
            )
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
        assert tm.on_signal_captured.call_count == 1


class TestForeignBeacons:
    def test_a_foreign_send_from_unknown_still_opens_no_window(self):
        """Owner ruling: foreign beacons keep the v0.6.6 restore rule."""
        monitor, _ = _monitor()
        monitor._on_emitter_beacon(_beacon("unknown"))
        assert monitor._foreign_pending == {}
        assert monitor._echo_expectations == []

    def test_a_foreign_send_from_a_timestamp_still_opens_one(self):
        monitor, _ = _monitor()
        monitor._on_emitter_beacon(_beacon(LAST_SEND))
        assert RM4 in monitor._foreign_pending


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
            yield DeviceManager(
                fake_hass, store, EntityFactory(fake_hass), "entry-1"
            )


class TestThroughTheSendPath:
    """End to end: a Device send through ``_async_broadcast``, core's
    state write from inside the platform send, then the echo."""

    async def _send_and_echo(self, manager, emitter_state: str):
        monitor, tm = _monitor()
        manager._hass.data[DOMAIN] = {"entry-1": {"signal_monitor": monitor}}
        manager._hass.states.get = MagicMock(
            return_value=SimpleNamespace(state=emitter_state)
        )
        device = IRDevice(
            name="Samsung TV",
            emitter_entity_ids=[RM4],
            commands=[IRCommand(
                id="c1", name="Power On",
                raw_timings=[4000, -2000, 4000],
            )],
        )
        manager._store.add_device(device)
        parsed, n = _capture()

        async def _core_send(hass, entity_id, command, **_kw):
            # async_send_command_internal: transmit, then write state.
            monitor._on_emitter_beacon(_beacon(emitter_state))

        with patch.object(sm, "normalize_command", lambda _c: n), \
                patch.object(
                    _infrared_mod, "async_send_command",
                    AsyncMock(side_effect=_core_send),
                ) as ir_send:
            await manager.async_send_command(device.id, "c1")
        assert ir_send.await_count == 1
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
        return monitor, tm

    @pytest.mark.asyncio
    async def test_an_unknown_emitter_echo_is_claimed(self, manager):
        monitor, tm = await self._send_and_echo(manager, "unknown")
        assert monitor._echo_expectations[0]["emitters"] == [RM4]
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_emitter_that_has_sent_before_is_claimed(self, manager):
        _, tm = await self._send_and_echo(manager, LAST_SEND)
        tm.on_signal_captured.assert_not_called()
