"""Tests for the SignalMonitor always-on listener."""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    EVENT_DISMISS_ACTIVITY,
    EVENT_SIGNAL_DETECTED,
    LEGACY_ESPHOME_IR_EVENT,
    SIGNAL_CLUSTER_THRESHOLD,
    SIGNAL_RATE_LIMIT_PER_SEC,
    SIGNAL_REPEAT_SUPPRESS_MS,
    SIGNAL_WS_PUSH_RATE_LIMIT,
)
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hass():
    """Create a minimal mock HomeAssistant.

    ``async_create_task`` is configured to return the coroutine it
    receives unmodified. That way, tests exercising sync ``@callback``
    handlers that schedule async work can drain the pending coroutine
    via ``await hass.async_create_task.call_args[0][0]`` rather than
    leaving it as an un-awaited RuntimeWarning.
    """
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_later = MagicMock(return_value=MagicMock())
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=MagicMock())
    hass.bus.async_fire = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states = MagicMock()
    # Default: entity exists (returns a mock state).
    hass.states.get = MagicMock(return_value=MagicMock())
    return hass


def _make_signal_store(hass):
    store = SignalStore(hass)
    store._loaded = True
    return store


def _make_hair_store():
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    return hair_store


def _make_event(data: dict):
    event = MagicMock()
    event.data = data
    return event


def _nec_event(code: str = "0x1234", protocol: str = "NEC") -> dict:
    return {"protocol": protocol, "code": code}


def _raw_event(timings: list[int] | None = None) -> dict:
    return {"raw": timings or [9000, -4500, 560, -560, 560, -1690]}


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestLifecycle:

    @pytest.mark.asyncio
    async def test_start_subscribes_to_bus(self):
        """Legacy fallback: subscribes to esphome.remote_received."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())
        await monitor.async_start()
        hass.bus.async_listen.assert_called_once()
        args = hass.bus.async_listen.call_args
        assert args[0][0] == LEGACY_ESPHOME_IR_EVENT

    @pytest.mark.asyncio
    async def test_start_legacy_fallback_sets_native_mode_false(self):
        """In test env, native import fails so legacy path activates."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())
        await monitor.async_start()
        assert not monitor.native_mode

    @pytest.mark.asyncio
    async def test_start_loads_store_if_not_loaded(self):
        hass = _make_hass()
        store = SignalStore(hass)
        with patch.object(store, "_store") as mock_inner:
            mock_inner.async_load = AsyncMock(return_value=None)
            monitor = SignalMonitor(hass, store, _make_hair_store())
            await monitor.async_start()
        assert store.loaded

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_and_flushes(self):
        hass = _make_hass()
        unsub = MagicMock()
        hass.bus.async_listen.return_value = unsub
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())
        await monitor.async_start()
        await monitor.async_stop()
        unsub.assert_called_once()


# ---------------------------------------------------------------------------
# Event handling -- basic flow
# ---------------------------------------------------------------------------


