"""Reading Tuya compressed IR (UFO-R11).

A Tuya blaster stores a code as base64 of a FastLZ level-1 stream whose
plaintext is a little-endian uint16 array of microsecond durations. HAIR
reads that container, converts to ordinary timings, and from there the
code is Pronto like any other: portable to any emitter, and matched like
any capture.

The fixture is lluisd's file from GH #108, which is where this came
from: a SmartIR climate file for a Cecotec ForceClima 12650 that
declares ``commandsEncoding: "Raw"`` and carries Tuya. Before the
reader, 33 of 33 values were unreadable. After it, 33 of 33 read.

ON THE FRAMES THEMSELVES. They carry NEC-family timings (a 9000/4500
leader and a ~560 us unit) but they are 56-bit air-conditioner state
frames, not 32-bit NEC, so HAIR's decoder registry does not name them
and they stay undecoded. That is ordinary for AC state codes and costs
nothing here: transmit works from timings, and identity works from the
byte hash and the fingerprint. The tests below assert the shape that is
real rather than a decode that is not.
"""
from __future__ import annotations

import base64
import json
import statistics
import struct
from pathlib import Path

import pytest

from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.tuya_ir import (
    MAX_INFLATED_BYTES,
    fastlz_decompress,
    tuya_b64_to_pronto,
    tuya_b64_to_timings,
)
from custom_components.hair.wig_adapters import (
    _smartir_code_to_pronto,
    broadlink_packet_to_pronto,
    convert,
    sniff_format,
)

FIXTURES = Path(__file__).parent / "fixtures" / "gh108"
FILE = FIXTURES / "cecotec-forceclima-12650.json"


def _values() -> list[tuple[str, str]]:
    """Every code value in his file, labelled by where it sits."""
    data = json.loads(FILE.read_text())
    out = [("off", data["commands"]["off"])]
    for fan in ("low", "high"):
        for temp, code in data["commands"]["cool"][fan].items():
            out.append((f"cool/{fan}/{temp}", code))
    return out


def _broadlink_ir_packet() -> str:
    """A real-shaped Broadlink IR packet, base64, built here.

    Type 0x26, repeat 0, little-endian payload length, then tick
    durations in 2^-15 s units. Used to prove the Tuya reader keeps its
    hands off something that belongs to another reader.
    """
    ticks = []
    for value in [9000, 4500] + [560, 1690] * 8 + [560]:
        t = max(1, round(value / 32.84))
        ticks.extend([0x00, t >> 8, t & 0xFF] if t > 255 else [t])
    payload = bytes(ticks)
    packet = bytes([0x26, 0x00, len(payload) & 0xFF, len(payload) >> 8])
    return base64.b64encode(packet + payload).decode()


# --------------------------------------------------------- the container


class TestTheContainer:
    def test_every_value_in_his_file_reads(self):
        values = _values()
        assert len(values) == 33
        unread = [label for label, code in values
                  if tuya_b64_to_timings(code) is None]
        assert unread == []

    def test_the_frames_are_nec_shaped_state_frames(self):
        """The shape the GH #108 report measured, pinned.

        31 of the 33 are a textbook 56-bit frame. ``cool/low/16`` is the
        same state sent twice in one code (113 bits by this count), and
        ``cool/high/17`` is two edges short at 55 bits, which is how it
        sits in his file: a slightly clipped recording, read faithfully
        rather than padded out.
        """
        for label, code in _values():
            timings = tuya_b64_to_timings(code)
            lead_mark, lead_space = timings[0], -timings[1]
            assert 8500 <= lead_mark <= 9600, label
            assert 4100 <= lead_space <= 4800, label
            bits = (len(timings) - 3) // 2
            assert bits in (55, 56, 113), f"{label} carried {bits} bits"
            # The TYPICAL unit, not the shortest one: these are real
            # captures and carry real jitter. cool/low/25 holds a single
            # 177 us edge in an otherwise textbook 586 us frame, which
            # is the recording, not the reader.
            units = [abs(v) for v in timings[2:-1] if abs(v) < 1200]
            assert 350 <= statistics.median(units) <= 700, label

    def test_a_code_round_trips_through_pronto(self):
        """Timings in, Pronto out, the same timings back within the
        rounding the Pronto unit imposes. This is the portability
        claim in miniature: what came out of the container is a code
        any emitter can send."""
        for label, code in _values():
            timings = tuya_b64_to_timings(code)
            pronto = tuya_b64_to_pronto(code)
            assert pronto, label
            back = list(ProntoCommand(pronto).get_raw_timings())
            assert len(back) == len(timings), label
            for original, returned in zip(timings, back, strict=True):
                assert (original > 0) == (returned > 0), label
                assert abs(abs(original) - abs(returned)) <= 30, label

    def test_the_carrier_is_38_khz(self):
        pronto = tuya_b64_to_pronto(_values()[0][1])
        assert pronto.split()[1].lower() == "006d"

    def test_a_code_ends_on_a_mark(self):
        for label, code in _values():
            timings = tuya_b64_to_timings(code)
            assert timings[-1] > 0, label
            assert len(timings) % 2 == 1, label


