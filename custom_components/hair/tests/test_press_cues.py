"""Press cues: a quick double press counts twice (GH #237, S1).

A quick double press of one button used to land inside the Sniffer's
and the trigger's windows, so its second press read as a repeat of the
first. press_cues.py reads three protocol families whose frames say for
themselves that a new press began, and lets exactly those presses
through.

Every timing below is hand-written, chosen against the repeat periods
in const.py: NEC 108 ms, RC5 114 ms, RC6 107 ms, JVC 58 ms, each times
the 1.2 factor for the soonest a cue may fire. A quick double press is
written as 180 to 250 ms between presses, inside the 300 ms windows and
well outside any repeat period.

The safety property is what most of these pin: a cue says "new press"
or nothing, so every sequence that fires today still fires the same
way, and the only change is a second fire for a press the frame proves.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import signal_monitor as sm
from custom_components.hair.const import (
    MULTI_RECEIVER_DEDUP_WINDOW_S,
    PRESS_CUE_REPEAT_FACTOR,
    PRESS_CUE_REPEAT_PERIOD_S,
    PRESS_CUE_TTL_S,
    SIGNAL_REPEAT_SUPPRESS_MS,
    TRIGGER_FIRE_DEDUP_WINDOW_S,
)
from custom_components.hair.decoders import jvc as jvc_mod
from custom_components.hair.decoders.jvc import JVCCommand
from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.rc6 import RC6Command
from custom_components.hair.models import IRTrigger
from custom_components.hair.press_cues import (
    RULE_DITTO,
    RULE_LEADER,
    RULE_TOGGLE,
    PressCue,
    PressCueTracker,
    cue_rule,
    min_gap_s,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager

from .test_decode_coverage import junk_state_frame
from .test_signal_monitor import _make_hair_store, _make_hass, _make_signal_store

RX_A = "infrared.living_room_rx"
RX_B = "infrared.kitchen_rx"
RM4 = "infrared.wi_fi_universal_remote_ir_emitter"


# ---------------------------------------------------------------------------
# Hand-built frames
# ---------------------------------------------------------------------------


def _nec(address: int, command: int) -> list[int]:
    """One full NEC frame: 9 ms leader, 32 bits LSB first, stop mark."""
    timings = [9000, -4500]
    for byte in (address, address ^ 0xFF, command, command ^ 0xFF):
        for i in range(8):
            timings += [560, -1690 if (byte >> i) & 1 else -560]
    timings.append(560)
    return timings


NEC_POWER = _nec(0x04, 0x08)
NEC_POWER_FP = "NEC:0xfb04:0x08"
NEC_OTHER = _nec(0x10, 0x20)  # the Device's command in the pinned case
UNDECODED = [3000, -3000, 1200, -400, 400, -1200, 1200, -400, 400, -1200,
             800, -800, 800]


def _rc5(toggle: int) -> list[int]:
    return list(RC5Command(address=5, command=0x10, toggle=toggle)
                .get_raw_timings())


def _rc6(toggle: int) -> list[int]:
    return list(RC6Command(address=4, command=0x0C, toggle=toggle)
                .get_raw_timings())


JVC_FULL = list(JVCCommand(address=0x03, command=0x17).get_raw_timings())
JVC_HEADERLESS = list(jvc_mod._bit_frame(0x03, 0x17))


def _norm(timings: list[int]):
    return sm.normalize(sm.EventParser.parse({"raw": list(timings)}))


class _Clock:
    """One clock for every module that reads time on the capture path."""

    def __init__(self, start: float = 5000.0) -> None:
        self.t = start

    def monotonic(self) -> float:
        return self.t

    def time(self) -> float:
        return 1_790_000_000.0 + self.t

    def advance(self, dt: float) -> None:
        self.t += dt


# ---------------------------------------------------------------------------
# The rules, on the tracker alone
# ---------------------------------------------------------------------------


@pytest.fixture
def tclock():
    return _Clock()


@pytest.fixture
def tracker(tclock):
    return PressCueTracker(clock=tclock.monotonic)


def _observe_at(tracker, clock, gaps, protocol, fp, toggles=None, rx=RX_A):
    """Observe one frame per gap; return the rule letter or None for each."""
    seen = []
    for i, gap in enumerate(gaps):
        clock.advance(gap)
        extras = None if toggles is None else {"toggle": toggles[i]}
        cue = tracker.observe(rx, protocol, fp, extras)
        seen.append(None if cue is None else cue.rule)
    return seen


class TestWhichProtocolsHaveARule:
    def test_the_three_families(self):
        for proto in ("NEC", "APPLE", "NEC42", "NEC42EXT"):
            assert cue_rule(proto) == RULE_DITTO
        for proto in ("RC5", "MARANTZ", "RC6", "NOKIA32"):
            assert cue_rule(proto) == RULE_TOGGLE
        assert cue_rule("JVC") == RULE_LEADER

    @pytest.mark.parametrize(
        "proto",
        # Kaseikyo is left out on purpose: most Panasonic remotes repeat
        # the whole frame, so it has no ditto to lean on.
        ["SONY", "SAMSUNG32", "KASEIKYO", "SHARP", "RCA", "PIONEER", None],
    )
    def test_everything_else_gets_no_cue_and_no_memory(
        self, tracker, tclock, proto
    ):
        assert _observe_at(
            tracker, tclock, (0.0, 0.200, 0.200), proto, "X:0x1:0x2"
        ) == [None, None, None]
        assert len(tracker) == 0

    def test_a_capture_with_no_identity_gets_no_cue(self, tracker, tclock):
        assert _observe_at(tracker, tclock, (0.0, 0.2), "NEC", None) == [
            None, None,
        ]
        assert len(tracker) == 0

    def test_every_period_has_a_rule_and_every_rule_a_period(self):
        ruled = {p for p in PRESS_CUE_REPEAT_PERIOD_S if cue_rule(p)}
        assert ruled == set(PRESS_CUE_REPEAT_PERIOD_S)

    def test_the_soonest_cue_is_the_factor_times_the_period(self):
        assert pytest.approx(1.2) == PRESS_CUE_REPEAT_FACTOR
        assert min_gap_s("NEC") == pytest.approx(0.1296)
        assert min_gap_s("JVC") == pytest.approx(0.0696)


class TestRuleN:
    """NEC family: a second full frame is a second press."""

    @pytest.mark.parametrize(
        "gap,rule", [(0.108, None), (0.200, RULE_DITTO)],
        ids=["repeat_at_108ms", "new_press_at_200ms"],
    )
    def test_the_second_frame_at_one_period_and_at_200ms(
        self, tracker, tclock, gap, rule
    ):
        """Section 8's case: one period after the first frame is a
        repeat, 200 ms after it is a new press."""
        assert _observe_at(
            tracker, tclock, (0.0, gap), "NEC", NEC_POWER_FP
        ) == [None, rule]

    def test_a_quick_double_press_is_new_on_the_second_frame(
        self, tracker, tclock
    ):
        assert _observe_at(
            tracker, tclock, (0.0, 0.200), "NEC", NEC_POWER_FP
        ) == [None, RULE_DITTO]

    def test_the_cue_carries_the_gap(self, tracker, tclock):
        tracker.observe(RX_A, "NEC", NEC_POWER_FP)
        tclock.advance(0.180)
        cue = tracker.observe(RX_A, "NEC", NEC_POWER_FP)
        assert cue == PressCue(RULE_DITTO, pytest.approx(0.180))

    def test_the_boundary_from_both_sides(self, tracker, tclock):
        """A millisecond out each way from 1.2 periods (129.6 ms)."""
        soonest = min_gap_s("NEC")
        assert _observe_at(
            tracker, tclock, (0.0, soonest + 0.001), "NEC", NEC_POWER_FP
        ) == [None, RULE_DITTO]
        other = PressCueTracker(clock=tclock.monotonic)
        assert _observe_at(
            other, tclock, (1.0, soonest - 0.001), "NEC", NEC_POWER_FP
        ) == [None, None]

    def test_a_hold_is_one_full_frame_and_no_cue(self, tracker, tclock):
        """A held NEC button: one frame, then dittos that never get here.

        So the hold observes once, and the next press after release is
        the second full frame.
        """
        assert _observe_at(
            tracker, tclock, (0.0,), "NEC", NEC_POWER_FP
        ) == [None]
        tclock.advance(2.0)  # the hold, all dittos
        assert tracker.observe(RX_A, "NEC", NEC_POWER_FP) is not None

    def test_a_full_frame_repeater_learns_on_its_first_quick_repeat(
        self, tracker, tclock
    ):
        """The Pioneer shape: whole frames every 108 ms while held.

        The first repeat is inside one period, so the button is learned
        as a full-frame repeater and never gives a cue again: not for the
        rest of the hold, not for a quick double press afterwards.
        """
        hold = (0.0,) + (0.108,) * 9
        assert _observe_at(
            tracker, tclock, hold, "NEC", NEC_POWER_FP
        ) == [None] * 10
        # Release, then a quick double press, then more of the same.
        presses = (0.600, 0.200, 0.250, 0.180, 1.5, 0.220)
        assert _observe_at(
            tracker, tclock, presses, "NEC", NEC_POWER_FP
        ) == [None] * 6

    def test_a_full_frame_repeater_is_learned_per_button(
        self, tracker, tclock
    ):
        """Learning one button says nothing about another."""
        _observe_at(tracker, tclock, (0.0, 0.108), "NEC", NEC_POWER_FP)
        assert _observe_at(
            tracker, tclock, (0.5, 0.200), "NEC", "NEC:0xfb04:0x09"
        ) == [None, RULE_DITTO]

    def test_every_member_of_the_family(self, tracker, tclock):
        for i, proto in enumerate(("APPLE", "NEC42", "NEC42EXT")):
            fp = f"{proto}:0x{i}:0x1"
            assert _observe_at(
                tracker, tclock, (1.0, 0.200), proto, fp
            ) == [None, RULE_DITTO]


class TestRuleT:
    """RC5 family: the toggle flips on every press."""

    @pytest.mark.parametrize("proto", ["RC5", "MARANTZ", "RC6", "NOKIA32"])
    def test_a_quick_double_press_is_new_when_the_toggle_flips(
        self, tracker, tclock, proto
    ):
        assert _observe_at(
            tracker, tclock, (0.0, 0.200), proto, f"{proto}:0x5:0x10",
            toggles=(0, 1),
        ) == [None, RULE_TOGGLE]

    @pytest.mark.parametrize(
        "proto,period",
        [("RC5", 0.114), ("MARANTZ", 0.114), ("RC6", 0.107),
         ("NOKIA32", 0.100)],
    )
    def test_a_hold_keeps_its_toggle_and_gives_no_cue(
        self, tracker, tclock, proto, period
    ):
        hold = (0.0,) + (period,) * 9
        assert _observe_at(
            tracker, tclock, hold, proto, f"{proto}:0x5:0x10",
            toggles=(1,) * 10,
        ) == [None] * 10

    def test_held_then_pressed_again(self, tracker, tclock):
        """A hold, a release, a new press: the new press is the cue."""
        seen = _observe_at(
            tracker, tclock, (0.0, 0.114, 0.114, 0.114, 0.200),
            "RC5", "RC5:0x0005:0x10", toggles=(0, 0, 0, 0, 1),
        )
        assert seen == [None, None, None, None, RULE_TOGGLE]

    def test_a_flip_too_soon_for_a_hand_is_no_cue(self, tracker, tclock):
        """A flip inside 1.2 periods is noise, not a finger."""
        assert _observe_at(
            tracker, tclock, (0.0, min_gap_s("RC5") - 0.001),
            "RC5", "RC5:0x0005:0x10", toggles=(0, 1),
        ) == [None, None]

    def test_no_toggle_no_cue(self, tracker, tclock):
        assert _observe_at(
            tracker, tclock, (0.0, 0.200), "RC5", "RC5:0x0005:0x10"
        ) == [None, None]

    def test_the_toggle_compares_with_the_last_frame_not_the_first(
        self, tracker, tclock
    ):
        """Three quick presses flip 0, 1, 0: two cues."""
        assert _observe_at(
            tracker, tclock, (0.0, 0.200, 0.200),
            "RC5", "RC5:0x0005:0x10", toggles=(0, 1, 0),
        ) == [None, RULE_TOGGLE, RULE_TOGGLE]


class TestRuleJ:
    """JVC: only a press's first frame carries the leader."""

    def test_a_second_decoded_capture_is_new(self, tracker, tclock):
        assert _observe_at(
            tracker, tclock, (0.0, 0.200), "JVC", "JVC:0x0003:0x17"
        ) == [None, RULE_LEADER]

    def test_inside_one_period_is_no_cue(self, tracker, tclock):
        assert _observe_at(
            tracker, tclock, (0.0, min_gap_s("JVC") - 0.001),
            "JVC", "JVC:0x0003:0x17",
        ) == [None, None]


