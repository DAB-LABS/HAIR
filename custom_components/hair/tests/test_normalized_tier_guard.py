"""The normalized tier does not name a press its own field map reads as
other settings.

That tier quantizes a waveform to a few levels so a receiver's drift
cannot lose a press, which also means a drift across one level boundary
can turn a press's fingerprint into its neighbour's. On the air bench of
2026-10-08 (SmartIR 2041, TCL112, through a Broadlink into a reflashed
Athom, 1,120 presses) three whole presses were heard that way, each
answered on the normalized tier by the box's own log line. TCL112's map
read every one of those captures, and read the state that was pressed.
So when the normalized tier would answer, the map that reads the heard
cell's code reads the capture too, and a capture it reads as other
settings than the cell is not answered there (``CellIndex.match``).

A capture that map cannot read is answered as before: that tier exists
to hear glitched presses and lone pieces the map declines, and refusing
them would have cost 2,637 of 6,004 correct hearings on the real-air
harness and 358 of 1,366 on that bench. The three glitched GREE presses
of the harness are that kind (frame 0 broken), so they stay heard as the
next fan speed, pinned in ``test_real_air_harness`` and
``test_closing_space``.

``fixtures/air-path/normalized-tier.json.gz`` holds the three wrong
captures and, per run, up to twenty captures the box heard as their own
cell on the normalized tier and the capture path here places the same
way. The two SmartIR files are the lattices of the 1030 and 2041 runs.
"""
from __future__ import annotations

import functools
import gzip
import json
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import TIER_NORM_FP, norm_fingerprint
from custom_components.hair.matrix_listener import (
    _index_to_payload,
    _payload_to_index,
    build_cell_index,
    tier_name,
)
from custom_components.hair.signal_monitor import SignalMonitor, normalize
from custom_components.hair.wig_adapters import convert
from custom_components.hair.wig_format import cell_key
from custom_components.hair.wig_identity import wig_signal_identity

from .merged_group_shapes import FIXTURES, PinnedBench
from .test_cell_index_shared_keys import _pack_matrix

AIR = FIXTURES / "air-path"
with gzip.open(AIR / "normalized-tier.json.gz", "rt", encoding="utf-8") as _f:
    BENCH = json.load(_f)


@functools.cache
def _matrix(source: str):
    if source.startswith("smartir-"):
        with gzip.open(AIR / f"{source}.json.gz", "rt", encoding="utf-8") as f:
            return convert(f.read(), f"{source}.json").wigs[0].climate
    return _pack_matrix(f"{source}.json")


@functools.cache
def _index(source: str):
    return build_cell_index(_matrix(source))


def _code(source: str, key: str) -> str:
    return next(c.pronto for c in _matrix(source).cells if cell_key(c) == key)


def _capture_path(pronto: str):
    """What the box computes for a capture: the receiver's timings,
    closing space included, through the native receiver path."""
    timings = fr.pronto_microseconds(pronto)
    while timings and timings[-1] == 0:
        timings.pop()
    signal = types.SimpleNamespace(timings=timings, modulation=38000)
    return normalize(EventParser.parse_received_signal(signal))


def _heard(index, pronto: str, *, compare: bool = True):
    n = _capture_path(pronto)
    hit = index.match(n.decoded_fingerprint, n.sig_fp, n.byte_hash, n.norm_fp,
                      n.decode_covers, n.raw_timings if compare else None)
    return None if hit is None else (hit[0].cell_key, tier_name(hit[1]))


def _norm_key(pronto: str) -> str:
    """The normalized key a cell's code claims in the index."""
    return norm_fingerprint(wig_signal_identity(pronto).raw_timings)


def test_the_bench_rows_are_here():
    assert [(w["pressed"], w["heard"]) for w in BENCH["wrong"]] == [
        ("heat_cool/level1/83", "heat_cool/level1/72"),
        ("heat_cool/level5/73", "heat_cool/level5/85"),
        ("heat_cool/silent/78", "heat_cool/level1/78"),
    ]
    runs: dict[tuple, int] = {}
    for row in BENCH["own"]:
        runs[(row["lattice"], row["shape"])] = runs.get(
            (row["lattice"], row["shape"]), 0) + 1
    assert runs == {
        ("MITSUBISHI144", "whole"): 20,
        ("PANASONIC216", "whole"): 20,
        ("PANASONIC216", "pieces"): 20,
        ("TCL112", "whole"): 2,
        ("smartir-1030", "whole"): 20,
        ("smartir-2041", "whole"): 20,
    }


