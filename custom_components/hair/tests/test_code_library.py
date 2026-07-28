"""Tests for the code_library picker introspection.

The introspection runs against the real infrared-protocols codes package.
The codes package is EMPTY on the 5.x library line that HA core ships today
and only carries codebooks on the 6.0+ line, so the content-dependent
tests skip when no codebooks are present and run automatically once a
library with codebooks is installed (no pin change needed). The
non-content tests (library import, invalid-id degradation, the Addition B
class-name pin) always run.

Tests are structural -- they exercise whatever codebooks the installed
library actually exposes rather than hardcoding member names that vary
across library versions.
"""
from __future__ import annotations

import pytest

pytest.importorskip("infrared_protocols")

from custom_components.hair import code_library
from custom_components.hair.pronto_validator import validate_pronto

_HAS_CODES = bool(code_library.get_tree())
_needs_codes = pytest.mark.skipif(
    not _HAS_CODES,
    reason=(
        "infrared-protocols codes package is empty (no codebooks ship until "
        "the 6.0 library line); install a library with codebooks to run these"
    ),
)


def test_library_available():
    assert code_library.library_available() is True


@_needs_codes
def test_tree_is_nonempty_and_well_formed():
    tree = code_library.get_tree()
    assert isinstance(tree, list) and tree
    for brand in tree:
        assert brand["brand"]
        assert brand["label"]
        assert brand["codebooks"]
        for cb in brand["codebooks"]:
            assert cb["id"].count(":") == 1
            assert cb["label"]
            assert cb["functions"]
            for fn in cb["functions"]:
                assert fn["id"].count(":") == 2
                assert fn["name"]


def _first_function_id() -> str:
    tree = code_library.get_tree()
    return tree[0]["codebooks"][0]["functions"][0]["id"]


@_needs_codes
def test_materialize_first_function_roundtrip():
    """Whatever the first available function is, it materializes to a Pronto
    code the Clipper validator accepts."""
    entry = code_library.materialize_function(_first_function_id())
    assert entry is not None
    assert entry["name"]
    assert validate_pronto(entry["code"]).valid
    if entry["decoded_protocol"] is not None:
        assert entry["decoded_fingerprint"].startswith(
            entry["decoded_protocol"] + ":"
        )
        assert isinstance(entry["decoded_address"], int)
        assert isinstance(entry["decoded_command"], int)


@_needs_codes
def test_materialize_codebook_returns_valid_entries():
    tree = code_library.get_tree()
    codebook_id = tree[0]["codebooks"][0]["id"]
    entries = code_library.materialize_codebook(codebook_id)
    assert entries
    assert all(validate_pronto(e["code"]).valid for e in entries)


@_needs_codes
def test_materialize_codebook_subset_filters():
    tree = code_library.get_tree()
    cb = tree[0]["codebooks"][0]
    one_fid = cb["functions"][0]["id"]
    entries = code_library.materialize_codebook(cb["id"], [one_fid])
    assert len(entries) == 1


def test_materialize_invalid_ids_degrade():
    assert code_library.materialize_function("not-a-valid-id") is None
    assert code_library.materialize_function("nope:Nope:NOPE") is None
    assert code_library.materialize_codebook("a:b") == []
    assert code_library.materialize_codebook("garbage") == []


def test_addition_b_nec_class_name_pins_decoded_protocol():
    """Pin the class-name -> protocol mechanism the picker relies on. If the
    library renames NECCommand, this fails loudly instead of the picker
    silently producing a wrong decoded_protocol."""
    from infrared_protocols.commands.nec import NECCommand

    cmd = NECCommand(address=0xFB04, command=0x08)
    assert type(cmd).__name__.removesuffix("Command") == "NEC"


# --- Codebook -> wig snapshot primitive (v0.8.1 library rows) ---


@_needs_codes
def test_build_wig_from_codebook_shape():
    tree = code_library.get_tree()
    brand = tree[0]
    cb = brand["codebooks"][0]
    wig = code_library.build_wig_from_codebook(cb["id"])
    assert wig is not None
    assert wig.name == cb["label"]
    assert wig.brand == brand["label"]
    assert wig.origin == "library"
    # Provenance: notes carry the codebook id for traceability.
    assert cb["id"] in (wig.notes or "")
    # One signal per materializable function, all valid Pronto.
    assert 0 < len(wig.signals) <= len(cb["functions"])
    for sig in wig.signals:
        assert sig.alias
        assert validate_pronto(sig.pronto).valid


@_needs_codes
def test_build_wig_from_codebook_deterministic():
    """Same library version -> same render -> same content hash. The
    property that makes fittings on snapshots comparable across
    installs (and the snapshot dedup work at all)."""
    from custom_components.hair.wig_format import signals_content_hash

    cb_id = code_library.get_tree()[0]["codebooks"][0]["id"]
    first = code_library.build_wig_from_codebook(cb_id)
    again = code_library.build_wig_from_codebook(cb_id)
    assert signals_content_hash(first.signals) == signals_content_hash(
        again.signals
    )


@_needs_codes
def test_build_wig_from_codebook_serialize_roundtrip():
    """The rendered wig must survive its own serialize -> parse cycle
    (the snapshot and download roads both ship serialize_wig output)."""
    from custom_components.hair.wig_format import parse_wig, serialize_wig

    cb_id = code_library.get_tree()[0]["codebooks"][0]["id"]
    wig = code_library.build_wig_from_codebook(cb_id)
    result = parse_wig(serialize_wig(wig))
    assert result.ok
    assert result.wig.origin == "library"
    assert len(result.wig.signals) == len(wig.signals)


def test_build_wig_from_codebook_invalid_ids_degrade():
    assert code_library.build_wig_from_codebook("garbage") is None
    assert code_library.build_wig_from_codebook("a:b:c") is None
    assert code_library.build_wig_from_codebook("no.such.module:Nope") is None
