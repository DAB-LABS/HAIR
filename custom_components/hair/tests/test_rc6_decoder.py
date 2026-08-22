"""Tests for the RC-6 decoder (GH #33, MaxRower's VU+ type VI remote).

The cross-protocol rejection matrix for RC-6 lives with every other
decoder's in ``test_decoders.py``; this file carries what is specific to
RC-6: the two mode shapes, the double-width trailer, the real capture
fixtures, and the toggle's ride on the existing per-press machinery.

The four Pronto codes are MaxRower's, posted verbatim in the GH #33
thread: two presses of the VU+ down button, each press learned as two
jittered rows by his ESPHome receiver. They are committed exactly as he
posted them, so the fixtures stay auditable against the thread.
"""
from __future__ import annotations

import pytest

from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.rc6 import RC6Command
from custom_components.hair.protocol_decode import (
    build_protocol_command,
    format_fingerprint,
    get_spec,
    registered_protocols,
    try_decode_identity,
)

# --- MaxRower's captures, GH #33 -------------------------------------------

_PRESS_1_ROW_1 = (
    "0000 006D 001E 0000 0068 0020 0013 000E 0013 000F 0013 0020 0013 0020"
    " 0034 0020 0013 0011 0011 0012 0011 0011 0012 0011 0011 0012 0011 0012"
    " 0011 0012 0021 0022 0021 0022 0011 0012 0022 0022 0011 0011 0011 0012"
    " 0011 0012 0021 0022 0011 0012 0011 0012 0011 0012 0011 0011 0022 0023"
    " 0021 0012 0011 0022 0011 0012 0021 017C"
)
_PRESS_1_ROW_2 = (
    "0000 006D 001E 0000 0065 0022 0012 0011 0011 0012 0011 0022 0011 0022"
    " 0032 0022 0011 0012 0011 0012 0011 0011 0011 0012 0011 0012 0011 0012"
    " 0011 0011 0023 0022 0021 0022 0011 0012 0021 0022 0012 0011 0011 0012"
    " 0011 0012 0021 0022 0011 0012 0011 0012 0011 0011 0011 0012 0022 0022"
    " 0021 0012 0011 0022 0011 0012 0021 017C"
)
_PRESS_2_ROW_1 = (
    "0000 006D 001D 0000 0068 0020 0014 000F 0013 000F 0013 0020 0013 0021"
    " 0034 0020 0013 000F 0013 0010 0012 0011 0011 0012 0011 0012 0011 0011"
    " 0011 0012 0021 0023 0022 0022 0011 0012 0021 0022 0021 0024 0011 0011"
    " 0023 0022 0011 0011 0012 0011 0011 0012 0010 0012 0021 0022 0022 0011"
    " 0011 0022 0011 0012 0022 017C"
)
_PRESS_2_ROW_2 = (
    "0000 006D 001D 0000 0065 0022 0011 0012 0011 0012 0011 0023 0011 0022"
    " 0032 0022 0011 0012 0011 0012 0011 0011 0011 0012 0011 0012 0011 0011"
    " 0012 0011 0022 0022 0021 0022 0011 0012 0021 0022 0022 0022 0011 0012"
    " 0021 0023 0011 0012 0011 0011 0011 0011 0012 0011 0022 0022 0021 0012"
    " 0011 0022 0011 0012 0021 017C"
)

_MAXROWER_PRESS_1 = (_PRESS_1_ROW_1, _PRESS_1_ROW_2)
_MAXROWER_PRESS_2 = (_PRESS_2_ROW_1, _PRESS_2_ROW_2)
_MAXROWER_ALL = _MAXROWER_PRESS_1 + _MAXROWER_PRESS_2

# His remote is a VU+ set-top box handset: RC-6 mode 6A, 16-bit customer.
_VU_CUSTOMER = 0x8052
_VU_ADDRESS = 0x10
_VU_DOWN = 0x59


