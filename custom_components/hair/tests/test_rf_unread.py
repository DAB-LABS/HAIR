"""A radio code heard in an open window that HAIR can't read.

Nothing is kept of it: the receiver's row and push carry
``unread_radio``, the count for the current or last window, and the
panel says so. A code HAIR could read in the same window, a closed
window, short noise and a new window all keep it at 0.
"""
from __future__ import annotations

import base64
import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.rf_window import RfAlwaysOn, UnreadLedger
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_hear import (
    RECEIVER,
    _Modulation,
    _monitor,
    _state,
)

# One capture of a car fob's press, as a receiver window delivered it: a
# rolling word that differs on every press, so no two frames vote.
_FOB = (
    "eMDwAHjOBAAREAgIEQgIEQgIERAICQgICAgJCAgICAkQCQgQEAkIEAkIEAkICAgREAgIERAR"
    "CAgICQgICAkQCAgJCBARCAgREBEICBAREBEICAgJEBEQEAgJEBEICBAJCAgICQgQEQgICAkQ"
    "CAACqwQAA/EJEBAREBEQERAQCXMIEBEQERAREBAREBEQEQgIEQgIEAkIEBEICAkICAgICQgI"
    "CAgRCAgREAkHEQgJEAgICQgQEQgIERAQCAkICAkICAgRCAgICRAQCQgQEBEICRAQERAJCAgI"
    "ERAREAgIERAICRAICAkICAgREAkICAgRCAAF3A=="
)


def _fob_timings():
    raw = base64.b64decode(_FOB)
    data = raw[4:4 + (raw[2] | raw[3] << 8)]
    values, i = [], 0
    while i < len(data):
        if data[i] == 0 and i + 2 < len(data):
            values.append(data[i + 1] << 8 | data[i + 2])
            i += 3
        else:
            values.append(data[i])
            i += 1
    return [
        round(v * 1e6 / 32768) * (1 if k % 2 == 0 else -1)
        for k, v in enumerate(values)
    ]


async def _hear(fake_hass, monitor, capture, *, capturing=True):
    tasks = []
    fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
    fake_hass.states.get = MagicMock(return_value=_state(
        RECEIVER, capturing=capturing, capture_phase="listening" if capturing else None,
        frequency_hz=315_000_000,
    ))
    signal = types.SimpleNamespace(
        timings=list(capture), frequency=None, modulation=_Modulation.OOK,
    )
    with patch(
        "custom_components.hair.signal_monitor.time.time", return_value=1_000.0,
    ), patch(
        "custom_components.hair.signal_monitor.time.monotonic", return_value=1_000.0,
    ):
        monitor._on_rf_signal(signal, RECEIVER)
        while tasks:
            await tasks.pop(0)


def _windowed(fake_hass):
    # A capture that doesn't vote goes to the burst assembler, which
    # reads the loop's clock.
    fake_hass.loop = MagicMock()
    fake_hass.loop.time = MagicMock(return_value=1_000.0)
    monitor, store = _monitor(fake_hass)
    monitor._trigger_manager = None
    return monitor, store


class TestTheLedger:
    def test_it_counts_until_a_readable_code(self):
        ledger = UnreadLedger()
        assert ledger.unread("r") is True
        assert ledger.unread("r") is True
        assert ledger.count("r") == 2
        assert ledger.readable("r") is True
        assert ledger.count("r") == 0
        assert ledger.unread("r") is False  # still 0: the window read one

    def test_a_new_window_starts_again(self):
        ledger = UnreadLedger()
        ledger.readable("r")
        assert ledger.opened("r") is False
        ledger.unread("r")
        assert ledger.count("r") == 1
        assert ledger.opened("r") is True
        assert ledger.count("r") == 0

    def test_the_window_is_keyed_by_when_it_opened(self):
        from datetime import UTC, datetime

        opened = datetime(2026, 11, 21, 6, 0, tzinfo=UTC)
        ledger = UnreadLedger()
        ledger.opened("r", opened)
        assert ledger.fields("r") == {
            "unread_radio": 0, "unread_window_opened_at": None,
            "ambiguous_radio": 0, "ambiguous_window_opened_at": None,
        }
        ledger.unread("r")
        assert ledger.fields("r") == {
            "unread_radio": 1, "unread_window_opened_at": "2026-11-21T06:00:00.000+00:00",
            "ambiguous_radio": 0, "ambiguous_window_opened_at": None,
        }

    def test_receivers_are_apart(self):
        ledger = UnreadLedger()
        ledger.unread("a")
        ledger.readable("b")
        assert (ledger.count("a"), ledger.count("b")) == (1, 0)


