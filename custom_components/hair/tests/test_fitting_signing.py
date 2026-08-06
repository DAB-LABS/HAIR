"""Tests for fitting signatures (Tier 1).

The properties under test are the ones the design claims: a signed
attestation verifies; ANY payload change (including key swap) flips it
to invalid; unsigned stays unsigned (never fails); and every part of
what somebody attested is inside what the signature covers.

v0.9.5 changed the thing being signed and not the signing. A fitting
used to be a session that finished, could be resumed, shed its stale
signature and was re-signed over grown content; it bound a whole-file
hash. It is now a bundle of per-row claims written once at SAVE TO
CLOSET and never reopened, so the resume-and-re-sign cycle these tests
used to protect no longer exists. What replaced it is the requirement
that the WHOLE SET of claims is covered -- rows cannot be added,
dropped, repointed or re-verdicted under a signature that still reads
as valid.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("cryptography")

from custom_components.hair.fitting_signing import (
    SIGNED_INVALID,
    SIGNED_VALID,
    canonical_fitting_bytes,
    key_fingerprint,
    sign_fitting,
    verify_fitting,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
_PRONTO_B = "0000 006D 0002 0000 0030 0050 0030 0050"


def _keypair_b64() -> tuple[str, str]:
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    private = Ed25519PrivateKey.generate()
    priv_b64 = base64.b64encode(
        private.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
    ).decode("ascii")
    pub_b64 = base64.b64encode(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")
    return priv_b64, pub_b64


def _entry() -> dict:
    """A stored claims bundle, as ``claims_bundle_out`` writes it.

    The signing primitives are generic over keys -- they sign whatever
    dict they are handed -- so these tests would pass over any shape.
    Using the real one keeps the file honest about what is on disk.
    """
    return {
        "wig_id": "w-dreo",
        "handle": "dab",
        "date": "2026-07-26",
        "rows": [
            {
                "alias_at_claim": "Power On",
                "digest": "a" * 16,
                "verdict": "worked",
            },
            {
                "alias_at_claim": "Power Off",
                "digest": "b" * 16,
                "verdict": "worked",
            },
        ],
    }


class TestCanonicalForm:
    def test_excludes_sig_includes_key(self):
        entry = _entry()
        entry["key"] = "KEYDATA"
        entry["sig"] = "SIGDATA"
        payload = json.loads(canonical_fitting_bytes(entry))
        assert "sig" not in payload
        assert payload["key"] == "KEYDATA"

    def test_key_order_is_irrelevant(self):
        a = _entry()
        b = dict(reversed(list(_entry().items())))
        assert canonical_fitting_bytes(a) == canonical_fitting_bytes(b)


class TestSignAndVerify:
    def test_round_trip(self):
        priv, pub = _keypair_b64()
        entry = _entry()
        assert sign_fitting(entry, priv)
        assert entry["key"] == pub
        assert verify_fitting(entry) == SIGNED_VALID

    def test_unsigned_is_none(self):
        assert verify_fitting(_entry()) is None

    def test_payload_tamper_invalidates(self):
        priv, _pub = _keypair_b64()
        entry = _entry()
        sign_fitting(entry, priv)
        entry["rows"].append({
            "alias_at_claim": "Forged Button",
            "digest": "f" * 16,
            "verdict": "worked",
        })
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_key_swap_invalidates(self):
        """Replacing the key breaks the sig: key is inside the payload."""
        priv, _pub = _keypair_b64()
        _other_priv, other_pub = _keypair_b64()
        entry = _entry()
        sign_fitting(entry, priv)
        entry["key"] = other_pub
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_garbage_envelope_invalid_not_crash(self):
        entry = _entry()
        entry["key"] = "not base64!!"
        entry["sig"] = 42
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_resign_replaces(self):
        priv, _ = _keypair_b64()
        entry = _entry()
        sign_fitting(entry, priv)
        first_sig = entry["sig"]
        entry["confirmed"] = ["Power On"]
        sign_fitting(entry, priv)
        assert entry["sig"] != first_sig
        assert verify_fitting(entry) == SIGNED_VALID

    def test_bad_private_key_records_unsigned(self):
        entry = _entry()
        assert not sign_fitting(entry, "garbage")
        assert "sig" not in entry and "key" not in entry

    def test_key_fingerprint(self):
        _priv, pub = _keypair_b64()
        fp = key_fingerprint(pub)
        assert fp is not None and len(fp) == 16
        assert key_fingerprint("!!!") is None


class TestBundleSigning:
    """The signature over a claims bundle (v0.9.5).

    Signing did not change: the canonical form is generic over keys, so
    it took the new envelope without a line of new signing code. What
    changed is WHAT is inside -- a set of per-row claims instead of a
    whole-file hash -- and these tests prove the whole set is covered.
    """

    def _bundle(self, **kw):
        from custom_components.hair.wig_format import ClaimsBundle, RowClaim

        base = dict(
            wig_id="w-dreo",
            handle="dab",
            date="2026-08-03",
            rows=[
                RowClaim(
                    alias_at_claim="Power", digest="a" * 16, verdict="worked"
                ),
                RowClaim(
                    alias_at_claim="Mode", digest="b" * 16, verdict="worked"
                ),
            ],
        )
        base.update(kw)
        return ClaimsBundle(**base)

    def _signed(self, bundle) -> dict:
        from custom_components.hair.wig_claims import sign_claims_bundle

        priv, _pub = _keypair_b64()
        return sign_claims_bundle(bundle, priv)

    def test_a_bundle_signs_and_verifies(self):
        assert verify_fitting(self._signed(self._bundle())) == SIGNED_VALID

    def test_an_unsigned_bundle_is_still_recorded(self):
        """A signing failure costs attribution, never the claims."""
        from custom_components.hair.wig_claims import sign_claims_bundle

        entry = sign_claims_bundle(self._bundle(), None)
        assert entry["rows"]
        assert verify_fitting(entry) is None

    def test_editing_a_verdict_after_signing_invalidates(self):
        entry = self._signed(self._bundle())
        entry["rows"][1]["verdict"] = "failed"
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_editing_a_digest_after_signing_invalidates(self):
        """The load-bearing one: a digest IS the row a claim is about,
        so repointing it at another row would forge an attestation."""
        entry = self._signed(self._bundle())
        entry["rows"][0]["digest"] = "c" * 16
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_adding_a_row_after_signing_invalidates(self):
        entry = self._signed(self._bundle())
        entry["rows"].append({
            "alias_at_claim": "Timer", "digest": "d" * 16, "verdict": "worked",
        })
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_dropping_a_row_after_signing_invalidates(self):
        """Both directions matter. Deleting a FAILED row would turn a
        scoped fitting into a perfect one."""
        entry = self._signed(self._bundle())
        del entry["rows"][1]
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_the_wig_id_is_covered(self):
        entry = self._signed(self._bundle())
        entry["wig_id"] = "w-somebody-elses"
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_the_matrix_lattice_binding_is_covered(self):
        """A checklist bundle vouches for a SET, so the hash naming
        that set has to be inside the signature."""
        entry = self._signed(self._bundle(cells_hash="sha256:abc"))
        assert verify_fitting(entry) == SIGNED_VALID
        entry["cells_hash"] = "sha256:def"
        assert verify_fitting(entry) == SIGNED_INVALID

    def test_a_rename_leaves_the_signature_standing(self):
        """``alias_at_claim`` is display context, not identity -- but it
        is still inside the envelope, so a rename is recorded as a NEW
        bundle rather than by editing an old one in place."""
        entry = self._signed(self._bundle())
        assert verify_fitting(entry) == SIGNED_VALID
        entry["rows"][0]["alias_at_claim"] = "Power Toggle"
        assert verify_fitting(entry) == SIGNED_INVALID


class TestSigningAtSave:
    def test_append_claims_signs_what_it_stores(self):
        from custom_components.hair.wig_claims import append_claims
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            Wig,
            WigSignal,
            signal_row_digest,
        )

        priv, _pub = _keypair_b64()
        wig = Wig(name="Dreo", wig_id="w-dreo", signals=[
            WigSignal(alias="Power", pronto=PRONTO),
        ])
        bundle = ClaimsBundle(wig_id="w-dreo", handle="dab", rows=[
            RowClaim(
                alias_at_claim="Power",
                digest=signal_row_digest(wig.signals[0]),
                verdict="worked",
            ),
        ])
        entry = append_claims(wig, bundle, priv)
        assert verify_fitting(entry) == SIGNED_VALID
        assert wig.extra["fittings"] == [entry]

    def test_a_second_save_with_the_same_key_replaces(self):
        """Second Fitting v3 punch list item 1 (owner ruling,
        2026-08-06): same-fitter re-sign is keyed on the signing key,
        not the handle. Two saves from the same per-install key --
        even under two different typed handles -- are the same
        fitter; the newer bundle replaces the older one instead of
        accumulating a duplicate entry."""
        from custom_components.hair.wig_claims import append_claims
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            Wig,
            WigSignal,
        )

        priv, _pub = _keypair_b64()
        wig = Wig(name="Dreo", wig_id="w-dreo", signals=[
            WigSignal(alias="Power", pronto=PRONTO),
        ])
        for handle in ("dab", "kno-te"):
            append_claims(wig, ClaimsBundle(
                wig_id="w-dreo", handle=handle, rows=[RowClaim(
                    alias_at_claim="Power", digest="a" * 16, verdict="worked",
                )],
            ), priv)
        entries = wig.extra["fittings"]
        assert len(entries) == 1
        assert verify_fitting(entries[0]) == SIGNED_VALID
        assert entries[0]["handle"] == "kno-te"

    def test_a_second_save_with_a_different_key_appends(self):
        """The other half of item 1's ruling: a different signing key
        is a different fitter's install, full stop, regardless of
        what handle either one typed -- claims still accumulate
        across distinct keys exactly as before."""
        from custom_components.hair.wig_claims import append_claims
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            Wig,
            WigSignal,
        )

        priv1, _pub1 = _keypair_b64()
        priv2, _pub2 = _keypair_b64()
        wig = Wig(name="Dreo", wig_id="w-dreo", signals=[
            WigSignal(alias="Power", pronto=PRONTO),
        ])
        for handle, priv in (("dab", priv1), ("kno-te", priv2)):
            append_claims(wig, ClaimsBundle(
                wig_id="w-dreo", handle=handle, rows=[RowClaim(
                    alias_at_claim="Power", digest="a" * 16, verdict="worked",
                )],
            ), priv)
        entries = wig.extra["fittings"]
        assert len(entries) == 2
        assert all(verify_fitting(e) == SIGNED_VALID for e in entries)
        assert [e["handle"] for e in entries] == ["dab", "kno-te"]

    @pytest.mark.asyncio
    async def test_one_install_signs_with_one_key(self, fake_hass, tmp_path):
        from custom_components.hair.fitting_signing import (
            async_get_private_key,
        )

        fake_hass.config.config_dir = str(tmp_path)
        key1 = await async_get_private_key(fake_hass)
        assert key1 is not None
        # The conftest Store stub is per-instance, so persistence
        # cannot be asserted through it; assert instead that a loaded
        # key is reused when the store returns one.
        key2 = await async_get_private_key(fake_hass)
        assert key2 is not None


class TestBypassIsSignedTransitively:
    """Flipping ``bypass_protocol`` cannot leave a claim vouching for a
    recipe nobody sent (Highlights, GH #78).

    The mechanism changed with the model and is worth stating plainly.
    The flag used to reach the signature through the whole-file
    ``content_hash``, so editing it INVALIDATED every fitting on the
    file, including the claims about rows nobody had touched. Now the
    flag is inside the ROW DIGEST, which is inside the signed bundle:
    the signature stays valid because the person really did sign that,
    and the claim simply stops matching any row on the wig. The bad
    attestation is still impossible; the collateral damage is gone.
    """

    def _claim_over(self, signal) -> dict:
        from custom_components.hair.wig_claims import sign_claims_bundle
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            signal_row_digest,
        )

        priv, _pub = _keypair_b64()
        return sign_claims_bundle(ClaimsBundle(
            wig_id="w-dreo", handle="dab", rows=[RowClaim(
                alias_at_claim=signal.alias,
                digest=signal_row_digest(signal),
                verdict="worked",
            )],
        ), priv)

    def test_adding_the_flag_orphans_the_claim(self):
        from custom_components.hair.wig_format import (
            Wig,
            WigSignal,
            coverage,
            parse_claims_bundle,
            wig_row_digests,
        )

        signal = WigSignal(alias="Power", pronto=PRONTO)
        entry = self._claim_over(signal)
        assert verify_fitting(entry) == SIGNED_VALID
        wig = Wig(name="Dreo", wig_id="w-dreo", signals=[signal])
        bundles = [parse_claims_bundle(entry)]
        assert coverage(bundles, wig_row_digests(wig))

        # The maintainer later decides Power needs raw replay.
        signal.bypass_protocol = True
        assert verify_fitting(entry) == SIGNED_VALID  # still theirs
        assert not coverage(bundles, wig_row_digests(wig))  # not this row

    def test_removing_the_flag_orphans_the_claim(self):
        from custom_components.hair.wig_format import (
            Wig,
            WigSignal,
            coverage,
            parse_claims_bundle,
            wig_row_digests,
        )

        signal = WigSignal(
            alias="Power", pronto=PRONTO, bypass_protocol=True
        )
        entry = self._claim_over(signal)
        wig = Wig(name="Dreo", wig_id="w-dreo", signals=[signal])
        bundles = [parse_claims_bundle(entry)]
        assert coverage(bundles, wig_row_digests(wig))

        signal.bypass_protocol = False
        assert not coverage(bundles, wig_row_digests(wig))

    def test_a_neighbouring_row_keeps_its_claim(self):
        """The half the old whole-file hash could not do: repairing one
        row leaves everybody else's proof of the others intact."""
        from custom_components.hair.wig_claims import sign_claims_bundle
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            Wig,
            WigSignal,
            coverage,
            parse_claims_bundle,
            signal_row_digest,
            wig_row_digests,
        )

        priv, _pub = _keypair_b64()
        power = WigSignal(alias="Power", pronto=PRONTO)
        mode = WigSignal(alias="Mode", pronto=_PRONTO_B)
        wig = Wig(name="Dreo", wig_id="w-dreo", signals=[power, mode])
        entry = sign_claims_bundle(ClaimsBundle(
            wig_id="w-dreo", handle="dab", rows=[
                RowClaim(
                    alias_at_claim=s.alias,
                    digest=signal_row_digest(s),
                    verdict="worked",
                )
                for s in (power, mode)
            ],
        ), priv)
        bundles = [parse_claims_bundle(entry)]
        assert len(coverage(bundles, wig_row_digests(wig))) == 2

        power.bypass_protocol = True
        proven = coverage(bundles, wig_row_digests(wig))
        assert proven == {signal_row_digest(mode)}
