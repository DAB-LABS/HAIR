"""The Candy Drawer's feed: every frame heard and every send made, raw.

What is pinned here:

- the four event shapes (a received frame, a repeat frame, a send, an
  echo of that send) as the monitor builds them;
- where the received frames come from: the native and the legacy entry
  points for repeat frames, and ``_process_parsed_signal`` after the echo
  claim for everything else, before the dismiss list, the rate limit and
  repeat suppression can hide anything;
- the echo verdict carrying the send's sequence number, and the three
  other echo kinds;
- nothing is built while nobody is subscribed, unsubscribing stops the
  stream, and the Sniffer's store and the Mirror come out byte for byte
  the same with the drawer open or closed;
- the WebSocket command: admin only, per connection, unsubscribed when
  the connection closes.
"""
from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import candy_feed
from custom_components.hair import signal_monitor as sm
from custom_components.hair.const import LEGACY_ESPHOME_IR_EVENT
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.websocket_api import ws_subscribe_candy

from .test_signal_monitor import (
    _FakeReceivedSignal,
    _make_event,
    _make_hair_store,
    _make_hass,
    _make_signal_store,
    _run_native_signal,
)

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None
_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY, reason="decoding NEC needs infrared_protocols"
)

RECEIVER = "infrared.living_ir"
EMITTER = "infrared.rm4_living"


def _nec(address: int = 0x04, command: int = 0x08) -> list[int]:
    """One NEC frame, as a receiver hands it over."""
    timings = [9000, -4500]
    for byte in (address, address ^ 0xFF, command, command ^ 0xFF):
        for bit in range(8):
            timings += [560, -1690 if (byte >> bit) & 1 else -560]
    return [*timings, 560]


DITTO = [9000, -2250, 560]


def _monitor():
    hass = _make_hass()
    store = _make_signal_store(hass)
    monitor = SignalMonitor(hass, store, _make_hair_store(), MagicMock())
    return monitor, hass, store


def _subscribe(monitor) -> list[dict]:
    events: list[dict] = []
    monitor.candy_subscribe(events.append)
    return events


def _received(timings: list[int]) -> _FakeReceivedSignal:
    signal = _FakeReceivedSignal(timings=[], modulation=38000)
    signal.timings = list(timings)
    return signal


def _beacon(entity_id: str = EMITTER):
    """The state write core makes when a platform send returns."""
    attrs = {"device_class": "emitter", "friendly_name": "RM4 living"}
    return SimpleNamespace(
        data={
            "entity_id": entity_id,
            "new_state": SimpleNamespace(state="2026-10-30T12:04:33", attributes=attrs),
            "old_state": SimpleNamespace(state="2026-10-30T12:00:00", attributes=attrs),
        },
        context=SimpleNamespace(parent_id=None),
    )


def _normalized(timings: list[int]):
    parsed = sm.EventParser.parse_received_signal(_received(timings))
    return parsed, sm.normalize(parsed)


def _send(monitor, timings: list[int], label: str = "TV / Power", **kwargs):
    """HAIR sends ``timings`` through the RM4 (the Command is stubbed by
    its normalized form, as the Mirror suite does)."""
    _, n = _normalized(timings)
    monitor._hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
    with patch.object(sm, "normalize_command", lambda _c: n):
        monitor.record_send(object(), label, [EMITTER], send_count=2, **kwargs)
    monitor._hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    return n


RX_KEYS = {
    "ts", "dir", "entity_id", "name", "protocol", "address", "command",
    "fingerprint", "covers", "carrier_hz", "frames", "pronto", "raw",
    "ditto", "echo", "echo_of", "echo_via",
}
TX_KEYS = {
    "ts", "dir", "seq", "emitters", "label", "device", "command_name",
    "sends", "origin", "protocol", "address", "command", "fingerprint",
    "covers", "carrier_hz", "frames", "pronto", "raw",
}


# --- the pure builders ----------------------------------------------------


