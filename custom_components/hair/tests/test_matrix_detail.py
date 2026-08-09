"""Cold Cuts second half (2026-07-29): the matrix device-detail WS
surface and the adopt signpost.

The contracts under test:

- The gated matrix clip stamps wig provenance (source_wig) on the
  clipped remote, and re-clipping collapses onto the one remote while
  REFRESHING the stamp (owner ruling CC5).
- The signpost resolves present / renamed / gone at list time:
  filename first, then cells_content_hash over the closet's matrix
  wigs, so a renamed wig still points home. Only stamped remotes pay.
- matrix-cells serves the whole lattice compactly: short keys, absent
  dimensions omitted, and not one byte of Pronto.
- matrix-send and matrix-command resolve EXACTLY -- the frontend
  sends coordinates read off matrix-cells, so a miss is not_found,
  never a snap. Sends and saved commands carry the display grammar,
  and a saved command's source is "matrix" (the STATE origin chip).

materialize_wig's own matrix behavior is pinned in test_wig_closet;
the display grammar itself in test_wig_climate.
"""
from __future__ import annotations

import json
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from custom_components.hair.const import (
    DOMAIN,
    CommandSource,
    DeviceType,
)
from custom_components.hair.models import IRDevice, UnknownDevice
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    _resolve_source_wig_states,
    ws_codes_import_remote,
    ws_device_matrix_cells,
    ws_device_matrix_command,
    ws_device_matrix_send,
    ws_get_unknown_devices,
    ws_update_device,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    cells_content_hash,
)
from custom_components.hair.wig_store import load_wig, write_wig_text

PRONTO = (
    "0000 006D 0006 0000 00E0 0070 0014 000D 0014 002E "
    "0014 000D 0014 000D 0014 0400"
)


def _p(word: str) -> str:
    """A distinct valid Pronto per duration word (distinct identity)."""
    return PRONTO.replace("002E", word)


def _matrix_wig_text(name: str = "Cold AC") -> str:
    return json.dumps({
        "format": "hair-wig/2",
        "name": name,
        "signals": [{"alias": "Beep", "pronto": _p("0020")}],
        "climate": {
            "min_temp": 16,
            "max_temp": 30,
            "precision": 1,
            "modes": ["cool", "dry"],
            "fan_modes": ["auto", "quiet"],
            "swing_modes": ["swing"],
            "off": _p("0060"),
            "on": _p("0090"),
            "cells": [
                {"mode": "cool", "fan": "auto", "temp": 22,
                 "pronto": _p("00C0")},
                {"mode": "cool", "fan": "quiet", "swing": "swing",
                 "temp": 25, "pronto": _p("0100"), "send_count": 2},
                {"mode": "dry", "fan": "auto", "pronto": _p("0130")},
            ],
        },
    })


def _make_connection():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _wire_hass(hass, manager=None, signal_monitor=None):
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager or MagicMock(),
        "orchestrator": MagicMock(),
        "signal_monitor": signal_monitor or MagicMock(),
    }}


def _real_monitor(hass) -> SignalMonitor:
    signal_store = SignalStore(hass)
    signal_store._loaded = True
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.async_save = AsyncMock()
    return SignalMonitor(hass, signal_store, hair_store)


# ---------------------------------------------------------------------------
# Clip stamp (owner ruling CC5)
# ---------------------------------------------------------------------------


