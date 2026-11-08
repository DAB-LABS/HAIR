"""irdb CSV files: protocol parameters, built into codes.

An irdb CSV carries no timings. Each row names a protocol and its
parameters, and HAIR builds the code from them::

    functionname,protocol,device,subdevice,function
    POWER,NECx1,45,45,48

``device``, ``subdevice`` and ``function`` are the protocol's D, S and F,
and ``-1`` means "use the protocol's default". The meaning of each field
is the protocol's published definition (the IRP notation the JP1 and
DecodeIR community maintains), never another program's code.

ONE TABLE. ``IRDB_PROTOCOLS`` maps a protocol name to a builder that
constructs a registered command class or one of this package's own
decoders, the way the Flipper reader does, or, for a protocol HAIR does
not decode, one of the encode-only classes in ``encoders``. There is no
encoding in this module itself. A protocol outside the table has its
rows come back as a receipt naming it.

THE FILE SHAPES ACCEPTED, from a measurement of irdb's files:

- the header ``functionname,protocol,device,subdevice,function``, in
  any letter case, with a byte order mark, spaces or a tab between the
  first two words, or ``function`` as the first word;
- no header at all, but only when every line is five fields, the second
  a protocol name irdb uses and the last three integers;
- CSV quoting, so a name may hold a comma;
- protocol names in any letter case (``nec1`` is ``NEC1``);
- a device field written ``D.S`` (``4.1``), read as device and
  subdevice when the file name says the same pair (``4,1.csv``).
"""
from __future__ import annotations

import csv
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

#: The header words, after letter case and spacing are folded away.
_HEADERS = (
    "functionname,protocol,device,subdevice,function",
    "function,protocol,device,subdevice,function",
)

#: Every protocol name irdb's files use, folded to lower case. A
#: headerless file is read as irdb only when every row names one of
#: these, so a stray five-field CSV is never mistaken for one. The names
#: are the protocols' own (IRP / DecodeIR spellings), not a list of files.
IRDB_NAMES = frozenset(name.lower() for name in (
    "48-NEC1", "48-NEC2", "Aiwa", "Akai", "Apple", "Barco", "Blaupunkt",
    "Bose", "CanalSat", "Denon", "Denon-K", "Denon{1}", "Denon{2}", "Dgtec",
    "DirecTV", "Dish_Network", "Dishplayer", "Emerson", "F12", "Fujitsu",
    "G.I.4DTV", "G.I.Cable", "Grundig16", "Grundig16-30", "GXB", "Jerrold",
    "JVC", "JVC-48", "JVC{2}", "Kathrein", "Konka", "Logitech", "Lumagen",
    "MCE", "Mitsubishi", "NEC", "NEC1", "NEC1-f16", "NEC1-rnc", "NEC1-y1",
    "NEC1-y2", "NEC1-y3", "NEC2", "NEC2-f16", "NECx1", "NECx2", "Nokia",
    "Nokia12", "Nokia32", "NRC16", "NRC17", "PaceMSS", "Panasonic",
    "Panasonic2", "Panasonic_Old", "Pioneer", "Proton", "RC5", "RC5-7F",
    "RC6", "RC6-6-20", "RCA", "RCA(Old)", "RCA-38", "RCA-38(Old)", "RECS80",
    "Replay", "Samsung20", "Samsung36", "ScAtl-6", "Sejin-1-38",
    "Sejin-1-56", "Sharp", "SharpDVD", "Sharp{1}", "Sharp{2}", "Sony12",
    "Sony15", "Sony20", "StreamZap", "Teac-K", "Thomson", "Thomson7",
    "Velleman", "XMP", "XMP-1", "XMP-2", "Zaptor-56", "Zenith",
))
_TIVO = re.compile(r"^tivo unit=\d$")

_INT = re.compile(r"^-?\d+$")
_MERGED = re.compile(r"^(\d+)\.(\d+)$")


class IrdbError(ValueError):
    """A row HAIR cannot build, in plain words."""


def known_name(protocol: str) -> bool:
    """Is this a protocol name irdb uses (any letter case)?"""
    name = protocol.strip().lower()
    return name in IRDB_NAMES or bool(_TIVO.match(name))


