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
    KEEP_NO_FINDING,
    PROVENANCE_KEY,
    list_tangles,
    read_repair,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply,
    ws_tangle_keep,
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


@pytest.fixture
def dreo(fake_hass, tmp_path):
    """A flat device built from the Dreo wig, no lattice. Module level
    since the comb-stamp class below works the same device."""
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


class TestFlatCommands:
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
class TestTheCombStampsFollowTheBytes:
    """Issue 16, ruled 2026-08-30.

    ``comb_suspect`` and ``comb_finding`` were written once at adopt,
    from the wig file's own receipt, and never looked at again. A
    command whose bytes had been repaired into perfectly good ones kept
    wearing the mark, and kept its TRIGGER button hidden, forever. The
    mark is a claim about the bytes a row is holding, and a repair
    changes the bytes underneath it.

    Re-derived from the live comb, in the same save as the write. The
    third test here matters as much as the first: a repair re-reads the
    row that was repaired and nothing else, because the adopt-time
    stamps came from the wig FILE and this reads the DEVICE, and those
    two can legitimately disagree about a row nobody has touched.
    """

    def _flagged(self, device):
        """The first open row's command, stamped as adopt leaves it:
        frozen at whatever the comb said that day."""
        row = list_tangles(device, None).rows[0]
        command = device.get_command(row.target.command_id)
        command.comb_suspect = True
        command.comb_finding = row.classes[0]
        return row, command

    @staticmethod
    def _healthy(device):
        """A command the comb has no complaint about."""
        flagged = {r.target.command_id for r in list_tangles(device, None).rows}
        return next(c for c in device.commands if c.id not in flagged)

    @staticmethod
    def _shape_preserving(pronto: str) -> str:
        """A code with the healthy family's frame shape and nobody
        else's bytes: one burst value nudged, the rest intact.
        Structurally normal, so it combs clean, and unique, so it draws
        no duplicate finding of its own."""
        words = pronto.split()
        words[20] = format(int(words[20], 16) + 4, "04X")
        return " ".join(words)

    @pytest.mark.asyncio
    async def test_bytes_that_comb_clean_clear_the_mark(self, dreo):
        """The whole point: the TRIGGER button comes back. The panel
        hides TRIGGER on a comb-flagged row, so a stamp that never
        cleared meant a repaired command could never be triggered
        again."""
        hass, device, _manager = dreo
        row, command = self._flagged(device)
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": self._shape_preserving(self._healthy(device).code),
            "tested": True, "source": "paste",
        })
        connection.send_error.assert_not_called()
        assert command.comb_suspect is False
        assert command.comb_finding is None

    @pytest.mark.asyncio
    async def test_a_repair_that_is_still_wrong_says_how(self, dreo):
        """"Fixed, and still wrong, differently" is a real outcome, and
        the tooltip should name the new class rather than the one the
        wig file recorded before anybody touched it. This repair
        borrows another command's bytes, so the row stops disagreeing
        about its frame and starts sharing a code."""
        hass, device, _manager = dreo
        row, command = self._flagged(device)
        assert command.comb_finding == "frame-disagreement"
        other = next(c for c in device.commands if c.id != command.id)
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": other.code, "tested": True, "source": "paste",
        })
        connection.send_error.assert_not_called()
        assert command.comb_suspect is True
        assert command.comb_finding == "duplicate-labels"

    @pytest.mark.asyncio
    async def test_a_command_nobody_repaired_keeps_its_own_stamps(
        self, dreo
    ):
        """THE SCOPE PIN, and it bites in the sharpest place: the
        borrow above makes the DONOR a duplicate too, so a sweep over
        every command would newly flag a command nobody touched."""
        hass, device, _manager = dreo
        row, command = self._flagged(device)
        other = next(c for c in device.commands if c.id != command.id)
        assert other.comb_suspect is False
        await ws_tangle_apply(hass, _conn(), {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": other.code, "tested": True, "source": "paste",
        })
        assert other.comb_suspect is False
        assert other.comb_finding is None

    @pytest.mark.asyncio
    async def test_the_undo_puts_the_mark_back(self, dreo):
        """A revert restores the bytes the comb doubted. Leaving the
        mark cleared would leave TRIGGER showing on a row that is
        broken again, which is issue 16 pointing the other way."""
        hass, device, _manager = dreo
        row, command = self._flagged(device)
        await ws_tangle_apply(hass, _conn(), {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": self._shape_preserving(self._healthy(device).code),
            "tested": True, "source": "paste",
        })
        assert command.comb_suspect is False
        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": row.id,
        })
        connection.send_error.assert_not_called()
        assert command.comb_suspect is True
        assert command.comb_finding == "frame-disagreement"

    @pytest.mark.asyncio
    async def test_a_porthole_is_re_read_through_its_cell(self, wired):
        """The matrix path. A porthole carries no row of its own -- the
        CELL is the row -- so its mark is looked up through the
        coordinates it stands for. This repair lands the donor's exact
        bytes, which is honestly a different problem from the one it
        started with, and the mark says so."""
        hass, device, _matrix, cells, _manager, _listener = wired
        porthole = device.commands[0]
        assert porthole.comb_finding == CHECK_FIELD_MISMATCH
        connection = await _apply(
            hass, device, cells[DONOR_KEY].pronto, source="donor")
        connection.send_error.assert_not_called()
        assert porthole.comb_suspect is True
        assert porthole.comb_finding == "duplicated-neighbour"
