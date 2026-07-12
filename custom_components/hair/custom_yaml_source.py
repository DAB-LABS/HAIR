"""CustomYamlSource — user-authored YAML remotes, alongside the library.

This is the *second* code source behind the Add Remote picker (see
``library.py``). It reads a directory of YAML files, each describing ONE
remote with an EXPLICIT schema — brand, model, and a mapping of stable
function ids to codes — rather than guessing anything from button names.

Location
--------
Files live in ``<config>/hair_codes/`` — deliberately OUTSIDE
``custom_components/`` so a HACS update of the integration never deletes a
user's remotes. On first access the directory is seeded (best-effort) with
``README.md`` and ``_template.yaml.example`` copied from this package.

Schema (see ``hair_codes_examples/_template.yaml.example``)
-----------------------------------------------------------
    brand: LG                 # required, top-level picker group
    model: AKB74915324        # required, codebook under the brand
    functions:                # required, mapping of STABLE id -> code
      power:                  # id is "power", not "btn_0"
        name: Power           # optional label (defaults to "Power")
        pronto: "0000 006D …" # code as a ready Pronto string …
      temp_up:
        raw: [9000, -4500, …] # … OR raw signed timings + frequency
        frequency: 38000
        protocol: NEC         # optional decoded identity — kept end to end
        address: 0x04
        command: 0x08

Ids
---
Every id is prefixed ``custom:`` for the dispatcher, then ``file_stem`` (so
a code can be relocated cheaply) plus the stable function key:
``custom:<file_stem>`` for a codebook, ``custom:<file_stem>:<key>`` for a
function.

Robustness
----------
A missing directory or a malformed file degrades to an empty tree (or a
skipped file), never a crash. Parsed files are cached by modification time,
so a file is only re-read when it actually changes.
"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any, Iterator

from .const import DECODED_FINGERPRINT_FORMAT
from .ir_command import raw_to_pronto

_LOGGER = logging.getLogger(__name__)

#: Routing prefix used by the ``library.py`` dispatcher. See ``LibrarySource``.
PREFIX = "custom"
_PREFIX_STR = f"{PREFIX}:"

#: Directory (relative to the HA config dir) that holds user YAML remotes.
_CUSTOM_DIRNAME = "hair_codes"
#: Documentation shipped inside the integration, seeded into the config dir.
_EXAMPLES_DIR = Path(__file__).resolve().parent / "hair_codes_examples"
_DEFAULT_FREQUENCY = 38000

#: Parsed-file cache: ``str(path) -> (mtime, parsed_or_None)``. A file is
#: re-parsed only when its mtime changes (reviewer point 6).
_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}


def _config_dir() -> Path:
    """Locate the Home Assistant config dir from this file's location.

    A HACS/custom integration lives at
    ``<config>/custom_components/<component>/custom_yaml_source.py``. When
    that layout holds we return ``<config>``; otherwise (tests, odd layouts)
    we fall back to the component's own parent so the feature still works.
    """
    component_dir = Path(__file__).resolve().parent
    if component_dir.parent.name == "custom_components":
        return component_dir.parent.parent
    return component_dir.parent


def _custom_dir() -> Path:
    return _config_dir() / _CUSTOM_DIRNAME


def _strip(identifier: str) -> str:
    """Remove the ``custom:`` routing prefix if present."""
    return identifier[len(_PREFIX_STR):] if identifier.startswith(_PREFIX_STR) else identifier


def _humanize(name: str) -> str:
    """``power_on`` / ``TEMP-UP`` -> ``Power On`` / ``Temp Up``."""
    cleaned = re.sub(r"[_\-]+", " ", str(name)).strip()
    return cleaned.title() or str(name)


def _slugify(text: str) -> str:
    """Turn arbitrary text into a stable, id-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return slug or "unknown"


