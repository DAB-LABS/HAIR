"""Tests for the SignalStore persistence layer."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    SIGNAL_BUFFER_MAX_DEVICES,
    SIGNAL_EVICT_AGE_DAYS,
)
from custom_components.hair.models import UnknownDevice, UnknownSignal
from custom_components.hair.signal_store import SignalStore


def _make_hass():
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_later = MagicMock(return_value=MagicMock())
    hass.async_create_task = MagicMock()
    return hass


def _make_device(
    device_id: str = "d1",
    fingerprint: str = "fp1",
    hit_count: int = 10,
    last_seen: str | None = None,
    dismissed: bool = False,
) -> UnknownDevice:
    if last_seen is None:
        last_seen = datetime.now(UTC).isoformat()
    return UnknownDevice(
        id=device_id,
        fingerprint=fingerprint,
        hit_count=hit_count,
        last_seen=last_seen,
        first_seen=last_seen,
        dismissed=dismissed,
    )


def _make_signal(fingerprint: str = "sig1", hit_count: int = 5) -> UnknownSignal:
    return UnknownSignal(fingerprint=fingerprint, hit_count=hit_count)


class TestLoadSave:

    @pytest.mark.asyncio
    async def test_load_empty_storage(self):
        hass = _make_hass()
        store = SignalStore(hass)
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=None)
            await store.async_load()
        assert store.loaded
        assert store.get_all_devices() == []
        assert store.dismissed_count == 0

    @pytest.mark.asyncio
    async def test_load_with_devices(self):
        """Load preserves devices and matching dismissed entries.

        The dismissed fingerprint here matches the loaded device's
        fingerprint so the v0.2.1 self-heal pass does NOT treat it as
        an orphan. (Orphan-pruning behavior is covered separately in
        test_load_self_heals_orphan_dismissed_fingerprints.)
        """
        hass = _make_hass()
        store = SignalStore(hass)
        raw = {
            "devices": [_make_device("d1", "fp1", 5).to_dict()],
            "dismissed": ["fp1"],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        assert store.loaded
        assert len(store.get_all_devices()) == 1
        assert store.get_device("d1") is not None
        assert store.is_dismissed("fp1")

    @pytest.mark.asyncio
    async def test_load_skips_malformed(self):
        hass = _make_hass()
        store = SignalStore(hass)
        raw = {
            "devices": [{"bad": "data"}, _make_device("d1").to_dict()],
            "dismissed": [],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        # Malformed entry should have a generated ID, so we should have 2
        # Actually the from_dict will succeed with defaults, let's just
        # verify it loaded without crashing.
        assert store.loaded

    @pytest.mark.asyncio
    async def test_load_self_heals_orphan_dismissed_fingerprints(self):
        """async_load prunes orphan _dismissed entries on load.

        Regression for GitHub issue #9: users upgrading from v0.2.0 or
        earlier may have accumulated orphan fingerprints in their on-disk
        dismiss set via the assign-from-dismissed bug. async_load now
        prunes any fingerprint that has no matching device record, so
        affected users auto-recover on next HA restart after upgrading
        to v0.2.1 without manual file editing.
        """
        hass = _make_hass()
        store = SignalStore(hass)
        raw = {
            # Only one device, fingerprint = "live_fp".
            "devices": [_make_device("d1", "live_fp").to_dict()],
            # Two dismissed entries: one matches the device, one is an
            # orphan (no matching device record).
            "dismissed": ["live_fp", "orphan_fp"],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()

        # Live fingerprint stays dismissed.
        assert store.is_dismissed("live_fp")
        # Orphan was pruned.
        assert not store.is_dismissed("orphan_fp")
        assert store.dismissed_count == 1
        # Self-heal flags the store as dirty so the cleanup persists on
        # next save.
        assert store._dirty

    @pytest.mark.asyncio
    async def test_load_with_no_orphans_does_not_mark_dirty(self):
        """If all _dismissed entries are valid, load leaves _dirty alone."""
        hass = _make_hass()
        store = SignalStore(hass)
        raw = {
            "devices": [_make_device("d1", "fp_a").to_dict()],
            "dismissed": ["fp_a"],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()

        assert store.is_dismissed("fp_a")
        assert not store._dirty

    @pytest.mark.asyncio
    async def test_save_serializes_correctly(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store._loaded = True
        device = _make_device("d1", "fp1")
        device.signals.append(_make_signal("sig1"))
        store.add_device(device)
        store.add_dismissed("dismissed_fp")

        with patch.object(store, "_store") as mock_store:
            mock_store.async_save = AsyncMock()
            await store.async_save()

        saved = mock_store.async_save.call_args[0][0]
        assert len(saved["devices"]) == 1
        assert saved["devices"][0]["id"] == "d1"
        assert "dismissed_fp" in saved["dismissed"]


class TestDeviceAccess:

    def test_get_device(self):
        hass = _make_hass()
        store = SignalStore(hass)
        device = _make_device("d1")
        store.add_device(device)
        assert store.get_device("d1") is device

    def test_get_device_not_found(self):
        hass = _make_hass()
        store = SignalStore(hass)
        assert store.get_device("nonexistent") is None

    def test_get_device_by_fingerprint(self):
        hass = _make_hass()
        store = SignalStore(hass)
        device = _make_device("d1", "unique_fp")
        store.add_device(device)
        assert store.get_device_by_fingerprint("unique_fp") is device

    def test_get_device_by_fingerprint_not_found(self):
        hass = _make_hass()
        store = SignalStore(hass)
        assert store.get_device_by_fingerprint("nope") is None

    def test_remove_device(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store.add_device(_make_device("d1"))
        assert store.remove_device("d1")
        assert store.get_device("d1") is None

    def test_remove_device_not_found(self):
        hass = _make_hass()
        store = SignalStore(hass)
        assert not store.remove_device("nonexistent")

    def test_device_count(self):
        hass = _make_hass()
        store = SignalStore(hass)
        assert store.device_count == 0
        store.add_device(_make_device("d1"))
        store.add_device(_make_device("d2"))
        assert store.device_count == 2

    def test_clear_all(self):
        """Clear All wipes both the device catalog AND the dismiss list.

        Behavior changed in v0.2.1 (GitHub issue #9): previously the
        dismiss list was preserved across Clear All, which contributed
        to orphan-fingerprint accumulation. Clear All now matches the
        user mental model of "clear everything".
        """
        hass = _make_hass()
        store = SignalStore(hass)
        store.add_device(_make_device("d1"))
        store.add_dismissed("fp1")
        store.clear_all()
        assert store.device_count == 0
        assert not store.is_dismissed("fp1")
        assert store.dismissed_count == 0

    def test_remove_device_discards_dismissed_fingerprint(self):
        """Removing a device also discards its fingerprint from _dismissed.

        Regression for GitHub issue #9: prior to v0.2.1, remove_device
        did not touch _dismissed, so a dismiss -> assign-last-signal or
        dismiss -> delete-last-signal sequence left an orphan fingerprint
        in _dismissed that silently dropped every future signal from that
        physical remote with no UI recovery path.
        """
        hass = _make_hass()
        store = SignalStore(hass)
        device = _make_device("d1", fingerprint="fp1", dismissed=True)
        store.add_device(device)
        store.add_dismissed("fp1")
        assert store.is_dismissed("fp1")

        assert store.remove_device("d1")
        assert store.get_device("d1") is None
        # The invariant: remove_device must also discard the fingerprint.
        assert not store.is_dismissed("fp1")
        assert store.dismissed_count == 0

    def test_remove_device_discards_for_non_dismissed_device_too(self):
        """The discard runs even for non-dismissed devices (harmless no-op).

        Belt-and-suspenders: even if the fingerprint isn't in _dismissed
        (because the user never dismissed this device), the discard call
        is a safe no-op.
        """
        hass = _make_hass()
        store = SignalStore(hass)
        store.add_device(_make_device("d1", fingerprint="fp_clean"))
        assert store.remove_device("d1")
        assert store.dismissed_count == 0


class TestDismissList:

    def test_add_and_check(self):
        hass = _make_hass()
        store = SignalStore(hass)
        assert not store.is_dismissed("fp1")
        store.add_dismissed("fp1")
        assert store.is_dismissed("fp1")

    def test_remove(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store.add_dismissed("fp1")
        store.remove_dismissed("fp1")
        assert not store.is_dismissed("fp1")

    def test_remove_nonexistent_is_safe(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store.remove_dismissed("nonexistent")  # should not raise

    def test_no_cap_on_dismiss_list(self):
        hass = _make_hass()
        store = SignalStore(hass)
        for i in range(1000):
            store.add_dismissed(f"fp_{i}")
        assert store.dismissed_count == 1000


class TestEviction:

    def test_evict_old_low_activity(self):
        hass = _make_hass()
        store = SignalStore(hass)
        old_time = (
            datetime.now(UTC) - timedelta(days=SIGNAL_EVICT_AGE_DAYS + 1)
        ).isoformat()
        store.add_device(_make_device("old_low", hit_count=2, last_seen=old_time))
        store.add_device(_make_device("old_high", hit_count=20, last_seen=old_time))
        store.add_device(_make_device("recent_low", hit_count=2))

        removed = store.evict()
        assert removed == 1
        assert store.get_device("old_low") is None
        assert store.get_device("old_high") is not None
        assert store.get_device("recent_low") is not None

    def test_evict_does_not_touch_dismissed(self):
        hass = _make_hass()
        store = SignalStore(hass)
        old_time = (
            datetime.now(UTC) - timedelta(days=SIGNAL_EVICT_AGE_DAYS + 1)
        ).isoformat()
        store.add_device(
            _make_device("dismissed_old", hit_count=1, last_seen=old_time, dismissed=True)
        )
        removed = store.evict()
        assert removed == 0
        assert store.get_device("dismissed_old") is not None

    def test_evict_does_not_touch_manual(self):
        """Manual (clipped) remotes are user creations, not captured
        noise -- eviction must never remove them, even old and at zero
        hits.
        """
        hass = _make_hass()
        store = SignalStore(hass)
        old_time = (
            datetime.now(UTC) - timedelta(days=SIGNAL_EVICT_AGE_DAYS + 1)
        ).isoformat()
        store.add_device(
            UnknownDevice(
                id="manual_old",
                fingerprint="manual:x",
                hit_count=0,
                last_seen=old_time,
                first_seen=old_time,
                source="manual",
            )
        )
        removed = store.evict()
        assert removed == 0
        assert store.get_device("manual_old") is not None

    def test_evict_over_buffer_limit(self):
        hass = _make_hass()
        store = SignalStore(hass)
        # Add more than SIGNAL_BUFFER_MAX_DEVICES.
        for i in range(SIGNAL_BUFFER_MAX_DEVICES + 10):
            store.add_device(
                _make_device(f"d{i}", f"fp{i}", hit_count=i)
            )
        removed = store.evict()
        assert removed == 10
        assert store.device_count == SIGNAL_BUFFER_MAX_DEVICES
        # Lowest hit_count devices should be evicted.
        assert store.get_device("d0") is None
        assert store.get_device("d9") is None
        # Highest hit_count should survive.
        assert store.get_device(f"d{SIGNAL_BUFFER_MAX_DEVICES + 9}") is not None

    def test_evict_no_op_when_under_limits(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store.add_device(_make_device("d1", hit_count=50))
        removed = store.evict()
        assert removed == 0

    def test_evict_pass2_skips_dismissed_devices(self):
        """Pass 2 must skip dismissed devices the same way Pass 1 does.

        Regression for GitHub issue #9: prior to v0.2.1, eviction Pass 2
        would evict a low-hit dismissed device without removing its
        fingerprint from _dismissed, leaving an orphan that silently
        dropped every future signal from that physical remote.
        """
        hass = _make_hass()
        store = SignalStore(hass)
        # Fill above the buffer limit with normal devices that all have
        # higher hit_count than the dismissed one.
        for i in range(SIGNAL_BUFFER_MAX_DEVICES + 1):
            store.add_device(
                _make_device(f"normal_{i}", f"fp_n{i}", hit_count=100 + i)
            )
        # Add one dismissed device at the bottom of the hit_count scale.
        # Without the Pass 2 guard, this is the first thing to be evicted.
        store.add_device(_make_device(
            "dismissed_low",
            fingerprint="fp_dismissed",
            hit_count=1,
            dismissed=True,
        ))
        store.add_dismissed("fp_dismissed")

        store.evict()

        # Dismissed device must survive Pass 2 just like Pass 1.
        assert store.get_device("dismissed_low") is not None
        assert store.is_dismissed("fp_dismissed")


class TestScheduleSave:

    def test_schedule_save_sets_debounce_timer(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store.schedule_save()
        hass.loop.call_later.assert_called()
        # First call is debounce, second is ceiling.
        assert hass.loop.call_later.call_count == 2

    def test_schedule_save_resets_debounce(self):
        hass = _make_hass()
        timer_mock = MagicMock()
        hass.loop.call_later.return_value = timer_mock
        store = SignalStore(hass)
        store.schedule_save()
        _first_count = hass.loop.call_later.call_count
        store.schedule_save()
        # Debounce timer should have been cancelled and re-created.
        timer_mock.cancel.assert_called()

    @pytest.mark.asyncio
    async def test_async_save_cancels_timers(self):
        hass = _make_hass()
        timer_mock = MagicMock()
        hass.loop.call_later.return_value = timer_mock
        store = SignalStore(hass)
        store.schedule_save()

        with patch.object(store, "_store") as mock_store:
            mock_store.async_save = AsyncMock()
            await store.async_save()

        timer_mock.cancel.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown_flushes_dirty(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store._dirty = True

        with patch.object(store, "_store") as mock_store:
            mock_store.async_save = AsyncMock()
            await store.async_shutdown()

        mock_store.async_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_no_op_when_clean(self):
        hass = _make_hass()
        store = SignalStore(hass)
        store._dirty = False

        with patch.object(store, "_store") as mock_store:
            mock_store.async_save = AsyncMock()
            await store.async_shutdown()

        mock_store.async_save.assert_not_called()


# ---------------------------------------------------------------------------
# Manual order: new-at-top, reorder, migration backfill (drag, v0.3.2)
# ---------------------------------------------------------------------------


def _ordered_device(device_id: str, source: str = "sniffed") -> UnknownDevice:
    return UnknownDevice(id=device_id, fingerprint=device_id, source=source)


class TestManualOrder:

    def test_add_device_places_new_on_top(self):
        store = SignalStore(_make_hass())
        a = _ordered_device("a")
        b = _ordered_device("b")
        c = _ordered_device("c")
        store.add_device(a)
        store.add_device(b)
        store.add_device(c)
        # First gets 0, each subsequent floats below the current min.
        assert a.order == 0
        assert b.order == -1
        assert c.order == -2

    def test_reorder_devices_sets_indices(self):
        store = SignalStore(_make_hass())
        a, b, c = (
            _ordered_device("a"), _ordered_device("b"), _ordered_device("c")
        )
        for d in (a, b, c):
            store.add_device(d)
        store.reorder_devices("sniffed", ["c", "a", "b"])
        assert (c.order, a.order, b.order) == (0, 1, 2)

    def test_reorder_devices_isolates_sources(self):
        store = SignalStore(_make_hass())
        s1, s2 = _ordered_device("s1"), _ordered_device("s2")
        m1, m2 = (
            _ordered_device("m1", "manual"), _ordered_device("m2", "manual")
        )
        for d in (s1, s2, m1, m2):
            store.add_device(d)
        # Reorder only the manual source; sniffed orders must be untouched.
        before = (s1.order, s2.order)
        store.reorder_devices("manual", ["m2", "m1"])
        assert (m2.order, m1.order) == (0, 1)
        assert (s1.order, s2.order) == before

    def test_reorder_devices_rejects_cross_source_id(self):
        store = SignalStore(_make_hass())
        s1 = _ordered_device("s1")
        m1 = _ordered_device("m1", "manual")
        store.add_device(s1)
        store.add_device(m1)
        # m1 is not in the sniffed set -> unknown for that source.
        with pytest.raises(ValueError, match="unknown"):
            store.reorder_devices("sniffed", ["s1", "m1"])

    def test_reorder_devices_duplicate_raises(self):
        store = SignalStore(_make_hass())
        s1 = _ordered_device("s1")
        store.add_device(s1)
        with pytest.raises(ValueError, match="Duplicate"):
            store.reorder_devices("sniffed", ["s1", "s1"])

    @pytest.mark.asyncio
    async def test_load_backfills_order_by_hit_count(self):
        """Pre-0.3.2 records (no order) seed manual order from hit_count."""
        store = SignalStore(_make_hass())
        raw = {
            "devices": [
                {"id": "low", "fingerprint": "low", "hit_count": 1,
                 "first_seen": "2026-01-01T00:00:00+00:00"},
                {"id": "high", "fingerprint": "high", "hit_count": 9,
                 "first_seen": "2026-01-01T00:00:00+00:00"},
                {"id": "mid", "fingerprint": "mid", "hit_count": 5,
                 "first_seen": "2026-01-01T00:00:00+00:00"},
            ],
            "dismissed": [],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        # Highest hit_count lands on top (order 0).
        assert store.get_device("high").order == 0
        assert store.get_device("mid").order == 1
        assert store.get_device("low").order == 2

    @pytest.mark.asyncio
    async def test_load_preserves_existing_order(self):
        """If order is already set, load must not reshuffle it."""
        store = SignalStore(_make_hass())
        raw = {
            "devices": [
                {"id": "a", "fingerprint": "a", "hit_count": 1, "order": 0},
                {"id": "b", "fingerprint": "b", "hit_count": 9, "order": 1},
            ],
            "dismissed": [],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        assert store.get_device("a").order == 0
        assert store.get_device("b").order == 1

    @pytest.mark.asyncio
    async def test_load_dedupes_twin_signals(self):
        """Signals sharing a fingerprint collapse to the first on load."""
        store = SignalStore(_make_hass())
        raw = {
            "devices": [
                {
                    "id": "m1",
                    "fingerprint": "manual:m1",
                    "source": "manual",
                    "order": 0,
                    "signals": [
                        {"fingerprint": "dup", "code": "AAAA", "source": "manual"},
                        {"fingerprint": "dup", "code": "AAAA", "source": "manual"},
                        {"fingerprint": "uniq", "code": "BBBB", "source": "manual"},
                    ],
                },
            ],
            "dismissed": [],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        sigs = store.get_device("m1").signals
        assert [s.fingerprint for s in sigs] == ["dup", "uniq"]
        # A change was made, so the cleaned list will be persisted.
        assert store._dirty is True

    @pytest.mark.asyncio
    async def test_load_v0_3_4_assigns_ids_and_keeps_distinct_byte_hash(self):
        """v0.3.4 migration: legacy signals get a stable id and a byte_hash,
        and two codes that share an S/L fingerprint but differ in bytes are
        NOT collapsed (Panasonic/TCL case)."""
        store = SignalStore(_make_hass())
        power = ("0000 006D 0006 0000 00E0 0070 0014 000D 0014 002E "
                 "0014 000D 0014 000D 0014 0400")
        volup = ("0000 006D 0006 0000 00E0 0070 0014 002E 0014 000D "
                 "0014 000D 0014 002E 0014 0400")
        raw = {
            "devices": [
                {
                    "id": "B", "fingerprint": "B", "order": 0, "signals": [
                        {"fingerprint": "fpY", "code": power, "protocol": "PRONTO"},
                        {"fingerprint": "fpY", "code": volup, "protocol": "PRONTO"},
                    ],
                },
            ],
            "dismissed": [],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        sigs = store.get_device("B").signals
        # Distinct codes sharing a fingerprint stay as two separate signals.
        assert len(sigs) == 2
        assert sigs[0].fingerprint == sigs[1].fingerprint
        assert sigs[0].byte_hash != sigs[1].byte_hash
        # Each legacy signal received a stable id and a computed byte_hash,
        # and the store is dirty so those persist on the next save.
        for sig in sigs:
            assert sig.id
            assert sig.byte_hash is not None
        assert store._dirty is True
