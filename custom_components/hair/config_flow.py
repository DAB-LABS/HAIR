"""Config flow for the HAIR integration.

HAIR is a hub integration: a single config entry hosts all IR devices.
The user-facing "add a device" experience lives in the admin panel; the
config flow is just a one-time initial setup that:

1. Detects available IR hardware (emitters via the native infrared
   platform, capture-capable devices via the native receiver API or the
   ESPHome event-bus bridge).
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
from .const import DOMAIN, TWEEZER_OBSERVER_ATTR

_LOGGER = logging.getLogger(__name__)


async def _async_get_emitters(hass) -> list:
    """Best-effort lookup of native IR emitters.

    Returns a list of state objects in domain ``infrared``. The native
    HA infrared platform (2026.4+) registers emitters as entities.

    On HA 2026.6+, receiver entities also live in the ``infrared``
    domain.  We filter those out by checking against the native
    receiver list when available.
    """
    # Exclude HAIR's own observer emitter (the Tweezer): it is an internal
    # capture target for the Plucker, never a user-selectable TX emitter.
    all_infrared = [
        s
        for s in hass.states.async_all("infrared")
        if not s.attributes.get(TWEEZER_OBSERVER_ATTR)
    ]
    receiver_ids = await _async_get_native_receivers(hass)
    if not receiver_ids:
        return all_infrared
    # Exclude receiver entities from the emitter list.
    return [s for s in all_infrared if s.entity_id not in receiver_ids]


async def _async_get_native_receivers(hass) -> set[str]:
    """Best-effort lookup of native IR receiver entity IDs.

    Returns an empty set on HA < 2026.6 or if no receivers are found.
    """
    try:
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
        )
        receivers = async_get_receivers(hass)
        return set(receivers) if receivers else set()
    except (ImportError, AttributeError):
        return set()


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
        native_receivers = await _async_get_native_receivers(self.hass)

        if user_input is None:
            emitter_names = [
                s.attributes.get("friendly_name", s.entity_id)
                for s in emitters
            ]
            capture_names = [p["name"] for p in capture_providers]
            # Add native receivers not already in capture_names.
            for entity_id in native_receivers:
                state = self.hass.states.get(entity_id)
                name = (
                    state.attributes.get("friendly_name", entity_id)
                    if state
                    else entity_id
                )
                if name not in capture_names:
                    capture_names.append(name)
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
