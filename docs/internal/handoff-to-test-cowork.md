# HAIR — Handoff to Test & Manage Cowork

**From:** Planning + Code Cowork sessions
**To:** Test & Manage Cowork (new session)
**Date:** 2026-05-08
**Author:** David Bailey
**Status:** Active handoff — read this first

---

## What HAIR Is

HAIR (Home Assistant IR) is a third-party Home Assistant custom integration that provides a unified admin interface for capturing, managing, and organizing infrared (IR) commands and devices. It's built on HA's native infrared platform (released in 2026.4). No YAML required. Works with any IR proxy (ESPHome, Broadlink, etc.).

For full context, read in this order:

1. `docs/internal/scope-ha-ir-admin.md` — One-page project scope
2. `docs/internal/plans/integration-plan-v2.md` — The locked integration plan (post-trio-review)
3. `docs/internal/architecture/code-architecture.md` — The blueprint Code worked from
4. `docs/internal/branding/brand-guide.md` — Branding (Hairy Hank, color palette, voice)

The pitch deck (`HAIR-pitch-deck.html`) at the repo root is a fun marketing artifact — read it last for context, skip if you're focused on testing.

---

## Your Mission, Test & Manage Cowork

You are taking over a codebase that:
- ✅ Was built by a previous Code session against the locked architecture document
- ✅ Has a working Python integration (~3,800 lines), a TypeScript frontend (~2,000 lines, 59KB bundle), and a partial test suite
- ❌ Has not been tested against a real Home Assistant instance
- ❌ Has no CI pipeline
- ❌ Has no top-level repo documentation (no README.md, no LICENSE, no HACS manifest)
- ❌ Has incomplete test coverage

**Your job is to take HAIR from "code exists" to "code ships."** That means:

1. Verify the code runs in a real HA instance
2. Build out test coverage to confidence-shipping levels
3. Add the missing repo infrastructure (README, LICENSE, hacs.json, CI)
4. Catch and fix bugs as you find them
5. Validate the UX flows actually work end-to-end with real IR hardware (or simulated)

You are NOT writing new features. The architecture is locked. You are stress-testing what exists, hardening it, and getting it ready for the world.

---

## Repo Inventory — What's Here

### Top-level structure

```
HAIR/
├── HAIR-pitch-deck.html               # Marketing deck (separate concern)
├── custom_components/
│   └── hair/                          # The integration itself
│       ├── __init__.py                # Setup/teardown + panel registration (158 lines)
│       ├── manifest.json              # Integration metadata
│       ├── const.py                   # Constants & enums (88 lines)
│       ├── models.py                  # Dataclasses (296 lines)
│       ├── storage.py                 # Persistent storage (126 lines)
│       ├── config_flow.py             # Config + options flow (130 lines)
│       ├── capture.py                 # CaptureProvider ABC + ESPHome/Broadlink/Mock (372 lines)
│       ├── capture_orchestrator.py    # Session management + locking (221 lines)
│       ├── device_manager.py          # Device CRUD (269 lines)
│       ├── entity_factory.py          # Entity creation (107 lines)
│       ├── command_templates.py       # Per-device-type command suggestions (79 lines)
│       ├── websocket_api.py           # WebSocket command handlers (518 lines)
│       ├── remote.py                  # Remote entity (147 lines)
│       ├── media_player.py            # Media player entity (177 lines)
│       ├── climate.py                 # Climate entity (236 lines)
│       ├── fan.py                     # Fan entity (169 lines)
│       ├── diagnostics.py             # Diagnostics (35 lines)
│       ├── icons.json                 # Custom entity icons
│       ├── strings.json               # UI strings (English)
│       ├── translations/
│       │   └── en.json                # English translations
│       ├── frontend/
│       │   ├── package.json           # npm config (lit, rollup, typescript)
│       │   ├── rollup.config.mjs      # Build config
│       │   ├── tsconfig.json          # TypeScript config
│       │   ├── src/
│       │   │   ├── ha-panel-ir-devices.ts   # Main panel entry (210 lines)
│       │   │   ├── ir-device-list.ts        # Device list view (172 lines)
│       │   │   ├── ir-device-detail.ts      # Device detail + checklist (476 lines)
│       │   │   ├── ir-capture-dialog.ts     # 2-phase capture dialog (396 lines)
│       │   │   ├── ir-add-device-dialog.ts  # Add device flow (299 lines)
│       │   │   ├── ir-command-row.ts        # Single command row (126 lines)
│       │   │   ├── ir-progress-bar.ts       # Setup progress bar (57 lines)
│       │   │   ├── api.ts                   # WebSocket API client (172 lines)
│       │   │   └── types.ts                 # TypeScript types (118 lines)
│       │   └── dist/
│       │       └── ha-panel-ir-devices.js   # Bundled output (59KB, committed)
│       └── tests/
│           ├── conftest.py              # Test fixtures (87 lines)
│           ├── test_models.py           # 133 lines
│           ├── test_storage.py          # 88 lines
│           ├── test_capture.py          # 128 lines
│           ├── test_device_manager.py   # 166 lines
│           ├── test_entity_factory.py   # 47 lines
│           └── test_command_templates.py # 32 lines
└── docs/
    └── internal/
        ├── scope-ha-ir-admin.md
        ├── handoff-to-test-cowork.md      ← (this file)
        ├── research/                       # 3 research docs
        ├── plans/                          # v1 + v2 integration plans
        ├── reviews/                        # Trio review boards v1 + v2
        ├── architecture/                   # Code architecture + self-review
        └── branding/                       # Brand guide + assets folder
```

