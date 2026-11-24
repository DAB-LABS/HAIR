"""The Plucker's ghosts, server half: one ghost per sub-device.

``stores/list`` gives every store a ``remotes`` list, one entry per
sub-device, with its counts, the label a pluck would give it, whether
anything in it can be plucked, and the plucked remote it already is.
``stores/import`` takes an optional ``subdevice`` so one ghost plucks
one remote, and answers with ``device_ids``. Both are additions: a call
without the new field behaves exactly as before.

A remote is matched by (integration, store id, sub-device), the key the
import has always found remotes by, never by its label.
"""
from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.learned_code_stores import decode_broadlink_code
from custom_components.hair.websocket_api import (
    ws_pluck_stores_import,
    ws_pluck_stores_list,
)

from .test_learned_code_stores import (
    BROADLINK_STORE,
    OPENIRBLASTER_ENTRY_ID,
    OPENIRBLASTER_STORE,
    TUYA_STORE,
    _broadlink_code,
    _oirb_code,
    _oirb_data,
    _signed_nec,
    _tuya_code,
    _write_store,
)
from .test_learned_store_ws import _conn, _result, _wire

BROADLINK_ID = "a4cf12880e2f"


def _rm4_capture(first_byte: int, khz: int) -> str:
    """A made-up RM4 Pro capture in the layout core stores: byte 1
    0xC0, a length, the carrier in kHz at bytes 4 to 7, then ticks.
    Synthetic, not anyone's learned code."""
    ticks = bytes([12, 36, 12, 36, 36, 12] * 4)
    body = khz.to_bytes(4, "little") + ticks
    header = bytes([first_byte, 0xC0]) + len(body).to_bytes(2, "little")
    return base64.b64encode(header + body).decode("ascii")
TUYA_ID = "eb6383fed1128526f7zzwf"
_TUYA_TAIL = 64464


@pytest.fixture
def stores_dir(tmp_path: Path) -> Path:
    _write_store(
        tmp_path,
        BROADLINK_STORE,
        {
            "tv": {
                "power": _broadlink_code([9000, -4500, 560, -560, 560]),
                "mute": [
                    _broadlink_code([8900, -4400, 600, -600, 600]),
                    _broadlink_code([8900, -4400, 600, -1700, 600]),
                ],
            },
            "gate": {"open": _broadlink_code([400, -400, 400], type_byte=0xB2)},
            "soundbar": {
                "vol_up": _broadlink_code([9000, -4500, 560, -1690, 560]),
            },
            "spare": {},
            "garage": {
                # An RM4 Pro learns at 433.92 as 0xB1 and at 315 as
                # 0x78: the first byte follows the carrier.
                "open": _rm4_capture(0xB1, 433920),
                "close": _rm4_capture(0x78, 315000),
            },
        },
    )
    _write_store(
        tmp_path,
        TUYA_STORE,
        {
            "candles": {
                "pwr_on": _tuya_code([806, 806, 806, 1600, 806, 806, 806, _TUYA_TAIL]),
            }
        },
    )
    return tmp_path


async def _list(hass) -> list[dict]:
    conn = _conn()
    await ws_pluck_stores_list(hass, conn, {"id": 1, "type": "hair/pluck/stores/list"})
    return _result(conn)["stores"]


async def _import(hass, store_id: str, subdevice: str | None = None):
    msg = {"id": 1, "type": "hair/pluck/stores/import", "store_id": store_id}
    if subdevice is not None:
        msg["subdevice"] = subdevice
    conn = _conn()
    await ws_pluck_stores_import(hass, conn, msg)
    return conn


def _store(stores: list[dict], store_id: str) -> dict:
    return next(s for s in stores if s["store_id"] == store_id)


def _remote(store: dict, subdevice: str) -> dict:
    return next(r for r in store["remotes"] if r["subdevice"] == subdevice)


