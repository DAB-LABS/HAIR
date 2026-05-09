# HAIR — Code Architecture Document

**Author:** David Bailey
**Date:** 2026-05-08
**Version:** 1.0
**Status:** Approved by Trio Review Board

---

## Table of Contents

1. File & Folder Structure
2. manifest.json
3. Constants & Enums
4. Data Models
5. Storage Layer
6. Config Flow
7. CaptureProvider Abstraction
8. Capture Orchestrator
9. Device Manager
10. Entity Factory
11. Entity Platforms
12. WebSocket API
13. Frontend Components
14. strings.json Structure
15. Integration Setup
16. Testing Architecture

---

## 1. File & Folder Structure

```
custom_components/hair/
├── __init__.py                     # Integration setup, platform forwarding, panel registration
├── manifest.json                   # Integration metadata
├── const.py                        # All constants, enums, defaults
├── config_flow.py                  # Config flow + options flow handlers
├── models.py                       # Dataclass definitions (IRDevice, IRCommand, etc.)
├── storage.py                      # HAIRStore — persistent storage with migration
├── device_manager.py               # DeviceManager — device/command CRUD
├── capture.py                      # CaptureProvider ABC + implementations
├── capture_orchestrator.py         # CaptureOrchestrator — session management + locking
├── entity_factory.py               # EntityFactory — creates HA entities from IR devices
├── command_templates.py            # Command templates per device type
├── websocket_api.py                # WebSocket command handlers
├── remote.py                       # Remote entity platform
├── media_player.py                 # Media player entity platform
├── climate.py                      # Climate entity platform
├── fan.py                          # Fan entity platform
├── diagnostics.py                  # Diagnostics data provider
├── icons.json                      # Custom entity icons
├── strings.json                    # UI strings (English)
├── translations/
│   └── en.json                     # English translations (mirrors strings.json)
├── frontend/
│   ├── src/
│   │   ├── ha-panel-ir-devices.ts      # Main panel entry point
│   │   ├── ir-device-list.ts           # Device list view
│   │   ├── ir-device-detail.ts         # Device detail + command checklist
│   │   ├── ir-capture-dialog.ts        # Capture dialog (2-phase)
│   │   ├── ir-command-row.ts           # Single command row component
│   │   ├── ir-progress-bar.ts          # Setup progress bar
│   │   └── types.ts                    # TypeScript type definitions
│   ├── rollup.config.mjs              # Build config
│   ├── package.json                    # Frontend dependencies
│   └── dist/
│       └── ha-panel-ir-devices.js      # Bundled output (committed)
└── tests/
    ├── conftest.py                     # Test fixtures
    ├── test_config_flow.py             # Config flow tests
    ├── test_storage.py                 # Storage + migration tests
    ├── test_device_manager.py          # Device CRUD tests
    ├── test_capture.py                 # Capture provider tests
    ├── test_capture_orchestrator.py    # Orchestrator + locking tests
    ├── test_entity_factory.py          # Entity creation tests
    ├── test_remote.py                  # Remote entity tests
    ├── test_media_player.py            # Media player entity tests
    ├── test_climate.py                 # Climate entity tests
    ├── test_fan.py                     # Fan entity tests
    ├── test_websocket_api.py           # WebSocket handler tests
    └── mock_capture_provider.py        # MockCaptureProvider for testing
```

---

## 2. manifest.json

```json
{
    "domain": "hair",
    "name": "HAIR - IR Device Manager",
    "version": "0.1.0",
    "documentation": "https://github.com/dbailey/hair",
    "issue_tracker": "https://github.com/dbailey/hair/issues",
    "dependencies": ["infrared"],
    "after_dependencies": ["esphome", "broadlink"],
    "codeowners": ["@dbailey"],
    "config_flow": true,
    "iot_class": "local_push",
    "integration_type": "hub",
    "requirements": [],
    "quality_scale": "silver",
    "loggers": ["custom_components.hair"]
}
```

### Key Decisions
- `domain`: `hair` (short, memorable, matches repo name)
- `dependencies`: `["infrared"]` — hard dependency on HA's IR platform
- `after_dependencies`: `["esphome", "broadlink"]` — soft deps for capture providers
- `integration_type`: `"hub"` — manages multiple sub-devices
- `iot_class`: `"local_push"` — local communication, event-driven capture
- `requirements`: Empty — no pip packages needed

---

## 3. Constants & Enums (`const.py`)

