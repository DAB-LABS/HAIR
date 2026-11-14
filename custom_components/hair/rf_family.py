"""Family labels for radio codes: which encoder chip sent a frame.

A family decoder reads a voted radio frame and names the encoder family
that could have sent it, with the fields that family defines. It is a
LABEL ONLY. Identity (the row key, the card key, matching, the echo
claim, triggers, sends, wigs and ``.sub``) stays on the raw fingerprint
and the raw timings; nothing here is stored, and nothing here is read by
any of those. Remove this module and every row, device and trigger is
exactly as it was.

The input is a frame as a row stores it in ``raw_timings``: signed
timings, mark first, with the measured gap last when there is one (the
voted frame, ``rf_frames.analyze(...).frame``). The output is an
``RfFamily`` or None.

Certainty:

- ``decoded``: the frame fits one family only.
- ``ambiguous``: it fits two or more; the label names them all.

Written from the manufacturers' datasheets (the spec table below). Other
projects were used only to cross-check numbers already taken from a
datasheet; no code, table or capture from them is in HAIR.

SPEC TABLE: PT2262 and EV1527
==============================

Sources (datasheets):

- Princeton PT2272 V3.9 (the RF code description it shares with the
  PT2262): https://static.chipdip.ru/lib/159/DOC013159025.pdf
- HX2262 (a pin and waveform compatible PT2262):
  https://www.mikrocontroller.net/attachment/599366/HX2262.pdf
- Princeton PT2260 V1.5:
  https://pdf.direnc.net/upload/pt2260-r4s-encoder-entegresi-dip-16-datasheet.pdf
- RT1527 (Rato), an EV1527:
  https://www.thebackshed.com/forum/uploads/Grogster/2018-03-10_115403_RT1527.pdf
- EV1527 (Silvan, English): https://hobbielektronika.hu/forum/getfile.php?id=357682
- EV1527 (Chinese, with the resistor table):
  https://atta.szlcsc.com/upload/public/pdf/source/20170918/C108704_1505726808528976126.pdf

``T`` is the family's base unit, ``H`` a mark, ``L`` a space.

| Fact | PT2262 | EV1527 |
|---|---|---|
| Base unit | T = 4 oscillator periods | T = 4 LCK |
| Bit 0 | 1H 3L, 1H 3L (two pulse cycles) | 1H 3L (one pulse cycle) |
| Bit 1 | 3H 1L, 3H 1L | 3H 1L |
| Third symbol | F (floating): 1H 3L, 3H 1L | none (binary) |
| Never sent | 3H 1L, 1H 3L | none |
| Sync | 1H 31L, AFTER the 12 symbols | 1H 31L, BEFORE the 24 bits |
| Code word | 12 symbols + sync = 128 T | sync + 24 bits = 128 T |
| Layout | A0..A11 (see below) | C0..C19 address, then D0..D3 |
| T | one resistor and the supply | one resistor and the supply |

Layout: a PT2262 sends A0 to A11; on data versions the last N positions
are data, which can only be 0 or 1, while address positions can also be
F. An EV1527 sends a 20-bit factory-set address C0 to C19, then the data
bits D0 to D3. The EV1527 resistor table gives T from about 71 us (47K)
to about 1 ms (910K) at 5 V, 390 us at the recommended 330K.

What follows for one frame (derived from the table, not a datasheet
statement):

1. Both send 24 mark-first pulse pairs of 1:3 or 3:1, each pair 4 T long,
   and a 1 T sync mark beside a 31 T space. HAIR's frame cut ends a frame
   at that long space, so a frame of either family is 24 pairs and the
   sync mark, whichever side of the data the datasheet puts the sync.
2. Read a short-mark pair as 0 and a long-mark pair as 1. Grouped two by
   two in transmit order, a PT2262 can only give 00 (symbol 0), 11
   (symbol 1) and 01 (symbol F). Any 10 means the frame cannot be a
   PT2262: it is an EV1527, ``decoded``.
3. A frame with no 10 fits both, so it is "PT2262 or EV1527",
   ``ambiguous``, with the tri-state reading first. (A random EV1527 code
   has no 10 with probability (3/4)^12, about 3 percent.)
4. The oscillator is an RC network, so T is measured on each frame, never
   assumed. Receivers widen or narrow marks by a fixed amount (measured
   on the bench: a Broadlink RM4 Pro reads marks about 60 us longer than
   spaces of the same length, an Athom about 20 us), so the 1:3 test uses
   the difference between the long and the short mark, which a fixed
   offset cancels: for 1:3 it is 2 T, for a 1:2 clone 4/3 T.

Aliases (words in the docs, not labels): SC2262, HX2262, SC5262, PT2260
and PT2264 send what a PT2262 sends; RT1527, FP1527 and HS1527 what an
EV1527 sends.

Values are written in transmit order, the first bit sent as the most
significant: the bench keyfob's button 1 on is ``950E49``, address
``950E4``, data ``9``.

SPEC TABLE: HT12E
=================

Source (datasheet, read 2026-11-14 through the portal; md5 787d9a31):

- Holtek HT12A/HT12E, Rev. 1.20, 2009-02-20:
  https://www.farnell.com/datasheets/1899539.pdf

``T`` is one oscillator period (1/fOSC).

| Fact | HT12E | Where |
|---|---|---|
| Base unit | T = 1/fOSC, set by one resistor | Electrical characteristics |
| Typical T | 333 us (3 kHz at 5 V, ROSC 1.1 M) | the same |
| Bit | 3 T | Address/Data bit waveform |
| One | 2 T low, then 1 T high | the same figure |
| Zero | 1 T low, then 2 T high | the same figure |
| Pilot | 12 bit-times low (36 T) | Composition of information |
| Sync | a 1/3 bit: 1 T high | the same |
| Bits | A0 to A7 address, AD8 to AD11 address or data | the same |
| Order | A0 first, AD11 last | Address/Data programming |
| Words | at least 4 per trigger, in 4-word cycles while TE is low | Operation |
| Pins | pulled high: an open pin sends 1 | Pin description |

What follows for one frame (derived, not a datasheet statement):

1. HAIR's frame starts on the first mark after the gap, so an HT12E
   frame is the 1 T sync mark, then 12 pairs of a space and a mark each
   3 T long, then the gap the next word's pilot made (36 T, unless the
   receiver cut it).
2. A one is the long space with the short mark. As in the 1:3 shape,
   the test that a pair is 1:2 is the difference between the long and
   the short mark over T (1 for 1:2, 2 for 1:3), which a receiver's fixed
   mark widening cancels.
3. AD8 to AD11 are data on a remote and address on some boards, so the
   label shows them as ``data`` and the whole word as ``code`` too.
4. T is an RC oscillator's and fits any value. CAME 12 (about 320 us)
   and Nice FLO 12 (about 700 us) send this shape too (research 5.3), so
   a 12-bit frame is never ``decoded`` once either family is in the
   table, shown or not.

Values: the address and data are written as the bits sent, A0 first,
1 for an open pin, as a DIP switch reads left to right; ``code`` is the
12 bits as hex, the first bit sent as the most significant.

SPEC TABLE: HT6P20
==================

Source (datasheet, read 2026-11-14 through the portal; md5 da214d13):

- Holtek HT6P20B2/D2/F2, Rev 1.10, 2011-04-26:
  https://assets.sourcengine.com/datasheets/750225b5-2537-43de-8398-182becdc2663.pdf

The older HT6P20B/D (external oscillator resistor) was not read; the
community sources say it sends the same waveform, and its T varies with
its resistor, which the decoder allows for by measuring T on each frame.

``λ`` (lambda) is 32 internal oscillator periods.

| Fact | HT6P20B2/D2/F2 | Where |
|---|---|---|
| Bit | 3 λ (96 oscillator periods) | Address/Data Bit Waveform |
| Zero | 1 λ low, then 2 λ high | the same |
| One | 2 λ low, then 1 λ high | the same |
| Typical λ | 400 us (bit width 1.2 ms, 1.08 to 1.32 ms, at 5 V) | tDW |
| Pilot | 23 λ low, then 1 λ high | Pilot Code |
| Data | 24 bits: B2 A0-A21 D1-D0, D2 A0-A19 D3-D0, F2 A0-A18 D4-D0 | Code Word |
| End code | 4 bits 0101, after the data | End code Waveform |
| Repeats | the code word, while a data pin is held low | Code Word |

What follows for one frame (derived): the bits are HT12E's (2 low 1
high is a one), so the frame is the 1 λ high of the pilot as the start
mark, then 28 space-mark pairs, then the gap the next pilot made (23 λ).
It is told from every other family of this shape by its 28 bits and the
0101 end code. The split of the 24 bits into address and data depends
on the part, which the frame cannot tell, so the label shows ``code``
(the 24 bits, the first sent as the most significant) and not a split.

SPEC TABLE: KeeLoq HCS200, HCS300, HCS301 (detection only)
===========================================================

Sources (datasheets, read 2026-11-14 through the portal):

- Microchip HCS301, DS21143B (md5 7b8dc83b):
  https://ww1.microchip.com/downloads/en/DeviceDoc/21143b.pdf
- Microchip HCS200, DS40138C (md5 ad455d4f):
  https://ww1.microchip.com/downloads/en/DeviceDoc/40138c.pdf
- Microchip HCS300, DS21137G (md5 78de68c8):
  https://ww1.microchip.com/downloads/en/DeviceDoc/21137g.pdf

| Fact | HCS301 (HCS300 the same) | Where |
|---|---|---|
| TE | 400 us typ (260 to 660); 200 or 100 us at the faster settings | Table 3-3, Table 8-4 |
| Bit | 3 TE | Table 8-4 (TBP) |
| Zero | 2 TE high, then 1 TE low | Figure 4-1 |
| One | 1 TE high, then 2 TE low | the same |
| Preamble | 23 TE at 50 percent duty (P1 to P12) | Figure 8-4 |
| Header | 10 TE low | the same |
| Data | 66 bits, sent LSb first | Figures 4-2 and 8-5 |
| Bits 0-31 | encrypted (hopping) | the same |
| Bits 32-59 | serial number | the same |
| Bits 60-63 | buttons, as S3 S0 S1 S2 | the same |
| Bits 64, 65 | VLOW, RPT | the same |
| Guard | 39 TE | Table 8-4 |
| Seed | all buttons held: a seed replaces the encrypted part | 4.2 |

HCS200: the same word, with bits 64 and 65 a status bit and a fixed bit
rather than VLOW and RPT (DS40138C 4.2). Its Synchronous Transmission
mode, which adds 16 reserved bits, is a test mode and is not read.

What follows for one frame (derived): the preamble is a run of equal
marks and the 10 TE header is a gap to HAIR, so HAIR drops the
preamble as a piece with no body and files the data as the frame (66
marks, the 65 spaces between them, the guard as the gap). Real decoders
accept 64 to 66 bits, since a receiver often loses the last ones. The
Athom (64 RMT symbols) cannot hold a code word with its preamble; the
RM4 Pro can.

What the label shows (owner ruling 2026-11-14): the fixed part only.
``serial`` is the datasheet's 28-bit serial number (LSb first on the
air, so read as the datasheet numbers it, in hex); ``buttons`` are the
inputs held; ``low battery`` is bit 64 when the frame holds it. The 32
encrypted bits are never shown, logged or carried. Nothing here decrypts,
learns or sends; a KeeLoq receiver rejects a replayed word.

SPEC TABLE: Nexa, KAKU and Intertechno, old fixed code (held off)
=================================================================

Source (one community description, re-read 2026-11-14; no datasheet for
its encoder was found):

- elektronikforumet wiki, "RF Protokoll - Nexa/Proove (aldre, ej
  sjalvlarande)":
  https://www.elektronikforumet.com/wiki/RF_Protokoll_-_Nexa/Proove_(%C3%A4ldre,_ej_sj%C3%A4lvl%C3%A4rande)

| Fact | Old Nexa | Note |
|---|---|---|
| T | 350 us; a symbol is 8 T | |
| 0 | 1H 3L 1H 3L | PT2262's 0 |
| 1 | 3H 1L 3H 1L | PT2262's 1, never used |
| X | 1H 3L 3H 1L | PT2262's F |
| Sync | 1H, then 32 L | PT2262 says 31 |
| Word | 12 symbols, b0 first, then the sync | |
| b0-b3 | house A to P: A 0000, B X000 ... P XXXX | X counts as 1, b0 lowest |
| b4-b7 | unit 1 to 16, the same way | |
| b8-b10 | 0 X X | the page calls them "Unknown" |
| b11 | 0 off, X on | |
| Repeats | 4 or more, in fours | |
| Encoder | MOSDESIGN M3E (named on the page; no datasheet) | |

What follows for one frame (derived): it is a PT2262 frame, so it is
read by the 1:3 shape and is always a two-name label beside PT2262.
It is told apart only by its symbols: none is 1, and b8 to b10 are
0 F F. Held off until one real capture (ruling 2026-11-14).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from statistics import median
from typing import Any

from .identity import canonical_edges

LABEL_EV1527 = "EV1527"
LABEL_PT2262_OR_EV1527 = "PT2262 or EV1527"
FAMILY_EV1527 = "ev1527"
FAMILY_PT2262_EV1527 = "pt2262_ev1527"
CERTAINTY_DECODED = "decoded"
CERTAINTY_AMBIGUOUS = "ambiguous"


# ---------------------------------------------------------------------------
# The families
# ---------------------------------------------------------------------------
#
# One row per family. A family is READ by its waveform shape's decoder
# (several families can share a shape) and SHOWN only when ``shown`` is
# True: turning one on is a one-line change here, with the real capture
# that confirmed it named in ``evidence`` (owner ruling 2026-11-14). A
# family that is off is built and tested like any other, never adds a
# name or an alias to a label, and still counts when the certainty is
# worked out, so a frame another family we know of also fits is never
# called ``decoded``.


@dataclass(frozen=True)
class FamilySpec:
    """One radio family: its label word, clone names and switch."""

    key: str
    name: str
    aliases: tuple[str, ...] = ()
    shown: bool = False
    evidence: str = ""


FAMILIES: dict[str, FamilySpec] = {
    spec.key: spec for spec in (
        FamilySpec(
            "pt2262", "PT2262",
            aliases=("SC2262", "HX2262", "SC5262", "PT2260", "PT2264"),
            shown=True,
            evidence="Princeton PT2272 V3.9, HX2262, PT2260 V1.5 datasheets; "
                     "the bench keyfob (2026-11-12)",
        ),
        FamilySpec(
            "ev1527", "EV1527",
            aliases=("RT1527", "FP1527", "HS1527"),
            shown=True,
            evidence="RT1527 and EV1527 datasheets; the bench keyfob "
                     "(2026-11-12)",
        ),
        FamilySpec(
            "ht12e", "HT12E",
            shown=True,
            evidence="Holtek HT12A/HT12E datasheet Rev. 1.20 (shown on the "
                     "datasheet alone, ruling 2026-11-14)",
        ),
        FamilySpec(
            "ht6p20", "HT6P20",
            aliases=("HT6P20B", "HT6P20D", "HT6P20B2", "HT6P20D2", "HT6P20F2"),
            shown=True,
            evidence="Holtek HT6P20B2/D2/F2 datasheet Rev 1.10 (shown on the "
                     "datasheet alone, ruling 2026-11-14)",
        ),
        FamilySpec(
            "nexa_old", "Nexa",
            aliases=("KlikAanKlikUit", "Intertechno", "Proove"),
            shown=False,
            evidence="elektronikforumet wiki (one community description); "
                     "held off until a real capture (ruling 2026-11-14)",
        ),
        FamilySpec(
            "keeloq", "KeeLoq",
            aliases=("HCS200", "HCS300", "HCS301"),
            shown=True,
            evidence="Microchip HCS301 DS21143B, HCS200 DS40138C, HCS300 "
                     "DS21137G (shown on the datasheets alone, ruling "
                     "2026-11-14); detection only",
        ),
    )
}


@dataclass(frozen=True)
class _Fit:
    """One family a shape decoder found the frame fits."""

    key: str
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _ShapeRead:
    """What one shape decoder made of a frame.

    ``shared`` are the fields shown when more than one family fits.
    """

    unit_us: int
    fits: tuple[_Fit, ...]
    shared: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RfFamily:
    """What the family decoders made of one frame."""

    label: str
    family: str
    certainty: str
    unit_us: int
    fields: tuple[tuple[str, str], ...] = field(default=())
    aliases: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "family": self.family,
            "certainty": self.certainty,
            "unit_us": self.unit_us,
            "fields": [{"name": n, "value": v} for n, v in self.fields],
            "aliases": list(self.aliases),
        }


def family_payload(frame: list[int] | tuple[int, ...] | None) -> dict[str, Any] | None:
    """``family_of`` as the panel receives it: the object, or None."""
    result = family_of(frame)
    return result.to_dict() if result is not None else None


def family_slots(frame: list[int] | tuple[int, ...] | None) -> dict[str, Any]:
    """The Candy Drawer's two keys for a radio event: ``protocol`` (the
    label) and ``family_fields`` (the fields as name and value)."""
    result = family_of(frame)
    if result is None:
        return {"protocol": None, "family_fields": None}
    return {
        "protocol": result.label,
        "family_fields": [{"name": n, "value": v} for n, v in result.fields],
    }


def family_of(
    frame: list[int] | tuple[int, ...] | None, *, include_hidden: bool = False
) -> RfFamily | None:
    """The family of one voted frame, or None when no family fits.

    ``include_hidden`` reads every family as if it were shown, for the
    tests that hold the families that are off to the same standard. No
    payload sets it.
    """
    if not frame:
        return None
    return _family_of(tuple(int(v) for v in frame), include_hidden)


@lru_cache(maxsize=1024)
def _family_of(frame: tuple[int, ...], include_hidden: bool) -> RfFamily | None:
    # ``_SHAPES`` is defined below its decoders.
    for decode in _SHAPES:
        read = decode(frame)
        if read is not None and read.fits:
            return _label(read, include_hidden)
    return None


def _label(read: _ShapeRead, include_hidden: bool) -> RfFamily | None:
    """One shape's fits as a label: shown names only, certainty over all."""
    shown = [
        fit for fit in read.fits
        if include_hidden or FAMILIES[fit.key].shown
    ]
    if not shown:
        return None
    names = [FAMILIES[fit.key].name for fit in shown]
    aliases = tuple(
        alias for fit in shown for alias in FAMILIES[fit.key].aliases
    )
    return RfFamily(
        label=" or ".join(names),
        family="_".join(fit.key for fit in shown),
        certainty=CERTAINTY_DECODED if len(read.fits) == 1 else CERTAINTY_AMBIGUOUS,
        unit_us=read.unit_us,
        fields=shown[0].fields if len(shown) == 1 else read.shared,
        aliases=aliases,
    )


