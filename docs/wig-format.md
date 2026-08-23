# The wig format (hair-wig/3)

A wig is a portable IR code set: one JSON file describing one remote. HAIR reads wigs from `/config/hair/wigs/`, and any tool can emit them. This page is the format contract; if you build something that writes wigs, this is everything you need.

The current version is `hair-wig/3`, and it is the only version to write: HAIR emits it for every wig, plain button sets and climate matrices alike, and new files -- including anything submitted to the WigShop -- must declare it. It supersedes `hair-wig/1` and `hair-wig/2`; the short history of those majors, and how existing old files are handled, lives in the collapsed section near the bottom.

## A complete example

```json
{
    "format": "hair-wig/3",
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
            "ditto_count": 0,
            "bypass_protocol": false,
            "send_count": 1
        }
    ]
}
```

## Rules

**Required fields:** `format`, `name`, and a non-empty `signals` list. Each signal requires `alias` and `pronto`. Everything else is optional. One exception: a wig with a `climate` block may have an empty or absent `signals` list -- matrix-only wigs are legal, because the matrix is the payload and flat signals are the optional extras riding alongside it.

**`format`** must be `"hair-wig/3"` for any file written today. The major version gates parsing: a reader that sees a higher major version than it knows refuses the file and asks the user to update, rather than guessing. Readers below 3 refuse a v3 file with a version message, and that refusal is the point: without it an older reader would compute the previous canonical form, see a mismatch, and report what looks like tampering on a perfectly good file, which is the worst possible thing to tell someone about a file they trust. (For what v3 changed and how the superseded majors are handled, see the collapsed section near the bottom.)

**`pronto`** carries the raw Pronto hex code, and it is the entire payload. Deliberately, there are no decoded-protocol fields in the file: the importing HAIR install decodes every signal fresh through its own decoders, so a wig can never carry a stale or wrong identity, and it benefits from decoders that shipped after the wig was written. Codes must be valid learned-format Pronto (`0000` header, correct burst-pair length math); HAIR validates each one and rejects the file with a per-signal reason if any code is malformed.

**`send_count`** (optional, default 1) is how many times the whole signal transmits per press, for devices that need a repeat. Values are clamped to HAIR's supported range on import.

From `hair-wig/3` it is a **ride-along**: carried, clamped, used to seed an adopted device, and deliberately **outside the content hash**. A claim has never attested it -- how many times a proof pressed was never part of what was proved -- and pinning a number nobody proved was the wrong kind of protection. The consequence is intended: five people proving the same codes at 3, 4, 3, 5 and 4 sends are proving the *same wig*, so their fittings accumulate on one file instead of forking it five ways. The honest cost is that someone can edit a send count on a signed wig and the signature still verifies. That edit is loud, locally fixable, and clamped on import; the protection budget goes to the flips that can make a device silently fail while still looking certified.

**`ditto_count`** (integer, added in `hair-wig/3`, always written explicitly) is how many repeat frames the encoder appends to each transmitted frame. Range 0..20, clamped on read; absent in a hand-made file reads as 0. It is **in the content hash**, because dittos change the waveform and the fitting transmits them.

A ditto is specifically the **NEC** repeat frame, and HAIR's editors only offer the field on a signal that decodes as NEC. The rule was measured rather than assumed, by counting the timings each protocol emits as the repeat count rises from 0 to 1 to 3: NEC goes 67, 71, 79, appending a four-entry frame each time. Samsung32 goes 67, 135, 271 and RC-5 goes 21, 43, 87 -- both duplicating the entire frame, which is what `send_count` already does, except from inside the hash where a delivery detail does not belong. Sharp and Sony do not move at all; they ignore the count, so a file carrying one would hash a number that never reaches the wire. A non-NEC signal should therefore always read 0. Files that carry otherwise still parse and still display their value, because a number hidden is a number nobody can find and correct.

