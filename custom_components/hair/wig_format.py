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
  (``canonical_signals_json`` / ``signals_content_hash``). It was
  defined as the target a flat wig's FITTING would bind to; v0.9.5
  moved that job to per-row digests (``row_digest``), because a
  whole-file hash cannot say which rows anybody actually proved. The
  canonical form stayed, and is still the definition of "the same
  codes": the duplicate-drop detector and the identity cache both read
  it. What it no longer does is appear in a file or bind a signature on
  a flat wig, which is hard rule 2.

Blocking I/O lives in wig_store, not here; this module is pure.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
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

# The supersession ancestry list is capped at BOTH ends -- parse trims
# to it, and the Save-as-new stamp composes then trims to it -- so the
# file on disk always matches what every reader sees (owner 2026-08-04).
# Newest-first means overflow drops the OLDEST ancestor, the one you can
# most afford to stop bouncing forward. Absurdly generous against real
# chain depth, short enough to scan past.
SUPERSEDES_MAX = 16

# Top-level and per-signal keys the schema knows. Anything else is
# tolerated and preserved (forward compatibility).
_KNOWN_TOP = {
    "format", "name", "brand", "model", "kind", "notes", "origin",
    "identifiers", "signals", "climate",
    # Fitting Room (v0.9.5): identity and provenance.
    "wig_id", "converted_from", "converted_from_sha256",
    # Second Fitting (v0.9.7): supersession ancestry, newest first.
    "supersedes",
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
    # STABLE IDENTITY (v0.9.5 Fitting Room). A UUID minted once, at
    # creation, and carried unchanged forever after: UPDATE keeps it,
    # save-as-new mints a fresh one. It is what claims bind their
    # bundle to and what the shop routes PRs by, and it is
    # deliberately in NO canonical form and NO digest -- renaming a
    # wig, retuning it or repairing a code must never change who it
    # is. Absent on a file from before this release; minted on import.
    wig_id: str | None = None
    # Where a converted seed came from: the filename for humans, and
    # a quiet digest of the source bytes for tooling that wants to
    # spot sibling conversions whose sources have drifted.
    converted_from: str | None = None
    converted_from_sha256: str | None = None
    # SUPERSESSION ANCESTRY (v0.9.7 Second Fitting), newest first: the
    # wig ids this one replaces -- its parent, then its parent's parent,
    # and so on. Stamped by Save as new (the source id prepended onto the
    # source's own ancestry) and read by the drop bar, which matches ANY
    # ancestor a local closet still holds and offers replace instead of
    # filing a twin. Metadata like every field around it: OUTSIDE every
    # canonical form and every digest, so lineage can never move a wig's
    # identity or disturb a claim. Capped at SUPERSEDES_MAX at both ends.
    supersedes: list[str] = field(default_factory=list)
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
            wig_id=_str_or_none(data.get("wig_id")),
            converted_from=_str_or_none(data.get("converted_from")),
            converted_from_sha256=_str_or_none(
                data.get("converted_from_sha256")
            ),
            supersedes=_parse_supersedes(data.get("supersedes")),
            extra={k: v for k, v in data.items() if k not in _KNOWN_TOP},
        ),
        [],
    )


