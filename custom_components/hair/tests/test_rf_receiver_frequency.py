"""One frequency row per radio receiver, and one way to set it.

``rf_receive.receiver_frequency`` gives the panel everything it draws a
receiver's frequency control from, with the form decided by the server;
``rf_tune.async_set_frequency`` sets it, by value or by preset. The four
receivers HAIR knows today map with no break:

- a windowed receiver that declares a select and its options (BroadSniff
  0.3.1): presets only, even with a frequency number on its device;
- the same with ``frequency_number`` and ``frequency_number_option``
  (0.3.2): presets plus "Other...", the number in force only while the
  select is on its option;
- a CC1101 board, which declares nothing: its number found by
  convention;
- a receiver fixed to one value (the Athom), and one that says nothing.
"""
from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import rf_receive, rf_tune

RX = "radio_frequency.rm4_pro_rf"
SELECT = "select.rm4_pro_rf_frequency"
CUSTOM = "number.rm4_pro_rf_custom_frequency"
LENGTH = "number.rm4_pro_rf_window_length"
DEVICE = "dev-rm4"
OTHER_DEVICE = "dev-other"

OPTIONS = {
    "mhz_433_92": 433_920_000,
    "mhz_315": 315_000_000,
    "sweep": "sweep",
    "custom": 390_000_000,
}


def _state(entity_id, value, **attributes):
    return SimpleNamespace(entity_id=entity_id, state=value, attributes=attributes)


def _entry(entity_id, device_id, disabled_by=None):
    return SimpleNamespace(entity_id=entity_id, device_id=device_id, disabled_by=disabled_by)


class _Hass:
    """A receiver, its select and numbers, and services that move them."""

    def __init__(self, receiver_attrs, *, option="mhz_433_92", custom="390.00",
                 entries=None, refuse=()):
        self.states_by_id = {
            RX: _state(RX, "2026-11-20T18:00:00", device_class="receiver",
                       **receiver_attrs),
            SELECT: _state(SELECT, option, options=list(OPTIONS)),
            CUSTOM: _state(CUSTOM, custom, unit_of_measurement="MHz", step=0.01,
                           min=300, max=450),
            LENGTH: _state(LENGTH, "30", unit_of_measurement="s"),
        }
        self.entries = entries if entries is not None else [
            _entry(RX, DEVICE), _entry(SELECT, DEVICE), _entry(CUSTOM, DEVICE),
            _entry(LENGTH, DEVICE),
        ]
        self.refuse = refuse
        self.listeners = []
        self.calls = []
        self.states = SimpleNamespace(get=self.states_by_id.get)
        self.services = SimpleNamespace(async_call=self._call)

    async def _call(self, domain, service, data, blocking=False):
        self.calls.append((domain, service, data))
        entity_id = data["entity_id"]
        if entity_id in self.refuse:
            return
        old = self.states_by_id[entity_id]
        value = data["option"] if domain == "select" else f"{float(data['value']):.2f}"
        self.states_by_id[entity_id] = _state(entity_id, value, **old.attributes)
        for listener in list(self.listeners):
            listener(None)


@contextlib.contextmanager
def _rig(hass, ranges=((305_000_000, 335_000_000), (433_420_000, 438_000_000))):
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
        patch.object(rf_tune, "RF_TUNE_CONFIRM_S", 0.01),
        patch.object(rf_receive, "supported_ranges", return_value=[tuple(r) for r in ranges]),
    ):
        yield hass


@pytest.fixture(autouse=True)
def _fresh():
    rf_tune.reset_for_test()
    yield
    rf_tune.reset_for_test()


def _broadsniff_031(**extra):
    return {
        "capturing": False,
        "frequency_select": SELECT,
        "frequency_options": dict(OPTIONS),
        "window_length": LENGTH,
        **extra,
    }


def _broadsniff_032(**extra):
    return _broadsniff_031(
        frequency_number=CUSTOM, frequency_number_option="custom", **extra
    )


def _signal():
    return SimpleNamespace(frequency=None, timings=[350, -1050], modulation="ook")


