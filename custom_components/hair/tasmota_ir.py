"""Tasmota infrared codes: one reader for the Closet and the paste box.

Tasmota has no export. What its users hold are the strings they copied:
``IRsend`` commands from their notes or rules, and ``IrReceived`` lines
from the console when they pressed a remote at the receiver. This module
reads one such string into a code and is shared by both doors, so a code
pasted alone and the same code in a file are one code.

THE FORMS, AS TASMOTA'S OWN DRIVER READS THEM:

- ``IRsend {"Protocol":"NEC","Bits":32,"Data":"0x20DF10EF"}``, the JSON
  form, also ``DataLSB`` (each byte's bits reversed) and ``Repeat``.
- ``IRsend <freq>,<v1>,<v2>,...``: a raw list in microseconds, marks and
  spaces alternating from a mark. A frequency of 0 means 38 kHz, and a
  value under 1000 is in kHz.
- ``IRsend <freq>,+8570-4240+550-1580C-510...``: the same list in
  Tasmota's compressed notation. Each new value is written with its sign
  (``+`` mark, ``-`` space) and given the next letter; a value seen
  before is written as its letter, capital for a mark and small for a
  space.
- ``IRsend raw,<freq>,...,<bitstream>``: a bit stream with its timings.
  With one or two timing parameters every character is one duration
  (``0`` the zero time, ``1`` the one time, twice the zero time unless
  given); with five (header mark, header space, bit mark, zero space,
  one space) every bit is a mark and a space after the header, then a
  closing mark. Tasmota accepts no other count.
- ``IRsend gc,<freq>,<repeat>,<offset>,<counts>``: a Global Cache body,
  read by ``sendir.py``.
- ``{"IrReceived":{"Protocol":...,"Bits":...,"Data":...,"RawData":...}}``,
  a console capture, with or without its time and MQTT topic.
- ``IRsend<n>`` sends the code ``n`` times.

THREE TRAPS, EACH NAMED WHERE IT IS HANDLED. ``IRhvac`` is a climate
state, not a code, and is refused. PANASONIC's ``Bits`` is a bit count
(48) in today's firmware and was the 16-bit vendor address (0x4004 =
16388) in the old driver, so anything above 64 is read as the address.
A raw list carries no carrier: 38 kHz is recorded as assumed, never as
declared.

A PROTOCOL IS RENDERED ONLY THROUGH AN ENCODER HAIR HAS, and every
rendering goes through the import doors' round-trip check. A protocol
with no encoder is a receipt, never a guess; an ``IrReceived`` line that
also carries its raw timings lands those instead, since they are the
person's own capture.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

DEFAULT_HZ = 38_000
MAX_RAW_US = 65_535  # Tasmota holds each duration in 16 bits
_NEC_REPEAT = (1 << 64) - 1  # the value IRremoteESP8266 reports for a ditto


class TasmotaError(ValueError):
    """A Tasmota code that cannot become a HAIR code, in plain words."""


@dataclass
class TasmotaCode:
    """One rendered code and what the caller should say about it."""

    pronto: str
    carrier_hz: int
    carrier_source: str  # "declared", "protocol" or "assumed"
    bypass: bool = False
    repeat: int = 0  # extra sends the source asked for
    notes: list[str] = field(default_factory=list)


# --- finding a code in a line -------------------------------------------

_CONSOLE = re.compile(r"^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s+(?:[A-Z]{3}:\s*)?")
_TOPIC = re.compile(r"^[\w.-]+(?:/[\w.%-]+)+\s*=\s*")
# A command word followed by a body that can only be a code: an object,
# a number, a compressed list, or the raw and gc forms. Prose that merely
# mentions IRsend is not a code line.
_COMMAND = re.compile(
    r"\bIR(?:send\d*\s*(?=\{)|send\d*\s+(?=[\d+]|raw\s*,|gc\s*,)"
    r"|hvac\d*\s*(?=\{))",
    re.IGNORECASE,
)
_COMPRESSED = re.compile(r"(?:^|(?<=[\s:=|,]))[+]\d+-\d+")
_IR_KEYS = ("irreceived", "irhvac", "protocol", "rawdata")


def is_ir_object(value: object) -> bool:
    """A JSON object that is a Tasmota IR payload."""
    if not isinstance(value, dict):
        return False
    keys = {str(k).lower() for k in value}
    if "irreceived" in keys or "irhvac" in keys:
        return True
    if "protocol" in keys and keys & {"data", "datalsb", "rawdata", "bits"}:
        return True
    return "rawdata" in keys


def _looks_like_ir_json(text: str) -> bool:
    lowered = text.lower()
    return any(f'"{key}"' in lowered for key in _IR_KEYS)


def find_code(line: str) -> tuple[str | None, str] | None:
    """``(name, code)`` for a line holding one Tasmota code, else None.

    A name may lead the code (``Power: IRsend ...``, ``Power = ...``) or
    sit in a markdown table's first cell; a console line's time and its
    MQTT topic are not names.
    """
    line = line.strip()
    if not line or line.startswith(("#", "//")):
        return None
    if line.startswith("|"):
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            return None
        for cell in cells[1:]:
            found = find_code(cell)
            if found is not None:
                return cells[0] or None, found[1]
        return None
    console = _CONSOLE.match(line)
    if console:
        line = line[console.end():]
        line = _TOPIC.sub("", line, count=1)
        named = False
    else:
        named = True
    start = None
    command = _COMMAND.search(line)
    if command:
        start = command.start()
    else:
        brace = line.find("{")
        if brace >= 0 and _looks_like_ir_json(line[brace:]):
            start = brace
        else:
            packed = _COMPRESSED.search(line)
            if packed:
                start = packed.start()
    if start is None:
        return None
    code = line[start:].strip().strip("`").strip()
    name = None
    if named:
        name = line[:start].strip().rstrip(":=|").strip().strip("\"'`").strip()
        name = name or None
    return name, code


# --- rendering one code -------------------------------------------------


def render(code: str) -> TasmotaCode:
    """One Tasmota code string to a HAIR code, or TasmotaError."""
    code = code.strip()
    command = re.match(r"IR(send|hvac)(\d*)\s*", code, re.IGNORECASE)
    if command:
        if command.group(1).lower() == "hvac":
            raise TasmotaError("climate state (IRhvac), not a code")
        sends = int(command.group(2) or 1)
        body = code[command.end():].strip()
        if not body:
            raise TasmotaError("IRsend with nothing after it")
        result = _render_body(body)
        result.repeat = max(result.repeat, sends - 1)
        return result
    if code.startswith("{"):
        return _render_json(code, sent=False)
    if code.startswith("+"):
        timings = parse_raw(code)
        return _raw(timings, None)
    raise TasmotaError("not a Tasmota IR code")


def _render_body(body: str) -> TasmotaCode:
    if body.startswith("{"):
        return _render_json(body, sent=True)
    head, _, rest = body.partition(",")
    word = head.strip().lower()
    if word == "gc":
        from .sendir import SendirError, parse_sendir_body

        try:
            parsed = parse_sendir_body(rest)
        except SendirError as err:
            raise TasmotaError(f"Global Cache form: {err}") from err
        result = _pronto_result(
            parsed.timings(), parsed.frequency, "declared"
        )
        result.repeat = parsed.repeat - 1
        return result
    if word == "raw":
        return _render_parametric(rest)
    hz, source = _frequency(head)
    return _raw(parse_raw(rest), hz, source)


def _frequency(text: str) -> tuple[int, str]:
    text = text.strip()
    if not text.isdigit():
        raise TasmotaError(f"the frequency {text!r} is not a number")
    value = int(text)
    if value == 0:
        return DEFAULT_HZ, "assumed"
    if value < 1000:
        value *= 1000  # IRremoteESP8266 reads a small value as kHz
    return value, "declared"


def parse_raw(text: str) -> list[int]:
    """A raw list, plain or compressed, as signed microseconds.

    Position decides mark or space, as it does on the device. The
    compressed notation also states it, with the sign of a number and the
    case of a letter, and a disagreement means the string was damaged,
    so it is refused rather than read one way or the other.
    """
    letters: list[int] = []
    values: list[int] = []
    pos = 0
    text = text.strip()
    token = re.compile(r"\s*,?\s*([+-]?)(\d+)|\s*,?\s*([A-Za-z])")
    while pos < len(text):
        match = token.match(text, pos)
        if match is None:
            if text[pos:].strip(" ,") == "":
                break
            raise TasmotaError(f"unexpected {text[pos]!r} in the raw timings")
        pos = match.end()
        index = len(values)
        if match.group(2) is not None:
            value = int(match.group(2))
            sign = match.group(1)
            if sign and (sign == "+") != (index % 2 == 0):
                raise TasmotaError("marks and spaces out of order")
            if value not in letters and len(letters) < 26:
                letters.append(value)
        else:
            letter = match.group(3)
            slot = ord(letter.upper()) - ord("A")
            if slot >= len(letters):
                raise TasmotaError(
                    f"the letter {letter} names a value not given yet"
                )
            if letter.isupper() != (index % 2 == 0):
                raise TasmotaError("marks and spaces out of order")
            value = letters[slot]
        if value <= 0 or value > MAX_RAW_US:
            raise TasmotaError(f"a duration of {value} us is not valid")
        values.append(value if index % 2 == 0 else -value)
    if len(values) < 4:
        raise TasmotaError("too few raw timings")
    return values


def _render_parametric(rest: str) -> TasmotaCode:
    fields = [f.strip() for f in rest.split(",")]
    if len(fields) < 3:
        raise TasmotaError("raw form too short")
    hz, source = _frequency(fields[0])
    stream = fields[-1]
    if not re.fullmatch(r"[01]+", stream):
        raise TasmotaError("the bit stream is not 0s and 1s")
    params = []
    for value in fields[1:-1]:
        if not value.isdigit() or int(value) == 0:
            raise TasmotaError("a raw timing parameter is not a positive number")
        params.append(int(value))
    if len(params) in (1, 2):
        zero = params[0]
        one = zero * 2
        if len(params) == 2:
            one = zero * params[1] if params[1] <= 10 else params[1]
        durations = [one if bit == "1" else zero for bit in stream]
        timings = [d if i % 2 == 0 else -d for i, d in enumerate(durations)]
    elif len(params) == 5:
        hdr_mark, hdr_space, bit_mark, zero_space, one_space = params
        timings = [hdr_mark, -hdr_space]
        for bit in stream:
            timings += [bit_mark, -(one_space if bit == "1" else zero_space)]
        timings.append(bit_mark)
    else:
        raise TasmotaError(
            f"Tasmota does not accept a raw form with {len(params)} timing "
            "parameters (it takes 1, 2 or 5)"
        )
    if any(abs(t) > MAX_RAW_US for t in timings):
        raise TasmotaError(f"a duration above {MAX_RAW_US} us is not valid")
    if len(timings) < 4:
        raise TasmotaError("too few raw timings")
    return _pronto_result(timings, hz, source)


def _raw(timings: list[int], hz: int | None, source: str = "assumed") -> TasmotaCode:
    return _pronto_result(timings, hz or DEFAULT_HZ, source if hz else "assumed")


def _pronto_result(timings: list[int], hz: int, source: str) -> TasmotaCode:
    from .ir_command import raw_to_pronto

    return TasmotaCode(raw_to_pronto(timings, frequency=hz), hz, source)


# --- the JSON forms -----------------------------------------------------

_LOOSE = re.compile(
    r'"(\w+)"\s*:\s*(?:"([^"]*)"|\[([^\]]*)\]|(0x[0-9a-f]+|-?\d+))',
    re.IGNORECASE,
)


def _loads(text: str) -> dict:
    """The IR object of a JSON line, read leniently.

    Tasmota's own documentation prints ``"RawData":[+8570-4240...]``,
    which is not JSON, and console copies get cut at the end; the fields
    this reader needs are pulled out one by one when strict parsing fails.
    """
    try:
        value = json.loads(text)
    except ValueError:
        value = None
    if isinstance(value, dict):
        return value
    found: dict = {}
    for key, text_value, list_value, number in _LOOSE.findall(text):
        if text_value or (not list_value and not number):
            found[key] = text_value
        elif list_value:
            found[key] = list_value
        else:
            # Tasmota's own parser takes a bare hex value ("Data":0x20DF..),
            # which is not JSON; keep it as text for _int to read.
            found[key] = number
    if not found:
        raise TasmotaError("not readable as Tasmota JSON")
    return found


def _lower(value: dict) -> dict:
    return {str(k).lower(): v for k, v in value.items()}


def _render_json(text: str, *, sent: bool) -> TasmotaCode:
    outer = _lower(_loads(text))
    # A leniently read line comes back flat, so the capture is also
    # recognised by its key in the text.
    received = "irreceived" in outer or '"irreceived"' in text.lower()
    payload = outer.get("irreceived", outer)
    if isinstance(payload, str):
        raise TasmotaError("not readable as Tasmota JSON")
    payload = _lower(payload)
    if "irhvac" in outer and "protocol" not in payload:
        raise TasmotaError("climate state (IRhvac), not a code")
    protocol = str(payload.get("protocol") or payload.get("vendor") or "")
    protocol = protocol.strip().upper()
    repeat = 0 if received else _int(payload.get("repeat"), 0)
    rawdata = payload.get("rawdata")

    def raw_fallback(reason: str) -> TasmotaCode:
        if rawdata in (None, "", []):
            raise TasmotaError(reason)
        info = payload.get("rawdatainfo")
        if isinstance(info, str):
            info = [int(v) for v in re.findall(r"\d+", info)]
        if isinstance(info, list) and len(info) >= 3 and info[2]:
            raise TasmotaError(
                "the capture overflowed Tasmota's buffer, so its timings "
                "are incomplete"
            )
        if isinstance(rawdata, list):
            timings_text = ",".join(str(v) for v in rawdata)
        else:
            timings_text = str(rawdata)
        hz, source = DEFAULT_HZ, "assumed"
        if not received and payload.get("frequency") not in (None, "", 0):
            frequency = _int(payload.get("frequency"), 0)
            if 0 < frequency <= 0xFFFF:
                hz, source = _frequency(str(frequency))
        result = _raw(parse_raw(timings_text), hz, source)
        result.repeat = repeat
        if received and reason:
            result.notes.append(f"used the raw timings ({reason})")
        return result

    if not protocol or protocol == "UNKNOWN":
        if rawdata in (None, "", []):
            raise TasmotaError(
                "protocol UNKNOWN carries only a hash, not a code"
                if protocol else "no protocol and no raw timings"
            )
        return raw_fallback("")
    bits = _int(payload.get("bits"), 0)
    data = _data(payload, bits)
    builder = _ENCODERS.get(protocol)
    if builder is None or data is None:
        reason = f"protocol {protocol} has no encoder in HAIR yet"
        if data is None and builder is not None:
            reason = f"the {protocol} line carries no Data"
        if received:
            return raw_fallback(reason)
        raise TasmotaError(reason)
    try:
        result = _encode(builder, protocol, bits, data)
    except TasmotaError as err:
        if received:
            return raw_fallback(str(err))
        raise
    result.repeat = repeat
    return result


def _int(value: object, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip()
    try:
        return int(text, 0)
    except ValueError:
        return default


def _data(payload: dict, bits: int) -> int | None:
    """The code's value as Tasmota sends it, most significant bit first."""
    if payload.get("data") not in (None, ""):
        value = _int(payload["data"], -1)
        return value if value >= 0 else None
    if payload.get("datalsb") not in (None, "") and bits:
        lsb = _int(payload["datalsb"], -1)
        if lsb < 0:
            return None
        width = (bits + 7) // 8
        return _bytes_value([_rev(b, 8) for b in lsb.to_bytes(width, "big")])
    return None


