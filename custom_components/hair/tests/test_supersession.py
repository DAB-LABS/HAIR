"""Supersession (v0.9.7 "Second Fitting"): the ``supersedes`` ancestry.

The format guarantee this file pins is the one the whole feature leans
on: ``supersedes`` is lineage METADATA and nothing more. It round-trips
in order, it is forgiving on read, it is capped at both ends, and it
sits OUTSIDE every canonical form and every digest -- so carrying an
ancestry can never move a wig's identity or disturb a claim. The golden
vector is the proof of that last point.

Design authority: docs/internal/plans/supersession.md (owner-ruled
2026-08-04). Build: supersession-coding-plan.md, commit 1.
"""
from __future__ import annotations

import json

from custom_components.hair.wig_format import (
    SUPERSEDES_MAX,
    WIG_FORMAT_V1,
    WIG_FORMAT_V2,
    Wig,
    WigSignal,
    canonical_cells_json,
    canonical_signals_json,
    compose_supersedes,
    download_filename,
    parse_wig,
    serialize_wig,
    signal_row_digest,
    wig_row_digests,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"


def _wig_dict(**overrides) -> dict:
    base = {
        "format": WIG_FORMAT_V1,
        "name": "Fan XYZ",
        "signals": [{"alias": "Power", "pronto": PRONTO}],
    }
    base.update(overrides)
    return base


def _matrix_dict(**overrides) -> dict:
    base = {
        "format": WIG_FORMAT_V2,
        "name": "AC",
        "climate": {
            "min_temp": 16,
            "max_temp": 30,
            "off": PRONTO,
            "cells": [
                {"mode": "cool", "fan": "auto", "temp": 22, "pronto": PRONTO},
            ],
        },
    }
    base.update(overrides)
    return base


def _parse(data: dict):
    return parse_wig(json.dumps(data))


class TestRoundTrip:
    def test_list_survives_in_order(self):
        result = _parse(_wig_dict(supersedes=["parent-id", "grandparent-id"]))
        assert result.ok, result.errors
        assert result.wig.supersedes == ["parent-id", "grandparent-id"]

    def test_round_trip_preserves_order(self):
        original = _parse(_wig_dict(supersedes=["b", "a"])).wig
        again = parse_wig(serialize_wig(original))
        assert again.ok, again.errors
        assert again.wig.supersedes == ["b", "a"]
        # Serialized ALWAYS as a list.
        assert json.loads(serialize_wig(original))["supersedes"] == ["b", "a"]

    def test_absent_stays_absent(self):
        wig = _parse(_wig_dict()).wig
        assert wig.supersedes == []
        # Nothing empty leaks into the file.
        assert "supersedes" not in json.loads(serialize_wig(wig))

    def test_bare_string_becomes_one_element_list(self):
        wig = _parse(_wig_dict(supersedes="solo-parent")).wig
        assert wig.supersedes == ["solo-parent"]
        # And re-serializes as a LIST, not the bare string it came in as.
        assert json.loads(serialize_wig(wig))["supersedes"] == ["solo-parent"]

    def test_junk_entries_are_dropped_not_errored(self):
        # A non-string, an empty string, and a whitespace-only string are
        # ignored; the good ids survive in order. Lineage is metadata: a
        # bad entry must never fail an otherwise valid wig.
        result = _parse(_wig_dict(
            supersedes=["good-1", 7, "", "   ", "good-2"]
        ))
        assert result.ok, result.errors
        assert result.wig.supersedes == ["good-1", "good-2"]

    def test_entries_are_stripped(self):
        wig = _parse(_wig_dict(supersedes=["  padded-id  "])).wig
        assert wig.supersedes == ["padded-id"]


class TestGoldenVector:
    """Adding an ancestry changes NOTHING that identity or a claim reads.

    This is the point of putting ``supersedes`` outside every canonical
    form, and this is the test that would fail the day someone folds it
    into a hash.
    """

    def test_flat_digests_and_canonical_unchanged(self):
        with_field = _parse(_wig_dict(
            supersedes=["parent-id", "grandparent-id"]
        )).wig
        without = _parse(_wig_dict()).wig
        assert wig_row_digests(with_field) == wig_row_digests(without)
        assert canonical_signals_json(with_field.signals) == (
            canonical_signals_json(without.signals)
        )

    def test_matrix_canonical_cells_unchanged(self):
        with_field = _parse(_matrix_dict(supersedes=["parent-id"])).wig
        without = _parse(_matrix_dict()).wig
        assert canonical_cells_json(with_field.climate) == (
            canonical_cells_json(without.climate)
        )


class TestCapBothEnds:
    def test_parse_trims_to_max_dropping_the_oldest(self):
        # 17 in, 16 out, no error. Newest-first, so the OLDEST (the tail)
        # is the one dropped.
        ids = [f"id{i}" for i in range(SUPERSEDES_MAX + 1)]
        result = _parse(_wig_dict(supersedes=ids))
        assert result.ok, result.errors
        kept = result.wig.supersedes
        assert len(kept) == SUPERSEDES_MAX
        assert kept == ids[:SUPERSEDES_MAX]
        assert kept[0] == "id0"                       # newest kept
        assert ids[SUPERSEDES_MAX] not in kept         # oldest dropped

    def test_stamp_composes_then_trims_never_seventeen(self):
        # A Save-as-new whose source already carries a full 16-entry
        # chain stamps [source_id, *first 15], never a 17th.
        source_chain = [f"a{i}" for i in range(SUPERSEDES_MAX)]
        stamped = compose_supersedes("source-id", source_chain)
        assert len(stamped) == SUPERSEDES_MAX
        assert stamped[0] == "source-id"
        assert stamped[1:] == source_chain[:SUPERSEDES_MAX - 1]
        # The source's oldest ancestor falls off the end.
        assert source_chain[-1] not in stamped

    def test_stamp_with_no_local_source_is_the_single_link(self):
        assert compose_supersedes("source-id") == ["source-id"]
        assert compose_supersedes("source-id", []) == ["source-id"]

    def test_stamp_head_is_newest(self):
        stamped = compose_supersedes("parent", ["grandparent"])
        assert stamped == ["parent", "grandparent"]


def _worked_fitting(wig_id, signals):
    """A signed-shape bundle (unsigned; claims_summary never verifies)
    claiming every listed signal worked."""
    return {
        "wig_id": wig_id,
        "rows": [
            {
                "alias_at_claim": s.alias,
                "digest": signal_row_digest(s),
                "verdict": "worked",
            }
            for s in signals
        ],
    }


class TestDownloadFilename:
    """The field-derived download name (v0.9.7 Second Fitting):
    ``<brand>-<kind>-<model>`` with the earned tier appended, HYPHENATED.
    The pure-function guard for the naming ruling; the frontend-no-longer-
    composes guard lives in test_polish_rulings.
    """

    def test_full_fields(self):
        wig = Wig(
            name="Ignored", brand="Edifier", kind="soundbar",
            model="R1280T", signals=[WigSignal("On", PRONTO)],
        )
        assert download_filename(wig) == "edifier-soundbar-r1280t.wig.json"

    def test_missing_kind_is_skipped(self):
        wig = Wig(
            name="Ignored", brand="Edifier", model="R1280T",
            signals=[WigSignal("On", PRONTO)],
        )
        assert download_filename(wig) == "edifier-r1280t.wig.json"

    def test_missing_brand_falls_back_to_the_name(self):
        # No brand -> the field-derived form has no anchor, so the stem is
        # the slug of the wig's name, exactly as a plain download today.
        wig = Wig(
            name="Bench Fan", kind="fan",
            signals=[WigSignal("On", PRONTO)],
        )
        assert download_filename(wig) == "bench-fan.wig.json"

    def test_slug_rule_on_th_05(self):
        # The ruled example: TH-05 slugs to th-05 (one hyphen, no dot).
        wig = Wig(
            name="Ignored", brand="Sanmli", kind="candles", model="TH-05",
            signals=[WigSignal("On", PRONTO)],
        )
        assert download_filename(wig) == "sanmli-candles-th-05.wig.json"

    def test_unproven_appends_no_tier(self):
        wig = Wig(
            name="Ignored", brand="Acme",
            signals=[WigSignal("On", PRONTO)],
        )
        assert download_filename(wig) == "acme.wig.json"

    def test_scoped_appends_hyphen_fitted(self):
        # Two rows, one claimed worked: signed but incomplete -> scoped.
        s1 = WigSignal("On", PRONTO)
        s2 = WigSignal("Off", PRONTO_B)
        wig = Wig(
            name="Ignored", brand="Acme", wig_id="w1", signals=[s1, s2],
        )
        wig.extra["fittings"] = [_worked_fitting("w1", [s1])]
        assert download_filename(wig) == "acme-fitted.wig.json"

    def test_perfect_appends_hyphen_perfect_fit(self):
        # Every row claimed worked -> perfect.
        s1 = WigSignal("On", PRONTO)
        wig = Wig(
            name="Ignored", brand="Acme", wig_id="w1", signals=[s1],
        )
        wig.extra["fittings"] = [_worked_fitting("w1", [s1])]
        assert download_filename(wig) == "acme-perfect-fit.wig.json"

    def test_tier_is_never_dotted(self):
        # The whole point of the ask: no dot anywhere in the stem.
        s1 = WigSignal("On", PRONTO)
        wig = Wig(
            name="Ignored", brand="Acme", wig_id="w1", signals=[s1],
        )
        wig.extra["fittings"] = [_worked_fitting("w1", [s1])]
        name = download_filename(wig)
        assert name.endswith(".wig.json")
        assert "." not in name[: -len(".wig.json")]
