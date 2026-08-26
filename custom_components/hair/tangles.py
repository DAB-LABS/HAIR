"""Tangles: the fix-flow derivation tier.

The comb says what is wrong with a wig. This module says what is wrong
with a DEVICE somebody is holding, in a shape a repair surface can act
on: one row per target that carries a finding, each with the finding's
own vote, the bytes it currently sends, and (from P2) where a correct
copy of those bytes already lives.

THE ROWS ARE DERIVED, NEVER STORED. Nothing here writes, nothing here
persists, and there is no tangle record to clean up when a device is
deleted or a repair lands. The listing is recomputed from the device's
live state on every call, which is what makes "apply a fix and watch
the row leave" true rather than bookkeeping.

WHERE THE FINDINGS COME FROM. Not from the source wig's stored receipt.
That receipt describes the file in the closet, and the moment a repair
writes a cell it describes something the device no longer is; a device
built from scratch has no receipt at all. So the device is projected
back into a wig (the shipped exporter, ``build_wig_from_device``) and
combed live. The comb is pure and cheap enough to run per call -- the
whole 82-wig closet combs in seconds -- and combing what is actually
on the device is the only reading that cannot go stale.

PORTHOLE ROWS ARE EXCLUDED FROM THE PROJECTION. ``_mint_cell_rows``
gives every comb-flagged cell a coordinate-named command so the command
toolset reaches it, which means a flagged cell appears twice in a device:
once in the lattice and once as a depth-0 command holding a copy of the
same bytes. A projection that kept both would comb the same code twice
and offer the same repair under two ids. The lattice is the authority
for a cell, so the porthole is dropped here and the cell stands for it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import UTC
from typing import Any

from . import field_readers
from .models import IRCommand, IRDevice
from .wig_comb import (
    ADVISORY_CHECKS,
    CHECK_DUPLICATED_NEIGHBOUR,
    CHECK_FIELD_MISMATCH,
    FIELD_COORDINATE,
    POWER_FIELD,
    SEVERITY_ORDER,
    Code,
    Coverage,
    Finding,
    comb_wig,
    matrix_codes,
    read_family,
)
from .wig_export import build_wig_from_device
from .wig_format import ClimateCell, ClimateMatrix, cell_key, row_digest

_LOGGER = logging.getLogger(__name__)

#: A row addressing one lattice cell, keyed by its coordinate string.
TARGET_CELL = "cell"
#: A row addressing one flat command, keyed by its command id.
TARGET_COMMAND = "command"

#: Why the field tier said nothing, when it said nothing. These ride
#: the listing so an empty field tier reads as "nobody could look"
#: rather than as a clean bill -- the same distinction the comb's own
#: coverage block exists to draw.
FIELD_TIER_UNMAPPED = "protocol-unmapped"
FIELD_TIER_NO_LATTICE = "no-lattice"
FIELD_TIER_READ = "read"


@dataclass(frozen=True)
class TangleTarget:
    """What a row is about: one lattice cell, or one flat command."""

    kind: str
    #: The comb's own key for this target -- a cell coordinate string
    #: (``heat_cool/medium/off/19``) or the command's alias. Never
    #: invented here: it is what the receipt would address.
    key: str
    command_id: str | None = None
    #: Cell coordinates, matrix targets only. The donor search and the
    #: guarded write both address a cell by these, never by its key.
    coordinates: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind, "key": self.key}
        if self.command_id is not None:
            out["command_id"] = self.command_id
        if self.coordinates is not None:
            out["coordinates"] = dict(self.coordinates)
        return out


@dataclass(frozen=True)
class TangleRow:
    """One target the comb doubts, with everything a fix needs to open.

    ``findings`` carries every finding that named this target, in the
    comb's own severity order, each with its message key and params --
    the vote, verbatim. A row that led with only its worst class would
    hide the cell that is both short AND lying, which is exactly the
    pair R2 went out of its way to keep side by side.
    """

    id: str
    target: TangleTarget
    classes: list[str]
    findings: list[dict[str, Any]]
    pronto: str
    digest: str
    has_donor: bool = False
    donor: dict[str, Any] | None = None
    #: Why the donor search came back empty, when it did. An abstention
    #: with a reason is a result; a silent None reads as "not looked at".
    donor_abstain: str | None = None
    #: What this row's CURRENT bytes read as, against its own label.
    #: The details view says "says Heat 18, will say Heat 19" from this
    #: and the candidate's verdict side by side.
    verdict: dict[str, Any] | None = None
    #: P5 fills this in: a standing attestation covering these bytes.
    attested: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target.as_dict(),
            "classes": list(self.classes),
            "findings": [dict(f) for f in self.findings],
            "pronto": self.pronto,
            "digest": self.digest,
            "has_donor": self.has_donor,
            "donor": dict(self.donor) if self.donor else None,
            "donor_abstain": self.donor_abstain,
            "verdict": self.verdict,
            "attested": dict(self.attested) if self.attested else None,
        }


@dataclass
class TangleListing:
    """Every open finding on one device, plus what was looked at."""

    rows: list[TangleRow] = field(default_factory=list)
    clusters: list[TangleCluster] = field(default_factory=list)
    #: Findings the comb files as ADVISORY -- same code under two
    #: names, and the two ditto advisories. They are not suspects and
    #: never become rows or cards, because "these two buttons share a
    #: code" is legitimate on a toggle remote. They are served beside
    #: the rows so a surface that asks a person to decide has something
    #: to show, without any of it counting as something wrong.
    advisories: list[dict[str, Any]] = field(default_factory=list)
    #: Rows a person has already answered with KEEP. Off the work list,
    #: still on the record.
    attested: list[dict[str, Any]] = field(default_factory=list)
    matrix: bool = False
    #: The comb's coverage block for this projection, verbatim.
    coverage: dict[str, Any] | None = None
    #: Which family read the lattice, when one did.
    protocol: str | None = None
    field_tier: str = FIELD_TIER_READ
    #: Candidate sources this device can offer at all. A flat device
    #: never gets donors in this release (frame-vote reconstruction is
    #: 3b), and saying so is better than an empty donor field.
    candidate_sources: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows": [row.as_dict() for row in self.rows],
            "clusters": [c.as_dict() for c in self.clusters],
            "advisories": [dict(a) for a in self.advisories],
            "attested": [dict(a) for a in self.attested],
            "matrix": self.matrix,
            "coverage": self.coverage,
            "protocol": self.protocol,
            "field_tier": self.field_tier,
            "candidate_sources": list(self.candidate_sources),
        }


def row_id(kind: str, key: str) -> str:
    """The stable reference a fix quotes back at the server."""
    return f"{kind}:{key}"


def is_porthole(command: IRCommand) -> bool:
    """A command that is a view of a lattice cell, not a code of its own."""
    return bool(getattr(command, "matrix_cell", None))


def project_device(
    device: IRDevice, matrix: ClimateMatrix | None
) -> tuple[Any, dict[str, str]]:
    """The device as a wig, plus alias -> command id for its flat rows.

    Uses the shipped exporter rather than a second serializer, so a
    tangle listing reads exactly the bytes a Save to Closet would write.
    Porthole rows are dropped first (see the module docstring).
    """
    flat = [c for c in device.commands if not is_porthole(c)]
    build = build_wig_from_device(replace(device, commands=flat), matrix)
    if build.wig is None:
        return None, {}
    sources: dict[str, str] = {}
    for signal, command_id in zip(build.wig.signals, build.sources, strict=False):
        sources.setdefault(signal.alias, command_id)
    return build.wig, sources


def _order(check: str) -> int:
    try:
        return SEVERITY_ORDER.index(check)
    except ValueError:
        return len(SEVERITY_ORDER)


def _findings_by_key(report: Any) -> dict[str, list[Finding]]:
    """Group non-advisory findings by every key they name, worst first.

    A relationship finding (duplicated neighbours, duplicate labels)
    names its whole group, and every member of that group has something
    to answer for, so it lands on each of their rows.
    """
    grouped: dict[str, list[Finding]] = {}
    for finding in report.findings:
        if finding.check in ADVISORY_CHECKS:
            continue
        for key in finding.keys:
            grouped.setdefault(key, []).append(finding)
    for entries in grouped.values():
        entries.sort(key=lambda f: _order(f.check))
    return grouped


def _cell_digest(pronto: str) -> str:
    """A cell's current-bytes digest.

    Cells carry no dittos and are never pinned to raw (plan 5.5), so
    the recipe is the bytes alone -- but it is still built through
    ``row_digest`` so a cell digest and a signal digest are the same
    kind of thing and can never drift apart.
    """
    return row_digest(pronto, 0, False)


def list_tangles(
    device: IRDevice, matrix: ClimateMatrix | None
) -> TangleListing:
    """Every open finding on this device, derived from its live state."""
    wig, sources = project_device(device, matrix)
    listing = TangleListing(matrix=matrix is not None)
    if wig is None:
        return listing

    report = comb_wig(wig)
    grouped = _findings_by_key(report)
    coverage = report.coverage.to_dict() if report.coverage else None
    listing.coverage = coverage
    protocol = None
    if coverage and isinstance(coverage.get("protocol"), dict):
        protocol = coverage["protocol"].get("id")
    listing.protocol = protocol

    if matrix is None:
        listing.field_tier = FIELD_TIER_NO_LATTICE
        listing.candidate_sources = ["capture", "paste"]
    elif protocol is None:
        listing.field_tier = FIELD_TIER_UNMAPPED
        listing.candidate_sources = ["capture", "paste"]
    else:
        listing.candidate_sources = ["donor", "capture", "paste"]

    rows: list[TangleRow] = []
    lattice = read_lattice(matrix, wig)
    listing.advisories = [
        finding.to_dict() for finding in report.findings
        if finding.check in ADVISORY_CHECKS
    ]
    if matrix is not None:
        portholes = {
            _coord_key(command.matrix_cell): command.id
            for command in device.commands
            if is_porthole(command)
        }
        for cell in matrix.cells:
            key = cell_key(cell)
            findings = grouped.pop(key, None)
            if not findings:
                continue
            coordinates = {
                "mode": cell.mode, "fan": cell.fan,
                "swing": cell.swing, "temp": cell.temp,
            }
            payload = [f.to_dict() for f in findings]
            donor, abstain = find_donor(lattice, key, payload)
            rows.append(TangleRow(
                id=row_id(TARGET_CELL, key),
                target=TangleTarget(
                    kind=TARGET_CELL, key=key,
                    command_id=portholes.get(_coord_key(coordinates)),
                    coordinates=coordinates,
                ),
                classes=[f.check for f in findings],
                findings=payload,
                pronto=cell.pronto,
                digest=_cell_digest(cell.pronto),
                has_donor=donor is not None,
                donor=donor,
                donor_abstain=abstain,
                verdict=pre_read(
                    lattice, cell.pronto, coordinates
                ).as_dict(),
            ))
        for key in ("off", "on"):
            findings = grouped.pop(key, None)
            pronto = matrix.off if key == "off" else matrix.on
            if not findings or pronto is None:
                continue
            rows.append(TangleRow(
                id=row_id(TARGET_CELL, key),
                target=TangleTarget(
                    kind=TARGET_CELL, key=key,
                    coordinates={"power": key},
                ),
                classes=[f.check for f in findings],
                findings=[f.to_dict() for f in findings],
                pronto=pronto,
                digest=_cell_digest(pronto),
            ))

    by_id = {command.id: command for command in device.commands}
    for signal in wig.signals:
        findings = grouped.pop(signal.alias, None)
        if not findings:
            continue
        command_id = sources.get(signal.alias)
        command = by_id.get(command_id or "")
        rows.append(TangleRow(
            id=row_id(TARGET_COMMAND, command_id or signal.alias),
            target=TangleTarget(
                kind=TARGET_COMMAND, key=signal.alias,
                command_id=command_id,
            ),
            classes=[f.check for f in findings],
            findings=[f.to_dict() for f in findings],
            pronto=signal.pronto,
            digest=row_digest(
                signal.pronto,
                signal.ditto_count,
                signal.bypass_protocol,
            ),
            verdict=pre_read(lattice, signal.pronto).as_dict(),
        ))
        if command is None:
            _LOGGER.debug(
                "Tangle row for %r has no command on device %s",
                signal.alias, device.id,
            )

    # An attested row has been ANSWERED: somebody looked at it, tested
    # it on their own hardware and vouched for it. It leaves the work
    # list and is reported separately, because a card offering to repair
    # something a person already settled is the surface nagging.
    #
    # The finding itself is untouched. Keep never deletes a finding, and
    # the receipt still carries it -- attested is a different thing from
    # clean and has to read as one.
    answered = []
    open_rows = []
    for row in rows:
        record = standing_attestation(device, row, lattice)
        if record is None:
            open_rows.append(row)
            continue
        answered.append(replace(row, attested=record))
    listing.rows = open_rows
    listing.attested = [row.as_dict() for row in answered]
    listing.clusters = cluster_rows(open_rows, lattice)
    return listing


# ---------------------------------------------------------------------------
# P2: the donor search
# ---------------------------------------------------------------------------

#: No cell anywhere in this lattice reads as the value this one claims.
#: The honest end of the search, and a loud one: the abstention is what
#: sends a card to the witnessed-capture road instead of inventing bytes.
ABSTAIN_NO_READING = "no-cell-reads-this"
#: The field the cell disagrees on is not one this map vouches for, so
#: there is nothing to search against.
ABSTAIN_NOT_RATIFIED = "field-not-ratified"
#: Nothing read the lattice at all.
ABSTAIN_UNREADABLE = "unreadable"
#: The finding is not a field mismatch, so a donor is the wrong idea:
#: a damaged capture is not repaired by another cell's bytes.
ABSTAIN_NOT_A_FIELD = "not-a-field-finding"


@dataclass
class LatticeReading:
    """Every cell of one lattice, read once, with its map.

    Built ONCE per listing and never re-read mid-run. A donor is chosen
    against the lattice as it stands before any write; re-reading after
    each write would let a repair chase its own tail through a column
    that is one long shift.
    """

    field_map: Any = None
    readings: dict[str, Any] = field(default_factory=dict)
    cells: dict[str, ClimateCell] = field(default_factory=dict)

    @property
    def readable(self) -> bool:
        return self.field_map is not None

    def spec_for(self, field_name: str) -> Any:
        if self.field_map is None:
            return None
        return self.field_map.field_named(field_name)

    def reads(self, key: str, spec: Any) -> int | None:
        reading = self.readings.get(key)
        if reading is None or spec is None:
            return None
        return field_readers.read_field(reading, spec)


def read_lattice(
    matrix: ClimateMatrix | None, wig: Any = None
) -> LatticeReading:
    """Decode a device's codes once, under one family vote.

    A flat device is read too, and by the same vote. R2's rule five
    stands -- integrity rules need no labels, so a flat wig whose codes
    identify under a map gets them -- and the vote is what keeps a
    single coincidental match from naming a family for a remote that
    has nothing to do with it. Only the label comparison is
    matrix-only, because a flat row carries a name, not a coordinate.
    """
    if matrix is not None:
        codes = matrix_codes(matrix)
        cells = {cell_key(cell): cell for cell in matrix.cells}
    elif wig is not None and wig.signals:
        codes = [
            Code(key=signal.alias, pronto=signal.pronto)
            for signal in wig.signals
        ]
        cells = {}
    else:
        return LatticeReading()
    field_map, readings = read_family(codes, Coverage())
    return LatticeReading(
        field_map=field_map, readings=readings, cells=cells,
    )


def _mismatched_fields(findings: list[dict[str, Any]]) -> list[str]:
    """Which field names a row's field-mismatch findings name.

    The comb writes the field as a locale key so the diagnosis renders
    in the reader's language; the name is the tail of it.
    """
    names = []
    for finding in findings:
        if finding.get("check") != CHECK_FIELD_MISMATCH:
            continue
        raw = str(finding.get("params", {}).get("field", ""))
        name = raw.rsplit(".", 1)[-1]
        if name and name not in names:
            names.append(name)
    return names


def _coordinate_of(cell: ClimateCell, field_name: str) -> Any:
    if field_name == POWER_FIELD:
        return "on"
    axis = FIELD_COORDINATE.get(field_name)
    return None if axis is None else getattr(cell, axis, None)


def _elsewhere(cell: ClimateCell, exclude: set[str]) -> tuple:
    """The cell's coordinates on every axis the search is NOT varying.

    A donor has to be the same cell in every respect except the thing
    that is wrong with the target. Without this the search would happily
    offer a cooling frame to repair a heating one, because the only
    field it can compare is the one they agree on.
    """
    axes = [
        axis for name, axis in FIELD_COORDINATE.items()
        if name not in exclude
    ]
    return tuple(getattr(cell, axis, None) for axis in sorted(axes))


def find_donor(
    lattice: LatticeReading,
    key: str,
    findings: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    """A cell whose READ is what this cell's LABEL claims, or a reason.

    Never constructs and never guesses. The search is a lookup over
    codes that already exist in this lattice: if one of them already
    sends what this cell is supposed to send, that frame is the repair.
    If none does, the search says so and stops -- which is the whole
    reason the witnessed-capture road exists.
    """
    if not lattice.readable:
        return None, ABSTAIN_UNREADABLE
    target = lattice.cells.get(key)
    if target is None:
        return None, ABSTAIN_UNREADABLE
    fields = _mismatched_fields(findings)
    if not fields:
        return None, ABSTAIN_NOT_A_FIELD

    wanted: dict[str, int] = {}
    for name in fields:
        spec = lattice.spec_for(name)
        if spec is None or not spec.ratified:
            return None, ABSTAIN_NOT_RATIFIED
        expected = field_readers.expected_value(
            spec, _coordinate_of(target, name)
        )
        if expected is None:
            return None, ABSTAIN_NOT_RATIFIED
        wanted[name] = expected

    varying = set(fields)
    anchor = _elsewhere(target, varying)
    for candidate_key, candidate in lattice.cells.items():
        if candidate_key == key:
            continue
        if _elsewhere(candidate, varying) != anchor:
            continue
        if any(
            lattice.reads(candidate_key, lattice.spec_for(name)) != value
            for name, value in wanted.items()
        ):
            continue
        return {
            "key": candidate_key,
            "coordinates": {
                "mode": candidate.mode, "fan": candidate.fan,
                "swing": candidate.swing, "temp": candidate.temp,
            },
            "pronto": candidate.pronto,
            "digest": _cell_digest(candidate.pronto),
            # STRUCTURED, not a sentence. This branch writes no
            # user-facing text; the surface renders "the frame at
            # heat_cool/medium/21 reads as 22" from these three facts.
            "reasoning": {
                "fields": list(fields),
                "labelled": {
                    name: _coordinate_of(candidate, name) for name in fields
                },
                "reads_as": {
                    name: _coordinate_of(target, name) for name in fields
                },
            },
        }, None
    return None, ABSTAIN_NO_READING


# ---------------------------------------------------------------------------
# P3: reading a candidate before anything is written
# ---------------------------------------------------------------------------


@dataclass
class CandidateVerdict:
    """What a candidate turns out to be, read against a target's label.

    Pure. Nothing here sends, saves or decides -- it is the sentence a
    surface shows before a person commits, and the same sentence the
    guarded write records when they commit anyway.
    """

    #: Field name -> the label these bytes read as, in the wig's own
    #: words. This is what "reads as: Heat / Fan High / 19" is built
    #: from; a byte value is not something to show anybody.
    reads_as: dict[str, Any] = field(default_factory=dict)
    #: Field name -> the label the target CLAIMS.
    claims: dict[str, Any] = field(default_factory=dict)
    #: The same two, unrendered, for the record.
    raw_read: dict[str, int] = field(default_factory=dict)
    raw_expected: dict[str, int] = field(default_factory=dict)
    #: Fields where the two disagree. Empty is a match.
    mismatches: list[str] = field(default_factory=list)
    #: None when there is no label to compare against (a flat command,
    #: an unmapped lattice). NOT the same as False.
    matches: bool | None = None
    protocol: str | None = None
    declined: str | None = None
    #: Rule type -> True, False, or None for a rule that could not be
    #: evaluated. A rule that cannot be evaluated is never a pass.
    integrity: dict[str, bool | None] = field(default_factory=dict)
    #: R1's frame check on the candidate itself, when it disagrees.
    frame_vote: dict[str, Any] | None = None
    #: Decoded identity, where a TX decoder recognises the capture. The
    #: only read-back a flat command has.
    decoded: dict[str, Any] | None = None

    @property
    def readable(self) -> bool:
        return self.protocol is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "reads_as": dict(self.reads_as),
            "claims": dict(self.claims),
            "raw_read": dict(self.raw_read),
            "raw_expected": dict(self.raw_expected),
            "mismatches": list(self.mismatches),
            "matches": self.matches,
            "protocol": self.protocol,
            "declined": self.declined,
            "integrity": dict(self.integrity),
            "frame_vote": self.frame_vote,
            "decoded": dict(self.decoded) if self.decoded else None,
        }


def _frame_vote(pronto: str) -> dict[str, Any] | None:
    """R1's own check, on the candidate itself.

    A capture whose repeats disagree is a bad capture whatever it reads
    as, and saying so while the remote is still in somebody's hand is
    the whole point of the check.
    """
    from .wig_comb import frame_disagreement

    vote = frame_disagreement(pronto)
    return None if vote is None else vote.as_dict()


def _decoded_identity(pronto: str) -> dict[str, Any] | None:
    from .ir_command import ProntoCommand
    from .protocol_decode import try_decode_identity

    try:
        timings = ProntoCommand(pronto).get_raw_timings()
    except Exception:
        return None
    identity = try_decode_identity(timings)
    if identity is None:
        return None
    return {
        "protocol": identity.protocol,
        "address": identity.address,
        "command": identity.command,
        "fingerprint": identity.fingerprint,
    }


def pre_read(
    lattice: LatticeReading,
    pronto: str,
    coordinates: dict[str, Any] | None = None,
) -> CandidateVerdict:
    """Read a candidate's fields and compare them to a target's label.

    ``coordinates`` is the cell this candidate is proposed FOR. Without
    them (a flat command, or a listen that is not yet aimed anywhere)
    the read still happens and still reports what the bytes say -- there
    is simply no claim to check it against, and ``matches`` stays None
    rather than becoming a False nobody can justify.
    """
    verdict = CandidateVerdict(
        frame_vote=_frame_vote(pronto),
        decoded=_decoded_identity(pronto),
    )
    if not lattice.readable:
        verdict.declined = field_readers.NO_MAP
        return verdict

    field_map = lattice.field_map
    reading = field_readers.read_code(
        pronto, [field_map], prefer=field_map.protocol_id
    )
    if not reading.identified:
        verdict.declined = reading.declined or field_readers.NO_MAP
        return verdict
    verdict.protocol = reading.protocol_id

    for rule in field_map.integrity:
        if not rule.ratified:
            continue
        verdict.integrity[rule.type] = field_readers.check_integrity(
            reading, rule
        )

    comparable = []
    for spec in field_map.fields:
        if not spec.ratified:
            continue
        value = field_readers.read_field(reading, spec)
        if value is None:
            continue
        verdict.raw_read[spec.name] = value
        domain = _axis_domain(lattice, spec.name)
        label = _label_for(spec, domain, value)
        if label is not None:
            verdict.reads_as[spec.name] = label
        if coordinates is None:
            continue
        axis = FIELD_COORDINATE.get(spec.name)
        claimed = (
            coordinates.get(POWER_FIELD, "on") if spec.name == POWER_FIELD
            else (None if axis is None else coordinates.get(axis))
        )
        if claimed is None:
            continue
        expected = field_readers.expected_value(spec, claimed)
        if expected is None:
            continue
        verdict.claims[spec.name] = claimed
        verdict.raw_expected[spec.name] = expected
        comparable.append(spec.name)
        if expected != value:
            verdict.mismatches.append(spec.name)
    if comparable:
        verdict.matches = not verdict.mismatches
    return verdict


# ---------------------------------------------------------------------------
# P4: the one door through the no-cell-editing wall
# ---------------------------------------------------------------------------

#: Where a repair's record lives, on the cell or on the command. Inside
#: the object's own extras, so it rides the matrix file and the exported
#: wig by the unknown-keys contract without a format change.
PROVENANCE_KEY = "hair_repair"

#: The write is honest about how much of it was proven on air.
TIER_AIR_TESTED = "air-tested"
TIER_RULE_DERIVED = "rule-derived"

APPLY_NO_FINDING = "no_finding"
APPLY_NOT_TESTED = "not_tested"
APPLY_BAD_CANDIDATE = "bad_candidate"
APPLY_DISAGREEMENT_UNDECLARED = "reading_disagreed_required"
APPLY_NOTHING_TO_REVERT = "nothing_to_revert"


def _now() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat(timespec="seconds")


def build_provenance(
    *,
    source: str,
    prior_pronto: str,
    lattice: LatticeReading,
    row: TangleRow,
    tested: bool,
    tier: str = TIER_AIR_TESTED,
    run: str | None = None,
    tested_keys: list[str] | None = None,
    detail: dict[str, Any] | None = None,
    disagreed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The record a repair leaves behind, and the undo it leaves with it.

    ``prior`` is the whole point: one step back lives in the record
    rather than in a history, so a revert needs nothing but the thing it
    is reverting.

    ``tested`` is RECORDED, never verified. The server cannot see
    somebody's air conditioner respond and must not pretend to; what it
    can do is write down that the assertion was made, and let the
    receipt carry it where anybody can read it.
    """
    record: dict[str, Any] = {
        "origin": "fix",
        "source": source,
        "applied": _now(),
        "tested": bool(tested),
        "tier": tier,
        "prior": {
            "pronto": prior_pronto,
            "digest": _cell_digest(prior_pronto),
        },
        "finding": {
            "key": row.target.key,
            "classes": list(row.classes),
        },
    }
    if lattice.readable:
        record["map"] = {
            "id": lattice.field_map.protocol_id,
            "version": lattice.field_map.version,
        }
    if run is not None:
        record["run"] = run
    if tested_keys:
        record["tested_cells"] = list(tested_keys)
    if detail:
        record["detail"] = dict(detail)
    if disagreed is not None:
        # The escalation ladder's third rung. A consistent mismatch is
        # evidence about OUR READING, not about the person pressing the
        # button -- a remote sends what its display shows. So the write
        # is allowed, and what it records is that a human overrode a
        # reading and exactly what the reading said. Repeated
        # same-family off-by-ones are how a field gets re-ratified, and
        # they can only accumulate if they are written down.
        record["reading_disagreed"] = {
            "user_attested": True,
            "reads_as": dict(disagreed.get("reads_as") or {}),
            "claims": dict(disagreed.get("claims") or {}),
            "mismatches": list(disagreed.get("mismatches") or []),
        }
    return record


