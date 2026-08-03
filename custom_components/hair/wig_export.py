"""Save as wig: serialize a HAIR device's command set into a wig.

Export scope narrowed to DEVICES ONLY (owner ruling 2026-08-03).
Sniffer, Clipper and Plucker remotes no longer export directly; they
go through Make Device first, so a wig is always born from something
somebody could actually press. That is what makes an attestation
possible at birth: a catalog remote has no emitter routing, so nobody
could have tested the codes they were about to vouch for.

The wig keeps its ``origin`` stamp, which now always reads ``device``
for a fresh export. The other three values (``captured``, ``clipped``,
``plucked``) still arrive on wigs written by earlier versions and by
other tools, and the editor popover still explains them.

Raw Pronto is the payload. Signals that carry a Pronto code ship it
verbatim; raw-timing-only signals convert through ``raw_to_pronto``;
a signal with neither is skipped and counted, never guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .const import MAX_DITTO_COUNT
from .ir_command import raw_to_pronto
from .models import IRDevice
from .wig_format import Wig, WigSignal

# Device-type to wig kind, unambiguous mappings only. media_player
# stays out (tv / soundbar / receiver / settopbox all live there) and
# switch / other say nothing about what the hardware is.
_KIND_BY_DEVICE_TYPE = {
    "ac": "ac",
    "fan": "fan",
    "light": "light",
    "screen": "screen",
}

@dataclass
class WigBuild:
    """An export attempt: the wig (or None) plus skip accounting."""

    wig: Wig | None
    skipped: int
    # Which source row each built signal came from, in step with
    # ``wig.signals``. Command id for a device export, signal id for a
    # catalog one. The save dialog needs this because the two lists are
    # NOT parallel: a signal with no usable Pronto is skipped, so index
    # 4 of the wig can be command 6 of the device, and a plan row that
    # guessed would attach a claim to the wrong command.
    sources: list[str] = field(default_factory=list)
    # Receipts for values the export deliberately changed rather than
    # refused. Currently only the bypass x ditto drop: a raw blob has no
    # ditto grammar, so a nonzero ditto on a pinned command cannot ride
    # along, and silently zeroing it would be the kind of quiet edit this
    # format exists to prevent. Same shape as the adapters' skipped
    # list: human strings, surfaced beside the export.
    notes: list[str] = field(default_factory=list)


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


def _ditto_for_export(
    alias: str, repeat_count: int | None, bypass: bool
) -> tuple[int, str | None]:
    """The wig's ditto value for one command, plus a receipt if dropped.

    Bypass and dittos are mutually exclusive (owner ruling). A raw blob
    has no ditto grammar: only the encoder can render a shortened repeat
    frame, so platform-level repetition of raw bytes is whole-blob
    repetition, which is send_count's job. Writing a nonzero ditto onto
    a pinned signal would also contradict the pin's whole promise --
    these bytes are the payload, do not improve them.

    The drop is announced rather than silent. A wig that quietly lost a
    value the author set is the failure this format exists to prevent.
    """
    value = max(0, min(int(repeat_count or 0), MAX_DITTO_COUNT))
    if bypass and value:
        return 0, (
            f"{alias}: dittos ({value}) dropped, the code is pinned to "
            "raw and a raw blob carries its repeats in the bytes"
        )
    return (0 if bypass else value), None



def build_wig_from_device(device: IRDevice) -> WigBuild:
    """Serialize a HAIR device's command set into a wig."""
    signals: list[WigSignal] = []
    sources: list[str] = []
    notes: list[str] = []
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
        ditto, note = _ditto_for_export(
            alias, command.repeat_count, command.tx_force_raw,
        )
        if note:
            notes.append(note)
        signals.append(WigSignal(
            alias=alias, pronto=pronto, send_count=command.send_count,
            # The raw pin travels with the codes (Highlights, GH #78).
            # Dropping it here is what made a repaired device export a
            # wig that arrived broken for the next person.
            bypass_protocol=command.tx_force_raw,
            ditto_count=ditto,
        ))
        sources.append(command.id)
    if not signals:
        return WigBuild(None, skipped, sources, notes)
    return WigBuild(
        Wig(
            name=(device.name or "Exported Device").strip()
            or "Exported Device",
            signals=signals,
            origin="device",
            # Where the seed came from (v0.9.5, plan 5.4). A device
            # built by converting a downloaded file says so in the wig
            # it later becomes, so shop tooling can spot siblings whose
            # bytes drifted. A device adopted from a closet wig carries
            # a ``source_wig_id`` instead, and that path is an UPDATE,
            # not a conversion.
            converted_from=device.source_file or None,
            # Kind auto-stamp (v0.8.0): the HAIR device already knows
            # what it is for the UNAMBIGUOUS types. media_player is
            # deliberately absent (tv? soundbar? receiver?) -- the
            # signing prompt asks the human in that case. Any explicit
            # kind from the export dialog overrides this in the WS
            # handler.
            kind=_KIND_BY_DEVICE_TYPE.get(
                getattr(device.device_type, "value", device.device_type)
            ),
        ),
        skipped,
        sources,
        notes,
    )
