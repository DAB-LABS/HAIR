"""Comb-flagged cells become command rows, and the rows are portholes.

A lattice has thousands of cells and a commands area listing them all
would be useless, so only the flagged handful surface. What makes the
row worth having is that the FULL command toolset then reaches the
cell for free: TEST sends it, edit rewrites it, delete removes it.

The word "porthole" is load-bearing. Every action through the row acts
on the lattice, never on a second copy that could drift from it -- the
climate entity reads the matrix store, so a row that edited only itself
would leave the entity transmitting the code the person just replaced.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.websocket_api import (
    _cell_row_name,
    _mint_cell_rows,
    _porthole_cell,
    ws_delete_command,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    cell_key,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"


def _matrix():
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, off=PRONTO_A,
        modes=["cool", "heat"], fan_modes=["auto", "high"],
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=24.0, pronto=PRONTO_A),
            ClimateCell(mode="cool", fan="high", temp=24.0, pronto=PRONTO_A),
            ClimateCell(mode="heat", fan="auto", temp=20.0, pronto=PRONTO_B),
        ],
    )


class TestWhichCellsSurface:
    def test_a_flagged_cell_becomes_a_row(self):
        matrix = _matrix()
        flagged = {cell_key(matrix.cells[0]): "duplicated-neighbour"}
        device = IRDevice(name="AC")
        assert _mint_cell_rows(device, matrix, flagged) == 1
        row = device.commands[0]
        # The marker has to say WHICH finding, not just that there is
        # one: a bare "suspect" names a problem and hides which.
        assert row.comb_finding == "duplicated-neighbour"
        assert row.matrix_cell["mode"] == "cool"
        assert row.matrix_cell["temp"] == 24.0
        assert row.comb_suspect is True
        assert row.code == PRONTO_A

    def test_a_healthy_cell_does_not(self):
        """The whole point of surfacing only the doubted ones. A
        commands area carrying the healthy thousands would bury the
        handful worth looking at."""
        matrix = _matrix()
        device = IRDevice(name="AC")
        _mint_cell_rows(
            device, matrix, {cell_key(matrix.cells[0]): "malformed"}
        )
        surfaced = {c.matrix_cell["fan"] for c in device.commands}
        assert surfaced == {"auto"}
        assert len(device.commands) == 1

    def test_no_receipt_means_no_rows(self):
        device = IRDevice(name="AC")
        assert _mint_cell_rows(device, _matrix(), {}) == 0
        assert device.commands == []

    def test_cells_carry_no_dittos(self):
        """Cells have no ditto grammar (plan 5.5), and IRCommand's own
        default is the catalog's 1 -- which would invent one."""
        matrix = _matrix()
        device = IRDevice(name="AC")
        _mint_cell_rows(
            device, matrix, {cell_key(matrix.cells[0]): "malformed"}
        )
        assert device.commands[0].repeat_count == 0


class TestRowNames:
    def test_a_row_reads_as_a_state_you_can_set(self):
        matrix = _matrix()
        assert _cell_row_name(matrix.cells[2], [matrix.cells[2]]) == "Heat 20"

    def test_coordinates_join_only_when_two_rows_would_collide(self):
        """A lattice usually carries several fan speeds per temperature,
        so two flagged cells can share mode and temp. Two rows reading
        "Cool 24" would help nobody."""
        matrix = _matrix()
        both = [matrix.cells[0], matrix.cells[1]]
        names = {_cell_row_name(c, both) for c in both}
        assert names == {"Cool 24 auto", "Cool 24 high"}


