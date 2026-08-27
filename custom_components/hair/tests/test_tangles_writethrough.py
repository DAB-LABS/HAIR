"""The closet follows the device, without anybody saving.

A person who repairs an adopted device should not then have to go and
find a save button. Their wig is what they care about; the device is
where the work happened. So finishing a repair writes a new version of
their wig on its own, and the surface is allowed to say "Your wig has
been updated." only because the answer to that write came back on the
same message that carried the repair.

The part worth reading closely is what this will and will not delete.
The succession machinery it rides can supersede -- remove the file it
replaced and repoint the devices. Turned loose that would delete the
contributor's original on the very first click. So a mint STAMPS what
it wrote, and the stamp is what a later write reads before allowing
itself to supersede: the flow only ever removes files the flow made.
The original stays where it is, forever, and the closet settles at two
files rather than one per repair.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.matrix_store import load_matrix
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.tangles import (
    PROVENANCE_KEY,
    REPAIR_SUCCESSOR,
    WROTE_NOT_ADOPTED,
)
from custom_components.hair.websocket_api import (
    ws_device_tangles,
    ws_tangle_apply,
    ws_tangle_apply_batch,
    ws_tangle_keep,
    ws_tangle_plan,
    ws_tangle_revert,
    ws_wig_make_device,
)
from custom_components.hair.wig_comb import comb_wig, stamp_receipt
from custom_components.hair.wig_format import cell_key, parse_wig, serialize_wig
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
DREO = (FIXTURES / "wigs"
        / "dreo-fan-dr-haf004s-perfect-fit.wig.json")
SOURCE = "komeco.wig.json"


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _call(handler, hass, payload, *, expect_error=None):
    connection = _conn()
    await handler(hass, connection, payload)
    if expect_error is None:
        connection.send_error.assert_not_called()
        return connection.send_result.call_args.args[1]
    assert connection.send_error.call_args.args[1] == expect_error
    return None


@pytest.fixture
def _no_signing(monkeypatch):
    monkeypatch.setattr(
        "custom_components.hair.fitting_signing.async_get_private_key",
        AsyncMock(return_value=None),
    )


def _wire(fake_hass, tmp_path):
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
    store.get_device = MagicMock(
        side_effect=lambda did: next(
            (d for d in devices if d.id == did), None))
    store.get_all_devices = MagicMock(side_effect=lambda: list(devices))
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "store": store,
        "matrix_listener": MagicMock(), "fitting_manager": None,
    }}
    return devices


@pytest.fixture
async def adopted(fake_hass, tmp_path):
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    wig = parsed.wig
    stamp_receipt(wig, comb_wig(wig), "2026-08-22")
    ensure_wigs_dir(tmp_path)
    (wigs_dir(tmp_path) / SOURCE).write_text(
        serialize_wig(wig), encoding="utf-8")
    devices = _wire(fake_hass, tmp_path)
    await _call(ws_wig_make_device, fake_hass, {
        "id": 1, "type": "hair/wigs/make-device", "filename": SOURCE,
        "name": "Komeco", "device_type": "ac",
        "emitter_entity_ids": ["infrared.blaster"],
    })
    return fake_hass, devices[0], tmp_path, wig


async def _tangles(hass, device):
    return await _call(ws_device_tangles, hass, {
        "id": 2, "type": "hair/device/tangles", "device_id": device.id,
    })


async def _repair_the_donors(hass, device):
    """The 48-cell card, applied the way the surface would apply it."""
    listing = await _tangles(hass, device)
    card = next(c for c in listing["clusters"] if c["mechanic"] == "donor")
    plan = await _call(ws_tangle_plan, hass, {
        "id": 3, "type": "hair/device/tangle/plan",
        "device_id": device.id, "cluster": card["id"],
    })
    return await _call(ws_tangle_apply_batch, hass, {
        "id": 4, "type": "hair/device/tangle/apply-batch",
        "device_id": device.id, "cluster": card["id"],
        "tested": True, "tested_targets": plan["sample"],
    })


def _closet(tmp_path):
    return sorted(p.name for p in wigs_dir(tmp_path).glob("*.wig.json"))


def _load(tmp_path, filename):
    parsed = parse_wig((wigs_dir(tmp_path) / filename).read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


class TestTheAnswerRidesBackWithTheRepair:
    @pytest.mark.asyncio
    async def test_the_batch_says_it_wrote(self, adopted, _no_signing):
        """The field the UI gates its one line on."""
        hass, device, tmp_path, _wig = adopted
        result = await _repair_the_donors(hass, device)
        assert result["applied"] == 48
        assert result["wig"]["written"] is True
        assert result["wig"]["filename"] in _closet(tmp_path)

    @pytest.mark.asyncio
    async def test_nobody_called_save(self, adopted, _no_signing):
        """The whole point. No save handler is imported by this file."""
        hass, device, tmp_path, _wig = adopted
        await _repair_the_donors(hass, device)

        closet = _closet(tmp_path)
        assert len(closet) == 2
        successor_name = next(name for name in closet if name != SOURCE)
        successor = _load(tmp_path, successor_name)

        matrix = load_matrix(str(tmp_path), device.id)
        cells = {cell_key(c): c for c in successor.climate.cells}
        for cell in matrix.cells:
            assert cells[cell_key(cell)].pronto == cell.pronto
        repaired = [
            key for key, cell in cells.items()
            if (getattr(cell, "extra", None) or {}).get(PROVENANCE_KEY)
        ]
        assert len(repaired) == 48

    @pytest.mark.asyncio
    async def test_a_single_apply_writes_through_too(
            self, adopted, _no_signing):
        hass, device, tmp_path, _wig = adopted
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"] if r.get("donor"))
        result = await _call(ws_tangle_apply, hass, {
            "id": 5, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "source": "donor", "pronto": row["donor"]["pronto"],
            "tested": True,
        })
        assert result["wig"]["written"] is True
        assert len(_closet(tmp_path)) == 2


class TestWhatItWillNotDelete:
    @pytest.mark.asyncio
    async def test_the_contributors_file_survives_the_first_repair(
            self, adopted, _no_signing):
        """The original is not the flow's to remove, ever."""
        hass, device, tmp_path, _wig = adopted
        before = (wigs_dir(tmp_path) / SOURCE).read_text()
        await _repair_the_donors(hass, device)
        assert SOURCE in _closet(tmp_path)
        assert (wigs_dir(tmp_path) / SOURCE).read_text() == before

    @pytest.mark.asyncio
    async def test_the_second_repair_replaces_the_first_version(
            self, adopted, _no_signing):
        """Not one file per click.

        The mint stamps what it wrote; the next write reads that stamp
        off the device's CURRENT source and only then allows itself to
        supersede. So the closet holds the original and exactly one
        repaired version, however many times somebody works the cards.
        """
        hass, device, tmp_path, _wig = adopted
        first = await _repair_the_donors(hass, device)
        assert len(_closet(tmp_path)) == 2

        successor = _load(tmp_path, first["wig"]["filename"])
        assert successor.extra.get(REPAIR_SUCCESSOR) is True

        listing = await _tangles(hass, device)
        row = listing["rows"][0]
        second = await _call(ws_tangle_keep, hass, {
            "id": 6, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": row["id"], "tested": True,
        })
        assert second["wig"]["written"] is True
        closet = _closet(tmp_path)
        assert SOURCE in closet
        assert len(closet) == 2, closet

    @pytest.mark.asyncio
    async def test_the_successor_names_the_original_as_its_parent(
            self, adopted, _no_signing):
        hass, device, tmp_path, wig = adopted
        result = await _repair_the_donors(hass, device)
        successor = _load(tmp_path, result["wig"]["filename"])
        assert wig.wig_id in successor.supersedes

    @pytest.mark.asyncio
    async def test_the_wig_keeps_its_own_name_not_the_devices(
            self, adopted, _no_signing):
        """A device renamed in Home Assistant must not quietly rename
        somebody's wig on the next repair."""
        hass, device, tmp_path, wig = adopted
        device.name = "Bedroom AC (upstairs)"
        result = await _repair_the_donors(hass, device)
        assert _load(tmp_path, result["wig"]["filename"]).name == wig.name