```python
"""Constants for the HAIR integration."""
from enum import StrEnum

# Integration identifiers
DOMAIN = "hair"
STORAGE_KEY = "hair_devices"
STORAGE_VERSION = 1
STORAGE_VERSION_MINOR = 1

# Config flow
CONF_EMITTER_ENTITY_ID = "emitter_entity_id"
CONF_CAPTURE_DEVICE_ID = "capture_device_id"
CONF_CAPTURE_PROVIDER_TYPE = "capture_provider_type"
CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_NAME = "device_name"
CONF_MANUFACTURER = "manufacturer"
CONF_MODEL = "model"

# Defaults
DEFAULT_CAPTURE_TIMEOUT = 15  # seconds
DEFAULT_CARRIER_FREQUENCY = 38000  # Hz
DEFAULT_REPEAT_COUNT = 1
MIN_CAPTURE_TIMEOUT = 5
MAX_CAPTURE_TIMEOUT = 60

# Platforms to set up
PLATFORMS = ["remote", "media_player", "climate", "fan"]

# Panel
PANEL_URL = "ir-devices"
PANEL_TITLE = "IR Devices"
PANEL_ICON = "mdi:remote"

# WebSocket command prefix
WS_PREFIX = "hair"

# Events
EVENT_COMMAND_CAPTURED = f"{DOMAIN}_command_captured"
EVENT_CAPTURE_TIMEOUT = f"{DOMAIN}_capture_timeout"
EVENT_CAPTURE_ERROR = f"{DOMAIN}_capture_error"


class DeviceType(StrEnum):
    """IR device types."""
    TV = "tv"
    AC = "ac"
    FAN = "fan"
    SOUNDBAR = "soundbar"
    PROJECTOR = "projector"
    OTHER = "other"


class CommandCategory(StrEnum):
    """IR command categories."""
    POWER = "power"
    VOLUME = "volume"
    CHANNEL = "channel"
    NAVIGATION = "navigation"
    MODE = "mode"
    TEMPERATURE = "temperature"
    FAN_SPEED = "fan_speed"
    CUSTOM = "custom"


class CommandSource(StrEnum):
    """How a command was obtained."""
    CAPTURED = "captured"
    DATABASE = "database"
    IMPORTED = "imported"


class CaptureProviderType(StrEnum):
    """Capture provider types."""
    ESPHOME = "esphome"
    BROADLINK = "broadlink"
    MOCK = "mock"  # For testing


class CaptureState(StrEnum):
    """States of a capture session."""
    IDLE = "idle"
    LISTENING = "listening"
    CAPTURED = "captured"
    TIMEOUT = "timeout"
    ERROR = "error"
```

---

## 4. Data Models (`models.py`)

```python
"""Data models for HAIR integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from .const import (
    CommandCategory,
    CommandSource,
    CaptureProviderType,
    DEFAULT_CARRIER_FREQUENCY,
    DEFAULT_REPEAT_COUNT,
    DeviceType,
)


def _new_id() -> str:
    return str(uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IRCommand:
    """A single IR command (learned or imported)."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    category: CommandCategory = CommandCategory.CUSTOM
    source: CommandSource = CommandSource.CAPTURED
    protocol: str | None = None
    code: str | None = None
    raw_timings: list[int] | None = None
    frequency: int = DEFAULT_CARRIER_FREQUENCY
    repeat_count: int = DEFAULT_REPEAT_COUNT
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> IRCommand:
        """Deserialize from dictionary."""
        ...


@dataclass
class CommandTemplate:
    """Template for a suggested command during device setup."""

    name: str
    category: CommandCategory
    essential: bool = True


@dataclass
class EntityConfig:
    """Configuration for the HA entity created from an IR device."""

    platform: str = "remote"  # "remote" | "media_player" | "climate" | "fan"
    command_mapping: dict[str, str] = field(default_factory=dict)
    # Climate-specific
    temperature_presets: list[int] | None = None
    hvac_modes: list[str] | None = None
    fan_modes: list[str] | None = None
    swing_modes: list[str] | None = None

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> EntityConfig: ...


@dataclass
class IRDevice:
    """An IR-controlled device managed by HAIR."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    device_type: DeviceType = DeviceType.OTHER
    manufacturer: str | None = None
    model: str | None = None
    emitter_entity_id: str = ""
    capture_device_id: str | None = None  # May differ from emitter
    capture_provider_type: CaptureProviderType = CaptureProviderType.ESPHOME
    commands: list[IRCommand] = field(default_factory=list)
    entity_config: EntityConfig = field(default_factory=EntityConfig)
    database_id: str | None = None  # Future: community code database
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def get_command(self, command_id: str) -> IRCommand | None:
        """Find a command by ID."""
        ...

    def get_command_by_name(self, name: str) -> IRCommand | None:
        """Find a command by name (case-insensitive)."""
        ...

    def add_command(self, command: IRCommand) -> None:
        """Add a command to this device."""
        ...

    def remove_command(self, command_id: str) -> bool:
        """Remove a command by ID. Returns True if found."""
        ...

    def replace_command(self, command_id: str, new_command: IRCommand) -> bool:
        """Replace a command (re-learn). Returns True if found."""
        ...

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> IRDevice: ...


@dataclass
class CaptureResult:
    """Result from a capture provider."""

    protocol: str | None = None
    code: str | None = None
    raw_timings: list[int] = field(default_factory=list)
    frequency: int = DEFAULT_CARRIER_FREQUENCY
    confidence: float = 1.0

    def matches(self, other: CaptureResult, tolerance: float = 0.1) -> bool:
        """Check if two captures are the same signal (for duplicate detection)."""
        ...

    def to_command(self, name: str, category: CommandCategory) -> IRCommand:
        """Convert capture result to a storable IRCommand."""
        ...


@dataclass
class CaptureSession:
    """Active capture session state."""

    session_id: str = field(default_factory=_new_id)
    device_id: str = ""
    provider_type: CaptureProviderType = CaptureProviderType.ESPHOME
    state: str = "idle"  # CaptureState
    started_at: str = field(default_factory=_now_iso)
    result: CaptureResult | None = None
```

---

## 5. Storage Layer (`storage.py`)

```python
"""Persistent storage for HAIR integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION, STORAGE_VERSION_MINOR
from .models import IRDevice


class HAIRStore:
    """Manages persistent storage of IR devices and commands."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            minor_version=STORAGE_VERSION_MINOR,
        )
        self._data: dict[str, IRDevice] = {}

    async def async_load(self) -> None:
        """Load data from storage."""
        ...

    async def async_save(self) -> None:
        """Save current data to storage."""
        ...

    async def _async_migrate(
        self, old_major: int, old_minor: int, data: dict
    ) -> dict:
        """Migrate storage schema between versions."""
        ...

    # Device operations
    def get_device(self, device_id: str) -> IRDevice | None: ...
    def get_all_devices(self) -> list[IRDevice]: ...
    def add_device(self, device: IRDevice) -> None: ...
    def update_device(self, device: IRDevice) -> None: ...
    def remove_device(self, device_id: str) -> bool: ...

    # Convenience
    def get_devices_by_emitter(self, emitter_entity_id: str) -> list[IRDevice]: ...
    def get_devices_by_type(self, device_type: str) -> list[IRDevice]: ...
```

