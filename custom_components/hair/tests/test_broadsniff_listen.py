"""HAIR opens and closes a BroadSniff remote's capture window.

BroadSniff (DAB-LABS/broadsniff) gives a Broadlink an IR receiver on
the infrared platform, but the remote only hears codes while a capture
window is open. These tests run against a fake BroadSniff remote in the
entity registry, shaped as BroadSniff 0.1.0 registers one: every entity
on platform ``broadsniff``, on the remote's device, with a unique ID of
``<mac>-<suffix>``. Entity IDs are deliberately odd, because HAIR must
find the entities by registry and never by name.

Without BroadSniff in the registry nothing may change, and the first
class says so.
"""
from __future__ import annotations

import asyncio
import contextlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import broadsniff as bs
from custom_components.hair.broadsniff import (
    ARM_FAILED_CODE,
    BroadSniffArmError,
    broadsniff_remote,
    ir_capture_switch,
    list_broadsniff_receivers,
)
from custom_components.hair.capture import NativeCaptureProvider
from custom_components.hair.capture_orchestrator import CaptureOrchestrator
from custom_components.hair.const import CaptureState

MAC = "a1b2c3d4e5f6"
DEVICE = "bsdev-living"
RECEIVER = "infrared.wohnzimmer_empfaenger"  # renamed by the user
SWITCH = "switch.the_listen_thing"
MODE = "select.living_mode"
WINDOW = "number.living_window"
CODES = "sensor.living_codes"
CORE_EMITTER = "infrared.living_room_rm4"  # the built-in Broadlink's
ESPHOME_RX = "infrared.athom_rx"

OTHER_MAC = "001122334455"
OTHER_DEVICE = "bsdev-office"
OTHER_RECEIVER = "infrared.office_rm_mini_ir_receiver"
OTHER_SWITCH = "switch.office_rm_mini_ir_capture"


def _entry(entity_id, platform, unique_id, device_id):
    return SimpleNamespace(
        entity_id=entity_id, platform=platform,
        unique_id=unique_id, device_id=device_id,
    )


def _registry_entries(*, with_broadsniff: bool = True):
    entries = [
        _entry(CORE_EMITTER, "broadlink", f"{MAC}-ir", "core-living"),
        _entry(ESPHOME_RX, "esphome", "athom-rx", "athom"),
    ]
    if with_broadsniff:
        entries += [
            _entry(RECEIVER, "broadsniff", f"{MAC}-receiver", DEVICE),
            _entry(SWITCH, "broadsniff", f"{MAC}-ir_capture", DEVICE),
            _entry("switch.living_rf", "broadsniff", f"{MAC}-rf_capture", DEVICE),
            _entry(MODE, "broadsniff", f"{MAC}-capture_mode", DEVICE),
            _entry(WINDOW, "broadsniff", f"{MAC}-capture_window", DEVICE),
            _entry(CODES, "broadsniff", f"{MAC}-codes_captured", DEVICE),
            _entry(OTHER_RECEIVER, "broadsniff", f"{OTHER_MAC}-receiver", OTHER_DEVICE),
            _entry(OTHER_SWITCH, "broadsniff", f"{OTHER_MAC}-ir_capture", OTHER_DEVICE),
        ]
    return entries


@contextlib.contextmanager
def _registry(entries, devices=None):
    by_id = {e.entity_id: e for e in entries}
    registry = SimpleNamespace(async_get=by_id.get)

    def for_device(_registry, device_id, **_kw):
        return [e for e in entries if e.device_id == device_id]

    devices = devices or {
        DEVICE: SimpleNamespace(name="Living Room RM4", name_by_user=None),
        OTHER_DEVICE: SimpleNamespace(name="Office RM mini", name_by_user="Office"),
    }
    device_registry = SimpleNamespace(async_get=devices.get)
    with (
        patch.object(bs.er, "async_get", return_value=registry),
        patch.object(bs.er, "async_entries_for_device", side_effect=for_device),
        patch.object(bs.dr, "async_get", return_value=device_registry),
    ):
        yield


