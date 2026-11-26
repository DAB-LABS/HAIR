"""A radio frame whose gap no capture held takes its chip family's gap.

A receiver whose idle is shorter than a code's sync hands each frame
over alone, so HAIR never measures the gap and used to send an assumed
30 ms. A PT2262 or EV1527 receiver decodes the 31 T space before the
word as its sync and does not take 30 ms as one (GH #4). The gap now
comes from the family the frame reads as, from the datasheets in
``rf_family``, stored with its own source so it is never taken for a
measurement; a measured gap always wins.

Every frame here is written from timings, not from anyone's capture.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.hair import rf_family, rf_frames, rf_send
from custom_components.hair.const import (
    MEDIUM_IR,
    MEDIUM_RF,
    RF_ASSUMED_FRAME_GAP_US,
    RF_GAP_ASSUMED,
    RF_GAP_FAMILY,
    RF_GAP_MEASURED,
    RF_PROTOCOL,
)
from custom_components.hair.models import repair_assumed_gap, upgrade_rf_fields
from custom_components.hair.storage import HAIRStore
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _capture as _kl_capture

# The GH #4 shape: 24 pulse pairs of a short (about 380 us) and a long
# (about 1,200 us) at 1:3 and 3:1, then the 1 T sync mark. The pair sum
# is 4 T, so T is 395 us and the family's sync is 31 T.
SHORT, LONG, SYNC_MARK = 380, 1200, 364
DATA = "011001100110011000011011"
T_US = (SHORT + LONG) / 4


def _ev1527(bits: str = DATA, short: int = SHORT, long: int = LONG) -> list[int]:
    frame: list[int] = []
    for bit in bits:
        frame += [long, -short] if bit == "1" else [short, -long]
    return [*frame, SYNC_MARK if short == SHORT else short]


def _ht12e(bits: str = "101100111010", t: int = 470) -> list[int]:
    """Start mark, then 12 space-mark pairs, 3 T each: a one is 2 T low,
    1 T high. T 470 us is outside the CAME and Nice FLO bands."""
    frame = [t]
    for bit in bits:
        frame += [-2 * t, t] if bit == "1" else [-t, 2 * t]
    return frame


def _ht6p20(code: str = "101100111000111100001010", lam: int = 400) -> list[int]:
    """The pilot's 1 lambda high, then 24 bits and the 0101 end code."""
    frame = [lam]
    for bit in code + "0101":
        frame += [-2 * lam, lam] if bit == "1" else [-lam, 2 * lam]
    return frame


def _row(frame: list[int], source: str | None, gap: int | None = None, **kw):
    return SimpleNamespace(
        medium=MEDIUM_RF, protocol=RF_PROTOCOL, raw_timings=list(frame),
        rf_frame_gap_us=gap, rf_frame_gap_source=source, **kw,
    )


class TestTheFamilysGap:
    def test_ev1527_gets_31_t_of_its_own_t(self):
        gap = rf_family.family_gap_us(_ev1527())
        assert gap == pytest.approx(31 * T_US, abs=31)
        assert 11_000 < gap < 13_500

    def test_a_faster_remote_gets_a_shorter_gap(self):
        fast = rf_family.family_gap_us(_ev1527(short=200, long=600))
        assert fast == pytest.approx(31 * 200, abs=31)

    def test_ht12e_gets_36_t(self):
        assert rf_family.family_gap_us(_ht12e()) == pytest.approx(36 * 470, abs=36)

    def test_ht6p20_gets_23_lambda(self):
        assert rf_family.family_gap_us(_ht6p20()) == pytest.approx(23 * 400, abs=23)

    def test_a_frame_no_family_reads_gets_none(self):
        assert rf_family.family_gap_us([500, -500] * 30 + [500]) is None
        assert rf_family.family_gap_us(None) is None
        assert rf_family.family_gap_us([]) is None

    def test_a_rolling_frame_gets_none(self):
        word = rf_frames.analyze(_kl_capture(_kl_bits(hopping=0x0BADF00D), words=4)).frame
        assert rf_family.rolling_family(word) == "keeloq"
        assert rf_family.family_gap_us(word) is None


