"""Repeats of one press should be identical (fitting integrity, R1).

The check this file pins is the only one in the comb that compares a code
to ITSELF. Everything else asks whether a code fits its neighbours; this
asks whether one press agreed with itself, which is why it works on a
seven-button fan nobody has written a decoder for.

The safety cases are pinned first and deliberately, because a check that
cries wolf on Sharp or on NEC dittos is worse than no check at all: people
learn to ignore it, and then it is silent about the Dreo.

- **Sharp sends a data frame and its inverse.** Two frames, deliberately
  different, and four frames of an alternating capture are a cycle rather
  than noise. Both stay silent.
- **NEC dittos are not readings.** A held button's repeat markers are two
  or three timings long; judging them against the main frame would flag
  every held capture in the world.
- **A single-frame code cannot disagree with itself**, and says so in
  coverage instead of passing quietly.

The acceptance fixtures are the WigShop's Dreo file (real noise, CC0) and
its Komeco lattice (1,156 structurally flawless cells, the false-positive
guard). See ``fixtures/wigs/README.md``.
"""
from __future__ import annotations

import json
from pathlib import Path

from custom_components.hair.wig_comb import (
    ADVISORY_CHECKS,
    CHECK_FRAME_DISAGREEMENT,
    COMB_VERSION,
    DECLINE_PINNED_TO_RAW,
    DECLINE_SINGLE_FRAME,
    DECLINE_TOO_FEW_FRAMES,
    comb_wig,
    frame_disagreement,
    receipt_summary,
    stamp_receipt,
    suspect_keys,
)
from custom_components.hair.wig_format import Wig, WigSignal, parse_wig

WIGS = Path(__file__).parent / "fixtures" / "wigs"
DREO = WIGS / "dreo-fan-dr-haf004s-perfect-fit.wig.json"
KOMECO = WIGS / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json"

# A repeat gap in the Dreo's own idiom: about 8 ms, well clear of the bit
# spaces and nowhere near PRONTO_GAP_THRESHOLD, which is exactly the case
# a fixed cut cannot see.
GAP = 0x0140
TRAILER = 0x09C4


def _pronto(frames: list[list[tuple[int, int]]]) -> str:
    """A Pronto code carrying ``frames`` verbatim, gaps between them."""
    pairs: list[tuple[int, int]] = []
    for index, frame in enumerate(frames):
        last = len(frame) - 1
        closer = TRAILER if index == len(frames) - 1 else GAP
        for position, (mark, space) in enumerate(frame):
            pairs.append((mark, closer if position == last else space))
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


def _frame(bits: str, *, short: int = 0x0010, long: int = 0x002E) -> list:
    """One pulse-width frame: bit width in the mark, constant space."""
    return [((long if bit == "1" else short), 0x0010) for bit in bits]


def _repeats(bits: str, times: int) -> str:
    return _pronto([_frame(bits) for _ in range(times)])


def _wig(codes: dict[str, str], **kw) -> Wig:
    return Wig(
        name="Remote",
        signals=[
            WigSignal(alias=alias, pronto=pronto, **kw)
            for alias, pronto in codes.items()
        ],
    )


