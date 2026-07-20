"""Tests for the v0.6.0 protocol decode registry.

Covers the multi-protocol decoder plan's acceptance set: registry
contents against the CI library version (finding B2), single-formatter
fingerprints with per-protocol suffix rules (N2/N3), end-to-end decode
through ``try_decode_identity``, TX rebuild dispatch including the
identity-only tier (B6), decoded_extras flow, and the field regression
that motivated the release: repeat presses of one Sony button must
produce ONE decoded identity regardless of frame count (hypothesis A)
or mark-width jitter (hypothesis B).
"""
from __future__ import annotations

import importlib.util

import pytest

from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.sharp import SharpCommand
from custom_components.hair.decoders.sony import SonyCommand
from custom_components.hair.decoders.symphony import SymphonyCommand
from custom_components.hair.ir_command import ProntoCommand, build_decoded_command
from custom_components.hair.protocol_decode import (
    build_protocol_command,
    format_fingerprint,
    get_spec,
    identity_from_command,
    registered_protocols,
    try_decode_identity,
)

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None
_HAS_GEAC = (
    importlib.util.find_spec("infrared_protocols.commands.general_electric")
    is not None
    if _HAS_LIBRARY
    else False
)

_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)

# Real SIRC-15 capture fixtures (loic.gouraud's remote family; see
# test_unified_identity for provenance). PASTED is the clean editor
# paste; RECEIVED is the live capture whose long marks crossed the S/L
# threshold (0x2E/0x2F -> 0x30/0x31) -- the byte_hash flip pair.
PASTED_YELLOW = (
    "0000 006D 0010 0000 005D 0016 002E 0017 002E 0017 002F 0016 0017 "
    "0017 0017 0017 002E 0017 0018 0016 002E 0017 002E 0017 002F 0016 "
    "0017 0017 002E 0017 0017 0017 0018 0016 002E 0181"
)
RECEIVED_YELLOW = PASTED_YELLOW.replace("002E", "0030").replace("002F", "0031")


# ---------------------------------------------------------------------------
# Registry contents (finding B2: a typo'd class name must show up here)
# ---------------------------------------------------------------------------


class TestRegistryContents:
    def test_expected_protocols_registered(self):
        listing = {row["protocol"]: row for row in registered_protocols()}

        # The seven decoder protocols are always present: upstream when
        # the bundled library decodes them (none as of 7.5.0), local
        # polyfill otherwise -- including on the no-library CI leg.
        for key in ("samsung32", "sony", "sharp", "marantz", "rc5",
                    "kaseikyo", "symphony"):
            assert key in listing, f"{key} missing from registry"
            assert listing[key]["source"] == "local"
            assert listing[key]["tx_rebuild"] is True

        # NEC is upstream-only (no local polyfill; the library has
        # decoded it since v0.4.0) so it registers only with the library.
        assert ("nec" in listing) == _HAS_LIBRARY
        if _HAS_LIBRARY:
            assert listing["nec"]["source"] == "upstream"
            assert listing["nec"]["tx_rebuild"] is True

        # GE-AC feature-detects the upstream decoder and registers on
        # the identity-only tier (finding B6).
        assert ("geac" in listing) == _HAS_GEAC
        if _HAS_GEAC:
            assert listing["geac"]["tx_rebuild"] is False

    def test_probe_order_strict_before_checksum_free(self):
        keys = [row["protocol"] for row in registered_protocols()]
        # The checksum-free tail: Dyson (15 strict-timed bits) then
        # Symphony (the loosest match in the registry) dead last.
        assert keys[-2:] == ["dyson", "symphony"]
        # Marantz (specific) probes before RC-5 (its generic parent).
        assert keys.index("marantz") < keys.index("rc5")

    def test_get_spec_resolves_variant_labels(self):
        assert get_spec("SONY15") is not None
        assert get_spec("SONY15").key == "sony"
        assert get_spec("KASEIKYO48").key == "kaseikyo"
        assert get_spec("SYMPHONY12").key == "symphony"
        assert get_spec("RC5").key == "rc5"
        assert get_spec("UNKNOWN99") is None
        assert get_spec(None) is None


# ---------------------------------------------------------------------------
# Fingerprint formatting (N2: one formatter; N3: per-protocol formats)
# ---------------------------------------------------------------------------


