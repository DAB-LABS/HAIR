"""The fix flow's TEST button can say HEARD.

``hair/device/tangle/test-send`` is the press the guarded write is
gated on, and the surface reuses the ordinary TEST button to make it.
That button renders SENT . HEARD off the ``heard`` field, and this
handler did not return one -- so in the fix flow the button could never
show it. Not because nothing was heard: because nobody waited for the
echo. The plumbing existed the whole way down (``_async_broadcast``
arms the Mirror audit and resolves the future); the two layers above it
simply did not carry the kwarg.

Mirrors ``ws_send_command`` exactly, including the rule that matters
most here: a send nothing hears is still a send. ``heard`` is a bonus
fact, never a condition, so the wait timing out reports
``heard: false`` and never an error -- the fix flow must not refuse a
candidate press just because the room was quiet or the receiver is
elsewhere.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRDevice
from custom_components.hair.websocket_api import ws_tangle_test_send
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")


@pytest.fixture(scope="module")
def komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture(scope="module")
def pronto(komeco) -> str:
    return next(
        c for c in komeco.climate.cells
        if cell_key(c) == "heat_cool/medium/off/24"
    ).pronto


@pytest.fixture
def wired(fake_hass, komeco):
    device = IRDevice(name="Komeco", climate_matrix=True,
                      emitter_entity_ids=["infrared.blaster"])
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=komeco.climate)
    manager.async_test_send = AsyncMock(return_value={"infrared.blaster"})
    fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
    return fake_hass, device, manager


@pytest.fixture
def instant_timeout(monkeypatch):
    """The real wait is 2 s and this suite exercises it three times.

    Patched at the module the handler imports it from, so the timeout
    path is genuinely taken -- the point is that it is taken and
    reported honestly, not how long it takes to get there.
    """
    monkeypatch.setattr(
        "custom_components.hair.wig_fitting.FITTING_HEARD_WAIT_S", 0.01
    )


async def _send(hass, device, pronto, **extra):
    connection = MagicMock()
    payload = {
        "id": 1, "type": "hair/device/tangle/test-send",
        "device_id": device.id, "pronto": pronto,
    }
    payload.update(extra)
    await ws_tangle_test_send(hass, connection, payload)
    return connection


class TestTheEchoReachesTheButton:
    @pytest.mark.asyncio
    async def test_a_heard_echo_reports_heard_and_its_receiver(
            self, wired, pronto):
        """The manager resolving the future -- the real
        _async_broadcast -> record_send -> _match_echo path, mocked
        here at the seam -- reaches the response unchanged."""
        hass, device, manager = wired

        async def _resolve(*_args, heard_future=None, **_kw):
            if heard_future is not None:
                heard_future.set_result("infrared.receiver")
            return {"infrared.blaster"}

        manager.async_test_send = AsyncMock(side_effect=_resolve)
        connection = await _send(hass, device, pronto)

        connection.send_error.assert_not_called()
        assert connection.send_result.call_args.args[1] == {
            "sent": True,
            "heard": True,
            "receiver": "infrared.receiver",
            "emitters": ["infrared.blaster"],
        }

    @pytest.mark.asyncio
    async def test_the_future_is_actually_handed_down(self, wired, pronto,
                                                      instant_timeout):
        """The defect was one missing kwarg at each of two layers. This
        pins the upper one; test_device_manager pins the lower."""
        hass, device, manager = wired
        await _send(hass, device, pronto, send_count=2)
        manager.async_test_send.assert_awaited_once_with(
            device.id, pronto, send_count=2, heard_future=ANY,
        )


class TestASendNothingHearsIsStillASend:
    @pytest.mark.asyncio
    async def test_silence_reports_heard_false_not_an_error(
            self, wired, pronto, instant_timeout):
        """The rule this handler must not get wrong. The press is the
        gate on a write; refusing it because the room was quiet would
        block a repair over a fact that was never a condition."""
        hass, device, _manager = wired
        connection = await _send(hass, device, pronto)

        connection.send_error.assert_not_called()
        payload = connection.send_result.call_args.args[1]
        assert payload["sent"] is True
        assert payload["heard"] is False
        assert payload["receiver"] is None

    @pytest.mark.asyncio
    async def test_the_emitters_field_still_rides_along(
            self, wired, pronto, instant_timeout):
        """Kept, not replaced: the fix flow's own receipts read it."""
        hass, device, _manager = wired
        connection = await _send(hass, device, pronto)
        assert connection.send_result.call_args.args[1]["emitters"] == [
            "infrared.blaster"
        ]

    @pytest.mark.asyncio
    async def test_the_response_shape_matches_send_command(
            self, wired, pronto, instant_timeout):
        """Same four keys ws_send_command answers with, plus emitters,
        so one button can read either response."""
        hass, device, _manager = wired
        connection = await _send(hass, device, pronto)
        assert set(connection.send_result.call_args.args[1]) == {
            "sent", "heard", "receiver", "emitters",
        }


