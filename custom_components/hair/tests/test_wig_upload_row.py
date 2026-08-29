"""The drop path stops asking twice.

Issue 6 of the detangler round, backend half. Dropping a file on the
ghost tile sat silent long enough that the owner doubted it had
registered. The import itself is not the slow part: `wigs/upload`
parses, converts, combs, checks supersession and writes, and it knows
the landed wig completely by the time it returns. What followed was the
waste -- the drop path then ran a whole `wigs/list`, which re-scans and
re-parses EVERY wig in the closet and computes claims, receipts and
matrix summaries for each, to find the one row whose filename it had
known since the write.

So the upload result carries that row. `wigs/list` is untouched: this
is the drop path's shortcut, not a replacement for the closet's own
payload, and the two have to agree about the same file or the shortcut
is a second truth. That agreement is what this file pins hardest.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.websocket_api import ws_wigs_list, ws_wigs_upload
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    serialize_wig,
)

from .test_wig_comb import _code

#: Everything the picker row needs, and the fields the drop path used
#: to go back to the closet for.
ROW_FIELDS = (
    "filename", "name", "brand", "model", "kind", "signal_count",
    "matrix", "comb",
)


@pytest.fixture
def wigs_dir_path(tmp_path):
    directory = tmp_path / "hair" / "wigs"
    directory.mkdir(parents=True)
    return directory


def _connection():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = "dab"
    return conn


def _wire(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "fitting_manager": None,
        "store": None,
    }}


def _flat() -> Wig:
    return Wig(
        name="Practice Remote", brand="Testco", model="TM-1", kind="fan",
        signals=[
            WigSignal(alias=f"Button {i}", pronto=_code([11], seed=i))
            for i in range(4)
        ],
    )


def _matrix() -> Wig:
    cells = [
        ClimateCell(mode="cool", fan="auto", temp=float(temp),
                    pronto=_code([10], seed=temp))
        for temp in range(16, 22)
    ]
    return Wig(
        name="Practice AC", brand="Testco", model="AC-9", kind="ac",
        signals=[], climate=ClimateMatrix(
            min_temp=16.0, max_temp=30.0,
            off=_code([10], seed=90), cells=cells,
        ),
    )


async def _upload(fake_hass, text: str, **extra) -> dict:
    conn = _connection()
    payload = {"id": 1, "type": "hair/wigs/upload", "text": text}
    payload.update(extra)
    await ws_wigs_upload(fake_hass, conn, payload)
    return conn.send_result.call_args.args[1]


async def _closet_row(fake_hass, filename: str) -> dict:
    conn = _connection()
    await ws_wigs_list(fake_hass, conn, {"id": 2, "type": "hair/wigs/list"})
    rows = {
        row["filename"]: row
        for row in conn.send_result.call_args.args[1]["wigs"]
    }
    return rows[filename]


class TestTheLandedRowComesBack:
    @pytest.mark.asyncio
    async def test_a_native_wig_carries_every_row_field(
            self, fake_hass, tmp_path, wigs_dir_path):
        _wire(fake_hass, tmp_path)
        result = await _upload(fake_hass, serialize_wig(_flat()))
        assert result["success"]
        entry = result["files"][0]
        for field in ROW_FIELDS:
            assert field in entry, field
        assert entry["name"] == "Practice Remote"
        assert entry["brand"] == "Testco"
        assert entry["model"] == "TM-1"
        assert entry["kind"] == "fan"
        assert entry["signal_count"] == 4
        assert entry["matrix"] is None

    @pytest.mark.asyncio
    async def test_a_matrix_wig_carries_its_matrix_summary(
            self, fake_hass, tmp_path, wigs_dir_path):
        """The chip the picker draws for a lattice. Computing it here
        costs nothing: the wig is already parsed and in hand."""
        _wire(fake_hass, tmp_path)
        result = await _upload(fake_hass, serialize_wig(_matrix()))
        entry = result["files"][0]
        assert entry["signal_count"] == 0
        assert entry["matrix"] is not None
        assert entry["matrix"]["cells"] == 6
        assert entry["matrix"]["modes"] == ["cool"]
        assert entry["matrix"]["min_temp"] == 16.0

    @pytest.mark.asyncio
    async def test_it_says_what_the_closet_says(
            self, fake_hass, tmp_path, wigs_dir_path):
        """The point. A shortcut that disagrees with the surface it is
        short-cutting is a second truth, not a shortcut."""
        _wire(fake_hass, tmp_path)
        result = await _upload(fake_hass, serialize_wig(_matrix()))
        entry = result["files"][0]
        row = await _closet_row(fake_hass, result["filename"])
        for field in ROW_FIELDS:
            assert entry[field] == row[field], field

    @pytest.mark.asyncio
    async def test_the_comb_summary_still_rides(
            self, fake_hass, tmp_path, wigs_dir_path):
        """It was already there and stays there: import is the cheapest
        moment in a wig's life to look."""
        _wire(fake_hass, tmp_path)
        result = await _upload(fake_hass, serialize_wig(_flat()))
        assert result["files"][0]["comb"] is not None
        assert result["files"][0]["comb"]["suspects"] == 0


