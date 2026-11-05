"""Always-on radio receivers: the stored opt-in, the tracker, and the doors.

The opt-in lives on the receiver's ``CaptureReceiverStore`` record,
keyed by registry entry id, beside the capture-device memory. These
tests reuse the registry and in-memory store fakes from
``test_receiver_window``.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import receiver_window as rw
from custom_components.hair import rf_receive
from custom_components.hair.const import DOMAIN, RF_SOFTWARE_WINDOW_S
from custom_components.hair.receiver_window import CaptureReceiverStore
from custom_components.hair.rf_window import RfAlwaysOn
from custom_components.hair.tests.test_receiver_window import (
    _entry,
    _MemStore,
    _Registry,
    _registry,
)
from custom_components.hair.tests.test_rf_always_on import FakeLoop

ALWAYS_ON = "radio_frequency.office_433mhz_rf_receiver"
ALWAYS_ON_ENTRY = "reg-rf-0001"
CAPTURE = "radio_frequency.office_rm4_pro_rf_receiver"
CAPTURE_ENTRY = "reg-rf-0002"


@pytest.fixture(autouse=True)
def _mem_store():
    _MemStore.loaded = None
    _MemStore.saved = []
    rw._refusals_logged.clear()
    with patch.object(rw, "Store", _MemStore):
        yield


def _rf_state(entity_id, state="2026-01-01T00:00:00+00:00", **attributes):
    attributes.setdefault("device_class", "receiver")
    return types.SimpleNamespace(entity_id=entity_id, state=state, attributes=attributes)


def _entries():
    return [
        _entry(ALWAYS_ON, ALWAYS_ON_ENTRY, "dev-athom"),
        _entry(CAPTURE, CAPTURE_ENTRY, "dev-rm4"),
    ]


class _Hass:
    def __init__(self, states):
        self._states = dict(states)
        self.states = types.SimpleNamespace(
            get=self._states.get,
            async_all=lambda domain=None: [
                s for s in self._states.values()
                if domain is None or s.entity_id.startswith(f"{domain}.")
            ],
        )
        self.loop = FakeLoop()
        self.data: dict = {}


async def _setup(states, loaded=None):
    hass = _Hass(states)
    _MemStore.loaded = loaded
    store = CaptureReceiverStore(hass)
    with _registry(_Registry(_entries())):
        await store.async_load()
    monitor = types.SimpleNamespace(
        rf_always_on=RfAlwaysOn(hass, wall_now=hass.loop.wall), _rf_tracker=None
    )
    hass.data[DOMAIN] = {"entry": {"capture_receivers": store, "signal_monitor": monitor}}
    return hass, store, monitor


def _conn():
    conn = MagicMock()
    conn.subscriptions = {}
    return conn


class TestTheStore:
    @pytest.mark.asyncio
    async def test_the_opt_in_survives_a_restart_and_is_not_a_capture_memory(self):
        _, store, _ = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        store.set_rf_listen(ALWAYS_ON_ENTRY, True)
        saved = _MemStore.saved[-1]
        assert saved == {"receivers": {
            ALWAYS_ON_ENTRY: {"capture": False, "switch": None, "rf_listen": True},
        }}
        assert store.rf_listen(ALWAYS_ON_ENTRY)
        assert not store.remembered(ALWAYS_ON_ENTRY)
        # A restart: loaded back, still opted in.
        _hass, again, _ = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)}, loaded=saved)
        assert again.rf_listen(ALWAYS_ON_ENTRY)

    @pytest.mark.asyncio
    async def test_opting_out_forgets_a_record_with_nothing_else_in_it(self):
        _hass, store, _ = await _setup({})
        store.set_rf_listen(ALWAYS_ON_ENTRY, True)
        store.set_rf_listen(ALWAYS_ON_ENTRY, False)
        assert _MemStore.saved[-1] == {"receivers": {}}

    @pytest.mark.asyncio
    async def test_a_record_for_a_receiver_gone_from_the_registry_is_dropped(self):
        loaded = {"receivers": {"reg-gone": {"capture": False, "switch": None, "rf_listen": True}}}
        _hass, store, _ = await _setup({}, loaded=loaded)
        assert not store.rf_listen("reg-gone")


class TestTheTracker:
    @pytest.fixture(autouse=True)
    def _trackers(self, monkeypatch):
        self.watch = []
        monkeypatch.setattr(rf_receive, "async_track_state_added_domain",
                            lambda *a: (lambda: None))
        monkeypatch.setattr(rf_receive, "async_track_state_removed_domain",
                            lambda *a: (lambda: None))
        monkeypatch.setattr(rf_receive, "async_track_state_change_event",
                            lambda hass, ids, cb: self.watch.append(cb) or (lambda: None))

    def test_an_always_on_receiver_is_subscribed_only_once_opted_in(self, rf_platform):
        states = {ALWAYS_ON: _rf_state(ALWAYS_ON), CAPTURE: _rf_state(CAPTURE, capturing=False)}
        hass = _Hass(states)
        opted = set()
        attached, detached = [], []
        tracker = rf_receive.RfReceiverTracker(
            hass, lambda *a: None,
            opted_in=lambda eid: eid in opted,
            on_attach=attached.append, on_detach=detached.append,
        )
        tracker.async_start()
        assert tracker.subscribed == [CAPTURE]
        assert attached == []  # a capture device is not attached as always-on
        opted.add(ALWAYS_ON)
        tracker.reconcile()
        assert tracker.subscribed == sorted([ALWAYS_ON, CAPTURE])
        assert attached == [ALWAYS_ON]
        opted.clear()
        tracker.reconcile()
        assert tracker.subscribed == [CAPTURE]
        assert detached == [ALWAYS_ON]

    def test_an_opted_in_receiver_going_unavailable_is_let_go(self, rf_platform):
        states = {ALWAYS_ON: _rf_state(ALWAYS_ON)}
        hass = _Hass(states)
        detached = []
        tracker = rf_receive.RfReceiverTracker(
            hass, lambda *a: None, opted_in=lambda eid: True,
            on_attach=lambda eid: None, on_detach=detached.append,
        )
        tracker.async_start()
        down = _rf_state(ALWAYS_ON, state="unavailable")
        states[ALWAYS_ON] = down
        hass._states[ALWAYS_ON] = down
        self.watch[-1](types.SimpleNamespace(data={"entity_id": ALWAYS_ON, "new_state": down}))
        assert tracker.subscribed == [] and detached == [ALWAYS_ON]


@pytest.fixture
def rf_platform(monkeypatch):
    from custom_components.hair.tests.test_rf_hear import rf_platform as kobe_platform

    return kobe_platform.__wrapped__(monkeypatch)


class TestTheDoors:
    @pytest.mark.asyncio
    async def test_opt_in_and_out(self):
        from custom_components.hair.websocket_api import ws_rf_opt_in

        hass, store, _ = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        conn = _conn()
        with _registry(_Registry(_entries())), patch(
            "custom_components.hair.websocket_api._get_first_entry_data",
            return_value=hass.data[DOMAIN]["entry"],
        ):
            ws_rf_opt_in(hass, conn, {"id": 1, "receiver_entity_id": ALWAYS_ON, "enabled": True})
            entry = conn.send_result.call_args.args[1]
            assert entry["always_on"] and entry["opted_in"] and entry["software_window"]
            assert entry["counters"] is None  # nobody attached it in this test
            assert store.rf_listen(ALWAYS_ON_ENTRY)
            ws_rf_opt_in(hass, conn, {"id": 2, "receiver_entity_id": ALWAYS_ON, "enabled": False})
            assert not conn.send_result.call_args.args[1]["opted_in"]
        conn.send_error.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("receiver", "code"), [
        (CAPTURE, "not_always_on"),
        ("radio_frequency.nobody", "unknown_receiver"),
        ("radio_frequency.unregistered", "not_registered"),
    ])
    async def test_opt_in_refusals(self, receiver, code):
        from custom_components.hair.websocket_api import ws_rf_opt_in

        hass, _store, _ = await _setup({
            ALWAYS_ON: _rf_state(ALWAYS_ON),
            CAPTURE: _rf_state(CAPTURE, capturing=False),
            "radio_frequency.unregistered": _rf_state("radio_frequency.unregistered"),
        })
        conn = _conn()
        with _registry(_Registry(_entries())):
            ws_rf_opt_in(hass, conn, {"id": 1, "receiver_entity_id": receiver, "enabled": True})
        assert conn.send_error.call_args.args[1] == code

    @pytest.mark.asyncio
    async def test_listen_opens_the_software_window_with_its_defaults_and_limits(self):
        from custom_components.hair.websocket_api import ws_receiver_listen

        hass, _store, monitor = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        monitor.rf_always_on.attach(ALWAYS_ON)
        conn = _conn()
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(
                hass, conn, {"id": 1, "receiver_entity_id": ALWAYS_ON, "on": True}
            )
        result = conn.send_result.call_args.args[1]
        assert result["on"] and result["capturing"] and result["capture_mode"] == "sliding"
        window = monitor.rf_always_on.window(ALWAYS_ON)
        assert window.seconds == RF_SOFTWARE_WINDOW_S
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(hass, conn, {
                "id": 2, "receiver_entity_id": ALWAYS_ON, "on": True,
                "mode": "single", "seconds": 120,
            })
        assert (window.mode, window.seconds) == ("single", 120)
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(
                hass, conn, {"id": 3, "receiver_entity_id": ALWAYS_ON, "on": False}
            )
        assert not window.capturing

    @pytest.mark.asyncio
    async def test_listen_on_an_always_on_receiver_not_opted_in(self):
        from custom_components.hair.websocket_api import ws_receiver_listen

        hass, _store, _ = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        conn = _conn()
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(
                hass, conn, {"id": 1, "receiver_entity_id": ALWAYS_ON, "on": True}
            )
        assert conn.send_error.call_args.args[1] == "not_opted_in"

    @pytest.mark.asyncio
    async def test_the_capture_door_lists_a_software_row(self):
        hass, _store, monitor = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        monitor.rf_always_on.attach(ALWAYS_ON)
        monitor.rf_always_on.window(ALWAYS_ON).open()
        with _registry(_Registry(_entries())):
            rows = rw.capture_receivers(hass)
        (row,) = rows
        assert row["receiver_entity_id"] == ALWAYS_ON
        assert row["capture_device"] is False and row["software_window"] is True
        assert row["source"] == "software" and row["switch_entity_id"] is None
        assert row["device_switches"] == []
        assert row["capturing"] is True and row["capture_mode"] == "sliding"
        assert row["window_ends_at"] is not None

    @pytest.mark.asyncio
    async def test_the_editor_listen_gets_a_software_arm(self):
        hass, _store, monitor = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        monitor.rf_always_on.attach(ALWAYS_ON)
        with _registry(_Registry(_entries())):
            arm = rw.arm_for(hass, ALWAYS_ON, on_failure=lambda e: None,
                             on_window_closed=lambda: None)
        assert type(arm).__name__ == "SoftwareWindowArm"
        await arm.async_start()
        assert monitor.rf_always_on.window_open(ALWAYS_ON)
        await arm.async_stop()
        assert not monitor.rf_always_on.window_open(ALWAYS_ON)

    @pytest.mark.asyncio
    async def test_the_subscription_snapshot_then_events(self):
        from custom_components.hair.websocket_api import ws_rf_subscribe

        hass, _store, monitor = await _setup({ALWAYS_ON: _rf_state(ALWAYS_ON)})
        always_on = monitor.rf_always_on
        always_on.attach(ALWAYS_ON)
        conn = _conn()
        ws_rf_subscribe(hass, conn, {"id": 7})
        (item,) = conn.send_result.call_args.args[1]
        assert set(item) == {"receiver_entity_id", "capturing", "window_ends_at",
                             "capture_mode", "counters"}
        assert item["capturing"] is False and item["counters"]["captures"] == 0
        # A window change: at once.
        always_on.window(ALWAYS_ON).open()
        assert conn.send_event.call_args.args[1]["capturing"] is True
        # Counters alone: at most once a second.
        sent = conn.send_event.call_count
        for _ in range(50):
            always_on.count(ALWAYS_ON, "captures")
        assert conn.send_event.call_count == sent
        hass.loop.advance_to(hass.loop.now + 1.01)
        assert conn.send_event.call_count == sent + 1
        assert conn.send_event.call_args.args[1]["counters"]["captures"] == 50
        # Opting out: a last item with no counters.
        always_on.detach(ALWAYS_ON)
        assert conn.send_event.call_args.args[1]["counters"] is None
        conn.subscriptions[7]()