class TestTheForms:
    def test_a_select_and_its_options_is_presets_only(self):
        """0.3.1: the custom number on its device is not found by
        convention, because the receiver declares how it is set."""
        with _rig(_Hass(_broadsniff_031())) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "select"
        assert row["number"] is None
        assert row["select"] == SELECT
        assert [(p["option"], p["hz"], p["current"]) for p in row["presets"]] == [
            ("mhz_433_92", 433_920_000, True),
            ("mhz_315", 315_000_000, False),
            ("sweep", None, False),
            ("custom", 390_000_000, False),
        ]
        assert not any(p.get("number") for p in row["presets"])
        assert row["ranges"] == [[305_000_000, 335_000_000], [433_420_000, 438_000_000]]
        assert (row["windowed"], row["listening"], row["trusted"]) == (True, False, True)

    def test_between_windows_it_listens_at_the_selects_option(self):
        with _rig(_Hass(_broadsniff_031(), option="mhz_315")) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["now"] == {"kind": "hz", "hz": 315_000_000, "source": "select"}

    def test_a_declared_number_and_its_option_is_both(self):
        with _rig(_Hass(_broadsniff_032())) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "both"
        assert row["number"] == {
            "entity_id": CUSTOM, "min_hz": 300_000_000, "max_hz": 450_000_000,
            "step_hz": 10_000, "source": "declared",
        }
        assert [p["option"] for p in row["presets"] if p.get("number")] == ["custom"]

    def test_the_number_is_in_force_only_on_its_option(self):
        with _rig(_Hass(_broadsniff_032(), option="custom", custom="391.50")) as hass:
            on_custom = rf_receive.receiver_frequency(hass, RX)["now"]
        with _rig(_Hass(_broadsniff_032(), option="mhz_433_92", custom="391.50")) as hass:
            on_preset = rf_receive.receiver_frequency(hass, RX)["now"]
        assert on_custom == {"kind": "hz", "hz": 391_500_000, "source": "number"}
        assert on_preset == {"kind": "hz", "hz": 433_920_000, "source": "select"}

    def test_a_cc1101_declares_nothing_and_its_number_is_found(self):
        attrs = {}
        entries = [_entry(RX, DEVICE), _entry(CUSTOM, DEVICE), _entry(LENGTH, DEVICE)]
        with _rig(_Hass(attrs, entries=entries, custom="433.92"),
                  ranges=[(300_000_000, 928_000_000)]) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "number"
        assert row["number"]["source"] == "found"
        assert row["presets"] == [] and row["select"] is None
        assert row["now"] == {"kind": "hz", "hz": 433_920_000, "source": "number"}
        assert row["windowed"] is False

    def test_one_fixed_value_is_fixed(self):
        with _rig(_Hass({}, entries=[_entry(RX, DEVICE)]),
                  ranges=[(433_920_000, 433_920_000)]) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "fixed"
        assert row["now"] == {"kind": "hz", "hz": 433_920_000, "source": "fixed"}

    def test_a_receiver_that_says_nothing_is_none(self):
        with _rig(_Hass({}, entries=[_entry(RX, DEVICE)]), ranges=[]) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "none"
        assert row["now"] == {"kind": "none", "hz": None, "source": None}

    def test_a_settable_receiver_with_no_value_is_unknown(self):
        entries = [_entry(RX, DEVICE), _entry(CUSTOM, DEVICE)]
        with _rig(_Hass({}, entries=entries, custom="unavailable")) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["now"]["kind"] == "unknown"


class TestTheSafetyRule:
    def test_a_declared_number_on_another_device_is_ignored(self):
        entries = [
            _entry(RX, DEVICE), _entry(SELECT, DEVICE), _entry(CUSTOM, OTHER_DEVICE),
        ]
        with _rig(_Hass(_broadsniff_032(), entries=entries)) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert (row["form"], row["number"]) == ("select", None)
        assert not any(p.get("number") for p in row["presets"])

    def test_a_disabled_declared_number_is_ignored(self):
        entries = [
            _entry(RX, DEVICE), _entry(SELECT, DEVICE),
            _entry(CUSTOM, DEVICE, disabled_by="user"),
        ]
        with _rig(_Hass(_broadsniff_032(), entries=entries)) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "select"

    def test_a_number_option_that_is_not_an_option_is_ignored(self):
        attrs = _broadsniff_031(frequency_number=CUSTOM, frequency_number_option="nope")
        with _rig(_Hass(attrs)) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["form"] == "both"
        assert not any(p.get("number") for p in row["presets"])

    def test_a_declared_number_in_another_domain_is_ignored(self):
        attrs = _broadsniff_031(frequency_number=SELECT, frequency_number_option="custom")
        with _rig(_Hass(attrs)) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert (row["form"], row["number"]) == ("select", None)


