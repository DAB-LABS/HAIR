# HAIR UI Redesign: Unified Palette and Layout

Status: Planning
Date: 2026-05-13

---

## Overview

Unify the HAIR frontend around the Sniffer page's color palette and
interaction patterns. Redesign the Devices page with four hardware
sections, inline device detail expansion, and consistent card styling.

## Color palette (canonical)

All pages will use this shared palette. No blue TX / green RX
distinction -- color encodes purpose, not hardware role.

| Role           | Color                        | Usage                               |
|----------------|------------------------------|-------------------------------------|
| Action/active  | `#2e7d32` / `rgba(46,125,50)`| Buttons, active states, glow pulses |
| Informational  | `#ff9800` / `rgba(255,152,0)`| Device type badges, metadata accents|
| Destructive    | `#b71c1c` / `rgba(183,28,28)`| Delete buttons only                 |
| Neutral        | HA theme vars                | Borders, backgrounds, text          |
| Diamonds       | `var(--primary-color)` (long), `var(--warning-color)` (short) | Signal fingerprint display |

The blue (`#1e88e5` / `#1565c0`) TX accent and green (`#43a047` /
`#2e7d32`) RX accent currently used on the Devices page and device
detail Hardware cards will be replaced with the unified palette above.

---

## Phase 1: Sniffer signal hit animations

**Files:** `ir-signal-monitor.ts`

### Current behavior
- Device label row gets blue glow on new signal hit
- Last 2 signal Assign buttons turn solid green (`recent` class)
- Assign button gets green glow pulse on hit (`glow` class)
- Hit count text is static

### Changes
1. Add glow animation to the hit count `<span>` when a signal fires.
   Reuse the same `@keyframes` pattern as the device label but scoped
   to the hit count element. On new signal event, add a `hit-flash`
   class to the matching signal row's hit count, remove after 1.2s.

2. Differentiate the two "recent" signal states:
   - Most recent signal (index 0 in `_recentFingerprints`): current
     bright green (`#2e7d32`) on Assign button + glow pulse on hit
   - Previous signal (index 1): muted green
     (`rgba(46,125,50, 0.5)` text, `rgba(46,125,50, 0.15)` border)
     No glow animation.

### New CSS
```css
.signal-meta .hit-flash {
    animation: hit-glow 1.2s ease-out;
}
@keyframes hit-glow {
    0% { color: #2e7d32; text-shadow: 0 0 6px rgba(46,125,50, 0.8); }
    100% { color: inherit; text-shadow: none; }
}

/* Most recent vs previous signal */
.action-btn.assign-btn.recent-latest {
    color: #fff;
    background: #2e7d32;
    border-color: #2e7d32;
}
.action-btn.assign-btn.recent-previous {
    color: rgba(46, 125, 50, 0.6);
    border-color: rgba(46, 125, 50, 0.25);
}
```

---

## Phase 2: Command row styling

**Files:** `ir-command-row.ts`

### Changes
1. Add row delineation: `border-bottom: 1px solid var(--divider-color)`
   on each `.row` except `:last-child`. Remove the border-radius from
   rows (they stack vertically, not floating).

2. Unify button colors with sniffer palette:
   - Test button: green outline (`#2e7d32` text, green border)
   - Re-learn button: neutral (current style, `--primary-color`)
   - Delete button: red (already correct)
   - Learn button: green filled (`#2e7d32` bg, white text) since it's
     the primary action for unlearned commands

3. Swap the status dot to green (`#2e7d32`) for learned commands
   instead of `--primary-color` (blue).

---

## Phase 3: Device detail redesign

**Files:** `ir-device-detail.ts`

### Layout: Option B (metadata grid)

Replace the current `device-fields` flex row and Hardware cards section
with a single metadata grid. The grid uses label-value rows for device
type and emitter picker.

```
+--------------------------------------------------+
| Living Room TV  [edit icon]           [Delete]    |
+--------------------------------------------------+
| TYPE      | [dropdown: TV / Monitor]              |
| EMITTERS  | [chip] [chip] [+ add]                 |
+--------------------------------------------------+
| COMMANDS (4)                                      |
| ------------------------------------------------ |
|  * power_toggle   [diamonds]    [Test] [Delete]   |
| ------------------------------------------------ |
|  * vol_up         [diamonds]    [Test] [Delete]   |
| ------------------------------------------------ |
|  * vol_down       [diamonds]    [Test] [Delete]   |
| ------------------------------------------------ |
|  * mute           [diamonds]    [Test] [Delete]   |
+--------------------------------------------------+
| [+ Add Command]                                   |
+--------------------------------------------------+
```

### Specific changes

1. Remove the Hardware section entirely (TX cards, RX card). The
   emitter picker already shows which blasters are assigned, and is
   interactive. The RX/capture info is secondary metadata.

2. Replace `device-fields` div with a CSS grid:
   ```css
   .device-meta {
       display: grid;
       grid-template-columns: 80px 1fr;
       gap: 8px 12px;
       align-items: center;
       margin: 12px 0 0;
   }
   ```

3. Apply sniffer palette:
   - Delete button: red (`#b71c1c`)
   - Device type badge uses amber accent if displayed as pill
   - Command row buttons follow Phase 2 styling
   - Toast notification stays `--primary-color` (neutral feedback)