class TestBuilders:
    def test_frames_split_at_eight_milliseconds(self):
        frame = _nec()
        assert candy_feed.frame_count(frame) == 1
        assert candy_feed.frame_count([*frame, -40000, *frame, -40000, *DITTO]) == 3
        # A header space of 4.5 ms never splits a frame.
        assert candy_feed.frame_count([9000, -4500, 560, -7999, 560]) == 1
        assert candy_feed.frame_count([]) == 0

    def test_no_decode_leaves_every_decode_field_empty(self):
        n = SimpleNamespace(decoded_protocol=None, decoded_address=None,
                            decoded_command=None)
        assert candy_feed.decode_fields(n) == {
            "protocol": None, "address": None, "command": None,
            "fingerprint": None, "covers": None,
        }

    def test_hex_comes_from_the_fingerprint_formatter(self):
        n = SimpleNamespace(
            decoded_protocol="NEC", decoded_address=0x04, decoded_command=0x08,
            decoded_fingerprint=None, decoded_extras=None, decode_covers=False,
        )
        fields = candy_feed.decode_fields(n)
        assert fields == {
            "protocol": "NEC", "address": "0x0004", "command": "0x08",
            "fingerprint": "NEC:0x0004:0x08", "covers": False,
        }

    def test_events_are_plain_json(self):
        _, n = _normalized(_nec())
        for event in (
            candy_feed.rx_event(ts=1.5, entity_id=RECEIVER, name="Living", n=n),
            candy_feed.ditto_event(ts=1.6, entity_id=RECEIVER, name="Living",
                                   raw=DITTO, carrier_hz=38000),
            candy_feed.tx_event(ts=1.7, seq=1, n=n, emitters=[], label="x",
                                device=None, command_name=None, sends=0,
                                origin=None),
        ):
            assert json.loads(json.dumps(event)) == event


# --- the four shapes from the monitor ---------------------------------------


