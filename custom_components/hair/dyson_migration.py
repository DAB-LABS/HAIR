"""The Dyson counter split, applied to rows already on disk.

WHY A MIGRATION AND NOT A BACKFILL. Until the protocol pack, this
integration read the Dyson rolling counter from the F byte's low two
bits. It is in the high two: they are the last two bits on the wire and
the frame layout, upstream's own enum and a corpus of rendered commands
all say so (``decoders/dyson.py`` has the recomputed table).
Correcting the reader moves the meaning of every stored ``DYSON`` row.

That matters because HAIR TRANSMITS FROM THE STORED TRIPLE. A row with
a decoded fingerprint and a coverage verdict that is not False is
rebuilt through its decoder on every press rather than replayed, so a
stored AM07 PowerToggle recorded as ``(device 9, function 0x10,
counter 0)`` would re-encode under the new split to the wire
``100100000001000`` where it used to emit ``100100000000010``. That is
a different button. Left alone, the pack would silently break every
Dyson button anybody has saved.

THE REMAP IS A LOSSLESS BIJECTION through the byte both readings share::

    f_byte      = ((old_function & 0x3F) << 2) | (old_counter & 0x3)
    new_function = f_byte & 0x3F
    new_counter  = (f_byte >> 6) & 0x3

Nothing is lost and the inverse is the same arithmetic the other way
round, so the migration is reversible if it ever has to be.

IT IS NOT IDEMPOTENT, which is why it runs from the store's migration
hook under the version machinery rather than from the load-time
backfill chain beside ``_backfill_canonical_identity`` and friends.
Those are safe to re-run because canonicalizing twice is canonicalizing
once; running this twice would remap already-remapped values and land
on a third, wrong button. The store's minor version is what guarantees
exactly one application.

TRIGGERS TAKE THE OTHER ROUTE. A trigger row carries a fingerprint and
a Pronto code but no triple, so there is no F byte to rebuild and the
arithmetic has nothing to work on. They are re-decoded from the stored
code instead, which is what ``_backfill_trigger_decoded`` already does
for a trigger that never had an identity, and which gives the answer a
fresh capture of the same button would give.

WIGS ON DISK NEED NOTHING. A wig stores Pronto, so its rows re-derive
their identity on the next parse. Signed fittings are over the code
text, not the triple, so they survive untouched.
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

DYSON = "DYSON"


def remap_fields(function: int, counter: int) -> tuple[int, int]:
    """``(old_function, old_counter)`` to ``(new_function, new_counter)``.

    The one place the bijection is written down. Both stores and the
    tests call it so there is no second copy to drift.
    """
    f_byte = (((int(function) & 0x3F) << 2) | (int(counter) & 0x3)) & 0xFF
    return (f_byte & 0x3F, (f_byte >> 6) & 0x3)


def _fingerprint(address: int, command: int) -> str:
    """The identity string, through the one function that formats them.

    Imported inside the call rather than at module scope: this module is
    reached from a store migration hook, and the registry that
    ``protocol_decode`` builds at import time has no business running
    that early.
    """
    from .protocol_decode import format_fingerprint

    return format_fingerprint(DYSON, address, command, None)


def migrate_row(row: dict[str, Any]) -> bool:
    """Remap one serialized row in place. True when it changed.

    Works on the raw dict rather than a model so it can run inside a
    store migration hook, before anything has been parsed into objects.
    A row that is not Dyson, or that is missing the fields the remap
    needs, is left exactly as it is.
    """
    if (row.get("decoded_protocol") or "").upper() != DYSON:
        return False
    command = row.get("decoded_command")
    address = row.get("decoded_address")
    if command is None or address is None:
        return False
    extras = row.get("decoded_extras") or {}
    try:
        new_command, new_counter = remap_fields(
            int(command), int(extras.get("counter", 0) or 0)
        )
    except (TypeError, ValueError):
        return False

    row["decoded_command"] = new_command
    merged = dict(extras)
    merged["counter"] = new_counter
    row["decoded_extras"] = merged
    # The counter is press state and never rides the fingerprint, so the
    # identity string is a function of the address and the new command
    # alone. Recomputed rather than string-edited: the format lives in
    # one constant and this must not become a second spelling of it.
    row["decoded_fingerprint"] = _fingerprint(int(address), new_command)
    return True


def migrate_rows(rows: list[dict[str, Any]]) -> int:
    """Remap every Dyson row in a serialized list. Returns the count."""
    return sum(1 for row in rows if migrate_row(row))


def migrate_device_store(data: dict[str, Any]) -> int:
    """Remap every Dyson command in a serialized device store."""
    changed = 0
    for device in data.get("devices") or []:
        if isinstance(device, dict):
            changed += migrate_rows(
                [c for c in (device.get("commands") or []) if isinstance(c, dict)]
            )
    if changed:
        _LOGGER.info(
            "Dyson counter split: remapped %d stored command(s) so they "
            "transmit the frame they always did", changed
        )
    return changed


def migrate_signal_store(data: dict[str, Any]) -> int:
    """Remap every Dyson row in a serialized unknown-signal catalog.

    The catalog nests signals under devices; both shapes are walked so
    a schema that moves them does not silently skip the remap.
    """
    changed = 0
    for key in ("devices", "signals"):
        for entry in data.get(key) or []:
            if not isinstance(entry, dict):
                continue
            if "signals" in entry:
                changed += migrate_rows(
                    [s for s in (entry.get("signals") or []) if isinstance(s, dict)]
                )
            else:
                changed += migrate_row(entry)
    if changed:
        _LOGGER.info(
            "Dyson counter split: remapped %d catalog signal(s)", changed
        )
    return changed


def retarget_dyson_triggers(triggers: Any) -> int:
    """Repoint DYSON trigger fingerprints by re-decoding their codes.

    A trigger has no triple to run the bijection on. Re-decoding the
    stored Pronto is both available and better: it is the same path a
    live press takes, so the trigger lands on exactly the identity the
    next press will produce.

    A trigger whose code will not decode keeps its old fingerprint and
    is named in the log rather than dropped. That row will stop matching
    until it is re-learned, and saying so is better than guessing at an
    identity for an automation.
    """
    from .ir_command import ProntoCommand
    from .protocol_decode import decode_to_fields

    changed = 0
    stranded: list[str] = []
    for trigger in triggers:
        old = getattr(trigger, "decoded_fingerprint", None)
        if not old or not old.upper().startswith(f"{DYSON}:"):
            continue
        code = getattr(trigger, "code", None)
        raw = None
        if code:
            try:
                raw = ProntoCommand(code).get_raw_timings()
            except (ValueError, IndexError):
                raw = None
        _, _, _, fingerprint = decode_to_fields(raw)
        if fingerprint is None:
            stranded.append(getattr(trigger, "name", "?"))
            continue
        if fingerprint != old:
            trigger.decoded_fingerprint = fingerprint
            changed += 1
    if changed:
        _LOGGER.info(
            "Dyson counter split: repointed %d trigger identity/ies", changed
        )
    if stranded:
        _LOGGER.warning(
            "Dyson counter split: %d trigger(s) could not be re-decoded from "
            "their stored code and keep their previous identity, so they will "
            "not match until re-learned: %s",
            len(stranded), ", ".join(stranded),
        )
    return changed