# ------------------------------------------------------------ the importer


class TestTheImporter:
    def test_his_file_imports_with_zero_receipts(self):
        text = FILE.read_text()
        assert sniff_format(text) == "smartir_climate"
        result = convert(text, "cecotec-forceclima-12650.json")
        assert result.error is None
        assert result.skipped == []
        wig = result.wigs[0]
        # 33 values: one off code and a 2 x 16 cool lattice.
        assert wig.climate.off
        assert len(wig.climate.cells) == 32

    def test_the_container_is_found_by_content_not_by_the_label(self):
        """His file says "Raw", which means a decimal timing list and is
        not what it carries. The reader is offered the value anyway."""
        code = _values()[0][1]
        for declared in ("raw", "base64", "", "tuya"):
            pronto, reason = _smartir_code_to_pronto(code, declared)
            assert reason is None, declared
            assert pronto, declared

    def test_a_broadlink_packet_still_takes_the_broadlink_branch(self):
        packet = _broadlink_ir_packet()
        assert tuya_b64_to_timings(packet) is None
        pronto, reason = _smartir_code_to_pronto(packet, "base64")
        assert reason is None
        assert pronto
        assert pronto == broadlink_packet_to_pronto(base64.b64decode(packet))

    def test_a_genuine_raw_timing_list_still_takes_the_raw_branch(self):
        pronto, reason = _smartir_code_to_pronto(
            "9000, 4500, 560, 560, 560, 1690, 560, 560", "raw"
        )
        assert reason is None
        assert pronto and pronto.startswith("0000 ")


# ------------------------------------------------------------------- fuzz


def _payload() -> bytes:
    return base64.b64decode(_values()[0][1])


class TestMalformedInputIsRefusedNotRaised:
    def test_truncation_at_every_length(self):
        """Every prefix of a real payload: none may raise or hang."""
        raw = _payload()
        for cut in range(1, len(raw)):
            code = base64.b64encode(raw[:cut]).decode()
            result = tuya_b64_to_timings(code)
            assert result is None or isinstance(result, list)

    def test_every_single_bit_flip(self):
        """A flipped bit may read as a shorter code, or as nothing. It
        may not raise, and it may not produce something enormous."""
        raw = _payload()
        for index in range(len(raw)):
            for bit in range(8):
                mutated = bytearray(raw)
                mutated[index] ^= 1 << bit
                code = base64.b64encode(bytes(mutated)).decode()
                result = tuya_b64_to_timings(code)
                if result is not None:
                    assert len(result) <= MAX_INFLATED_BYTES // 2

    @pytest.mark.parametrize(
        "code",
        [
            "",
            "   ",
            "not base64 at all!!",
            "AAAA",
            "////////",
            base64.b64encode(b"\x00").decode(),
            base64.b64encode(b"\x1f" + b"A" * 4).decode(),
        ],
    )
    def test_junk_reads_as_nothing(self, code):
        assert tuya_b64_to_timings(code) is None
        assert tuya_b64_to_pronto(code) is None

    def test_a_back_reference_before_the_start_is_refused(self):
        """The classic decompressor hole: a match pointing behind the
        output buffer. Refused rather than read from nowhere."""
        assert fastlz_decompress(bytes([0x20, 0xFF])) is None

    def test_a_truncated_match_is_refused(self):
        assert fastlz_decompress(bytes([0xE0])) is None
        assert fastlz_decompress(bytes([0xE0, 0x05])) is None

    def test_a_truncated_literal_is_refused(self):
        assert fastlz_decompress(bytes([0x05, 0x01, 0x02])) is None

    def test_output_is_capped(self):
        """A tiny stream that would inflate forever stops at the cap
        instead of eating memory."""
        stream = bytes([0x00, 0x41]) + bytes([0xE0, 0xFF, 0x00]) * 4096
        assert fastlz_decompress(stream) is None

    def test_a_stream_that_inflates_to_implausible_timings_is_refused(self):
        """Inflating is not the same as being a code."""
        blob = struct.pack("<8H", *([1] * 8))
        literal = bytes([len(blob) - 1]) + blob
        assert fastlz_decompress(literal) == blob
        assert tuya_b64_to_timings(base64.b64encode(literal).decode()) is None

    def test_an_odd_byte_count_is_refused(self):
        blob = struct.pack("<4H", 9000, 4500, 560, 560) + b"\x01"
        literal = bytes([len(blob) - 1]) + blob
        assert tuya_b64_to_timings(base64.b64encode(literal).decode()) is None
