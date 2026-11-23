"""An on/off state source wins at the end of the settle window.

A watt plug's reading at the end of a window is often the draw from
before the send, so the handback takes only a reading reported after
it (``test_power_settle_window.py``). An on/off source (a binary
sensor, switch, input boolean or device tracker) may never report
again: a helper writes its state only when it changes. Under the
plug's rule a press the device never received would stand until
somebody flipped the helper. So at the end of the window an on/off
source's current state wins, whenever it was reported:

- a source that stays off undoes an on press at the end;
- a toggle, which promises nothing, ends as the source says;
- unavailable, unknown or a zone name still holds;
- a source that comes round to the press still ends the window early;
- a watt plug's pre-send reading is still not taken;
- an on/off source with no settle time of its own waits 180 s, a watt
  plug 20 s, and a stored value is kept.

Devices and typed Remotes share the monitor, so each rule is checked
for both.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.core import State

from custom_components.hair.const import DeviceType
from custom_components.hair.models import (
    DEFAULT_ON_OFF_SETTLE_S,
    DEFAULT_POWER_SETTLE_S,
    default_power_settle_s,
    power_settle_seconds,
)
from custom_components.hair.remote_state import SIGNAL_REMOTE_POWER_VERDICT
from custom_components.hair.tests.test_power_settle_window import (
    SENT_WALL,
    _device,
    _reading,
    rig_factory,  # noqa: F401 (a fixture)
    sent_wall,  # noqa: F401 (a fixture)
)
from custom_components.hair.tests.test_remote_power import (
    PLUG,
    _remote,
    _watts,
    rig_for,  # noqa: F401 (a fixture)
)

HELPER = "input_boolean.fan_on"
PRESENCE = "input_boolean.bench_tv_presence"


def _onoff(entity_id, state, *, seconds_from_send):
    """An on/off reading reported relative to the send or press."""
    return State(
        entity_id,
        state,
        last_reported=SENT_WALL + timedelta(seconds=seconds_from_send),
    )


def _fire(callbacks, entity_id, state):
    """The source changes: HA's state tracker fires."""
    event = MagicMock()
    event.data = {"new_state": state}
    callbacks[entity_id](event)


def _onoff_device(**overrides):
    values = dict(
        power_sensor_entity_id=HELPER,
        power_off_below_w=None,
        power_on_above_w=None,
    )
    values.update(overrides)
    return _device(**values)


def _onoff_remote(**overrides):
    values = dict(
        power_sensor_entity_id=PRESENCE,
        power_off_below_w=None,
        power_on_above_w=None,
    )
    values.update(overrides)
    return _remote(DeviceType.MEDIA_PLAYER, **values)


def _remote_verdict(verdict):
    return [(SIGNAL_REMOTE_POWER_VERDICT, "rem-1", verdict)]


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


class TestADevice:
    def _started(self, rig_factory, state, **overrides):  # noqa: F811
        rig = rig_factory(_onoff_device(**overrides))
        rig.readings[HELPER] = _onoff(HELPER, state, seconds_from_send=-300)
        rig.start()
        rig.take()  # the seed
        return rig

    def test_a_helper_that_stays_off_undoes_an_on_send_at_the_end(
        self, rig_factory, sent_wall  # noqa: F811
    ):
        rig = self._started(rig_factory, "off")
        rig.send(command_id="c-on")
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S - 1)
        assert rig.take() == []
        rig.loop.advance(1)
        assert rig.take() == [("fan-1", "off")]
        assert rig.monitor._windows == {}

    def test_a_helper_that_stays_on_undoes_an_off_send_at_the_end(
        self, rig_factory, sent_wall  # noqa: F811
    ):
        rig = self._started(rig_factory, "on")
        rig.send(command_id="c-off")
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S)
        assert rig.take() == [("fan-1", "on")]

    def test_a_toggle_ends_as_the_source_says(self, rig_factory, sent_wall):  # noqa: F811
        rig = self._started(rig_factory, "on")
        rig.send(command_id="c-tog")
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S)
        assert rig.take() == [("fan-1", "on")]

    @pytest.mark.parametrize("state", ["unavailable", "unknown", "Work"])
    def test_a_source_that_says_nothing_still_holds(
        self, rig_factory, sent_wall, state  # noqa: F811
    ):
        rig = self._started(rig_factory, "off")
        rig.send(command_id="c-on")
        rig.readings[HELPER] = _onoff(HELPER, state, seconds_from_send=-300)
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S)
        assert rig.take() == []
        assert rig.monitor._windows == {}

    def test_a_source_that_comes_round_still_ends_the_window_early(
        self, rig_factory, sent_wall  # noqa: F811
    ):
        rig = self._started(rig_factory, "off")
        rig.send(command_id="c-on")
        rig.loop.advance(30)
        state = _onoff(HELPER, "on", seconds_from_send=30)
        rig.readings[HELPER] = state
        _fire(rig.state_callbacks, HELPER, state)
        assert rig.take() == [("fan-1", "on")]
        assert rig.monitor._windows == {}
        assert rig.loop.live() == []

    def test_a_disagreement_inside_the_window_still_waits_for_the_end(
        self, rig_factory, sent_wall  # noqa: F811
    ):
        rig = self._started(rig_factory, "on")
        rig.send(command_id="c-on")
        rig.loop.advance(30)
        state = _onoff(HELPER, "off", seconds_from_send=30)
        rig.readings[HELPER] = state
        _fire(rig.state_callbacks, HELPER, state)
        assert rig.take() == []
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S - 30)
        assert rig.take() == [("fan-1", "off")]

    def test_a_watt_plugs_pre_send_reading_is_still_not_taken(
        self, rig_factory, sent_wall  # noqa: F811
    ):
        rig = rig_factory(_device())
        rig.readings["sensor.fan_power"] = _reading(0.4, seconds_from_send=-10)
        rig.start()
        rig.take()
        rig.send(command_id="c-on")
        rig.loop.advance(DEFAULT_POWER_SETTLE_S)
        assert rig.take() == []
        assert rig.monitor._windows == {}

    def test_a_stored_settle_time_is_kept(self, rig_factory, sent_wall):  # noqa: F811
        rig = self._started(rig_factory, "off", power_settle_s=30.0)
        rig.send(command_id="c-on")
        rig.loop.advance(30)
        assert rig.take() == [("fan-1", "off")]


