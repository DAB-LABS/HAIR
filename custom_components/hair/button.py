"""Button entity platform for HAIR.

Creates one ButtonEntity per IR command on every device, giving users
a pressable button for each learned command in the HA UI.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity_factory import button_unique_id, forget_entity_row
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAIR button entities for ``entry``."""
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    # Track button entities: {device_id: {command_id: entity}}
    buttons: dict[str, dict[str, HAIRButtonEntity]] = {}

    @callback
    def _sync_buttons(device: IRDevice) -> None:
        """Create / remove buttons so they match the device's current commands."""
        existing = buttons.setdefault(device.id, {})
        current_cmd_ids = {cmd.id for cmd in device.commands}
        existing_cmd_ids = set(existing.keys())

        # Remove buttons for deleted commands. The registry row goes
        # with the entity (GH #186): async_remove alone leaves the row
        # behind, still attached to the HA device, so the deleted
        # command kept showing up in entity pickers as an unavailable
        # button of a device it no longer belonged to. Same order the
        # factory's own platform retirement uses -- schedule the
        # entity's removal, then forget the row.
        removed_ids = existing_cmd_ids - current_cmd_ids
        for cmd_id in removed_ids:
            entity = existing.pop(cmd_id)
            hass.async_create_task(entity.async_remove())
            forget_entity_row(
                hass, "button", button_unique_id(device.id, cmd_id)
            )

        # Add buttons for new commands.
        new_entities: list[HAIRButtonEntity] = []
        for cmd in device.commands:
            if cmd.id not in existing:
                entity = HAIRButtonEntity(device, cmd.id, cmd.name, device_manager)
                existing[cmd.id] = entity
                new_entities.append(entity)
            else:
                # Update name if it changed.
                existing[cmd.id].update_command(device, cmd.id, cmd.name)

        if new_entities:
            async_add_entities(new_entities)

    @callback
    def _on_add(device: IRDevice) -> None:
        _sync_buttons(device)

    @callback
    def _on_remove(device_id: str) -> None:
        existing = buttons.pop(device_id, {})
        for entity in existing.values():
            hass.async_create_task(entity.async_remove())

    @callback
    def _on_update(device: IRDevice) -> None:
        _sync_buttons(device)

    factory.register_platform_hooks(
        "button", on_add=_on_add, on_remove=_on_remove, on_update=_on_update
    )
    factory.register_platform("button", async_add_entities)

    # Bootstrap: create buttons for every existing device.
    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRButtonEntity(ButtonEntity):
    """A pressable button that sends a single IR command."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        device: IRDevice,
        command_id: str,
        command_name: str,
        device_manager,
    ) -> None:
        self._device = device
        self._command_id = command_id
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_btn_{command_id}"
        self._attr_name = command_name

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
        }

    async def async_press(self) -> None:
        """Send the IR command when the button is pressed."""
        await self._manager.async_send_command(
            self._device.id, self._command_id
        )

    @callback
    def update_command(
        self, device: IRDevice, command_id: str, command_name: str
    ) -> None:
        """Update if the command was renamed."""
        self._device = device
        self._command_id = command_id
        if self._attr_name != command_name:
            self._attr_name = command_name
            if self.hass is None:
                # Race: entity instantiated and tracked in the platform's local
                # dict but not yet registered with HA via async_add_entities.
                # The state from __init__ is correct; HA writes it once the
                # registration coroutine completes.
                return
            self.async_write_ha_state()
