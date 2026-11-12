"""Always-on radio receivers: the burst gate, the software window, the opt-in.

A radio receiver with no ``capturing`` listens all the time. The fixtures
are a fixed 433.92 MHz receiver (``fixtures/rf/athom/``): an hour of its
noise with nobody pressing, and keyfob presses arriving one frame per
capture with that noise between them, plus the same presses heard whole
by an RM4 pro. Their timestamps have 1-second resolution, so the replay
below keeps each second's captures in that second and in order, spaces
noise evenly across it, and spaces frames at the keyfob's measured frame
period. That reproduces the rates and the burst structure; it does not
reproduce sub-second jitter.
"""
from __future__ import annotations

import gzip
import heapq
import itertools
import json
import os
import types
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import rf_frames
from custom_components.hair.const import (
    MEDIUM_RF,
    RF_BURST_HOLD_S,
    RF_BURST_SILENCE_S,
    RF_FREQUENCY_SOURCE_RECEIVER,
    RF_FREQUENCY_SOURCE_SIGNAL,
    RF_GAP_ASSUMED,
    RF_GAP_MEASURED,
    RF_PENDING_MAX,
    RF_WINDOW_MAX_S,
)
from custom_components.hair.models import upgrade_rf_fields
from custom_components.hair.rf_burst import BurstAssembler
from custom_components.hair.rf_window import SoftwareWindow, SoftwareWindowArm
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore

ATHOM = Path(__file__).parent / "fixtures" / "rf" / "athom"
RID = "radio_frequency.office_433mhz_rf_receiver"
RM4 = "radio_frequency.office_rm4_pro_rf_receiver"
# The fixtures' keyfob frame period: a 49-edge frame of about 40 ms and
# its 12.9 ms gap.
FRAME_PERIOD_S = 0.053

CODES = {
    0x49: "1 ON", 0x41: "1 OFF", 0x4B: "2 ON", 0x43: "2 OFF",
    0x4D: "3 ON", 0x45: "3 OFF", 0x4F: "ALL ON", 0x47: "ALL OFF",
}


# ---------------------------------------------------------------------------
# Harness: a loop with a clock the test moves
# ---------------------------------------------------------------------------


class _Handle:
    def __init__(self, loop, when, fn, seq):
        self.loop, self.when, self.fn, self.seq = loop, when, fn, seq
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def __lt__(self, other):
        return (self.when, self.seq) < (other.when, other.seq)


class FakeLoop:
    """``time``, ``call_at`` and ``call_later``, run by ``advance_to``."""

    def __init__(self):
        self.now = 1_000.0
        self._heap: list[_Handle] = []
        self._seq = itertools.count()

    def time(self):
        return self.now

    def call_at(self, when, fn, *args):
        handle = _Handle(self, when, (lambda: fn(*args)), next(self._seq))
        heapq.heappush(self._heap, handle)
        return handle

    def call_later(self, delay, fn, *args):
        return self.call_at(self.now + delay, fn, *args)

    def advance_to(self, when):
        while self._heap and self._heap[0].when <= when:
            handle = heapq.heappop(self._heap)
            if handle.cancelled:
                continue
            self.now = max(self.now, handle.when)
            handle.fn()
        self.now = max(self.now, when)

    def wall(self):
        return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=self.now)


def _load(name):
    path = ATHOM / name
    if not path.exists():
        folder = os.environ.get("HAIR_RF_FIXTURES")
        path = Path(folder) / name if folder else path
    if not path.exists():
        pytest.skip(f"{name} is kept outside the repository")
    with gzip.open(path, "rb") as handle:
        return json.loads(handle.read())


FRAME_BODY_MIN = 40  # the fixtures' keyfob bodies: 49 edges (47 when clipped)


def _is_frame(timings):
    pieces = rf_frames.bodied_pieces(rf_frames.split_frames(timings))
    return any(len(parts.body) >= FRAME_BODY_MIN for _, parts in pieces)


def _schedule(captures, start):
    """(time, timings) for every capture, paced as the module docstring says."""
    by_second: dict[int, list] = {}
    for second, timings in captures:
        by_second.setdefault(second, []).append(timings)
    out = []
    last_frame = -1.0
    for second in sorted(by_second):
        items = by_second[second]
        base = start + second
        noise_step = 1.0 / (len(items) + 1)
        for index, timings in enumerate(items):
            if _is_frame(timings):
                at = max(base, last_frame + FRAME_PERIOD_S)
                last_frame = at
            else:
                at = base + noise_step * (index + 1)
            out.append((at, timings))
    out.sort(key=lambda item: item[0])
    return out


