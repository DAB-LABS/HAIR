"""Paste acceptance, slice 1: Tuya and Broadlink base64 in the paste box.

The paste box read only Pronto. A Zigbee2MQTT ``ir_code_to_send`` value
(Tuya base64) or a Broadlink base64 packet was refused with "Pronto codes
use hex digits only". ``pasted_code.coerce_pasted_code`` reads both with
the readers HAIR already had and hands every paste door Pronto.

Fixtures are real files already in the suite: the GH #108 UFO-R11 SmartIR
file (Tuya containers declared "Raw") and the SmartIR Broadlink adapter
fixtures. The reference conversion for each is what the SmartIR importer
itself produces, so a pasted code and an imported one are one code.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import pasted_code
from custom_components.hair.const import DOMAIN
from custom_components.hair.identity import canonical_byte_hash, canonical_fingerprint
from custom_components.hair.pasted_code import (
    CARRIER_NOTE,
    SOURCE_BROADLINK,
    SOURCE_PRONTO,
    SOURCE_TUYA,
    coerce_pasted_code,
)
from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    ws_clip_create_signal,
    ws_clip_validate_pronto,
    ws_command_update,
    ws_send_spacing_info,
    ws_tangle_apply,
    ws_tangle_pre_read,
    ws_tangle_test_send,
    ws_unknown_signal_edit_pronto,
    ws_unknown_signal_snap_preview,
)
from custom_components.hair.wig_adapters import _smartir_code_to_pronto

FIXTURES = Path(__file__).parent / "fixtures"


def _codes(path: str) -> list[str]:
    out: list[str] = []

    def walk(node):
        if isinstance(node, str) and len(node) > 16:
            out.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads((FIXTURES / path).read_text())["commands"])
    return out


TUYA = _codes("gh108/cecotec-forceclima-12650.json")
BROADLINK = (
    _codes("adapters/smartir_fan_1220.json")
    + _codes("adapters/smartir_media_player_1000.json")
)
# One of each, longer than one 76-character line so wrapping splits it.
TUYA_CODE = next(c for c in TUYA if len(c) > 76)
BROADLINK_CODE = next(c for c in BROADLINK if len(c) > 2 * 76)


def _wrap(code: str, width: int = 76) -> str:
    return "\n".join(code[i:i + width] for i in range(0, len(code), width))


def _tuya_ref(code: str) -> str:
    pronto, why = _smartir_code_to_pronto(code, "Raw")
    assert pronto and why is None
    return pronto


def _broadlink_ref(code: str) -> str:
    pronto, why = _smartir_code_to_pronto(code, "Base64")
    assert pronto and why is None
    return pronto


def _rf_packet(type_byte: int) -> str:
    payload = bytes([type_byte, 0, 24, 0]) + bytes(range(1, 25))
    return base64.b64encode(payload).decode()


SEVERAL = "The paste box takes one code"


# ---------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------


class TestConverts:
    @pytest.mark.parametrize("code", TUYA, ids=range(len(TUYA)))
    def test_every_tuya_fixture_matches_the_smartir_import(self, code):
        got = coerce_pasted_code(code)
        assert got.source == SOURCE_TUYA
        assert got.error is None
        assert got.pronto == _tuya_ref(code)
        assert validate_pronto(got.pronto).valid

    @pytest.mark.parametrize("code", BROADLINK, ids=range(len(BROADLINK)))
    def test_every_broadlink_fixture_matches_the_smartir_import(self, code):
        got = coerce_pasted_code(code)
        assert got.source == SOURCE_BROADLINK
        assert got.error is None
        assert got.pronto == _broadlink_ref(code)

    def test_quotes_whitespace_and_b64_prefix_are_stripped(self):
        for text in (
            f'  "{TUYA_CODE}"  ',
            f"'{TUYA_CODE}'\n",
            f"b64:{TUYA_CODE}",
            f"B64:{TUYA_CODE},",
        ):
            assert coerce_pasted_code(text).pronto == _tuya_ref(TUYA_CODE)
        assert (
            coerce_pasted_code(f"b64:{BROADLINK_CODE}").pronto
            == _broadlink_ref(BROADLINK_CODE)
        )

    def test_broadlink_without_padding_is_salvaged(self):
        stripped = BROADLINK_CODE.rstrip("=")
        assert coerce_pasted_code(stripped).pronto == _broadlink_ref(BROADLINK_CODE)

    def test_tuya_is_tried_first_and_never_reaches_the_broadlink_reader(self):
        with patch.object(
            pasted_code, "broadlink_b64_to_pronto",
            side_effect=AssertionError("Broadlink reader called"),
        ):
            for code in TUYA:
                assert coerce_pasted_code(code).source == SOURCE_TUYA

    def test_a_broadlink_packet_is_not_read_as_tuya(self):
        for code in BROADLINK:
            assert coerce_pasted_code(code).source == SOURCE_BROADLINK


class TestProntoDoesNotMove:
    @pytest.mark.parametrize("text", [
        "0000 006D 0002 0000 0010 0010 0010 0010",
        "  0000 006d 0002 0000\n0010 0010 0010 0010  ",
        '"0000 006D 0002 0000 0010 0010 0010 0010"',
        "0100 0073 0002 0000 0010 0010 0010 0010",
    ])
    def test_valid_pronto_comes_back_character_for_character(self, text):
        got = coerce_pasted_code(text)
        assert got.source == SOURCE_PRONTO
        assert got.error is None
        assert got.pronto == text
        assert validate_pronto(got.pronto).normalized == validate_pronto(text).normalized

    @pytest.mark.parametrize("text", [
        "", "   ", "0000 006D 0002", "not hex", "0200 006D 0001 0000 0010 0010",
    ])
    def test_invalid_pronto_gets_todays_error(self, text):
        got = coerce_pasted_code(text)
        assert got.source is None
        assert got.error is None
        assert got.pronto == text
        assert validate_pronto(got.pronto).errors == validate_pronto(text).errors


class TestNoFalseConversions:
    def test_pronto_without_spaces_is_not_base64(self):
        pronto = _tuya_ref(TUYA_CODE)
        squashed = pronto.replace(" ", "")
        got = coerce_pasted_code(squashed)
        assert got.source is None and got.error is None
        assert got.pronto == squashed
        assert validate_pronto(squashed).errors == [
            "Each Pronto value must be 4 hex digits (got "
            f"{squashed})."
        ]

    @pytest.mark.parametrize("text", [
        "hello", "Power", "PowerOnButtonCode", "TheQuickBrownFoxJumpsOverTheLazyDog",
        "abcd", "QUJD", "b64:", "b64:QUJD", "ir_code_to_send", "Volume Up",
        "AAAAAAAAAAAAAAAAAAAAAAAA", "////////////////////////",
    ])
    def test_words_and_short_tokens_do_not_convert(self, text):
        got = coerce_pasted_code(text)
        assert got.source is None
        assert got.error is None
        assert got.pronto == text

    # Found by searching random hex strings, random base64 and camel-case
    # runs of remote-button words: each of these IS read by one of the
    # file readers (asserted first), so it is the paste guard, not luck,
    # that keeps it from becoming a code.
    @pytest.mark.parametrize("text,reader", [
        ("Da5CF06afB11bfBb4f2A", "tuya"),
        ("AutoSwinggreenLight", "tuya"),
        ("AmpTvgreenvolumesource", "tuya"),
        ("Exitbrightchanneltimerselect", "tuya"),
        ("JhxUhg+C", "broadlink"),
    ])
    def test_text_a_file_reader_would_read_is_not_converted(self, text, reader):
        from custom_components.hair.tuya_ir import tuya_b64_to_pronto
        from custom_components.hair.wig_adapters import broadlink_b64_to_pronto

        read = tuya_b64_to_pronto if reader == "tuya" else broadlink_b64_to_pronto
        assert read(text), "precondition: the file reader accepts this text"
        got = coerce_pasted_code(text)
        assert got.source is None and got.error is None
        assert got.pronto == text

    # Each guard on its own, with the reader rigged to say yes, so that no
    # guard is only ever covered by another one catching the same text.
    def _rigged(self, monkeypatch):
        real = _tuya_ref(TUYA_CODE)
        monkeypatch.setattr(pasted_code, "tuya_b64_to_pronto", lambda _t: real)
        return real

    def test_guard_hex_only_token(self, monkeypatch):
        self._rigged(monkeypatch)
        assert coerce_pasted_code("0000006D00220000015B00AD").source is None
        assert coerce_pasted_code("DEADBEEFdeadbeef01234567").source is None

    def test_guard_short_token(self, monkeypatch):
        self._rigged(monkeypatch)
        assert coerce_pasted_code("QUJDREVGR0hJ").source is None  # 12 chars
        assert coerce_pasted_code("QUJDREVGR0hJSktM").source == SOURCE_TUYA  # 16

    def test_guard_too_few_durations(self, monkeypatch):
        few = "0000 006D 0004 0000 0016 0016 0016 0016 0016 0016 0016 0040"
        monkeypatch.setattr(pasted_code, "tuya_b64_to_pronto", lambda _t: few)
        assert coerce_pasted_code("QUJDREVGR0hJSktM").source is None

    def test_guard_durations_too_long(self, monkeypatch):
        # Ten pairs, every duration about 50 ms: plenty of them, none IR-like.
        slow = "0000 006D 000A 0000 " + " ".join(["07B5"] * 20)
        assert validate_pronto(slow).valid
        monkeypatch.setattr(pasted_code, "tuya_b64_to_pronto", lambda _t: slow)
        assert coerce_pasted_code("QUJDREVGR0hJSktM").source is None

    def test_garbage_base64_falls_through(self):
        junk = base64.b64encode(bytes(range(7, 107))).decode()
        got = coerce_pasted_code(junk)
        assert got.source is None and got.error is None

    def test_a_truncated_broadlink_packet_is_not_read(self):
        # The first wrapped line alone declares a payload it does not hold.
        first_line = BROADLINK_CODE[:76]
        assert coerce_pasted_code(first_line).source is None

    @pytest.mark.parametrize("type_byte,band", [(0xB2, "433 MHz"), (0xD7, "315 MHz")])
    def test_broadlink_rf_packet_gets_its_own_message(self, type_byte, band):
        got = coerce_pasted_code(_rf_packet(type_byte))
        assert got.source is None
        assert got.error is not None
        assert "Broadlink RF code" in got.error and band in got.error
        assert "infrared only" in got.error


class TestOneCode:
    @pytest.mark.parametrize("width", [76, 64])
    def test_wrapped_tuya_is_one_code(self, width):
        text = _wrap(TUYA_CODE, width)
        assert "\n" in text
        got = coerce_pasted_code(text)
        assert got.error is None
        assert got.source == SOURCE_TUYA
        assert got.pronto == _tuya_ref(TUYA_CODE)

    @pytest.mark.parametrize("width", [76, 64])
    def test_wrapped_broadlink_is_one_code(self, width):
        text = _wrap(BROADLINK_CODE, width)
        assert text.count("\n") >= 2
        got = coerce_pasted_code(text)
        assert got.error is None
        assert got.source == SOURCE_BROADLINK
        assert got.pronto == _broadlink_ref(BROADLINK_CODE)

    def test_every_fixture_survives_wrapping(self):
        for width in (64, 76):
            for code in TUYA:
                if len(code) > width:
                    assert coerce_pasted_code(_wrap(code, width)).pronto == _tuya_ref(code)
            for code in BROADLINK:
                if len(code) > width:
                    assert (
                        coerce_pasted_code(_wrap(code, width)).pronto
                        == _broadlink_ref(code)
                    )

    def test_two_tuya_codes_are_refused_with_the_upload_pointer(self):
        got = coerce_pasted_code(TUYA[0] + "\n" + TUYA[1])
        assert got.source is None
        assert SEVERAL in got.error
        assert "2 Tuya base64 codes" in got.error
        assert "Closet" in got.error

    def test_two_broadlink_codes_are_refused(self):
        got = coerce_pasted_code(BROADLINK[0] + " " + BROADLINK[1])
        assert "2 Broadlink base64 codes" in got.error

    def test_one_of_each_is_refused(self):
        got = coerce_pasted_code(TUYA_CODE + "\n" + BROADLINK_CODE)
        assert "2 Broadlink and Tuya base64 codes" in got.error

    def test_two_wrapped_codes_are_refused(self):
        text = _wrap(TUYA[0]) + "\n" + _wrap(TUYA[2])
        assert SEVERAL in coerce_pasted_code(text).error

    def test_two_broadlink_packets_run_together_are_not_one_code(self):
        # No separator at all: the first packet's length field ends it and
        # the second follows. That is not one code.
        got = coerce_pasted_code(BROADLINK[0].rstrip("=") + BROADLINK[1])
        assert got.source is None

    def test_two_pronto_codes_get_the_pointer(self):
        a = "0000 006D 0002 0000 0010 0010 0010 0010"
        b = "0000 006D 0002 0000 0040 0010 0010 0010"
        got = coerce_pasted_code(a + "\n" + b)
        assert SEVERAL in got.error
        assert "2 Pronto codes" in got.error
        # Before this slice the same paste failed on length; it still fails.
        assert not validate_pronto(a + "\n" + b).valid


# ---------------------------------------------------------------------------
# The doors
# ---------------------------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _monitor(hass):
    store = SignalStore(hass)
    store._loaded = True
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    return SignalMonitor(hass, store, hair_store)


def _wire(hass, *, monitor=None, manager=None):
    if manager is None:
        manager = MagicMock()
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager,
        "orchestrator": MagicMock(),
        "signal_monitor": monitor or MagicMock(),
        "trigger_manager": MagicMock(),
    }}


async def _validate(fake_hass, text):
    conn = _conn()
    await ws_clip_validate_pronto(
        fake_hass, conn, {"id": 1, "type": "hair/clip/validate-pronto", "pronto": text},
    )
    return conn.send_result.call_args[0][1]


class TestValidateDoor:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("code,source,ref", [
        (TUYA_CODE, SOURCE_TUYA, _tuya_ref),
        (BROADLINK_CODE, SOURCE_BROADLINK, _broadlink_ref),
    ], ids=["tuya", "broadlink"])
    async def test_base64_is_validated_as_its_pronto(self, fake_hass, code, source, ref):
        payload = await _validate(fake_hass, code)
        assert payload["valid"] is True
        assert payload["source_format"] == source
        assert payload["normalized"] == ref(code)
        assert payload["frequency_khz"] == validate_pronto(ref(code)).frequency_khz
        assert payload["burst_pair_count"] == validate_pronto(ref(code)).burst_pair_count
        assert payload["warnings"][0] == CARRIER_NOTE[source]
        assert "38 kHz assumed" in payload["warnings"][0]

    @pytest.mark.asyncio
    async def test_wrapped_paste_validates(self, fake_hass):
        payload = await _validate(fake_hass, _wrap(TUYA_CODE))
        assert payload["valid"] is True
        assert payload["source_format"] == SOURCE_TUYA

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text", [
        "0000 006D 0002 0000 0010 0010 0010 0010",
        "0000 0063 0002 0000 0010 0010 0010 0010",
        "0100 0073 0002 0000 0010 0010 0010 0010",
        "not hex",
        "",
    ])
    async def test_pronto_responses_are_unchanged(self, fake_hass, text):
        payload = await _validate(fake_hass, text)
        expected = validate_pronto(text)
        assert set(payload) == {
            "valid", "errors", "warnings", "frequency_khz",
            "burst_pair_count", "normalized", "recognized_protocol",
        }
        assert payload["valid"] == expected.valid
        assert payload["errors"] == expected.errors
        assert payload["warnings"] == expected.warnings
        assert payload["normalized"] == expected.normalized

    @pytest.mark.asyncio
    async def test_rf_and_several_codes_are_invalid_with_their_message(self, fake_hass):
        rf = await _validate(fake_hass, _rf_packet(0xB2))
        assert rf["valid"] is False
        assert "Broadlink RF code" in rf["errors"][0]
        assert "source_format" not in rf
        several = await _validate(fake_hass, TUYA[0] + "\n" + TUYA[1])
        assert several["valid"] is False
        assert SEVERAL in several["errors"][0]


class TestClipperDoor:
    async def _add(self, fake_hass, monitor, remote_id, text, msg_id=1):
        conn = _conn()
        await ws_clip_create_signal(fake_hass, conn, {
            "id": msg_id, "type": "hair/clip/create-signal",
            "device_id": remote_id, "pronto": text,
        })
        return conn

    @pytest.mark.asyncio
    @pytest.mark.parametrize("code,ref", [
        (TUYA_CODE, _tuya_ref), (BROADLINK_CODE, _broadlink_ref),
    ], ids=["tuya", "broadlink"])
    async def test_base64_is_stored_as_the_pronto_a_pronto_paste_stores(
        self, fake_hass, code, ref,
    ):
        monitor = _monitor(fake_hass)
        _wire(fake_hass, monitor=monitor)
        a = await monitor.create_manual_remote("From base64")
        b = await monitor.create_manual_remote("From Pronto")
        with patch.object(monitor._signal_store, "async_save", AsyncMock()):
            conn_a = await self._add(fake_hass, monitor, a.id, code)
            conn_b = await self._add(fake_hass, monitor, b.id, ref(code))
        conn_a.send_error.assert_not_called()
        conn_b.send_error.assert_not_called()
        sa = monitor._signal_store.get_device(a.id).signals[0]
        sb = monitor._signal_store.get_device(b.id).signals[0]
        assert sa.code == ref(code)
        assert code not in sa.code
        for attr in (
            "code", "fingerprint", "byte_hash", "decoded_protocol",
            "decoded_address", "decoded_command", "decoded_fingerprint",
            "frequency", "raw_timings",
        ):
            assert getattr(sa, attr) == getattr(sb, attr), attr
        assert sa.byte_hash == canonical_byte_hash(ref(code))
        assert sa.fingerprint == canonical_fingerprint("PRONTO", ref(code), [])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("first_is_base64", [True, False])
    @pytest.mark.parametrize("code,ref", [
        (TUYA_CODE, _tuya_ref), (BROADLINK_CODE, _broadlink_ref),
    ], ids=["tuya", "broadlink"])
    async def test_duplicate_guard_both_ways(self, fake_hass, code, ref, first_is_base64):
        monitor = _monitor(fake_hass)
        _wire(fake_hass, monitor=monitor)
        remote = await monitor.create_manual_remote("Clip")
        first, second = (code, ref(code)) if first_is_base64 else (ref(code), code)
        with patch.object(monitor._signal_store, "async_save", AsyncMock()):
            ok = await self._add(fake_hass, monitor, remote.id, first)
            dup = await self._add(fake_hass, monitor, remote.id, second, 2)
        ok.send_error.assert_not_called()
        dup.send_result.assert_not_called()
        assert dup.send_error.call_args[0][1] == "duplicate_signal"
        assert len(monitor._signal_store.get_device(remote.id).signals) == 1

    @pytest.mark.asyncio
    async def test_several_codes_and_rf_are_refused_before_anything_is_stored(
        self, fake_hass,
    ):
        monitor = _monitor(fake_hass)
        _wire(fake_hass, monitor=monitor)
        remote = await monitor.create_manual_remote("Clip")
        for text in (TUYA[0] + "\n" + TUYA[1], _rf_packet(0xD7)):
            conn = await self._add(fake_hass, monitor, remote.id, text)
            assert conn.send_error.call_args[0][1] == "invalid_pronto"
        assert monitor._signal_store.get_device(remote.id).signals == []


class TestSignalEditDoor:
    """The Sniffer and Clipper edit door: base64 in, and its own guard."""

    _A = "0000 006D 0002 0000 0010 0010 0010 0010"

    async def _edit(self, fake_hass, remote_id, signal_id, text):
        conn = _conn()
        await ws_unknown_signal_edit_pronto(fake_hass, conn, {
            "id": 3, "type": "hair/unknown/signal/edit-pronto",
            "device_id": remote_id, "signal_id": signal_id, "pronto": text,
        })
        return conn

    @pytest.mark.asyncio
    async def test_edit_to_base64_stores_pronto(self, fake_hass):
        monitor = _monitor(fake_hass)
        _wire(fake_hass, monitor=monitor)
        remote = await monitor.create_manual_remote("R")
        with patch.object(monitor._signal_store, "async_save", AsyncMock()):
            created = await monitor.create_manual_signal(remote.id, self._A)
            conn = await self._edit(
                fake_hass, remote.id, created["signal"]["id"], TUYA_CODE,
            )
        conn.send_error.assert_not_called()
        sig = remote.get_signal_by_id(created["signal"]["id"])
        assert sig.code == _tuya_ref(TUYA_CODE)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("held_is_base64", [True, False])
    async def test_collision_guard_both_ways(self, fake_hass, held_is_base64):
        monitor = _monitor(fake_hass)
        _wire(fake_hass, monitor=monitor)
        remote = await monitor.create_manual_remote("R")
        held = BROADLINK_CODE if held_is_base64 else _broadlink_ref(BROADLINK_CODE)
        edit_to = _broadlink_ref(BROADLINK_CODE) if held_is_base64 else BROADLINK_CODE
        with patch.object(monitor._signal_store, "async_save", AsyncMock()):
            conn = _conn()
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 4, "type": "hair/clip/create-signal",
                "device_id": remote.id, "pronto": held,
            })
            other = await monitor.create_manual_signal(remote.id, self._A)
            res = await self._edit(
                fake_hass, remote.id, other["signal"]["id"], edit_to,
            )
        assert res.send_error.call_args[0][1] == "duplicate_signal"


class TestCommandDoor:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("code,ref", [
        (TUYA_CODE, _tuya_ref), (BROADLINK_CODE, _broadlink_ref),
    ], ids=["tuya", "broadlink"])
    async def test_device_command_gets_the_pronto(self, fake_hass, code, ref):
        manager = MagicMock()
        manager.async_update_command = AsyncMock(
            return_value={"success": True, "command": {}, "triggers": {}, "mappings_updated": 0}
        )
        manager.get_device = MagicMock(return_value=None)
        _wire(fake_hass, manager=manager)
        for text in (code, _wrap(code), ref(code)):
            conn = _conn()
            await ws_command_update(fake_hass, conn, {
                "id": 5, "type": "hair/command/update",
                "device_id": "dev", "command_id": "cmd", "pronto": text,
            })
            assert manager.async_update_command.await_args.kwargs["pronto"] == ref(code)

    @pytest.mark.asyncio
    async def test_rename_only_is_untouched(self, fake_hass):
        manager = MagicMock()
        manager.async_update_command = AsyncMock(
            return_value={"success": True, "command": {}, "triggers": {}, "mappings_updated": 0}
        )
        manager.get_device = MagicMock(return_value=None)
        _wire(fake_hass, manager=manager)
        conn = _conn()
        await ws_command_update(fake_hass, conn, {
            "id": 6, "type": "hair/command/update",
            "device_id": "dev", "command_id": "cmd", "name": "Power",
        })
        assert manager.async_update_command.await_args.kwargs["pronto"] is None

    @pytest.mark.asyncio
    async def test_rf_refused(self, fake_hass):
        manager = MagicMock()
        manager.async_update_command = AsyncMock()
        _wire(fake_hass, manager=manager)
        conn = _conn()
        await ws_command_update(fake_hass, conn, {
            "id": 7, "type": "hair/command/update",
            "device_id": "dev", "command_id": "cmd", "pronto": _rf_packet(0xB2),
        })
        assert conn.send_error.call_args[0][1] == "invalid_pronto"
        manager.async_update_command.assert_not_awaited()


class TestReadOnlyAndTangleDoors:
    """Doors that take the box's text: each sees Pronto, stores nothing new."""

    @pytest.mark.asyncio
    async def test_snap_preview_reads_base64(self, fake_hass):
        conn = _conn()
        await ws_unknown_signal_snap_preview(fake_hass, conn, {
            "id": 8, "type": "hair/unknown/signal/snap-preview",
            "pronto": BROADLINK_CODE, "target_frequency": 38000,
        })
        conn.send_error.assert_not_called()
        conn.send_result.assert_called_once()

    def test_send_spacing_info_measures_the_converted_code(self, fake_hass):
        _wire(fake_hass)
        answers = []
        for text in (TUYA_CODE, _tuya_ref(TUYA_CODE)):
            conn = _conn()
            ws_send_spacing_info(fake_hass, conn, {
                "id": 9, "type": "hair/send_spacing_info",
                "pronto": text, "send_count": 2, "repeat_count": 0,
            })
            answers.append(conn.send_result.call_args[0][1])
        assert answers[0] == answers[1]
        assert answers[0]["block_ms"]

    def test_send_spacing_info_never_refuses(self, fake_hass):
        _wire(fake_hass)
        conn = _conn()
        ws_send_spacing_info(fake_hass, conn, {
            "id": 10, "type": "hair/send_spacing_info",
            "pronto": TUYA[0] + "\n" + TUYA[1], "send_count": 1,
        })
        conn.send_error.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler,extra", [
        (ws_tangle_apply, {"target": "t", "tested": True}),
        (ws_tangle_pre_read, {"target": "t"}),
    ])
    async def test_tangle_doors_see_pronto(self, fake_hass, handler, extra):
        msg = {"id": 11, "device_id": "dev", "pronto": TUYA_CODE, **extra}
        with patch(
            "custom_components.hair.websocket_api._device_and_matrix",
            AsyncMock(return_value=(None, None)),
        ):
            await handler(fake_hass, _conn(), msg)
        assert msg["pronto"] == _tuya_ref(TUYA_CODE)

    @pytest.mark.asyncio
    async def test_tangle_test_send_sends_pronto(self, fake_hass):
        manager = MagicMock()
        manager.async_test_send = AsyncMock(return_value={"infrared.x"})
        _wire(fake_hass, manager=manager)
        msg = {"id": 12, "device_id": "dev", "pronto": BROADLINK_CODE, "send_count": 1}
        await ws_tangle_test_send(fake_hass, _conn(), msg)
        assert manager.async_test_send.await_args.args[1] == _broadlink_ref(BROADLINK_CODE)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler", [ws_tangle_apply, ws_tangle_pre_read, ws_tangle_test_send])
    async def test_tangle_doors_refuse_rf(self, fake_hass, handler):
        conn = _conn()
        await handler(fake_hass, conn, {
            "id": 13, "device_id": "dev", "pronto": _rf_packet(0xD7),
            "target": "t", "tested": True, "send_count": 1,
        })
        assert conn.send_error.call_args[0][1] == "invalid_pronto"