def is_header(line: str) -> bool:
    """Is this line irdb's header?"""
    folded = re.sub(r"[ \t]*[,\t][ \t]*", ",", line.lstrip("\ufeff").strip())
    return folded.lower() in _HEADERS


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in next(csv.reader([line]), [])]


def looks_headerless(text: str) -> bool:
    """A file with no header that is irdb by every line's shape."""
    lines = [ln for ln in text.lstrip("\ufeff").splitlines() if ln.strip()]
    if not lines:
        return False
    for line in lines:
        cells = _cells(line)
        if len(cells) != 5 or not known_name(cells[1]):
            return False
        if not all(_INT.match(c) for c in cells[2:]):
            return False
    return True


def is_irdb(text: str) -> bool:
    """The probe: irdb's header on the first line, or a headerless file
    that fits the shape on every line."""
    for line in text.lstrip("\ufeff").splitlines():
        if line.strip():
            return is_header(line) or looks_headerless(text)
    return False


@dataclass(frozen=True)
class Row:
    """One readable row: its alias and the protocol's parameters."""

    line: int
    alias: str
    protocol: str
    device: int
    subdevice: int
    function: int


def rows(
    text: str, file_pair: tuple[int, int] | None
) -> tuple[list[Row], list[tuple[int, str]]]:
    """The file's rows, and ``(line, reason)`` for each line that is not one.

    ``file_pair`` is the ``(device, subdevice)`` the file name states
    (``45,45.csv``), when it states one: it settles a merged ``D.S``
    device field and nothing else.
    """
    out: list[Row] = []
    problems: list[tuple[int, str]] = []
    lines = text.lstrip("\ufeff").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if number == 1 and is_header(line):
            continue
        cells = _cells(line)
        if len(cells) == 4 and _MERGED.match(cells[2]):
            # ``4.1`` written for device 4, subdevice 1. Read only when the
            # file name names the same pair; otherwise which number is
            # which is a guess.
            d, s = (int(x) for x in _MERGED.match(cells[2]).groups())
            if file_pair != (d, s):
                problems.append((number, (
                    f"line {number}: device and subdevice are written together "
                    f"as {cells[2]}, and the file name does not say which is which"
                )))
                continue
            cells = [cells[0], cells[1], str(d), str(s), cells[3]]
        if len(cells) != 5:
            problems.append((number, f"line {number}: {len(cells)} fields, not 5"))
            continue
        name, protocol, d, s, f = cells
        if not protocol:
            problems.append((number, f"line {number}: no protocol"))
            continue
        if not all(_INT.match(c) for c in (d, s, f)):
            problems.append((number, (
                f"line {number}: device, subdevice and function must be whole numbers"
            )))
            continue
        function = int(f)
        out.append(Row(
            line=number,
            alias=name or f"Function {function}",
            protocol=protocol,
            device=int(d),
            subdevice=int(s),
            function=function,
        ))
    return out, problems


def file_pair(name_hint: str) -> tuple[int, int] | None:
    """The ``(device, subdevice)`` an irdb file name states, if any."""
    stem = re.split(r"[\\/]", name_hint.strip())[-1]
    m = re.match(r"^(-?\d+),(-?\d+)\.csv$", stem, re.IGNORECASE)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _path_parts(name_hint: str) -> list[str]:
    return [p.strip() for p in re.split(r"[\\/]", name_hint.strip()) if p.strip()]


def wig_name(name_hint: str) -> str:
    """``LG Blu-Ray 45,45`` from ``LG/Blu-Ray/45,45.csv``; the stem otherwise."""
    parts = _path_parts(name_hint)
    if not parts:
        return ""
    stem = re.sub(r"\.csv$", "", parts[-1], flags=re.IGNORECASE).strip()
    if len(parts) >= 3:
        return f"{parts[-3]} {parts[-2]} {stem}".strip()
    return stem


