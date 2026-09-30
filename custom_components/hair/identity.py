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

import hashlib
import logging
import statistics
from dataclasses import dataclass, field
from functools import lru_cache

_LOGGER = logging.getLogger(__name__)

# Tier numbers, used in strongest_key() tuples and heal/diagnostic logs.
TIER_DECODED = 1
TIER_BYTE_HASH = 2
TIER_FINGERPRINT = 3
# The receiver-tolerant tier (2026-08-18). Lowest of the four, consulted
# only after the three above miss, and only for undecoded records whose
# bytes never came through a receiver. See the normalized-fingerprint
# block at the foot of this module.
TIER_NORM_FP = 4


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
    #: Did the decode explain the WHOLE capture? False means it did
    #: not, and then the decoded fingerprint is not this record's
    #: identity: every DAIKIN216 code reads as the same
    #: ``KASEIKYO64:0xda11:0x20f000000002`` because the decoder only
    #: ever reads the constant frame 0. None is TRUSTED, matching
    #: ``protocol_decode``'s own rule that an unverifiable census is
    #: unknown rather than false -- the upstream strict NEC path
    #: reports None for every capture and must not be demoted by it.
    #: Default None so every existing construction site stays valid.
    decode_covers: bool | None = None

    @property
    def _usable_decoded(self) -> str | None:
        """The decoded fingerprint, unless the decode did not cover."""
        if self.decode_covers is False:
            return None
        return self.decoded_fingerprint

    def match_tier(self, other: SignalIdentity) -> int | None:
        """Return the tier this pair matches at, or None for no match.

        The highest tier BOTH sides carry decides; a decided-tier
        mismatch is final (no fallthrough), a tier either side lacks is
        skipped. Empty fingerprints never match at tier 3.

        A NON-COVERING DECODE IS NOT A TIER (owner ruling 2026-09-29).
        A record whose ``decode_covers`` is False has no usable decoded
        identity, so this falls to the byte hash -- which, for an
        allowlisted family, is now computed on the setting frames and
        therefore separates the states. Without this the byte hash is
        never reached: every Daikin press carries the same frame-0
        decoded fingerprint and matched every Daikin trigger.
        """
        mine = self._usable_decoded
        theirs = other._usable_decoded
        if mine and theirs:
            if mine == theirs:
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
        if self._usable_decoded:
            return (TIER_DECODED, self._usable_decoded)
        if self.byte_hash:
            return (TIER_BYTE_HASH, self.byte_hash)
        return (TIER_FINGERPRINT, self.fingerprint)


TIER_NAMES = {
    TIER_DECODED: "decoded",
    TIER_BYTE_HASH: "byte hash",
    TIER_FINGERPRINT: "fingerprint",
    TIER_NORM_FP: "normalized",
}


def tier_name(tier: int | None) -> str:
    """The tier's name for a log line, never a KeyError."""
    return TIER_NAMES.get(tier, "unknown")


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


@lru_cache(maxsize=512)
def degenerate_pronto(code: str | None) -> bool:
    """True when a code parses as Pronto but carries no burst at all.

    GH #108: a SmartIR file whose codes are in a format HAIR could not
    read was converted into structurally valid Pronto whose every burst
    pair is zero. Such a code transmits nothing and cannot be matched
    against anything; treating it as "no identity" is the only honest
    answer, and it is what every identity helper below returns for it.

    Cached on the code TEXT, which also makes the DEBUG line fire once
    per distinct code rather than once per lookup: these are consulted
    on every index build and every capture.
    """
    if not code:
        return False
    from .ir_command import ProntoCommand

    try:
        raw = ProntoCommand(code).get_raw_timings()
    except (ValueError, IndexError, TypeError):
        return False
    if raw and not any(raw):
        _LOGGER.debug(
            "Code has no usable timings (every burst pair is zero); "
            "treating it as carrying no identity: %.80s",
            code,
        )
        return True
    return False


def canonical_pronto(code: str | None) -> str | None:
    """The Pronto a receiver would hand us for ``code``, or None.

    None when the code is absent, unparseable, or yields no timings --
    callers then fall back to the code as written, which is the old
    behavior and no worse than it was.

    The trailing gap comes off through :func:`canonical_edges`, the one
    strip every identity computation in HAIR shares. ``ProntoCommand``
    already drops a trailing space of its own, so this is a no-op for a
    well-formed Pronto today; routing through the shared helper anyway
    is what keeps a second strip rule from appearing later (the air-path
    run measured the same code presenting as 67 or 68 edges depending on
    which side computed it).
    """
    if not code:
        return None
    from .ir_command import ProntoCommand, raw_to_pronto

    try:
        command = ProntoCommand(code)
        raw = command.get_raw_timings()
    except (ValueError, IndexError, TypeError):
        return None
    raw = canonical_edges(raw, signed=True)
    if not raw:
        return None
    try:
        return raw_to_pronto(
            raw,
            frequency=command.modulation,
            timebase_hz=command.timebase_hz,
        )
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

    # A CODE THAT PARSES AS PRONTO WORDS IS PRONTO, stamp or no stamp
    # (GH #125). ``protocol`` defaults to None on UnknownSignal,
    # IRCommand and IRTrigger, and both load-time migrations call this
    # with raw_timings=None. Without this widening such a row fell to
    # ``signal_fingerprint(None, code, None)``, which hashes an EMPTY
    # raw timing list and hands back one constant for every caller --
    # so every protocol-less Pronto row in a store was rewritten onto a
    # single shared fingerprint at load, and they all matched each
    # other. Pre-existing since the 2026-08-17 backfill rather than new
    # here; in scope because that same migration is its vehicle.
    is_pronto = bool(protocol and protocol.upper() == "PRONTO")
    if not protocol and code:
        is_pronto = EventParser._parse_pronto_words(code) is not None

    if is_pronto:
        # No burst, no identity (GH #108). Hashing the text of an
        # all-zero code would mint a fingerprint that matches nothing on
        # the air and collides with every other empty code; the empty
        # string is the answer callers already skip on.
        if degenerate_pronto(code):
            return ""
        wire = canonical_pronto(code)
        if wire is not None:
            return EventParser.signal_fingerprint("PRONTO", wire, raw_timings)
        # Hashable but not canonicalizable (the over-declared-header
        # class). Hash it AS PRONTO rather than falling through, or an
        # unstamped one lands on the empty-raw constant after all.
        return EventParser.signal_fingerprint("PRONTO", code, raw_timings)

    # THE SAME COLLAPSE, ONE STEP FURTHER OUT. A row with no protocol
    # stamp, a code that is not Pronto at all, and no raw timings to
    # fall back on has nothing to hash: signal_fingerprint would hand
    # back the fingerprint of an EMPTY timing list, one constant shared
    # by every such row, and the load-time migration would write it in.
    # No identity is the honest answer and every caller already skips
    # the empty string (GH #108 set that convention). A row that HAS
    # timings still gets their fingerprint, which is real.
    if not protocol and code and not raw_timings:
        return ""
    return EventParser.signal_fingerprint(protocol, code, raw_timings)


