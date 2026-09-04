"""The tangle listing: what one device still has wrong with it.

`test_field_sweep.py` pins what the comb FINDS in a file.
`test_field_gate_to_closet.py` pins what adopt does with those findings.
This pins the third leg: a device somebody is holding, listed as things
that can be fixed, derived from the bytes the device carries RIGHT NOW.

The Komeco fixture makes the case for deriving rather than remembering
better than any argument could. Its own stored receipt is a version 1
receipt written before the field tier existed, and it says zero
suspects. A listing that read that receipt would tell the owner of a
device with 52 wrong cells that there was nothing to do.
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
    FIELD_TIER_NO_LATTICE,
    FIELD_TIER_READ,
    FIELD_TIER_UNMAPPED,
    TARGET_CELL,
    TARGET_COMMAND,
    list_tangles,
    pre_read,
    project_device,
    read_lattice,
)
from custom_components.hair.websocket_api import ws_device_tangles
from custom_components.hair.wig_comb import (
    CHECK_DUPLICATED_NEIGHBOUR,
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_DISAGREEMENT,
    FIELD_COORDINATE,
    POWER_FIELD,
    comb_wig,
    receipt_summary,
    stamp_receipt,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    cell_key,
    parse_wig,
)

from .util_disagreeing_capture import SECOND_OPEN_ROW

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
DREO = (FIXTURES / "wigs"
        / "dreo-fan-dr-haf004s-perfect-fit.wig.json")



def _wig(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


def _flagged(wig: Wig, check: str) -> set[str]:
    """The keys one check flagged. Cached: combing a 1,156-cell lattice
    is real arithmetic and several tests want the same answer."""
    cached = _FLAGGED_CACHE.get((id(wig), check))
    if cached is None:
        cached = {finding.keys[0] for finding in comb_wig(wig).findings
                  if finding.check == check}
        _FLAGGED_CACHE[(id(wig), check)] = cached
    return cached


_FLAGGED_CACHE: dict[tuple[int, str], set[str]] = {}


@pytest.fixture
def komeco_device():
    """The Komeco lattice as an adopted device, portholes and all.

    Built the way ``ws_wig_make_device`` builds one -- a matrix device
    plus a coordinate-named porthole command per flagged cell -- so the
    listing is exercised against the shape adopt actually produces.
    """
    wig = _wig(KOMECO)
    stamp_receipt(wig, comb_wig(wig), "2026-08-22")
    device = IRDevice(name="Komeco", climate_matrix=True)
    flagged = _flagged(wig, CHECK_FIELD_MISMATCH)
    for cell in wig.climate.cells:
        if cell_key(cell) not in flagged:
            continue
        # Names differ per swing on purpose: ``add_command`` REPLACES a
        # same-named command, so four cells sharing "Heat_cool 19
        # medium" would leave one porthole where there should be four.
        device.add_command(IRCommand(
            name=f"Heat_cool {cell.temp:g} {cell.fan} {cell.swing}",
            category=CommandCategory.CUSTOM,
            protocol="PRONTO",
            code=cell.pronto,
            repeat_count=0,
            matrix_cell={
                "mode": cell.mode, "fan": cell.fan,
                "swing": cell.swing, "temp": cell.temp,
            },
            comb_suspect=True,
            comb_finding=CHECK_FIELD_MISMATCH,
        ))
    return device, wig


@pytest.fixture
def dreo_device():
    """The Dreo fan as a flat device: seven buttons, one of them noisy.

    It was two until 0.14.1 A1: Speed Down is a capture the decoder
    reads whole, so its frames disagreeing is the protocol working
    rather than a bad capture, and it no longer reaches the work
    list.
    """
    wig = _wig(DREO)
    device = IRDevice(name="Dreo")
    for signal in wig.signals:
        device.add_command(IRCommand(
            name=signal.alias,
            category=CommandCategory.CUSTOM,
            protocol="PRONTO",
            code=signal.pronto,
            send_count=signal.send_count,
            repeat_count=signal.ditto_count,
            tx_force_raw=signal.bypass_protocol,
        ))
    return device, wig


class TestTheKomecoListing:
    def test_fifty_two_rows(self, komeco_device):
        """The number the whole fitting-integrity release exists for."""
        device, wig = komeco_device
        listing = list_tangles(device, wig.climate)
        assert len(listing.rows) == 52

    def test_on_the_coordinates_the_sweep_named(self, komeco_device):
        """A set, not a count that happens to match."""
        device, wig = komeco_device
        listing = list_tangles(device, wig.climate)
        assert {row.target.key for row in listing.rows} == _flagged(
            wig, CHECK_FIELD_MISMATCH)
        assert {row.target.kind for row in listing.rows} == {TARGET_CELL}

    def test_every_row_carries_its_vote(self, komeco_device):
        """"Wrong" is not a diagnosis. What it should send and what it
        does send, in the reader's own language, is."""
        device, wig = komeco_device
        listing = list_tangles(device, wig.climate)
        for row in listing.rows:
            assert row.classes == [CHECK_FIELD_MISMATCH]
            params = row.findings[0]["params"]
            assert params["field"] == "comb.field.temperature"
            assert params["protocol"] == "ZHLT01"
            assert params["expected"] != params["read"]

    def test_a_row_names_its_porthole(self, komeco_device):
        """The porthole is the command toolset's handle on a cell. A row
        that did not name it would leave the fix window unable to TEST
        the thing it is about to replace."""
        device, wig = komeco_device
        listing = list_tangles(device, wig.climate)
        assert all(row.target.command_id for row in listing.rows)
        ids = {row.target.command_id for row in listing.rows}
        assert len(ids) == 52

    def test_the_porthole_is_not_listed_twice(self, komeco_device):
        """A flagged cell lives in the lattice AND as a depth-0 command
        holding a copy of the same bytes. The lattice is the authority;
        listing both would offer one repair under two ids."""
        device, wig = komeco_device
        listing = list_tangles(device, wig.climate)
        assert not [r for r in listing.rows if r.target.kind == TARGET_COMMAND]

    def test_the_field_tier_reports_that_it_read(self, komeco_device):
        device, wig = komeco_device
        listing = list_tangles(device, wig.climate)
        assert listing.protocol == "ZHLT01"
        assert listing.field_tier == FIELD_TIER_READ
        assert "donor" in listing.candidate_sources

    def test_the_stored_receipt_would_have_said_nothing(self, komeco_device):
        """The reason this tier combs instead of remembering.

        The contributor's file carries a real receipt, and that receipt
        is honest about what it knew when it was written: zero suspects,
        version 1, no field tier in existence yet. Reading it would
        report a clean device.
        """
        _device, wig = komeco_device
        parsed = parse_wig(KOMECO.read_text())
        assert parsed.wig is not None
        stored = receipt_summary(parsed.wig)
        assert stored is not None
        assert stored["suspects"] == 0
        assert len(list_tangles(_device, wig.climate).rows) == 52


