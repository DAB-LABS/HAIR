"""Tests for the HAIR config flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.config_flow import HAIRConfigFlow

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


def _make_emitter(entity_id: str = "infrared.test_emitter", friendly_name: str | None = None):
    """Create a fake HA state object that looks like an IR emitter."""
    state = MagicMock()
    state.entity_id = entity_id
    state.attributes = {"friendly_name": friendly_name or entity_id}
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
    assert "infrared.test_emitter" in result["description_placeholders"]["hardware_summary"]


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

    fake_ir_entity = MagicMock()
    fake_ir_entity.entity_id = "infrared.hair1_tx"

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
        return_value=[fake_ir_entity],
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
    assert result["title"] == "HAIR"
    assert result["data"] == {}