def repair_extras(holder: Any) -> dict[str, Any]:
    """The unknown-keys bag a repair record lives in.

    A cell and a command keep theirs under different names, and asking
    with ``or`` rather than by type is how a cell with an EMPTY extras
    dict falls through to the attribute it does not have.
    """
    if isinstance(holder, IRCommand):
        return holder._extra
    return holder.extra


def repair_bytes(holder: Any) -> str:
    """Whatever this holder currently transmits."""
    return holder.code if isinstance(holder, IRCommand) else holder.pronto


def restore_holder(
    holder: Any, pronto: str, extras: dict[str, Any]
) -> None:
    """Put a holder back exactly as it was, bytes and record together."""
    if isinstance(holder, IRCommand):
        holder.code = pronto
    else:
        holder.pronto = pronto
    bag = repair_extras(holder)
    bag.clear()
    bag.update(extras)


_extras_of = repair_extras


def write_repair(
    holder: Any, pronto: str, provenance: dict[str, Any]
) -> None:
    """Put the bytes in and the record beside them."""
    if isinstance(holder, IRCommand):
        holder.code = pronto
        holder.protocol = "PRONTO"
        # The repaired bytes ARE the code. A stale raw_timings beside
        # them would win at transmit on the raw path and quietly undo
        # the repair.
        holder.raw_timings = None
    else:
        holder.pronto = pronto
    _extras_of(holder)[PROVENANCE_KEY] = provenance


