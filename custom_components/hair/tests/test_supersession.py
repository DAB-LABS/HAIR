"""Supersession (v0.9.7 "Second Fitting"): the ``supersedes`` ancestry.

The format guarantee this file pins is the one the whole feature leans
on: ``supersedes`` is lineage METADATA and nothing more. It round-trips
in order, it is forgiving on read, it is capped at both ends, and it
sits OUTSIDE every canonical form and every digest -- so carrying an
ancestry can never move a wig's identity or disturb a claim. The golden
vector is the proof of that last point.

Design authority: docs/internal/plans/supersession.md (owner-ruled
2026-08-04), amended by second-fitting-amendment.md v2 (owner-ruled on
the bench 2026-08-04). Build: supersession-coding-plan.md, commit 1;
TestTheVerbIsDerived below is amendment v2, commit 8.
"""
from __future__ import annotations

import json

from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.wig_export import build_wig_from_device
from custom_components.hair.wig_format import (
    SUPERSEDES_MAX,
    VERDICT_WORKED,
    WIG_FORMAT_V1,
    WIG_FORMAT_V2,
    ClaimsBundle,
    ClimateCell,
    ClimateMatrix,
    RowClaim,
    Wig,
    WigSignal,
    canonical_cells_json,
    canonical_signals_json,
    claims_bundle_out,
    compose_supersedes,
    download_filename,
    parse_wig,
    serialize_wig,
    signal_row_digest,
    wig_row_digests,
)
from custom_components.hair.wig_save import (
    VARIANT_CREATE,
    VARIANT_SUCCESSION,
    VARIANT_UPDATE,
    Attestation,
    _allowed_claim_digests,
    _differentiated_name,
    build_save_plan,
    detect_supersession,
    drop_ghost_claims,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"
PRONTO_C = "0000 006D 0002 0000 0040 0040 0020 0040"


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


def _pronto_command(name, code):
    return IRCommand(name=name, protocol="PRONTO", code=code, repeat_count=0)


class TestDetectSupersession:
    """The shared detection both doorways call. Pure: it takes a config
    dir, the arriving wig, and the device list, and answers with the
    replace-flow block or None."""

    def _closet(self, tmp_path, wig, filename):
        ensure_wigs_dir(tmp_path)
        (wigs_dir(tmp_path) / filename).write_text(
            serialize_wig(wig), encoding="utf-8"
        )

    def test_no_local_ancestor_returns_none(self, tmp_path):
        new = Wig(
            name="New", wig_id="new", supersedes=["not-here"],
            signals=[WigSignal("On", PRONTO)],
        )
        assert detect_supersession(str(tmp_path), new, []) is None

    def test_no_supersedes_returns_none(self, tmp_path):
        new = Wig(name="Fresh", wig_id="new", signals=[WigSignal("On", PRONTO)])
        assert detect_supersession(str(tmp_path), new, []) is None

    def test_local_ancestor_returns_block_with_counts(self, tmp_path):
        old = Wig(
            name="Fan XYZ", wig_id="old",
            signals=[WigSignal("On", PRONTO), WigSignal("Off", PRONTO_B)],
        )
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan XYZ v2", wig_id="new", supersedes=["old"],
            signals=[
                WigSignal("On", PRONTO), WigSignal("Off", PRONTO_B),
                WigSignal("Boost", PRONTO_C),
            ],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block is not None
        assert block["old_filename"] == "old.wig.json"
        assert block["old_name"] == "Fan XYZ"
        assert block["old_signals"] == 2
        assert block["new_signals"] == 3
        # Every old row is carried forward, so nothing is lost.
        assert block["lost_digests"] == []
        assert block["lost_aliases"] == []
        assert block["devices"] == []

    def test_lost_rows_are_exact_by_digest_not_name(self, tmp_path):
        old = Wig(
            name="Fan", wig_id="old",
            signals=[
                WigSignal("On", PRONTO), WigSignal("Oscillate", PRONTO_B),
            ],
        )
        self._closet(tmp_path, old, "old.wig.json")
        # The successor carries On (renamed to Power -- same bytes, same
        # digest, so NOT a loss) but drops Oscillate.
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("Power", PRONTO)],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block["lost_aliases"] == ["Oscillate"]
        assert block["lost_digests"] == [
            signal_row_digest(WigSignal("Oscillate", PRONTO_B))
        ]

    def test_any_hop_matches_the_second_ancestor(self, tmp_path):
        # The parent left the shelf; the grandparent (second entry) is
        # still local. The block fires on the grandparent.
        grand = Wig(
            name="Gen1", wig_id="grand", signals=[WigSignal("On", PRONTO)]
        )
        self._closet(tmp_path, grand, "grand.wig.json")
        new = Wig(
            name="Gen3", wig_id="new", supersedes=["parent", "grand"],
            signals=[WigSignal("On", PRONTO)],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block is not None
        assert block["old_filename"] == "grand.wig.json"

    def test_newest_first_prefers_the_nearer_ancestor(self, tmp_path):
        parent = Wig(
            name="Gen2", wig_id="parent", signals=[WigSignal("On", PRONTO)]
        )
        grand = Wig(
            name="Gen1", wig_id="grand", signals=[WigSignal("On", PRONTO)]
        )
        self._closet(tmp_path, parent, "parent.wig.json")
        self._closet(tmp_path, grand, "grand.wig.json")
        new = Wig(
            name="Gen3", wig_id="new", supersedes=["parent", "grand"],
            signals=[WigSignal("On", PRONTO)],
        )
        block = detect_supersession(str(tmp_path), new, [])
        # First match wins, walking newest-first.
        assert block["old_filename"] == "parent.wig.json"

    def test_sourced_devices_report_their_missing_counts(self, tmp_path):
        old = Wig(name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO)])
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("On", PRONTO), WigSignal("Boost", PRONTO_B)],
        )
        # Adopted from old, holds only On -> missing 1 (Boost). An
        # unrelated device is not listed.
        living = IRDevice(
            name="Living Room Fan", source_wig_id="old",
            commands=[_pronto_command("On", PRONTO)],
        )
        other = IRDevice(
            name="Unrelated", source_wig_id="elsewhere",
            commands=[_pronto_command("On", PRONTO)],
        )
        block = detect_supersession(str(tmp_path), new, [living, other])
        assert len(block["devices"]) == 1
        assert block["devices"][0]["name"] == "Living Room Fan"
        assert block["devices"][0]["missing_commands"] == 1
        # Amendment v2 section 2: the confirm names the missing row,
        # it no longer just counts it.
        assert block["devices"][0]["missing_aliases"] == ["Boost"]


