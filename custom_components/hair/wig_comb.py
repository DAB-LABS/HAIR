"""Combing: do a wig's codes agree with each other?

Smart Perm phase 2. The capability is COMBING on every user-facing
surface (owner ruling 2026-07-31); the class names below (malformed,
duplicated neighbour, stray burst) are the defect taxonomy, not the
feature name. Design source: docs/internal/plans/wig-repair-pipeline.md
Section 2; taxonomy and measurements in smartir-defects-and-repair.md,
whose Section 3 is the contract this module implements.

The point, stated plainly because it is easy to lose: **fitting and
combing are orthogonal.** A fitting proves a human pointed a blaster and a device
answered. A comb proves the other 945 codes are internally coherent. The
findings measured the dimension checklist against 74 known-defective cells
across six real wigs and it caught one, by luck -- not a flaw in the
checklist, which attests DIMENSIONS and says so, but the reason this module
exists.

Every check here runs on the lattice's internal consistency, never on
understanding the protocol. That is what makes it cheap and universal: four
of the six devices in the census decode as nothing at all, and a check that
needed a decoder would have nothing to say about them.

Two rules that are easy to get wrong and expensive to get wrong:

- **A whole row sending one code for every temperature is CORRECT.** It
  means the device ignores temperature in that combination. Daikin does it
  in 19 rows of 40, Sharp in 8 of 12, Samsung across all of heat_cool.
  Flagging those would have produced 37 false positives against 5 real
  defects on the census sample and buried the real ones. Only a PARTIAL
  collapse is a defect: the row proves the device responds to temperature,
  and then two values collide anyway.
- **Combing never changes a code.** It reports. Repair is a separate,
  explicit, marked operation, and the derivation engine that would perform
  it is the next release.

Pure by construction: no hass, no I/O, no clock. A wig goes in, findings
come out, and the caller decides what to do with them.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from . import field_readers
from .const import PRONTO_BYTE_HASH_BIN, PRONTO_GAP_THRESHOLD
from .decoders import split_frames
from .wig_fitting import normalized_pronto
from .wig_format import ClimateMatrix, Wig, cell_key

# Bumped when a check changes what it reports, so a stored receipt can be
# read as "checked by a version that did not know about X".
#
# 2 (fitting integrity, release one): CHECK_FRAME_DISAGREEMENT joins the
# taxonomy and every receipt carries a ``coverage`` section. A version 1
# receipt still parses and still displays; it simply cannot say what it
# did not look at, which is exactly the distinction coverage exists to
# draw.
COMB_VERSION = 2

# Findings are capped in the stored receipt (brief 5.2): a 2,689-cell
# Mitsubishi with 91 duplicate groups should not write a novel into the
# wig file. The count is always exact; the list is what truncates.
MAX_STORED_FINDINGS = 200

# --- check ids ------------------------------------------------------------
CHECK_MALFORMED = "malformed"
CHECK_FRAME_DISAGREEMENT = "frame-disagreement"
# Release two: what the frame SAYS against what the cell CLAIMS, and
# whether the frame satisfies its own protocol's structural rules.
CHECK_FIELD_MISMATCH = "field-mismatch"
CHECK_FRAME_INTEGRITY = "frame-integrity"
CHECK_STRAY_BURST = "stray-burst"
CHECK_FRAME_SHAPE = "frame-shape"
CHECK_DUPLICATED_NEIGHBOUR = "duplicated-neighbour"
CHECK_MISSING_CELL = "missing-cell"
CHECK_STRAY_CELL = "stray-cell"
CHECK_COORDINATE_COLLISION = "coordinate-collision"
CHECK_DUPLICATE_LABELS = "duplicate-labels"
CHECK_BYPASS_WITH_DITTOS = "bypass-with-dittos"
CHECK_RAMP_DITTOS = "ramp-dittos"

# Worst first (findings Section 3). A duplicated neighbour leads because it
# is the only class the device responds to: the user sets 17, gets 18, and
# either never notices or notices in six months with no idea why. A stray
# burst trails because a receiver ignores it -- it is reported only because
# it means the capture was not clean.
SEVERITY_ORDER = (
    CHECK_DUPLICATED_NEIGHBOUR,
    # A cell whose frame says a different temperature than its label is
    # the Komeco class, and it belongs at the top with the duplicated
    # neighbour for the same reason: the device answers, the UI looks
    # right, and the room sits a degree off.
    CHECK_FIELD_MISMATCH,
    # A capture whose own repeats disagree ranks next because at least
    # one of those frames is wrong and nothing in the file says which. A
    # receiver that acts on the first frame it likes can act on the bad
    # one, and the person holding the remote never sees why.
    CHECK_FRAME_DISAGREEMENT,
    CHECK_MALFORMED,
    # A frame that fails its own checksum or complement rule is a frame
    # most receivers throw away, so it ranks with the malformed rather
    # than with the wrong.
    CHECK_FRAME_INTEGRITY,
    CHECK_FRAME_SHAPE,
    CHECK_MISSING_CELL,
    CHECK_COORDINATE_COLLISION,
    CHECK_STRAY_CELL,
    CHECK_STRAY_BURST,
    CHECK_DUPLICATE_LABELS,
    CHECK_BYPASS_WITH_DITTOS,
    CHECK_RAMP_DITTOS,
)

# Advisory checks never count toward the "suspect" total and never light
# the closet chip. Same code under two names is legitimate on a toggle
# remote ("Power On" / "Power Off" sharing one code), and a flat file has
# no lattice to prove intent either way -- this is triage, not deduction.
ADVISORY_CHECKS = frozenset({
    CHECK_DUPLICATE_LABELS,
    # A hand-made file can carry both a raw pin and a ditto count. HAIR
    # never writes that pair -- the exporter drops the ditto with a
    # receipt -- so seeing it means a human wrote the file by hand and
    # deserves a look, not a verdict. The pin still wins at transmit.
    CHECK_BYPASS_WITH_DITTOS,
    # A high ditto count on a ramp-prone button is a legitimate and
    # visible behaviour choice: some receivers step once per ditto, so
    # "Volume Up with 8 dittos" may be exactly what the author meant.
    # Advisory forever, by design -- this is the one way the knob
    # encodes a surprise, and surprises get mentioned, not corrected.
    CHECK_RAMP_DITTOS,
})


@dataclass(frozen=True)
class Finding:
    """One thing the comb noticed, addressed by row key.

    ``message`` is a localization key and ``params`` its substitutions:
    the diagnosis is rendered in the reader's language, never prebaked in
    English here (brief 5.1). ``keys`` carries every row involved, which
    is more than one for the checks that are about a RELATIONSHIP --
    duplicated neighbours and duplicate labels both name their group.
    """

    check: str
    keys: list[str]
    message: str
    params: dict[str, str] = field(default_factory=dict)

    @property
    def advisory(self) -> bool:
        return self.check in ADVISORY_CHECKS

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "check": self.check,
            "keys": list(self.keys),
            "message": self.message,
        }
        if self.params:
            out["params"] = dict(self.params)
        return out


@dataclass
class Coverage:
    """What the comb looked at, and what it declined to look at and why.

    The brief's fourth ask, and the one that costs the least to get
    wrong until the day it costs everything: "a silent pass on an
    unreadable protocol is worse than no check at all, because it would
    have told us case two was fine". A receipt that says CLEAN has to be
    distinguishable from a receipt that says NOBODY LOOKED, and the only
    way to do that is to write down what ran.

    Per check id: how many codes it judged, and a tally of the codes it
    declined by reason. Release two adds per-protocol readable counts to
    the same structure, which is why the shape is a dict of dicts rather
    than two flat numbers.
    """

    codes: int = 0
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Keys any check managed to judge. A code nothing could judge is the
    # unverified case the closet has to draw differently.
    seen: set[str] = field(default_factory=set)
    # Release two: which protocol read this wig, and how much of it the
    # field tier could actually read. ``id`` is None when no map claims
    # the codes, which is the "protocol unmapped, 0 of N verified" line
    # the brief asked for by name.
    protocol: dict[str, Any] | None = None
    # Per field name, how many codes the sweep compared and what it
    # declined. A partial map is legal and useful, and this is where a
    # reader sees exactly how partial.
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _slot(self, check: str) -> dict[str, Any]:
        return self.checks.setdefault(check, {"checked": 0, "declined": {}})

    def _field_slot(self, name: str) -> dict[str, Any]:
        return self.fields.setdefault(name, {"checked": 0, "declined": {}})

    def judged(self, check: str, key: str | None = None) -> None:
        self._slot(check)["checked"] += 1
        if key is not None:
            self.seen.add(key)

    def declined(self, check: str, reason: str, count: int = 1) -> None:
        if count <= 0:
            return
        declined = self._slot(check)["declined"]
        declined[reason] = declined.get(reason, 0) + count

    def field_judged(self, name: str) -> None:
        self._field_slot(name)["checked"] += 1

    def field_declined(self, name: str, reason: str, count: int = 1) -> None:
        if count <= 0:
            return
        declined = self._field_slot(name)["declined"]
        declined[reason] = declined.get(reason, 0) + count

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "codes": self.codes,
            "checked": len(self.seen),
            "checks": {
                check: {
                    "checked": slot["checked"],
                    "declined": dict(slot["declined"]),
                }
                for check, slot in self.checks.items()
            },
        }
        if self.protocol is not None:
            out["protocol"] = dict(self.protocol)
        if self.fields:
            out["fields"] = {
                name: {
                    "checked": slot["checked"],
                    "declined": dict(slot["declined"]),
                }
                for name, slot in self.fields.items()
            }
        return out


@dataclass
class CombReport:
    """What a check found, ready for a receipt or a dialog."""

    findings: list[Finding] = field(default_factory=list)
    # Row keys the comb declined to judge because they are pinned to raw
    # (Highlights, GH #78). Recorded so a reader can tell "nothing wrong
    # with this row" from "nobody looked at this row" -- the same
    # distinction the receipt itself draws between clean and absent.
    skipped: list[str] = field(default_factory=list)
    version: int = COMB_VERSION
    coverage: Coverage | None = None

    @property
    def suspects(self) -> int:
        """Rows worth a human's attention. Advisories are not suspects."""
        return sum(1 for f in self.findings if not f.advisory)

    def counts(self) -> dict[str, int]:
        """Findings per check id, in severity order."""
        tally = Counter(f.check for f in self.findings)
        return {c: tally[c] for c in SEVERITY_ORDER if tally[c]}

    def to_receipt(self, date: str) -> dict[str, Any]:
        """The stored form (wig extra, outside every canonical hash).

        The date is passed in rather than read from a clock, so this
        module stays pure and the caller owns "now".
        """
        stored = self.findings[:MAX_STORED_FINDINGS]
        receipt: dict[str, Any] = {
            "version": self.version,
            "date": date,
            "suspects": self.suspects,
            "counts": self.counts(),
            "findings": [f.to_dict() for f in stored],
        }
        if self.coverage is not None:
            receipt["coverage"] = self.coverage.to_dict()
        if self.skipped:
            receipt["skipped"] = list(self.skipped)
        if len(self.findings) > len(stored):
            receipt["truncated"] = len(self.findings) - len(stored)
        return receipt


