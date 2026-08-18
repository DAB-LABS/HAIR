"""Data models for the HAIR integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from .const import (
    DEFAULT_CARRIER_FREQUENCY,
    DEFAULT_REPEAT_COUNT,
    TRIGGER_ALIAS_HISTORY_MAX,
    CaptureProviderType,
    CaptureState,
    CommandCategory,
    CommandSource,
    DeviceType,
)


def _new_id() -> str:
    return str(uuid4())


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class IRCommand:
    """A single IR command (learned or imported)."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    category: CommandCategory = CommandCategory.CUSTOM
    source: CommandSource = CommandSource.CAPTURED
    protocol: str | None = None
    code: str | None = None
    raw_timings: list[int] | None = None
    frequency: int = DEFAULT_CARRIER_FREQUENCY
    repeat_count: int = DEFAULT_REPEAT_COUNT
    # Whole-frame send count: transmit the built signal this many times
    # (1 = once). Orthogonal to repeat_count (NEC dittos) -- this loops the
    # entire frame protocol-agnostically. Set at assign, edited in the command
    # editor. Defaults to 1 so existing commands send once exactly as before.
    send_count: int = 1
    # Quantized byte hash carried over from the source signal on assign
    # (the v0.3.4 duplicate-guard tiebreaker). Optional; None for commands
    # created before 0.3.4 or from sources without a Pronto code.
    byte_hash: str | None = None
    # Decoded protocol identity (v0.4.0 Phase A). Populated when the
    # infrared-protocols library can read the signal as a known protocol
    # (NEC today). Lets the matcher key on the decoded fingerprint and the
    # TX path re-encode canonical timings. All None when undecodable or
    # for commands created before v0.4.0 (backfilled lazily on load).
    decoded_protocol: str | None = None
    decoded_address: int | None = None
    decoded_command: int | None = None
    decoded_fingerprint: str | None = None
    # Protocol state the decoded re-encode needs beyond the identity
    # triple (v0.6.0): RC-5/Marantz toggle, Sharp extension. Plain dict,
    # no schema; None for protocols without extras and for commands
    # stored before v0.6.0.
    decoded_extras: dict[str, int] | None = None
    # Per-command opt-out: when True, TX replays the captured Pronto rather
    # than re-encoding from the decoded value. Default False, so a command
    # with decoded fields transmits canonical timings unless the user
    # explicitly pins it to the captured ones.
    tx_force_raw: bool = False
    # Source attribution carried from a plucked signal on assign-to-device
    # (Plucker, v0.5.0). The user-typed vendor command name; None for
    # commands not sourced from a pluck.
    plucked_command_name: str | None = None
    # A PORTHOLE TO A LATTICE CELL (v0.9.5). Present only on the
    # coordinate-named rows a matrix device grows for cells the comb
    # doubted: {"mode", "fan", "swing", "temp"}. Every action through
    # such a row acts on the lattice rather than on this record -- TEST
    # sends the cell, edit rewrites it, delete removes it -- so the row
    # is a view, not a second copy that could drift from the matrix
    # store behind it.
    matrix_cell: dict[str, Any] | None = None
    # The comb doubted this row in the wig it was adopted from (v0.9.5).
    # Carried onto the device so the comb's receipt stops being
    # closet-only knowledge: the person can see what was doubted, test
    # exactly those, and attest them at export like any other row. It is
    # a note about where the code came from, not a verdict on it, so
    # nothing in HAIR treats it as a reason to refuse a send.
    comb_suspect: bool = False
    # WHICH finding flagged it: the comb's check class, e.g.
    # "duplicated-neighbour". The marker's tooltip says what the comb
    # actually found rather than a generic "suspect" -- the comb knows,
    # so the row should say (bench 2026-08-03).
    comb_finding: str | None = None
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": str(self.category),
            "source": str(self.source),
            "protocol": self.protocol,
            "code": self.code,
            "raw_timings": list(self.raw_timings) if self.raw_timings else None,
            "frequency": self.frequency,
            "repeat_count": self.repeat_count,
            "send_count": self.send_count,
            "byte_hash": self.byte_hash,
            "decoded_protocol": self.decoded_protocol,
            "decoded_address": self.decoded_address,
            "decoded_command": self.decoded_command,
            "decoded_fingerprint": self.decoded_fingerprint,
            "decoded_extras": dict(self.decoded_extras)
            if self.decoded_extras
            else None,
            "tx_force_raw": self.tx_force_raw,
            "plucked_command_name": self.plucked_command_name,
            "matrix_cell": dict(self.matrix_cell)
            if self.matrix_cell else None,
            "comb_suspect": self.comb_suspect,
            "comb_finding": self.comb_finding,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IRCommand:
        return cls(
            id=data.get("id") or _new_id(),
            name=data.get("name", ""),
            category=CommandCategory(data.get("category", CommandCategory.CUSTOM)),
            source=CommandSource(data.get("source", CommandSource.CAPTURED)),
            protocol=data.get("protocol"),
            code=data.get("code"),
            raw_timings=data.get("raw_timings"),
            frequency=int(data.get("frequency", DEFAULT_CARRIER_FREQUENCY)),
            repeat_count=int(data.get("repeat_count", DEFAULT_REPEAT_COUNT)),
            send_count=int(data.get("send_count", 1)),
            byte_hash=data.get("byte_hash"),
            decoded_protocol=data.get("decoded_protocol"),
            decoded_address=data.get("decoded_address"),
            decoded_command=data.get("decoded_command"),
            decoded_fingerprint=data.get("decoded_fingerprint"),
            decoded_extras=data.get("decoded_extras") or None,
            tx_force_raw=bool(data.get("tx_force_raw", False)),
            plucked_command_name=data.get("plucked_command_name"),
            matrix_cell=data.get("matrix_cell") or None,
            comb_suspect=bool(data.get("comb_suspect", False)),
            comb_finding=data.get("comb_finding") or None,
            created_at=data.get("created_at") or _now_iso(),
        )


@dataclass
class CommandTemplate:
    """Template for a suggested command during device setup."""

    name: str
    category: CommandCategory
    essential: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": str(self.category),
            "essential": self.essential,
        }


@dataclass
class EntityConfig:
    """Configuration for the HA entity created from an IR device."""

    platform: str = "remote"
    command_mapping: dict[str, str] = field(default_factory=dict)
    temperature_presets: list[int] | None = None
    hvac_modes: list[str] | None = None
    fan_modes: list[str] | None = None
    swing_modes: list[str] | None = None
    # Climate presets: the star (climate-presets-star.md). Command
    # NAMES a user starred on an AC device, in click order; the
    # climate entity turns them into Home Assistant preset_modes.
    #
    # NOT a command_mapping key, deliberately: ws_update_mapping
    # enforces one mapping key per command (it clears every key
    # pointing at the command before setting a new one), and a flat
    # "Cool" command is commonly mapped to mode_cool AND wants to be
    # starrable. A separate list is the only shape where both can be
    # true at once.
    #
    # Names, not ids, because that is how every other mapping on this
    # dataclass refers to commands, and the rename cascade in
    # device_manager.async_update_command already exists for names.
    # Absent in stored JSON reads as empty; empty means the entity
    # never advertises PRESET_MODE at all.
    starred: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "command_mapping": dict(self.command_mapping),
            "starred": list(self.starred),
            "temperature_presets": list(self.temperature_presets)
            if self.temperature_presets
            else None,
            "hvac_modes": list(self.hvac_modes) if self.hvac_modes else None,
            "fan_modes": list(self.fan_modes) if self.fan_modes else None,
            "swing_modes": list(self.swing_modes) if self.swing_modes else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityConfig:
        return cls(
            platform=data.get("platform", "remote"),
            command_mapping=dict(data.get("command_mapping") or {}),
            starred=list(data.get("starred") or []),
            temperature_presets=data.get("temperature_presets"),
            hvac_modes=data.get("hvac_modes"),
            fan_modes=data.get("fan_modes"),
            swing_modes=data.get("swing_modes"),
        )


