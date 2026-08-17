"""Tiered signal identity -- the one shared answer to "same signal?".

Unified signal identity (v0.5.8, second half). Three identity layers
exist for every captured signal, from most to least precise:

1. ``decoded_fingerprint`` -- the protocol library decoded the signal
   (NEC today on live captures; more protocols as upstream decoders
   land). Immune to timing jitter. The permanent answer.
2. ``byte_hash`` -- quantized timing words (20-unit bins), present on
   essentially every Pronto capture. Robust to the jitter that breaks
   the S/L fingerprint (Sony's long mark sits exactly ON the 48-unit
   S/L threshold, so the same button flips fingerprints between
   captures; its byte_hash survives the round trip exactly).
3. ``signal_fingerprint`` (S/L) -- the coarse short/long pattern.
   Retained for records that carry nothing better (non-Pronto legacy
   protocol/code pairs, pre-byte_hash data).

Match rule: two signals are the same when the highest tier they BOTH
carry agrees. A tier that only one side carries is skipped (never
fatal); a tier both sides carry decides (a mismatch there does NOT
fall through to a lower tier). This is a strict generalization of the
byte_hash trigger-identity rule: the only new truth-table cell is
"fingerprint mismatch + byte_hash match", which used to be a miss and
is now a match. No previously-working match can regress.

Every identity consumer (trigger matching, the known-command matcher,
Sniffer dedup, repeat suppression, the Assign-dot index) goes through
this module so the rule cannot drift between call sites.
"""
from __future__ import annotations

from dataclasses import dataclass

# Tier numbers, used in strongest_key() tuples and heal/diagnostic logs.
TIER_DECODED = 1
TIER_BYTE_HASH = 2
TIER_FINGERPRINT = 3


@dataclass(frozen=True, slots=True)
class SignalIdentity:
    """Frozen value object bundling the three identity layers.

    ``NormalizedSignal``, ``UnknownSignal``, ``IRCommand``, and
    ``IRTrigger`` all carry these three fields (the trigger under the
    name ``signal_fingerprint``); this object exists so they can be
    passed together instead of as three loose ``str | None`` positionals
    across call sites, and so key derivation (``strongest_key``) and
    comparison (``same_as``) share one implementation.
    """

    decoded_fingerprint: str | None = None
    byte_hash: str | None = None
    fingerprint: str = ""

    def match_tier(self, other: SignalIdentity) -> int | None:
        """Return the tier this pair matches at, or None for no match.

        The highest tier BOTH sides carry decides; a decided-tier
        mismatch is final (no fallthrough), a tier either side lacks is
        skipped. Empty fingerprints never match at tier 3.
        """
        if self.decoded_fingerprint and other.decoded_fingerprint:
            if self.decoded_fingerprint == other.decoded_fingerprint:
                return TIER_DECODED
            return None
        if self.byte_hash and other.byte_hash:
            if self.byte_hash == other.byte_hash:
                return TIER_BYTE_HASH
            return None
        if self.fingerprint and other.fingerprint:
            if self.fingerprint == other.fingerprint:
                return TIER_FINGERPRINT
            return None
        return None

    def same_as(self, other: SignalIdentity) -> bool:
        """Tiered identity comparison: decoded > byte_hash > S/L."""
        return self.match_tier(other) is not None

    def strongest_key(self) -> tuple[int, str]:
        """Return ``(tier, value)`` for the strongest layer present.

        The tier tag keeps the three hash namespaces from colliding in
        shared dicts. Used as the dict-key form of the identity by
        repeat suppression and the assignment index; two identities
        with equal strongest keys match under ``same_as`` whenever both
        actually carry that layer, which holds for keys derived from
        the same code path.
        """
        if self.decoded_fingerprint:
            return (TIER_DECODED, self.decoded_fingerprint)
        if self.byte_hash:
            return (TIER_BYTE_HASH, self.byte_hash)
        return (TIER_FINGERPRINT, self.fingerprint)


def same_signal(
    a_decoded: str | None,
    a_byte_hash: str | None,
    a_fingerprint: str,
    b_decoded: str | None,
    b_byte_hash: str | None,
    b_fingerprint: str,
) -> bool:
    """Functional form of the tiered rule for call sites without objects."""
    return SignalIdentity(a_decoded, a_byte_hash, a_fingerprint).same_as(
        SignalIdentity(b_decoded, b_byte_hash, b_fingerprint)
    )


