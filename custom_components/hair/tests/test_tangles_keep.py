"""The other outcome: looked at it, it works, keep it.

A finding is a doubt about bytes. A person with the hardware in front of
them can answer that doubt, and this records the answer -- which is a
different act from repairing, and produces a different kind of record.

Nothing is deleted. The finding stands in the receipt, the wig carries
both the math and the human's answer, and the shop's own re-derive sees
both. What changes is that the row leaves the work list, and combing
stays quiet about it for exactly as long as the bytes and the map hold
still.

Expiry is structural, which is the part worth pinning. There is no
scheduler, no sweep and no stored "still valid" flag that could be
wrong: an attestation names the bytes and the map version it answered,
and if either moves the name stops matching and the finding is simply
open again.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRDevice
from custom_components.hair.tangles import (
    ATTESTED_KEY,
    KEEP_NO_FINDING,
    KEEP_NOT_TESTED,
    list_tangles,
)
from custom_components.hair.websocket_api import ws_tangle_keep
from custom_components.hair.wig_comb import CHECK_FIELD_MISMATCH, COMB_KEY
from custom_components.hair.wig_export import build_wig_from_device
from custom_components.hair.wig_format import Wig, cell_key, parse_wig
from custom_components.hair.wig_save import recomb

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

TARGET_KEY = "heat_cool/medium/off/25"
TARGET = f"cell:{TARGET_KEY}"


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


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _keep(hass, device, target=TARGET, tested=True, **extra):
    connection = _conn()
    payload = {"id": 1, "type": "hair/device/tangle/keep",
               "device_id": device.id, "target": target, "tested": tested}
    payload.update(extra)
    await ws_tangle_keep(hass, connection, payload)
    return connection


class TestRecordingTheAnswer:
    @pytest.mark.asyncio
    async def test_the_record_says_what_it_answers(self, wired):
        hass, device, _wig = wired
        connection = await _keep(hass, device, note="works on my unit")
        connection.send_error.assert_not_called()
        record = connection.send_result.call_args.args[1]["record"]
        assert record["target"] == TARGET_KEY
        assert record["classes"] == [CHECK_FIELD_MISMATCH]
        assert record["tested"] is True
        assert record["map"]["id"] == "ZHLT01"
        assert record["map"]["version"]
        assert record["note"] == "works on my unit"

    @pytest.mark.asyncio
    async def test_it_lives_with_the_device(self, wired):
        """A statement about THIS installation's hardware, not about the
        file, so it is device-side and travels with the device."""
        hass, device, _wig = wired
        await _keep(hass, device)
        assert len(device.tangle_attestations) == 1
        assert device.tangle_attestations[0]["target"] == TARGET_KEY

    @pytest.mark.asyncio
    async def test_keeping_twice_leaves_one_record(self, wired):
        hass, device, _wig = wired
        await _keep(hass, device)
        await _keep(hass, device)
        assert len(device.tangle_attestations) == 1

    @pytest.mark.asyncio
    async def test_the_row_leaves_the_work_list(self, wired):
        hass, device, wig = wired
        before = len(list_tangles(device, wig.climate).rows)
        await _keep(hass, device)
        listing = list_tangles(device, wig.climate)
        assert len(listing.rows) == before - 1
        assert TARGET_KEY not in {r.target.key for r in listing.rows}

    @pytest.mark.asyncio
    async def test_but_stays_on_the_record(self, wired):
        """Attested is not clean and must never render as clean."""
        hass, device, wig = wired
        await _keep(hass, device)
        listing = list_tangles(device, wig.climate)
        assert len(listing.attested) == 1
        answered = listing.attested[0]
        assert answered["target"]["key"] == TARGET_KEY
        assert answered["classes"] == [CHECK_FIELD_MISMATCH]
        assert answered["attested"]["tested"] is True

    @pytest.mark.asyncio
    async def test_the_card_shrinks_by_one(self, wired):
        hass, device, wig = wired
        before = next(c for c in list_tangles(device, wig.climate).clusters
                      if c.mechanic == "donor").size
        await _keep(hass, device)
        after = next(c for c in list_tangles(device, wig.climate).clusters
                     if c.mechanic == "donor").size
        assert after == before - 1


class TestWhatItRefuses:
    @pytest.mark.asyncio
    async def test_without_a_press_there_is_nothing_to_vouch_for(self, wired):
        hass, device, _wig = wired
        connection = await _keep(hass, device, tested=False)
        assert connection.send_error.call_args.args[1] == KEEP_NOT_TESTED
        assert device.tangle_attestations == []

    @pytest.mark.asyncio
    async def test_a_healthy_cell_has_nothing_to_answer(self, wired):
        hass, device, _wig = wired
        connection = await _keep(hass, device, target="cell:cool/high/off/22")
        assert connection.send_error.call_args.args[1] == KEEP_NO_FINDING
        assert device.tangle_attestations == []


class TestExpiryIsStructural:
    @pytest.mark.asyncio
    async def test_changed_bytes_open_the_finding_again(self, wired):
        """Nothing swept it away. The attestation names the bytes it
        answered, and these are not those bytes."""
        hass, device, wig = wired
        await _keep(hass, device)
        cells = {cell_key(c): c for c in wig.climate.cells}
        assert TARGET_KEY not in {
            r.target.key for r in list_tangles(device, wig.climate).rows}

        cells[TARGET_KEY].pronto = cells["heat_cool/medium/off/28"].pronto
        listing = list_tangles(device, wig.climate)
        assert TARGET_KEY in {r.target.key for r in listing.rows}
        assert listing.attested == []
        assert len(device.tangle_attestations) == 1

    @pytest.mark.asyncio
    async def test_a_changed_map_opens_the_finding_again(self, wired):
        """The map is half of what an attestation answers. A person
        vouched for these bytes against what the map said THEN, and a
        map that has learned something since is asking a new question.
        """
        hass, device, wig = wired
        await _keep(hass, device)
        record = device.tangle_attestations[0]
        target, digest, _version = record["key"].split("|")
        record["key"] = f"{target}|{digest}|somethingelse"

        listing = list_tangles(device, wig.climate)
        assert TARGET_KEY in {r.target.key for r in listing.rows}
        assert listing.attested == []


class TestItRidesOutWithTheWig:
    @pytest.mark.asyncio
    async def test_the_receipt_carries_both(self, wired):
        """The file leaves with the math AND the human's answer, so the
        shop's own re-derive sees both."""
        hass, device, wig = wired
        await _keep(hass, device, note="my unit is fine at 25")

        build = build_wig_from_device(device, wig.climate)
        assert build.wig is not None
        recomb(build.wig)
        receipt = build.wig.extra[COMB_KEY]
        assert receipt["suspects"] == 52
        carried = receipt[ATTESTED_KEY]
        assert len(carried) == 1
        assert carried[0]["target"] == TARGET_KEY
        assert carried[0]["note"] == "my unit is fine at 25"

    @pytest.mark.asyncio
    async def test_the_finding_is_still_in_the_receipt(self, wired):
        """Keep never deletes a finding. The cell is still doubted by
        the math; a person has simply answered the doubt."""
        hass, device, wig = wired
        await _keep(hass, device)
        build = build_wig_from_device(device, wig.climate)
        recomb(build.wig)
        keys = {
            key for finding in build.wig.extra[COMB_KEY]["findings"]
            for key in finding["keys"]
        }
        assert TARGET_KEY in keys

    def test_a_device_with_no_answers_carries_no_block(self, wired):
        """No empty block on a file nobody vouched for anything in."""
        _hass, device, wig = wired
        build = build_wig_from_device(device, wig.climate)
        recomb(build.wig)
        assert ATTESTED_KEY not in build.wig.extra[COMB_KEY]

    @pytest.mark.asyncio
    async def test_nothing_temporary_is_left_on_the_wig(self, wired):
        """The block is parked on the way out and folded into the
        receipt; the parking spot does not survive into the file."""
        hass, device, wig = wired
        await _keep(hass, device)
        build = build_wig_from_device(device, wig.climate)
        recomb(build.wig)
        assert "comb_attested_pending" not in build.wig.extra
