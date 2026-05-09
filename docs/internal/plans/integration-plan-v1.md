# HA IR Admin — Integration Plan v1

**Author:** David Bailey
**Date:** 2026-05-08
**Status:** Draft — Pending Trio Review

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Home Assistant                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  HA IR Admin Integration                  │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │   │
│  │  │  Admin Panel │  │  Config Flow  │  │  Entity        │   │   │
│  │  │  (Frontend)  │  │  (Setup UX)   │  │  Platform      │   │   │
│  │  │              │  │              │  │  (media_player │   │   │
│  │  │  - Device    │  │  - Emitter   │  │   climate, fan │   │   │
│  │  │    list      │  │    select    │  │   remote)      │   │   │
│  │  │  - Capture   │  │  - Device    │  │              │   │   │
│  │  │    dialog    │  │    type      │  └──────┬────────┘   │   │
│  │  │  - Command   │  │  - Name     │         │            │   │
│  │  │    mgmt      │  │            │         │            │   │
│  │  └──────┬───────┘  └──────┬──────┘         │            │   │
│  │         │                 │                 │            │   │
│  │  ┌──────▼─────────────────▼─────────────────▼──────────┐ │   │
│  │  │              WebSocket API Layer                     │ │   │
│  │  │  - Device CRUD    - Capture control                  │ │   │
│  │  │  - Command mgmt   - Entity management                │ │   │
│  │  └──────────────────────┬───────────────────────────────┘ │   │
│  │                         │                                  │   │
│  │  ┌──────────────────────▼───────────────────────────────┐ │   │
│  │  │              Storage Layer (.storage/)                │ │   │
│  │  │  - Device profiles  - Learned IR codes                │ │   │
│  │  │  - Command mappings - Entity configurations           │ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐   │
│  │              HA Infrared Platform (2026.4)                 │   │
│  │  - InfraredEntity     - async_send_command()               │   │
│  │  - async_get_emitters()  - infrared-protocols lib          │   │
│  └───────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐   │
│  │              Emitter Integrations                          │   │
│  │  - ESPHome IR    - Broadlink RM    - SMLIGHT SLZB         │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Config Flow Design

### Flow Steps

```
Step 1: Select Emitter              Step 2: Device Type
┌───────────────────────┐          ┌───────────────────────┐
│  Choose IR Emitter    │          │  What kind of device? │
│                       │          │                       │
│  ○ ESPHome IR Blaster │   ──▶   │  ○ TV / Monitor       │
│  ○ Broadlink RM4      │          │  ○ Air Conditioner    │
│  ○ Living Room IR     │          │  ○ Fan                │
│                       │          │  ○ Soundbar / Audio   │
│  [Next]               │          │  ○ Projector          │
└───────────────────────┘          │  ○ Other              │
                                   │  [Next]               │
                                   └───────────────────────┘

Step 3: Name & Brand                Step 4: Done
┌───────────────────────┐          ┌───────────────────────┐
│  Device Details       │          │  ✓ Device Created!    │
│                       │          │                       │
│  Name: Living Room TV │   ──▶   │  "Living Room TV"     │
│  Brand: Samsung       │          │  is ready to learn    │
│  Model: (optional)    │          │  IR commands.         │
│                       │          │                       │
│  [Create]             │          │  [Open IR Admin ▶]    │
└───────────────────────┘          └───────────────────────┘
```

### Design Decisions
- **Emitter selection first** — Fail fast if no emitters exist
- **Device type drives entity creation** — Selecting "Air Conditioner" creates a climate entity
- **Brand/model optional** — Don't block setup with fields users may not know
- **Immediate redirect to admin panel** — Capture commands right away, no dead-end

---

## 3. Admin Panel UI

### Navigation Structure

```
IR Admin Panel
├── Devices (default view)
│   ├── Device Card (per device)
│   │   ├── Name, type, brand
│   │   ├── Command count badge
│   │   ├── Quick actions (test, capture, edit)
│   │   └── Status indicator
│   └── [+ Add Device] button
├── Device Detail View
│   ├── Info section (name, brand, model, emitter)
│   ├── Commands section
│   │   ├── Command list (name, protocol, test button)
│   │   ├── [+ Capture Command] button
│   │   └── Drag-to-reorder
│   └── Entity section
│       ├── Created entities list
│       └── Entity mapping configuration
└── Settings
    ├── Default emitter
    ├── Capture timeout settings
    └── Advanced options
```

### Device List View

