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

import base64
import importlib.util
import itertools

import pytest

from custom_components.hair.decoders.kaseikyo import KaseikyoCommand
from custom_components.hair.decoders.marantz_extended import MarantzExtendedCommand
from custom_components.hair.decoders.nokia32 import Nokia32Command
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


def _broadlink_to_us(b64: str) -> list[int]:
    """Convert a Broadlink RM base64 IR payload to signed us timings."""
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    length = raw[2] | (raw[3] << 8)
    ticks = list(raw[4 : 4 + length])
    while ticks and ticks[-1] == 0:
        ticks = ticks[:-1]
    tick_us = 1_000_000 / 32768
    return [
        round(v * tick_us) if i % 2 == 0 else -round(v * tick_us)
        for i, v in enumerate(ticks)
    ]


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

    def test_nokia32(self):
        # Nokia32 is not in the released library yet (it lives on the
        # upstream branch from discussion #70), so unlike its siblings this
        # needs a per-module guard: _needs_library only proves the library
        # is installed, not that it ships this protocol.
        upstream_mod = pytest.importorskip(
            "infrared_protocols.commands.nokia32",
            reason="upstream library has no Nokia32 yet",
        )
        Upstream = upstream_mod.Nokia32Command

        for device, subdevice, function, extension, toggle in (
            (33, 160, 12, 38, 0),   # Foxtel iQ POWER
            (33, 160, 253, 38, 1),  # Foxtel iQ ACTIVE, toggled
            (0, 0, 0, 0, 0),
        ):
            local = Nokia32Command(
                device=device, subdevice=subdevice, function=function,
                extension=extension, toggle=toggle,
            )
            upstream = Upstream(
                device=device, subdevice=subdevice, function=function,
                extension=extension, toggle=toggle,
            )
            assert local.get_raw_timings() == upstream.get_raw_timings()
            assert local.modulation == upstream.modulation


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

    def test_kaseikyo_trailing_subgap_space_tolerated(self):
        """A small trailing space after the end pulse (below the frame-gap
        threshold, so it stays glued to the frame) must not be misread as
        a 49th bit's space -- field finding from bench loopback codes."""
        clean = KaseikyoCommand(
            address=0x2002, data=bytes([0x80, 0x00, 0x3D, 0xBD])
        ).get_raw_timings()
        # Replace the 10ms trailer-adjacent tail with a 368us stray space.
        assert clean[-1] > 0  # ends on the end pulse mark
        dirty = [*clean, -368]
        decoded = KaseikyoCommand.from_raw_timings(dirty)
        assert decoded is not None
        assert decoded.address == 0x2002
        assert bytes(decoded.data) == bytes([0x80, 0x00, 0x3D, 0xBD])

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

    @pytest.mark.parametrize(
        ("device", "subdevice", "function", "extension", "toggle"),
        [
            (33, 160, 12, 38, 0),    # Foxtel iQ POWER
            (33, 160, 16, 38, 0),    # Foxtel iQ VOLUME_UP
            (33, 160, 253, 38, 1),   # Foxtel iQ ACTIVE, toggle set
            (0, 0, 0, 0, 0),
            (0xFF, 0xFF, 0xFF, 0x7F, 1),
        ],
    )
    def test_nokia32(self, device, subdevice, function, extension, toggle):
        encoded = Nokia32Command(
            device=device, subdevice=subdevice, function=function,
            extension=extension, toggle=toggle,
        ).get_raw_timings()
        decoded = Nokia32Command.from_raw_timings(encoded)
        assert decoded is not None
        assert (
            decoded.device, decoded.subdevice, decoded.function,
            decoded.extension, decoded.toggle,
        ) == (device, subdevice, function, extension, toggle)

    def test_nokia32_held_button_multi_frame_same_identity(self):
        """Nokia32 has no repeat frame -- a held key just re-sends the whole
        frame on a ~100ms period. Three back-to-back frames (one toggle
        value, as a real hold keeps) must majority-vote to one identity."""
        one = Nokia32Command(
            device=33, subdevice=160, function=12, extension=38, toggle=1,
        ).get_raw_timings()
        held = [*one, -90000, *one, -90000, *one]
        decoded = Nokia32Command.from_raw_timings(held)
        assert decoded is not None
        assert (decoded.device, decoded.subdevice, decoded.function) == (33, 160, 12)
        assert (decoded.extension, decoded.toggle) == (38, 1)

    def test_nokia32_real_foxtel_captures(self):
        """Real Foxtel iQ remote captures (Broadlink RM, base64). Device 33 /
        subdevice 160 / system 38, verified bit-for-bit against the remote."""
        captures = {
            # function -> Broadlink base64 payload
            12: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBQkFCQUZBQkFAA0F",   # POWER
            16: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBQkFDwUJBQkFAA0F",   # VOLUME_UP
            32: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBQkFFAUJBQkFAA0F",   # CHANNEL_UP
            56: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBQkFGQUUBQkFAA0F",   # AV
            92: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBQ8FDwUZBQkFAA0F",   # SELECT
            142: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBRQFCQUZBRQFAA0F",  # FOXTEL
            204: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBRkFCQUZBQkFAA0F",  # TV_GUIDE
            253: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBRkFGQUZBQ8FAA0F",  # ACTIVE
            9: "JgAkAA4JBQkFFAUJBQ8FFAUUBQkFCQUJBRQFDwUUBQkFCQUUBQ8FAA0F",    # NUM_9
        }
        for function, payload in captures.items():
            timings = _broadlink_to_us(payload)
            decoded = Nokia32Command.from_raw_timings(timings)
            assert decoded is not None, f"real capture fn={function} refused"
            assert (decoded.device, decoded.subdevice, decoded.extension) == (
                33, 160, 38,
            )
            assert decoded.function == function

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

    # Nokia32's marks are a short 164us, so the 0.3 band is only +-49us --
    # tighter than the pulse-distance protocols. Real Foxtel captures sit
    # well inside it (see test_nokia32_real_foxtel_captures); this just
    # confirms symmetric in-band jitter does not shift identity.
    @pytest.mark.parametrize("stretch", [-40, -20, 40])
    def test_nokia32_jitter(self, stretch):
        clean = Nokia32Command(
            device=33, subdevice=160, function=12, extension=38,
        ).get_raw_timings()
        decoded = Nokia32Command.from_raw_timings(_jitter(clean, stretch, -stretch))
        assert decoded is not None
        assert (decoded.device, decoded.subdevice, decoded.function) == (33, 160, 12)