class TestTheDreoListing:
    def test_the_listing_is_exactly_what_the_comb_flagged(
        self, dreo_device
    ):
        """The claim has not moved: the rows ARE the flagged captures,
        counted from the same comb the listing runs. What moved is the
        number. 0.14.1 A1 stands Speed Down down, so the fan has one
        noisy capture where it used to have two, and both sides of this
        comparison say so together."""
        device, wig = dreo_device
        listing = list_tangles(device, None)
        assert len(listing.rows) == 1
        assert {row.target.key for row in listing.rows} == _flagged(
            wig, CHECK_FRAME_DISAGREEMENT)

    def test_rows_address_commands_by_id(self, dreo_device):
        device, _wig = dreo_device
        listing = list_tangles(device, None)
        on_device = {command.id for command in device.commands}
        for row in listing.rows:
            assert row.target.kind == TARGET_COMMAND
            assert row.target.command_id in on_device
            assert row.id == f"{TARGET_COMMAND}:{row.target.command_id}"

    def test_a_flat_device_is_told_it_has_no_lattice(self, dreo_device):
        """No oracle, so no donors -- and saying which sources DO exist
        is better than an empty donor field the caller has to interpret."""
        device, _wig = dreo_device
        listing = list_tangles(device, None)
        assert listing.field_tier == FIELD_TIER_NO_LATTICE
        assert listing.candidate_sources == ["capture", "paste"]
        assert all(row.has_donor is False for row in listing.rows)


class TestHonestSilence:
    def test_a_clean_device_lists_nothing(self, dreo_device):
        """Zero findings is zero rows, not an empty shell with a
        reassuring header."""
        _device, wig = dreo_device
        clean = IRDevice(name="Clean")
        good = {s.alias for s in wig.signals} - _flagged(
            wig, CHECK_FRAME_DISAGREEMENT)
        for signal in wig.signals:
            if signal.alias not in good:
                continue
            clean.add_command(IRCommand(
                name=signal.alias, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=signal.pronto,
            ))
        assert list_tangles(clean, None).rows == []

    def test_an_unmapped_lattice_says_so(self):
        """A lattice no map covers passes every protocol-blind check and
        has not one byte of its payload read. That is not a clean bill,
        and the listing has to be able to tell them apart."""
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto="0000 006D 0004 0000 0060 0020 "
                               "0020 0020 0020 0020 0020 0060")
            for t in (20, 21)
        ]
        matrix = ClimateMatrix(
            min_temp=20.0, max_temp=21.0, off="0000 006D 0002 0000 "
            "0060 0020 0020 0060", cells=cells,
            modes=["cool"], fan_modes=["auto"],
        )
        device = IRDevice(name="Unmapped", climate_matrix=True)
        listing = list_tangles(device, matrix)
        assert listing.protocol is None
        assert listing.field_tier == FIELD_TIER_UNMAPPED
        assert "donor" not in listing.candidate_sources

    def test_a_device_with_nothing_to_export_lists_nothing(self):
        """No commands and no lattice: the projection has no wig to
        comb, and the honest answer is an empty listing rather than a
        crash on None."""
        assert list_tangles(IRDevice(name="Bare"), None).rows == []


