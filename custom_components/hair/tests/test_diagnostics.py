"""Tests for HAIR diagnostics."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.diagnostics import (
    async_get_config_entry_diagnostics,
    REDACT_KEYS,
)
from custom_components.hair.const import (
    CommandCategory,
    CommandSource,
    CaptureProviderType,
    DeviceType,
    DOMAIN,
)
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice


def _device_with_command():
    cmd = IRCommand(
        id="cmd-1",
        name="Power",
        category=CommandCategory.POWER,
        source=CommandSource.CAPTURED,
        protocol="NEC",
        code="0xDEADBEEF",
        raw_timings=[9000, -4500, 560],
        frequency=38000,
    )
    return IRDevice(
        id="dev-1",
        name="Test TV",
        device_type=DeviceType.MEDIA_PLAYER,
        commands=[cmd],
        entity_config=EntityConfig(platform="media_player"),
    )


class TestDiagnostics:

    @pytest.mark.asyncio
    async def test_returns_entry_info(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test-entry"
        entry.options = {}
        entry.data = {}

        manager = MagicMock()
        manager.get_all_devices.return_value = []
        orchestrator = MagicMock()
        orchestrator.is_capturing = False

        hass.data = {DOMAIN: {entry.entry_id: {
            "device_manager": manager,
            "orchestrator": orchestrator,
        }}}

        result = await async_get_config_entry_diagnostics(hass, entry)
        assert result["entry"]["options"] == {}
        assert result["entry"]["data"] == {}
        assert result["devices"] == []
        assert result["is_capturing"] is False

    @pytest.mark.asyncio
    async def test_devices_serialized_and_redacted(self):
        """Verify devices are serialized and passed through async_redact_data."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test-entry"
        entry.options = {}
        entry.data = {}

        device = _device_with_command()
        manager = MagicMock()
        manager.get_all_devices.return_value = [device]
        orchestrator = MagicMock()
        orchestrator.is_capturing = False

        hass.data = {DOMAIN: {entry.entry_id: {
            "device_manager": manager,
            "orchestrator": orchestrator,
        }}}

        # Patch async_redact_data to verify it's called with REDACT_KEYS
        with patch(
            "custom_components.hair.diagnostics.async_redact_data",
            side_effect=lambda data, keys: {
                **data,
                **{k: "**REDACTED**" for k in keys if k in data},
                "commands": [
                    {**c, **{k: "**REDACTED**" for k in keys if k in c}}
                    for c in data.get("commands", [])
                ],
            },
        ) as mock_redact:
            result = await async_get_config_entry_diagnostics(hass, entry)

        assert len(result["devices"]) == 1
        mock_redact.assert_called_once()
        # Verify the call args: first arg is the device dict, second is REDACT_KEYS
        call_args = mock_redact.call_args
        assert call_args[0][1] is REDACT_KEYS
        # Verify the device dict has the expected structure
        device_dict = call_args[0][0]
        assert device_dict["name"] == "Test TV"
        assert device_dict["commands"][0]["code"] == "0xDEADBEEF"

    @pytest.mark.asyncio
    async def test_handles_unconfigured_gracefully(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "missing-entry"
        entry.options = {}
        entry.data = {}

        hass.data = {}

        result = await async_get_config_entry_diagnostics(hass, entry)
        assert result["devices"] == []
        assert result["is_capturing"] is False

    def test_redact_keys_includes_sensitive_fields(self):
        assert "raw_timings" in REDACT_KEYS
        assert "code" in REDACT_KEYS
