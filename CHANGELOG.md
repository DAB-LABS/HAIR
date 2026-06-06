# Changelog

All notable changes to HAIR will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-06

### Added

- HAIR Clipper tab. A third panel tab for building virtual remotes by pasting Pronto hex codes, for when you have a code from a converter, a datasheet, or an ESPHome log but no live capture. Create a named remote, then add a signal per button by pasting its Pronto code. The Create Signal dialog validates the code live (a green/red check, the detected carrier frequency, the burst pair count, an S/L diamond preview, and specific error messages that tell you what to fix) and Enter creates the signal once it validates. Pasted signals are first-class peers of sniffed ones: Test, Trigger, Assign, and Promote all work identically.
- Signal aliases. Give any signal a nickname by clicking its S/L diamonds and typing. The alias ("alias" in copper, the name in the diamond blue) replaces the diamonds until you clear it, and an alias never claims to be a command, so the same signal can still become differently-named commands across devices. Available in both the Sniffer and Clipper.
- Two add-command paths on every HAIR device card. The device detail footer now offers "+ Sniffed Signal" and "+ Clipped Signal", jumping to the Sniffer or Clipper so you can add a command by capturing or by pasting.
- The Sniffer signal rows now show each signal's captured carrier frequency (e.g. 38 kHz), matching the Clipper signal rows.
- A clipped remote with no signals can be deleted directly from the Clipper tab (a remote that has signals is removed when its last signal is deleted).

### Changed

- Assigning a signal now keeps it. Previously, assigning a signal to a device consumed it and removed it from the Sniffer or Clipper. Now the signal is copied into the device and stays put, so one signal can be assigned to several devices or as several commands. Only Delete, Dismiss, and Clear All remove a signal, and there is no duplicate guard: assigning the same signal more than once is allowed.
- Clipped (manual) remotes are never auto-evicted. The buffer eviction that ages out old, low-activity sniffed signals now skips manual remotes entirely, so anything you build in Clipper is permanent until you delete it.
- The HAIR Device badge now matches the Promote badge in size and uses uppercase, and the Promote badge moved to a more vivid teal so it reads distinctly from the green.
- Each tab's remote names and cards carry their own accent. Sniffer remote names lead with the blue radio icon and their cards have a subtle blue stroke; Clipper remotes lead with the copper paperclip and a muted copper stroke. The two tabs read as a consistent family while keeping their own identity.
- Remote card titles collapse to a single line (name, counts, and the Promote or HAIR Device badge inline), and the remote name is now edited inline on hover, the same way aliases are, with no pencil icon.
- Header and per-card counts read singular at one ("1 remote", "1 signal", "1 hit").

### Fixed

- The row hover highlight no longer escapes the rounded corners of a card on either tab.

## [0.2.1] - 2026-06-04

### Fixed

