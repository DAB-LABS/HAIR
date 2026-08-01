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

from .const import MAX_DITTO_COUNT, MAX_SEND_COUNT
from .pronto_validator import validate_pronto

WIG_FORMAT_NAME = "hair-wig"
WIG_FORMAT_MAJOR = 1
# hair-wig/2 (Cold Cuts, v0.8.8): v1 plus an optional ``climate``
# state-matrix block. A wig with no climate block still reads and
# writes as v1, so older installs keep reading everything they could
# read before; only matrix wigs are gated behind the version they
# actually need.
WIG_FORMAT_MAJOR_CLIMATE = 2
# hair-wig/3 (Highlights, the transmit recipe): the canonical form takes
# one complete break. ``ditto_count`` enters the signal hash,
# ``bypass_protocol`` is promoted from only-when-true to always
# explicit, and ``send_count`` leaves the hash entirely -- flat signals
# AND matrix cells -- because the fitting has never transmitted it.
#
# Unlike the /2 bump, this major is a pure CAPABILITY gate rather than a
# statement about the wig's kind: the parser has always decided
# matrix-ness from the presence of the ``climate`` block, never from the
# major, so both kinds now stamp /3. Both have to, because the break
# changes cell hashes as well as signal hashes.
#
# The point of the bump is the failure message. An older HAIR reading a
# /3 file would compute the old-style hash, see a mismatch, and report
# what looks like TAMPERING on a perfectly good file. Refusing on the
# version instead is the difference between "update HAIR to import it"
# and an accusation.
WIG_FORMAT_MAJOR_RECIPE = 3
WIG_FORMAT_V1 = f"{WIG_FORMAT_NAME}/{WIG_FORMAT_MAJOR}"
WIG_FORMAT_V2 = f"{WIG_FORMAT_NAME}/{WIG_FORMAT_MAJOR_CLIMATE}"
WIG_FORMAT_V3 = f"{WIG_FORMAT_NAME}/{WIG_FORMAT_MAJOR_RECIPE}"

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
    "min_temp", "max_temp", "precision", "unit", "modes", "fan_modes",
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


_KNOWN_SIGNAL = {
    "alias", "pronto", "send_count", "ditto_count", "bypass_protocol",
}

_OPTIONAL_TOP_STRINGS = ("brand", "model", "kind", "notes", "origin")


