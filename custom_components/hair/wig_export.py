"""Save as wig: serialize catalog remotes and HAIR devices into wigs.

Export scope (owner rulings, wigs.md sections 7 and 13): catalog remotes
from all three acquisition roads (sniffed, clipped, plucked) AND HAIR
device command sets (ruled into v1 on 2026-07-20). The wig gets an
``origin`` stamp describing which road produced it, driving the editor
popover's plain-English origin sentence:

- ``captured`` -- exported from signals sniffed off real hardware
- ``clipped`` -- assembled in the Clipper (pasted or library codes)
- ``plucked`` -- vendor codes extracted live through the Plucker
- ``device`` -- a HAIR device's command set

Raw Pronto is the payload. Signals that carry a Pronto code ship it
verbatim; raw-timing-only signals convert through ``raw_to_pronto``;
a signal with neither is skipped and counted, never guessed.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ir_command import raw_to_pronto
from .models import IRDevice, UnknownDevice
from .wig_format import Wig, WigSignal

_ORIGIN_BY_SOURCE = {
    "sniffed": "captured",
    "manual": "clipped",
    "plucked": "plucked",
}


@dataclass
class WigBuild:
    """An export attempt: the wig (or None) plus skip accounting."""

    wig: Wig | None
    skipped: int


def _pronto_for(
    protocol: str | None,
    code: str | None,
    raw_timings: list[int] | None,
    frequency: int | None,
) -> str | None:
    if protocol == "PRONTO" and code:
        return code
    if raw_timings:
        try:
            return raw_to_pronto(
                list(raw_timings), frequency=frequency or 38000
            )
        except Exception:
            return None
    return None


def build_wig_from_catalog(device: UnknownDevice) -> WigBuild:
    """Serialize a catalog remote's signals into a wig."""
    signals: list[WigSignal] = []
    skipped = 0
    for i, sig in enumerate(device.signals, start=1):
        pronto = _pronto_for(
            sig.protocol, sig.code, sig.raw_timings, sig.frequency
        )
        if pronto is None:
            skipped += 1
            continue
        alias = (
            sig.alias.strip()
            or (sig.plucked_command_name or "").strip()
            or (sig.decoded_fingerprint or "").strip()
            or f"Signal {i}"
        )
        signals.append(WigSignal(
            alias=alias, pronto=pronto, send_count=sig.send_count
        ))
    if not signals:
        return WigBuild(None, skipped)
    return WigBuild(
        Wig(
            name=(device.label or "Exported Remote").strip()
            or "Exported Remote",
            signals=signals,
            origin=_ORIGIN_BY_SOURCE.get(device.source),
        ),
        skipped,
    )


def build_wig_from_device(device: IRDevice) -> WigBuild:
    """Serialize a HAIR device's command set into a wig."""
    signals: list[WigSignal] = []
    skipped = 0
    for i, command in enumerate(device.commands, start=1):
        pronto = _pronto_for(
            command.protocol,
            command.code,
            command.raw_timings,
            getattr(command, "frequency", None),
        )
        if pronto is None:
            skipped += 1
            continue
        alias = (command.name or "").strip() or f"Command {i}"
        signals.append(WigSignal(
            alias=alias, pronto=pronto, send_count=command.send_count
        ))
    if not signals:
        return WigBuild(None, skipped)
    return WigBuild(
        Wig(
            name=(device.name or "Exported Device").strip()
            or "Exported Device",
            signals=signals,
            origin="device",
        ),
        skipped,
    )