def _build_frame(symbols: list[tuple[int, int]]) -> list[int]:
    """Build RC-6 timings from explicit ``(bit, half_width_units)`` symbols.

    A second, deliberately naive implementation of the wire rules, used to
    construct frames the encoder will not produce (a mode 6B submode, a
    trailer at the wrong width). Merging adjacent same-sign halves is the
    whole of the wire format, so this stays a few lines and does not
    borrow anything from the module under test.
    """
    unit = 444
    timings: list[int] = [6 * unit, -2 * unit]  # leader
    for bit, width in symbols:
        halves = [width * unit, -width * unit] if bit else [-width * unit, width * unit]
        for half in halves:
            if timings and (timings[-1] > 0) == (half > 0):
                timings[-1] += half
            else:
                timings.append(half)
    if timings[-1] < 0:
        timings.pop()
    return timings


def _bits(value: int, width: int) -> list[tuple[int, int]]:
    """MSB-first single-width symbols for ``value``."""
    return [((value >> shift) & 1, 1) for shift in range(width - 1, -1, -1)]


def _pronto_to_us(text: str) -> list[int]:
    """Convert a learned (0000) Pronto hex string to signed us timings."""
    words = [int(w, 16) for w in text.split()]
    assert words[0] == 0, "learned Pronto only"
    unit = words[1] * 0.241246
    body = words[4:]
    return [
        round(w * unit) if i % 2 == 0 else -round(w * unit)
        for i, w in enumerate(body)
    ]


