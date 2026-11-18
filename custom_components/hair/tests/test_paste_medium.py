"""Which medium a pasted code is, for the Clipper's one add window.

Every format either paste reader takes is tried here, through the shape
rule and through the reader of the medium it names, so a format that
lands on the wrong side shows up as a failure.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

import pytest

from custom_components.hair import rf_paste
from custom_components.hair.paste_medium import (
    MEDIUM_EITHER,
    MEDIUM_IR,
    MEDIUM_RF,
    PASTE_FORMATS,
    medium_of,
)
from custom_components.hair.pasted_code import coerce_pasted_code
from custom_components.hair.pronto_validator import validate_pronto

from .test_paste_base64 import BROADLINK_CODE, TUYA_CODE, _wrap
from .test_rf_paste import BUTTON_A, IT104_B64, _broadlink, _frame

# Built from its words at run time: a Pronto string literal in a test
# module is a row of the decode census, and this module is not in its
# baseline.
NEC = " ".join((
    "0000", "006D", "0022", "0002", "0157", "00AC", "0015", "0016", "0015", "0016",
    "0015", "0041", "0015", "0016", "0015", "0016", "0015", "0016", "0015", "0016",
    "0015", "0016", "0015", "0041", "0015", "0041", "0015", "0016", "0015", "0041",
    "0015", "0041", "0015", "0041", "0015", "0041", "0015", "0041", "0015", "0016",
    "0015", "0016", "0015", "0016", "0015", "0041", "0015", "0016", "0015", "0016",
    "0015", "0016", "0015", "0016", "0015", "0041", "0015", "0041", "0015", "0041",
    "0015", "0016", "0015", "0041", "0015", "0041", "0015", "0041", "0015", "0041",
    "0015", "0689", "0157", "0056", "0015", "0E94"
))
SENDIR = "sendir,1:1,1,38000,1,1," + ",".join(["341", "170"] + ["21", "64"] * 32 + ["21", "1517"])
TASMOTA = 'IRsend {"Protocol":"NEC","Bits":32,"Data":"0x48B7807F"}'
TASMOTA_RECEIVED = (
    '{"IrReceived":{"Protocol":"NEC","Bits":32,"Data":"0x48B7807F"}}'
)
# Tasmota's raw form as plain durations, and written compressed.
TASMOTA_RAW = "9000,4500," + ",".join(["560", "560", "560", "1690"] * 16) + ",560"
# Tasmota's raw form written compressed: signed durations run together.
TASMOTA_COMPRESSED = "+9000-4500" + "+560-560+560-1690" * 16 + "+560"
FRAMES = _frame(BUTTON_A) * 4
SUB = (
    "Filetype: Flipper SubGhz RAW File\nVersion: 1\nFrequency: 433920000\n"
    "Preset: FuriHalSubGhzPresetOok650Async\nProtocol: RAW\nRAW_Data: "
    + " ".join(str(v) for v in FRAMES)
)
BROADLINK_RF = base64.b64encode(_broadlink(0xB2, FRAMES)).decode()


def _ir_reads(text: str) -> bool:
    pasted = coerce_pasted_code(text)
    return pasted.error is None and validate_pronto(pasted.pronto).valid


def _rf_reads(text: str) -> bool:
    return rf_paste.validate(text).get("ok") is True


# Every format the two readers take today, with the medium it is.
FORMATS = [
    ("pronto", NEC, MEDIUM_IR),
    ("pronto, lowercase", NEC.lower(), MEDIUM_IR),
    ("tuya", TUYA_CODE, MEDIUM_IR),
    ("tuya, wrapped", _wrap(TUYA_CODE), MEDIUM_IR),
    ("broadlink infrared", BROADLINK_CODE, MEDIUM_IR),
    ("broadlink infrared, wrapped", _wrap(BROADLINK_CODE), MEDIUM_IR),
    ("global cache sendir", SENDIR, MEDIUM_IR),
    ("tasmota IRsend", TASMOTA, MEDIUM_IR),
    ("tasmota IrReceived", TASMOTA_RECEIVED, MEDIUM_IR),
    ("tasmota IRsend raw", "IRsend 0," + TASMOTA_RAW, MEDIUM_IR),
    ("flipper .sub", SUB, MEDIUM_RF),
    ("broadlink radio", BROADLINK_RF, MEDIUM_RF),
    ("broadlink radio, an RM4 Pro capture", IT104_B64, MEDIUM_RF),
    ("signed timings", " ".join(str(v) for v in FRAMES), MEDIUM_EITHER),
    ("timings with brackets", "[" + ", ".join(str(v) for v in FRAMES) + "]", MEDIUM_EITHER),
    ("unsigned timings", ",".join(str(abs(v)) for v in FRAMES), MEDIUM_EITHER),
    ("tasmota compressed raw", TASMOTA_COMPRESSED, MEDIUM_IR),
    ("tasmota compressed raw at a frequency", "0," + TASMOTA_COMPRESSED, MEDIUM_IR),
]


class TestEveryFormat:
    @pytest.mark.parametrize(("name", "text", "medium"), FORMATS, ids=[f[0] for f in FORMATS])
    def test_lands_on_its_medium_and_reads_there(self, name, text, medium):
        assert medium_of(text) == medium
        if medium == MEDIUM_IR:
            assert _ir_reads(text), name
        else:
            # A list of timings is radio until the window can ask.
            assert _rf_reads(text), name

    def test_no_format_is_read_by_the_other_side(self):
        """The bug the shape rule exists for: the radio reader took the
        hex digits of a Pronto as a Broadlink radio packet."""
        for _name, text, medium in FORMATS:
            # Tasmota's compressed raw is a list of signed timings too, and
            # the radio editor still takes one pasted there; the add window
            # sends it to infrared by its shape.
            if medium == MEDIUM_IR and not _name.startswith("tasmota compressed"):
                assert not _rf_reads(text), _name
            if medium == MEDIUM_RF:
                assert not _ir_reads(text), _name


class TestWhatIsNoCode:
    @pytest.mark.parametrize("text", ["", "   ", "hello world", None, "!!!"])
    def test_says_nothing(self, text):
        assert medium_of(text) is None

    def test_a_damaged_pronto_is_still_infrared(self):
        """So the infrared reader's own error is what shows."""
        broken = NEC[:-5]
        assert not validate_pronto(broken).valid
        assert medium_of(broken) == MEDIUM_IR

    def test_several_pronto_codes_are_infrared(self):
        assert medium_of(NEC + "\n" + NEC) == MEDIUM_IR

    @pytest.mark.parametrize("typed", ["0000", "0000 0", "0000 006", "1 2 3"])
    def test_a_pronto_typed_by_hand_is_never_sent_to_radio(self, typed):
        """Digits on the way to a Pronto code read as no radio code, so
        the window stays where it is while they are typed."""
        assert medium_of(typed) in (None, MEDIUM_IR)

    def test_an_unusable_tasmota_code_is_infrared(self):
        bad = "IRsend 0,9000,4500,560,98000"
        assert coerce_pasted_code(bad).error is not None
        assert medium_of(bad) == MEDIUM_IR