class TestMemory:
    def test_per_receiver_the_first_frame_never_gives_a_cue(
        self, tracker, tclock
    ):
        """The same press reaching a second receiver is that receiver's
        first frame of the button, so the windows fold it as before."""
        assert _observe_at(
            tracker, tclock, (0.0,), "NEC", NEC_POWER_FP, rx=RX_A
        ) == [None]
        assert _observe_at(
            tracker, tclock, (0.020,), "NEC", NEC_POWER_FP, rx=RX_B
        ) == [None]

    def test_past_the_ttl_the_button_starts_over(self, tracker, tclock):
        _observe_at(tracker, tclock, (0.0, 0.108), "NEC", NEC_POWER_FP)
        tclock.advance(PRESS_CUE_TTL_S + 1)
        # Fresh: first frame no cue, then the learner starts again.
        assert _observe_at(
            tracker, tclock, (0.0, 0.200), "NEC", NEC_POWER_FP
        ) == [None, RULE_DITTO]

    def test_forget_receiver(self, tracker, tclock):
        _observe_at(tracker, tclock, (0.0,), "NEC", NEC_POWER_FP, rx=RX_A)
        _observe_at(tracker, tclock, (0.0,), "NEC", NEC_POWER_FP, rx=RX_B)
        tracker.forget_receiver(RX_A)
        assert len(tracker) == 1
        assert _observe_at(
            tracker, tclock, (0.200,), "NEC", NEC_POWER_FP, rx=RX_A
        ) == [None]

    def test_stale_entries_are_swept(self, tracker, tclock):
        for i in range(50):
            tracker.observe(RX_A, "NEC", f"NEC:0x1:0x{i:02x}")
        tclock.advance(PRESS_CUE_TTL_S + 1)
        for _ in range(200):
            tracker.observe(RX_B, "NEC", NEC_POWER_FP)
        assert len(tracker) == 1


