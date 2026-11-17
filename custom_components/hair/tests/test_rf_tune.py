"""Listening PR 1, the server half: tuning a radio receiver.

HAIR finds the frequency number on a receiver's own device, stamps each
capture with the band the number held when the capture arrived
(``tuned``), and sets the number from the Sniffer. The plan is HARF's
(``rf-2026-11-16-listen-picker-pr1-build-plan.md``) with Shaq's fixes,
taken: the reading of a burst's first frame stamps the press; captures
in the first 2 s after HAIR's own set are band unknown; a set is
compared after rounding to the number's step; MHz, kHz and Hz all read.
The facts are the owner's CC1101 (Proxie, 2026-11-16): a ``number`` in
MHz, step 0.005, that refuses a value in the chip's gaps by keeping its
old one.
"""
from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import rf_burst, rf_receive, rf_tune
from custom_components.hair.const import (
    RF_FREQUENCY_SOURCE_RECEIVER,
    RF_FREQUENCY_SOURCE_SIGNAL,
    RF_FREQUENCY_SOURCE_TUNED,
    RF_FREQUENCY_SOURCE_WINDOW,
)
from custom_components.hair.models import upgrade_rf_fields

RX = "radio_frequency.esp32_cc1101_rf_receiver"
NUMBER = "number.esp32_cc1101_listen_frequency"
DEVICE = "dev-cc1101"
ATHOM_RX = "radio_frequency.athom_rf_receiver"


def _state(entity_id, value, **attributes):
    return SimpleNamespace(entity_id=entity_id, state=value, attributes=attributes)


def _entry(entity_id, device_id, disabled_by=None):
    return SimpleNamespace(entity_id=entity_id, device_id=device_id, disabled_by=disabled_by)


class _Hass:
    """States, a registry and a number that behaves like the CC1101's."""

    def __init__(self, *, value="433.92", unit="MHz", extra=(), entries=None, gaps=()):
        self.states_by_id = {
            RX: _state(RX, "2026-11-16T20:00:00", device_class="receiver"),
            NUMBER: _state(NUMBER, value, unit_of_measurement=unit, step=0.005,
                           min=300, max=928),
        }
        for entity_id, state in extra:
            self.states_by_id[entity_id] = state
        self.entries = entries if entries is not None else [
            _entry(RX, DEVICE), _entry(NUMBER, DEVICE),
            _entry("number.esp32_cc1101_rx_attenuation", DEVICE),
        ]
        self.states_by_id.setdefault(
            "number.esp32_cc1101_rx_attenuation",
            _state("number.esp32_cc1101_rx_attenuation", "0", unit_of_measurement="dB"),
        )
        self.gaps = gaps
        self.listeners = []
        self.states = SimpleNamespace(get=self.states_by_id.get)
        self.calls = []
        self.services = SimpleNamespace(async_call=self._call)

    async def _call(self, domain, service, data, blocking=False):
        self.calls.append((domain, service, data))
        value = float(data["value"])
        if any(low <= value <= high for low, high in self.gaps):
            return  # the firmware refuses it: no retune, the old value stays
        old = self.states_by_id[data["entity_id"]]
        self.states_by_id[data["entity_id"]] = _state(
            data["entity_id"], f"{round(value / 0.005) * 0.005:.3f}", **old.attributes
        )
        for listener in list(self.listeners):
            listener(None)


@contextlib.contextmanager
def _rig(hass):
    registry = SimpleNamespace(async_get=lambda key: next(
        (e for e in hass.entries if e.entity_id == key), None))

    def for_device(_reg, device_id, **_kw):
        return [e for e in hass.entries if e.device_id == device_id]

    def track(_hass, _ids, action):
        hass.listeners.append(action)
        return lambda: hass.listeners.remove(action)

    with (
        patch.object(rf_tune.er, "async_get", return_value=registry),
        patch.object(rf_tune.er, "async_entries_for_device", side_effect=for_device),
        patch.object(rf_tune, "async_track_state_change_event", track),
        patch.object(rf_receive, "supported_ranges", return_value=[(300_000_000, 928_000_000)]),
    ):
        yield hass


