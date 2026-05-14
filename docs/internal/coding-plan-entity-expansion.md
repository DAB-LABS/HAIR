# Coding Plan: Entity Platform Expansion + Action Mapping

## Summary

7 device types (1:1 platform mapping), action mapping via dropdown, inline action badge on command rows, remove Re-learn button. Migrate old TV/Soundbar/Projector types to Media Player on load.

## Phase 1: Backend - Types and Templates

### Step 1: Update `const.py`

**File:** `custom_components/hair/const.py`

Changes:
- Replace DeviceType enum members:
  ```python
  class DeviceType(StrEnum):
      MEDIA_PLAYER = "media_player"
      AC = "ac"
      FAN = "fan"
      LIGHT = "light"
      SWITCH = "switch"
      SCREEN = "screen"
      OTHER = "other"
  ```
- Add CommandCategory members: `BRIGHTNESS = "brightness"`, `COVER = "cover"`, `MEDIA_CONTROL = "media_control"`
- Update PLATFORMS list: add `"light"`, `"switch"`, `"cover"`

### Step 2: Update `command_templates.py`

**File:** `custom_components/hair/command_templates.py`

Changes:
- Remove entries for `DeviceType.TV`, `DeviceType.SOUNDBAR`, `DeviceType.PROJECTOR`
- Add `DeviceType.MEDIA_PLAYER` with superset template (~20 commands):
  Power On, Power Off, Volume Up, Volume Down, Mute, Source/Input, Channel Up, Channel Down, Up, Down, Left, Right, Select/OK, Back/Return, Guide, Menu, Play, Pause, Stop, Rewind, Fast Forward
- Add `DeviceType.LIGHT`: On, Off, Brightness Up, Brightness Down
- Add `DeviceType.SWITCH`: On, Off
- Add `DeviceType.SCREEN`: Open, Close, Stop
- Keep AC, FAN, OTHER unchanged

### Step 3: Add ACTION_OPTIONS constant

**File:** `custom_components/hair/command_templates.py` (add at bottom)

New constant mapping DeviceType to list of `(action_key, label)` tuples. This is the canonical source for dropdown options:

```python
ACTION_OPTIONS: dict[DeviceType, list[tuple[str, str]]] = {
    DeviceType.MEDIA_PLAYER: [
        ("turn_on", "Power On"),
        ("turn_off", "Power Off"),
        ("power_toggle", "Power Toggle"),
        ("volume_up", "Volume Up"),
        ("volume_down", "Volume Down"),
        ("mute", "Mute"),
        ("select_source", "Source/Input"),
        ("channel_up", "Channel Up"),
        ("channel_down", "Channel Down"),
        ("navigate_up", "Up"),
        ("navigate_down", "Down"),
        ("navigate_left", "Left"),
        ("navigate_right", "Right"),
        ("navigate_select", "Select/OK"),
        ("navigate_back", "Back/Return"),
        ("guide", "Guide"),
        ("menu", "Menu"),
        ("play", "Play"),
        ("pause", "Pause"),
        ("stop", "Stop"),
        ("rewind", "Rewind"),
        ("fast_forward", "Fast Forward"),
    ],
    DeviceType.AC: [
        ("turn_on", "Power On"),
        ("turn_off", "Power Off"),
        ("mode_cool", "Mode: Cool"),
        ("mode_heat", "Mode: Heat"),
        ("mode_fan_only", "Mode: Fan"),
        ("mode_dry", "Mode: Dry"),
        ("mode_auto", "Mode: Auto"),
        ("fan_low", "Fan: Low"),
        ("fan_medium", "Fan: Medium"),
        ("fan_high", "Fan: High"),
        ("fan_auto", "Fan: Auto"),
        ("swing_toggle", "Swing Toggle"),
    ],
    DeviceType.FAN: [
        ("turn_on", "Power"),
        ("turn_off", "Power Off"),
        ("power_toggle", "Power Toggle"),
        ("speed_up", "Speed Up"),
        ("speed_down", "Speed Down"),
        ("oscillate", "Oscillate"),
    ],
    DeviceType.LIGHT: [
        ("turn_on", "On"),
        ("turn_off", "Off"),
        ("brightness_up", "Brightness Up"),
        ("brightness_down", "Brightness Down"),
    ],
    DeviceType.SWITCH: [
        ("turn_on", "On"),
        ("turn_off", "Off"),
    ],
    DeviceType.SCREEN: [
        ("open_cover", "Open"),
        ("close_cover", "Close"),
        ("stop_cover", "Stop"),
    ],
    DeviceType.OTHER: [],
}
```