class TestFingerprints:
    def test_nec_format_byte_identical_to_v040(self):
        assert format_fingerprint("NEC", 0xFB04, 0x08) == "NEC:0xfb04:0x08"

    def test_sony_variant_in_label(self):
        identity = try_decode_identity(
            SonyCommand(address=0xA5, address_bits=8, command=0x69).get_raw_timings()
        )
        assert identity is not None
        assert identity.protocol == "SONY15"
        assert identity.fingerprint == "SONY15:0x00a5:0x69"

    def test_toggle_excluded_from_identity(self):
        """The same RC-5 button with flipped toggle is ONE identity."""
        a = try_decode_identity(
            RC5Command(address=5, command=0x35, toggle=0).get_raw_timings()
        )
        b = try_decode_identity(
            RC5Command(address=5, command=0x35, toggle=1).get_raw_timings()
        )
        assert a is not None and b is not None
        assert a.fingerprint == b.fingerprint
        assert a.extras == {"toggle": 0}
        assert b.extras == {"toggle": 1}

    def test_sharp_extension_is_identity(self):
        plain = try_decode_identity(
            SharpCommand(address=1, command=0x68, extension=0).get_raw_timings()
        )
        extended = try_decode_identity(
            SharpCommand(address=1, command=0x68, extension=1).get_raw_timings()
        )
        assert plain is not None and extended is not None
        assert plain.fingerprint != extended.fingerprint
        assert extended.fingerprint.endswith(":x1")
        assert not plain.fingerprint.endswith(":x1")


# ---------------------------------------------------------------------------
# The field regression: one button, one identity (GH forum reports)
# ---------------------------------------------------------------------------


class TestSonyFragmentationCured:
    def test_real_capture_pair_unifies_at_tier_1(self):
        """The v0.5.8 byte_hash flip pair now shares a decoded identity."""
        pasted = try_decode_identity(ProntoCommand(PASTED_YELLOW).get_raw_timings())
        received = try_decode_identity(
            ProntoCommand(RECEIVED_YELLOW).get_raw_timings()
        )
        assert pasted is not None, "clean Sony capture must decode"
        assert received is not None, "jittered Sony capture must decode"
        assert pasted.fingerprint == received.fingerprint
        assert pasted.protocol == "SONY15"

    def test_twelve_presses_one_identity(self):
        """loic's 12-rows regression: repeat presses with varying frame
        counts (hypothesis A) and mark jitter (hypothesis B) must all
        decode to a single identity."""
        fingerprints = set()
        for press in range(12):
            frames = press % 3  # 1-3 frames per capture
            jitter = (press % 5 - 2) * 60  # -120..+120us mark wobble
            clean = SonyCommand(
                address=0xA5, address_bits=8, command=0x69, repeat_count=frames
            ).get_raw_timings()
            dirty = [
                v + jitter if v > 0 else min(-1, v - jitter) for v in clean
            ]
            identity = try_decode_identity(dirty)
            assert identity is not None, f"press {press} failed to decode"
            fingerprints.add(identity.fingerprint)
        assert len(fingerprints) == 1, (
            f"one button fragmented into {len(fingerprints)} identities: "
            f"{sorted(fingerprints)}"
        )

    def test_four_colored_buttons_stay_distinct(self):
        """The v0.5.8 win is preserved: different buttons never merge."""
        codes = (0x52E9, 0x32E9, 0x72E9, 0x12E9)  # ESPHome bit order
        fingerprints = set()
        for wire in codes:
            # ESPHome logs MSB-first transmission order; rebuild the
            # (address, command) pair the way the decoder sees the wire.
            bits = [(wire >> i) & 1 for i in range(14, -1, -1)]
            command = 0
            for index, bit in enumerate(bits[:7]):
                command |= bit << index
            address = 0
            for index, bit in enumerate(bits[7:]):
                address |= bit << index
            identity = try_decode_identity(
                SonyCommand(
                    address=address, address_bits=8, command=command
                ).get_raw_timings()
            )
            assert identity is not None
            fingerprints.add(identity.fingerprint)
        assert len(fingerprints) == 4


# ---------------------------------------------------------------------------
# TX rebuild dispatch
# ---------------------------------------------------------------------------


