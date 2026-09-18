"""Inbound format adapters: one funnel, N one-way doors (wigs.md s8).

Every format converts INTO a wig; nothing else enters the system. The
drop zone sniffs the format and routes here; adapter output is always
a list of Wig objects stamped ``origin: "converted:<format>"`` so a
database conversion never masquerades as hardware-proven codes.

v0.7.0 ships the drop-file adapters whose formats were verified against
real files: SmartIR (media_player/fan), Flipper Zero ``.ir``, LIRC
``lircd.conf``, and Girr (IrScrutinizer's XML interchange -- one door
that buys the whole harctoolbox funnel, since IrScrutinizer normalizes
IRDB, Pronto CCF, CML, JP1, and more into Girr-with-Pronto). SmartIR
climate files are rejected with a clear reason (state matrices, not
buttons -- plan section 8). The Broadlink scan and CSV wizard follow in
0.7.x (they need their own UI); RMBridge waits for a genuine sample
export to exist.

Nothing here does I/O; the WS layer owns files. Conversion is
defensive: a signal that cannot convert is skipped WITH A REASON, and
one bad signal never sinks the rest of the file.
"""
from __future__ import annotations

import base64
import binascii
import itertools
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from .ir_command import carrier_or_default, raw_to_pronto
from .tuya_ir import tuya_b64_to_pronto
from .wig_format import Wig, WigSignal

# One Broadlink tick is 2^-15 s (~30.518 us); "us * 269 / 8192" is the
# inverse conversion (python-broadlink protocol.md, verified against
# real RC5 captures -- NOT 32.84 us/tick, which misreads the ratio).
_BROADLINK_TICK_US = 1_000_000 / 32_768

# The two Flipper file headers. A remote file is one device's buttons
# and is what HAIR reads; a library file is the firmware's shotgun file
# for a whole device type, carrying the same handful of buttons for
# hundreds of models. See ``_refuse_flipper_library``.
FLIPPER_REMOTE_HEADER = "Filetype: IR signals file"
FLIPPER_LIBRARY_HEADER = "Filetype: IR library file"

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
    # Sequence-to-send_count collapses (Smart Perm). Conversion is a
    # transcode everywhere else; this is the one place import TRANSFORMS
    # rather than transcodes, so every fold is named rather than left to
    # be noticed later as a signal that sends three times for no visible
    # reason.
    folds: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class FormatProbe:
    """One format's claim on a file.

    ``rank`` orders the claims: a file that matches several formats is
    the highest-ranked one that matched. The ranks below reproduce the
    if-chain this registry replaced, and the overlaps they resolve are
    real (a fork climate file matches both the fork probe and the
    ordinary climate probe, a climate file matches the generic SmartIR
    probe as well).

    ``probe`` takes the text and the parsed JSON (None when the file is
    not a JSON object), so the JSON formats do not each re-parse it.
    """

    name: str
    rank: int
    probe: Callable[[str, object], bool]


@dataclass(frozen=True)
class SniffResult:
    """What the registry made of a file."""

    format: str | None
    candidates: tuple[str, ...] = ()
    reason: str | None = None


# NO LIGHT PROBE LIVES HERE, ON PURPOSE. An earlier cut of this work
# carried one, keyed first on a ``brightness`` array and then on the
# light command vocabulary, and both markers are the ordinary light
# schema's own: the vocabulary IS the upstream vocabulary, so the probe
# fired on stock light files and refused a file that imported as seven
# buttons the day before. Nothing in the content separates the two
# light schemas, so no narrowing of the marker set can be correct.
# Light files keep the flat-button path they have always had, and a
# light schema this reader cannot represent is a later phase's problem,
# to be keyed on whatever a real pair of files turns out to differ by.


def _is_json_object(parsed: object) -> bool:
    return isinstance(parsed, dict)


def _smartir_shaped(parsed: object) -> bool:
    """A SmartIR family file: a JSON object with a ``commands`` object."""
    return _is_json_object(parsed) and isinstance(
        parsed.get("commands"), dict  # type: ignore[union-attr]
    )


def _probe_fork_climate(text: str, parsed: object) -> bool:
    """A fork climate file: a non-empty top-level ``presetModes``.

    ONE MARKER, NOT TWO. The plan also listed "``operationModes`` is an
    object rather than a list", and the review measured it across
    every file it walked: it fires on nothing, and the fork schema says
    the key is a list. What ``presetModes`` answers is the question the
    deeper walk actually needs answered -- does this file carry a preset
    level -- and the files that carry it are the files that need it.
    """
    if not _smartir_shaped(parsed):
        return False
    presets = parsed.get("presetModes")  # type: ignore[union-attr]
    return isinstance(presets, list) and len(presets) > 0


def _probe_girr(text: str, parsed: object) -> bool:
    return text.lstrip().startswith("<") and (
        "harctoolbox.org/Girr" in text or "girrVersion" in text
    )


def _probe_smartir_climate(text: str, parsed: object) -> bool:
    return _smartir_shaped(parsed) and bool(
        _SMARTIR_CLIMATE_KEYS & set(parsed)  # type: ignore[arg-type]
    )


def _probe_smartir(text: str, parsed: object) -> bool:
    return _smartir_shaped(parsed) and any(
        key in parsed  # type: ignore[operator]
        for key in ("commandsEncoding", "supportedController", "manufacturer")
    )


# A HEADER LINE, NOT A SUBSTRING. Both of these read a declaration
# that a Flipper file makes on a line of its own, so both are anchored
# to one. An unanchored search refused a legitimate single-remote file
# whose comment quoted the library header -- which is precisely the
# file the library refusal tells a person to go and make.
_FLIPPER_HEADER_RE = re.compile(
    r"^Filetype:\s*IR (signals|library) file\s*$", re.MULTILINE
)


def _flipper_header(text: str) -> str | None:
    """``"signals"``, ``"library"``, or None: the file's own claim."""
    if text.lstrip().startswith("{"):
        return None
    match = _FLIPPER_HEADER_RE.search(text)
    return match.group(1) if match else None


def _probe_flipper_library(text: str, parsed: object) -> bool:
    return _flipper_header(text) == "library"


def _probe_flipper(text: str, parsed: object) -> bool:
    return _flipper_header(text) == "signals"


def _probe_lirc(text: str, parsed: object) -> bool:
    return not text.lstrip().startswith("{") and bool(
        re.search(r"^\s*begin remote\b", text, re.MULTILINE)
    )


# THE REGISTRY. Ranks reproduce the if-chain exactly, including its one
# structural rule: a file that starts with "{" is a JSON file and is
# never read as Flipper or LIRC, whatever else its bytes contain. The
# old chain got that from returning early inside the JSON branch; here
# each text probe carries the same guard, because a registry runs every
# probe rather than stopping at the first.
_PROBES: tuple[FormatProbe, ...] = (
    FormatProbe("smartir_fork_climate", 60, _probe_fork_climate),
    FormatProbe("girr", 50, _probe_girr),
    FormatProbe("smartir_climate", 40, _probe_smartir_climate),
    FormatProbe("smartir", 30, _probe_smartir),
    FormatProbe("flipper_library", 25, _probe_flipper_library),
    FormatProbe("flipper", 20, _probe_flipper),
    FormatProbe("lirc", 10, _probe_lirc),
)

# Which extension names which format, for the tie-break below. A hint
# may only CHOOSE between formats that already matched at the top rank
# (GH #108 settled that content wins): it can never add a format no
# probe matched, and never veto one.
_HINT_FORMATS: dict[str, tuple[str, ...]] = {
    ".ir": ("flipper", "flipper_library"),
    ".conf": ("lirc",),
    ".girr": ("girr",),
    ".xml": ("girr",),
    ".json": (
        "smartir_fork_climate", "smartir_climate", "smartir",
    ),
}


def sniff(text: str, name_hint: str = "") -> SniffResult:
    """Identify a dropped file through the probe registry.

    Every probe runs; the answer is the highest rank that matched, and
    only when exactly one probe holds that rank. Two at the top rank is
    a refusal naming both, which the file's extension may break if it
    names one of them.

    NO SHIPPED PAIR CAN TIE TODAY. Every rank in the table is distinct,
    so ``max`` is always held by one probe and the refusal below is
    unreachable from any file. It is here for phase 2, which adds
    formats identified by punctuation rather than by a header word, and
    it is tested by registering a probe at a rank another one already
    holds. Saying that plainly is the point: a reader should not take
    the code below for a guard that fires today.
    """
    parsed: object = None
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, RecursionError):
            parsed = None
    matched = [p for p in _PROBES if p.probe(text, parsed)]
    if not matched:
        return SniffResult(None)
    top = max(p.rank for p in matched)
    holders = [p.name for p in matched if p.rank == top]
    if len(holders) == 1:
        return SniffResult(holders[0], tuple(holders))
    suffix = _name_suffix(name_hint)
    preferred = [
        name for name in holders if name in _HINT_FORMATS.get(suffix, ())
    ]
    if len(preferred) == 1:
        return SniffResult(
            preferred[0], tuple(holders),
            f"resolved to {preferred[0]} by the filename extension",
        )
    return SniffResult(
        None, tuple(holders),
        "this file matches both "
        + " and ".join(holders)
        + ", and HAIR will not guess",
    )