def canonical_byte_hash(code: str | None) -> str | None:
    """``EventParser.pronto_byte_hash`` on the canonical form."""
    from .event_parser import EventParser

    if degenerate_pronto(code):
        return None
    wire = canonical_pronto(code)
    return EventParser.pronto_byte_hash(wire if wire is not None else code)


# ---------------------------------------------------------------------------
# THE RECEIVER-TOLERANT TIER: a normalized fingerprint for file-sourced,
# undecoded codes (2026-08-18, from the air-path characterization run)
# ---------------------------------------------------------------------------
#
# WHAT THE MEASUREMENT SAID. A code HAIR knows only from a FILE -- a
# matrix cell, a wig-minted trigger or command, a Clipper paste, a
# Plucker pull -- does not match its own capture over a real air path on
# the byte-hash tier. Twenty presses of one Mitsubishi cell through the
# microsecond-accurate ESPHome transmitter produced twenty distinct byte
# hashes and not one of them was the code that was sent. Short flat
# codes hash stably but on a transmitter-specific wrong value: ESPHome
# and Broadlink each land on their own, and neither is the file's. The
# injector reproduces the file identity exactly in every case, so the
# identity code is right and the air is what moves.
#
# The distortion is the receiver's, not the transmitter's: marks come
# back short and spaces come back long (mean mark ratio 0.88 to 0.95 on
# ESPHome, 0.83 to 0.85 on Broadlink; spaces 1.00 to 1.12), the classic
# photodiode AGC signature, with per-edge excursions from 0.71 to 1.27 --
# more than enough to flip an individual S/L decision. Press to press
# the mean is very steady (spread 0.002 to 0.023), so the distortion is
# systematic rather than random.
#
# WHAT SURVIVES IT. Divide a capture's marks by its own median mark and
# its spaces by its own median space, and a systematic stretch cancels.
# Classify the normalized runs into two levels and hash the class
# sequence with the edge count: over 35 air captures of three codes from
# two transmitters, that value equalled the value computed from the FILE
# in 34 cases (the one miss is a Broadlink capture of C2, the worst
# transmitter). It is also distinct where it has to be: 34 distinct
# values for the 34 distinct codes of a 64-cell Mitsubishi lattice, and
# 16 for the 16 signals of an ACER RC-17DE0 wig.
#
# WHY THE LEVELS ARE FOUND, NOT THRESHOLDED. The obvious cheap version
# is to keep the existing S/L threshold and apply it to the normalized
# values. Measured on the same corpus, that collapses ALL SIXTEEN ACER
# codes onto one value, because a fixed multiple of the median lands on
# the wrong side of a protocol whose short and long runs are not spread
# the way NEC's are. Splitting at the widest RELATIVE gap in the code's
# own sorted runs (and only if that gap is at least 1.20x, so a run with
# no real separation stays one level) gives 16 of 16 on the same data.
# Two levels only: three and four levels were measured and buy nothing.
#
# WHY THE TIER IS NOT FOR EVERYONE. It is deliberately the LOWEST tier,
# reached only after decoded, (fingerprint, byte hash) and byte hash all
# miss, and only for records that are BOTH file-sourced and undecoded.
# A receiver-learned record already matches through its existing tiers,
# and handing it this one would re-collapse the sibling buttons the byte
# hash exists to separate: a sub-threshold remote (Sony and family)
# classifies every run the same way, so its whole keypad shares one
# normalized fingerprint. Measured across the bench closet, 53 buttons
# of one Sony wig share a single value -- which costs nothing there
# because every one of them decodes and never reaches this tier, and
# would cost a great deal on a keypad that does not.
#
# AMBIGUITY IS NOT A MATCH. Even inside the scope above, two genuinely
# different waveforms can share a normalized fingerprint: 13 groups out
# of 2,354 across the same closet, mostly long AC blobs whose runs sit
# in one cluster. An index therefore REFUSES a value claimed by two
# different codes rather than letting the last one win (NormFpIndex
# below). Reporting the wrong state is worse than reporting none, and
# that is a rule this file now enforces structurally instead of asking
# every call site to remember it.

# A run must sit at least this far above the next one down before the
# two count as different levels. Below it, the code has no real
# separation and stays one level.
NORM_LEVEL_MIN_RATIO = 1.20
# A space this many times the 90th-percentile space is an inter-frame
# gap rather than a data space. Referencing the 90th percentile rather
# than the median keeps a protocol's long data space (roughly three
# times its short one) below the bar while a real inter-frame gap, an
# order of magnitude longer again, clears it.
NORM_FRAME_GAP_FACTOR = 3.0


