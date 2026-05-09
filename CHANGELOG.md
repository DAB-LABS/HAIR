# Changelog

All notable changes to HAIR will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial integration scaffolding targeting Home Assistant 2026.4+
- Config flow with hardware auto-detection (IR emitters and capture providers)
- Options flow for capture timeout and default repeat count
- Device CRUD via WebSocket API (12 commands under `hair/` prefix)
- IR command capture orchestrator with asyncio-based resource locking
- Capture provider abstraction with ESPHome, Broadlink, and Mock implementations
- Auto-mapping of captured commands to entity features
- Command template system for guided device setup
- Entity platforms: remote, media_player, climate (preset-based), fan
- Device manager with storage-backed persistence
- Admin panel registration (LitElement frontend, bundled JS)
- Unit test suite (169 tests across all modules)
