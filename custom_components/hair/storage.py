"""Persistent storage for the HAIR integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    STORAGE_VERSION_MINOR,
)
from .models import IRDevice, IRTrigger, TriggerRemote

_LOGGER = logging.getLogger(__name__)

# Default display name for the HAIR Triggers drawer (Trigger Remotes
# signpost 1, Track B). Matches event.TRIGGER_DEVICE_NAME's literal
# value; kept as a separate constant rather than an import to avoid a
# circular import (event.py -> trigger_manager.py -> this module).
_DEFAULT_TRIGGER_DRAWER_NAME = "HAIR Triggers"


class _HAIRDeviceStore(Store):
    """``Store`` subclass so the migration hook is actually invoked.

    HA's ``Store.async_load`` calls ``_async_migrate_func`` on the Store
    instance. Before v0.4.0, ``HAIRStore`` composed a plain ``Store`` and
    defined ``_async_migrate_func`` on the wrapper, so the override was
    never called and the base raised ``NotImplementedError`` on any
    version mismatch -- the first ``STORAGE_VERSION_MINOR`` bump would
    fail every install's load. Subclassing is the standard HA pattern.
    v0.4.0 backfills the new decoded fields in-application (no version
    bump), but the scaffold must be real before any future schema
    migration ships.
    """

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Migrate storage schema between versions.

        v1.1 is the initial schema. Future migrations bump
        ``STORAGE_VERSION_MINOR`` (or ``STORAGE_VERSION`` for breaking
        changes) and add branches here.
        """
        _LOGGER.info(
            "Migrating HAIR device store from v%s.%s to v%s.%s",
            old_major_version,
            old_minor_version,
            STORAGE_VERSION,
            STORAGE_VERSION_MINOR,
        )
        return old_data


