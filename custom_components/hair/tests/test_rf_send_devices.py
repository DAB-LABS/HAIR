"""RF send round, T2: what can be a device's emitter, and the doors.

A HAIR device sends through infrared emitters and radio transmitters,
and may hold both (owner's ruling 2026-11-06). The doors that store an
emitter list refuse anything else before writing; the Sniffer's Test
sends a row only through an emitter of its own medium; and
``hair/rf/transmitters`` lists the radio transmitters with whether each
can send a frequency, by the send path's own rule
(``agent-exchange/rf-hear/rf-send-doors.md`` sections 3 and 4).

``rf_send`` is Shaq's (T1). Until it lands these tests stand in a
module with the two functions the contract names.
"""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import emitters as em
from custom_components.hair.const import DOMAIN, MEDIUM_IR, MEDIUM_RF
from custom_components.hair.tests.test_receiver_window import (
    _entry,
    _Registry,
    _registry,
)

IR_TX = "infrared.living_room_blaster"
IR_RX = "infrared.rm4_pro_ir_receiver"
TWEEZER = "infrared.hair_tweezer"
ATHOM_TX = "radio_frequency.athom_rf_transmitter"
RM4_TX = "radio_frequency.rm4_pro_rf_transmitter"
ATHOM_RX = "radio_frequency.athom_rf_receiver"
LIGHT = "light.kitchen"
OFFLINE_TX = "radio_frequency.not_loaded_yet"


def _state(entity_id, state="2026-11-06T20:00:00+00:00", **attributes):
    return types.SimpleNamespace(entity_id=entity_id, state=state, attributes=attributes)


STATES = {
    IR_TX: _state(IR_TX, device_class="emitter", friendly_name="Living room blaster"),
    IR_RX: _state(IR_RX, device_class="receiver"),
    TWEEZER: _state(TWEEZER, device_class="emitter", hair_observer=True),
    ATHOM_TX: _state(ATHOM_TX, device_class="transmitter", friendly_name="Athom RF transmitter"),
    RM4_TX: _state(RM4_TX, state="unavailable", device_class="transmitter",
                   friendly_name="Broadlink RM4 Pro RF transmitter"),
    ATHOM_RX: _state(ATHOM_RX, device_class="receiver"),
    LIGHT: _state(LIGHT, state="on"),
}

RANGES = {
    ATHOM_TX: [(433_920_000, 433_920_000)],
    RM4_TX: [(433_050_000, 434_790_000), (314_950_000, 315_250_000)],
}


@dataclass(frozen=True)
class _Fit:
    ok: bool
    send_hz: int | None
    substituted: bool
    code: str | None


def _fit(hass, entity_id, frequency_hz):
    """The stand-in for rf_send.transmitter_fit: the plan 5.7 rule."""
    ranges = RANGES.get(entity_id) or []
    if not ranges:
        return _Fit(False, None, False, "no_ranges")
    if any(low <= frequency_hz <= high for low, high in ranges):
        return _Fit(True, frequency_hz, False, None)
    fixed = len(ranges) == 1 and ranges[0][0] == ranges[0][1]
    if fixed and abs(ranges[0][0] - frequency_hz) <= 400_000:
        return _Fit(True, ranges[0][0], True, None)
    return _Fit(False, None, False, "rf_frequency_unsupported")


@pytest.fixture(autouse=True)
def _rf_send():
    fake = types.ModuleType("custom_components.hair.rf_send")
    fake.transmitter_ranges = lambda hass, entity_id: RANGES.get(entity_id)
    fake.transmitter_fit = _fit
    import custom_components.hair as pkg

    with patch.dict(sys.modules, {"custom_components.hair.rf_send": fake}), \
            patch.object(pkg, "rf_send", fake, create=True):
        yield fake


class _Hass:
    def __init__(self, states=None):
        self._states = dict(STATES if states is None else states)
        self.states = types.SimpleNamespace(
            get=self._states.get,
            async_all=lambda domain=None: [
                s for s in self._states.values()
                if domain is None or s.entity_id.startswith(f"{domain}.")
            ],
        )
        self.data: dict = {}


def _entries():
    return [
        _entry(ATHOM_TX, "reg-athom-tx", "dev-athom"),
        _entry(RM4_TX, "reg-rm4-tx", "dev-rm4"),
    ]


def _conn():
    conn = MagicMock()
    conn.subscriptions = {}
    return conn


