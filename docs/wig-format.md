# The wig format (hair-wig/1, hair-wig/2)

A wig is a portable IR code set: one JSON file describing one remote. HAIR reads wigs from `/config/hair/wigs/`, and any tool can emit them. This page is the format contract; if you build something that writes wigs, this is everything you need.

There are two versions, and the version follows the content. A wig of plain button signals is `hair-wig/1`, unchanged since 0.7.0, and every install that ever read wigs keeps reading it. A wig that carries a climate state matrix (added in HAIR 0.8.8) is `hair-wig/2`: everything in v1 plus the optional `climate` block documented below. An exporter must only write v2 when the wig actually has a climate block, so files never demand a newer reader than they need.

## A complete example

```json
{
    "format": "hair-wig/1",
    "name": "Foxtel IQ",
    "brand": "Foxtel",
    "model": "IQ3",
    "notes": "Captured from an IQ3 remote, verified on hardware",
    "kind": "settopbox",
    "origin": "captured",
    "identifiers": {
        "fcc_id": "SUW74000BT"
    },
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

**Required fields:** `format`, `name`, and a non-empty `signals` list. Each signal requires `alias` and `pronto`. Everything else is optional. One exception: a wig with a `climate` block may have an empty or absent `signals` list -- matrix-only wigs are legal, because the matrix is the payload and flat signals are the optional extras riding alongside it.

**`format`** must be `"hair-wig/1"` or `"hair-wig/2"`. The major version gates parsing: a reader that sees a higher major version than it knows refuses the file and asks the user to update, rather than guessing. Write v2 only when the wig carries a `climate` block; everything else stays v1.

**`pronto`** carries the raw Pronto hex code, and it is the entire payload. Deliberately, there are no decoded-protocol fields in the file: the importing HAIR install decodes every signal fresh through its own decoders, so a wig can never carry a stale or wrong identity, and it benefits from decoders that shipped after the wig was written. Codes must be valid learned-format Pronto (`0000` header, correct burst-pair length math); HAIR validates each one and rejects the file with a per-signal reason if any code is malformed.

**`send_count`** (optional, default 1) is how many times the whole signal transmits per press, for devices that need a repeat. Values are clamped to HAIR's supported range on import.

**`origin`** (optional, free-form string) records where the codes came from: `"captured"` for signals exported off real hardware, `"clipped"` for remotes assembled in HAIR's Clipper from pasted or library codes, `"device"` for a HAIR device's command set, `"converted"` or `"converted:smartir"` for adapter output that never touched hardware, `"plucked"` or `"plucked:tuya_local"` for codes extracted live from a vendor blaster. HAIR uses this to explain a wig's provenance in the UI. If you write an adapter, stamp your own: `"converted:yourtool"`.

**`kind`** (optional, added in HAIR 0.8.0) says what the device is: a short lowercase word with no separators, such as `tv`, `soundbar`, `settopbox`, `candles`, `fan`, `ac`. Brand and model say who made the device and which one; kind says what it is, which is what people search for when wigs are shared. Any value is accepted; HAIR suggests common ones and squashes whatever is entered to lowercase letters and digits (so `Sound Bar` and `sound-bar` both store as `soundbar`). HAIR asks for it once when a fitting is recorded on a wig that has none.

**`identifiers`** (optional, added in HAIR 0.8.0) is a map of product identity anchors, for hardware whose brand and model do not mean much. The devices only community code sets will ever cover are exactly the ones with no real brand: the marketplace candle set, the no-name fan. When present it must be an object; each value is a non-empty string or a non-empty array of non-empty strings, since rebadged device families often carry several UPCs or listings for the same hardware (`"upc": ["812345678901", "812345678902"]`). Keys are free-form; these four are the documented conventions:

- `fcc_id`: the FCC ID printed on the device or remote. The strongest anchor when present, since the public grantee record leads to the actual maker, internal photos, and manuals. Many IR-only remotes are exempt from FCC certification, so this is often absent, which is why it is one convention among several rather than a required field.
- `upc`: the barcode on the retail box (UPC or EAN digits). Nearly every product has one.
- `asin`: the Amazon listing identifier, when "sold on Amazon as X" is the only name the product has.
- `oem`: the established manufacturer, once someone has actually established it. Kept separate from `brand` on purpose: `brand` records what the box said, `oem` records what was verified, and the two should never overwrite each other. A confidently wrong manufacturer is worse than an honest unknown.

Identifiers are search anchors for humans, not machine identity. The codes themselves remain the strongest fingerprint a wig has: two rebadged units from the same maker share their protocol and device address no matter whose logo is on the shell, and HAIR derives that identity fresh from every wig. Fill in whatever you know; leave out what you do not.

**Unknown keys are tolerated and preserved.** A reader ignores top-level and per-signal keys it does not recognize, and an editor that re-saves a wig keeps them. This is how the format grows without breaking old installs.

**Validation is all-or-nothing.** A file either validates completely or is rejected with concrete, field-level reasons (`signals[3].pronto: ...`). There is no such thing as a half-imported wig.

**Size cap:** 16 MB. Raised from 1 MB in 0.8.8 for matrix wigs: a converted climate corpus file runs around 286 KB at the median and 7.9 MB at the worst case.

**File naming:** `<slug>.wig.json`, lowercase, hyphen-separated (for example `foxtel-iq.wig.json`). HAIR only scans files ending in `.wig.json`.

## The climate block (hair-wig/2)

Added in HAIR 0.8.8 for stateful devices, air conditioners above all. An AC remote does not send buttons: every press transmits the complete state the unit should be in, so the code set is a matrix -- one complete Pronto code per mode / fan / swing / temperature combination -- rather than a list of signals. The optional top-level `climate` object carries that matrix.

```json
"climate": {
    "min_temp": 16,
    "max_temp": 30,
    "precision": 1,
    "modes": ["cool", "heat", "fan_only"],
    "fan_modes": ["auto", "low", "high"],
    "swing_modes": ["off", "swing"],
    "off": "0000 006d 0022 0002 ...",
    "on": "0000 006d 0022 0002 ...",
    "cells": [
        {
            "mode": "cool",
            "fan": "auto",
            "swing": "off",
            "temp": 22,
            "pronto": "0000 006d 0022 0002 ..."
        }
    ]
}
```

The field rules:

- **`min_temp`** and **`max_temp`** are required numbers with `min_temp` below `max_temp`. **`precision`** (optional, default 1) is the temperature step, a positive number; a few real matrices step by 0.5.
- **`unit`** (optional) is `"C"` or `"F"`, defaulting to `"C"` -- the SmartIR corpus writes Celsius by convention, and a converter must not guess. It names the scale every temperature in the block is written in. Machine values stay file-native forever; displays convert dynamically to the install's unit, and names minted from a cell freeze in the minter's unit. HAIR's serializer emits the key only when it is `"F"`, so Celsius files stay byte-identical to files written before the key existed.
- **`modes`**, **`fan_modes`**, **`swing_modes`** (optional lists of non-empty strings) declare the vocabularies in display order. Vocabulary strings are VERBATIM everywhere: they are lookup keys and entity attribute values at once, so a reader or writer must never case-normalize or respell them.
- **`off`** is required and **`on`** is optional; both are complete-state Pronto codes, validated like any signal. Many real matrices carry only `off` because any cell send implies on.
- **`cells`** is a required non-empty list. Each cell requires `mode` (non-empty string) and `pronto` (valid Pronto); `fan`, `swing`, and `temp` are each optional, and `send_count` (optional, default 1) works exactly as it does on signals. Dimensions vary per branch: one mode subtree can carry fan / swing / temp while another is a bare one-code mode, so a cell simply omits the dimensions its branch does not have. A cell's canonical key is its coordinates joined by `/` with absent dimensions omitted -- `cool/auto/23`, or a bare `fan_only`.
- **Sparse matrices are honest.** A combination the device cannot do is simply not a cell. Readers must not invent, interpolate, or snap to invented states; HAIR sends nothing on a sparse miss.
- Unknown keys inside `climate` and inside each cell are tolerated and preserved, the same growth rule as everywhere else in the format.

A wig may carry a matrix, flat `signals`, or both. The flat signals alongside a matrix are the depth-0 extras (sleep timers, LED toggles, one-shot codes) that are buttons, not states.

## Canonical signals form

Fittings (below) attach evidence to the exact codes in a wig. For a signal wig they hash the `signals` array in a canonical form, defined from v1 so every install computes identical hashes:

- A JSON array of objects, in the wig's signal order.
- Each object carries exactly `alias`, `pronto`, and `send_count` (explicit even when 1); unknown keys are excluded.
- Keys sorted alphabetically, compact separators (no whitespace).
- `pronto` whitespace-normalized (single spaces between 4-digit words) and lowercased.

The hash form is `sha256:<hex digest>` over the UTF-8 encoding of that string. Nothing in `hair-wig/1` requires you to compute it; it is documented so files and tools written today stay compatible with what comes next.

## Canonical cells form

Matrix fittings bind to the matrix, so `hair-wig/2` defines a canonical form for the climate block, with the same posture as the signals form:

- A JSON object carrying exactly `unit`, `off`, `on`, and `cells`.
- `cells` is an array of objects in the wig's cell order; each object carries exactly `mode`, `fan`, `swing`, `temp`, `pronto`, and `send_count`, with absent dimensions as explicit `null` and `send_count` explicit even when 1. Unknown keys are excluded.
- Every Pronto (`off`, `on`, each cell) whitespace-normalized to single spaces and lowercased; an absent `on` is `null`.
- Keys sorted alphabetically, compact separators (no whitespace).
- `unit` participates on purpose: the same numbers on a different scale are different states, so a 22 C lattice and a 22 F lattice can never share a fitting ledger.

The hash form is again `sha256:<hex digest>` over the UTF-8 encoding. Which hash a fitting binds to follows the wig's type: signal wigs use the canonical signals hash, matrix wigs use the canonical cells hash. The flat extras riding alongside a matrix are outside the cells hash -- renaming an extra never invalidates a matrix fitting, and changing any cell always does.

## Fittings

Added in HAIR 0.8.0. A fitting records that a person sent a wig's signals at real hardware and marked, signal by signal, whether the device responded. Fittings live in an optional top-level `fittings` array; readers that do not know the key carry it through unchanged under the unknown-keys rule.

```json
"fittings": [
    {
        "handle": "dab",
        "github": "DAB-LABS",
        "date": "2026-07-27",
        "hair_version": "0.8.0",
        "ha_version": "2026.7.2",
        "emitter": "broadlink",
        "receiver": "esphome",
        "confirmed": ["Power On", "Power Off"],
        "failed": [],
        "signals_heard": 2,
        "send_times_used": 3,
        "content_hash": "sha256:...",
        "key": "<base64 ed25519 public key>",
        "sig": "<base64 ed25519 signature>"
    }
]
```

The load-bearing rules:

- `confirmed` and `failed` are row-key lists, not counts. Anything in neither list was not tested. For a signal wig the keys are aliases, exactly as before 0.8.8. For a matrix wig the keys are cell keys (`cool/auto/23` -- coordinates joined by `/`, absent dimensions omitted, whole-number temps written bare and half-degree temps with their decimal) plus the literal `on` and `off` for the power codes.
- `content_hash` is the wig's canonical hash above (signals hash for signal wigs, cells hash for matrix wigs), computed when the fitting was made. If the hashed content changes afterward (including an alias rename on a signal wig, or any cell change on a matrix wig), the hash no longer matches and the fitting is displayed as outdated rather than silently claiming codes it never saw.
- A fitting is **complete** when `confirmed` covers every fitting row of the wig and `failed` is empty. For a signal wig the rows are its signals, one each. For a matrix wig the rows are the **dimension checklist**: a deterministic 12-to-20-row walk derived purely from the climate block that covers the on code, one representative cell per mode, every fan speed and every swing position in the richest mode, the coldest and warmest temperatures, and the off code last. The checklist attests that each dimension works along its own axis; it does not claim every cell was individually fired, and the flat extras alongside a matrix are not rows at all. HAIR only lets complete fittings travel: its download and share paths strip incomplete or in-progress fittings, so a shared wig carries whole claims or none.
- `send_times_used` (optional, added in HAIR 0.9.0) records how many times each signal was transmitted per press during this fitting: the value of the session's send-times control, raised when a device does not respond to a single send. It is evidence about the fitter's conditions (distance, blaster power, angle), never a rewrite of any signal's `send_count` -- it sits on the fitting entry, outside both canonical hashes, so recording it cannot invalidate anything. **Absent is not 1**: a fitting without the field predates it (or came from a tool that does not write it) and claims nothing, while an explicit `1` means the fitter had the control and one send was enough. Readers clamp the value to 1..10 on read. Consumers aggregate across complete fittings by taking the **maximum**, never the mean -- send times is a threshold ("at least N to be reliable"), and HAIR's ADOPT DEVICE seeds new commands and matrix cells from that maximum, with the wig's own `send_count` winning where higher. On a matrix wig the value attests the sampled dimension checklist, not every cell in the lattice.
- `key` and `sig` are optional. When present, `sig` is an ed25519 signature over the fitting object minus `sig` (with `key` included), serialized with sorted keys, compact separators, UTF-8. The key pair is generated on the fitting install; a valid signature means the fitting has not been altered since it was recorded there. Unsigned fittings are valid; they are simply self-reported.
- Fittings are social proof, not cryptographic identity. The handle is what the fitter typed; the GitHub handle is checkable by asking that person; the signature proves the record is unaltered and that fittings sharing a key came from one install.

## Replace: provenance and carry

Added in HAIR 0.9.5. When a fitter replaces a code from the fitting session -- pasting a Pronto, or capturing one from the real remote -- HAIR records two things. Both are **optional conventions riding in `extra` maps, outside every canonical hash**, so a reader that does not know them carries them through unchanged and neither one can move a wig's identity.

**The provenance marker** says where a code came from, on the thing that changed:

```json
{"alias": "Power On", "pronto": "0000 ...", "provenance": {"replaced": "captured", "date": "2026-07-31"}}
```

- It rides the **signal** object on a signal wig and the **cell** object on a matrix wig. The two matrix power codes are not cells, so their markers ride the climate block instead, under `provenance_power` keyed by `on` and `off`.
- `replaced` is `captured` (off real hardware, through a receiver) or `pasted` (user-supplied bytes, unverified until fitted). A later release adds `rule-derived` for regenerated codes.
- A repeat replace overwrites the marker; latest wins, and the marker never leaves the file once present.
- A marker always implies the wig's hash rolled, because replacing a code with the identical code is refused rather than stamped. On a matrix wig, HAIR appends every marked cell the dimension checklist does not already cover to the fitting session as a **changed codes** row, so the human proves exactly what was touched; that is only safe while the implication holds.

**The replaced-from record** keeps the code the row used to hold, so a repair can be undone:

```json
"replaced_from": {
    "Power On": {"pronto": "0000 ...", "provenance": null, "by": "dab", "to": "0000 ...", "session": false}
}
```

- One entry per replaced row, keyed by fitting row key. `pronto` and `provenance` are what the row held **before the first replace**, and later replaces never overwrite them, so putting a row back always means the code the wig came with rather than whatever a previous repair attempt left behind.
- `to` is the code the most recent replace wrote. A put-back only proceeds while the row still holds it; anything else means the file was edited outside this machinery and the record no longer describes it.
- `by` and `session` mark whose current session the replace belongs to. Discarding a session puts back only that user's rows; signing sets `session` to false, which closes them to a later discard without removing the record.
- The record is **not** removed at signing, so a repair that was proved and later turned out wrong can still be undone. Putting a row back rolls the hash to what it was, which correctly marks any fitting that attested the replaced code as outdated. The entry is dropped when the row goes back, because a row holding its original code has nothing left to return to.
- On the share paths the codes travel and the session bookkeeping does not: `by` and `session` are dropped, so a recipient can still put a row back but nobody's in-progress session follows the file to another install.

**The carry map** lets the next session keep the verdicts that are still true:

```json
"carry": {"sha256:<superseded hash>": {"Power On": "9f2c1a...", "Power Off": "40b7de..."}}
```

- One entry per superseded content hash, taken at the moment that hash was replaced away from. Each value maps a fitting row key to a truncated SHA-256 of that row's normalized Pronto, so byte-identity is provable without storing the codes twice.
- A new session seeds its verdicts from the fitter's last fitting for every row whose key and code digest both still match. Rows whose code changed, and rows whose key changed, come back untested. Without a carry entry nothing is seeded: matching on the key alone would carry a verdict onto bytes it never attested.
- Entries no fitting references are pruned on the next replace, and the share paths drop any whose fitting was stripped: a snapshot exists to seed a session against an attestation, so it never travels without one.

## The comb receipt

Added in HAIR 0.9.5. **Combing** checks that a wig's codes agree with each other: frame-shape uniformity, partial row collapse, gaps in a captured temperature run, coordinate uniqueness, and duplicate-label groups. It runs at import on every wig and on demand from the closet, and it **never changes a code** -- it reports.

The result is stored on `wig.extra["comb"]`, an optional extra-key convention **outside every canonical hash**, so recording a result can never move a wig's identity or invalidate a fitting:

```json
"comb": {
    "version": 1,
    "date": "2026-07-31",
    "suspects": 48,
    "counts": {"duplicated-neighbour": 1, "malformed": 34, "stray-burst": 13},
    "findings": [
        {"check": "malformed", "keys": ["heat/low/19"], "message": "comb.frame_short",
         "params": {"frame": "0", "timings": "2"}}
    ]
}
```

- `suspects` counts findings a human should look at. **Advisories are not suspects**: a flat file legitimately puts one code under two names on a toggle remote, so `duplicate-labels` is reported and never counted.
- `message` is a localization key and `params` its substitutions. Findings never carry prebaked English, so a diagnosis renders in the reader's language.
- `findings` is capped at 200 entries with a `truncated` count of the remainder; `counts` and `suspects` always describe the full result.
- **An absent `comb` key means nobody has combed the wig**, which is deliberately not the same as clean. A wig that was combed and came back empty carries a receipt with `suspects: 0`.
- A receipt describes the codes as they were when it was written. A REPLACE changes codes without touching the receipt, so a stale receipt is expected and combing again is what refreshes it.

## For adapter authors

Convert inbound only: read your source format, emit a wig. Wigs are HAIR's single canonical format, and nothing round-trips out except the wig itself. Do not bundle or redistribute another project's code database; convert files the user already holds.