def read_repair(holder: Any) -> dict[str, Any] | None:
    record = _extras_of(holder).get(PROVENANCE_KEY)
    return record if isinstance(record, dict) else None


def revert_repair(holder: Any) -> dict[str, Any] | None:
    """One step back, then forget it happened.

    Not a history. The record carries the bytes that were there before
    this repair and nothing older, so reverting twice is not a thing
    that can happen and does not need a guard that pretends otherwise.
    """
    record = read_repair(holder)
    if record is None:
        return None
    prior = (record.get("prior") or {}).get("pronto")
    if not isinstance(prior, str) or not prior:
        return None
    if isinstance(holder, IRCommand):
        holder.code = prior
        holder.protocol = "PRONTO"
        holder.raw_timings = None
    else:
        holder.pronto = prior
    _extras_of(holder).pop(PROVENANCE_KEY, None)
    return record


def portholes_for(device: IRDevice, coordinates: dict[str, Any]) -> list:
    """Every porthole command standing for one lattice cell.

    A repair has to reach these too. The porthole holds a COPY of the
    cell's bytes taken at adopt, and it is what TEST sends and what the
    command editor shows, so leaving it behind would give somebody a
    button that still transmits the code they just repaired.
    """
    anchor = _coord_key(coordinates)
    return [
        command for command in device.commands
        if is_porthole(command) and _coord_key(command.matrix_cell) == anchor
    ]