class TestClipStamp:
    async def _clip(self, fake_hass, conn, filename, include_matrix=True):
        await ws_codes_import_remote(fake_hass, conn, {
            "id": 1,
            "type": "hair/codes/import-remote",
            "codebook_id": f"wig:{filename}",
            "include_matrix": include_matrix,
        })
        return conn.send_result.call_args[0][1]

    @pytest.mark.asyncio
    async def test_matrix_clip_stamps_provenance(self, fake_hass, tmp_path):
        fake_hass.config.config_dir = str(tmp_path)
        monitor = _real_monitor(fake_hass)
        _wire_hass(fake_hass, signal_monitor=monitor)
        filename = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")

        result = await self._clip(fake_hass, _make_connection(), filename)
        # Flat signal + Off + On + 3 cells, named by the grammar.
        aliases = [s["alias"] for s in result["device"]["signals"]]
        assert aliases == [
            "Beep", "Off", "On",
            "cool / fan: auto / 22",
            "cool / fan: quiet / swing: swing / 25",
            "dry / fan: auto",
        ]
        wig = load_wig(tmp_path, filename)
        assert result["device"]["source_wig"] == {
            "filename": filename,
            "cells_hash": cells_content_hash(wig.climate),
        }
        # send_count carried onto the clipped signal.
        by_alias = {s["alias"]: s for s in result["device"]["signals"]}
        assert by_alias[
            "cool / fan: quiet / swing: swing / 25"
        ]["send_count"] == 2

    @pytest.mark.asyncio
    async def test_clip_names_mint_in_the_install_unit(
        self, fake_hass, tmp_path
    ):
        """Mint-time naming (unit ruling 2026-07-29): on an imperial
        install a C-file clip mints Fahrenheit names, frozen there;
        temp-less cells and flat signals ride unchanged."""
        from homeassistant.const import UnitOfTemperature

        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.config.units.temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
        )
        _wire_hass(fake_hass, signal_monitor=_real_monitor(fake_hass))
        filename = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")
        result = await self._clip(fake_hass, _make_connection(), filename)
        aliases = [s["alias"] for s in result["device"]["signals"]]
        assert aliases == [
            "Beep", "Off", "On",
            "cool / fan: auto / 72",
            "cool / fan: quiet / swing: swing / 77",
            "dry / fan: auto",
        ]

    @pytest.mark.asyncio
    async def test_flat_clip_of_matrix_wig_leaves_no_stamp(
        self, fake_hass, tmp_path
    ):
        """Gate closed: matrix wigs clip flat-only, exactly as today,
        stamp included -- "as today" means no provenance either."""
        fake_hass.config.config_dir = str(tmp_path)
        _wire_hass(fake_hass, signal_monitor=_real_monitor(fake_hass))
        filename = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")
        result = await self._clip(
            fake_hass, _make_connection(), filename, include_matrix=False
        )
        aliases = [s["alias"] for s in result["device"]["signals"]]
        assert aliases == ["Beep"]
        assert result["device"]["source_wig"] is None

    @pytest.mark.asyncio
    async def test_reclip_collapses_and_refreshes_stamp(
        self, fake_hass, tmp_path
    ):
        """Re-clipping merges onto the one remote (the existing
        re-try-on behavior) and the stamp follows the wig's CURRENT
        filename, so a clip after a rename repoints the signpost."""
        fake_hass.config.config_dir = str(tmp_path)
        monitor = _real_monitor(fake_hass)
        _wire_hass(fake_hass, signal_monitor=monitor)
        first = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")
        one = await self._clip(fake_hass, _make_connection(), first)

        # Same wig content under a new closet name.
        (tmp_path / "hair/wigs" / first).unlink()
        second = write_wig_text(tmp_path, _matrix_wig_text(), "Renamed AC")
        two = await self._clip(fake_hass, _make_connection(), second)

        assert two["merged"] is True
        assert two["device"]["id"] == one["device"]["id"]
        # Every re-clipped signal collapsed onto its existing row.
        assert two["imported"] == 0
        assert two["device"]["source_wig"]["filename"] == second


# ---------------------------------------------------------------------------
# Signpost resolution (present / renamed / gone)
# ---------------------------------------------------------------------------


