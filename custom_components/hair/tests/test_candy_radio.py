"""Radio in the Candy Drawer, and the verdict every drawer event carries.

What is pinned here:

- the radio event shapes (a voted press, a lone frame, the static summary,
  a single static capture, a send), plain JSON with the infrared-only
  keys null;
- ``frame``, ``frequency_hz`` and ``gap_us`` are what the row minted from
  the same capture holds, so the panel's ``toSub`` gives the radio
  editor's ``.sub`` (``rf_paste.to_sub`` is its pinned twin);
- the receive path: a whole capture prints one press; frames handed to
  the burst assembler print as frames, then the voted press; a capture
  with no body and a vote too short to be a remote's are static;
- the static summary: at most one per receiver every 5 s, single
  captures only to a subscription that asked for them;
- the verdict: echo, then device, then trigger, then Sniffer row, and
  working it out changes nothing;
- a radio send prints a TX block and its echo names it;
- the infrared ditto carries the verdict of the frame it repeats;
- with nobody subscribed, nothing is built on any radio branch.
"""
from __future__ import annotations

import collections
import json
import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import candy_feed, rf_frames, rf_paste, rf_send
from custom_components.hair import signal_monitor as sm
from custom_components.hair.const import (
    MEDIUM_RF,
    RF_PROTOCOL,
    CommandCategory,
    CommandSource,
)
from custom_components.hair.models import IRCommand
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore

from .test_rf_hear import FIXTURE, _signed

RX = "radio_frequency.rm4_pro_receiver"
ATHOM_RX = "radio_frequency.athom_rf_receiver"
ATHOM_TX = "radio_frequency.athom_rf_transmitter"
IR_RX = "infrared.living_ir"
HZ = 433_920_000
STATIC_CAPTURE = [312]  # a lone mark: no body


@pytest.fixture(scope="module")
def captures():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["captures"]


@pytest.fixture(scope="module")
def keyfob(captures):
    return rf_frames.analyze(_signed(captures[0]["pulses"]))


def _hair_store():
    hair = MagicMock()
    hair.get_all_devices = MagicMock(return_value=[])
    hair.get_device = MagicMock(return_value=None)
    hair.match_command = MagicMock(return_value=None)
    hair.get_triggers_for_signal = MagicMock(return_value=[])
    return hair


def _monitor(fake_hass):
    store = SignalStore(fake_hass)
    store._loaded = True
    store.schedule_save = MagicMock()
    fake_hass.loop = MagicMock()
    fake_hass.loop.call_later = MagicMock(return_value=MagicMock())
    fake_hass.loop.call_at = MagicMock(return_value=MagicMock())
    fake_hass.loop.time = MagicMock(return_value=100.0)
    fake_hass.states.get = MagicMock(return_value=None)
    fake_hass.bus = MagicMock()
    hair = _hair_store()
    monitor = SignalMonitor(fake_hass, store, hair)
    return monitor, store, hair


def _subscribe(monitor, static=False) -> list[dict]:
    events: list[dict] = []
    monitor.candy_subscribe(events.append, static=static)
    return events


def _signal(timings, frequency=HZ):
    return types.SimpleNamespace(
        timings=list(timings), frequency=frequency, modulation="ook"
    )


async def _hear(fake_hass, monitor, timings_list, receiver=RX):
    """Captures through the receive path, the pipeline run to the end."""
    tasks = []
    fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
    for timings in timings_list:
        monitor._on_rf_signal(_signal(timings), receiver)
        while tasks:
            await tasks.pop(0)


async def _flush_bursts(fake_hass, monitor, receiver):
    tasks = []
    fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
    monitor._rf_bursts[receiver].flush()
    while tasks:
        await tasks.pop(0)


def _one_frame_captures(keyfob, n=6):
    """The keyfob as a one-frame-per-capture receiver delivers it: each
    frame its own capture, ending on a mark (the receiver's idle is not
    a gap)."""
    body = [v for v in keyfob.frame]
    if body[-1] < 0:
        body = body[:-1]
    return [list(body) for _ in range(n)]


def _command(frame, **fields) -> IRCommand:
    command = IRCommand(
        id="c1", name="On", category=CommandCategory.CUSTOM,
        source=CommandSource.CAPTURED, protocol=RF_PROTOCOL, code=None,
        raw_timings=list(frame),
    )
    command.medium = MEDIUM_RF
    command.rf_frequency_hz = fields.pop("rf_frequency_hz", HZ)
    command.rf_frame_gap_us = fields.pop("rf_frame_gap_us", 12_881)
    command.send_count = fields.pop("send_count", 4)
    return command