def _signal(timings, frequency=None):
    return types.SimpleNamespace(timings=timings, frequency=frequency, modulation="ook")


def _monitor(fake_hass, loop):
    fake_hass.loop = loop
    store = SignalStore(fake_hass)
    store._loaded = True
    store.schedule_save = MagicMock()
    store.async_save = AsyncMock()
    hair = MagicMock()
    hair.get_all_devices = MagicMock(return_value=[])
    hair.get_device = MagicMock(return_value=None)
    hair.async_save = AsyncMock()
    hair.match_command = MagicMock(return_value=None)
    monitor = SignalMonitor(fake_hass, store, hair)
    from custom_components.hair.rf_window import RfAlwaysOn

    monitor.rf_always_on = RfAlwaysOn(fake_hass, wall_now=loop.wall)
    return monitor, store


class _Run:
    """Feeds captures to a monitor on the fake loop and drains its tasks."""

    def __init__(self, fake_hass, loop, monitor):
        self.loop = loop
        self.monitor = monitor
        self.tasks: list = []
        fake_hass.async_create_task = MagicMock(side_effect=self.tasks.append)
        fake_hass.states.get = MagicMock(return_value=types.SimpleNamespace(
            entity_id=RID, state="2026-01-01T00:00:00+00:00",
            attributes={"device_class": "receiver"},
        ))

    async def drain(self):
        while self.tasks:
            await self.tasks.pop(0)

    async def feed(self, schedule, receiver=RID, frequency=None, before=None):
        with patch(
            "custom_components.hair.signal_monitor.time.monotonic",
            side_effect=lambda: self.loop.now,
        ), patch(
            "custom_components.hair.signal_monitor.time.time",
            side_effect=lambda: self.loop.now,
        ):
            for at, timings in schedule:
                self.loop.advance_to(at)
                await self.drain()
                if before is not None:
                    before()
                self.monitor._on_rf_signal(_signal(timings, frequency), receiver)
                await self.drain()
            self.loop.advance_to(self.loop.now + 2.0)
            await self.drain()


def _code_of(signal):
    """The keyfob button a stored row is, read from its canonical frame."""
    edges = [abs(v) for v in signal.raw_timings]
    bits = "".join("1" if edges[2 * k] > edges[2 * k + 1] else "0" for k in range(24))
    value = int(bits, 2)
    return CODES.get(value & 0xFF) if value >> 8 == 0x950E else None


def _rows(store):
    out = Counter()
    for device in store.get_all_devices():
        for signal in device.signals:
            out[_code_of(signal) or "?"] += 1
    return out


# ---------------------------------------------------------------------------
# The burst assembler on its own
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def frame_parts():
    """One real whole frame (49-edge body) from the 150us/6ms file, split."""
    data = _load("athom-433-it104-150us-6ms-presses.json.gz")
    for _second, timings in data["captures"]:
        whole = [
            p for p in rf_frames.bodied_pieces(rf_frames.split_frames(timings))
            if len(p[1].body) == 49
        ]
        if len(whole) == 1:
            return whole[0]
    raise AssertionError("no frame in the fixture")