```
┌─────────────────────────────────────────────────┐
│  IR Devices                         [+ Add]     │
│─────────────────────────────────────────────────│
│  ┌─────────────────────────────────────────┐    │
│  │ 📺 Living Room TV           12 commands │    │
│  │    Samsung · via ESPHome IR Blaster     │    │
│  │    [Test ▶] [Capture] [···]             │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ ❄️ Bedroom AC                8 commands │    │
│  │    Daikin · via Broadlink RM4           │    │
│  │    [Test ▶] [Capture] [···]             │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ 🔊 Soundbar                  6 commands │    │
│  │    Vizio · via ESPHome IR Blaster       │    │
│  │    [Test ▶] [Capture] [···]             │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Command Capture Dialog (The Magic Moment)

This is the most critical UX element. It must feel **magical, not technical.**

```
Phase 1: Ready                       Phase 2: Listening
┌───────────────────────────┐       ┌───────────────────────────┐
│  Capture IR Command       │       │  Capture IR Command       │
│                           │       │                           │
│  Point your remote at     │       │       ◉ ◉ ◉              │
│  the IR blaster and       │  ──▶  │    Listening...           │
│  press a button.          │       │                           │
│                           │       │  Point your remote at     │
│  Command name:            │       │  the IR blaster and       │
│  ┌─────────────────────┐  │       │  press a button now.      │
│  │ Power               │  │       │                           │
│  └─────────────────────┘  │       │  ████████░░░░  15s left   │
│                           │       │                           │
│  [Start Capture]          │       │  [Cancel]                 │
└───────────────────────────┘       └───────────────────────────┘

Phase 3: Received!                   Phase 4: Confirm
┌───────────────────────────┐       ┌───────────────────────────┐
│  Capture IR Command       │       │  Capture IR Command       │
│                           │       │                           │
│       ✓ Got it!           │       │  ✓ Command Saved!         │
│                           │       │                           │
│  Detected:                │  ──▶  │  "Power" has been added   │
│  Protocol: NEC            │       │  to Living Room TV.       │
│  Code: 0x20DF10EF         │       │                           │
│                           │       │  [Capture Another]        │
│  [Test It ▶] [Save]       │       │  [Done]                   │
└───────────────────────────┘       └───────────────────────────┘
```

### UX Flow Principles
1. **Name first, capture second** — User declares intent before the technical step
2. **Animated listening state** — Pulsing dots, countdown timer, clear visual feedback
3. **Instant test** — After capture, immediately test the command. This is the "did it work?" moment.
4. **Capture loop** — After saving, offer "Capture Another" to stay in flow for multi-command devices
5. **Progressive disclosure** — Protocol/code details shown but not emphasized. Power users see them; casual users skip them.

---

## 4. Data Model

### Device Profile
```
Device {
    id: UUID
    name: string                    # "Living Room TV"
    type: DeviceType                # tv | ac | fan | soundbar | projector | other
    manufacturer: string?           # "Samsung"
    model: string?                  # "UN55TU7000"
    emitter_entity_id: string       # "infrared.esphome_ir_blaster"
    commands: Command[]
    entity_config: EntityConfig
    created_at: datetime
    updated_at: datetime
}
```

### Command
```
Command {
    id: UUID
    name: string                    # "Power"
    category: CommandCategory       # power | volume | channel | navigation | mode | temp | fan_speed | custom
    protocol: string?               # "NEC" (if detected)
    code: string?                   # "0x20DF10EF" (if protocol-based)
    raw_timings: int[]?             # Raw timing data (fallback)
    frequency: int                  # Carrier frequency in Hz (default 38000)
    repeat_count: int               # Number of times to send (default 1)
    created_at: datetime
}
```

### Entity Configuration
```
EntityConfig {
    platform: string                # "media_player" | "climate" | "fan" | "remote"
    command_mapping: {
        // Platform-specific mappings
        // media_player example:
        "turn_on": "power_on_command_id",
        "turn_off": "power_off_command_id",
        "volume_up": "vol_up_command_id",
        ...
    }
    // climate-specific
    temperature_range: [min, max]?
    fan_modes: string[]?
    swing_modes: string[]?
    hvac_modes: string[]?
}
```

### Storage Format (.storage/ha_ir_admin)
```json
{
    "version": 1,
    "data": {
        "devices": {
            "uuid-1": {
                "name": "Living Room TV",
                "type": "tv",
                "manufacturer": "Samsung",
                "model": "UN55TU7000",
                "emitter_entity_id": "infrared.esphome_ir_blaster",
                "commands": [
                    {
                        "id": "cmd-uuid-1",
                        "name": "Power",
                        "category": "power",
                        "protocol": "NEC",
                        "code": "0x20DF10EF",
                        "raw_timings": null,
                        "frequency": 38000,
                        "repeat_count": 1
                    }
                ],
                "entity_config": {
                    "platform": "media_player",
                    "command_mapping": {
                        "turn_on": "cmd-uuid-1",
                        "turn_off": "cmd-uuid-1"
                    }
                }
            }
        }
    }
}
```

---

## 5. UX Flow — End to End

### First-Time User Journey

```
1. Install HA IR Admin via HACS
   └─▶ Integration appears in Settings > Devices & Services

2. Add Integration
   └─▶ Config flow: Select emitter → Device type → Name → Done
   └─▶ Takes 15 seconds

3. Redirect to IR Admin panel
   └─▶ Device created, zero commands
   └─▶ Prominent "Capture your first command" CTA

4. Capture first command
   └─▶ Click "Capture" → Name it "Power" → Start → Press remote → Got it! → Test → Save
   └─▶ Takes 20 seconds

5. Capture remaining commands
   └─▶ Stay in capture loop for Volume Up, Volume Down, etc.
   └─▶ 10 seconds per additional command

