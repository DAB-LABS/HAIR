"""The IR receiving hardware HAIR can hear, for the Devices tab and setup.

Two kinds of hardware, as the Devices tab's Receivers and Proxies cards
and the config flow's summary count them:

1. **Native (HA 2026.6+):** every ``InfraredReceiverEntity`` on HA's
   infrared platform, which HAIR hears through
   ``infrared.async_subscribe_receiver``.
2. **ESPHome bridge (legacy):** ESPHome devices seen forwarding
   ``esphome.remote_received`` events this session.

This used to be ``capture.py``'s ``get_available_capture_providers``,
beside the capture provider classes the Learn dialog drove. The dialog
and the providers are gone (windowed receivers, round 3, owner ruling
2026-10-18); the discovery stayed, because the Devices cards and the
config flow have always been its real readers, and moved here under a
name that says what it does.

A Broadlink is a receiver only through an integration that gives it an
infrared receiver entity, such as BroadSniff (DAB-LABS/broadsniff); the
built-in Broadlink integration sends only. A receiver that listens only
while a capture window is open is a capture device, which is
``receiver_window.py``'s business, not discovery's: it is found here
like any other native receiver.
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, ReceiverHardwareType


def _get_bridge_active_device_ids(hass: HomeAssistant) -> set[str]:
    """Return HA device IDs whose ESPHome bridge has fired events this session.

    Looks up the active ``SignalMonitor`` instance via ``hass.data`` and
    returns its bridge-tracking set. Returns an empty set if HAIR isn't
    fully set up yet (e.g. during config flow), so callers can iterate
    without needing a None check.
    """
    entries = hass.data.get(DOMAIN, {})
    for value in entries.values():
        if not isinstance(value, dict):
            continue
        monitor = value.get("signal_monitor")
        if monitor is not None and hasattr(monitor, "bridge_active_device_ids"):
            return set(monitor.bridge_active_device_ids)
    return set()


def _has_ir_entities(ent_registry: Any, device_id: str) -> bool:
    """Return True if the device has IR-related entities.

    Checks for ``infrared.*`` entities (ESPHome ``ir_rf_proxy``) or
    ``remote.*`` entities as a fallback.  Non-IR ESPHome devices
    (sensors, switches, lights, etc.) are excluded.
    """
    entities = er.async_entries_for_device(ent_registry, device_id)
    for entity in entities:
        entity_id = entity.entity_id if hasattr(entity, "entity_id") else str(entity)
        if entity_id.startswith("infrared.") or entity_id.startswith("remote."):
            return True
    return False


async def list_receiver_hardware(hass: HomeAssistant) -> list[dict[str, Any]]:
    """The receiving hardware, as lightweight dicts for the websocket.

    On HA 2026.6+, native ``InfraredReceiverEntity`` instances come
    first, then ESPHome devices seen on the legacy event-bus bridge.
    """
    hardware: list[dict[str, Any]] = []

    # Native receivers (HA 2026.6+).
    try:
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
        )

        from .receiver_filter import is_rf_receiver

        receivers = async_get_receivers(hass)
        for entity_id in receivers:
            if is_rf_receiver(hass, entity_id):
                # GH #72: RF proxy receivers on the infrared platform
                # are never subscribed, so never offer them either.
                continue
            state = hass.states.get(entity_id)
            name = entity_id
            if state is not None:
                name = state.attributes.get("friendly_name", entity_id)
            hardware.append(
                {
                    "type": str(ReceiverHardwareType.NATIVE),
                    "device_id": entity_id,
                    "name": str(name),
                    "config_entry_id": None,
                    "receiver_entity_id": entity_id,
                }
            )
    except (ImportError, AttributeError):
        pass  # Pre-2026.6: no native receiver API.

    # ESPHome devices via the legacy event-bus bridge.
    #
    # We can't introspect a device's YAML to know whether ``on_pronto:``
    # is configured, so the only reliable signal is "have we seen an
    # ``esphome.remote_received`` event from this device this session?"
    # The signal monitor records that set; we surface bridge hardware
    # only for those devices. This means: after HA restart, the bridge
    # badge stays hidden until the user presses a button on a remote
    # whose ESPHome host actually forwards events. That trade-off is
    # acceptable -- the badge is informational, and once a bridge is
    # detected it stays surfaced for the rest of the HA session.
    bridge_active_device_ids = _get_bridge_active_device_ids(hass)
    if "esphome" in hass.config.components and bridge_active_device_ids:
        dev_registry = dr.async_get(hass)
        ent_registry = er.async_get(hass)
        for entry in hass.config_entries.async_entries("esphome"):
            for device in dr.async_entries_for_config_entry(
                dev_registry, entry.entry_id
            ):
                if device.id not in bridge_active_device_ids:
                    continue
                if not _has_ir_entities(ent_registry, device.id):
                    continue
                hardware.append(
                    {
                        "type": str(ReceiverHardwareType.ESPHOME),
                        "device_id": device.id,
                        "name": device.name_by_user
                        or device.name
                        or "ESPHome IR device",
                        "config_entry_id": entry.entry_id,
                    }
                )

    return hardware
