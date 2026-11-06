"""Reading a pasted radio code, and writing one back (RF send round, T3).

The editor's radio code box, the Clipper and (later) wigs exchange a
radio code as text. Three shapes are read (plan 5.3):

- a Flipper SubGhz RAW file, ``.sub``: any number of ``RAW_Data:``
  lines, signed microseconds, and its ``Frequency:`` line in Hz;
- a bare list of signed integers, the platform's own convention (mark
  positive), as an ESPHome ``dump: raw`` line prints it; and
- Broadlink RF base64, the packets an RM pro learns and SmartIR-style
  files hold: ``0xB1`` (an RM4 Pro capture, which records its carrier),
  and the ``0xB_`` and ``0xD_`` sends, whose band is assumed from the type.

Whatever was pasted, the timings are put in HAIR's form before anything
reads them: leading spaces and zeros dropped, and a capture that began
in the middle of a pulse (every inter-frame gap on a mark) moved back by
one, so even positions are marks. Then ``rf_frames`` does what it does
for a capture: ``analyze`` votes over a burst, and a lone frame is read
by ``identity_of_frame``. Nothing here decides identity.

What comes back is the row a paste becomes, in the shape every radio row
has (``rf-send-doors.md`` section 1): one frame with its gap last, the
frequency and where it came from, the gap and where it came from.

Written out, a radio code is a ``.sub`` file holding that one frame
(the repeats and the gap are send settings, not part of the code).
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Any

from .const import MEDIUM_RF, RF_GAP_MEASURED, RF_MIN_BODY_EDGES, RF_PROTOCOL

FORMAT_SUB = "sub"
FORMAT_TIMINGS = "timings"
FORMAT_BROADLINK = "broadlink"

PASTE_EMPTY = "rf_paste_empty"
PASTE_UNREADABLE = "rf_paste_unreadable"
PASTE_NO_FRAME = "rf_paste_no_frame"
PASTE_FRAMES_DISAGREE = "rf_paste_frames_disagree"

SOURCE_SIGNAL = "signal"
SOURCE_ASSUMED = "assumed"
SOURCE_USER = "user"

# A Broadlink tick, as the infrared packet reader has it
# (wig_adapters._BROADLINK_TICK_US). Identity never reads an absolute
# width, so the small difference from the library's own figure does not
# reach a fingerprint.
_BROADLINK_TICK_US = 1_000_000 / 32_768
_RM4_CAPTURE = 0xB1
_BAND_433_HZ = 433_920_000
_BAND_315_HZ = 315_000_000

# A space this long or longer is an inter-frame gap when realigning a
# capture that started mid-pulse (about 3 ms, the library's rule:
# longer than any data pulse, shorter than any gap).
_REALIGN_GAP_US = 3_000

_SUB_HEADER = "Filetype: Flipper SubGhz RAW File"
_SUB_PRESET = "FuriHalSubGhzPresetOok650Async"
_SUB_LINE_VALUES = 512

_INT_LIST = re.compile(r"^[\s\[\](),;+\-\d]*$")


@dataclass(frozen=True)
class PasteRead:
    """What a paste says before identity is worked out."""

    format: str
    timings: list[int]
    frequency_hz: int | None
    frequency_source: str | None


class PasteError(ValueError):
    """A paste that is not a radio code; ``code`` says why."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def read_paste(text: str) -> PasteRead:
    """The format, timings and frequency a pasted text holds.

    Raises PasteError with ``rf_paste_empty`` or ``rf_paste_unreadable``.
    """
    text = (text or "").strip()
    if not text:
        raise PasteError(PASTE_EMPTY, "Nothing was pasted")
    if "RAW_Data:" in text or text.startswith("Filetype:"):
        return _read_sub(text)
    if _INT_LIST.match(text) and re.search(r"\d", text):
        values = [int(v) for v in re.findall(r"[+-]?\d+", text)]
        return PasteRead(FORMAT_TIMINGS, normalise(values), None, None)
    return _read_broadlink(text)


def _read_sub(text: str) -> PasteRead:
    frequency: int | None = None
    protocol: str | None = None
    values: list[int] = []
    for line in text.splitlines():
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "Frequency":
            try:
                frequency = int(value) or None
            except ValueError:
                raise PasteError(
                    PASTE_UNREADABLE, f"Frequency is not a number: {value!r}"
                ) from None
        elif key == "Protocol":
            protocol = value
        elif key == "RAW_Data":
            try:
                values.extend(int(v) for v in value.split())
            except ValueError:
                raise PasteError(
                    PASTE_UNREADABLE, "RAW_Data holds something that is not a number"
                ) from None
    if protocol is not None and protocol != "RAW":
        # A decoded .sub (Princeton, CAME and the rest) names a protocol
        # and a key, not timings; HAIR reads timings.
        raise PasteError(
            PASTE_UNREADABLE, f"A {protocol} .sub holds a key, not timings; record it as RAW"
        )
    if not values:
        raise PasteError(PASTE_UNREADABLE, "The .sub has no RAW_Data")
    return PasteRead(
        FORMAT_SUB,
        normalise(values),
        frequency,
        SOURCE_SIGNAL if frequency else None,
    )