def _plan(row, *transmitters, on_air=HZ, skipped=None):
    timings = rf_send.wire_frame(row)
    count = rf_send.send_count_for(row, timings)
    plan = rf_send.RadioSend(
        timings=timings, count=count, air_s=rf_send.burst_air_s(timings, count)
    )
    for entity_id in transmitters:
        plan.attempted.append(entity_id)
        plan.fits[entity_id] = rf_send.TransmitterFit(
            True, on_air, on_air != row.rf_frequency_hz, None
        )
    plan.skipped.update(skipped or {})
    return plan


IR_ONLY = ("address", "command", "covers", "carrier_hz", "pronto", "ditto")


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


class TestShapes:
    @pytest.mark.asyncio
    async def test_a_whole_capture_prints_one_press(self, fake_hass, keyfob, captures):
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor)
        capture = _signed(captures[0]["pulses"])
        await _hear(fake_hass, monitor, [capture])
        assert len(events) == 1
        press = events[0]
        json.dumps(press)
        assert (press["medium"], press["stage"], press["dir"]) == (MEDIUM_RF, "press", "rx")
        assert press["verdict"] == "unknown" and press["known_from"] is None
        assert press["fingerprint"] == keyfob.fingerprint
        assert press["frame_hash"] == keyfob.frame_hash
        assert press["votes"] == keyfob.votes
        assert press["frames"] >= press["votes"]
        assert press["frequency_hz"] == HZ and press["frequency_source"] == "signal"
        assert press["modulation"] == "OOK"
        assert press["raw"] == capture
        assert press["protocol"] is None
        assert all(press[key] is None for key in IR_ONLY)

    @pytest.mark.asyncio
    async def test_the_sub_is_the_rows_own(self, fake_hass, keyfob, captures):
        """``frame``, ``frequency_hz``, ``gap_us`` are the minted row's, so
        the editor's writer gives the same ``.sub`` for both."""
        monitor, store, _ = _monitor(fake_hass)
        events = _subscribe(monitor)
        await _hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        row = store.get_all_devices()[0].signals[0]
        press = events[0]
        assert press["frame"] == list(row.raw_timings)
        assert press["frequency_hz"] == row.rf_frequency_hz
        assert press["gap_us"] == row.rf_frame_gap_us
        assert rf_paste.to_sub(
            press["frame"], press["frequency_hz"], press["gap_us"]
        ) == rf_paste.to_sub(row.raw_timings, row.rf_frequency_hz, row.rf_frame_gap_us)

    @pytest.mark.asyncio
    async def test_frames_print_before_their_press(self, fake_hass, keyfob):
        monitor, store, _ = _monitor(fake_hass)
        events = _subscribe(monitor)
        frames = _one_frame_captures(keyfob)
        await _hear(fake_hass, monitor, frames, receiver=ATHOM_RX)
        await _flush_bursts(fake_hass, monitor, ATHOM_RX)
        stages = [e["stage"] for e in events]
        assert stages == ["frame"] * len(frames) + ["press"]
        frame = events[0]
        json.dumps(frame)
        assert frame["verdict"] == "unknown"
        assert frame["fingerprint"] == keyfob.fingerprint
        assert frame["frames"] == 1 and frame["votes"] is None
        assert frame["raw"] == frames[0]
        # What a row minted from this burst holds: the assumed gap.
        assert frame["gap_us"] == sm.RF_ASSUMED_FRAME_GAP_US
        assert frame["gap_source"] == "assumed"
        press = events[-1]
        assert press["frames"] == len(frames)
        # A burst never existed as one capture: raw is the voted frame.
        assert press["raw"] == press["frame"]
        assert len(store.get_all_devices()) == 1

    def test_a_piece_with_a_measured_gap_keeps_it_last(self):
        """As a row stores one frame: signed, the gap last when measured."""
        closed = rf_frames.FramePiece((400, 1200, 1200, 400, 400, 12_881), 12_881)
        open_ = rf_frames.FramePiece((400, 1200, 1200, 400, 400), None)
        assert rf_frames.piece_frame(closed) == [400, -1200, 1200, -400, 400, -12_881]
        assert rf_frames.piece_frame(open_) == [400, -1200, 1200, -400, 400]

    @pytest.mark.asyncio
    async def test_a_frame_of_a_held_code_reads_known(self, fake_hass, keyfob):
        monitor, _, _ = _monitor(fake_hass)
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob), receiver=ATHOM_RX)
        await _flush_bursts(fake_hass, monitor, ATHOM_RX)
        events = _subscribe(monitor)
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob, 2), receiver=ATHOM_RX)
        assert [e["stage"] for e in events] == ["frame", "frame"]
        assert events[0]["verdict"] == "known"
        assert events[0]["known_from"] == "sniffer"
        assert events[0]["known_name"].endswith("/ Signal 1")


# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------


