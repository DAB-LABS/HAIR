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
    # DOES THIS DECODE EXPLAIN THE WHOLE CAPTURE? (GH #134)
    #
    # An air conditioner state blob is a long opaque payload, and a
    # decoder looking for a short addressed frame can find one inside it
    # by coincidence -- the reported case was a KASEIKYO48 match on a
    # climate state, re-encoded into a meaningless 99-timing frame. The
    # two adversarial reviews settled that re-encoding the identity and
    # comparing it to the capture fails honest captures and passes this
    # exact false class, and that the discriminator that works is frame
    # coverage: a true decode explains every frame of its capture,
    # directly or through repeat voting, and a false one explains a
    # fraction.
    #
    # All three carry DEFAULTS on purpose. Every existing construction
    # site stays valid, and ``covers_capture`` of None means the
    # accounting was not computed rather than that it came out badly.
    # None is TRUSTED: an upstream decoder whose vote count this repo
    # cannot see must not be treated as a false decode.
    frames_total: int = 0
    frames_explained: int = 0
    covers_capture: bool | None = None


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


def _extract_rc6(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    # Mode and customer/OEM are IDENTITY -- two remotes can share an
    # address and command and be told apart only by them -- so they ride
    # the fingerprint suffix. Toggle is press state: in mode 0 it is the
    # trailer bit, in mode 6 it is the first payload bit (the trailer is
    # spent on the submode flag there), but either way it flips per press
    # and stays out of the fingerprint.
    extras: dict[str, int] = {"mode": int(cmd.mode), "toggle": int(cmd.toggle)}
    if cmd.customer is not None:
        extras["customer"] = int(cmd.customer)
    return ("RC6", int(cmd.address), int(cmd.command), extras)


def _construct_rc6(cls: type, label: str, address: int, command: int,
                   extras: Any) -> Any:
    bag = extras or {}
    customer = bag.get("customer")
    return cls(
        address=address,
        command=command,
        toggle=int(bag.get("toggle", 0)) & 1,
        mode=int(bag.get("mode", 0)),
        customer=None if customer is None else int(customer),
    )


def _extract_sharp(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    extension = int(cmd.extension)
    return ("SHARP", int(cmd.address), int(cmd.command),
            {"extension": extension} if extension else None)


def _construct_sharp(cls: type, label: str, address: int, command: int,
                     extras: Any) -> Any:
    extension = int((extras or {}).get("extension", 0))
    return cls(address=address, command=command, extension=extension & 1)


def _extract_rca(cmd: Any) -> tuple[str, int, int, dict[str, int] | None]:
    # Identity = device + function. RCA has no toggle, no counter and no
    # repeat code, so there are no extras at all: the frame count of a
    # held button is press length, and folding it into identity is
    # precisely the bug this decoder exists to cure.
    return ("RCA", int(cmd.device), int(cmd.function), None)


def _construct_rca(cls: type, label: str, address: int, command: int,
                   extras: Any) -> Any:
    return cls(device=address, function=command)


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
    if protocol == "RC6":
        # Mode picks the frame shape; the customer/OEM field separates
        # Media Center from a VU+ box from any other mode 6 vendor that
        # happens to reuse an address and command. Mode 0 has no
        # customer field and gets the mode alone.
        suffix = f":m{int(extras.get('mode', 0)):x}"
        customer = extras.get("customer")
        if customer is not None:
            suffix += f":c{int(customer):04x}"
        return suffix
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
    # RCA carries a strict whole-payload checksum (the second twelve bits
    # are the exact complement of the first), so it belongs in the strict
    # tier rather than the checksum-free tail. Upstream ships no rca
    # module today; the path is registered so a future library gains it
    # automatically by feature detection, never by a version pin.
    ("rca", "infrared_protocols.commands.rca", "RCACommand",
     "custom_components.hair.decoders.rca", True,
     _extract_rca, _construct_rca, ("RCA",)),
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
    # RC-6 probes AHEAD of RC-5: it carries a 6t/2t leader and a
    # structured header where RC-5 has neither, so it is the more
    # specific match of the two Manchester formats -- the same
    # specific-before-generic reasoning that puts Marantz ahead of RC-5.
    # Upstream ships no rc6 module today, so this resolves local; if the
    # library ever adds RC6Command with from_raw_timings, HAIR defers to
    # it automatically.
    ("rc6", "infrared_protocols.commands.rc6", "RC6Command",
     "custom_components.hair.decoders.rc6", True,
     _extract_rc6, _construct_rc6, ("RC6",)),
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


# WHAT THE STORE CAN HOLD (0.10.1 item 1). Home Assistant serializes its
# stores through a writer that refuses an integer outside the signed
# 64-bit range, and it refuses the WHOLE payload, not the one field: on
# the bench a capture that decoded to a ~1.5e23 command stopped every
# Sniffer save for eighty minutes, until the 200-signal cap happened to
# evict the offending row.
#
# A value that large is not a real IR identity anyway -- the widest
# protocol HAIR decodes is 48 bits of payload -- so this is not a
# storage workaround dressed as a decode rule. It is the decoder saying
# it produced something that cannot be true, which is exactly when the
# raw timings should be left to speak for themselves. Refuse, do not
# clamp: a truncated identity is a WRONG identity, and a wrong identity
# would match the wrong command forever, where an absent one just means
# the signal stays undecoded and matches on the raw tiers as it always
# did.
_MAX_DECODED_FIELD = 1 << 63


def _storable(
    label: str,
    address: Any,
    command: Any,
    extras: Mapping[str, int] | None,
) -> bool:
    """True when every decoded field is an int the store can hold.

    DEBUG, not WARNING: this is one capture out of a stream, the signal
    is kept undecoded rather than lost, and a noisy remote could
    otherwise produce the same line hundreds of times.
    """
    fields: list[tuple[str, Any]] = [("address", address), ("command", command)]
    fields.extend((key, value) for key, value in (extras or {}).items())
    for name, value in fields:
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            _LOGGER.debug(
                "Decoder %s produced a non-integer field (%s=%r); "
                "storing undecoded", label, name, value,
            )
            return False
        if not 0 <= value < _MAX_DECODED_FIELD:
            _LOGGER.debug(
                "Decoder %s produced an out-of-range field (%s=%r); "
                "storing undecoded", label, name, value,
            )
            return False
    return True


# How far over the kept frames a discarded one may be and still be
# forgiven as the same frame seen badly. Half again on each axis.
#
# THE NUMBER CAME FROM THE CORPUS, not from taste. The Dreo Speed Down
# capture is the boundary case the review named: four frames of one
# button, two decoded and two not, all four ~18.8ms long, the discarded
# pair carrying 13 and 14 marks against the winners' 12 because
# receiver jitter split single pulses into extra edges. It has to pass.
# A 120-edge air conditioner state frame beside a real one is 60 marks
# and roughly five times the duration. It has to fail. Anything from
# about 1.2 to about 2.5 separates those two; half again sits in the
# middle of that window on both axes.
_SHAPE_SLACK = 1.5


def _mark_count(frame: list[int]) -> int:
    """How many marks are in this frame -- half of its shape."""
    return sum(1 for value in frame if value > 0)


def _duration(frame: list[int]) -> int:
    """How long this frame is in microseconds -- the other half."""
    return sum(abs(value) for value in frame)


def _winning_mark_count(frames: list[list[int]]) -> int:
    """The mark count of the frame shape the decoder most likely won on.

    The decoder reports HOW MANY frames it explained, not WHICH, so the
    winning shape is inferred: the most common mark count wins, and a
    tie goes to the SMALLER one. The tie-break is the conservative
    direction -- it forgives less -- and it is what keeps a capture of
    two real frames beside two junk frames from electing the junk.
    """
    if not frames:
        return 0
    counts: dict[int, int] = {}
    for frame in frames:
        marks = _mark_count(frame)
        counts[marks] = counts.get(marks, 0) + 1
    best = max(counts.values())
    return min(marks for marks, seen in counts.items() if seen == best)


def _same_shape(frame: list[int], marks: int, shortest: int) -> bool:
    """Is this discarded frame the winning frame seen badly?

    Two measures, because one of them alone gets the corpus wrong.
    Edge count catches a dense payload; duration catches a long one,
    and duration is the one that matters for the real boundary case,
    where jitter added two marks to a frame of exactly the right
    length. A truncated tail is SHORTER on both and passes, which is
    what it should do: a cut frame is the same frame, cut.
    """
    return (
        _mark_count(frame) <= marks * _SHAPE_SLACK
        and _duration(frame) <= shortest * _SHAPE_SLACK
    )


def _coverage(
    spec: ProtocolSpec, cmd: Any, attempt: list[int]
) -> tuple[int, int, bool | None]:
    """``(frames_total, frames_explained, covers_capture)`` for a win.

    THE RULING SET, in order (GH #134 review 2):

    1. Identity-only tiers are skipped entirely. GE-AC transmit always
       replays the captured raw, so there is nothing for a verdict to
       protect and computing one would only invite somebody to persist
       it.
    2. A decoder that declares no frame gap, or that returns an
       instance carrying no census, has accounting this repo cannot
       verify. That is the upstream NEC strict path today. Unknown, not
       false.
    3. The repeat-voting carve-out, BOUNDED. A voting decoder reaches
       its verdict by discarding frames that disagree, and a vendor
       preamble, a truncated tail and one jittered frame are exactly
       that. Those are forgiven -- but only when each unexplained frame
       is the same SIZE as the ones the decoder kept, on edge count and
       on duration both. A truncation or a preamble is at most that
       size; a 120-edge state frame sitting beside two good ones is
       several times it, and forgiving that is how the false class
       would walk straight back in.
    4. Otherwise the base rule: every frame explained, or the decode
       does not cover the capture.
    """
    if not spec.tx_rebuild:
        return (0, 0, None)
    gap = getattr(spec.command_cls, "FRAME_GAP_US", None)
    explained = getattr(cmd, "frames_explained", None)
    if not gap or explained is None:
        return (0, 0, None)

    from .decoders import split_frames

    frames = split_frames(attempt, int(gap))
    total = len(frames)
    explained = int(explained)
    if total == 0:
        return (0, explained, None)
    if explained >= total:
        return (total, explained, True)

    if int(getattr(spec.command_cls, "MIN_FRAME_VOTES", 1)) >= 2:
        marks = _winning_mark_count(frames)
        shortest = min(_duration(f) for f in frames)
        if all(_same_shape(f, marks, shortest) for f in frames):
            return (total, explained, True)
    return (total, explained, False)


def _salvage_coverage(spec: ProtocolSpec, attempt: list[int]) -> tuple[
    int, int, bool | None
]:
    """Coverage for an identity that came out of the salvage hook.

    WITHIN-FRAME ONLY. The salvage exists because one pulse of one
    frame was jittered into the dead zone, and that frame is read and
    explained. What it does NOT license is the rest of the capture:
    every other frame still counts, so a salvage that rescues one frame
    of six covers nothing.

    The seek-trimmed prefix never reaches here -- ``attempt`` is already
    the sliced capture -- which is the exemption stated as an absence.
    """
    if spec.key != "nec":
        return (0, 0, None)
    from .decoders import nec_recovery

    total, explained = nec_recovery.salvaged_frame_census(attempt)
    if total == 0:
        return (0, 0, None)
    return (total, explained, explained >= total)


def _identify(
    raw_timings: list[int] | None,
) -> tuple[DecodedIdentity, ProtocolSpec] | None:
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
                    if not _storable(protocol, address, command, None):
                        continue
                    total, explained, covers = _salvage_coverage(spec, attempt)
                    return DecodedIdentity(
                        protocol=protocol,
                        address=address,
                        command=command,
                        fingerprint=format_fingerprint(
                            protocol, address, command, None
                        ),
                        extras=None,
                        source=spec.source,
                        frames_total=total,
                        frames_explained=explained,
                        covers_capture=covers,
                    ), spec
            continue
        try:
            protocol, address, command, extras = spec.extract(cmd)
        except (AttributeError, TypeError, ValueError):
            continue
        # A decoder that produced something the store cannot hold has
        # not identified this signal; try the next spec, and if none is
        # left the signal stays undecoded (0.10.1 item 1).
        if not _storable(protocol, address, command, extras):
            continue
        total, explained, covers = _coverage(spec, cmd, attempt)
        return DecodedIdentity(
            protocol=protocol,
            address=address,
            command=command,
            fingerprint=format_fingerprint(protocol, address, command, extras),
            extras=extras,
            source=spec.source,
            frames_total=total,
            frames_explained=explained,
            covers_capture=covers,
        ), spec
    return None


def try_decode_identity(
    raw_timings: list[int] | None,
) -> DecodedIdentity | None:
    """The decoded identity for a capture, or None.

    The public probe. Everything about HOW the answer was reached lives
    in ``_identify``; callers that only want the identity get it here
    and stay unaffected by which spec produced it.
    """
    found = _identify(raw_timings)
    return None if found is None else found[0]


def decode_is_repeat_voted(raw_timings: list[int] | None) -> bool:
    """Did a REPEAT-VOTING decoder accept this whole capture?

    A protocol with no checksum has one piece of integrity evidence:
    the same frame arriving more than once and saying the same thing.
    Its decoder therefore demands a minimum number of agreeing frames
    before it accepts a capture at all, and it reaches that verdict by
    discarding the frames that disagree, which is exactly what a vendor
    preamble, a truncated tail, or one frame mangled by jitter is.

    That matters to a protocol-blind check that doubts a capture
    BECAUSE its raw frames differ. Where a voting decoder has accepted
    the whole capture, those differences are the ones it already looked
    at and ruled on, and doubting them again is re-asking a question
    that has an answer.

    Detected, never listed: any decoder declaring MIN_FRAME_VOTES of
    two or more qualifies, so a protocol added later arrives with this
    behaviour instead of needing to be remembered here. Today that is
    Symphony alone.
    """
    found = _identify(raw_timings)
    if found is None:
        return False
    return int(getattr(found[1].command_cls, "MIN_FRAME_VOTES", 1)) >= 2


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
        if not _storable(protocol, address, cmd_val, extras):
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


def decode_coverage(raw_timings: list[int] | None) -> bool | None:
    """Does the decode of this capture explain the whole capture?

    The public read of the verdict, for the stores and the mint doors.
    ``None`` means there is nothing to say -- no decode, an
    identity-only tier, or a decoder whose accounting this repo cannot
    verify -- and None is never persisted, so a row that could not be
    judged stays judgeable later rather than being stamped trusted
    forever.
    """
    identity = try_decode_identity(raw_timings)
    return None if identity is None else identity.covers_capture


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
