"""What a repair record is allowed to claim about the room.

RULED 2026-08-28, ship-blocker. A bench run produced 48 repair records
carrying ``tier: "air-tested"`` with zero sends behind them. Nothing
lied on purpose: single apply DEFAULTED the tier to air-tested, and
``tested`` is an assertion the caller makes rather than anything the
server checks. The code did what it said. What it said overclaimed,
against this project's own rule that the server must never pretend to
verify a press it cannot see.

The honest form, from design brief section 8: apply and apply-batch
take ``sends_fired`` per row, the record keeps that number verbatim,
and ``air-tested`` is written ONLY where there is send evidence behind
it -- a positive count for that row, or membership in a batch's
air-tested sample. Everything else a person accepts is ``accepted``,
which claims exactly what happened: a human said yes to these bytes.

The distinction is worth more than the word. ``air-tested`` is the
strongest thing a record can say, it is what a later reader will trust
when deciding whether to re-prove a cell, and a tier that arrives free
with every write is worth nothing to them.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.matrix_store import load_matrix
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    PROVENANCE_KEY,
    TIER_ACCEPTED,
    TIER_AIR_TESTED,
    TIER_RULE_DERIVED,
    list_tangles,
    read_repair,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply,
    ws_tangle_apply_batch,
    ws_tangle_plan,
    ws_wig_make_device,
)
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    comb_wig,
    stamp_receipt,
)
from custom_components.hair.wig_export import build_wig_from_device
from custom_components.hair.wig_format import (
    Wig,
    cell_key,
    parse_wig,
    serialize_wig,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

TARGET_KEY = "heat_cool/medium/off/25"
TARGET = f"cell:{TARGET_KEY}"
DONOR_KEY = "heat_cool/medium/off/24"


@pytest.fixture
def komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture
def wired(fake_hass, komeco, tmp_path):
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
    return connection


def _record(cells):
    return read_repair(cells[TARGET_KEY])


class TestASingleApplyClaimsOnlyWhatItCan:
    @pytest.mark.asyncio
    async def test_no_sends_is_accepted_never_air_tested(self, wired):
        """The bench's 48 records, in one assertion. This is the exact
        shape that produced them: a person accepted a repair and
        pressed nothing."""
        hass, device, _matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto,
                     source="donor", sends_fired=0)
        record = _record(cells)
        assert record["tier"] == TIER_ACCEPTED
        assert record["tier"] != TIER_AIR_TESTED
        assert record["sends_fired"] == 0

    @pytest.mark.asyncio
    async def test_an_absent_field_is_also_accepted(self, wired):
        """The regression that mattered. The old code DEFAULTED to
        air-tested, so a caller that said nothing about sends got the
        strongest claim in the vocabulary for free."""
        hass, device, _matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        record = _record(cells)
        assert record["tier"] == TIER_ACCEPTED
        assert record["sends_fired"] == 0

    @pytest.mark.asyncio
    async def test_a_press_earns_air_tested(self, wired):
        hass, device, _matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto,
                     source="donor", sends_fired=1)
        record = _record(cells)
        assert record["tier"] == TIER_AIR_TESTED
        assert record["sends_fired"] == 1

    @pytest.mark.asyncio
    async def test_the_count_is_recorded_verbatim(self, wired):
        """Not a boolean. "accepted, N sends fired" needs the N, and a
        reader deciding whether to re-prove a cell wants to know
        whether it was pressed once or six times."""
        hass, device, _matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto,
                     source="donor", sends_fired=6)
        assert _record(cells)["sends_fired"] == 6

    @pytest.mark.asyncio
    async def test_tested_still_means_what_it_meant(self, wired):
        """``tested`` is still the caller's assertion, still recorded,
        still never verified. sends_fired does not replace it -- it is
        the countable evidence beside it."""
        hass, device, _matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto,
                     source="donor", sends_fired=0)
        assert _record(cells)["tested"] is True


class TestTheBatchKeepsItsTwoTiers:
    @pytest.fixture
    async def adopted(self, fake_hass, tmp_path):
        parsed = parse_wig(KOMECO.read_text())
        wig = parsed.wig
        stamp_receipt(wig, comb_wig(wig), "2026-08-22")
        ensure_wigs_dir(tmp_path)
        (wigs_dir(tmp_path) / "komeco.wig.json").write_text(
            serialize_wig(wig), encoding="utf-8")
        devices: list = []
        manager = MagicMock()
        manager.async_create_device = AsyncMock(
            side_effect=lambda d: devices.append(d))
        manager.async_update_device = AsyncMock()
        manager._auto_map_command = MagicMock()
        manager.get_device = MagicMock(
            side_effect=lambda did: next(
                (d for d in devices if d.id == did), None))
        manager.async_get_matrix = AsyncMock(
            side_effect=lambda did: load_matrix(str(tmp_path), did))
        store = MagicMock()
        store.get_device = manager.get_device
        store.get_all_devices = MagicMock(side_effect=lambda: list(devices))
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": manager, "store": store,
            "matrix_listener": MagicMock(), "fitting_manager": None,
        }}
        connection = _conn()
        await ws_wig_make_device(fake_hass, connection, {
            "id": 1, "type": "hair/wigs/make-device",
            "filename": "komeco.wig.json", "name": "Komeco",
            "device_type": "ac", "emitter_entity_ids": ["infrared.blaster"],
        })
        return fake_hass, devices[0], tmp_path

    async def _read_plan(self, hass, device):
        """The plan alone, so a caller can decide what to fire BEFORE
        the batch runs. A repair is one-way: the fixture hands back one
        device, and once its donor cluster is spent there is no second
        run to compare against."""
        from custom_components.hair.websocket_api import ws_device_tangles

        conn = _conn()
        await ws_device_tangles(hass, conn, {
            "id": 2, "type": "hair/device/tangles", "device_id": device.id})
        listing = conn.send_result.call_args.args[1]
        card = next(c for c in listing["clusters"]
                    if c["mechanic"] == "donor")
        conn = _conn()
        await ws_tangle_plan(hass, conn, {
            "id": 3, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": card["id"]})
        return card, conn.send_result.call_args.args[1]

    async def _apply_plan(self, hass, device, card, plan, **extra):
        conn = _conn()
        payload = {
            "id": 4, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": card["id"],
            "tested": True, "tested_targets": plan["sample"],
        }
        payload.update(extra)
        await ws_tangle_apply_batch(hass, conn, payload)
        conn.send_error.assert_not_called()
        return conn.send_result.call_args.args[1]

    async def _run_batch(self, hass, device, **extra):
        card, plan = await self._read_plan(hass, device)
        return plan, await self._apply_plan(
            hass, device, card, plan, **extra)

    def _tiers(self, tmp_path, device):
        matrix = load_matrix(str(tmp_path), device.id)
        out: dict[str, int] = {}
        for cell in matrix.cells:
            record = read_repair(cell)
            if record:
                out[record["tier"]] = out.get(record["tier"], 0) + 1
        return out

    @pytest.mark.asyncio
    async def test_the_sample_is_air_tested_and_the_rest_derived(
            self, adopted):
        """Unchanged by the ruling, and pinned here so the fix cannot
        quietly flatten a run into one tier."""
        hass, device, tmp_path = adopted
        _plan, result = await self._run_batch(hass, device)
        assert result["applied"] == 48
        tiers = self._tiers(tmp_path, device)
        assert tiers[TIER_AIR_TESTED] == len(result["air_tested"])
        assert tiers[TIER_RULE_DERIVED] == 48 - len(result["air_tested"])
        assert TIER_ACCEPTED not in tiers

    @pytest.mark.asyncio
    async def test_a_fired_row_earns_air_tested_on_its_own_evidence(
            self, adopted):
        """On TOP of the sample, not instead of it. A row the surface
        actually fired has the same evidence the sample has."""
        hass, device, tmp_path = adopted
        card, plan = await self._read_plan(hass, device)
        extra = next(m for m in plan["candidates"]
                     if m not in plan["sample"])
        result = await self._apply_plan(
            hass, device, card, plan, sends_fired={extra: 2})

        assert result["applied"] == 48
        assert extra not in result["air_tested"]
        tiers = self._tiers(tmp_path, device)
        assert tiers[TIER_AIR_TESTED] == len(result["air_tested"]) + 1
        assert tiers[TIER_RULE_DERIVED] == 48 - len(result["air_tested"]) - 1

        matrix = load_matrix(str(tmp_path), device.id)
        fired = next(read_repair(c) for c in matrix.cells
                     if cell_key(c) == extra.split(":", 1)[-1])
        assert fired["sends_fired"] == 2
        assert fired["tier"] == TIER_AIR_TESTED

    @pytest.mark.asyncio
    async def test_every_batch_record_carries_its_count(self, adopted):
        hass, device, tmp_path = adopted
        await self._run_batch(hass, device)
        matrix = load_matrix(str(tmp_path), device.id)
        records = [read_repair(c) for c in matrix.cells if read_repair(c)]
        assert len(records) == 48
        assert all("sends_fired" in r for r in records)


class TestItRidesOutInTheReceipt:
    @pytest.mark.asyncio
    async def test_the_field_reaches_the_exported_wig(self, wired):
        """The wire field has to survive all the way to the file, or
        the receipt a person reads still cannot say it."""
        hass, device, matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto,
                     source="donor", sends_fired=3)

        build = build_wig_from_device(device, matrix)
        assert build.wig is not None
        exported = {cell_key(c): c for c in build.wig.climate.cells}
        record = (getattr(exported[TARGET_KEY], "extra", None)
                  or {}).get(PROVENANCE_KEY)
        assert record["sends_fired"] == 3
        assert record["tier"] == TIER_AIR_TESTED

    @pytest.mark.asyncio
    async def test_an_accepted_repair_says_so_in_the_file(self, wired):
        hass, device, matrix, cells = wired
        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")

        build = build_wig_from_device(device, matrix)
        raw = json.loads(serialize_wig(build.wig))
        text = json.dumps(raw)
        assert '"tier": "accepted"' in text
        assert '"tier": "air-tested"' not in text


class TestTheBenchRegressionShape:
    @pytest.mark.asyncio
    async def test_the_forty_eight_would_not_read_air_tested_today(
            self, wired):
        """The record of what went wrong, as a test.

        On the bench, 48 cells were repaired through single applies
        with nothing pressed, and every record claimed air-tested. The
        same sequence now produces accepted with a zero count, which is
        both true and the thing a later reader needs in order to know
        the cell is still worth proving.
        """
        hass, device, _matrix, cells = wired
        listing = list_tangles(device, _matrix)
        assert any(r.target.key == TARGET_KEY for r in listing.rows)

        await _apply(hass, device, cells[DONOR_KEY].pronto, source="donor")
        record = _record(cells)
        assert (record["tier"], record["sends_fired"]) == (TIER_ACCEPTED, 0)