@pytest.mark.parametrize("row", BENCH["wrong"], ids=lambda r: r["pressed"])
class TestATcl112PressHeardAsItsNeighbour:

    def test_the_map_reads_the_capture_as_the_state_pressed(self, row):
        """Why the defect is not a refused press: the map read it, and
        read the state that was pressed, not the one that was heard."""
        got = fr.read_settings(row["received"], "TCL112")
        pressed = fr.read_settings(_code(row["lattice"], row["pressed"]))
        heard = fr.read_settings(_code(row["lattice"], row["heard"]))
        assert got is not None and pressed is not None and heard is not None
        assert got == pressed
        assert fr.settings_differ(got[1], heard[1])

    def test_the_walk_and_the_frame_widths_accept_it(self, row):
        """Why refusing on the walk, or on a frame-width bound, would
        not have touched it."""
        tcl = next(m for m in fr.library() if m.protocol_id == "TCL112")
        train = fr.pronto_microseconds(row["received"])
        assert fr.walk_refusal(tcl.timing, train) is None
        assert fr.read_code(row["received"], [tcl]).protocol_id == "TCL112"

    @pytest.mark.parametrize("form", ["train", "pronto"])
    def test_on_the_key_the_box_answered_it_names_nothing(self, row, form):
        """The box's own line: the capture's normalized fingerprint was
        the heard cell's key. Asked on that key, the tier named the
        neighbour without the capture, and names nothing with it, given
        as the receiver's train (what the capture path passes) or as the
        Pronto the Sniffer stored."""
        index = _index(row["lattice"])
        key = _norm_key(_code(row["lattice"], row["heard"]))
        assert index.norm_readings[key]
        before = index.match(None, None, None, key, None)
        assert before is not None
        assert (before[0].cell_key, before[1]) == (row["heard"], TIER_NORM_FP)
        capture = (
            _capture_path(row["received"]).raw_timings if form == "train"
            else row["received"]
        )
        assert index.match(None, None, None, key, None, capture) is None

    def test_through_the_capture_path_it_is_not_the_neighbour(self, row):
        """Recomputed from the Sniffer's Pronto the capture's levels can
        land differently from the box's (the quantization the code
        carries), so the heard cell is pinned as the box logged it and
        the recompute's answer without the comparison is recorded beside
        it in the fixture. Two of the three recompute to the neighbour,
        and only those two test the comparison here; the third already
        lands on its own cell, and the key test above covers it."""
        index = _index(row["lattice"])
        before = _heard(index, row["received"], compare=False)
        assert list(before) == row["offline"]
        after = _heard(index, row["received"])
        assert after is None or after[0] != row["heard"]


@pytest.mark.parametrize(
    "row", BENCH["own"],
    ids=lambda r: f"{r['lattice']}-{r['shape']}-{r['pressed']}",
)
def test_a_press_the_box_heard_right_on_the_normalized_tier_still_is(row):
    assert _heard(_index(row["lattice"]), row["received"]) == (
        row["heard"], "normalized")


def test_a_key_with_a_cell_no_map_reads_compares_nothing():
    """A key the map cannot speak for in full keeps today's behaviour:
    the build stores no reading for it, and with none stored the tier
    answers as it always did."""
    import dataclasses

    wrong = BENCH["wrong"][0]
    built = _index(wrong["lattice"])
    key = _norm_key(_code(wrong["lattice"], wrong["heard"]))
    readings = dict(built.norm_readings)
    readings.pop(key)
    index = dataclasses.replace(built, norm_readings=readings)
    hit = index.match(None, None, None, key, None, wrong["received"])
    assert hit is not None and hit[0].cell_key == wrong["heard"]