class TestThePorthole:
    def _wire(self, fake_hass, device, manager):
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}

    def test_an_ordinary_command_is_not_a_porthole(self):
        device = IRDevice(name="TV", commands=[IRCommand(id="c1", name="On")])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        assert _porthole_cell(manager, device.id, "c1") is None

    def test_a_cell_row_reports_its_coordinates(self):
        row = IRCommand(
            id="c1", name="Cool 24",
            matrix_cell={"mode": "cool", "fan": "auto",
                         "swing": None, "temp": 24.0},
        )
        device = IRDevice(name="AC", commands=[row])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        assert _porthole_cell(manager, device.id, "c1")["mode"] == "cool"

    @pytest.mark.asyncio
    async def test_deleting_the_row_deletes_the_cell(self, fake_hass):
        """The row is a porthole, so a delete through it reaches the
        lattice. The climate entity simply stops offering that state --
        sparse lattices are already legal."""
        row = IRCommand(
            id="c1", name="Cool 24",
            matrix_cell={"mode": "cool", "fan": "auto",
                         "swing": None, "temp": 24.0},
        )
        device = IRDevice(name="AC", commands=[row], climate_matrix=True)
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_delete_cell = AsyncMock(return_value=True)
        manager.async_remove_command = AsyncMock(return_value=True)
        self._wire(fake_hass, device, manager)
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()
        await ws_delete_command(fake_hass, conn, {
            "id": 1, "type": "hair/command/delete",
            "device_id": device.id, "command_id": "c1",
        })
        manager.async_delete_cell.assert_awaited_once()
        assert manager.async_delete_cell.await_args.args[1]["mode"] == "cool"

    @pytest.mark.asyncio
    async def test_deleting_an_ordinary_command_touches_no_lattice(
        self, fake_hass
    ):
        device = IRDevice(name="TV", commands=[IRCommand(id="c1", name="On")])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_delete_cell = AsyncMock(return_value=True)
        manager.async_remove_command = AsyncMock(return_value=True)
        self._wire(fake_hass, device, manager)
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()
        await ws_delete_command(fake_hass, conn, {
            "id": 1, "type": "hair/command/delete",
            "device_id": device.id, "command_id": "c1",
        })
        manager.async_delete_cell.assert_not_awaited()


class TestTheLatticeWriters:
    """The manager's two writers. Both refresh the cache, because
    async_get_matrix caches and a stale cache is the bug that looks
    fixed on the bench and comes back at the next restart."""

    def _manager(self, matrix):
        from custom_components.hair.device_manager import DeviceManager

        manager = MagicMock(spec=DeviceManager)
        manager._matrix_cache = {}
        manager._cell_matches = DeviceManager._cell_matches
        manager.async_get_matrix = AsyncMock(return_value=matrix)
        manager.async_write_matrix = AsyncMock()
        manager.async_replace_cell = lambda d, c, p: (
            DeviceManager.async_replace_cell(manager, d, c, p)
        )
        manager.async_delete_cell = lambda d, c: (
            DeviceManager.async_delete_cell(manager, d, c)
        )
        return manager

    @pytest.mark.asyncio
    async def test_replace_writes_the_cell_and_persists(self):
        matrix = _matrix()
        manager = self._manager(matrix)
        ok = await manager.async_replace_cell(
            "d1", {"mode": "cool", "fan": "auto", "swing": None,
                   "temp": 24.0}, PRONTO_B,
        )
        assert ok is True
        assert matrix.cells[0].pronto == PRONTO_B
        manager.async_write_matrix.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_a_temp_that_round_tripped_as_an_int_still_matches(self):
        """Coordinates are compared numerically, not by cell_key. A
        temperature that came back from JSON as 24 rather than 24.0
        would stop matching its own row under string comparison."""
        matrix = _matrix()
        manager = self._manager(matrix)
        ok = await manager.async_replace_cell(
            "d1", {"mode": "cool", "fan": "auto", "swing": None,
                   "temp": 24}, PRONTO_B,
        )
        assert ok is True

    @pytest.mark.asyncio
    async def test_replacing_a_vanished_cell_reports_failure(self):
        manager = self._manager(_matrix())
        ok = await manager.async_replace_cell(
            "d1", {"mode": "dry", "fan": None, "swing": None,
                   "temp": 24.0}, PRONTO_B,
        )
        assert ok is False
        manager.async_write_matrix.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_removes_only_that_cell(self):
        matrix = _matrix()
        manager = self._manager(matrix)
        ok = await manager.async_delete_cell(
            "d1", {"mode": "cool", "fan": "auto", "swing": None,
                   "temp": 24.0},
        )
        assert ok is True
        assert len(matrix.cells) == 2
        assert all(
            not (c.mode == "cool" and c.fan == "auto") for c in matrix.cells
        )

    @pytest.mark.asyncio
    async def test_writing_the_lattice_refreshes_the_cache(self):
        """THE ONE THAT BITES LATER. async_get_matrix caches, and the
        climate entity reads through it. A write that persisted without
        refreshing would leave the entity transmitting the code the
        person just replaced, until a restart -- which looks fixed on
        the bench and comes back in the morning."""
        from custom_components.hair.device_manager import DeviceManager

        matrix = _matrix()
        manager = MagicMock(spec=DeviceManager)
        manager._matrix_cache = {"d1": _matrix()}
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock()
        manager._hass = hass
        await DeviceManager.async_write_matrix(manager, "d1", matrix)
        hass.async_add_executor_job.assert_awaited_once()
        assert manager._matrix_cache["d1"] is matrix


