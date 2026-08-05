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
from custom_components.hair.websocket_api import (
    ws_wigs_save,
    ws_wigs_save_plan,
    ws_wigs_supersede,
    ws_wigs_upload,
)
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
PRONTO_C = "0000 006D 0002 0000 0040 0040 0020 0040"


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
    store.get_all_devices = MagicMock(return_value=[device])
    manager = MagicMock()
    manager.async_update_device = AsyncMock()
    hass.data[DOMAIN] = {
        "entry-1": {"store": store, "device_manager": manager}
    }
    return manager


def _wire_many(hass, tmp_path, devices):
    """Wiring for the supersession flow: many devices, by-id lookup, and
    a real _auto_map_command no-op so the top-up loop runs."""
    hass.config.config_dir = str(tmp_path)
    ensure_wigs_dir(tmp_path)
    by_id = {d.id: d for d in devices}
    store = MagicMock()
    store.get_device = MagicMock(side_effect=lambda did: by_id.get(did))
    store.get_all_devices = MagicMock(return_value=list(devices))
    manager = MagicMock()
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    hass.data[DOMAIN] = {
        "entry-1": {"store": store, "device_manager": manager}
    }
    return manager


def _closet_wig(tmp_path, wig, filename="edifier.wig.json"):
    ensure_wigs_dir(tmp_path)
    text = serialize_wig(wig)
    path = wigs_dir(tmp_path) / filename
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


class TestSaveAsNewStampsLineage:
    """Save as new (v0.9.7 Second Fitting): the successor carries its
    ancestry automatically.

    A sourced device saved with mode=create mints a successor. Its
    ``supersedes`` is stamped from the DEVICE's source id then the source
    file's own ancestry -- the whole authoring story, with the person
    never thinking about lineage. From-scratch saves stamp nothing.
    """

    @pytest.mark.asyncio
    async def test_sourced_save_extends_the_ancestry_in_order(
        self, fake_hass, tmp_path, _no_signing
    ):
        # Second Fitting amendment v2: the verb is derived, not sent.
        # Matching content stays UPDATE and never mints a successor, so
        # this fixture needs genuine divergence -- a command the source
        # wig does not have -- to actually reach the stamping path
        # (_do_create) the way a real outgrown-wig save would. Source
        # file already two generations deep: its own ancestry is [A, B].
        # The successor prepends the source id -> [source, A, B].
        wig = Wig(
            name="Fan XYZ", wig_id="u-source",
            supersedes=["A", "B"],
            signals=[WigSignal(alias="On", pronto=PRONTO_A)],
        )
        _closet_wig(tmp_path, wig)
        device = IRDevice(
            name="Fan", commands=[
                _command("On", PRONTO_A), _command("Turbo", PRONTO_C),
            ],
            source_wig_id="u-source",
        )
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "name": "Fan XYZ v2",
        })
        conn.send_error.assert_not_called()
        result = conn.send_result.call_args[0][1]
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert written["supersedes"] == ["u-source", "A", "B"]
        # The addition rode along too -- this is a successor, not a
        # from-scratch mint that happens to share a name.
        assert {s["alias"] for s in written["signals"]} == {"On", "Turbo"}

    @pytest.mark.asyncio
    async def test_unresolvable_source_stamps_the_single_link(
        self, fake_hass, tmp_path, _no_signing
    ):
        # The device points at a source no longer on the shelf. The one
        # link still known to be true is the source id itself.
        device = IRDevice(
            name="Fan", commands=[_command("On", PRONTO_A)],
            source_wig_id="u-gone",
        )
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Orphan",
        })
        result = conn.send_result.call_args[0][1]
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert written["supersedes"] == ["u-gone"]

    @pytest.mark.asyncio
    async def test_from_scratch_stamps_nothing(
        self, fake_hass, tmp_path, _no_signing
    ):
        device = IRDevice(name="Fan", commands=[_command("On", PRONTO_A)])
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Bench Fan",
        })
        result = conn.send_result.call_args[0][1]
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert "supersedes" not in written

    @pytest.mark.asyncio
    async def test_head_is_the_devices_source_not_the_closet_current_id(
        self, fake_hass, tmp_path, _no_signing
    ):
        # The closet copy of the source lineage was itself replaced: the
        # file now on the shelf is a successor with a DIFFERENT id that
        # supersedes the device's source. find_wig_by_id(source) finds
        # nothing, so the stamp is the device's source id alone -- never
        # the successor's id, which the device never pointed at.
        successor = Wig(
            name="Fan XYZ v2", wig_id="u-successor",
            supersedes=["u-source"],
            signals=[WigSignal(alias="On", pronto=PRONTO_A)],
        )
        _closet_wig(tmp_path, successor)
        device = IRDevice(
            name="Fan", commands=[_command("On", PRONTO_A)],
            source_wig_id="u-source",
        )
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Fan XYZ v3",
        })
        result = conn.send_result.call_args[0][1]
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert written["supersedes"] == ["u-source"]
        assert "u-successor" not in written["supersedes"]


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
async def test_update_against_a_missing_source_degrades_to_create(
    fake_hass, tmp_path, _no_signing
):
    """Second Fitting amendment v2: the verb is derived, not taken from
    the caller. A source id that no longer resolves on the shelf means
    build_save_plan sees no source at all, so the derived verb is
    CREATE -- the same graceful degrade as an unsourced device (Section
    2: refusing would strand a working device with no way to save).
    The one link still known to be true, the source id itself, still
    gets stamped -- exactly as test_unresolvable_source_stamps_the_single_link
    already covers for the explicit-create path."""
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
            "attest": {
                "claims": [{"digest": "d" * 16, "verdict": VERDICT_WORKED}],
            },
        },
    )
    result = conn.send_result.call_args[0][1]
    written = json.loads(
        (wigs_dir(tmp_path) / result["filename"]).read_text()
    )
    assert written["supersedes"] == ["u-gone"]


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