---

## 6. Config Flow (`config_flow.py`)

```python
"""Config flow for HAIR integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import infrared
from homeassistant.core import callback

from .const import (
    CONF_CAPTURE_DEVICE_ID,
    CONF_CAPTURE_PROVIDER_TYPE,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_EMITTER_ENTITY_ID,
    CONF_MANUFACTURER,
    CONF_MODEL,
    DOMAIN,
    DeviceType,
)
from .capture import get_available_capture_providers


class HAIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAIR."""

    VERSION = 1

    def __init__(self) -> None:
        self._emitters: list = []
        self._capture_providers: list = []
        self._device_type: str = ""
        self._emitter_entity_id: str = ""
        self._capture_device_id: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Auto-detect IR hardware, select device type."""
        ...

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Select device type (TV, AC, Fan, etc.)."""
        ...

    async def async_step_device_details(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 3: Name, brand, model, emitter/capture device selection."""
        ...

    async def async_step_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 4: Create entry and redirect to panel."""
        ...

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HAIROptionsFlow:
        """Get options flow handler."""
        return HAIROptionsFlow(config_entry)


class HAIROptionsFlow(config_entries.OptionsFlow):
    """Handle HAIR options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options: default emitter, capture timeout, etc."""
        ...
```

---

## 7. CaptureProvider Abstraction (`capture.py`)

```python
"""IR capture provider abstraction and implementations."""
from __future__ import annotations

from abc import ABC, abstractmethod

from homeassistant.core import HomeAssistant

from .const import CaptureProviderType
from .models import CaptureResult


class CaptureProvider(ABC):
    """Abstract base class for IR signal capture."""

    @property
    @abstractmethod
    def provider_type(self) -> CaptureProviderType: ...

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Human-readable name of the capture device."""
        ...

    @abstractmethod
    async def async_start_capture(self, timeout: int = 15) -> None:
        """Enter learning/listening mode."""
        ...

    @abstractmethod
    async def async_stop_capture(self) -> None:
        """Exit learning mode and clean up."""
        ...

    @abstractmethod
    async def async_wait_for_signal(self) -> CaptureResult | None:
        """Block until signal received or timeout. Returns None on timeout."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if capture hardware is ready."""
        ...


class ESPHomeCaptureProvider(CaptureProvider):
    """Capture IR signals via ESPHome remote_receiver."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        device_id: str,
    ) -> None: ...

    @property
    def provider_type(self) -> CaptureProviderType:
        return CaptureProviderType.ESPHOME

    @property
    def device_name(self) -> str: ...

    async def async_start_capture(self, timeout: int = 15) -> None:
        """Subscribe to ESPHome IR receiver events via native API."""
        ...

    async def async_wait_for_signal(self) -> CaptureResult | None:
        """Wait for IR event. Decode protocol if recognized."""
        ...

    async def async_stop_capture(self) -> None:
        """Unsubscribe from ESPHome events."""
        ...

    def is_available(self) -> bool:
        """Check ESPHome device connection state."""
        ...


class BroadlinkCaptureProvider(CaptureProvider):
    """Capture IR signals via Broadlink learning mode."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        device,  # broadlink.Device
    ) -> None: ...

    @property
    def provider_type(self) -> CaptureProviderType:
        return CaptureProviderType.BROADLINK

    @property
    def device_name(self) -> str: ...

    async def async_start_capture(self, timeout: int = 15) -> None:
        """Call device.enter_learning_mode()."""
        ...

    async def async_wait_for_signal(self) -> CaptureResult | None:
        """Poll device.check_data() until signal received or timeout."""
        ...

    async def async_stop_capture(self) -> None:
        """Cancel learning mode if active."""
        ...

    def is_available(self) -> bool:
        """Check Broadlink device is connected."""
        ...


class MockCaptureProvider(CaptureProvider):
    """Mock provider for testing."""

    def __init__(
        self,
        result: CaptureResult | None = None,
        delay: float = 0.5,
        fail: bool = False,
    ) -> None: ...

    @property
    def provider_type(self) -> CaptureProviderType:
        return CaptureProviderType.MOCK

    # ... implementations that return preconfigured results


# Discovery functions

async def get_available_capture_providers(
    hass: HomeAssistant,
) -> list[CaptureProvider]:
    """Discover all available capture-capable devices."""
    ...

async def get_capture_provider_for_device(
    hass: HomeAssistant,
    provider_type: CaptureProviderType,
    device_id: str,
) -> CaptureProvider | None:
    """Get a specific capture provider by type and device."""
    ...
```

---

## 8. Capture Orchestrator (`capture_orchestrator.py`)

