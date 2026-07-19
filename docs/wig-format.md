# The wig format (hair-wig/1)

A wig is a portable IR code set: one JSON file describing one remote. HAIR reads wigs from `/config/hair/wigs/`, and any tool can emit them. This page is the format contract; if you build something that writes wigs, this is everything you need.

## A complete example

```json
{
    "format": "hair-wig/1",
    "name": "Foxtel IQ",
    "brand": "Foxtel",
    "model": "IQ3",
    "notes": "Captured from an IQ3 remote, verified on hardware",
    "origin": "captured",
    "signals": [
        {
            "alias": "Power",
            "pronto": "0000 006d 0022 0002 ...",
            "send_count": 1
        }
    ]
}
```

## Rules

**Required fields:** `format`, `name`, and a non-empty `signals` list. Each signal requires `alias` and `pronto`. Everything else is optional.

**`format`** must be `"hair-wig/1"`. The major version gates parsing: a reader that sees a higher major version than it knows refuses the file and asks the user to update, rather than guessing.

**`pronto`** carries the raw Pronto hex code, and it is the entire payload. Deliberately, there are no decoded-protocol fields in the file: the importing HAIR install decodes every signal fresh through its own decoders, so a wig can never carry a stale or wrong identity, and it benefits from decoders that shipped after the wig was written. Codes must be valid learned-format Pronto (`0000` header, correct burst-pair length math); HAIR validates each one and rejects the file with a per-signal reason if any code is malformed.

**`send_count`** (optional, default 1) is how many times the whole signal transmits per press, for devices that need a repeat. Values are clamped to HAIR's supported range on import.

**`origin`** (optional, free-form string) records where the codes came from: `"captured"` for signals exported off real hardware, `"converted"` or `"converted:smartir"` for adapter output that never touched hardware, `"plucked"` or `"plucked:tuya_local"` for codes extracted live from a vendor blaster. HAIR uses this to explain a wig's provenance in the UI. If you write an adapter, stamp your own: `"converted:yourtool"`.

**Unknown keys are tolerated and preserved.** A reader ignores top-level and per-signal keys it does not recognize, and an editor that re-saves a wig keeps them. This is how the format grows without breaking old installs.

**Validation is all-or-nothing.** A file either validates completely or is rejected with concrete, field-level reasons (`signals[3].pronto: ...`). There is no such thing as a half-imported wig.

**Size cap:** 1 MB. A wig is text; this is generous.

**File naming:** `<slug>.wig.json`, lowercase, hyphen-separated (for example `foxtel-iq.wig.json`). HAIR only scans files ending in `.wig.json`.

## Canonical signals form

Future format features attach evidence to the exact codes in a wig (for example, a record that someone tested them on real hardware). Those features hash the `signals` array in a canonical form, defined from v1 so every install computes identical hashes:

- A JSON array of objects, in the wig's signal order.
- Each object carries exactly `alias`, `pronto`, and `send_count` (explicit even when 1); unknown keys are excluded.
- Keys sorted alphabetically, compact separators (no whitespace).
- `pronto` whitespace-normalized (single spaces between 4-digit words) and lowercased.

The hash form is `sha256:<hex digest>` over the UTF-8 encoding of that string. Nothing in `hair-wig/1` requires you to compute it; it is documented so files and tools written today stay compatible with what comes next.

## For adapter authors

Convert inbound only: read your source format, emit a wig. Wigs are HAIR's single canonical format, and nothing round-trips out except the wig itself. Do not bundle or redistribute another project's code database; convert files the user already holds.
