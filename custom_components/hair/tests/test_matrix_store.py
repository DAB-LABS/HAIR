"""Cold Cuts (v0.8.8): matrix files and the manager's matrix plumbing.

The contracts under test:

- Matrices live as their own files under hair/matrices/ (the devices
  JSON is rewritten wholesale on every update; a 7.9 MB census matrix
  must never ride that write). Round-trip, delete, and byte-copy for
  the device clone path.
- load_matrix returns None on ANY problem (missing, corrupt, wrong
  format, schema errors) -- the entity refuses rather than guesses.
- DeviceManager caches loaded matrices, invalidates on device delete,
  and deletes the file best-effort when a matrix device is removed.
- async_send_matrix_cell rides the SAME emitter broadcast path as
  async_send_command: pre-skip, per-emitter guard, honest
  all-unavailable failure, Mirror audit armed before transmit with
  the cell key as the command name.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.const import DOMAIN, DeviceType
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.matrix_store import (
    copy_matrix,
    delete_matrix,
    load_matrix,
    matrices_dir,
    write_matrix,
)
from custom_components.hair.models import IRDevice
from custom_components.hair.storage import HAIRStore
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    cells_content_hash,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0040 0020 0040 0020"


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "dry"],
        fan_modes=["auto", "low"],
        swing_modes=[],
        off=PRONTO_A,
        on=PRONTO_B,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=16.0, pronto=PRONTO_A),
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=PRONTO_B),
            ClimateCell(mode="cool", fan="low", temp=22.0, pronto=PRONTO_A),
            ClimateCell(mode="dry", fan="auto", pronto=PRONTO_B,
                        send_count=2),
        ],
    )


# ---------------------------------------------------------------------------
# The store: pure blocking-IO layer
# ---------------------------------------------------------------------------


class TestMatrixStore:
    def test_round_trip(self, tmp_path):
        write_matrix(tmp_path, "dev-1", _matrix())
        path = matrices_dir(tmp_path) / "dev-1.matrix.json"
        assert path.is_file()
        loaded = load_matrix(tmp_path, "dev-1")
        assert loaded is not None
        assert cells_content_hash(loaded) == cells_content_hash(_matrix())
        assert loaded.min_temp == 16.0 and loaded.max_temp == 30.0
        assert loaded.fan_modes == ["auto", "low"]
        # Verbatim send_count survives too.
        dry = next(c for c in loaded.cells if c.mode == "dry")
        assert dry.send_count == 2

    def test_file_shape(self, tmp_path):
        """The documented envelope: format marker + wig-shaped climate."""
        write_matrix(tmp_path, "dev-1", _matrix())
        data = json.loads(
            (matrices_dir(tmp_path) / "dev-1.matrix.json").read_text()
        )
        assert data["format"] == "hair-matrix/1"
        assert data["climate"]["min_temp"] == 16
        assert len(data["climate"]["cells"]) == 4

    def test_load_missing_is_none(self, tmp_path):
        assert load_matrix(tmp_path, "nope") is None

    def test_load_corrupt_json_is_none(self, tmp_path):
        d = matrices_dir(tmp_path)
        d.mkdir(parents=True)
        (d / "dev-1.matrix.json").write_text("{not json", encoding="utf-8")
        assert load_matrix(tmp_path, "dev-1") is None

    def test_load_wrong_format_is_none(self, tmp_path):
        d = matrices_dir(tmp_path)
        d.mkdir(parents=True)
        (d / "dev-1.matrix.json").write_text(
            json.dumps({"format": "hair-matrix/2", "climate": {}}),
            encoding="utf-8",
        )
        assert load_matrix(tmp_path, "dev-1") is None

    def test_load_schema_error_is_none(self, tmp_path):
        d = matrices_dir(tmp_path)
        d.mkdir(parents=True)
        (d / "dev-1.matrix.json").write_text(
            json.dumps({
                "format": "hair-matrix/1",
                "climate": {"min_temp": 16, "max_temp": 30,
                            "off": "garbage", "cells": []},
            }),
            encoding="utf-8",
        )
        assert load_matrix(tmp_path, "dev-1") is None

    def test_delete(self, tmp_path):
        write_matrix(tmp_path, "dev-1", _matrix())
        assert delete_matrix(tmp_path, "dev-1") is True
        assert not (matrices_dir(tmp_path) / "dev-1.matrix.json").exists()
        assert delete_matrix(tmp_path, "dev-1") is False

    def test_copy_for_clone(self, tmp_path):
        write_matrix(tmp_path, "src", _matrix())
        assert copy_matrix(tmp_path, "src", "dst") is True
        dst = load_matrix(tmp_path, "dst")
        assert dst is not None
        assert cells_content_hash(dst) == cells_content_hash(_matrix())
        # Byte copy: the files are identical.
        d = matrices_dir(tmp_path)
        assert (d / "src.matrix.json").read_bytes() == \
            (d / "dst.matrix.json").read_bytes()

    def test_copy_missing_source_is_false(self, tmp_path):
        assert copy_matrix(tmp_path, "nope", "dst") is False

    def test_unsafe_device_ids_refused(self, tmp_path):
        """Device ids are HAIR-minted uuids; anything path-like is a
        bug or an attack and must never leave the folder."""
        assert load_matrix(tmp_path, "../evil") is None
        assert delete_matrix(tmp_path, "../evil") is False
        assert copy_matrix(tmp_path, "../evil", "dst") is False
        assert copy_matrix(tmp_path, "src", "../evil") is False
        with pytest.raises(ValueError):
            write_matrix(tmp_path, "../evil", _matrix())


# ---------------------------------------------------------------------------
# DeviceManager: cache, delete hook, matrix cell sends
# ---------------------------------------------------------------------------


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.fixture
def manager(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.states.get = MagicMock(return_value=None)
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        store._loaded = True
        factory = EntityFactory(fake_hass)
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(
                    return_value=MagicMock(id="ha-dev-1")
                ),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


def _matrix_device(emitters: list[str] | None = None) -> IRDevice:
    return IRDevice(
        id="dev-1",
        name="Bedroom AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=emitters or ["infrared.blaster"],
        climate_matrix=True,
    )


class TestManagerMatrixCache:
    @pytest.mark.asyncio
    async def test_get_matrix_loads_and_caches(self, manager, tmp_path):
        write_matrix(tmp_path, "dev-1", _matrix())
        first = await manager.async_get_matrix("dev-1")
        assert first is not None
        # Delete the file behind the cache: the cached object survives,
        # which is the point (one disk read per install lifetime).
        delete_matrix(tmp_path, "dev-1")
        again = await manager.async_get_matrix("dev-1")
        assert again is first

    @pytest.mark.asyncio
    async def test_miss_is_not_cached(self, manager, tmp_path):
        assert await manager.async_get_matrix("dev-1") is None
        # A file appearing later (restored backup) is picked up.
        write_matrix(tmp_path, "dev-1", _matrix())
        assert await manager.async_get_matrix("dev-1") is not None

    @pytest.mark.asyncio
    async def test_remove_device_deletes_file_and_cache(
        self, manager, tmp_path
    ):
        device = _matrix_device()
        manager._store.add_device(device)
        write_matrix(tmp_path, "dev-1", _matrix())
        assert await manager.async_get_matrix("dev-1") is not None
        assert await manager.async_remove_device("dev-1") is True
        assert not (matrices_dir(tmp_path) / "dev-1.matrix.json").exists()
        assert "dev-1" not in manager._matrix_cache

    @pytest.mark.asyncio
    async def test_remove_device_survives_delete_failure(
        self, manager, tmp_path
    ):
        """Best-effort: a broken matrix cleanup never resurrects the
        device the user already deleted."""
        device = _matrix_device()
        manager._store.add_device(device)
        with patch(
            "custom_components.hair.matrix_store.delete_matrix",
            side_effect=OSError("disk says no"),
        ):
            assert await manager.async_remove_device("dev-1") is True
        assert manager.get_device("dev-1") is None


class _FakeMonitor:
    def __init__(self, log: list | None = None):
        self.calls = []
        self._log = log

    def record_send(self, command, source_label, emitter_entity_ids,
                    decoded_fingerprint=None, heard_future=None):
        self.calls.append({
            "label": source_label,
            "emitters": emitter_entity_ids,
            "decoded_fingerprint": decoded_fingerprint,
        })
        if self._log is not None:
            self._log.append("record")


class TestSendMatrixCell:
    def _wire_monitor(self, fake_hass, monitor):
        fake_hass.data[DOMAIN] = {"entry-1": {"signal_monitor": monitor}}

    @pytest.mark.asyncio
    async def test_sends_pronto_with_cell_label(self, manager, fake_hass):
        device = _matrix_device(["infrared.a", "infrared.b"])
        manager._store.add_device(device)
        monitor = _FakeMonitor()
        self._wire_monitor(fake_hass, monitor)
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send):
            await manager.async_send_matrix_cell(
                "dev-1", "cool/auto/22", PRONTO_B
            )
        # Broadcast: every configured emitter got the frame.
        sent_to = [c.args[1] for c in ir_send.call_args_list]
        assert sent_to == ["infrared.a", "infrared.b"]
        # The Mirror row is labeled by the cell key (owner ruling: the
        # send must read as the state it set, not "raw pronto").
        assert monitor.calls[0]["label"] == "Bedroom AC / cool/auto/22"
        assert monitor.calls[0]["emitters"] == ["infrared.a", "infrared.b"]
        assert monitor.calls[0]["decoded_fingerprint"] is None

    @pytest.mark.asyncio
    async def test_mirror_armed_before_transmit(self, manager, fake_hass):
        """record_send BEFORE the first frame, so the loopback echo is
        claimed as HAIR's own instead of entering the Sniffer."""
        order: list[str] = []
        device = _matrix_device()
        manager._store.add_device(device)
        self._wire_monitor(fake_hass, _FakeMonitor(log=order))

        async def _send(hass, emitter_id, ir_cmd):
            order.append("send")

        with patch.object(
            _infrared_mod, "async_send_command", AsyncMock(side_effect=_send)
        ):
            await manager.async_send_matrix_cell("dev-1", "off", PRONTO_A)
        assert order == ["record", "send"]

    @pytest.mark.asyncio
    async def test_send_count_repeats_frames(self, manager, fake_hass):
        device = _matrix_device()
        manager._store.add_device(device)
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send):
            await manager.async_send_matrix_cell(
                "dev-1", "dry/auto", PRONTO_B, send_count=2
            )
        assert ir_send.await_count == 2

    @pytest.mark.asyncio
    async def test_all_emitters_dead_raises_honest_message(
        self, manager, fake_hass
    ):
        device = _matrix_device(["infrared.a"])
        manager._store.add_device(device)
        ir_send = AsyncMock(side_effect=RuntimeError("Not connected!"))
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                pytest.raises(RuntimeError,
                              match="All emitters for Bedroom AC"):
            await manager.async_send_matrix_cell("dev-1", "off", PRONTO_A)

    @pytest.mark.asyncio
    async def test_partial_failure_succeeds_and_notifies(
        self, manager, fake_hass
    ):
        """The GH #65 semantics ride along: one dead blaster is a
        silent success plus a persistent notification."""
        import homeassistant.components.persistent_notification as pn

        device = _matrix_device(["infrared.dead", "infrared.live"])
        manager._store.add_device(device)

        async def _send(hass, emitter_id, ir_cmd):
            if emitter_id == "infrared.dead":
                raise RuntimeError("nope")

        with patch.object(pn, "async_create") as create, \
                patch.object(pn, "async_dismiss") as dismiss, \
                patch.object(
                    _infrared_mod, "async_send_command",
                    AsyncMock(side_effect=_send),
                ):
            await manager.async_send_matrix_cell(
                "dev-1", "cool/auto/16", PRONTO_A
            )  # no raise
        assert create.call_args.kwargs["notification_id"] == (
            "hair_emitter_down_infrared.dead"
        )
        dismissed = [c.args[1] for c in dismiss.call_args_list]
        assert "hair_emitter_down_infrared.live" in dismissed

    @pytest.mark.asyncio
    async def test_unknown_device_and_no_emitters(self, manager):
        with pytest.raises(KeyError):
            await manager.async_send_matrix_cell("nope", "off", PRONTO_A)
        device = _matrix_device([])
        device.emitter_entity_ids = []
        manager._store.add_device(device)
        with pytest.raises(RuntimeError, match="no emitters"):
            await manager.async_send_matrix_cell("dev-1", "off", PRONTO_A)
