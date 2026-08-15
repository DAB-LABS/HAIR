"""Device trigger platform for HAIR Triggers and named trigger remotes.

Lets the automation editor offer "Device: <name> -> <button>" instead of
picking an event entity by hand (Trigger Remotes signpost 1; the
device_trigger ruling in
docs/internal/plans/trigger-remotes-release-a.md, "Ruling: device
triggers ship in Release A", 2026-08-10). Originally written against the
single HAIR Triggers device; generalized (Add Popups signpost 2, Track
1B-B5) to recognize any HAIR trigger-bearing device -- the drawer OR a
named TriggerRemote -- and to scope subtype resolution to whichever one
owns the device_id in front of it, so two remotes (or a remote and the
drawer) can carry same-named buttons without colliding.

Rename tolerance is the whole point, not an afterthought. HA's automation
editor stores the picked dropdown entry's ``subtype`` as a raw string --
code-verified against home-assistant/frontend's
``localizeDeviceAutomationTrigger``: the editor renders the subtype raw
whenever no per-subtype translation exists, so what is displayed and what
is stored are the same string, and that string is the trigger's CURRENT
NAME, not a stable id. Renaming a trigger after an automation is built
against it would silently strand the automation without the alias-history
resolution below (see :func:`_resolve_subtype`).

Delegates the actual listening to HA's own event-trigger platform
(``homeassistant.components.homeassistant.triggers.event``), filtered on
HAIR's ``EVENT_TRIGGER_FIRED`` bus event plus the resolved trigger id --
the exact same bus event the trigger's event entity already fires
(``trigger_manager.TriggerManager._fire_trigger``). This is a second,
friendlier door onto identical firing, additive and never a second source
of truth: nothing here changes event-entity behavior, and a signal press
still fires both.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_TRIGGER_FIRED
from .event import TRIGGER_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

# Not a shared homeassistant.const symbol -- every device_trigger.py in HA
# core defines this locally (verified against homeassistant/components/
# zha/device_trigger.py, the reference implementation this file follows).
CONF_SUBTYPE = "subtype"

TRIGGER_TYPE_BUTTON_PRESSED = "button_pressed"
TRIGGER_TYPES = {TRIGGER_TYPE_BUTTON_PRESSED}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): str,
    }
)

# A trigger_id that can never occur (stored trigger ids are uuid4 strings),
# used as the event-data filter when a subtype resolves to no live
# trigger. Keeps async_attach_trigger permissive -- the HA convention that
# a device trigger referencing a since-removed target attaches cleanly and
# simply never fires -- without special-casing "no filter at all", which
# would instead fire on every OTHER trigger's press.
_UNRESOLVED_SENTINEL = "__hair_unresolved_trigger__"


def _get_first_entry_data(hass: HomeAssistant) -> dict[str, Any] | None:
    """Return the first entry's hass.data for HAIR.

    HAIR is a hub integration with at most one entry per HA instance.
    Duplicated from websocket_api.py's private helper of the same shape
    rather than imported, so this platform module does not pull in the
    whole (much heavier) websocket_api module just for one lookup.
    """
    entries = hass.data.get(DOMAIN, {})
    for value in entries.values():
        if isinstance(value, dict) and "device_manager" in value:
            return value
    return None


# Sentinel distinguishing "not a HAIR trigger device at all" (e.g. a
# Controlled Device, or some other integration's device) from a real
# scope that happens to resolve to the drawer (whose own scope value,
# TRIGGER_DEVICE_ID, is a normal string and cannot double as its own
# not-found marker).
_NOT_A_TRIGGER_DEVICE = object()


def _owning_scope_for_device(hass: HomeAssistant, device_id: str) -> Any:
    """Resolve which HAIR trigger scope owns ``device_id``.

    Returns ``TRIGGER_DEVICE_ID`` when ``device_id`` is the HAIR
    Triggers drawer, a TriggerRemote's own id when it is a named remote
    (Add Popups signpost 2), or ``_NOT_A_TRIGGER_DEVICE`` when it is
    neither -- e.g. a Controlled Device, which must never be offered
    (nonexistent) device triggers.
    """
    device_entry = dr.async_get(hass).async_get(device_id)
    if device_entry is None:
        return _NOT_A_TRIGGER_DEVICE
    identifier_values = {
        identifier for domain, identifier in device_entry.identifiers
        if domain == DOMAIN
    }
    if TRIGGER_DEVICE_ID in identifier_values:
        return TRIGGER_DEVICE_ID
    data = _get_first_entry_data(hass)
    if data is not None:
        store = data["store"]
        for identifier in identifier_values:
            if store.get_trigger_remote(identifier) is not None:
                return identifier
    return _NOT_A_TRIGGER_DEVICE


def _resolve_subtype(
    hass: HomeAssistant, subtype: str, remote_id: str | None = None
) -> str | None:
    """Resolve a device trigger's stored subtype to a trigger id.

    Scoped to ``remote_id``'s own rows (None = the drawer, also the
    default -- pre-signpost-2 callers that never pass it keep resolving
    against the drawer exactly as before). Add Popups signpost 2, Track
    1B-B5: two remotes (or a remote and the drawer) may carry
    same-named buttons, so resolution must never search past the
    device the automation was actually built against.

    Current names win first: a live trigger whose CURRENT name equals
    ``subtype`` always resolves to itself, even if some other trigger's
    alias history also contains that string -- the owner's "live names
    always win" rule (a name someone is actively using outranks a name
    someone else abandoned). Only when no live trigger claims the name
    does history apply, which is what lets an automation built against an
    old name keep resolving across any number of later renames.

    Returns None when nothing matches at all (a deleted trigger, or a
    name that was never real). The caller then attaches a filter that
    never fires rather than raising, matching the ruled behavior: "a
    deleted trigger simply drops out and stored automations referencing
    it never fire again, no sweep, no error."
    """
    data = _get_first_entry_data(hass)
    if data is None:
        return None
    store = data["store"]
    triggers = store.get_triggers_for_remote(remote_id)
    for trigger in triggers:
        if trigger.name == subtype:
            return trigger.id
    for trigger in triggers:
        if subtype in trigger.alias_history:
            return trigger.id
    return None


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers: one per stored trigger owned by
    ``device_id``, in order.

    Only a HAIR trigger device (the drawer or a named remote) offers
    any -- ``_owning_scope_for_device`` is what keeps HAIR from
    offering (nonexistent) device triggers on a Controlled Device.
    """
    scope = _owning_scope_for_device(hass, device_id)
    if scope is _NOT_A_TRIGGER_DEVICE:
        return []
    remote_id = None if scope == TRIGGER_DEVICE_ID else scope
    data = _get_first_entry_data(hass)
    if data is None:
        return []
    store = data["store"]
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: TRIGGER_TYPE_BUTTON_PRESSED,
            CONF_SUBTYPE: trigger.name,
        }
        for trigger in store.get_triggers_for_remote(remote_id)
    ]