class TestNow:
    def test_an_open_window_says_where_it_listens(self):
        attrs = _broadsniff_031(
            capturing=True, capture_phase="listening", frequency_hz=315_000_000,
        )
        with _rig(_Hass(attrs)) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["listening"] is True
        assert row["now"] == {"kind": "hz", "hz": 315_000_000, "source": "receiver"}

    def test_a_sweeping_window_sweeps(self):
        attrs = _broadsniff_031(capturing=True, capture_phase="sweeping")
        with _rig(_Hass(attrs, option="sweep")) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["now"]["kind"] == "sweep"

    def test_a_windowed_receivers_frequency_hz_between_windows_is_not_read(self):
        attrs = _broadsniff_031(frequency_hz=315_000_000)
        with _rig(_Hass(attrs, option="mhz_433_92")) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
        assert row["now"]["hz"] == 433_920_000

    def test_an_always_on_receivers_frequency_hz_is_read_in_any_phase(self):
        entries = [_entry(RX, DEVICE), _entry(CUSTOM, DEVICE)]
        attrs = {"frequency_hz": 433_420_000}
        with _rig(_Hass(attrs, entries=entries, custom="433.92")) as hass:
            row = rf_receive.receiver_frequency(hass, RX)
            stamped = rf_receive.frequency_of(hass, RX, _signal())
        assert row["now"] == {"kind": "hz", "hz": 433_420_000, "source": "receiver"}
        assert stamped[0] == 433_420_000

    def test_an_always_on_receiver_that_says_it_sweeps_is_not_read(self):
        entries = [_entry(RX, DEVICE)]
        attrs = {"frequency_hz": 433_420_000, "capture_phase": "sweeping"}
        with _rig(_Hass(attrs, entries=entries), ranges=[]) as hass:
            assert rf_receive.frequency_of(hass, RX, _signal()) == (None, None)

    def test_the_stamp_between_windows_is_the_selects_option(self):
        with _rig(_Hass(_broadsniff_031(), option="mhz_315")) as hass:
            assert rf_receive.frequency_of(hass, RX, _signal())[0] == 315_000_000

    def test_a_sweep_between_windows_stamps_band_unknown(self):
        with _rig(_Hass(_broadsniff_031(), option="sweep")) as hass:
            assert rf_receive.frequency_of(hass, RX, _signal()) == (None, None)

    def test_the_open_window_still_beats_the_select(self):
        attrs = _broadsniff_031(
            capturing=True, capture_phase="listening", frequency_hz=315_000_000,
        )
        with _rig(_Hass(attrs, option="mhz_433_92")) as hass:
            assert rf_receive.frequency_of(hass, RX, _signal())[0] == 315_000_000


