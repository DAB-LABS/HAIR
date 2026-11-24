"""An RM4 Pro capture is read by its header, not by its first byte.

An RM4 Pro writes a different first byte for each carrier it learned
on (0x78 at 315, 0xB0 at 433.42, 0xB1 at 433.92, ...), so the reader
knows the layout by its structure: byte 1 is 0xC0 and bytes 4 to 7 hold
a 300 to 950 MHz carrier in kHz. Before this, only 0xB1 got that
layout: a 315 capture was refused, and a 433.42 one was read from the
wrong offset and filed at 433.92.

Every packet here is synthetic, laid out the way the seven measured
carriers are: type byte, 0xC0, length, carrier, ticks, and the
1500-tick close.
"""
from __future__ import annotations

import base64

import pytest

from custom_components.hair import rf_paste

TICK_US = 1_000_000 / 32_768
SHORT, LONG, GAP = 350, 1050, 10850
BUTTON = "101100111000111100001010"

# The first byte an RM4 Pro writes for each carrier it was measured on.
CARRIERS = [
    (0x64, 305_000),
    (0x78, 315_000),
    (0x82, 320_000),
    (0xA0, 335_000),
    (0xB0, 433_420),
    (0xB1, 433_920),
    (0xBA, 438_000),
]


def _frame() -> list[int]:
    out: list[int] = []
    for bit in BUTTON:
        out += [LONG, -SHORT] if bit == "1" else [SHORT, -LONG]
    return [*out, SHORT, -GAP]


def _ticks(timings: list[int]) -> bytes:
    body = bytearray()
    for value in timings:
        ticks = round(abs(value) / TICK_US)
        body += bytes([ticks]) if ticks < 256 else bytes([0, ticks >> 8, ticks & 0xFF])
    return bytes(body)


def _capture(type_byte: int, khz: int, frames: int = 8) -> bytes:
    """An RM4 Pro capture: the length counts from byte 4, carrier included."""
    body = khz.to_bytes(4, "little") + _ticks(_frame() * frames) + bytes([0, 0x05, 0xDC])
    return bytes([type_byte, 0xC0]) + len(body).to_bytes(2, "little") + body


def _four_byte(type_byte: int, repeat: int, timings: list[int]) -> bytes:
    body = _ticks(timings)
    return bytes([type_byte, repeat]) + len(body).to_bytes(2, "little") + body


def _b64(packet: bytes) -> str:
    return base64.b64encode(packet).decode()


@pytest.mark.parametrize(("type_byte", "khz"), CARRIERS)
def test_every_measured_carrier_reads_with_its_own_carrier(type_byte, khz):
    packet = _capture(type_byte, khz)
    assert rf_paste.is_rm4_header(packet)
    read = rf_paste.broadlink_rf_packet(packet)
    assert read is not None
    assert (read.frequency_hz, read.frequency_source) == (khz * 1000, rf_paste.SOURCE_SIGNAL)
    # The timings start at byte 8: the first value is the frame's first mark.
    assert read.timings[:2] == [round(round(LONG / TICK_US) * TICK_US), -round(
        round(SHORT / TICK_US) * TICK_US)]


@pytest.mark.parametrize(("type_byte", "khz"), CARRIERS)
def test_every_carrier_pastes_as_the_same_code(type_byte, khz):
    """Only the carrier differs, so only the frequency does."""
    anchor = rf_paste.validate(_b64(_capture(0xB1, 433_920)))
    result = rf_paste.validate(_b64(_capture(type_byte, khz)))
    assert result["ok"], result
    assert (result["frames_found"], result["frames_agreeing"]) == (8, 8)
    assert (result["frequency_hz"], result["frequency_source"]) == (
        khz * 1000, rf_paste.SOURCE_SIGNAL)
    assert result["frame"] == anchor["frame"]
    assert result["fingerprint"] == anchor["fingerprint"]


def test_a_315_capture_is_no_longer_refused():
    result = rf_paste.validate(_b64(_capture(0x78, 315_000)))
    assert result["ok"], result
    assert result["frequency_hz"] == 315_000_000


@pytest.mark.parametrize("type_byte", [0xB2, 0xB4, 0xD7])
def test_four_byte_packets_keep_the_four_byte_layout(type_byte):
    packet = _four_byte(type_byte, 3, _frame() * 3)
    assert not rf_paste.is_rm4_header(packet)
    read = rf_paste.broadlink_rf_packet(packet)
    assert read is not None
    assert read.frequency_source == rf_paste.SOURCE_ASSUMED


def test_a_four_byte_packet_with_repeat_192_is_not_mistaken():
    """Byte 1 of a 4-byte packet is a repeat count, and 192 is 0xC0. Its
    first timings would have to read as a 300 to 950 MHz carrier to be
    taken for an RM4 Pro header; ordinary timings do not."""
    packet = _four_byte(0xB2, 192, [500, -1000, 500, -1000, 500, -1000, *(_frame() * 3)])
    assert packet[1] == 0xC0
    assert not rf_paste.is_rm4_header(packet)
    read = rf_paste.broadlink_rf_packet(packet)
    assert (read.frequency_hz, read.frequency_source) == (433_920_000, rf_paste.SOURCE_ASSUMED)
    assert read.timings[0] == round(round(500 / TICK_US) * TICK_US)


@pytest.mark.parametrize(
    "packet",
    [
        # Carrier field below 300 MHz.
        bytes.fromhex("78c00600f88f04000d0d"),
        # Carrier field above 950 MHz.
        bytes.fromhex("78c00600c0c62d000d0d"),
        # Length field shorter than the carrier field.
        bytes.fromhex("78c0020078ce04000d0d"),
        # Byte 1 is not 0xC0.
        bytes.fromhex("7800060078ce04000d0d"),
        # An IR code never has a carrier field.
        bytes.fromhex("26c0060078ce04000d0d"),
        # Too short to hold a carrier field.
        bytes.fromhex("78c0030078ce04"),
    ],
)
def test_headers_that_do_not_fit_are_not_rm4(packet):
    assert not rf_paste.is_rm4_header(packet)
    # And none of them reads as a radio code: 0x78 and 0x26 are not
    # radio types without the header.
    assert rf_paste.broadlink_rf_packet(packet) is None


def test_an_infrared_code_is_still_refused_as_infrared():
    packet = _four_byte(0x26, 0, [9000, -4500, 560, -560])
    result = rf_paste.validate(_b64(packet))
    assert (result["ok"], result["code"]) == (False, rf_paste.PASTE_UNREADABLE)
    assert "infrared" in result["error"]
