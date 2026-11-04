"""Radio frames: the keyfob captures, and constructed families.

The keyfob fixture is real (``fixtures/rf/README.md``). The families
are built here from their published timings, each to pin one case of
the rules in ``rf_frames``: the address-first 24-symbol key (PT2262),
the strict body rule (Nexa, refused; an open ruling), a preamble family
keyed on shape alone (Dooya), a rolling code behind a preamble
(KeeLoq-shaped) and Manchester behind a sync header (Somfy-shaped).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from custom_components.hair import rf_frames as rf
from custom_components.hair.const import (
    RF_ADDRESS_HEAD_EDGES,
    RF_ASSUMED_FRAME_GAP_US,
    RF_GAP_ASSUMED,
    RF_GAP_MEASURED,
)

FIXTURE = Path(__file__).parent / "fixtures" / "rf" / "it104-keyfob-433.json"
TAIL_US = 45_680


def _signed(edges):
    return [abs(v) if i % 2 == 0 else -abs(v) for i, v in enumerate(edges)]


@pytest.fixture(scope="module")
def captures():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["captures"]


@pytest.fixture(scope="module")
def analyses(captures):
    return [rf.analyze(_signed(c["pulses"])) for c in captures]


# ---------------------------------------------------------------------------
# The keyfob
# ---------------------------------------------------------------------------


class TestKeyfob:
    def test_seven_rows_on_one_card(self, analyses):
        assert all(a is not None for a in analyses)
        assert len({a.fingerprint for a in analyses}) == 7
        assert len({a.frame_hash for a in analyses}) == 7
        assert len({a.device_key for a in analyses}) == 1

    def test_eight_voting_frames_per_normal_capture(self, captures, analyses):
        votes = Counter(
            (len(c["pulses"]), a.votes) for c, a in zip(captures, analyses, strict=True)
        )
        # 28 captures of 500 durations, one realigned at 498, one of 1,000
        # that holds two bursts' worth of frames.
        assert votes == {(500, 8): 28, (498, 8): 1, (1000, 16): 1}

    def test_each_buttons_presses_land_on_one_row(self, captures, analyses):
        def rows(batch):
            return [
                a.fingerprint
                for c, a in zip(captures, analyses, strict=True)
                if c["batch"] == batch
            ]

        button_1 = rows("button-1")
        assert len(button_1) == 4 and len(set(button_1)) == 1
        later = rows("buttons-2-3-all")
        # Button 2's three presses, then button 3's.
        assert len(set(later[0:3])) == 1
        assert len(set(later[3:6])) == 1
        assert later[0] != later[3]

    def test_the_card_key_is_the_address_head(self, analyses):
        key = analyses[0].device_key
        assert key.startswith("DEV:RF:49:h0:")
        assert len(key.rsplit(":", 1)[1]) == 12

    def test_the_frame_shape(self, analyses):
        a = analyses[0]
        assert a.body_edges == 49
        assert a.header_shape == "h0"
        assert len(a.frame) == 50
        assert a.frame[0] > 0 and a.frame[-1] < 0
        assert a.gap_source == RF_GAP_MEASURED
        assert 395 <= a.short_mark_us <= 456

    def test_the_tail_is_never_the_gap(self, analyses):
        for a in analyses:
            assert 12_800 <= a.gap_us <= 13_000
            assert -TAIL_US not in a.frame

    def test_the_seam_is_dropped(self, captures):
        pulses = captures[0]["pulses"]
        # The stretched space sits at index 249 of every normal capture.
        assert pulses[249] > 4_000
        pieces = rf.split_frames(_signed(pulses))
        lengths = [len(p.edges) for p in pieces]
        assert lengths.count(50) == 8
        whole = rf.whole_frames(pieces)
        assert len(whole) == 8
        assert {len(piece.edges) for piece, _ in whole} == {50}
        # The seam piece's "gap" (the stretched data space) is not one of
        # the winning gaps.
        assert all(piece.gap < 13_500 for piece, _ in whole)

    def test_a_stretched_gap_does_not_move_the_median(self, captures):
        pulses = list(captures[0]["pulses"])
        before = rf.analyze(_signed(pulses))
        gaps = [i for i, v in enumerate(pulses[:-1]) if i % 2 and v > 12_000]
        pulses[gaps[3]] = 30_000
        after = rf.analyze(_signed(pulses))
        assert after.fingerprint == before.fingerprint
        # Eight gaps: the median moves to the next interior value at most,
        # and the stretched one never becomes the gap.
        interior = sorted(captures[0]["pulses"][i] for i in gaps)
        assert interior[0] <= after.gap_us <= interior[-1]
        assert abs(after.gap_us - before.gap_us) < 50

    def test_signed_and_unsigned_agree(self, captures):
        pulses = captures[5]["pulses"]
        a, b = rf.analyze(pulses), rf.analyze(_signed(pulses))
        assert (a.fingerprint, a.frame_hash, a.device_key, a.frame) == (
            b.fingerprint, b.frame_hash, b.device_key, b.frame
        )

    def test_a_stored_frame_reidentifies(self, analyses):
        for a in analyses:
            again = rf.identity_of_frame(a.frame)
            assert (again.fingerprint, again.frame_hash, again.device_key) == (
                a.fingerprint, a.frame_hash, a.device_key
            )


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


class TestGate:
    def test_a_bodiless_pair_is_refused(self):
        # Mark, space, at one width each, repeated: no body however long.
        assert rf.analyze(_signed([500, 500] * 40 + [500])) is None
        assert rf.analyze(_signed([300, 9_000] * 12 + [300])) is None

    def test_one_whole_frame_is_not_enough(self):
        frame = _pt2262("0F1F0F1F" "0F10")
        assert rf.analyze(_signed(frame)) is None
        # Two frames, the second closed by its gap inside the capture.
        assert rf.analyze(_burst(frame, 1)) is None
        assert rf.analyze(_burst(frame, 2)).votes == 2

    def test_an_empty_capture(self):
        assert rf.analyze([]) is None
        assert rf.analyze(None) is None

    def test_a_lone_stored_frame_assumes_its_gap(self):
        # A stored frame ends on its gap, which canonical_edges strips as
        # the last value, so a re-read never measures one. The vote's
        # assumed branch is for split delivery (always-on receivers, a
        # later round): two frames inside one capture always measure.
        frame = _signed(_pt2262("0F1F0F1F" "0F10"))
        again = rf.identity_of_frame(frame)
        assert again.gap_source == RF_GAP_ASSUMED
        assert again.gap_us == RF_ASSUMED_FRAME_GAP_US


# ---------------------------------------------------------------------------
# Constructed families
# ---------------------------------------------------------------------------

A = 350  # PT2262 base unit (alpha)


def _pt2262(trits: str, unit: int = A) -> list[int]:
    """One PT2262 frame: 12 trits, the sync mark, the 31-unit gap."""
    symbol = {
        "0": [unit, 3 * unit, unit, 3 * unit],
        "1": [3 * unit, unit, 3 * unit, unit],
        "F": [unit, 3 * unit, 3 * unit, unit],
    }
    edges: list[int] = []
    for trit in trits:
        edges += symbol[trit]
    return [*edges, unit, 31 * unit]


def _burst(frame: list[int], count: int = 6, tail: int = TAIL_US) -> list[int]:
    return _signed(frame * count + [frame[0], tail])


class TestPT2262:
    ADDRESS = "0F1F0F1F"

    def _key(self, trits):
        return rf.analyze(_burst(_pt2262(trits))).device_key

    def test_it_reads_as_an_address_first_frame(self):
        result = rf.analyze(_burst(_pt2262(self.ADDRESS + "0001")))
        assert result.body_edges == 49
        assert result.header_shape == "h0"
        assert result.device_key.startswith("DEV:RF:49:h0:")

    def test_the_key_keeps_exactly_the_address_trits(self):
        assert RF_ADDRESS_HEAD_EDGES == 32  # 8 trits of 4 edges
        base = self._key(self.ADDRESS + "0000")
        # Every data trit, each value: same card.
        for position in range(4):
            for value in "01F":
                data = list("0000")
                data[position] = value
                assert self._key(self.ADDRESS + "".join(data)) == base
        # Every address trit changed: a different card.
        for position in range(8):
            address = list(self.ADDRESS)
            address[position] = "1" if address[position] != "1" else "0"
            assert self._key("".join(address) + "0000") != base

    def test_buttons_are_rows(self):
        prints = {
            rf.analyze(_burst(_pt2262(self.ADDRESS + data))).fingerprint
            for data in ("0001", "0010", "0100", "1000")
        }
        assert len(prints) == 4


class TestNexa:
    """Self-learning KAKU / Nexa: every mark the same width.

    Refused by the strict body rule (both polarities need two levels).
    This is the open ruling the report names: a family reader, or a
    looser rule for one-width marks, would mint it.
    """

    def _frame(self, bits: str) -> list[int]:
        t = 250
        edges = [t, 10 * t]
        for bit in bits:
            edges += [t, t, t, 5 * t] if bit == "0" else [t, 5 * t, t, t]
        return [*edges, t, 40 * t]

    def test_it_is_refused(self):
        frame = self._frame("1011" * 8)
        assert rf.analyze(_burst(frame, 5)) is None


class TestDooya:
    """A header pair, 40 PWM bits and a trailing mark: keyed on shape."""

    def _frame(self, bits: str) -> list[int]:
        edges = [4_700, 1_500]
        for bit in bits:
            edges += [350, 700] if bit == "0" else [700, 350]
        return [*edges, 350, 8000]

    def test_header_and_shape_key(self):
        result = rf.analyze(_burst(self._frame("1100101011110000" * 2 + "10100101"), 4))
        assert result is not None
        assert result.header_shape == "h2"
        assert result.body_edges == 81
        assert result.device_key == "DEV:RF:81:h2"
        assert result.votes == 4

    def test_two_channels_two_rows_one_card(self):
        one = rf.analyze(_burst(self._frame("10" * 20), 4))
        two = rf.analyze(_burst(self._frame("01" * 20), 4))
        assert one.fingerprint != two.fingerprint
        assert one.device_key == two.device_key


class TestKeeloqShaped:
    """A one-width preamble, a header gap, 66 PWM bits.

    The preamble is cut off at the header gap and has no body, so the
    data is the frame. The hopping half changes every press, so every
    press is a new row on one card: rolling detection is a later round
    (``rolling_state`` is written ``none`` this round).
    """

    def _frame(self, bits: str) -> list[int]:
        edges = [400, 400] * 11 + [400, 4_000]
        for bit in bits:
            edges += [400, 800] if bit == "0" else [800, 400]
        edges[-1] = 15_000  # the last bit's space is the inter-frame gap
        return edges

    def _press(self, hop: str):
        fixed = "1010011100001111010110100110" + "0110" + "00"
        return rf.analyze(_burst(self._frame(hop + fixed), 4))

    def test_each_press_is_a_row_on_one_card(self):
        one = self._press("10110010" * 4)
        two = self._press("01001101" * 4)
        assert one is not None and two is not None
        assert one.header_shape == "h0"
        assert one.fingerprint != two.fingerprint
        assert one.device_key == two.device_key == f"DEV:RF:{one.body_edges}:h0"
        assert one.votes == 4


def _segments(levels_and_widths: list[tuple[int, int]]) -> list[int]:
    """Run-length a level sequence into alternating edges, high first."""
    merged: list[list[int]] = []
    for level, width in levels_and_widths:
        if merged and merged[-1][0] == level:
            merged[-1][1] += width
        else:
            merged.append([level, width])
    assert merged[0][0] == 1
    return [width for _, width in merged]


class TestSomfyShaped:
    """Two hardware sync pairs, a software sync, 56 Manchester bits.

    The sync is the header. A Manchester body's edge count follows its
    data, and the key is edge count plus header, so two presses can land
    on different cards until a family reader exists. Pinned so that
    stays visible.
    """

    def _press(self, bits: str, repeats: int = 3) -> list[int]:
        half = 640
        frame: list[tuple[int, int]] = []
        for _ in range(2):
            frame += [(1, 2_416), (0, 2_416)]
        frame += [(1, 4_550), (0, half)]
        for bit in bits:
            frame += [(0, half), (1, half)] if bit == "1" else [(1, half), (0, half)]
        frame += [(0, 27_000)]
        return _signed([*_segments(frame * repeats), half, TAIL_US])

    def test_the_sync_is_the_header(self):
        result = rf.analyze(self._press("1011" * 14))
        assert result is not None
        assert result.header_shape == "h5"
        assert result.device_key == f"DEV:RF:{result.body_edges}:h5"
        assert result.votes >= 2
