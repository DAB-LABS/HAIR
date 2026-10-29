"""Paste repairs: a refused code with a known kind of damage is offered a fix.

The first entry, ``broadlink_header``: some IR blasters write a
Broadlink IR packet whose length field counts the whole packet instead
of the payload, and leave off the trailing gap a learned packet ends
with. The readers take such a code for the first line of a wrapped one
and refuse it. The paste door offers to correct the length field; the
fix is applied only when the person asks for it, and the save doors
never apply it.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.pasted_code import (
    CARRIER_NOTE,
    PASTE_REPAIRS,
    SOURCE_BROADLINK,
    SOURCE_GLOBALCACHE,
    SOURCE_PRONTO,
    SOURCE_TASMOTA,
    coerce_pasted_code,
)
from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.protocol_decode import decode_to_fields
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.websocket_api import (
    ws_clip_create_signal,
    ws_clip_validate_pronto,
)
from custom_components.hair.wig_adapters import broadlink_b64_to_pronto

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None
_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)

REPAIR = "broadlink_header"
FIXTURES = Path(__file__).parent / "fixtures"
FRONTEND = Path(__file__).parents[1] / "frontend" / "src"

# An NEC press (address 0x00, command 0x41) and its repeat frame, as a
# blaster wrote it: 81 bytes, header 26 00 51 00 (the whole
# packet), no trailing gap.
HEADER_OFF = (
    "JgBRAAABGYsSEBIQEhASEBIQEhASEBIQEjMSMxIzEjMSMxIzEjMSMxIzEhASEBIQEhASEBIz"
    "EhASEBI0EjMSMxIzEjMSEBIzEgAE1gABGUUT"
)
# The same blaster's dialect, but the ticks do not read as any code (the
# packet declares 81 bytes and holds 80). Not repairable.
UNREADABLE = (
    "JgBRAABGYwREbESEhERERERERIRERESETQRNBE0ETQRNBE0ETQRNBESERERNBE0EREREhERE"
    "TQRNBE0ER5SERE0ETQRNBESEQAE2AABGEYT"
)
GAP = b"\x00\x0d\x05"


def _packet(token: str) -> bytes:
    return base64.b64decode(token + "=" * (-len(token) % 4))


def _b64(packet: bytes) -> str:
    return base64.b64encode(packet).decode("ascii")


def _standard(payload: bytes, *, pad: bool = False) -> bytes:
    """A packet with a standard header: the length field counts the
    payload only."""
    packet = bytes([0x26, 0x00]) + len(payload).to_bytes(2, "little") + payload
    if pad:
        packet += b"\x00" * (-len(packet) % 16)
    return packet


def _whole_length(payload: bytes) -> bytes:
    """A packet whose length field counts the whole packet."""
    return bytes([0x26, 0x00]) + (len(payload) + 4).to_bytes(2, "little") + payload


PAYLOAD = _packet(HEADER_OFF)[4:]


def _first_line(code: str, width: int) -> str:
    return code[:width]


def _broadlink_fixtures() -> list[str]:
    out: list[str] = []

    def walk(node):
        if isinstance(node, str) and node.startswith("Jg"):
            out.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for name in ("smartir_fan_1220.json", "smartir_media_player_1000.json"):
        walk(json.loads((FIXTURES / "adapters" / name).read_text())["commands"])
    return out


STANDARD_CODES = _broadlink_fixtures()
STANDARD_CODE = next(c for c in STANDARD_CODES if len(c) > 2 * 76)


class TestTheList:
    def test_one_entry_with_a_unique_id(self):
        ids = [repair.id for repair in PASTE_REPAIRS]
        assert ids == [REPAIR]
        assert len(set(ids)) == len(ids)

    def test_every_repair_has_its_offer_text_in_every_locale(self):
        for path in sorted((FRONTEND / "locales").glob("*.json")):
            strings = json.loads(path.read_text(encoding="utf-8"))
            for key in ("editor.repair.apply", "editor.converted_repaired"):
                assert strings.get(key), (path.name, key)
            for repair in PASTE_REPAIRS:
                assert strings.get(f"editor.repair.{repair.id}"), (path.name, repair.id)

    def test_no_em_dash_in_the_new_strings(self):
        for path in sorted((FRONTEND / "locales").glob("*.json")):
            strings = json.loads(path.read_text(encoding="utf-8"))
            for key, value in strings.items():
                if key.startswith("editor.repair.") or key == "editor.converted_repaired":
                    assert "\u2014" not in value, (path.name, key)


class TestOffer:
    def test_refused_with_an_offer(self):
        got = coerce_pasted_code(HEADER_OFF)
        assert got.source is None
        assert got.pronto == HEADER_OFF
        assert got.error is None
        assert got.repair_offer == REPAIR
        assert got.repaired is None
        # The refusal stays the Pronto validator's own.
        assert validate_pronto(got.pronto).valid is False

    @pytest.mark.parametrize("width", [64, 76])
    def test_a_wrapped_copy_is_offered_too(self, width):
        text = "\n".join(
            HEADER_OFF[i:i + width] for i in range(0, len(HEADER_OFF), width)
        )
        assert coerce_pasted_code(text).repair_offer == REPAIR
        fixed = coerce_pasted_code(text, apply_repair=REPAIR)
        assert fixed.repaired == REPAIR
        assert fixed.pronto == coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR).pronto

    def test_quoted_or_prefixed_copies_are_offered(self):
        for text in (f'"{HEADER_OFF}"', f"b64:{HEADER_OFF}", f"  {HEADER_OFF}\n"):
            assert coerce_pasted_code(text).repair_offer == REPAIR


class TestApply:
    def test_applied_on_request(self):
        got = coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR)
        assert got.source == SOURCE_BROADLINK
        assert got.repaired == REPAIR
        assert got.repair_offer is None
        assert got.error is None
        assert validate_pronto(got.pronto).valid is True

    def test_the_fix_is_the_length_field_and_nothing_else(self):
        (repair,) = PASTE_REPAIRS
        assert repair.detect(HEADER_OFF)
        original = _packet(HEADER_OFF)
        fixed = _packet(repair.fix(HEADER_OFF))
        assert len(fixed) == len(original) == 81
        assert fixed[2] | (fixed[3] << 8) == 77
        assert fixed[:2] == original[:2]
        assert fixed[4:] == original[4:]

    def test_the_repaired_code_is_what_the_broadlink_reader_makes_of_the_fixed_packet(self):
        (repair,) = PASTE_REPAIRS
        got = coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR)
        assert got.pronto == broadlink_b64_to_pronto(repair.fix(HEADER_OFF))
        # Every tick read, ending on a mark: 71 durations, nothing dropped.
        assert len(ProntoCommand(got.pronto).get_raw_timings()) == 71

    @_needs_library
    def test_the_repaired_code_decodes_as_the_press(self):
        got = coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR)
        protocol, address, command, _ = decode_to_fields(
            ProntoCommand(got.pronto).get_raw_timings()
        )
        assert protocol == "NEC"
        # Address 0x00 with its inverse 0xFF, read as one 16-bit field.
        assert (address, command) == (0xFF00, 0x41)

    def test_apply_on_text_that_does_not_match_is_the_plain_refusal(self):
        for text in (UNREADABLE, "not a code at all", "0000 006D 0002"):
            plain = coerce_pasted_code(text)
            asked = coerce_pasted_code(text, apply_repair=REPAIR)
            assert asked == plain
            assert asked.repaired is None
            assert asked.repair_offer is None

    def test_an_unknown_repair_id_is_ignored(self):
        got = coerce_pasted_code(HEADER_OFF, apply_repair="no_such_repair")
        assert got == coerce_pasted_code(HEADER_OFF)
        assert got.repaired is None
        assert got.repair_offer == REPAIR

    def test_a_readable_code_is_not_touched_by_a_request(self):
        plain = coerce_pasted_code(STANDARD_CODE)
        asked = coerce_pasted_code(STANDARD_CODE, apply_repair=REPAIR)
        assert asked == plain
        assert asked.source == SOURCE_BROADLINK
        assert asked.repaired is None

    def test_pronto_does_not_move(self):
        pronto = coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR).pronto
        got = coerce_pasted_code(pronto, apply_repair=REPAIR)
        assert got.pronto == pronto
        assert got.source == SOURCE_PRONTO
        assert got.repaired is None and got.repair_offer is None


class TestNoOffer:
    @pytest.mark.parametrize("code", STANDARD_CODES, ids=range(len(STANDARD_CODES)))
    def test_a_standard_code_reads_with_no_offer(self, code):
        got = coerce_pasted_code(code)
        assert got.source == SOURCE_BROADLINK
        assert got.repair_offer is None and got.repaired is None

    @pytest.mark.parametrize("width", [64, 76])
    def test_the_first_line_of_a_wrapped_standard_code(self, width):
        got = coerce_pasted_code(_first_line(STANDARD_CODE, width))
        assert got.source is None
        assert got.repair_offer is None

    def test_the_unreadable_blaster_code(self):
        got = coerce_pasted_code(UNREADABLE)
        assert got.source is None
        assert got.repair_offer is None

    def test_whole_length_header_that_ends_with_the_trailing_gap(self):
        # Ends with the standard gap: whatever is wrong, it is not this.
        # The second payload keeps the tick count odd, so only the gap
        # check refuses it.
        for payload in (PAYLOAD + GAP, PAYLOAD[:-1] + GAP):
            packet = _whole_length(payload)
            assert coerce_pasted_code(_b64(packet)).repair_offer is None

    def test_whole_length_header_that_ends_on_a_space(self):
        packet = _whole_length(PAYLOAD[:-1])  # drop the last mark
        assert coerce_pasted_code(_b64(packet)).repair_offer is None

    def test_whole_length_header_with_a_value_cut_off(self):
        packet = _whole_length(PAYLOAD + b"\x00\x01")
        assert coerce_pasted_code(_b64(packet)).repair_offer is None

    def test_a_length_field_one_off_is_not_this_repair(self):
        for delta in (-1, 1):
            packet = bytearray(_whole_length(PAYLOAD))
            packet[2:4] = (len(packet) + delta).to_bytes(2, "little")
            assert coerce_pasted_code(_b64(bytes(packet))).repair_offer is None

    def test_not_infrared_after_the_fix(self):
        # Shape matches, but a few long durations are not a burst of IR.
        payload = bytes([0x00, 0x7F, 0xFF] * 4 + [0x10])
        assert coerce_pasted_code(_b64(_whole_length(payload))).repair_offer is None

    def test_rf_type_byte(self):
        packet = bytearray(_whole_length(PAYLOAD))
        packet[0] = 0xB2
        assert coerce_pasted_code(_b64(bytes(packet))).repair_offer is None

    def test_several_codes_are_never_offered(self):
        for text in (
            HEADER_OFF + " " + HEADER_OFF,
            HEADER_OFF + "\n" + STANDARD_CODE,
            STANDARD_CODE + "\n" + HEADER_OFF,
        ):
            for repair in (None, REPAIR):
                got = coerce_pasted_code(text, apply_repair=repair)
                assert got.repair_offer is None, text
                assert got.repaired is None, text


class TestEveryReaderFirst:
    """A repair is considered only after every reader has refused the
    paste: the text readers (Global Cache sendir, Tasmota), then Tuya,
    then Broadlink."""

    def test_the_blaster_code_is_no_text_code(self):
        from custom_components.hair.pasted_code import _read_text_code

        assert _read_text_code(HEADER_OFF) is None

    @pytest.mark.parametrize("text", [
        "sendir,1:1,1,38000,1,1",
        'IRsend {"Protocol":"NOPE","Bits":32,"Data":"0x1"}',
    ], ids=["sendir", "tasmota"])
    def test_a_refused_text_code_keeps_its_own_error_and_gets_no_offer(self, text):
        for repair in (None, REPAIR):
            got = coerce_pasted_code(text, apply_repair=repair)
            assert got.error
            assert got.repair_offer is None and got.repaired is None

    @pytest.mark.parametrize("text,source", [
        ("sendir,1:1,1,38000,1,1,341,170,21,21,21,64,21,1517", SOURCE_GLOBALCACHE),
        ('IRsend {"Protocol":"NEC","Bits":32,"Data":"0x20DF10EF"}', SOURCE_TASMOTA),
    ], ids=["sendir", "tasmota"])
    def test_a_read_text_code_is_not_touched_by_a_request(self, text, source):
        plain = coerce_pasted_code(text)
        asked = coerce_pasted_code(text, apply_repair=REPAIR)
        assert asked == plain
        assert asked.source == source and asked.repaired is None

    def test_repairs_are_tried_after_the_readers(self, monkeypatch):
        from custom_components.hair import pasted_code

        calls = []
        real = pasted_code._convert

        def spy(token):
            calls.append("convert")
            return real(token)

        monkeypatch.setattr(pasted_code, "_convert", spy)
        (repair,) = PASTE_REPAIRS
        original = repair.detect

        def detect(token):
            calls.append("detect")
            return original(token)

        monkeypatch.setattr(
            pasted_code, "PASTE_REPAIRS",
            (pasted_code.PasteRepair(repair.id, detect, repair.fix),),
        )
        assert coerce_pasted_code(HEADER_OFF).repair_offer == REPAIR
        assert calls[0] == "convert"
        assert "detect" in calls


class TestKnownLimit:
    """Which cut-short codes can match the shape. A decision, pinned.

    A code cut short by exactly its last four bytes declares the length
    of what is left, so its length field counts the whole packet. A
    standard learned packet ends with the trailing gap (00 0d 05), and
    losing four bytes always takes the gap and part of the mark before
    it: the ticks end on a space or a value is cut in half, and no
    offer is made. That holds at every length, padded or not.

    A packet written with no trailing gap (it ends on its last mark, as
    some encoders write them) and cut by four whole one-byte ticks DOES
    match. The person is asked first, and the code it reads as is the
    original without its last four durations.
    """

    def test_a_standard_learned_packet_cut_short_is_never_offered(self):
        for pad in (False, True):
            packet = _standard(PAYLOAD + GAP, pad=pad)
            assert coerce_pasted_code(_b64(packet)).source == SOURCE_BROADLINK
            for n in range(6, len(packet)):
                cut = _b64(packet[:n])
                assert coerce_pasted_code(cut).repair_offer is None, n
            text = _b64(packet)
            for n in range(16, len(text)):
                assert coerce_pasted_code(text[:n]).repair_offer is None, n

    @pytest.mark.parametrize("code", STANDARD_CODES, ids=range(len(STANDARD_CODES)))
    def test_fixture_codes_cut_short_are_never_offered(self, code):
        packet = _packet(code)
        assert packet[4:4 + (packet[2] | packet[3] << 8)].endswith(GAP)
        for n in range(6, len(packet)):
            assert coerce_pasted_code(_b64(packet[:n])).repair_offer is None, n

    def test_a_gapless_packet_missing_four_whole_ticks_is_offered(self):
        # The first NEC frame alone, ending on its stop mark, no gap.
        frame = PAYLOAD[: PAYLOAD.index(b"\x00\x04\xd6")]
        packet = _standard(frame)
        assert coerce_pasted_code(_b64(packet)).source == SOURCE_BROADLINK
        cut = packet[:-4]
        assert all(b != 0 for b in packet[-4:])  # four one-byte ticks
        got = coerce_pasted_code(_b64(cut))
        assert got.repair_offer == REPAIR
        whole = ProntoCommand(
            coerce_pasted_code(_b64(packet)).pronto
        ).get_raw_timings()
        short = ProntoCommand(
            coerce_pasted_code(_b64(cut), apply_repair=REPAIR).pronto
        ).get_raw_timings()
        assert short == whole[:-4]


# -- the doors ---------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


async def _validate(fake_hass, text, repair=None):
    conn = _conn()
    msg = {"id": 1, "type": "hair/clip/validate-pronto", "pronto": text}
    if repair is not None:
        msg["repair"] = repair
    await ws_clip_validate_pronto(fake_hass, conn, msg)
    return conn.send_result.call_args[0][1]


class TestValidateDoor:
    @pytest.mark.asyncio
    async def test_offer_in_the_response(self, fake_hass):
        payload = await _validate(fake_hass, HEADER_OFF)
        assert payload["valid"] is False
        assert payload["repair_offer"] == REPAIR
        assert "repaired" not in payload
        assert "source_format" not in payload
        assert payload["errors"] == validate_pronto(HEADER_OFF).errors

    @pytest.mark.asyncio
    async def test_repair_passes_through_and_is_reported(self, fake_hass):
        payload = await _validate(fake_hass, HEADER_OFF, REPAIR)
        pronto = coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR).pronto
        assert payload["valid"] is True
        assert payload["source_format"] == SOURCE_BROADLINK
        assert payload["repaired"] == REPAIR
        assert "repair_offer" not in payload
        assert payload["normalized"] == validate_pronto(pronto).normalized
        assert payload["warnings"][0] == CARRIER_NOTE[SOURCE_BROADLINK]

    @pytest.mark.asyncio
    async def test_other_responses_carry_no_repair_keys(self, fake_hass):
        pronto = coerce_pasted_code(HEADER_OFF, apply_repair=REPAIR).pronto
        for text in (pronto, STANDARD_CODE, UNREADABLE, "nonsense"):
            for repair in (None, REPAIR):
                payload = await _validate(fake_hass, text, repair)
                assert "repair_offer" not in payload, text
                assert "repaired" not in payload, text


def _monitor(hass):
    store = SignalStore(hass)
    store._loaded = True
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    return SignalMonitor(hass, store, hair_store)


class TestSaveDoorsNeverRepair:
    @pytest.mark.asyncio
    async def test_the_clipper_refuses_the_code_as_pasted(self, fake_hass):
        monitor = _monitor(fake_hass)
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": MagicMock(),
            "signal_monitor": monitor,
            "trigger_manager": MagicMock(),
        }}
        with patch.object(monitor._signal_store, "async_save", AsyncMock()):
            remote = await monitor.create_manual_remote("Clip")
            conn = _conn()
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 1, "type": "hair/clip/create-signal",
                "device_id": remote.id, "pronto": HEADER_OFF,
            })
        conn.send_result.assert_not_called()
        assert conn.send_error.called
        assert monitor._signal_store.get_device(remote.id).signals == []

    def test_the_save_helper_calls_without_a_repair(self):
        source = (Path(__file__).parents[1] / "websocket_api.py").read_text()
        helper = source[source.index("def _coerce_paste("):]
        helper = helper[: helper.index("\n\n\n")]
        assert "coerce_pasted_code(text)" in helper
        assert "apply_repair" not in helper
        assert source.count("apply_repair=") == 1


class TestEditorSource:
    """The editor's half, read from the source (one component serves
    every paste box)."""

    SRC = (FRONTEND / "ir-signal-editor.ts").read_text()

    def test_offer_is_inline_with_one_button(self):
        assert "v.repair_offer ? this._renderRepairOffer(v.repair_offer)" in self.SRC
        block = self.SRC[self.SRC.index("private _renderRepairOffer("):]
        block = block[: block.index("\n    }\n")]
        assert "t(`editor.repair.${id}`)" in block
        assert 't("editor.repair.apply")' in block
        assert block.count("<button") == 1
        assert "ha-dialog" not in block

    def test_button_asks_again_with_the_repair_id(self):
        assert "this.api.validatePronto(sent, repair)" in self.SRC
        assert "await this._validate(id)" in self.SRC

    def test_repaired_note_and_its_reset_points(self):
        assert '"editor.converted_repaired"' in self.SRC
        assert "this._repaired = v.repaired ?? null;" in self.SRC
        resets = re.findall(
            r"this\._convertedFrom = null;\n\s+this\._repaired = null;", self.SRC
        )
        assert len(resets) == 2

    def test_api_sends_repair_only_when_given(self):
        api = (FRONTEND / "api.ts").read_text()
        assert "...(repair ? { repair } : {})" in api

    def test_plucker_dialog_untouched(self):
        pluck = (FRONTEND / "ir-pluck-signal-dialog.ts").read_text()
        assert "repair" not in pluck