class TestWhenThereIsNoWigToWrite:
    @pytest.mark.asyncio
    async def test_a_device_built_from_scratch_says_so(
            self, fake_hass, tmp_path, _no_signing):
        """Honestly, not as an error.

        Nothing was adopted, so no wig is owed a new version -- and the
        repair itself still stands. A caller that treated a missing
        write as a failure would be refusing good work over a wig that
        was never there.

        Hand-built from the fan's signals rather than adopted, so the
        device genuinely has no source. The fan is the fixture that
        gives a flat device real findings: a matrix cell disagrees with
        the LABEL its coordinates claim, and a flat command has no
        coordinates to disagree with.
        """
        ensure_wigs_dir(tmp_path)
        devices = _wire(fake_hass, tmp_path)
        parsed = parse_wig(DREO.read_text())
        assert parsed.wig is not None, parsed.errors
        device = IRDevice(name="Hand-built fan", climate_matrix=False,
                          emitter_entity_ids=["infrared.blaster"])
        for signal in parsed.wig.signals:
            device.add_command(IRCommand(
                name=signal.alias, code=signal.pronto, protocol="PRONTO"))
        devices.append(device)
        assert not device.source_wig_id

        listing = await _tangles(fake_hass, device)
        row = listing["rows"][0]
        clean = next(
            signal.pronto for signal in parsed.wig.signals
            if signal.alias not in {r["target"]["key"] for r in listing["rows"]}
        )
        result = await _call(ws_tangle_apply, fake_hass, {
            "id": 7, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "source": "paste", "pronto": clean, "tested": True,
        })
        assert result["applied"] is True
        assert result["wig"]["written"] is False
        assert result["wig"]["reason"] == WROTE_NOT_ADOPTED

    @pytest.mark.asyncio
    async def test_a_source_that_left_the_closet_says_so(
            self, adopted, _no_signing):
        """Deleted from under the device. The repair still lands; the
        write reports what happened instead of inventing a new file."""
        hass, device, tmp_path, _wig = adopted
        (wigs_dir(tmp_path) / SOURCE).unlink()
        result = await _repair_the_donors(hass, device)
        assert result["applied"] == 48
        assert result["wig"]["written"] is False
        assert result["wig"]["reason"] == "source_missing"


