"""Two names, one code, and a card that can ask about it.

Issue 5 of the detangler round. The practice-dupe wig was built to
surface a DECIDE pair -- "Speed Down" carrying "Power"'s code -- and the
device showed one LISTEN row and no DECIDE card at all. The comb had
found it and called it `duplicate-labels`, which is ADVISORY, and
advisories never became rows. DECIDE's only feed was a two-member
`identical-bytes` cluster, which only the matrix-lattice check could
produce, so on a flat wig DECIDE could not populate in any build.

Owner ruled 2026-08-29: promote the pair, and only the pair.

The classification does not move. `duplicate-labels` stays advisory,
stays out of the suspect count, and the closet's comb chip reads
exactly as before -- a flat file has no lattice to prove intent, and
same-code-different-label is right on a toggle remote. What changes is
that the ONE shape of it with a small obvious answer reaches the
surface built to ask: two names over one payload, rename or delete.
Three or more stays a mess for a person to look at rather than a
question a card can ask.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import CLUSTER_IDENTICAL, list_tangles
from custom_components.hair.wig_comb import (
    CHECK_DUPLICATE_LABELS,
    CHECK_FRAME_DISAGREEMENT,
    comb_wig,
    stamp_receipt,
    suspect_findings,
)
from custom_components.hair.wig_format import Wig, parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
DREO = (FIXTURES / "wigs" / "dreo-fan-dr-haf004s-perfect-fit.wig.json")

POWER = "Power"
DUPE = "Speed Down"
#: The Dreo's own frame-disagreement row, inherited from the real
#: capture and nothing to do with the pair. This is the LISTEN row the
#: owner saw where he expected a DECIDE card.
LISTENER = "Oscillate Horizontal"


@pytest.fixture
def dreo() -> Wig:
    parsed = parse_wig(DREO.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


def _device(wig: Wig, copies: dict[str, str]) -> IRDevice:
    """The wig as a flat device, with `copies` aliases sharing a code."""
    by_alias = {signal.alias: signal for signal in wig.signals}
    device = IRDevice(
        name="Practice Fan", emitter_entity_ids=["infrared.blaster"]
    )
    for signal in wig.signals:
        source = copies.get(signal.alias)
        device.add_command(IRCommand(
            name=signal.alias, category=CommandCategory.CUSTOM,
            protocol="PRONTO",
            code=by_alias[source].pronto if source else signal.pronto,
            repeat_count=signal.ditto_count,
            tx_force_raw=signal.bypass_protocol,
        ))
    return device


def _flat_wig(wig: Wig, copies: dict[str, str]) -> Wig:
    """The same shape as a wig, for combing on its own."""
    from dataclasses import replace

    by_alias = {signal.alias: signal for signal in wig.signals}
    return replace(wig, signals=[
        replace(signal, pronto=by_alias[copies[signal.alias]].pronto)
        if signal.alias in copies else signal
        for signal in wig.signals
    ])


def _listing(wig: Wig, copies: dict[str, str]) -> dict:
    return list_tangles(_device(wig, copies), None).as_dict()


def _rows_for(listing: dict, alias: str) -> list[dict]:
    return [
        row for row in listing["rows"]
        if row["target"]["key"] == alias
    ]


class TestThePairBecomesACard:
    def test_both_names_get_a_row(self, dreo):
        listing = _listing(dreo, {DUPE: POWER})
        assert len(_rows_for(listing, POWER)) == 1
        assert len(_rows_for(listing, DUPE)) == 1
        for alias in (POWER, DUPE):
            classes = _rows_for(listing, alias)[0]["classes"]
            assert CHECK_DUPLICATE_LABELS in classes

    def test_they_land_in_one_two_member_cluster(self, dreo):
        """What DECIDE reads. Two rows and one card, not two cards of
        one row each."""
        listing = _listing(dreo, {DUPE: POWER})
        ids = {
            row["id"] for row in listing["rows"]
            if row["target"]["key"] in (POWER, DUPE)
        }
        pairs = [
            cluster for cluster in listing["clusters"]
            if cluster["rule"] == CLUSTER_IDENTICAL
        ]
        assert len(pairs) == 1
        assert set(pairs[0]["members"]) == ids

    def test_one_card_even_when_the_two_carry_different_dittos(self, dreo):
        """The rows' digests take the ditto count in, so keying the card
        on them would split a pair that differs only in delivery. The
        card is keyed on the payload the comb grouped them by."""
        listing = _listing(dreo, {DUPE: POWER})
        digests = {
            row["digest"] for row in listing["rows"]
            if row["target"]["key"] in (POWER, DUPE)
        }
        assert len(digests) == 2
        assert len([
            c for c in listing["clusters"] if c["rule"] == CLUSTER_IDENTICAL
        ]) == 1

    def test_the_pair_leaves_the_advisory_list(self, dreo):
        """No double-report. A finding that became rows is not also
        reported as something nobody acted on."""
        listing = _listing(dreo, {DUPE: POWER})
        assert [
            advisory for advisory in listing["advisories"]
            if advisory["check"] == CHECK_DUPLICATE_LABELS
        ] == []


class TestTheClassificationDoesNotMove:
    def test_the_comb_still_calls_it_advisory(self, dreo):
        """Promotion happens in the listing. The comb is untouched, so
        the file's own receipt reads exactly as it did."""
        report = comb_wig(_flat_wig(dreo, {DUPE: POWER}))
        finding = next(
            f for f in report.findings if f.check == CHECK_DUPLICATE_LABELS
        )
        assert finding.advisory is True
        assert sorted(finding.keys) == sorted([POWER, DUPE])

    def test_the_pair_counts_as_no_suspects(self, dreo):
        """The closet chip and the suspect count are the owner's stated
        boundary on this change."""
        wig = _flat_wig(dreo, {DUPE: POWER})
        stamp_receipt(wig, comb_wig(wig), "2026-08-29")
        suspects = suspect_findings(wig)
        assert POWER not in suspects
        assert DUPE not in suspects