class TestStatic:
    @pytest.mark.asyncio
    async def test_a_capture_with_no_body_is_counted_not_printed(self, fake_hass):
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor)
        await _hear(fake_hass, monitor, [STATIC_CAPTURE] * 7)
        assert events == []
        # One timer per receiver, armed by the first capture.
        assert fake_hass.loop.call_later.call_count == 1
        delay, flush = fake_hass.loop.call_later.call_args[0]
        assert delay == candy_feed.CANDY_STATIC_SUMMARY_S
        flush()
        assert len(events) == 1
        summary = events[0]
        json.dumps(summary)
        assert (summary["verdict"], summary["stage"], summary["count"]) == ("static", "static", 7)
        assert summary["entity_id"] == RX and "raw" not in summary
        # The next static capture opens a new window.
        await _hear(fake_hass, monitor, [STATIC_CAPTURE])
        assert fake_hass.loop.call_later.call_count == 2

    @pytest.mark.asyncio
    async def test_single_captures_go_only_to_who_asked(self, fake_hass):
        monitor, _, _ = _monitor(fake_hass)
        plain = _subscribe(monitor)
        static = _subscribe(monitor, static=True)
        await _hear(fake_hass, monitor, [STATIC_CAPTURE] * 3)
        assert plain == []
        assert [e["count"] for e in static] == [None, None, None]
        assert static[0]["raw"] == STATIC_CAPTURE and static[0]["values"] == 1
        fake_hass.loop.call_later.call_args[0][1]()
        assert [e["count"] for e in plain] == [3]
        assert static[-1]["count"] == 3

    @pytest.mark.asyncio
    async def test_a_vote_too_short_to_be_a_remote_is_static(
        self, fake_hass, keyfob, captures, monkeypatch
    ):
        """A repeating scrap can pass the vote; the pipeline counts it as
        noise and never files it, and the drawer calls it static."""
        monkeypatch.setattr(sm, "RF_MIN_BODY_EDGES", keyfob.body_edges + 1)
        monitor, store, _ = _monitor(fake_hass)
        events = _subscribe(monitor, static=True)
        capture = _signed(captures[0]["pulses"])
        await _hear(fake_hass, monitor, [capture])
        assert [(e["stage"], e["count"]) for e in events] == [("static", None)]
        assert events[0]["raw"] == capture
        assert store.get_all_devices() == []
        fake_hass.loop.call_later.call_args[0][1]()
        assert events[-1]["count"] == 1

    def test_closing_the_drawer_drops_the_windows(self, fake_hass):
        monitor, _, _ = _monitor(fake_hass)
        listener = MagicMock()
        monitor.candy_subscribe(listener)
        monitor._on_rf_signal(_signal(STATIC_CAPTURE), RX)
        handle = fake_hass.loop.call_later.return_value
        monitor.candy_unsubscribe(listener)
        handle.cancel.assert_called_once()
        assert monitor._candy_static_window == {}


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------