# ---------------------------------------------------------------------------
# P5: the KEEP outcome
# ---------------------------------------------------------------------------

KEEP_NO_FINDING = "no_finding"
KEEP_NOT_TESTED = "not_tested"

#: Where a carried attestation waits between the exporter and the comb
#: receipt it belongs in. Removed as soon as the receipt is stamped.
ATTESTED_PENDING = "comb_attested_pending"
#: The block inside the receipt.
ATTESTED_KEY = "attested"


def attestation_key(
    target_key: str, digest: str, map_version: str | None
) -> str:
    """What an attestation is ABOUT, expressed so it can expire itself.

    The bytes and the map that doubted them. Change either and this key
    stops matching, the attestation stops applying, and the finding is
    open again -- which is the whole expiry mechanism. Nothing is
    scheduled, nothing is swept, and there is no state that can be
    wrong: an attestation that does not apply simply does not match.
    """
    return f"{target_key}|{digest}|{map_version or '-'}"


def build_attestation(
    row: TangleRow, lattice: LatticeReading, *, note: str | None = None
) -> dict[str, Any]:
    """A person's answer to a finding: looked at it, it works, keep it."""
    version = lattice.field_map.version if lattice.readable else None
    record: dict[str, Any] = {
        "key": attestation_key(row.target.key, row.digest, version),
        "target": row.target.key,
        "kind": row.target.kind,
        "digest": row.digest,
        "classes": list(row.classes),
        "tested": True,
        "attested": _now(),
    }
    if lattice.readable:
        record["map"] = {
            "id": lattice.field_map.protocol_id, "version": version,
        }
    if note:
        record["note"] = note
    return record


def standing_attestation(
    device: IRDevice, row: TangleRow, lattice: LatticeReading
) -> dict[str, Any] | None:
    """The attestation covering this row's CURRENT bytes, if any."""
    version = lattice.field_map.version if lattice.readable else None
    wanted = attestation_key(row.target.key, row.digest, version)
    for record in device.tangle_attestations:
        if record.get("key") == wanted:
            return record
    return None


def carry_attestations(wig: Any, device: IRDevice) -> None:
    """Park the device's attestations where the re-comb will find them.

    A wig leaving for the closet gets a fresh receipt, and the receipt
    is where an attestation belongs: the file then carries both the
    math and the human's answer, and the shop's own re-derive sees
    both. Parked rather than stamped because the receipt does not exist
    yet at export time -- ``recomb`` writes it, and folds this in.
    """
    if device.tangle_attestations:
        wig.extra[ATTESTED_PENDING] = [
            dict(record) for record in device.tangle_attestations
        ]


# ---------------------------------------------------------------------------
# P8: one cause, one run
# ---------------------------------------------------------------------------

BATCH_EMPTY = "nothing_to_apply"
BATCH_SAMPLE_SHORT = "sample_incomplete"
BATCH_NO_CANDIDATE = "no_candidate"

#: How many cells a run proves on air before writing the rest. Two,
#: chosen to span the card's modes -- the same philosophy as a dimension
#: check, which attests axes rather than walking 600 cells.
DEFAULT_SAMPLE = 2


