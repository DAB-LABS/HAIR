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
WIG_FORMAT_V1 = f"{WIG_FORMAT_NAME}/{WIG_FORMAT_MAJOR}"
WIG_SUFFIX = ".wig.json"

# A wig is text; this is generous (plan section 4).
MAX_WIG_BYTES = 1_000_000

_FORMAT_RE = re.compile(rf"^{WIG_FORMAT_NAME}/(\d+)$")

# Top-level and per-signal keys the v1 schema knows. Anything else is
# tolerated and preserved (forward compatibility).
_KNOWN_TOP = {"format", "name", "brand", "model", "notes", "origin", "signals"}
_KNOWN_SIGNAL = {"alias", "pronto", "send_count"}

_OPTIONAL_TOP_STRINGS = ("brand", "model", "notes", "origin")


@dataclass
class WigSignal:
    """One signal in a wig: alias + raw Pronto, optional send count."""

    alias: str
    pronto: str
    send_count: int = 1
    extra: dict = field(default_factory=dict)


@dataclass
class Wig:
    """A parsed, validated wig."""

    name: str
    signals: list[WigSignal]
    brand: str | None = None
    model: str | None = None
    notes: str | None = None
    origin: str | None = None
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
    if int(match.group(1)) > WIG_FORMAT_MAJOR:
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

    raw_signals = data.get("signals")
    signals: list[WigSignal] = []
    if not isinstance(raw_signals, list) or not raw_signals:
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
            notes=data.get("notes"),
            origin=data.get("origin"),
            extra={k: v for k, v in data.items() if k not in _KNOWN_TOP},
        ),
        [],
    )


def serialize_wig(wig: Wig) -> str:
    """Serialize a wig to file text.

    Stable key order (schema keys first, preserved unknown keys after,
    in their original order), 4-space indent, trailing newline. This is
    the exporter's output shape and the shape edits re-save in.
    """
    out: dict = {"format": WIG_FORMAT_V1, "name": wig.name}
    for key, value in (
        ("brand", wig.brand),
        ("model", wig.model),
        ("notes", wig.notes),
        ("origin", wig.origin),
    ):
        if value is not None:
            out[key] = value
    out["signals"] = [_signal_out(s) for s in wig.signals]
    out.update(wig.extra)
    return json.dumps(out, indent=4, ensure_ascii=False) + "\n"


def _signal_out(sig: WigSignal) -> dict:
    out: dict = {"alias": sig.alias, "pronto": sig.pronto}
    if sig.send_count != 1:
        out["send_count"] = sig.send_count
    out.update(sig.extra)
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
