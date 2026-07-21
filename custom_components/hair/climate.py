"""Climate entity platform for HAIR (preset-based)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)

HVAC_MODE_TO_FEATURE: dict[HVACMode, str] = {
    HVACMode.COOL: "mode_cool",
    HVACMode.HEAT: "mode_heat",
    HVACMode.FAN_ONLY: "mode_fan_only",
    HVACMode.DRY: "mode_dry",
    HVACMode.AUTO: "mode_auto",
}

FAN_MODE_TO_FEATURE: dict[str, str] = {
    "low": "fan_low",
    "medium": "fan_medium",
    "high": "fan_high",
    "auto": "fan_auto",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRClimateEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.AC:
            return
        if device.id in entities:
            return
        entity = HAIRClimateEntity(device, device_manager)
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
        "climate",
        on_add=_on_add,
        on_remove=_on_remove,
        on_update=_on_update,
    )
    factory.register_platform("climate", async_add_entities)

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRClimateEntity(ClimateEntity):
    """IR-controlled climate device (preset-based)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_climate"
        self._attr_name = None
        self._hvac_mode = HVACMode.OFF
        self._target_temperature: float | None = None
        self._fan_mode: str | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Air Conditioner",
        }

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = (
            ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        )
        config = self._device.entity_config

        if config.fan_modes:
            features |= ClimateEntityFeature.FAN_MODE
        if config.temperature_presets:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        modes: list[HVACMode] = [HVACMode.OFF]
        configured = self._device.entity_config.hvac_modes or []
        for raw in configured:
            try:
                mode = HVACMode(raw)
            except ValueError:
                continue
            if mode not in modes:
                modes.append(mode)
        return modes

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def min_temp(self) -> float:
        presets = self._device.entity_config.temperature_presets
        if presets:
            return float(min(presets))
        return 60.0

    @property
    def max_temp(self) -> float:
        presets = self._device.entity_config.temperature_presets
        if presets:
            return float(max(presets))
        return 86.0

    @property
    def fan_modes(self) -> list[str] | None:
        return list(self._device.entity_config.fan_modes or []) or None

    @property
    def fan_mode(self) -> str | None:
        return self._fan_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if self._device.entity_config.ac_protocol_id:
            self._hvac_mode = hvac_mode
            await self._send_live_state()
            self.async_write_ha_state()
            return
        if hvac_mode == HVACMode.OFF:
            await self._send("turn_off", "power_toggle")
            self._hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
            return

        feature = HVAC_MODE_TO_FEATURE.get(hvac_mode)
        if feature and await self._send(feature):
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
            return
        # Fall back to power-on if no mode-specific command was captured.
        if await self._send("turn_on", "power_toggle"):
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        raw_target = kwargs.get(ATTR_TEMPERATURE)
        if raw_target is None:
            return
        # Bind a definitely-non-None float before the lambda below: mypy
        # does not carry the None-narrowing into a nested closure, so
        # ``target`` must already be a plain float where the lambda captures it.
        target = float(raw_target)
        if self._device.entity_config.ac_protocol_id:
            self._target_temperature = target
            await self._send_live_state()
            self.async_write_ha_state()
            return
        presets = self._device.entity_config.temperature_presets or []
        if presets:
            snapped = min(presets, key=lambda t: abs(t - target))
            target = float(snapped)
            await self._send(f"temp_{int(snapped)}")
        self._target_temperature = target
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if self._device.entity_config.ac_protocol_id:
            self._fan_mode = fan_mode
            await self._send_live_state()
            self.async_write_ha_state()
            return
        feature = FAN_MODE_TO_FEATURE.get(fan_mode.lower())
        if feature and await self._send(feature):
            self._fan_mode = fan_mode
            self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        if self._device.entity_config.ac_protocol_id:
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_mode = HVACMode.AUTO
            await self._send_live_state()
            self.async_write_ha_state()
            return
        await self._send("turn_on", "power_toggle")
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_mode = HVACMode.AUTO
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        if self._device.entity_config.ac_protocol_id:
            self._hvac_mode = HVACMode.OFF
            await self._send_live_state()
            self.async_write_ha_state()
            return
        await self._send("turn_off", "power_toggle")
        self._hvac_mode = HVACMode.OFF
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

    async def _send_live_state(self) -> None:
        """Encode the entity's CURRENT settings and transmit, right now.

        Unlike ``_send()``, which looks up one pre-captured Pronto command
        by name, a live AC protocol has no discrete commands at all -- the
        whole state (power/mode/temperature/fan/swing) is re-encoded into
        one fresh IR frame on every change, exactly like a real AC remote
        re-sends its full state on every button press. Called from every
        actuation method once ``ac_protocol_id`` is set.
        """
        protocol_id = self._device.entity_config.ac_protocol_id
        if not protocol_id:
            return

        from .custom_ac_source import build_state
        from .custom_ac_source import encode as ac_encode

        # ACState.temperature is Celsius in the protocol library; this
        # entity is Fahrenheit-only (_attr_temperature_unit above).
        temperature_c = 22
        if self._target_temperature is not None:
            temperature_c = round((self._target_temperature - 32) * 5 / 9)

        state = build_state(
            power=self._hvac_mode != HVACMode.OFF,
            hvac_mode=(self._hvac_mode.value if self._hvac_mode != HVACMode.OFF else "cool"),
            temperature_c=temperature_c,
            fan_mode=self._fan_mode,
        )
        if state is None:
            _LOGGER.warning(
                "Custom AC protocol library unavailable for %s; nothing sent",
                self._device.name,
            )
            return

        packet = ac_encode(protocol_id, state)
        if packet is None:
            _LOGGER.warning(
                "Failed to encode live AC state for %s (%s); nothing sent",
                self._device.name,
                protocol_id,
            )
            return

        await self._manager.async_send_raw(
            self._device.id, packet.timings, packet.frequency
        )

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
