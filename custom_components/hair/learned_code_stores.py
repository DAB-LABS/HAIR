"""Read learned IR codes at rest, out of another integration's store.

The Plucker's SECOND mechanism (0.10.3). Until now a pluck meant replay:
ask a vendor integration to send a stored code, point it at the HAIR
Tweezer, and catch the ``Command`` before it becomes light. That works
for appliance codebooks and not at all for codes the user learned
themselves on hardware that only transmits through its own emitter.

Broadlink and Tuya Local both write every learned code to a file under
``.storage`` and both use the same construction: an HA ``Store``
envelope wrapping ``subdevice -> command name -> code``, with a sibling
``_flags`` file tracking toggle state. This module reads those files.

READ-ONLY, ALWAYS. Home Assistant warns against editing ``.storage`` and
HAIR never does. Nothing here opens a file for writing, and nothing here
holds a handle open past the read.

PURE. No ``hass``, no I/O scheduling, no registries. The caller runs
``discover_stores`` and ``read_store`` in an executor job (they block on
disk) and resolves friendly names from the config entries and the device
registry, which is where that knowledge lives.

RULE ZERO: THE STORE DECIDES THE DECODER.
=========================================
A Tuya store payload beginning ``26 03`` is a plain little-endian
microsecond array whose first duration is 806 us. It is also, byte for
byte, something HAIR's Broadlink packet parser accepts: 0x26 is the
Broadlink IR type byte. The parser does not fail on it. It returns
silently wrong timings, which is the worst outcome an import path has,
because a wrong code looks exactly like a right one until someone
presses it.

A raw timing array can begin with any byte, so no amount of sniffing
fixes this. What fixes it is that a store read is not anonymous: the
filename says which integration wrote the file, and that is the whole
answer. A code from a ``broadlink_remote_*`` store goes to the Broadlink
packet decoder. A code from a ``tuya_local_remote_*`` store goes to the
Tuya plaintext decoder. Payload content NEVER routes between them.

Content detection remains the law for the anonymous drop bar, where
there is no filename to ask. That is a different problem.

ONE DECODER, ONE TICK CONSTANT.
The Broadlink packet decoder here is the same function the SmartIR
import calls (``wig_adapters.broadlink_b64_to_pronto``), called and
never re-declared. The tick constant, the escape handling, and the
trailing capture-timeout strip all live there. Two doors onto the same
physical code must produce one identity, and the only way to guarantee
that is to run one implementation.

TWO STORE SHAPES, NOT ONE.
Everything above describes the PACKET MAP: ``subdevice -> command name
-> base64 packet``, which Broadlink and Tuya Local share and where the
providers differ only in how one base64 string becomes Pronto.
OpenIRBlaster (GH #169) keeps its library in a different construction
altogether: ``data["codes"]`` is a flat LIST of JSON objects, each
carrying its own ``name``, its own signed-microsecond ``pulses`` and,
unlike either packet-map store, its own MEASURED ``carrier_hz``. That
is a second shape, not a third decoder, so each provider row names its
shape and the four places that walk a store (the discovery glob, the
discovery count, the iterator, the reader) branch on it. The
packet-map arms are untouched; the code-list arms sit beside them.

Rule zero holds across shapes exactly as it holds across decoders: the
filename picks the provider, the provider picks the shape, and nothing
in a payload is ever consulted to choose either.
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .ir_command import ProntoCommand, raw_to_pronto
from .tuya_ir import TUYA_CARRIER_HZ, plain_b64_to_timings
from .wig_adapters import broadlink_b64_to_pronto

_LOGGER = logging.getLogger(__name__)

# Neither format records a carrier. Consumer IR is 38 kHz unless the
# source says otherwise, and neither of these sources says anything.
# Recorded as ASSUMED on every code so the report can say so out loud.
# (OpenIRBlaster does record one, per code; it falls back to this only
# when that field is missing or unusable, and says so the same way.)
ASSUMED_CARRIER_HZ = TUYA_CARRIER_HZ

# Broadlink type bytes. 0x26 is IR; 0xb2 and 0xd7 are RF, which share
# the same file and are told apart only by this byte (HA core's
# broadlink/remote.py does the same check).
_BROADLINK_IR = 0x26
_BROADLINK_RF = (0xB2, 0xD7)

# The suffix every code store carries. The sibling ``_flags`` store is
# deliberately not read: it holds which half of a toggle pair goes out
# next, which is transmit state belonging to the other integration, and
# on the probe's real Tuya store it was empty anyway. Both packets of a
# pair are imported as named signals instead.
_CODES_SUFFIX = "_codes"

# The two store shapes a provider row can name. See the module
# docstring: the shape is a property of the provider, chosen by the
# filename like everything else, and never sniffed from the payload.
SHAPE_PACKET_MAP = "packet_map"  # subdevice -> command -> base64 packet
SHAPE_CODE_LIST = "code_list"  # data["codes"] -> list of code objects

# A flat code list has no subdevice level, and a plucked remote is one
# subdevice, so every code in it lands on one remote named for the
# device record inside the file. On every OpenIRBlaster install that
# record says "OpenIRBlaster" (the integration never passes its own
# name through), which is also the fallback when it is missing.
_OPENIRBLASTER_SUBDEVICE = "OpenIRBlaster"

# Trailing gap appended to an odd-length OpenIRBlaster capture, the one
# that ended on a mark. The same -38000 us OpenIRBlaster's own wig
# exporter appends (its ``normalize_pulses``), so the two ways that
# file reaches HAIR (exported wig, plucked store) agree on what a given
# code's timings are. It is a space, so it puts no extra energy on the
# emitter.
_OPENIRBLASTER_TRAILING_GAP_US = -38000

# Receipt kinds. Anything unconvertible gets one of these and is never
# invented into a code (the 0.8.8 rule, and the whole shape of GH #108).
RECEIPT_RF = "rf"
RECEIPT_NO_TIMINGS = "no_timings"
RECEIPT_UNREADABLE = "unreadable"


@dataclass
class PluckedCode:
    """One code read out of a store: converted, or receipted."""

    subdevice: str
    command_name: str
    base_command_name: str
    pronto: str | None = None
    timings: list[int] = field(default_factory=list)
    frequency: int = ASSUMED_CARRIER_HZ
    carrier_assumed: bool = True
    # Half two of a two-packet toggle command, named "<name> (alt)".
    is_toggle_alt: bool = False
    receipt: str | None = None
    receipt_kind: str | None = None

    @property
    def imported(self) -> bool:
        return self.pronto is not None and self.receipt is None


@dataclass
class StoreInfo:
    """A discovered code store, counted but not decoded."""

    integration: str
    store_id: str
    path: str
    subdevices: int = 0
    codes: int = 0
    ir_codes: int = 0
    rf_codes: int = 0
    parse_error: str | None = None
    # Filled by the hass layer from the config entry / device registry.
    # The pure layer has no way to know a device's friendly name and
    # never guesses one; empty means "caller, resolve this".
    friendly_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "integration": self.integration,
            "friendly_name": self.friendly_name or self.store_id,
            "subdevices": self.subdevices,
            "codes": self.codes,
            "ir_codes": self.ir_codes,
            "rf_codes": self.rf_codes,
            "error": self.parse_error,
        }


def _b64_bytes(value: str) -> bytes | None:
    """Decode base64 with the padding salvage both readers already do.

    HA core's own ``broadlink.helpers.data_packet`` repairs missing
    trailing padding before decoding, and so does the SmartIR path, so
    repairing it here keeps all three in agreement.
    """
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    if len(cleaned) % 4:
        cleaned += "=" * (-len(cleaned) % 4)
    try:
        return base64.b64decode(cleaned, validate=False)
    except (binascii.Error, ValueError):
        return None


def _pronto_timings(pronto: str) -> list[int]:
    """Signed timings for a Pronto string, or [] if it will not parse."""
    try:
        return list(ProntoCommand(pronto).get_raw_timings())
    except Exception:  # a code that will not re-read is still a code
        return []


def decode_broadlink_code(value: str) -> tuple[str | None, list[int], str | None, str | None]:
    """(pronto, timings, receipt, receipt_kind) for one Broadlink code.

    Called ONLY for codes read out of a ``broadlink_remote_*`` store.
    """
    packet = _b64_bytes(value)
    if not packet:
        return None, [], "could not read this code", RECEIPT_UNREADABLE
    first = packet[0]
    if first in _BROADLINK_RF:
        return (
            None,
            [],
            "RF code set aside -- HAIR plucks IR today",
            RECEIPT_RF,
        )
    if first != _BROADLINK_IR:
        return (
            None,
            [],
            f"unknown packet type 0x{first:02x}",
            RECEIPT_UNREADABLE,
        )
    pronto = broadlink_b64_to_pronto(value)
    if pronto is None:
        return None, [], "no usable timings", RECEIPT_NO_TIMINGS
    return pronto, _pronto_timings(pronto), None, None


def decode_tuya_local_code(value: str) -> tuple[str | None, list[int], str | None, str | None]:
    """(pronto, timings, receipt, receipt_kind) for one Tuya Local code.

    Called ONLY for codes read out of a ``tuya_local_remote_*`` store.
    The payload is base64 of a PLAIN little-endian uint16 microsecond
    array -- the same plaintext that sits inside the FastLZ container
    the 0.10.2 reader handles, with no container around it. There is no
    type byte and no header, so nothing here inspects the first byte:
    see this module's rule zero.
    """
    timings = plain_b64_to_timings(value)
    if not timings:
        return None, [], "no usable timings", RECEIPT_NO_TIMINGS
    try:
        pronto = raw_to_pronto(timings, frequency=ASSUMED_CARRIER_HZ)
    except (ValueError, TypeError, IndexError):
        return None, [], "no usable timings", RECEIPT_NO_TIMINGS
    return pronto, list(timings), None, None


def _is_int(value: Any) -> bool:
    """A real JSON integer. ``bool`` is an ``int`` in Python and is not one."""
    return isinstance(value, int) and not isinstance(value, bool)


def decode_openirblaster_code(
    entry: dict[str, Any],
) -> tuple[str | None, list[int], int, bool, str | None, str | None]:
    """(pronto, timings, frequency, assumed, receipt, receipt_kind).

    Called ONLY for entries read out of an ``openirblaster_*`` store,
    and only once the reader has a name for the entry: naming is the
    reader's job, this is the payload. See this module's rule zero: the
    filename routes, the content never does.

    The payload is a JSON object rather than a base64 string, which is
    why this is not a drop-in for the packet-map decoders above and why
    it returns two more fields than they do. ``pulses`` is signed
    microseconds, positive a mark and negative a space, and goes to
    ``raw_to_pronto`` as it is, the same way the Tuya plaintext does.

    ``carrier_hz`` is the reason this route exists. OpenIRBlaster
    measured it at learn time, and ESPHome reports no carrier through
    ``ir_rf_proxy``, so a code re-learned through HAIR would come back
    at 38 kHz and a 36 or 40 kHz device may then not respond. A
    positive integer is taken as measured and encoded into the Pronto
    preamble, which is the carrier the import path actually keeps.
    Anything else (missing, null, a string, a bool, zero, negative) is
    38 kHz ASSUMED, recorded as assumed like the packet-map stores.

    A capture that ended on a mark has an odd number of durations. It
    is repaired with a trailing ``-38000`` us gap, matching OpenIRBlaster's
    own wig exporter, and logged at debug; it is not receipted, because
    the code is sound and only its last idle is missing.

    Every failure is a receipt, never a raise and never an invented
    code: an empty or non-list array, a non-integer duration, or an
    array the encoder will not take all come back as ``no_timings``.
    """
    carrier = entry.get("carrier_hz")
    if _is_int(carrier) and carrier > 0:
        frequency, assumed = carrier, False
    else:
        frequency, assumed = ASSUMED_CARRIER_HZ, True

    pulses = entry.get("pulses")
    if not isinstance(pulses, list) or not pulses:
        return None, [], frequency, assumed, "no usable timings", RECEIPT_NO_TIMINGS
    if not all(_is_int(p) for p in pulses):
        return (
            None,
            [],
            frequency,
            assumed,
            "timings are not whole microseconds",
            RECEIPT_NO_TIMINGS,
        )

    timings = list(pulses)
    if len(timings) % 2:
        timings.append(_OPENIRBLASTER_TRAILING_GAP_US)
        _LOGGER.debug(
            "OpenIRBlaster code %r: odd pulse count (%d), appended a %d us "
            "trailing gap",
            entry.get("name") or entry.get("id"),
            len(pulses),
            abs(_OPENIRBLASTER_TRAILING_GAP_US),
        )

    try:
        pronto = raw_to_pronto(timings, frequency=frequency)
    except (ValueError, TypeError, IndexError, ZeroDivisionError, OverflowError):
        return None, [], frequency, assumed, "no usable timings", RECEIPT_NO_TIMINGS
    # A hand-edited carrier far outside anything IR uses, or a duration
    # longer than 65535 carrier periods, encodes to a word wider than
    # Pronto's sixteen bits. That is not a code; receipt it here rather
    # than hand the import path a string it has to refuse.
    if any(len(word) > 4 for word in pronto.split()):
        return None, [], frequency, assumed, "no usable timings", RECEIPT_NO_TIMINGS
    return pronto, timings, frequency, assumed, None, None


def _broadlink_packet_type(value: str) -> int | None:
    """First byte of a stored code, for cheap IR/RF counting."""
    packet = _b64_bytes(value)
    return packet[0] if packet else None


# The two decoder signatures, one per shape. A packet-map decoder takes
# one base64 string; a code-list decoder takes one code object and also
# hands back the carrier it used and whether that carrier was assumed.
PacketDecoder = Callable[[str], tuple[str | None, list[int], str | None, str | None]]
CodeEntryDecoder = Callable[
    [dict[str, Any]],
    tuple[str | None, list[int], int, bool, str | None, str | None],
]


@dataclass(frozen=True)
class StoreProvider:
    """One row of the provider table.

    Data, not code paths: adding an integration that follows the same
    convention is a row here plus a payload decoder, and nothing else in
    this module changes. An integration with a DIFFERENT convention is a
    row that names a different ``shape``, and the reader dispatches on
    that field before it ever calls the decoder.
    """

    integration: str
    prefix: str
    kind: str
    # Which of the two signatures this is follows from ``shape``:
    # a ``PacketDecoder`` for SHAPE_PACKET_MAP, a ``CodeEntryDecoder``
    # for SHAPE_CODE_LIST. ``read_store`` checks the shape first, so the
    # pairing is enforced where the call happens.
    decoder: PacketDecoder | CodeEntryDecoder
    # Where the hass layer should look for the display name. Broadlink's
    # store id is the device MAC as hex; Tuya Local's is the config
    # entry unique_id. Both resolve through the config entries, and
    # Broadlink additionally through the device registry's MAC
    # connection, which is the name the user actually sees.
    # OpenIRBlaster's is the config entry's entry_id, which is NOT its
    # unique_id (that is the device MAC), so ``entry_id`` is a value
    # ``pluck.resolve_store_names`` acts on rather than only reads.
    name_hint: str
    # The filename tail after the store id. Both packet-map stores end
    # in ``_codes``; OpenIRBlaster's file is ``openirblaster_<entry_id>``
    # with nothing after it, so its row carries an empty suffix.
    suffix: str = _CODES_SUFFIX
    shape: str = SHAPE_PACKET_MAP


PROVIDERS: tuple[StoreProvider, ...] = (
    StoreProvider(
        integration="broadlink",
        prefix="broadlink_remote_",
        kind="Broadlink learned codes",
        decoder=decode_broadlink_code,
        name_hint="mac",
    ),
    StoreProvider(
        integration="tuya_local",
        prefix="tuya_local_remote_",
        kind="Tuya Local learned codes",
        decoder=decode_tuya_local_code,
        name_hint="entry_unique_id",
    ),
    StoreProvider(
        integration="openirblaster",
        prefix="openirblaster_",
        kind="OpenIRBlaster learned codes",
        decoder=decode_openirblaster_code,
        name_hint="entry_id",
        suffix="",
        shape=SHAPE_CODE_LIST,
    ),
)

PROVIDERS_BY_INTEGRATION: dict[str, StoreProvider] = {
    provider.integration: provider for provider in PROVIDERS
}


def provider_for(integration: str) -> StoreProvider | None:
    return PROVIDERS_BY_INTEGRATION.get(integration)


def _load_envelope(path: Path) -> dict[str, Any] | None:
    """Parse an HA Store file and hand back its ``data`` mapping."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    data = raw.get("data")
    if not isinstance(data, dict):
        return None
    return data


