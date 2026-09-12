"""plan_send: what one emitter is asked to do for one send.

The two-path split lives here. A row with no stored spacing gets no
plan at all and its caller runs the code it always ran; a row with one
gets a bundle on an emitter that can take it and today's per-frame
loop on an emitter that cannot (send spacing, GH #151).
"""
from __future__ import annotations

import importlib.util
from types import SimpleNamespace

import pytest

from custom_components.hair.const import (
    BROADLINK_MAX_PACKET_BYTES,
    DOMAIN,
    SEND_REPEAT_GAP,
    SEND_SILENCE_FLOOR_US,
    SEND_SPACING_MAX_MS,
    SEND_SPACING_MIN_MS,
    SINGLE_LIST_MAX_ENTRIES,
)
from custom_components.hair.ir_command import (
    TERMINATOR_SPACE_US,
    RawTimingsCommand,
    block_duration_us,
)
from custom_components.hair.send_plan import (
    broadlink_packet_bytes,
    capability,
    clear_platform_cache,
    emitter_platform,
    estimate_spacing_ms,
    plan_send,
    realised_air_ms,
    silence_us,
    spacing_air_time_ok,
)

_HAS_BROADLINK = importlib.util.find_spec("broadlink") is not None

# 10ms of block, so the arithmetic below reads at a glance.
BLOCK = [4000, -2000, 4000]
BLOCK_US = 10_000


def _inner(timings=None):
    return RawTimingsCommand(timings if timings is not None else BLOCK)


class TestTheSplit:
    def test_no_spacing_means_no_plan(self):
        # The whole two-path contract in one assertion: an old row
        # never reaches this module's output.
        assert plan_send(_inner(), 8, None, "esphome") is None

    def test_a_spacing_of_zero_is_still_a_plan(self):
        # 0 is not None. Only None means "old row"; the doors keep a
        # real value inside the bounds.
        assert plan_send(_inner(), 2, 0, "esphome") is not None


class TestCapability:
    @pytest.mark.parametrize("platform", ["esphome", "broadlink"])
    def test_the_two_that_can(self, platform):
        assert capability(platform) == "exact"

    @pytest.mark.parametrize("platform", ["mqtt", "hair", "tuya", "", None])
    def test_everything_else_cannot(self, platform):
        assert capability(platform) == "incapable"

    def test_an_unknown_entity_is_incapable_not_capable(self):
        # Unit fixtures use bare ids with no registry entry. Guessing
        # capable for those would bundle a burst at an emitter nobody
        # has checked.
        hass = SimpleNamespace(data={})
        assert emitter_platform(hass, "infrared.a") is None
        assert capability(emitter_platform(hass, "infrared.a")) == "incapable"


class TestTheCache:
    def test_a_lookup_is_remembered_and_can_be_dropped(self):
        hass = SimpleNamespace(data={DOMAIN: {}})
        assert emitter_platform(hass, "infrared.a") is None
        cache = hass.data[DOMAIN]["_send_plan_platform_cache"]
        assert cache == {"infrared.a": None}
        cache["infrared.a"] = "esphome"
        assert emitter_platform(hass, "infrared.a") == "esphome"
        clear_platform_cache(hass)
        assert hass.data[DOMAIN]["_send_plan_platform_cache"] == {}

    def test_the_cache_does_not_look_like_a_config_entry(self):
        # hass.data[DOMAIN] is keyed by entry id and _get_first_entry_data
        # walks its values looking for a "device_manager". The cache must
        # never be mistaken for an entry.
        hass = SimpleNamespace(data={DOMAIN: {}})
        emitter_platform(hass, "infrared.a")
        for value in hass.data[DOMAIN].values():
            assert "device_manager" not in value

    def test_no_domain_bucket_is_survivable(self):
        assert emitter_platform(SimpleNamespace(data={}), "infrared.a") is None
        assert emitter_platform(None, "infrared.a") is None


class TestTheSilenceFloor:
    def test_ordinary_spacing_is_the_difference(self):
        assert silence_us(BLOCK_US, 135) == 125_000

    def test_a_spacing_shorter_than_the_block_floors(self):
        # The code is simply longer than the number. It goes out as
        # fast as it can and the editor says so.
        assert silence_us(200_000, 135) == SEND_SILENCE_FLOOR_US

    def test_exactly_the_block_floors_too(self):
        assert silence_us(135_000, 135) == SEND_SILENCE_FLOOR_US


class TestTheAirTime:
    def test_count_one_is_one_block(self):
        assert realised_air_ms(_inner(), 1, 500) == 10

    def test_eight_blocks_carry_seven_gaps(self):
        # 8 x 10ms of block plus 7 x 125ms of quiet.
        assert realised_air_ms(_inner(), 8, 135) == 8 * 10 + 7 * 125

    def test_the_floor_is_counted_not_the_wish(self):
        # A 20ms ask against a 200ms block: the real air is eight
        # blocks and seven floors, not eight times twenty.
        long_block = [100_000, -50_000, 50_000]
        assert realised_air_ms(_inner(long_block), 8, 20) == 8 * 200 + 7 * 10

    def test_the_cap_reads_the_real_number(self):
        # 10 sends of a 400ms block is 4s of air whatever spacing is
        # asked for, so the cap refuses it on the block alone.
        long_block = [200_000, -100_000, 200_000]
        assert not spacing_air_time_ok(_inner(long_block), 10, 20)
        assert spacing_air_time_ok(_inner(), 8, 135)


