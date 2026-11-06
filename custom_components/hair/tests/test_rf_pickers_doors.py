"""The Sniffer's pickers and the Devices tab's facts: the server side.

RF hear round 1, frontend. A capture device may declare the entities
that set its next window (``frequency_select``, ``window_length``,
``capture_mode_select``) and what each frequency option stands for
(``frequency_options``); HAIR passes them to the panel under the
``capture_switch`` safety rule. An always-on radio receiver's software
window has no entities, so its length and mode are kept on its
``CaptureReceiverStore`` record. And the hardware rows' one fact each:
when HAIR last took a code from a receiver, and last sent through an
emitter.

Reuses the registry and store fakes from ``test_receiver_window``.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import receiver_window as rw
from custom_components.hair.const import DOMAIN
from custom_components.hair.receiver_window import CaptureReceiverStore
from custom_components.hair.rf_window import RfAlwaysOn
from custom_components.hair.tests.test_receiver_window import (
    _entry,
    _MemStore,
    _Registry,
    _registry,
)
from custom_components.hair.tests.test_rf_always_on import FakeLoop

RM4_RF = "radio_frequency.rm4_pro_rf_receiver"
RM4_RF_ENTRY = "reg-rf-rm4"
RM4 = "dev-rm4"
FREQ = "select.rm4_pro_rf_frequency"
LENGTH = "number.rm4_pro_capture_window"
MODE = "select.rm4_pro_capture_mode"
SWITCH = "switch.rm4_pro_rf_capture"
ELSEWHERE_SELECT = "select.garage_mode"

ATHOM = "radio_frequency.athom_433mhz_rf_receiver"
ATHOM_ENTRY = "reg-rf-athom"

OPTIONS = {"mhz_433_92": 433_920_000, "mhz_315": 315_000_000, "sweep": "sweep"}


@pytest.fixture(autouse=True)
def _mem_store():
    _MemStore.loaded = None
    _MemStore.saved = []
    rw._refusals_logged.clear()
    with patch.object(rw, "Store", _MemStore):
        yield


def _entries():
    return [
        _entry(RM4_RF, RM4_RF_ENTRY, RM4),
        _entry(FREQ, "reg-freq", RM4),
        _entry(LENGTH, "reg-len", RM4),
        _entry(MODE, "reg-mode", RM4),
        _entry(SWITCH, "reg-sw", RM4),
        _entry(ATHOM, ATHOM_ENTRY, "dev-athom"),
        _entry(ELSEWHERE_SELECT, "reg-garage", "dev-garage"),
    ]


def _rf(entity_id, state="2026-01-01T00:00:00+00:00", **attributes):
    attributes.setdefault("device_class", "receiver")
    return types.SimpleNamespace(entity_id=entity_id, state=state, attributes=attributes)


def _rm4(**extra):
    """BroadSniff 0.3.1's RF receiver: the window, and its three settings."""
    attributes = {
        "capturing": False, "capture_switch": SWITCH, "capture_mode": "sliding",
        "frequency_select": FREQ, "window_length": LENGTH, "capture_mode_select": MODE,
        "frequency_options": dict(OPTIONS),
    }
    attributes.update(extra)
    return _rf(RM4_RF, **attributes)


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

    def set(self, entity_id, state):
        self._states[entity_id] = state


async def _setup(states, loaded=None):
    hass = _Hass(states)
    _MemStore.loaded = loaded
    store = CaptureReceiverStore(hass)
    with _registry(_Registry(_entries())):
        await store.async_load()
    monitor = types.SimpleNamespace(
        rf_always_on=RfAlwaysOn(hass, wall_now=hass.loop.wall), _rf_tracker=None
    )
    hass.data[DOMAIN] = {
        "entry": {
            "capture_receivers": store, "signal_monitor": monitor,
            "device_manager": object(),
        }
    }
    return hass, store, monitor


def _conn():
    conn = MagicMock()
    conn.subscriptions = {}
    return conn


def _row(rows, receiver):
    return next(r for r in rows if r["receiver_entity_id"] == receiver)


