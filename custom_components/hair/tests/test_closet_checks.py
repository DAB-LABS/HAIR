"""The closet row's check: perfect or nothing, derived from claims.

One-to-one with the download filename tiers, because a row and a
filename saying different things about the same wig is a contradiction
somebody has to open the file to resolve. The three-tier "scoped"
middle retired 2026-08-07 (owner ruling): a wig is a PERFECT FIT or the
row shows nothing, and an incomplete bundle -- old files with
exclusions from before the ruling, or a matrix carrying them today --
still parses, still counts toward ``fitters``/``covered``, and still
lists in the ledger. It just is not a tier the closet tick names.

The load-bearing rule is that GREEN IS ONE PERSON'S COMPLETE COVERAGE.
Three people who each proved a different third have not, between them,
produced anybody who can say the whole wig works on their hardware --
so the union is tooltip material, never the colour.
"""
from __future__ import annotations

from custom_components.hair.wig_comb import comb_wig, stamp_receipt
from custom_components.hair.wig_fitting import claims_summary
from custom_components.hair.wig_format import (
    VERDICT_NOT_ON_DEVICE,
    VERDICT_WORKED,
    ClaimsBundle,
    RowClaim,
    Wig,
    WigSignal,
    wig_row_digests,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"
PRONTO_C = "0000 006D 0004 0000 0020 0040 0020 0040 0030 0020 0020 0040"

# Second Fitting v3 punch list item 8: "yours" is a key comparison
# now, not a typed-handle-vs-username one -- these stand in for the
# install's own public key and somebody else's.
INSTALL_KEY = "install-key-aaaaaaaaaaaaaaaa"
OTHER_KEY = "other-key-bbbbbbbbbbbbbbbbbbb"


def _wig():
    return Wig(name="TV", wig_id="u-1", signals=[
        WigSignal(alias="On", pronto=PRONTO_A),
        WigSignal(alias="Off", pronto=PRONTO_B),
    ])


def _bundle(wig, verdicts, handle="David", key=None):
    digests = wig_row_digests(wig)
    return ClaimsBundle(
        wig_id=wig.wig_id or "u-1",
        handle=handle,
        key=key,
        rows=[
            RowClaim(alias_at_claim="x", digest=d, verdict=v)
            for d, v in zip(digests, verdicts, strict=True)
        ],
    )


def _attach(wig, *bundles):
    from custom_components.hair.wig_format import claims_bundle_out

    wig.extra["fittings"] = [claims_bundle_out(b) for b in bundles]
    return wig


class TestTheTwoTiers:
    def test_no_attestations_shows_nothing(self):
        assert claims_summary(_wig(), None)["state"] is None

    def test_an_incomplete_attestation_shows_nothing(self):
        """Perfect or nothing (owner ruling 2026-08-07): a complete,
        signed, honest attestation that carries exclusions is real and
        stays in the ledger, but it is no longer a tier the closet tick
        names -- it reads exactly like no attestation at all here."""
        wig = _wig()
        _attach(wig, _bundle(wig, [VERDICT_WORKED, VERDICT_NOT_ON_DEVICE]))
        summary = claims_summary(wig, None)
        assert summary["state"] is None
        # Still counted -- display of history is not judgment.
        assert summary["fitters"] == 1
        assert summary["covered"] == 1

    def test_a_perfect_fit_turns_it_green(self):
        wig = _wig()
        _attach(wig, _bundle(wig, [VERDICT_WORKED, VERDICT_WORKED]))
        summary = claims_summary(wig, None)
        assert summary["state"] == "perfect"
        assert summary["perfect_by"] == ["David"]

    def test_adding_a_perfect_fit_promotes_an_incomplete_wig(self):
        wig = _wig()
        partial = _bundle(wig, [VERDICT_WORKED, VERDICT_NOT_ON_DEVICE], "Ann")
        _attach(wig, partial)
        assert claims_summary(wig, None)["state"] is None
        _attach(wig, partial, _bundle(wig, [VERDICT_WORKED, VERDICT_WORKED]))
        assert claims_summary(wig, None)["state"] == "perfect"

    def test_union_coverage_never_inflates_the_check(self):
        """THE ONE THAT MATTERS. Two fitters who each proved a
        different half cover the wig between them, and neither can say
        the whole thing works on their own hardware. That is no tick,
        with the union in the tooltip.
        """
        wig = _wig()
        _attach(
            wig,
            _bundle(wig, [VERDICT_WORKED, VERDICT_NOT_ON_DEVICE], "Ann"),
            _bundle(wig, [VERDICT_NOT_ON_DEVICE, VERDICT_WORKED], "Bo"),
        )
        summary = claims_summary(wig, None)
        assert summary["state"] is None
        # The union IS reported -- it is real, it just is not the check.
        assert summary["covered"] == 2
        assert summary["total"] == 2
        assert summary["fitters"] == 2

    def test_it_knows_which_fitting_is_yours(self):
        """Second Fitting v3 punch list item 8: keyed on the install's
        public signing key, not the typed handle against the HA
        username."""
        wig = _wig()
        _attach(
            wig,
            _bundle(
                wig, [VERDICT_WORKED, VERDICT_WORKED], "Ann", key=OTHER_KEY,
            ),
            _bundle(
                wig, [VERDICT_WORKED, VERDICT_NOT_ON_DEVICE], "David",
                key=INSTALL_KEY,
            ),
        )
        assert claims_summary(wig, INSTALL_KEY)["user_state"] is None
        assert claims_summary(wig, OTHER_KEY)["user_state"] == "perfect"

    def test_a_matching_handle_with_a_different_key_is_not_yours(self):
        """The regression item 8 fixes directly: a bundle whose typed
        handle happens to equal the reader's HA username must not read
        as theirs when the signing key says otherwise."""
        wig = _wig()
        _attach(
            wig,
            _bundle(
                wig, [VERDICT_WORKED, VERDICT_WORKED], "David", key=OTHER_KEY,
            ),
        )
        assert claims_summary(wig, INSTALL_KEY)["user_state"] is None


class TestTheCombStaysIndependent:
    """A different glyph making a different statement about different
    evidence. A wig can honestly wear a green check and a glowing comb
    at once -- someone proved it on their hardware and the bytes still
    look odd. That is information, not contradiction."""

    def _doubted(self):
        wig = Wig(name="TV", wig_id="u-1", signals=[
            WigSignal(alias="On", pronto=PRONTO_A),
            WigSignal(alias="Off", pronto=PRONTO_A),
            WigSignal(alias="Mute", pronto=PRONTO_A),
            WigSignal(alias="Sleep", pronto=PRONTO_C),
        ])
        stamp_receipt(wig, comb_wig(wig), "2026-08-03")
        return wig

    def test_a_green_check_and_a_glowing_comb_coexist(self):
        wig = self._doubted()
        digests = wig_row_digests(wig)
        _attach(wig, ClaimsBundle(
            wig_id="u-1", handle="David",
            rows=[
                RowClaim(alias_at_claim="x", digest=d, verdict=VERDICT_WORKED)
                for d in digests
            ],
        ))
        from custom_components.hair.wig_comb import receipt_summary

        assert claims_summary(wig, None)["state"] == "perfect"
        assert receipt_summary(wig)["suspects"] > 0

    def test_attesting_never_clears_the_comb(self):
        """Only fixed bytes do. The comb doubts bytes, a person vouches
        for hardware, and neither silences the other."""
        wig = self._doubted()
        before = comb_wig(wig).suspects
        digests = wig_row_digests(wig)
        _attach(wig, ClaimsBundle(
            wig_id="u-1", handle="David",
            rows=[
                RowClaim(alias_at_claim="x", digest=d, verdict=VERDICT_WORKED)
                for d in digests
            ],
        ))
        assert comb_wig(wig).suspects == before
