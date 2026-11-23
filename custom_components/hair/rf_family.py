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
   a 12-bit frame whose T falls in either family's band (220 to 450 us,
   500 to 900 us) is never ``decoded``, shown or not. Outside both bands,
   including the 450 to 500 us gap between them, it is HT12E alone.

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
Its names are not aliases until its datasheet is read (ruling
2026-11-14).

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

HCS200: the same word, with bit 64 VLOW and bit 65 a fixed bit rather
than RPT (DS40138C Figure 4-2). Its Synchronous Transmission
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

Its house, unit and state stay in the decoder: PT2262 always fits beside
it, so the label carries the shape's shared tri-state and code, never
these fields (ruling 2026-11-15). Revisit the label rule when this
family is turned on, or those fields never reach the tooltip.

SPEC TABLE: CAME 12 and 24 (held off)
=====================================

No vendor specification exists. Sources, re-read 2026-11-14:

- Flipper forum thread with independent measurements (BitcoinRaven,
  a.fabbro, 2022): https://forum.flipper.net/t/protocol-documentation/4794
- rtl_433 flex config CAME-TOP432.conf (rtl_433 is GPL-2.0; a config
  file, read for facts only):
  https://git.sudo.is/mirrors/rtl_433/src/branch/master/conf/CAME-TOP432.conf
- came.c in unleashed-firmware, a Flipper-lineage decoder (GPL-3.0; read
  for facts only, ruling 2026-11-14; no code, table, names or comments
  taken):
  https://code.popov.link/mirrors/unleashed-firmware/src/branch/dev/lib/subghz/protocols/came.c

Rows marked [GPL only] have no published description: each was taken
from came.c in unleashed-firmware (GPL-3.0), read for facts only; no
published description found.

| Fact | CAME | Sources |
|---|---|---|
| T | 320 us (measured 321 to 343; 250 also works) | forum, rtl_433, Flipper |
| Tolerance used | +/- 150 us | [GPL only] |
| Zero | 1 T low, then 2 T high | forum (-334/667), Flipper |
| One | 2 T low, then 1 T high | forum (-664/343), Flipper |
| Start | a 1 T pulse after the pilot | forum, rtl_433 |
| Pilot | at least 36 T (11.5 ms) | rtl_433; forum (about 47 T) |
| Pilot, 24 bits | 76 T | [GPL only] |
| Bits, 12 | 12 | forum, rtl_433 |
| Bits, 24 | 24 | [GPL only] |
| Order | most significant first | forum (by its script) |
| Repeats | 4 per press | forum, rtl_433 |

What follows (derived): this is the HT12E shape (research 5.3). A
12-bit frame with T in the CAME band (220 to 450 us) fits both CAME and
HT12E and is never ``decoded``; a 24-bit frame in the band fits CAME
alone. The same waveform at 18, 25 and 42 bits is named for other brands
(Airforce, Prastel) in the Flipper lineage only, and is not built.
Held off until one real capture (ruling 2026-11-14).

SPEC TABLE: Nice FLO 12 and 24 (held off)
=========================================

One source only, re-read 2026-11-14:

- nice_flo.c in unleashed-firmware, a Flipper-lineage decoder (GPL-3.0;
  read for facts only, ruling 2026-11-14; no code, table, names or
  comments taken):
  https://code.popov.link/mirrors/unleashed-firmware/src/branch/dev/lib/subghz/protocols/nice_flo.c

Every row below was taken from nice_flo.c in unleashed-firmware
(GPL-3.0), read for facts only; no published description found. A real
capture will be the primary evidence when one exists.

| Fact | Nice FLO | |
|---|---|---|
| T | 700 us, long 1400 | |
| Tolerance used | +/- 200 us | |
| Zero | 1 T low, then 2 T high | |
| One | 2 T low, then 1 T high | |
| Pilot | about 36 T low | |
| Bits | 12 or 24 | |
| End | a low of at least 4 T | |

