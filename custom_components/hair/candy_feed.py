"""The Candy Drawer's events: one JSON object per infrared event.

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
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .decoders import split_frames
from .protocol_decode import format_fingerprint

# A silence this long or longer ends a frame, for the "N frames" count.
# The decoders each declare their own frame gap, 4 to 8 ms; this count is
# protocol-blind, so it uses the common 8 ms. No protocol HAIR decodes
# has a header space anywhere near it.
CANDY_FRAME_GAP_US = 8000

# Echo kinds, as the verdict reports them.
ECHO_SEND = "send"
ECHO_GUARD = "guard"
ECHO_GARBLED = "garbled"
ECHO_FOREIGN = "foreign"

CandyListener = Callable[[dict[str, Any]], None]


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
) -> dict[str, Any]:
    """A frame a receiver delivered, with the echo verdict if any."""
    return {
        "ts": ts,
        "dir": "rx",
        "entity_id": entity_id,
        "name": name,
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
) -> dict[str, Any]:
    """A repeat frame, printed before the pipeline drops or folds it."""
    timings = [int(v) for v in (raw or [])]
    return {
        "ts": ts,
        "dir": "rx",
        "entity_id": entity_id,
        "name": name,
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
    """A send, as built, before it goes on the air."""
    return {
        "ts": ts,
        "dir": "tx",
        "seq": seq,
        "emitters": emitters,
        "label": label,
        "device": device,
        "command_name": command_name,
        "sends": max(1, int(sends or 1)),
        "origin": origin,
        **_signal_fields(n),
    }
