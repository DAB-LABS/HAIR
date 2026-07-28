"""Cold Cuts (v0.8.8): matrix wigs through the fitting flow and adopt.

The contracts under test (owner rulings 2026-07-28):

- fitting_rows is the one session surface: aliases for signal wigs
  (v1 behavior unchanged), the dimension checklist for matrix wigs --
  and a matrix wig's flat extras are deliberately NOT rows.
- Marks store ROW KEYS (checklist cell keys, "on"/"off"), the hash
  binds to the cells hash via wig_content_hash, completeness means the
  checklist is covered.
- ws_fitting_state serves sectioned rows for the CC1 dialog layout;
  signal wigs keep their existing payload shape.
- make-device forces AC for matrix wigs, writes the matrix file before
  the device lands, copies flat extras as commands, and reports the
  cell count. Duplicate copies the matrix file to the clone's id.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.matrix_store import load_matrix, matrices_dir
from custom_components.hair.models import IRDevice
from custom_components.hair.websocket_api import (
    ws_duplicate_device,
    ws_fitting_state,
    ws_wig_make_device,
)
from custom_components.hair.wig_fitting import (
    FITTINGS_KEY,
    FittingManager,
    fitting_is_complete,
    fitting_is_valid,
    fitting_rows,
    fitting_summary,
    parse_fittings,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    parse_wig,
    serialize_wig,
    wig_content_hash,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0040 0020 0040 0020"
PRONTO_C = "0000 006D 0002 0000 0030 0030 0030 0060"

# The checklist this fixture matrix derives (deterministic; see
# wig_climate.dimension_checklist).
CHECKLIST_KEYS = [
    "on", "cool/auto/22", "dry/auto", "heat/auto/22", "cool/low/22",
    "cool/auto/16", "cool/auto/30", "off",
]


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "dry", "heat"],
        fan_modes=["auto", "low"],
        swing_modes=[],
        off=PRONTO_A,
        on=PRONTO_B,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=16.0, pronto=PRONTO_A),
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=PRONTO_B),
            ClimateCell(mode="cool", fan="auto", temp=30.0, pronto=PRONTO_A),
            ClimateCell(mode="cool", fan="low", temp=22.0, pronto=PRONTO_B),
            ClimateCell(mode="dry", fan="auto", pronto=PRONTO_A),
            ClimateCell(mode="heat", fan="auto", temp=22.0, pronto=PRONTO_B,
                        send_count=2),
        ],
    )


def _matrix_wig() -> Wig:
    """A matrix wig with one flat depth-0 extra riding along."""
    return Wig(
        name="Bedroom AC",
        kind="ac",
        signals=[WigSignal(alias="Sleep", pronto=PRONTO_C)],
        climate=_matrix(),
    )


def _signal_wig() -> Wig:
    return Wig(name="TV", signals=[
        WigSignal(alias="Power On", pronto=PRONTO_A),
        WigSignal(alias="Power Off", pronto=PRONTO_B),
    ])


@pytest.fixture
def wigs_dir_path(tmp_path):
    d = tmp_path / "hair" / "wigs"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def manager(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    return FittingManager(fake_hass, monitor=None)


def _write_wig(wigs_dir_path, wig, filename="bedroom-ac.wig.json"):
    (wigs_dir_path / filename).write_text(
        serialize_wig(wig), encoding="utf-8"
    )
    return filename


def _read_wig(wigs_dir_path, filename="bedroom-ac.wig.json"):
    result = parse_wig(
        (wigs_dir_path / filename).read_text(encoding="utf-8")
    )
    assert result.ok, result.errors
    return result.wig


# ---------------------------------------------------------------------------
# The rows abstraction
# ---------------------------------------------------------------------------


class TestFittingRows:
    def test_signal_wig_rows_are_aliases(self):
        rows = fitting_rows(_signal_wig())
        assert rows == [
            ("Power On", PRONTO_A, 1),
            ("Power Off", PRONTO_B, 1),
        ]

    def test_matrix_wig_rows_are_the_checklist(self):
        rows = fitting_rows(_matrix_wig())
        assert [key for key, _, _ in rows] == CHECKLIST_KEYS
        # send_count rides from the cell.
        heat = next(r for r in rows if r[0] == "heat/auto/22")
        assert heat[2] == 2

    def test_flat_extras_are_not_rows(self):
        assert all(key != "Sleep" for key, _, _ in
                   fitting_rows(_matrix_wig()))


class TestMatrixHashBinding:
    def _fitting(self, wig, **overrides):
        entry = {
            "handle": "tester",
            "date": "2026-07-28",
            "content_hash": wig_content_hash(wig),
            "confirmed": list(CHECKLIST_KEYS),
            "failed": [],
        }
        entry.update(overrides)
        return entry

    def test_valid_and_complete_on_checklist_coverage(self):
        wig = _matrix_wig()
        wig.extra[FITTINGS_KEY] = [self._fitting(wig)]
        f = parse_fittings(wig).fittings[0]
        assert fitting_is_valid(f, wig)
        assert fitting_is_complete(f, wig)

    def test_cell_change_invalidates(self):
        wig = _matrix_wig()
        wig.extra[FITTINGS_KEY] = [self._fitting(wig)]
        f = parse_fittings(wig).fittings[0]
        wig.climate.cells[0].temp = 17.0
        assert not fitting_is_valid(f, wig)

    def test_flat_extra_change_does_not_invalidate(self):
        """The matrix hash deliberately excludes the flat extras: the
        dimension check attests the MATRIX."""
        wig = _matrix_wig()
        wig.extra[FITTINGS_KEY] = [self._fitting(wig)]
        f = parse_fittings(wig).fittings[0]
        wig.signals[0].alias = "Renamed"
        assert fitting_is_valid(f, wig)

    def test_partial_checklist_not_complete(self):
        wig = _matrix_wig()
        wig.extra[FITTINGS_KEY] = [
            self._fitting(wig, confirmed=CHECKLIST_KEYS[:-1])
        ]
        f = parse_fittings(wig).fittings[0]
        assert not fitting_is_complete(f, wig)

    def test_summary_totals_are_checklist_sized(self):
        wig = _matrix_wig()
        wig.extra[FITTINGS_KEY] = [
            self._fitting(wig, confirmed=["on", "off"], handle="me")
        ]
        s = fitting_summary(wig, "me")
        assert s["total"] == len(CHECKLIST_KEYS)
        assert s["confirmed"] == 2

    def test_matrix_survives_share_strip(self):
        """shared_wig_text rebuilds the Wig; the climate block must
        ride along (the identifiers field-drop bug, not repeated)."""
        from custom_components.hair.wig_fitting import shared_wig_text

        wig = _matrix_wig()
        wig.extra[FITTINGS_KEY] = [self._fitting(wig, draft=True)]
        shared = json.loads(shared_wig_text(wig))
        assert FITTINGS_KEY not in shared
        assert len(shared["climate"]["cells"]) == 6


# ---------------------------------------------------------------------------
# The manager: matrix sessions
# ---------------------------------------------------------------------------


class TestMatrixMarks:
    @pytest.mark.asyncio
    async def test_marks_store_cell_keys(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        result = await manager.async_mark(filename, 1, "worked", "dab")
        assert result["success"]
        assert result["total"] == len(CHECKLIST_KEYS)
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        draft = parse_fittings(wig).fittings[0]
        assert draft.confirmed == ["cool/auto/22"]
        assert draft.content_hash == wig_content_hash(wig)

    @pytest.mark.asyncio
    async def test_full_checklist_is_perfect(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        for index in range(len(CHECKLIST_KEYS)):
            result = await manager.async_mark(
                filename, index, "worked", "dab"
            )
        assert result["perfect_ready"]
        finish = await manager.async_finish(
            filename, "dab", None, None, None
        )
        assert finish["state"] == "perfect"
        assert finish["total"] == len(CHECKLIST_KEYS)
        wig = _read_wig(wigs_dir_path)
        f = parse_fittings(wig).fittings[0]
        assert fitting_is_complete(f, wig)

    @pytest.mark.asyncio
    async def test_bad_index_measures_rows_not_signals(
        self, manager, wigs_dir_path
    ):
        """The wig has ONE flat signal but eight rows: index 7 is
        valid, index 8 is not."""
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        ok = await manager.async_mark(filename, 7, "worked", "dab")
        assert ok["success"]
        bad = await manager.async_mark(filename, 8, "worked", "dab")
        assert not bad["success"] and bad["code"] == "bad_index"

    @pytest.mark.asyncio
    async def test_finish_never_overwrites_the_imported_kind(
        self, manager, wigs_dir_path
    ):
        """Matrix wigs import with kind "ac", so the signing screen's
        kind prompt condition (kind missing) never fires; even a stray
        kind in the finish call must not overwrite the fact."""
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None,
                                   kind="tv")
        assert _read_wig(wigs_dir_path).kind == "ac"


class _FakeMonitor:
    def __init__(self):
        self.calls = []

    def record_send(self, command, source_label, emitter_entity_ids,
                    decoded_fingerprint=None, heard_future=None):
        self.calls.append(source_label)
        if heard_future is not None:
            heard_future.set_result("infrared.rx")


@pytest.fixture
def _fast_heard_wait(monkeypatch):
    from custom_components.hair import wig_fitting

    monkeypatch.setattr(wig_fitting, "FITTING_HEARD_WAIT_S", 0.01)


class TestMatrixSend:
    @pytest.mark.asyncio
    async def test_send_addresses_checklist_rows(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: object()
        monitor = _FakeMonitor()
        manager = FittingManager(fake_hass, monitor)
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        result = await manager.async_send(filename, 0, "infrared.e")
        assert result["success"] and result["heard"]
        assert monitor.calls == ["Fitting send: on"]
        # The heard evidence carries the ROW KEY into the draft.
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_flush()
        draft = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert draft.raw.get("heard") == ["on"]

    @pytest.mark.asyncio
    async def test_send_bad_index_measures_rows(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: object()
        manager = FittingManager(fake_hass, _FakeMonitor())
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        result = await manager.async_send(filename, 8, "infrared.e")
        assert not result["success"] and result["code"] == "bad_index"


# ---------------------------------------------------------------------------
# ws_fitting_state: the sectioned rows payload
# ---------------------------------------------------------------------------


def _make_connection(username="dab"):
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = username
    return conn


def _wire_fitting(fake_hass, manager):
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "fitting_manager": manager,
    }}


class TestFittingStateRows:
    @pytest.mark.asyncio
    async def test_matrix_rows_carry_checklist_facts(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_mark(filename, 2, "failed", "dab")
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        conn.send_error.assert_not_called()
        payload = conn.send_result.call_args.args[1]
        assert payload["matrix"] is True
        assert payload["signals"] == CHECKLIST_KEYS
        rows = payload["rows"]
        assert [r["key"] for r in rows] == CHECKLIST_KEYS
        cool = next(r for r in rows if r["key"] == "cool/auto/22")
        assert cool["section"] == "modes"
        assert cool["mode"] == "cool" and cool["fan"] == "auto"
        assert cool["temp"] == 22.0 and cool["temp_less"] is False
        assert cool["confirmed"] is True and cool["failed"] is False
        dry = next(r for r in rows if r["key"] == "dry/auto")
        assert dry["temp_less"] is True and dry["failed"] is True
        temp_min = next(r for r in rows if r["key"] == "cool/auto/16")
        assert temp_min["temp_role"] == "min"
        assert rows[0]["section"] == "start"
        assert rows[-1]["section"] == "wrap"

    @pytest.mark.asyncio
    async def test_signal_wig_shape_unchanged(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(
            wigs_dir_path, _signal_wig(), "tv.wig.json"
        )
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["matrix"] is False
        # The pre-0.8.8 contract, byte-identical.
        assert payload["signals"] == ["Power On", "Power Off"]
        assert [(r["key"], r["section"]) for r in payload["rows"]] == [
            ("Power On", None), ("Power Off", None),
        ]


# ---------------------------------------------------------------------------
# Adopt (make-device) and duplicate
# ---------------------------------------------------------------------------


def _adopt_manager():
    manager = MagicMock()
    manager.async_create_device = AsyncMock()
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    # _device_full loads the matrix summary through the manager since
    # the device page grew its state-matrix card (owner ruling
    # 2026-07-28); a bare MagicMock is not awaitable, so the stub
    # answers like a manager whose cache and file both miss.
    manager.async_get_matrix = AsyncMock(return_value=None)
    return manager


def _wire_adopt(fake_hass, manager):
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager,
        "fitting_manager": None,
    }}


class TestMakeDeviceMatrix:
    @pytest.mark.asyncio
    async def test_matrix_wig_adopts_as_ac_with_matrix_file(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        manager = _adopt_manager()
        _wire_adopt(fake_hass, manager)
        conn = _make_connection()
        await ws_wig_make_device(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/make-device",
            "filename": filename, "name": "Bedroom AC",
            "device_type": "ac", "emitter_entity_ids": ["infrared.e"],
        })
        conn.send_error.assert_not_called()
        result = conn.send_result.call_args.args[1]
        assert result["climate_matrix"] is True
        assert result["device_type"] == "ac"
        assert result["matrix_cells"] == 6
        # The flat extra copied as an ordinary command; cells did not.
        assert result["copied"] == 1
        assert [c["name"] for c in result["commands"]] == ["Sleep"]
        # The matrix file landed under the new device id, readable.
        matrix = load_matrix(tmp_path, result["id"])
        assert matrix is not None and len(matrix.cells) == 6
        manager.async_create_device.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_ac_type_refused(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        filename = _write_wig(wigs_dir_path, _matrix_wig())
        manager = _adopt_manager()
        _wire_adopt(fake_hass, manager)
        conn = _make_connection()
        await ws_wig_make_device(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/make-device",
            "filename": filename, "name": "Bedroom AC",
            "device_type": "media_player",
            "emitter_entity_ids": ["infrared.e"],
        })
        conn.send_result.assert_not_called()
        assert conn.send_error.call_args.args[1] == "invalid_format"
        assert "AC devices" in conn.send_error.call_args.args[2]
        # Nothing half-created: no device, no matrix folder content.
        manager.async_create_device.assert_not_awaited()
        assert not any(matrices_dir(tmp_path).glob("*")) \
            if matrices_dir(tmp_path).is_dir() else True

    @pytest.mark.asyncio
    async def test_signal_wig_adopt_unchanged(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        filename = _write_wig(
            wigs_dir_path, _signal_wig(), "tv.wig.json"
        )
        manager = _adopt_manager()
        _wire_adopt(fake_hass, manager)
        conn = _make_connection()
        await ws_wig_make_device(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/make-device",
            "filename": filename, "name": "TV",
            "device_type": "media_player",
            "emitter_entity_ids": ["infrared.e"],
        })
        result = conn.send_result.call_args.args[1]
        assert result["climate_matrix"] is False
        assert result["matrix_cells"] == 0
        assert result["copied"] == 2


class TestDuplicateMatrixDevice:
    def _source(self) -> IRDevice:
        return IRDevice(
            id="src-1", name="Bedroom AC", climate_matrix=True,
        )

    @pytest.mark.asyncio
    async def test_duplicate_copies_matrix_file(self, fake_hass, tmp_path):
        from custom_components.hair.matrix_store import write_matrix

        fake_hass.config.config_dir = str(tmp_path)
        write_matrix(tmp_path, "src-1", _matrix())
        manager = _adopt_manager()
        manager.get_device = MagicMock(return_value=self._source())
        _wire_adopt(fake_hass, manager)
        conn = _make_connection()
        await ws_duplicate_device(fake_hass, conn, {
            "id": 1, "type": "hair/device/duplicate",
            "device_id": "src-1", "new_name": "Office AC",
        })
        result = conn.send_result.call_args.args[1]
        assert result["climate_matrix"] is True
        assert load_matrix(tmp_path, result["id"]) is not None

    @pytest.mark.asyncio
    async def test_failed_copy_clears_the_flag(self, fake_hass, tmp_path):
        """No matrix file to copy: the clone must not claim one."""
        fake_hass.config.config_dir = str(tmp_path)
        manager = _adopt_manager()
        manager.get_device = MagicMock(return_value=self._source())
        _wire_adopt(fake_hass, manager)
        conn = _make_connection()
        await ws_duplicate_device(fake_hass, conn, {
            "id": 1, "type": "hair/device/duplicate",
            "device_id": "src-1", "new_name": "Office AC",
        })
        result = conn.send_result.call_args.args[1]
        assert result["climate_matrix"] is False
