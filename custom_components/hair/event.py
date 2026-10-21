"""Event entity platform for HAIR Triggers.

Creates one EventEntity per IR trigger. A trigger in the HAIR Triggers
drawer lives under a single virtual HA device of that name; a named
Remote's triggers live under the Remote's own device. When a trigger
fires, the corresponding event entity emits an ``ir_command_received``
event.

LAST PRESSED (heard state round 1, GH discussion #172). Every named
Remote also gets ONE event entity, "Last pressed", whose event types are
its buttons: an automation picks "Last pressed: Power" from a list. It
fires from the same TriggerManager callback as the per-trigger entities,
so it follows the same echo rules (an echo is claimed in signal_monitor
and never reaches a trigger). The drawer gets none: it is not a handset.
A matrix Remote's heard cells do not fire it; the STATE MATRIX card and
the "State heard" trigger carry those.
"""
from __future__ import annotations

import logging
from typing import Any, ClassVar

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity_factory import (
    forget_entity_row,
    remote_last_pressed_unique_id,
    trigger_unique_id,
)
from .models import IRTrigger, TriggerRemote
from .trigger_manager import TriggerManager

_LOGGER = logging.getLogger(__name__)

TRIGGER_DEVICE_ID = "triggers"
TRIGGER_DEVICE_NAME = "HAIR Triggers"
EVENT_TYPE = "ir_command_received"
LAST_PRESSED_TRANSLATION_KEY = "last_pressed"
#: The event type of a button whose name is blank.
BLANK_BUTTON = "Button"


def remote_event_types(store: Any, remote_id: str) -> dict[str, str]:
    """``{trigger id: event type}`` for one Remote, in its button order.

    The event type is the button's name as written (trimmed), so it
    reads in whatever language the user named it. A blank name becomes
    ``BLANK_BUTTON``. Types are claimed in the order buttons were
    CREATED: each claims its name if it is free and otherwise the next
    free " (n)". So an older button never loses its type to a newer one:
    reordering reshuffles nothing, and a newer button literally named
    "Power (2)", when an older second "Power" already holds that, becomes
    "Power (2) (2)" (owner ruling 2026-10-21). A rename changes the
    type: the per-
    trigger entity, whose entity id never follows a rename, and the
    ``trigger_id`` in the event data are what survive it.
    """
    triggers = store.get_triggers_for_remote(remote_id)
    used: set[str] = set()
    types: dict[str, str] = {}
    for trigger in sorted(triggers, key=lambda t: (t.created_at or "", t.id)):
        base = (trigger.name or "").strip() or BLANK_BUTTON
        candidate, n = base, 1
        while candidate in used:
            n += 1
            candidate = f"{base} ({n})"
        used.add(candidate)
        types[trigger.id] = candidate
    return {t.id: types[t.id] for t in triggers}


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

    # Track "Last pressed" entities: {remote_id: entity}
    remote_entities: dict[str, HAIRRemoteLastPressedEntity] = {}

    def _fire_entity(trigger_id: str, event_data: dict[str, Any]) -> None:
        """Called by TriggerManager when a trigger fires."""
        entity = entities.get(trigger_id)
        if entity is not None:
            entity.fire_event(event_data)
        trigger = store.get_trigger(trigger_id)
        if trigger is None or trigger.trigger_remote_id is None:
            return
        remote_entity = remote_entities.get(trigger.trigger_remote_id)
        if remote_entity is not None:
            remote_entity.fire_press(
                store, trigger, event_data,
                _trigger_entity_id(hass, trigger.id),
            )

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
    data["_remote_last_pressed_entities"] = remote_entities
    sync_remote_entities(hass, entry.entry_id)


def _trigger_entity_id(hass: HomeAssistant, trigger_id: str) -> str | None:
    """The per-trigger event entity's id, from the registry, or None."""
    from homeassistant.helpers import entity_registry as er

    try:
        return er.async_get(hass).async_get_entity_id(
            "event", DOMAIN, trigger_unique_id(trigger_id)
        )
    except Exception:
        return None


