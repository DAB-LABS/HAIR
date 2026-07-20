"""Protocol decode registry: decoded identity for captured IR signals.

v0.4.0 decoded NEC through Home Assistant's bundled ``infrared-protocols``
library. v0.6.0 generalizes that into a registry (multi-protocol decoder
plan, Section 4.1) fed from two sources, probed in this order per
protocol:

1. **Upstream**: the bundled ``infrared_protocols`` class, used whenever
   it ships a ``from_raw_timings`` decoder (feature-detected, never
   version-pinned). What upstream can decode, upstream decodes.
2. **Local**: HAIR's own decoder in ``custom_components/hair/decoders/``,
   the polyfill used until the upstream library gains that protocol's
   decoder (local-first strategy, plan Section 6). Local classes are
   upstream-shaped, and their encoders are asserted byte-identical to
   upstream's, so which source serves a protocol is invisible to stored
   identity and to transmit.

A protocol whose class cannot be imported from either source is skipped
with a DEBUG log -- silent-skip is correct for "user's HA ships an older
library", wrong for a typo'd class name, and the log plus the
``registered_protocols()`` diagnostics listing tell the two apart.

The decoded fingerprint is formatted in exactly one place
(:func:`format_fingerprint`); nothing outside this module may assemble
one by hand. The NEC format is byte-identical to every release since
v0.4.0, so existing stored identities keep matching with zero migration.
Toggle bits (RC-5, Marantz) are press state, not identity, and are
excluded from the fingerprint; Sharp's extension bit and Marantz's
extension field are identity and are folded in via a per-protocol
suffix. Protocol variants that change the frame's bit count (SIRC-12/15/20,
Kaseikyo/Symphony widths) are folded into the protocol label itself, so
the ``(protocol, address, command)`` triple plus the label is always a
complete identity.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .const import DECODED_FINGERPRINT_FORMAT, DECODED_PROTOCOL_NEC

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Identity container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecodedIdentity:
    """Rich decode result: the four decoded_* fields plus state extras."""

    protocol: str
    address: int
    command: int
    fingerprint: str
    extras: dict[str, int] | None
    source: str  # "upstream" | "local"


# ---------------------------------------------------------------------------
# Protocol specs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProtocolSpec:
    """One registered protocol: its class, its adapters, its tier."""

    key: str  # stable registry key, e.g. "sony"
    command_cls: type
    source: str  # "upstream" | "local"
    tx_rebuild: bool
    # Adapters bridging the class's fields and HAIR's identity triple.
    extract: Any  # Callable[[command], (label, address, command, extras|None)]
    construct: Any  # Callable[[label, address, command, extras|None], command|None]
    labels: tuple[str, ...] = field(default=())  # labels this spec serves
    # Optional recovery hooks (v0.6.1, NEC only today).
    # ``seek``: pre-pass trimming leading junk before the decode attempt.
    # ``salvage``: lenient re-read tried ONLY when the strict decoder
    # rejects; must gate on the protocol's own integrity check and
    # return (address, command) or None. Both apply to this spec's
    # attempt alone; later specs in the probe order see the original
    # capture untouched.
    seek: Any = None  # Callable[[list[int]], list[int]] | None
    salvage: Any = None  # Callable[[list[int]], tuple[int, int] | None] | None


def _import_class(module_name: str, class_name: str) -> type | None:
    """Import a command class, returning None when unavailable."""
    try:
        module = __import__(module_name, fromlist=[class_name])
    except ImportError:
        return None
    return getattr(module, class_name, None)


def _resolve_class(
    protocol_key: str, upstream_module: str | None, class_name: str,
    local_module: str | None,
) -> tuple[type, str] | None:
    """Feature-detect the decoding class for a protocol.

    Upstream wins when it can decode; the local polyfill covers the gap;
    None (with a DEBUG log) when neither source provides the class.
    """
    if upstream_module is not None:
        cls = _import_class(upstream_module, class_name)
        if cls is not None and hasattr(cls, "from_raw_timings"):
            return (cls, "upstream")
    if local_module is not None:
        cls = _import_class(local_module, class_name)
        if cls is not None and hasattr(cls, "from_raw_timings"):
            return (cls, "local")
    _LOGGER.debug(
        "protocol %s not registered: no decoding class %s available "
        "(upstream=%s, local=%s)",
        protocol_key, class_name, upstream_module, local_module,
    )
    return None


# --- per-protocol adapters --------------------------------------------------

_SONY_ADDRESS_BITS_TO_TOTAL = {5: 12, 8: 15, 13: 20}
_SONY_TOTAL_TO_ADDRESS_BITS = {12: 5, 15: 8, 20: 13}


def _extract_nec(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    return (DECODED_PROTOCOL_NEC, int(cmd.address), int(cmd.command), None)


def _construct_nec(cls: type, label: str, address: int, command: int,
                   extras: Any) -> Any:
    return cls(address=address, command=command)


def _extract_sony(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    total = _SONY_ADDRESS_BITS_TO_TOTAL[int(cmd.address_bits)]
    return (f"SONY{total}", int(cmd.address), int(cmd.command), None)


def _construct_sony(cls: type, label: str, address: int, command: int,
                    extras: Any) -> Any:
    try:
        total_bits = int(label[4:])
    except ValueError:
        return None
    address_bits = _SONY_TOTAL_TO_ADDRESS_BITS.get(total_bits)
    if address_bits is None:
        return None
    return cls(address=address, address_bits=address_bits, command=command)


def _extract_samsung(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    return ("SAMSUNG32", int(cmd.address), int(cmd.command), None)


def _construct_samsung(cls: type, label: str, address: int, command: int,
                       extras: Any) -> Any:
    return cls(address=address, command=command)


def _extract_rc5(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    return ("RC5", int(cmd.address), int(cmd.command), {"toggle": int(cmd.toggle)})


def _construct_rc5(cls: type, label: str, address: int, command: int,
                   extras: Any) -> Any:
    toggle = int((extras or {}).get("toggle", 0))
    return cls(address=address, command=command, toggle=toggle & 1)


def _extract_sharp(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    extension = int(cmd.extension)
    return ("SHARP", int(cmd.address), int(cmd.command),
            {"extension": extension} if extension else None)


def _construct_sharp(cls: type, label: str, address: int, command: int,
                     extras: Any) -> Any:
    extension = int((extras or {}).get("extension", 0))
    return cls(address=address, command=command, extension=extension & 1)


def _extract_nokia32(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    # device/subdevice pack into the 16-bit box address; function is the
    # command; X (system/OEM) is identity and rides in the suffix; toggle
    # is press state, carried for TX but kept out of the fingerprint.
    address = (int(cmd.device) << 8) | int(cmd.subdevice)
    return ("NOKIA32", address, int(cmd.function),
            {"extension": int(cmd.extension), "toggle": int(cmd.toggle)})


def _construct_nokia32(cls: type, label: str, address: int, command: int,
                       extras: Any) -> Any:
    bag = extras or {}
    return cls(
        device=(address >> 8) & 0xFF,
        subdevice=address & 0xFF,
        function=command,
        extension=int(bag.get("extension", 0)) & 0x7F,
        toggle=int(bag.get("toggle", 0)) & 1,
    )


def _extract_marantz(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    return ("MARANTZ", int(cmd.address), int(cmd.command),
            {"extension": int(cmd.extension), "toggle": int(cmd.toggle)})


def _construct_marantz(cls: type, label: str, address: int, command: int,
                       extras: Any) -> Any:
    bag = extras or {}
    return cls(
        address=address,
        command=command,
        extension=int(bag.get("extension", 0)),
        toggle=int(bag.get("toggle", 0)) & 1,
    )


def _extract_kaseikyo(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    payload = bytes(cmd.data)
    total_bits = 8 * (2 + len(payload))
    return (
        f"KASEIKYO{total_bits}",
        int(cmd.address),
        int.from_bytes(payload, "big"),
        None,
    )


def _construct_kaseikyo(cls: type, label: str, address: int, command: int,
                        extras: Any) -> Any:
    try:
        total_bits = int(label[8:])
    except ValueError:
        return None
    payload_len = total_bits // 8 - 2
    if payload_len < 1:
        return None
    return cls(address=address, data=command.to_bytes(payload_len, "big"))


def _extract_symphony(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    return (f"SYMPHONY{int(cmd.nbits)}", 0, int(cmd.data), None)


def _construct_symphony(cls: type, label: str, address: int, command: int,
                        extras: Any) -> Any:
    try:
        nbits = int(label[8:])
    except ValueError:
        return None
    return cls(data=command, nbits=nbits)


def _extract_dyson(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    # Identity = device + function; the mod-4 rolling counter is press
    # state (the fan rejects a reused value), carried for TX and
    # advanced after every send like an RC-5 toggle.
    return ("DYSON", int(cmd.device), int(cmd.function),
            {"counter": int(cmd.counter)})


def _construct_dyson(cls: type, label: str, address: int, command: int,
                     extras: Any) -> Any:
    counter = int((extras or {}).get("counter", 0))
    return cls(device=address, function=command, counter=counter & 0x3)


def _extract_geac(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    return ("GEAC", int(cmd.address), int(cmd.command), None)


def _construct_geac(cls: type, label: str, address: int, command: int,
                    extras: Any) -> Any:
    # Identity-only tier: GE-AC transmit always replays the captured raw
    # (plan finding B6) -- decoded identity is for matching only.
    return None


# --- fingerprint suffixes (identity-bearing extras) --------------------------

# Per-protocol identity suffix appended to the base fingerprint. Toggle
# never appears here: it flips per press and would split one button into
# two identities.
def _identity_suffix(protocol: str, extras: Mapping[str, int] | None) -> str:
    if not extras:
        return ""
    if protocol == "SHARP" and extras.get("extension"):
        return ":x1"
    if protocol == "MARANTZ":
        return f":x{int(extras.get('extension', 0)):02x}"
    if protocol == "NOKIA32":
        # X (system/OEM) separates Foxtel/Sky/Mediamaster on one protocol.
        return f":x{int(extras.get('extension', 0)):02x}"
    return ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# (key, upstream module, class name, local module, tx_rebuild, extract,
#  construct, label prefix) -- probe order is registration order: strict
# checksum-validated protocols first, checksum-free last, and specific
# formats ahead of their generic parents (plan finding B6).
_REGISTRATIONS: tuple[tuple, ...] = (
    ("nec", "infrared_protocols.commands.nec", "NECCommand",
     None, True, _extract_nec, _construct_nec, (DECODED_PROTOCOL_NEC,)),
    ("samsung32", "infrared_protocols.commands.samsung", "Samsung32Command",
     "custom_components.hair.decoders.samsung", True,
     _extract_samsung, _construct_samsung, ("SAMSUNG32",)),
    ("sony", "infrared_protocols.commands.sony", "SonyCommand",
     "custom_components.hair.decoders.sony", True,
     _extract_sony, _construct_sony, ("SONY12", "SONY15", "SONY20")),
    ("sharp", "infrared_protocols.commands.sharp", "SharpCommand",
     "custom_components.hair.decoders.sharp", True,
     _extract_sharp, _construct_sharp, ("SHARP",)),
    # Upstream ships no Nokia32 yet, so this resolves to the local decoder;
    # if the library ever adds Nokia32Command with from_raw_timings, HAIR
    # defers to it automatically (rohrsh's branch, discussion #70).
    ("nokia32", "infrared_protocols.commands.nokia32", "Nokia32Command",
     "custom_components.hair.decoders.nokia32", True,
     _extract_nokia32, _construct_nokia32, ("NOKIA32",)),
    ("marantz", "infrared_protocols.commands.marantz_extended",
     "MarantzExtendedCommand",
     "custom_components.hair.decoders.marantz_extended", True,
     _extract_marantz, _construct_marantz, ("MARANTZ",)),
    ("rc5", "infrared_protocols.commands.rc5", "RC5Command",
     "custom_components.hair.decoders.rc5", True,
     _extract_rc5, _construct_rc5, ("RC5",)),
    ("kaseikyo", "infrared_protocols.commands.kaseikyo", "KaseikyoCommand",
     "custom_components.hair.decoders.kaseikyo", True,
     _extract_kaseikyo, _construct_kaseikyo, ("KASEIKYO",)),
    ("geac", "infrared_protocols.commands.general_electric", "GEACCommand",
     None, False, _extract_geac, _construct_geac, ("GEAC",)),
    # Upstream's DysonCoolCommand (7.3.0+) is encode-only with the
    # rolling counter frozen into enum constants, so no upstream
    # fallback is registered -- the local class serves both directions
    # (revisit if upstream ever grows a real decoder). Checksum-free
    # 15-bit protocol, so it probes in the checksum-free
    # tail -- ahead of Symphony only because Symphony's short frames
    # are the loosest match in the registry and must stay last.
    ("dyson", None, "DysonCommand",
     "custom_components.hair.decoders.dyson", True,
     _extract_dyson, _construct_dyson, ("DYSON",)),
    ("symphony", None, "SymphonyCommand",
     "custom_components.hair.decoders.symphony", True,
     _extract_symphony, _construct_symphony, ("SYMPHONY",)),
)

_registry: list[ProtocolSpec] | None = None


def _build_registry() -> list[ProtocolSpec]:
    """Build the ordered spec list by feature-detecting each protocol."""
    specs: list[ProtocolSpec] = []
    for (key, upstream_module, class_name, local_module, tx_rebuild,
         extract, construct, labels) in _REGISTRATIONS:
        resolved = _resolve_class(key, upstream_module, class_name, local_module)
        if resolved is None:
            continue
        cls, source = resolved
        seek = salvage = None
        if key == "nec":
            # v0.6.1 recovery hooks: leader-seek admits repeat-prefix
            # captures to the strict decoder; checksum salvage rescues
            # single-pulse dead-zone jitter (blalor's Previous Track).
            from .decoders import nec_recovery

            seek = nec_recovery.seek_main_leader
            salvage = nec_recovery.salvage_decode
        specs.append(
            ProtocolSpec(
                key=key,
                command_cls=cls,
                source=source,
                tx_rebuild=tx_rebuild,
                extract=extract,
                construct=construct,
                labels=labels,
                seek=seek,
                salvage=salvage,
            )
        )
    return specs


def _ensure_registry() -> list[ProtocolSpec]:
    """Lazily build the registry (import-time builds hurt the test matrix)."""
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def _reset_registry_for_tests() -> None:
    """Drop the cached registry so tests can rebuild under monkeypatching."""
    global _registry
    _registry = None


def get_spec(protocol: str | None) -> ProtocolSpec | None:
    """Resolve a decoded-protocol label to its registered spec, or None.

    Labels either match a spec exactly ("NEC", "RC5", "SHARP") or start
    with the spec's registered prefix carrying a bit-count variant
    ("SONY15", "KASEIKYO48", "SYMPHONY12").
    """
    if not protocol:
        return None
    for spec in _ensure_registry():
        for label in spec.labels:
            if protocol == label or (
                protocol.startswith(label) and protocol[len(label):].isdigit()
            ):
                return spec
    return None


def registered_protocols() -> list[dict[str, Any]]:
    """Describe the live registry for diagnostics: key, source, tier."""
    return [
        {
            "protocol": spec.key,
            "source": spec.source,
            "tx_rebuild": spec.tx_rebuild,
        }
        for spec in _ensure_registry()
    ]


# ---------------------------------------------------------------------------
# Public decode / format API
# ---------------------------------------------------------------------------


def library_available() -> bool:
    """Return True if the upstream NEC decoder is importable and usable."""
    cls = _import_class("infrared_protocols.commands.nec", "NECCommand")
    return cls is not None and hasattr(cls, "from_raw_timings")


def format_fingerprint(
    protocol: str,
    address: int,
    command: int,
    extras: Mapping[str, int] | None = None,
) -> str:
    """Format the decoded fingerprint -- the single place that does.

    The base template is byte-identical to the v0.4.0 NEC format;
    identity-bearing extras (Sharp extension, Marantz extension) append a
    per-protocol suffix. Toggle state never participates.
    """
    base = DECODED_FINGERPRINT_FORMAT.format(
        protocol=protocol, address=address, command=command
    )
    return base + _identity_suffix(protocol, extras)


def try_decode_identity(raw_timings: list[int] | None) -> DecodedIdentity | None:
    """Decode raw timings into a :class:`DecodedIdentity`, or ``None``.

    Probes the registry in order; the first protocol whose decoder
    accepts the capture wins. Decoders validate their protocols'
    checksums and structure, so a match is a real identification, not a
    guess. Never raises into the capture hot path.
    """
    if not raw_timings:
        return None
    for spec in _ensure_registry():
        attempt = list(raw_timings)
        if spec.seek is not None:
            try:
                attempt = spec.seek(attempt)
            except Exception:  # a broken seek must not cost the strict path
                attempt = list(raw_timings)
        try:
            cmd = spec.command_cls.from_raw_timings(attempt)
        except Exception:  # never break capture on a malformed-input error
            cmd = None
        if cmd is None:
            if spec.salvage is not None:
                try:
                    salvaged = spec.salvage(attempt)
                except Exception:
                    salvaged = None
                if salvaged is not None:
                    address, command = salvaged
                    protocol = spec.labels[0]
                    return DecodedIdentity(
                        protocol=protocol,
                        address=address,
                        command=command,
                        fingerprint=format_fingerprint(
                            protocol, address, command, None
                        ),
                        extras=None,
                        source=spec.source,
                    )
            continue
        try:
            protocol, address, command, extras = spec.extract(cmd)
        except (AttributeError, TypeError, ValueError):
            continue
        return DecodedIdentity(
            protocol=protocol,
            address=address,
            command=command,
            fingerprint=format_fingerprint(protocol, address, command, extras),
            extras=extras,
            source=spec.source,
        )
    return None


def identity_from_command(command: Any) -> DecodedIdentity | None:
    """Derive decoded identity from an existing Command instance.

    Used by the code library / Plucker surfaces that already hold a
    library (or local) Command object rather than raw timings. Specs are
    matched by class name so an upstream encode-only instance (e.g. a
    pluckable built from the upstream SonyCommand) still resolves to the
    protocol's registered spec and gets the same label and fingerprint a
    captured signal would.
    """
    if command is None:
        return None
    name = type(command).__name__
    for spec in _ensure_registry():
        if name != spec.command_cls.__name__ and not isinstance(
            command, spec.command_cls
        ):
            continue
        try:
            protocol, address, cmd_val, extras = spec.extract(command)
        except (AttributeError, TypeError, ValueError, KeyError):
            return None
        return DecodedIdentity(
            protocol=protocol,
            address=address,
            command=cmd_val,
            fingerprint=format_fingerprint(protocol, address, cmd_val, extras),
            extras=extras,
            source=spec.source,
        )
    return None


def try_decode(raw_timings: list[int] | None) -> tuple[str, int, int] | None:
    """Decode raw IR timings to ``(protocol, address, command)`` or ``None``.

    Kept for callers (and tests) that predate the richer
    :func:`try_decode_identity`; identical probe behavior.
    """
    identity = try_decode_identity(raw_timings)
    if identity is None:
        return None
    return (identity.protocol, identity.address, identity.command)


def decode_to_fields(
    raw_timings: list[int] | None,
) -> tuple[str | None, int | None, int | None, str | None]:
    """Decode raw timings into the four ``decoded_*`` fields, or all-None.

    Wraps :func:`try_decode_identity` and keeps the original 4-tuple
    contract (plan finding B3: callers that need extras migrate to
    ``try_decode_identity`` deliberately, one at a time). Never raises.
    """
    identity = try_decode_identity(raw_timings)
    if identity is None:
        return (None, None, None, None)
    return (
        identity.protocol,
        identity.address,
        identity.command,
        identity.fingerprint,
    )


def build_protocol_command(
    protocol: str | None,
    address: int | None,
    command: int | None,
    *,
    extras: Mapping[str, int] | None = None,
) -> Any | None:
    """Build a protocol-native Command from decoded fields, or ``None``.

    Returns None when the protocol is unregistered, the spec is
    identity-only (``tx_rebuild=False``), a field is missing, or the
    class rejects the values -- callers fall back to Pronto/raw replay.
    """
    if protocol is None or address is None or command is None:
        return None
    spec = get_spec(protocol)
    if spec is None or not spec.tx_rebuild:
        return None
    try:
        return spec.construct(spec.command_cls, protocol, address, command, extras)
    except (TypeError, ValueError, OverflowError):
        return None
