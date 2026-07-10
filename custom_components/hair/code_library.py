"""Introspect the ``custom_codes`` YAML directory into a pickable tree.

The "database" behind the Add Remote picker is a directory of YAML files
(``custom_codes/``) written in the ESPHome / Flipper-IRDB style, one file
per remote (or, as with IR-to-ESPHome exports, one file per AC model with
many buttons). Each file defines a list of ``button`` entries, each holding
a ``remote_transmitter.transmit_raw`` action with a carrier frequency and a
list of raw signed timings.

Grouping is derived from each button's ``name`` field when it follows the
``"Brand Model - FUNCTION"`` convention (e.g. produced by ir_to_esphome.py
style exporters): the brand becomes the picker's top-level bucket, the
model becomes the codebook, and the trailing function token becomes the
button label. Buttons whose name doesn't follow that convention fall back
to a flat ``Custom`` brand with the filename as the codebook, so no file is
ever dropped from the tree.

Everything is filesystem- and parsing-guarded: a missing directory or a
malformed YAML file degrades to an empty tree (or a skipped file), never a
crash. Discovery walks the ``custom_codes`` directory for ``.yaml``/``.yml``
files, so remotes dropped in by the user appear automatically without any
hardcoded filenames.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Iterator

import yaml

from .const import DECODED_FINGERPRINT_FORMAT
from .ir_command import raw_to_pronto

_LOGGER = logging.getLogger(__name__)

_CUSTOM_CODES_DIR = Path(__file__).resolve().parent / "custom_codes"
_FALLBACK_BRAND_KEY = "custom"
_FALLBACK_BRAND_LABEL = "Custom"
_DEFAULT_FREQUENCY = 38000


def library_available() -> bool:
    """Return True if the custom_codes directory exists."""
    try:
        return _CUSTOM_CODES_DIR.is_dir()
    except Exception:
        return False


def _humanize_member(name: str) -> str:
    """``power_on`` / ``POWER-ON`` -> ``Power On``."""
    cleaned = re.sub(r"[_\-]+", " ", name).strip()
    return cleaned.title() or name


def _humanize_codebook(stem: str) -> str:
    """``living_room_ac`` / ``Electrol_ESV09CRO_B2I`` -> ``Living Room Ac`` etc.

    Strips underscores/dashes and inserts spaces at camelCase and
    letter/digit boundaries, then title-cases the result.
    """
    name = re.sub(r"[_\-]+", " ", stem)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    name = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", name)
    return name.strip().title() or stem


def _slugify(text: str) -> str:
    """Turn arbitrary text into a stable, id-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "unknown"


def _parse_button_name(name: str) -> tuple[str, str, str] | None:
    """Parse ``"Brand Model - FUNCTION"`` into ``(brand, model, function)``.

    Returns None if the name doesn't follow the convention: there must be
    a `` - `` separator, and the part before it must itself contain a
    space (so a brand can be split off from the model). Names that don't
    match simply fall back to flat filename-based grouping.
    """
    if " - " not in name:
        return None
    prefix, _, function_part = name.rpartition(" - ")
    prefix = prefix.strip()
    function_part = function_part.strip()
    if not prefix or not function_part or " " not in prefix:
        return None
    brand, _, model = prefix.partition(" ")
    brand = brand.strip()
    model = model.strip()
    if not brand or not model:
        return None
    return brand, model, function_part


def _iter_yaml_files() -> Iterator[Path]:
    """Yield every ``.yaml``/``.yml`` file directly inside custom_codes/.

    Missing directory yields nothing rather than raising.
    """
    if not _CUSTOM_CODES_DIR.is_dir():
        return
    paths = [
        p
        for p in _CUSTOM_CODES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".yaml", ".yml")
    ]
    for path in sorted(paths, key=lambda p: p.name.lower()):
        yield path


