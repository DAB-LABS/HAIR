"""The claims model, and the contract external verifiers reproduce.

The row digest is a portability deliverable, not an implementation
detail: WigFactory and any third-party verifier must be able to compute
it from the spec in docs/wig-format.md alone. So it gets GOLDEN
VECTORS -- literal expected values, not round-trips. A round-trip test
would happily pass while the whole scheme drifted, because both sides
of it would drift together.
"""
from __future__ import annotations

import hashlib

import pytest

from custom_components.hair.wig_format import (
    EXCLUSION_REASONS,
    VERDICT_NOT_ON_DEVICE,
    VERDICT_WONT_WORK,
    VERDICT_WORKED,
    ClaimsBundle,
    RowClaim,
    Wig,
    WigSignal,
    claims_bundle_out,
    claims_of,
    coverage,
    drop_legacy_fittings,
    is_claims_bundle,
    is_legacy_fitting,
    new_wig_id,
    normalized_pronto,
    parse_claims_bundle,
    perfect_by,
    row_digest,
    serialize_wig,
    signal_row_digest,
    wig_row_digests,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


def _expected(pronto: str, ditto: int, bypass: bool) -> str:
    """The spec, computed independently of the implementation."""
    recipe = f"{normalized_pronto(pronto)}|d{ditto}|b{1 if bypass else 0}"
    return hashlib.sha256(recipe.encode("utf-8")).hexdigest()[:16]


class TestRowDigestGoldenVectors:
    """sha256(normalized_pronto + "|d<ditto>" + "|b<0|1>")[:16]."""

    def test_the_plain_case(self):
        assert row_digest(PRONTO) == _expected(PRONTO, 0, False)

    def test_it_is_sixteen_hex_characters(self):
        digest = row_digest(PRONTO)
        assert len(digest) == 16
        assert all(c in "0123456789abcdef" for c in digest)

    @pytest.mark.parametrize("ditto", [0, 1, 2, 20])
    def test_every_ditto_value_moves_it(self, ditto):
        assert row_digest(PRONTO, ditto) == _expected(PRONTO, ditto, False)

    def test_bypass_moves_it(self):
        assert row_digest(PRONTO, 0, True) == _expected(PRONTO, 0, True)
        assert row_digest(PRONTO, 0, True) != row_digest(PRONTO, 0, False)

    def test_ditto_and_bypass_are_independent_axes(self):
        seen = {
            row_digest(PRONTO, d, b)
            for d in (0, 1, 2)
            for b in (False, True)
        }
        assert len(seen) == 6

    def test_whitespace_and_case_do_not_move_it(self):
        """Normalization is part of the contract: the same code typed
        differently is the same code."""
        assert row_digest(PRONTO) == row_digest(PRONTO.lower())
        assert row_digest(PRONTO) == row_digest(f"  {PRONTO}  ")


class TestWhatTheDigestDeliberatelyIgnores:
    """Two exclusions that must never be reversed. Both are load-
    bearing for the whole model: a claim has to survive a rename, and
    two people in different rooms have to be proving the same wig."""

    def test_alias_is_out(self):
        a = WigSignal(alias="On", pronto=PRONTO)
        b = WigSignal(alias="Power", pronto=PRONTO)
        assert signal_row_digest(a) == signal_row_digest(b)

    def test_send_count_is_out(self):
        a = WigSignal(alias="On", pronto=PRONTO, send_count=1)
        b = WigSignal(alias="On", pronto=PRONTO, send_count=10)
        assert signal_row_digest(a) == signal_row_digest(b)

    def test_but_ditto_is_in(self):
        a = WigSignal(alias="On", pronto=PRONTO, ditto_count=0)
        b = WigSignal(alias="On", pronto=PRONTO, ditto_count=1)
        assert signal_row_digest(a) != signal_row_digest(b)

    def test_and_bypass_is_in(self):
        a = WigSignal(alias="On", pronto=PRONTO, bypass_protocol=False)
        b = WigSignal(alias="On", pronto=PRONTO, bypass_protocol=True)
        assert signal_row_digest(a) != signal_row_digest(b)


LEGACY_FITTING = {
    "handle": "David",
    "date": "2026-08-02",
    "content_hash": "sha256:abc",
    "confirmed": ["On"],
    "failed": [],
    "send_times_used": 3,
    "key": "k",
    "sig": "s",
}
NEW_BUNDLE = {
    "wig_id": "u-1",
    "rows": [
        {"alias_at_claim": "On", "digest": "d1", "verdict": "worked"},
    ],
    "handle": "David",
    "key": "k",
    "sig": "s",
}
NEW_MATRIX_BUNDLE = {**NEW_BUNDLE, "cells_hash": "sha256:def"}


class TestTheDiscriminator:
    """Hard rule 6. Keys on the SHAPE of the entry, never the file's
    major, because this branch itself wrote /3 files carrying old
    whole-wig fittings before the claims model landed."""

    def test_legacy_is_recognized(self):
        assert is_legacy_fitting(LEGACY_FITTING)
        assert not is_claims_bundle(LEGACY_FITTING)

    def test_a_claims_bundle_is_not_legacy(self):
        assert not is_legacy_fitting(NEW_BUNDLE)
        assert is_claims_bundle(NEW_BUNDLE)

    def test_a_new_matrix_bundle_is_NOT_dropped_by_the_legacy_path(self):
        """The pinned guard (hard rule 6). A matrix bundle binds a
        lattice hash too, and if that field had reused the old name
        this test would fail -- which is exactly why it is called
        cells_hash."""
        assert not is_legacy_fitting(NEW_MATRIX_BUNDLE)
        assert is_claims_bundle(NEW_MATRIX_BUNDLE)
        assert parse_claims_bundle(NEW_MATRIX_BUNDLE) is not None

    def test_the_matrix_binding_never_uses_the_old_name(self):
        bundle = parse_claims_bundle(NEW_MATRIX_BUNDLE)
        out = claims_bundle_out(bundle)
        assert out["cells_hash"] == "sha256:def"
        assert "content_hash" not in out

    def test_the_interim_v3_shape_still_drops(self):
        """A /3 file this branch wrote before claims existed. The
        stamp says 3; the block is legacy; shape wins."""
        wig = Wig(name="W", signals=[WigSignal(alias="On", pronto=PRONTO)])
        wig.extra["fittings"] = [dict(LEGACY_FITTING)]
        assert drop_legacy_fittings(wig) == 1
        assert "fittings" not in wig.extra

    def test_a_mixed_list_keeps_only_the_claims(self):
        wig = Wig(name="W", signals=[WigSignal(alias="On", pronto=PRONTO)])
        wig.extra["fittings"] = [dict(LEGACY_FITTING), dict(NEW_BUNDLE)]
        assert drop_legacy_fittings(wig) == 1
        assert wig.extra["fittings"] == [NEW_BUNDLE]

    def test_nothing_to_drop_is_not_an_error(self):
        wig = Wig(name="W", signals=[])
        assert drop_legacy_fittings(wig) == 0


class TestBundleRoundTrip:
    def test_parse_then_serialize_is_stable(self):
        raw = {
            "wig_id": "u-1",
            "handle": "David",
            "github": "DAB-LABS",
            "date": "2026-08-02",
            "note": "bench",
            "rows": [
                {
                    "alias_at_claim": "On",
                    "digest": "abc",
                    "verdict": VERDICT_WORKED,
                },
            ],
            "key": "k",
            "sig": "s",
        }
        assert claims_bundle_out(parse_claims_bundle(raw)) == raw

    def test_unknown_fields_survive(self):
        """A bundle from a newer HAIR must round-trip intact, or this
        install silently breaks the signature covering those fields."""
        raw = {
            "wig_id": "u-1",
            "rows": [],
            "future_field": {"nested": 1},
            "sig": "s",
        }
        out = claims_bundle_out(parse_claims_bundle(raw))
        assert out["future_field"] == {"nested": 1}

    def test_an_unknown_verdict_is_refused_not_guessed(self):
        raw = {
            "wig_id": "u-1",
            "rows": [
                {"alias_at_claim": "On", "digest": "d", "verdict": "maybe"},
            ],
        }
        assert parse_claims_bundle(raw).rows == []

    def test_a_bundle_with_no_wig_id_is_not_a_bundle(self):
        assert parse_claims_bundle({"rows": []}) is None


class TestDerivedFacts:
    """Perfect fit and coverage are computed, never stored, so the
    file cannot disagree with itself after an edit."""

    def _wig(self):
        return Wig(name="W", signals=[
            WigSignal(alias="On", pronto=PRONTO),
            WigSignal(alias="Off", pronto=PRONTO, ditto_count=1),
        ])

    def _bundle(self, wig, verdicts):
        digests = wig_row_digests(wig)
        return ClaimsBundle(
            wig_id="u-1",
            rows=[
                RowClaim(alias_at_claim="x", digest=d, verdict=v)
                for d, v in zip(digests, verdicts, strict=True)
            ],
        )

    def test_all_worked_is_a_perfect_fit(self):
        wig = self._wig()
        bundle = self._bundle(wig, [VERDICT_WORKED, VERDICT_WORKED])
        assert perfect_by(bundle, wig_row_digests(wig))

    @pytest.mark.parametrize("reason", EXCLUSION_REASONS)
    def test_any_exclusion_is_not_perfect(self, reason):
        wig = self._wig()
        bundle = self._bundle(wig, [VERDICT_WORKED, reason])
        assert not perfect_by(bundle, wig_row_digests(wig))

    def test_editing_a_row_orphans_only_that_row(self):
        """The whole point of per-row claims. Under the old model this
        invalidated the entire fitting."""
        wig = self._wig()
        bundle = self._bundle(wig, [VERDICT_WORKED, VERDICT_WORKED])
        wig.signals[1].ditto_count = 5
        after = wig_row_digests(wig)
        assert not perfect_by(bundle, after)
        # The untouched row's claim survives intact.
        assert coverage([bundle], after) == {after[0]}

    def test_coverage_is_the_union_across_fitters(self):
        wig = self._wig()
        a = self._bundle(wig, [VERDICT_WORKED, VERDICT_WONT_WORK])
        b = self._bundle(wig, [VERDICT_NOT_ON_DEVICE, VERDICT_WORKED])
        digests = wig_row_digests(wig)
        assert coverage([a, b], digests) == set(digests)
        assert not perfect_by(a, digests)
        assert not perfect_by(b, digests)

    def test_a_matrix_wig_has_no_flat_row_digests(self):
        from custom_components.hair.wig_format import (
            ClimateCell,
            ClimateMatrix,
        )
        wig = Wig(name="AC", signals=[], climate=ClimateMatrix(
            min_temp=16.0, max_temp=30.0, off=PRONTO,
            cells=[ClimateCell(mode="cool", temp=20.0, pronto=PRONTO)],
        ))
        assert wig_row_digests(wig) == []


class TestWigIdentity:
    def test_minted_ids_are_unique(self):
        assert new_wig_id() != new_wig_id()

    def test_identity_survives_a_round_trip(self):
        from custom_components.hair.wig_format import parse_wig
        wig = Wig(
            name="W",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
            wig_id="fixed-id",
        )
        again = parse_wig(serialize_wig(wig)).wig
        assert again.wig_id == "fixed-id"

    def test_identity_is_in_no_digest(self):
        """A wig's identity must survive every edit to its contents,
        which is exactly why it replaced the content hash in that
        role."""
        a = WigSignal(alias="On", pronto=PRONTO)
        before = signal_row_digest(a)
        wig = Wig(name="W", signals=[a], wig_id="anything-at-all")
        assert wig_row_digests(wig) == [before]

    def test_claims_of_skips_legacy(self):
        wig = Wig(name="W", signals=[])
        wig.extra["fittings"] = [
            LEGACY_FITTING,
            NEW_BUNDLE,
        ]
        bundles = claims_of(wig)
        assert len(bundles) == 1
        assert bundles[0].wig_id == "u-1"


class TestIdentityIsMintedAtTheChokePoint:
    """Eight constructors across five modules build wigs. Requiring
    each to remember an id would guarantee one eventually did not, so
    serialize_wig -- the one path to becoming a file -- mints it."""

    def test_serializing_mints_an_id(self):
        wig = Wig(name="W", signals=[WigSignal(alias="On", pronto=PRONTO)])
        assert wig.wig_id is None
        serialize_wig(wig)
        assert wig.wig_id

    def test_the_id_is_stable_across_saves(self):
        """The mutation is deliberate. Minting into the output dict
        alone would leave the wig without an id and the next save
        would mint a different one -- identity changing on every
        write, the exact opposite of the point."""
        wig = Wig(name="W", signals=[WigSignal(alias="On", pronto=PRONTO)])
        serialize_wig(wig)
        first = wig.wig_id
        serialize_wig(wig)
        assert wig.wig_id == first

    def test_an_existing_id_is_never_replaced(self):
        wig = Wig(
            name="W",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
            wig_id="came-from-the-shop",
        )
        serialize_wig(wig)
        assert wig.wig_id == "came-from-the-shop"

    def test_provenance_round_trips(self):
        from custom_components.hair.wig_format import parse_wig
        wig = Wig(
            name="W",
            signals=[WigSignal(alias="On", pronto=PRONTO)],
            converted_from="living-room.json",
            converted_from_sha256="sha256:abc",
        )
        again = parse_wig(serialize_wig(wig)).wig
        assert again.converted_from == "living-room.json"
        assert again.converted_from_sha256 == "sha256:abc"


class TestDeviceRemembersItsSource:
    """SAVE TO CLOSET decides between UPDATE and CREATE from what the
    device remembers. Getting this wrong mints a second copy of a wig
    the closet already holds."""

    def test_the_source_round_trips(self):
        from custom_components.hair.models import IRDevice
        device = IRDevice(name="TV", source_wig_id="u-1")
        again = IRDevice.from_dict(device.to_dict())
        assert again.source_wig_id == "u-1"

    def test_a_device_built_from_scratch_has_none(self):
        from custom_components.hair.models import IRDevice
        assert IRDevice(name="TV").source_wig_id is None

    def test_pre_095_devices_read_as_built_from_scratch(self):
        """Absent on every device made before this release, which is
        the truth about them."""
        from custom_components.hair.models import IRDevice
        old = {"id": "d1", "name": "TV", "device_type": "media_player"}
        device = IRDevice.from_dict(old)
        assert device.source_wig_id is None
        assert device.source_file is None


class TestBackfillingClosetIdentity:
    """A wig already in the closet never passed through upload, so it
    has no id. Minting only in memory would be worse than not minting:
    the device would carry an id the file does not."""

    def _closet(self, tmp_path, text: str, name="old.wig.json"):
        from custom_components.hair.wig_store import ensure_wigs_dir
        directory = ensure_wigs_dir(tmp_path)
        (directory / name).write_text(text, encoding="utf-8")
        return name

    def test_it_mints_and_persists(self, tmp_path):
        import json

        from custom_components.hair.wig_store import (
            backfill_wig_id,
            load_wig,
        )
        raw = json.dumps({
            "format": "hair-wig/1",
            "name": "Old",
            "signals": [{"alias": "On", "pronto": PRONTO}],
        })
        name = self._closet(tmp_path, raw)
        assert load_wig(tmp_path, name).wig_id is None

        minted = backfill_wig_id(tmp_path, name)
        assert minted
        # The FILE has it now, not just the object we handed back.
        assert load_wig(tmp_path, name).wig_id == minted

    def test_it_is_idempotent(self, tmp_path):
        import json

        from custom_components.hair.wig_store import backfill_wig_id
        raw = json.dumps({
            "format": "hair-wig/3",
            "name": "Known",
            "wig_id": "already-mine",
            "signals": [{"alias": "On", "pronto": PRONTO}],
        })
        name = self._closet(tmp_path, raw, "known.wig.json")
        assert backfill_wig_id(tmp_path, name) == "already-mine"
        assert backfill_wig_id(tmp_path, name) == "already-mine"

    def test_an_unloadable_file_is_not_an_error(self, tmp_path):
        from custom_components.hair.wig_store import backfill_wig_id
        assert backfill_wig_id(tmp_path, "nope.wig.json") is None