def choose_sample(
    rows: dict[str, TangleRow], members: list[str], size: int = DEFAULT_SAMPLE
) -> list[str]:
    """Which members of a card get pressed at, in a stable order.

    Modes first: a card that spans heating and cooling proves one of
    each before it writes either, because a rule that holds in one mode
    is exactly the kind of thing that does not hold in the other. Once
    every mode is represented the remaining picks spread across the
    card, and a single-member card tests that member.

    Deterministic, so the sample a person was asked to press is the
    sample the write then records.
    """
    ordered = sorted(m for m in members if m in rows)
    if not ordered:
        return []
    by_mode: dict[Any, list[str]] = {}
    for member in ordered:
        mode = (rows[member].target.coordinates or {}).get("mode")
        by_mode.setdefault(mode, []).append(member)

    picked: list[str] = [group[0] for group in by_mode.values()]
    if len(picked) < size:
        spare = [m for m in ordered if m not in picked]
        # From the far end first, so a shifted column is proved at both
        # ends rather than twice at the same corner.
        while spare and len(picked) < size:
            picked.append(spare.pop(-1))
    return sorted(picked[:max(1, size)] if len(picked) > size else picked)


def sample_covers_modes(
    rows: dict[str, TangleRow], members: list[str], tested: list[str]
) -> bool:
    """Every mode this card touches was proved on air by something."""
    def _modes(ids: list[str]) -> set:
        return {
            (rows[i].target.coordinates or {}).get("mode")
            for i in ids if i in rows
        }

    return _modes(members) <= _modes(tested)


@dataclass
class BatchPlan:
    """What one run is about to do, before anybody presses anything."""

    cluster: str
    candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    sample: list[str] = field(default_factory=list)
    declined: dict[str, str] = field(default_factory=dict)
    refused: str | None = None
    witness: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "cluster": self.cluster,
            "candidates": {k: dict(v) for k, v in self.candidates.items()},
            "sample": list(self.sample),
            "declined": dict(self.declined),
            "refused": self.refused,
            "witness": dict(self.witness) if self.witness else None,
        }


def plan_batch(
    listing: TangleListing,
    lattice: LatticeReading,
    cluster_id: str,
    *,
    witness: str | None = None,
    witness_target: str | None = None,
    supplied: dict[str, str] | None = None,
    sample_size: int = DEFAULT_SAMPLE,
) -> BatchPlan:
    """Resolve every member's candidate, then choose what to prove.

    THE WHOLE CARD IS RESOLVED BEFORE ANYTHING IS WRITTEN. On a shifted
    column the correct bytes for one cell are the bytes the cell below
    it is carrying right now, so resolving as you write would walk the
    shift down the column and hand back codes it had just replaced.
    """
    rows = {row.id: row for row in listing.rows}
    cluster = next(
        (c for c in listing.clusters if c.id == cluster_id), None)
    if cluster is None:
        return BatchPlan(cluster=cluster_id, refused=BATCH_EMPTY)
    plan = BatchPlan(cluster=cluster_id)
    members = [m for m in cluster.members if m in rows]

    if witness is not None:
        result = synthesize(
            lattice, [rows[m] for m in members], witness,
            cluster.field or "temperature", witness_target=witness_target,
        )
        if result.refused:
            plan.refused = result.refused
            return plan
        plan.witness = result.witness
        plan.declined.update(result.declined)
        for member, candidate in result.candidates.items():
            plan.candidates[member] = candidate
    for member in members:
        if member in plan.candidates:
            continue
        pronto = (supplied or {}).get(member)
        source = ORIGIN_PASTE
        detail: dict[str, Any] = {}
        if pronto is None and rows[member].has_donor:
            pronto = rows[member].donor["pronto"]
            source = ORIGIN_DONOR
            detail = {"donor": rows[member].donor["key"]}
        if pronto is None:
            plan.declined[member] = BATCH_NO_CANDIDATE
            continue
        plan.candidates[member] = {
            "pronto": pronto,
            "digest": _cell_digest(pronto),
            "origin": source,
            "verdict": pre_read(
                lattice, pronto, rows[member].target.coordinates
            ).as_dict(),
            **detail,
        }
    if not plan.candidates:
        plan.refused = BATCH_EMPTY
        return plan
    plan.sample = choose_sample(
        rows, list(plan.candidates), size=sample_size)
    return plan


# ---------------------------------------------------------------------------
# P7: witnessed-field synthesis
# ---------------------------------------------------------------------------

#: The map does not vouch for the field being rewritten.
SYNTH_FIELD_PROVISIONAL = "field-not-ratified"
#: The map declares an integrity rule it does not vouch for, so a
#: recomputed frame could not be trusted even if the field could.
SYNTH_RULE_PROVISIONAL = "integrity-rule-not-ratified"
#: The capture does not read as the value the cluster needs. Nothing is
#: witnessed, so nothing is synthesized.
SYNTH_NO_WITNESS = "capture-does-not-read-as-needed"
#: This cell has no healthy relative to build from.
SYNTH_NO_SIBLING = "no-healthy-sibling"
#: Nothing read the lattice, or the sibling's own bytes will not parse.
SYNTH_UNREADABLE = "unreadable"

#: Where a candidate came from, recorded in provenance and never
#: guessed at afterwards.
ORIGIN_DONOR = "donor"
ORIGIN_SYNTHESIZED = "synthesized"
ORIGIN_CAPTURE = "capture"
ORIGIN_PASTE = "paste"


class SynthesisBug(RuntimeError):
    """A synthesized candidate did not read back as its own cell.

    Raised, never returned. Every candidate this module builds is
    checked against the same reader that judged the cell in the first
    place, and a candidate that fails that check is a defect in the
    synthesis, not a result to hand somebody.
    """


@dataclass
class Synthesis:
    """What one witnessed value could and could not build."""

    candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    declined: dict[str, str] = field(default_factory=dict)
    #: Set when the whole run is refused before any cell is attempted.
    refused: str | None = None
    witness: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidates": {k: dict(v) for k, v in self.candidates.items()},
            "declined": dict(self.declined),
            "refused": self.refused,
            "witness": dict(self.witness) if self.witness else None,
        }


def _pronto_words(pronto: str) -> list[int] | None:
    try:
        words = [int(token, 16) for token in pronto.split()]
    except ValueError:
        return None
    return words if len(words) >= 6 and words[1] > 0 else None


def _words_to_pronto(words: list[int]) -> str:
    return " ".join(f"{word:04X}" for word in words)


def _carrier_index(field_map: Any, pair: int) -> int:
    """Which word of a pulse pair carries the bit, per the map."""
    return 5 + 2 * pair if field_map.timing.classify == "space" \
        else 4 + 2 * pair


def _byte_bits(value: int, bit_order: str) -> list[int]:
    """One byte as eight bits in TRANSMISSION order.

    The exact inverse of ``bits_to_bytes``'s packing, so a byte written
    here reads back as the byte that was written.
    """
    if bit_order == "lsb_first":
        return [(value >> index) & 1 for index in range(8)]
    return [(value >> (7 - index)) & 1 for index in range(8)]