class TestDetectSupersessionMatrix:
    """Second Fitting v3 punch list item 15: a matrix wig meeting this
    shared detection for the first time. ``wig_row_digests()`` returns
    ``[]`` for any wig carrying a climate block (a matrix wig's claims
    bind the lattice by ``cells_hash``, not row digests), but a matrix
    wig still carries flat ``.signals`` beside the lattice (Fujitsu
    AR-RY4: 11 flat signals plus the lattice) -- pairing
    ``wig_row_digests(new_wig)`` against ``new_wig.signals`` via
    ``zip(strict=True)`` crashed the moment those two disagreed in
    length, AFTER the file had already been written to the shelf. This
    is the owner's bench traceback, reproduced and pinned.
    """

    def _closet(self, tmp_path, wig, filename):
        ensure_wigs_dir(tmp_path)
        (wigs_dir(tmp_path) / filename).write_text(
            serialize_wig(wig), encoding="utf-8"
        )

    def _matrix(self):
        return ClimateMatrix(
            min_temp=16.0, max_temp=30.0, off=PRONTO,
            modes=["cool"], fan_modes=["auto"],
            cells=[
                ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=PRONTO),
            ],
        )

    def test_matching_matrix_wig_does_not_crash_and_loses_nothing(
        self, tmp_path
    ):
        old = Wig(
            name="AC", wig_id="old",
            signals=[WigSignal("Sleep", PRONTO), WigSignal("Timer", PRONTO_B)],
        )
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="AC v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("Sleep", PRONTO), WigSignal("Timer", PRONTO_B)],
            climate=self._matrix(),
        )
        # Pre-fix this raised ValueError: zip() argument 2 is longer
        # than argument 1 -- wig_row_digests(new) returned [] because
        # new.climate is set, but new.signals still had two rows.
        block = detect_supersession(str(tmp_path), new, [])
        assert block is not None
        assert block["lost_digests"] == []
        assert block["lost_aliases"] == []

    def test_diverged_matrix_wig_reports_the_lost_flat_row(self, tmp_path):
        old = Wig(
            name="AC", wig_id="old",
            signals=[WigSignal("Sleep", PRONTO), WigSignal("Timer", PRONTO_B)],
        )
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="AC v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("Sleep", PRONTO)],
            climate=self._matrix(),
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block["lost_aliases"] == ["Timer"]
        assert block["lost_digests"] == [
            signal_row_digest(WigSignal("Timer", PRONTO_B))
        ]

    def test_sourced_device_missing_aliases_resolve_through_the_new_map(
        self, tmp_path
    ):
        """The exact line that crashed: ``new_alias_by_digest``, now
        built per-signal instead of zipped against
        ``wig_row_digests()``, must still resolve every missing
        device row's alias for a matrix arrival."""
        old = Wig(name="AC", wig_id="old", signals=[WigSignal("Sleep", PRONTO)])
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="AC v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("Sleep", PRONTO), WigSignal("Timer", PRONTO_B)],
            climate=self._matrix(),
        )
        living = IRDevice(
            name="Living Room AC", source_wig_id="old",
            commands=[_pronto_command("Sleep", PRONTO)],
        )
        block = detect_supersession(str(tmp_path), new, [living])
        assert block["devices"][0]["missing_aliases"] == ["Timer"]