class _Hass:
    """States, a switch service that moves the switch, and real tasks."""

    def __init__(self, *, switch="off", mode="sliding", fail_on=()):
        self.data = {}
        self._states = {
            SWITCH: SimpleNamespace(state=switch, attributes={}),
            OTHER_SWITCH: SimpleNamespace(state="off", attributes={}),
            MODE: SimpleNamespace(state=mode, attributes={}),
            RECEIVER: SimpleNamespace(state="on", attributes={}),
            ESPHOME_RX: SimpleNamespace(state="on", attributes={}),
        }
        self.states = SimpleNamespace(get=self._states.get)
        self.calls: list[tuple[str, str, str]] = []
        self._fail_on = set(fail_on)

        async def async_call(domain, service, data, blocking=False):
            entity_id = data["entity_id"]
            self.calls.append((domain, service, entity_id))
            if len(self.calls) in self._fail_on:
                raise RuntimeError("device did not answer")
            self._states[entity_id] = SimpleNamespace(
                state="on" if service == "turn_on" else "off", attributes={},
            )

        self.services = SimpleNamespace(async_call=async_call)
        self.bus = SimpleNamespace(async_fire=MagicMock())

    def async_create_task(self, coro):
        return asyncio.get_running_loop().create_task(coro)

    def set(self, entity_id, state):
        self._states[entity_id] = SimpleNamespace(state=state, attributes={})


@contextlib.contextmanager
def _receivers_and_tracking(receivers=(RECEIVER, OTHER_RECEIVER, ESPHOME_RX)):
    """The infrared platform's receiver API and HA's state tracker."""
    listeners: dict[str, list] = {}
    unsubscribed: list[str] = []

    def track(_hass, entity_ids, action):
        for entity_id in entity_ids:
            listeners.setdefault(entity_id, []).append(action)

        def unsub():
            for entity_id in entity_ids:
                listeners[entity_id].remove(action)
                unsubscribed.append(entity_id)

        return unsub

    infrared = MagicMock()
    infrared.async_get_receivers = lambda _hass: list(receivers)
    infrared.async_subscribe_receiver = MagicMock(return_value=MagicMock())
    with (
        patch.dict("sys.modules", {"homeassistant.components.infrared": infrared}),
        patch("homeassistant.helpers.event.async_track_state_change_event", track),
    ):
        yield SimpleNamespace(
            listeners=listeners, unsubscribed=unsubscribed, infrared=infrared,
        )


def _close_window(hass: _Hass, tracking) -> None:
    """BroadSniff closing the window on its own: the switch goes off."""
    hass.set(SWITCH, "off")
    event = SimpleNamespace(data={"new_state": SimpleNamespace(state="off")})
    for action in list(tracking.listeners.get(SWITCH, [])):
        action(event)


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Without BroadSniff, nothing changes
# ---------------------------------------------------------------------------


class TestWithoutBroadSniff:
    @pytest.mark.asyncio
    async def test_a_capture_session_makes_no_switch_calls(self):
        hass = _Hass()
        with _registry(_registry_entries(with_broadsniff=False)), \
                _receivers_and_tracking(receivers=(ESPHOME_RX,)) as tracking:
            provider = NativeCaptureProvider(hass, ESPHOME_RX)
            await provider.async_start_capture(timeout=1)
            await provider.async_stop_capture()
        assert hass.calls == []
        assert tracking.listeners == {}

    def test_no_receiver_is_a_broadsniff_receiver(self):
        hass = _Hass()
        with _registry(_registry_entries(with_broadsniff=False)), \
                _receivers_and_tracking(receivers=(ESPHOME_RX,)):
            assert ir_capture_switch(hass, ESPHOME_RX) is None
            assert ir_capture_switch(hass, RECEIVER) is None
            assert list_broadsniff_receivers(hass) == []


# ---------------------------------------------------------------------------
# The helper: by registry, never by name
# ---------------------------------------------------------------------------


class TestTheHelper:
    def test_it_finds_the_switch_whatever_the_entities_are_called(self):
        with _registry(_registry_entries()):
            remote = broadsniff_remote(_Hass(), RECEIVER)
        assert remote is not None
        assert (remote.switch, remote.mode, remote.window, remote.codes) == (
            SWITCH, MODE, WINDOW, CODES,
        )
        assert remote.device_id == DEVICE

    def test_it_never_returns_another_remotes_entities(self):
        entries = _registry_entries()
        # Even a second remote's switch on the SAME device is not ours:
        # the unique ID prefix decides, not the device alone.
        entries.append(_entry(
            "switch.stray", "broadsniff", f"{OTHER_MAC}-ir_capture", DEVICE,
        ))
        with _registry(entries):
            assert ir_capture_switch(_Hass(), RECEIVER) == SWITCH
            assert ir_capture_switch(_Hass(), OTHER_RECEIVER) == OTHER_SWITCH

    def test_a_receiver_of_another_platform_is_not_broadsniff(self):
        with _registry(_registry_entries()):
            assert ir_capture_switch(_Hass(), ESPHOME_RX) is None
            assert ir_capture_switch(_Hass(), CORE_EMITTER) is None
            assert ir_capture_switch(_Hass(), "infrared.unknown") is None

    def test_a_remote_without_its_switch_is_not_armable(self):
        entries = [e for e in _registry_entries() if e.entity_id != SWITCH]
        with _registry(entries):
            assert broadsniff_remote(_Hass(), RECEIVER) is None

    def test_registry_trouble_is_not_broadsniff(self):
        with patch.object(bs.er, "async_get", side_effect=RuntimeError("boom")):
            assert ir_capture_switch(_Hass(), RECEIVER) is None

    def test_the_listen_rows(self):
        with _registry(_registry_entries()), _receivers_and_tracking():
            rows = list_broadsniff_receivers(_Hass())
        assert [r["name"] for r in rows] == ["Living Room RM4", "Office"]
        living = rows[0]
        assert living == {
            "receiver_entity_id": RECEIVER,
            "switch_entity_id": SWITCH,
            "mode_entity_id": MODE,
            "window_entity_id": WINDOW,
            "codes_entity_id": CODES,
            "ha_device_id": DEVICE,
            "name": "Living Room RM4",
        }