def _str_or_none(value: object) -> str | None:
    """A non-empty string, else None. Anything else is not identity."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_supersedes(value: object) -> list[str]:
    """The supersession ancestry list: forgiving parse, newest first.

    Accepts a list of non-empty strings; a bare string becomes a
    one-element list, for hand-written files. Junk entries (non-string,
    empty, whitespace-only) are dropped, never errored -- lineage is
    optional metadata and a single bad entry must not fail an otherwise
    good wig. Trimmed to SUPERSEDES_MAX keeping the head, so overflow
    drops the OLDEST ancestor (the tail), matching the Save-as-new stamp
    so a file's on-disk list and every reader's view stay identical.
    """
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out[:SUPERSEDES_MAX]


def compose_supersedes(
    source_wig_id: str, source_supersedes: list[str] | None = None
) -> list[str]:
    """The Save-as-new ancestry stamp: the source id, then its ancestry.

    Newest first -- the source is the new wig's immediate parent, so its
    id leads, followed by the source's own ancestry unchanged. Trimmed to
    SUPERSEDES_MAX from the head, so a source already carrying a full
    16-entry chain yields ``[source_id, *first 15]`` and never a 17th:
    the WRITE end of the cap, matching ``_parse_supersedes`` on the read
    end. When the source file does not resolve locally the caller passes
    no ancestry, and the stamp is ``[source_id]`` alone -- the one link
    still known to be true.
    """
    chain = [source_wig_id, *(source_supersedes or [])]
    return chain[:SUPERSEDES_MAX]


def ensure_wig_id(wig: Wig) -> bool:
    """Give a wig an identity if it has none. True if one was minted.

    Called from ``serialize_wig``, which is the ONE choke point every
    wig passes through to become a file. Eight different constructors
    across five modules build wigs -- the adapters, the code library,
    both export builders -- and requiring each to remember would
    guarantee that one eventually did not.

    It mutates deliberately. Minting into the output dict alone would
    leave the in-memory wig without an id, and the next save would mint
    a DIFFERENT one: the same wig would change identity every time it
    was written, which is the precise opposite of the field's purpose.
    """
    if wig.wig_id:
        return False
    wig.wig_id = new_wig_id()
    return True


def new_wig_id() -> str:
    """Mint a wig identity.

    A plain UUID4 string. Deliberately random rather than derived from
    content: a wig's identity must survive every edit to its contents,
    which is the whole reason it replaced the content hash in that
    role (v0.9.5).
    """
    return str(uuid.uuid4())


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
    # No wig reaches disk without an identity (v0.9.5). See
    # ensure_wig_id for why this is here and not at each constructor.
    ensure_wig_id(wig)
    # Third, not second: format and name are what a human wants when
    # they open the file. Identity is for machines and can wait a line.
    out: dict = {"format": fmt, "name": wig.name}
    if wig.wig_id:
        out["wig_id"] = wig.wig_id
    for key, value in (
        ("brand", wig.brand),
        ("model", wig.model),
        ("kind", wig.kind),
        ("notes", wig.notes),
        ("origin", wig.origin),
        ("converted_from", wig.converted_from),
        ("converted_from_sha256", wig.converted_from_sha256),
    ):
        if value is not None:
            out[key] = value
    # Emitted as a list ALWAYS, and only when non-empty. Both writers
    # (parse and the Save-as-new stamp) have already capped it to
    # SUPERSEDES_MAX, so the on-disk list matches what every reader sees.
    if wig.supersedes:
        out["supersedes"] = list(wig.supersedes)
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
    """The canonical form of a signals array: "the same codes", exactly.

    Contract (docs/wig-format.md mirrors this, and WigFactory and any
    upstream verifier must reproduce it byte-for-byte): a JSON array of
    objects carrying EXACTLY four keys -- ``alias``, ``pronto``,
    ``ditto_count``, ``bypass_protocol`` -- every field, every signal,
    every time; keys sorted; separators compact; ``pronto`` in its
    normalized form (validator whitespace normalization, then lowercased
    hex); unknown per-signal keys excluded. Zero conditional rules.

    The four keys are the ones that shape the waveform, and that was
    chosen when this form was a fitting's binding target: a signature
    certifying that this content drove the device had to cover exactly
    what left the blaster and no more.

    - ``pronto``: the bytes. Transmitted as stored.
    - ``ditto_count``: repeat frames the encoder appends. Shapes the
      waveform.
    - ``bypass_protocol``: suppresses the re-encode. Shapes the
      waveform.
    - ``send_count``: ABSENT, deliberately. Whole-blob retransmission is
      delivery, not meaning.

    v0.9.5 moved attestation onto per-row digests (``row_digest``,
    which keeps exactly these axes minus the alias), so nothing signs
    this form any more. It survives as the DEDUPLICATION identity: two
    wigs with the same canonical signals are the same codes under
    possibly different names, which is what the duplicate-drop receipt
    and the identity cache each need to know. Both are local judgments
    about local files, so the old worry about forking hashes across
    installs no longer bites -- but the form is contract anyway,
    because docs/wig-format.md publishes it.
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
    """``sha256:<hex>`` over the canonical signals form.

    NEVER WRITTEN TO A FLAT WIG (hard rule 2). Nothing on disk carries
    this: a flat wig's claims bind row digests, one per row, so that
    editing one code orphans one claim instead of invalidating
    everybody's attestation of every other row. This is an in-memory
    identity for local bookkeeping and nothing else.
    """
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
    """"Are these two wigs the same codes?", for either shape.

    NOT an attestation binding, despite the name it kept from when it
    was one. Claims bind row digests on a flat wig and ``cells_hash`` on
    a matrix wig; neither reads this. It answers the duplicate-drop
    question, and it dispatches on SHAPE because a matrix wig's codes
    live in its lattice: hashing only the (empty) signals list made
    every matrix wig collide with every other one, so a Mitsubishi drop
    reported itself as already in Toyotomi (owner bench 2026-07-28).
    """
    if wig.climate is not None:
        return cells_content_hash(wig.climate)
    return signals_content_hash(wig.signals)


