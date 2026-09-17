"""The verbatim NEC-shaped class: an encoder and a file reader.

The point of most of this module is what does NOT happen. The class is
deliberately unregistered, so no capture mints ``NECNC``, and the tests
say so rather than leaving it to a reader to notice the absence.
"""
from __future__ import annotations

import pytest

from custom_components.hair.decoders.nec_variant import (
    LABEL,
    NECNoComplementCommand,
)
from custom_components.hair.protocol_decode import (
    get_spec,
    registered_protocols,
    try_decode_identity,
)
from custom_components.hair.tests.leg import strict_nec_available

#: The three Yamaha addresses the measured non-complement frames carry,
#: as HAIR reads them off the wire. Those frames are written MSB-first
#: per byte, so 0x857A here is the value published as 0x5EA1.
YAMAHA_ADDRESSES = [0x857A, 0x817E, 0x017F]


class TestNotADecoder:
    """The ruling, as tests.

    A verbatim reader's only possible gate is "the complement does not
    hold", which is the absence of the one error check the NEC frame
    carries, so every NEC capture corrupted in its payload bytes would
    pass it. The genuine population makes that unfixable rather than
    merely risky: the sampled Yamaha frames all sit at Hamming distance
    exactly one from a legal NEC frame, so a real Yamaha press and a
    one-bit-corrupted NEC press are the same shape.
    """

    def test_the_label_is_not_registered(self):
        assert get_spec(LABEL) is None
        assert LABEL not in {
            entry["protocol"].upper() for entry in registered_protocols()
        }

    @pytest.mark.parametrize("address", YAMAHA_ADDRESSES)
    def test_a_non_complement_capture_stays_raw(self, address):
        """Off the air these keep being a raw row, as they are today."""
        source = NECNoComplementCommand(address=address, command=0x7F82)
        assert not source.complement_holds
        assert try_decode_identity(source.get_raw_timings()) is None

    def test_a_one_bit_corrupted_nec_frame_is_not_claimed_either(self):
        """The reason there is no decoder, stated as the failure it
        would have caused: a marginal capture must stay raw so the user
        re-captures, not become a confident wrong identity."""
        clean = NECNoComplementCommand(address=0x04FB, command=0xF708)
        assert clean.complement_holds
        if strict_nec_available():
            assert try_decode_identity(clean.get_raw_timings()) is not None
        for flipped in range(8, 16):
            corrupt = NECNoComplementCommand(
                address=0x04FB, command=0xF708 ^ (1 << flipped)
            )
            assert not corrupt.complement_holds
            assert try_decode_identity(corrupt.get_raw_timings()) is None

    def test_the_genuine_population_is_one_bit_from_legal(self):
        """Why no distance gate rescues a decoder here."""
        for address in YAMAHA_ADDRESSES:
            command = 0x7F82
            byte3, byte4 = command & 0xFF, (command >> 8) & 0xFF
            distance = bin(byte3 ^ byte4 ^ 0xFF).count("1")
            assert distance == 1, (address, distance)


class TestVerbatimWire:
    @pytest.mark.parametrize("address", YAMAHA_ADDRESSES)
    @pytest.mark.parametrize("command", [0x0000, 0x7F82, 0xFFFF, 0x2E02])
    def test_round_trip(self, address, command):
        source = NECNoComplementCommand(address=address, command=command)
        rebuilt = NECNoComplementCommand.from_raw_timings(
            source.get_raw_timings())
        assert rebuilt is not None
        assert (rebuilt.address, rebuilt.command) == (address, command)

    def test_both_payload_bytes_go_out_as_written(self):
        source = NECNoComplementCommand(address=0x87EE, command=0x2E02)
        assert source.wire_bytes == (0xEE, 0x87, 0x02, 0x2E)

    def test_upstream_timing_constants_are_matched(self):
        """A complement-valid file must keep the exact Pronto it had.

        The stored code is a function of these constants, so they are
        upstream's rather than a protocol definition's slightly
        different rendering. Compared against the real encoder when the
        library is present.
        """
        upstream = pytest.importorskip("infrared_protocols.commands.nec")
        for address, command in ((0x87EE, 0x5E), (0x40BF, 0x12), (0xFF00, 0xA5)):
            theirs = upstream.NECCommand(
                address=address, command=command).get_raw_timings()
            verbatim = command | ((~command & 0xFF) << 8)
            ours = NECNoComplementCommand(
                address=address, command=verbatim).get_raw_timings()
            assert ours == theirs, hex(address)

    def test_dittos_are_markers_not_duplicated_frames(self):
        lengths = [
            len(NECNoComplementCommand(
                address=0x87EE, command=0x2E02, repeat_count=n
            ).get_raw_timings())
            for n in (0, 1, 3)
        ]
        assert lengths == [67, 71, 79]

    def test_out_of_range_fields_are_refused(self):
        with pytest.raises(ValueError, match="0xFFFF"):
            NECNoComplementCommand(address=0x10000, command=0)
        with pytest.raises(ValueError, match="0xFFFF"):
            NECNoComplementCommand(address=0, command=0x10000)


class TestWhatFilesLandOn:
    """The division the ruling turns on: the file told us the bytes."""

    def test_an_apple_frame_built_verbatim_decodes_as_apple(self):
        source = NECNoComplementCommand(address=0x87EE, command=0x2E02)
        identity = try_decode_identity(source.get_raw_timings())
        assert identity is not None
        assert identity.fingerprint == "APPLE:0x87ee:0x01:p2e"

    def test_a_complement_valid_frame_built_verbatim_decodes_as_nec(self):
        source = NECNoComplementCommand(address=0x40BF, command=0xED12)
        assert source.complement_holds
        identity = try_decode_identity(source.get_raw_timings())
        if not strict_nec_available():
            # No strict NEC decoder on this leg, so the frame is
            # correctly unclaimed. What must hold either way is that
            # the verbatim class did not mint an identity of its own.
            assert identity is None
            return
        assert identity is not None
        assert identity.protocol == "NEC"
        assert (identity.address, identity.command) == (0x40BF, 0x12)