class TestBurstAssembler:
    def _assembler(self, loop):
        bursts, failed = [], []
        assembler = BurstAssembler(
            on_burst=lambda analysis, signal, _frames: bursts.append(
                (analysis, signal)
            ),
            on_lone=lambda: failed.append(loop.now),
            call_at=loop.call_at,
            now=loop.time,
        )
        return assembler, bursts, failed

    def test_frames_of_one_press_vote_once_the_press_is_over(self, frame_parts):
        loop = FakeLoop()
        assembler, bursts, failed = self._assembler(loop)
        fp = rf_frames.frame_fingerprint(frame_parts[1])
        for index in range(6):
            loop.advance_to(1_000.0 + index * FRAME_PERIOD_S)
            assembler.add(fp, frame_parts, "sig")
        assert bursts == []  # still open
        loop.advance_to(loop.now + RF_BURST_SILENCE_S + 0.001)
        assert len(bursts) == 1 and failed == []
        analysis, signal = bursts[0]
        assert analysis.votes == 6 and signal == "sig"
        assert analysis.gap_source == RF_GAP_ASSUMED  # never read from a join

    def test_a_lone_frame_is_counted_as_one(self, frame_parts):
        loop = FakeLoop()
        assembler, bursts, failed = self._assembler(loop)
        assembler.add("fp", frame_parts)
        loop.advance_to(loop.now + 1.0)
        assert bursts == [] and len(failed) == 1

    def test_noise_between_frames_neither_joins_nor_extends(self, frame_parts):
        loop = FakeLoop()
        assembler, bursts, failed = self._assembler(loop)
        fp = rf_frames.frame_fingerprint(frame_parts[1])
        noise = (frame_parts[0], frame_parts[1])
        for index in range(4):
            loop.advance_to(1_000.0 + index * 0.1)
            assembler.add(fp, frame_parts)
            assembler.add(f"noise-{index}", noise)
        loop.advance_to(1_000.3 + RF_BURST_SILENCE_S + 0.001)
        assert [a.votes for a, _ in bursts] == [4]
        assert len(failed) == 4

    def test_a_held_key_becomes_a_burst_every_hold(self, frame_parts):
        loop = FakeLoop()
        assembler, bursts, _failed = self._assembler(loop)
        fp = rf_frames.frame_fingerprint(frame_parts[1])
        steps = int(3.0 / FRAME_PERIOD_S)
        for index in range(steps):
            loop.advance_to(1_000.0 + index * FRAME_PERIOD_S)
            assembler.add(fp, frame_parts)
        loop.advance_to(loop.now + 1.0)
        assert len(bursts) == round(3.0 / RF_BURST_HOLD_S)

    def test_the_pending_map_is_bounded(self, frame_parts):
        loop = FakeLoop()
        assembler, _bursts, failed = self._assembler(loop)
        for index in range(RF_PENDING_MAX + 5):
            assembler.add(f"fp-{index}", frame_parts)
        assert assembler.open_count == RF_PENDING_MAX
        assert len(failed) == 5

    def test_one_timer_however_many_captures(self, frame_parts):
        loop = FakeLoop()
        assembler, _bursts, _failed = self._assembler(loop)
        fp = rf_frames.frame_fingerprint(frame_parts[1])
        for index in range(50):
            loop.advance_to(1_000.0 + index * 0.01)
            assembler.add(fp, frame_parts)
        live = [h for h in loop._heap if not h.cancelled]
        assert len(live) == 1

    def test_discard_drops_unvoted(self, frame_parts):
        loop = FakeLoop()
        assembler, bursts, failed = self._assembler(loop)
        assembler.add("fp", frame_parts)
        assembler.add("fp", frame_parts)
        assembler.discard()
        loop.advance_to(loop.now + 5.0)
        assert bursts == [] and failed == [] and assembler.open_count == 0


# ---------------------------------------------------------------------------
# The software window
# ---------------------------------------------------------------------------