class HAIRStore:
    """Manage persistent storage of IR devices and commands.

    Uses HA's versioned Store. Migrations run when the on-disk
    major/minor version is older than STORAGE_VERSION/STORAGE_VERSION_MINOR.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = _HAIRDeviceStore(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            minor_version=STORAGE_VERSION_MINOR,
            atomic_writes=True,
        )
        self._data: dict[str, IRDevice] = {}
        self._triggers: dict[str, IRTrigger] = {}
        # Named trigger remotes (Add Popups signpost 2, Track 1B). The
        # HAIR Triggers drawer is NOT stored here -- it is the implicit
        # ``IRTrigger.trigger_remote_id is None`` default, so there is
        # no row to accidentally delete and the non-deletable-drawer
        # rule needs no special-case guard.
        self._trigger_remotes: dict[str, TriggerRemote] = {}
        # The HAIR Triggers drawer's own display name (Trigger Remotes
        # signpost 1, Track B: header rename-in-place). A plain scalar,
        # not part of any IRTrigger -- there is exactly one drawer for
        # signpost 1, so this is not modeled as a list-backed entity the
        # way devices/triggers are. Deliberately a local literal rather
        # than importing event.TRIGGER_DEVICE_NAME: event.py imports
        # trigger_manager.py, which imports this module, so importing
        # event.py from here would be circular.
        self._trigger_drawer_name: str = _DEFAULT_TRIGGER_DRAWER_NAME
        self._loaded = False
        # Reverse indexes for the known-command matcher (Phase B). Map a
        # signal's identity to the (device_id, command_id) that owns it, so
        # the signal monitor can decide "is this an already-assigned
        # command?" with O(1) lookups instead of an exact code-string scan
        # (the v0.3.4 byte-hash tiebreaker and native-path re-encoding made
        # that scan miss). Tiered by precision: decoded protocol identity,
        # then (S/L fingerprint, byte_hash), then S/L fingerprint alone.
        # Rebuilt wholesale on load and on any device mutation; device
        # counts are small and mutations are user actions, not a hot path.
        self._idx_decoded: dict[str, tuple[str, str]] = {}
        self._idx_fp_bytehash: dict[tuple[str, str | None], tuple[str, str]] = {}
        # Byte_hash-only tier (v0.5.8 unified identity): rescues captures
        # whose S/L fingerprint flipped across the classification boundary
        # (Sony) but whose byte_hash still matches the assigned command.
        # Consulted after the composite key, before the legacy tier.
        self._idx_bytehash: dict[str, tuple[str, str]] = {}
        # Bare-fingerprint tier: LEGACY commands only (byte_hash is None)
        # since v0.5.8. See _rebuild_command_index.
        self._idx_fp: dict[str, tuple[str, str]] = {}
        # Fingerprints with at least one hash-bearing command; diagnostic
        # only (the blocked-legacy-match DEBUG log in match_command).
        self._fps_with_hashed: set[str] = set()

    @property
    def loaded(self) -> bool:
        return self._loaded

    async def async_load(self) -> None:
        """Load data from storage. Safe to call multiple times."""
        raw = await self._store.async_load()
        if raw is None:
            self._data = {}
            self._triggers = {}
            self._trigger_remotes = {}
            self._trigger_drawer_name = _DEFAULT_TRIGGER_DRAWER_NAME
            self._loaded = True
            return

        devices_raw = raw.get("devices") or []
        self._data = {}
        for entry in devices_raw:
            try:
                device = IRDevice.from_dict(entry)
            except Exception as err:
                _LOGGER.warning(
                    "Skipping malformed device entry %s: %s",
                    entry.get("id"),
                    err,
                )
                continue
            self._data[device.id] = device

        triggers_raw = raw.get("triggers") or []
        self._triggers = {}
        for entry in triggers_raw:
            try:
                trigger = IRTrigger.from_dict(entry)
            except Exception as err:
                _LOGGER.warning(
                    "Skipping malformed trigger entry %s: %s",
                    entry.get("id"),
                    err,
                )
                continue
            self._triggers[trigger.id] = trigger

        # Named trigger remotes (signpost 2, Track 1B). Absent on every
        # store written before this field existed -- resolves to {},
        # matching every IRTrigger in it reading trigger_remote_id as
        # None (drawer-owned), which is exactly correct: there is
        # nothing to migrate, the drawer already held them.
        remotes_raw = raw.get("trigger_remotes") or []
        self._trigger_remotes = {}
        for entry in remotes_raw:
            try:
                remote = TriggerRemote.from_dict(entry)
            except Exception as err:
                _LOGGER.warning(
                    "Skipping malformed trigger remote entry %s: %s",
                    entry.get("id"),
                    err,
                )
                continue
            self._trigger_remotes[remote.id] = remote

        # Absent (pre-Track-B store) or blank both resolve to the
        # module default -- there is no prior source of truth to
        # backfill a rename from.
        self._trigger_drawer_name = (
            raw.get("trigger_drawer_name") or _DEFAULT_TRIGGER_DRAWER_NAME
        )

        # v0.4.0 backfill: decode stored commands into their decoded_*
        # fields. v0.5.8 backfills: compute byte_hash for pre-0.3.4 commands
        # that carry a Pronto code, so the legacy bare-fingerprint matcher
        # tier empties out; and decode stored trigger codes into
        # decoded_fingerprint (unified identity -- decoded only, NEVER
        # byte_hash: decode is checksum-validated so a snapped code decodes
        # to the same identity or to None, while a recomputed hash could
        # mismatch live captures and silence the trigger, a tier-2 miss
        # being fatal). All run BEFORE the index rebuild (the index shape
        # depends on byte_hash presence) and fold into one save.
        changed = self._backfill_decoded_fields()
        changed = self._backfill_byte_hash() or changed
        changed = self._backfill_trigger_decoded() or changed
        changed = self._backfill_canonical_identity() or changed
        changed = self._backfill_trigger_order() or changed
        changed = self._backfill_pin_bindings() or changed
        self._rebuild_command_index()
        self._loaded = True
        if changed:
            await self.async_save()

    async def async_save(self) -> None:
        """Persist current in-memory state."""
        await self._store.async_save(self._serialize())

    def _serialize(self) -> dict[str, Any]:
        return {
            "devices": [d.to_dict() for d in self._data.values()],
            "triggers": [t.to_dict() for t in self._triggers.values()],
            "trigger_remotes": [
                r.to_dict() for r in self._trigger_remotes.values()
            ],
            "trigger_drawer_name": self._trigger_drawer_name,
        }

    # -----------------------------------------------------------------
    # Known-command reverse index (Phase B matcher)
    # -----------------------------------------------------------------

    def _rebuild_command_index(self) -> None:
        """Rebuild the known-command reverse indexes from current devices.

        ``_idx_fp`` (the bare-fingerprint tier) only indexes commands whose
        OWN ``byte_hash`` is None (v0.5.8): a command that carries a hash is
        matchable only via its decoded identity, the composite key, or the
        byte_hash-only tier, so distinct sub-threshold buttons (Sony et al)
        stop collapsing onto an assigned sibling. ``_idx_bytehash`` (unified
        identity) maps each command's hash alone, so a capture whose S/L
        fingerprint flipped across the classification boundary still
        resolves to its command. Two commands sharing a byte_hash (the RC-6
        2T/3T bin-share corner) is last-write-wins; the overwrite is
        DEBUG-logged so the ambiguity is visible in diagnostics rather than
        silent. ``_fps_with_hashed`` records which fingerprints have at
        least one hash-bearing command, purely for the diagnostic log in
        ``match_command``.
        """
        from .identity import canonical_fingerprint

        self._idx_decoded = {}
        self._idx_fp_bytehash = {}
        self._idx_bytehash = {}
        self._idx_fp = {}
        self._fps_with_hashed: set[str] = set()
        for device in self._data.values():
            for cmd in device.commands:
                ref = (device.id, cmd.id)
                if cmd.decoded_fingerprint:
                    self._idx_decoded[cmd.decoded_fingerprint] = ref
                # Canonical (wire) form, always: a command minted from
                # a wig carries file text, and a real press arrives as
                # wire text. See identity.py's canonical-form block.
                fp = canonical_fingerprint(
                    cmd.protocol, cmd.code, cmd.raw_timings
                )
                if fp:
                    self._idx_fp_bytehash[(fp, cmd.byte_hash)] = ref
                    if cmd.byte_hash is None:
                        self._idx_fp[fp] = ref
                    else:
                        prev = self._idx_bytehash.get(cmd.byte_hash)
                        if prev is not None and prev != ref:
                            _LOGGER.debug(
                                "byte_hash %s is shared by commands %s and "
                                "%s (RC-6-class bin collision); the "
                                "hash-only matcher tier keeps the latter",
                                cmd.byte_hash,
                                prev,
                                ref,
                            )
                        self._idx_bytehash[cmd.byte_hash] = ref
                        self._fps_with_hashed.add(fp)

    def _backfill_pin_bindings(self) -> bool:
        """Recompute every pinned remote's derived button map at load.

        Signpost 4, Track 1. Runs AFTER the decoded/byte_hash/trigger
        backfills, because derivation matches on exactly the identity
        fields those fill -- deriving first would map on tier 3 alone
        and produce a weaker map than the same content deserves.

        Deliberately derives ALL pinned remotes rather than only those
        with an empty map. It costs remotes x pinned-devices x triggers
        on a path that already walks every device, it fills in remotes
        pinned during signpost 3's dark period (pins existed, bindings
        did not), and it means a restart repairs a map that drifted --
        a mutation wire that is missed shows up as "correct after a
        restart" rather than as a wrong retransmit that never heals.
        Returns True when anything changed, folding into async_load's
        single save like the other backfills.
        """
        from .pin_bindings import rederive_remote

        changed = False
        for remote in self._trigger_remotes.values():
            if not remote.pinned_device_ids:
                continue
            changed = rederive_remote(self, remote) or changed
        return changed

    def _backfill_trigger_decoded(self) -> bool:
        """Decode stored trigger codes into ``decoded_fingerprint`` in place.

        Unified identity (v0.5.8): runs once at load, mirrors
        ``_backfill_decoded_fields``, folds into the single load-time save.
        Gives pre-upgrade triggers the jitter-immune tier-1 identity the
        moment a decoder exists for their protocol.

        Deliberately does NOT touch ``byte_hash``: decode is
        tolerance-based and checksum-validated (a snapped or re-encoded
        stored code decodes to the same identity or to None -- never to a
        wrong-but-plausible one), while a recomputed byte_hash is
        bin-quantized and snap-fragile, and a tier-2 mismatch is fatal
        with no tier-3 fallthrough -- it would permanently silence the
        trigger. Legacy triggers keep their broad semantics.
        """
        from .ir_command import ProntoCommand
        from .protocol_decode import decode_to_fields

        changed = 0
        for trigger in self._triggers.values():
            if trigger.decoded_fingerprint or not trigger.code:
                continue
            try:
                raw = ProntoCommand(trigger.code).get_raw_timings()
            except (ValueError, IndexError):
                raw = None
            _, _, _, fingerprint = decode_to_fields(raw)
            if fingerprint is None:
                continue
            trigger.decoded_fingerprint = fingerprint
            changed += 1
        if changed:
            _LOGGER.info(
                "Backfilled decoded protocol identity on %d trigger(s)",
                changed,
            )
        return changed > 0

    def _backfill_trigger_order(self) -> bool:
        """Assign ``order`` to triggers that predate Trigger Remotes signpost 1.

        Mirrors ``_backfill_trigger_decoded``: runs once at load, mutates
        in place, returns True when anything changed so ``async_load``
        persists a single combined save. Each order-less trigger gets its
        current position in the stored (insertion-ordered) list, so a
        pre-upgrade catalog keeps listing in the order it always has
        instead of every legacy trigger tying at the same value. A
        running counter (rather than a bare ``enumerate``) also tolerates
        a mixed store -- some triggers already carrying an explicit order
        -- by never handing out a value that collides with one already
        seen.
        """
        changed = False
        next_order = 0
        for trigger in self._triggers.values():
            if trigger.order is not None:
                next_order = max(next_order, trigger.order + 1)
                continue
            trigger.order = next_order
            next_order += 1
            changed = True
        if changed:
            _LOGGER.info("Backfilled order on trigger(s) missing one")
        return changed

    def _backfill_byte_hash(self) -> bool:
        """Compute ``byte_hash`` for stored commands that predate v0.3.4.

        Mirrors ``_backfill_decoded_fields``: runs once at load, mutates in
        place, returns True when anything changed so ``async_load`` persists
        a single combined save. A command with no Pronto code (legacy
        protocol/code pairs, raw-only) hashes to None and stays on the
        legacy bare-fingerprint matcher tier, which is correct because its
        captured signals hash to None through the same code path.
        """
        from .identity import canonical_byte_hash

        changed = False
        for device in self._data.values():
            for cmd in device.commands:
                if cmd.byte_hash is not None:
                    continue
                # Canonical (wire) form, like every other hash in HAIR
                # since 2026-08-17 -- identity.py's canonical-form block.
                bh = canonical_byte_hash(cmd.code)
                if bh is not None:
                    cmd.byte_hash = bh
                    changed = True
        return changed

    def _backfill_canonical_identity(self) -> bool:
        """Move stored identity onto the canonical (wire) form.

        WHAT THIS REPAIRS. Until 2026-08-17 every mint door that started
        from a FILE Pronto -- a closet wig adopted as a Device, USEd as a
        Remote, a Clipper paste, a Plucker place -- hashed the file text.
        A real press arrives rebuilt from raw timings, which drops the
        trailing gap word (identity.py's canonical-form block has the
        mechanism and the measured numbers), so those records carried an
        identity nothing on the air could match: 121 of 943 flat closet
        signals and 23 of 272 wig-adopted device commands, all of them
        undecoded, silently never matched. Decoded records were unhurt --
        tier 1 is computed from timings, so it never moved.

        THE STORED PRONTO TEXT IS NEVER REWRITTEN. Only identity fields
        move. A wig's claim digests hash the code text as written
        (``wig_format.row_digest``), so rewriting it would invalidate
        every fitting ever signed; and the text is what a person reads,
        copies and pastes. Bench-verified: digests are stable across
        this backfill, and the digest of the wire text differs.

        Runs BEFORE ``_rebuild_command_index`` with the other backfills,
        because the index keys on exactly these values. Canonicalization
        is idempotent (verified over 1,411 closet codes), so this is a
        no-op from the second boot on and folds into the one load-time
        save when it does change something.
        """
        from .identity import (
            canonical_byte_hash,
            canonical_fingerprint,
            canonical_pronto,
        )

        changed = commands = triggers = 0
        for device in self._data.values():
            for cmd in device.commands:
                # Only rows whose code is readable Pronto have a wire
                # form at all. A legacy protocol/code pair or a
                # hand-written record keeps exactly the identity it has.
                if not cmd.code or canonical_pronto(cmd.code) is None:
                    continue
                fresh = canonical_byte_hash(cmd.code)
                if fresh is not None and fresh != cmd.byte_hash:
                    cmd.byte_hash = fresh
                    commands += 1
                    changed += 1
        for trigger in self._triggers.values():
            if not trigger.code or canonical_pronto(trigger.code) is None:
                continue
            moved = False
            # REPOINT an existing hash; never ADD one. A trigger that
            # has no byte_hash is a pre-0.5.8 legacy row matching
            # broadly on its fingerprint, and v0.5.8 ruled deliberately
            # that the load-time backfill must not narrow it (a snapped
            # code could then mismatch the live capture and the trigger
            # would go silent, a tier-2 miss being fatal). What was
            # wrong was hashing the FILE form, so that is what this
            # repairs -- it does not change which tier a row matches on.
            if trigger.byte_hash is not None:
                fresh_hash = canonical_byte_hash(trigger.code)
                if fresh_hash is not None and fresh_hash != trigger.byte_hash:
                    trigger.byte_hash = fresh_hash
                    moved = True
            fresh_fp = canonical_fingerprint(
                trigger.protocol, trigger.code, None
            )
            if fresh_fp and fresh_fp != trigger.signal_fingerprint:
                trigger.signal_fingerprint = fresh_fp
                moved = True
            if moved:
                triggers += 1
                changed += 1
        if changed:
            _LOGGER.info(
                "Canonical identity backfill: %d commands, %d triggers "
                "repointed onto the wire form (stored codes unchanged)",
                commands, triggers,
            )
        return bool(changed)

    def match_command(
        self,
        decoded_fingerprint: str | None,
        signal_fingerprint: str | None,
        byte_hash: str | None,
    ) -> tuple[str, str] | None:
        """Return the ``(device_id, command_id)`` a signal maps to, or None.

        Tiers, most precise first: decoded protocol identity, then the
        byte-level identity -- probed via the composite ``(S/L fingerprint,
        byte_hash)`` key first and the hash alone second (unified identity:
        the hash-only lookup is what recognizes an assigned command when a
        boundary protocol's fingerprint flips between captures, so the
        re-press is suppressed from the live feed instead of refiling as a
        new unknown) -- then the bare S/L fingerprint restricted to LEGACY
        commands (no byte_hash of their own, v0.5.8). An incoming signal
        whose byte_hash matched no command must not fall through to a
        hash-bearing command on the bare fingerprint: that false match is
        how assigning one Sony button used to swallow its siblings.
        """
        if decoded_fingerprint and decoded_fingerprint in self._idx_decoded:
            return self._idx_decoded[decoded_fingerprint]
        if signal_fingerprint or byte_hash:
            ref = self._idx_fp_bytehash.get((signal_fingerprint, byte_hash))
            if ref is not None:
                return ref
            if byte_hash is not None:
                ref = self._idx_bytehash.get(byte_hash)
                if ref is not None:
                    return ref
            ref = self._idx_fp.get(signal_fingerprint)
            if ref is not None:
                return ref
            if byte_hash is not None and signal_fingerprint in self._fps_with_hashed:
                _LOGGER.debug(
                    "Signal fp=%s hash=%s matched no command; a pre-v0.5.8 "
                    "matcher would have matched a hash-bearing command on "
                    "the bare fingerprint (blocked by byte_hash identity)",
                    signal_fingerprint,
                    byte_hash,
                )
        return None

    def _backfill_decoded_fields(self) -> bool:
        """Decode stored commands into their ``decoded_*`` fields in place.

        Runs once on load (v0.4.0). For each command with no
        ``decoded_fingerprint``, derive raw timings (from the stored field,
        or from the Pronto code) and try to decode. Returns True if any
        command was updated, so the caller can persist. Non-decodable
        commands are left untouched. Idempotent: a command that already
        carries a ``decoded_fingerprint`` is skipped.
        """
        from .ir_command import ProntoCommand
        from .protocol_decode import try_decode_identity

        changed = 0
        for device in self._data.values():
            for cmd in device.commands:
                if cmd.decoded_fingerprint:
                    continue
                raw = cmd.raw_timings
                if not raw and cmd.code:
                    try:
                        raw = ProntoCommand(cmd.code).get_raw_timings()
                    except (ValueError, IndexError):
                        raw = None
                identity = try_decode_identity(raw)
                if identity is None:
                    continue
                cmd.decoded_protocol = identity.protocol
                cmd.decoded_address = identity.address
                cmd.decoded_command = identity.command
                cmd.decoded_fingerprint = identity.fingerprint
                cmd.decoded_extras = (
                    dict(identity.extras) if identity.extras else None
                )
                changed += 1
        if changed:
            _LOGGER.info(
                "Backfilled decoded protocol identity on %d device command(s)",
                changed,
            )
        return changed > 0

    def get_device(self, device_id: str) -> IRDevice | None:
        return self._data.get(device_id)

    def get_all_devices(self) -> list[IRDevice]:
        return list(self._data.values())

    def add_device(self, device: IRDevice) -> None:
        self._data[device.id] = device
        self._rebuild_command_index()

    def update_device(self, device: IRDevice) -> None:
        self._data[device.id] = device
        self._rebuild_command_index()

    def remove_device(self, device_id: str) -> bool:
        if device_id in self._data:
            del self._data[device_id]
            self._rebuild_command_index()
            return True
        return False

    def reorder_devices(self, ordered_ids: list[str]) -> None:
        """Reorder the device list to match ``ordered_ids``.

        Persistence relies on dict insertion order, so the dict is
        rebuilt in the requested sequence (no schema change). The list
        must be exactly the current set of device ids -- no duplicates,
        unknown, or missing. The drag UI always sends the complete list,
        so any divergence is a stale client and is rejected loudly.
        Mirrors ``IRDevice.reorder_commands``.

        Raises :class:`ValueError` on mismatch and changes nothing.
        """
        if len(ordered_ids) != len(set(ordered_ids)):
            raise ValueError("Duplicate device ids in reorder list")
        current = set(self._data.keys())
        requested = set(ordered_ids)
        if requested != current:
            missing = current - requested
            unknown = requested - current
            details: list[str] = []
            if missing:
                details.append(f"missing {sorted(missing)}")
            if unknown:
                details.append(f"unknown {sorted(unknown)}")
            raise ValueError(
                "Reorder list does not match current devices: "
                + ", ".join(details)
            )
        self._data = {device_id: self._data[device_id] for device_id in ordered_ids}

    def get_devices_by_emitter(
        self, emitter_entity_id: str
    ) -> list[IRDevice]:
        return [
            d for d in self._data.values()
            if emitter_entity_id in d.emitter_entity_ids
        ]

    def get_devices_by_type(self, device_type: str) -> list[IRDevice]:
        return [
            d for d in self._data.values()
            if str(d.device_type) == str(device_type)
        ]

    # -----------------------------------------------------------------
    # Trigger CRUD
    # -----------------------------------------------------------------

    def get_trigger(self, trigger_id: str) -> IRTrigger | None:
        return self._triggers.get(trigger_id)

    def get_all_triggers(self) -> list[IRTrigger]:
        return list(self._triggers.values())

    def get_enabled_triggers(self) -> list[IRTrigger]:
        return [t for t in self._triggers.values() if t.enabled]

    def add_trigger(self, trigger: IRTrigger) -> None:
        if trigger.order is None:
            trigger.order = self._next_trigger_order()
        self._triggers[trigger.id] = trigger

    def update_trigger(self, trigger: IRTrigger) -> None:
        self._triggers[trigger.id] = trigger

    def remove_trigger(self, trigger_id: str) -> bool:
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False

    def _next_trigger_order(self) -> int:
        """Return the next ``order`` value for a newly created trigger.

        Appends to the end of the existing catalog, mirroring what
        ``order`` means for pre-existing triggers via the load-time
        backfill (list position).
        """
        existing = [
            t.order for t in self._triggers.values() if t.order is not None
        ]
        return (max(existing) + 1) if existing else 0

    def get_all_triggers_ordered(self) -> list[IRTrigger]:
        """Return triggers sorted by ``order`` (Trigger Remotes signpost 1).

        Every trigger has a non-None ``order`` by the time this can be
        called: the load-time backfill assigns one to every pre-existing
        trigger, and creation assigns one to every new one. The ``or 0``
        and id tiebreak are defense-in-depth for a trigger constructed
        directly (bypassing ``add_trigger``), not the expected path.
        """
        return sorted(
            self._triggers.values(),
            key=lambda t: (t.order if t.order is not None else 0, t.id),
        )

    def reorder_triggers(self, ordered_ids: list[str]) -> None:
        """Reorder triggers to match ``ordered_ids`` (Track B, item 7).

        Unlike ``reorder_devices`` (dict insertion order), ``IRTrigger``
        carries an explicit ``order`` int -- also read by the automation
        editor's device-trigger dropdown (Track A), so it must stay a
        real, comparable field rather than implicit position -- and
        reordering rewrites those values directly (0..N-1) instead of
        rebuilding a dict. Same validation contract as
        ``reorder_devices``/``IRDevice.reorder_commands``: the list must
        be exactly the current trigger id set, no dupes/missing/unknown.

        Raises :class:`ValueError` on mismatch and changes nothing.
        """
        if len(ordered_ids) != len(set(ordered_ids)):
            raise ValueError("Duplicate trigger ids in reorder list")
        current = set(self._triggers.keys())
        requested = set(ordered_ids)
        if requested != current:
            missing = current - requested
            unknown = requested - current
            details: list[str] = []
            if missing:
                details.append(f"missing {sorted(missing)}")
            if unknown:
                details.append(f"unknown {sorted(unknown)}")
            raise ValueError(
                "Reorder list does not match current triggers: "
                + ", ".join(details)
            )
        for index, trigger_id in enumerate(ordered_ids):
            self._triggers[trigger_id].order = index

    def get_trigger_drawer_name(self) -> str:
        """Return the HAIR Triggers drawer's current display name."""
        return self._trigger_drawer_name

    def set_trigger_drawer_name(self, name: str) -> None:
        """Rename the HAIR Triggers drawer (header rename-in-place)."""
        self._trigger_drawer_name = name

    # -----------------------------------------------------------------
    # Trigger remotes (Add Popups signpost 2, Track 1B)
    # -----------------------------------------------------------------

    def get_trigger_remote(self, remote_id: str) -> TriggerRemote | None:
        return self._trigger_remotes.get(remote_id)

    def get_all_trigger_remotes(self) -> list[TriggerRemote]:
        return list(self._trigger_remotes.values())

    def add_trigger_remote(self, remote: TriggerRemote) -> None:
        self._trigger_remotes[remote.id] = remote

    def update_trigger_remote(self, remote: TriggerRemote) -> None:
        self._trigger_remotes[remote.id] = remote

    def remove_trigger_remote(self, remote_id: str) -> list[IRTrigger] | None:
        """Delete a named remote AND every trigger it owns.

        Delete-takes-its-triggers (Release A ruling). There is no
        drawer row to protect here -- the drawer is not stored as a
        TriggerRemote at all, so a caller can never pass its id in.
        Returns the removed triggers (not just their ids) so the
        caller can sync/remove their event entities and clean up any
        device-registry state, mirroring how ``remove_device`` callers
        need the removed device's own data, not just a bool.

        Returns ``None`` (not ``[]``) when ``remote_id`` does not
        exist, so callers can tell "not found" apart from "found but
        owned zero triggers" -- both are legitimate but distinct
        outcomes for a WS delete handler's error reporting.
        """
        if remote_id not in self._trigger_remotes:
            return None
        del self._trigger_remotes[remote_id]
        removed = [
            t for t in self._triggers.values() if t.trigger_remote_id == remote_id
        ]
        for trigger in removed:
            del self._triggers[trigger.id]
        return removed

    def get_triggers_for_remote(self, remote_id: str | None) -> list[IRTrigger]:
        """Return triggers owned by ``remote_id`` (None = the drawer).

        Ordered the same way ``get_all_triggers_ordered`` orders the
        drawer's own rows, so a named remote's device-trigger dropdown
        and (later) detail-view rows sort consistently with it.
        """
        return sorted(
            (
                t
                for t in self._triggers.values()
                if t.trigger_remote_id == remote_id
            ),
            key=lambda t: (t.order if t.order is not None else 0, t.id),
        )

    def get_trigger_by_fingerprint(
        self, fingerprint: str
    ) -> IRTrigger | None:
        """Find a trigger by signal fingerprint (first match).

        Retained for callers that only need existence. Prefer
        :meth:`get_triggers_by_fingerprint` where multiple scoped triggers per
        fingerprint are possible (v0.5.7).

        NOT byte_hash-aware: on a sub-threshold remote (Sony et al) every
        button shares one fingerprint, so this can return a sibling's
        trigger. No production caller today; for matching, use
        :meth:`get_triggers_for_signal`, which applies the full identity.
        """
        for t in self._triggers.values():
            if t.signal_fingerprint == fingerprint:
                return t
        return None

    def get_triggers_by_fingerprint(
        self, fingerprint: str
    ) -> list[IRTrigger]:
        """Return all triggers bound to a signal fingerprint.

        Multiple triggers per fingerprint are legal (v0.5.7 location-aware
        scoping): one signal can drive several triggers with different receiver
        scopes. Returns every match so callers can present or scope them all.

        NOT byte_hash-aware: on a sub-threshold remote (Sony et al) this
        returns every button's trigger, since they share one fingerprint. No
        production caller today; for matching, use
        :meth:`get_triggers_for_signal`, which applies the full identity.
        """
        return [
            t
            for t in self._triggers.values()
            if t.signal_fingerprint == fingerprint
        ]

    def get_triggers_for_signal(
        self,
        protocol: str | None,
        code: str | None,
        fingerprint: str,
        byte_hash: str | None = None,
        decoded_fingerprint: str | None = None,
    ) -> list[IRTrigger]:
        """Find all enabled triggers matching a signal.

        Matching is the tiered identity rule (v0.5.8 unified identity,
        ``IRTrigger.matches_signal``): decoded > byte_hash > S/L
        fingerprint, highest shared tier decides. The protocol+code exact
        branch (legacy ESPHome-bridge captures) is kept as an additional
        way in, still gated by the byte-level rule so a sub-threshold
        sibling cannot ride in on a shared code representation.

        The old fingerprint-equality precondition is gone: a Sony capture
        whose S/L fingerprint flipped across the classification boundary
        still reaches its trigger via byte_hash. Legacy triggers (no hash,
        no decoded identity) keep matching on bare fingerprint, so
        pre-upgrade behavior is preserved for everything except the two
        failure classes this work fixes.
        """
        matches = []
        for t in self._triggers.values():
            if not t.enabled:
                continue
            exact_code = (
                t.protocol
                and t.code
                and protocol
                and code
                and t.protocol == protocol
                and t.code == code
            )
            if exact_code:
                # Same wire representation; still apply the byte-level rule
                # for consistency (a None-vs-None or equal-hash pair passes).
                if t.matches_byte_hash(byte_hash):
                    matches.append(t)
                continue
            if t.matches_signal(fingerprint, byte_hash, decoded_fingerprint):
                matches.append(t)
        return matches
