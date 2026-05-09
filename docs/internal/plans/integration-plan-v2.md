# HA IR Admin — Integration Plan v2

**Author:** David Bailey
**Date:** 2026-05-08
**Status:** Post-Review Iteration
**Changes from v1:** Incorporates all 16 action items from Trio Review Board v1

---

## Changes Summary (v1 → v2)

| Area | v1 | v2 |
|---|---|---|
| Name | IR Admin | IR Devices (sidebar), HAIR (repo) |
| Capture abstraction | Ad-hoc per provider | `CaptureProvider` ABC |
| Capture dialog | 4-phase | 2-phase (listen → confirm+test) with auto-loop |
| Command naming | User types from scratch | Template-driven with suggestions per device type |
| Capture UX | Static dialog | Guided checklist with progress tracking |
| Climate entity | Full climate with slider | Preset-based (honest about IR limitations) |
| Data model | Basic | Added `source`, `database_id`, migration strategy |
| Concurrency | Not addressed | Receiver resource locking |
| Release strategy | Single MVP | Phase 0 → Phase 1 → Phase 2 |
| Onboarding | Standard config flow | Auto-detect existing IR hardware |
| Migration | Not planned | SmartIR import path designed for v1.1 |

---

## 1. Revised Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Home Assistant                                │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                    HAIR Integration                           │   │
│  │                                                               │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐   │   │
│  │  │  IR Devices  │  │  Config Flow  │  │  Entity Platforms  │   │   │
│  │  │  Panel       │  │  + Onboarding │  │  ┌──────────────┐ │   │   │
│  │  │  (Frontend)  │  │  Auto-detect  │  │  │ remote       │ │   │   │
│  │  └──────┬───────┘  └──────┬───────┘  │  │ media_player │ │   │   │
│  │         │                 │           │  │ climate      │ │   │   │
│  │         │                 │           │  │ fan          │ │   │   │
│  │         │                 │           │  └──────────────┘ │   │   │
│  │  ┌──────▼─────────────────▼───────────┴──────────────────┐│   │   │
│  │  │              WebSocket API Layer                       ││   │   │
│  │  └──────────────────────┬─────────────────────────────────┘│   │   │
│  │                         │                                   │   │   │
│  │  ┌──────────────────────▼──────────────────────────────┐   │   │   │
│  │  │              Core Services                           │   │   │   │
│  │  │  ┌─────────────┐ ┌────────────┐ ┌───────────────┐   │   │   │   │
│  │  │  │DeviceManager│ │CaptureOrch.│ │EntityFactory  │   │   │   │   │
│  │  │  └─────────────┘ └──────┬─────┘ └───────────────┘   │   │   │   │
│  │  │                         │                             │   │   │   │
│  │  │  ┌──────────────────────▼──────────────────────────┐  │   │   │   │
│  │  │  │         CaptureProvider Abstraction              │  │   │   │   │
│  │  │  │  ┌──────────────┐  ┌──────────────────────┐     │  │   │   │   │
│  │  │  │  │ ESPHome      │  │ Broadlink            │     │  │   │   │   │
│  │  │  │  │ Provider     │  │ Provider             │     │  │   │   │   │
│  │  │  │  └──────────────┘  └──────────────────────┘     │  │   │   │   │
│  │  │  └─────────────────────────────────────────────────┘  │   │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │   │
│  │                         │                                   │   │   │
│  │  ┌──────────────────────▼──────────────────────────────┐   │   │   │
│  │  │   Storage Layer (.storage/hair)                      │   │   │   │
│  │  │   Version: 1 | Migration: SchemaVersioned            │   │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │   │
│  └───────────────────────────────────────────────────────────┘   │   │
│                              │                                   │   │
│  ┌───────────────────────────▼───────────────────────────────┐   │   │
│  │              HA Infrared Platform (2026.4+)                │   │   │
│  └───────────────────────────────────────────────────────────┘   │   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Revised Config Flow + Onboarding