# ---------------------------------------------------------------------------
# Pronto shape: frames, without a decoder
# ---------------------------------------------------------------------------


def _pairs(pronto: str) -> list[tuple[int, int]] | None:
    """A Pronto code as (mark, space) pairs, or None if it will not parse.

    Deliberately forgiving: an unparseable code is not the comb's business
    (the format validator already refused it at import) and raising here
    would make one bad row abort a whole wig's check.
    """
    tokens = pronto.split()
    if len(tokens) < 6:
        return None
    try:
        words = [int(tok, 16) for tok in tokens]
    except ValueError:
        return None
    body = words[4:]
    if len(body) < 2:
        return None
    return [(body[i], body[i + 1]) for i in range(0, len(body) - 1, 2)]


def _frame_lengths(pairs: list[tuple[int, int]]) -> tuple[int, ...]:
    """Pair-counts per frame, split on the long gaps between frames.

    A frame ends where its trailing space runs long (``PRONTO_GAP_THRESHOLD``,
    the same constant the fingerprinter uses). Comparing SHAPES rather than
    total lengths is what turns "this cell is different" into "frame 0 is
    two timings short", which is a diagnosis instead of an observation
    (findings Section 5).
    """
    lengths: list[int] = []
    run = 0
    for _mark, space in pairs:
        run += 1
        if space >= PRONTO_GAP_THRESHOLD:
            lengths.append(run)
            run = 0
    if run:
        lengths.append(run)
    return tuple(lengths)


# ---------------------------------------------------------------------------
# Repeat frames: does one press agree with itself?
# ---------------------------------------------------------------------------
#
# Every other check in this module compares a code to the OTHER codes in
# the wig. This one compares a code to ITSELF, which is why it works on a
# seven-button fan nobody has written a decoder for, and why it is the
# only check that needs no population at all: repeats of one press should
# be identical, and six repeats yielding five readings is noise whatever
# the protocol.

# A repeat gap is a space that stands well clear of the code's own bit
# spaces. PRONTO_GAP_THRESHOLD cannot do this job: it is tuned to end a
# SIGNAL, and plenty of remotes separate their repeats by far less. The
# Dreo fan of the WigShop brief puts about 8 ms between frames (roughly
# 310 Pronto units against a threshold of 1024), so a fixed cut reads its
# eight repeats as one frame and the check has nothing to compare.
#
# So the gap is derived from the code's own space distribution: the
# HIGHEST multiplicative step in the sorted spaces that is at least this
# wide and leaves few enough spaces above it to be separators rather than
# data. Highest rather than widest, deliberately -- a frame separator is
# always the longest space class in a code, while the widest ratio can
# sit between a protocol's short and long bit spaces and would cut frames
# in half. A code with no such step is a single frame and says so, which
# is a coverage line, not a finding.
#
# A ratio alone cannot do it, and the reason is worth writing down. The
# step between a protocol's long and short BIT space is already about
# three: NEC spends 1690 us on a one against 560 on a zero, and a
# Fujitsu lattice on the test box reads 44 against 14. In a code that
# carries no repeat gap at all, that bit step is the biggest step there
# is, so the search found it, cut every cell into bit-sized fragments
# and reported that the fragments disagreed. 716 findings across the
# test box's closet, all of them nonsense (bench 2026-08-22).
#
# So the separator must also be a separator in absolute terms. Below
# roughly 2.6 ms nothing is a frame gap; it is a bit. Every real
# separator measured here clears that by a wide margin (the Dreo fan
# 304, a two-part air conditioner press 310, a plucked RC-5 candle 456)
# and every bit space measured falls under it (64 at the widest). The
# bar is deliberately one-directional: a missed separator costs a
# coverage line, an invented one costs a wig full of findings.
_REPEAT_GAP_RATIO = 3.0
_REPEAT_GAP_SHARE = 0.25
_REPEAT_GAP_FLOOR = 100

# Frames below this are leaders, trailing bursts and NEC dittos: real
# enough, but not a reading. Judging them would put a lattice's one-pair
# lead-in burst next to its trailing burst and call the pair a
# disagreement on every cell of the file.
_MIN_JUDGED_FRAME = 8

# Two frames that disagree tell you nothing about which one is wrong --
# the same reason `_shape_findings` wants three codes and
# `_branch_findings` wants three temperatures. It is also what keeps a
# Sharp data/inverted pair silent: two frames, deliberately different,
# nothing to vote on.
_MIN_CLUSTER_FRAMES = 3