def _name_suffix(name_hint: str) -> str:
    name = (name_hint or "").strip().lower()
    dot = name.rfind(".")
    return name[dot:] if dot > 0 else ""


def sniff_format(text: str) -> str | None:
    """Identify a dropped file: the format name, or None.

    Kept as the one-argument answer both existing call sites want; the
    registry behind it is :func:`sniff`.
    """
    return sniff(text).format


def convert(text: str, name_hint: str = "") -> AdapterResult:
    """Route a non-wig file through its adapter."""
    result = sniff(text, name_hint)
    fmt = result.format
    if fmt is None and result.candidates:
        return AdapterResult(format="ambiguous", error=result.reason)
    if fmt in ("smartir_climate", "smartir_fork_climate"):
        return _convert_smartir_climate(text, fork=fmt.startswith("smartir_fork"))
    if fmt == "smartir":
        return _convert_smartir(text)
    if fmt == "flipper_library":
        return _refuse_flipper_library(text)
    if fmt == "flipper":
        return _convert_flipper(text, name_hint)
    if fmt == "lirc":
        return _convert_lirc(text, name_hint)
    if fmt == "girr":
        return _convert_girr(text, name_hint)
    return AdapterResult(format="unknown", error="not a recognized format")


# --- Broadlink packets (shared by SmartIR Base64/Hex; RMBridge later) ---


def broadlink_packet_to_pronto(packet: bytes) -> str | None:
    """Decode a Broadlink IR packet into Pronto hex, or None.

    Packet: 0x26 type byte (anything else, incl. RF 0xb2/0xd7, is
    refused), repeat byte, little-endian payload length, then tick
    durations (2^-15 s units; values >255 as 0x00 + big-endian pair),
    alternating mark/space starting with a mark. The trailing tick is
    almost always the Broadlink RM's own learning-mode capture
    timeout -- about 102ms, baked into 96% of the SmartIR climate
    corpus -- not part of the code; it broke 16-bit-limited emitters
    like Tuya/ZoSung, which reject anything over 65,535us
    (GH #93). Dropped here since 0.9.8, per smartir-trailing-gap.md:
    the source format says a trailing silence is meaningless on
    transmit, so removing it is a bit-identical waveform, not a
    different code.
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
    # SmartIR trailing gap (smartir-trailing-gap.md, 4b): ticks
    # alternate starting with a mark, so an EVEN-length list ends on a
    # space -- drop it before encoding so newly-converted wigs stop
    # storing the capture-timeout artifact (see the docstring above).
    # An odd-length list already ends on a mark; nothing to drop.
    # This only changes what NEW conversions produce -- existing
    # stored wigs and their hashes are untouched (owner-accepted
    # re-import hash split, smartir-trailing-gap.md 10.4).
    if len(ticks) % 2 == 0:
        ticks.pop()
    timings = [
        round(t * _BROADLINK_TICK_US) * (1 if idx % 2 == 0 else -1)
        for idx, t in enumerate(ticks)
    ]
    return raw_to_pronto(timings, frequency=38000)


def _broadlink_b64_to_pronto(code: str) -> str | None:
    # Padding salvage (SmartIR census, 2026-07-2x): about 1.7% of the
    # SmartIR corpus's Base64 cells are valid except for missing
    # trailing "=" padding, which some encoder once stripped. Appending
    # the padding the length demands rescues them; anything still
    # malformed fails exactly as before.
    cleaned = code.strip()
    if len(cleaned) % 4:
        cleaned += "=" * (-len(cleaned) % 4)
    try:
        packet = base64.b64decode(cleaned, validate=False)
    except (binascii.Error, ValueError):
        return None
    return broadlink_packet_to_pronto(packet)


# The public name for the shared Broadlink base64 entry point. The
# learned-code store reader (0.10.3) holds base64 exactly as SmartIR
# does, and both must produce one identity for one physical code, so it
# calls THIS function rather than re-implementing the tick constant, the
# escape handling or the trailing-gap strip. Aliased instead of renamed
# so the existing call sites in this module stay untouched.
broadlink_b64_to_pronto = _broadlink_b64_to_pronto


# --- SmartIR ---


def _humanize_key(key: str) -> str:
    """``volumeUp`` -> ``Volume Up``; ``level1`` -> ``Level 1``."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key)
    spaced = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", spaced)
    return spaced.replace("_", " ").strip().title() or key


def _smartir_code_to_pronto(
    code: str, encoding: str
) -> tuple[str | None, str | None]:
    """(pronto, failure_reason) for one SmartIR code value.

    A failure reason means the cell is SKIPPED with a receipt, never
    invented (the 0.8.8 rule). GH #108 is what happens when something
    unconvertible slips through as a code instead: the import looks like
    it worked and the damage surfaces later, somewhere else entirely.

    THE CONTAINER IS DETECTED BY CONTENT, NOT BY THE LABEL. A SmartIR
    file for an MQTT controller declares ``commandsEncoding: "Raw"`` and
    then carries a Tuya container, which is not a decimal timing list
    and not a Broadlink packet. Believing the label is what produced GH
    #108, so the Tuya reader is offered the value first: it either reads
    as that container or it does not, and if it does not the declared
    encoding takes over exactly as before.
    """
    encoding = (encoding or "").strip().lower()
    code = code.strip()
    # Tuya first, on content. It is cheap (a base64 decode that fails
    # closed, then an inflate that fails closed) and it is the only
    # reader that can tell this container from the text around it.
    if encoding in ("raw", "base64", "", "tuya"):
        tuya = tuya_b64_to_pronto(code)
        if tuya:
            return tuya, None
    if encoding == "base64":
        pronto = _broadlink_b64_to_pronto(code)
        if pronto is None:
            # Not Broadlink and not Tuya (tried above): out of readers.
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
        # "Raw" in SmartIR means a decimal timing list. It does NOT mean
        # "whatever bytes the controller happens to use", and the two
        # look nothing alike: a Tuya / UFO-R11 MQTT file carries base64
        # of a compressed timing stream under this same encoding name.
        # Scraping the digits out of base64 text and calling them
        # microseconds is how GH #108 produced 26 codes that parse as
        # Pronto and transmit nothing. A timing list is digits,
        # separators and signs; anything else is not one.
        if re.search(r"[A-Za-z+/=]", code):
            # The Tuya reader already had its turn above, so this is
            # encoded as something HAIR cannot read yet.
            return None, "not a decimal timing list (looks encoded)"
        values = re.findall(r"-?\d+", code)
        if len(values) < 4:
            return None, "raw list too short"
        timings = [int(v) for v in values]
        if not any(abs(t) for t in timings):
            return None, "no usable timings"
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
        send_count = 1
        if isinstance(value, list):
            unique = {v for v in value if isinstance(v, str)}
            if len(unique) == 1 and len(value) > 1:
                # The sequence repeats ONE code N times -- that is
                # exactly wig send_count, so the semantic survives
                # intact (e.g. SmartIR "Channel 11" = digit 1 twice).
                send_count = len(value)
                result.folds.append(
                    f"{alias}: {send_count} identical codes folded into "
                    f"send_count {send_count}"
                )
                value = value[0]
            else:
                # Genuinely different codes per press; wigs carry one
                # signal per button, so only the first code imports.
                result.skipped.append(
                    f"{alias}: multi-code sequence, imported first "
                    "code only"
                )
                value = value[0] if value else None
        if not isinstance(value, str) or not value.strip():
            result.skipped.append(f"{alias}: empty code")
            continue
        pronto, reason = _smartir_code_to_pronto(value, encoding)
        if pronto is None:
            result.skipped.append(f"{alias}: {reason}")
            continue
        signals.append(WigSignal(
            alias=alias, pronto=pronto, send_count=send_count,
            # Item 7 on this door too. A Pronto-encoded file states its
            # own carrier in the code's header word; every other
            # encoding this reader handles (Broadlink, Tuya, a decimal
            # timing list) carries no carrier at all, so the 38 kHz in
            # the code is HAIR's and the row says so.
            extra=_carrier_from_pronto(
                pronto,
                "declared" if encoding.strip().lower() == "pronto"
                else "assumed",
            ),
        ))
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