```python
"""Capture session orchestration with resource locking."""
from __future__ import annotations

import asyncio
from typing import Callable

from homeassistant.core import HomeAssistant

from .capture import CaptureProvider
from .const import CaptureState
from .models import CaptureResult, CaptureSession, IRCommand, IRDevice


class CaptureInProgressError(Exception):
    """Raised when a capture session is already active."""


class CaptureOrchestrator:
    """Manages IR capture sessions with resource locking and event streaming."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._lock = asyncio.Lock()
        self._active_session: CaptureSession | None = None
        self._listeners: dict[str, list[Callable]] = {}

    @property
    def is_capturing(self) -> bool:
        """Check if a capture session is active."""
        return self._lock.locked()

    async def start_capture(
        self,
        provider: CaptureProvider,
        device_id: str,
        timeout: int = 15,
    ) -> CaptureSession:
        """Start a new capture session. Raises CaptureInProgressError if locked."""
        ...

    async def cancel_capture(self, session_id: str) -> None:
        """Cancel an active capture session."""
        ...

    def subscribe(
        self,
        session_id: str,
        callback: Callable[[CaptureState, CaptureResult | None], None],
    ) -> Callable[[], None]:
        """Subscribe to capture events. Returns unsubscribe function."""
        ...

    async def _capture_loop(
        self,
        session: CaptureSession,
        provider: CaptureProvider,
        timeout: int,
    ) -> None:
        """Internal capture loop running in background task."""
        ...

    def check_duplicate(
        self,
        device: IRDevice,
        result: CaptureResult,
    ) -> IRCommand | None:
        """Check if captured signal matches an existing command. Returns match or None."""
        ...
```

---

## 9. Device Manager (`device_manager.py`)

```python
"""Device CRUD and entity lifecycle management."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .entity_factory import EntityFactory
from .models import IRCommand, IRDevice
from .storage import HAIRStore


class DeviceManager:
    """Manages IR device lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HAIRStore,
        entity_factory: EntityFactory,
    ) -> None:
        self._hass = hass
        self._store = store
        self._entity_factory = entity_factory

    async def async_create_device(self, device: IRDevice) -> IRDevice:
        """Create a new IR device, register in HA device registry, create entities."""
        ...

    async def async_update_device(self, device: IRDevice) -> IRDevice:
        """Update device metadata."""
        ...

    async def async_remove_device(self, device_id: str) -> bool:
        """Remove device, cleanup entities and device registry."""
        ...

    async def async_add_command(
        self, device_id: str, command: IRCommand
    ) -> IRCommand:
        """Add a captured command to a device, update entity mappings."""
        ...

    async def async_remove_command(
        self, device_id: str, command_id: str
    ) -> bool:
        """Remove a command from a device."""
        ...

    async def async_replace_command(
        self, device_id: str, command_id: str, new_command: IRCommand
    ) -> bool:
        """Replace a command (re-learn)."""
        ...

    async def async_send_command(
        self, device_id: str, command_id: str
    ) -> None:
        """Send a stored IR command via the emitter."""
        ...

    def _register_ha_device(self, device: IRDevice) -> None:
        """Register/update device in HA device registry."""
        ...

    def _auto_map_command(self, device: IRDevice, command: IRCommand) -> None:
        """Auto-map a captured command to entity features based on name/category."""
        ...

    def get_device(self, device_id: str) -> IRDevice | None: ...
    def get_all_devices(self) -> list[IRDevice]: ...
```

---

## 10. Entity Factory (`entity_factory.py`)

```python
"""Factory for creating HA entities from IR device profiles."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DeviceType
from .models import IRDevice


DEVICE_TYPE_TO_PLATFORM: dict[str, str] = {
    DeviceType.TV: "media_player",
    DeviceType.SOUNDBAR: "media_player",
    DeviceType.AC: "climate",
    DeviceType.FAN: "fan",
    DeviceType.PROJECTOR: "media_player",
    DeviceType.OTHER: "remote",
}


class EntityFactory:
    """Creates and manages HA entities for IR devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._add_entity_callbacks: dict[str, AddEntitiesCallback] = {}

    def register_platform(
        self, platform: str, async_add_entities: AddEntitiesCallback
    ) -> None:
        """Register entity addition callback for a platform."""
        ...

    async def async_create_entities(self, device: IRDevice) -> None:
        """Create HA entities for an IR device based on its type."""
        ...

    async def async_remove_entities(self, device_id: str) -> None:
        """Remove all entities associated with a device."""
        ...

    async def async_update_entities(self, device: IRDevice) -> None:
        """Update entity capabilities based on current commands."""
        ...

    def get_platform_for_device(self, device: IRDevice) -> str:
        """Determine which entity platform to use for a device type."""
        return DEVICE_TYPE_TO_PLATFORM.get(
            device.device_type, "remote"
        )
```

---

## 11. Entity Platforms

### Remote Entity (`remote.py`)

```python
"""Remote entity platform for HAIR."""
from __future__ import annotations

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import IRDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAIR remote entities."""
    ...


class HAIRRemoteEntity(RemoteEntity):
    """IR remote entity managed by HAIR."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: IRDevice) -> None:
        self._device = device
        self._attr_unique_id = f"hair_{device.id}_remote"
        self._attr_name = "Remote"
        self._is_on = True  # Assumed state

    @property
    def device_info(self) -> dict:
        """Return device info for device registry."""
        ...

    @property
    def is_on(self) -> bool:
        """Return assumed on state."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Send power on command."""
        ...

    async def async_turn_off(self, **kwargs) -> None:
        """Send power off command."""
        ...

    async def async_send_command(self, command: list[str], **kwargs) -> None:
        """Send IR commands by name."""
        ...

    @property
    def extra_state_attributes(self) -> dict:
        """Return available commands as attribute."""
        ...
```

### Media Player Entity (`media_player.py`)