# ---------------------------------------------------------------------------
# Round trips
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Encode then decode recovers every field, in both modes."""

    @pytest.mark.parametrize("address", [0x00, 0x05, 0x7F, 0xC3, 0xFF])
    @pytest.mark.parametrize("command", [0x00, 0x0C, 0x59, 0xFF])
    @pytest.mark.parametrize("toggle", [0, 1])
    def test_mode_0(self, address, command, toggle):
        cmd = RC6Command(address=address, command=command, toggle=toggle)
        back = RC6Command.from_raw_timings(cmd.get_raw_timings())
        assert back is not None
        assert (back.mode, back.customer) == (0, None)
        assert (back.address, back.command, back.toggle) == (
            address, command, toggle,
        )

    @pytest.mark.parametrize(
        "customer",
        [0x00, 0x52, 0x7F, 0x8000, 0x800F, _VU_CUSTOMER, 0xFFFF],
    )
    @pytest.mark.parametrize("address", [0x00, 0x10, 0x74, 0x7F])
    @pytest.mark.parametrize("command", [0x00, 0x0C, _VU_DOWN, 0xFF])
    @pytest.mark.parametrize("toggle", [0, 1])
    def test_mode_6(self, customer, address, command, toggle):
        cmd = RC6Command(
            address=address, command=command, toggle=toggle,
            mode=6, customer=customer,
        )
        back = RC6Command.from_raw_timings(cmd.get_raw_timings())
        assert back is not None
        assert (back.mode, back.customer) == (6, customer)
        assert (back.address, back.command, back.toggle) == (
            address, command, toggle,
        )

    def test_repeat_count_counts_extra_agreeing_frames(self):
        cmd = RC6Command(
            address=_VU_ADDRESS, command=_VU_DOWN, toggle=1,
            mode=6, customer=_VU_CUSTOMER, repeat_count=3,
        )
        back = RC6Command.from_raw_timings(cmd.get_raw_timings())
        assert back is not None
        assert back.repeat_count == 3
        assert back.address == _VU_ADDRESS

    def test_lone_frame_decodes_standalone(self):
        """A single frame with no repeats must decode on its own.

        MaxRower learns two rows per press, which means his receiver
        hands us frames one at a time rather than as a multi-frame
        capture -- a decoder that needed two agreeing frames would
        reject every row he has.
        """
        cmd = RC6Command(
            address=_VU_ADDRESS, command=_VU_DOWN,
            mode=6, customer=_VU_CUSTOMER, repeat_count=0,
        )
        timings = cmd.get_raw_timings()
        back = RC6Command.from_raw_timings(timings)
        assert back is not None
        assert back.repeat_count == 0
        assert (back.address, back.command) == (_VU_ADDRESS, _VU_DOWN)


class TestFieldValidation:
    """The constructor refuses field values that have no wire form."""

    def test_mode_must_be_0_or_6(self):
        with pytest.raises(ValueError):
            RC6Command(address=1, command=1, mode=3)

    def test_mode_0_takes_no_customer(self):
        with pytest.raises(ValueError):
            RC6Command(address=1, command=1, mode=0, customer=0x800F)

    def test_mode_6_requires_a_customer(self):
        with pytest.raises(ValueError):
            RC6Command(address=1, command=1, mode=6)

    @pytest.mark.parametrize("customer", [0x80, 0x100, 0x7FFF, 0x10000, -1])
    def test_customer_outside_either_field_width_is_refused(self, customer):
        """The field's first bit signals its length, so 0x80..0x7FFF has
        no encoding: too big for the 7-bit value behind a leading 0, and
        without the leading 1 that would buy the 15-bit form."""
        with pytest.raises(ValueError):
            RC6Command(address=1, command=1, mode=6, customer=customer)

    def test_mode_6_address_is_seven_bits(self):
        """Mode 6 spends the top payload bit on the toggle, so an
        address of 0x80 or more cannot be represented."""
        with pytest.raises(ValueError):
            RC6Command(address=0x80, command=1, mode=6, customer=_VU_CUSTOMER)

    def test_mode_0_address_is_eight_bits(self):
        RC6Command(address=0xFF, command=1, mode=0)
        with pytest.raises(ValueError):
            RC6Command(address=0x100, command=1, mode=0)

    def test_command_is_eight_bits(self):
        with pytest.raises(ValueError):
            RC6Command(address=1, command=0x100, mode=0)


# ---------------------------------------------------------------------------
# Wire format pin
# ---------------------------------------------------------------------------


def test_wire_format_pin_mode_0():
    """One explicit timing vector, hand-derived from the protocol.

    Fields: mode 0, address 0x00, command 0x00, toggle 0. Unit t = 444us.

    Symbols, before any merging (RC-6 polarity: 1 is mark-then-space,
    0 is space-then-mark)::

        leader                 M6 S2
        start bit    1         M1 S1
        mode bit 2   0         S1 M1
        mode bit 1   0         S1 M1
        mode bit 0   0         S1 M1
        trailer      0  (2t)   S2 M2
        D and F      sixteen 0 bits, each S1 M1

    Adjacent same-sign halves then merge on the wire. Only two merges
    happen here: the start bit's trailing space runs into mode bit 2's
    leading space (S1+S1 = S2), and nothing else abuts a same-sign
    neighbour, because a 0 bit ends on a mark and the next 0 bit opens
    on a space. The trailer therefore stands alone as a clean 2t space
    followed by a clean 2t mark. The final bit ends on a mark, so no
    trailing idle is stripped.
    """
    timings = RC6Command(address=0x00, command=0x00, toggle=0).get_raw_timings()
    assert timings == [
        2664, -888,          # leader: 6t mark, 2t space
        444, -888,           # start bit's mark, then S1+S1 merged
        444, -444,           # mode bit 2
        444, -444,           # mode bit 1
        444, -888,           # mode bit 0's mark, then the trailer's 2t space
        888,                 # the trailer's 2t mark
        *([-444, 444] * 16),  # D=0x00 and F=0x00, sixteen 0 bits
    ]


def test_wire_format_total_duration_pins_the_double_width_trailer():
    """The trailer costs 4t, not 2t, and the whole frame's length says so.

    A mode 0 frame is leader 8t + start 2t + mode 6t + trailer 4t +
    sixteen data bits 32t = 52t. A decoder or encoder that treated the
    trailer as an ordinary bit would produce 50t, which this catches
    without depending on where any individual merge falls.
    """
    timings = RC6Command(address=0x00, command=0x00, toggle=0).get_raw_timings()
    assert sum(abs(t) for t in timings) == 52 * 444


def test_wire_format_leader_is_the_rc5_discriminator():
    """RC-5 has no leader; RC-6 opens with 6t mark + 2t space."""
    rc6 = RC6Command(address=0x00, command=0x00).get_raw_timings()
    assert rc6[0] == 6 * 444
    assert rc6[1] == -2 * 444
    rc5 = RC5Command(address=0x00, command=0x00).get_raw_timings()
    assert rc5[0] < 3 * 444


# ---------------------------------------------------------------------------
# The double-width trailer
# ---------------------------------------------------------------------------


class TestTrailerWidth:
    """The trailer's 2t halves are modelled explicitly, not quantized."""

    def test_trailer_mark_merges_with_a_following_one_bit(self):
        """The 3t run that only RC-6 produces.

        Mode 6 with a 16-bit customer puts a 1 bit (mark-first) straight
        after the trailer, so the trailer's 2t mark absorbs it into a 3t
        run. That run is why a two-bucket short/long classifier cannot
        slice this protocol, and why the frame-gap constant has to clear
        3t rather than 2t.
        """
        timings = RC6Command(
            address=0x00, command=0x00, mode=6, customer=0x8000,
        ).get_raw_timings()
        assert 3 * 444 in timings
        assert max(abs(t) for t in timings[2:]) == 3 * 444

    def test_trailer_mark_stands_alone_before_a_zero_bit(self):
        """With a 0 bit (space-first) after it, the trailer's 2t mark is
        undisguised by any merge."""
        timings = RC6Command(
            address=0x00, command=0x00, mode=6, customer=0x00,
        ).get_raw_timings()
        assert 2 * 444 in timings

    def test_post_trailer_bits_survive_the_width_change(self):
        """The regression this pins: a uniform half-bit quantizer reads
        the trailer's four halves as two bits and misaligns every data
        bit after it, which silently yields a plausible wrong identity
        rather than a rejection. Sweeping the byte-wide command through
        values whose bit runs straddle the trailer catches that."""
        for command in range(0x100):
            cmd = RC6Command(address=0x2A, command=command, toggle=1)
            back = RC6Command.from_raw_timings(cmd.get_raw_timings())
            assert back is not None, f"command {command:#04x} failed to decode"
            assert back.command == command
            assert back.address == 0x2A
            assert back.toggle == 1

    def test_the_independent_builder_agrees_with_the_encoder(self):
        """Guard on the guard: the naive builder used by the next two
        tests must reproduce the encoder exactly for a frame both can
        express, or its negative results would prove nothing."""
        built = _build_frame(
            [(1, 1), (0, 1), (0, 1), (0, 1), (1, 2), *_bits(0x2A, 8), *_bits(0x59, 8)]
        )
        assert built == RC6Command(
            address=0x2A, command=0x59, toggle=1
        ).get_raw_timings()

    def test_trailer_at_single_width_is_rejected(self):
        """A frame identical in every way except that its trailer is
        transmitted at 1t must not decode. Accepting it would mean the
        walk is quantizing uniformly rather than reading the trailer at
        its declared width -- and a uniform read of a real frame silently
        produces a plausible wrong identity."""
        symbols = [(1, 1), (0, 1), (0, 1), (0, 1), (1, 2)]
        symbols += [*_bits(0x2A, 8), *_bits(0x59, 8)]
        assert RC6Command.from_raw_timings(_build_frame(symbols)) is not None

        narrowed = list(symbols)
        narrowed[4] = (1, 1)  # trailer at ordinary width
        assert RC6Command.from_raw_timings(_build_frame(narrowed)) is None

    def test_mode_6b_submode_is_not_a_command_frame(self):
        """In mode 6 the trailer is the submode bit, not a toggle: 0 is
        mode 6A, the command form, and 1 is mode 6B, reserved for
        pointing devices. A 6B frame must not decode as a command."""
        payload = [*_bits(_VU_CUSTOMER, 16), (0, 1), *_bits(_VU_ADDRESS, 7)]
        payload += _bits(_VU_DOWN, 8)
        mode_6 = [(1, 1), (1, 1), (1, 1), (0, 1)]

        as_6a = _build_frame([*mode_6, (0, 2), *payload])
        assert RC6Command.from_raw_timings(as_6a) is not None

        as_6b = _build_frame([*mode_6, (1, 2), *payload])
        assert RC6Command.from_raw_timings(as_6b) is None