class TestConversionCarriesItToo:
    @pytest.mark.asyncio
    async def test_a_smartir_drop_lands_a_full_row(
            self, fake_hass, tmp_path, wigs_dir_path):
        """A converted file is exactly the case where the person is
        least sure anything happened."""
        _wire(fake_hass, tmp_path)
        source = {
            "manufacturer": "Testco",
            "supportedModels": ["TM-1"],
            "supportedController": "MQTT",
            "commandsEncoding": "Pronto",
            "commands": {
                "power": _code([11], seed=1),
                "volumeUp": _code([11], seed=2),
            },
        }
        result = await _upload(
            fake_hass, json.dumps(source), filename="1234.json")
        assert result["success"] and result["format"] == "smartir"
        entry = result["files"][0]
        for field in ROW_FIELDS:
            assert field in entry, field
        assert entry["signal_count"] == 2
        row = await _closet_row(fake_hass, result["filename"])
        for field in ROW_FIELDS:
            assert entry[field] == row[field], field


class TestNothingElseMoves:
    @pytest.mark.asyncio
    async def test_the_failure_shape_is_unchanged(
            self, fake_hass, tmp_path, wigs_dir_path):
        _wire(fake_hass, tmp_path)
        result = await _upload(fake_hass, "{\"not\": \"a wig\"}")
        assert result["success"] is False
        assert result["errors"]
        assert "files" not in result

    @pytest.mark.asyncio
    async def test_the_duplicate_receipt_is_unchanged(
            self, fake_hass, tmp_path, wigs_dir_path):
        """The row rides alongside what was already on the entry, not
        instead of it."""
        _wire(fake_hass, tmp_path)
        text = serialize_wig(_flat())
        await _upload(fake_hass, text)
        again = await _upload(fake_hass, text)
        entry = again["files"][0]
        assert entry["duplicate_of"] is not None
        assert entry["duplicates"]
        assert entry["signal_count"] == 4

    @pytest.mark.asyncio
    async def test_the_closet_payload_is_untouched(
            self, fake_hass, tmp_path, wigs_dir_path):
        """wigs/list keeps every field it had. The drop path got a
        shortcut; the closet did not lose anything."""
        _wire(fake_hass, tmp_path)
        await _upload(fake_hass, serialize_wig(_flat()))
        row = await _closet_row(
            fake_hass,
            (await _closet_row_names(fake_hass))[0],
        )
        for field in (
            "filename", "name", "brand", "model", "notes", "origin",
            "signal_count", "signals", "kind", "identifiers", "matrix",
            "fitting", "comb", "linked_devices",
        ):
            assert field in row, field


async def _closet_row_names(fake_hass) -> list[str]:
    conn = _connection()
    await ws_wigs_list(fake_hass, conn, {"id": 3, "type": "hair/wigs/list"})
    return [
        row["filename"]
        for row in conn.send_result.call_args.args[1]["wigs"]
    ]