class TestSoftwareWindow:
    def _window(self, loop, changes):
        return SoftwareWindow(
            on_change=lambda: changes.append(loop.now),
            call_later=loop.call_later,
            wall_now=loop.wall,
        )

    def test_sliding_moves_its_end_and_expires(self):
        loop, changes = FakeLoop(), []
        window = self._window(loop, changes)
        window.open()
        first_end = window.ends_at
        loop.advance_to(loop.now + 20)
        window.note_code()
        assert window.ends_at == first_end + timedelta(seconds=20)
        loop.advance_to(loop.now + 30.1)
        assert not window.capturing and window.state() == {
            "capturing": False, "window_ends_at": None, "capture_mode": None,
        }

    def test_the_ceiling_stops_a_sliding_window(self):
        loop, changes = FakeLoop(), []
        window = self._window(loop, changes)
        window.open("sliding", 30)
        opened = loop.now
        while window.capturing:
            loop.advance_to(loop.now + 10)
            window.note_code()
        assert loop.now - opened <= RF_WINDOW_MAX_S + 10
        assert loop.now - opened >= RF_WINDOW_MAX_S

    def test_single_closes_after_its_first_code_and_multiple_keeps_its_end(self):
        loop = FakeLoop()
        single = self._window(loop, [])
        single.open("single", 60)
        single.note_code()
        assert not single.capturing
        multiple = self._window(loop, [])
        multiple.open("multiple", 60)
        end = multiple.ends_at
        loop.advance_to(loop.now + 10)
        multiple.note_code()
        assert multiple.capturing and multiple.ends_at == end

    def test_seconds_is_capped_at_the_ceiling(self):
        loop = FakeLoop()
        window = self._window(loop, [])
        window.open("sliding", 10_000)
        assert window.seconds == RF_WINDOW_MAX_S

    @pytest.mark.asyncio
    async def test_a_listen_holds_it_and_its_closing_ends_the_listen(self):
        loop = FakeLoop()
        window = self._window(loop, [])
        ended = []
        arm = SoftwareWindowArm(
            window, on_failure=lambda err: None, on_window_closed=lambda: ended.append(1)
        )
        await arm.async_start()
        assert window.capturing and arm.owns_window
        loop.advance_to(loop.now + 60)  # past its 30 s length: held
        assert window.capturing
        window.close()  # the user closes it from the panel
        assert ended == [1]

    @pytest.mark.asyncio
    async def test_a_listen_closes_only_the_window_it_opened(self):
        loop = FakeLoop()
        window = self._window(loop, [])
        window.open()  # the user is already listening from the Sniffer
        arm = SoftwareWindowArm(window, on_failure=lambda e: None, on_window_closed=lambda: None)
        await arm.async_start()
        assert not arm.owns_window
        await arm.async_stop()
        assert window.capturing

    @pytest.mark.asyncio
    async def test_the_ceiling_ends_a_held_window_too(self):
        loop = FakeLoop()
        window = self._window(loop, [])
        ended = []
        arm = SoftwareWindowArm(
            window, on_failure=lambda e: None, on_window_closed=lambda: ended.append(1)
        )
        await arm.async_start()
        loop.advance_to(loop.now + RF_WINDOW_MAX_S + 1)
        assert not window.capturing and ended == [1]


# ---------------------------------------------------------------------------
# Fixture replay through the monitor
# ---------------------------------------------------------------------------


# Each press file: which buttons were pressed (three presses each, more
# in the 100us file), heard on one card with one row per button.
PRESSES = {
    "athom-433-it104-100us-4ms-presses.json.gz": {"1 ON", "1 OFF", "ALL ON", "2 OFF", "3 OFF"},
    "athom-433-it104-150us-4ms-presses.json.gz": {"1 ON", "1 OFF", "ALL OFF", "2 OFF", "3 OFF"},
    "athom-433-it104-250us-4ms-presses.json.gz": {"1 ON", "1 OFF", "ALL ON", "2 OFF", "3 ON"},
    "athom-433-it104-150us-6ms-presses.json.gz": {"1 ON", "1 OFF", "ALL ON", "2 OFF", "3 ON"},
    "athom-433-it104-150us-12ms-presses.json.gz": {"1 ON", "1 OFF", "ALL ON", "2 ON", "3 ON"},
    "athom-433-it104-150us-6ms-fs20-joint-presses.json.gz": {"1 ON", "1 OFF", "ALL ON", "ALL OFF"},
}


async def _replay(fake_hass, name, *, window=None, trigger_manager=None, monitor=None):
    loop = monitor[2] if monitor else FakeLoop()
    if monitor:
        mon, store = monitor[0], monitor[1]
    else:
        mon, store = _monitor(fake_hass, loop)
        mon.rf_always_on.attach(RID)
    if trigger_manager is not None:
        mon._trigger_manager = trigger_manager
    win = mon.rf_always_on.window(RID)

    def keep():
        if window == "open" and not win.capturing:
            win.open("multiple", RF_WINDOW_MAX_S)

    run = _Run(fake_hass, loop, mon)
    await run.feed(_schedule(_load(name)["captures"], loop.now), before=keep)
    return mon, store, loop


