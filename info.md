# HAIR

A full admin interface for infrared device management in Home Assistant.

Built on HA's native `infrared` platform (2026.4+), HAIR handles capturing, organizing, and controlling IR commands through a single sidebar panel at `/hair`. No YAML required.

## What you get

- **Native receiver support (HA 2026.6+)** - Captures IR via the new `InfraredReceiverEntity` API, hardware-agnostic. Falls back to the legacy ESPHome event-bus bridge automatically on 2026.4-2026.5.
- **HAIR Sniffer** - Real-time IR signal monitor with fingerprinting, deduplication, and hit tracking. Find a mystery remote in seconds.
- **HAIR Clipper** - Build virtual remotes by pasting Pronto hex codes, with live validation. For commands you have a code for but cannot sniff. The Create Remote dialog can also pick a known manufacturer and model from the device codes in your installed Home Assistant infrared library and pre-fill the buttons for you.
- **Protocol-decoded transmit** - When HAIR can read a captured signal as NEC, it sends clean re-encoded timings instead of replaying the captured ones, which fixes replay failures against destinations that expect undistorted timing. A per-command toggle keeps the captured timings when you want them.
- **Pronto editor** - View or edit a signal's or command's raw Pronto in one editor, with live validation, protocol recognition, and a one-click snap of an off-standard carrier to the nearest IR standard.
- **Send N times** - Give a command a send count so HAIR transmits it more than once per press, for a device that needs the repeat to register.
- **Command rename** - Rename a device command inline on its row or in the editor; action mappings pointed at the old name follow it automatically.
- **Signal aliases** - Name any signal by clicking its diamond pattern, in both the Sniffer and Clipper.
- **IR triggers** - Captured signals become native HA event entities. Any automation can listen for them.
- **Device Management** - Create profiles for TVs, ACs, fans, lights, switches, screens, and more. One-click duplicate to clone a device's commands, mappings, and emitters.
- **Multi-Emitter TX** - Broadcast commands to multiple IR emitters simultaneously. Zone the IR across rooms.
- **Action Mapping** - Bind captured IR commands to HA entity features via dropdown selection.
- **Auto Entities** - Devices get native HA entities (`media_player`, `climate`, `fan`, `light`, `switch`, `cover`, `remote`, `button`).
- **Command Templates** - Device-type-aware guided setup with predefined command names.
- **UX polish** - Drag-to-reorder device cards, remotes, signals, and commands, NATIVE / BRIDGE badges to see migration state at a glance, Sniffer Test with an emitter picker, and a mobile-friendly nav button for phone users.

## Requirements

- Home Assistant 2026.4 or later
- **For capture:** HA 2026.6+ with any integration exposing an `InfraredReceiverEntity`, or HA 2026.4-2026.5 with an ESPHome device running the `remote_receiver` component and an `on_pronto:` bridge action.
- **For send:** any integration on HA's native infrared platform (ESPHome, Tuya Local, Broadlink, SMLIGHT, and any future adopter).