class TestTheRetireMomentSweep:
    """The device-proved-clean moment (owner ruled 2026-08-30).

    T1 re-reads only the rows a write touched, on purpose: the
    adopt-time stamps came from the wig FILE and a listing reads the
    DEVICE, so a repair is not licence to re-open every verdict. But
    when every bucket is empty -- no open rows anywhere, the same
    moment the section retires and the write-through fires -- the
    device has just answered the question for all of itself.

    The healthy twin is why it matters. An identical pair where one
    member was repaired leaves the OTHER still wearing a mark it
    earned only by resembling its broken partner, and nothing will
    ever touch that command again.
    """

    def _twins(self, device, listing_rows):
        """Two commands the comb flagged, one of which nothing will
        repair: the classic identical pair."""
        return [device.get_command(r.target.command_id) for r in listing_rows]

    @pytest.mark.asyncio
    async def test_the_untouched_twin_releases_when_the_device_comes_clean(
        self, dreo
    ):
        hass, device, _manager = dreo
        rows = list_tangles(device, None).rows
        assert len(rows) == 2
        first, second = self._twins(device, rows)
        for command, row in zip((first, second), rows, strict=True):
            command.comb_suspect = True
            command.comb_finding = row.classes[0]

        # Repair BOTH rows with codes that comb clean, so the last
        # write empties the section.
        healthy = next(
            c for c in device.commands
            if c.id not in {r.target.command_id for r in rows}
        )
        for index, row in enumerate(rows):
            words = healthy.code.split()
            words[20] = format(int(words[20], 16) + 4 + index, "04X")
            connection = _conn()
            await ws_tangle_apply(hass, connection, {
                "id": 1, "type": "hair/device/tangle/apply",
                "device_id": device.id, "target": row.id,
                "pronto": " ".join(words), "tested": True, "source": "paste",
            })
            connection.send_error.assert_not_called()

        assert list_tangles(device, None).rows == []
        assert first.comb_suspect is False
        assert second.comb_suspect is False

    @pytest.mark.asyncio
    async def test_nothing_is_swept_while_a_row_is_still_open(self, dreo):
        """THE RESTRAINT, still in force. One row repaired out of two
        leaves the device with work to do, and the other row's command
        keeps the mark it arrived with -- exactly T1's scope rule."""
        hass, device, _manager = dreo
        rows = list_tangles(device, None).rows
        assert len(rows) == 2
        first, second = self._twins(device, rows)
        for command, row in zip((first, second), rows, strict=True):
            command.comb_suspect = True
            command.comb_finding = row.classes[0]

        healthy = next(
            c for c in device.commands
            if c.id not in {r.target.command_id for r in rows}
        )
        words = healthy.code.split()
        words[20] = format(int(words[20], 16) + 4, "04X")
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": rows[0].id,
            "pronto": " ".join(words), "tested": True, "source": "paste",
        })
        connection.send_error.assert_not_called()

        assert list_tangles(device, None).rows
        assert first.comb_suspect is False
        assert second.comb_suspect is True
        assert second.comb_finding == rows[1].classes[0]

    @pytest.mark.asyncio
    async def test_an_answered_row_keeps_its_mark_through_the_sweep(
        self, dreo
    ):
        """ATTESTED IS NOT CLEAN. A kept row leaves the work list, so
        the section can retire with it still flagged -- and its command
        must not shed the mark and quietly get its TRIGGER back. The
        receipt carries both facts and so does the row."""
        hass, device, _manager = dreo
        rows = list_tangles(device, None).rows
        assert len(rows) == 2
        first, second = self._twins(device, rows)
        for command, row in zip((first, second), rows, strict=True):
            command.comb_suspect = True
            command.comb_finding = row.classes[0]

        # Answer both rows instead of repairing them: the section
        # retires with every finding still standing, attested.
        for row in rows:
            connection = _conn()
            await ws_tangle_keep(hass, connection, {
                "id": 1, "type": "hair/device/tangle/keep",
                "device_id": device.id, "target": row.id, "tested": True,
            })
            connection.send_error.assert_not_called()

        listing = list_tangles(device, None)
        assert listing.rows == []
        assert len(listing.attested) == 2
        assert first.comb_suspect is True
        assert second.comb_suspect is True
