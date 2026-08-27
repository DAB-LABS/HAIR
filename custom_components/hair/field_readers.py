"""Reading what a state frame SAYS, to check it against what a cell CLAIMS.

Fitting integrity, release two. The WigShop's Komeco case is the reason
this module exists: a 1,156-cell lattice that is structurally flawless
and semantically wrong, where one column sends T+1 and every check HAIR
had was happy. Nothing in the comb decoded fields, so nothing could see
it.

**This tier is READ-ONLY, and the isolation is the design rather than a
convention.** A field reader identifies a state-frame protocol and
decodes its fields so the comb can compare them to a label. It never
constructs, never re-encodes, never touches transmit. HAIR replays AC
state frames raw on purpose (wig-model.md, and the whole raw-first
design decision), and the way to make that impossible to forget is that
this module imports nothing from the TX side and nothing on the TX side
imports it. A test pins both directions.

Three properties worth stating before the code, because each one is a
decision somebody could reasonably have made the other way:

- **Maps are DATA, and the engine executes them.** The closed set of
  encodings and integrity rules below is implemented here in Python and
  referenced BY NAME from the YAML. There is no expression to evaluate,
  so extending the set is a code change with a review, by design.
- **Frame splitting and bit reading are map-driven, never heuristic.**
  Every map states its own timing alphabet (`frame.timing`, schema
  v0.2) and this module executes the five-rule decision procedure that
  schema defines. There is no threshold in here derived from the data,
  and deliberately no reuse of the S/L constants the fingerprinter uses:
  Mitsubishi Heavy's 48-bit family writes a one as a 3601 us space and
  closes its frame with a 7629 us gap, and no constant that reads that
  family also reads Gree's 20 ms gap (derivation report three, 2d).
- **A pulse outside every stated window makes the frame UNREADABLE.**
  Not skipped, not guessed: dropping a pulse shifts every bit after it,
  and a confidently wrong reading is the one failure mode that matters
  here. An unreadable frame fails identification and the cell becomes
  coverage.

Source of truth for the map format: `docs/internal/plans/field-maps/
SCHEMA.md` (v0.2) and the three derivation reports beside it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)

# The vendored maps, one YAML per protocol family.
MAPS_DIRNAME = "field_maps"

# Pronto's time base: one unit is this many microseconds times the code's
# own frequency word. Derived here rather than imported because every
# helper that already knows it lives on the transmit side.
_PRONTO_TICK_US = 0.241246

CONFIDENCE_RATIFIED = "ratified"

# --- the closed sets ------------------------------------------------------
#
# Named from the map, implemented here. Adding one is a code change and a
# review; that is the point of the set being closed (coding plan B5).
ENCODING_LINEAR = "linear"
ENCODING_OFFSET_LINEAR = "offset_linear"
ENCODING_REVERSE_BITS4 = "reverse_bits4_31_minus_t"
ENCODING_ENUM_NIBBLE = "enum_nibble"
ENCODING_ENUM_BYTE = "enum_byte"
ENCODING_BITFLAG = "bitflag"
ENCODINGS = frozenset({
    ENCODING_LINEAR, ENCODING_OFFSET_LINEAR, ENCODING_REVERSE_BITS4,
    ENCODING_ENUM_NIBBLE, ENCODING_ENUM_BYTE, ENCODING_BITFLAG,
})

RULE_COMPLEMENT_PAIRS = "complement_pairs"
RULE_CHECKSUM_SUM = "checksum_sum"
RULE_NIBBLE_SUM = "nibble_sum"
RULE_FRAME_REPEAT = "frame_repeat"
INTEGRITY_RULES = frozenset({
    RULE_COMPLEMENT_PAIRS, RULE_CHECKSUM_SUM, RULE_NIBBLE_SUM,
    RULE_FRAME_REPEAT,
})

# Why a code, a cell or a field was not checked. These ride the comb's
# coverage section and are localized for display.
NO_MAP = "protocol-unmapped"
UNREADABLE = "unreadable-frame"
NOT_RATIFIED = "field-provisional"
NO_COORDINATE = "no-coordinate"
NOT_APPLICABLE = "not-applicable"
TEMP_INVARIANT = "mode-temp-invariant"
TEMP_FROZEN = "mode-temp-frozen"
UNKNOWN_LABEL = "unknown-label"
OUT_OF_DOMAIN = "out-of-domain"
FAN_FORCED = "mode-fan-forced"
FIELD_ABSENT = "field-absent"
RULE_UNEVALUATED = "rule-unevaluable"
NO_LABELS = "no-labels"


# ---------------------------------------------------------------------------
# The map, as the engine sees it
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Window:
    """A stated timing window, in microseconds. Inclusive both ends."""

    minimum: float
    maximum: float
    nominal: float = 0.0

    def holds(self, value: float) -> bool:
        return self.minimum <= value <= self.maximum


@dataclass(frozen=True)
class FrameTiming:
    """The timing alphabet a family transmits in (schema v0.2).

    Stated by the map, never inferred. ``classify`` says which pulse of
    each pair carries the bit; every map in the directory today carries
    it in the space, and the mark form is implemented because the shape
    exists rather than because something needs it yet.
    """

    classify: str
    unit: Window
    zero: Window
    one: Window
    header_mark: Window
    header_space: Window
    gap_min: float


@dataclass(frozen=True)
class FieldSpec:
    """One field of a frame, and how to turn a coordinate into its value."""

    name: str
    frame: int
    byte: int
    bits: str
    encoding: str | None
    params: dict[str, Any]
    applies_in: dict[str, list[str]]
    applies_not_in: dict[str, list[str]]
    confidence: str
    mode_traits: dict[str, dict[str, Any]]

    @property
    def ratified(self) -> bool:
        return self.confidence == CONFIDENCE_RATIFIED


@dataclass(frozen=True)
class IntegrityRule:
    """One structural rule the frame must satisfy on its own terms."""

    type: str
    params: dict[str, Any]
    confidence: str
    description: str

    @property
    def ratified(self) -> bool:
        return self.confidence == CONFIDENCE_RATIFIED


@dataclass(frozen=True)
class FieldMap:
    """One protocol family: how to read its frames and what they mean."""

    protocol_id: str
    #: A content tag for the map itself, so anything that recorded
    #: "this map justified that write" can tell later whether the map
    #: it trusted is still the map on disk. Derived from the document
    #: rather than declared in it, because a hand-maintained version
    #: number is exactly the field that does not get bumped.
    version: str
    frame_layout: list[int]
    payload_frame: int
    bit_order: str
    bits_tolerance: int
    identity_bytes: list[tuple[int, int, int]]
    timing: FrameTiming
    fields: list[FieldSpec]
    integrity: list[IntegrityRule]

    def field_named(self, name: str) -> FieldSpec | None:
        for spec in self.fields:
            if spec.name == name:
                return spec
        return None


@dataclass(frozen=True)
class Reading:
    """What one code turned out to be, or why it could not be read.

    ``frames`` holds the decoded bytes per frame. ``declined`` is the
    coverage reason when nothing could be read, and the two are mutually
    exclusive: a Reading either carries bytes or carries a reason.
    """

    protocol_id: str | None = None
    frames: tuple[tuple[int, ...], ...] = ()
    declined: str | None = None

    @property
    def identified(self) -> bool:
        return self.protocol_id is not None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def maps_dir() -> Path:
    return Path(__file__).parent / MAPS_DIRNAME


def _window(raw: Any, fallback_min: float = 0.0,
            fallback_max: float = 0.0) -> Window:
    if not isinstance(raw, dict):
        return Window(fallback_min, fallback_max)
    return Window(
        minimum=float(raw.get("min", fallback_min)),
        maximum=float(raw.get("max", fallback_max)),
        nominal=float(raw.get("nominal", 0) or 0),
    )


def _timing(raw: dict[str, Any]) -> FrameTiming | None:
    """The timing block, or None when the map does not state one.

    A map without a timing block cannot be executed, and the engine says
    so rather than falling back on a threshold of its own. That is the
    whole lesson of derivation report three section 2d.
    """
    if not isinstance(raw, dict):
        return None
    gap = raw.get("frame_gap_us")
    if not isinstance(gap, dict) or "min" not in gap:
        return None
    return FrameTiming(
        classify=str(raw.get("classify", "space")),
        unit=_window(raw.get("unit_mark_us")),
        zero=_window(raw.get("space_zero_us")),
        one=_window(raw.get("space_one_us")),
        header_mark=_window(raw.get("header_mark_us")),
        header_space=_window(raw.get("header_space_us")),
        gap_min=float(gap["min"]),
    )


def _field(raw: dict[str, Any]) -> FieldSpec | None:
    name = raw.get("name")
    if not isinstance(name, str) or not isinstance(raw.get("byte"), int):
        return None
    ref = raw.get("encoding_ref")
    ref = ref if isinstance(ref, dict) else {}
    encoding = ref.get("name")
    if encoding is not None and encoding not in ENCODINGS:
        # An unknown encoding is a map written against a newer engine.
        # Carry the field so coverage can name it; never guess at it.
        _LOGGER.debug("field map: unknown encoding %s on %s", encoding, name)
        encoding = None
    applies = raw.get("applies_when")
    applies = applies if isinstance(applies, dict) else {}
    traits = raw.get("mode_traits")
    return FieldSpec(
        name=name,
        frame=int(raw.get("frame", 0) or 0),
        byte=int(raw["byte"]),
        bits=str(raw.get("bits", "full_byte")),
        encoding=encoding,
        params=dict(ref.get("params") or {}),
        applies_in=dict(applies.get("in") or {}),
        applies_not_in=dict(applies.get("not_in") or {}),
        confidence=str(raw.get("confidence", "unratified")),
        mode_traits=dict(traits) if isinstance(traits, dict) else {},
    )


def _rule(raw: dict[str, Any]) -> IntegrityRule | None:
    kind = raw.get("type")
    if kind not in INTEGRITY_RULES:
        _LOGGER.debug("field map: unknown integrity rule %s", kind)
        return None
    return IntegrityRule(
        type=str(kind),
        params=dict(raw.get("params") or {}),
        confidence=str(raw.get("confidence", "unratified")),
        description=str(raw.get("description", "")),
    )


def _map_version(raw: dict[str, Any]) -> str:
    """A short content digest of one map document."""
    import hashlib
    import json

    # Document order, not sorted keys: a map's vocabulary legitimately
    # mixes key types (YAML reads `on:` as the boolean True beside
    # `"cool"`), and sorting those against each other raises. Order is
    # stable for a given file, which is all a content tag needs.
    canonical = json.dumps(raw, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def parse_map(raw: dict[str, Any]) -> FieldMap | None:
    """One YAML document as a map, or None when it cannot be executed."""
    if not isinstance(raw, dict):
        return None
    protocol_id = raw.get("protocol_id")
    frame = raw.get("frame")
    if not isinstance(protocol_id, str) or not isinstance(frame, dict):
        return None
    timing = _timing(frame.get("timing"))
    if timing is None:
        _LOGGER.debug("field map %s: no timing block, skipped", protocol_id)
        return None
    layout = frame.get("frame_layout")
    if not isinstance(layout, list) or not layout:
        total = frame.get("total_bits")
        layout = [int(total)] if isinstance(total, int) else None
    if not layout:
        return None
    identity: list[tuple[int, int, int]] = []
    for entry in frame.get("identity_bytes") or []:
        if isinstance(entry, list | tuple) and len(entry) == 3:
            identity.append((int(entry[0]), int(entry[1]), int(entry[2])))
    fields = [
        spec for spec in (_field(f) for f in raw.get("fields") or [])
        if spec is not None
    ]
    rules = [
        rule for rule in (_rule(r) for r in raw.get("integrity") or [])
        if rule is not None
    ]
    return FieldMap(
        protocol_id=protocol_id,
        version=_map_version(raw),
        frame_layout=[int(bits) for bits in layout],
        payload_frame=int(frame.get("payload_frame", 0) or 0),
        bit_order=str(frame.get("bit_order", "msb_first")),
        bits_tolerance=int(frame.get("bits_tolerance", 1) or 0),
        identity_bytes=identity,
        timing=timing,
        fields=fields,
        integrity=rules,
    )


def load_maps(directory: Path | None = None) -> list[FieldMap]:
    """Every executable map in the directory, worst case an empty list.

    A bad map never breaks a comb: it is logged and skipped, the same
    contract the pluckable registry keeps.
    """
    where = directory or maps_dir()
    maps: list[FieldMap] = []
    try:
        paths = sorted(where.glob("*.yaml"))
    except OSError:  # pragma: no cover - a missing directory is not a crash
        return maps
    for path in paths:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as err:
            _LOGGER.warning("field map %s did not load: %s", path.name, err)
            continue
        parsed = parse_map(raw)
        if parsed is None:
            _LOGGER.warning("field map %s is not executable, skipped",
                            path.name)
            continue
        maps.append(parsed)
    return maps


_LIBRARY: list[FieldMap] | None = None


def library() -> list[FieldMap]:
    """The vendored maps, loaded once per process."""
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = load_maps()
    return _LIBRARY


def reset_library() -> None:
    """Drop the cache. Tests only."""
    global _LIBRARY
    _LIBRARY = None


# ---------------------------------------------------------------------------
# Pronto to pulses, without the transmit side
# ---------------------------------------------------------------------------


def pronto_microseconds(pronto: str) -> list[int] | None:
    """A Pronto code as signed microseconds, or None if it will not parse.

    Positive is a mark, negative a space, which is the convention the
    decoders package already uses. The conversion is here rather than
    imported because every existing helper for it lives on the transmit
    side, and this tier does not import that side at all.
    """
    if not isinstance(pronto, str):
        return None
    try:
        words = [int(token, 16) for token in pronto.split()]
    except ValueError:
        return None
    if len(words) < 6 or words[1] <= 0:
        return None
    unit = words[1] * _PRONTO_TICK_US
    out: list[int] = []
    for index, word in enumerate(words[4:]):
        value = round(word * unit)
        out.append(value if index % 2 == 0 else -value)
    return out


def read_frames(
    timing: FrameTiming, timings: list[int]
) -> tuple[list[list[int]], bool]:
    """The five-rule decision procedure of schema v0.2, in order.

    Returns (frames as bit lists, unreadable). The header test comes
    FIRST and that ordering is load bearing: in most of these families
    the header space is longer than the frame gap, so testing the gap
    first would end the frame before it began.
    """
    frames, _positions, unreadable = read_frames_positioned(timing, timings)
    return frames, unreadable


def read_frames_positioned(
    timing: FrameTiming, timings: list[int]
) -> tuple[list[list[int]], list[list[int]], bool]:
    """The same walk, also reporting WHERE each bit came from.

    ``positions[f][i]`` is the index of the pulse pair, in the
    trailing-zero-stripped train, that carried bit ``i`` of frame ``f``.

    This exists so a caller that has to change one field can change the
    pulses that field actually occupies, in the code's own timings,
    instead of rendering a fresh waveform from the map's nominal
    windows. Reporting where a bit came from is still READING: this
    module has no encoder, imports no transmit path, and both are
    asserted by test. Whoever builds something with these positions
    does it somewhere else.

    ``read_frames`` is this function with the positions dropped, so
    there is one walk and it cannot drift from itself.
    """
    # A zero at the end of the train is Pronto saying "nothing more", not
    # a pulse of no length. Leaving it in makes the last pair of every
    # code that carries one fall outside every window, which would fail
    # identification on the whole family for a value that is not a
    # measurement at all. Zeros anywhere else stay: those really are
    # unreadable.
    train = list(timings)
    while train and train[-1] == 0:
        train.pop()
    frames: list[list[int]] = []
    places: list[list[int]] = []
    bits: list[int] = []
    where: list[int] = []
    pairs = zip(train[0::2], train[1::2], strict=False)
    for index, (mark, space) in enumerate(pairs):
        mark_us = abs(mark)
        space_us = abs(space)
        carrier = space_us if timing.classify == "space" else mark_us
        other = mark_us if timing.classify == "space" else space_us
        if not bits and timing.header_mark.holds(mark_us) \
                and timing.header_space.holds(space_us):
            continue  # the header carries no bit
        if space_us >= timing.gap_min:
            frames.append(bits)
            places.append(where)
            bits = []
            where = []
            continue
        if not timing.unit.holds(other):
            return [], [], True
        if timing.zero.holds(carrier):
            bits.append(0)
            where.append(index)
        elif timing.one.holds(carrier):
            bits.append(1)
            where.append(index)
        else:
            # Outside every window the map states. Guessing here would
            # be a reading nobody can check, and skipping would shift
            # every bit after it.
            return [], [], True
    if bits:
        frames.append(bits)
        places.append(where)
    kept = [i for i, frame in enumerate(frames) if frame]
    return (
        [frames[i] for i in kept],
        [places[i] for i in kept],
        False,
    )


def bits_to_bytes(bits: list[int], bit_order: str) -> tuple[int, ...]:
    """Whole bytes only, in transmission order, honoring the bit order."""
    out: list[int] = []
    for start in range(0, len(bits) - 7, 8):
        chunk = bits[start:start + 8]
        value = 0
        for index, bit in enumerate(chunk):
            if bit:
                value |= 1 << index if bit_order == "lsb_first" \
                    else 1 << (7 - index)
        out.append(value)
    return tuple(out)


# ---------------------------------------------------------------------------
# Identification
# ---------------------------------------------------------------------------


def _matches_layout(field_map: FieldMap, frames: list[list[int]]) -> bool:
    if len(frames) != len(field_map.frame_layout):
        return False
    tolerance = field_map.bits_tolerance
    return all(
        abs(len(frame) - expected) <= tolerance
        for frame, expected in zip(frames, field_map.frame_layout, strict=True)
    )


def _matches_identity(
    field_map: FieldMap, decoded: list[tuple[int, ...]]
) -> bool:
    """The constant bytes that separate families sharing a signature.

    Never a prefix on its own: `23 CB 26 01` is both MITSUBISHI144 and
    OEM112, and `23 CB 26 02` is TCL112 (derivation report three,
    section 3). Signature plus identity bytes is the key.
    """
    for frame_index, byte_index, value in field_map.identity_bytes:
        if frame_index >= len(decoded):
            return False
        frame = decoded[frame_index]
        if byte_index >= len(frame) or frame[byte_index] != value:
            return False
    return True


def read_code(
    pronto: str, maps: list[FieldMap] | None = None,
    prefer: str | None = None,
) -> Reading:
    """Identify one code and decode its frames, or say why not.

    ``prefer`` names the protocol to try first, which is what makes a
    1,156-cell sweep cheap: a lattice is one family, so the map that
    read the last cell reads the next one.
    """
    candidates = maps if maps is not None else library()
    if not candidates:
        return Reading(declined=NO_MAP)
    timings = pronto_microseconds(pronto)
    if not timings:
        return Reading(declined=UNREADABLE)
    ordered = candidates
    if prefer:
        ordered = sorted(candidates, key=lambda m: m.protocol_id != prefer)
    unreadable = False
    for field_map in ordered:
        frames, failed = read_frames(field_map.timing, timings)
        if failed:
            unreadable = True
            continue
        if not _matches_layout(field_map, frames):
            continue
        decoded = [
            bits_to_bytes(frame, field_map.bit_order) for frame in frames
        ]
        if not _matches_identity(field_map, decoded):
            continue
        return Reading(
            protocol_id=field_map.protocol_id,
            frames=tuple(decoded),
        )
    # Every map either read it as noise or did not recognize it. Those
    # are different facts and the receipt keeps them apart.
    return Reading(declined=UNREADABLE if unreadable else NO_MAP)


# ---------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------


def _bit_selector(bits: str) -> tuple[int, int]:
    """(mask, shift) for a field's bit selector inside its byte."""
    text = bits.strip()
    if text == "full_byte":
        return 0xFF, 0
    if text == "high_nibble":
        return 0xF0, 4
    if text == "low_nibble":
        return 0x0F, 0
    if text.startswith("bit:"):
        index = int(text[4:])
        return 1 << index, index
    if text.startswith("mask:"):
        mask = int(text[5:], 0)
        shift = (mask & -mask).bit_length() - 1 if mask else 0
        return mask, shift
    if text.startswith("[") and text.endswith("]"):
        start, length = (int(part) for part in text[1:-1].split(","))
        mask = ((1 << length) - 1) << start
        return mask, start
    raise ValueError(f"unknown bit selector {bits!r}")