class TestOnlyExactlyTwo:
    def test_three_names_stay_advisory_with_no_rows(self, dreo):
        """A pair has one question with two answers. Three is a mess a
        person should look at, not a card."""
        listing = _listing(dreo, {DUPE: POWER, "Timer": POWER})
        for alias in (POWER, DUPE, "Timer"):
            assert _rows_for(listing, alias) == []
        assert [
            advisory for advisory in listing["advisories"]
            if advisory["check"] == CHECK_DUPLICATE_LABELS
        ] != []

    def test_a_clean_wig_still_has_no_pair_card(self, dreo):
        listing = _listing(dreo, {})
        assert [
            cluster for cluster in listing["clusters"]
            if cluster["rule"] == CLUSTER_IDENTICAL
        ] == []


class TestThePracticeDupeShape:
    """The fixture the owner was actually holding: one planted pair, and
    the Dreo's own unrelated frame disagreement."""

    def test_a_decide_pair_and_one_listen_row(self, dreo):
        listing = _listing(dreo, {DUPE: POWER})
        by_rule: dict[str, list] = {}
        for cluster in listing["clusters"]:
            by_rule.setdefault(cluster["rule"], []).append(cluster)
        assert len(by_rule[CLUSTER_IDENTICAL]) == 1
        assert len(by_rule[CLUSTER_IDENTICAL][0]["members"]) == 2

        others = [
            cluster for cluster in listing["clusters"]
            if cluster["rule"] != CLUSTER_IDENTICAL
        ]
        assert len(others) == 1
        listener = _rows_for(listing, LISTENER)
        assert len(listener) == 1
        assert CHECK_FRAME_DISAGREEMENT in listener[0]["classes"]
        assert others[0]["members"] == [listener[0]["id"]]

    def test_the_pair_does_not_swallow_the_listen_row(self, dreo):
        """Three rows in total, and the LISTEN one is still its own
        question."""
        listing = _listing(dreo, {DUPE: POWER})
        assert len(listing["rows"]) == 3
