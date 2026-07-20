"""Inbound format adapters: one funnel, N one-way doors (wigs.md s8).

Every format converts INTO a wig; nothing else enters the system. The
drop zone sniffs the format and routes here; adapter output is always
a list of Wig objects stamped ``origin: "converted:<format>"`` so a
database conversion never masquerades as hardware-proven codes.

v0.7.0 ships the drop-file adapters whose formats were verified against
real files: SmartIR (media_player/fan), Flipper Zero ``.ir``, and LIRC
``lircd.conf``. SmartIR climate files are rejected with a clear reason
(state matrices, not buttons -- plan section 8). The Broadlink scan and
CSV wizard follow in 0.7.x (they need their own UI); RMBridge waits for
a genuine sample export to exist.

Nothing here does I/O; the WS layer owns files. Conversion is
defensive: a signal that cannot convert is skipped WITH A REASON, and
one bad signal never sinks the rest of the file.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass, field

from .ir_command import raw_to_pronto
from .wig_format import Wig, WigSignal

# One Broadlink tick is 2^-15 s (~30.518 us); "us * 269 / 8192" is the
# inverse conversion (python-broadlink protocol.md, verified against
# real RC5 captures -- NOT 32.84 us/tick, which misreads the ratio).
_BROADLINK_TICK_US = 1_000_000 / 32_768

# SmartIR climate files are mode x fan x temperature matrices; importing
# one naively yields hundreds of context-free rows.
_SMARTIR_CLIMATE_KEYS = {
    "minTemperature", "maxTemperature", "precision",
    "operationModes", "fanModes", "swingModes",
}


@dataclass
class AdapterResult:
    """Conversion outcome: wigs plus per-signal skip reasons."""

    format: str
    wigs: list[Wig] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    error: str | None = None


def sniff_format(text: str) -> str | None:
    """Identify a dropped file: "smartir" | "smartir_climate" |
    "flipper" | "lirc" | None (wig files are handled before this by
    ``parse_wig``; None means nothing recognized)."""
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, RecursionError):
            return None
        if not isinstance(data, dict):
            return None
        if isinstance(data.get("commands"), dict):
            if _SMARTIR_CLIMATE_KEYS & set(data):
                return "smartir_climate"
            if any(
                key in data
                for key in ("commandsEncoding", "supportedController",
                            "manufacturer")
            ):
                return "smartir"
        return None
    if "Filetype: IR signals file" in text:
        return "flipper"
    if re.search(r"^\s*begin remote\b", text, re.MULTILINE):
        return "lirc"
    return None


def convert(text: str, name_hint: str = "") -> AdapterResult:
    """Route a non-wig file through its adapter."""
    fmt = sniff_format(text)
    if fmt == "smartir_climate":
        return AdapterResult(
            format="smartir",
            error=(
                "SmartIR climate files are state matrices (mode x fan x "
                "temperature), not buttons, and are not supported yet. "
                "SmartIR media_player and fan files import fine."
            ),
        )
    if fmt == "smartir":
        return _convert_smartir(text)
    if fmt == "flipper":
        return _convert_flipper(text, name_hint)
    if fmt == "lirc":
        return _convert_lirc(text, name_hint)
    return AdapterResult(format="unknown", error="not a recognized format")


# --- Broadlink packets (shared by SmartIR Base64/Hex; RMBridge later) ---


def broadlink_packet_to_pronto(packet: bytes) -> str | None:
    """Decode a Broadlink IR packet into Pronto hex, or None.

    Packet: 0x26 type byte (anything else, incl. RF 0xb2/0xd7, is
    refused), repeat byte, little-endian payload length, then tick
    durations (2^-15 s units; values >255 as 0x00 + big-endian pair),
    alternating mark/space starting with a mark. The trailing 3333-tick
    terminator space rides through harmlessly as the final gap.
    """
    if len(packet) < 6 or packet[0] != 0x26:
        return None
    length = packet[2] | (packet[3] << 8)
    payload = packet[4:4 + length]
    ticks: list[int] = []
    i = 0
    while i < len(payload):
        value = payload[i]
        if value == 0:
            if i + 2 >= len(payload):
                break
            value = (payload[i + 1] << 8) | payload[i + 2]
            i += 3
        else:
            i += 1
        ticks.append(value)
    if len(ticks) < 2:
        return None
    timings = [
        round(t * _BROADLINK_TICK_US) * (1 if idx % 2 == 0 else -1)
        for idx, t in enumerate(ticks)
    ]
    return raw_to_pronto(timings, frequency=38000)


def _broadlink_b64_to_pronto(code: str) -> str | None:
    try:
        packet = base64.b64decode(code.strip(), validate=False)
    except (binascii.Error, ValueError):
        return None
    return broadlink_packet_to_pronto(packet)


# --- SmartIR ---


def _humanize_key(key: str) -> str:
    """``volumeUp`` -> ``Volume Up``; ``level1`` -> ``Level 1``."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key)
    spaced = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", spaced)
    return spaced.replace("_", " ").strip().title() or key