@dataclass
class WigSignal:
    """One signal in a wig: alias + raw Pronto, optional send count."""

    alias: str
    pronto: str
    # The author's suggested per-press transmission count. A RIDE-ALONG
    # from the recipe break onward: carried, clamped, adopt-seeded, and
    # deliberately OUT of the content hash. The fitting has never
    # transmitted this value -- the session's send-times control decides
    # what goes on the wire -- so the signature never attested it, and
    # pinning something no fitter proved was the wrong protection.
    #
    # The corollary is the point: five fitters proving the same codes at
    # 3, 4, 3, 5 and 4 sends are proving THE SAME WIG, and now hash
    # identically so their fittings accumulate on one file.
    send_count: int = 1
    # Encoder repeat frames appended to each transmitted frame. IN the
    # content hash, always explicit, because dittos change the waveform
    # and the fitting transmits them.
    #
    # Named ditto_count rather than repeat_count on purpose: internally
    # HAIR calls dittos ``repeat_count`` while humans say "repeats" for
    # send counts, and the portable format is the one place that
    # ambiguity can be killed. The export boundary maps
    # ``IRCommand.repeat_count`` -> ``ditto_count``.
    #
    # Dittos are device grammar, not environment: a strict receiver (the
    # NAD C320BEE of GH #14) rejects a lone NEC frame and needs the
    # key-held pattern before it commits to a press. Distance does not
    # change what a decoder chip demands.
    ditto_count: int = 0
    # Send these bytes verbatim: do not decode and re-encode them
    # (Highlights, GH #78). It asserts nothing about protocol identity,
    # only "this is the payload, do not improve it", so unlike a decoded
    # field it can never go stale against a better future decoder -- the
    # reason wigs carry no decoded fields does not apply to it.
    #
    # Set where a code's repeats are baked into the capture: a Symphony
    # repeat-train re-encodes to one clean frame and the device ignores
    # it. Maps to and from the device command's ``tx_force_raw``.
    #
    # IN the content hash, but only when true (canonical_signals_json),
    # because it changes what transmits.
    bypass_protocol: bool = False
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
    # The scale every temperature in this block is written in (owner
    # ruling 2026-07-29): "C" or "F", default "C" because the SmartIR
    # corpus is Celsius by convention. Machine keys (cell_key, temps)
    # stay file-native forever; displays convert dynamically and names
    # freeze at mint time (wig_climate.cell_display_name).
    unit: str = "C"
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
    if int(match.group(1)) > WIG_FORMAT_MAJOR_RECIPE:
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
            # Refused rather than coerced: a truthy string here would
            # silently change what the signal transmits AND what it
            # hashes to, so a wrong type has to be an error a writer can
            # see, not a value we guess at.
            bypass = raw.get("bypass_protocol", False)
            if not isinstance(bypass, bool):
                errors.append(
                    f"signals[{i}].bypass_protocol: must be true or false "
                    "when present"
                )
                bypass = False
            # Same posture as send_count and bypass: refused rather than
            # coerced. This one is hashed, so a guessed value would
            # change the signature of a file the writer thought they
            # understood.
            ditto_count = raw.get("ditto_count", 0)
            if (
                not isinstance(ditto_count, int)
                or isinstance(ditto_count, bool)
            ):
                errors.append(
                    f"signals[{i}].ditto_count: must be an integer when "
                    "present"
                )
                ditto_count = 0
            if len(errors) > signals_errors_before:
                continue
            signals.append(WigSignal(
                alias=alias.strip(),
                pronto=pronto.strip(),
                # Clamp on materialize per plan; parse stores the clamp
                # so every consumer sees one truth.
                send_count=max(1, min(send_count, MAX_SEND_COUNT)),
                ditto_count=max(0, min(ditto_count, MAX_DITTO_COUNT)),
                bypass_protocol=bypass,
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

    # The block's temperature scale (owner ruling 2026-07-29). Default
    # "C": the SmartIR corpus writes Celsius by convention, and every
    # existing hair-wig/2 file predates the key.
    unit = raw.get("unit", "C")
    if unit not in ("C", "F"):
        errors.append('climate.unit: must be "C" or "F" when present')
        unit = "C"

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
        unit=unit,
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
    # Both kinds stamp /3: the break changed cell hashes as well as
    # signal hashes, so a matrix wig has to refuse on an old install for
    # exactly the same reason a flat one does.
    fmt = WIG_FORMAT_V3
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
    """Serialize one signal.

    Both recipe fields are written ALWAYS from hair-wig/3 on. The
    only-when-true convention ``bypass_protocol`` shipped with lived for
    exactly one release and dies here, before any external verifier ever
    implemented it: the canonicalization spec WigFactory and any
    upstream checker must reproduce byte-for-byte now has zero
    conditional rules. ``send_count`` keeps its only-when-not-1
    shorthand because it is no longer hashed, so its presence in the
    file is a readability question rather than a correctness one.
    """
    out: dict = {"alias": sig.alias, "pronto": sig.pronto}
    if sig.send_count != 1:
        out["send_count"] = sig.send_count
    out["ditto_count"] = sig.ditto_count
    out["bypass_protocol"] = sig.bypass_protocol
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
    }
    # Emitted only when Fahrenheit: "C" is the documented default, so
    # a Celsius file stays byte-identical to its pre-unit self.
    if matrix.unit == "F":
        out["unit"] = matrix.unit
    out["modes"] = list(matrix.modes)
    out["fan_modes"] = list(matrix.fan_modes)
    if matrix.swing_modes:
        out["swing_modes"] = list(matrix.swing_modes)
    out["off"] = matrix.off
    if matrix.on is not None:
        out["on"] = matrix.on
    out["cells"] = [_cell_out(c) for c in matrix.cells]
    out.update(matrix.extra)
    return out


def canonical_signals_json(signals: list[WigSignal]) -> str:
    """The canonical form of a signals array, the fitting-hash target.

    Contract (docs/wig-format.md mirrors this, and WigFactory and any
    upstream verifier must reproduce it byte-for-byte): a JSON array of
    objects carrying EXACTLY four keys -- ``alias``, ``pronto``,
    ``ditto_count``, ``bypass_protocol`` -- every field, every signal,
    every time; keys sorted; separators compact; ``pronto`` in its
    normalized form (validator whitespace normalization, then lowercased
    hex); unknown per-signal keys excluded. Zero conditional rules.

    The ruling principle: the hash covers what the fitting proves. A
    fitting's signature certifies that this content drove the device
    when a named person pressed the buttons, so it must cover exactly
    the waveform that left the blaster and no more.

    - ``pronto``: the bytes. Transmitted as stored.
    - ``ditto_count``: repeat frames the encoder appends. Shapes the
      waveform, and the fitting transmits it.
    - ``bypass_protocol``: suppresses the re-encode. Shapes the
      waveform.
    - ``send_count``: ABSENT, deliberately. Whole-blob retransmission is
      delivery, not meaning. The fitting has never transmitted the row's
      value (the session control decides), so the signature never
      attested it, and it has been hashed-but-unproven since
      hair-wig/1.

    The honest cost of that exclusion: someone can edit a send count on
    a signed wig and the signature still verifies. The edit is loud,
    locally fixable and clamped on import, and the protection budget
    goes to the flips that make a device silently fail while looking
    certified -- bytes, dittos, bypass -- which all stay pinned.
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
            "ditto_count": sig.ditto_count,
            "bypass_protocol": sig.bypass_protocol,
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
    carrying exactly mode / fan / swing / temp / pronto (absent
    dimensions as null, pronto normalized lowercase), plus off, on, and
    the block's unit, keys sorted, separators compact. Two files whose
    matrices differ only in formatting hash identically; any change to a
    code or a state key changes the hash. The unit participates
    (2026-07-29) because the same numbers on a different scale are
    different states -- a 22C lattice and a 22F lattice must never share
    a fitting ledger.

    ``send_count`` LEFT the cell object in the recipe break, for the
    same reason it left the signal object: the checklist never
    transmitted it. Cells carry no ditto field at all -- dittos are an
    NEC-family frame construct and an AC state blob is one long frame
    (owner ruling), so there is nothing for the concept to mean here.
    """
    def _pronto(code: str) -> str:
        result = validate_pronto(code)
        return (result.normalized if result.valid else code).lower()

    canon = {
        "unit": matrix.unit,
        "off": _pronto(matrix.off),
        "on": _pronto(matrix.on) if matrix.on is not None else None,
        "cells": [
            {
                "mode": c.mode,
                "fan": c.fan,
                "swing": c.swing,
                "temp": _json_temp(c.temp) if c.temp is not None else None,
                "pronto": _pronto(c.pronto),
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