@pytest.mark.asyncio
class TestAWindowedReceiver:
    async def test_the_fob_is_counted_and_nothing_is_filed(self, fake_hass):
        monitor, store = _windowed(fake_hass)
        await _hear(fake_hass, monitor, _fob_timings())
        assert monitor.rf_always_on.unread.count(RECEIVER) == 1
        assert store.get_all_devices() == []

    async def test_a_readable_press_in_the_same_window_wins(self, fake_hass):
        monitor, store = _windowed(fake_hass)
        await _hear(fake_hass, monitor, _fob_timings())
        await _hear(fake_hass, monitor, _pt_frame(0x95A3C6) * 4)
        assert monitor.rf_always_on.unread.count(RECEIVER) == 0
        assert len(store.get_all_devices()) == 1

    async def test_short_noise_is_not_counted(self, fake_hass):
        monitor, _store = _windowed(fake_hass)
        await _hear(fake_hass, monitor, [400, -400] * 6 + [400, -12000])
        assert monitor.rf_always_on.unread.count(RECEIVER) == 0

    async def test_a_closed_window_counts_nothing(self, fake_hass):
        monitor, _store = _windowed(fake_hass)
        await _hear(fake_hass, monitor, _fob_timings(), capturing=False)
        assert monitor.rf_always_on.unread.count(RECEIVER) == 0

    async def test_the_count_stays_after_the_window_closes_until_the_next_opens(
        self, fake_hass
    ):
        monitor, _store = _windowed(fake_hass)
        await _hear(fake_hass, monitor, _fob_timings())

        def change(old, new):
            monitor._on_receiver_availability_change(types.SimpleNamespace(data={
                "entity_id": RECEIVER,
                "old_state": _state(RECEIVER, capturing=old),
                "new_state": _state(RECEIVER, capturing=new),
            }))

        with patch.object(monitor, "_reconcile_receivers"):
            change(True, False)
            assert monitor.rf_always_on.unread.count(RECEIVER) == 1
            change(True, True)  # still open: not a new window
            assert monitor.rf_always_on.unread.count(RECEIVER) == 1
            change(False, True)
        assert monitor.rf_always_on.unread.count(RECEIVER) == 0


class TestASoftwareWindow:
    """An always-on receiver's window is HAIR's own: its push says it."""

    def _always_on(self):
        hass = MagicMock()
        hass.loop.call_later = MagicMock(return_value=MagicMock())
        always_on = RfAlwaysOn(hass)
        pushed = []
        always_on.subscribe(pushed.append)
        always_on.attach("radio_frequency.cc1101")
        return always_on, pushed

    def test_the_push_carries_the_count(self):
        always_on, pushed = self._always_on()
        always_on.window("radio_frequency.cc1101").open("multiple", 30)
        always_on.note_unread("radio_frequency.cc1101", readable=False)
        assert pushed[-1]["unread_radio"] == 1
        assert pushed[-1]["unread_window_opened_at"] is not None
        always_on.note_unread("radio_frequency.cc1101", readable=True)
        assert pushed[-1]["unread_radio"] == 0

    def test_a_new_window_starts_again_and_a_moved_end_does_not(self):
        always_on, pushed = self._always_on()
        window = always_on.window("radio_frequency.cc1101")
        window.open("sliding", 30)
        always_on.note_unread("radio_frequency.cc1101", readable=False)
        window.open("sliding", 30)  # restarting an open window moves its end
        assert pushed[-1]["unread_radio"] == 1
        window.close()
        assert pushed[-1]["unread_radio"] == 1
        window.open("sliding", 30)
        assert pushed[-1]["unread_radio"] == 0

    def test_the_row_carries_it(self):
        from custom_components.hair import receiver_window

        always_on, _pushed = self._always_on()
        always_on.window("radio_frequency.cc1101").open("multiple", 30)
        always_on.note_unread("radio_frequency.cc1101", readable=False)
        with patch(
            "custom_components.hair.rf_window.rf_always_on", return_value=always_on,
        ):
            assert receiver_window._unread(
                MagicMock(), "radio_frequency.cc1101"
            )["unread_radio"] == 1
            assert receiver_window._unread(MagicMock(), "infrared.tv") == {
                "unread_radio": 0, "unread_window_opened_at": None,
                "ambiguous_radio": 0, "ambiguous_window_opened_at": None,
            }
