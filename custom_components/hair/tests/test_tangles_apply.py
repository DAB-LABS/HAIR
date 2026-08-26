"""The one door, and what it refuses.

Everything else in this flow reads. This writes, and it is the only
thing that does: there is no general cell editor, and there is no way to
reach a lattice cell except by naming a finding that is open against it
right now.

Three things make the door narrow. It takes a finding reference and
refuses a target with nothing wrong with it. It requires the caller to
assert that somebody pressed the button, which is RECORDED and never
verified -- the server cannot watch an air conditioner respond and must
not pretend to. And it refuses bytes that read as the wrong thing unless
the caller says out loud that they are overriding the reading, which is
what turns a frustrated user's third attempt into evidence about the map
instead of a silent bad write.

Every write leaves the bytes it replaced beside it, so the undo needs
nothing but the thing it is undoing.
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
    APPLY_DISAGREEMENT_UNDECLARED,
    APPLY_NO_FINDING,
    APPLY_NOT_TESTED,
    APPLY_NOTHING_TO_REVERT,
    PROVENANCE_KEY,
    list_tangles,
    read_repair,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply,
    ws_tangle_revert,
)
from custom_components.hair.wig_comb import CHECK_FIELD_MISMATCH
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
DREO = (FIXTURES / "wigs"
        / "dreo-fan-dr-haf004s-perfect-fit.wig.json")

TARGET_KEY = "heat_cool/medium/off/25"
TARGET = f"cell:{TARGET_KEY}"
DONOR_KEY = "heat_cool/medium/off/24"


def _wig(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture
def komeco() -> Wig:
    return _wig(KOMECO)


@pytest.fixture
def wired(fake_hass, komeco, tmp_path):
    """A Komeco device with one porthole over the target cell."""
    matrix = komeco.climate
    cells = {cell_key(c): c for c in matrix.cells}
    device = IRDevice(name="Komeco", climate_matrix=True,
                      emitter_entity_ids=["infrared.blaster"])
    device.add_command(IRCommand(
        name="Heat_cool 25 medium off", category=CommandCategory.CUSTOM,
        protocol="PRONTO", code=cells[TARGET_KEY].pronto, repeat_count=0,
        matrix_cell={"mode": "heat_cool", "fan": "medium",
                     "swing": "off", "temp": 25.0},
        comb_suspect=True, comb_finding=CHECK_FIELD_MISMATCH,
    ))
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    manager.async_update_device = AsyncMock()
    listener = MagicMock()
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "matrix_listener": listener,
    }}
    return fake_hass, device, matrix, cells, manager, listener


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _apply(hass, device, pronto, **extra):
    connection = _conn()
    payload = {
        "id": 1, "type": "hair/device/tangle/apply",
        "device_id": device.id, "target": TARGET,
        "pronto": pronto, "tested": True,
    }
    payload.update(extra)
    await ws_tangle_apply(hass, connection, payload)
    return connection


class TestTheWrite:
    @pytest.mark.asyncio
    async def test_the_bytes_land_in_the_cell(self, wired):
        hass, device, _matrix, cells, manager, _listener = wired
        donor = cells[DONOR_KEY].pronto
        connection = await _apply(hass, device, donor, source="donor")
        connection.send_error.assert_not_called()
        assert cells[TARGET_KEY].pronto == donor
        manager.async_update_device.assert_awaited()

    @pytest.mark.asyncio
    async def test_only_that_cell_moves(self, wired):
        hass, device, _matrix, cells, _manager, _listener = wired
        before = {
            key: cell.pronto for key, cell in cells.items()
            if key != TARGET_KEY
        }
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        assert {
            key: cell.pronto for key, cell in cells.items()
            if key != TARGET_KEY
        } == before

    @pytest.mark.asyncio
    async def test_the_porthole_follows_the_cell(self, wired):
        """The porthole is what TEST sends. A repair that left it behind
        would hand somebody a button still transmitting the code they
        just replaced."""
        hass, device, _matrix, cells, _manager, _listener = wired
        donor = cells[DONOR_KEY].pronto
        await _apply(hass, device, donor, source="donor")
        porthole = device.commands[0]
        assert porthole.code == donor
        assert read_repair(porthole) is not None

    @pytest.mark.asyncio
    async def test_the_record_carries_the_undo(self, wired):
        hass, device, _matrix, cells, _manager, _listener = wired
        was = cells[TARGET_KEY].pronto
        connection = await _apply(
            hass, device, cells[DONOR_KEY].pronto, source="donor")
        record = connection.send_result.call_args.args[1]["provenance"]
        assert record["prior"]["pronto"] == was
        assert record["origin"] == "fix"
        assert record["source"] == "donor"
        assert record["tested"] is True
        assert record["finding"]["key"] == TARGET_KEY
        assert record["finding"]["classes"] == [CHECK_FIELD_MISMATCH]
        assert record["map"]["id"] == "ZHLT01"
        assert record["map"]["version"]

    @pytest.mark.asyncio
    async def test_the_record_rides_the_cell_itself(self, wired):
        """Inside the cell's own extras, so it travels with the matrix
        file and into an exported wig without a format change."""
        hass, device, _matrix, cells, _manager, _listener = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        assert PROVENANCE_KEY in cells[TARGET_KEY].extra

    @pytest.mark.asyncio
    async def test_a_live_entity_is_told_the_lattice_moved(self, wired):
        """A climate entity loads its matrix once. Before repairs that
        was safe; now it is not, and the signal is the difference
        between a fixed cell and a fixed cell nobody transmits."""
        hass, device, _matrix, cells, _manager, listener = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        listener.invalidate.assert_called_once_with(device.id)

    @pytest.mark.asyncio
    async def test_the_row_leaves_the_listing(self, wired):
        hass, device, matrix, cells, _manager, _listener = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        remaining = [
            row for row in list_tangles(device, matrix).rows
            if CHECK_FIELD_MISMATCH in row.classes
        ]
        assert TARGET_KEY not in {row.target.key for row in remaining}
        assert len(remaining) == 51


class TestWhatItRefuses:
    @pytest.mark.asyncio
    async def test_without_a_press_there_is_no_write(self, wired):
        hass, device, _matrix, cells, _manager, _listener = wired
        was = cells[TARGET_KEY].pronto
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": TARGET,
            "pronto": cells[DONOR_KEY].pronto, "tested": False,
        })
        assert connection.send_error.call_args.args[1] == APPLY_NOT_TESTED
        assert cells[TARGET_KEY].pronto == was

    @pytest.mark.asyncio
    async def test_a_healthy_cell_cannot_be_edited_through_this_door(
            self, wired):
        """Not a cell editor. A target with nothing open against it is
        refused even with a perfectly good candidate in hand."""
        hass, device, _matrix, cells, _manager, _listener = wired
        healthy = "cell:cool/high/off/22"
        was = cells["cool/high/off/22"].pronto
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": healthy,
            "pronto": cells["cool/high/off/23"].pronto, "tested": True,
        })
        assert connection.send_error.call_args.args[1] == APPLY_NO_FINDING
        assert cells["cool/high/off/22"].pronto == was

    @pytest.mark.asyncio
    async def test_bytes_that_read_wrong_need_saying_so(self, wired):
        """The escalation ladder's third rung has to be DECLARED. A
        silent write of bytes our own reader disagrees with would lose
        the only evidence that our reading might be the thing at
        fault."""
        hass, device, _matrix, cells, _manager, _listener = wired
        was = cells[TARGET_KEY].pronto
        connection = await _apply(hass, device, cells[
            "heat_cool/medium/off/28"].pronto)
        assert connection.send_error.call_args.args[1] == (
            APPLY_DISAGREEMENT_UNDECLARED)
        assert cells[TARGET_KEY].pronto == was

    @pytest.mark.asyncio
    async def test_declared_disagreement_writes_and_records_the_reading(
            self, wired):
        """A remote sends what its display shows. A repeated off-by-one
        is the signature of a map defect, so the write is allowed and
        what our reader claimed is written down beside it."""
        hass, device, _matrix, cells, _manager, _listener = wired
        wrong = cells["heat_cool/medium/off/28"].pronto
        connection = await _apply(
            hass, device, wrong, reading_disagreed=True, source="capture")
        connection.send_error.assert_not_called()
        assert cells[TARGET_KEY].pronto == wrong
        record = read_repair(cells[TARGET_KEY])
        assert record["reading_disagreed"]["user_attested"] is True
        assert record["reading_disagreed"]["reads_as"]["temperature"] == 29.0
        assert record["reading_disagreed"]["claims"]["temperature"] == 25.0
        assert record["reading_disagreed"]["mismatches"] == ["temperature"]

    @pytest.mark.asyncio
    async def test_an_unusable_code_is_refused(self, wired):
        hass, device, _matrix, cells, _manager, _listener = wired
        was = cells[TARGET_KEY].pronto
        connection = await _apply(hass, device, "not a pronto code")
        assert connection.send_error.call_args.args[1] == "bad_candidate"
        assert cells[TARGET_KEY].pronto == was


class TestPuttingItBack:
    @pytest.mark.asyncio
    async def test_revert_restores_the_exact_bytes(self, wired):
        hass, device, _matrix, cells, _manager, _listener = wired
        was = cells[TARGET_KEY].pronto
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        assert cells[TARGET_KEY].pronto != was

        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": TARGET,
        })
        connection.send_error.assert_not_called()
        assert cells[TARGET_KEY].pronto == was
        assert PROVENANCE_KEY not in cells[TARGET_KEY].extra

    @pytest.mark.asyncio
    async def test_the_finding_comes_back(self, wired):
        hass, device, matrix, cells, _manager, _listener = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": TARGET,
        })
        rows = list_tangles(device, matrix).rows
        assert TARGET_KEY in {row.target.key for row in rows}

    @pytest.mark.asyncio
    async def test_the_porthole_comes_back_too(self, wired):
        hass, device, _matrix, cells, _manager, _listener = wired
        was = device.commands[0].code
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": TARGET,
        })
        assert device.commands[0].code == was

    @pytest.mark.asyncio
    async def test_nothing_to_revert_says_so(self, wired):
        hass, device, _matrix, _cells, _manager, _listener = wired
        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": TARGET,
        })
        assert connection.send_error.call_args.args[1] == (
            APPLY_NOTHING_TO_REVERT)

    @pytest.mark.asyncio
    async def test_one_step_back_and_no_further(self, wired):
        """Not a history. After a revert there is no record left, so a
        second revert has nothing to undo and says so rather than
        walking backwards through bytes nobody kept."""
        hass, device, _matrix, cells, _manager, _listener = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        for expected_error in (None, APPLY_NOTHING_TO_REVERT):
            connection = _conn()
            await ws_tangle_revert(hass, connection, {
                "id": 2, "type": "hair/device/tangle/revert",
                "device_id": device.id, "target": TARGET,
            })
            if expected_error is None:
                connection.send_error.assert_not_called()
            else:
                assert connection.send_error.call_args.args[1] == (
                    expected_error)


class TestFlatCommands:
    @pytest.fixture
    def dreo(self, fake_hass, tmp_path):
        wig = _wig(DREO)
        device = IRDevice(name="Dreo", emitter_entity_ids=["infrared.b"])
        for signal in wig.signals:
            device.add_command(IRCommand(
                name=signal.alias, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=signal.pronto,
            ))
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=None)
        manager.async_update_device = AsyncMock()
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        return fake_hass, device, manager

    @pytest.mark.asyncio
    async def test_a_flat_repair_goes_through_the_command(self, dreo):
        """Same door, same record. The persistence rides
        async_update_device so the known-command index rebuilds on the
        new bytes and the entity hooks fire."""
        hass, device, manager = dreo
        row = list_tangles(device, None).rows[0]
        clean = next(c for c in device.commands
                     if c.id != row.target.command_id).code
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": clean, "tested": True, "source": "paste",
        })
        connection.send_error.assert_not_called()
        command = device.get_command(row.target.command_id)
        assert command.code == clean
        record = read_repair(command)
        assert record["prior"]["pronto"] == row.pronto
        manager.async_update_device.assert_awaited()

    @pytest.mark.asyncio
    async def test_a_flat_revert_puts_the_capture_back(self, dreo):
        hass, device, _manager = dreo
        row = list_tangles(device, None).rows[0]
        clean = next(c for c in device.commands
                     if c.id != row.target.command_id).code
        await ws_tangle_apply(hass, _conn(), {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": clean, "tested": True, "source": "paste",
        })
        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": row.id,
        })
        connection.send_error.assert_not_called()
        assert device.get_command(row.target.command_id).code == row.pronto
