"""Device CRUD and entity lifecycle management."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ASSIGN_SERVICE_TIMEOUT_S,
    DEFAULT_CARRIER_FREQUENCY,
    DOMAIN,
    MAX_DITTO_COUNT,
    MAX_SEND_COUNT,
    SEND_REPEAT_GAP,
    CommandCategory,
    DeviceType,
)
from .entity_factory import EntityFactory
from .models import IRCommand, IRDevice
from .power_monitor import PowerMonitor
from .storage import HAIRStore
from .vocabulary import localized_auto_map

if TYPE_CHECKING:
    from .trigger_manager import TriggerManager
    from .wig_format import ClimateMatrix

_LOGGER = logging.getLogger(__name__)

# Maps a captured command name (lowercased) → a feature key on the entity.
# The key space is platform-specific; the entity reads
# ``entity_config.command_mapping[<feature key>]`` to find the command name.
# Temp N naming convention for AC target temperatures (v0.6.1, GH #45).
# Matches "Temp 24", "Temp: 24", "Temperature 24" (case-insensitive,
# 1-3 digits). The degree value is unit-agnostic; HA interprets it in
# the installation's unit system.
_TEMP_COMMAND_PATTERN = re.compile(
    r"temp(?:erature)?\s*:?\s*(\d{1,3})", re.IGNORECASE
)

AUTO_MAP_RULES: dict[str, str] = {
    "power": "power_toggle",
    "power on": "turn_on",
    "power off": "turn_off",
    "volume up": "volume_up",
    "volume down": "volume_down",
    "mute": "mute",
    "channel up": "channel_up",
    "channel down": "channel_down",
    "source/input": "select_source",
    "source": "select_source",
    "input": "select_source",
    "up": "navigate_up",
    "down": "navigate_down",
    "left": "navigate_left",
    "right": "navigate_right",
    "select/ok": "navigate_select",
    "back/return": "navigate_back",
    "mode: cool": "mode_cool",
    "mode: heat": "mode_heat",
    "mode: fan": "mode_fan_only",
    "mode: dry": "mode_dry",
    "mode: auto": "mode_auto",
    "fan: low": "fan_low",
    "fan: medium": "fan_medium",
    "fan: high": "fan_high",
    "fan: auto": "fan_auto",
    "speed up": "speed_up",
    "speed down": "speed_down",
    "speed 1": "speed_1",
    "speed 2": "speed_2",
    "speed 3": "speed_3",
    "speed 4": "speed_4",
    "speed 5": "speed_5",
    "speed 6": "speed_6",
    "speed 7": "speed_7",
    "speed 8": "speed_8",
    "speed 9": "speed_9",
    "speed 10": "speed_10",
    "oscillate": "oscillate",
    "swing toggle": "swing_toggle",
    "timer": "timer",
    # Light
    "on": "turn_on",
    "off": "turn_off",
    "brightness up": "brightness_up",
    "brightness down": "brightness_down",
    "color temp warmer": "color_temp_warmer",
    "color temp cooler": "color_temp_cooler",
    # Cover / screen
    "open": "open_cover",
    "close": "close_cover",
    # Media transport
    "guide": "guide",
    "menu": "menu",
    "play": "play",
    "pause": "pause",
    "rewind": "rewind",
    "fast forward": "fast_forward",
}


class DeviceManager:
    """Manage IR device lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HAIRStore,
        entity_factory: EntityFactory,
        config_entry_id: str,
        power_monitor: PowerMonitor | None = None,
    ) -> None:
        self._hass = hass
        self._store = store
        self._entity_factory = entity_factory
        self._config_entry_id = config_entry_id
        # Optional: absent in tests that don't exercise power monitoring.
        # Rebuilt/torn down alongside entities so a sensor picked, changed,
        # or cleared in the settings dialog takes effect without a reload.
        self._power_monitor = power_monitor
        # Parsed climate matrices by device id (Cold Cuts). Loaded from
        # hair/matrices/ on first ask, held for the install's lifetime:
        # matrix files only change through adopt/duplicate/delete, all
        # of which run through this manager, so the cache never goes
        # stale behind our back. Misses are NOT cached, so a file that
        # appears later (restored backup) is picked up on the next ask.
        self._matrix_cache: dict[str, ClimateMatrix] = {}

    async def async_create_device(self, device: IRDevice) -> IRDevice:
        """Create a new IR device, register in HA registry, create entities."""
        self._store.add_device(device)
        await self._store.async_save()
        self._register_ha_device(device)
        await self._entity_factory.async_create_entities(device)
        if self._power_monitor is not None:
            self._power_monitor.rebuild_device(device)
        return device

    async def async_update_device(self, device: IRDevice) -> IRDevice:
        self._store.update_device(device)
        # Signpost 4, Track 1. This is the single funnel every command
        # add, edit and delete persists through (see async_update_command
        # and the assign paths), so re-deriving pin maps here covers
        # every device-side content change with one hook instead of one
        # per call site. Only remotes actually pinned to this device are
        # touched, and it lands before the save so it costs no extra
        # write.
        from .pin_bindings import rederive_remotes_for_device

        rederive_remotes_for_device(self._store, device.id)
        await self._store.async_save()
        self._register_ha_device(device)
        await self._entity_factory.async_update_entities(device)
        if self._power_monitor is not None:
            self._power_monitor.rebuild_device(device)
        return device

    async def async_update_command(
        self,
        device_id: str,
        command_id: str,
        *,
        name: str | None = None,
        pronto: str | None = None,
        send_count: int | None = None,
        repeat_count: int | None = None,
        trigger_manager: TriggerManager | None = None,
    ) -> dict[str, Any]:
        """Edit a device command's name and/or Pronto in place.

        On a name change: guard against a duplicate name on the device,
        then cascade the action mappings (every ``command_mapping`` value
        equal to the old name moves to the new name) and report the count.
        On a Pronto change: re-evaluate the new code as a fresh capture
        (``code`` / ``raw_timings`` / ``byte_hash`` / ``decoded_*`` /
        ``frequency``) and rewire any bound trigger when the S/L
        fingerprint changes. Persists through :meth:`async_update_device`
        so the known-command reverse index rebuilds (a code edit changes
        its keys) and the entity ``update_device`` hooks fire.

        Returns ``{success, command, triggers, mappings_updated}`` on
        success, or ``{success: False, code, error}``.
        """
        from .ir_command import ProntoCommand
        from .pronto_validator import validate_pronto
        from .protocol_decode import try_decode_identity

        device = self._store.get_device(device_id)
        if device is None:
            return {"success": False, "code": "device_not_found",
                    "error": "Device not found"}
        command = device.get_command(command_id)
        if command is None:
            return {"success": False, "code": "command_not_found",
                    "error": "Command not found"}

        rewire: dict[str, list[str]] = {"rewired": [], "skipped": []}
        mappings_updated = 0

        # --- name change: collision guard + mapping cascade ---
        if name is not None:
            new_name = name.strip()
            if not new_name:
                return {"success": False, "code": "invalid_name",
                        "error": "Command name cannot be empty"}
            if new_name.casefold() != command.name.casefold():
                clash = device.get_command_by_name(new_name)
                if clash is not None and clash.id != command.id:
                    return {
                        "success": False, "code": "duplicate_name",
                        "error": "Another command on this device has that name",
                    }
                old_name = command.name
                command.name = new_name
                # Cascade every mapping whose value is the old command name.
                mapping = device.entity_config.command_mapping
                for key, val in mapping.items():
                    if val.casefold() == old_name.casefold():
                        mapping[key] = new_name
                        mappings_updated += 1
                # Climate presets: the star. A starred command's name IS
                # the preset name on the climate entity, so a rename has
                # to travel the same way the action mappings just did --
                # otherwise the star stays lit on a row whose preset
                # silently vanished from the more-info dialog.
                starred = device.entity_config.starred
                for index, entry in enumerate(starred):
                    if entry.casefold() == old_name.casefold():
                        starred[index] = new_name

        # --- pronto change: recompute identity + rewire triggers ---
        if pronto is not None:
            result = validate_pronto(pronto)
            if not result.valid:
                return {
                    "success": False, "code": "invalid_pronto",
                    "error": (result.errors[0] if result.errors
                              else "Invalid Pronto code"),
                }
            new_code = result.normalized
            from .identity import canonical_fingerprint as _canon_fp

            old_fp = _canon_fp(
                command.protocol, command.code, command.raw_timings
            )
            # Captured BEFORE the mutations below: a sub-threshold edit
            # (Sony code A to code B) changes only the byte_hash -- and
            # rewire needs the old byte-level AND decoded values to repoint
            # precisely (v0.5.8 unified identity).
            old_byte_hash = command.byte_hash
            old_decoded_fingerprint = command.decoded_fingerprint
            # Canonical (wire) identity for the edited code; the stored
            # code text stays as the user typed it (identity.py).
            from .identity import canonical_byte_hash, canonical_fingerprint

            new_fp = canonical_fingerprint("PRONTO", new_code, [])
            new_byte_hash = canonical_byte_hash(new_code)
            try:
                raw = ProntoCommand(new_code).get_raw_timings()
            except Exception:  # bad code falls back to no decoded timings
                raw = None
            identity = try_decode_identity(raw)
            decoded_protocol = identity.protocol if identity else None
            decoded_address = identity.address if identity else None
            decoded_command = identity.command if identity else None
            decoded_fingerprint = identity.fingerprint if identity else None
            command.protocol = "PRONTO"
            command.code = new_code
            command.raw_timings = list(raw) if raw else None
            command.byte_hash = new_byte_hash
            command.frequency = (
                round(result.frequency_khz * 1000)
                if result.frequency_khz
                else DEFAULT_CARRIER_FREQUENCY
            )
            command.decoded_protocol = decoded_protocol
            command.decoded_address = decoded_address
            command.decoded_command = decoded_command
            command.decoded_fingerprint = decoded_fingerprint
            command.decoded_extras = (
                dict(identity.extras) if identity and identity.extras else None
            )
            # Rewire on ANY identity component changing (v0.5.8): a
            # sub-threshold edit shifts only the byte_hash, never the S/L
            # fingerprint, and would otherwise orphan a scoped trigger.
            if (
                trigger_manager is not None
                and new_fp
                and (
                    new_fp != old_fp
                    or new_byte_hash != old_byte_hash
                    or decoded_fingerprint != old_decoded_fingerprint
                )
            ):
                rewire = await trigger_manager.rewire(
                    old_fp, new_fp, "PRONTO", new_code,
                    old_byte_hash=old_byte_hash,
                    new_byte_hash=new_byte_hash,
                    old_decoded_fingerprint=old_decoded_fingerprint,
                    new_decoded_fingerprint=decoded_fingerprint,
                )

        # --- whole-frame send count ---
        if send_count is not None:
            command.send_count = max(1, min(int(send_count), MAX_SEND_COUNT))

        # --- NEC ditto count ---
        if repeat_count is not None:
            command.repeat_count = max(0, min(int(repeat_count), MAX_DITTO_COUNT))

        await self.async_update_device(device)
        return {
            "success": True,
            "command": command.to_dict(),
            "triggers": rewire,
            "mappings_updated": mappings_updated,
        }

    async def async_reorder_devices(self, ordered_ids: list[str]) -> None:
        """Reorder the device list and persist. Raises ValueError on a
        stale/mismatched id list (see ``HAIRStore.reorder_devices``)."""
        self._store.reorder_devices(ordered_ids)
        await self._store.async_save()

    async def async_remove_device(self, device_id: str) -> bool:
        device = self._store.get_device(device_id)
        if device is None:
            return False
        await self._entity_factory.async_remove_entities(device_id)

        registry = dr.async_get(self._hass)
        ha_device = registry.async_get_device(
            identifiers={(DOMAIN, device.id)}
        )
        if ha_device is not None:
            registry.async_remove_device(ha_device.id)

        self._store.remove_device(device_id)
        # Both halves of the delete commit together: the store's single
        # save below covers the device removal and the unpin.
        self._unpin_deleted_device(device_id)
        await self._store.async_save()
        if self._power_monitor is not None:
            self._power_monitor.remove_device(device_id)
        self._forget_matrix_caches(device_id)

        # Matrix file cleanup (Cold Cuts): best-effort, AFTER the store
        # commit -- a full disk or bad permission must never resurrect
        # a device the user already deleted, and an orphaned matrix
        # file is inert (nothing reads it without the device id).
        self._matrix_cache.pop(device_id, None)
        if device.climate_matrix:
            try:
                from .matrix_store import delete_matrix

                await self._hass.async_add_executor_job(
                    delete_matrix, self._hass.config.config_dir, device_id
                )
            except Exception:
                _LOGGER.warning(
                    "Could not delete matrix file for device %s",
                    device_id, exc_info=True,
                )
        return True

    def _unpin_deleted_device(self, device_id: str) -> int:
        """Strip a deleted device's id out of every Remote that pinned it.

        The mirror of the starred prune a command delete already does.
        A pin that outlives its device is not inert: ``pin_bindings``
        skips an id it cannot resolve, so the remote drives nothing,
        while every surface that reads "pinned" off a non-empty
        ``pinned_device_ids`` (the Devices card, the settings dialog,
        the Mirror's "Pinned to") keeps saying it is pinned. A remote
        whose only pin was the deleted device is then pinned to nothing
        and says otherwise.

        Bindings are cleaned in the same pass, including a key with no
        matching pin, so the derived map can never outlive the pin that
        justified it. Returns how many remotes were touched.
        """
        touched = 0
        for remote in self._store.get_all_trigger_remotes():
            if (
                device_id not in remote.pinned_device_ids
                and device_id not in remote.bindings
            ):
                continue
            remote.pinned_device_ids = [
                d for d in remote.pinned_device_ids if d != device_id
            ]
            remote.bindings.pop(device_id, None)
            remote.updated_at = datetime.now(UTC).isoformat()
            self._store.update_trigger_remote(remote)
            touched += 1
            _LOGGER.info(
                "Unpinned Remote '%s' from deleted Device %s",
                remote.name, device_id,
            )
        return touched

    def _forget_matrix_caches(self, device_id: str) -> None:
        """Drop the matrix listener's per-device state for a gone device.

        A pinned matrix Device is indexed through the LISTENER's cache,
        not this manager's, because ``_cell_by_identity`` asks its
        lattice "which of your cells is this frame?" (Track 4). Deleting
        the device left that index, its parsed matrix and its
        already-reported unmapped pairings in memory for the rest of the
        run. Inert once the pins above are gone, and still worth not
        holding. Best effort: hygiene must never fail a delete the store
        has already committed.
        """
        data = self._hass.data.get(DOMAIN, {}).get(self._config_entry_id)
        listener = data.get("matrix_listener") if data else None
        if listener is None:
            return
        try:
            listener.forget_matrix(device_id)
        except Exception:
            _LOGGER.debug(
                "Could not drop the matrix listener's caches for device %s",
                device_id, exc_info=True,
            )

    async def async_get_matrix(self, device_id: str) -> ClimateMatrix | None:
        """The device's climate matrix, cache-first (Cold Cuts).

        The climate entity calls this from ``async_added_to_hass`` and
        again on updates until a matrix lands; file I/O runs on the
        executor. None = no file or an unreadable one (matrix_store
        logs the reason), and the entity refuses sends rather than
        guessing.
        """
        cached = self._matrix_cache.get(device_id)
        if cached is not None:
            return cached
        from .matrix_store import load_matrix

        matrix = await self._hass.async_add_executor_job(
            load_matrix, self._hass.config.config_dir, device_id
        )
        if matrix is not None:
            self._matrix_cache[device_id] = matrix
        return matrix

    async def async_add_command(
        self, device_id: str, command: IRCommand
    ) -> IRCommand:
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        device.add_command(command)
        self._auto_map_command(device, command)
        self._store.update_device(device)
        await self._store.async_save()
        await self._entity_factory.async_update_entities(device)
        return command

    async def async_apply_auto_map(
        self, device_id: str, command_id: str
    ) -> IRDevice | None:
        """Apply the action auto-map to an already-stored command and refresh.

        The assign path (``signal_monitor.assign_*``) creates the command via
        the model's ``add_command``, which -- unlike the learn path's
        ``async_add_command`` -- does not run ``_auto_map_command``. Call this
        after an assign so a command whose name matches a standard action
        (Power, Fan: Auto, Mode: Cool, ...) gets mapped, the AC fan/hvac modes
        get registered, and the entities refresh to expose them. A no-op for a
        custom name with no standard action. Returns the updated device.
        """
        device = self._store.get_device(device_id)
        if device is None:
            return None
        command = device.get_command(command_id)
        if command is None:
            return device
        self._auto_map_command(device, command)
        return await self.async_update_device(device)

    async def async_remove_command(
        self, device_id: str, command_id: str
    ) -> bool:
        device = self._store.get_device(device_id)
        if device is None:
            return False

        command = device.get_command(command_id)
        removed = device.remove_command(command_id)
        if not removed:
            return False

        if command is not None:
            self._unmap_command(device, command)

        self._store.update_device(device)
        await self._store.async_save()
        await self._entity_factory.async_update_entities(device)
        return True

    async def async_replace_command(
        self,
        device_id: str,
        command_id: str,
        new_command: IRCommand,
    ) -> bool:
        device = self._store.get_device(device_id)
        if device is None:
            return False
        if not device.replace_command(command_id, new_command):
            return False
        self._auto_map_command(device, new_command)
        self._store.update_device(device)
        await self._store.async_save()
        await self._entity_factory.async_update_entities(device)
        return True

    def _signal_monitor(self) -> Any | None:
        """Resolve the SignalMonitor for Mirror send auditing (v0.6.6).

        Looked up lazily through hass.data to avoid a construction-order
        dependency; None (and silently no audit) when unavailable, e.g.
        in tests that build a bare DeviceManager.
        """
        domain_data = self._hass.data.get(DOMAIN)
        if not isinstance(domain_data, dict):
            return None
        entry = domain_data.get(self._config_entry_id)
        if not isinstance(entry, dict):
            return None
        return entry.get("signal_monitor")

    # --- The cell porthole (v0.9.5) --------------------------------
    #
    # A matrix device grows coordinate-named command rows for the cells
    # the comb doubted. Those rows are VIEWS of lattice cells, so an
    # edit or a delete through one has to reach the matrix store rather
    # than the command record -- otherwise the row and the lattice drift
    # apart and the climate entity keeps transmitting the code the
    # person just replaced.
    #
    # Both writers go through here so the cache invalidation cannot be
    # forgotten at a call site: async_get_matrix caches, and a stale
    # cache is exactly the bug that looks fixed on the bench and comes
    # back at the next restart.

    async def async_write_matrix(
        self, device_id: str, matrix: ClimateMatrix
    ) -> None:
        """Persist a device's lattice and refresh what everything reads."""
        from .matrix_store import write_matrix

        await self._hass.async_add_executor_job(
            write_matrix, self._hass.config.config_dir, device_id, matrix
        )
        self._matrix_cache[device_id] = matrix

    @staticmethod
    def _cell_matches(cell: Any, coords: dict[str, Any]) -> bool:
        """Does this cell sit at those coordinates?

        Compared field by field rather than by cell_key, because a key
        is a formatted string and a temperature that round-tripped
        through JSON as 23 rather than 23.0 would stop matching its own
        row. The numeric compare does not care.
        """
        if cell.mode != coords.get("mode"):
            return False
        if (cell.fan or None) != (coords.get("fan") or None):
            return False
        if (cell.swing or None) != (coords.get("swing") or None):
            return False
        a, b = cell.temp, coords.get("temp")
        if a is None or b is None:
            return a is None and b is None
        return abs(float(a) - float(b)) < 1e-6

    async def async_replace_cell(
        self, device_id: str, coords: dict[str, Any], pronto: str
    ) -> bool:
        """Write new bytes into one lattice cell. False if it is gone."""
        matrix = await self.async_get_matrix(device_id)
        if matrix is None:
            return False
        for cell in matrix.cells:
            if self._cell_matches(cell, coords):
                cell.pronto = pronto
                await self.async_write_matrix(device_id, matrix)
                return True
        return False

    async def async_delete_cell(
        self, device_id: str, coords: dict[str, Any]
    ) -> bool:
        """Remove one cell from the lattice. False if it is already gone.

        Sparse lattices are legal, so this leaves a working matrix: the
        climate entity simply stops offering that state.
        """
        matrix = await self.async_get_matrix(device_id)
        if matrix is None:
            return False
        keep = [c for c in matrix.cells if not self._cell_matches(c, coords)]
        if len(keep) == len(matrix.cells):
            return False
        matrix.cells = keep
        await self.async_write_matrix(device_id, matrix)
        return True

    @staticmethod
    def _sent_for_command(device: IRDevice, command: IRCommand, origin: str):
        """Describe a stored-command send structurally (0.10.1 item 7).

        Coordinates come off the command record, never off its name: a
        STATE row's name is display grammar that converts units live and
        froze at mint time, so reading state back out of it would be a
        guess dressed as a fact.
        """
        from .send_signal import DeviceSent

        state = command.sent_state or {}
        power = state.get("power")
        cell = None if power else (dict(state) or None)
        starred = command.name.casefold() in {
            name.casefold() for name in device.entity_config.starred
        }
        return DeviceSent(
            device_id=device.id,
            command_id=command.id,
            command_name=command.name,
            matrix_cell=cell,
            power=power,
            starred=starred,
            origin=origin,
        )

    async def async_test_send(
        self,
        device_id: str,
        pronto: str,
        *,
        send_count: int = 1,
        label: str = "Test",
    ) -> set[str]:
        """Transmit candidate bytes once, saving nothing.

        The fix flow has to let somebody point a candidate at the real
        unit BEFORE it is written anywhere -- that press is the whole
        gate on the write. So this takes raw Pronto rather than a stored
        command id, and there is deliberately no path from here to the
        store: it rides the same all-emitters resilience machinery every
        other send uses (``_async_broadcast``) and then forgets.

        Raw ALWAYS, never the canonical re-encode. A candidate is being
        judged on what it will actually transmit once written, and
        re-encoding it from a decoded identity would test bytes the
        device is not about to store.
        """
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        if not device.emitter_entity_ids:
            raise RuntimeError(f"Device {device_id} has no emitters configured")

        from .ir_command import build_command

        ir_cmd = build_command(protocol="PRONTO", code=pronto)
        return await self._async_broadcast(
            device, ir_cmd, label, send_count=max(1, min(int(send_count), 10)),
        )

    async def async_send_command(
        self,
        device_id: str,
        command_id: str,
        heard_future: Any | None = None,
        pinned: bool = False,
        origin: str | None = None,
    ) -> None:
        """Send a stored IR command via all configured emitters (broadcast).

        Uses ``homeassistant.components.infrared.async_send_command``
        (HA 2026.4+) which accepts an ``infrared_protocols.Command``
        instance wrapping the raw timings or Pronto hex.

        The command is sent to every emitter in the device's
        ``emitter_entity_ids`` list for maximum coverage.
        """
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        command = device.get_command(command_id)
        if command is None:
            raise KeyError(f"Unknown command {command_id} on device {device_id}")

        if not device.emitter_entity_ids:
            raise RuntimeError(f"Device {device_id} has no emitters configured")

        from .ir_command import build_command, build_decoded_command

        # Prefer canonical encode-from-decoded when the command carries a
        # decoded protocol identity and the user has not pinned it to the
        # captured timings. This transmits clean library-encoded timings
        # rather than replaying captured (receiver-distorted) ones, which
        # fixes replay failures against non-TSOP destinations (GH #14).
        # Falls back to Pronto/raw replay when undecodable, opted out, or
        # the library is unavailable.
        ir_cmd = None
        if command.decoded_fingerprint and not command.tx_force_raw:
            ir_cmd = build_decoded_command(
                command.decoded_protocol,
                command.decoded_address,
                command.decoded_command,
                repeat_count=command.repeat_count or 0,
                decoded_extras=command.decoded_extras,
            )
        decoded_tx = ir_cmd is not None
        if ir_cmd is None:
            ir_cmd = build_command(
                protocol=command.protocol,
                code=command.code,
                raw_timings=command.raw_timings,
                frequency=command.frequency or 38000,
                repeat_count=command.repeat_count or 0,
            )

        from .send_signal import ORIGIN_MANAGER

        # Broadcast through the shared emitter path; raises when every
        # emitter fails, so the code below only runs on a landed send.
        await self._async_broadcast(
            device,
            ir_cmd,
            command.name,
            send_count=max(1, command.send_count or 1),
            decoded_fingerprint=(
                command.decoded_fingerprint
                if not command.tx_force_raw else None
            ),
            heard_future=heard_future,
            pinned=pinned,
            sent=self._sent_for_command(
                device, command, origin or ORIGIN_MANAGER
            ),
        )

        # Per-press protocol state (v0.6.0 toggles, v0.7.1 counters):
        # one send-command call is one logical press, so advance once
        # when AT LEAST ONE send landed (GH #65: "loop finished without
        # raising" desynced state when a late emitter failed after the
        # device already got the frame from an earlier one) --
        # send_count > 1 deliberately re-sends the same state. The
        # decoded fingerprint excludes both fields, so the reverse
        # index is unaffected and a bare save is safe.
        # - RC-5-family toggle: flips 0/1 per press.
        # - Dyson rolling counter: increments mod 4 per press. The fan
        #   rejects a frame reusing its last-seen counter (GH #33), so
        #   advancing AFTER each send guarantees consecutive HAIR
        #   presses always differ.
        if decoded_tx and command.decoded_extras:
            advanced = False
            if "toggle" in command.decoded_extras:
                command.decoded_extras["toggle"] = (
                    int(command.decoded_extras["toggle"]) ^ 1
                )
                advanced = True
            if "counter" in command.decoded_extras:
                command.decoded_extras["counter"] = (
                    int(command.decoded_extras["counter"]) + 1
                ) & 0x3
                advanced = True
            if advanced:
                self._store.update_device(device)
                await self._store.async_save()

    async def _async_broadcast(
        self,
        device: IRDevice,
        ir_cmd: Any,
        send_name: str,
        *,
        send_count: int = 1,
        decoded_fingerprint: str | None = None,
        heard_future: Any | None = None,
        pinned: bool = False,
        sent: Any | None = None,
    ) -> set[str]:
        """The shared all-emitters transmit path (GH #65 semantics).

        Extracted from ``async_send_command`` for Cold Cuts so matrix
        cell sends ride the EXACT same resilience machinery instead of
        a third path: pre-skip known-down emitters, per-emitter guard
        with the assign timeout, a failing emitter dropped from later
        frames, Mirror audit armed BEFORE transmitting, degrade
        notifications raised and self-dismissed identically. Succeeds
        (returns the landed set) when at least one (emitter, frame)
        landed; raises RuntimeError with the honest "all unavailable"
        message otherwise. ``send_name`` is the command-name channel
        for the Mirror label and the log lines ("<device> / <name>").

        ``sent`` (0.10.1 item 7) is what to tell the entities about this
        send. Dispatched only once at least one emitter has ACCEPTED it:
        a send that failed everywhere changed nothing on the unit, so
        moving the climate card for it would be a lie. None means say
        nothing, which is what a fitting send and every caller that does
        not care pass.
        """
        # Lazy import: infrared component only available at runtime on
        # HA 2026.4+.
        from homeassistant.components.infrared import (
            async_send_command as ir_send,
        )

        from .tx_gate import gated_send

        # Emitter resilience (GH #65, rvgfox): multi-emitter is the
        # redundancy feature, so one napping blaster must never block
        # the others or paint a red toast on a command that actually
        # fired. Pre-skip emitters HA already knows are down; the
        # per-send guard below is the real backstop, because a wifi
        # proxy can fail at SEND time while its state still reads fine
        # (the Athom in the report did exactly that).
        skipped: dict[str, str] = {}
        attempt_ids: list[str] = []
        for emitter_id in device.emitter_entity_ids:
            state = self._hass.states.get(emitter_id)
            # "unavailable" is down. "unknown" is merely NEVER USED: an
            # infrared emitter's state is the timestamp of its last
            # send, None until the first one -- so skipping "unknown"
            # made a fresh install unable to send its first command
            # ever (GH #83, Lilian877 + Warpshock: every emitter
            # pre-skipped, "All emitters unavailable" on a clean
            # setup). The per-send guard below catches an emitter that
            # is actually dead but not yet marked, exactly as the
            # comment above has always said.
            if state is not None and state.state == "unavailable":
                skipped[emitter_id] = state.state
                continue
            attempt_ids.append(emitter_id)
        if not attempt_ids:
            self._notify_emitter_degraded(device, skipped)
            raise RuntimeError(
                f"All emitters for {device.name} are unavailable"
            )

        # The Mirror (v0.6.6): audit this send and arm echo attribution
        # BEFORE transmitting, so every emitter's state beacon reads as
        # HAIR's own and the loopback captures enrich the Mirror row
        # instead of entering the Sniffer. Attempted emitters only, so
        # the row's "via" names the blasters that actually keyed up.
        monitor = self._signal_monitor()
        if monitor is not None:
            monitor.record_send(
                ir_cmd,
                # Provenance for the Mirror's chip (signpost 4, Track
                # 4). A pinned retransmit is a HAIR device send in
                # every mechanical sense, so it takes the same path,
                # but a user reading the Mirror needs to tell "the
                # handset drove this" from "I pressed the button in
                # the panel". The prefix is the channel; ir-mirror.ts
                # reads it the same way it already reads the test and
                # fitting prefixes.
                (
                    f"Pinned send: {device.name} / {send_name}"
                    if pinned
                    else f"{device.name} / {send_name}"
                ),
                attempt_ids,
                decoded_fingerprint=decoded_fingerprint,
                # Passed explicitly: send_count is this method's loop
                # bound below and is never written onto ir_cmd, so the
                # Mirror cannot read it back off the Command.
                send_count=send_count,
                # The caller's echo hook, when it wants one. The TEST
                # button's SENT . HEARD reading comes from here: the
                # Mirror already attributes this send's own loopback,
                # so reporting whether it came back costs one future
                # rather than a second capture path.
                heard_future=heard_future,
            )

        # Whole-frame repetition: transmit the built Command send_count times
        # to every emitter, with a short pause between frames so the receiver
        # registers them as distinct presses. send_count defaults to 1.
        # Sends route through the transmit gate, which staggers emitter
        # CHANGES so a multi-emitter broadcast doesn't superimpose in the
        # air at a receiver that hears both blasters (see tx_gate).
        # Per-emitter guard (GH #65): a failing emitter is recorded and
        # dropped from later frames (no point stacking timeouts on a
        # dead unit); the command succeeds when at least one (emitter,
        # frame) landed.
        landed: set[str] = set()
        # GH #98: the wire copy ends on a bounded trailing space
        # (RM4 Pro firmware garbles mark-terminated streams; the
        # 16-bit Zigbee formats bound its size). Transmit-only --
        # ir_cmd's own array stays identity-stable.
        from .ir_command import TerminatedCommand

        ir_cmd = TerminatedCommand(ir_cmd)
        failures: dict[str, str] = {}
        for i in range(send_count):
            if i:
                await asyncio.sleep(SEND_REPEAT_GAP)
            for emitter_id in attempt_ids:
                if emitter_id in failures:
                    continue
                try:
                    await asyncio.wait_for(
                        gated_send(
                            self._hass, emitter_id, ir_cmd, ir_send
                        ),
                        timeout=ASSIGN_SERVICE_TIMEOUT_S,
                    )
                    landed.add(emitter_id)
                except TimeoutError:
                    failures[emitter_id] = "timed out"
                except Exception as err:
                    failures[emitter_id] = str(err) or type(err).__name__

        if not landed:
            # Every attempt failed: honest message, not the raw driver
            # string (details go to the log).
            _LOGGER.warning(
                "Send %s / %s: every emitter failed: %s",
                device.name, send_name,
                {**skipped, **failures},
            )
            self._notify_emitter_degraded(
                device, {**skipped, **failures}
            )
            raise RuntimeError(
                f"All emitters for {device.name} are unavailable"
            )
        if failures or skipped:
            # Partial success is SILENT success (invisible resilience
            # is the point of redundancy); the log keeps the receipt,
            # and the persistent notification below is the one visible
            # trace (GH #65 bench, queued 2026-07-27: "the user should
            # know one of their transmitters is out").
            _LOGGER.warning(
                "Send %s / %s went out via %s; skipped/failed: %s",
                device.name, send_name, sorted(landed),
                {**skipped, **failures},
            )
            self._notify_emitter_degraded(
                device, {**skipped, **failures}
            )
        # Self-healing: an emitter that answered clears its own
        # notification, so a Broadlink coming back from a power blip
        # tidies up without the user hunting for a dismiss button.
        for emitter_id in landed:
            self._dismiss_emitter_notification(emitter_id)
        # THE CARD FOLLOWS WHAT HAIR SENDS (0.10.1 item 7, GH #105).
        # Here and only here: every device send passes through this
        # method, and by this line at least one emitter has accepted it.
        if sent is not None:
            from .send_signal import SIGNAL_DEVICE_SENT

            async_dispatcher_send(self._hass, SIGNAL_DEVICE_SENT, sent)
        return landed

    async def async_send_matrix_cell(
        self,
        device_id: str,
        cell_name: str,
        pronto: str,
        send_count: int = 1,
        heard_future: Any | None = None,
        pinned: bool = False,
        cell: dict[str, Any] | None = None,
        power: str | None = None,
        origin: str | None = None,
    ) -> None:
        """Send one climate matrix cell's raw Pronto (Cold Cuts).

        Rides ``_async_broadcast`` so a matrix send behaves EXACTLY
        like a stored-command send: same pre-skip, same per-emitter
        guard and timeout, same "all unavailable" contract, same
        degrade notifications, and the Mirror row labeled with the
        cell key ("Bedroom AC / cool/auto/23"). Deliberately raw
        Pronto replay with no decoded re-encode attempt: AC frames are
        long state blobs the decoders do not cover, and the matrix
        file's code IS the ground truth (census finding).

        ``heard_future`` (Second Fitting v3 punch list item 14): the
        same echo hook ``async_send_command`` has always accepted.
        Before this it was silently dropped here, so a matrix TEST
        could only ever report SENT -- the Mirror's echo matching is
        content-based (decoded fingerprint / signal fingerprint), not
        a command-table lookup, so it already recognized a cell's own
        echo; the wire to report that back just never existed.

        ``cell`` and ``power`` (0.10.1 item 7) are the COORDINATES of
        what is going out, so the climate card can follow it. Every
        caller already holds them: the STATE MATRIX card resolved them,
        the pinned retransmit heard them, the entity's own setters
        chose them. They travel structurally rather than being parsed
        back out of ``cell_name``, which is display grammar that
        converts units live. Omitting both means a send with no state
        meaning, which moves nothing.
        """
        device = self._store.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device {device_id}")
        if not device.emitter_entity_ids:
            raise RuntimeError(f"Device {device_id} has no emitters configured")

        from .ir_command import build_command
        from .send_signal import ORIGIN_MANAGER, DeviceSent

        ir_cmd = build_command(protocol="PRONTO", code=pronto)
        await self._async_broadcast(
            device, ir_cmd, cell_name,
            send_count=max(1, send_count or 1),
            heard_future=heard_future,
            # Signpost 4, Track 4: a heard state driving a pinned
            # matrix Device rides here, and the Mirror row has to read
            # "Pinned send" like any other retransmit.
            pinned=pinned,
            sent=DeviceSent(
                device_id=device.id,
                command_name=cell_name,
                matrix_cell=dict(cell) if cell else None,
                power=power,
                origin=origin or ORIGIN_MANAGER,
            ),
        )

    # --- Saved STATE rows learn their coordinates (0.10.1 item 7) ------
    #
    # A STATE row minted before item 7 carries only its cell's BYTES, so
    # sending one told the climate card nothing and a preset (which IS a
    # starred STATE row) could not move the dial. The repair is to match
    # each row's Pronto back against the device's CURRENT lattice: the
    # file is the only thing entitled to say what a state is, and
    # matching against today's file means a re-fit can never leave a row
    # claiming a state the device no longer has.
    #
    # Runs here rather than in storage.async_load because the lattice
    # lives in its own file behind this manager's cache, which does not
    # exist yet when the store loads. A row that matches nothing stays
    # unstamped and simply does not move the card.

    @staticmethod
    def _pronto_key(pronto: str | None) -> str | None:
        """Compare Pronto by content, not by whitespace and case.

        A STATE row stores the FILE's text (``wig_signal_identity``
        returns it verbatim), so exact equality is the common case; this
        only keeps a hand-edited file's spacing from costing a match.
        """
        if not pronto:
            return None
        return " ".join(pronto.split()).upper()

    async def async_backfill_sent_states(self) -> int:
        """Stamp saved STATE rows with the cell they transmit.

        Returns how many rows were stamped, for the setup log and the
        tests. Folds every device's changes into one save.
        """
        from .const import CommandSource

        total = 0
        changed = False
        for device in self._store.get_all_devices():
            if not device.climate_matrix:
                continue
            pending = [
                command
                for command in device.commands
                if command.source == CommandSource.MATRIX
                and command.sent_state is None
                and command.matrix_cell is None
            ]
            if not pending:
                continue
            matrix = await self.async_get_matrix(device.id)
            if matrix is None:
                continue
            lattice: dict[str, dict[str, Any]] = {}
            for cell in matrix.cells:
                key = self._pronto_key(cell.pronto)
                if key is not None:
                    lattice[key] = {
                        "mode": cell.mode, "fan": cell.fan,
                        "swing": cell.swing, "temp": cell.temp,
                    }
            # Power codes last: a lattice that spells a cell with the
            # same bytes as its own off code is malformed, and reading
            # such a row as power is the safer of the two answers.
            for kind, pronto in (("off", matrix.off), ("on", matrix.on)):
                key = self._pronto_key(pronto)
                if key is not None:
                    lattice[key] = {"power": kind}
            stamped = 0
            for command in pending:
                state = lattice.get(self._pronto_key(command.code))
                if state is not None:
                    command.sent_state = dict(state)
                    stamped += 1
            if stamped:
                total += stamped
                changed = True
                self._store.update_device(device)
            _LOGGER.info(
                "Stamped %d of %d saved STATE rows with their cell on '%s'",
                stamped, len(pending), device.name,
            )
        if changed:
            await self._store.async_save()
        return total

    # --- Emitter-degrade notifications (GH #65 rider, v0.8.1) ---
    #
    # The resilience fix made partial failure a silent success, which is
    # right for the send but wrong for the human: a dead blaster should
    # not stay invisible until the day its twin dies too. One persistent
    # notification per unresponsive emitter (stable id, so repeats
    # replace instead of stack), self-dismissed the next time that
    # emitter answers. Notifications must never break a send, so every
    # path here swallows its own errors.

    @staticmethod
    def _emitter_notification_id(emitter_id: str) -> str:
        return f"hair_emitter_down_{emitter_id}"

    def _notify_emitter_degraded(
        self, device: IRDevice, problems: dict[str, str]
    ) -> None:
        try:
            from homeassistant.components import persistent_notification

            for emitter_id, reason in problems.items():
                state = self._hass.states.get(emitter_id)
                attrs = getattr(state, "attributes", None) or {}
                name = attrs.get("friendly_name") or emitter_id
                persistent_notification.async_create(
                    self._hass,
                    (
                        f"{name} did not answer while sending to "
                        f"{device.name} ({reason}). Check its power and "
                        "network. This notice clears itself the next "
                        "time the emitter answers."
                    ),
                    title="HAIR: IR emitter not responding",
                    notification_id=self._emitter_notification_id(
                        emitter_id
                    ),
                )
        except Exception:  # pragma: no cover - never break a send
            _LOGGER.debug(
                "Could not raise emitter-degrade notification",
                exc_info=True,
            )

    def _dismiss_emitter_notification(self, emitter_id: str) -> None:
        try:
            from homeassistant.components import persistent_notification

            persistent_notification.async_dismiss(
                self._hass, self._emitter_notification_id(emitter_id)
            )
        except Exception:  # pragma: no cover - never break a send
            pass

    async def async_set_command_tx_force_raw(
        self, device_id: str, command_id: str, tx_force_raw: bool
    ) -> bool:
        """Toggle a command's ``tx_force_raw`` flag and persist.

        When True, transmit replays the captured Pronto/raw timings instead
        of re-encoding from the decoded value -- the per-command escape
        hatch for the rare destination that wants the captured timings.
        """
        device = self._store.get_device(device_id)
        if device is None:
            return False
        command = device.get_command(command_id)
        if command is None:
            return False
        command.tx_force_raw = tx_force_raw
        self._store.update_device(device)
        await self._store.async_save()
        return True

    async def async_set_starred(
        self, device_id: str, command_name: str, starred: bool
    ) -> list[str] | None:
        """Star or unstar a command, and persist.

        A starred command becomes a Home Assistant preset on the
        device's climate entity, named exactly what the command is
        named (climate-presets-star.md). One gesture, no dialog: this
        is the whole write path behind the star glyph on the command
        row.

        Idempotent in both directions -- starring an already-starred
        command, or unstarring one that was never starred, changes
        nothing and writes nothing. Returns the resulting list of
        starred names, or None when the device or the command does not
        exist.

        Persists through :meth:`async_update_device` rather than a bare
        save so the entity ``update_device`` hooks fire and the climate
        entity re-reads its presets; a bare save would leave the
        more-info dialog showing the previous set until a restart.
        """
        device = self._store.get_device(device_id)
        if device is None:
            return None
        command = device.get_command_by_name(command_name)
        if command is None:
            return None

        current = list(device.entity_config.starred)
        target = command.name.casefold()
        present = any(name.casefold() == target for name in current)
        if starred == present:
            # Already in the asked-for state: no write, no entity
            # refresh, and no reshuffle of the click order.
            return current
        if starred:
            # Store the command's own name, not the caller's spelling,
            # so the preset reads exactly as the row does.
            updated = [*current, command.name]
        else:
            updated = [
                name for name in current if name.casefold() != target
            ]

        device.entity_config.starred = updated
        await self.async_update_device(device)
        return list(device.entity_config.starred)

    def _register_ha_device(self, device: IRDevice) -> None:
        registry = dr.async_get(self._hass)
        registry.async_get_or_create(
            config_entry_id=self._config_entry_id,
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer=device.manufacturer or "HAIR",
            model=device.model or _human_device_type(device.device_type),
        )

    def _auto_map_command(self, device: IRDevice, command: IRCommand) -> None:
        feature = AUTO_MAP_RULES.get(command.name.casefold())
        if feature is None:
            # Localized template names (v0.6.8 "French Braid"): accepting
            # a localized template stores the localized string as the
            # command name, so the English rules above miss it. The
            # synonyms table recognizes the same vocabulary across every
            # shipped locale at once (see vocabulary.py).
            feature = localized_auto_map(AUTO_MAP_RULES).get(
                command.name.casefold()
            )
        if feature is None:
            # Pattern rule (v0.6.1, GH #45): "Temp 24" / "Temp: 24" /
            # "Temperature 24" on an AC device maps to the temp_24
            # feature the climate entity already dispatches to, and
            # registers 24 as a temperature preset so the thermostat
            # card gains the step. Unit-agnostic: presets are plain
            # integers interpreted in the installation's unit system,
            # so 16..30 behaves as Celsius on a metric install.
            if device.device_type == DeviceType.AC:
                match = _TEMP_COMMAND_PATTERN.fullmatch(command.name.strip())
                if match is not None:
                    degrees = int(match.group(1))
                    device.entity_config.command_mapping[
                        f"temp_{degrees}"
                    ] = command.name
                    presets = list(
                        device.entity_config.temperature_presets or []
                    )
                    if degrees not in presets:
                        presets.append(degrees)
                        device.entity_config.temperature_presets = sorted(
                            presets
                        )
            return
        device.entity_config.command_mapping[feature] = command.name

        # Track surfaced HVAC and fan modes for the climate entity so the
        # supported_features dynamic computation has something to read.
        if device.device_type == DeviceType.AC:
            if feature.startswith("mode_"):
                modes = list(device.entity_config.hvac_modes or [])
                mode_token = feature.removeprefix("mode_")
                hvac_token = {
                    "cool": "cool",
                    "heat": "heat",
                    "fan_only": "fan_only",
                    "dry": "dry",
                    "auto": "auto",
                }.get(mode_token)
                if hvac_token and hvac_token not in modes:
                    modes.append(hvac_token)
                    device.entity_config.hvac_modes = modes
            elif feature.startswith("fan_"):
                modes = list(device.entity_config.fan_modes or [])
                token = feature.removeprefix("fan_")
                if token not in modes:
                    modes.append(token)
                    device.entity_config.fan_modes = modes

    def _unmap_command(self, device: IRDevice, command: IRCommand) -> None:
        # Climate presets: the star. Deleting a starred command has to
        # drop the star too, the same way it drops the action mapping
        # below -- a preset naming a command that no longer exists
        # would advertise a mode the entity could never send.
        device.entity_config.starred = [
            name
            for name in device.entity_config.starred
            if name.casefold() != command.name.casefold()
        ]
        mapping = device.entity_config.command_mapping
        for key, value in list(mapping.items()):
            if value.casefold() == command.name.casefold():
                mapping.pop(key, None)
                # Deleting a temp command retires its preset too, so the
                # thermostat's min/max and snap targets track reality.
                if key.startswith("temp_") and key[5:].isdigit():
                    degrees = int(key[5:])
                    presets = list(
                        device.entity_config.temperature_presets or []
                    )
                    if degrees in presets:
                        presets.remove(degrees)
                        device.entity_config.temperature_presets = (
                            sorted(presets) or None
                        )

    def get_device(self, device_id: str) -> IRDevice | None:
        return self._store.get_device(device_id)

    def get_all_devices(self) -> list[IRDevice]:
        return self._store.get_all_devices()


