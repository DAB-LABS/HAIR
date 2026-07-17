"""Data models for the HAIR integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from .const import (
    DEFAULT_CARRIER_FREQUENCY,
    DEFAULT_REPEAT_COUNT,
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "command_mapping": dict(self.command_mapping),
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
    capture_device_id: str | None = None
    capture_provider_type: CaptureProviderType = CaptureProviderType.ESPHOME
    commands: list[IRCommand] = field(default_factory=list)
    entity_config: EntityConfig = field(default_factory=EntityConfig)
    database_id: str | None = None
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
            capture_device_id=self.capture_device_id,
            capture_provider_type=self.capture_provider_type,
            commands=cloned_commands,
            entity_config=cloned_entity_config,
            database_id=self.database_id,
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
            "capture_device_id": self.capture_device_id,
            "capture_provider_type": str(self.capture_provider_type),
            "commands": [c.to_dict() for c in self.commands],
            "entity_config": self.entity_config.to_dict(),
            "database_id": self.database_id,
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
            capture_device_id=data.get("capture_device_id"),
            capture_provider_type=CaptureProviderType(
                data.get("capture_provider_type", CaptureProviderType.ESPHOME)
            ),
            commands=[
                IRCommand.from_dict(c) for c in (data.get("commands") or [])
            ],
            entity_config=EntityConfig.from_dict(data.get("entity_config") or {}),
            database_id=data.get("database_id"),
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
        )

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
    # ``tx_force_raw`` is a device-command concept and is NOT carried here.
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
    source: Literal["sniffed", "manual", "plucked"] = "sniffed"
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
            "observed_repeat_count": self.observed_repeat_count,
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
            observed_repeat_count=int(data.get("observed_repeat_count", 0)),
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
    source: Literal["sniffed", "manual", "plucked"] = "sniffed"
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
        )
