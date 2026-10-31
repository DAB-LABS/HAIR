"""A Device's state read from an on/off entity (GH #232).

A Device's state source can be a power sensor in watts or an on/off
entity: a binary sensor, switch, input boolean or device tracker. The
on/off kind is read by its state alone (``on`` and ``home`` are on,
``off`` and ``not_home`` are off, anything else holds) and everything
after the verdict is shared with the watts kind: the settle window, the
seed at subscribe, the handback that only trusts a reading reported
after the send. Only the settle time's ceiling differs: 600 s for an
on/off source, 120 s for watts.
"""
from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import State

from custom_components.hair import power_monitor as pm
from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    MAX_ON_OFF_SETTLE_S,
    MAX_POWER_SETTLE_S,
    ON_OFF_DOMAINS,
    IRDevice,
    is_on_off_entity,
    max_power_settle_s,
)
from custom_components.hair.power_monitor import classify_power_reading
from custom_components.hair.tests.test_power_settle_window import (
    SENT_WALL,
    _device,
    _Rig,
)
from custom_components.hair.tests.test_websocket_api import (
    _make_connection,
    _wire_hass,
)
from custom_components.hair.websocket_api import ws_update_device

TRACKER = "device_tracker.living_room_tv"
SOURCES = {
    "binary_sensor": "binary_sensor.tv_on",
    "switch": "switch.tv_plug",
    "input_boolean": "input_boolean.tv_on",
    "device_tracker": TRACKER,
}


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------


READINGS = {
    "on": "on",
    "home": "on",
    "off": "off",
    "not_home": "off",
    "unavailable": None,
    "unknown": None,
    "Work": None,  # a GPS tracker in a zone says nothing about the TV
    "idle": None,
    "": None,
}


class TestVerdict:
    @pytest.mark.parametrize("domain", ON_OFF_DOMAINS)
    @pytest.mark.parametrize("reading,verdict", sorted(READINGS.items()))
    def test_every_domain_and_state(self, domain, reading, verdict):
        state = State(f"{domain}.source", reading)
        assert classify_power_reading(state, None, None) == verdict

    @pytest.mark.parametrize("domain", ON_OFF_DOMAINS)
    def test_thresholds_are_ignored(self, domain):
        on = State(f"{domain}.source", "on")
        off = State(f"{domain}.source", "off")
        for thresholds in ((None, None), (2.0, 10.0), (100.0, 200.0)):
            assert classify_power_reading(on, *thresholds) == "on"
            assert classify_power_reading(off, *thresholds) == "off"
        # A number is not an on/off state, whatever the thresholds say.
        assert classify_power_reading(
            State(f"{domain}.source", "50"), 2.0, 10.0
        ) is None

    def test_no_state_holds(self):
        assert classify_power_reading(None, None, None) is None

    @pytest.mark.parametrize("entity_id", [
        "light.tv_backlight", "media_player.tv", "sensor.tv_power",
        "binary_sensors.typo", "switch", "",
    ])
    def test_other_domains_are_not_on_off(self, entity_id):
        assert not is_on_off_entity(entity_id)

    def test_other_domains_take_the_watts_path(self):
        # "on" from a light is not a number, so the watts path holds.
        assert classify_power_reading(State("light.x", "on"), 2.0, 10.0) is None

    def test_the_four_domains(self):
        assert set(ON_OFF_DOMAINS) == {
            "binary_sensor", "switch", "input_boolean", "device_tracker",
        }
        for domain, entity_id in SOURCES.items():
            assert is_on_off_entity(entity_id), domain

    def test_the_panel_lists_the_same_domains(self):
        source = (
            Path(__file__).parent.parent / "frontend" / "src" / "state-source.ts"
        ).read_text(encoding="utf-8")
        block = source[source.index("export const ON_OFF_DOMAINS"):]
        block = block[: block.index("];")]
        assert tuple(re.findall(r'"([a-z_]+)"', block)) == ON_OFF_DOMAINS


# ---------------------------------------------------------------------------
# A device tracker as a Device's source, through the settle window
# ---------------------------------------------------------------------------


def _tracker(state, *, seconds_from_send):
    return State(
        TRACKER, state,
        last_reported=SENT_WALL + timedelta(seconds=seconds_from_send),
    )


@pytest.fixture
def rig():
    with patch.object(pm, "_utcnow", return_value=SENT_WALL):
        made = _Rig(_device(
            power_sensor_entity_id=TRACKER,
            power_off_below_w=None,
            power_on_above_w=None,
        ))
        yield made
        made.close()


def _report(rig, state, *, seconds_from_send):
    reading = _tracker(state, seconds_from_send=seconds_from_send)
    rig.readings[TRACKER] = reading
    event = MagicMock()
    event.data = {"new_state": reading}
    rig.state_callbacks[TRACKER](event)


