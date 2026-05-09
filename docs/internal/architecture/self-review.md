# Code Architecture Self-Review

**Date:** 2026-05-08
**Reviewer:** David Bailey
**Document Reviewed:** `architecture/code-architecture.md`

---

## Methodology

Evaluated the code architecture against:
1. HA Core integration best practices (2026 developer docs)
2. Patterns from production integrations (Z-Wave JS, ZHA, ESPHome)
3. HACS quality guidelines
4. Trio Review Board requirements

---

## Issues Found & Resolutions

### Issue 1: WebSocket Command Registration — Duplicate Registration Risk
**Problem:** `async_register_websocket_commands` is called in `async_setup_entry`. If a user adds a second config entry (unlikely for HAIR, but possible), WebSocket commands would be registered twice, causing errors.

**Resolution:** Guard with a registration check:
```python
if DOMAIN not in hass.data.get("_ws_registered", set()):
    async_register_websocket_commands(hass)
    hass.data.setdefault("_ws_registered", set()).add(DOMAIN)
```

**Status:** Applied to architecture doc. Changed `__init__.py` to register WS commands only once, using an `_ws_registered` flag in `hass.data`.

---

### Issue 2: Panel Module URL — HACS vs. Dev Path
**Problem:** The `module_url` in panel registration is hardcoded to `/hacsfiles/hair/ha-panel-ir-devices.js`. This assumes HACS installation. During development (manual install), the path would be different.

**Resolution:** Dynamic path resolution:
```python
module_url = f"/hacsfiles/{DOMAIN}/ha-panel-ir-devices.js"
# Fallback for manual installation:
# module_url = f"/local/hair/ha-panel-ir-devices.js"
```
Add documentation noting both paths. For HACS, files in `custom_components/hair/frontend/dist/` are automatically served.

**Status:** Added note to architecture. HACS serves files from the integration directory automatically — the `module_url` should use the HACS path by default with documentation for manual installs.

---

