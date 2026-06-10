"""Root-level conftest: create HA API stubs for unit testing.

The HAIR integration targets HA 2026.4+. This sandbox has Python 3.10 and
no compatible HA version. We create lightweight stubs of every HA module
that HAIR imports so pure-logic unit tests can run.

Integration tests against a real HA instance run on the HA Dev VM (VM999).
"""
from __future__ import annotations

import datetime
import enum
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Python 3.10 fallback -- datetime.UTC was added in 3.11.
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc  # type: ignore[attr-defined]  # noqa: UP017

try:
    from enum import StrEnum
except ImportError:
    # Python 3.10 fallback -- inject into enum module so HAIR's const.py works.
    # Real StrEnum (3.11+) has str(member) == member.value. The default 3.10
    # (str, Enum) gives "ClassName.MEMBER". Override __str__ to match 3.11+.
    class StrEnum(str, enum.Enum):  # noqa: UP042  # type: ignore[no-redef]
        def __str__(self) -> str:
            return self.value

        @staticmethod
        def _generate_next_value_(name, start, count, last_values):
            return name.lower()

    enum.StrEnum = StrEnum  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helper to create stub module hierarchies
# ---------------------------------------------------------------------------

def _stub(dotted: str, attrs: dict | None = None) -> ModuleType:
    """Create a stub module and all its parent packages."""
    parts = dotted.split(".")
    for i in range(1, len(parts) + 1):
        name = ".".join(parts[:i])
        if name not in sys.modules:
            sys.modules[name] = ModuleType(name)
    mod = sys.modules[dotted]
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# homeassistant.core
# ---------------------------------------------------------------------------
_stub("homeassistant")
_stub("homeassistant.core", {
    "HomeAssistant": MagicMock,
    "callback": lambda fn: fn,
    "CALLBACK_TYPE": None,  # type alias, not used at runtime in tests
    "Event": MagicMock,
    "CoreState": MagicMock,
})

# ---------------------------------------------------------------------------
# homeassistant.const
# ---------------------------------------------------------------------------

class _Platform(StrEnum):
    REMOTE = "remote"
    MEDIA_PLAYER = "media_player"
    CLIMATE = "climate"
    FAN = "fan"
    LIGHT = "light"
    SWITCH = "switch"
    COVER = "cover"
    BUTTON = "button"
    EVENT = "event"

class _UnitOfTemperature:
    FAHRENHEIT = "°F"
    CELSIUS = "°C"

_stub("homeassistant.const", {
    "Platform": _Platform,
    "UnitOfTemperature": _UnitOfTemperature,
})

# ---------------------------------------------------------------------------
# homeassistant.config_entries
# ---------------------------------------------------------------------------

class _ConfigEntry:
    def __init__(self, **kw):
        self.entry_id = kw.get("entry_id", "test-entry")
        self.data = kw.get("data", {})
        self.options = kw.get("options", {})
        self.title = kw.get("title", "HAIR")

    def add_update_listener(self, listener):
        return lambda: None

    def async_on_unload(self, unsub):
        pass

class _ConfigFlowResult(dict):
    pass

class _ConfigFlow:
    domain = ""
    VERSION = 1
    def __init_subclass__(cls, domain=None, **kw):
        if domain:
            cls.domain = domain

class _OptionsFlow:
    pass

_stub("homeassistant.config_entries", {
    "ConfigEntry": _ConfigEntry,
    "ConfigFlow": _ConfigFlow,
    "OptionsFlow": _OptionsFlow,
    "ConfigFlowResult": _ConfigFlowResult,
})

# Also make it importable as `from homeassistant import config_entries`
sys.modules["homeassistant"].config_entries = sys.modules["homeassistant.config_entries"]

# ---------------------------------------------------------------------------
# homeassistant.components.*
# ---------------------------------------------------------------------------
_stub("homeassistant.components")
_stub("homeassistant.components.http", {
    "StaticPathConfig": type("StaticPathConfig", (), {"__init__": lambda *a, **kw: None}),
})
_stub("homeassistant.components.panel_custom", {
    "async_register_panel": MagicMock(),
})
_stub("homeassistant.components.frontend", {
    "async_remove_panel": MagicMock(),
})
_stub("homeassistant.components.infrared", {
    "async_get_emitters": MagicMock(return_value=[]),
})
_stub("homeassistant.components.websocket_api", {
    "require_admin": lambda fn: fn,
    "websocket_command": lambda schema: lambda fn: fn,
    "async_response": lambda fn: fn,
    "async_register_command": MagicMock(),
    "ActiveConnection": MagicMock,
})
_stub("homeassistant.components.diagnostics", {
    "async_redact_data": lambda data, keys: data,
})

# Entity base classes
class _RemoteEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

class _MediaPlayerEntityFeature:
    TURN_ON = 1
    TURN_OFF = 2
    VOLUME_STEP = 4
    VOLUME_MUTE = 8
    SELECT_SOURCE = 16
    PLAY = 16384
    PAUSE = 32768
    STOP = 65536
    def __init__(self, val=0): self._val = val
    def __or__(self, other):
        if isinstance(other, int):
            return _MediaPlayerEntityFeature(self._val | other)
        return _MediaPlayerEntityFeature(self._val | other._val)
    def __ior__(self, other): return self.__or__(other)
    def __int__(self): return self._val

class _MediaPlayerState(StrEnum):
    ON = "on"
    OFF = "off"
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"

class _MediaPlayerEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

