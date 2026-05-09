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
from homeassistant.core import callback

from .capture import get_available_capture_providers
from .const import (
    CONF_CAPTURE_TIMEOUT,
    CONF_DEFAULT_REPEAT_COUNT,
    DEFAULT_CAPTURE_TIMEOUT,
    DEFAULT_REPEAT_COUNT,
    DOMAIN,
    MAX_CAPTURE_TIMEOUT,
    MIN_CAPTURE_TIMEOUT,
)

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

        if not emitters and not capture_providers:
            return self.async_abort(
                reason="no_ir_hardware",
                description_placeholders={
                    "setup_url": "https://hair.dev/setup-guide",
                },
            )

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "emitter_count": str(len(emitters)),
                    "capture_count": str(len(capture_providers)),
                },
            )

        return self.async_create_entry(
            title="IR Devices",
            data={},
            options={
                CONF_CAPTURE_TIMEOUT: DEFAULT_CAPTURE_TIMEOUT,
                CONF_DEFAULT_REPEAT_COUNT: DEFAULT_REPEAT_COUNT,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HAIROptionsFlow:
        return HAIROptionsFlow(config_entry)


class HAIROptionsFlow(config_entries.OptionsFlow):
    """Handle HAIR options (capture timeout, default repeat count)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CAPTURE_TIMEOUT,
                    default=options.get(
                        CONF_CAPTURE_TIMEOUT, DEFAULT_CAPTURE_TIMEOUT
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_CAPTURE_TIMEOUT, max=MAX_CAPTURE_TIMEOUT),
                ),
                vol.Required(
                    CONF_DEFAULT_REPEAT_COUNT,
                    default=options.get(
                        CONF_DEFAULT_REPEAT_COUNT, DEFAULT_REPEAT_COUNT
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