# ---------------------------------------------------------------------------
# MaxRower's fixtures
# ---------------------------------------------------------------------------


class TestMaxRowerFixtures:
    """GH #33: four captures, one identity, two toggle values."""

    @pytest.mark.parametrize("pronto", _MAXROWER_ALL)
    def test_every_capture_decodes(self, pronto):
        cmd = RC6Command.from_raw_timings(_pronto_to_us(pronto))
        assert cmd is not None
        assert cmd.mode == 6
        assert cmd.customer == _VU_CUSTOMER
        assert cmd.address == _VU_ADDRESS
        assert cmd.command == _VU_DOWN

    def test_all_four_collapse_to_one_identity(self):
        decoded = [
            RC6Command.from_raw_timings(_pronto_to_us(p)) for p in _MAXROWER_ALL
        ]
        assert all(c is not None for c in decoded)
        identities = {
            (c.mode, c.customer, c.address, c.command) for c in decoded
        }
        assert identities == {(6, _VU_CUSTOMER, _VU_ADDRESS, _VU_DOWN)}

    def test_exactly_two_toggle_values_split_along_press_boundaries(self):
        press_1 = {
            RC6Command.from_raw_timings(_pronto_to_us(p)).toggle
            for p in _MAXROWER_PRESS_1
        }
        press_2 = {
            RC6Command.from_raw_timings(_pronto_to_us(p)).toggle
            for p in _MAXROWER_PRESS_2
        }
        # Both rows of one press agree; the two presses differ.
        assert len(press_1) == 1
        assert len(press_2) == 1
        assert press_1 != press_2
        assert press_1 | press_2 == {0, 1}

    def test_the_toggle_is_the_only_difference_between_the_presses(self):
        """The point of the whole exercise: MaxRower sees two catalog
        rows per button because the presses differ. They differ in the
        toggle and in nothing else, so excluding the toggle from
        identity is what collapses them."""
        one = RC6Command.from_raw_timings(_pronto_to_us(_PRESS_1_ROW_1))
        two = RC6Command.from_raw_timings(_pronto_to_us(_PRESS_2_ROW_1))
        assert one.toggle != two.toggle
        assert (one.mode, one.customer, one.address, one.command) == (
            two.mode, two.customer, two.address, two.command,
        )

    @pytest.mark.parametrize("pronto", _MAXROWER_ALL)
    def test_captures_do_not_decode_as_rc5(self, pronto):
        assert RC5Command.from_raw_timings(_pronto_to_us(pronto)) is None

    @pytest.mark.parametrize("pronto", _MAXROWER_ALL)
    def test_capture_re_encodes_to_the_same_identity(self, pronto):
        """Canonical re-encode is what HAIR transmits, so a capture that
        decodes must survive the round trip back through the wire."""
        original = RC6Command.from_raw_timings(_pronto_to_us(pronto))
        rebuilt = RC6Command.from_raw_timings(original.get_raw_timings())
        assert rebuilt is not None
        assert (
            rebuilt.mode, rebuilt.customer, rebuilt.address,
            rebuilt.command, rebuilt.toggle,
        ) == (
            original.mode, original.customer, original.address,
            original.command, original.toggle,
        )