```python
"""Media player entity platform for HAIR."""
from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import IRDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None: ...


class HAIRMediaPlayerEntity(MediaPlayerEntity):
    """IR-controlled media player."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True  # IR is one-directional

    def __init__(self, device: IRDevice) -> None:
        self._device = device
        self._attr_unique_id = f"hair_{device.id}_media_player"
        self._attr_name = None  # Uses device name
        self._state = MediaPlayerState.ON
        self._volume_level = 0.5
        self._is_muted = False

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return features based on which commands are mapped."""
        features = MediaPlayerEntityFeature(0)
        mapping = self._device.entity_config.command_mapping

        if "turn_on" in mapping or "turn_off" in mapping:
            features |= MediaPlayerEntityFeature.TURN_ON
            features |= MediaPlayerEntityFeature.TURN_OFF
        if "volume_up" in mapping:
            features |= MediaPlayerEntityFeature.VOLUME_STEP
        if "mute" in mapping:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE
        if "select_source" in mapping:
            features |= MediaPlayerEntityFeature.SELECT_SOURCE

        return features

    @property
    def device_info(self) -> dict: ...
    @property
    def state(self) -> MediaPlayerState: ...

    async def async_turn_on(self) -> None: ...
    async def async_turn_off(self) -> None: ...
    async def async_volume_up(self) -> None: ...
    async def async_volume_down(self) -> None: ...
    async def async_mute_volume(self, mute: bool) -> None: ...
```

### Climate Entity (`climate.py`)

```python
"""Climate entity platform for HAIR (preset-based)."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import IRDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None: ...


class HAIRClimateEntity(ClimateEntity):
    """IR-controlled climate device (preset-based)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, device: IRDevice) -> None:
        self._device = device
        self._attr_unique_id = f"hair_{device.id}_climate"
        self._attr_name = None
        self._hvac_mode = HVACMode.OFF
        self._target_temperature: float | None = None
        self._fan_mode: str | None = None

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return features based on mapped commands."""
        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        config = self._device.entity_config

        if config.hvac_modes:
            # No feature flag needed — hvac_modes is always supported
            pass
        if config.fan_modes:
            features |= ClimateEntityFeature.FAN_MODE
        if config.temperature_presets:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return available HVAC modes based on captured commands."""
        ...

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current assumed HVAC mode."""
        return self._hvac_mode

    @property
    def device_info(self) -> dict: ...

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode by sending the corresponding IR command."""
        ...

    async def async_set_temperature(self, **kwargs) -> None:
        """Set temperature (snaps to nearest preset)."""
        ...

    async def async_turn_on(self) -> None: ...
    async def async_turn_off(self) -> None: ...
```

### Fan Entity (`fan.py`)

```python
"""Fan entity platform for HAIR."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import IRDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None: ...


class HAIRFanEntity(FanEntity):
    """IR-controlled fan."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, device: IRDevice) -> None:
        self._device = device
        self._attr_unique_id = f"hair_{device.id}_fan"
        self._attr_name = None
        self._is_on = False
        self._percentage: int | None = None
        self._oscillating: bool | None = None

    @property
    def supported_features(self) -> FanEntityFeature: ...
    @property
    def device_info(self) -> dict: ...

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None: ...
    async def async_turn_off(self) -> None: ...
    async def async_oscillate(self, oscillating: bool) -> None: ...
```

---

## 12. WebSocket API (`websocket_api.py`)

```python
"""WebSocket API for HAIR frontend communication."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN, WS_PREFIX


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket commands."""
    websocket_api.async_register_command(hass, ws_get_devices)
    websocket_api.async_register_command(hass, ws_get_device)
    websocket_api.async_register_command(hass, ws_create_device)
    websocket_api.async_register_command(hass, ws_update_device)
    websocket_api.async_register_command(hass, ws_delete_device)
    websocket_api.async_register_command(hass, ws_get_commands)
    websocket_api.async_register_command(hass, ws_delete_command)
    websocket_api.async_register_command(hass, ws_send_command)
    websocket_api.async_register_command(hass, ws_start_capture)
    websocket_api.async_register_command(hass, ws_cancel_capture)
    websocket_api.async_register_command(hass, ws_save_captured_command)
    websocket_api.async_register_command(hass, ws_get_command_templates)
    websocket_api.async_register_command(hass, ws_get_capture_providers)


# --- Device Operations ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/devices",
})
@websocket_api.async_response
async def ws_get_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return all IR devices."""
    # Returns: [{ id, name, device_type, manufacturer, command_count, emitter_name }]
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_get_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return a single device with all commands."""
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/create",
    vol.Required("name"): str,
    vol.Required("device_type"): str,
    vol.Required("emitter_entity_id"): str,
    vol.Optional("manufacturer"): str,
    vol.Optional("model"): str,
    vol.Optional("capture_device_id"): str,
    vol.Optional("capture_provider_type"): str,
})
@websocket_api.async_response
async def ws_create_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new IR device."""
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/update",
    vol.Required("device_id"): str,
    vol.Optional("name"): str,
    vol.Optional("manufacturer"): str,
    vol.Optional("model"): str,
    vol.Optional("emitter_entity_id"): str,
})
@websocket_api.async_response
async def ws_update_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update device metadata."""
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/device/delete",
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_delete_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a device and all its commands/entities."""
    ...


# --- Command Operations ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/send",
    vol.Required("device_id"): str,
    vol.Required("command_id"): str,
})
@websocket_api.async_response
async def ws_send_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send (test) a stored IR command."""
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/command/delete",
    vol.Required("device_id"): str,
    vol.Required("command_id"): str,
})
@websocket_api.async_response
async def ws_delete_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a command from a device."""
    ...


# --- Capture Operations (with event streaming) ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/start",
    vol.Required("device_id"): str,
    vol.Optional("timeout", default=15): int,
})
@websocket_api.async_response
async def ws_start_capture(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Start IR capture. Sends events as capture progresses.

    Events sent to client:
    - {type: "capture_listening"} — capture started, waiting for signal
    - {type: "capture_received", result: {...}} — signal captured
    - {type: "capture_timeout"} — no signal within timeout
    - {type: "capture_error", error: "..."} — hardware error
    - {type: "capture_duplicate", existing_command: {...}} — duplicate detected
    """
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/cancel",
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_cancel_capture(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Cancel an active capture session."""
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/save",
    vol.Required("device_id"): str,
    vol.Required("session_id"): str,
    vol.Required("command_name"): str,
    vol.Required("command_category"): str,
})
@websocket_api.async_response
async def ws_save_captured_command(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Save a captured command to a device."""
    ...


# --- Template & Provider Info ---

@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/templates",
    vol.Required("device_type"): str,
})
@websocket_api.async_response
async def ws_get_command_templates(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get command templates for a device type."""
    ...


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{WS_PREFIX}/capture/providers",
})
@websocket_api.async_response
async def ws_get_capture_providers(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get available capture providers."""
    ...
```

