"""The power settle window (0.17.2): no flicker after a HAIR send.

Before this, ``PowerMonitor._evaluate`` dispatched a verdict on every
plug report outside the hysteresis gap and knew nothing about sends. A
HAIR "on" to a fan whose plug had not yet reported the new draw went on
optimistically, the plug's next (stale) report flipped it off, and the
report after that flipped it on again. These tests drive the monitor
through that exact sequence, plus the ways a window could quietly stop
working: outliving the monitor, a timer for a device that is gone, a
stored None read as 0, and the seed at subscribe slipping past the gate.

The loop is a fake with a hand-moved clock, so a window's timer fires
only when a test says time has passed, and a cancelled timer is visible
as cancelled rather than merely harmless.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

from custom_components.hair import power_monitor as pm
from custom_components.hair.const import DeviceType
from custom_components.hair.models import (
    DEFAULT_POWER_SETTLE_S,
    EntityConfig,
    IRCommand,
    IRDevice,
    power_settle_seconds,
)
from custom_components.hair.power_monitor import (
    SIGNAL_POWER_VERDICT,
    PowerMonitor,
    expected_power_state,
)
from custom_components.hair.send_signal import (
    ORIGIN_ENTITY,
    SIGNAL_DEVICE_SENT,
    DeviceSent,
)

SENSOR = "sensor.fan_power"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _Handle:
    def __init__(self, when, fn, args):
        self.when = when
        self.fn = fn
        self.args = args
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class _FakeLoop:
    """``loop.call_later`` on a clock the test moves by hand."""

    def __init__(self):
        self.now = 1000.0
        self.handles: list[_Handle] = []

    def time(self):
        return self.now

    def call_later(self, delay, fn, *args):
        handle = _Handle(self.now + delay, fn, args)
        self.handles.append(handle)
        return handle

    def advance(self, seconds):
        self.now += seconds
        due = sorted(
            (h for h in self.handles if not h.cancelled and h.when <= self.now),
            key=lambda h: h.when,
        )
        for handle in due:
            self.handles.remove(handle)
            handle.fn(*handle.args)

    def live(self):
        return [h for h in self.handles if not h.cancelled]


def _state(watts, entity_id=SENSOR) -> State:
    return State(entity_id, str(watts), {ATTR_UNIT_OF_MEASUREMENT: "W"})


def _commands():
    return [
        IRCommand(id="c-on", name="Power On"),
        IRCommand(id="c-off", name="Power Off"),
        IRCommand(id="c-tog", name="Power"),
        IRCommand(id="c-osc", name="Oscillate"),
    ]


def _device(**overrides) -> IRDevice:
    values = dict(
        id="fan-1",
        name="Bench Fan",
        device_type=DeviceType.FAN,
        power_sensor_entity_id=SENSOR,
        power_off_below_w=2,
        power_on_above_w=10,
        commands=_commands(),
        entity_config=EntityConfig(
            platform="fan",
            command_mapping={
                "turn_on": "Power On",
                "turn_off": "power off",  # mapping names match casefolded
                "power_toggle": "Power",
                "oscillate": "Oscillate",
            },
        ),
    )
    values.update(overrides)
    return IRDevice(**values)


class _Rig:
    """A started PowerMonitor with every HA touch point captured."""

    def __init__(self, *devices):
        self.loop = _FakeLoop()
        self.hass = MagicMock()
        self.hass.loop = self.loop
        self.readings: dict[str, State | None] = {}
        self.hass.states.get.side_effect = self.readings.get
        self.by_id = {d.id: d for d in devices}
        self.store = MagicMock()
        self.store.get_all_devices.side_effect = lambda: list(self.by_id.values())
        self.store.get_device.side_effect = self.by_id.get
        self.state_callbacks: dict[str, object] = {}
        self.unsubs: dict[str, MagicMock] = {}
        self.sent_handler = None
        self.sent_unsub = MagicMock()
        self.verdicts: list[tuple[str, str]] = []

        def _track(hass, entity_ids, fn):
            unsub = MagicMock()
            for entity_id in entity_ids:
                self.state_callbacks[entity_id] = fn
                self.unsubs[entity_id] = unsub
            return unsub

        def _connect(hass, signal, fn):
            assert signal == SIGNAL_DEVICE_SENT
            self.sent_handler = fn
            return self.sent_unsub

        def _send(hass, signal, device_id, verdict):
            assert signal == SIGNAL_POWER_VERDICT
            self.verdicts.append((device_id, verdict))

        self._patches = [
            patch.object(pm, "async_track_state_change_event", side_effect=_track),
            patch.object(pm, "async_dispatcher_connect", side_effect=_connect),
            patch.object(pm, "async_dispatcher_send", side_effect=_send),
            patch.object(pm, "_monotonic", side_effect=self.loop.time),
        ]
        for p in self._patches:
            p.start()
        self.monitor = PowerMonitor(self.hass, self.store)

    def close(self):
        for p in self._patches:
            p.stop()

    def start(self):
        self.monitor.start()

    def report(self, watts, entity_id=SENSOR):
        """The plug reports: HA state changes and the tracker fires."""
        state = _state(watts, entity_id)
        self.readings[entity_id] = state
        event = MagicMock()
        event.data = {"new_state": state}
        self.state_callbacks[entity_id](event)

    def send(self, device_id="fan-1", **kwargs):
        """A landed HAIR send, as device_manager dispatches it."""
        self.sent_handler(DeviceSent(device_id=device_id, **kwargs))

    def take(self):
        out, self.verdicts = self.verdicts, []
        return out


@pytest.fixture
def rig_factory():
    rigs = []

    def _make(*devices):
        rig = _Rig(*devices)
        rigs.append(rig)
        return rig

    yield _make
    for rig in rigs:
        rig.close()


# ---------------------------------------------------------------------------
# The flicker, and the window that ends it
# ---------------------------------------------------------------------------


class TestFlicker:
    def test_stale_report_is_held_and_fresh_report_clears_the_window(
        self, rig_factory
    ):
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _state(0.4)  # fan is off
        rig.start()
        assert rig.take() == [("fan-1", "off")]  # the startup seed

        # HAIR turns the fan on; the entity goes on optimistically.
        rig.send(command_id="c-on", command_name="Power On",
                 origin=ORIGIN_ENTITY)
        assert len(rig.loop.live()) == 1

        # 8 s later the plug reports the OLD draw. Before 0.17.2 this
        # was dispatched and flipped the entity back off.
        rig.loop.advance(8)
        rig.report(0.4)
        assert rig.take() == []

        # The next report shows the fan running: it agrees with the
        # send, so it is dispatched and the window closes at once.
        rig.loop.advance(10)
        rig.report(31.0)
        assert rig.take() == [("fan-1", "on")]
        assert rig.loop.live() == []

        # Window closed: back to a verdict on every report.
        rig.report(30.5)
        assert rig.take() == [("fan-1", "on")]

    def test_early_clear_on_turn_off(self, rig_factory):
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _state(30)
        rig.start()
        rig.take()

        rig.send(command_id="c-off")
        rig.report(29)  # stale: still running
        assert rig.take() == []
        rig.report(0.3)
        assert rig.take() == [("fan-1", "off")]
        assert rig.loop.live() == []

    def test_hysteresis_reading_inside_window_changes_nothing(self, rig_factory):
        rig = rig_factory(_device())
        rig.start()
        rig.send(command_id="c-on")
        rig.report(5)  # between 2 W and 10 W: no verdict at all
        assert rig.take() == []
        assert len(rig.loop.live()) == 1


class TestTimeoutHandback:
    def test_device_that_never_got_the_ir_goes_off_when_the_window_ends(
        self, rig_factory
    ):
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()

        rig.send(command_id="c-on")
        rig.loop.advance(10)
        rig.report(0.4)
        rig.loop.advance(9)
        rig.report(0.5)
        assert rig.take() == []

        # 20 s after the send: the current reading is evaluated the way
        # the seed is, and it wins.
        rig.loop.advance(1)
        assert rig.take() == [("fan-1", "off")]
        assert rig.loop.live() == []

        # And every report after is a verdict again.
        rig.report(0.4)
        assert rig.take() == [("fan-1", "off")]

    def test_toggle_has_no_expected_state_and_runs_full_length(
        self, rig_factory
    ):
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()

        rig.send(command_id="c-tog")
        rig.loop.advance(5)
        rig.report(31)  # agrees with "on", but a toggle promised nothing
        assert rig.take() == []
        rig.loop.advance(15)
        assert rig.take() == [("fan-1", "on")]

    def test_handback_with_ambiguous_reading_dispatches_nothing(
        self, rig_factory
    ):
        rig = rig_factory(_device())
        rig.start()
        rig.send(command_id="c-tog")
        rig.readings[SENSOR] = _state(5)
        rig.loop.advance(20)
        assert rig.take() == []
        assert rig.monitor._windows == {}


class TestLatestSendWins:
    def test_two_sends_one_window(self, rig_factory):
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()

        rig.send(command_id="c-on")
        first = rig.loop.live()[0]
        rig.loop.advance(15)
        rig.send(command_id="c-osc")  # no expected state
        assert first.cancelled
        assert len(rig.loop.live()) == 1

        # The first window's deadline passes: nothing, the second holds.
        rig.loop.advance(6)
        assert rig.take() == []
        # The second send replaced the expectation too: an agreeing
        # "on" no longer clears early.
        rig.report(31)
        assert rig.take() == []
        rig.loop.advance(14)
        assert rig.take() == [("fan-1", "on")]

    def test_off_after_on_expects_off(self, rig_factory):
        rig = rig_factory(_device())
        rig.start()
        rig.send(command_id="c-on")
        rig.send(command_id="c-off")
        rig.report(31)
        assert rig.take() == []
        rig.report(0.2)
        assert rig.take() == [("fan-1", "off")]


# ---------------------------------------------------------------------------
# The opt-out and the default
# ---------------------------------------------------------------------------


class TestOptOut:
    def test_zero_reproduces_dispatch_on_every_reading(self, rig_factory):
        rig = rig_factory(_device(power_settle_s=0))
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        assert rig.take() == [("fan-1", "off")]

        rig.send(command_id="c-on")
        assert rig.loop.live() == []
        rig.report(0.4)
        rig.report(31)
        rig.report(5)
        rig.report(30)
        assert rig.take() == [
            ("fan-1", "off"), ("fan-1", "on"), ("fan-1", "on"),
        ]
        assert rig.monitor._windows == {}

    def test_custom_value_is_the_window_length(self, rig_factory):
        rig = rig_factory(_device(power_settle_s=45))
        rig.start()
        rig.send(command_id="c-tog")
        assert rig.loop.live()[0].when == rig.loop.now + 45


class TestDefaultAndMigration:
    def test_none_reads_as_twenty(self):
        assert DEFAULT_POWER_SETTLE_S == 20
        assert power_settle_seconds(_device()) == 20
        assert power_settle_seconds(_device(power_settle_s=0)) == 0
        assert power_settle_seconds(_device(power_settle_s=7.5)) == 7.5

    def test_stored_device_without_the_key_gets_the_default_window(
        self, rig_factory
    ):
        record = _device().to_dict()
        assert "power_settle_s" not in record
        migrated = IRDevice.from_dict(record)
        assert migrated.power_settle_s is None

        rig = rig_factory(migrated)
        rig.start()
        rig.send(command_id="c-on")
        assert rig.loop.live()[0].when == rig.loop.now + 20

    def test_to_dict_writes_the_key_only_once_set(self):
        never = IRDevice.from_dict(_device().to_dict())
        assert "power_settle_s" not in never.to_dict()

        for value in (0, 0.0, 12, 120):
            stored = _device(power_settle_s=value).to_dict()
            assert stored["power_settle_s"] == value
            assert IRDevice.from_dict(stored).power_settle_s == value

    def test_zero_survives_a_round_trip_as_zero(self):
        # The opt-out must never come back as None (which is 20).
        again = IRDevice.from_dict(_device(power_settle_s=0).to_dict())
        assert again.power_settle_s == 0
        assert power_settle_seconds(again) == 0

    @pytest.mark.parametrize("junk", ["20", True, -1, 121, float("nan"), [5]])
    def test_unreadable_stored_value_falls_back_to_default_not_zero(self, junk):
        record = _device().to_dict()
        record["power_settle_s"] = junk
        assert IRDevice.from_dict(record).power_settle_s is None

    def test_clone_carries_the_value(self):
        assert _device(power_settle_s=0).clone("Copy").power_settle_s == 0
        assert _device(power_settle_s=33).clone("Copy").power_settle_s == 33
        assert _device().clone("Copy").power_settle_s is None


# ---------------------------------------------------------------------------
# The window and the monitor's own life
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_remove_device_mid_window_cancels_the_timer(self, rig_factory):
        device = _device()
        rig = rig_factory(device)
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()
        rig.send(command_id="c-on")
        handle = rig.loop.live()[0]

        rig.monitor.remove_device("fan-1")
        del rig.by_id["fan-1"]
        assert handle.cancelled
        # Even run by hand, the stale timer must not dispatch.
        handle.fn(*handle.args)
        rig.loop.advance(60)
        assert rig.take() == []

    def test_timer_for_a_deleted_and_recreated_device_is_inert(
        self, rig_factory
    ):
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()
        rig.send(command_id="c-on")
        stale = rig.loop.live()[0]

        rig.monitor.remove_device("fan-1")
        rig.monitor.rebuild_device(rig.by_id["fan-1"])  # same id again
        rig.take()  # its seed
        rig.send(command_id="c-tog")
        assert len(rig.loop.live()) == 1

        # The first device's timer, forced to run, does nothing; the
        # new device's window is still open.
        stale.fn(*stale.args)
        assert rig.take() == []
        assert "fan-1" in rig.monitor._windows

    def test_stop_cancels_every_window_and_the_send_subscription(
        self, rig_factory
    ):
        a = _device()
        b = _device(id="fan-2", power_sensor_entity_id="sensor.b_power")
        rig = rig_factory(a, b)
        rig.start()
        rig.send("fan-1", command_id="c-on")
        rig.send("fan-2", command_id="c-on")
        handles = rig.loop.live()
        assert len(handles) == 2

        rig.monitor.stop()
        assert all(h.cancelled for h in handles)
        rig.sent_unsub.assert_called_once()
        assert rig.monitor._windows == {}
        rig.loop.advance(60)
        assert rig.take() == []

    def test_start_after_stop_resubscribes_to_sends(self, rig_factory):
        rig = rig_factory(_device())
        rig.start()
        rig.monitor.stop()
        rig.sent_handler = None
        rig.start()
        assert rig.sent_handler is not None

    def test_rebuild_mid_window_keeps_the_window_and_gates_the_seed(
        self, rig_factory
    ):
        device = _device()
        rig = rig_factory(device)
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()

        rig.send(command_id="c-on")
        old = rig.loop.live()[0]
        rig.loop.advance(5)
        # The user renames the device mid-window. The re-subscribe seed
        # reads the stale 0.4 W and must not flip the entity off.
        device.name = "Bench Fan 2"
        rig.monitor.rebuild_device(device)
        assert rig.take() == []
        assert old.cancelled
        new = rig.loop.live()
        assert len(new) == 1
        # Same deadline as before the edit, not a fresh 20 s.
        assert new[0].when == old.when

        # The kept window still clears early on agreement.
        rig.report(31)
        assert rig.take() == [("fan-1", "on")]

    def test_rebuild_with_a_shorter_value_past_its_deadline_hands_back(
        self, rig_factory
    ):
        device = _device()
        rig = rig_factory(device)
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()
        rig.send(command_id="c-on")
        rig.loop.advance(8)

        device.power_settle_s = 5
        rig.monitor.rebuild_device(device)
        assert rig.loop.live() == []
        assert rig.take() == [("fan-1", "off")]  # the seed, ungated

    def test_rebuild_to_zero_ends_the_window(self, rig_factory):
        device = _device()
        rig = rig_factory(device)
        rig.readings[SENSOR] = _state(0.4)
        rig.start()
        rig.take()
        rig.send(command_id="c-on")
        device.power_settle_s = 0
        rig.monitor.rebuild_device(device)
        assert rig.loop.live() == []
        assert rig.take() == [("fan-1", "off")]

    def test_rebuild_with_sensor_cleared_ends_the_window(self, rig_factory):
        device = _device()
        rig = rig_factory(device)
        rig.start()
        rig.send(command_id="c-on")
        handle = rig.loop.live()[0]
        device.power_sensor_entity_id = None
        rig.monitor.rebuild_device(device)
        assert handle.cancelled
        assert rig.monitor._windows == {}
        rig.loop.advance(60)
        assert rig.take() == []

    def test_after_restart_there_is_no_window(self, rig_factory):
        device = _device()
        rig = rig_factory(device)
        rig.start()
        rig.send(command_id="c-on")
        rig.monitor.stop()

        # A fresh monitor, as after a restart or reload.
        rig.readings[SENSOR] = _state(0.4)
        rig.monitor = PowerMonitor(rig.hass, rig.store)
        rig.start()
        assert rig.take() == [("fan-1", "off")]


class TestWhoGetsAWindow:
    def test_device_without_a_sensor_opens_nothing(self, rig_factory):
        rig = rig_factory(
            _device(power_sensor_entity_id=None,
                    power_off_below_w=None, power_on_above_w=None)
        )
        rig.start()
        rig.send(command_id="c-on")
        assert rig.loop.live() == []
        assert rig.monitor._windows == {}

    def test_send_to_an_unknown_device_opens_nothing(self, rig_factory):
        rig = rig_factory(_device())
        rig.start()
        rig.send("ghost", command_id="c-on")
        assert rig.loop.live() == []

    def test_window_is_per_device(self, rig_factory):
        a = _device()
        b = _device(id="fan-2", power_sensor_entity_id="sensor.b_power")
        rig = rig_factory(a, b)
        rig.start()
        rig.take()
        rig.send("fan-1", command_id="c-on")
        rig.report(0.4, "sensor.b_power")
        assert rig.take() == [("fan-2", "off")]
        rig.report(0.4)
        assert rig.take() == []

    def test_every_origin_opens_a_window(self, rig_factory):
        rig = rig_factory(_device())
        rig.start()
        rig.send(command_id="c-on")  # manager origin, as fan.py sends
        assert len(rig.loop.live()) == 1
        rig.send(command_id="c-on", origin=ORIGIN_ENTITY)
        assert len(rig.loop.live()) == 1


# ---------------------------------------------------------------------------
# Expected state
# ---------------------------------------------------------------------------


class TestExpectedState:
    def test_matrix_power_codes(self):
        device = _device()
        assert expected_power_state(device, DeviceSent("fan-1", power="on")) == "on"
        assert expected_power_state(device, DeviceSent("fan-1", power="off")) == "off"

    def test_matrix_cell_is_on(self):
        sent = DeviceSent("fan-1", matrix_cell={"mode": "cool", "temp": 22})
        assert expected_power_state(_device(), sent) == "on"

    def test_flat_command_by_mapping(self):
        device = _device()
        assert expected_power_state(device, DeviceSent("fan-1", command_id="c-on")) == "on"
        assert expected_power_state(device, DeviceSent("fan-1", command_id="c-off")) == "off"

    def test_toggle_unmapped_and_unknown_say_nothing(self):
        device = _device()
        for command_id in ("c-tog", "c-osc", "missing", None):
            sent = DeviceSent("fan-1", command_id=command_id)
            assert expected_power_state(device, sent) is None

    def test_never_parsed_from_the_command_name(self):
        # Named "Power On" but mapped to nothing: no expectation.
        device = _device(entity_config=EntityConfig(platform="fan"))
        sent = DeviceSent("fan-1", command_id="c-on", command_name="Power On")
        assert expected_power_state(device, sent) is None

    def test_one_command_mapped_both_ways_says_nothing(self):
        device = _device(entity_config=EntityConfig(
            platform="fan",
            command_mapping={"turn_on": "Power", "turn_off": "Power"},
        ))
        sent = DeviceSent("fan-1", command_id="c-tog")
        assert expected_power_state(device, sent) is None


# ---------------------------------------------------------------------------
# Fix round one: the handback and the half-mapped toggle
# ---------------------------------------------------------------------------

# A fixed wall clock for the send, an hour back so that any state the
# stub stamps with the real time reads as after it.
SENT_WALL = datetime.now(UTC) - timedelta(hours=1)


def _reading(watts, *, seconds_from_send):
    """A reading whose last_reported is placed relative to the send."""
    return State(
        SENSOR,
        str(watts),
        {ATTR_UNIT_OF_MEASUREMENT: "W"},
        last_reported=SENT_WALL + timedelta(seconds=seconds_from_send),
    )


@pytest.fixture
def sent_wall():
    with patch.object(pm, "_utcnow", return_value=SENT_WALL):
        yield SENT_WALL


class TestHandbackIgnoresPreSendReadings:
    def test_thirty_second_plug_no_flicker_at_window_close(
        self, rig_factory, sent_wall
    ):
        # The plug last reported 10 s before the send and reports every
        # 30 s. At the end of a 20 s window its state is still that
        # pre-send reading, which must not be dispatched.
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _reading(0.4, seconds_from_send=-10)
        rig.start()
        assert rig.take() == [("fan-1", "off")]  # the seed, unchanged

        rig.send(command_id="c-on")
        rig.loop.advance(20)
        assert rig.take() == []
        assert rig.monitor._windows == {}

        # The plug's next report, after the send, is dispatched as usual.
        rig.loop.advance(5)
        rig.report(31.0)
        assert rig.take() == [("fan-1", "on")]

    def test_change_only_plug_never_got_the_ir_is_corrected_by_next_report(
        self, rig_factory, sent_wall
    ):
        # A plug that reports only on change: the device never got the
        # IR, the draw never changed, so the state at window close is
        # the pre-send one. No handback; the next change corrects it.
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _reading(0.4, seconds_from_send=-300)
        rig.start()
        rig.take()

        rig.send(command_id="c-on")
        rig.loop.advance(20)
        assert rig.take() == []

        rig.loop.advance(100)
        rig.report(0.5)
        assert rig.take() == [("fan-1", "off")]

    def test_reading_reported_after_the_send_is_handed_back(
        self, rig_factory, sent_wall
    ):
        # Home Assistant refreshes last_reported on an identical report
        # without a state_changed event, so the tracker never fires.
        # That report is still after the send, and the handback uses it.
        rig = rig_factory(_device())
        rig.readings[SENSOR] = _reading(0.4, seconds_from_send=-10)
        rig.start()
        rig.take()

        rig.send(command_id="c-on")
        rig.loop.advance(15)
        rig.readings[SENSOR] = _reading(0.4, seconds_from_send=15)
        assert rig.take() == []
        rig.loop.advance(5)
        assert rig.take() == [("fan-1", "off")]

    def test_reading_reported_at_the_send_counts_as_after_it(
        self, rig_factory, sent_wall
    ):
        rig = rig_factory(_device())
        rig.start()
        rig.send(command_id="c-tog")
        rig.readings[SENSOR] = _reading(31, seconds_from_send=0)
        rig.loop.advance(20)
        assert rig.take() == [("fan-1", "on")]

    def test_rebuild_mid_window_keeps_the_send_time(
        self, rig_factory, sent_wall
    ):
        device = _device()
        rig = rig_factory(device)
        rig.readings[SENSOR] = _reading(0.4, seconds_from_send=-10)
        rig.start()
        rig.take()
        rig.send(command_id="c-on")
        rig.loop.advance(5)
        device.name = "Bench Fan 2"
        with patch.object(
            pm, "_utcnow", return_value=SENT_WALL + timedelta(seconds=5)
        ):
            rig.monitor.rebuild_device(device)
        # The rebuilt window still dates from the send, so a reading
        # from 2 s after the send is after it.
        rig.readings[SENSOR] = _reading(0.4, seconds_from_send=2)
        rig.loop.advance(15)
        assert rig.take() == [("fan-1", "off")]

    def test_handback_with_no_reading_dispatches_nothing(
        self, rig_factory, sent_wall
    ):
        rig = rig_factory(_device())
        rig.start()
        rig.send(command_id="c-on")
        rig.loop.advance(20)
        assert rig.take() == []
        assert rig.monitor._windows == {}


class TestHalfMappedToggle:
    def _device(self):
        return _device(entity_config=EntityConfig(
            platform="fan",
            command_mapping={"turn_on": "Power", "power_toggle": "Power"},
        ))

    def test_toggle_also_mapped_as_turn_on_promises_nothing(self):
        sent = DeviceSent("fan-1", command_id="c-tog")
        assert expected_power_state(self._device(), sent) is None

    def test_toggle_casefolded_like_the_other_mappings(self):
        device = _device(entity_config=EntityConfig(
            platform="fan",
            command_mapping={"turn_off": "POWER", "power_toggle": "power"},
        ))
        sent = DeviceSent("fan-1", command_id="c-tog")
        assert expected_power_state(device, sent) is None

    def test_stale_agreeing_report_is_held(self, rig_factory):
        # The fan is running; turn_off falls back to the toggle button.
        rig = rig_factory(self._device())
        rig.readings[SENSOR] = _state(30)
        rig.start()
        assert rig.take() == [("fan-1", "on")]

        rig.send(command_id="c-tog")
        rig.report(29)  # stale: still the running draw
        assert rig.take() == []
        assert "fan-1" in rig.monitor._windows
        rig.report(0.3)  # the toggle did not promise off either
        assert rig.take() == []
