# Changelog

All notable changes to HAIR will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.20] - 2026-06-19

### Added

- A single Pronto editor for signals and device commands. The old read-only "copy code" popover and the separate paste-a-signal dialog are replaced by one editor you open from the copy/edit glyph on any Sniffer signal, Clipper signal, or device command. It validates the code live (carrier frequency, burst pair count, S/L diamond preview), recognizes a known protocol as you type ("Recognized as NEC"), grows to fit the code so a long Pronto opens fully visible, and lets you copy the code by selecting it (with a keyboard hint, since the panel runs in a context where the browser blocks programmatic clipboard writes on plain http).
- Edit a stored Pronto in place. Change the code on a Sniffer signal, a Clipper signal, or a device command, and HAIR re-evaluates it as if freshly captured (new fingerprint, carrier, and decoded identity). If the edited signal or command has a trigger bound to it and the change shifts the S/L fingerprint, the trigger re-points to the new code automatically, and the editor names the trigger it moved.
- Snap an off-standard carrier to the nearest IR standard. On the Sniffer, when a captured signal's carrier reads off the common consumer standards, the editor shows an amber notice with a one-click "Snap to N kHz" button that re-encodes the Pronto at the nearest standard (30, 33, 36, 38, 40, or 56 kHz). Useful for a receiver whose frequency detection drifts a little. You review the result before saving.
- Rename a device command. Rename a command inline on its row or in the editor, and any action mappings that pointed at the old name follow it to the new name automatically. The editor names any trigger affected by the change.
- Send a command more than once per press. Each device command has a "Send times" count (1 to 10): set it when you assign the signal, or change it later in the command editor. HAIR transmits the whole command that many times with a short gap between sends, for devices that need a repeat to register. A small orange indicator on the command row shows the count when it is greater than 1.

### Changed

- The transmit-mode toggle on a decoded command now reads as the protocol name (for example "NEC") for the clean re-encoded path and "PRONTO" for the captured-replay override, instead of "AUTO" and "RAW". Both states are colored to match the signal's S/L diamonds: blue for the decoded protocol, orange for the captured Pronto.

### Fixed

- Assigning a signal as a standard-action command now wires up the action mapping. Picking a name like "Fan: Auto", "Mode: Cool", or "Power" while assigning previously created the command but left it unmapped, so the ACTIONS button stayed blank and an AC's fan or mode never appeared on the climate entity. The assign path now applies the same auto-mapping the learn path does, including registering an AC's fan and HVAC modes.
- Reordering remotes on the Sniffer no longer snaps back. When the store held a low-hit remote that the Sniffer hides behind its noise filter (or a dismissed remote), the drag list left those out, the reorder was rejected, and the list silently reverted. A reorder now arranges the remotes you can see and leaves the hidden ones exactly where they are.

## [0.4.0] - 2026-06-09

### Added

- Pick a known device when creating a remote. The Create Remote dialog on the Clipper tab gains a Type dropdown: leave it on Blank remote for the usual remote you fill by pasting, or choose a manufacturer and model under "From code library" to materialize a remote pre-filled with one signal per button, each named for its function. The list is whatever device codes your installed Home Assistant infrared library carries (TVs from LG, Samsung, Vizio and Sharp, Sony PlayStation, a few audio and lighting devices). It is a shortcut for the supported devices, not a universal lookup -- anything not listed is still a paste-Pronto away.
- Protocol-decoded matching for NEC-family remotes. When HAIR can read a captured signal as NEC, it records the decoded identity alongside the raw timings. Pressing an already-assigned button is now recognized reliably even when the receiver path jitters the timings, so it no longer leaks back into the Sniffer as an unknown signal.
- Encode-from-decoded transmit. For commands HAIR decoded as NEC, Test and automations send clean, library-encoded timings instead of replaying the captured ones. A per-command toggle (AUTO / RAW) on the device detail lets you fall back to the captured timings for the rare device that wants them.

### Changed

- Transmit uses canonical NEC timings by default for decodable commands, with the per-command opt-out described above. Commands HAIR cannot decode transmit exactly as before.
- The Sniffer empty state now tells "no IR receiver is set up" apart from "no signals yet", so a missing receiver does not look like an idle one.
- The Assign and Trigger dialogs show a signal's name when you have given it one, instead of the raw diamond pattern.
- Diagnostics now report the installed infrared library version and a count of decoded commands by protocol.
- The Clipper now has a persistent "Delete remote" button on every remote, so a remote can be removed in one step instead of deleting each signal first. The confirmation names the remote and how many signals it holds.

