"""The corpus the no-steal census walks, and how a row is addressed.

THE CENSUS IS THE PACK'S LICENCE. Four decoders that read the NEC1 frame
shape arrive in one patch, and the only honest way to show none of them
took a frame that belonged to something else is to record what the tree
decoded BEFORE they existed and assert it afterwards, row by row.

Two rules make it able to fail, both from review round 1:

1. ``raw`` IS A LABEL. A row no decoder claims is recorded as ``raw``,
   not omitted. A row that was ``raw`` and is now claimed is the exact
   shape of a false positive -- a decoder finding a frame inside a blob
   that is not one -- so the test fails on it unless the fixture is on
   the allowlist in ``test_no_steal_census.py`` naming the family the
   pack is expected to claim there.
2. ROWS ARE KEYED BY (file, index), never by position in a flat list.
   A later phase adding a fixture must not read as every later row
   changing. A key absent from the baseline is a new row: reported,
   never a failure. A key present whose label moved always fails.

The corpus is every fixture under ``tests/fixtures/`` that decodes to
timings by any route this repo can read, plus every inline capture the
test modules expose. The inline half matters: eighteen modules carry
literal NEC-shaped timing lists, and a census that walked only the
fixture tree would have missed most of the repo's NEC captures.

Readers are deliberately tolerant. Anything that does not yield timings
is skipped rather than raising, because the corpus is a moving target
and a census that dies on a new fixture shape is a census nobody runs.
"""
from __future__ import annotations

import ast
import base64
import csv
import gzip
import io
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
TESTS = Path(__file__).parent

# Broadlink tick, the same figure ``wig_adapters`` uses. Duplicated here
# rather than imported so the corpus reader keeps working if the adapter
# module is mid-edit; a census that cannot be generated is no licence.
_BROADLINK_TICK_US = 1_000_000 / 32_768

# A Pronto word run long enough to be a code rather than a hex-looking
# sentence. Six pairs is below any real code and above any accident.
_PRONTO_RE = re.compile(r"(?:[0-9A-Fa-f]{4}\s+){6,}[0-9A-Fa-f]{4}")


@dataclass(frozen=True)
class CensusRow:
    """One addressable capture: where it came from and its timings."""

    source: str  # repo-relative path, or "TEST:<module>"
    index: str  # stable within the source; a path, a name or an offset
    timings: list[int]

    @property
    def key(self) -> str:
        return f"{self.source}#{self.index}"


def _pronto_to_raw(text: str) -> list[int] | None:
    """Pronto hex to signed microseconds, or None.

    A local reader on purpose: ``ProntoCommand`` strips a trailing space
    and raises on shapes this corpus would rather skip, and the census
    wants the timings a decoder would see, not a validated command.
    """
    try:
        words = [int(w, 16) for w in text.split()]
    except ValueError:
        return None
    if len(words) < 4 or words[1] == 0:
        return None
    period = words[1] * 0.241246
    pairs = words[2] + words[3]
    body = words[4:]
    if len(body) < pairs * 2:
        return None
    out: list[int] = []
    for i in range(pairs):
        out.append(round(body[2 * i] * period))
        space = round(body[2 * i + 1] * period)
        if space > 0:
            out.append(-space)
    if out and out[-1] < 0:
        out.pop()
    return out or None


def _broadlink_to_raw(packet: bytes) -> list[int] | None:
    """Broadlink IR packet to signed microseconds, or None."""
    if len(packet) < 6 or packet[0] != 0x26:
        return None
    length = packet[2] | (packet[3] << 8)
    data = packet[4:4 + length]
    values: list[int] = []
    i = 0
    while i < len(data):
        value = data[i]
        i += 1
        if value == 0:
            if i + 1 >= len(data):
                break
            value = (data[i] << 8) | data[i + 1]
            i += 2
        values.append(round(value * _BROADLINK_TICK_US))
    if not values:
        return None
    return [v if n % 2 == 0 else -v for n, v in enumerate(values)]


def _maybe_base64(text: str) -> list[int] | None:
    if len(text) < 40 or not re.fullmatch(r"[A-Za-z0-9+/=\s]+", text):
        return None
    try:
        return _broadlink_to_raw(base64.b64decode(text))
    except Exception:
        return None


