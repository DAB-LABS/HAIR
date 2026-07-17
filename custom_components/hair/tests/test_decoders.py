"""Tests for the local decoder package (shave-and-a-haircut).

Three layers per protocol:

1. Encoder parity -- the local encoder's output is byte-identical to the
   upstream ``infrared_protocols`` encoder (where upstream ships one), so
   the registry swapping between the classes can never change what is
   transmitted. Skipped on Python legs without the library.
2. Round-trips -- encode with either encoder, decode with the local
   decoder, recover the identical fields, including repeat counts from
   multi-frame captures.
3. Rejection -- clean frames of every other protocol, and NEC frames,
   must decode to None. Cross-protocol acceptance is how wrong-decoder
   bugs corrupt stored identities, so the full matrix is asserted.

Dirty-capture cases (receiver jitter, truncated tails, vendor preamble
frames) are built from the field reports that motivated each decoder.
"""
from __future__ import annotations

import importlib.util
import itertools

import pytest

from custom_components.hair.decoders.kaseikyo import KaseikyoCommand
from custom_components.hair.decoders.marantz_extended import MarantzExtendedCommand
from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.samsung import Samsung32Command
from custom_components.hair.decoders.sharp import SharpCommand
from custom_components.hair.decoders.sony import SonyCommand
from custom_components.hair.decoders.symphony import SymphonyCommand

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None

_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)


# ---------------------------------------------------------------------------
# 1. Encoder parity with upstream
# ---------------------------------------------------------------------------


@_needs_library
class TestEncoderParity:
    """Local encoders are byte-identical to upstream encoders."""

    def test_sony(self):
        from infrared_protocols.commands.sony import SonyCommand as Upstream

        for address_bits, address, command in (
            (5, 0x01, 0x15),
            (8, 0xA5, 0x69),
            (13, 0x1A5A, 0x2E),
        ):
            local = SonyCommand(
                address=address, address_bits=address_bits, command=command
            )
            upstream = Upstream(
                address=address, address_bits=address_bits, command=command
            )
            assert local.get_raw_timings() == upstream.get_raw_timings()
            assert local.modulation == upstream.modulation

    def test_rc5_standard_and_rc5x(self):
        from infrared_protocols.commands.rc5 import RC5Command as Upstream

        for address, command, toggle, repeats in (
            (5, 0x35, 1, 0),
            (0x1F, 0x75, 0, 2),  # bit 6 set: RC5X encoding
            (0, 0, 0, 1),
        ):
            local = RC5Command(
                address=address, command=command, toggle=toggle, repeat_count=repeats
            )
            upstream = Upstream(
                address=address, command=command, toggle=toggle, repeat_count=repeats
            )
            assert local.get_raw_timings() == upstream.get_raw_timings()
            assert local.modulation == upstream.modulation

    def test_samsung(self):
        from infrared_protocols.commands.samsung import Samsung32Command as Upstream

        for address, command, repeats in ((0x07, 0x02, 0), (0x1234, 0xAB, 2)):
            local = Samsung32Command(
                address=address, command=command, repeat_count=repeats
            )
            upstream = Upstream(address=address, command=command, repeat_count=repeats)
            assert local.get_raw_timings() == upstream.get_raw_timings()

    def test_sharp(self):
        from infrared_protocols.commands.sharp import SharpCommand as Upstream

        local = SharpCommand(address=0x01, command=0x68, extension=1)
        upstream = Upstream(address=0x01, command=0x68, extension=1)
        assert local.get_raw_timings() == upstream.get_raw_timings()

    def test_kaseikyo(self):
        from infrared_protocols.commands.kaseikyo import KaseikyoCommand as Upstream

        payload = bytes([0x40, 0x04, 0x01, 0x00])
        local = KaseikyoCommand(address=0x2002, data=payload, repeat_count=1)
        upstream = Upstream(address=0x2002, data=payload, repeat_count=1)
        assert local.get_raw_timings() == upstream.get_raw_timings()

    def test_marantz(self):
        from infrared_protocols.commands.marantz_extended import (
            MarantzExtendedCommand as Upstream,
        )

        local = MarantzExtendedCommand(
            address=0x10, command=0x0C, extension=0x20, toggle=1, repeat_count=2
        )
        upstream = Upstream(
            address=0x10, command=0x0C, extension=0x20, toggle=1, repeat_count=2
        )
        assert local.get_raw_timings() == upstream.get_raw_timings()