class TestVerdict:
    def _known(self, monitor, keyfob):
        return monitor._candy_known(
            sig_fp=keyfob.fingerprint, byte_hash=keyfob.frame_hash,
            decoded_fingerprint=None, norm_fp=None, protocol=RF_PROTOCOL,
            code=None, decode_covers=None,
        )

    @pytest.mark.asyncio
    async def test_device_then_trigger_then_sniffer(self, fake_hass, keyfob, captures):
        monitor, _, hair = _monitor(fake_hass)
        await _hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        device = types.SimpleNamespace(
            name="Bench Plug",
            get_command=lambda cid: types.SimpleNamespace(name="On") if cid == "c1" else None,
        )
        hair.match_command.return_value = ("d1", "c1")
        hair.get_device.return_value = device
        hair.get_triggers_for_signal.return_value = [
            types.SimpleNamespace(name="Porch"), types.SimpleNamespace(name="Desk"),
        ]
        assert self._known(monitor, keyfob) == candy_feed.CandyVerdict(
            "known", "device", "Bench Plug / On"
        )
        hair.match_command.return_value = None
        assert self._known(monitor, keyfob) == candy_feed.CandyVerdict(
            "known", "trigger", "Desk"
        )
        hair.get_triggers_for_signal.return_value = []
        verdict = self._known(monitor, keyfob)
        assert (verdict.verdict, verdict.known_from) == ("known", "sniffer")
        assert verdict.known_name == "Remote 1 / Signal 1"

    def test_a_code_held_nowhere_is_unknown(self, fake_hass, keyfob):
        monitor, _, _ = _monitor(fake_hass)
        assert self._known(monitor, keyfob) == candy_feed.UNKNOWN

    def test_the_trigger_lookup_is_the_unscoped_matcher(self, fake_hass, keyfob):
        """Known means held anywhere: the store's matcher, no receiver
        scope, and never the trigger manager's firing path."""
        monitor, _, hair = _monitor(fake_hass)
        monitor._trigger_manager = MagicMock()
        self._known(monitor, keyfob)
        hair.get_triggers_for_signal.assert_called_once_with(
            RF_PROTOCOL, None, keyfob.fingerprint, keyfob.frame_hash, None, None, None
        )
        assert not monitor._trigger_manager.method_calls

    def test_the_drawers_filing_lookup_prunes_nothing(self, fake_hass, keyfob):
        monitor, store, _ = _monitor(fake_hass)
        with patch.object(store, "find_filed_signal", return_value=None) as find:
            self._known(monitor, keyfob)
        assert find.call_args.kwargs == {"prune": False}

    def test_prune_false_leaves_the_index_as_it_is(self, fake_hass, keyfob):
        from custom_components.hair.identity import SignalIdentity
        from custom_components.hair.models import UnknownDevice

        from .test_rf_hear import _rf_signal

        _, store, _ = _monitor(fake_hass)
        device = UnknownDevice(id="gone", fingerprint="x", signals=[_rf_signal(keyfob)])
        store.index_signal(device, device.signals[0])  # never added: a dead entry
        before = {k: list(v) for k, v in store._sig_index.items()}
        identity = SignalIdentity(None, keyfob.frame_hash, keyfob.fingerprint)
        assert store.find_filed_signal(identity, prune=False) is None
        assert {k: list(v) for k, v in store._sig_index.items()} == before
        store.find_filed_signal(identity)
        assert store._sig_index == {}

    def test_a_mirror_row_is_never_the_sniffer_answer(self, fake_hass, keyfob):
        """The Mirror is HAIR's log of its own sends and is never in the
        filing index, so a press of a code HAIR once sent cannot read
        ``known: Mirror / ...``."""
        from custom_components.hair.const import MIRROR_DEVICE_FP
        from custom_components.hair.models import UnknownDevice

        from .test_rf_hear import _rf_signal

        monitor, store, _ = _monitor(fake_hass)
        mirror = UnknownDevice(
            id="m", fingerprint=MIRROR_DEVICE_FP, source="echo",
            signals=[_rf_signal(keyfob)],
        )
        store.add_device(mirror)
        store.index_signal(mirror, mirror.signals[0])
        assert self._known(monitor, keyfob) == candy_feed.UNKNOWN

    @pytest.mark.asyncio
    async def test_the_drawer_changes_nothing(self, fake_hass):
        """An always-on receiver, presses through the burst assembler with
        noise between them, a window open for the first file and closed
        for the second, a trigger on the frame path. Rows, saves, the
        receiver's counters and every trigger call come out the same with
        the drawer open (Static on) and closed."""
        from . import test_rf_always_on as ao

        files = [
            ("athom-433-it104-150us-6ms-presses.json.gz", "open"),
            ("athom-433-it104-150us-12ms-presses.json.gz", None),
        ]

        async def run(open_drawer):
            loop = ao.FakeLoop()
            monitor, store = ao._monitor(fake_hass, loop)
            monitor.rf_always_on.attach(ao.RID)
            store.async_save = MagicMock(side_effect=lambda: _noop())
            triggers = MagicMock()
            triggers.on_signal_captured = MagicMock(return_value=["trigger-1"])
            monitor._trigger_manager = triggers
            if open_drawer:
                _subscribe(monitor, static=True)
            for name, window in files:
                await ao._replay(
                    fake_hass, name, window=window, trigger_manager=triggers,
                    monitor=(monitor, store, loop),
                )
            rows = []
            for device in store.get_all_devices():
                for signal in device.signals:
                    rows.append((
                        device.fingerprint, signal.rf_frame_hash, signal.hit_count,
                        list(signal.raw_timings), signal.rf_frequency_hz,
                    ))
            fires = [
                (c.args[:3], sorted(c.kwargs.items(), key=lambda kv: kv[0]))
                for c in triggers.on_signal_captured.call_args_list
            ]
            counters = dict(monitor.rf_always_on.counters(ao.RID))
            counters.pop("since", None)
            return (
                sorted(rows),
                store.schedule_save.call_count,
                counters,
                [str(f) for f in fires],
            )

        closed = await run(False)
        opened = await run(True)
        assert closed[0], "the presses minted rows"
        assert closed[3], "the trigger was asked on the frame path"
        assert opened == closed


# ---------------------------------------------------------------------------
# An always-on receiver's noise, with a drawer open
# ---------------------------------------------------------------------------