def prime_localized_auto_map() -> None:
    """Build the localized name->action table (blocking file I/O).

    Called once from ``async_setup_entry`` via the executor so the
    first assign-time auto-map never reads files on the event loop.
    """
    localized_auto_map(AUTO_MAP_RULES)


def _human_device_type(device_type: DeviceType) -> str:
    return {
        DeviceType.MEDIA_PLAYER: "Media Player",
        DeviceType.AC: "Air Conditioner",
        DeviceType.FAN: "Fan",
        DeviceType.LIGHT: "Light",
        DeviceType.SWITCH: "Switch",
        DeviceType.SCREEN: "Screen / Shade",
        DeviceType.OTHER: "IR Device",
    }.get(device_type, "IR Device")


def category_for_command_name(name: str) -> CommandCategory:
    """Best-effort category classification for a command name."""
    lowered = name.casefold()
    if "power" in lowered:
        return CommandCategory.POWER
    if "volume" in lowered or "mute" in lowered:
        return CommandCategory.VOLUME
    if "channel" in lowered:
        return CommandCategory.CHANNEL
    if any(
        token in lowered
        for token in ("up", "down", "left", "right", "ok", "back", "select")
    ):
        return CommandCategory.NAVIGATION
    if "mode" in lowered:
        return CommandCategory.MODE
    if "fan" in lowered or "speed" in lowered:
        return CommandCategory.FAN_SPEED
    if "temp" in lowered:
        return CommandCategory.TEMPERATURE
    return CommandCategory.CUSTOM
