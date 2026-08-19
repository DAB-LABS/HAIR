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


# ---------------------------------------------------------------------------
# Changing a device's type (GH #106, 0.10.1 item 9)
# ---------------------------------------------------------------------------
#
# async_update_entities used to resolve the RECORDED platform and call
# only that one's on_update, so a type change never reached the new
# platform and the entity appeared only after an HA restart rebuilt
# everything from the store. A change of type is a retire and an add.


class _Platforms:
    """Every hook a platform can install, recorded per platform."""

    def __init__(self, factory, *platforms):
        self.added: list[tuple[str, str]] = []
        self.removed: list[tuple[str, str]] = []
        self.updated: list[tuple[str, str]] = []
        for platform in platforms:
            factory.register_platform_hooks(
                platform,
                on_add=self._rec(self.added, platform),
                on_remove=self._rec(self.removed, platform, ident=True),
                on_update=self._rec(self.updated, platform),
            )

    @staticmethod
    def _rec(bucket, platform, ident=False):
        def _hook(arg):
            bucket.append((platform, arg if ident else arg.id))

        return _hook

    def names(self, bucket):
        return [p for p, _ in bucket]


def _factory(fake_hass):
    from custom_components.hair.entity_factory import EntityFactory

    return EntityFactory(fake_hass)


@pytest.mark.asyncio
async def test_other_to_fan_creates_the_fan_entity(fake_hass):
    factory = _factory(fake_hass)
    hooks = _Platforms(factory, "remote", "button", "fan", "climate")
    device = IRDevice(name="Adopted", device_type=DeviceType.OTHER)
    await factory.async_create_entities(device)
    hooks.added.clear()

    device.device_type = DeviceType.FAN
    await factory.async_update_entities(device)

    assert hooks.added == [("fan", device.id)]
    # The remote and button entities a universal platform owns stay put.
    assert hooks.removed == []
    assert set(hooks.names(hooks.updated)) == {"remote", "button"}
    assert factory._entities[device.id] == "fan"
    assert device.entity_config.platform == "fan"


@pytest.mark.asyncio
async def test_fan_to_climate_removes_the_fan_and_adds_the_climate(fake_hass):
    factory = _factory(fake_hass)
    hooks = _Platforms(factory, "remote", "button", "fan", "climate")
    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    await factory.async_create_entities(device)
    hooks.added.clear()
    hooks.updated.clear()

    device.device_type = DeviceType.AC
    await factory.async_update_entities(device)

    assert hooks.removed == [("fan", device.id)]
    assert hooks.added == [("climate", device.id)]
    # The new platform is added, not added and then updated on the same
    # tick; the entity's constructor already has the device.
    assert ("climate", device.id) not in hooks.updated
    assert factory._entities[device.id] == "climate"


@pytest.mark.asyncio
async def test_ac_to_other_removes_the_climate_and_keeps_the_remote(fake_hass):
    factory = _factory(fake_hass)
    hooks = _Platforms(factory, "remote", "button", "climate")
    device = IRDevice(name="Unit", device_type=DeviceType.AC)
    await factory.async_create_entities(device)
    hooks.added.clear()
    hooks.updated.clear()

    device.device_type = DeviceType.OTHER
    await factory.async_update_entities(device)

    assert hooks.removed == [("climate", device.id)]
    # "remote" is universal: its entity already exists, so it is updated
    # rather than added again.
    assert hooks.added == []
    assert set(hooks.names(hooks.updated)) == {"remote", "button"}
    assert factory._entities[device.id] == "remote"


@pytest.mark.asyncio
async def test_a_same_type_save_only_updates(fake_hass):
    factory = _factory(fake_hass)
    hooks = _Platforms(factory, "remote", "button", "fan")
    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    await factory.async_create_entities(device)
    hooks.added.clear()
    hooks.updated.clear()

    device.name = "Renamed"
    await factory.async_update_entities(device)

    assert hooks.added == []
    assert hooks.removed == []
    assert set(hooks.names(hooks.updated)) == {"fan", "remote", "button"}


@pytest.mark.asyncio
async def test_a_platform_with_no_hook_yet_gets_the_dispatcher_signal(
    fake_hass, monkeypatch
):
    from custom_components.hair import entity_factory as ef

    factory = _factory(fake_hass)
    _Platforms(factory, "remote", "button")
    device = IRDevice(name="Adopted", device_type=DeviceType.OTHER)
    await factory.async_create_entities(device)
    sent: list[tuple] = []
    monkeypatch.setattr(
        ef, "async_dispatcher_send",
        lambda hass, signal, payload: sent.append((signal, payload)),
    )

    device.device_type = DeviceType.FAN
    await factory.async_update_entities(device)

    assert sent == [(ef.SIGNAL_ADD_ENTITY, device)]