# --- SmartIR climate (Cold Cuts, v0.8.8) ---
#
# Climate files are precomputed state tables, not button lists:
# commands[mode][fan][swing?][temp] -> code, plus off/on and bounds.
# Flattening one yields hundreds of context-free rows (the refusal
# this adapter replaces); importing it as a STRUCTURED matrix keeps
# every cell named by its complete state. Census-driven rules
# (docs/internal/research/smartir-corpus-census.md, 358 files):
# depth detected per BRANCH (2320's dry subtree is itself mixed),
# "$"-prefixed keys filtered at every level, vocabulary verbatim
# (never _humanize_key on cells), Xiaomi "Raw" refused (proprietary
# blob), null/empty cells counted not fatal, and depth-0 extras
# (on_once, sleep, led...) become ordinary flat signals riding
# alongside the matrix.


def _is_temp_key(key: str) -> bool:
    try:
        float(key)
        return True
    except ValueError:
        return False


def _climate_flat_signal(alias: str, pronto: str, source: str = "assumed"):
    """One depth-0 button from a climate file, with its bypass decided.

    THE SAME ROUND-TRIP CHECK THE FLIPPER PATH USES. A code whose
    decoded triple cannot reproduce it is pinned to raw replay, which
    for a climate file's flat buttons is where a non-modulated code
    and any code whose encoder rounds differently both land.

    A matrix CELL needs no flag: the send path already refuses to
    re-encode anything carrying ``matrix_cell`` (GH #134), so a cell
    transmits its stored bytes whatever its decode says.
    """
    from .ir_command import ProntoCommand

    stamp = _carrier_from_pronto(pronto, source)
    try:
        timings = ProntoCommand(pronto).get_raw_timings()
    except (ValueError, IndexError, TypeError):
        return WigSignal(alias=alias, pronto=pronto, extra=stamp)
    return WigSignal(
        alias=alias,
        pronto=pronto,
        bypass_protocol=not _triple_reproduces(pronto, timings),
        extra=stamp,
    )


def _trim(value: float) -> str:
    """``1.0`` -> ``1``, ``0.5`` -> ``0.5``: a number in a receipt."""
    return f"{value:g}"


def _observed_precision(cells: list) -> float | None:
    """The finest temperature step these cells actually use, or None.

    None when there are fewer than two distinct temperatures, which is
    the case the plan names: below two there is nothing to measure and
    the declared value stands.
    """
    temps = sorted({c.temp for c in cells if c.temp is not None})
    if len(temps) < 2:
        return None
    steps = [
        round(b - a, 6) for a, b in itertools.pairwise(temps)
        if b > a
    ]
    return min(steps) if steps else None


