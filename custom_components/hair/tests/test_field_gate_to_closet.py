"""The 52 cells, all the way to the Perfect Fit checklist.

`test_field_sweep.py` pins what the sweep FINDS. This pins what happens
to it afterwards, through the paths a person actually walks: import
combs and stamps a receipt, ADOPT mints a porthole row per doubted cell,
and SAVE TO CLOSET puts those rows in front of somebody as things to
attest. Nothing here is mocked below the websocket handler -- the device
manager is a stand-in for Home Assistant's storage, but the minting, the
plan build and the comb gate are the shipped code.

The number is the same number: 52 findings in, 52 flagged rows out, on
the coordinates the sweep named and no others. A finding that dies
between the comb and the checklist is a finding nobody acts on.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.websocket_api import ws_wig_make_device
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    comb_wig,
    stamp_receipt,
)
from custom_components.hair.wig_format import Wig, parse_wig, serialize_wig
from custom_components.hair.wig_save import build_save_plan

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
FILENAME = "komeco.wig.json"


def _combed_komeco() -> Wig:
    """The contributor's file, combed and stamped as import would."""
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    wig = parsed.wig
    stamp_receipt(wig, comb_wig(wig), "2026-08-22")
    return wig


@pytest.fixture
def wigs_dir_path(tmp_path):
    directory = tmp_path / "hair" / "wigs"
    directory.mkdir(parents=True)
    return directory


@pytest.fixture
def adopted(fake_hass, tmp_path, wigs_dir_path):
    """The Komeco wig, adopted through the real make-device handler.

    Returns ``(device, wig)``. The device is the object the handler
    built and handed to the manager, portholes and all.
    """
    wig = _combed_komeco()
    (wigs_dir_path / FILENAME).write_text(
        serialize_wig(wig), encoding="utf-8")

    manager = MagicMock()
    manager.async_create_device = AsyncMock()
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    manager.async_get_matrix = AsyncMock(return_value=None)
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "fitting_manager": None,
    }}

    async def _run():
        connection = MagicMock()
        connection.send_result = MagicMock()
        connection.send_error = MagicMock()
        await ws_wig_make_device(fake_hass, connection, {
            "id": 1, "type": "hair/wigs/make-device",
            "filename": FILENAME, "name": "Komeco",
            "device_type": "ac",
            "emitter_entity_ids": ["infrared.e"],
        })
        connection.send_error.assert_not_called()
        return connection.send_result.call_args.args[1]

    return _run, manager, wig


def _flagged_coordinates(wig: Wig) -> set[str]:
    return {finding.keys[0] for finding in comb_wig(wig).findings
            if finding.check == CHECK_FIELD_MISMATCH}


@pytest.mark.asyncio
async def test_adopt_mints_a_porthole_for_every_doubted_cell(adopted):
    """52 findings, 52 rows. The lattice's other 1,104 cells stay in
    the lattice: a commands area listing all of them would be useless,
    and one listing none of them would leave the defective column with
    no way to reach it."""
    run, _manager, wig = adopted
    result = await run()
    assert result["cell_rows"] == 52
    assert result["matrix_cells"] == len(wig.climate.cells)


@pytest.mark.asyncio
async def test_the_portholes_are_the_cells_the_sweep_named(adopted):
    """Not a count that happens to match -- the same coordinates."""
    run, manager, wig = adopted
    await run()
    device = manager.async_create_device.call_args.args[0]
    minted = {
        "/".join([
            command.matrix_cell["mode"],
            command.matrix_cell["fan"],
            command.matrix_cell["swing"],
            f"{command.matrix_cell['temp']:g}",
        ])
        for command in device.commands if command.matrix_cell
    }
    assert minted == _flagged_coordinates(wig)


@pytest.mark.asyncio
async def test_each_porthole_says_which_check_doubted_it(adopted):
    """A bare "suspect" tells somebody there is a problem and nothing
    about which problem. These rows all carry the same class because
    they all have the same cause."""
    run, manager, _ = adopted
    await run()
    device = manager.async_create_device.call_args.args[0]
    cells = [c for c in device.commands if c.matrix_cell]
    assert {c.comb_finding for c in cells} == {CHECK_FIELD_MISMATCH}
    assert all(c.comb_suspect for c in cells)


@pytest.mark.asyncio
async def test_the_checklist_carries_the_gate(adopted):
    """SAVE TO CLOSET through the real plan builder. The 52 arrive as
    comb-gated rows: a person cannot attest the lattice without being
    shown the column that lies about its setpoint."""
    run, manager, wig = adopted
    await run()
    device = manager.async_create_device.call_args.args[0]

    plan = build_save_plan(
        device, source_wig=wig, source_filename=FILENAME,
        matrix=wig.climate,
    )
    gated = [row for row in plan.rows if row.comb_suspect]
    assert len(gated) == 52
    assert {row.comb_finding for row in gated} == {CHECK_FIELD_MISMATCH}
    # Named as instructions, not coordinates: "set your remote to
    # heat_cool, medium, 19". Fan and swing join because four swing
    # modes share each temperature.
    assert all(row.alias.startswith("Heat_cool ") for row in gated)
    assert all("medium" in row.alias for row in gated)
    degrees = {int(row.alias.split()[1]) for row in gated}
    assert degrees == set(range(19, 32))


@pytest.mark.asyncio
async def test_the_rest_of_the_checklist_is_not_gated(adopted):
    """The gate has to be worth something. The dimension checklist's
    own sample rows are drawn from cells the sweep read and agreed
    with, and they arrive clean."""
    run, manager, wig = adopted
    await run()
    device = manager.async_create_device.call_args.args[0]

    plan = build_save_plan(
        device, source_wig=wig, source_filename=FILENAME,
        matrix=wig.climate,
    )
    clean = [row for row in plan.rows if not row.comb_suspect]
    assert clean
    assert {row.comb_finding for row in clean} == {None}


@pytest.mark.asyncio
async def test_a_wig_nobody_combed_gates_nothing(
    fake_hass, tmp_path, wigs_dir_path
):
    """Adopt reads the receipt; it never re-combs. An uncombed file
    brings no claim either way, and the same lattice must then reach
    the checklist ungated rather than half-judged."""
    parsed = parse_wig(KOMECO.read_text())
    wig = parsed.wig
    assert wig is not None
    (wigs_dir_path / FILENAME).write_text(
        serialize_wig(wig), encoding="utf-8")

    manager = MagicMock()
    manager.async_create_device = AsyncMock()
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    manager.async_get_matrix = AsyncMock(return_value=None)
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "fitting_manager": None,
    }}

    connection = MagicMock()
    connection.send_error = MagicMock()
    await ws_wig_make_device(fake_hass, connection, {
        "id": 1, "type": "hair/wigs/make-device",
        "filename": FILENAME, "name": "Komeco",
        "device_type": "ac",
        "emitter_entity_ids": ["infrared.e"],
    })
    connection.send_error.assert_not_called()
    assert connection.send_result.call_args.args[1]["cell_rows"] == 0

    device = manager.async_create_device.call_args.args[0]
    plan = build_save_plan(
        device, source_wig=wig, source_filename=FILENAME,
        matrix=wig.climate,
    )
    assert [row for row in plan.rows if row.comb_suspect] == []
