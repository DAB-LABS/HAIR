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
        self._idx_fp: dict[str, tuple[str, str]] = {}

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
        # fields, then build the known-command reverse index.
        changed = self._backfill_decoded_fields()
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
        """Rebuild the known-command reverse indexes from current devices."""
        from .event_parser import EventParser

        self._idx_decoded = {}
        self._idx_fp_bytehash = {}
        self._idx_fp = {}
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
                    self._idx_fp[fp] = ref

    def match_command(
        self,
        decoded_fingerprint: str | None,
        signal_fingerprint: str | None,
        byte_hash: str | None,
    ) -> tuple[str, str] | None:
        """Return the ``(device_id, command_id)`` a signal maps to, or None.

        Tiers, most precise first: decoded protocol identity, then the
        composite ``(S/L fingerprint, byte_hash)``, then the S/L
        fingerprint alone (so a pre-0.3.4 command with no ``byte_hash``
        still matches). The signal monitor uses this to suppress
        re-presses of already-assigned commands from the live feed.
        """
        if decoded_fingerprint and decoded_fingerprint in self._idx_decoded:
            return self._idx_decoded[decoded_fingerprint]
        if signal_fingerprint:
            ref = self._idx_fp_bytehash.get((signal_fingerprint, byte_hash))
            if ref is not None:
                return ref
            return self._idx_fp.get(signal_fingerprint)
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
        from .const import DECODED_FINGERPRINT_FORMAT
        from .ir_command import ProntoCommand
        from .protocol_decode import try_decode

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
                decoded = try_decode(raw)
                if decoded is None:
                    continue
                protocol, address, command = decoded
                cmd.decoded_protocol = protocol
                cmd.decoded_address = address
                cmd.decoded_command = command
                cmd.decoded_fingerprint = DECODED_FINGERPRINT_FORMAT.format(
                    protocol=protocol, address=address, command=command
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
        """Find a trigger by signal fingerprint."""
        for t in self._triggers.values():
            if t.signal_fingerprint == fingerprint:
                return t
        return None

    def get_triggers_for_signal(
        self, protocol: str | None, code: str | None, fingerprint: str
    ) -> list[IRTrigger]:
        """Find all enabled triggers matching a signal.

        Matches on protocol+code first (exact), falls back to fingerprint.
        """
        matches = []
        for t in self._triggers.values():
            if not t.enabled:
                continue
            if (
                t.protocol
                and t.code
                and protocol
                and code
                and t.protocol == protocol
                and t.code == code
            ) or t.signal_fingerprint == fingerprint:
                matches.append(t)
        return matches
