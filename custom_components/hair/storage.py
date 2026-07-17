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
from .models import IRDevice, IRTrigger

_LOGGER = logging.getLogger(__name__)


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
        from .event_parser import EventParser

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
                fp = EventParser.signal_fingerprint(
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

    def _backfill_byte_hash(self) -> bool:
        """Compute ``byte_hash`` for stored commands that predate v0.3.4.

        Mirrors ``_backfill_decoded_fields``: runs once at load, mutates in
        place, returns True when anything changed so ``async_load`` persists
        a single combined save. A command with no Pronto code (legacy
        protocol/code pairs, raw-only) hashes to None and stays on the
        legacy bare-fingerprint matcher tier, which is correct because its
        captured signals hash to None through the same code path.
        """
        from .event_parser import EventParser

        changed = False
        for device in self._data.values():
            for cmd in device.commands:
                if cmd.byte_hash is not None:
                    continue
                bh = EventParser.pronto_byte_hash(cmd.code)
                if bh is not None:
                    cmd.byte_hash = bh
                    changed = True
        return changed

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
        self._triggers[trigger.id] = trigger

    def update_trigger(self, trigger: IRTrigger) -> None:
        self._triggers[trigger.id] = trigger

    def remove_trigger(self, trigger_id: str) -> bool:
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False

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