# ---------------------------------------------------------------------------
# A capture session on a BroadSniff receiver
# ---------------------------------------------------------------------------


class TestACaptureSession:
    @pytest.mark.asyncio
    async def test_it_turns_the_switch_on_and_then_off(self):
        hass = _Hass(switch="off")
        with _registry(_registry_entries()), _receivers_and_tracking() as tracking:
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=1)
            assert hass.calls == [("switch", "turn_on", SWITCH)]
            await provider.async_stop_capture()
        assert hass.calls == [
            ("switch", "turn_on", SWITCH), ("switch", "turn_off", SWITCH),
        ]
        assert tracking.unsubscribed == [SWITCH]

    @pytest.mark.asyncio
    async def test_a_window_the_user_opened_is_left_open(self):
        hass = _Hass(switch="on")
        with _registry(_registry_entries()), _receivers_and_tracking():
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=1)
            await provider.async_stop_capture()
        assert hass.calls == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["sliding", "multiple"])
    async def test_a_window_that_closes_mid_session_is_rearmed(self, mode):
        hass = _Hass(switch="off", mode=mode)
        with _registry(_registry_entries()), \
                _receivers_and_tracking() as tracking, \
                patch.object(bs, "monotonic", side_effect=[0.0, 10.0, 10.0, 20.0]):
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=1)
            _close_window(hass, tracking)
            await _settle()
            assert hass.calls == [("switch", "turn_on", SWITCH)] * 2
            await provider.async_stop_capture()
            # Re-arming stops with the session.
            _close_window(hass, tracking)
            await _settle()
        assert hass.calls[-1] == ("switch", "turn_off", SWITCH)
        assert hass.calls.count(("switch", "turn_on", SWITCH)) == 2

    @pytest.mark.asyncio
    async def test_a_user_window_that_closes_is_rearmed_and_then_hairs(self):
        hass = _Hass(switch="on")
        with _registry(_registry_entries()), \
                _receivers_and_tracking() as tracking, \
                patch.object(bs, "monotonic", side_effect=[10.0, 20.0]):
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=1)
            _close_window(hass, tracking)
            await _settle()
            await provider.async_stop_capture()
        assert hass.calls == [
            ("switch", "turn_on", SWITCH), ("switch", "turn_off", SWITCH),
        ]

    @pytest.mark.asyncio
    async def test_single_mode_is_never_rearmed_and_ends_with_its_window(self):
        """Owner ruling 2026-10-17: in single mode the window IS the
        session. An empty window ends the session at once."""
        hass = _Hass(switch="off", mode="single")
        with _registry(_registry_entries()), _receivers_and_tracking() as tracking:
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=30)
            _close_window(hass, tracking)
            await _settle()
            result = await asyncio.wait_for(provider.async_wait_for_signal(), 1)
            await provider.async_stop_capture()
        assert result is None
        assert hass.calls == [("switch", "turn_on", SWITCH)]

    @pytest.mark.asyncio
    async def test_single_mode_takes_the_code_heard_before_its_window_closed(self):
        hass = _Hass(switch="off", mode="single")
        with _registry(_registry_entries()), _receivers_and_tracking() as tracking:
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=30)
            heard = SimpleNamespace(code="0x1234")
            provider._signal_queue.put_nowait(heard)
            _close_window(hass, tracking)
            result = await asyncio.wait_for(provider.async_wait_for_signal(), 1)
            await provider.async_stop_capture()
        assert result is heard

    @pytest.mark.asyncio
    async def test_a_failed_start_ends_the_session_with_no_retry(self):
        hass = _Hass(switch="off", fail_on={1})
        with _registry(_registry_entries()), _receivers_and_tracking() as tracking:
            provider = NativeCaptureProvider(hass, RECEIVER)
            with pytest.raises(BroadSniffArmError) as raised:
                await provider.async_start_capture(timeout=1)
            await _settle()
        assert raised.value.code == ARM_FAILED_CODE
        assert hass.calls == [("switch", "turn_on", SWITCH)]
        assert tracking.listeners.get(SWITCH, []) == []
        assert provider._running is False
        tracking.infrared.async_subscribe_receiver.return_value.assert_called_once()

    @pytest.mark.asyncio
    async def test_a_failed_rearm_ends_the_session_with_no_retry(self):
        hass = _Hass(switch="off", fail_on={2})
        with _registry(_registry_entries()), \
                _receivers_and_tracking() as tracking, \
                patch.object(bs, "monotonic", side_effect=[0.0, 10.0]):
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=30)
            _close_window(hass, tracking)
            await _settle()
            with pytest.raises(BroadSniffArmError):
                await asyncio.wait_for(provider.async_wait_for_signal(), 1)
            _close_window(hass, tracking)
            await _settle()
            await provider.async_stop_capture()
        assert hass.calls == [("switch", "turn_on", SWITCH)] * 2

    @pytest.mark.asyncio
    async def test_a_window_that_closes_at_once_is_not_rearmed_in_a_loop(self):
        hass = _Hass(switch="off")
        with _registry(_registry_entries()), \
                _receivers_and_tracking() as tracking, \
                patch.object(bs, "monotonic", side_effect=[0.0, 0.1]):
            provider = NativeCaptureProvider(hass, RECEIVER)
            await provider.async_start_capture(timeout=30)
            _close_window(hass, tracking)
            with pytest.raises(BroadSniffArmError):
                await asyncio.wait_for(provider.async_wait_for_signal(), 1)
            await provider.async_stop_capture()
        assert hass.calls == [("switch", "turn_on", SWITCH)]


