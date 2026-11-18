"""Which medium a pasted code is: infrared, radio, or either.

The Clipper's one add window takes any code HAIR reads and shows the
fields of the medium it is. This module answers that question, and both
paste readers' validate doors carry its answer as ``medium``, so the
panel follows one decision instead of guessing.

BY SHAPE, NOT BY WHICH READER ACCEPTS. The two readers each try hard to
read what they are given, and a radio reader can read the hex digits of
a Pronto code as base64. So the text's own shape decides first: a
Flipper ``.sub`` is radio, Pronto and the other infrared text formats are
infrared, a Broadlink packet says which it is in its type byte. Only a
bare list of numbers says nothing, and is ``either``, once it reads as a
code: a Pronto being typed by hand starts as digits, and must not be
sent to the radio editor on its way to becoming one.

For ``either`` the add window still shows one editor first, picked by
``timings_guess``: infrared when the timings, at 38 kHz, decode as an
infrared protocol (the decode the "Recognized as" pill shows), radio
otherwise. The person can switch it.

``PASTE_FORMATS`` lists the formats per medium, for the add window's
hint. ``frontend/src/paste-formats.ts`` holds the same table for the
panel, and a test checks that the two agree.
"""
from __future__ import annotations

import re

from .pasted_code import coerce_pasted_code, read_raw_timings
from .pronto_validator import validate_pronto

MEDIUM_IR = "ir"
MEDIUM_RF = "rf"
MEDIUM_EITHER = "either"

# Format ids per medium, in the order the hint names them. The panel
# shows each by its name (paste-formats.ts); a new paste format is one
# entry here and one there.
PASTE_FORMATS: dict[str, tuple[str, ...]] = {
    MEDIUM_IR: ("pronto", "broadlink", "tuya", "globalcache", "tasmota"),
    MEDIUM_RF: ("sub", "broadlink", "timings"),
}

_SUB = re.compile(r"RAW_Data:|^\s*Filetype:", re.MULTILINE)
# Hex words with spaces, or hex run together: a Pronto code, whole or
# damaged. The infrared reader's own error is the right answer for a
# damaged one.
_HEX_TEXT = re.compile(r"^[0-9A-Fa-f\s]+$")
# The radio reader's list of timings (rf_paste._INT_LIST).
_NUMBER_LIST = re.compile(r"^[\s\[\](),;+\-\d]*$")


def medium_of(text: str | None) -> str | None:
    """``"ir"``, ``"rf"``, ``"either"``, or None for text that is no code
    either reader would take (empty included)."""
    text = (text if isinstance(text, str) else "").strip()
    if not text:
        return None
    if _SUB.search(text):
        return MEDIUM_RF
    if validate_pronto(text).valid:
        return MEDIUM_IR
    if _NUMBER_LIST.match(text) and re.search(r"\d", text):
        # Tasmota's compressed raw form ("+9000-4500+560...") is numbers
        # and signs too, and it is infrared.
        if coerce_pasted_code(text).source is not None:
            return MEDIUM_IR
        return MEDIUM_EITHER if _radio_reads(text) else None
    if _HEX_TEXT.match(text):
        return MEDIUM_IR
    pasted = coerce_pasted_code(text)
    if pasted.source is not None or pasted.repair_offer is not None:
        return MEDIUM_IR
    if _broadlink_radio(text):
        return MEDIUM_RF
    if pasted.error is not None:
        # A text code the infrared reader recognized and refused
        # (several codes, an unusable Tasmota or sendir code).
        return MEDIUM_IR
    return None


def timings_guess(text: str | None) -> str:
    """``"ir"`` or ``"rf"``: which kind raw timings most likely are.

    Infrared when they decode as an infrared protocol at 38 kHz, radio
    otherwise, radio included when they do not read at all. Infrared
    wins when a radio family could claim the same timings too.
    """
    from .ir_command import ProntoCommand
    from .protocol_decode import decode_to_fields

    pasted = read_raw_timings(text if isinstance(text, str) else "")
    if pasted is None:
        return MEDIUM_RF
    try:
        raw = ProntoCommand(pasted.pronto).get_raw_timings()
    except Exception:
        # A guess never fails the door.
        return MEDIUM_RF
    return MEDIUM_IR if decode_to_fields(raw)[0] is not None else MEDIUM_RF


def _radio_reads(text: str) -> bool:
    """The radio reader takes the text as a code."""
    from . import rf_paste

    return rf_paste.validate(text).get("ok") is True


def _broadlink_radio(text: str) -> bool:
    """A Broadlink radio packet, as the radio reader reads one."""
    from . import rf_paste

    try:
        return rf_paste.read_paste(text).format == rf_paste.FORMAT_BROADLINK
    except rf_paste.PasteError:
        return False