class TestSignpost:
    def _stamp(self, tmp_path, filename):
        wig = load_wig(tmp_path, filename)
        return {
            "filename": filename,
            "cells_hash": cells_content_hash(wig.climate),
        }

    def test_present_renamed_gone(self, tmp_path):
        filename = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")
        stamp = self._stamp(tmp_path, filename)

        assert _resolve_source_wig_states(str(tmp_path), [stamp]) == [
            ("present", filename)
        ]

        # Rename: same cells under a new closet name resolves by hash
        # (owner ruling CC5: rename-safe).
        (tmp_path / "hair/wigs" / filename).unlink()
        renamed = write_wig_text(
            tmp_path, _matrix_wig_text("Renamed AC"), "Renamed AC"
        )
        assert _resolve_source_wig_states(str(tmp_path), [stamp]) == [
            ("renamed", renamed)
        ]

        # Gone: no file, no hash match.
        (tmp_path / "hair/wigs" / renamed).unlink()
        assert _resolve_source_wig_states(str(tmp_path), [stamp]) == [
            ("gone", None)
        ]

    def test_hash_match_ignores_name_field_changes(self, tmp_path):
        """The rename fallback keys on CELLS, not the wig's name: the
        hash covers the matrix, so editing name/notes still matches."""
        filename = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")
        stamp = self._stamp(tmp_path, filename)
        stamp["filename"] = "long-gone.wig.json"
        assert _resolve_source_wig_states(str(tmp_path), [stamp]) == [
            ("renamed", filename)
        ]

    def test_empty_closet_is_gone(self, tmp_path):
        stamp = {"filename": "x.wig.json", "cells_hash": "sha256:ab"}
        assert _resolve_source_wig_states(str(tmp_path), [stamp]) == [
            ("gone", None)
        ]

    @pytest.mark.asyncio
    async def test_list_payload_annotates_only_stamped_remotes(
        self, fake_hass, tmp_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        filename = write_wig_text(tmp_path, _matrix_wig_text(), "Cold AC")
        stamped = UnknownDevice(
            label="Cold AC", source="manual",
            source_wig=self._stamp(tmp_path, filename),
        )
        plain = UnknownDevice(label="Plain Remote", source="manual")
        monitor = MagicMock()
        monitor.get_unknown_devices = MagicMock(
            return_value=[stamped, plain]
        )
        _wire_hass(fake_hass, signal_monitor=monitor)

        conn = _make_connection()
        await ws_get_unknown_devices(
            fake_hass, conn, {"id": 5, "type": "hair/unknown/devices"}
        )
        rows = conn.send_result.call_args[0][1]
        assert rows[0]["source_wig_state"] == "present"
        assert rows[0]["source_wig_filename"] == filename
        assert rows[0]["source_wig"]["filename"] == filename
        # Unstamped remotes carry no signpost keys at all.
        assert "source_wig_state" not in rows[1]
        assert rows[1]["source_wig"] is None


# ---------------------------------------------------------------------------
# The cell browser: matrix-cells / matrix-send / matrix-command
# ---------------------------------------------------------------------------


def _entity_matrix(
    real_prontos: bool = False, with_on: bool = False
) -> ClimateMatrix:
    """A small lattice; tags for send tests, real Pronto for saves.
    ``with_on`` adds a discrete on code (matrix-power-row.md item 1's
    "On chip only when the matrix has one" case) -- absent by default,
    matching the far more common off-only shape."""
    def code(tag: str, word: str) -> str:
        return _p(word) if real_prontos else tag

    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "dry"],
        fan_modes=["auto", "quiet"],
        swing_modes=["swing"],
        off=code("P-OFF", "0060"),
        on=code("P-ON", "0090") if with_on else None,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0,
                        pronto=code("P-C-A-22", "00C0")),
            ClimateCell(mode="cool", fan="quiet", swing="swing",
                        temp=25.0, pronto=code("P-C-Q-S-25", "0100"),
                        send_count=2),
            ClimateCell(mode="dry", fan="auto",
                        pronto=code("P-D-A", "0130")),
        ],
    )


def _matrix_device() -> IRDevice:
    return IRDevice(
        id="dev-1", name="Bedroom AC", device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"], climate_matrix=True,
    )


def _wire_matrix(fake_hass, matrix, device=None):
    device = device or _matrix_device()
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    manager.async_send_matrix_cell = AsyncMock()
    manager.async_update_device = AsyncMock(return_value=device)
    _wire_hass(fake_hass, manager=manager)
    return manager, device