def _matrix(pronto_a=PRONTO_A, pronto_b=PRONTO_B):
    from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, off=pronto_a,
        modes=["cool"], fan_modes=["auto"],
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=24.0, pronto=pronto_a),
            ClimateCell(mode="cool", fan="auto", temp=25.0, pronto=pronto_b),
        ],
    )


def _wire_matrix(fake_hass, tmp_path, device, device_matrix):
    manager = _wire(fake_hass, tmp_path, device)
    manager.async_get_matrix = AsyncMock(return_value=device_matrix)
    return manager


def _matrix_wig(matrix):
    return Wig(name="AC", wig_id="u-source", signals=[], climate=matrix)


@pytest.mark.asyncio
async def test_a_diverged_lattice_blocks_matrix_attestation(
    fake_hass, tmp_path, _no_signing
):
    """A checklist bundle binds cells_hash, a SET. Signing while the
    device's lattice has moved would bind bytes the fitter never
    tested, so it refuses and names the three ways out."""
    wig = _matrix_wig(_matrix())
    _closet_wig(tmp_path, wig)
    repaired = _matrix()
    repaired.cells[0].pronto = "0000 006D 0002 0000 0050 0040 0020 0040"
    device = IRDevice(
        name="AC", commands=[], source_wig_id="u-source",
        climate_matrix=True,
    )
    _wire_matrix(fake_hass, tmp_path, device, repaired)
    conn = _conn()
    await ws_wigs_save(fake_hass, conn, {
        "id": 1, "type": "hair/wigs/save", "device_id": device.id,
        "mode": "update",
        "attest": {"claims": [{"digest": "d" * 16,
                               "verdict": VERDICT_WORKED}]},
    })
    assert conn.send_error.call_args[0][1] == "lattice_diverged"
    assert "Propose" in conn.send_error.call_args[0][2]


@pytest.mark.asyncio
async def test_propose_then_attest_succeeds_and_binds_the_new_lattice(
    fake_hass, tmp_path, _no_signing
):
    from custom_components.hair.wig_format import cells_content_hash

    wig = _matrix_wig(_matrix())
    path = _closet_wig(tmp_path, wig)
    repaired = _matrix()
    repaired.cells[0].pronto = "0000 006D 0002 0000 0050 0040 0020 0040"
    device = IRDevice(
        name="AC", commands=[], source_wig_id="u-source",
        climate_matrix=True,
    )
    _wire_matrix(fake_hass, tmp_path, device, repaired)
    conn = _conn()
    await ws_wigs_save(fake_hass, conn, {
        "id": 1, "type": "hair/wigs/save", "device_id": device.id,
        "mode": "update", "propose_lattice": True,
        "attest": {"claims": [{"digest": "d" * 16,
                               "verdict": VERDICT_WORKED}]},
    })
    conn.send_error.assert_not_called()
    result = conn.send_result.call_args[0][1]
    assert result["cells_proposed"] == 1
    after = json.loads(path.read_text())
    assert after["fittings"][0]["cells_hash"] == cells_content_hash(repaired)
    # And the file describes itself: a fresh receipt, not the one that
    # arrived with the broken lattice.
    assert "comb" in after


@pytest.mark.asyncio
async def test_a_matching_lattice_attests_without_proposing(
    fake_hass, tmp_path, _no_signing
):
    wig = _matrix_wig(_matrix())
    path = _closet_wig(tmp_path, wig)
    device = IRDevice(
        name="AC", commands=[], source_wig_id="u-source",
        climate_matrix=True,
    )
    _wire_matrix(fake_hass, tmp_path, device, _matrix())
    conn = _conn()
    await ws_wigs_save(fake_hass, conn, {
        "id": 1, "type": "hair/wigs/save", "device_id": device.id,
        "mode": "update",
        "attest": {"claims": [{"digest": "d" * 16,
                               "verdict": VERDICT_WORKED}]},
    })
    conn.send_error.assert_not_called()
    assert json.loads(path.read_text())["fittings"]


