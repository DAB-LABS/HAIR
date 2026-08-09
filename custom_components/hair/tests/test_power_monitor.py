"""Tests for power_monitor.py -- classification and subscription lifecycle."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State

from custom_components.hair.const import DeviceType
from custom_components.hair.models import IRDevice
from custom_components.hair.power_monitor import (
    SIGNAL_POWER_VERDICT,
    PowerMonitor,
    classify_power_reading,
)


def _device(**overrides) -> IRDevice:
    defaults = dict(
        id="dev-1",
        name="Living Room Amp",
        device_type=DeviceType.MEDIA_PLAYER,
    )
    defaults.update(overrides)
    return IRDevice(**defaults)


def _state(value, unit="W", entity_id="sensor.amp_power") -> State:
    return State(entity_id, str(value), {ATTR_UNIT_OF_MEASUREMENT: unit})


class TestClassifyPowerReading:
    def test_at_or_below_off_threshold_is_off(self):
        assert classify_power_reading(_state(2), off_below_w=5, on_above_w=20) == "off"
        assert classify_power_reading(_state(5), off_below_w=5, on_above_w=20) == "off"

    def test_at_or_above_on_threshold_is_on(self):
        assert classify_power_reading(_state(20), off_below_w=5, on_above_w=20) == "on"
        assert classify_power_reading(_state(50), off_below_w=5, on_above_w=20) == "on"

    def test_hysteresis_band_holds(self):
        assert classify_power_reading(_state(10), off_below_w=5, on_above_w=20) is None

    def test_missing_thresholds_hold(self):
        assert classify_power_reading(_state(50), off_below_w=None, on_above_w=20) is None
        assert classify_power_reading(_state(50), off_below_w=5, on_above_w=None) is None
        assert classify_power_reading(_state(50), off_below_w=None, on_above_w=None) is None

    def test_none_state_holds(self):
        assert classify_power_reading(None, off_below_w=5, on_above_w=20) is None

    def test_unavailable_and_unknown_hold(self):
        s = State("sensor.amp_power", STATE_UNAVAILABLE, {})
        assert classify_power_reading(s, off_below_w=5, on_above_w=20) is None
        s = State("sensor.amp_power", STATE_UNKNOWN, {})
        assert classify_power_reading(s, off_below_w=5, on_above_w=20) is None

    def test_non_numeric_state_holds(self):
        s = State("sensor.amp_power", "not-a-number", {})
        assert classify_power_reading(s, off_below_w=5, on_above_w=20) is None

    def test_kilowatt_reading_is_converted_to_watts(self):
        s = _state(0.003, unit="kW")  # 3W -> below the 5W off threshold
        assert classify_power_reading(s, off_below_w=5, on_above_w=20) == "off"
        s = _state(0.5, unit="kW")  # 500W -> above the 20W on threshold
        assert classify_power_reading(s, off_below_w=5, on_above_w=20) == "on"


class TestPowerMonitorLifecycle:
    def _hass(self):
        hass = MagicMock()
        hass.states.get.return_value = None
        return hass

    def _store(self, *devices):
        store = MagicMock()
        store.get_all_devices.return_value = list(devices)
        by_id = {d.id: d for d in devices}
        store.get_device.side_effect = lambda device_id: by_id.get(device_id)
        return store

    def test_start_subscribes_only_devices_with_sensor_configured(self):
        hass = self._hass()
        with_sensor = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        without_sensor = _device(id="dev-2", name="Fan")
        store = self._store(with_sensor, without_sensor)

        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event"
        ) as track:
            monitor = PowerMonitor(hass, store)
            monitor.start()

        track.assert_called_once()
        args, _kwargs = track.call_args
        assert args[0] is hass
        assert args[1] == ["sensor.amp_power"]

    def test_subscribe_evaluates_current_reading_as_startup_seed(self):
        hass = self._hass()
        hass.states.get.return_value = _state(50)
        device = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device)

        with patch("custom_components.hair.power_monitor.async_track_state_change_event"), \
             patch("custom_components.hair.power_monitor.async_dispatcher_send") as send:
            monitor = PowerMonitor(hass, store)
            monitor.start()

        send.assert_called_once_with(hass, SIGNAL_POWER_VERDICT, "dev-1", "on")

    def test_startup_seed_holds_when_reading_is_ambiguous(self):
        hass = self._hass()
        hass.states.get.return_value = _state(10)  # inside hysteresis band
        device = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device)

        with patch("custom_components.hair.power_monitor.async_track_state_change_event"), \
             patch("custom_components.hair.power_monitor.async_dispatcher_send") as send:
            monitor = PowerMonitor(hass, store)
            monitor.start()

        send.assert_not_called()

    def test_rebuild_device_resubscribes_on_sensor_change(self):
        hass = self._hass()
        device = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device)
        old_unsub = MagicMock()

        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event",
            return_value=old_unsub,
        ) as track:
            monitor = PowerMonitor(hass, store)
            monitor.rebuild_device(device)

        old_unsub.assert_not_called()  # nothing to unsub yet, first subscribe
        assert track.call_count == 1

        new_unsub = MagicMock()
        device.power_sensor_entity_id = "sensor.other_power"
        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event",
            return_value=new_unsub,
        ) as track:
            monitor.rebuild_device(device)

        old_unsub.assert_called_once()
        args, _kwargs = track.call_args
        assert args[1] == ["sensor.other_power"]

    def test_rebuild_device_with_sensor_cleared_only_unsubscribes(self):
        hass = self._hass()
        device = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device)
        unsub = MagicMock()

        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event",
            return_value=unsub,
        ):
            monitor = PowerMonitor(hass, store)
            monitor.rebuild_device(device)

        device.power_sensor_entity_id = None
        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event"
        ) as track:
            monitor.rebuild_device(device)

        unsub.assert_called_once()
        track.assert_not_called()

    def test_remove_device_unsubscribes(self):
        hass = self._hass()
        device = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device)
        unsub = MagicMock()

        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event",
            return_value=unsub,
        ):
            monitor = PowerMonitor(hass, store)
            monitor.rebuild_device(device)

        monitor.remove_device("dev-1")
        unsub.assert_called_once()

    def test_stop_unsubscribes_all(self):
        hass = self._hass()
        device_a = _device(
            id="dev-1", power_sensor_entity_id="sensor.a_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        device_b = _device(
            id="dev-2", name="Heater", power_sensor_entity_id="sensor.b_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device_a, device_b)
        unsub_a, unsub_b = MagicMock(), MagicMock()

        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event",
            side_effect=[unsub_a, unsub_b],
        ):
            monitor = PowerMonitor(hass, store)
            monitor.start()

        monitor.stop()
        unsub_a.assert_called_once()
        unsub_b.assert_called_once()

    def test_state_change_callback_dispatches_verdict_on_crossing(self):
        hass = self._hass()
        device = _device(
            id="dev-1", power_sensor_entity_id="sensor.amp_power",
            power_off_below_w=5, power_on_above_w=20,
        )
        store = self._store(device)
        captured_callback = {}

        def _fake_track(hass_arg, entity_ids, callback_fn):
            captured_callback["fn"] = callback_fn
            return MagicMock()

        with patch(
            "custom_components.hair.power_monitor.async_track_state_change_event",
            side_effect=_fake_track,
        ), patch(
            "custom_components.hair.power_monitor.async_dispatcher_send"
        ) as send:
            monitor = PowerMonitor(hass, store)
            monitor.start()
            send.reset_mock()  # discard the startup-seed call (no sensor state yet)

            event = MagicMock()
            event.data = {"new_state": _state(2)}
            captured_callback["fn"](event)

        send.assert_called_once_with(hass, SIGNAL_POWER_VERDICT, "dev-1", "off")

    def test_evaluate_is_noop_for_unknown_device(self):
        hass = self._hass()
        store = self._store()  # empty
        with patch("custom_components.hair.power_monitor.async_dispatcher_send") as send:
            monitor = PowerMonitor(hass, store)
            monitor._evaluate("ghost-device", _state(50))
        send.assert_not_called()
