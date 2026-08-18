"""The receiver-tolerant fingerprint, against real air captures.

Every number asserted here was measured on the bench on 2026-08-17 and
is carried in ``fixtures/air-path/`` (see the README there). The point
of the tier is that a code HAIR knows only from a file matches its own
capture over a real air path, so the tests are captures, not synthetic
timings: ten presses per code per transmitter, through the best
transmitter available (a microsecond-accurate ESP32) and the worst
(a consumer Broadlink blaster on a 32.84 us tick).
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from pathlib import Path

import pytest

from custom_components.hair.identity import (
    NormFpIndex,
    canonical_edges,
    canonical_fingerprint,
    first_frame,
    norm_fingerprint,
    norm_fingerprint_of_code,
)
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.wig_identity import wig_signal_identity

FIXTURES = Path(__file__).parent / "fixtures" / "air-path"


def _captures() -> list[dict]:
    with gzip.open(FIXTURES / "captures.csv.gz", "rt", encoding="utf-8") as fh:
        return list(csv.DictReader(io.StringIO(fh.read())))


def _code(name: str) -> str:
    return (FIXTURES / f"{name}.pronto").read_text(encoding="utf-8").strip()


def _wig_codes(filename: str) -> dict:
    with gzip.open(FIXTURES / filename, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _timings(row: dict) -> list[int]:
    """A capture's edges as HAIR sees them (mark positive, space negative)."""
    values = json.loads(row["timings_us"])
    return [v if i % 2 == 0 else -abs(v) for i, v in enumerate(values)]


# --- the strip ------------------------------------------------------------


def test_canonical_edges_leaves_the_list_ending_on_a_mark():
    """One rule for both sides: no trailing space, no trailing zeros.

    The air-path run measured the same code presenting as 67 edges from
    the file path and 68 from the capture path, purely because a
    receiver appends its terminating silence and the Pronto round trip
    renders the file's inter-frame gap as a zero word.
    """
    assert canonical_edges([100, -200, 300, -9992]) == [100, 200, 300]
    assert canonical_edges([100, -200, 300, 0]) == [100, 200, 300]
    assert canonical_edges([100, -200, 300]) == [100, 200, 300]
    assert canonical_edges([]) == []
    # signed=True gives HAIR's own convention back.
    assert canonical_edges([100, -200, 300, -9992], signed=True) == [
        100, -200, 300,
    ]


def test_canonical_edges_is_idempotent():
    once = canonical_edges(_timings(_captures()[0]))
    assert canonical_edges(once) == once


def test_capture_and_file_agree_on_edge_count_after_the_strip():
    """The count is load-bearing, and only the strip makes it stable.

    One capture in the run genuinely lost two edges: a Broadlink send of
    C2 the receiver clipped. It is the same capture that misses the
    fingerprint below, and it is the whole reason the Broadlink is on
    the bench -- a code that only survives the good transmitter has not
    been tested.
    """
    short = []
    for name in ("C1", "C2", "F1"):
        file_edges = canonical_edges(
            first_frame(
                canonical_edges(ProntoCommand(_code(name)).get_raw_timings())
            )
        )
        for row in _captures():
            if row["code"] != name or row["transmitter"] == "inject":
                continue
            heard = canonical_edges(first_frame(canonical_edges(_timings(row))))
            if len(heard) != len(file_edges):
                short.append(
                    (name, row["transmitter"], len(heard), len(file_edges))
                )
    assert short == [("C2", "broadlink", 289, 291)]


# --- the fingerprint, against the air --------------------------------------


@pytest.mark.parametrize("name", ["C1", "C2", "F1"])
def test_every_air_capture_matches_its_file(name: str):
    """The property the byte hash lacks.

    34 of 35 captures across two transmitters. The one miss is a
    Broadlink capture of C2 and is asserted as such below rather than
    hidden: the worst transmitter we own does miss one press in nine,
    and a test that pretended otherwise would be lying about the bench.
    """
    expected = norm_fingerprint_of_code(_code(name))
    assert expected is not None
    misses = [
        row["first_seen"]
        for row in _captures()
        if row["code"] == name
        and row["transmitter"] != "inject"
        and norm_fingerprint(_timings(row)) != expected
    ]
    allowed = 1 if name == "C2" else 0
    assert len(misses) == allowed, f"{name} missed on {misses}"


def test_the_injected_control_matches_its_file():
    """The bench_rx inject hands over the file's own timings.

    It matched on the byte hash too, which is what proved the identity
    code was right and the air was what moved.
    """
    for name in ("C1", "C2", "F1"):
        expected = norm_fingerprint_of_code(_code(name))
        for row in _captures():
            if row["code"] == name and row["transmitter"] == "inject":
                assert norm_fingerprint(_timings(row)) == expected