# ---------------------------------------------------------------------------
# 2. Round-trips
# ---------------------------------------------------------------------------


class TestRoundTrips:
    """encode -> decode recovers identical fields."""

    @pytest.mark.parametrize(
        ("address_bits", "address", "command"),
        [(5, 0x01, 0x15), (8, 0xA5, 0x69), (13, 0x1A5A, 0x2E), (5, 0, 0)],
    )
    def test_sony(self, address_bits, address, command):
        encoded = SonyCommand(
            address=address, address_bits=address_bits, command=command
        ).get_raw_timings()
        decoded = SonyCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert (decoded.address, decoded.address_bits, decoded.command) == (
            address,
            address_bits,
            command,
        )
        assert decoded.repeat_count == 0

    def test_sony_multi_frame_repeats(self):
        encoded = SonyCommand(
            address=0xA5, address_bits=8, command=0x69, repeat_count=3
        ).get_raw_timings()
        decoded = SonyCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert decoded.repeat_count == 3
        assert (decoded.address, decoded.command) == (0xA5, 0x69)

    @pytest.mark.parametrize(
        ("address", "command", "toggle"),
        [(5, 0x35, 1), (0x1F, 0x75, 0), (0, 0, 0), (0x0A, 0x40, 1)],
    )
    def test_rc5(self, address, command, toggle):
        encoded = RC5Command(
            address=address, command=command, toggle=toggle
        ).get_raw_timings()
        decoded = RC5Command.from_raw_timings(encoded)
        assert decoded is not None
        assert (decoded.address, decoded.command, decoded.toggle) == (
            address,
            command,
            toggle,
        )

    def test_rc5_repeats(self):
        encoded = RC5Command(
            address=5, command=0x35, toggle=1, repeat_count=2
        ).get_raw_timings()
        decoded = RC5Command.from_raw_timings(encoded)
        assert decoded is not None
        assert decoded.repeat_count == 2

    @pytest.mark.parametrize(
        ("address", "command"),
        [(0x07, 0x02), (0x1234, 0xAB), (0, 0), (0xFF, 0xFF)],
    )
    def test_samsung(self, address, command):
        encoded = Samsung32Command(address=address, command=command).get_raw_timings()
        decoded = Samsung32Command.from_raw_timings(encoded)
        assert decoded is not None
        assert (decoded.address, decoded.command) == (address, command)

    def test_samsung_repeats(self):
        encoded = Samsung32Command(
            address=0x07, command=0x02, repeat_count=2
        ).get_raw_timings()
        decoded = Samsung32Command.from_raw_timings(encoded)
        assert decoded is not None
        assert decoded.repeat_count == 2

    @pytest.mark.parametrize(
        ("address", "command", "extension"),
        [(0x01, 0x68, 1), (0x1F, 0x00, 0), (0, 0xFF, 0)],
    )
    def test_sharp(self, address, command, extension):
        encoded = SharpCommand(
            address=address, command=command, extension=extension
        ).get_raw_timings()
        decoded = SharpCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert (decoded.address, decoded.command, decoded.extension) == (
            address,
            command,
            extension,
        )

    def test_sharp_lone_halves_decode_to_same_identity(self):
        """The 40ms mid-pair trailer splits real captures, so each half
        must decode alone -- and both halves of one press must agree
        (field finding: Sharp hardware via the Athom receiver delivers
        one half per capture)."""
        full = SharpCommand(
            address=0x01, command=0x68, extension=0
        ).get_raw_timings()
        # The pair is two 32-entry frames; split them apart.
        data_half, inverted_half = full[:32], full[32:]
        a = SharpCommand.from_raw_timings(data_half)
        b = SharpCommand.from_raw_timings(inverted_half)
        assert a is not None and b is not None
        assert (a.address, a.command, a.extension) == (0x01, 0x68, 0)
        assert (b.address, b.command, b.extension) == (0x01, 0x68, 0)

    def test_sharp_real_capture_fixtures(self):
        """Real Sharp-remote captures (test-bench Athom receiver,
        2026-07-17): lone inverted halves with receiver-shifted mark
        widths (342us and 263us against the nominal 320us)."""
        real = {
            # (address, command, extension) -> Pronto capture
            (0x01, 0x14, 1): (
                "0000 006D 0010 0000 000D 0042 000D 001A 000D 001A 000D "
                "001A 000D 001A 000D 0042 000D 0042 000D 001A 000D 0042 "
                "000D 001A 000D 0042 000D 0042 000D 0042 000D 001A 000D "
                "0042 000D 017C"
            ),
            (0x11, 0x4B, 1): (
                "0000 006D 0010 0000 000A 0046 000A 001E 000A 001E 000A "
                "001E 000A 0046 000A 001E 000A 001E 000A 0046 000A 001E "
                "000A 0046 000A 0046 000A 001E 000A 0046 000A 001E 000A "
                "0046 000A 017C"
            ),
        }
        for (address, command, extension), code in real.items():
            words = [int(w, 16) for w in code.split()]
            period = words[1] * 0.241246
            raw: list[int] = []
            for i in range(words[2]):
                mark, space = words[4 + 2 * i], words[5 + 2 * i]
                raw.append(round(mark * period))
                if space:
                    raw.append(-round(space * period))
            decoded = SharpCommand.from_raw_timings(raw)
            assert decoded is not None, f"real capture {address:#x} refused"
            assert (decoded.address, decoded.command, decoded.extension) == (
                address,
                command,
                extension,
            )

    def test_sharp_mark_constancy_rejects_mixed_marks(self):
        """With the check bit spent on half-detection, mark constancy is
        the structural gate: a 15-pair frame whose marks vary wildly is
        not Sharp."""
        frame: list[int] = []
        for i in range(15):
            frame.append(320 if i % 2 else 640)  # alternating mark widths
            frame.append(-680)
        frame.append(320)
        assert SharpCommand.from_raw_timings(frame) is None

    def test_sharp_repeats(self):
        encoded = SharpCommand(
            address=0x01, command=0x68, extension=1, repeat_count=1
        ).get_raw_timings()
        decoded = SharpCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert decoded.repeat_count == 1

    @pytest.mark.parametrize(
        ("address", "payload"),
        [
            (0x2002, bytes([0x40, 0x04, 0x01, 0x00])),  # Panasonic-shaped, 48-bit
            (0x0301, bytes([0xF0, 0xAA])),
        ],
    )
    def test_kaseikyo(self, address, payload):
        encoded = KaseikyoCommand(address=address, data=payload).get_raw_timings()
        decoded = KaseikyoCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert decoded.address == address
        assert bytes(decoded.data) == payload

    def test_kaseikyo_data_low_nibble_is_parity_domain(self):
        """The constructor discards data[0]'s low nibble; decode returns 0 there."""
        encoded = KaseikyoCommand(
            address=0x2002, data=bytes([0x4F, 0x04])
        ).get_raw_timings()
        decoded = KaseikyoCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert bytes(decoded.data) == bytes([0x40, 0x04])
        # Re-encoding reproduces the identical wire frame.
        assert (
            KaseikyoCommand(
                address=0x2002, data=bytes(decoded.data)
            ).get_raw_timings()
            == encoded
        )

    def test_kaseikyo_nec_style_repeats(self):
        encoded = KaseikyoCommand(
            address=0x2002, data=bytes([0x40, 0x04, 0x01, 0x00]), repeat_count=2
        ).get_raw_timings()
        decoded = KaseikyoCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert decoded.repeat_count == 2

    @pytest.mark.parametrize(
        ("address", "command", "extension", "toggle"),
        [(0x10, 0x0C, 0x20, 1), (0x10, 0x4C, 0x20, 1), (0, 0, 0, 0)],
    )
    def test_marantz(self, address, command, extension, toggle):
        encoded = MarantzExtendedCommand(
            address=address, command=command, extension=extension, toggle=toggle
        ).get_raw_timings()
        decoded = MarantzExtendedCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert (
            decoded.address,
            decoded.command,
            decoded.extension,
            decoded.toggle,
        ) == (address, command, extension, toggle)

    def test_symphony(self):
        encoded = SymphonyCommand(data=0xC00, nbits=12, repeat_count=3).get_raw_timings()
        decoded = SymphonyCommand.from_raw_timings(encoded)
        assert decoded is not None
        assert (decoded.data, decoded.nbits, decoded.repeat_count) == (0xC00, 12, 3)

    def test_symphony_rejects_single_frame(self):
        """No checksum, so one frame is not enough evidence."""
        encoded = SymphonyCommand(data=0xC00, nbits=12).get_raw_timings()
        assert SymphonyCommand.from_raw_timings(encoded) is None

    def test_symphony_majority_discards_vendor_preambles(self):
        """Real remotes send 0x000 / 0xFFF preamble frames first (GH #38)."""
        preamble_a = SymphonyCommand(data=0x000, nbits=12).get_raw_timings()
        preamble_b = SymphonyCommand(data=0xFFF, nbits=12).get_raw_timings()
        button = SymphonyCommand(data=0xC00, nbits=12, repeat_count=4).get_raw_timings()
        decoded = SymphonyCommand.from_raw_timings(preamble_a + preamble_b + button)
        assert decoded is not None
        assert (decoded.data, decoded.nbits) == (0xC00, 12)
        assert decoded.repeat_count == 4