@pytest.fixture(autouse=True)
def _fresh():
    rf_tune.reset_for_test()
    yield
    rf_tune.reset_for_test()


def _signal(frequency=None):
    return SimpleNamespace(frequency=frequency, timings=[350, -1050], modulation="ook")


# ---------------------------------------------------------------------------
# Finding the number
# ---------------------------------------------------------------------------


class TestTheNumber:
    def test_the_one_frequency_number_on_the_receivers_device(self):
        with _rig(_Hass()) as hass:
            assert rf_tune.tuning_number(hass, RX) == NUMBER

    def test_none_when_the_device_has_none(self):
        with _rig(_Hass(entries=[_entry(RX, DEVICE)])) as hass:
            assert rf_tune.tuning_number(hass, RX) is None

    def test_none_when_there_are_two(self):
        second = "number.esp32_cc1101_other_frequency"
        hass = _Hass(extra=[(second, _state(second, "315", unit_of_measurement="MHz"))])
        hass.entries.append(_entry(second, DEVICE))
        with _rig(hass):
            assert rf_tune.tuning_number(hass, RX) is None

    def test_a_disabled_number_is_not_offered(self):
        hass = _Hass()
        hass.entries[1] = _entry(NUMBER, DEVICE, disabled_by="user")
        with _rig(hass):
            assert rf_tune.tuning_number(hass, RX) is None

    def test_a_number_on_another_device_is_not_this_receivers(self):
        hass = _Hass()
        hass.entries[1] = _entry(NUMBER, "dev-elsewhere")
        with _rig(hass):
            assert rf_tune.tuning_number(hass, RX) is None

    @pytest.mark.parametrize(("value", "unit", "hz"), [
        ("433.92", "MHz", 433_920_000),
        ("433920", "kHz", 433_920_000),
        ("433920000", "Hz", 433_920_000),
    ])
    def test_its_unit_is_read(self, value, unit, hz):
        with _rig(_Hass(value=value, unit=unit)) as hass:
            assert rf_tune.number_hz(hass, NUMBER) == hz


# ---------------------------------------------------------------------------
# The stamp
# ---------------------------------------------------------------------------