def test_a_capture_is_refused_only_against_every_claimant():
    """A key whose claimants read as more than one setting answers a
    capture that reads as any of them."""
    import dataclasses

    wrong = BENCH["wrong"][0]
    built = _index(wrong["lattice"])
    key = _norm_key(_code(wrong["lattice"], wrong["heard"]))
    pressed = built.norm_readings[_norm_key(_code(wrong["lattice"],
                                                  wrong["pressed"]))]
    readings = dict(built.norm_readings)
    readings[key] = built.norm_readings[key] + pressed
    index = dataclasses.replace(built, norm_readings=readings)
    hit = index.match(None, None, None, key, None, wrong["received"])
    assert hit is not None and hit[0].cell_key == wrong["heard"]


@pytest.mark.parametrize("pack", ["GREE", "TCL112", "MITSUBISHI144"])
def test_a_field_the_file_never_varies_is_not_compared(pack):
    """It cannot tell two cells apart, only refuse a press that sets it
    otherwise: GREE's swing, in the frame its fingerprint does not
    cover, from a handset with swing on against a file stored without."""
    matrix = _pack_matrix(f"{pack}.json")
    index = build_cell_index(matrix)
    field_map = next(m for m in fr.library() if m.protocol_id == pack)
    values = [fr.read_settings(c.pronto) for c in matrix.cells]
    for position, spec in enumerate(field_map.fields):
        constant = len({v[1][position] for v in values if v}) == 1
        stored = {
            reading[1][position]
            for readings in index.norm_readings.values()
            for reading in readings
        }
        if constant:
            assert stored == {None}, spec.name
    gree = {"GREE": "swing"}.get(pack)
    if gree:
        position = [f.name for f in field_map.fields].index(gree)
        assert {r[1][position] for rs in index.norm_readings.values()
                for r in rs} == {None}


def test_readings_of_another_length_compare_nothing():
    """A stored reading that does not fit the map (a hand-edited index)
    does not raise on the capture path; it compares nothing."""
    import dataclasses

    wrong = BENCH["wrong"][0]
    built = _index(wrong["lattice"])
    key = _norm_key(_code(wrong["lattice"], wrong["heard"]))
    family, values = built.norm_readings[key][0]
    readings = dict(built.norm_readings)
    readings[key] = ((family, values[:-1]),)
    index = dataclasses.replace(built, norm_readings=readings)
    hit = index.match(None, None, None, key, None, wrong["received"])
    assert hit is not None and hit[0].cell_key == wrong["heard"]


@pytest.mark.asyncio
async def test_the_listener_hears_nothing_rather_than_the_neighbour():
    """The whole hop, capture path to state_heard: given the train, the
    remote does not report the neighbour; without it, it did."""
    from custom_components.hair.models import TriggerRemote

    from .test_matrix_listener import _listener_ready

    wrong = next(w for w in BENCH["wrong"] if w["offline"][0] == w["heard"])
    n = _capture_path(wrong["received"])
    for capture, expected in ((None, [wrong["heard"]]), (n.raw_timings, [])):
        remote = TriggerRemote(id="r1", name="TCL", climate_matrix=True)
        hass, _store, listener = _listener_ready(
            remote, matrix=_matrix("TCL112"))
        listener._matrix_cache[remote.id] = _matrix(wrong["lattice"])
        listener._index_cache[remote.id] = _index(wrong["lattice"])
        heard = await listener.on_signal_captured(
            n.sig_fp, n.byte_hash, n.decoded_fingerprint, None, n.norm_fp,
            n.decode_covers, capture,
        )
        cells = [
            call.args[1]["cell_key"]
            for call in hass.bus.async_fire.call_args_list
        ]
        assert cells == expected
        assert heard == (["r1"] if expected else [])


def test_the_readings_survive_a_restart():
    """Stored and read back, the index still compares: a /10 index has
    no readings and is not read (``INDEX_FORMAT``)."""
    wrong = BENCH["wrong"][0]
    built = _index(wrong["lattice"])
    payload = json.loads(json.dumps(_index_to_payload(built, "hash", None)))
    restored = _payload_to_index(payload)
    assert restored is not None
    assert restored.norm_readings == built.norm_readings
    key = _norm_key(_code(wrong["lattice"], wrong["heard"]))
    assert restored.match(None, None, None, key, None, wrong["received"]) is None