def brand(name_hint: str) -> str | None:
    """The brand folder of ``Brand/Kind/D,S.csv``: ``LG`` for
    ``LG/Blu-Ray/45,45.csv``. None when the name carries no folders, or
    only one, since one folder alone does not say whether it is the
    brand or the kind."""
    parts = _path_parts(name_hint)
    return parts[-3] if len(parts) >= 3 else None


def kind(name_hint: str) -> str | None:
    """HAIR's kind for the kind folder, only when the folder names one of
    HAIR's own kinds (``TV``, ``Receiver``, ``Air Conditioner``); None for
    any other folder (``Blu-Ray``, ``DVD Player``). Read through
    ``normalize_kind``, so no spelling is added here."""
    from .wig_format import normalize_kind

    parts = _path_parts(name_hint)
    return normalize_kind(parts[-2]) if len(parts) >= 3 else None


# --- the protocol table ------------------------------------------------------


def _field(name: str, value: int, top: int, protocol: str) -> int:
    if value == -1:
        raise IrdbError(f"{protocol} needs a {name}, and -1 has no default here")
    if not 0 <= value <= top:
        raise IrdbError(f"{protocol} {name} {value} is outside 0 to {top}")
    return value


def _none(name: str, value: int, protocol: str) -> None:
    if value != -1:
        raise IrdbError(f"{protocol} has no {name}, but the row gives {value}")


def _registered(label: str) -> Any:
    from .protocol_decode import get_spec

    spec = get_spec(label)
    if spec is None or spec.command_cls is None:
        raise IrdbError(f"no {label} class is registered")
    return spec.command_cls


def _nec(protocol: str) -> Callable[[int, int, int], Any]:
    """NEC, NEC1, NEC2, NEC1-f16: one 32-bit frame, D S F ~F.

    S defaults to 255-D. NEC2 differs only in how a held button repeats
    (the whole frame), which is what HAIR's send count does; the stored
    code is the same frame. NEC1-f16's fourth byte is its own parameter
    E, which defaults to 255-F and which an irdb row cannot carry, so
    its frame is NEC1's. Built with the verbatim class, which carries
    the NEC timing and works with or without the optional library.
    """
    def build(d: int, s: int, f: int) -> Any:
        from .decoders.nec_variant import NECNoComplementCommand

        _field("device", d, 0xFF, protocol)
        s = 255 - d if s == -1 else s
        _field("subdevice", s, 0xFF, protocol)
        _field("function", f, 0xFF, protocol)
        return NECNoComplementCommand(
            address=d | (s << 8), command=f | ((~f & 0xFF) << 8)
        )
    return build


def _necx(protocol: str) -> Callable[[int, int, int], Any]:
    """NECx1, NECx2: the NEC frame behind a 4.5 ms leader, S default 255-D.

    The Samsung32 class takes D and S as one 16-bit address, except that
    an address of 0xFF or less goes out as D,D, so S = 0 with a nonzero
    D cannot be sent and is refused rather than changed. NECx1's held
    button repeats a one-bit ditto HAIR does not send; a press is the
    same frame either way.
    """
    def build(d: int, s: int, f: int) -> Any:
        _field("device", d, 0xFF, protocol)
        s = 255 - d if s == -1 else s
        _field("subdevice", s, 0xFF, protocol)
        _field("function", f, 0xFF, protocol)
        if s == 0 and d != 0:
            raise IrdbError(
                f"{protocol} subdevice 0 with device {d} cannot be sent yet"
            )
        return _registered("SAMSUNG32")(address=d | (s << 8), command=f)
    return build


def _rc5(d: int, s: int, f: int) -> Any:
    _field("device", d, 31, "RC5")
    _none("subdevice", s, "RC5")
    _field("function", f, 127, "RC5")
    # Function 64..127 is RC5X: the class spends the second start bit on
    # function bit 6, which is what the protocol does. Toggle 0: a wig
    # holds one code per button and the toggle flips per press.
    return _registered("RC5")(address=d, command=f, toggle=0)