class TestReplay:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", sorted(PRESSES))
    async def test_window_open_one_card_one_row_per_button(self, fake_hass, name):
        monitor, store, _ = await _replay(fake_hass, name, window="open")
        devices = store.get_all_devices()
        assert len(devices) == 1
        assert devices[0].medium == MEDIUM_RF
        assert _rows(store) == Counter({button: 1 for button in PRESSES[name]})
        for signal in devices[0].signals:
            # Three presses (more in a few files) on one row: the replay's
            # 1-second pacing can split one press into two bursts.
            assert signal.hit_count >= 2
            assert signal.rf_frame_gap_source == RF_GAP_ASSUMED
            assert signal.rf_repeats_observed >= 2
        counters = monitor.rf_always_on.counters(RID)
        assert counters["minted"] == len(PRESSES[name])
        assert counters["new_window_closed"] == 0

    @pytest.mark.asyncio
    async def test_window_closed_mints_nothing_and_counts_what_it_drops(self, fake_hass):
        name = "athom-433-it104-150us-6ms-presses.json.gz"
        monitor, store, _ = await _replay(fake_hass, name, window=None)
        assert store.get_all_devices() == []
        counters = monitor.rf_always_on.counters(RID)
        assert counters["minted"] == 0
        assert counters["new_window_closed"] >= len(PRESSES[name])

    @pytest.mark.asyncio
    async def test_window_closed_known_rows_count_and_triggers_fire(self, fake_hass):
        name = "athom-433-it104-150us-6ms-presses.json.gz"
        loop = FakeLoop()
        monitor, store = _monitor(fake_hass, loop)
        monitor.rf_always_on.attach(RID)
        await _replay(fake_hass, name, window="open", monitor=(monitor, store, loop))
        hits_before = {
            _code_of(s): s.hit_count for d in store.get_all_devices() for s in d.signals
        }
        triggers = MagicMock()
        triggers.on_signal_captured = MagicMock(return_value=["trigger-1"])
        await _replay(fake_hass, name, window=None, trigger_manager=triggers,
                      monitor=(monitor, store, loop))
        hits_after = {
            _code_of(s): s.hit_count for d in store.get_all_devices() for s in d.signals
        }
        assert set(hits_after) == set(hits_before)  # no new row
        assert all(hits_after[b] > hits_before[b] for b in hits_before)
        assert triggers.on_signal_captured.call_count >= len(hits_before)

    @pytest.mark.asyncio
    async def test_presses_extend_a_sliding_window_to_the_ceiling_not_past(self, fake_hass):
        loop = FakeLoop()
        monitor, store = _monitor(fake_hass, loop)
        monitor.rf_always_on.attach(RID)
        window = monitor.rf_always_on.window(RID)
        # The file's first code is 35 s in and its laps sit up to ~50 s
        # apart, so a 60 s window is what its presses can keep open.
        window.open("sliding", 60)
        opened = loop.now
        closed_at = []
        close = window.close

        def recording_close():
            if window.capturing:
                closed_at.append(loop.now)
            close()

        window.close = recording_close
        first = "athom-433-it104-150us-6ms-presses.json.gz"
        laps = 0
        while window.capturing and laps < 10:
            await _replay(fake_hass, first, monitor=(monitor, store, loop))
            laps += 1
        # Opened for 60 s, carried by its presses to the ceiling, not past.
        assert closed_at == [pytest.approx(opened + RF_WINDOW_MAX_S)]
        minted = monitor.rf_always_on.counters(RID)["minted"]
        dropped = monitor.rf_always_on.counters(RID)["new_window_closed"]

        # The first new button after the ceiling bumps nothing new.
        await _replay(
            fake_hass, "athom-433-it104-150us-12ms-presses.json.gz",
            monitor=(monitor, store, loop),
        )
        assert "2 ON" not in _rows(store)
        counters = monitor.rf_always_on.counters(RID)
        assert counters["minted"] == minted
        assert counters["new_window_closed"] > dropped
        assert not window.capturing

    @pytest.mark.asyncio
    async def test_a_hidden_card_counts_and_mints_nothing_new(self, fake_hass):
        name = "athom-433-it104-150us-6ms-presses.json.gz"
        loop = FakeLoop()
        monitor, store = _monitor(fake_hass, loop)
        monitor.rf_always_on.attach(RID)
        await _replay(fake_hass, name, window="open", monitor=(monitor, store, loop))
        device = store.get_all_devices()[0]
        rows_before = len(device.signals)
        hits_before = device.hit_count
        store.is_dismissed = MagicMock(side_effect=lambda fp: fp == device.fingerprint)
        events_before = fake_hass.bus.async_fire.call_count
        await _replay(fake_hass, name, window="open", monitor=(monitor, store, loop))
        assert len(device.signals) == rows_before
        assert device.hit_count > hits_before
        fired = [c.args[0] for c in fake_hass.bus.async_fire.call_args_list[events_before:]]
        assert "hair_signal_detected" not in fired

    @pytest.mark.asyncio
    async def test_n15_a_radio_hit_says_its_rows_carrier(self, fake_hass):
        """A hit that moves a row's carrier (a better source on the ladder)
        reaches the Sniffer with the carrier the row holds after it, so the
        band cell updates in place (N15)."""
        name = "athom-433-it104-150us-6ms-presses.json.gz"
        loop = FakeLoop()
        monitor, store = _monitor(fake_hass, loop)
        monitor.rf_always_on.attach(RID)
        await _replay(fake_hass, name, window="open", monitor=(monitor, store, loop))
        signals = {s.id: s for s in store.get_all_devices()[0].signals}
        # A user-set 315 on every row, as on the bench; the next hits
        # carry whatever the ladder leaves on the row.
        for s in signals.values():
            s.rf_frequency_hz, s.rf_frequency_source = 315_000_000, "user"
        before = fake_hass.bus.async_fire.call_count
        # The second round's receiver measures the carrier (a signal
        # source), which outranks a user-set band on the ladder.
        win = monitor.rf_always_on.window(RID)
        win.open("multiple", RF_WINDOW_MAX_S)
        run = _Run(fake_hass, loop, monitor)
        await run.feed(
            _schedule(_load(name)["captures"], loop.now),
            frequency=433_920_000,
            before=lambda: win.capturing or win.open("multiple", RF_WINDOW_MAX_S),
        )
        last: dict[str, dict] = {}
        for call in fake_hass.bus.async_fire.call_args_list[before:]:
            if call.args[0] == "hair_signal_detected":
                last[call.args[1]["signal_id"]] = call.args[1]
        assert last
        moved = [s for s in signals.values() if s.rf_frequency_hz == 433_920_000]
        assert moved, "no row took the measured carrier"
        assert all(s.rf_frequency_source != "user" for s in moved)
        for signal_id, data in last.items():
            assert data["medium"] == MEDIUM_RF
            assert data["rf_frequency_hz"] == signals[signal_id].rf_frequency_hz
            assert data["rf_frequency_source"] == signals[signal_id].rf_frequency_source

    @pytest.mark.asyncio
    async def test_noise_hour_window_closed_mints_nothing(self, fake_hass):
        monitor, store, _ = await _replay(
            fake_hass, "athom-433-150us-6ms-noise-1h.json.gz", window=None
        )
        assert store.get_all_devices() == []
        counters = monitor.rf_always_on.counters(RID)
        assert counters["captures"] == 11_857
        assert counters["minted"] == 0

    @pytest.mark.asyncio
    async def test_noise_hour_window_held_open_mints_nothing(self, fake_hass):
        """An hour of noise with the window open the whole time.

        A few bursts of noise pass the frame vote (two agreeing frames,
        each with a body), but every one is a body of four to six edges,
        under ``RF_MIN_BODY_EDGES``, so none becomes a row. They count as
        noise instead.
        """
        monitor, store, _ = await _replay(
            fake_hass, "athom-433-150us-6ms-noise-1h.json.gz", window="open"
        )
        assert store.get_all_devices() == []
        counters = monitor.rf_always_on.counters(RID)
        assert counters["minted"] == 0
        # The noise captures, plus the five voted scraps (4 to 6 edges).
        assert counters["noise"] == 475 + 5

    @pytest.mark.asyncio
    async def test_noise_hour_with_filter_symbols(self, fake_hass):
        """The same, at ``filter_symbols: 20`` (a fixture kept outside the repository)."""
        name = "athom-433-150us-6ms-fs20-noise-1h.json.gz"
        _m, closed, _ = await _replay(fake_hass, name, window=None)
        assert closed.get_all_devices() == []
        _m, held, _ = await _replay(fake_hass, name, window="open")
        assert held.get_all_devices() == []