---

## 13. Frontend Components

### TypeScript Types (`frontend/src/types.ts`)

```typescript
interface IRDevice {
    id: string;
    name: string;
    device_type: "tv" | "ac" | "fan" | "soundbar" | "projector" | "other";
    manufacturer: string | null;
    model: string | null;
    emitter_entity_id: string;
    capture_device_id: string | null;
    commands: IRCommand[];
    entity_config: EntityConfig;
    command_count: number;
    created_at: string;
}

interface IRCommand {
    id: string;
    name: string;
    category: string;
    source: "captured" | "database" | "imported";
    protocol: string | null;
    code: string | null;
    frequency: number;
    repeat_count: number;
}

interface CommandTemplate {
    name: string;
    category: string;
    essential: boolean;
}

interface CaptureEvent {
    type: "capture_listening" | "capture_received" | "capture_timeout"
        | "capture_error" | "capture_duplicate";
    result?: CaptureResult;
    error?: string;
    existing_command?: IRCommand;
}

interface CaptureResult {
    protocol: string | null;
    code: string | null;
    raw_timings: number[];
    frequency: number;
    confidence: number;
}

interface EntityConfig {
    platform: string;
    command_mapping: Record<string, string>;
}
```

### Main Panel (`frontend/src/ha-panel-ir-devices.ts`)

```typescript
/**
 * Main panel entry point for HAIR.
 *
 * Renders in HA Settings sidebar as "IR Devices".
 * Handles routing between device list and device detail views.
 *
 * Elements:
 * - Navigation breadcrumb
 * - Router: list view | detail view
 *
 * WebSocket subscriptions:
 * - hair/devices (initial load)
 *
 * HA components used:
 * - ha-top-app-bar-fixed
 * - ha-menu-button
 * - ha-fab (floating action button for "Add Device")
 */
```

### Device List (`frontend/src/ir-device-list.ts`)

```typescript
/**
 * Grid/list of IR devices.
 *
 * Elements per device card:
 * - Device icon (based on type: mdi:television, mdi:air-conditioner, etc.)
 * - Device name
 * - Manufacturer + emitter name subtitle
 * - Command count badge
 * - Quick actions: [Test ▶] [Capture] [···]
 *
 * Empty state:
 * - "No IR devices yet. Add your first device to get started."
 * - [+ Add Device] button
 *
 * HA components used:
 * - ha-card
 * - ha-icon-button
 * - ha-button
 * - ha-chip (for command count)
 */
```

### Device Detail (`frontend/src/ir-device-detail.ts`)

```typescript
/**
 * Device detail view with command checklist.
 *
 * Sections:
 * 1. Header: device name, type icon, manufacturer, emitter
 * 2. Progress bar: X/Y commands captured
 * 3. Command checklist (grouped by essential/optional)
 *    - Each row: checkbox state, name, protocol info, [Test] [Re-learn] buttons
 *    - Unlearned rows: [Learn] button
 * 4. Custom command section: [+ Add Custom Command]
 * 5. Entity section: auto-created entity info, mapped features
 *
 * Interactions:
 * - Click [Learn] → opens ir-capture-dialog for that command name
 * - Click [Test] → sends hair/command/send via WebSocket
 * - Click [Re-learn] → opens ir-capture-dialog in replace mode
 * - Click [···] on command → delete option
 *
 * HA components used:
 * - ha-card, ha-list-item, ha-icon-button
 * - ha-linear-progress (setup progress)
 * - ha-button-menu (overflow menus)
 */
```

### Capture Dialog (`frontend/src/ir-capture-dialog.ts`)