def _exemplars(
    field_map: Any, words: list[int], frames: list[list[int]],
    positions: list[list[int]],
) -> dict[int, int]:
    """This code's OWN pulse widths for a zero and for a one.

    Synthesis rewrites bits inside a real capture rather than rendering
    a fresh waveform from the map's nominal windows, so the bits it
    changes have to look like the bits it did not: same device, same
    receiver, same jitter. The exemplar is the code's own median for
    that bit value.

    A code with no bit of one value falls back to the map's stated
    window, because a value that never occurs has no exemplar to copy.
    """
    seen: dict[int, list[int]] = {0: [], 1: []}
    for frame, place in zip(frames, positions, strict=True):
        for bit, pair in zip(frame, place, strict=True):
            index = _carrier_index(field_map, pair)
            if index < len(words):
                seen[bit].append(words[index])
    out: dict[int, int] = {}
    for bit, window in ((0, field_map.timing.zero), (1, field_map.timing.one)):
        values = sorted(seen[bit])
        if values:
            out[bit] = values[len(values) // 2]
        else:
            nominal = window.nominal or (window.minimum + window.maximum) / 2
            out[bit] = max(1, round(nominal / 0.241246 / words[1]))
    return out


def _repair_integrity(
    field_map: Any, frames: list[list[int]]
) -> list[list[int]]:
    """Recompute every ratified rule the map declares, in place.

    The arithmetic mirrors ``field_readers.check_integrity`` rather than
    importing it, because that function ASKS and this one ANSWERS. The
    coupling is pinned instead of assumed: a test recomputes and then
    puts the result back through ``check_integrity``, so the day the two
    drift, the suite says so.
    """
    out = [list(frame) for frame in frames]
    for rule in field_map.integrity:
        if not rule.ratified:
            continue
        params = rule.params
        index = int(params.get("frame", 0) or 0)
        if index >= len(out):
            continue
        frame = out[index]
        if rule.type == "complement_pairs":
            pairs = params.get("pairs")
            if not pairs:
                start = int(params.get("start", 0) or 0)
                count = int(params.get("count", 0) or 0)
                pairs = [
                    [start + 2 * i, start + 2 * i + 1] for i in range(count)
                ]
            for low, high in pairs:
                if max(low, high) < len(frame):
                    frame[high] = (~frame[low]) & 0xFF
        elif rule.type in ("checksum_sum", "nibble_sum"):
            target = params.get("target_byte")
            if not isinstance(target, int) or target >= len(frame):
                continue
            if rule.type == "checksum_sum":
                span = params.get("range")
                if not isinstance(span, list | tuple) or len(span) != 2:
                    continue
                first, last = int(span[0]), int(span[1])
                if last >= len(frame):
                    continue
                modulus = int(params.get("mod", 256) or 256)
                total = (
                    sum(frame[first:last + 1])
                    + int(params.get("offset", 0) or 0)
                ) % modulus % 256
            else:
                nibbles = params.get("nibbles")
                if not isinstance(nibbles, list):
                    continue
                total = 0
                broken = False
                for entry in nibbles:
                    if not isinstance(entry, list | tuple) or len(entry) != 2:
                        broken = True
                        break
                    byte_index, half = int(entry[0]), str(entry[1])
                    if byte_index >= len(frame):
                        broken = True
                        break
                    byte = frame[byte_index]
                    total += (byte >> 4) if half in ("high", "hi") \
                        else (byte & 0x0F)
                if broken:
                    continue
                modulus = int(params.get("mod", 16) or 16)
                total = (total + int(params.get("offset", 0) or 0)) % modulus
            bits = params.get("bits")
            if bits is None:
                frame[target] = total & 0xFF
            else:
                try:
                    mask, shift = field_readers.bit_selector(str(bits))
                except ValueError:
                    continue
                frame[target] = (frame[target] & ~mask & 0xFF) | (
                    (total << shift) & mask)
        elif rule.type == "frame_repeat":
            other = int(params.get("equals", 0) or 0)
            if other < len(out):
                out[index] = list(out[other])
    return out


def rewrite_field(
    field_map: Any, pronto: str, spec: Any, value: int
) -> str | None:
    """One field rewritten inside a real capture's own timings.

    NOT a rendering. The pulses this does not change are the bytes that
    arrived from the device, untouched down to the Pronto word, and the
    ones it does change take their width from this same code's own
    median zero and one. That is what keeps a synthesized frame a
    member of the family it came from rather than an idealised drawing
    of one.

    Returns None when the capture will not parse under the map.
    """
    words = _pronto_words(pronto)
    if words is None:
        return None
    timings = field_readers.pronto_microseconds(pronto)
    if timings is None:
        return None
    frames, positions, unreadable = field_readers.read_frames_positioned(
        field_map.timing, timings
    )
    if unreadable or spec.frame >= len(frames):
        return None
    try:
        mask, shift = field_readers.bit_selector(spec.bits)
    except ValueError:
        return None

    before = [
        list(field_readers.bits_to_bytes(frame, field_map.bit_order))
        for frame in frames
    ]
    after = [list(frame) for frame in before]
    if spec.byte >= len(after[spec.frame]):
        return None
    current = after[spec.frame][spec.byte]
    after[spec.frame][spec.byte] = (current & ~mask & 0xFF) | (
        (value << shift) & mask)
    after = _repair_integrity(field_map, after)

    exemplar = _exemplars(field_map, words, frames, positions)
    for frame_index, (old_bytes, new_bytes) in enumerate(
            zip(before, after, strict=False)):
        place = positions[frame_index]
        for byte_index, (old, new) in enumerate(
                zip(old_bytes, new_bytes, strict=False)):
            if old == new:
                continue
            old_bits = _byte_bits(old, field_map.bit_order)
            new_bits = _byte_bits(new, field_map.bit_order)
            for offset in range(8):
                if old_bits[offset] == new_bits[offset]:
                    continue
                bit_index = byte_index * 8 + offset
                if bit_index >= len(place):
                    return None
                word = _carrier_index(field_map, place[bit_index])
                if word >= len(words):
                    return None
                words[word] = exemplar[new_bits[offset]]
    return _words_to_pronto(words)


def _healthy_siblings(
    lattice: LatticeReading, target: ClimateCell, field_name: str
) -> list[ClimateCell]:
    """Cells identical to the target except on the rewritten axis, whose
    own bytes agree with their own label.

    A sibling that is itself lying would carry its lie into every cell
    built from it, so the check is not "same coordinates" but "same
    coordinates AND telling the truth".
    """
    axis = FIELD_COORDINATE.get(field_name)
    if axis is None:
        return []
    anchor = _elsewhere(target, {field_name})
    out = []
    for key, candidate in lattice.cells.items():
        if candidate is target or _elsewhere(candidate, {field_name}) != anchor:
            continue
        healthy = True
        for spec in lattice.field_map.fields:
            if not spec.ratified:
                continue
            claimed = _coordinate_of(candidate, spec.name)
            if claimed is None:
                continue
            expected = field_readers.expected_value(spec, claimed)
            read = lattice.reads(key, spec)
            if expected is None or read is None:
                continue
            if expected != read:
                healthy = False
                break
        if healthy:
            out.append(candidate)
    # Nearest on the rewritten axis first, then by key, so the choice is
    # deterministic and a card built twice is built the same way.
    target_value = _coordinate_of(target, field_name)

    def _distance(cell: ClimateCell) -> tuple:
        value = _coordinate_of(cell, field_name)
        if isinstance(value, int | float) and isinstance(
                target_value, int | float):
            return (abs(float(value) - float(target_value)), cell_key(cell))
        return (0.0, cell_key(cell))

    return sorted(out, key=_distance)


def synthesize(
    lattice: LatticeReading,
    rows: list[TangleRow],
    witness_pronto: str,
    field_name: str,
    witness_target: str | None = None,
) -> Synthesis:
    """Build candidates for a cluster from ONE witnessed value.

    The witness is a capture from the user's own hardware that reads as
    the value the cluster needs. That press is what makes this legal:
    the map could compute the same byte on its own, and deliberately is
    not allowed to. A value nobody demonstrated is a value nobody
    checked, and unreadable-never-guessed does not bend because the
    arithmetic happens to be easy.

    Each remaining cell is then built from its OWN healthy sibling --
    same mode, fan and swing, a different value of the rewritten field
    -- with only that field changed and the map's ratified rules
    recomputed over the result.

    ``witness_target`` is the row the capture was AIMED at, and only
    that row receives the captured bytes verbatim. Matching on the
    witnessed value alone is not enough and the first build got it
    wrong: four cells needing 19 differ by swing, ZHLT01 marks swing
    provisional, and handing all four the same frame produced four
    candidates that passed their own read-back while three of them
    carried the wrong swing. The read-back can only check what the map
    ratifies, so the rule is structural instead -- every cell nobody
    aimed at is built from its own sibling, which is right on every
    axis by construction.
    """
    result = Synthesis()
    if not lattice.readable:
        result.refused = SYNTH_UNREADABLE
        return result
    field_map = lattice.field_map
    spec = lattice.spec_for(field_name)
    if spec is None or not spec.ratified:
        result.refused = SYNTH_FIELD_PROVISIONAL
        return result
    if any(not rule.ratified for rule in field_map.integrity):
        # A frame carries its own proof. If the map will not vouch for
        # the rule that proves it, a recomputed frame is a guess wearing
        # a checksum, and the Galanz class stays untouchable.
        result.refused = SYNTH_RULE_PROVISIONAL
        return result

    reading = field_readers.read_code(
        witness_pronto, [field_map], prefer=field_map.protocol_id
    )
    if not reading.identified:
        result.refused = SYNTH_NO_WITNESS
        return result
    witnessed = field_readers.read_field(reading, spec)
    if witnessed is None:
        result.refused = SYNTH_NO_WITNESS
        return result

    needed = {
        field_readers.expected_value(
            spec, _coordinate_of(lattice.cells[row.target.key], field_name)
        )
        for row in rows
        if row.target.key in lattice.cells
    }
    if witnessed not in needed:
        result.refused = SYNTH_NO_WITNESS
        return result

    witness_digest = _cell_digest(witness_pronto)
    result.witness = {
        "digest": witness_digest,
        "field": field_name,
        "value": witnessed,
        "reads_as": _label_for(
            spec, _axis_domain(lattice, field_name), witnessed),
    }

    for row in rows:
        cell = lattice.cells.get(row.target.key)
        if cell is None:
            result.declined[row.id] = SYNTH_UNREADABLE
            continue
        wanted = field_readers.expected_value(
            spec, _coordinate_of(cell, field_name))
        if wanted is None:
            result.declined[row.id] = SYNTH_FIELD_PROVISIONAL
            continue

        if witness_target is not None and row.id == witness_target:
            # The press was aimed here. The capture IS the candidate: a
            # frame the user actually produced beats one derived from a
            # sibling, and their aim is the attestation for the axes
            # this map does not ratify and cannot check.
            built = witness_pronto
            origin = ORIGIN_CAPTURE
            sibling_key = None
        else:
            siblings = _healthy_siblings(lattice, cell, field_name)
            if not siblings:
                result.declined[row.id] = SYNTH_NO_SIBLING
                continue
            sibling = siblings[0]  # sorted; nearest on the rewritten axis
            sibling_key = cell_key(sibling)
            built = rewrite_field(field_map, sibling.pronto, spec, wanted)
            origin = ORIGIN_SYNTHESIZED
            if built is None:
                result.declined[row.id] = SYNTH_UNREADABLE
                continue

        verdict = pre_read(lattice, built, row.target.coordinates)
        if verdict.matches is not True:
            raise SynthesisBug(
                f"synthesized candidate for {row.target.key} reads as "
                f"{verdict.reads_as} against {verdict.claims}"
            )
        result.candidates[row.id] = {
            "pronto": built,
            "digest": _cell_digest(built),
            "origin": origin,
            "witness_digest": witness_digest,
            "witness_field": field_name,
            "sibling": sibling_key,
            "verdict": verdict.as_dict(),
        }
    return result


# ---------------------------------------------------------------------------
# P6: causes, not findings
# ---------------------------------------------------------------------------

#: The same field wrong by the same STEP across many cells. A shifted
#: column is one mistake, not one mistake per cell, and this is the rule
#: that says so.
CLUSTER_SHIFT = "same-shift"
#: The same field reading the same wrong value, where the step between
#: label and reading cannot be expressed (a non-numeric axis, or a
#: reading whose label this lattice does not contain).
CLUSTER_READING = "same-reading"
#: Codes that are byte-identical where the lattice says they should
#: differ. The copy-paste class.
CLUSTER_IDENTICAL = "identical-bytes"
#: Same class, same field, nothing else in common.
CLUSTER_FIELD = "same-field"
#: Whatever refuses to cluster. Never invented structure.
CLUSTER_SINGLETON = "singleton"

_CLUSTER_ORDER = (
    CLUSTER_SHIFT,
    CLUSTER_READING,
    CLUSTER_IDENTICAL,
    CLUSTER_FIELD,
    CLUSTER_SINGLETON,
)

#: Every member already has a correct copy of its bytes elsewhere in
#: the lattice: the card can offer a repair outright.
MECHANIC_DONOR = "donor"
#: No donor, but the field is one the map vouches for, so one capture
#: that reads as the missing value can seed the rest (P7).
MECHANIC_WITNESS = "witness"
#: Nothing can be derived. Press the button again, or paste.
MECHANIC_RECAPTURE = "recapture"


@dataclass(frozen=True)
class TangleCluster:
    """One CAUSE, and the one action that answers it.

    Two axes decide a card. The cause says why these targets are wrong
    together; the mechanic says what can be done about them. They are
    both needed because a single cause can straddle two roads -- the
    Komeco column is one shift, but the cells at the bottom of its range
    have nothing to copy from and have to be witnessed instead, and a
    card has one primary action or it is not a card.
    """

    id: str
    rule: str
    #: The cause this card belongs to. Cards that share it are the same
    #: mistake reached by different roads.
    cause: str
    mechanic: str
    #: The finding class every member leads with.
    check: str
    field: str | None
    members: list[str]
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.members)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule": self.rule,
            "cause": self.cause,
            "mechanic": self.mechanic,
            "check": self.check,
            "field": self.field,
            "members": list(self.members),
            "size": self.size,
            "detail": dict(self.detail),
        }


