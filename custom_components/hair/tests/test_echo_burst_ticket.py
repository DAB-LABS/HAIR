"""The echo ticket sized to the send that minted it.

A ticket used to be worth one claim and to live for a fixed window,
which was right when every send was a frame or two. A whole-frame
repeat is neither: eight frames at one receiver are eight captures, and
a bundled burst keeps the air for over a second past the call that
started it. Both regimes leak real presses into the trigger pipeline
unless the ticket knows how long the send is and how many echoes it can
legitimately produce (send spacing, GH #151).
"""
from __future__ import annotations

from time import monotonic
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.const import (
    MIRROR_DEVICE_FP,
    PINNED_ECHO_GUARD_S,
)
from custom_components.hair.ir_command import RawTimingsCommand, raw_to_pronto
from custom_components.hair.models import CaptureResult
from custom_components.hair.signal_monitor import SignalMonitor, normalize

from .test_signal_monitor import (
    _make_hair_store,
    _make_hass,
    _make_signal_store,
)

ATHOM = "infrared.athom_rx"
PUCK = "infrared.garage_workbench_ir_puck"

# A short undecodable frame, so every capture below is shape-matched
# rather than decoded: 10ms of block, the arithmetic of the plan.
FRAME = [4000, -2000, 4000]
# The same frame with its leader mark clipped, as a receiver hands back
# a fragment it caught late.
TRUNCATED = [1800, -2000, 4000]
SILENCE_US = 125_000


def _monitor():
    hass = _make_hass()
    store = _make_signal_store(hass)
    trigger_manager = MagicMock()
    monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)
    return monitor, trigger_manager


def _capture(timings):
    """A parsed capture of ``timings``, as a receiver hands it up.

    Shaped exactly like ``EventParser.parse_received_signal``'s tail:
    the raw pulse train plus the Pronto rendering of it, which is what
    every fingerprint in the ticket is computed from.
    """
    raw = list(timings)
    return CaptureResult(
        protocol="PRONTO",
        code=raw_to_pronto(raw, frequency=38000),
        raw_timings=raw,
        frequency=38000,
    )


def _burst_timings(count=8, silence_us=SILENCE_US):
    out = list(FRAME)
    for _ in range(count - 1):
        out.append(-silence_us)
        out.extend(FRAME)
    return out


def _send(monitor, *, count, air_s, burst, emitters=(ATHOM,)):
    """record_send exactly as a transmit path calls it, then arm."""
    monitor.record_send(
        RawTimingsCommand(FRAME),
        "Amplificateur Pioneer / Power",
        list(emitters),
        send_count=count,
        air_s=air_s,
        burst=burst,
    )
    exp = monitor._echo_expectations[-1]
    monitor._arm_expectation(exp, monotonic())
    return exp


class TestTheWindow:
    def test_the_guard_outlives_an_eight_send_burst(self):
        # 8 frames at 135ms is 1.25s of air. A guard that expires
        # before the burst does turns HAIR's own last frames into a
        # handset press.
        monitor, _ = _monitor()
        exp = _send(monitor, count=8, air_s=1.25, burst=(8, SILENCE_US))
        assert exp["guard_until"] - monotonic() > 1.0
        assert exp["guard_until"] - monotonic() > PINNED_ECHO_GUARD_S

    def test_an_ordinary_send_barely_moves(self):
        # The old path's short sends must not suddenly hold a window
        # open for seconds; the margin alone is the whole widening.
        monitor, _ = _monitor()
        exp = _send(monitor, count=1, air_s=0.06, burst=None)
        assert exp["extra_window_s"] < 0.6

    def test_the_ttl_is_widened_by_the_same_figure(self):
        monitor, _ = _monitor()
        plain = _send(monitor, count=1, air_s=0.0, burst=None)
        long_send = _send(monitor, count=10, air_s=3.0, burst=(10, 290_000))
        assert long_send["expires"] - plain["expires"] > 2.9
        assert long_send["garble_expires"] - plain["garble_expires"] > 2.9