class TestTheOrchestrator:
    @pytest.mark.asyncio
    async def test_a_failed_rearm_reaches_the_session_as_its_error(self):
        hass = _Hass(switch="off", fail_on={2})
        orchestrator = CaptureOrchestrator(hass)
        events: list = []
        with _registry(_registry_entries()), \
                _receivers_and_tracking() as tracking, \
                patch.object(bs, "monotonic", side_effect=[0.0, 10.0]):
            provider = NativeCaptureProvider(hass, RECEIVER)
            session = await orchestrator.start_capture(provider, "dev-1", timeout=30)
            orchestrator.subscribe(
                session.session_id, lambda state, _r: events.append(state),
            )
            _close_window(hass, tracking)
            await _settle()
            await asyncio.wait_for(orchestrator._task, 1) if orchestrator._task else None
            await _settle()
        assert events[-1] is CaptureState.ERROR
        assert session.error_code == ARM_FAILED_CODE
        assert session.error == "The Broadlink could not start listening"
        assert not orchestrator.is_capturing


# ---------------------------------------------------------------------------
# The Listen row's websocket doors
# ---------------------------------------------------------------------------


class TestTheWebsocket:
    def _wire(self, hass):
        from custom_components.hair.const import DOMAIN

        hass.data[DOMAIN] = {"entry-1": {}}

    def test_the_rows(self):
        from custom_components.hair.websocket_api import ws_broadsniff_receivers

        hass = _Hass()
        conn = MagicMock()
        with _registry(_registry_entries()), _receivers_and_tracking():
            ws_broadsniff_receivers(hass, conn, {"id": 1})
        rows = conn.send_result.call_args[0][1]
        assert [r["switch_entity_id"] for r in rows] == [SWITCH, OTHER_SWITCH]

    def test_no_rows_without_broadsniff(self):
        from custom_components.hair.websocket_api import ws_broadsniff_receivers

        conn = MagicMock()
        with _registry(_registry_entries(with_broadsniff=False)), \
                _receivers_and_tracking(receivers=(ESPHOME_RX,)):
            ws_broadsniff_receivers(_Hass(), conn, {"id": 1})
        assert conn.send_result.call_args[0][1] == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("on, service", [(True, "turn_on"), (False, "turn_off")])
    async def test_listen_toggles_the_resolved_switch(self, on, service):
        from custom_components.hair.websocket_api import ws_broadsniff_listen

        hass = _Hass(switch="off" if on else "on")
        conn = MagicMock()
        with _registry(_registry_entries()):
            await ws_broadsniff_listen(hass, conn, {
                "id": 2, "receiver_entity_id": RECEIVER, "on": on,
            })
        assert not conn.send_error.called
        assert hass.calls == [("switch", service, SWITCH)]

    @pytest.mark.asyncio
    async def test_listen_refuses_anything_that_is_not_broadsniff(self):
        from custom_components.hair.websocket_api import ws_broadsniff_listen

        hass = _Hass()
        conn = MagicMock()
        with _registry(_registry_entries()):
            await ws_broadsniff_listen(hass, conn, {
                "id": 3, "receiver_entity_id": ESPHOME_RX, "on": True,
            })
        assert conn.send_error.call_args[0][1] == "not_broadsniff"
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_listen_says_when_the_broadlink_would_not_start(self):
        from custom_components.hair.websocket_api import ws_broadsniff_listen

        hass = _Hass(fail_on={1})
        conn = MagicMock()
        with _registry(_registry_entries()):
            await ws_broadsniff_listen(hass, conn, {
                "id": 4, "receiver_entity_id": RECEIVER, "on": True,
            })
        assert conn.send_error.call_args[0][1] == ARM_FAILED_CODE

    @pytest.mark.asyncio
    async def test_a_session_start_failure_reaches_the_panel_with_its_code(self):
        from custom_components.hair.websocket_api import ws_start_capture

        orchestrator = MagicMock()
        orchestrator.start_capture = AsyncMock(side_effect=BroadSniffArmError())
        device = SimpleNamespace(
            id="dev-1", capture_device_id=RECEIVER,
            capture_provider_type="native",
        )
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        hass = _Hass()
        from custom_components.hair.const import DOMAIN

        hass.data[DOMAIN] = {"entry-1": {
            "device_manager": manager, "orchestrator": orchestrator,
        }}
        conn = MagicMock()
        with patch(
            "custom_components.hair.websocket_api.get_capture_provider_for_device",
            AsyncMock(return_value=MagicMock()),
        ):
            await ws_start_capture(hass, conn, {"id": 5, "device_id": "dev-1"})
        assert conn.send_error.call_args[0][1:] == (
            ARM_FAILED_CODE, "The Broadlink could not start listening",
        )