def _walk_json(obj: object, source: str, path: str) -> Iterator[CensusRow]:
    """Every capture inside a parsed JSON document, addressed by path."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_json(value, source, f"{path}/{key}")
        return
    if isinstance(obj, list):
        if obj and all(isinstance(v, int) for v in obj) and len(obj) >= 20:
            yield CensusRow(source, path or "/", list(obj))
            return
        for n, value in enumerate(obj):
            yield from _walk_json(value, source, f"{path}[{n}]")
        return
    if isinstance(obj, str):
        text = obj.strip()
        raw = _maybe_base64(text)
        if raw is not None:
            yield CensusRow(source, path, raw)
            return
        if _PRONTO_RE.fullmatch(text):
            raw = _pronto_to_raw(text)
            if raw is not None:
                yield CensusRow(source, path, raw)


def _read(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", errors="replace") as handle:
            return handle.read()
    return path.read_text(errors="replace")


def _fixture_rows(path: Path) -> Iterator[CensusRow]:
    source = str(path.relative_to(FIXTURES.parent))
    try:
        text = _read(path)
    except Exception:
        return

    if path.name.endswith((".json", ".json.gz", ".partial")):
        try:
            yield from _walk_json(json.loads(text), source, "")
            return
        except Exception:
            pass  # fall through to the text scanners

    if path.name.endswith(".csv.gz"):
        for row in csv.DictReader(io.StringIO(text)):
            try:
                values = json.loads(row["timings_us"])
            except Exception:
                continue
            signed = [v if n % 2 == 0 else -v for n, v in enumerate(values)]
            yield CensusRow(source, row.get("code") or "?", signed)
        return

    if path.suffix == ".ir":
        # Flipper raw blocks: "data: 9000 4500 560 ..." unsigned.
        for match in re.finditer(r"name:\s*(\S+)[\s\S]*?data:\s*([\d\s]+)", text):
            values = [int(v) for v in match.group(2).split()]
            if len(values) >= 20:
                yield CensusRow(
                    source, match.group(1),
                    [v if n % 2 == 0 else -v for n, v in enumerate(values)],
                )

    if path.name.endswith(".conf.excerpt") or path.suffix == ".conf":
        # LIRC raw_codes blocks.
        for match in re.finditer(r"name\s+(\S+)\n((?:\s+\d[\d\s]*\n)+)", text):
            values = [int(v) for v in match.group(2).split()]
            if len(values) >= 20:
                yield CensusRow(
                    source, match.group(1),
                    [v if n % 2 == 0 else -v for n, v in enumerate(values)],
                )

    for match in _PRONTO_RE.finditer(text):
        raw = _pronto_to_raw(match.group(0))
        if raw is not None:
            yield CensusRow(source, f"pronto@{match.start()}", raw)


def _inline_rows(path: Path) -> Iterator[CensusRow]:
    """Inline captures in one test module, addressed by source offset.

    Parsed with ``ast`` rather than a regex over the text: a list
    literal of signed ints is unambiguous in the tree and guessable at
    best in the text, and the offset of the node is a stable key.
    """
    source = f"TEST:{path.name}"
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and len(node.elts) >= 20:
            values: list[int] = []
            for element in node.elts:
                if isinstance(element, ast.Constant) and isinstance(
                    element.value, int
                ):
                    values.append(element.value)
                elif (
                    isinstance(element, ast.UnaryOp)
                    and isinstance(element.op, ast.USub)
                    and isinstance(element.operand, ast.Constant)
                    and isinstance(element.operand.value, int)
                ):
                    values.append(-element.operand.value)
                else:
                    values = []
                    break
            if values:
                yield CensusRow(
                    source, f"line{node.lineno}col{node.col_offset}", values
                )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value.strip()
            if _PRONTO_RE.fullmatch(text):
                raw = _pronto_to_raw(text)
                if raw is not None:
                    yield CensusRow(
                        source, f"line{node.lineno}col{node.col_offset}", raw
                    )


def _adapter_rows(path: Path) -> Iterator[CensusRow]:
    """What an importable fixture becomes after conversion.

    THE OTHER HALF OF THE CORPUS, and the half that catches the change
    this pack actually makes to a file on disk. A Flipper ``parsed``
    line carries no timings at all: it names a protocol and two field
    values, and the waveform only exists once a builder has rendered it.
    Walking the file's bytes therefore sees nothing, and the repo's
    Apple fixture -- the one fixture whose stored waveform this pack
    deliberately changes -- would sit outside a census meant to notice
    exactly that.

    So importable fixtures are also converted and their rendered Pronto
    walked. Addressed under a separate ``adapters:`` source so a reader
    can tell a rendered row from a row that was in the file.
    """
    source = f"adapters:{path.name}"
    try:
        from custom_components.hair.wig_adapters import convert

        result = convert(path.read_text(errors="replace"), path.name)
    except Exception:
        return
    for wig in result.wigs or []:
        for signal in wig.signals or []:
            raw = _pronto_to_raw(signal.pronto or "")
            if raw is not None:
                yield CensusRow(source, signal.alias or "?", raw)


def corpus() -> list[CensusRow]:
    """Every capture the census walks, in a stable order."""
    rows: list[CensusRow] = []
    for path in sorted(FIXTURES.rglob("*")):
        if path.is_file():
            rows.extend(_fixture_rows(path))
    for path in sorted((FIXTURES / "adapters").glob("*")):
        if path.is_file():
            rows.extend(_adapter_rows(path))
    for path in sorted(TESTS.glob("*.py")):
        rows.extend(_inline_rows(path))
    conftest = TESTS.parent.parent.parent / "conftest.py"
    if conftest.is_file():
        rows.extend(_inline_rows(conftest))
    seen: set[str] = set()
    unique: list[CensusRow] = []
    for row in rows:
        if row.key in seen:
            continue
        seen.add(row.key)
        unique.append(row)
    return unique


def label_for(timings: list[int]) -> str:
    """The protocol label the live tree gives these timings, or ``raw``.

    ``raw`` is a label and not an absence: it is what the census has to
    be able to see change.
    """
    from custom_components.hair.protocol_decode import try_decode_identity

    try:
        identity = try_decode_identity(timings)
    except Exception:
        return "raw"
    return "raw" if identity is None else identity.protocol


def census() -> dict[str, str]:
    """``{row key: label}`` for the whole corpus."""
    return {row.key: label_for(row.timings) for row in corpus()}


def sources() -> dict[str, int]:
    """``{source: row count}``, for the report's walk list."""
    counts: dict[str, int] = {}
    for row in corpus():
        counts[row.source] = counts.get(row.source, 0) + 1
    return counts
