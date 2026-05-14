"""Tests for the entity factory."""
from __future__ import annotations

import pytest

from custom_components.hair.const import DeviceType
from custom_components.hair.entity_factory import (
    DEVICE_TYPE_TO_PLATFORM,
    EntityFactory,
)
from custom_components.hair.models import IRDevice


def test_device_type_to_platform_map():
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.MEDIA_PLAYER] == "media_player"
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.AC] == "climate"
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.FAN] == "fan"
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.LIGHT] == "light"
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.SWITCH] == "switch"
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.SCREEN] == "cover"
    assert DEVICE_TYPE_TO_PLATFORM[DeviceType.OTHER] == "remote"


@pytest.mark.asyncio
async def test_factory_dispatches_to_registered_platform(fake_hass):
    factory = EntityFactory(fake_hass)
    added: list[IRDevice] = []
    factory.register_platform_hooks(
        "media_player", on_add=lambda d: added.append(d)
    )
    device = IRDevice(name="TV", device_type=DeviceType.MEDIA_PLAYER)
    await factory.async_create_entities(device)
    assert added == [device]


@pytest.mark.asyncio
async def test_factory_remove_clears_tracking(fake_hass):
    factory = EntityFactory(fake_hass)
    removed: list[str] = []
    factory.register_platform_hooks(
        "media_player",
        on_add=lambda d: None,
        on_remove=lambda did: removed.append(did),
    )
    device = IRDevice(name="TV", device_type=DeviceType.MEDIA_PLAYER)
    await factory.async_create_entities(device)
    await factory.async_remove_entities(device.id)
    assert removed == [device.id]