def _rev(value: int, width: int) -> int:
    out = 0
    for _ in range(width):
        out = (out << 1) | (value & 1)
        value >>= 1
    return out


def _bytes_value(values: list[int]) -> int:
    out = 0
    for value in values:
        out = (out << 8) | value
    return out


def _wire(data: int, width: int) -> list[int]:
    """Bytes in the order they go on the air, each LSB first.

    Tasmota writes the value most significant bit first, which for the
    pulse-distance families here is the first bit sent, so each byte is
    bit-reversed into the least-significant-first order HAIR's encoders
    take.
    """
    return [_rev(b, 8) for b in data.to_bytes(width, "big")]


# --- the encoder table --------------------------------------------------


def _nec(bits: int, data: int):
    from .decoders.nec_variant import NECNoComplementCommand

    _bits(bits, 32)
    if data == _NEC_REPEAT or data == 0xFFFFFFFF:
        raise TasmotaError("NEC repeat code, not a key")
    wb = _wire(data, 4)
    return NECNoComplementCommand(
        address=wb[0] | (wb[1] << 8), command=wb[2] | (wb[3] << 8)
    )


def _samsung(bits: int, data: int):
    from .decoders.samsung import Samsung32Command

    _bits(bits, 32)
    wb = _wire(data, 4)
    if wb[3] != wb[2] ^ 0xFF:
        raise TasmotaError(
            "the Samsung command byte and its complement disagree"
        )
    if wb[0] == wb[1]:
        address = wb[0]
    elif wb[1] == 0:
        # The encoder writes an address of one byte twice, so it cannot
        # write this one: say so rather than send a different code.
        raise TasmotaError("HAIR's Samsung encoder cannot write this address")
    else:
        address = wb[0] | (wb[1] << 8)
    return Samsung32Command(address=address, command=wb[2])


