"""Tests for the device manager."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    CommandCategory,
    CommandSource,
    DeviceType,
)
from custom_components.hair.device_manager import (
    DeviceManager,
    category_for_command_name,
)
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.storage import HAIRStore


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.fixture
def manager(fake_hass):
    with patch("custom_components.hair.storage.Store", _FakeStore):
        store = HAIRStore(fake_hass)
        # Don't await async_load; the fake returns None synchronously for tests.
        store._loaded = True
        factory = EntityFactory(fake_hass)
        # Stub registry interactions used during create.
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="ha-dev-1")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


@pytest.mark.asyncio
async def test_create_and_remove_device(manager, mock_device: IRDevice):
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="ha-dev-1")),
            async_get_device=MagicMock(return_value=MagicMock(id="ha-dev-1")),
            async_remove_device=MagicMock(),
        ),
    ):
        await manager.async_create_device(mock_device)
        assert manager.get_device(mock_device.id) is not None

        removed = await manager.async_remove_device(mock_device.id)
        assert removed is True
        assert manager.get_device(mock_device.id) is None


@pytest.mark.asyncio
async def test_add_command_auto_maps_for_tv(manager):
    device = IRDevice(
        name="TV", device_type=DeviceType.MEDIA_PLAYER, emitter_entity_ids=["infrared.a"]
    )
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id,
        IRCommand(name="Volume Up", protocol="NEC", code="0x1"),
    )
    refreshed = manager.get_device(device.id)
    assert "volume_up" in refreshed.entity_config.command_mapping
    assert refreshed.entity_config.command_mapping["volume_up"] == "Volume Up"


@pytest.mark.asyncio
async def test_add_command_populates_ac_modes(manager):
    device = IRDevice(
        name="AC", device_type=DeviceType.AC, emitter_entity_ids=["infrared.a"]
    )
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id, IRCommand(name="Mode: Cool", protocol="NEC", code="0x1")
    )
    await manager.async_add_command(
        device.id, IRCommand(name="Fan: High", protocol="NEC", code="0x2")
    )
    refreshed = manager.get_device(device.id)
    assert "cool" in (refreshed.entity_config.hvac_modes or [])
    assert "high" in (refreshed.entity_config.fan_modes or [])


@pytest.mark.asyncio
async def test_remove_command_clears_mapping(manager):
    device = IRDevice(
        name="TV", device_type=DeviceType.MEDIA_PLAYER, emitter_entity_ids=["infrared.a"]
    )
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        await manager.async_create_device(device)
    cmd = IRCommand(name="Volume Up", protocol="NEC", code="0x1")
    await manager.async_add_command(device.id, cmd)

    refreshed = manager.get_device(device.id)
    cmd_id = refreshed.commands[0].id

    await manager.async_remove_command(device.id, cmd_id)
    refreshed = manager.get_device(device.id)
    assert "volume_up" not in refreshed.entity_config.command_mapping


@pytest.mark.asyncio
async def test_send_command_calls_infrared_helper(manager, mock_device: IRDevice):
    """Verify async_send_command() calls infrared.async_send_command with a built Command."""
    mock_ir_send = AsyncMock()
    with (
        patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
                async_get_device=MagicMock(return_value=None),
            ),
        ),
    ):
        await manager.async_create_device(mock_device)

    import sys
    ir_mod = sys.modules["homeassistant.components.infrared"]
    orig = ir_mod.async_send_command
    ir_mod.async_send_command = mock_ir_send
    try:
        await manager.async_send_command(mock_device.id, "cmd-1")
    finally:
        ir_mod.async_send_command = orig

    mock_ir_send.assert_awaited_once()
    call_args = mock_ir_send.call_args
    assert call_args[0][0] is manager._hass  # hass
    assert call_args[0][1] == "infrared.test_emitter"  # entity_id
    ir_cmd = call_args[0][2]  # the Command object
    assert hasattr(ir_cmd, "get_raw_timings")


def test_category_for_command_name():
    assert category_for_command_name("Power") == CommandCategory.POWER
    assert category_for_command_name("Volume Up") == CommandCategory.VOLUME
    assert category_for_command_name("Mute") == CommandCategory.VOLUME
    assert category_for_command_name("Channel Up") == CommandCategory.CHANNEL
    assert category_for_command_name("Mode: Cool") == CommandCategory.MODE
    assert category_for_command_name("Fan: High") == CommandCategory.FAN_SPEED
    assert category_for_command_name("Random") == CommandCategory.CUSTOM
