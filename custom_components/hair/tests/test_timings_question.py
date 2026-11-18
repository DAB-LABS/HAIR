"""Raw timings in the Clipper's add window: infrared or radio.

A bare list of numbers says nothing about its medium (``medium`` is
``either``). The window shows HAIR's guess first (``guess`` on both
validate doors, ``paste_medium.timings_guess``) and two chips to switch
it. Infrared from raw timings is read only when asked (``as_infrared``),
at 38 kHz.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.paste_medium import (
    MEDIUM_EITHER,
    MEDIUM_IR,
    MEDIUM_RF,
    medium_of,
    timings_guess,
)
from custom_components.hair.pasted_code import (
    CARRIER_NOTE,
    SOURCE_TIMINGS,
    coerce_pasted_code,
)
from custom_components.hair.pronto_validator import validate_pronto

from .test_paste_medium import FORMATS, FRAMES, NEC


def _signed(values) -> str:
    return " ".join(str(v) for v in values)


# NEC as an ESPHome dump prints it: signed microseconds.
NEC_TIMINGS = _signed(ProntoCommand(NEC).get_raw_timings())
# The same, unsigned and comma separated, as other tools copy it.
NEC_UNSIGNED = ",".join(str(abs(v)) for v in ProntoCommand(NEC).get_raw_timings())
# Samsung32: a 4500/4500 header, then 32 bits.
SAMSUNG_TIMINGS = _signed(
    [4500, -4500]
    + [v for bit in "11100000111000000100000010111111"
       for v in ((560, -1690) if bit == "1" else (560, -560))]
    + [560, -46000]
)
# An EV1527 radio frame, four times.
RADIO_TIMINGS = _signed(FRAMES)
# Timings no decoder names.
NOTHING_TIMINGS = _signed([v * (1 if i % 2 == 0 else -1)
                           for i, v in enumerate([700, 900, 1300] * 12)])


class TestTheGuess:
    @pytest.mark.parametrize("text", [NEC_TIMINGS, NEC_UNSIGNED, SAMSUNG_TIMINGS],
                             ids=["nec", "nec unsigned", "samsung"])
    def test_an_infrared_dump_guesses_infrared(self, text):
        assert medium_of(text) == MEDIUM_EITHER
        assert timings_guess(text) == MEDIUM_IR

    @pytest.mark.parametrize("text", [RADIO_TIMINGS, NOTHING_TIMINGS],
                             ids=["ev1527", "nothing decodes"])
    def test_anything_else_guesses_radio(self, text):
        assert medium_of(text) == MEDIUM_EITHER
        assert timings_guess(text) == MEDIUM_RF

    @pytest.mark.parametrize("text", ["", None, "hello", "0000"])
    def test_text_that_is_no_timings_guesses_radio(self, text):
        assert timings_guess(text) == MEDIUM_RF


class TestInfraredFromTimings:
    def test_only_when_asked(self):
        assert coerce_pasted_code(NEC_TIMINGS).source is None

    def test_read_at_38_khz_with_the_note(self):
        pasted = coerce_pasted_code(NEC_TIMINGS, as_infrared=True)
        assert pasted.source == SOURCE_TIMINGS
        result = validate_pronto(pasted.pronto)
        assert result.valid
        assert round(result.frequency_khz) == 38
        assert "raw timings" in CARRIER_NOTE[SOURCE_TIMINGS]
        assert "38 kHz assumed" in CARRIER_NOTE[SOURCE_TIMINGS]

    def test_the_same_code_as_the_pronto(self):
        """NEC read from its timings decodes as the NEC it came from."""
        from custom_components.hair.protocol_decode import decode_to_fields

        pasted = coerce_pasted_code(NEC_TIMINGS, as_infrared=True)
        ours = decode_to_fields(ProntoCommand(pasted.pronto).get_raw_timings())
        theirs = decode_to_fields(ProntoCommand(NEC).get_raw_timings())
        assert ours == theirs
        assert ours[0] is not None

    def test_every_other_format_reads_as_before(self):
        for name, text, _medium in FORMATS:
            plain = coerce_pasted_code(text)
            asked = coerce_pasted_code(text, as_infrared=True)
            if plain.source is not None or plain.error is not None:
                assert asked == plain, name


class TestTheDoors:
    @pytest.mark.asyncio
    async def test_both_doors_carry_the_guess_for_timings_only(self, fake_hass):
        from custom_components.hair.websocket_api import (
            ws_clip_validate_pronto,
            ws_rf_validate,
        )

        conn = MagicMock()
        await ws_clip_validate_pronto(
            fake_hass, conn,
            {"id": 1, "type": "hair/clip/validate-pronto", "pronto": NEC_TIMINGS},
        )
        answer = conn.send_result.call_args.args[1]
        assert (answer["medium"], answer["guess"]) == (MEDIUM_EITHER, MEDIUM_IR)

        ws_rf_validate(fake_hass, conn, {"id": 2, "type": "hair/rf/validate",
                                         "text": RADIO_TIMINGS})
        answer = conn.send_result.call_args.args[1]
        assert (answer["medium"], answer["guess"]) == (MEDIUM_EITHER, MEDIUM_RF)

        ws_rf_validate(fake_hass, conn, {"id": 3, "type": "hair/rf/validate",
                                         "text": NEC})
        assert "guess" not in conn.send_result.call_args.args[1]

    @pytest.mark.asyncio
    async def test_the_infrared_door_reads_timings_when_asked(self, fake_hass):
        from custom_components.hair.websocket_api import ws_clip_validate_pronto

        conn = MagicMock()
        await ws_clip_validate_pronto(
            fake_hass, conn,
            {"id": 1, "type": "hair/clip/validate-pronto", "pronto": NEC_TIMINGS,
             "as_infrared": True},
        )
        answer = conn.send_result.call_args.args[1]
        assert answer["valid"] is True
        assert answer["source_format"] == SOURCE_TIMINGS
        assert answer["warnings"][0] == CARRIER_NOTE[SOURCE_TIMINGS]
        assert answer["recognized_protocol"] is not None
        # The Pronto the editor saves: what the save doors already take.
        assert validate_pronto(answer["normalized"]).valid
        assert coerce_pasted_code(answer["normalized"]).source == "pronto"

        await ws_clip_validate_pronto(
            fake_hass, conn,
            {"id": 2, "type": "hair/clip/validate-pronto", "pronto": NEC_TIMINGS},
        )
        assert conn.send_result.call_args.args[1]["valid"] is False
