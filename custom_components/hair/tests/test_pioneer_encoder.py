"""Pioneer: a real encoder, and the ruling that it is never registered.

The interesting assertions here are negative. Pioneer is not a decoded
label anywhere, and this module pins the three outcomes a Pioneer frame
can actually have so the ruling cannot be quietly reversed.
"""
from __future__ import annotations

import pytest

from custom_components.hair.decoders.pioneer import PioneerCommand
from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.protocol_decode import (
    get_spec,
    registered_protocols,
    try_decode_identity,
)
from custom_components.hair.tests.leg import strict_nec_available

#: NEC's nominals and the 40 percent band this package uses, so the
#: window claim is arithmetic in the test rather than prose in a plan.
NEC_NOMINALS = {
    "leader mark": 9000,
    "leader space": 4500,
    "bit mark": 562,
    "zero space": 562,
    "one space": 1687,
}
#: Both timing sets in circulation, named by their bit mark. The class
#: ships the 532 set's numbers, the tighter of the two, but the ruling
#: has to hold for either, so both are checked. Their tightest
#: separations from NEC differ and the test names each rather than
#: quoting one figure for both.
PIONEER_VARIANTS = {
    "Pioneer 548": {
        "leader mark": 8470,
        "leader space": 4230,
        "bit mark": 548,
        "zero space": 500,
        "one space": 1570,
    },
    "Pioneer 532": {
        "leader mark": 8510,
        "leader space": 4256,
        "bit mark": 532,
        "zero space": 532,
        "one space": 1596,
    },
}
PIONEER_VALUES = PIONEER_VARIANTS["Pioneer 532"]


class TestPioneerIsNeverMinted:
    def test_the_label_is_not_registered(self):
        assert get_spec("PIONEER") is None
        assert "PIONEER" not in {
            entry["protocol"].upper() for entry in registered_protocols()
        }

    def test_an_air_capture_of_a_pioneer_frame_reads_as_nec(self):
        """Outcome one of three, and the reason for the ruling.

        A complement-valid Pioneer payload is indistinguishable from NEC
        once the carrier is gone, so it decodes as NEC. Pinning it here
        means a future registration cannot land without this test going
        red and somebody reading the docstring in ``decoders/pioneer``.
        """
        from custom_components.hair.wig_adapters import _build_pioneer

        # Built the way the Flipper importer builds it: from the two
        # 8-bit payload bytes a Flipper line carries, complements derived.
        source = _build_pioneer(0x5A, 0x14)
        assert (source.address, source.command) == (0xA55A, 0xEB14)
        identity = try_decode_identity(source.get_raw_timings())
        if not strict_nec_available():
            assert identity is None, "no NEC decoder on this leg"
            return
        assert identity is not None
        assert identity.protocol == "NEC"
        assert (identity.address, identity.command) == (0xA55A, 0x14)

    def test_a_non_complement_pioneer_frame_stays_raw(self):
        """Outcome two of three."""
        source = PioneerCommand(address=0xA55A, command=0x1234)
        assert try_decode_identity(source.get_raw_timings()) is None

    def test_a_built_row_is_stored_at_40_khz_and_still_reads_as_nec(self):
        """Outcome three of three: the Flipper route.

        The builder entry buys the 40 kHz carrier and the tighter leader
        in the stored waveform. The identity still comes from re-decoding
        that waveform, which lands on NEC, because HAIR cannot hear a
        carrier and does not pretend to.
        """
        command = 0x14 | ((~0x14 & 0xFF) << 8)
        source = PioneerCommand(address=0xA55A, command=command)
        assert source.modulation == 40000
        pronto = raw_to_pronto(
            source.get_raw_timings(), frequency=source.modulation)
        assert pronto.split()[1] == "0068", "the 40 kHz word must survive"
        identity = try_decode_identity(source.get_raw_timings())
        expected = "NEC" if strict_nec_available() else None
        assert (None if identity is None else identity.protocol) == expected


class TestPioneerSitsInsideEveryNecWindow:
    """The measurement the ruling rests on, recomputed here."""

    @pytest.mark.parametrize("variant", sorted(PIONEER_VARIANTS))
    @pytest.mark.parametrize("axis", sorted(NEC_NOMINALS))
    def test_every_axis_is_inside_nec_tolerance(self, variant, axis):
        nominal = NEC_NOMINALS[axis]
        low, high = nominal * 0.6, nominal * 1.4
        assert low <= PIONEER_VARIANTS[variant][axis] <= high, (variant, axis)

    @pytest.mark.parametrize(
        ("variant", "tightest"),
        [("Pioneer 548", 0.0255), ("Pioneer 532", 0.0564)],
    )
    def test_no_usable_tolerance_separates_them(self, variant, tightest):
        """How tight a band would have to be to tell the two apart.

        Both figures are an order of magnitude below what a real
        receiver delivers and well under what this package's tightest
        decoder uses, which is 0.3 for Dyson. The two definitions differ
        on which axis is worst and by how much, so each is asserted with
        its own number rather than one standing in for both.
        """
        values = PIONEER_VARIANTS[variant]
        worst = min(
            (NEC_NOMINALS[a] - values[a]) / values[a] for a in NEC_NOMINALS
        )
        assert worst == pytest.approx(tightest, abs=0.0005)
        assert worst < 0.30, "inside even the tightest band this package uses"


class TestPioneerWire:
    @pytest.mark.parametrize(
        ("address", "command"),
        [(0x0000, 0x0000), (0xFFFF, 0xFFFF), (0xA55A, 0xEB14)],
    )
    def test_round_trip(self, address, command):
        source = PioneerCommand(address=address, command=command)
        rebuilt = PioneerCommand.from_raw_timings(source.get_raw_timings())
        assert rebuilt is not None
        assert (rebuilt.address, rebuilt.command) == (address, command)

    def test_the_frame_matches_the_definition(self):
        timings = PioneerCommand(address=0, command=0).get_raw_timings()
        assert timings[0] == 8510
        assert timings[1] == -4256
        assert timings[2] == 532
        assert timings[3] == -532
        assert len(timings) == 2 + 32 * 2 + 1
        ones = PioneerCommand(address=0xFFFF, command=0xFFFF).get_raw_timings()
        assert ones[3] == -1596

    def test_bit_order_is_lsb_first_per_byte(self):
        source = PioneerCommand(address=0x0001, command=0x0000)
        timings = source.get_raw_timings()
        assert timings[3] == -1596, "bit 0 of byte 1 must be the first bit"
        assert timings[5] == -532

    def test_out_of_range_fields_are_refused(self):
        with pytest.raises(ValueError, match="0xFFFF"):
            PioneerCommand(address=0x10000, command=0)
