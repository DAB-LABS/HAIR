"""Identifying a two-frame family from the one frame that arrived.

Issue 9 of the detangler round, proven live on the Daikin 1103 file
2026-08-29 and reproduced here from the fixture's own bytes. A
MITSUBISHI144 press transmits 144 bits twice with a gap between them,
the receiver hands back what it heard between gaps, and so one press
arrives as two capture events of one frame each. Identification wanted
both frames, so every half read as unidentified and the surface called
a perfectly clean press garbled. A whole column of that file cannot be
recaptured from the remote until this changes.

The fix is reader-side and nothing else. Capture stitching would add
latency to every capture on the shared monitor path to serve two
families out of twelve; the maps already carry the fact that makes
stitching unnecessary, which is that their frames are declared
IDENTICAL. A map that says so has said the payload survives on its
own.

What replaces the missing evidence is the point of the tests below. The
doubled shape was evidence, and a half press spends it, so the frame
that did arrive has to hold together on the map's own terms instead:
identity bytes, and every ratified integrity rule that can still be
judged. A corrupted half stays unidentified, which is the difference
between reading less and believing more.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair.tangles import pre_read, read_lattice
from custom_components.hair.wig_adapters import _broadlink_b64_to_pronto
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, Wig

PACKS = Path(__file__).parent / "fixtures" / "field-packs"


def _map(protocol_id: str) -> fr.FieldMap:
    for candidate in fr.load_maps():
        if candidate.protocol_id == protocol_id:
            return candidate
    raise AssertionError(f"{protocol_id} is not vendored")


def _first_code(pack: str) -> str:
    """The first code in a synthesized field pack, as Pronto."""
    raw = json.loads((PACKS / pack).read_text())

    def walk(node: object) -> str | None:
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        return None

    encoded = walk(raw["commands"])
    assert encoded, f"{pack} carries no codes"
    pronto = _broadlink_b64_to_pronto(encoded)
    assert pronto, f"{pack} did not convert"
    return pronto


def _words(pronto: str) -> list[int]:
    return [int(word, 16) for word in pronto.split()]


def _rebuild(head: list[int], body: list[int]) -> str:
    words = list(head) + list(body)
    words[2] = len(body) // 2
    words[3] = 0
    return " ".join(f"{word:04X}" for word in words)


def _halves(pronto: str, field_map: fr.FieldMap) -> tuple[str, str]:
    """One press, cut at the gap the receiver itself cuts at."""
    words = _words(pronto)
    head, body = words[:4], words[4:]
    unit = words[1] * 0.241246
    boundary = None
    for index in range(0, len(body) - 1, 2):
        if body[index + 1] * unit >= field_map.timing.gap_min:
            boundary = index + 2
            break
    assert boundary is not None, "the fixture code carries no frame gap"
    return _rebuild(head, body[:boundary]), _rebuild(head, body[boundary:])


def _flip(pronto: str, field_map: fr.FieldMap, bit: int) -> str:
    """One data bit of frame 0, rewritten to the other symbol.

    Through the map's own positions, so the flip lands on the pulse
    that actually carries the bit rather than on a word counted by
    hand.
    """
    timings = fr.pronto_microseconds(pronto)
    assert timings is not None
    _frames, places, failed = fr.read_frames_positioned(
        field_map.timing, timings
    )
    assert not failed
    pair = places[0][bit]
    words = _words(pronto)
    body = words[4:]
    unit = words[1] * 0.241246
    space = body[pair * 2 + 1] * unit
    other = (
        field_map.timing.one.nominal
        if field_map.timing.zero.holds(space)
        else field_map.timing.zero.nominal
    )
    body[pair * 2 + 1] = max(1, round(other / unit))
    return _rebuild(words[:4], body)


def _pack_matrix(pack: str) -> tuple[Wig, ClimateMatrix]:
    """A one-family lattice from a pack, enough to read against."""
    raw = json.loads((PACKS / pack).read_text())
    cells: list[ClimateCell] = []
    for mode, by_fan in raw["commands"].items():
        if not isinstance(by_fan, dict):
            continue
        for fan, by_swing in by_fan.items():
            if not isinstance(by_swing, dict):
                continue
            for swing, by_temp in by_swing.items():
                if not isinstance(by_temp, dict):
                    continue
                for temp, code in by_temp.items():
                    if not isinstance(code, str):
                        continue
                    cells.append(ClimateCell(
                        mode=mode, fan=fan, swing=swing, temp=float(temp),
                        pronto=_broadlink_b64_to_pronto(code) or "",
                    ))
    temps = [cell.temp for cell in cells if cell.temp is not None]
    matrix = ClimateMatrix(
        min_temp=min(temps), max_temp=max(temps),
        off=cells[0].pronto, cells=cells,
        modes=sorted({cell.mode for cell in cells if cell.mode}),
        fan_modes=sorted({cell.fan for cell in cells if cell.fan}),
        swing_modes=sorted({cell.swing for cell in cells if cell.swing}),
    )
    return Wig(name="Pack", signals=[], climate=matrix), matrix


@pytest.fixture
def mitsubishi() -> fr.FieldMap:
    return _map("MITSUBISHI144")


@pytest.fixture
def full(mitsubishi: fr.FieldMap) -> str:
    return _first_code("MITSUBISHI144.json")


class TestTheHalfPressIdentifies:
    def test_the_full_code_still_identifies(self, full, mitsubishi):
        """First, because the relaxation must cost nothing. A code that
        arrives whole is read by the layout branch exactly as before."""
        reading = fr.read_code(full, [mitsubishi])
        assert reading.protocol_id == "MITSUBISHI144"
        assert len(reading.frames) == 2

    def test_each_half_identifies_on_its_own(self, full, mitsubishi):
        """The defect, cured. Before this branch both halves came back
        unidentified and the fix flow said garbled."""
        for half in _halves(full, mitsubishi):
            reading = fr.read_code(half, [mitsubishi])
            assert reading.protocol_id == "MITSUBISHI144"
            assert reading.declined is None
            assert len(reading.frames) == 1

    def test_a_half_reads_the_same_fields_as_the_whole(
            self, full, mitsubishi):
        """Identification is worth nothing on its own. The half has to
        say the same thing the press said, field for field."""
        whole = fr.read_code(full, [mitsubishi])
        half = fr.read_code(_halves(full, mitsubishi)[0], [mitsubishi])
        read = {
            spec.name: (
                fr.read_field(whole, spec), fr.read_field(half, spec),
            )
            for spec in mitsubishi.fields if spec.ratified
        }
        assert read, "the map states no ratified fields"
        for name, (from_whole, from_half) in read.items():
            assert from_whole == from_half, name

    def test_the_second_half_reads_it_too(self, full, mitsubishi):
        """Both capture events are the same press. Whichever one the
        surface happens to hand over has to answer the same way, or the
        repair depends on which half the receiver reported first."""
        first, second = _halves(full, mitsubishi)
        spec = mitsubishi.field_named("temperature")
        assert spec is not None
        from_first = fr.read_field(fr.read_code(first, [mitsubishi]), spec)
        from_second = fr.read_field(fr.read_code(second, [mitsubishi]), spec)
        assert from_first is not None
        assert from_first == from_second


class TestIntegrityStillBinds:
    def test_a_corrupted_half_is_refused(self, full, mitsubishi):
        """The compensating control, and the reason this is safe.

        A half press has no repeat to check itself against, so the
        map's checksum stands in for the shape that did not arrive. Flip
        one data bit and the frame no longer adds up, so it is not this
        family's code and identification says so.
        """
        half = _halves(full, mitsubishi)[0]
        bent = _flip(half, mitsubishi, 56)
        assert fr.read_code(half, [mitsubishi]).protocol_id == "MITSUBISHI144"
        reading = fr.read_code(bent, [mitsubishi])
        assert reading.protocol_id is None
        assert reading.declined is not None

    def test_the_identity_bytes_still_gate_it(self, full, mitsubishi):
        """A frame of the right width that is not this family stays
        unidentified, same as it ever was."""
        half = _halves(full, mitsubishi)[0]
        bent = _flip(half, mitsubishi, 2)      # inside identity byte 0
        assert fr.read_code(bent, [mitsubishi]).protocol_id is None

    def test_the_repeat_rule_reads_as_unevaluated_not_passed(
            self, full, mitsubishi):
        """A rule that cannot be judged is never a pass, and a half
        press is exactly the case that tempts a shortcut."""
        reading = fr.read_code(_halves(full, mitsubishi)[0], [mitsubishi])
        assert reading.protocol_id == "MITSUBISHI144"
        rule = next(
            r for r in mitsubishi.integrity
            if r.type == fr.RULE_FRAME_REPEAT
        )
        assert fr.check_integrity(reading, rule) is None

    def test_the_whole_code_is_not_held_to_the_new_standard(
            self, full, mitsubishi):
        """Deliberate asymmetry, stated so nobody 'fixes' it.

        A code that matches the declared layout identifies on its shape,
        as it always has, and a checksum failure on it surfaces as a
        comb finding about a code we know the family of. Only the short
        branch, which has spent the shape, has to buy identification
        with integrity.
        """
        bent = _flip(full, mitsubishi, 56)
        assert fr.read_code(bent, [mitsubishi]).protocol_id == "MITSUBISHI144"


class TestOnlyWhereTheMapSaysSo:
    def test_a_single_frame_family_is_untouched(self):
        """ZHLT01 declares one frame. There is no short capture of a
        one-frame code, and nothing about it changes."""
        code = _first_code("ZHLT01.json")
        zhlt = _map("ZHLT01")
        assert zhlt.repeats_identically is False
        reading = fr.read_code(code, [zhlt])
        assert reading.protocol_id == "ZHLT01"
        assert len(reading.frames) == 1

    def test_two_frames_are_not_enough_to_qualify(self):
        """TCL112 sends [112, 112] and carries its payload in the
        SECOND frame, with no repeat rule anywhere. Its two frames are
        two different things, so one of them is not the code and this
        branch must not touch it."""
        tcl = _map("TCL112")
        assert tcl.repeats_identically is False
        code = _first_code("TCL112.json")
        for half in _halves(code, tcl):
            assert fr.read_code(half, [tcl]).protocol_id is None

    def test_the_declaring_maps_are_the_two_that_declare_it(self):
        """The licence comes from the map and from nowhere else, so
        which maps hold it is a fact worth pinning: adding a third is a
        map change somebody reviewed."""
        holders = {
            candidate.protocol_id for candidate in fr.load_maps()
            if candidate.repeats_identically
        }
        assert holders == {"MITSUBISHI144", "MIDEA_COOLIX"}

    def test_a_whole_code_outranks_any_half_reading(self, full, mitsubishi):
        """Two passes, in order. The full library is offered the code
        first and the layout branch answers, so no short reading can
        take a code away from the family that transmits it whole."""
        reading = fr.read_code(full)
        assert reading.protocol_id == "MITSUBISHI144"
        assert len(reading.frames) == 2


class TestTheSurfaceStopsSayingGarbled:
    """What the fix is FOR, one layer up.

    The listen ladder judges a capture through ``pre_read``. Before
    this, a half press reached it unidentified, so the row could only
    offer USE IT ANYWAY on a code that was never in doubt.
    """

    def test_a_half_press_reads_against_its_own_cell(self, mitsubishi):
        wig, matrix = _pack_matrix("MITSUBISHI144.json")
        lattice = read_lattice(matrix, wig)
        assert lattice.readable
        cell = matrix.cells[0]
        coordinates = {
            "mode": cell.mode, "fan": cell.fan,
            "swing": cell.swing, "temp": cell.temp,
        }
        half = _halves(cell.pronto, mitsubishi)[0]
        verdict = pre_read(lattice, half, coordinates)
        assert verdict.readable
        assert verdict.protocol == "MITSUBISHI144"
        assert verdict.matches is True
        assert verdict.mismatches == []

    def test_and_a_half_press_of_the_wrong_cell_still_disagrees(
            self, mitsubishi):
        """Readable is not agreeable. The ladder still has something to
        say when the press is not the one the row asked for."""
        wig, matrix = _pack_matrix("MITSUBISHI144.json")
        lattice = read_lattice(matrix, wig)
        column = sorted(
            (c for c in matrix.cells
             if (c.mode, c.fan, c.swing)
             == (matrix.cells[0].mode, matrix.cells[0].fan,
                 matrix.cells[0].swing)),
            key=lambda c: c.temp or 0,
        )
        target, other = column[0], column[-1]
        assert target.temp != other.temp
        verdict = pre_read(
            lattice, _halves(other.pronto, mitsubishi)[0],
            {"mode": target.mode, "fan": target.fan,
             "swing": target.swing, "temp": target.temp},
        )
        assert verdict.readable
        assert verdict.matches is False
        assert "temperature" in verdict.mismatches
