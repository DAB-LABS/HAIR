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
from custom_components.hair.wig_comb import CHECK_DUPLICATED_NEIGHBOUR
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
    def test_fifty_two_findings_two_cards(self, komeco):
        """The number that decides whether this surface is usable."""
        assert len(komeco.rows) == 52
        assert len(komeco.clusters) == 2

    def test_the_two_cards_are_what_actually_went_wrong(self, komeco):
        """Pinned by identity, not by count. The column sends one step
        high. Forty-eight of those cells have a correct copy one step
        below them; four at the bottom have nothing below them to copy.
        """
        shape = {
            (c.rule, c.mechanic, c.detail.get("step")): c.size
            for c in komeco.clusters
        }
        assert shape == {
            (CLUSTER_SHIFT, MECHANIC_DONOR, 1): 48,
            (CLUSTER_SHIFT, MECHANIC_WITNESS, 1): 4,
        }

    def test_the_top_of_the_range_is_the_same_cause(self, komeco):
        """A four-bit field wrapping is still one step high. Counting
        the step around the field's own ring is what keeps the cells at
        the top of the domain in the card that repairs them -- split
        out, they draw their donor from a cell the other card
        overwrites."""
        card = next(c for c in komeco.clusters
                    if c.mechanic == MECHANIC_DONOR)
        tops = {m for m in card.members if m.endswith("/31")}
        assert len(tops) == 4

    def test_the_witness_card_is_the_bottom_of_the_range(self, komeco):
        card = next(c for c in komeco.clusters
                    if c.mechanic == MECHANIC_WITNESS)
        assert set(card.members) == {
            "cell:heat_cool/medium/both/19",
            "cell:heat_cool/medium/horizontal/19",
            "cell:heat_cool/medium/off/19",
            "cell:heat_cool/medium/vertical/19",
        }

    def test_a_card_that_feeds_another_is_offered_after_it(self, komeco):
        """The witness card holds the donors the big card needs, so it
        sorts behind it. Worked top down, every donor is still there
        when its card runs."""
        card = next(c for c in komeco.clusters
                    if c.mechanic == MECHANIC_WITNESS)
        assert card.detail["feeds"] == [
            "same-shift:temperature:1:donor"]
        assert komeco.clusters[-1] is card

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
            "same-shift:temperature:1:donor",
            "same-shift:temperature:1:witness",
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
    def test_a_twin_that_also_lies_is_filed_as_the_lie(self):
        """The severity order is about which finding a person reads
        first, and it is right. This is about which finding is the
        CAUSE, and a duplicate whose own bytes also disagree with its
        own label is a symptom of that disagreement.

        It matters because that is what a half-repaired shift looks
        like from the inside: copy a donor into a cell and it matches
        the still-broken neighbour it copied from until that neighbour
        is repaired too. Ranking the twin first would pull cells out of
        the very card about to fix them.
        """
        def drift(cells):
            cells["cool/medium/off/22"].pronto = cells[
                "cool/medium/off/23"].pronto

        listing = _komeco_listing(drift)
        rows = {r.target.key: r for r in listing.rows}
        liar = rows["cool/medium/off/22"]
        assert liar.classes[0] == CHECK_DUPLICATED_NEIGHBOUR
        card = next(c for c in listing.clusters if liar.id in c.members)
        assert card.rule == CLUSTER_SHIFT

    def test_the_healthy_twin_stands_alone_until_its_partner_is_fixed(self):
        """Cell 23 is correct. It is only a duplicate because 22 is
        carrying its code, and that stops being true the moment 22 is
        repaired -- so it is its own small card and not part of the
        repair."""
        def drift(cells):
            cells["cool/medium/off/22"].pronto = cells[
                "cool/medium/off/23"].pronto

        listing = _komeco_listing(drift)
        rows = {r.target.key: r for r in listing.rows}
        healthy = rows["cool/medium/off/23"]
        assert healthy.classes == [CHECK_DUPLICATED_NEIGHBOUR]
        card = next(c for c in listing.clusters if healthy.id in c.members)
        assert card.rule == CLUSTER_IDENTICAL
        assert card.members == [healthy.id]


class TestTheDriftedColumn:
    def test_a_four_cell_drift_joins_the_cause_that_explains_it(self):
        """The SG15H shape.

        Four cells sending one step high inside an otherwise healthy
        column are the same mistake as any other one-step drift, so they
        join that card -- except the one at the bottom, which has
        nothing left below it that reads as its label and needs a press
        instead. The healthy cell above the drift is briefly a duplicate
        of its top member and says so on its own.
        """
        def drift(cells):
            source = {t: cells[f"cool/high/off/{t}"].pronto
                      for t in (21, 22, 23, 24)}
            for t in (20, 21, 22, 23):
                cells[f"cool/high/off/{t}"].pronto = source[t + 1]

        listing = _komeco_listing(drift)
        placed = {}
        for card in listing.clusters:
            for member in card.members:
                if "cool/high/off" in member:
                    placed[member.rsplit("/", 1)[-1]] = card
        assert set(placed) == {"20", "21", "22", "23", "24"}
        assert {placed[t].mechanic for t in ("21", "22", "23")} == {
            MECHANIC_DONOR}
        assert placed["20"].mechanic == MECHANIC_WITNESS
        assert placed["24"].rule == CLUSTER_IDENTICAL

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
                    if c.id == "same-shift:temperature:1:donor")
        assert "cell:cool/high/off/21" in card.members
        assert "cell:heat_cool/medium/off/25" in card.members
        assert sorted(card.detail["spans"]["mode"]) == ["cool", "heat_cool"]
        assert sorted(card.detail["spans"]["fan"]) == ["high", "medium"]
