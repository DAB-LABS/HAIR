"""Pin bindings: which command a Remote's trigger drives on each Device.

Signpost 4, Track 1 (derivation). A pinned Remote drives its pinned
Devices: every trigger on the remote maps to at most one command on
each pinned device, matched by CONTENT identity. Same content, same
button -- so a Remote and a Device minted from the same wig map
completely with no mapping UI, and a Remote pinned to two unrelated
devices sends volume to one and channel to the other purely because
that is where the content matches. Per-trigger targeting emerges; no
routing table exists.

The map is DERIVED and STORED (bound-trigger-remotes.md, open
question 2: "lean stored"). It is recomputed at pin and unpin, and
whenever content changes on either side -- never on the fire path,
which reads it and nothing more.

Identity tiers mirror ``HAIRStore.match_command`` exactly, scoped to
a single device:

1. decoded protocol identity (jitter-immune)
2. composite ``(S/L fingerprint, byte_hash)``, then ``byte_hash``
   alone (the unified-identity rescue for a boundary protocol whose
   fingerprint flips between captures)
3. bare S/L fingerprint, restricted to LEGACY commands

Tier 3's legacy restriction is not an optimization. It is the v0.5.8
rule: a hash-bearing command must never be reachable through a bare
fingerprint, or one Sony button's trigger would map onto its sibling
-- the exact collapse byte_hash identity exists to prevent. A pinned
remote that mapped that way would retransmit the wrong button, which
is worse than not mapping at all.

Derivation covers disabled triggers too. A disabled trigger fires
nothing and therefore retransmits nothing (the retransmit rides the
fire), so mapping it costs nothing and keeps the stored map stable
across enable/disable toggles instead of churning storage on a
checkbox.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .identity import (
    NormFpIndex,
    file_sourced_trigger,
    norm_fingerprint_of_code,
)

if TYPE_CHECKING:
    from .models import IRDevice, IRTrigger, TriggerRemote
    from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceCommandIndex:
    """Per-device reverse index over command identities.

    The single-device twin of the four ``_idx_*`` maps in
    ``HAIRStore._rebuild_command_index``. Built on demand rather than
    held on the store: derivation is a user-action-paced operation
    over a handful of devices, and a cached per-device index would be
    one more thing to invalidate on every command mutation for no
    measurable gain.
    """

    decoded: dict[str, str] = field(default_factory=dict)
    fp_bytehash: dict[tuple[str, str | None], str] = field(default_factory=dict)
    bytehash: dict[str, str] = field(default_factory=dict)
    fp_legacy: dict[str, str] = field(default_factory=dict)
    # The receiver-tolerant tier (2026-08-18), built only for commands
    # whose bytes never came through a receiver. This is what lets a
    # trigger minted from a wig bind to the same wig's command on a
    # device: neither side's byte hash is what the air would produce,
    # but both were computed from the same file.
    norm_fp: NormFpIndex = field(default_factory=NormFpIndex)

    def __bool__(self) -> bool:
        return bool(
            self.decoded
            or self.fp_bytehash
            or self.bytehash
            or self.fp_legacy
            or self.norm_fp
        )


def build_device_index(device: IRDevice) -> DeviceCommandIndex:
    """Index one device's commands by every identity tier.

    Last-write-wins on a collision, matching the store's global index
    so a device whose commands share an identity resolves the same way
    here as it does for the known-command matcher.
    """
    from .identity import (
        canonical_fingerprint,
        file_sourced_command,
        norm_fingerprint_of_code,
    )

    index = DeviceCommandIndex()
    for cmd in device.commands:
        # Per-command resilience (GH #108): a row that cannot produce an
        # identity costs itself, not the whole pin map.
        try:
            if file_sourced_command(cmd, device):
                index.norm_fp.add(
                    norm_fingerprint_of_code(cmd.code),
                    cmd.byte_hash or cmd.code,
                    cmd.id,
                )
            if cmd.decoded_fingerprint:
                index.decoded[cmd.decoded_fingerprint] = cmd.id
            # Canonical (wire) form, so a capture-minted trigger and a
            # wig-adopted command meet on the same identity (identity.py).
            fp = canonical_fingerprint(
                cmd.protocol, cmd.code, cmd.raw_timings
            )
        except Exception:
            _LOGGER.warning(
                "Skipping command '%s' (%s) on device '%s' (%s) while "
                "building its pin map: its identity could not be computed "
                "from its stored code",
                getattr(cmd, "name", "?"),
                getattr(cmd, "id", "?"),
                getattr(device, "name", "?"),
                getattr(device, "id", "?"),
            )
            continue
        if not fp:
            continue
        index.fp_bytehash[(fp, cmd.byte_hash)] = cmd.id
        if cmd.byte_hash is None:
            index.fp_legacy[fp] = cmd.id
        else:
            index.bytehash[cmd.byte_hash] = cmd.id
    return index


def match_on_device(
    index: DeviceCommandIndex,
    decoded_fingerprint: str | None,
    signal_fingerprint: str | None,
    byte_hash: str | None,
    norm_fp: str | None = None,
) -> str | None:
    """Return the command id on this device matching an identity, or None.

    Tier order is ``HAIRStore.match_command``'s, and the fall-through
    rule is the same one: an identity carrying a byte_hash that missed
    every hash-aware tier must NOT drop onto a hash-bearing command via
    the bare fingerprint. ``fp_legacy`` holds only hashless commands, so
    that block is structural rather than a guard that can be forgotten.
    """
    if decoded_fingerprint and decoded_fingerprint in index.decoded:
        return index.decoded[decoded_fingerprint]
    if not (signal_fingerprint or byte_hash):
        return None
    cmd_id = index.fp_bytehash.get((signal_fingerprint, byte_hash))
    if cmd_id is not None:
        return cmd_id
    if byte_hash is not None:
        cmd_id = index.bytehash.get(byte_hash)
        if cmd_id is not None:
            return cmd_id
    if signal_fingerprint:
        cmd_id = index.fp_legacy.get(signal_fingerprint)
        if cmd_id is not None:
            return cmd_id
    # Lowest tier, and only when the caller supplied a value: a
    # file-sourced trigger against a file-sourced command.
    if norm_fp and not decoded_fingerprint:
        return index.norm_fp.get(norm_fp)
    return None


def triggers_of_remote(store: HAIRStore, remote_id: str) -> list[IRTrigger]:
    """Every trigger owned by ``remote_id``, in stored order."""
    return [
        t
        for t in store.get_all_triggers_ordered()
        if t.trigger_remote_id == remote_id
    ]


def derive_bindings(
    store: HAIRStore, remote: TriggerRemote
) -> dict[str, dict[str, str]]:
    """Compute ``{device_id: {trigger_id: command_id}}`` for one remote.

    Only pinned devices appear. A device that still exists but matches
    nothing keeps an empty map rather than vanishing, so the detail
    page can tell "pinned, nothing matched" apart from "not pinned".
    A pinned device id that no longer resolves is dropped entirely --
    it has no commands to drive.
    """
    bindings: dict[str, dict[str, str]] = {}
    triggers = triggers_of_remote(store, remote.id)
    for device_id in remote.pinned_device_ids:
        device = store.get_device(device_id)
        if device is None:
            continue
        index = build_device_index(device)
        mapped: dict[str, str] = {}
        for trigger in triggers:
            # The lowest tier is offered only when BOTH sides are file
            # records: a wig-minted trigger and the same wig's command
            # on an adopted device hold identities computed from one
            # file, and neither is what the air would produce.
            tolerant = None
            if not trigger.decoded_fingerprint and file_sourced_trigger(
                trigger, store
            ):
                tolerant = norm_fingerprint_of_code(trigger.code)
            cmd_id = match_on_device(
                index,
                trigger.decoded_fingerprint,
                trigger.signal_fingerprint,
                trigger.byte_hash,
                tolerant,
            )
            if cmd_id is not None:
                mapped[trigger.id] = cmd_id
        bindings[device_id] = mapped
    return bindings


def rederive_remote(store: HAIRStore, remote: TriggerRemote) -> bool:
    """Recompute one remote's bindings in place. True if they changed.

    The caller owns persistence. This mutates the remote and reports
    whether a save is warranted, so a batch (one command edit touching
    several pinned remotes) folds into a single write.

    Deliberately does NOT call ``store.update_trigger_remote``: that
    method re-assigns the store's dict entry to an object already in it,
    so for a remote obtained FROM the store the mutation above is
    already visible and the call is a no-op that only muddies the
    "derivation mutates, callers save" rule -- and, at the pin and unpin
    handlers, would double a call those handlers already make.
    """
    fresh = derive_bindings(store, remote)
    if fresh == remote.bindings:
        return False
    remote.bindings = fresh
    _LOGGER.debug(
        "Pin bindings rederived for remote %s: %s",
        remote.id,
        {d: len(m) for d, m in fresh.items()},
    )
    return True


def rederive_remotes_for_device(store: HAIRStore, device_id: str) -> bool:
    """Recompute every remote pinned to ``device_id``. True if any changed.

    The device side stores nothing of its own (signpost 3's pin scope
    split keeps the link in exactly one place), so "what changed for
    this device" is answered by scanning the remotes that point at it.
    Remote counts are small and this runs on command mutations, which
    are user actions.
    """
    changed = False
    for remote in store.get_all_trigger_remotes():
        if device_id in remote.pinned_device_ids:
            changed = rederive_remote(store, remote) or changed
    return changed


def rederive_all_pinned(store: HAIRStore) -> bool:
    """Recompute every pinned remote's map. True if any changed.

    The blunt instrument, used where precision buys nothing: a trigger
    was added, edited or deleted somewhere, and resolving exactly which
    remote owned it would mean threading the owning id through delete
    paths that currently report only success. Remote counts are small,
    derivation is a dict build over one device's commands, and these
    are user actions -- so recomputing all of them is cheaper than the
    bookkeeping needed to recompute one, and it cannot go stale by
    missing a case.
    """
    changed = False
    for remote in store.get_all_trigger_remotes():
        if remote.pinned_device_ids:
            changed = rederive_remote(store, remote) or changed
    return changed


def bound_targets(
    store: HAIRStore, remote_id: str, trigger_id: str
) -> list[tuple[str, str]]:
    """Return ``[(device_id, command_id)]`` a confirmed fire should drive.

    The fire path's only read. Returns an empty list for an unknown
    remote, an unpinned one, or a trigger that mapped nowhere -- all of
    which mean the same thing at the fire: send nothing, the event
    still fires for automations.

    Bindings are read as STORED, never recomputed here: derivation is a
    mutation-time job (see the module docstring), and doing content
    matching on the capture path would put an index build behind every
    press.
    """
    remote = store.get_trigger_remote(remote_id)
    if remote is None:
        return []
    targets: list[tuple[str, str]] = []
    for device_id in remote.pinned_device_ids:
        command_id = remote.bindings.get(device_id, {}).get(trigger_id)
        if command_id is not None:
            targets.append((device_id, command_id))
    return targets