def canonical_edges(
    timings: list[int] | None, *, signed: bool = False
) -> list[int]:
    """THE trailing-gap strip: drop trailing zeros, then a trailing space.

    Both sides of every comparison carry a trailing gap inconsistently.
    A receiver appends its own terminating silence to what it heard; a
    file writes an inter-frame gap the Pronto round trip renders as a
    zero word. The air-path run measured the same code presenting as 67
    edges from one path and 68 from the other, which is enough on its
    own to break any identity that counts edges.

    So: one strip, used by every identity computation. An edge list is
    left ending on a MARK, which is the only end both paths agree on.
    ``signed=True`` returns HAIR's signed convention (mark positive,
    space negative); the default returns absolute values, which is what
    the level classifier wants.
    """
    if not timings:
        return []
    out = [int(v) for v in timings]
    while out and out[-1] == 0:
        out.pop()
    # DEGENERATE INPUT IS NO IDENTITY (GH #108). A code whose every
    # burst pair is zero strips away to nothing here. There is no frame
    # in it, so there is no identity to compute, and the empty list says
    # exactly that: every caller already reads empty as "no answer".
    # Before this, an all-zero code reached the pop below with an empty
    # list (zero is even) and raised IndexError from inside the identity
    # layer, which took out the whole index build and every websocket
    # handler that touched it.
    if not out:
        return []
    # Even length means the list ends on a space, whatever its sign
    # convention: position, not sign, is what says mark or space.
    if len(out) % 2 == 0:
        out.pop()
    if not out:
        return []
    if signed:
        return [v if i % 2 == 0 else -abs(v) for i, v in enumerate(out)]
    return [abs(v) for v in out]


def first_frame(edges: list[int]) -> list[int]:
    """The first frame of a possibly multi-frame code.

    A capture is one frame: a receiver ends its capture at the gap, so a
    two-frame press arrives as two separate captures of 292 edges each
    while the file holds all 584. Comparing a file's whole code against
    a capture could therefore never match, so both sides reduce to their
    first frame before anything is hashed. A state frame is a complete
    state, and the remote-level dedup already collapses the second
    hearing of one press.
    """
    if len(edges) < 8:
        return list(edges)
    spaces = [s for s in edges[1::2] if s > 0]
    if len(spaces) < 4:
        return list(edges)
    ordered = sorted(spaces)
    floor = ordered[int(0.9 * (len(ordered) - 1))] * NORM_FRAME_GAP_FACTOR
    for i in range(1, len(edges), 2):
        if edges[i] < floor:
            continue
        head = edges[: i + 1]
        # Only a real split: what follows has to be a comparable frame
        # rather than a stray tail, or a code with one long interior
        # space would be cut in half.
        if len(edges) - len(head) >= len(head) / 4:
            return head
    return list(edges)


def _level_labels(values: list[float]) -> list[int]:
    """Two levels, split at the widest relative gap in the sorted runs.

    Returns all zeros when no gap reaches ``NORM_LEVEL_MIN_RATIO`` --
    a run with no real separation is one level, not two halves of noise.
    """
    n = len(values)
    if n < 2:
        return [0] * n
    order = sorted(range(n), key=lambda i: values[i])
    ordered = [values[i] for i in order]
    best_ratio = 0.0
    cut = 0
    for i in range(1, n):
        if ordered[i - 1] <= 0:
            continue
        ratio = ordered[i] / ordered[i - 1]
        if ratio > best_ratio:
            best_ratio, cut = ratio, i
    if best_ratio < NORM_LEVEL_MIN_RATIO:
        return [0] * n
    labels = [0] * n
    for position, index in enumerate(order):
        labels[index] = 1 if position >= cut else 0
    return labels


# ---------------------------------------------------------------------------
# SETTING-FRAME IDENTITY (owner rulings 2026-09-28 and 2026-09-29)
# ---------------------------------------------------------------------------
#
# An AC handset spreads one press over several frames, and only some of
# them carry the settings. Identity computed on the FIRST frame reads
# the same for every state the unit can be in, which is what made a
# matrix remote hear Off for every Daikin press (#178 stopped it
# answering; this makes it answer correctly). Identity computed on the
# SETTING frames separates the states.
#
# WHICH FRAMES: the map says, in ``setting_frames``, since schema v0.5.
# They are concatenated in the order the map lists them, which puts
# ``payload_frame`` first and is the map's own statement of which block
# is primary. Order only has to be agreed, and taking it from one place
# is what agrees it.
#
# WHY AN ALLOWLIST AS WELL. A map naming its setting frames is a claim,
# and the claim is checkable: read every code in the family's own
# ``derivation.files_used`` and ask whether one setting-frame identity
# ever covers two cells whose frames do not all decode alike. Measured
# 2026-09-29, counting only collisions this change would INTRODUCE
# (cells already sharing every frame are one waveform today and resolve
# as one now):
#
#   DAIKIN216     setting_frames [1]     1 source  (the FTXS50KVM wig)   0
#   PANASONIC216  setting_frames [1]     11 files                        0
#   TCL112        setting_frames [1, 0]  14 files                        0
#   DAIKIN152     setting_frames [3]     8 files                        14
#
# TCL112 is the case the key was added for: on ``payload_frame`` alone
# it had 692 colliding identities, because its fan speed rides in frame
# 0, and naming both frames takes it to zero.
#
# DAIKIN152's fourteen are all in one file, smartHomeHub codeset 1108,
# and they are that file mislabelling rather than the map misreading.
# They are cool/level5/T against heat/level5/T for T = 18 through 31,
# a whole contiguous temperature run at one fan level, and the ONLY
# bytes that differ anywhere in the four frames are frame 2 bytes 5
# and 7, which are the capture-time clock. Two captures of one press,
# filed under two modes. The owner ruled the target is zero collisions
# between cells that differ in something the unit ACTS ON; by that
# measure this file contributes zero and the family is on the list.
#
# GREE is NOT on the list. Its map declares setting_frames [0, 1], but
# its derivation names no file list to check it against ("25 distinct
# files with the (35,32) layout"), so the claim is unverified here.
# Unverified is off.
#
# The set lives here rather than in the map YAML on purpose (owner
# ruling 2026-09-28): the maps are the field-map author's format, and
# once they record which families are verified this constant moves into
# them.
SETTING_IDENTITY_VERIFIED = frozenset({
    "DAIKIN216", "PANASONIC216", "TCL112", "DAIKIN152",
})