def _iter_commands(data: dict[str, Any]):
    """Yield ``(subdevice, command_name, packets)`` over a store's data.

    A value that is a list of two is a TOGGLE PAIR (HA core writes it
    that way when a device learns an alternating command); anything else
    is a single packet. Non-string junk is skipped rather than trusted.
    """
    for subdevice, commands in data.items():
        if not isinstance(commands, dict):
            continue
        for command_name, value in commands.items():
            if isinstance(value, list):
                packets = [v for v in value if isinstance(v, str)]
            elif isinstance(value, str):
                packets = [value]
            else:
                packets = []
            yield str(subdevice), str(command_name), packets


def _iter_code_entries(data: dict[str, Any]):
    """Yield ``(index, entry)`` over a code-list store's ``data["codes"]``.

    The sibling of ``_iter_commands`` for the second shape, kept apart
    so the packet-map walk keeps its exact signature. Entries come out
    as they are, junk included: the reader receipts a bad one by its
    position rather than dropping it here, which is how a user finds
    out which entry of a hand-edited file was the problem.
    """
    codes = data.get("codes")
    if not isinstance(codes, list):
        return
    yield from enumerate(codes)


def _code_list_subdevice(data: dict[str, Any]) -> str:
    """The one subdevice a flat code list becomes."""
    device = data.get("device")
    name = device.get("name") if isinstance(device, dict) else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    return _OPENIRBLASTER_SUBDEVICE