# ---------------------------------------------------------------------------
# HAIR's own send, heard by the Broadlink it went out through
# ---------------------------------------------------------------------------


class TestTheEcho:
    """Kickoff, differs from brief item 7: the echo defence is keyed by
    the code's identity, not by device, so a BroadSniff receiver that
    hears what HAIR just sent through the same Broadlink's built-in
    emitter is already claimed. No MAC matching is needed."""

    def _monitor(self):
        from custom_components.hair.signal_monitor import SignalMonitor

        from .test_signal_monitor import (
            _make_hair_store,
            _make_hass,
            _make_signal_store,
        )

        hass = _make_hass()
        trigger_manager = MagicMock()
        monitor = SignalMonitor(
            hass, _make_signal_store(hass), _make_hair_store(), trigger_manager,
        )
        return monitor, trigger_manager, hass

    @staticmethod
    async def _drain(hass):
        """Run what record_send scheduled (its Mirror row), so nothing
        is left un-awaited."""
        for call in hass.async_create_task.call_args_list:
            coro = call.args[0]
            if asyncio.iscoroutine(coro):
                await coro

    def _parsed(self):
        from custom_components.hair import signal_monitor as sm

        from .test_signal_monitor import _make_event, _nec_event

        parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
        return parsed, sm.normalize(parsed)

    @pytest.mark.asyncio
    async def test_the_broadlinks_own_send_is_claimed_as_an_echo(self):
        from custom_components.hair import signal_monitor as sm

        monitor, triggers, hass = self._monitor()
        parsed, n = self._parsed()
        with patch.object(sm, "normalize_command", lambda _c: n):
            monitor.record_send(
                object(), "TV / Power", [CORE_EMITTER],
                decoded_fingerprint=n.decoded_fingerprint, send_count=1,
            )
            await self._drain(hass)
        # The built-in Broadlink emitter's beacon: the IR has left.
        monitor._arm_expectations_for(CORE_EMITTER, sm.monotonic())

        await monitor._process_parsed_signal(parsed, receiver_entity_id=RECEIVER)

        triggers.on_signal_captured.assert_not_called()
        assert monitor._echo_expectations[0]["claims_left"] == {RECEIVER: 0}

    @pytest.mark.asyncio
    async def test_the_same_code_with_no_send_is_a_real_press(self):
        monitor, triggers, _hass = self._monitor()
        parsed, _ = self._parsed()

        await monitor._process_parsed_signal(parsed, receiver_entity_id=RECEIVER)

        assert triggers.on_signal_captured.call_count == 1
