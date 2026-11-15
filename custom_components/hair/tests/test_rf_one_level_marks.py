"""A pulse-distance body: one mark width over two space widths (ruling
2026-11-14).

Nexa self-learning and KlikAanKlikUit send every mark one width and
carry the code in the spaces (1 T or 5 T). Without this, ``has_body``
wants two mark widths and drops such a press as noise. The rule: one mark
level, the spaces' two most populated levels 3 to 7 apart holding at
least 90 percent of the spaces, and at least 40 pairs.

Held to: a synthetic press votes; the same shape below 40 pairs is still
noise; both recorded noise hours are counted, filed and printed to the
Candy Drawer exactly as before; and every real bench fixture votes the
same frame as before.
"""
from __future__ import annotations

import gzip
import json
import random
from collections import Counter
from pathlib import Path

import pytest

from custom_components.hair import rf_frames
from custom_components.hair.tests.test_rf_always_on import (
    RID,
    _monitor,
    _replay,
)

FIXTURES = Path(__file__).parent / "fixtures" / "rf"
NOISE_HOURS = (
    "athom-433-150us-6ms-noise-1h.json.gz",
    "athom-433-150us-6ms-fs20-noise-1h.json.gz",
)


def _word(*, t: int = 260, bits: int = 32, long_t: float = 5.0, seed: int = 0) -> list[int]:
    """A self-learning word: a start pair, then each logical bit as two
    wire bits (short then long is 0, long then short is 1), then the
    stop mark and its low as the gap."""
    rng = random.Random(seed)
    out = [t, -10 * t]
    short, long = (t, -t), (t, -round(long_t * t))
    for _ in range(bits):
        bit = rng.randint(0, 1)
        for mark, space in ((long, short) if bit else (short, long)):
            out += [mark, space]
    out += [t, -40 * t]
    return out


def _widened(word: list[int], by: int) -> list[int]:
    """A receiver reading every mark and space ``by`` wider (negative
    ``by`` for narrower), the gap kept."""
    return [v + by if v > 0 else (v - by if v > -5000 else v) for v in word]


def _parts(timings: list[int]) -> rf_frames.FrameParts:
    pieces = rf_frames.split_frames(timings)
    return rf_frames.split_body(pieces[0])


def _today(monkeypatch) -> None:
    monkeypatch.setattr(rf_frames, "has_body", rf_frames._has_two_level_body)


class TestAPressVotes:
    @pytest.mark.parametrize("widen", [0, 60, -60])
    def test_a_self_learning_press_votes(self, widen):
        word = _widened(_word(), widen)
        capture = rf_frames.analyze(word * 4)
        assert capture is not None
        assert capture.votes >= 2

    def test_it_was_noise_before(self, monkeypatch):
        _today(monkeypatch)
        assert rf_frames.analyze(_word() * 4) is None

    @pytest.mark.parametrize("long_t", [4.2, 5.0, 6.5])
    def test_long_spaces_from_4_to_7_t(self, long_t):
        assert rf_frames.analyze(_word(long_t=long_t) * 4) is not None

    @pytest.mark.parametrize("long_t", [3.0, 3.4])
    def test_a_3_to_3_4_t_remote_is_still_noise(self, long_t):
        """RFLink-ESP says 3 T and 3.4 T long spaces also work. Below
        about 3.2 T the 10 T start space takes the fingerprint's
        short/long cut and a remote's buttons share one fingerprint, so
        such a remote stays dropped, as it was before (ruling
        2026-11-15). A real capture of one decides an identity change."""
        assert rf_frames.analyze(_word(long_t=long_t) * 4) is None

    def test_every_button_keeps_its_own_fingerprint(self):
        """The reason for the floor: across the band that is let in, 40
        buttons give 40 fingerprints."""
        for long_t in (4.0, 5.0, 7.0):
            prints = {
                rf_frames.analyze(_word(long_t=long_t, seed=seed) * 4).fingerprint
                for seed in range(40)
            }
            assert len(prints) == 40, long_t

    def test_a_dim_word(self):
        """36 logical bits: 72 wire bits."""
        assert rf_frames.analyze(_word(bits=36) * 4) is not None

    def test_two_presses_of_one_button_are_one_identity(self):
        one = rf_frames.analyze(_word(seed=3) * 4)
        two = rf_frames.analyze(_widened(_word(seed=3), 40) * 4)
        assert one.frame_hash == two.frame_hash

    def test_two_buttons_are_two_identities(self):
        one = rf_frames.analyze(_word(seed=3) * 4)
        two = rf_frames.analyze(_word(seed=4) * 4)
        assert one.frame_hash != two.frame_hash


def _wire(n: int, *, t: int = 260, long_t: float = 5.0, seed: int = 0) -> list[int]:
    """``n`` wire bits with no start pair (a receiver that lost it), a
    short and a long space in turn, then the stop mark and the gap: ``n``
    mark-space pairs in the body."""
    rng = random.Random(seed)
    out: list[int] = []
    for index in range(n):
        long = (index % 2 == 0) ^ bool(rng.randint(0, 1) and index % 4 == 0)
        out += [t, -(round(long_t * t) if long else t)]
    return [*out, t, -40 * t]


class TestBelowTheFloor:
    def test_39_pairs_has_no_body(self):
        parts = _parts(_wire(39))
        assert len(rf_frames._polarities(parts)[1]) == 39
        assert not rf_frames.has_body(parts)

    def test_40_pairs_has_a_body(self):
        parts = _parts(_wire(40))
        marks, spaces = rf_frames._polarities(parts)
        assert len(spaces) == 40 and len(marks) == 41
        assert rf_frames.has_body(parts)

    @pytest.mark.asyncio
    async def test_a_short_scrap_is_still_counted_as_noise(self, fake_hass):
        """The counters keep their meaning for short scraps."""
        import types

        from .test_rf_always_on import FakeLoop

        loop = FakeLoop()
        monitor, _store = _monitor(fake_hass, loop)
        monitor.rf_always_on.attach(RID)
        signal = types.SimpleNamespace(
            timings=_wire(39), frequency=433_920_000, modulation="ook",
        )
        monitor._on_rf_signal(signal, RID)
        counters = monitor.rf_always_on.counters(RID)
        assert counters["captures"] == 1
        assert counters["noise"] == 1