### Step 4: Update `device_manager.py`

**File:** `custom_components/hair/device_manager.py`

Changes:
- Add new AUTO_MAP_RULES entries:
  ```python
  "on": "turn_on",
  "off": "turn_off",
  "brightness up": "brightness_up",
  "brightness down": "brightness_down",
  "open": "open_cover",
  "close": "close_cover",
  "stop": "stop_cover",
  "guide": "guide",
  "menu": "menu",
  "play": "play",
  "pause": "pause",
  "rewind": "rewind",
  "fast forward": "fast_forward",
  ```
- Update `_human_device_type()`: remove TV/Soundbar/Projector entries, add Media Player, Light, Switch, Screen

### Step 5: Update `entity_factory.py`

**File:** `custom_components/hair/entity_factory.py`

Changes:
- Replace DEVICE_TYPE_TO_PLATFORM:
  ```python
  DEVICE_TYPE_TO_PLATFORM = {
      DeviceType.MEDIA_PLAYER: "media_player",
      DeviceType.AC: "climate",
      DeviceType.FAN: "fan",
      DeviceType.LIGHT: "light",
      DeviceType.SWITCH: "switch",
      DeviceType.SCREEN: "cover",
      DeviceType.OTHER: "remote",
  }
  ```

### Step 6: Update `models.py` - Migration

**File:** `custom_components/hair/models.py`

Changes:
- In `IRDevice.from_dict()`, add migration for old device types:
  ```python
  raw_type = data.get("device_type", DeviceType.OTHER)
  # Migrate legacy types to media_player
  _LEGACY_MEDIA_TYPES = {"tv", "soundbar", "projector"}
  if raw_type in _LEGACY_MEDIA_TYPES:
      raw_type = "media_player"
  device_type = DeviceType(raw_type)
  ```

### Step 7: Update `__init__.py`

**File:** `custom_components/hair/__init__.py`

Changes:
- Add `Platform.LIGHT`, `Platform.SWITCH`, `Platform.COVER` to PLATFORMS_LIST

## Phase 2: Backend - New Entity Platforms

### Step 8: Update `media_player.py`

**File:** `custom_components/hair/media_player.py`

Changes:
- Replace `MEDIA_PLAYER_DEVICE_TYPES` set with single check: `device.device_type == DeviceType.MEDIA_PLAYER`
- Add media transport features to `supported_features`:
  ```python
  if "play" in mapping:
      features |= MediaPlayerEntityFeature.PLAY
  if "pause" in mapping:
      features |= MediaPlayerEntityFeature.PAUSE
  if "stop" in mapping:
      features |= MediaPlayerEntityFeature.STOP
  ```
- Add `async_media_play`, `async_media_pause`, `async_media_stop` methods

### Step 9: Create `light.py`

**File:** `custom_components/hair/light.py`

New file modeled after `fan.py`:
- Filter: `device.device_type == DeviceType.LIGHT`
- `_attr_assumed_state = True`
- `_attr_color_mode = ColorMode.ONOFF` (upgrade to BRIGHTNESS if brightness commands mapped)
- `supported_color_modes` based on command_mapping
- `async_turn_on` -> send "turn_on" action
- `async_turn_off` -> send "turn_off" action
- Assumed brightness tracked internally, step via brightness_up/brightness_down
- unique_id: `hair_{device.id}_light`

### Step 10: Create `switch.py`

**File:** `custom_components/hair/switch.py`

New file modeled after `fan.py` (simplest platform):
- Filter: `device.device_type == DeviceType.SWITCH`
- `_attr_assumed_state = True`
- `_attr_device_class = SwitchDeviceClass.SWITCH`
- `async_turn_on` / `async_turn_off` only
- unique_id: `hair_{device.id}_switch`

### Step 11: Create `cover.py`

**File:** `custom_components/hair/cover.py`

New file modeled after `fan.py`:
- Filter: `device.device_type == DeviceType.SCREEN`
- `_attr_assumed_state = True`
- `_attr_device_class = CoverDeviceClass.SHADE`
- Dynamic features based on command_mapping:
  - `open_cover` mapped -> `CoverEntityFeature.OPEN`
  - `close_cover` mapped -> `CoverEntityFeature.CLOSE`
  - `stop_cover` mapped -> `CoverEntityFeature.STOP`
- unique_id: `hair_{device.id}_cover`

## Phase 3: Backend - Action Mapping WS Endpoints

### Step 12: Add WS endpoints to `websocket_api.py`