class TestRC5CapturesRejectAsRC6:
    """Neither Manchester format may claim the other's frames."""

    @pytest.mark.parametrize("address", [0x00, 0x05, 0x14, 0x1F])
    @pytest.mark.parametrize("command", [0x01, 0x35, 0x40, 0x7F])
    @pytest.mark.parametrize("toggle", [0, 1])
    def test_rc5_frames_are_not_rc6(self, address, command, toggle):
        rc5 = RC5Command(
            address=address, command=command, toggle=toggle, repeat_count=2,
        ).get_raw_timings()
        assert RC6Command.from_raw_timings(rc5) is None

    @pytest.mark.parametrize("mode,customer", [(0, None), (6, _VU_CUSTOMER)])
    def test_rc6_frames_are_not_rc5(self, mode, customer):
        rc6 = RC6Command(
            address=0x10, command=0x59, toggle=1, mode=mode, customer=customer,
            repeat_count=2,
        ).get_raw_timings()
        assert RC5Command.from_raw_timings(rc6) is None


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_rc6_is_registered_local(self):
        listing = {row["protocol"]: row for row in registered_protocols()}
        assert "rc6" in listing
        assert listing["rc6"]["source"] == "local"
        assert listing["rc6"]["tx_rebuild"] is True

    def test_rc6_probes_before_rc5(self):
        keys = [row["protocol"] for row in registered_protocols()]
        assert keys.index("rc6") < keys.index("rc5")

    def test_get_spec_resolves_rc6(self):
        spec = get_spec("RC6")
        assert spec is not None
        assert spec.key == "rc6"

    def test_identity_decodes_through_the_registry(self):
        identity = try_decode_identity(_pronto_to_us(_PRESS_1_ROW_1))
        assert identity is not None
        assert identity.protocol == "RC6"
        assert identity.address == _VU_ADDRESS
        assert identity.command == _VU_DOWN
        assert identity.extras == {
            "mode": 6, "toggle": 0, "customer": _VU_CUSTOMER,
        }

    def test_toggle_is_excluded_from_the_fingerprint(self):
        """The whole collapse depends on this: two presses, one
        fingerprint."""
        one = try_decode_identity(_pronto_to_us(_PRESS_1_ROW_1))
        two = try_decode_identity(_pronto_to_us(_PRESS_2_ROW_1))
        assert one.extras["toggle"] != two.extras["toggle"]
        assert one.fingerprint == two.fingerprint

    def test_all_four_captures_share_one_fingerprint(self):
        prints = {
            try_decode_identity(_pronto_to_us(p)).fingerprint
            for p in _MAXROWER_ALL
        }
        assert len(prints) == 1

    def test_mode_and_customer_are_identity(self):
        """Same address and command, different mode or customer, must be
        different signals -- otherwise a Media Center remote and a VU+
        box would land on one catalog row."""
        base = format_fingerprint(
            "RC6", _VU_ADDRESS, _VU_DOWN,
            {"mode": 6, "customer": _VU_CUSTOMER, "toggle": 0},
        )
        other_customer = format_fingerprint(
            "RC6", _VU_ADDRESS, _VU_DOWN,
            {"mode": 6, "customer": 0x800F, "toggle": 0},
        )
        mode_0 = format_fingerprint(
            "RC6", _VU_ADDRESS, _VU_DOWN, {"mode": 0, "toggle": 0},
        )
        assert base != other_customer
        assert base != mode_0
        assert other_customer != mode_0

    def test_fingerprint_ignores_toggle_only_changes(self):
        with_toggle = format_fingerprint(
            "RC6", _VU_ADDRESS, _VU_DOWN,
            {"mode": 6, "customer": _VU_CUSTOMER, "toggle": 1},
        )
        without = format_fingerprint(
            "RC6", _VU_ADDRESS, _VU_DOWN,
            {"mode": 6, "customer": _VU_CUSTOMER, "toggle": 0},
        )
        assert with_toggle == without

    @pytest.mark.parametrize(
        "extras",
        [
            {"mode": 6, "customer": _VU_CUSTOMER, "toggle": 1},
            {"mode": 0, "toggle": 1},
        ],
    )
    def test_build_protocol_command_rebuilds_for_tx(self, extras):
        address = _VU_ADDRESS if extras["mode"] == 6 else 0xC3
        cmd = build_protocol_command("RC6", address, _VU_DOWN, extras=extras)
        assert cmd is not None
        assert cmd.mode == extras["mode"]
        assert cmd.customer == extras.get("customer")
        assert cmd.address == address
        assert cmd.command == _VU_DOWN
        assert cmd.toggle == 1

    def test_rebuilt_command_transmits_the_captured_waveform(self):
        """Canonical re-encode must land back on the captured identity,
        which is what makes a HAIR send match the row it came from."""
        identity = try_decode_identity(_pronto_to_us(_PRESS_1_ROW_1))
        cmd = build_protocol_command(
            identity.protocol, identity.address, identity.command,
            extras=identity.extras,
        )
        assert cmd is not None
        again = try_decode_identity(cmd.get_raw_timings())
        assert again is not None
        assert again.fingerprint == identity.fingerprint


