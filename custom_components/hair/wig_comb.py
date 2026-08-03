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
from typing import Any

from .const import PRONTO_GAP_THRESHOLD
from .wig_fitting import normalized_pronto
from .wig_format import ClimateMatrix, Wig, cell_key

# Bumped when a check changes what it reports, so a stored receipt can be
# read as "checked by a version that did not know about X".
COMB_VERSION = 1

# Findings are capped in the stored receipt (brief 5.2): a 2,689-cell
# Mitsubishi with 91 duplicate groups should not write a novel into the
# wig file. The count is always exact; the list is what truncates.
MAX_STORED_FINDINGS = 200

# --- check ids ------------------------------------------------------------
CHECK_MALFORMED = "malformed"
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
    CHECK_MALFORMED,
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
class CombReport:
    """What a check found, ready for a receipt or a dialog."""

    findings: list[Finding] = field(default_factory=list)
    # Row keys the comb declined to judge because they are pinned to raw
    # (Highlights, GH #78). Recorded so a reader can tell "nothing wrong
    # with this row" from "nobody looked at this row" -- the same
    # distinction the receipt itself draws between clean and absent.
    skipped: list[str] = field(default_factory=list)
    version: int = COMB_VERSION

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
    rows: list[tuple[str, str]], strict: bool
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
    if len(shapes) < 3:
        # Too few codes to have a "normal". Two signals that disagree tell
        # you nothing about which one is wrong.
        return []

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


def _branch_findings(matrix: ClimateMatrix) -> list[Finding]:
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
            continue
        branches.setdefault((cell.mode, cell.fan, cell.swing), []).append(
            (cell.temp, normalized_pronto(cell.pronto), cell_key(cell))
        )

    findings: list[Finding] = []
    for cells in branches.values():
        if len(cells) < 3:
            # Two temperatures sharing a code is as likely to be a
            # two-step device as a defect. Not enough row to judge.
            continue
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
    if wig.climate is not None:
        # The matrix and its flat extras are different populations: a
        # 2,689-cell lattice plus three depth-0 buttons should not have
        # the buttons dragged into the lattice's modal shape, or into
        # its duplicate-label groups.
        cells = [(cell_key(c), c.pronto) for c in wig.climate.cells]
        cells.append(("off", wig.climate.off))
        if wig.climate.on is not None:
            cells.append(("on", wig.climate.on))
        findings += _shape_findings(cells, strict=True)
        findings += _branch_findings(wig.climate)
        findings += _completeness_findings(wig.climate)
        findings += _coordinate_findings(wig.climate)
    else:
        findings += _shape_findings(rows, strict=False)
        findings += _duplicate_label_findings(wig)
    # Recipe advisories run on BOTH kinds' flat signal lists: a matrix
    # wig's flat extras are ordinary signals and can carry either knob.
    findings += _bypass_ditto_findings(wig)
    findings += _ramp_ditto_findings(wig)

    order = {check: i for i, check in enumerate(SEVERITY_ORDER)}
    findings.sort(key=lambda f: (order.get(f.check, 99), f.keys[:1]))
    return CombReport(findings=findings, skipped=skipped)


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
    return {
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