### Fixed

- Replaying a captured NEC signal failed against some destinations that expect clean timings (for example a NAD C320BEE bridged setup), because the captured Pronto carried receiver-side timing distortion. Transmitting the re-encoded canonical timings fixes it. Reported by @frafall (GH #14).
- The code-library picker and diagnostics no longer do file-system work on the event loop. Building the manufacturer list and reading the installed library version now run in a worker thread, clearing the blocking-call warnings Home Assistant logged when opening the Create Remote dialog or downloading diagnostics.
- Panel components now register defensively, so a re-evaluated frontend bundle no longer throws a "name has already been used" error in the browser console. The panel rendered correctly either way, but the stray exception is gone.

### Removed

- The Broadlink capture provider. Its learn-mode output was never a sendable IR code, so capturing through it could not work. Broadlink transmit is unaffected. Broadlink receive belongs upstream in the Broadlink integration.

## [0.3.4] - 2026-06-08

### Fixed

- Distinct IR codes that share an S/L fingerprint are now kept as separate signals. Some protocols (the Panasonic and Kaseikyo family, the TCL family, and a handful of similar consumer remotes) have a "long" pulse that sits just below HAIR's S/L threshold, so genuinely different buttons produced the same S/L pattern. The Clipper's duplicate guard then refused the second paste as "already on this remote", and on the Sniffer the two signals collapsed into one. HAIR now adds a byte-level tiebreaker so signals that share a pattern but carry different timing are stored, named, tested, reordered, and assigned independently. Only an identical code is still treated as a duplicate. Reported by @SNMetamorph (GH #13 follow-up) and @akikun21 (GH #16).
- Empty Actions popover on Other-type device cards. The Actions button now hides on devices whose platform (remote) does not expose mappable feature actions, so it no longer opens an empty popover.

## [0.3.3] - 2026-06-07

### Fixed

- Updating a device while its entity was still being registered with Home Assistant could raise "Attribute hass is None for &lt;entity unknown.unknown=unknown&gt;" and roll back the change. The race fired most often when promoting a remote with several commands (each command-add fires a device update before the entity registration coroutine has finished). Affects every HAIR entity platform (media_player, climate, fan, light, switch, cover, remote, button). Each entity's update path now defers state writes until registration completes; the initial state captured at construction time is correct and is written when HA finishes adding the entity. Reported from a Seeed XIAO IR Mate user 2026-06-07.

## [0.3.2] - 2026-06-06

### Added

- Drag-to-reorder across the panel. Drag device cards on the Devices tab, remotes on the Sniffer and Clipper, and the signals within a remote on both tabs. On the Sniffer and Clipper a six-dot grip handle replaces each remote's leading icon (blue on the Sniffer, copper on the Clipper) and a lighter gray grip sits on each signal row; device cards drag by the whole card. The order you set persists across reloads.

### Changed

- The Sniffer and Clipper no longer order remotes by hit count. They use the manual order you set by dragging, and a newly seen remote or newly added signal appears at the top until you move it. Existing lists are seeded once from the previous hit-count order on upgrade so nothing jumps around.
- Renamed the Clipper's add buttons to match the Devices tab. The top-right "Create" is now "Add Remote" (mirroring "Add Device"), and the in-card "Create" is now "Add Signal". The in-card button is a lighter borderless text action instead of a pill.

### Fixed

- The Clipper no longer accepts a Pronto code that is already on the remote. Previously a repeated paste created a second signal with the same fingerprint that could not be used independently and broke reordering. Pasting a duplicate now returns a clear message, and any duplicate created by an earlier version is removed automatically on the next restart.

## [0.3.1] - 2026-06-06

### Added

- A copy control on every signal row (Sniffer and Clipper) opens a small popover showing the signal's raw Pronto code in a selectable box, with a Copy button. Copy works on plain http via a clipboard fallback, and the code is always selectable so you can copy it by hand if needed.

### Changed

- The Clipper's "Create" button moved to the top-right of the tab bar, matching the Devices tab's "Add Device" button (kept in the Clipper's copper accent). The Show Dismissed toggle stays in the Clipper header.

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