class TestDeclaredSettings:
    @pytest.mark.asyncio
    async def test_a_capture_device_passes_its_three_entities_and_the_map(self):
        hass, _store, _ = await _setup({RM4_RF: _rm4()})
        with _registry(_Registry(_entries())):
            row = _row(rw.capture_receivers(hass), RM4_RF)
        assert (row["frequency_select"], row["window_length"], row["capture_mode_select"]) == (
            FREQ, LENGTH, MODE,
        )
        assert row["frequency_options"] == [
            {"option": "mhz_433_92", "hz": 433_920_000},
            {"option": "mhz_315", "hz": 315_000_000},
            {"option": "sweep", "hz": None},
        ]
        # A capture device's pickers drive its entities, not HAIR's record.
        assert (row["window_seconds"], row["window_mode"]) == (None, None)

    @pytest.mark.asyncio
    async def test_a_setting_off_the_device_or_in_the_wrong_domain_is_refused(self):
        hass, _store, _ = await _setup({RM4_RF: _rm4(
            frequency_select=ELSEWHERE_SELECT,   # another device's select
            window_length=MODE,                  # a select where a number goes
        )})
        with _registry(_Registry(_entries())):
            row = _row(rw.capture_receivers(hass), RM4_RF)
        assert row["frequency_select"] is None
        assert row["window_length"] is None
        assert row["capture_mode_select"] == MODE
        # The map means nothing without a frequency select.
        assert row["frequency_options"] == []

    def test_the_map_keeps_what_it_can_read(self):
        assert rw.frequency_options({
            "a": 433_920_000, "b": "sweep", "c": 0, "d": "433.92", "e": True,
            "": 315_000_000, "f": -1, "custom": None,
        }) == [{"option": "a", "hz": 433_920_000}, {"option": "b", "hz": None}]
        assert rw.frequency_options(["mhz_433_92"]) == []
        assert rw.frequency_options(None) == []

    @pytest.mark.asyncio
    async def test_the_settings_outlast_an_unavailable_receiver(self):
        """HA drops extra attributes while an entity is unavailable; the
        pickers keep what the device last declared, greyed."""
        hass, _store, _ = await _setup({RM4_RF: _rm4()})
        with _registry(_Registry(_entries())):
            rw.capture_receivers(hass)
            hass.set(RM4_RF, _rf(RM4_RF, state="unavailable"))
            row = _row(rw.capture_receivers(hass), RM4_RF)
        assert row["available"] is False
        assert row["frequency_select"] == FREQ
        assert [o["option"] for o in row["frequency_options"]] == [
            "mhz_433_92", "mhz_315", "sweep",
        ]
        assert _MemStore.saved[-1]["receivers"][RM4_RF_ENTRY]["settings"][
            "window_length"
        ] == LENGTH

    @pytest.mark.asyncio
    async def test_settings_stop_when_the_device_stops_declaring(self):
        hass, store, _ = await _setup({RM4_RF: _rm4()})
        with _registry(_Registry(_entries())):
            rw.capture_receivers(hass)
            hass.set(RM4_RF, _rf(RM4_RF, capturing=False, capture_switch=SWITCH))
            row = _row(rw.capture_receivers(hass), RM4_RF)
        assert row["frequency_select"] is None and row["frequency_options"] == []
        assert store.settings(RM4_RF_ENTRY) == {}

    @pytest.mark.asyncio
    async def test_stored_settings_survive_a_restart_and_bad_ones_do_not(self):
        _hass, store, _ = await _setup({}, loaded={"receivers": {
            RM4_RF_ENTRY: {
                "capture": True, "switch": None,
                "settings": {
                    "frequency_select": FREQ, "window_length": 5,
                    "frequency_options": [{"option": "sweep", "hz": None}, "junk"],
                },
            },
        }})
        assert store.settings(RM4_RF_ENTRY) == {
            "frequency_select": FREQ,
            "frequency_options": [{"option": "sweep", "hz": None}],
        }