def _smartir_code_to_pronto(
    code: str, encoding: str
) -> tuple[str | None, str | None]:
    """(pronto, failure_reason) for one SmartIR code value."""
    encoding = (encoding or "").strip().lower()
    code = code.strip()
    if encoding == "base64":
        pronto = _broadlink_b64_to_pronto(code)
        if pronto is None:
            return None, "not an IR Broadlink packet"
        return pronto, None
    if encoding == "hex":
        try:
            packet = bytes.fromhex(re.sub(r"\s+", "", code))
        except ValueError:
            return None, "invalid hex"
        pronto = broadlink_packet_to_pronto(packet)
        if pronto is None:
            return None, "not an IR Broadlink packet"
        return pronto, None
    if encoding == "pronto":
        return code, None
    if encoding == "raw":
        values = re.findall(r"-?\d+", code)
        if len(values) < 4:
            return None, "raw list too short"
        timings = [int(v) for v in values]
        return raw_to_pronto(timings, frequency=38000), None
    return None, f"unsupported encoding {encoding or 'missing'!r}"


def _flatten_smartir_commands(
    commands: dict, prefix: str = ""
) -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    for key, value in commands.items():
        label = _humanize_key(str(key))
        path = f"{prefix} {label}".strip()
        if isinstance(value, dict):
            out.extend(_flatten_smartir_commands(value, path))
        else:
            out.append((path, value))
    return out


def _convert_smartir(text: str) -> AdapterResult:
    result = AdapterResult(format="smartir")
    data = json.loads(text)
    encoding = str(data.get("commandsEncoding") or "")
    manufacturer = str(data.get("manufacturer") or "").strip()
    models = data.get("supportedModels") or []
    model = str(models[0]).strip() if models else ""
    name = " ".join(part for part in (manufacturer, model) if part) \
        or "SmartIR Import"

    signals: list[WigSignal] = []
    for alias, value in _flatten_smartir_commands(data.get("commands", {})):
        if isinstance(value, list):
            # A sequence entry sends several codes per press; wigs carry
            # one signal per button, so only the first code imports.
            result.skipped.append(
                f"{alias}: multi-code sequence, imported first code only"
            )
            value = value[0] if value else None
        if not isinstance(value, str) or not value.strip():
            result.skipped.append(f"{alias}: empty code")
            continue
        pronto, reason = _smartir_code_to_pronto(value, encoding)
        if pronto is None:
            result.skipped.append(f"{alias}: {reason}")
            continue
        signals.append(WigSignal(alias=alias, pronto=pronto))
    if not signals:
        result.error = "no convertible codes in this SmartIR file"
        return result
    controller = str(data.get("supportedController") or "").strip()
    result.wigs.append(Wig(
        name=name,
        signals=signals,
        brand=manufacturer or None,
        model=model or None,
        notes=(
            f"Imported from SmartIR ({controller} / {encoding})"
            if controller else "Imported from SmartIR"
        ),
        origin="converted:smartir",
    ))
    return result


# --- Flipper Zero .ir ---

# Flipper renders address/command as 4 little-endian hex bytes; the
# numeric value is what the builders below consume. Builders return an
# infrared-protocols Command or raise/return None to skip.


def _flipper_builders():
    builders = {}
    try:
        from infrared_protocols.commands.nec import NECCommand

        builders["NEC"] = lambda a, c: NECCommand(
            address=a & 0xFF, command=c & 0xFF
        )
        # NECext: 16-bit address; Flipper packs command + inverse into
        # 16 bits (byte0 = command, byte1 = its inverse).
        builders["NECext"] = lambda a, c: NECCommand(
            address=a & 0xFFFF, command=c & 0xFF
        )
    except ImportError:
        pass
    try:
        from infrared_protocols.commands.samsung import Samsung32Command

        builders["Samsung32"] = lambda a, c: Samsung32Command(
            address=a & 0xFF, command=c & 0xFF
        )
    except ImportError:
        pass
    try:
        from infrared_protocols.commands.sony import SonyCommand

        builders["SIRC"] = lambda a, c: SonyCommand(
            address=a & 0x1F, address_bits=5, command=c & 0x7F
        )
        builders["SIRC15"] = lambda a, c: SonyCommand(
            address=a & 0xFF, address_bits=8, command=c & 0x7F
        )
        builders["SIRC20"] = lambda a, c: SonyCommand(
            address=a & 0x1FFF, address_bits=13, command=c & 0x7F
        )
    except ImportError:
        pass
    try:
        from infrared_protocols.commands.rc5 import RC5Command

        builders["RC5"] = lambda a, c: RC5Command(
            address=a & 0x1F, command=c & 0x3F
        )
    except ImportError:
        pass
    return builders