def _sony(bits: int) -> Callable[[int, int, int], Any]:
    """Sony12/15/20: F 7 bits, then D 5 or 8 bits, then (20) S 8 bits."""
    protocol = f"Sony{bits}"

    def build(d: int, s: int, f: int) -> Any:
        _field("function", f, 127, protocol)
        cls = _registered(f"SONY{bits}")
        if bits == 20:
            _field("device", d, 31, protocol)
            _field("subdevice", s, 0xFF, protocol)
            return cls(address=d | (s << 5), address_bits=13, command=f)
        _none("subdevice", s, protocol)
        top = 31 if bits == 12 else 0xFF
        _field("device", d, top, protocol)
        return cls(address=d, address_bits=5 if bits == 12 else 8, command=f)
    return build


def _rc6(d: int, s: int, f: int) -> Any:
    """RC6, mode 0, 8-bit device and function."""
    _field("device", d, 0xFF, "RC6")
    _none("subdevice", s, "RC6")
    _field("function", f, 0xFF, "RC6")
    return _registered("RC6")(address=d, command=f, mode=0, toggle=0)


def _mce(d: int, s: int, f: int) -> Any:
    """MCE: RC6 mode 6 with OEM1 128 and S as OEM2, then T, D 7, F 8."""
    _field("device", d, 127, "MCE")
    _field("subdevice", s, 0xFF, "MCE")
    _field("function", f, 0xFF, "MCE")
    return _registered("RC6")(
        address=d, command=f, mode=6, customer=(128 << 8) | s, toggle=0
    )


def _panasonic(d: int, s: int, f: int) -> Any:
    """Panasonic: Kaseikyo with vendor bytes 2, 32, then D S F and D^S^F.

    The class derives the low nibble of the byte after the vendor from
    the vendor's parity, which is 0 for Panasonic, so a D whose low
    nibble is not 0 cannot be sent as written and is refused. 37 kHz,
    the protocol's own carrier.
    """
    _field("device", d, 0xFF, "Panasonic")
    _field("subdevice", s, 0xFF, "Panasonic")
    _field("function", f, 0xFF, "Panasonic")
    if d & 0x0F:
        raise IrdbError(
            f"Panasonic device {d} cannot be sent yet (HAIR needs its low "
            "four bits to be 0)"
        )
    return _registered("KASEIKYO")(
        address=0x2002, data=bytes([d, s, f, d ^ s ^ f]), modulation=37000
    )


def _denon_k(d: int, s: int, f: int) -> Any:
    """Denon-K: Kaseikyo with vendor bytes 84, 50, then 0:4, D:4, S:4,
    F:12 and the check byte (D*16 ^ S ^ F*16 ^ F:8:4). 37 kHz."""
    _field("device", d, 15, "Denon-K")
    _field("subdevice", s, 15, "Denon-K")
    _field("function", f, 0xFFF, "Denon-K")
    check = ((d << 4) ^ s ^ (f << 4) ^ ((f >> 4) & 0xFF)) & 0xFF
    return _registered("KASEIKYO")(
        address=0x3254,
        data=bytes([d << 4, s | ((f & 0x0F) << 4), (f >> 4) & 0xFF, check]),
        modulation=37000,
    )


def _pioneer(d: int, s: int, f: int) -> Any:
    """Pioneer: the NEC2 frame at 40 kHz, S default 255-D."""
    from .decoders.pioneer import PioneerCommand

    _field("device", d, 0xFF, "Pioneer")
    s = 255 - d if s == -1 else s
    _field("subdevice", s, 0xFF, "Pioneer")
    _field("function", f, 0xFF, "Pioneer")
    return PioneerCommand(address=d | (s << 8), command=f | ((~f & 0xFF) << 8))


def _rca(protocol: str, carrier: int) -> Callable[[int, int, int], Any]:
    """RCA: D 4 bits, F 8 bits, both complemented, at the protocol's carrier.

    RCA is 58 kHz. RCA-38 is the same frame at 38.7 kHz, which is the
    only difference the protocol reference gives between the two.
    """
    def build(d: int, s: int, f: int) -> Any:
        _field("device", d, 15, protocol)
        _none("subdevice", s, protocol)
        _field("function", f, 0xFF, protocol)
        return _registered("RCA")(device=d, function=f, modulation=carrier)
    return build