def _axis_domain(lattice: LatticeReading, field_name: str) -> list[Any]:
    """Every value this lattice actually uses on one field's axis.

    The domain comes from the wig, never from the map's vocabulary: a
    label this file does not contain is not a label this file can be
    said to read as.
    """
    if field_name == POWER_FIELD:
        # Power has no lattice axis -- it is the difference between the
        # cells and the off code -- so its domain is stated rather than
        # gathered, and the read-back can name it like any other field.
        return ["on", "off"]
    axis = FIELD_COORDINATE.get(field_name)
    if axis is None:
        return []
    seen = []
    for cell in lattice.cells.values():
        value = getattr(cell, axis, None)
        if value is not None and value not in seen:
            seen.append(value)
    return sorted(seen, key=lambda v: (isinstance(v, str), v))


def _ring_domain(lattice: LatticeReading, field_name: str) -> list[Any]:
    """The domain a step is counted around: one label per byte value.

    ``_axis_domain`` answers "what values does this file use", which is
    the right question for reading a byte back as a label. It is the
    wrong one for measuring a shift, because a lattice can carry two
    labels that encode to the SAME byte -- the Komeco file has both 16
    and 32, and ZHLT01's special case sends them identically. Counting
    positions around a domain with a duplicate in it puts the wrap one
    step out and splits one cause into two.

    So the ring keeps the first label that claims each byte and drops
    the rest. What is left is the field's own cycle.
    """
    spec = lattice.spec_for(field_name)
    if spec is None:
        return []
    seen: set[int] = set()
    domain: list[Any] = []
    for label in _axis_domain(lattice, field_name):
        value = field_readers.expected_value(spec, label)
        if value is None or value in seen:
            continue
        seen.add(value)
        domain.append(label)
    return domain


def _ring_step(domain: list[Any], claimed: Any, actual: Any) -> int | None:
    """How far a reading sits from its label, in positions on the ring.

    Counted the shorter way around, because a field is a fixed number of
    bits and its top wraps to its bottom: a column that sends one step
    high sends 20 for 19 AND 16 for 31, and those are the same mistake
    arriving at the end of the domain.

    This is not a tidier way to say it. Split into two causes, the cells
    at the top of the range draw their donor from a cell the other cause
    owns -- and whichever runs first destroys the only copy of the bytes
    the other needed, or leaves a byte-identical twin at the seam that
    reclassifies the cell out of its own card. The chain is one cause
    and has to be repaired in one run.

    The shorter way around also keeps a genuine long shift honest: a
    reading seven positions down stays -7 rather than folding into +9.
    """
    if claimed is None or actual is None:
        return None
    try:
        here, there = domain.index(claimed), domain.index(actual)
    except ValueError:
        return None
    size = len(domain)
    if size < 2:
        return None
    step = (there - here) % size
    return step - size if step > size // 2 else step


def _label_for(spec: Any, domain: list[Any], value: int) -> Any:
    """Which label encodes to this byte, or None.

    The inverse of ``expected_value``, done by asking the map to encode
    each label this lattice uses and seeing which one lands. No
    arithmetic is inverted, so an encoding as awkward as ZHLT01's
    reversed nibble costs nothing.
    """
    for label in domain:
        if field_readers.expected_value(spec, label) == value:
            return label
    return None