class TestTrackerThroughTheWindow:
    def test_the_seed_reads_the_tracker(self, rig):
        rig.readings[TRACKER] = _tracker("home", seconds_from_send=-60)
        rig.start()
        assert rig.take() == [("fan-1", "on")]

    def test_still_home_inside_the_window_is_held_then_not_home_clears_it(
        self, rig
    ):
        rig.readings[TRACKER] = _tracker("home", seconds_from_send=-60)
        rig.start()
        rig.take()

        rig.send(command_id="c-off")
        rig.loop.advance(5)
        _report(rig, "home", seconds_from_send=5)
        assert rig.take() == []

        rig.loop.advance(5)
        _report(rig, "not_home", seconds_from_send=10)
        assert rig.take() == [("fan-1", "off")]
        assert rig.monitor._windows == {}

    def test_a_tracker_that_has_not_reported_holds_at_the_window_end(
        self, rig
    ):
        rig.readings[TRACKER] = _tracker("home", seconds_from_send=-60)
        rig.start()
        rig.take()

        rig.send(command_id="c-off")
        rig.loop.advance(20)
        # Still the pre-send "home": not evidence about the send.
        assert rig.take() == []
        assert rig.monitor._windows == {}

        # The tracker catches up after the window and is dispatched.
        rig.loop.advance(100)
        _report(rig, "not_home", seconds_from_send=120)
        assert rig.take() == [("fan-1", "off")]

    def test_home_after_the_window_is_dispatched(self, rig):
        rig.readings[TRACKER] = _tracker("not_home", seconds_from_send=-60)
        rig.start()
        assert rig.take() == [("fan-1", "off")]

        rig.send(command_id="c-on")
        rig.loop.advance(20)
        assert rig.take() == []

        rig.loop.advance(40)
        _report(rig, "home", seconds_from_send=60)
        assert rig.take() == [("fan-1", "on")]

    def test_a_late_home_after_turning_off_overrules_the_send(self, rig):
        """The lag the settle help warns about: a tracker that still says
        home after the window has the last word, as a plug would."""
        rig.readings[TRACKER] = _tracker("home", seconds_from_send=-60)
        rig.start()
        rig.take()

        rig.send(command_id="c-off")
        rig.loop.advance(25)
        _report(rig, "home", seconds_from_send=25)
        assert rig.take() == [("fan-1", "on")]

    def test_a_zone_or_unavailable_reading_changes_nothing(self, rig):
        rig.readings[TRACKER] = _tracker("home", seconds_from_send=-60)
        rig.start()
        rig.take()
        for state in ("Work", "unavailable", "unknown"):
            _report(rig, state, seconds_from_send=5)
        assert rig.take() == []


# ---------------------------------------------------------------------------
# The websocket door
# ---------------------------------------------------------------------------


async def _update(fake_hass, mock_device, **fields):
    manager = MagicMock()
    manager.get_device.return_value = mock_device
    manager.async_update_device = AsyncMock(side_effect=lambda d: d)
    _wire_hass(fake_hass, manager=manager)
    conn = _make_connection()
    await ws_update_device(fake_hass, conn, {
        "id": 4, "type": "hair/device/update",
        "device_id": mock_device.id, **fields,
    })
    return conn, manager


class TestWebsocket:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity_id", sorted(SOURCES.values()))
    async def test_each_on_off_domain_is_accepted_and_thresholds_clear(
        self, fake_hass, mock_device, entity_id
    ):
        conn, _manager = await _update(
            fake_hass, mock_device,
            power_sensor_entity_id=entity_id,
            power_off_below_w=5, power_on_above_w=10, power_settle_s=60,
        )
        conn.send_result.assert_called_once()
        assert mock_device.power_sensor_entity_id == entity_id
        assert mock_device.power_off_below_w is None
        assert mock_device.power_on_above_w is None
        assert mock_device.power_settle_s == 60

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity_id", [
        "light.tv_backlight", "media_player.tv", "remote.tv", "tv",
    ])
    async def test_anything_else_is_refused(
        self, fake_hass, mock_device, entity_id
    ):
        conn, manager = await _update(
            fake_hass, mock_device, power_sensor_entity_id=entity_id,
        )
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "invalid_format"
        manager.async_update_device.assert_not_called()
        assert mock_device.power_sensor_entity_id is None

    @pytest.mark.asyncio
    async def test_a_hair_entity_is_refused(self, fake_hass, mock_device):
        registry = MagicMock()
        registry.async_get.return_value = MagicMock(platform=DOMAIN)
        with patch(
            "custom_components.hair.websocket_api.er.async_get",
            return_value=registry,
        ):
            conn, manager = await _update(
                fake_hass, mock_device,
                power_sensor_entity_id="switch.hair_bench_fan",
            )
        conn.send_error.assert_called_once()
        assert "HAIR entity" in conn.send_error.call_args[0][2]
        manager.async_update_device.assert_not_called()
        assert mock_device.power_sensor_entity_id is None

    @pytest.mark.asyncio
    async def test_an_entity_of_another_integration_is_accepted(
        self, fake_hass, mock_device
    ):
        registry = MagicMock()
        registry.async_get.return_value = MagicMock(platform="unifi")
        with patch(
            "custom_components.hair.websocket_api.er.async_get",
            return_value=registry,
        ):
            conn, _ = await _update(
                fake_hass, mock_device, power_sensor_entity_id=TRACKER,
            )
        conn.send_result.assert_called_once()
        assert mock_device.power_sensor_entity_id == TRACKER

    @pytest.mark.asyncio
    async def test_back_to_a_power_sensor_keeps_the_thresholds_sent(
        self, fake_hass, mock_device
    ):
        mock_device.power_sensor_entity_id = TRACKER
        conn, _ = await _update(
            fake_hass, mock_device,
            power_sensor_entity_id="sensor.tv_power",
            power_off_below_w=3, power_on_above_w=40,
        )
        conn.send_result.assert_called_once()
        assert mock_device.power_sensor_entity_id == "sensor.tv_power"
        assert (mock_device.power_off_below_w, mock_device.power_on_above_w) == (
            3, 40,
        )