class TestTheCombMarker:
    """The marker names the comb's ACTUAL finding.

    A bare "suspect" tells somebody there is a problem and hides which
    one, and they are about to decide whether to test the row, replace
    it, or leave it. The comb recorded a class, so the row should say.
    """

    def _combed(self):
        from custom_components.hair.wig_comb import comb_wig, stamp_receipt
        from custom_components.hair.wig_format import Wig, WigSignal

        odd = (
            "0000 006D 0004 0000 0020 0040 0020 0040 0030 0020 0020 0040"
        )
        wig = Wig(name="TV", signals=[
            WigSignal(alias="Power", pronto=PRONTO_A),
            WigSignal(alias="Volume Up", pronto=PRONTO_A),
            WigSignal(alias="Volume Down", pronto=PRONTO_A),
            WigSignal(alias="Sleep", pronto=odd),
        ])
        stamp_receipt(wig, comb_wig(wig), "2026-08-03")
        return wig

    def test_the_marker_carries_the_finding_class(self):
        from custom_components.hair.wig_comb import (
            comb_wig,
            suspect_findings,
        )

        wig = self._combed()
        findings = suspect_findings(wig)
        assert findings
        # Whatever the comb actually reported for that row is what the
        # tooltip will name -- checked against the report itself rather
        # than a class hard-coded into the test.
        reported = {
            key: entry.check
            for entry in comb_wig(wig).findings
            for key in entry.keys
        }
        for key, check in findings.items():
            assert reported[key] == check

    def test_a_row_the_comb_did_not_flag_carries_no_finding(self):
        from custom_components.hair.wig_comb import suspect_findings

        findings = suspect_findings(self._combed())
        assert "Power" not in findings

    def test_an_uncombed_wig_yields_no_findings(self):
        from custom_components.hair.wig_format import Wig, WigSignal

        wig = Wig(name="TV", signals=[
            WigSignal(alias="Power", pronto=PRONTO_A),
        ])
        from custom_components.hair.wig_comb import suspect_findings

        assert suspect_findings(wig) == {}


class TestASavedStateRowIsNotAPorthole:
    """0.10.1 item 7 keeps the two apart deliberately.

    A saved STATE row and a porthole row both carry a lattice cell's
    bytes and both name a cell's coordinates, so it is tempting to
    stamp one field for both. They mean opposite things about
    ownership: a porthole IS the cell (edit rewrites it, DELETE DELETES
    IT), while a saved STATE row is an ordinary stored command that
    happens to transmit those bytes. Sharing the field would have made
    deleting a saved STATE row silently remove the state from the
    device's matrix.
    """

    @pytest.mark.asyncio
    async def test_deleting_a_saved_state_row_leaves_the_lattice_alone(
        self, fake_hass
    ):
        from custom_components.hair.const import CommandSource

        row = IRCommand(
            id="c1", name="cool / fan: auto / 24",
            source=CommandSource.MATRIX,
            sent_state={"mode": "cool", "fan": "auto",
                        "swing": None, "temp": 24.0},
        )
        device = IRDevice(name="AC", commands=[row], climate_matrix=True)
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_delete_cell = AsyncMock(return_value=True)
        manager.async_remove_command = AsyncMock(return_value=True)
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()

        await ws_delete_command(fake_hass, conn, {
            "id": 1, "type": "hair/command/delete",
            "device_id": device.id, "command_id": "c1",
        })

        manager.async_delete_cell.assert_not_awaited()
        manager.async_remove_command.assert_awaited_once()

    def test_sent_state_is_not_read_as_a_porthole(self):
        row = IRCommand(
            id="c1", name="cool / fan: auto / 24",
            sent_state={"mode": "cool", "fan": "auto",
                        "swing": None, "temp": 24.0},
        )
        device = IRDevice(name="AC", commands=[row])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)

        assert _porthole_cell(manager, device.id, "c1") is None