def setting_identity_families() -> tuple[str, ...]:
    """The allowlist, sorted, for the stored index's digest."""
    return tuple(sorted(SETTING_IDENTITY_VERIFIED))


# ---------------------------------------------------------------------------
# IDENTITY FROM THE BYTES THE MAP READS (GH #183, 2026-09-30)
# ---------------------------------------------------------------------------
#
# Setting-frame identity hashes the settings frame's TIMINGS. Two things
# a real handset does defeat that, and both were measured:
#
# - The air moves every edge. Research doc 22: twenty presses of one AC
#   state through a microsecond-accurate transmitter gave twenty byte
#   hashes, none the file's, because a receiver brings marks back short
#   and spaces long (marks 0.83-0.95, spaces 1.00-1.12, single edges
#   0.71-1.27) and a 300-edge frame always has some edge on a bin line.
# - The handset writes bytes the file did not. The #183 reporter's
#   capture reads as the state his wig holds, and its settings frame
#   still differs from that cell in bytes 5, 11, 12 and 15: timer and
#   clock bits nothing reads.
#
# So for a family on the list below, the byte hash is instead a hash of
# what the map READS: the protocol id, its declared identity bytes, and
# every field's raw bits in map order. Provisional fields take part
# exactly like ratified ones (owner ruling 2026-09-30: confidence gates
# comb findings, never identity). Bits no field names do not take part,
# and the frame's own checksum never does -- it is recomputed and must
# hold before any key is formed, so a bit the air flipped is refused
# rather than heard as a different state.
#
# WHY A SECOND LIST. The key is only as distinct as the map: a family
# whose file varies a setting the map does not read (a swing the map
# has no field for, a turbo flag beside the fan nibble) would collapse
# two states onto one key. Completeness is a fact about a family's
# files, not something a map can say about itself, so a family joins
# only when the distinctness sweep over its own derivation sources is
# clean, and ``test_read_bytes_identity``'s sweep over its field pack
# keeps it honest. Measured 2026-09-30 on f9f76fb's maps:
#
#   DAIKIN216     FTXS50KVM wig        520 states, 520 keys      clean
#   PANASONIC216  11 files             swing unmapped (1030), quiet
#                                      beside fan (1032)         out
#   TCL112        14 files             turbo beside fan, Fahrenheit
#                                      and half-degree labels    out
#   DAIKIN152     8 files              powerful beside fan; swing
#                                      unmapped (the #183 wig)   out
#
# DAIKIN152 joins in a one-line follow-up once its map reads swing and
# the fan flags (owner ruling 2026-09-30). The others keep setting-frame
# identity until their maps grow.
READ_BYTES_VERIFIED = frozenset({"DAIKIN216"})


def read_bytes_families() -> tuple[str, ...]:
    """The read-bytes list, sorted, for the stored index's digest."""
    return tuple(sorted(READ_BYTES_VERIFIED))


def _stripped(timings: list[int] | None) -> list[int]:
    """The train ``field_readers`` walks: trailing Pronto zeros removed."""
    train = [int(v) for v in (timings or [])]
    while train and train[-1] == 0:
        train.pop()
    return train


def _verified_reading(train: list[int]):
    """``(map, places)`` for an allowlisted family, or None.

    One place decides both whether the setting-frame path applies and
    where its frames sit, so the two can never disagree.
    """
    got = _verified_decoding(train, SETTING_IDENTITY_VERIFIED)
    return None if got is None else (got[0], got[1])


def _verified_decoding(train: list[int], families: frozenset[str]):
    """``(map, places, decoded)`` for the first family in ``families``
    that reads and identifies this train, or None.

    ``decoded`` holds each frame's bytes laid on the map's layout, so a
    frame index means the same thing whether or not an optional leader
    was sent.
    """
    from .field_readers import (
        _matches_identity,
        aligned_positioned,
        bits_to_bytes,
        library,
        read_frames_positioned,
    )

    if not train:
        return None
    for field_map in library():
        if field_map.protocol_id not in families:
            continue
        frames, places, failed = read_frames_positioned(
            field_map.timing, train
        )
        if failed:
            continue
        # Laid on the map's layout, so a code that left out an optional
        # leader (schema v0.6) still names its setting frames by the
        # map's own indices. The stand-in leader has no positions and is
        # never a setting frame, so it contributes nothing to a span.
        laid = aligned_positioned(field_map, frames, places)
        if laid is None:
            continue
        frames, places = laid
        decoded = [
            bits_to_bytes(frame, field_map.bit_order) for frame in frames
        ]
        if not _matches_identity(field_map, decoded):
            continue
        return field_map, places, decoded
    return None


