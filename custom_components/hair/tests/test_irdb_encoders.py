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
from custom_components.hair.encoders.dish_network import DishNetworkCommand
from custom_components.hair.encoders.gi_cable import GICableCommand
from custom_components.hair.encoders.mitsubishi import MitsubishiCommand
from custom_components.hair.encoders.panasonic_old import PanasonicOldCommand
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


# --- G.I. Cable --------------------------------------------------------------
#
# {38.7k,490}<1,-4.5|1,-9>(18,-9,F:8,D:4,C:4,1,-84,(18,-4.5,1,-178)*)
# {C = -(D + F:4 + F:4:4)} [D:0..15,F:0..255], LSB first.

_GI_LEAD = [8820, -4410]
_GI_TAIL = [490, -41160]


class TestGICable:
    def test_the_frame_written_out(self):
        # F = 29 = 0b00011101 -> 1011 1000, D = 0 -> 0000.
        # C = -(0 + 13 + 1) mod 16 = 2 -> 0100.
        expected = _GI_LEAD + _train(
            "10111000" + "0000" + "0100", 490, 2205, 4410
        ) + _GI_TAIL
        assert GICableCommand(device=0, function=29).get_raw_timings() == expected

    def test_the_check_with_a_device(self):
        # D = 3 -> 1100. C = -(3 + 13 + 1) mod 16 = 15 -> 1111.
        expected = _GI_LEAD + _train(
            "10111000" + "1100" + "1111", 490, 2205, 4410
        ) + _GI_TAIL
        assert GICableCommand(device=3, function=29).get_raw_timings() == expected

    def test_the_four_bits_always_sum_to_zero(self):
        for d in range(16):
            for f in range(256):
                t = GICableCommand(device=d, function=f).get_raw_timings()
                bits = [1 if space == -4410 else 0 for space in t[3:35:2]]
                value = sum(b << i for i, b in enumerate(bits))
                nibbles = [(value >> s) & 0xF for s in (0, 4, 8, 12)]
                assert sum(nibbles) % 16 == 0, (d, f)

    def test_carrier(self):
        assert GICableCommand(device=0, function=0).modulation == 38700

    def test_a_repeat_is_a_ditto(self):
        frame = GICableCommand(device=0, function=7).get_raw_timings()
        held = GICableCommand(
            device=0, function=7, repeat_count=2
        ).get_raw_timings()
        assert held == frame + [8820, -2205, 490, -87220] * 2

    @pytest.mark.parametrize(("d", "f"), [(16, 0), (0, 256), (-1, 0)])
    def test_out_of_range_is_refused(self, d, f):
        with pytest.raises(ValueError):
            GICableCommand(device=d, function=f)

    def test_the_row_builds_it(self):
        assert irdb_csv.build("G.I.Cable", 0, -1, 29).get_raw_timings() == (
            GICableCommand(device=0, function=29).get_raw_timings()
        )
        # irdb's name in any letter case.
        assert irdb_csv.build("g.i.cable", 0, -1, 29).get_raw_timings() == (
            GICableCommand(device=0, function=29).get_raw_timings()
        )

    def test_the_row_refuses_what_the_protocol_does_not_define(self):
        with pytest.raises(IrdbError, match=r"G\.I\.Cable device 16 is outside 0 to 15"):
            irdb_csv.build("G.I.Cable", 16, -1, 1)
        with pytest.raises(IrdbError, match=r"G\.I\.Cable has no subdevice"):
            irdb_csv.build("G.I.Cable", 0, 0, 1)

    @pytest.mark.parametrize("d", [0, 1, 7, 15])
    def test_no_decoder_claims_it(self, d):
        for f in range(256):
            timings = GICableCommand(device=d, function=f).get_raw_timings()
            assert _nothing_decodes(timings), (d, f)

    def test_stored_as_built(self):
        timings = GICableCommand(device=0, function=29).get_raw_timings()
        assert _triple_reproduces(raw_to_pronto(timings, frequency=38700), timings)


# --- Dish Network ------------------------------------------------------------
#
# {57.6k,406}<1,-7|1,-4>(1,-15,(F:-6,S:5,D:5,1,-15)+)
# [F:0..63,S:0..31,D:0..31]. F high bit first, S and D low bit first,
# and the LONG space is 0.

_DISH_GAP = [406, -6090]