# ---------------------------------------------------------------------------
# Toggle rides the existing per-press machinery
# ---------------------------------------------------------------------------


class TestToggleFlipMachinery:
    """No new toggle code: RC-6 rides the v0.6.0 flip both send paths use.

    ``device_manager.async_send_command`` and
    ``signal_monitor.test_signal`` both flip any ``decoded_extras``
    entry named ``toggle`` once per logical press. These pin that RC-6's
    extras are shaped to ride it and that a flip produces the other real
    press, rather than re-testing the send paths themselves.
    """

    def test_extras_carry_a_toggle_key(self):
        identity = try_decode_identity(_pronto_to_us(_PRESS_1_ROW_1))
        assert "toggle" in identity.extras

    def test_flipping_extras_yields_the_other_press(self):
        first = try_decode_identity(_pronto_to_us(_PRESS_1_ROW_1))
        second = try_decode_identity(_pronto_to_us(_PRESS_2_ROW_1))

        extras = dict(first.extras)
        extras["toggle"] = int(extras["toggle"]) ^ 1  # the send-path flip
        assert extras["toggle"] == second.extras["toggle"]

        flipped = build_protocol_command(
            "RC6", first.address, first.command, extras=extras
        )
        assert flipped is not None
        # The re-encoded frame carries the second press's toggle and the
        # first press's identity, which is exactly what a second send
        # from HAIR should put on the air.
        again = try_decode_identity(flipped.get_raw_timings())
        assert again.extras["toggle"] == second.extras["toggle"]
        assert again.fingerprint == first.fingerprint

    def test_flip_is_an_involution(self):
        """Two presses return to the starting toggle, so a held-button
        pair of sends reproduces the two frames the remote emits."""
        identity = try_decode_identity(_pronto_to_us(_PRESS_1_ROW_1))
        toggle = int(identity.extras["toggle"])
        assert ((toggle ^ 1) ^ 1) == toggle

    def test_send_count_repeats_the_same_toggle(self):
        """send_count is whole-frame retransmission inside ONE logical
        press, so every frame in the burst carries the same toggle --
        the flip happens once, after the send loop."""
        cmd = RC6Command(
            address=_VU_ADDRESS, command=_VU_DOWN, toggle=1,
            mode=6, customer=_VU_CUSTOMER, repeat_count=3,
        )
        timings = cmd.get_raw_timings()
        back = RC6Command.from_raw_timings(timings)
        assert back is not None
        assert back.repeat_count == 3
        # Every frame in the capture agrees on the toggle, so the
        # majority vote is unanimous rather than split.
        assert back.toggle == 1


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------


