"""Causes, not findings.

Fifty-two findings must not read as fifty-two chores. The comb emits one
finding per cell because that is what it observed; this tier asks what
went wrong ONCE and lists the cells as the evidence behind it.

Two axes decide a card, and both are needed. The CAUSE says why these
targets are wrong together. The MECHANIC says what can be done about
them, and it has to split a cause when one road runs out: the Komeco
column is a single shift, but the four cells at the bottom of its range
have nothing to copy from and have to be witnessed instead, and a card
with two primary actions is not a card.

Nothing here invents structure. Where the rules do not group, the row
stands alone.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    CLUSTER_IDENTICAL,
    CLUSTER_SHIFT,
    CLUSTER_SINGLETON,
    MECHANIC_DONOR,
    MECHANIC_RECAPTURE,
    MECHANIC_WITNESS,
    list_tangles,
)
from custom_components.hair.wig_format import Wig, cell_key, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
DREO = (FIXTURES / "wigs"
        / "dreo-fan-dr-haf004s-perfect-fit.wig.json")


def _wig(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


def _komeco_listing(mutate=None):
    wig = _wig(KOMECO)
    if mutate is not None:
        mutate({cell_key(c): c for c in wig.climate.cells})
    return list_tangles(
        IRDevice(name="Komeco", climate_matrix=True), wig.climate)


@pytest.fixture(scope="module")
def komeco():
    return _komeco_listing()


class TestTheKomecoCards:
    def test_fifty_two_findings_three_cards(self, komeco):
        """The number that decides whether this surface is usable."""
        assert len(komeco.rows) == 52
        assert len(komeco.clusters) == 3

    def test_the_three_cards_are_what_actually_went_wrong(self, komeco):
        """Pinned by identity, not by count.

        The column sends one step high. Forty-four of those cells have a
        correct copy one step below them. Four at the TOP of the range
        wrap the four-bit field instead of stepping, which is the same
        mistake arriving at the end of the domain. Four at the BOTTOM
        have nothing below them to copy.
        """
        shape = {
            (c.rule, c.mechanic, c.detail.get("step")): c.size
            for c in komeco.clusters
        }
        assert shape == {
            (CLUSTER_SHIFT, MECHANIC_DONOR, 1.0): 44,
            (CLUSTER_SHIFT, MECHANIC_DONOR, -15.0): 4,
            (CLUSTER_SHIFT, MECHANIC_WITNESS, 1.0): 4,
        }

    def test_the_witness_card_is_the_bottom_of_the_range(self, komeco):
        card = next(c for c in komeco.clusters
                    if c.mechanic == MECHANIC_WITNESS)
        assert set(card.members) == {
            "cell:heat_cool/medium/both/19",
            "cell:heat_cool/medium/horizontal/19",
            "cell:heat_cool/medium/off/19",
            "cell:heat_cool/medium/vertical/19",
        }

    def test_every_row_is_on_exactly_one_card(self, komeco):
        """A row on no card is a repair nobody is offered; a row on two
        is a repair somebody applies twice."""
        members = [m for c in komeco.clusters for m in c.members]
        assert sorted(members) == sorted(r.id for r in komeco.rows)

    def test_a_card_says_what_it_spans(self, komeco):
        """The representative test picks its sample from this."""
        for card in komeco.clusters:
            assert card.detail["spans"]["mode"] == ["heat_cool"]
            assert card.detail["spans"]["fan"] == ["medium"]
            assert card.detail["spans"]["swing"] == [
                "both", "horizontal", "off", "vertical"]

    def test_the_cards_name_the_field(self, komeco):
        assert {c.field for c in komeco.clusters} == {"temperature"}


class TestDeterminism:
    def test_two_calls_agree(self):
        first, second = _komeco_listing(), _komeco_listing()
        assert [c.as_dict() for c in first.clusters] == [
            c.as_dict() for c in second.clusters]

    def test_ids_come_from_the_cause_not_a_counter(self, komeco):
        """So a card the user opened yesterday is the same card today,
        on any install, after any restart."""
        assert {c.id for c in komeco.clusters} == {
            "same-shift:temperature:1.0:donor",
            "same-shift:temperature:-15.0:donor",
            "same-shift:temperature:1.0:witness",
        }
        for card in komeco.clusters:
            assert card.id.startswith(card.cause)


class TestNoInventedStructure:
    def test_the_dreo_stays_two_separate_things(self):
        """Two noisy captures on one remote are two accidents, not a
        pattern. The receipt carries no capture session to group them
        by, so grouping them would be a claim nothing supports."""
        wig = _wig(DREO)
        device = IRDevice(name="Dreo")
        for signal in wig.signals:
            device.add_command(IRCommand(
                name=signal.alias, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=signal.pronto,
                send_count=signal.send_count,
                repeat_count=signal.ditto_count,
                tx_force_raw=signal.bypass_protocol,
            ))
        listing = list_tangles(device, None)
        assert len(listing.clusters) == 2
        assert {c.rule for c in listing.clusters} == {CLUSTER_SINGLETON}
        assert {c.mechanic for c in listing.clusters} == {MECHANIC_RECAPTURE}
        assert all(c.size == 1 for c in listing.clusters)

    def test_a_clean_device_has_no_cards(self):
        assert list_tangles(IRDevice(name="Bare"), None).clusters == []


class TestByteIdenticalGroups:
    def test_a_shared_code_lists_every_location(self):
        """One card per shared code, listing everywhere it appears --
        and NOT split by road, because the answer to "these four cells
        send the same bytes" is about the group, not the member.
        """
        def drift(cells):
            for swing in ("off", "both", "horizontal", "vertical"):
                cells[f"cool/medium/{swing}/22"].pronto = cells[
                    f"cool/medium/{swing}/23"].pronto

        listing = _komeco_listing(drift)
        duplicates = [c for c in listing.clusters
                      if c.rule == CLUSTER_IDENTICAL]
        assert len(duplicates) == 4
        assert all(card.size == 2 for card in duplicates)
        for card in duplicates:
            assert len({m.rsplit("/", 1)[-1] for m in card.members}) == 2

    def test_the_duplicate_outranks_the_mismatch_that_came_with_it(self):
        """A cell that is both a duplicate and a lie is a duplicate
        first: the comb ranks it higher, and its repair is different in
        kind -- one of the two has to change, and no donor decides
        which."""
        def drift(cells):
            cells["cool/medium/off/22"].pronto = cells[
                "cool/medium/off/23"].pronto

        listing = _komeco_listing(drift)
        card = next(c for c in listing.clusters
                    if c.rule == CLUSTER_IDENTICAL)
        assert set(card.members) == {
            "cell:cool/medium/off/22", "cell:cool/medium/off/23"}


class TestTheDriftedColumn:
    def test_a_four_cell_drift_does_not_land_as_one_card(self):
        """The SG15H shape, and an honest correction to the expectation
        written for it.

        Four cells sending T+1 inside an otherwise healthy column do NOT
        collapse to a single card of four, and cannot. The top member of
        any contiguous one-step drift is byte-identical to the healthy
        cell above it -- that is what a one-step drift MEANS at its
        upper edge -- so the duplicate check claims that pair, and the
        bottom member has nothing left below it that reads as its label.
        What survives in the shift card is the middle.

        Pinned to what the checks actually compute rather than tuned to
        a number reached by a different method.
        """
        def drift(cells):
            source = {t: cells[f"cool/high/off/{t}"].pronto
                      for t in (21, 22, 23, 24)}
            for t in (20, 21, 22, 23):
                cells[f"cool/high/off/{t}"].pronto = source[t + 1]

        listing = _komeco_listing(drift)
        cards = {
            card.id: card for card in listing.clusters
            if any("cool/high/off" in member for member in card.members)
        }
        drifted = {
            member for card in cards.values() for member in card.members
            if "cool/high/off" in member
        }
        assert drifted == {
            "cell:cool/high/off/20", "cell:cool/high/off/21",
            "cell:cool/high/off/22", "cell:cool/high/off/23",
            "cell:cool/high/off/24",
        }
        duplicate = next(c for c in cards.values()
                         if c.rule == CLUSTER_IDENTICAL)
        assert set(duplicate.members) == {
            "cell:cool/high/off/23", "cell:cool/high/off/24"}

        witness = next(c for c in cards.values()
                       if c.mechanic == MECHANIC_WITNESS)
        assert "cell:cool/high/off/20" in witness.members

    def test_two_drifted_columns_of_the_same_step_share_a_card(self):
        """Deliberate. The diagnosis is true of every member -- the
        temperature reads one step high -- and the card carries the
        spans, so a surface can still name both columns. Splitting by
        coordinate would multiply the Komeco load by its swing count for
        no gain in what anybody has to decide.
        """
        def drift(cells):
            source = {t: cells[f"cool/high/off/{t}"].pronto
                      for t in (21, 22, 23, 24)}
            for t in (20, 21, 22, 23):
                cells[f"cool/high/off/{t}"].pronto = source[t + 1]

        listing = _komeco_listing(drift)
        card = next(c for c in listing.clusters
                    if c.id == "same-shift:temperature:1.0:donor")
        assert "cell:cool/high/off/21" in card.members
        assert "cell:heat_cool/medium/off/25" in card.members
        assert sorted(card.detail["spans"]["mode"]) == ["cool", "heat_cool"]
        assert sorted(card.detail["spans"]["fan"]) == ["high", "medium"]