# ---------------------------------------------------------------------------
# The decoders give the rules what they read
# ---------------------------------------------------------------------------


class TestDecodedShapes:
    def test_nec_frame(self):
        n = _norm(NEC_POWER)
        assert n.decoded_protocol == "NEC"
        assert n.decoded_fingerprint == NEC_POWER_FP

    @pytest.mark.parametrize("build,proto", [(_rc5, "RC5"), (_rc6, "RC6")])
    def test_the_toggle_is_outside_the_identity(self, build, proto):
        """Both toggle states are one button, told apart by extras."""
        n0, n1 = _norm(build(0)), _norm(build(1))
        assert n0.decoded_protocol == n1.decoded_protocol == proto
        assert n0.decoded_fingerprint == n1.decoded_fingerprint
        assert n0.decoded_extras["toggle"] == 0
        assert n1.decoded_extras["toggle"] == 1

    def test_jvc_decodes_only_with_its_leader(self):
        assert _norm(JVC_FULL).decoded_protocol == "JVC"
        assert _norm(JVC_HEADERLESS).decoded_fingerprint is None

    def test_a_merged_jvc_hold_is_one_capture(self):
        held = JVCCommand(address=0x03, command=0x17, repeat_count=3)
        assert _norm(list(held.get_raw_timings())).decoded_protocol == "JVC"


