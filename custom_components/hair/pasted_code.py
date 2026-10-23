"""One pasted code, whatever form it arrived in (paste acceptance, slice 1).

The paste box has only ever read Pronto. A person holding a Zigbee2MQTT
``ir_code_to_send`` value (a Tuya base64 container) or a Broadlink base64
packet had to convert it by hand first. This module is the one place the
paste doors ask "what is this text", so the Clipper, the code editor, the
Sniffer edit and the Needs attention paste all answer the same way.

PRONTO DOES NOT MOVE. Text that is already valid Pronto comes back
unchanged, character for character, and the door validates it exactly as
it always did. Only text that is not Pronto is looked at further.

NO NEW READERS. A base64 token goes to the two readers HAIR already has,
in the order the SmartIR importer uses: Tuya first (it answers by content
and refuses a Broadlink type byte), then Broadlink. Whatever they return
is ordinary Pronto from then on, so a converted code gets the same
fingerprint, byte hash and decode as the same code pasted as Pronto or
heard off the air. The base64 text itself is not kept.

ONE CODE, NOT A REMOTE. A paste that holds several codes is refused with
a pointer to the Closet, where a file of codes becomes a wig. Forum and
app copies wrap long base64 at 64 or 76 characters, so several LINES are
not several codes: the lines are joined and tried as one code before
anything is refused.

TEXT CODES (import phase 2). A Global Cache ``sendir`` command reads
through the same parser the Closet's code-set reader uses
(``sendir.py``), so a code pasted alone becomes exactly the Pronto the
same code becomes inside a file. A sendir code the hardware itself would
refuse is refused here with the reason, rather than left to the Pronto
validator's error, which would not say what is wrong with it.

FAILS CLOSED. When nothing reads, the caller shows the Pronto
validator's own error, exactly as today. The only new refusals are the
several-codes pointer, a Broadlink RF packet, which is named for what
it is because HAIR sends infrared only, and an unusable text code.
"""
from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass

from .pronto_validator import validate_pronto
from .sendir import SendirError, is_sendir, parse_sendir
from .tuya_ir import tuya_b64_to_pronto
from .wig_adapters import broadlink_b64_to_pronto

SOURCE_PRONTO = "pronto"
SOURCE_TUYA = "tuya"
SOURCE_BROADLINK = "broadlink"
SOURCE_GLOBALCACHE = "globalcache"

# Shorter than this is a word, a name or a typo, not a code. The shortest
# real Broadlink IR packet is a few dozen characters and a Tuya container
# is longer than its 4-duration floor allows below this.
MIN_BASE64_CHARS = 16

# What a pasted code has to look like once read, before it is believed.
# The readers are built for files, where every value is meant to be a
# code; in a paste box a word or a stray token can inflate into a few
# huge durations by accident (measured: about 1 in 1,000 random hex
# strings and camel-case word runs did). A real IR command is a burst of
# at least eight mark and space pairs whose typical duration is a few
# hundred microseconds to a couple of milliseconds. Accidental reads are
# a handful of durations spread across tens of milliseconds.
MIN_DURATIONS = 16
MAX_MEDIAN_US = 5000

_BASE64_TOKEN = re.compile(r"^[A-Za-z0-9+/_-]+={0,2}$")
_HEX_ONLY = re.compile(r"^[0-9A-Fa-f]+$")

_BROADLINK_IR = 0x26
_BROADLINK_RF = {0xB2: "433 MHz", 0xD7: "315 MHz"}

# Shown when a paste was converted. The Tuya note also asks for a whole
# copy: a Tuya container records no length, and a FastLZ stream cut at a
# block boundary still inflates, so a copy missing its last line can read
# as a shorter, wrong code with nothing here able to tell. A Broadlink
# packet declares its length and is refused when cut short.
CARRIER_NOTE = {
    SOURCE_TUYA: (
        "Converted from a Tuya code; 38 kHz assumed (the format does not "
        "record a carrier). Check the code was copied whole."
    ),
    SOURCE_BROADLINK: (
        "Converted from a Broadlink code; 38 kHz assumed (the format does "
        "not record a carrier)."
    ),
    SOURCE_GLOBALCACHE: (
        "Converted from a Global Cache sendir code; the carrier comes from "
        "the code."
    ),
}