_stub("homeassistant.components.remote", {"RemoteEntity": _RemoteEntity})
_stub("homeassistant.components.media_player", {
    "MediaPlayerEntity": _MediaPlayerEntity,
    "MediaPlayerEntityFeature": _MediaPlayerEntityFeature,
    "MediaPlayerState": _MediaPlayerState,
})

class _ClimateEntityFeature:
    TURN_ON = 1
    TURN_OFF = 2
    TARGET_TEMPERATURE = 4
    FAN_MODE = 8
    def __init__(self, val=0): self._val = val
    def __or__(self, other):
        if isinstance(other, int):
            return _ClimateEntityFeature(self._val | other)
        return _ClimateEntityFeature(self._val | other._val)
    def __ior__(self, other): return self.__or__(other)

class _HVACMode(StrEnum):
    OFF = "off"
    COOL = "cool"
    HEAT = "heat"
    FAN_ONLY = "fan_only"
    DRY = "dry"
    AUTO = "auto"

class _ClimateEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_temperature_unit = "°F"
    _enable_turn_on_off_backwards_compatibility = False
    def __init_subclass__(cls, **kw): pass

_stub("homeassistant.components.climate", {
    "ATTR_TEMPERATURE": "temperature",
    "ClimateEntity": _ClimateEntity,
    "ClimateEntityFeature": _ClimateEntityFeature,
    "HVACMode": _HVACMode,
})

class _FanEntityFeature:
    SET_SPEED = 1
    OSCILLATE = 2
    DIRECTION = 4
    PRESET_MODE = 8
    TURN_ON = 16
    TURN_OFF = 32
    def __init__(self, val=0): self._val = val
    def __or__(self, other):
        if isinstance(other, int):
            return _FanEntityFeature(self._val | other)
        return _FanEntityFeature(self._val | other._val)
    def __ior__(self, other): return self.__or__(other)

class _FanEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

_stub("homeassistant.components.fan", {
    "FanEntity": _FanEntity,
    "FanEntityFeature": _FanEntityFeature,
})

# --- Light ---

class _ColorMode(StrEnum):
    ONOFF = "onoff"
    BRIGHTNESS = "brightness"

class _LightEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

class _LightEntityFeature:
    pass  # HAIR doesn't use feature flags for light

_stub("homeassistant.components.light", {
    "LightEntity": _LightEntity,
    "LightEntityFeature": _LightEntityFeature,
    "ColorMode": _ColorMode,
})

# --- Switch ---

class _SwitchEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

_stub("homeassistant.components.switch", {
    "SwitchEntity": _SwitchEntity,
})

# --- Cover ---

class _CoverEntityFeature:
    OPEN = 1
    CLOSE = 2
    STOP = 8
    def __init__(self, val=0): self._val = val
    def __or__(self, other):
        if isinstance(other, int):
            return _CoverEntityFeature(self._val | other)
        return _CoverEntityFeature(self._val | other._val)
    def __ior__(self, other): return self.__or__(other)
    def __int__(self): return self._val

class _CoverDeviceClass(StrEnum):
    SHADE = "shade"

class _CoverEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

_stub("homeassistant.components.cover", {
    "CoverEntity": _CoverEntity,
    "CoverDeviceClass": _CoverDeviceClass,
    "CoverEntityFeature": _CoverEntityFeature,
})

# --- Button ---

class _ButtonEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass

_stub("homeassistant.components.button", {
    "ButtonEntity": _ButtonEntity,
})

# --- Event ---

class _EventEntity:
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_event_types: list[str] = []  # noqa: RUF012
    hass = None  # mirrors HA's Entity class attribute (None pre-registration)
    def __init_subclass__(cls, **kw): pass
    def _trigger_event(self, event_type, event_attributes=None): pass
    def async_write_ha_state(self): pass

_stub("homeassistant.components.event", {
    "EventEntity": _EventEntity,
})

# ---------------------------------------------------------------------------
# homeassistant.helpers.*
# ---------------------------------------------------------------------------
_stub("homeassistant.helpers")

_mock_registry = MagicMock()
_stub("homeassistant.helpers.device_registry", {
    "async_get": MagicMock(return_value=_mock_registry),
    "async_entries_for_config_entry": MagicMock(return_value=[]),
    "DeviceEntry": MagicMock,
})

_mock_entity_registry = MagicMock()
_stub("homeassistant.helpers.entity_registry", {
    "async_get": MagicMock(return_value=_mock_entity_registry),
    "async_entries_for_device": MagicMock(return_value=[]),
    "RegistryEntry": MagicMock,
})

_stub("homeassistant.helpers.entity_platform", {
    "AddEntitiesCallback": MagicMock,
})

_stub("homeassistant.helpers.dispatcher", {
    "async_dispatcher_send": MagicMock(),
    "async_dispatcher_connect": MagicMock(),
})


class _Store:
    """Minimal stub of homeassistant.helpers.storage.Store."""
    def __init__(self, hass, version, key, *, minor_version=1, atomic_writes=False):
        self._data = None
        self.version = version
        self.key = key

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data

_stub("homeassistant.helpers.storage", {"Store": _Store})

# ---------------------------------------------------------------------------
# voluptuous (used by websocket_api.py and config_flow.py)
# ---------------------------------------------------------------------------
try:
    import voluptuous  # noqa: F401
except ImportError:
    _vol = _stub("voluptuous", {
        "Any": lambda *a: a,
        "Required": lambda key, **kw: key,
        "Optional": lambda key, **kw: key,
        "Schema": lambda schema: schema,
        "All": lambda *a: a,
        "Range": lambda **kw: kw,
        "Length": lambda **kw: kw,
        "In": lambda vals: vals,
        "Coerce": lambda t: t,
    })