# ---------------------------------------------------------------------------
# Shape: mark first, 1:3 and 3:1 pairs (PT2262, EV1527)
# ---------------------------------------------------------------------------

# The 24-pair pulse-width code word (section above).
_PAIRS = 24
# Every data pair is 4 T; one may sit this far from the frame's median
# pair and still count (the Athom's measured spread is about 30 percent
# on short pulses, 10 percent on long ones, and a pair is one of each).
_PAIR_TOLERANCE = 0.30
# (long mark - short mark) / T: 2 for 1:3, 4/3 for a 1:2 clone.
_MARK_SPLIT_MIN = 1.7
_MARK_SPLIT_MAX = 2.3
# The sync mark is 1 T: no longer than this many short marks.
_SYNC_MAX_SHORT_MARKS = 1.6
# A measured gap after the sync is 31 T; a receiver may cut it shorter.
_GAP_MIN_T = 12.0
_GAP_MAX_T = 45.0


def _pt2262_ev1527(frame: tuple[int, ...]) -> _ShapeRead | None:
    gap = -frame[-1] if len(frame) % 2 == 0 and frame[-1] < 0 else None
    edges = canonical_edges(list(frame))
    # 24 pairs and the sync mark: 49 edges. HAIR's frame cut ends a frame
    # at the 31 T space, which always follows the sync mark, so a whole
    # frame always has it. Without it, 24 pairs that lost their last space
    # look exactly like 23 pairs and a sync, so such a frame is not read.
    if len(edges) != 2 * _PAIRS + 1:
        return None
    marks = edges[0:2 * _PAIRS:2]
    spaces = edges[1:2 * _PAIRS:2]
    sync = edges[-1]
    sums = [m + s for m, s in zip(marks, spaces, strict=False)]
    typical = median(sums)
    if typical <= 0 or any(
        abs(total - typical) > _PAIR_TOLERANCE * typical for total in sums
    ):
        return None
    unit = typical / 4.0
    # Two mark widths, split where the frame's own marks split.
    low, high = min(marks), max(marks)
    if high - low < unit:
        return None
    cut = (low + high) / 2.0
    short_marks = [m for m in marks if m < cut]
    long_marks = [m for m in marks if m >= cut]
    if not short_marks or not long_marks:
        return None
    split = (median(long_marks) - median(short_marks)) / unit
    if not _MARK_SPLIT_MIN <= split <= _MARK_SPLIT_MAX:
        return None
    if sync > _SYNC_MAX_SHORT_MARKS * median(short_marks):
        return None
    if gap is not None and not _GAP_MIN_T <= gap / unit <= _GAP_MAX_T:
        return None
    bits = "".join("1" if m >= cut else "0" for m in marks)
    code = f"{int(bits, 2):06X}"
    unit_us = round(unit)
    symbols = [bits[i:i + 2] for i in range(0, _PAIRS, 2)]
    ev1527 = _Fit("ev1527", (("address", code[:5]), ("data", code[5])))
    if "10" in symbols:
        return _ShapeRead(unit_us, (ev1527,))
    tri = "".join({"00": "0", "11": "1", "01": "F"}[s] for s in symbols)
    pt2262 = _Fit("pt2262", (("tri-state", tri),))
    fits = [pt2262, ev1527]
    if "1" not in tri and tri[8:11] == "0FF" and "nexa_old" in FAMILIES:
        fits.append(_Fit("nexa_old", _nexa_old_fields(tri)))
    return _ShapeRead(
        unit_us, tuple(fits), shared=(("tri-state", tri), ("code", code)),
    )


