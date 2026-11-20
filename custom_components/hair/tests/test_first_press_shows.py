"""A new remote is listed in the Sniffer on its first press.

A code only reaches the catalog through a capture window, or by matching a
row already there, so the first press is the user's own and the card shows
at once. The door's ``min_hits`` still filters for a caller that asks.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_hear import (
    RECEIVER,
    _Modulation,
    _monitor,
    _state,
)


async def _press(fake_hass, monitor, capture):
    tasks = []
    fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
    fake_hass.states.get = MagicMock(return_value=_state(
        RECEIVER, capturing=True, capture_phase="listening",
        frequency_hz=433_920_000,
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


@pytest.mark.asyncio
class TestTheFirstPress:
    async def test_one_press_lists_the_card(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        monitor._trigger_manager = None
        await _press(fake_hass, monitor, _pt_frame(0x95A3C6) * 4)
        (device,) = store.get_all_devices()
        assert device.hit_count == 1
        listed = monitor.get_unknown_devices(source="sniffed")
        assert [d.id for d in listed] == [device.id]

    async def test_an_explicit_minimum_still_hides_it(self, fake_hass):
        monitor, _store = _monitor(fake_hass)
        monitor._trigger_manager = None
        await _press(fake_hass, monitor, _pt_frame(0x95A3C6) * 4)
        assert monitor.get_unknown_devices(min_hits=3, source="sniffed") == []