@dataclass
class IRDevice:
    """An IR-controlled device managed by HAIR."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    device_type: DeviceType = DeviceType.OTHER
    manufacturer: str | None = None
    model: str | None = None
    emitter_entity_ids: list[str] = field(default_factory=list)
    # Power monitoring (Device Settings, 0.9.8). Install wiring, like
    # emitter_entity_ids -- which smart plug feeds this device, not
    # wig content. power_sensor_entity_id is a ``sensor.`` entity with
    # device_class power; both thresholds are watts. All three None
    # (the default) means no power monitoring configured.
    power_sensor_entity_id: str | None = None
    power_off_below_w: float | None = None
    power_on_above_w: float | None = None
    # Climate room sensors (climate-sensors.md, riding 0.9.8). Same
    # install-wiring status as power_sensor_entity_id above -- which
    # thermometer/hygrometer feeds this device's thermostat card, not
    # wig content. Each is a ``sensor.`` entity (device_class
    # temperature / humidity respectively); display only, no
    # thresholds, no coupling between the two -- either can be set or
    # cleared independently of the other. Both None (the default)
    # means no room sensors configured. Only meaningful on matrix
    # devices (climate_matrix True), but not validated against that
    # here -- the WS layer and the dialog gate on device type/matrix,
    # this field just holds whatever was last saved.
    temperature_sensor_entity_id: str | None = None
    humidity_sensor_entity_id: str | None = None
    capture_device_id: str | None = None
    capture_provider_type: CaptureProviderType = CaptureProviderType.ESPHOME
    commands: list[IRCommand] = field(default_factory=list)
    entity_config: EntityConfig = field(default_factory=EntityConfig)
    database_id: str | None = None
    # Climate state matrix marker (Cold Cuts, v0.8.8). True = this
    # device's climate entity runs in matrix mode off a
    # ``hair/matrices/<device_id>.matrix.json`` file. A boolean, not a
    # path or an embedded blob: the reference is implicit (the file is
    # named by this device's id) and the matrix stays OUT of the
    # devices JSON, which storage.py rewrites wholesale on every
    # update (census worst case 7.9 MB; addendum 2.3).
    climate_matrix: bool = False
    # WHERE THIS DEVICE CAME FROM (v0.9.5 Fitting Room). Set at adopt
    # and never by hand.
    #
    # ``source_wig_id`` is the wig's UUID, and its PRESENCE is the
    # "this is an existing wig" tag -- there is no separate flag,
    # because a second field could disagree with the first. It is what
    # SAVE TO CLOSET reads to decide between offering UPDATE and
    # offering CREATE, and what the shop routes a resulting PR by.
    #
    # ``source_file`` is the seed filename for a device built from a
    # converted foreign file. That is a CREATE with provenance, not an
    # update: nothing in the closet owns the result yet.
    #
    # Both None for a device built from scratch by sniffing or
    # clipping. Local renames and send-count tweaks never touch either.
    source_wig_id: str | None = None
    source_file: str | None = None
    # WHERE THIS DEVICE CAME FROM, mirror-door half (signpost 3, Track
    # 3.5, owner-directed 2026-08-15). The device-side twin of
    # TriggerRemote.source_device_id: set only by
    # ws_trigger_remote_make_device to the source Remote's id, so the
    # Track 3.5 pin prompt can offer to pin the new device straight
    # back to it -- a mirror-door mint's source IS its counterpart by
    # construction. Mutually exclusive with source_wig_id in practice
    # (a device is adopted from a wig OR minted from a remote's
    # triggers, never both); nothing enforces that here, same as
    # source_wig_id/source_file's own unenforced exclusivity above.
    source_remote_id: str | None = None
    # Creation-door provenance (Add Popups signpost 2, 2026-08-10
    # provenance ruling): "manual" | "closet" | "device" | "remote",
    # taken from whichever tab of the add dialog created this device.
    # Distinct from source_wig_id/source_file above -- those answer
    # "which wig, if any, backs this device" for the closet's own
    # update-vs-create routing; this answers "which door was clicked"
    # and exists for every device regardless of wig linkage. None for
    # devices created before this field existed; not backfilled, per
    # the ruling ("no chip renders yet -- the field is the point").
    origin: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def get_command(self, command_id: str) -> IRCommand | None:
        for command in self.commands:
            if command.id == command_id:
                return command
        return None

    def get_command_by_name(self, name: str) -> IRCommand | None:
        target = name.casefold()
        for command in self.commands:
            if command.name.casefold() == target:
                return command
        return None

    def add_command(self, command: IRCommand) -> None:
        existing = self.get_command_by_name(command.name)
        if existing is not None:
            self.replace_command(existing.id, command)
        else:
            self.commands.append(command)
        self.updated_at = _now_iso()

    def remove_command(self, command_id: str) -> bool:
        for index, command in enumerate(self.commands):
            if command.id == command_id:
                del self.commands[index]
                self.updated_at = _now_iso()
                return True
        return False

    def replace_command(self, command_id: str, new_command: IRCommand) -> bool:
        for index, command in enumerate(self.commands):
            if command.id == command_id:
                new_command.id = command.id
                self.commands[index] = new_command
                self.updated_at = _now_iso()
                return True
        return False

    def clone(self, new_name: str) -> IRDevice:
        """Return a deep copy of this device with a new id and name.

        Every ``IRCommand`` on the clone gets a fresh id but otherwise
        mirrors the source command (protocol, code, raw_timings, category,
        etc). The ``entity_config`` mapping is deep-copied so action
        bindings come along. Emitter assignments and the capture device
        are copied as-is -- the user almost always re-points the clone
        to a different emitter, but copying lets them verify the clone
        works first before reassigning.

        Triggers are NOT cloned. They live in the trigger store, reference
        specific command ids, and auto-duplicating them would create
        duplicate event entities firing on the same physical button.
        """
        cloned_commands = [
            IRCommand(
                name=cmd.name,
                category=cmd.category,
                source=cmd.source,
                protocol=cmd.protocol,
                code=cmd.code,
                raw_timings=(
                    list(cmd.raw_timings) if cmd.raw_timings else None
                ),
                frequency=cmd.frequency,
                repeat_count=cmd.repeat_count,
                send_count=cmd.send_count,
                # Carry every signal-identity field so a clone matches and
                # transmits exactly like its source. Dropping any of these
                # silently degrades dedup (byte_hash) or canonical TX
                # (decoded_*) on the clone.
                byte_hash=cmd.byte_hash,
                decoded_protocol=cmd.decoded_protocol,
                decoded_extras=(
                    dict(cmd.decoded_extras) if cmd.decoded_extras else None
                ),
                decoded_address=cmd.decoded_address,
                decoded_command=cmd.decoded_command,
                decoded_fingerprint=cmd.decoded_fingerprint,
                tx_force_raw=cmd.tx_force_raw,
            )
            for cmd in self.commands
        ]
        cloned_entity_config = EntityConfig(
            platform=self.entity_config.platform,
            command_mapping=dict(self.entity_config.command_mapping),
            # The clone's commands keep their names, so the starred
            # names still point at real commands on the copy.
            starred=list(self.entity_config.starred),
            temperature_presets=(
                list(self.entity_config.temperature_presets)
                if self.entity_config.temperature_presets
                else None
            ),
            hvac_modes=(
                list(self.entity_config.hvac_modes)
                if self.entity_config.hvac_modes
                else None
            ),
            fan_modes=(
                list(self.entity_config.fan_modes)
                if self.entity_config.fan_modes
                else None
            ),
            swing_modes=(
                list(self.entity_config.swing_modes)
                if self.entity_config.swing_modes
                else None
            ),
        )
        return IRDevice(
            name=new_name,
            device_type=self.device_type,
            manufacturer=self.manufacturer,
            model=self.model,
            emitter_entity_ids=list(self.emitter_entity_ids),
            # Install wiring copies as-is, same as emitter_entity_ids --
            # see the field comment above.
            power_sensor_entity_id=self.power_sensor_entity_id,
            power_off_below_w=self.power_off_below_w,
            power_on_above_w=self.power_on_above_w,
            temperature_sensor_entity_id=self.temperature_sensor_entity_id,
            humidity_sensor_entity_id=self.humidity_sensor_entity_id,
            capture_device_id=self.capture_device_id,
            capture_provider_type=self.capture_provider_type,
            commands=cloned_commands,
            entity_config=cloned_entity_config,
            database_id=self.database_id,
            # The flag rides; the matrix FILE is copied by the
            # duplicate path (device_manager/WS) via copy_matrix,
            # since a dataclass copy cannot touch disk.
            climate_matrix=self.climate_matrix,
        )

    def reorder_commands(self, command_ids: list[str]) -> None:
        """Reorder ``self.commands`` to match the given ID list.

        The provided list must contain exactly the set of IDs currently
        held by this device -- no duplicates, no unknown IDs, no missing
        IDs. This is intentional: callers (the drag-to-reorder UI) always
        send the complete list, so any divergence indicates a bug or a
        stale client that should be rejected loudly rather than silently
        accepted.

        Raises :class:`ValueError` on any of those mismatches and leaves
        ``self.commands`` untouched.
        """
        if len(command_ids) != len(set(command_ids)):
            raise ValueError("Duplicate command IDs in reorder list")
        current_ids = {c.id for c in self.commands}
        requested_ids = set(command_ids)
        if requested_ids != current_ids:
            missing = current_ids - requested_ids
            unknown = requested_ids - current_ids
            details: list[str] = []
            if missing:
                details.append(f"missing {sorted(missing)}")
            if unknown:
                details.append(f"unknown {sorted(unknown)}")
            raise ValueError(
                "Reorder list does not match current commands: "
                + ", ".join(details)
            )

        by_id = {c.id: c for c in self.commands}
        self.commands = [by_id[cid] for cid in command_ids]
        self.updated_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": str(self.device_type),
            "manufacturer": self.manufacturer,
            "model": self.model,
            "emitter_entity_ids": list(self.emitter_entity_ids),
            "power_sensor_entity_id": self.power_sensor_entity_id,
            "power_off_below_w": self.power_off_below_w,
            "power_on_above_w": self.power_on_above_w,
            "temperature_sensor_entity_id": self.temperature_sensor_entity_id,
            "humidity_sensor_entity_id": self.humidity_sensor_entity_id,
            "capture_device_id": self.capture_device_id,
            "capture_provider_type": str(self.capture_provider_type),
            "commands": [c.to_dict() for c in self.commands],
            "entity_config": self.entity_config.to_dict(),
            "database_id": self.database_id,
            "climate_matrix": self.climate_matrix,
            "source_wig_id": self.source_wig_id,
            "source_file": self.source_file,
            "source_remote_id": self.source_remote_id,
            "origin": self.origin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IRDevice:
        # Migrate legacy device types to media_player.
        _LEGACY_MEDIA_TYPES = {"tv", "soundbar", "projector"}
        raw_type = data.get("device_type", DeviceType.OTHER)
        if raw_type in _LEGACY_MEDIA_TYPES:
            raw_type = "media_player"

        return cls(
            id=data.get("id") or _new_id(),
            name=data.get("name", ""),
            device_type=DeviceType(raw_type),
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            emitter_entity_ids=list(data.get("emitter_entity_ids") or []),
            # Absent on every device made before this field existed;
            # resolves to "no power monitoring configured".
            power_sensor_entity_id=data.get("power_sensor_entity_id") or None,
            power_off_below_w=data.get("power_off_below_w"),
            power_on_above_w=data.get("power_on_above_w"),
            # Absent on every device made before this field existed
            # (and on every non-matrix device); resolves to "no room
            # sensor configured", same as the power sensor above.
            temperature_sensor_entity_id=(
                data.get("temperature_sensor_entity_id") or None
            ),
            humidity_sensor_entity_id=(
                data.get("humidity_sensor_entity_id") or None
            ),
            capture_device_id=data.get("capture_device_id"),
            capture_provider_type=CaptureProviderType(
                data.get("capture_provider_type", CaptureProviderType.ESPHOME)
            ),
            commands=[
                IRCommand.from_dict(c) for c in (data.get("commands") or [])
            ],
            entity_config=EntityConfig.from_dict(data.get("entity_config") or {}),
            database_id=data.get("database_id"),
            # Absent (pre-0.8.8 record) resolves to False = preset mode.
            climate_matrix=bool(data.get("climate_matrix", False)),
            # Absent on every device made before v0.9.5, which reads
            # correctly as "built from scratch here".
            source_wig_id=data.get("source_wig_id") or None,
            source_file=data.get("source_file") or None,
            # Absent on every device made before Track 3.5 (signpost 3);
            # resolves correctly as "not minted from a remote".
            source_remote_id=data.get("source_remote_id") or None,
            # Absent on every device made before Add Popups signpost 2;
            # not backfilled, per the provenance ruling.
            origin=data.get("origin") or None,
            created_at=data.get("created_at") or _now_iso(),
            updated_at=data.get("updated_at") or _now_iso(),
        )


@dataclass
class IRTrigger:
    """An IR trigger that fires an HA event entity on signal match."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    signal_fingerprint: str = ""
    protocol: str | None = None
    code: str | None = None
    min_hits: int = 1
    enabled: bool = True
    source_device_id: str | None = None
    source_command_id: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    # Location-aware trigger scope (v0.5.7). Empty = fires on any receiver
    # (backward-compatible with pre-0.5.7 triggers). Non-empty = fires only
    # when the capturing receiver's entity_id is in this list. Legacy captures
    # (receiver_entity_id None) never match a scoped trigger.
    receiver_entity_ids: list[str] = field(default_factory=list)
    # Byte-level identity (v0.5.8). Sub-threshold protocols (Sony SIRC,
    # Panasonic/Kaseikyo, TCL) collapse distinct buttons onto one S/L
    # fingerprint; the v0.3.4 byte_hash tiebreaker separates them. None =
    # legacy trigger = byte_hash-agnostic (pre-0.5.8 behavior). Set at
    # creation from the source signal/command so the trigger fires only
    # on its own button. See matches_signal().
    byte_hash: str | None = None
    # Decoded protocol identity (v0.5.8, unified identity). The strongest
    # identity tier: jitter-immune, so it keeps a trigger firing even when
    # a boundary protocol's S/L fingerprint flips between captures. None =
    # not decoded (no decoder for the protocol, or a pre-upgrade record
    # before the load-time backfill runs). Backfilled at load from the
    # stored code -- decode is checksum-validated, so the backfill is safe
    # in a way a byte_hash backfill would not be (bin-quantized hashes are
    # snap-fragile and a tier-2 mismatch is fatal; see the plan doc).
    decoded_fingerprint: str | None = None
    # Trigger Remotes signpost 1. List position for the automation-editor
    # dropdown (device_trigger.async_get_triggers) and, later, drag reorder.
    # None = not yet assigned; the storage load-time backfill
    # (_backfill_trigger_order) assigns one from the trigger's position in
    # the stored list so a pre-upgrade catalog lists in its existing order
    # rather than every legacy trigger tying at the same value. Creation
    # assigns max(existing) + 1 so new triggers append to the end.
    order: int | None = None
    # Alias history (device_trigger rename tolerance). A device trigger's
    # stored subtype is the trigger's NAME, not its id (HA's automation
    # editor renders the subtype raw and stores what it shows), so a rename
    # would silently strand every automation built against the old name.
    # Each rename retires the name being replaced onto the front of this
    # list (most-recent-first, deduped, capped at
    # TRIGGER_ALIAS_HISTORY_MAX). Resolution is current-names-first, then
    # history -- see device_trigger.py. Empty for a trigger that has never
    # been renamed.
    alias_history: list[str] = field(default_factory=list)
    # Trigger Remotes signpost 1, Track B (the row's "aliveness" fact --
    # trigger-remote-detail-design-brief.md, "live hit count -- last
    # fired"). Cumulative across restarts, incremented once per
    # CONFIRMED fire (i.e. once the min_hits chain actually completes
    # and the event entity fires), not once per raw hit -- a min_hits=3
    # trigger presses three times for one fire_count increment. Unlike
    # ``last fired``, HA's event-entity state has no equivalent lifetime
    # counter to read this from, so this is real, new, persisted state
    # rather than a value derived from something HA already tracks.
    fire_count: int = 0
    # ISO timestamp of the last confirmed fire. The design brief's own
    # wording points at "the event entity's state" for this fact, since
    # an HA event entity's state IS its last-fired timestamp -- but
    # reading it back would mean the frontend resolving each trigger's
    # auto-assigned entity_id through the entity registry on every
    # render, a fragile round trip for a value TriggerManager already
    # computes at the moment it fires. Stamping it here alongside
    # fire_count produces the identical displayed value from a single
    # write, with no dependency on registry timing.
    last_fired_at: str | None = None
    # Owning remote (Add Popups signpost 2, Track 1B). None = the HAIR
    # Triggers drawer -- the same "no explicit group" default
    # trigger-remotes.md section 4.1 specified: "None means the default
    # HAIR Triggers device. No migration hook." Every pre-signpost-2
    # Origin vocabulary (Add Popups signpost 2, Track 3; extended
    # 2026-08-18): "closet" a wig file, "matrix" a lattice cell,
    # "device" a HAIR device command, "clip" a Clipper paste,
    # "plucked" a Plucker pull, "remote" a SNIFFED catalog row,
    # "manual" or None the drawer dialog. Which of these are
    # file-sourced is identity.FILE_SOURCED_TRIGGER_ORIGINS. The panel
    # only ever tests this field for equality against "matrix"
    # (ir-trigger-row.ts), so new values need no frontend change.
    # trigger reads as drawer-owned with zero backfill needed. Set once
    # at creation (Manual/Closet/Device tabs of the new Add Trigger
    # Remote dialog, or the drawer's own "+ Add Trigger" leaving it
    # None); never reassigned afterward -- moving between remotes was
    # ruled out 2026-08-10 ("they just create a brand new one... and put
    # it on the other device"). unique_id (event.py) is qualified by
    # this field so the same signal can legitimately carry triggers on
    # two different remotes.
    trigger_remote_id: str | None = None
    # Creation-door provenance (2026-08-10 origin-tracking ruling):
    # "manual" | "closet" | "device" | "remote". Drawer-created triggers
    # (the existing "+ Add Trigger" dialog, untouched by signpost 2) get
    # "manual" going forward. None for triggers created before this
    # field existed; not backfilled.
    origin: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "signal_fingerprint": self.signal_fingerprint,
            "protocol": self.protocol,
            "code": self.code,
            "min_hits": self.min_hits,
            "enabled": self.enabled,
            "source_device_id": self.source_device_id,
            "source_command_id": self.source_command_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "receiver_entity_ids": list(self.receiver_entity_ids),
            "byte_hash": self.byte_hash,
            "decoded_fingerprint": self.decoded_fingerprint,
            "order": self.order,
            "alias_history": list(self.alias_history),
            "fire_count": self.fire_count,
            "last_fired_at": self.last_fired_at,
            "trigger_remote_id": self.trigger_remote_id,
            "origin": self.origin,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IRTrigger:
        return cls(
            id=data.get("id") or _new_id(),
            name=data.get("name", ""),
            signal_fingerprint=data.get("signal_fingerprint", ""),
            protocol=data.get("protocol"),
            code=data.get("code"),
            min_hits=int(data.get("min_hits", 1)),
            enabled=bool(data.get("enabled", True)),
            source_device_id=data.get("source_device_id"),
            source_command_id=data.get("source_command_id"),
            created_at=data.get("created_at") or _now_iso(),
            updated_at=data.get("updated_at") or _now_iso(),
            # Absent (pre-0.5.7 record) or null both resolve to [] = unscoped.
            receiver_entity_ids=list(data.get("receiver_entity_ids") or []),
            # Absent (pre-0.5.8 record) or null both resolve to None =
            # byte_hash-agnostic, matching the pre-0.5.8 behavior.
            byte_hash=data.get("byte_hash"),
            # Absent or null = not decoded; the load-time backfill fills
            # this from the stored code where a decoder exists.
            decoded_fingerprint=data.get("decoded_fingerprint"),
            # Absent (pre-signpost-1 record) or null = not yet assigned;
            # the storage load-time backfill fills this from list position.
            order=data.get("order"),
            # Absent or null both resolve to [] = never renamed.
            alias_history=list(data.get("alias_history") or []),
            # Absent (pre-Track-B record) = never fired since this field
            # existed. Not backfilled from anything -- there is no prior
            # source of truth for a lifetime fire count.
            fire_count=int(data.get("fire_count", 0)),
            last_fired_at=data.get("last_fired_at"),
            # Absent (pre-signpost-2 record) or null both resolve to
            # None = owned by the HAIR Triggers drawer. No migration
            # hook, matching trigger-remotes.md section 4.1.
            trigger_remote_id=data.get("trigger_remote_id") or None,
            # Absent on every trigger made before signpost 2; not
            # backfilled, per the provenance ruling.
            origin=data.get("origin") or None,
        )

    def rename(self, new_name: str) -> None:
        """Rename the trigger, retiring the old name into alias history.

        No-op when the name is unchanged or was never set (creation path
        should not seed history with an empty string). Most-recent-first,
        deduped against both the rest of the history and the new name
        itself (renaming back to a name already in history should not
        leave a duplicate entry), capped at TRIGGER_ALIAS_HISTORY_MAX,
        trimmed from the oldest (tail) end.

        Live-names-always-win resolution (device_trigger.py) means a
        stale history entry that a later trigger's current name shadows
        is harmless to keep here; this trigger's own record does not know
        about other triggers and should not try to.
        """
        old_name = self.name
        if not old_name or old_name == new_name:
            self.name = new_name
            return
        history = [n for n in self.alias_history if n != old_name and n != new_name]
        history.insert(0, old_name)
        self.alias_history = history[:TRIGGER_ALIAS_HISTORY_MAX]
        self.name = new_name

    def matches_byte_hash(self, byte_hash: str | None) -> bool:
        """Return True if this trigger's byte-level identity matches.

        Three-way None-tolerant rule: a legacy trigger (``self.byte_hash``
        None) matches anything; an incoming signal without a byte_hash
        (non-Pronto or malformed code) matches anything; otherwise the two
        hashes must be equal. Keeps pre-0.5.8 triggers firing broadly while
        new triggers distinguish sub-threshold buttons (Sony et al).

        Retained as the tier-2-only comparison; production matching goes
        through :meth:`matches_signal`, which layers the decoded tier on
        top and drops the fingerprint-equality precondition.
        """
        if self.byte_hash is None or byte_hash is None:
            return True
        return self.byte_hash == byte_hash

    def matches_signal(
        self,
        fingerprint: str,
        byte_hash: str | None = None,
        decoded_fingerprint: str | None = None,
    ) -> bool:
        """Tiered identity match against an incoming signal (v0.5.8).

        Decoded > byte_hash > S/L fingerprint; the highest tier both
        sides carry decides (see ``identity.SignalIdentity``). Notably
        this DROPS the old fingerprint-equality precondition: a Sony
        capture whose S/L fingerprint flipped across the 48-unit
        threshold still matches its trigger via byte_hash, which is the
        bench-verified failure the unified-identity work exists to fix.
        Legacy triggers (no hash, no decoded identity) still match on
        fingerprint alone, exactly as before.
        """
        from .identity import SignalIdentity

        return SignalIdentity(
            self.decoded_fingerprint, self.byte_hash, self.signal_fingerprint
        ).same_as(
            SignalIdentity(decoded_fingerprint, byte_hash, fingerprint)
        )

    def matches_receiver(self, receiver_entity_id: str | None) -> bool:
        """Return True if this trigger's scope matches the capturing receiver.

        Empty ``receiver_entity_ids`` = unscoped = matches any receiver,
        including None (legacy captures). A non-empty list matches only when
        ``receiver_entity_id`` is in the list; legacy captures (None) never
        match a scoped trigger.
        """
        if not self.receiver_entity_ids:
            return True
        if receiver_entity_id is None:
            return False
        return receiver_entity_id in self.receiver_entity_ids


