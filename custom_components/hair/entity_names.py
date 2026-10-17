"""Display names for the entities HAIR talks about, without the double.

Home Assistant composes an entity's ``friendly_name`` as the device's
name followed by the entity's own name. When the entity's own name
already starts with the device's name, the device name prints twice:
HAIR's shipped ESPHome configs name the transmitter
``${friendly_name} TX``, so a device called "KinCony AGv3 1" gets the
friendly name "KinCony AGv3 1 KinCony AGv3 1 TX", and the Mirror said
"via" that whole string (owner's phone, 2026-10-16).

HA's own interface strips that repeated device name before showing an
entity under its device; this does the same for the labels HAIR builds.
It only ever removes a repeat of the device's own name, read from the
registries, so a name that merely starts with a repeated word ("Bora
Bora Lamp") is untouched. Anything missing (no registry entry, no
device, no friendly name) falls back to what HAIR showed before.

Renaming the entity in the shipped ESPHome configs is NOT the fix: the
ESPHome object id follows the name, so a rename creates a new Home
Assistant entity and orphans every HAIR device pointed at the old one.
"""
from __future__ import annotations

from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


def collapse_doubled_device_name(friendly_name: str, device_name: str | None) -> str:
    """Drop a leading device name that the entity's own name repeats.

    ``"D D TX"`` with device ``"D"`` becomes ``"D TX"``. Anything else is
    returned unchanged, including ``"D TX"`` itself.
    """
    if not isinstance(friendly_name, str) or not isinstance(device_name, str):
        return friendly_name
    if not friendly_name or not device_name:
        return friendly_name
    device_name = device_name.strip()
    if not device_name:
        return friendly_name
    doubled = f"{device_name} {device_name}"
    if friendly_name == doubled or friendly_name.startswith(doubled + " "):
        return friendly_name[len(device_name) + 1:]
    return friendly_name


def entity_display_name(hass: Any, entity_id: str) -> str:
    """The entity's friendly name, its device name said once."""
    state = hass.states.get(entity_id)
    name = None
    if state is not None:
        name = state.attributes.get("friendly_name")
    if not name:
        return entity_id
    name = str(name)
    # A label must never break a send: any registry trouble falls back
    # to the friendly name as it was.
    try:
        entry = er.async_get(hass).async_get(entity_id)
        if entry is None or entry.device_id is None:
            return name
        device = dr.async_get(hass).async_get(entry.device_id)
    except Exception:
        return name
    if device is None:
        return name
    for candidate in (device.name_by_user, device.name):
        collapsed = collapse_doubled_device_name(name, candidate)
        if collapsed != name:
            return collapsed
    return name
