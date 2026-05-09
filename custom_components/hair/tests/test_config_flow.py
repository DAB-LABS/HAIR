"""Tests for the HAIR config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.config_flow import HAIRConfigFlow, HAIROptionsFlow
from custom_components.hair.const import (
    CONF_CAPTURE_TIMEOUT,
    CONF_DEFAULT_REPEAT_COUNT,
    DEFAULT_CAPTURE_TIMEOUT,
    DEFAULT_REPEAT_COUNT,
    DOMAIN,
    MAX_CAPTURE_TIMEOUT,
    MIN_CAPTURE_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flow(hass, existing_entries=None):
    """Create a HAIRConfigFlow wired to a fake hass."""
    flow = HAIRConfigFlow()
    flow.hass = hass
    flow._async_current_entries = MagicMock(return_value=existing_entries or [])
    flow.async_abort = MagicMock(
        side_effect=lambda reason, **kw: {"type": "abort", "reason": reason}
    )
    flow.async_show_form = MagicMock(
        side_effect=lambda **kw: {"type": "form", **kw}
    )
    flow.async_create_entry = MagicMock(
        side_effect=lambda **kw: {"type": "create_entry", **kw}
    )
    return flow


def _make_emitter(entity_id: str = "infrared.test_emitter"):
    """Create a fake HA state object that looks like an IR emitter."""
    state = MagicMock()
    state.entity_id = entity_id
    return state


# ---------------------------------------------------------------------------
# async_step_user tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abort_single_instance(fake_hass):
    """Second config entry should be rejected."""
    flow = _make_flow(fake_hass, existing_entries=[MagicMock()])
    result = await flow.async_step_user()
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.asyncio
async def test_shows_form_no_ir_hardware(fake_hass):
    """No emitters and no capture providers should still show the form."""
    fake_hass.states = MagicMock()
    fake_hass.states.async_all = MagicMock(return_value=[])
    fake_hass.config.components = set()
    fake_hass.config_entries.async_entries = MagicMock(return_value=[])

    flow = _make_flow(fake_hass)
    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["description_placeholders"]["emitter_count"] == "0"
    assert result["description_placeholders"]["capture_count"] == "0"


@pytest.mark.asyncio
async def test_shows_form_when_emitter_found(fake_hass):
    """When at least one emitter exists, show the confirmation form."""
    emitter = _make_emitter()
    fake_hass.states = MagicMock()
    fake_hass.states.async_all = MagicMock(return_value=[emitter])
    fake_hass.config.components = set()
    fake_hass.config_entries.async_entries = MagicMock(return_value=[])

    flow = _make_flow(fake_hass)
    result = await flow.async_step_user(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["description_placeholders"]["emitter_count"] == "1"


@pytest.mark.asyncio
async def test_shows_form_when_capture_provider_found(fake_hass):
    """Capture providers alone (even without emitters) should show the form."""
    fake_hass.states = MagicMock()
    fake_hass.states.async_all = MagicMock(return_value=[])
    fake_hass.config.components = {"esphome"}
    fake_hass.config_entries.async_entries = MagicMock(
        return_value=[MagicMock(entry_id="esp-entry-1")]
    )

    fake_device = MagicMock()
    fake_device.id = "esphome-dev-1"
    fake_device.name_by_user = None
    fake_device.name = "ESPHome IR"

    fake_entity = MagicMock()
    fake_entity.entity_id = "remote.esphome_ir"

    with patch(
        "custom_components.hair.capture.dr.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.capture.dr.async_entries_for_config_entry",
        return_value=[fake_device],
    ), patch(
        "custom_components.hair.capture.er.async_get",
        return_value=MagicMock(),
    ), patch(
        "custom_components.hair.capture.er.async_entries_for_device",
        return_value=[fake_entity],
    ):
        flow = _make_flow(fake_hass)
        result = await flow.async_step_user(user_input=None)
    assert result["type"] == "form"
    assert result["description_placeholders"]["capture_count"] == "1"


@pytest.mark.asyncio
async def test_creates_entry_on_submit(fake_hass):
    """Submitting the form (user_input != None) should create the entry."""
    emitter = _make_emitter()
    fake_hass.states = MagicMock()
    fake_hass.states.async_all = MagicMock(return_value=[emitter])
    fake_hass.config.components = set()
    fake_hass.config_entries.async_entries = MagicMock(return_value=[])

    flow = _make_flow(fake_hass)
    result = await flow.async_step_user(user_input={})
    assert result["type"] == "create_entry"
    assert result["title"] == "IR Devices"
    assert result["data"] == {}
    assert result["options"][CONF_CAPTURE_TIMEOUT] == DEFAULT_CAPTURE_TIMEOUT
    assert result["options"][CONF_DEFAULT_REPEAT_COUNT] == DEFAULT_REPEAT_COUNT


# ---------------------------------------------------------------------------
# Options flow tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_options_flow_shows_form():
    """Options flow should show a form with current values as defaults."""
    entry = MagicMock()
    entry.options = {
        CONF_CAPTURE_TIMEOUT: 20,
        CONF_DEFAULT_REPEAT_COUNT: 3,
    }
    flow = HAIROptionsFlow(entry)
    flow.async_show_form = MagicMock(
        side_effect=lambda **kw: {"type": "form", **kw}
    )
    flow.async_create_entry = MagicMock(
        side_effect=lambda **kw: {"type": "create_entry", **kw}
    )
    result = await flow.async_step_init(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_saves_input():
    """Submitting options should create an entry with the user values."""
    entry = MagicMock()
    entry.options = {}
    flow = HAIROptionsFlow(entry)
    flow.async_create_entry = MagicMock(
        side_effect=lambda **kw: {"type": "create_entry", **kw}
    )
    result = await flow.async_step_init(
        user_input={CONF_CAPTURE_TIMEOUT: 30, CONF_DEFAULT_REPEAT_COUNT: 2}
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_CAPTURE_TIMEOUT] == 30
    assert result["data"][CONF_DEFAULT_REPEAT_COUNT] == 2
