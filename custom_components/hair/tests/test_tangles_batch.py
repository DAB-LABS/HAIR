"""One cause, one run.

Fittings never walked six hundred cells; a dimension check attests axes.
Repairs follow the same philosophy: a run presses at a representative
sample spanning the card's modes and, on a pass, writes every member in
one batch, with each cell's record honest about which tier it got.

The batch is not only the safe unit, it is the CORRECT one. The Komeco
column is a shift, so the right bytes for one cell are the bytes the cell
below it is carrying right now. Apply one cell of that cause and it ends
up byte-identical to its still-broken neighbour, which the duplicate
check then reports -- correctly. Apply the whole cause and the shift
walks back and the twins never exist.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import field_readers
from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRDevice
from custom_components.hair.tangles import (
    BATCH_SAMPLE_SHORT,
    TIER_AIR_TESTED,
    TIER_RULE_DERIVED,
    choose_sample,
    list_tangles,
    read_lattice,
    read_repair,
    rewrite_field,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply_batch,
    ws_tangle_plan,
    ws_tangle_revert_run,
)
from custom_components.hair.wig_comb import comb_wig
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

DONOR_CARD = "same-shift:temperature:1:donor"
WITNESS_CARD = "same-shift:temperature:1:witness"


def _wig() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture
def wired(fake_hass, tmp_path):
    wig = _wig()
    device = IRDevice(name="Komeco", climate_matrix=True,
                      emitter_entity_ids=["infrared.blaster"])
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=wig.climate)
    manager.async_update_device = AsyncMock()
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "matrix_listener": MagicMock(),
    }}
    return fake_hass, device, wig


def _press(lattice, wig, row):
    """A capture that reads as the row's own label on this hardware.

    Stands in for the press: built from a healthy cell of the same
    column, so it carries the remote's own timings the way a real
    capture would.
    """
    spec = lattice.spec_for("temperature")
    cells = {cell_key(c): c for c in wig.climate.cells}
    coordinates = row.target.coordinates
    sibling = cells[
        f"{coordinates['mode']}/{coordinates['fan']}"
        f"/{coordinates['swing']}/16"
    ]
    built = rewrite_field(
        lattice.field_map, sibling.pronto, spec,
        field_readers.expected_value(spec, coordinates["temp"]),
    )
    assert built is not None
    return built


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _plan(hass, device, cluster, **extra):
    connection = _conn()
    payload = {"id": 1, "type": "hair/device/tangle/plan",
               "device_id": device.id, "cluster": cluster}
    payload.update(extra)
    await ws_tangle_plan(hass, connection, payload)
    connection.send_error.assert_not_called()
    return connection.send_result.call_args.args[1]


async def _run(hass, device, cluster, tested, **extra):
    connection = _conn()
    payload = {
        "id": 2, "type": "hair/device/tangle/apply-batch",
        "device_id": device.id, "cluster": cluster,
        "tested": True, "tested_targets": tested,
    }
    payload.update(extra)
    await ws_tangle_apply_batch(hass, connection, payload)
    return connection


class TestChoosingWhatToPressAt:
    def test_modes_come_first(self, wired):
        _hass, device, wig = wired
        listing = list_tangles(device, wig.climate)
        rows = {row.id: row for row in listing.rows}
        card = next(c for c in listing.clusters if c.id == DONOR_CARD)
        sample = choose_sample(rows, card.members)
        assert 1 <= len(sample) <= 2
        assert set(sample) <= set(card.members)

    def test_a_single_member_card_tests_that_member(self, wired):
        _hass, device, wig = wired
        listing = list_tangles(device, wig.climate)
        rows = {row.id: row for row in listing.rows}
        only = listing.rows[0].id
        assert choose_sample(rows, [only]) == [only]

    def test_the_choice_is_stable(self, wired):
        _hass, device, wig = wired
        listing = list_tangles(device, wig.climate)
        rows = {row.id: row for row in listing.rows}
        card = next(c for c in listing.clusters if c.id == DONOR_CARD)
        assert choose_sample(rows, card.members) == choose_sample(
            rows, card.members)


class TestThePlan:
    @pytest.mark.asyncio
    async def test_a_donor_card_resolves_every_member(self, wired):
        hass, device, _wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        assert plan["refused"] is None
        assert len(plan["candidates"]) == 48
        assert plan["declined"] == {}
        assert plan["sample"]

    @pytest.mark.asyncio
    async def test_every_candidate_arrives_with_its_read_back(self, wired):
        hass, device, _wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        for candidate in plan["candidates"].values():
            assert candidate["verdict"]["matches"] is True
            assert candidate["origin"] == "donor"

    @pytest.mark.asyncio
    async def test_the_plan_writes_nothing(self, wired):
        hass, device, wig = wired
        before = [cell.pronto for cell in wig.climate.cells]
        await _plan(hass, device, DONOR_CARD)
        assert [cell.pronto for cell in wig.climate.cells] == before

    @pytest.mark.asyncio
    async def test_a_witness_card_needs_a_witness(self, wired):
        """No donor anywhere, and nothing supplied: the card resolves to
        nothing rather than to something invented."""
        hass, device, _wig = wired
        plan = await _plan(hass, device, WITNESS_CARD)
        assert plan["refused"] == "nothing_to_apply"

    @pytest.mark.asyncio
    async def test_the_whole_card_is_resolved_before_anything_moves(
            self, wired):
        """On a shifted column, resolving as you write would walk the
        shift down and hand back codes it had just replaced. Every
        candidate here comes from the lattice as it stands."""
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        cells = {cell_key(c): c for c in wig.climate.cells}
        for candidate in plan["candidates"].values():
            donor = candidate["donor"]
            assert cells[donor].pronto == candidate["pronto"]


class TestTheRun:
    @pytest.mark.asyncio
    async def test_a_pass_writes_every_member(self, wired):
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        connection = await _run(hass, device, DONOR_CARD, plan["sample"])
        connection.send_error.assert_not_called()
        result = connection.send_result.call_args.args[1]
        assert result["applied"] == 48
        cells = {cell_key(c): c for c in wig.climate.cells}
        for member, candidate in plan["candidates"].items():
            assert cells[member.split(":", 1)[1]].pronto == candidate[
                "pronto"]

    @pytest.mark.asyncio
    async def test_the_record_says_which_tier_each_cell_got(self, wired):
        """Honest about what was proved. The pressed cells are
        air-tested; the rest are rule-derived, and the record names the
        cells the rule was proved on."""
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        await _run(hass, device, DONOR_CARD, plan["sample"])
        cells = {cell_key(c): c for c in wig.climate.cells}
        tested_keys = {t.split(":", 1)[1] for t in plan["sample"]}
        tiers = {}
        for member in plan["candidates"]:
            key = member.split(":", 1)[1]
            record = read_repair(cells[key])
            tiers[key] = record["tier"]
            assert set(record["tested_cells"]) == tested_keys
        for key, tier in tiers.items():
            expected = (TIER_AIR_TESTED if key in tested_keys
                        else TIER_RULE_DERIVED)
            assert tier == expected

    @pytest.mark.asyncio
    async def test_one_run_one_id(self, wired):
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        connection = await _run(hass, device, DONOR_CARD, plan["sample"])
        run = connection.send_result.call_args.args[1]["run"]
        cells = {cell_key(c): c for c in wig.climate.cells}
        runs = {
            read_repair(cells[m.split(":", 1)[1]])["run"]
            for m in plan["candidates"]
        }
        assert runs == {run}

    @pytest.mark.asyncio
    async def test_an_untested_mode_refuses_the_whole_run(self, wired):
        """A rule proved in cooling is exactly the kind of thing that
        does not hold in heating."""
        hass, device, wig = wired
        before = [cell.pronto for cell in wig.climate.cells]
        connection = await _run(hass, device, DONOR_CARD, [])
        assert connection.send_error.call_args.args[1] == BATCH_SAMPLE_SHORT
        assert [cell.pronto for cell in wig.climate.cells] == before

    @pytest.mark.asyncio
    async def test_a_failed_run_leaves_the_lattice_byte_identical(
            self, wired, monkeypatch):
        """No partial batches, ever -- proved by comparing every cell,
        not by trusting the code path."""
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        before = [cell.pronto for cell in wig.climate.cells]

        def _boom(*args, **kwargs):
            raise OSError("disk went away")

        monkeypatch.setattr(
            "custom_components.hair.matrix_store.write_matrix", _boom)
        connection = await _run(hass, device, DONOR_CARD, plan["sample"])
        assert connection.send_error.call_args.args[1] == "write_failed"
        assert [cell.pronto for cell in wig.climate.cells] == before
        assert all(read_repair(cell) is None for cell in wig.climate.cells)

    @pytest.mark.asyncio
    async def test_the_card_leaves_the_listing(self, wired):
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        await _run(hass, device, DONOR_CARD, plan["sample"])
        cards = {c.id for c in list_tangles(device, wig.climate).clusters}
        assert DONOR_CARD not in cards


class TestUndoingARun:
    @pytest.mark.asyncio
    async def test_one_apply_is_one_undo(self, wired):
        hass, device, wig = wired
        before = [cell.pronto for cell in wig.climate.cells]
        plan = await _plan(hass, device, DONOR_CARD)
        connection = await _run(hass, device, DONOR_CARD, plan["sample"])
        run = connection.send_result.call_args.args[1]["run"]

        undo = _conn()
        await ws_tangle_revert_run(hass, undo, {
            "id": 3, "type": "hair/device/tangle/revert-run",
            "device_id": device.id, "run": run,
        })
        undo.send_error.assert_not_called()
        assert [cell.pronto for cell in wig.climate.cells] == before
        assert all(read_repair(cell) is None for cell in wig.climate.cells)

    @pytest.mark.asyncio
    async def test_an_unknown_run_says_so(self, wired):
        hass, device, _wig = wired
        connection = _conn()
        await ws_tangle_revert_run(hass, connection, {
            "id": 3, "type": "hair/device/tangle/revert-run",
            "device_id": device.id, "run": "nope",
        })
        assert connection.send_error.call_args.args[1] == (
            "nothing_to_revert")

    @pytest.mark.asyncio
    async def test_a_second_run_is_undone_on_its_own(self, wired):
        """Two runs, one taken back: the other stays."""
        hass, device, wig = wired
        first = await _plan(hass, device, DONOR_CARD)
        run_one = (await _run(
            hass, device, DONOR_CARD, first["sample"]
        )).send_result.call_args.args[1]["run"]

        listing = list_tangles(device, wig.climate)
        witness = next(c for c in listing.clusters
                       if c.mechanic == "witness")
        rows = {r.id: r for r in listing.rows}
        lattice = read_lattice(wig.climate)
        aimed = sorted(witness.members)[0]
        press = _press(lattice, wig, rows[aimed])
        second = await _plan(
            hass, device, witness.id, witness=press, witness_target=aimed)
        await _run(hass, device, witness.id, second["sample"],
                   witness=press, witness_target=aimed)

        undo = _conn()
        await ws_tangle_revert_run(hass, undo, {
            "id": 3, "type": "hair/device/tangle/revert-run",
            "device_id": device.id, "run": run_one,
        })
        undo.send_error.assert_not_called()
        cells = {cell_key(c): c for c in wig.climate.cells}
        for member, candidate in second["candidates"].items():
            assert cells[member.split(":", 1)[1]].pronto == candidate[
                "pronto"]


class TestTheCauseIsTheUnit:
    @pytest.mark.asyncio
    async def test_the_shift_walks_back_inside_the_card(self, wired):
        """Why a cause is applied whole.

        One cell of this card, applied alone, ends up byte-identical to
        the neighbour it copied from until that neighbour is repaired
        too. Applied whole, the shift walks back in one step and no two
        cells the card touched carry the same code.

        The card's lower EDGE is a different matter and is not a defect:
        cell 20 takes what 19 was carrying, and 19 belongs to the card
        that needs a press, so the two match until that press happens.
        The comb reports the pair, correctly.
        """
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        await _run(hass, device, DONOR_CARD, plan["sample"])
        touched = [m.split(":", 1)[1] for m in plan["candidates"]]
        cells = {cell_key(c): c for c in wig.climate.cells}
        codes = [cells[key].pronto for key in touched]
        assert len(set(codes)) == len(codes)

        twins = [
            f for f in comb_wig(wig).findings
            if f.check == "duplicated-neighbour"
        ]
        assert {f.params["temp"] for f in twins} == {"20"}
        assert {f.params["other"] for f in twins} == {"19"}

    @pytest.mark.asyncio
    async def test_the_whole_chain_is_one_card(self, wired):
        """The cells at the top of the range are the same mistake as the
        rest of the column -- a four-bit field wrapping is still one step
        high. Split apart they break each other: whichever card ran first
        would either overwrite the donor the other was waiting on, or
        leave a byte-identical twin at the seam that reclassifies a cell
        out of its own card.
        """
        _hass, device, wig = wired
        cards = list_tangles(device, wig.climate).clusters
        assert len(cards) == 2
        donor = next(c for c in cards if c.mechanic == "donor")
        assert donor.size == 48
        assert donor.detail["step"] == 1
        keys = {m.rsplit("/", 1)[-1] for m in donor.members}
        assert "31" in keys and "20" in keys

    @pytest.mark.asyncio
    async def test_donors_and_one_press_leave_the_file_clean(self, wired):
        """The whole loop through the shipped handlers.

        One run repairs 48 cells, one press repairs the four nobody
        could copy for, and the comb comes back with nothing.
        """
        hass, device, wig = wired
        plan = await _plan(hass, device, DONOR_CARD)
        connection = await _run(hass, device, DONOR_CARD, plan["sample"])
        connection.send_error.assert_not_called()

        listing = list_tangles(device, wig.climate)
        card = next(c for c in listing.clusters if c.mechanic == "witness")
        rows = {r.id: r for r in listing.rows}
        aimed = sorted(card.members)[0]
        press = _press(read_lattice(wig.climate), wig, rows[aimed])
        second = await _plan(
            hass, device, card.id, witness=press, witness_target=aimed)
        assert second["refused"] is None
        assert len(second["candidates"]) == 4
        connection = await _run(
            hass, device, card.id, second["sample"],
            witness=press, witness_target=aimed)
        connection.send_error.assert_not_called()

        assert comb_wig(wig).findings == []
        assert list_tangles(device, wig.climate).rows == []