# ---------------------------------------------------------------------------
# 3. Dirty captures: jitter, truncation, mixed frames
# ---------------------------------------------------------------------------


def _jitter(timings: list[int], stretch_marks_us: int, shrink_spaces_us: int) -> list[int]:
    """Simulate receiver AGC: marks stretch, spaces shrink."""
    out: list[int] = []
    for value in timings:
        if value > 0:
            out.append(value + stretch_marks_us)
        else:
            out.append(min(-1, value + shrink_spaces_us))
    return out


class TestDirtyCaptures:
    """Receiver-shaped distortions must not change decoded identity."""

    @pytest.mark.parametrize("stretch", [-120, -60, 60, 120, 180])
    def test_sony_jitter(self, stretch):
        clean = SonyCommand(
            address=0xA5, address_bits=8, command=0x69, repeat_count=2
        ).get_raw_timings()
        dirty = _jitter(clean, stretch, -stretch)
        decoded = SonyCommand.from_raw_timings(dirty)
        assert decoded is not None
        assert (decoded.address, decoded.command) == (0xA5, 0x69)

    def test_sony_truncated_tail_frame(self):
        """A capture window that cuts the last frame mid-bit still decodes."""
        clean = SonyCommand(
            address=0xA5, address_bits=8, command=0x69, repeat_count=2
        ).get_raw_timings()
        truncated = clean[:-7]  # chop into the final frame
        decoded = SonyCommand.from_raw_timings(truncated)
        assert decoded is not None
        assert (decoded.address, decoded.command) == (0xA5, 0x69)

    def test_sony_variable_frame_count_same_identity(self):
        """Hypothesis A from the field reports: 2-frame and 3-frame captures
        of one button must decode to the same identity."""
        two = SonyCommand.from_raw_timings(
            SonyCommand(
                address=0xA5, address_bits=8, command=0x69, repeat_count=1
            ).get_raw_timings()
        )
        three = SonyCommand.from_raw_timings(
            SonyCommand(
                address=0xA5, address_bits=8, command=0x69, repeat_count=2
            ).get_raw_timings()
        )
        assert two is not None and three is not None
        assert (two.address, two.address_bits, two.command) == (
            three.address,
            three.address_bits,
            three.command,
        )

    @pytest.mark.parametrize("stretch", [-100, 100, 200])
    def test_samsung_jitter(self, stretch):
        clean = Samsung32Command(address=0x07, command=0x02).get_raw_timings()
        decoded = Samsung32Command.from_raw_timings(_jitter(clean, stretch, -stretch))
        assert decoded is not None
        assert (decoded.address, decoded.command) == (0x07, 0x02)

    @pytest.mark.parametrize("stretch", [-100, 100, 200])
    def test_rc5_jitter(self, stretch):
        clean = RC5Command(address=5, command=0x35, toggle=1).get_raw_timings()
        decoded = RC5Command.from_raw_timings(_jitter(clean, stretch, -stretch))
        assert decoded is not None
        assert (decoded.address, decoded.command) == (5, 0x35)

    @pytest.mark.parametrize("stretch", [-60, 60, 120])
    def test_sharp_jitter(self, stretch):
        clean = SharpCommand(address=0x01, command=0x68).get_raw_timings()
        decoded = SharpCommand.from_raw_timings(_jitter(clean, stretch, -stretch))
        assert decoded is not None
        assert (decoded.address, decoded.command) == (0x01, 0x68)

    @pytest.mark.parametrize("stretch", [-80, 80, 140])
    def test_kaseikyo_jitter(self, stretch):
        clean = KaseikyoCommand(
            address=0x2002, data=bytes([0x40, 0x04, 0x01, 0x00])
        ).get_raw_timings()
        decoded = KaseikyoCommand.from_raw_timings(_jitter(clean, stretch, -stretch))
        assert decoded is not None
        assert decoded.address == 0x2002

    @pytest.mark.parametrize("stretch", [-100, 100, 200])
    def test_symphony_jitter(self, stretch):
        clean = SymphonyCommand(data=0xC00, nbits=12, repeat_count=3).get_raw_timings()
        decoded = SymphonyCommand.from_raw_timings(_jitter(clean, stretch, -stretch))
        assert decoded is not None
        assert (decoded.data, decoded.nbits) == (0xC00, 12)


