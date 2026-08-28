"""Two bench findings on the fix flow's LISTEN, both real.

Found in window 2 with hardware in the room, confirmed in source by
review, and both of the kind that only a real press exposes: the code
was self-consistent and the tests around it passed.

ONE. The listen subscription was single-shot. ``_finish()`` unsubscribed
after the first forwarded capture, so one arm delivered one capture --
and the mismatch ladder counts misses on ONE arm. Hear 18 when 19 was
asked for, say so; hear it again, say so again; on the third, offer USE
IT ANYWAY, the rung that admits our reading may be at fault rather than
the remote. That third rung was unreachable through real presses no
matter how many times somebody pressed, because after the first there
was nobody listening.

TWO. ``decoded`` meant the wrong thing. It was
``bool(decoded_fingerprint)`` -- the GENERAL protocol classifier, which
does not recognise AC protocols like ZHLT01 at all -- while the very
same event carried a field-tier verdict that had read the press
perfectly. The surface obeys the flag, so a byte-perfect press rendered
"came through garbled". Any device on a map-read protocol could never
capture cleanly.

Neither needed a frontend change. Both were the backend telling the
truth about the wrong question.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRDevice
from custom_components.hair.websocket_api import (
    ws_command_listen,
    ws_tangle_listen,
)
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

#: A cell whose label the fix flow would aim a press at.
TARGET = "heat_cool/medium/off/25"


@pytest.fixture(scope="module")
def komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


def _cell(wig: Wig, key: str):
    return next(c for c in wig.climate.cells if cell_key(c) == key)


class _Monitor:
    """The signal monitor's subscriber feed, as much as is needed."""

    def __init__(self) -> None:
        self.subscribers: list = []

    def subscribe(self, cb) -> None:
        self.subscribers.append(cb)

    def unsubscribe(self, cb) -> None:
        if cb in self.subscribers:
            self.subscribers.remove(cb)

    def emit(self, summary) -> None:
        for cb in list(self.subscribers):
            cb(summary)


class _Store:
    """A signal store whose next capture is whatever was last set.

    One store, many presses: the point of half these tests is that a
    second and third press reach the same armed listener, so the store
    has to be able to answer differently each time.
    """

    def __init__(self, pronto: str) -> None:
        self.pronto = pronto
        self.decoded_fingerprint = None

    def get_device(self, _device_id):
        signal = MagicMock()
        signal.code = self.pronto
        signal.protocol = "PRONTO"
        signal.decoded_fingerprint = self.decoded_fingerprint
        signal.decoded_protocol = None
        signal.heard_by = ["infrared.receiver"]
        device = MagicMock()
        device.get_signal_by_id = MagicMock(return_value=signal)
        return device


class _Timer:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def _wire(fake_hass, komeco, pronto):
    device = IRDevice(name="Komeco", climate_matrix=True,
                      emitter_entity_ids=["infrared.blaster"])
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=komeco.climate)
    monitor = _Monitor()
    store = _Store(pronto)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager,
        "signal_monitor": monitor,
        "signal_store": store,
    }}
    timers: list[_Timer] = []

    def _call_later(_delay, callback):
        timer = _Timer()
        timer.callback = callback
        timers.append(timer)
        return timer

    fake_hass.loop = MagicMock()
    fake_hass.loop.call_later = MagicMock(side_effect=_call_later)
    return device, monitor, store, timers


def _conn():
    connection = MagicMock()
    connection.subscriptions = {}
    return connection


def _press(monitor):
    monitor.emit({"device_id": "d", "device_fingerprint": "f",
                  "signal_id": "s", "protocol": "PRONTO"})


def _events(connection):
    return [call.args[1] for call in connection.send_event.call_args_list]


async def _arm_tangle(fake_hass, connection, device, target=TARGET):
    msg = {"id": 9, "type": "hair/device/tangle/listen",
           "device_id": device.id}
    if target:
        msg["target"] = f"cell:{target}"
    await ws_tangle_listen(fake_hass, connection, msg)


class TestTheLadderCanClimb:
    """Three misses on one arm, which is what USE IT ANYWAY costs."""

    @pytest.mark.asyncio
    async def test_three_mismatched_presses_all_forward(self, fake_hass,
                                                        komeco):
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        device, monitor, _store, _timers = _wire(
            fake_hass, komeco, wrong.pronto)
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)
        assert connection.send_result.call_args.args[1] == {"listening": True}

        for _ in range(3):
            _press(monitor)

        events = _events(connection)
        assert len(events) == 3, "the ladder never gets past its first rung"
        for event in events:
            assert event["type"] == "tangle_capture"
            assert event["verdict"]["matches"] is False
            assert event["verdict"]["reads_as"]["temperature"] == 29.0

    @pytest.mark.asyncio
    async def test_the_listener_is_still_subscribed_between_presses(
            self, fake_hass, komeco):
        """The mechanism, not just the count. A window that forwarded
        three events while unsubscribing would be a different bug."""
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        device, monitor, _store, _timers = _wire(
            fake_hass, komeco, wrong.pronto)
        await _arm_tangle(fake_hass, _conn(), device)
        assert len(monitor.subscribers) == 1
        _press(monitor)
        assert len(monitor.subscribers) == 1

    @pytest.mark.asyncio
    async def test_the_presses_can_differ(self, fake_hass, komeco):
        """A real ladder is somebody trying again, not the same event
        replayed: the second press reads as its own reading."""
        device, monitor, store, _timers = _wire(
            fake_hass, komeco, _cell(komeco, "heat_cool/medium/off/28").pronto)
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        _press(monitor)
        store.pronto = _cell(komeco, "heat_cool/medium/off/24").pronto
        _press(monitor)

        reads = [e["verdict"]["reads_as"]["temperature"]
                 for e in _events(connection)]
        assert reads == [29.0, 25.0]

    @pytest.mark.asyncio
    async def test_each_press_gets_a_fresh_silence_window(self, fake_hass,
                                                          komeco):
        """The timeout is a silence window, not a total budget. A
        ladder that lost its listener because somebody paused between
        presses would fail the way the single-shot bug failed."""
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        device, monitor, _store, timers = _wire(
            fake_hass, komeco, wrong.pronto)
        await _arm_tangle(fake_hass, _conn(), device)
        assert len(timers) == 1

        _press(monitor)
        assert timers[0].cancelled is True
        assert len(timers) == 2
        assert timers[1].cancelled is False