def _parse_int(value: Any) -> int | None:
    """Parse an int given as int or as a hex/decimal string (``0x04``, ``4``)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip(), 0)
        except ValueError:
            return None
    return None


def _parse_frequency(value: Any) -> int:
    """Parse a carrier frequency like ``38000``, ``38000Hz``, or ``38.0kHz``."""
    if isinstance(value, bool):
        return _DEFAULT_FREQUENCY
    if isinstance(value, (int, float)):
        return int(value) or _DEFAULT_FREQUENCY
    if isinstance(value, str):
        match = re.search(r"([\d.]+)\s*(k?)hz", value.strip(), re.IGNORECASE)
        if match:
            number = float(match.group(1))
            if match.group(2):
                number *= 1000
            return int(number) or _DEFAULT_FREQUENCY
        try:
            return int(float(value)) or _DEFAULT_FREQUENCY
        except ValueError:
            pass
    return _DEFAULT_FREQUENCY


def ensure_dir(seed: bool = True) -> Path:
    """Create ``<config>/hair_codes/`` if missing; seed docs on first run.

    Best-effort: any I/O error is swallowed (logged at debug). Returns the
    directory path either way. Call this from the integration setup so the
    user finds a ready-to-edit template. Safe to call repeatedly.
    """
    directory = _custom_dir()
    try:
        if directory.is_dir():
            return directory
        directory.mkdir(parents=True, exist_ok=True)
        if seed and _EXAMPLES_DIR.is_dir():
            for name in ("README.md", "_template.yaml.example"):
                src = _EXAMPLES_DIR / name
                if src.is_file():
                    shutil.copyfile(src, directory / name)
    except Exception:
        _LOGGER.debug("Could not create/seed %s", directory, exc_info=True)
    return directory


def _iter_files() -> Iterator[Path]:
    """Yield every ``.yaml``/``.yml`` file directly inside the custom dir."""
    directory = _custom_dir()
    if not directory.is_dir():
        return
    paths = [
        p
        for p in directory.iterdir()
        if p.is_file()
        and p.suffix.lower() in (".yaml", ".yml")
        and not p.name.endswith(".yaml.example")
    ]
    for path in sorted(paths, key=lambda p: p.name.lower()):
        yield path


def _read_yaml(path: Path) -> dict[str, Any] | None:
    """Parse and validate one YAML file into a normalized structure.

    ``import yaml`` lives here, inside the reader (reviewer point 10), not at
    module import time. Returns ``{brand, model, functions}`` where functions
    is an ordered ``{key: normalized_function}`` mapping, or None if the file
    is unreadable / not a mapping / missing required fields.
    """
    import yaml  # local import: only paid when a file is actually read

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except Exception:
        _LOGGER.warning("Skipping unreadable custom code file: %s", path, exc_info=True)
        return None
    if not isinstance(data, dict):
        _LOGGER.warning("Skipping malformed custom code file (not a mapping): %s", path)
        return None

    brand = data.get("brand")
    model = data.get("model")
    raw_functions = data.get("functions")
    if not isinstance(brand, str) or not brand.strip():
        _LOGGER.warning("Skipping %s: missing required 'brand' field", path)
        return None
    if not isinstance(model, str) or not model.strip():
        _LOGGER.warning("Skipping %s: missing required 'model' field", path)
        return None
    if not isinstance(raw_functions, dict) or not raw_functions:
        _LOGGER.warning("Skipping %s: missing/empty 'functions' mapping", path)
        return None

    functions: dict[str, dict[str, Any]] = {}
    for key, entry in raw_functions.items():
        normalized = _normalize_function(str(key), entry)
        if normalized is None:
            _LOGGER.warning("Skipping function %r in %s: no usable code", key, path)
            continue
        functions[str(key)] = normalized
    if not functions:
        return None
    return {"brand": brand.strip(), "model": model.strip(), "functions": functions}


def _normalize_function(key: str, entry: Any) -> dict[str, Any] | None:
    """Normalize one function entry; a bare string is treated as a Pronto code."""
    if isinstance(entry, str):
        entry = {"pronto": entry}
    if not isinstance(entry, dict):
        return None
    pronto = entry.get("pronto")
    raw = entry.get("raw")
    has_pronto = isinstance(pronto, str) and pronto.strip()
    has_raw = isinstance(raw, list) and raw
    if not has_pronto and not has_raw:
        return None
    return {
        "name": str(entry.get("name") or _humanize(key)),
        "pronto": pronto.strip() if has_pronto else None,
        "raw": list(raw) if has_raw else None,
        "frequency": _parse_frequency(entry.get("frequency")),
        "protocol": entry.get("protocol") if isinstance(entry.get("protocol"), str) else None,
        "address": _parse_int(entry.get("address")),
        "command": _parse_int(entry.get("command")),
    }


def _load_file(path: Path) -> dict[str, Any] | None:
    """Return the parsed file, using the mtime cache (reviewer point 6)."""
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _CACHE.pop(key, None)
        return None
    cached = _CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    parsed = _read_yaml(path)
    _CACHE[key] = (mtime, parsed)
    return parsed


def _find_file(file_stem: str) -> Path | None:
    """Locate the YAML file whose stem matches ``file_stem``."""
    for path in _iter_files():
        if path.stem == file_stem:
            return path
    return None


def _decoded_fields(func: dict[str, Any]) -> dict[str, Any]:
    """Keep decoded identity when the YAML supplies it (reviewer point 5)."""
    protocol = func.get("protocol")
    address = func.get("address")
    command = func.get("command")
    if protocol and isinstance(address, int) and isinstance(command, int):
        return {
            "decoded_protocol": protocol,
            "decoded_address": int(address),
            "decoded_command": int(command),
            "decoded_fingerprint": DECODED_FINGERPRINT_FORMAT.format(
                protocol=protocol, address=int(address), command=int(command)
            ),
        }
    return {
        "decoded_protocol": None,
        "decoded_address": None,
        "decoded_command": None,
        "decoded_fingerprint": None,
    }


def _materialize(func: dict[str, Any]) -> dict[str, Any] | None:
    """Turn a normalized function into a Clipper-ready entry, or None."""
    try:
        if func["pronto"]:
            code = func["pronto"]
        else:
            timings = [abs(int(t)) for t in func["raw"]]
            code = raw_to_pronto(timings, frequency=func["frequency"] or _DEFAULT_FREQUENCY)
    except Exception:
        _LOGGER.warning("Failed to materialize custom code %r", func.get("name"), exc_info=True)
        return None
    return {"name": func["name"], "code": code, **_decoded_fields(func)}


def _available() -> bool:
    """True only if at least one file yields at least one function."""
    for path in _iter_files():
        data = _load_file(path)
        if data and data["functions"]:
            return True
    return False


def _get_tree() -> list[dict[str, Any]]:
    """Return the brand -> codebook -> function tree for the picker.

    Brand and model come from the file's EXPLICIT fields (reviewer points
    2/3). One file is one codebook; files sharing a brand group together.
    """
    brands: dict[str, dict[str, Any]] = {}
    for path in _iter_files():
        data = _load_file(path)
        if data is None:
            continue
        brand_key = _slugify(data["brand"])
        brand = brands.setdefault(
            brand_key,
            {"brand": brand_key, "label": data["brand"], "codebooks": []},
        )
        functions = [
            {"id": f"{_PREFIX_STR}{path.stem}:{key}", "name": func["name"]}
            for key, func in data["functions"].items()
        ]
        brand["codebooks"].append(
            {
                "id": f"{_PREFIX_STR}{path.stem}",
                "label": data["model"],
                "functions": functions,
            }
        )
    result = sorted(brands.values(), key=lambda b: b["label"].lower())
    for brand in result:
        brand["codebooks"].sort(key=lambda c: c["label"].lower())
    return result


def _codebook_label(codebook_id: str) -> str | None:
    """Human label (the model) for a codebook id."""
    file_stem = _strip(codebook_id)
    path = _find_file(file_stem)
    if path is None:
        return None
    data = _load_file(path)
    return data["model"] if data else None


def _split_function_id(function_id: str) -> tuple[str, str] | None:
    """``custom:<file_stem>:<key>`` -> ``(file_stem, key)``."""
    try:
        file_stem, key = _strip(function_id).split(":", 1)
    except ValueError:
        return None
    return file_stem, key


def _materialize_function(function_id: str) -> dict[str, Any] | None:
    """Materialize a single function id into a Clipper entry, or None."""
    parsed = _split_function_id(function_id)
    if parsed is None:
        return None
    file_stem, key = parsed
    path = _find_file(file_stem)
    if path is None:
        return None
    data = _load_file(path)
    if data is None:
        return None
    func = data["functions"].get(key)
    return _materialize(func) if func is not None else None


def _materialize_codebook(
    codebook_id: str, function_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Materialize a whole codebook (or a subset of its functions)."""
    file_stem = _strip(codebook_id)
    path = _find_file(file_stem)
    if path is None:
        return []
    data = _load_file(path)
    if data is None:
        return []
    wanted: set[str] | None = None
    if function_ids:
        wanted = set()
        for fid in function_ids:
            parsed = _split_function_id(fid)
            if parsed is not None:
                wanted.add(parsed[1])
    entries: list[dict[str, Any]] = []
    for key, func in data["functions"].items():
        if wanted is not None and key not in wanted:
            continue
        entry = _materialize(func)
        if entry is not None:
            entries.append(entry)
    return entries


class CustomYamlSource:
    """Adapter exposing ``<config>/hair_codes/`` YAML files as a code source."""

    #: Routing prefix used by the ``library.py`` dispatcher.
    prefix = PREFIX

    def ensure_dir(self, seed: bool = True) -> Path:
        return ensure_dir(seed=seed)

    def available(self) -> bool:
        return _available()

    def get_tree(self) -> list[dict[str, Any]]:
        return _get_tree()

    def codebook_label(self, codebook_id: str) -> str | None:
        return _codebook_label(codebook_id)

    def materialize_function(self, function_id: str) -> dict[str, Any] | None:
        return _materialize_function(function_id)

    def materialize_codebook(
        self, codebook_id: str, function_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        return _materialize_codebook(codebook_id, function_ids)
