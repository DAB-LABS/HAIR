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
import statistics
from dataclasses import dataclass, field
from functools import lru_cache

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
    # Even length means the list ends on a space, whatever its sign
    # convention: position, not sign, is what says mark or space.
    if len(out) % 2 == 0:
        out.pop()
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


def norm_fingerprint(timings: list[int] | None) -> str | None:
    """The receiver-tolerant fingerprint of one code, or None.

    None when there is nothing to hash, or when the code carries no
    structure at all (every run in one level) -- such a value would
    match anything of the same length and is worse than no answer.
    """
    edges = canonical_edges(first_frame(canonical_edges(timings)))
    marks = edges[0::2]
    spaces = edges[1::2]
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
    - ``origin="remote"`` -- minted from a catalog remote's signals.
      Sniffer rows are receiver-learned, and the four-value origin
      vocabulary (which the panel renders as four colors) cannot say
      that a Clipper paste or a Plucker pull is not. Those two miss the
      tier today; widening the vocabulary is a frontend change and is
      recorded as such rather than guessed at here.
    - ``origin="manual"`` / None -- the drawer's own dialog. Not
      file-sourced on its own.

    On top of the door, the owning Remote answers for the rows created
    ON it: a trigger saved from a matrix Remote's card or from its LAST
    HEARD row carries the origin of the dialog, not of the lattice, and
    a lattice is always a file. Same shape as the command rule's clause
    (b), including the no-decoded-identity condition.
    """
    origin = getattr(trigger, "origin", None)
    if origin in ("closet", "matrix"):
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