def test_a_stored_index_without_readings_is_rebuilt():
    built = _index(BENCH["wrong"][0]["lattice"])
    payload = json.loads(json.dumps(_index_to_payload(built, "hash", None)))
    del payload["norm_readings"]
    assert _payload_to_index(payload) is None


def test_the_pinned_device_compares_too():
    """A pinned device is asked "which of your cells is this frame?"
    from the identity the hearing carried, the capture included, so its
    own normalized tier does not name the neighbour either."""
    wrong = BENCH["wrong"][0]
    matrix = _matrix(wrong["lattice"])
    bench = PinnedBench(matrix, matrix, _index(wrong["lattice"]),
                        _index(wrong["lattice"]))
    key = _norm_key(_code(wrong["lattice"], wrong["heard"]))
    blind = (None, None, None, key, None, None)
    cell, _extra = bench.listener._cell_by_identity("dev-1", matrix, blind)
    assert cell is not None and cell_key(cell) == wrong["heard"]
    seen = (None, None, None, key, None, wrong["received"])
    assert bench.listener._cell_by_identity("dev-1", matrix, seen) == (None, None)


@pytest.mark.asyncio
async def test_the_capture_path_hands_the_listener_the_code():
    """Without the capture the comparison never runs, and nothing would
    say so: the capture path passes its train, on the event-bus path as
    on the native one, and it reads as the press."""
    from .test_signal_monitor import (
        _make_event,
        _make_hair_store,
        _make_hass,
        _make_signal_store,
    )

    wrong = BENCH["wrong"][0]
    hass = _make_hass()
    listener = MagicMock()
    listener.on_signal_captured = AsyncMock(return_value=[])
    monitor = SignalMonitor(hass, _make_signal_store(hass), _make_hair_store(),
                            None, listener)
    timings = fr.pronto_microseconds(wrong["received"])
    while timings and timings[-1] == 0:
        timings.pop()
    await monitor._on_ir_event(_make_event({"raw": timings}))

    args = listener.on_signal_captured.call_args[0]
    assert len(args) == 7
    assert fr.read_settings(args[6], "TCL112") == fr.read_settings(
        _code(wrong["lattice"], wrong["pressed"]))


#: The maps with normalized-tier hearings in the real-air harness. The
#: counts move with the protocol library (the harness docstring says so:
#: without it, two more MIDEA_COOLIX presses fall to that tier), so they
#: are not pinned; that every one of these maps is still examined, and
#: enough presses overall, is. Measured 2026-10-09: 6,007 with the
#: library and 6,009 without (GREE's three wrong among them on both),
#: MHI160 the smallest at 80.
HARNESS_NORMALIZED_MAPS = frozenset({
    "AUX104", "DAIKIN152", "DAIKIN216", "FUJITSU128", "GREE", "MHI152",
    "MHI160", "MHI48", "MIDEA_COOLIX", "MITSUBISHI144", "OEM112",
    "PANASONIC216", "TCL112",
})
HARNESS_NORMALIZED_FLOOR = 5_000


def test_every_normalized_hearing_of_the_harness_survives():
    """The comparison costs the harness nothing: every press and piece
    the normalized tier answered before is answered the same with the
    capture given, on every map and both transmitters. Checked press by
    press, so it holds on either leg; the floor and the map set are only
    there so it cannot hold by examining nothing."""
    from . import test_real_air_harness as h
    from .merged_group_shapes import press_identity

    examined: dict[str, int] = {}
    for pid in h._packs():
        matrix, index = h._matrix(pid), h._index(pid)
        gap = h._maps()[pid].timing.gap_min
        for cell in matrix.cells:
            for tx, presses in h.PRESSES.items():
                for press in presses:
                    heard, _glitched = h._press(cell.pronto, press, tx)
                    for _shape, variant in h._variants(cell.pronto, heard, gap):
                        identity = press_identity(variant)
                        if identity is None:
                            continue
                        before = index.match(*identity[:5])
                        if before is None or before[1] != TIER_NORM_FP:
                            continue
                        assert index.match(*identity) == before, (pid, tx)
                        examined[pid] = examined.get(pid, 0) + 1
    assert set(examined) == HARNESS_NORMALIZED_MAPS
    assert sum(examined.values()) >= HARNESS_NORMALIZED_FLOOR


