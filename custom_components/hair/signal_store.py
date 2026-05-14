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


class SignalStore:
    """Manage persistent storage of the unknown-signal catalog."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
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
        self._devices[device.id] = device

    def remove_device(self, device_id: str) -> bool:
        if device_id in self._devices:
            del self._devices[device_id]
            return True
        return False

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

        # Pass 1: age + low activity.
        to_remove = []
        for device in self._devices.values():
            if device.dismissed:
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
        if len(self._devices) > SIGNAL_BUFFER_MAX_DEVICES:
            sorted_devices = sorted(
                self._devices.values(),
                key=lambda d: (d.hit_count, d.last_seen),
            )
            while len(self._devices) > SIGNAL_BUFFER_MAX_DEVICES:
                victim = sorted_devices.pop(0)
                del self._devices[victim.id]
                removed += 1

        return removed

    # -----------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------

    def clear_all(self) -> None:
        """Wipe the entire unknown catalog (but keep dismiss list)."""
        self._devices.clear()

    async def async_shutdown(self) -> None:
        """Flush pending writes and cancel timers."""
        self._cancel_timers()
        if self._dirty:
            await self.async_save()
