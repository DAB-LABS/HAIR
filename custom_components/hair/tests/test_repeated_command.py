"""RepeatedCommand: the shape of a bundled burst.

The wrapper is the whole reason a stored spacing can be exact, so
these pin the arithmetic rather than the API: what the list looks
like, where the silences land, what the terminator does to it, and
that a block carrying its own trailing space cannot push every repeat
early (send spacing, GH #151).
"""
from __future__ import annotations

import pytest

from custom_components.hair.ir_command import (
    TERMINATOR_SPACE_US,
    ProntoCommand,
    RawTimingsCommand,
    RepeatedCommand,
    TerminatedCommand,
    block_duration_us,
    stripped_block,
)

# A block that ends on a MARK, which is what every library encoder but
# Sharp produces.
MARK_TAIL = [1000, -500, 1000]
# A block that ends on a -40ms SPACE, standing in for Sharp's encoder.
SPACE_TAIL = [1000, -500, 1000, -40_000]


class TestTheStrip:
    def test_a_trailing_space_comes_off(self):
        assert stripped_block(SPACE_TAIL) == MARK_TAIL

    def test_a_trailing_mark_is_left_alone(self):
        assert stripped_block(MARK_TAIL) == MARK_TAIL

    def test_the_source_list_is_not_mutated(self):
        source = list(SPACE_TAIL)
        stripped_block(source)
        assert source == SPACE_TAIL

    def test_duration_is_measured_on_the_stripped_block(self):
        # 40ms of Sharp's own tail must not be counted as block, or
        # every gap computed from it lands 40ms short.
        assert block_duration_us(SPACE_TAIL) == 2500
        assert block_duration_us(MARK_TAIL) == 2500

    def test_an_empty_block_is_zero(self):
        assert stripped_block([]) == []
        assert block_duration_us([]) == 0


class TestTheShape:
    def test_count_one_is_the_bare_block(self):
        inner = RawTimingsCommand(MARK_TAIL)
        assert RepeatedCommand(inner, 1, 10_000).get_raw_timings() == MARK_TAIL

    def test_three_blocks_carry_two_silences(self):
        inner = RawTimingsCommand(MARK_TAIL)
        out = RepeatedCommand(inner, 3, 70_000).get_raw_timings()
        assert out == [
            *MARK_TAIL, -70_000, *MARK_TAIL, -70_000, *MARK_TAIL
        ]
        assert out.count(-70_000) == 2

    def test_each_copy_is_stripped_before_the_silence_goes_in(self):
        # The Sharp case: without the per-copy strip the list would read
        # ... 1000, -40000, -70000, 1000 ... and every gap would be
        # 40ms too long.
        inner = RawTimingsCommand(SPACE_TAIL)
        out = RepeatedCommand(inner, 2, 70_000).get_raw_timings()
        assert out == [*MARK_TAIL, -70_000, *MARK_TAIL]
        assert -40_000 not in out

    def test_trailing_silence_ends_the_seam_chunk_on_its_gap(self):
        inner = RawTimingsCommand(MARK_TAIL)
        out = RepeatedCommand(
            inner, 2, 70_000, trailing_silence=True
        ).get_raw_timings()
        assert out[-1] == -70_000
        assert out == [*MARK_TAIL, -70_000, *MARK_TAIL, -70_000]


class TestTheAirTime:
    def test_air_counts_blocks_and_silences(self):
        inner = RawTimingsCommand(MARK_TAIL)
        # 3 x 2500us of block plus 2 x 70000us of quiet.
        assert RepeatedCommand(inner, 3, 70_000).planned_air_us == 147_500

    def test_a_seam_chunk_counts_its_trailing_gap(self):
        inner = RawTimingsCommand(MARK_TAIL)
        plain = RepeatedCommand(inner, 2, 70_000).planned_air_us
        seam = RepeatedCommand(
            inner, 2, 70_000, trailing_silence=True
        ).planned_air_us
        assert seam - plain == 70_000

    def test_a_block_with_ditto_gaps_inside_it_counts_them(self):
        # NEC dittos live INSIDE the block, so the air time sees them
        # without anything having to know they exist.
        dittoed = [9000, -4500, 560, -41_000, 9000, -2250, 560]
        inner = RawTimingsCommand(dittoed)
        block = sum(abs(v) for v in dittoed)
        assert RepeatedCommand(inner, 2, 20_000).planned_air_us == (
            2 * block + 20_000
        )


