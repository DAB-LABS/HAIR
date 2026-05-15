"""Event entity platform for HAIR Triggers.

Creates one EventEntity per IR trigger. All trigger entities live under
a single virtual HA device called "HAIR Triggers". When a trigger fires,
the corresponding event entity emits an ``ir_command_received`` event.
"""
from __future__ import annotations

import logging
from typing import Any, ClassVar

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import IRTrigger
from .trigger_manager import TriggerManager

_LOGGER = logging.getLogger(__name__)

TRIGGER_DEVICE_ID = "triggers"
TRIGGER_DEVICE_NAME = "HAIR Triggers"
EVENT_TYPE = "ir_command_received"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAIR event entities for triggers."""
    data = hass.data[DOMAIN][entry.entry_id]
    store = data["store"]
    trigger_manager: TriggerManager = data["trigger_manager"]

    # Track event entities: {trigger_id: entity}
    entities: dict[str, HAIRTriggerEventEntity] = {}

    def _fire_entity(trigger_id: str, event_data: dict[str, Any]) -> None:
        """Called by TriggerManager when a trigger fires."""
        entity = entities.get(trigger_id)
        if entity is not None:
            entity.fire_event(event_data)

    trigger_manager.register_entity_callback(_fire_entity)

    # Bootstrap: create entities for existing triggers.
    new_entities: list[HAIRTriggerEventEntity] = []
    for trigger in store.get_all_triggers():
        entity = HAIRTriggerEventEntity(trigger)
        entities[trigger.id] = entity
        new_entities.append(entity)
    if new_entities:
        async_add_entities(new_entities)

    # Store the add callback and entity map so the WS API can sync entities
    # when triggers are created/deleted.
    data["_trigger_entities"] = entities
    data["_trigger_add_entities"] = async_add_entities


def sync_trigger_entities(
    hass: HomeAssistant,
    entry_id: str,
    trigger: IRTrigger | None = None,
    removed_id: str | None = None,
) -> None:
    """Sync event entities after trigger create/delete.

    Called from the WebSocket API handlers.
    """
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        return

    entities: dict[str, HAIRTriggerEventEntity] = data.get(
        "_trigger_entities", {}
    )
    async_add_entities = data.get("_trigger_add_entities")

    if removed_id and removed_id in entities:
        entity = entities.pop(removed_id)
        hass.async_create_task(entity.async_remove())

    if trigger and trigger.id not in entities:
        entity = HAIRTriggerEventEntity(trigger)
        entities[trigger.id] = entity
        if async_add_entities:
            async_add_entities([entity])


class HAIRTriggerEventEntity(EventEntity):
    """An event entity that fires when a matching IR signal is received."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_event_types: ClassVar[list[str]] = [EVENT_TYPE]

    def __init__(self, trigger: IRTrigger) -> None:
        self._trigger = trigger
        self._attr_unique_id = f"hair_trigger_{trigger.id}"
        self._attr_name = trigger.name

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, TRIGGER_DEVICE_ID)},
            "name": TRIGGER_DEVICE_NAME,
            "manufacturer": "HAIR",
            "model": "IR Triggers",
        }

    @callback
    def fire_event(self, event_data: dict[str, Any]) -> None:
        """Trigger the event entity with the given data."""
        self._trigger_event(EVENT_TYPE, event_data)
        self.async_write_ha_state()

    @callback
    def update_trigger(self, trigger: IRTrigger) -> None:
        """Update if the trigger was renamed."""
        self._trigger = trigger
        if self._attr_name != trigger.name:
            self._attr_name = trigger.name
            self.async_write_ha_state()