### What Code Built — Quick Read

- **5,836 total lines of code** across 36 files
- **Python:** ~3,800 lines (integration logic)
- **TypeScript:** ~2,000 lines (frontend panel)
- **Tests:** ~681 lines across 6 test files (clearly incomplete — see gaps below)
- **Frontend bundle:** 59KB (`frontend/dist/ha-panel-ir-devices.js`)
- **No top-level README, LICENSE, or HACS manifest yet**

---

## Architectural Touchstones (So You Know What "Right" Looks Like)

These are the design decisions Code implemented. If a test fails or behavior seems weird, check the code against these:

1. **HAIR is a hub integration** — single config entry hosts all IR devices. Adding/managing devices happens in the admin panel, NOT through the config flow. The config flow only does initial setup detection.

2. **Hard dependency on `infrared` (HA 2026.4+)** — the integration won't load without it. `manifest.json` declares this in `dependencies`.

3. **Soft dependencies on ESPHome and Broadlink** — declared in `after_dependencies`. HAIR works without them but capture providers need them.

4. **CaptureProvider is an ABC with three implementations:**
 - `ESPHomeCaptureProvider` — subscribes to ESPHome native API for IR receiver events
 - `BroadlinkCaptureProvider` — uses Broadlink learning mode polling
 - `MockCaptureProvider` — for tests, returns canned `CaptureResult`

5. **Capture orchestration uses an `asyncio.Lock`** for concurrency protection — only one capture session at a time per HA instance.

6. **Storage is a single `.storage/hair_devices` JSON file** with versioned schema (currently v1.1) and a migration hook in `storage.py`.

7. **Entity creation is automatic** — when commands are captured, `EntityFactory` creates HA entities (`remote`, `media_player`, `climate`, `fan`) based on `DeviceType`. Entity features light up as commands are mapped.

8. **WebSocket API uses `hair/` prefix** for all admin panel communication. Capture sessions stream events back to the frontend via `connection.send_event()`.

9. **Frontend bundle is built with rollup + lit** — single JS file at `frontend/dist/ha-panel-ir-devices.js` served via `StaticPathConfig` registered in `__init__.py`.

10. **Climate entities are preset-based** by design (not full slider control) — IR is one-directional, so we offer captured presets per HVAC mode rather than pretending to have full state control.

---

## Critical Gaps (Your First Priorities)

### 🔴 P0 — Blockers for any community release

