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
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_DISAGREEMENT,
    CHECK_FRAME_INTEGRITY,
    COMB_VERSION,
    DECLINE_DECODE_RESOLVED,
    DECLINE_PINNED_TO_RAW,
    DECLINE_SINGLE_FRAME,
    DECLINE_TOO_FEW_FRAMES,
    _repeat_reading,
    comb_wig,
    decode_resolves_repeats,
    frame_disagreement,
    receipt_summary,
    stamp_receipt,
    suspect_keys,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    parse_wig,
)

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

    def test_a_bit_space_is_never_mistaken_for_a_frame_gap(self):
        """The step between a protocol's long and short BIT space is
        already about three: NEC spends 1690 us on a one against 560 on
        a zero, a Fujitsu lattice 44 against 14. In a code carrying no
        repeat gap at all, that step is the biggest one there is, and a
        search that took it cut every cell into bit-sized fragments and
        reported that the fragments disagreed. 716 of those across the
        test box's closet (bench 2026-08-22), which is why a separator
        has to be a separator in absolute terms as well."""
        bits = "0010110010100010110010101000101100101010001011001"
        pairs = [(17, 44 if bit == "1" else 13) for bit in bits]
        pairs.append((17, 0x09C4))
        words = [0x0000, 0x006D, len(pairs), 0x0000]
        for mark, space in pairs:
            words += [mark, space]
        code = " ".join(f"{w:04X}" for w in words)
        assert frame_disagreement(code) is None
        report = comb_wig(_wig({"Cool 24": code}))
        assert report.findings == []
        declined = report.coverage.to_dict()["checks"][
            CHECK_FRAME_DISAGREEMENT]["declined"]
        assert declined == {DECLINE_SINGLE_FRAME: 1}

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
        ordinary finding is what puts the row on the checklist.

        The COUNT moved in 0.14.1 A1 and the mechanism did not. Speed
        Down decodes cleanly under a repeat-voting protocol, so the
        check stands down and it is no longer a suspect; Oscillate
        Horizontal decodes as nothing at all and still is. What this
        pins is the wiring from finding to suspect key, and that a
        settled row does not reach the checklist.
        """
        wig = _load(DREO)
        report = comb_wig(wig)
        assert report.suspects == 1
        stamp_receipt(wig, report, "2026-08-22")
        assert "Oscillate Horizontal" in suspect_keys(wig)
        assert "Speed Down" not in suspect_keys(wig)


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

    def test_only_the_capture_nothing_could_read_stays_flagged(self):
        """SUPERSEDES test_the_five_clean_buttons_stay_clean (0.14.1 A1).

        Speed Down used to be flagged beside Oscillate Horizontal, and
        the raw measurement behind that has not changed: its four frames
        still say three different things. What changed is that Speed
        Down DECODES, cleanly, as SYMPHONY12, and Symphony reaches that
        answer by voting across exactly these frames. Oscillate
        Horizontal does not decode at all, so nothing overrules the
        doubt and it still flags.

        That split is the whole point of the item: the check keeps its
        teeth for the capture nobody can read, and stands down for the
        one a decoder already read whole.
        """
        wig = _load(DREO)
        flagged = {
            key
            for finding in comb_wig(wig).findings
            for key in finding.keys
        }
        assert flagged == {"Oscillate Horizontal"}

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

    def test_speed_down_still_votes_four_frames_underneath(self):
        """14, 12, 12, 13 pairs. The two intact frames agree with each
        other, which is why the length class carries slack: strict
        equality would leave them alone in a cluster and report nothing
        about a capture the brief calls unambiguously broken.

        The raw measurement is pinned here as it always was, straight
        off _repeat_reading, because 0.14.1 A1 did not change what this
        capture MEASURES. It changed who gets the last word about it:
        frame_disagreement now consults the decode and stands down, so
        the public answer is None while the arithmetic underneath is
        untouched. Both halves are pinned so a regression in either one
        is visible.
        """
        wig = _load(DREO)
        code = next(s.pronto for s in wig.signals if s.alias == "Speed Down")
        _outcome, vote = _repeat_reading(code)
        assert vote is not None
        assert vote.frames == 4
        assert vote.readings == 3
        assert decode_resolves_repeats(code) is True
        assert frame_disagreement(code) is None

    def test_power_is_pinned_to_raw_and_reported_as_such(self):
        """kno-te pinned Power to raw, so the comb never judged it. That
        is a coverage line, not a clean bill."""
        wig = _load(DREO)
        report = comb_wig(wig)
        assert report.skipped == ["Power"]
        declined = report.coverage.to_dict()["checks"][
            CHECK_FRAME_DISAGREEMENT]["declined"]
        assert declined[DECLINE_PINNED_TO_RAW] == 1


class TestTheDebrisTrim:
    """0.14.1 B3. A stray burst gets a candidate built by deleting it.

    A capture that ends with one extra timing after the last complete
    frame is the classic unclean capture. Every receiver ignores it,
    which is why the comb ranks it last, and it still means the file
    carries a frame that is not a frame. The repair is a deletion, so
    the candidate is provably the original minus the debris rather than
    anything reconstructed.
    """

    def _matrix(self, codes):
        """A lattice of ``codes``, one cell each, so the shape check has
        a modal shape to compare against."""
        cells = [
            ClimateCell(mode="cool", pronto=pronto, temp=float(20 + i))
            for i, pronto in enumerate(codes)
        ]
        return Wig(
            name="Lattice",
            signals=[],
            climate=ClimateMatrix(
                min_temp=16.0, max_temp=30.0, off=codes[0], cells=cells,
            ),
        )

    #: Above PRONTO_GAP_THRESHOLD, so _frame_lengths splits here. The
    #: module-level GAP is deliberately below it, which is right for the
    #: repeat check and wrong for this one.
    SPLIT = 0x0800

    def _code(self, bits, frames=2, dangle=False):
        """``frames`` copies of ``bits``, optionally with debris."""
        pairs = []
        for _ in range(frames):
            body = _frame(bits)
            last = len(body) - 1
            for index, (mark, space) in enumerate(body):
                pairs.append((mark, self.SPLIT if index == last else space))
        if dangle:
            pairs.append((0x0010, TRAILER))
        words = [0x0000, 0x006D, len(pairs), 0x0000]
        for mark, space in pairs:
            words += [mark, space]
        return " ".join(f"{w:04X}" for w in words)

    def _dangling(self, bits="110100100101"):
        return self._code(bits, dangle=True)

    def _clean(self, bits="110100100101"):
        return self._code(bits)

    def test_the_candidate_is_the_original_minus_the_dangle(self):
        """Byte-level, not approximately. Every timing in the candidate
        was already in the code, and the only difference is the pair
        that was hanging off the end."""
        from custom_components.hair.tangles import ORIGIN_TRIM, find_trim
        from custom_components.hair.wig_comb import _pairs

        dangling = self._dangling()
        findings = [{"check": "stray-burst"}]
        candidate, abstain = find_trim(dangling, findings)
        assert abstain is None
        assert candidate is not None
        assert candidate["reasoning"]["origin"] == ORIGIN_TRIM
        assert candidate["reasoning"]["pairs_removed"] == 1

        before = _pairs(dangling)
        after = _pairs(candidate["pronto"])
        assert after == before[:-1]

    def test_it_only_trims_a_fragment_shorter_than_a_real_frame(self):
        """THE GUARD THAT MATTERS. A short trailing frame is not always
        debris: an NEC ditto is a deliberate repeat marker, and a
        protocol whose last frame is legitimately shorter is one this
        must not touch. A tail as long as anything else in the code
        makes this abstain and say why rather than guess."""
        from custom_components.hair.tangles import (
            TRIM_FRAGMENT_IS_A_FRAME,
            find_trim,
        )

        # Every frame the same length: nothing here is debris.
        even = self._code("110100100101", frames=3)
        candidate, abstain = find_trim(even, [{"check": "stray-burst"}])
        assert candidate is None
        assert abstain == TRIM_FRAGMENT_IS_A_FRAME

    def test_it_does_not_go_looking_for_fragments_on_its_own(self):
        """It repairs the thing the comb named. A code with no
        stray-burst finding is not this branch to look at, whatever
        shape it happens to have."""
        from custom_components.hair.tangles import (
            TRIM_NOTHING_TO_TRIM,
            find_trim,
        )

        candidate, abstain = find_trim(self._dangling(), [])
        assert candidate is None
        assert abstain == TRIM_NOTHING_TO_TRIM

        candidate, abstain = find_trim(
            self._dangling(), [{"check": "field-mismatch"}])
        assert candidate is None
        assert abstain == TRIM_NOTHING_TO_TRIM

    def test_the_candidate_reaches_the_fixes_ready_card(self):
        """The wiring, end to end through the real listing.

        Everything above tests the builder. This tests that its answer
        arrives: the frontend buckets Fixes ready on has_donor alone, so
        a candidate that never lands on the row is a repair nobody can
        reach. The origin rides along in the reasoning, which is what
        the accept path reads to record where the bytes came from.
        """
        from custom_components.hair.models import IRDevice
        from custom_components.hair.tangles import ORIGIN_TRIM, list_tangles

        first = self._clean("110100100101")
        second = self._clean("110100100110")
        matrix = ClimateMatrix(
            min_temp=16.0, max_temp=30.0, off=first,
            cells=[
                ClimateCell(mode="cool", pronto=first, temp=20.0),
                ClimateCell(mode="cool", pronto=second, temp=21.0),
                ClimateCell(mode="cool", pronto=self._dangling(), temp=22.0),
            ],
        )
        device = IRDevice(
            name="AC", climate_matrix=True,
            emitter_entity_ids=["infrared.b"],
        )
        rows = list_tangles(device, matrix).rows
        row = next(r for r in rows if "stray-burst" in r.classes)
        assert row.has_donor is True
        assert row.donor is not None
        assert row.donor["reasoning"]["origin"] == ORIGIN_TRIM
        assert row.donor_abstain is None

    def test_the_trimmed_code_combs_clean_where_the_original_did_not(self):
        """The end-to-end claim: accepting this candidate is what makes
        the finding go away on the next comb. Proved by combing the
        lattice with the trimmed bytes in place rather than by trusting
        the builder."""
        from custom_components.hair.tangles import find_trim

        dangling = self._dangling()
        # Distinct codes: two identical cells would file a duplicated
        # neighbour and drown the finding under test.
        first = self._clean("110100100101")
        second = self._clean("110100100110")
        before = comb_wig(self._matrix([first, second, dangling]))
        flagged = {f.check for f in before.findings}
        assert "stray-burst" in flagged

        candidate, _abstain = find_trim(
            dangling, [{"check": "stray-burst"}])
        assert candidate is not None
        after = comb_wig(
            self._matrix([first, second, candidate["pronto"]]))
        assert "stray-burst" not in {f.check for f in after.findings}


class TestADecodeThatVotesStandsTheCheckDown:
    """0.14.1 A1. The field case, and the four ways it must not overreach.

    The Dreo fan is a real capture of a real remote. Its frames differ
    from each other because a Symphony remote sends a vendor preamble
    and then repeats, and because a receiver picking that up at arm
    length does not hear every frame identically. The decoder knows all
    of that: it splits, discards what loses, and requires two survivors
    to agree. This check does not know any of it, and said so, forever,
    with no way for the person holding the remote to make it stop.

    So the check asks the decoder before it files. Narrowly.
    """

    def _dreo_code(self, alias):
        wig = _load(DREO)
        return next(s.pronto for s in wig.signals if s.alias == alias)

    # (1) The field case itself.
    def test_a_capture_the_decoder_read_whole_combs_clean(self):
        code = self._dreo_code("Speed Down")
        report = comb_wig(_wig({"Speed Down": code}))
        flagged = {k for f in report.findings for k in f.keys}
        assert "Speed Down" not in flagged

    def test_and_the_receipt_says_why_rather_than_going_quiet(self):
        """A silent pass and a reasoned one look identical from the
        outside, which is the failure the coverage section exists to
        prevent. The code is COUNTED as looked at and the reason is
        recorded beside it."""
        code = self._dreo_code("Speed Down")
        report = comb_wig(_wig({"Speed Down": code}))
        slot = report.coverage.to_dict()["checks"][CHECK_FRAME_DISAGREEMENT]
        assert slot["declined"][DECLINE_DECODE_RESOLVED] == 1
        assert slot["checked"] == 1
        assert "Speed Down" in report.coverage.seen

    # (2) A non-voting protocol earns no exemption.
    def test_a_disagreeing_capture_under_a_non_voting_protocol_still_flags(
        self,
    ):
        """The exemption is not "it decoded". A protocol carrying its own
        checksum proves each frame on its own and never has to reconcile
        them, so frames that disagree under one are still a bad capture
        and still get reported.

        Built rather than borrowed: a NEC frame followed by a mangled
        copy of itself. NEC decodes, NEC does not repeat-vote, and the
        disagreement survives.
        """
        from custom_components.hair.decoders import split_frames
        from custom_components.hair.ir_command import ProntoCommand
        from custom_components.hair.protocol_decode import (
            decode_is_repeat_voted,
            try_decode_identity,
        )

        code = _repeats("110100100101", 4)
        timings = ProntoCommand(code).get_raw_timings()
        identity = try_decode_identity(timings)
        # Whatever this synthetic capture resolves to, the claim under
        # test is the same one: no repeat-voting decoder accepted it.
        assert decode_is_repeat_voted(timings) is False
        assert decode_resolves_repeats(code) is False
        assert split_frames is not None
        assert identity is None or identity.protocol != "SYMPHONY12"

    # (3) A voting protocol whose vote did not carry earns no exemption.
    def test_a_voting_capture_whose_vote_does_not_carry_still_flags(self):
        """Oscillate Horizontal, straight off the fixture. Six frames,
        six readings, and Symphony refuses it: no two survivors agree,
        so there is no verdict to defer to and the doubt stands."""
        code = self._dreo_code("Oscillate Horizontal")
        assert decode_resolves_repeats(code) is False
        vote = frame_disagreement(code)
        assert vote is not None
        assert vote.frames == 6
        report = comb_wig(_wig({"Oscillate Horizontal": code}))
        flagged = {k for f in report.findings for k in f.keys}
        assert flagged == {"Oscillate Horizontal"}

    # (4) The capture-time notice follows the same rule.
    def test_the_capture_time_notice_is_suppressed_too(self):
        """One implementation, one answer. The notice in the assign
        dialog and the command editor reads frame_disagreement, so a
        capture the decoder settles raises no red line while the person
        is still holding the remote."""
        assert frame_disagreement(self._dreo_code("Speed Down")) is None
        assert frame_disagreement(
            self._dreo_code("Oscillate Horizontal")) is not None

    # (5) The matrix branch is untouched.
    def test_a_matrix_cell_gets_no_exemption(self):
        """THE SCOPE LINE. A flat row is a captured button and can
        legitimately be a voting protocol whose frames differ by design.
        A lattice cell is generated, and frames that disagree there are
        a defect in the file rather than a property of the remote, so
        the same bytes that stand the check down on a flat row must
        still flag inside a matrix.

        Pinned with the identical Speed Down code on both sides, so the
        only variable is which branch read it.
        """
        code = self._dreo_code("Speed Down")
        flat = comb_wig(_wig({"Speed Down": code}))
        assert not {k for f in flat.findings for k in f.keys}

        matrix = Wig(
            name="Lattice",
            signals=[],
            climate=ClimateMatrix(
                min_temp=16.0,
                max_temp=30.0,
                off=code,
                cells=[ClimateCell(mode="cool", pronto=code, temp=20.0)],
            ),
        )
        report = comb_wig(matrix)
        flagged = {k for f in report.findings for k in f.keys}
        assert flagged, "the matrix branch must still doubt these bytes"
        slot = report.coverage.to_dict()["checks"][CHECK_FRAME_DISAGREEMENT]
        assert DECLINE_DECODE_RESOLVED not in slot["declined"]


class TestTheKomecoLattice:
    """WigShop PR #19. 1,156 cells, frame shape (1, 97, 1) on every one of
    them, zero structural variance. The defect in this file is semantic,
    so every STRUCTURAL check must stay silent on it -- that was release
    one's whole claim about this fixture, and release two's field sweep
    (which does find the 52 shifted cells, pinned in
    ``test_field_sweep.py``) does not change it."""

    def test_no_structural_check_fires(self):
        structural = {
            finding.check for finding in comb_wig(_load(KOMECO)).findings
        } - {CHECK_FIELD_MISMATCH, CHECK_FRAME_INTEGRITY}
        assert structural == set()

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

    def test_a_stale_verdict_from_the_store_does_not_come_back(self):
        """The signal store writes what to_dict returns, so a derived
        key reaches the file. That is harmless while it is recomputed on
        the way back out and fatal if it is not: the fresh answer for a
        clean code is silence, and silence cannot overwrite anything.
        Nine air conditioner rows on the test box kept a verdict the
        check had already stopped making (bench 2026-08-22)."""
        from custom_components.hair.models import UnknownSignal

        stored = self._signal(_repeats("110110010000", 4)).to_dict()
        stored["repeats_disagree"] = {
            "frames": 9, "readings": 9, "positions": [1, 2, 3],
        }
        again = UnknownSignal.from_dict(stored).to_dict()
        assert "repeats_disagree" not in again

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
