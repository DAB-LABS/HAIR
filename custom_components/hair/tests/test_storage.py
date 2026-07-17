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
from custom_components.hair.event_parser import EventParser
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.protocol_decode import DecodedIdentity
from custom_components.hair.storage import HAIRStore, _HAIRDeviceStore


class _FakeStore:
    """In-memory replacement for homeassistant.helpers.storage.Store."""

    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


_PRONTO_CODE = (
    "0000 006D 0006 0000 00E0 0070 0014 000D 0014 002E "
    "0014 000D 0014 000D 0014 0400"
)


def test_match_command_decoded_tier(fake_hass):
    """The most precise tier matches on the decoded protocol identity."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0xfb04:0x08")],
    )
    store.add_device(dev)
    ref = (dev.id, dev.commands[0].id)
    assert store.match_command("NEC:0xfb04:0x08", "anyfp", None) == ref
    assert store.match_command("NEC:0xffff:0x01", None, None) is None


def test_match_command_fingerprint_and_bytehash_tiers(fake_hass):
    """Composite (fingerprint, byte_hash) matches; a byte_hash miss does
    NOT fall back to the bare fingerprint when the command carries its own
    hash (v0.5.8 behavior flip, deliberate: that false match is how
    assigning one sub-threshold button used to swallow its siblings). The
    bare tier serves only legacy hash-less commands."""
    dev = IRDevice(
        name="TV",
        commands=[
            IRCommand(
                name="Power", protocol="PRONTO", code=_PRONTO_CODE, byte_hash="bh1"
            )
        ],
    )
    store = HAIRStore(fake_hass)
    store.add_device(dev)
    fp = EventParser.signal_fingerprint("PRONTO", _PRONTO_CODE, None)
    ref = (dev.id, dev.commands[0].id)
    assert store.match_command(None, fp, "bh1") == ref
    assert store.match_command(None, fp, "other") is None
    assert store.match_command(None, fp, None) is None
    assert store.match_command(None, "nope", None) is None


def test_match_command_legacy_bare_fp_tier(fake_hass):
    """A hash-less (legacy) command still matches on the bare fingerprint,
    regardless of the incoming signal's byte_hash. Backfill normally
    eliminates this class at load; commands with no Pronto code keep it."""
    dev = IRDevice(
        name="TV",
        commands=[
            IRCommand(name="Power", protocol="PRONTO", code=_PRONTO_CODE)
        ],
    )
    store = HAIRStore(fake_hass)
    store.add_device(dev)
    fp = EventParser.signal_fingerprint("PRONTO", _PRONTO_CODE, None)
    ref = (dev.id, dev.commands[0].id)
    assert store.match_command(None, fp, None) == ref
    assert store.match_command(None, fp, "anything") == ref


def test_command_index_rebuilds_on_remove(fake_hass):
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x2")],
    )
    store = HAIRStore(fake_hass)
    store.add_device(dev)
    assert store.match_command("NEC:0x1:0x2", None, None) is not None
    store.remove_device(dev.id)
    assert store.match_command("NEC:0x1:0x2", None, None) is None


@pytest.mark.asyncio
async def test_async_load_backfills_decoded_fields(fake_hass):
    """v0.4.0 load decodes stored commands into their decoded_* fields and
    the reverse index picks them up."""
    backing = _FakeStore()
    backing._data = {
        "devices": [
            {
                "id": "d1",
                "name": "TV",
                "device_type": "media_player",
                "commands": [
                    {
                        "id": "c1",
                        "name": "Power",
                        "protocol": "PRONTO",
                        "code": _PRONTO_CODE,
                    }
                ],
            }
        ],
        "triggers": [],
    }
    with patch(
        "custom_components.hair.storage._HAIRDeviceStore",
        lambda *a, **k: backing,
    ), patch(
        "custom_components.hair.protocol_decode.try_decode_identity",
        return_value=DecodedIdentity(
            protocol="NEC", address=0xFB04, command=0x08,
            fingerprint="NEC:0xfb04:0x08", extras=None, source="upstream",
        ),
    ):
        store = HAIRStore(fake_hass)
        await store.async_load()
    cmd = store.get_device("d1").commands[0]
    assert cmd.decoded_protocol == "NEC"
    assert cmd.decoded_address == 0xFB04
    assert cmd.decoded_command == 0x08
    assert cmd.decoded_fingerprint == "NEC:0xfb04:0x08"
    assert store.match_command("NEC:0xfb04:0x08", None, None) == ("d1", "c1")


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
