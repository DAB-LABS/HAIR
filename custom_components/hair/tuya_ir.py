"""Read Tuya compressed IR codes (UFO-R11 and friends).

WHAT THE CONTAINER IS. A Tuya IR blaster stores a code as base64 of a
FastLZ level-1 compressed stream. Inflated, that stream is a plain
little-endian uint16 array of microsecond durations, alternating mark
and space and starting on a mark. There is no carrier field: 38 kHz is
the assumption, the same one the Broadlink reader makes.

WHY IT NEEDED READING. SmartIR files for MQTT controllers declare
``commandsEncoding: "Raw"``, which in SmartIR means a decimal timing
list. A UFO-R11 file says the same thing and carries this instead. GH
#108 is what came of believing the label: the digits inside base64 text
were read as microseconds and became codes that transmit nothing. So the
container is detected by CONTENT here, never by what the file calls it.

WHAT THIS IS NOT. It is not a Tuya writer, and it is not needed to send:
``mqtt.infrared`` shipped in HA 2026.8, so a Zigbee2MQTT-attached
UFO-R11 is an ordinary infrared-platform emitter HAIR already discovers.
Reading completes the path: once a code is timings, it is Pronto, and
Pronto goes out of any emitter and decodes like any capture.

WRITTEN FROM THE FORMAT, NOT FROM ANYONE'S SOURCE. FastLZ level 1 is a
short, well-documented byte format and the decoder below was written
from that description, in the same spirit as the decoders package rule:
HAIR carries no copied implementation.

  * A control byte under 0x20 opens a literal run of ``ctrl + 1`` bytes,
    which follow it verbatim.
  * Otherwise the top three bits are a match length and the low five are
    the high bits of a back reference. A length of 7 means "read one
    more byte and add it". One more byte carries the low eight bits of
    the reference. The match is ``length + 2`` bytes copied from
    ``reference + 1`` bytes back, byte at a time so overlapping runs
    expand the way the compressor intended.

Everything is bounds-checked before it is read, the output is capped,
and any malformed stream returns None rather than raising, looping or
allocating without limit. A corrupt payload is an unreadable code, which
is an ordinary outcome on an import path, not an exception.
"""
from __future__ import annotations

import base64
import binascii
import logging
import struct

_LOGGER = logging.getLogger(__name__)

# A Tuya code is a button press, not a recording. The longest real
# payloads seen are AC state frames around 230 durations; the cap is an
# order of magnitude above that, so a corrupt stream that decodes to
# something enormous is refused instead of eating memory.
MAX_INFLATED_BYTES = 8192
MAX_DURATIONS = MAX_INFLATED_BYTES // 2

# Plausibility of the inflated array, applied before anything downstream
# sees it. These are deliberately loose: the point is to reject noise
# that happens to inflate, not to have opinions about protocols.
MIN_DURATIONS = 4
MIN_DURATION_US = 10
MAX_DURATION_US = 100_000
MAX_TOTAL_US = 2_000_000

# Tuya carries no carrier frequency. Consumer IR is 38 kHz unless it
# says otherwise, and nothing here says otherwise.
TUYA_CARRIER_HZ = 38000

# Broadlink packets are the OTHER thing that arrives as base64 on this
# path, and their first byte is a type: 0x26 IR, 0xb2 and 0xd7 RF. A
# type byte is not a FastLZ opcode, but nothing stops a Broadlink packet
# from inflating into something that passes a loose plausibility check,
# and a code read by the wrong reader is worse than a code refused. So
# the packet is handed back to its own reader rather than guessed at.
BROADLINK_TYPES = (0x26, 0xB2, 0xD7)


def fastlz_decompress(data: bytes, *, max_output: int = MAX_INFLATED_BYTES):
    """Inflate a FastLZ level-1 stream, or None if it is not one.

    Returns None for a truncated stream, a back reference pointing
    before the start of the output, or output that would exceed
    ``max_output``. Never raises on input, and always terminates: every
    iteration consumes at least one input byte.
    """
    if not data:
        return None
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        ctrl = data[i]
        i += 1
        if ctrl < 0x20:
            length = ctrl + 1
            if i + length > n:
                return None
            if len(out) + length > max_output:
                return None
            out += data[i:i + length]
            i += length
            continue
        length = ctrl >> 5
        ref = (ctrl & 0x1F) << 8
        if length == 7:
            if i >= n:
                return None
            length += data[i]
            i += 1
        if i >= n:
            return None
        ref |= data[i]
        i += 1
        length += 2
        start = len(out) - ref - 1
        if start < 0:
            return None
        if len(out) + length > max_output:
            return None
        for _ in range(length):
            out.append(out[start])
            start += 1
    return bytes(out)


def _durations(blob: bytes):
    """The uint16 little-endian array, or None if the blob is not one."""
    if not blob or len(blob) % 2:
        return None
    count = len(blob) // 2
    if count < MIN_DURATIONS or count > MAX_DURATIONS:
        return None
    return list(struct.unpack("<" + "H" * count, blob))


def _plausible(values) -> bool:
    """Does this read as an IR burst rather than as noise?

    Loose on purpose. A code has at least a few edges, no zero-length
    ones, nothing longer than a tenth of a second, and does not add up
    to more than a couple of seconds of air time.
    """
    if not values or len(values) < MIN_DURATIONS:
        return False
    if any(v < MIN_DURATION_US or v > MAX_DURATION_US for v in values):
        return False
    return sum(values) <= MAX_TOTAL_US


def looks_like_tuya(code: str | None) -> bool:
    """True when this text is a Tuya container HAIR can read."""
    return tuya_b64_to_timings(code) is not None


def tuya_b64_to_timings(code: str | None):
    """Signed HAIR timings for a Tuya base64 code, or None.

    None means "this is not a Tuya container", which is a question this
    function is asked about every base64 value on the import path. It
    answers by trying, because the file's own label cannot be trusted
    (GH #108), and says nothing louder than DEBUG when the answer is no.

    The returned list is HAIR's convention: marks positive, spaces
    negative, ending on a mark. A trailing space is dropped the same way
    the Broadlink reader drops it, since a terminating silence is not
    part of the code.
    """
    if not code or not isinstance(code, str):
        return None
    cleaned = code.strip()
    if len(cleaned) < 8:
        return None
    if len(cleaned) % 4:
        cleaned += "=" * (-len(cleaned) % 4)
    try:
        packet = base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError):
        return None
    if packet and packet[0] in BROADLINK_TYPES:
        return None
    blob = fastlz_decompress(packet)
    if blob is None:
        return None
    values = _durations(blob)
    if values is None or not _plausible(values):
        return None
    if len(values) % 2 == 0:
        values = values[:-1]
    if len(values) < MIN_DURATIONS - 1:
        return None
    _LOGGER.debug(
        "Read a Tuya IR container: %d durations, %d us of air time",
        len(values), sum(values),
    )
    return [
        v if index % 2 == 0 else -v for index, v in enumerate(values)
    ]


def tuya_b64_to_pronto(code: str | None):
    """Pronto for a Tuya base64 code, or None if it is not one.

    Once it is timings it is an ordinary HAIR code: the Pronto goes out
    of any emitter and decodes like any capture, which is the whole
    point of reading the container rather than passing it through.
    """
    timings = tuya_b64_to_timings(code)
    if not timings:
        return None
    from .ir_command import raw_to_pronto

    try:
        return raw_to_pronto(timings, frequency=TUYA_CARRIER_HZ)
    except (ValueError, TypeError, IndexError):
        return None
