"""An edit is not a press (owner, 2026-11-08).

Editing a Sniffer row, radio or infrared, its code, frequency, alias or
send count, leaves the row's last seen alone, so the "last seen" column
and the remote's band (the carrier of the most recently heard row) stay
where the air left them.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.models import UnknownDevice
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.tests.test_rf_paste import (
    BUTTON_A,
    BUTTON_B,
    IT104_B64,
    _frame,
    _rf_row,
)
from custom_components.hair.tests.test_signal_monitor import (
    _make_hair_store,
    _make_hass,
    _make_signal_store,
)
from custom_components.hair.tests.test_websocket_api import _make_signal_monitor
from custom_components.hair.websocket_api import _unknown_device_medium

HEARD = "2026-11-07T17:00:00+00:00"
EARLIER = "2026-11-06T17:00:00+00:00"


def _rf_monitor(fake_hass, rows):
    monitor = _make_signal_monitor(fake_hass)
    device = UnknownDevice(id="r1", fingerprint="fp", signals=rows, medium="rf")
    device.last_seen = HEARD
    monitor._signal_store.add_device(device)
    monitor._signal_store.async_save = AsyncMock()
    monitor._trigger_manager = MagicMock()
    monitor._trigger_manager.rewire = AsyncMock(return_value={"rewired": [], "skipped": []})
    return monitor, device


def _heard(signal_id, bits, frequency_hz, last_seen):
    row = _rf_row(signal_id, bits)
    row.rf_frequency_hz = frequency_hz
    row.last_seen = last_seen
    return row


@pytest.mark.parametrize(
    "edit",
    [
        {"rf_frequency_hz": 315_000_000},
        {"rf_code": IT104_B64},
        {"rf_code": " ".join(map(str, _frame(BUTTON_B) * 3))},
        {"alias": "All off"},
        {"send_count": 6},
    ],
    ids=["frequency", "paste", "timings", "alias", "count"],
)
@pytest.mark.asyncio
async def test_a_radio_edit_leaves_last_seen(fake_hass, edit):
    monitor, device = _rf_monitor(fake_hass, [_heard("s1", BUTTON_A, 433_920_000, EARLIER)])
    result = await monitor.edit_signal_rf("r1", "s1", **edit)
    assert result["success"] is True
    assert (device.signals[0].last_seen, device.last_seen) == (EARLIER, HEARD)


@pytest.mark.asyncio
async def test_the_remote_band_stays_with_the_last_row_heard(fake_hass):
    """N15's neighbor: editing an older row's band does not make it the
    remote's band."""
    on = _heard("on", BUTTON_A, 433_920_000, HEARD)
    off = _heard("off", BUTTON_B, 433_920_000, EARLIER)
    monitor, device = _rf_monitor(fake_hass, [on, off])
    await monitor.edit_signal_rf("r1", "off", rf_frequency_hz=315_000_000)
    assert off.rf_frequency_hz == 315_000_000
    assert _unknown_device_medium(device)["rf_frequency_hz"] == 433_920_000


@pytest.mark.asyncio
async def test_an_infrared_edit_leaves_last_seen():
    hass = _make_hass()
    store = _make_signal_store(hass)
    monitor = SignalMonitor(hass, store, _make_hair_store())
    with patch.object(store, "async_save", AsyncMock()):
        device = await monitor.create_manual_remote("R")
        created = await monitor.create_manual_signal(
            device.id, "0000 006D 0002 0000 0010 0010 0010 0010"
        )
        sig = device.get_signal_by_id(created["signal"]["id"])
        sig.last_seen = EARLIER
        res = await monitor.edit_signal_pronto(
            device.id, sig.id, "0000 006D 0002 0000 0010 0040 0010 0010", alias="Power"
        )
    assert res["success"] is True
    assert (sig.alias, sig.last_seen) == ("Power", EARLIER)