- Sniffer would go silent for previously-seen remotes after a specific sequence of dismiss and assign actions, with no UI indication that anything was being dropped. Root cause was an orphaned entry in the persistent dismiss set that survived HA restarts and HACS reinstalls (the device record was removed when the last signal was assigned or deleted, but its fingerprint stayed in the dismiss list). Signals from affected remotes now reach the Sniffer again automatically on the next HA restart after upgrade thanks to a self-heal pass at load time. Reported by @KimmoJ (GH #9) and follow-up by @roblamoreaux.
- Buffer eviction's second pass could independently produce the same orphan when a dismissed device with a low hit count was evicted to make room for new signals. The eviction now skips dismissed devices in both passes.

### Changed

- "Clear All" in the Sniffer now also clears the dismiss list, matching the user mental model of "clear all means clear all." Previously the dismiss list survived Clear All, which contributed to silent orphan accumulation. Users who hit the orphan bug above can use Clear All as an alternative recovery route if they prefer not to wait for the self-heal on restart.
- The Sniffer's Clear All button has moved from the top toolbar to a position below the device list. The Show Dismissed toggle stays in the top toolbar. The relocation pairs visually with the new "clear everything including the dismiss list" semantic and adds a small scroll-past-it speed bump before the destructive action.
- In the Show Dismissed view, the Assign / Test / Trigger buttons on individual signals are now disabled until the remote is restored. Delete stays enabled so users can still clean up unwanted entries. Disabled buttons show a "Restore this remote first" tooltip on hover.

## [0.2.0] - 2026-06-03

### Added

- Native `InfraredReceiverEntity` support (HA 2026.6+). HAIR now subscribes to native receiver entities via `infrared.async_subscribe_receiver()` when available, enabling hardware-agnostic signal capture from any integration that implements the receiver entity. Falls back to the legacy ESPHome event bus bridge on HA 2026.4-2026.5 automatically.
- `NativeCaptureProvider` for capture sessions using native receiver entities. Discovered alongside ESPHome and Broadlink providers in the capture provider list.
- `raw_to_pronto()` encoder function in `ir_command.py` for converting raw signed microsecond timings to Pronto hex strings.
- Native receiver discovery in config flow hardware summary.
- `hair/receivers` WebSocket endpoint for frontend receiver entity listing.
- Receiver section in the Devices tab showing discovered native receiver entities.
- `excludeEntityIds` property on `ir-emitter-picker` to prevent receiver entities from appearing in emitter dropdowns.
- Drag-to-reorder for commands inside a device, backed by `hair/device/reorder-commands` and persisted across reloads.
- NATIVE / BRIDGE badges on receiver and proxy cards so the receive-path migration state is visible at a glance.
- Runtime bridge detection: HAIR listens for legacy `esphome.remote_received` events even in native mode and tags the corresponding hardware so users see which devices still rely on the YAML bridge.
- Device duplicate via `hair/device/duplicate`. Clones a device with all its commands, action mappings, and emitter assignments preserved in one click. Triggers stay attached to the original.
- Sniffer Test emitter picker. Replaces the silent "first emitter on first HAIR device" fallback with an explicit Send from dialog that broadcasts to every picked emitter at once and remembers the choice for the session.
- Card-level duplicate and delete corner actions on every device card so users can clone or remove a device without opening the detail view.
- Quiet blue glow on the Sniffer "Show Dismissed" button when previously hidden remotes are still firing, plus a persistent dot indicator until you click through. Surfaces dismissed-remote activity without re-exposing the signals in the live feed.
- "Show Dismissed" button tooltip reworded to "Restore previously hidden remotes" for clarity.
- Navigation button at the top of the HAIR panel on mobile viewports. Lets phone and tablet users return to the HA sidebar without relying on the edge-swipe gesture. Hidden on desktop.
- `EVENT_DISMISS_ACTIVITY` bus event fired (rate-limited) when a signal arrives from a remote in the dismiss set. Drives the Show Dismissed glow and dot.

### Changed

- Signal monitor refactored with dual-path architecture: native receiver API (primary) with legacy event bus fallback. Shared processing pipeline ensures consistent fingerprinting regardless of receive path.
- Event parser extended with `timings_to_raw()`, `parse_received_signal()`, and `is_native_repeat()` static methods for native `InfraredReceivedSignal` handling.
- Native Timing signals are converted to Pronto hex at the entry point, maintaining fingerprint consistency with the legacy path.
- Capture provider timeout handling improved for Python 3.10 compatibility.
- Panel JS bundle is now read off the event loop during integration startup, silencing HA's blocking-call warning.
- Trigger card trash icon visual style aligned with the device card trash icon for consistency.
- Sniffer signal row mobile layout: on viewports under 768 px, action buttons now sit on a dedicated row below the diamonds and meta instead of floating in the vertical middle of the row. Desktop layout unchanged.

### Fixed

- Missing Device name field in the Assign-to-New-Device dialog on HA 2026.5+. The dialog still used `ha-textfield`, which the same regression silenced for Add Device in v0.1.2 but was missed here. Replaced with a native input element so the field renders on all supported HA versions.
- HAIR Device badge in the Sniffer rendered taller than the Promote badge because the mixed-case text content produced a taller line-box than the uppercase Promote. Added explicit `display: inline-flex; line-height: 1.4` to bound the badge height so both badges read as the same visual weight.

## [0.1.2] - 2026-05-17

### Fixed

- Add "Add Device" button to the tab bar, visible in all states including the zero-device onboarding flow. Previously there was no way to add a device when hardware was detected but no HAIR devices existed yet.
- Fix missing Name field in the Add Device dialog on HA 2026.5+ (`ha-textfield` component no longer renders). Replaced with a native input element.
- Always show the HAIR Devices section header even when no devices exist, with an empty-state hint message.
- Remove redundant floating action button from bottom-right corner.

## [0.1.1] - 2026-05-16

### Fixed

- Fix TX failure on HA 2026.5+ ("Timing object cannot be interpreted as an integer"). The upstream `infrared-protocols` library removed the `Timing` dataclass in v2.0.0, changing `get_raw_timings()` from `list[Timing]` to `list[int]` with signed microseconds. HAIR's `ProntoCommand` and `RawTimingsCommand` adapters now return flat signed integers, compatible with both HA 2026.4 and 2026.5+.
- Add error logging to the send command WebSocket handler. Previously, TX errors were returned to the frontend but not logged in HA logs, making diagnosis difficult.

## [0.1.0] - 2026-05-15

### Added

- Config flow with hardware auto-detection (IR emitters and capture providers)
- Options flow for capture timeout and default repeat count
- Device CRUD via WebSocket API (12 commands under `hair/` prefix)
- Signal Sniffer with real-time IR signal monitoring and device grouping
- Pronto hex fingerprinting with S/L pulse-duration pattern analysis
- Per-signal hit counts, last-seen timestamps, and active indicators
- Inline device rename and promote-to-HAIR-device workflow in Sniffer
- Device-level dismiss/restore for noise filtering
- IR command capture orchestrator with asyncio-based resource locking
- Capture provider abstraction with ESPHome, Broadlink, and Mock implementations
- Multi-emitter TX support (broadcast to multiple IR emitters per device)
- Command template system with device-type-aware dropdown picker
- Action mapping system with popover UI for binding commands to entity features
- Entity platforms: `remote`, `media_player`, `climate`, `fan`, `light`, `switch`, `cover`, `button`
- Device manager with storage-backed persistence
- Admin panel (LitElement/TypeScript frontend) at `/hair` sidebar URL
- Branded header banner on admin panel
- Add Device dialog with name, type, and emitter picker
- Device detail view with inline expand, editable metadata, hardware cards, and command list
- Assign Signal dialog with template command picker and existing/new device modes
- Promote dialog for converting sniffer devices to managed HAIR devices
- HACS compatibility and CI workflow with HACS validation
- Unit test suite (383 tests) covering all backend modules
