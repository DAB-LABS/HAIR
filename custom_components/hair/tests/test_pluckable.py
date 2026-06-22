"""Tests for the pluckable YAML registry loader and schema (Plucker v0.5.0)."""
from __future__ import annotations

import textwrap

import pytest
import voluptuous as vol

from custom_components.hair.pluckable_loader import (
    load_pluckables,
    validate_pluckable,
)

_VALID = {
    "schema_version": 1,
    "name": "Tuya Local",
    "integration": "tuya_local",
    "service": {
        "domain": "tuya_local",
        "name": "send_learned_ir_command",
        "target_param": "entity_id",
        "data": {
            "command": "{command_name}",
            "device": "{appliance}",
            "emitter_entity_id": "{tweezer}",
        },
    },
}


def _copy(**overrides):
    """Deep-ish copy of _VALID with top-level overrides."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _VALID.items()}
    out.update(overrides)
    return out


# --- validator ------------------------------------------------------------


def test_valid_pluckable_returns_normalized_entry():
    entry = validate_pluckable(_copy())
    assert entry["integration"] == "tuya_local"
    assert entry["error_map"] == {}  # default applied


def test_missing_service_invalid():
    bad = _copy()
    bad.pop("service")
    with pytest.raises(vol.Invalid):
        validate_pluckable(bad)


def test_missing_schema_version_invalid():
    bad = _copy()
    bad.pop("schema_version")
    with pytest.raises(vol.Invalid):
        validate_pluckable(bad)


def test_unknown_schema_version_invalid():
    with pytest.raises(vol.Invalid):
        validate_pluckable(_copy(schema_version=2))


def test_extra_key_invalid_prevent_extra():
    with pytest.raises(vol.Invalid):
        validate_pluckable(_copy(apliance_label="typo"))


def test_bad_placeholder_invalid():
    bad = _copy()
    bad["service"] = dict(_VALID["service"])
    bad["service"]["data"] = {"command": "{command_nam}"}
    with pytest.raises(vol.Invalid):
        validate_pluckable(bad)


def test_allowed_placeholders_and_literal_pass():
    ok = _copy()
    ok["service"] = dict(_VALID["service"])
    ok["service"]["data"] = {
        "a": "{command_name}",
        "b": "{appliance}",
        "c": "{tweezer}",
        "d": "a literal value",
    }
    entry = validate_pluckable(ok)
    assert entry["service"]["data"]["d"] == "a literal value"


def test_bad_remote_feature_filter_invalid():
    with pytest.raises(vol.Invalid):
        validate_pluckable(_copy(remote_feature_filter="NONSENSE"))


def test_non_mapping_invalid():
    with pytest.raises(vol.Invalid):
        validate_pluckable(["not", "a", "mapping"])


# --- loader / scan --------------------------------------------------------

_VALID_YAML = textwrap.dedent(
    """
    schema_version: 1
    name: Tuya Local
    integration: tuya_local
    service:
      domain: tuya_local
      name: send_learned_ir_command
      target_param: entity_id
      data:
        command: "{command_name}"
        device: "{appliance}"
        emitter_entity_id: "{tweezer}"
    """
)


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_file(tmp_path):
    _write(tmp_path, "tuya_local.yaml", _VALID_YAML)
    reg = load_pluckables(tmp_path)
    assert len(reg) == 1
    assert reg[0]["integration"] == "tuya_local"
    assert reg[0]["_source_file"] == "tuya_local.yaml"


def test_empty_file_skipped(tmp_path):
    _write(tmp_path, "empty.yaml", "")
    assert load_pluckables(tmp_path) == []


def test_malformed_yaml_skipped_others_load(tmp_path):
    _write(tmp_path, "bad.yaml", "foo: [1, 2")  # unterminated flow sequence
    _write(tmp_path, "tuya_local.yaml", _VALID_YAML)
    reg = load_pluckables(tmp_path)
    assert [e["integration"] for e in reg] == ["tuya_local"]


def test_underscore_files_excluded(tmp_path):
    _write(tmp_path, "_template.yaml", _VALID_YAML)
    _write(tmp_path, "_draft.yaml", _VALID_YAML)
    assert load_pluckables(tmp_path) == []


def test_duplicate_integration_keeps_first(tmp_path):
    _write(tmp_path, "a_tuya.yaml", _VALID_YAML)
    _write(tmp_path, "b_tuya.yaml", _VALID_YAML)
    reg = load_pluckables(tmp_path)
    assert len(reg) == 1
    assert reg[0]["_source_file"] == "a_tuya.yaml"  # lexical first kept


def test_non_yaml_files_ignored(tmp_path):
    _write(tmp_path, "notes.txt", "ignore me")
    _write(tmp_path, "tuya_local.yaml", _VALID_YAML)
    assert len(load_pluckables(tmp_path)) == 1


def test_invalid_file_skipped_without_crash(tmp_path):
    _write(tmp_path, "broken.yaml", "schema_version: 1\nname: X\n")  # missing required
    assert load_pluckables(tmp_path) == []


def test_missing_directory_returns_empty(tmp_path):
    assert load_pluckables(tmp_path / "does_not_exist") == []


def test_shipped_tuya_yaml_validates():
    """The real tuya_local.yaml that ships with HAIR must validate."""
    from pathlib import Path

    import custom_components.hair as hair_pkg

    pluckable_dir = Path(hair_pkg.__file__).parent / "pluckable"
    reg = load_pluckables(pluckable_dir)
    integrations = {e["integration"] for e in reg}
    assert "tuya_local" in integrations