It is named `ditto_count` rather than `repeat_count` on purpose. Inside HAIR dittos are called `repeat_count` while humans say "repeats" for send counts, and the portable format is the one place that ambiguity can be killed. The export boundary maps a device command's `repeat_count` onto this field, exactly as it maps `tx_force_raw` onto `bypass_protocol`.

Dittos are device grammar rather than environment. A strict receiver rejects a lone frame and needs the key-held pattern -- frame plus at least one repeat -- before it commits to a press, and standing closer does not change what a decoder chip demands. Send counts are the opposite: they answer "does the signal arrive", which is why one is hashed and the other is not.

`ditto_count` and `bypass_protocol` are **mutually exclusive**. A raw blob has no ditto grammar -- only the encoder can render a shortened repeat frame -- so HAIR's exporter writes `ditto_count: 0` on any pinned signal and reports the drop rather than doing it quietly. A hand-made file carrying both parses, and the code checker raises an advisory.

**`origin`** (optional, free-form string) records where the codes came from: `"captured"` for signals exported off real hardware, `"clipped"` for remotes assembled in HAIR's Clipper from pasted or library codes, `"device"` for a HAIR device's command set, `"converted"` or `"converted:smartir"` for adapter output that never touched hardware, `"plucked"` or `"plucked:tuya_local"` for codes extracted live from a vendor blaster. HAIR uses this to explain a wig's provenance in the UI. If you write an adapter, stamp your own: `"converted:yourtool"`.

**`kind`** (optional, added in HAIR 0.8.0) says what the device is: a short lowercase word with no separators, such as `tv`, `soundbar`, `settopbox`, `candles`, `fan`, `ac`. Brand and model say who made the device and which one; kind says what it is, which is what people search for when wigs are shared. Any value is accepted; HAIR suggests common ones and squashes whatever is entered to lowercase letters and digits (so `Sound Bar` and `sound-bar` both store as `soundbar`). HAIR asks for it once when a fitting is recorded on a wig that has none.

**`identifiers`** (optional, added in HAIR 0.8.0) is a map of product identity anchors, for hardware whose brand and model do not mean much. The devices only community code sets will ever cover are exactly the ones with no real brand: the marketplace candle set, the no-name fan. When present it must be an object; each value is a non-empty string or a non-empty array of non-empty strings, since rebadged device families often carry several UPCs or listings for the same hardware (`"upc": ["812345678901", "812345678902"]`). Keys are free-form; these four are the documented conventions:

- `fcc_id`: the FCC ID printed on the device or remote. The strongest anchor when present, since the public grantee record leads to the actual maker, internal photos, and manuals. Many IR-only remotes are exempt from FCC certification, so this is often absent, which is why it is one convention among several rather than a required field.
- `upc`: the barcode on the retail box (UPC or EAN digits). Nearly every product has one.
- `asin`: the Amazon listing identifier, when "sold on Amazon as X" is the only name the product has.
- `oem`: the established manufacturer, once someone has actually established it. Kept separate from `brand` on purpose: `brand` records what the box said, `oem` records what was verified, and the two should never overwrite each other. A confidently wrong manufacturer is worse than an honest unknown.

Identifiers are search anchors for humans, not machine identity. The codes themselves remain the strongest fingerprint a wig has: two rebadged units from the same maker share their protocol and device address no matter whose logo is on the shell, and HAIR derives that identity fresh from every wig. Fill in whatever you know; leave out what you do not.

**`supersedes`** (optional top-level list, added in HAIR 0.9.7) is the wig's ancestry: wig ids newest first, naming the wig this one grew out of and that wig's own ancestors before it. Supersession is declared by the successor and never marked on the ancestor -- copies of the old file sit in closets nobody can reach, so the lineage has to ride on the file that travels. Save as new stamps it automatically, prepending the source wig's id onto the source's own ancestry; a from-scratch wig carries none. A reader uses it at the drop bar: an arriving wig whose ancestry names a wig already in the closet is offered as a replacement for that ancestor rather than filed as a twin. A bare string is accepted as a one-element list, and the list is capped at 16 ids at both ends, the oldest dropped first when it overflows. Like all metadata it is **outside every canonical form and every digest**, so lineage can never move a wig's identity or disturb a claim; it joins the known-key list beside `converted_from`, and an older reader round-trips it untouched under the unknown-keys rule.

