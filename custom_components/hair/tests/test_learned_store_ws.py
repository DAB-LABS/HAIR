"""The learned-code store WS contract, both commands and both shapes.

The dialog is entirely driven by these two responses, so the payload
shapes are the contract: ``stores/list`` fills the card stack and
``stores/import`` fills the landing sentence. Every clause the dialog
can print has a counter here, which is why the import summary is
asserted key by key rather than "it returned something".

The list is where per-item resilience shows up. A corrupt store renders
its own card with a receipt where the counts go; it does not vanish, and
it does not take the healthy store beside it down.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import pluck
from custom_components.hair.const import DOMAIN
from custom_components.hair.pluckable_loader import load_pluckables
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    ws_pluck_list_vendors,
    ws_pluck_stores_forget,
    ws_pluck_stores_import,
    ws_pluck_stores_list,
)

from .test_learned_code_stores import (
    BROADLINK_STORE,
    TUYA_STORE,
    _broadlink_code,
    _tuya_code,
    _write_store,
)

PLUCKABLE_DIR = Path(__file__).parent.parent / "pluckable"
_TUYA_TAIL = 64464


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _wire(hass, config_dir: Path) -> SignalStore:
    signal_store = SignalStore(hass)
    signal_store._loaded = True
    signal_store.schedule_save = MagicMock()
    signal_store.async_save = AsyncMock()
    hair = MagicMock()
    hair.get_all_devices = MagicMock(return_value=[])
    hair.get_device = MagicMock(return_value=None)
    hair.async_save = AsyncMock()
    hair.match_command = MagicMock(return_value=None)
    monitor = SignalMonitor(hass, signal_store, hair)
    hass.config.config_dir = str(config_dir)
    hass.data[DOMAIN] = {
        "entry": {
            "device_manager": MagicMock(),
            "signal_store": signal_store,
            "signal_monitor": monitor,
            "pluckable_registry": load_pluckables(PLUCKABLE_DIR),
        }
    }
    return signal_store


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
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
        },
    )
    _write_store(
        tmp_path,
        TUYA_STORE,
        {
            "candles": {
                "pwr_on": _tuya_code([806, 806, 806, 1600, 806, 806, 806, _TUYA_TAIL]),
                "OFF": "AAAAAAAAAAAA",
            }
        },
    )
    return tmp_path


def _result(conn):
    conn.send_error.assert_not_called()
    conn.send_result.assert_called_once()
    return conn.send_result.call_args[0][1]


# ---------------------------------------------------------------------
# hair/pluck/stores/list
# ---------------------------------------------------------------------


class TestStoresList:
    async def test_both_integrations_in_one_list_broadlink_first(
        self, fake_hass, config_dir
    ):
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        stores = _result(conn)["stores"]
        assert [s["integration"] for s in stores] == ["broadlink", "tuya_local"]

    async def test_every_contract_field_is_present(self, fake_hass, config_dir):
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        broadlink = _result(conn)["stores"][0]
        assert set(broadlink) == {
            "store_id",
            "integration",
            "friendly_name",
            "subdevices",
            "codes",
            "ir_codes",
            "rf_codes",
            "error",
        }
        assert broadlink["store_id"] == "a4cf12880e2f"
        assert broadlink["subdevices"] == 2
        assert broadlink["codes"] == 3
        assert broadlink["ir_codes"] == 3
        assert broadlink["rf_codes"] == 1
        assert broadlink["error"] is None

    async def test_the_config_entry_title_becomes_the_name(
        self, fake_hass, config_dir
    ):
        _wire(fake_hass, config_dir)
        fake_hass.config_entries.async_entries = MagicMock(
            side_effect=lambda domain: (
                [SimpleNamespace(unique_id="eb6383fed1128526f7zzwf",
                                 title="IR Remote Garage")]
                if domain == "tuya_local"
                else []
            )
        )
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        tuya = _result(conn)["stores"][1]
        assert tuya["friendly_name"] == "IR Remote Garage"

    async def test_a_broadlink_device_name_beats_the_entry_title(
        self, fake_hass, config_dir
    ):
        """The MAC is a lookup key and never something the user reads."""
        _wire(fake_hass, config_dir)
        registry = MagicMock()
        registry.async_get_device.return_value = SimpleNamespace(
            name_by_user=None, name="Living Room RM4"
        )
        conn = _conn()
        with patch.object(pluck.dr, "async_get", return_value=registry):
            await ws_pluck_stores_list(
                fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
            )
        broadlink = _result(conn)["stores"][0]
        assert broadlink["friendly_name"] == "Living Room RM4"
        # Looked up by the colon form, built from the store id.
        connections = registry.async_get_device.call_args.kwargs["connections"]
        assert ("mac", "a4:cf:12:88:0e:2f") in connections

    async def test_a_nameless_store_falls_back_to_its_id_not_to_blank(
        self, fake_hass, config_dir
    ):
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        assert _result(conn)["stores"][0]["friendly_name"] == "a4cf12880e2f"

    async def test_a_corrupt_store_gets_a_receipt_and_keeps_its_siblings(
        self, fake_hass, config_dir
    ):
        (config_dir / ".storage" / "broadlink_remote_deadbeef0001_codes").write_text(
            "{not json", encoding="utf-8"
        )
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        stores = _result(conn)["stores"]
        assert len(stores) == 3
        broken = next(s for s in stores if s["store_id"] == "deadbeef0001")
        assert broken["error"] == "Could not read this file"
        assert all(s["error"] is None for s in stores if s is not broken)

    async def test_no_stores_is_an_empty_list_not_an_error(
        self, fake_hass, tmp_path
    ):
        _wire(fake_hass, tmp_path)
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        assert _result(conn)["stores"] == []

    async def test_no_hair_entry_is_an_error_not_a_crash(self, fake_hass):
        conn = _conn()
        await ws_pluck_stores_list(
            fake_hass, conn, {"id": 1, "type": "hair/pluck/stores/list"}
        )
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "not_configured"


# ---------------------------------------------------------------------
# hair/pluck/stores/import
# ---------------------------------------------------------------------


class TestStoresImport:
    async def test_the_landing_numbers_come_back_key_by_key(
        self, fake_hass, config_dir
    ):
        store = _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_import(
            fake_hass,
            conn,
            {
                "id": 1,
                "type": "hair/pluck/stores/import",
                "store_id": "a4cf12880e2f",
            },
        )
        summary = _result(conn)
        assert set(summary) == {
            "remotes",
            "signals",
            "washed",
            "kept_raw",
            "toggle_pairs",
            "rf_receipted",
            "no_timings",
            "already_present",
        }
        assert summary["remotes"] == 1
        assert summary["signals"] == 3
        assert summary["toggle_pairs"] == 1
        assert summary["rf_receipted"] == 1
        assert summary["already_present"] == 0
        assert len(store.get_all_devices()) == 1

    async def test_the_tuya_store_imports_through_its_own_decoder(
        self, fake_hass, config_dir
    ):
        """The misroute case, through the real WS path this time.

        ``pwr_on`` begins 806 us, which packs as bytes 26 03. If the
        dispatch ever went by payload instead of by store, this is the
        code that would come back quietly wrong.
        """
        store = _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_import(
            fake_hass,
            conn,
            {
                "id": 1,
                "type": "hair/pluck/stores/import",
                "store_id": "eb6383fed1128526f7zzwf",
            },
        )
        summary = _result(conn)
        assert summary["signals"] == 1
        assert summary["no_timings"] == 1

        from custom_components.hair.ir_command import ProntoCommand
        from custom_components.hair.wig_adapters import broadlink_b64_to_pronto

        signal = store.get_all_devices()[0].signals[0]
        stored = ProntoCommand(signal.code).get_raw_timings()

        # 815, not 806: Pronto quantizes every duration to whole carrier
        # periods, and at 38 kHz that period is 26.3 us, so 806 stores as
        # 31 periods and reads back as 815. That rounding is the Pronto
        # format and applies to every code in HAIR; the reader's own
        # timings are exactly 806 (pinned in test_learned_code_stores).
        assert stored[0] == 815

        # What the misroute would have produced, for contrast. If this
        # code had gone to the Broadlink parser, the first duration would
        # be near 1160 us, because 0x26 would have been read as a type
        # byte and 38 ticks of 30.5176 us as the first mark.
        misread = ProntoCommand(
            broadlink_b64_to_pronto(
                _tuya_code([806, 806, 806, 1600, 806, 806, 806, _TUYA_TAIL])
            )
        ).get_raw_timings()
        assert misread[0] == pytest.approx(1160, abs=30)
        assert stored[0] != misread[0]

    async def test_a_second_import_reports_already_present(
        self, fake_hass, config_dir
    ):
        store = _wire(fake_hass, config_dir)
        msg = {
            "id": 1,
            "type": "hair/pluck/stores/import",
            "store_id": "a4cf12880e2f",
        }
        await ws_pluck_stores_import(fake_hass, _conn(), msg)
        conn = _conn()
        await ws_pluck_stores_import(fake_hass, conn, msg)
        summary = _result(conn)
        assert summary["already_present"] == summary["signals"] == 3
        assert sum(len(d.signals) for d in store.get_all_devices()) == 3

    async def test_an_unknown_store_id_is_an_error_result(
        self, fake_hass, config_dir
    ):
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_import(
            fake_hass,
            conn,
            {"id": 1, "type": "hair/pluck/stores/import", "store_id": "nope"},
        )
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "unknown_store"

    async def test_a_corrupt_store_refuses_with_its_receipt(
        self, fake_hass, config_dir
    ):
        (config_dir / ".storage" / "broadlink_remote_deadbeef0001_codes").write_text(
            "{not json", encoding="utf-8"
        )
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_import(
            fake_hass,
            conn,
            {
                "id": 1,
                "type": "hair/pluck/stores/import",
                "store_id": "deadbeef0001",
            },
        )
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "unreadable_store"
        assert conn.send_error.call_args[0][2] == "Could not read this file"


# ---------------------------------------------------------------------
# The Devices-tab row and its delete
# ---------------------------------------------------------------------


class TestPluckedStoreRows:
    async def test_list_vendors_carries_the_plucked_stores(
        self, fake_hass, config_dir
    ):
        _wire(fake_hass, config_dir)
        fake_hass.services.has_service = MagicMock(return_value=False)
        await ws_pluck_stores_import(
            fake_hass,
            _conn(),
            {
                "id": 1,
                "type": "hair/pluck/stores/import",
                "store_id": "a4cf12880e2f",
            },
        )
        conn = _conn()
        await ws_pluck_list_vendors(
            fake_hass, conn, {"id": 2, "type": "hair/pluck/list-vendors"}
        )
        payload = _result(conn)
        assert payload["vendors"] == []
        assert len(payload["plucked_stores"]) == 1
        row = payload["plucked_stores"][0]
        assert row["kind"] == "Broadlink learned codes"
        assert row["friendly_name"] == "a4cf12880e2f"

    async def test_forgetting_a_row_leaves_the_remotes(
        self, fake_hass, config_dir
    ):
        store = _wire(fake_hass, config_dir)
        await ws_pluck_stores_import(
            fake_hass,
            _conn(),
            {
                "id": 1,
                "type": "hair/pluck/stores/import",
                "store_id": "a4cf12880e2f",
            },
        )
        record_id = store.get_plucked_stores()[0]["id"]
        conn = _conn()
        await ws_pluck_stores_forget(
            fake_hass,
            conn,
            {"id": 2, "type": "hair/pluck/stores/forget", "record_id": record_id},
        )
        assert _result(conn) == {"forgotten": True}
        assert store.get_plucked_stores() == []
        assert len(store.get_all_devices()) == 1

    async def test_forgetting_a_row_that_is_gone_is_an_error(
        self, fake_hass, config_dir
    ):
        _wire(fake_hass, config_dir)
        conn = _conn()
        await ws_pluck_stores_forget(
            fake_hass,
            conn,
            {"id": 1, "type": "hair/pluck/stores/forget", "record_id": "nope"},
        )
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "not_found"
