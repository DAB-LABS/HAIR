"""The wig format: ``hair-wig/1`` parsing, validation, serialization.

A wig is a portable IR code set: one JSON file, one remote, raw Pronto
as the payload. This module is the single authority every entry point
shares (drop zone, folder scan, adapters, export): a file either
validates fully or is rejected with a concrete field-level reason,
never half-imported (plan: wigs.md section 3).

Deliberate format rules, restated from the plan:

- Raw Pronto is the payload; NO decoded fields in the file. Import
  routes every signal through the same ``normalize()`` path paste and
  pluck use, so decode happens fresh on the importing install and a
  wig can never carry a stale identity.
- Unknown keys, top-level and per-signal, are IGNORED on read but
  PRESERVED through parse -> serialize, so a future additive key (the
  v0.7.x ``fittings`` list, say) survives an older install editing the
  wig's name.
- ``format`` gates parsing on its MAJOR version only: ``hair-wig/2``
  refuses politely with an update-HAIR message rather than guessing.
- Canonicalization of the ``signals`` array is part of the v1 contract
  (``canonical_signals_json`` / ``signals_content_hash``) even though
  nothing in core consumes it yet: future fittings bind to this exact
  form, and defining it later would fork hashes across installs.

Blocking I/O lives in wig_store, not here; this module is pure.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from .const import MAX_SEND_COUNT
from .pronto_validator import validate_pronto

WIG_FORMAT_NAME = "hair-wig"
WIG_FORMAT_MAJOR = 1
# hair-wig/2 (Cold Cuts, v0.8.8): v1 plus an optional ``climate``
# state-matrix block. A wig with no climate block still reads and
# writes as v1, so older installs keep reading everything they could
# read before; only matrix wigs are gated behind the version they
# actually need.
WIG_FORMAT_MAJOR_CLIMATE = 2
WIG_FORMAT_V1 = f"{WIG_FORMAT_NAME}/{WIG_FORMAT_MAJOR}"
WIG_FORMAT_V2 = f"{WIG_FORMAT_NAME}/{WIG_FORMAT_MAJOR_CLIMATE}"

WIG_SUFFIX = ".wig.json"

# A wig is text; this is generous (plan section 4). Raised from 1 MB
# for Cold Cuts: the SmartIR climate census (2026-07-20) measured a
# 286 KB MEDIAN matrix wig as Pronto text, 25 real devices over 1 MB,
# and a 7.9 MB worst case (Mitsubishi 1129, 2,689 cells).
MAX_WIG_BYTES = 16_000_000

_FORMAT_RE = re.compile(rf"^{WIG_FORMAT_NAME}/(\d+)$")

# Top-level and per-signal keys the schema knows. Anything else is
# tolerated and preserved (forward compatibility).
_KNOWN_TOP = {
    "format", "name", "brand", "model", "kind", "notes", "origin",
    "identifiers", "signals", "climate",
}

_KNOWN_CLIMATE = {
    "min_temp", "max_temp", "precision", "modes", "fan_modes",
    "swing_modes", "off", "on", "cells",
}
_KNOWN_CELL = {"mode", "fan", "swing", "temp", "pronto", "send_count"}

# Curated kind suggestions (v0.8.0). The field accepts ANY value (the
# dialogs offer these plus a custom entry); values are squashed-slug
# lowercase alphanumerics with no separators (owner ruling 2026-07-27:
# the repo naming convention <brand>-<kind>-<model>-infrared already
# carries the dashes, so the kind itself stays one word --
# "soundbar", "settopbox"). Kind labels the device for discovery once
# wigs are shared (the Wig Shop) and picks the factory's wrapper
# platform.
KIND_SUGGESTIONS = (
    "tv", "soundbar", "receiver", "settopbox", "projector",
    "fan", "light", "candles", "ac", "heater", "blinds",
)


def kind_slug(value: str) -> str:
    """Normalize a kind to its canonical form: lowercase, [a-z0-9] only.

    "Sound Bar", "sound-bar", and "soundbar" must collapse to one form
    because kind feeds the generated-integration naming convention.
    Returns "" when nothing survives.
    """
    return re.sub(r"[^a-z0-9]+", "", value.lower())


# Blessed identifier keys, documented in docs/wig-format.md. The map
# accepts ANY keys (future anchors arrive without a format bump), and
# each value is a non-empty string or a non-empty list of them --
# rebadged device families carry several UPCs and listings for the
# same hardware (owner ruling 2026-07-27). This set exists for docs
# and UI hints, not enforcement. Rationale (owner ruling 2026-07-27):
# brand/model die on off-brand hardware -- the Amazon candle, the
# no-name fan -- and those are exactly the devices only HAIR will
# ever cover. fcc_id is the strongest anchor WHEN present (grantee
# lookup, internal photos, manuals) but pure-IR remotes are
# FCC-exempt, so it cannot be required; upc is the one identifier
# nearly every retail box has; asin captures "sold on Amazon as X",
# often the only name the thing has; oem records an ESTABLISHED
# maker, kept separate from brand so detective work never overwrites
# what the box said.
IDENTIFIER_KEYS = ("fcc_id", "upc", "asin", "oem")


def _valid_identifier_value(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(v, str) and v.strip() for v in value)
    )


def identifier_values(
    identifiers: dict[str, str | list[str]] | None, key: str
) -> list[str]:
    """All values for one identifier key, single-or-list normalized.

    The consumer-side helper (search, dedup, the factory's attribution
    gate): callers never branch on the value shape.
    """
    if not identifiers or key not in identifiers:
        return []
    value = identifiers[key]
    return [value] if isinstance(value, str) else list(value)


_KNOWN_SIGNAL = {"alias", "pronto", "send_count"}

_OPTIONAL_TOP_STRINGS = ("brand", "model", "kind", "notes", "origin")


@dataclass
class WigSignal:
    """One signal in a wig: alias + raw Pronto, optional send count."""

    alias: str
    pronto: str
    send_count: int = 1
    extra: dict = field(default_factory=dict)


@dataclass
class ClimateCell:
    """One complete state in a climate matrix.

    Vocabulary strings (``mode``, ``fan``, ``swing``) are VERBATIM from
    the source: the census found 71 fan spellings including case
    variants, spaces, and vendor tokens, and they double as lookup keys
    AND entity attribute values, so normalizing any of them breaks the
    lookup (addendum section 3). ``fan``/``swing``/``temp`` are None
    when that mode subtree has no such dimension (depth varies per
    BRANCH, census finding).
    """

    mode: str
    pronto: str
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None
    send_count: int = 1
    extra: dict = field(default_factory=dict)


@dataclass
class ClimateMatrix:
    """The hair-wig/2 climate block: a stateful device's full lattice."""

    min_temp: float
    max_temp: float
    off: str
    cells: list[ClimateCell]
    precision: float = 1.0
    modes: list[str] = field(default_factory=list)
    fan_modes: list[str] = field(default_factory=list)
    swing_modes: list[str] = field(default_factory=list)
    on: str | None = None
    extra: dict = field(default_factory=dict)