@dataclass(frozen=True, slots=True)
class PastedCode:
    """What a paste door should validate and store.

    ``pronto`` is the text to hand to ``validate_pronto``: the paste
    itself when it is Pronto or when nothing read it (so the validator's
    own error surfaces), the converted Pronto when a reader did.
    ``source`` is ``"pronto"``, one of the converted sources in
    ``CARRIER_NOTE``, or None when nothing read it. ``error`` is set only
    for the refusals this module owns, and then replaces the Pronto
    validator's message. ``notes`` are further things a converted code
    asks to be said, after the carrier note (a repeat count the source
    set and HAIR does not store, for one).
    """

    pronto: str
    source: str | None = None
    error: str | None = None
    notes: tuple[str, ...] = ()


def coerce_pasted_code(text: str | None) -> PastedCode:
    """Read one pasted code. See the module docstring for the rules."""
    text = text if isinstance(text, str) else ""
    if validate_pronto(text).valid:
        return PastedCode(text, SOURCE_PRONTO)

    tokens = _tokens(text)
    if not tokens:
        return PastedCode(text)

    text_code = _read_text_code(text)
    if text_code is not None:
        return text_code

    # Several Pronto codes, one per line: each line is valid on its own.
    pronto_lines = [
        line for line in text.splitlines()
        if line.strip() and validate_pronto(line).valid
    ]
    if len(pronto_lines) >= 2:
        return PastedCode(text, error=_several(len(pronto_lines), "Pronto codes"))

    if not all(_BASE64_TOKEN.match(tok) for tok in tokens):
        return PastedCode(text)

    if len(tokens) == 1:
        return _read_one(text, tokens[0], name_rf=True)

    # Base64 padding only ever ends a code, so a padded token before the
    # last one means the paste holds separate codes, not a wrapped one.
    padded_early = any(tok.endswith("=") for tok in tokens[:-1])

    # A copy wrapped at a standard width is one code: join it and try
    # once. This comes before reading the lines on their own, because a
    # line of a wrapped Tuya code can itself inflate into something
    # plausible.
    if not padded_early and _wrapped(tokens):
        joined = "".join(tokens)
        if _convert(joined) is not None or _broadlink_rf_band(joined):
            return _read_one(text, joined, name_rf=True)

    # Codes that each read whole on their own are several codes.
    alone = [_convert(tok) for tok in tokens]
    if all(hit is not None for hit in alone):
        return PastedCode(text, error=_several(len(tokens), _kinds(alone)))

    # Otherwise a wrapped code: lines at the wrap width continue a code
    # and a shorter line ends one. One group is one code, joined and
    # tried once; several groups that each read are several codes.
    groups = _wrap_groups(tokens)
    if len(groups) == 1:
        return _read_one(text, groups[0])
    read = [_convert(group) for group in groups]
    if sum(hit is not None for hit in read) >= 2:
        hits = [hit for hit in read if hit is not None]
        return PastedCode(text, error=_several(len(hits), _kinds(hits)))
    return _read_one(text, "".join(tokens))


# -- internals ---------------------------------------------------------


# Labels a Control Tower single-code email puts around its code. A paste
# of the whole email is one code: the sendir line is read and these are
# set aside.
_GC_LABEL = re.compile(
    r"^\s*(code\s*set|function|hex\s*code\s*\d|code\s*2)\s*:", re.IGNORECASE
)
_GC_CODE1 = re.compile(r"^\s*code\s*1\s*:\s*", re.IGNORECASE)
_GC_CONTINUATION = re.compile(r"^[\d,\sA-O]+$")