async def async_validate_trigger_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate config. Deliberately permissive, per HA convention.

    Does not check that the subtype still resolves to a live trigger: a
    renamed or deleted trigger must not fail automation validation on
    every HA restart or reload. Resolution -- and its rename tolerance --
    happens at attach time in :func:`async_attach_trigger`.
    """
    return TRIGGER_SCHEMA(config)


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a listener that fires on this trigger's own signal.

    Resolves ``subtype`` once, at attach time, to a trigger id, then
    filters HAIR's ``EVENT_TRIGGER_FIRED`` bus event on that id for the
    life of the listener. Because the filter is keyed on id rather than
    name, a trigger renamed WHILE an automation is already attached keeps
    firing without missing a beat -- the id never changes underneath it.
    The alias-history resolution in :func:`_resolve_subtype` is what lets
    an automation attached (or re-attached, e.g. on HA restart) AFTER a
    rename -- still carrying the OLD subtype in its stored config --
    resolve to the correct, still-current trigger.

    Resolves the owning device's scope (drawer vs. named remote) fresh
    at attach time too, same as the subtype -- so an automation still
    resolves correctly even if it was attached before its remote
    existed and only now does (device_id is stable; scope lookup is
    cheap and re-run on every attach, never cached).
    """
    config = TRIGGER_SCHEMA(config)
    scope = _owning_scope_for_device(hass, config[CONF_DEVICE_ID])
    if scope is _NOT_A_TRIGGER_DEVICE:
        # The device itself is gone (or was never a HAIR trigger
        # device) -- do not fall back to searching the drawer, that
        # would let a deleted remote's automation start resolving
        # against an unrelated same-named drawer trigger. Unresolved,
        # same as a subtype that matches nothing (see below).
        trigger_id = None
    else:
        remote_id = None if scope == TRIGGER_DEVICE_ID else scope
        trigger_id = _resolve_subtype(hass, config[CONF_SUBTYPE], remote_id)
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_TRIGGER_FIRED,
            event_trigger.CONF_EVENT_DATA: {
                "trigger_id": trigger_id or _UNRESOLVED_SENTINEL,
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