def cell_key(cell: ClimateCell) -> str:
    """Canonical human-readable key for one cell: ``cool/auto/23``.

    Dimensions the cell does not have are omitted; a bare mode cell is
    just its mode. This string is what fittings record in confirmed /
    failed (dimension check, Cold Cuts rulings 2026-07-28), so it must
    be stable across installs: built only from the cell's own values.
    """
    parts = [cell.mode]
    if cell.fan is not None:
        parts.append(cell.fan)
    if cell.swing is not None:
        parts.append(cell.swing)
    if cell.temp is not None:
        parts.append(_temp_str(cell.temp))
    return "/".join(parts)


def _temp_str(temp: float) -> str:
    """``23.0`` -> ``"23"``; ``22.5`` stays ``"22.5"``."""
    return str(int(temp)) if float(temp).is_integer() else str(temp)


@dataclass
class Wig:
    """A parsed, validated wig."""

    name: str
    signals: list[WigSignal]
    brand: str | None = None
    model: str | None = None
    # What the device IS ("candles", "tv", "soundbar"): a squashed
    # lowercase slug, any value, curated suggestions in
    # KIND_SUGGESTIONS. Labels the device for Wig Shop discovery and
    # picks the factory's wrapper platform (v0.8.0).
    kind: str | None = None
    notes: str | None = None
    origin: str | None = None
    # Product identity anchors for hardware whose brand/model mean
    # nothing (v0.8.0): free map of string or list-of-string values,
    # blessed keys in IDENTIFIER_KEYS. None when absent.
    identifiers: dict[str, str | list[str]] | None = None
    # The state matrix (hair-wig/2, Cold Cuts). A wig may carry a
    # matrix, flat signals, or both (depth-0 SmartIR extras like
    # on_once / sleep import as ordinary buttons alongside the
    # matrix -- census second pass).
    climate: ClimateMatrix | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class WigParseResult:
    """Outcome of parsing: a wig, or the reasons there is not one."""

    wig: Wig | None
    errors: list[str]

    @property
    def ok(self) -> bool:
        return self.wig is not None and not self.errors