### Issue 3: Entity Unique ID Collision
**Problem:** Unique IDs follow `hair_{device.id}_{platform}`. If a user somehow creates two HAIR devices with the same UUID (shouldn't happen, but defensive coding), entities would collide.

**Resolution:** UUID4 generation is sufficient — collision probability is negligible. No change needed. The existing approach is correct.

**Status:** No change. UUIDs are safe.

---

### Issue 4: Missing `async_remove_config_entry_device` Hook
**Problem:** HA 2024.7+ supports device removal via the UI. If a user deletes a HAIR device from the HA device registry, the integration should clean up the associated IR device data. The architecture doc doesn't define this hook.

**Resolution:** Add `async_remove_config_entry_device` to `__init__.py`:
```python
async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Remove a HAIR device when deleted from device registry."""
    device_manager = hass.data[DOMAIN][config_entry.entry_id]["device_manager"]
    # Extract HAIR device ID from device identifiers
    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN:
            await device_manager.async_remove_device(identifier[1])
            return True
    return False
```

**Status:** Applied. Added function signature to `__init__.py` section.

---

### Issue 5: Climate Entity — Missing `_enable_turn_on_off_backwards_compatibility`
**Problem:** HA 2024.x deprecated the old turn_on/turn_off behavior for climate entities. The architecture doc correctly sets `_enable_turn_on_off_backwards_compatibility = False` but should also explicitly include `TURN_ON | TURN_OFF` in supported features.

**Resolution:** Already correct in the architecture. The climate entity's `supported_features` property includes:
```python
features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
```

**Status:** No change needed. Already correct.

---

### Issue 6: Storage — No Backup/Restore Consideration
**Problem:** If a user backs up and restores HA, the `.storage/hair_devices` file restores with the old data. But device registry entries and entity registry entries are also restored separately. If they get out of sync, orphaned entities or missing devices could result.

**Resolution:** Add a startup reconciliation step:
```python
async def async_reconcile(self, device_registry, entity_registry):
    """Ensure storage, device registry, and entity registry are in sync."""
    # Remove HAIR devices from storage if not in device registry
    # Remove orphaned entities
    # Re-register devices that are in storage but missing from registry
```

**Status:** Applied. Added `async_reconcile` method signature to `storage.py` section and a call in `async_setup_entry`.

---

### Issue 7: Capture Orchestrator — No Heartbeat/Stale Session Cleanup
**Problem:** If the WebSocket connection drops during a capture session, the lock could be held indefinitely. There's no mechanism to detect and clean up stale sessions.

**Resolution:** Add a session timeout:
```python
class CaptureOrchestrator:
    MAX_SESSION_DURATION = 120  # seconds

    async def _watchdog(self):
        """Clean up sessions that exceed MAX_SESSION_DURATION."""
        ...
```

**Status:** Applied. Added `MAX_SESSION_DURATION` constant and `_watchdog` coroutine to the orchestrator.

---

### Issue 8: Missing `diagnostics.py` Detail
**Problem:** The architecture doc lists `diagnostics.py` but doesn't define what data it exposes. HA has specific patterns for diagnostics.

**Resolution:** Define diagnostics output:
```python
async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    return {
        "devices": [
            {
                "id": device.id,
                "type": device.device_type,
                "command_count": len(device.commands),
                "emitter": device.emitter_entity_id,
                "capture_provider": device.capture_provider_type,
                # Redact: no raw IR codes (could be sensitive)
            }
            for device in store.get_all_devices()
        ],
        "capture_providers": [...],
        "storage_version": STORAGE_VERSION,
    }
```

**Status:** Applied. Added full diagnostics function signature.

---

### Issue 9: Command Templates — Missing Projector Type
**Problem:** `COMMAND_TEMPLATES` defines templates for TV, AC, Fan, Soundbar, but not Projector. Projectors have unique commands (e.g., keystone, freeze, blank).

**Resolution:** Add projector template:
```python
DeviceType.PROJECTOR: [
    CommandTemplate("Power On", CommandCategory.POWER, essential=True),
    CommandTemplate("Power Off", CommandCategory.POWER, essential=True),
    CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=False),
    CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=False),
    CommandTemplate("Mute", CommandCategory.VOLUME, essential=False),
    CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
    CommandTemplate("Menu", CommandCategory.NAVIGATION, essential=False),
    CommandTemplate("Up", CommandCategory.NAVIGATION, essential=False),
    CommandTemplate("Down", CommandCategory.NAVIGATION, essential=False),
    CommandTemplate("Left", CommandCategory.NAVIGATION, essential=False),
    CommandTemplate("Right", CommandCategory.NAVIGATION, essential=False),
    CommandTemplate("Select/OK", CommandCategory.NAVIGATION, essential=False),
],
```

**Status:** Applied. Added to `command_templates.py`.

---

### Issue 10: Frontend — No Dark Mode Consideration
**Problem:** The frontend components don't mention dark mode handling. HA supports both light and dark themes.

**Resolution:** By using HA's native web components (`ha-card`, `ha-dialog`, etc.) and CSS custom properties (`--primary-color`, `--card-background-color`, etc.), dark mode is handled automatically. No extra work needed.

**Status:** No change needed. HA components inherit theme automatically. Added a note to the frontend section confirming this.

---

## Changes Summary

| # | Issue | Severity | Action |
|---|---|---|---|
| 1 | WS duplicate registration | Medium | Added guard flag |
| 2 | Panel module URL | Low | Added documentation note |
| 3 | Unique ID collision | None | No change (UUIDs safe) |
| 4 | Missing device removal hook | High | Added `async_remove_config_entry_device` |
| 5 | Climate turn_on/off compat | None | Already correct |
| 6 | Storage backup/restore sync | Medium | Added `async_reconcile` |
| 7 | Stale capture session | Medium | Added watchdog timeout |
| 8 | Diagnostics detail missing | Low | Added diagnostics output |
| 9 | Missing projector template | Low | Added projector templates |
| 10 | Dark mode | None | No change (auto-handled) |

---

## Overall Assessment

The architecture is **solid and ready for implementation.** The 10 issues found are all addressable — 3 required no changes (already correct), 4 were medium-severity additions, and 3 were low-severity documentation improvements.

**Strengths:**
- Clean separation of concerns (storage, capture, device management, entities)
- `CaptureProvider` abstraction is well-designed and extensible
- WebSocket API is comprehensive and follows HA conventions
- Data model is future-proof (source field, database_id, migration strategy)
- Frontend design leverages HA components for native look/feel

**Areas to Watch During Implementation:**
- ESPHome native API integration for IR receiver will need careful testing with real hardware
- Broadlink learning mode polling has timing sensitivities
- Frontend build pipeline (rollup/esbuild) needs setup and CI integration
- Climate entity preset behavior should be user-tested early

**Confidence Level:** High. This architecture can support MVP through v2.0 without major restructuring.

---

*Self-review complete. Architecture is approved for implementation.*