class TestTheStamp:
    def test_tuned_beats_the_declared_range(self):
        with _rig(_Hass(value="433.00")) as hass:
            assert rf_receive.frequency_of(hass, RX, _signal()) == (
                433_000_000, RF_FREQUENCY_SOURCE_TUNED,
            )

    def test_the_signals_own_frequency_and_a_window_still_come_first(self):
        with _rig(_Hass(value="433.00")) as hass:
            assert rf_receive.frequency_of(hass, RX, _signal(315_000_000)) == (
                315_000_000, RF_FREQUENCY_SOURCE_SIGNAL,
            )
            hass.states_by_id[RX] = _state(
                RX, "x", device_class="receiver", capture_phase="listening",
                frequency_hz=434_000_000,
            )
            assert rf_receive.frequency_of(hass, RX, _signal()) == (
                434_000_000, RF_FREQUENCY_SOURCE_WINDOW,
            )

    @pytest.mark.parametrize("state", ["unavailable", "unknown"])
    def test_an_unavailable_number_is_band_unknown_not_433_92(self, state):
        with _rig(_Hass(value=state)) as hass, patch.object(
            rf_receive, "supported_ranges", return_value=[(433_920_000, 433_920_000)],
        ):
            assert rf_receive.frequency_of(hass, RX, _signal()) == (None, None)

    def test_a_receiver_without_a_number_is_as_before(self):
        hass = _Hass(entries=[_entry(ATHOM_RX, "dev-athom")])
        with _rig(hass), patch.object(
            rf_receive, "supported_ranges", return_value=[(433_920_000, 433_920_000)],
        ):
            assert rf_receive.frequency_of(hass, ATHOM_RX, _signal()) == (
                433_920_000, RF_FREQUENCY_SOURCE_RECEIVER,
            )

    def test_the_reading_is_the_one_taken_on_arrival(self):
        with _rig(_Hass(value="433.00")) as hass:
            stamped = rf_tune.stamp(hass, RX, _signal())
            hass.states_by_id[NUMBER] = _state(NUMBER, "315.00", unit_of_measurement="MHz")
            assert rf_receive.frequency_of(hass, RX, stamped) == (
                433_000_000, RF_FREQUENCY_SOURCE_TUNED,
            )
            assert stamped.timings == [350, -1050]  # the signal reads through

    def test_a_failure_reads_as_no_number(self):
        hass = _Hass()
        with patch.object(rf_tune.er, "async_get", side_effect=RuntimeError):
            assert rf_tune.reading(hass, RX) == rf_tune.NO_TUNING

    def test_a_row_stamped_receiver_upgrades_to_tuned_and_not_back(self):
        row = SimpleNamespace(
            rf_frequency_hz=433_920_000, rf_frequency_source=RF_FREQUENCY_SOURCE_RECEIVER,
            rf_frame_gap_source=None,
        )
        tuned = SimpleNamespace(
            rf_frequency_hz=433_000_000, rf_frequency_source=RF_FREQUENCY_SOURCE_TUNED,
            rf_frame_gap_source=None,
        )
        assert upgrade_rf_fields(row, tuned) is True
        assert (row.rf_frequency_hz, row.rf_frequency_source) == (433_000_000, "tuned")
        back = SimpleNamespace(
            rf_frequency_hz=433_920_000, rf_frequency_source=RF_FREQUENCY_SOURCE_RECEIVER,
            rf_frame_gap_source=None,
        )
        assert upgrade_rf_fields(row, back) is False


class TestABurst:
    """A press delivered one frame per capture is stamped with its first
    frame's reading, so a retune during the hold does not move it."""

    def test_the_first_frames_reading_stamps_the_press(self):
        got = []
        assembler = rf_burst.BurstAssembler(
            on_burst=lambda analysis, signal, frames, fp: got.append(signal),
            on_lone=lambda fp: None,
            call_at=lambda when, fn: MagicMock(),
            now=lambda: 0.0,
        )
        first = rf_tune.Stamped(_signal(), rf_tune.Reading(rf_tune.READING_HZ, 433_000_000))
        later = rf_tune.Stamped(_signal(), rf_tune.Reading(rf_tune.READING_HZ, 315_000_000))
        frame = (MagicMock(), MagicMock())
        with patch.object(rf_burst, "vote", return_value=MagicMock()):
            assembler.add("fp", frame, first)
            assembler.add("fp", frame, later)
            assembler.flush()
        (signal,) = got
        assert signal.hair_tuned.hz == 433_000_000

    def test_an_unstamped_burst_is_as_before(self):
        got = []
        assembler = rf_burst.BurstAssembler(
            on_burst=lambda analysis, signal, frames, fp: got.append(signal),
            on_lone=lambda fp: None,
            call_at=lambda when, fn: MagicMock(),
            now=lambda: 0.0,
        )
        plain = _signal()
        with patch.object(rf_burst, "vote", return_value=MagicMock()):
            assembler.add("fp", (MagicMock(), MagicMock()), plain)
            assembler.add("fp", (MagicMock(), MagicMock()), plain)
            assembler.flush()
        assert got == [plain]


# ---------------------------------------------------------------------------
# Setting it
# ---------------------------------------------------------------------------