# Frames cluster by length class before anything is compared, with slack
# so that a repeat carrying a spurious pair stays in the class it belongs
# to instead of escaping into a cluster of its own. The Dreo's Speed Down
# is exactly that case: 14, 12, 12 and 13 pairs, where strict equality
# would leave the two intact frames agreeing with each other and report
# nothing.
#
# The slack is measured from the class's SHORTEST member, not from the
# previous length, and that distinction is the whole guard. Chaining a
# tolerance from member to member lets a class walk: nineteen timings
# joins twenty-one joins twenty-three, all the way to thirty-three, and
# a spray of unrelated fragment lengths collapses into one "class" that
# looks like a set of repeats. Anchored at the shortest member, a class
# is what it says it is -- frames of one length, give or take a pair.
_LENGTH_CLASS_SLACK = 4

# A press is one frame, or a handful of parts sent together: the test
# box's 8,407 codes produce splits of one class (plain repeats), two (a
# two-part air conditioner press) or three (Daikin's leader plus two
# blocks plus a tail), and never more. More than three classes, or more
# frames than any remote sends in one capture, means the separator was
# not a separator and the split is fragments rather than repeats.
_MAX_FRAME_CLASSES = 3
_MAX_FRAME_LENGTHS = 4
_MAX_PLAUSIBLE_FRAMES = 12

# Two timings read the same when they are within the byte-hash bin's
# half-width, which is the tolerance HAIR already trusts to tell one
# button from another (const.py: N=20 collapses same-button captures at
# typical receiver jitter). The relative term is a floor-raiser for long
# timings only: a 4.5 ms NEC leader jitters by more than half a bin
# without meaning anything, and an absolute tolerance would invent a
# disagreement there.
_READING_SLACK = 0.2
_READING_FLOOR = PRONTO_BYTE_HASH_BIN // 2

# Beyond this many disagreeing positions the list stops being evidence
# and starts being a wall, so the message switches to a counted form.
_MAX_NAMED_POSITIONS = 8

# Why a code was not judged. These ride the receipt's coverage section
# and are localized in the reader's language like everything else.
DECLINE_UNPARSEABLE = "unparseable"
DECLINE_SINGLE_FRAME = "single-frame"
# Something in the code was shaped like a repeat boundary and could not
# be trusted as one. Distinct from single-frame on purpose: "this is one
# frame" is a claim, and where the timings will not say, the receipt has
# to say THAT instead of guessing (Mitsubishi Heavy, R1 follow-up).
DECLINE_SEPARATOR_UNCLEAR = "separator-unclear"
DECLINE_TOO_FEW_FRAMES = "too-few-frames"
DECLINE_PINNED_TO_RAW = "pinned-to-raw"
DECLINE_TOO_FEW_CODES = "too-few-codes"
DECLINE_NO_LATTICE = "no-lattice"
DECLINE_ROW_TOO_SHORT = "row-too-short"
DECLINE_NO_TEMPERATURE = "no-temperature"
JUDGED = "judged"


@dataclass(frozen=True)
class FrameVote:
    """The vote behind a repeat disagreement, shown rather than summarized.

    ``frames`` is how many repeats were compared, ``readings`` how many
    distinct things they said, and ``positions`` where inside the frame
    they parted company. Showing all three is the brief's own constraint:
    the person fitting and the shop reviewing both have to be able to
    judge the judgment.
    """

    frames: int
    readings: int
    positions: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "frames": self.frames,
            "readings": self.readings,
            "positions": list(self.positions),
        }


def _frames_at(pairs: list[tuple[int, int]], cut: float) -> list[list[int]]:
    """Split at ``cut`` and keep the frames long enough to be readings.

    Frames are compared mark to last mark. Every frame but the last one
    ends where its gap was removed; the last one keeps whatever trailer
    the capture happened to carry, which is a zero as often as not. That
    single element is an artefact of where the code stopped, never a
    reading, and leaving it on made a clean RC-5 remote's last repeat a
    frame of its own (bench 2026-08-22, four plucked candle codes).
    """
    timings: list[int] = []
    for mark, space in pairs:
        timings.append(mark)
        timings.append(-space)
    frames: list[list[int]] = []
    for frame in split_frames(timings, int(cut)):
        while frame and frame[-1] <= 0:
            frame = frame[:-1]
        if len(frame) >= _MIN_JUDGED_FRAME:
            frames.append(frame)
    return frames


def _reads_as_repeats(frames: list[list[int]]) -> bool:
    """Does this split look like a press, rather than like debris?

    The question a ratio cannot answer. A real separator cuts a capture
    into a press or a few presses: one length class, or two or three when
    the press itself has parts. A bit space mistaken for a separator cuts
    the SAME frame at every one-bit, and the giveaway is the shape of
    what comes out -- a spray of lengths in four classes or more, or more
    frames than any remote sends in one capture.

    Measured, not guessed: across 8,407 codes on the test box, every
    genuine split lands on one, two or three classes and at most ten
    frames (fitting integrity R1 bench, 2026-08-22).
    """
    if not frames or len(frames) > _MAX_PLAUSIBLE_FRAMES:
        return False
    classes = _length_classes(frames)
    if len(classes) > _MAX_FRAME_CLASSES:
        return False
    # And the classes have to be BALANCED, which is the part a ratio can
    # never see. Every part of a press arrives once per repeat, so two
    # presses of a two-part code give two classes of two, and Daikin's
    # leader, two blocks and tail give one, two and one. Debris does not
    # balance: cutting a frame at its one-bits gives six short pieces,
    # four middling and two long, and no amount of looking at the spaces
    # would have told you that.
    sizes = [len(members) for members in classes]
    if max(sizes) - min(sizes) > 1:
        return False
    # Last bar, and the one that catches what balance alone lets through:
    # a press has a FEW lengths in it, not a spectrum. Every genuine
    # split measured on the test box carries three distinct frame lengths
    # or fewer, jitter included; the fragments left by cutting a frame at
    # its one-bits run seven and up.
    return len({len(frame) for frame in frames}) <= _MAX_FRAME_LENGTHS


def _split_repeats(
    pairs: list[tuple[int, int]]
) -> tuple[list[list[int]], bool]:
    """This code's repeats, and whether a separator was doubted.

    The final space is excluded before anything is measured. It is the
    trailer by construction, it is always the longest space in the code,
    and leaving it in makes it the only step the search can find -- which
    is how a code with eight visible repeats reports one frame.

    The second return value is what stops the coverage line from lying.
    A code where nothing even looks like a separator is a single frame
    and says so. A code where something DOES look like one and cannot be
    trusted -- long spaces too common to be boundaries, or a split whose
    pieces are not repeats -- is a different fact, and reporting it as
    "one frame" would claim knowledge the check does not have.
    """
    spaces = [space for _mark, space in pairs[:-1] if space > 0]
    if len(spaces) < 4:
        return [], False
    ladder = sorted(set(spaces))
    limit = len(spaces) * _REPEAT_GAP_SHARE
    doubted = False
    for lower, upper in reversed(list(pairwise(ladder))):
        if upper < _REPEAT_GAP_FLOOR:
            break
        if upper / lower < _REPEAT_GAP_RATIO:
            # Long enough to be a boundary, not distinct enough from the
            # spaces below it to tell. Ambiguous with data rather than
            # gap-shaped, so it does not raise the doubt flag: an NEC
            # leader looks exactly like this on every single-frame code
            # in the corpus.
            continue
        if sum(1 for space in spaces if space >= upper) > limit:
            # Gap-shaped, but there are too many of them to be
            # separators. Mitsubishi Heavy's one-bit is this case: a 3.6
            # ms space that clears every bar except being common.
            doubted = True
            continue
        frames = _frames_at(pairs, (lower * upper) ** 0.5)
        if _reads_as_repeats(frames):
            return frames, doubted
        doubted = True
    return [], doubted