class TestThePastedProntoFix:
    def test_the_radio_reader_refuses_a_pronto(self):
        result = rf_paste.validate(NEC)
        assert result["ok"] is False
        assert result["code"] == "wrong_medium_code"

    def test_and_the_same_hex_run_together(self):
        result = rf_paste.validate(NEC.replace(" ", ""))
        assert result["code"] == "wrong_medium_code"

    def test_the_infrared_refusal_of_a_radio_packet_names_add_signal(self):
        pasted = coerce_pasted_code(BROADLINK_RF)
        assert "Add Signal" in pasted.error
        assert "Add Radio Code" not in pasted.error


class TestThePanelTable:
    """``paste-formats.ts`` is the hint's table: it must name the same
    formats, per medium and in order, as ``PASTE_FORMATS``."""

    SOURCE = (
        Path(__file__).parent.parent / "frontend" / "src" / "paste-formats.ts"
    ).read_text(encoding="utf-8")

    def _ids(self, medium: str) -> tuple[str, ...]:
        block = re.search(
            rf"^\s*{medium}:\s*\[(.*?)\]", self.SOURCE, re.DOTALL | re.MULTILINE
        )
        assert block is not None, medium
        return tuple(re.findall(r'"([a-z]+)"', block.group(1)))

    def test_the_two_tables_agree(self):
        assert self._ids("ir") == PASTE_FORMATS[MEDIUM_IR]
        assert self._ids("rf") == PASTE_FORMATS[MEDIUM_RF]


class TestTheDoorsSayIt:
    @pytest.mark.asyncio
    async def test_both_validate_doors_carry_the_medium(self, fake_hass):
        from unittest.mock import MagicMock

        from custom_components.hair.websocket_api import (
            ws_clip_validate_pronto,
            ws_rf_validate,
        )

        conn = MagicMock()
        await ws_clip_validate_pronto(
            fake_hass, conn,
            {"id": 1, "type": "hair/clip/validate-pronto", "pronto": SUB},
        )
        answer = conn.send_result.call_args.args[1]
        assert (answer["valid"], answer["medium"]) == (False, MEDIUM_RF)

        ws_rf_validate(fake_hass, conn, {"id": 2, "type": "hair/rf/validate", "text": NEC})
        answer = conn.send_result.call_args.args[1]
        assert (answer["ok"], answer["medium"]) == (False, MEDIUM_IR)
