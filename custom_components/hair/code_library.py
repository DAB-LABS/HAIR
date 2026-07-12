"""Code-source dispatcher behind the Add Remote picker.

This module keeps the SAME public API the rest of the integration already
imports from ``code_library`` (``library_available``, ``get_tree``,
``codebook_label``, ``materialize_function``, ``materialize_codebook``) but
no longer contains any code logic itself. It fans out to a list of *sources*:

* ``LibrarySource``    — the built-in infrared-protocols codebooks (ids ``lib:…``)
* ``CustomYamlSource`` — user YAML in ``<config>/hair_codes/``  (ids ``custom:…``)

Adding a third source later is just appending to ``_SOURCES``.

Ids carry a routing prefix (``lib:`` / ``custom:``) so a materialize call
goes back to the source that produced it. Unprefixed ids — anything stored
before this refactor — fall through to ``LibrarySource``, which is where
they came from, so nothing breaks.
"""
from __future__ import annotations

import re
from typing import Any

from .custom_yaml_source import CustomYamlSource
from .library_source import LibrarySource

#: Order matters only for display/legacy fallback. The first entry is also
#: the fallback for unprefixed (legacy) ids.
_SOURCES = [LibrarySource(), CustomYamlSource()]


def _route(identifier: str):
    """Pick the source that owns ``identifier`` by its ``prefix:`` token."""
    prefix = identifier.split(":", 1)[0]
    for source in _SOURCES:
        if source.prefix == prefix:
            return source
    return _SOURCES[0]  # legacy, unprefixed ids belonged to the library


def library_available() -> bool:
    """True if ANY source actually has codes (reviewer point 7).

    Name kept for backwards compatibility with existing callers; semantics
    fixed so it reflects real, materializable codes rather than a successful
    import or an existing (possibly empty) directory.
    """
    return any(source.available() for source in _SOURCES)


def _brand_key(brand: dict[str, Any]) -> str:
    """Normalize a brand label so e.g. library ``LG`` and custom ``LG`` merge."""
    return re.sub(r"[^a-z0-9]+", "", str(brand.get("label", "")).lower()) or str(
        brand.get("brand", "")
    )


def get_tree() -> list[dict[str, Any]]:
    """Merged brand -> codebook -> function tree across every source.

    Brands with the same (normalized) label are merged into one bucket so
    the picker shows a single "LG" holding both library and custom
    codebooks. Codebook ids stay prefixed, so there is never a collision —
    the merge is purely presentational; the sources remain independent.
    """
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for source in _SOURCES:
        for brand in source.get_tree():
            key = _brand_key(brand)
            bucket = merged.get(key)
            if bucket is None:
                bucket = {"brand": brand["brand"], "label": brand["label"], "codebooks": []}
                merged[key] = bucket
                order.append(key)
            bucket["codebooks"].extend(brand["codebooks"])

    result = [merged[key] for key in order]
    for bucket in result:
        bucket["codebooks"].sort(key=lambda c: c["label"].lower())
    result.sort(key=lambda b: b["label"].lower())
    return result


def codebook_label(codebook_id: str) -> str | None:
    """Human label for a codebook id, e.g. for a default remote name."""
    return _route(codebook_id).codebook_label(codebook_id)


def materialize_function(function_id: str) -> dict[str, Any] | None:
    """Materialize a single function id into a Clipper entry, or None."""
    return _route(function_id).materialize_function(function_id)


def materialize_codebook(
    codebook_id: str, function_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Materialize a whole codebook (or a subset of its functions)."""
    return _route(codebook_id).materialize_codebook(codebook_id, function_ids)


def ensure_custom_dir(seed: bool = True):
    """Create/seed ``<config>/hair_codes/``. Call once from integration setup.

    Delegates to every source that supports it (currently ``CustomYamlSource``)
    so users get a ready-to-edit template + README on first run.
    """
    for source in _SOURCES:
        ensure = getattr(source, "ensure_dir", None)
        if callable(ensure):
            ensure(seed=seed)