def _sony(bits: int, data: int):
    from .decoders.sony import SonyCommand

    if bits not in (12, 15, 20):
        raise TasmotaError(f"SONY with {bits} bits (HAIR sends 12, 15 or 20)")
    value = _rev(data, bits)
    return SonyCommand(
        address=value >> 7, address_bits=bits - 7, command=value & 0x7F
    )


def _rc5(bits: int, data: int, extended: bool):
    from .decoders.rc5 import RC5Command

    if bits == 13 or extended:
        field = (data >> 12) & 1
    elif bits == 12:
        field = 0
    else:
        raise TasmotaError(f"RC5 with {bits} bits (Tasmota sends 12 or 13)")
    return RC5Command(
        address=(data >> 6) & 0x1F,
        command=(data & 0x3F) | (field << 6),
        toggle=(data >> 11) & 1,
    )


def _rc6(bits: int, data: int):
    from .decoders.rc6 import RC6Command

    if bits == 20:
        if (data >> 17) & 0x7:
            raise TasmotaError("RC6 20-bit code that is not mode 0")
        return RC6Command(
            address=(data >> 8) & 0xFF, command=data & 0xFF, mode=0,
            toggle=(data >> 16) & 1,
        )
    if bits == 36:
        customer = (data >> 16) & 0xFFFF
        if (data >> 33) & 0x7 != 6 or (data >> 32) & 1 or customer < 0x8000:
            raise TasmotaError(
                "RC6 36-bit code HAIR's mode 6 encoder cannot write"
            )
        return RC6Command(
            address=(data >> 8) & 0x7F, command=data & 0xFF, mode=6,
            customer=customer, toggle=(data >> 15) & 1,
        )
    raise TasmotaError(f"RC6 with {bits} bits (HAIR sends 20 or 36)")


