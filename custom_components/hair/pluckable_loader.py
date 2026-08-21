"""Loader and schema for the pluckable YAML registry (Plucker, v0.5.0).

Pluckable definitions live in ``custom_components/hair/pluckable/`` as one
YAML file per vendor integration. At integration setup HAIR scans that
directory (in a single executor job), validates each file against a
version-keyed voluptuous schema, and registers the valid entries into an
in-memory registry. A new vendor is a single-file PR, no Python touched.

Design rules (see ``docs/internal/plans/plucker.md`` and the YAML review):
  - A bad pluckable never fails HAIR setup. Every error is log-and-skip.
  - ``extra=vol.PREVENT_EXTRA`` catches contributor typos at load time.
  - ``service.data`` templates may only use the fixed placeholder set
    ``{command_name, appliance, tweezer}``; an unknown placeholder is a
    load-time error, not a pluck-time KeyError.
  - Files starting with ``_`` are skipped (templates, drafts).
  - There is NO ``.py`` discovery / import path in v1.

Standalone schema-check (needs only voluptuous + pyyaml, not a full HA env),
run as a direct script from the repo root:
    python custom_components/hair/pluckable_loader.py <file.yaml>
"""
from __future__ import annotations

import logging
import string
from pathlib import Path
from typing import Any

import voluptuous as vol
import yaml

_LOGGER = logging.getLogger(__name__)

# The only placeholders a service.data template may reference. Adding a new
# user-collected input is a schema_version bump + frontend work, not a YAML
# change (see the README "schema boundary" section).
ALLOWED_PLACEHOLDERS = frozenset({"command_name", "appliance", "tweezer"})

# RemoteEntityFeature member names accepted by remote_feature_filter.
_REMOTE_FEATURES = ("LEARN_COMMAND", "DELETE_COMMAND", "LEARN_RF")

# How HAIR gets codes out of a vendor integration (0.10.3).
#
#   replay  -- ask the integration to SEND a stored code and catch it at
#              the HAIR Tweezer before it becomes light. The v0.5.0
#              mechanism, and the only one until now.
#   storage -- read the codes the user already learned, at rest, out of
#              the file the integration keeps under .storage. Read-only,
#              always.
#
# A v1 file has no mechanism field and is normalized to "replay", so
# every existing pluckable keeps loading forever with nothing to
# migrate.
MECHANISMS = ("replay", "storage")
DEFAULT_MECHANISM = "replay"


def _template_value(value: Any) -> str:
    """Validate that a service.data template uses only allowed placeholders."""
    if not isinstance(value, str):
        raise vol.Invalid("service.data values must be strings")
    for _literal, field_name, _spec, _conv in string.Formatter().parse(value):
        if field_name is None:
            continue
        if field_name not in ALLOWED_PLACEHOLDERS:
            raise vol.Invalid(
                f"unknown placeholder '{{{field_name}}}' in '{value}' "
                f"(allowed: {sorted(ALLOWED_PLACEHOLDERS)})"
            )
    return value


_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("domain"): str,
        vol.Required("name"): str,
        vol.Required("target_param"): str,
        vol.Required("data"): {str: _template_value},
    }
)

SCHEMA_V1 = vol.Schema(
    {
        vol.Required("schema_version"): vol.All(int, vol.Range(min=1)),
        vol.Required("name"): str,
        vol.Required("integration"): str,
        # Validated as a plain string, not vol.Url(): the URL-format
        # validators were dropped from newer voluptuous releases, and docs_url
        # is an optional informational link, so strict URL validation is not
        # worth the cross-version fragility.
        vol.Optional("docs_url"): str,
        vol.Optional("remote_feature_filter"): vol.In(_REMOTE_FEATURES),
        vol.Required("service"): _SERVICE_SCHEMA,
        vol.Optional("appliance_label"): str,
        vol.Optional("appliance_help"): str,
        vol.Optional("error_map", default=dict): {str: str},
    },
    extra=vol.PREVENT_EXTRA,
)