# ---------------------------------------------------------------------------
# 4. Rejection matrix
# ---------------------------------------------------------------------------

_DECODERS = {
    "sony": SonyCommand,
    "rc5": RC5Command,
    "samsung": Samsung32Command,
    "sharp": SharpCommand,
    "kaseikyo": KaseikyoCommand,
    "marantz": MarantzExtendedCommand,
    "symphony": SymphonyCommand,
}


def _samples() -> dict[str, list[int]]:
    return {
        "sony": SonyCommand(
            address=0xA5, address_bits=8, command=0x69, repeat_count=2
        ).get_raw_timings(),
        "rc5": RC5Command(address=5, command=0x35, repeat_count=2).get_raw_timings(),
        "samsung": Samsung32Command(
            address=0x07, command=0x02, repeat_count=2
        ).get_raw_timings(),
        "sharp": SharpCommand(
            address=0x01, command=0x68, repeat_count=1
        ).get_raw_timings(),
        "kaseikyo": KaseikyoCommand(
            address=0x2002, data=bytes([0x40, 0x04, 0x01, 0x00]), repeat_count=1
        ).get_raw_timings(),
        "marantz": MarantzExtendedCommand(
            address=0x10, command=0x0C, extension=0x20, repeat_count=2
        ).get_raw_timings(),
        "symphony": SymphonyCommand(
            data=0xC00, nbits=12, repeat_count=3
        ).get_raw_timings(),
    }


class TestRejectionMatrix:
    """No decoder may accept another protocol's clean transmission."""

    @pytest.mark.parametrize(
        ("sample_name", "decoder_name"),
        [
            (s, d)
            for s, d in itertools.product(_DECODERS, _DECODERS)
            if s != d
        ],
    )
    def test_cross_rejection(self, sample_name, decoder_name):
        sample = _samples()[sample_name]
        assert _DECODERS[decoder_name].from_raw_timings(sample) is None

    @_needs_library
    @pytest.mark.parametrize("decoder_name", sorted(_DECODERS))
    def test_nec_rejected_by_all(self, decoder_name):
        from infrared_protocols.commands.nec import NECCommand

        nec = NECCommand(address=0x04, command=0x08, repeat_count=2).get_raw_timings()
        assert _DECODERS[decoder_name].from_raw_timings(nec) is None

    @pytest.mark.parametrize("decoder_name", sorted(_DECODERS))
    def test_garbage_rejected(self, decoder_name):
        assert _DECODERS[decoder_name].from_raw_timings([]) is None
        assert _DECODERS[decoder_name].from_raw_timings([100]) is None
        assert (
            _DECODERS[decoder_name].from_raw_timings([1000, -1000] * 200) is None
        )