class TestAlwaysOnNoise:
    """The review's blocker: on an Athom most bodied pieces are noise that
    never votes. With Static off the drawer must print none of them."""

    @staticmethod
    async def _replay(fake_hass, name, *, monitor=None, window=None):
        from . import test_rf_always_on as ao

        loop = monitor[2] if monitor else ao.FakeLoop()
        if monitor is None:
            mon, store = ao._monitor(fake_hass, loop)
            mon.rf_always_on.attach(ao.RID)
            monitor = (mon, store, loop)
        events = monitor[3] if len(monitor) > 3 else None
        flushes = []
        real_call_later = loop.call_later

        def call_later(delay, fn, *args):
            flushes.append(1)
            return real_call_later(delay, fn, *args)

        loop.call_later = call_later
        await ao._replay(fake_hass, name, window=window, monitor=monitor[:3])
        loop.advance_to(loop.now + candy_feed.CANDY_STATIC_SUMMARY_S + 1)
        return monitor, events

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", [
        "athom-433-150us-6ms-noise-1h.json.gz",
        "athom-433-150us-6ms-fs20-noise-1h.json.gz",
    ])
    async def test_an_hour_of_noise_prints_only_summaries(self, fake_hass, name):
        from . import test_rf_always_on as ao

        loop = ao.FakeLoop()
        monitor, store = ao._monitor(fake_hass, loop)
        monitor.rf_always_on.attach(ao.RID)
        events = _subscribe(monitor)
        captures = ao._load(name)["captures"]
        await ao._replay(fake_hass, name, monitor=(monitor, store, loop))
        loop.advance_to(loop.now + candy_feed.CANDY_STATIC_SUMMARY_S + 1)
        stages = {e["stage"] for e in events}
        assert stages == {"static"}
        assert all(e["count"] is not None for e in events)  # summaries only
        assert sum(e["count"] for e in events) == len(captures)
        assert monitor._candy_hold.get(ao.RID, ()) == collections.deque() or not (
            monitor._candy_hold.get(ao.RID)
        )

    @pytest.mark.asyncio
    async def test_a_known_press_in_the_noise_prints_and_nothing_else(self, fake_hass):
        from . import test_rf_always_on as ao

        name = "athom-433-it104-150us-6ms-presses.json.gz"
        loop = ao.FakeLoop()
        monitor, store = ao._monitor(fake_hass, loop)
        monitor.rf_always_on.attach(ao.RID)
        await ao._replay(fake_hass, name, window="open", monitor=(monitor, store, loop))
        held_codes = {
            s.rf_fingerprint if hasattr(s, "rf_fingerprint") else s.fingerprint
            for d in store.get_all_devices() for s in d.signals
        }
        assert held_codes
        events = _subscribe(monitor)
        await ao._replay(fake_hass, name, window=None, monitor=(monitor, store, loop))
        loop.advance_to(loop.now + candy_feed.CANDY_STATIC_SUMMARY_S + 1)
        printed = [e for e in events if e["stage"] in ("frame", "press")]
        assert any(e["stage"] == "press" for e in printed)
        assert any(e["stage"] == "frame" and e["verdict"] == "known" for e in printed)
        assert {e["fingerprint"] for e in printed} <= held_codes
        assert all(e["stage"] in ("frame", "press", "static") for e in events)

    @pytest.mark.asyncio
    async def test_a_lone_burst_goes_to_static_with_its_reason(self, fake_hass, keyfob):
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor, static=True)
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob, 1), receiver=ATHOM_RX)
        assert events == []  # held, not printed
        await _flush_bursts(fake_hass, monitor, ATHOM_RX)
        assert [(e["stage"], e["reason"]) for e in events] == [("static", "lone")]
        assert events[0]["raw"] == _one_frame_captures(keyfob, 1)[0]
        assert monitor._candy_hold[ATHOM_RX] == collections.deque()

    @pytest.mark.asyncio
    async def test_the_hold_is_bounded(self, fake_hass, keyfob, monkeypatch):
        monkeypatch.setattr(candy_feed, "CANDY_HOLD_MAX", 3)
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor, static=True)
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob, 5), receiver=ATHOM_RX)
        assert len(monitor._candy_hold[ATHOM_RX]) == 3
        assert [e["reason"] for e in events] == ["lone", "lone"]

    @pytest.mark.asyncio
    async def test_reasons_on_single_static_captures(self, fake_hass, captures, monkeypatch):
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor, static=True)
        await _hear(fake_hass, monitor, [STATIC_CAPTURE])
        monkeypatch.setattr(sm, "RF_MIN_BODY_EDGES", 10_000)
        await _hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        assert [e["reason"] for e in events] == ["no_body", "short"]


# ---------------------------------------------------------------------------
# A failing drawer never costs a capture or a send
# ---------------------------------------------------------------------------


def _boom(*_args, **_kwargs):
    raise RuntimeError("drawer failure")


