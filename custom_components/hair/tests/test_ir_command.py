"""Tests for the ir_command adapter module."""
from __future__ import annotations

import pytest

from custom_components.hair.ir_command import (
    ProntoCommand,
    RawTimingsCommand,
    build_command,
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
        assert len(timings) == 2
        # Each timing should have positive high_us and low_us
        for t in timings:
            assert t.high_us > 0
            assert t.low_us > 0

    def test_modulation_frequency(self):
        # word[1] = 0x006D = 109
        # freq = 1_000_000 / (109 * 0.241246) ≈ 38028
        cmd = ProntoCommand(PRONTO_SIMPLE)
        assert 37000 < cmd.modulation < 39000

    def test_timing_values(self):
        cmd = ProntoCommand(PRONTO_SIMPLE)
        timings = cmd.get_raw_timings()
        # word[1] = 0x6D = 109, period_us = 109 * 0.241246 ≈ 26.3
        # mark = 0x20 * 26.3 ≈ 841, space = 0x40 * 26.3 ≈ 1683
        assert 800 < timings[0].high_us < 900
        assert 1600 < timings[0].low_us < 1750

    def test_repeat_count_passthrough(self):
        cmd = ProntoCommand(PRONTO_SIMPLE, repeat_count=3)
        assert cmd.repeat_count == 3

    def test_both_burst_sequences(self):
        # 1 burst1 pair + 1 burst2 pair = 2 total
        pronto = "0000 006D 0001 0001 0020 0040 0030 0050"
        cmd = ProntoCommand(pronto)
        assert len(cmd.get_raw_timings()) == 2

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


# ---------------------------------------------------------------------------
# RawTimingsCommand
# ---------------------------------------------------------------------------

class TestRawTimingsCommand:
    """RawTimingsCommand adapter tests."""

    def test_positive_pairs(self):
        cmd = RawTimingsCommand([9000, 4500, 560, 560])
        timings = cmd.get_raw_timings()
        assert len(timings) == 2
        assert timings[0].high_us == 9000
        assert timings[0].low_us == 4500

    def test_negative_space_normalised(self):
        # HAIR stores raw as [mark, -space, mark, -space]
        cmd = RawTimingsCommand([9000, -4500, 560, -560])
        timings = cmd.get_raw_timings()
        assert timings[0].high_us == 9000
        assert timings[0].low_us == 4500

    def test_odd_timings_trailing_mark(self):
        cmd = RawTimingsCommand([9000, -4500, 560])
        timings = cmd.get_raw_timings()
        assert len(timings) == 2
        assert timings[1].high_us == 560
        assert timings[1].low_us == 0

    def test_frequency_passthrough(self):
        cmd = RawTimingsCommand([100, 200], frequency=36000)
        assert cmd.modulation == 36000

    def test_repeat_count(self):
        cmd = RawTimingsCommand([100, 200], repeat_count=5)
        assert cmd.repeat_count == 5


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