def _panasonic(bits: int, data: int):
    from .decoders.kaseikyo import KaseikyoCommand

    if bits > 64:
        # THE TRAP. The old driver took Bits as the 16-bit vendor address
        # (0x4004 = 16388) and Data as the 32 bits after it.
        data = (bits << 32) | (data & 0xFFFFFFFF)
        bits = 48
    _bits(bits, 48)
    wb = _wire(data, 6)
    address = wb[0] | (wb[1] << 8)
    parity = address ^ (address >> 8)
    parity = (parity ^ (parity >> 4)) & 0x0F
    if wb[2] & 0x0F != parity:
        raise TasmotaError("the Panasonic vendor check nibble does not match")
    return KaseikyoCommand(address=address, data=bytes(wb[2:]))


def _sharp(bits: int, data: int):
    from .decoders.sharp import SharpCommand

    _bits(bits, 15)
    value = _rev(data, 15)
    if (value >> 14) & 1:
        raise TasmotaError("SHARP inverted frame (check bit set), not a key")
    return SharpCommand(
        address=value & 0x1F, command=(value >> 5) & 0xFF,
        extension=(value >> 13) & 1,
    )


def _pioneer(bits: int, data: int):
    from .decoders.pioneer import PioneerCommand

    if bits == 64:
        high, low = data >> 32, data & 0xFFFFFFFF
        if high != low:
            raise TasmotaError(
                "two different Pioneer codes per press; HAIR's Pioneer "
                "encoder sends one"
            )
        data, frames = low, 2
    elif bits == 32:
        frames = 1
    else:
        raise TasmotaError(f"PIONEER with {bits} bits (Tasmota sends 64)")
    wb = _wire(data, 4)
    return PioneerCommand(
        address=wb[0] | (wb[1] << 8), command=wb[2] | (wb[3] << 8),
        repeat_count=frames - 1,
    )


def _bits(bits: int, expected: int) -> None:
    if bits != expected:
        raise TasmotaError(f"{bits} bits where the protocol has {expected}")


_ENCODERS = {
    "NEC": _nec,
    "NEC_LIKE": _nec,
    "SAMSUNG": _samsung,
    "SONY": _sony,
    "RC5": lambda bits, data: _rc5(bits, data, False),
    "RC5X": lambda bits, data: _rc5(bits, data, True),
    "RC6": _rc6,
    "PANASONIC": _panasonic,
    "SHARP": _sharp,
    "PIONEER": _pioneer,
}


def _encode(builder, protocol: str, bits: int, data: int) -> TasmotaCode:
    from .ir_command import carrier_or_default, raw_to_pronto
    from .wig_adapters import _triple_reproduces

    try:
        command = builder(bits, data)
    except TasmotaError:
        raise
    except (ValueError, OverflowError) as err:
        raise TasmotaError(f"{protocol}: {err}") from err
    timings = list(command.get_raw_timings())
    hz = carrier_or_default(getattr(command, "modulation", None))
    pronto = raw_to_pronto(timings, frequency=hz)
    return TasmotaCode(
        pronto, hz, "protocol",
        bypass=not _triple_reproduces(pronto, timings),
    )