class TestGuards:
    @pytest.mark.asyncio
    async def test_a_failing_press_print_still_files_the_press(self, fake_hass, captures):
        monitor, store, _ = _monitor(fake_hass)
        _subscribe(monitor)
        with patch.object(candy_feed, "rf_press_event", _boom):
            await _hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        assert len(store.get_all_devices()) == 1

    @pytest.mark.asyncio
    async def test_a_failing_frame_print_still_assembles(self, fake_hass, keyfob):
        monitor, store, _ = _monitor(fake_hass)
        _subscribe(monitor)
        with patch.object(candy_feed, "rf_frame_event", _boom):
            await _hear(fake_hass, monitor, _one_frame_captures(keyfob), receiver=ATHOM_RX)
            await _flush_bursts(fake_hass, monitor, ATHOM_RX)
        assert len(store.get_all_devices()) == 1

    @pytest.mark.asyncio
    async def test_a_failing_release_still_emits_the_press(self, fake_hass, keyfob):
        monitor, store, _ = _monitor(fake_hass)
        _subscribe(monitor)
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob), receiver=ATHOM_RX)
        with patch.object(monitor, "_candy_release", _boom):
            await _flush_bursts(fake_hass, monitor, ATHOM_RX)
        assert len(store.get_all_devices()) == 1

    @pytest.mark.asyncio
    async def test_a_failing_lone_release_still_counts_the_lone_frame(
        self, fake_hass, keyfob
    ):
        monitor, _, _ = _monitor(fake_hass)
        monitor.rf_always_on.count = MagicMock()
        _subscribe(monitor)
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob, 1), receiver=ATHOM_RX)
        with patch.object(monitor, "_candy_release", _boom):
            await _flush_bursts(fake_hass, monitor, ATHOM_RX)
        monitor.rf_always_on.count.assert_called_once_with(ATHOM_RX, "lone_frames")

    @pytest.mark.asyncio
    async def test_a_failing_static_print_still_counts_the_noise(self, fake_hass):
        from . import test_rf_always_on as ao

        loop = ao.FakeLoop()
        monitor, _ = ao._monitor(fake_hass, loop)
        monitor.rf_always_on.attach(ao.RID)
        _subscribe(monitor, static=True)
        run = ao._Run(fake_hass, loop, monitor)
        with patch.object(candy_feed, "rf_static_capture_event", _boom):
            await run.feed([(loop.now + 0.1, list(STATIC_CAPTURE))])
        assert monitor.rf_always_on.counters(ao.RID)["noise"] == 1

    def test_a_failing_radio_tx_print_still_sends(self, fake_hass, keyfob):
        monitor, _, _ = _monitor(fake_hass)
        _subscribe(monitor)
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        row = _command(keyfob.frame)
        with patch.object(candy_feed, "rf_tx_event", _boom):
            monitor.record_send_rf(row, _plan(row, ATHOM_TX), "Plug / On")
        ticket = monitor._echo_expectations[-1]
        assert ticket["candy_seq"] is None and ticket["sig_fp"] == keyfob.fingerprint

    def test_a_failing_infrared_tx_print_still_sends(self):
        from .test_candy_feed import _monitor as ir_monitor
        from .test_candy_feed import _send

        monitor, _, _ = ir_monitor()
        _subscribe(monitor)
        with patch.object(candy_feed, "tx_event", _boom):
            _send(monitor, _nec())
        assert monitor._echo_expectations[-1]["candy_seq"] is None

    @pytest.mark.asyncio
    async def test_a_failing_ditto_print_still_attributes_the_ditto(self):
        monitor, hass, _ = TestDitto()._ir_monitor()
        _subscribe(monitor)
        with patch.object(candy_feed, "ditto_event", _boom), patch.object(
            monitor, "_maybe_attribute_repeat_frame"
        ) as attribute:
            await TestDitto()._press(monitor, hass, DITTO)
        attribute.assert_called_once()


# ---------------------------------------------------------------------------
# Stopping
# ---------------------------------------------------------------------------


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_leaves_the_drawer_nothing(self, fake_hass, keyfob):
        from unittest.mock import AsyncMock

        monitor, store, _ = _monitor(fake_hass)
        store.async_shutdown = AsyncMock()
        _subscribe(monitor, static=True)
        await _hear(fake_hass, monitor, [STATIC_CAPTURE])
        await _hear(fake_hass, monitor, _one_frame_captures(keyfob, 1), receiver=ATHOM_RX)
        handle = fake_hass.loop.call_later.return_value
        await monitor.async_stop()
        handle.cancel.assert_called()
        assert monitor._candy == [] and monitor._candy_static == []
        assert monitor._candy_static_window == {}
        assert monitor._candy_hold == {} and monitor._candy_memo == {}


# ---------------------------------------------------------------------------
# Radio send
# ---------------------------------------------------------------------------