class TestSoftwareWindowChoices:
    @pytest.mark.asyncio
    async def test_the_row_carries_the_defaults_then_the_choice(self):
        from custom_components.hair.websocket_api import ws_receiver_window_prefs

        hass, _store, monitor = await _setup({ATHOM: _rf(ATHOM)})
        monitor.rf_always_on.attach(ATHOM)
        with _registry(_Registry(_entries())):
            row = _row(rw.capture_receivers(hass), ATHOM)
            assert (row["window_seconds"], row["window_mode"]) == (30, "sliding")
            assert row["frequency_select"] is None and row["frequency_options"] == []
            conn = _conn()
            ws_receiver_window_prefs(hass, conn, {
                "id": 1, "receiver_entity_id": ATHOM, "seconds": 120, "mode": "multiple",
            })
            assert conn.send_result.call_args.args[1] == {
                "window_seconds": 120, "window_mode": "multiple",
            }
            row = _row(rw.capture_receivers(hass), ATHOM)
        assert (row["window_seconds"], row["window_mode"]) == (120, "multiple")
        record = _MemStore.saved[-1]["receivers"][ATHOM_ENTRY]
        assert record["window"] == {"seconds": 120, "mode": "multiple"}
        assert record["capture"] is False, "a choice never makes a capture device"

    @pytest.mark.asyncio
    async def test_listen_opens_with_the_choice_unless_told_otherwise(self):
        from custom_components.hair.websocket_api import ws_receiver_listen

        hass, _store, monitor = await _setup({ATHOM: _rf(ATHOM)}, loaded={"receivers": {
            ATHOM_ENTRY: {"capture": False, "switch": None,
                          "window": {"seconds": 60, "mode": "single"}},
        }})
        monitor.rf_always_on.attach(ATHOM)
        window = monitor.rf_always_on.window(ATHOM)
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(hass, _conn(), {
                "id": 1, "receiver_entity_id": ATHOM, "on": True,
            })
            assert (window.seconds, window.mode) == (60, "single")
            await ws_receiver_listen(hass, _conn(), {
                "id": 2, "receiver_entity_id": ATHOM, "on": True,
                "seconds": 10, "mode": "sliding",
            })
        assert (window.seconds, window.mode) == (10, "sliding")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("receiver", "code"), [
        (RM4_RF, "capture_device"),
        ("infrared.living_rx", "unknown_receiver"),
        ("radio_frequency.unregistered", "not_registered"),
    ])
    async def test_refusals(self, receiver, code):
        from custom_components.hair.websocket_api import ws_receiver_window_prefs

        hass, _store, _ = await _setup({
            RM4_RF: _rm4(),
            "radio_frequency.unregistered": _rf("radio_frequency.unregistered"),
        })
        conn = _conn()
        with _registry(_Registry(_entries())):
            ws_receiver_window_prefs(hass, conn, {
                "id": 1, "receiver_entity_id": receiver, "seconds": 30, "mode": "sliding",
            })
        assert conn.send_error.call_args.args[1] == code

    @pytest.mark.asyncio
    async def test_a_bad_stored_choice_is_dropped_at_load(self):
        _hass, store, _ = await _setup({}, loaded={"receivers": {
            ATHOM_ENTRY: {"capture": False, "switch": None,
                          "window": {"seconds": 900, "mode": "sliding"}},
        }})
        assert store.window_prefs(ATHOM_ENTRY) == (30, "sliding")


class TestTheFacts:
    def _monitor(self):
        from custom_components.hair.signal_monitor import SignalMonitor

        monitor = SignalMonitor.__new__(SignalMonitor)
        monitor._last_heard_at = {}
        monitor._last_sent_at = {}
        return monitor

    def test_heard_is_noted_per_receiver_and_never_for_none(self):
        monitor = self._monitor()
        monitor._note_heard("infrared.rx")
        monitor._note_heard(None)
        facts = monitor.hardware_facts()
        assert list(facts["heard"]) == ["infrared.rx"]
        assert facts["sent"] == {}
        assert facts["heard"]["infrared.rx"].endswith("+00:00")

    @pytest.mark.asyncio
    async def test_the_door_answers_empty_without_a_monitor(self):
        from custom_components.hair.websocket_api import ws_hardware_facts

        hass = _Hass({})
        conn = _conn()
        ws_hardware_facts(hass, conn, {"id": 1})
        assert conn.send_result.call_args.args[1] == {"heard": {}, "sent": {}}

    @pytest.mark.asyncio
    async def test_the_door_returns_the_monitors_facts(self):
        from custom_components.hair.websocket_api import ws_hardware_facts

        monitor = self._monitor()
        monitor._note_heard(ATHOM)
        monitor._last_sent_at["infrared.blaster"] = "2026-11-06T18:00:00+00:00"
        hass = _Hass({})
        hass.data[DOMAIN] = {"entry": {"signal_monitor": monitor, "device_manager": object()}}
        conn = _conn()
        ws_hardware_facts(hass, conn, {"id": 1})
        facts = conn.send_result.call_args.args[1]
        assert list(facts["heard"]) == [ATHOM]
        assert facts["sent"] == {"infrared.blaster": "2026-11-06T18:00:00+00:00"}


def test_where_heard_is_noted_in_the_pipeline():
    """Accepted codes only: a trigger match, a hidden row counting up, a
    stored row. Never the drops before them (noise, a short radio body,
    a closed software window, an echo)."""
    import inspect

    from custom_components.hair.signal_monitor import SignalMonitor

    source = inspect.getsource(SignalMonitor._process_parsed_signal)
    assert source.count("self._note_heard(receiver_entity_id)") == 3
    echo = source.index("if echo:")
    first = source.index("self._note_heard(")
    assert first > echo, "an echo of HAIR's own send is never 'heard'"
    window_drop = source.index('"new_window_closed"')
    assert source.index("self._note_heard(", window_drop) > window_drop
