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


def _device_identity_for_trigger(store: Any, trigger: IRTrigger) -> tuple[str, str]:
    """Resolve the (HA device identifier, device name) an event entity
    for ``trigger`` should register under.

    ``trigger.trigger_remote_id`` is None for every row that lives in
    the HAIR Triggers drawer (the implicit default -- see models.py)
    and is a TriggerRemote's id for a row owned by a named remote (Add
    Popups signpost 2, Track 1B). The drawer keeps its fixed
    ``TRIGGER_DEVICE_ID`` identifier; a named remote gets its own
    device keyed by the TriggerRemote's (stable) id, not its name, so
    renaming the remote never orphans the HA device the identifier
    resolves to.
    """
    if trigger.trigger_remote_id is None:
        return TRIGGER_DEVICE_ID, store.get_trigger_drawer_name()
    remote = store.get_trigger_remote(trigger.trigger_remote_id)
    if remote is None:
        # The owning remote is gone (remove_trigger_remote cascades its
        # triggers, so this should not happen in practice) -- fall back
        # to the drawer rather than construct an entity with a dangling
        # device identifier.
        return TRIGGER_DEVICE_ID, store.get_trigger_drawer_name()
    return remote.id, remote.name


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

    # Bootstrap: create entities for existing triggers. Every entity is
    # constructed with its owning device's CURRENT identity (drawer or
    # named remote -- Trigger Remotes signpost 1 Track B and Add Popups
    # signpost 2 Track 1B) so the device registry entry it registers
    # under carries whatever the owner has renamed that device to, not
    # a module default.
    new_entities: list[HAIRTriggerEventEntity] = []
    for trigger in store.get_all_triggers():
        device_id, device_name = _device_identity_for_trigger(store, trigger)
        entity = HAIRTriggerEventEntity(trigger, device_id, device_name)
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
        store = data["store"]
        device_id, device_name = _device_identity_for_trigger(store, trigger)
        entity = HAIRTriggerEventEntity(trigger, device_id, device_name)
        entities[trigger.id] = entity
        if async_add_entities:
            async_add_entities([entity])


def resync_drawer_name(hass: HomeAssistant, entry_id: str, drawer_name: str) -> None:
    """Push a renamed drawer's name onto every live drawer-owned trigger
    entity (``trigger_remote_id is None``).

    Trigger Remotes signpost 1, Track B (header rename-in-place). A
    fresh ``device_info`` alone does not reach the device registry --
    HA syncs device_info into the registry at entity ADD time, not on
    every state write -- so the WS rename handler also updates the
    registry entry directly (``dr.async_update_device``); this just
    keeps each entity's own cached copy consistent for any future
    lookup that reads ``device_info`` off the entity itself. Scoped to
    drawer-owned entities only -- a named remote's entities carry their
    own device identity and must not pick up the drawer's rename (Add
    Popups signpost 2, Track 1B).
    """
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        return
    entities: dict[str, HAIRTriggerEventEntity] = data.get(
        "_trigger_entities", {}
    )
    for entity in entities.values():
        if entity.trigger.trigger_remote_id is None:
            entity.update_device_identity(TRIGGER_DEVICE_ID, drawer_name)


def resync_remote_name(
    hass: HomeAssistant, entry_id: str, remote_id: str, remote_name: str
) -> None:
    """Push a renamed named-remote's name onto its live trigger entities.

    Mirrors ``resync_drawer_name`` for a TriggerRemote instead of the
    drawer (Add Popups signpost 2, Track 1B-B3): same reasoning applies
    -- the WS rename handler updates the registry entry directly, this
    keeps each owned entity's own cached copy consistent.
    """
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        return
    entities: dict[str, HAIRTriggerEventEntity] = data.get(
        "_trigger_entities", {}
    )
    for entity in entities.values():
        if entity.trigger.trigger_remote_id == remote_id:
            entity.update_device_identity(remote_id, remote_name)


class HAIRTriggerEventEntity(EventEntity):
    """An event entity that fires when a matching IR signal is received."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_event_types: ClassVar[list[str]] = [EVENT_TYPE]

    def __init__(
        self,
        trigger: IRTrigger,
        device_identifier: str = TRIGGER_DEVICE_ID,
        device_name: str = TRIGGER_DEVICE_NAME,
    ) -> None:
        self._trigger = trigger
        self._device_identifier = device_identifier
        self._device_name = device_name
        self._attr_unique_id = f"hair_trigger_{trigger.id}"
        self._attr_name = trigger.name

    @property
    def trigger(self) -> IRTrigger:
        """The IRTrigger this entity fires for (read by the resync helpers
        above to tell drawer-owned rows apart from named-remote rows)."""
        return self._trigger

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device_identifier)},
            "name": self._device_name,
            "manufacturer": "HAIR",
            "model": "IR Triggers",
        }

    @callback
    def update_device_identity(self, device_identifier: str, device_name: str) -> None:
        """Update this entity's cached device identity after a rename."""
        self._device_identifier = device_identifier
        self._device_name = device_name

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
