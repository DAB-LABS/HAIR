"""The whole loop, through the shipped handlers.

A contributor's file arrives with 52 wrong cells. Somebody adopts it,
works the cards the surface would show them, presses their own remote
once for the cells nothing could be copied for, vouches for one finding
they decided is fine, and saves the result back to the closet -- and
what lands there is clean, carries the record of every repair, and no
longer claims the fittings that were signed over the broken bytes.

Nothing below reaches past a websocket handler. The adopt is the adopt,
the repairs are the repairs, and the save is the save. The point of the
file is that the pieces fit together, not that each works alone -- that
is what the other five suites are for.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import field_readers
from custom_components.hair.const import DOMAIN
from custom_components.hair.matrix_store import load_matrix, matrix_content_hash
from custom_components.hair.tangles import (
    APPLY_NO_FINDING,
    APPLY_NOT_TESTED,
    ATTESTED_KEY,
    PROVENANCE_KEY,
    TIER_AIR_TESTED,
    TIER_RULE_DERIVED,
    read_lattice,
    rewrite_field,
)
from custom_components.hair.websocket_api import (
    ws_device_tangles,
    ws_tangle_apply,
    ws_tangle_apply_batch,
    ws_tangle_keep,
    ws_tangle_plan,
    ws_tangle_revert,
    ws_wig_make_device,
    ws_wigs_save,
)
from custom_components.hair.wig_comb import COMB_KEY, comb_wig, stamp_receipt
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
    connection.send_result.assert_not_called()
    return None


@pytest.fixture
def _no_signing(monkeypatch):
    monkeypatch.setattr(
        "custom_components.hair.fitting_signing.async_get_private_key",
        AsyncMock(return_value=None),
    )


@pytest.fixture
async def adopted(fake_hass, tmp_path):
    """The contributor's file, combed at import and adopted for real.

    ``async_get_matrix`` reads the matrix FILE rather than holding an
    object, so every repair below round-trips through disk exactly as it
    would on a running install.
    """
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    wig = parsed.wig
    stamp_receipt(wig, comb_wig(wig), "2026-08-22")
    ensure_wigs_dir(tmp_path)
    (wigs_dir(tmp_path) / SOURCE).write_text(
        serialize_wig(wig), encoding="utf-8")

    fake_hass.config.config_dir = str(tmp_path)
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
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "store": store,
        "matrix_listener": MagicMock(), "fitting_manager": None,
    }}

    result = await _call(ws_wig_make_device, fake_hass, {
        "id": 1, "type": "hair/wigs/make-device", "filename": SOURCE,
        "name": "Komeco", "device_type": "ac",
        "emitter_entity_ids": ["infrared.blaster"],
    })
    assert result["cell_rows"] == 52
    return fake_hass, devices[0], tmp_path, wig


async def _tangles(hass, device):
    return await _call(ws_device_tangles, hass, {
        "id": 2, "type": "hair/device/tangles", "device_id": device.id,
    })


async def _press(hass, device, tmp_path, row):
    """A capture reading as the row's own label, on this hardware."""
    matrix = load_matrix(str(tmp_path), device.id)
    lattice = read_lattice(matrix)
    spec = lattice.spec_for("temperature")
    coordinates = row["target"]["coordinates"]
    sibling = next(
        c for c in matrix.cells
        if cell_key(c) == (
            f"{coordinates['mode']}/{coordinates['fan']}"
            f"/{coordinates['swing']}/16"
        )
    )
    built = rewrite_field(
        lattice.field_map, sibling.pronto, spec,
        field_readers.expected_value(spec, coordinates["temp"]),
    )
    assert built is not None
    return built