class TestEventHandling:

    @pytest.mark.asyncio
    async def test_parseable_event_creates_device_and_signal(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        assert store.device_count == 1
        devices = store.get_all_devices()
        assert len(devices) == 1
        assert devices[0].hit_count == 1
        assert len(devices[0].signals) == 1
        assert devices[0].signals[0].hit_count == 1

    @pytest.mark.asyncio
    async def test_unparseable_event_ignored(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event({}))
        assert store.device_count == 0

    @pytest.mark.asyncio
    async def test_nec_repeat_ignored(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event({
            "protocol": "NEC", "repeat": True,
        }))
        assert store.device_count == 0

    @pytest.mark.asyncio
    async def test_duplicate_signal_increments_counts(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # First event.
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        # Clear repeat suppression so second event goes through.
        monitor._last_seen_times.clear()
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        assert store.device_count == 1
        device = store.get_all_devices()[0]
        assert device.hit_count == 2
        assert device.signals[0].hit_count == 2

    @pytest.mark.asyncio
    async def test_different_signals_same_device(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Two different codes from the same NEC device address (0x12).
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        await monitor._on_ir_event(_make_event(_nec_event("0x1256")))

        assert store.device_count == 1
        device = store.get_all_devices()[0]
        assert len(device.signals) == 2
        assert device.hit_count == 2

    @pytest.mark.asyncio
    async def test_fires_ha_event(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        hass.bus.async_fire.assert_called_once()
        args = hass.bus.async_fire.call_args
        assert args[0][0] == EVENT_SIGNAL_DETECTED
        summary = args[0][1]
        assert "device_id" in summary
        assert "signal_fingerprint" in summary
        assert summary["protocol"] == "NEC"
        assert summary["code"] == "0x1234"

    @pytest.mark.asyncio
    async def test_notifies_subscribers(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        received = []
        monitor.subscribe(lambda data: received.append(data))

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        assert len(received) == 1
        assert received[0]["protocol"] == "NEC"


# ---------------------------------------------------------------------------
# Known command check
# ---------------------------------------------------------------------------


class TestKnownCommandCheck:

    @pytest.mark.asyncio
    async def test_skips_known_command(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()

        # Set up a known device with a matching command.
        known_device = IRDevice(
            name="TV",
            commands=[IRCommand(name="power", protocol="NEC", code="0x1234")],
        )
        hair_store.get_all_devices.return_value = [known_device]

        monitor = SignalMonitor(hass, store, hair_store)
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        assert store.device_count == 0

    @pytest.mark.asyncio
    async def test_does_not_skip_unknown_command(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()

        known_device = IRDevice(
            name="TV",
            commands=[IRCommand(name="power", protocol="NEC", code="0x5678")],
        )
        hair_store.get_all_devices.return_value = [known_device]

        monitor = SignalMonitor(hass, store, hair_store)
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        assert store.device_count == 1

    @pytest.mark.asyncio
    async def test_raw_signal_not_checked_against_known(self):
        """Raw-only signals have no protocol/code so can't match known commands."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_raw_event()))
        assert store.device_count == 1


# ---------------------------------------------------------------------------
# Dismiss list
# ---------------------------------------------------------------------------


class TestDismissCheck:

    @pytest.mark.asyncio
    async def test_dismissed_device_skipped(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # First, let a signal create a device.
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        assert store.device_count == 1

        device = store.get_all_devices()[0]
        monitor.dismiss_device(device.id)

        # Clear repeat suppression.
        monitor._last_seen_times.clear()

        # New signal from the same device should be skipped.
        await monitor._on_ir_event(_make_event(_nec_event("0x1256")))
        # Device should still have only 1 signal.
        device = store.get_device(device.id)
        assert device.hit_count == 1

    @pytest.mark.asyncio
    async def test_undismiss_allows_events_again(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        device = store.get_all_devices()[0]
        monitor.dismiss_device(device.id)
        monitor.undismiss_device(device.id)

        monitor._last_seen_times.clear()
        await monitor._on_ir_event(_make_event(_nec_event("0x1256")))

        device = store.get_device(device.id)
        assert device.hit_count == 2


# ---------------------------------------------------------------------------
# Dismiss-activity bus event push
#
# Step 4 of ``_process_parsed_signal`` early-returns when a signal arrives
# from a dismissed device, but it also fires an ``EVENT_DISMISS_ACTIVITY``
# bus event (rate-limited) so the Sniffer's "Show Dismissed" button can
# glow and surface a dot indicator. The signal itself stays out of the
# live feed -- only the bus event fires.
# ---------------------------------------------------------------------------


def _dismiss_event_fires(hass) -> list[tuple[str, dict]]:
    """Return all ``EVENT_DISMISS_ACTIVITY`` fire calls recorded on the bus."""
    return [
        call.args
        for call in hass.bus.async_fire.call_args_list
        if call.args and call.args[0] == EVENT_DISMISS_ACTIVITY
    ]


class TestDismissActivityPush:

    @pytest.mark.asyncio
    async def test_dismissed_signal_fires_activity_event(self):
        """A signal from a dismissed device fires the activity bus event."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Create and dismiss a device.
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        device = store.get_all_devices()[0]
        dev_fp = device.fingerprint
        monitor.dismiss_device(device.id)
        monitor._last_seen_times.clear()
        hass.bus.async_fire.reset_mock()

        # New signal from the same (now dismissed) device.
        await monitor._on_ir_event(_make_event(_nec_event("0x1256")))

        fires = _dismiss_event_fires(hass)
        assert len(fires) == 1
        event_name, payload = fires[0]
        assert event_name == EVENT_DISMISS_ACTIVITY
        assert payload == {"device_fingerprint": dev_fp}

    @pytest.mark.asyncio
    async def test_non_dismissed_signal_does_not_fire_activity_event(self):
        """A signal from a NON-dismissed device must not fire the event."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        # No dismiss. Send another signal.
        monitor._last_seen_times.clear()
        hass.bus.async_fire.reset_mock()
        await monitor._on_ir_event(_make_event(_nec_event("0x1256")))

        assert _dismiss_event_fires(hass) == []

    @pytest.mark.asyncio
    async def test_dismissed_signal_does_not_reach_storage(self):
        """Activity event is informational only; signal is still dropped."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        device = store.get_all_devices()[0]
        monitor.dismiss_device(device.id)
        monitor._last_seen_times.clear()

        await monitor._on_ir_event(_make_event(_nec_event("0x1256")))

        # Device still has only its original signal -- the dismissed
        # second arrival did not add a new one or bump the hit_count.
        device = store.get_device(device.id)
        assert device.hit_count == 1

    @pytest.mark.asyncio
    async def test_dismissed_activity_rate_limited(self):
        """Held-down dismissed button does not flood the bus."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        device = store.get_all_devices()[0]
        monitor.dismiss_device(device.id)
        monitor._last_seen_times.clear()
        hass.bus.async_fire.reset_mock()

        # Blast well past the push budget.
        for _ in range(SIGNAL_WS_PUSH_RATE_LIMIT + 10):
            monitor._last_seen_times.clear()
            await monitor._on_ir_event(_make_event(_nec_event("0x1256")))

        # Capped at the WS push budget.
        assert len(_dismiss_event_fires(hass)) <= SIGNAL_WS_PUSH_RATE_LIMIT

    def test_dismiss_push_rate_window_expires(self):
        """Dismiss-push bucket empties after the sliding window."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Fill the dismiss-push bucket.
        for _ in range(SIGNAL_WS_PUSH_RATE_LIMIT):
            assert monitor._check_dismiss_push_rate("dev_fp_1")

        # Should be blocked now.
        assert not monitor._check_dismiss_push_rate("dev_fp_1")

        # Push the bucket's timestamps past the 1-second window.
        monitor._dismiss_push_buckets["dev_fp_1"] = [
            time.monotonic() - 2.0
        ] * SIGNAL_WS_PUSH_RATE_LIMIT

        # Window expired -- should accept again.
        assert monitor._check_dismiss_push_rate("dev_fp_1")

    def test_dismiss_push_per_fingerprint_isolation(self):
        """Each device fingerprint has its own dismiss-push budget."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        for _ in range(SIGNAL_WS_PUSH_RATE_LIMIT):
            assert monitor._check_dismiss_push_rate("dev_fp_A")
        # A is exhausted.
        assert not monitor._check_dismiss_push_rate("dev_fp_A")

        # B starts fresh.
        assert monitor._check_dismiss_push_rate("dev_fp_B")


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:

    @pytest.mark.asyncio
    async def test_rate_limit_drops_excess(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Blast more than SIGNAL_RATE_LIMIT_PER_SEC events.
        for _ in range(SIGNAL_RATE_LIMIT_PER_SEC + 5):
            monitor._last_seen_times.clear()
            await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        device = store.get_all_devices()[0]
        # Should be capped at the rate limit.
        assert device.hit_count <= SIGNAL_RATE_LIMIT_PER_SEC

    def test_rate_limit_window_expires(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Fill the bucket.
        for _ in range(SIGNAL_RATE_LIMIT_PER_SEC):
            assert monitor._check_rate_limit("fp1")

        # Should be blocked now.
        assert not monitor._check_rate_limit("fp1")

        # Simulate time passing (clear the bucket manually).
        monitor._rate_buckets["fp1"] = [
            time.monotonic() - 2.0
        ] * SIGNAL_RATE_LIMIT_PER_SEC

        # Should pass again after old entries expire.
        assert monitor._check_rate_limit("fp1")


# ---------------------------------------------------------------------------
# Repeat suppression
# ---------------------------------------------------------------------------


class TestRepeatSuppression:

    @pytest.mark.asyncio
    async def test_repeat_within_window_suppressed(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # First event goes through.
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        assert store.get_all_devices()[0].hit_count == 1

        # Immediate repeat should be suppressed.
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        assert store.get_all_devices()[0].hit_count == 1

    def test_repeat_check_passes_after_window(self):
        hass = _make_hass()
        monitor = SignalMonitor(hass, _make_signal_store(hass), _make_hair_store())

        assert monitor._check_repeat("fp1")
        assert not monitor._check_repeat("fp1")

        # Simulate time beyond suppression window.
        monitor._last_seen_times["fp1"] = (
            time.monotonic() - (SIGNAL_REPEAT_SUPPRESS_MS / 1000.0) - 0.01
        )
        assert monitor._check_repeat("fp1")

    def test_different_fingerprints_not_suppressed(self):
        hass = _make_hass()
        monitor = SignalMonitor(hass, _make_signal_store(hass), _make_hair_store())

        assert monitor._check_repeat("fp1")
        assert monitor._check_repeat("fp2")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class TestPublicAPI:

    def test_get_unknown_devices_sorted_by_hits(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        d1 = UnknownDevice(id="d1", fingerprint="fp1", hit_count=5)
        d2 = UnknownDevice(id="d2", fingerprint="fp2", hit_count=20)
        d3 = UnknownDevice(id="d3", fingerprint="fp3", hit_count=10)
        store.add_device(d1)
        store.add_device(d2)
        store.add_device(d3)

        result = monitor.get_unknown_devices(min_hits=0)
        assert [d.id for d in result] == ["d2", "d3", "d1"]

    def test_get_unknown_devices_filters_dismissed(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        d1 = UnknownDevice(id="d1", fingerprint="fp1", hit_count=10)
        d2 = UnknownDevice(id="d2", fingerprint="fp2", hit_count=5, dismissed=True)
        store.add_device(d1)
        store.add_device(d2)

        result = monitor.get_unknown_devices(min_hits=0)
        assert len(result) == 1
        assert result[0].id == "d1"

        # With include_dismissed.
        result = monitor.get_unknown_devices(include_dismissed=True, min_hits=0)
        assert len(result) == 2

    def test_get_unknown_devices_min_hits_default(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        d1 = UnknownDevice(id="d1", fingerprint="fp1", hit_count=1)
        d2 = UnknownDevice(id="d2", fingerprint="fp2", hit_count=SIGNAL_CLUSTER_THRESHOLD)
        store.add_device(d1)
        store.add_device(d2)

        # Default min_hits = SIGNAL_CLUSTER_THRESHOLD.
        result = monitor.get_unknown_devices()
        assert len(result) == 1
        assert result[0].id == "d2"

    def test_get_unknown_device(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        d = UnknownDevice(id="d1", fingerprint="fp1")
        store.add_device(d)

        assert monitor.get_unknown_device("d1") is d
        assert monitor.get_unknown_device("nonexistent") is None

    def test_dismiss_device(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        d = UnknownDevice(id="d1", fingerprint="fp1", hit_count=5)
        store.add_device(d)

        assert monitor.dismiss_device("d1")
        assert d.dismissed
        assert store.is_dismissed("fp1")

    def test_dismiss_nonexistent_returns_false(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        assert not monitor.dismiss_device("nope")

    def test_undismiss_device(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        d = UnknownDevice(id="d1", fingerprint="fp1", hit_count=5)
        store.add_device(d)
        monitor.dismiss_device("d1")
        assert monitor.undismiss_device("d1")
        assert not d.dismissed
        assert not store.is_dismissed("fp1")

    def test_clear_all(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        store.add_device(UnknownDevice(id="d1", fingerprint="fp1"))
        monitor.clear_all()
        assert store.device_count == 0


# ---------------------------------------------------------------------------
# Assign signal
# ---------------------------------------------------------------------------


class TestAssignSignal:

    @pytest.mark.asyncio
    async def test_assign_creates_command_and_removes_signal(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        monitor = SignalMonitor(hass, store, hair_store)

        # Set up an unknown device with a signal.
        sig = UnknownSignal(
            fingerprint="sig_fp", protocol="NEC", code="0x1234",
            frequency=38000, hit_count=5,
        )
        device = UnknownDevice(
            id="ud1", fingerprint="dev_fp", signals=[sig], hit_count=5,
        )
        store.add_device(device)

        # Set up target HAIR device.
        hair_device = IRDevice(id="hd1", name="TV")
        hair_store.get_device.return_value = hair_device

        result = await monitor.assign_signal(
            "ud1", "sig_fp", "hd1", "Power", "custom",
        )
        assert result["success"] is True
        assert "command_id" in result
        assert len(hair_device.commands) == 1
        assert hair_device.commands[0].name == "Power"
        assert hair_device.commands[0].protocol == "NEC"
        assert hair_device.commands[0].code == "0x1234"
        # Unknown device should be removed (no signals left).
        assert store.get_device("ud1") is None

    @pytest.mark.asyncio
    async def test_assign_keeps_device_with_remaining_signals(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        monitor = SignalMonitor(hass, store, hair_store)

        sig1 = UnknownSignal(fingerprint="sig1", protocol="NEC", code="0x1234")
        sig2 = UnknownSignal(fingerprint="sig2", protocol="NEC", code="0x5678")
        device = UnknownDevice(
            id="ud1", fingerprint="dev_fp", signals=[sig1, sig2],
        )
        store.add_device(device)

        hair_device = IRDevice(id="hd1", name="TV")
        hair_store.get_device.return_value = hair_device

        result = await monitor.assign_signal(
            "ud1", "sig1", "hd1", "Power", "custom",
        )
        assert result["success"] is True
        # Device should still exist with 1 signal.
        remaining = store.get_device("ud1")
        assert remaining is not None
        assert len(remaining.signals) == 1
        assert remaining.signals[0].fingerprint == "sig2"

    @pytest.mark.asyncio
    async def test_assign_unknown_device_not_found(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        result = await monitor.assign_signal(
            "nope", "sig", "hd1", "Power", "custom",
        )
        assert result["success"] is False
        assert result["code"] == "device_not_found"

    @pytest.mark.asyncio
    async def test_assign_signal_not_found(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        device = UnknownDevice(id="ud1", fingerprint="dev_fp")
        store.add_device(device)

        result = await monitor.assign_signal(
            "ud1", "nonexistent", "hd1", "Power", "custom",
        )
        assert result["success"] is False
        assert result["code"] == "signal_not_found"

    @pytest.mark.asyncio
    async def test_assign_hair_device_not_found(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        monitor = SignalMonitor(hass, store, hair_store)

        sig = UnknownSignal(fingerprint="sig_fp", protocol="NEC", code="0x1234")
        device = UnknownDevice(id="ud1", fingerprint="dev_fp", signals=[sig])
        store.add_device(device)

        # hair_store.get_device returns None by default.
        result = await monitor.assign_signal(
            "ud1", "sig_fp", "hd1", "Power", "custom",
        )
        assert result["success"] is False
        assert result["code"] == "target_not_found"


# ---------------------------------------------------------------------------
# Test signal
# ---------------------------------------------------------------------------


class TestTestSignal:

    @pytest.mark.asyncio
    async def test_sends_decoded_signal(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        sig = UnknownSignal(
            fingerprint="sig_fp", protocol="NEC", code="0x1234",
            raw_timings=[9000, -4500, 560, -560],
        )
        device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
        store.add_device(device)

        mock_ir_send = AsyncMock()
        import sys
        ir_mod = sys.modules["homeassistant.components.infrared"]
        orig = ir_mod.async_send_command
        ir_mod.async_send_command = mock_ir_send
        try:
            result = await monitor.test_signal("sig_fp", "remote.ir_blaster")
        finally:
            ir_mod.async_send_command = orig
        assert result["success"] is True
        mock_ir_send.assert_awaited_once()
        call_args = mock_ir_send.call_args
        assert call_args[0][0] is hass
        assert call_args[0][1] == "remote.ir_blaster"
        assert hasattr(call_args[0][2], "get_raw_timings")

    @pytest.mark.asyncio
    async def test_signal_not_found_returns_false(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        result = await monitor.test_signal("nonexistent", "remote.ir_blaster")
        assert result["success"] is False
        assert result["code"] == "signal_not_found"


# ---------------------------------------------------------------------------
# Subscriber management
# ---------------------------------------------------------------------------


class TestSubscribers:

    def test_subscribe_and_unsubscribe(self):
        hass = _make_hass()
        monitor = SignalMonitor(hass, _make_signal_store(hass), _make_hair_store())

        cb = MagicMock()
        monitor.subscribe(cb)
        assert cb in monitor._subscribers

        monitor.unsubscribe(cb)
        assert cb not in monitor._subscribers

    def test_unsubscribe_nonexistent_safe(self):
        hass = _make_hass()
        monitor = SignalMonitor(hass, _make_signal_store(hass), _make_hair_store())
        monitor.unsubscribe(MagicMock())  # Should not raise.

    def test_duplicate_subscribe_ignored(self):
        hass = _make_hass()
        monitor = SignalMonitor(hass, _make_signal_store(hass), _make_hair_store())

        cb = MagicMock()
        monitor.subscribe(cb)
        monitor.subscribe(cb)
        assert monitor._subscribers.count(cb) == 1

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_break_processing(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        bad_cb = MagicMock(side_effect=RuntimeError("boom"))
        good_cb = MagicMock()
        monitor.subscribe(bad_cb)
        monitor.subscribe(good_cb)

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        bad_cb.assert_called_once()
        good_cb.assert_called_once()


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------


class TestAssignIdempotency:

    @pytest.mark.asyncio
    async def test_duplicate_signal_rejected(self):
        """Assigning the same protocol+code to a device twice is rejected."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        monitor = SignalMonitor(hass, store, hair_store)

        sig = UnknownSignal(
            fingerprint="sig_fp", protocol="NEC", code="0x1234",
            frequency=38000, hit_count=5,
        )
        device = UnknownDevice(
            id="ud1", fingerprint="dev_fp", signals=[sig], hit_count=5,
        )
        store.add_device(device)

        # Target device already has a command with same protocol+code.
        existing_cmd = IRCommand(
            name="Existing", protocol="NEC", code="0x1234",
        )
        hair_device = IRDevice(id="hd1", name="TV", commands=[existing_cmd])
        hair_store.get_device.return_value = hair_device

        result = await monitor.assign_signal(
            "ud1", "sig_fp", "hd1", "Power", "custom",
        )
        assert result["success"] is False
        assert result["code"] == "duplicate_signal"
        # Signal should NOT have been removed.
        assert store.get_device("ud1") is not None
        assert len(store.get_device("ud1").signals) == 1


# ---------------------------------------------------------------------------
# Delete signal
# ---------------------------------------------------------------------------


class TestDeleteSignal:

    @pytest.mark.asyncio
    async def test_delete_removes_signal_and_fires_event(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        sig1 = UnknownSignal(fingerprint="sig1", protocol="NEC", code="0x1")
        sig2 = UnknownSignal(fingerprint="sig2", protocol="NEC", code="0x2")
        device = UnknownDevice(
            id="ud1", fingerprint="fp", signals=[sig1, sig2],
        )
        store.add_device(device)

        result = await monitor.delete_signal("ud1", "sig1")
        assert result["success"] is True
        assert result["device_removed"] is False

        # Signal removed, device still exists.
        remaining = store.get_device("ud1")
        assert remaining is not None
        assert len(remaining.signals) == 1
        assert remaining.signals[0].fingerprint == "sig2"

        # Event bus fired.
        hass.bus.async_fire.assert_called()
        fire_args = hass.bus.async_fire.call_args
        assert fire_args[0][0] == "hair_signal_removed"
        assert fire_args[0][1]["signal_fingerprint"] == "sig1"

    @pytest.mark.asyncio
    async def test_delete_last_signal_removes_device(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        sig = UnknownSignal(fingerprint="sig1", protocol="NEC", code="0x1")
        device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
        store.add_device(device)

        result = await monitor.delete_signal("ud1", "sig1")
        assert result["success"] is True
        assert result["device_removed"] is True
        assert store.get_device("ud1") is None

    @pytest.mark.asyncio
    async def test_delete_device_not_found(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        result = await monitor.delete_signal("nope", "sig")
        assert result["success"] is False
        assert result["code"] == "device_not_found"

    @pytest.mark.asyncio
    async def test_delete_signal_not_found(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        device = UnknownDevice(id="ud1", fingerprint="fp")
        store.add_device(device)

        result = await monitor.delete_signal("ud1", "nonexistent")
        assert result["success"] is False
        assert result["code"] == "signal_not_found"


# ---------------------------------------------------------------------------
# Assign to new device
# ---------------------------------------------------------------------------


class TestAssignToNewDevice:

    @pytest.mark.asyncio
    async def test_creates_device_and_assigns(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        monitor = SignalMonitor(hass, store, hair_store)

        sig = UnknownSignal(
            fingerprint="sig_fp", protocol="NEC", code="0x1234",
            frequency=38000, hit_count=5,
        )
        device = UnknownDevice(
            id="ud1", fingerprint="dev_fp", signals=[sig], hit_count=5,
        )
        store.add_device(device)

        result = await monitor.assign_to_new_device(
            device_id="ud1",
            signal_fingerprint="sig_fp",
            device_name="Living Room TV",
            device_type="media_player",
            emitter_entity_ids=["remote.ir_blaster"],
            command_name="Power",
            command_category="power",
        )
        assert result["success"] is True
        assert "device_id" in result
        assert "command_id" in result
        assert result["device"].name == "Living Room TV"
        assert len(result["device"].commands) == 1
        assert result["device"].commands[0].name == "Power"

        # Signal should be removed.
        assert store.get_device("ud1") is None

        # HAIRStore should have been saved.
        hair_store.async_save.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_device_type(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        sig = UnknownSignal(fingerprint="sig_fp", protocol="NEC", code="0x1")
        device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
        store.add_device(device)

        result = await monitor.assign_to_new_device(
            "ud1", "sig_fp", "Test", "invalid_type",
            "remote.ir", "Power", "power",
        )
        assert result["success"] is False
        assert result["code"] == "invalid_device_type"

    @pytest.mark.asyncio
    async def test_rollback_on_hair_store_failure(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        hair_store.async_save = AsyncMock(side_effect=OSError("disk full"))
        monitor = SignalMonitor(hass, store, hair_store)

        sig = UnknownSignal(fingerprint="sig_fp", protocol="NEC", code="0x1")
        device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
        store.add_device(device)

        result = await monitor.assign_to_new_device(
            "ud1", "sig_fp", "Test", "media_player",
            "remote.ir", "Power", "power",
        )
        assert result["success"] is False
        assert result["code"] == "save_failed"
        # Signal should still exist.
        assert store.get_device("ud1") is not None
        assert len(store.get_device("ud1").signals) == 1


# ---------------------------------------------------------------------------
# Test signal - structured errors
# ---------------------------------------------------------------------------


class TestTestSignalErrors:

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        hass = _make_hass()
        hass.states.get.return_value = None  # Entity doesn't exist.
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        result = await monitor.test_signal("sig_fp", "remote.nonexistent")
        assert result["success"] is False
        assert result["code"] == "entity_not_found"

    @pytest.mark.asyncio
    async def test_send_timeout(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        sig = UnknownSignal(
            fingerprint="sig_fp", protocol="NEC", code="0x1234",
            raw_timings=[9000, -4500, 560, -560],
        )
        device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
        store.add_device(device)

        # Make the ir_send call hang.
        async def _hang(*a, **kw):
            await asyncio.sleep(999)

        # Patch timeout to 0.1s so test doesn't wait 10s.
        import sys
        ir_mod = sys.modules["homeassistant.components.infrared"]
        orig = ir_mod.async_send_command
        ir_mod.async_send_command = _hang
        try:
            with patch(
                "custom_components.hair.signal_monitor.ASSIGN_SERVICE_TIMEOUT_S",
                0.1,
            ):
                result = await monitor.test_signal("sig_fp", "remote.ir_blaster")
        finally:
            ir_mod.async_send_command = orig
        assert result["success"] is False
        assert result["code"] == "send_timeout"

    @pytest.mark.asyncio
    async def test_send_failed(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        sig = UnknownSignal(
            fingerprint="sig_fp", protocol="NEC", code="0x1234",
            raw_timings=[9000, -4500, 560, -560],
        )
        device = UnknownDevice(id="ud1", fingerprint="fp", signals=[sig])
        store.add_device(device)

        import sys
        ir_mod = sys.modules["homeassistant.components.infrared"]
        orig = ir_mod.async_send_command
        ir_mod.async_send_command = AsyncMock(side_effect=RuntimeError("hardware error"))
        try:
            result = await monitor.test_signal("sig_fp", "remote.ir_blaster")
        finally:
            ir_mod.async_send_command = orig
        assert result["success"] is False
        assert result["code"] == "send_failed"


# ---------------------------------------------------------------------------
# Native receiver path (HA 2026.6+)
# ---------------------------------------------------------------------------


class _FakeTiming:
    """Minimal stand-in for ``infrared_protocols.Timing``."""

    def __init__(self, high_us: int, low_us: int) -> None:
        self.high_us = high_us
        self.low_us = low_us


class _FakeReceivedSignal:
    """Minimal stand-in for ``InfraredReceivedSignal``."""

    def __init__(
        self,
        timings: list[_FakeTiming],
        modulation: int = 38000,
    ) -> None:
        self.timings = timings
        self.modulation = modulation


class TestNativeReceiverLifecycle:
    """Tests for the native ``InfraredReceiverEntity`` subscription path."""

    @pytest.mark.asyncio
    async def test_native_mode_activates_when_api_available(self):
        """When async_subscribe_receiver is importable, native mode activates."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        mock_unsub = MagicMock()

        def fake_get_receivers(_hass):
            return ["infrared.living_room_rx"]

        def fake_subscribe(_hass, entity_id, callback):
            return mock_unsub

        with patch(
            "custom_components.hair.signal_monitor.SignalMonitor"
            "._start_native_receivers",
            wraps=monitor._start_native_receivers,
        ), patch.dict(
            "sys.modules",
            {
                "homeassistant.components.infrared": MagicMock(
                    async_get_receivers=fake_get_receivers,
                    async_subscribe_receiver=fake_subscribe,
                ),
            },
        ):
            await monitor._start_native_receivers()

        assert monitor.native_mode
        assert len(monitor._unsubs) == 1

    @pytest.mark.asyncio
    async def test_native_no_receivers_falls_back(self):
        """If native API exists but no receivers found, falls back to legacy."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        def fake_get_receivers(_hass):
            return []

        with patch.dict(
            "sys.modules",
            {
                "homeassistant.components.infrared": MagicMock(
                    async_get_receivers=fake_get_receivers,
                ),
            },
        ):
            await monitor._start_native_receivers()

        # Should have fallen back to legacy.
        assert not monitor.native_mode
        hass.bus.async_listen.assert_called_once()

    @pytest.mark.asyncio
    async def test_native_stop_cleans_up_all_unsubs(self):
        """async_stop() should call all native unsubs."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        unsub1 = MagicMock()
        unsub2 = MagicMock()
        monitor._unsubs = [unsub1, unsub2]
        monitor._native_mode = True

        await monitor.async_stop()

        unsub1.assert_called_once()
        unsub2.assert_called_once()
        assert len(monitor._unsubs) == 0


async def _run_native_signal(monitor, hass, signal):
    """Invoke the sync native callback and drain the scheduled async pipeline.

    ``_on_received_signal`` is a sync ``@callback`` (per the 2026.6 API).
    It schedules ``_process_parsed_signal`` via ``hass.async_create_task``.
    The test ``_make_hass`` passes that coroutine through unchanged, so
    we can await it here to actually run the processing pipeline.
    """
    monitor._on_received_signal(signal)
    if hass.async_create_task.called:
        coro = hass.async_create_task.call_args[0][0]
        if hasattr(coro, "__await__"):
            await coro
        hass.async_create_task.reset_mock()


class TestNativeSignalProcessing:
    """Tests for _on_received_signal processing path."""

    @pytest.mark.asyncio
    async def test_native_signal_creates_device_and_signal(self):
        """A native signal should create an unknown device and signal."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Native API delivers timings as list[int] (signed microseconds).
        # 8 ints exceeds the repeat threshold (<= 6).
        signal = _FakeReceivedSignal(
            timings=[9000, -4500, 560, -560, 560, -1690, 560, -560],
            modulation=38000,
        )

        await _run_native_signal(monitor, hass, signal)

        assert store.device_count == 1
        devices = store.get_all_devices()
        assert len(devices) == 1
        assert devices[0].hit_count == 1
        assert len(devices[0].signals) == 1
        # Signal should be stored as PRONTO protocol.
        assert devices[0].signals[0].protocol == "PRONTO"

    @pytest.mark.asyncio
    async def test_native_repeat_frame_filtered(self):
        """Short signals (<=3 timing pairs) should be filtered as repeats."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Only 4 raw values (<= 6 threshold) -- repeat frame.
        signal = _FakeReceivedSignal(
            timings=[9000, -2250, 560, -560],
            modulation=38000,
        )

        await _run_native_signal(monitor, hass, signal)
        assert store.device_count == 0

    @pytest.mark.asyncio
    async def test_native_signal_fires_ha_event(self):
        """Native path should fire hair_signal_detected event."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        # Native API delivers timings as list[int] (signed microseconds).
        # 8 ints exceeds the repeat threshold (<= 6).
        signal = _FakeReceivedSignal(
            timings=[9000, -4500, 560, -560, 560, -1690, 560, -560],
            modulation=38000,
        )

        await _run_native_signal(monitor, hass, signal)

        hass.bus.async_fire.assert_called_once()
        args = hass.bus.async_fire.call_args
        assert args[0][0] == EVENT_SIGNAL_DETECTED

    @pytest.mark.asyncio
    async def test_native_signal_notifies_subscribers(self):
        """Native path should notify WebSocket subscribers."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = SignalMonitor(hass, store, _make_hair_store())

        received = []
        monitor.subscribe(lambda data: received.append(data))

        # Native API delivers timings as list[int] (signed microseconds).
        # 8 ints exceeds the repeat threshold (<= 6).
        signal = _FakeReceivedSignal(
            timings=[9000, -4500, 560, -560, 560, -1690, 560, -560],
            modulation=38000,
        )

        await _run_native_signal(monitor, hass, signal)
        assert len(received) == 1
        assert "signal_fingerprint" in received[0]