# ---------------------------------------------------------------------------
# One button, two receivers
# ---------------------------------------------------------------------------


def _rm4_schedule(start):
    with gzip.open(ATHOM / "rm4pro-433-it104-joint-presses.json.gz", "rb") as handle:
        data = json.loads(handle.read())
    return [
        (start + item["t"], [v if i % 2 == 0 else -v for i, v in enumerate(item["pulses"])])
        for item in data["captures"]
    ]


class TestTwoReceivers:
    async def _both(self, fake_hass, first):
        loop = FakeLoop()
        monitor, store = _monitor(fake_hass, loop)
        monitor.rf_always_on.attach(RID)
        monitor.rf_always_on.window(RID).open("multiple", RF_WINDOW_MAX_S)
        run = _Run(fake_hass, loop, monitor)
        athom = _schedule(
            _load("athom-433-it104-150us-6ms-fs20-joint-presses.json.gz")["captures"],
            loop.now,
        )
        rm4 = _rm4_schedule(loop.now)
        order = [(athom, RID, None), (rm4, RM4, 433_920_000)]
        if first == "rm4":
            order.reverse()
        for schedule, receiver, frequency in order:
            await run.feed(
                [(at + loop.now - schedule[0][0] + 1, t) for at, t in schedule],
                receiver=receiver, frequency=frequency,
            )
        return store

    @pytest.mark.asyncio
    @pytest.mark.parametrize("first", ["athom", "rm4"])
    async def test_one_row_per_button_whichever_is_heard_first(self, fake_hass, first):
        store = await self._both(fake_hass, first)
        assert len(store.get_all_devices()) == 1
        assert _rows(store) == Counter({"1 ON": 1, "1 OFF": 1, "ALL ON": 1, "ALL OFF": 1})
        for signal in store.get_all_devices()[0].signals:
            # The row keeps the better of what each receiver told it.
            assert signal.rf_frame_gap_source == RF_GAP_MEASURED
            assert signal.rf_frequency_source == RF_FREQUENCY_SOURCE_SIGNAL

    def test_the_hash_is_the_voted_frames_not_the_first(self):
        """A burst whose first frame reads a variant hash still votes the
        hash the other receiver gives for that button."""
        rm4 = {}
        for _at, timings in _rm4_schedule(0.0):
            analysis = rf_frames.analyze(timings)
            rm4[analysis.fingerprint] = analysis.frame_hash
        data = _load("athom-433-it104-150us-6ms-fs20-joint-presses.json.gz")
        frames = []
        for _second, timings in data["captures"]:
            for piece, parts in rf_frames.bodied_pieces(rf_frames.split_frames(timings)):
                if len(parts.body) == 49:
                    frames.append((piece, parts))
        found = 0
        for start in range(len(frames) - 5):
            window = frames[start:start + 6]
            prints = {rf_frames.frame_fingerprint(p) for _, p in window}
            if len(prints) != 1:
                continue
            fp = prints.pop()
            first = rf_frames.frame_hash(window[0][1])
            if fp in rm4 and first != rm4[fp]:
                assert rf_frames.vote(window).frame_hash == rm4[fp]
                found += 1
        assert found >= 1