class TestTheBudget:
    @pytest.mark.asyncio
    async def test_an_eight_send_burst_leaks_nothing(self):
        """Today's regime, on the old path: one press, eight frames on
        the air, eight captures at the receiver, no trigger fires."""
        monitor, tm = _monitor()
        _send(monitor, count=8, air_s=1.25, burst=None)
        for _ in range(8):
            await monitor._process_parsed_signal(
                _capture(FRAME), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_two_emitter_three_by_two_send_leaks_nothing(self):
        """Two emitters times three frames is six hearings at one
        receiver, spread over about 1.7s once the staggers are counted."""
        monitor, tm = _monitor()
        _send(
            monitor, count=3, air_s=1.7, burst=None,
            emitters=(ATHOM, PUCK),
        )
        for _ in range(3):
            await monitor._process_parsed_signal(
                _capture(FRAME), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_ten_by_three_hundred_burst_leaks_nothing(self):
        """The new path at its longest: ten sends 300ms apart, just
        under the air-time cap."""
        monitor, tm = _monitor()
        _send(monitor, count=10, air_s=2.8, burst=(10, 290_000))
        for _ in range(10):
            await monitor._process_parsed_signal(
                _capture(FRAME), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_the_budget_is_the_send_count_and_no_more(self):
        """The cost of the widened window, recorded rather than hidden:
        a genuine press inside the window, after the budget is spent,
        is the first capture that fires."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=3, air_s=0.4, burst=None)
        # Close the guard AND the garble window: both are backstops for
        # captures the budget did not cover, and this test is about the
        # budget itself. The stand-in frame below does not decode, so
        # without this the swallow would catch it and the assertion
        # would be measuring the wrong mechanism.
        exp["guard_until"] = 0.0
        exp["garble_expires"] = monotonic() - 1.0
        for _ in range(3):
            await monitor._process_parsed_signal(
                _capture(FRAME), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        assert tm.on_signal_captured.call_count == 1

    @pytest.mark.asyncio
    async def test_a_press_after_the_window_closes_always_fires(self):
        monitor, tm = _monitor()
        exp = _send(monitor, count=8, air_s=1.25, burst=None)
        exp["expires"] = monotonic() - 1.0
        exp["garble_expires"] = monotonic() - 1.0
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        assert tm.on_signal_captured.call_count == 1

    @pytest.mark.asyncio
    async def test_two_receivers_each_get_their_own_budget(self):
        monitor, tm = _monitor()
        # Seed the Mirror row the way record_send's own task would, so
        # heard_by has something to enrich.
        await monitor._mirror_upsert(
            normalize(_capture(FRAME)), decoded_fp=None,
            echo_source="Amplificateur Pioneer / Power -- via Emitter",
            reset_heard=True,
        )
        exp = _send(monitor, count=2, air_s=0.3, burst=None)
        exp["guard_until"] = 0.0
        for receiver in (ATHOM, ATHOM, PUCK, PUCK):
            await monitor._process_parsed_signal(
                _capture(FRAME), receiver_entity_id=receiver
            )
        tm.on_signal_captured.assert_not_called()
        assert exp["claims_left"] == {ATHOM: 0, PUCK: 0}
        row = monitor._signal_store.get_device_by_fingerprint(
            MIRROR_DEVICE_FP
        ).signals[0]
        assert sorted(row.heard_by) == sorted([ATHOM, PUCK])

    @pytest.mark.asyncio
    async def test_a_hand_built_ticket_still_gets_exactly_one_claim(self):
        """Every fixture written before this feature omits the budget
        keys, and must keep the single-use behaviour it was written for."""
        monitor, tm = _monitor()
        _send(monitor, count=1, air_s=0.0, burst=None)
        exp = monitor._echo_expectations[-1]
        exp.pop("claim_budget")
        exp.pop("claims_left")
        exp["guard_until"] = 0.0
        exp["garble_expires"] = monotonic() - 1.0
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        tm.on_signal_captured.assert_not_called()
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        assert tm.on_signal_captured.call_count == 1


class TestTheBurstShape:
    @pytest.mark.asyncio
    async def test_a_merged_capture_of_the_whole_burst_claims(self):
        """A receiver that hears the bundle as ONE transmission hands
        back one long capture. It matches neither the frame's identity
        nor its shape, and without the burst shape it minted a junk
        Sniffer row and fired a trigger every time."""
        monitor, tm = _monitor()
        _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        await monitor._process_parsed_signal(
            _capture(_burst_timings(4)), receiver_entity_id=ATHOM
        )
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_merged_capture_spends_the_whole_budget(self):
        """Everything HAIR sent has now been heard, so there is nothing
        left out there to claim; the next capture is a real press."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        await monitor._process_parsed_signal(
            _capture(_burst_timings(4)), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 0
        exp["guard_until"] = 0.0
        exp["garble_expires"] = monotonic() - 1.0
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        assert tm.on_signal_captured.call_count == 1

    def test_an_old_path_send_carries_no_burst_shape(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=None)
        assert exp["burst_sig_fp"] is None
        assert exp["burst_sl"] is None


class TestThePinnedRegime:
    @pytest.mark.asyncio
    async def test_a_pinned_remote_does_not_run_away_on_either_path(self):
        """The failure pin_retransmit.py documents: an echo read as a
        press retransmits, echoes, and breeds. Neither an eight-frame
        old-path send nor a bundled one may reach the triggers."""
        for burst in (None, (8, SILENCE_US)):
            monitor, tm = _monitor()
            _send(monitor, count=8, air_s=1.25, burst=burst)
            for _ in range(8):
                await monitor._process_parsed_signal(
                    _capture(FRAME), receiver_entity_id=ATHOM
                )
            tm.on_signal_captured.assert_not_called()


class TestTheGarbleSwallow:
    @pytest.mark.asyncio
    async def test_a_mangled_frame_of_a_burst_is_swallowed(self):
        """Frame three comes back with its tail merged. It decodes as
        nothing and misses every identity, so only the shape match can
        recognise it -- and it spends a claim like a clean echo would."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=8, air_s=1.25, burst=(8, SILENCE_US))
        exp["guard_until"] = 0.0
        mangled = [4000, -2000, 4000, -1200, 900]
        with patch(
            "custom_components.hair.signal_monitor."
            "_sl_fuzzy_substring_ratio",
            return_value=0.0,
        ):
            await monitor._process_parsed_signal(
                _capture(mangled), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()
        # Its own allowance, not the clean budget: the frames the
        # receiver merged are counted there, and a fragment of the same
        # burst arrives after that budget is gone.
        assert exp["garble_left"][ATHOM] == 7
        assert ATHOM not in exp["claims_left"]

    @pytest.mark.asyncio
    async def test_the_swallow_runs_out_with_the_budget(self):
        monitor, tm = _monitor()
        exp = _send(monitor, count=1, air_s=0.06, burst=None)
        exp["guard_until"] = 0.0
        mangled = [4000, -2000, 4000, -1200, 900]
        with patch(
            "custom_components.hair.signal_monitor."
            "_sl_fuzzy_substring_ratio",
            return_value=0.0,
        ):
            await monitor._process_parsed_signal(
                _capture(mangled), receiver_entity_id=ATHOM
            )
            tm.on_signal_captured.assert_not_called()
            await monitor._process_parsed_signal(
                _capture(mangled), receiver_entity_id=ATHOM
            )
        assert tm.on_signal_captured.call_count == 1


class TestHowTheTwoShapesAreToldApart:
    def test_the_identity_is_the_same_and_the_length_is_not(self):
        """A Pronto identity stops at the end-of-signal gap, and the
        first gap in a burst IS the spacing -- so a merged capture
        usually carries the SAME fingerprint as one frame. Length is
        what separates them, which is why the claim reads that and not
        the fingerprint."""
        one = normalize(_capture(FRAME))
        many = normalize(_capture(_burst_timings(4)))
        assert one.sig_fp == many.sig_fp
        assert len(many.raw_timings) >= 2 * len(one.raw_timings)

    @pytest.mark.asyncio
    async def test_a_single_frame_does_not_spend_the_whole_budget(self):
        """The other side of that coin: since the fingerprints match, a
        claim that read identity alone would treat frame one of a burst
        as the whole burst and hand the rest to the triggers."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 3
        tm.on_signal_captured.assert_not_called()


class TestAPartialMerge:
    """What a receiver actually hands back when it merges.

    A receiver merges whatever arrives inside its own idle window, and
    that is rarely all or nothing: the bench (QA on VM999, 2026-09-12)
    got a four-send burst back as one frame, then two frames merged
    into one capture, then one frame, then a truncated frame whose
    leader mark was clipped.

    Reading a two-frame merge as "the whole burst" spent every
    remaining claim on it and left the rest of the burst unprotected.
    A capture now pays for the frames it carries.
    """

    @pytest.mark.asyncio
    async def test_a_two_frame_merge_spends_two(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        # The guard would cover this on its own; close it so the
        # accounting below is what is being measured.
        exp["guard_until"] = 0.0
        await monitor._process_parsed_signal(
            _capture([*FRAME, -SILENCE_US, *FRAME]), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 2

    @pytest.mark.asyncio
    async def test_a_three_frame_merge_spends_three(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        exp["guard_until"] = 0.0
        await monitor._process_parsed_signal(
            _capture(_burst_timings(3)), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 1

    @pytest.mark.asyncio
    async def test_a_single_frame_still_spends_one(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        exp["guard_until"] = 0.0
        await monitor._process_parsed_signal(
            _capture(FRAME), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 3

    @pytest.mark.asyncio
    async def test_a_whole_burst_capture_still_spends_everything(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=(4, SILENCE_US))
        exp["guard_until"] = 0.0
        await monitor._process_parsed_signal(
            _capture(_burst_timings(4)), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 0

    @pytest.mark.asyncio
    async def test_a_merge_can_never_overspend(self):
        """A capture longer than the burst cannot take the budget
        negative and cannot borrow against another send's ticket."""
        monitor, _ = _monitor()
        exp = _send(monitor, count=2, air_s=0.3, burst=(2, SILENCE_US))
        exp["guard_until"] = 0.0
        await monitor._process_parsed_signal(
            _capture(_burst_timings(8)), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 0

    @pytest.mark.asyncio
    async def test_an_old_path_send_still_spends_one_per_capture(self):
        """No burst means no merging to account for: every capture is
        one frame and pays for one."""
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.5, burst=None)
        exp["guard_until"] = 0.0
        await monitor._process_parsed_signal(
            _capture(_burst_timings(4)), receiver_entity_id=ATHOM
        )
        assert exp["claims_left"][ATHOM] == 3


class TestAShortSeamMergeIsTheSwallowsJob:
    """Where the proportional spend stops reaching, and what covers it.

    A Pronto identity ends at a space of PRONTO_GAP_THRESHOLD or more,
    about 27 ms. A merge whose seam is longer than that still carries
    the single frame's fingerprint, which is the case above. A merge at
    a SHORT spacing does not: the frames run together into an identity
    that is neither the frame's nor the whole burst's, so the clean
    claim cannot recognise it at all.

    That is the bench's own case (spacing 20, silence on the 10 ms
    floor, receiver idle 10.1 ms), and what covers it is the garbled-
    echo swallow, which matches on shape rather than identity. Which is
    exactly why the swallow needed an allowance of its own.
    """

    def _bench_sequence(self):
        """F, FF-merged, F, truncated-F: what the Athom handed up."""
        merged = [*FRAME, -10_000, *FRAME]
        truncated = [1800, -2000, 4000]  # leader mark clipped short
        return [list(FRAME), merged, list(FRAME), truncated]

    def test_a_short_seam_merge_carries_neither_fingerprint(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=4, air_s=0.1, burst=(4, 10_000))
        merged = normalize(_capture([*FRAME, -10_000, *FRAME]))
        assert merged.sig_fp != exp["sig_fp"]
        assert merged.sig_fp != exp["burst_sig_fp"]

    @pytest.mark.asyncio
    async def test_the_whole_bench_sequence_stays_ours(self):
        monitor, tm = _monitor()
        exp = _send(monitor, count=4, air_s=0.1, burst=(4, 10_000))
        # Both backstops closed but the swallow: this pins that the
        # swallow alone is enough for the sequence that broke.
        exp["guard_until"] = 0.0
        for timings in self._bench_sequence():
            await monitor._process_parsed_signal(
                _capture(timings), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()


class TestTheSwallowHasItsOwnAllowance:
    def _spent(self, exp, receiver=ATHOM):
        """The clean budget already gone, the way the merges spend it."""
        exp.setdefault("claims_left", {})[receiver] = 0

    @pytest.mark.asyncio
    async def test_a_fragment_after_the_clean_budget_is_still_ours(self):
        """The exact shape of the defect: the merges spend the clean
        budget, and the truncated fragment arrives with nothing left.
        It is still this send coming back."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=2, air_s=0.1, burst=(2, 10_000))
        exp["guard_until"] = 0.0
        self._spent(exp)
        with patch(
            "custom_components.hair.signal_monitor."
            "_sl_fuzzy_substring_ratio",
            return_value=0.0,
        ):
            await monitor._process_parsed_signal(
                _capture(TRUNCATED), receiver_entity_id=ATHOM
            )
        tm.on_signal_captured.assert_not_called()
        assert exp["garble_left"][ATHOM] == 1
        # And it did not reach into the clean budget to do it.
        assert exp["claims_left"][ATHOM] == 0

    @pytest.mark.asyncio
    async def test_the_same_fragment_after_the_window_is_a_press(self):
        """The allowance is bounded by the garble window, not by the
        clean budget. Once the window closes, an undecodable capture is
        somebody else's, whatever it looks like."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=2, air_s=0.1, burst=(2, 10_000))
        exp["guard_until"] = 0.0
        exp["garble_expires"] = monotonic() - 1.0
        self._spent(exp)
        with patch(
            "custom_components.hair.signal_monitor."
            "_sl_fuzzy_substring_ratio",
            return_value=0.0,
        ):
            await monitor._process_parsed_signal(
                _capture(TRUNCATED), receiver_entity_id=ATHOM
            )
        assert tm.on_signal_captured.call_count == 1

    @pytest.mark.asyncio
    async def test_the_allowance_is_per_receiver(self):
        monitor, _ = _monitor()
        exp = _send(monitor, count=2, air_s=0.1, burst=(2, 10_000))
        exp["guard_until"] = 0.0
        self._spent(exp, ATHOM)
        self._spent(exp, PUCK)
        with patch(
            "custom_components.hair.signal_monitor."
            "_sl_fuzzy_substring_ratio",
            return_value=0.0,
        ):
            for receiver in (ATHOM, PUCK):
                await monitor._process_parsed_signal(
                    _capture(TRUNCATED), receiver_entity_id=receiver,
                )
        assert exp["garble_left"] == {ATHOM: 1, PUCK: 1}

    @pytest.mark.asyncio
    async def test_the_allowance_runs_out(self):
        """Bounded, not free. Once a receiver has been handed back as
        many damaged copies as HAIR put frames in the air, the next one
        is treated as a press."""
        monitor, tm = _monitor()
        exp = _send(monitor, count=2, air_s=0.1, burst=(2, 10_000))
        exp["guard_until"] = 0.0
        self._spent(exp)
        with patch(
            "custom_components.hair.signal_monitor."
            "_sl_fuzzy_substring_ratio",
            return_value=0.0,
        ):
            for _ in range(3):
                await monitor._process_parsed_signal(
                    _capture(TRUNCATED), receiver_entity_id=ATHOM
                )
        assert exp["garble_left"][ATHOM] == 0
        assert tm.on_signal_captured.call_count == 1
