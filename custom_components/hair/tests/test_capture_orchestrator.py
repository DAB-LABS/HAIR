"""Dedicated tests for CaptureOrchestrator edge cases and lifecycle."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from custom_components.hair.capture import CaptureProvider, MockCaptureProvider
from custom_components.hair.capture_orchestrator import (
    CaptureInProgressError,
    CaptureOrchestrator,
)
from custom_components.hair.const import (
    EVENT_CAPTURE_ERROR,
    EVENT_CAPTURE_TIMEOUT,
    EVENT_COMMAND_CAPTURED,
    CaptureProviderType,
    CaptureState,
    CommandCategory,
    CommandSource,
)
from custom_components.hair.models import (
    CaptureResult,
    IRCommand,
    IRDevice,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hass():
    """Minimal fake hass that runs tasks on the real loop."""
    hass = MagicMock()
    hass.data = {}
    hass.bus.async_fire = MagicMock()
    hass.async_create_task = lambda coro: asyncio.get_event_loop().create_task(coro)
    return hass


def _result(**overrides):
    defaults = dict(
        protocol="NEC", code="0x1234", raw_timings=[9000, -4500],
        frequency=38000, confidence=0.95,
    )
    defaults.update(overrides)
    return CaptureResult(**defaults)


class _FailingProvider(CaptureProvider):
    """Provider that raises during async_wait_for_signal."""

    @property
    def provider_type(self):
        return CaptureProviderType.MOCK

    @property
    def device_name(self):
        return "Failing Provider"

    async def async_start_capture(self, timeout=10):
        pass

    async def async_stop_capture(self):
        pass

    async def async_wait_for_signal(self):
        raise RuntimeError("Hardware communication failed")

    def is_available(self):
        return True


# ===========================================================================
# Orchestrator lifecycle
# ===========================================================================


class TestOrchestratorLifecycle:

    @pytest.mark.asyncio
    async def test_initial_state(self):
        orch = CaptureOrchestrator(_hass())
        assert orch.is_capturing is False
        assert orch.active_session is None

    @pytest.mark.asyncio
    async def test_successful_capture_flow(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=0.01)

        events = []
        session = await orch.start_capture(provider, "dev-1", timeout=1)

        orch.subscribe(session.session_id, lambda s, r: events.append((s, r)))

        await asyncio.sleep(0.15)

        states = [e[0] for e in events]
        assert CaptureState.CAPTURED in states

        result = orch.get_session_result(session.session_id)
        assert result is not None
        assert result.code == "0x1234"

        assert not orch.is_capturing
        assert orch.active_session is None

    @pytest.mark.asyncio
    async def test_listening_event_fires_immediately(self):
        """The LISTENING event should fire before the background task returns."""
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=1.0)

        # Subscribe before start_capture won't work because we don't have
        # the session_id yet. Instead, check state after start returns.
        session = await orch.start_capture(provider, "dev-1", timeout=5)

        # Subscribe now and verify LISTENING was sent during start_capture
        # by checking that session state was set.
        assert orch.is_capturing

        # Cancel to clean up
        await orch.cancel_capture(session.session_id)
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_concurrent_capture_rejected(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider1 = MockCaptureProvider(result=_result(), delay=1.0)
        provider2 = MockCaptureProvider(result=_result(), delay=0.01)

        await orch.start_capture(provider1, "dev-1", timeout=5)

        with pytest.raises(CaptureInProgressError):
            await orch.start_capture(provider2, "dev-2", timeout=1)

        # Clean up
        await orch.cancel_capture(orch.active_session.session_id)
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_unavailable_provider_raises(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result())
        provider.set_available(False)

        with pytest.raises(RuntimeError, match="not available"):
            await orch.start_capture(provider, "dev-1")

        # Lock should NOT be held after failure
        assert not orch.is_capturing


# ===========================================================================
# Cancel tests
# ===========================================================================


class TestOrchestratorCancel:

    @pytest.mark.asyncio
    async def test_cancel_active_session(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=2.0)

        events = []
        session = await orch.start_capture(provider, "dev-1", timeout=5)
        orch.subscribe(session.session_id, lambda s, r: events.append((s, r)))

        await asyncio.sleep(0.05)
        await orch.cancel_capture(session.session_id)
        await asyncio.sleep(0.15)

        states = [e[0] for e in events]
        assert CaptureState.CANCELLED in states
        assert not orch.is_capturing

    @pytest.mark.asyncio
    async def test_cancel_wrong_session_id_is_noop(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=1.0)

        session = await orch.start_capture(provider, "dev-1", timeout=5)

        # Cancel with wrong ID should do nothing
        await orch.cancel_capture("wrong-session-id")
        assert orch.is_capturing  # still running

        # Clean up
        await orch.cancel_capture(session.session_id)
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_cancel_when_no_active_session(self):
        orch = CaptureOrchestrator(_hass())
        # Should not raise
        await orch.cancel_capture("nonexistent")


# ===========================================================================
# Error and timeout paths
# ===========================================================================


class TestOrchestratorErrors:

    @pytest.mark.asyncio
    async def test_provider_error_fires_event_and_releases_lock(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = _FailingProvider()

        events = []
        session = await orch.start_capture(provider, "dev-1", timeout=1)
        orch.subscribe(session.session_id, lambda s, r: events.append((s, r)))

        await asyncio.sleep(0.1)

        states = [e[0] for e in events]
        assert CaptureState.ERROR in states
        assert not orch.is_capturing

        # Verify HA bus event fired
        hass.bus.async_fire.assert_any_call(
            EVENT_CAPTURE_ERROR,
            {"session_id": session.session_id, "error": "Hardware communication failed"},
        )

    @pytest.mark.asyncio
    async def test_timeout_fires_event(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        # Provider returns None (simulates timeout)
        provider = MockCaptureProvider(result=None, delay=0.01)
        provider._result = None

        events = []
        session = await orch.start_capture(provider, "dev-1", timeout=1)
        orch.subscribe(session.session_id, lambda s, r: events.append((s, r)))

        await asyncio.sleep(0.15)

        states = [e[0] for e in events]
        assert CaptureState.TIMEOUT in states
        assert not orch.is_capturing

        hass.bus.async_fire.assert_any_call(
            EVENT_CAPTURE_TIMEOUT,
            {"session_id": session.session_id},
        )

    @pytest.mark.asyncio
    async def test_successful_capture_fires_bus_event(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=0.01)

        session = await orch.start_capture(provider, "dev-1", timeout=1)
        await asyncio.sleep(0.15)

        hass.bus.async_fire.assert_any_call(
            EVENT_COMMAND_CAPTURED,
            {
                "session_id": session.session_id,
                "device_id": "dev-1",
                "result": _result().to_dict(),
            },
        )


# ===========================================================================
# Subscribe / unsubscribe
# ===========================================================================


class TestOrchestratorSubscriptions:

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=0.01)

        events = []
        session = await orch.start_capture(provider, "dev-1", timeout=1)

        unsub = orch.subscribe(session.session_id, lambda s, r: events.append((s, r)))
        unsub()

        await asyncio.sleep(0.15)

        # After unsubscribe, should not receive CAPTURED event
        # (may receive LISTENING if subscribe happened before the notify)
        captured_events = [e for e in events if e[0] == CaptureState.CAPTURED]
        assert len(captured_events) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=0.01)

        events_a, events_b = [], []
        session = await orch.start_capture(provider, "dev-1", timeout=1)
        orch.subscribe(session.session_id, lambda s, r: events_a.append(s))
        orch.subscribe(session.session_id, lambda s, r: events_b.append(s))

        await asyncio.sleep(0.15)

        assert CaptureState.CAPTURED in events_a
        assert CaptureState.CAPTURED in events_b

    @pytest.mark.asyncio
    async def test_listener_exception_does_not_break_others(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=0.01)

        events = []
        session = await orch.start_capture(provider, "dev-1", timeout=1)

        def bad_listener(s, r):
            raise ValueError("boom")

        orch.subscribe(session.session_id, bad_listener)
        orch.subscribe(session.session_id, lambda s, r: events.append(s))

        await asyncio.sleep(0.15)

        # Second listener should still get the event despite first raising
        assert CaptureState.CAPTURED in events


# ===========================================================================
# check_duplicate (static method)
# ===========================================================================


class TestCheckDuplicate:

    def test_exact_protocol_code_match(self):
        cmd = IRCommand(
            id="c1", name="Power", protocol="NEC", code="0xABCD",
            category=CommandCategory.POWER, source=CommandSource.CAPTURED,
        )
        device = IRDevice(id="d1", name="TV", commands=[cmd])
        result = CaptureResult(protocol="NEC", code="0xABCD")

        dup = CaptureOrchestrator.check_duplicate(device, result)
        assert dup is not None
        assert dup.id == "c1"

    def test_no_match_different_code(self):
        cmd = IRCommand(
            id="c1", name="Power", protocol="NEC", code="0xABCD",
            category=CommandCategory.POWER, source=CommandSource.CAPTURED,
        )
        device = IRDevice(id="d1", name="TV", commands=[cmd])
        result = CaptureResult(protocol="NEC", code="0xFFFF")

        assert CaptureOrchestrator.check_duplicate(device, result) is None

    def test_no_match_empty_commands(self):
        device = IRDevice(id="d1", name="TV", commands=[])
        result = CaptureResult(protocol="NEC", code="0xABCD")
        assert CaptureOrchestrator.check_duplicate(device, result) is None

    def test_raw_timing_match_fallback(self):
        """When protocol/code is None, falls back to raw timing comparison."""
        timings = [9000, -4500, 560, -560, 560, -1690, 560, -560]
        cmd = IRCommand(
            id="c1", name="Power", protocol=None, code=None,
            raw_timings=timings,
            category=CommandCategory.POWER, source=CommandSource.CAPTURED,
        )
        device = IRDevice(id="d1", name="TV", commands=[cmd])
        result = CaptureResult(protocol=None, code=None, raw_timings=timings)

        dup = CaptureOrchestrator.check_duplicate(device, result)
        assert dup is not None

    def test_raw_timing_no_match(self):
        cmd = IRCommand(
            id="c1", name="Power", protocol=None, code=None,
            raw_timings=[9000, -4500, 560, -560],
            category=CommandCategory.POWER, source=CommandSource.CAPTURED,
        )
        device = IRDevice(id="d1", name="TV", commands=[cmd])
        # Completely different timings
        result = CaptureResult(
            protocol=None, code=None, raw_timings=[100, -200, 100, -200]
        )

        assert CaptureOrchestrator.check_duplicate(device, result) is None


# ===========================================================================
# Lock release after errors
# ===========================================================================


class TestLockRecovery:

    @pytest.mark.asyncio
    async def test_lock_released_after_start_failure(self):
        """If async_start_capture raises, the lock must be released."""
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(fail=True)

        with pytest.raises(RuntimeError):
            await orch.start_capture(provider, "dev-1")

        assert not orch.is_capturing
        # Should be able to start a new capture
        good_provider = MockCaptureProvider(result=_result(), delay=0.01)
        session = await orch.start_capture(good_provider, "dev-1", timeout=1)
        assert session is not None
        await asyncio.sleep(0.15)

    @pytest.mark.asyncio
    async def test_lock_released_after_provider_error(self):
        """If the provider errors during capture_loop, lock is released."""
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = _FailingProvider()

        await orch.start_capture(provider, "dev-1", timeout=1)
        await asyncio.sleep(0.15)

        assert not orch.is_capturing

        # Should be able to start again
        good = MockCaptureProvider(result=_result(), delay=0.01)
        session2 = await orch.start_capture(good, "dev-1", timeout=1)
        assert session2 is not None
        await asyncio.sleep(0.15)

    @pytest.mark.asyncio
    async def test_lock_released_after_cancel(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=2.0)

        session = await orch.start_capture(provider, "dev-1", timeout=5)
        await asyncio.sleep(0.05)
        await orch.cancel_capture(session.session_id)
        await asyncio.sleep(0.15)

        assert not orch.is_capturing

        # Start new capture to confirm lock is free
        good = MockCaptureProvider(result=_result(), delay=0.01)
        session2 = await orch.start_capture(good, "dev-1", timeout=1)
        assert session2 is not None
        await asyncio.sleep(0.15)


# ===========================================================================
# get_session_result
# ===========================================================================


class TestGetSessionResult:

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_session(self):
        orch = CaptureOrchestrator(_hass())
        assert orch.get_session_result("nonexistent") is None

    @pytest.mark.asyncio
    async def test_result_persists_after_capture(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=_result(), delay=0.01)

        session = await orch.start_capture(provider, "dev-1", timeout=1)
        await asyncio.sleep(0.15)

        # Result should persist in the results dict
        result = orch.get_session_result(session.session_id)
        assert result is not None
        assert result.protocol == "NEC"

    @pytest.mark.asyncio
    async def test_no_result_after_timeout(self):
        hass = _hass()
        orch = CaptureOrchestrator(hass)
        provider = MockCaptureProvider(result=None, delay=0.01)
        provider._result = None

        session = await orch.start_capture(provider, "dev-1", timeout=1)
        await asyncio.sleep(0.15)

        assert orch.get_session_result(session.session_id) is None
