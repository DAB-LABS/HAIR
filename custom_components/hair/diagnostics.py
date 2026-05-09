"""Diagnostics for the HAIR integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACT_KEYS = {"raw_timings", "code"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    manager = data.get("device_manager")
    orchestrator = data.get("orchestrator")

    devices: list[dict[str, Any]] = []
    if manager is not None:
        for device in manager.get_all_devices():
            devices.append(async_redact_data(device.to_dict(), REDACT_KEYS))

    return {
        "entry": {
            "options": dict(entry.options),
            "data": dict(entry.data),
        },
        "devices": devices,
        "is_capturing": getattr(orchestrator, "is_capturing", False),
    }