### Auto-Detection Step (NEW)

Before the config flow begins, HAIR checks for existing IR-capable integrations:

```python
async def async_step_user(self, user_input=None):
    """Handle initial step with auto-detection."""
    # Detect existing IR hardware
    emitters = infrared.async_get_emitters(self.hass)
    broadlink_entries = self.hass.config_entries.async_entries("broadlink")
    esphome_ir_devices = [...]  # Check ESPHome devices for IR capability

    if not emitters and not broadlink_entries:
        return self.async_abort(
            reason="no_ir_hardware",
            description_placeholders={
                "setup_url": "https://hair.dev/setup-guide"
            },
        )
    ...
```

### Revised Flow

```
Auto-Detect (implicit)              Step 1: Device Type
┌───────────────────────┐          ┌───────────────────────┐
│  Found IR hardware:   │          │  What are you         │
│                       │          │  setting up?          │
│  ✓ ESPHome IR Blaster │   ──▶   │                       │
│  ✓ Broadlink RM4      │          │  📺 TV / Monitor      │
│                       │          │  ❄️ Air Conditioner    │
│  (auto-proceed if     │          │  🌀 Fan               │
│   only one emitter)   │          │  🔊 Soundbar / Audio  │
│                       │          │  📽️ Projector         │
└───────────────────────┘          │  🎛️ Other             │
                                   └───────────────────────┘

Step 2: Details + Emitter           Step 3: Ready to Learn
┌───────────────────────┐          ┌───────────────────────┐
│  Device Details       │          │  ✓ "Living Room TV"   │
│                       │          │  is ready!            │
│  Name: Living Room TV │   ──▶   │                       │
│  Brand: Samsung       │          │  Let's learn some     │
│  (opt.)               │          │  commands.            │
│                       │          │                       │
│  IR Emitter:          │          │  [Start Learning ▶]   │
│  ○ ESPHome IR Blaster │          │  [Skip for now]       │
│  ○ Broadlink RM4      │          │                       │
│  [Create]             │          │                       │
└───────────────────────┘          └───────────────────────┘
```

**Key changes:**
- Device type FIRST (drives everything downstream)
- Auto-select emitter if only one exists
- "Start Learning" takes user directly into guided capture checklist
- Brand field is optional, never blocks progress

---

## 3. Revised Capture UX — Guided Checklist

### Device Detail with Command Checklist