**File:** `custom_components/hair/websocket_api.py`

New commands:

**`hair/device/action-options`** - Returns dropdown options for a device type:
```python
vol.Required("device_type"): str
```
Returns: `[{"key": "turn_on", "label": "Power On"}, ...]`

**`hair/device/update-mapping`** - Set or clear an action mapping on a device:
```python
vol.Required("device_id"): str,
vol.Required("command_id"): str,
vol.Optional("action"): vol.Any(str, None),
```
Handler:
1. Find device, find command by ID
2. If action is not None: remove any existing mapping with that action key (reassign), then set `command_mapping[action] = command.name`
3. If action is None: find and remove any mapping whose value matches this command's name
4. Save and trigger entity update
5. Return updated device

Also register both new commands in `async_register_websocket_commands`.

## Phase 4: Frontend - Types and API

### Step 13: Update `types.ts`

**File:** `frontend/src/types.ts`

Changes:
- Update DeviceTypeId:
  ```typescript
  export type DeviceTypeId =
      | "media_player" | "ac" | "fan" | "light" | "switch" | "screen" | "other";
  ```
- Add CommandCategoryId values: `"brightness"`, `"cover"`, `"media_control"`
- Add interface:
  ```typescript
  export interface ActionOption {
      key: string;
      label: string;
  }
  ```

### Step 14: Create `constants.ts`

**File:** `frontend/src/constants.ts`

New shared file to eliminate DEVICE_TYPES duplication:
```typescript
export const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "AC" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];
```

### Step 15: Update `api.ts`

**File:** `frontend/src/api.ts`

Add methods:
- `getActionOptions(deviceType: DeviceTypeId): Promise<ActionOption[]>` -- calls `hair/device/action-options`
- `updateCommandMapping(deviceId: string, commandId: string, action: string | null): Promise<IRDevice>` -- calls `hair/device/update-mapping`

## Phase 5: Frontend - Assign Dialog Dropdown

### Step 16: Update `ir-assign-signal-dialog.ts`

**File:** `frontend/src/ir-assign-signal-dialog.ts`

Changes:
- Import DEVICE_TYPES from constants.ts (remove local array)
- Add state: `@state() private _actionOptions: ActionOption[] = []`
- Add state: `@state() private _selectedActionKey: string = ""`
- Add state: `@state() private _customMode: boolean = false`
- When device is selected (existing mode) or device type changes (new mode), fetch action options via `this.api.getActionOptions(deviceType)`
- Replace `_renderCommandPicker()`:
  - Show `<select>` dropdown with action options + "Custom..." at bottom
  - When a standard action is selected: set `_commandName` to label, `_selectedActionKey` to key, `_customMode = false`
  - When "Custom" is selected: show freeform `<ha-textfield>`, `_customMode = true`, `_selectedActionKey = ""`
- On assign/assign-new-device: pass `_selectedActionKey` as optional `action_key` param (or rely on AUTO_MAP_RULES since dropdown label matches template name)

### Step 17: Update `ws_assign_signal` and `ws_assign_new_device`

**File:** `custom_components/hair/websocket_api.py`

Changes:
- Add `vol.Optional("action_key"): vol.Any(str, None)` to both handlers
- After command is created, if `action_key` is provided, explicitly set `command_mapping[action_key] = command_name` on the device and save

## Phase 6: Frontend - Command Row Action Badge

### Step 18: Update `ir-command-row.ts`

**File:** `frontend/src/ir-command-row.ts`

Changes:
- Add properties:
  ```typescript
  @property({ attribute: false }) public actionOptions: ActionOption[] = [];
  @property({ attribute: false }) public commandMapping: Record<string, string> = {};
  ```
- Add state: `@state() private _showActionDropdown = false;`
- Remove the Re-learn button and `relearn` event emit
- Add action badge in `.actions` div (before TEST button):
  ```html
  <button class="action-btn action-badge ${mapped ? '' : 'unmapped'}"
      @click=${this._toggleActionDropdown}>
      ${currentActionLabel}
  </button>
  ```
- When dropdown is open, render positioned `<div class="action-dropdown">` with:
  - Each action option as a row (show "(Command X)" if already assigned to another command)
  - "NONE" option to unmap
  - Click dispatches `map-action` event with `{commandId, actionKey}` or `{commandId, actionKey: null}`
- Close dropdown on outside click (use `@blur` or document click listener)
- Add CSS for `.action-badge`, `.action-badge.unmapped`, `.action-dropdown`

### Step 19: Update `ir-device-detail.ts`

