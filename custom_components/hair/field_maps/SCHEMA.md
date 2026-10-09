# Field-map schema v0.6

Proposed v0 by the first derivation pass (2026-08-22). Extended to v0.1 by round two
and to v0.2 by round three, same date, and to v0.3 by the DAIKIN216 map (2026-09-14), and to v0.4 by the AC
derivation pass (2026-09-23), which added one optional rule parameter:
`integrity[].params.scale` on `checksum_sum`. It defaults to 1, so every
map written against v0.3 computes exactly what it did before. v0.5 (2026-09-28)
added one optional frame key, `frame.setting_frames`, which defaults to
`[payload_frame]`, so every map written against v0.4 describes exactly the same
frames it did before. v0.6 (2026-09-29) added one optional frame key,
`frame.optional_leader`, which defaults to false, so every map that does not
declare it reads exactly the codes it read before.
**Every change in every round is additive**: a reader written against v0 still reads
every map in this directory correctly, with one conformance point (round two,
`vocabulary`) called out at the end.

One YAML file per protocol family under `field-maps/<protocol_id>.yaml`.

```yaml
schema_version: "0.1"
protocol_id: <short id, e.g. ZHLT01>
aliases: [<other names/brand codes seen in the corpus>]
status: <draft | ratified>

frame:
  total_bits: <int>                  # payload bits of the frame that carries the fields
  frames_per_command: <int>          # how many frames one button press transmits
  frame_layout: [<int>, ...]         # NEW v0.1: bits per frame, in transmission order
  payload_frame: <int>               # NEW v0.1: which frame carries the PRIMARY state
                                     # block (0-based). Advisory for consumers that
                                     # need every setting-bearing byte; see
                                     # setting_frames.
  setting_frames: [<int>, ...]       # NEW v0.5: EVERY frame that carries a setting,
                                     # payload_frame first, in reading order.
                                     # Defaults to [payload_frame].
  optional_leader: <bool>            # NEW v0.6: frame 0 is a leader a code may
                                     # leave out. Default false. See below.
  modulation: pulse_distance | pulse_width | other
  bit_order: msb_first | lsb_first
  header_us: [<mark>, <space>]
  bit0_us: {mark: <int>, space: <int>}
  bit1_us: {mark: <int>, space: <int>}
  carrier_hz: <int or null>
  bits_tolerance: <int>              # NEW v0.1: identification window, default 1
  header_tolerance_us: <int>         # NEW v0.1: identification window, default 700
  identity_bytes: [[<frame>, <byte>, <value>], ...]   # NEW v0.1: constant bytes that
                                     # must match for the protocol to be identified
  timing:                            # NEW v0.2: the timing alphabet, stated not guessed
    classify: space | mark           # which pulse of each pair carries the bit
    unit_mark_us:    {nominal: <int>, min: <int>, max: <int>}
    space_zero_us:   {nominal: <int>, min: <int>, max: <int>}
    space_one_us:    {nominal: <int>, min: <int>, max: <int>}
    header_mark_us:  {nominal: <int>, min: <int>, max: <int>}
    header_space_us: {nominal: <int>, min: <int>, max: <int>}
    frame_gap_us:    {min: <int>}    # a space at or above this closes the frame

integrity:
  - type: complement_pairs | checksum_sum | nibble_sum | frame_repeat
    description: <plain-language rule>
    params: {...}                    # NEW v0.1: typed parameters, see "Rules" below
    verified_on: "<N/M checks across K files>"
    confidence: ratified | provisional | unratified   # NEW v0.1

fields:
  - name: <temperature | mode | fan_speed | swing | power | ...>
    frame: <int>                     # NEW v0.1 (typed): 0-based frame index, default 0
    byte: <index, 0-based, in the order bytes are transmitted>
    bits: full_byte | high_nibble | low_nibble | bit:N | mask:0xNN | "[start,len]"
    encoding: "<prose description, unchanged from v0>"
    encoding_ref:                    # NEW v0.1: machine-readable, CLOSED SET
      name: <linear | offset_linear | reverse_bits4_31_minus_t | enum_nibble
             | enum_byte | bitflag>
      params: {...}
    coordinate: <dim>                # NEW v0.3: which wig dimension answers this
                                     # field, when the NAME does not say
    applies_when:                    # NEW v0.1: when this field carries a fact at all
      in:     {<dim>: [<label>, ...]}
      not_in: {<dim>: [<label>, ...]}
    confidence: ratified | provisional | unratified   # NEW v0.1
    domain: "<value range / notes>"
    vocabulary: {<label>: <int or 0xNN>}   # values are NUMBERS, see conformance note
    vocabulary_notes: [<free text caveats that used to be inlined in the values>]
    mode_traits:                     # NEW v0.1: only on the field named "mode"
      <mode label>:
        temp: invariant | varies | file_dependent
        fan:  forced | free
        sentinel: <int>              # the fixed value the temperature field takes
    agreement:
      pass: <int>
      checked: <int>
      rate: "<pct>"
      files_at_100: "<n/m>"          # NEW v0.1
      disagreeing_files: [<file ids with the observed anomaly>]

synthesis:                           # NEW v0.1: enough to CONSTRUCT a frame from the map
  template: [[<byte>, ...], ...]     # constant background per frame
  tail_bits: {<frame>: "<bits>"}     # frames whose bit count is not a multiple of 8
  fixture_coordinates: {<dim>: [<label or number>, ...]}

derivation:
  files_used: [{repo: <...>, file: <...>, manufacturer: <...>, models: [...]}]
  external_sources: [...]
  open_questions: [...]
  notes: [...]
```