@pytest.mark.asyncio
async def test_proposing_without_attesting_is_allowed(
    fake_hass, tmp_path, _no_signing
):
    """Save without attesting is one of the three ways out, so a
    proposal on its own has to be writable."""
    wig = _matrix_wig(_matrix())
    path = _closet_wig(tmp_path, wig)
    repaired = _matrix()
    repaired.cells[0].pronto = "0000 006D 0002 0000 0050 0040 0020 0040"
    device = IRDevice(
        name="AC", commands=[], source_wig_id="u-source",
        climate_matrix=True,
    )
    _wire_matrix(fake_hass, tmp_path, device, repaired)
    conn = _conn()
    await ws_wigs_save(fake_hass, conn, {
        "id": 1, "type": "hair/wigs/save", "device_id": device.id,
        "mode": "update", "propose_lattice": True,
    })
    conn.send_error.assert_not_called()
    after = json.loads(path.read_text())
    assert "fittings" not in after
    assert (
        after["climate"]["cells"][0]["pronto"]
        == "0000 006D 0002 0000 0050 0040 0020 0040"
    )


class TestSupersedeAction:
    """hair/wigs/supersede: delete the old file, repoint its devices, top
    up the delta. Re-verify the pair first; refuse if it changed."""

    @pytest.mark.asyncio
    async def test_replace_deletes_relinks_and_tops_up_the_delta(
        self, fake_hass, tmp_path, _no_signing
    ):
        old = Wig(
            name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO_A)]
        )
        old_path = _closet_wig(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("On", PRONTO_A), WigSignal("Boost", PRONTO_B)],
        )
        _closet_wig(tmp_path, new, "new.wig.json")
        device = IRDevice(
            name="Living Room Fan", source_wig_id="old",
            commands=[_command("On", PRONTO_A)],
        )
        manager = _wire_many(fake_hass, tmp_path, [device])
        conn = _conn()
        await ws_wigs_supersede(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/supersede",
            "new_filename": "new.wig.json", "old_filename": "old.wig.json",
            "relink": True, "topup_device_ids": [device.id],
        })
        conn.send_error.assert_not_called()
        result = conn.send_result.call_args[0][1]
        assert result["deleted"] is True
        assert not old_path.exists()
        # Device repointed to the successor and topped up with EXACTLY the
        # delta (Boost); the row it already had (On) was not re-minted.
        assert device.source_wig_id == "new"
        assert result["devices"][0]["relinked"] is True
        assert result["devices"][0]["commands_added"] == 1
        assert sorted(c.name for c in device.commands) == ["Boost", "On"]
        manager.async_update_device.assert_awaited()

    @pytest.mark.asyncio
    async def test_topup_adds_nothing_when_the_device_already_has_it(
        self, fake_hass, tmp_path, _no_signing
    ):
        old = Wig(
            name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO_A)]
        )
        _closet_wig(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("On", PRONTO_A)],
        )
        _closet_wig(tmp_path, new, "new.wig.json")
        device = IRDevice(
            name="Fan", source_wig_id="old",
            commands=[_command("On", PRONTO_A)],
        )
        _wire_many(fake_hass, tmp_path, [device])
        conn = _conn()
        await ws_wigs_supersede(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/supersede",
            "new_filename": "new.wig.json", "old_filename": "old.wig.json",
            "relink": True, "topup_device_ids": [device.id],
        })
        result = conn.send_result.call_args[0][1]
        assert result["devices"][0]["commands_added"] == 0
        assert len(device.commands) == 1

    @pytest.mark.asyncio
    async def test_relink_false_leaves_the_device_pointer_standing(
        self, fake_hass, tmp_path, _no_signing
    ):
        old = Wig(
            name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO_A)]
        )
        _closet_wig(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("On", PRONTO_A)],
        )
        _closet_wig(tmp_path, new, "new.wig.json")
        device = IRDevice(
            name="Fan", source_wig_id="old",
            commands=[_command("On", PRONTO_A)],
        )
        _wire_many(fake_hass, tmp_path, [device])
        conn = _conn()
        await ws_wigs_supersede(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/supersede",
            "new_filename": "new.wig.json", "old_filename": "old.wig.json",
            "relink": False, "topup_device_ids": [],
        })
        conn.send_error.assert_not_called()
        # Nothing to touch: the device is neither relinked nor topped up.
        assert device.source_wig_id == "old"
        assert conn.send_result.call_args[0][1]["devices"] == []

    @pytest.mark.asyncio
    async def test_refuses_and_deletes_nothing_when_the_pair_changed(
        self, fake_hass, tmp_path, _no_signing
    ):
        old = Wig(
            name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO_A)]
        )
        old_path = _closet_wig(tmp_path, old, "old.wig.json")
        # The successor no longer names "old" in its ancestry: the closet
        # changed under the dialog, so the confirm is stale.
        new = Wig(
            name="Other", wig_id="new", supersedes=["unrelated"],
            signals=[WigSignal("On", PRONTO_A)],
        )
        _closet_wig(tmp_path, new, "new.wig.json")
        _wire_many(fake_hass, tmp_path, [])
        conn = _conn()
        await ws_wigs_supersede(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/supersede",
            "new_filename": "new.wig.json", "old_filename": "old.wig.json",
        })
        assert conn.send_error.call_args[0][1] == "pair_changed"
        assert old_path.exists()


