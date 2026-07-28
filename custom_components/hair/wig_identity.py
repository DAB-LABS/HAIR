"""Wig-signal identity: derive live identity from a wig's raw Pronto.

The shared helper of fitting-flow.md 5.1 and closet-direct-to-device.md
4.1: a wig file carries raw Pronto and NO decoded fields (wig_format
rule), so anything that wants to transmit or match a wig signal must
derive fingerprint, byte-hash, and decoded identity fresh on this
install. Fitting builds this; direct-to-device consumes it.

Derivation is deliberately NOT bespoke: the Pronto is normalized by the
same validator every import path uses, converted to raw timings by the
same ``ProntoCommand`` the transmit path uses, and pushed through the
same ``signal_monitor.normalize()`` the Sniffer and Plucker share. A
wig signal therefore resolves to byte-identical identity values as the
same signal captured off the air, which is what lets a fitting send
claim its own Mirror echo and lets direct-to-device dedup against the
catalog.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import CaptureResult
from .pronto_validator import validate_pronto


@dataclass(frozen=True)
class WigSignalIdentity:
    """Identity of one wig signal, derived fresh from its Pronto.

    Mirrors the identity slice of ``NormalizedSignal``; ``pronto`` is
    the validator-normalized code the values were derived from, and
    ``raw_timings``/``frequency`` ride along so a caller building a
    fallback replay command does not re-derive them.
    """

    pronto: str
    raw_timings: list[int]
    frequency: int
    fingerprint: str
    byte_hash: str | None
    decoded_protocol: str | None
    decoded_address: int | None
    decoded_command: int | None
    decoded_fingerprint: str | None
    decoded_extras: dict[str, int] | None


def wig_signal_identity(pronto: str) -> WigSignalIdentity | None:
    """Derive a :class:`WigSignalIdentity` from raw Pronto, or ``None``.

    ``None`` means the Pronto does not validate or does not convert to
    timings -- possible for a wig edited by hand after import, since
    parse-time validation and this call can straddle that edit. Callers
    treat it as "this signal cannot be sent", never as a crash.
    """
    result = validate_pronto(pronto)
    if not result.valid:
        return None
    normalized = result.normalized

    from .ir_command import ProntoCommand

    try:
        command = ProntoCommand(normalized)
    except (ValueError, IndexError):
        return None
    raw = command.get_raw_timings()
    if not raw:
        return None

    # The exact Sniffer/Plucker normalization, so identity can never
    # drift between a wig signal and the same signal off the air.
    from .signal_monitor import normalize

    parsed = CaptureResult(
        protocol="PRONTO",
        code=normalized,
        raw_timings=raw,
        frequency=command.modulation,
        confidence=1.0,
    )
    n = normalize(parsed)
    return WigSignalIdentity(
        pronto=normalized,
        raw_timings=list(raw),
        frequency=n.frequency,
        fingerprint=n.sig_fp,
        byte_hash=n.byte_hash,
        decoded_protocol=n.decoded_protocol,
        decoded_address=n.decoded_address,
        decoded_command=n.decoded_command,
        decoded_fingerprint=n.decoded_fingerprint,
        decoded_extras=n.decoded_extras,
    )


# ---------------------------------------------------------------------------
# Cached whole-wig identity (Adopt Device, v0.8.1)
# ---------------------------------------------------------------------------

# Keyed by signals_content_hash: the fitting machinery guarantees a
# wig's signals cannot change without the hash changing, so entries
# never go stale. Small LRU-ish cap; a closet scan touches every wig,
# and decoding a 300-signal wig per scan would otherwise be felt.
_IDENTITY_CACHE: dict[str, list[WigSignalIdentity | None]] = {}
_IDENTITY_CACHE_MAX = 128


def wig_signal_identities(wig) -> list[WigSignalIdentity | None]:
    """Identities for every signal in a wig, cached by content hash.

    Position-aligned with ``wig.signals``; an entry is ``None`` when
    that signal's Pronto does not validate (the caller skips it).
    """
    from .wig_format import signals_content_hash

    key = signals_content_hash(wig.signals)
    cached = _IDENTITY_CACHE.get(key)
    if cached is not None:
        return cached
    identities = [
        wig_signal_identity(sig.pronto) for sig in wig.signals
    ]
    if len(_IDENTITY_CACHE) >= _IDENTITY_CACHE_MAX:
        _IDENTITY_CACHE.pop(next(iter(_IDENTITY_CACHE)))
    _IDENTITY_CACHE[key] = identities
    return identities
