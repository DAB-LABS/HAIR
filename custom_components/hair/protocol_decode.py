"""NEC protocol decoding via Home Assistant's bundled infrared-protocols.

Phase A of the protocols integration (v0.4.0): HAIR decodes captured
signals as NEC when the library can read them and stores the decoded
identity alongside the raw Pronto, so later releases can match by decoded
fingerprint and transmit canonical timings instead of replaying captured
(receiver-distorted) timings.

The library is consumed via HA core's ``infrared`` dependency -- there is
no ``manifest.json`` pin. All access is guarded so a missing or
restructured library degrades cleanly to "no decode" rather than breaking
the capture path. Adding a protocol is a one-line addition to
``try_decode`` once the library ships that protocol's ``from_raw_timings``
classmethod.
"""
from __future__ import annotations

import logging

from .const import DECODED_PROTOCOL_NEC

_LOGGER = logging.getLogger(__name__)

try:
    from infrared_protocols.commands.nec import NECCommand

    _HAS_NEC = hasattr(NECCommand, "from_raw_timings")
except ImportError:
    NECCommand = None  # type: ignore[assignment,misc]
    _HAS_NEC = False


def library_available() -> bool:
    """Return True if the NEC decoder is importable and usable."""
    return _HAS_NEC


def try_decode(raw_timings: list[int] | None) -> tuple[str, int, int] | None:
    """Decode raw IR timings to ``(protocol, address, command)`` or ``None``.

    Probes NEC today. Returns the protocol-family label, the 16-bit
    address, and the 8-bit command data byte (NOT the wire-packed
    ``(command << 8) | ~command`` form ESPHome's ``transmit_nec`` accepts),
    so a stored ``decoded_command`` of ``0x08`` reads the way the user
    expects when correlating with the protocol layer.

    Returns ``None`` when the timings are absent, the library is
    unavailable, or no probed protocol matches. The library validates
    NEC's command-inverse checksum, so a non-match is a real reject, not a
    guess. Never raises into the capture hot path.
    """
    if not raw_timings or not _HAS_NEC:
        return None

    try:
        nec = NECCommand.from_raw_timings(list(raw_timings))
    except Exception:  # never break capture on a malformed-input decode error
        return None

    if nec is None:
        return None

    try:
        return (DECODED_PROTOCOL_NEC, int(nec.address), int(nec.command))
    except (AttributeError, TypeError, ValueError):
        return None