class TestTheListingOnARealAdopt:
    @pytest.mark.asyncio
    async def test_fifty_two_rows_two_cards(self, adopted):
        hass, device, _tmp, _wig = adopted
        listing = await _tangles(hass, device)
        assert len(listing["rows"]) == 52
        assert len(listing["clusters"]) == 2
        assert listing["protocol"] == "ZHLT01"

    @pytest.mark.asyncio
    async def test_forty_eight_have_a_donor_and_four_abstain(self, adopted):
        hass, device, _tmp, _wig = adopted
        listing = await _tangles(hass, device)
        assert sum(1 for r in listing["rows"] if r["has_donor"]) == 48
        abstained = [r for r in listing["rows"] if not r["has_donor"]]
        assert {r["target"]["key"] for r in abstained} == {
            "heat_cool/medium/both/19",
            "heat_cool/medium/horizontal/19",
            "heat_cool/medium/off/19",
            "heat_cool/medium/vertical/19",
        }
        assert {r["donor_abstain"] for r in abstained} == {
            "no-cell-reads-this"}


class TestOneRepairAndItsUndo:
    @pytest.mark.asyncio
    async def test_apply_lands_on_disk_and_moves_the_hash(self, adopted):
        hass, device, tmp_path, _wig = adopted
        before_hash = matrix_content_hash(str(tmp_path), device.id)
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"]
                   if r["target"]["key"] == "heat_cool/medium/off/25")

        await _call(ws_tangle_apply, hass, {
            "id": 3, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "pronto": row["donor"]["pronto"], "tested": True,
            "source": "donor",
        })

        matrix = load_matrix(str(tmp_path), device.id)
        cell = next(c for c in matrix.cells
                    if cell_key(c) == "heat_cool/medium/off/25")
        assert cell.pronto == row["donor"]["pronto"]
        assert PROVENANCE_KEY in cell.extra
        assert matrix_content_hash(str(tmp_path), device.id) != before_hash

    @pytest.mark.asyncio
    async def test_the_finding_goes_and_comes_back(self, adopted):
        hass, device, _tmp, _wig = adopted
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"]
                   if r["target"]["key"] == "heat_cool/medium/off/25")

        await _call(ws_tangle_apply, hass, {
            "id": 3, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "pronto": row["donor"]["pronto"], "tested": True,
            "source": "donor",
        })
        after = await _tangles(hass, device)
        assert len([
            r for r in after["rows"]
            if "field-mismatch" in r["classes"]
        ]) == 51

        await _call(ws_tangle_revert, hass, {
            "id": 4, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": row["id"],
        })
        restored = await _tangles(hass, device)
        assert len(restored["rows"]) == 52
        assert "heat_cool/medium/off/25" in {
            r["target"]["key"] for r in restored["rows"]}


class TestTheGuardRails:
    @pytest.mark.asyncio
    async def test_apply_without_a_press_refuses(self, adopted):
        hass, device, _tmp, _wig = adopted
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"] if r["has_donor"])
        await _call(ws_tangle_apply, hass, {
            "id": 3, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "pronto": row["donor"]["pronto"], "tested": False,
        }, expect_error=APPLY_NOT_TESTED)

    @pytest.mark.asyncio
    async def test_apply_to_a_healthy_cell_refuses(self, adopted):
        hass, device, _tmp, _wig = adopted
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"] if r["has_donor"])
        await _call(ws_tangle_apply, hass, {
            "id": 3, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": "cell:cool/high/off/22",
            "pronto": row["donor"]["pronto"], "tested": True,
        }, expect_error=APPLY_NO_FINDING)

    @pytest.mark.asyncio
    async def test_an_attestation_expires_when_the_map_moves(self, adopted):
        """The finding comes back on its own. Nothing swept it: the
        attestation names the map version it answered, and a map that
        has learned something since is asking a new question."""
        hass, device, _tmp, _wig = adopted
        listing = await _tangles(hass, device)
        row = next(r for r in listing["rows"] if r["has_donor"])
        await _call(ws_tangle_keep, hass, {
            "id": 5, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": row["id"], "tested": True,
        })
        quiet = await _tangles(hass, device)
        assert row["target"]["key"] not in {
            r["target"]["key"] for r in quiet["rows"]}

        record = device.tangle_attestations[0]
        target, digest, _version = record["key"].split("|")
        record["key"] = f"{target}|{digest}|a-newer-map"
        again = await _tangles(hass, device)
        assert row["target"]["key"] in {
            r["target"]["key"] for r in again["rows"]}
        assert again["attested"] == []


