"""Persistent storage for the HAIR unknown-signal catalog.

Separate from ``HAIRStore`` (which holds configured devices) so that
clearing unknown signals never touches user-configured devices, and
vice versa.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    SIGNAL_BUFFER_MAX_DEVICES,
    SIGNAL_EVICT_AGE_DAYS,
    SIGNAL_EVICT_MIN_HITS,
    SIGNAL_SAVE_DEBOUNCE_S,
    SIGNAL_SAVE_MAX_DELAY_S,
    SIGNAL_STORAGE_KEY,
    SIGNAL_STORAGE_VERSION,
)
from .models import UnknownDevice

_LOGGER = logging.getLogger(__name__)


class _SignalCatalogStore(Store):
    """``Store`` subclass so the migration hook actually runs (H3).

    Mirrors ``storage._HAIRDeviceStore``. The unknown-signal catalog does
    its schema evolution with an in-application backfill on load (stable
    ids, byte_hash, and the v0.4.0 decoded fields), not a storage-version
    bump, but the migration scaffold must be wired so a future
    ``SIGNAL_STORAGE_VERSION`` bump does not fail every install's load the
    way the composed plain ``Store`` would have.
    """

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        _LOGGER.info(
            "Migrating HAIR signal store from v%s.%s to v%s",
            old_major_version,
            old_minor_version,
            SIGNAL_STORAGE_VERSION,
        )
        return old_data


class SignalStore:
    """Manage persistent storage of the unknown-signal catalog."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = _SignalCatalogStore(
            hass,
            SIGNAL_STORAGE_VERSION,
            SIGNAL_STORAGE_KEY,
            atomic_writes=True,
        )
        self._devices: dict[str, UnknownDevice] = {}
        self._dismissed: set[str] = set()
        self._loaded = False
        self._dirty = False
        self._debounce_handle: asyncio.TimerHandle | None = None
        self._ceiling_handle: asyncio.TimerHandle | None = None
        self._first_dirty_time: float | None = None

    @property
    def loaded(self) -> bool:
        return self._loaded

    # -----------------------------------------------------------------
    # Load / Save
    # -----------------------------------------------------------------

    async def async_load(self) -> None:
        """Load data from storage. Safe to call multiple times."""
        raw = await self._store.async_load()
        if raw is None:
            self._devices = {}
            self._dismissed = set()
            self._loaded = True
            return

        self._devices = {}
        for entry in raw.get("devices") or []:
            try:
                device = UnknownDevice.from_dict(entry)
                self._devices[device.id] = device
            except Exception as err:
                _LOGGER.warning("Skipping malformed unknown device: %s", err)

        self._dismissed = set(raw.get("dismissed") or [])

        # Self-heal: prune any fingerprint in ``_dismissed`` that has no
        # matching ``_devices`` entry. Users upgrading from v0.2.0 or
        # earlier may have accumulated orphan fingerprints on disk via
        # the GH #9 bug. We clean them up at load time so the user
        # auto-recovers on next HA restart after upgrading to v0.2.1
        # without any manual intervention.
        live_fingerprints = {d.fingerprint for d in self._devices.values()}
        orphans = self._dismissed - live_fingerprints
        if orphans:
            self._dismissed -= orphans
            self._dirty = True
            _LOGGER.warning(
                "Pruned %d orphan dismissed fingerprint(s) on load. "
                "This was a v0.2.0 issue (GitHub issue #9) fixed in "
                "v0.2.1; signals from previously-silent remotes should "
                "now appear in the Sniffer normally.",
                len(orphans),
            )

        # v0.3.4 migration: every signal needs a stable id and a byte_hash.
        # ``UnknownSignal.from_dict`` already assigns a fresh id when the
        # stored record has none; compute the byte_hash from the Pronto
        # code where it is missing. Mark the store dirty so the generated
        # ids and computed hashes persist (otherwise ids would regenerate
        # on every load). Runs BEFORE the duplicate cleanup below, which as
        # of v0.3.4 keys on the composite (fingerprint, byte_hash).
        from .event_parser import EventParser

        legacy_signals = any(
            not s.get("id") or s.get("byte_hash") is None
            for d in (raw.get("devices") or [])
            for s in (d.get("signals") or [])
        )
        for device in self._devices.values():
            for sig in device.signals:
                if sig.byte_hash is None and sig.code:
                    sig.byte_hash = EventParser.pronto_byte_hash(sig.code)
        if legacy_signals:
            self._dirty = True

        # Duplicate-signal cleanup (v0.3.2, composite key as of v0.3.4).
        # The Clipper's manual paste path historically had no guard, so a
        # remote could hold two truly identical signals (the same Pronto
        # pasted twice). Collapse each remote's signals to the first
        # occurrence of each (fingerprint, byte_hash) on load. Two signals
        # that share an S/L fingerprint but differ in byte_hash (Panasonic,
        # TCL, and similar protocols) are distinct and are NOT collapsed.
        for device in self._devices.values():
            seen: set[tuple[str, str | None]] = set()
            deduped = []
            for sig in device.signals:
                key = (sig.fingerprint, sig.byte_hash)
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(sig)
            if len(deduped) != len(device.signals):
                device.signals = deduped
                self._dirty = True

        # One-time order backfill (v0.3.2). Pre-0.3.2 records have no
        # ``order`` field, so every device deserializes with order 0. On
        # first load after upgrade, seed the manual order from the old
        # hit_count-descending sort so a user's list does not visibly
        # reshuffle. After this the order is purely manual. Detect the
        # un-migrated state as "more than one device and all order 0".
        if len(self._devices) > 1 and all(
            d.order == 0 for d in self._devices.values()
        ):
            ranked = sorted(
                self._devices.values(),
                key=lambda d: (-d.hit_count, d.first_seen),
            )
            for index, device in enumerate(ranked):
                device.order = index
            self._dirty = True

        self._loaded = True

    async def async_save(self) -> None:
        """Persist current state to disk immediately."""
        self._cancel_timers()
        self._dirty = False
        self._first_dirty_time = None
        await self._store.async_save(self._serialize())

    def schedule_save(self) -> None:
        """Schedule a debounced save.

        Resets the debounce timer on each call. A hard ceiling ensures
        that a busy environment cannot defer writes indefinitely.
        """
        self._dirty = True
        now = time.monotonic()

        # Track when the first unsaved change happened.
        if self._first_dirty_time is None:
            self._first_dirty_time = now

        # Cancel existing debounce timer.
        if self._debounce_handle is not None:
            self._debounce_handle.cancel()

        loop = self._hass.loop

        # Hard ceiling: force save if first dirty change was > max_delay ago.
        elapsed = now - self._first_dirty_time
        if elapsed >= SIGNAL_SAVE_MAX_DELAY_S:
            self._hass.async_create_task(self.async_save())
            return

        # Set debounce timer.
        self._debounce_handle = loop.call_later(
            SIGNAL_SAVE_DEBOUNCE_S,
            lambda: self._hass.async_create_task(self.async_save()),
        )

        # Set ceiling timer if not already set.
        if self._ceiling_handle is None:
            remaining = SIGNAL_SAVE_MAX_DELAY_S - elapsed
            self._ceiling_handle = loop.call_later(
                remaining,
                lambda: self._hass.async_create_task(self.async_save()),
            )

    def _cancel_timers(self) -> None:
        if self._debounce_handle is not None:
            self._debounce_handle.cancel()
            self._debounce_handle = None
        if self._ceiling_handle is not None:
            self._ceiling_handle.cancel()
            self._ceiling_handle = None

    def _serialize(self) -> dict[str, Any]:
        return {
            "devices": [d.to_dict() for d in self._devices.values()],
            "dismissed": list(self._dismissed),
        }

    # -----------------------------------------------------------------
    # Device access
    # -----------------------------------------------------------------

    def get_device(self, device_id: str) -> UnknownDevice | None:
        return self._devices.get(device_id)

    def get_device_by_fingerprint(
        self, fingerprint: str
    ) -> UnknownDevice | None:
        for device in self._devices.values():
            if device.fingerprint == fingerprint:
                return device
        return None

    def get_all_devices(self) -> list[UnknownDevice]:
        return list(self._devices.values())

    def add_device(self, device: UnknownDevice) -> None:
        """Register a newly-discovered unknown device.

        The device is placed at the top of its tab's list by giving it an
        ``order`` strictly below every existing device (min - 1), so a
        brand-new remote always surfaces on top until the user drags it
        into place. ``order`` is computed across all devices; because the
        Sniffer and Clipper each sort their own source-filtered slice, a
        single global minimum is enough to float a new remote to the top
        of whichever tab it belongs to. Reload reconstructs devices
        directly (not through this method), so stored order is preserved.
        """
        if self._devices:
            device.order = min(d.order for d in self._devices.values()) - 1
        else:
            device.order = 0
        self._devices[device.id] = device

    def reorder_devices(self, source: str, ordered_ids: list[str]) -> None:
        """Reorder the devices of one source to match ``ordered_ids``.

        ``ordered_ids`` must be exactly the set of device ids currently
        held for that ``source`` -- no duplicates, unknown, or missing.
        The drag UI always sends the complete per-tab list, so any
        divergence is a stale client and is rejected loudly. Devices of
        the other source are untouched. Renumbers the given source 0..n.

        Raises :class:`ValueError` on mismatch and changes nothing.
        """
        if len(ordered_ids) != len(set(ordered_ids)):
            raise ValueError("Duplicate device ids in reorder list")
        current = {
            d.id for d in self._devices.values() if d.source == source
        }
        requested = set(ordered_ids)
        if requested != current:
            missing = current - requested
            unknown = requested - current
            details: list[str] = []
            if missing:
                details.append(f"missing {sorted(missing)}")
            if unknown:
                details.append(f"unknown {sorted(unknown)}")
            raise ValueError(
                "Reorder list does not match current devices: "
                + ", ".join(details)
            )
        for index, device_id in enumerate(ordered_ids):
            self._devices[device_id].order = index

    def remove_device(self, device_id: str) -> bool:
        """Remove an unknown device from the catalog.

        Also discards the device's fingerprint from the persistent
        dismiss set so that ``_dismissed`` can never hold a fingerprint
        whose corresponding ``_devices`` entry has been removed. Without
        this guarantee, a sequence like dismiss -> assign-last-signal or
        dismiss -> delete-last-signal could leave an orphan fingerprint
        in ``_dismissed`` that silently drops every future signal from
        that physical remote at step 4 of the signal pipeline, with no
        UI affordance to recover. Fixed in v0.2.1 (GitHub issue #9).
        """
        device = self._devices.get(device_id)
        if device is None:
            return False
        self._dismissed.discard(device.fingerprint)
        del self._devices[device_id]
        return True

    @property
    def device_count(self) -> int:
        return len(self._devices)

    # -----------------------------------------------------------------
    # Dismiss list
    # -----------------------------------------------------------------

    def add_dismissed(self, fingerprint: str) -> None:
        """Add a fingerprint to the dismiss list (persisted, no cap)."""
        self._dismissed.add(fingerprint)

    def is_dismissed(self, fingerprint: str) -> bool:
        return fingerprint in self._dismissed

    def remove_dismissed(self, fingerprint: str) -> None:
        self._dismissed.discard(fingerprint)

    @property
    def dismissed_count(self) -> int:
        return len(self._dismissed)

    # -----------------------------------------------------------------
    # Eviction
    # -----------------------------------------------------------------

    def evict(self) -> int:
        """Apply eviction rules. Returns count of devices removed.

        Rules (applied in order):
        1. Age + low activity: >30 days old AND <5 hits -> remove.
        2. If still over buffer max: evict lowest hit_count, oldest
           last_seen first until under the limit.
        """
        removed = 0
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=SIGNAL_EVICT_AGE_DAYS)

        # Pass 1: age + low activity. Manual (clipped) remotes are user
        # creations, not captured noise -- never evict them.
        to_remove = []
        for device in self._devices.values():
            if device.dismissed or device.source == "manual":
                continue
            try:
                last = datetime.fromisoformat(device.last_seen)
            except (ValueError, TypeError):
                continue
            if last < cutoff and device.hit_count < SIGNAL_EVICT_MIN_HITS:
                to_remove.append(device.id)

        for device_id in to_remove:
            del self._devices[device_id]
            removed += 1

        # Pass 2: if still over limit, evict lowest activity.
        # Also skip dismissed devices here so an orphan fingerprint can
        # never form via eviction. Without this guard, a dismissed
        # device with a low ``hit_count`` could be evicted while its
        # fingerprint remains in ``_dismissed``, silently dropping every
        # future signal from that physical remote (GitHub issue #9).
        # Matches the Pass 1 skip behavior.
        if len(self._devices) > SIGNAL_BUFFER_MAX_DEVICES:
            sorted_devices = sorted(
                (
                    d
                    for d in self._devices.values()
                    if not d.dismissed and d.source != "manual"
                ),
                key=lambda d: (d.hit_count, d.last_seen),
            )
            while (
                len(self._devices) > SIGNAL_BUFFER_MAX_DEVICES
                and sorted_devices
            ):
                victim = sorted_devices.pop(0)
                del self._devices[victim.id]
                removed += 1

        return removed

    # -----------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------

    def clear_all(self, source: str | None = None) -> None:
        """Wipe the unknown catalog AND the dismiss list.

        ``source=None`` clears everything (the historical behavior).
        Passing ``"sniffed"`` or ``"manual"`` clears only devices of that
        source and discards just their fingerprints from the dismiss set,
        leaving the other source untouched. This lets each tab (Sniffer /
        Clips) clear its own world without touching the other's.

        Behavior changed in v0.2.1: prior versions kept the dismiss
        list across Clear All. That design choice contributed to silent
        accumulation of orphan dismissed fingerprints (GitHub issue #9)
        because the dismiss list was reachable only through devices that
        had been Clear All'd away. Clear All now matches the user mental
        model of "clear everything," and serves as a manual recovery
        route for users who hit the orphan bug before upgrading.
        """
        if source is None:
            self._devices.clear()
            self._dismissed.clear()
            return

        for device_id in [
            d.id for d in self._devices.values() if d.source == source
        ]:
            device = self._devices.pop(device_id)
            self._dismissed.discard(device.fingerprint)

    async def async_shutdown(self) -> None:
        """Flush pending writes and cancel timers."""
        self._cancel_timers()
        if self._dirty:
            await self.async_save()