def _load(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


# ---------------------------------------------------------------------------
# The safety cases, first
# ---------------------------------------------------------------------------


class TestItStaysSilentWhereItShould:
    def test_identical_repeats_say_nothing(self):
        assert frame_disagreement(_repeats("110110010000", 6)) is None

    def test_receiver_jitter_is_not_a_disagreement(self):
        """Every timing wobbles a little on the way through a receiver.
        Half a byte-hash bin is the tolerance HAIR already trusts to tell
        one button from another, and the check inherits it."""
        clean = _frame("110110010000")
        jittered = [(mark + 3, space - 2) for mark, space in clean]
        wobbled = [(mark - 4, space + 3) for mark, space in clean]
        code = _pronto([clean, jittered, wobbled, clean, jittered])
        assert frame_disagreement(code) is None

    def test_a_long_leader_may_jitter_by_more_than_a_bin(self):
        """A 4.5 ms leader wobbling by 8 percent moves further than half a
        bin without meaning anything. An absolute tolerance would invent a
        disagreement on every NEC capture in the catalog."""
        body = _frame("10110010")
        lead = [(0x0154, 0x00AA)]
        frames = [
            lead + body,
            [(0x0164, 0x00B4), *body],
            [(0x0148, 0x00A0), *body],
            lead + body,
        ]
        assert frame_disagreement(_pronto(frames)) is None

    def test_sharp_style_pair_is_two_frames_and_stays_quiet(self):
        """Data frame then its inverse. Two frames that disagree tell you
        nothing about which one is wrong."""
        code = _pronto([_frame("10110010"), _frame("01001101")])
        assert frame_disagreement(code) is None

    def test_sharp_style_alternation_is_a_cycle_not_noise(self):
        """Four frames, two readings, on a fixed period. Noise does not
        repeat itself; structure does, and the comb abstains."""
        data = _frame("10110010")
        inverted = _frame("01001101")
        code = _pronto([data, inverted, data, inverted])
        assert frame_disagreement(code) is None

    def test_nec_dittos_are_not_readings(self):
        """A held NEC button sends a full frame and then repeat markers
        two timings long. They are not repeats of the reading and must not
        be judged against it."""
        main = [(0x0154, 0x00AA), *_frame("1011001010110010")]
        ditto = [(0x0154, 0x0055)]
        code = _pronto([main, ditto, ditto, ditto])
        assert frame_disagreement(code) is None

    def test_a_two_part_press_compares_part_against_part(self):
        """Several air conditioners send one press as two frames of
        different lengths with a pause between them, so a capture of two
        presses splits four ways as A B A B. The length class is what
        keeps the parts apart; without it every code of that shape reads
        as four frames that disagree. Nine Mirror rows on the test box
        did exactly that before the class narrowed (bench 2026-08-22)."""
        head = _frame("101100101011001010110010101100101")
        tail = _frame("11001010110010101100101011001")
        code = _pronto([head, tail, head, tail])
        assert frame_disagreement(code) is None

    def test_a_trailing_zero_is_not_a_reading(self):
        """The last frame keeps whatever trailer the capture carried,
        which is a zero as often as not. Four plucked RC-5 candle codes
        on the test box read as three frames plus a fourth of its own
        length until that element was trimmed."""
        frame = _frame("10110010101")
        pairs: list[tuple[int, int]] = []
        for index in range(4):
            for position, (mark, space) in enumerate(frame):
                last = position == len(frame) - 1
                closer = (0 if index == 3 else GAP) if last else space
                pairs.append((mark, closer))
        words = [0x0000, 0x006D, len(pairs), 0x0000]
        for mark, space in pairs:
            words += [mark, space]
        assert frame_disagreement(" ".join(f"{w:04X}" for w in words)) is None

    def test_a_single_frame_code_cannot_disagree_with_itself(self):
        assert frame_disagreement(_pronto([_frame("110110010000")])) is None

    def test_an_unparseable_code_is_not_the_combs_business(self):
        assert frame_disagreement("not pronto at all") is None


# ---------------------------------------------------------------------------
# The vote
# ---------------------------------------------------------------------------


class TestItShowsTheVote:
    def test_one_frame_out_of_five_is_a_finding_with_its_vote(self):
        code = _pronto([
            _frame("110110010000"),
            _frame("110110010000"),
            _frame("110110011000"),
            _frame("110110010000"),
            _frame("110110010000"),
        ])
        vote = frame_disagreement(code)
        assert vote is not None
        assert vote.frames == 5
        assert vote.readings == 2
        # Bit 8 is the one that moved; a pulse-width frame spends one
        # mark-space pair per bit, so it is timing index 16.
        assert vote.positions == (16,)

    def test_the_finding_carries_the_vote_as_localization_params(self):
        code = _pronto([
            _frame("110110010000"),
            _frame("110110010000"),
            _frame("110110011000"),
        ])
        report = comb_wig(_wig({"Speed": code}))
        finding = report.findings[0]
        assert finding.check == CHECK_FRAME_DISAGREEMENT
        assert finding.message == "comb.frame_disagreement"
        assert finding.params["frames"] == "3"
        assert finding.params["readings"] == "2"
        assert finding.params["positions"] == "16"

    def test_repeats_of_different_lengths_name_no_positions(self):
        """Everything they share reads the same and they are still
        different lengths, so the repeats lost or gained edges at the
        ends. The message says that instead of naming positions it does
        not have."""
        bits = "10110010101"
        code = _pronto([
            _frame(bits), _frame(bits + "0"), _frame(bits + "00"),
        ])
        report = comb_wig(_wig({"Speed": code}))
        finding = report.findings[0]
        assert finding.message == "comb.frame_disagreement_lengths"
        assert "positions" not in finding.params
        assert finding.params["frames"] == "3"

    def test_a_wall_of_positions_switches_to_the_counted_message(self):
        noisy = [
            _frame("110110010000"),
            _frame("001001101111"),
            _frame("101010101010"),
        ]
        report = comb_wig(_wig({"Speed": _pronto(noisy)}))
        finding = report.findings[0]
        assert finding.message == "comb.frame_disagreement_many"
        assert int(finding.params["count"]) > 8
        assert len(finding.params["positions"].split(", ")) == 8


# ---------------------------------------------------------------------------
# It is a suspect, so the gate already carries it
# ---------------------------------------------------------------------------


class TestItReachesTheGate:
    def test_it_is_never_advisory(self):
        assert CHECK_FRAME_DISAGREEMENT not in ADVISORY_CHECKS

    def test_a_flagged_row_becomes_a_suspect_key(self):
        """The 0.9.8 comb gate turns suspicion into a human pressing the
        doubted button. Nothing new was needed for that: filing as an
        ordinary finding is what puts the row on the checklist."""
        wig = _load(DREO)
        report = comb_wig(wig)
        assert report.suspects == 2
        stamp_receipt(wig, report, "2026-08-22")
        assert "Oscillate Horizontal" in suspect_keys(wig)
        assert "Speed Down" in suspect_keys(wig)


# ---------------------------------------------------------------------------
# The acceptance fixtures
# ---------------------------------------------------------------------------


class TestTheDreoFan:
    """WigShop PR #18. The comb reported 0 suspects on this file and was
    right to; nothing compared a signal's frames to each other."""

    def test_the_file_still_says_it_was_clean(self):
        stored = json.loads(DREO.read_text())["comb"]
        assert stored["suspects"] == 0
        assert stored["version"] == 1

    def test_the_five_clean_buttons_stay_clean(self):
        wig = _load(DREO)
        flagged = {
            key
            for finding in comb_wig(wig).findings
            for key in finding.keys
        }
        assert flagged == {"Oscillate Horizontal", "Speed Down"}

    def test_oscillate_horizontal_votes_six_frames(self):
        """The brief's framing, reproduced: 11, 12, 12, 12, 12, 12 pairs.
        The brief counted five distinct twelve-bit decodes; the comb is
        protocol-blind and reads timings, so it separates all six. The
        framing and the disagreeing positions are the shared ground."""
        wig = _load(DREO)
        code = next(
            s.pronto for s in wig.signals if s.alias == "Oscillate Horizontal"
        )
        vote = frame_disagreement(code)
        assert vote is not None
        assert vote.frames == 6
        assert vote.readings == 6
        assert vote.positions[:4] == (0, 1, 2, 3)

    def test_speed_down_votes_four_frames(self):
        """14, 12, 12, 13 pairs. The two intact frames agree with each
        other, which is why the length class carries slack: strict
        equality would leave them alone in a cluster and report nothing
        about a capture the brief calls unambiguously broken."""
        wig = _load(DREO)
        code = next(s.pronto for s in wig.signals if s.alias == "Speed Down")
        vote = frame_disagreement(code)
        assert vote is not None
        assert vote.frames == 4
        assert vote.readings == 3

    def test_power_is_pinned_to_raw_and_reported_as_such(self):
        """kno-te pinned Power to raw, so the comb never judged it. That
        is a coverage line, not a clean bill."""
        wig = _load(DREO)
        report = comb_wig(wig)
        assert report.skipped == ["Power"]
        declined = report.coverage.to_dict()["checks"][
            CHECK_FRAME_DISAGREEMENT]["declined"]
        assert declined[DECLINE_PINNED_TO_RAW] == 1


class TestTheKomecoLattice:
    """WigShop PR #19. 1,156 cells, frame shape (1, 97, 1) on every one of
    them, zero structural variance. Release one must stay completely
    silent here: the defect in this file is semantic, and release two is
    what reads fields."""

    def test_no_structural_check_fires(self):
        report = comb_wig(_load(KOMECO))
        assert report.suspects == 0
        assert report.findings == []

    def test_its_cells_are_reported_as_unjudged_by_the_repeat_check(self):
        """One frame per cell that is long enough to read, so there is
        nothing to compare. Saying so is the point: a silent pass on a
        code nobody could check is the failure mode the brief named."""
        report = comb_wig(_load(KOMECO))
        checks = report.coverage.to_dict()["checks"]
        assert checks[CHECK_FRAME_DISAGREEMENT]["checked"] == 0
        assert checks[CHECK_FRAME_DISAGREEMENT]["declined"][
            DECLINE_TOO_FEW_FRAMES] == 1157


# ---------------------------------------------------------------------------
# The capture-time surface
# ---------------------------------------------------------------------------


class TestTheAssignPath:
    """A captured signal carries its own verdict to the assign dialog.

    Derived at serialization rather than stored: the check is cheap, the
    answer follows the bytes, and a stored flag would go stale the moment
    somebody edited the code.
    """

    def _signal(self, code: str):
        from custom_components.hair.models import UnknownSignal

        return UnknownSignal(
            fingerprint="fp", protocol="PRONTO", code=code,
            raw_timings=[], frequency=38000,
        )

    def test_a_noisy_capture_carries_the_vote(self):
        noisy = _pronto([
            _frame("110110010000"),
            _frame("110110010000"),
            _frame("110110011000"),
        ])
        assert self._signal(noisy).to_dict()["repeats_disagree"] == {
            "frames": 3, "readings": 2, "positions": [16],
        }

    def test_a_clean_capture_says_nothing(self):
        clean = _repeats("110110010000", 4)
        assert "repeats_disagree" not in self._signal(clean).to_dict()

    def test_a_non_pronto_signal_is_left_alone(self):
        signal = self._signal("whatever")
        signal.protocol = "NEC"
        assert "repeats_disagree" not in signal.to_dict()


# ---------------------------------------------------------------------------
# Coverage: what ran, what did not, and why
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_the_receipt_carries_coverage_at_version_two(self):
        wig = _wig({
            "One": _repeats("110110010000", 4),
            "Two": _repeats("110110100000", 4),
            "Three": _pronto([_frame("110110000100")]),
        })
        receipt = comb_wig(wig).to_receipt("2026-08-22")
        assert receipt["version"] == COMB_VERSION == 2
        coverage = receipt["coverage"]
        assert coverage["codes"] == 3
        assert coverage["checked"] == 3
        repeats = coverage["checks"][CHECK_FRAME_DISAGREEMENT]
        assert repeats["checked"] == 2
        assert repeats["declined"] == {DECLINE_SINGLE_FRAME: 1}

    def test_a_version_one_receipt_still_reads(self):
        """Old receipts stay valid. They simply cannot say what they did
        not look at, and the summary reports that as unknown rather than
        inventing a clean bill."""
        wig = _wig({"One": _repeats("110110010000", 4)})
        wig.extra["comb"] = {
            "version": 1, "date": "2026-07-31", "suspects": 0,
            "counts": {}, "findings": [],
        }
        summary = receipt_summary(wig)
        assert summary["version"] == 1
        assert summary["coverage"] is None

    def test_a_fresh_comb_upgrades_the_receipt(self):
        wig = _load(DREO)
        assert wig.extra["comb"]["version"] == 1
        stamp_receipt(wig, comb_wig(wig), "2026-08-22")
        assert wig.extra["comb"]["version"] == 2
        assert receipt_summary(wig)["coverage"]["codes"] == 7