class TestRemotesOnTheList:
    async def test_every_sub_device_in_file_order_with_its_counts(
        self, fake_hass, stores_dir
    ):
        _wire(fake_hass, stores_dir)
        broadlink = _store(await _list(fake_hass), BROADLINK_ID)
        assert [r["subdevice"] for r in broadlink["remotes"]] == [
            "tv", "gate", "soundbar", "spare", "garage",
        ]
        tv = _remote(broadlink, "tv")
        assert set(tv) == {
            "subdevice", "label", "codes", "ir_codes", "rf_codes",
            "pluckable", "reason", "device_id",
        }
        # A toggle pair is one command and two packets, as the store's
        # own counts have always read.
        assert (tv["codes"], tv["ir_codes"], tv["rf_codes"]) == (2, 3, 0)
        # The store's totals are the sum of its sub-devices, unchanged.
        assert broadlink["subdevices"] == 5
        assert broadlink["codes"] == 6
        assert broadlink["ir_codes"] == 4
        assert broadlink["rf_codes"] == 3

    async def test_the_label_is_what_a_pluck_would_name_it(
        self, fake_hass, stores_dir
    ):
        _wire(fake_hass, stores_dir)
        fake_hass.config_entries.async_entries = MagicMock(
            side_effect=lambda domain: (
                [SimpleNamespace(unique_id=TUYA_ID, title="IR Remote Garage")]
                if domain == "tuya_local"
                else []
            )
        )
        tuya = _store(await _list(fake_hass), TUYA_ID)
        assert _remote(tuya, "candles")["label"] == "IR Remote Garage: candles"
        await _import(fake_hass, TUYA_ID, "candles")
        store = fake_hass.data[DOMAIN]["entry"]["signal_store"]
        assert [d.label for d in store.get_all_devices()] == [
            "IR Remote Garage: candles"
        ]

    async def test_an_empty_and_a_radio_only_sub_device_cannot_be_plucked(
        self, fake_hass, stores_dir
    ):
        _wire(fake_hass, stores_dir)
        broadlink = _store(await _list(fake_hass), BROADLINK_ID)
        gate = _remote(broadlink, "gate")
        assert (gate["pluckable"], gate["reason"]) == (False, "radio_only")
        spare = _remote(broadlink, "spare")
        assert (spare["pluckable"], spare["reason"]) == (False, "empty")
        tv = _remote(broadlink, "tv")
        assert (tv["pluckable"], tv["reason"]) == (True, None)

    async def test_an_rm4_pro_store_is_radio_by_its_header(
        self, fake_hass, stores_dir
    ):
        """Its first byte is not 0xB2 or 0xD7, so a first-byte peek
        read it as neither radio nor infrared, and the sub-device came
        out as empty."""
        _wire(fake_hass, stores_dir)
        garage = _remote(_store(await _list(fake_hass), BROADLINK_ID), "garage")
        assert (garage["codes"], garage["ir_codes"], garage["rf_codes"]) == (2, 0, 2)
        assert (garage["pluckable"], garage["reason"]) == (False, "radio_only")

    async def test_a_short_or_wrong_header_is_not_counted_as_radio(
        self, fake_hass, tmp_path
    ):
        good = base64.b64decode(_rm4_capture(0xB1, 433920))
        too_long = bytearray(good)
        too_long[2:4] = (len(good)).to_bytes(2, "little")  # does not fit
        no_mark = bytearray(good)
        no_mark[1] = 0x00
        off_band = bytearray(good)
        off_band[4:8] = (38).to_bytes(4, "little")
        _write_store(
            tmp_path,
            BROADLINK_STORE,
            {
                "odd": {
                    f"c{i}": base64.b64encode(bytes(p)).decode("ascii")
                    for i, p in enumerate((too_long, no_mark, off_band))
                }
            },
        )
        _wire(fake_hass, tmp_path)
        odd = _remote(_store(await _list(fake_hass), BROADLINK_ID), "odd")
        assert (odd["codes"], odd["rf_codes"]) == (3, 0)

    async def test_an_infrared_code_is_not_mistaken_for_an_rm4_capture(
        self, fake_hass, stores_dir
    ):
        assert decode_broadlink_code(
            _broadlink_code([9000, -4500, 560, -560, 560])
        )[2] is None

    async def test_nothing_is_plucked_yet(self, fake_hass, stores_dir):
        _wire(fake_hass, stores_dir)
        for store in await _list(fake_hass):
            assert all(r["device_id"] is None for r in store["remotes"])

    async def test_an_unreadable_store_has_no_remotes(self, fake_hass, stores_dir):
        (stores_dir / ".storage" / "broadlink_remote_deadbeef0001_codes").write_text(
            "{not json", encoding="utf-8"
        )
        _wire(fake_hass, stores_dir)
        broken = _store(await _list(fake_hass), "deadbeef0001")
        assert broken["error"] == "Could not read this file"
        assert broken["remotes"] == []

    async def test_a_flat_code_list_is_one_remote_named_for_the_store(
        self, fake_hass, tmp_path
    ):
        _write_store(
            tmp_path,
            OPENIRBLASTER_STORE,
            _oirb_data([_oirb_code("TV Power", _signed_nec())]),
        )
        _wire(fake_hass, tmp_path)
        fake_hass.config_entries.async_entries = MagicMock(
            side_effect=lambda domain: (
                [SimpleNamespace(
                    entry_id=OPENIRBLASTER_ENTRY_ID,
                    unique_id="2ca965aabbcc",
                    title="Den Blaster",
                )]
                if domain == "openirblaster"
                else []
            )
        )
        oirb = _store(await _list(fake_hass), OPENIRBLASTER_ENTRY_ID)
        assert len(oirb["remotes"]) == 1
        remote = oirb["remotes"][0]
        assert remote["subdevice"] == "OpenIRBlaster"
        assert remote["label"] == "Den Blaster"
        assert (remote["codes"], remote["pluckable"]) == (1, True)
        # Its key is the name the reader files the codes under, so a
        # sub-device import of it lands them.
        conn = await _import(fake_hass, OPENIRBLASTER_ENTRY_ID, "OpenIRBlaster")
        assert _result(conn)["signals"] == 1

    async def test_an_empty_flat_code_list_has_no_remotes(self, fake_hass, tmp_path):
        _write_store(tmp_path, OPENIRBLASTER_STORE, _oirb_data([]))
        _wire(fake_hass, tmp_path)
        oirb = _store(await _list(fake_hass), OPENIRBLASTER_ENTRY_ID)
        assert oirb["remotes"] == []


