"""What can be a device's emitter, by medium (RF send round, T2).

A HAIR device sends through infrared emitters and radio frequency
transmitters, and may hold both (owner's ruling 2026-11-06: one device
for a fan with an infrared and a radio remote). Each command goes only to
the emitters of its own medium; that routing is the send path's
(``rf_send.py``). This module answers the two questions the doors ask
before anything is stored or sent:

- which medium an entity sends, by its domain, and whether it can be an
  emitter at all (not a receiver, not HAIR's own observer, not another
  domain); and
- which radio transmitters exist, with the frequency ranges they
  declare and whether each can send a given frequency.

The frequency rule itself (a fixed-frequency transmitter close enough to
the row's Hz sends at its own) lives in ``rf_send.transmitter_fit`` so
the picker and the send can never disagree. See
``agent-exchange/rf-hear/rf-send-doors.md`` sections 3 and 4.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant

from .const import MEDIUM_IR, MEDIUM_RF, TWEEZER_OBSERVER_ATTR

INFRARED_DOMAIN = "infrared"
RADIO_FREQUENCY_DOMAIN = "radio_frequency"

_MEDIUM_OF_DOMAIN = {
    INFRARED_DOMAIN: MEDIUM_IR,
    RADIO_FREQUENCY_DOMAIN: MEDIUM_RF,
}

INVALID_EMITTER = "invalid_emitter"
EMITTER_WRONG_MEDIUM = "emitter_wrong_medium"


def emitter_medium(entity_id: str) -> str | None:
    """The medium an emitter sends, by domain; None for any other domain."""
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    return _MEDIUM_OF_DOMAIN.get(domain)


def emitter_problem(hass: HomeAssistant, entity_id: str) -> str | None:
    """Why an entity cannot be an emitter, or None when it can.

    Judged from the domain, and from the state only when there is one:
    an emitter whose integration has not loaded yet has no state, and is
    still a valid choice (a device keeps pointing at an emitter that is
    offline, as it always has).
    """
    medium = emitter_medium(entity_id)
    if medium is None:
        return f"{entity_id} is not an infrared emitter or a radio transmitter"
    state = hass.states.get(entity_id)
    if state is None:
        return None
    attrs = state.attributes if isinstance(state.attributes, Mapping) else {}
    if attrs.get(TWEEZER_OBSERVER_ATTR) is True:
        return f"{entity_id} is HAIR's own observer, not an emitter"
    device_class = attrs.get("device_class")
    if medium == MEDIUM_IR and device_class == "receiver":
        return f"{entity_id} is a receiver, not an emitter"
    if medium == MEDIUM_RF and device_class not in (None, "transmitter"):
        return f"{entity_id} is a radio {device_class}, not a transmitter"
    return None


def emitters_error(
    hass: HomeAssistant, entity_ids: list[str]
) -> tuple[str, str] | None:
    """The door's error for an emitter list, or None when every one is valid."""
    problems = [
        problem
        for problem in (emitter_problem(hass, entity_id) for entity_id in entity_ids)
        if problem is not None
    ]
    if not problems:
        return None
    return INVALID_EMITTER, "; ".join(problems)


def of_medium(entity_ids: list[str], medium: str) -> list[str]:
    """The emitters in a list that send a medium, in order."""
    return [entity_id for entity_id in entity_ids if emitter_medium(entity_id) == medium]


def _name(state: Any, entity_id: str) -> str:
    if state is None:
        return entity_id
    return (state.attributes or {}).get("friendly_name") or entity_id


def transmitter_items(
    hass: HomeAssistant, frequency_hz: int | None = None
) -> list[dict[str, Any]]:
    """Every radio transmitter, for the picker (``hair/rf/transmitters``).

    ``fit`` says whether the transmitter can send ``frequency_hz``, by
    the send path's own rule; it is None when no frequency was asked.
    """
    from homeassistant.helpers import entity_registry as er

    from . import rf_send

    registry = er.async_get(hass)
    items: list[dict[str, Any]] = []
    for state in hass.states.async_all(RADIO_FREQUENCY_DOMAIN):
        attrs = state.attributes or {}
        if attrs.get("device_class") != "transmitter":
            continue
        entity_id = state.entity_id
        entry = registry.async_get(entity_id)
        ranges = rf_send.transmitter_ranges(hass, entity_id) or []
        fixed = (
            ranges[0][0]
            if len(ranges) == 1 and ranges[0][0] == ranges[0][1] and ranges[0][0] != 0
            else None
        )
        fit = None
        if frequency_hz is not None:
            result = rf_send.transmitter_fit(hass, entity_id, frequency_hz)
            fit = {
                "ok": result.ok,
                "send_hz": result.send_hz,
                "substituted": result.substituted,
                "code": result.code,
            }
        items.append({
            "entity_id": entity_id,
            "name": _name(state, entity_id),
            "ha_device_id": entry.device_id if entry is not None else None,
            "available": state.state != "unavailable",
            "ranges": [[low, high] for low, high in ranges],
            "fixed_hz": fixed,
            "fit": fit,
        })
    items.sort(key=lambda item: item["name"].casefold())
    return items
