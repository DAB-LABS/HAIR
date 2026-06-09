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
DEFAULT_CAPTURE_TIMEOUT = 15
DEFAULT_CARRIER_FREQUENCY = 38000
DEFAULT_REPEAT_COUNT = 1

PLATFORMS = ["remote", "media_player", "climate", "fan", "light", "switch", "cover"]

PANEL_URL = "hair"
PANEL_TITLE = "HAIR"
PANEL_ICON = "mdi:remote"

WS_PREFIX = "hair"

EVENT_COMMAND_CAPTURED = f"{DOMAIN}_command_captured"
EVENT_CAPTURE_TIMEOUT = f"{DOMAIN}_capture_timeout"
EVENT_CAPTURE_ERROR = f"{DOMAIN}_capture_error"
EVENT_SIGNAL_DETECTED = f"{DOMAIN}_signal_detected"
EVENT_SIGNAL_REMOVED = f"{DOMAIN}_signal_removed"
# Fired (rate-limited) when a signal arrives whose device fingerprint is in
# the persisted dismiss set. Drives the Sniffer's "Show Dismissed" button
# glow + dot indicator so users can tell that dismissed remotes are still
# active without bringing those signals back into the live feed.
EVENT_DISMISS_ACTIVITY = f"{DOMAIN}_dismiss_activity"

# ---------------------------------------------------------------------------
# Receiver mode detection
# ---------------------------------------------------------------------------
# Legacy ESPHome event bus bridge (pre-2026.6).
LEGACY_ESPHOME_IR_EVENT = "esphome.remote_received"
# Native infrared receiver API (HA 2026.6+).
NATIVE_RECEIVER_AVAILABLE = "native_receiver_available"

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

# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------
TRIGGER_HIT_RESET_WINDOW_S = 5
EVENT_TRIGGER_FIRED = f"{DOMAIN}_trigger_fired"

# Pronto S/L classification threshold (in Pronto timing units).
# Timing words below this are "short" (S), above are "long" (L).
# Real-world IR remotes cluster around ~0x20 (short) and ~0x40 (long)
# with a clear gap between ~0x24 and ~0x3D.
PRONTO_SL_THRESHOLD = 0x30
# Timing words above this are treated as end-of-signal gaps.
# Must be high enough to include NEC/Samsung/JVC/LG lead-in marks
# (0x100-0x200 range) but low enough to catch real inter-frame gaps
# (typically 0x0800+).
PRONTO_GAP_THRESHOLD = 0x0400
# Number of S/L pairs from the preamble used for device grouping.
PRONTO_DEVICE_PREAMBLE_PAIRS = 1
# NEC-family address length in burst pairs (8 address bits = 8 pairs).
# Used for device grouping when a lead-in mark is detected.
PRONTO_NEC_ADDRESS_PAIRS = 8
# Byte-hash quantization bin, in Pronto timing units (carrier cycles).
# The byte hash is a tiebreaker layered on top of the S/L fingerprint:
# two signals that share an S/L pattern but differ in their quantized
# timing bytes are stored as distinct signals rather than merged. Each
# timing word is rounded to the nearest multiple of this bin before
# hashing. N=20 is empirically the only bin size that collapses
# same-button captures across NEC, RC-5, Sony SIRC, and Samsung at
# typical receiver jitter (+/-3 cycles) while still distinguishing
# protocols whose long pulse sits below PRONTO_SL_THRESHOLD (Panasonic
# at 46 cycles, TCL112 at 40). Boundary placement matters more than bin
# width; do not retune without re-running the protocol-matrix sweep.
# Exposed as a tunable for unusually noisy capture environments.
PRONTO_BYTE_HASH_BIN = 20
ASSIGN_SERVICE_TIMEOUT_S = 10


class DeviceType(StrEnum):
    """IR device types."""

    MEDIA_PLAYER = "media_player"
    AC = "ac"
    FAN = "fan"
    LIGHT = "light"
    SWITCH = "switch"
    SCREEN = "screen"
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
    BRIGHTNESS = "brightness"
    COVER = "cover"
    MEDIA_CONTROL = "media_control"
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
    NATIVE = "native"
    MOCK = "mock"


class CaptureState(StrEnum):
    """States of a capture session."""

    IDLE = "idle"
    LISTENING = "listening"
    CAPTURED = "captured"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"