**`bypass_protocol`** (optional per-signal boolean, added in HAIR 0.9.2) says *send these bytes verbatim; do not decode and re-encode them*. Normally an importing HAIR decodes each signal fresh and transmits clean rebuilt timings, which strips receiver distortion and is almost always right. It is wrong when a capture has its repeats baked in: some devices want a burst of frames, and rebuilding one clean frame from the decoded value throws the rest away, so the device does nothing. The field exists so that intent travels with the codes instead of being rediscovered by whoever imports the wig next.

It asserts nothing about protocol identity, only that these bytes are the payload. That is why it does not violate the no-decoded-fields rule: it cannot go stale against a better future decoder. `send_count` stays orthogonal (a bypassed signal can still repeat the whole blob N times), and carrier handling is unchanged. It bypasses the codec, not all processing.

Two rules ride with it:

- **It is IN the canonical hash, always explicitly.** It changes what transmits, so leaving it out would let someone alter a fitted wig's send behaviour while its signature still verified. HAIR 0.9.2 emitted it only when true, to avoid rolling every existing hash at once; `hair-wig/3` retired that shortcut in the same break that took the hash roll anyway, so the canonicalization spec now has zero conditional rules.
- **An older HAIR preserves it.** A reader that predates the field parses it as an unknown per-signal key, round-trips it on export, and excludes it from the hash. That install transmits the code the old way, and its fitting reads as not matching rather than silently attesting a code it sent differently.

**Unknown keys are tolerated and preserved.** A reader ignores top-level and per-signal keys it does not recognize, and an editor that re-saves a wig keeps them. This is how the format grows without breaking old installs.

**Validation is all-or-nothing.** A file either validates completely or is rejected with concrete, field-level reasons (`signals[3].pronto: ...`). There is no such thing as a half-imported wig.

**Size cap:** 16 MB. Raised from 1 MB in 0.8.8 for matrix wigs: a converted climate corpus file runs around 286 KB at the median and 7.9 MB at the worst case.

**File naming:** `<slug>.wig.json`, lowercase, hyphen-separated (for example `foxtel-iq.wig.json`). HAIR only scans files ending in `.wig.json`.

## The climate block

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

A canonical form for the `signals` array, so every install computes identical hashes. As of 0.9.5 a flat wig's claims bind per-row digests instead (see Row digests below) and nothing in HAIR writes a wig-level signals hash any more, but the form stays specified: it is what tools built against the superseded majors computed, and dropping the definition would leave those files undecipherable.

The rule that decides what belongs here: **the hash covers what the fitting proves.** A fitting's signature certifies that this content drove the device when a named person pressed the buttons, so it covers exactly the waveform that left the blaster -- the bytes, the repeat frames appended to them, and whether the encoder was bypassed -- and nothing else. Delivery decisions such as how many times to press live outside it.

The form is a portability contract. Any tool that computes or verifies one must reproduce it byte-for-byte:

- A JSON array of objects, in the wig's signal order.
- Each object carries exactly **four** keys -- `alias`, `pronto`, `ditto_count`, `bypass_protocol` -- every field, every signal, every time. No conditional rules, no omissions. `send_count` does not appear. Unknown keys are excluded.
- Keys sorted alphabetically, compact separators (no whitespace).
- `pronto` whitespace-normalized (single spaces between 4-digit words) and lowercased.

The hash form is `sha256:<hex digest>` over the UTF-8 encoding of that string. Nothing requires a writer to compute it; it is documented so files and tools written today stay compatible with what comes next.

## Canonical cells form

Matrix fittings bind to the matrix, so the format defines a canonical form for the climate block, with the same posture as the signals form:

