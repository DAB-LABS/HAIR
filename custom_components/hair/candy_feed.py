"""The Candy Drawer's events: one JSON object per infrared or radio event.

The Candy Drawer is a live, raw console on the Mirror tab. While a panel
has it open, the signal monitor hands every frame a receiver delivers and
every send HAIR makes to the subscribers registered here, and the panel
prints each one as a block of text. Nothing here is stored, nothing goes
on the Home Assistant bus, and nothing runs while nobody is subscribed:
every caller checks for subscribers before building an event.

The builders below are pure. They take what the pipeline already worked
out (the normalized capture, the echo verdict, the send's built command)
and lay it out as plain JSON: numbers as numbers, hex as strings formatted
by ``format_fingerprint``, the one place HAIR formats a decoded identity.

Every event says its medium and its verdict: whether HAIR already holds
the code (``known``, with where from), meets it for the first time
(``unknown``), or is looking at a radio receiver's static (``static``).
The monitor works the verdict out; the builders only lay it out.

A radio event carries ``frame``, ``frequency_hz`` and ``gap_us`` exactly
as a Sniffer row minted from it would hold them (``raw_timings``,
``rf_frequency_hz``, ``rf_frame_gap_us``), so the panel's ``toSub`` turns
them into the very ``.sub`` the radio editor copies. No ``.sub`` text is
written here: the editor's writer is the only one.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .const import MEDIUM_IR, MEDIUM_RF
from .decoders import split_frames
from .protocol_decode import format_fingerprint

# A silence this long or longer ends a frame, for the "N frames" count.
# The decoders each declare their own frame gap, 4 to 8 ms; this count is
# protocol-blind, so it uses the common 8 ms. No protocol HAIR decodes
# has a header space anywhere near it.
CANDY_FRAME_GAP_US = 8000

# A radio receiver's static is summarized at most this often, per
# receiver: an always-on receiver hands over several captures a second.
CANDY_STATIC_SUMMARY_S = 5.0

# An unknown radio frame is held until its burst ends: printed if the
# burst votes, counted as static if it ends lone. At most this many are
# held per receiver; past it the oldest is counted as static.
CANDY_HOLD_MAX = 256

# Why a radio capture is static.
STATIC_NO_BODY = "no_body"  # no frame with a body
STATIC_SHORT = "short"  # a vote too short to be a remote's
STATIC_LONE = "lone"  # a frame whose burst never voted

# Echo kinds, as the verdict reports them.
ECHO_SEND = "send"
ECHO_GUARD = "guard"
ECHO_GARBLED = "garbled"
ECHO_FOREIGN = "foreign"

# Verdicts, and where a known code is known from (first match wins, in
# this order).
VERDICT_KNOWN = "known"
VERDICT_UNKNOWN = "unknown"
VERDICT_STATIC = "static"
KNOWN_FROM_ECHO = "echo"
KNOWN_FROM_DEVICE = "device"
KNOWN_FROM_TRIGGER = "trigger"
KNOWN_FROM_SNIFFER = "sniffer"

# Radio RX stages.
STAGE_PRESS = "press"
STAGE_FRAME = "frame"
STAGE_STATIC = "static"

CandyListener = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class CandyVerdict:
    """What HAIR makes of a code: known (and where from), unknown, static."""

    verdict: str
    known_from: str | None = None
    known_name: str | None = None

    def fields(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "known_from": self.known_from,
            "known_name": self.known_name,
        }


UNKNOWN = CandyVerdict(VERDICT_UNKNOWN)
STATIC = CandyVerdict(VERDICT_STATIC)
KNOWN_ECHO = CandyVerdict(VERDICT_KNOWN, KNOWN_FROM_ECHO)
# A send is HAIR's own code by definition.
KNOWN_SENT = CandyVerdict(VERDICT_KNOWN)

# The infrared-only keys, null on a radio event so every event has one
# shape.
_IR_ONLY_NULLS: dict[str, Any] = {
    "address": None,
    "command": None,
    "covers": None,
    "carrier_hz": None,
    "pronto": None,
    "ditto": None,
}


def frame_count(raw: list[int] | None) -> int:
    """How many frames the timings hold, split at ``CANDY_FRAME_GAP_US``."""
    if not raw:
        return 0
    return len(split_frames(raw, CANDY_FRAME_GAP_US))


def decode_fields(n: Any) -> dict[str, Any]:
    """The decode line's fields from a normalized capture.

    ``address`` and ``command`` are the second and third fields of the
    decoded fingerprint, so they read exactly as the fingerprint does.
    ``covers`` is the coverage verdict: False means the decode explains
    only part of the capture.
    """
    protocol = getattr(n, "decoded_protocol", None)
    address = getattr(n, "decoded_address", None)
    command = getattr(n, "decoded_command", None)
    if protocol is None or address is None or command is None:
        return {
            "protocol": None,
            "address": None,
            "command": None,
            "fingerprint": None,
            "covers": None,
        }
    base = format_fingerprint(protocol, int(address), int(command))
    _, address_hex, command_hex = base.split(":", 2)
    fingerprint = getattr(n, "decoded_fingerprint", None) or format_fingerprint(
        protocol, int(address), int(command), getattr(n, "decoded_extras", None)
    )
    return {
        "protocol": protocol,
        "address": address_hex,
        "command": command_hex,
        "fingerprint": fingerprint,
        "covers": getattr(n, "decode_covers", None),
    }


def _signal_fields(n: Any) -> dict[str, Any]:
    raw = [int(v) for v in (getattr(n, "raw_timings", None) or [])]
    return {
        **decode_fields(n),
        "carrier_hz": int(getattr(n, "frequency", 0) or 0) or None,
        "frames": frame_count(raw),
        "pronto": getattr(n, "code", None),
        "raw": raw,
    }


def rx_event(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    n: Any,
    echo: str | None = None,
    echo_of: int | None = None,
    echo_via: str | None = None,
    verdict: CandyVerdict = UNKNOWN,
) -> dict[str, Any]:
    """An infrared frame a receiver delivered, with the echo verdict if any."""
    return {
        "ts": ts,
        "dir": "rx",
        "entity_id": entity_id,
        "name": name,
        "medium": MEDIUM_IR,
        "stage": None,
        **verdict.fields(),
        **_signal_fields(n),
        "ditto": False,
        "echo": echo,
        "echo_of": echo_of,
        "echo_via": echo_via,
    }


def ditto_event(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    raw: list[int] | None,
    carrier_hz: int | None = None,
    pronto: str | None = None,
    verdict: CandyVerdict = UNKNOWN,
) -> dict[str, Any]:
    """A repeat frame, printed before the pipeline drops or folds it.

    ``verdict`` is the frame it repeats, when the monitor knows it.
    """
    timings = [int(v) for v in (raw or [])]
    return {
        "ts": ts,
        "dir": "rx",
        "entity_id": entity_id,
        "name": name,
        "medium": MEDIUM_IR,
        "stage": None,
        **verdict.fields(),
        "protocol": None,
        "address": None,
        "command": None,
        "fingerprint": None,
        "covers": None,
        "carrier_hz": int(carrier_hz) if carrier_hz else None,
        "frames": frame_count(timings),
        "pronto": pronto,
        "raw": timings,
        "ditto": True,
        "echo": None,
        "echo_of": None,
        "echo_via": None,
    }


def tx_event(
    *,
    ts: float,
    seq: int,
    n: Any,
    emitters: list[dict[str, str]],
    label: str,
    device: str | None,
    command_name: str | None,
    sends: int,
    origin: str | None,
) -> dict[str, Any]:
    """An infrared send, as built, before it goes on the air."""
    return {
        "ts": ts,
        "dir": "tx",
        "medium": MEDIUM_IR,
        "stage": None,
        **KNOWN_SENT.fields(),
        "seq": seq,
        "emitters": emitters,
        "label": label,
        "device": device,
        "command_name": command_name,
        "sends": max(1, int(sends or 1)),
        "origin": origin,
        **_signal_fields(n),
    }


# ---------------------------------------------------------------------------
# Radio
# ---------------------------------------------------------------------------


def _ints(values: Any) -> list[int]:
    return [int(v) for v in (values or [])]


def _rf_rx_base(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    stage: str,
    verdict: CandyVerdict,
) -> dict[str, Any]:
    return {
        "ts": ts,
        "dir": "rx",
        "entity_id": entity_id,
        "name": name,
        "medium": MEDIUM_RF,
        "stage": stage,
        **verdict.fields(),
        **_IR_ONLY_NULLS,
        "protocol": None,
        "echo": None,
        "echo_of": None,
        "echo_via": None,
    }


def rf_press_event(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    n: Any,
    frames: int | None,
    raw: list[int] | None,
    frequency_hz: int | None,
    frequency_source: str | None,
    modulation: str | None,
    verdict: CandyVerdict = UNKNOWN,
    echo: str | None = None,
    echo_of: int | None = None,
    echo_via: str | None = None,
) -> dict[str, Any]:
    """A radio press that passed the vote.

    ``n`` is the normalized capture; ``n.rf`` holds the vote. ``frame``,
    ``frequency_hz`` and ``gap_us`` are what a row minted from it holds.
    ``raw`` is the capture as received, or, for a press assembled from
    several captures, the voted frame again.
    """
    rf = n.rf
    event = _rf_rx_base(
        ts=ts, entity_id=entity_id, name=name, stage=STAGE_PRESS, verdict=verdict
    )
    event.update({
        "echo": echo,
        "echo_of": echo_of,
        "echo_via": echo_via,
        "frequency_hz": frequency_hz,
        "frequency_source": frequency_source,
        "modulation": modulation,
        "short_mark_us": rf.short_mark_us,
        "gap_us": int(rf.gap_us) if rf.gap_us is not None else None,
        "gap_source": rf.gap_source,
        "frames": frames,
        "votes": rf.votes,
        "fingerprint": rf.fingerprint,
        "frame_hash": rf.frame_hash,
        "body_edges": rf.body_edges,
        "frame": _ints(rf.frame),
        "raw": _ints(raw if raw is not None else rf.frame),
    })
    return event


def rf_frame_event(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    frame: list[int],
    gap_us: int | None,
    gap_source: str,
    fingerprint: str,
    frame_hash: str,
    body_edges: int,
    frequency_hz: int | None,
    frequency_source: str | None,
    raw: list[int] | None,
    verdict: CandyVerdict = UNKNOWN,
) -> dict[str, Any]:
    """One frame a one-frame-per-capture receiver handed to the burst
    assembler, before the press it belongs to is voted."""
    event = _rf_rx_base(
        ts=ts, entity_id=entity_id, name=name, stage=STAGE_FRAME, verdict=verdict
    )
    event.update({
        "frequency_hz": frequency_hz,
        "frequency_source": frequency_source,
        "modulation": None,
        "short_mark_us": None,
        "gap_us": gap_us,
        "gap_source": gap_source,
        "frames": 1,
        "votes": None,
        "fingerprint": fingerprint,
        "frame_hash": frame_hash,
        "body_edges": body_edges,
        "frame": _ints(frame),
        "raw": _ints(raw),
    })
    return event


def rf_static_summary_event(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    count: int,
    since: float,
) -> dict[str, Any]:
    """How many static captures a receiver delivered since its last summary."""
    return {
        **_rf_rx_base(
            ts=ts, entity_id=entity_id, name=name, stage=STAGE_STATIC,
            verdict=STATIC,
        ),
        "count": int(count),
        "since": since,
    }


def rf_static_capture_event(
    *,
    ts: float,
    entity_id: str | None,
    name: str | None,
    raw: list[int] | None,
    reason: str,
) -> dict[str, Any]:
    """One static capture, for a subscription that asked for them.

    ``reason`` says why it is static: ``no_body``, ``short`` or ``lone``.
    """
    timings = _ints(raw)
    return {
        **_rf_rx_base(
            ts=ts, entity_id=entity_id, name=name, stage=STAGE_STATIC,
            verdict=STATIC,
        ),
        "count": None,
        "reason": reason,
        "raw": timings,
        "values": len(timings),
    }


def rf_tx_event(
    *,
    ts: float,
    seq: int,
    n: Any,
    frame: list[int],
    gap_us: int | None,
    wire: list[int],
    emitters: list[dict[str, str]],
    skipped: list[dict[str, str]],
    label: str,
    device: str | None,
    command_name: str | None,
    sends: int,
    origin: str | None,
    frequency_hz: int | None,
    on_air_hz: int | None,
    substituted: bool,
) -> dict[str, Any]:
    """A radio send, as planned, before it goes on the air.

    ``frame``, ``frequency_hz`` and ``gap_us`` are the command's own
    stored code, so its ``.sub`` is the editor's. ``n`` is the wire frame
    read back through the receive code (the echo ticket's identity, so
    the echo's fingerprint matches); ``wire`` is the frame as sent once.
    """
    rf = n.rf
    return {
        "ts": ts,
        "dir": "tx",
        "medium": MEDIUM_RF,
        "stage": None,
        **KNOWN_SENT.fields(),
        **_IR_ONLY_NULLS,
        "seq": seq,
        "emitters": emitters,
        "skipped": skipped,
        "label": label,
        "device": device,
        "command_name": command_name,
        "sends": max(1, int(sends or 1)),
        "origin": origin,
        "protocol": None,
        "frequency_hz": frequency_hz,
        "on_air_hz": on_air_hz,
        "substituted": bool(substituted),
        "gap_us": int(gap_us) if gap_us is not None else None,
        "fingerprint": rf.fingerprint,
        "frame_hash": rf.frame_hash,
        "frame": _ints(frame),
        "raw": _ints(wire),
        "frames": None,
    }
