"""Reading a candidate, sending it, and hearing one from the air.

Three doors, one rule between them: NOTHING here writes. A candidate is
read, transmitted, or heard; the person watching the unit decides, and
the guarded write is somewhere else entirely.

The read-back is the point. "Invalid" tells somebody nothing; "reads as
26 degrees, and this cell claims 25" tells them exactly what they are
looking at, in the words their own remote uses.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    list_tangles,
    pre_read,
    project_device,
    read_lattice,
)
from custom_components.hair.websocket_api import (
    ws_tangle_pre_read,
    ws_tangle_test_send,
)
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
DREO = (FIXTURES / "wigs"
        / "dreo-fan-dr-haf004s-perfect-fit.wig.json")

TARGET = "heat_cool/medium/off/25"


def _wig(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture(scope="module")
def komeco() -> Wig:
    return _wig(KOMECO)


@pytest.fixture(scope="module")
def lattice(komeco):
    return read_lattice(komeco.climate)


@pytest.fixture(scope="module")
def komeco_rows(komeco):
    return {
        row.target.key: row for row in list_tangles(
            IRDevice(name="Komeco", climate_matrix=True), komeco.climate
        ).rows
    }


def _cell(komeco: Wig, key: str):
    return next(c for c in komeco.climate.cells if cell_key(c) == key)


class TestReadingACandidate:
    def test_the_right_bytes_read_as_the_label(self, lattice, komeco,
                                               komeco_rows):
        """The donor, read against the cell it is offered for."""
        row = komeco_rows[TARGET]
        verdict = pre_read(lattice, row.donor["pronto"], row.target.coordinates)
        assert verdict.matches is True
        assert verdict.mismatches == []
        assert verdict.reads_as["temperature"] == 25.0
        assert verdict.claims["temperature"] == 25.0
        assert verdict.protocol == "ZHLT01"

    def test_the_wrong_bytes_say_what_they_actually_are(self, lattice,
                                                        komeco, komeco_rows):
        """Never just "invalid". The user pressed 18 when we asked for
        19, and the only useful thing to tell them is which one we
        heard."""
        row = komeco_rows[TARGET]
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        verdict = pre_read(lattice, wrong.pronto, row.target.coordinates)
        assert verdict.matches is False
        assert verdict.mismatches == ["temperature"]
        assert verdict.reads_as["temperature"] == 29.0
        assert verdict.claims["temperature"] == 25.0

    def test_a_row_carries_what_its_own_bytes_say(self, komeco_rows):
        """"says Heat 26, will say Heat 25" comes from here."""
        verdict = komeco_rows[TARGET].verdict
        assert verdict["reads_as"]["temperature"] == 26.0
        assert verdict["claims"]["temperature"] == 25.0
        assert verdict["matches"] is False

    def test_integrity_rides_the_same_line(self, lattice, komeco_rows):
        """The map's own checksum, on the candidate. A rule that cannot
        be evaluated is None here and never a pass."""
        row = komeco_rows[TARGET]
        verdict = pre_read(lattice, row.donor["pronto"], row.target.coordinates)
        assert verdict.integrity == {"complement_pairs": True}

    def test_no_target_means_no_verdict_about_a_claim(self, lattice, komeco):
        """Read the bytes, report them, claim nothing. matches stays
        None rather than becoming a False nobody can justify."""
        verdict = pre_read(lattice, _cell(komeco, "cool/high/off/22").pronto)
        assert verdict.matches is None
        assert verdict.mismatches == []
        assert verdict.reads_as["temperature"] == 22.0
        assert verdict.claims == {}

    def test_unreadable_bytes_decline_rather_than_guess(self, lattice):
        verdict = pre_read(
            lattice, "0000 006D 0004 0000 0060 0020 0020 0020 0020 0060")
        assert verdict.protocol is None
        assert verdict.declined
        assert verdict.reads_as == {}


class TestTheFrameCheckRidesAlong:
    def test_a_noisy_candidate_carries_its_vote(self, lattice):
        """R1's check, on the candidate itself. A capture whose repeats
        disagree is a bad capture whatever it reads as."""
        dreo = _wig(DREO)
        noisy = next(s for s in dreo.signals
                     if s.alias == "Oscillate Horizontal")
        verdict = pre_read(lattice, noisy.pronto)
        assert verdict.frame_vote is not None
        assert verdict.frame_vote["frames"] > 1

    def test_a_clean_candidate_carries_none(self, lattice, komeco):
        verdict = pre_read(lattice, _cell(komeco, "cool/high/off/22").pronto)
        assert verdict.frame_vote is None


class TestFlatCommands:
    def test_a_flat_row_still_gets_read(self):
        """No lattice, so no label to check against -- but the frame
        vote and the decoded identity are the read-back a flat command
        has, and both still arrive."""
        dreo = _wig(DREO)
        device = IRDevice(name="Dreo")
        for signal in dreo.signals:
            device.add_command(IRCommand(
                name=signal.alias, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=signal.pronto,
            ))
        rows = list_tangles(device, None).rows
        assert rows
        for row in rows:
            assert row.verdict["matches"] is None
            assert row.verdict["frame_vote"] is not None

    def test_the_flat_read_uses_the_same_family_vote(self):
        """A single code matching one map by coincidence must not name a
        family for a whole remote -- R2's bench find, and it applies to
        a device exactly as it applies to a file."""
        dreo = _wig(DREO)
        device = IRDevice(name="Dreo")
        for signal in dreo.signals:
            device.add_command(IRCommand(
                name=signal.alias, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=signal.pronto,
            ))
        wig, _sources = project_device(device, None)
        assert read_lattice(None, wig).field_map is None


class TestOverTheWire:
    @pytest.fixture
    def wired(self, fake_hass, komeco):
        device = IRDevice(name="Komeco", climate_matrix=True,
                          emitter_entity_ids=["infrared.blaster"])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=komeco.climate)
        manager.async_test_send = AsyncMock(
            return_value={"infrared.blaster"})
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        return fake_hass, device, manager

    @pytest.mark.asyncio
    async def test_pre_read_over_the_wire(self, wired, komeco):
        hass, device, _manager = wired
        donor = _cell(komeco, "heat_cool/medium/off/24")
        connection = MagicMock()
        await ws_tangle_pre_read(hass, connection, {
            "id": 1, "type": "hair/device/tangle/pre-read",
            "device_id": device.id, "pronto": donor.pronto,
            "target": f"cell:{TARGET}",
        })
        connection.send_error.assert_not_called()
        payload = connection.send_result.call_args.args[1]
        assert payload["matches"] is True
        assert payload["reads_as"]["temperature"] == 25.0

    @pytest.mark.asyncio
    async def test_a_target_with_no_finding_is_refused(self, wired, komeco):
        """The pre-read is part of a repair, and there is no repair for
        a cell nothing is wrong with."""
        hass, device, _manager = wired
        connection = MagicMock()
        await ws_tangle_pre_read(hass, connection, {
            "id": 1, "type": "hair/device/tangle/pre-read",
            "device_id": device.id,
            "pronto": _cell(komeco, "cool/high/off/22").pronto,
            "target": "cell:cool/high/off/22",
        })
        connection.send_result.assert_not_called()
        assert connection.send_error.call_args.args[1] == "unknown_target"

    @pytest.mark.asyncio
    async def test_test_send_transmits_and_saves_nothing(self, wired, komeco):
        hass, device, manager = wired
        donor = _cell(komeco, "heat_cool/medium/off/24")
        connection = MagicMock()
        await ws_tangle_test_send(hass, connection, {
            "id": 1, "type": "hair/device/tangle/test-send",
            "device_id": device.id, "pronto": donor.pronto, "send_count": 1,
        })
        connection.send_error.assert_not_called()
        assert connection.send_result.call_args.args[1]["sent"] is True
        manager.async_test_send.assert_awaited_once()
        manager.async_update_device.assert_not_called()
        assert not device.commands

    @pytest.mark.asyncio
    async def test_a_device_with_no_emitters_says_so(self, wired, komeco):
        hass, device, manager = wired
        manager.async_test_send = AsyncMock(
            side_effect=RuntimeError("Device x has no emitters configured"))
        connection = MagicMock()
        await ws_tangle_test_send(hass, connection, {
            "id": 1, "type": "hair/device/tangle/test-send",
            "device_id": device.id,
            "pronto": _cell(komeco, "cool/high/off/22").pronto,
        })
        connection.send_result.assert_not_called()
        assert connection.send_error.call_args.args[1] == "send_failed"


class TestListeningIntoContext:
    """The same listen path, aimed at a target.

    The R1 notice, the Mirror filter and the timeout are all the shared
    path's, unchanged. What is added is the read-back against the cell
    the capture was aimed at, so a surface can answer "heard it: 25
    degrees" or "heard 29" without a second round trip.

    This class used to open by saying one capture per arm, which was
    true of the shared path and wrong for this caller: the mismatch
    ladder counts misses on ONE arm, so the fix flow's window stays
    open. See test_tangle_listen_fixes.py, which pins that and the
    reason it was not noticed here.
    """

    class _Monitor:
        def __init__(self):
            self.subscribers = []

        def subscribe(self, cb):
            self.subscribers.append(cb)

        def unsubscribe(self, cb):
            if cb in self.subscribers:
                self.subscribers.remove(cb)

        def emit(self, summary):
            for cb in list(self.subscribers):
                cb(summary)

    @staticmethod
    def _store(pronto):
        signal = MagicMock()
        signal.code = pronto
        signal.protocol = "PRONTO"
        signal.decoded_fingerprint = None
        signal.decoded_protocol = None
        signal.heard_by = ["infrared.receiver"]
        device = MagicMock()
        device.get_signal_by_id = MagicMock(return_value=signal)
        store = MagicMock()
        store.get_device = MagicMock(return_value=device)
        return store

    async def _arm(self, fake_hass, komeco, pronto, target=None):
        from custom_components.hair.websocket_api import ws_tangle_listen

        device = IRDevice(name="Komeco", climate_matrix=True,
                          emitter_entity_ids=["infrared.blaster"])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=komeco.climate)
        monitor = self._Monitor()
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": manager,
            "signal_monitor": monitor,
            "signal_store": self._store(pronto),
        }}
        connection = MagicMock()
        connection.subscriptions = {}
        msg = {"id": 9, "type": "hair/device/tangle/listen",
               "device_id": device.id}
        if target:
            msg["target"] = target
        await ws_tangle_listen(fake_hass, connection, msg)
        return connection, monitor

    @pytest.mark.asyncio
    async def test_a_right_press_reads_back_as_the_label(self, fake_hass,
                                                         komeco):
        donor = _cell(komeco, "heat_cool/medium/off/24")
        connection, monitor = await self._arm(
            fake_hass, komeco, donor.pronto, f"cell:{TARGET}")
        assert connection.send_result.call_args.args[1] == {"listening": True}

        monitor.emit({"device_id": "d", "device_fingerprint": "f",
                      "signal_id": "s", "protocol": "PRONTO",
                      "code": donor.pronto})
        event = connection.send_event.call_args.args[1]
        assert event["type"] == "tangle_capture"
        assert event["target"] == f"cell:{TARGET}"
        assert event["verdict"]["matches"] is True
        assert event["verdict"]["reads_as"]["temperature"] == 25.0

    @pytest.mark.asyncio
    async def test_a_wrong_press_says_what_it_heard(self, fake_hass, komeco):
        """The 19-heard-as-18 case. The capture is parked, not armed,
        and the surface has the number it needs to say so."""
        wrong = _cell(komeco, "heat_cool/medium/off/28")
        connection, monitor = await self._arm(
            fake_hass, komeco, wrong.pronto, f"cell:{TARGET}")
        monitor.emit({"device_id": "d", "device_fingerprint": "f",
                      "signal_id": "s", "protocol": "PRONTO",
                      "code": wrong.pronto})
        verdict = connection.send_event.call_args.args[1]["verdict"]
        assert verdict["matches"] is False
        assert verdict["reads_as"]["temperature"] == 29.0

    @pytest.mark.asyncio
    async def test_an_unaimed_listen_still_reads(self, fake_hass, komeco):
        cell = _cell(komeco, "cool/high/off/22")
        connection, monitor = await self._arm(
            fake_hass, komeco, cell.pronto)
        monitor.emit({"device_id": "d", "device_fingerprint": "f",
                      "signal_id": "s", "protocol": "PRONTO",
                      "code": cell.pronto})
        event = connection.send_event.call_args.args[1]
        assert "target" not in event
        assert event["verdict"]["matches"] is None
        assert event["verdict"]["reads_as"]["temperature"] == 22.0

    @pytest.mark.asyncio
    async def test_the_capture_notice_still_rides(self, fake_hass, komeco):
        """R1's warn-and-allow line is not replaced by the read-back;
        both facts reach the surface together."""
        noisy = next(s for s in _wig(DREO).signals
                     if s.alias == "Oscillate Horizontal")
        connection, monitor = await self._arm(
            fake_hass, komeco, noisy.pronto, f"cell:{TARGET}")
        monitor.emit({"device_id": "d", "device_fingerprint": "f",
                      "signal_id": "s", "protocol": "PRONTO",
                      "code": noisy.pronto})
        event = connection.send_event.call_args.args[1]
        assert event["repeats_disagree"]["frames"] > 1
        assert event["verdict"]["frame_vote"]["frames"] > 1