---

## Phase 4: Inline device detail expand

**Files:** `ha-panel-ir-devices.ts`, `ir-device-list.ts`,
`ir-device-detail.ts`

### Architecture change

Currently, selecting a device navigates to a full-page detail view
(hides tabs, shows back arrow in app bar). The new pattern expands the
device detail inline below the selected card.

### Panel changes (`ha-panel-ir-devices.ts`)

1. Remove `_selectedDevice` as a navigation driver. Instead, pass an
   `expandedDeviceId` prop down to `ir-device-list`.

2. Keep tabs visible at all times (no more `showTabs` conditional).

3. Remove the `history.pushState` URL-based routing for device detail.
   Expanding a card is a UI state change, not a navigation event.

4. The app bar title stays "HAIR" regardless of expand state.

### Device list changes (`ir-device-list.ts`)

1. Accept `expandedDeviceId: string | null` property.

2. When a device card is clicked:
   - If it's already expanded, collapse it (`expandedDeviceId = null`)
   - Otherwise, fire `device-selected` (panel sets `expandedDeviceId`)

3. Render `ir-device-detail` inline below the expanded card, outside
   the grid, spanning full width:
   ```html
   ${device.id === this.expandedDeviceId
       ? html`</div><!-- close grid temporarily -->
              <div class="expanded-detail">
                  <ir-device-detail ...></ir-device-detail>
              </div>
              <div class="grid"><!-- reopen grid -->`
       : ""}
   ```
   
   Better approach: render the grid items as a flat list with detail
   rows injected after the expanded card. Use CSS `grid-column: 1 / -1`
   on the detail row to span the full grid width.

4. Add a subtle expand/collapse animation (max-height transition or
   similar).

### Device detail changes (`ir-device-detail.ts`)

1. Emit `collapse` event instead of relying on back-navigation.
   The parent list component handles the state.

2. Add a collapse/close affordance (chevron or X in the header area).

---

## Phase 5: Four-section devices page

**Files:** `ir-device-list.ts`, possibly `api.ts` / `types.ts`

### Four sections

```
DEVICES     (3)
+--------+  +--------+  +--------+
| TV     |  | AC     |  | Fan    |
+--------+  +--------+  +--------+

EMITTERS    (2)
+--------+  +--------+
| Living |  | Bed    |
+--------+  +--------+

RECEIVERS   (1)
+--------+
| HAIR1  |
+--------+

PROXIES     (1)
+--------+
| HAIR1  |      (shows TX + RX capability badges)
+--------+
```

### Data sources (no new backend needed)

| Section   | Source                           | Currently used in         |
|-----------|----------------------------------|---------------------------|
| Devices   | `api.listDevices()`              | Device list (existing)    |
| Emitters  | `hass.states` infrared.* entities | Device list (existing)    |
| Receivers | `api.listCaptureProviders()`     | Add-device dialog, device list proxies section |
| Proxies   | `api.listUnknownDevices()`       | Sniffer page              |

Note: Receivers and Proxies may overlap (same ESPHome board might be
both a capture provider and a sniffer proxy). Cards should show
capability badges (TX, RX) to clarify what each device can do.

### Unified card design

All four sections use the same card template. Cards should be compact
and consistent.

```
+---------------------------------------+
| [icon]  Device Name                   |
| metadata line (type, entity_id, etc.) |
| [badge: TX] [badge: RX] [badge: N cmds] |
+---------------------------------------+
```

Card styling (sniffer palette):
- Background: `var(--card-background-color)`
- Border: `1px solid var(--divider-color)`
- Border-radius: 8px
- Hover: subtle lift (`translateY(-1px)`, light shadow)
- No colored backgrounds per section -- color lives in badges only

Badge colors:
- Device command count: green badge (`rgba(46,125,50, 0.15)` bg,
  `#2e7d32` text)
- TX capability: amber badge (`rgba(255,152,0, 0.15)` bg,
  `#e65100` text)
- RX capability: amber badge (same -- both are hardware capabilities)
- Device type: amber pill in card metadata

Section header styling:
- Consistent across all four: uppercase label, count pill, bottom
  border in green (`#2e7d32`) for all sections (unified, no
  per-section color coding)

### Card sizing

Current cards at `minmax(260px, 1fr)` are a bit large. Reduce to
`minmax(200px, 1fr)` for a tighter grid. Reduce vertical padding
from 16px to 12px.

---

## Implementation order

| Phase | Scope                          | Files changed | Risk  |
|-------|--------------------------------|---------------|-------|
| 1     | Signal hit animations          | 1             | Low   |
| 2     | Command row styling            | 1             | Low   |
| 3     | Device detail layout           | 1             | Low   |
| 4     | Inline expand                  | 3             | Medium|
| 5     | Four-section page + cards      | 1-2           | Medium|

Each phase is independently committable and testable. Phases 1-3 are
CSS/template-only changes with no architectural impact. Phases 4-5
involve structural changes to component relationships.

---

## Out of scope

- Backend API changes (none needed)
- New WebSocket endpoints
- Dark mode rework (HA vars handle this)
- Mobile-specific responsive breakpoints (keep current auto-fit grid)