6. Entity auto-created
   └─▶ media_player.living_room_tv appears in HA
   └─▶ Commands mapped to entity actions automatically

TOTAL TIME TO WORKING IR CONTROL: < 2 minutes
```

### Error States

| Scenario | User Sees | Recovery |
|---|---|---|
| No emitters available | "No IR emitters found. Set up an ESPHome or Broadlink device first." with link to docs | Setup guide link |
| Capture timeout | "No signal detected. Make sure you're pointing at the receiver." with retry button | Retry, adjust position |
| Capture noise | "Multiple signals detected. Try again in a quieter IR environment." | Retry |
| Duplicate command | "This looks like the same signal as 'Power'. Save as new or replace?" | User choice |
| Emitter offline | "IR Blaster is unavailable. Check the device." with device link | Device diagnostics |
| Test fails (no visible response) | "Command sent! Did the device respond?" with Yes/No buttons | Re-capture option |

---

## 6. Technical Dependencies

### Required
- Home Assistant 2026.4+ (infrared platform)
- At least one IR emitter integration (ESPHome, Broadlink, SMLIGHT)

### Python Dependencies
- None beyond HA core (no pip requirements)

### Frontend Dependencies
- LitElement (bundled with HA)
- HA Web Components (ha-card, ha-dialog, ha-button, etc.)

### IR Receiving Challenge
The IR platform defines emitters (transmitters) but not receivers. For command capture:

**Option A: ESPHome IR Receiver**
- ESPHome already has `remote_receiver` component
- We could communicate with ESPHome via its API to listen for IR signals
- Requires ESPHome device with IR receiver hardware

**Option B: Broadlink Learning Mode**
- Broadlink RM devices have built-in learning mode
- Existing `broadlink.learn` service call captures raw IR data
- Limited to Broadlink hardware

**Option C: Abstract Receiver Platform**
- Define our own receiver abstraction (like the emitter platform)
- More future-proof but higher effort
- Could propose as HA core contribution

**Recommended: Option A + B initially** — Support ESPHome and Broadlink learning, with an abstraction layer that allows future receivers.

---

## 7. File Structure

```
custom_components/ha_ir_admin/
├── __init__.py                 # Integration setup, panel registration
├── manifest.json               # Integration manifest
├── config_flow.py              # Config flow handler
├── const.py                    # Constants, enums
├── strings.json                # UI strings
├── translations/
│   └── en.json                 # English translations
├── models.py                   # Data models (Device, Command, etc.)
├── storage.py                  # Persistent storage manager
├── device_manager.py           # Device CRUD operations
├── capture.py                  # IR capture/learning orchestration
├── entity_factory.py           # Entity creation from device profiles
├── websocket_api.py            # WebSocket command handlers
├── media_player.py             # Media player entity platform
├── climate.py                  # Climate entity platform
├── fan.py                      # Fan entity platform
├── remote.py                   # Remote entity platform
├── diagnostics.py              # Diagnostics support
├── icons.json                  # Custom icons
└── frontend/
    ├── ha-panel-ir-admin.js    # Main panel component
    ├── ha-ir-device-list.js    # Device list component
    ├── ha-ir-device-detail.js  # Device detail component
    ├── ha-ir-capture-dialog.js # Capture dialog component
    └── ha-ir-command-list.js   # Command list component
```

---

## 8. Service Calls

```yaml
ha_ir_admin.send_command:
  description: Send a stored IR command
  fields:
    device_id:
      description: The HA IR Admin device ID
      required: true
    command_name:
      description: The command name (e.g., "power")
      required: true

ha_ir_admin.capture_command:
  description: Start capturing an IR command
  fields:
    device_id:
      description: Target device to add the command to
      required: true
    command_name:
      description: Name for the captured command
      required: true
    timeout:
      description: Capture timeout in seconds
      default: 30
```

---

## 9. MVP Scope vs. Future

### MVP (v1.0)
- Device CRUD (create, read, update, delete)
- IR command capture (ESPHome + Broadlink)
- Command test/playback
- Admin panel in HA Settings
- media_player entity creation
- climate entity creation (basic)
- fan entity creation (basic)

### v1.1
- Command import/export
- Device profile sharing (community library)
- Bulk command capture mode
- Command groups (macros)

### v2.0
- Climate entity with full mode/temp support
- AC state tracking (best-effort, since IR is one-directional)
- Voice assistant integration hints
- Dashboard card (custom Lovelace card)
- IR code database lookup (known devices)

### v3.0
- Community device profile repository
- Automatic protocol detection suggestions
- Multi-emitter routing (room-based)
- RF support (when HA adds RF platform)

---

## 10. Success Criteria

| Metric | Target |
|---|---|
| Time to first command captured | < 60 seconds from install |
| Commands to capture for basic TV control | 5-8 commands |
| Config flow completion rate | > 90% (no abandonment) |
| HACS installs in month 1 | 1,000+ |
| Community forum positive sentiment | > 80% |
| Zero YAML required | 100% UI-driven |

---

*This plan is pending review by the Trio Review Board (CTO, Senior Dev, HA Power User).*