def _slug_part(text: str) -> str:
    """One filename part, slugified: lowercase, runs of non-alphanumerics
    collapse to a single hyphen, ends trimmed.

    The single rule ``wig_filename`` and the field-derived download name
    both share, so ``TH-05`` becomes ``th-05`` in each (owner ruling).
    Returns "" when nothing survives.
    """
    return re.sub(
        r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())
    ).strip("-")


def wig_filename(name: str, taken: set[str] | None = None) -> str:
    """Slugify ``name`` into a ``.wig.json`` filename, dodging ``taken``.

    "Foxtel IQ" -> "foxtel-iq.wig.json"; on collision, "-2", "-3", ...
    """
    slug = _slug_part(name)
    if not slug:
        slug = "wig"
    taken = taken or set()
    candidate = f"{slug}{WIG_SUFFIX}"
    n = 2
    while candidate in taken:
        candidate = f"{slug}-{n}{WIG_SUFFIX}"
        n += 1
    return candidate


# Download-name tier suffixes (v0.9.7 Second Fitting). HYPHENATED, never
# dotted: a dot in the stem fails the shop's filename rule, which was the
# whole reason a fitted download would not upload. An unproven wig gets
# no suffix.
_DOWNLOAD_TIER_SUFFIX = {"perfect": "-perfect-fit", "scoped": "-fitted"}


def download_filename(wig: Wig) -> str:
    """The suggested download name, composed from the wig's own fields.

    ``<brand>-<kind>-<model>[-<tier>].wig.json``. Each part is slugified
    by the ``wig_filename`` rule (``TH-05`` -> ``th-05``), skipping any
    part the wig does not carry. Brand is the anchor of the repo naming
    convention, so when the wig has no brand the stem falls back to the
    slug of its name -- exactly what a plain download produced before
    this existed.

    The tier comes from the wig's OWN claims via ``claims_summary``:
    ``perfect`` appends ``-perfect-fit``, ``scoped`` appends ``-fitted``,
    an unproven wig appends nothing. Hyphenated, never dotted. Pure and
    WS-free so it is testable on its own and reusable if another surface
    ever needs the same name.
    """
    # Local import: wig_fitting imports this module, so a module-level
    # import would be circular. The tier is claims-derived and belongs to
    # the ledger, but the composition belongs here beside wig_filename.
    from .wig_fitting import claims_summary

    if wig.brand and wig.brand.strip():
        stem = "-".join(
            _slug_part(part)
            for part in (wig.brand, wig.kind, wig.model)
            if part and part.strip()
        )
    else:
        stem = _slug_part(wig.name)
    if not stem:
        stem = "wig"
    tier = claims_summary(wig, None).get("state")
    stem += _DOWNLOAD_TIER_SUFFIX.get(tier or "", "")
    return f"{stem}{WIG_SUFFIX}"


# ---------------------------------------------------------------------------
# Claims (v0.9.5 "Fitting Room")
# ---------------------------------------------------------------------------
#
# A fitting is no longer a claim about a whole file. It is a signed
# bundle of PER-ROW claims, each binding one row's transmit recipe by
# digest. That single change dissolves the machinery the old model
# needed: staleness, carry maps, hash rolls and re-seeding all existed
# to keep a whole-file claim attached to a file that kept changing.
# Edit a row now and only that row's claims are orphaned, by
# construction.
#
# Wig-level facts are DERIVED, never stored: "perfect fit by X" means
# X's claims cover every row; "proven" means the union of everybody's
# claims does. Storing them would let the file disagree with itself.

VERDICT_WORKED = "worked"
#: Why a row was NOT claimed. Standardized, never free text, so the
#: shop can count them: three fitters reporting wont_work on the same
#: row is a mechanical review flag rather than three sentences someone
#: has to read.
VERDICT_NOT_ON_DEVICE = "not_on_device"
VERDICT_WONT_WORK = "wont_work"
EXCLUSION_REASONS = (VERDICT_NOT_ON_DEVICE, VERDICT_WONT_WORK)
VERDICTS = (VERDICT_WORKED, *EXCLUSION_REASONS)