class TestUndoFollowsToo:
    @pytest.mark.asyncio
    async def test_the_closet_does_not_stay_ahead_of_the_device(
            self, adopted, _no_signing):
        """Undo puts the old bytes back. A wig still holding the
        repaired ones would be silently ahead of its own device."""
        hass, device, tmp_path, _wig = adopted
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"] if r.get("donor"))
        await _call(ws_tangle_apply, hass, {
            "id": 8, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "source": "donor", "pronto": row["donor"]["pronto"],
            "tested": True,
        })
        reverted = await _call(ws_tangle_revert, hass, {
            "id": 9, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": row["id"],
        })
        assert reverted["reverted"] is True
        assert reverted["wig"]["written"] is True

        successor = _load(tmp_path, reverted["wig"]["filename"])
        matrix = load_matrix(str(tmp_path), device.id)
        cells = {cell_key(c): c for c in successor.climate.cells}
        for cell in matrix.cells:
            assert cells[cell_key(cell)].pronto == cell.pronto


class TestKeepRidesOut:
    @pytest.mark.asyncio
    async def test_the_answer_reaches_the_wig_without_a_save(
            self, adopted, _no_signing):
        hass, device, tmp_path, _wig = adopted
        listing = await _tangles(hass, device)
        row = listing["rows"][0]
        result = await _call(ws_tangle_keep, hass, {
            "id": 10, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": row["id"], "tested": True,
            "note": "runs fine on my unit",
        })
        assert result["wig"]["written"] is True
        raw = json.loads(
            (wigs_dir(tmp_path) / result["wig"]["filename"]).read_text())
        assert "runs fine on my unit" in json.dumps(raw)