def _read_broadlink(text: str) -> PasteRead:
    cleaned = "".join(text.split())
    if len(cleaned) % 4:
        cleaned += "=" * (-len(cleaned) % 4)
    try:
        packet = base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError):
        raise PasteError(
            PASTE_UNREADABLE, "Not a .sub, a list of timings or Broadlink base64"
        ) from None
    read = broadlink_rf_packet(packet)
    if read is None:
        kind = packet[0] if packet else None
        raise PasteError(
            PASTE_UNREADABLE,
            "An infrared Broadlink code, not a radio one"
            if kind == 0x26
            else "Not a Broadlink radio packet",
        )
    return read


def broadlink_rf_packet(packet: bytes) -> PasteRead | None:
    """A Broadlink radio packet's timings and carrier, or None.

    ``0xB1``, an RM4 Pro capture, records the carrier it was learned on
    in kHz at offsets 4 to 7, and its timings start at offset 8. Every
    other radio type starts at offset 4 and carries no carrier: its band
    is assumed from the type (``0xB_`` 433.92 MHz, ``0xD_`` 315 MHz).
    Durations are ticks, read by ``wig_adapters``' one tick reader.
    """
    if len(packet) < 4:
        return None
    kind = packet[0] & 0xF0
    if kind not in (0xB0, 0xD0):
        return None
    offset = 4
    frequency: int | None = None
    source: str | None = None
    if packet[0] == _RM4_CAPTURE and len(packet) >= 8:
        khz = int.from_bytes(packet[4:8], "little")
        offset = 8
        if khz:
            frequency, source = khz * 1000, SOURCE_SIGNAL
    if frequency is None:
        frequency = _BAND_433_HZ if kind == 0xB0 else _BAND_315_HZ
        source = SOURCE_ASSUMED
    from .wig_adapters import broadlink_payload_ticks

    end = min(4 + int.from_bytes(packet[2:4], "little"), len(packet))
    ticks = broadlink_payload_ticks(packet[offset:end])
    if not ticks:
        return None
    timings = [
        round(t * _BROADLINK_TICK_US) * (1 if i % 2 == 0 else -1)
        for i, t in enumerate(ticks)
    ]
    return PasteRead(FORMAT_BROADLINK, normalise(timings), frequency, source)


def normalise(values: list[int]) -> list[int]:
    """Timings in HAIR's form: signed, starting on a mark.

    Signed input keeps its signs; a list with no negative value is read
    as alternating, mark first. Leading spaces and zeros are dropped. A
    capture that started in the middle of a pulse puts every
    inter-frame gap on a mark; when at least two gaps do and none sits
    on a space, the first value is dropped and the signs follow.
    """
    if any(v < 0 for v in values):
        signed = [int(v) for v in values if v != 0]
    else:
        signed = [int(v) * (1 if i % 2 == 0 else -1) for i, v in enumerate(values) if v]
    while signed and signed[0] < 0:
        signed.pop(0)
    # Make the signs strictly alternate: two marks or two spaces in a row
    # (a .sub can split one pulse across RAW_Data lines) are one edge.
    merged: list[int] = []
    for value in signed:
        if merged and (merged[-1] > 0) == (value > 0):
            merged[-1] += value
        else:
            merged.append(value)
    long_marks = [i for i, v in enumerate(merged) if v >= _REALIGN_GAP_US]
    long_spaces = [i for i, v in enumerate(merged) if v <= -_REALIGN_GAP_US]
    if len(long_marks) >= 2 and not long_spaces:
        merged = [-v for v in merged[1:]]
        while merged and merged[0] < 0:
            merged.pop(0)
    return merged


# ---------------------------------------------------------------------------
# Identity and the validate door's answer
# ---------------------------------------------------------------------------