def _flipper_bytes_value(raw: str) -> int:
    """``"4F 50 00 00"`` (little-endian bytes) -> 0x504F."""
    parts = raw.split()
    value = 0
    for i, part in enumerate(parts):
        value |= int(part, 16) << (8 * i)
    return value


def _convert_flipper(text: str, name_hint: str) -> AdapterResult:
    result = AdapterResult(format="flipper")
    builders = _flipper_builders()
    signals: list[WigSignal] = []

    current: dict[str, str] = {}

    def _finish() -> None:
        if not current:
            return
        name = current.get("name", f"Signal {len(signals) + 1}")
        sig_type = current.get("type")
        if sig_type == "raw":
            values = [int(v) for v in current.get("data", "").split()]
            if len(values) < 4:
                result.skipped.append(f"{name}: raw data too short")
                return
            frequency = int(current.get("frequency", "38000") or 38000)
            timings = [
                v if i % 2 == 0 else -v for i, v in enumerate(values)
            ]
            signals.append(WigSignal(
                alias=name,
                pronto=raw_to_pronto(timings, frequency=frequency),
            ))
            return
        if sig_type == "parsed":
            protocol = current.get("protocol", "")
            builder = builders.get(protocol)
            if builder is None:
                result.skipped.append(
                    f"{name}: parsed protocol {protocol or 'unknown'} "
                    "is not encodable yet"
                )
                return
            try:
                address = _flipper_bytes_value(current.get("address", "0"))
                command_v = _flipper_bytes_value(current.get("command", "0"))
                command = builder(address, command_v)
                timings = list(command.get_raw_timings())
                modulation = int(
                    getattr(command, "modulation", 0) or 0
                ) or 38000
                signals.append(WigSignal(
                    alias=name,
                    pronto=raw_to_pronto(timings, frequency=modulation),
                ))
            except Exception as err:
                result.skipped.append(f"{name}: encode failed ({err})")
            return
        result.skipped.append(f"{name}: unknown signal type")

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if key == "name":
            _finish()
            current = {"name": value}
        elif current or key not in ("Filetype", "Version"):
            current[key] = value
    _finish()

    if not signals:
        result.error = "no convertible signals in this Flipper file"
        return result
    name = _stem(name_hint) or "Flipper Import"
    result.wigs.append(Wig(
        name=name,
        signals=signals,
        notes="Imported from a Flipper Zero .ir file",
        origin="converted:flipper",
    ))
    return result


# --- LIRC lircd.conf ---


def _convert_lirc(text: str, name_hint: str) -> AdapterResult:
    result = AdapterResult(format="lirc")
    blocks = re.findall(
        r"begin remote(.*?)end remote", text, re.DOTALL | re.IGNORECASE
    )
    if not blocks:
        result.error = "no remote blocks found"
        return result
    for block in blocks:
        wig = _convert_lirc_remote(block, result)
        if wig is not None:
            result.wigs.append(wig)
    if not result.wigs:
        result.error = result.error or (
            "no convertible remotes in this LIRC file"
        )
    return result


def _lirc_params(block: str) -> dict[str, list[str]]:
    params: dict[str, list[str]] = {}
    body = re.split(
        r"begin (?:raw_)?codes", block, maxsplit=1, flags=re.IGNORECASE
    )[0]
    for line in body.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            params[parts[0].lower()] = parts[1:]
    return params