What follows (derived): the HT12E shape again, at about twice CAME's T.
A 12-bit frame with T in the Nice FLO band (500 to 900 us) fits Nice
FLO and HT12E and is never ``decoded``; 24 bits in the band fit Nice FLO
alone. Held off until one real capture (ruling 2026-11-14).

SPEC TABLE: Somfy RTS (held off; detection only)
================================================

One source, re-read 2026-11-14: the PushStack write-up, built from
passive observation; its author says it "can be inaccurate or
incorrect". No vendor document was found. The page states no license;
facts only were taken from it.

- https://pushstack.wordpress.com/somfy-rts-protocol/

| Fact | Somfy RTS |
|---|---|
| Carrier | 433.42 MHz (the Athom's 433.92 SAW does not hear it) |
| Coding | Manchester: a rising edge is 1, a falling edge 0 |
| Symbol | 1208 us; half a symbol about 604 us |
| Wake-up | 9415 us high, 89565 us low, before the first frame only |
| Hardware sync | about 2416 us high and 2416 us low; 2 pairs on the |
| | first frame, 7 on repeats |
| Software sync | about 4550 us high, then about 604 us low |
| Payload | 56 bits, 7 bytes, MSB first from byte 0 |
| Byte 0 | key: 0xA and a counter (one commenter: the 0xA varies) |
| Byte 1 | command (upper nibble), checksum (lower nibble) |
| Bytes 2, 3 | rolling code, 16 bits, big-endian |
| Bytes 4 to 6 | address, 24 bits, little-endian |
| Obfuscation | each byte from byte 1 on is XORed with the byte sent |
| | before it |
| Checksum | the XOR of all 14 nibbles is 0 |
| Gap | about 30415 us, half a symbol longer after a final 0 |

What follows (derived): HAIR's frame cut drops the wake-up mark (a piece
with no body) and keeps each frame from its first sync pair to the gap.
The decoder takes the half-symbol from the sync pairs (2416 is four
halves), so a stretched clock is read at its own pace. A frame whose
checksum fails is not read at all. Shown: the address and the command,
as a number (ruling 2026-11-14). The rolling code and the key change on
every press and are never shown.

SPEC TABLE: Dooya (held off)
============================

Three sources, re-read 2026-11-14. The timing agrees across all three,
two of them independent measurements; the field layout does not.

- ESPHome ``dooya_protocol.cpp`` (C++, GPL-3.0; read for facts only):
  https://api-docs.esphome.io/dooya__protocol_8cpp_source
- Flipper forum thread "Dooya and clones" (r15ch13, a DC174/DC90
  remote; Z4urce, a copy remote), measured:
  https://forum.flipper.net/t/dooya-and-clones-electric-roller-shutters-blinds/9369
- MySensors forum thread (petewill, an Audacity trace of a DV24CE
  remote), measured: https://forum.mysensors.org/post/13556

| Fact | ESPHome | Flipper forum | MySensors |
|---|---|---|---|
| Header | 5000 mark, 1500 space | sync about 4800 | 4812 mark, 1479 space |
| Zero | 350 mark, 750 space | 350 short, 720 long | 376-395 mark, 653-687 space |
| One | 750 mark, 350 space | | 713-750 mark, 317-333 space |
| Bits | 40, MSB first | 40 | 40 |
| After the 24-bit id | [GPL only] channel 8, button | 4 bits, channel 4, key 8 | none named |
| | 4, check 4 | | |
| Last bit | [GPL only] a mark, no space | | |

What follows (derived): a header pair, then 40 mark-first pairs of
about 3 units, 1:2 or 2:1, a long mark for 1. Shown: ``remote`` (the
24-bit id, in which the layouts agree) and ``code`` (the other 16 bits
as hex); no channel or button split until a real capture settles it
(ruling 2026-11-14). No source gives the gap between repeats. HAIR cuts
frames on long spaces only, so a press sent back to back (header, bits,
header) is one piece and gives no frame today; a cut before a long
header mark waits for a real capture (ruling 2026-11-14).

SPEC TABLE: Nexa self-learning (held off)
=========================================

No chip datasheet exists; this is a microcontroller protocol. Two
community descriptions, re-read 2026-11-14; neither states a license,
and facts only were taken:

- elektronikforumet wiki, "RF Protokoll - Proove self learning":
  https://elektronikforumet.com/wiki/index.php/RF_Protokoll_-_Proove_self_learning
- RFLink-ESP, KlikAanKlikUit (Stef Mientki, with scope measurements):
  https://stef-aap.github.io/RFLink-ESP/KlikAanKlikUit.html

| Fact | elektronikforumet | RFLink-ESP |
|---|---|---|
| T | | 275 us (375 also works); measured 260 and 262 |
| Wire bits | | 1 T high, then 1 T or 5 T low (3.4 T also works) |
| Logical bits | two wire bits, the second the inverse; | 0 is T,T,T,5T; 1 is T,5T,T,T |
| | 0 is 01, 1 is 10 | |
| Start | a sync bit | T high, about 10 T low (2940 us measured) |
| Stop | a pause bit | T high, about 39 T low (10511 us measured) |
| Layout | id 26, group 1, on/off 1, channel 2, | address 26, group 1, on/off/dim 1, |
| | unit 2 | unit 4 |
| On/off bit | 0 is on | on is 1 |
| Units | #1 is 00, #2 01, #3 10 | A is 1010, B 1011 |
| Dim | | the on/off slot as T,T,T,T, then 4 dim bits after the unit |
| Repeats | 4 | 10 to 20 |
| Names | Proove | KlikAanKlikUit, KAKU, COCO |

The label word "Nexa" is not sourced for this family: neither page names
it. It stands while the family is off, as the name HAIR's research
filed these codes under (old Nexa's page names Nexa for the older
codes); the real capture that turns this family on settles the word from what
the remote says on its case (ruling 2026-11-14).

What follows (derived): HAIR's frame is the start pair, 64 wire bits (72
with dim) and the stop mark, the stop's low as the gap. Every mark is
one width; the receive path hears it as a pulse-distance body. Both
sources agree on which wire pair is 1. They
disagree on the on/off bit; the state follows elektronikforumet (0 is
on), recorded as such, until a real capture of a known press (plan
answer 2026-11-14). The unit is shown as its 4-bit number, since the
sources number units differently.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from statistics import median
from typing import Any

from .identity import canonical_edges

_LOGGER = logging.getLogger(__name__)

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
            aliases=("HT6P20B2", "HT6P20D2", "HT6P20F2"),
            shown=True,
            evidence="Holtek HT6P20B2/D2/F2 datasheet Rev 1.10 (shown on the "
                     "datasheet alone, ruling 2026-11-14)",
        ),
        FamilySpec(
            "came", "CAME",
            aliases=("CAME TOP-432", "CAME TAM-432"),
            shown=False,
            evidence="Flipper forum measurements, rtl_433 CAME-TOP432.conf, "
                     "Flipper-lineage came.c (facts only); held off until a "
                     "real capture (ruling 2026-11-14)",
        ),
        FamilySpec(
            "nice_flo", "Nice FLO",
            shown=False,
            evidence="Flipper-lineage nice_flo.c (one lineage, facts only); "
                     "held off until a real capture (ruling 2026-11-14)",
        ),
        FamilySpec(
            "nexa_old", "Nexa",
            # The page's own title: "The NEXA/PROOVE Remote Protocol".
            aliases=("Proove",),
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
        FamilySpec(
            "somfy_rts", "Somfy RTS",
            shown=False,
            evidence="PushStack write-up (one source); held off until a "
                     "real capture (ruling 2026-11-14); detection only",
        ),
        FamilySpec(
            "dooya", "Dooya",
            shown=False,
            evidence="ESPHome dooya_protocol.cpp (facts only), Flipper forum "
                     "and MySensors forum measurements; held off until a "
                     "real capture (ruling 2026-11-14)",
        ),
        FamilySpec(
            "nexa_sl", "Nexa",
            # Proove: elektronikforumet's title. KlikAanKlikUit and COCO:
            # RFLink-ESP's ("KlikAanKlikUit (KAKU, COCO)"). Neither page
            # names Nexa; the label word waits on a ruling.
            aliases=("Proove", "KlikAanKlikUit", "COCO"),
            shown=False,
            evidence="elektronikforumet wiki and RFLink-ESP descriptions; "
                     "held off until a real capture",
        ),
    )
}


