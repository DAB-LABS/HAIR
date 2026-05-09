# Research: HA Integration Development Patterns

**Researcher:** David Bailey
**Date:** 2026-05-08
**Sources:** HA Developer Docs, Community Guides, Z-Wave/ZHA Source Code

---

## 1. Integration Architecture Overview

Home Assistant integrations follow a standardized architecture with these core components:

### Required Files
```
custom_components/ha_ir_admin/
├── __init__.py          # Integration setup and teardown
├── manifest.json        # Metadata, dependencies, requirements
├── config_flow.py       # UI-based configuration
├── const.py             # Constants
├── strings.json         # UI strings and translations
└── translations/
    └── en.json          # English translations
```

### Optional Components (relevant to HA IR Admin)
```
├── entity.py            # Base entity class
├── media_player.py      # Media player entities (TVs, soundbars)
├── climate.py           # Climate entities (ACs, mini-splits)
├── fan.py               # Fan entities
├── remote.py            # Remote entities
├── panel/               # Custom admin panel (frontend)
│   └── ha-ir-admin.js   # LitElement web component
├── websocket_api.py     # WebSocket command handlers
├── storage.py           # Persistent storage helpers
└── icons.json           # Custom entity icons
```

---

## 2. Config Flow Patterns

### Standard Flow
Config flows manage integration setup through the UI. Key patterns:

```python
class HAIRAdminConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for HA IR Admin."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Step 1: Select IR emitter
        # Step 2: Name the device
        # Step 3: Select device type (TV, AC, Fan, etc.)
        ...
```

### Unique IDs
- Must be a string, unique within the integration domain
- Used to prevent duplicate setups
- For HA IR Admin: combination of emitter entity_id + device name

### Options Flow
For modifying settings after initial setup:
```python
class HAIRAdminOptionsFlow(config_entries.OptionsFlow):
    """Handle options for HA IR Admin."""
    ...
```

---

## 3. Device Registry Integration

Devices are registered to associate entities with physical hardware:

```python
device_registry.async_get_or_create(
    config_entry_id=entry.entry_id,
    identifiers={(DOMAIN, unique_id)},
    name="Living Room TV",
    manufacturer="Samsung",
    model="UN55TU7000",
    via_device=(DOMAIN, emitter_device_id),
)
```

Key patterns from Z-Wave/ZHA:
- Use `via_device` to link IR devices to their emitter
- Store device metadata (manufacturer, model) for user reference
- Support device removal with cleanup of associated entities

---

## 4. Admin Panel Architecture

### How Z-Wave/ZHA Do It

Z-Wave and ZHA provide admin panels within HA Settings. The pattern:

1. **Register a panel** in `__init__.py`:
```python
async_register_panel(
    hass,
    frontend_url_path="ha-ir-admin",
    sidebar_title="IR Admin",
    sidebar_icon="mdi:remote",
    config={"entry_id": entry.entry_id},
    require_admin=True,
)
```

2. **Frontend component** (LitElement web component):
- Stored in `panel/` directory or served from `www/`
- Communicates with backend via WebSocket API
- Uses HA's design system (ha-card, ha-dialog, etc.)
- Built with Lit (LitElement) framework

3. **WebSocket API** for backend communication:
```python
@websocket_api.websocket_command({
    vol.Required("type"): "ha_ir_admin/devices",
})
async def ws_get_devices(hass, connection, msg):
    """Get all IR devices."""
    ...
```

### Z-Wave Panel Features (model for HA IR Admin)
- Device list with status indicators
- Device details page (entities, configuration)
- Network map visualization
- Add/remove device flows
- Firmware update management
- Logs and diagnostics

### Custom Panel Registration
```python
# In __init__.py
from homeassistant.components import panel_custom

await panel_custom.async_register_panel(
    hass,
    webcomponent_name="ha-panel-ir-admin",
    sidebar_title="IR Admin",
    sidebar_icon="mdi:remote",
    frontend_url_path="ir-admin",
    config={"entry_id": config_entry.entry_id},
    require_admin=True,
    update=True,
)
```

Alternatively, integrations in Settings are accessed via:
`Settings > Devices & Services > HA IR Admin > Configure`

---

## 5. Data Storage

### `.storage/` Pattern
HA integrations store persistent data in `.storage/`:

```python
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "ha_ir_admin"

store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
data = await store.async_load()
await store.async_save(data)
```

### Storage Schema Design
```json
{
    "version": 1,
    "data": {
        "devices": {
            "device_uuid_1": {
                "name": "Living Room TV",
                "type": "media_player",
                "manufacturer": "Samsung",
                "model": "UN55TU7000",
                "emitter_entity_id": "infrared.esphome_ir_blaster",
                "commands": {
                    "power": {"protocol": "samsung", "code": "0xE0E040BF"},
                    "volume_up": {"protocol": "samsung", "code": "0xE0E0E01F"},
                    ...
                }
            }
        }
    }
}
```

---

## 6. Entity Platform Patterns

### Media Player (for TVs, Soundbars)
```python
class IRMediaPlayer(MediaPlayerEntity):
    """IR-controlled media player."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | ...
    )
```

### Climate (for ACs, Mini-Splits)
```python
class IRClimate(ClimateEntity):
    """IR-controlled climate device."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ...
    )
```

---

## 7. Best Practices (2026)

1. **Use `_attr_` pattern** for entity attributes (not property methods)
2. **Async everywhere** — no blocking I/O in the event loop
3. **Config entries, not YAML** — all configuration through UI
4. **Unique IDs on all entities** — required for entity registry
5. **Device info on all entities** — links entities to devices
6. **Translation keys** — all UI strings in `strings.json`
7. **Quality scale** — target at least Silver quality rating
8. **Type hints** — full type annotations on all functions
9. **Tests** — pytest-based testing with `pytest-homeassistant-custom-component`

---

## 8. WebSocket API Design

### Command Registration
```python
@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "ha_ir_admin/capture_start",
    vol.Required("emitter_id"): str,
})
@websocket_api.async_response
async def ws_capture_start(hass, connection, msg):
    """Start IR command capture."""
    ...
    connection.send_result(msg["id"], {"status": "listening"})
```

### Real-time Updates (for capture feedback)
```python
# Send events during capture
connection.send_event(msg["id"], {
    "type": "ir_received",
    "protocol": "NEC",
    "code": "0x20DF10EF",
    "raw": [...],
})
```

---

## 9. Manifest Structure

```json
{
    "domain": "ha_ir_admin",
    "name": "HA IR Admin",
    "version": "1.0.0",
    "documentation": "https://github.com/DBAILEY/ha-ir-admin",
    "issue_tracker": "https://github.com/DBAILEY/ha-ir-admin/issues",
    "dependencies": ["infrared"],
    "codeowners": ["@DBAILEY"],
    "config_flow": true,
    "iot_class": "local_push",
    "integration_type": "device",
    "requirements": [],
    "quality_scale": "silver"
}
```

---

## Sources

- [Config Flow Docs](https://developers.home-assistant.io/docs/core/integration/config_flow/)
- [WebSocket API](https://developers.home-assistant.io/docs/api/websocket/)
- [Custom Panel Integration](https://www.home-assistant.io/integrations/panel_custom/)
- [Frontend Dev Sidebar Panel Guide](https://community.home-assistant.io/t/how-to-add-a-sidebar-panel-to-a-home-assistant-integration/981585)
- [HA Integration Blueprint (2026)](https://github.com/jpawlowski/hacs.integration_blueprint)
- [Writing An Integration For Home Assistant](https://retired.re-ynd.com/2026/writing-an-integration-for-home-assistant/)
