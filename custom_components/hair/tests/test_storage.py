"""Tests for the HAIR storage layer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    STORAGE_VERSION_MINOR,
    DeviceType,
)
from custom_components.hair.models import IRDevice
from custom_components.hair.storage import HAIRStore, _HAIRDeviceStore


class _FakeStore:
    """In-memory replacement for homeassistant.helpers.storage.Store."""

    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.mark.asyncio
async def test_device_store_migration_hook_wired_on_subclass():
    """H3: the migrate hook lives on the Store subclass (so HA's
    async_load dispatches to it), not on the HAIRStore wrapper where it
    was dead code before v0.4.0."""
    # The wrapper must NOT define the hook -- that was the bug.
    assert "_async_migrate_func" not in HAIRStore.__dict__
    # The Store subclass defines it, so HA's async_load will call it.
    assert "_async_migrate_func" in _HAIRDeviceStore.__dict__

    store = _HAIRDeviceStore(
        MagicMock(),
        STORAGE_VERSION,
        STORAGE_KEY,
        minor_version=STORAGE_VERSION_MINOR + 1,
    )
    old_data = {"devices": [{"id": "d1"}], "triggers": []}
    migrated = await store._async_migrate_func(STORAGE_VERSION, 0, old_data)
    assert migrated == old_data


@pytest.mark.asyncio
async def test_store_save_load_round_trip(fake_hass, mock_device: IRDevice):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()

        store.add_device(mock_device)
        await store.async_save()

        store2 = HAIRStore(fake_hass)
        # Inject the same fake-store backing data so the second instance
        # sees what the first wrote.
        store2._store = store._store  # type: ignore[attr-defined]
        await store2.async_load()

        loaded = store2.get_device(mock_device.id)
        assert loaded is not None
        assert loaded.name == mock_device.name
        assert len(loaded.commands) == 1


@pytest.mark.asyncio
async def test_store_remove_device(fake_hass, mock_device: IRDevice):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        store.add_device(mock_device)
        assert store.remove_device(mock_device.id) is True
        assert store.get_device(mock_device.id) is None
        assert store.remove_device("missing") is False


@pytest.mark.asyncio
async def test_store_filters(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()

        tv = IRDevice(
            name="TV", device_type=DeviceType.MEDIA_PLAYER,
            emitter_entity_ids=["infrared.a"],
        )
        ac = IRDevice(name="AC", device_type=DeviceType.AC, emitter_entity_ids=["infrared.b"])
        store.add_device(tv)
        store.add_device(ac)

        assert len(store.get_devices_by_emitter("infrared.a")) == 1
        assert len(store.get_devices_by_type("media_player")) == 1
        assert len(store.get_all_devices()) == 2


@pytest.mark.asyncio
async def test_store_skips_malformed_entries(fake_hass):
    backing = _FakeStore()
    backing._data = {
        "devices": [
            {"id": "good", "name": "Good", "device_type": "tv"},
            {"id": "bad", "device_type": "not-a-type"},  # Triggers ValueError
        ]
    }
    with patch("custom_components.hair.storage._HAIRDeviceStore", lambda *a, **k: backing):
        store = HAIRStore(fake_hass)
        await store.async_load()
        # Bad entry should be skipped, good one should load.
        assert store.get_device("good") is not None
        assert store.get_device("bad") is None


# ---------------------------------------------------------------------------
# reorder_devices (drag-to-reorder on the Devices tab, v0.3.2)
# ---------------------------------------------------------------------------

def _dev(name: str) -> IRDevice:
    return IRDevice(name=name, device_type=DeviceType.MEDIA_PLAYER)


@pytest.mark.asyncio
async def test_reorder_devices_happy_path(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        a, b, c = _dev("A"), _dev("B"), _dev("C")
        for d in (a, b, c):
            store.add_device(d)

        store.reorder_devices([c.id, a.id, b.id])

        assert [d.id for d in store.get_all_devices()] == [c.id, a.id, b.id]


@pytest.mark.asyncio
async def test_reorder_devices_persists_order(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        a, b = _dev("A"), _dev("B")
        store.add_device(a)
        store.add_device(b)
        store.reorder_devices([b.id, a.id])
        await store.async_save()

        store2 = HAIRStore(fake_hass)
        store2._store = store._store  # type: ignore[attr-defined]
        await store2.async_load()
        assert [d.id for d in store2.get_all_devices()] == [b.id, a.id]


@pytest.mark.asyncio
async def test_reorder_devices_duplicate_raises(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        a = _dev("A")
        store.add_device(a)
        with pytest.raises(ValueError, match="Duplicate"):
            store.reorder_devices([a.id, a.id])


@pytest.mark.asyncio
async def test_reorder_devices_unknown_raises(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        a = _dev("A")
        store.add_device(a)
        before = [d.id for d in store.get_all_devices()]
        with pytest.raises(ValueError, match="unknown"):
            store.reorder_devices([a.id, "ghost"])
        assert [d.id for d in store.get_all_devices()] == before


@pytest.mark.asyncio
async def test_reorder_devices_missing_raises(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        a, b = _dev("A"), _dev("B")
        store.add_device(a)
        store.add_device(b)
        before = [d.id for d in store.get_all_devices()]
        with pytest.raises(ValueError, match="missing"):
            store.reorder_devices([a.id])
        assert [d.id for d in store.get_all_devices()] == before
