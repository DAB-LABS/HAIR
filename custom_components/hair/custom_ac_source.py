"""CustomAcSource -- user-authored, code-based AC protocols (opt-in).

Unlike ``code_library.py`` / a future ``custom_yaml_source.py``, this is NOT
a picker source that materializes fixed Pronto strings up front. An AC
protocol module encodes a *live* state (temperature/mode/fan/swing) into IR
timings on every send, so there is nothing fixed to pre-materialize. This
module's job is just: discover protocol files, and encode one ACState into
a Packet on demand.

Location
--------
    <config>/hair_codes/ac/<brand_slug>/code.py

Deliberately OUTSIDE custom_components/ (HACS-safe), and under its own
``ac/`` subfolder so it's visually distinct from the plain YAML button
remotes that may later live directly in ``hair_codes/``.

Import convention -- read this before writing a file
------------------------------------------------------
Each file is imported standalone (this module never mounts it inside the
real ``infrared_protocols`` package tree), so it MUST import the shared
types with an ABSOLUTE path:

    from infrared_protocols.core import ACState, FanSpeed, Mode, Packet, Swing

NOT a relative one (``from ..core import ...``) -- that will fail to
resolve here and the file will be skipped with a warning, not crash HAIR.

Contract
--------
A file must define a module-level ``PROTOCOL`` object exposing
``encode(state) -> Packet``. Everything else (constants, helper functions,
the ``Protocol`` class name) is up to the file, exactly like a contribution
to the upstream library.

Gating
------
This source is opt-in. Whether it is actually consulted is decided by the
caller (checked against the integration's options flag) -- this module
does not know about config entries and will happily discover files
whenever asked. Keep the "is this feature turned on" check at the call
site (currently: climate.py, before it will use an ``ac_protocol_id``).

Robustness
----------
A missing directory, an unreadable file, a file missing ``PROTOCOL``, or an
``encode()`` that raises all degrade to "not available" / ``None``, never a
crash. Parsed files are cached by (path, mtime), like ``custom_yaml_source``.
"""
from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

#: Routing prefix, consistent with the other code-library sources.
PREFIX = "customac"
_PREFIX_STR = f"{PREFIX}:"

_AC_DIRNAME = "ac"  # <config>/hair_codes/ac/<brand_slug>/code.py
_MODULE_FILENAME = "code.py"
#: Synthetic sys.modules prefix for loaded user files. Never collides with
#: any real package -- these files are NOT mounted inside infrared_protocols.
_MODULE_NS = "hair_custom_ac_source"

#: (path str) -> (mtime, PROTOCOL-or-None). Re-imported only when mtime changes.
_CACHE: dict[str, tuple[float, Any]] = {}

# Human-facing HA values -> the enum member NAMES on infrared_protocols.core.
_HVAC_TO_MODE_NAME = {
    "cool": "COOL",
    "heat": "HEAT",
    "dry": "DRY",
    "fan_only": "FAN",
    "auto": "AUTO",
}
_FAN_TO_SPEED_NAME = {
    "auto": "AUTO",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "quiet": "QUIET",
}
_SWING_TO_NAME = {
    "off": "OFF",
    "vertical": "VERTICAL",
    "horizontal": "HORIZONTAL",
    "both": "BOTH",
}


def _config_dir() -> Path:
    """Locate the Home Assistant config dir from this file's location.

    Mirrors the same trick used elsewhere in HAIR for hair_codes/-style
    directories: a custom integration lives at
    ``<config>/custom_components/hair/custom_ac_source.py``.
    """
    component_dir = Path(__file__).resolve().parent
    if component_dir.parent.name == "custom_components":
        return component_dir.parent.parent
    return component_dir.parent


def _ac_dir() -> Path:
    return _config_dir() / "hair_codes" / _AC_DIRNAME


def _strip(identifier: str) -> str:
    return identifier[len(_PREFIX_STR):] if identifier.startswith(_PREFIX_STR) else identifier


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return slug or "unknown"


def _iter_brand_dirs():
    """Yield each ``<ac_dir>/<brand_slug>/`` that has a ``code.py`` in it."""
    directory = _ac_dir()
    if not directory.is_dir():
        return
    for path in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if path.is_dir() and (path / _MODULE_FILENAME).is_file():
            yield path