def _convert_lirc_remote(block: str, result: AdapterResult) -> Wig | None:
    params = _lirc_params(block)
    remote_name = (params.get("name") or ["LIRC Remote"])[0]
    frequency = int((params.get("frequency") or ["38000"])[0])
    flags = " ".join(params.get("flags", [])).upper()
    signals: list[WigSignal] = []

    raw_section = re.search(
        r"begin raw_codes(.*?)end raw_codes", block,
        re.DOTALL | re.IGNORECASE,
    )
    if raw_section:
        for name, numbers in _lirc_raw_entries(raw_section.group(1)):
            if len(numbers) < 3:
                result.skipped.append(f"{remote_name}/{name}: too short")
                continue
            timings = [
                v if i % 2 == 0 else -v for i, v in enumerate(numbers)
            ]
            signals.append(WigSignal(
                alias=name,
                pronto=raw_to_pronto(timings, frequency=frequency),
            ))
    else:
        codes_section = re.search(
            r"begin codes(.*?)end codes", block, re.DOTALL | re.IGNORECASE
        )
        if codes_section is None:
            result.skipped.append(f"{remote_name}: no codes section")
            return None
        if "RC5" in flags or "RC6" in flags:
            result.skipped.append(
                f"{remote_name}: RC5/RC6 coded remotes are not "
                "reconstructable yet"
            )
            return None
        builder = _LircSpaceEnc.from_params(params)
        if builder is None:
            result.skipped.append(
                f"{remote_name}: missing or zero one/zero/bits timings"
            )
            return None
        for line in codes_section.group(1).splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0]
            try:
                value = int(parts[1], 0)
            except ValueError:
                result.skipped.append(f"{remote_name}/{name}: bad code")
                continue
            timings = builder.build(value)
            signals.append(WigSignal(
                alias=_humanize_key(name.removeprefix("KEY_").lower()),
                pronto=raw_to_pronto(timings, frequency=frequency),
            ))

    if not signals:
        result.skipped.append(f"{remote_name}: nothing convertible")
        return None
    return Wig(
        name=remote_name,
        signals=signals,
        notes="Imported from a LIRC lircd.conf",
        origin="converted:lirc",
    )


def _lirc_raw_entries(section: str):
    name: str | None = None
    numbers: list[int] = []
    for line in section.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower().startswith("name "):
            if name is not None and numbers:
                yield name, numbers
            name = line.split(None, 1)[1]
            numbers = []
        else:
            numbers.extend(
                int(v) for v in line.split() if v.lstrip("-").isdigit()
            )
    if name is not None and numbers:
        yield name, numbers


@dataclass
class _LircSpaceEnc:
    """SPACE_ENC pulse-train reconstruction.

    Frame order per the lircd.conf man page:
    header | plead | pre_data | pre | data | post_data | post | ptrail.
    Bits are MSB first (REVERSE flips to LSB). The inter-frame gap is a
    trailing space so the Pronto frame is self-delimiting.
    """

    bits: int
    one: tuple[int, int]
    zero: tuple[int, int]
    header: tuple[int, int] | None
    plead: int | None
    ptrail: int | None
    pre_data: int | None
    pre_data_bits: int
    post_data: int | None
    post_data_bits: int
    gap: int
    reverse: bool

    @classmethod
    def from_params(cls, params: dict) -> _LircSpaceEnc | None:
        def pair(key):
            values = params.get(key)
            if not values or len(values) < 2:
                return None
            p, s = int(values[0]), int(values[1])
            return (p, s) if p > 0 and s > 0 else None

        def single(key):
            values = params.get(key)
            if not values:
                return None
            v = int(values[0])
            return v if v > 0 else None

        one, zero = pair("one"), pair("zero")
        bits = int((params.get("bits") or ["0"])[0])
        if one is None or zero is None or bits <= 0:
            return None
        pre_values = params.get("pre_data")
        post_values = params.get("post_data")
        return cls(
            bits=bits,
            one=one,
            zero=zero,
            header=pair("header"),
            plead=single("plead"),
            ptrail=single("ptrail"),
            pre_data=int(pre_values[0], 0) if pre_values else None,
            pre_data_bits=int((params.get("pre_data_bits") or ["0"])[0]),
            post_data=int(post_values[0], 0) if post_values else None,
            post_data_bits=int((params.get("post_data_bits") or ["0"])[0]),
            gap=int((params.get("gap") or ["40000"])[0]),
            reverse="REVERSE" in " ".join(params.get("flags", [])).upper(),
        )

    def _emit_bits(self, out: list[int], value: int, width: int) -> None:
        order = range(width) if self.reverse else range(width - 1, -1, -1)
        for bit_index in order:
            pulse, space = (
                self.one if (value >> bit_index) & 1 else self.zero
            )
            out.extend((pulse, -space))

    def build(self, code: int) -> list[int]:
        out: list[int] = []
        if self.header:
            out.extend((self.header[0], -self.header[1]))
        if self.plead:
            out.append(self.plead)
        if self.pre_data is not None and self.pre_data_bits > 0:
            self._emit_bits(out, self.pre_data, self.pre_data_bits)
        self._emit_bits(out, code, self.bits)
        if self.post_data is not None and self.post_data_bits > 0:
            self._emit_bits(out, self.post_data, self.post_data_bits)
        if self.ptrail:
            out.append(self.ptrail)
        # Trailing gap keeps the frame self-delimiting; cap it so a
        # 16-million-us LIRC gap does not distort the Pronto frame.
        out.append(-min(self.gap, 100_000))
        return out


def _stem(name_hint: str) -> str:
    stem = re.sub(r"\.(ir|json|conf|txt)$", "", name_hint.strip(),
                  flags=re.IGNORECASE)
    stem = stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() if stem else ""
