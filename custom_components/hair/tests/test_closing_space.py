"""Captures a receiver closed with its own idle time, from real air.

A receiver ends every capture with its idle time as the final space, so
the space after a code's last mark says how the code was handed over,
not what it carries. ESPHome's default idle is 10 ms, which sits between
DAIKIN152's frame gap (2 ms) and DAIKIN216's (11 ms). Walked as data
under DAIKIN216's timing, that space is one more bit pair outside every
window, and the shared Daikin settings key needs both Daikin timings to
walk the frame. So until identity dropped the closing space
(``identity._stripped``), a lone Daikin settings frame from such a
receiver formed no read key and was heard only on the receiver-tolerant
tier, while the same frame stored from a file keyed, because every
stored identity already went through ``canonical_byte_hash``.

The captures are from the fake-remote air bench of 2026-10-05
(``fixtures/air-path/closing-space.json``): pack file codes played
through a Broadlink by legacy ``remote.send_command`` into an Athom
receiver at ESPHome's default idle. There, 0 of 2,300 lone Daikin
settings frames formed a read key. The same bench's three GREE
wrong hearings are pinned here too, as known and not fixed.
"""
from __future__ import annotations

import json
import types

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair.event_parser import EventParser
from custom_components.hair.matrix_listener import build_cell_index, tier_name
from custom_components.hair.signal_monitor import normalize
from custom_components.hair.wig_format import cell_key

from .merged_group_shapes import FIXTURES, press_identity
from .test_cell_index_shared_keys import _pack_matrix

BENCH = json.loads(
    (FIXTURES / "air-path" / "closing-space.json").read_text(encoding="utf-8")
)
MAPS = {m.protocol_id: m for m in fr.library()}


def _capture_path(pronto: str):
    """What the box computes for a capture: the receiver's timings,
    closing space included, through the native receiver path. Not
    through ``ProntoCommand``, whose constructor drops the closing space
    (the stored path), which is the very difference under test."""
    timings = fr.pronto_microseconds(pronto)
    while timings and timings[-1] == 0:
        timings.pop()
    signal = types.SimpleNamespace(timings=timings, modulation=38000)
    return normalize(EventParser.parse_received_signal(signal))


def _heard(index, pronto: str):
    n = _capture_path(pronto)
    hit = index.match(n.decoded_fingerprint, n.sig_fp, n.byte_hash, n.norm_fp,
                      n.decode_covers)
    return None if hit is None else (hit[0].cell_key, tier_name(hit[1]))


def _file_code(frame: dict) -> str:
    cells = _pack_matrix(f"{frame['family']}.json").cells
    return next(c.pronto for c in cells if cell_key(c) == frame["pack_cell"])


def _with_closing(pronto: str, closing_us: int) -> str:
    words = pronto.split()
    tick = int(words[1], 16) * fr._PRONTO_TICK_US
    words[-1] = f"{round(closing_us / tick):04X}"
    return " ".join(words)


def test_the_bench_captures_are_here():
    assert [f["family"] for f in BENCH["lone_frames"]] == ["DAIKIN216", "DAIKIN152"]
    assert len(BENCH["gree_wrong"]) == 3


@pytest.mark.parametrize("frame", BENCH["lone_frames"], ids=lambda f: f["family"])
class TestALoneDaikinSettingsFrameClosedAtTenMilliseconds:

    def test_it_closes_between_the_two_daikin_gaps(self, frame):
        words = frame["received"].split()
        closing = int(words[-1], 16) * int(words[1], 16) * fr._PRONTO_TICK_US
        assert MAPS["DAIKIN152"].timing.gap_min <= closing
        assert closing < MAPS["DAIKIN216"].timing.gap_min

    def test_daikin216s_timing_walks_that_space_as_one_more_pair(self, frame):
        """Why it never keyed: handed the train as received, DAIKIN216's
        walk refuses at the closing pair, and the shared key needs that
        walk to read the frame."""
        train = fr.pronto_microseconds(frame["received"])
        why = fr.walk_refusal(MAPS["DAIKIN216"].timing, train)
        assert why is not None and why.window == "carrier"
        assert why.pair == len(train) // 2 - 1

    def test_it_keys_as_its_file_code(self, frame):
        key = EventParser.pronto_read_key(_file_code(frame))
        assert key is not None
        assert EventParser.pronto_read_key(frame["received"]) == key

    def test_the_box_hashes_it_to_that_key(self, frame):
        """``byte_hash`` carries the read key for a listed family, so the
        capture path and every stored identity now agree on it."""
        key = EventParser.pronto_read_key(_file_code(frame))
        assert _capture_path(frame["received"]).byte_hash == key
        assert press_identity(frame["received"])[2] == key

    def test_any_closing_space_keys_the_same(self, frame):
        key = EventParser.pronto_read_key(_file_code(frame))
        for closing in (0, 1_000, 5_000, 9_992, 10_999, 11_000, 20_000, 80_000):
            assert EventParser.pronto_read_key(
                _with_closing(frame["received"], closing)) == key, closing

    def test_its_own_lattice_hears_it_by_its_settings(self, frame):
        """Heard as its cell on the read key (the byte-hash tier, where
        the key rides) rather than on the receiver-tolerant tier."""
        index = build_cell_index(_pack_matrix(f"{frame['family']}.json"))
        assert _heard(index, frame["received"]) == (frame["pack_cell"], "byte hash")


def test_the_three_gree_glitch_presses_are_still_heard_as_the_neighbouring_fan():
    """KNOWN WRONG, PINNED, NOT FIXED. The real-air harness's three
    glitched GREE blaster presses, sent through the Broadlink on the air
    bench, are heard by a real receiver exactly as the model predicts:
    as the next fan speed up, on the receiver-tolerant tier (15 of 15
    sends; the GitHub issue draft on the GREE wrong hearing carries them).
    The GREE round changes this count on purpose, from 3."""
    index = build_cell_index(_pack_matrix("GREE.json"))
    heard = {
        (w["pressed"], _heard(index, w["received"])) for w in BENCH["gree_wrong"]
    }
    assert heard == {
        ("cool/low/24", ("cool/high/24", "normalized")),
        ("cool/mid/16", ("cool/high/16", "normalized")),
        ("heat/low/27", ("heat/high/27", "normalized")),
    }