def _code_list_name(entry: dict[str, Any]) -> str:
    """The display name, falling back to the stable id, or "" for neither.

    ``name`` is what the user typed and may have renamed since, so it
    is the command name and the seeded alias. ``id`` is the slug of the
    ORIGINAL name, kept stable across renames, and is only a fallback.
    """
    for key in ("name", "id"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def discover_stores(config_dir: str | Path) -> list[StoreInfo]:
    """Every learned-code store under ``<config_dir>/.storage``.

    Counts only. Nothing is decoded here, so listing a store with a
    thousand codes costs one file read and a first-byte peek per code.
    A corrupt or unreadable file comes back as a StoreInfo carrying
    ``parse_error`` -- it never raises, and it never removes the other
    stores from the list (the 0.10.2 per-item resilience rule).

    Ordering is Broadlink stores first, then Tuya Local, then
    OpenIRBlaster, matching the dialog's card order so the UI does not
    have to re-sort.

    An empty suffix needs one more guard. ``openirblaster_*`` also
    matches Home Assistant's own corruption backups, which it writes as
    ``<store>.corrupt.<isotime>`` beside the store, so a store id with a
    dot in it is not a store. A config entry id never has one.
    """
    storage_dir = Path(config_dir) / ".storage"
    out: list[StoreInfo] = []
    if not storage_dir.is_dir():
        return out
    for provider in PROVIDERS:
        pattern = f"{provider.prefix}*{provider.suffix}"
        for path in sorted(storage_dir.glob(pattern)):
            # Sliced conditionally, because ``name[a:-0]`` is empty and
            # the guard below would silently swallow every store.
            store_id = (
                path.name[len(provider.prefix):-len(provider.suffix)]
                if provider.suffix
                else path.name[len(provider.prefix):]
            )
            if not store_id:
                continue
            if not provider.suffix and "." in store_id:
                continue
            info = StoreInfo(
                integration=provider.integration,
                store_id=store_id,
                path=str(path),
            )
            try:
                data = _load_envelope(path)
            except (OSError, ValueError, RecursionError) as err:
                info.parse_error = "Could not read this file"
                _LOGGER.debug("Learned-code store %s unreadable: %s", path.name, err)
                out.append(info)
                continue
            if data is None:
                info.parse_error = "Could not read this file"
                out.append(info)
                continue
            if provider.shape == SHAPE_CODE_LIST:
                # A flat list is one remote, every entry one code, and
                # there is no RF in it to count apart. Walking data's
                # values the packet-map way would count the ``device``
                # record as a subdevice and skip the list entirely.
                entries = data.get("codes")
                count = len(entries) if isinstance(entries, list) else 0
                info.subdevices = 1 if count else 0
                info.codes = count
                info.ir_codes = count
                out.append(info)
                continue
            subdevices = 0
            codes = 0
            ir_codes = 0
            rf_codes = 0
            for commands in data.values():
                if not isinstance(commands, dict):
                    continue
                subdevices += 1
                for _name, value in commands.items():
                    codes += 1
                    packets = value if isinstance(value, list) else [value]
                    for packet in packets:
                        if not isinstance(packet, str):
                            continue
                        if provider.integration != "broadlink":
                            ir_codes += 1
                            continue
                        first = _broadlink_packet_type(packet)
                        if first in _BROADLINK_RF:
                            rf_codes += 1
                        elif first == _BROADLINK_IR:
                            ir_codes += 1
            info.subdevices = subdevices
            info.codes = codes
            info.ir_codes = ir_codes
            info.rf_codes = rf_codes
            out.append(info)
    return out


def read_store(info: StoreInfo) -> list[PluckedCode]:
    """Decode every code in one store, receipts included.

    The decoder is chosen by ``info.integration`` and by nothing else --
    see this module's rule zero. A code that cannot convert comes back
    as a PluckedCode carrying a receipt and no Pronto, so the caller
    counts it and shows it rather than discovering later that a code
    quietly vanished.

    Multi-frame codes pass through whole: frame handling belongs to the
    normalize pipeline that every other capture goes through, not to a
    reader.
    """
    provider = provider_for(info.integration)
    if provider is None:
        return []
    path = Path(info.path)
    try:
        data = _load_envelope(path)
    except (OSError, ValueError, RecursionError) as err:
        _LOGGER.debug("Learned-code store %s unreadable: %s", path.name, err)
        return []
    if data is None:
        return []
    if provider.shape == SHAPE_CODE_LIST:
        return _read_code_list(info, provider, data)

    out: list[PluckedCode] = []
    for subdevice, command_name, packets in _iter_commands(data):
        if not packets:
            out.append(
                PluckedCode(
                    subdevice=subdevice,
                    command_name=command_name,
                    base_command_name=command_name,
                    receipt="could not read this code",
                    receipt_kind=RECEIPT_UNREADABLE,
                )
            )
            continue
        is_pair = len(packets) > 1
        for index, packet in enumerate(packets):
            name = command_name if index == 0 else f"{command_name} (alt)"
            pronto, timings, receipt, kind = provider.decoder(packet)
            out.append(
                PluckedCode(
                    subdevice=subdevice,
                    command_name=name,
                    base_command_name=command_name,
                    pronto=pronto,
                    timings=timings,
                    is_toggle_alt=is_pair and index > 0,
                    receipt=receipt,
                    receipt_kind=kind,
                )
            )
            if receipt is not None:
                _LOGGER.debug(
                    "Learned-code store %s: %s/%s skipped (%s)",
                    info.store_id, subdevice, name, receipt,
                )
    return out


def _read_code_list(
    info: StoreInfo, provider: StoreProvider, data: dict[str, Any]
) -> list[PluckedCode]:
    """``read_store``'s arm for a flat code list, one PluckedCode per entry.

    No packets and no toggle pairs: an entry is one code with its own
    name and carrier. An entry that is not an object, or that has
    neither a name nor an id to file it under, is receipted as
    unreadable under its position in the list. Tags and notes have no
    home on a HAIR signal and are not carried.
    """
    # The shape check in read_store is what makes this the right
    # signature; the cast says so to a type checker.
    decoder = cast(CodeEntryDecoder, provider.decoder)
    subdevice = _code_list_subdevice(data)
    out: list[PluckedCode] = []
    for index, entry in _iter_code_entries(data):
        name = _code_list_name(entry) if isinstance(entry, dict) else ""
        if not name:
            label = f"entry {index}"
            receipt = (
                "no name to import this code under"
                if isinstance(entry, dict)
                else "could not read this code"
            )
            out.append(
                PluckedCode(
                    subdevice=subdevice,
                    command_name=label,
                    base_command_name=label,
                    receipt=receipt,
                    receipt_kind=RECEIPT_UNREADABLE,
                )
            )
            _LOGGER.debug(
                "Learned-code store %s: %s skipped (%s)",
                info.store_id, label, receipt,
            )
            continue
        pronto, timings, frequency, assumed, receipt, kind = decoder(entry)
        out.append(
            PluckedCode(
                subdevice=subdevice,
                command_name=name,
                base_command_name=name,
                pronto=pronto,
                timings=timings,
                frequency=frequency,
                carrier_assumed=assumed,
                receipt=receipt,
                receipt_kind=kind,
            )
        )
        if receipt is not None:
            _LOGGER.debug(
                "Learned-code store %s: %s/%s skipped (%s)",
                info.store_id, subdevice, name, receipt,
            )
    return out


def count_toggle_pairs(codes: list[PluckedCode]) -> int:
    """How many commands arrived as a two-packet toggle pair."""
    return sum(1 for code in codes if code.is_toggle_alt)
