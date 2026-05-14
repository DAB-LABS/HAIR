# Entity Platform Expansion - Design Reference

## Overview

HAIR is expanding from 6 device types (mapped to 4 platforms) to 7 device types with a clean 1:1 platform mapping. This also introduces an action mapping system that lets users explicitly bind IR commands to HA entity features via dropdown selection.

## Device Types and Platform Mapping

### Final Device Type List

| DeviceType | Enum Value | HA Platform | Use Case |
|---|---|---|---|
| Media Player | `media_player` | media_player | TVs, soundbars, projectors, set-top boxes, AV receivers |
| AC | `ac` | climate | Air conditioners, mini-splits |
| Fan | `fan` | fan | Ceiling/standing fans |
| Light | `light` | light | IR-controlled LED strips, dimmable lights |
| Switch | `switch` | switch | Generic on/off devices (fireplaces, heaters, etc.) |
| Screen | `screen` | cover | Projector screens, motorized shades/blinds |
| Other | `other` | remote | Anything else |

All devices also get `remote` and `button` entities regardless of type.

### Removed Types

The following types are consolidated into **Media Player**:
- TV, Soundbar, Projector, Set-top Box, Amplifier

These were all media_player entities with different default templates. The action mapping system makes sub-types unnecessary -- the entity exposes only the features the user actually maps commands to.

### New Entity Platforms

All new platforms use `assumed_state = True` because IR provides no feedback channel.

**light.py**
- `ColorMode.ONOFF` if only on/off commands mapped
- `ColorMode.BRIGHTNESS` if brightness stepping commands are mapped
- Tracks assumed brightness internally, steps up/down by fixed increments
- No color support (IR lights rarely have addressable color via discrete commands)

**switch.py**
- Simplest platform: just on/off
- `SwitchDeviceClass.SWITCH`
- Tracks assumed on/off state

**cover.py**
- `CoverDeviceClass.SHADE` (reasonable default for screens and shades)
- Feature detection: only exposes OPEN/CLOSE/STOP if corresponding commands are mapped
- No position tracking (no feedback)

### Updated media_player.py

Single type (`media_player`) replaces the old TV/Soundbar/Projector set. Add media transport features (play, pause, stop, rewind, fast forward). Feature exposure is driven entirely by which action keys have commands mapped.

## Command Templates

Templates define the dropdown options shown when assigning signals to a device.

### Media Player (~20 options)

Power On, Power Off, Volume Up, Volume Down, Mute, Source/Input, Channel Up, Channel Down, Up, Down, Left, Right, Select/OK, Back/Return, Guide, Menu, Play, Pause, Stop, Rewind, Fast Forward

### AC

Power On, Power Off, Mode: Cool, Mode: Heat, Mode: Fan, Mode: Dry, Mode: Auto, Fan: Low, Fan: Medium, Fan: High, Fan: Auto, Swing Toggle

### Fan

Power, Speed Up, Speed Down, Oscillate, Timer

### Light

On, Off, Brightness Up, Brightness Down

### Switch

On, Off

### Screen

Open, Close, Stop

### Other

(no predefined templates, freeform only)

## Action Mapping System

### Problem

Entity platforms currently determine capabilities by matching command names. A media_player checks if a command named "Volume Up" exists to decide whether to expose volume control. This is fragile -- the user has to type the exact name.

### Solution

Explicit action mapping via `EntityConfig.command_mapping`. Each device type defines a set of "action keys" (e.g., `turn_on`, `volume_up`, `open_cover`). Users map their IR commands to these action keys through dropdown selection in the UI.

### Action Keys Per Device Type

**Media Player:**
- `turn_on`, `turn_off`
- `volume_up`, `volume_down`, `mute`
- `select_source`
- `channel_up`, `channel_down`
- `navigate_up`, `navigate_down`, `navigate_left`, `navigate_right`
- `navigate_select`, `navigate_back`
- `play`, `pause`, `stop`, `rewind`, `fast_forward`
- `guide`, `menu`

