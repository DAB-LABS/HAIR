"""Read the bits a pulse-distance frame puts on the air, for import tests.

THE CHECK THAT DOES NOT TRUST A DECODER. The import-phase-2 readers turn
other formats' numbers into HAIR's codes, and the thing worth proving is
that the bytes on the wire are the bytes the source file stated. HAIR's
NEC decoder exists only on the library leg, so a test that asked it
would prove nothing on the other. This reads the frame directly: a long
leader, then one bit per mark and space, the space deciding the bit.
"""
from __future__ import annotations

from custom_components.hair.ir_command import ProntoCommand


def timings(pronto: str) -> list[int]:
    return list(ProntoCommand(pronto).get_raw_timings())


def frames(raw: list[int], *, leader_us: int = 3000) -> list[list[int]]:
    """Each frame's bits, LSB-first per byte, in transmission order.

    A frame starts at a mark longer than ``leader_us`` followed by its
    space, and its bits run until a space longer than 4 ms. A ditto (a
    leader with no bits after it) yields an empty list and is dropped.
    """
    out: list[list[int]] = []
    i = 0
    while i < len(raw) - 1:
        if raw[i] > leader_us and raw[i + 1] < 0:
            i += 2
            bits: list[int] = []
            while i + 1 < len(raw) and raw[i] > 0 and -raw[i + 1] < 4000:
                mark, space = raw[i], -raw[i + 1]
                bits.append(1 if space > 2 * mark else 0)
                i += 2
            if bits:
                out.append(bits)
        else:
            i += 1
    return out


def frame_bytes(bits: list[int]) -> list[int]:
    """Bits sent LSB-first, grouped into bytes."""
    out = []
    for start in range(0, len(bits) - len(bits) % 8, 8):
        out.append(sum(bit << n for n, bit in enumerate(bits[start:start + 8])))
    return out


def first_frame_bytes(pronto: str) -> list[int]:
    found = frames(timings(pronto))
    assert found, "no pulse-distance frame in this code"
    return frame_bytes(found[0])