```typescript
/**
 * 2-phase IR capture dialog.
 *
 * Phase 1: Listening
 * - Title: "Learning: {command_name}"
 * - Animated pulsing indicator (CSS animation)
 * - Instruction text with device-specific tips
 * - Countdown timer (ha-circular-progress or custom)
 * - [Cancel] button
 * - aria-live region for screen reader updates
 *
 * Phase 2: Captured / Confirm
 * - Success indicator (checkmark animation)
 * - Protocol info (de-emphasized)
 * - [Test Command] button — sends command immediately
 * - [Re-capture] button — returns to Phase 1
 * - [Save & Learn Next] primary CTA — saves, auto-advances to next template
 *
 * Error states (inline, no separate dialog):
 * - Timeout: tips + [Try Again]
 * - Duplicate: shows matching command + [Save Anyway] | [Re-capture]
 * - Hardware error: message + [Try Again] | [Cancel]
 *
 * WebSocket flow:
 * 1. Send hair/capture/start → subscribe to events
 * 2. Receive capture_listening → show Phase 1
 * 3. Receive capture_received → show Phase 2
 *    OR capture_timeout → show error inline
 *    OR capture_duplicate → show duplicate warning
 * 4. User clicks Save → send hair/capture/save
 * 5. User clicks Save & Learn Next → save + trigger next capture
 *
 * HA components used:
 * - ha-dialog
 * - ha-button (primary, outlined variants)
 * - ha-circular-progress
 * - ha-alert (for warnings/errors)
 *
 * Accessibility:
 * - aria-live="polite" on status region
 * - aria-valuenow on countdown
 * - Focus management between phases
 */
```

### Build Configuration (`frontend/rollup.config.mjs`)

```javascript
/**
 * Rollup config to bundle all frontend components into a single JS file.
 *
 * Input: src/ha-panel-ir-devices.ts
 * Output: dist/ha-panel-ir-devices.js
 *
 * Externals: lit, @lit/reactive-element (provided by HA runtime)
 * Plugins: typescript, terser (minification), node-resolve
 *
 * Build command: npm run build
 * Watch command: npm run dev
 */
```

---

## 14. strings.json Structure

```json
{
    "config": {
        "step": {
            "user": {
                "title": "Set Up IR Device",
                "description": "Choose what type of IR device you want to control.",
                "data": {
                    "device_type": "Device type"
                }
            },
            "device_details": {
                "title": "Device Details",
                "description": "Give your device a name and select the IR hardware.",
                "data": {
                    "device_name": "Device name",
                    "manufacturer": "Brand (optional)",
                    "model": "Model (optional)",
                    "emitter_entity_id": "IR emitter (sends commands)",
                    "capture_device_id": "IR receiver (learns commands)"
                }
            },
            "complete": {
                "title": "Device Created!",
                "description": "{device_name} is ready to learn IR commands."
            }
        },
        "abort": {
            "no_ir_hardware": "No IR hardware found. Set up an ESPHome or Broadlink device first.",
            "no_capture_device": "No IR receiver found. You need a device that can learn IR signals.",
            "already_configured": "This device is already configured."
        },
        "error": {
            "cannot_connect": "Cannot connect to IR hardware.",
            "unknown": "An unexpected error occurred."
        }
    },
    "options": {
        "step": {
            "init": {
                "title": "IR Device Options",
                "data": {
                    "capture_timeout": "Capture timeout (seconds)",
                    "default_repeat_count": "Default repeat count"
                }
            }
        }
    },
    "device_types": {
        "tv": "TV / Monitor",
        "ac": "Air Conditioner",
        "fan": "Fan",
        "soundbar": "Soundbar / Audio",
        "projector": "Projector",
        "other": "Other"
    },
    "panel": {
        "title": "IR Devices",
        "devices": "Devices",
        "add_device": "Add Device",
        "no_devices": "No IR devices yet",
        "no_devices_description": "Add your first device to get started.",
        "commands": "Commands",
        "command_count": "{count} commands",
        "essential_commands": "Essential Commands",
        "optional_commands": "Optional Commands",
        "custom_commands": "Custom Commands",
        "add_custom_command": "Add Custom Command",
        "learn": "Learn",
        "relearn": "Re-learn",
        "test": "Test",
        "delete": "Delete",
        "setup_progress": "{learned}/{total} commands",
        "entity_section": "Entity",
        "entity_auto_created": "Auto-created: {entity_id}",
        "mapped_features": "Mapped: {features}"
    },
    "capture": {
        "title": "Learning: \"{command_name}\"",
        "listening": "Listening for IR signal...",
        "instruction": "Point your remote at the IR receiver and press the \"{command_name}\" button.",
        "time_remaining": "{seconds}s remaining",
        "captured": "Signal Captured!",
        "protocol_detected": "Protocol: {protocol}",
        "test_prompt": "Did it work? Press Test to verify.",
        "test_command": "Test Command",
        "recapture": "Re-capture",
        "save": "Save",
        "save_and_next": "Save & Learn Next",
        "cancel": "Cancel",
        "timeout_title": "No signal detected",
        "timeout_tip_1": "Point the remote directly at the IR receiver",
        "timeout_tip_2": "Move closer (within 3 feet / 1 meter)",
        "timeout_tip_3": "Press and hold the button briefly",
        "try_again": "Try Again",
        "duplicate_title": "Duplicate Signal Detected",
        "duplicate_message": "This matches your \"{existing_name}\" command.",
        "save_anyway": "Save Anyway",
        "recapture_different": "Re-capture Different Signal",
        "error_title": "Capture Error",
        "error_hardware": "Could not communicate with the IR receiver.",
        "error_in_progress": "Another capture is already in progress.",
        "ac_preset_warning": "Before learning AC commands, set your AC to a neutral state (e.g., 72°F, fan auto). Each command captures the full AC state."
    }
}
```

---

## 15. Integration Setup (`__init__.py`)