class TestWhatCanBeAnEmitter:
    def test_the_medium_is_the_domain(self):
        assert em.emitter_medium(IR_TX) == MEDIUM_IR
        assert em.emitter_medium(ATHOM_TX) == MEDIUM_RF
        assert em.emitter_medium(LIGHT) is None
        assert em.emitter_medium("nonsense") is None

    @pytest.mark.parametrize(("entity_id", "ok"), [
        (IR_TX, True),
        (ATHOM_TX, True),
        (RM4_TX, True),        # unavailable is still an emitter
        (OFFLINE_TX, True),    # no state yet: offline, still a valid choice
        (IR_RX, False),        # an infrared receiver
        (TWEEZER, False),      # HAIR's own observer
        (ATHOM_RX, False),     # a radio receiver
        (LIGHT, False),        # another domain
    ])
    def test_each_kind(self, entity_id, ok):
        assert (em.emitter_problem(_Hass(), entity_id) is None) is ok

    def test_a_list_is_refused_with_every_reason(self):
        code, message = em.emitters_error(_Hass(), [IR_TX, IR_RX, LIGHT])
        assert code == "invalid_emitter"
        assert IR_RX in message and LIGHT in message and IR_TX not in message
        assert em.emitters_error(_Hass(), [IR_TX, ATHOM_TX]) is None
        assert em.emitters_error(_Hass(), []) is None

    def test_of_medium_keeps_order(self):
        mixed = [ATHOM_TX, IR_TX, RM4_TX]
        assert em.of_medium(mixed, MEDIUM_RF) == [ATHOM_TX, RM4_TX]
        assert em.of_medium(mixed, MEDIUM_IR) == [IR_TX]


class TestTheTransmittersDoor:
    def _items(self, frequency_hz=None):
        from custom_components.hair.websocket_api import ws_rf_transmitters

        conn = _conn()
        msg = {"id": 1}
        if frequency_hz is not None:
            msg["frequency_hz"] = frequency_hz
        with _registry(_Registry(_entries())):
            ws_rf_transmitters(_Hass(), conn, msg)
        return conn.send_result.call_args.args[1]

    def test_every_transmitter_and_nothing_else(self):
        items = self._items()
        assert [i["entity_id"] for i in items] == [ATHOM_TX, RM4_TX]  # by name
        athom, rm4 = items
        assert athom["fixed_hz"] == 433_920_000
        assert rm4["fixed_hz"] is None
        assert rm4["ranges"] == [[433_050_000, 434_790_000], [314_950_000, 315_250_000]]
        assert (athom["available"], rm4["available"]) == (True, False)
        assert (athom["ha_device_id"], rm4["ha_device_id"]) == ("dev-athom", "dev-rm4")
        assert athom["fit"] is None and rm4["fit"] is None

    def test_the_fit_is_the_send_paths_rule(self):
        athom, rm4 = self._items(433_825_000)
        # A measured 433.825 row: the Athom is fixed at 433.92 and close
        # enough, so it sends at its own; the RM4 Pro's band takes it.
        assert athom["fit"] == {
            "ok": True, "send_hz": 433_920_000, "substituted": True, "code": None,
        }
        assert rm4["fit"] == {
            "ok": True, "send_hz": 433_825_000, "substituted": False, "code": None,
        }
        athom, rm4 = self._items(315_000_000)
        assert athom["fit"]["ok"] is False and athom["fit"]["code"] == "rf_frequency_unsupported"
        assert rm4["fit"]["ok"] is True

    def test_nothing_when_no_transmitter(self):
        from custom_components.hair.websocket_api import ws_rf_transmitters

        conn = _conn()
        ws_rf_transmitters(_Hass({IR_TX: STATES[IR_TX]}), conn, {"id": 1})
        assert conn.send_result.call_args.args[1] == []


def _data(hass, **extra):
    data = {"device_manager": MagicMock(), "store": MagicMock(), **extra}
    hass.data[DOMAIN] = {"entry": data}
    return data


