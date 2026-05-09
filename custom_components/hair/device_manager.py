"""Device CRUD and entity lifecycle management."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, CommandCategory, DeviceType
from .entity_factory import EntityFactory
from .models import IRCommand, IRDevice
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)

# Maps a captured command name (lowercased) → a feature key on the entity.
# The key space is platform-specific; the entity reads
# ``entity_config.command_mapping[<feature key>]`` to find the command name.
AUTO_MAP_RULES: dict[str, str] = {
    "power": "power_toggle",
    "power on": "turn_on",
    "power off": "turn_off",
    "volume up": "volume_up",
    "volume down": "volume_down",
    "mute": "mute",
    "channel up": "channel_up",
    "channel down": "channel_down",
    "source/input": "select_source",
    "source": "select_source",
    "input": "select_source",
    "up": "navigate_up",
    "down": "navigate_down",
    "left": "navigate_left",
    "right": "navigate_right",
    "select/ok": "navigate_select",
    "back/return": "navigate_back",
    "mode: cool": "mode_cool",
    "mode: heat": "mode_heat",
    "mode: fan": "mode_fan_only",
    "mode: dry": "mode_dry",
    "mode: auto": "mode_auto",
    "fan: low": "fan_low",
    "fan: medium": "fan_medium",
    "fan: high": "fan_high",
    "fan: auto": "fan_auto",
    "speed up": "speed_up",
    "speed down": "speed_down",
    "oscillate": "oscillate",
    "swing toggle": "swing_toggle",
    "timer": "timer",
}


class DeviceManager:
    """Manage IR device lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HAIRStore,
        entity_factory: EntityFactory,
        config_entry_id: str,
    ) -> None:
        self._hass = hass
        self._store = store
        self._entity_factory = entity_factory
        self._config_entry_id = config_entry_id

    async def async_create_device(self, device: IRDevice) -> IRDevice:
        """Create a new IR device, register in HA registry, create entities."""
        self._store.add_device(device)
        await self._store.async_save()
        self._register_ha_device(device)
        await self._entity_factory.async_create_entities(device)
        return device

    async def async_update_device(self, device: IRDevice) -> IRDevice:
        self._store.update_device(device)
        await self._store.async_save()
        self._register_ha_device(device)
        await self._entity_factory.async_update_entities(device)
        return device

    async def async_remove_device(self, device_id: str) -> bool:
        device = self._store.get_device(device_id)
        if device is None:
            return False
        await self._entity_factory.async_remove_entities(device_id)

        registry = dr.async_get(self._hass)
        ha_device = registry.async_get_device(
            identifiers={(DOMAIN, device.id)}
        )
        if ha_device is not None:
            registry.async_remove_device(ha_device.id)

        self._store.remove_device(device_id)
        await self._store.async_save()
        return True

    async def async_add_command(
        self, device_id: str, command: IRCommand
    ) -> IRCommand:
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        device.add_command(command)
        self._auto_map_command(device, command)
        self._store.update_device(device)
        await self._store.async_save()
        await self._entity_factory.async_update_entities(device)
        return command

    async def async_remove_command(
        self, device_id: str, command_id: str
    ) -> bool:
        device = self._store.get_device(device_id)
        if device is None:
            return False

        command = device.get_command(command_id)
        removed = device.remove_command(command_id)
        if not removed:
            return False

        if command is not None:
            self._unmap_command(device, command)

        self._store.update_device(device)
        await self._store.async_save()
        await self._entity_factory.async_update_entities(device)
        return True

    async def async_replace_command(
        self,
        device_id: str,
        command_id: str,
        new_command: IRCommand,
    ) -> bool:
        device = self._store.get_device(device_id)
        if device is None:
            return False
        if not device.replace_command(command_id, new_command):
            return False
        self._auto_map_command(device, new_command)
        self._store.update_device(device)
        await self._store.async_save()
        await self._entity_factory.async_update_entities(device)
        return True

    async def async_send_command(
        self, device_id: str, command_id: str
    ) -> None:
        """Send a stored IR command via the configured emitter.

        Forwards to ``infrared.send_command`` (HA's native IR platform
        as of 2026.4). The infrared service accepts either an encoded
        ``code`` or ``raw_timings``.
        """
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        command = device.get_command(command_id)
        if command is None:
            raise KeyError(f"Unknown command {command_id} on device {device_id}")

        service_data: dict[str, object] = {
            "entity_id": device.emitter_entity_id,
            "frequency": command.frequency,
            "repeat": command.repeat_count,
        }
        if command.code is not None:
            service_data["code"] = command.code
        if command.protocol is not None:
            service_data["protocol"] = command.protocol
        if command.raw_timings:
            service_data["raw"] = command.raw_timings

        await self._hass.services.async_call(
            "infrared",
            "send_command",
            service_data,
            blocking=True,
        )

    def _register_ha_device(self, device: IRDevice) -> None:
        registry = dr.async_get(self._hass)
        registry.async_get_or_create(
            config_entry_id=self._config_entry_id,
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer=device.manufacturer or "HAIR",
            model=device.model or _human_device_type(device.device_type),
        )

    def _auto_map_command(self, device: IRDevice, command: IRCommand) -> None:
        feature = AUTO_MAP_RULES.get(command.name.casefold())
        if feature is None:
            return
        device.entity_config.command_mapping[feature] = command.name

        # Track surfaced HVAC and fan modes for the climate entity so the
        # supported_features dynamic computation has something to read.
        if device.device_type == DeviceType.AC:
            if feature.startswith("mode_"):
                modes = list(device.entity_config.hvac_modes or [])
                mode_token = feature.removeprefix("mode_")
                hvac_token = {
                    "cool": "cool",
                    "heat": "heat",
                    "fan_only": "fan_only",
                    "dry": "dry",
                    "auto": "auto",
                }.get(mode_token)
                if hvac_token and hvac_token not in modes:
                    modes.append(hvac_token)
                    device.entity_config.hvac_modes = modes
            elif feature.startswith("fan_"):
                modes = list(device.entity_config.fan_modes or [])
                token = feature.removeprefix("fan_")
                if token not in modes:
                    modes.append(token)
                    device.entity_config.fan_modes = modes

    def _unmap_command(self, device: IRDevice, command: IRCommand) -> None:
        mapping = device.entity_config.command_mapping
        for key, value in list(mapping.items()):
            if value.casefold() == command.name.casefold():
                mapping.pop(key, None)

    def get_device(self, device_id: str) -> IRDevice | None:
        return self._store.get_device(device_id)

    def get_all_devices(self) -> list[IRDevice]:
        return self._store.get_all_devices()


def _human_device_type(device_type: DeviceType) -> str:
    return {
        DeviceType.TV: "TV",
        DeviceType.AC: "Air Conditioner",
        DeviceType.FAN: "Fan",
        DeviceType.SOUNDBAR: "Soundbar",
        DeviceType.PROJECTOR: "Projector",
        DeviceType.OTHER: "IR Device",
    }.get(device_type, "IR Device")


def category_for_command_name(name: str) -> CommandCategory:
    """Best-effort category classification for a command name."""
    lowered = name.casefold()
    if "power" in lowered:
        return CommandCategory.POWER
    if "volume" in lowered or "mute" in lowered:
        return CommandCategory.VOLUME
    if "channel" in lowered:
        return CommandCategory.CHANNEL
    if any(
        token in lowered
        for token in ("up", "down", "left", "right", "ok", "back", "select")
    ):
        return CommandCategory.NAVIGATION
    if "mode" in lowered:
        return CommandCategory.MODE
    if "fan" in lowered or "speed" in lowered:
        return CommandCategory.FAN_SPEED
    if "temp" in lowered:
        return CommandCategory.TEMPERATURE
    return CommandCategory.CUSTOM