# ---------------------------------------------------------------------------
# The trigger fold
# ---------------------------------------------------------------------------


@pytest.fixture
def tm_hass():
    hass = MagicMock()
    hass.bus = MagicMock()
    hass.async_create_task = lambda coro, *a, **kw: coro.close()
    return hass


@pytest.fixture
def tm_store(tm_hass):
    store = HAIRStore(tm_hass)
    store._loaded = True
    return store


@pytest.fixture
def clock(monkeypatch):
    fake = _Clock()
    monkeypatch.setattr(sm, "monotonic", fake.monotonic)
    monkeypatch.setattr(sm, "time", fake)
    monkeypatch.setattr(
        "custom_components.hair.trigger_manager.time", fake
    )
    return fake


_CUE = PressCue(RULE_DITTO, 0.2)


class TestTriggerFold:
    @staticmethod
    def _feed(manager, clock, steps):
        """steps: (gap, cue, receiver). Returns fired yes/no per step."""
        seen = []
        for gap, cue, rx in steps:
            clock.advance(gap)
            seen.append(bool(manager.on_signal_captured(
                "fp1", "pronto", "0000 0001", None, rx, press_cue=cue,
            )))
        return seen

    @pytest.fixture
    def manager(self, tm_hass, tm_store):
        tm_store.add_trigger(IRTrigger(
            name="T", signal_fingerprint="fp1", protocol="pronto",
            code="0000 0001",
        ))
        return TriggerManager(tm_hass, tm_store)

    def test_a_cue_inside_the_window_fires(self, manager, clock):
        assert self._feed(manager, clock, [
            (0.0, None, RX_A), (0.200, _CUE, RX_A),
        ]) == [True, True]

    def test_without_a_cue_the_window_is_as_it_was(self, manager, clock):
        assert self._feed(manager, clock, [
            (0.0, None, RX_A), (0.200, None, RX_A),
        ]) == [True, False]

    def test_a_cue_within_the_multi_receiver_window_is_folded(
        self, manager, clock
    ):
        assert self._feed(manager, clock, [
            (0.0, None, RX_A),
            (MULTI_RECEIVER_DEDUP_WINDOW_S - 0.001, _CUE, RX_B),
        ]) == [True, False]

    def test_a_cue_anchors_the_window_like_any_fire(self, manager, clock):
        """After a cue fires, its own repeat frames fold behind it."""
        assert self._feed(manager, clock, [
            (0.0, None, RX_A), (0.200, _CUE, RX_A), (0.108, None, RX_A),
        ]) == [True, True, False]

    def test_two_receivers_hear_a_double_press_as_two_fires(
        self, manager, clock
    ):
        """Each receiver's second frame carries a cue, the second one
        15 ms after the first was let through: two fires, not four."""
        assert self._feed(manager, clock, [
            (0.0, None, RX_A), (0.015, None, RX_B),
            (0.185, _CUE, RX_A), (0.015, _CUE, RX_B),
        ]) == [True, False, True, False]

    def test_a_multi_frame_file_row_keeps_its_window(
        self, manager, clock, monkeypatch
    ):
        monkeypatch.setattr(
            manager, "_is_multi_frame_file_row", lambda trigger: True
        )
        assert self._feed(manager, clock, [
            (0.0, None, RX_A), (0.200, _CUE, RX_A),
        ]) == [True, False]

    def test_min_hits_counts_a_quick_double_press_as_two(
        self, tm_hass, tm_store, clock
    ):
        tm_store.add_trigger(IRTrigger(
            name="Two", signal_fingerprint="fp1", protocol="pronto",
            code="0000 0001", min_hits=2,
        ))
        manager = TriggerManager(tm_hass, tm_store)
        assert self._feed(manager, clock, [
            (0.0, None, RX_A), (0.200, _CUE, RX_A),
        ]) == [False, True]

    def test_the_cue_line_is_logged(self, manager, clock, caplog):
        caplog.set_level("DEBUG", logger="custom_components.hair")
        self._feed(manager, clock, [(0.0, None, RX_A), (0.2, _CUE, RX_A)])
        assert "a new press by rule N" in caplog.text


