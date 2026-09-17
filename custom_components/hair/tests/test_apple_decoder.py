"""The Apple remote decoder, its parity gate and its pairing identity.

Fixtures are synthesized by round-tripping this package's own encoder.
The values exercised are the ones derived from the frame layout and
from the repo's own Flipper fixture; no third-party data is carried
here.
"""
from __future__ import annotations

import pytest

from custom_components.hair.decoders.apple import APPLE_ADDRESS, AppleCommand
from custom_components.hair.protocol_decode import (
    build_protocol_command,
    try_decode_identity,
)
from custom_components.hair.tests.leg import strict_nec_available

#: The six buttons that appear in both sources, with the command each
#: resolves to. Cross-source agreement on these is what confirms the
#: ``(command << 1) | parity`` split: the two sources carry different
#: pairing ids, so the same command arrives behind a different byte3.
SHARED_BUTTONS = {
    "Menu": 0x01,
    "Right": 0x03,
    "Left": 0x04,
    "Up": 0x05,
    "Down": 0x06,
    "Reboot": 0x0C,
}


def _nec32(address: int, command: int) -> list[int]:
    """A complement-valid 32-bit NEC frame, built locally."""
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


def _bytes_of(timings: list[int]) -> list[int]:
    data = [0, 0, 0, 0]
    for index in range(32):
        if -timings[3 + 2 * index] > 1100:
            data[index // 8] |= 1 << (index % 8)
    return data


class TestAppleRoundTrip:
    @pytest.mark.parametrize("command", [0x00, 0x01, 0x2F, 0x7F, 0x40])
    @pytest.mark.parametrize("pair_id", [0x00, 0x01, 0x2E, 0x37, 0xFF])
    def test_round_trip_over_corners(self, command, pair_id):
        source = AppleCommand(command=command, pair_id=pair_id)
        rebuilt = AppleCommand.from_raw_timings(source.get_raw_timings())
        assert rebuilt is not None
        assert (rebuilt.command, rebuilt.pair_id) == (command, pair_id)

    @pytest.mark.parametrize("command", [0x00, 0x01, 0x2F, 0x7F])
    @pytest.mark.parametrize("pair_id", [0x01, 0x2E, 0x37])
    def test_parity_is_recomputed_not_round_tripped(self, command, pair_id):
        """Derived on encode, never stored.

        Asserted against a freshly computed popcount rather than against
        whatever the encoder produced, so this fails if the rule and the
        encoder ever drift apart.
        """
        source = AppleCommand(command=command, pair_id=pair_id)
        byte3, byte4 = source.byte3, pair_id
        ones = bin(byte3).count("1") + bin(byte4).count("1")
        assert ones % 2 == 1
        assert byte3 >> 1 == command

    def test_the_command_split_agrees_across_two_pairing_ids(self):
        """One button, two remotes, two byte3 values, one command.

        This is the shape of the cross-source evidence: the measured
        frames carry pairing id 0x01 and the repo's Flipper fixture
        carries 0x2E, and the six shared buttons resolve to the same
        command through different third bytes.
        """
        for _name, command in SHARED_BUTTONS.items():
            paired_one = AppleCommand(command=command, pair_id=0x01)
            flipper = AppleCommand(command=command, pair_id=0x2E)
            assert paired_one.command == flipper.command == command
            decoded_a = AppleCommand.from_raw_timings(
                paired_one.get_raw_timings())
            decoded_f = AppleCommand.from_raw_timings(
                flipper.get_raw_timings())
            assert decoded_a is not None and decoded_f is not None
            assert decoded_a.command == decoded_f.command == command
            assert decoded_a.pair_id == 0x01
            assert decoded_f.pair_id == 0x2E

    def test_out_of_range_fields_are_refused(self):
        with pytest.raises(ValueError, match="0x7F"):
            AppleCommand(command=0x80, pair_id=0)
        with pytest.raises(ValueError, match="0xFF"):
            AppleCommand(command=0, pair_id=0x100)
        with pytest.raises(ValueError, match="0x87EE"):
            AppleCommand(command=0, pair_id=0, address=0x87E5)


class TestAppleGates:
    def test_a_frame_at_another_apple_address_is_refused(self):
        """0x87E5 and 0x87E0 are other Apple products, not the remote.

        Nine rows of the sampled codeset carry them and none satisfies
        the parity rule, so both gates refuse independently. Built here
        at 0x87E5 with the parity rule deliberately satisfied, so what
        refuses it is the address pin alone.
        """
        good = AppleCommand(command=0x0D, pair_id=0x01)
        timings = list(good.get_raw_timings())
        # Rewrite byte 2 from 0x87 to 0x87E5's high byte, keeping parity.
        rebuilt = _bytes_of(timings)
        rebuilt[0] = 0xE5
        frame = [9000, -4500]
        for byte in rebuilt:
            for bit in range(8):
                frame += [562, -1687 if (byte >> bit) & 1 else -562]
        frame.append(562)
        assert AppleCommand.from_raw_timings(frame) is None

    @pytest.mark.parametrize("command", [0x00, 0x12, 0x5E, 0xFF])
    def test_a_complement_valid_frame_can_never_be_apple(self, command):
        """The disjointness proof, exercised rather than trusted.

        popcount(x) + popcount(~x) is 8 for any byte, which is even, and
        the parity rule demands odd. So no strict NEC frame at Apple's
        address can reach this decoder, whatever the probe order.
        """
        timings = _nec32(APPLE_ADDRESS, command)
        # The half that matters on BOTH legs: the Apple gate refuses it.
        assert AppleCommand.from_raw_timings(timings) is None
        identity = try_decode_identity(timings)
        if not strict_nec_available():
            assert identity is None, "no NEC decoder on this leg"
            return
        assert identity is not None
        assert identity.protocol == "NEC"

    def test_the_proof_holds_for_every_byte(self):
        for byte3 in range(256):
            byte4 = (~byte3) & 0xFF
            ones = bin(byte3).count("1") + bin(byte4).count("1")
            assert ones == 8 and ones % 2 == 0

    def test_a_frame_that_keeps_going_is_refused(self):
        source = AppleCommand(command=0x01, pair_id=0x2E)
        extended = [*source.get_raw_timings(), -562, 562, -1687, 562]
        assert AppleCommand.from_raw_timings(extended) is None

    def test_a_truncated_frame_is_refused(self):
        source = AppleCommand(command=0x01, pair_id=0x2E)
        assert AppleCommand.from_raw_timings(
            source.get_raw_timings()[:-8]) is None


class TestAppleDittos:
    def test_repeat_count_emits_markers_and_not_whole_frames(self):
        """A ditto is the same press still held, not a second press.

        The ditto knob is widened to this family, and a gate that admits
        a protocol whose encoder duplicates frames is worse than no
        gate. Lengths: 67, then 4 more per marker.
        """
        lengths = [
            len(AppleCommand(
                command=0x01, pair_id=0x2E, repeat_count=n
            ).get_raw_timings())
            for n in (0, 1, 3)
        ]
        assert lengths == [67, 71, 79]

    def test_two_markers_are_read_back_and_counted(self):
        source = AppleCommand(command=0x01, pair_id=0x2E, repeat_count=2)
        timings = source.get_raw_timings()
        markers = [
            index for index in range(len(timings) - 2)
            if timings[index] == 9000 and timings[index + 1] == -2250
        ]
        assert len(markers) == 2
        rebuilt = AppleCommand.from_raw_timings(timings)
        assert rebuilt is not None
        assert rebuilt.repeat_count == 2
        assert rebuilt.frames_explained == 3


class TestAppleIdentity:
    def test_fingerprint_carries_the_pairing_suffix(self):
        source = AppleCommand(command=0x01, pair_id=0x2E)
        identity = try_decode_identity(source.get_raw_timings())
        assert identity is not None
        assert identity.fingerprint == "APPLE:0x87ee:0x01:p2e"
        assert identity.extras == {"pair_id": 0x2E}

    def test_two_pairing_ids_are_two_identities(self):
        one = try_decode_identity(
            AppleCommand(command=0x01, pair_id=0x2E).get_raw_timings())
        two = try_decode_identity(
            AppleCommand(command=0x01, pair_id=0x37).get_raw_timings())
        assert one is not None and two is not None
        assert one.address == two.address and one.command == two.command
        assert one.fingerprint != two.fingerprint

    def test_rebuild_reproduces_the_wire_exactly(self):
        source = AppleCommand(command=0x2F, pair_id=0x2E)
        rebuilt = build_protocol_command(
            "APPLE", APPLE_ADDRESS, 0x2F, extras={"pair_id": 0x2E})
        assert rebuilt is not None
        assert rebuilt.get_raw_timings() == source.get_raw_timings()

    def test_a_capture_covers_itself(self):
        source = AppleCommand(command=0x01, pair_id=0x2E)
        identity = try_decode_identity(source.get_raw_timings())
        assert identity is not None
        assert identity.covers_capture is True
