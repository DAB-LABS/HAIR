"""Device-registry lookups that do not use the deprecated door.

Home Assistant deprecated ``DeviceRegistry.async_get_device`` because an
identifier or a connection is unique only WITHIN a config entry, not
across them: two integrations may both register ``("foo", "1")``, and a
lookup with no entry to scope it by has to guess which device the caller
meant. The deprecated call reports its usage on 2026.9 and is removed in
2027.8.0. Its replacements each take the entry that owns the device:

- ``async_get_device_by_identifier(identifier, config_entry_id)``
- ``async_get_device_by_connection(connection, config_entry_id)``
- ``async_get_devices(identifiers=, connections=, config_entry_id=)``

WHY THIS MODULE EXISTS AT ALL. All three arrived in Home Assistant
2026.8.0 (core PR 176879). HAIR supports 2026.4.0 and up, so four
supported releases do not have them, and a straight switch would break
import on the floor of the support range. Every HAIR lookup therefore
goes through the two functions below, which use the new call where the
registry has it and the old one only where it does not. One place to
delete when the floor eventually reaches 2026.8.0, rather than nine.

WHY THE CAPABILITY IS ASKED OF THE CLASS. ``_registry_has`` looks at
``type(registry)``, not at the instance. HAIR's suite runs against a
stubbed Home Assistant whose registry doubles are plain mocks, and a
mock answers every attribute request on an instance -- so an instance
check would report the new API present everywhere and hand back a mock
in place of a device. Asking the type is also the more honest question:
what a registry can do is a property of the registry class.
"""
from __future__ import annotations

from typing import Any

from .const import DOMAIN

#: The release that first shipped the three replacement methods. Kept as
#: a constant because the report, the fallback and any future floor bump
#: all refer to the same number.
NEW_API_HA_VERSION = "2026.8.0"


def _registry_has(registry: Any, name: str) -> bool:
    """Does this registry's CLASS carry ``name``? (see module docstring)"""
    return hasattr(type(registry), name)


def hair_config_entry_id(hass: Any) -> str | None:
    """HAIR's own config entry id, or None when HAIR is not set up.

    ``hass.data[DOMAIN]`` is keyed by entry id (``__init__.py``), and
    HAIR is a hub integration with at most one entry per instance, which
    is the same assumption ``websocket_api._get_first_entry_data``
    already makes. Callers that hold an entry (a config entry object, or
    ``DeviceManager._config_entry_id``) pass theirs instead of asking.
    """
    entries = getattr(hass, "data", None)
    if not isinstance(entries, dict):
        return None
    domain_data = entries.get(DOMAIN)
    if not isinstance(domain_data, dict):
        return None
    for key, value in domain_data.items():
        if isinstance(value, dict) and "device_manager" in value:
            entry = value.get("config_entry")
            entry_id = getattr(entry, "entry_id", None)
            if isinstance(entry_id, str) and entry_id:
                return entry_id
            if isinstance(key, str) and key:
                return key
    return None


def device_by_identifier(
    registry: Any,
    identifier: tuple[str, str],
    config_entry_id: str | None,
) -> Any | None:
    """The device carrying ``identifier``, owned by ``config_entry_id``.

    Three answers, in order of how much the caller knows:

    1. The registry has the new API and the caller named an entry: the
       exact replacement call, scoped as Home Assistant intends.
    2. The registry has the new API and the entry is unknown (HAIR not
       set up yet, or a caller that genuinely cannot say): the plural
       call with no entry scope, first match. Same breadth the
       deprecated call had, without calling it.
    3. The registry predates 2026.8.0: the deprecated call, which is
       the only door those releases have.
    """
    if _registry_has(registry, "async_get_device_by_identifier"):
        if config_entry_id:
            return registry.async_get_device_by_identifier(
                identifier, config_entry_id
            )
        return _first(
            registry.async_get_devices(identifiers={identifier})
        )
    return registry.async_get_device(identifiers={identifier})


def device_by_connection(
    registry: Any,
    connection: tuple[str, str],
    config_entry_id: str | None,
) -> Any | None:
    """The device carrying ``connection``, owned by ``config_entry_id``.

    The connection half of :func:`device_by_identifier`, with the same
    three answers. Used for a device owned by ANOTHER integration's
    entry (the Broadlink blaster behind a pluck source), so the entry id
    passed here is that integration's, never HAIR's.
    """
    if _registry_has(registry, "async_get_device_by_connection"):
        if config_entry_id:
            return registry.async_get_device_by_connection(
                connection, config_entry_id
            )
        return _first(
            registry.async_get_devices(connections={connection})
        )
    return registry.async_get_device(connections={connection})


def _first(devices: Any) -> Any | None:
    """The first device of a plural lookup, or None.

    ``async_get_devices`` returns a list; an unscoped lookup can match
    more than one device across entries, and picking the first is what
    the deprecated call effectively did for HAIR's own identifiers.
    """
    if not devices:
        return None
    return next(iter(devices), None)
