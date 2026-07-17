"""Diagnostics for the HAIR integration."""
from __future__ import annotations

import importlib.metadata
from collections import Counter
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .protocol_decode import registered_protocols

REDACT_KEYS = {"raw_timings", "code"}


def _infrared_protocols_version() -> str:
    """Installed infrared-protocols version, or 'unavailable'."""
    try:
        return importlib.metadata.version("infrared-protocols")
    except Exception:  # never let diagnostics raise on a missing library
        return "unavailable"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    manager = data.get("device_manager")
    orchestrator = data.get("orchestrator")

    devices: list[dict[str, Any]] = []
    decoded_total = 0
    decoded_by_protocol: Counter[str] = Counter()
    if manager is not None:
        for device in manager.get_all_devices():
            devices.append(async_redact_data(device.to_dict(), REDACT_KEYS))
            for cmd in device.commands:
                if cmd.decoded_protocol:
                    decoded_total += 1
                    decoded_by_protocol[cmd.decoded_protocol] += 1

    # importlib.metadata.version reads the package dist-info from disk, so it
    # is offloaded to the executor rather than run on the event loop.
    version = await hass.async_add_executor_job(_infrared_protocols_version)

    return {
        "entry": {
            "options": dict(entry.options),
            "data": dict(entry.data),
        },
        "devices": devices,
        "is_capturing": getattr(orchestrator, "is_capturing", False),
        "infrared_protocols_version": version,
        "protocol_registry": registered_protocols(),
        "decoded_commands": {
            "total": decoded_total,
            "by_protocol": dict(decoded_by_protocol),
        },
    }
