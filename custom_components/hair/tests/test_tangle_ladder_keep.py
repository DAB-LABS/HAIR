"""What USE IT ANYWAY leaves behind.

Issue 8 of the detangler round, reproduced by the owner on the practice
AC 2026-08-29: the ladder settled a row, and closing and reopening the
device brought the same row back as a LISTEN ask. Worse, the pulled
command beside it read REPAIRED while the tangle row asked again, so
the two surfaces disagreed about a question the person had already
answered.

Nothing was broken in the write. The bytes landed, the porthole
followed, the wig was updated. What was missing is that the finding is
DERIVED: the next listing re-combs the file, reads the same disputed
value out of the same bytes, and files the same finding, because
nothing anywhere remembered that a person had looked at it and said
keep it.

That memory already exists and is called an attestation. The keep
endpoint writes one; this makes the ladder's third rung write the same
record, keyed to the bytes it just wrote, so it expires on its own the
moment those bytes or the map that doubted them move.
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
    ATTEST_LADDER_OVERRIDE,
    build_attestation,
    list_tangles,
    project_device,
    read_lattice,
    read_repair,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply,
    ws_tangle_revert,
)
from custom_components.hair.wig_comb import CHECK_FIELD_MISMATCH
from custom_components.hair.wig_format import (
    Wig,
    cell_key,
    parse_wig,
    row_digest,
)

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

TARGET_KEY = "heat_cool/medium/off/25"
TARGET = f"cell:{TARGET_KEY}"
#: One step BELOW the target: this cell's bytes read as the target's own
#: label, which is what a donor repair copies and what reads clean.
CLEAN_KEY = "heat_cool/medium/off/24"
#: One step ABOVE: these bytes read as 27 against a cell claiming 25, so
#: the disagreement survives the write. That is the ladder's case.
DISPUTED_KEY = "heat_cool/medium/off/26"


@pytest.fixture
def komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


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
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "matrix_listener": MagicMock(),
    }}
    return fake_hass, device, matrix, cells


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
    connection.send_error.assert_not_called()
    return connection.send_result.call_args.args[1]


def _rows(device, matrix):
    listing = list_tangles(device, matrix)
    return (
        {row["id"] for row in listing.as_dict()["rows"]},
        {row["id"] for row in listing.as_dict()["attested"]},
    )


class TestTheOverrideIsRemembered:
    @pytest.mark.asyncio
    async def test_the_apply_records_an_attestation(self, wired):
        hass, device, _matrix, cells = wired
        result = await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        assert result["verdict"]["matches"] is False
        assert result["attested"] is not None
        assert len(device.tangle_attestations) == 1

    @pytest.mark.asyncio
    async def test_the_row_leaves_the_work_list(self, wired):
        """The defect itself. Reopening the device used to bring the
        same ask straight back."""
        hass, device, matrix, cells = wired
        open_before, _ = _rows(device, matrix)
        assert f"cell:{TARGET_KEY}" in open_before
        await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        open_after, answered = _rows(device, matrix)
        assert f"cell:{TARGET_KEY}" not in open_after
        assert f"cell:{TARGET_KEY}" in answered

    @pytest.mark.asyncio
    async def test_the_two_surfaces_agree_afterwards(self, wired):
        """The owner's extra wrinkle: the pulled command read REPAIRED
        while the tangle row asked again. Both now say settled."""
        hass, device, matrix, cells = wired
        await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        porthole = device.commands[0]
        assert read_repair(porthole) is not None
        open_after, answered = _rows(device, matrix)
        assert f"cell:{TARGET_KEY}" not in open_after
        assert f"cell:{TARGET_KEY}" in answered

    @pytest.mark.asyncio
    async def test_the_finding_itself_is_untouched(self, wired):
        """Attested is not clean, and has to keep reading as one. The
        answered row still carries the finding it answers."""
        hass, device, matrix, cells = wired
        await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        listing = list_tangles(device, matrix).as_dict()
        row = next(
            r for r in listing["attested"] if r["id"] == f"cell:{TARGET_KEY}"
        )
        assert CHECK_FIELD_MISMATCH in row["classes"]
        assert row["attested"]["note"] == ATTEST_LADDER_OVERRIDE


class TestWhatTheRecordSays:
    @pytest.mark.asyncio
    async def test_the_note_marks_the_road_it_came_down(self, wired):
        """A KEEP says the finding is wrong about these bytes. This says
        the person heard the disputed value and is keeping it anyway.
        Same standing, and a later reader should be able to tell them
        apart."""
        hass, device, _matrix, cells = wired
        result = await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        assert result["attested"]["note"] == ATTEST_LADDER_OVERRIDE

    @pytest.mark.asyncio
    async def test_it_is_keyed_to_the_bytes_just_written(self, wired):
        """Not to the bytes it replaced. An answer keyed to the old
        digest would expire the instant it was recorded, which is the
        same nagging with extra steps."""
        hass, device, _matrix, cells = wired
        written = cells[DISPUTED_KEY].pronto
        result = await _apply(
            hass, device, written, source="capture", reading_disagreed=True,
        )
        assert result["attested"]["digest"] == row_digest(written, 0, False)
        assert cells[TARGET_KEY].pronto == written

    @pytest.mark.asyncio
    async def test_it_is_the_keep_endpoint_s_own_record(self, wired):
        """Same record, from the same builder, so one reader
        understands both roads and the receipt carries one shape."""
        hass, device, matrix, cells = wired
        listing = list_tangles(device, matrix)
        wig, _sources = project_device(device, matrix)
        lattice = read_lattice(matrix, wig)
        reference = build_attestation(listing.rows[0], lattice, note="keep")

        result = await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        assert set(result["attested"]) == set(reference)
        assert result["attested"]["tested"] is True
        assert result["attested"]["map"]["id"] == "ZHLT01"
        assert result["attested"]["target"] == TARGET_KEY
        assert result["attested"]["kind"] == "cell"

    @pytest.mark.asyncio
    async def test_a_later_write_reopens_it(self, wired):
        """The whole expiry mechanism, and there is nothing scheduled in
        it: change the bytes and the key stops matching."""
        hass, device, matrix, cells = wired
        await _apply(
            hass, device, cells[DISPUTED_KEY].pronto,
            source="capture", reading_disagreed=True,
        )
        _open, answered = _rows(device, matrix)
        assert f"cell:{TARGET_KEY}" in answered

        connection = _conn()
        await ws_tangle_revert(hass, connection, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": TARGET,
        })
        connection.send_error.assert_not_called()
        open_after, answered_after = _rows(device, matrix)
        assert f"cell:{TARGET_KEY}" in open_after
        assert f"cell:{TARGET_KEY}" not in answered_after
        # The record is still there and simply no longer applies, which
        # is the design: nothing is swept, so there is no sweep to be
        # wrong.
        assert len(device.tangle_attestations) == 1


class TestWhatRecordsNothing:
    @pytest.mark.asyncio
    async def test_a_repair_that_reads_clean_records_nothing(self, wired):
        """The finding clears on its own arithmetic. An attestation here
        would be claiming a dispute that no longer exists."""
        hass, device, _matrix, cells = wired
        result = await _apply(
            hass, device, cells[CLEAN_KEY].pronto,
            source="donor", reading_disagreed=True,
        )
        assert result["verdict"]["matches"] is True
        assert result["attested"] is None
        assert device.tangle_attestations == []

    @pytest.mark.asyncio
    async def test_an_ordinary_donor_repair_records_nothing(self, wired):
        hass, device, _matrix, cells = wired
        result = await _apply(
            hass, device, cells[CLEAN_KEY].pronto, source="donor")
        assert result["attested"] is None
        assert device.tangle_attestations == []
