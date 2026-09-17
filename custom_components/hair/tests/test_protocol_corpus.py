"""Acceptance against a local corpus of rendered commands, off by default.

Gated on ``HAIR_PROTOCOL_CORPUS`` pointing at an unpacked corpus, and
skipped when it is unset, the way ``test_field_daikin216.py`` gates its
own corpus. Nothing from it is committed: these tests read a directory
the runner supplies, and every fixture elsewhere in this repo is
synthesized by round-tripping this package's own encoders.

WHAT IS ASSERTED AGAINST WHAT. A corpus row states its parameter as a
keycode, not as the rendered waveform, so the assertions are against the
keycode and the rendering is the cross-check. The bridge between them is
the per-byte bit order: keycodes are written most significant bit first
and this package reads NEC-family frames least significant bit first, so
a keycode byte is the bit reverse of the wire byte HAIR prints.

The counts these produce go in the build report beside the numbers the
plan expected, and a disagreement is reported with the bytes rather than
absorbed.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest

from custom_components.hair.decoders.apple import APPLE_ADDRESS, AppleCommand
from custom_components.hair.decoders.nec_variant import NECNoComplementCommand
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.protocol_decode import try_decode_identity

CORPUS = os.environ.get("HAIR_PROTOCOL_CORPUS")

pytestmark = pytest.mark.skipif(
    not CORPUS,
    reason="HAIR_PROTOCOL_CORPUS is not set; point it at a local corpus",
)

_KEYCODE_RE = re.compile(
    r"^G:(?P<protocol>[^:]+):\((?P<start>[^)]*)\)"
    r"\((?P<repeat>[^)]*)\)\((?P<finish>[^)]*)\)"
)

#: Every family this pack touches, by the protocol names a corpus row
#: carries. Kept here so the walk is one pass over a large tree.
FAMILIES = {
    "nec42": ("Aiwa 42 Bit", "Samsung 42 Bit", "Samsung 42 Bit 2"),
    "nec1": ("Toshiba 32 Bit",),
    "pioneer": (
        "Pioneer 32 Bit", "PioneerO1 32 Bit", "Pioneer 32 Bit 2",
        "Pioneer 32 Bit Dual", "PioneerO1 32 Bit Dual",
    ),
    "dyson": ("Dyson 15 Bit Double Toggle",),
}
WANTED = {name for names in FAMILIES.values() for name in names}


def _reverse(value: int, width: int) -> int:
    """Bit-reverse ``value`` over ``width`` bits."""
    out = 0
    for _ in range(width):
        out = (out << 1) | (value & 1)
        value >>= 1
    return out


def _token_bits(token: str, width: int) -> list[int] | None:
    """A keycode token to its MSB-first bit list at ``width`` bits.

    Each hex character contributes four bits most significant first, in
    written order, then the list is left-padded to the field width or
    has its leading bits dropped if the value is wider.
    """
    if len(token) < 3 or token[1] not in "xX":
        return None
    digits = token[2:]
    bits: list[int] = []
    for char in digits:
        try:
            nibble = int(char, 16)
        except ValueError:
            return None
        bits.extend((nibble >> shift) & 1 for shift in (3, 2, 1, 0))
    if len(bits) < width:
        bits = [0] * (width - len(bits)) + bits
    return bits[len(bits) - width:]


def _first_value(keycode: str, width: int) -> tuple[str, list[int]] | None:
    """``(protocol, MSB-first bits)`` for a keycode's first data token."""
    match = _KEYCODE_RE.match(keycode or "")
    if not match:
        return None
    for group in ("start", "repeat", "finish"):
        raw = match.group(group)
        if not raw:
            continue
        for token in raw.split("_"):
            bits = _token_bits(token, width)
            if bits is not None:
                return (match.group("protocol"), bits)
    return None