# ---------------------------------------------------------------------------
# The settle time's ceiling: 600 s for an on/off source, 120 s for watts
# ---------------------------------------------------------------------------


class TestSettleCap:
    def test_the_caps(self):
        assert (MAX_POWER_SETTLE_S, MAX_ON_OFF_SETTLE_S) == (120.0, 600.0)
        for entity_id in SOURCES.values():
            assert max_power_settle_s(entity_id) == 600.0
        for entity_id in ("sensor.tv_power", None, "", "light.x"):
            assert max_power_settle_s(entity_id) == 120.0

    @pytest.mark.parametrize("entity_id", sorted(SOURCES.values()))
    def test_a_stored_on_off_settle_up_to_600_loads(self, entity_id):
        for value in (0, 300, 600):
            device = IRDevice.from_dict({
                "id": "d", "power_sensor_entity_id": entity_id,
                "power_settle_s": value,
            })
            assert device.power_settle_s == value
        # Over the cap is damaged: the default, never 0 and never kept.
        device = IRDevice.from_dict({
            "id": "d", "power_sensor_entity_id": entity_id,
            "power_settle_s": 601,
        })
        assert device.power_settle_s is None

    def test_a_stored_watts_settle_over_120_does_not_load(self):
        device = IRDevice.from_dict({
            "id": "d", "power_sensor_entity_id": "sensor.tv_power",
            "power_settle_s": 300,
        })
        assert device.power_settle_s is None

    def test_an_on_off_settle_survives_a_round_trip(self):
        device = IRDevice.from_dict({
            "id": "d", "power_sensor_entity_id": TRACKER,
            "power_settle_s": 300,
        })
        assert IRDevice.from_dict(device.to_dict()).power_settle_s == 300

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity_id", sorted(SOURCES.values()))
    async def test_the_websocket_takes_up_to_600_for_on_off(
        self, fake_hass, mock_device, entity_id
    ):
        conn, _ = await _update(
            fake_hass, mock_device,
            power_sensor_entity_id=entity_id, power_settle_s=600,
        )
        conn.send_result.assert_called_once()
        assert mock_device.power_settle_s == 600

    @pytest.mark.asyncio
    async def test_the_websocket_refuses_601_for_on_off(
        self, fake_hass, mock_device
    ):
        conn, manager = await _update(
            fake_hass, mock_device,
            power_sensor_entity_id=TRACKER, power_settle_s=601,
        )
        conn.send_error.assert_called_once()
        assert "from 0 to 600 seconds" in conn.send_error.call_args[0][2]
        manager.async_update_device.assert_not_called()

    @pytest.mark.asyncio
    async def test_the_websocket_still_refuses_121_for_watts(
        self, fake_hass, mock_device
    ):
        conn, manager = await _update(
            fake_hass, mock_device,
            power_sensor_entity_id="sensor.tv_power",
            power_off_below_w=3, power_on_above_w=40, power_settle_s=121,
        )
        conn.send_error.assert_called_once()
        assert "from 0 to 120 seconds" in conn.send_error.call_args[0][2]
        manager.async_update_device.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_tracker_settle_does_not_carry_to_a_power_sensor(
        self, fake_hass, mock_device
    ):
        """A save that switches to watts and sends no settle time falls
        back on the stored 300, which is over the watts cap: refused."""
        mock_device.power_sensor_entity_id = TRACKER
        mock_device.power_settle_s = 300
        conn, manager = await _update(
            fake_hass, mock_device,
            power_sensor_entity_id="sensor.tv_power",
            power_off_below_w=3, power_on_above_w=40,
        )
        conn.send_error.assert_called_once()
        manager.async_update_device.assert_not_called()