def test_two_frames_of_one_press_carry_one_fingerprint():
    """A C1 press is two identical frames; the receiver stores each.

    The file holds all 584 edges, a capture holds the 292 of one frame,
    so both sides reduce to their first frame before hashing. Either
    half therefore works as the press.
    """
    whole = ProntoCommand(_code("C1")).get_raw_timings()
    edges = canonical_edges(whole)
    frame = first_frame(edges)
    assert 0 < len(frame) < len(edges)
    assert norm_fingerprint(edges) == norm_fingerprint(frame)
    second = edges[len(frame):]
    assert norm_fingerprint(second) == norm_fingerprint(frame)


def test_the_byte_hash_is_what_fails_over_the_air():
    """The finding itself, pinned so nobody re-derives it by hand.

    Twenty ESPHome presses of C2 produced twenty byte hashes and not one
    of them was the file's.
    """
    rows = [
        r for r in _captures()
        if r["code"] == "C2" and r["transmitter"] == "esphome"
    ]
    assert len(rows) == 20
    hashes = {r["byte_hash"] for r in rows}
    assert len(hashes) == 20
    file_identity = wig_signal_identity(_code("C2"))
    assert file_identity is not None
    assert file_identity.byte_hash not in hashes


# --- distinctness ----------------------------------------------------------


def test_the_mitsubishi_lattice_stays_34_distinct_codes():
    """64 cells, 34 distinct codes, 34 distinct normalized fingerprints.

    The lattice stores the same code sixteen times over for dry and
    sixteen for fan_only, because the unit ignores temperature in those
    modes. Nothing else collides: no two cells differing in mode or
    temperature share a value.
    """
    data = _wig_codes("sg15h-matrix.json.gz")
    codes = [entry["pronto"] for entry in data["codes"]]
    assert len(codes) == 34
    fingerprints = {norm_fingerprint_of_code(code) for code in codes}
    assert None not in fingerprints
    assert len(fingerprints) == 34
    off = norm_fingerprint_of_code(data["off"])
    assert off is not None and off not in fingerprints


def test_the_acer_wig_stays_16_distinct_signals():
    """The flat undecoded case: 16 signals, 16 values, no collisions."""
    data = _wig_codes("acer-rc-17de0.json.gz")
    codes = [entry["pronto"] for entry in data["signals"]]
    assert len(codes) == 16
    fingerprints = {norm_fingerprint_of_code(code) for code in codes}
    assert None not in fingerprints
    assert len(fingerprints) == 16


# --- the two paths agree ---------------------------------------------------


def test_d1_fingerprint_agrees_across_both_paths():
    """The wig path and the Pronto path land on one S/L fingerprint.

    D1 is the decoded control (SAMSUNG32:0x0007:0x02 on every capture
    from every source). Its air captures legitimately differ in the S/L
    fingerprint -- the Samsung end mark fuses with the following frame
    on this receiver, a real waveform difference, and the decoded tier
    is what carries it. What must not differ is HAIR's two internal
    readings of the same file text.
    """
    code = _code("D1")
    identity = wig_signal_identity(code)
    assert identity is not None
    assert identity.fingerprint == canonical_fingerprint("PRONTO", code, None)
    assert identity.decoded_fingerprint == "SAMSUNG32:0x0007:0x02"
    for row in _captures():
        if row["code"] == "D1":
            assert row["decoded_fingerprint"] == identity.decoded_fingerprint


def test_a_structureless_code_gets_no_fingerprint():
    """Every run in one level would match anything of the same length."""
    assert norm_fingerprint([500, -500, 500, -500, 500, -500]) is None
    assert norm_fingerprint_of_code(None) is None
    assert norm_fingerprint_of_code("not a pronto code") is None


# --- ambiguity -------------------------------------------------------------


def test_the_index_refuses_a_value_two_different_codes_claim():
    """Reporting the wrong state is worse than reporting none.

    Measured across the bench closet, 13 of 2,354 normalized values are
    claimed by two genuinely different waveforms. Those values answer
    None rather than handing back whichever record was indexed last.
    """
    index = NormFpIndex()
    index.add("aaaa", "hash-1", "cool/auto/23")
    assert index.get("aaaa") == "cool/auto/23"
    # The same waveform under a second name is not a conflict.
    index.add("aaaa", "hash-1", "cool/auto/23-again")
    assert index.get("aaaa") == "cool/auto/23-again"
    # A different code claiming it poisons the value, permanently.
    index.add("aaaa", "hash-2", "heat/low/20")
    assert index.get("aaaa") is None
    index.add("aaaa", "hash-1", "cool/auto/23")
    assert index.get("aaaa") is None
    assert "aaaa" in index.ambiguous


def test_the_index_ignores_an_absent_fingerprint():
    index = NormFpIndex()
    index.add(None, "hash-1", "ref")
    assert not index
    assert index.get(None) is None