def _length_classes(frames: list[list[int]]) -> list[list[list[int]]]:
    """Frames grouped by length class, shortest class first.

    The class is what makes the comparison like with like, and that
    matters for more than jitter: several air conditioners send one press
    as two frames of DIFFERENT lengths with a pause between them, so a
    capture of two presses splits four ways as A B A B. Class the parts
    apart and each part is compared against its own kind, which is
    correct; class them together and every one of those codes reads as
    four frames that disagree (bench 2026-08-22, nine Mirror rows on the
    test box, all of them fine).
    """
    lengths = sorted({len(frame) for frame in frames})
    classes: list[list[int]] = [[lengths[0]]]
    for length in lengths[1:]:
        if length - classes[-1][0] <= _LENGTH_CLASS_SLACK:
            classes[-1].append(length)
        else:
            classes.append([length])
    return [
        [frame for frame in frames if len(frame) in set(sizes)]
        for sizes in classes
    ]


def _slack(*values: int) -> float:
    return max(_READING_FLOOR, max(abs(v) for v in values) * _READING_SLACK)


def _same_reading(left: list[int], right: list[int]) -> bool:
    if len(left) != len(right):
        return False
    for a, b in zip(left, right, strict=True):
        if (a < 0) != (b < 0):
            return False
        if abs(abs(a) - abs(b)) > _slack(a, b):
            return False
    return True


def _readings(frames: list[list[int]]) -> tuple[int, list[int]]:
    """How many distinct things the frames said, and which said which."""
    first_of: list[list[int]] = []
    sequence: list[int] = []
    for frame in frames:
        for index, known in enumerate(first_of):
            if _same_reading(frame, known):
                sequence.append(index)
                break
        else:
            first_of.append(frame)
            sequence.append(len(first_of) - 1)
    return len(first_of), sequence


