"""Send review test gap 8: the Mirror's band through the doors.

The Mirror tab lists the echo remote with ``hair/unknown/devices``
(``source: "echo"``) and reads its rows with ``hair/unknown/device``.
A radio echo row must arrive there with ``medium: "rf"`` and its
``rf_frequency_hz``, for HAIR's own send (the stored row's carrier) and
for a foreign send heard back (the carrier it was heard at), not only on
the in-memory row.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from custom_components.hair import rf_frames
from custom_components.hair.const import DOMAIN, MEDIUM_RF, RF_PROTOCOL
from custom_components.hair.models import CaptureResult
from custom_components.hair.signal_monitor import _normalize_rf
from custom_components.hair.tests.test_rf_hear import (
    FIXTURE,
    _monitor,
    _rf_signal,
    _signed,
)
from custom_components.hair.tests.test_websocket_api import _make_connection
from custom_components.hair.websocket_api import (
    ws_get_unknown_device,
    ws_get_unknown_devices,
)


@pytest.fixture(scope="module")
def captures():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["captures"]


def _heard(pulses, frequency_hz):
    analysis = rf_frames.analyze(_signed(pulses))
    parsed = CaptureResult(
        protocol=RF_PROTOCOL, code=None, raw_timings=list(analysis.frame),
        medium=MEDIUM_RF,
    )
    parsed.rf_frequency_hz = frequency_hz
    parsed.rf = analysis
    return analysis, _normalize_rf(parsed)


async def _mirror_rows(fake_hass, monitor):
    fake_hass.data[DOMAIN] = {
        "entry-1": {"device_manager": MagicMock(), "signal_monitor": monitor}
    }
    conn = _make_connection()
    await ws_get_unknown_devices(
        fake_hass, conn,
        {"id": 1, "type": "hair/unknown/devices", "source": "echo", "min_hits": 0},
    )
    listed = conn.send_result.call_args[0][1]
    assert len(listed) == 1
    conn = _make_connection()
    await ws_get_unknown_device(
        fake_hass, conn,
        {"id": 2, "type": "hair/unknown/device", "device_id": listed[0]["id"]},
    )
    # The door's answer as the panel receives it: through JSON.
    return json.loads(json.dumps(conn.send_result.call_args[0][1]))["signals"]


@pytest.mark.asyncio
async def test_hairs_own_radio_send_carries_its_stored_carrier(fake_hass, captures):
    monitor, _store = _monitor(fake_hass)
    analysis, n = _heard(captures[0]["pulses"], 433_840_000)
    sent = _rf_signal(analysis, rf_frequency_hz=315_000_000)
    await monitor._mirror_upsert(
        n, decoded_fp=None, echo_source="Plug / Button 1 on -- via Athom",
        reset_heard=True, rf_fields=sent,
    )
    rows = await _mirror_rows(fake_hass, monitor)
    assert [(r["medium"], r["rf_frequency_hz"]) for r in rows] == [
        (MEDIUM_RF, 315_000_000)
    ]
    assert rows[0]["echo_source"] == "Plug / Button 1 on -- via Athom"


@pytest.mark.asyncio
async def test_a_foreign_radio_send_carries_the_carrier_it_was_heard_at(
    fake_hass, captures
):
    monitor, _store = _monitor(fake_hass)
    _analysis, n = _heard(captures[0]["pulses"], 433_920_000)
    await monitor._mirror_upsert(
        n, decoded_fp=None, echo_source="Unknown send", reset_heard=False
    )
    rows = await _mirror_rows(fake_hass, monitor)
    assert [(r["medium"], r["rf_frequency_hz"]) for r in rows] == [
        (MEDIUM_RF, 433_920_000)
    ]