def _nexa_old_fields(tri: str) -> tuple[tuple[str, str], ...]:
    """House, unit and state from an old Nexa word: X counts as 1 and the
    first symbol is the lowest (the spec table above)."""
    def value(symbols: str) -> int:
        return sum(1 << index for index, s in enumerate(symbols) if s == "F")

    return (
        ("house", chr(ord("A") + value(tri[0:4]))),
        ("unit", str(value(tri[4:8]) + 1)),
        ("state", "on" if tri[11] == "F" else "off"),
    )


# ---------------------------------------------------------------------------
# Shape: space first, 1:2 and 2:1 pairs after a start mark (HT12E)
# ---------------------------------------------------------------------------

# Bits a word of this shape carries, by family (spec table above).
_SF_BITS = (12, 28)
# Every bit is 3 T; one may sit this far from the frame's median bit
# (the same allowance as the 1:3 shape, for the same receivers).
_SF_PAIR_TOLERANCE = 0.30
# (long - short) / T: 1 for 1:2, 2 for a 1:3 frame read in this shape.
_SF_SPLIT_MIN = 0.7
_SF_SPLIT_MAX = 1.4
# The start mark is 1 T: no longer than this many short marks.
_SF_START_MAX_SHORT_MARKS = 1.6
# The pilot before the start mark is 12 bit-times (36 T) on the HT12E;
# a receiver may cut it shorter, and other families of this shape send
# up to about 76 T.
_SF_GAP_MIN_T = 12.0
_SF_GAP_MAX_T = 90.0


