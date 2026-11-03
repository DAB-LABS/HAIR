"""LIRC SPACE_ENC blocks: the ``pre`` and ``post`` pulses are written.

lircd.conf(5) gives a frame as
``header | plead | pre_data | pre | data | post | post_data | ptrail``:
``pre`` is a pulse and space immediately following the pre_data, and
``post`` a pulse and space immediately following the button code. A
remote that states one sends it on every press, so a code rendered
without it is not the code the remote sends.
"""
from __future__ import annotations

from pathlib import Path

from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.wig_adapters import _LircSpaceEnc, convert

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"


def _params(**extra: str) -> dict[str, list[str]]:
    base = {
        "bits": "8",
        "header": "9000 4500",
        "one": "560 1690",
        "zero": "560 560",
        "ptrail": "560",
        "gap": "40000",
    }
    base.update(extra)
    return {key: value.split() for key, value in base.items()}


def _bits(value: int, width: int, one=(560, 1690), zero=(560, 560)) -> list[int]:
    out: list[int] = []
    for i in range(width - 1, -1, -1):
        pulse, space = one if (value >> i) & 1 else zero
        out.extend((pulse, -space))
    return out


class TestFrameOrder:
    def test_a_block_with_neither_is_unchanged(self):
        built = _LircSpaceEnc.from_params(_params()).build(0xA5)
        assert built == [9000, -4500, *_bits(0xA5, 8), 560, -40000]

    def test_pre_follows_the_pre_data(self):
        builder = _LircSpaceEnc.from_params(_params(
            pre_data_bits="8", pre_data="0x54", pre="570 3890",
        ))
        assert builder.build(0x70) == [
            9000, -4500, *_bits(0x54, 8), 570, -3890, *_bits(0x70, 8),
            560, -40000,
        ]

    def test_post_follows_the_code_and_comes_before_the_post_data(self):
        builder = _LircSpaceEnc.from_params(_params(
            post_data_bits="4", post_data="0x9", post="600 2000",
        ))
        assert builder.build(0x70) == [
            9000, -4500, *_bits(0x70, 8), 600, -2000, *_bits(0x9, 4),
            560, -40000,
        ]

    def test_all_of_them_in_the_man_page_order(self):
        builder = _LircSpaceEnc.from_params(_params(
            plead="300",
            pre_data_bits="4", pre_data="0x3", pre="570 3890",
            post="600 2000", post_data_bits="4", post_data="0xC",
        ))
        assert builder.build(0x81) == [
            9000, -4500, 300, *_bits(0x3, 4), 570, -3890, *_bits(0x81, 8),
            600, -2000, *_bits(0xC, 4), 560, -40000,
        ]

    def test_a_pre_or_post_without_data_bits_is_still_written(self):
        builder = _LircSpaceEnc.from_params(_params(pre="570 3890", post="600 2000"))
        assert builder.build(0x01) == [
            9000, -4500, 570, -3890, *_bits(0x01, 8), 600, -2000, 560, -40000,
        ]

    def test_a_malformed_pre_or_post_is_ignored(self):
        plain = _LircSpaceEnc.from_params(_params()).build(0x33)
        for extra in ({"pre": "570"}, {"post": "0 2000"}, {"pre": "570 0"}):
            assert _LircSpaceEnc.from_params(_params(**extra)).build(0x33) == plain


class TestTheFixture:
    """A remote whose block states ``pre 570 3890`` between its two bytes."""

    def _signals(self):
        result = convert(
            (FIXTURES / "lirc_space_enc_pre_data_futarque.lircd.conf").read_text()
        )
        assert result.error is None
        (wig,) = result.wigs
        return wig.signals

    def test_every_code_carries_the_pre_pulse_between_its_bytes(self):
        signals = self._signals()
        assert len(signals) == 41
        for sig in signals:
            timings = ProntoCommand(sig.pronto).get_raw_timings()
            # header (2), eight pre_data bits (16), then the pre pulse.
            assert abs(timings[18] - 570) <= 30, sig.alias
            assert abs(-timings[19] - 3890) <= 30, sig.alias
            # eight data bits and the trailing pulse follow it.
            assert abs(timings[36] - 555) <= 30, sig.alias

    def test_the_codes_read_as_no_protocol(self):
        for sig in self._signals():
            assert try_decode_identity(
                ProntoCommand(sig.pronto).get_raw_timings()
            ) is None, sig.alias