## Changes in v0.1, itemised

Additive, in the order they appear above:

1. `frame.frame_layout`, `frame.payload_frame` -- multi-frame protocols (Daikin's
   leader plus two 64-bit frames plus a 152-bit frame) cannot be described by a
   single `total_bits`. This answers the first pass's first open schema question
   without typing an integrity sub-block: frame-to-frame relationships are now an
   integrity RULE (`frame_repeat`), which is where they belong.
2. `frame.bits_tolerance`, `frame.header_tolerance_us` -- real captures jitter.
   Identification needs a stated window, not a magic constant in the reader.
   `frame.identity_bytes` earns its place too: the corpus's largest census family
   holds two unrelated protocols with the same bit count, frame count and header
   window, told apart only by a constant payload byte (0xB2 versus 0xA1). Frame
   signature alone is not an identity.
3. `fields[].frame` -- v0 already used this informally in GREE.yaml and
   TCL112.yaml; it is now part of the schema with a default of 0.
4. `fields[].encoding_ref` -- the machine-readable half of `encoding`. `encoding`
   stays as prose for humans; `encoding_ref` names one of a CLOSED SET of encodings
   implemented in code. There is no expression to evaluate, which is the property
   `fitting-integrity-coding-plan.md` B5 requires of the HAIR-side reader.
5. `fields[].applies_when` -- some fields carry no fact in some coordinates.
6. `fields[].confidence` -- per-field, per the round-two brief.
7. `mode_traits` -- the temperature-invariance convention the first pass found by
   hand, encoded so the sweep can skip the comparison. See below.
8. `integrity[].params` and the rule set `complement_pairs | checksum_sum |
   nibble_sum | frame_repeat`.
9. `vocabulary_notes` -- somewhere for the caveats that v0 inlined into the value
   strings.
10. `synthesis` -- the block that lets a map CONSTRUCT a frame, which is what makes
    synthesized fixtures possible.
11. `agreement.files_at_100` -- "97 percent" reads very differently when it is one
    bad file out of thirty than when it is spread evenly.

## Changes in v0.2: the timing block

One addition, `frame.timing`, and it exists because a heuristic splitter cannot be
made correct for every family by tuning a constant. Mitsubishi Heavy's 48-bit and
160-bit frames encode a one as a ~3550us space and close the frame with a ~7550us
gap: a ratio of 2.1. A fixed 3500us gap floor lands below the one-bit and shatters
the frame into two dozen fragments. Round two's adaptive rule (2.5x the 80th
percentile of the spaces) lands near 8800us and never sees the gap at all, so
three-symbol families read as one long frame. There is no third constant that
works for both those families and, say, Gree's 20ms gap.

Stating the alphabet removes the guess. **The decision procedure a reader should
implement, in order:**

1. Walk the pulse train as mark/space pairs.
2. If no bits have been read yet for the current frame, and the mark falls inside
   `header_mark_us` AND the space falls inside `header_space_us`, that pair is the
   header. It carries no bit. (This test comes FIRST, which is what stops a header
   space from being mistaken for a gap in families where the two overlap.)
3. Otherwise, if the space is at or above `frame_gap_us.min`, the frame ends here.
4. Otherwise classify the space: inside `space_zero_us` emits a 0, inside
   `space_one_us` emits a 1.
5. Otherwise the pulse is outside every window the map states. **Do not guess and
   do not skip it**: mark the frame unreadable, because dropping a pulse shifts
   every bit after it. An unreadable frame fails identification, so the cell counts
   as coverage rather than as a field reading.