def _pinned_pair(wrong: dict):
    """A remote that hears ``wrong``'s capture on its byte-hash tier, as
    a state the pinned device's lattice does not hold, so the device is
    asked by identity, where its normalized tier names the neighbour."""
    from custom_components.hair.models import TriggerRemote
    from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

    device = _matrix(wrong["lattice"])
    canonical = wig_signal_identity(wrong["received"])
    remote_matrix = ClimateMatrix(
        min_temp=61, max_temp=99, off=device.off, unit="F",
        cells=[ClimateCell(mode="heat_cool", fan="level9", temp=99.0,
                           pronto=wrong["received"])],
    )
    bench = PinnedBench(remote_matrix, device, None, _index(wrong["lattice"]))
    remote = TriggerRemote(id="r1", name="TCL", climate_matrix=True,
                           pinned_device_ids=["dev-1"])
    bench.listener._store.get_all_trigger_remotes.return_value = [remote]
    bench.listener._index_cache[remote.id] = bench.remote_index
    bench.listener._trigger_manager.resolve_receiver_area.return_value = (
        None, None)
    tasks: list = []
    bench.listener._hass.async_create_task = MagicMock(side_effect=tasks.append)
    key = _norm_key(_code(wrong["lattice"], wrong["heard"]))
    heard = (canonical.fingerprint, canonical.byte_hash,
             canonical.decoded_fingerprint, None, key,
             canonical.decode_covers)
    return bench, tasks, heard


async def _drain(tasks: list) -> None:
    """Run what the listener scheduled, including what that schedules."""
    import inspect

    while tasks:
        batch, tasks[:] = list(tasks), []
        for task in batch:
            if inspect.isawaitable(task):
                await task


@pytest.mark.asyncio
@pytest.mark.parametrize("given", [True, False], ids=["capture", "none"])
async def test_a_pinned_device_asked_by_identity_is_not_sent_the_neighbour(
    given,
):
    """End to end, from ``on_signal_captured``: the remote hears the
    press on its byte-hash tier as a state the device lacks, so the
    device is asked which of its cells the frame is, and its normalized
    tier would say the neighbour. With the capture carried through the
    hearing, nothing is dispatched; without it (the ``none`` case, and
    what dropping it anywhere on the way does) the neighbour is."""
    wrong = BENCH["wrong"][0]
    bench, tasks, heard = _pinned_pair(wrong)
    capture = _capture_path(wrong["received"]).raw_timings if given else None
    assert await bench.listener.on_signal_captured(*heard, capture) == ["r1"]
    await _drain(tasks)
    tm = bench.listener._trigger_manager
    if given:
        tm.dispatch_cell_retransmit.assert_not_called()
    else:
        tm.dispatch_cell_retransmit.assert_called_once()
        assert tm.dispatch_cell_retransmit.call_args.args[2] == (
            "heat_cool/level9/99")
        hit, identity = bench.listener._heard_frames["heat_cool/level9/99"]
        resolved = await bench.listener._async_resolve_device_cell(
            "dev-1", hit, identity)
        assert resolved is not None and resolved[3]["temp"] == 72.0


@pytest.mark.asyncio
async def test_the_kept_capture_is_packed_and_resolves_as_the_list_did():
    """What the send resolves from later is the packed train: an int
    array, a tenth of the list, and the same answer from the device."""
    from array import array

    wrong = BENCH["wrong"][0]
    bench, tasks, heard = _pinned_pair(wrong)
    train = _capture_path(wrong["received"]).raw_timings
    await bench.listener.on_signal_captured(*heard, train)
    await _drain(tasks)
    hit, identity = bench.listener._heard_frames["heat_cool/level9/99"]
    assert isinstance(identity[5], array)
    assert list(identity[5]) == list(train)
    assert identity[5].itemsize * len(identity[5]) < 2_500
    listed = (*identity[:5], list(train))
    blind = (*identity[:5], None)
    resolve = bench.listener._async_resolve_device_cell
    assert await resolve("dev-1", hit, identity) is None
    assert await resolve("dev-1", hit, listed) is None
    assert await resolve("dev-1", hit, blind) is not None


