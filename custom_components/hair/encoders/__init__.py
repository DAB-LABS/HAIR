"""Encode-only command classes for protocols HAIR builds but does not decode.

irdb CSV rows name a protocol and its D, S and F (irdb_csv.py). Most of
those protocols already have a class in ``decoders`` or in the optional
library. The ones here have none: each module builds one protocol's
frame from its published IRP definition (the notation the JP1 and
DecodeIR community maintains), with the protocol's own carrier and
timing, and nothing else. No GPL implementation was consulted; each
module names where its facts came from.

NO DECODERS, ON PURPOSE. These protocols have no checksum or a weak one,
and their reference marks most of them "not a robust protocol, so
spurious decodes are likely". A decoder for one would claim captures
that belong to other remotes. So a code built here is stored to send as
built: nothing decodes it, and the import round-trip check
(``wig_adapters._triple_reproduces``) passes it through unchanged.

Every class subclasses the same ``Command`` base as the decoders, so it
works with and without the optional library, and returns signed
microsecond timings that end with the frame's lead-out space, so the
send path can repeat a frame without gluing two together.
"""
from __future__ import annotations

from collections.abc import Iterable


def bits_lsb(value: int, width: int) -> list[int]:
    """``value``'s low ``width`` bits, least significant first."""
    return [(value >> i) & 1 for i in range(width)]


def bits_msb(value: int, width: int) -> list[int]:
    """``value``'s low ``width`` bits, most significant first."""
    return [(value >> i) & 1 for i in range(width - 1, -1, -1)]


def pulse_distance(
    bits: Iterable[int], mark_us: int, zero_us: int, one_us: int
) -> list[int]:
    """Each bit as a mark and a space whose length says 0 or 1."""
    timings: list[int] = []
    for bit in bits:
        timings += [mark_us, -(one_us if bit else zero_us)]
    return timings


def check_range(name: str, value: int, top: int) -> None:
    """Refuse a field outside 0..top, the way the decoder classes do."""
    if not 0 <= value <= top:
        raise ValueError(f"{name} must be in range 0-{top}, got {value}")