`classify: mark` inverts steps 4 and 5 for pulse-width families. None of the maps
in this directory need it yet; it is in the schema because the shape exists. A map that uses it
needs identity's trailing-space strip revisited first: identity drops a capture's last
space as its terminator, which is only safe while the bit is in the space.

Windows are stated as observed, not as nominal plus a tolerance: they come from
measuring every cell of every file in the family and padding the 1st and 99th
percentiles. `space_zero_us.max` and `space_one_us.min` are adjacent by
construction, so there is no dead zone between them for a jittery capture to fall
into. That detail is worth stating because leaving a gap between the two windows
costs real coverage: a first cut at these numbers left TCL112 abstaining on 4.25%
of its cells purely because spaces between 509us and 784us matched neither window.

**What it costs and what it buys.** Across the eight families that round two
already mapped, switching from the heuristic to the map's own timing moves the
number of cells decoded by between -0.37% and +0.96%. What it buys is that no cell
is read through a threshold inferred from the data, and two integrity rules got
BETTER rather than worse: Gree's checksum went from 99.98% to 100.00% and
Midea/Coolix's complement rule returned to 100.00%. The failures round two
recorded there were splitter artifacts, not bad codes.

## Changes in v0.3: naming the coordinate a field answers

One addition, `fields[].coordinate`, optional, and no existing map sets it.

A reader matches a field to the cell coordinate it should be compared against by
the field's NAME: `temperature` to temp, `mode` to mode, `fan_speed` to fan,
`swing` to swing. That table works while one field answers one dimension, and
DAIKIN216 is the family where it stops: the frame carries vertical and horizontal
vane swing as two independent nibbles in different bytes, and the wig carries the
same fact as one `swing` dimension with four labels (off, vertical, horizontal,
both). Two fields have to answer one coordinate, and only one of them can be
called `swing`. Without a way to say so the second field is not skipped loudly --
it is counted as coverage with a `no-coordinate` receipt, which reads like the wig
lacking a dimension rather than the map lacking a word.

`coordinate` is that word. It names the dimension, the reader parses it onto the
field spec, and a consumer consults it BEFORE falling back to the name table. A
field without it behaves exactly as it did, which is why every map in this
directory is unaffected and none of them needed touching.

The same key covers the general case as well as the two-vanes one: a family whose
mode lives in a field nobody would name `mode` can say `coordinate: mode` rather
than being renamed to suit a lookup table.

## Changes in v0.5: setting_frames

One addition, `frame.setting_frames`, and it exists because `payload_frame` is
singular and at least one family is not.

`fields[].frame` has been per-field since v0.1, so a map has always been able to
put a field in any frame it likes, and TCL112 has set it on every field from the
start. What no map could say is which frames, taken together, hold the settings.
A consumer that wants the setting-bearing bytes -- payload identity above all,
which hashes them to decide whether two codes are the same press -- has only
`payload_frame` to read. Reading it alone on a family whose settings span two
frames means hashing one of them and collapsing two different presses into one
identity. That is not a hypothetical: TCL112 carries a quiet flag in frame 0 bit
5 of byte 5, and `silent` and `level1` differ in nothing else, so a
`payload_frame`-only identity cannot tell them apart.

The key states the set:

```yaml
frame:
  payload_frame: 1
  setting_frames: [1, 0]
```

Rules a map must keep, and the test `test_field_map_schema.py` enforces each one
against the YAML documents themselves:

- `setting_frames[0] == payload_frame`. The primary block stays first, so a
  consumer that only wants one frame still gets the right one.
- Every index is a valid frame of `frame_layout`.
- No repeats.
- `setting_frames` is a superset of `{f.frame for f in fields}`. A field in a
  frame the map has not declared as setting-bearing is a map bug, and it is the
  exact bug this key exists to make visible.

A reader that has not been updated keeps working: absent the key, a map's setting
frames are `[payload_frame]`, which is what every consumer already assumed.
Within HAIR the two places that read `payload_frame` to decide what a capture
needs now read `setting_frames` instead, and on every map in this directory the
two answers are identical, because no map other than TCL112 declares a field
outside its payload frame and TCL112 declares no `frame_repeat` rule, so the
short-capture path it guards was already closed for it.

Unlike v0.1 through v0.4, this round touches every map: each one gains the key
explicitly rather than relying on the default, so that the superset test has
something to check, and each one's `schema_version` moves to `"0.5"` to say so.
Declaring the key rather than defaulting it is the point -- a map that has
thought about the question and a map that has not should not look the same.