**AC (climate):**
- `turn_on`, `turn_off`
- `mode_cool`, `mode_heat`, `mode_fan`, `mode_dry`, `mode_auto`
- `fan_low`, `fan_medium`, `fan_high`, `fan_auto`
- `swing_toggle`

**Fan:**
- `turn_on`, `turn_off`
- `speed_up`, `speed_down`
- `oscillate`

**Light:**
- `turn_on`, `turn_off`
- `brightness_up`, `brightness_down`

**Switch:**
- `turn_on`, `turn_off`

**Screen (cover):**
- `open_cover`, `close_cover`, `stop_cover`

**Other:**
- (no predefined actions, all commands are freeform)

### Data Model

`EntityConfig.command_mapping` is a `dict[str, str]` mapping action keys to command names:

```python
{
    "turn_on": "Power On",
    "turn_off": "Power Off",
    "volume_up": "Volume Up",
    "volume_down": "Volume Down",
}
```

Entity platforms check this mapping to determine which features to expose and which IR command to fire for each HA service call. If `volume_up` is not in the mapping, the media_player does not expose volume control.

### Auto-Mapping

When a command is assigned via the dropdown (not custom), the action mapping is set automatically because the dropdown selection carries both the display label and the action key. No guessing needed.

Custom-named commands get no auto-mapping. The user can manually assign an action via the command row badge.

## UI Changes

### Assign Signal Dialog - Action Dropdown

When assigning a signal to a device:
1. The command name field becomes a dropdown pre-populated with the device type's action labels
2. "Custom" option at the bottom reveals a freeform text field
3. Selecting a predefined action sets both the command name and the action mapping in one step

### Device Detail - Command Row Action Badge

Each command row gets an inline action badge (left of TEST button):
- Shows the mapped action label (e.g., "Open", "Volume Up") or "NONE" if unmapped
- Styled grey like the Dismiss button when showing "NONE"
- Click to open inline dropdown of all actions for that device type
- Already-assigned actions show which command currently has them
- Picking an assigned action silently reassigns (unmaps from old command, maps to new)
- Picking "NONE" unmaps the action from the command
- No confirmation dialogs needed

### Add Device Dialog

Type dropdown updated with 7 types:
- Media Player
- AC
- Fan
- Light
- Switch
- Screen / Shade
- Other

## Implementation Order

1. Backend: const.py (update DeviceType enum) -> entity_factory.py -> command_templates.py -> device_manager.py
2. Backend: new platform files (light.py, switch.py, cover.py) + media_player.py consolidation
3. Backend: websocket_api.py (action mapping + action options endpoints)
4. Frontend: types.ts -> api.ts -> shared DEVICE_TYPES constant
5. Frontend: assign dialog dropdown -> command row action badge -> device detail wiring
6. Tests for all new backend code
7. Build frontend, run full suite, manual verification

## Design Decisions

- **1:1 type-to-platform mapping** - No sub-types. Media Player covers all audio/video devices. Action mapping handles the variation.
- **No state tracking** - IR has no feedback. We use `assumed_state = True` everywhere.
- **Action keys are the source of truth** - Entity platforms check `command_mapping`, not command names, to determine features.
- **Dropdown-driven mapping** - Picking from the dropdown sets the mapping automatically. No separate mapping step needed.
- **Reassign, don't confirm** - Moving an action from one command to another is a single click. Easy to undo.
- **Shared DEVICE_TYPES constant** - Extract to frontend `constants.ts` to avoid duplication across components.

## Migration

Existing devices with types TV, Soundbar, Projector will need migration to the new `media_player` type. Options:
- Auto-migrate on load: if `device_type` is `tv`/`soundbar`/`projector`, change to `media_player`
- Preserve old type in a `device_subtype` field for display purposes if desired
- Existing `command_mapping` entries carry over unchanged