class TestMatrixCells:
    @pytest.mark.asyncio
    async def test_compact_lattice_without_prontos(self, fake_hass):
        _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_cells(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-cells",
            "device_id": "dev-1",
        })
        payload = conn.send_result.call_args[0][1]
        # Bounds and cell temps NATIVE, the file's unit riding along
        # (unit ruling 2026-07-29): the frontend converts for display
        # and computes absent tiles from these native numbers.
        assert payload["min_temp"] == 16.0
        assert payload["max_temp"] == 30.0
        assert payload["precision"] == 1.0
        assert payload["unit"] == "C"
        assert payload["modes"] == ["cool", "dry"]
        assert payload["fan_modes"] == ["auto", "quiet"]
        assert payload["swing_modes"] == ["swing"]
        assert payload["has_on"] is False
        # Short keys; absent dimensions OMITTED, not spelled null --
        # 2,689 cells must stay lightweight.
        assert payload["cells"] == [
            {"m": "cool", "f": "auto", "t": 22.0},
            {"m": "cool", "f": "quiet", "s": "swing", "t": 25.0},
            {"m": "dry", "f": "auto"},
        ]
        # Not one byte of Pronto anywhere in the payload.
        assert "P-C-A-22" not in json.dumps(payload)

    @pytest.mark.asyncio
    async def test_non_matrix_device_errors(self, fake_hass):
        device = _matrix_device()
        device.climate_matrix = False
        _wire_matrix(fake_hass, None, device=device)
        conn = _make_connection()
        await ws_device_matrix_cells(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-cells",
            "device_id": "dev-1",
        })
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "not_found"


class TestMatrixSend:
    @pytest.mark.asyncio
    async def test_exact_cell_sends_display_name(self, fake_hass):
        manager, _device = _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1", "mode": "cool", "fan": "quiet",
            "swing": "swing", "temp": 25,
        })
        manager.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: quiet / swing: swing / 25",
            "P-C-Q-S-25", 2, heard_future=ANY,
        )
        # Second Fitting v3 punch list item 14: nothing echoed back
        # through the mocked manager, so heard is false after the
        # wait -- the same "mocked send times out honestly" shape
        # test_send_command_success already pins for the flat path.
        conn.send_result.assert_called_once_with(
            1, {
                "sent": "cool / fan: quiet / swing: swing / 25",
                "heard": False, "receiver": None,
            }
        )

    @pytest.mark.asyncio
    async def test_a_heard_echo_reports_heard_true(self, fake_hass):
        """The manager resolving the heard_future -- the real
        _async_broadcast -> record_send -> _match_echo path, mocked
        here at the seam -- reaches the WS response unchanged. Second
        Fitting v3 punch list item 14's guard: a cell TEST with the
        receiver live reports heard."""
        manager, _device = _wire_matrix(fake_hass, _entity_matrix())

        async def _resolve_heard(*_args, heard_future=None, **_kw):
            if heard_future is not None:
                heard_future.set_result("infrared.receiver")

        manager.async_send_matrix_cell = AsyncMock(side_effect=_resolve_heard)
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1", "mode": "cool", "fan": "quiet",
            "swing": "swing", "temp": 25,
        })
        conn.send_result.assert_called_once_with(
            1, {
                "sent": "cool / fan: quiet / swing: swing / 25",
                "heard": True, "receiver": "infrared.receiver",
            }
        )

    @pytest.mark.asyncio
    async def test_mirror_label_converts_to_the_install_unit(
        self, fake_hass
    ):
        """The unit ruling's LIVE surface: nothing persists on a bare
        send, so the label follows the install's unit of the moment
        while the lookup coordinates stay native."""
        from homeassistant.const import UnitOfTemperature

        fake_hass.config.units.temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
        )
        manager, _device = _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1", "mode": "cool", "fan": "auto",
            "temp": 22,
        })
        manager.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "cool / fan: auto / 72", "P-C-A-22", 1,
            heard_future=ANY,
        )
        conn.send_result.assert_called_once_with(
            1, {
                "sent": "cool / fan: auto / 72",
                "heard": False, "receiver": None,
            }
        )

    @pytest.mark.asyncio
    async def test_never_snaps(self, fake_hass):
        """23 sits between real temps; the browser sent stale
        coordinates and the honest answer is not_found."""
        manager, _device = _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1", "mode": "cool", "fan": "auto",
            "temp": 23,
        })
        manager.async_send_matrix_cell.assert_not_awaited()
        assert conn.send_error.call_args[0][1] == "not_found"

    @pytest.mark.asyncio
    async def test_power_off(self, fake_hass):
        manager, _device = _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1", "power": "off",
        })
        manager.async_send_matrix_cell.assert_awaited_once_with(
            "dev-1", "Off", "P-OFF", 1, heard_future=ANY,
        )

    @pytest.mark.asyncio
    async def test_power_on_without_on_code_errors(self, fake_hass):
        manager, _device = _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1", "power": "on",
        })
        manager.async_send_matrix_cell.assert_not_awaited()
        assert conn.send_error.call_args[0][1] == "not_found"

    @pytest.mark.asyncio
    async def test_neither_power_nor_mode_errors(self, fake_hass):
        _wire_matrix(fake_hass, _entity_matrix())
        conn = _make_connection()
        await ws_device_matrix_send(fake_hass, conn, {
            "id": 1, "type": "hair/devices/matrix-send",
            "device_id": "dev-1",
        })
        assert conn.send_error.call_args[0][1] == "invalid_format"