def _load_module(brand_slug: str, path: Path) -> Any | None:
    """Import one ``code.py`` in isolation; return its ``PROTOCOL`` or None.

    Cached by (path, mtime) -- a file is only re-imported when it actually
    changes. The synthetic module name is removed from ``sys.modules``
    again immediately after exec so a reload of the file (new mtime) gets
    a genuinely fresh module object rather than a stale cached one, while
    still letting ``exec_module`` run with normal module semantics.
    """
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _CACHE.pop(key, None)
        return None
    cached = _CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    module_name = f"{_MODULE_NS}.{brand_slug}"
    protocol = None
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is not None and spec.loader is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            candidate = getattr(module, "PROTOCOL", None)
            if candidate is not None and callable(getattr(candidate, "encode", None)):
                protocol = candidate
            else:
                _LOGGER.warning(
                    "Skipping custom AC protocol %s: no usable "
                    "'PROTOCOL' with an encode() method",
                    path,
                )
        except Exception:
            _LOGGER.warning(
                "Skipping custom AC protocol %s: import failed. Did you use "
                "an absolute import ('from infrared_protocols.core import "
                "...') instead of a relative one?",
                path,
                exc_info=True,
            )
        finally:
            sys.modules.pop(module_name, None)
    _CACHE[key] = (mtime, protocol)
    return protocol


def available() -> bool:
    """True if at least one file in ``ac/`` yields a usable PROTOCOL."""
    for path in _iter_brand_dirs():
        if _load_module(path.name, path / _MODULE_FILENAME) is not None:
            return True
    return False


def list_protocols() -> list[dict[str, Any]]:
    """``[{id, brand, name}]`` for every loadable custom AC protocol.

    Used by the config flow to populate an "AC protocol" picker instead of
    the usual function-tree picker (there ARE no discrete functions here --
    everything is encoded live from the entity's current state).
    """
    out: list[dict[str, Any]] = []
    for path in _iter_brand_dirs():
        brand_slug = path.name
        protocol = _load_module(brand_slug, path / _MODULE_FILENAME)
        if protocol is None:
            continue
        out.append(
            {
                "id": f"{_PREFIX_STR}{brand_slug}",
                "brand": brand_slug,
                "name": getattr(protocol, "name", brand_slug),
            }
        )
    return out


def build_state(
    *,
    power: bool,
    hvac_mode: str,
    temperature_c: int,
    fan_mode: str | None = None,
    swing_mode: str | None = None,
):
    """Build a real ``infrared_protocols.core.ACState`` from HA-side values.

    Returns None if the library isn't importable, or if it's missing any
    of the four enums a protocol file needs -- the caller logs and skips
    the send rather than crashing the entity.
    """
    try:
        from infrared_protocols.core import ACState, FanSpeed, Mode, Swing
    except Exception:
        _LOGGER.warning(
            "infrared_protocols.core unavailable; cannot build ACState",
            exc_info=True,
        )
        return None

    mode_name = _HVAC_TO_MODE_NAME.get(hvac_mode.lower(), "AUTO")
    fan_name = _FAN_TO_SPEED_NAME.get((fan_mode or "auto").lower(), "AUTO")
    swing_name = _SWING_TO_NAME.get((swing_mode or "off").lower(), "OFF")
    try:
        return ACState(
            power=power,
            mode=getattr(Mode, mode_name),
            temperature=temperature_c,
            fan=getattr(FanSpeed, fan_name),
            swing=getattr(Swing, swing_name),
        )
    except Exception:
        _LOGGER.warning("Failed to construct ACState", exc_info=True)
        return None


def encode(protocol_id: str, state: Any):
    """Call the protocol's ``encode(state)``; None on any failure.

    ``state`` should be an ``ACState`` built by ``build_state`` above (or,
    for tests, any object shaped the same way).
    """
    brand_slug = _strip(protocol_id)
    path = _ac_dir() / brand_slug / _MODULE_FILENAME
    protocol = _load_module(brand_slug, path)
    if protocol is None:
        return None
    try:
        return protocol.encode(state)
    except Exception:
        _LOGGER.warning("encode() raised for protocol %s", protocol_id, exc_info=True)
        return None


class CustomAcSource:
    """Thin object wrapper, for symmetry with the other code sources."""

    prefix = PREFIX

    def available(self) -> bool:
        return available()

    def list_protocols(self) -> list[dict[str, Any]]:
        return list_protocols()

    def build_state(self, **kwargs: Any):
        return build_state(**kwargs)

    def encode(self, protocol_id: str, state: Any):
        return encode(protocol_id, state)