_BLOCK_KEYS = {
    "old_filename", "old_name", "old_signals", "new_signals",
    "lost_digests", "lost_aliases", "devices",
}


class TestSupersessionDoorways:
    """Both doorways return the SAME block for the same pair: the drop bar
    (upload) and Save as new (create)."""

    @pytest.mark.asyncio
    async def test_upload_with_a_local_ancestor_returns_the_block(
        self, fake_hass, tmp_path
    ):
        old = Wig(
            name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO_A)]
        )
        _closet_wig(tmp_path, old, "old.wig.json")
        _wire_many(fake_hass, tmp_path, [])
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("On", PRONTO_A), WigSignal("Boost", PRONTO_B)],
        )
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload", "text": serialize_wig(new),
        })
        result = conn.send_result.call_args[0][1]
        assert "supersession" in result
        assert result["supersession"]["old_filename"] == "old.wig.json"
        assert set(result["supersession"]) == _BLOCK_KEYS

    @pytest.mark.asyncio
    async def test_upload_without_an_ancestor_has_no_block(
        self, fake_hass, tmp_path
    ):
        _wire_many(fake_hass, tmp_path, [])
        fresh = Wig(
            name="Fresh", wig_id="new", signals=[WigSignal("On", PRONTO_A)]
        )
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload", "text": serialize_wig(fresh),
        })
        assert "supersession" not in conn.send_result.call_args[0][1]

    @pytest.mark.asyncio
    async def test_save_as_new_self_supersession_returns_the_same_block(
        self, fake_hass, tmp_path, _no_signing
    ):
        # Someone perfect-fitted their own wig, found an eighth button,
        # added it on the device, and saves as new: the successor is born
        # in the closet and the create path returns the block itself.
        old = Wig(
            name="My Fan", wig_id="u-old", signals=[WigSignal("On", PRONTO_A)]
        )
        _closet_wig(tmp_path, old, "old.wig.json")
        device = IRDevice(
            name="My Fan", source_wig_id="u-old",
            commands=[_command("On", PRONTO_A), _command("Boost", PRONTO_B)],
        )
        _wire_many(fake_hass, tmp_path, [device])
        conn = _conn()
        await ws_wigs_save(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "My Fan v2",
        })
        result = conn.send_result.call_args[0][1]
        assert "supersession" in result
        assert result["supersession"]["old_filename"] == "old.wig.json"
        # Identical shape to the upload doorway.
        assert set(result["supersession"]) == _BLOCK_KEYS


@pytest.mark.asyncio
async def test_update_drops_a_foreign_digest_claim(
    fake_hass, tmp_path, _no_signing
):
    """The checklist stops signing ghosts (v0.9.7): a claim whose digest
    the wig does not carry never enters the bundle, even from a stale
    client that still offered the tick."""
    wig = Wig(
        name="Edifier", wig_id="u-source",
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )
    path = _closet_wig(tmp_path, wig)
    device = IRDevice(
        name="Speakers", commands=[_command("On", PRONTO_A)],
        source_wig_id="u-source",
    )
    _wire(fake_hass, tmp_path, device)
    conn = _conn()
    real = signal_row_digest(wig.signals[0])
    await ws_wigs_save(fake_hass, conn, {
        "id": 1, "type": "hair/wigs/save", "device_id": device.id,
        "mode": "update",
        "attest": {
            "claims": [
                {"digest": real, "verdict": VERDICT_WORKED},
                {"digest": "f" * 16, "verdict": VERDICT_WORKED},
            ],
            "handle": "David",
        },
    })
    conn.send_error.assert_not_called()
    after = json.loads(path.read_text())
    digests = [r["digest"] for r in after["fittings"][0]["rows"]]
    # The ghost never entered the bundle; the real claim is untouched.
    assert digests == [real]