class TestSend:
    def test_the_tx_block(self, fake_hass, keyfob):
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor)
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        row = _command(keyfob.frame)
        plan = _plan(row, ATHOM_TX, skipped={"radio_frequency.rm4": "unavailable"})
        monitor.record_send_rf(
            row, plan, "Bench Plug / On",
            device_name="Bench Plug", command_name="On", origin="manager",
        )
        assert len(events) == 1
        tx = events[0]
        json.dumps(tx)
        assert (tx["dir"], tx["medium"], tx["verdict"], tx["seq"]) == ("tx", MEDIUM_RF, "known", 1)
        assert tx["known_from"] is None and tx["stage"] is None
        assert [e["entity_id"] for e in tx["emitters"]] == [ATHOM_TX]
        assert tx["skipped"] == [{
            "entity_id": "radio_frequency.rm4",
            "name": monitor._friendly_name("radio_frequency.rm4"),
            "reason": "unavailable",
        }]
        assert (tx["device"], tx["command_name"], tx["origin"]) == ("Bench Plug", "On", "manager")
        assert tx["sends"] == plan.count
        assert (tx["frequency_hz"], tx["on_air_hz"], tx["substituted"]) == (HZ, HZ, False)
        assert tx["frame"] == list(row.raw_timings) and tx["gap_us"] == 12_881
        assert tx["raw"] == list(plan.timings)
        assert tx["fingerprint"] == keyfob.fingerprint
        assert monitor._echo_expectations[-1]["candy_seq"] == 1

    @pytest.mark.asyncio
    async def test_the_echo_names_its_send(self, fake_hass, keyfob, captures):
        monitor, _, _ = _monitor(fake_hass)
        events = _subscribe(monitor)
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        row = _command(keyfob.frame)
        monitor.record_send_rf(row, _plan(row, ATHOM_TX), "Plug / On")
        ticket = monitor._echo_expectations[-1]
        monitor._arm_expectation(ticket, 0.0)
        ticket["armed_at"], ticket["expires"] = 0.0, float("inf")
        mark = MagicMock(side_effect=lambda *_: _noop())
        with patch.object(monitor, "_mirror_mark_heard", mark):
            await _hear(
                fake_hass, monitor, [_signed(captures[0]["pulses"])], receiver=ATHOM_RX
            )
        echo = events[-1]
        assert echo["stage"] == "press"
        assert (echo["echo"], echo["echo_of"]) == ("send", 1)
        assert (echo["verdict"], echo["known_from"]) == ("known", "echo")

    def test_nothing_is_built_for_a_send_nobody_watches(self, fake_hass, keyfob):
        monitor, _, _ = _monitor(fake_hass)
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        row = _command(keyfob.frame)
        with patch.object(candy_feed, "rf_tx_event") as build:
            monitor.record_send_rf(row, _plan(row, ATHOM_TX), "Plug / On")
        build.assert_not_called()
        assert monitor._echo_expectations[-1]["candy_seq"] is None


async def _noop():
    return None


# ---------------------------------------------------------------------------
# The hot path with nobody subscribed
# ---------------------------------------------------------------------------


class TestCost:
    @pytest.mark.asyncio
    async def test_no_subscriber_builds_nothing_on_any_radio_branch(
        self, fake_hass, keyfob, captures
    ):
        monitor, _, _ = _monitor(fake_hass)
        builders = [
            "rf_press_event", "rf_frame_event", "rf_static_summary_event",
            "rf_static_capture_event", "rx_event",
        ]
        with patch.multiple(candy_feed, **{b: MagicMock() for b in builders}) as built, \
                patch.object(monitor, "_candy_known") as known:
            await _hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
            await _hear(fake_hass, monitor, _one_frame_captures(keyfob), receiver=ATHOM_RX)
            await _flush_bursts(fake_hass, monitor, ATHOM_RX)
            await _hear(fake_hass, monitor, [STATIC_CAPTURE] * 3)
        assert not any(mock.called for mock in built.values())
        known.assert_not_called()
        fake_hass.loop.call_later.assert_not_called()
        assert monitor._candy_static_window == {} and monitor._candy_memo == {}


# ---------------------------------------------------------------------------
# The infrared ditto
# ---------------------------------------------------------------------------


def _nec(address: int = 0x04, command: int = 0x08) -> list[int]:
    timings = [9000, -4500]
    for byte in (address, address ^ 0xFF, command, command ^ 0xFF):
        for bit in range(8):
            timings += [560, -1690 if (byte >> bit) & 1 else -560]
    return [*timings, 560]


DITTO = [9000, -2250, 560]