def parse_wig(text: str) -> WigParseResult:
    """Parse and fully validate wig JSON text.

    Returns every schema error found (field-path prefixed), not just
    the first, so a hand-written file gets one round of feedback. The
    single deliberate exception: an unsupported major version returns
    exactly one error, because reporting field errors against a schema
    we do not know would be noise.
    """
    if len(text.encode("utf-8", errors="ignore")) > MAX_WIG_BYTES:
        return WigParseResult(None, [
            f"file exceeds the {MAX_WIG_BYTES // 1_000_000} MB wig size cap"
        ])
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        return WigParseResult(None, [
            f"not valid JSON: {err.msg} (line {err.lineno}, column {err.colno})"
        ])
    if not isinstance(data, dict):
        return WigParseResult(None, ["top level must be a JSON object"])

    fmt = data.get("format")
    if not isinstance(fmt, str):
        return WigParseResult(None, [
            'missing required "format" (expected "hair-wig/1")'
        ])
    match = _FORMAT_RE.match(fmt)
    if match is None:
        return WigParseResult(None, [
            f'"format" is {fmt!r}, expected "hair-wig/1"'
        ])
    if int(match.group(1)) > WIG_FORMAT_MAJOR_CLIMATE:
        return WigParseResult(None, [
            f"this wig uses {fmt}, which this version of HAIR does not "
            "read yet; update HAIR to import it"
        ])

    errors: list[str] = []

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append('"name" is required and must be a non-empty string')
        name = ""

    for key in _OPTIONAL_TOP_STRINGS:
        if key in data and not isinstance(data[key], str):
            errors.append(f'"{key}" must be a string when present')

    identifiers: dict[str, str | list[str]] | None = None
    if "identifiers" in data:
        raw_ids = data["identifiers"]
        if not isinstance(raw_ids, dict):
            errors.append(
                '"identifiers" must be an object when present '
                '(e.g. {"fcc_id": "...", "upc": ["...", "..."]})'
            )
        else:
            ids_ok = True
            for id_key, id_value in raw_ids.items():
                if _valid_identifier_value(id_value):
                    continue
                errors.append(
                    f"identifiers.{id_key}: must be a non-empty string "
                    "or a non-empty list of non-empty strings"
                )
                ids_ok = False
            if ids_ok:
                identifiers = dict(raw_ids) or None

    climate: ClimateMatrix | None = None
    if "climate" in data:
        climate = _parse_climate(data["climate"], errors)

    raw_signals = data.get("signals")
    signals: list[WigSignal] = []
    if raw_signals is None and "climate" in data:
        # Matrix-only wigs are legal (hair-wig/2): the matrix IS the
        # payload; flat signals are the optional extras.
        raw_signals = []
    if not isinstance(raw_signals, list) or (
        not raw_signals and "climate" not in data
    ):
        errors.append('"signals" is required and must be a non-empty list')
    else:
        for i, raw in enumerate(raw_signals):
            signals_errors_before = len(errors)
            if not isinstance(raw, dict):
                errors.append(f"signals[{i}]: must be an object")
                continue
            alias = raw.get("alias")
            if not isinstance(alias, str) or not alias.strip():
                errors.append(
                    f"signals[{i}].alias: required, non-empty string"
                )
            pronto = raw.get("pronto")
            if not isinstance(pronto, str) or not pronto.strip():
                errors.append(
                    f"signals[{i}].pronto: required, non-empty string"
                )
            else:
                result = validate_pronto(pronto)
                if not result.valid:
                    reason = (
                        result.errors[0] if result.errors
                        else "not a valid Pronto code"
                    )
                    errors.append(f"signals[{i}].pronto: {reason}")
            send_count = raw.get("send_count", 1)
            if not isinstance(send_count, int) or isinstance(send_count, bool):
                errors.append(
                    f"signals[{i}].send_count: must be an integer when present"
                )
                send_count = 1
            if len(errors) > signals_errors_before:
                continue
            signals.append(WigSignal(
                alias=alias.strip(),
                pronto=pronto.strip(),
                # Clamp on materialize per plan; parse stores the clamp
                # so every consumer sees one truth.
                send_count=max(1, min(send_count, MAX_SEND_COUNT)),
                extra={k: v for k, v in raw.items() if k not in _KNOWN_SIGNAL},
            ))

    if errors:
        return WigParseResult(None, errors)

    return WigParseResult(
        Wig(
            name=name.strip(),
            signals=signals,
            brand=data.get("brand"),
            model=data.get("model"),
            kind=data.get("kind"),
            notes=data.get("notes"),
            origin=data.get("origin"),
            identifiers=identifiers,
            climate=climate,
            extra={k: v for k, v in data.items() if k not in _KNOWN_TOP},
        ),
        [],
    )