@dataclass
class TriggerRemote:
    """A named group that triggers belong to (Add Popups signpost 2).

    Each remote becomes a real HA device carrying its triggers' event
    entities and device-trigger dropdown, per trigger-remotes.md
    section 4.1. Deliberately thin -- area lives in Home Assistant, not
    here. The HAIR Triggers drawer is NOT one of these: it is the
    ``trigger_remote_id is None`` default (event.py's fixed
    ``TRIGGER_DEVICE_ID``), non-deletable by construction since there
    is no row here to delete.
    """

    id: str = field(default_factory=_new_id)
    name: str = ""
    # Remote-level receiver scope (2026-08-10 scoping ruling). Empty =
    # any receiver. No per-trigger receiver UI ever appears on a named
    # remote's rows -- that stays exclusive to HAIR Triggers drawer
    # rows, which keep their own per-trigger receiver_entity_ids.
    receiver_scope: list[str] = field(default_factory=list)
    # Creation-door provenance (2026-08-10 origin-tracking ruling):
    # "manual" | "closet" | "device" | "remote", taken from the tab
    # that created this remote.
    origin: str | None = None
    # WHERE IT CAME FROM (signpost 3, Track 2 item 4) -- the remote-side
    # twin of IRDevice.source_wig_id. Written only by ws_wig_make_remote's
    # filename path (a codebook-made remote renders a transient wig that
    # was never in the closet and has nothing to inherit, so this stays
    # None for that door, exactly as the device side does). The linked-
    # count "pointer wins" rule (_wig_linked_remotes) reads this so a
    # matrix wig's remote -- which, like a matrix device, may carry no
    # flat signals to identity-match against -- still chips its wig.
    source_wig_id: str | None = None
    # WHERE THIS REMOTE CAME FROM, mirror-door half (signpost 3, Track
    # 3.5, owner-directed 2026-08-15). The remote-side twin of
    # IRDevice.source_remote_id (and, by shape, of source_wig_id just
    # above): set only by ws_device_make_remote to the source Device's
    # id, so the Track 3.5 pin prompt can offer to pin the new remote
    # straight back to it. Mutually exclusive with source_wig_id in
    # practice, same unenforced convention as the device side.
    source_device_id: str | None = None
    # THE PIN SCOPE SPLIT (signpost 3 coding-plan.md section 0b). The
    # many-to-many seed: which HAIR devices this remote's presses are
    # meant to drive. Storing a pin here does NOTHING yet -- no
    # retransmit, no derivation, no echo defense; that machinery, and
    # turning stored pins live, is signpost 4 / Release B. The device
    # side deliberately stores nothing of its own and stays a derived
    # view (queried by scanning every remote's pinned_device_ids for a
    # given device id) so the link only ever lives in one place. All
    # pin UI reading this stays behind ir-pin-flag.ts's
    # PINNING_UI_ENABLED = False until the owner flips it at the
    # signpost boundary.
    pinned_device_ids: list[str] = field(default_factory=list)
    # DERIVED BUTTON MAP (signpost 4, Track 1): per pinned device,
    # which command each of this remote's triggers drives --
    # {device_id: {trigger_id: command_id}}. Content-matched by
    # pin_bindings.derive_bindings and rewritten whenever either side
    # changes (pin, unpin, trigger or command mutation). NEVER computed
    # on the fire path, which only reads it. A pinned device sharing no
    # content maps to an empty dict, which is how a detail page tells
    # "pinned, nothing matched" apart from "not pinned at all".
    bindings: dict[str, dict[str, str]] = field(default_factory=dict)
    # THE HEAR-SIDE LATTICE (signpost 4, Track M). The exact mirror of
    # IRDevice.climate_matrix, and a boolean for the same reason: the
    # matrix itself lives in its own file at
    # ``hair/matrices/<remote_id>.matrix.json`` (matrix_store names
    # files by whatever id it is handed and both tables mint uuid4, so
    # remotes and devices share one flat namespace without colliding),
    # and the reference stays implicit so a remote payload cannot
    # orphan-point at a wrong matrix. A matrix Remote HEARS its
    # lattice where a matrix Device SENDS from one -- same bytes,
    # opposite direction.
    climate_matrix: bool = False
    # THE MOST RECENT STATE HEARD (signpost 4, Track M, handoff
    # reviewer addendum "Persistence"). Stamped by the matrix listener
    # on every heard cell the way _fire_trigger stamps a trigger's
    # fire_count, and the single stored fact behind three surfaces: the
    # card's rest ring, its slim readout, and the LAST HEARD row. Absent
    # (None) reads as "Nothing heard yet" and is what a remote carries
    # until its handset is first heard. Shape: cell_key, cell_name,
    # power ("on"/"off"/None), at (iso), sl_pattern, receiver_entity_id,
    # receiver_area_name. A loose dict rather than a dataclass because
    # nothing computes on it -- it is stamped whole and rendered whole.
    last_heard: dict[str, Any] | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "receiver_scope": list(self.receiver_scope),
            "origin": self.origin,
            "source_wig_id": self.source_wig_id,
            "source_device_id": self.source_device_id,
            "pinned_device_ids": list(self.pinned_device_ids),
            "bindings": {
                d: dict(m) for d, m in self.bindings.items()
            },
            "climate_matrix": self.climate_matrix,
            "last_heard": (
                dict(self.last_heard) if self.last_heard else None
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TriggerRemote:
        return cls(
            id=data.get("id") or _new_id(),
            name=data.get("name", ""),
            receiver_scope=list(data.get("receiver_scope") or []),
            origin=data.get("origin"),
            source_wig_id=data.get("source_wig_id"),
            # Absent on every remote made before Track 3.5 (signpost 3);
            # resolves correctly as "not minted from a device".
            source_device_id=data.get("source_device_id"),
            pinned_device_ids=list(data.get("pinned_device_ids") or []),
            # Absent on every remote written before signpost 4, and on
            # any remote pinned during signpost 3's dark period --
            # both resolve to {} and are filled by the load-time
            # backfill in HAIRStore.async_load. Coerced defensively:
            # a hand-edited store must not put non-strings on the
            # fire path.
            bindings={
                str(d): {
                    str(t): str(c) for t, c in m.items()
                }
                for d, m in (data.get("bindings") or {}).items()
                if isinstance(m, dict)
            },
            # Absent on every remote written before signpost 4's Track
            # M; False and None are exactly right for one -- no matrix
            # file was ever written under its id, and nothing has been
            # heard into a lattice it does not have.
            climate_matrix=bool(data.get("climate_matrix", False)),
            last_heard=(
                dict(lh)
                if isinstance(lh := data.get("last_heard"), dict)
                else None
            ),
            created_at=data.get("created_at") or _now_iso(),
            updated_at=data.get("updated_at") or _now_iso(),
        )

    def matches_receiver(self, receiver_entity_id: str | None) -> bool:
        """Return True if this remote's scope matches the capturing receiver.

        Same three-way shape as ``IRTrigger.matches_receiver``: empty
        scope = unscoped = matches any receiver, including a legacy
        capture with no receiver_entity_id at all.
        """
        if not self.receiver_scope:
            return True
        if receiver_entity_id is None:
            return False
        return receiver_entity_id in self.receiver_scope

    def clone(self, new_name: str) -> TriggerRemote:
        """Return a copy of this remote (not its triggers) under a new name.

        Add Popups signpost 2, Track 5: mirrors IRDevice.clone()'s
        shape -- fresh id/timestamps, everything else about the remote
        itself copied. receiver_scope is copied since it is genuinely
        part of the remote's own identity; origin is always "manual"
        since duplicating is itself a manual action regardless of how
        the source remote was created.

        This does NOT touch triggers. Unlike IRDevice.clone(), which
        explicitly excludes them (see that method's own docstring),
        the caller here (ws_duplicate_trigger_remote) copies them
        separately -- a trigger remote's triggers are its entire
        content, so leaving that decision to a shared dataclass method
        would either force it on every caller or require a parameter
        this method has no other reason to carry.

        ``climate_matrix`` rides along, exactly as IRDevice.clone()
        carries it: the FLAG is part of what this remote is, the FILE
        is the caller's job (ws_duplicate_trigger_remote copies it and
        clears the flag if the copy fails, the same shape
        ws_duplicate_device already uses). ``last_heard`` does NOT: a
        copy has heard nothing, and inheriting a timestamp would put a
        stale "2 min ago" on a remote that has never been in the room.
        """
        return TriggerRemote(
            name=new_name,
            receiver_scope=list(self.receiver_scope),
            origin="manual",
            climate_matrix=self.climate_matrix,
        )


@dataclass
class CaptureResult:
    """Result from a capture provider."""

    protocol: str | None = None
    code: str | None = None
    raw_timings: list[int] = field(default_factory=list)
    frequency: int = DEFAULT_CARRIER_FREQUENCY
    confidence: float = 1.0

    def matches(self, other: CaptureResult, tolerance: float = 0.1) -> bool:
        """Return True if two captures appear to be the same signal.

        Compares protocol/code first (cheap exact match). If either lacks an
        encoded code, falls back to raw-timing comparison within tolerance.
        """
        if self.protocol and other.protocol and self.code and other.code:
            return self.protocol == other.protocol and self.code == other.code

        if not self.raw_timings or not other.raw_timings:
            return False
        if abs(len(self.raw_timings) - len(other.raw_timings)) > 2:
            return False
        length = min(len(self.raw_timings), len(other.raw_timings))
        if length == 0:
            return False
        diffs = 0
        for a, b in zip(self.raw_timings[:length], other.raw_timings[:length], strict=False):
            if abs(a) == 0:
                continue
            if abs(a - b) / max(abs(a), 1) > tolerance:
                diffs += 1
        return diffs / length < tolerance

    def to_command(
        self, name: str, category: CommandCategory
    ) -> IRCommand:
        return IRCommand(
            name=name,
            category=category,
            source=CommandSource.CAPTURED,
            protocol=self.protocol,
            code=self.code,
            raw_timings=list(self.raw_timings) if self.raw_timings else None,
            frequency=self.frequency,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "code": self.code,
            "raw_timings": list(self.raw_timings),
            "frequency": self.frequency,
            "confidence": self.confidence,
        }


@dataclass
class CaptureSession:
    """Active capture session state."""

    session_id: str = field(default_factory=_new_id)
    device_id: str = ""
    provider_type: CaptureProviderType = CaptureProviderType.ESPHOME
    state: CaptureState = CaptureState.IDLE
    started_at: str = field(default_factory=_now_iso)
    result: CaptureResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "provider_type": str(self.provider_type),
            "state": str(self.state),
            "started_at": self.started_at,
            "result": self.result.to_dict() if self.result else None,
        }