def _read_text_code(text: str) -> PastedCode | None:
    """A Global Cache sendir paste, or None when the text is not one."""
    lines = [
        _GC_CODE1.sub("", line.strip().strip("\"'\u201c\u201d"))
        for line in text.splitlines()
    ]
    lines = [line for line in lines if line.strip()]
    sendir = [i for i, line in enumerate(lines) if is_sendir(line)]
    if not sendir:
        return None
    if len(sendir) >= 2:
        return PastedCode(
            text, error=_several(len(sendir), "Global Cache sendir codes")
        )
    # One sendir line; a copy wrapped at a narrow width continues it on
    # lines of digits and commas. Anything else around it must be one of
    # the email's own labels.
    start = sendir[0]
    code = lines[start]
    for line in lines[start + 1:]:
        if _GC_CONTINUATION.match(line):
            code += line.strip()
        elif not _GC_LABEL.match(line):
            return PastedCode(text)
    if any(not _GC_LABEL.match(line) for line in lines[:start]):
        return PastedCode(text)
    try:
        parsed = parse_sendir(code)
    except SendirError as err:
        return PastedCode(
            text, error=f"This Global Cache code cannot be used: {err}."
        )
    notes = ()
    if parsed.repeat > 1:
        notes = (
            f"Global Cache sent this code {parsed.repeat} times; HAIR stores "
            "it once. Set the send count to match.",
        )
    return PastedCode(parsed.pronto(), SOURCE_GLOBALCACHE, notes=notes)


def _tokens(text: str) -> list[str]:
    """Whitespace-separated tokens, outer quotes and ``b64:`` stripped."""
    s = text.strip()
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        s = s[1:-1]
    out = []
    for tok in s.split():
        tok = tok.strip("\"',")
        if tok[:4].lower() == "b64:":
            tok = tok[4:]
        if tok:
            out.append(tok)
    return out


def _read_one(text: str, token: str, *, name_rf: bool = False) -> PastedCode:
    """One candidate code: convert it, name an RF packet, or fall through.

    ``name_rf`` is set only where the token is the whole paste or a copy
    wrapped at a standard width. A multi-word paste joined as a last try
    is never named RF: words run together are not a packet, and the
    Pronto error is the honest answer for them.
    """
    hit = _convert(token)
    if hit is not None:
        pronto, source = hit
        return PastedCode(pronto, source)
    band = _broadlink_rf_band(token) if name_rf else None
    if band is not None:
        return PastedCode(
            text,
            error=(
                f"This is a Broadlink RF code ({band}), not infrared. HAIR "
                "sends infrared only, so it cannot use this code."
            ),
        )
    return PastedCode(text)


def _convert(token: str) -> tuple[str, str] | None:
    """(pronto, source) for one whole code, or None."""
    if len(token) < MIN_BASE64_CHARS:
        return None
    # A Pronto pasted with its spaces removed is all hex digits, which is
    # also base64 alphabet. It is not a base64 code and must not be read
    # as one; the Pronto validator's own error is the honest answer.
    if _HEX_ONLY.match(token.rstrip("=")):
        return None
    # A URL-safe copy (``-`` and ``_`` for ``+`` and ``/``) is the same
    # code. Both readers get the standard alphabet: the Broadlink reader
    # decodes leniently and would silently DROP the two URL-safe
    # characters, shifting every byte after them into a different code
    # that still looks like IR.
    token = _standard_alphabet(token)
    pronto = tuya_b64_to_pronto(token)
    if pronto:
        return (pronto, SOURCE_TUYA) if _looks_like_ir(pronto) else None
    packet = _decode(token)
    if packet is None or not _whole_broadlink_ir(packet):
        return None
    pronto = broadlink_b64_to_pronto(token)
    if pronto and _looks_like_ir(pronto):
        return pronto, SOURCE_BROADLINK
    return None


