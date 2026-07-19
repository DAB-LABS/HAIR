"""Fan entity platform for HAIR."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ordered_list_item,
    ordered_list_item_to_percentage,
)

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)

SPEED_COUNT = 10
SPEED_KEYS = [f"speed_{i}" for i in range(1, SPEED_COUNT + 1)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRFanEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.FAN:
            return
        if device.id in entities:
            return
        entity = HAIRFanEntity(device, device_manager)
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
        "fan", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("fan", async_add_entities)

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRFanEntity(FanEntity):
    """IR-controlled fan."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_fan"
        self._attr_name = None
        self._is_on = False
        self._percentage: int | None = None
        self._oscillating: bool = False

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Fan",
        }

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        mapping = self._device.entity_config.command_mapping
        if "speed_up" in mapping or "speed_down" in mapping or self._mapped_speed_steps(mapping):
            features |= FanEntityFeature.SET_SPEED
        if "oscillate" in mapping:
            features |= FanEntityFeature.OSCILLATE
        return features

    @property
    def speed_count(self) -> int:
        mapping = self._device.entity_config.command_mapping
        return len(self._mapped_speed_steps(mapping)) or SPEED_COUNT

    @staticmethod
    def _mapped_speed_steps(mapping: dict[str, str]) -> list[str]:
        return [key for key in SPEED_KEYS if key in mapping]

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def percentage(self) -> int | None:
        return self._percentage

    @property
    def oscillating(self) -> bool:
        return self._oscillating

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self._send("turn_on", "power_toggle")
        self._is_on = True
        if percentage is not None:
            self._percentage = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off", "power_toggle")
        self._is_on = False
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        mapping = self._device.entity_config.command_mapping
        speed_steps = self._mapped_speed_steps(mapping)
        if speed_steps:
            if percentage == 0:
                await self.async_turn_off()
                return
            step = percentage_to_ordered_list_item(speed_steps, percentage)
            await self._send(step)
            self._percentage = ordered_list_item_to_percentage(speed_steps, step)
            self.async_write_ha_state()
            return

        target = percentage
        current = self._percentage or 0
        # Step toward target using speed_up / speed_down.
        delta = target - current
        if delta > 0:
            steps = max(1, delta // 25)
            for _ in range(steps):
                if not await self._send("speed_up"):
                    break
        elif delta < 0:
            steps = max(1, abs(delta) // 25)
            for _ in range(steps):
                if not await self._send("speed_down"):
                    break
        self._percentage = target
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        await self._send("oscillate")
        self._oscillating = oscillating
        self.async_write_ha_state()

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        if self.hass is None:
            # Race: entity instantiated and tracked in the platform's local
            # dict but not yet registered with HA via async_add_entities.
            # The state from __init__ is correct; HA writes it once the
            # registration coroutine completes.
            return
        self.async_write_ha_state()

    async def _send(self, *feature_keys: str) -> bool:
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
                return True
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
        return False