class TestDitto:
    def _ir_monitor(self):
        from .test_signal_monitor import _make_hair_store, _make_hass, _make_signal_store

        hass = _make_hass()
        store = _make_signal_store(hass)
        hair = _make_hair_store()
        hair.get_triggers_for_signal = MagicMock(return_value=[])
        return SignalMonitor(hass, store, hair, MagicMock()), hass, hair

    @staticmethod
    def _received(timings):
        from .test_signal_monitor import _FakeReceivedSignal

        signal = _FakeReceivedSignal(timings=[], modulation=38000)
        signal.timings = list(timings)
        return signal

    async def _press(self, monitor, hass, timings, receiver=IR_RX):
        tasks = []
        hass.async_create_task = MagicMock(side_effect=tasks.append)
        monitor._on_received_signal(self._received(timings), receiver)
        while tasks:
            await tasks.pop(0)

    @pytest.mark.asyncio
    async def test_dittos_after_a_device_known_press_read_known(self):
        monitor, hass, hair = self._ir_monitor()
        device = types.SimpleNamespace(
            name="TV", get_command=lambda _cid: types.SimpleNamespace(name="Power")
        )
        hair.match_command.return_value = ("d1", "c1")
        hair.get_device.return_value = device
        events = _subscribe(monitor)
        await self._press(monitor, hass, _nec())
        await self._press(monitor, hass, DITTO)
        await self._press(monitor, hass, DITTO)
        assert [(e["ditto"], e["verdict"], e["known_from"]) for e in events] == [
            (False, "known", "device"), (True, "known", "device"), (True, "known", "device"),
        ]
        assert events[2]["known_name"] == "TV / Power"

    @pytest.mark.asyncio
    async def test_dittos_after_an_echoed_frame_read_echo(self):
        monitor, hass, _ = self._ir_monitor()
        events = _subscribe(monitor)
        echo = sm.EchoVerdict(candy_feed.ECHO_SEND, {"candy_seq": 4})
        with patch.object(monitor, "_match_echo", MagicMock(side_effect=lambda *_: _value(echo))):
            await self._press(monitor, hass, _nec())
        await self._press(monitor, hass, DITTO)
        assert (events[1]["verdict"], events[1]["known_from"]) == ("known", "echo")

    @pytest.mark.asyncio
    async def test_an_orphan_ditto_is_unknown(self):
        monitor, hass, _ = self._ir_monitor()
        events = _subscribe(monitor)
        await self._press(monitor, hass, DITTO)
        assert (events[0]["verdict"], events[0]["known_from"], events[0]["known_name"]) == (
            "unknown", None, None,
        )

    @pytest.mark.asyncio
    async def test_a_stale_memo_is_not_inherited(self, monkeypatch):
        monitor, hass, hair = self._ir_monitor()
        hair.match_command.return_value = ("d1", "c1")
        hair.get_device.return_value = types.SimpleNamespace(
            name="TV", get_command=lambda _cid: types.SimpleNamespace(name="Power")
        )
        events = _subscribe(monitor)
        clock = [1000.0]
        monkeypatch.setattr(sm.time, "monotonic", lambda: clock[0])
        await self._press(monitor, hass, _nec())
        clock[0] += sm.REPEAT_ATTRIBUTION_WINDOW + 0.1
        await self._press(monitor, hass, DITTO)
        assert events[-1]["verdict"] == "unknown"

    @pytest.mark.asyncio
    async def test_the_legacy_path_inherits(self):
        from .test_signal_monitor import _make_event

        monitor, _, hair = self._ir_monitor()
        hair.match_command.return_value = ("d1", "c1")
        hair.get_device.return_value = types.SimpleNamespace(
            name="TV", get_command=lambda _cid: types.SimpleNamespace(name="Power")
        )
        events = _subscribe(monitor)
        await monitor._on_ir_event(_make_event({"raw": _nec()}))
        await monitor._on_ir_event(_make_event({"protocol": "NEC", "raw": DITTO}))
        assert [e["ditto"] for e in events] == [False, True]
        assert (events[-1]["verdict"], events[-1]["known_from"]) == ("known", "device")

    @pytest.mark.asyncio
    async def test_a_ditto_while_its_frame_is_in_flight_is_an_orphan(self):
        """The sentinel write clears the memo: a ditto landing before its
        main frame has printed must not borrow the last press's verdict."""
        monitor, hass, hair = self._ir_monitor()
        hair.match_command.return_value = ("d1", "c1")
        hair.get_device.return_value = types.SimpleNamespace(
            name="TV", get_command=lambda _cid: types.SimpleNamespace(name="Power")
        )
        events = _subscribe(monitor)
        await self._press(monitor, hass, _nec())
        pending = []
        hass.async_create_task = MagicMock(side_effect=pending.append)
        monitor._on_received_signal(self._received(_nec(command=0x09)), IR_RX)
        monitor._on_received_signal(self._received(DITTO), IR_RX)
        assert events[-1]["ditto"] is True
        assert events[-1]["verdict"] == "unknown"
        for coro in pending:
            coro.close()

    @pytest.mark.asyncio
    async def test_no_subscriber_no_memo(self):
        monitor, hass, _ = self._ir_monitor()
        await self._press(monitor, hass, _nec())
        await self._press(monitor, hass, DITTO)
        assert monitor._candy_memo == {}


async def _value(value):
    return value
