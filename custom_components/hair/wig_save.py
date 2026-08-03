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
    RowClaim,
    Wig,
    claims_of,
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
    #: How many fittings the source wig already carries. Shown so an
    #: UPDATE reads as joining a record rather than starting one -- the
    #: bench mistook two appended fittings for two lost wigs.
    existing_fittings: int = 0
    #: This device is a climate matrix. Its lattice lives in the climate
    #: entity, not in the command list, so the flat rows below are only
    #: its depth-0 extras -- attesting them would claim a fraction of
    #: the device and call it whole. The dialog says so instead.
    matrix: bool = False
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
            "existing_fittings": self.existing_fittings,
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


def build_save_plan(
    device: IRDevice,
    source_wig: Wig | None = None,
    source_filename: str | None = None,
) -> SavePlan:
    """What SAVE TO CLOSET is about to do, row by row.

    ``source_wig`` is the closet wig the device's ``source_wig_id``
    resolved to. Passing None with a device that HAS a source id means
    the file is gone -- deleted, renamed away, never downloaded on this
    install -- and the plan degrades to CREATE with ``source_missing``
    set. Refusing instead would strand a working device with no way to
    save; pretending it was always new would hide that the link broke.
    """
    matrix = bool(getattr(device, "climate_matrix", False))
    build = build_wig_from_device(device)
    if build.wig is None:
        return SavePlan(
            variant=VARIANT_CREATE, skipped=build.skipped,
            notes=build.notes, matrix=matrix,
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

    if source_wig is None:
        return SavePlan(
            variant=VARIANT_CREATE,
            rows=rows,
            converted_from=device.source_file or None,
            metadata=_device_metadata(device, build.wig),
            skipped=build.skipped,
            notes=build.notes,
            source_missing=bool(device.source_wig_id),
            matrix=matrix,
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
        matrix=matrix,
        existing_fittings=len(claims_of(source_wig)),
    )


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
    return serialize_wig(wig), result


def update_text(
    original_text: str,
    source_wig: Wig,
    attestation: Attestation | None = None,
    private_key_b64: str | None = None,
    mutate: Any | None = None,
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
    written = update_wig_with_claims(
        original_text,
        bundle,
        private_key_b64,
        renames or None,
        mutate,
    )
    if written is None:
        return None
    text, _entry, outcome = written
    return text, SaveResult(
        wig_id=source_wig.wig_id,
        signal_count=len(source_wig.signals),
        attested=len(bundle.rows) if bundle else 0,
        variant=VARIANT_UPDATE,
        stale_renames=[p.alias_at_claim for p in outcome.stale],
    )