class TestTheEstimate:
    def test_it_is_block_plus_terminator_plus_pipeline_rounded(self):
        # 10 + 50 + 60 = 120.
        assert estimate_spacing_ms(_inner()) == 120

    def test_it_rounds_to_five(self):
        assert estimate_spacing_ms(_inner([4123, -2000, 4000])) % 5 == 0

    def test_a_long_block_is_not_the_short_answer(self):
        # An AC blob must not show the NEC number. This is the
        # editor's "a long AC code shows ~400, not 175" case.
        ac = [200_000, -50_000, 50_000]
        assert estimate_spacing_ms(_inner(ac)) == 410

    def test_it_clamps_into_the_stored_range(self):
        huge = [2_000_000, -1000, 1000]
        assert estimate_spacing_ms(_inner(huge)) == SEND_SPACING_MAX_MS
        tiny = [10, -10, 10]
        assert estimate_spacing_ms(_inner(tiny)) >= SEND_SPACING_MIN_MS


class TestTheExactPath:
    def test_one_emitter_gets_one_call(self):
        plan = plan_send(_inner(), 8, 135, "esphome")
        assert plan is not None
        assert plan.exact is True
        assert plan.chunks == 1
        assert len(plan.calls) == 1
        assert plan.sleep_s == 0.0

    def test_the_one_call_is_terminated(self):
        plan = plan_send(_inner(), 8, 135, "esphome")
        assert plan.calls[0].terminate is True

    def test_the_list_carries_every_repeat_and_gap(self):
        plan = plan_send(_inner(), 3, 135, "esphome")
        timings = plan.calls[0].command.get_raw_timings()
        assert timings.count(-125_000) == 2
        assert timings == [
            *BLOCK, -125_000, *BLOCK, -125_000, *BLOCK
        ]

    def test_the_plan_air_includes_the_terminator(self):
        plan = plan_send(_inner(), 3, 135, "esphome")
        expected_us = 3 * BLOCK_US + 2 * 125_000 + TERMINATOR_SPACE_US
        assert round(plan.air_s * 1_000_000) == expected_us


class TestTheIncapablePath:
    def test_it_is_todays_loop_pace_included(self):
        plan = plan_send(_inner(), 8, 135, "mqtt")
        assert plan.exact is False
        assert len(plan.calls) == 8
        assert plan.sleep_s == SEND_REPEAT_GAP
        assert all(call.terminate for call in plan.calls)

    def test_every_call_is_the_bare_inner_command(self):
        inner = _inner()
        plan = plan_send(inner, 4, 135, "mqtt")
        assert all(call.command is inner for call in plan.calls)

    def test_an_unknown_platform_takes_the_same_path(self):
        assert plan_send(_inner(), 4, 135, None).exact is False


class TestChunking:
    def test_an_entry_cap_splits_into_the_fewest_chunks(self):
        # Three entries per block: 2000 entries is 666 blocks plus the
        # seams, so ten sends never split, but a big block does.
        big = [1] * 1200
        plan = plan_send(_inner(big), 4, 500, "esphome")
        assert plan.chunks > 1
        # Every block still goes out: the chunks partition the burst,
        # they do not drop any of it.
        total = sum(
            len(call.command.get_raw_timings()) for call in plan.calls
        )
        stripped_len = len(big) - 1  # the normalised block ends on a space
        seams = plan.chunks - 1
        assert total == 4 * stripped_len + seams
        for call in plan.calls:
            assert len(call.command.get_raw_timings()) <= (
                SINGLE_LIST_MAX_ENTRIES
            )

    def test_only_the_last_chunk_is_terminated(self):
        big = [1] * 1200
        plan = plan_send(_inner(big), 4, 500, "esphome")
        assert [call.terminate for call in plan.calls] == (
            [False] * (plan.chunks - 1) + [True]
        )

    def test_every_seam_carries_the_spacing(self):
        # The seam is the whole point: without the trailing silence the
        # gap between chunks would be whatever the pipeline gave.
        big = [1] * 1200
        plan = plan_send(_inner(big), 4, 500, "esphome")
        block_us = block_duration_us(_inner(big).get_raw_timings())
        for call in plan.calls[:-1]:
            assert call.command.get_raw_timings()[-1] == -(
                500 * 1000 - block_us
            )

    def test_a_byte_cap_splits_broadlink(self):
        plan = plan_send(_inner(), 10, 1000, "broadlink")
        for call in plan.calls:
            assert broadlink_packet_bytes(
                call.command.get_raw_timings()
            ) <= BROADLINK_MAX_PACKET_BYTES

    def test_a_single_block_too_big_to_fit_still_goes_out_alone(self):
        # Refusing to send at all would be worse than one oversized
        # call the emitter may still accept.
        huge = [1] * (SINGLE_LIST_MAX_ENTRIES + 50)
        plan = plan_send(_inner(huge), 2, 500, "esphome")
        assert plan.chunks == 2
        assert all(len(c.command.get_raw_timings()) > 0 for c in plan.calls)


class TestTheBroadlinkByteMath:
    def test_the_header_is_four_bytes(self):
        assert broadlink_packet_bytes([]) == 4

    def test_the_three_byte_threshold_is_where_the_library_puts_it(self):
        # 256 ticks of 32.84us = 8407.04us, so 8407 is still one byte
        # and 8408 is three.
        assert broadlink_packet_bytes([8407]) == 5
        assert broadlink_packet_bytes([8408]) == 7

    @pytest.mark.skipif(
        not _HAS_BROADLINK, reason="python-broadlink unavailable"
    )
    def test_it_agrees_with_the_installed_library(self):
        from broadlink.remote import pulses_to_data

        for value in (1000, 8406, 8407, 8408, 9000, 250_000):
            assert broadlink_packet_bytes([value]) == len(
                pulses_to_data([value])
            ), value