```
┌──────────────────────────────────────────────────────────────┐
│  ← Back    Living Room TV                           [⚙️]   │
│─────────────────────────────────────────────────────────────│
│                                                              │
│  Setup Progress ██████████░░░░░░░░░░ 4/10 commands          │
│                                                              │
│  ESSENTIAL COMMANDS                                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ✅ Power          NEC · 0x20DF10EF    [▶Test] [↻]    │  │
│  │ ✅ Volume Up      NEC · 0x20DFC03F    [▶Test] [↻]    │  │
│  │ ✅ Volume Down    NEC · 0x20DF40BF    [▶Test] [↻]    │  │
│  │ ✅ Mute           NEC · 0x20DF906F    [▶Test] [↻]    │  │
│  │ ○  Source/Input   ──────────────────  [Learn]         │  │
│  │ ○  Channel Up     ──────────────────  [Learn]         │  │
│  │ ○  Channel Down   ──────────────────  [Learn]         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  NAVIGATION (optional)                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ○  Up             ──────────────────  [Learn]         │  │
│  │ ○  Down           ──────────────────  [Learn]         │  │
│  │ ○  Left           ──────────────────  [Learn]         │  │
│  │ ○  Right          ──────────────────  [Learn]         │  │
│  │ ○  Select/OK      ──────────────────  [Learn]         │  │
│  │ ○  Back/Return    ──────────────────  [Learn]         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [+ Add Custom Command]                                      │
│                                                              │
│  ── Entity ──────────────────────────────────────────────    │
│  ✓ media_player.living_room_tv (auto-created)                │
│    Power: mapped  Volume: mapped  Mute: mapped               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Key UX details:**
- **[↻] is "Re-learn"** — always visible, one-click re-capture
- **[▶Test] sends the command immediately** — instant feedback
- **Progress bar** at top gamifies the setup
- **Essential vs. optional sections** — users know when "enough" is captured
- **Entity auto-maps** commands as they're learned (no manual mapping step)
- **Protocol info shown but de-emphasized** — power users see it, casual users ignore it

---

## 4. Revised Capture Dialog (2-Phase)

### Phase 1: Listening

```
┌────────────────────────────────────────────┐
│  Learning: "Source/Input"            [×]   │
│                                            │
│              ◉ ◉ ◉                         │
│         Listening for IR...                │
│                                            │
│  Point your remote at the IR receiver      │
│  and press the "Source/Input" button.      │
│                                            │
│  ████████████████░░░░░░░░  12s remaining   │
│                                            │
│  [Cancel]                                  │
└────────────────────────────────────────────┘
```

Auto-opens in listening mode. No extra "Start" button.

### Phase 2: Captured — Confirm & Test

```
┌────────────────────────────────────────────┐
│  Learning: "Source/Input"            [×]   │
│                                            │
│           ✓ Signal Captured!               │
│                                            │
│  Protocol: NEC                             │
│  ┌──────────────────────────────────────┐  │
│  │ Did it work? Press Test to verify.  │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  [▶ Test Command]     [↻ Re-capture]      │
│                                            │
│  [Save & Learn Next ▶▶]                   │
└────────────────────────────────────────────┘
```

**"Save & Learn Next"** is the primary (filled/prominent) button. It saves the command, returns to the checklist, and auto-opens the dialog for the next unlearned command. The user flows through the entire checklist without ever returning to the device detail manually.

**"Test Command"** sends the IR signal so the user can verify. Essential for confidence.

**"Re-capture"** returns to Phase 1 without losing the command name.

### Error Handling (inline, not separate dialog)

```
┌────────────────────────────────────────────┐
│  Learning: "Source/Input"            [×]   │
│                                            │
│           ⚠️ No signal detected            │
│                                            │
│  Tips:                                     │
│  • Point the remote directly at the        │
│    IR receiver                             │
│  • Move closer (within 3 feet)             │
│  • Press and hold the button briefly       │
│                                            │
│  [↻ Try Again]              [Cancel]       │
└────────────────────────────────────────────┘
```

Errors are inline in the same dialog. "Try Again" restarts Phase 1 instantly.

### Duplicate Detection (inline)

```
┌────────────────────────────────────────────┐
│  Learning: "Source/Input"            [×]   │
│                                            │
│       ⚠️ Duplicate Signal Detected         │
│                                            │
│  This matches your "Power" command.        │
│  Some remotes use the same signal for      │
│  multiple functions (toggle behavior).     │
│                                            │
│  [Save Anyway]  [Re-capture Different]     │
└────────────────────────────────────────────┘
```

---

## 5. Revised Data Model

### Device

```python
@dataclass
class IRDevice:
    id: str                          # UUID
    name: str                        # "Living Room TV"
    device_type: DeviceType          # tv, ac, fan, soundbar, projector, other
    manufacturer: str | None         # "Samsung"
    model: str | None                # "UN55TU7000"
    emitter_entity_id: str           # "infrared.esphome_ir_blaster"
    capture_provider_type: str       # "esphome" | "broadlink"
    capture_provider_config: dict    # Provider-specific config
    commands: list[IRCommand]
    entity_config: EntityConfig
    database_id: str | None          # Future: ID in community code database
    created_at: str                  # ISO datetime
    updated_at: str                  # ISO datetime
