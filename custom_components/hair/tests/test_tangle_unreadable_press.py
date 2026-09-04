"""Two different nulls, and the doors that tell them apart.

``CandidateVerdict.matches`` is None whenever nothing could be
compared, and that happens for two unrelated reasons.

On a wig with no field map there is no claim to check a press against
at all. The owner ruled that "nothing to disagree with" accepts, and it
still does: reading it as a miss made recapture structurally impossible
on flat wigs.

On a MAP-COVERED wig the same null also means the press could not be
read under the wig's own map. The owner pressed a Samsung remote at a
BAXI cell, the flow accepted the foreign code, and the comb re-flagged
the row on the next pass. There the reading is not absent, it FAILED,
and the noread ladder is the thing that says so.

THESE ARE THE REAL DOORS. ``pre_read`` builds the verdicts from real
wig fixtures and real codes, and ``ws_tangle_apply`` is the write. What
the popup does with the two verdicts is a source pin in
test_polish_rulings, because the judgment itself lives in TypeScript;
what it is judging is here, measured rather than assumed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import field_readers
from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    APPLY_DISAGREEMENT_UNDECLARED,
    FIELD_TIER_NO_LATTICE,
    FIELD_TIER_READ,
    list_tangles,
    pre_read,
    read_lattice,
    read_repair,
)
from custom_components.hair.websocket_api import ws_tangle_apply
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
WRONG_KEY = "heat_cool/medium/off/28"
CLAIM = {"mode": "heat_cool", "fan": "medium", "swing": "off", "temp": 25.0}


def _wig(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture(scope="module")
def komeco() -> Wig:
    return _wig(KOMECO)


@pytest.fixture(scope="module")
def dreo_wig() -> Wig:
    return _wig(DREO)


@pytest.fixture(scope="module")
def foreign(dreo_wig) -> str:
    """A press from the wrong remote entirely.

    The owner's Samsung at a BAXI cell, reproduced with what the
    fixtures have: a fan's code offered to an air conditioner's
    lattice. What matters is that it is not the family the cell's map
    reads, which is the whole of the field case.
    """
    return dreo_wig.signals[0].pronto


@pytest.fixture(scope="module")
def cells(komeco):
    return {cell_key(c): c for c in komeco.climate.cells}


@pytest.fixture(scope="module")
def lattice(komeco):
    return read_lattice(komeco.climate)


@pytest.fixture
def wired(fake_hass, komeco, tmp_path):
    """A Komeco device with one porthole over the target cell."""
    matrix = komeco.climate
    live = {cell_key(c): c for c in matrix.cells}
    device = IRDevice(name="Komeco", climate_matrix=True,
                      emitter_entity_ids=["infrared.blaster"])
    device.add_command(IRCommand(
        name="Heat_cool 25 medium off", category=CommandCategory.CUSTOM,
        protocol="PRONTO", code=live[TARGET_KEY].pronto, repeat_count=0,
        matrix_cell=dict(CLAIM),
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
    return fake_hass, device, matrix, live


@pytest.fixture
def flat(fake_hass, dreo_wig, tmp_path):
    """The same Dreo wig as a flat device, no lattice under it."""
    device = IRDevice(name="Dreo", emitter_entity_ids=["infrared.b"])
    for signal in dreo_wig.signals:
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


class TestTheListingSaysWhichWigThisIs:
    """The signal that separates the two nulls, and where it comes
    from. It is not on the verdict, because the verdict cannot know it:
    an unmapped wig and a mapped wig that could not read the press both
    arrive with no protocol and nothing compared. It is on the listing,
    it has been on the wire since the field tier shipped, and the
    frontend types already carry it."""

    def test_a_flat_device_reports_no_lattice(self, flat):
        _hass, device, _manager = flat
        listing = list_tangles(device, None)
        assert listing.rows, "the flat fixture must have open rows"
        assert listing.field_tier == FIELD_TIER_NO_LATTICE

    def test_a_matrix_device_with_a_map_reports_read(self, wired):
        _hass, device, matrix, _live = wired
        listing = list_tangles(device, matrix)
        assert listing.field_tier == FIELD_TIER_READ


class TestTheTwoNullsAreDistinguishable:
    """Both verdicts carry ``matches: None``. Everything else about
    them differs, and the pair below is what the popup keys on."""

    def test_a_flat_rows_null_has_no_map_behind_it(self, foreign):
        """No lattice, so nothing was ever going to be compared. This
        is the ruled accept, and the reason it is ruled."""
        verdict = pre_read(read_lattice(None), foreign)
        assert verdict.matches is None
        assert verdict.protocol is None
        assert verdict.declined == field_readers.NO_MAP

    def test_a_mapped_wigs_unreadable_press_is_the_other_null(
            self, lattice, foreign):
        """The owner's case. A map was there and the press defeated it,
        so there IS a reading that failed, and nothing to quote from
        it."""
        verdict = pre_read(lattice, foreign, CLAIM)
        assert verdict.matches is None
        assert verdict.protocol is None
        assert verdict.readable is False
        assert verdict.reads_as == {}

    def test_a_mapped_readable_matching_press_is_a_match(
            self, lattice, cells):
        """The healthy neighbour's bytes are what this cell should be
        storing, and they read as its own claim."""
        verdict = pre_read(lattice, cells[DONOR_KEY].pronto, CLAIM)
        assert verdict.matches is True
        assert verdict.protocol is not None

    def test_a_mapped_readable_mismatching_press_is_a_miss(
            self, lattice, cells):
        """False, not None, and with a reading to quote: this is the
        ladder that speaks in words, and it is unchanged."""
        verdict = pre_read(lattice, cells[WRONG_KEY].pronto, CLAIM)
        assert verdict.matches is False
        assert verdict.reads_as, "a worded rung needs something to say"


class TestTheDoorUnderTheLadder:
    """Use It Anyway at rung three, through the same write as every
    other declared override."""

    @pytest.mark.asyncio
    async def test_an_unreadable_press_can_be_forced_through_declared(
            self, wired, foreign):
        """The third rung applies, and the declaration is recorded. The
        record is the whole point: a person overriding a reading is
        evidence about the map, and it can only accumulate if it is
        written down."""
        hass, device, _matrix, live = wired
        connection = await _apply(
            hass, device, foreign,
            reading_disagreed=True, source="capture")
        connection.send_error.assert_not_called()
        assert live[TARGET_KEY].pronto == foreign
        record = read_repair(live[TARGET_KEY])
        assert record["reading_disagreed"]["user_attested"] is True

    @pytest.mark.asyncio
    async def test_a_flat_rows_press_still_goes_straight_in(self, flat):
        """The ruled behaviour, from the other end: a flat repair needs
        no declaration and is not refused."""
        hass, device, _manager = flat
        row = list_tangles(device, None).rows[0]
        clean = next(c for c in device.commands
                     if c.id != row.target.command_id).code
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": clean, "tested": True, "source": "capture",
        })
        connection.send_error.assert_not_called()
        assert device.get_command(row.target.command_id).code == clean

    @pytest.mark.asyncio
    async def test_a_readable_mismatch_is_still_refused_undeclared(
            self, wired, cells):
        """The worded ladder's door is untouched by this round."""
        hass, device, _matrix, live = wired
        was = live[TARGET_KEY].pronto
        connection = await _apply(hass, device, cells[WRONG_KEY].pronto)
        assert connection.send_error.call_args.args[1] == (
            APPLY_DISAGREEMENT_UNDECLARED)
        assert live[TARGET_KEY].pronto == was