class TestMatrixCommand:
    def _msg(self, **coords):
        return {
            "id": 1, "type": "hair/devices/matrix-command",
            "device_id": "dev-1", **coords,
        }

    @pytest.mark.asyncio
    async def test_save_state_builds_stamped_command(self, fake_hass):
        manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(
            fake_hass, conn,
            self._msg(mode="cool", fan="quiet", swing="swing", temp=25),
        )
        manager.async_update_device.assert_awaited_once_with(device)
        assert len(device.commands) == 1
        command = device.commands[0]
        assert command.name == "cool / fan: quiet / swing: swing / 25"
        # Fresh identity, exactly like adopt's per-signal stamping.
        assert command.protocol == "PRONTO"
        assert command.code is not None
        assert command.byte_hash is not None
        assert command.raw_timings
        assert command.send_count == 2
        # The origin marker: source "matrix" IS the STATE chip signal.
        assert command.source == CommandSource.MATRIX
        payload = conn.send_result.call_args[0][1]
        assert payload["commands"][0]["source"] == "matrix"

    @pytest.mark.asyncio
    async def test_saved_name_mints_in_the_install_unit(self, fake_hass):
        """Mint-time naming (unit ruling 2026-07-29): the saved
        command's name freezes in the install's unit as of now; the
        lookup coordinates stay native."""
        from homeassistant.const import UnitOfTemperature

        fake_hass.config.units.temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
        )
        _manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        await ws_device_matrix_command(
            fake_hass, _make_connection(),
            self._msg(mode="cool", fan="quiet", swing="swing", temp=25),
        )
        assert device.commands[0].name == (
            "cool / fan: quiet / swing: swing / 77"
        )

    @pytest.mark.asyncio
    async def test_saving_twice_replaces_by_name(self, fake_hass):
        _manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        msg = self._msg(mode="cool", fan="auto", temp=22)
        await ws_device_matrix_command(fake_hass, _make_connection(), msg)
        first_id = device.commands[0].id
        await ws_device_matrix_command(fake_hass, _make_connection(), msg)
        # One command, same id: refreshed, not twinned.
        assert len(device.commands) == 1
        assert device.commands[0].id == first_id

    @pytest.mark.asyncio
    async def test_exact_resolve_or_not_found(self, fake_hass):
        manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(
            fake_hass, conn, self._msg(mode="cool", fan="auto", temp=23)
        )
        assert conn.send_error.call_args[0][1] == "not_found"
        assert device.commands == []
        manager.async_update_device.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_depth1_cell_saves(self, fake_hass):
        _manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        await ws_device_matrix_command(
            fake_hass, _make_connection(),
            self._msg(mode="dry", fan="auto"),
        )
        assert device.commands[0].name == "dry / fan: auto"

    # -------------------------------------------------------------
    # Power promotion (matrix-power-row.md items 2 & 4, ruled
    # 2026-08-08 / 2026-08-09) -- "+ Command" for the Power row.
    # -------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_power_off_mints_matrix_source_command(self, fake_hass):
        manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(
            fake_hass, conn, self._msg(power="off"),
        )
        manager.async_update_device.assert_awaited_once_with(device)
        assert len(device.commands) == 1
        command = device.commands[0]
        # state_display_name("off") is the same grammar a power SEND
        # uses -- the card and the stored command speak the same word.
        assert command.name == "Off"
        assert command.source == CommandSource.MATRIX
        assert command.send_count == 1
        assert command.code is not None

    @pytest.mark.asyncio
    async def test_power_on_without_on_code_errors_not_found(
        self, fake_hass
    ):
        manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(
            fake_hass, conn, self._msg(power="on"),
        )
        assert conn.send_error.call_args[0][1] == "not_found"
        assert device.commands == []
        manager.async_update_device.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_power_on_with_code_mints(self, fake_hass):
        manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True, with_on=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(
            fake_hass, conn, self._msg(power="on"),
        )
        manager.async_update_device.assert_awaited_once_with(device)
        assert len(device.commands) == 1
        assert device.commands[0].name == "On"
        assert device.commands[0].source == CommandSource.MATRIX

    @pytest.mark.asyncio
    async def test_saving_same_power_twice_replaces_not_twins(
        self, fake_hass
    ):
        _manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        msg = self._msg(power="off")
        await ws_device_matrix_command(fake_hass, _make_connection(), msg)
        first_id = device.commands[0].id
        await ws_device_matrix_command(fake_hass, _make_connection(), msg)
        assert len(device.commands) == 1
        assert device.commands[0].id == first_id

    @pytest.mark.asyncio
    async def test_neither_power_nor_mode_errors_invalid_format(
        self, fake_hass
    ):
        _manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(fake_hass, conn, self._msg())
        assert conn.send_error.call_args[0][1] == "invalid_format"
        assert device.commands == []

    @pytest.mark.asyncio
    async def test_both_power_and_mode_errors_invalid_format(
        self, fake_hass
    ):
        _manager, device = _wire_matrix(
            fake_hass, _entity_matrix(real_prontos=True)
        )
        conn = _make_connection()
        await ws_device_matrix_command(
            fake_hass, conn, self._msg(power="off", mode="cool", fan="auto"),
        )
        assert conn.send_error.call_args[0][1] == "invalid_format"
        assert device.commands == []