#: Public name for the selector, so a caller that has to WRITE a field
#: addresses exactly the bits this module READS it from. Two selectors
#: would be two answers to one question.
bit_selector = _bit_selector


def read_field(reading: Reading, spec: FieldSpec) -> int | None:
    """The raw value this frame carries in that field, or None."""
    if spec.frame >= len(reading.frames):
        return None
    frame = reading.frames[spec.frame]
    if spec.byte >= len(frame):
        return None
    try:
        mask, shift = _bit_selector(spec.bits)
    except ValueError:
        return None
    return (frame[spec.byte] & mask) >> shift


def _reverse_bits4(value: int) -> int:
    out = 0
    for index in range(4):
        if value & (1 << index):
            out |= 1 << (3 - index)
    return out


def _rounded(value: float, how: str) -> int:
    return int(value // 1) if how == "floor" else round(value)


def expected_value(spec: FieldSpec, coordinate: Any) -> int | None:
    """What the frame SHOULD carry for this coordinate, or None.

    None is the honest answer and it happens often: a label the map's
    vocabulary does not know, a temperature outside the domain, an
    encoding the map did not state. Every None is coverage, never a
    finding, because a check nobody can compute is not a check that
    passed (coding plan: partial maps are legal and useful).
    """
    if spec.encoding is None or coordinate is None:
        return None
    params = spec.params
    if spec.encoding in (ENCODING_ENUM_NIBBLE, ENCODING_ENUM_BYTE):
        vocabulary = params.get("vocabulary")
        if not isinstance(vocabulary, dict):
            return None
        value = vocabulary.get(coordinate)
        if value is None and isinstance(coordinate, float) \
                and coordinate.is_integer():
            value = vocabulary.get(int(coordinate))
        if value is None and not isinstance(coordinate, str):
            value = vocabulary.get(str(coordinate))
        return _as_int(value)
    if spec.encoding == ENCODING_BITFLAG:
        true_values = params.get("true_values") or []
        return 1 if coordinate in true_values else 0
    if spec.encoding == ENCODING_REVERSE_BITS4:
        number = _as_number(coordinate)
        if number is None:
            return None
        special = params.get("special") or {}
        for key, value in special.items():
            if _as_number(key) == number:
                return _as_int(value)
        if not 16 <= number <= 31:
            return None
        return _reverse_bits4(31 - int(number))
    number = _as_number(coordinate)
    if number is None:
        return None
    how = str(params.get("round", "nearest"))
    if spec.encoding == ENCODING_LINEAR:
        return _rounded(number + float(params.get("offset", 0) or 0), how)
    if spec.encoding == ENCODING_OFFSET_LINEAR:
        scale = float(params.get("scale", 1) or 0)
        offset = float(params.get("offset", 0) or 0)
        return _rounded(scale * number + offset, how)
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def applies(spec: FieldSpec, coordinates: dict[str, Any]) -> bool:
    """Does this field carry a fact at these coordinates at all?"""
    for dimension, labels in spec.applies_in.items():
        if coordinates.get(dimension) not in labels:
            return False
    for dimension, labels in spec.applies_not_in.items():
        if coordinates.get(dimension) in labels:
            return False
    return True


def mode_trait(spec: FieldSpec, mode: str | None, trait: str) -> Any:
    """One trait of one mode, or None when the map does not state it."""
    if mode is None:
        return None
    traits = spec.mode_traits.get(mode)
    if not isinstance(traits, dict):
        return None
    return traits.get(trait)


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------


def check_integrity(reading: Reading, rule: IntegrityRule) -> bool | None:
    """True (holds), False (violated), or None (cannot be evaluated).

    None matters as much as False: a rule that addresses a byte the
    frame does not have has not passed, and calling it a pass would be
    the same lie as a silent field check.
    """
    frames = reading.frames
    params = rule.params
    index = int(params.get("frame", 0) or 0)
    if index >= len(frames):
        return None
    frame = frames[index]
    if rule.type == RULE_COMPLEMENT_PAIRS:
        pairs = params.get("pairs")
        if not pairs:
            start = int(params.get("start", 0) or 0)
            count = int(params.get("count", 0) or 0)
            pairs = [[start + 2 * i, start + 2 * i + 1] for i in range(count)]
        if not pairs:
            return None
        for low, high in pairs:
            if max(low, high) >= len(frame):
                return None
            if frame[high] != (~frame[low]) & 0xFF:
                return False
        return True
    if rule.type == RULE_CHECKSUM_SUM:
        span = params.get("range")
        target = params.get("target_byte")
        if not isinstance(span, list | tuple) or len(span) != 2 \
                or not isinstance(target, int):
            return None
        first, last = int(span[0]), int(span[1])
        if last >= len(frame) or target >= len(frame):
            return None
        modulus = int(params.get("mod", 256) or 256)
        offset = int(params.get("offset", 0) or 0)
        total = (sum(frame[first:last + 1]) + offset) % modulus
        return _masked(frame[target], params) == total % 256
    if rule.type == RULE_NIBBLE_SUM:
        nibbles = params.get("nibbles")
        target = params.get("target_byte")
        if not isinstance(nibbles, list) or not isinstance(target, int):
            return None
        if target >= len(frame):
            return None
        total = 0
        for entry in nibbles:
            if not isinstance(entry, list | tuple) or len(entry) != 2:
                return None
            byte_index, half = int(entry[0]), str(entry[1])
            if byte_index >= len(frame):
                return None
            byte = frame[byte_index]
            total += (byte >> 4) if half in ("high", "hi") else (byte & 0x0F)
        modulus = int(params.get("mod", 16) or 16)
        offset = int(params.get("offset", 0) or 0)
        return _masked(frame[target], params) == (total + offset) % modulus
    if rule.type == RULE_FRAME_REPEAT:
        other = int(params.get("equals", 0) or 0)
        if other >= len(frames):
            return None
        return frames[index] == frames[other]
    return None


def _masked(byte: int, params: dict[str, Any]) -> int:
    """The part of the target byte a sum rule addresses."""
    bits = params.get("bits")
    if bits is None:
        return byte
    try:
        mask, shift = _bit_selector(str(bits))
    except ValueError:
        return byte
    return (byte & mask) >> shift