# ---------------------------------------------------------------------------
# Remotes
# ---------------------------------------------------------------------------


class TestARemote:
    def _started(self, rig_for, state, **overrides):  # noqa: F811
        rig = rig_for(_onoff_remote(**overrides))
        rig.readings[PRESENCE] = _onoff(PRESENCE, state, seconds_from_send=-300)
        rig.monitor.start()
        rig.take()  # the seed
        return rig

    def test_a_helper_that_stays_off_undoes_an_on_press_at_the_end(self, rig_for):  # noqa: F811
        # The bench case: helper off, Power on pressed on
        # the handset, the TV never came on.
        rig = self._started(rig_for, "off")
        rig.press("t-on")
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S - 1)
        assert rig.take() == []
        rig.loop.advance(1)
        assert rig.take() == _remote_verdict("off")
        assert rig.monitor._windows == {}

    def test_a_toggle_ends_as_the_source_says(self, rig_for):  # noqa: F811
        rig = self._started(rig_for, "off")
        rig.press("t-tog")
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S)
        assert rig.take() == _remote_verdict("off")

    @pytest.mark.parametrize("state", ["unavailable", "unknown", "Work"])
    def test_a_source_that_says_nothing_still_holds(self, rig_for, state):  # noqa: F811
        rig = self._started(rig_for, "off")
        rig.press("t-on")
        rig.readings[PRESENCE] = _onoff(PRESENCE, state, seconds_from_send=-300)
        rig.loop.advance(DEFAULT_ON_OFF_SETTLE_S)
        assert rig.take() == []

    def test_a_source_that_comes_round_still_ends_the_window_early(self, rig_for):  # noqa: F811
        rig = self._started(rig_for, "off")
        rig.press("t-on")
        state = _onoff(PRESENCE, "on", seconds_from_send=20)
        rig.readings[PRESENCE] = state
        _fire(rig.callbacks, PRESENCE, state)
        assert rig.take() == _remote_verdict("on")
        assert rig.monitor._windows == {}

    def test_a_watt_plugs_pre_press_reading_is_still_not_taken(self, rig_for):  # noqa: F811
        rig = rig_for(_remote(DeviceType.MEDIA_PLAYER))
        rig.readings[PLUG] = _watts(0, reported=SENT_WALL - timedelta(seconds=10))
        rig.monitor.start()
        rig.take()
        rig.press("t-on")
        rig.loop.advance(DEFAULT_POWER_SETTLE_S)
        assert rig.take() == []
        assert rig.monitor._windows == {}


# ---------------------------------------------------------------------------
# The default settle time
# ---------------------------------------------------------------------------


class TestTheDefault:
    @pytest.mark.parametrize(
        ("source", "seconds"),
        [
            ("sensor.fan_power", 20),
            ("binary_sensor.tv_on", 180),
            ("switch.amp_plug", 180),
            ("input_boolean.tv_on", 180),
            ("device_tracker.living_room_tv", 180),
            (None, 20),
        ],
    )
    def test_the_default_follows_the_source(self, source, seconds):
        assert default_power_settle_s(source) == seconds
        assert power_settle_seconds(_device(power_sensor_entity_id=source)) == seconds
        assert power_settle_seconds(_remote(power_sensor_entity_id=source)) == seconds

    def test_a_stored_value_is_kept_whatever_the_source(self):
        for source in ("sensor.fan_power", HELPER):
            assert power_settle_seconds(
                _device(power_sensor_entity_id=source, power_settle_s=45.0)
            ) == 45
            assert power_settle_seconds(
                _device(power_sensor_entity_id=source, power_settle_s=0.0)
            ) == 0

    def test_nothing_is_rewritten_in_the_store(self):
        device = _onoff_device()
        assert device.power_settle_s is None
        assert "power_settle_s" not in device.to_dict()