- A JSON object carrying exactly `unit`, `off`, `on`, and `cells`.
- `cells` is an array of objects in the wig's cell order; each object carries exactly `mode`, `fan`, `swing`, `temp`, and `pronto`, with absent dimensions as explicit `null`. Unknown keys are excluded. `send_count` left this object in the same break that removed it from signals, for the same reason: the dimension checklist never transmitted it. Cells carry no `ditto_count` at all, because dittos are an NEC-family frame construct and an air-conditioner state blob is one long frame.
- Every Pronto (`off`, `on`, each cell) whitespace-normalized to single spaces and lowercased; an absent `on` is `null`.
- Keys sorted alphabetically, compact separators (no whitespace).
- `unit` participates on purpose: the same numbers on a different scale are different states, so a 22 C lattice and a 22 F lattice can never share a fitting ledger.

The hash form is again `sha256:<hex digest>` over the UTF-8 encoding. Which hash a fitting binds to follows the wig's type: signal wigs use the canonical signals hash, matrix wigs use the canonical cells hash. The flat extras riding alongside a matrix are outside the cells hash -- renaming an extra never invalidates a matrix fitting, and changing any cell always does.

## Row digests

Added in HAIR 0.9.5, and the foundation everything below stands on. A **row digest** identifies one row by its transmit recipe:

```
sha256(normalized_pronto + "|d<ditto_count>" + "|b<0|1>")   truncated to 16 hex characters
```

Exact layout, so any external verifier reproduces it byte for byte: the normalized Pronto, then `|d` and the integer ditto count, then `|b1` when the encoder is bypassed or `|b0` when it is not. `normalized_pronto` is the same normalization the canonical forms use, single spaces between 4-digit words and lowercased.

**`alias` is out, and must never be added.** Names are metadata, renames are free, and a claim has to survive one.

**`send_count` is out, and must never be added.** How many times to press depends on the room rather than the device, so two people proving the same codes at three sends and at five are proving the same thing.

What is in is exactly what changes the waveform: the bytes, the repeat frames appended to them, and whether the encoder is bypassed. That is the set a claim needs to bind, because it is the set that decides what leaves the emitter.

## Claims

Added in HAIR 0.9.5, replacing the whole-file fittings of 0.8.0. A **claims bundle** is one person's signed set of per-row claims, made in one sitting about one wig. Bundles live in the same optional top-level `fittings` array, and readers that do not know the key carry it through unchanged under the unknown-keys rule.

```json
"fittings": [
    {
        "wig_id": "0d0f2e6c-...",
        "handle": "dab",
        "github": "DAB-LABS",
        "date": "2026-08-03",
        "note": "Tested on the 2019 model",
        "rows": [
            {"alias_at_claim": "Power On", "digest": "9f2c1a4b7e05d318", "verdict": "worked"},
            {"alias_at_claim": "Sleep", "digest": "40b7de91c2a6f085", "verdict": "not_on_device"}
        ],
        "key": "<base64 ed25519 public key>",
        "sig": "<base64 ed25519 signature>"
    }
]
```

The load-bearing rules:

- **A claim binds a row's recipe, not the file.** Each entry in `rows` carries a `digest` and a `verdict`. Editing one row leaves every other row's claim intact, which is the whole reason the model changed: a whole-file hash says "these bytes, all of them" and carries no information about which rows anybody proved.
- `verdict` is `worked`, `not_on_device`, or `wont_work`. The last two are **exclusions rather than failures**: a row the fitter's hardware does not have, and a row they could not make work. A row with no claim at all was simply not tested.
- `alias_at_claim` is the row's name when it was claimed. **Display context only** -- it is not in the digest, so a later rename cannot invalidate the claim, and it is what lets HAIR say "the wig calls this On, you called it Power" instead of silently orphaning a row.
- A claim whose digest matches no row in the file is shown as **orphaned** rather than dropped. Somebody really did prove that recipe; it just is not the recipe on the file any more, and hiding that would let a ledger read as coverage it does not have.
- **THERE IS NO WIG-LEVEL CONTENT HASH ON A FLAT WIG.** Row digests are the whole binding, and adding a file hash back would re-import the problem they exist to solve. A bundle carrying `content_hash` is a pre-0.9.5 fitting by definition, and that shape is the discriminator: the format stamp describes what a reader needs, not what is in the block, and the two demonstrably drift.
- **A matrix bundle pins its lattice with `cells_hash`,** never `content_hash`. A dimension checklist samples a lattice, so the claim is about the set and not only the rows walked; if the lattice moved, the sample no longer describes it. This is also why the two names never overlap, so the legacy test stays a single check.
- `key` and `sig` are optional. When present, `sig` is an ed25519 signature over the bundle minus `sig` (with `key` included), serialized with sorted keys, compact separators, UTF-8. A bad signature discredits the **attribution**, never the data: the claims are still on the file and still legible, and what is in doubt is whether this person made them.
- Claims are social proof, not cryptographic identity. The handle is what the fitter typed, the GitHub handle is checkable by asking that person, and the signature proves the record is unaltered and that bundles sharing a key came from one install.

