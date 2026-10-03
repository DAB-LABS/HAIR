"""The repair path on a field the map places by its own coordinate.

A field map may say which label axis a field answers (schema v0.3), and
two maps need it: DAIKIN216 answers swing with two vanes in two nibbles,
and DAIKIN152 answers the fan with a speed nibble and three flags. The
comb has filed findings on those fields since they were ratified. The
repair path read them through the comb's four-name table, found no axis,
and showed every such row as "field not ratified" for a field the map
vouches for.

These pins hold the corrected reading in place, and most of them hold
the places where a reading through the map would go wrong:

- A donor is another CELL, so it differs on a whole axis, not on one
  field. Every field answering the axis is held to what the target's
  label implies, provisional ones included, so a donor that sends the
  right vertical vane and the wrong horizontal one is never offered.
- The anchor is the cell's four labels, never the axes a map has fields
  for. A map with no swing field still sends a swing.
- Power varies no axis and keeps the donor it had.
- What the map says applies decides what is compared, at the search,
  at the read-back and at the sibling check -- and the donor must be
  judged by the same fields as its target.
- A field outside the name table is compared but not named, and its
  card stays a fresh capture: the witness road and the card's own
  mirror of the table cannot carry it yet.

Every lattice is a shipped field pack or the #183 shape built by the
test-side encoders the DAIKIN152 pins already use, with one defect
placed by hand.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from custom_components.hair import field_readers
from custom_components.hair.models import IRDevice
from custom_components.hair.tangles import (
    ABSTAIN_NO_READING,
    MECHANIC_RECAPTURE,
    MECHANIC_WITNESS,
    ORIGIN_SYNTHESIZED,
    ORIGIN_TRIM,
    SYNTH_NO_WITNESS,
    TRIM_READS_WRONG,
    find_donor,
    find_trim,
    list_tangles,
    plan_batch,
    pre_read,
    read_lattice,
    rewrite_field,
    synthesize,
)
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    CHECK_STRAY_BURST,
    FIELD_COORDINATE,
    POWER_FIELD,
    comb_wig,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    cell_key,
)

from .test_a_leader_is_not_off import _handset, _stored_state
from .test_daikin152_joins import _file_form
from .test_daikin152_traits import _settings as _d152_settings
from .test_field_sweep import _pack_wig

MAPS = {m.protocol_id: m for m in field_readers.library()}


# ---------------------------------------------------------------------------
# Lattices
# ---------------------------------------------------------------------------


def _pack(name: str) -> ClimateMatrix:
    return _pack_wig(name).climate


def _codes(matrix: ClimateMatrix) -> dict[str, str]:
    return {cell_key(cell): cell.pronto for cell in matrix.cells}


def _with(matrix: ClimateMatrix, codes: dict[str, str]) -> ClimateMatrix:
    """The same lattice with some cells carrying other bytes."""
    return replace(matrix, cells=[
        replace(cell, pronto=codes.get(cell_key(cell), cell.pronto))
        for cell in matrix.cells
    ])


def _swapped(matrix: ClimateMatrix, first: str, second: str) -> ClimateMatrix:
    codes = _codes(matrix)
    return _with(matrix, {first: codes[second], second: codes[first]})


def _copied(matrix: ClimateMatrix, target: str, source: str) -> ClimateMatrix:
    return _with(matrix, {target: _codes(matrix)[source]})


def _coords(key: str) -> dict:
    mode, fan, *rest = key.split("/")
    swing = rest[0] if len(rest) == 2 else None
    return {"mode": mode, "fan": fan, "swing": swing,
            "temp": float(rest[-1])}


def _listing(matrix: ClimateMatrix):
    return list_tangles(IRDevice(name="AC", climate_matrix=True), matrix)


def _row(listing, key: str):
    return next(row for row in listing.rows if row.target.key == key)


def _payloads(matrix: ClimateMatrix):
    """The lattice and the comb's own findings per key, as the listing
    hands them to the donor search."""
    wig = Wig(name="AC", signals=[], climate=matrix)
    grouped: dict[str, list[dict]] = {}
    for finding in comb_wig(wig).findings:
        for key in finding.keys:
            grouped.setdefault(key, []).append(finding.to_dict())
    return read_lattice(matrix, wig), grouped


def _fields(payload: list[dict]) -> list[str]:
    return [str(f["params"]["field"]).rsplit(".", 1)[-1]
            for f in payload if f["check"] == CHECK_FIELD_MISMATCH]


#: The #183 remote's fan column: four labels on one speed nibble, told
#: apart by the flags beside it.
D183_FANS = {
    "high": (0x7, {}),
    "powerful": (0x7, {"powerful": True}),
    "economy": (0x7, {"economy": True}),
    "sleep": (0x7, {"sleep": True}),
}


def _d183(override: dict | None = None, fans: dict = D183_FANS,
          mode: str = "cool") -> ClimateMatrix:
    """A DAIKIN152 lattice of the #183 wig's shape, in its file's form.

    ``override`` places a defect: a key mapped to the (nibble, flags)
    that cell actually sends instead of its own.
    """
    cells = []
    for fan, (nibble, flags) in fans.items():
        for swing in ("off", "vertical"):
            for temp in (23, 24, 25):
                key = f"{mode}/{fan}/{swing}/{temp}"
                sends, sent_flags = (override or {}).get(key, (nibble, flags))
                cells.append(ClimateCell(
                    mode=mode, fan=fan, swing=swing, temp=float(temp),
                    pronto=_stored_state(_file_form(_d152_settings(
                        mode, sends, temp, swing=swing, **sent_flags))),
                ))
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0, modes=[mode],
        fan_modes=sorted(fans), swing_modes=["off", "vertical"],
        off=_handset(_d152_settings("cool", 0x7, 24, power=0)),
        cells=cells,
    )


def _stray(pronto: str) -> str:
    """The same code with one stray burst caught after the last frame."""
    words = pronto.split()
    body = words[4:]
    if int(body[-1], 16) < 0x0800:
        # Close the last frame with a real gap, so the burst stands
        # alone the way a late edge after the release does.
        body[-1] = "0800"
    once = int(words[2], 16) + 1
    return " ".join(
        [words[0], words[1], f"{once:04X}", words[3], *body, "0010", "09C4"])


# ---------------------------------------------------------------------------
# A swap is repaired from the cell that carries the right bytes
# ---------------------------------------------------------------------------


class TestASwapFindsItsDonor:
    """Two cells carrying each other's codes: each one's right bytes
    sit in the other. Both rows used to say "field not ratified"."""

    def test_two_daikin216_swing_cells_repair_each_other(self):
        matrix = _swapped(_pack("DAIKIN216.json"),
                          "cool/low/vertical/22", "cool/low/off/22")
        listing = _listing(matrix)
        lattice = read_lattice(matrix)
        for target, donor in (("cool/low/vertical/22", "cool/low/off/22"),
                              ("cool/low/off/22", "cool/low/vertical/22")):
            row = _row(listing, target)
            assert row.has_donor, row.donor_abstain
            assert row.donor["key"] == donor
            verdict = pre_read(lattice, row.donor["pronto"], _coords(target))
            assert verdict.matches is True
            assert {"swing_vertical", "swing_horizontal"} <= set(
                verdict.raw_expected)

    def test_the_donor_says_what_it_reads_as(self):
        matrix = _swapped(_pack("DAIKIN216.json"),
                          "cool/low/vertical/22", "cool/low/off/22")
        row = _row(_listing(matrix), "cool/low/vertical/22")
        assert row.donor["reasoning"] == {
            "fields": ["swing_vertical"],
            "labelled": {"swing_vertical": "off"},
            "reads_as": {"swing_vertical": "vertical"},
        }

    def test_powerful_and_high_swapped_on_the_183_shape(self):
        matrix = _d183({
            "cool/powerful/off/24": (0x7, {}),
            "cool/high/off/24": (0x7, {"powerful": True}),
        })
        listing = _listing(matrix)
        lattice = read_lattice(matrix)
        for target, donor in (("cool/high/off/24", "cool/powerful/off/24"),
                              ("cool/powerful/off/24", "cool/high/off/24")):
            row = _row(listing, target)
            assert row.donor and row.donor["key"] == donor
            verdict = pre_read(lattice, row.donor["pronto"], _coords(target))
            assert verdict.matches is True
            assert "powerful" in verdict.raw_expected


# ---------------------------------------------------------------------------
# A copy has nothing to copy from
# ---------------------------------------------------------------------------


class TestACopyHasNoDonor:
    """The real defect is mostly this: a cell that is a copy of its
    neighbour. Then no cell anywhere sends what it claims, and the
    honest answer is that none does."""

    def test_a_vertical_cell_copied_from_swing_off(self):
        matrix = _copied(_pack("DAIKIN216.json"),
                         "cool/low/vertical/22", "cool/low/off/22")
        row = _row(_listing(matrix), "cool/low/vertical/22")
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING

    def test_the_cell_that_reads_the_right_vane_is_not_offered(self):
        """Why the search holds the whole axis. The ``both`` cell sends
        the vertical vane this target needs and a horizontal vane it
        does not; a search on the named field alone would offer it."""
        matrix = _copied(_pack("DAIKIN216.json"),
                         "cool/low/vertical/22", "cool/low/off/22")
        lattice = read_lattice(matrix)
        vertical = lattice.spec_for("swing_vertical")
        horizontal = lattice.spec_for("swing_horizontal")
        both = "cool/low/both/22"
        assert lattice.reads(both, vertical) == field_readers.expected_value(
            vertical, "vertical")
        assert lattice.reads(both, horizontal) != (
            field_readers.expected_value(horizontal, "vertical"))
        _lattice, payloads = _payloads(matrix)
        donor, reason = find_donor(
            lattice, "cool/low/vertical/22", payloads["cool/low/vertical/22"])
        assert donor is None
        assert reason == ABSTAIN_NO_READING

    def test_a_powerful_cell_copied_from_high(self):
        """1114's shape: thirteen fan_only/powerful cells that are copies
        of fan_only/high."""
        matrix = _d183({"cool/powerful/off/24": (0x7, {})})
        row = _row(_listing(matrix), "cool/powerful/off/24")
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING


# ---------------------------------------------------------------------------
# A dry target, judged by what applies in dry
# ---------------------------------------------------------------------------


DRY_FANS = {
    "auto": (0xA, {}),
    "low": (0xA, {}),
    "powerful": (0xA, {"powerful": True}),
}


class TestADryTarget:
    """DAIKIN152 forces the fan in dry: every dry code sends 0xA
    whatever its label says. A donor for a dry/low cell therefore never
    reads 0x3, and a read-back that compared the fan refused every dry
    donor for a setting the unit ignores."""

    def _matrix(self) -> ClimateMatrix:
        return _d183({"dry/low/off/24": (0xA, {"powerful": True})},
                     fans=DRY_FANS, mode="dry")

    def test_a_dry_cell_carrying_powerful_gets_a_dry_donor(self):
        matrix = self._matrix()
        row = _row(_listing(matrix), "dry/low/off/24")
        assert _fields(row.findings) == ["powerful"]
        assert row.donor and row.donor["key"] == "dry/auto/off/24"

    def test_its_donor_reads_true_without_the_forced_fan(self):
        matrix = self._matrix()
        lattice = read_lattice(matrix)
        donor = _codes(matrix)["dry/auto/off/24"]
        verdict = pre_read(lattice, donor, _coords("dry/low/off/24"))
        # The fan is read -- the bytes do say 0xA -- and not compared,
        # because the map says it carries nothing in dry.
        assert verdict.raw_read["fan_speed"] == 0xA
        assert "fan_speed" not in verdict.raw_expected
        assert verdict.matches is True


# ---------------------------------------------------------------------------
# Provisional fields on the varying axis
# ---------------------------------------------------------------------------


class TestAProvisionalFlagIsStillASetting:
    """Economy and sleep are provisional on DAIKIN152: read, never
    judged by the comb. They are still settings the unit acts on, so a
    donor for a fan label is held to the value the label implies for
    them as well."""

    def test_a_high_cell_is_not_offered_the_economy_code(self):
        """The high cell carries the powerful flag. The economy cell
        beside it sends no powerful flag either, and would pass a search
        that never required economy."""
        matrix = _d183({"cool/high/off/24": (0x7, {"powerful": True})})
        row = _row(_listing(matrix), "cool/high/off/24")
        assert _fields(row.findings) == ["powerful"]
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING

    def test_an_economy_copy_of_powerful_is_not_offered_the_high_code(self):
        """The economy cell is a copy of the powerful cell, so its OWN
        economy flag is the wrong 0. A search that held it to its own
        value would offer the high code for an economy label."""
        matrix = _d183({"cool/economy/off/24": (0x7, {"powerful": True})})
        row = _row(_listing(matrix), "cool/economy/off/24")
        assert _fields(row.findings) == ["powerful"]
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING


# ---------------------------------------------------------------------------
# An axis the map does not model is still an axis
# ---------------------------------------------------------------------------


def _panasonic_with_two_swings() -> ClimateMatrix:
    """PANASONIC216 has no swing field, and real remotes of it send one.

    The pack has no swing level, so one is made: the cool/low column
    under swing ``auto`` as the pack has it, and again under ``top``
    with the vane bits (frame 1, byte 8, low nibble, which no field of
    the map reads) moved and the checksum recomputed. That is the shape
    of corpus file 1030.
    """
    pack = _pack("PANASONIC216.json")
    field_map = MAPS["PANASONIC216"]
    vane = replace(field_map.field_named("fan_speed"), name="vane",
                   bits="low_nibble")
    cells = []
    for cell in pack.cells:
        if (cell.mode, cell.fan) != ("cool", "low"):
            continue
        reading = field_readers.read_code(cell.pronto)
        current = reading.frames[vane.frame][vane.byte] & 0x0F
        top = rewrite_field(field_map, cell.pronto, vane, current ^ 0x06)
        assert top is not None
        cells.append(replace(cell, swing="auto"))
        cells.append(replace(cell, swing="top", pronto=top))
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0, modes=["cool"],
        fan_modes=["low"], swing_modes=["auto", "top"],
        off=pack.off, cells=cells,
    )


class TestAnAxisTheMapDoesNotModel:
    def test_a_panasonic_cell_takes_no_donor_at_another_swing(self):
        """The cell at the other swing reads the right temperature and
        sends the wrong vane. An anchor built from the map's own fields
        would have no swing in it, and would offer it."""
        matrix = _panasonic_with_two_swings()
        matrix = _copied(matrix, "cool/low/top/18", "cool/low/top/20")
        row = _row(_listing(matrix), "cool/low/top/18")
        assert "temperature" in _fields(row.findings)
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING

    def test_a_panasonic_swap_is_repaired_within_its_swing(self):
        matrix = _swapped(_panasonic_with_two_swings(),
                          "cool/low/top/22", "cool/low/top/24")
        listing = _listing(matrix)
        assert _row(listing, "cool/low/top/22").donor["key"] == (
            "cool/low/top/24")
        for row in listing.rows:
            if row.has_donor and row.donor.get("coordinates"):
                assert row.donor["coordinates"]["swing"] == (
                    row.target.coordinates["swing"])

    def test_a_fujitsu_mode_finding_takes_no_donor_at_another_temp(self):
        """FUJITSU128 has no temperature field. ``cool/auto/20`` reads
        cool, and sends 20 for an 18 label."""
        matrix = _copied(_pack("FUJITSU128.json"),
                         "cool/auto/18", "heat/auto/18")
        row = _row(_listing(matrix), "cool/auto/18")
        assert "mode" in _fields(row.findings)
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING

    def test_a_fujitsu_swap_is_repaired_at_its_own_temp(self):
        matrix = _swapped(_pack("FUJITSU128.json"),
                          "cool/auto/18", "heat/auto/18")
        listing = _listing(matrix)
        assert _row(listing, "cool/auto/18").donor["key"] == "heat/auto/18"
        for row in listing.rows:
            if row.has_donor and row.donor.get("coordinates"):
                assert row.donor["coordinates"]["temp"] == (
                    row.target.coordinates["temp"])


# ---------------------------------------------------------------------------
# Power varies no axis
# ---------------------------------------------------------------------------


class TestPowerInAFinding:
    def test_a_cell_wrong_on_power_mode_and_temp_keeps_its_donor(self):
        """Corpus 2661's shape. The target sends heat at 24 with power
        off; the cell beside it carries the target's own bytes. Power
        has no axis by design and is required at "on", so it must not
        turn the row into "not a field finding"."""
        pack = _pack("TCL112.json")
        field_map = MAPS["TCL112"]
        codes = _codes(pack)
        target, donor = "cool/low/static/20", "heat/low/static/24"
        off = rewrite_field(field_map, codes[donor],
                            field_map.field_named(POWER_FIELD), 0)
        assert off is not None
        matrix = _with(pack, {target: off, donor: codes[target]})
        lattice, payloads = _payloads(matrix)
        assert set(_fields(payloads[target])) == {
            "temperature", "mode", POWER_FIELD}
        found, reason = find_donor(lattice, target, payloads[target])
        assert reason is None
        assert found["key"] == donor
        verdict = pre_read(lattice, found["pronto"], _coords(target))
        assert verdict.matches is True


# ---------------------------------------------------------------------------
# The trim and the paste on DAIKIN216
# ---------------------------------------------------------------------------


class TestTheTrimAndThePaste:
    """A vertical cell carrying its swing-off neighbour's code plus a
    stray trailing burst. The trim used to be offered: the read-back
    did not compare the vanes, so a code that sends swing off read
    True for a vertical label. It is withdrawn now -- a code that
    sends a different setting is never offered -- and the row asks for
    a fresh capture instead."""

    TARGET = "cool/low/vertical/22"

    def _matrix(self) -> ClimateMatrix:
        pack = _pack("DAIKIN216.json")
        return _with(pack, {
            self.TARGET: _stray(_codes(pack)["cool/low/off/22"])})

    def test_the_trim_is_withdrawn(self):
        matrix = self._matrix()
        lattice, payloads = _payloads(matrix)
        payload = payloads[self.TARGET]
        assert {f["check"] for f in payload} == {
            CHECK_FIELD_MISMATCH, CHECK_STRAY_BURST}
        trimmed, reason = find_trim(
            lattice.cells[self.TARGET].pronto, payload, lattice,
            self.TARGET, _coords(self.TARGET))
        assert trimmed is None
        assert reason == TRIM_READS_WRONG

    def test_the_row_asks_for_a_capture(self):
        row = _row(_listing(self._matrix()), self.TARGET)
        assert not row.has_donor
        assert row.donor_abstain == ABSTAIN_NO_READING

    @pytest.mark.parametrize("pasted,matches,mismatches", [
        ("both", False, ["swing_horizontal"]),
        ("horizontal", False, ["swing_vertical", "swing_horizontal"]),
        ("vertical", True, []),
    ])
    def test_a_paste_is_judged_on_both_vanes(self, pasted, matches,
                                             mismatches):
        matrix = self._matrix()
        lattice = read_lattice(matrix)
        code = _codes(_pack("DAIKIN216.json"))[f"cool/low/{pasted}/22"]
        verdict = pre_read(lattice, code, _coords(self.TARGET))
        assert verdict.matches is matches
        assert verdict.mismatches == mismatches


# ---------------------------------------------------------------------------
# Trims the map now allows
# ---------------------------------------------------------------------------


class TestATrimInAModeThatIgnoresTheTemperature:
    """MITSUBISHI144 sends no temperature in dry: every dry cell of the
    pack carries the same nibble whatever its label. A dry cell with a
    stray burst used to have its trim refused, because the read-back
    compared that nibble to the label. The map says the temperature
    does not apply there, and 63 such trims across three corpus files
    are offered now."""

    TARGET = "dry/auto/auto/24"

    def _matrix(self) -> ClimateMatrix:
        pack = _pack("MITSUBISHI144.json")
        return _with(pack, {self.TARGET: _stray(_codes(pack)[self.TARGET])})

    def test_the_trim_is_offered(self):
        row = _row(_listing(self._matrix()), self.TARGET)
        assert [f["check"] for f in row.findings] == [CHECK_STRAY_BURST]
        assert row.has_donor
        assert row.donor["reasoning"]["origin"] == ORIGIN_TRIM
        assert row.donor["reasoning"]["pairs_removed"] == 1
        clean = _codes(_pack("MITSUBISHI144.json"))[self.TARGET]
        assert field_readers.read_code(row.donor["pronto"]).frames == (
            field_readers.read_code(clean).frames)

    def test_the_read_back_names_the_fields_it_compared(self):
        matrix = self._matrix()
        lattice = read_lattice(matrix)
        temperature = lattice.spec_for("temperature")
        clean = _codes(_pack("MITSUBISHI144.json"))[self.TARGET]
        verdict = pre_read(lattice, clean, _coords(self.TARGET))
        assert verdict.raw_read["temperature"] != (
            field_readers.expected_value(temperature, 24.0))
        assert set(verdict.claims) == {"mode", "fan_speed", POWER_FIELD}
        assert verdict.matches is True


# ---------------------------------------------------------------------------
# The witness road
# ---------------------------------------------------------------------------


def _defects(name: str):
    matrix = _pack(f"{name}.defects.json")
    return matrix, _listing(matrix), read_lattice(matrix)


class TestTheWitnessRoad:
    """The road builds every member nobody aimed at from its own healthy
    sibling. A dry sibling is not healthy for a cool target: its frozen
    temperature byte would ride into the built code."""

    @pytest.mark.parametrize("pack,target,sibling,digest", [
        ("CHIGO96B", "cool/auto/24", "heat/auto/24", "67b32eaab58e3c9f"),
        ("MITSUBISHI144", "cool/auto/auto/24", "heat/auto/auto/24",
         "07fb65db7b01611b"),
    ])
    def test_the_unaimed_mode_witness_builds_the_same_code(
            self, pack, target, sibling, digest):
        """Pinned by digest: the code the road built before the map's
        axes reached the sibling check, byte for byte."""
        _matrix, listing, lattice = _defects(pack)
        rows = {row.id: row for row in listing.rows}
        card = next(c for c in listing.clusters
                    if c.field == "mode"
                    and rows[c.members[0]].target.key == target)
        assert card.mechanic == MECHANIC_WITNESS
        witness = _codes(_pack(f"{pack}.json"))[target]
        plan = plan_batch(listing, lattice, card.id, witness=witness)
        assert plan.refused is None
        built = plan.candidates[f"cell:{target}"]
        assert built["origin"] == ORIGIN_SYNTHESIZED
        assert built["sibling"] == sibling
        assert built["verdict"]["matches"] is True
        assert built["digest"] == digest

    def _map_only_cards(self):
        d216 = _copied(_copied(_pack("DAIKIN216.json"),
                               "cool/low/vertical/22", "cool/low/off/22"),
                       "cool/low/vertical/25", "cool/low/off/25")
        d152 = _d183({"cool/powerful/off/24": (0x7, {}),
                      "cool/powerful/off/25": (0x7, {})})
        clean216 = _codes(_pack("DAIKIN216.json"))["cool/low/vertical/22"]
        clean152 = _codes(_d183())["cool/powerful/off/24"]
        return [
            (d216, "swing_vertical", "cool/low/vertical/22", clean216),
            (d152, "powerful", "cool/powerful/off/24", clean152),
        ]

    def test_a_map_only_field_is_refused_as_it_was(self):
        """The road rewrites one field; on these axes other fields ride
        along. It refuses them exactly as it always has, aimed or not,
        and never raises."""
        for matrix, field_name, aimed, witness in self._map_only_cards():
            listing = _listing(matrix)
            lattice = read_lattice(matrix)
            card = next(c for c in listing.clusters if c.field == field_name)
            rows = [r for r in listing.rows if r.id in card.members]
            assert len(rows) == 2
            for target in (f"cell:{aimed}", None):
                result = synthesize(lattice, rows, witness, field_name,
                                    witness_target=target)
                assert result.refused == SYNTH_NO_WITNESS
                assert result.candidates == {}
                plan = plan_batch(listing, lattice, card.id, witness=witness,
                                  witness_target=target)
                assert plan.refused == SYNTH_NO_WITNESS

    def test_no_witness_card_on_a_map_only_field(self):
        for matrix, field_name, _aimed, _witness in self._map_only_cards():
            listing = _listing(matrix)
            card = next(c for c in listing.clusters if c.field == field_name)
            assert card.mechanic == MECHANIC_RECAPTURE
            for row in listing.rows:
                if row.id in card.members:
                    assert row.donor_abstain == ABSTAIN_NO_READING


# ---------------------------------------------------------------------------
# A column holding two units
# ---------------------------------------------------------------------------


class TestAMixedUnitColumn:
    """MITSUBISHI144 reads a Celsius label from the low nibble and a
    Fahrenheit label from five bits of the same byte, the fifth being
    the half degree. A 76 F cell whose bytes say 24.5 C reads nibble 8,
    which is 24 C, so a search that compared only the fields applying
    at the 24 C target would hand it over and the repair would send
    24.5 for 24."""

    def test_a_24c_target_does_not_take_a_76f_donor(self):
        pack = _pack("MITSUBISHI144.json")
        field_map = MAPS["MITSUBISHI144"]
        codes = _codes(pack)
        target = "cool/auto/auto/24"
        fahrenheit = rewrite_field(
            field_map, codes[target],
            field_map.field_named("temperature_fahrenheit"), 0x18)
        assert fahrenheit is not None
        cell_76f = replace(
            next(c for c in pack.cells if cell_key(c) == target),
            temp=76.0, pronto=fahrenheit)
        matrix = _with(pack, {target: codes["cool/auto/auto/28"]})
        matrix = replace(matrix, cells=[*matrix.cells, cell_76f])
        lattice, payloads = _payloads(matrix)
        assert "temperature" in _fields(payloads[target])
        assert lattice.reads("cool/auto/auto/76", lattice.spec_for(
            "temperature")) == field_readers.expected_value(
                lattice.spec_for("temperature"), 24.0)
        donor, reason = find_donor(lattice, target, payloads[target])
        assert donor is None
        assert reason == ABSTAIN_NO_READING


# ---------------------------------------------------------------------------
# Compared, not named
# ---------------------------------------------------------------------------


class TestAMapOnlyFieldIsComparedNotNamed:
    """A vane nibble or a flag is a share of one setting, and naming it
    alone says something the code does not send: a powerful flag of 0
    is not "economy". So the read-back compares these fields and leaves
    them out of the labels it shows."""

    @pytest.mark.parametrize("build,target,source,field_name", [
        (lambda: _pack("DAIKIN216.json"), "cool/low/vertical/22",
         "cool/low/off/22", "swing_vertical"),
        (lambda: _d183(), "cool/powerful/off/24", "cool/high/off/24",
         "powerful"),
    ])
    def test_claims_and_reads_as_leave_it_out(self, build, target, source,
                                              field_name):
        matrix = build()
        lattice = read_lattice(matrix)
        verdict = pre_read(lattice, _codes(matrix)[source], _coords(target))
        assert verdict.matches is False
        assert field_name in verdict.mismatches
        assert field_name in verdict.raw_expected
        assert field_name in verdict.raw_read
        assert field_name not in verdict.claims
        assert field_name not in verdict.reads_as
        for name in verdict.claims:
            assert name in FIELD_COORDINATE or name == POWER_FIELD


# ---------------------------------------------------------------------------
# The #183 listing
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def listing_183():
    """Two powerful cells copied from high, and one cool cell that
    sends heat."""
    matrix = _d183({
        "cool/powerful/off/24": (0x7, {}),
        "cool/powerful/off/25": (0x7, {}),
    })
    heat = _stored_state(_file_form(_d152_settings(
        "heat", 0x7, 23, swing="vertical")))
    return _listing(_with(matrix, {"cool/high/vertical/23": heat}))


class TestThe183Listing:
    """The Needs attention listing on the #183 shape with two powerful
    cells copied from high and one cool cell sending heat. Only the
    reason on the powerful rows moves; the labels, the cards, their ids
    and their roads are what they were."""

    def test_the_powerful_rows_say_no_cell_reads_this(self, listing_183):
        for key in ("cool/powerful/off/24", "cool/powerful/off/25"):
            row = _row(listing_183, key)
            assert row.donor_abstain == ABSTAIN_NO_READING
            params = next(f["params"] for f in row.findings
                          if f["check"] == CHECK_FIELD_MISMATCH)
            # The plain sentence, as before: no label is put on a flag.
            assert "claimed" not in params
            assert "reads_as" not in params
            assert row.verdict["matches"] is False
            assert row.verdict["mismatches"] == ["powerful"]

    def test_the_other_row_is_unchanged(self, listing_183):
        row = _row(listing_183, "cool/high/vertical/23")
        assert row.donor_abstain == ABSTAIN_NO_READING
        params = next(f["params"] for f in row.findings
                      if f["check"] == CHECK_FIELD_MISMATCH)
        # No cell of this lattice is labelled heat, so the reading has
        # no label to borrow; the claim does.
        assert params["claimed"] == "cool"
        assert "reads_as" not in params

    def test_the_cards_keep_their_ids_and_roads(self, listing_183):
        assert {c.id: c.mechanic for c in listing_183.clusters} == {
            "same-reading:powerful:0x01:0x00:recapture": MECHANIC_RECAPTURE,
            "same-reading:mode:0x03:0x04:witness": MECHANIC_WITNESS,
        }