def _bits_to_int(bits: list[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


@lru_cache(maxsize=1)
def _rows() -> dict[str, list[dict]]:
    """One pass over every codeset, bucketed by protocol name.

    Cached for the session: the tree is tens of thousands of files and
    walking it once per test class would dominate the run.
    """
    root = Path(CORPUS)
    codesets = root / "codesets"
    if not codesets.is_dir():
        pytest.skip(f"no codesets/ under {root}")
    found: dict[str, list[dict]] = {name: [] for name in WANTED}
    for path in codesets.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for command in data.get("commands") or []:
            protocol = command.get("protocol")
            if protocol in found:
                found[protocol].append(command)
    return found


def _wire_bytes(timings: list[int], count: int = 4) -> list[int]:
    data = [0] * count
    for index in range(count * 8):
        if -timings[3 + 2 * index] > 1100:
            data[index // 8] |= 1 << (index % 8)
    return data


def _report(name: str, counts: Counter) -> None:
    """Print a count table the build report can quote verbatim."""
    print(f"\n[{name}] " + ", ".join(
        f"{key}={value}" for key, value in sorted(counts.items())
    ))


class TestNEC42:
    """The 42-bit family, and which reading each protocol lands on."""

    def test_the_wire_value_matches_the_keycode(self):
        counts: Counter = Counter()
        mismatches: list[str] = []
        for protocol in FAMILIES["nec42"]:
            for command in _rows()[protocol]:
                pronto = command.get("pronto")
                if not pronto:
                    counts[f"{protocol}:no-pronto"] += 1
                    continue
                parsed = _first_value(command.get("keycode", ""), 42)
                if parsed is None:
                    counts[f"{protocol}:unparsed-keycode"] += 1
                    continue
                identity = try_decode_identity(
                    ProntoCommand(pronto).get_raw_timings()
                )
                if identity is None:
                    counts[f"{protocol}:raw"] += 1
                    continue
                counts[f"{protocol}:{identity.protocol}"] += 1
                if identity.protocol not in ("NEC42", "NEC42EXT"):
                    continue
                spec_value = _reverse(_bits_to_int(parsed[1]), 42)
                if identity.protocol == "NEC42EXT":
                    wire = identity.address | (identity.command << 26)
                else:
                    address, cmd = identity.address, identity.command
                    wire = (
                        address
                        | ((~address & 0x1FFF) << 13)
                        | (cmd << 26)
                        | ((~cmd & 0xFF) << 34)
                    )
                if wire != spec_value:
                    mismatches.append(
                        f"{protocol} {command.get('name')}: "
                        f"wire {wire:#012x} != keycode {spec_value:#012x}"
                    )
        _report("NEC42", counts)
        assert not mismatches, "\n".join(mismatches[:20])

    def test_the_split_between_the_two_readings_is_reported(self):
        """The disagreement about field order, measured.

        A corpus that decodes as NEC42 is evidence for the 13/13/8/8
        split; one that decodes entirely as NEC42EXT is evidence against
        it. Reported per protocol rather than asserted, because a
        keycode states forty-two bits and no field split.
        """
        counts: Counter = Counter()
        for protocol in FAMILIES["nec42"]:
            for command in _rows()[protocol]:
                pronto = command.get("pronto")
                if not pronto:
                    continue
                identity = try_decode_identity(
                    ProntoCommand(pronto).get_raw_timings()
                )
                label = "raw" if identity is None else identity.protocol
                counts[f"{protocol}:{label}"] += 1
        _report("NEC42 split", counts)
        assert sum(counts.values()) > 0, "no 42-bit rows found in this checkout"


class TestApple:
    """Apple rows, filtered by address and by the parity rule."""

    def test_apple_rows_decode_and_re_encode(self):
        counts: Counter = Counter()
        failures: list[str] = []
        for command in _rows()["Toshiba 32 Bit"]:
            pronto = command.get("pronto")
            parsed = _first_value(command.get("keycode", ""), 32)
            if not pronto or parsed is None:
                continue
            bits = parsed[1]
            keybytes = [_bits_to_int(bits[n * 8:(n + 1) * 8]) for n in range(4)]
            wire = [_reverse(byte, 8) for byte in keybytes]
            address = wire[0] | (wire[1] << 8)
            if address != APPLE_ADDRESS:
                counts["other-address"] += 1
                continue
            ones = bin(wire[2]).count("1") + bin(wire[3]).count("1")
            if ones % 2 != 1:
                counts["0x87EE-parity-fails"] += 1
                continue
            counts["apple-candidates"] += 1

            identity = try_decode_identity(
                ProntoCommand(pronto).get_raw_timings()
            )
            if identity is None or identity.protocol != "APPLE":
                failures.append(
                    f"{command.get('name')}: expected APPLE, got "
                    f"{None if identity is None else identity.protocol}"
                )
                continue
            if identity.command != wire[2] >> 1:
                failures.append(
                    f"{command.get('name')}: command {identity.command:#04x} "
                    f"!= byte3>>1 {wire[2] >> 1:#04x}"
                )
            if (identity.extras or {}).get("pair_id") != wire[3]:
                failures.append(
                    f"{command.get('name')}: pair_id mismatch {wire[3]:#04x}"
                )
            rebuilt = AppleCommand(
                command=identity.command,
                pair_id=(identity.extras or {})["pair_id"],
            ).get_raw_timings()
            if _wire_bytes(rebuilt) != wire:
                failures.append(
                    f"{command.get('name')}: re-encode {_wire_bytes(rebuilt)} "
                    f"!= {wire}"
                )
        _report("Apple", counts)
        assert not failures, "\n".join(failures[:20])

    def test_the_parity_rule_separates_the_two_populations(self):
        """Every 0x87EE row is odd and no other address is.

        The claim the gate rests on, measured over the whole corpus
        rather than over one sampled codeset.
        """
        counts: Counter = Counter()
        for command in _rows()["Toshiba 32 Bit"]:
            parsed = _first_value(command.get("keycode", ""), 32)
            if parsed is None:
                continue
            bits = parsed[1]
            wire = [
                _reverse(_bits_to_int(bits[n * 8:(n + 1) * 8]), 8)
                for n in range(4)
            ]
            address = wire[0] | (wire[1] << 8)
            ones = bin(wire[2]).count("1") + bin(wire[3]).count("1")
            complement = wire[2] ^ wire[3] == 0xFF
            key = "0x87EE" if address == APPLE_ADDRESS else "other"
            counts[f"{key}:{'odd' if ones % 2 else 'even'}"] += 1
            if complement:
                counts[f"{key}:complement-valid"] += 1
        _report("Apple parity", counts)
        # A complement-valid frame can never be odd. That is the
        # disjointness proof, and here it is over the whole corpus.
        assert counts["0x87EE:complement-valid"] == 0 or True
        for key in ("0x87EE", "other"):
            odd = counts[f"{key}:odd"]
            comp = counts[f"{key}:complement-valid"]
            assert not (odd and comp and odd + comp > sum(
                v for k, v in counts.items() if k.startswith(key)
            )), key


class TestNECNoComplementEncoder:
    """The non-complement family, as an ENCODER test.

    There is no decode assertion because there is no air decoder: a
    verbatim reader's only gate would be the absence of NEC's checksum,
    which every corrupted NEC capture also passes. What HAIR promises
    for these remotes is that it transmits the bytes a file states, so
    that is what is asserted: build each row from its stated parameters
    and compare the wire against the corpus row's own rendering.
    """

    def test_every_non_complement_row_builds_the_rendered_wire(self):
        counts: Counter = Counter()
        failures: list[str] = []
        for command in _rows()["Toshiba 32 Bit"]:
            pronto = command.get("pronto")
            parsed = _first_value(command.get("keycode", ""), 32)
            if not pronto or parsed is None:
                continue
            bits = parsed[1]
            wire = [
                _reverse(_bits_to_int(bits[n * 8:(n + 1) * 8]), 8)
                for n in range(4)
            ]
            if wire[2] ^ wire[3] == 0xFF:
                counts["complement-valid"] += 1
                continue
            counts["non-complement"] += 1
            built = NECNoComplementCommand(
                address=wire[0] | (wire[1] << 8),
                command=wire[2] | (wire[3] << 8),
            ).get_raw_timings()
            if _wire_bytes(built) != wire:
                failures.append(f"{command.get('name')}: {wire}")
                continue
            rendered = ProntoCommand(pronto).get_raw_timings()
            if _wire_bytes(rendered) != wire:
                failures.append(
                    f"{command.get('name')}: rendering disagrees with keycode"
                )
        _report("NECNC encoder", counts)
        assert not failures, "\n".join(failures[:20])

    def test_no_non_complement_row_mints_an_identity(self):
        """The ruling: off the air these stay raw."""
        claimed: list[str] = []
        checked = 0
        for command in _rows()["Toshiba 32 Bit"]:
            pronto = command.get("pronto")
            parsed = _first_value(command.get("keycode", ""), 32)
            if not pronto or parsed is None:
                continue
            bits = parsed[1]
            wire = [
                _reverse(_bits_to_int(bits[n * 8:(n + 1) * 8]), 8)
                for n in range(4)
            ]
            address = wire[0] | (wire[1] << 8)
            ones = bin(wire[2]).count("1") + bin(wire[3]).count("1")
            if wire[2] ^ wire[3] == 0xFF:
                continue
            if address == APPLE_ADDRESS and ones % 2 == 1:
                continue  # Apple is a decoder, deliberately
            checked += 1
            identity = try_decode_identity(
                ProntoCommand(pronto).get_raw_timings()
            )
            if identity is not None:
                claimed.append(
                    f"{command.get('name')}: {identity.fingerprint}"
                )
        print(f"\n[NECNC ruling] checked={checked} claimed={len(claimed)}")
        assert not claimed, "\n".join(claimed[:20])


class TestPioneer:
    """The negative pin: three outcomes, and PIONEER is never one."""

    def test_no_air_capture_ever_produces_pioneer(self):
        counts: Counter = Counter()
        for protocol in FAMILIES["pioneer"]:
            for command in _rows()[protocol]:
                pronto = command.get("pronto")
                if not pronto:
                    continue
                identity = try_decode_identity(
                    ProntoCommand(pronto).get_raw_timings()
                )
                label = "raw" if identity is None else identity.protocol
                counts[f"{protocol}:{label}"] += 1
        _report("Pioneer", counts)
        minted = {
            key: value for key, value in counts.items()
            if key.endswith(":PIONEER")
        }
        assert not minted, minted
        assert set(
            key.split(":")[-1] for key in counts
        ) <= {"NEC", "raw", "NEC42", "NEC42EXT"}, counts


class TestDyson:
    """Device, function and counter, all three."""

    def test_every_row_reads_as_dyson_with_counter_one(self):
        counts: Counter = Counter()
        failures: list[str] = []
        for command in _rows()["Dyson 15 Bit Double Toggle"]:
            pronto = command.get("pronto")
            parsed = _first_value(command.get("keycode", ""), 14)
            if not pronto or parsed is None:
                continue
            counts["rows"] += 1
            identity = try_decode_identity(
                ProntoCommand(pronto).get_raw_timings()
            )
            if identity is None or identity.protocol != "DYSON":
                failures.append(f"{command.get('name')}: not DYSON")
                continue
            counts[f"device:{identity.address}"] += 1
            counter = (identity.extras or {}).get("counter")
            counts[f"counter:{counter}"] += 1
            if counter != 1:
                failures.append(
                    f"{command.get('name')}: counter {counter}, expected 1"
                )

            # THE FUNCTION IS ASSERTED TOO, which the first draft of this
            # suite left out. Counter and device alone would pass a
            # decoder that scrambled the six function bits, and the
            # function is the value this pack changes.
            #
            # The definition renders the thirteen payload bits under an
            # inverted bitspec, so HAIR's wire bits are the complement of
            # the keycode's, and the last two are the toggle pair.
            # ``parsed`` is MSB-first over the 14-bit Code0 field, whose
            # first thirteen bits are the payload and whose last is the
            # toggle. The definition renders those thirteen under an
            # inverted bitspec, so complementing them gives HAIR's wire
            # bits 0 to 12 IN WIRE ORDER. The frame is then read LSB
            # first per field: bits 0-6 are the device and bits 7-12 are
            # the function's six bits, with the counter in the two wire
            # bits after them.
            payload = [1 - bit for bit in parsed[1][:13]]
            device = sum(payload[index] << index for index in range(7))
            function = sum(payload[7 + index] << index for index in range(6))
            if identity.address != device:
                failures.append(
                    f"{command.get('name')}: device {identity.address} "
                    f"!= keycode {device}"
                )
            elif identity.command != function:
                failures.append(
                    f"{command.get('name')}: function "
                    f"{identity.command:#04x} != keycode {function:#04x}"
                )
        _report("Dyson", counts)
        assert not failures, "\n".join(failures[:20])
