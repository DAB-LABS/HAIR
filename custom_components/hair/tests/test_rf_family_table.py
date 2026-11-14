"""The family table (second decoder round, owner go 2026-11-14 07:43 PT).

Every family is built and tested; whether its label is shown is one flag
in ``rf_family.FAMILIES``. A family that is off never adds a name or an
alias, and still counts when the certainty is worked out, so a frame
another family we know of also fits is never called ``decoded``.
"""
from __future__ import annotations

import dataclasses

import pytest

from custom_components.hair import rf_family
from custom_components.hair.rf_family import (
    CERTAINTY_AMBIGUOUS,
    CERTAINTY_DECODED,
    FAMILIES,
    family_of,
    family_payload,
)
from custom_components.hair.tests.test_rf_family import _frame

KEYFOB_ON = 0x950E49  # has a "10" symbol: EV1527 only
NO_10 = 0x0F3C0F  # symbols 00 11 11 00 ... : PT2262 or EV1527


@pytest.fixture
def switch(monkeypatch):
    """Set a family's ``shown`` flag for one test."""

    def set_shown(key: str, shown: bool) -> None:
        table = dict(FAMILIES)
        table[key] = dataclasses.replace(table[key], shown=shown)
        monkeypatch.setattr(rf_family, "FAMILIES", table)
        rf_family._family_of.cache_clear()

    yield set_shown
    rf_family._family_of.cache_clear()


class TestTheTable:
    def test_every_family_names_its_evidence(self):
        for spec in FAMILIES.values():
            assert spec.name and spec.evidence, spec.key

    def test_the_label_is_unchanged_for_the_first_round(self):
        assert family_of(_frame(KEYFOB_ON)).label == "EV1527"
        ambiguous = family_of(_frame(NO_10))
        assert ambiguous.label == "PT2262 or EV1527"
        assert ambiguous.family == "pt2262_ev1527"
        assert ambiguous.certainty == CERTAINTY_AMBIGUOUS

    def test_aliases_reach_the_payload(self):
        assert family_payload(_frame(KEYFOB_ON))["aliases"] == [
            "RT1527", "FP1527", "HS1527",
        ]
        assert family_payload(_frame(NO_10))["aliases"] == [
            "SC2262", "HX2262", "SC5262", "PT2260", "PT2264",
            "RT1527", "FP1527", "HS1527",
        ]

    def test_the_drawer_slots_do_not_change(self):
        assert set(rf_family.family_slots(_frame(KEYFOB_ON))) == {
            "protocol", "family_fields",
        }


class TestHiddenFamilies:
    def test_a_hidden_family_adds_no_name_or_alias(self, switch):
        switch("ev1527", False)
        result = family_of(_frame(NO_10))
        assert result.label == "PT2262"
        assert result.family == "pt2262"
        assert "RT1527" not in result.aliases

    def test_a_hidden_family_that_also_fits_keeps_it_ambiguous(self, switch):
        switch("ev1527", False)
        assert family_of(_frame(NO_10)).certainty == CERTAINTY_AMBIGUOUS

    def test_only_a_hidden_family_fits_means_no_label(self, switch):
        switch("ev1527", False)
        assert family_of(_frame(KEYFOB_ON)) is None
        assert family_payload(_frame(KEYFOB_ON)) is None

    def test_include_hidden_reads_it_as_shown(self, switch):
        switch("ev1527", False)
        result = family_of(_frame(KEYFOB_ON), include_hidden=True)
        assert result.label == "EV1527"
        assert result.certainty == CERTAINTY_DECODED

    def test_the_flag_is_the_only_switch(self, switch):
        switch("ev1527", False)
        assert family_of(_frame(KEYFOB_ON)) is None
        switch("ev1527", True)
        assert family_of(_frame(KEYFOB_ON)).label == "EV1527"


class TestNoise:
    """Both recorded noise hours (an Athom with nobody pressing, about
    33,000 pieces), through every family, hidden ones included: none may
    read as a family. Each new family is held to this as it lands."""

    @pytest.mark.parametrize("name", [
        "athom-433-150us-6ms-noise-1h.json.gz",
        "athom-433-150us-6ms-fs20-noise-1h.json.gz",
    ])
    def test_no_noise_piece_reads_as_any_family(self, name):
        import gzip
        import json
        from pathlib import Path

        from custom_components.hair import rf_frames

        path = Path(__file__).parent / "fixtures" / "rf" / "athom" / name
        captures = json.loads(gzip.decompress(path.read_bytes()))["captures"]
        read = [
            family_of(rf_frames._signed(list(piece.edges)), include_hidden=True)
            for _, timings in captures
            for piece in rf_frames.split_frames(timings)
        ]
        assert len(read) > 14_000
        assert [r.label for r in read if r is not None] == []


class TestNoDecoderRaises:
    """``family_of`` runs on every radio event and on every stored row a
    page loads, so a decoder must return None on garbage, never raise.
    Degenerate frames (zeros, one value, a stray edge; GH #108) and
    random ones, at every edge count any shape reads."""

    COUNTS = (25, 49, 57, 81, 127, 129, 131, 147)

    @staticmethod
    def _shapes():
        from custom_components.hair import rf_family
        return rf_family._SHAPES

    @pytest.mark.parametrize("n", COUNTS)
    def test_degenerate_frames(self, n):
        frames = [
            [0] * n,
            [0] * (n - 2) + [-100, 1],
            [1] * n,
            [1, -1] * (n // 2) + [1],
            [5, -5] * (n // 2) + [5, -30000],
            [0, -1] * (n // 2) + [0],
        ]
        for frame in frames:
            for decode in self._shapes():
                decode(tuple(frame))
            family_of(frame, include_hidden=True)

    @pytest.mark.parametrize("n", COUNTS)
    def test_random_frames(self, n):
        import random

        rng = random.Random(n)
        for _ in range(300):
            frame = [
                rng.choice((0, 1, rng.randint(0, 20000))) * (1 if i % 2 == 0 else -1)
                for i in range(n + rng.choice((0, 1)))
            ]
            for decode in self._shapes():
                decode(tuple(frame))