class TestTxRebuild:
    @pytest.mark.parametrize(
        ("protocol", "address", "command", "extras"),
        [
            ("SONY15", 0xA5, 0x69, None),
            ("SONY12", 0x01, 0x15, None),
            ("SAMSUNG32", 0x07, 0x02, None),
            ("RC5", 5, 0x35, {"toggle": 1}),
            ("SHARP", 1, 0x68, {"extension": 1}),
            ("MARANTZ", 0x10, 0x0C, {"extension": 0x20, "toggle": 0}),
            ("KASEIKYO48", 0x2002, 0x40040100, None),
            ("SYMPHONY12", 0, 0xC00, None),
        ],
    )
    def test_rebuild_round_trips_identity(self, protocol, address, command, extras):
        cmd = build_protocol_command(protocol, address, command, extras=extras)
        assert cmd is not None, f"{protocol} must rebuild"
        rebuilt = try_decode_identity(cmd.get_raw_timings())
        # Symphony's single rebuilt frame is (correctly) below the
        # decoder's two-frame evidence bar; re-send once to decode.
        if rebuilt is None and protocol.startswith("SYMPHONY"):
            doubled = cmd.get_raw_timings() * 2
            rebuilt = try_decode_identity(doubled)
        assert rebuilt is not None
        assert rebuilt.protocol == protocol
        assert rebuilt.address == address
        assert rebuilt.command == command

    def test_unregistered_and_missing_fields_return_none(self):
        assert build_protocol_command("UNKNOWN", 1, 2) is None
        assert build_protocol_command(None, 1, 2) is None
        assert build_protocol_command("RC5", None, 2) is None
        assert build_protocol_command("SONY99", 1, 2) is None

    @pytest.mark.skipif(not _HAS_GEAC, reason="GE-AC needs upstream 6.x+")
    def test_geac_is_identity_only(self):
        assert build_protocol_command("GEAC", 0x01, 0x02) is None

    def test_build_decoded_command_threads_repeats_and_extras(self):
        cmd = build_decoded_command(
            "RC5", 5, 0x35, repeat_count=2, decoded_extras={"toggle": 1}
        )
        assert cmd is not None
        assert cmd.repeat_count == 2
        assert cmd.toggle == 1

    def test_kaseikyo_payload_survives_int_packing(self):
        """Leading-zero payload bytes round-trip through the packed int."""
        source = try_decode_identity(
            build_protocol_command(
                "KASEIKYO48", 0x2002, 0x00040100
            ).get_raw_timings()
        )
        assert source is not None
        assert source.protocol == "KASEIKYO48"
        assert source.command == 0x00040100


# ---------------------------------------------------------------------------
# identity_from_command (code library / pluckable surface)
# ---------------------------------------------------------------------------


class TestIdentityFromCommand:
    def test_local_instance_resolves(self):
        identity = identity_from_command(
            SonyCommand(address=0xA5, address_bits=8, command=0x69)
        )
        assert identity is not None
        assert identity.fingerprint == "SONY15:0x00a5:0x69"

    @_needs_library
    def test_upstream_encode_only_instance_resolves_by_class_name(self):
        """A pluckable built from the upstream (encode-only) SonyCommand
        still resolves to the sony spec and the same fingerprint."""
        from infrared_protocols.commands.sony import SonyCommand as Upstream

        identity = identity_from_command(
            Upstream(address=0xA5, address_bits=8, command=0x69)
        )
        assert identity is not None
        assert identity.fingerprint == "SONY15:0x00a5:0x69"

    def test_unknown_instance_returns_none(self):
        assert identity_from_command(object()) is None
        assert identity_from_command(None) is None


# ---------------------------------------------------------------------------
# Symphony end-to-end (GH #38 shape)
# ---------------------------------------------------------------------------


class TestSymphonyEndToEnd:
    def test_mvdwetering_shape_decodes_to_one_identity(self):
        """Preamble frames + variable button-frame counts, three captures
        of different lengths -> one identity (the 108/120/132-pair
        splitting reported in GH #38)."""
        fingerprints = set()
        for repeats in (7, 8, 9):
            capture = (
                SymphonyCommand(data=0x000, nbits=12).get_raw_timings()
                + SymphonyCommand(data=0xFFF, nbits=12).get_raw_timings()
                + SymphonyCommand(
                    data=0xC00, nbits=12, repeat_count=repeats
                ).get_raw_timings()
            )
            identity = try_decode_identity(capture)
            assert identity is not None
            assert identity.protocol == "SYMPHONY12"
            assert identity.command == 0xC00
            fingerprints.add(identity.fingerprint)
        assert len(fingerprints) == 1