def _looks_like_ir(pronto: str) -> bool:
    """A burst of IR, not an accident of inflating a word. See the bounds."""
    from .ir_command import ProntoCommand

    try:
        durations = sorted(abs(t) for t in ProntoCommand(pronto).get_raw_timings())
    except Exception:
        return False
    if len(durations) < MIN_DURATIONS:
        return False
    return durations[len(durations) // 2] <= MAX_MEDIAN_US


def _standard_alphabet(token: str) -> str:
    return token.replace("-", "+").replace("_", "/")


def _decode(token: str) -> bytes | None:
    cleaned = _standard_alphabet(token)
    cleaned += "=" * (-len(cleaned) % 4)
    try:
        return base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError):
        return None


def _whole_broadlink_ir(packet: bytes) -> bool:
    """One complete Broadlink IR packet and nothing after it but padding.

    The shared reader is lenient on purpose (it serves file imports), so
    two things are checked here before a paste is believed: the payload
    its length field declares is all present, which refuses the first
    line of a wrapped code read on its own, and nothing but zero padding
    follows it, which refuses two packets run together.
    """
    if len(packet) < 6 or packet[0] != _BROADLINK_IR:
        return False
    return _whole_packet(packet)


def _whole_packet(packet: bytes) -> bool:
    end = 4 + (packet[2] | (packet[3] << 8))
    if end > len(packet):
        return False
    return not packet[end:].rstrip(b"\x00")


def _broadlink_rf_band(token: str) -> str | None:
    """The band of one whole Broadlink RF packet, or None.

    Held to the same bar as an IR packet before anything is named: long
    enough to be a code, not all hex digits, and a packet whose declared
    payload is all present with only padding after it. A type byte alone
    is not enough; plenty of words decode to a first byte of 0xb2 or 0xd7.
    """
    if len(token) < MIN_BASE64_CHARS or _HEX_ONLY.match(token.rstrip("=")):
        return None
    packet = _decode(token)
    if packet is None or len(packet) < 6 or packet[0] not in _BROADLINK_RF:
        return None
    if not _whole_packet(packet):
        return None
    return _BROADLINK_RF[packet[0]]


# The widths copy tools wrap base64 at: 64 (PEM and most apps) and 76
# (MIME). A paste whose lines all sit at one of these, apart from a
# shorter last line, is one code that was wrapped on the way.
WRAP_WIDTHS = (64, 76)


def _wrapped(tokens: list[str]) -> bool:
    width = len(tokens[0])
    return (
        width in WRAP_WIDTHS
        and all(len(tok) == width for tok in tokens[:-1])
        and len(tokens[-1]) <= width
    )


def _wrap_groups(tokens: list[str]) -> list[str]:
    """Join wrapped lines back into codes.

    The wrap width is the longest token. A token at that width continues
    the current code; a shorter one ends it.
    """
    width = max(len(tok) for tok in tokens)
    groups: list[str] = []
    current = ""
    for tok in tokens:
        current += tok
        if len(tok) < width:
            groups.append(current)
            current = ""
    if current:
        groups.append(current)
    return groups


def _kinds(hits) -> str:
    """How to name the codes found: "Tuya base64 codes", or for a mix,
    "base64 codes (Broadlink and Tuya)"."""
    names = {"tuya": "Tuya", "broadlink": "Broadlink"}
    kinds = sorted({names[source] for _, source in hits})
    if len(kinds) == 1:
        return f"{kinds[0]} base64 codes"
    return "base64 codes (" + " and ".join(kinds) + ")"


def _several(count: int, codes: str) -> str:
    return (
        f"This paste holds {count} {codes}. The paste box takes one "
        "code. To bring in several at once, save them as a file (a wig, "
        "SmartIR, Flipper, LIRC, Girr, Harmony or Global Cache) and drop "
        "it on the Closet tab."
    )