class TestShapes:
    @pytest.mark.asyncio
    async def test_a_received_frame(self):
        monitor, hass, _ = _monitor()
        events = _subscribe(monitor)
        await _run_native_signal(monitor, hass, _received(_nec()))
        assert len(events) == 1
        rx = events[0]
        assert set(rx) == RX_KEYS
        assert rx["dir"] == "rx"
        assert rx["entity_id"] is None  # _run_native_signal passes no receiver
        assert rx["raw"] == _nec()
        assert rx["frames"] == 1
        assert rx["carrier_hz"] == 38000
        assert rx["pronto"].startswith("0000 ")
        assert rx["ditto"] is False
        assert rx["echo"] is None and rx["echo_of"] is None

    @_needs_library
    @pytest.mark.asyncio
    async def test_a_received_frame_carries_its_decode(self):
        monitor, hass, _ = _monitor()
        events = _subscribe(monitor)
        await _run_native_signal(monitor, hass, _received(_nec()))
        rx = events[0]
        assert rx["protocol"] == "NEC"
        assert rx["command"] == "0x08"
        assert rx["fingerprint"] == f"NEC:{rx['address']}:0x08"

    @pytest.mark.asyncio
    async def test_a_repeat_frame_prints_before_it_is_folded(self):
        monitor, hass, _ = _monitor()
        events = _subscribe(monitor)
        monitor._on_received_signal(_received(DITTO), RECEIVER)
        assert len(events) == 1
        ditto = events[0]
        assert set(ditto) == RX_KEYS
        assert ditto["ditto"] is True
        assert ditto["raw"] == DITTO
        assert ditto["entity_id"] == RECEIVER
        assert ditto["protocol"] is None
        # Nothing was scheduled for the Sniffer: a ditto never was.
        hass.async_create_task.assert_not_called()

    def test_a_send(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        _send(monitor, _nec(), device_name="TV", command_name="Power",
              origin="manager")
        assert len(events) == 1
        tx = events[0]
        assert set(tx) == TX_KEYS
        assert tx["dir"] == "tx"
        assert tx["seq"] == 1
        assert tx["sends"] == 2
        assert tx["label"] == "TV / Power"
        assert (tx["device"], tx["command_name"], tx["origin"]) == (
            "TV", "Power", "manager",
        )
        assert [e["entity_id"] for e in tx["emitters"]] == [EMITTER]
        assert tx["raw"] == _nec()
        assert monitor._echo_expectations[0]["candy_seq"] == 1

    @pytest.mark.asyncio
    async def test_the_echo_names_its_send(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        _send(monitor, _nec())
        _send(monitor, _nec(0x10, 0x20), label="Amp / Mute")
        monitor._on_emitter_beacon(_beacon())
        parsed, _ = _normalized(_nec())
        await monitor._process_parsed_signal(parsed, RECEIVER, arrived_at=12.5)
        rx = events[-1]
        assert rx["dir"] == "rx"
        assert rx["echo"] == candy_feed.ECHO_SEND
        assert rx["echo_of"] == 1
        assert rx["ts"] == 12.5
        # The claimed echo still never reached the triggers.
        monitor._trigger_manager.on_signal_captured.assert_not_called()


# --- where frames are printed -----------------------------------------------


class TestEntryPoints:
    @pytest.mark.asyncio
    async def test_five_presses_print_five_blocks_while_the_sniffer_counts(self):
        """Repeat suppression folds presses on the Sniffer; the drawer
        prints each one."""
        monitor, hass, store = _monitor()
        events = _subscribe(monitor)
        for _ in range(5):
            await _run_native_signal(monitor, hass, _received(_nec()))
        assert len(events) == 5
        assert store.device_count == 1

    @pytest.mark.asyncio
    async def test_a_dismissed_remote_still_prints(self):
        monitor, hass, store = _monitor()
        events = _subscribe(monitor)
        store.is_dismissed = MagicMock(return_value=True)
        await _run_native_signal(monitor, hass, _received(_nec()))
        assert len(events) == 1
        assert store.device_count == 0

    @pytest.mark.asyncio
    async def test_the_legacy_path_prints_frames_and_repeats(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        await monitor._on_ir_event(_make_event({"raw": _nec()}))
        await monitor._on_ir_event(_make_event({"protocol": "NEC", "raw": DITTO}))
        assert [e["ditto"] for e in events] == [False, True]
        assert all(e["name"] == LEGACY_ESPHOME_IR_EVENT for e in events)
        assert all(e["entity_id"] is None for e in events)

    @pytest.mark.asyncio
    async def test_a_forged_legacy_event_prints_nothing(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        await monitor._on_ir_event(_make_event({"raw": _nec()}, user_id="u1"))
        assert events == []


# --- the echo kinds -------------------------------------------------------


class TestEchoKinds:
    @pytest.mark.asyncio
    async def test_a_send_made_before_the_drawer_opened_has_no_seq(self):
        monitor, _, _ = _monitor()
        _send(monitor, _nec())
        events = _subscribe(monitor)
        monitor._on_emitter_beacon(_beacon())
        parsed, _ = _normalized(_nec())
        await monitor._process_parsed_signal(parsed, RECEIVER)
        assert events[-1]["echo"] == candy_feed.ECHO_SEND
        assert events[-1]["echo_of"] is None

    @pytest.mark.asyncio
    async def test_the_guard_after_the_budget_is_spent(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        _send(monitor, _nec())
        monitor._on_emitter_beacon(_beacon())
        parsed, _ = _normalized(_nec())
        for _ in range(3):  # budget of two sends, then the guard
            await monitor._process_parsed_signal(parsed, RECEIVER)
        kinds = [e["echo"] for e in events if e["dir"] == "rx"]
        assert kinds == ["send", "send", "guard"]
        assert all(e["echo_of"] == 1 for e in events if e["dir"] == "rx")

    @pytest.mark.asyncio
    async def test_a_foreign_send_names_its_emitter(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        monitor._foreign_pending["infrared.other"] = {
            "expires": sm.monotonic() + 5, "label": "Foreign send",
            "cancel": None,
        }
        monitor._mirror_upsert = MagicMock(side_effect=_noop)
        parsed, _ = _normalized(_nec())
        await monitor._process_parsed_signal(parsed, RECEIVER)
        assert events[-1]["echo"] == candy_feed.ECHO_FOREIGN
        assert events[-1]["echo_via"]
        assert events[-1]["echo_of"] is None

    @pytest.mark.asyncio
    async def test_a_garbled_echo(self):
        monitor, _, _ = _monitor()
        events = _subscribe(monitor)
        _send(monitor, _nec())
        monitor._on_emitter_beacon(_beacon())
        # The same send with its tail cut off and one bit flipped: no
        # decode, a different fingerprint, the same S/L shape mostly.
        mangled = _nec()[:-10]
        mangled[20] = -1690 if mangled[20] == -560 else -560
        parsed, n = _normalized(mangled)
        assert n.decoded_fingerprint is None
        await monitor._process_parsed_signal(parsed, RECEIVER)
        assert events[-1]["echo"] == candy_feed.ECHO_GARBLED
        assert events[-1]["echo_of"] == 1


async def _noop(*_args, **_kwargs):
    return None


# --- nothing while closed, and nothing changes -------------------------------


class TestCost:
    @pytest.mark.asyncio
    async def test_no_subscriber_builds_nothing(self):
        monitor, hass, _ = _monitor()
        with patch.object(candy_feed, "rx_event") as rx, \
                patch.object(candy_feed, "ditto_event") as ditto, \
                patch.object(candy_feed, "tx_event") as tx:
            await _run_native_signal(monitor, hass, _received(_nec()))
            monitor._on_received_signal(_received(DITTO), RECEIVER)
            await monitor._on_ir_event(_make_event({"raw": DITTO}))
            _send(monitor, _nec())
        rx.assert_not_called()
        ditto.assert_not_called()
        tx.assert_not_called()
        assert monitor._candy_seq == 0
        assert monitor._echo_expectations[0]["candy_seq"] is None

    @pytest.mark.asyncio
    async def test_unsubscribing_stops_the_stream(self):
        monitor, hass, _ = _monitor()
        events = _subscribe(monitor)
        await _run_native_signal(monitor, hass, _received(_nec()))
        monitor.candy_unsubscribe(events.append)
        await _run_native_signal(monitor, hass, _received(_nec()))
        monitor._on_received_signal(_received(DITTO), RECEIVER)
        assert len(events) == 1
        assert monitor._candy == []

    @pytest.mark.asyncio
    async def test_a_listener_that_raises_breaks_nothing(self):
        monitor, hass, store = _monitor()
        monitor.candy_subscribe(MagicMock(side_effect=RuntimeError("boom")))
        await _run_native_signal(monitor, hass, _received(_nec()))
        assert store.device_count == 1

    @pytest.mark.asyncio
    async def test_the_store_and_the_mirror_are_the_same_open_or_closed(self):
        async def run(open_drawer: bool) -> str:
            monitor, hass, store = _monitor()
            if open_drawer:
                _subscribe(monitor)
            hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
            for timings in (_nec(), DITTO, _nec(), _nec(0x10, 0x20)):
                monitor._on_received_signal(_received(timings), RECEIVER)
                if hass.async_create_task.called:
                    await hass.async_create_task.call_args[0][0]
                    hass.async_create_task.reset_mock()
            _, n = _normalized(_nec())
            with patch.object(sm, "normalize_command", lambda _c: n):
                monitor.record_send(object(), "TV / Power", [EMITTER])
                if hass.async_create_task.called:
                    await hass.async_create_task.call_args[0][0]
            monitor._on_emitter_beacon(_beacon())
            parsed, _ = _normalized(_nec())
            await monitor._process_parsed_signal(parsed, RECEIVER)
            devices = [asdict(d) for d in store.get_all_devices()]
            text = json.dumps(devices, sort_keys=True, default=str)
            # Timestamps and minted ids differ between two runs; the
            # shape and every count must not.
            text = re.sub(r'"(first_seen|last_seen|id|created_at)": "[^"]*"',
                          r'"\1": ""', text)
            text = re.sub(r"<MagicMock[^>]*>", "<mock>", text)
            return text

        assert await run(False) == await run(True)


# --- the WebSocket command ----------------------------------------------------


def _connection():
    conn = MagicMock()
    conn.subscriptions = {}
    return conn


class TestWebSocket:
    def test_admin_only(self):
        """Stated in the source, as HA's decorator is a stub here."""
        source = Path(sm.__file__).with_name("websocket_api.py").read_text()
        block = source[: source.index("async def ws_subscribe_candy(")]
        tail = block[block.rindex("\n\n\n") :]
        assert tail.lstrip().startswith("@websocket_api.require_admin")
        assert 'f"{WS_PREFIX}/candy/subscribe"' in tail

    @pytest.mark.asyncio
    async def test_subscribe_streams_and_close_unsubscribes(self, fake_hass):
        monitor, hass, _ = _monitor()
        from custom_components.hair.const import DOMAIN

        fake_hass.data[DOMAIN] = {
            "entry-1": {"signal_monitor": monitor, "device_manager": MagicMock()}
        }
        conn = _connection()
        await ws_subscribe_candy(fake_hass, conn, {"id": 7, "type": "hair/candy/subscribe"})
        conn.send_result.assert_called_once_with(7, {"subscribed": True})
        assert len(monitor._candy) == 1

        await _run_native_signal(monitor, hass, _received(_nec()))
        assert conn.send_event.call_count == 1
        msg_id, event = conn.send_event.call_args[0]
        assert msg_id == 7 and event["dir"] == "rx"

        conn.subscriptions[7]()  # the connection closes
        assert monitor._candy == []
        await _run_native_signal(monitor, hass, _received(_nec()))
        assert conn.send_event.call_count == 1

    @pytest.mark.asyncio
    async def test_not_configured(self, fake_hass):
        conn = _connection()
        await ws_subscribe_candy(fake_hass, conn, {"id": 3, "type": "hair/candy/subscribe"})
        conn.send_error.assert_called_once()
        assert conn.subscriptions == {}