def _space_first_1_2(frame: tuple[int, ...]) -> _ShapeRead | None:
    """A start mark, then N bits of a space and a mark, 1:2 or 2:1.

    HAIR's frame starts on the first mark after the gap, so the frame is
    the start mark, the bits, and the gap the next word's pilot made.
    A one is the long space and the short mark (HT12E datasheet: 2
    periods low, 1 high).
    """
    gap = -frame[-1] if len(frame) % 2 == 0 and frame[-1] < 0 else None
    edges = canonical_edges(list(frame))
    bits_n = (len(edges) - 1) // 2
    if len(edges) % 2 != 1 or bits_n not in _SF_BITS:
        return None
    start = edges[0]
    spaces = edges[1::2]
    marks = edges[2::2]
    sums = [s + m for s, m in zip(spaces, marks, strict=True)]
    typical = median(sums)
    if typical <= 0 or any(
        abs(total - typical) > _SF_PAIR_TOLERANCE * typical for total in sums
    ):
        return None
    unit = typical / 3.0
    low, high = min(marks), max(marks)
    if high - low < 0.5 * unit:
        return None
    cut = (low + high) / 2.0
    short_marks = [m for m in marks if m < cut]
    long_marks = [m for m in marks if m >= cut]
    if not short_marks or not long_marks:
        return None
    split = (median(long_marks) - median(short_marks)) / unit
    if not _SF_SPLIT_MIN <= split <= _SF_SPLIT_MAX:
        return None
    if start > _SF_START_MAX_SHORT_MARKS * median(short_marks):
        return None
    if gap is not None and not _SF_GAP_MIN_T <= gap / unit <= _SF_GAP_MAX_T:
        return None
    bits = "".join("1" if m < cut else "0" for m in marks)
    unit_us = round(unit)
    fits: list[_Fit] = []
    if bits_n == 12 and "ht12e" in FAMILIES:
        fits.append(_Fit("ht12e", (
            ("address", bits[:8]), ("data", bits[8:]), ("code", f"{int(bits, 2):03X}"),
        )))
    if bits_n == 28 and bits[24:] == "0101" and "ht6p20" in FAMILIES:
        fits.append(_Fit("ht6p20", (("code", f"{int(bits[:24], 2):06X}"),)))
    return _ShapeRead(unit_us, tuple(fits), shared=(("code", bits),))


