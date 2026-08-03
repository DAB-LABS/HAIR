"""Claims on wigs: what a closet row shows, and content bookkeeping.

What is LEFT of the fitting engine after v0.9.5. The session apparatus
that used to live here -- drafts, verdict maps, session send times,
carry snapshot and re-seeding, finish and discard, the whole-wig hash
roll -- went with the dialog it served. Attestation is a signed bundle
of per-row claims now, written once at SAVE TO CLOSET (wig_save.py),
and there is nothing to keep between visits.

What is left is three readers and two constants:

- ``claims_summary``: the closet row's three-tier check, DERIVED from
  the claims on the file every time it is asked. Nothing is stored.
- ``claims_ledger``: the same evidence at full detail, for the ledger
  dialog. Read only, and structurally so -- the writable version of it
  went with the session.
- ``bundle_is_complete``: the one judgment both of the above ask, kept
  in one place so the check and the ledger cannot disagree.

The provenance machinery went too (RULED 2026-08-03). ``captured`` /
``pasted`` / ``tuned`` markers recorded how a row's bytes got there, and
for a while that mattered: a marker implied a hash roll, which was how a
Changed Codes row could count toward completeness. Per-row digests carry
that binding directly now, the device is the only place codes change
hands, and nothing in the UI had rendered a marker since the fitting
dialog's chips went. Unrendered freight is not bookkeeping, so
``_merge_provenance``, ``_write_row_code`` (which had no callers left at
all) and both provenance keys are gone. Markers already sitting in wig
files are inert ``extra`` data: unread, unmigrated, and outside every
canonical form, so they cannot move a wig's identity.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .wig_format import (
    VERDICT_WORKED,
    Wig,
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
    "bundle_is_complete",
    "claims_ledger",
    "claims_summary",
    "normalized_pronto",
]

_LOGGER = logging.getLogger(__name__)

FITTINGS_KEY = "fittings"

# How long a send waits for its own Mirror echo before reporting that
# nothing heard it. Read by the TEST button's SENT . HEARD line.
FITTING_HEARD_WAIT_S = 2.0

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