# ---------------------------------------------------------------------------
# Type lock (matrix-power-row.md item 4, ruled 2026-08-08)
# ---------------------------------------------------------------------------


class TestMatrixTypeLock:
    @pytest.mark.asyncio
    async def test_device_type_change_refused_on_matrix_device(
        self, fake_hass
    ):
        device = _matrix_device()
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        _wire_hass(fake_hass, manager=manager)
        conn = _make_connection()
        await ws_update_device(fake_hass, conn, {
            "id": 1, "type": "hair/device/update",
            "device_id": "dev-1", "device_type": "fan",
        })
        assert conn.send_error.call_args[0][1] == "invalid_format"
        # Refused before anything mutates -- same device_type it had.
        assert device.device_type == DeviceType.AC

    @pytest.mark.asyncio
    async def test_device_type_change_still_succeeds_on_flat_device(
        self, fake_hass
    ):
        device = _matrix_device()
        device.climate_matrix = False
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_update_device = AsyncMock(return_value=device)
        _wire_hass(fake_hass, manager=manager)
        conn = _make_connection()
        await ws_update_device(fake_hass, conn, {
            "id": 1, "type": "hair/device/update",
            "device_id": "dev-1", "device_type": "fan",
        })
        conn.send_error.assert_not_called()
        assert device.device_type == DeviceType.FAN
