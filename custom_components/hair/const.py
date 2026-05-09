"""Constants for the HAIR integration."""
from __future__ import annotations

from enum import StrEnum

DOMAIN = "hair"
STORAGE_KEY = "hair_devices"
STORAGE_VERSION = 1
STORAGE_VERSION_MINOR = 1

CONF_EMITTER_ENTITY_ID = "emitter_entity_id"
CONF_CAPTURE_DEVICE_ID = "capture_device_id"
CONF_CAPTURE_PROVIDER_TYPE = "capture_provider_type"
CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_NAME = "device_name"
CONF_MANUFACTURER = "manufacturer"
CONF_MODEL = "model"
CONF_CAPTURE_TIMEOUT = "capture_timeout"
CONF_DEFAULT_REPEAT_COUNT = "default_repeat_count"

DEFAULT_CAPTURE_TIMEOUT = 15
DEFAULT_CARRIER_FREQUENCY = 38000
DEFAULT_REPEAT_COUNT = 1
MIN_CAPTURE_TIMEOUT = 5
MAX_CAPTURE_TIMEOUT = 60

PLATFORMS = ["remote", "media_player", "climate", "fan"]

PANEL_URL = "ir-devices"
PANEL_TITLE = "IR Devices"
PANEL_ICON = "mdi:remote"

WS_PREFIX = "hair"

EVENT_COMMAND_CAPTURED = f"{DOMAIN}_command_captured"
EVENT_CAPTURE_TIMEOUT = f"{DOMAIN}_capture_timeout"
EVENT_CAPTURE_ERROR = f"{DOMAIN}_capture_error"
EVENT_SIGNAL_DETECTED = f"{DOMAIN}_signal_detected"

# ---------------------------------------------------------------------------
# Signal Monitor
# ---------------------------------------------------------------------------
SIGNAL_STORAGE_KEY = "hair_unknown_signals"
SIGNAL_STORAGE_VERSION = 1
SIGNAL_BUFFER_MAX_DEVICES = 500
SIGNAL_EVICT_AGE_DAYS = 30
SIGNAL_EVICT_MIN_HITS = 5
SIGNAL_CLUSTER_THRESHOLD = 3
SIGNAL_REPEAT_SUPPRESS_MS = 300
SIGNAL_SAVE_DEBOUNCE_S = 30
SIGNAL_SAVE_MAX_DELAY_S = 300
SIGNAL_RATE_LIMIT_PER_SEC = 10
SIGNAL_WS_PUSH_RATE_LIMIT = 5
SIGNAL_RAW_QUANTIZE_BIN_US = 50
SIGNAL_RAW_FINGERPRINT_LEN = 64


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
    MOCK = "mock"


class CaptureState(StrEnum):
    """States of a capture session."""

    IDLE = "idle"
    LISTENING = "listening"
    CAPTURED = "captured"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"