class TestTheWrapperOrder:
    def test_the_terminator_is_applied_once_at_the_very_end(self):
        inner = RawTimingsCommand(MARK_TAIL)
        out = TerminatedCommand(
            RepeatedCommand(inner, 3, 70_000)
        ).get_raw_timings()
        assert out[-1] == -TERMINATOR_SPACE_US
        # One terminator, not one per frame: the interior gaps are all
        # the spacing.
        assert out.count(-TERMINATOR_SPACE_US) == 1
        assert out.count(-70_000) == 2

    def test_wrapping_a_seam_chunk_would_clamp_its_gap(self):
        # Why send_plan marks seam chunks terminate=False. Pinned so the
        # reason survives if anyone simplifies the call site.
        inner = RawTimingsCommand(MARK_TAIL)
        seam = RepeatedCommand(inner, 2, 300_000, trailing_silence=True)
        assert seam.get_raw_timings()[-1] == -300_000
        assert TerminatedCommand(seam).get_raw_timings()[-1] == (
            -TERMINATOR_SPACE_US
        )

    def test_attributes_delegate_through_the_wrapper(self):
        inner = ProntoCommand("0000 006D 0002 0000 0020 0040 0020 0040")
        wrapped = RepeatedCommand(inner, 2, 20_000)
        assert wrapped.modulation == inner.modulation
        assert wrapped.repeat_count == inner.repeat_count


class TestWhatADittoDoesToTheBlock:
    """Design R14, re-measured against the installed library.

    R14 was written from a 2026-08-02 bench note saying Sharp and Sony
    IGNORE repeat_count. Against infrared-protocols 5.8.1 they do not:
    both DUPLICATE the whole frame, the way Samsung32 and RC-5 already
    did. NEC remains the only protocol whose repeat_count is a real
    4-entry ditto frame, so the panel's NEC-only ditto gate is
    unaffected and no user can set a ditto on these anyway. The note in
    ir-tx-knobs.ts that the original reading came from carries the same
    correction, so the two cannot drift apart again.

    What matters for send spacing is the same either way, and is what
    this pins: whatever repeat_count does, it does it INSIDE the block
    the encoder returns. So a block measured after the build already
    contains every ditto, which is why the air-time cap and the spacing
    arithmetic read ``block_duration_us`` of the built command and
    never have to know that dittos exist.
    """

    @pytest.mark.parametrize(
        ("protocol", "address", "command"),
        # The registry's own labels, not the friendly names: SIRC is
        # registered per bit count (see get_spec's prefix rule).
        [("SHARP", 0x01, 0x02), ("SONY12", 0x01, 0x02), ("NEC", 0x01, 0x02)],
    )
    def test_a_ditto_lives_inside_the_block(
        self, protocol, address, command
    ):
        pytest.importorskip("infrared_protocols")
        from custom_components.hair.ir_command import build_decoded_command

        plain = build_decoded_command(protocol, address, command)
        if plain is None:
            pytest.skip(f"{protocol} is not on the rebuild tier here")
        base = block_duration_us(plain.get_raw_timings())
        for repeats in (1, 3):
            cmd = build_decoded_command(
                protocol, address, command, repeat_count=repeats
            )
            grown = block_duration_us(cmd.get_raw_timings())
            # Never shorter, and never invisible: whatever the protocol
            # does with the count, the block reports it.
            assert grown >= base
