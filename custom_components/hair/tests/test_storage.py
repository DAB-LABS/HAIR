"""Tests for the HAIR storage layer."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.hair.const import DeviceType
from custom_components.hair.models import IRDevice
from custom_components.hair.storage import HAIRStore


class _FakeStore:
    """In-memory replacement for homeassistant.helpers.storage.Store."""

    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.mark.asyncio
async def test_store_save_load_round_trip(fake_hass, mock_device: IRDevice):
    with patch("custom_components.hair.storage.Store", _FakeStore):
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
    with patch("custom_components.hair.storage.Store", _FakeStore):
        store = HAIRStore(fake_hass)
        await store.async_load()
        store.add_device(mock_device)
        assert store.remove_device(mock_device.id) is True
        assert store.get_device(mock_device.id) is None
        assert store.remove_device("missing") is False


@pytest.mark.asyncio
async def test_store_filters(fake_hass):
    with patch("custom_components.hair.storage.Store", _FakeStore):
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
    with patch("custom_components.hair.storage.Store", lambda *a, **k: backing):
        store = HAIRStore(fake_hass)
        await store.async_load()
        # Bad entry should be skipped, good one should load.
        assert store.get_device("good") is not None
        assert store.get_device("bad") is None
