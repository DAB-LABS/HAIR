"""Tests for the RCA decoder (docs/internal/plans/rca-decoder.md).

The motivating field report: a TCL Google TV remote into an Athom
receiver minted a NEW Sniffer row on every press of one button, because
the remote re-sends the whole frame while held and the ~8.7 ms
inter-frame space is under HAIR's signal-end threshold -- so a 3-frame
train and a 5-frame train of the SAME payload landed as one capture
each with different S/L patterns. The cure is a decoded identity that
ignores frame count, which is what these tests pin.

The protocol's twelve-bit complement half is the only integrity check
it has, so it is asserted strictly everywhere: a single flipped bit
rejects the frame. There is deliberately no salvage tier.

The reporter's five verbatim captures are committed at
``fixtures/rca/forum-captures.json`` and drive ``TestForumCaptures``
below, which is the plan's acceptance condition: all five, at their
differing frame counts, must collapse to ONE identity with the
complement check strict.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from custom_components.hair.decoders.rca import RCACommand
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.protocol_decode import try_decode_identity

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None

_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)

# The timings the reporter's captures actually read, as recorded in the
# plan: header 4077/4077, 500us bit marks, 1000-1026us zero spaces,
# 2025-2050us one spaces, ~8700us between frames. Frames built from
# these exercise the decoder against observed values rather than
# against its own nominals.
_OBS_HEADER = 4077
_OBS_MARK = 500
_OBS_ZERO = 1026
_OBS_ONE = 2050
_OBS_GAP = 8700
# The button the reporter pressed: D=0xF, F=0x2A -> 0xF2A, complement
# 0x0D5, on the wire as 0xF2A0D5.
_OBS_DEVICE = 0xF
_OBS_FUNCTION = 0x2A

_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "rca" / "forum-captures.json").read_text()
)
_CAPTURES = _FIXTURES["captures"]


def _observed_frame(word24: int = 0xF2A0D5) -> list[int]:
    """One frame at the captured timings, MSB first, with trailer mark."""
    timings = [_OBS_HEADER, -_OBS_HEADER]
    for index in range(23, -1, -1):
        timings.append(_OBS_MARK)
        timings.append(-(_OBS_ONE if (word24 >> index) & 1 else _OBS_ZERO))
    timings.append(_OBS_MARK)
    return timings


def _observed_capture(frames: int, word24: int = 0xF2A0D5) -> list[int]:
    """``frames`` frames of one payload, separated by the ~8.7ms space."""
    capture: list[int] = []
    for index in range(frames):
        if index:
            capture.append(-_OBS_GAP)
        capture.extend(_observed_frame(word24))
    return capture


# ---------------------------------------------------------------------------
# Round trips
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        ("device", "function"),
        [
            (0xF, 0x2A),  # the reported button
            (0x0, 0x00),
            (0xF, 0xFF),
            (0x0, 0xFF),
            (0xF, 0x00),
            (0x5, 0x55),
            (0xA, 0xAA),
            (0x1, 0x80),
        ],
    )
    def test_device_function_lattice(self, device, function):
        encoded = RCACommand(device=device, function=function).get_raw_timings()
        decoded = RCACommand.from_raw_timings(encoded)
        assert decoded is not None
        assert (decoded.device, decoded.function) == (device, function)

    def test_full_lattice_is_bijective(self):
        """Every (D, F) pair in the protocol's whole domain decodes back
        to itself and to a distinct identity -- 4096 codes, no collisions."""
        seen: dict[tuple[int, int], int] = {}
        for device in range(16):
            for function in range(256):
                decoded = RCACommand.from_raw_timings(
                    RCACommand(device=device, function=function).get_raw_timings()
                )
                assert decoded is not None, f"D={device:#x} F={function:#04x}"
                key = (decoded.device, decoded.function)
                assert key not in seen or seen[key] == (device, function)
                seen[key] = (device, function)
        assert len(seen) == 16 * 256

    def test_constructor_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            RCACommand(device=0x10, function=0)
        with pytest.raises(ValueError):
            RCACommand(device=0, function=0x100)
        with pytest.raises(ValueError):
            RCACommand(device=-1, function=0)


# ---------------------------------------------------------------------------
# Wire format, derived by hand from the IRP
# ---------------------------------------------------------------------------


class TestWireFormat:
    def test_wire_format_pinned(self):
        """The exact frame for the reported button, D=0xF F=0x2A.

        IRP: {58k,460,msb}<1,-2|1,-4>(8,-8,D:4,F:8,~D:4,~F:8,1,-16)+

        D:4  = 0xF  = 1111
        F:8  = 0x2A = 0010 1010
        ~D:4 = 0x0  = 0000
        ~F:8 = 0xD5 = 1101 0101

        so the wire carries 1111 0010 1010 0000 1101 0101 = 0xF2A0D5,
        MSB first, each bit a 500us mark plus a 1000us (zero) or 2000us
        (one) space, wrapped in the 4ms/4ms header and closed by a
        trailer mark and the lead-out.
        """
        bits = [int(c) for c in "111100101010" "000011010101"]
        assert len(bits) == 24
        expected = [4000, -4000]
        for bit in bits:
            expected.append(500)
            expected.append(-2000 if bit else -1000)
        expected.extend([500, -8700])
        assert RCACommand(device=0xF, function=0x2A).get_raw_timings() == expected

    def test_complement_half_is_exact(self):
        """The second twelve bits are the bitwise complement of the
        first, for every code -- read straight off the encoder output."""
        for device, function in ((0, 0), (0xF, 0xFF), (0x9, 0x5C)):
            timings = RCACommand(
                device=device, function=function
            ).get_raw_timings()
            spaces = [-timings[3 + 2 * i] for i in range(24)]
            bits = [1 if space > 1500 else 0 for space in spaces]
            data = int("".join(str(b) for b in bits[:12]), 2)
            check = int("".join(str(b) for b in bits[12:]), 2)
            assert check == (~data & 0xFFF)
            assert data == (device << 8) | function

    def test_frame_duration_is_constant(self):
        """The complement half forces exactly twelve ones and twelve
        zeros, so every RCA frame is the same length on the wire --
        56.5ms of frame plus the 8.7ms lead-out, which is the ~64ms
        start-to-start period sbprojects documents."""
        durations = {
            sum(
                abs(t)
                for t in RCACommand(device=d, function=f).get_raw_timings()
            )
            for d, f in ((0, 0), (0xF, 0xFF), (0x3, 0x71), (0xC, 0x08))
        }
        assert durations == {65_200}


# ---------------------------------------------------------------------------
# The report's actual complaint: frame count must not be identity
# ---------------------------------------------------------------------------


class TestFrameCountIsNotIdentity:
    @pytest.mark.parametrize("frames", [1, 2, 3, 4, 5, 6, 9])
    def test_lone_and_multi_frame_captures_decode(self, frames):
        decoded = RCACommand.from_raw_timings(_observed_capture(frames))
        assert decoded is not None
        assert (decoded.device, decoded.function) == (_OBS_DEVICE, _OBS_FUNCTION)
        assert decoded.repeat_count == frames - 1

    def test_frame_count_is_not_identity(self):
        """Synthetic control for the acceptance test below: the
        reporter's press lengths, built from the plan's stated timings,
        collapse to one identity."""
        fingerprints = {
            try_decode_identity(_observed_capture(count)).fingerprint
            for count in (3, 4, 4, 5, 4)
        }
        assert fingerprints == {"RCA:0x000f:0x2a"}

    def test_receiver_jitter_across_frames_still_one_identity(self):
        """Real captures wobble frame to frame (the plan notes 0x26 /
        0x27 / 0x28 spaces in one train). Marks stretch, spaces shrink;
        the majority vote and the complement gate absorb it."""
        capture: list[int] = []
        for index, jitter in enumerate((-60, 0, 45, -30, 70)):
            if index:
                capture.append(-_OBS_GAP)
            for value in _observed_frame():
                capture.append(
                    value + jitter if value > 0 else min(-1, value - jitter)
                )
        identity = try_decode_identity(capture)
        assert identity is not None
        assert identity.fingerprint == "RCA:0x000f:0x2a"

    def test_one_bad_frame_does_not_poison_the_vote(self):
        """A truncated or corrupt frame in the middle of a train is
        dropped, not decoded -- the surviving frames still agree."""
        good = _observed_frame()
        corrupt = _observed_frame()
        # Flip bit 12, the first bit of the complement half (a zero in
        # this payload), so the halves no longer agree.
        corrupt[3 + 2 * 12] = -_OBS_ONE
        capture = [*good, -_OBS_GAP, *corrupt, -_OBS_GAP, *good]
        decoded = RCACommand.from_raw_timings(capture)
        assert decoded is not None
        assert (decoded.device, decoded.function) == (_OBS_DEVICE, _OBS_FUNCTION)
        assert decoded.repeat_count == 1  # two good frames voted


# ---------------------------------------------------------------------------
# The acceptance condition: the reporter's five captures
# ---------------------------------------------------------------------------


class TestForumCaptures:
    """The five verbatim Pronto captures from the forum report.

    One button, five presses, 3 / 4 / 4 / 5 / 4 frames. Before v0.11
    each of these minted a separate Sniffer row, because the whole
    train lands as ONE capture and a 3-frame train has a different S/L
    pattern than a 5-frame train. They must now be ONE identity.
    """

    def test_fixture_file_is_intact(self):
        """The transcription's own self-check, re-run at test time so a
        later edit to the fixture file cannot quietly corrupt it: each
        capture's third Pronto word is its pair count, and the total
        word count must be 4 + 2 x that."""
        assert [c["capture"] for c in _CAPTURES] == [1, 2, 3, 4, 5]
        assert [c["frames"] for c in _CAPTURES] == [3, 4, 4, 5, 4]
        for capture in _CAPTURES:
            words = capture["pronto"].split()
            assert all(len(w) == 4 for w in words)
            pairs = int(words[2], 16)
            assert len(words) == 4 + 2 * pairs
            assert int(words[0], 16) == 0
            assert int(words[3], 16) == 0
            # Frame count follows from the pair count: 26 pairs a frame
            # (header + 24 bits + trailer/lead-out).
            assert pairs == capture["frames"] * 26

    def test_captures_are_38khz_not_56khz(self):
        """Every capture's carrier word is 0x006D, ~38 kHz. This is the
        evidence behind the design rule: the re-encode uses what was
        captured and never snaps to the documented 56/58 kHz."""
        for capture in _CAPTURES:
            assert capture["pronto"].split()[1].upper() == "006D"

    @pytest.mark.parametrize("index", range(5))
    def test_each_capture_decodes(self, index):
        capture = _CAPTURES[index]
        timings = ProntoCommand(capture["pronto"]).get_raw_timings()
        decoded = RCACommand.from_raw_timings(timings)
        assert decoded is not None, f"capture {capture['capture']} failed"
        assert (decoded.device, decoded.function) == (_OBS_DEVICE, _OBS_FUNCTION)
        # repeat_count counts the extra agreeing frames, so every frame
        # in the train voted -- none was dropped as unreadable.
        assert decoded.repeat_count == capture["frames"] - 1

    def test_all_five_collapse_to_one_identity(self):
        """THE acceptance condition (plan section 3, fixture 1)."""
        identities = {}
        for capture in _CAPTURES:
            timings = ProntoCommand(capture["pronto"]).get_raw_timings()
            identity = try_decode_identity(timings)
            assert identity is not None, f"capture {capture['capture']}"
            identities[capture["capture"]] = identity.fingerprint
        assert set(identities.values()) == {"RCA:0x000f:0x2a"}, (
            f"frame count leaked into identity: {identities}"
        )

    def test_every_frame_satisfies_the_complement(self):
        """Twenty frames across the five captures, each read
        independently: all carry 0xF2A0D5 and all satisfy the 12-bit
        complement. Nothing here needs the check loosened."""
        frames_checked = 0
        for capture in _CAPTURES:
            timings = ProntoCommand(capture["pronto"]).get_raw_timings()
            for start in range(0, capture["frames"] * 52, 52):
                word = 0
                for bit in range(24):
                    space = -timings[start + 3 + 2 * bit]
                    word = (word << 1) | (1 if space > 1500 else 0)
                assert word == 0xF2A0D5
                assert (word & 0xFFF) == (~(word >> 12) & 0xFFF)
                frames_checked += 1
        assert frames_checked == 20

    def test_real_receiver_jitter_is_present(self):
        """The fixtures are real captures, not clean synthesis: the
        one-space appears as 0x4D and 0x4E and the zero-space as 0x26,
        0x27 and 0x28 within a single train. If this ever stops being
        true the fixtures have been regenerated, not transcribed."""
        words = set()
        for capture in _CAPTURES:
            words.update(capture["pronto"].split()[4:])
        assert {"004D", "004E"} <= words
        assert {"0026", "0027", "0028"} <= words

    def test_captures_do_not_decode_as_anything_else(self):
        """Pin the registry: RCA claims them, and before this decoder
        existed nothing did (plan section 1, verified on main)."""
        from custom_components.hair.protocol_decode import get_spec

        for capture in _CAPTURES:
            timings = ProntoCommand(capture["pronto"]).get_raw_timings()
            identity = try_decode_identity(timings)
            assert identity is not None
            assert identity.protocol == "RCA"
            assert get_spec(identity.protocol).key == "rca"

    def test_no_other_decoder_accepts_the_real_captures(self):
        """Plan fixture 3, the other direction, on the REAL captures
        rather than on a synthesized RCA frame: every other decoder in
        the package must return None."""
        from custom_components.hair.tests.test_decoders import _DECODERS

        for capture in _CAPTURES:
            timings = ProntoCommand(capture["pronto"]).get_raw_timings()
            for name, decoder in _DECODERS.items():
                if name == "rca":
                    continue
                assert decoder.from_raw_timings(timings) is None, (
                    f"{name} accepted RCA capture {capture['capture']}"
                )


# ---------------------------------------------------------------------------
# Rejection: the complement is the whole integrity story
# ---------------------------------------------------------------------------


class TestRejection:
    @pytest.mark.parametrize("bit_index", [0, 1, 5, 11, 12, 17, 23])
    def test_single_flipped_bit_rejects(self, bit_index):
        """Flipping ANY one of the 24 bits breaks the complement, in
        either half. No salvage: the frame is refused outright."""
        frame = _observed_frame()
        position = 3 + 2 * bit_index
        frame[position] = (
            -_OBS_ZERO if frame[position] == -_OBS_ONE else -_OBS_ONE
        )
        assert RCACommand.from_raw_timings(frame) is None

    def test_complement_violation_rejects_whole_capture(self):
        """Every frame in the train carrying the same corruption means
        no frame votes, so the capture stays undecoded rather than
        decoding to a plausible wrong identity."""
        word = 0xF2A0D4  # last bit of the complement half flipped
        assert RCACommand.from_raw_timings(_observed_capture(4, word)) is None
        assert try_decode_identity(_observed_capture(4, word)) is None

    @pytest.mark.parametrize("pairs", [23, 25, 12, 32])
    def test_wrong_bit_count_rejects(self, pairs):
        frame = [_OBS_HEADER, -_OBS_HEADER]
        for index in range(pairs):
            frame.append(_OBS_MARK)
            frame.append(-(_OBS_ONE if index % 2 else _OBS_ZERO))
        frame.append(_OBS_MARK)
        assert RCACommand.from_raw_timings(frame) is None

    @pytest.mark.parametrize("header", [9000, 2000, 6000, 500, 14720])
    def test_wrong_header_rejects(self, header):
        """Including RCA(Old)'s 32-unit (14720us) lead-in, which the plan
        puts out of scope: it must reject cleanly, never half-decode."""
        frame = _observed_frame()
        frame[0] = header
        assert RCACommand.from_raw_timings(frame) is None

    def test_missing_trailer_mark_rejects(self):
        frame = _observed_frame()[:-1]
        assert RCACommand.from_raw_timings(frame) is None

    def test_garbage_rejects(self):
        assert RCACommand.from_raw_timings([]) is None
        assert RCACommand.from_raw_timings([100]) is None
        assert RCACommand.from_raw_timings([1000, -1000] * 200) is None
        assert RCACommand.from_raw_timings([4000, -4000]) is None


# ---------------------------------------------------------------------------
# Frame splitting: the gap threshold is squeezed from both sides
# ---------------------------------------------------------------------------


class TestFrameSplitting:
    def test_header_space_is_not_a_frame_boundary(self):
        """RCA's header space is ~4ms, longer than most protocols' whole
        inter-frame gap. A splitter threshold at or below it cuts every
        frame in half at its own header -- the trap this decoder's
        6000us constant exists to avoid."""
        decoded = RCACommand.from_raw_timings(_observed_capture(2))
        assert decoded is not None
        assert decoded.repeat_count == 1

    def test_lead_out_is_a_frame_boundary(self):
        """Two frames glued without a gap must NOT decode as one; the
        splitter has to see the ~8.7ms lead-out."""
        fused = [*_observed_frame(), *_observed_frame()]
        assert RCACommand.from_raw_timings(fused) is None

    def test_jp1_lead_out_still_splits(self):
        """DecodeIR's IRP puts the lead-out at 16 units of 460us =
        7360us, shorter than the captured 8700us. Both must split."""
        capture = [*_observed_frame(), -7360, *_observed_frame()]
        decoded = RCACommand.from_raw_timings(capture)
        assert decoded is not None
        assert decoded.repeat_count == 1

    @pytest.mark.parametrize("mark", [421, 462, 504, 585, 665, 681])
    def test_agc_stretched_marks_decode(self, mark):
        """Real receivers lengthen marks. The Flipper-IRDB sweep put
        genuine RCA bit marks at 421..681us (p50 504), so the whole of
        that range must decode -- an earlier +/-30% band silently
        refused 18 real Thomson signals at the top of it."""
        word = 0xF2A0D5
        frame = [_OBS_HEADER, -_OBS_HEADER]
        for index in range(23, -1, -1):
            frame.append(mark)
            frame.append(-(_OBS_ONE if (word >> index) & 1 else _OBS_ZERO))
        frame.append(mark)
        decoded = RCACommand.from_raw_timings(frame)
        assert decoded is not None, f"{mark}us marks must decode"
        assert (decoded.device, decoded.function) == (_OBS_DEVICE, _OBS_FUNCTION)

    @pytest.mark.parametrize("unit", [834, 857, 886, 937])
    def test_longer_unit_sibling_family_rejects(self, unit):
        """The sweep surfaced a family sharing RCA's whole architecture
        -- 4-unit/4-unit header, 24 bits, valid 12-bit complement -- at
        a ~845us unit instead of ~500us (Hitachi MX421, Panasonic,
        Uniden, Funai, DMX). Plan section 8 puts other RCA timing
        variants out of scope, so these must reject cleanly rather than
        half-decode into the RCA namespace."""
        word = 0xF2A0D5
        frame = [4 * unit, -4 * unit]
        for index in range(23, -1, -1):
            frame.append(unit)
            frame.append(-(3 * unit if (word >> index) & 1 else unit))
        frame.append(unit)
        assert RCACommand.from_raw_timings(frame) is None

    def test_jp1_unit_timings_decode(self):
        """A handset built to the JP1 460us unit rather than sbprojects'
        round numbers -- header 3680, mark 460, spaces 920/1840 -- is
        the same protocol and must decode identically."""
        word = 0xF2A0D5
        frame = [3680, -3680]
        for index in range(23, -1, -1):
            frame.append(460)
            frame.append(-(1840 if (word >> index) & 1 else 920))
        frame.append(460)
        decoded = RCACommand.from_raw_timings(frame)
        assert decoded is not None
        assert (decoded.device, decoded.function) == (_OBS_DEVICE, _OBS_FUNCTION)


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_end_to_end_identity(self):
        identity = try_decode_identity(_observed_capture(4))
        assert identity is not None
        assert identity.protocol == "RCA"
        assert identity.address == 0xF
        assert identity.command == 0x2A
        assert identity.fingerprint == "RCA:0x000f:0x2a"
        assert identity.extras is None
        assert identity.source == "local"

    def test_tx_rebuild_round_trips(self):
        from custom_components.hair.protocol_decode import build_protocol_command

        cmd = build_protocol_command("RCA", 0xF, 0x2A)
        assert cmd is not None
        rebuilt = try_decode_identity(cmd.get_raw_timings())
        assert rebuilt is not None
        assert rebuilt.fingerprint == "RCA:0x000f:0x2a"

    def test_rebuild_uses_the_captured_carrier(self):
        """Design rule from the plan: never snap to the documented
        56/58 kHz on the strength of a spec sheet. DecodeIR documents
        RCA-38 at 38.7 kHz as a real variant, and the captures read
        ~38 kHz, so that is what the re-encode transmits at."""
        from custom_components.hair.protocol_decode import build_protocol_command

        assert build_protocol_command("RCA", 0xF, 0x2A).modulation == 38000

    def test_repeat_count_threads_to_tx(self):
        from custom_components.hair.ir_command import build_decoded_command

        cmd = build_decoded_command("RCA", 0xF, 0x2A, repeat_count=3)
        assert cmd is not None
        assert cmd.repeat_count == 3
        assert len(cmd.get_raw_timings()) == 4 * 52

    @_needs_library
    def test_no_upstream_rca_module_today(self):
        """The registry feature-detects rather than version-pinning, so
        this is a fact about the pinned library, not a requirement: if
        upstream ever ships commands.rca with from_raw_timings, HAIR
        defers to it and this test is the thing that says so out loud."""
        assert importlib.util.find_spec("infrared_protocols") is not None
        found = importlib.util.find_spec("infrared_protocols.commands.rca")
        assert found is None, "upstream now ships RCA -- re-check the spec"
