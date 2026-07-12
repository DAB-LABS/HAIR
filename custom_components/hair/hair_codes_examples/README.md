# HAIR — custom YAML remote codes

HAIR's **Add Remote** picker is fed by two independent sources:

| Source            | Where the codes come from                              | Id prefix |
| ----------------- | ------------------------------------------------------ | --------- |
| `LibrarySource`   | the built-in `infrared-protocols` codebooks (shipped)  | `lib:`    |
| `CustomYamlSource`| **your** YAML files, described here                    | `custom:` |

Both appear together in the picker. This document is about the second one.

## Where your files go

Put your YAML files in:

```
<config>/hair_codes/
```

That directory is **outside** `custom_components/`, on purpose: updating HAIR
through HACS replaces the integration's own files but never touches your
`hair_codes/` folder, so your remotes survive upgrades.

The folder (with this README and `_template.yaml.example`) is created
automatically the first time HAIR loads. If it isn't there, create it
yourself and drop `.yaml` files in.

## File format

One file = one remote (one brand + one model). Copy
`_template.yaml.example` to `<config>/hair_codes/my_remote.yaml` and edit it.

```yaml
brand: LG                 # required — top-level group in the picker
model: AKB74915324        # required — the codebook under that brand
functions:                # required — mapping of STABLE id -> code
  power:
    name: Power           # optional label (defaults to a title-cased key)
    pronto: "0000 006D …" # code as a ready Pronto string …
  temp_up:
    raw: [9000, -4500, …] # … OR raw signed timings + carrier frequency
    frequency: 38000
    protocol: NEC         # optional decoded identity (kept end-to-end)
    address: 0x04
    command: 0x08
```

### Rules

- **`brand` and `model` are explicit fields.** HAIR does **not** guess them
  from button names.
- **Function keys are stable ids** — `power`, `temp_up`, `mode` — not
  `btn_0`, `btn_1`. Keep them meaningful and don't renumber them; HAIR
  refers to a button by its key.
- **Each function needs a code**, given as either:
  - `pronto:` — a ready Pronto hex string, or
  - `raw:` — a list of signed microsecond timings (positive = mark,
    negative = space) plus an optional `frequency:` (default `38000`).
- **Decoded identity is optional but encouraged.** If you supply
  `protocol`, `address`, and `command`, HAIR stores the protocol, address,
  command, and a fingerprint next to the Pronto code instead of discarding
  them. `address`/`command` accept ints or hex strings (`0x04`).

Malformed files (or individual bad functions) are skipped with a warning in
the HA log — one broken file never breaks the picker. Files are cached and
only re-read when they change on disk.

## Ids

The picker emits ids you don't normally see, but for reference:

- codebook: `custom:<file_stem>` — e.g. `custom:my_remote`
- function: `custom:<file_stem>:<key>` — e.g. `custom:my_remote:power`

The `custom:` prefix is how HAIR routes a chosen code back to this source;
library codes use `lib:` instead.