### Perfect fit and coverage are derived, never stored

Nothing in the file records "this wig is proven". A bundle is **complete** when its claims cover every row of the wig: for a flat wig, every row digest; for a matrix wig, every checklist row carrying `worked`. Completeness is computed from the claims and the file in front of you, so it cannot go stale and cannot be asserted by a file that has since changed.

The closet's check has three tiers, computed the same way:

| Tier | What it means |
|---|---|
| none | No attestations at all. |
| scoped | At least one signed attestation, none of them complete. |
| perfect | **One person's** claims cover every row. |

**Downloads carry the tier in the filename.** Since v0.9.8 there are two names: `name.wig.json` for anything short of a complete fitting, and `name.perfect-fit.wig.json` when at least one person's claims cover every row. (Earlier versions also emitted `name.fitted.wig.json` for signed-but-incomplete attestations; those files still parse everywhere and their claims list as Incomplete.) The name is presentation only -- the file contents are identical across tiers, an importing install never reads the name, and renaming the file changes nothing.

**Green is keyed to one person's complete coverage.** Union coverage across fitters never inflates it: three people who each proved a different third have not, between them, produced anybody who can say the whole wig works on their hardware. That union is real and worth knowing, and it is tooltip material rather than a colour.

### Pre-0.9.5 fittings

Old whole-file fittings are **dropped on import**, with a notice saying how many went. They cannot be converted: a `content_hash` records that some bytes were proved, not which rows, so there is no honest way to turn one into per-row claims. Re-fitting takes a few minutes; a fabricated claim lasts forever.

## Retired conventions

HAIR 0.9.1 wrote three bookkeeping conventions into `extra` maps during fitting-session repairs: a `provenance` marker recording where a replaced code came from, a `replaced_from` record keeping the code a row used to hold, and a `carry` map seeding the next fitting session's verdicts. All three served the whole-file attestation model and were retired with it in 0.9.5 -- nothing writes them any more, and nothing reads them.

A file written by 0.9.1 may still carry them. They were always outside every canonical form, so they cannot move a wig's identity; a reader treats them like any other unknown `extra` data and passes them through unchanged.

## The comb receipt

Added in HAIR 0.9.1. **Combing** checks that a wig's codes agree with each other: frame-shape uniformity, partial row collapse, gaps in a captured temperature run, coordinate uniqueness, duplicate-label groups, and, from receipt version 2, whether a code's own repeat frames agree with each other. It runs at import on every wig and on demand from the closet, and it **never changes a code** -- it reports.

Those checks are all **protocol-blind**: they compare codes to their neighbours without reading a single byte of what a code says. A second tier, added alongside them, reads the payload against a **field map** and compares it to what the cell's own coordinates claim -- the check that catches a lattice whose 24-degree cell sends 25. It is strictly additive: it files its own two check classes, it declines loudly wherever it cannot read, and a wig no map covers combs exactly as it did before.

The result is stored on `wig.extra["comb"]`, an optional extra-key convention **outside every canonical hash**, so recording a result can never move a wig's identity or invalidate a fitting:

