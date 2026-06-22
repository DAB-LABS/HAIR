# Pluckable registry

This directory holds the pluckable registry: one YAML file per vendor
integration that HAIR can pull stored IR codes from. Adding a vendor is a
single-file pull request. No HAIR Python code changes.

## What a pluckable is

The Plucker imports IR codes that already live in a vendor IR blaster (codes
you learned in the vendor's app) into HAIR as native signals, without
re-learning each one at an IR receiver.

It works by asking the vendor integration to replay a stored code, by name,
through a chosen emitter, and pointing that emitter at HAIR's own observer
emitter (the HAIR Tweezer). HAIR captures the code before it becomes physical
IR. No IR is broadcast during a pluck.

A vendor qualifies as a pluckable only if it exposes a service that replays a
stored code by name through a target emitter entity. An integration that only
fires through its own hardware, or that addresses codes by a raw blob instead
of a stored name, does not fit and cannot be added as a YAML file alone.

## The schema

Every field, with `tuya_local.yaml` as the worked example:

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | yes | Schema version this file targets. Keep at 1 unless told otherwise. |
| `name` | yes | Vendor name shown in the UI and used as the error-message prefix. |
| `integration` | yes | HA integration domain that owns the blaster entities and the service. |
| `docs_url` | no | Link to the vendor integration's docs. |
| `remote_feature_filter` | no | A `RemoteEntityFeature` name. Only matching `remote.*` entities are offered. Usually `LEARN_COMMAND`. |
| `service.domain` | yes | The send service's integration domain. |
| `service.name` | yes | The send service's name. |
| `service.target_param` | yes | The target parameter that receives the vendor blaster entity id (usually `entity_id`). |
| `service.data` | yes | The service-call data. Values are templates (see below). |
| `appliance_label` | no | Override the Add Remote dialog's appliance field label. |
| `appliance_help` | no | Override the appliance field help text. |
| `error_map` | no | Map a raw vendor error substring to friendlier text. |

## The schema boundary

`service.data` template values may use ONLY this fixed placeholder set:

- `{command_name}` -- the command name the user types in the Pluck dialog
- `{appliance}` -- the appliance/group name set on the plucked blaster
- `{tweezer}` -- the HAIR Tweezer entity id, filled in by HAIR

The Add Remote dialog collects exactly one free input (the appliance) and the
Pluck dialog collects exactly one (the command name). A vendor whose service
needs a third user-supplied input cannot be expressed in YAML alone. That
needs a `schema_version` bump and new dialog work, not just a YAML file. If
you think you need a third input or custom Python logic, talk to the
maintainer first.

Literal values are fine. A literal `{` or `}` you want in the output is
written doubled (`{{` and `}}`). Any placeholder outside the allowed set
fails at load time, so a typo such as `{command_nam}` shows up in the HA log
rather than at pluck time.

## Versioning

- Adding an optional field does not bump the version.
- Adding a required field, or changing what a field means, bumps the version.
- A file is always validated against the schema for the version it declares,
  so an older file keeps working unchanged. Contributor files are never
  rewritten on disk.
- Omitting `schema_version` is an error: the file is skipped with a log line.
- A version newer than the running HAIR is skipped with a log line.

## Testing your file

Schema-check without a HAIR dev setup. This runs as a direct script and needs
only `pip install voluptuous pyyaml`, not a full Home Assistant environment.
From the repository root:

    python custom_components/hair/pluckable_loader.py custom_components/hair/pluckable/your_vendor.yaml

It prints `OK` or `INVALID: <reason>`.

Real-blaster check without a HAIR dev setup, on a running HA that has HAIR
installed: call your vendor's send service from Developer Tools, Actions, with
the emitter target set to the HAIR Tweezer entity, and confirm a signal
appears in the Pluck dialog or the Sniffer. This validates the service shape,
which is the only vendor-specific risk.

## `error_map` policy

Pass-through is the default and the right choice. Only add an `error_map`
entry when the raw vendor message is genuinely confusing to an end user. Never
use it to suppress or rewrite a real failure into a misleadingly positive
message.

## Opening a pull request

1. Copy `_template.yaml.example` to `<integration>.yaml`.
2. Fill in the fields against your vendor's service.
3. Schema-check it with the command above.
4. If you can, run the real-blaster check.
5. Open a PR with the one new YAML file and a one-line CHANGELOG entry.

### Review checklist (maintainer)

- `schema_version` present and supported.
- `integration` is a real HA integration domain.
- `service.domain` and `service.name` are plausible for that integration.
- `target_param` is correct for that service.
- Every `service.data` value uses only allowed placeholders.
- `error_map` keys are genuine exception substrings.
- `docs_url` resolves.
- `name` and `integration` are unique across this directory.
- No `.py` sibling file (not supported in this version).