These need to be addressed before HAIR can ship to HACS or be installed by anyone:

1. **No `README.md` at repo root.** Users installing via HACS see this as the integration's storefront. Must include: what HAIR does, install instructions, screenshots/GIFs of the capture flow, link to docs, MIT license badge.

2. **No `LICENSE` file.** Pick MIT (mentioned in the brand guide as the planned license) and add it. HACS requires it.

3. **No `hacs.json`.** HACS requires this manifest to list the repo. Minimal version:
 ```json
 {
 "name": "HAIR - IR Device Manager",
 "render_readme": true,
 "homeassistant": "2026.4.0",
 "content_in_root": false
 }
 ```

4. **No CI pipeline.** Set up GitHub Actions for: lint (ruff), type check (mypy), Python tests (pytest), frontend build verification (rollup), and HACS validation action.

5. **No `requirements_test.txt` or `pyproject.toml`.** Tests reference `pytest_homeassistant_custom_component` fixtures but there's no declared test dependency setup. Add a proper Python project config.

6. **Integration has never been loaded into HA.** No one has confirmed this code actually works in a running HA instance. **Step 1 of testing: install it in a HA dev environment and watch it boot.**

### 🟠 P1 — Test coverage gaps

Test files exist but coverage is shallow. What's missing:

| File | Tested? | Notes |
|---|---|---|
| `models.py` | ✅ partial | Has tests, but check edge cases: invalid enums, missing fields, dict roundtrip |
| `storage.py` | ✅ partial | Tests exist; **needs migration test** (v1.0→v1.1) and reconciliation test |
| `capture.py` | ✅ partial | MockCaptureProvider tested. **ESPHome and Broadlink providers untested.** |
| `device_manager.py` | ✅ partial | CRUD tested; entity lifecycle and auto-mapping likely thin |
| `entity_factory.py` | ⚠️ minimal | Only 47 lines of test for 107 lines of code |
| `command_templates.py` | ⚠️ minimal | 32 lines of test, mostly smoke |
| `__init__.py` | ❌ none | Setup/teardown lifecycle untested |
| `config_flow.py` | ❌ none | The whole config flow is untested |
| `websocket_api.py` | ❌ none | 518 lines of WS handlers, zero tests |
| `capture_orchestrator.py` | ❌ none | Session locking and event streaming untested |
| `remote.py`, `media_player.py`, `climate.py`, `fan.py` | ❌ none | Entity platforms untested |
| `diagnostics.py` | ❌ none | Untested |
| Frontend (TypeScript) | ❌ none | No frontend test suite exists at all |

**Recommended order for adding tests:**
1. Config flow (most user-visible, easy to test)
2. WebSocket API handlers (largest untested surface)
3. Entity platforms (4 of them, similar patterns)
4. Capture orchestrator (concurrency edge cases matter)
5. End-to-end integration test (load into HA, capture a fake signal, verify entity)

### 🟡 P2 — Polish before ship

1. **No top-level `requirements.txt`.** Python deps are HA-managed but there should still be a constraints file for tests.

2. **`tests/__init__.py` is 1 line.** Probably empty — fine but verify.

3. **Frontend `dist/` is committed but no build verification in CI.** Add a check that `frontend/dist/ha-panel-ir-devices.js` matches what `npm run build` would produce.

4. **No CHANGELOG.md.** Should track v0.1.0 (initial), and any subsequent fixes.

5. **No issue/PR templates.** Add `.github/ISSUE_TEMPLATE/` for bug reports and feature requests.

6. **Strings.json may have untranslated keys.** Verify `translations/en.json` mirrors `strings.json` 1:1.

7. **`diagnostics.py` is only 35 lines** — verify it actually returns useful redacted data per the architecture doc spec.

---

## How to Test This Locally

You'll need:

1. **A Home Assistant dev environment.** Easiest path: HA Dev Container in VSCode, or `docker run` with the official HA container, mounting the `custom_components/hair` folder into `/config/custom_components/hair`.
2. **HA version 2026.4 or newer** (for the native infrared platform).
3. **Optional but ideal:** ESPHome device with an IR receiver configured, OR a Broadlink RM device. Without one of these, the capture flow can only be tested with `MockCaptureProvider`.

### First-boot smoke test

```bash
# In the HA dev container or instance:
# 1. Mount the custom_components/hair directory into /config/custom_components/hair
# 2. Start HA
# 3. Watch logs for: "Setting up hair" and "Successfully set up entry"
# 4. Settings > Devices & Services > Add Integration > search "HAIR"
# 5. Verify the config flow loads, detects (or doesn't detect) IR hardware
# 6. Verify the "IR Devices" sidebar item appears
# 7. Click into the panel, verify it loads (the bundled JS should load from /hair_panel/...)
```

If any of those steps fail, that's bug #1.

### Running the existing tests

There's no `pyproject.toml` or `requirements_test.txt` yet, so this is what to add:

```bash
# From the repo root:
pip install pytest pytest-homeassistant-custom-component pytest-asyncio
cd custom_components/hair
pytest tests/ -v
```

If they don't pass on first run, that's bug #2 (the tests themselves may have drift from the implementation).

### Frontend build verification

```bash
cd custom_components/hair/frontend
npm install
npm run build
# Verify dist/ha-panel-ir-devices.js was regenerated and is roughly 59KB
```

---

## Known Risks & Gotchas (Things to Watch For)

These are things either Code or the architecture flagged as risky during planning. Test these specifically:

1. **Integration registration of WebSocket commands can double-register.** `__init__.py` should guard with the `_panel_registered` flag pattern, but verify it survives a config-entry reload.

2. **Panel removal on unload assumes "last entry."** If for some reason multiple HAIR entries existed, panel removal logic might be wrong. Architecturally HAIR should only ever have one entry — `config_flow.py` enforces `single_instance_allowed` — but verify the unload path.

3. **Storage backup/restore reconciliation.** If a user backs up HA, restores, and HAIR storage is out of sync with the device/entity registries, what happens? The architecture doc called for an `async_reconcile` method. Verify it exists or add it.

4. **Capture session watchdog.** The architecture doc called for a `MAX_SESSION_DURATION` watchdog to clean up stale sessions if the WebSocket drops. Check `capture_orchestrator.py` (221 lines) — does it have one?

5. **ESPHome native API event subscription.** `ESPHomeCaptureProvider.async_start_capture` subscribes to ESPHome events. Verify it gracefully handles the ESPHome device being offline mid-capture.

6. **Broadlink learning mode polling has timing sensitivities.** The provider polls `device.check_data()` until a signal arrives or it times out. Verify it doesn't hammer the device or hold the event loop.

7. **Entity auto-mapping happens in `device_manager.async_add_command`.** Verify command name normalization is consistent (case-insensitive? trim whitespace? handle Unicode?).

8. **Climate entity preset behavior.** It's preset-based by design. Verify it doesn't pretend to support a temperature slider that just rounds — the user should see honest preset selection.

9. **Frontend assumes specific WebSocket event shapes.** If `websocket_api.py` and the TS `api.ts` ever diverge on event payload structure, the panel breaks silently. Add a contract test or schema validation.

10. **The 59KB bundled JS is committed to the repo.** Make sure your changes to TS source always rebuild and recommit the bundle — or better, add a CI check that fails if dist/ is stale.

---

## Documentation You Should Read First

Don't write new code or tests until you've read these (all under `docs/internal/`):

| Doc | Why |
|---|---|
| `architecture/code-architecture.md` | The blueprint Code worked from. Compare reality to spec. |
| `architecture/self-review.md` | Catches Code-vs-spec gaps and known issues. |
| `plans/integration-plan-v2.md` | The locked product plan. UX expectations live here. |
| `reviews/trio-review-v1.md` and `trio-review-v2-final.md` | Why decisions were made. Check before second-guessing them. |
| `branding/brand-guide.md` | If you touch UI strings, voice rules apply. |
| `research/01-ha-ir-platform.md` | Understand the HA 2026.4 IR platform Code is integrating with. |