class TestOldFittings:
    """Amendment v2 section 2: the confirm grades what replacing the
    ancestor retires. ``handles`` credits every handle that ever
    fitted it, first-seen order, regardless of scoped or complete --
    the self doorway's "is anyone OTHER than me on this ancestor"
    check needs everyone, not just the perfect ones.
    """

    def _closet(self, tmp_path, wig, filename):
        ensure_wigs_dir(tmp_path)
        (wigs_dir(tmp_path) / filename).write_text(
            serialize_wig(wig), encoding="utf-8"
        )

    def test_no_claims_is_the_light_state(self, tmp_path):
        old = Wig(name="Fan", wig_id="old", signals=[WigSignal("On", PRONTO)])
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"],
            signals=[WigSignal("On", PRONTO), WigSignal("Boost", PRONTO_B)],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block["old_fittings"] == {
            "count": 0, "state": None, "handles": [],
        }

    def test_scoped_credits_everyone_who_tried(self, tmp_path):
        s1 = WigSignal("On", PRONTO)
        s2 = WigSignal("Off", PRONTO_B)
        old = Wig(name="Fan", wig_id="old", signals=[s1, s2])
        # Alice only claimed On -> scoped, not perfect.
        old.extra["fittings"] = [
            {**_worked_fitting("old", [s1]), "handle": "Alice"},
        ]
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"], signals=[s1, s2],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block["old_fittings"]["state"] == "scoped"
        assert block["old_fittings"]["count"] == 1
        assert block["old_fittings"]["handles"] == ["Alice"]

    def test_perfect_when_someone_covers_every_row(self, tmp_path):
        s1 = WigSignal("On", PRONTO)
        old = Wig(name="Fan", wig_id="old", signals=[s1])
        old.extra["fittings"] = [
            {**_worked_fitting("old", [s1]), "handle": "Bob"},
        ]
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"], signals=[s1],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block["old_fittings"]["state"] == "perfect"
        assert block["old_fittings"]["handles"] == ["Bob"]

    def test_handles_are_deduped_first_seen_order(self, tmp_path):
        # Everyone, not just the perfect ones -- Alice never covers
        # every row, but her name still carries so the self doorway can
        # ask "is anyone OTHER than me on this ancestor".
        s1 = WigSignal("On", PRONTO)
        s2 = WigSignal("Off", PRONTO_B)
        old = Wig(name="Fan", wig_id="old", signals=[s1, s2])
        old.extra["fittings"] = [
            {**_worked_fitting("old", [s1]), "handle": "Alice"},
            {**_worked_fitting("old", [s1, s2]), "handle": "Bob"},
            {**_worked_fitting("old", [s2]), "handle": "Alice"},
        ]
        self._closet(tmp_path, old, "old.wig.json")
        new = Wig(
            name="Fan v2", wig_id="new", supersedes=["old"], signals=[s1, s2],
        )
        block = detect_supersession(str(tmp_path), new, [])
        assert block["old_fittings"]["state"] == "perfect"
        assert block["old_fittings"]["count"] == 3
        assert block["old_fittings"]["handles"] == ["Alice", "Bob"]