class TestSetting:
    @pytest.mark.asyncio
    async def test_a_presets_value_picks_the_preset(self):
        with _rig(_Hass(_broadsniff_032(), option="mhz_315")) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, frequency_hz=433_920_000)
        assert result == {"result": "confirmed", "current_mhz": 433.92}
        assert hass.calls == [
            ("select", "select_option", {"entity_id": SELECT, "option": "mhz_433_92"}),
        ]

    @pytest.mark.asyncio
    async def test_any_other_value_sets_the_number_then_its_option(self):
        with _rig(_Hass(_broadsniff_032())) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, frequency_hz=391_500_000)
        assert result == {"result": "confirmed", "current_mhz": 391.5}
        assert hass.calls == [
            ("number", "set_value", {"entity_id": CUSTOM, "value": 391.5}),
            ("select", "select_option", {"entity_id": SELECT, "option": "custom"}),
        ]

    @pytest.mark.asyncio
    async def test_the_custom_options_own_value_sets_the_number_not_a_preset(self):
        """Custom carries the number's value; asking for it is "Other..."."""
        with _rig(_Hass(_broadsniff_032())) as hass:
            await rf_tune.async_set_frequency(hass, RX, frequency_hz=390_000_000)
        assert hass.calls[0][0] == "number"

    @pytest.mark.asyncio
    async def test_a_sweep_is_picked_by_name(self):
        with _rig(_Hass(_broadsniff_031())) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, option="sweep")
        assert result == {"result": "confirmed", "current_mhz": None}
        assert hass.calls == [
            ("select", "select_option", {"entity_id": SELECT, "option": "sweep"}),
        ]

    @pytest.mark.asyncio
    async def test_an_option_it_does_not_have_cannot_tune(self):
        with _rig(_Hass(_broadsniff_031())) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, option="mhz_868")
        assert result["result"] == "cannot_tune"
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_presets_only_and_another_value_cannot_tune(self):
        with _rig(_Hass(_broadsniff_031())) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, frequency_hz=391_500_000)
        assert result["result"] == "cannot_tune"
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_a_select_that_does_not_move_did_not_change(self):
        with _rig(_Hass(_broadsniff_031(), option="mhz_315", refuse=(SELECT,))) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, frequency_hz=433_920_000)
        assert result == {"result": "did_not_change", "current_mhz": 315.0}

    @pytest.mark.asyncio
    async def test_a_cc1101_is_set_as_before(self):
        entries = [_entry(RX, DEVICE), _entry(CUSTOM, DEVICE)]
        with _rig(_Hass({}, entries=entries)) as hass:
            result = await rf_tune.async_set_frequency(hass, RX, frequency_hz=433_000_000)
        assert result == {"result": "confirmed", "current_mhz": 433.0}
        assert hass.calls == [("number", "set_value", {"entity_id": CUSTOM, "value": 433.0})]

    @pytest.mark.asyncio
    async def test_after_a_set_the_row_is_not_trusted_for_the_settle(self):
        with _rig(_Hass(_broadsniff_031())) as hass:
            await rf_tune.async_set_frequency(hass, RX, option="mhz_315")
            assert rf_receive.receiver_frequency(hass, RX)["trusted"] is False
            assert rf_receive.frequency_of(hass, RX, _signal()) == (None, None)


class TestTheDoors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("given", [{}, {"frequency_hz": 433_920_000, "option": "sweep"}])
    async def test_the_tune_door_wants_exactly_one_of_value_and_option(self, given):
        from custom_components.hair.websocket_api import ws_rf_receiver_tune

        conn = MagicMock()
        with _rig(_Hass(_broadsniff_031())) as hass:
            await ws_rf_receiver_tune(hass, conn, {
                "id": 1, "receiver_entity_id": RX, **given,
            })
        assert conn.send_error.call_args.args[1] == "invalid_format"

    @pytest.mark.asyncio
    async def test_the_tune_door_answers_with_the_row(self):
        from custom_components.hair.websocket_api import ws_rf_receiver_tune

        conn = MagicMock()
        with _rig(_Hass(_broadsniff_031())) as hass:
            await ws_rf_receiver_tune(hass, conn, {
                "id": 1, "receiver_entity_id": RX, "option": "mhz_315",
            })
        answer = conn.send_result.call_args.args[1]
        assert answer["result"] == "confirmed"
        assert answer["row"]["presets"][1] == {
            "option": "mhz_315", "hz": 315_000_000, "current": True,
        }

    def test_the_tuning_door_carries_the_row_and_the_earlier_fields(self):
        from custom_components.hair.websocket_api import ws_rf_receiver_tuning

        conn = MagicMock()
        with (
            _rig(_Hass(_broadsniff_032())) as hass,
            patch.object(rf_receive, "rf_receiver_ids", return_value=[RX]),
        ):
            ws_rf_receiver_tuning(hass, conn, {"id": 1})
        (row,) = conn.send_result.call_args.args[1]["receivers"]
        assert row["form"] == "both"
        assert row["tunable"] is True and row["number_entity"] == CUSTOM
