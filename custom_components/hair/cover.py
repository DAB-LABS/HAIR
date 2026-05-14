"""Cover entity platform for HAIR."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRCoverEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.SCREEN:
            return
        if device.id in entities:
            return
        entity = HAIRCoverEntity(device, device_manager)
        entities[device.id] = entity
        async_add_entities([entity])

    @callback
    def _on_remove(device_id: str) -> None:
        entity = entities.pop(device_id, None)
        if entity is not None:
            hass.async_create_task(entity.async_remove())

    @callback
    def _on_update(device: IRDevice) -> None:
        entity = entities.get(device.id)
        if entity is not None:
            entity.update_device(device)

    factory.register_platform_hooks(
        "cover", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("cover", async_add_entities)

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRCoverEntity(CoverEntity):
    """IR-controlled cover (projector screen, shade, etc.)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_device_class = CoverDeviceClass.SHADE

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_cover"
        self._attr_name = None
        self._is_closed: bool | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Screen / Shade",
        }

    @property
    def supported_features(self) -> CoverEntityFeature:
        features = CoverEntityFeature(0)
        mapping = self._device.entity_config.command_mapping
        if "open_cover" in mapping:
            features |= CoverEntityFeature.OPEN
        if "close_cover" in mapping:
            features |= CoverEntityFeature.CLOSE
        if "stop_cover" in mapping:
            features |= CoverEntityFeature.STOP
        return features

    @property
    def is_closed(self) -> bool | None:
        return self._is_closed

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._send("open_cover")
        self._is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._send("close_cover")
        self._is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._send("stop_cover")
        self.async_write_ha_state()

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        self.async_write_ha_state()

    async def _send(self, *feature_keys: str) -> None:
        mapping = self._device.entity_config.command_mapping
        for key in feature_keys:
            command_name = mapping.get(key)
            if command_name is None:
                continue
            command = self._device.get_command_by_name(command_name)
            if command is not None:
                await self._manager.async_send_command(
                    self._device.id, command.id
                )
                return
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
