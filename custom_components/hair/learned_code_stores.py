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
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ir_command import ProntoCommand, raw_to_pronto
from .tuya_ir import TUYA_CARRIER_HZ, plain_b64_to_timings
from .wig_adapters import broadlink_b64_to_pronto

_LOGGER = logging.getLogger(__name__)

# Neither format records a carrier. Consumer IR is 38 kHz unless the
# source says otherwise, and neither of these sources says anything.
# Recorded as ASSUMED on every code so the report can say so out loud.
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


def _broadlink_packet_type(value: str) -> int | None:
    """First byte of a stored code, for cheap IR/RF counting."""
    packet = _b64_bytes(value)
    return packet[0] if packet else None


@dataclass(frozen=True)
class StoreProvider:
    """One row of the provider table.

    Data, not code paths: adding an integration that follows the same
    convention is a row here plus a payload decoder, and nothing else in
    this module changes.
    """

    integration: str
    prefix: str
    kind: str
    decoder: Callable[[str], tuple[str | None, list[int], str | None, str | None]]
    # Where the hass layer should look for the display name. Broadlink's
    # store id is the device MAC as hex; Tuya Local's is the config
    # entry unique_id. Both resolve through the config entries, and
    # Broadlink additionally through the device registry's MAC
    # connection, which is the name the user actually sees.
    name_hint: str


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


def discover_stores(config_dir: str | Path) -> list[StoreInfo]:
    """Every learned-code store under ``<config_dir>/.storage``.

    Counts only. Nothing is decoded here, so listing a store with a
    thousand codes costs one file read and a first-byte peek per code.
    A corrupt or unreadable file comes back as a StoreInfo carrying
    ``parse_error`` -- it never raises, and it never removes the other
    stores from the list (the 0.10.2 per-item resilience rule).

    Ordering is Broadlink stores first, then Tuya Local, matching the
    dialog's card order so the UI does not have to re-sort.
    """
    storage_dir = Path(config_dir) / ".storage"
    out: list[StoreInfo] = []
    if not storage_dir.is_dir():
        return out
    for provider in PROVIDERS:
        pattern = f"{provider.prefix}*{_CODES_SUFFIX}"
        for path in sorted(storage_dir.glob(pattern)):
            store_id = path.name[len(provider.prefix):-len(_CODES_SUFFIX)]
            if not store_id:
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


def count_toggle_pairs(codes: list[PluckedCode]) -> int:
    """How many commands arrived as a two-packet toggle pair."""
    return sum(1 for code in codes if code.is_toggle_alt)
