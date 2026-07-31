"""Combing wired into the closet: receipts, the list payload, on demand.

The contracts here are about WHEN a wig gets looked at and what survives
being looked at:

- Combing at import is safe to do automatically because the receipt rides
  in wig extra, outside every canonical hash. Stamping one can never move
  a wig's identity or invalidate somebody's fitting.
- No receipt is NOT clean. A wig nobody has combed serves ``comb: null``
  and the row draws plain grey, the same as a wig that came back empty;
  the tooltip is what separates them (owner ruling CG3).
- Red versus yellow follows the taxonomy, not the count: one duplicated
  neighbour outranks any number of malformed frames.
- The sequence-to-send_count fold is the one place import transforms
  rather than transcodes, so every fold is named in the response.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.websocket_api import (
    ws_wigs_comb,
    ws_wigs_list,
    ws_wigs_upload,
)
from custom_components.hair.wig_comb import (
    CHECK_DUPLICATED_NEIGHBOUR,
    COMB_KEY,
    comb_wig,
    receipt_summary,
    stamp_receipt,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    canonical_cells_json,
    canonical_signals_json,
    parse_wig,
    serialize_wig,
    wig_content_hash,
)

from .test_wig_comb import _code


@pytest.fixture
def wigs_dir_path(tmp_path):
    d = tmp_path / "hair" / "wigs"
    d.mkdir(parents=True)
    return d


def _make_connection(username="dab"):
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = username
    return conn


def _wire(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "fitting_manager": None,
        "store": None,
    }}


def _signal_wig(codes: dict[str, str]) -> Wig:
    return Wig(name="Remote", signals=[
        WigSignal(alias=a, pronto=p) for a, p in codes.items()
    ])


def _clean_wig() -> Wig:
    return _signal_wig({
        f"Button {i}": _code([11], seed=i) for i in range(6)
    })


def _defective_matrix() -> Wig:
    """A lattice with one duplicated neighbour: the dangerous class."""
    cells = [
        ClimateCell(mode="cool", fan="auto", temp=float(t),
                    pronto=_code([10], seed=t))
        for t in range(16, 22)
    ]
    cells[3].pronto = cells[2].pronto
    return Wig(name="AC", signals=[], climate=ClimateMatrix(
        min_temp=16.0, max_temp=30.0, off=_code([10], seed=90), cells=cells,
    ))


# ---------------------------------------------------------------------------
# The receipt cannot move a wig's identity
# ---------------------------------------------------------------------------


class TestReceiptIsInert:
    def test_stamping_leaves_the_hash_alone(self):
        """The reason combing can run automatically at import: recording
        what was found is not a change to what the wig IS."""
        plain = _defective_matrix()
        marked = _defective_matrix()
        before = wig_content_hash(plain)
        stamp_receipt(marked, comb_wig(marked), "2026-07-31")
        assert wig_content_hash(marked) == before
        assert canonical_cells_json(marked.climate) == \
            canonical_cells_json(plain.climate)

    def test_stamping_a_signal_wig_leaves_the_hash_alone(self):
        plain = _clean_wig()
        marked = _clean_wig()
        stamp_receipt(marked, comb_wig(marked), "2026-07-31")
        assert wig_content_hash(marked) == wig_content_hash(plain)
        assert canonical_signals_json(marked.signals) == \
            canonical_signals_json(plain.signals)

    def test_receipt_survives_serialize_and_parse(self):
        wig = _defective_matrix()
        stamp_receipt(wig, comb_wig(wig), "2026-07-31")
        back = parse_wig(serialize_wig(wig)).wig
        assert back.extra[COMB_KEY]["suspects"] == 1
        assert back.extra[COMB_KEY]["date"] == "2026-07-31"
        assert receipt_summary(back)["dangerous"] is True

    def test_no_receipt_reads_as_unknown_not_clean(self):
        assert receipt_summary(_clean_wig()) is None

    def test_combed_clean_is_a_receipt_with_zero_suspects(self):
        """Distinct from no receipt at all, which is the whole point of
        stamping one even when nothing is found."""
        wig = _clean_wig()
        stamp_receipt(wig, comb_wig(wig), "2026-07-31")
        summary = receipt_summary(wig)
        assert summary is not None
        assert summary["suspects"] == 0 and summary["dangerous"] is False

    def test_dangerous_flag_follows_the_taxonomy_not_the_count(self):
        wig = _defective_matrix()
        stamp_receipt(wig, comb_wig(wig), "2026-07-31")
        summary = receipt_summary(wig)
        assert summary["suspects"] == 1
        assert summary["dangerous"] is True
        assert summary["counts"][CHECK_DUPLICATED_NEIGHBOUR] == 1

    def test_a_junk_receipt_does_not_crash_the_row(self):
        wig = _clean_wig()
        wig.extra[COMB_KEY] = "not a dict"
        assert receipt_summary(wig) is None
        wig.extra[COMB_KEY] = {"suspects": "lots"}
        assert receipt_summary(wig)["suspects"] == 0


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


class TestCombAtImport:
    @pytest.mark.asyncio
    async def test_dropped_wig_is_combed_and_stamped(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        _wire(fake_hass, tmp_path)
        conn = _make_connection()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload",
            "text": serialize_wig(_defective_matrix()),
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["success"]
        assert payload["files"][0]["comb"]["suspects"] == 1
        assert payload["files"][0]["comb"]["dangerous"] is True

        written = parse_wig(
            (wigs_dir_path / payload["filename"]).read_text()
        ).wig
        assert written.extra[COMB_KEY]["suspects"] == 1

    @pytest.mark.asyncio
    async def test_a_clean_drop_still_gets_a_receipt(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        _wire(fake_hass, tmp_path)
        conn = _make_connection()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload",
            "text": serialize_wig(_clean_wig()),
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["files"][0]["comb"]["suspects"] == 0
        written = parse_wig(
            (wigs_dir_path / payload["filename"]).read_text()
        ).wig
        assert COMB_KEY in written.extra

    @pytest.mark.asyncio
    async def test_smartir_fold_is_named_in_the_response(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        """The one place import transforms rather than transcodes."""
        _wire(fake_hass, tmp_path)
        code = _code([11], seed=3)
        source = {
            "manufacturer": "Testco",
            "supportedModels": ["TM-1"],
            "supportedController": "MQTT",
            "commandsEncoding": "Pronto",
            "commands": {
                "power": code,
                "channel11": [code, code, code],
            },
        }
        conn = _make_connection()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload",
            "text": json.dumps(source), "filename": "1234.json",
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["success"] and payload["format"] == "smartir"
        assert len(payload["folds"]) == 1
        assert "send_count 3" in payload["folds"][0]
        assert payload["files"][0]["comb"] is not None


# ---------------------------------------------------------------------------
# The closet row and the on-demand comb
# ---------------------------------------------------------------------------


class TestClosetPayload:
    @pytest.mark.asyncio
    async def test_list_serves_the_receipt_or_null(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        _wire(fake_hass, tmp_path)
        (wigs_dir_path / "plain.wig.json").write_text(
            serialize_wig(_clean_wig()), encoding="utf-8"
        )
        combed = _defective_matrix()
        stamp_receipt(combed, comb_wig(combed), "2026-07-31")
        (wigs_dir_path / "combed.wig.json").write_text(
            serialize_wig(combed), encoding="utf-8"
        )
        conn = _make_connection()
        await ws_wigs_list(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/list",
        })
        rows = {
            w["filename"]: w
            for w in conn.send_result.call_args.args[1]["wigs"]
        }
        # Never combed: null, so the glyph stays plain grey.
        assert rows["plain.wig.json"]["comb"] is None
        assert rows["combed.wig.json"]["comb"]["suspects"] == 1
        assert rows["combed.wig.json"]["comb"]["dangerous"] is True

    @pytest.mark.asyncio
    async def test_comb_on_demand_writes_a_receipt(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        _wire(fake_hass, tmp_path)
        (wigs_dir_path / "ac.wig.json").write_text(
            serialize_wig(_defective_matrix()), encoding="utf-8"
        )
        conn = _make_connection()
        await ws_wigs_comb(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/comb", "filename": "ac.wig.json",
        })
        conn.send_error.assert_not_called()
        report = conn.send_result.call_args.args[1]
        assert report["suspects"] == 1
        assert report["matrix"] is True
        assert report["findings"][0]["check"] == CHECK_DUPLICATED_NEIGHBOUR
        written = parse_wig(
            (wigs_dir_path / "ac.wig.json").read_text()
        ).wig
        assert written.extra[COMB_KEY]["suspects"] == 1

    @pytest.mark.asyncio
    async def test_comb_on_demand_refreshes_a_stale_receipt(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        """A replace changes the codes, so the receipt written before it
        describes codes that no longer exist. This is how it catches up."""
        _wire(fake_hass, tmp_path)
        wig = _defective_matrix()
        stamp_receipt(wig, comb_wig(wig), "2026-07-30")
        # The defect is repaired: the colliding cell gets its own code.
        wig.climate.cells[3].pronto = _code([10], seed=200)
        (wigs_dir_path / "ac.wig.json").write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        conn = _make_connection()
        await ws_wigs_comb(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/comb", "filename": "ac.wig.json",
        })
        assert conn.send_result.call_args.args[1]["suspects"] == 0
        written = parse_wig(
            (wigs_dir_path / "ac.wig.json").read_text()
        ).wig
        assert written.extra[COMB_KEY]["suspects"] == 0
        assert written.extra[COMB_KEY]["date"] != "2026-07-30"

    @pytest.mark.asyncio
    async def test_comb_preserves_fittings_and_the_hash(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        """Combing must never cost somebody their proof."""
        _wire(fake_hass, tmp_path)
        wig = _defective_matrix()
        entry = {
            "handle": "dab", "date": "2026-07-30",
            "content_hash": wig_content_hash(wig),
            "confirmed": [], "failed": [],
        }
        wig.extra["fittings"] = [entry]
        before = wig_content_hash(wig)
        (wigs_dir_path / "ac.wig.json").write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        conn = _make_connection()
        await ws_wigs_comb(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/comb", "filename": "ac.wig.json",
        })
        written = parse_wig(
            (wigs_dir_path / "ac.wig.json").read_text()
        ).wig
        assert wig_content_hash(written) == before
        assert written.extra["fittings"] == [entry]

    @pytest.mark.asyncio
    async def test_comb_unknown_file(self, fake_hass, tmp_path,
                                     wigs_dir_path):
        _wire(fake_hass, tmp_path)
        conn = _make_connection()
        await ws_wigs_comb(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/comb", "filename": "nope.wig.json",
        })
        conn.send_result.assert_not_called()
        assert conn.send_error.call_args.args[1] == "not_found"
