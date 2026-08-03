"""The two SAVE TO CLOSET commands, end to end through the WS layer.

These are the seam tests: the plan and the save each work in isolation
(test_wig_save), so what is left to prove is that the wiring between
them and the closet on disk is honest -- the right file gets written,
the device remembers what it should, and the refusals refuse.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.websocket_api import ws_wigs_save, ws_wigs_save_plan
from custom_components.hair.wig_format import (
    VERDICT_WORKED,
    Wig,
    WigSignal,
    serialize_wig,
    signal_row_digest,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _command(name, pronto):
    return IRCommand(
        name=name, protocol="PRONTO", code=pronto, repeat_count=0
    )


def _wire(hass, tmp_path, device):
    hass.config.config_dir = str(tmp_path)
    ensure_wigs_dir(tmp_path)
    store = MagicMock()
    store.get_device = MagicMock(
        side_effect=lambda did: device if did == device.id else None
    )
    manager = MagicMock()
    manager.async_update_device = AsyncMock()
    hass.data[DOMAIN] = {
        "entry-1": {"store": store, "device_manager": manager}
    }
    return manager


def _closet_wig(tmp_path, wig):
    ensure_wigs_dir(tmp_path)
    text = serialize_wig(wig)
    path = wigs_dir(tmp_path) / "edifier.wig.json"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def _no_signing(monkeypatch):
    """Unsigned bundles. Signing is tested where signing lives; here it
    would only add a key-generation round trip to every case."""
    monkeypatch.setattr(
        "custom_components.hair.fitting_signing.async_get_private_key",
        AsyncMock(return_value=None),
    )


@pytest.mark.asyncio
async def test_plan_for_a_new_device_is_create(fake_hass, tmp_path):
    device = IRDevice(name="Fan", commands=[_command("On", PRONTO_A)])
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save_plan(
        fake_hass, conn,
        {"id": 1, "type": "hair/wigs/save_plan", "device_id": device.id},
    )
    result = conn.send_result.call_args[0][1]
    assert result["variant"] == "create"
    assert [r["alias"] for r in result["rows"]] == ["On"]


@pytest.mark.asyncio
async def test_plan_finds_the_source_wig_by_identity(fake_hass, tmp_path):
    """By id, never by filename. A closet file is free to be renamed,
    re-downloaded, or replaced by a shop copy; the id survives all
    three, and it is what the device actually remembers."""
    wig = Wig(
        name="Edifier", wig_id="u-source",
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )
    _closet_wig(tmp_path, wig)
    device = IRDevice(
        name="Speakers", commands=[_command("Power", PRONTO_A)],
        source_wig_id="u-source",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save_plan(
        fake_hass, conn,
        {"id": 1, "type": "hair/wigs/save_plan", "device_id": device.id},
    )
    result = conn.send_result.call_args[0][1]
    assert result["variant"] == "update"
    assert result["source_filename"] == "edifier.wig.json"
    assert result["rows"][0]["renamed"] is True
    assert result["rows"][0]["wig_alias"] == "On"


@pytest.mark.asyncio
async def test_plan_for_an_unknown_device_errors(fake_hass, tmp_path):
    device = IRDevice(name="Fan", commands=[_command("On", PRONTO_A)])
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save_plan(
        fake_hass, conn,
        {"id": 1, "type": "hair/wigs/save_plan", "device_id": "nope"},
    )
    assert conn.send_error.call_args[0][1] == "not_found"


@pytest.mark.asyncio
async def test_create_writes_the_file_and_the_device_remembers_it(
    fake_hass, tmp_path, _no_signing
):
    """After a CREATE the device carries the new wig's id.

    Without this the next SAVE TO CLOSET would offer to mint a second
    copy of a wig the closet already holds, and the person would end up
    curating two files that drift apart.
    """
    device = IRDevice(name="Fan", commands=[_command("On", PRONTO_A)])
    manager = _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Bench Fan", "brand": "Dreo",
        },
    )
    result = conn.send_result.call_args[0][1]
    assert result["variant"] == "create"
    written = json.loads(
        (wigs_dir(tmp_path) / result["filename"]).read_text()
    )
    assert written["name"] == "Bench Fan"
    assert written["brand"] == "Dreo"
    assert device.source_wig_id == result["wig_id"]
    manager.async_update_device.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_carries_the_attestation(
    fake_hass, tmp_path, _no_signing
):
    command = _command("On", PRONTO_A)
    device = IRDevice(name="Fan", commands=[command])
    _wire(fake_hass, tmp_path, device)
    from custom_components.hair.wig_export import build_wig_from_device

    digest = signal_row_digest(build_wig_from_device(device).wig.signals[0])
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Bench Fan",
            "attest": {
                "claims": [{"digest": digest, "verdict": VERDICT_WORKED}],
                "handle": "David",
            },
        },
    )
    result = conn.send_result.call_args[0][1]
    assert result["attested"] == 1
    written = json.loads(
        (wigs_dir(tmp_path) / result["filename"]).read_text()
    )
    assert written["fittings"][0]["handle"] == "David"


@pytest.mark.asyncio
async def test_update_appends_to_the_source_file(
    fake_hass, tmp_path, _no_signing
):
    wig = Wig(
        name="Edifier", wig_id="u-source",
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )
    path = _closet_wig(tmp_path, wig)
    before = path.read_text()
    device = IRDevice(
        name="Speakers", commands=[_command("On", PRONTO_A)],
        source_wig_id="u-source",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "update",
            "attest": {
                "claims": [{
                    "digest": signal_row_digest(wig.signals[0]),
                    "verdict": VERDICT_WORKED,
                }],
                "handle": "David",
            },
        },
    )
    result = conn.send_result.call_args[0][1]
    assert result["filename"] == "edifier.wig.json"
    after = json.loads(path.read_text())
    assert after["fittings"][0]["handle"] == "David"
    # Hard rule 3, at the file boundary: the signals are the bytes that
    # were already there.
    assert after["signals"] == json.loads(before)["signals"]


@pytest.mark.asyncio
async def test_a_metadata_only_update_is_allowed(
    fake_hass, tmp_path, _no_signing
):
    """Editing brand on a shop wig is a content PR, not an attestation.

    The plan rules that metadata edits ride the PR as reviewed changes,
    so gating them behind the oath would have made the prefilled fields
    read-only decoration. Hard rule 3 protects the SIGNALS block, and a
    brand correction touches none of it.
    """
    wig = Wig(
        name="Edifier", brand="Edifier", wig_id="u-source",
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )
    path = _closet_wig(tmp_path, wig)
    before = path.read_text()
    device = IRDevice(
        name="Speakers", commands=[_command("On", PRONTO_A)],
        source_wig_id="u-source",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "update", "brand": "Edifier International",
        },
    )
    conn.send_error.assert_not_called()
    after = json.loads(path.read_text())
    assert after["brand"] == "Edifier International"
    assert "fittings" not in after
    assert after["signals"] == json.loads(before)["signals"]


@pytest.mark.asyncio
async def test_unchanged_metadata_is_not_a_change(
    fake_hass, tmp_path, _no_signing
):
    """The dialog prefills every field from the wig and sends them all
    back. Treating present as changed would let an untouched dialog
    write a metadata PR that changes nothing -- which is precisely the
    shape an attestation must never be confused with."""
    wig = Wig(
        name="Edifier", brand="Edifier", wig_id="u-source",
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )
    _closet_wig(tmp_path, wig)
    device = IRDevice(
        name="Speakers", commands=[_command("On", PRONTO_A)],
        source_wig_id="u-source",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "update", "name": "Edifier", "brand": "Edifier",
        },
    )
    assert conn.send_error.call_args[0][1] == "nothing_to_update"


@pytest.mark.asyncio
async def test_update_with_nothing_to_attest_refuses(
    fake_hass, tmp_path, _no_signing
):
    """An UPDATE with no claims would rewrite the file with no change in
    it: a shop PR that says nothing."""
    wig = Wig(
        name="Edifier", wig_id="u-source",
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )
    _closet_wig(tmp_path, wig)
    device = IRDevice(
        name="Speakers", commands=[_command("On", PRONTO_A)],
        source_wig_id="u-source",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "update",
        },
    )
    assert conn.send_error.call_args[0][1] == "nothing_to_update"


@pytest.mark.asyncio
async def test_update_against_a_missing_source_says_so(
    fake_hass, tmp_path, _no_signing
):
    device = IRDevice(
        name="Speakers", commands=[_command("On", PRONTO_B)],
        source_wig_id="u-gone",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "update",
            "attest": {
                "claims": [{"digest": "d" * 16, "verdict": VERDICT_WORKED}],
            },
        },
    )
    assert conn.send_error.call_args[0][1] == "source_missing"


@pytest.mark.asyncio
async def test_a_device_with_no_usable_codes_refuses(
    fake_hass, tmp_path, _no_signing
):
    device = IRDevice(
        name="Empty", commands=[IRCommand(name="Broken")],
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    await ws_wigs_save(
        fake_hass, conn,
        {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Empty",
        },
    )
    assert conn.send_error.call_args[0][1] == "no_signals"