def _convert_smartir_climate(text: str, fork: bool = False) -> AdapterResult:
    from .wig_climate import ha_mode_for
    from .wig_format import ClimateCell, ClimateExtra, ClimateMatrix

    result = AdapterResult(
        format="smartir_fork_climate" if fork else "smartir_climate"
    )
    data = json.loads(text)

    encoding = str(data.get("commandsEncoding") or "")
    controller = str(data.get("supportedController") or "").strip()
    if encoding.strip().lower() == "raw" and controller.lower() == "xiaomi":
        # Census: Xiaomi "Raw" is a base64-looking proprietary
        # compressed blob (miio), not decimal timings. ESPHome "Raw"
        # converts fine; the distinction is controller-keyed.
        result.error = (
            "this file's codes are in Xiaomi's proprietary compressed "
            "format, which HAIR cannot decode yet"
        )
        return result

    min_temp = data.get("minTemperature")
    max_temp = data.get("maxTemperature")
    if not isinstance(min_temp, (int, float)) \
            or not isinstance(max_temp, (int, float)) \
            or isinstance(min_temp, bool) or isinstance(max_temp, bool) \
            or float(min_temp) >= float(max_temp):
        result.error = "missing or invalid temperature bounds"
        return result
    precision = data.get("precision")
    if not isinstance(precision, (int, float)) or isinstance(precision, bool) \
            or float(precision) <= 0:
        precision = 1.0

    commands = data.get("commands")
    if not isinstance(commands, dict):
        result.error = "no commands object"
        return result

    cells: list[ClimateCell] = []
    signals: list[WigSignal] = []
    off_pronto: str | None = None
    on_pronto: str | None = None
    absent = 0  # null / empty cells: states the device does not have
    fail_counts: dict[str, int] = {}
    skipped_modes: list[str] = []

    def _cell_pronto(value: object) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            nonlocal absent
            absent += 1
            return None
        if not isinstance(value, str):
            fail_counts["not a string code"] = (
                fail_counts.get("not a string code", 0) + 1
            )
            return None
        pronto, reason = _smartir_code_to_pronto(value, encoding)
        if pronto is None:
            fail_counts[reason or "unconvertible"] = (
                fail_counts.get(reason or "unconvertible", 0) + 1
            )
            return None
        return pronto

    def _walk_temps(mode: str, fan: str | None, swing: str | None,
                    subtree: dict) -> None:
        for temp_key, value in subtree.items():
            if str(temp_key).startswith("$"):
                continue
            pronto = _cell_pronto(value)
            if pronto is None:
                continue
            cells.append(ClimateCell(
                mode=mode, fan=fan, swing=swing,
                temp=float(temp_key), pronto=pronto,
            ))

    def _deeper_than_upstream(node: object) -> str | None:
        """A branch the upstream walk has no name for, or None.

        The upstream shape is mode / fan / [swing] / temp. A dict
        sitting where a code belongs -- under the swing level -- is a
        level this file did not declare and the walk cannot name, and
        reading it as one of the levels it does know is exactly the
        silent mis-keying this work exists to stop. It is refused with
        the branch and the depth in the receipt.
        """
        for mode_key, mode_val in node.items():  # type: ignore[union-attr]
            if str(mode_key).startswith("$") or str(mode_key) in ("off", "on"):
                continue
            if not isinstance(mode_val, dict):
                continue
            # THE SAME SKIP THE WALK ITSELF APPLIES. A mode with no
            # Home Assistant word (ion, ifeel, money_saver) is skipped
            # with a receipt rather than read, so how deep its subtree
            # goes is not this check's business: judging it here
            # refused a whole file over a branch the converter would
            # never have opened.
            if ha_mode_for(str(mode_key)) is None:
                continue
            for fan_key, fan_val in mode_val.items():
                if not isinstance(fan_val, dict):
                    continue
                keys = [
                    k for k in map(str, fan_val) if not k.startswith("$")
                ]
                if keys and all(_is_temp_key(k) for k in keys):
                    continue
                for swing_key, swing_val in fan_val.items():
                    if not isinstance(swing_val, dict):
                        continue
                    deeper = [
                        k for k, v in swing_val.items()
                        if isinstance(v, dict)
                    ]
                    if deeper:
                        return (
                            f"{mode_key}/{fan_key}/{swing_key}/"
                            f"{deeper[0]} is five levels deep"
                        )
        return None

    def _walk_fan_value(mode: str, fan: str | None, value: object) -> None:
        # Below the fan level sits either temps (numeric keys) or a
        # swing layer (census: swing is between fan and temp in all 37
        # swing files) -- detected per BRANCH, never per file.
        if isinstance(value, dict):
            keys = [k for k in value if not str(k).startswith("$")]
            if keys and all(_is_temp_key(str(k)) for k in keys):
                _walk_temps(mode, fan, None, value)
                return
            for swing_key, sval in value.items():
                if str(swing_key).startswith("$") or not str(swing_key):
                    continue
                if isinstance(sval, dict):
                    _walk_temps(mode, fan, str(swing_key), sval)
                else:
                    pronto = _cell_pronto(sval)
                    if pronto is not None:
                        cells.append(ClimateCell(
                            mode=mode, fan=fan, swing=str(swing_key),
                            pronto=pronto,
                        ))
            return
        pronto = _cell_pronto(value)
        if pronto is not None:
            cells.append(ClimateCell(mode=mode, fan=fan, pronto=pronto))

    # THE FORK'S EXTRA LEVEL, NAMED FROM THE DECLARED LISTS.
    #
    # A fork climate file carries a preset level between the mode and
    # the fan, so its tree is four deep where an upstream file's is
    # three -- and an upstream file WITH swing is four deep too, with a
    # different meaning at each level. Depth cannot separate them; the
    # declared vocabulary can, and only it can. So every level below
    # the mode is named by testing its keys against ``presetModes``,
    # then ``fanModes``, then ``swingModes``, then the numeric test for
    # temperatures, and a level whose keys match none of them is
    # refused with a receipt rather than read as whatever sits at that
    # depth in some other file.
    declared: dict[str, set[str]] = {}
    for axis, source_key in (
        ("preset", "presetModes"),
        ("fan", "fanModes"),
        ("swing", "swingModes"),
    ):
        values = data.get(source_key)
        declared[axis] = {
            str(v) for v in values if str(v).strip()
        } if isinstance(values, list) else set()

    # READ ONLY AS A LIST OF STRINGS, and anything else is absent with
    # a receipt. The comprehension this replaces iterated the value
    # before checking its type, so a scalar raised TypeError out of
    # ``convert`` at an upload handler that has no try/except, and a
    # string iterated into single characters and mis-keyed silently.
    raw_presets = data.get("presetModes")
    preset_order: list[str] = []
    if isinstance(raw_presets, list):
        preset_order = [
            str(v) for v in raw_presets
            if isinstance(v, str) and v.strip()
        ]
        if len(preset_order) != len(raw_presets):
            result.folds.append(
                "presetModes: entries that are not names were ignored"
            )
    elif raw_presets is not None:
        result.folds.append(
            "presetModes is not a list of names, so it was read as absent"
        )
    # The main lattice takes the first declared preset; the rest become
    # extra lattices. An empty main lattice would make every fork wig
    # hash as the same empty matrix at the upload door, which is the
    # collision the matrix-wig hash already learned about once.
    # CHOSEN AFTER THE WALK, not from the declared list. A file may
    # declare a preset its code tree does not carry -- a neutral name
    # offered for Home Assistant's benefit, or simply a stale list --
    # and taking the declared first meant the main lattice came out
    # empty and a file full of convertible cells was refused as having
    # none. The walk files every preset's cells; the promotion below
    # picks the first declared preset that actually has some.
    main_preset: str | None = None
    preset_cells: dict[str, list[ClimateCell]] = {}

    def _level_axis(keys: list[str]) -> str | None:
        """What this level is, from what the file declared it to be."""
        if keys and all(_is_temp_key(k) for k in keys):
            return "temp"
        names = set(keys)
        for axis in ("preset", "fan", "swing"):
            if declared[axis] and names <= declared[axis]:
                return axis
        return None

    # mode / preset / fan / swing / temp is five, and the cap is one
    # more, so a shape this reader can actually name always fits. Past
    # it the walk stops with a receipt instead of recursing until the
    # interpreter raises out of an upload handler that cannot catch it.
    fork_depth_cap = 6

    def _walk_fork(
        mode: str, preset: str | None, fan: str | None,
        swing: str | None, node: object, path: str, depth: int = 1,
    ) -> None:
        """One branch of a fork tree, level by declared level."""
        if depth > fork_depth_cap:
            reason = (
                f"{path} is more than {fork_depth_cap} levels deep; the "
                "rest of that branch was not read"
            )
            fail_counts[reason] = fail_counts.get(reason, 0) + 1
            return
        if not isinstance(node, dict):
            pronto = _cell_pronto(node)
            if pronto is not None:
                _place(mode, preset, fan, swing, None, pronto)
            return
        keys = [k for k in map(str, node) if not k.startswith("$") and k]
        axis = _level_axis(keys)
        if axis is None:
            fail_counts[
                f"level under {path} names none of the declared lists "
                f"({', '.join(sorted(keys)[:4])})"
            ] = fail_counts.get(
                f"level under {path} names none of the declared lists "
                f"({', '.join(sorted(keys)[:4])})", 0
            ) + 1
            return
        for raw_child, child in node.items():
            child_key = str(raw_child)
            if child_key.startswith("$") or not child_key:
                continue
            if axis == "temp":
                pronto = _cell_pronto(child)
                if pronto is not None:
                    _place(
                        mode, preset, fan, swing, float(child_key), pronto
                    )
                continue
            _walk_fork(
                mode,
                child_key if axis == "preset" else preset,
                child_key if axis == "fan" else fan,
                child_key if axis == "swing" else swing,
                child,
                f"{path}/{child_key}",
                depth + 1,
            )

    def _place(
        mode: str, preset: str | None, fan: str | None,
        swing: str | None, temp: float | None, pronto: str,
    ) -> None:
        """File one cell, in the main lattice or in a preset's own."""
        cell = ClimateCell(
            mode=mode, fan=fan, swing=swing, temp=temp, pronto=pronto,
        )
        if preset is None:
            # A branch with no preset level at all belongs to the main
            # lattice whichever preset is promoted.
            cells.append(cell)
            return
        preset_cells.setdefault(preset, []).append(cell)

    if not fork:
        deeper = _deeper_than_upstream(commands)
        if deeper is not None:
            result.error = (
                f"this file has a level HAIR cannot name: {deeper}. A "
                "climate file whose branches go deeper than mode, fan, "
                "swing and temperature has to say what the extra level "
                "is (the fork schema names it with presetModes); reading "
                "it as one of the levels HAIR does know would store the "
                "wrong state on every cell"
            )
            return result

    for raw_key, value in commands.items():
        key = str(raw_key)
        if key.startswith("$") or not key:
            continue
        if key == "off":
            off_pronto = _cell_pronto(value)
            continue
        if key == "on":
            on_pronto = _cell_pronto(value)
            continue
        if ha_mode_for(key) is None:
            if isinstance(value, dict):
                # A real lattice under a mode HA has no word for
                # (ion, ifeel, money_saver...): skip with receipt.
                skipped_modes.append(key)
                continue
            # Depth-0 extras (on_once, sleep, led, swing, clean...)
            # are ordinary one-shot buttons -- route them into the
            # flat signal list (census second pass).
            pronto = _cell_pronto(value)
            if pronto is not None:
                signals.append(_climate_flat_signal(
                    _humanize_key(key), pronto,
                    "declared" if encoding.strip().lower() == "pronto"
                    else "assumed",
                ))
            continue
        if fork:
            _walk_fork(key, None, None, None, value, key)
        elif isinstance(value, dict):
            for fan_key, fval in value.items():
                if str(fan_key).startswith("$") or not str(fan_key):
                    continue
                _walk_fan_value(key, str(fan_key), fval)
        else:
            _walk_fan_value(key, None, value)

    def _emit_receipts() -> None:
        """Every receipt the walk gathered, before any answer.

        BEFORE EVERY EARLY RETURN, not only the last one. Both refusals
        below used to return with ``fail_counts``, ``absent`` and
        ``skipped_modes`` still in hand, so the five-level fork case
        reported "no convertible state cells in this file" and an empty
        skipped list -- the file said nothing about why, and neither
        did HAIR.
        """
        for reason, count in sorted(fail_counts.items()):
            result.skipped.append(f"{count} cells: {reason}")
        if absent:
            result.skipped.append(
                f"{absent} absent states (null or empty cells) skipped"
            )
        for mode in skipped_modes:
            result.skipped.append(
                f'mode "{mode}": no Home Assistant equivalent, subtree '
                "skipped"
            )

    if fork:
        main_preset = next(
            (key for key in preset_order if preset_cells.get(key)), None
        )
        if main_preset is not None:
            cells.extend(preset_cells.pop(main_preset))
        for key in preset_order:
            if not preset_cells.get(key) and key != main_preset:
                result.folds.append(
                    f'preset "{key}" is declared but carries no cells'
                )

    if off_pronto is None:
        _emit_receipts()
        result.error = 'no convertible "off" code (every climate file needs one)'
        return result
    if not cells:
        _emit_receipts()
        result.error = "no convertible state cells in this file"
        return result

    # Vocabulary lists: observed order, with the file's declared lists
    # (advisory, census anomaly finding) providing the preferred order.
    def _ordered(declared: object, observed: list[str]) -> list[str]:
        declared_list = [
            str(v) for v in declared
        ] if isinstance(declared, list) else []
        ordered = [v for v in declared_list if v in observed]
        ordered += [v for v in observed if v not in ordered]
        return ordered

    obs_modes: list[str] = []
    obs_fans: list[str] = []
    obs_swings: list[str] = []
    for cell in cells:
        if cell.mode not in obs_modes:
            obs_modes.append(cell.mode)
        if cell.fan is not None and cell.fan not in obs_fans:
            obs_fans.append(cell.fan)
        if cell.swing is not None and cell.swing not in obs_swings:
            obs_swings.append(cell.swing)

    # No unit is set: the format default "C" IS the SmartIR convention
    # (their climate corpus is Celsius throughout; owner ruling
    # 2026-07-29 rejected detection heuristics -- a file that "looks
    # Fahrenheit" is a hand-edit problem, not an import guess).
    # THE DECLARED PRECISION, KEPT UNLESS IT CANNOT BE TRUE.
    #
    # A matrix declaring 0.1 over whole-degree cells makes the comb
    # invent twenty-seven missing temperatures spelled with float drift.
    # But demoting on any mismatch is worse: a real half-degree device
    # whose observed temperatures happen to be whole would lose its
    # step, and the comb would stop reporting the half-degree holes it
    # exists to report. So the rule is one-sided -- a declared value is
    # kept unless it is FINER than the spacing the cells actually show
    # by more than one step of itself -- and the result never goes
    # below the finest spacing observed.
    # AND NEVER COARSER THAN A WHOLE DEGREE. A sparse lattice carrying
    # 16, 22 and 30 shows a six-degree spacing and is not a device that
    # steps by six: those are holes, and reporting them is the comb's
    # job. Demoting there would silence the comb in exactly the way the
    # review warned about for half-degree files, so the demotion stops
    # at 1.0 and a declared whole degree is never rewritten.
    observed = _observed_precision(cells)
    stored_precision = float(precision)
    if observed is not None and observed - stored_precision > stored_precision:
        demoted = min(observed, 1.0)
        if demoted > stored_precision:
            stored_precision = demoted
            # A FOLD, NOT A SKIP. ``skipped`` is rows that did not
            # convert, and the panel counts it: "{count} signals could
            # not convert". Every cell converted here; one number was
            # rewritten, which is what ``folds`` is for.
            result.folds.append(
                f"declared precision {_trim(precision)} is finer than the "
                f"{_trim(observed)} step these cells actually use; stored "
                f"as {_trim(demoted)}"
            )

    matrix = ClimateMatrix(
        min_temp=float(min_temp),
        max_temp=float(max_temp),
        precision=stored_precision,
        modes=_ordered(data.get("operationModes"), obs_modes),
        fan_modes=_ordered(data.get("fanModes"), obs_fans),
        swing_modes=_ordered(data.get("swingModes"), obs_swings),
        off=off_pronto,
        on=on_pronto,
        cells=cells,
        extras=[
            ClimateExtra(axis="preset", key=key, cells=preset_cells[key])
            for key in preset_order
            if preset_cells.get(key)
        ],
    )
    if matrix.extras:
        result.folds.append(
            f'preset "{main_preset}" read as the main lattice; '
            f"{len(matrix.extras)} other preset(s) kept as extra lattices"
        )
        # A MODE THAT EXISTS ONLY UNDER A SECONDARY PRESET LEAVES THE
        # MODE LIST, AND IS SAID SO. The climate entity is built from
        # the main lattice, so a file whose heating codes live only
        # under an eco preset yields a cooling-only entity. The codes
        # are in the file, inside the digest, and the device detail
        # grid can reach them later; what must not happen is the mode
        # disappearing without a word. Not a promotion: promoting one
        # mode out of an extra lattice would mix two presets into one
        # entity and send the wrong state.
        reported: set[str] = set(matrix.modes)
        for extra in matrix.extras:
            for mode in dict.fromkeys(c.mode for c in extra.cells):
                if mode in reported:
                    continue
                reported.add(mode)  # named once, not once per preset
                result.folds.append(
                    f'mode "{mode}" is only under preset "{extra.key}"; it '
                    "is kept as an extra lattice and is not on the climate "
                    "entity"
                )

    _emit_receipts()

    manufacturer = str(data.get("manufacturer") or "").strip()
    models = data.get("supportedModels") or []
    model = str(models[0]).strip() if models else ""
    name = " ".join(part for part in (manufacturer, model) if part) \
        or "SmartIR Climate Import"
    result.wigs.append(Wig(
        name=name,
        signals=signals,
        brand=manufacturer or None,
        model=model or None,
        kind="ac",
        notes=(
            f"Imported from SmartIR climate ({controller} / {encoding}); "
            f"{len(cells)} states"
        ),
        origin="converted:smartir",
        climate=matrix,
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

    # --- the NEC-family block -------------------------------------------
    #
    # LOCAL CLASSES, SO THESE WORK ON BOTH LEGS. Everything above is
    # feature-detected against ``infrared_protocols`` and disappears when
    # the library is absent; everything here is in this package, so a
    # Flipper file carrying these protocols converts either way. Imported
    # directly rather than through ``protocol_decode.get_spec`` because
    # two of the four classes are deliberately unregistered and a builder
    # table that reached into the registry would not find them.
    from .decoders.nec42 import NEC42Command, NEC42ExtCommand
    from .decoders.nec_variant import NECNoComplementCommand

    # NECext: 16-bit address, and the command field is the THIRD AND
    # FOURTH WIRE BYTES AS WRITTEN, not a command whose complement is
    # re-derived.
    #
    # This used to build ``NECCommand(address=a & 0xFFFF, command=c &
    # 0xFF)``, which threw the file's fourth byte away and wrote the
    # complement of the third in its place. For an ordinary remote that
    # is the same frame and nobody noticed. For an Apple remote the
    # fourth byte is the pairing id, so HAIR stored a Pronto the remote
    # never sends: the repo's own Apple fixture carries pairing id 0x2E
    # and was being rendered with 0xFD.
    #
    # Where the file's fourth byte IS the complement of its third, the
    # wire is byte-identical to what this built before -- the verbatim
    # class carries upstream's exact NEC timing constants for that
    # reason, and a test asserts the Pronto string does not move.
    #
    # ONE CASE DOES CHANGE BESIDES THE NON-COMPLEMENT ONE. Upstream
    # treats an address of 0xFF or less as a standard 8-bit NEC address
    # and emits its complement as the second byte. A file that says
    # ``NECext`` and gives a low address means the two bytes it wrote,
    # so they go out as written and that file's Pronto moves. The
    # stored Pronto alone would not have been enough: the row decodes to
    # a 16-bit NEC address the NEC encoder re-complements on send, which
    # is why ``_triple_reproduces`` marks such a row bypass.
    builders["NECext"] = lambda a, c: NECNoComplementCommand(
        address=a & 0xFFFF, command=c & 0xFFFF
    )

    # The 42-bit family. NO MASKS: these check and let the class refuse.
    # A mask invents a code -- it silently turns an address the file
    # could not have meant into one HAIR will happily transmit -- and
    # the refusal lands in ``result.skipped`` with the range in it, so
    # the person is told which row was dropped and why. The entries
    # above keep their masks because changing them would move existing
    # imports.
    builders["NEC42"] = lambda a, c: NEC42Command(address=a, command=c)
    builders["NEC42ext"] = lambda a, c: NEC42ExtCommand(address=a, command=c)

    # Pioneer buys one thing an air capture cannot: the 40 kHz carrier
    # and the tighter leader, carried into the stored Pronto through the
    # command's ``modulation``. The row's decoded identity still comes
    # from re-decoding that Pronto, which lands on NEC, because HAIR
    # cannot tell Pioneer from NEC without the carrier and does not
    # pretend to. See ``decoders/pioneer.py``.
    #
    # THE FILE CARRIES EIGHT BITS OF EACH, AND THE COMPLEMENTS ARE
    # IMPLIED. A Flipper ``Pioneer`` line is written by a decoder that
    # reads an 8-bit address, an 8-bit command and their two inverse
    # bytes, refuses the frame unless both inverses hold, and records
    # only the two payload bytes. So ``address: A5 00 00 00`` means the
    # wire ``A5 5A`` and ``command: 1E 00 00 00`` means ``1E E1``. The
    # first cut of this builder took both fields as sixteen verbatim
    # bits and rendered ``A5 00 1E 00``, a frame no Pioneer accepts and
    # no decoder here claims (review round 2, finding 1). The two bytes
    # are expanded here, and a value with bits above eight is refused by
    # name rather than masked, for the same reason the 42-bit entries
    # above carry no masks.
    builders["Pioneer"] = _build_pioneer

    # --- the Manchester and RCA block (import phase 1) ----------------
    #
    # THROUGH THE REGISTRY, NOT THROUGH THE LIBRARY. These three resolve
    # their class with ``get_spec``, which answers with whichever
    # implementation is registered: upstream ships no RC-6 and no RCA,
    # so those are this package's own decoders, and they are real
    # encoders. A Flipper file carrying these lines therefore converts
    # with or without the optional library installed, which the block
    # above already established for the NEC family.
    #
    # WIDTHS ARE THE FIRMWARE'S, AND EACH IS CHECKED RATHER THAN MASKED.
    # A mask invents a code: it turns a value the file could not have
    # meant into one HAIR will happily transmit. A value too wide for
    # its field raises here and lands in ``result.skipped`` naming the
    # row, which is what the person needs to see.
    #
    # Kaseikyo is NOT here. Its Flipper address is a packed 26-bit
    # composite (an id, a 16-bit vendor, two 4-bit genre nibbles) and
    # the firmware's own files disagree about whether the command is 10
    # or 12 bits wide, while this package's class takes a vendor
    # address and payload BYTES. That mapping cannot be confirmed from
    # the firmware as it stands, so the entry is not added and the
    # honest "not encodable yet" receipt stays.
    def _rc6(address: int, command: int):
        # Flipper's RC6: address 8 bits, command 8 bits, and its encoder
        # writes mode 0 only. The toggle is pinned to 0 for the same
        # reason the LIRC reader pins it: a wig holds one Pronto per
        # button and the toggle flips per press.
        cls = _registry_class("RC6")
        if cls is None:
            raise ValueError("no RC-6 encoder is registered")
        _check_width("RC6 address", address, 0xFF)
        _check_width("RC6 command", command, 0xFF)
        return cls(address=address, command=command, mode=0, toggle=0)

    def _rc5x(address: int, command: int):
        # Flipper's RC5X: address 5 bits, command 7 bits. NOT the RC5
        # entry's ``& 0x3F``: this package's class spends the second
        # start bit on command bit 6, so 0x40..0x7F is exactly what
        # RC5X means and a six-bit mask cannot express it.
        cls = _registry_class("RC5")
        if cls is None:
            raise ValueError("no RC-5 encoder is registered")
        _check_width("RC5X address", address, 0x1F)
        _check_width("RC5X command", command, 0x7F)
        return cls(address=address, command=command, toggle=0)

    def _rca(address: int, command: int):
        # Flipper's RCA: address 4 bits, command 8 bits, with both
        # complements derived by the encoder.
        cls = _registry_class("RCA")
        if cls is None:
            raise ValueError("no RCA encoder is registered")
        _check_width("RCA device", address, 0xF)
        _check_width("RCA function", command, 0xFF)
        return cls(device=address, function=command)

    builders["RC6"] = _rc6
    builders["RC5X"] = _rc5x
    builders["RCA"] = _rca

    return builders


def _registry_class(label: str):
    """The registered command class for a decoded label, or None."""
    from .protocol_decode import get_spec

    spec = get_spec(label)
    return None if spec is None else spec.command_cls


def _check_width(what: str, value: int, limit: int) -> None:
    """Refuse a field the file could not have meant, by name."""
    if not 0 <= value <= limit:
        raise ValueError(
            f"{what} {value:#x} is wider than the {limit.bit_length()} "
            "bits a Flipper line carries for it"
        )


def _build_pioneer(address: int, command: int):
    """A Flipper ``Pioneer`` line to the 32-bit frame it stands for."""
    from .decoders.pioneer import PioneerCommand

    if not 0 <= address <= 0xFF:
        raise ValueError(
            f"Pioneer address {address:#x} is wider than the 8 bits a "
            "Flipper Pioneer line carries"
        )
    if not 0 <= command <= 0xFF:
        raise ValueError(
            f"Pioneer command {command:#x} is wider than the 8 bits a "
            "Flipper Pioneer line carries"
        )
    return PioneerCommand(
        address=address | ((~address & 0xFF) << 8),
        command=command | ((~command & 0xFF) << 8),
    )


def _carrier_for(
    declared_hz: int | None, protocol_hz: int | None = None
) -> tuple[int, str]:
    """``(carrier, source)`` for one row, and where the number came from.

    ``declared`` is the file's own value, ``protocol`` an encoder's
    nominal, ``assumed`` HAIR's 38 kHz fallback, and ``none`` a code
    that carries no carrier at all. Every reader in import phase 1 goes
    through here so the four answers are spelled one way.
    """
    if declared_hz is not None:
        return (int(declared_hz), "none" if declared_hz == 0 else "declared")
    if protocol_hz:
        return (int(protocol_hz), "protocol")
    return (38000, "assumed")


def _carrier_extra(carrier: int, source: str) -> dict:
    """The per-signal carrier stamp.

    Rides ``WigSignal.extra``, which round trips through ``_KNOWN_SIGNAL``
    and is excluded from ``canonical_signals_json``, so this is additive
    and outside every digest: a wig written before this carries no
    stamp and hashes exactly as it did.
    """
    return {"carrier": {"hz": carrier, "source": source}}


def _carrier_from_pronto(pronto: str, source: str) -> dict:
    """The stamp for a row whose carrier is already inside its code.

    A Pronto's header word IS a carrier statement, so a file that wrote
    the Pronto stated it (``declared``) and a code HAIR built at its own
    default did not (``assumed``). A ``0100`` code states that there is
    no carrier at all, which reads as ``none`` whoever wrote it.
    """
    from .ir_command import ProntoCommand

    try:
        command = ProntoCommand(pronto)
    except (ValueError, IndexError, TypeError):
        return {}
    if command.unmodulated:
        return _carrier_extra(0, "none")
    return _carrier_extra(int(command.modulation or 0), source)


def _int_or_none(value: object) -> int | None:
    """A declared number, or None when the file declared nothing.

    The import readers distinguish "the file says 0" from "the file
    says nothing" from here on, because zero is a carrier that means no
    carrier and the two answers are not the same (item 6). Anything
    that will not read as a number is None: an unreadable value is an
    absent one for this purpose, and the row still converts.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _flipper_bytes_value(raw: str) -> int:
    """``"4F 50 00 00"`` (little-endian bytes) -> 0x504F."""
    parts = raw.split()
    value = 0
    for i, part in enumerate(parts):
        value |= int(part, 16) << (8 * i)
    return value


def _triple_reproduces(pronto: str, timings: list[int]) -> bool:
    """Would the send path's re-encode put these bytes on the air?

    THE DECODE-TRUST RULE, APPLIED AT THE IMPORT DOOR. HAIR transmits a
    decodable row from its decoded triple, not from its stored code. A
    file can state bytes the encoder for that triple does not
    reproduce: a ``NECext`` line whose address is 0xFF or less decodes
    to a 16-bit NEC address, and the NEC encoder treats any address
    that small as 8-bit and writes its complement as the second byte,
    so ``04 00 08 F7`` in the file would go out as ``04 FB 08 F7``
    (review round 2, finding 2). The same rule covers the other cases
    where a rendering outruns the encoders: a non-complement fourth
    byte, and a Pioneer line whose 40 kHz Pronto the NEC encoder would
    rebuild at 38 kHz with NEC's own timings.

    So every rendered row is checked the way a capture is checked at
    mint: decode it, re-encode the triple, compare the Pronto strings.
    A row the triple cannot reproduce is stored with ``bypass_protocol``
    set, so the air carries the bytes the file wrote. A row nothing
    decodes needs no bypass, because there is no triple to re-encode
    from and the send path already replays it.
    """
    from .ir_command import build_decoded_command
    from .protocol_decode import try_decode_identity

    try:
        identity = try_decode_identity(list(timings))
    except Exception:
        return True
    if identity is None:
        return True
    rebuilt = build_decoded_command(
        identity.protocol,
        identity.address,
        identity.command,
        decoded_extras=dict(identity.extras) if identity.extras else None,
    )
    if rebuilt is None:
        return True
    modulation = carrier_or_default(getattr(rebuilt, "modulation", None))
    return raw_to_pronto(
        list(rebuilt.get_raw_timings()), frequency=modulation
    ) == pronto


def _refuse_flipper_library(text: str) -> AdapterResult:
    """A Flipper universal library file, refused by name.

    These are the firmware's shotgun files -- ``tv.ir``, ``ac.ir``,
    ``audio.ir``, ``projector.ir`` -- one per device type, carrying the
    same six or so buttons for hundreds of models, walked in full by
    the Flipper's own Universal Remote feature. They are a database,
    and a database lookup is not what a wig is: a wig is one remote.

    The refusal names what the file is and what to do with it, because
    a person who dropped one has a reasonable question. The count comes
    from the ``# Model:`` markers when the file carries them; the file
    is refused either way.
    """
    models = len(re.findall(r"^#\s*Model:", text, re.MULTILINE))
    counted = f" ({models} models)" if models else ""
    return AdapterResult(
        format="flipper_library",
        error=(
            f"this is a Flipper universal remote library{counted}, not a "
            "single remote. HAIR imports one remote per file. Copy the "
            "block for your model into its own file with "
            f"'{FLIPPER_REMOTE_HEADER}' at the top and drop that."
        ),
    )


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
            declared_hz = _int_or_none(current.get("frequency"))
            frequency, source = _carrier_for(declared_hz)
            timings = [
                v if i % 2 == 0 else -v for i, v in enumerate(values)
            ]
            signals.append(WigSignal(
                alias=name,
                pronto=raw_to_pronto(timings, frequency=frequency),
                extra=_carrier_extra(frequency, source),
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
                modulation, source = _carrier_for(
                    None, _int_or_none(getattr(command, "modulation", None))
                )
                pronto = raw_to_pronto(timings, frequency=modulation)
                signals.append(WigSignal(
                    alias=name,
                    pronto=pronto,
                    bypass_protocol=not _triple_reproduces(pronto, timings),
                    extra=_carrier_extra(modulation, source),
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
    # The file's own carrier, or None when it declares none. Item 7:
    # the reader records which of those it was rather than spelling a
    # silent 38000 the file never said.
    declared_hz = _int_or_none((params.get("frequency") or [None])[0])
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
            carrier, source = _carrier_for(declared_hz)
            pronto = raw_to_pronto(timings, frequency=carrier)
            signals.append(WigSignal(
                alias=name,
                pronto=pronto,
                bypass_protocol=not _triple_reproduces(pronto, timings),
                extra=_carrier_extra(carrier, source),
            ))
    else:
        codes_section = re.search(
            r"begin codes(.*?)end codes", block, re.DOTALL | re.IGNORECASE
        )
        if codes_section is None:
            result.skipped.append(f"{remote_name}: no codes section")
            return None
        if "RC5" in flags or "SHIFT_ENC" in flags or "RC6" in flags:
            signals.extend(_convert_lirc_manchester(
                params, codes_section.group(1), remote_name, flags,
                declared_hz, result,
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
            carrier, source = _carrier_for(declared_hz)
            pronto = raw_to_pronto(timings, frequency=carrier)
            signals.append(WigSignal(
                alias=_humanize_key(name.removeprefix("KEY_").lower()),
                pronto=pronto,
                bypass_protocol=not _triple_reproduces(pronto, timings),
                extra=_carrier_extra(carrier, source),
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


# --- LIRC RC-5 and RC-6, through this package's own encoders ---------
#
# A block with the RC5, SHIFT_ENC or RC6 flag states its codes as a
# NUMBER, not as a pulse train, and until now HAIR refused it as "not
# reconstructable". Both encoders have been in ``decoders/`` all along;
# what was missing was the mapping from the file's fields onto them.
#
# WHAT THE OBJECT IS. ``lircd.conf(5)`` gives the frame as
# ``header | plead | pre data | pre | data | post | post data | ptrail |
# foot | gap`` and says the toggle mask "is applied to the concatenated
# value of pre data - data - post_data". So the word these readers split
# is that concatenation, MSB first, of width
# ``pre_data_bits + bits + post_data_bits``.
#
# RECONSTRUCTED FROM THE PROTOCOL, NOT FROM THE FILE'S NUMBERS. The
# timings come from the encoders' canonical units (889 us half-bits for
# RC-5, 444 us units for RC-6), not from the block's measured ``one`` /
# ``zero`` / ``plead``, exactly as the Flipper parsed path already
# rebuilds from parameters. The receipt says so.
#
# THE TOGGLE IS PINNED TO 0 AND THE RECEIPT SAYS SO. A wig holds one
# Pronto per button and the toggle flips per press, so there is no
# "the" toggle to preserve; ``decoders/rc5.py`` states that callers
# must keep it out of identity, and both extractors put it in extras
# rather than in the fingerprint suffix.


class LircManchesterError(ValueError):
    """A block this reader will not guess at, with the reason."""


def _lirc_word(params: dict) -> tuple[int, int]:
    """``(value, width)`` for the pre_data|code|post_data concatenation.

    Returns the width alone here; the code is folded in per row.
    """
    pre_bits = int((params.get("pre_data_bits") or ["0"])[0])
    post_bits = int((params.get("post_data_bits") or ["0"])[0])
    bits = int((params.get("bits") or ["0"])[0])
    return (pre_bits, bits, post_bits)


def _lirc_concat(params: dict, code: int) -> tuple[int, int]:
    """The whole word and its width, for one row's code."""
    pre_bits, bits, post_bits = _lirc_word(params)
    pre_values = params.get("pre_data")
    post_values = params.get("post_data")
    pre = int(pre_values[0], 0) if pre_values else 0
    post = int(post_values[0], 0) if post_values else 0
    width = pre_bits + bits + post_bits
    value = 0
    if pre_bits:
        value = pre & ((1 << pre_bits) - 1)
    value = (value << bits) | (code & ((1 << bits) - 1))
    if post_bits:
        value = (value << post_bits) | (post & ((1 << post_bits) - 1))
    return value, width


def _toggle_position(params: dict, width: int) -> int | None:
    """Which bit from the MSB the file says the toggle is, or None.

    ``toggle_bit_mask`` first, because it is unambiguous: a mask over
    the concatenated word. ``toggle_bit`` second, which ``lircd.conf(5)``
    documents as one-based from the most significant bit. ``rc6_mask``
    is NOT read: it is absent from the man page, 21 of the 86 native
    RC-6 blocks do not carry it (including the database's own generic
    template), and every one of those says the same thing with
    ``toggle_bit``.
    """
    mask_values = params.get("toggle_bit_mask")
    if mask_values:
        mask = int(mask_values[0], 0)
        if mask and mask.bit_count() == 1:
            return width - mask.bit_length()
    bit_values = params.get("toggle_bit")
    if bit_values:
        one_based = int(bit_values[0], 0)
        if 1 <= one_based <= width:
            return one_based - 1
    return None


def _lirc_rc5_fields(params: dict, code: int) -> tuple[int, int]:
    """``(address, command)`` for one RC-5 row, or raise.

    W is the concatenation's width. 13 is the common shape, S1 riding as
    ``plead`` and the reconstruction supplying it; 14 carries S1 in the
    word and it must read 1. S2 is the RC5X bit: 0 folds command bit 6
    on, which is exactly the inverse of what ``decoders/rc5.py`` does on
    encode.
    """
    _pre_bits, _bits, post_bits = _lirc_word(params)
    if post_bits:
        raise LircManchesterError(
            "RC-5 with post_data is not read: the command bits cannot be "
            "told from the trailing field"
        )
    value, width = _lirc_concat(params, code)
    if width == 14:
        if (value >> 13) & 1 != 1:
            raise LircManchesterError(
                "14-bit RC-5 word whose first start bit reads 0"
            )
        value &= (1 << 13) - 1
    elif width != 13:
        raise LircManchesterError(
            f"RC-5 word is {width} bits; this reader knows 13 and 14"
        )
    start2 = (value >> 12) & 1
    address = (value >> 6) & 0x1F
    command = value & 0x3F
    if not start2:
        command |= 0x40
    return address, command


def _lirc_rc6_fields(params: dict, code: int) -> tuple[dict, list[str]]:
    """RC-6 constructor kwargs for one row, plus any receipt notes.

    THE LIRC WORD IS THE BITWISE COMPLEMENT of the logical RC-6 bits.
    Derived rather than assumed, and every native block the review
    checked agrees: complementing the concatenation gives a leading 1
    on all of them but one, which is mode 15 and is refused on mode
    anyway.
    Reading the word uncomplemented gives a leading 0, which RC-6 does
    not permit.

    Layout after complementing, MSB first: S:1, mode:3, trailer:1, then
    the payload. Mode 6's customer field states its own width with its
    first bit, which is what ``decoders/rc6.py`` reads, so the width is
    taken from the field and never from W.
    """
    value, width = _lirc_concat(params, code)
    if width == 25:
        raise LircManchesterError(
            "RC-6-6-20 (a 25-bit word) is a documented deferral in this "
            "package's RC-6 decoder"
        )
    if width not in (21, 29, 37):
        raise LircManchesterError(
            f"RC-6 word is {width} bits; this reader knows 21, 29 and 37"
        )
    word = (~value) & ((1 << width) - 1)
    if (word >> (width - 1)) & 1 != 1:
        raise LircManchesterError(
            "RC-6 start bit reads 0 after complementing the word"
        )
    mode = (word >> (width - 4)) & 0b111
    if mode not in (0, 6):
        raise LircManchesterError(f"RC-6 mode {mode} is not read")
    trailer = (word >> (width - 5)) & 1
    notes: list[str] = []
    if _toggle_position(params, width) is None:
        notes.append(
            "the block names no toggle bit, so the trailer position was "
            "assumed to be it"
        )
    rest_bits = width - 5
    rest = word & ((1 << rest_bits) - 1)
    if mode == 0:
        if rest_bits != 16:
            raise LircManchesterError(
                f"RC-6 mode 0 payload is {rest_bits} bits, expected 16"
            )
        return (
            {"address": (rest >> 8) & 0xFF, "command": rest & 0xFF,
             "mode": 0, "toggle": 0},
            notes,
        )
    # Mode 6. The customer field's first bit gives its width, then one
    # toggle bit, then a 7-bit device and an 8-bit function.
    if trailer:
        raise LircManchesterError(
            "RC-6 mode 6 with a set trailer is not submode 6A"
        )
    lead = (rest >> (rest_bits - 1)) & 1
    customer_bits = 16 if lead else 8
    if rest_bits < customer_bits + 16:
        raise LircManchesterError(
            f"RC-6 mode 6 word is {rest_bits} bits after the header, too "
            f"short for a {customer_bits}-bit customer field"
        )
    customer = (rest >> (rest_bits - customer_bits)) & (
        (1 << customer_bits) - 1
    )
    remainder_bits = rest_bits - customer_bits
    if remainder_bits != 16:
        raise LircManchesterError(
            f"RC-6 mode 6 remainder is {remainder_bits} bits, expected 16"
        )
    remainder = rest & 0xFFFF
    return (
        {
            "address": (remainder >> 8) & 0x7F,
            "command": remainder & 0xFF,
            "mode": 6,
            "toggle": 0,
            "customer": customer,
        },
        notes,
    )


def _convert_lirc_manchester(
    params: dict, codes_section: str, remote_name: str,
    flags: str, declared_hz: int | None, result: AdapterResult,
) -> list[WigSignal]:
    """Every row of an RC-5 or RC-6 block, or an empty list."""
    is_rc6 = "RC6" in flags
    label = "RC-6" if is_rc6 else "RC-5"
    cls = _registry_class("RC6" if is_rc6 else "RC5")
    if cls is None:
        result.skipped.append(
            f"{remote_name}: no {label} encoder is registered"
        )
        return []
    signals: list[WigSignal] = []
    notes_seen: set[str] = set()
    for line in codes_section.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[0]
        try:
            code = int(parts[1], 0)
        except ValueError:
            result.skipped.append(f"{remote_name}/{name}: bad code")
            continue
        try:
            if is_rc6:
                kwargs, notes = _lirc_rc6_fields(params, code)
            else:
                address, command = _lirc_rc5_fields(params, code)
                kwargs, notes = (
                    {"address": address, "command": command, "toggle": 0},
                    [],
                )
            # Every construction is wrapped: a value the class refuses
            # is a receipted skip, never a ValueError out of the
            # converter.
            command_obj = cls(**kwargs)
        except (LircManchesterError, ValueError, TypeError) as err:
            result.skipped.append(f"{remote_name}/{name}: {err}")
            continue
        notes_seen.update(notes)
        timings = list(command_obj.get_raw_timings())
        carrier, source = _carrier_for(
            declared_hz, getattr(command_obj, "modulation", None)
        )
        pronto = raw_to_pronto(timings, frequency=carrier)
        signals.append(WigSignal(
            alias=_humanize_key(name.removeprefix("KEY_").lower()),
            pronto=pronto,
            bypass_protocol=not _triple_reproduces(pronto, timings),
            extra=_carrier_extra(carrier, source),
        ))
    if signals:
        result.folds.append(
            f"{remote_name}: {len(signals)} {label} rows rebuilt from the "
            "protocol's own timings, with the toggle pinned to 0"
        )
    # A FOLD, NOT A SKIP, for the same reason the precision note is:
    # these rows converted. What the note records is an assumption the
    # reconstruction made, and "{count} signals could not convert" is
    # not what happened.
    for note in sorted(notes_seen):
        result.folds.append(f"{remote_name}: {note}")
    return signals


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


# --- Girr (IrScrutinizer / harctoolbox XML interchange) ---

# Each <command> carries up to three representations (parameters | raw
# | ccf); <ccf> is VERBATIM learned-format Pronto, which is exactly
# what wigs store, so the happy path is a straight copy. raw is
# synthesized mechanically; parameters-only commands would need IRP
# rendering and are skipped with a pointer at IrScrutinizer's own
# Pronto export (research/irscrutinizer.md).

_PRONTO_WORD = re.compile(r"^[0-9A-Fa-f]{4}$")


def _girr_local(tag: object) -> str:
    """Namespace-blind local tag name."""
    return str(tag).rpartition("}")[2]


def _girr_children(element, name: str):
    return [c for c in element.iter() if _girr_local(c.tag) == name]


def _girr_ccf(command) -> str | None:
    """First <ccf> normalized to one-line uppercase Pronto, or None."""
    for ccf in _girr_children(command, "ccf"):
        words = (ccf.text or "").split()
        if len(words) >= 6 and all(_PRONTO_WORD.match(w) for w in words):
            return " ".join(w.upper() for w in words)
    return None


def _girr_sequence_timings(sequence) -> list[int]:
    """One <intro>/<repeat> to signed microseconds. Handles both the
    flat text form (``+9024 -4512 ...``) and <flash>/<gap> children."""
    timings: list[int] = []
    flat = "".join(sequence.itertext())
    for child in sequence:
        local = _girr_local(child.tag)
        if local == "flash":
            timings.append(abs(int(float(child.text or "0"))))
        elif local == "gap":
            timings.append(-abs(int(float(child.text or "0"))))
    if timings:
        return timings
    values = re.findall(r"[+-]?\d+", flat)
    return [
        abs(int(v)) if i % 2 == 0 else -abs(int(v))
        for i, v in enumerate(values)
    ]


def _girr_raw_pronto(command) -> tuple[str | None, str | None, str]:
    """(pronto, caveat, carrier source) from a <raw> element.

    ``(None, None, "assumed")`` when there is no usable raw element.
    The third value is item 7's: a ``frequency`` attribute is the
    file's own statement, and its absence is HAIR's 38 kHz default,
    which the row records rather than passing off as the file's.
    """
    for raw in _girr_children(command, "raw"):
        try:
            frequency, source = _carrier_for(_int_or_none(raw.get("frequency")))
        except ValueError:
            frequency, source = 38000, "assumed"
        intro = repeat = None
        has_ending = False
        for child in raw:
            local = _girr_local(child.tag)
            if local == "intro":
                intro = child
            elif local == "repeat":
                repeat = child
            elif local == "ending":
                has_ending = True
        # The intro is the complete one-shot frame for nearly every
        # protocol; repeat-only remotes (RC5 style) fall back to one
        # repeat frame. Endings are inexpressible in Pronto.
        timings = _girr_sequence_timings(intro) if intro is not None else []
        if not timings and repeat is not None:
            timings = _girr_sequence_timings(repeat)
        if len(timings) < 2:
            continue
        caveat = (
            "'ending' sequence dropped (inexpressible in Pronto)"
            if has_ending else None
        )
        return raw_to_pronto(timings, frequency=frequency), caveat, source
    return None, None, "assumed"


def _girr_scope_has_parameters(remote) -> set[int]:
    """ids of <command> elements whose SCOPE carries <parameters>.

    Parametric Girr commonly hoists one <parameters> block to the
    commandSet (or remote) level and gives each command only its
    function number, so a per-command check misses the common shape
    and mislabels the skip. A command inherits parameters from any
    enclosing commandSet/remote that has a direct <parameters> child.
    """
    covered: set[int] = set()
    for scope in [remote, *_girr_children(remote, "commandSet")]:
        has_params = any(
            _girr_local(child.tag) == "parameters" for child in scope
        )
        if has_params:
            for cmd in _girr_children(scope, "command"):
                covered.add(id(cmd))
    return covered


def _convert_girr(text: str, name_hint: str) -> AdapterResult:
    import xml.etree.ElementTree as ET

    result = AdapterResult(format="girr")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        result.error = f"not well-formed XML ({err})"
        return result

    remotes = _girr_children(root, "remote")
    if not remotes:
        # The spec allows four root elements: remotes, remote,
        # commandSet, and command. A bare commandSet/command root has
        # no remote wrapper, so treat the whole document as one
        # anonymous remote named from the file.
        if _girr_children(root, "command"):
            remotes = [root]
        else:
            result.error = "no remotes or commands in this Girr file"
            return result

    for remote in remotes:
        remote_name = (
            remote.get("displayName") or remote.get("name") or ""
        ).strip()
        if _girr_local(remote.tag) != "remote" or not remote_name:
            remote_name = _stem(name_hint) or remote_name or "Girr Import"
        manufacturer = (remote.get("manufacturer") or "").strip()
        model = (remote.get("model") or "").strip()
        inherited = _girr_scope_has_parameters(remote)
        signals: list[WigSignal] = []
        for command in _girr_children(remote, "command"):
            cmd_name = (command.get("name") or "").strip()
            alias = _humanize_key(cmd_name) if cmd_name \
                else f"Signal {len(signals) + 1}"
            pronto = _girr_ccf(command)
            # A ccf element IS a Pronto the file wrote, header word and
            # all, so its carrier is declared by the source.
            carrier_source = "declared"
            if pronto is None:
                pronto, caveat, carrier_source = _girr_raw_pronto(command)
                if pronto is not None and caveat:
                    result.skipped.append(
                        f"{remote_name}/{alias}: {caveat}"
                    )
            if pronto is None:
                if (
                    _girr_children(command, "parameters")
                    or id(command) in inherited
                ):
                    result.skipped.append(
                        f"{remote_name}/{alias}: protocol-parameter "
                        "command with no ccf or raw timings -- "
                        "re-export from IrScrutinizer with Pronto "
                        "included"
                    )
                else:
                    result.skipped.append(
                        f"{remote_name}/{alias}: no usable "
                        "representation"
                    )
                continue
            signals.append(WigSignal(
                alias=alias,
                pronto=pronto,
                extra=_carrier_from_pronto(pronto, carrier_source),
            ))
        if not signals:
            result.skipped.append(f"{remote_name}: nothing convertible")
            continue
        result.wigs.append(Wig(
            name=remote_name,
            signals=signals,
            brand=manufacturer or None,
            model=model or None,
            notes="Imported from a Girr file (IrScrutinizer)",
            origin="converted:girr",
        ))
    if not result.wigs:
        result.error = result.error or (
            "no convertible remotes in this Girr file"
        )
    return result


def _stem(name_hint: str) -> str:
    stem = re.sub(r"\.(ir|json|conf|txt|girr|xml)$", "", name_hint.strip(),
                  flags=re.IGNORECASE)
    stem = stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() if stem else ""
