# Field maps

Thirteen protocol families, one YAML file each, read by `field_readers.py` and by
nothing else. A map says what the bytes of a frame mean: where the temperature
lives, which nibble carries the mode, which rule the frame's own checksum must
satisfy, and how confident the derivation is about each of those claims.

`SCHEMA.md` is the format. This file is the provenance.

## Where they came from

Every map in this directory was derived from **public SmartIR climate files**
(`smartHomeHub/SmartIR`, and where noted the community forks that carry the same
codes), by reading a whole family of files together and keeping only what they
agree on. Each map records its own working in a `derivation` block:

- `files_used` -- the exact corpus files, by repository, filename, manufacturer
  and model. A claim in a map can always be walked back to the codes it came
  from.
- `external_sources` -- prior art consulted, including the WigShop brief that
  started this work. Where a reference was used as a hypothesis rather than as
  evidence, the block says so and the field was re-derived from the corpus
  anyway.
- `open_questions` -- what the corpus could not settle. These are not TODOs to
  be quietly closed; several of them need a physical remote to answer, and the
  honest state of a map is one that names them.
- `notes` -- the near misses, especially files an earlier pass had assigned to
  the wrong family.

One exception to the corpus rule, and it is stated rather than smoothed over.
**DAIKIN216** was derived from a single WigShop wig (DAB-LABS/WigShop PR 24, a
Daikin FTXS50KVM captured from an ARC433B70 remote and fitted on the physical
unit), not from a family of SmartIR files read together. A map with one source
cannot show agreement across a family, so it does not pretend to: its
`derivation.files_used` names the one file, and its `open_questions` opens with
the fact that every claim in it rests on that file. What it has instead of
breadth is depth -- 521 of 521 codes agree with the layout on every field and
both checksums -- and a fitting signed on hardware. A later pass may cross-check
it against SmartIR Daikin files carrying the same 64+152 frame signature, which
would either confirm the map or produce the first disagreement it has to record.

No map was copied from another project's source code, and no map contains
transmittable codes. A field map describes a layout; it is not a remote.

## Confidence is part of the data

Fields and integrity rules carry a `confidence` marking, and it is load-bearing
rather than documentation. **Only `ratified` claims produce findings.** A
`provisional` field is one the family itself disagrees about -- ZHLT01's mode
vocabulary is the standing example, where two files invert `fan_only` and
`heat_cool` -- and sweeping it would bury real findings under a thousand false
ones. Provisional claims still appear in coverage, so a reader can see exactly
which questions were left open.

Where a `status: draft` map contradicts a later derivation report, **the report
and `SCHEMA.md` win**. The maps are vendored as they stand, markings and open
questions intact, rather than tidied into a false uniformity.

## What HAIR reads, and what it does not

`field_readers.py` reads `frame`, `fields`, `integrity`, `identity_bytes` and
the `confidence` markings. It does **not** read `synthesis`: that block is
fixture tooling, used by the derivation pass's `validate.py` to generate the
licence-free clean and defective test packs under
`tests/fixtures/field-packs/`. Nothing in the shipped integration touches it.

The reader is also hard-isolated from transmit. No TX path imports
`field_readers`, and `field_readers` imports no TX module; both directions are
pinned by test. A map is read-only knowledge used to judge codes HAIR already
has. It is never a source of codes to send.

## Adding one

A new family needs a map that conforms to `SCHEMA.md`, a `derivation` block with
its corpus, and confidence markings that reflect what the corpus actually
showed. Mark a field `ratified` only where every file in the family agrees; if
they disagree, the disagreement is the finding, and `provisional` plus a note is
the honest record of it.