def _donor_debts(
    rows: dict[str, TangleRow], clusters: list[TangleCluster]
) -> dict[str, set[str]]:
    """Which cards hand donors to which other cards.

    Cards are not always independent, and the Komeco lattice shows why.
    The cells at the TOP of its range draw their donor from the cell one
    step below them -- which belongs to the big card. Apply the big card
    first and that donor is overwritten, destroying the only copy of the
    bytes the top cells needed; the top card then has nothing to copy
    from and degrades to asking for a press.

    Nothing is corrupted either way, which is why this is an ordering
    and not a guard. But a card that quietly turns into a chore because
    of the order somebody happened to click in is a bad surprise, and
    the dependency is knowable, so it is written down.
    """
    owner = {}
    for cluster in clusters:
        for member in cluster.members:
            owner[member] = cluster.id
    key_to_row = {
        rows[m].target.key: m for m in rows
    }
    debts: dict[str, set[str]] = {c.id: set() for c in clusters}
    for cluster in clusters:
        for member in cluster.members:
            donor = rows[member].donor if member in rows else None
            if not donor:
                continue
            supplier = owner.get(key_to_row.get(donor["key"], ""))
            if supplier is not None and supplier != cluster.id:
                debts[supplier].add(cluster.id)
    return debts


def _cause_of(
    row: TangleRow, lattice: LatticeReading
) -> tuple[str, tuple, str | None, dict[str, Any]]:
    """The rule that claims this row, its cause key, field and detail.

    Rules are tried in the brief's order and the row's LEADING class
    decides which are eligible: a cell that is both a duplicate and a
    mismatch is a duplicate first, because that is the finding the comb
    ranks higher and the one whose repair is different in kind.
    """
    leading = row.classes[0] if row.classes else CLUSTER_SINGLETON

    # A row that is BOTH a twin and a lie is a lie first, even though
    # the comb ranks the twin higher. The severity order is about which
    # finding a person should read first, and it is right; this is about
    # which finding is the CAUSE, and a duplicate whose own bytes also
    # disagree with its own label is a symptom of that disagreement.
    #
    # It is what a half-repaired shift looks like from the inside. Copy
    # a donor into a cell and it matches the still-broken neighbour it
    # copied from until that neighbour is repaired too, so ranking the
    # twin first would pull cells out of the very card that is about to
    # fix them. The same rule makes a four-cell copy-paste drift land as
    # one card rather than as three plus a pair.
    if CHECK_FIELD_MISMATCH in row.classes:
        leading = CHECK_FIELD_MISMATCH

    if leading == CHECK_FIELD_MISMATCH:
        fields = _mismatched_fields(row.findings)
        name = fields[0] if fields else None
        # The FIELD-MISMATCH finding's params, not the row's first: a
        # row that is also a twin leads with the twin, whose params say
        # which neighbour it matches rather than what it reads as.
        params = next(
            (dict(f.get("params") or {}) for f in row.findings
             if f.get("check") == CHECK_FIELD_MISMATCH),
            {},
        )
        expected, read = params.get("expected"), params.get("read")
        spec = lattice.spec_for(name) if name else None
        if spec is not None and expected is not None and read is not None:
            domain = _axis_domain(lattice, name)
            claimed = _label_for(spec, domain, int(str(expected), 16))
            actual = _label_for(spec, domain, int(str(read), 16))
            step = _ring_step(
                _ring_domain(lattice, name), claimed, actual)
            if step is not None:
                return CLUSTER_SHIFT, (CLUSTER_SHIFT, name, step), name, {
                    "field": name, "step": step,
                }
            if claimed is not None and actual is not None:
                return CLUSTER_READING, (
                    CLUSTER_READING, name, str(claimed), str(actual),
                ), name, {"field": name, "claimed": claimed,
                          "reads_as": actual}
        if name is not None and expected is not None and read is not None:
            return CLUSTER_READING, (
                CLUSTER_READING, name, str(expected), str(read),
            ), name, {"field": name, "expected": expected, "read": read}
        if name is not None:
            return CLUSTER_FIELD, (CLUSTER_FIELD, name), name, {
                "field": name}

    if leading == CHECK_DUPLICATED_NEIGHBOUR:
        return CLUSTER_IDENTICAL, (
            CLUSTER_IDENTICAL, row.digest,
        ), None, {"digest": row.digest}

    return CLUSTER_SINGLETON, (
        CLUSTER_SINGLETON, row.id,
    ), None, {}


def _mechanic(row: TangleRow, lattice: LatticeReading) -> str:
    if row.has_donor:
        return MECHANIC_DONOR
    if (
        row.target.kind == TARGET_CELL
        and row.donor_abstain == ABSTAIN_NO_READING
        and lattice.readable
    ):
        # The search reached the end of a readable lattice on a field
        # the map vouches for and found nothing. That is exactly the
        # case a witnessed capture answers.
        return MECHANIC_WITNESS
    return MECHANIC_RECAPTURE


def _best_mechanic(found: list[str]) -> str:
    """The strongest road any member of a card can take."""
    for mechanic in (MECHANIC_DONOR, MECHANIC_WITNESS, MECHANIC_RECAPTURE):
        if mechanic in found:
            return mechanic
    return MECHANIC_RECAPTURE


def cluster_rows(
    rows: list[TangleRow], lattice: LatticeReading
) -> list[TangleCluster]:
    """Group a listing's rows into causes, deterministically.

    Pure, and stable for unchanged inputs: every id is built from the
    cause itself rather than from a counter, so the same lattice yields
    the same cards in the same order on any install and after any
    restart.
    """
    buckets: dict[tuple, list[TangleRow]] = {}
    meta: dict[tuple, tuple[str, str | None, dict[str, Any]]] = {}
    mechanics: dict[tuple, list[str]] = {}
    for row in rows:
        rule, cause, field_name, detail = _cause_of(row, lattice)
        mechanic = _mechanic(row, lattice)
        # A cause whose repair is per-target splits by road, because a
        # card has ONE primary action: the Komeco column is one shift,
        # but its bottom four have nothing to copy from and have to be
        # witnessed instead. A byte-identical group does NOT split --
        # its whole point is to list every location that carries the
        # same code, and the answer is about the group, not the member.
        key = cause if rule == CLUSTER_IDENTICAL else (*cause, mechanic)
        buckets.setdefault(key, []).append(row)
        meta.setdefault(key, (rule, field_name, detail))
        mechanics.setdefault(key, []).append(mechanic)

    clusters: list[TangleCluster] = []
    for key, members in buckets.items():
        rule, field_name, detail = meta[key]
        mechanic = _best_mechanic(mechanics[key])
        spans = {
            axis: sorted({
                str((row.target.coordinates or {}).get(axis))
                for row in members
                if (row.target.coordinates or {}).get(axis) is not None
            })
            for axis in ("mode", "fan", "swing")
        }
        clusters.append(TangleCluster(
            id=":".join(str(part) for part in key),
            rule=rule,
            cause=":".join(str(part) for part in key[:-1]),
            mechanic=mechanic,
            check=members[0].classes[0] if members[0].classes else "",
            field=field_name,
            members=[row.id for row in members],
            detail={**detail, "spans": {k: v for k, v in spans.items() if v}},
        ))
    debts = _donor_debts({row.id: row for row in rows}, clusters)
    for cluster in clusters:
        if debts.get(cluster.id):
            # Worked top down, this card would take the donors another
            # card is waiting on, so it sorts after the cards it feeds.
            cluster.detail["feeds"] = sorted(debts[cluster.id])
    clusters.sort(key=lambda c: (
        len(debts.get(c.id, ())),
        _CLUSTER_ORDER.index(c.rule) if c.rule in _CLUSTER_ORDER
        else len(_CLUSTER_ORDER),
        -c.size,
        c.id,
    ))
    return clusters


def _coord_key(coordinates: Any) -> tuple:
    """A hashable coordinate tuple, tolerant of a porthole's dict."""
    if not isinstance(coordinates, dict):
        return ()
    temp = coordinates.get("temp")
    return (
        coordinates.get("mode"),
        coordinates.get("fan"),
        coordinates.get("swing"),
        None if temp is None else float(temp),
    )