def read_bytes_key(field_map, frames) -> str | None:
    """The read-bytes identity of these decoded frames, or None.

    ``frames`` is laid on the map's layout (a frame the caller does not
    have is an empty tuple). None when any field cannot be read, so a
    key is never formed from part of what the map says identity is.
    """
    import json

    from .field_readers import Reading, read_field

    reading = Reading(
        field_map.protocol_id, tuple(tuple(frame) for frame in frames)
    )
    values: list[list[object]] = []
    for spec in field_map.fields:
        value = read_field(reading, spec)
        if value is None:
            return None
        values.append([spec.name, value])
    payload = json.dumps(
        [
            field_map.protocol_id,
            [list(entry) for entry in field_map.identity_bytes],
            values,
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(("read:" + payload).encode()).hexdigest()[:16]


def _setting_rules_hold(field_map, frames) -> bool:
    """Every ratified integrity rule on a setting frame evaluates True.

    The key vouches for the bytes it hashes, so a rule that cannot be
    evaluated counts as failing here.
    """
    from .field_readers import RULE_FRAME_REPEAT, Reading, check_integrity

    wanted = set(field_map.setting_frames)
    reading = Reading(
        field_map.protocol_id, tuple(tuple(frame) for frame in frames)
    )
    for rule in field_map.integrity:
        if not rule.ratified or rule.type == RULE_FRAME_REPEAT:
            continue
        if int(rule.params.get("frame", 0) or 0) not in wanted:
            continue
        if check_integrity(reading, rule) is not True:
            return False
    return True


def read_bytes_hash(timings: list[int] | None) -> str | None:
    """The read-bytes identity of a WHOLE capture, or None.

    The whole capture has to read as a family on ``READ_BYTES_VERIFIED``;
    the key is then that family's fields read from its setting frames.
    Otherwise None, and the caller keeps today's identity exactly.

    A LONE setting frame gets no key, on purpose (owner ruling
    2026-09-30). The 19-byte Daikin settings frame is the same frame in
    DAIKIN216 and DAIKIN152 -- same width, same 11 DA 27 header, same
    checksum -- so alone it names neither family (measured on 200 of 200
    DAIKIN216 pack frames and every synthetic DAIKIN152 one), and with
    only one of the two families listed, any key chosen for it would
    stop the other family's lone frames matching their cells. It keeps
    its setting-frame timing identity until the DAIKIN152 follow-up,
    where the lone frame takes one shared key over both maps' fields.
    """
    if not READ_BYTES_VERIFIED:
        return None
    train = _stripped(timings)
    if not train:
        return None
    got = _verified_decoding(train, READ_BYTES_VERIFIED)
    if got is None:
        return None
    field_map, _places, decoded = got
    if not _setting_rules_hold(field_map, decoded):
        return None
    return read_bytes_key(field_map, decoded)


def setting_frame_spans(
    timings: list[int] | None,
) -> list[tuple[int, int]] | None:
    """``[(start, end), ...]`` for each setting frame, or None.

    Word indices into the trailing-zero-stripped train, so a caller
    holding Pronto words and a caller holding microseconds slice the
    same boundary from one definition. In map order.

    EACH SPAN IS ITS HEADER PAIR THROUGH ITS STOP MARK (review finding
    3). ``read_frames_positioned`` records bit pairs only; a frame's
    stop mark rides in the following pair, together with the gap that
    closes the frame. A receiver handing over that frame alone ends on
    that stop mark, and ``canonical_edges`` strips the trailing space
    after it. A slice ending at the last bit pair is two edges short
    and equals a lone frame never: measured 0 of 521 with the last bit
    pair, 521 of 521 including the stop mark.

    None when nothing reads the code or the family is not allowlisted,
    in which case the caller keeps today's behaviour exactly.
    """
    train = _stripped(timings)
    got = _verified_reading(train)
    if got is None:
        return None
    field_map, places = got
    spans: list[tuple[int, int]] = []
    for index in field_map.setting_frames:
        if index >= len(places) or not places[index]:
            return None
        first = places[index][0]
        if first > 0:
            mark = abs(train[2 * (first - 1)])
            space = abs(train[2 * (first - 1) + 1])
            if (field_map.timing.header_mark.holds(mark)
                    and field_map.timing.header_space.holds(space)):
                first -= 1
        last = places[index][-1]
        spans.append((2 * first, min(2 * last + 3, len(train))))
    return spans or None


def setting_identity_edges(timings: list[int] | None) -> list[int] | None:
    """The setting frames' own edges, concatenated, or None."""
    spans = setting_frame_spans(timings)
    if spans is None:
        return None
    train = _stripped(timings)
    out: list[int] = []
    for start, end in spans:
        out.extend(train[start:end])
    return out or None


def lone_frame_families() -> frozenset[str]:
    """Allowlisted families a SINGLE frame can still identify.

    Only where the map names one setting frame (owner ruling
    2026-09-29). A receiver hands over one frame between two gaps, so
    if the state needs two frames a lone frame does not carry it, and
    no identity computed from it can name the state. That is a fact
    about the air, not about this code. TCL112 and GREE are the
    multi-frame cases; both keep whole-capture identity only.

    Derived from the map rather than a second allowlist, so a map that
    gains or loses a setting frame changes this with it.
    """
    from .field_readers import library

    return frozenset(
        m.protocol_id for m in library()
        if m.protocol_id in SETTING_IDENTITY_VERIFIED
        and len(m.setting_frames) == 1
    )


def field_map_digest() -> str:
    """What the setting-frame path's answers depend on, as one hash.

    A stored cell index is only as good as the rules that built it, and
    those rules are not all in this repository's code: they are in the
    field-map YAML, plus the allowlist above. Edit a map's frame layout
    or its setting frames and every stored index is answering with
    boundaries the current library would not choose -- silently,
    because nothing else in the index's freshness check moves.
    ``INDEX_FORMAT`` catches a change to the ALGORITHM and the matrix
    content hash catches a change to the LATTICE; this is the third
    thing, and it was review finding 2.

    Hashed from the map SOURCE rather than the parsed objects: a parse
    is lossy by design (unknown keys are dropped), and a key this code
    ignores today may be one it reads tomorrow. That also means the
    map version schema v0.5 derives per map rides along without this
    needing to know about it.
    """
    from .field_readers import maps_dir

    hasher = hashlib.sha256()
    hasher.update(("|".join(setting_identity_families())).encode())
    # The read-bytes list decides what a listed family's byte hash IS,
    # so a family joining it rebuilds every stored index, the same way
    # a map edit does.
    hasher.update(("|read:" + "|".join(read_bytes_families())).encode())
    try:
        paths = sorted(maps_dir().glob("*.yaml"))
    except OSError:  # pragma: no cover - a missing directory is not a crash
        paths = []
    for path in paths:
        hasher.update(path.name.encode())
        try:
            hasher.update(path.read_bytes())
        except OSError:  # pragma: no cover
            hasher.update(b"<unreadable>")
    return hasher.hexdigest()[:16]


@dataclass(frozen=True)
class LoneFrame:
    """One frame of a multi-frame family, recognized on its own.

    ``judged`` is the whole point (review finding 5). A frame index a
    map says nothing about -- no identity byte, no ratified rule that
    names it -- passes every test it has, because it has none. GREE
    frame 1 is 32 bits with neither, so under a rule that only asks
    "did anything fail", every 32-bit capture in the world qualifies as
    a GREE preamble: the census had 46 rows doing exactly that, and
    they were a Samsung TV button and real NEC presses. A verdict is
    only a verdict when something was actually checked.
    """

    protocol_id: str
    frame_index: int
    is_setting: bool


def lone_frame_candidates(timings: list[int] | None) -> list[LoneFrame]:
    """Every (family, frame) this single frame could be, judged.

    A candidate needs a width inside the map's tolerance AND at least
    one identity byte or ratified non-repeat rule EVALUATED on that
    frame index, all of them passing. ``frame_repeat`` is skipped: it
    is a statement about a frame's relationship to other frames, and
    there are no other frames here.
    """
    from .field_readers import (
        RULE_FRAME_REPEAT,
        IntegrityRule,
        Reading,
        bits_to_bytes,
        check_integrity,
        library,
        read_frames,
    )

    train = _stripped(timings)
    if not train:
        return []
    out: list[LoneFrame] = []
    for field_map in library():
        frames, failed = read_frames(field_map.timing, train)
        if failed or len(frames) != 1:
            continue
        bits = frames[0]
        for index, width in enumerate(field_map.frame_layout):
            if abs(len(bits) - width) > field_map.bits_tolerance:
                continue
            decoded = bits_to_bytes(bits, field_map.bit_order)
            judged = False
            passes = True
            for frame_index, byte_index, value in field_map.identity_bytes:
                if frame_index != index:
                    continue
                judged = True
                if byte_index >= len(decoded) or decoded[byte_index] != value:
                    passes = False
            for rule in field_map.integrity:
                if not rule.ratified or rule.type == RULE_FRAME_REPEAT:
                    continue
                if int(rule.params.get("frame", 0) or 0) != index:
                    continue
                params = dict(rule.params)
                params["frame"] = 0
                verdict = check_integrity(
                    Reading(field_map.protocol_id, (decoded,)),
                    IntegrityRule(rule.type, params, rule.confidence, ""),
                )
                if verdict is None:
                    continue
                judged = True
                if not verdict:
                    passes = False
            if judged and passes:
                out.append(LoneFrame(
                    field_map.protocol_id, index,
                    index in field_map.setting_frames,
                ))
    return out


def identify_lone_frame(timings: list[int] | None) -> LoneFrame | None:
    """The one family and frame this is, or None.

    None when nothing qualifies AND when more than one thing does: a
    frame two families both claim names neither of them. Callers key
    on this verdict object, never on a fingerprint coming back None --
    "no identity" and "this is a known preamble" are different answers
    and only one of them is safe to act on.
    """
    candidates = lone_frame_candidates(timings)
    return candidates[0] if len(candidates) == 1 else None


def identity_frame(timings: list[int] | None) -> list[int]:
    """The edges identity is computed on.

    Three answers, in order:

    1. The setting frames concatenated, when the whole capture reads as
       an allowlisted family.
    2. The frame itself, when this is a LONE frame that an allowlisted
       single-setting-frame family recognizes as its setting frame --
       which is what makes a receiver's half-press meet the same
       lattice cell the whole press does.
    3. Otherwise exactly what this layer has always used:
       ``first_frame`` of the UNSIGNED edges. Unsigned matters --
       ``first_frame`` only counts positive spaces, so handing it
       signed edges moves unmapped rows that nothing asked to move
       (review finding 3).

    A lone NON-setting frame (a Daikin preamble, say) falls to 3 rather
    than being suppressed. It will match nothing, because no cell is
    indexed on it, and "no match" is the honest answer without this
    layer having to invent a special one.
    """
    setting = setting_identity_edges(timings)
    if setting is not None:
        return [abs(v) for v in setting]
    verdict = identify_lone_frame(timings)
    if (verdict is not None
            and verdict.is_setting
            and verdict.protocol_id in lone_frame_families()):
        return canonical_edges(timings)
    return first_frame(canonical_edges(timings))


def norm_fingerprint(timings: list[int] | None) -> str | None:
    """The receiver-tolerant fingerprint of one code, or None.

    None when there is nothing to hash, or when the code carries no
    structure at all (every run in one level) -- such a value would
    match anything of the same length and is worse than no answer.
    """
    edges = canonical_edges(identity_frame(timings))
    marks = edges[0::2]
    spaces = edges[1::2]
    # Also the degenerate case (GH #108): an all-zero code strips to no
    # edges at all, so there is nothing to hash and nothing to say.
    if not marks or not spaces:
        return None
    median_mark = statistics.median(marks) or 1
    median_space = statistics.median(spaces) or 1
    mark_levels = _level_labels([m / median_mark for m in marks])
    space_levels = _level_labels([s / median_space for s in spaces])
    if not any(mark_levels) and not any(space_levels):
        return None
    sequence = [
        mark_levels[i // 2] if i % 2 == 0 else space_levels[i // 2]
        for i in range(len(edges))
    ]
    payload = f"{len(edges)}|" + "".join(str(level) for level in sequence)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _value_levels(values: list[int], ratio: float) -> list[int]:
    """``_level_labels`` generalized from two levels to as many as the
    values actually show.

    Sort, then start a new level wherever consecutive sorted values jump
    by ``ratio`` or more. Every boundary therefore sits inside a real
    gap in the data rather than at a fixed microsecond, which is what
    makes the result survive jitter: a value has to cross a genuine
    cluster gap to change level, not merely drift.

    ``_level_labels`` itself stays two-level and untouched:
    ``norm_fingerprint`` is a MATCHING identity and its coarseness is
    deliberate. This is for telling two records apart, which needs to
    see more than "long or short".
    """
    n = len(values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: values[i])
    labels = [0] * n
    level = 0
    for position in range(1, n):
        previous = values[order[position - 1]]
        current = values[order[position]]
        if previous > 0 and current / previous >= ratio:
            level += 1
        labels[order[position]] = level
    return labels


def whole_code_discriminator(
    timings: list[int] | None, frame_identity: str | None = None
) -> str | None:
    """"Are these two records the same code?", over EVERY frame.

    THE DISCRIMINATOR AN INDEX REFUSES ON (owner bench 2026-09-25).
    ``NormFpIndex`` and the cell index's other tiers poison a key that
    two genuinely different codes claim, and to do that they need a
    value saying WHICH code a record is. The byte hash cannot be that
    value for a lattice: ``_pronto_identity_timings`` stops at the first
    gap, so all 520 cells of a Daikin 216 lattice share one byte hash,
    one S/L fingerprint and one normalized fingerprint, every one of
    them computed from the single constant frame 0. An index given only
    those cannot tell a repeated waveform from a genuinely different
    state, so it kept whichever came last -- the Off code, which
    ``build_cell_index`` adds after the cells.

    So this reads the whole code, on the levels its own edges show.

    QUANTIZED, NOT EXACT (owner ruling 2026-09-25). Exact edges would be
    a sharper test and the wrong one: not every lattice is pristine file
    text. A lattice built from captures -- a WigFactory pull, a repaired
    or listened cell -- can hold one waveform twice with microseconds
    between the two, and exact edges would call those different codes
    and refuse a pair that is really one press. Measured on the Komeco
    PR-19 lattices, which are capture-built: seven such pairs, each
    differing on up to 134 of 197 edges, and every difference a wobble
    inside its own cluster (short marks 447-579, long spaces
    1578-1709). Not one position crosses between the short-space and
    long-space clusters, which is what a different bit would look like.

    WHY LEVELS AND NOT A FIXED TOLERANCE. Bucketing each edge at a fixed
    ratio was measured first and fails: with ~200 edges, some edge sits
    near a bucket boundary in almost every code, so jitter flips it and
    two captures of one press stop matching. Levels put every boundary
    inside a real gap in that code's own values, which survived all
    2,560 synthetic jitter cases in the bench sweep.

    WHY NOT ``norm_fingerprint``'s TWO LEVELS OVER EVERY FRAME. Also
    measured, also fails, in the other direction: two levels are too few
    to carry a payload, and the Komeco lattices collapsed from 836
    distinct codes to 15 discriminators. Two levels answer "is this
    edge long or short"; telling states apart needs "which of this
    code's several widths is it".

    IT FOLDS IN THE OLD DISCRIMINATOR RATHER THAN REPLACING IT.
    ``frame_identity`` is the record's existing frame-0 identity -- its
    byte hash, or its fingerprint when it has no hash -- which is
    exactly the value callers passed as the whole discriminator before
    this function existed. It is still needed, because levels are
    RATIOS and therefore blind to scale: the same code played 15%
    slower has every ratio unchanged and would otherwise read as the
    same waveform, when it is a different one (pinned by
    test_matrix_listener's one-shape-twice test). Frame 0 sees that;
    the levels see the payload frame 0 is blind to. Together they
    answer both ways round.

    The pairing is measured, not assumed: on the capture-built Komeco
    lattices the seven jitter-twin pairs agree on BOTH halves, because
    the byte hash is quantized and survived all 180 small-jitter cases
    in the bench sweep.

    WHICH WAY IT FAILS. Equal discriminators MERGE (the key resolves);
    different ones REFUSE (the key answers nothing). Merging wrongly
    names a state nobody pressed; refusing wrongly says nothing. Every
    uncertainty here therefore resolves towards refusing, which is also
    why the two halves are ANDed: disagree on either and the pair is
    refused.

    Returns None only for a code with no edges at all, which carries no
    identity of any kind (GH #108).
    """
    edges = canonical_edges(timings)
    if not edges:
        return None
    mark_levels = _value_levels(edges[0::2], NORM_LEVEL_MIN_RATIO)
    space_levels = _value_levels(edges[1::2], NORM_LEVEL_MIN_RATIO)
    sequence = [
        mark_levels[i // 2] if i % 2 == 0 else space_levels[i // 2]
        for i in range(len(edges))
    ]
    payload = (
        f"{frame_identity or ''}|{len(edges)}|"
        + ",".join(str(level) for level in sequence)
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@lru_cache(maxsize=1024)
def norm_fingerprint_of_code(code: str | None) -> str | None:
    """:func:`norm_fingerprint` for a stored Pronto code, or None.

    Cached on the code TEXT, which is the whole key: trigger matching
    walks every trigger on every capture, and an edited code is a
    different string and so a different entry. Nothing to invalidate.
    """
    if not code:
        return None
    from .ir_command import ProntoCommand

    try:
        raw = ProntoCommand(code).get_raw_timings()
    except (ValueError, IndexError, TypeError):
        return None
    return norm_fingerprint(raw)


@lru_cache(maxsize=1024)
def is_multi_frame_code(code: str | None) -> bool:
    """True when this code is more than one frame of one press.

    An AC state code is typically two complete frames; a flat remote's
    button is one. What follows from it is timing, not identity: a
    two-frame press arrives as two captures a tenth of a second apart,
    so anything that collapses a press to one event has to cover the gap
    between them (const.MATRIX_STATE_DEDUP_WINDOW_S).
    """
    if not code:
        return False
    from .ir_command import ProntoCommand

    try:
        raw = ProntoCommand(code).get_raw_timings()
    except (ValueError, IndexError, TypeError):
        return False
    edges = canonical_edges(raw)
    return bool(edges) and len(first_frame(edges)) < len(edges)


@dataclass
class NormFpIndex:
    """A ``norm_fp -> ref`` map that refuses to answer when ambiguous.

    Two records that ARE the same waveform (a lattice storing one code
    under sixteen coordinates, a wig imported twice) may share a value
    freely: the last one wins, exactly as every other index in HAIR
    resolves that case. Two records that are genuinely DIFFERENT codes
    poison the value instead, and it answers None from then on. The tier
    exists to recognize a press nothing else can; it is not allowed to
    invent one.
    """

    refs: dict[str, object] = field(default_factory=dict)
    #: Values claimed by more than one distinct code, answered as None.
    ambiguous: set[str] = field(default_factory=set)
    _claims: dict[str, object] = field(default_factory=dict, repr=False)

    def add(
        self, norm_fp: str | None, discriminator: object, ref: object
    ) -> None:
        """Claim ``norm_fp`` for ``ref``; ``discriminator`` says which code.

        The discriminator is the record's own stronger identity (its
        byte hash, or its fingerprint when it has no hash): two records
        agreeing there are the same waveform, and two that disagree are
        not.
        """
        if not norm_fp or norm_fp in self.ambiguous:
            return
        claimed = self._claims.get(norm_fp)
        if claimed is not None and claimed != discriminator:
            self.ambiguous.add(norm_fp)
            self.refs.pop(norm_fp, None)
            self._claims.pop(norm_fp, None)
            return
        self._claims[norm_fp] = discriminator
        self.refs[norm_fp] = ref

    def get(self, norm_fp: str | None):
        """The ref claimed by ``norm_fp``, or None."""
        if not norm_fp:
            return None
        return self.refs.get(norm_fp)

    def __bool__(self) -> bool:
        return bool(self.refs)

    def __len__(self) -> int:
        return len(self.refs)


# ---------------------------------------------------------------------------
# WHOSE BYTES NEVER CAME THROUGH A RECEIVER (owner ruling 2026-08-18)
# ---------------------------------------------------------------------------
#
# The tolerant tier is for records HAIR knows only from a file. A
# receiver-learned record already matches through its existing tiers,
# and handing it this one would re-collapse the sibling buttons the byte
# hash exists to separate.
#
# The ruling, verbatim in shape: a command is file-sourced when either
# (a) its own ``source`` says so -- the value a mint door stamped -- or
# (b) the owning device came from a file AND the command carries no
# decoded identity. (b) exists only for data written before the doors
# stamped anything, so an install that adopted a wig last month gains
# the tier without re-adopting; (a) is what every new mint uses.
#
# Wig-adopted and plucked commands are stamped IMPORTED rather than
# given a new enum value: ``CommandSource.IMPORTED`` already means "came
# from a file rather than off the air", nothing in the frontend renders
# it (the STATE chip is gated on "matrix" alone), and a fourth value
# would be a second name for the same fact.
_FILE_COMMAND_SOURCES = frozenset({"database", "imported", "matrix"})


def file_sourced_command(command, device=None) -> bool:
    """True when this command's bytes never came off a receiver."""
    if str(getattr(command, "source", "") or "") in _FILE_COMMAND_SOURCES:
        return True
    # Two per-command markers that predate the stamp and mean the same
    # thing: a Plucker pull was replayed by a vendor integration and
    # never crossed the air, and a porthole row IS a lattice cell.
    if getattr(command, "plucked_command_name", None):
        return True
    if getattr(command, "matrix_cell", None):
        return True
    if device is None or getattr(command, "decoded_fingerprint", None):
        return False
    return bool(
        getattr(device, "source_wig_id", None)
        or getattr(device, "source_file", None)
        or getattr(device, "origin", None) == "closet"
    )


# Trigger origins whose bytes cannot have come off a receiver. One
# home for the vocabulary: the mint doors write these, this tier reads
# them, and the load-time backfill in storage.py repairs rows written
# before "clip" and "plucked" existed.
FILE_SOURCED_TRIGGER_ORIGINS = frozenset({
    "closet", "matrix", "clip", "plucked",
})


def file_sourced_trigger(trigger, store) -> bool:
    """True when this trigger's bytes never came off a receiver.

    Read from what each mint door actually writes:

    - ``origin="closet"`` -- minted from a wig file by USE as a Remote.
      File-sourced by construction.
    - ``origin="matrix"`` -- saved off a lattice by Track M's own
      "+ Trigger" (the panel sends this one; ir-trigger-row paints its
      STATE chip on it). A lattice is always a file.
    - ``origin="device"`` -- minted from a HAIR device's commands, so
      the SOURCE COMMAND decides. A device minted from sniffed rows
      gives receiver-learned triggers; one adopted from a wig gives
      file-sourced ones.
    - ``origin="clip"`` / ``origin="plucked"`` -- minted
      from a Clipper paste or a Plucker pull. Both are files by
      definition: those bytes were pasted or read out of a vendor
      integration and never came off a receiver. Added 2026-08-18,
      after the regression bench proved the gap over air -- an Arris
      Power row pasted through the Clipper could not hear itself,
      because the byte hash moved, the bare-fingerprint tier is
      withheld from hash-bearing rows since v0.5.8, and the one tier
      that did match (norm_fp was identical) was never offered.
    - ``origin="remote"`` -- minted from a SNIFFED catalog
      remote's signals. Receiver-learned, so it stays off the tier.
      The only one of the three catalog sources that is.
    - ``origin="manual"`` / None -- the drawer's own dialog. Not
      file-sourced on its own.

    On top of the door, the owning Remote answers for the rows created
    ON it: a trigger saved from a matrix Remote's card or from its LAST
    HEARD row carries the origin of the dialog, not of the lattice, and
    a lattice is always a file. Same shape as the command rule's clause
    (b), including the no-decoded-identity condition.
    """
    origin = getattr(trigger, "origin", None)
    if origin in FILE_SOURCED_TRIGGER_ORIGINS:
        return True
    if origin == "device":
        device_id = getattr(trigger, "source_device_id", None)
        command_id = getattr(trigger, "source_command_id", None)
        if device_id and command_id:
            device = store.get_device(device_id)
            command = device.get_command(command_id) if device else None
            if command is not None:
                return file_sourced_command(command, device)
        return False
    if getattr(trigger, "decoded_fingerprint", None):
        return False
    remote_id = getattr(trigger, "trigger_remote_id", None)
    if not remote_id:
        return False
    remote = store.get_trigger_remote(remote_id)
    if remote is None:
        return False
    return bool(
        getattr(remote, "climate_matrix", False)
        or getattr(remote, "origin", None) == "closet"
        or getattr(remote, "source_wig_id", None)
    )