class TestPluckedOrGhost:
    async def test_a_plucked_sub_device_carries_its_remote(
        self, fake_hass, stores_dir
    ):
        _wire(fake_hass, stores_dir)
        conn = await _import(fake_hass, BROADLINK_ID, "tv")
        (device_id,) = _result(conn)["device_ids"]
        broadlink = _store(await _list(fake_hass), BROADLINK_ID)
        assert _remote(broadlink, "tv")["device_id"] == device_id
        assert _remote(broadlink, "soundbar")["device_id"] is None

    async def test_a_renamed_remote_is_still_matched_by_its_key(
        self, fake_hass, stores_dir
    ):
        store = _wire(fake_hass, stores_dir)
        await _import(fake_hass, BROADLINK_ID, "tv")
        device = store.get_all_devices()[0]
        device.label = "Bedroom TV"
        broadlink = _store(await _list(fake_hass), BROADLINK_ID)
        assert _remote(broadlink, "tv")["device_id"] == device.id

    async def test_deleting_the_remote_brings_its_ghost_back(
        self, fake_hass, stores_dir
    ):
        store = _wire(fake_hass, stores_dir)
        await _import(fake_hass, BROADLINK_ID, "tv")
        device = store.get_all_devices()[0]
        store.remove_device(device.id)
        broadlink = _store(await _list(fake_hass), BROADLINK_ID)
        assert _remote(broadlink, "tv")["device_id"] is None
        # The store record outlives its remotes, by design.
        assert len(store.get_plucked_stores()) == 1

    async def test_a_store_plucked_whole_shows_every_remote_plucked(
        self, fake_hass, stores_dir
    ):
        """The way every store was plucked before ghosts: nothing to
        migrate, since those remotes carry the same key."""
        _wire(fake_hass, stores_dir)
        await _import(fake_hass, BROADLINK_ID)
        broadlink = _store(await _list(fake_hass), BROADLINK_ID)
        plucked = {
            r["subdevice"] for r in broadlink["remotes"] if r["device_id"]
        }
        # The radio-only and empty sub-devices never became remotes.
        assert plucked == {"tv", "soundbar"}