def _sharp(protocol: str, extension: int) -> Callable[[int, int, int], Any]:
    """Sharp and Denon share one frame: D 5, F 8, then two bits that are
    1,0 for Sharp and 0,0 for Denon, followed by the inverted half."""
    def build(d: int, s: int, f: int) -> Any:
        _field("device", d, 31, protocol)
        _none("subdevice", s, protocol)
        _field("function", f, 0xFF, protocol)
        return _registered("SHARP")(address=d, command=f, extension=extension)
    return build


def _aiwa(d: int, s: int, f: int) -> Any:
    """Aiwa: the 42-bit NEC frame, D 8 and S 5 as the 13-bit address."""
    from .decoders.nec42 import NEC42Command

    _field("device", d, 0xFF, "Aiwa")
    _field("subdevice", s, 31, "Aiwa")
    _field("function", f, 0xFF, "Aiwa")
    return NEC42Command(address=d | (s << 8), command=f)


def _jvc(protocol: str) -> Callable[[int, int, int], Any]:
    """JVC: D 8 bits, F 8 bits, no subdevice, at the class's 38 kHz.

    JVC{2} is the same remote: DecodeIR's name for a JVC signal learned
    without its lead-in, which only a press's first frame carries. The
    reference says that when JVC{2} is correct it means the same as JVC,
    so its rows build the full JVC frame, lead-in and all, as the
    handset sends it.
    """
    def build(d: int, s: int, f: int) -> Any:
        _field("device", d, 0xFF, protocol)
        _none("subdevice", s, protocol)
        _field("function", f, 0xFF, protocol)
        return _registered("JVC")(address=d, command=f)
    return build


def _mitsubishi(d: int, s: int, f: int) -> Any:
    """Mitsubishi: D 8 bits (0 to 127), F 8 bits, at 32.6 kHz. Encode only."""
    from .encoders.mitsubishi import MitsubishiCommand

    _field("device", d, 127, "Mitsubishi")
    _none("subdevice", s, "Mitsubishi")
    _field("function", f, 0xFF, "Mitsubishi")
    return MitsubishiCommand(device=d, function=f)


def _recs80(d: int, s: int, f: int) -> Any:
    """RECS80: D 3 bits, F 6 bits, toggle 0, at 38 kHz. Encode only."""
    from .encoders.recs80 import RECS80Command

    _field("device", d, 7, "RECS80")
    _none("subdevice", s, "RECS80")
    _field("function", f, 63, "RECS80")
    return RECS80Command(device=d, function=f, toggle=0)


def _gi_cable(d: int, s: int, f: int) -> Any:
    """G.I.Cable: F 8 bits, D 4 bits and a check nibble, at 38.7 kHz.

    Encode only. Every irdb row gives D 0, the device the reference
    lists for these boxes, but any D up to 15 is the protocol's own.
    """
    from .encoders.gi_cable import GICableCommand

    _field("device", d, 15, "G.I.Cable")
    _none("subdevice", s, "G.I.Cable")
    _field("function", f, 0xFF, "G.I.Cable")
    return GICableCommand(device=d, function=f)


def _dish_network(d: int, s: int, f: int) -> Any:
    """Dish_Network: F 6 bits, S 5 bits, D 5 bits, at 57.6 kHz. Encode only."""
    from .encoders.dish_network import DishNetworkCommand

    _field("device", d, 31, "Dish_Network")
    _field("subdevice", s, 31, "Dish_Network")
    _field("function", f, 63, "Dish_Network")
    return DishNetworkCommand(device=d, subdevice=s, function=f)


def _fujitsu(d: int, s: int, f: int) -> Any:
    """Fujitsu: Kaseikyo with vendor bytes 20, 99, then 0:4, E:4, D, S, F.

    No check byte. S defaults to D. E has a default of 0 in the IRP and
    an irdb row cannot carry it, so the byte after the vendor is 0. The
    Kaseikyo class derives that byte's low four bits from the vendor's
    parity, which for 20 and 99 is the 0 the protocol writes there.
    37 kHz, the protocol's own carrier.
    """
    _field("device", d, 0xFF, "Fujitsu")
    s = d if s == -1 else s
    _field("subdevice", s, 0xFF, "Fujitsu")
    _field("function", f, 0xFF, "Fujitsu")
    return _registered("KASEIKYO")(
        address=20 | (99 << 8), data=bytes([0, d, s, f]), modulation=37000
    )