def _load_yaml(path: Path) -> dict[str, Any] | None:
    """Safely load a YAML file, returning None (and logging) on any failure."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except Exception:
        _LOGGER.warning("Skipping unreadable custom code file: %s", path, exc_info=True)
        return None
    if not isinstance(data, dict):
        _LOGGER.warning("Skipping malformed custom code file (not a mapping): %s", path)
        return None
    return data


def _parse_frequency(value: Any) -> int:
    """Parse a carrier frequency like ``38000Hz``, ``38000``, or ``38.0kHz``."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"([\d.]+)\s*(k?)hz", value.strip(), re.IGNORECASE)
        if match:
            number = float(match.group(1))
            if match.group(2):
                number *= 1000
            return int(number)
        try:
            return int(float(value))
        except ValueError:
            pass
    return _DEFAULT_FREQUENCY


def _extract_raw_action(button: dict[str, Any]) -> tuple[list[Any], int] | None:
    """Pull ``(code, frequency)`` out of a button's ``on_press`` actions.

    Looks for a ``remote_transmitter.transmit_raw`` action anywhere in the
    button's ``on_press`` list. Returns None if the button doesn't hold one
    or is otherwise malformed. Unrelated keys (e.g. ``transmitter_id``) are
    ignored.
    """
    on_press = button.get("on_press")
    if not isinstance(on_press, list):
        return None
    for action in on_press:
        if not isinstance(action, dict):
            continue
        payload = action.get("remote_transmitter.transmit_raw")
        if not isinstance(payload, dict):
            continue
        code = payload.get("code")
        if not isinstance(code, list) or not code:
            continue
        frequency = _parse_frequency(payload.get("carrier_frequency"))
        return code, frequency
    return None