class TestTheDeviceDoors:
    @pytest.mark.asyncio
    async def test_create_refuses_before_writing(self):
        from custom_components.hair.websocket_api import ws_create_device

        hass = _Hass()
        data = _data(hass)
        data["device_manager"].async_create_device = AsyncMock()
        conn = _conn()
        await ws_create_device(hass, conn, {
            "id": 1, "name": "Fan", "device_type": "fan",
            "emitter_entity_ids": [IR_TX, ATHOM_RX],
        })
        assert conn.send_error.call_args.args[1] == "invalid_emitter"
        data["device_manager"].async_create_device.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_judges_only_the_emitters_being_added(self):
        """A device that already holds an emitter HAIR cannot send
        through (an old remote.* entry) can still be saved: the picker
        hands its list back unchanged."""
        from custom_components.hair.websocket_api import ws_update_device

        hass = _Hass()
        data = _data(hass)
        device = types.SimpleNamespace(emitter_entity_ids=["remote.old_blaster", IR_TX])
        data["device_manager"].get_device.return_value = device
        conn = _conn()
        await ws_update_device(hass, conn, {
            "id": 1, "device_id": "d1",
            "emitter_entity_ids": ["remote.old_blaster", IR_TX, LIGHT],
        })
        assert conn.send_error.call_args.args[1] == "invalid_emitter"
        assert "remote.old_blaster" not in conn.send_error.call_args.args[2]
        assert device.emitter_entity_ids == ["remote.old_blaster", IR_TX]

    @pytest.mark.asyncio
    async def test_assign_new_device_refuses_before_the_monitor(self):
        from custom_components.hair.websocket_api import ws_assign_new_device

        hass = _Hass()
        monitor = MagicMock()
        monitor.assign_to_new_device = AsyncMock()
        _data(hass, signal_monitor=monitor)
        conn = _conn()
        await ws_assign_new_device(hass, conn, {
            "id": 1, "device_id": "u1", "signal_id": "s1", "device_name": "Fan",
            "device_type": "fan", "emitter_entity_ids": [TWEEZER],
            "command_name": "Power", "command_category": "custom",
        })
        assert conn.send_error.call_args.args[1] == "invalid_emitter"
        monitor.assign_to_new_device.assert_not_called()

    def test_every_door_that_stores_emitters_checks_them(self):
        """Five doors take an emitter list; each runs the check first."""
        import inspect

        from custom_components.hair import websocket_api as ws

        for name in ("ws_create_device", "ws_assign_new_device",
                     "ws_wig_make_device", "ws_trigger_remote_make_device"):
            source = inspect.getsource(getattr(ws, name))
            check = source.index("emitters_error(hass")
            assert check < source.index("_get_first_entry_data(hass)"), name
        # The update door checks after it has the device, and before it
        # writes the list.
        source = inspect.getsource(ws.ws_update_device)
        check = source.index("emitters_error(hass, added)")
        assert source.index("manager.get_device(") < check
        assert check < source.index('device.emitter_entity_ids = list(msg["emitter_entity_ids"])')


class _Remote:
    def __init__(self, rows):
        self._rows = {row.id: row for row in rows}

    def get_signal_by_id(self, signal_id):
        return self._rows.get(signal_id)


class TestTheSnifferTest:
    async def _test(self, *, signal, emitter=None, devices=()):
        from custom_components.hair.websocket_api import ws_test_signal

        hass = _Hass()
        monitor = MagicMock()
        monitor._signal_store.get_all_devices.return_value = [_Remote([signal])]
        monitor.test_signal = AsyncMock(return_value={"success": True})
        data = _data(hass, signal_monitor=monitor)
        data["store"].get_all_devices.return_value = list(devices)
        conn = _conn()
        msg = {"id": 1, "signal_id": signal.id}
        if emitter:
            msg["emitter_entity_id"] = emitter
        await ws_test_signal(hass, conn, msg)
        return conn, monitor

    @pytest.mark.asyncio
    async def test_a_radio_row_never_goes_through_an_infrared_emitter(self):
        row = types.SimpleNamespace(id="s1", medium=MEDIUM_RF)
        conn, monitor = await self._test(signal=row, emitter=IR_TX)
        assert conn.send_error.call_args.args[1] == "emitter_wrong_medium"
        monitor.test_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_nor_an_infrared_row_through_a_transmitter(self):
        row = types.SimpleNamespace(id="s1", medium=MEDIUM_IR)
        conn, monitor = await self._test(signal=row, emitter=ATHOM_TX)
        assert conn.send_error.call_args.args[1] == "emitter_wrong_medium"
        monitor.test_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_the_default_emitter_is_of_the_rows_medium(self):
        mixed = types.SimpleNamespace(emitter_entity_ids=[IR_TX, ATHOM_TX])
        row = types.SimpleNamespace(id="s1", medium=MEDIUM_RF)
        _, monitor = await self._test(signal=row, devices=[mixed])
        monitor.test_signal.assert_awaited_once_with("s1", ATHOM_TX)

        row = types.SimpleNamespace(id="s2")  # an infrared row says nothing
        _, monitor = await self._test(signal=row, devices=[mixed])
        monitor.test_signal.assert_awaited_once_with("s2", IR_TX)

    @pytest.mark.asyncio
    async def test_a_radio_row_with_no_transmitter_anywhere(self):
        ir_only = types.SimpleNamespace(emitter_entity_ids=[IR_TX])
        row = types.SimpleNamespace(id="s1", medium=MEDIUM_RF)
        conn, monitor = await self._test(signal=row, devices=[ir_only])
        assert conn.send_error.call_args.args[1] == "no_emitter"
        monitor.test_signal.assert_not_called()