class TestTheFailurePathsAreUnchanged:
    @pytest.mark.asyncio
    async def test_an_unknown_device_still_refuses(self, wired, pronto):
        hass, device, manager = wired
        manager.async_test_send = AsyncMock(side_effect=KeyError("nope"))
        connection = await _send(hass, device, pronto)
        assert connection.send_error.call_args.args[1] == "not_found"
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_dead_emitter_still_refuses(self, wired, pronto):
        """RuntimeError means nothing transmitted at all, which is a
        real failure -- unlike silence after a landed send."""
        hass, device, manager = wired
        manager.async_test_send = AsyncMock(
            side_effect=RuntimeError("all emitters unavailable"))
        connection = await _send(hass, device, pronto)
        assert connection.send_error.call_args.args[1] == "send_failed"
        connection.send_result.assert_not_called()


class TestTheManagerForwardsIt:
    """The lower of the two layers that were dropping the kwarg.

    Uses the real DeviceManager with the broadcast mocked at its own
    seam, so what is pinned is the forwarding rather than a mock of the
    thing doing the forwarding.
    """

    @pytest.fixture
    def real_manager(self, fake_hass):
        from unittest.mock import patch

        from custom_components.hair.device_manager import DeviceManager
        from custom_components.hair.entity_factory import EntityFactory
        from custom_components.hair.storage import HAIRStore

        class _FakeStore:
            def __init__(self, *args, **kwargs):
                self._data = None

            async def async_load(self):
                return self._data

            async def async_save(self, data):
                self._data = data

        with patch(
            "custom_components.hair.storage._HAIRDeviceStore", _FakeStore
        ):
            store = HAIRStore(fake_hass)
            store._loaded = True
            manager = DeviceManager(
                fake_hass, store, EntityFactory(fake_hass), "entry-1"
            )
        device = IRDevice(name="Komeco", climate_matrix=True,
                          emitter_entity_ids=["infrared.blaster"])
        store._data[device.id] = device
        manager._async_broadcast = AsyncMock(return_value={"infrared.blaster"})
        return manager, device

    @pytest.mark.asyncio
    async def test_the_kwarg_reaches_the_broadcast(self, real_manager, pronto):
        manager, device = real_manager
        sentinel = object()
        landed = await manager.async_test_send(
            device.id, pronto, heard_future=sentinel,
        )
        assert landed == {"infrared.blaster"}
        assert manager._async_broadcast.await_args.kwargs["heard_future"] is (
            sentinel
        )

    @pytest.mark.asyncio
    async def test_it_stays_optional(self, real_manager, pronto):
        """Callers that do not care keep working, and get None."""
        manager, device = real_manager
        await manager.async_test_send(device.id, pronto)
        assert manager._async_broadcast.await_args.kwargs["heard_future"] is None