```json
"comb": {
    "version": 2,
    "date": "2026-07-31",
    "suspects": 48,
    "counts": {"duplicated-neighbour": 1, "malformed": 34, "stray-burst": 13},
    "findings": [
        {"check": "malformed", "keys": ["heat/low/19"], "message": "comb.frame_short",
         "params": {"frame": "0", "timings": "2"}}
    ],
    "coverage": {
        "codes": 1157,
        "checked": 1157,
        "checks": {
            "frame-shape": {"checked": 1157, "declined": {}},
            "duplicated-neighbour": {"checked": 1156, "declined": {}},
            "frame-disagreement": {"checked": 0, "declined": {"too-few-frames": 1157}},
            "field-mismatch": {"checked": 1156, "declined": {"no-coordinate": 1}},
            "frame-integrity": {"checked": 1157, "declined": {}}
        },
        "protocol": {"id": "ZHLT01", "codes": 1157, "readable": 1157, "declined": {}},
        "fields": {
            "power": {"checked": 1157, "declined": {}},
            "temperature": {"checked": 816,
                            "declined": {"mode-temp-frozen": 340, "no-coordinate": 1}},
            "mode": {"checked": 0, "declined": {"field-provisional": 1156,
                                                "no-coordinate": 1}}
        }
    }
}
```

- `suspects` counts findings a human should look at. **Advisories are not suspects**: a flat file legitimately puts one code under two names on a toggle remote, so `duplicate-labels` is reported and never counted.
- `message` is a localization key and `params` its substitutions. Findings never carry prebaked English, so a diagnosis renders in the reader's language.
- `findings` is capped at 200 entries with a `truncated` count of the remainder; `counts` and `suspects` always describe the full result.
- **An absent `comb` key means nobody has combed the wig**, which is deliberately not the same as clean. A wig that was combed and came back empty carries a receipt with `suspects: 0`.
- `coverage` (receipt version 2) records **what the comb looked at and what it declined to look at**, per check id: `checked` counts the codes a check judged, and `declined` tallies the ones it could not, by reason. `codes` is every code in the wig and the top-level `checked` is how many of them at least one check judged. Reasons are stable identifiers, localized for display: `pinned-to-raw`, `unparseable`, `single-frame`, `separator-unclear`, `too-few-frames`, `too-few-codes`, `no-lattice`, `row-too-short`, `no-temperature`.
- `single-frame` and `separator-unclear` are both "nothing was compared", and the difference between them is worth keeping. `single-frame` means no repeat boundary was found in the timings. `separator-unclear` means something in the code was shaped like one and could not be trusted as one -- a space long enough to be a boundary that is too common to be anything but data, or a split whose pieces turned out to be fragments rather than repeats. Some families make that ambiguity unavoidable: Mitsubishi Heavy writes a one-bit as roughly 3600 us and separates two presses by roughly 7600 us, so depending on how many one-bits a code carries, either the bits look like boundaries or the boundary looks like a bit. Neither is reported as checked.
- `protocol` and `fields` are the **field tier's** half of coverage, written whenever that tier ran. `protocol` names the map that identified the codes (`id: null` when none did), how many codes there were, and how many of them the map could actually read; `fields` reports, per field the map declares, how many codes the sweep compared and what it declined. Both are absent from a receipt written before the tier existed, which is the same honest absence a version 1 receipt has for `coverage` itself.
- **A family has to carry the wig.** Identification is a vote across all of a wig's codes, not a first match: the winning map must be claimed by at least a quarter of them, and by at least two. At a few hundred bits a lone coincidence is close to inevitable, and one accidental match naming the family for a whole remote is how a reader ends up with findings about a protocol nobody mapped. A candidate that appears and does not clear the bar is recorded in `protocol.rejected` as `{map id: codes}` rather than dropped, because a near miss is worth a reader's attention.
- **`id: null` is the loud case, not the quiet one.** A wig no map covers passes every protocol-blind check and has not one byte of its payload read, so its structural `checked` is a full count of a much narrower question. The closet draws that state differently from clean, and the report says it in words: *no field map covers this protocol: 0 of N codes had their contents checked*.
- Field-tier decline reasons are stable identifiers alongside the structural ones: `protocol-unmapped`, `unreadable-frame`, `field-provisional`, `no-coordinate`, `not-applicable`, `mode-temp-invariant`, `mode-temp-frozen`, `mode-fan-forced`, `unknown-label`, `out-of-domain`, `field-absent`, `rule-unevaluable`, `no-labels`.
- **`unreadable-frame` is never a skip and never a guess.** A map carries the timing alphabet its family uses, and a pulse that falls outside every window it declares means the frame was not understood -- so identification fails and the code lands in coverage. Nothing downstream is inferred from a frame that could not be split, because a wrong split reads as a wrong byte, and a wrong byte reads as a finding about a file that was fine.
- **`field-provisional` is the confidence gate.** A field map records how sure each field and each integrity rule is, derived across a whole family of files; only fields marked ratified join the sweep. A provisional field is real information and it is not evidence: ZHLT01's own family disagrees about two of its mode values, so sweeping mode on a wig that follows the minority reading would file a thousand findings that say nothing about that wig.
- **`mode-temp-frozen` is decided per wig, not per map.** Some families hold one setpoint in dry or fan-only and carry a real one in others, and the map says exactly that (`file_dependent`) rather than picking. Whether a given wig's column moves is then read off that wig's own cells. Skipping a column that moves would miss a shifted setpoint; checking one that does not would invent thirty findings about a mode that never had a temperature.
- **`frame-integrity` needs no labels.** Where a flat wig's codes identify under a map, the map's checksum and complement rules run on them too and report in coverage; only the field-versus-label comparison needs a lattice, and on a flat wig it declines with `no-labels`.
- **Coverage is why a clean receipt is readable at all.** A check that quietly says nothing about a code it could not read is indistinguishable from a check that read it and approved, and the second claim is much stronger than the first. A reader that shows `suspects: 0` without showing coverage is overstating the receipt.
- **A version 1 receipt has no `coverage` key and that absence is the honest answer**, not an empty one: a receipt written before coverage existed cannot say what it did not check. Version 1 receipts still parse and still display; combing again writes a version 2 receipt in place.
- A receipt describes the codes as they were when it was written. A REPLACE changes codes without touching the receipt, so a stale receipt is expected and combing again is what refreshes it.

