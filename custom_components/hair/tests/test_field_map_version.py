"""A map's version moves when what it reads moves, and at no other time.

Stored answers to comb findings -- Keep, Keep Both, the Unusual card's
Keep -- are keyed on the map version (``tangles.attestation_key``). A
version that moved on a note, an agreement figure or the schema_version
line sent every answered finding for that family back to its owner, for
an edit that could not have changed a single reading. So the version is
a digest of the PARSED map: the frame shape and timing alphabet, the
identity bytes, every field's location, encoding, parameters,
applicability, traits, coordinate and confidence, and every rule's type,
parameters and confidence. Nothing descriptive.

Each direction is pinned against a real map from the directory rather
than a toy, so a test here fails the day a real map stops behaving.
"""
from __future__ import annotations

import copy
import dataclasses
import inspect
from pathlib import Path

import pytest
import yaml

from custom_components.hair import field_readers as fr

MAPS_DIR = Path(fr.__file__).parent / "field_maps"


def _doc(name: str = "TCL112") -> dict:
    raw = yaml.safe_load((MAPS_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _version(raw: dict) -> str:
    parsed = fr.parse_map(raw)
    assert parsed is not None
    return parsed.version


def _field(raw: dict, name: str) -> dict:
    return next(f for f in raw["fields"] if f["name"] == name)


# ---------------------------------------------------------------------------
# Edits that must NOT move it
# ---------------------------------------------------------------------------

def _set_schema_version(raw):
    raw["schema_version"] = "9.9"


def _edit_notes(raw):
    raw["derivation"]["notes"].append("a note written after the fact")


def _edit_open_questions(raw):
    raw["derivation"]["open_questions"] = []


def _edit_files_used(raw):
    raw["derivation"]["files_used"] = [{"repo": "elsewhere", "file": "1"}]


def _drop_derivation(raw):
    del raw["derivation"]


def _edit_agreement(raw):
    agreement = _field(raw, "mode")["agreement"]
    agreement["pass"] += 1
    agreement["rate"] = "100.00%"
    agreement["disagreeing_files"] = []


def _edit_vocabulary_notes(raw):
    _field(raw, "fan_speed")["vocabulary_notes"].append("another caveat")


def _edit_prose(raw):
    _field(raw, "mode")["encoding"] = "reworded entirely"
    raw["integrity"][0]["description"] = "reworded entirely"


def _edit_verified_on(raw):
    raw["integrity"][0]["verified_on"] = "1/1 cells"


def _edit_aliases_and_status(raw):
    raw["aliases"] = ["something else"]
    raw["status"] = "ratified"


def _edit_synthesis(raw):
    raw["synthesis"]["fixture_coordinates"]["temp"] = [18]


def _edit_human_vocabulary_copy(raw):
    """The copy beside ``encoding_ref`` is for people. The reader uses
    ``encoding_ref.params.vocabulary`` and never looks at this one."""
    _field(raw, "mode")["vocabulary"]["cool"] = 0x6


def _edit_superseded_frame_keys(raw):
    """Pre-v0.2 keys the timing block replaced; only the offline fixture
    synthesizer reads them, never the reader."""
    frame = raw["frame"]
    frame["header_us"] = [1, 1]
    frame["bit0_us"] = {"mark": 1, "space": 1}
    frame["carrier_hz"] = 40000
    frame["modulation"] = "other"
    frame["frames_per_command"] = 9
    frame["header_tolerance_us"] = 1


NEUTRAL_EDITS = [
    _set_schema_version, _edit_notes, _edit_open_questions, _edit_files_used,
    _drop_derivation, _edit_agreement, _edit_vocabulary_notes, _edit_prose,
    _edit_verified_on, _edit_aliases_and_status, _edit_synthesis,
    _edit_human_vocabulary_copy, _edit_superseded_frame_keys,
]


@pytest.mark.parametrize("edit", NEUTRAL_EDITS, ids=lambda f: f.__name__)
def test_a_descriptive_edit_leaves_the_version_alone(edit):
    raw = _doc()
    before = _version(raw)
    edited = copy.deepcopy(raw)
    edit(edited)
    assert _version(edited) == before


def test_leaving_out_a_default_leaves_it_alone():
    """Same reading, so same version: an omitted frame parses as frame 0
    and an omitted bits as full_byte, so writing them out or leaving
    them off is one map, not two."""
    raw = _doc("MHI152")
    before = _version(raw)
    edited = copy.deepcopy(raw)
    removed = 0
    for field in edited["fields"]:
        if field.get("frame") == 0:
            del field["frame"]
            removed += 1
        if field.get("bits") == "full_byte":
            del field["bits"]
            removed += 1
    assert removed, "the edit must actually change the document"
    assert _version(edited) == before


# ---------------------------------------------------------------------------
# Edits that MUST move it
# ---------------------------------------------------------------------------

def _move_byte(raw):
    _field(raw, "mode")["byte"] += 1


def _change_bits(raw):
    _field(raw, "mode")["bits"] = "mask:0x0F"


def _change_vocabulary_value(raw):
    _field(raw, "mode")["encoding_ref"]["params"]["vocabulary"]["cool"] = 0x6


def _change_field_confidence(raw):
    _field(raw, "fan_speed")["confidence"] = "ratified"


def _change_encoding(raw):
    ref = _field(raw, "temperature")["encoding_ref"]
    ref["params"]["offset"] = ref["params"]["offset"] + 1


def _change_field_frame(raw):
    _field(raw, "quiet")["frame"] = 1


def _change_applies_when(raw):
    _field(raw, "quiet")["applies_when"] = {"not_in": {"mode": ["dry", "heat"]}}


def _change_mode_traits(raw):
    _field(raw, "mode")["mode_traits"]["dry"]["temp"] = "varies"


def _change_coordinate(raw):
    _field(raw, "quiet")["coordinate"] = "swing"


def _change_rule_params(raw):
    raw["integrity"][1]["params"]["offset"] = 16


def _change_rule_confidence(raw):
    raw["integrity"][0]["confidence"] = "provisional"


def _drop_a_rule(raw):
    raw["integrity"].pop()


def _change_timing_window(raw):
    raw["frame"]["timing"]["space_one_us"]["min"] += 1


def _change_identity_bytes(raw):
    raw["frame"]["identity_bytes"][0][2] = 0x24


def _change_setting_frames(raw):
    raw["frame"]["setting_frames"] = [1]


def _change_bit_order(raw):
    raw["frame"]["bit_order"] = "msb_first"


def _change_bits_tolerance(raw):
    raw["frame"]["bits_tolerance"] = 3


READING_EDITS = [
    _move_byte, _change_bits, _change_vocabulary_value,
    _change_field_confidence, _change_encoding, _change_field_frame,
    _change_applies_when, _change_mode_traits, _change_coordinate,
    _change_rule_params, _change_rule_confidence, _drop_a_rule,
    _change_timing_window, _change_identity_bytes, _change_setting_frames,
    _change_bit_order, _change_bits_tolerance,
]


@pytest.mark.parametrize("edit", READING_EDITS, ids=lambda f: f.__name__)
def test_an_edit_to_what_the_map_reads_moves_the_version(edit):
    raw = _doc()
    before = _version(raw)
    edited = copy.deepcopy(raw)
    edit(edited)
    assert _version(edited) != before


# ---------------------------------------------------------------------------
# Same content, same version
# ---------------------------------------------------------------------------

def test_the_same_content_gives_the_same_version():
    first = {m.protocol_id: m.version for m in fr.load_maps()}
    second = {m.protocol_id: m.version for m in fr.load_maps()}
    assert first == second
    assert len(set(first.values())) == len(first), "two maps share a version"


def test_key_order_in_the_document_does_not_matter():
    raw = _doc()
    reordered = {key: raw[key] for key in reversed(list(raw))}
    reordered["frame"] = {
        key: raw["frame"][key] for key in reversed(list(raw["frame"]))
    }
    field = _field(reordered, "mode")
    vocab = field["encoding_ref"]["params"]["vocabulary"]
    field["encoding_ref"]["params"]["vocabulary"] = {
        key: vocab[key] for key in reversed(list(vocab))
    }
    assert _version(reordered) == _version(raw)


def test_a_vocabulary_that_mixes_key_types_is_digested():
    """YAML reads a bare ``on:`` as the boolean True, beside string keys.
    Sorting those against each other would raise; the digest must not,
    and must still tell True from the string "True"."""
    raw = _doc()
    params = _field(raw, "power")["encoding_ref"]["params"]
    params["vocabulary"] = {True: 1, "off": 0}
    as_bool = _version(raw)
    params["vocabulary"] = {"True": 1, "off": 0}
    assert _version(raw) != as_bool


# ---------------------------------------------------------------------------
# Nothing the reader holds can be left out by accident
# ---------------------------------------------------------------------------

def test_every_part_of_a_parsed_map_is_digested_or_named_as_excluded():
    """``FieldSpec``, ``FrameTiming`` and ``IntegrityRule`` go in whole,
    minus the named exclusions, so a new attribute on any of them is
    covered the day it lands. ``FieldMap`` is assembled by hand, so this
    catches a new attribute there that nobody decided about."""
    parameters = set(inspect.signature(fr._map_version).parameters)
    renamed = {"identity": "identity_bytes", "rules": "integrity"}
    digested = {renamed.get(name, name) for name in parameters}
    declared = {field.name for field in dataclasses.fields(fr.FieldMap)}
    assert declared - fr._VERSION_EXCLUDED["FieldMap"] == digested
    rule_fields = {field.name for field in dataclasses.fields(fr.IntegrityRule)}
    assert fr._VERSION_EXCLUDED["IntegrityRule"] <= rule_fields