# ---------------------------------------------------------------------------
# Signal Monitor models
# ---------------------------------------------------------------------------


@dataclass
class UnknownSignal:
    """A single unidentified IR signal observed by the signal monitor."""

    # Stable per-signal identity. The S/L ``fingerprint`` is NOT unique on
    # a remote once the byte-hash tiebreaker (v0.3.4) stores two distinct
    # commands that share an S/L pattern (Panasonic, TCL, Sony, etc.), so
    # all per-signal operations (alias, delete, test, assign, reorder, the
    # frontend row key) key on this id, not the fingerprint. Triggers key
    # on (fingerprint, byte_hash) since v0.5.8; a None trigger byte_hash
    # (pre-0.5.8) matches any hash on the fingerprint.
    id: str = field(default_factory=_new_id)
    fingerprint: str = ""
    # Quantized byte hash, the duplicate-guard tiebreaker layered on top of
    # the S/L fingerprint. Two signals with the same fingerprint but
    # different byte_hash are distinct. None for pre-0.3.4 records until
    # populated lazily on load.
    byte_hash: str | None = None
    # Decoded protocol identity (v0.4.0 Phase A). Populated at capture
    # when the infrared-protocols library can read the signal (NEC today),
    # and backfilled on load for older records. None when undecodable.
    decoded_protocol: str | None = None
    decoded_address: int | None = None
    decoded_command: int | None = None
    decoded_fingerprint: str | None = None
    # Protocol state beyond the identity triple (v0.6.0): RC-5/Marantz
    # toggle, Sharp extension. Carried onto the IRCommand at assign time
    # via _apply_signal_provenance so decoded TX can re-encode it.
    decoded_extras: dict[str, int] | None = None
    protocol: str | None = None
    code: str | None = None
    raw_timings: list[int] = field(default_factory=list)
    frequency: int = DEFAULT_CARRIER_FREQUENCY
    hit_count: int = 0
    first_seen: str = field(default_factory=_now_iso)
    last_seen: str = field(default_factory=_now_iso)
    source: Literal["sniffed", "manual", "plucked", "echo"] = "sniffed"
    alias: str = ""
    # User-typed vendor command name for a plucked signal (Plucker, v0.5.0).
    # None for sniffed/manual signals. Preserved across a Pronto edit.
    plucked_command_name: str | None = None
    # User-tunable TX knobs (mirror IRCommand, default to the same values).
    # Surfaced in the signal editor as "Send times" and "Ditto count" so a
    # user can tune them on the catalog signal before assigning; carried onto
    # the new IRCommand at assign time via _apply_signal_provenance.
    repeat_count: int = DEFAULT_REPEAT_COUNT  # NEC ditto count
    send_count: int = 1  # whole-frame TX count
    # Send the captured Pronto verbatim instead of re-encoding from the
    # decoded identity (Highlights, GH #78). The third knob of exactly
    # the same kind as the two above, and it exists because a capture
    # whose repeats are baked in has no other way to declare itself: a
    # Symphony repeat-train re-encodes to one clean frame and the device
    # ignores it.
    #
    # A USER DECISION, and it survives re-capture on purpose. The capture
    # path only touches hit_count and last_seen on an existing signal, so
    # this rides through untouched like send_count and repeat_count
    # already do. Do not add a refresh-on-hit that resets it.
    tx_force_raw: bool = False
    # Mirror provenance (v0.6.6). Only ever set on rows of the synthetic
    # Mirror device: a human-readable line describing the most recent send
    # ("Test AC / Temp 22 -- via Living Room Broadlink"), and the receiver
    # entity ids whose echoes matched that send's window (empty list =
    # sent, not heard; None = not a Mirror row).
    echo_source: str | None = None
    heard_by: list[str] | None = None
    # Capture-side observation: count of NEC dittos that followed the main
    # frame within the attribution window. Max-merge (high water mark) across
    # captures so a held-press observation persists across later brief taps.
    # Read-only at the model layer; surfaced as a UI hint. NOT carried onto an
    # IRCommand at assign time.
    observed_repeat_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "fingerprint": self.fingerprint,
            "byte_hash": self.byte_hash,
            "decoded_protocol": self.decoded_protocol,
            "decoded_address": self.decoded_address,
            "decoded_command": self.decoded_command,
            "decoded_fingerprint": self.decoded_fingerprint,
            "decoded_extras": dict(self.decoded_extras)
            if self.decoded_extras
            else None,
            "protocol": self.protocol,
            "code": self.code,
            "raw_timings": list(self.raw_timings),
            "frequency": self.frequency,
            "hit_count": self.hit_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "source": self.source,
            "alias": self.alias,
            "plucked_command_name": self.plucked_command_name,
            "repeat_count": self.repeat_count,
            "send_count": self.send_count,
            "tx_force_raw": self.tx_force_raw,
            "observed_repeat_count": self.observed_repeat_count,
            "echo_source": self.echo_source,
            "heard_by": list(self.heard_by) if self.heard_by is not None else None,
        }
        # Compute S/L pattern for Pronto signals (not stored, derived).
        if self.protocol and self.protocol.upper() == "PRONTO" and self.code:
            from .event_parser import EventParser

            sl = EventParser._pronto_sl_pattern(self.code)
            d["sl_pattern"] = sl
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnknownSignal:
        return cls(
            id=data.get("id") or _new_id(),
            fingerprint=data.get("fingerprint", ""),
            byte_hash=data.get("byte_hash"),
            decoded_protocol=data.get("decoded_protocol"),
            decoded_address=data.get("decoded_address"),
            decoded_command=data.get("decoded_command"),
            decoded_fingerprint=data.get("decoded_fingerprint"),
            decoded_extras=data.get("decoded_extras") or None,
            protocol=data.get("protocol"),
            code=data.get("code"),
            raw_timings=data.get("raw_timings") or [],
            frequency=int(data.get("frequency", DEFAULT_CARRIER_FREQUENCY)),
            hit_count=int(data.get("hit_count", 0)),
            first_seen=data.get("first_seen") or _now_iso(),
            last_seen=data.get("last_seen") or _now_iso(),
            source=data.get("source", "sniffed"),
            alias=data.get("alias", ""),
            plucked_command_name=data.get("plucked_command_name"),
            repeat_count=int(data.get("repeat_count", DEFAULT_REPEAT_COUNT)),
            send_count=int(data.get("send_count", 1)),
            tx_force_raw=bool(data.get("tx_force_raw", False)),
            observed_repeat_count=int(data.get("observed_repeat_count", 0)),
            echo_source=data.get("echo_source"),
            heard_by=(
                list(data["heard_by"]) if data.get("heard_by") is not None else None
            ),
        )


