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
# Whole-frame "send N times" for a device command. Orthogonal to the NEC
# ditto repeat_count above: this loops the entire built frame, protocol-
# agnostically. 1 = transmit once (default). MAX_SEND_COUNT caps the value;
# SEND_REPEAT_GAP is the inter-frame pause in seconds between whole-frame sends.
MAX_SEND_COUNT = 10
SEND_REPEAT_GAP = 0.1

# Minimum quiet time (seconds) between HAIR-originated transmissions on
# DIFFERENT emitters. Two blasters keying up at once superimpose their
# marks and spaces at any receiver in range of both; the hybrid arrives
# as a valid pulse train that decodes as nothing, fails the echo claim,
# and mints a junk Sniffer row (owner bench 2026-07-18: dual-emitter
# test of a SAMSUNG32 signal). Enforced by tx_gate.gated_send. Measured
# from the previous send's service ack, so it also absorbs the blaster's
# own post-ack transmit time. Same-emitter pacing (SEND_REPEAT_GAP)
# is untouched -- devices queue their own back-to-back sends.
EMITTER_STAGGER_GAP_S = 0.3

# Maximum delay (seconds) between a captured main frame and any NEC ditto from
# the same source device for the ditto to attribute to that frame. NEC dittos
# arrive every ~110ms; this 1.0s window covers up to ~9 consecutive dittos,
# enough for an intentional press-and-hold. Longer than that is treated as a
# fresh unrelated press.
REPEAT_ATTRIBUTION_WINDOW = 1.0

# Maximum delay (seconds) between two successive attributed dittos in the same
# burst. NEC dittos arrive ~110ms apart; > 250ms means the burst is over and
# the next short signal starts a new orphan burst. Closes the cross-remote
# attribution edge case (see ditto-count plan Section 1).
DITTO_INTER_FRAME_MAX_S = 0.25

# Maximum ditto count exposed in the UI. Mirrors MAX_SEND_COUNT for symmetric
# clamping. NEC has no hard spec ceiling, but 20 covers an intentional 2-second
# hold-down and prevents pathological values.
MAX_DITTO_COUNT = 20

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
# Fired when a signal's assignment set changes (assign, or a device command
# referencing it is added/removed). Carries {signal_fingerprint}. Lets other
# browser tabs refresh the green Assign badge and yellow trigger dot live.
EVENT_SIGNAL_UPDATED = f"{DOMAIN}_signal_updated"
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
# min_hits accumulation window, anchored at the FIRST press of a chain
# (v0.6.6): all min_hits presses must land within this many seconds of the
# first one, exactly as the trigger dialog's "within 5s" copy states. A
# press arriving after the window closes starts a fresh chain. (Pre-0.6.6
# the window slid on every press, letting slow chains accumulate across an
# unbounded total span.) Distinct from MULTI_RECEIVER_DEDUP_WINDOW_S below,
# which collapses one physical press seen by several receivers.
TRIGGER_HIT_RESET_WINDOW_S = 5
EVENT_TRIGGER_FIRED = f"{DOMAIN}_trigger_fired"
# Trigger dedup window (v0.5.7, resized v0.5.8). A single physical press
# captured by several receivers within this window counts as one press per
# (trigger, fingerprint): it increments a trigger's hit state once and fires
# each matching trigger at most once. Composes with min_hits (distinct
# presses still accumulate).
#
# Since v0.5.8 the window SLIDES (each suppressed capture refreshes it), so it
# must only cover the gap BETWEEN consecutive frames of one press, not the
# whole burst. It is sized against the widest inter-frame gap we know of:
# Sony SIRC repeats a full frame about every 45ms while a button is held.
# 100ms leaves real headroom for a jittery receiver without approaching a
# human double-press interval (150ms+ between distinct presses, since a
# release and re-press cannot happen faster).
MULTI_RECEIVER_DEDUP_WINDOW_S = 0.100

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

# ---------------------------------------------------------------------------
# Protocol decode (infrared-protocols integration, v0.4.0 Phase A)
# ---------------------------------------------------------------------------
# Canonical string form of a decoded signal's identity, used as the
# decoded_fingerprint for decoded-first matching. The address is always
# rendered as 16-bit (the library emits a 16-bit NEC address; standard
# 8-bit NEC has high byte == ~low) and the command as 8-bit. Example for
# NEC(address=0xFB04, command=0x08): "NEC:0xFB04:0x08".
DECODED_FINGERPRINT_FORMAT = "{protocol}:{address:#06x}:{command:#04x}"
# Protocol-family label stored in decoded_protocol for NEC-family signals.
DECODED_PROTOCOL_NEC = "NEC"

# ---------------------------------------------------------------------------
# Plucker (vendor code import via observer emitter, v0.5.0)
# ---------------------------------------------------------------------------
# Per-pluck capture window. The vendor service call is awaited (blocking),
# so happy-path captures land synchronously within the await; this timeout
# is the safety net for a vendor call that returns without dispatching a
# Command to the HAIR Tweezer.
PLUCK_TIMEOUT_S = 5
# Marker attribute set on the HAIR Tweezer observer-emitter entity so HAIR
# can filter it out of its own emitter pickers while leaving it visible to
# HA's general infrared emitter list (vendor services must be able to target
# it).
TWEEZER_OBSERVER_ATTR = "hair_observer"

# --- The Mirror (v0.6.6) ----------------------------------------------------
# Synthetic Sniffer-store device that logs every HA-originated IR
# transmission (send-time rows; echoes enrich with heard_by). Rendered by
# the Mirror tab; the Sniffer filters it out of its own feed.
MIRROR_DEVICE_FP = "hair-mirror"
MIRROR_DEVICE_LABEL = "Mirror"
# How long after a send (or a foreign emitter beacon) an arriving capture
# may still be claimed as that send's echo. Generous for slow emitters
# (Broadlink queueing) and multi-frame sends.
MIRROR_ECHO_TTL_S = 2.5
# A state beacon on an emitter within this window of HAIR's own recorded
# send on that emitter is HAIR's own beacon, not a foreign integration's.
# 3.0s, not 1.0: the mark is set BEFORE the send loop, and a queued
# Broadlink can take over a second to actually transmit and write its
# state -- at 1.0s the bench caught HAIR mistaking its own send for a
# foreign integration's (which then claimed stray captures as echoes).
# Matches the echo TTL's generosity for slow emitters.
MIRROR_OWN_BEACON_WINDOW_S = 3.0
# Synthetic per-emitter fingerprint prefix for foreign sends that no
# receiver heard (identity unknown, send still audited).
MIRROR_UNKNOWN_SEND_FP_PREFIX = "mirror-unknown::"
# Directory (relative to this package) holding the pluckable YAML registry,
# one file per vendor integration. Files starting with "_" are skipped by
# the loader (templates, drafts).
PLUCKABLE_DIRNAME = "pluckable"
# Schema versions the running HAIR knows how to validate. A file declaring a
# version not in this set is skipped (higher version: needs a newer HAIR).
PLUCKABLE_SCHEMA_VERSIONS = (1,)


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
    COLOR_TEMP = "color_temp"
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