class TestDropGhostClaims:
    """A claim whose digest the wig does not carry never reaches the
    bundle (v0.9.7): a device-only row's tick would bind bytes not in the
    file. Server-side belt-and-suspenders behind the dialog no longer
    offering it.
    """

    def test_foreign_digest_dropped_real_kept(self):
        s1 = WigSignal("On", PRONTO)
        wig = Wig(name="Fan", wig_id="w", signals=[s1])
        real = signal_row_digest(s1)
        att = Attestation(
            claims={real: "worked", "f" * 16: "worked"}, handle="David"
        )
        out = drop_ghost_claims(att, wig)
        assert out.claims == {real: "worked"}
        # Everything else on the attestation is untouched.
        assert out.handle == "David"

    def test_all_real_returns_the_same_object(self):
        s1 = WigSignal("On", PRONTO)
        wig = Wig(name="Fan", wig_id="w", signals=[s1])
        att = Attestation(claims={signal_row_digest(s1): "worked"})
        # Nothing filtered -> no copy, the caller's object comes straight
        # back.
        assert drop_ghost_claims(att, wig) is att

    def test_matrix_checklist_digest_is_allowed(self):
        # A matrix wig's dimension-checklist cells are legitimate claims;
        # a foreign digest is still dropped.
        matrix_wig = _parse(_matrix_dict()).wig
        allowed = _allowed_claim_digests(matrix_wig)
        assert allowed
        good = next(iter(allowed))
        att = Attestation(claims={good: "worked", "f" * 16: "worked"})
        out = drop_ghost_claims(att, matrix_wig)
        assert good in out.claims
        assert "f" * 16 not in out.claims