def _panasonic_old(d: int, s: int, f: int) -> Any:
    """Panasonic_Old: D 5 bits, F 6 bits, both again inverted, at 57.6 kHz.

    Encode only.
    """
    from .encoders.panasonic_old import PanasonicOldCommand

    _field("device", d, 31, "Panasonic_Old")
    _none("subdevice", s, "Panasonic_Old")
    _field("function", f, 63, "Panasonic_Old")
    return PanasonicOldCommand(device=d, function=f)


def _tivo(unit: int) -> Callable[[int, int, int], Any]:
    """Tivo: the NEC1 frame with D 133, S 48, F, then U:4 and ~F:4:4.

    The protocol reference fixes D at 133 and S at 48, so -1 gives those
    and anything else is refused. The fourth byte is the unit U in its
    low four bits and the complement of F's high four bits above them.
    irdb names the unit in the protocol name (``Tivo unit=3``), the way
    DecodeIR reports a Tivo decode, so each unit is its own table row.
    Built with the verbatim NEC class, as NEC1-f16 is.
    """
    protocol = f"Tivo unit={unit}"

    def build(d: int, s: int, f: int) -> Any:
        from .decoders.nec_variant import NECNoComplementCommand

        d = 133 if d == -1 else d
        s = 48 if s == -1 else s
        if d != 133:
            raise IrdbError(f"{protocol} device is always 133, but the row gives {d}")
        if s != 48:
            raise IrdbError(f"{protocol} subdevice is always 48, but the row gives {s}")
        _field("function", f, 0xFF, protocol)
        fourth = unit | (((~f >> 4) & 0x0F) << 4)
        return NECNoComplementCommand(
            address=d | (s << 8), command=f | (fourth << 8)
        )
    return build


#: irdb protocol name (lower case) -> (its spelling, the builder).
IRDB_PROTOCOLS: dict[str, tuple[str, Callable[[int, int, int], Any]]] = {
    name.lower(): (name, build)
    for name, build in (
        ("NEC", _nec("NEC")),
        ("NEC1", _nec("NEC1")),
        ("NEC2", _nec("NEC2")),
        ("NEC1-f16", _nec("NEC1-f16")),
        ("NECx1", _necx("NECx1")),
        ("NECx2", _necx("NECx2")),
        ("RC5", _rc5),
        ("Sony12", _sony(12)),
        ("Sony15", _sony(15)),
        ("Sony20", _sony(20)),
        ("RC6", _rc6),
        ("MCE", _mce),
        ("Panasonic", _panasonic),
        ("Denon-K", _denon_k),
        ("Pioneer", _pioneer),
        ("RCA", _rca("RCA", 58000)),
        ("RCA-38", _rca("RCA-38", 38700)),
        ("Sharp", _sharp("Sharp", 1)),
        ("Denon", _sharp("Denon", 0)),
        ("Aiwa", _aiwa),
        ("JVC", _jvc("JVC")),
        ("JVC{2}", _jvc("JVC{2}")),
        ("Mitsubishi", _mitsubishi),
        ("RECS80", _recs80),
        ("G.I.Cable", _gi_cable),
        ("Dish_Network", _dish_network),
        *((f"Tivo unit={unit}", _tivo(unit)) for unit in range(10)),
        ("Panasonic_Old", _panasonic_old),
        ("Fujitsu", _fujitsu),
    )
}


def build(protocol: str, device: int, subdevice: int, function: int) -> Any:
    """The command for one row; IrdbError when HAIR cannot build it."""
    entry = IRDB_PROTOCOLS.get(protocol.strip().lower())
    if entry is None:
        raise IrdbError(f"{protocol.strip()} cannot be built yet")
    return entry[1](device, subdevice, function)
