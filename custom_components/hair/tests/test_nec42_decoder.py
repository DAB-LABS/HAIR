"""The 42-bit NEC family, in both its readings.

Fixtures are synthesized by round-tripping this package's own encoders.
Nothing here is transcribed from a third-party rendering.
"""
from __future__ import annotations

import pytest

from custom_components.hair.decoders.nec42 import (
    NEC42Command,
    NEC42ExtCommand,
)
from custom_components.hair.protocol_decode import (
    build_protocol_command,
    try_decode_identity,
)

CORNERS = [(0x0000, 0x00), (0x1FFF, 0xFF), (0x0001, 0x80), (0x1234, 0x56)]


def _nec32(address: int, command: int) -> list[int]:
    """A strict 32-bit NEC frame, built here so the test needs no library."""
    data = [
        address & 0xFF,
        (address >> 8) & 0xFF,
        command & 0xFF,
        (~command) & 0xFF,
    ]
    timings = [9000, -4500]
    for byte in data:
        for bit in range(8):
            timings += [562, -1687 if (byte >> bit) & 1 else -562]
    timings.append(562)
    return timings


class TestNEC42RoundTrip:
    @pytest.mark.parametrize(("address", "command"), CORNERS)
    def test_round_trip(self, address, command):
        source = NEC42Command(address=address, command=command)
        rebuilt = NEC42Command.from_raw_timings(source.get_raw_timings())
        assert rebuilt is not None
        assert (rebuilt.address, rebuilt.command) == (address, command)

    @pytest.mark.parametrize(("address", "command"), CORNERS)
    def test_one_wire_builder_serves_both_readings(self, address, command):
        """The checked reading expands into the verbatim one's wire.

        Two classes over one frame can drift into two waveforms, which
        would be invisible until somebody re-encoded a stored identity
        through the other one. They share a builder and this says so.
        """
        checked = NEC42Command(address=address, command=command)
        expanded = NEC42ExtCommand(
            address=checked.wire_value & 0x3FFFFFF,
            command=(checked.wire_value >> 26) & 0xFFFF,
        )
        assert checked.get_raw_timings() == expanded.get_raw_timings()

    def test_ext_round_trips_the_full_width(self):
        source = NEC42ExtCommand(address=0x3FFFFFF, command=0xFFFF)
        rebuilt = NEC42ExtCommand.from_raw_timings(source.get_raw_timings())
        assert rebuilt is not None
        assert (rebuilt.address, rebuilt.command) == (0x3FFFFFF, 0xFFFF)

    def test_out_of_range_fields_are_refused_not_masked(self):
        """Masking invents a code the file could not have meant."""
        with pytest.raises(ValueError, match="0x1FFF"):
            NEC42Command(address=0x2000, command=0)
        with pytest.raises(ValueError, match="0xFF"):
            NEC42Command(address=0, command=0x100)
        with pytest.raises(ValueError, match="0x3FFFFFF"):
            NEC42ExtCommand(address=0x4000000, command=0)


class TestNEC42Gates:
    def test_a_broken_complement_decodes_ext_and_not_nec42(self):
        """The one that separates the two readings."""
        good = NEC42Command(address=0x1234, command=0x56)
        broken = NEC42ExtCommand(
            address=(good.wire_value & 0x3FFFFFF) ^ 0x2000,
            command=(good.wire_value >> 26) & 0xFFFF,
        )
        timings = broken.get_raw_timings()
        assert NEC42Command.from_raw_timings(timings) is None
        assert NEC42ExtCommand.from_raw_timings(timings) is not None
        identity = try_decode_identity(timings)
        assert identity is not None
        assert identity.protocol == "NEC42EXT"

    def test_a_32_bit_nec_frame_is_refused_by_both(self):
        timings = _nec32(0x04, 0x08)
        assert NEC42Command.from_raw_timings(timings) is None
        assert NEC42ExtCommand.from_raw_timings(timings) is None

    def test_a_frame_that_keeps_going_is_refused(self):
        """The termination gate, which is the whole of NEC42EXT's honesty.

        A long state blob offers a perfectly good first forty-two bits.
        What refuses it is that the frame does not end there.
        """
        source = NEC42ExtCommand(address=0x2345678, command=0xABCD)
        timings = source.get_raw_timings()
        assert NEC42ExtCommand.from_raw_timings(timings) is not None
        extended = [*timings, -562, 562, -1687, 562, -562, 562]
        assert NEC42ExtCommand.from_raw_timings(extended) is None
        assert NEC42Command.from_raw_timings(
            [
                *NEC42Command(address=0x1234, command=0x56).get_raw_timings(),
                -562, 562, -1687, 562,
            ]
        ) is None

    def test_a_truncated_frame_is_refused(self):
        source = NEC42ExtCommand(address=0x2345678, command=0xABCD)
        timings = source.get_raw_timings()
        assert NEC42ExtCommand.from_raw_timings(timings[:-6]) is None

    def test_trailing_repeat_markers_are_accounted_for_not_refused(self):
        """A held button leaves markers behind; they are part of the
        capture and the census has to count them."""
        source = NEC42Command(address=0x1234, command=0x56)
        timings = [
            *source.get_raw_timings(),
            -41_000, 9000, -2250, 562, -96_000, 9000, -2250, 562,
        ]
        rebuilt = NEC42Command.from_raw_timings(timings)
        assert rebuilt is not None
        assert rebuilt.frames_explained == 3


class TestNEC42Registry:
    @pytest.mark.parametrize(("address", "command"), CORNERS)
    def test_identity_and_rebuild(self, address, command):
        source = NEC42Command(address=address, command=command)
        identity = try_decode_identity(source.get_raw_timings())
        assert identity is not None
        assert identity.protocol == "NEC42"
        assert (identity.address, identity.command) == (address, command)
        assert identity.extras is None
        assert identity.fingerprint == f"NEC42:{address:#06x}:{command:#04x}"

        rebuilt = build_protocol_command("NEC42", address, command)
        assert rebuilt is not None
        assert rebuilt.get_raw_timings() == source.get_raw_timings()

    def test_a_42_bit_identity_never_rebuilds_as_a_32_bit_frame(self):
        """The ``get_spec`` prefix bug, pinned where it would have bitten.

        ``get_spec("NEC42")`` used to resolve to the **nec** spec,
        because "NEC42" starts with "NEC" and "42" is a digit string and
        nec is registered first. A stored 42-bit identity would then
        have been rebuilt as a 32-bit NEC frame and transmitted.
        """
        rebuilt = build_protocol_command("NEC42", 0x1234, 0x56)
        assert rebuilt is not None
        assert type(rebuilt).__name__ == "NEC42Command"
        assert len(rebuilt.get_raw_timings()) == 2 + 42 * 2 + 1

    def test_ext_identity_and_rebuild(self):
        source = NEC42ExtCommand(address=0x2345678, command=0xABCD)
        identity = try_decode_identity(source.get_raw_timings())
        assert identity is not None
        assert identity.protocol == "NEC42EXT"
        rebuilt = build_protocol_command("NEC42EXT", 0x2345678, 0xABCD)
        assert rebuilt is not None
        assert rebuilt.get_raw_timings() == source.get_raw_timings()

    def test_the_checked_reading_wins_when_both_could_read_a_frame(self):
        """NEC42 probes ahead of NEC42EXT, so a complement-valid frame
        gets the reading that carries a checksum."""
        source = NEC42Command(address=0x1234, command=0x56)
        identity = try_decode_identity(source.get_raw_timings())
        assert identity is not None
        assert identity.protocol == "NEC42"