class TestTheSource:
    def test_one_lone_frame_takes_the_family_gap(self):
        frame = _ev1527()
        seen = rf_frames.identity_of_frame(frame)
        assert seen.gap_source == RF_GAP_FAMILY
        assert seen.gap_us == rf_family.family_gap_us(frame)

    def test_frames_split_one_per_capture_take_it_too(self):
        """A burst of frames that arrived one per capture carries no gap."""
        frame = _ev1527()
        pieces = [
            (piece, rf_frames.split_body(piece))
            for piece in rf_frames.split_frames(frame) * 4
        ]
        voted = rf_frames.vote(pieces)
        assert voted.gap_source == RF_GAP_FAMILY
        assert voted.frame[-1] > 0  # the stored frame has no gap on it

    def test_a_measured_gap_wins(self):
        frame = _ev1527()
        capture = [*frame, -10_850, *frame, -10_850, *frame]
        seen = rf_frames.analyze(capture)
        assert (seen.gap_us, seen.gap_source) == (10_850, RF_GAP_MEASURED)

    def test_a_frame_no_family_reads_keeps_the_assumed_gap(self):
        assert rf_frames.unmeasured_gap([500, -500] * 30 + [500]) == (
            RF_ASSUMED_FRAME_GAP_US, RF_GAP_ASSUMED,
        )

    def test_the_wire_frame_ends_in_the_family_gap_not_30_ms(self):
        """GH #4: the code as sent ends in about 31 T, not 30,000 us."""
        frame = _ev1527()
        gap, source = rf_frames.unmeasured_gap(frame)
        wire = rf_send.wire_frame(_row(frame, source, gap))
        assert wire[:-1] == frame
        assert -wire[-1] == gap
        assert 11_000 < -wire[-1] < 13_500


class TestTheRepair:
    def test_an_assumed_row_takes_its_familys_gap(self):
        row = _row(_ev1527(), RF_GAP_ASSUMED, RF_ASSUMED_FRAME_GAP_US)
        assert repair_assumed_gap(row) is True
        assert row.rf_frame_gap_source == RF_GAP_FAMILY
        assert row.rf_frame_gap_us == rf_family.family_gap_us(_ev1527())
        assert repair_assumed_gap(row) is False  # once

    def test_a_measured_or_edited_row_is_left_alone(self):
        """A gap set in the radio editor is stored as measured."""
        for gap in (10_850, 30_000):
            row = _row([*_ev1527(), -gap], RF_GAP_MEASURED, gap)
            assert repair_assumed_gap(row) is False
            assert (row.rf_frame_gap_us, row.rf_frame_gap_source) == (gap, RF_GAP_MEASURED)

    def test_rows_no_family_reads_and_infrared_rows_are_left_alone(self):
        odd = _row([500, -500] * 30 + [500], RF_GAP_ASSUMED, RF_ASSUMED_FRAME_GAP_US)
        assert repair_assumed_gap(odd) is False
        assert odd.rf_frame_gap_source == RF_GAP_ASSUMED
        ir = _row(_ev1527(), RF_GAP_ASSUMED)
        ir.medium = MEDIUM_IR
        assert repair_assumed_gap(ir) is False

    def test_the_load_walk_repairs_commands_triggers_and_sniffer_rows(self):
        def assumed():
            return _row(_ev1527(), RF_GAP_ASSUMED, RF_ASSUMED_FRAME_GAP_US)

        cmd, measured = assumed(), _row(_ev1527(), RF_GAP_MEASURED, 10_850)
        trigger, catalog = assumed(), assumed()
        ir_cmd = SimpleNamespace(protocol="PRONTO", raw_timings=None)
        fake = SimpleNamespace(
            _data={"d": SimpleNamespace(commands=[cmd, measured, ir_cmd])},
            _triggers={"t": trigger},
        )
        signal_store = SimpleNamespace(
            get_all_devices=lambda: [SimpleNamespace(signals=[catalog])],
        )
        assert HAIRStore.repair_assumed_gaps(fake, signal_store) == (True, True)
        assert {r.rf_frame_gap_source for r in (cmd, trigger, catalog)} == {RF_GAP_FAMILY}
        assert measured.rf_frame_gap_us == 10_850
        assert HAIRStore.repair_assumed_gaps(fake, signal_store) == (False, False)


class TestAKnownRowLearns:
    def test_family_beats_assumed_and_measured_beats_both(self):
        row = _row(_ev1527(), RF_GAP_ASSUMED, RF_ASSUMED_FRAME_GAP_US,
                   rf_frequency_source=None)
        family = SimpleNamespace(rf_frame_gap_us=12_245, rf_frame_gap_source=RF_GAP_FAMILY,
                                 rf_frequency_source=None, rf_frequency_hz=None)
        measured = SimpleNamespace(rf_frame_gap_us=10_850, rf_frame_gap_source=RF_GAP_MEASURED,
                                   rf_frequency_source=None, rf_frequency_hz=None)
        assert upgrade_rf_fields(row, family) is True
        assert (row.rf_frame_gap_us, row.rf_frame_gap_source) == (12_245, RF_GAP_FAMILY)
        assert upgrade_rf_fields(row, measured) is True
        assert row.rf_frame_gap_source == RF_GAP_MEASURED
        assert upgrade_rf_fields(row, family) is False
        assert row.rf_frame_gap_us == 10_850