class TestUpgrade:
    def test_measured_beats_assumed_and_signal_beats_receiver(self):
        row = types.SimpleNamespace(
            rf_frame_gap_us=30_000, rf_frame_gap_source=RF_GAP_ASSUMED,
            rf_frequency_hz=433_920_000, rf_frequency_source=RF_FREQUENCY_SOURCE_RECEIVER,
        )
        better = types.SimpleNamespace(
            rf_frame_gap_us=12_881, rf_frame_gap_source=RF_GAP_MEASURED,
            rf_frequency_hz=433_880_000, rf_frequency_source=RF_FREQUENCY_SOURCE_SIGNAL,
        )
        assert upgrade_rf_fields(row, better)
        assert (row.rf_frame_gap_us, row.rf_frame_gap_source) == (12_881, RF_GAP_MEASURED)
        assert row.rf_frequency_source == RF_FREQUENCY_SOURCE_SIGNAL
        assert not upgrade_rf_fields(row, types.SimpleNamespace(
            rf_frame_gap_us=30_000, rf_frame_gap_source=RF_GAP_ASSUMED,
            rf_frequency_hz=433_920_000, rf_frequency_source=RF_FREQUENCY_SOURCE_RECEIVER,
        ))
        assert row.rf_frame_gap_us == 12_881