# ---------------------------------------------------------------------------
# End to end: SignalMonitor, a real TriggerManager, one clock
# ---------------------------------------------------------------------------


class _Rig:
    """A monitor and a real trigger manager sharing one fake clock."""

    def __init__(self, clock, tm_hass, tm_store, trigger_frames):
        self.clock = clock
        hass = _make_hass()
        hass.async_create_task = MagicMock(
            side_effect=lambda coro, *a, **kw: coro.close()
        )
        self.manager = TriggerManager(tm_hass, tm_store)
        self.fires: list[str] = []
        real = self.manager.on_signal_captured

        def spy(*args, **kwargs):
            fired = real(*args, **kwargs)
            self.fires.extend(fired)
            return fired

        self.manager.on_signal_captured = spy
        self.monitor = SignalMonitor(
            hass, _make_signal_store(hass), _make_hair_store(), self.manager
        )
        self.monitor._press_cues = PressCueTracker(clock=clock.monotonic)
        n = _norm(trigger_frames)
        tm_store.add_trigger(IRTrigger(
            name="Button", signal_fingerprint=n.sig_fp,
            decoded_fingerprint=n.decoded_fingerprint,
        ))

    async def feed(self, steps):
        """steps: (gap_s, timings, receiver). Returns the fire count."""
        before = len(self.fires)
        for gap, timings, rx in steps:
            self.clock.advance(gap)
            parsed = sm.EventParser.parse({"raw": list(timings)})
            await self.monitor._process_parsed_signal(
                parsed, receiver_entity_id=rx
            )
        return len(self.fires) - before

    def hits(self, timings=None) -> int:
        """Sniffer hit count, over all rows or one button's rows."""
        fp = None if timings is None else _norm(timings).decoded_fingerprint
        total = 0
        for device in self.monitor._signal_store.get_all_devices():
            for sig in device.signals:
                if fp is None or sig.decoded_fingerprint == fp:
                    total += sig.hit_count
        return total