class TestTheWholeFile:
    @pytest.mark.asyncio
    async def test_two_cards_one_press_and_the_comb_goes_quiet(
            self, adopted):
        hass, device, tmp_path, _wig = adopted

        listing = await _tangles(hass, device)
        donor_card = next(c for c in listing["clusters"]
                          if c["mechanic"] == "donor")
        plan = await _call(ws_tangle_plan, hass, {
            "id": 6, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": donor_card["id"],
        })
        assert len(plan["candidates"]) == 48
        run = await _call(ws_tangle_apply_batch, hass, {
            "id": 7, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": donor_card["id"],
            "tested": True, "tested_targets": plan["sample"],
        })
        assert run["applied"] == 48

        listing = await _tangles(hass, device)
        witness_card = next(c for c in listing["clusters"]
                            if c["mechanic"] == "witness")
        aimed = sorted(witness_card["members"])[0]
        row = next(r for r in listing["rows"] if r["id"] == aimed)
        press = await _press(hass, device, tmp_path, row)

        plan = await _call(ws_tangle_plan, hass, {
            "id": 8, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": witness_card["id"],
            "witness": press, "witness_target": aimed,
        })
        assert len(plan["candidates"]) == 4
        assert plan["witness"]["reads_as"] == 19.0
        run = await _call(ws_tangle_apply_batch, hass, {
            "id": 9, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": witness_card["id"],
            "tested": True, "tested_targets": plan["sample"],
            "witness": press, "witness_target": aimed,
        })
        assert run["applied"] == 4

        final = await _tangles(hass, device)
        assert final["rows"] == []
        assert final["clusters"] == []
        matrix = load_matrix(str(tmp_path), device.id)
        assert [
            f for f in comb_wig(
                parse_wig(KOMECO.read_text()).wig
            ).findings
        ], "the fixture itself is still the broken one"
        repaired = parse_wig(KOMECO.read_text()).wig
        repaired.climate = matrix
        assert comb_wig(repaired).findings == []

    @pytest.mark.asyncio
    async def test_the_record_says_what_was_proved_on_air(self, adopted):
        hass, device, tmp_path, _wig = adopted
        listing = await _tangles(hass, device)
        card = next(c for c in listing["clusters"]
                    if c["mechanic"] == "donor")
        plan = await _call(ws_tangle_plan, hass, {
            "id": 6, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": card["id"],
        })
        await _call(ws_tangle_apply_batch, hass, {
            "id": 7, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": card["id"],
            "tested": True, "tested_targets": plan["sample"],
        })
        matrix = load_matrix(str(tmp_path), device.id)
        tiers = {
            cell.extra[PROVENANCE_KEY]["tier"]
            for cell in matrix.cells if PROVENANCE_KEY in cell.extra
        }
        assert tiers == {TIER_AIR_TESTED, TIER_RULE_DERIVED}
        tested = {
            cell_key(cell) for cell in matrix.cells
            if cell.extra.get(PROVENANCE_KEY, {}).get("tier")
            == TIER_AIR_TESTED
        }
        assert tested == {t.split(":", 1)[1] for t in plan["sample"]}