**File:** `frontend/src/ir-device-detail.ts`

Changes:
- Import DEVICE_TYPES from constants.ts (remove local array)
- Add state: `@state() private _actionOptions: ActionOption[] = []`
- Load action options when device loads/changes: `this.api.getActionOptions(this.device.device_type)`
- Pass to command rows:
  ```html
  <ir-command-row
      .templateName=${cmd.name}
      .command=${cmd}
      .actionOptions=${this._actionOptions}
      .commandMapping=${this.device.entity_config.command_mapping}
      .busy=${this._busy}
      @test=${this._onTest}
      @delete=${this._onDelete}
      @map-action=${this._onMapAction}
  ></ir-command-row>
  ```
- Remove `@relearn` handler and `_onRelearn` method
- Add `_onMapAction` handler:
  ```typescript
  private async _onMapAction(e: CustomEvent) {
      const { commandId, actionKey } = e.detail;
      await this.api.updateCommandMapping(this.device.id, commandId, actionKey);
      // Refresh device data
  }
  ```

### Step 20: Update `ir-add-device-dialog.ts`

**File:** `frontend/src/ir-add-device-dialog.ts`

Changes:
- Import DEVICE_TYPES from constants.ts (remove local array)

## Phase 7: Tests

### Step 21: Update existing tests

Files:
- `tests/test_config_flow.py` - no changes needed (doesn't reference DeviceType)
- `tests/test_device_manager.py` - update `_human_device_type` assertions, update any DeviceType.TV references to DeviceType.MEDIA_PLAYER
- `tests/test_entity_factory.py` - update platform mapping assertions
- `tests/test_command_templates.py` - update for new type names, add tests for new types

### Step 22: Add tests for new platforms

Files:
- `tests/test_light.py` - test turn_on/off, brightness stepping, feature detection from mapping
- `tests/test_switch.py` - test turn_on/off, assumed state
- `tests/test_cover.py` - test open/close/stop, feature detection from mapping

### Step 23: Add tests for action mapping

File: `tests/test_websocket_api.py` (or new `tests/test_action_mapping.py`)
- Test `hair/device/action-options` returns correct options per type
- Test `hair/device/update-mapping` sets mapping
- Test reassign: mapping moves from old command to new
- Test unmap: action=None removes mapping
- Test migration: device with `device_type: "tv"` loads as `media_player`

## Phase 8: Build and Verify

### Step 24: Run full test suite

```bash
python -m pytest custom_components/hair/tests/ -v
```

### Step 25: Build frontend

```bash
cd custom_components/hair/frontend && npm run build
```

### Step 26: Manual verification

1. Existing devices migrate correctly (TV -> Media Player)
2. Add device dialog shows 7 types
3. Create a Light device, assign On/Off/Brightness Up/Down via dropdown
4. Verify light entity appears in HA with correct features
5. Create a Screen device, assign Open/Close/Stop
6. Verify cover entity with open/close/stop buttons
7. Create a Switch device, verify on/off
8. Action badge shows on command rows, click to reassign
9. Reassigning an action from one command to another works
10. Custom command name works (no action mapping)
11. No Re-learn button on command rows

## File Change Summary

### Modified files (14):
1. `const.py` - DeviceType enum, CommandCategory, PLATFORMS
2. `command_templates.py` - templates + ACTION_OPTIONS
3. `device_manager.py` - AUTO_MAP_RULES, _human_device_type
4. `entity_factory.py` - DEVICE_TYPE_TO_PLATFORM
5. `models.py` - migration in from_dict
6. `__init__.py` - PLATFORMS_LIST
7. `media_player.py` - single type check, transport features
8. `websocket_api.py` - two new WS commands, action_key param on assign
9. `frontend/src/types.ts` - DeviceTypeId, ActionOption
10. `frontend/src/api.ts` - new API methods
11. `frontend/src/ir-command-row.ts` - action badge, remove Re-learn
12. `frontend/src/ir-assign-signal-dialog.ts` - action dropdown
13. `frontend/src/ir-device-detail.ts` - wire action mapping, remove relearn
14. `frontend/src/ir-add-device-dialog.ts` - import shared DEVICE_TYPES

### New files (4):
1. `light.py` - Light entity platform
2. `switch.py` - Switch entity platform
3. `cover.py` - Cover entity platform
4. `frontend/src/constants.ts` - Shared DEVICE_TYPES array

### New test files (3):
1. `tests/test_light.py`
2. `tests/test_switch.py`
3. `tests/test_cover.py`
