"""Device CRUD and entity lifecycle management."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    DEFAULT_CARRIER_FREQUENCY,
    DOMAIN,
    MAX_DITTO_COUNT,
    MAX_SEND_COUNT,
    SEND_REPEAT_GAP,
    CommandCategory,
    DeviceType,
)
from .entity_factory import EntityFactory
from .models import IRCommand, IRDevice
from .storage import HAIRStore

if TYPE_CHECKING:
    from .trigger_manager import TriggerManager

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
    # Light
    "on": "turn_on",
    "off": "turn_off",
    "brightness up": "brightness_up",
    "brightness down": "brightness_down",
    # Cover / screen
    "open": "open_cover",
    "close": "close_cover",
    # Media transport
    "guide": "guide",
    "menu": "menu",
    "play": "play",
    "pause": "pause",
    "rewind": "rewind",
    "fast forward": "fast_forward",
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

    async def async_update_command(
        self,
        device_id: str,
        command_id: str,
        *,
        name: str | None = None,
        pronto: str | None = None,
        send_count: int | None = None,
        repeat_count: int | None = None,
        trigger_manager: TriggerManager | None = None,
    ) -> dict[str, Any]:
        """Edit a device command's name and/or Pronto in place.

        On a name change: guard against a duplicate name on the device,
        then cascade the action mappings (every ``command_mapping`` value
        equal to the old name moves to the new name) and report the count.
        On a Pronto change: re-evaluate the new code as a fresh capture
        (``code`` / ``raw_timings`` / ``byte_hash`` / ``decoded_*`` /
        ``frequency``) and rewire any bound trigger when the S/L
        fingerprint changes. Persists through :meth:`async_update_device`
        so the known-command reverse index rebuilds (a code edit changes
        its keys) and the entity ``update_device`` hooks fire.

        Returns ``{success, command, triggers, mappings_updated}`` on
        success, or ``{success: False, code, error}``.
        """
        from .event_parser import EventParser
        from .ir_command import ProntoCommand
        from .pronto_validator import validate_pronto
        from .protocol_decode import decode_to_fields

        device = self._store.get_device(device_id)
        if device is None:
            return {"success": False, "code": "device_not_found",
                    "error": "Device not found"}
        command = device.get_command(command_id)
        if command is None:
            return {"success": False, "code": "command_not_found",
                    "error": "Command not found"}

        rewire: dict[str, list[str]] = {"rewired": [], "skipped": []}
        mappings_updated = 0

        # --- name change: collision guard + mapping cascade ---
        if name is not None:
            new_name = name.strip()
            if not new_name:
                return {"success": False, "code": "invalid_name",
                        "error": "Command name cannot be empty"}
            if new_name.casefold() != command.name.casefold():
                clash = device.get_command_by_name(new_name)
                if clash is not None and clash.id != command.id:
                    return {
                        "success": False, "code": "duplicate_name",
                        "error": "Another command on this device has that name",
                    }
                old_name = command.name
                command.name = new_name
                # Cascade every mapping whose value is the old command name.
                mapping = device.entity_config.command_mapping
                for key, val in mapping.items():
                    if val.casefold() == old_name.casefold():
                        mapping[key] = new_name
                        mappings_updated += 1

        # --- pronto change: recompute identity + rewire triggers ---
        if pronto is not None:
            result = validate_pronto(pronto)
            if not result.valid:
                return {
                    "success": False, "code": "invalid_pronto",
                    "error": (result.errors[0] if result.errors
                              else "Invalid Pronto code"),
                }
            new_code = result.normalized
            old_fp = EventParser.signal_fingerprint(
                command.protocol, command.code, command.raw_timings
            )
            new_fp = EventParser.signal_fingerprint("PRONTO", new_code, [])
            try:
                raw = ProntoCommand(new_code).get_raw_timings()
            except Exception:  # bad code falls back to no decoded timings
                raw = None
            (
                decoded_protocol,
                decoded_address,
                decoded_command,
                decoded_fingerprint,
            ) = decode_to_fields(raw)
            command.protocol = "PRONTO"
            command.code = new_code
            command.raw_timings = list(raw) if raw else None
            command.byte_hash = EventParser.pronto_byte_hash(new_code)
            command.frequency = (
                round(result.frequency_khz * 1000)
                if result.frequency_khz
                else DEFAULT_CARRIER_FREQUENCY
            )
            command.decoded_protocol = decoded_protocol
            command.decoded_address = decoded_address
            command.decoded_command = decoded_command
            command.decoded_fingerprint = decoded_fingerprint
            if trigger_manager is not None and new_fp and new_fp != old_fp:
                rewire = await trigger_manager.rewire(
                    old_fp, new_fp, "PRONTO", new_code
                )

        # --- whole-frame send count ---
        if send_count is not None:
            command.send_count = max(1, min(int(send_count), MAX_SEND_COUNT))

        # --- NEC ditto count ---
        if repeat_count is not None:
            command.repeat_count = max(0, min(int(repeat_count), MAX_DITTO_COUNT))

        await self.async_update_device(device)
        return {
            "success": True,
            "command": command.to_dict(),
            "triggers": rewire,
            "mappings_updated": mappings_updated,
        }

    async def async_reorder_devices(self, ordered_ids: list[str]) -> None:
        """Reorder the device list and persist. Raises ValueError on a
        stale/mismatched id list (see ``HAIRStore.reorder_devices``)."""
        self._store.reorder_devices(ordered_ids)
        await self._store.async_save()

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

    async def async_apply_auto_map(
        self, device_id: str, command_id: str
    ) -> IRDevice | None:
        """Apply the action auto-map to an already-stored command and refresh.

        The assign path (``signal_monitor.assign_*``) creates the command via
        the model's ``add_command``, which -- unlike the learn path's
        ``async_add_command`` -- does not run ``_auto_map_command``. Call this
        after an assign so a command whose name matches a standard action
        (Power, Fan: Auto, Mode: Cool, ...) gets mapped, the AC fan/hvac modes
        get registered, and the entities refresh to expose them. A no-op for a
        custom name with no standard action. Returns the updated device.
        """
        device = self._store.get_device(device_id)
        if device is None:
            return None
        command = device.get_command(command_id)
        if command is None:
            return device
        self._auto_map_command(device, command)
        return await self.async_update_device(device)

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
        """Send a stored IR command via all configured emitters (broadcast).

        Uses ``homeassistant.components.infrared.async_send_command``
        (HA 2026.4+) which accepts an ``infrared_protocols.Command``
        instance wrapping the raw timings or Pronto hex.

        The command is sent to every emitter in the device's
        ``emitter_entity_ids`` list for maximum coverage.
        """
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        command = device.get_command(command_id)
        if command is None:
            raise KeyError(f"Unknown command {command_id} on device {device_id}")

        if not device.emitter_entity_ids:
            raise RuntimeError(f"Device {device_id} has no emitters configured")

        # Lazy imports: infrared component only available at runtime on HA 2026.4+.
        from homeassistant.components.infrared import (
            async_send_command as ir_send,
        )

        from .ir_command import build_command, build_decoded_command

        # Prefer canonical encode-from-decoded when the command carries a
        # decoded protocol identity and the user has not pinned it to the
        # captured timings. This transmits clean library-encoded timings
        # rather than replaying captured (receiver-distorted) ones, which
        # fixes replay failures against non-TSOP destinations (GH #14).
        # Falls back to Pronto/raw replay when undecodable, opted out, or
        # the library is unavailable.
        ir_cmd = None
        if command.decoded_fingerprint and not command.tx_force_raw:
            ir_cmd = build_decoded_command(
                command.decoded_protocol,
                command.decoded_address,
                command.decoded_command,
                repeat_count=command.repeat_count or 0,
            )
        if ir_cmd is None:
            ir_cmd = build_command(
                protocol=command.protocol,
                code=command.code,
                raw_timings=command.raw_timings,
                frequency=command.frequency or 38000,
                repeat_count=command.repeat_count or 0,
            )

        # Whole-frame repetition: transmit the built Command send_count times
        # to every emitter, with a short pause between frames so the receiver
        # registers them as distinct presses. send_count defaults to 1.
        send_count = max(1, command.send_count or 1)
        for i in range(send_count):
            if i:
                await asyncio.sleep(SEND_REPEAT_GAP)
            for emitter_id in device.emitter_entity_ids:
                await ir_send(self._hass, emitter_id, ir_cmd)

    async def async_set_command_tx_force_raw(
        self, device_id: str, command_id: str, tx_force_raw: bool
    ) -> bool:
        """Toggle a command's ``tx_force_raw`` flag and persist.

        When True, transmit replays the captured Pronto/raw timings instead
        of re-encoding from the decoded value -- the per-command escape
        hatch for the rare destination that wants the captured timings.
        """
        device = self._store.get_device(device_id)
        if device is None:
            return False
        command = device.get_command(command_id)
        if command is None:
            return False
        command.tx_force_raw = tx_force_raw
        self._store.update_device(device)
        await self._store.async_save()
        return True

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
        DeviceType.MEDIA_PLAYER: "Media Player",
        DeviceType.AC: "Air Conditioner",
        DeviceType.FAN: "Fan",
        DeviceType.LIGHT: "Light",
        DeviceType.SWITCH: "Switch",
        DeviceType.SCREEN: "Screen / Shade",
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