def _alternating(sequence: list[int]) -> bool:
    """True when the readings run on a fixed cycle rather than at random.

    Some protocols alternate on purpose. Sharp sends a data frame and its
    inverse; a capture holding two of each is four frames and two
    readings, and it is correct. Noise does not repeat itself on a period,
    so a sequence that does is structure, and the comb abstains: reporting
    it would train people to ignore this check on exactly the families it
    is safest on.
    """
    total = len(sequence)
    if len(set(sequence)) < 2:
        return False
    for period in range(2, total // 2 + 1):
        if total % period:
            continue
        if len(set(sequence[:period])) != period:
            continue
        if all(sequence[i] == sequence[i % period] for i in range(total)):
            return True
    return False


def _disagreeing_positions(frames: list[list[int]]) -> tuple[int, ...]:
    """Timing offsets where the frames do not read the same."""
    span = min(len(frame) for frame in frames)
    positions: list[int] = []
    for index in range(span):
        column = [frame[index] for frame in frames]
        if len({value < 0 for value in column}) > 1:
            positions.append(index)
            continue
        widths = [abs(value) for value in column]
        if max(widths) - min(widths) > _slack(*column):
            positions.append(index)
    return tuple(positions)


def _repeat_reading(pronto: str) -> tuple[str, FrameVote | None]:
    """Judge one code's repeats: (outcome, vote when they disagree).

    The outcome is what coverage records. "Nobody looked" and "looked and
    found nothing" are different facts about a code, and the whole point
    of the coverage section is that a reader can tell them apart.
    """
    pairs = _pairs(pronto)
    if not pairs:
        return DECLINE_UNPARSEABLE, None
    frames, doubted = _split_repeats(pairs)
    if not frames:
        if doubted:
            return DECLINE_SEPARATOR_UNCLEAR, None
        return DECLINE_SINGLE_FRAME, None
    if len(frames) < _MIN_CLUSTER_FRAMES:
        return DECLINE_TOO_FEW_FRAMES, None
    judged = False
    for members in _length_classes(frames):
        if len(members) < _MIN_CLUSTER_FRAMES:
            continue
        judged = True
        readings, sequence = _readings(members)
        if readings < 2 or _alternating(sequence):
            continue
        return JUDGED, FrameVote(
            frames=len(members),
            readings=readings,
            positions=_disagreeing_positions(members),
        )
    return (JUDGED if judged else DECLINE_TOO_FEW_FRAMES), None


def frame_disagreement(pronto: str) -> FrameVote | None:
    """The vote when a code's own repeats disagree, else None.

    Public because the check runs at capture time too, while the person
    is still holding the remote and can simply press the button again
    (design plan 1a). Same code, same answer, one implementation.
    """
    return _repeat_reading(pronto)[1]


def _repeat_findings(
    rows: list[tuple[str, str]], coverage: Coverage
) -> list[Finding]:
    findings: list[Finding] = []
    for key, pronto in rows:
        outcome, vote = _repeat_reading(pronto)
        if outcome != JUDGED:
            coverage.declined(CHECK_FRAME_DISAGREEMENT, outcome)
            continue
        coverage.judged(CHECK_FRAME_DISAGREEMENT, key)
        if vote is None:
            continue
        named = vote.positions[:_MAX_NAMED_POSITIONS]
        params = {
            "frames": str(vote.frames),
            "readings": str(vote.readings),
            "positions": ", ".join(str(p) for p in named),
        }
        message = "comb.frame_disagreement"
        if not vote.positions:
            # Every timing they share reads the same and they are still
            # different lengths, so the repeats lost or gained edges at
            # the ends. Naming positions here would name none of them.
            message = "comb.frame_disagreement_lengths"
            params.pop("positions")
        elif len(vote.positions) > len(named):
            message = "comb.frame_disagreement_many"
            params["count"] = str(len(vote.positions))
        findings.append(Finding(
            check=CHECK_FRAME_DISAGREEMENT, keys=[key],
            message=message, params=params,
        ))
    return findings


# ---------------------------------------------------------------------------
# The field tier: what the frame SAYS against what the cell CLAIMS
# ---------------------------------------------------------------------------
#
# Release two, and the answer to the WigShop's second case. Every other
# check in this module is protocol-blind on purpose; this one is the
# exception that earns itself, because a lattice can be structurally
# flawless and still send T+1 down one whole column, and no amount of
# comparing codes to each other sees that.
#
# The rules the tier holds itself to, all four load bearing:
#
# - Only fields the map marks RATIFIED are checked. Provisional and
#   unratified fields are coverage. ZHLT01's mode vocabulary is the
#   worked example: the Komeco lattice follows the minority reading, so
#   sweeping a provisional vocabulary would bury 52 real findings under
#   hundreds of false ones.
# - Temperature invariance is decided per mode AND, where the map says
#   `file_dependent`, per WIG: if the temperature field moves across
#   that mode's own cells here, check it; if it is frozen, count the
#   cells as coverage. Skipping outright misses whole shifted columns;
#   checking outright invents them.
# - A coordinate the map cannot express -- a label outside its
#   vocabulary, a temperature outside its domain -- is coverage. The
#   sweep never guesses at what a cell "probably" means.
# - Nothing here transmits, re-encodes or repairs. It reads.

# Which cell coordinate answers which map field.
_FIELD_COORDINATE = {
    "temperature": "temp",
    "mode": "mode",
    "fan_speed": "fan",
    "swing": "swing",
}

_POWER_FIELD = "power"


@dataclass(frozen=True)
class _Code:
    """One code of a wig, with whatever the file claims about it."""

    key: str
    pronto: str
    coordinates: dict[str, Any] = field(default_factory=dict)


def _matrix_codes(matrix: ClimateMatrix) -> list[_Code]:
    codes = [
        _Code(
            key=cell_key(cell),
            pronto=cell.pronto,
            coordinates={
                "mode": cell.mode, "fan": cell.fan, "swing": cell.swing,
                "temp": cell.temp, _POWER_FIELD: "on",
            },
        )
        for cell in matrix.cells
    ]
    codes.append(_Code(key="off", pronto=matrix.off,
                       coordinates={_POWER_FIELD: "off"}))
    if matrix.on is not None:
        codes.append(_Code(key="on", pronto=matrix.on,
                           coordinates={_POWER_FIELD: "on"}))
    return codes


# A family has to CARRY the wig, not merely appear in it. The bench
# found a 547-code Fujitsu remote in which exactly one code satisfied
# GREE's bit count and identity bytes -- a coincidence, at that width,
# is close to inevitable -- and on a first-code-wins rule that one
# accident named the family for the whole file and then filed findings
# from it. A real family reads most of its own wig: on the test box the
# genuine ones sit between half and all of their codes, and the
# coincidence sat at one in five hundred. Anything under a quarter is
# treated as noise and the wig reports as unidentified, which is the
# honest answer and the one that files nothing.
_FAMILY_SHARE = 0.25
_FAMILY_MINIMUM = 2


def _read_family(
    codes: list[_Code], coverage: Coverage
) -> tuple[Any, dict[str, Any]]:
    """Identify the family by vote, then read every code with its map.

    Two passes, and the first one only votes. Every code is offered to
    the whole library, the winner is the family most of them claim, and
    a candidate that cannot clear ``_FAMILY_SHARE`` of the wig is
    rejected outright rather than promoted by being first.

    The second pass re-reads under the winner via ``prefer``, so a code
    that could be read two ways is read the way the rest of the wig is.
    A cell that stops identifying there is declined on its own merits
    rather than assumed.
    """
    maps = field_readers.library()
    first: dict[str, Any] = {}
    votes: Counter[str] = Counter()
    for code in codes:
        reading = field_readers.read_code(code.pronto, maps)
        first[code.key] = reading
        if reading.identified and reading.protocol_id:
            votes[reading.protocol_id] += 1

    protocol: str | None = None
    rejected: dict[str, int] = {}
    if votes:
        leader, count = votes.most_common(1)[0]
        if count >= _FAMILY_MINIMUM \
                and count >= len(codes) * _FAMILY_SHARE:
            protocol = leader
        else:
            rejected = dict(votes)

    chosen = None
    for candidate in maps:
        if candidate.protocol_id == protocol:
            chosen = candidate
            break

    readings: dict[str, Any] = {}
    declined: Counter[str] = Counter()
    for code in codes:
        reading = first[code.key]
        if protocol is None:
            declined[field_readers.NO_MAP] += 1
            continue
        if reading.protocol_id != protocol:
            reading = field_readers.read_code(
                code.pronto, maps, prefer=protocol)
        if reading.identified and reading.protocol_id == protocol:
            readings[code.key] = reading
        else:
            declined[reading.declined or field_readers.NO_MAP] += 1

    coverage.protocol = {
        "id": protocol,
        "codes": len(codes),
        "readable": len(readings),
        "declined": dict(declined),
    }
    if rejected:
        # Named rather than dropped: "one code in this remote looked
        # like GREE" is worth a reader's second of attention, and
        # silence about it would leave the unmapped line looking like
        # nothing was ever a candidate.
        coverage.protocol["rejected"] = rejected
    return chosen, readings


def _temperature_moves(
    field_map: Any, readings: dict[str, Any], codes: list[_Code]
) -> dict[str, bool]:
    """Per mode: does the temperature FIELD actually move in this wig?

    The third state of ``mode_traits`` (schema v0.2), and the reason it
    exists. ZHLT01's `fan_only` is frozen in two files of its family and
    carries a real setpoint in two others, so the map cannot say and the
    wig can. Frozen means the cells are coverage; moving means they are
    checked.
    """
    spec = field_map.field_named("temperature")
    if spec is None:
        return {}
    seen: dict[str, set[int]] = {}
    for code in codes:
        reading = readings.get(code.key)
        mode = code.coordinates.get("mode")
        if reading is None or mode is None \
                or code.coordinates.get("temp") is None:
            continue
        value = field_readers.read_field(reading, spec)
        if value is not None:
            seen.setdefault(mode, set()).add(value)
    return {mode: len(values) > 1 for mode, values in seen.items()}


def _skip_reason(
    spec: Any, mode_spec: Any, code: _Code, moves: dict[str, bool]
) -> str | None:
    """Why this field is not comparable on this code, or None."""
    if not spec.ratified:
        return field_readers.NOT_RATIFIED
    if not field_readers.applies(spec, code.coordinates):
        return field_readers.NOT_APPLICABLE
    mode = code.coordinates.get("mode")
    if spec.name == "temperature" and mode_spec is not None:
        trait = field_readers.mode_trait(mode_spec, mode, "temp")
        if trait == "invariant":
            return field_readers.TEMP_INVARIANT
        # A mode the map never named is treated as file_dependent: the
        # map cannot vouch for it, so the wig's own behaviour decides.
        if trait != "varies" and not moves.get(mode or "", False):
            return field_readers.TEMP_FROZEN
    if spec.name == "fan_speed" and mode_spec is not None \
            and field_readers.mode_trait(mode_spec, mode, "fan") == "forced":
        return field_readers.FAN_FORCED
    return None


def _field_findings(
    codes: list[_Code], coverage: Coverage, labelled: bool
) -> list[Finding]:
    """Compare every readable code's fields to what its label claims.

    A CODE THE STRUCTURAL TIER ALREADY FLAGGED IS STILL READ (owner
    ruling, 2026-08-23). The sweep does not consult the structural
    verdict and does not skip a code because `malformed` or
    `frame-shape` reached it first. Deliberate, on three grounds.

    Findings never block, so a structural finding is not a disposal --
    the code is still in the file, the device will still send it, and
    what it says is still worth knowing. The two tiers also answer
    different questions: `malformed` says a capture is the wrong SHAPE
    for its neighbours, which on a multi-frame family can be true of a
    trailing frame while the payload frame reads perfectly, and that is
    exactly where a shifted setpoint hides. And the receipt carries
    every finding on a key side by side, so a reader sees a cell that
    is both short AND lying rather than only the first thing that hit
    it -- which is the whole picture, and the more useful one.

    The tier still declines the code it genuinely cannot read: a frame
    whose pulses fall outside the map's own windows fails
    identification and lands in coverage as `unreadable-frame`. That is
    a different judgement from "somebody else already complained".
    """
    field_map, readings = _read_family(codes, coverage)
    if field_map is None:
        coverage.declined(
            CHECK_FIELD_MISMATCH, field_readers.NO_MAP, len(codes))
        coverage.declined(
            CHECK_FRAME_INTEGRITY, field_readers.NO_MAP, len(codes))
        return []

    findings: list[Finding] = []
    mode_spec = field_map.field_named("mode")
    moves = _temperature_moves(field_map, readings, codes)
    protocol = field_map.protocol_id

    for code in codes:
        reading = readings.get(code.key)
        if reading is None:
            coverage.declined(CHECK_FIELD_MISMATCH, field_readers.UNREADABLE)
            coverage.declined(CHECK_FRAME_INTEGRITY, field_readers.UNREADABLE)
            continue

        # Integrity first: it needs no labels at all, which is why it
        # runs on flat wigs too where the sweep below cannot.
        judged_rule = False
        for rule in field_map.integrity:
            if not rule.ratified:
                coverage.declined(CHECK_FRAME_INTEGRITY,
                                  field_readers.NOT_RATIFIED)
                continue
            holds = field_readers.check_integrity(reading, rule)
            if holds is None:
                coverage.declined(CHECK_FRAME_INTEGRITY,
                                  field_readers.RULE_UNEVALUATED)
                continue
            judged_rule = True
            if not holds:
                findings.append(Finding(
                    check=CHECK_FRAME_INTEGRITY, keys=[code.key],
                    message="comb.frame_integrity",
                    params={"protocol": protocol,
                            "rule": f"comb.rule.{rule.type}"},
                ))
        if judged_rule:
            coverage.judged(CHECK_FRAME_INTEGRITY, code.key)

        if not labelled:
            coverage.declined(CHECK_FIELD_MISMATCH, field_readers.NO_LABELS)
            continue

        judged_field = False
        for spec in field_map.fields:
            coordinate_name = _FIELD_COORDINATE.get(spec.name)
            if spec.name == _POWER_FIELD:
                coordinate = code.coordinates.get(_POWER_FIELD)
            elif coordinate_name is None:
                coverage.field_declined(spec.name, field_readers.NO_COORDINATE)
                continue
            else:
                coordinate = code.coordinates.get(coordinate_name)
            if coordinate is None:
                coverage.field_declined(spec.name, field_readers.NO_COORDINATE)
                continue
            reason = _skip_reason(spec, mode_spec, code, moves)
            if reason is not None:
                coverage.field_declined(spec.name, reason)
                continue
            expected = field_readers.expected_value(spec, coordinate)
            if expected is None:
                coverage.field_declined(spec.name, field_readers.UNKNOWN_LABEL)
                continue
            value = field_readers.read_field(reading, spec)
            if value is None:
                coverage.field_declined(spec.name, field_readers.FIELD_ABSENT)
                continue
            coverage.field_judged(spec.name)
            judged_field = True
            if value != expected:
                findings.append(Finding(
                    check=CHECK_FIELD_MISMATCH, keys=[code.key],
                    message="comb.field_mismatch",
                    params={
                        "field": f"comb.field.{spec.name}",
                        "protocol": protocol,
                        "expected": f"0x{expected:02X}",
                        "read": f"0x{value:02X}",
                    },
                ))
        if judged_field:
            coverage.judged(CHECK_FIELD_MISMATCH, code.key)

    return findings


def _outlier_findings(shapes: dict[str, tuple[int, ...]]) -> list[Finding]:
    """Frame shape on a FLAT remote: gross outliers only.

    Strict shape equality is right for a lattice and wrong here, and the
    difference is the encoding rather than the data quality. Pulse-distance
    protocols (NEC, Samsung, Kaseikyo -- everything in the census, because
    the census is air conditioners) spend one mark-space pair per bit, so
    every command of one device is the same length and a cell two timings
    short really is malformed. Bi-phase protocols (RC-5, RC-6) merge
    adjacent same-level half-bits, so pair count is a function of the
    COMMAND'S BITS: a real RC-5 remote emits 10, 11 and 12-pair codes all
    day and none of them is broken. A live specimen made the point -- a
    twelve-button RC-5 candle remote where strict modal matching would have
    condemned five good buttons.

    So on flat wigs the bar is a code that cannot be the same protocol as
    its neighbours: twice the median length or half of it, or a different
    number of frames entirely. That still catches what matters -- the same
    specimen carries a 34-pair SAMSUNG32 frame among 11-pair RC-5 ones,
    which is a 3x outlier and exactly the sort of foreign code that ends
    up in a wig by accident.
    """
    totals = sorted(sum(shape) for shape in shapes.values())
    median = totals[len(totals) // 2]
    if median <= 0:
        return []
    frame_counts = Counter(len(shape) for shape in shapes.values())
    modal_frames, modal_frames_n = frame_counts.most_common(1)[0]

    findings: list[Finding] = []
    for key, shape in sorted(shapes.items()):
        total = sum(shape)
        if total >= median * 2 or total * 2 <= median:
            findings.append(Finding(
                check=CHECK_FRAME_SHAPE, keys=[key],
                message="comb.frame_outlier",
                params={"pairs": str(total), "median": str(median)},
            ))
        elif len(shape) != modal_frames and modal_frames_n > len(shapes) / 2:
            findings.append(Finding(
                check=CHECK_FRAME_SHAPE, keys=[key],
                message="comb.frame_count",
                params={"frames": str(len(shape)),
                        "expected": str(modal_frames)},
            ))
    return findings


def _shape_findings(
    rows: list[tuple[str, str]], strict: bool, coverage: Coverage | None = None
) -> list[Finding]:
    """Frame-shape uniformity across every code in one wig.

    Every cell of one device sends the same protocol, so every cell should
    split into the same number of frames with the same number of timings in
    each. The modal shape is the wig's own definition of normal -- no
    protocol knowledge, no reference table, and it works on vendors nobody
    has ever written a decoder for.

    ``strict`` is on for a matrix, where the census validated exact shape
    matching across 2,709 cells, and off for a flat remote, where a
    bi-phase encoding makes exact matching produce false positives on
    perfectly good buttons (see ``_outlier_findings``).
    """
    shapes: dict[str, tuple[int, ...]] = {}
    for key, pronto in rows:
        pairs = _pairs(pronto)
        if pairs:
            shapes[key] = _frame_lengths(pairs)
        elif coverage is not None:
            coverage.declined(CHECK_FRAME_SHAPE, DECLINE_UNPARSEABLE)
    if len(shapes) < 3:
        # Too few codes to have a "normal". Two signals that disagree tell
        # you nothing about which one is wrong.
        if coverage is not None:
            coverage.declined(
                CHECK_FRAME_SHAPE, DECLINE_TOO_FEW_CODES, len(shapes))
        return []
    if coverage is not None:
        for key in shapes:
            coverage.judged(CHECK_FRAME_SHAPE, key)

    if not strict:
        return _outlier_findings(shapes)

    modal, modal_n = Counter(shapes.values()).most_common(1)[0]
    if modal_n < 2:
        return []

    findings: list[Finding] = []
    for key, shape in shapes.items():
        if shape == modal:
            continue
        # One extra single-pair frame on the end: the classic trailing
        # burst. Cosmetically wrong, functionally harmless, worth saying
        # because it means the capture was not clean.
        if shape[:-1] == modal and shape[-1] == 1:
            findings.append(Finding(
                check=CHECK_STRAY_BURST, keys=[key],
                message="comb.stray_burst",
            ))
            continue
        if len(shape) == len(modal):
            short = [
                (i, modal[i] - shape[i])
                for i in range(len(shape)) if shape[i] < modal[i]
            ]
            if short and all(shape[i] <= modal[i] for i in range(len(shape))):
                index, deficit = short[0]
                findings.append(Finding(
                    check=CHECK_MALFORMED, keys=[key],
                    message="comb.frame_short",
                    params={"frame": str(index),
                            "timings": str(deficit * 2)},
                ))
                continue
        if len(shape) < len(modal):
            findings.append(Finding(
                check=CHECK_MALFORMED, keys=[key],
                message="comb.frame_missing",
                params={"missing": str(len(modal) - len(shape))},
            ))
            continue
        findings.append(Finding(
            check=CHECK_FRAME_SHAPE, keys=[key],
            message="comb.frame_shape",
            params={"pairs": str(sum(shape)),
                    "expected": str(sum(modal))},
        ))
    return findings


# ---------------------------------------------------------------------------
# Matrix checks
# ---------------------------------------------------------------------------


def _temp_str(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _branch_findings(
    matrix: ClimateMatrix, coverage: Coverage | None = None
) -> list[Finding]:
    """Partial row collapse: the check that finds the dangerous class.

    Within one (mode, fan, swing) branch, sorted by temperature: if EVERY
    cell shares one code the device ignores temperature there and that is
    legitimate and load bearing. If the row varies at all and two adjacent
    temperatures still collide, the row has proved the device responds and
    then contradicted itself. That single discriminator caught all five
    duplicate defects across 2,709 census cells with zero false positives.
    """
    branches: dict[
        tuple[str, str | None, str | None], list[tuple[float, str, str]]
    ] = {}
    for cell in matrix.cells:
        if cell.temp is None:
            if coverage is not None:
                coverage.declined(
                    CHECK_DUPLICATED_NEIGHBOUR, DECLINE_NO_TEMPERATURE)
            continue
        branches.setdefault((cell.mode, cell.fan, cell.swing), []).append(
            (cell.temp, normalized_pronto(cell.pronto), cell_key(cell))
        )

    findings: list[Finding] = []
    for cells in branches.values():
        if len(cells) < 3:
            # Two temperatures sharing a code is as likely to be a
            # two-step device as a defect. Not enough row to judge.
            if coverage is not None:
                coverage.declined(
                    CHECK_DUPLICATED_NEIGHBOUR, DECLINE_ROW_TOO_SHORT,
                    len(cells))
            continue
        if coverage is not None:
            for _t, _code, key in cells:
                coverage.judged(CHECK_DUPLICATED_NEIGHBOUR, key)
        cells.sort(key=lambda c: c[0])
        codes = {code for _t, code, _k in cells}
        if len(codes) == 1:
            continue  # whole-row collapse: correct, never flagged
        for i in range(len(cells) - 1):
            (t_a, code_a, key_a) = cells[i]
            (t_b, code_b, key_b) = cells[i + 1]
            if code_a == code_b:
                findings.append(Finding(
                    check=CHECK_DUPLICATED_NEIGHBOUR,
                    keys=[key_b, key_a],
                    message="comb.duplicated_neighbour",
                    params={"other": _temp_str(t_a),
                            "temp": _temp_str(t_b)},
                ))
    return findings


def _completeness_findings(matrix: ClimateMatrix) -> list[Finding]:
    """Holes in a temperature run, and states nothing advertises.

    Deliberately NARROW on the missing side: the obvious reading of
    "every advertised combination has a cell" is the full cross product of
    modes, fans, swings and temperatures, and real matrices are SPARSE by
    construction -- the census found depth varying per BRANCH and 158
    explicit nulls. Cross-product checking would bury a real hole under
    hundreds of combinations that were never meant to exist. What IS
    unambiguous is a gap inside a run somebody did capture: Sharp's
    auto/auto goes 18, 19, 21, 22, and Home Assistant will happily offer
    the user the 20 that does nothing.
    """
    findings: list[Finding] = []
    step = matrix.precision if matrix.precision > 0 else 1.0

    branches: dict[
        tuple[str, str | None, str | None], list[float]
    ] = {}
    for cell in matrix.cells:
        if cell.temp is not None:
            branches.setdefault(
                (cell.mode, cell.fan, cell.swing), []
            ).append(cell.temp)

    for (mode, fan, swing), temps in branches.items():
        if len(temps) < 3:
            continue
        present = sorted(set(temps))
        want = present[0]
        missing: list[str] = []
        # Walk the run in the file's own precision. Tolerance is a tenth
        # of a step, so float drift on 0.5C matrices cannot invent holes.
        while want < present[-1] - step / 10:
            if not any(abs(want - t) < step / 10 for t in present):
                missing.append(_temp_str(want))
            want += step
        if missing:
            label = "/".join(p for p in (mode, fan, swing) if p)
            findings.append(Finding(
                check=CHECK_MISSING_CELL,
                keys=[f"{label}/{m}" for m in missing],
                message="comb.missing_cell",
                params={"branch": label,
                        "temps": ", ".join(missing)},
            ))

    # Vocabulary the header never declares. Only checked when the header
    # declares anything at all -- plenty of hand-rolled files leave the
    # lists empty, and an empty list is "unstated", not "nothing allowed".
    if matrix.modes:
        stray = sorted({
            c.mode for c in matrix.cells if c.mode not in matrix.modes
        })
        if stray:
            findings.append(Finding(
                check=CHECK_STRAY_CELL, keys=stray,
                message="comb.stray_mode",
                params={"values": ", ".join(stray)},
            ))
    if matrix.fan_modes:
        stray = sorted({
            c.fan for c in matrix.cells
            if c.fan is not None and c.fan not in matrix.fan_modes
        })
        if stray:
            findings.append(Finding(
                check=CHECK_STRAY_CELL, keys=stray,
                message="comb.stray_fan",
                params={"values": ", ".join(stray)},
            ))
    return findings


def _coordinate_findings(matrix: ClimateMatrix) -> list[Finding]:
    """One state, one cell. Two cells at the same coordinates mean the
    lookup is a coin toss, whichever code the entity happens to find
    first."""
    seen: dict[str, int] = {}
    for cell in matrix.cells:
        key = cell_key(cell)
        seen[key] = seen.get(key, 0) + 1
    return [
        Finding(
            check=CHECK_COORDINATE_COLLISION, keys=[key],
            message="comb.coordinate_collision", params={"count": str(n)},
        )
        for key, n in sorted(seen.items()) if n > 1
    ]


def _duplicate_label_findings(wig: Wig) -> list[Finding]:
    """Distinct names, one payload. ADVISORY, forever, by owner ruling.

    A flat file has no lattice to prove intent, and same-code-different-
    label is genuinely correct on toggle devices, where "Power On" and
    "Power Off" are one button. Reported so a human can look; never
    merged, never counted as a suspect.
    """
    groups: dict[str, list[str]] = {}
    for sig in wig.signals:
        groups.setdefault(normalized_pronto(sig.pronto), []).append(sig.alias)
    return [
        Finding(
            check=CHECK_DUPLICATE_LABELS, keys=list(aliases),
            message="comb.duplicate_labels",
            params={"aliases": ", ".join(aliases)},
        )
        for aliases in groups.values()
        if len(aliases) > 1 and len(set(aliases)) > 1
    ]


# Buttons whose whole job is to step a value. A ditto on one of these
# repeats the step, so a high count is a behaviour choice worth
# mentioning rather than a defect. Token match against the alias, using
# the same lowercase-token approach the comb already takes elsewhere.
_RAMP_TOKENS = frozenset({
    "vol", "volume", "ch", "channel", "bright", "brightness", "dim",
    "temp", "temperature", "speed", "level", "zoom", "track", "seek",
    "scroll", "tune", "warmer", "cooler", "up", "down", "plus", "minus",
})

# Above this, a ramp button's ditto count stops looking like grammar and
# starts looking like a decision. DEFAULT_REPEAT_COUNT is 1 and matches
# NEC spec for a single tap, so the threshold sits well clear of normal.
_RAMP_DITTO_THRESHOLD = 4


def _bypass_ditto_findings(wig: Wig) -> list[Finding]:
    """Both knobs set on one signal (owner ruling: mutually exclusive).

    A raw blob has no ditto grammar. Only the encoder renders a
    shortened repeat frame, so platform-level repetition of raw bytes is
    whole-blob repetition, which is send_count's job. HAIR's own
    exporter can never produce this pair; a hand-edited file can.
    """
    return [
        Finding(
            check=CHECK_BYPASS_WITH_DITTOS, keys=[sig.alias],
            message="comb.bypass_with_dittos",
            params={"count": str(sig.ditto_count)},
        )
        for sig in wig.signals
        if sig.bypass_protocol and sig.ditto_count
    ]


def _ramp_ditto_findings(wig: Wig) -> list[Finding]:
    """An unusually high ditto count on a button that steps a value."""
    findings = []
    for sig in wig.signals:
        if sig.ditto_count <= _RAMP_DITTO_THRESHOLD:
            continue
        tokens = {
            t for t in re.split(r"[^a-z0-9]+", sig.alias.lower()) if t
        }
        if tokens & _RAMP_TOKENS:
            findings.append(Finding(
                check=CHECK_RAMP_DITTOS, keys=[sig.alias],
                message="comb.ramp_dittos",
                params={"count": str(sig.ditto_count)},
            ))
    return findings


# ---------------------------------------------------------------------------
# The entry point
# ---------------------------------------------------------------------------


def comb_wig(wig: Wig) -> CombReport:
    """Every check, on any wig, in severity order.

    Runs on EVERY wig, not just converted ones (design Section 2): a
    HAIR-captured wig should pass by construction, so a failure there is a
    free diagnostic that something else is wrong.
    """
    findings: list[Finding] = []
    coverage = Coverage()
    # A bypassed signal is a deliberate repeat-train (Highlights, GH #78),
    # so it is excluded from the shape checks entirely -- and that means
    # BOTH halves: it is not judged, and it does not vote on what normal
    # looks like. Skipping only the judgement would leave kno-te's
    # seven-frame Power code in the population that decides the median for
    # a remote whose every other button is one frame, which would silence
    # one false positive and manufacture eight.
    #
    # The comb cannot have an opinion about a code somebody deliberately
    # pinned to raw, and should not pretend to.
    skipped = sorted(
        sig.alias for sig in wig.signals if sig.bypass_protocol
    )
    rows: list[tuple[str, str]] = [
        (sig.alias, sig.pronto)
        for sig in wig.signals
        if not sig.bypass_protocol
    ]
    coverage.declined(
        CHECK_FRAME_DISAGREEMENT, DECLINE_PINNED_TO_RAW, len(skipped))
    coverage.declined(
        CHECK_FRAME_SHAPE, DECLINE_PINNED_TO_RAW, len(skipped))
    if wig.climate is not None:
        # The matrix and its flat extras are different populations: a
        # 2,689-cell lattice plus three depth-0 buttons should not have
        # the buttons dragged into the lattice's modal shape, or into
        # its duplicate-label groups.
        cells = [(cell_key(c), c.pronto) for c in wig.climate.cells]
        cells.append(("off", wig.climate.off))
        if wig.climate.on is not None:
            cells.append(("on", wig.climate.on))
        findings += _shape_findings(cells, strict=True, coverage=coverage)
        findings += _branch_findings(wig.climate, coverage)
        findings += _completeness_findings(wig.climate)
        findings += _coordinate_findings(wig.climate)
        # The repeat check needs no population, so it runs on the flat
        # extras too: a matrix wig's depth-0 buttons are captures like
        # any other and can be just as noisy.
        coverage.codes = len(cells) + len(rows) + len(skipped)
        findings += _repeat_findings(cells + rows, coverage)
        # The field tier, on the lattice only: a flat row carries a
        # free-form name, not a coordinate, so there is nothing to check
        # its bytes against (design plan section 4).
        findings += _field_findings(
            _matrix_codes(wig.climate), coverage, labelled=True)
    else:
        findings += _shape_findings(rows, strict=False, coverage=coverage)
        findings += _duplicate_label_findings(wig)
        coverage.codes = len(rows) + len(skipped)
        findings += _repeat_findings(rows, coverage)
        coverage.declined(CHECK_DUPLICATED_NEIGHBOUR, DECLINE_NO_LATTICE)
        # Integrity rules need no labels, so a flat wig whose codes
        # identify under a map gets them anyway. The field-versus-label
        # sweep stays matrix-only and says so in coverage.
        findings += _field_findings(
            [_Code(key=alias, pronto=pronto) for alias, pronto in rows],
            coverage, labelled=False)
    # Recipe advisories run on BOTH kinds' flat signal lists: a matrix
    # wig's flat extras are ordinary signals and can carry either knob.
    findings += _bypass_ditto_findings(wig)
    findings += _ramp_ditto_findings(wig)

    order = {check: i for i, check in enumerate(SEVERITY_ORDER)}
    findings.sort(key=lambda f: (order.get(f.check, 99), f.keys[:1]))
    return CombReport(findings=findings, skipped=skipped, coverage=coverage)


# ---------------------------------------------------------------------------
# The stored receipt: writing it, reading it back
# ---------------------------------------------------------------------------

COMB_KEY = "comb"


def stamp_receipt(wig: Wig, report: CombReport, date: str) -> None:
    """Record a comb result on the wig, outside every canonical hash.

    ``wig.extra`` is preserved through parse and serialize by the format's
    unknown-key contract, and the canonical forms exclude it, so stamping a
    result can never move a wig's identity or invalidate a fitting. That is
    the whole reason combing is safe to run automatically at import.
    """
    wig.extra[COMB_KEY] = report.to_receipt(date)


def receipt_summary(wig: Wig) -> dict[str, Any] | None:
    """What the closet row needs to draw the comb glyph, or None.

    None means NO RECEIPT, which is not the same as clean: nobody has
    combed this wig, so the glyph stays plain grey and says so. A wig that
    was combed and came back empty also draws plain grey, and the two are
    told apart by the tooltip, not the colour (owner ruling CG3).
    """
    raw = wig.extra.get(COMB_KEY)
    if not isinstance(raw, dict):
        return None
    counts = raw.get("counts")
    counts = counts if isinstance(counts, dict) else {}
    suspects = raw.get("suspects")
    coverage = raw.get("coverage")
    return {
        # Absent on a version 1 receipt, and that absence is the honest
        # answer: a receipt written before coverage existed cannot say
        # what it did not look at, so the closet draws it as unknown
        # rather than inventing a clean bill.
        "coverage": coverage if isinstance(coverage, dict) else None,
        "suspects": suspects if isinstance(suspects, int) else 0,
        "date": raw.get("date"),
        "version": raw.get("version"),
        # Red versus yellow follows the taxonomy, not the count: one
        # duplicated neighbour outranks thirty-four malformed frames,
        # because it is the class the device answers and a human never
        # catches unaided.
        "dangerous": bool(counts.get(CHECK_DUPLICATED_NEIGHBOUR)),
        "counts": counts,
        # Rows the comb declined to judge because they are pinned to raw.
        "skipped": [k for k in raw.get("skipped") or [] if isinstance(k, str)],
    }


def suspect_findings(wig: Wig) -> dict[str, str]:
    """Row key -> the check class that flagged it, worst first.

    ``suspect_keys`` answers WHETHER a row is doubted; this answers
    WHY, which is what a marker's tooltip has to say. A bare "suspect"
    tells somebody there is a problem and nothing about which problem,
    and the comb already knows: it recorded the class.

    Findings are ordered worst-first in the receipt, so the first class
    to claim a key wins -- a row that is both a duplicated neighbour
    and an odd frame shape leads with the one that matters.
    """
    raw = wig.extra.get(COMB_KEY)
    if not isinstance(raw, dict):
        return {}
    findings = raw.get("findings")
    if not isinstance(findings, list):
        return {}
    bypassed = {sig.alias for sig in wig.signals if sig.bypass_protocol}
    out: dict[str, str] = {}
    for entry in findings:
        if not isinstance(entry, dict):
            continue
        check = entry.get("check")
        if check in ADVISORY_CHECKS or not isinstance(check, str):
            continue
        for key in entry.get("keys") or []:
            if isinstance(key, str) and key not in out \
                    and key not in bypassed:
                out[key] = check
    return out


def suspect_keys(wig: Wig) -> list[str]:
    """Row keys the stored receipt flagged, worst first, deduped.

    What the fitting session surfaces for proofing. ADVISORY findings are
    excluded: "same code, different names" is legitimate on a toggle
    remote and putting it in front of a fitter as something to prove
    would be noise.

    Reads the stored receipt rather than re-combing, because the session
    must not do lattice work on open -- and because a receipt is exactly
    the claim the closet glyph is already making.
    """
    raw = wig.extra.get(COMB_KEY)
    if not isinstance(raw, dict):
        return []
    findings = raw.get("findings")
    if not isinstance(findings, list):
        return []
    # A bypassed row is not a suspect. The comb never judged it, so there
    # is no doubt to surface -- and it reaches the fitting as an ordinary
    # checklist row rather than an advisory one (7.1).
    bypassed = {
        sig.alias for sig in wig.signals if sig.bypass_protocol
    }
    seen: list[str] = []
    for entry in findings:
        if not isinstance(entry, dict):
            continue
        if entry.get("check") in ADVISORY_CHECKS:
            continue
        for key in entry.get("keys") or []:
            if isinstance(key, str) and key not in seen \
                    and key not in bypassed:
                seen.append(key)
    return seen