class TestMalformedInput:
    @pytest.mark.parametrize(
        "timings",
        [
            [],
            [100],
            [2664],
            [2664, -888],
            [1000, -1000] * 200,
            [-888, 2664, 444, -444],       # starts on a space
            [2664, 888, 444, -444],        # leader space is a mark
        ],
    )
    def test_garbage_returns_none(self, timings):
        assert RC6Command.from_raw_timings(timings) is None

    def test_wrong_leader_width_is_rejected(self):
        timings = RC6Command(address=0x10, command=0x59).get_raw_timings()
        assert RC6Command.from_raw_timings(timings) is not None
        bad = list(timings)
        bad[0] = 444  # a 1t leader mark is not a leader
        assert RC6Command.from_raw_timings(bad) is None

    def test_start_bit_must_be_one(self):
        """The start bit is fixed at 1; a frame whose first symbol reads
        as 0 is not RC-6."""
        timings = RC6Command(address=0x10, command=0x59).get_raw_timings()
        bad = list(timings)
        bad[2] = -444          # turn the start bit's mark-then-space
        bad.insert(3, 444)     # into space-then-mark
        assert RC6Command.from_raw_timings(bad) is None

    def test_unsupported_payload_width_stays_undecoded(self):
        """Mode 6A does not encode its own length. Rather than guess at a
        width the family does not use, the decoder refuses -- an absent
        identity leaves the signal on the raw tiers, a wrong one would
        match the wrong command forever."""
        cmd = RC6Command(
            address=0x10, command=0x59, mode=6, customer=_VU_CUSTOMER,
        )
        timings = cmd.get_raw_timings()
        # Drop the final data bit, leaving a 15-bit remainder.
        truncated = timings[:-2]
        assert RC6Command.from_raw_timings(truncated) is None

    def test_a_run_longer_than_three_units_is_not_a_half_bit(self):
        """3t is the longest legal run inside a frame (a 2t trailer half
        abutting a 1t neighbour). Anything longer mid-frame is corruption,
        not a symbol."""
        timings = RC6Command(address=0x10, command=0x59).get_raw_timings()
        bad = list(timings)
        bad[4] = 4 * 444
        assert RC6Command.from_raw_timings(bad) is None