class TestDerivedNotRemembered:
    def test_repairing_the_bytes_drops_the_finding(self, komeco_device):
        """The whole point of deriving. Nothing is invalidated, nothing
        is refreshed: the next call combs different bytes and reaches a
        different answer."""
        device, wig = komeco_device
        matrix = wig.climate
        target_key = "heat_cool/medium/off/25"
        before = list_tangles(device, matrix)
        assert CHECK_FIELD_MISMATCH in next(
            r for r in before.rows if r.target.key == target_key).classes

        donor = next(c for c in matrix.cells
                     if cell_key(c) == "heat_cool/medium/off/24")
        cell = next(c for c in matrix.cells if cell_key(c) == target_key)
        assert cell.pronto != donor.pronto
        cell.pronto = donor.pronto

        after = list_tangles(device, matrix)
        mismatches = [r for r in after.rows
                      if CHECK_FIELD_MISMATCH in r.classes]
        assert len(mismatches) == 51
        assert target_key not in {r.target.key for r in mismatches}

    def test_one_donor_fix_inside_a_shift_leaves_a_twin(self, komeco_device):
        """Honest consequence, pinned rather than hidden.

        The defective column is a SHIFT: every cell sends what the next
        one up should send, so the correct bytes for 25 are the bytes 24
        is carrying today. Copying them repairs 25 and, until 24 is
        repaired from 23, leaves the two cells byte-identical -- which
        the duplicated-neighbour check then reports, correctly.

        The pair is an artifact of stopping halfway, not of the donor
        rule. Applying the whole cause at once walks the shift back and
        the twins never exist; this is why repairs are batched per cause
        rather than offered one cell at a time.
        """
        device, wig = komeco_device
        matrix = wig.climate
        cells = {cell_key(c): c for c in matrix.cells}
        cells["heat_cool/medium/off/25"].pronto = cells[
            "heat_cool/medium/off/24"].pronto

        rows = {r.target.key: r for r in list_tangles(device, matrix).rows}
        assert CHECK_DUPLICATED_NEIGHBOUR in rows[
            "heat_cool/medium/off/25"].classes
        assert CHECK_DUPLICATED_NEIGHBOUR in rows[
            "heat_cool/medium/off/24"].classes
        assert CHECK_FIELD_MISMATCH in rows[
            "heat_cool/medium/off/24"].classes

    def test_the_digest_follows_the_bytes(self, dreo_device):
        """Swapped for OTHER bytes the comb also flags, so the row
        survives the edit and the digest is the only thing that moved.

        The other bytes used to be the fan's second noisy capture. A1
        stood that one down, so they are built here instead, and the
        substitution is the same one: still flagged, still this row."""
        device, _wig = dreo_device
        rows = list_tangles(device, None).rows
        first = rows[0]
        command = next(c for c in device.commands
                       if c.id == first.target.command_id)
        assert first.pronto == command.code
        command.code = SECOND_OPEN_ROW
        again = next(
            r for r in list_tangles(device, None).rows
            if r.target.command_id == command.id
        )
        assert again.digest != first.digest
        assert again.pronto == command.code


class TestOverTheWire:
    @pytest.fixture
    def wired(self, fake_hass, komeco_device):
        device, wig = komeco_device
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=wig.climate)
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        return fake_hass, device, manager

    @pytest.mark.asyncio
    async def test_the_handler_returns_the_listing(self, wired):
        hass, device, _manager = wired
        connection = MagicMock()
        await ws_device_tangles(hass, connection, {
            "id": 1, "type": "hair/device/tangles", "device_id": device.id,
        })
        connection.send_error.assert_not_called()
        payload = connection.send_result.call_args.args[1]
        assert len(payload["rows"]) == 52
        assert payload["matrix"] is True
        assert payload["protocol"] == "ZHLT01"
        assert payload["coverage"]["protocol"]["readable"] == 1157

    @pytest.mark.asyncio
    async def test_an_unknown_device_is_a_refusal(self, wired):
        hass, _device, manager = wired
        manager.get_device = MagicMock(return_value=None)
        connection = MagicMock()
        await ws_device_tangles(hass, connection, {
            "id": 1, "type": "hair/device/tangles", "device_id": "nope",
        })
        connection.send_result.assert_not_called()
        assert connection.send_error.call_args.args[1] == "not_found"