def test_the_heard_frames_are_never_stored():
    """The packed train is memory only: nothing that writes JSON or the
    store reads ``_heard_frames``."""
    from custom_components.hair import matrix_listener as ml

    source = ml.__file__
    with open(source, encoding="utf-8") as f:
        lines = [line for line in f if "_heard_frames" in line]
    assert len(lines) == 3, lines
    assert any("self._heard_frames: dict" in line for line in lines)
    assert any("self._heard_frames[hit.cell_key] =" in line for line in lines)
    assert any("self._heard_frames.get(" in line for line in lines)


def test_a_key_with_one_unread_claimant_stores_no_reading(monkeypatch):
    """All or nothing: one claimant the map cannot read leaves the key
    with nothing to compare, rather than comparing against the rest."""
    from custom_components.hair import field_readers
    from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

    wrong = BENCH["wrong"][0]
    code = _code(wrong["lattice"], wrong["heard"])
    device = _matrix(wrong["lattice"])
    matrix = ClimateMatrix(
        min_temp=61, max_temp=88, off=device.off, unit="F",
        cells=[
            ClimateCell(mode="heat_cool", fan="level1", temp=72.0, pronto=code),
            ClimateCell(mode="heat_cool", fan="level1", temp=73.0, pronto=code),
        ],
    )
    key = _norm_key(code)
    assert key in build_cell_index(matrix).norm_readings

    real = field_readers.read_settings
    calls = {"n": 0}

    def second_unread(pronto, family=None, prefer=None):
        got = real(pronto, family, prefer)
        if family is None and got is not None and got[0] == "TCL112":
            calls["n"] += 1
            if calls["n"] == 2:
                return None
        return got

    monkeypatch.setattr(field_readers, "read_settings", second_unread)
    index = build_cell_index(matrix)
    assert calls["n"] >= 2
    assert key not in index.norm_readings


def test_the_reader_version_rebuilds_the_index_once_and_nothing_else(
    tmp_path, monkeypatch,
):
    """A change in what the reader returns moves no YAML byte, so the
    reader carries a version the index digest folds in. Moving it makes
    every stored index rebuild once, to the same index, and moves no
    other identity: the digest is read by the cell index alone."""
    import pathlib
    import re

    from custom_components.hair import field_readers, identity
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import (
        load_cell_index,
        write_matrix,
    )

    package = pathlib.Path(identity.__file__).parent
    call = re.compile(r"(?<!def )field_map_digest\(\)")
    readers = sorted(
        path.name for path in package.glob("*.py")
        if call.search(path.read_text(encoding="utf-8"))
    )
    assert readers == ["matrix_listener.py"]

    matrix = _pack_matrix("TCL112.json")
    write_matrix(tmp_path, "r1", matrix)
    _build_and_store_index(str(tmp_path), "r1", matrix, "F")
    before = load_cell_index(tmp_path, "r1")
    assert _load_stored_index(str(tmp_path), "r1", "F") is not None
    code = matrix.cells[0].pronto
    hashes = (EventParser.pronto_byte_hash(code),
              EventParser.signal_fingerprint("PRONTO", code, None))

    monkeypatch.setattr(field_readers, "READER_VERSION",
                        field_readers.READER_VERSION + 1)
    assert _load_stored_index(str(tmp_path), "r1", "F") is None
    _build_and_store_index(str(tmp_path), "r1", matrix, "F")
    after = load_cell_index(tmp_path, "r1")
    assert _load_stored_index(str(tmp_path), "r1", "F") is not None
    assert after["maps"] != before["maps"]
    assert {k: v for k, v in after.items() if k != "maps"} == {
        k: v for k, v in before.items() if k != "maps"}
    assert (EventParser.pronto_byte_hash(code),
            EventParser.signal_fingerprint("PRONTO", code, None)) == hashes