@dataclass(frozen=True)
class _Fit:
    """One family a shape decoder found the frame fits."""

    key: str
    fields: tuple[tuple[str, str], ...]
    # A rolling family's changing part (the KeeLoq encrypted word, the
    # Somfy counter), for the replay check only: never a field, never
    # shown or logged.
    rolling: int | None = field(default=None, repr=False, compare=False)


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
    label) and ``family_fields`` (the fields as name and value).

    A label never costs the drawer its line: a decoder failure is logged
    at debug and the event goes out with no label.
    """
    try:
        result = family_of(frame)
    except Exception:
        _LOGGER.debug("Radio family label failed", exc_info=True)
        result = None
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


def _fitting_reads(frame: tuple[int, ...]) -> tuple[_ShapeRead, ...]:
    """Every shape that fits the frame, in ``_SHAPES`` order.

    One walk shared by the label, the rolling check and the rolling
    identity, each of which caches its own answer. Hidden families
    count: a shape that fits only hidden families still fits. Two shapes
    fitting one frame should not happen (each family's tests have every
    other shape refuse its frames), but a damaged frame could, and then
    nothing is taken from either.

    A decoder that raises is skipped, logged at warning, and the other
    shapes' reads are kept: one broken decoder must not throw away the
    rolling answer of the shape that did fit.
    """
    # Not cached on purpose. The three readers above cache their own
    # answers, and a cache here would outlive a test that swaps
    # ``_SHAPES``. A frame goes through every decoder at most four times
    # (the three readers and ``fits_two_shapes`` once per press), which
    # is nothing at radio rates.
    # ``_SHAPES`` is defined below its decoders.
    reads = []
    for decode in _SHAPES:
        try:
            read = decode(frame)
        except Exception:
            _LOGGER.warning(
                "Radio family decoder %s failed; its shape is skipped",
                getattr(decode, "__name__", decode), exc_info=True,
            )
            continue
        if read is not None and read.fits:
            reads.append(read)
    return tuple(reads)


def fits_two_shapes(frame: list[int] | tuple[int, ...] | None) -> bool:
    """True when more than one shape fits the frame: HAIR can't tell
    which kind of remote sent it, so it gets no family, no rolling
    identity, and counts as rolling. Fails to False, logged at warning."""
    if not frame:
        return False
    try:
        return len(_fitting_reads(tuple(int(v) for v in frame))) > 1
    except Exception:
        _LOGGER.warning("Radio family check failed", exc_info=True)
        return False


@lru_cache(maxsize=1024)
def _family_of(frame: tuple[int, ...], include_hidden: bool) -> RfFamily | None:
    # One shape that fits gives the label, even when all it fits are
    # hidden families. Two shapes that fit give none: no pill rather
    # than a guess.
    reads = _fitting_reads(frame)
    if len(reads) != 1:
        return None
    return _label(reads[0], include_hidden)


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
        # One family alone gets its own fields. When more than one fits,
        # shown or hidden, the fields are the shape's shared ones, so an
        # HT12E that CAME also fits never shows an address/data split the
        # frame does not prove (ruling 2026-11-15).
        fields=shown[0].fields if len(read.fits) == 1 else (read.shared or shown[0].fields),
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
_SF_BITS = (12, 24, 28)
# Every bit is 3 T; one may sit this far from the frame's median bit
# (the same allowance as the 1:3 shape, for the same receivers).
_SF_PAIR_TOLERANCE = 0.30
# (long - short) / T: 1 for 1:2, 2 for a 1:3 frame read in this shape.
_SF_SPLIT_MIN = 0.7
_SF_SPLIT_MAX = 1.4
# The start mark is 1 T: no longer than this many short marks.
_SF_START_MAX_SHORT_MARKS = 1.6
# The unit a CAME remote sends (320 us; +/- 150 in the GPL lineage
# only; 250 shown to work on the forum): a frame of this shape whose T
# falls here also fits CAME.
_CAME_T_US = (220.0, 450.0)
# Nice FLO's unit (700 us, +/- 200 in the one lineage that reads it).
_NICE_FLO_T_US = (500.0, 900.0)
# The pilot before the start mark is 12 bit-times (36 T) on the HT12E;
# a receiver may cut it shorter, and other families of this shape send
# up to about 76 T.
_SF_GAP_MIN_T = 12.0
_SF_GAP_MAX_T = 90.0


def _hex(bits: str) -> str:
    """Bits as hex, the first bit sent as the most significant."""
    return f"{int(bits, 2):0{(len(bits) + 3) // 4}X}"


def _sf_fields(bits: str) -> tuple[tuple[str, str], ...]:
    """A gate remote's code: 12 bits also as the switches read (``bits``),
    always hex as ``code`` (one meaning per field, ruling 2026-11-14)."""
    if len(bits) == 12:
        return (("bits", bits), ("code", _hex(bits)))
    return (("code", _hex(bits)),)


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
    if bits_n in (12, 24) and "came" in FAMILIES and (
        _CAME_T_US[0] <= unit <= _CAME_T_US[1]
    ):
        fits.append(_Fit("came", _sf_fields(bits)))
    if bits_n in (12, 24) and "nice_flo" in FAMILIES and (
        _NICE_FLO_T_US[0] <= unit <= _NICE_FLO_T_US[1]
    ):
        fits.append(_Fit("nice_flo", _sf_fields(bits)))
    if bits_n == 28 and bits[24:] == "0101" and "ht6p20" in FAMILIES:
        fits.append(_Fit("ht6p20", (("code", f"{int(bits[:24], 2):06X}"),)))
    return _ShapeRead(
        unit_us, tuple(fits), shared=(("bits", bits), ("code", _hex(bits))),
    )


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
    hopping = sum(bit << index for index, bit in enumerate(bits[:32]))
    return _ShapeRead(round(unit), (_Fit("keeloq", tuple(fields), hopping),))


# ---------------------------------------------------------------------------
# Shape: Manchester after sync pairs (Somfy RTS)
# ---------------------------------------------------------------------------

# Hardware sync pairs before the software sync: 2 on a press's first
# frame, 7 on its repeats.
_SOMFY_SYNC_PAIRS = (2, 7)
# How far a sync edge may stray from the sync pairs' median.
_SOMFY_SYNC_TOLERANCE = 0.30
# The software sync mark, in half-symbols (4550 / 604 is about 7.5).
_SOMFY_SOFT_SYNC_HALVES = (6.0, 9.0)
# One half-symbol or two, read from a measured width.
_SOMFY_ONE_HALF = (0.5, 1.5)
_SOMFY_TWO_HALVES = (1.5, 2.6)
_SOMFY_BITS = 56


def _somfy_halves(width: float, half: float) -> int | None:
    ratio = width / half
    if _SOMFY_ONE_HALF[0] <= ratio < _SOMFY_ONE_HALF[1]:
        return 1
    if _SOMFY_TWO_HALVES[0] <= ratio <= _SOMFY_TWO_HALVES[1]:
        return 2
    return None


def _manchester_somfy(frame: tuple[int, ...]) -> _ShapeRead | None:
    """Sync pairs, a software sync, then 56 Manchester bits.

    HAIR's frame starts on the first sync mark; the gap is last. Each
    width after the software sync is one half-symbol or two, high on a
    mark and low on a space; the software sync's own low half comes
    first and is dropped. A final 0 ends on a low half that runs into
    the gap, so a stream one half short gets it back.
    """
    edges = canonical_edges(list(frame))
    pairs = 0
    while 2 * pairs + 2 < len(edges) and edges[2 * pairs] < 2.5 * edges[2 * pairs + 1]:
        pairs += 1
        if pairs > _SOMFY_SYNC_PAIRS[1]:
            return None
    if not _SOMFY_SYNC_PAIRS[0] <= pairs <= _SOMFY_SYNC_PAIRS[1]:
        return None
    sync = edges[: 2 * pairs]
    typical = median(sync)
    if typical <= 0 or any(
        abs(width - typical) > _SOMFY_SYNC_TOLERANCE * typical for width in sync
    ):
        return None
    half = typical / 4.0
    soft = edges[2 * pairs] / half
    if not _SOMFY_SOFT_SYNC_HALVES[0] <= soft <= _SOMFY_SOFT_SYNC_HALVES[1]:
        return None
    levels: list[int] = []
    level = 0
    for width in edges[2 * pairs + 1:]:
        count = _somfy_halves(width, half)
        if count is None:
            return None
        levels += [level] * count
        level ^= 1
    levels = levels[1:]
    if len(levels) == 2 * _SOMFY_BITS - 1:
        levels.append(0)
    if len(levels) != 2 * _SOMFY_BITS:
        return None
    bits: list[int] = []
    for first, second in zip(levels[0::2], levels[1::2], strict=True):
        if first == second:
            return None
        bits.append(second)
    sent = [
        int("".join(map(str, bits[8 * i: 8 * i + 8])), 2) for i in range(7)
    ]
    plain = [sent[0]] + [sent[i] ^ sent[i - 1] for i in range(1, 7)]
    check = 0
    for byte in plain:
        check ^= (byte >> 4) ^ (byte & 0x0F)
    if check:
        return None
    if "somfy_rts" not in FAMILIES:
        return _ShapeRead(round(half), ())
    address = plain[4] | plain[5] << 8 | plain[6] << 16
    return _ShapeRead(round(half), (_Fit("somfy_rts", (
        ("address", f"{address:06X}"),
        ("command", str(plain[1] >> 4)),
    ), plain[2] << 8 | plain[3]),))


# ---------------------------------------------------------------------------
# Shape: a long header pair, then mark-first 1:2 and 2:1 pairs (Dooya)
# ---------------------------------------------------------------------------

_DOOYA_BITS = 40
# Every bit is about 3 units (350 and 750 us).
_HD_PAIR_TOLERANCE = 0.30
_HD_SPLIT_MIN = 0.7
_HD_SPLIT_MAX = 1.4
# The header in units: 5000 / 367 is about 13.6, 1500 / 367 about 4.1.
_DOOYA_HEADER_MARK_UNITS = (10.0, 18.0)
_DOOYA_HEADER_SPACE_UNITS = (3.0, 5.5)


def _header_mark_first_1_2(frame: tuple[int, ...]) -> _ShapeRead | None:
    """A header mark and space, then 40 bits of a mark and a space.

    The last bit's space runs into the gap, so the frame holds the
    header pair, 40 marks and the 39 spaces between them. A one is the
    long mark (all three sources).
    """
    edges = canonical_edges(list(frame))
    if len(edges) != 2 + 2 * _DOOYA_BITS - 1:
        return None
    marks = edges[2::2]
    spaces = edges[3::2]
    sums = [m + s for m, s in zip(marks, spaces, strict=False)]
    typical = median(sums)
    if typical <= 0 or any(
        abs(total - typical) > _HD_PAIR_TOLERANCE * typical for total in sums
    ):
        return None
    unit = typical / 3.0
    if not _DOOYA_HEADER_MARK_UNITS[0] <= edges[0] / unit <= _DOOYA_HEADER_MARK_UNITS[1]:
        return None
    if not _DOOYA_HEADER_SPACE_UNITS[0] <= edges[1] / unit <= _DOOYA_HEADER_SPACE_UNITS[1]:
        return None
    cut = (min(marks) + max(marks)) / 2.0
    short_marks = [m for m in marks if m < cut]
    long_marks = [m for m in marks if m >= cut]
    if not short_marks or not long_marks:
        return None
    split = (median(long_marks) - median(short_marks)) / unit
    if not _HD_SPLIT_MIN <= split <= _HD_SPLIT_MAX:
        return None
    bits = "".join("1" if m >= cut else "0" for m in marks)
    if "dooya" not in FAMILIES:
        return _ShapeRead(round(unit), ())
    return _ShapeRead(round(unit), (_Fit("dooya", (
        ("remote", f"{int(bits[:24], 2):06X}"),
        ("code", f"{int(bits[24:], 2):04X}"),
    )),))


# ---------------------------------------------------------------------------
# Shape: one mark width, short and long spaces (Nexa self-learning)
# ---------------------------------------------------------------------------

# Wire bits: 32 logical bits as pairs, or 36 with a dim level.
_SL_WIRE_BITS = (64, 72)
# A long wire bit's mark and space over a short one's: 6 T over 2 T,
# or 4.4 T with the 3.4 T space that also works.
_SL_LONG_OVER_SHORT = (1.8, 3.6)
# The start's low, in T (9 to 11 T in the sources).
_SL_START_T = (7.0, 13.0)
# A mark may stretch to this many T before it is not one width.
_SL_MARK_MAX_T = 2.0
# The logical bit whose slot becomes the dim symbol (bit 28).
_SL_STATE_BIT = 27


def _distance_1_5(frame: tuple[int, ...]) -> _ShapeRead | None:
    """A start pair, wire bits of one mark and a short or long space,
    then the stop mark; the stop's low is the gap.

    Two wire bits make one logical bit: short then long is 0, long then
    short is 1 (both sources). Two short wire bits in the on/off slot
    are the dim symbol, and then four dim bits follow the unit.
    """
    edges = canonical_edges(list(frame))
    wire_n = (len(edges) - 3) // 2
    if len(edges) % 2 != 1 or wire_n not in _SL_WIRE_BITS:
        return None
    marks = edges[0::2]
    spaces = edges[3:-1:2]
    pairs = [m + s for m, s in zip(edges[2:-1:2], spaces, strict=True)]
    cut = (min(pairs) + max(pairs)) / 2.0
    short = [p for p in pairs if p < cut]
    long = [p for p in pairs if p >= cut]
    if not short or not long or median(short) <= 0:
        return None
    t = median(short) / 2.0
    ratio = median(long) / median(short)
    if not _SL_LONG_OVER_SHORT[0] <= ratio <= _SL_LONG_OVER_SHORT[1]:
        return None
    if max(marks) > _SL_MARK_MAX_T * t:
        return None
    if not _SL_START_T[0] <= edges[1] / t <= _SL_START_T[1]:
        return None
    wire = [1 if p >= cut else 0 for p in pairs]
    bits: list[int | None] = []
    for index, (first, second) in enumerate(zip(wire[0::2], wire[1::2], strict=True)):
        if first != second:
            bits.append(first)
        elif first == 0 and index == _SL_STATE_BIT:
            bits.append(None)
        else:
            return None
    dimmed = bits[_SL_STATE_BIT] is None
    if dimmed != (len(bits) == 36):
        return None
    if "nexa_sl" not in FAMILIES:
        return _ShapeRead(round(t), ())

    def number(part: list[int | None]) -> int:
        return int("".join(str(bit) for bit in part), 2)

    state = "dim" if dimmed else "on" if bits[_SL_STATE_BIT] == 0 else "off"
    fields: list[tuple[str, str]] = [
        ("id", f"{number(bits[:26]):07X}"),
        ("group", str(bits[26])),
        ("state", state),
        ("unit", str(number(bits[28:32]))),
    ]
    if dimmed:
        fields.append(("dim", str(number(bits[32:36]))))
    return _ShapeRead(round(t), (_Fit("nexa_sl", tuple(fields)),))


_SHAPES = (
    _pt2262_ev1527, _space_first_1_2, _mark_first_1_2, _manchester_somfy,
    _header_mark_first_1_2, _distance_1_5,
)


# ---------------------------------------------------------------------------
# Rolling codes: never sent
# ---------------------------------------------------------------------------

# The families whose code changes on every press. HAIR never sends one:
# a saved one won't work a second time.
ROLLING_FAMILIES = frozenset({"keeloq", "somfy_rts"})


def rolling_family(frame: list[int] | tuple[int, ...] | None) -> str | None:
    """The rolling family a frame reads as, or None.

    Hidden families count: a frame is refused for what it is, not for
    what the pill shows, so Somfy RTS is caught while its label is off.
    A frame that is not a clean read of one (a partial KeeLoq word, a
    Somfy frame whose checksum fails) is not caught, and is sent as any
    other radio code.

    A decoder that raises gives None, logged at warning: a bug here must
    not stop every radio send, and None is how HAIR sent before this
    check existed.
    """
    if not frame:
        return None
    try:
        return _rolling_family(tuple(int(v) for v in frame))
    except Exception:
        _LOGGER.warning(
            "Radio rolling-code check failed; the code is treated as fixed",
            exc_info=True,
        )
        return None


@lru_cache(maxsize=1024)
def _rolling_family(frame: tuple[int, ...]) -> str | None:
    # Rolling if any shape that fits reads it as rolling, so a frame two
    # shapes fit is refused when either says it changes on every press.
    for read in _fitting_reads(frame):
        for fit in read.fits:
            if fit.key in ROLLING_FAMILIES:
                return fit.key
    return None


# ---------------------------------------------------------------------------
# Rolling codes: identity from the fixed part
# ---------------------------------------------------------------------------

# The fixed fields of each rolling family, in identity order: who sent it
# and which button. KeeLoq's low battery and repeat bits sit in the clear
# part too but change between presses, so they are left out.
_ROLLING_FIXED = {
    "keeloq": ("serial", "buttons"),
    "somfy_rts": ("address", "command"),
}
# What a KeeLoq word with all four buttons carries: a seed, sent to pair a
# receiver, in place of the encrypted part.
KEELOQ_SEED_BUTTONS = "all (seed)"


@dataclass(frozen=True)
class RollingIdentity:
    """A clean read of a rolling-code frame, split into its two parts.

    ``fingerprint`` is the row's decoded identity: the family and the
    fixed fields only, so every press of one button is the same code.
    ``remote`` keys a remote (KeeLoq serial, Somfy address) and
    ``button`` one of its buttons. ``rolling`` is the part that changes on
    every press, held for the replay check and nothing else.
    """

    family: str
    remote: str
    button: str
    rolling: int | None = field(default=None, repr=False, compare=False)

    @property
    def fingerprint(self) -> str:
        return f"RF:{self.family}:{self.remote}:{self.button}"

    @property
    def device_key(self) -> str:
        """The Sniffer card: one per remote."""
        return f"DEV:RF:{self.family}:{self.remote}"

    @property
    def seed(self) -> bool:
        """A KeeLoq pairing word rather than a button press."""
        return self.family == "keeloq" and self.button == KEELOQ_SEED_BUTTONS


def rolling_identity(
    frame: list[int] | tuple[int, ...] | None,
) -> RollingIdentity | None:
    """The fixed-part identity of a rolling-code frame, or None.

    Only a clean read of exactly one rolling family counts: a frame two
    families fit, or one a decoder only half reads, keeps the identity
    every other radio frame has. Fails open to None, logged at warning,
    as ``rolling_family`` does.
    """
    if not frame:
        return None
    try:
        return _rolling_identity(tuple(int(v) for v in frame))
    except Exception:
        _LOGGER.warning(
            "Radio rolling-code identity failed; the code keeps its frame identity",
            exc_info=True,
        )
        return None


@lru_cache(maxsize=1024)
def _rolling_identity(frame: tuple[int, ...]) -> RollingIdentity | None:
    # Only when exactly one shape fits: a frame two shapes fit keeps the
    # identity every other radio frame has (and is still never sent).
    reads = _fitting_reads(frame)
    if len(reads) != 1:
        return None
    read = reads[0]
    if len(read.fits) != 1 or read.fits[0].key not in _ROLLING_FIXED:
        return None
    fit = read.fits[0]
    values = dict(fit.fields)
    remote_name, button_name = _ROLLING_FIXED[fit.key]
    if remote_name not in values or button_name not in values:
        return None
    return RollingIdentity(
        family=fit.key,
        remote=values[remote_name],
        button=values[button_name],
        rolling=fit.rolling,
    )