SCHEMA_V2 = vol.Schema(
    {
        vol.Required("schema_version"): vol.All(int, vol.Range(min=1)),
        vol.Required("name"): str,
        vol.Required("integration"): str,
        vol.Optional("docs_url"): str,
        vol.Optional("mechanism", default=DEFAULT_MECHANISM): vol.In(MECHANISMS),
        vol.Optional("remote_feature_filter"): vol.In(_REMOTE_FEATURES),
        # Conditional, and THAT is why this is a version bump rather
        # than a new Optional field on v1 (the loader's own rule, and
        # the probe called it): a store-read entry has nothing to put in
        # a service block, so "service" stops being Required and its
        # requirement moves into _validate_v2 below.
        vol.Optional("service"): _SERVICE_SCHEMA,
        vol.Optional("store_provider"): str,
        vol.Optional("appliance_label"): str,
        vol.Optional("appliance_help"): str,
        vol.Optional("error_map", default=dict): {str: str},
    },
    extra=vol.PREVENT_EXTRA,
)


def _validate_v2(data: Any) -> dict[str, Any]:
    """Schema v2 plus the rules a declarative schema cannot express."""
    entry = dict(SCHEMA_V2(data))
    mechanism = entry.get("mechanism", DEFAULT_MECHANISM)
    if mechanism == "replay":
        if not entry.get("service"):
            raise vol.Invalid("a replay pluckable needs a service block")
        if entry.get("store_provider"):
            raise vol.Invalid("store_provider belongs to mechanism: storage")
    else:
        if entry.get("service"):
            raise vol.Invalid(
                "a storage pluckable reads files and calls no vendor service"
            )
        if not entry.get("store_provider"):
            raise vol.Invalid("a storage pluckable needs a store_provider")
    return entry


# Version-keyed schemas. A file is validated against the schema matching its
# declared schema_version, so a v1 file keeps loading forever with no
# migration. Adding a new Optional field needs no bump; a new Required field
# or changed semantics bumps the version and adds a SCHEMA_V2 entry here.
_SCHEMAS: dict[int, Any] = {1: SCHEMA_V1, 2: _validate_v2}


def validate_pluckable(data: Any) -> dict[str, Any]:
    """Validate one pluckable mapping against its declared schema version.

    Raises ``vol.Invalid`` on any problem (missing version, unknown version,
    schema violation). Returns the normalized entry (defaults applied) on
    success.
    """
    if not isinstance(data, dict):
        raise vol.Invalid("pluckable file must be a YAML mapping")
    version = data.get("schema_version")
    if version is None:
        raise vol.Invalid("schema_version is required")
    if version not in _SCHEMAS:
        raise vol.Invalid(
            f"schema_version {version} needs a newer HAIR "
            f"(known: {sorted(_SCHEMAS)})"
        )
    entry = dict(_SCHEMAS[version](data))
    # Normalized so every consumer can read entry["mechanism"] without
    # caring which schema version the file declared.
    entry.setdefault("mechanism", DEFAULT_MECHANISM)
    return entry


def load_pluckables(directory: Path) -> list[dict[str, Any]]:
    """Scan, parse, and validate every pluckable YAML file in a directory.

    Synchronous and self-contained so the caller can run the whole scan in a
    single ``hass.async_add_executor_job`` hop off the event loop. One bad
    file never drops a good sibling and never fails setup; each problem is
    logged and skipped. Files starting with ``_`` are excluded.
    """
    registry: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], str] = {}
    if not directory.is_dir():
        return registry
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as err:
            _LOGGER.warning("Pluckable %s skipped: unreadable YAML (%s)", path.name, err)
            continue
        try:
            entry = validate_pluckable(data)
        except vol.Invalid as err:
            _LOGGER.warning("Pluckable %s skipped: %s", path.name, err)
            continue
        # One entry per (integration, mechanism), not per integration:
        # Tuya Local legitimately ships both, and they cover different
        # things (replay reaches the vendor codebook, storage reaches
        # the codes the user learned themselves).
        key = (entry["integration"], entry["mechanism"])
        if key in seen:
            _LOGGER.warning(
                "Pluckable %s skipped: %s/%s already defined by %s",
                path.name,
                key[0],
                key[1],
                seen[key],
            )
            continue
        seen[key] = path.name
        entry["_source_file"] = path.name
        registry.append(entry)
    return registry


def _main(argv: list[str] | None = None) -> int:
    """Standalone schema-check entry point for contributors."""
    import sys

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m custom_components.hair.pluckable_loader <file.yaml>")
        return 2
    path = Path(args[0])
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate_pluckable(data)
    except (OSError, yaml.YAMLError, vol.Invalid) as err:
        print(f"INVALID: {err}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
