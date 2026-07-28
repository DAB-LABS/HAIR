"""Tests for dynamic receiver tracking (v0.5.8 receiver hot-plug).

Covers the test list from
``docs/internal/community-feedback/forum-blalor-receiver-hotplug.md``:
a receiver appearing after startup is subscribed with no reload
(blalor's hot-plug report); zero receivers at setup stays native
instead of latching the legacy bus (the post-#85 cold-boot race);
removal releases cleanly; reconcile is idempotent; the started-once
re-scan is guarded; a failing subscribe skips that entity without
latching legacy; per-receiver ditto state is purged on release; and the
hot-plugged callback threads its own receiver id (late-binding
preserved).

The ghost-receiver heal (config entry reload replaces the entity
OBJECT under the same entity_id) is covered by TestAvailabilityHeal:
hardware testing on HA 2026.7.2 proved that entry reloads NEVER fire
the domain add/remove trackers -- registry-registered entities keep an
``unavailable`` state placeholder across unload -- so the heal rides
the unavailable/available transitions instead, exactly like HA core's
own ``InfraredReceiverConsumerEntity``.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.signal_monitor import SignalMonitor

from .test_signal_monitor import (
    _make_hair_store,
    _make_hass,
    _make_signal_store,
)


class _FakeInfrared:
    """Controllable stand-in for homeassistant.components.infrared.

    ``receivers`` is mutable so tests can hot-plug and remove entities
    between reconciles. Subscriptions are recorded per entity_id; each
    subscribe hands back a fresh unsub MagicMock so release can be
    asserted per-handle.
    """

    def __init__(self, receivers=None):
        self.receivers = list(receivers or [])
        self.subscriptions: list[tuple[str, object]] = []
        self.unsubs: dict[str, list[MagicMock]] = {}
        self.fail_for: set[str] = set()

    def module(self) -> MagicMock:
        return MagicMock(
            async_get_receivers=lambda _hass: list(self.receivers),
            async_subscribe_receiver=self._subscribe,
        )

    def _subscribe(self, _hass, entity_id, callback):
        if entity_id in self.fail_for:
            raise RuntimeError(f"entity {entity_id} not ready")
        self.subscriptions.append((entity_id, callback))
        unsub = MagicMock()
        self.unsubs.setdefault(entity_id, []).append(unsub)
        return unsub


def _monitor(hass):
    return SignalMonitor(hass, _make_signal_store(hass), _make_hair_store())


def _state_event(entity_id, new_state):
    """Build a fake state_changed event; new_state None = removed."""
    event = MagicMock()
    ns = None
    if new_state is not None:
        ns = MagicMock()
        ns.state = new_state
    event.data = {"entity_id": entity_id, "new_state": ns}
    return event


def _patched(fake: _FakeInfrared):
    return patch.dict(
        "sys.modules",
        {"homeassistant.components.infrared": fake.module()},
    )


# ---------------------------------------------------------------------------
# Hot-plug: receiver appears after start (blalor's new report)
# ---------------------------------------------------------------------------


class TestHotPlug:
    def test_receiver_added_after_start_gets_subscribed(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=[])

        with _patched(fake):
            monitor._start_native_tracking()
            assert monitor._receiver_subs == {}
            assert monitor.has_receivers is False

            # The proxy comes online later; the added-domain tracker fires.
            fake.receivers.append("infrared.new_proxy_rx")
            event = MagicMock()
            event.data = {"entity_id": "infrared.new_proxy_rx"}
            monitor._on_infrared_entity_added(event)

        assert set(monitor._receiver_subs) == {"infrared.new_proxy_rx"}
        assert monitor.has_receivers is True

    def test_hotplugged_callback_threads_its_own_receiver_id(self):
        """Late-binding idiom preserved under reconcile: each receiver's
        callback carries its OWN entity_id into _on_received_signal."""
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx_a"])

        with _patched(fake):
            monitor._start_native_tracking()
            fake.receivers.append("infrared.rx_b")
            monitor._reconcile_receivers()

        seen: list[str] = []
        monitor._on_received_signal = lambda sig, rid: seen.append(rid)
        for _entity_id, callback in fake.subscriptions:
            callback(MagicMock())
        assert seen == ["infrared.rx_a", "infrared.rx_b"]

    def test_added_event_for_emitter_only_entity_subscribes_nothing(self):
        """The domain trackers fire for emitters too (Tuya, Tweezer);
        reconcile filters through async_get_receivers."""
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=[])

        with _patched(fake):
            monitor._start_native_tracking()
            event = MagicMock()
            event.data = {"entity_id": "infrared.some_emitter_tx"}
            monitor._on_infrared_entity_added(event)

        assert monitor._receiver_subs == {}


# ---------------------------------------------------------------------------
# Cold-boot race: zero receivers must not latch legacy (post #85)
# ---------------------------------------------------------------------------


class TestNoLegacyLatch:
    @pytest.mark.asyncio
    async def test_zero_receivers_at_setup_then_late_arrival_works(self):
        hass = _make_hass()
        hass.state = MagicMock()  # not CoreState.running
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=[])

        with _patched(fake):
            await monitor.async_start()

            assert monitor.native_mode is True
            # The legacy processing path must not be wired: the only bus
            # listeners allowed are bridge tracking (async_listen) and the
            # started-once re-scan (async_listen_once).
            for call in hass.bus.async_listen.call_args_list:
                assert call.args[1] != monitor._on_ir_event

            # ESPHome finishes registering after HA starts; the re-scan
            # picks the receiver up with no reload.
            fake.receivers.append("infrared.cold_boot_rx")
            monitor._on_hass_started(MagicMock())

        assert set(monitor._receiver_subs) == {"infrared.cold_boot_rx"}

    @pytest.mark.asyncio
    async def test_import_error_still_selects_legacy(self):
        """Regression: HA 2026.4-2026.5 (no native API) keeps the legacy
        event-bus path, selected by capability, not inventory."""
        hass = _make_hass()
        monitor = _monitor(hass)

        real_import = __import__

        def _no_infrared(name, *args, **kwargs):
            if name == "homeassistant.components.infrared":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch.dict("sys.modules"), patch(
            "builtins.__import__", side_effect=_no_infrared
        ):
            import sys

            sys.modules.pop("homeassistant.components.infrared", None)
            await monitor.async_start()

        assert monitor.native_mode is False
        listened = [c.args[0] for c in hass.bus.async_listen.call_args_list]
        assert "esphome.remote_received" in listened

    def test_one_bad_entity_skipped_without_latching(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.broken_rx", "infrared.good_rx"])
        fake.fail_for.add("infrared.broken_rx")

        with _patched(fake):
            monitor._start_native_tracking()

        assert monitor.native_mode is True
        assert set(monitor._receiver_subs) == {"infrared.good_rx"}

    @pytest.mark.asyncio
    async def test_bridge_tracking_wired_once_in_zero_receiver_state(self):
        """RX-BRIDGE detection must work while waiting for receivers."""
        hass = _make_hass()
        hass.state = MagicMock()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=[])

        with _patched(fake):
            await monitor.async_start()

        bridge_wires = [
            c
            for c in hass.bus.async_listen.call_args_list
            if c.args[1] == monitor._on_bridge_tracking_event
        ]
        assert len(bridge_wires) == 1


# ---------------------------------------------------------------------------
# Removal, idempotence, teardown
# ---------------------------------------------------------------------------


class TestReleaseAndReconcile:
    def test_removed_receiver_releases_subscription(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            fake.receivers.clear()
            event = MagicMock()
            event.data = {"entity_id": "infrared.rx"}
            monitor._on_infrared_entity_removed(event)

        assert monitor._receiver_subs == {}
        fake.unsubs["infrared.rx"][0].assert_called_once()

    def test_reconcile_is_idempotent(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            monitor._reconcile_receivers()
            monitor._reconcile_receivers()

        assert len(fake.subscriptions) == 1
        assert set(monitor._receiver_subs) == {"infrared.rx"}

    def test_release_purges_per_receiver_state(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            monitor._ditto_anchor["infrared.rx"] = (None, 1.0, None)
            monitor._ditto_running_count["infrared.rx"] = 2
            monitor._last_ditto_monotonic["infrared.rx"] = 1.0
            monitor._last_seen_times[((2, "somehash"), "infrared.rx")] = 1.0
            monitor._last_seen_times[((2, "somehash"), "infrared.other")] = 1.0

            monitor._release_receiver("infrared.rx")

        assert "infrared.rx" not in monitor._ditto_anchor
        assert "infrared.rx" not in monitor._ditto_running_count
        assert "infrared.rx" not in monitor._last_ditto_monotonic
        assert list(monitor._last_seen_times) == [
            ((2, "somehash"), "infrared.other")
        ]

    @pytest.mark.asyncio
    async def test_stop_releases_all_receiver_subs_and_trackers(self):
        hass = _make_hass()
        hass.state = MagicMock()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx_a", "infrared.rx_b"])

        tracker_unsubs = [MagicMock(), MagicMock()]
        with _patched(fake), patch(
            "custom_components.hair.signal_monitor."
            "async_track_state_added_domain",
            return_value=tracker_unsubs[0],
        ), patch(
            "custom_components.hair.signal_monitor."
            "async_track_state_removed_domain",
            return_value=tracker_unsubs[1],
        ):
            await monitor.async_start()
            await monitor.async_stop()

        assert monitor._receiver_subs == {}
        for unsubs in fake.unsubs.values():
            for unsub in unsubs:
                unsub.assert_called_once()
        for unsub in tracker_unsubs:
            unsub.assert_called_once()

    def test_started_once_rescan_guarded_by_core_state(self):
        """Wired only while HA is still starting; a config entry added at
        runtime must not wait on an event that already fired."""
        from custom_components.hair import signal_monitor as sm

        fake = _FakeInfrared(receivers=[])

        # Still starting -> listener wired.
        hass = _make_hass()
        hass.state = MagicMock()
        monitor = _monitor(hass)
        with _patched(fake):
            monitor._start_native_tracking()
        hass.bus.async_listen_once.assert_called_once()

        # Already running -> no listener.
        hass2 = _make_hass()
        hass2.state = sm.CoreState.running
        monitor2 = _monitor(hass2)
        with _patched(fake):
            monitor2._start_native_tracking()
        hass2.bus.async_listen_once.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_after_started_fired_skips_dead_unsubscribe(self):
        """Teardown guard (2026-07-28): a once-listener consumes itself
        at fire time, so calling its stored unsubscribe on stop made HA
        log 'Unable to remove unknown job listener ... _on_hass_started'
        on every normal restart. Fired -> stop must not touch it."""
        hass = _make_hass()
        hass.state = MagicMock()  # still starting -> listener wired
        started_unsub = MagicMock()
        hass.bus.async_listen_once.return_value = started_unsub
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=[])

        with _patched(fake):
            await monitor.async_start()
            monitor._on_hass_started(MagicMock())
            assert monitor._started_unsub is None
            await monitor.async_stop()

        started_unsub.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_before_started_fires_unsubscribes_once(self):
        """The complement: an entry unloaded while HA is still starting
        holds a live once-listener, and stop must release exactly it."""
        hass = _make_hass()
        hass.state = MagicMock()  # still starting -> listener wired
        started_unsub = MagicMock()
        hass.bus.async_listen_once.return_value = started_unsub
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=[])

        with _patched(fake):
            await monitor.async_start()
            await monitor.async_stop()

        started_unsub.assert_called_once()
        assert monitor._started_unsub is None


# ---------------------------------------------------------------------------
# The reload / ghost heal: availability transitions (GH #16 class)
# ---------------------------------------------------------------------------


class TestAvailabilityHeal:
    """Config entry reload on HA 2026.7: the receiver's state is NEVER
    removed -- it flips to 'unavailable' and back while the entity OBJECT
    is replaced (verified live; the domain add/remove trackers never fire
    for reloads). The heal therefore mirrors core's
    InfraredReceiverConsumerEntity: release on unavailable, subscribe
    fresh on available."""

    def test_unavailable_releases_subscription(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            assert set(monitor._receiver_subs) == {"infrared.rx"}
            monitor._on_receiver_availability_change(
                _state_event("infrared.rx", "unavailable")
            )

        assert monitor._receiver_subs == {}
        fake.unsubs["infrared.rx"][0].assert_called_once()

    def test_reload_cycle_resubscribes_fresh(self):
        """unavailable -> available across an entry reload lands a NEW
        subscription (resolving the new entity object); the dead handle
        was already dropped on the unavailable edge."""
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            old_unsub = fake.unsubs["infrared.rx"][0]
            monitor._on_receiver_availability_change(
                _state_event("infrared.rx", "unavailable")
            )
            monitor._on_receiver_availability_change(
                _state_event("infrared.rx", "2026-07-14T06:00:00+00:00")
            )

        old_unsub.assert_called_once()
        assert len(fake.unsubs["infrared.rx"]) == 2
        assert (
            monitor._receiver_subs["infrared.rx"]
            is fake.unsubs["infrared.rx"][1]
        )

    def test_value_update_is_a_cheap_noop(self):
        """Every received signal bumps the receiver's state; a tracked,
        available receiver must not be resubscribed per signal."""
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            for _ in range(5):
                monitor._on_receiver_availability_change(
                    _state_event("infrared.rx", "2026-07-14T06:00:01+00:00")
                )

        assert len(fake.subscriptions) == 1

    def test_reconcile_skips_unavailable_receiver(self):
        """Mirror core: never subscribe while unavailable; the watcher
        brings the receiver in when it comes up."""
        hass = _make_hass()
        unavailable = MagicMock()
        unavailable.state = "unavailable"
        hass.states.get = MagicMock(return_value=unavailable)
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        with _patched(fake):
            monitor._start_native_tracking()
            assert monitor._receiver_subs == {}
            hass.states.get = MagicMock(
                return_value=MagicMock(state="2026-07-14T06:00:02+00:00")
            )
            monitor._on_receiver_availability_change(
                _state_event("infrared.rx", "2026-07-14T06:00:02+00:00")
            )

        assert set(monitor._receiver_subs) == {"infrared.rx"}

    def test_watcher_rewired_per_reconcile(self):
        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        watch_calls = []

        def fake_watch(_hass, ids, action):
            unsub = MagicMock()
            watch_calls.append((list(ids), unsub))
            return unsub

        with _patched(fake), patch(
            "custom_components.hair.signal_monitor."
            "async_track_state_change_event",
            side_effect=fake_watch,
        ):
            monitor._start_native_tracking()
            assert watch_calls[-1][0] == ["infrared.rx"]
            fake.receivers.append("infrared.rx_b")
            monitor._reconcile_receivers()

        watch_calls[0][1].assert_called_once()
        assert watch_calls[-1][0] == ["infrared.rx", "infrared.rx_b"]

    @pytest.mark.asyncio
    async def test_stop_clears_watcher(self):
        hass = _make_hass()
        hass.state = MagicMock()
        monitor = _monitor(hass)
        fake = _FakeInfrared(receivers=["infrared.rx"])

        watcher_unsub = MagicMock()
        with _patched(fake), patch(
            "custom_components.hair.signal_monitor."
            "async_track_state_change_event",
            return_value=watcher_unsub,
        ):
            await monitor.async_start()
            await monitor.async_stop()

        watcher_unsub.assert_called_once()
        assert monitor._receiver_watch_unsub is None