# ---------------------------------------------------------------------------
# 4. Rejection matrix
# ---------------------------------------------------------------------------

_DECODERS = {
    "sony": SonyCommand,
    "rc5": RC5Command,
    "samsung": Samsung32Command,
    "sharp": SharpCommand,
    "nokia32": Nokia32Command,
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
        "nokia32": Nokia32Command(
            device=33, subdevice=160, function=12, extension=38
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


# --- Samsung32 fused end pulse (v0.6.1 bench, Broadlink packet replay) ------


def test_samsung32_fused_end_pulse_real_capture():
    """Real loopback capture: Broadlink replayed the packet for the
    command's repeat_count with no junction gap, fusing the 560us end
    mark with the replay's 4500us leader into one ~4944us mark. Data
    and checksum are intact; the decode must survive the fused tail."""
    pairs = (
        "00A0 009F 0014 003B 0014 003B 0014 003A 0014 0013 0014 0013"
        " 0015 0013 0014 0013 0014 0013 0014 003B 0014 003A 0015 003A"
        " 0014 0013 0014 0013 0014 0013 0014 0013 0014 0013 0014 0013"
        " 0014 003B 0014 0012 0015 0012 0014 0013 0014 0013 0014 0013"
        " 0014 0013 0014 003B 0014 0013 0014 003B 0014 003A 0014 003B"
        " 0014 003B 0014 003B 0014 003B 00BC 017C"
    )
    unit = 0x6D * 0.241246
    words = [int(w, 16) for w in pairs.split()]
    timings = [
        round(w * unit) if i % 2 == 0 else -round(w * unit)
        for i, w in enumerate(words)
    ]
    cmd = Samsung32Command.from_raw_timings(timings)
    assert cmd is not None
    assert cmd.address == 0x0007


def test_samsung32_larger_fusion_real_capture():
    """Second real junction variant: ~6968us fused end mark. The end
    pulse has no upper bound once fusion is possible."""
    pairs = (
        "00A0 009F 0014 003B 0014 003B 0014 003A 0014 0013 0014 0013"
        " 0014 0013 0014 0013 0015 0012 0014 003B 0014 003A 0015 003A"
        " 0014 0013 0014 0013 0014 0013 0014 0013 0014 0013 0014 003B"
        " 0014 003A 0015 003A 0014 0013 0014 0013 0014 0013 0014 0013"
        " 0014 0013 0014 0013 0014 0013 0014 0013 0014 003A 0014 003B"
        " 0014 003B 0014 003B 0014 003B 0109 017C"
    )
    unit = 0x6D * 0.241246
    words = [int(w, 16) for w in pairs.split()]
    timings = [
        round(w * unit) if i % 2 == 0 else -round(w * unit)
        for i, w in enumerate(words)
    ]
    cmd = Samsung32Command.from_raw_timings(timings)
    assert cmd is not None
    assert cmd.address == 0x0007


def test_samsung32_fused_end_pulse_still_checksum_gated():
    """A fused tail does not loosen the gate: corrupt one command bit
    and the frame must still decode as nothing."""
    base = Samsung32Command(address=0x0007, command=0x07).get_raw_timings()
    # Fuse the end pulse as the junction artifact does.
    fused = [*base[:-1], base[-1] + 4500]
    assert Samsung32Command.from_raw_timings(fused) is not None
    # Now flip a command bit's space (bit 16 pair space index 3 + 2*16).
    corrupt = list(fused)
    idx = 3 + 2 * 16
    corrupt[idx] = -1690 if corrupt[idx] > -1125 else -560
    assert Samsung32Command.from_raw_timings(corrupt) is None


def test_samsung32_data_marks_keep_strict_bounds():
    """The fused allowance applies to the end pulse only; an oversized
    DATA mark still rejects the frame."""
    base = Samsung32Command(address=0x0007, command=0x07).get_raw_timings()
    bad = list(base)
    bad[2] = 4944  # first data mark
    assert Samsung32Command.from_raw_timings(bad) is None
