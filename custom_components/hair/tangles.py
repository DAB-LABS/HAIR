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
from typing import Any

from . import field_readers
from .models import IRCommand, IRDevice
from .wig_comb import (
    ADVISORY_CHECKS,
    CHECK_FIELD_MISMATCH,
    FIELD_COORDINATE,
    POWER_FIELD,
    SEVERITY_ORDER,
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
            "attested": dict(self.attested) if self.attested else None,
        }


@dataclass
class TangleListing:
    """Every open finding on one device, plus what was looked at."""

    rows: list[TangleRow] = field(default_factory=list)
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
    if matrix is not None:
        lattice = read_lattice(matrix)
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
        ))
        if command is None:
            _LOGGER.debug(
                "Tangle row for %r has no command on device %s",
                signal.alias, device.id,
            )

    listing.rows = rows
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


def read_lattice(matrix: ClimateMatrix | None) -> LatticeReading:
    """Decode every cell of a lattice once, under one family vote."""
    if matrix is None:
        return LatticeReading()
    codes = matrix_codes(matrix)
    field_map, readings = read_family(codes, Coverage())
    return LatticeReading(
        field_map=field_map,
        readings=readings,
        cells={cell_key(cell): cell for cell in matrix.cells},
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