class TestKeepingAPairIsOneAnswer:
    """Issue 23, confirmed live on the Mitsubishi before it was built.

    Round three's KEEP BOTH settled a pair on screen and wrote nothing,
    so the duplicate-labels finding regenerated on the next listing and
    the pair came back. Renaming does not change bytes, and the comb
    reads bytes.

    Both members are answered together, through the mechanism issue 8
    already built: an attestation keyed to each row's own digest and
    the map version, which expires itself the moment either moves.
    """

    def _pair(self, device):
        rows = list_tangles(device, None).rows
        assert len(rows) == 2
        return rows

    async def _keep(self, hass, device, targets, note=None):
        connection = _conn()
        payload = {
            "id": 1, "type": "hair/device/tangle/keep",
            "device_id": device.id, "targets": targets, "tested": True,
        }
        if note is not None:
            payload["note"] = note
        await ws_tangle_keep(hass, connection, payload)
        return connection

    @pytest.mark.asyncio
    async def test_both_members_are_answered_in_one_call(self, dreo):
        hass, device, manager = dreo
        rows = self._pair(device)

        connection = await self._keep(
            hass, device, [rows[0].id, rows[1].id], note="pair-kept")

        connection.send_error.assert_not_called()
        result = connection.send_result.call_args.args[1]
        assert len(result["records"]) == 2
        assert {r["note"] for r in result["records"]} == {"pair-kept"}
        assert len(device.tangle_attestations) == 2
        # One save and one write-through for one human answer: keeping
        # them one at a time would mint a successor wig per member.
        manager.async_update_device.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_the_pair_is_gone_from_the_next_listing(self, dreo):
        """The whole point. Both rows leave the work list, and stay
        gone as long as their bytes and the map hold still."""
        hass, device, _manager = dreo
        rows = self._pair(device)

        await self._keep(hass, device, [rows[0].id, rows[1].id])

        after = list_tangles(device, None)
        assert after.rows == []
        assert len(after.attested) == 2

    @pytest.mark.asyncio
    async def test_renaming_after_the_answer_does_not_resurrect_it(
        self, dreo
    ):
        """Round three's shape, from the other side: a rename changes
        no bytes, so it cannot reopen an answer that is keyed to
        bytes."""
        hass, device, _manager = dreo
        rows = self._pair(device)
        await self._keep(hass, device, [rows[0].id, rows[1].id])

        device.get_command(rows[0].target.command_id).name = "Renamed"

        assert list_tangles(device, None).rows == []

    @pytest.mark.asyncio
    async def test_changing_the_bytes_reopens_it(self, dreo):
        """The expiry mechanism, unchanged: an attestation is about
        SOME BYTES, and different bytes are a different question. There
        is nothing scheduled and nothing swept -- the key simply stops
        matching."""
        hass, device, _manager = dreo
        rows = self._pair(device)
        await self._keep(hass, device, [rows[0].id, rows[1].id])
        assert list_tangles(device, None).rows == []

        command = device.get_command(rows[0].target.command_id)
        words = command.code.split()
        words[20] = format(int(words[20], 16) + 6, "04X")
        command.code = " ".join(words)

        assert list_tangles(device, None).rows

    @pytest.mark.asyncio
    async def test_a_target_with_no_finding_refuses_the_whole_call(
        self, dreo
    ):
        """No half-answered pairs. Everything is resolved before
        anything is stored, so a stale target takes the call down
        rather than leaving one member settled and one open."""
        hass, device, _manager = dreo
        rows = self._pair(device)

        connection = await self._keep(
            hass, device, [rows[0].id, "command:not-a-real-target"])

        assert connection.send_error.call_args.args[1] == KEEP_NO_FINDING
        assert device.tangle_attestations == []
        assert len(list_tangles(device, None).rows) == 2

    @pytest.mark.asyncio
    async def test_one_target_still_works_exactly_as_before(self, dreo):
        """Every existing caller sends a single target. The exclusive
        pair is additive precisely so none of them had to change."""
        hass, device, _manager = dreo
        rows = self._pair(device)

        connection = _conn()
        await ws_tangle_keep(hass, connection, {
            "id": 1, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": rows[0].id, "tested": True,
        })

        connection.send_error.assert_not_called()
        result = connection.send_result.call_args.args[1]
        assert result["target"] == rows[0].id
        assert result["record"]["target"] == rows[0].target.key
        assert len(device.tangle_attestations) == 1
        assert len(list_tangles(device, None).rows) == 1