class TestBackToTheCloset:
    @pytest.mark.asyncio
    async def test_the_successor_is_clean_and_carries_the_repairs(
            self, adopted, _no_signing):
        """The owner's loop, end to end.

        Repair the file, vouch for one finding, save it back as a new
        wig -- and what reaches the shelf combs clean, says how every
        cell got there, and carries the human's answer beside the math.
        """
        hass, device, tmp_path, source = adopted

        listing = await _tangles(hass, device)
        card = next(c for c in listing["clusters"]
                    if c["mechanic"] == "donor")
        plan = await _call(ws_tangle_plan, hass, {
            "id": 6, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": card["id"],
        })
        await _call(ws_tangle_apply_batch, hass, {
            "id": 7, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": card["id"],
            "tested": True, "tested_targets": plan["sample"],
        })

        listing = await _tangles(hass, device)
        kept = listing["rows"][0]
        await _call(ws_tangle_keep, hass, {
            "id": 8, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": kept["id"], "tested": True,
            "note": "runs fine on my unit",
        })

        saved = await _call(ws_wigs_save, hass, {
            "id": 9, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Komeco KOS 09QC 3HX repaired",
        })
        successor = json.loads(
            (wigs_dir(tmp_path) / saved["filename"]).read_text())

        # A NEW file, not the one it came from.
        assert saved["filename"] != SOURCE
        assert successor["wig_id"] != source.wig_id

        parsed = parse_wig(json.dumps(successor))
        assert parsed.wig is not None, parsed.errors
        repaired = parsed.wig

        # The repaired bytes travelled.
        cells = {cell_key(c): c for c in repaired.climate.cells}
        matrix = load_matrix(str(tmp_path), device.id)
        for cell in matrix.cells:
            assert cells[cell_key(cell)].pronto == cell.pronto

        # And so did the record of how they got there.
        with_records = [
            c for c in repaired.climate.cells if PROVENANCE_KEY in c.extra
        ]
        assert len(with_records) == 48
        record = with_records[0].extra[PROVENANCE_KEY]
        assert record["origin"] == "fix"
        assert record["source"] == "donor"
        assert record["tested"] is True
        assert record["map"]["id"] == "ZHLT01"
        assert record["prior"]["pronto"]

        # The human's answer rides in the receipt beside the math.
        receipt = repaired.extra[COMB_KEY]
        assert receipt[ATTESTED_KEY][0]["note"] == "runs fine on my unit"
        assert "comb_attested_pending" not in repaired.extra

        # And a fresh comb of what reached the shelf finds the four the
        # donors could not reach and nothing else.
        left = comb_wig(repaired).findings
        assert {f.check for f in left} == {
            "duplicated-neighbour", "field-mismatch"}
        assert receipt["suspects"] == len(left)

    @pytest.mark.asyncio
    async def test_the_priors_do_not_follow_the_repaired_bytes(
            self, adopted, _no_signing):
        """Fix-then-fit. A signed claim binds the lattice it was signed
        over, and this is not that lattice any more, so the successor
        arrives asking to be fitted rather than carrying somebody's word
        for bytes they never saw.
        """
        hass, device, tmp_path, source = adopted
        assert source.extra.get("fittings"), "fixture carries a fitting"

        listing = await _tangles(hass, device)
        card = next(c for c in listing["clusters"]
                    if c["mechanic"] == "donor")
        plan = await _call(ws_tangle_plan, hass, {
            "id": 6, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": card["id"],
        })
        await _call(ws_tangle_apply_batch, hass, {
            "id": 7, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": card["id"],
            "tested": True, "tested_targets": plan["sample"],
        })
        saved = await _call(ws_wigs_save, hass, {
            "id": 9, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Komeco repaired",
        })
        successor = json.loads(
            (wigs_dir(tmp_path) / saved["filename"]).read_text())
        assert not successor.get("fittings")


