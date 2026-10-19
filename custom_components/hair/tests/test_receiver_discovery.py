"""Tests for the receiver hardware discovery behind the Devices cards and setup.

This was ``get_available_capture_providers`` in ``capture.py``, beside the
capture hardware the Learn dialog drove. The dialog and the hardware are
gone (windowed receivers, round 3); the discovery moved to
``receiver_discovery.py`` and these tests moved with it, unchanged but for
the names.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.const import ReceiverHardwareType
from custom_components.hair.receiver_discovery import list_receiver_hardware


def _make_fake_device(device_id="dev-1", name="ESP Device"):
    dev = MagicMock()
    dev.id = device_id
    dev.name_by_user = None
    dev.name = name
    dev.disabled = False
    dev.config_entries = {"esp-entry-1"}
    return dev


def _make_fake_entity(entity_id="remote.ir_blaster"):
    ent = MagicMock()
    ent.entity_id = entity_id
    return ent


def _wire_bridge_active(fake_hass, *device_ids: str) -> None:
    """Populate hass.data with a signal monitor whose bridge-active set
    includes the given device IDs. ``receiver_discovery.list_receiver_hardware``
    consults this to decide whether to surface ESPHome bridge entries.
    """
    from custom_components.hair.const import DOMAIN
    monitor = MagicMock()
    monitor.bridge_active_device_ids = set(device_ids)
    fake_hass.data.setdefault(DOMAIN, {})["entry-1"] = {
        "signal_monitor": monitor,
    }


@pytest.mark.asyncio
async def test_esphome_device_with_ir_entities_included(fake_hass):
    """ESPHome device with IR entities should be listed when bridge is active."""
    fake_hass.config.components = {"esphome"}
    fake_hass.config_entries.async_entries = MagicMock(
        return_value=[MagicMock(entry_id="esp-entry-1")]
    )
    fake_device = _make_fake_device()
    fake_ir_entity = _make_fake_entity("infrared.hair1_tx")
    # Bridge is only surfaced once we've actually observed a bus event
    # from the device. Simulate that by populating the bridge-active set.
    _wire_bridge_active(fake_hass, "dev-1")

    with patch(
        "custom_components.hair.receiver_discovery.dr.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.receiver_discovery.dr.async_entries_for_config_entry",
        return_value=[fake_device],
    ), patch(
        "custom_components.hair.receiver_discovery.er.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.receiver_discovery.er.async_entries_for_device",
        return_value=[fake_ir_entity],
    ):
        hardware = await list_receiver_hardware(fake_hass)
    assert len(hardware) == 1
    assert hardware[0]["device_id"] == "dev-1"
    assert hardware[0]["type"] == "esphome"


@pytest.mark.asyncio
async def test_esphome_device_without_ir_entities_excluded(fake_hass):
    """ESPHome device without IR entities should be excluded from the hardware list."""
    fake_hass.config.components = {"esphome"}
    fake_hass.config_entries.async_entries = MagicMock(
        return_value=[MagicMock(entry_id="esp-entry-1")]
    )
    fake_device = _make_fake_device()
    fake_sensor = _make_fake_entity("sensor.temperature")
    _wire_bridge_active(fake_hass, "dev-1")

    with patch(
        "custom_components.hair.receiver_discovery.dr.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.receiver_discovery.dr.async_entries_for_config_entry",
        return_value=[fake_device],
    ), patch(
        "custom_components.hair.receiver_discovery.er.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.receiver_discovery.er.async_entries_for_device",
        return_value=[fake_sensor],
    ):
        hardware = await list_receiver_hardware(fake_hass)
    assert len(hardware) == 0


@pytest.mark.asyncio
async def test_esphome_device_without_bridge_events_excluded(fake_hass):
    """ESPHome device with IR entities but no observed bridge events stays hidden."""
    fake_hass.config.components = {"esphome"}
    fake_hass.config_entries.async_entries = MagicMock(
        return_value=[MagicMock(entry_id="esp-entry-1")]
    )
    fake_device = _make_fake_device()
    fake_ir_entity = _make_fake_entity("infrared.hair1_tx")
    # Deliberately do NOT call _wire_bridge_active -- no events seen yet.

    with patch(
        "custom_components.hair.receiver_discovery.dr.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.receiver_discovery.dr.async_entries_for_config_entry",
        return_value=[fake_device],
    ), patch(
        "custom_components.hair.receiver_discovery.er.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.receiver_discovery.er.async_entries_for_device",
        return_value=[fake_ir_entity],
    ):
        hardware = await list_receiver_hardware(fake_hass)
    assert hardware == []


# ---------------------------------------------------------------------------
# Native receiver discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_native_receivers_discovered(fake_hass):
    """Native receivers should appear in the hardware list."""
    fake_hass.config.components = set()
    state = MagicMock()
    state.attributes = {"friendly_name": "HAIR1 RX"}
    fake_hass.states.get.return_value = state

    def fake_get_receivers(_hass):
        return ["infrared.hair1_rx"]

    mock_ir_module = MagicMock()
    mock_ir_module.async_get_receivers = fake_get_receivers

    with patch.dict("sys.modules", {
        "homeassistant.components.infrared": mock_ir_module,
    }):
        hardware = await list_receiver_hardware(fake_hass)

    native = [p for p in hardware if p["type"] == str(ReceiverHardwareType.NATIVE)]
    assert len(native) == 1
    assert native[0]["device_id"] == "infrared.hair1_rx"
    assert native[0]["receiver_entity_id"] == "infrared.hair1_rx"
    assert native[0]["name"] == "HAIR1 RX"