# ---------------------------------------------------------------------------
# Shape: mark first, 1:2 and 2:1 pairs, no start mark (KeeLoq)
# ---------------------------------------------------------------------------

# Bits a KeeLoq data piece holds: 66, and real decoders accept 64 and 65
# because a receiver often loses the last bits (research 6.1).
_KEELOQ_BITS = (64, 65, 66)
# Every bit is 3 TE.
_MF2_PAIR_TOLERANCE = 0.30
_MF2_SPLIT_MIN = 0.7
_MF2_SPLIT_MAX = 1.4
# The guard after the last bit is 39 TE, plus the last bit's own low.
_KEELOQ_GAP_MIN_TE = 20.0
_KEELOQ_GAP_MAX_TE = 60.0
# Button inputs as they ride the air, bits 60 to 63 (Figure 8-5).
_KEELOQ_BUTTON_ORDER = ("S3", "S0", "S1", "S2")


def _keeloq_buttons(pressed: list[str]) -> str:
    """The inputs held, S0 first; all four is the seed word, which
    carries a seed where the hopping code would be (HCS301 4.2)."""
    if len(pressed) == 4:
        return "all (seed)"
    return "+".join(sorted(pressed)) if pressed else "none"


def _mark_first_1_2(frame: tuple[int, ...]) -> _ShapeRead | None:
    """Bits of a mark and a space, 1:2 or 2:1, with no start mark.

    A KeeLoq code word's 23 TE preamble is a run of equal marks, and the
    10 TE header after it is a gap to HAIR, so HAIR files the preamble
    as a piece with no body (and drops it) and the data as the frame:
    66 marks, the 65 spaces between them, and the guard as the gap. A
    one is the short mark with the long space (HCS301 Figure 4-1).
    """
    gap = -frame[-1] if len(frame) % 2 == 0 and frame[-1] < 0 else None
    edges = canonical_edges(list(frame))
    if len(edges) % 2 != 1:
        return None
    bits_n = (len(edges) + 1) // 2
    if bits_n not in _KEELOQ_BITS:
        return None
    marks = edges[0::2]
    spaces = edges[1::2]
    sums = [m + s for m, s in zip(marks, spaces, strict=False)]
    typical = median(sums)
    if typical <= 0 or any(
        abs(total - typical) > _MF2_PAIR_TOLERANCE * typical for total in sums
    ):
        return None
    unit = typical / 3.0
    low, high = min(marks), max(marks)
    if high - low < 0.5 * unit:
        return None
    cut = (low + high) / 2.0
    short_marks = [m for m in marks if m < cut]
    long_marks = [m for m in marks if m >= cut]
    if not short_marks or not long_marks:
        return None
    split = (median(long_marks) - median(short_marks)) / unit
    if not _MF2_SPLIT_MIN <= split <= _MF2_SPLIT_MAX:
        return None
    if gap is not None and not _KEELOQ_GAP_MIN_TE <= gap / unit <= _KEELOQ_GAP_MAX_TE:
        return None
    bits = [1 if m < cut else 0 for m in marks]
    if "keeloq" not in FAMILIES:
        return _ShapeRead(round(unit), ())
    # The fixed part only (ruling 2026-11-14): bits 0 to 31 are the
    # encrypted hopping code and are never shown, logged or carried.
    serial = sum(bit << index for index, bit in enumerate(bits[32:60]))
    pressed = [
        name for name, bit in zip(_KEELOQ_BUTTON_ORDER, bits[60:64], strict=False)
        if bit
    ]
    fields: list[tuple[str, str]] = [
        ("serial", f"{serial:07X}"),
        ("buttons", _keeloq_buttons(pressed)),
    ]
    if bits_n >= 65:
        fields.append(("low battery", "yes" if bits[64] else "no"))
    return _ShapeRead(round(unit), (_Fit("keeloq", tuple(fields)),))


_SHAPES = (_pt2262_ev1527, _space_first_1_2, _mark_first_1_2)
