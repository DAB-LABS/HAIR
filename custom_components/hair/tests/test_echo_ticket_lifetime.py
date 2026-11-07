"""An echo ticket lives as long as its own windows say.

A ticket's ``expires`` and ``garble_expires`` are widened by the send's
own length (send spacing, GH #151), but the cleanup that deletes it used
to fire at a fixed 3.0 s. A long bundled send then lost its widened
window at 3.0 s, and an echo arriving after that read as a stranger's
press (GH #237 note, section 6).

These tests run the monitor on a fake clock and a fake loop, so what is
pinned is the ticket's LIFETIME, not the values of its fields.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.ir_command import RawTimingsCommand, raw_to_pronto
from custom_components.hair.models import CaptureResult
from custom_components.hair.signal_monitor import SignalMonitor

from .test_signal_monitor import _make_hair_store, _make_hass, _make_signal_store

RX = "infrared.athom_rx"
FRAME = [4000, -2000, 4000]


class _Clock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t


class _Loop:
    """``call_later`` on the fake clock; ``advance`` runs what fell due."""

    def __init__(self, clock: _Clock) -> None:
        self._clock = clock
        self._timers: list[list] = []

    def call_later(self, delay, callback, *args):
        timer = [self._clock.t + delay, callback, args, False]
        self._timers.append(timer)
        handle = MagicMock()
        handle.cancel = lambda: timer.__setitem__(3, True)
        return handle

    def advance(self, to: float) -> None:
        self._clock.t = to
        for timer in sorted(self._timers, key=lambda t: t[0]):
            due, callback, args, cancelled = timer
            if due <= to and not cancelled:
                timer[3] = True
                callback(*args)


def _capture() -> CaptureResult:
    return CaptureResult(
        protocol="PRONTO",
        code=raw_to_pronto(list(FRAME), frequency=38000),
        raw_timings=list(FRAME),
        frequency=38000,
    )


@pytest.fixture
def rig():
    clock = _Clock()
    hass = _make_hass()
    loop = _Loop(clock)
    hass.loop = loop
    trigger_manager = MagicMock()
    monitor = SignalMonitor(
        hass, _make_signal_store(hass), _make_hair_store(), trigger_manager
    )
    with patch("custom_components.hair.signal_monitor.monotonic", clock):
        yield monitor, trigger_manager, clock, loop


def _send(monitor, clock, *, air_s: float):
    monitor.record_send(
        RawTimingsCommand(FRAME), "Amplifier / Power", [RX],
        send_count=1, air_s=air_s, burst=None,
    )
    exp = monitor._echo_expectations[-1]
    monitor._arm_expectation(exp, clock.t)
    return exp


class TestTheLifetime:
    @pytest.mark.asyncio
    async def test_a_widened_ticket_still_claims_its_echo_after_three_seconds(
        self, rig
    ):
        monitor, tm, clock, loop = rig
        exp = _send(monitor, clock, air_s=2.0)
        # The send keeps the air for 2 s, so the ticket's own window runs
        # to 2.5 + 2.0 + the margin past the send.
        assert exp["expires"] - 1000.0 > 4.0
        # Past the old fixed cleanup and past the guard, inside expires.
        loop.advance(1000.0 + 4.0)
        assert exp in monitor._echo_expectations
        await monitor._process_parsed_signal(_capture(), receiver_entity_id=RX)
        tm.on_signal_captured.assert_not_called()

    @pytest.mark.asyncio
    async def test_the_ticket_is_gone_once_its_own_windows_close(self, rig):
        monitor, _, clock, loop = rig
        exp = _send(monitor, clock, air_s=2.0)
        loop.advance(max(exp["expires"], exp["garble_expires"]) + 0.01)
        assert exp not in monitor._echo_expectations

    @pytest.mark.asyncio
    async def test_never_deleted_before_either_window(self, rig):
        monitor, _, clock, loop = rig
        exp = _send(monitor, clock, air_s=2.0)
        loop.advance(max(exp["expires"], exp["garble_expires"]) - 0.01)
        assert exp in monitor._echo_expectations

    @pytest.mark.asyncio
    async def test_a_short_send_still_dies_within_seconds(self, rig):
        monitor, _, clock, loop = rig
        exp = _send(monitor, clock, air_s=0.06)
        loop.advance(1000.0 + 4.0)
        assert exp not in monitor._echo_expectations