---

## Brand & Voice Notes (For UI Work)

If you find yourself writing user-facing text:

- **Voice:** Old-school barbershop. Brief, confident, slightly mischievous. See `branding/brand-guide.md` Section 3.
- **Tagline:** "Style Your HAIR." Supporting line: "Walk-ins welcome."
- **Pun budget:** Marketing only. Error messages, setup flow, docs, and diagnostics get plain clear language. Per the brand guide Section 4.
- **Mascot:** Hairy Hank — locked v8 reference at `docs/internal/branding/assets/hank-master-v8-final.png`. Don't redesign him.

---

## Working Agreements With This Cowork

A few suggestions for how to work efficiently:

1. **Don't add features.** The architecture is locked. If you find a gap, document it as an issue for a future feature Cowork — don't scope-creep this session.

2. **Tests before fixes.** When you find a bug, write a failing test first, then fix it. We need regression protection.

3. **Use `MockCaptureProvider` aggressively.** It's already in the codebase for exactly this — testing capture flows without real hardware.

4. **Document deviations.** If you discover that Code's implementation differs from the architecture doc, note it in a new file: `docs/internal/architecture/code-vs-spec-deltas.md`. Don't silently update the architecture doc to match — we want to see drift.

5. **Bug log.** Keep a running list at `docs/internal/bugs.md` as you find them. Even tiny ones. The pattern of bugs tells you what part of the codebase is shakiest.

6. **Talk to me before:** changing the brand, breaking the storage schema, removing a documented feature, or restructuring the architecture. Otherwise drive forward.

---

## First Five Tasks (Suggested)

When you start, here's an opening punch list:

1. **Boot HAIR in a real HA instance.** Confirm it loads. Take notes on every error in the logs. (~30 min if smooth, hours if rough)
2. **Set up the test infrastructure.** Add `pyproject.toml` with `[project.optional-dependencies] test = [...]`, get the existing tests running. (~1 hour)
3. **Write the missing config_flow tests.** It's the user's first interaction — should be solid. (~2 hours)
4. **Write the missing WebSocket API tests.** Largest untested surface. (~half day)
5. **Add CI.** GitHub Actions running lint + tests + frontend build on every PR. (~1 hour once tests pass)

After those five, the codebase is in a defensible state and you can start fixing real bugs with confidence.

---

## Contact / Context Continuity

If you need context that isn't in this doc or the linked materials:

- **Owner / decision-maker:** David Bailey (david.a.bailey@gmail.com)
- **Repo location:** `/Users/DBAILEY/Desktop/GitHub-Desktop/HAIR/`
- **Predecessor sessions:**
 - Planning Cowork (produced all of `docs/internal/`)
 - Code Cowork (produced all of `custom_components/hair/`)
 - Brand iteration sessions (produced `docs/internal/branding/` including the locked Hairy Hank mascot)

If you hit something genuinely ambiguous, default to: **read the architecture doc, then read the trio reviews, then ask David.**

---

## Quick-Reference Map

| If you need to... | Look at... |
|---|---|
| Understand what HAIR does | `docs/internal/scope-ha-ir-admin.md` |
| Understand why it works the way it does | `docs/internal/plans/integration-plan-v2.md` |
| Understand the code's intended structure | `docs/internal/architecture/code-architecture.md` |
| See known issues from architecture review | `docs/internal/architecture/self-review.md` |
| Understand the brand voice / mascot | `docs/internal/branding/brand-guide.md` |
| Find what Code actually built | `custom_components/hair/` |
| Find what's tested | `custom_components/hair/tests/` |
| Find what's NOT tested | This doc, the "Critical Gaps" section above |
| Run the integration | A Home Assistant dev container with `custom_components/hair` mounted |
| Build the frontend | `cd custom_components/hair/frontend && npm install && npm run build` |

---

*Walk-ins welcome.*
