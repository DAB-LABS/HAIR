"""Writing claims onto wigs: the CREATE and UPDATE export paths.

Two verbs, chosen by whether the device remembers a wig it came from.

**CREATE** mints a new wig from a device: a fresh identity, the
device's stated send counts, dittos and raw pins, provenance if it
grew from a converted seed, and optionally the author's first claims
bundle.

**UPDATE** appends a claims bundle to a wig that already exists and
**touches nothing else** (brief hard rule 3). Not the signals, not
their order, not their aliases, not their send counts. An attestation
PR should be readable at a glance as "one person vouched for these
rows" -- if updating also rewrote content, every attestation would
arrive looking like a content change and a maintainer would have to
diff it to find out. The round-trip test in test_wig_claims pins this:
adopt, then update, and the signals block comes back byte-identical.

The one deliberate exception is a rename the fitter explicitly asked
to propose, which writes the alias and nothing else. Names live
outside every digest, so writing one orphans no claims -- which is
what makes "suggest the rename" a plain PR rather than new machinery.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .fitting_signing import sign_fitting
from .wig_format import (
    ClaimsBundle,
    Wig,
    claims_bundle_out,
    ensure_wig_id,
    serialize_wig,
    signal_row_digest,
)

_LOGGER = logging.getLogger(__name__)

FITTINGS_KEY = "fittings"


@dataclass
class RenameOutcome:
    """What a batch of rename proposals actually did.

    ``stale`` is the interesting field. A proposal that matches nothing
    -- because the wig moved on since the dialog opened -- writes
    nothing, which is correct, but reporting it as plain success would
    be a silent success-shaped nothing. The save result carries these
    back so the fitter learns their rename did not land instead of
    assuming it did.
    """

    applied: int = 0
    #: Matched a row that already had that name. Harmless, not stale.
    unchanged: list[RenameProposal] = field(default_factory=list)
    #: Matched no row at all. The wig is not what the dialog showed.
    stale: list[RenameProposal] = field(default_factory=list)


@dataclass
class RenameProposal:
    """One "the wig calls this X, I call it Y" suggestion.

    Carries the SAME row identity a RowClaim does -- the current alias
    and the row digest together -- because either one alone is
    ambiguous, in opposite directions (see apply_rename_suggestions).
    """

    digest: str
    #: What the wig calls the row NOW. Half the key, not decoration.
    alias_at_claim: str
    #: What to call it instead.
    alias: str


def sign_claims_bundle(
    bundle: ClaimsBundle, private_key_b64: str | None
) -> dict[str, Any]:
    """Serialize a bundle and sign it, returning the entry to store.

    An unsigned bundle is still recorded. A signing failure must never
    lose somebody's attestation -- it only costs them the ability to
    prove it was theirs, which is a smaller loss than the claims
    themselves, and the reader already treats a missing signature as
    "unattributed" rather than "invalid".
    """
    entry = claims_bundle_out(bundle)
    if private_key_b64:
        sign_fitting(entry, private_key_b64)
    return entry


def append_claims(
    wig: Wig, bundle: ClaimsBundle, private_key_b64: str | None = None
) -> dict[str, Any]:
    """Append one signed claims bundle. Content is not touched.

    The bundle's ``wig_id`` is forced to the wig's own, because a claim
    that names a different wig is not a claim about this one -- and the
    two can legitimately differ when a device is saved as new after
    being adopted from something else.
    """
    ensure_wig_id(wig)
    bundle.wig_id = wig.wig_id or bundle.wig_id
    entry = sign_claims_bundle(bundle, private_key_b64)
    existing = wig.extra.get(FITTINGS_KEY)
    wig.extra[FITTINGS_KEY] = [
        *(existing if isinstance(existing, list) else []),
        entry,
    ]
    return entry


def apply_rename_suggestions(
    wig: Wig, proposals: list[RenameProposal]
) -> RenameOutcome:
    """Write proposed aliases. Reports what landed and what did not.

    THE SUGGESTION IS THE APPLIED RENAME (design ruling): names sit
    outside every digest, so writing one into the file orphans nothing
    and the shop PR shows ``alias: On -> Power`` for a maintainer to
    adjudicate like any other prose change. No separate suggestion
    channel, no new machinery.

    KEYED BY THE PAIR of digest AND current alias (amended 2026-08-02),
    because each alone is ambiguous in a different direction and both
    directions are real:

    - **Name alone** breaks when two rows share a name. Renaming one
      would move both.
    - **Digest alone** breaks when two rows share a payload under
      different labels -- and that is not a hypothetical. Distinct
      names over one identical code is the SmartIR defect class this
      whole repair pipeline was built for; the comb carries an advisory
      for it. Those wigs are exactly the converted ones people fit
      first, so digest-sharing rows are common precisely where this
      code runs most.

    The pair is unambiguous in both directions. It is also the identity
    ``RowClaim`` already uses -- alias_at_claim plus digest -- so a
    rename proposal and a claim point at a row the same way.

    A row that is a true duplicate of another in BOTH fields is
    indistinguishable by construction; there is no way to target one,
    so both move. That is the honest behaviour rather than a silent
    pick of the first.
    """
    outcome = RenameOutcome()
    if not proposals:
        return outcome
    by_key: dict[tuple[str, str], list[RenameProposal]] = {}
    for proposal in proposals:
        by_key.setdefault(
            (proposal.digest, proposal.alias_at_claim), []
        ).append(proposal)

    landed: set[int] = set()
    for signal in wig.signals:
        key = (signal_row_digest(signal), signal.alias)
        for i, proposal in enumerate(by_key.get(key, [])):
            landed.add(id(proposal))
            if proposal.alias != signal.alias:
                signal.alias = proposal.alias
                outcome.applied += 1
            elif i == 0:
                outcome.unchanged.append(proposal)
            break

    outcome.stale = [p for p in proposals if id(p) not in landed]
    return outcome


def signals_block(text: str) -> str:
    """The serialized ``signals`` array, for round-trip comparison.

    Used by the guarantee test rather than by product code: the point
    of hard rule 3 is that this substring is identical before and after
    an UPDATE.
    """
    start = text.find('"signals"')
    if start == -1:
        return ""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def update_wig_with_claims(
    original_text: str,
    bundle: ClaimsBundle,
    private_key_b64: str | None = None,
    renames: list[RenameProposal] | None = None,
) -> tuple[str, dict[str, Any], RenameOutcome] | None:
    """Append claims to an existing wig's text.

    Returns ``(text, entry, rename_outcome)``.

    Parses, appends, reserializes. None when the text will not parse.

    Reserialization is safe for hard rule 3 precisely because the wig
    on disk was itself written by this serializer, so the signals block
    round-trips unchanged. A wig hand-edited into a different shape
    would come back normalized -- correct, but worth knowing.
    """
    from .wig_format import parse_wig

    result = parse_wig(original_text)
    if not result.ok or result.wig is None:
        return None
    wig = result.wig
    outcome = (
        apply_rename_suggestions(wig, renames)
        if renames
        else RenameOutcome()
    )
    entry = append_claims(wig, bundle, private_key_b64)
    # The outcome rides back so the save result can report a rename
    # that did not land. A stale proposal writing nothing is correct;
    # reporting it as plain success would not be.
    return serialize_wig(wig), entry, outcome


# ---------------------------------------------------------------------------
# Matching a device's commands to a wig's rows (UPDATE)
# ---------------------------------------------------------------------------


@dataclass
class MatchRow:
    """One side of the match: a row identified the way claims are."""

    digest: str
    alias: str


@dataclass
class RowMatch:
    """A device command paired to a wig row."""

    device_index: int
    wig_index: int
    digest: str
    #: True when the PAIR matched -- same bytes AND same name. False
    #: when only the digest did, which is the legitimate rename case
    #: and what raises the "the wig calls this On; you call it Power"
    #: line in the dialog.
    exact: bool


@dataclass
class MatchResult:
    matched: list[RowMatch] = field(default_factory=list)
    #: Wig rows nothing on the device covers. These feed the exclusion
    #: picker: the fitter says not_on_device or wont_work, or leaves
    #: them unclaimed.
    unmatched_wig_rows: list[int] = field(default_factory=list)
    #: Device commands the wig does not have. These feed the
    #: content-change prompt: propose adding them, or attest the rest.
    unmatched_device_rows: list[int] = field(default_factory=list)


def match_device_to_wig(
    wig_rows: list[MatchRow], device_rows: list[MatchRow]
) -> MatchResult:
    """Pair a device's commands with a wig's rows, 1:1 and strictly.

    TWO PASSES. First the PAIR (digest and alias together), which is
    unambiguous and settles every row whose name did not change. Then
    digest-only, across ONLY what the first pass left over, which is
    what lets a locally renamed command still find its row.

    Pair-first matters because digest-only on its own has the
    duplicated-payload ambiguity: distinct names over one identical
    code, the SmartIR defect class this pipeline exists for. Running
    the exact pass first means those rows are already claimed by their
    true partners before the loose pass can shuffle them.

    CONSUMPTION IS STRICT. Every wig row and every device command is
    used at most once. That is what keeps the two leftover lists honest
    -- an unmatched wig row really is uncovered, an unmatched command
    really is absent from the wig -- so the exclusion picker and the
    content-change prompt cannot double-count the same row into both.

    Residual ties in pass two are broken by file order, and that is
    SOUND rather than merely convenient: rows sharing a digest share a
    waveform by definition, so whichever way a tie resolves, the bytes
    the claim binds are identical. No tie-break can route the wrong
    code. Order is fixed rather than genuinely arbitrary only so the
    same inputs always produce the same output; nothing depends on
    which one wins.
    """
    result = MatchResult()
    wig_taken: set[int] = set()
    device_taken: set[int] = set()

    def _index(rows: list[MatchRow], key, skip: set[int]) -> dict:
        out: dict = {}
        for i, row in enumerate(rows):
            if i not in skip:
                out.setdefault(key(row), []).append(i)
        return out

    # Pass one: the pair.
    by_pair = _index(wig_rows, lambda r: (r.digest, r.alias), set())
    for j, device_row in enumerate(device_rows):
        available = by_pair.get((device_row.digest, device_row.alias))
        if available:
            i = available.pop(0)
            result.matched.append(RowMatch(j, i, device_row.digest, True))
            wig_taken.add(i)
            device_taken.add(j)

    # Pass two: digest alone, over the remainders only.
    by_digest = _index(wig_rows, lambda r: r.digest, wig_taken)
    for j, device_row in enumerate(device_rows):
        if j in device_taken:
            continue
        available = by_digest.get(device_row.digest)
        if available:
            i = available.pop(0)
            result.matched.append(RowMatch(j, i, device_row.digest, False))
            wig_taken.add(i)
            device_taken.add(j)

    result.matched.sort(key=lambda m: m.device_index)
    result.unmatched_wig_rows = [
        i for i in range(len(wig_rows)) if i not in wig_taken
    ]
    result.unmatched_device_rows = [
        j for j in range(len(device_rows)) if j not in device_taken
    ]
    return result