class TestTheWitnessComparisonHasTheKeysItNeeds:
    """Issue 18, found live 2026-08-30: the witness happy path could
    never match.

    A bench send of a wig's own vertical/26 frame, verified reading
    temperature 26, at that wig's own armed 26C witness row, answered
    "Heard 26. Check the remote's display and try again." The reading
    was right and the ask was right; the comparison was reading one of
    them with the other's key.

    A verdict's ``reads_as`` is keyed by MAP FIELD NAME, because that
    is what the field map calls it. A target's ``coordinates`` are
    keyed by CELL AXIS, because that is what the lattice calls it.
    ``FIELD_COORDINATE`` is the bridge, and the frontend mirrors it in
    one constant.

    These pins hold the two vocabularies apart on the backend side,
    where nothing in TypeScript can notice a rename. The fixture is the
    Komeco's own witness cluster, the same shape as the small-shift AC
    left standing on the bench box.
    """

    @pytest.fixture
    def witness(self, komeco_device):
        device, wig = komeco_device
        matrix = wig.climate
        listing = list_tangles(device, matrix)
        cluster = next(
            c for c in listing.clusters if c.mechanic == "witness"
        )
        rows = {row.id: row for row in listing.rows}
        return device, matrix, cluster, rows[cluster.members[0]]

    def test_a_witness_cluster_names_a_map_field(self, witness):
        _device, _matrix, cluster, _row = witness
        assert cluster.field == "temperature"
        assert cluster.field in FIELD_COORDINATE

    def test_the_field_name_is_not_a_coordinate_key(self, witness):
        """THE BUG, stated as a fact about the data. Indexing the
        coordinates with the cluster's own field name yields nothing,
        which is why every witness capture missed: the value it was
        compared against was undefined."""
        _device, _matrix, cluster, row = witness
        assert cluster.field not in row.target.coordinates
        assert row.target.coordinates.get(cluster.field) is None

    def test_the_axis_is_where_the_asked_value_lives(self, witness):
        _device, _matrix, cluster, row = witness
        axis = FIELD_COORDINATE[cluster.field]
        assert axis == "temp"
        assert row.target.coordinates[axis] == 19.0

    def test_a_capture_reading_the_asked_value_says_so_under_the_field(
        self, witness
    ):
        """THE REGRESSION CASE, on real fixture bytes. A witness press
        from a different fan branch reads the asked temperature
        exactly. Its verdict still says matches is False, because the
        fan axis honestly disagrees, which is exactly why the witness
        flow compares the witnessed FIELD rather than the verdict, and
        exactly why the field has to be translated first.

        Translated, 19.0 meets 19.0 and the row settles. Untranslated,
        19.0 meets None and a perfect press climbs the ladder.
        """
        device, matrix, cluster, row = witness
        wig, _sources = project_device(device, matrix)
        lattice = read_lattice(matrix, wig)
        press = next(
            cell for cell in matrix.cells
            if cell_key(cell) == "cool/auto/off/19"
        )
        verdict = pre_read(lattice, press.pronto, row.target.coordinates)
        reads_as = verdict.as_dict()["reads_as"]

        assert reads_as[cluster.field] == 19.0
        assert verdict.as_dict()["matches"] is False

        asked = row.target.coordinates[FIELD_COORDINATE[cluster.field]]
        assert reads_as[cluster.field] == asked
        assert row.target.coordinates.get(cluster.field) is None

    def test_every_field_a_cluster_can_name_has_an_axis(self, witness):
        """Four field names, four axes, and the frontend mirrors this
        table. A fifth field added on the backend without its mirror
        would make that field's clusters unmatchable in exactly the way
        temperature was."""
        _device, _matrix, _cluster, _row = witness
        assert set(FIELD_COORDINATE) == {
            "temperature", "mode", "fan_speed", "swing",
        }
        assert set(FIELD_COORDINATE.values()) == {
            "temp", "mode", "fan", "swing",
        }
        assert POWER_FIELD == "power"

    def test_no_cluster_names_a_field_the_bridge_cannot_cross(
        self, witness
    ):
        device, matrix, _cluster, _row = witness
        for cluster in list_tangles(device, matrix).clusters:
            if cluster.field is None:
                continue
            assert (
                cluster.field in FIELD_COORDINATE
                or cluster.field == POWER_FIELD
            )