@pytest.mark.asyncio
async def test_the_retired_platforms_registry_row_goes_too(fake_hass):
    """Entity.async_remove leaves a REGISTERED entity as unavailable, so
    without this a dead fan.* row would survive under Settings >
    Entities forever."""
    from unittest.mock import MagicMock, patch

    from custom_components.hair.const import DOMAIN
    from custom_components.hair.entity_factory import platform_unique_id

    factory = _factory(fake_hass)
    _Platforms(factory, "remote", "button", "fan", "climate")
    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    await factory.async_create_entities(device)
    registry = MagicMock()
    registry.async_get_entity_id = MagicMock(return_value="fan.unit")

    device.device_type = DeviceType.AC
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=registry,
    ):
        await factory.async_update_entities(device)

    registry.async_get_entity_id.assert_called_once_with(
        "fan", DOMAIN, platform_unique_id(device.id, "fan")
    )
    registry.async_remove.assert_called_once_with("fan.unit")


@pytest.mark.asyncio
async def test_no_registry_row_to_remove_is_not_an_error(fake_hass):
    from unittest.mock import MagicMock, patch

    factory = _factory(fake_hass)
    _Platforms(factory, "remote", "button", "fan", "climate")
    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    await factory.async_create_entities(device)
    registry = MagicMock()
    registry.async_get_entity_id = MagicMock(return_value=None)

    device.device_type = DeviceType.AC
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=registry,
    ):
        await factory.async_update_entities(device)

    registry.async_remove.assert_not_called()
    assert factory._entities[device.id] == "climate"


@pytest.mark.asyncio
async def test_a_refusing_registry_never_undoes_the_type_change(fake_hass):
    from unittest.mock import MagicMock, patch

    factory = _factory(fake_hass)
    hooks = _Platforms(factory, "remote", "button", "fan", "climate")
    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    await factory.async_create_entities(device)
    hooks.added.clear()
    registry = MagicMock()
    registry.async_remove.side_effect = RuntimeError("busy")
    registry.async_get_entity_id = MagicMock(return_value="fan.unit")

    device.device_type = DeviceType.AC
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=registry,
    ):
        await factory.async_update_entities(device)

    assert hooks.added == [("climate", device.id)]
    assert factory._entities[device.id] == "climate"


@pytest.mark.asyncio
async def test_a_device_delete_does_not_touch_the_registry(fake_hass):
    """Removing the HA device already takes its entity rows."""
    from unittest.mock import MagicMock, patch

    factory = _factory(fake_hass)
    _Platforms(factory, "remote", "button", "fan")
    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    await factory.async_create_entities(device)
    registry = MagicMock()

    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=registry,
    ):
        await factory.async_remove_entities(device.id)

    registry.async_remove.assert_not_called()


def test_the_ha_device_identity_does_not_move_with_the_type():
    """The new entity has to land on the SAME device page."""
    from unittest.mock import MagicMock

    from custom_components.hair.climate import HAIRClimateEntity
    from custom_components.hair.fan import HAIRFanEntity

    device = IRDevice(name="Unit", device_type=DeviceType.FAN)
    fan = HAIRFanEntity(device, MagicMock())
    device.device_type = DeviceType.AC
    climate = HAIRClimateEntity(device, MagicMock())

    assert fan.device_info["identifiers"] == climate.device_info["identifiers"]


def test_platform_unique_id_matches_what_the_platforms_build():
    """The registry row is only findable by unique id, so the factory's
    idea of that id and the platforms' must not drift."""
    from unittest.mock import MagicMock

    from custom_components.hair.climate import HAIRClimateEntity
    from custom_components.hair.cover import HAIRCoverEntity
    from custom_components.hair.entity_factory import platform_unique_id
    from custom_components.hair.fan import HAIRFanEntity
    from custom_components.hair.light import HAIRLightEntity
    from custom_components.hair.media_player import HAIRMediaPlayerEntity
    from custom_components.hair.remote import HAIRRemoteEntity
    from custom_components.hair.switch import HAIRSwitchEntity

    device = IRDevice(name="Unit")
    for platform, cls in (
        ("climate", HAIRClimateEntity),
        ("cover", HAIRCoverEntity),
        ("fan", HAIRFanEntity),
        ("light", HAIRLightEntity),
        ("media_player", HAIRMediaPlayerEntity),
        ("remote", HAIRRemoteEntity),
        ("switch", HAIRSwitchEntity),
    ):
        entity = cls(device, MagicMock())
        assert entity._attr_unique_id == platform_unique_id(
            device.id, platform
        )
