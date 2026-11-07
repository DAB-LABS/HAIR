"""The encode-only classes irdb rows are built with (custom_components/hair/encoders).

WHAT ANCHORS EACH ONE. A build checked against the same helper that
built it proves nothing, so every expected train below is written out
by hand from the protocol's IRP definition (quoted in each class's
module docstring): the bit strings are spelled out literally, in the
order the protocol sends them, and the timings are the IRP's units
multiplied out.

NOTHING DECODES THEM. These protocols have no decoder in HAIR on
purpose, and a code built here is stored to send as built. That only
holds if no other decoder claims the code either, so each protocol's
builds are put through the full registry on whichever leg runs.
"""
from __future__ import annotations

import pytest

from custom_components.hair import irdb_csv
from custom_components.hair.encoders.mitsubishi import MitsubishiCommand
from custom_components.hair.encoders.recs80 import RECS80Command
from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.irdb_csv import IrdbError
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.wig_adapters import _triple_reproduces


def _train(bits: str, mark: int, zero: int, one: int) -> list[int]:
    """A literal bit string as mark/space pairs, written for the tests."""
    out: list[int] = []
    for ch in bits:
        out += [mark, -(one if ch == "1" else zero)]
    return out


def _nothing_decodes(timings: list[int]) -> bool:
    return try_decode_identity(list(timings)) is None


# --- Mitsubishi --------------------------------------------------------------
#
# {32.6k,300}<1,-3|1,-7>(D:8,F:8,1,-80)* [D:0..127,F:0..255], LSB first.


class TestMitsubishi:
    def test_the_frame_written_out(self):
        # D = 71 = 0b01000111, sent low bit first: 1110 0010.
        # F = 23 = 0b00010111, sent low bit first: 1110 1000.
        expected = _train("11100010" + "11101000", 300, 900, 2100)
        expected += [300, -24000]
        assert MitsubishiCommand(device=71, function=23).get_raw_timings() == expected

    def test_carrier_and_frame_length(self):
        command = MitsubishiCommand(device=0, function=0)
        timings = command.get_raw_timings()
        assert command.modulation == 32600
        assert len(timings) == 16 * 2 + 2

    def test_a_repeat_is_the_whole_frame_again(self):
        once = MitsubishiCommand(device=5, function=9).get_raw_timings()
        twice = MitsubishiCommand(
            device=5, function=9, repeat_count=1
        ).get_raw_timings()
        assert twice == once + once

    @pytest.mark.parametrize(("d", "f"), [(128, 0), (-1, 0), (0, 256)])
    def test_out_of_range_is_refused(self, d, f):
        with pytest.raises(ValueError):
            MitsubishiCommand(device=d, function=f)

    def test_the_row_builds_it(self):
        assert irdb_csv.build("Mitsubishi", 71, -1, 23).get_raw_timings() == (
            MitsubishiCommand(device=71, function=23).get_raw_timings()
        )

    def test_the_row_refuses_what_the_protocol_does_not_define(self):
        with pytest.raises(IrdbError, match="Mitsubishi device 128 is outside 0 to 127"):
            irdb_csv.build("Mitsubishi", 128, -1, 23)
        with pytest.raises(IrdbError, match="Mitsubishi has no subdevice"):
            irdb_csv.build("Mitsubishi", 71, 0, 23)

    @pytest.mark.parametrize("d", [0, 3, 71, 119, 127])
    def test_no_decoder_claims_it(self, d):
        for f in range(0, 256, 5):
            timings = MitsubishiCommand(device=d, function=f).get_raw_timings()
            assert _nothing_decodes(timings), (d, f)

    def test_stored_as_built(self):
        timings = MitsubishiCommand(device=71, function=23).get_raw_timings()
        assert _triple_reproduces(raw_to_pronto(timings, frequency=32600), timings)


# --- RECS80 ------------------------------------------------------------------
#
# {38k,158,msb}<1,-31|1,-47>(1:1,T:1,D:3,F:6,1,-45m)* [D:0..7,F:0..63],
# MSB first, T defaults to 0.


class TestRECS80:
    def test_the_frame_written_out(self):
        # Start 1, T 0, D = 5 = 101, F = 38 = 100110, high bit first.
        expected = _train("1" + "0" + "101" + "100110", 158, 4898, 7426)
        expected += [158, -45000]
        assert RECS80Command(device=5, function=38).get_raw_timings() == expected

    def test_the_toggle_is_the_second_bit(self):
        t0 = RECS80Command(device=5, function=38).get_raw_timings()
        t1 = RECS80Command(device=5, function=38, toggle=1).get_raw_timings()
        assert t0[3] == -4898 and t1[3] == -7426
        assert t0[:3] == t1[:3] and t0[4:] == t1[4:]

    def test_carrier_and_frame_length(self):
        command = RECS80Command(device=0, function=0)
        assert command.modulation == 38000
        assert len(command.get_raw_timings()) == 11 * 2 + 2

    def test_a_repeat_keeps_the_toggle(self):
        once = RECS80Command(device=2, function=9, toggle=1).get_raw_timings()
        twice = RECS80Command(
            device=2, function=9, toggle=1, repeat_count=1
        ).get_raw_timings()
        assert twice == once + once

    @pytest.mark.parametrize(
        ("d", "f", "t"), [(8, 0, 0), (0, 64, 0), (0, 0, 2), (-1, 0, 0)]
    )
    def test_out_of_range_is_refused(self, d, f, t):
        with pytest.raises(ValueError):
            RECS80Command(device=d, function=f, toggle=t)

    def test_the_row_builds_it_with_toggle_0(self):
        assert irdb_csv.build("RECS80", 5, -1, 38).get_raw_timings() == (
            RECS80Command(device=5, function=38, toggle=0).get_raw_timings()
        )

    def test_the_row_refuses_what_the_protocol_does_not_define(self):
        with pytest.raises(IrdbError, match="RECS80 device 8 is outside 0 to 7"):
            irdb_csv.build("RECS80", 8, -1, 1)
        with pytest.raises(IrdbError, match="RECS80 function 64 is outside 0 to 63"):
            irdb_csv.build("RECS80", 1, -1, 64)
        with pytest.raises(IrdbError, match="RECS80 has no subdevice"):
            irdb_csv.build("RECS80", 1, 0, 1)

    def test_no_decoder_claims_it(self):
        for d in range(8):
            for f in range(64):
                for t in (0, 1):
                    timings = RECS80Command(
                        device=d, function=f, toggle=t
                    ).get_raw_timings()
                    assert _nothing_decodes(timings), (d, f, t)

    def test_stored_as_built(self):
        timings = RECS80Command(device=5, function=38).get_raw_timings()
        assert _triple_reproduces(raw_to_pronto(timings, frequency=38000), timings)
