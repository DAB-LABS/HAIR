"""Tests for the ir_command adapter module."""
from __future__ import annotations

import pytest

from custom_components.hair.ir_command import (
    ProntoCommand,
    RawTimingsCommand,
    build_command,
    raw_to_pronto,
)

# ---------------------------------------------------------------------------
# ProntoCommand
# ---------------------------------------------------------------------------

# Minimal valid Pronto hex: learned format, freq word, 2 burst1 pairs, 0 burst2
PRONTO_SIMPLE = "0000 006D 0002 0000 0020 0040 0020 0040"


class TestProntoCommand:
    """ProntoCommand adapter tests."""

    def test_basic_parse(self):
        cmd = ProntoCommand(PRONTO_SIMPLE)
        timings = cmd.get_raw_timings()
        # 2 pairs -> 4 values (mark, -space, mark, -space)
        assert len(timings) == 4
        # All values are plain ints
        for t in timings:
            assert isinstance(t, int)

    def test_signed_convention(self):
        cmd = ProntoCommand(PRONTO_SIMPLE)
        timings = cmd.get_raw_timings()
        # Alternating positive (mark) and negative (space)
        assert timings[0] > 0   # mark
        assert timings[1] < 0   # space
        assert timings[2] > 0   # mark
        assert timings[3] < 0   # space

    def test_modulation_frequency(self):
        # word[1] = 0x006D = 109
        # freq = 1_000_000 / (109 * 0.241246) ~ 38028
        cmd = ProntoCommand(PRONTO_SIMPLE)
        assert 37000 < cmd.modulation < 39000

    def test_timing_values(self):
        cmd = ProntoCommand(PRONTO_SIMPLE)
        timings = cmd.get_raw_timings()
        # word[1] = 0x6D = 109, period_us = 109 * 0.241246 ~ 26.3
        # mark = 0x20 * 26.3 ~ 841, space = 0x40 * 26.3 ~ 1683
        assert 800 < timings[0] < 900        # mark
        assert -1750 < timings[1] < -1600     # -space

    def test_repeat_count_passthrough(self):
        cmd = ProntoCommand(PRONTO_SIMPLE, repeat_count=3)
        assert cmd.repeat_count == 3

    def test_both_burst_sequences(self):
        # 1 burst1 pair + 1 burst2 pair = 2 total pairs = 4 timing values
        pronto = "0000 006D 0001 0001 0020 0040 0030 0050"
        cmd = ProntoCommand(pronto)
        assert len(cmd.get_raw_timings()) == 4

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            ProntoCommand("0000 006D")

    def test_zero_frequency_raises(self):
        with pytest.raises(ValueError, match="frequency word is zero"):
            ProntoCommand("0000 0000 0001 0000 0020 0040")

    def test_insufficient_timing_words_raises(self):
        # Claims 2 pairs but only provides 2 words (1 pair)
        with pytest.raises(ValueError, match="pairs"):
            ProntoCommand("0000 006D 0002 0000 0020 0040")

    def test_get_raw_timings_returns_copy(self):
        cmd = ProntoCommand(PRONTO_SIMPLE)
        t1 = cmd.get_raw_timings()
        t2 = cmd.get_raw_timings()
        assert t1 == t2
        assert t1 is not t2

    def test_trailing_mark_no_zero_space(self):
        """A pair with space_periods=0 should emit only the mark, not -0."""
        pronto = "0000 006D 0001 0000 0020 0000"
        cmd = ProntoCommand(pronto)
        timings = cmd.get_raw_timings()
        # Only the mark, no trailing -0
        assert len(timings) == 1
        assert timings[0] > 0


# ---------------------------------------------------------------------------
# RawTimingsCommand
# ---------------------------------------------------------------------------

class TestRawTimingsCommand:
    """RawTimingsCommand adapter tests."""

    def test_positive_pairs(self):
        cmd = RawTimingsCommand([9000, 4500, 560, 560])
        timings = cmd.get_raw_timings()
        assert len(timings) == 4
        assert timings[0] == 9000
        assert timings[1] == -4500
        assert timings[2] == 560
        assert timings[3] == -560

    def test_negative_space_normalised(self):
        # Already signed input
        cmd = RawTimingsCommand([9000, -4500, 560, -560])
        timings = cmd.get_raw_timings()
        assert timings[0] == 9000
        assert timings[1] == -4500

    def test_odd_timings_trailing_mark(self):
        cmd = RawTimingsCommand([9000, -4500, 560])
        timings = cmd.get_raw_timings()
        assert len(timings) == 3
        assert timings[2] == 560  # trailing mark, positive

    def test_frequency_passthrough(self):
        cmd = RawTimingsCommand([100, 200], frequency=36000)
        assert cmd.modulation == 36000

    def test_repeat_count(self):
        cmd = RawTimingsCommand([100, 200], repeat_count=5)
        assert cmd.repeat_count == 5

    def test_all_values_are_ints(self):
        cmd = RawTimingsCommand([9000, -4500, 560, -560, 560])
        for t in cmd.get_raw_timings():
            assert isinstance(t, int)