class TestTheFlatFan:
    """The Dreo: seven buttons, two noisy captures, no lattice at all.

    Everything the matrix path leans on is absent here -- no oracle, no
    donors, no coordinates -- so what is left has to work on its own:
    the finding, its vote, a candidate somebody pastes, and the same
    door.
    """

    @pytest.fixture
    async def fan(self, fake_hass, tmp_path):
        from custom_components.hair.models import (
            CommandCategory,
            IRCommand,
            IRDevice,
        )

        parsed = parse_wig(DREO.read_text())
        assert parsed.wig is not None, parsed.errors
        wig = parsed.wig
        device = IRDevice(name="Dreo", emitter_entity_ids=["infrared.b"])
        for signal in wig.signals:
            device.add_command(IRCommand(
                name=signal.alias, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=signal.pronto,
                send_count=signal.send_count,
                repeat_count=signal.ditto_count,
                tx_force_raw=signal.bypass_protocol,
            ))
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=None)
        manager.async_update_device = AsyncMock()
        manager.async_test_send = AsyncMock(return_value={"infrared.b"})
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        return fake_hass, device, wig, manager

    @pytest.mark.asyncio
    async def test_two_rows_no_donors_and_it_says_why(self, fan):
        hass, device, _wig, _manager = fan
        listing = await _tangles(hass, device)
        assert len(listing["rows"]) == 2
        assert {r["classes"][0] for r in listing["rows"]} == {
            "frame-disagreement"}
        assert not any(r["has_donor"] for r in listing["rows"])
        assert listing["field_tier"] == "no-lattice"
        assert listing["candidate_sources"] == ["capture", "paste"]

    @pytest.mark.asyncio
    async def test_every_row_carries_its_vote(self, fan):
        hass, device, _wig, _manager = fan
        listing = await _tangles(hass, device)
        for row in listing["rows"]:
            vote = row["findings"][0]["params"]
            assert int(vote["frames"]) > 1
            assert row["verdict"]["frame_vote"]["frames"] > 1

    @pytest.mark.asyncio
    async def test_a_pasted_candidate_is_read_sent_and_applied(self, fan):
        hass, device, wig, manager = fan
        from custom_components.hair.websocket_api import (
            ws_tangle_pre_read,
            ws_tangle_test_send,
        )

        listing = await _tangles(hass, device)
        row = listing["rows"][0]
        clean = next(
            s.pronto for s in wig.signals
            if s.alias not in {r["target"]["key"] for r in listing["rows"]}
        )

        verdict = await _call(ws_tangle_pre_read, hass, {
            "id": 3, "type": "hair/device/tangle/pre-read",
            "device_id": device.id, "target": row["id"], "pronto": clean,
        })
        # No lattice, so no claim to check against -- and it says so
        # rather than inventing a verdict.
        assert verdict["matches"] is None
        assert verdict["frame_vote"] is None

        await _call(ws_tangle_test_send, hass, {
            "id": 4, "type": "hair/device/tangle/test-send",
            "device_id": device.id, "pronto": clean,
        })
        manager.async_test_send.assert_awaited_once()

        await _call(ws_tangle_apply, hass, {
            "id": 5, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row["id"],
            "pronto": clean, "tested": True, "source": "paste",
        })
        command = device.get_command(row["target"]["command_id"])
        assert command.code == clean
        record = command._extra[PROVENANCE_KEY]
        assert record["source"] == "paste"
        assert record["prior"]["pronto"] == row["pronto"]

    @pytest.mark.asyncio
    async def test_the_second_row_is_kept_instead(self, fan):
        """Two noisy captures, two different answers. One gets replaced;
        the other works on this fan and its owner says so."""
        hass, device, _wig, _manager = fan
        listing = await _tangles(hass, device)
        row = listing["rows"][1]
        await _call(ws_tangle_keep, hass, {
            "id": 6, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": row["id"], "tested": True,
            "note": "the fan does what I expect",
        })
        after = await _tangles(hass, device)
        assert len(after["rows"]) == 1
        assert len(after["attested"]) == 1
        assert after["attested"][0]["classes"] == ["frame-disagreement"]

    @pytest.mark.asyncio
    async def test_a_flat_attestation_has_no_map_to_name(self, fan):
        """Nothing read this remote, so the record says so by carrying
        no map rather than by naming one it never used."""
        hass, device, _wig, _manager = fan
        listing = await _tangles(hass, device)
        result = await _call(ws_tangle_keep, hass, {
            "id": 6, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": listing["rows"][0]["id"],
            "tested": True,
        })
        assert "map" not in result["record"]
        assert result["record"]["key"].endswith("|-")