def validate(text: str, frequency_hz: int | None = None) -> dict[str, Any]:
    """The ``hair/rf/validate`` answer for a paste (rf-send-doors.md 5).

    ``frequency_hz`` given by the caller wins over the paste's own, and
    is recorded as the user's.
    """
    from . import rf_frames

    try:
        read = read_paste(text)
    except PasteError as err:
        return {"ok": False, "code": err.code, "error": str(err)}

    pieces = rf_frames.split_frames(read.timings)
    whole = rf_frames.whole_frames(pieces)
    capture = rf_frames.analyze(read.timings)
    if capture is None:
        if len(whole) > 1:
            return {
                "ok": False, "code": PASTE_FRAMES_DISAGREE,
                "error": f"{len(whole)} frames found, and too few of them agree",
                "frames_found": len(whole),
            }
        capture = rf_frames.identity_of_frame(read.timings)
    if capture is None or capture.body_edges < RF_MIN_BODY_EDGES:
        return {"ok": False, "code": PASTE_NO_FRAME, "error": "No frame with a body was found"}

    if frequency_hz:
        frequency, source = int(frequency_hz), SOURCE_USER
    else:
        frequency, source = read.frequency_hz, read.frequency_source
    gap_us, gap_source = capture.gap_us, capture.gap_source
    if capture.votes == 1 and read.timings and read.timings[-1] <= -_REALIGN_GAP_US:
        # A lone frame that ends on a long space carries its gap: a .sub
        # HAIR wrote, or a stored frame pasted back. identity_of_frame
        # cannot see it (the identity strip drops a trailing space), so
        # it is read here rather than assumed.
        gap_us, gap_source = -read.timings[-1], RF_GAP_MEASURED
    frame = _single_frame(capture)
    # The identity is read back off the frame that will be STORED, by the
    # function every later recomputation uses (identity.canonical_fingerprint
    # calls identity_of_frame on a radio row), so the row never disagrees
    # with itself.
    stored = rf_frames.identity_of_frame(frame)
    if stored is None:
        return {"ok": False, "code": PASTE_NO_FRAME, "error": "No frame with a body was found"}
    return {
        "ok": True,
        "format": read.format,
        "frames_found": max(len(whole), 1),
        "frames_agreeing": capture.votes,
        "frame": frame,
        "frequency_hz": frequency,
        "frequency_source": source,
        "gap_us": gap_us,
        "gap_source": gap_source,
        "repeats_observed": capture.votes,
        "fingerprint": stored.fingerprint,
        "frame_hash": stored.frame_hash,
        "header_shape": stored.header_shape,
        "sub_text": to_sub(frame, frequency, gap_us),
    }


def apply_code(row: Any, result: dict[str, Any]) -> None:
    """Write a validated paste onto a radio row, as a capture would.

    Every identity field is replaced; the knobs a user set (send count,
    alias, spacing) are left alone. A paste without a frequency keeps
    the row's own. Rows that keep a fingerprint (a Sniffer row) get the
    new one; a device command has none stored, it is recomputed from
    the frame.
    """
    row.medium = MEDIUM_RF
    row.protocol = RF_PROTOCOL
    row.code = None
    row.raw_timings = list(result["frame"])
    row.byte_hash = result["frame_hash"]
    row.rf_frame_hash = result["frame_hash"]
    row.rf_repeats_observed = result["repeats_observed"]
    row.rf_frame_gap_us = result["gap_us"]
    row.rf_frame_gap_source = result["gap_source"]
    row.rf_header_shape = result.get("header_shape")
    row.rf_short_mark_us = None
    row.rf_modulation = getattr(row, "rf_modulation", None) or "OOK"
    if result.get("frequency_hz"):
        row.rf_frequency_hz = int(result["frequency_hz"])
        row.rf_frequency_source = result.get("frequency_source") or SOURCE_USER
    for name in ("decoded_protocol", "decoded_address", "decoded_command",
                 "decoded_fingerprint", "decoded_extras", "decode_covers"):
        if hasattr(row, name):
            setattr(row, name, None)
    if hasattr(row, "fingerprint"):
        row.fingerprint = result["fingerprint"]


def set_frequency(row: Any, frequency_hz: int) -> None:
    """The user's frequency for a radio row: the editor's field, the one
    step of the frequency ladder a user takes (go, decision 5)."""
    row.rf_frequency_hz = int(frequency_hz)
    row.rf_frequency_source = SOURCE_USER


def _single_frame(capture: Any) -> list[int]:
    """The capture's frame in the stored shape: one frame, its gap last
    when the gap was measured (rf-send-doors.md section 1)."""
    frame = [int(v) for v in capture.frame]
    if capture.gap_source == RF_GAP_MEASURED and frame and frame[-1] > 0:
        frame.append(-int(capture.gap_us))
    return frame


def to_sub(frame: list[int], frequency_hz: int | None, gap_us: int | None = None) -> str:
    """One frame as a Flipper SubGhz RAW file.

    The frame is written once, ending on its gap so a Flipper replaying
    it in a loop leaves the gap between repeats. ``Frequency`` is 0 when
    the code has none yet; a Flipper asks for one then, as HAIR does.
    """
    values = [int(v) for v in frame if v]
    if values and values[-1] > 0 and gap_us:
        values.append(-int(gap_us))
    lines = [
        _SUB_HEADER,
        "Version: 1",
        f"Frequency: {int(frequency_hz or 0)}",
        f"Preset: {_SUB_PRESET}",
        "Protocol: RAW",
    ]
    for start in range(0, len(values), _SUB_LINE_VALUES):
        chunk = values[start:start + _SUB_LINE_VALUES]
        lines.append("RAW_Data: " + " ".join(str(v) for v in chunk))
    return "\n".join(lines) + "\n"