def normalized_pronto(code: str) -> str:
    """A Pronto code in the form the canonical serializers hash.

    Validator whitespace normalization, then lowercased -- byte-identical
    to what ``canonical_cells_json`` writes, so "same code" means the
    same thing to the digest as it does to the hash. Lives here, beside
    the digest it defines, because it IS part of the canonicalization
    contract an external verifier has to reproduce.
    """
    result = validate_pronto(code)
    return (result.normalized if result.valid else code).lower()


def row_digest(
    pronto: str, ditto_count: int = 0, bypass_protocol: bool = False
) -> str:
    """THE canonicalization contract. Reproduce this byte-for-byte.

    ``sha256(normalized_pronto + "|d<ditto>" + "|b<0|1>")``, truncated
    to 16 hex characters. Exact layout, so WigFactory and any external
    verifier can reproduce it: the normalized pronto, then ``|d`` and
    the integer ditto count, then ``|b1`` or ``|b0``.

    ALIAS IS OUT, and must never be added: names are metadata, renames
    are free, and a claim has to survive one. SEND_COUNT IS OUT, and
    must never be added: it is delivery, not meaning -- how many times
    to press depends on the room, not the device, so two people proving
    the same codes at three and five sends are proving the same thing.

    What IS in is what changes the waveform: the bytes, the repeat
    frames appended to them, and whether the encoder is bypassed
    entirely. That is exactly the set a claim needs to bind, because it
    is exactly the set that decides what leaves the emitter.
    """
    recipe = (
        f"{normalized_pronto(pronto)}"
        f"|d{int(ditto_count)}"
        f"|b{1 if bypass_protocol else 0}"
    )
    return hashlib.sha256(recipe.encode("utf-8")).hexdigest()[:16]


def signal_row_digest(signal: WigSignal) -> str:
    """The digest of a flat wig's signal row."""
    return row_digest(
        signal.pronto, signal.ditto_count, signal.bypass_protocol
    )


def is_legacy_fitting(entry: object) -> bool:
    """True for a pre-claims fitting, under ANY format major.

    THE DISCRIMINATOR IS THE SHAPE, NEVER THE VERSION STAMP (hard rule
    6). The stamp describes what capabilities a reader needs, not what
    is actually in the block, and the two demonstrably drift: this very
    branch wrote ``hair-wig/3`` files carrying old whole-wig fittings
    before the claims model landed. Trusting the major would let those
    through into a format with no reader for them.

    Legacy carries ``content_hash``. A claims bundle carries ``wig_id``
    and ``rows``, and a MATRIX bundle names its lattice binding
    ``cells_hash`` -- never ``content_hash``, precisely so this stays a
    single test with no overlap. No legitimate file carries both.
    """
    if not isinstance(entry, dict):
        return False
    return "content_hash" in entry


def is_claims_bundle(entry: object) -> bool:
    """True for a claims bundle. The complement of the above."""
    if not isinstance(entry, dict):
        return False
    return "wig_id" in entry and "rows" in entry


@dataclass
class RowClaim:
    """One person's claim about one row's transmit recipe."""

    #: The row's name WHEN CLAIMED. Display context only: it is not in
    #: the digest, so a later rename cannot invalidate the claim, and
    #: this is what lets the save dialog say "the wig calls this On;
    #: you call it Power" instead of silently orphaning a row.
    alias_at_claim: str
    digest: str
    verdict: str


@dataclass
class ClaimsBundle:
    """A signed set of row claims: one person, one sitting, one wig."""

    wig_id: str
    rows: list[RowClaim]
    handle: str | None = None
    github: str | None = None
    date: str | None = None
    note: str | None = None
    #: MATRIX ONLY, and never named ``content_hash`` (hard rule 6). A
    #: dimension checklist samples a lattice, so it has to pin the
    #: lattice it sampled -- the claim is about the set, not just the
    #: rows walked.
    cells_hash: str | None = None
    key: str | None = None
    sig: str | None = None
    extra: dict = field(default_factory=dict)


_KNOWN_CLAIM = {"alias_at_claim", "digest", "verdict"}
_KNOWN_BUNDLE = {
    "wig_id", "rows", "handle", "github", "date", "note",
    "cells_hash", "key", "sig",
}