## Changes in v0.6: optional_leader

One addition, `frame.optional_leader`, and it exists because a leader block is
something one sender transmits and another does not.

DAIKIN152 describes four frames: a five-bit leader block, the 8-byte constant
frame, the 8-byte clock frame and the 19-byte settings frame. Every handset
capture in its derivation files carries the leader. A lattice rendered by an
encoder that sends the three frames alone (GH #183) met a four-frame layout and
read as nothing, while that same remote's Off, captured from a handset, read
fine. One remote was split across "read" and "unread" by a block that carries
no byte.

```yaml
frame:
  frame_layout: [5, 64, 64, 152]
  payload_frame: 3
  setting_frames: [3]
  optional_leader: true
```

**Numbering does not change.** A code that carries the leader is read exactly as
before. A code whose frames fit the layout from frame 1 onward, and do not fit
it whole, is read with an EMPTY frame 0 standing in for the leader, so frame 3
is the settings frame either way and every index the map states -- fields,
identity bytes, rules, `payload_frame`, `setting_frames` -- keeps its meaning.
The whole layout is always tried first, so the short form is only ever a second
chance.

Rules a map must keep, enforced by `test_field_map_schema.py` against the
documents:

- The value is the boolean `true`. Anything else is not a declaration.
- The layout has at least two frames, and frame 0 is shorter than a byte.
- Nothing reads frame 0: it is not `payload_frame`, not in `setting_frames`,
  and no identity byte, field or integrity rule names it. On the codes that
  leave it out there would be nothing there to read.

The loader salvages a document that breaks the last rule by ignoring the key,
as it salvages a badly declared `setting_frames`; the document itself fails the
test.

Within HAIR the leader-aware reading is used for identification (`read_code`,
and through it every comb check that reads fields and rules), for setting-frame
identity (the spans a press's identity is computed from), and in the comb's
frame-shape check, which sets a present optional leader aside when a lattice
mixes the two forms, so the cells that carry it are not reported for it. A
lattice whose codes all carry the leader is compared exactly as before. One
place does not use it yet: rewriting a field inside a real capture to build a
repair candidate still needs a capture that carries the leader, and declines a
leaderless one as unreadable.

Only DAIKIN152 declares the key. It moves that map's version (see below) and no
other.

## What moves a map's version

HAIR derives a version for every map and keys people's answers to comb
findings on it (Keep, Keep Both, Keep on the Unusual card): change the
version and every answered finding for that family comes back to be
answered again. So the version is a digest of what the map READS AND
JUDGES, taken over the parsed map rather than the document:

- **Moves it:** `protocol_id`; the frame layout, `payload_frame`,
  `setting_frames`, `optional_leader` (when true; a map that leaves it
  off or writes `false` has the version it had before v0.6),
  `bit_order`, `bits_tolerance`, `identity_bytes` and the `timing` block; each field's `name`, `frame`, `byte`, `bits`,
  `encoding_ref` (name and every param, including the vocabulary),
  `applies_when`, `mode_traits`, `coordinate` and `confidence`; each
  integrity rule's `type`, `params` and `confidence`.
- **Does not:** `schema_version`, aliases, `status`, `derivation`,
  `agreement` blocks, `vocabulary_notes`, open questions, prose
  (`encoding`, `domain`, rule `description`), `verified_on`, `synthesis`,
  the human copy of a field's `vocabulary` beside `encoding_ref`, and the
  pre-v0.2 frame keys the timing block superseded (`header_us`,
  `bit0_us`, `bit1_us`, `modulation`, `carrier_hz`, `frames_per_command`,
  `header_tolerance_us`).

Key order in the document does not matter, and neither does writing a
default out or leaving it off. Update agreement figures and notes
freely; treat an edit in the first list as one that asks every user of
that family to look again, because it does.

## Encodings, the closed set

| name | value = | params |
|---|---|---|
| `linear` | `coord + offset` | `offset`, `round: nearest\|floor` |
| `offset_linear` | `scale * coord + offset` | `scale`, `offset`, `round` |
| `reverse_bits4_31_minus_t` | `reverse_bits4(31 - T)` | `special: {<T>: <value>}` |
| `enum_nibble` | vocabulary lookup, 4-bit field | `vocabulary` |
| `enum_byte` | vocabulary lookup, wider field | `vocabulary` |
| `bitflag` | 1 if the label is in `true_values` else 0 | `true_values` |

`enum_nibble`/`enum_byte` take numeric coordinates as well as labels, which is how
MIDEA_COOLIX's Gray-coded temperature table is expressed without adding a
`lookup_table` encoding: temperature is simply an enum over the integers 17..30.

## Integrity rules, the closed set

| type | params | meaning |
|---|---|---|
| `complement_pairs` | `frame`, `pairs` or `start`/`count` | `byte[hi] == ~byte[lo] & 0xFF` |
| `checksum_sum` | `frame`, `range`, `target_byte`, `mod`, `offset`, `scale`, `bits` | `scale * sum(range) + offset`, mod `mod`; `scale` defaults to 1 |
| `nibble_sum` | `frame`, `nibbles`, `target_byte`, `bits`, `offset` | sum of selected nibbles |
| `frame_repeat` | `frame`, `equals` | frame N is byte-identical to frame M |

## The temperature-invariance convention

Three of the four families the first pass derived, and every family this pass
touched, have modes whose temperature byte does not move with the labelled
temperature: the physical unit has no settable target in dry or fan-only. A sweep
that compares temperature in those coordinates generates a false positive on every
single cell.

`mode_traits` states this per mode. Values:

- `temp: invariant` -- never varies, in any file of this family. Skip temperature.
- `temp: varies` -- carries a real setpoint. Compare it.
- `temp: file_dependent` -- both behaviours occur in this family's own corpus, so
  the MAP cannot say which a given wig will use. The WIG can: the reference
  implementation looks at whether the temperature field actually moves across that
  mode's own cells in the wig in front of it, checks the mode when it does, and
  counts the cells as unchecked coverage when it does not. A reader that cannot see
  the whole matrix should skip the comparison and count coverage, never clean.

  That distinction is worth real defects. ZHLT01's `heat_cool` is file_dependent;
  skipping it outright puts the family's temperature agreement at 99.83% and misses
  1581.json's whole shifted column, while deciding per wig puts it at 95.11% and
  surfaces the column. The lower number is the useful one.

`file_dependent` is the honest third state and it matters: ZHLT01's `fan_only` is
frozen in 1440.json and 1581.json and carries a real setpoint in 2300.json and
2760.json. A two-state convention would have to guess, and guessing here means
either missing a whole column of real defects or inventing a column of false ones.

`sentinel` records the fixed value where it is known (MIDEA_COOLIX 0xE,
DAIKIN152 0xC0 in dry and 0x32 in fan-only), which a reader may use to distinguish
"this cell says no temperature" from "this cell says the wrong temperature".

`fan: forced` is the same idea one dimension over: ZHLT01, GREE, TCL112 and
MIDEA_COOLIX all pin the fan field to a fixed value inside particular modes
regardless of the labelled fan speed.

## Conformance note on `vocabulary` (read this one)

v0 declared `vocabulary` as `<label>: <value, hex>` but the four v0 maps stored
strings carrying prose, for example `cool: "0xB (0x3 at T=32)"`. Those values are
not machine-readable. In this directory `vocabulary` now holds numbers only (int or
a `0xNN` string), and the prose moved to `vocabulary_notes`.

This is a conformance fix rather than a schema change -- v0's own text always said
the value was a value -- but a reader that was written to accept the v0 FILES as
they actually shipped would need to stop expecting free text there. It is the one
point in this document where old files and new files differ in a way a parser can
notice, so it is called out rather than buried.

## Open questions on the schema, carried forward

- `bits: "[start,len]"` is now implemented but only exercised by nothing in this
  directory yet; every field derived so far is nibble-, byte- or mask-aligned. It
  stays in the schema because the first pass predicted needing it.
- `synthesis.template` is a constant background per frame. Families whose constant
  background differs per source file (TCL112's frame 0 varies across 5 values in
  1661.json) get the most common template and a note; the block is for building
  fixtures, not for transmitting, and nothing in HAIR may use it to transmit.
- Half-degree temperatures: AUX104 labels 16.0 and 16.5 read the same integer
  field, so a half-degree bit exists somewhere this pass did not locate. No schema
  support is proposed until it is found.
- There is no way to say "this field applies only to the files of this family that
  share a given constant byte". TCL112 wants one: 3020.json carries `0x12` where
  every other file in the family carries `0x02` at frame 0 byte 3, and that one
  difference accounts for every residual disagreement on the `quiet` field. The
  field stays `provisional` rather than a predicate being invented for it, because
  the honest alternatives are a real dialect predicate or splitting the dialect
  into its own map, and neither is a one-line schema change.
