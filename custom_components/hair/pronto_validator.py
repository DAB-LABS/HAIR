"""Validation for manually-entered Pronto hex codes (HAIR Clips).

Pure and dependency-free so it can run server-side in the WebSocket
layer and be unit-tested without Home Assistant. No protocol decoding --
just a generic structural check chain with specific, user-facing error
messages that tell the user what to fix.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# The Pronto carrier-frequency word is expressed in units of this many
# microseconds: freq_hz = 1_000_000 / (word * 0.241246).
_PRONTO_CLOCK_US = 0.241246

# Soft carrier-frequency window (kHz). Outside this range we warn but
# still allow the code through.
_FREQ_MIN_KHZ = 20.0
_FREQ_MAX_KHZ = 60.0

_LENGTH_ERROR = (
    "Code length does not match the declared burst pair count. The code "
    "may be truncated or corrupted."
)


@dataclass
class ProntoValidationResult:
    """Outcome of validating a pasted Pronto hex string."""

    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    frequency_khz: float | None = None
    burst_pair_count: int | None = None
    normalized: str = ""
    # Item 6: ``0100`` is a learned code with no carrier. False says the
    # code names no frequency at all, which is different from a code
    # whose frequency is unusual, and ``frequency_khz`` stays None for
    # it: there is no carrier to report, only a time base.
    modulated: bool = True


def validate_pronto(text: str) -> ProntoValidationResult:
    """Validate a pasted Pronto hex code.

    Check chain: normalize, hex charset, 4-digit word shape, ``0000``
    learned-code header, burst-pair length math, and a soft
    carrier-frequency sanity check (warning only). Returns on the first
    blocking error so the message points at one concrete problem.
    """
    result = ProntoValidationResult()

    # 1. Normalize: strip outer whitespace, strip a single pair of outer
    # quotes (handles ``data="..."`` paste), collapse internal whitespace.
    s = (text or "").strip()
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        s = s[1:-1].strip()
    s = " ".join(s.split())
    result.normalized = s

    if not s:
        result.errors.append("Paste a Pronto hex code.")
        return result

    # 2. Character set.
    if any(c not in "0123456789abcdefABCDEF " for c in s):
        result.errors.append("Pronto codes use hex digits only.")
        return result

    tokens = s.split(" ")

    # 3. Word shape: every token must be exactly 4 hex digits.
    for tok in tokens:
        if len(tok) != 4:
            result.errors.append(
                f"Each Pronto value must be 4 hex digits (got {tok})."
            )
            return result

    words = [int(tok, 16) for tok in tokens]

    # 4. Header check: the two learned formats, and only those.
    #
    # ``0000`` is the modulated learned code and ``0100`` is the same
    # layout with no carrier, which is the format a device driven
    # without one uses. Both carry a time base in the second word and
    # burst pairs after it, so everything below reads them identically.
    # Every other header is a parameter form (``5000`` and ``6000`` are
    # RC5 and RC6 written as parameters, ``900x`` and ``8000`` name a
    # code in a database rather than a waveform); those are refused
    # here, naming the word, until something in HAIR can render them.
    if words[0] not in (0x0000, 0x0100):
        result.errors.append(
            "HAIR only supports learned Pronto codes (codes starting with "
            f"0000 or 0100). Got header {tokens[0]}."
        )
        return result
    result.modulated = words[0] == 0x0000

    # 5. Length math. Header is 4 words, then 2 words per burst pair.
    if len(words) < 4:
        result.errors.append(_LENGTH_ERROR)
        return result
    burst1 = words[2]
    burst2 = words[3]
    result.burst_pair_count = burst1 + burst2
    if len(words) != 4 + 2 * (burst1 + burst2):
        result.errors.append(_LENGTH_ERROR)
        return result

    # 6. Carrier frequency sanity (warning only).
    #
    # Skipped entirely for a non-modulated code: its second word is a
    # time base, not a carrier, and warning that a time base is outside
    # the usual carrier range would be telling the user off for the one
    # thing the format is for.
    freq_word = words[1]
    if freq_word > 0 and result.modulated:
        freq_khz = round(1000.0 / (freq_word * _PRONTO_CLOCK_US), 1)
        result.frequency_khz = freq_khz
        if not (_FREQ_MIN_KHZ <= freq_khz <= _FREQ_MAX_KHZ):
            result.warnings.append(
                f"Carrier frequency reads as {freq_khz} kHz. Typical IR is "
                "30-60 kHz. Continue if you are sure."
            )

    result.valid = True
    return result
