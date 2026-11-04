"""The IR pin's corpus: every air-path code, walked through the capture path.

The radio work (RF hear, round 1) touched the models, the normalizer,
the send planner and the store backfills that every infrared row goes
through. The pin is the proof it changed nothing for infrared: each
code in the air-path fixtures, the field captures and the field packs
is handed to the native receive path exactly as a receiver would hand
it over, and what HAIR derives from it is recorded:

- ``code``, ``byte_hash``, ``fingerprint``, ``norm_fingerprint``, the
  device key and the decoded fingerprint, from ``normalize``;
- the planned sends on each emitter class (``esphome``, ``broadlink``
  and an unlisted one), three sends at the estimated spacing, from
  ``build_like_send_path`` and ``plan_send``;
- ``row_digest`` of the stored code;
- the stored records, ``UnknownSignal.to_dict`` and
  ``IRCommand.to_dict``, with the id and the timestamps fixed, so a key
  added to an infrared record fails here.

Each row reduces to a short digest of all of that. The baseline holds
one digest per row, keyed by source and index, and was generated at the
base commit by ``tests/tools/gen_ir_pin.py``. Only APIs that exist at
that commit are used here, so the same file runs on both sides.

The field packs are SmartIR files in Broadlink base64; they are read
with the store reader HAIR uses for Broadlink codes. Every code is
taken as the file holds it; the air model of the real-air harness is
not applied, because that harness already pins what the air does and
this file pins what the pipeline does with a given capture.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import types
from dataclasses import dataclass
from pathlib import Path

TESTS = Path(__file__).resolve().parent
FIXTURES = TESTS / "fixtures"

#: The directories walked, relative to ``FIXTURES``.
DIRECTORIES = ("air-path", "field-captures", "field-packs")

#: The emitter classes a planned send is recorded for. ``None`` is an
#: emitter on no exact platform, which takes today's loop.
PLATFORMS = ("esphome", "broadlink", None)

SEND_COUNT = 3
FIXED_ID = "irpin"
FIXED_TIME = "2026-01-01T00:00:00+00:00"

_PRONTO = re.compile(r"^\s*0000( [0-9A-Fa-f]{4}){5,}\s*$")
_B64 = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")


@dataclass(frozen=True)
class PinInput:
    """One code to press: where it came from and what it is."""

    source: str
    index: int
    path: str
    kind: str  # "pronto", "timings" or "broadlink"
    value: object

    @property
    def key(self) -> str:
        return f"{self.source}#{self.index}"


def _load(path: Path):
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = path.read_text(encoding="utf-8")
    if path.name.endswith((".json", ".json.gz")):
        return json.loads(text)
    return text


def _walk(value, path: str, out: list[tuple[str, str, object]]) -> None:
    """Every code inside a JSON fixture, in document order."""
    if isinstance(value, dict):
        for key in value:
            _walk(value[key], f"{path}/{key}", out)
    elif isinstance(value, list):
        if (
            len(value) >= 6
            and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
            and all(v != 0 for v in value)
        ):
            out.append((path, "timings", list(value)))
            return
        for position, item in enumerate(value):
            _walk(item, f"{path}[{position}]", out)
    elif isinstance(value, str):
        if _PRONTO.match(value):
            out.append((path, "pronto", value.strip()))
        elif _B64.match(value):
            out.append((path, "broadlink", value))


def _csv_rows(text: str) -> list[tuple[str, str, object]]:
    out: list[tuple[str, str, object]] = []
    for number, row in enumerate(csv.DictReader(io.StringIO(text))):
        if row.get("timings_us"):
            out.append((f"row{number}", "timings", json.loads(row["timings_us"])))
        elif row.get("code") and _PRONTO.match(row["code"]):
            out.append((f"row{number}", "pronto", row["code"].strip()))
    return out


def corpus() -> list[PinInput]:
    """Every code the pin presses, sorted by source then position."""
    rows: list[PinInput] = []
    for directory in DIRECTORIES:
        for path in sorted((FIXTURES / directory).iterdir()):
            name = path.name
            source = f"{directory}/{name}"
            if name.endswith((".json", ".json.gz")):
                found: list[tuple[str, str, object]] = []
                _walk(_load(path), "", found)
            elif name.endswith((".csv", ".csv.gz")):
                found = _csv_rows(_load(path))
            elif name.endswith(".pronto"):
                found = [
                    (f"line{n}", "pronto", line.strip())
                    for n, line in enumerate(_load(path).splitlines())
                    if _PRONTO.match(line)
                ]
            else:
                continue
            rows.extend(
                PinInput(source, index, where, kind, value)
                for index, (where, kind, value) in enumerate(found)
            )
    return rows


def _signed(timings: list[int]) -> list[int]:
    """Signed microseconds, the way a native receiver delivers them."""
    if any(v < 0 for v in timings):
        return [int(v) for v in timings]
    return [int(v) if i % 2 == 0 else -int(v) for i, v in enumerate(timings)]


def _received(item: PinInput):
    """The ``(timings, modulation)`` a receiver hands over, or a label."""
    from custom_components.hair.ir_command import ProntoCommand
    from custom_components.hair.learned_code_stores import decode_broadlink_code

    if item.kind == "broadlink":
        pronto, _timings, receipt, kind = decode_broadlink_code(item.value)
        if pronto is None:
            return None, f"unread:{kind}:{receipt}"
        item_value = pronto
    elif item.kind == "pronto":
        item_value = item.value
    else:
        return (_signed(item.value), None), None
    try:
        command = ProntoCommand(item_value)
        raw = list(command.get_raw_timings())
        modulation = getattr(command, "modulation", None)
    except Exception as err:  # the label is the row
        return None, f"pronto:{type(err).__name__}"
    return (_signed(raw), modulation), None


def _digest(value) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _plans(row) -> list:
    from custom_components.hair import send_plan

    try:
        inner = send_plan.build_like_send_path(row)
    except Exception as err:
        return [f"build:{type(err).__name__}"]
    if inner is None:
        return ["build:None"]
    try:
        spacing = send_plan.estimate_spacing_ms(inner)
    except Exception as err:
        return [f"spacing:{type(err).__name__}"]
    out: list = [spacing, _digest(list(inner.get_raw_timings()))]
    for platform in PLATFORMS:
        try:
            plan = send_plan.plan_send(inner, SEND_COUNT, spacing, platform)
        except Exception as err:
            out.append(f"plan:{type(err).__name__}")
            continue
        if plan is None:
            out.append(None)
            continue
        out.append([
            plan.exact,
            plan.chunks,
            round(plan.sleep_s, 6),
            round(plan.air_s, 6),
            [
                [
                    call.terminate,
                    round(call.air_s, 6),
                    _digest(list(call.command.get_raw_timings())),
                ]
                for call in plan.calls
            ],
        ])
    return out


def identity_of(item: PinInput) -> dict:
    """Everything HAIR derives from one code, as plain values."""
    from custom_components.hair.event_parser import EventParser
    from custom_components.hair.models import (
        CommandCategory,
        UnknownSignal,
    )
    from custom_components.hair.signal_monitor import normalize
    from custom_components.hair.wig_format import row_digest

    received, label = _received(item)
    if received is None:
        return {"label": label}
    timings, modulation = received
    parsed = EventParser.parse_received_signal(
        types.SimpleNamespace(timings=timings, modulation=modulation)
    )
    if parsed is None:
        return {"label": "parse:None"}
    n = normalize(parsed)

    signal = UnknownSignal(
        id=FIXED_ID,
        fingerprint=n.sig_fp,
        byte_hash=n.byte_hash,
        decoded_protocol=n.decoded_protocol,
        decoded_address=n.decoded_address,
        decoded_command=n.decoded_command,
        decoded_fingerprint=n.decoded_fingerprint,
        decoded_extras=n.decoded_extras,
        protocol=n.protocol,
        code=n.code,
        raw_timings=list(n.raw_timings),
        frequency=n.frequency,
        hit_count=1,
        first_seen=FIXED_TIME,
        last_seen=FIXED_TIME,
        decode_covers=n.decode_covers,
    )
    command = parsed.to_command("pin", CommandCategory.CUSTOM)
    command.id = FIXED_ID
    command.decoded_protocol = n.decoded_protocol
    command.decoded_address = n.decoded_address
    command.decoded_command = n.decoded_command
    command.decoded_fingerprint = n.decoded_fingerprint
    command.decoded_extras = n.decoded_extras
    command.decode_covers = n.decode_covers
    for name in ("created_at", "updated_at"):
        if hasattr(command, name):
            setattr(command, name, FIXED_TIME)

    return {
        "code": n.code,
        "byte_hash": n.byte_hash,
        "fingerprint": n.sig_fp,
        "norm_fingerprint": n.norm_fp,
        "device_key": n.dev_fp,
        "decoded_fingerprint": n.decoded_fingerprint,
        "frequency": n.frequency,
        "row_digest": row_digest(n.code) if n.code else None,
        "sends": _plans(command),
        "signal_record": _digest(signal.to_dict()),
        "command_record": _digest(command.to_dict()),
    }


def row_hash(item: PinInput) -> str:
    """The one value the baseline stores per row."""
    return _digest(identity_of(item))


def pin() -> dict[str, list[str]]:
    """Row digests per source, in corpus order."""
    out: dict[str, list[str]] = {}
    for item in corpus():
        out.setdefault(item.source, []).append(row_hash(item))
    return out