# ---------------------------------------------------------------------------
# build_command factory
# ---------------------------------------------------------------------------

class TestBuildCommand:
    """build_command() factory tests."""

    def test_pronto_by_protocol(self):
        cmd = build_command(protocol="PRONTO", code=PRONTO_SIMPLE)
        assert isinstance(cmd, ProntoCommand)

    def test_pronto_case_insensitive(self):
        cmd = build_command(protocol="pronto", code=PRONTO_SIMPLE)
        assert isinstance(cmd, ProntoCommand)

    def test_pronto_by_code_prefix(self):
        cmd = build_command(protocol=None, code=PRONTO_SIMPLE)
        assert isinstance(cmd, ProntoCommand)

    def test_raw_timings_fallback(self):
        cmd = build_command(
            protocol="NEC", code=None, raw_timings=[9000, -4500, 560]
        )
        assert isinstance(cmd, RawTimingsCommand)

    def test_raw_timings_no_protocol(self):
        cmd = build_command(raw_timings=[9000, -4500])
        assert isinstance(cmd, RawTimingsCommand)

    def test_raises_when_nothing_usable(self):
        with pytest.raises(ValueError, match="no Pronto hex"):
            build_command(protocol="NEC", code="0x1234")

    def test_raises_no_data_at_all(self):
        with pytest.raises(ValueError):
            build_command()

    def test_repeat_count_forwarded(self):
        cmd = build_command(
            protocol="PRONTO", code=PRONTO_SIMPLE, repeat_count=2
        )
        assert cmd.repeat_count == 2

    def test_pronto_returns_list_of_int(self):
        """Verify the v2.0 contract: get_raw_timings() returns list[int]."""
        cmd = build_command(protocol="PRONTO", code=PRONTO_SIMPLE)
        timings = cmd.get_raw_timings()
        assert all(isinstance(t, int) for t in timings)

    def test_raw_returns_list_of_int(self):
        """Verify the v2.0 contract: get_raw_timings() returns list[int]."""
        cmd = build_command(raw_timings=[9000, -4500, 560])
        timings = cmd.get_raw_timings()
        assert all(isinstance(t, int) for t in timings)


# ---------------------------------------------------------------------------
# raw_to_pronto encoder
# ---------------------------------------------------------------------------

class TestRawToPronto:
    """Tests for raw_to_pronto() encoder."""

    def test_basic_encoding(self):
        """Encode simple timings and verify the Pronto format."""
        pronto = raw_to_pronto([9000, -4500, 560, -560])
        words = pronto.split()
        assert words[0] == "0000"  # learned format
        assert len(words) >= 8     # header(4) + 2 pairs * 2 words

    def test_frequency_word(self):
        """Verify the frequency word for 38 kHz."""
        pronto = raw_to_pronto([1000, -1000], frequency=38000)
        words = pronto.split()
        freq_word = int(words[1], 16)
        # 1_000_000 / (38000 * 0.241246) ~ 109 = 0x006D
        assert 100 < freq_word < 120

    def test_round_trip(self):
        """Encode raw -> Pronto -> ProntoCommand -> get_raw_timings.

        The round-trip should produce values close to the originals
        (within rounding tolerance of the Pronto period quantization).
        """
        original = [9000, -4500, 560, -560, 560, -1690]
        pronto = raw_to_pronto(original, frequency=38000)

        cmd = ProntoCommand(pronto)
        recovered = cmd.get_raw_timings()

        assert len(recovered) == len(original)
        for orig, rec in zip(original, recovered):
            # Rounding tolerance: Pronto period is ~26us, so values
            # can differ by up to ~26us per quantization step.
            assert abs(abs(orig) - abs(rec)) < 50, (
                f"Round-trip mismatch: {orig} vs {rec}"
            )

    def test_burst1_count(self):
        """Verify burst1_count matches the number of pairs."""
        pronto = raw_to_pronto([100, -200, 300, -400, 500, -600])
        words = [int(w, 16) for w in pronto.split()]
        assert words[2] == 3  # 3 pairs in burst1
        assert words[3] == 0  # 0 pairs in burst2

    def test_odd_timings_trailing_mark(self):
        """Odd number of timings: trailing mark gets space=0."""
        pronto = raw_to_pronto([1000, -2000, 500])
        words = [int(w, 16) for w in pronto.split()]
        # 2 pairs: (1000, -2000) and (500, 0)
        assert words[2] == 2

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            raw_to_pronto([])

    def test_zero_frequency_raises(self):
        with pytest.raises(ValueError, match="frequency"):
            raw_to_pronto([100, -200], frequency=0)

    def test_unsigned_timings_work(self):
        """Unsigned (all positive) alternating timings should work."""
        pronto = raw_to_pronto([9000, 4500, 560, 560])
        assert pronto.startswith("0000")