## Superseded versions

<details>
<summary><code>hair-wig/1</code> and <code>hair-wig/2</code> -- superseded; click for the history and the compatibility rules</summary>

<br>

`hair-wig/1` (HAIR 0.7.0) was the original: a plain list of button signals, a wig-level canonical signals hash, and `bypass_protocol` emitted only when true. `hair-wig/2` (HAIR 0.8.8) added the optional `climate` block for state-matrix devices; exporters wrote v2 only when a matrix was present. `hair-wig/3` (HAIR 0.9.5) is the current major and marks the one canonical break: `ditto_count` entered the signal hash, `bypass_protocol` became always-explicit, `send_count` left the hash entirely, and per-row claims replaced whole-file fittings. Since then HAIR writes v3 for every wig regardless of content.

Compatibility rules for old files:

- HAIR still reads `hair-wig/1` and `hair-wig/2` files, and re-saving one through HAIR (Save to Closet) upgrades it to v3. That is the migration path; nothing else is needed.
- New files must be v3. Tools should not emit the superseded majors, and the WigShop accepts v3 or better only.
- Pre-0.9.5 whole-file fittings on old files are dropped on import with a notice (see Pre-0.9.5 fittings above); the codes themselves import fine.
- Download filenames from pre-0.9.8 installs may end `.fitted.wig.json`; the name is presentation only and such files parse normally.

</details>

## For adapter authors

Convert inbound only: read your source format, emit a wig. Wigs are HAIR's single canonical format, and nothing round-trips out except the wig itself. Do not bundle or redistribute another project's code database; convert files the user already holds.