class TestDishNetwork:
    def test_the_frame_written_out(self):
        # F = 35 = 100011 high bit first; S = 2 -> 01000; D = 24 -> 00011.
        expected = _DISH_GAP + _train(
            "100011" + "01000" + "00011", 406, 2842, 1624
        ) + _DISH_GAP
        assert DishNetworkCommand(
            device=24, subdevice=2, function=35
        ).get_raw_timings() == expected

    def test_f_is_high_bit_first_and_d_low_bit_first(self):
        """F = 1 lands on F's last bit; D = 1 on D's first."""
        f1 = DishNetworkCommand(device=0, subdevice=0, function=1).get_raw_timings()
        d1 = DishNetworkCommand(device=1, subdevice=0, function=0).get_raw_timings()
        # The bit spaces sit at every other index from 3 (after the
        # lead-in pair and the first bit's mark).
        assert [i for i, s in enumerate(f1[3:35:2]) if s == -1624] == [5]
        assert [i for i, s in enumerate(d1[3:35:2]) if s == -1624] == [11]

    def test_carrier(self):
        command = DishNetworkCommand(device=0, subdevice=0, function=0)
        assert command.modulation == 57600

    def test_a_repeat_is_the_frame_without_the_lead_in(self):
        once = DishNetworkCommand(device=3, subdevice=1, function=9).get_raw_timings()
        held = DishNetworkCommand(
            device=3, subdevice=1, function=9, repeat_count=1
        ).get_raw_timings()
        assert held == once + once[2:]

    @pytest.mark.parametrize(
        ("d", "s", "f"), [(32, 0, 0), (0, 32, 0), (0, 0, 64), (-1, 0, 0)]
    )
    def test_out_of_range_is_refused(self, d, s, f):
        with pytest.raises(ValueError):
            DishNetworkCommand(device=d, subdevice=s, function=f)

    def test_the_row_builds_it(self):
        assert irdb_csv.build("Dish_Network", 24, 2, 35).get_raw_timings() == (
            DishNetworkCommand(device=24, subdevice=2, function=35).get_raw_timings()
        )

    def test_the_row_refuses_what_the_protocol_does_not_define(self):
        with pytest.raises(IrdbError, match="Dish_Network needs a subdevice"):
            irdb_csv.build("Dish_Network", 24, -1, 35)
        with pytest.raises(IrdbError, match="Dish_Network function 64 is outside 0 to 63"):
            irdb_csv.build("Dish_Network", 24, 2, 64)

    @pytest.mark.parametrize("d", [0, 1, 24, 31])
    def test_no_decoder_claims_it(self, d):
        for s in range(32):
            for f in range(0, 64, 3):
                timings = DishNetworkCommand(
                    device=d, subdevice=s, function=f
                ).get_raw_timings()
                assert _nothing_decodes(timings), (d, s, f)

    def test_stored_as_built(self):
        timings = DishNetworkCommand(device=24, subdevice=2, function=35).get_raw_timings()
        assert _triple_reproduces(raw_to_pronto(timings, frequency=57600), timings)


# --- Panasonic_Old -----------------------------------------------------------
#
# {57.6k,833}<1,-1|1,-3>(4,-4,D:5,F:6,~D:5,~F:6,1,-44m)*
# [D:0..31,F:0..63], LSB first.


class TestPanasonicOld:
    def test_the_frame_written_out(self):
        # D = 9 -> 10010, F = 44 -> 001101, then ~D = 22 -> 01101 and
        # ~F = 19 -> 110010, each low bit first.
        bits = _train("10010" + "001101" + "01101" + "110010", 833, 833, 2499)
        expected = [3332, -3332, *bits, 833, -44000]
        assert PanasonicOldCommand(device=9, function=44).get_raw_timings() == expected

    def test_the_second_half_inverts_the_first(self):
        for d in range(32):
            for f in range(64):
                t = PanasonicOldCommand(device=d, function=f).get_raw_timings()
                bits = [1 if space == -2499 else 0 for space in t[3:47:2]]
                assert bits[11:] == [1 - b for b in bits[:11]], (d, f)

    def test_carrier(self):
        assert PanasonicOldCommand(device=0, function=0).modulation == 57600

    def test_a_repeat_is_the_whole_frame_again(self):
        once = PanasonicOldCommand(device=3, function=5).get_raw_timings()
        twice = PanasonicOldCommand(
            device=3, function=5, repeat_count=1
        ).get_raw_timings()
        assert twice == once + once

    @pytest.mark.parametrize(("d", "f"), [(32, 0), (0, 64), (-1, 0)])
    def test_out_of_range_is_refused(self, d, f):
        with pytest.raises(ValueError):
            PanasonicOldCommand(device=d, function=f)

    def test_the_row_builds_it(self):
        assert irdb_csv.build("Panasonic_Old", 9, -1, 44).get_raw_timings() == (
            PanasonicOldCommand(device=9, function=44).get_raw_timings()
        )

    def test_the_row_refuses_what_the_protocol_does_not_define(self):
        with pytest.raises(IrdbError, match="Panasonic_Old function 64 is outside 0 to 63"):
            irdb_csv.build("Panasonic_Old", 9, -1, 64)
        with pytest.raises(IrdbError, match="Panasonic_Old has no subdevice"):
            irdb_csv.build("Panasonic_Old", 9, 0, 44)

    def test_no_decoder_claims_it(self):
        for d in range(32):
            for f in range(64):
                timings = PanasonicOldCommand(device=d, function=f).get_raw_timings()
                assert _nothing_decodes(timings), (d, f)

    def test_stored_as_built(self):
        timings = PanasonicOldCommand(device=9, function=44).get_raw_timings()
        assert _triple_reproduces(raw_to_pronto(timings, frequency=57600), timings)
