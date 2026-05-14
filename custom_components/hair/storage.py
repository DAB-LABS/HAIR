"""Persistent storage for the HAIR integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    STORAGE_VERSION_MINOR,
)
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


class HAIRStore:
    """Manage persistent storage of IR devices and commands.

    Uses HA's versioned Store. Migrations run when the on-disk
    major/minor version is older than STORAGE_VERSION/STORAGE_VERSION_MINOR.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            minor_version=STORAGE_VERSION_MINOR,
            atomic_writes=True,
        )
        self._data: dict[str, IRDevice] = {}
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    async def async_load(self) -> None:
        """Load data from storage. Safe to call multiple times."""
        raw = await self._store.async_load()
        if raw is None:
            self._data = {}
            self._loaded = True
            return

        devices_raw = raw.get("devices") or []
        self._data = {}
        for entry in devices_raw:
            try:
                device = IRDevice.from_dict(entry)
            except Exception as err:
                _LOGGER.warning(
                    "Skipping malformed device entry %s: %s",
                    entry.get("id"),
                    err,
                )
                continue
            self._data[device.id] = device
        self._loaded = True

    async def async_save(self) -> None:
        """Persist current in-memory state."""
        await self._store.async_save(self._serialize())

    def _serialize(self) -> dict[str, Any]:
        return {
            "devices": [d.to_dict() for d in self._data.values()],
        }

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Migrate storage schema between versions.

        v1.1 (current) is the initial schema. Future migrations bump
        STORAGE_VERSION_MINOR (or STORAGE_VERSION for breaking changes)
        and add branches here.
        """
        _LOGGER.info(
            "Migrating HAIR storage from v%s.%s to v%s.%s",
            old_major_version,
            old_minor_version,
            STORAGE_VERSION,
            STORAGE_VERSION_MINOR,
        )
        return old_data

    def get_device(self, device_id: str) -> IRDevice | None:
        return self._data.get(device_id)

    def get_all_devices(self) -> list[IRDevice]:
        return list(self._data.values())

    def add_device(self, device: IRDevice) -> None:
        self._data[device.id] = device

    def update_device(self, device: IRDevice) -> None:
        self._data[device.id] = device

    def remove_device(self, device_id: str) -> bool:
        if device_id in self._data:
            del self._data[device_id]
            return True
        return False

    def get_devices_by_emitter(
        self, emitter_entity_id: str
    ) -> list[IRDevice]:
        return [
            d for d in self._data.values()
            if emitter_entity_id in d.emitter_entity_ids
        ]

    def get_devices_by_type(self, device_type: str) -> list[IRDevice]:
        return [
            d for d in self._data.values()
            if str(d.device_type) == str(device_type)
        ]
