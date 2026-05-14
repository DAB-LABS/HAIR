"""Config flow for the HAIR integration.

HAIR is a hub integration: a single config entry hosts all IR devices.
The user-facing "add a device" experience lives in the admin panel; the
config flow is just a one-time initial setup that:

1. Detects available IR hardware (emitters via the native infrared
   platform, capture-capable devices via ESPHome / Broadlink integrations).
2. Aborts gracefully when nothing is found and points the user at the
   setup guide.
3. Creates the singleton config entry once hardware is present.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .capture import get_available_capture_providers
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _async_get_emitters(hass) -> list:
    """Best-effort lookup of native IR emitters.

    Returns a list of state objects in domain ``infrared``. The native
    HA infrared platform (2026.4+) registers emitters as entities.
    """
    return [
        state for state in hass.states.async_all("infrared")
    ]


class HAIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the HAIR setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initial step: detect hardware, then create the singleton entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        emitters = await _async_get_emitters(self.hass)
        capture_providers = await get_available_capture_providers(self.hass)

        if user_input is None:
            emitter_names = [
                s.attributes.get("friendly_name", s.entity_id)
                for s in emitters
            ]
            capture_names = [p["name"] for p in capture_providers]
            hw_lines: list[str] = []
            if emitter_names:
                hw_lines.append(f"**Emitters:** {', '.join(emitter_names)}")
            if capture_names:
                hw_lines.append(f"**Receivers:** {', '.join(capture_names)}")
            hw_summary = "\n\n".join(hw_lines) if hw_lines else "_No hardware detected yet._"

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "emitter_count": str(len(emitters)),
                    "capture_count": str(len(capture_providers)),
                    "hardware_summary": hw_summary,
                },
            )

        return self.async_create_entry(
            title="HAIR",
            data={},
        )