@dataclass
class UnknownDevice:
    """A group of unknown IR signals from the same physical remote/device."""

    id: str = field(default_factory=_new_id)
    fingerprint: str = ""
    protocol: str | None = None
    device_address: str | None = None
    label: str | None = None
    signals: list[UnknownSignal] = field(default_factory=list)
    hit_count: int = 0
    first_seen: str = field(default_factory=_now_iso)
    last_seen: str = field(default_factory=_now_iso)
    dismissed: bool = False
    source: Literal["sniffed", "manual", "plucked", "echo"] = "sniffed"
    # Manual display order within a tab (Sniffer / Clipper). Lower sorts
    # higher. New remotes are inserted below the minimum so they land on
    # top until the user drags them. Replaces the old hit_count sort.
    order: int = 0
    # Plucker source attribution (v0.5.0). Set on plucked blasters at create
    # time and immutable; None for sniffed/manual remotes. vendor_entity_id
    # is the mirrored HA remote entity; appliance is the user-typed grouping
    # that maps to the vendor service's device parameter.
    vendor_entity_id: str | None = None
    appliance: str | None = None
    # Identity-based promote linkage (v0.7.0, the GH promote-rename
    # anomaly): the HAIR device id this remote was promoted into. The
    # Sniffer's linked-device chip resolves it live by id, so renaming
    # either side never breaks the link. None = never promoted.
    promoted_to: str | None = None
    # Identity-based promote linkage, the REMOTE half (signpost 3,
    # Track 2 item 2 -- "USE as a Remote" from a Sniffer/Clipper/Plucker
    # catalog remote). Mirrors promoted_to exactly, keyed to a
    # TriggerRemote id instead of an IRDevice id. A single catalog
    # remote can carry BOTH links at once (promoted_to AND
    # promoted_to_remote both set) -- the "both-kinds" case
    # (mockup-handoff.md open item 1, both-kinds count-dot split
    # dropped 2026-08-15): one combined linked-count dot reads both
    # fields, kind-badging the rows in its popover instead of tracking
    # separate counts. None = never used as a remote.
    promoted_to_remote: str | None = None
    # Wig provenance for a matrix clip (Cold Cuts second half, owner
    # ruling CC5 2026-07-29): {"filename": ..., "cells_hash": ...}
    # stamped when a matrix wig CLIPs with its cells. The adopt
    # signpost resolves it live at list time -- filename first, then
    # cells hash over the closet's matrix wigs, so a renamed wig still
    # points home. None for every other remote.
    source_wig: dict[str, Any] | None = None

    def get_signal(
        self,
        fingerprint: str,
        byte_hash: str | None = None,
        decoded_fingerprint: str | None = None,
    ) -> UnknownSignal | None:
        """Find the signal an incoming capture belongs to (tiered, v0.5.8).

        The duplicate-guard matcher used by the capture pipeline and the
        Clipper paste guard. Matching is the tiered identity rule
        (decoded > byte_hash > S/L fingerprint, ``identity.SignalIdentity``):
        a boundary-protocol capture whose S/L fingerprint flipped (Sony)
        still lands on its existing row via byte_hash instead of minting a
        duplicate, while two genuinely different sub-threshold buttons
        (differing byte_hash) stay distinct.

        Scans in TIERED PASSES -- all signals at tier 1, then tier 2, then
        tier 3 -- not first-match-wins on one linear pass, so grouping does
        not depend on row insertion order (a decode-failed row sitting above
        its decoded sibling must not absorb a capture via tier 2 before the
        sibling's tier-1 match is considered).

        For per-signal operations use ``get_signal_by_id`` instead, since
        neither the fingerprint nor even the composite identity is unique
        across a remote's rows in legacy data.
        """
        from .identity import SignalIdentity

        incoming = SignalIdentity(decoded_fingerprint, byte_hash, fingerprint)
        best: UnknownSignal | None = None
        best_tier = 99
        for sig in self.signals:
            tier = SignalIdentity(
                sig.decoded_fingerprint, sig.byte_hash, sig.fingerprint
            ).match_tier(incoming)
            if tier is not None and tier < best_tier:
                best = sig
                best_tier = tier
                if tier == 1:
                    break
        return best

    def get_signal_by_id(self, signal_id: str) -> UnknownSignal | None:
        """Find a signal by its stable id (the per-operation identity)."""
        for sig in self.signals:
            if sig.id == signal_id:
                return sig
        return None

    def remove_signal_by_id(self, signal_id: str) -> bool:
        """Remove a signal by its stable id. Returns True if found."""
        for i, sig in enumerate(self.signals):
            if sig.id == signal_id:
                del self.signals[i]
                return True
        return False

    def reorder_signals(self, signal_ids: list[str]) -> None:
        """Reorder ``self.signals`` to match the given id list.

        The provided list must contain exactly the set of signal ids
        currently held by this remote -- no duplicates, no unknown, no
        missing. The drag-to-reorder UI always sends the complete list,
        so any divergence indicates a stale client and is rejected loudly
        rather than applied. Mirrors ``IRDevice.reorder_commands``.

        Keyed by id, not fingerprint: two signals on a remote can share a
        fingerprint (the byte-hash tiebreaker), so fingerprints are not a
        valid reorder key.

        Raises :class:`ValueError` on mismatch and leaves ``self.signals``
        untouched.
        """
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("Duplicate signal ids in reorder list")
        current = {s.id for s in self.signals}
        requested = set(signal_ids)
        if requested != current:
            missing = current - requested
            unknown = requested - current
            details: list[str] = []
            if missing:
                details.append(f"missing {sorted(missing)}")
            if unknown:
                details.append(f"unknown {sorted(unknown)}")
            raise ValueError(
                "Reorder list does not match current signals: "
                + ", ".join(details)
            )

        by_id = {s.id: s for s in self.signals}
        self.signals = [by_id[sid] for sid in signal_ids]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fingerprint": self.fingerprint,
            "protocol": self.protocol,
            "device_address": self.device_address,
            "label": self.label,
            "signals": [s.to_dict() for s in self.signals],
            "hit_count": self.hit_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "dismissed": self.dismissed,
            "source": self.source,
            "order": self.order,
            "vendor_entity_id": self.vendor_entity_id,
            "appliance": self.appliance,
            "promoted_to": self.promoted_to,
            "promoted_to_remote": self.promoted_to_remote,
            "source_wig": dict(self.source_wig) if self.source_wig else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnknownDevice:
        return cls(
            id=data.get("id") or _new_id(),
            fingerprint=data.get("fingerprint", ""),
            protocol=data.get("protocol"),
            device_address=data.get("device_address"),
            label=data.get("label"),
            signals=[
                UnknownSignal.from_dict(s)
                for s in (data.get("signals") or [])
            ],
            hit_count=int(data.get("hit_count", 0)),
            first_seen=data.get("first_seen") or _now_iso(),
            last_seen=data.get("last_seen") or _now_iso(),
            dismissed=bool(data.get("dismissed", False)),
            source=data.get("source", "sniffed"),
            order=int(data.get("order", 0)),
            vendor_entity_id=data.get("vendor_entity_id"),
            appliance=data.get("appliance"),
            promoted_to=data.get("promoted_to"),
            promoted_to_remote=data.get("promoted_to_remote"),
            source_wig=data.get("source_wig") or None,
        )
