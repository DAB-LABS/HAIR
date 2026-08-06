"""Fitting signatures: per-install ed25519 attestation (Tier 1).

Design: fitting-flow.md Section 14. What a signature buys, honestly:
nobody can forge or alter an EXISTING attester's fitting, and fittings
from one install are provably from one install over time, so
reputation can accumulate. It does NOT stop a fresh forger minting a
fresh key -- the factory's three-distinct-GitHub-handles bar and the
Tier 2 key binding (``github.com/<handle>.keys``) answer that.

The envelope: two optional fields on a signed fitting --

- ``key``: base64 raw 32-byte ed25519 public key
- ``sig``: base64 raw 64-byte signature over the canonical fitting form

The canonical form is the fitting object WITHOUT ``sig`` (``key``
included, preventing key swap), JSON-serialized with sorted keys and
compact separators, UTF-8. ``content_hash`` sits inside the fitting,
so the signature transitively pins the exact signal set.

Privacy ruling restated: no HA user UUID, install UUID, or any hash of
them ever enters a wig. The public key is the install's only pseudonym,
and unlike an identifier it cannot be claimed without the private half.

``cryptography`` is an HA core dependency, so it is present on every
real install; the guarded imports exist for bare test environments and
degrade to unsigned fittings, never to failure.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

SIGNING_STORAGE_KEY = "hair.fitting_key"
SIGNING_STORAGE_VERSION = 1

SIG_FIELD = "sig"
KEY_FIELD = "key"

# Verification states rendered by the ledger.
SIGNED_VALID = "valid"
SIGNED_INVALID = "invalid"


def crypto_available() -> bool:
    """True when the ed25519 primitives can be imported."""
    try:
        from cryptography.hazmat.primitives.asymmetric import (  # noqa: F401
            ed25519,
        )
    except ImportError:
        return False
    return True


def canonical_fitting_bytes(entry: dict[str, Any]) -> bytes:
    """The exact bytes a fitting signature covers.

    The entry minus ``sig`` (``key`` stays in), sorted keys, compact
    separators, ensure_ascii off, UTF-8. This form is contract: any
    change forks signature validity across installs, exactly like the
    canonical signals form it sits beside in wig_format.
    """
    payload = {k: v for k, v in entry.items() if k != SIG_FIELD}
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sign_fitting(entry: dict[str, Any], private_key_b64: str) -> bool:
    """Sign ``entry`` in place: sets ``key`` and ``sig``. False on failure.

    Any pre-existing signature is replaced (re-finishing a resumed
    fitting re-signs it).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        private = Ed25519PrivateKey.from_private_bytes(
            base64.b64decode(private_key_b64)
        )
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
        )

        public_raw = private.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        entry.pop(SIG_FIELD, None)
        entry[KEY_FIELD] = base64.b64encode(public_raw).decode("ascii")
        signature = private.sign(canonical_fitting_bytes(entry))
        entry[SIG_FIELD] = base64.b64encode(signature).decode("ascii")
        return True
    except Exception:  # a signing failure must never lose the fitting
        _LOGGER.exception("Could not sign fitting; recording unsigned")
        entry.pop(SIG_FIELD, None)
        entry.pop(KEY_FIELD, None)
        return False


def verify_fitting(entry: dict[str, Any]) -> str | None:
    """Verify a fitting's signature.

    Returns ``"valid"``, ``"invalid"`` (payload altered, key swapped, or
    malformed envelope), or ``None`` for an unsigned fitting. A bad
    signature never invalidates the fitting's DATA -- it invalidates the
    attribution claim, and the UI says which.
    """
    sig_b64 = entry.get(SIG_FIELD)
    key_b64 = entry.get(KEY_FIELD)
    if sig_b64 is None and key_b64 is None:
        return None
    if not isinstance(sig_b64, str) or not isinstance(key_b64, str):
        return SIGNED_INVALID
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError:
        # No crypto in this environment: the claim cannot be checked.
        # Report invalid rather than valid -- never vouch blind.
        return SIGNED_INVALID
    try:
        public = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(key_b64)
        )
        public.verify(
            base64.b64decode(sig_b64), canonical_fitting_bytes(entry)
        )
    except InvalidSignature:
        return SIGNED_INVALID
    except Exception:
        return SIGNED_INVALID
    return SIGNED_VALID


def key_fingerprint(key_b64: str) -> str | None:
    """Short display form of a public key: sha256, first 16 hex."""
    import hashlib

    try:
        raw = base64.b64decode(key_b64, validate=True)
    except Exception:
        return None
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()[:16]


async def async_get_public_key(hass: HomeAssistant) -> str | None:
    """This install's public signing key, base64, or None.

    Derives the public half of ``async_get_private_key``'s key for
    callers that only need to check "is this bundle mine" without
    handling the private key themselves -- the same-key re-sign
    notice (Second Fitting v3 punch list, item 1) is the first one.
    """
    private_key_b64 = await async_get_private_key(hass)
    if not private_key_b64:
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
        )

        private = Ed25519PrivateKey.from_private_bytes(
            base64.b64decode(private_key_b64)
        )
        public_raw = private.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        return base64.b64encode(public_raw).decode('ascii')
    except Exception:
        _LOGGER.exception('Could not derive this install public key')
        return None


async def async_get_private_key(hass: HomeAssistant) -> str | None:
    """Load (or create on first use) the install's signing key.

    Stored via HA's Store with the private flag, so it is excluded from
    cloud backups' unencrypted paths the same way auth data is. Returns
    the base64 private key, or None when crypto is unavailable or
    storage fails -- callers then record unsigned fittings.
    """
    if not crypto_available():
        return None
    try:
        from homeassistant.helpers.storage import Store

        store: Any = Store(
            hass, SIGNING_STORAGE_VERSION, SIGNING_STORAGE_KEY,
            private=True,
        )
        data = await store.async_load()
        if data and isinstance(data.get("private_key"), str):
            return data["private_key"]

        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
        )

        private = Ed25519PrivateKey.generate()
        private_b64 = base64.b64encode(
            private.private_bytes(
                Encoding.Raw, PrivateFormat.Raw, NoEncryption()
            )
        ).decode("ascii")
        await store.async_save({"private_key": private_b64})
        _LOGGER.info(
            "Generated this install's fitting signing key (ed25519)"
        )
        return private_b64
    except Exception:
        _LOGGER.exception(
            "Fitting signing key unavailable; fittings record unsigned"
        )
        return None