# ---------------------------------------------------------------------------
# THE CANONICAL FORM: identity is computed on the WIRE Pronto, never the
# file Pronto (owner ruling 2026-08-17, one authoritative form)
# ---------------------------------------------------------------------------
#
# A Pronto that came out of a FILE and the same code coming back off a
# RECEIVER are not the same string, so hashing them gives different
# identities. The mechanism is the trailing gap word:
#
#   file  ... 002E 0011 0F1C     <- the inter-frame gap, as written
#   wire  ... 002E 0011 0000     <- what a capture rebuilds to
#
# Every capture is rebuilt from raw timings through ``raw_to_pronto``,
# and ``ProntoCommand.get_raw_timings`` strips the trailing space on the
# way out (the 0.9.8 identity rule, GH #98 terminator handling). One
# word is enough: both the S/L fingerprint and the byte hash move with
# it. So identity derived from file text can never match a real press.
#
# This is not theoretical. Measured on the bench closet, 2026-08-17:
#
#   - 469 of 943 flat wig signals change identity across that round
#     trip. 348 of them are rescued by the decoded tier, which is
#     computed from timings and so is form-independent. The remaining
#     121 are undecoded and MISSED ENTIRELY -- a Remote minted from
#     such a wig sat there with its triggers never firing (reproduced
#     on the bench with acer-rc-17de0: 16 triggers, 0 fires, until the
#     press was matched on the wire form).
#   - 80 of 272 Pronto commands on wig-adopted devices carry file-form
#     identity, 23 of them undecoded, so ``match_command`` did not
#     recognize the real remote's press and ``pin_bindings`` could not
#     map a capture-minted trigger onto them.
#
# Hence: canonicalize BEFORE hashing, everywhere. Mint doors, edit
# paths, both reverse indexes, and the matrix cell index all go through
# the three helpers below, so a second form cannot be reintroduced by
# adding a call site.
#
# What is NOT canonicalized is the stored Pronto TEXT. It stays exactly
# as written, because a wig's claim digests hash that text
# (``wig_format.row_digest``) and rewriting it would invalidate every
# fitting ever signed -- verified on the bench: the digest is stable
# across this change, and the digest OF the wire text differs. Identity
# fields move; the code a person can read and paste does not.
#
# Canonicalization is idempotent (verified over 1,411 closet codes:
# canonical(canonical(x)) == canonical(x)), which is what lets the
# load-time backfill run on every boot without churn.


def canonical_pronto(code: str | None) -> str | None:
    """The Pronto a receiver would hand us for ``code``, or None.

    None when the code is absent, unparseable, or yields no timings --
    callers then fall back to the code as written, which is the old
    behavior and no worse than it was.
    """
    if not code:
        return None
    from .ir_command import ProntoCommand, raw_to_pronto

    try:
        command = ProntoCommand(code)
        raw = command.get_raw_timings()
    except (ValueError, IndexError, TypeError):
        return None
    if not raw:
        return None
    try:
        return raw_to_pronto(raw, frequency=command.modulation)
    except (ValueError, TypeError):
        return None


def canonical_fingerprint(
    protocol: str | None, code: str | None, raw_timings: list[int] | None
) -> str:
    """``EventParser.signal_fingerprint`` on the canonical form.

    Non-Pronto protocols pass straight through: their fingerprint is
    hashed from protocol and code, which no round trip touches.
    """
    from .event_parser import EventParser

    if protocol and protocol.upper() == "PRONTO":
        wire = canonical_pronto(code)
        if wire is not None:
            return EventParser.signal_fingerprint("PRONTO", wire, raw_timings)
    return EventParser.signal_fingerprint(protocol, code, raw_timings)


def canonical_byte_hash(code: str | None) -> str | None:
    """``EventParser.pronto_byte_hash`` on the canonical form."""
    from .event_parser import EventParser

    wire = canonical_pronto(code)
    return EventParser.pronto_byte_hash(wire if wire is not None else code)