class TestSetting:
    @pytest.mark.asyncio
    async def test_confirmed(self):
        with _rig(_Hass()) as hass:
            result = await rf_tune.async_tune(hass, RX, 433_000_000)
        assert result == {"result": rf_tune.TUNE_CONFIRMED, "current_mhz": 433.0}
        assert hass.calls == [("number", "set_value", {"entity_id": NUMBER, "value": 433.0})]

    @pytest.mark.asyncio
    async def test_compared_after_rounding_to_the_step(self):
        """433.9199 MHz asked; the number snaps to 433.92 and that is a yes."""
        with _rig(_Hass(value="315.00")) as hass:
            result = await rf_tune.async_tune(hass, RX, 433_919_900)
        assert result["result"] == rf_tune.TUNE_CONFIRMED
        assert result["current_mhz"] == 433.92

    @pytest.mark.asyncio
    async def test_a_value_in_the_chips_gap_did_not_change(self):
        with (
            patch.object(rf_tune, "RF_TUNE_CONFIRM_S", 0.01),
            _rig(_Hass(gaps=[(348, 387)])) as hass,
        ):
            result = await rf_tune.async_tune(hass, RX, 360_000_000)
        assert result == {"result": rf_tune.TUNE_DID_NOT_CHANGE, "current_mhz": 433.92}

    @pytest.mark.asyncio
    async def test_cannot_tune_calls_nothing(self):
        with _rig(_Hass(entries=[_entry(RX, DEVICE)])) as hass:
            result = await rf_tune.async_tune(hass, RX, 433_000_000)
        assert result["result"] == rf_tune.TUNE_CANNOT
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_a_kilohertz_number_is_set_in_its_own_unit(self):
        with _rig(_Hass(value="433920", unit="kHz")) as hass:
            await rf_tune.async_tune(hass, RX, 433_000_000)
        assert hass.calls[0][2]["value"] == pytest.approx(433_000.0)

    @pytest.mark.asyncio
    async def test_captures_just_after_hairs_own_set_are_band_unknown(self):
        with _rig(_Hass()) as hass:
            await rf_tune.async_tune(hass, RX, 433_000_000)
            assert rf_tune.reading(hass, RX) == rf_tune.UNKNOWN_BAND
            assert rf_receive.frequency_of(hass, RX, _signal()) == (None, None)
            with patch.object(rf_tune.time, "monotonic",
                              return_value=rf_tune._last_set[RX] + rf_tune.RF_TUNE_SETTLE_S):
                assert rf_tune.reading(hass, RX).hz == 433_000_000


class TestThePanel:
    def test_describe(self):
        with _rig(_Hass()) as hass:
            row = rf_tune.describe(hass, RX)
        assert row == {
            "receiver_entity_id": RX,
            "tunable": True,
            "number_entity": NUMBER,
            "available": True,
            "current_mhz": 433.92,
            "min_mhz": 300.0,
            "max_mhz": 928.0,
            "declared": [[300_000_000, 928_000_000]],
        }

    def test_describe_a_receiver_hair_cannot_tune(self):
        with _rig(_Hass(entries=[_entry(RX, DEVICE)])) as hass:
            row = rf_tune.describe(hass, RX)
        assert (row["tunable"], row["number_entity"], row["current_mhz"]) == (False, None, None)

    @pytest.mark.asyncio
    async def test_the_tune_door_refuses_what_is_not_a_receiver(self):
        from custom_components.hair.websocket_api import ws_rf_receiver_tune

        conn = MagicMock()
        with _rig(_Hass()) as hass:
            await ws_rf_receiver_tune(hass, conn, {
                "id": 1, "receiver_entity_id": NUMBER, "frequency_hz": 433_000_000,
            })
        assert conn.send_error.call_args.args[1] == "not_found"


def test_the_capture_path_stamps_each_bodied_capture_once():
    """The reading is taken in the capture handler, before the vote and
    the burst assembler see the signal, and only for a capture with a body
    (junk is not worth a registry read)."""
    import inspect

    from custom_components.hair.signal_monitor import SignalMonitor

    source = inspect.getsource(SignalMonitor)
    at = source.index("signal = stamp(self._hass, receiver_entity_id, signal)")
    assert source.index("bodied = bodied_pieces(split_frames(timings))") < at
    assert at < source.index("analysis = vote(bodied)", at)
    assert source.count("stamp(self._hass") == 1
