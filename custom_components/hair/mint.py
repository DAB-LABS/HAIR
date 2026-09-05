"""One constructor for the final make-the-record step.

FIVE DOORS MINTED COMMANDS AND NONE OF THEM AGREED (GH #134 review 2).
Save-captured decoded at save; the STATE mint and wig adopt copied a
pre-derived identity; the Mirror door copied a fingerprint from a
trigger and filled nothing else in; the retired cell-row mint filled in
neither. Each was right about its own case and none of them knew about
the coverage verdict, which is exactly how a field added in one place
goes missing in four.

WHAT THIS IS NOT. It is not a capture pipeline and not a decoder: the
payload arrives already normalized, in one of three shapes, and this
turns it into an ``IRCommand``. The signal-to-command adapter
(``signal_monitor._apply_signal_provenance``) stays where it is and
keeps its own name -- it carries a stored catalog signal's user
decisions onto a new row, which is a different job from minting one,
and tests call it directly.

Decode-free mints are legal and ordinary. A trigger whose code will not
convert to timings still becomes a command; it simply will not transmit
canonically, which is what a row with no decode has always done.
"""
from __future__ import annotations

from typing import Any

from .models import CommandCategory, CommandSource, IRCommand


def _knob(explicit: Any, fallback: Any, floor: int) -> int:
    """Resolve one TX knob with the None-vs-0 sentinel precedence.

    The same precedence ``_apply_signal_provenance`` documents, for the
    same reason: ``0 or X`` and ``1 or X`` short-circuit under Python
    truthiness, so a truthy fallback cannot tell "caller passed 0" from
    "caller passed nothing". None means nothing was passed.
    """
    value = fallback if explicit is None else explicit
    if value is None:
        value = floor
    return max(floor, int(value))


def mint_command(
    *,
    name: str,
    category: CommandCategory = CommandCategory.CUSTOM,
    source: CommandSource = CommandSource.CAPTURED,
    protocol: str | None = None,
    code: str | None = None,
    raw_timings: list[int] | None = None,
    frequency: int | None = None,
    send_count: int | None = None,
    repeat_count: int | None = None,
    tx_force_raw: bool = False,
    identity: Any = None,
    byte_hash: Any = None,
    comb_suspect: bool = False,
    comb_finding: Any = None,
    sent_state: dict[str, Any] | None = None,
    matrix_cell: dict[str, Any] | None = None,
    plucked_command_name: str | None = None,
) -> IRCommand:
    """Build one command record.

    ``identity`` is anything carrying the five decoded fields plus the
    coverage verdict -- a ``WigSignalIdentity`` or a ``DecodedIdentity``
    read off the bytes -- or None for a decode-free mint. ``byte_hash``
    overrides the identity's own, for the one door that copies a
    trigger's hash rather than deriving it.
    """
    command = IRCommand(
        name=name,
        category=category,
        source=source,
        protocol=protocol,
        code=code,
        raw_timings=list(raw_timings) if raw_timings else None,
        comb_suspect=comb_suspect,
        comb_finding=comb_finding,
        sent_state=dict(sent_state) if sent_state else None,
        matrix_cell=dict(matrix_cell) if matrix_cell else None,
        plucked_command_name=plucked_command_name,
        tx_force_raw=bool(tx_force_raw),
    )
    if frequency is not None:
        command.frequency = frequency
    command.send_count = _knob(send_count, None, 1)
    if repeat_count is not None:
        command.repeat_count = max(0, int(repeat_count))
    apply_identity(command, identity)
    if byte_hash is not None:
        command.byte_hash = byte_hash
    return command


def apply_identity(command: IRCommand, identity: Any) -> None:
    """Stamp the five decoded fields and the verdict onto a command.

    ALL FIVE OR NONE. A triple beside a fingerprint that was not derived
    from the same read is the failure this whole change is about, so
    there is no path here that fills in some of them.
    """
    if identity is None:
        command.decoded_protocol = None
        command.decoded_address = None
        command.decoded_command = None
        command.decoded_fingerprint = None
        command.decoded_extras = None
        command.decode_covers = None
        return
    # WHICH SPELLING, decided once from the shape of the object rather
    # than field by field. A WigSignalIdentity carries BOTH
    # ``decoded_fingerprint`` (the protocol identity) and
    # ``fingerprint`` (the S/L signal fingerprint), and they are not the
    # same fact. Falling back per field would put the second in the slot
    # meant for the first on any wig row that did not decode -- an
    # identity nothing derived, which is the exact failure this change
    # exists to prevent.
    prefixed = hasattr(identity, "decoded_fingerprint")
    def read(name: str) -> Any:
        return getattr(identity, f"decoded_{name}" if prefixed else name, None)

    extras = read("extras")
    command.decoded_protocol = read("protocol")
    command.decoded_address = read("address")
    command.decoded_command = read("command")
    command.decoded_fingerprint = read("fingerprint")
    command.decoded_extras = dict(extras) if extras else None
    covers = getattr(identity, "decode_covers", None)
    if covers is None:
        covers = getattr(identity, "covers_capture", None)
    command.decode_covers = covers
    hash_value = getattr(identity, "byte_hash", None)
    if hash_value is not None:
        command.byte_hash = hash_value


def mint_from_code(
    *,
    name: str,
    code: str | None,
    protocol: str | None,
    byte_hash: Any = None,
    claimed_fingerprint: Any = None,
    source: CommandSource = CommandSource.CAPTURED,
) -> IRCommand:
    """Mint from a bare code, deriving what can be derived (door 11).

    THE REPAIR RULE (GH #134 review 2). This door used to copy a
    trigger's ``decoded_fingerprint`` across and fill in none of the
    triple beside it, leaving a row that claims an identity nothing
    here derived. All five fields are re-derived from the code. Where
    the derivation disagrees with the copied fingerprint the copy is
    discarded rather than kept, because a fingerprint whose triple we
    could not reproduce cannot be transmitted from.

    Rows already stored half-stamped are left alone; the load backfill
    judges them, and inventing a migration for them would be inventing
    identities.
    """
    from .ir_command import ProntoCommand
    from .protocol_decode import try_decode_identity

    raw_timings = None
    if code:
        try:
            raw_timings = ProntoCommand(code).get_raw_timings()
        except Exception:  # a bad code just will not transmit yet
            raw_timings = None
    identity = try_decode_identity(raw_timings)
    if (
        identity is not None
        and claimed_fingerprint
        and identity.fingerprint != claimed_fingerprint
    ):
        identity = None
    return mint_command(
        name=name,
        source=source,
        protocol=protocol,
        code=code,
        raw_timings=raw_timings,
        identity=identity,
        byte_hash=byte_hash,
    )
