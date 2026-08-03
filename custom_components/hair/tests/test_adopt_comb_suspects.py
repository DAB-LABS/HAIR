"""Adopt carries the comb's doubts onto the device.

The comb runs at import and its receipt used to be closet-only
knowledge: the wig row glowed, the device built from it said nothing.
Under the Fitting Room model the device is where a person lives, tests
and attests, so a doubt that stays in the closet is a doubt nobody acts
on. These tests pin the flag crossing the boundary, and pin the three
places it must NOT appear.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.websocket_api import ws_wig_make_device
from custom_components.hair.wig_comb import comb_wig, stamp_receipt
from custom_components.hair.wig_format import Wig, WigSignal, serialize_wig

# Three frames of one shape and one that is not: the frame-shape
# outlier, which is a suspect. The odd one out is what the comb doubts.
PRONTO_HOUSE = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_ODD = "0000 006D 0004 0000 0020 0040 0020 0040 0030 0020 0020 0040"


@pytest.fixture
def wigs_dir_path(tmp_path):
    directory = tmp_path / "hair" / "wigs"
    directory.mkdir(parents=True)
    return directory


def _manager():
    manager = MagicMock()
    manager.async_create_device = AsyncMock()
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    manager.async_get_matrix = AsyncMock(return_value=None)
    return manager


def _wire(fake_hass, tmp_path, manager):
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "fitting_manager": None,
    }}


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _wig(combed=True, odd_bypassed=False):
    wig = Wig(name="TV", signals=[
        WigSignal(alias="Power", pronto=PRONTO_HOUSE),
        WigSignal(alias="Volume Up", pronto=PRONTO_HOUSE),
        WigSignal(alias="Volume Down", pronto=PRONTO_HOUSE),
        WigSignal(
            alias="Sleep",
            pronto=PRONTO_ODD,
            bypass_protocol=odd_bypassed,
        ),
    ])
    if combed:
        stamp_receipt(wig, comb_wig(wig), "2026-08-02")
    return wig


def _write(wigs_dir_path, wig, filename="tv.wig.json"):
    (wigs_dir_path / filename).write_text(
        serialize_wig(wig), encoding="utf-8"
    )
    return filename


async def _adopt(fake_hass, filename):
    conn = _conn()
    await ws_wig_make_device(fake_hass, conn, {
        "id": 1, "type": "hair/wigs/make-device",
        "filename": filename, "name": "TV",
        "device_type": "media_player",
        "emitter_entity_ids": ["infrared.e"],
    })
    conn.send_error.assert_not_called()
    result = conn.send_result.call_args.args[1]
    return {c["name"]: c["comb_suspect"] for c in result["commands"]}


@pytest.mark.asyncio
async def test_the_doubted_row_arrives_flagged(
    fake_hass, tmp_path, wigs_dir_path
):
    _wire(fake_hass, tmp_path, _manager())
    flags = await _adopt(fake_hass, _write(wigs_dir_path, _wig()))
    assert flags["Sleep"] is True


@pytest.mark.asyncio
async def test_the_rest_arrive_clean(fake_hass, tmp_path, wigs_dir_path):
    """The flag has to be worth something. If it landed on everything,
    the amber dot would be wallpaper and the person would stop reading
    it -- which is the same as not having it."""
    _wire(fake_hass, tmp_path, _manager())
    flags = await _adopt(fake_hass, _write(wigs_dir_path, _wig()))
    assert flags["Power"] is False
    assert flags["Volume Up"] is False
    assert flags["Volume Down"] is False


@pytest.mark.asyncio
async def test_an_uncombed_wig_carries_no_doubts(
    fake_hass, tmp_path, wigs_dir_path
):
    """NO RECEIPT is not the same as CLEAN, and adopt must not re-comb
    to find out. A wig nobody combed brings no claim either way, and
    inventing one at adopt would put the comb's authority behind a
    judgement it never made."""
    _wire(fake_hass, tmp_path, _manager())
    flags = await _adopt(
        fake_hass, _write(wigs_dir_path, _wig(combed=False))
    )
    assert set(flags.values()) == {False}


@pytest.mark.asyncio
async def test_a_pinned_row_is_not_a_suspect(
    fake_hass, tmp_path, wigs_dir_path
):
    """A bypassed row was never judged, so there is no doubt to carry.
    Same rule the closet already applies; the device must not invent a
    stricter one."""
    _wire(fake_hass, tmp_path, _manager())
    flags = await _adopt(
        fake_hass, _write(wigs_dir_path, _wig(odd_bypassed=True))
    )
    assert flags["Sleep"] is False
