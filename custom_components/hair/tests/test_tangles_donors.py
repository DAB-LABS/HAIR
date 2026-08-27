"""The donor search: a repair that already exists somewhere in the wig.

A donor is not a reconstruction. Nothing here builds a frame, adjusts
one, or reasons about what bytes ought to look like. It asks one
question of codes that are already in the lattice -- does any of them
already send what this cell is supposed to send -- and where the answer
is no it says so and stops.

The Komeco column is the worked example and the reason the abstention
matters. Its defect is a shift: every cell sends what the next one up
should send. So 48 of the 52 have a donor sitting one step below them,
and the four at the bottom of the range have nothing to draw on,
because no code anywhere in that wig reads as 19.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hair.models import IRDevice
from custom_components.hair.tangles import (
    ABSTAIN_NO_READING,
    ABSTAIN_NOT_A_FIELD,
    ABSTAIN_NOT_RATIFIED,
    ABSTAIN_UNREADABLE,
    find_donor,
    list_tangles,
    read_lattice,
)
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_DISAGREEMENT,
)
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, Wig, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")

#: The four cells at the bottom of the defective column. Nothing in the
#: wig reads as 19, so the search has nowhere to look.
NO_DONOR = {
    "heat_cool/medium/both/19",
    "heat_cool/medium/horizontal/19",
    "heat_cool/medium/off/19",
    "heat_cool/medium/vertical/19",
}


@pytest.fixture(scope="module")
def komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


@pytest.fixture(scope="module")
def listing(komeco):
    return list_tangles(IRDevice(name="Komeco", climate_matrix=True),
                        komeco.climate)


def _mismatch(field: str = "temperature") -> list[dict]:
    return [{"check": CHECK_FIELD_MISMATCH,
             "params": {"field": f"comb.field.{field}"}}]


class TestTheKomecoColumn:
    def test_forty_eight_of_fifty_two(self, listing):
        """The ticket's acceptance number, and the abstention beside
        it. A search that found 52 would have invented four."""
        assert len(listing.rows) == 52
        assert sum(1 for row in listing.rows if row.has_donor) == 48

    def test_the_four_that_abstain_are_the_bottom_of_the_range(self, listing):
        without = {row.target.key for row in listing.rows
                   if not row.has_donor}
        assert without == NO_DONOR

    def test_an_abstention_says_why(self, listing):
        """Silence and "I looked and there is nothing" are different
        answers, and only one of them tells a person what to do next."""
        for row in listing.rows:
            if row.has_donor:
                assert row.donor_abstain is None
            else:
                assert row.donor_abstain == ABSTAIN_NO_READING

    def test_the_donor_is_the_cell_one_step_down(self, listing):
        """Pinned concretely rather than by shape: the column sends
        T+1, so the frame that reads as 25 is the one labelled 24."""
        row = next(r for r in listing.rows
                   if r.target.key == "heat_cool/medium/off/25")
        assert row.donor["key"] == "heat_cool/medium/off/24"
        assert row.donor["reasoning"] == {
            "fields": ["temperature"],
            "labelled": {"temperature": 24.0},
            "reads_as": {"temperature": 25.0},
        }

    def test_the_donor_carries_the_bytes_and_their_digest(self, listing,
                                                          komeco):
        row = next(r for r in listing.rows
                   if r.target.key == "heat_cool/medium/off/25")
        source = next(c for c in komeco.climate.cells
                      if c.temp == 24 and c.fan == "medium"
                      and c.mode == "heat_cool" and c.swing == "off")
        assert row.donor["pronto"] == source.pronto
        assert row.donor["pronto"] != row.pronto

    def test_a_donor_never_comes_from_another_corner_of_the_lattice(
            self, listing):
        """The only field this map ratifies on these cells is
        temperature, so nothing but the coordinate anchor stops a
        cooling frame being offered to repair a heating one."""
        for row in listing.rows:
            if not row.has_donor:
                continue
            here, there = row.target.coordinates, row.donor["coordinates"]
            assert (here["mode"], here["fan"], here["swing"]) == (
                there["mode"], there["fan"], there["swing"])
            assert here["temp"] != there["temp"]


class TestWhenItRefuses:
    def test_a_damaged_capture_has_no_donor(self, komeco):
        """Another cell's bytes do not repair a noisy recording of this
        one. The search declines the class rather than offering the
        nearest thing it can find."""
        lattice = read_lattice(komeco.climate)
        donor, reason = find_donor(
            lattice, "heat_cool/medium/off/25",
            [{"check": CHECK_FRAME_DISAGREEMENT, "params": {}}],
        )
        assert donor is None
        assert reason == ABSTAIN_NOT_A_FIELD

    def test_a_provisional_field_is_not_searched(self, komeco):
        """ZHLT01 marks mode provisional -- its own family inverts two
        mode values between files. A field the map will not vouch for
        cannot decide which frame is the right one."""
        lattice = read_lattice(komeco.climate)
        donor, reason = find_donor(
            lattice, "heat_cool/medium/off/25", _mismatch("mode"))
        assert donor is None
        assert reason == ABSTAIN_NOT_RATIFIED

    def test_an_unreadable_lattice_abstains(self):
        cells = [ClimateCell(mode="cool", fan="auto", temp=float(t),
                             pronto="0000 006D 0004 0000 0060 0020 0020 "
                                    "0020 0020 0020 0020 0060")
                 for t in (20, 21)]
        matrix = ClimateMatrix(
            min_temp=20.0, max_temp=21.0,
            off="0000 006D 0002 0000 0060 0020 0020 0060",
            cells=cells, modes=["cool"], fan_modes=["auto"],
        )
        lattice = read_lattice(matrix)
        assert not lattice.readable
        donor, reason = find_donor(lattice, "cool/auto/20", _mismatch())
        assert donor is None
        assert reason == ABSTAIN_UNREADABLE

    def test_no_lattice_at_all_abstains(self):
        lattice = read_lattice(None)
        assert not lattice.readable
        assert find_donor(lattice, "anything", _mismatch()) == (
            None, ABSTAIN_UNREADABLE)


class TestStability:
    def test_the_same_lattice_gives_the_same_donors(self, komeco):
        """Derived and pure: two calls over unchanged bytes agree, so a
        card the user opened twice never offers two different repairs."""
        device = IRDevice(name="Komeco", climate_matrix=True)
        first = list_tangles(device, komeco.climate)
        second = list_tangles(device, komeco.climate)
        assert [row.as_dict() for row in first.rows] == [
            row.as_dict() for row in second.rows]

    def test_the_lattice_is_read_before_any_repair_lands(self, komeco,
                                                         listing):
        """Every donor in one listing is resolved against the lattice as
        it stands, not against a lattice that is being written to. On a
        shifted column a search that re-read after each write would
        chase the shift and hand back the bytes it had just replaced.
        """
        lattice = read_lattice(komeco.climate)
        for row in listing.rows:
            if not row.has_donor:
                continue
            assert lattice.cells[row.donor["key"]].pronto == row.donor[
                "pronto"]