```

### Command

```python
@dataclass
class IRCommand:
    id: str                          # UUID
    name: str                        # "Power"
    category: CommandCategory        # power, volume, channel, navigation, mode, temp, fan_speed, custom
    source: CommandSource            # captured, database, imported
    protocol: str | None             # "NEC" (if detected)
    code: str | None                 # "0x20DF10EF" (protocol-encoded)
    raw_timings: list[int] | None    # Raw mark/space microsecond timings
    frequency: int                   # Carrier frequency Hz (default 38000)
    repeat_count: int                # Send repetitions (default 1)
    created_at: str                  # ISO datetime
```

### Command Templates

```python
COMMAND_TEMPLATES: dict[DeviceType, list[CommandTemplate]] = {
    DeviceType.TV: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Mute", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
        CommandTemplate("Channel Up", CommandCategory.CHANNEL, essential=True),
        CommandTemplate("Channel Down", CommandCategory.CHANNEL, essential=True),
        CommandTemplate("Up", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Down", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Left", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Right", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Select/OK", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Back/Return", CommandCategory.NAVIGATION, essential=False),
    ],
    DeviceType.AC: [
        CommandTemplate("Power On", CommandCategory.POWER, essential=True),
        CommandTemplate("Power Off", CommandCategory.POWER, essential=True),
        CommandTemplate("Mode: Cool", CommandCategory.MODE, essential=True),
        CommandTemplate("Mode: Heat", CommandCategory.MODE, essential=False),
        CommandTemplate("Mode: Fan", CommandCategory.MODE, essential=False),
        CommandTemplate("Mode: Dry", CommandCategory.MODE, essential=False),
        CommandTemplate("Mode: Auto", CommandCategory.MODE, essential=False),
        CommandTemplate("Fan: Low", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Fan: Medium", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Fan: High", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Fan: Auto", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Swing Toggle", CommandCategory.CUSTOM, essential=False),
    ],
    DeviceType.FAN: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Speed Up", CommandCategory.FAN_SPEED, essential=True),
        CommandTemplate("Speed Down", CommandCategory.FAN_SPEED, essential=True),
        CommandTemplate("Oscillate", CommandCategory.CUSTOM, essential=False),
        CommandTemplate("Timer", CommandCategory.CUSTOM, essential=False),
    ],
    DeviceType.SOUNDBAR: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Mute", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
    ],
}
```

---

## 6. CaptureProvider Abstraction

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class CaptureResult:
    """Result of an IR capture attempt."""
    protocol: str | None           # Detected protocol name
    code: str | None               # Protocol-encoded code
    raw_timings: list[int]         # Raw timing data (always available)
    frequency: int                 # Carrier frequency
    confidence: float              # 0.0 - 1.0, how clean the signal was


class CaptureProvider(ABC):
    """Abstract base for IR signal capture."""

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return provider type identifier."""

    @abstractmethod
    async def async_start_capture(self, timeout: int = 15) -> None:
        """Enter learning/capture mode."""

    @abstractmethod
    async def async_stop_capture(self) -> None:
        """Exit learning mode."""

    @abstractmethod
    async def async_wait_for_signal(self) -> CaptureResult | None:
        """Wait for an IR signal. Returns None on timeout."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the capture hardware is ready."""


class ESPHomeCaptureProvider(CaptureProvider):
    """Capture IR signals via ESPHome remote_receiver component."""

    @property
    def provider_type(self) -> str:
        return "esphome"

    async def async_start_capture(self, timeout: int = 15) -> None:
        # Subscribe to ESPHome IR receiver events via native API
        ...

    async def async_wait_for_signal(self) -> CaptureResult | None:
        # Listen for IR event from ESPHome, decode protocol if possible
        ...


class BroadlinkCaptureProvider(CaptureProvider):
    """Capture IR signals via Broadlink learning mode."""

    @property
    def provider_type(self) -> str:
        return "broadlink"

    async def async_start_capture(self, timeout: int = 15) -> None:
        # Call broadlink device.enter_learning_mode()
        ...

    async def async_wait_for_signal(self) -> CaptureResult | None:
        # Poll broadlink device.check_data() until signal or timeout
        ...
```

### Receiver Resource Locking