class TestRefusals:
    """Built from wire bits with no start space, so the frame cut (three
    times the p90 space) never lands inside the word."""

    @pytest.mark.parametrize("long_t", [2.0, 3.0, 3.8])
    def test_spaces_under_4_apart(self, long_t):
        parts = _parts(_wire(64, long_t=long_t))
        assert len(rf_frames._polarities(parts)[1]) == 64
        assert not rf_frames.has_body(parts)

    @pytest.mark.parametrize("long_t", [7.5, 9.0])
    def test_spaces_over_7_apart(self, long_t):
        parts = _parts(_wire(64, long_t=long_t))
        assert len(rf_frames._polarities(parts)[1]) == 64
        assert not rf_frames.has_body(parts)

    @pytest.mark.parametrize("long_t", [4.2, 6.8])
    def test_spaces_inside_4_to_7_apart(self, long_t):
        assert rf_frames.has_body(_parts(_wire(64, long_t=long_t)))

    def test_the_top_two_space_levels_under_90_percent(self):
        word = _word()
        rng = random.Random(1)
        # Turn about a fifth of the spaces into a third width (2.5 T).
        for index in range(3, len(word) - 2, 2):
            if rng.random() < 0.2:
                word[index] = -650
        assert not rf_frames.has_body(_parts(word))

    def test_a_run_of_one_width(self):
        assert not rf_frames.has_body(_parts([260, -260] * 60 + [260, -10400]))


def _bench_captures() -> list[tuple[str, int, list[int]]]:
    """Every capture of every real bench fixture, by name."""
    out: list[tuple[str, int, list[int]]] = []
    keyfob = json.loads((FIXTURES / "it104-keyfob-433.json").read_text())
    for index, capture in enumerate(keyfob["captures"]):
        pulses = capture["pulses"]
        out.append(("it104-keyfob-433.json", index,
                    [v if i % 2 == 0 else -v for i, v in enumerate(pulses)]))
    for path in sorted((FIXTURES / "athom").glob("*presses.json.gz")):
        data = json.loads(gzip.decompress(path.read_bytes()))
        for index, capture in enumerate(data["captures"]):
            if isinstance(capture, dict):
                pulses = capture["pulses"]
                timings = [v if i % 2 == 0 else -v for i, v in enumerate(pulses)]
            else:
                timings = list(capture[1])
            out.append((path.name, index, timings))
    return out


def _read(timings: list[int]) -> tuple:
    """What the vote makes of a capture, and the pieces the burst
    assembler and the noise count are handed."""
    capture = rf_frames.analyze(timings)
    bodied = tuple(
        rf_frames.frame_fingerprint(parts)
        for _, parts in rf_frames.bodied_pieces(rf_frames.split_frames(timings))
    )
    if capture is None:
        return None, bodied
    return (
        (tuple(capture.frame), capture.fingerprint, capture.frame_hash, capture.votes),
        bodied,
    )


class TestTheBenchIsUnchanged:
    def test_the_fixtures_are_all_here(self):
        names = {name for name, _, _ in _bench_captures()}
        assert {
            "it104-keyfob-433.json",
            "rm4pro-433-it104-joint-presses.json.gz",
            "athom-433-it104-150us-6ms-fs20-joint-presses.json.gz",
            "athom-433-it104-150us-6ms-presses.json.gz",
        } <= names

    def test_every_capture_votes_the_same_frame(self, monkeypatch):
        captures = _bench_captures()
        new = [_read(timings) for _, _, timings in captures]
        _today(monkeypatch)
        old = [_read(timings) for _, _, timings in captures]
        changed = [
            (name, index) for (name, index, _), a, b in zip(captures, old, new, strict=True)
            if a != b
        ]
        assert changed == []
        assert sum(r[0] is not None for r in new) >= 50
        assert sum(len(r[1]) for r in new) > 1000


class TestTheNoiseHours:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", NOISE_HOURS)
    @pytest.mark.parametrize("window", [None, "open"])
    async def test_counters_and_rows_are_unchanged(self, fake_hass, monkeypatch, name, window):
        def counted(monitor, store):
            counters = dict(monitor.rf_always_on.counters(RID))
            counters.pop("since")  # the replay's own start time
            return counters, len(store.get_all_devices())

        new = counted(*(await _replay(fake_hass, name, window=window))[:2])
        _today(monkeypatch)
        old = counted(*(await _replay(fake_hass, name, window=window))[:2])
        assert new == old
        assert new[0]["captures"] > 10_000

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", NOISE_HOURS)
    async def test_the_candy_drawers_static_reasons_are_unchanged(
        self, fake_hass, monkeypatch, name
    ):
        from .test_rf_always_on import FakeLoop

        async def reasons() -> Counter:
            loop = FakeLoop()
            monitor, store = _monitor(fake_hass, loop)
            monitor.rf_always_on.attach(RID)
            events: list[dict] = []
            monitor.candy_subscribe(events.append, static=True)
            await _replay(fake_hass, name, monitor=(monitor, store, loop))
            return Counter(
                event["reason"] for event in events if event.get("reason")
            )

        new = await reasons()
        _today(monkeypatch)
        old = await reasons()
        assert new == old
        assert old["no_body"] > 100
