# Changelog

All notable changes to HAIR will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-28

### Added

- Native `InfraredReceiverEntity` support (HA 2026.6+). HAIR now subscribes to native receiver entities via `infrared.async_subscribe_receiver()` when available, enabling hardware-agnostic signal capture from any integration that implements the receiver entity. Falls back to the legacy ESPHome event bus bridge on HA 2026.4-2026.5 automatically.
- `NativeCaptureProvider` for capture sessions using native receiver entities. Discovered alongside ESPHome and Broadlink providers in the capture provider list.
- `raw_to_pronto()` encoder function in `ir_command.py` for converting raw signed microsecond timings to Pronto hex strings.
- Native receiver discovery in config flow hardware summary.
- `hair/receivers` WebSocket endpoint for frontend receiver entity listing.
- Receiver section in the Devices tab showing discovered native receiver entities.
- `excludeEntityIds` property on `ir-emitter-picker` to prevent receiver entities from appearing in emitter dropdowns.

### Changed

- Signal monitor refactored with dual-path architecture: native receiver API (primary) with legacy event bus fallback. Shared processing pipeline ensures consistent fingerprinting regardless of receive path.
- Event parser extended with `timings_to_raw()`, `parse_received_signal()`, and `is_native_repeat()` static methods for native `InfraredReceivedSignal` handling.
- Native Timing signals are converted to Pronto hex at the entry point, maintaining fingerprint consistency with the legacy path.
- Capture provider timeout handling improved for Python 3.10 compatibility.

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
