"""A real Daikin ARC486A1 press, and the four things it settles.

The decode-trust and capture-fragmentation reviews both kept reaching
for the same worst case -- one air conditioner press whose INTERIOR
gaps are longer than a receiver's idle setting -- and neither had a
real capture of one. This is that capture, contributed publicly by a
forum user (see fixtures/field-captures/README.md for provenance).

It earns its place four times over: it is why the shipped receiver
configurations moved from a 10 ms idle to 100 ms, it is a real
example of a decode that must NOT be trusted to rebuild a signal, it
shows where HAIR's generic frame split sits relative to this
protocol's own, and it is long enough to be an honest test of the
send-spacing entry cap.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from custom_components.hair.const import (
    PRONTO_GAP_THRESHOLD,
    SINGLE_LIST_MAX_ENTRIES,
)
from custom_components.hair.ir_command import ProntoCommand, RepeatedCommand
from custom_components.hair.wig_comb import _frame_lengths, _pairs

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None

_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)

CODE = (
    Path(__file__).parent
    / "fixtures"
    / "field-captures"
    / "arc486a1-orthobot.pronto"
).read_text(encoding="utf-8").strip()

# Pronto's own clock, from the code's carrier word. Every millisecond
# figure below is derived from the file rather than asserted at it.
_PERIOD_US = int(CODE.split()[1], 16) * 0.241246


def _gaps_ms() -> list[tuple[int, float]]:
    """Every space long enough to end a capture somewhere, in ms."""
    return [
        (index, round(space * _PERIOD_US / 1000, 1))
        for index, (_mark, space) in enumerate(_pairs(CODE))
        if space * _PERIOD_US / 1000 >= 5
    ]


class TestTheCaptureItself:
    def test_it_is_the_press_the_file_says_it_is(self):
        assert len(_pairs(CODE)) == 293

    def test_its_gaps_are_where_the_provenance_says(self):
        """A 7-pair preamble, a 25.1 ms rest, then frames separated by
        the protocol's own 35.1 ms, and the receiver's 100 ms idle
        echoed back as the tail."""
        assert _gaps_ms() == [(6, 25.1), (72, 35.1), (138, 35.1), (292, 100.0)]


class TestWhyTenMillisecondsWasNotEnough:
    """The reason the shipped ESPHome configurations now say 100 ms.

    A receiver ends a capture after `idle` of silence. This press has
    three silences inside it, and at 10 ms every one of them ends the
    capture, so one press arrives as four codes and each piece looks
    like a signal from a different remote.
    """

    def test_every_interior_gap_would_split_this_press_at_ten(self):
        interior = [ms for index, ms in _gaps_ms() if index != 292]
        assert len(interior) == 3
        assert all(ms > 10 for ms in interior)

    def test_none_of_them_reaches_a_hundred(self):
        """Which is what makes 100 ms the value that holds the press
        together. The only gap at or above it is the tail, and the tail
        is the idle setting itself showing up in the capture."""
        interior = [ms for index, ms in _gaps_ms() if index != 292]
        assert max(interior) < 100
        assert _gaps_ms()[-1][1] == 100.0


class TestWhereTheFrameSplitFalls:
    def test_the_protocols_own_gap_yields_four_frames(self):
        """Split anywhere below the preamble's 25.1 ms rest and the
        press reads as the four parts it is: preamble, then three
        frames."""
        pairs = _pairs(CODE)
        cut_words = 20_000 / _PERIOD_US
        lengths: list[int] = []
        run = 0
        for _mark, space in pairs:
            run += 1
            if space >= cut_words:
                lengths.append(run)
                run = 0
        if run:
            lengths.append(run)
        assert lengths == [7, 66, 66, 154]

    def test_hairs_generic_threshold_yields_three(self):
        """Not a bug, and worth having written down. HAIR's own frame
        split uses one threshold for every protocol, and at 26.9 ms it
        sits just above this preamble's 25.1 ms rest, so the preamble
        travels with the frame behind it. The comb compares SHAPES
        between codes of the same device, and a split that is
        consistent matters more there than one that is protocol-exact.
        """
        assert round(PRONTO_GAP_THRESHOLD * _PERIOD_US / 1000, 1) == 26.9
        assert _frame_lengths(_pairs(CODE)) == (73, 66, 154)


class TestDecodeTrustRefusesIt:
    """The verdict is False, and False is the right answer.

    The fixup plan expected "not False" here. Measured, the decoder
    reads this capture as KASEIKYO64 and accounts for one of its four
    frames, so decode-trust marks it as not covering the capture. That
    is the mechanism working: a label that explains a quarter of a
    press must never be trusted to rebuild it, and this row transmits
    exactly as captured instead. Pinned as False on purpose, because a
    future change that made it True would be a regression in the thing
    GH #134 exists to prevent.
    """

    @_needs_library
    def test_the_verdict_is_false(self):
        from custom_components.hair.protocol_decode import decode_coverage

        raw = ProntoCommand(CODE).get_raw_timings()
        assert decode_coverage(raw) is False

    @_needs_library
    def test_and_the_accounting_says_why(self):
        from custom_components.hair.protocol_decode import try_decode_identity

        identity = try_decode_identity(ProntoCommand(CODE).get_raw_timings())
        assert identity is not None
        assert identity.frames_total == 4
        assert identity.frames_explained == 1

    @_needs_library
    def test_so_the_send_path_will_replay_it_raw(self):
        from custom_components.hair.send_plan import would_send_decoded

        raw = ProntoCommand(CODE).get_raw_timings()
        row = _StoredAsCaptured(CODE, raw)
        assert would_send_decoded(row) is False


class _StoredAsCaptured:
    """A row shaped the way the stores hold this capture."""

    def __init__(self, code: str, raw: list[int]) -> None:
        from custom_components.hair.protocol_decode import (
            decode_coverage,
            try_decode_identity,
        )

        identity = try_decode_identity(raw)
        self.protocol = "PRONTO"
        self.code = code
        self.raw_timings = raw
        self.frequency = 38000
        self.repeat_count = 0
        self.tx_force_raw = False
        self.decoded_protocol = getattr(identity, "protocol", None)
        self.decoded_address = getattr(identity, "address", None)
        self.decoded_command = getattr(identity, "command", None)
        self.decoded_fingerprint = getattr(identity, "fingerprint", None)
        self.decoded_extras = None
        self.decode_covers = decode_coverage(raw)
        self.matrix_cell = None
        self.source = None


class TestTheEntryCapOnARealAcBlob:
    """Bench B2 in software.

    B2 asks what a long air conditioner code does to the single-list
    entry cap on an ESPHome emitter. A synthetic block can be made any
    length; this is what a real one costs.
    """

    def test_one_send_is_already_a_third_of_the_cap(self):
        entries = len(ProntoCommand(CODE).get_raw_timings())
        assert entries == 585
        assert entries < SINGLE_LIST_MAX_ENTRIES

    def test_three_sends_still_fit_in_one_call(self):
        inner = ProntoCommand(CODE)
        bundled = RepeatedCommand(inner, 3, 50_000).get_raw_timings()
        assert len(bundled) <= SINGLE_LIST_MAX_ENTRIES

    def test_ten_sends_do_not_and_must_chunk(self):
        inner = ProntoCommand(CODE)
        bundled = RepeatedCommand(inner, 10, 50_000).get_raw_timings()
        assert len(bundled) > SINGLE_LIST_MAX_ENTRIES

    def test_the_planner_chunks_it_rather_than_dropping_frames(self):
        """The cap is not a refusal. Every send still goes out, in the
        fewest calls the emitter will take."""
        from custom_components.hair.send_plan import plan_send

        inner = ProntoCommand(CODE)
        plan = plan_send(inner, 10, 500, "esphome")
        assert plan is not None
        assert plan.chunks > 1
        for call in plan.calls:
            assert len(call.command.get_raw_timings()) <= (
                SINGLE_LIST_MAX_ENTRIES
            )
        assert [call.terminate for call in plan.calls] == (
            [False] * (plan.chunks - 1) + [True]
        )