```python
"""The HAIR integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import panel_custom

from .const import DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL, PLATFORMS
from .capture_orchestrator import CaptureOrchestrator
from .device_manager import DeviceManager
from .entity_factory import EntityFactory
from .storage import HAIRStore
from .websocket_api import async_register_websocket_commands

PLATFORMS_LIST: list[Platform] = [
    Platform.REMOTE,
    Platform.MEDIA_PLAYER,
    Platform.CLIMATE,
    Platform.FAN,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up HAIR from a config entry."""
    # 1. Initialize storage
    store = HAIRStore(hass)
    await store.async_load()

    # 2. Initialize components
    entity_factory = EntityFactory(hass)
    orchestrator = CaptureOrchestrator(hass)
    device_manager = DeviceManager(hass, store, entity_factory)

    # 3. Store in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "device_manager": device_manager,
        "orchestrator": orchestrator,
        "entity_factory": entity_factory,
    }

    # 4. Register WebSocket commands
    async_register_websocket_commands(hass)

    # 5. Register admin panel
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="ha-panel-ir-devices",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL,
        config={"entry_id": entry.entry_id},
        require_admin=True,
        update=True,
        module_url=f"/hacsfiles/hair/ha-panel-ir-devices.js",
    )

    # 6. Forward platform setup
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_LIST
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a HAIR config entry."""
    # 1. Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS_LIST
    )

    if unload_ok:
        # 2. Cancel any active capture
        data = hass.data[DOMAIN].pop(entry.entry_id)
        orchestrator: CaptureOrchestrator = data["orchestrator"]
        if orchestrator.is_capturing:
            await orchestrator.cancel_capture(
                orchestrator._active_session.session_id
            )

        # 3. Remove panel (if last entry)
        if not hass.data[DOMAIN]:
            hass.components.frontend.async_remove_panel(PANEL_URL)

    return unload_ok
```

---

## 16. Testing Architecture

### Test Fixtures (`tests/conftest.py`)

```python
"""Test fixtures for HAIR integration."""
import pytest
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    CaptureResult,
    IRCommand,
    IRDevice,
)
from custom_components.hair.capture import MockCaptureProvider


@pytest.fixture
def mock_capture_result() -> CaptureResult:
    """Return a mock capture result."""
    return CaptureResult(
        protocol="NEC",
        code="0x20DF10EF",
        raw_timings=[9000, -4500, 560, -560, ...],
        frequency=38000,
        confidence=0.95,
    )


@pytest.fixture
def mock_capture_provider(mock_capture_result) -> MockCaptureProvider:
    """Return a mock capture provider."""
    return MockCaptureProvider(
        result=mock_capture_result,
        delay=0.1,
    )


@pytest.fixture
def mock_device() -> IRDevice:
    """Return a mock IR device."""
    return IRDevice(
        id="test-device-1",
        name="Test TV",
        device_type="tv",
        manufacturer="Samsung",
        emitter_entity_id="infrared.test_emitter",
        commands=[
            IRCommand(
                id="cmd-1",
                name="Power",
                category="power",
                protocol="NEC",
                code="0x20DF10EF",
            ),
        ],
    )


@pytest.fixture
def mock_emitters():
    """Mock infrared.async_get_emitters to return test emitters."""
    ...


@pytest.fixture
def mock_setup_entry():
    """Mock integration setup."""
    ...
```

### Key Test Scenarios

```python
# test_capture.py
async def test_esphome_capture_success(): ...
async def test_broadlink_capture_success(): ...
async def test_capture_timeout(): ...
async def test_capture_duplicate_detection(): ...
async def test_capture_concurrent_lock(): ...
async def test_capture_cancel(): ...

# test_config_flow.py
async def test_flow_no_emitters_aborts(): ...
async def test_flow_single_emitter_auto_selects(): ...
async def test_flow_multiple_emitters_shows_picker(): ...
async def test_flow_creates_entry(): ...
async def test_flow_device_types(): ...

# test_device_manager.py
async def test_create_device(): ...
async def test_delete_device_cleans_entities(): ...
async def test_add_command_auto_maps(): ...
async def test_replace_command(): ...
async def test_send_command_via_emitter(): ...

# test_storage.py
async def test_storage_save_load_roundtrip(): ...
async def test_storage_migration_v1_to_v2(): ...

# test_media_player.py
async def test_features_match_mapped_commands(): ...
async def test_turn_on_sends_power_command(): ...
async def test_volume_up_sends_command(): ...
async def test_assumed_state_tracking(): ...

# test_climate.py
async def test_preset_based_temperature(): ...
async def test_hvac_mode_changes(): ...
async def test_assumed_state(): ...
```

---

## Summary of All Artifacts

| File | Purpose | Lines (est.) |
|---|---|---|
| `__init__.py` | Integration lifecycle | 80-100 |
| `manifest.json` | Metadata | 15 |
| `const.py` | Constants, enums | 80-100 |
| `config_flow.py` | Setup wizard | 150-200 |
| `models.py` | Data classes | 200-250 |
| `storage.py` | Persistence | 100-120 |
| `device_manager.py` | Device CRUD | 150-200 |
| `capture.py` | Provider abstraction | 200-250 |
| `capture_orchestrator.py` | Session management | 120-150 |
| `entity_factory.py` | Entity creation | 80-100 |
| `command_templates.py` | Command suggestions | 60-80 |
| `websocket_api.py` | WS handlers | 250-300 |
| `remote.py` | Remote entity | 80-100 |
| `media_player.py` | Media player entity | 120-150 |
| `climate.py` | Climate entity | 120-150 |
| `fan.py` | Fan entity | 80-100 |
| `diagnostics.py` | Debug info | 30-40 |
| `strings.json` | UI strings | 120 |
| Frontend (bundled) | Admin panel | 800-1000 |
| Tests | All test files | 600-800 |
| **Total** | | **~3,400-4,200** |

---

*This document defines the complete code architecture for HAIR. No actual code has been written — this is the blueprint for implementation. All module boundaries, function signatures, data models, and API contracts are defined here.*
