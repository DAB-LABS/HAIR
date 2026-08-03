"""SAVE TO CLOSET: the plan the dialog draws, and the save it performs.

Two verbs behind one button (plan Section 4). A device that remembers a
``source_wig_id`` offers **UPDATE**; anything else is a **CREATE**. This
module is the seam between the device and the wig: it answers "what am I
about to attest, and against what" (``build_save_plan``) and then does
it (``perform_create`` / ``perform_update``).

Nothing here decides anything the person did not. The plan reports what
matched, what did not, and where a name differs; every check, reason and
rename is carried back in as an explicit instruction. That is the whole
reason the old fitting session died: state that accumulated behind the
fitter's back is state nobody signed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .models import IRDevice
from .wig_claims import (
    MatchRow,
    RenameProposal,
    append_claims,
    match_device_to_wig,
    update_wig_with_claims,
)
from .wig_export import WigBuild, build_wig_from_device
from .wig_format import (
    VERDICTS,
    ClaimsBundle,
    ClimateMatrix,
    RowClaim,
    Wig,
    claims_of,
    normalized_pronto,
    row_digest,
    serialize_wig,
    signal_row_digest,
)

_LOGGER = logging.getLogger(__name__)

VARIANT_CREATE = "create"
VARIANT_UPDATE = "update"


@dataclass
class PlanRow:
    """One line of the attestation list, as the dialog will draw it."""

    #: The device command this row came from. The dialog sends TEST
    #: through this, and claims come back keyed by digest, so both ends
    #: agree on which physical command is meant.
    command_id: str
    alias: str
    digest: str
    send_count: int
    ditto_count: int
    bypass: bool
    #: Decoded protocol for the pill, or None when the row is raw only.
    protocol: str | None = None
    #: MATRIX ONLY. A checklist row addresses a CELL, not a command, so
    #: TEST sends by coordinate rather than by command id and these are
    #: what it sends. ``section`` and the coordinates also compose the
    #: row's human label ("Cool 16 (the coldest)") in the dialog.
    section: str | None = None
    mode: str | None = None
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None
    temp_less: bool = False
    temp_role: str | None = None
    #: "on" / "off" for the power rows, which have no coordinates.
    power: str | None = None
    #: UPDATE only: the wig row this matched, if any.
    wig_index: int | None = None
    #: UPDATE only: what the WIG calls this row. Differs from ``alias``
    #: exactly when the fitter renamed it locally, which is what raises
    #: the "the wig calls this On; you call it Power" line.
    wig_alias: str | None = None

    @property
    def matched(self) -> bool:
        return self.wig_index is not None

    @property
    def renamed(self) -> bool:
        return self.matched and self.wig_alias != self.alias


@dataclass
class PlanMissingRow:
    """A wig row nothing on the device covers.

    Feeds the exclusion picker. The person either says why (not on my
    device / could not make it work) or leaves it unclaimed, which is
    the honest default: silence is not a verdict.
    """

    wig_index: int
    alias: str
    digest: str


@dataclass
class SavePlan:
    variant: str
    rows: list[PlanRow] = field(default_factory=list)
    missing_rows: list[PlanMissingRow] = field(default_factory=list)
    #: UPDATE only: the closet file and identity being updated.
    source_filename: str | None = None
    source_wig_id: str | None = None
    source_wig_name: str | None = None
    #: CREATE only: the seed file this device was converted from.
    converted_from: str | None = None
    #: Metadata to prefill. On UPDATE it comes from the wig (plan
    #: Section 4: edits ride the PR as reviewed changes); on CREATE from
    #: the device.
    metadata: dict[str, Any] = field(default_factory=dict)
    skipped: int = 0
    notes: list[str] = field(default_factory=list)
    #: MATRIX ONLY: the lattice the checklist vouches for, and the
    #: units its temperatures are written in. The hash is stamped onto
    #: the bundle at save time rather than carried back from the dialog:
    #: a claim about a lattice must bind the lattice the SERVER read,
    #: not one the caller says it saw.
    cells_hash: str | None = None
    unit: str = "C"
    precision: float = 1.0
    #: How many fittings the source wig already carries. Shown so an
    #: UPDATE reads as joining a record rather than starting one -- the
    #: bench mistook two appended fittings for two lost wigs.
    existing_fittings: int = 0
    #: This device is a climate matrix. Its lattice lives in the climate
    #: entity, not in the command list, so the flat rows below are only
    #: its depth-0 extras -- attesting them would claim a fraction of
    #: the device and call it whole. The dialog says so instead.
    matrix: bool = False
    #: MATRIX UPDATE only: how the device's lattice differs from the
    #: wig's. Non-empty means the checklist cannot be attested as-is --
    #: a bundle binds cells_hash, which is a SET, so signing a diverged
    #: lattice would bind bytes the fitter never tested.
    cell_changes: list[CellChange] = field(default_factory=list)
    #: Set when the device remembers a wig the closet no longer holds.
    #: The save falls back to CREATE, and says so rather than pretending
    #: the source never existed.
    source_missing: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "rows": [
                {
                    "command_id": row.command_id,
                    "alias": row.alias,
                    "digest": row.digest,
                    "send_count": row.send_count,
                    "ditto_count": row.ditto_count,
                    "bypass": row.bypass,
                    "protocol": row.protocol,
                    "wig_index": row.wig_index,
                    "wig_alias": row.wig_alias,
                    "matched": row.matched,
                    "renamed": row.renamed,
                    "section": row.section,
                    "mode": row.mode,
                    "fan": row.fan,
                    "swing": row.swing,
                    "temp": row.temp,
                    "temp_less": row.temp_less,
                    "temp_role": row.temp_role,
                    "power": row.power,
                }
                for row in self.rows
            ],
            "missing_rows": [
                {
                    "wig_index": row.wig_index,
                    "alias": row.alias,
                    "digest": row.digest,
                }
                for row in self.missing_rows
            ],
            "source_filename": self.source_filename,
            "source_wig_id": self.source_wig_id,
            "source_wig_name": self.source_wig_name,
            "source_missing": self.source_missing,
            "converted_from": self.converted_from,
            "metadata": dict(self.metadata),
            "skipped": self.skipped,
            "notes": list(self.notes),
            "matrix": self.matrix,
            "cells_hash": self.cells_hash,
            "unit": self.unit,
            "precision": self.precision,
            "existing_fittings": self.existing_fittings,
            "cell_changes": [c.as_dict() for c in self.cell_changes],
            "lattice_diverged": bool(self.cell_changes),
        }


def _protocol_of(device: IRDevice, command_id: str) -> str | None:
    for command in device.commands:
        if command.id == command_id:
            return command.decoded_protocol
    return None


def _device_metadata(device: IRDevice, wig: Wig) -> dict[str, Any]:
    return {
        "name": wig.name,
        "brand": wig.brand or device.manufacturer or "",
        "model": wig.model or device.model or "",
        "kind": wig.kind or "",
        "notes": "",
    }


def _wig_metadata(wig: Wig) -> dict[str, Any]:
    """Prefill from the wig being updated (plan Section 4, RULED).

    An UPDATE that arrived with the device's metadata would quietly
    propose overwriting the author's brand and model with whatever the
    adopter happened to call their device -- a content change disguised
    as an attestation. Prefilling from the wig means an edit here is
    deliberate, and reads as deliberate in the PR.
    """
    identifiers = wig.identifiers or {}

    def _one(key: str) -> str:
        # An identifier may legitimately be a list (a remote with three
        # FCC IDs). The dialog holds one field per key, so show the
        # first and leave the rest alone: a prefill that flattened a
        # list into a comma string would write that string back on save.
        value = identifiers.get(key)
        if isinstance(value, list):
            return value[0] if value else ""
        return value or ""

    return {
        "name": wig.name,
        "brand": wig.brand or "",
        "model": wig.model or "",
        "kind": wig.kind or "",
        "notes": wig.notes or "",
        "fcc_id": _one("fcc_id"),
        "upc": _one("upc"),
        "asin": _one("asin"),
        "oem": _one("oem"),
    }


def _lattice(matrix: ClimateMatrix | None) -> dict[str, Any]:
    """The lattice facts every plan carries, present or absent."""
    if matrix is None:
        return {"matrix": False}
    from .wig_format import cells_content_hash

    return {
        "matrix": True,
        "cells_hash": cells_content_hash(matrix),
        "unit": matrix.unit,
        "precision": matrix.precision,
    }


def _checklist_rows(matrix: ClimateMatrix) -> list[PlanRow]:
    """The dimension checklist, as attestation rows.

    A matrix has thousands of cells and nobody presses thousands of
    buttons, so the checklist SAMPLES it: every mode, every fan speed,
    every swing, the ends of the temperature range. That sample is what
    a person can actually vouch for, and it is why a matrix bundle also
    binds ``cells_hash`` -- the claim is about the lattice these rows
    were drawn from, not only the rows themselves.

    Each row still carries a digest of its own cell's bytes, so hard
    rule 1 holds here exactly as it does on a flat wig: a claim binds
    bytes. The lattice hash is the extra promise, not the only one.
    """
    from .wig_climate import SECTION_START, SECTION_WRAP, dimension_checklist

    rows: list[PlanRow] = []
    for item in dimension_checklist(matrix):
        power = (
            item.key
            if item.section in (SECTION_START, SECTION_WRAP)
            and item.key in ("on", "off")
            else None
        )
        rows.append(PlanRow(
            # No command to send through: a cell is addressed by its
            # coordinates, and TEST routes on those instead.
            command_id="",
            alias=item.key,
            digest=row_digest(item.pronto, 0, False),
            send_count=item.send_count,
            ditto_count=0,
            bypass=False,
            protocol=_decoded_protocol(item.pronto),
            section=item.section,
            mode=item.mode,
            fan=item.fan,
            swing=item.swing,
            temp=item.temp,
            temp_less=item.temp_less,
            temp_role=item.temp_role,
            power=power,
        ))
    return rows


def _decoded_protocol(pronto: str) -> str | None:
    """The protocol name for a checklist row's pill, or None.

    Wigs carry no decoded fields by design, so the name is derived on
    read. Bounded work: the checklist is a dozen or two rows, never the
    whole lattice.
    """
    from .ir_command import ProntoCommand
    from .protocol_decode import try_decode_identity

    try:
        timings = ProntoCommand(pronto).get_raw_timings()
    except Exception:
        return None
    identity = try_decode_identity(timings)
    return identity.protocol if identity else None


def build_save_plan(
    device: IRDevice,
    source_wig: Wig | None = None,
    source_filename: str | None = None,
    matrix: ClimateMatrix | None = None,
) -> SavePlan:
    """What SAVE TO CLOSET is about to do, row by row.

    ``source_wig`` is the closet wig the device's ``source_wig_id``
    resolved to. Passing None with a device that HAS a source id means
    the file is gone -- deleted, renamed away, never downloaded on this
    install -- and the plan degrades to CREATE with ``source_missing``
    set. Refusing instead would strand a working device with no way to
    save; pretending it was always new would hide that the link broke.
    """
    is_matrix = matrix is not None
    build = build_wig_from_device(device, matrix)
    if build.wig is None:
        return SavePlan(
            variant=VARIANT_CREATE, skipped=build.skipped,
            notes=build.notes, matrix=is_matrix,
        )

    rows = [
        PlanRow(
            command_id=build.sources[i],
            alias=signal.alias,
            digest=signal_row_digest(signal),
            send_count=signal.send_count,
            ditto_count=signal.ditto_count,
            bypass=signal.bypass_protocol,
            protocol=_protocol_of(device, build.sources[i]),
        )
        for i, signal in enumerate(build.wig.signals)
    ]
    if matrix is not None:
        # The lattice first, then the depth-0 extras beside it. A
        # person reads the checklist as the device and the extras as
        # the leftovers, which is what they are.
        rows = [*_checklist_rows(matrix), *rows]

    if source_wig is None:
        return SavePlan(
            variant=VARIANT_CREATE,
            rows=rows,
            converted_from=device.source_file or None,
            metadata=_device_metadata(device, build.wig),
            skipped=build.skipped,
            notes=build.notes,
            source_missing=bool(device.source_wig_id),
            **_lattice(matrix),
        )

    match = match_device_to_wig(
        [MatchRow(signal_row_digest(s), s.alias) for s in source_wig.signals],
        [MatchRow(row.digest, row.alias) for row in rows],
    )
    for pairing in match.matched:
        row = rows[pairing.device_index]
        row.wig_index = pairing.wig_index
        row.wig_alias = source_wig.signals[pairing.wig_index].alias

    return SavePlan(
        variant=VARIANT_UPDATE,
        rows=rows,
        missing_rows=[
            PlanMissingRow(
                wig_index=i,
                alias=source_wig.signals[i].alias,
                digest=signal_row_digest(source_wig.signals[i]),
            )
            for i in match.unmatched_wig_rows
        ],
        source_filename=source_filename,
        source_wig_id=source_wig.wig_id,
        source_wig_name=source_wig.name,
        metadata=_wig_metadata(source_wig),
        skipped=build.skipped,
        notes=build.notes,
        existing_fittings=len(claims_of(source_wig)),
        cell_changes=lattice_diff(matrix, source_wig.climate),
        **_lattice(matrix),
    )



# ---------------------------------------------------------------------------
# Lattice divergence (matrix UPDATE)
# ---------------------------------------------------------------------------

CELL_CHANGED = "changed"
CELL_DELETED = "deleted"
CELL_ADDED = "added"


@dataclass
class CellChange:
    """One way the device's lattice differs from the wig's."""

    kind: str
    label: str
    mode: str | None = None
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "label": self.label, "mode": self.mode,
            "fan": self.fan, "swing": self.swing, "temp": self.temp,
        }


def _coord_key(cell: Any) -> tuple:
    """Coordinates as a comparable tuple.

    Temperature is floated rather than formatted, because a value that
    round-tripped through JSON as 24 rather than 24.0 is the same cell
    and a string key would say otherwise.
    """
    return (
        cell.mode,
        cell.fan or None,
        cell.swing or None,
        None if cell.temp is None else float(cell.temp),
    )


def _coord_label(cell: Any, siblings: list[Any]) -> str:
    """What the content-change prompt calls a cell.

    The SAME rule the porthole rows use on the device: mode and
    temperature, with fan and swing joining only when two of the cells
    on show would otherwise read alike. The person should recognize the
    prompt's "Cool 24" as the row they just repaired, so the two
    surfaces have to name a cell the same way.
    """
    base = [cell.mode.capitalize() if cell.mode else "Cell"]
    if cell.temp is not None:
        base.append(
            str(int(cell.temp))
            if float(cell.temp).is_integer() else str(cell.temp)
        )
    same = [
        c for c in siblings
        if c is not cell
        and c.mode == cell.mode
        and (c.temp is None) == (cell.temp is None)
        and (c.temp is None or abs(float(c.temp) - float(cell.temp)) < 1e-6)
    ]
    if not same:
        return " ".join(base)
    extra = [v for v in (cell.fan, cell.swing) if v]
    return " ".join([*base, *extra]) if extra else " ".join(base)


def lattice_diff(device_matrix: Any, wig_matrix: Any) -> list[CellChange]:
    """How the device's lattice differs from the wig it came from.

    Cell by cell, by COORDINATE. A repair rewrote bytes at a coordinate
    the wig also has (changed); a delete through a porthole row removed
    a coordinate the wig still carries (deleted). Additions are reported
    for completeness even though no current flow produces one.

    This is what the content-change prompt lists and what the matrix
    attestation gate reads. Order is deterministic -- the wig's own cell
    order, then any additions -- so the same divergence always reads the
    same way.
    """
    if wig_matrix is None or device_matrix is None:
        return []
    device_by_coord = {_coord_key(c): c for c in device_matrix.cells}
    wig_by_coord = {_coord_key(c): c for c in wig_matrix.cells}
    found: list[tuple[str, Any, tuple]] = []
    for coord, wig_cell in wig_by_coord.items():
        device_cell = device_by_coord.get(coord)
        if device_cell is None:
            found.append((CELL_DELETED, wig_cell, coord))
        elif normalized_pronto(device_cell.pronto) != normalized_pronto(
            wig_cell.pronto
        ):
            found.append((CELL_CHANGED, device_cell, coord))
    for coord, device_cell in device_by_coord.items():
        if coord not in wig_by_coord:
            found.append((CELL_ADDED, device_cell, coord))
    # Labels last, so collision-awareness sees only the cells actually
    # on show rather than the whole lattice.
    shown = [cell for _, cell, _ in found]
    return [
        CellChange(kind, _coord_label(cell, shown), *coord)
        for kind, cell, coord in found
    ]


@dataclass
class Attestation:
    """What the person signed, straight from the dialog.

    ``claims`` maps a row digest to its verdict. A digest ABSENT from
    the map is unclaimed, which is different from excluded: the fitter
    unchecked it and gave no reason, so no claim is made about it at
    all. That distinction is the whole reason this is a dict rather than
    a list of booleans.
    """

    claims: dict[str, str] = field(default_factory=dict)
    handle: str | None = None
    github: str | None = None
    note: str | None = None
    #: Renames the fitter chose to propose. UPDATE only.
    renames: list[RenameProposal] = field(default_factory=list)
    #: MATRIX only: the lattice the checklist vouched for.
    cells_hash: str | None = None

    def is_empty(self) -> bool:
        return not self.claims


def _now_date() -> str:
    return datetime.now(UTC).date().isoformat()


def build_bundle(
    wig_id: str,
    aliases_by_digest: dict[str, str],
    attestation: Attestation,
) -> ClaimsBundle:
    """Assemble the signed bundle from the dialog's answers.

    Rows are emitted in the order the digests were claimed, and each
    carries the alias the row had AT CLAIM TIME -- display context, not
    identity, so a later rename leaves the claim standing.

    A verdict the format does not know is dropped rather than stored. A
    bundle is signed, and signing something we cannot read back would
    put a claim in the file that no reader can act on.
    """
    rows = [
        RowClaim(
            alias_at_claim=aliases_by_digest.get(digest, ""),
            digest=digest,
            verdict=verdict,
        )
        for digest, verdict in attestation.claims.items()
        if verdict in VERDICTS
    ]
    return ClaimsBundle(
        wig_id=wig_id,
        rows=rows,
        handle=attestation.handle,
        github=attestation.github,
        date=_now_date(),
        note=attestation.note,
        cells_hash=attestation.cells_hash,
    )



def recomb(wig: Wig) -> int:
    """Re-comb an outgoing wig and stamp a fresh receipt. Returns suspects.

    Suspects are DERIVED FROM BYTES, never stored as taint, so a
    repaired wig cures itself the next time anybody combs it. The
    re-comb exists so the file describes ITSELF rather than its
    ancestor: without it, a receipt written when the wig was imported
    broken rides out on the fixed file and the next person sees doubts
    that no longer apply.

    It also cuts the other way, and that is the point of keeping the
    two independent. Attesting a row never silences the comb -- only
    changing the bytes does. The comb doubts bytes; a person vouches
    for hardware; a row can honestly carry both.
    """
    from .wig_comb import comb_wig, stamp_receipt

    report = comb_wig(wig)
    stamp_receipt(wig, report, _now_date())
    return report.suspects


def apply_lattice(wig: Wig, device_matrix: Any, changes: list) -> int:
    """Write the device's lattice into the wig. Returns cells touched.

    THE PROPOSE-CHANGE PATH for a matrix, and it is what that path
    exists for rather than an exception to hard rule 3: the person
    repaired cells on the device and explicitly asked to send the
    repair upstream. Changed cells take the device's bytes and a
    provenance marker; deleted cells leave the lattice, which stays
    legal because sparse lattices already are.

    Only the coordinates in ``changes`` move. Copying the device's
    whole lattice over the wig's would also carry differences nobody
    proposed -- a send_count tuned locally, a cell the device never had
    -- and turn a targeted repair into a wholesale overwrite.
    """
    if wig.climate is None or device_matrix is None or not changes:
        return 0
    device_by_coord = {_coord_key(c): c for c in device_matrix.cells}
    touched = 0
    drop: set[tuple] = set()
    for change in changes:
        coord = (
            change.mode,
            change.fan or None,
            change.swing or None,
            None if change.temp is None else float(change.temp),
        )
        if change.kind == CELL_DELETED:
            drop.add(coord)
            touched += 1
            continue
        source = device_by_coord.get(coord)
        if source is None:
            continue
        for cell in wig.climate.cells:
            if _coord_key(cell) == coord:
                # The bytes, and nothing else. A provenance marker used
                # to ride along here recording that this cell had been
                # replaced; it retired 2026-08-03 because nothing read
                # it. The propose-change PR diff shows the repair, and
                # the re-comb below judges the result on its bytes --
                # both of which say more than a stamp ever did.
                cell.pronto = source.pronto
                touched += 1
                break
        else:
            if change.kind == CELL_ADDED:
                wig.climate.cells.append(source)
                touched += 1
    if drop:
        wig.climate.cells = [
            c for c in wig.climate.cells if _coord_key(c) not in drop
        ]
    return touched


@dataclass
class SaveResult:
    filename: str | None = None
    wig_id: str | None = None
    signal_count: int = 0
    skipped: int = 0
    attested: int = 0
    variant: str = VARIANT_CREATE
    notes: list[str] = field(default_factory=list)
    #: Renames that matched nothing. Reported, never silent.
    stale_renames: list[str] = field(default_factory=list)
    #: What the fresh comb receipt says about the file just written.
    suspects: int = 0
    #: Lattice cells this save proposed upstream. UPDATE only.
    cells_proposed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "wig_id": self.wig_id,
            "signal_count": self.signal_count,
            "skipped": self.skipped,
            "attested": self.attested,
            "variant": self.variant,
            "notes": list(self.notes),
            "stale_renames": list(self.stale_renames),
            "suspects": self.suspects,
            "cells_proposed": self.cells_proposed,
        }


def create_text(
    build: WigBuild,
    attestation: Attestation | None = None,
    private_key_b64: str | None = None,
) -> tuple[str, SaveResult]:
    """CREATE: a new wig, optionally born with its author's claims.

    The identity is minted by serialization, so the bundle has to be
    appended AFTER the wig has one -- ``append_claims`` forces the
    bundle's ``wig_id`` to the wig's for exactly this reason.
    """
    wig = build.wig
    assert wig is not None
    from .wig_format import ensure_wig_id

    ensure_wig_id(wig)
    result = SaveResult(
        wig_id=wig.wig_id,
        signal_count=len(wig.signals),
        skipped=build.skipped,
        variant=VARIANT_CREATE,
        notes=list(build.notes),
    )
    if attestation is not None and not attestation.is_empty():
        aliases = {
            signal_row_digest(s): s.alias for s in wig.signals
        }
        bundle = build_bundle(wig.wig_id or "", aliases, attestation)
        append_claims(wig, bundle, private_key_b64)
        result.attested = len(bundle.rows)
    # A fresh receipt on the way out, so the file describes itself. A
    # new wig has no inherited receipt to go stale, but it would leave
    # the closet with NO receipt at all -- which reads as "nobody has
    # combed this", deliberately not the same as clean.
    result.suspects = recomb(wig)
    return serialize_wig(wig), result


def update_text(
    original_text: str,
    source_wig: Wig,
    attestation: Attestation | None = None,
    private_key_b64: str | None = None,
    mutate: Any | None = None,
    device_matrix: Any | None = None,
    cell_changes: list | None = None,
) -> tuple[str, SaveResult] | None:
    """UPDATE: append the bundle, touch no CONTENT (hard rule 3).

    ``attestation`` may be None: a metadata-only update is a legitimate
    content PR, not an attestation, and the plan already rules that
    metadata edits ride the PR as reviewed changes. What hard rule 3
    protects is the SIGNALS block -- the codes, their order, their
    aliases, their send counts -- so a brand correction is free to land
    while an attestation PR still reads at a glance as one person
    vouching for rows nobody rewrote.

    The aliases carried into the claims are the WIG's, not the device's.
    A claim's ``alias_at_claim`` is meant to read as "the row the wig
    called On", so a locally renamed device would otherwise write a name
    that appears nowhere in the file it is attesting.

    A rename being proposed in the SAME save is folded in first, so the
    claim records the name the file will carry. Otherwise the bundle
    would say ``On`` beside a row the same commit renames to ``Power``,
    and a later reader would conclude the rename happened after the
    claim, which is the one thing alias_at_claim exists to tell them.
    """
    renames = attestation.renames if attestation else []
    proposed = {
        (p.digest, p.alias_at_claim): p.alias for p in renames
    }
    # Keyed by digest alone, which collapses rows that share one. That
    # is right here: claims are themselves keyed by digest, so such rows
    # share a claim, and this map only supplies its display name.
    aliases = {
        signal_row_digest(s): proposed.get(
            (signal_row_digest(s), s.alias), s.alias
        )
        for s in source_wig.signals
    }
    bundle = (
        build_bundle(source_wig.wig_id or "", aliases, attestation)
        if attestation is not None
        else None
    )
    proposed = 0
    suspects = 0

    def _mutate(wig: Wig) -> None:
        nonlocal proposed, suspects
        if mutate is not None:
            mutate(wig)
        if cell_changes:
            proposed = apply_lattice(wig, device_matrix, cell_changes)
            # The repaired lattice is new bytes, so the receipt that
            # came in with the file is about a wig that no longer
            # exists. Re-combed only when content actually moved: an
            # attestation-only update rewrites nothing, so its receipt
            # is still true.
            suspects = recomb(wig)
            # Bind the lattice AS PROPOSED, not as it arrived. The
            # bundle was assembled before this ran, so the hash goes on
            # the bundle itself -- stamping the attestation here would
            # be writing to an object nothing reads again.
            if bundle is not None and wig.climate is not None:
                from .wig_format import cells_content_hash

                bundle.cells_hash = cells_content_hash(wig.climate)

    written = update_wig_with_claims(
        original_text,
        bundle,
        private_key_b64,
        renames or None,
        _mutate,
    )
    if written is None:
        return None
    text, _entry, outcome = written
    return text, SaveResult(
        suspects=suspects,
        cells_proposed=proposed,
        wig_id=source_wig.wig_id,
        signal_count=len(source_wig.signals),
        attested=len(bundle.rows) if bundle else 0,
        variant=VARIANT_UPDATE,
        stale_renames=[p.alias_at_claim for p in outcome.stale],
    )