def parse_claims_bundle(raw: object) -> ClaimsBundle | None:
    """Read one claims bundle, or None if it is not one.

    Forgiving by design: a bundle from a newer HAIR carrying fields
    this one does not know keeps them in ``extra`` and round-trips
    them, because dropping a field would silently break the signature
    that covers it.
    """
    if not is_claims_bundle(raw):
        return None
    assert isinstance(raw, dict)
    wig_id = _str_or_none(raw.get("wig_id"))
    if not wig_id:
        return None
    rows: list[RowClaim] = []
    for item in raw.get("rows") or []:
        if not isinstance(item, dict):
            continue
        digest = _str_or_none(item.get("digest"))
        verdict = _str_or_none(item.get("verdict"))
        if not digest or verdict not in VERDICTS:
            continue
        alias = item.get("alias_at_claim")
        rows.append(RowClaim(
            alias_at_claim=alias if isinstance(alias, str) else "",
            digest=digest,
            verdict=verdict,
        ))
    return ClaimsBundle(
        wig_id=wig_id,
        rows=rows,
        handle=_str_or_none(raw.get("handle")),
        github=_str_or_none(raw.get("github")),
        date=_str_or_none(raw.get("date")),
        note=_str_or_none(raw.get("note")),
        cells_hash=_str_or_none(raw.get("cells_hash")),
        key=_str_or_none(raw.get("key")),
        sig=_str_or_none(raw.get("sig")),
        extra={k: v for k, v in raw.items() if k not in _KNOWN_BUNDLE},
    )


def claims_bundle_out(bundle: ClaimsBundle) -> dict:
    """Serialize a bundle. Key order stable, absent fields omitted.

    The output of this IS what gets signed (minus ``sig``), so its
    shape is part of the contract: adding a field here changes what a
    signature covers.
    """
    out: dict = {"wig_id": bundle.wig_id}
    for key, value in (
        ("handle", bundle.handle),
        ("github", bundle.github),
        ("date", bundle.date),
        ("note", bundle.note),
        ("cells_hash", bundle.cells_hash),
    ):
        if value is not None:
            out[key] = value
    out["rows"] = [
        {
            "alias_at_claim": row.alias_at_claim,
            "digest": row.digest,
            "verdict": row.verdict,
        }
        for row in bundle.rows
    ]
    out.update(bundle.extra)
    for key in ("key", "sig"):
        value = getattr(bundle, key)
        if value is not None:
            out[key] = value
    return out


def wig_row_digests(wig: Wig) -> list[str]:
    """Every flat row's digest, in file order.

    Matrix wigs return nothing here: their claims bind the lattice by
    ``cells_hash`` and their rows are checklist coordinates, not
    signals.
    """
    if wig.climate is not None:
        return []
    return [signal_row_digest(s) for s in wig.signals]


def claims_of(wig: Wig) -> list[ClaimsBundle]:
    """Every claims bundle on a wig, legacy fittings skipped."""
    raw = wig.extra.get("fittings")
    if not isinstance(raw, list):
        return []
    out = []
    for entry in raw:
        bundle = parse_claims_bundle(entry)
        if bundle is not None:
            out.append(bundle)
    return out


def drop_legacy_fittings(wig: Wig) -> int:
    """Strip pre-claims fittings, returning how many were dropped.

    Called on import so the notice can say what happened. They cannot
    become claims: a whole-file hash says "these bytes, all of them",
    which carries no information about WHICH rows anybody proved, and
    inventing per-row claims from it would manufacture evidence nobody
    gave.
    """
    raw = wig.extra.get("fittings")
    if not isinstance(raw, list):
        return 0
    kept = [e for e in raw if not is_legacy_fitting(e)]
    dropped = len(raw) - len(kept)
    if dropped:
        if kept:
            wig.extra["fittings"] = kept
        else:
            wig.extra.pop("fittings", None)
    return dropped


def perfect_by(bundle: ClaimsBundle, digests: list[str]) -> bool:
    """Did this fitter claim every row worked?

    DERIVED, never stored. A stored flag could disagree with the rows
    beside it the moment one of them was edited.
    """
    if not digests:
        return False
    worked = {
        row.digest for row in bundle.rows if row.verdict == VERDICT_WORKED
    }
    return all(digest in worked for digest in digests)


def coverage(bundles: list[ClaimsBundle], digests: list[str]) -> set[str]:
    """Which rows anybody has claimed worked. The union, derived."""
    proven = {
        row.digest
        for bundle in bundles
        for row in bundle.rows
        if row.verdict == VERDICT_WORKED
    }
    return {digest for digest in digests if digest in proven}