class TestTheVerbIsDerived:
    """Second Fitting amendment v2 (owner-ruled on the bench 2026-08-04),
    commit 8. Nobody picks the verb: build_save_plan reads it off the
    device's own divergence from its source, by digest. Renames and
    metadata never count -- only an added or removed row does.
    """

    def test_no_source_is_create(self):
        device = IRDevice(
            name="Fan", commands=[_pronto_command("On", PRONTO)],
        )
        plan = build_save_plan(device)
        assert plan.variant == VARIANT_CREATE

    def test_matching_content_is_update(self):
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        device = IRDevice(
            name="Fan", commands=[_pronto_command("On", PRONTO)],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_UPDATE

    def test_rename_only_is_still_update(self):
        """A local rename is a digest-only match (pass two), never a
        divergence -- the amendment's own rule: digest-set comparison
        decides, nothing else."""
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        device = IRDevice(
            name="Fan", commands=[_pronto_command("Power", PRONTO)],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_UPDATE
        assert plan.rows[0].renamed is True

    def test_addition_diverges_to_succession(self):
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        device = IRDevice(
            name="Fan", commands=[
                _pronto_command("On", PRONTO),
                _pronto_command("Turbo", PRONTO_B),
            ],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_SUCCESSION

    def test_removal_diverges_to_succession(self):
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[
                WigSignal(alias="On", pronto=PRONTO),
                WigSignal(alias="Oscillate", pronto=PRONTO_B),
            ],
        )
        device = IRDevice(
            name="Fan", commands=[_pronto_command("On", PRONTO)],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_SUCCESSION
        assert [r.alias for r in plan.missing_rows] == ["Oscillate"]

    # -- matrix: the lattice must never masquerade as a flat divergence --

    _P_A = "0000 006D 0002 0000 0020 0040 0020 0040"
    _P_B = "0000 006D 0002 0000 0030 0040 0020 0040"
    _P_C = "0000 006D 0002 0000 0040 0040 0020 0040"
    _P_SLEEP = "0000 006D 0002 0000 0070 0040 0020 0040"
    _P_TIMER = "0000 006D 0002 0000 0080 0040 0020 0040"
    _P_REPAIRED = "0000 006D 0002 0000 0090 0040 0020 0040"

    def _matrix(self):
        return ClimateMatrix(
            min_temp=16.0, max_temp=30.0, off=self._P_A,
            modes=["cool", "heat"], fan_modes=["auto"],
            cells=[
                ClimateCell(mode="cool", fan="auto", temp=16.0,
                            pronto=self._P_A),
                ClimateCell(mode="cool", fan="auto", temp=30.0,
                            pronto=self._P_B),
                ClimateCell(mode="heat", fan="auto", temp=22.0,
                            pronto=self._P_C),
            ],
        )

    def _matrix_source_wig(self, extra_pronto=None):
        device = IRDevice(name="AC", commands=(
            [_pronto_command("Sleep", extra_pronto)]
            if extra_pronto else []
        ))
        device.climate_matrix = True
        build = build_wig_from_device(device, self._matrix())
        return Wig(
            name="AC", wig_id="u-source", signals=build.wig.signals,
            climate=self._matrix(),
        )

    def test_a_stable_matrix_stays_update(self):
        """The checklist samples the lattice, and the lattice never
        lives in .signals -- every checklist row reads as unmatched
        against the wig on EVERY save, whether or not anything moved.
        Counting that as divergence would route every matrix save
        through SUCCESSION regardless of change; the amendment keeps
        matrix repairs proposing in place instead."""
        source_wig = self._matrix_source_wig(self._P_SLEEP)
        device = IRDevice(
            name="AC", commands=[_pronto_command("Sleep", self._P_SLEEP)],
            source_wig_id="u-source",
        )
        device.climate_matrix = True
        plan = build_save_plan(device, source_wig, "ac.wig.json", self._matrix())
        assert plan.variant == VARIANT_UPDATE
        assert plan.missing_rows == []

    def test_matrix_flat_addition_diverges(self):
        source_wig = self._matrix_source_wig(self._P_SLEEP)
        device = IRDevice(
            name="AC", commands=[
                _pronto_command("Sleep", self._P_SLEEP),
                _pronto_command("Timer", self._P_TIMER),
            ],
            source_wig_id="u-source",
        )
        device.climate_matrix = True
        plan = build_save_plan(device, source_wig, "ac.wig.json", self._matrix())
        assert plan.variant == VARIANT_SUCCESSION

    def test_matrix_flat_removal_diverges(self):
        source_wig = self._matrix_source_wig(self._P_SLEEP)
        device = IRDevice(name="AC", commands=[], source_wig_id="u-source")
        device.climate_matrix = True
        plan = build_save_plan(device, source_wig, "ac.wig.json", self._matrix())
        assert plan.variant == VARIANT_SUCCESSION
        assert [r.alias for r in plan.missing_rows] == ["Sleep"]

    def test_matrix_lattice_only_change_stays_update(self):
        """A repaired cell is lattice divergence, gated by cell_changes
        / propose_lattice on the UPDATE path -- not a reason to mint a
        successor. Flat extras are unchanged, so the verb stays UPDATE."""
        source_wig = self._matrix_source_wig(self._P_SLEEP)
        device = IRDevice(
            name="AC", commands=[_pronto_command("Sleep", self._P_SLEEP)],
            source_wig_id="u-source",
        )
        device.climate_matrix = True
        repaired = self._matrix()
        repaired.cells[0].pronto = self._P_REPAIRED
        plan = build_save_plan(device, source_wig, "ac.wig.json", repaired)
        assert plan.variant == VARIANT_UPDATE
        assert plan.cell_changes  # the repair is still reported, just not as a divergence


class TestTheSuccessorNameAutoDifferentiates:
    """Bench addendum ruling (2026-08-05). The bench produced three
    shelf wigs all named "Fable Ceiling Fan" -- a SUCCESSION save now
    prefills a distinguishing default instead: the source name plus a
    numeric suffix, counting past whatever is already on the shelf.
    UPDATE keeps the source name exactly as it always has."""

    def test_the_bare_name_needs_no_suffix_when_free(self):
        assert _differentiated_name("Fable Ceiling Fan", []) == (
            "Fable Ceiling Fan"
        )

    def test_one_collision_proposes_two(self):
        assert _differentiated_name(
            "Fable Ceiling Fan", ["Fable Ceiling Fan"],
        ) == "Fable Ceiling Fan (2)"

    def test_counts_past_an_existing_suffix_too(self):
        """A prior succession already claimed "(2)" -- the new default
        has to count past THAT, not just the bare name, or two
        successions in a row would propose the same name."""
        assert _differentiated_name(
            "Fable Ceiling Fan",
            ["Fable Ceiling Fan", "Fable Ceiling Fan (2)"],
        ) == "Fable Ceiling Fan (3)"

    def test_an_unrelated_name_never_collides(self):
        assert _differentiated_name(
            "Fable Ceiling Fan", ["Guest Room Lamp"],
        ) == "Fable Ceiling Fan"

    def test_a_succession_plan_prefills_the_differentiated_name(self):
        """Integration point: build_save_plan itself, not just the
        helper -- the ancestor is still on the shelf under the bare
        name at plan time (it is only superseded after the confirm
        resolves later), so existing_names is expected to already
        contain it, exactly as a real scan_wigs() would report.

        Second Fitting v3 punch list item 4 (owner ruling,
        2026-08-06): prefill differentiation is Save As New's alone
        now. A replace route -- and SUCCESSION, reached only through
        UPDATE CLOSET WIG or VALIDATE FOR PERFECT FIT, is always a
        replace route -- takes the ancestor's place on the shelf and
        inherits its name untouched. The differentiated default moves
        to ``suggested_new_name``, which Save As New's own dialog
        prefills from instead of ``plan.metadata["name"]``."""
        wig = Wig(
            name="Fable Ceiling Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        device = IRDevice(
            name="Fable Ceiling Fan", commands=[
                _pronto_command("On", PRONTO),
                _pronto_command("Turbo", PRONTO_B),
            ],
            source_wig_id="u-source",
        )
        plan = build_save_plan(
            device, wig, "fan.wig.json",
            existing_names=["Fable Ceiling Fan"],
        )
        assert plan.variant == VARIANT_SUCCESSION
        assert plan.metadata["name"] == "Fable Ceiling Fan"
        assert plan.suggested_new_name == "Fable Ceiling Fan (2)"

    def test_an_update_plan_keeps_the_source_name_exactly(self):
        """Same shelf, same collision -- but nothing diverged, so the
        verb is UPDATE and the addendum is explicit: UPDATE keeps the
        source name exactly as today, not a differentiated one."""
        wig = Wig(
            name="Fable Ceiling Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        device = IRDevice(
            name="Fable Ceiling Fan",
            commands=[_pronto_command("On", PRONTO)],
            source_wig_id="u-source",
        )
        plan = build_save_plan(
            device, wig, "fan.wig.json",
            existing_names=["Fable Ceiling Fan"],
        )
        assert plan.variant == VARIANT_UPDATE
        assert plan.metadata["name"] == "Fable Ceiling Fan"

    def test_no_existing_names_passed_falls_back_to_the_bare_name(self):
        """The default parameter is ``()`` -- a caller that forgets to
        pass the shelf (as most of this file's other tests do) still
        gets a real name back, just undifferentiated, rather than an
        error."""
        wig = Wig(
            name="Fable Ceiling Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        device = IRDevice(
            name="Fable Ceiling Fan", commands=[
                _pronto_command("On", PRONTO),
                _pronto_command("Turbo", PRONTO_B),
            ],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_SUCCESSION
        assert plan.metadata["name"] == "Fable Ceiling Fan"


def _attach_bundle(wig, handle, verdicts):
    digests = wig_row_digests(wig)
    bundle = ClaimsBundle(
        wig_id=wig.wig_id or "u-source",
        handle=handle,
        rows=[
            RowClaim(alias_at_claim="x", digest=d, verdict=v)
            for d, v in zip(digests, verdicts, strict=True)
        ],
    )
    existing = wig.extra.get("fittings")
    wig.extra["fittings"] = [
        *(existing if isinstance(existing, list) else []),
        claims_bundle_out(bundle),
    ]
    return wig


def _diverging_device(source_wig_id="u-source"):
    return IRDevice(
        name="Fan", commands=[
            _pronto_command("On", PRONTO),
            _pronto_command("Turbo", PRONTO_B),
        ],
        source_wig_id=source_wig_id,
    )


class TestTheOldFittingGrade:
    """Second Fitting v3, Commit 4: the Update dialog's inline warning
    renders BEFORE the click now, not after the save in a confirm --
    build_save_plan grades the source wig's own fitting history right
    on a diverged plan, the same claims_summary already grades for the
    self-supersession doorway's post-save confirm."""

    def test_a_diverged_plan_with_no_fittings_carries_no_state(self):
        """Present, but empty (RULED elsewhere: no claims is light --
        nothing extra renders). An absent object and a null-state one
        read identically to the dialog, but this way the shape never
        has to distinguish "no ancestor" from "an unfitted ancestor"."""
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        plan = build_save_plan(_diverging_device(), wig, "fan.wig.json")
        assert plan.variant == VARIANT_SUCCESSION
        assert plan.old_fitting_grade is not None
        assert plan.old_fitting_grade.state is None
        assert plan.old_fitting_grade.handles == []

    def test_a_complete_claim_grades_perfect_and_names_the_handle(self):
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        _attach_bundle(wig, "David", [VERDICT_WORKED])
        plan = build_save_plan(_diverging_device(), wig, "fan.wig.json")
        assert plan.old_fitting_grade.state == "perfect"
        assert plan.old_fitting_grade.count == 1
        assert plan.old_fitting_grade.handles == ["David"]

    def test_a_partial_claim_grades_scoped(self):
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[
                WigSignal(alias="On", pronto=PRONTO),
                WigSignal(alias="Off", pronto=PRONTO_C),
            ],
        )
        _attach_bundle(wig, "David", [VERDICT_WORKED, "not_on_device"])
        device = IRDevice(
            name="Fan", commands=[
                _pronto_command("On", PRONTO),
                _pronto_command("Off", PRONTO_C),
                _pronto_command("Turbo", PRONTO_B),
            ],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_SUCCESSION
        assert plan.old_fitting_grade.state == "scoped"
        assert plan.old_fitting_grade.count == 1

    def test_handles_are_deduped_first_seen_order(self):
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        _attach_bundle(wig, "David", [VERDICT_WORKED])
        _attach_bundle(wig, "Robin", ["not_on_device"])
        _attach_bundle(wig, "David", [VERDICT_WORKED])
        plan = build_save_plan(_diverging_device(), wig, "fan.wig.json")
        # Three bundles, two unique handles: the count is fitting
        # bundles (matching supersede.fitted_scoped's own plural key),
        # the handle list is deduped for the "by {who}" text.
        assert plan.old_fitting_grade.count == 3
        assert plan.old_fitting_grade.handles == ["David", "Robin"]

    def test_a_matching_plan_carries_no_grade(self):
        """Nothing is about to be retired on a plain UPDATE -- the
        field stays None entirely, not an empty-state object."""
        wig = Wig(
            name="Fan", wig_id="u-source",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
        )
        _attach_bundle(wig, "David", [VERDICT_WORKED])
        device = IRDevice(
            name="Fan", commands=[_pronto_command("On", PRONTO)],
            source_wig_id="u-source",
        )
        plan = build_save_plan(device, wig, "fan.wig.json")
        assert plan.variant == VARIANT_UPDATE
        assert plan.old_fitting_grade is None

    def test_a_from_scratch_plan_carries_no_grade(self):
        device = IRDevice(name="Fan", commands=[_pronto_command("On", PRONTO)])
        plan = build_save_plan(device)
        assert plan.variant == VARIANT_CREATE
        assert plan.old_fitting_grade is None
