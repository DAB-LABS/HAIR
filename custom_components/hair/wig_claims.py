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


def apply_rename_suggestions(wig: Wig, renames: dict[str, str]) -> int:
    """Write proposed aliases, keyed by row digest. Returns how many.

    THE SUGGESTION IS THE APPLIED RENAME (design ruling): names sit
    outside every digest, so writing one into the file orphans nothing
    and the shop PR shows ``alias: On -> Power`` for a maintainer to
    adjudicate like any other prose change. No separate suggestion
    channel, no new machinery.

    Keyed by digest rather than by old name because the digest is what
    survives; two rows could otherwise share a name and both move.
    """
    if not renames:
        return 0
    written = 0
    for signal in wig.signals:
        proposed = renames.get(signal_row_digest(signal))
        if proposed and proposed != signal.alias:
            signal.alias = proposed
            written += 1
    return written


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
    renames: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]] | None:
    """Append claims to an existing wig's text. Returns (text, entry).

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
    if renames:
        apply_rename_suggestions(wig, renames)
    entry = append_claims(wig, bundle, private_key_b64)
    return serialize_wig(wig), entry