class TestImportOneSubDevice:
    async def test_only_that_sub_device_lands(self, fake_hass, stores_dir):
        store = _wire(fake_hass, stores_dir)
        conn = await _import(fake_hass, BROADLINK_ID, "soundbar")
        summary = _result(conn)
        assert summary["remotes"] == 1
        assert summary["signals"] == 1
        assert summary["rf_receipted"] == 0
        devices = store.get_all_devices()
        assert [d.store_subdevice for d in devices] == ["soundbar"]
        assert summary["device_ids"] == [devices[0].id]
        assert len(store.get_plucked_stores()) == 1

    async def test_a_second_click_adds_nothing(self, fake_hass, stores_dir):
        store = _wire(fake_hass, stores_dir)
        first = _result(await _import(fake_hass, BROADLINK_ID, "tv"))
        second = _result(await _import(fake_hass, BROADLINK_ID, "tv"))
        assert second["already_present"] == second["signals"] == 3
        assert second["device_ids"] == first["device_ids"]
        assert len(store.get_all_devices()) == 1
        assert sum(len(d.signals) for d in store.get_all_devices()) == 3

    async def test_a_sub_device_the_store_no_longer_has(self, fake_hass, stores_dir):
        _wire(fake_hass, stores_dir)
        conn = await _import(fake_hass, BROADLINK_ID, "kitchen")
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "unknown_subdevice"

    async def test_the_key_is_sent_as_is_not_trimmed(self, fake_hass, stores_dir):
        _wire(fake_hass, stores_dir)
        conn = await _import(fake_hass, BROADLINK_ID, " tv ")
        assert conn.send_error.call_args[0][1] == "unknown_subdevice"

    async def test_an_empty_sub_device_is_an_empty_error(
        self, fake_hass, stores_dir
    ):
        _wire(fake_hass, stores_dir)
        conn = await _import(fake_hass, BROADLINK_ID, "spare")
        assert conn.send_error.call_args[0][1] == "empty_store"
        assert conn.send_error.call_args[0][2] == "That remote has no codes in it"

    async def test_a_radio_only_sub_device_lands_nothing(
        self, fake_hass, stores_dir
    ):
        store = _wire(fake_hass, stores_dir)
        summary = _result(await _import(fake_hass, BROADLINK_ID, "gate"))
        assert summary["rf_receipted"] == 1
        assert summary["device_ids"] == []
        assert store.get_all_devices() == []

    async def test_without_a_sub_device_the_whole_store_lands(
        self, fake_hass, stores_dir
    ):
        store = _wire(fake_hass, stores_dir)
        summary = _result(await _import(fake_hass, BROADLINK_ID))
        assert summary["remotes"] == 2
        assert summary["signals"] == 4
        # Counted as radio on the list; reading them is separate work,
        # so the import still sets them aside as before.
        assert summary["rf_receipted"] == 1
        assert sorted(summary["device_ids"]) == sorted(
            d.id for d in store.get_all_devices()
        )