def _extract_buttons(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize a YAML file's ``button`` list into raw button dicts.

    Each entry: ``{id, name, code, frequency}``. Buttons missing a usable
    ``remote_transmitter.transmit_raw`` action are skipped. Buttons without
    an explicit ``id`` fall back to a positional id so they remain
    addressable.
    """
    raw_buttons = data.get("button")
    if not isinstance(raw_buttons, list):
        return []
    buttons: list[dict[str, Any]] = []
    for index, button in enumerate(raw_buttons):
        if not isinstance(button, dict):
            continue
        action = _extract_raw_action(button)
        if action is None:
            continue
        code, frequency = action
        button_id = str(button.get("id") or f"btn_{index}")
        name = str(button.get("name") or _humanize_member(button_id))
        buttons.append({"id": button_id, "name": name, "code": code, "frequency": frequency})
    return buttons


def _iter_grouped_buttons() -> Iterator[dict[str, Any]]:
    """Yield every button across every file, annotated with its picker grouping.

    Each yielded dict carries: ``function_id`` (``"{file_stem}:{button_id}"``,
    used to relocate the raw code later), ``code``, ``frequency``, plus the
    resolved ``brand_key``, ``brand_label``, ``codebook_id``,
    ``codebook_label`` and ``function_label`` for tree placement.

    Grouping comes from parsing the button's ``name`` as
    ``"Brand Model - FUNCTION"`` when possible; otherwise it falls back to
    a flat ``Custom`` brand keyed by the source filename.
    """
    for path in _iter_yaml_files():
        data = _load_yaml(path)
        if data is None:
            continue
        file_stem = path.stem
        for button in _extract_buttons(data):
            parsed = _parse_button_name(button["name"])
            if parsed is not None:
                brand, model, function_part = parsed
                brand_key = _slugify(brand)
                brand_label = brand
                codebook_label = _humanize_codebook(model)
                function_label = _humanize_member(function_part)
            else:
                brand_key = _FALLBACK_BRAND_KEY
                brand_label = _FALLBACK_BRAND_LABEL
                codebook_label = _humanize_codebook(file_stem)
                function_label = button["name"] or _humanize_member(button["id"])
            codebook_id = f"{brand_key}__{_slugify(codebook_label)}"
            yield {
                "function_id": f"{file_stem}:{button['id']}",
                "code": button["code"],
                "frequency": button["frequency"],
                "brand_key": brand_key,
                "brand_label": brand_label,
                "codebook_id": codebook_id,
                "codebook_label": codebook_label,
                "function_label": function_label,
            }


def _find_yaml_file(file_stem: str) -> Path | None:
    """Locate the YAML file whose stem matches ``file_stem``."""
    for path in _iter_yaml_files():
        if path.stem == file_stem:
            return path
    return None


def _decoded_fields() -> dict[str, Any]:
    """Custom codes carry no decoded protocol identity, only raw Pronto."""
    return {
        "decoded_protocol": None,
        "decoded_address": None,
        "decoded_command": None,
        "decoded_fingerprint": None,
    }


def _materialize_raw(name: str, code: list[Any], frequency: int) -> dict[str, Any] | None:
    """Turn raw timings + frequency into a Clipper-ready entry, or None on failure."""
    try:
        timings = [abs(int(t)) for t in code]
        pronto = raw_to_pronto(timings, frequency=int(frequency) or _DEFAULT_FREQUENCY)
    except Exception:
        _LOGGER.warning("Failed to materialize custom code button: %s", name, exc_info=True)
        return None
    return {"name": name, "code": pronto, **_decoded_fields()}


def get_tree() -> list[dict[str, Any]]:
    """Return the brand -> codebook -> function tree for the picker.

    Each brand: ``{brand, label, codebooks: [...]}``. Each codebook:
    ``{id, label, functions: [{id, name}]}``. Brands and codebooks are
    derived from each button's ``"Brand Model - FUNCTION"`` name when
    present, otherwise from a flat ``Custom`` bucket keyed by filename.
    """
    brands: dict[str, dict[str, Any]] = {}
    for entry in _iter_grouped_buttons():
        brand = brands.setdefault(
            entry["brand_key"],
            {"brand": entry["brand_key"], "label": entry["brand_label"], "codebooks": {}},
        )
        codebook = brand["codebooks"].setdefault(
            entry["codebook_id"],
            {"id": entry["codebook_id"], "label": entry["codebook_label"], "functions": []},
        )
        codebook["functions"].append({"id": entry["function_id"], "name": entry["function_label"]})

    result: list[dict[str, Any]] = []
    for brand in brands.values():
        codebooks = sorted(brand["codebooks"].values(), key=lambda c: c["label"].lower())
        result.append({"brand": brand["brand"], "label": brand["label"], "codebooks": codebooks})
    result.sort(key=lambda b: b["label"].lower())
    return result


def codebook_label(codebook_id: str) -> str | None:
    """Human label for a codebook id, e.g. for a default remote name."""
    for entry in _iter_grouped_buttons():
        if entry["codebook_id"] == codebook_id:
            return entry["codebook_label"]
    return None


def materialize_function(function_id: str) -> dict[str, Any] | None:
    """Materialize a single function id into a Clipper entry, or None."""
    try:
        file_stem, button_id = function_id.split(":", 1)
    except ValueError:
        return None
    path = _find_yaml_file(file_stem)
    if path is None:
        return None
    data = _load_yaml(path)
    if data is None:
        return None
    for button in _extract_buttons(data):
        if button["id"] == button_id:
            parsed = _parse_button_name(button["name"])
            display_name = _humanize_member(parsed[2]) if parsed else button["name"]
            return _materialize_raw(display_name, button["code"], button["frequency"])
    return None


def materialize_codebook(
    codebook_id: str, function_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Materialize a whole codebook (or a subset of its functions).

    Returns a list of Clipper entries (``{name, code, decoded_*}``). Entries
    that fail to materialize are skipped, so a single bad code never breaks
    the import. An unknown codebook returns an empty list. A codebook may
    span multiple YAML files if they share the same parsed brand/model.
    """
    wanted: set[str] | None = set(function_ids) if function_ids else None
    entries: list[dict[str, Any]] = []
    for entry in _iter_grouped_buttons():
        if entry["codebook_id"] != codebook_id:
            continue
        if wanted is not None and entry["function_id"] not in wanted:
            continue
        result = _materialize_raw(entry["function_label"], entry["code"], entry["frequency"])
        if result is not None:
            entries.append(result)
    return entries
