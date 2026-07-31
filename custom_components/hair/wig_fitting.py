"""Fittings: proving a wig on real hardware (Perfect Fit).

Design source: docs/internal/plans/fitting-flow.md. The load-bearing
rulings, restated:

- A fitting is per-signal human verdicts (worked / did not), and the
  overall verdict is DERIVED from them, never asked (2.2). PERFECT FIT
  means every signal confirmed and none failed.
- Session state lives IN THE LOCAL WIG FILE, not a side store (13.3):
  the first mark writes a draft fitting into the .wig.json (debounced),
  so progress survives reboots and updates. RESUME is just reading the
  file. DISCARD removes the draft; closing the dialog loses nothing.
- Partials and drafts are LOCAL ONLY (2.3): the share paths (download /
  copy JSON) strip every fitting that is not complete-and-signed, and
  drop the ``fittings`` key when nothing survives. The on-disk file
  always keeps everything.
- Fittings bind to ``wig_content_hash`` (tamper evidence): the v1
  signals hash for signal wigs, byte-for-byte as shipped in 0.8.0, and
  the cells hash for matrix wigs (Cold Cuts) -- the dimension check
  attests the MATRIX, so that is what the hash must cover. A hash
  mismatch marks the fitting invalid ("codes changed since this
  fitting") rather than deleting it.
- The verdict lists are ROW-KEY lists, not counts: the alias for a
  signal wig, the checklist cell key ("cool/auto/23", "on", "off") for
  a matrix wig. Both live inside their canonical hash form, so a
  rename breaks the hash and invalidates the fitting instead of
  silently mismatching.
- Matrix wigs fit through the SAME manager via the rows abstraction
  (``fitting_rows``): a session addresses rows by index whichever kind
  of wig is under test, and only the row source differs -- the signals
  array for v1 wigs, the dimension checklist for matrix wigs (owner
  rulings 2026-07-28: nobody fits 2,689 cells; everybody can fit every
  dimension).

Smart Perm adds REPLACE (Section 4 of the implementation brief): a
fitting row's code can be swapped in place from a paste or a live
Sniffer capture. Three rules ride with it and are load-bearing:

- Replace is the ONLY path that changes a wig's codes, it is always
  explicit, it always stamps provenance, and it always rolls the
  content hash. Pasting the code that is already there is refused
  rather than stamped, so "a provenance marker exists" always implies
  "the hash rolled" -- which is what keeps an appended Changed Codes
  row from retroactively demoting somebody else's complete fitting.
- Nothing ever edits a signed fitting. Replace re-binds only the
  CALLING user's open draft; everyone else's fittings go stale by
  hash, which is tamper evidence working as designed.
- Carry-forward is byte-exact or nothing. A verdict carries into the
  next session only when the row's key AND its normalized Pronto match
  what the old fitting covered, proven against the ``carry`` receipt
  written at replace time -- never on the key alone.

Storage shape: fittings live under the ``fittings`` top-level key,
which wig_format deliberately does NOT school itself on -- it rides in
``Wig.extra`` under the unknown-key preservation contract (an older
install editing the wig cannot destroy them). This module is the only
writer. Entries it cannot parse are preserved on disk, surfaced as
warnings, and dropped from the share paths (a newer format's fitting is
not something this install can attest as complete).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import MAX_SEND_COUNT
from .pronto_validator import validate_pronto
from .wig_format import Wig, cell_key, serialize_wig, wig_content_hash

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .signal_monitor import SignalMonitor

_LOGGER = logging.getLogger(__name__)

FITTINGS_KEY = "fittings"
# Receipts, both OUTSIDE every canonical hash (wig / signal / cell
# extra, preserved by every reader since v1): recording provenance or
# carry-forward evidence must never move a wig's identity.
PROVENANCE_KEY = "provenance"
PROVENANCE_POWER_KEY = "provenance_power"
CARRY_KEY = "carry"
# What a replaced row used to be (owner rulings 2026-07-30, second
# bench). One entry per replaced row, keyed by row key, holding the
# code the wig CAME WITH -- the first replace on a row records it and
# later replaces never overwrite it, so "put it back" always means the
# file's own original however many repairs happened since.
#
# Two consumers, and they stop at different places:
#
# - REVERT, offered on the row's provenance chip, works off this
#   record forever. Signing does not take it away (owner ruling): a
#   capture you proved and later regret is still fixable, at the price
#   of the signed fitting going stale by hash, which is what a hash is
#   for.
# - DISCARD only puts back rows this user replaced in the CURRENT
#   unsigned session, which is what ``by`` and ``session`` track.
#   FINISH clears ``session`` and leaves everything else standing.
#
# In the wig file, not a side store, for the same reason marks are
# (design 13.3): an HA restart must not quietly turn a revertible
# replace into a permanent one.
REPLACED_FROM_KEY = "replaced_from"

# The Changed Codes section (brief 4.6): replaced cells that are not
# already dimension-checklist rows list here and are proved like any
# other row.
SECTION_CHANGED = "changed"

REPLACE_SOURCES = ("captured", "pasted")

# Marks are written through to the wig file with this debounce, so a
# fast run down a signal list costs one write, not one per tap.
FITTING_WRITE_DEBOUNCE_S = 2.0

# How long a fitting send waits for its Mirror echo before reporting
# heard=false. Loopback normally lands within ~300 ms; this stays under
# MIRROR_ECHO_TTL_S so we never report on an expired expectation.
FITTING_HEARD_WAIT_S = 2.0

_VERDICT_WORKED = "worked"
_VERDICT_FAILED = "failed"
_VERDICT_UNTESTED = "untested"
VERDICTS = (_VERDICT_WORKED, _VERDICT_FAILED, _VERDICT_UNTESTED)


# ---------------------------------------------------------------------------
# Pure layer: parsing, completeness, summaries, share stripping
# ---------------------------------------------------------------------------


@dataclass
class FittingRowSpec:
    """One row of a fitting session, with everything any consumer needs.

    THE single row source (Smart Perm). Before this, ``fitting_rows``
    built the send/mark index from the dimension checklist while
    ``ws_fitting_state`` rebuilt its display rows from
    ``dimension_checklist`` separately -- fine while the two lists were
    the same length, and a silent index shear the moment Changed Codes
    rows started appending to one of them. Both now project from here.
    """

    key: str
    pronto: str
    send_count: int = 1
    # None for signal wigs; the checklist section or SECTION_CHANGED
    # for matrix wigs.
    section: str | None = None
    mode: str | None = None
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None
    temp_less: bool = False
    temp_role: str | None = None
    # The replaced-marker riding this row's extra, or None.
    provenance: dict[str, Any] | None = None
    # True when an earlier code for this row is on record, so the
    # chip can offer REVERT. Resolved by the caller that needs it
    # (``revertible_keys``), not by the row builder, which stays a
    # pure projection of the wig.
    revertible: bool = False
    # True for a comb suspect surfaced for proofing that is NOT a
    # fitting row. It can be sent and replaced; it carries no verdict
    # and never counts toward completeness (see session_row_specs).
    advisory: bool = False


def _provenance_of(extra: dict[str, Any] | None) -> dict[str, Any] | None:
    """A readable ``provenance`` marker out of a signal / cell extra."""
    if not isinstance(extra, dict):
        return None
    marker = extra.get(PROVENANCE_KEY)
    return marker if isinstance(marker, dict) else None


def _power_provenance(wig: Wig, which: str) -> dict[str, Any] | None:
    """The marker for a matrix power code ("on" / "off").

    Power codes are not cells, so they have no extra of their own; the
    marker rides the matrix block's extra under ``provenance_power``.
    """
    if wig.climate is None:
        return None
    block = wig.climate.extra.get(PROVENANCE_POWER_KEY)
    if not isinstance(block, dict):
        return None
    marker = block.get(which)
    return marker if isinstance(marker, dict) else None


def fitting_row_specs(wig: Wig) -> list[FittingRowSpec]:
    """Every row a fitting session walks, in session order.

    The rows abstraction (Cold Cuts): signal wigs fit their signals
    one-to-one (key = alias, exactly the pre-0.8.8 behavior); matrix
    wigs fit the DIMENSION CHECKLIST (key = cell key, or literal
    "on"/"off"), never the raw lattice. Deterministic by construction
    on both sides -- session indexes, marks, and completeness all key
    off this one list, so the two wig kinds cannot drift apart. Note
    the deliberate asymmetry: a matrix wig's flat extras (on_once,
    sleep...) are NOT rows; the dimension check attests the matrix,
    and the extras are ordinary buttons outside its hash.

    Smart Perm appends the CHANGED CODES section (brief 4.6) for
    matrix wigs: one row per replaced cell that the checklist does not
    already cover, in file order, so the human proves exactly the cells
    the machine touched. A signal wig grows nothing -- every signal is
    already a standard row, so a replaced one keeps its place and just
    carries a chip. These rows join completeness like any other, which
    is only safe because a marker cannot exist without a replace, and a
    replace always rolls the hash (see ``async_replace``).
    """
    if wig.climate is None:
        return [
            FittingRowSpec(
                key=sig.alias,
                pronto=sig.pronto,
                send_count=sig.send_count,
                provenance=_provenance_of(sig.extra),
            )
            for sig in wig.signals
        ]

    from .wig_climate import dimension_checklist

    by_key: dict[str, Any] = {}
    for cell in wig.climate.cells:
        by_key.setdefault(cell_key(cell), cell)

    specs: list[FittingRowSpec] = []
    for row in dimension_checklist(wig.climate):
        if row.key in ("on", "off"):
            marker = _power_provenance(wig, row.key)
        else:
            marker = _provenance_of(getattr(by_key.get(row.key), "extra", None))
        specs.append(FittingRowSpec(
            key=row.key,
            pronto=row.pronto,
            send_count=row.send_count,
            section=row.section,
            mode=row.mode,
            fan=row.fan,
            swing=row.swing,
            temp=row.temp,
            temp_less=row.temp_less,
            temp_role=row.temp_role,
            provenance=marker,
        ))

    seen = {spec.key for spec in specs}
    for cell in wig.climate.cells:
        marker = _provenance_of(cell.extra)
        if marker is None:
            continue
        key = cell_key(cell)
        if key in seen:
            continue
        seen.add(key)
        specs.append(FittingRowSpec(
            key=key,
            pronto=cell.pronto,
            send_count=cell.send_count,
            section=SECTION_CHANGED,
            mode=cell.mode,
            fan=cell.fan,
            swing=cell.swing,
            temp=cell.temp,
            provenance=marker,
        ))
    return specs


def _row_provenance(wig: Wig, key: str) -> dict[str, Any] | None:
    """The marker currently on a row, by key. None when it has none."""
    if wig.climate is not None:
        if key in ("on", "off"):
            return _power_provenance(wig, key)
        for cell in wig.climate.cells:
            if cell_key(cell) == key:
                return _provenance_of(cell.extra)
        return None
    for sig in wig.signals:
        if sig.alias == key:
            return _provenance_of(sig.extra)
    return None


def _write_row_code(
    wig: Wig, key: str, pronto: str, marker: dict[str, Any] | None
) -> bool:
    """Put ``pronto`` on the row ``key`` names and stamp its provenance.

    Three destinations, because a row key means three different things:
    a signal alias, a matrix cell coordinate, or one of the literal
    power keys "on" / "off" -- which are not cells at all, so their
    marker rides the matrix block instead. Repeat replaces overwrite
    the marker (latest wins). A ``marker`` of None REMOVES it, which is
    the discard-revert path: a code that went back to what it was was
    never replaced, and leaving the marker would claim otherwise (and
    on a matrix wig would leave a Changed Codes row behind it).
    Returns False when the key addresses nothing, which means the
    caller's row list and the wig have drifted.
    """
    def _stamp(extra: dict[str, Any]) -> None:
        if marker is None:
            extra.pop(PROVENANCE_KEY, None)
        else:
            extra[PROVENANCE_KEY] = marker

    if wig.climate is not None:
        if key in ("on", "off"):
            if key == "on":
                wig.climate.on = pronto
            else:
                wig.climate.off = pronto
            block = wig.climate.extra.get(PROVENANCE_POWER_KEY)
            if not isinstance(block, dict):
                block = {}
            if marker is None:
                block.pop(key, None)
            else:
                block[key] = marker
            if block:
                wig.climate.extra[PROVENANCE_POWER_KEY] = block
            else:
                wig.climate.extra.pop(PROVENANCE_POWER_KEY, None)
            return True
        for cell in wig.climate.cells:
            if cell_key(cell) == key:
                cell.pronto = pronto
                _stamp(cell.extra)
                return True
        return False
    for sig in wig.signals:
        if sig.alias == key:
            sig.pronto = pronto
            _stamp(sig.extra)
            return True
    return False


def fitting_rows(wig: Wig) -> list[tuple[str, str, int]]:
    """What a fitting session sends: (key, pronto, send_count).

    A projection of :func:`fitting_row_specs`, kept as the narrow shape
    the send / mark / completeness paths have always used.
    """
    return [
        (spec.key, spec.pronto, spec.send_count)
        for spec in fitting_row_specs(wig)
    ]


def session_row_specs(wig: Wig) -> list[FittingRowSpec]:
    """Fitting rows, plus comb suspects appended as ADVISORY rows.

    The dialog walks this; completeness does not. That distinction is
    the whole design, and getting it backwards would be quietly
    destructive:

    Combing stamps a receipt WITHOUT rolling the content hash -- by
    design, so recording what was found never invalidates a fitting. But
    it means that if suspects counted toward completeness, running a comb
    on a wig would retroactively demote every complete fitting in its
    ledger, including other people's, with no code having changed
    anywhere. Somebody's signed PERFECT FIT would silently become partial
    because a different person pressed a button in a different install.

    So a suspect appears in the session to be SENT and, if it is wrong,
    REPLACED -- and replacing it stamps provenance, which rolls the hash,
    which is what legitimately promotes it to a Changed Codes row that
    does count. Lint finds it, the session shows it, replace fixes it,
    and only then does the arithmetic move.

    A suspect that is already a checklist or changed row is NOT
    duplicated here; it is the same row, and it keeps its verdict
    buttons.
    """
    from .wig_comb import suspect_keys

    specs = fitting_row_specs(wig)
    known = {spec.key for spec in specs}
    suspects = [key for key in suspect_keys(wig) if key not in known]
    if not suspects:
        return specs

    by_key: dict[str, Any] = {}
    if wig.climate is not None:
        for cell in wig.climate.cells:
            by_key.setdefault(cell_key(cell), cell)
    else:
        for sig in wig.signals:
            by_key.setdefault(sig.alias, sig)

    for key in suspects:
        source = by_key.get(key)
        if source is None:
            # The receipt names a row that no longer exists: the codes
            # moved since it was written. Silently skipped -- a stale
            # receipt is expected, and combing again is what fixes it.
            continue
        specs.append(FittingRowSpec(
            key=key,
            pronto=source.pronto,
            send_count=source.send_count,
            section=SECTION_CHANGED,
            mode=getattr(source, "mode", None),
            fan=getattr(source, "fan", None),
            swing=getattr(source, "swing", None),
            temp=getattr(source, "temp", None),
            provenance=_provenance_of(source.extra),
            advisory=True,
        ))
    return specs


@dataclass
class Fitting:
    """One parsed fittings entry, wrapping its raw dict.

    ``raw`` is the live dict inside ``Wig.extra["fittings"]``; mutations
    through the manager write into it so unknown per-fitting keys are
    preserved. The parsed attributes are read-time conveniences.
    """

    raw: dict[str, Any]
    handle: str
    confirmed: list[str]
    failed: list[str]
    content_hash: str
    draft: bool

    @property
    def github(self) -> str | None:
        value = self.raw.get("github")
        return value if isinstance(value, str) and value else None

    @property
    def send_times_used(self) -> int | None:
        """The send-times evidence this fitting carries, clamped.

        ABSENT IS NOT 1: a fitting without the field predates it (or
        came from a tool that does not write it) and claims nothing --
        None here, never coerced. An explicit value is clamped to
        1..MAX_SEND_COUNT on read (design 5.3: a signature makes a
        value tamper-evident, not sane).
        """
        return _read_send_times(self.raw)


@dataclass
class FittingsView:
    """Every parseable fitting in a wig, plus what could not be parsed."""

    fittings: list[Fitting] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_fittings(wig: Wig) -> FittingsView:
    """Read ``wig.extra['fittings']`` permissively.

    A malformed block or entry never invalidates the wig (plan 5.1: the
    block is surfaced, not fatal); it is skipped with a warning and left
    untouched on disk.
    """
    view = FittingsView()
    raw_list = wig.extra.get(FITTINGS_KEY)
    if raw_list is None:
        return view
    if not isinstance(raw_list, list):
        view.warnings.append('"fittings" is not a list; ignored')
        return view
    for i, entry in enumerate(raw_list):
        parsed = _parse_entry(entry)
        if parsed is None:
            view.warnings.append(
                f"fittings[{i}]: unreadable entry (kept on disk, "
                "ignored here)"
            )
            continue
        view.fittings.append(parsed)
    return view


def _parse_entry(entry: Any) -> Fitting | None:
    if not isinstance(entry, dict):
        return None
    handle = entry.get("handle")
    content_hash = entry.get("content_hash")
    if not isinstance(handle, str) or not handle:
        return None
    if not isinstance(content_hash, str) or not content_hash:
        return None
    confirmed = entry.get("confirmed", [])
    failed = entry.get("failed", [])
    if not _is_str_list(confirmed) or not _is_str_list(failed):
        return None
    return Fitting(
        raw=entry,
        handle=handle,
        confirmed=list(confirmed),
        failed=list(failed),
        content_hash=content_hash,
        draft=entry.get("draft") is True,
    )


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _read_send_times(entry: dict[str, Any]) -> int | None:
    """Read ``send_times_used`` from a raw fitting dict, clamped.

    None for absent or unreadable (bool is an int subclass and reads
    as garbage, not as 1). This is the ONE place the value is parsed,
    so the absent-is-not-1 rule cannot drift between readers.
    """
    value = entry.get("send_times_used")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(1, min(value, MAX_SEND_COUNT))


def fitting_send_times_max(wig: Wig) -> int:
    """The highest send-times any fitter needed: the adopt/factory seed.

    THE single aggregation point (handoff 4.1): ADOPT DEVICE, the
    factory and the shop index all call this, so the rule cannot
    drift. Max, never mean or mode -- send times is a threshold ("at
    least N to be reliable"), and averaging [1, 3, 3] to 2 serves
    nobody (design section 4).

    Counts every COMPLETE fitting whose content hash matches the
    CURRENT codes, signed or unsigned (design 5.0: a measurement, not
    a vote; the incentive to inflate is nil). Stale-hash fittings
    describe different codes and are excluded. Absent values
    contribute nothing. Returns 1 when nothing is known.
    """
    best = 1
    for fitting in parse_fittings(wig).fittings:
        if not fitting_is_valid(fitting, wig):
            continue
        if not fitting_is_complete(fitting, wig):
            continue
        value = fitting.send_times_used
        if value is not None and value > best:
            best = value
    return best


def fitting_is_valid(fitting: Fitting, wig: Wig) -> bool:
    """Hash validity: do the codes still match what was fitted?"""
    return fitting.content_hash == wig_content_hash(wig)


def fitting_is_complete(fitting: Fitting, wig: Wig) -> bool:
    """Complete = signed (not draft), nothing failed, every row confirmed.

    Only a complete fitting travels (2.3) and only complete fittings
    count toward the factory promotion bar (Section 8). "Every row" is
    the rows abstraction: aliases for signal wigs, the dimension
    checklist for matrix wigs.
    """
    if fitting.draft or fitting.failed:
        return False
    keys = {key for key, _, _ in fitting_rows(wig)}
    return keys <= set(fitting.confirmed)


def shared_wig_text(wig: Wig) -> str:
    """Serialize a wig for the SHARE paths (download / copy JSON).

    Keeps only complete, hash-valid fittings; drops the ``fittings`` key
    entirely when nothing survives; drops unparseable entries (this
    install cannot attest them). The on-disk file is never touched by
    this -- partials are progress, not attestations, and the shared
    artifact must not carry half-claims (owner ruling 2026-07-25).
    """
    view = parse_fittings(wig)
    kept = [
        f.raw for f in view.fittings
        if fitting_is_complete(f, wig) and fitting_is_valid(f, wig)
    ]
    extra = dict(wig.extra)
    if kept:
        extra[FITTINGS_KEY] = kept
    else:
        extra.pop(FITTINGS_KEY, None)

    # Carry snapshots exist to seed the NEXT session against a fitting
    # this install holds. Stripping a fitting therefore strips the
    # snapshot it was for, or the shared file ships digests of codes
    # keyed to an attestation that is not in it.
    live = {f.get("content_hash") for f in kept}
    carry = {
        h: rows for h, rows in _carry_map(wig).items() if h in live
    }
    if carry:
        extra[CARRY_KEY] = carry
    else:
        extra.pop(CARRY_KEY, None)

    # A shared wig says what a code IS and what it WAS, never whose
    # session it is in the middle of. Dropping ``by`` and ``session``
    # keeps REVERT working for the recipient (it needs the codes) while
    # making sure a stranger's in-flight replace can never be swept up
    # by their discard.
    origins = {
        key: {
            k: v for k, v in record.items()
            if k not in ("by", "session")
        }
        for key, record in _origin_map(wig).items()
    }
    if origins:
        extra[REPLACED_FROM_KEY] = origins
    else:
        extra.pop(REPLACED_FROM_KEY, None)
    stripped = Wig(
        name=wig.name,
        signals=wig.signals,
        brand=wig.brand,
        model=wig.model,
        kind=wig.kind,
        notes=wig.notes,
        origin=wig.origin,
        identifiers=wig.identifiers,
        # The matrix travels too (Cold Cuts): omitting it here would
        # replay the shared_wig_text field-drop bug that once ate
        # identifiers (regression-tested since 0.8.0).
        climate=wig.climate,
        extra=extra,
    )
    return serialize_wig(stripped)


def wig_needs_share_strip(wig: Wig) -> bool:
    """True when sharing this wig verbatim would leak a non-attestation.

    Lets the download path return the byte-exact original file whenever
    stripping would change nothing (hand-authored formatting survives).
    """
    # Session bookkeeping never travels, even on a wig whose fittings
    # would all survive as they are.
    if any(
        "by" in record or "session" in record
        for record in _origin_map(wig).values()
    ):
        return True
    raw_list = wig.extra.get(FITTINGS_KEY)
    if raw_list is None:
        return False
    if not isinstance(raw_list, list):
        return True
    view = parse_fittings(wig)
    if len(view.fittings) != len(raw_list):
        return True  # unparseable entries present
    return any(
        not (fitting_is_complete(f, wig) and fitting_is_valid(f, wig))
        for f in view.fittings
    )


def fitting_summary(wig: Wig, username: str | None) -> dict[str, Any]:
    """The closet-row payload: coverage, failures, local user's state.

    Computed here so the frontend filter never recomputes from raw
    fittings (plan 5.2). Hash-invalid fittings are excluded -- a row
    marker must never claim codes that changed since the fitting; the
    editor's ledger is where invalidity is explained.
    """
    rows = fitting_rows(wig)
    total = len(rows)
    view = parse_fittings(wig)
    valid = [f for f in view.fittings if fitting_is_valid(f, wig)]

    def _state(fitting: Fitting) -> str:
        if fitting_is_complete(fitting, wig):
            return "perfect"
        return "partial"

    user_fitting = next(
        (
            f for f in valid
            if username and f.handle.strip().lower() == username.strip().lower()
        ),
        None,
    )
    others_complete = sum(
        1 for f in valid
        if f is not user_fitting and fitting_is_complete(f, wig)
    )
    best: str | None = None
    if any(fitting_is_complete(f, wig) for f in valid):
        best = "perfect"
    elif valid:
        best = "partial"

    coverage_source = user_fitting or (valid[0] if valid else None)
    keys = {key for key, _, _ in rows}
    confirmed = failed = 0
    if coverage_source is not None:
        confirmed = len(set(coverage_source.confirmed) & keys)
        failed = len(set(coverage_source.failed) & keys)
    return {
        "state": best,
        "user_state": _state(user_fitting) if user_fitting else None,
        "user_draft": bool(user_fitting and user_fitting.draft),
        "confirmed": confirmed,
        "failed": failed,
        "total": total,
        "others_complete": others_complete,
        "warnings": view.warnings,
    }


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


# ---------------------------------------------------------------------------
# Carry-forward: keeping verdicts across a hash roll
# ---------------------------------------------------------------------------
# A replace edits the wig in place, so the codes the OLD fitting
# attested are gone the moment the hash rolls. Carry-forward therefore
# cannot compare against them later; the evidence has to be captured AT
# REPLACE TIME. ``wig.extra["carry"]`` maps each superseded hash to a
# snapshot of every row it had, as digests rather than whole Pronto
# codes: byte-exactness is preserved (a digest match IS a byte match)
# at about forty bytes a row instead of a kilobyte, which matters on a
# 288-signal wig. Receipts territory: wig extra, outside all hashes.


def normalized_pronto(code: str) -> str:
    """A Pronto code in the form the canonical serializers hash.

    Validator whitespace normalization, then lowercased -- byte-identical
    to what ``canonical_signals_json`` / ``canonical_cells_json`` write,
    so "same code" means the same thing here as it does to the hash.
    """
    result = validate_pronto(code)
    return (result.normalized if result.valid else code).lower()


def _row_digest(pronto: str) -> str:
    """The carry snapshot's per-row value: a truncated sha256."""
    return hashlib.sha256(
        normalized_pronto(pronto).encode("utf-8")
    ).hexdigest()[:16]


def carry_snapshot(wig: Wig) -> dict[str, str]:
    """Every current row as key -> code digest."""
    return {
        spec.key: _row_digest(spec.pronto)
        for spec in fitting_row_specs(wig)
    }


def _carry_map(wig: Wig) -> dict[str, dict[str, str]]:
    raw = wig.extra.get(CARRY_KEY)
    if not isinstance(raw, dict):
        return {}
    return {
        key: value for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _prune_carry(wig: Wig) -> None:
    """Drop carry snapshots no fitting in the file points at."""
    carry = _carry_map(wig)
    if not carry:
        wig.extra.pop(CARRY_KEY, None)
        return
    live = {f.content_hash for f in parse_fittings(wig).fittings}
    kept = {h: rows for h, rows in carry.items() if h in live}
    if kept:
        wig.extra[CARRY_KEY] = kept
    else:
        wig.extra.pop(CARRY_KEY, None)


def _origin_map(wig: Wig) -> dict[str, dict[str, Any]]:
    raw = wig.extra.get(REPLACED_FROM_KEY)
    if not isinstance(raw, dict):
        return {}
    return {
        key: value for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, dict)
        and isinstance(value.get("pronto"), str)
    }


def _origin_still_applies(record: dict[str, Any], current: str) -> bool:
    """True when the row still holds the code the record describes.

    The consistency guard on every put-back: if a row's code is not
    what the record says was written there, something outside this
    machinery has edited the file and the record no longer describes
    reality. Leave it alone rather than clobbering an unknown edit.
    """
    wrote = record.get("to")
    if not isinstance(wrote, str):
        return False
    return normalized_pronto(current) == normalized_pronto(wrote)


def revertible_keys(wig: Wig) -> set[str]:
    """Rows whose provenance chip can offer REVERT.

    A chip alone is not enough: markers also arrive inside shared wigs
    and from installs that never wrote a record, and those rows have
    nothing on disk to go back to.
    """
    origins = _origin_map(wig)
    if not origins:
        return set()
    return {
        spec.key for spec in fitting_row_specs(wig)
        if spec.key in origins
        and _origin_still_applies(origins[spec.key], spec.pronto)
    }


def pending_replaces(wig: Wig, username: str) -> int:
    """How many rows this user's DISCARD would put back.

    Only the current unsigned session's replaces: signing commits them,
    and somebody else's replace is not this session's to throw away.
    """
    handle = username.strip().lower()
    return sum(
        1 for record in _origin_map(wig).values()
        if record.get("session") is True and record.get("by") == handle
    )


def carry_forward_seed(
    wig: Wig, username: str
) -> tuple[list[str], list[str]]:
    """Verdicts a NEW session inherits from this user's last fitting.

    Seeds only rows whose key and normalized Pronto are byte-identical
    to what the old fitting covered, proven against the carry snapshot
    taken when that hash was superseded. No snapshot means no seeding:
    matching on the key alone would carry a verdict onto bytes it never
    attested, which the hard rule forbids. The old entry is never
    touched -- it is signed history; the seeded draft is new.

    Pure and side-effect free, so the dialog can SHOW what will carry
    before the first mark writes a draft carrying it.
    """
    current = wig_content_hash(wig)
    handle = username.strip().lower()
    previous = [
        f for f in parse_fittings(wig).fittings
        if f.handle.strip().lower() == handle
        and f.content_hash != current
    ]
    if not previous:
        return ([], [])
    snapshot = _carry_map(wig).get(previous[-1].content_hash)
    if not snapshot:
        return ([], [])
    source = previous[-1]
    confirmed_keys = set(source.confirmed)
    failed_keys = set(source.failed)
    confirmed: list[str] = []
    failed: list[str] = []
    for spec in fitting_row_specs(wig):
        if snapshot.get(spec.key) != _row_digest(spec.pronto):
            continue
        if spec.key in confirmed_keys:
            confirmed.append(spec.key)
        elif spec.key in failed_keys:
            failed.append(spec.key)
    return (confirmed, failed)


# ---------------------------------------------------------------------------
# The manager: sessions, sends, marks, the debounced writer
# ---------------------------------------------------------------------------


class FittingManager:
    """Fitting sessions against wig files, with write-through persistence.

    One instance per config entry, alongside signal_monitor in the entry
    data. All mutation happens on the event loop; only file I/O leaves
    it, so no lock is needed. Anything else that rewrites a wig file
    (wigs/update, delete, download) must call :meth:`async_flush` first
    so a pending debounced write can never resurrect stale content over
    a newer edit.
    """

    def __init__(self, hass: HomeAssistant, monitor: SignalMonitor) -> None:
        self._hass = hass
        self._monitor = monitor
        # filename -> in-memory Wig with unwritten fitting marks.
        self._pending: dict[str, Wig] = {}
        self._timers: dict[str, Any] = {}
        # filename -> session facts that are not (yet) in the file:
        # chosen emitter, per-signal protocol state (RC-5 toggle / Dyson
        # counter) advanced per press, receiver platform seen on echoes.
        self._sessions: dict[str, dict[str, Any]] = {}
        self._hair_version: str | None = None
        # The install's signing key, loaded (or minted) on first
        # finish. False = tried and unavailable, don't retry per-sign.
        self._signing_key: str | bool | None = None

    # -- loading ---------------------------------------------------------

    async def _load(self, filename: str) -> Wig | None:
        """The manager's view of a wig: pending in-memory copy first."""
        if filename in self._pending:
            return self._pending[filename]
        from .wig_store import load_wig

        return await self._hass.async_add_executor_job(
            load_wig, self._hass.config.config_dir, filename
        )

    def _session(self, filename: str) -> dict[str, Any]:
        return self._sessions.setdefault(filename, {
            "emitter": None,
            "emitter_platform": None,
            "receiver_platform": None,
            "extras": {},        # signal index -> live decoded_extras
            "heard": set(),      # aliases whose echo came back
            # Highest send-times value used on any send this session
            # (fine-tuned-fittings). MONOTONIC by owner ruling
            # 2026-07-30: lowering the control never lowers the
            # record, so a signal proven at 3 stays claimed at 3 even
            # if the fitter drops back to 1 for the next one. None
            # until the control is first exercised; merged into the
            # draft at mark/finish and written directly on send when
            # a draft already exists.
            "send_times": None,
        })

    def session_send_times(self, filename: str) -> int | None:
        """Peek the session's send-times record without creating one."""
        session = self._sessions.get(filename)
        if not session:
            return None
        return session.get("send_times")

    async def _versions(self) -> tuple[str | None, str | None]:
        if self._hair_version is None:
            try:
                from homeassistant.loader import async_get_integration

                from .const import DOMAIN

                integration = await async_get_integration(
                    self._hass, DOMAIN
                )
                self._hair_version = str(integration.version)
            except Exception:  # never block a fitting on metadata
                self._hair_version = ""
        try:
            from homeassistant.const import __version__ as ha_version
        except ImportError:
            ha_version = None
        return (self._hair_version or None, ha_version)

    async def _private_key(self) -> str | None:
        if self._signing_key is None:
            from .fitting_signing import async_get_private_key

            key = await async_get_private_key(self._hass)
            self._signing_key = key if key is not None else False
        return self._signing_key or None

    def _platform_of(self, entity_id: str) -> str | None:
        try:
            from homeassistant.helpers import entity_registry as er

            entry = er.async_get(self._hass).async_get(entity_id)
            platform = entry.platform if entry else None
            # Only ever a plain string lands in the fitting evidence
            # (this value is written into the wig file).
            return platform if isinstance(platform, str) else None
        except Exception:
            return None

    # -- send ------------------------------------------------------------

    async def async_send(
        self,
        filename: str,
        index: int,
        emitter_entity_id: str,
        send_times: int | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        """Send one fitting row through an emitter; report sent + heard.

        No signal-store dependency (plan 4.1): identity derives fresh
        from the row's Pronto via the shared helper, the command builds
        decoded-preferring exactly like the catalog Test path, and the
        send claims its own Mirror echo, which is where ``heard`` comes
        from. ``index`` addresses ``session_row_specs(wig)`` -- the
        session's list, comb-suspect advisory rows included, because a
        suspect exists to be SENT -- while marks stay on
        ``fitting_rows(wig)``, the countable rows. The distinction is
        load-bearing: see ``session_row_specs``.

        ``send_times`` is the session control (fine-tuned-fittings):
        this send loops that many times instead of the row's own
        ``send_count``, and the highest value ever used is recorded as
        ``send_times_used`` evidence. When the caller's ``username``
        already has a draft, the record is written into it here, on
        the send, so a mid-fitting HA restart cannot roll a tested-at-3
        claim back to 1 (handoff 4.2); before the first mark the
        session carries it, because the first mark is what creates the
        draft and a bare test send must not.
        """
        if self._hass.states.get(emitter_entity_id) is None:
            return {"success": False, "code": "entity_not_found",
                    "error": f"Entity {emitter_entity_id} not found"}
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        # The SESSION list, not the fitting list: a comb suspect must be
        # sendable, which is how a fitter decides whether it is really
        # wrong before replacing it.
        rows = [
            (s.key, s.pronto, s.send_count) for s in session_row_specs(wig)
        ]
        if not 0 <= index < len(rows):
            return {"success": False, "code": "bad_index",
                    "error": "No such signal in this wig"}
        row_key, row_pronto, row_send_count = rows[index]

        from .wig_identity import wig_signal_identity

        ident = wig_signal_identity(row_pronto)
        if ident is None:
            return {"success": False, "code": "bad_pronto",
                    "error": "This signal's Pronto code does not validate"}

        session = self._session(filename)
        session["emitter"] = emitter_entity_id
        session["emitter_platform"] = (
            self._platform_of(emitter_entity_id)
            or session["emitter_platform"]
        )
        if send_times is not None:
            used = max(1, min(int(send_times), MAX_SEND_COUNT))
            session["send_times"] = max(
                session.get("send_times") or 0, used
            )
            if username:
                draft = self._find_user_draft(wig, username)
                if draft is not None:
                    draft["send_times_used"] = max(
                        _read_send_times(draft) or 0,
                        session["send_times"],
                    )
                    self._pending[filename] = wig
                    self._schedule_write(filename)

        from .ir_command import build_command, build_decoded_command

        # Per-press protocol state: session-held extras (advanced each
        # press) override the file-derived ones, mirroring test_signal.
        # The wig file itself never stores decoded state.
        extras = session["extras"].get(index) or ident.decoded_extras
        ir_cmd = None
        if ident.decoded_fingerprint:
            ir_cmd = build_decoded_command(
                ident.decoded_protocol,
                ident.decoded_address,
                ident.decoded_command,
                repeat_count=0,
                decoded_extras=extras,
            )
        decoded_tx = ir_cmd is not None
        if ir_cmd is None:
            try:
                ir_cmd = build_command(
                    protocol="PRONTO", code=ident.pronto,
                    frequency=ident.frequency,
                )
            except ValueError as exc:
                return {"success": False, "code": "no_signal_data",
                        "error": str(exc)}

        heard_future: asyncio.Future[str | None] = (
            asyncio.get_running_loop().create_future()
        )
        label = f"Fitting send: {row_key}" if row_key else "Fitting send"
        self._monitor.record_send(
            ir_cmd, label, [emitter_entity_id],
            decoded_fingerprint=ident.decoded_fingerprint,
            heard_future=heard_future,
        )

        from homeassistant.components.infrared import (
            async_send_command as ir_send,
        )

        from .const import ASSIGN_SERVICE_TIMEOUT_S, SEND_REPEAT_GAP
        from .tx_gate import gated_send

        # The session control substitutes for the row's own send_count
        # when set (fine-tuned-fittings). THIS call's value drives the
        # loop -- the monotonic session record above is what gets
        # claimed, but a fitter who lowered the control back to 1
        # genuinely sends once.
        send_count = max(
            1, min(send_times or row_send_count or 1, MAX_SEND_COUNT)
        )
        try:
            for i in range(send_count):
                if i:
                    await asyncio.sleep(SEND_REPEAT_GAP)
                await asyncio.wait_for(
                    gated_send(
                        self._hass, emitter_entity_id, ir_cmd, ir_send
                    ),
                    timeout=ASSIGN_SERVICE_TIMEOUT_S,
                )
        except (TimeoutError, asyncio.CancelledError):
            return {"success": False, "code": "send_timeout",
                    "error": "Emitter timed out"}
        except Exception as exc:
            return {"success": False, "code": "send_failed",
                    "error": f"Emitter did not respond: {exc}"}

        # One fitting send is one logical press: advance RC-5-family
        # toggle / Dyson counter state in the session so consecutive
        # sends are always fresh (GH #33 machinery, session-scoped).
        if decoded_tx and extras:
            advanced = dict(extras)
            if "toggle" in advanced:
                advanced["toggle"] = int(advanced["toggle"]) ^ 1
            if "counter" in advanced:
                advanced["counter"] = (int(advanced["counter"]) + 1) & 0x3
            if advanced != extras:
                session["extras"][index] = advanced

        heard_receiver: str | None = None
        try:
            heard_receiver = await asyncio.wait_for(
                heard_future, FITTING_HEARD_WAIT_S
            )
        except (TimeoutError, asyncio.CancelledError):
            heard_future.cancel()
        heard = heard_receiver is not None or (
            heard_future.done() and not heard_future.cancelled()
        )
        if heard:
            session["heard"].add(row_key)
            if heard_receiver:
                session["receiver_platform"] = (
                    self._platform_of(heard_receiver)
                    or session["receiver_platform"]
                )
        return {
            "success": True,
            "heard": bool(heard),
            "decoded": decoded_tx,
        }

    # -- replace ---------------------------------------------------------

    async def async_replace(
        self,
        filename: str,
        index: int,
        pronto: str,
        source: str,
        username: str,
    ) -> dict[str, Any]:
        """Swap one fitting row's code, from a paste or a live capture.

        The only path that changes a wig's codes (brief Section 2), and
        it is never quiet about it: the new code is validated, written
        in place, stamped with provenance, and the content hash rolls.
        Everyone else's fittings go stale by hash, which is the tamper
        evidence doing its job; only the CALLING user's open draft is
        re-bound so their session survives the roll.

        Refuses a code byte-identical to the one already on the row.
        That is not pedantry: an appended Changed Codes row is only
        safe to count toward completeness because a provenance marker
        implies a hash roll, and stamping a no-op replace would add a
        row to a wig whose hash never moved -- retroactively demoting
        every complete fitting in its ledger, including other people's.
        """
        if source not in REPLACE_SOURCES:
            return {"success": False, "code": "bad_source",
                    "error": f"source must be one of {REPLACE_SOURCES}"}
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        # Session rows: repairing a comb suspect is the whole point of
        # surfacing it. Replacing one stamps provenance and rolls the
        # hash, which is what promotes it to a real Changed Codes row.
        specs = session_row_specs(wig)
        if not 0 <= index < len(specs):
            return {"success": False, "code": "bad_index",
                    "error": "No such signal in this wig"}
        row_key = specs[index].key

        result = validate_pronto(pronto)
        if not result.valid:
            reason = (
                result.errors[0] if result.errors
                else "not a valid Pronto code"
            )
            return {"success": False, "code": "bad_pronto",
                    "error": reason}
        new_code = result.normalized
        if normalized_pronto(new_code) == normalized_pronto(
            specs[index].pronto
        ):
            return {"success": False, "code": "same_code",
                    "error": "That is already this row's code"}

        old_hash = wig_content_hash(wig)
        snapshot = carry_snapshot(wig)
        marker = {"replaced": source, "date": _today()}

        # What this row used to be. The FIRST replace records the code
        # the wig came with and no later one overwrites it, so REVERT
        # always means the file's own original rather than whatever the
        # previous repair attempt happened to leave behind.
        origins = _origin_map(wig)
        record = origins.get(row_key)
        if record is None:
            record = {
                "pronto": specs[index].pronto,
                "provenance": _row_provenance(wig, row_key),
            }
            origins[row_key] = record
        record["by"] = username.strip().lower()
        record["to"] = new_code
        record["session"] = True
        wig.extra[REPLACED_FROM_KEY] = origins

        if not _write_row_code(wig, row_key, new_code, marker):
            return {"success": False, "code": "row_not_found",
                    "error": "Could not find that row's code to replace"}
        new_hash = wig_content_hash(wig)

        # Re-bind this user's open draft (brief 4.3). Without it the
        # draft-by-hash lookups all go blind the instant the hash
        # rolls: the next mark would mint a SECOND draft and the state
        # payload would report the session wiped. Every key but the
        # replaced one keeps its verdict -- those bytes did not change,
        # so those verdicts still describe them.
        carried = 0
        draft = self._find_user_draft(wig, username)
        if draft is not None:
            draft["content_hash"] = new_hash
            keys = {spec.key for spec in fitting_row_specs(wig)}
            confirmed = [
                k for k in draft.get("confirmed", []) if k != row_key
            ]
            failed = [k for k in draft.get("failed", []) if k != row_key]
            draft["confirmed"] = confirmed
            draft["failed"] = failed
            carried = len(
                (set(confirmed) | set(failed)) & keys
            )

        # The snapshot the NEXT session carries forward from, plus a
        # sweep of entries no fitting references any more (a wig
        # replaced through ten times should not carry ten dead
        # snapshots for the rest of its life). AFTER the re-bind, so
        # the sweep reads the hashes fittings actually point at now:
        # a draft that just moved to the new hash is not a reason to
        # keep a snapshot of the old one.
        carry = _carry_map(wig)
        carry[old_hash] = snapshot
        wig.extra[CARRY_KEY] = carry
        _prune_carry(wig)

        self._pending[filename] = wig
        self._schedule_write(filename)
        return {
            "success": True,
            "content_hash": new_hash,
            "row_key": row_key,
            "carried": carried,
        }

    def _put_back(self, wig: Wig, row_key: str) -> bool:
        """Restore one row to the code the wig came with.

        Shared by REVERT (one row, deliberate) and DISCARD (this
        session's rows, wholesale). Drops the record afterward, because
        a row holding its original code has nothing left to go back to
        -- and drops the provenance marker with it unless the file
        arrived carrying one, since a restored code was never replaced
        and must not keep claiming it was. On a matrix wig that is also
        what retires the row's Changed Codes entry.
        """
        origins = _origin_map(wig)
        record = origins.get(row_key)
        if record is None:
            return False
        current = {spec.key: spec.pronto for spec in fitting_row_specs(wig)}
        if row_key not in current:
            return False
        if not _origin_still_applies(record, current[row_key]):
            return False
        marker = record.get("provenance")
        if not _write_row_code(
            wig, row_key, record["pronto"],
            marker if isinstance(marker, dict) else None,
        ):
            return False
        origins.pop(row_key, None)
        if origins:
            wig.extra[REPLACED_FROM_KEY] = origins
        else:
            wig.extra.pop(REPLACED_FROM_KEY, None)
        return True

    async def async_revert(
        self, filename: str, index: int, username: str
    ) -> dict[str, Any]:
        """Put one row back to the code the wig came with.

        The other half of REPLACE, offered on the row's provenance
        chip. Available for as long as the record exists, which is
        forever (owner ruling 2026-07-30): signing does not consume it,
        so a capture that was proved and later regretted is still
        fixable. The cost is honest and visible -- the hash rolls back,
        and any fitting that attested the replaced code goes stale,
        including a signed one of the caller's own.
        """
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        specs = session_row_specs(wig)
        if not 0 <= index < len(specs):
            return {"success": False, "code": "bad_index",
                    "error": "No such signal in this wig"}
        row_key = specs[index].key

        old_hash = wig_content_hash(wig)
        snapshot = carry_snapshot(wig)
        if not self._put_back(wig, row_key):
            return {"success": False, "code": "not_revertible",
                    "error": "This row has no earlier code on record"}
        new_hash = wig_content_hash(wig)

        carry = _carry_map(wig)
        carry[old_hash] = snapshot
        wig.extra[CARRY_KEY] = carry
        _prune_carry(wig)

        carried = 0
        draft = self._find_user_draft(wig, username)
        if draft is not None:
            draft["content_hash"] = new_hash
            keys = {spec.key for spec in fitting_row_specs(wig)}
            confirmed = [
                k for k in draft.get("confirmed", []) if k != row_key
            ]
            failed = [k for k in draft.get("failed", []) if k != row_key]
            draft["confirmed"] = confirmed
            draft["failed"] = failed
            carried = len((set(confirmed) | set(failed)) & keys)

        self._pending[filename] = wig
        self._schedule_write(filename)
        return {
            "success": True,
            "content_hash": new_hash,
            "row_key": row_key,
            "carried": carried,
        }

    # -- marks -----------------------------------------------------------

    async def async_mark(
        self, filename: str, index: int, verdict: str, username: str
    ) -> dict[str, Any]:
        """Record a per-row verdict into the user's draft fitting.

        The first mark creates the draft inside the wig file (13.3);
        every mark schedules a debounced write, so progress survives
        anything short of the disk itself. ``index`` addresses
        ``fitting_rows(wig)`` and the verdict lists store ROW KEYS --
        aliases for signal wigs (unchanged on disk), checklist cell
        keys for matrix wigs, both stable across installs because both
        derive purely from file content.
        """
        if verdict not in VERDICTS:
            return {"success": False, "code": "bad_verdict",
                    "error": f"verdict must be one of {VERDICTS}"}
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        rows = fitting_rows(wig)
        if not 0 <= index < len(rows):
            return {"success": False, "code": "bad_index",
                    "error": "No such signal in this wig"}
        row_key = rows[index][0]

        draft = await self._draft_for(wig, filename, username)
        confirmed = [k for k in draft["confirmed"] if k != row_key]
        failed = [k for k in draft["failed"] if k != row_key]
        if verdict == _VERDICT_WORKED:
            confirmed.append(row_key)
        elif verdict == _VERDICT_FAILED:
            failed.append(row_key)
        draft["confirmed"] = confirmed
        draft["failed"] = failed
        draft["date"] = _today()
        self._merge_session_evidence(filename, draft)

        self._pending[filename] = wig
        self._schedule_write(filename)

        keys = {key for key, _, _ in rows}
        return {
            "success": True,
            "confirmed": len(set(confirmed) & keys),
            "failed": len(set(failed) & keys),
            "total": len(rows),
            "perfect_ready": (
                not failed and keys <= set(confirmed)
            ),
        }

    async def _draft_for(
        self, wig: Wig, filename: str, username: str
    ) -> dict[str, Any]:
        """Find or create this user's draft against the CURRENT hash.

        Match order implements plan 5.1.4's merge rule (handle plus
        content hash yields ONE fitting that grows, never two ledger
        rows): an open draft first; failing that, the user's SIGNED
        fitting on the same hash is re-opened as a draft -- resuming a
        recorded partial continues it, and FINISH re-signs it. Handle
        matching is case-insensitive so signing as "DAB" still merges
        with the HA username "dab"; a genuinely different signing
        handle starts its own ledger row, which is correct -- the row
        belongs to the attester name on it.
        """
        current_hash = wig_content_hash(wig)
        raw_list = wig.extra.get(FITTINGS_KEY)
        if not isinstance(raw_list, list):
            raw_list = []
            wig.extra[FITTINGS_KEY] = raw_list
        candidates = [
            f for f in parse_fittings(wig).fittings
            if f.handle.strip().lower() == username.strip().lower()
            and f.content_hash == current_hash
        ]
        for fitting in candidates:
            if fitting.draft:
                return fitting.raw
        if candidates:
            reopened = candidates[-1].raw
            reopened["draft"] = True
            # The content is about to change; the old attestation no
            # longer covers it. FINISH re-signs (Section 14.2).
            reopened.pop("sig", None)
            reopened.pop("key", None)
            return reopened
        # Nothing on this hash: seed the fresh draft with whatever the
        # user's last fitting still describes truthfully (Smart Perm
        # carry-forward). One bad button on a 288-signal wig is
        # fit-one-and-re-sign, not start-over. Byte-exact or nothing,
        # and send_times_used is deliberately NOT carried -- it
        # described the old session's conditions, not this one's.
        seed_confirmed, seed_failed = carry_forward_seed(wig, username)
        hair_version, ha_version = await self._versions()
        draft: dict[str, Any] = {
            "handle": username,
            "draft": True,
            "date": _today(),
            "content_hash": current_hash,
            "confirmed": seed_confirmed,
            "failed": seed_failed,
        }
        if hair_version:
            draft["hair_version"] = hair_version
        if ha_version:
            draft["ha_version"] = ha_version
        raw_list.append(draft)
        return draft

    def _merge_session_evidence(
        self, filename: str, draft: dict[str, Any]
    ) -> None:
        session = self._sessions.get(filename)
        if not session:
            return
        if session["emitter_platform"]:
            draft["emitter"] = session["emitter_platform"]
        if session["receiver_platform"]:
            draft["receiver"] = session["receiver_platform"]
        if session["heard"]:
            merged = set(draft.get("heard") or []) | session["heard"]
            draft["heard"] = sorted(merged)
        if session.get("send_times"):
            # Monotonic (owner ruling 2026-07-30): the record only ever
            # rises, so re-marking a row after lowering the control
            # cannot roll a tested-at-3 claim back down.
            draft["send_times_used"] = max(
                _read_send_times(draft) or 0, session["send_times"]
            )

    # -- finish / discard ------------------------------------------------

    async def async_finish(
        self,
        filename: str,
        username: str,
        handle: str | None,
        github: str | None,
        note: str | None,
        kind: str | None = None,
    ) -> dict[str, Any]:
        """Sign the draft: the attestation moment (State C).

        Removes the draft flag, collapses draft-only evidence, writes
        immediately, and reports the derived verdict. ``kind`` fills
        the WIG's kind when it has none (owner ruling 2026-07-27: the
        signing screen asks once, because a fitter demonstrably cares
        about this wig) -- it is a fact about the device, so it lives
        on the wig, never inside the fitting entry, and it sits
        outside the signals hash so setting it cannot invalidate the
        fitting being signed.
        """
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        draft = self._find_user_draft(wig, username)
        if draft is None:
            return {"success": False, "code": "no_draft",
                    "error": "No fitting in progress to record"}
        if kind and kind.strip() and not wig.kind:
            from .wig_format import kind_slug

            wig.kind = kind_slug(kind) or None
        self._merge_session_evidence(filename, draft)
        if handle and handle.strip():
            draft["handle"] = handle.strip()
        # Leading @ stripped: people naturally type "@name" (live bench,
        # 2026-07-27), but Tier 2 key lookups and the ledger's own @
        # prefix both want the bare handle.
        if github and github.strip().lstrip("@").strip():
            draft["github"] = github.strip().lstrip("@").strip()
        if note and note.strip():
            draft["note"] = note.strip()
        heard_list = draft.pop("heard", None)
        if heard_list:
            draft["signals_heard"] = len(heard_list)
        draft["date"] = _today()
        # Version stamps refresh at the signing moment, exactly like
        # the date (owner bench, 2026-07-30): a reopened fitting kept
        # the stamps from when its entry was FIRST created, so a
        # re-fit on 0.9.0 signed an entry claiming hair_version 0.7.2
        # while carrying send_times_used, a field 0.7.2 could not
        # write. The attestation is made now, by this install.
        hair_version, ha_version = await self._versions()
        if hair_version:
            draft["hair_version"] = hair_version
        if ha_version:
            draft["ha_version"] = ha_version
        draft.pop("draft", None)

        # Signing closes this session's replaces to DISCARD -- the
        # attestation covers the codes as they are now, so a later
        # session's discard has no business undoing them. The records
        # themselves stay (owner ruling 2026-07-30), so the chip can
        # still offer REVERT on a repair that was proved and later
        # turned out wrong.
        handle = username.strip().lower()
        origins = _origin_map(wig)
        for record in origins.values():
            if record.get("by") == handle and record.get("session") is True:
                record["session"] = False
        if origins:
            wig.extra[REPLACED_FROM_KEY] = origins

        # Sign the attestation (Section 14): per-install ed25519 key,
        # canonical form covers everything but the sig itself. A
        # signing failure records the fitting unsigned, never loses it.
        signed = False
        private_key = await self._private_key()
        if private_key is not None:
            from .fitting_signing import sign_fitting

            signed = sign_fitting(draft, private_key)

        self._pending[filename] = wig
        await self.async_flush(filename)

        fitting = _parse_entry(draft)
        complete = bool(
            fitting and fitting_is_complete(fitting, wig)
        )
        rows = fitting_rows(wig)
        keys = {key for key, _, _ in rows}
        return {
            "success": True,
            "state": "perfect" if complete else "partial",
            "confirmed": len(set(draft.get("confirmed", [])) & keys),
            "failed": len(set(draft.get("failed", [])) & keys),
            "total": len(rows),
            "signed": signed,
        }

    async def async_discard(
        self, filename: str, username: str
    ) -> dict[str, Any]:
        """Throw the session away: verdicts AND replaced codes.

        Owner bench 2026-07-30: discard is the explicit "none of this
        happened" action, so a code replaced during the session goes
        back to what it was, not just the verdicts recorded about it.
        Signed fittings stay untouched, and a replace the user already
        FINISHED is not reverted -- signing is what commits it.

        A row is only put back when it still holds the code this user's
        replace wrote. If somebody else has replaced it since, theirs
        stands: reverting it would be this session quietly editing
        another user's work.
        """
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        draft = self._find_user_draft(wig, username)
        handle = username.strip().lower()
        mine = [
            key for key, record in _origin_map(wig).items()
            if record.get("session") is True and record.get("by") == handle
        ]
        if draft is None and not mine:
            return {"success": False, "code": "no_draft",
                    "error": "No fitting in progress to discard"}

        reverted = sum(1 for key in mine if self._put_back(wig, key))

        if draft is not None:
            raw_list = wig.extra.get(FITTINGS_KEY)
            if isinstance(raw_list, list) and draft in raw_list:
                raw_list.remove(draft)
            if not raw_list:
                wig.extra.pop(FITTINGS_KEY, None)
        _prune_carry(wig)
        self._sessions.pop(filename, None)
        self._pending[filename] = wig
        await self.async_flush(filename)
        return {"success": True, "reverted": reverted}

    def _find_user_draft(
        self, wig: Wig, username: str
    ) -> dict[str, Any] | None:
        """The user's most recent draft, any hash (finish/discard target).

        Unlike mark, finish and discard do not require the current hash:
        if the codes changed mid-session the draft is stale either way,
        and the user's explicit action should still land on it.
        """
        candidates = [
            f.raw for f in parse_fittings(wig).fittings
            if f.draft and f.handle.strip().lower() == username.strip().lower()
        ]
        return candidates[-1] if candidates else None

    # -- the debounced writer -------------------------------------------

    def _schedule_write(self, filename: str) -> None:
        timer = self._timers.pop(filename, None)
        if timer is not None:
            timer.cancel()

        def _fire() -> None:
            self._timers.pop(filename, None)
            self._hass.async_create_task(self.async_flush(filename))

        self._timers[filename] = self._hass.loop.call_later(
            FITTING_WRITE_DEBOUNCE_S, _fire
        )

    async def async_flush(self, filename: str | None = None) -> None:
        """Write pending marks now. With no argument, flush everything.

        Every other wig-file writer calls this first (wigs/update,
        delete, download), so a debounced fitting write can never land
        on top of a newer edit.
        """
        names = (
            [filename] if filename is not None else list(self._pending)
        )
        for name in names:
            timer = self._timers.pop(name, None)
            if timer is not None:
                timer.cancel()
            wig = self._pending.pop(name, None)
            if wig is None:
                continue
            text = serialize_wig(wig)

            def _write(name: str = name, text: str = text) -> None:
                from .wig_store import safe_wig_filename, wigs_dir

                if not safe_wig_filename(name):
                    return
                path = wigs_dir(self._hass.config.config_dir) / name
                if not path.is_file():
                    return  # deleted mid-session; do not resurrect
                path.write_text(text, encoding="utf-8")

            try:
                await self._hass.async_add_executor_job(_write)
            except OSError as err:
                _LOGGER.warning(
                    "Could not write fitting progress to %s: %s", name, err
                )

    async def async_shutdown(self) -> None:
        """Flush everything; called from unload and HA stop."""
        await self.async_flush()
