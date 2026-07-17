"""Tests for the v0.5.5 ditto-count + capture-observation arc.

Covers:
- capture-side NEC ditto attribution (window gate, inter-frame gate, max-merge,
  sentinel drop, dismiss invalidation),
- the catalog Test path honoring repeat_count + send_count,
- _apply_signal_provenance carrying the knobs (incl. the Optional precedence),
- UnknownSignal round-trip / backward-compat for the three new fields,
- edit_signal_pronto preserving the knobs, and the edit-pronto WS accepting them.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.const import (
    DEFAULT_REPEAT_COUNT,
    DOMAIN,
    REPEAT_ATTRIBUTION_WINDOW,
)
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.signal_monitor import (
    SignalMonitor,
    _apply_signal_provenance,
)
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    ws_assign_signal,
    ws_unknown_signal_edit_pronto,
)

_PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
_PRONTO_B = "0000 006D 0002 0000 0030 0050 0030 0050"

_MONO = "custom_components.hair.signal_monitor.time.monotonic"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _monitor(fake_hass, *signals: UnknownSignal):
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
    for i, sig in enumerate(signals):
        store.add_device(
            UnknownDevice(
                id=f"ud{i}", fingerprint=f"d{i}", source="manual", signals=[sig]
            )
        )
    return monitor, store


def _sig(sig_id="s1", observed=0):
    return UnknownSignal(
        id=sig_id, fingerprint=sig_id, protocol="PRONTO", code=_PRONTO_A,
        observed_repeat_count=observed,
    )


def _decoded_sig(sig_id="s1", **overrides):
    fields = {
        "id": sig_id,
        "fingerprint": sig_id,
        "protocol": "PRONTO",
        "code": _PRONTO_A,
        "frequency": 38000,
        "decoded_protocol": "NEC",
        "decoded_address": 0x1000,
        "decoded_command": 0x18,
        "decoded_fingerprint": "NEC:0x1000:0x18",
    }
    fields.update(overrides)
    return UnknownSignal(**fields)


# v0.5.7: ditto-anchor state is per-receiver (dict keyed by receiver_entity_id,
# or the "__legacy__" sentinel for the ESPHome-bridge / no-receiver path). These
# capture-attribution tests exercise a single receiver, so they key everything on
# the legacy sentinel.
_RID = "__legacy__"


def _set_anchor(monitor, anchor, running=0, last=None):
    """Seed the per-receiver ditto state for the legacy sentinel receiver."""
    monitor._ditto_anchor = {_RID: anchor}
    monitor._ditto_running_count = {_RID: running}
    monitor._last_ditto_monotonic = {} if last is None else {_RID: last}


def _fire_ditto(monitor, now):
    with patch(_MONO, return_value=now):
        monitor._maybe_attribute_repeat_frame(_RID)


# ---------------------------------------------------------------------------
# Capture-side attribution
# ---------------------------------------------------------------------------


def test_ditto_attribution_within_window(fake_hass):
    sig = _sig("s1")
    monitor, _ = _monitor(fake_hass, sig)
    _set_anchor(monitor, ("s1", 0.0, "df"))
    _fire_ditto(monitor, 0.2)  # 200ms, inside the 1.0s window
    assert sig.observed_repeat_count == 1


def test_ditto_attribution_outside_window(fake_hass):
    sig = _sig("s1")
    monitor, _ = _monitor(fake_hass, sig)
    _set_anchor(monitor, ("s1", 0.0, "df"))
    # Past REPEAT_ATTRIBUTION_WINDOW (1.0s): the main-frame window gate refuses.
    _fire_ditto(monitor, REPEAT_ATTRIBUTION_WINDOW + 0.5)
    assert sig.observed_repeat_count == 0


def test_ditto_attribution_different_device(fake_hass):
    # Single-anchor: a ditto attributes to the most recent main frame (the
    # anchor). After remote B's main frame overwrites the anchor, A's signal
    # must not pick up B's dittos.
    sig_a = _sig("sA")
    sig_b = _sig("sB")
    monitor, _ = _monitor(fake_hass, sig_a, sig_b)
    _set_anchor(monitor, ("sB", 0.0, "dfB"))
    _fire_ditto(monitor, 0.1)
    assert sig_b.observed_repeat_count == 1
    assert sig_a.observed_repeat_count == 0


def test_ditto_max_merge(fake_hass):
    # An earlier hold observed 5; a later 2-ditto tap must not lower it.
    sig = _sig("s1", observed=5)
    monitor, _ = _monitor(fake_hass, sig)
    _set_anchor(monitor, ("s1", 0.0, "df"))
    _fire_ditto(monitor, 0.10)
    _fire_ditto(monitor, 0.21)
    assert sig.observed_repeat_count == 5


def test_ditto_inter_frame_gate_stops_burst(fake_hass):
    sig = _sig("s1")
    monitor, _ = _monitor(fake_hass, sig)
    _set_anchor(monitor, ("s1", 0.0, "df"))
    # 5 dittos at ~110ms intervals all attribute.
    for i in range(5):
        _fire_ditto(monitor, 0.05 + i * 0.11)
    assert sig.observed_repeat_count == 5
    # A short signal 400ms after the last ditto (> DITTO_INTER_FRAME_MAX_S):
    # the inter-frame gate refuses it; the count does not climb.
    _fire_ditto(monitor, 0.05 + 4 * 0.11 + 0.4)
    assert sig.observed_repeat_count == 5


def test_ditto_dropped_during_sentinel_window(fake_hass):
    sig = _sig("s1")
    monitor, _ = _monitor(fake_hass, sig)
    # Sentinel: main frame in flight, signal_id is None -> drop the ditto.
    _set_anchor(monitor, (None, 0.0, "df"))
    _fire_ditto(monitor, 0.1)
    assert sig.observed_repeat_count == 0
    # Pipeline confirms the anchor; subsequent dittos now attribute.
    _set_anchor(monitor, ("s1", 0.0, "df"))
    _fire_ditto(monitor, 0.2)
    assert sig.observed_repeat_count == 1


@pytest.mark.asyncio
async def test_dismiss_invalidates_anchor_no_inflation(fake_hass):
    from custom_components.hair.models import CaptureResult

    sig_n = _sig("sN")
    monitor, store = _monitor(fake_hass, sig_n)
    store.is_dismissed = MagicMock(return_value=True)  # dismissed remote D

    # D's main frame wrote a sentinel synchronously; the async pipeline's
    # dismiss early-return must invalidate it before any ditto attributes.
    _set_anchor(monitor, (None, 0.0, "dfD"))
    parsed = CaptureResult(
        protocol="PRONTO", code=_PRONTO_A,
        raw_timings=[560, -560, 560, -1690], frequency=38000,
    )
    await monitor._process_parsed_signal(parsed)
    assert monitor._ditto_anchor.get(_RID) is None

    # D's dittos drop (anchor is None).
    _fire_ditto(monitor, 0.1)
    assert sig_n.observed_repeat_count == 0

    # N's main frame sets a fresh confirmed anchor; its dittos attribute to N.
    _set_anchor(monitor, ("sN", 1.0, "dfN"))
    _fire_ditto(monitor, 1.1)
    assert sig_n.observed_repeat_count == 1


# ---------------------------------------------------------------------------
# Catalog Test path honors the knobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_signal_honors_repeat_count(fake_hass):
    sig = _decoded_sig("s1", repeat_count=3)
    monitor, _ = _monitor(fake_hass, sig)
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()),
        patch(
            "custom_components.hair.ir_command.build_decoded_command",
            return_value=object(),
        ) as bdc,
        patch("custom_components.hair.ir_command.build_command"),
    ):
        res = await monitor.test_signal("s1", "infrared.e")
    assert res["success"]
    bdc.assert_called_once_with(
        "NEC", 0x1000, 0x18, repeat_count=3, decoded_extras=None
    )


@pytest.mark.asyncio
async def test_test_signal_honors_send_count(fake_hass):
    sig = _decoded_sig("s1", send_count=4)
    monitor, _ = _monitor(fake_hass, sig)
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch(
            "custom_components.hair.ir_command.build_decoded_command",
            return_value=object(),
        ),
        patch("custom_components.hair.ir_command.build_command"),
        patch(
            "custom_components.hair.signal_monitor.asyncio.sleep", AsyncMock()
        ) as sleep_mock,
    ):
        res = await monitor.test_signal("s1", "infrared.e")
    assert res["success"]
    assert ir_send.await_count == 4
    assert sleep_mock.await_count == 3  # gap between the four frames


@pytest.mark.asyncio
async def test_test_signal_composes_repeat_and_send(fake_hass):
    sig = _decoded_sig("s1", repeat_count=5, send_count=3)
    monitor, _ = _monitor(fake_hass, sig)
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch(
            "custom_components.hair.ir_command.build_decoded_command",
            return_value=object(),
        ) as bdc,
        patch("custom_components.hair.ir_command.build_command"),
        patch("custom_components.hair.signal_monitor.asyncio.sleep", AsyncMock()),
    ):
        res = await monitor.test_signal("s1", "infrared.e")
    assert res["success"]
    bdc.assert_called_once_with(
        "NEC", 0x1000, 0x18, repeat_count=5, decoded_extras=None
    )
    assert ir_send.await_count == 3


@pytest.mark.asyncio
async def test_test_signal_raw_fallback_honors_repeat_count(fake_hass):
    # No decoded identity -> the raw build path; it still honors both knobs.
    sig = UnknownSignal(
        id="s1", fingerprint="s1", protocol="PRONTO", code=_PRONTO_A,
        frequency=38000, repeat_count=4, send_count=2,
    )
    monitor, _ = _monitor(fake_hass, sig)
    with (
        patch.object(_infrared_mod, "async_send_command", AsyncMock()) as ir_send,
        patch("custom_components.hair.ir_command.build_decoded_command") as bdc,
        patch(
            "custom_components.hair.ir_command.build_command",
            return_value=object(),
        ) as bc,
        patch("custom_components.hair.signal_monitor.asyncio.sleep", AsyncMock()),
    ):
        res = await monitor.test_signal("s1", "infrared.e")
    assert res["success"]
    bdc.assert_not_called()
    assert bc.call_args.kwargs["repeat_count"] == 4
    assert ir_send.await_count == 2


# ---------------------------------------------------------------------------
# _apply_signal_provenance carries the knobs (Optional precedence)
# ---------------------------------------------------------------------------


def test_apply_signal_provenance_carries_repeat_and_send():
    sig = UnknownSignal(id="s1", fingerprint="s1", repeat_count=7, send_count=4)
    cmd = IRCommand(name="X")
    _apply_signal_provenance(cmd, sig, send_count=None)
    assert cmd.repeat_count == 7
    assert cmd.send_count == 4  # None -> falls back to signal.send_count


def test_apply_signal_provenance_precedence():
    sig = UnknownSignal(id="s1", fingerprint="s1", send_count=5)
    # Explicit WS arg wins, even when it equals 1.
    cmd1 = IRCommand(name="A")
    _apply_signal_provenance(cmd1, sig, send_count=3)
    assert cmd1.send_count == 3
    # No WS arg (None) -> signal-side fallback.
    cmd2 = IRCommand(name="B")
    _apply_signal_provenance(cmd2, sig, send_count=None)
    assert cmd2.send_count == 5


# ---------------------------------------------------------------------------
# Storage round-trip + backward compat
# ---------------------------------------------------------------------------


def test_signal_round_trip_carries_new_fields():
    sig = UnknownSignal(
        id="s1", fingerprint="s1", repeat_count=8, send_count=3,
        observed_repeat_count=6,
    )
    sig2 = UnknownSignal.from_dict(sig.to_dict())
    assert sig2.repeat_count == 8
    assert sig2.send_count == 3
    assert sig2.observed_repeat_count == 6


def test_signal_missing_fields_uses_defaults():
    sig = UnknownSignal.from_dict({"id": "s1", "fingerprint": "s1"})
    assert sig.repeat_count == DEFAULT_REPEAT_COUNT
    assert sig.send_count == 1
    assert sig.observed_repeat_count == 0


def test_signal_backward_compat_load():
    # A dict matching the v0.5.1 schema (no new fields).
    v051 = {
        "id": "s1", "fingerprint": "fp", "byte_hash": "bh", "protocol": "PRONTO",
        "code": _PRONTO_A, "raw_timings": [], "frequency": 38000, "hit_count": 2,
        "source": "sniffed", "alias": "",
    }
    sig = UnknownSignal.from_dict(v051)
    assert sig.repeat_count == DEFAULT_REPEAT_COUNT
    assert sig.send_count == 1
    assert sig.observed_repeat_count == 0


# ---------------------------------------------------------------------------
# edit_signal_pronto preservation + WS acceptance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_signal_pronto_preserves_tx_knobs(fake_hass):
    sig = UnknownSignal(
        id="s1", fingerprint="s1", protocol="PRONTO", code=_PRONTO_A,
        repeat_count=3, send_count=2, observed_repeat_count=8,
    )
    monitor, _ = _monitor(fake_hass, sig)
    # Edit the code with no explicit knob args -> the re-derivation preserves
    # the user's tunings and the observation.
    res = await monitor.edit_signal_pronto("ud0", "s1", _PRONTO_B)
    assert res["success"]
    assert sig.repeat_count == 3
    assert sig.send_count == 2
    assert sig.observed_repeat_count == 8


@pytest.mark.asyncio
async def test_signal_edit_ws_accepts_repeat_and_send(fake_hass):
    sig = UnknownSignal(
        id="s1", fingerprint="s1", protocol="PRONTO", code=_PRONTO_A,
        repeat_count=1, send_count=1,
    )
    monitor, _ = _monitor(fake_hass, sig)
    fake_hass.data[DOMAIN] = {
        "e1": {
            "signal_monitor": monitor,
            "device_manager": MagicMock(),
            "orchestrator": MagicMock(),
        }
    }
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    await ws_unknown_signal_edit_pronto(
        fake_hass,
        conn,
        {
            "id": 1,
            "type": "hair/unknown/signal/edit-pronto",
            "device_id": "ud0",
            "signal_id": "s1",
            "pronto": _PRONTO_B,
            "repeat_count": 6,
            "send_count": 3,
        },
    )
    conn.send_error.assert_not_called()
    assert sig.repeat_count == 6
    assert sig.send_count == 3


# ---------------------------------------------------------------------------
# Assign-path repeat_count precedence + WS carriage (v0.5.5 follow-up)
# ---------------------------------------------------------------------------


def test_apply_signal_provenance_repeat_count_precedence():
    sig = UnknownSignal(id="s1", fingerprint="s1", repeat_count=8)
    # Explicit WS arg wins.
    cmd1 = IRCommand(name="A")
    _apply_signal_provenance(cmd1, sig, repeat_count=3)
    assert cmd1.repeat_count == 3
    # No WS arg (None) -> signal-side fallback.
    cmd2 = IRCommand(name="B")
    _apply_signal_provenance(cmd2, sig, repeat_count=None)
    assert cmd2.repeat_count == 8
    # Explicit 0 is valid ("no dittos") and must win over the fallback -- the
    # Optional sentinel handles it where a truthy fallback would not.
    cmd3 = IRCommand(name="C")
    _apply_signal_provenance(cmd3, sig, repeat_count=0)
    assert cmd3.repeat_count == 0


@pytest.mark.asyncio
async def test_assign_signal_ws_carries_repeat_count(fake_hass):
    sig1 = _decoded_sig("s1", repeat_count=2)
    sig2 = _decoded_sig(
        "s2", repeat_count=2, code=_PRONTO_B,
        decoded_fingerprint="NEC:0x1000:0x19",
    )
    store = SignalStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    store.schedule_save = MagicMock()
    hair_device = IRDevice(id="hd1", name="TV")
    hair_store = MagicMock()
    hair_store.get_device = MagicMock(return_value=hair_device)
    hair_store.async_save = AsyncMock()
    hair_store.match_command = MagicMock(return_value=None)
    monitor = SignalMonitor(fake_hass, store, hair_store)
    store.add_device(
        UnknownDevice(
            id="ud0", fingerprint="d0", source="manual", signals=[sig1, sig2]
        )
    )
    dm = MagicMock()
    dm.async_apply_auto_map = AsyncMock()
    fake_hass.data[DOMAIN] = {
        "e1": {
            "signal_monitor": monitor,
            "device_manager": dm,
            "orchestrator": MagicMock(),
        }
    }
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()

    # Explicit repeat_count=5 overrides signal.repeat_count=2.
    await ws_assign_signal(
        fake_hass,
        conn,
        {
            "id": 1, "type": "hair/unknown/assign", "device_id": "ud0",
            "signal_id": "s1", "hair_device_id": "hd1", "command_name": "Power",
            "repeat_count": 5,
        },
    )
    conn.send_error.assert_not_called()
    assert hair_device.commands[0].repeat_count == 5

    # No repeat_count in the payload -> signal-side fallback (2).
    await ws_assign_signal(
        fake_hass,
        conn,
        {
            "id": 2, "type": "hair/unknown/assign", "device_id": "ud0",
            "signal_id": "s2", "hair_device_id": "hd1", "command_name": "Mute",
        },
    )
    conn.send_error.assert_not_called()
    assert hair_device.commands[1].repeat_count == 2


@pytest.mark.asyncio
async def test_assign_to_new_device_ws_carries_repeat_count(fake_hass):
    # Driven at the assign_to_new_device method level: the WS handler forwards
    # repeat_count=msg.get("repeat_count") identically to assign_signal (which
    # the WS-level test above covers), then creates HA entities -- out of scope
    # for this carriage assertion.
    sig = _decoded_sig("s1", repeat_count=2)
    monitor, _ = _monitor(fake_hass, sig)

    # Explicit override.
    res = await monitor.assign_to_new_device(
        device_id="ud0", signal_id="s1", device_name="TV",
        device_type="media_player", emitter_entity_ids=["infrared.e"],
        command_name="Power", command_category="custom", repeat_count=5,
    )
    assert res["success"]
    assert res["device"].commands[0].repeat_count == 5

    # Fallback to the signal-side value when not passed.
    res2 = await monitor.assign_to_new_device(
        device_id="ud0", signal_id="s1", device_name="TV2",
        device_type="media_player", emitter_entity_ids=["infrared.e"],
        command_name="Power", command_category="custom",
    )
    assert res2["success"]
    assert res2["device"].commands[0].repeat_count == 2
