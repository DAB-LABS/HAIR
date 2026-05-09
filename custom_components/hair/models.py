"""Data models for the HAIR integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
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
    return datetime.now(timezone.utc).isoformat()


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
    emitter_entity_id: str = ""
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": str(self.device_type),
            "manufacturer": self.manufacturer,
            "model": self.model,
            "emitter_entity_id": self.emitter_entity_id,
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
        return cls(
            id=data.get("id") or _new_id(),
            name=data.get("name", ""),
            device_type=DeviceType(data.get("device_type", DeviceType.OTHER)),
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            emitter_entity_id=data.get("emitter_entity_id", ""),
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
        for a, b in zip(self.raw_timings[:length], other.raw_timings[:length]):
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "protocol": self.protocol,
            "code": self.code,
            "raw_timings": list(self.raw_timings),
            "frequency": self.frequency,
            "hit_count": self.hit_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

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
        )


@dataclass
class UnknownDevice:
    """A group of unknown IR signals from the same physical remote/device."""

    id: str = field(default_factory=_new_id)
    fingerprint: str = ""
    protocol: str | None = None
    device_address: str | None = None
    signals: list[UnknownSignal] = field(default_factory=list)
    hit_count: int = 0
    first_seen: str = field(default_factory=_now_iso)
    last_seen: str = field(default_factory=_now_iso)
    dismissed: bool = False

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
            "signals": [s.to_dict() for s in self.signals],
            "hit_count": self.hit_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "dismissed": self.dismissed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnknownDevice:
        return cls(
            id=data.get("id") or _new_id(),
            fingerprint=data.get("fingerprint", ""),
            protocol=data.get("protocol"),
            device_address=data.get("device_address"),
            signals=[
                UnknownSignal.from_dict(s)
                for s in (data.get("signals") or [])
            ],
            hit_count=int(data.get("hit_count", 0)),
            first_seen=data.get("first_seen") or _now_iso(),
            last_seen=data.get("last_seen") or _now_iso(),
            dismissed=bool(data.get("dismissed", False)),
        )
