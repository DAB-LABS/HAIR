"""Claims on wigs: what a closet row shows, and content bookkeeping.

What is LEFT of the fitting engine after v0.9.5. The session apparatus
that used to live here -- drafts, verdict maps, session send times,
carry snapshot and re-seeding, finish and discard, the whole-wig hash
roll -- went with the dialog it served. Attestation is a signed bundle
of per-row claims now, written once at SAVE TO CLOSET (wig_save.py),
and there is nothing to keep between visits.

What survives is everything that was never about the session, plus the
two readers that replaced it:

- ``claims_summary``: the closet row's three-tier check, DERIVED from
  the claims on the file every time it is asked. Nothing is stored.
- ``claims_ledger``: the same evidence at full detail, for the ledger
  dialog. Read only, and structurally so -- the writable version of it
  went with the session.
- ``bundle_is_complete``: the one judgment both of the above ask, kept
  in one place so the check and the ledger cannot disagree.
- ``_merge_provenance`` and the provenance keys: content edits record
  where a row's bytes came from, and that is wig bookkeeping regardless
  of who is attesting what.
- ``_write_row_code``: the one writer that changes a row's bytes in a
  wig, used by the propose-change path.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .wig_format import (
    VERDICT_WORKED,
    Wig,
    cell_key,
    cells_content_hash,
    claims_of,
    coverage,
    normalized_pronto,
    perfect_by,
    wig_row_digests,
)

# Re-exported: wig_comb reads it from here, as it always has.
__all__ = [
    "FITTINGS_KEY",
    "FITTING_HEARD_WAIT_S",
    "PROVENANCE_KEY",
    "PROVENANCE_POWER_KEY",
    "bundle_is_complete",
    "claims_ledger",
    "claims_summary",
    "normalized_pronto",
]

_LOGGER = logging.getLogger(__name__)

FITTINGS_KEY = "fittings"
# Provenance rides in ``extra``, OUTSIDE every canonical form, so
# recording where a row's bytes came from can never move a wig's
# identity. That was true when a fitting bound a whole-file hash and it
# is still true now that claims bind rows.
PROVENANCE_KEY = "provenance"
PROVENANCE_POWER_KEY = "provenance_power"

# How long a send waits for its own Mirror echo before reporting that
# nothing heard it. Read by the TEST button's SENT . HEARD line.
FITTING_HEARD_WAIT_S = 2.0

def _merge_provenance(
    existing: object, incoming: dict[str, Any]
) -> dict[str, Any]:
    """Fold a new provenance claim into whatever the row already had.

    Both claims are true and they are about different things: REPLACED
    says the bytes changed and where they came from, TUNED says the
    ditto count changed. Assigning wholesale, which is what both paths
    used to do, made the second one erase the first -- so a code
    captured off a real remote and then tuned came back reporting only
    the tune, and (because the chip picks its label off ``replaced``)
    described itself as pasted (owner bench 2026-08-02).

    ``date`` is the LATEST claim's, since that is when the row was last
    touched. Nothing here is hashed: provenance rides in ``extra`` and
    the canonical form is alias, pronto, ditto_count, bypass_protocol.
    """
    merged: dict[str, Any] = {}
    if isinstance(existing, dict):
        merged.update(existing)
    merged.update(incoming)
    return merged

def _write_row_code(
    wig: Wig, key: str, pronto: str, marker: dict[str, Any] | None,
    bypass_protocol: bool | None = None,
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
            extra[PROVENANCE_KEY] = _merge_provenance(
                extra.get(PROVENANCE_KEY), marker
            )

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
                # NO bypass here, deliberately. A cell's canonical form
                # is exactly mode/fan/swing/temp/pronto, so there is
                # nowhere to put the flag and nothing downstream would
                # read it. This branch used to accept the argument and
                # drop it on the floor: REPLACE offered the toggle on a
                # matrix row, the fitter set it, and the chip came back
                # still naming the decoded protocol because nothing had
                # been written (owner bench 2026-08-02). The caller now
                # refuses instead, and the dialog does not offer it.
                _stamp(cell.extra)
                return True
        return False
    for sig in wig.signals:
        if sig.alias == key:
            sig.pronto = pronto
            # REPLACE STARTS FRESH (owner ruling 2026-08-01): the new
            # code and the decision about how to send it are written
            # together, in the one hash roll, so the row never exists in
            # a state where the bytes and that decision disagree. None
            # means "leave it", which is the discard-revert path putting
            # a code back exactly as it was.
            if bypass_protocol is not None:
                sig.bypass_protocol = bool(bypass_protocol)
            _stamp(sig.extra)
            return True
    return False

def bundle_is_complete(
    bundle: Any, wig: Wig, digests: list[str] | None = None
) -> bool:
    """Did this one bundle claim everything there was to claim?

    Lifted out of ``claims_summary`` so the closet's check and the
    ledger's per-row detail cannot drift apart. They are two renderings
    of one judgment, and a person who sees a green check beside a
    ledger row that reads "scoped" has found a bug in HAIR rather than
    a fact about their wig.

    A matrix wig's claims bind the lattice as a SET rather than a list
    of row digests, so completeness there is "they claimed the rows
    they were shown", which for a checklist bundle is every row in it.
    """
    if wig.climate is not None:
        return bool(bundle.rows) and all(
            row.verdict == VERDICT_WORKED for row in bundle.rows
        )
    if digests is None:
        digests = wig_row_digests(wig)
    return perfect_by(bundle, digests)


def claims_ledger(wig: Wig, username: str | None) -> dict[str, Any]:
    """Everything a reader can honestly say about a wig's attestations.

    READ ONLY, and structurally so. The ledger used to be a tab inside
    the fitting dialog, which meant it sat next to controls that could
    change the very rows it was reporting on -- and it grew a couple
    (jump to the first failed row) because they were cheap to add
    there. v0.9.5 makes attestation a thing you do once, at SAVE TO
    CLOSET, on the device you actually tested. So the ledger has no
    session to drive and no reason to be writable: it is a record of
    who claimed what about which rows, on what date, signed by whom.

    Everything here is DERIVED on read. Nothing in the payload is
    stored on the file except the claims themselves, so a wig whose
    codes were edited yesterday reports honestly today without anybody
    having to remember to invalidate something.
    """
    from .fitting_signing import key_fingerprint, verify_fitting

    bundles = claims_of(wig)
    digests = wig_row_digests(wig)
    live = set(digests)
    handle = (username or "").strip().lower()
    raw_entries = wig.extra.get(FITTINGS_KEY)
    raw_entries = raw_entries if isinstance(raw_entries, list) else []
    # A matrix wig has no flat row digests BY DESIGN -- its claims bind
    # the lattice as a set, and its rows are checklist coordinates. So
    # per-row presence is not a question that can be asked here, and
    # asking it anyway against an empty set answered "no" for every row:
    # a signed, current, complete Panasonic checklist reported all eight
    # of its rows as orphaned (bench 2026-08-03). ``lattice_current`` is
    # the honest answer for this shape, and it is computed below.
    per_row_presence = wig.climate is None

    entries = []
    for bundle in bundles:
        rows = [
            {
                "alias": row.alias_at_claim,
                "digest": row.digest,
                "verdict": row.verdict,
                # A claim about a row that is no longer on the wig.
                # Not an error and not a lie: somebody proved a recipe
                # that has since been edited, and saying so is more
                # use than hiding it.
                "present": row.digest in live if per_row_presence else True,
            }
            for row in bundle.rows
        ]
        raw = next(
            (
                e
                for e in raw_entries
                if isinstance(e, dict) and e.get("sig") == bundle.sig
                and bundle.sig is not None
            ),
            None,
        )
        entries.append({
            "handle": bundle.handle,
            "github": bundle.github,
            "date": bundle.date,
            "note": bundle.note,
            "signed": verify_fitting(raw) if raw is not None else None,
            "key_fingerprint": (
                key_fingerprint(bundle.key) if bundle.key else None
            ),
            "complete": bundle_is_complete(bundle, wig, digests),
            "worked": sum(1 for r in rows if r["verdict"] == VERDICT_WORKED),
            "excluded": sum(
                1 for r in rows if r["verdict"] != VERDICT_WORKED
            ),
            "orphaned": sum(1 for r in rows if not r["present"]),
            "cells_hash": bundle.cells_hash,
            # MATRIX ONLY: whether the lattice this checklist vouched
            # for is still the lattice on the file. None on a flat wig,
            # where there is no set to have moved.
            "lattice_current": (
                None
                if wig.climate is None or not bundle.cells_hash
                else bundle.cells_hash == cells_content_hash(wig.climate)
            ),
            "mine": bool(handle)
            and (bundle.handle or "").strip().lower() == handle,
            "rows": rows,
        })

    return {
        "name": wig.name,
        "wig_id": wig.wig_id,
        "matrix": wig.climate is not None,
        "total": len(digests),
        "covered": len(coverage(bundles, digests)),
        "entries": entries,
    }


def claims_summary(wig: Wig, username: str | None) -> dict[str, Any]:
    """The closet row's check, DERIVED from claims (RULED 2026-08-03).

    Three tiers, one-to-one with the download filename tiers, because a
    row and a filename saying different things about the same wig is a
    contradiction somebody has to resolve by opening it:

    - nothing: no attestations at all
    - "scoped": at least one signed attestation, none of them complete
    - "perfect": at least one person's claims cover every row

    GREEN IS KEYED TO ONE PERSON'S COMPLETE COVERAGE. Union coverage
    across fitters never inflates it: three people who each proved a
    different third have not, between them, produced anybody who can
    say the whole wig works on their hardware. That union is real and
    worth knowing, but it is shop-side judgment and tooltip material,
    not a green check.

    Says nothing about the comb. The comb's glyph is a different
    statement about different evidence -- bytes, not hardware -- and a
    wig can honestly wear a green check and a glowing comb at once.
    """
    bundles = claims_of(wig)
    digests = wig_row_digests(wig)

    def _complete(bundle: Any) -> bool:
        return bundle_is_complete(bundle, wig, digests)

    state: str | None = None
    if any(_complete(b) for b in bundles):
        state = "perfect"
    elif bundles:
        state = "scoped"

    def _mine(bundle: Any) -> bool:
        handle = (bundle.handle or "").strip().lower()
        return bool(username) and handle == (username or "").strip().lower()

    mine = [b for b in bundles if _mine(b)]
    return {
        "state": state,
        "user_state": (
            ("perfect" if any(_complete(b) for b in mine) else "scoped")
            if mine else None
        ),
        "fitters": len(bundles),
        "perfect_by": [
            b.handle for b in bundles if _complete(b) and b.handle
        ],
        "covered": len(coverage(bundles, digests)),
        "total": len(digests),
    }

def _today() -> str:
    return datetime.now(UTC).date().isoformat()