@pytest.fixture
def rig(clock, tm_hass, tm_store):
    def make(frames=NEC_POWER):
        return _Rig(clock, tm_hass, tm_store, frames)
    return make


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_an_nec_quick_double_press_fires_twice_and_counts_twice(
        self, rig
    ):
        r = rig()
        assert await r.feed([(0.0, NEC_POWER, RX_A),
                             (0.200, NEC_POWER, RX_A)]) == 2
        assert r.hits() == 2

    @pytest.mark.asyncio
    async def test_an_undecoded_double_press_is_as_it_was(self, rig):
        """No decode, no cue: one fire, one Sniffer hit, as before."""
        r = rig(UNDECODED)
        assert await r.feed([(0.0, UNDECODED, RX_A),
                             (0.200, UNDECODED, RX_A)]) == 1
        assert r.hits() == 1

    @pytest.mark.asyncio
    async def test_rc5_double_press_and_hold(self, rig):
        r = rig(_rc5(0))
        # A double press: toggle flips.
        assert await r.feed([(0.0, _rc5(0), RX_A),
                             (0.200, _rc5(1), RX_A)]) == 2
        # A hold: one toggle, frames every 114 ms for 6 frames. The
        # anchored window fires on frames 1 and 4, exactly as today.
        hold = [(1.0, _rc5(0), RX_A)] + [(0.114, _rc5(0), RX_A)] * 5
        assert await r.feed(hold) == 2

    @pytest.mark.asyncio
    async def test_rc6_double_press(self, rig):
        r = rig(_rc6(0))
        assert await r.feed([(0.0, _rc6(0), RX_A),
                             (0.200, _rc6(1), RX_A)]) == 2

    @pytest.mark.asyncio
    async def test_jvc_double_press_and_hold(self, rig):
        r = rig(JVC_FULL)
        assert await r.feed([(0.0, JVC_FULL, RX_A),
                             (0.200, JVC_FULL, RX_A)]) == 2
        # A hold heard frame by frame: the leader frame, then headerless
        # repeats that decode as nothing and so give no cue.
        hold = [(1.0, JVC_FULL, RX_A)] + [(0.058, JVC_HEADERLESS, RX_A)] * 8
        assert await r.feed(hold) == 1

    @pytest.mark.asyncio
    async def test_a_pioneer_shape_hold_fires_as_today_and_is_never_doubled(
        self, rig
    ):
        """Full NEC frames every 108 ms: the same fires as an uncued
        protocol, then a quick double press afterwards still fires once."""
        r = rig()
        hold = [(0.0, NEC_POWER, RX_A)] + [(0.108, NEC_POWER, RX_A)] * 5
        assert await r.feed(hold) == 2  # frames 1 and 4, the anchored ramp
        assert await r.feed([(0.800, NEC_POWER, RX_A),
                             (0.200, NEC_POWER, RX_A)]) == 1

    @pytest.mark.asyncio
    async def test_two_receivers_two_fires_not_four(self, rig):
        r = rig()
        single = await r.feed([(0.0, NEC_POWER, RX_A),
                               (0.015, NEC_POWER, RX_B)])
        assert single == 1
        assert r.hits() == 2  # each receiver counts its own, as before
        assert await r.feed([(1.0, NEC_POWER, RX_A),
                             (0.015, NEC_POWER, RX_B),
                             (0.185, NEC_POWER, RX_A),
                             (0.015, NEC_POWER, RX_B)]) == 2

    @pytest.mark.asyncio
    async def test_the_sniffer_window_still_folds_without_a_cue(self, rig):
        """Inside SIGNAL_REPEAT_SUPPRESS_MS with no cue: still one hit."""
        r = rig()
        gap = SIGNAL_REPEAT_SUPPRESS_MS / 1000.0 - 0.050
        assert gap < TRIGGER_FIRE_DEDUP_WINDOW_S
        await r.feed([(0.0, NEC_POWER, RX_A), (0.108, NEC_POWER, RX_A),
                      (gap - 0.108, NEC_POWER, RX_A)])
        # Frame 2 is inside a period: learned, no cue; frame 3 then has
        # no cue either, so both fold.
        assert r.hits() == 1

    @pytest.mark.asyncio
    async def test_a_decode_covering_part_of_the_capture_gives_no_cue(
        self, rig
    ):
        """An RC5 frame beside a state blob: the decode is not the
        capture's identity, so the toggle is not asked."""
        r = rig()
        blobs = [[*_rc5(t), -35000, *junk_state_frame()] for t in (0, 1)]
        assert _norm(blobs[0]).decode_covers is False
        await r.feed([(0.0, blobs[0], RX_A), (0.200, blobs[1], RX_A)])
        assert len(r.monitor._press_cues) == 0

    @pytest.mark.asyncio
    async def test_a_released_receiver_is_forgotten(self, rig):
        r = rig()
        await r.feed([(0.0, NEC_POWER, RX_A), (0.0, NEC_POWER, RX_B)])
        assert len(r.monitor._press_cues) == 2
        r.monitor._release_receiver(RX_A)
        assert len(r.monitor._press_cues) == 1

    @pytest.mark.asyncio
    async def test_the_debug_line(self, rig, caplog):
        caplog.set_level("DEBUG", logger="custom_components.hair")
        r = rig()
        await r.feed([(0.0, NEC_POWER, RX_A), (0.2, NEC_POWER, RX_A)])
        lines = [rec for rec in caplog.records
                 if rec.getMessage().startswith("Press cue:")]
        assert len(lines) == 1
        assert "rule N, 200 ms" in lines[0].getMessage()