```python
class CaptureOrchestrator:
    """Manages capture sessions with resource locking."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._active_session: CaptureSession | None = None

    async def start_session(self, provider: CaptureProvider, device_id: str) -> str:
        """Start a capture session. Returns session_id. Raises if locked."""
        if self._lock.locked():
            raise CaptureInProgressError("Another capture is in progress")
        await self._lock.acquire()
        ...

    async def end_session(self, session_id: str) -> None:
        """End capture session and release lock."""
        self._lock.release()
        ...
```

---

## 7. Storage Schema + Migration Strategy

### Schema v1

```json
{
    "version": 1,
    "minor_version": 1,
    "data": {
        "devices": { ... }
    }
}
```

### Migration Strategy

Using HA's built-in `Store` with version checking:

```python
STORAGE_VERSION = 1
STORAGE_VERSION_MINOR = 1

class HAIRStore:
    def __init__(self, hass):
        self._store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            minor_version=STORAGE_VERSION_MINOR,
        )

    async def _async_migrate(self, old_major, old_minor, data):
        """Migrate storage schema."""
        if old_major == 1:
            if old_minor < 2:
                # v1.1 → v1.2: Add command groups
                for device in data["devices"].values():
                    device.setdefault("command_groups", [])
        return data
```

---

## 8. Release Phasing (Revised)

### Phase 0: Capture Core (Week 1-2)
- `CaptureProvider` abstraction + ESPHome + Broadlink implementations
- Storage layer with device/command CRUD
- WebSocket API for capture control
- Minimal capture-only UI (dialog test page)
- **Goal:** Validate capture UX with real hardware

### Phase 1: Admin Panel + Remote Entity (Week 3-6)
- Full admin panel (device list, detail, capture checklist)
- Command templates per device type
- `remote` entity platform (basic send_command)
- Config flow with onboarding auto-detection
- HACS listing
- **Goal:** First public release, community feedback

### Phase 2: Rich Entities (Week 7-10)
- `media_player` entity platform (TV/soundbar control)
- `climate` entity platform (preset-based AC control)
- `fan` entity platform
- Entity auto-mapping from captured commands
- **Goal:** Full functionality for the three main device types

### Phase 2.5: Polish (Week 11-12)
- SmartIR import tool
- Command export/share
- Documentation site with GIFs
- Bug fixes from community feedback

---

## 9. Entity Auto-Mapping

When commands are captured, HAIR automatically maps them to entity features:

```python
ENTITY_COMMAND_MAPPING = {
    DeviceType.TV: {
        "platform": "media_player",
        "mappings": {
            "Power": ("turn_on", "turn_off"),  # Toggle
            "Volume Up": "volume_up",
            "Volume Down": "volume_down",
            "Mute": "mute",
            "Source/Input": "select_source",
        }
    },
    DeviceType.AC: {
        "platform": "climate",
        "mappings": {
            "Power On": "turn_on",
            "Power Off": "turn_off",
            "Mode: Cool": ("set_hvac_mode", HVACMode.COOL),
            "Mode: Heat": ("set_hvac_mode", HVACMode.HEAT),
            ...
        }
    },
}
```

**As users capture commands matching template names, entity capabilities light up automatically.** No manual mapping step required. The entity grows its feature set as more commands are learned.

---

## 10. Success Criteria (Revised)

| Metric | Target | How We Measure |
|---|---|---|
| Time to first command captured | < 45 seconds from install | User testing |
| Capture flow completion rate | > 85% per command | Analytics (opt-in) |
| Config flow abandonment | < 10% | Analytics |
| HACS installs — Month 1 | 2,000+ | HACS stats |
| HACS installs — Month 6 | 15,000+ | HACS stats |
| GitHub issues (bugs) — Month 1 | < 30 | GitHub |
| Community sentiment | > 85% positive | Forum monitoring |
| Zero YAML required | 100% | Architecture constraint |

---

*This plan incorporates all feedback from the Trio Review Board v1. Proceeding to final review pass.*
