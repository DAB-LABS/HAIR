"""Test fixtures for the HAIR integration."""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub the homeassistant.components.infrared module for test environments
# that run an older HA version without the 2026.4 infrared platform.
# The lazy imports in device_manager / signal_monitor will pick this up.
# ---------------------------------------------------------------------------
_INFRARED_MOD_NAME = "homeassistant.components.infrared"
if _INFRARED_MOD_NAME not in sys.modules or not hasattr(
    sys.modules[_INFRARED_MOD_NAME], "async_send_command"
):
    _fake_ir = types.ModuleType(_INFRARED_MOD_NAME)
    _fake_ir.async_send_command = AsyncMock()  # type: ignore[attr-defined]
    sys.modules[_INFRARED_MOD_NAME] = _fake_ir

from custom_components.hair.capture import MockCaptureProvider
from custom_components.hair.const import (
    CaptureProviderType,
    CommandCategory,
    CommandSource,
    DeviceType,
)
from custom_components.hair.models import (
    CaptureResult,
    EntityConfig,
    IRCommand,
    IRDevice,
)


@pytest.fixture
def capture_result() -> CaptureResult:
    return CaptureResult(
        protocol="NEC",
        code="0x20DF10EF",
        raw_timings=[9000, -4500, 560, -560, 560, -1690, 560, -560],
        frequency=38000,
        confidence=0.95,
    )


@pytest.fixture
def mock_capture_provider(capture_result: CaptureResult) -> MockCaptureProvider:
    return MockCaptureProvider(result=capture_result, delay=0.01)


@pytest.fixture
def mock_command() -> IRCommand:
    return IRCommand(
        id="cmd-1",
        name="Power",
        category=CommandCategory.POWER,
        source=CommandSource.CAPTURED,
        protocol="NEC",
        code="0x20DF10EF",
        raw_timings=[9000, -4500, 560, -560],
        frequency=38000,
    )


@pytest.fixture
def mock_device(mock_command: IRCommand) -> IRDevice:
    return IRDevice(
        id="test-device-1",
        name="Test TV",
        device_type=DeviceType.TV,
        manufacturer="Samsung",
        model="UN55TU7000",
        emitter_entity_ids=["infrared.test_emitter"],
        capture_device_id="esphome-device-1",
        capture_provider_type=CaptureProviderType.ESPHOME,
        commands=[mock_command],
        entity_config=EntityConfig(
            platform="media_player",
            command_mapping={"power_toggle": "Power"},
        ),
    )


@pytest.fixture
def fake_hass():
    """Minimal HA stub for unit tests that don't need a full instance.

    Replaces homeassistant.helpers.storage.Store interactions with
    in-memory storage so tests run quickly without a real config dir.
    """
    hass = MagicMock()
    hass.data = {}
    hass.config.components = set()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    hass.bus.async_fire = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=lambda: None)
    hass.services.async_call = AsyncMock()
    return hass