class TestItStillEndsWhenItShould:
    """Open-ended is not the same as never closing."""

    @pytest.mark.asyncio
    async def test_the_timeout_still_tears_it_down(self, fake_hass, komeco):
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        device, monitor, _store, timers = _wire(
            fake_hass, komeco, wrong.pronto)
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        _press(monitor)
        timers[-1].callback()

        assert monitor.subscribers == []
        assert _events(connection)[-1] == {"type": "tangle_listen_timeout"}
        _press(monitor)
        assert len(_events(connection)) == 2, "a torn-down window forwarded"

    @pytest.mark.asyncio
    async def test_the_client_can_unsubscribe(self, fake_hass, komeco):
        """Cancel, or simply closing the dialog. The subscription is
        registered for exactly this and it still is."""
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        device, monitor, _store, _timers = _wire(
            fake_hass, komeco, wrong.pronto)
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        assert 9 in connection.subscriptions
        connection.subscriptions[9]()
        assert monitor.subscribers == []
        _press(monitor)
        assert _events(connection) == []


class TestTheOtherListenersAreUnchanged:
    """One flag, one surface. The command editor's Replace box holds
    one code, so its window is still one capture and done."""

    @pytest.mark.asyncio
    async def test_the_command_editor_stays_single_shot(self, fake_hass,
                                                        komeco):
        donor = _cell(komeco, "heat_cool/medium/off/24")
        _device, monitor, _store, _timers = _wire(
            fake_hass, komeco, donor.pronto)
        connection = _conn()
        ws_command_listen(fake_hass, connection,
                          {"id": 4, "type": "hair/command/listen"})

        _press(monitor)
        _press(monitor)

        assert len(_events(connection)) == 1
        assert monitor.subscribers == []


class TestDecodedMeansReadable:
    """The flag the surface renders "garbled" from."""

    @pytest.mark.asyncio
    async def test_a_map_read_capture_arrives_decoded(self, fake_hass,
                                                      komeco):
        """The whole bug in one assertion. This capture is a real
        ZHLT01 frame: the general classifier gives it no fingerprint
        (decoded_fingerprint is None, exactly as on the bench) and the
        field tier reads it perfectly. Before the fix it arrived
        decoded false and rendered as garbage."""
        donor = _cell(komeco, "heat_cool/medium/off/24")
        device, monitor, store, _timers = _wire(
            fake_hass, komeco, donor.pronto)
        assert store.decoded_fingerprint is None
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        _press(monitor)
        event = _events(connection)[0]
        assert event["decoded"] is True
        assert event["verdict"]["protocol"] == "ZHLT01"
        assert event["verdict"]["reads_as"]["temperature"] == 25.0

    @pytest.mark.asyncio
    async def test_a_mismatched_press_is_still_decoded(self, fake_hass,
                                                       komeco):
        """Readable is not the same as right. A press that reads as the
        wrong temperature came through perfectly well, and the ladder
        depends on saying which number it heard."""
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        device, monitor, _store, _timers = _wire(
            fake_hass, komeco, wrong.pronto)
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        _press(monitor)
        event = _events(connection)[0]
        assert event["decoded"] is True
        assert event["verdict"]["matches"] is False

    @pytest.mark.asyncio
    async def test_the_general_classifier_still_counts(self, fake_hass,
                                                       komeco):
        """OR, not instead of. A code the classifier recognises is
        decoded whatever the field tier makes of it."""
        donor = _cell(komeco, "heat_cool/medium/off/24")
        device, monitor, store, _timers = _wire(
            fake_hass, komeco, donor.pronto)
        store.decoded_fingerprint = "nec:0x20df:0x10ef"
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        _press(monitor)
        assert _events(connection)[0]["decoded"] is True

    @pytest.mark.asyncio
    async def test_something_neither_reader_knows_is_not_decoded(
            self, fake_hass, komeco):
        """The flag still means something. Widening it to "readable"
        must not quietly widen it to "always true", or the surface
        loses the only way it has to say a capture came through badly.
        """
        device, monitor, _store, _timers = _wire(
            fake_hass, komeco,
            "0000 006D 0004 0000 0060 0018 0018 0018 0018 0018 0018 0018")
        connection = _conn()
        await _arm_tangle(fake_hass, connection, device)

        _press(monitor)
        event = _events(connection)[0]
        assert event["decoded"] is False
        assert event["verdict"]["protocol"] is None