# ---------------------------------------------------------------------------
# Echoes
# ---------------------------------------------------------------------------


LAST_SEND = "2026-11-06T18:30:29.751+00:00"
THIS_SEND = "2026-11-07T03:34:27.690+00:00"


def _beacon():
    attrs = {"device_class": "emitter", "friendly_name": "RM4 Pro"}
    return SimpleNamespace(
        data={
            "entity_id": RM4,
            "new_state": SimpleNamespace(state=THIS_SEND, attributes=attrs),
            "old_state": SimpleNamespace(state=LAST_SEND, attributes=attrs),
        },
        context=SimpleNamespace(parent_id=None),
    )


def _send(monitor, timings, label):
    """HAIR sends through the RM4, and core writes its state."""
    n = _norm(timings)
    with patch.object(sm, "normalize_command", lambda _c: n):
        monitor.record_send(
            object(), label, [RM4],
            decoded_fingerprint=n.decoded_fingerprint, send_count=1,
        )
    monitor._on_emitter_beacon(_beacon())
    return monitor._echo_expectations[-1]


class TestEchoes:
    @pytest.mark.asyncio
    async def test_an_echo_never_gives_a_cue_or_moves_the_tracker(self, rig):
        r = rig()
        _send(r.monitor, NEC_POWER, "TV / Power")
        assert await r.feed([(0.180, NEC_POWER, RX_A)]) == 0
        _send(r.monitor, NEC_POWER, "TV / Power")
        assert await r.feed([(0.200, NEC_POWER, RX_A)]) == 0
        assert len(r.monitor._press_cues) == 0
        assert r.hits() == 0

    @pytest.mark.asyncio
    async def test_an_echo_between_two_presses_is_not_one_of_them(
        self, rig
    ):
        """A press, HAIR's own send of the same code, then the echo: the
        echo neither fires nor stands in for a press frame."""
        r = rig()
        assert await r.feed([(0.0, NEC_POWER, RX_A)]) == 1
        seen = r.monitor._press_cues._seen[(RX_A, NEC_POWER_FP)].at
        _send(r.monitor, NEC_POWER, "TV / Power")
        assert await r.feed([(0.180, NEC_POWER, RX_A)]) == 0
        assert r.monitor._press_cues._seen[(RX_A, NEC_POWER_FP)].at == seen

    @pytest.mark.asyncio
    async def test_a_pinned_device_sends_twice_and_both_echoes_are_claimed(
        self, rig
    ):
        """A quick double press of a handset button pinned to a Device.

        Each fire sends the Device's own command (a different code) and
        each send's echo is claimed: two fires, two sends, two claims,
        and the Device's code never reaches the trigger or the tracker.
        """
        r = rig()
        tickets = []
        assert await r.feed([(0.0, NEC_POWER, RX_A)]) == 1
        tickets.append(_send(r.monitor, NEC_OTHER, "Amp / Power"))
        assert await r.feed([(0.090, NEC_OTHER, RX_A)]) == 0
        assert await r.feed([(0.110, NEC_POWER, RX_A)]) == 1
        tickets.append(_send(r.monitor, NEC_OTHER, "Amp / Power"))
        assert await r.feed([(0.090, NEC_OTHER, RX_A)]) == 0

        assert len(r.fires) == 2
        assert [t["claims_left"] for t in tickets] == [{RX_A: 0}, {RX_A: 0}]
        other_fp = _norm(NEC_OTHER).decoded_fingerprint
        assert (RX_A, other_fp) not in r.monitor._press_cues._seen
        assert r.hits(NEC_OTHER) == 0