def sync_remote_entities(
    hass: HomeAssistant, entry_id: str, removed_remote_id: str | None = None
) -> None:
    """Make the "Last pressed" entities match the store. Idempotent.

    Adds one for every named Remote that lacks it (an empty Remote
    included, which also gives it its HA device), removes the entity of
    a Remote that is gone and forgets its registry row (as GH #186 does
    for triggers), and pushes every Remote's current name and event
    types, writing state only when either changed. Called from every
    place that changes a Remote or its buttons; a fire that lands before
    such a call syncs its own Remote first (``fire_press``).
    """
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        return
    remote_entities: dict[str, HAIRRemoteLastPressedEntity] | None = data.get(
        "_remote_last_pressed_entities"
    )
    if remote_entities is None:
        return
    store = data["store"]
    async_add_entities = data.get("_trigger_add_entities")

    live = {remote.id: remote for remote in store.get_all_trigger_remotes()}
    gone = [rid for rid in remote_entities if rid not in live]
    if removed_remote_id is not None and removed_remote_id not in gone:
        gone.append(removed_remote_id)
    for remote_id in gone:
        entity = remote_entities.pop(remote_id, None)
        # A disabled entity was never added (its hass is None), so there
        # is nothing to remove from the state machine; the row still goes.
        if entity is not None and entity.hass is not None:
            hass.async_create_task(entity.async_remove())
        forget_entity_row(
            hass, "event", remote_last_pressed_unique_id(remote_id)
        )

    added: list[HAIRRemoteLastPressedEntity] = []
    for remote_id, remote in live.items():
        types = remote_event_types(store, remote_id)
        entity = remote_entities.get(remote_id)
        if entity is None:
            entity = HAIRRemoteLastPressedEntity(remote, types)
            remote_entities[remote_id] = entity
            added.append(entity)
        else:
            entity.refresh(remote.name, types)
    if added and async_add_entities:
        async_add_entities(added)


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

    if removed_id:
        # The row goes whether or not this run holds the entity object
        # (GH #186). It does not after a restart, since the dict is
        # rebuilt per setup, and the row outlives the object either way.
        entity = entities.pop(removed_id, None)
        if entity is not None:
            hass.async_create_task(entity.async_remove())
        forget_entity_row(hass, "event", trigger_unique_id(removed_id))

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


class HAIRRemoteLastPressedEntity(EventEntity):
    """One named Remote's "Last pressed": its buttons as event types."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = LAST_PRESSED_TRANSLATION_KEY

    def __init__(self, remote: TriggerRemote, types: dict[str, str]) -> None:
        self._remote_id = remote.id
        self._remote_name = remote.name
        self._types = dict(types)
        self._attr_unique_id = remote_last_pressed_unique_id(remote.id)
        self._attr_event_types = list(types.values())

    @property
    def remote_id(self) -> str:
        return self._remote_id

    @property
    def device_info(self) -> dict[str, Any]:
        # The same shape the Remote's per-trigger entities register, so
        # the device's fields do not move when this entity is added.
        return {
            "identifiers": {(DOMAIN, self._remote_id)},
            "name": self._remote_name,
            "manufacturer": "HAIR",
            "model": "IR Triggers",
        }

    @callback
    def refresh(self, remote_name: str, types: dict[str, str]) -> bool:
        """Take the Remote's current name and event types. True when
        either changed; state is written only then, and only once the
        entity is registered."""
        # Compared as ordered pairs: a dict compares equal in any order,
        # and a reorder changes nothing but the order.
        if remote_name == self._remote_name and list(types.items()) == list(
            self._types.items()
        ):
            return False
        self._remote_name = remote_name
        self._types = dict(types)
        self._attr_event_types = list(types.values())
        if self._writable:
            self.async_write_ha_state()
        return True

    @property
    def _writable(self) -> bool:
        """Can this entity write state right now?

        Not while its add is still pending (``entity_id`` unset), and
        never when its registry row is disabled: HA aborts the add and
        puts ``hass`` back to None, and a write would raise on the
        capture path. A disabled "Last pressed" is a normal choice for
        someone who does not want it on every Remote, so it must cost
        nothing but its own silence.
        """
        return self.hass is not None and getattr(self, "entity_id", None) is not None

    @callback
    def fire_press(
        self,
        store: Any,
        trigger: IRTrigger,
        event_data: dict[str, Any],
        trigger_entity_id: str | None,
    ) -> bool:
        """Fire for one confirmed trigger fire of this Remote.

        THE TYPE IS RESOLVED NOW, NOT TRUSTED FROM THE LAST SYNC. HA
        refuses an event whose type is not in ``event_types``, and a
        button pressed the moment it was created or renamed can fire
        before anything synced this entity. So the Remote's types are
        computed from the store here and pushed first when they moved.
        """
        types = remote_event_types(store, self._remote_id)
        remote = store.get_trigger_remote(self._remote_id)
        self.refresh(remote.name if remote is not None else self._remote_name, types)
        event_type = types.get(trigger.id)
        if event_type is None or not self._writable:
            return False
        self._trigger_event(event_type, {
            **event_data,
            "button": trigger.name,
            "entity_id": trigger_entity_id,
            "remote_id": self._remote_id,
            "remote_name": self._remote_name,
        })
        self.async_write_ha_state()
        return True
