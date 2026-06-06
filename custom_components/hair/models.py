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

    fingerprint: str = ""
    protocol: str | None = None
    code: str | None = None
    raw_timings: list[int] = field(default_factory=list)
    frequency: int = DEFAULT_CARRIER_FREQUENCY
    hit_count: int = 0
    first_seen: str = field(default_factory=_now_iso)
    last_seen: str = field(default_factory=_now_iso)
    source: Literal["sniffed", "manual"] = "sniffed"
    alias: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "fingerprint": self.fingerprint,
            "protocol": self.protocol,
            "code": self.code,
            "raw_timings": list(self.raw_timings),
            "frequency": self.frequency,
            "hit_count": self.hit_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "source": self.source,
            "alias": self.alias,
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
            fingerprint=data.get("fingerprint", ""),
            protocol=data.get("protocol"),
            code=data.get("code"),
            raw_timings=data.get("raw_timings") or [],
            frequency=int(data.get("frequency", DEFAULT_CARRIER_FREQUENCY)),
            hit_count=int(data.get("hit_count", 0)),
            first_seen=data.get("first_seen") or _now_iso(),
            last_seen=data.get("last_seen") or _now_iso(),
            source=data.get("source", "sniffed"),
            alias=data.get("alias", ""),
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
    source: Literal["sniffed", "manual"] = "sniffed"

    def get_signal(self, fingerprint: str) -> UnknownSignal | None:
        """Find a signal by fingerprint."""
        for sig in self.signals:
            if sig.fingerprint == fingerprint:
                return sig
        return None

    def remove_signal(self, fingerprint: str) -> bool:
        """Remove a signal by fingerprint. Returns True if found."""
        for i, sig in enumerate(self.signals):
            if sig.fingerprint == fingerprint:
                del self.signals[i]
                return True
        return False

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
        )
