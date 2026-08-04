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
    canonical_cells_json,
    canonical_signals_json,
    compose_supersedes,
    parse_wig,
    serialize_wig,
    wig_row_digests,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


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
