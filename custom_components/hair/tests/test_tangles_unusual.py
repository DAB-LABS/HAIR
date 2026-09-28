"""The Unusual card: a finding that means "looks odd", not "is wrong".

GH Discussion #177. A TV remote showed Needs attention on a few codes
because their frames were a different shape from the rest of the
remote. Fix "didn't quite work", and it could not: a frame-shape row on
a flat remote has no donor, so it landed in LISTEN and asked for a
fresh press, and a button that really sends that shape sends it every
time. The press was accepted, written, combed again, and the same row
came back. Meanwhile the open row held up a Perfect Fit.

Owner rulings, 2026-09-27 and 2026-09-28:

- A row is Unusual when EVERY class on it is in ``UNUSUAL_CLASSES`` AND
  HAIR has no candidate for it. A row carrying any other class keeps
  the bucket it had, and a row HAIR can already repair (a trimmable
  stray burst on a lattice) stays under Fixes ready.
- The class list lives in one place, served by the listing.
- Unusual rows do not hold up a Perfect Fit.
- "It Works, Keep It" is the existing keep door, and a kept row settles
  exactly as a kept row always has.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    FIT_HAS_TANGLES,
    ORIGIN_TRIM,
    TARGET_COMMAND,
    UNUSUAL_CLASSES,
    TangleListing,
    TangleRow,
    TangleTarget,
    blocking_rows,
    is_unusual,
    list_tangles,
    rederive_comb_stamps,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply,
    ws_tangle_keep,
    ws_wigs_save,
)
from custom_components.hair.wig_comb import (
    CHECK_BYPASS_WITH_DITTOS,
    CHECK_DUPLICATE_LABELS,
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_SHAPE,
    CHECK_MALFORMED,
    CHECK_RAMP_DITTOS,
    CHECK_STRAY_BURST,
    CHECK_STRAY_CELL,
)
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# --- fixtures -------------------------------------------------------------


def _flat_code(frames: list[int], seed: int = 0) -> str:
    """A Pronto whose frame shape is exactly ``frames`` (the comb's own
    test idiom). ``seed`` varies the mark so no two codes collide."""
    pairs: list[tuple[int, int]] = []
    for count in frames:
        for i in range(count):
            space = 0x0500 if i == count - 1 else 0x0020
            pairs.append((0x0020 + seed, space))
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


#: The #177 shape: every button sends two frames, one sends three. The
#: totals stay inside the flat comb's 2x band, so the finding is the
#: frame-COUNT outlier, which is what nbarnard's remote reported.
ODD = "Input"
ODD_CODE = _flat_code([12, 12, 12], seed=9)
#: A fresh press of the same button: same three frames, a hair different.
ODD_PRESS = _flat_code([12, 12, 12], seed=10)


def _tv() -> IRDevice:
    device = IRDevice(name="TV", emitter_entity_ids=["infrared.b"])
    for i in range(6):
        device.add_command(IRCommand(
            name=f"Key {i}", category=CommandCategory.CUSTOM,
            protocol="PRONTO", code=_flat_code([12, 12], seed=i),
        ))
    device.add_command(IRCommand(
        name=ODD, category=CommandCategory.CUSTOM,
        protocol="PRONTO", code=ODD_CODE,
    ))
    return device


def _wire(fake_hass, tmp_path, device, matrix=None):
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    manager.async_update_device = AsyncMock()
    store = MagicMock()
    store.get_device = MagicMock(return_value=device)
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "store": store,
        "matrix_listener": MagicMock(), "fitting_manager": None,
    }}
    return fake_hass


@pytest.fixture
def tv(fake_hass, tmp_path):
    device = _tv()
    return _wire(fake_hass, tmp_path, device), device


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


def _row(classes: list[str], has_donor: bool = False) -> TangleRow:
    return TangleRow(
        id="command:x",
        target=TangleTarget(kind=TARGET_COMMAND, key="X", command_id="x"),
        classes=classes, findings=[], pronto="", digest="d",
        has_donor=has_donor,
    )


def replace_id(row: TangleRow, row_id: str) -> TangleRow:
    return replace(row, id=row_id)


def _odd_row(device: IRDevice) -> TangleRow:
    return next(r for r in list_tangles(device, None).rows
                if r.target.key == ODD)


# --- the lattice fixture: stray bursts with and without a candidate ------

#: Above PRONTO_GAP_THRESHOLD so the comb splits frames here (the same
#: construction test_comb_frame_disagreement's trim tests use).
_SPLIT = 0x0800
_TRAILER = 0x09C4


def _lattice_code(bits: str, dangle: bool = False) -> str:
    pairs = []
    for _ in range(2):
        body = [((0x002E if b == "1" else 0x0010), 0x0010) for b in bits]
        last = len(body) - 1
        for index, (mark, space) in enumerate(body):
            pairs.append((mark, _SPLIT if index == last else space))
    if dangle:
        pairs.append((0x0010, _TRAILER))
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


def _held_dangle(bits: str) -> str:
    """A stray burst the trim builder must refuse: the dangling pair is
    declared as the Pronto repeat sequence, so deleting it would rewrite
    what a blaster loops while the button is held
    (TRIM_HAS_REPEAT_SEQUENCE). A stray burst HAIR cannot repair."""
    words = _lattice_code(bits, dangle=True).split()
    total = int(words[2], 16)
    words[2] = f"{total - 1:04X}"
    words[3] = "0001"
    return " ".join(words)


def _lattice(odd: str) -> ClimateMatrix:
    first = _lattice_code("110100100101")
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, off=first,
        cells=[
            ClimateCell(mode="cool", pronto=first, temp=20.0),
            ClimateCell(mode="cool", pronto=_lattice_code("110100100110"),
                        temp=21.0),
            ClimateCell(mode="cool", pronto=odd, temp=22.0),
        ],
    )


TRIMMABLE = _lattice(_lattice_code("110100100011", dangle=True))
UNTRIMMABLE = _lattice(_held_dangle("110100100011"))


def _ac() -> IRDevice:
    return IRDevice(name="AC", climate_matrix=True,
                    emitter_entity_ids=["infrared.b"])


def _stray(matrix: ClimateMatrix) -> TangleRow:
    return next(r for r in list_tangles(_ac(), matrix).rows
                if CHECK_STRAY_BURST in r.classes)


# --- the class list -------------------------------------------------------


class TestTheOneList:
    def test_it_names_the_four_ruled_classes(self):
        assert set(UNUSUAL_CLASSES) == {
            CHECK_FRAME_SHAPE, CHECK_STRAY_BURST,
            CHECK_BYPASS_WITH_DITTOS, CHECK_RAMP_DITTOS,
        }

    def test_stray_cell_is_not_moved_this_round(self):
        assert CHECK_STRAY_CELL not in UNUSUAL_CLASSES

    def test_the_listing_serves_it(self, tv):
        """The panel reads the list from here and nowhere else."""
        _hass, device = tv
        served = list_tangles(device, None).as_dict()
        assert served["unusual_classes"] == list(UNUSUAL_CLASSES)

    def test_an_empty_listing_still_serves_it(self):
        assert TangleListing().as_dict()["unusual_classes"] == list(
            UNUSUAL_CLASSES)


# --- the predicate --------------------------------------------------------


class TestIsUnusual:
    @pytest.mark.parametrize("check", UNUSUAL_CLASSES)
    def test_one_unusual_class_and_no_candidate(self, check):
        assert is_unusual(_row([check])) is True

    def test_several_unusual_classes_together(self):
        assert is_unusual(_row([CHECK_FRAME_SHAPE, CHECK_STRAY_BURST]))

    def test_the_stricter_bucket_wins(self):
        """Odd shape AND malformed is malformed."""
        assert is_unusual(_row([CHECK_FRAME_SHAPE, CHECK_MALFORMED])) is False
        assert is_unusual(
            _row([CHECK_STRAY_BURST, CHECK_FIELD_MISMATCH])) is False

    def test_a_promoted_duplicate_pair_is_not_unusual(self):
        assert is_unusual(
            _row([CHECK_FRAME_SHAPE, CHECK_DUPLICATE_LABELS])) is False

    def test_stray_cell_alone_is_not_unusual(self):
        assert is_unusual(_row([CHECK_STRAY_CELL])) is False

    def test_a_row_with_no_classes_is_not_unusual(self):
        assert is_unusual(_row([])) is False

    def test_a_row_hair_can_repair_is_not_unusual(self):
        """The donor side of the 2026-09-28 ruling, on its own."""
        assert is_unusual(_row([CHECK_STRAY_BURST], has_donor=True)) is False
        assert is_unusual(_row([CHECK_FRAME_SHAPE], has_donor=True)) is False


class TestTheDonorRuleOnARealLattice:
    """Both sides of 2026-09-28 against rows the comb actually raises."""

    def test_a_trimmable_stray_burst_stays_under_fixes_ready(self):
        row = _stray(TRIMMABLE)
        assert row.classes == [CHECK_STRAY_BURST]
        assert row.has_donor is True
        assert row.donor["reasoning"]["origin"] == ORIGIN_TRIM
        assert is_unusual(row) is False
        served = list_tangles(_ac(), TRIMMABLE).as_dict()["rows"]
        assert [r["unusual"] for r in served if r["id"] == row.id] == [False]

    def test_a_stray_burst_hair_cannot_trim_is_unusual(self):
        row = _stray(UNTRIMMABLE)
        assert row.classes == [CHECK_STRAY_BURST]
        assert row.has_donor is False
        assert is_unusual(row) is True
        served = list_tangles(_ac(), UNTRIMMABLE).as_dict()["rows"]
        assert [r["unusual"] for r in served if r["id"] == row.id] == [True]


# --- the #177 remote ------------------------------------------------------


class TestTheRemoteFromDiscussion177:
    def test_the_odd_button_is_a_frame_shape_row_with_no_donor(self, tv):
        """The reproduction's starting point: one frame-count outlier on
        a flat remote, and nothing HAIR could build to replace it."""
        _hass, device = tv
        listing = list_tangles(device, None)
        assert [r.target.key for r in listing.rows] == [ODD]
        row = listing.rows[0]
        assert row.classes == [CHECK_FRAME_SHAPE]
        assert row.findings[0]["message"] == "comb.frame_count"
        assert row.has_donor is False

    def test_it_is_marked_unusual_on_the_wire(self, tv):
        """Unusual, not LISTEN: the panel buckets on this flag."""
        _hass, device = tv
        rows = list_tangles(device, None).as_dict()["rows"]
        assert [(r["target"]["key"], r["unusual"]) for r in rows] == [
            (ODD, True)]

    @pytest.mark.asyncio
    async def test_a_fresh_press_cannot_clear_it(self, tv):
        """THE DEAD END, pinned. This is what LISTEN offered: a press on
        a flat wig is accepted (there is no map to disagree with), the
        bytes are written, and the comb raises the same row on the new
        bytes, because the button really sends three frames. Nothing
        about this is wrong; it is why the row needed a keep instead."""
        hass, device = tv
        row = _odd_row(device)
        connection = _conn()
        await ws_tangle_apply(hass, connection, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "pronto": ODD_PRESS, "tested": True, "sends_fired": 0,
            "source": "capture",
        })
        connection.send_error.assert_not_called()
        assert device.get_command(row.target.command_id).code == ODD_PRESS
        again = _odd_row(device)
        assert again.id == row.id
        assert again.digest != row.digest
        assert again.classes == [CHECK_FRAME_SHAPE]
        assert is_unusual(again) is True


# --- keeping it -----------------------------------------------------------


async def _keep(hass, device, target, tested=True):
    connection = _conn()
    await ws_tangle_keep(hass, connection, {
        "id": 1, "type": "hair/device/tangle/keep",
        "device_id": device.id, "target": target, "tested": tested,
    })
    return connection


class TestItWorksKeepIt:
    @pytest.mark.asyncio
    async def test_the_row_leaves_the_list_and_the_mark_comes_off(self, tv):
        hass, device = tv
        row = _odd_row(device)
        command = device.get_command(row.target.command_id)
        rederive_comb_stamps(device, None, list(device.commands))
        assert command.comb_suspect is True
        assert command.comb_finding == CHECK_FRAME_SHAPE

        connection = await _keep(hass, device, row.id)

        connection.send_error.assert_not_called()
        record = connection.send_result.call_args.args[1]["record"]
        assert record["classes"] == [CHECK_FRAME_SHAPE]
        assert record["tested"] is True
        listing = list_tangles(device, None)
        assert listing.rows == []
        assert [a["id"] for a in listing.attested] == [row.id]
        assert command.comb_suspect is False
        assert command.comb_finding is None

    @pytest.mark.asyncio
    async def test_the_door_still_refuses_an_untested_keep(self, tv):
        hass, device = tv
        connection = await _keep(hass, device, _odd_row(device).id,
                                 tested=False)
        assert connection.send_error.call_args.args[1] == "not_tested"
        assert device.tangle_attestations == []

    @pytest.mark.asyncio
    async def test_changing_the_kept_bytes_brings_the_finding_back(self, tv):
        """Expiry is structural: the attestation names the bytes, and new
        bytes are not the ones anybody vouched for."""
        hass, device = tv
        row = _odd_row(device)
        await _keep(hass, device, row.id)
        assert list_tangles(device, None).rows == []

        device.get_command(row.target.command_id).code = ODD_PRESS

        back = list_tangles(device, None).rows
        assert [r.id for r in back] == [row.id]
        assert back[0].attested is None
        assert is_unusual(back[0]) is True


# --- the fit gate ---------------------------------------------------------


class TestBlockingRows:
    def test_only_the_rows_outside_unusual_count(self):
        unusual = _row([CHECK_FRAME_SHAPE])
        wrong = replace_id(_row([CHECK_MALFORMED]), "command:y")
        fixable = replace_id(_row([CHECK_STRAY_BURST], has_donor=True),
                             "command:z")
        listing = TangleListing(rows=[unusual, wrong, fixable])
        assert [r.id for r in blocking_rows(listing)] == [
            "command:y", "command:z"]

    def test_a_device_with_only_unusual_rows_blocks_nothing(self, tv):
        _hass, device = tv
        listing = list_tangles(device, None)
        assert listing.rows
        assert blocking_rows(listing) == []


async def _sign(hass, device):
    """A save that claims a fit (the gate's own trigger)."""
    connection = _conn()
    await ws_wigs_save(hass, connection, {
        "id": 9, "type": "hair/wigs/save", "device_id": device.id,
        "attest": {
            "github": "someone", "hair_version": "0.16.0",
            "ha_version": "2026.9.0",
            "claims": [{"digest": "d" * 16, "verdict": "worked"}],
        },
    })
    return connection


def _refusal(connection) -> str | None:
    if not connection.send_error.called:
        return None
    return connection.send_error.call_args.args[1]


class TestTheServerGate:
    """Matrix-only, as it always was; it now counts blocking rows."""

    @pytest.mark.asyncio
    async def test_unusual_rows_do_not_block_a_fit(self, fake_hass, tmp_path):
        device = _ac()
        hass = _wire(fake_hass, tmp_path, device, UNTRIMMABLE)
        assert list_tangles(device, UNTRIMMABLE).rows
        connection = await _sign(hass, device)
        assert _refusal(connection) != FIT_HAS_TANGLES

    @pytest.mark.asyncio
    async def test_any_other_open_row_still_blocks(self, fake_hass, tmp_path):
        """The trimmable stray burst is a Fixes ready row, so it holds
        the fit up exactly as it did before this card existed."""
        device = _ac()
        hass = _wire(fake_hass, tmp_path, device, TRIMMABLE)
        connection = await _sign(hass, device)
        assert _refusal(connection) == FIT_HAS_TANGLES
        assert "1 codes" in connection.send_error.call_args.args[2]