def _num(value: object) -> float | None:
    """A JSON number (int or float, never bool) as float, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _parse_climate(raw: object, errors: list[str]) -> ClimateMatrix | None:
    """Validate the climate block strictly-with-reasons.

    Appends field-path errors like the rest of parse_wig; returns None
    whenever anything is wrong (parse fails as a whole on any error).
    Vocabulary strings pass through verbatim -- validation checks
    types, never spelling.
    """
    if not isinstance(raw, dict):
        errors.append('"climate" must be an object when present')
        return None
    before = len(errors)

    min_temp = _num(raw.get("min_temp"))
    max_temp = _num(raw.get("max_temp"))
    if min_temp is None:
        errors.append("climate.min_temp: required, must be a number")
    if max_temp is None:
        errors.append("climate.max_temp: required, must be a number")
    if min_temp is not None and max_temp is not None and min_temp >= max_temp:
        errors.append("climate.min_temp must be below climate.max_temp")

    precision = _num(raw.get("precision", 1.0))
    if precision is None or precision <= 0:
        errors.append("climate.precision: must be a positive number")
        precision = 1.0

    lists: dict[str, list[str]] = {}
    for key in ("modes", "fan_modes", "swing_modes"):
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(v, str) and v.strip() for v in value
        ):
            errors.append(
                f"climate.{key}: must be a list of non-empty strings"
            )
            lists[key] = []
        else:
            lists[key] = list(value)

    off = raw.get("off")
    if not isinstance(off, str) or not validate_pronto(off).valid:
        errors.append("climate.off: required, must be a valid Pronto code")
        off = ""
    on = raw.get("on")
    if on is not None and (
        not isinstance(on, str) or not validate_pronto(on).valid
    ):
        errors.append("climate.on: must be a valid Pronto code when present")
        on = None

    raw_cells = raw.get("cells")
    cells: list[ClimateCell] = []
    if not isinstance(raw_cells, list) or not raw_cells:
        errors.append("climate.cells: required, must be a non-empty list")
    else:
        for i, raw_cell in enumerate(raw_cells):
            cell_errors_before = len(errors)
            if not isinstance(raw_cell, dict):
                errors.append(f"climate.cells[{i}]: must be an object")
                continue
            mode = raw_cell.get("mode")
            if not isinstance(mode, str) or not mode.strip():
                errors.append(
                    f"climate.cells[{i}].mode: required, non-empty string"
                )
            for dim in ("fan", "swing"):
                value = raw_cell.get(dim)
                if value is not None and (
                    not isinstance(value, str) or not value.strip()
                ):
                    errors.append(
                        f"climate.cells[{i}].{dim}: must be a non-empty "
                        "string when present"
                    )
            temp = raw_cell.get("temp")
            if temp is not None and _num(temp) is None:
                errors.append(
                    f"climate.cells[{i}].temp: must be a number when present"
                )
            pronto = raw_cell.get("pronto")
            if not isinstance(pronto, str) or not validate_pronto(pronto).valid:
                errors.append(
                    f"climate.cells[{i}].pronto: required, must be a valid "
                    "Pronto code"
                )
            send_count = raw_cell.get("send_count", 1)
            if not isinstance(send_count, int) or isinstance(send_count, bool):
                errors.append(
                    f"climate.cells[{i}].send_count: must be an integer "
                    "when present"
                )
                send_count = 1
            if len(errors) > cell_errors_before:
                continue
            cells.append(ClimateCell(
                mode=mode,
                fan=raw_cell.get("fan"),
                swing=raw_cell.get("swing"),
                temp=_num(temp) if temp is not None else None,
                pronto=pronto.strip(),
                send_count=max(1, min(send_count, MAX_SEND_COUNT)),
                extra={
                    k: v for k, v in raw_cell.items() if k not in _KNOWN_CELL
                },
            ))

    if len(errors) > before:
        return None
    return ClimateMatrix(
        min_temp=min_temp,  # type: ignore[arg-type]
        max_temp=max_temp,  # type: ignore[arg-type]
        precision=precision,
        modes=lists["modes"],
        fan_modes=lists["fan_modes"],
        swing_modes=lists["swing_modes"],
        off=off,
        on=on,
        cells=cells,
        extra={k: v for k, v in raw.items() if k not in _KNOWN_CLIMATE},
    )


def serialize_wig(wig: Wig) -> str:
    """Serialize a wig to file text.

    Stable key order (schema keys first, preserved unknown keys after,
    in their original order), 4-space indent, trailing newline. This is
    the exporter's output shape and the shape edits re-save in.
    """
    # The version follows the content: a wig with no climate block is
    # a v1 file every existing install reads; only matrix wigs demand
    # the version they need.
    fmt = WIG_FORMAT_V2 if wig.climate is not None else WIG_FORMAT_V1
    out: dict = {"format": fmt, "name": wig.name}
    for key, value in (
        ("brand", wig.brand),
        ("model", wig.model),
        ("kind", wig.kind),
        ("notes", wig.notes),
        ("origin", wig.origin),
    ):
        if value is not None:
            out[key] = value
    if wig.identifiers:
        out["identifiers"] = dict(wig.identifiers)
    out["signals"] = [_signal_out(s) for s in wig.signals]
    if wig.climate is not None:
        out["climate"] = _climate_out(wig.climate)
    out.update(wig.extra)
    return json.dumps(out, indent=4, ensure_ascii=False) + "\n"


def _signal_out(sig: WigSignal) -> dict:
    out: dict = {"alias": sig.alias, "pronto": sig.pronto}
    if sig.send_count != 1:
        out["send_count"] = sig.send_count
    out.update(sig.extra)
    return out


def _json_temp(temp: float) -> int | float:
    return int(temp) if float(temp).is_integer() else temp


def _cell_out(cell: ClimateCell) -> dict:
    out: dict = {"mode": cell.mode}
    if cell.fan is not None:
        out["fan"] = cell.fan
    if cell.swing is not None:
        out["swing"] = cell.swing
    if cell.temp is not None:
        out["temp"] = _json_temp(cell.temp)
    out["pronto"] = cell.pronto
    if cell.send_count != 1:
        out["send_count"] = cell.send_count
    out.update(cell.extra)
    return out


def _climate_out(matrix: ClimateMatrix) -> dict:
    out: dict = {
        "min_temp": _json_temp(matrix.min_temp),
        "max_temp": _json_temp(matrix.max_temp),
        "precision": _json_temp(matrix.precision),
        "modes": list(matrix.modes),
        "fan_modes": list(matrix.fan_modes),
    }
    if matrix.swing_modes:
        out["swing_modes"] = list(matrix.swing_modes)
    out["off"] = matrix.off
    if matrix.on is not None:
        out["on"] = matrix.on
    out["cells"] = [_cell_out(c) for c in matrix.cells]
    out.update(matrix.extra)
    return out


def canonical_signals_json(signals: list[WigSignal]) -> str:
    """The v1 canonical form of a signals array, the fitting-hash target.

    Contract (docs/wig-format.md mirrors this): a JSON array of objects
    carrying exactly alias, pronto, send_count; keys sorted; separators
    compact; ``pronto`` in its normalized form (validator whitespace
    normalization, then lowercased hex); ``send_count`` explicit even
    when 1; unknown per-signal keys excluded. Two wigs whose signals
    differ only in formatting hash identically everywhere, and any
    change to a code, alias, or count changes the hash.
    """
    canon = []
    for sig in signals:
        result = validate_pronto(sig.pronto)
        pronto = (
            result.normalized if result.valid else sig.pronto
        ).lower()
        canon.append({
            "alias": sig.alias,
            "pronto": pronto,
            "send_count": sig.send_count,
        })
    return json.dumps(
        canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def signals_content_hash(signals: list[WigSignal]) -> str:
    """``sha256:<hex>`` over the canonical signals form."""
    digest = hashlib.sha256(
        canonical_signals_json(signals).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def canonical_cells_json(matrix: ClimateMatrix) -> str:
    """The canonical form of a climate matrix, the matrix-fitting-hash
    target (hair-wig/2 contract, mirrored in docs/wig-format.md).

    Same posture as ``canonical_signals_json``: every cell as an object
    carrying exactly mode / fan / swing / temp / pronto / send_count
    (absent dimensions as null, send_count explicit, pronto normalized
    lowercase), plus off and on, keys sorted, separators compact. Two
    files whose matrices differ only in formatting hash identically;
    any change to a code or a state key changes the hash.
    """
    def _pronto(code: str) -> str:
        result = validate_pronto(code)
        return (result.normalized if result.valid else code).lower()

    canon = {
        "off": _pronto(matrix.off),
        "on": _pronto(matrix.on) if matrix.on is not None else None,
        "cells": [
            {
                "mode": c.mode,
                "fan": c.fan,
                "swing": c.swing,
                "temp": _json_temp(c.temp) if c.temp is not None else None,
                "pronto": _pronto(c.pronto),
                "send_count": c.send_count,
            }
            for c in matrix.cells
        ],
    }
    return json.dumps(
        canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def cells_content_hash(matrix: ClimateMatrix) -> str:
    """``sha256:<hex>`` over the canonical matrix form."""
    digest = hashlib.sha256(
        canonical_cells_json(matrix).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def wig_content_hash(wig: Wig) -> str:
    """The hash fittings bind to for THIS wig.

    Signal wigs keep the v1 signals hash byte-for-byte (existing
    fittings in the wild must stay valid); matrix wigs bind to the
    matrix, which is what the dimension check actually attests.
    """
    if wig.climate is not None:
        return cells_content_hash(wig.climate)
    return signals_content_hash(wig.signals)


def wig_filename(name: str, taken: set[str] | None = None) -> str:
    """Slugify ``name`` into a ``.wig.json`` filename, dodging ``taken``.

    "Foxtel IQ" -> "foxtel-iq.wig.json"; on collision, "-2", "-3", ...
    """
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")
    if not slug:
        slug = "wig"
    taken = taken or set()
    candidate = f"{slug}{WIG_SUFFIX}"
    n = 2
    while candidate in taken:
        candidate = f"{slug}-{n}{WIG_SUFFIX}"
        n += 1
    return candidate
