"""The identity round: one state held as several captures, and a lone
frame of a listed family.

Two things kept a clean family from joining read-bytes identity. The
cell index merged two claimants of a key only when they were one state
or one quantized waveform, so a lattice built from one capture per cell
(SmartIR 1128: dry stored once per temperature, each cell its own
capture, the captures identical on every bit the map reads) refused its
own read keys. And ``read_bytes_hash`` formed a key from a lone frame
only through the Daikin shared-frame path, so a press a receiver splits
at its gap found its state only for a Daikin.

The first is fixed here for every listed family: two claimants with the
same decoded bytes in the same mode of the same lattice merge, a key
remembers which claimant each waveform is, and the merged groups follow
the merge. The second was built and pinned under a patched list, since
no family on the lists of the time reached it; MITSUBISHI144 has since
joined both lists, so those pins run on the real lists, and the ones
that say what an unlisted family sees run with it taken off again
(``_unlisted``).

Every listed shape here is DAIKIN216 from ``test_read_bytes_identity``'s
encoder, with one extra (unit, zero) pulse pair that reads one bit over
inside the map's tolerance, so the bytes and the read key stay the same
and the waveform does not (``merged_group_shapes.extra_pair_code``).
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import hashlib
import itertools
import json
from pathlib import Path
from typing import ClassVar

import pytest

import custom_components.hair.identity as idm
from custom_components.hair import field_readers as fr
from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import (
    TIER_BYTE_HASH,
    TIER_NORM_FP,
    NormFpIndex,
    norm_fingerprint,
    whole_code_discriminator,
)
from custom_components.hair.matrix_listener import (
    _coords,
    _index_to_payload,
    _payload_to_index,
    build_cell_index,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateExtra,
    ClimateMatrix,
    cell_key,
)
from custom_components.hair.wig_identity import wig_signal_identity

from . import merged_group_shapes as shapes
from . import test_read_bytes_identity as d216
from .test_cell_index_shared_keys import _match, _pack_matrix

MAPS = {m.protocol_id: m for m in fr.library()}
FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _listed(*families: str):
    """Both identity lists with ``families`` added, as a family joining
    them would be. ``norm_fingerprint_of_code`` is cached on code text
    and reads the setting-frame list, so its cache is cleared on the
    way in and on the way out."""
    saved = (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED)
    idm.norm_fingerprint_of_code.cache_clear()
    try:
        idm.READ_BYTES_VERIFIED = frozenset(saved[0] | set(families))
        idm.SETTING_IDENTITY_VERIFIED = frozenset(saved[1] | set(families))
        idm.norm_fingerprint_of_code.cache_clear()
        yield
    finally:
        idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED = saved
        idm.norm_fingerprint_of_code.cache_clear()


@contextlib.contextmanager
def _unlisted(*families: str):
    """Both identity lists with ``families`` taken off, as they were
    before those families joined: the inverse of ``_listed``, clearing
    the same cache the same way."""
    saved = (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED)
    idm.norm_fingerprint_of_code.cache_clear()
    try:
        idm.READ_BYTES_VERIFIED = frozenset(saved[0] - set(families))
        idm.SETTING_IDENTITY_VERIFIED = frozenset(saved[1] - set(families))
        idm.norm_fingerprint_of_code.cache_clear()
        yield
    finally:
        idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED = saved
        idm.norm_fingerprint_of_code.cache_clear()


#: The lists as they ship. A test that patches them must put them back.
_SHIPPED = (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED)


@pytest.fixture(autouse=True)
def _the_lists_are_the_shipped_ones():
    """Nothing leaks between tests: every test here starts and ends on
    the lists as they ship, whatever it patched in between."""
    assert (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED) == _SHIPPED
    yield
    assert (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED) == _SHIPPED


def test_mitsubishi144_is_on_the_shipped_lists():
    """So every pin below that names it runs on the real lists."""
    assert "MITSUBISHI144" in idm.READ_BYTES_VERIFIED
    assert "MITSUBISHI144" in idm.SETTING_IDENTITY_VERIFIED


def _lattice(cells, extras=None) -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0,
        modes=sorted({c.mode for c in cells}),
        fan_modes=sorted({c.fan for c in cells}), swing_modes=[],
        off=None, cells=list(cells), extras=extras,
    )


def _us(pronto: str) -> list[int]:
    return EventParser._pronto_us(EventParser._parse_pronto_words(pronto))


def _identity(pronto: str):
    return shapes.press_identity(pronto)


_COOL = d216._settings()                       # cool / low / 18
_PLAIN = d216._code(_COOL)
_EXTRA = shapes.extra_pair_code(_COOL, "settings")
_EXTRA_0 = shapes.extra_pair_code(_COOL, "preamble")
_HANDSET = d216._code(d216._settings(byte15=0xC5))  # cool / 18, unread byte


def _read_key(pronto: str) -> str:
    key = EventParser.pronto_read_key(pronto)
    assert key is not None
    return key


# ---------------------------------------------------------------------------
# 1. The merge
# ---------------------------------------------------------------------------


class TestTheMerge:

    def test_the_extra_pair_keeps_the_bytes_and_moves_the_waveform(self):
        """What every shape below is built on."""
        for extra in (_EXTRA, _EXTRA_0):
            assert idm.read_bytes_form(_us(extra)) == idm.read_bytes_form(
                _us(_PLAIN)
            )
            plain, other = (wig_signal_identity(p) for p in (_PLAIN, extra))
            assert whole_code_discriminator(
                plain.raw_timings, plain.byte_hash
            ) != whole_code_discriminator(other.raw_timings, other.byte_hash)
        # In the preamble only the whole code sees it; in the settings
        # frame the normalized fingerprint does too.
        assert _identity(_EXTRA_0)[1:4] == _identity(_PLAIN)[1:4]
        assert _identity(_EXTRA)[3] != _identity(_PLAIN)[3]

    def test_one_state_in_two_waveforms_answers_at_the_read_key(self):
        """Shape F0: refused on every tier before this round, so the
        file refused its own dry state; every dry cell is heard now."""
        matrix = shapes.shape_extra_pair_preamble()
        index = build_cell_index(matrix)
        dry = [c for c in matrix.cells if c.mode == "dry"]
        assert _read_key(dry[0].pronto) in index.bytehash
        for cell in dry:
            heard = _match(index, cell.pronto)
            assert heard is not None, cell_key(cell)
            assert heard[0].startswith("dry/low/") and heard[2] == (
                TIER_BYTE_HASH
            )
            for press in range(3):
                air, _ = d216._air(cell.pronto, press, "esphome")
                assert _match(index, air)[0].startswith("dry/low/")
        for cell in matrix.cells:
            if cell.mode == "cool":
                assert _match(index, cell.pronto)[0] == cell_key(cell)

    @pytest.mark.parametrize("order", [0, 1])
    def test_the_same_bytes_in_another_mode_is_refused(self, order):
        """The owner's ruling that one code merges across modes is about
        identical waveforms; bytes alone do not carry it."""
        cells = [
            ClimateCell(mode="cool", fan="low", temp=18.0, pronto=_PLAIN),
            ClimateCell(mode="dry", fan="low", temp=18.0, pronto=_EXTRA),
        ]
        index = build_cell_index(_lattice(cells[::-1] if order else cells))
        assert _read_key(_PLAIN) not in index.bytehash
        assert _match(index, _HANDSET) is None

    @pytest.mark.parametrize("order", [0, 1])
    def test_the_same_bytes_in_another_lattice_is_refused(self, order):
        """A preset carrying a main cell's bytes in another waveform: a
        merge would hear every main press of that state as the preset."""
        main = [ClimateCell(mode="cool", fan="low", temp=18.0, pronto=_PLAIN)]
        eco = [ClimateCell(mode="cool", fan="low", temp=18.0, pronto=_EXTRA)]
        if order:
            main, eco = (
                [ClimateCell(mode="cool", fan="low", temp=18.0,
                             pronto=_EXTRA)],
                [ClimateCell(mode="cool", fan="low", temp=18.0,
                             pronto=_PLAIN)],
            )
        index = build_cell_index(_lattice(
            main, extras=[ClimateExtra(axis="preset", key="eco", cells=eco)],
        ))
        assert _read_key(_PLAIN) not in index.bytehash
        assert _match(index, _HANDSET) is None

    @pytest.mark.parametrize("order", [0, 1])
    def test_codes_that_differ_in_one_unread_bit_stay_refused(self, order):
        cells = [
            ClimateCell(mode="cool", fan="low", temp=18.0, pronto=_PLAIN),
            ClimateCell(mode="cool", fan="low", temp=19.0,
                        pronto=d216._code(d216._settings(byte11=0x06))),
        ]
        index = build_cell_index(_lattice(cells[::-1] if order else cells))
        assert _read_key(_PLAIN) not in index.bytehash
        assert _match(index, _HANDSET) is None

    @pytest.mark.parametrize("case", ["bytes then code", "state then code"])
    def test_three_claimants_not_all_one_thing_are_refused_in_every_order(
        self, case,
    ):
        """A is one thing with B and B with C, and A is not C. Checked
        against the last claimant alone the answer depended on the order
        of the file and could name a state nobody pressed; checked
        against every claimant it is refused in all six orders.

        "bytes then code": A cool/18, B cool/19 with A's bytes in another
        waveform, C heat/19 carrying B's exact code (a label error).
        "state then code": A cool/18, B cool/18 again with an unread
        byte changed, C cool/19 carrying B's exact code."""
        if case == "bytes then code":
            spec = [("cool", 18.0, _PLAIN), ("cool", 19.0, _EXTRA),
                    ("heat", 19.0, _EXTRA)]
        else:
            other = d216._code(d216._settings(byte11=0x06))
            spec = [("cool", 18.0, _PLAIN), ("cool", 18.0, other),
                    ("cool", 19.0, other)]
        for order in itertools.permutations(spec):
            index = build_cell_index(_lattice([
                ClimateCell(mode=m, fan="low", temp=t, pronto=p)
                for m, t, p in order
            ]))
            assert _read_key(_PLAIN) not in index.bytehash, order
            assert _match(index, _HANDSET) is None, order

    def test_the_normalized_tier_keeps_every_claimant_too(self):
        """The same three claimants built so all three share one
        normalized fingerprint (the extra pair in the preamble): the
        cell index's own normalized bookkeeping refuses it in every
        order, and records it as ambiguous."""
        spec = [("cool", 18.0, _PLAIN), ("cool", 19.0, _EXTRA_0),
                ("heat", 19.0, _EXTRA_0)]
        waveform = _identity(_PLAIN)[3]
        assert {_identity(p)[3] for _m, _t, p in spec} == {waveform}
        for order in itertools.permutations(spec):
            index = build_cell_index(_lattice([
                ClimateCell(mode=m, fan="low", temp=t, pronto=p)
                for m, t, p in order
            ]))
            assert index.norm_fp.get(waveform) is None, order
            assert waveform in index.norm_fp.ambiguous

    def test_normfpindex_itself_is_unchanged(self):
        """Its other users claim with plain strings, for which the last
        claimant and every claimant give one verdict: a second code
        poisons, permanently, in any order."""
        for order in itertools.permutations(["h1", "h1", "h2"]):
            index = NormFpIndex()
            for n, code in enumerate(order):
                index.add("aaaa", code, f"ref-{n}")
            assert index.get("aaaa") is None
            assert "aaaa" in index.ambiguous
        index = NormFpIndex()
        index.add("aaaa", "h1", "first")
        index.add("aaaa", "h1", "second")
        assert index.get("aaaa") == "second"

    def test_two_file_commands_sharing_one_code_stay_known_and_pinned(self):
        """``storage`` and ``pin_bindings`` keep ``NormFpIndex`` as it
        was: two file-sourced commands carrying one code both index,
        the later one answering, in the known-command index and in a
        pin map alike."""
        from unittest.mock import MagicMock

        from custom_components.hair.const import CommandCategory, CommandSource
        from custom_components.hair.models import CaptureResult, IRDevice
        from custom_components.hair.pin_bindings import build_device_index
        from custom_components.hair.storage import HAIRStore

        code = _pack_matrix("MITSUBISHI144.json").cells[0].pronto
        identity = wig_signal_identity(code)
        device = IRDevice(name="Adopted", source_wig_id="wig-1")
        for name in ("Cool A", "Cool B"):
            command = CaptureResult(
                protocol="PRONTO", code=identity.pronto,
                raw_timings=list(identity.raw_timings),
                frequency=identity.frequency,
            ).to_command(name, CommandCategory.CUSTOM)
            command.source = CommandSource.IMPORTED
            command.byte_hash = identity.byte_hash
            device.commands.append(command)
        store = HAIRStore(MagicMock())
        store._loaded = True
        store._data[device.id] = device
        store._rebuild_command_index()
        waveform = norm_fingerprint(identity.raw_timings)
        assert store.match_command(None, None, None, waveform) == (
            device.id, device.commands[1].id,
        )
        assert build_device_index(device).norm_fp.get(waveform) == (
            device.commands[1].id
        )


# ---------------------------------------------------------------------------
# 2. Exact waveform wins inside a merged key
# ---------------------------------------------------------------------------


def _presses(pronto: str, family: str = "DAIKIN216") -> list[str]:
    """The file code, then ten capture-shaped presses per transmitter,
    whole and split at the map's gap."""
    gap = MAPS[family].timing.gap_min
    out = [pronto]
    for transmitter in ("esphome", "broadlink"):
        for press in range(10):
            heard, _ = d216._air(pronto, press, transmitter)
            out.append(heard)
            out.extend(shapes.map_split(heard, gap))
    return out


def _first_key(index, identity):
    """The tier key that answers a press of a waveform the normalized
    tier does not know: the first one the press reaches that the rule
    before the bytes half kept; else the first held-back key it reaches
    that names the press's own waveform, as that waveform's cell; else
    the first held-back key's representative. The decoded tier holds no
    listed family's code here (DAIKIN216's decode never covers,
    MITSUBISHI144 does not decode)."""
    _decoded, fingerprint, byte_hash, waveform, _covers = identity
    reached = [
        (tier, key, store.get(key))
        for tier, key, store in (
            ("fp_bytehash", (fingerprint, byte_hash), index.fp_bytehash),
            ("bytehash", byte_hash, index.bytehash),
        )
    ]
    reached = [(tier, key, hit) for tier, key, hit in reached if hit]
    for tier, key, hit in reached:
        if (tier, key) not in index.held_back:
            return hit
    for tier, key, _hit in reached:
        named = index.by_waveform.get((tier, key), {}).get(waveform)
        if named is not None:
            return named
    return reached[0][2] if reached else None


class TestExactWaveformWins:
    """A press heard before the merge is heard as the same cell after.

    Shape F1: dry / low / 18-23, the even temperatures one waveform and
    the odd ones another, one set of bytes. Before this round the read
    key was refused, and each waveform's own composite and normalized
    keys answered the last cell of that waveform: dry / low / 22 for the
    plain code and 23 for the extra pair. The read key now merges all
    six, and its representative is 23, so if it answered in its turn,
    every plain press the air moved off its composite key would be named
    23 and a pinned device sent 23's text instead of 22's. It answers
    last instead, after the normalized tier that answered before.

    The two S/L-split lattices are where answering from the merged key
    in its turn goes wrong even with the by-waveform answer: the
    composite key a press lands on holds none of its waveform's cells,
    or an earlier one than the normalized tier answers.
    """

    BEFORE: ClassVar[dict[str, str]] = {
        "plain": "dry/low/22", "extra": "dry/low/23",
    }

    @staticmethod
    def _kind(cell) -> str:
        return "plain" if int(cell.temp) % 2 == 0 else "extra"

    def _check(self, index, matrix, family="DAIKIN216", extra=(),
               goes_on=True):
        """Every press heard is heard as it was before the merge.

        A cool cell as itself. A dry press whose waveform the normalized
        tier knows, as that tier's cell for it, which is what these
        lattices answered before (their composite keys never part a
        waveform's cells; checked against the base by probe). A dry
        press of a waveform it does not know, as the first key it
        reaches answers (``_first_key``). And, unless ``goes_on`` is False
        (a lattice where every key of the state is held back), some
        presses must reach a key only the bytes half keeps and go on past
        it to the tier that answered them before: the case the held-back
        keys exist for.
        """
        went_on = 0
        presses = [(None, press) for press in extra] + [
            (cell, press) for cell in matrix.cells
            for press in _presses(cell.pronto, family)
        ]
        for cell, press in presses:
            identity = _identity(press)
            heard = identity and index.match(*identity)
            if not heard:
                continue
            hit, tier = heard
            if cell is not None and cell.mode != "dry":
                assert hit.cell_key == cell_key(cell)
                continue
            own = index.norm_fp.get(identity[3])
            if own is None:
                assert hit.cell_key == _first_key(index, identity).cell_key, (
                    press
                )
                continue
            assert hit.cell_key == own.cell_key, press
            composite = ("fp_bytehash", (identity[1], identity[2]))
            if tier == TIER_NORM_FP and (
                    composite in index.held_back
                    or ("bytehash", identity[2]) in index.held_back):
                went_on += 1
        assert went_on > 0 or not goes_on

    def test_the_map_forms_for_the_one_merged_key(self):
        index = build_cell_index(shapes.shape_extra_pair_settings())
        key = _read_key(d216._code(d216._settings(mode_power=0x21)))
        assert set(index.by_waveform) == {("bytehash", key)}
        answers = {h.cell_key for h in index.by_waveform[("bytehash", key)]
                   .values()}
        assert answers == set(self.BEFORE.values())
        assert index.bytehash[key].cell_key == "dry/low/23"

    def test_every_press_heard_before_keeps_its_cell(self):
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            if cell.mode == "dry":
                assert index.norm_fp.get(_identity(cell.pronto)[3]).cell_key == (
                    self.BEFORE[self._kind(cell)]
                )
        self._check(index, matrix)

    def test_and_after_a_restart(self):
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        restored = _payload_to_index(json.loads(json.dumps(
            _index_to_payload(index, "h", "C")
        )))
        assert restored.by_waveform.keys() == index.by_waveform.keys()
        self._check(restored, matrix)

    def test_the_same_on_a_listed_mitsubishi144(self):
        """SmartIR 1128's shape on its own family, listed: dry / auto /
        auto / 16-21, the pack's code on the even temperatures and the
        extra pair on the odd ones. A lone second frame is the same
        waveform in both, and is heard as the plain cell, as before."""
        matrix = shapes.shape_mitsubishi144_capture_per_cell()
        index = build_cell_index(matrix)
        before = {"plain": "dry/auto/auto/20", "extra": "dry/auto/auto/21"}
        ((tier, _key), claimants), = index.by_waveform.items()
        assert tier == "bytehash"
        assert {h.cell_key for h in claimants.values()} == set(
            before.values()
        )
        self._check(index, matrix, "MITSUBISHI144")
        restored = _payload_to_index(json.loads(json.dumps(
            _index_to_payload(index, "h", "C")
        )))
        self._check(restored, matrix, "MITSUBISHI144")

    @pytest.mark.asyncio
    async def test_a_pinned_device_is_sent_the_text_of_the_cell_heard(self):
        """Every dry press is sent its own waveform's cell's text by a
        same-file pinned device, as before the merge: a plain press is
        sent 22's text, never the representative's (the same bytes in
        another text, and on a device built from another file, another
        cell)."""
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        bench = shapes.PinnedBench(matrix, copy.deepcopy(matrix), index,
                                   index)
        own = {}
        for cell in matrix.cells:
            if cell.mode == "dry" and cell.temp in (22.0, 23.0):
                own[self._kind(cell)] = shapes.sent_row(
                    await bench.resolve(bench.hear(cell.pronto))
                )
        assert own["plain"] != own["extra"]
        sent = 0
        for cell in matrix.cells:
            if cell.mode != "dry":
                continue
            for press in _presses(cell.pronto):
                heard = bench.hear(press)
                if heard is None:
                    continue
                assert shapes.sent_row(await bench.resolve(heard)) == (
                    own[self._kind(cell)]
                )
                sent += 1
        assert sent > 0

    def test_an_unknown_waveform_of_the_state_gets_the_representative(self):
        """A handset writing an unread byte its own way: the state's read
        key, a waveform no claimant carries."""
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        press = d216._code(d216._settings(mode_power=0x21, byte15=0xC5))
        assert _match(index, press) == ("dry/low/23", None, TIER_BYTE_HASH)

    def test_a_claimant_answer_carries_the_groups_facts(self):
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        key = next(iter(index.by_waveform))
        representative = index.bytehash[key[1]]
        assert representative.spanned == (
            ("temp", tuple(float(t) for t in range(18, 24))),
        )
        for hit in index.by_waveform[key].values():
            assert hit.spanned == representative.spanned
            assert hit.members is representative.members
            assert hit.cell_name == "dry / fan: low / 18-23"

    def test_no_split_press_is_heard_as_two_cells(self):
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        gap = d216.D216.timing.gap_min
        for cell in matrix.cells:
            for transmitter in ("esphome", "broadlink"):
                for press in range(10):
                    whole, _ = d216._air(cell.pronto, press, transmitter)
                    heard = set()
                    for capture in [whole, *shapes.map_split(whole, gap)]:
                        identity = _identity(capture)
                        got = identity and index.match(*identity)
                        if got:
                            heard.add(got[0].cell_key)
                    assert len(heard) <= 1, (cell_key(cell), heard)

    @pytest.mark.asyncio
    async def test_a_composite_key_holding_none_of_the_presss_waveform(self):
        """``shape_sl_split``: the plain code's composite key holds 18 and
        19 (one waveform, two whole codes) and only the bytes half keeps
        it. The press with the plain S/L pattern and the moved code's
        waveform was heard as 21 on the normalized tier, and a same-file
        device sent the moved code's text. It still is, live and after a
        round trip of the stored index, where the composite key comes
        back a tuple and still answers last."""
        matrix = shapes.shape_sl_split()
        index = build_cell_index(matrix)
        press = shapes.shape_sl_split_press()
        identity = _identity(press)
        composite = ("fp_bytehash", (identity[1], identity[2]))
        assert composite in index.held_back
        assert set(index.by_waveform[composite]) == {
            _identity(matrix.cells[0].pronto)[3],
        }
        payload = json.loads(json.dumps(_index_to_payload(index, "h", "C")))
        assert ["fp_bytehash", list(composite[1])] in payload["held_back"]
        restored = _payload_to_index(payload)
        assert composite in restored.held_back
        assert composite in restored.by_waveform
        moved = matrix.cells[3].pronto
        for built in (index, restored):
            assert built.match(*identity) == (
                built.norm_fp.get(identity[3]), TIER_NORM_FP,
            )
            assert built.match(*identity)[0].cell_key == "dry/low/21"
            bench = shapes.PinnedBench(matrix, copy.deepcopy(matrix), built,
                                       built)
            sent = await bench.resolve(bench.hear(press))
            assert sent[1] == moved
            self._check(built, matrix, extra=[press])

    @pytest.mark.asyncio
    async def test_a_press_nothing_heard_is_named_by_a_key_of_its_waveform(
        self,
    ):
        """``shape_sl_split_two_codes``: every key the press reaches is held
        back, so nothing heard it before. The first, its composite key,
        holds only the plain waveform; the read key's map and the
        normalized key both name 21, the last cell of the press's own
        waveform, and the press is named and sent as 21, not as the
        composite key's representative."""
        matrix = shapes.shape_sl_split_two_codes()
        index = build_cell_index(matrix)
        press = shapes.shape_sl_split_press()
        identity = _identity(press)
        composite = ("fp_bytehash", (identity[1], identity[2]))
        assert composite in index.held_back
        assert identity[3] not in index.by_waveform[composite]
        assert ("norm_fp", identity[3]) in index.held_back
        assert index.match(*identity)[0].cell_key == "dry/low/21"
        bench = shapes.PinnedBench(matrix, copy.deepcopy(matrix), index,
                                   index)
        sent = await bench.resolve(bench.hear(press))
        assert sent[1] == matrix.cells[3].pronto
        self._check(index, matrix, extra=[press], goes_on=False)

    def test_a_composite_key_holding_an_earlier_cell_of_the_waveform(self):
        """``shape_sl_split_one_code``: 18's own text lands on a composite
        key that holds 18 and 19, kept only by the bytes half, and 18 is
        its claimant of that waveform; the normalized tier, which answered
        before, holds 20, the last cell of the waveform (the same whole
        code under another S/L pattern). It is still heard as 20."""
        matrix = shapes.shape_sl_split_one_code()
        index = build_cell_index(matrix)
        identity = _identity(matrix.cells[0].pronto)
        composite = ("fp_bytehash", (identity[1], identity[2]))
        assert composite in index.held_back
        assert index.by_waveform[composite][identity[3]].cell_key == (
            "dry/low/18"
        )
        assert index.match(*identity)[0].cell_key == "dry/low/20"
        self._check(index, matrix)

    def test_a_held_back_key_answers_what_nothing_else_hears(self):
        """Shape F0, where every key of the dry state is one only the
        bytes half keeps: nothing heard it before, and now the first key
        a press reaches answers it, at the composite tier."""
        matrix = shapes.shape_extra_pair_preamble()
        index = build_cell_index(matrix)
        dry = next(c for c in matrix.cells if c.mode == "dry")
        identity = _identity(dry.pronto)
        assert ("fp_bytehash", (identity[1], identity[2])) in index.held_back
        assert ("norm_fp", identity[3]) in index.held_back
        assert index.match(*identity) == (
            index.fp_bytehash[(identity[1], identity[2])], TIER_BYTE_HASH,
        )


# ---------------------------------------------------------------------------
# 3. The merged groups follow the merge
# ---------------------------------------------------------------------------


def _stored(index):
    for tier in ("decoded", "fp_bytehash", "bytehash"):
        yield from getattr(index, tier).values()
    yield from index.norm_fp.refs.values()
    for claimants in index.by_waveform.values():
        yield from claimants.values()


def _whole_code_groups(matrix) -> set:
    """The merged groups as they were before a key could merge two
    codes: two or more cells of one lattice carrying one whole code,
    never Off's or On's."""
    def inner(pronto):
        identity = wig_signal_identity(pronto) if pronto else None
        if identity is None:
            return None
        return whole_code_discriminator(
            identity.raw_timings, identity.byte_hash or identity.fingerprint,
        )

    power = {inner(code) for code in (matrix.off, matrix.on)} - {None}
    by_code: dict = {}
    lattices = [(None, matrix.cells)] + [
        ((extra.axis, extra.key), extra.cells)
        for extra in matrix.extras or ()
    ]
    for lattice, cells in lattices:
        for cell in cells:
            code = inner(cell.pronto)
            if code is not None:
                by_code.setdefault((lattice, code), []).append(_coords(cell))
    out = set()
    for (lattice, code), coords in by_code.items():
        members = tuple(dict.fromkeys(coords))
        if code not in power and len(members) > 1:
            out.add((lattice, members))
    return out


def _groups(index) -> set:
    return {(g.lattice, g.members) for g in index.groups.values()}


class TestTheGroupsFollowTheMerge:

    def test_one_group_per_read_key_at_every_tier(self):
        matrix = shapes.shape_extra_pair_preamble()
        index = build_cell_index(matrix)
        dry = tuple(
            ("dry", "low", None, float(t)) for t in range(18, 24)
        )
        assert _groups(index) == {(None, dry)}
        hits = [h for h in _stored(index) if h.mode == "dry"]
        assert hits
        for hit in hits:
            assert hit.members == dry
            assert hit.cell_name == "dry / fan: low / 18-23"

    def test_a_group_joined_only_by_its_whole_code_survives(self):
        """Every key of the dry captures is poisoned by another cell, so
        no surviving key connects them; their whole code still does,
        and the send side reads that group on a device's own index."""
        matrix = shapes.shape_1128_poisoned()
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            if cell.mode != "dry":
                continue
            identity = wig_signal_identity(cell.pronto)
            assert identity.decoded_fingerprint not in index.decoded
            assert (identity.fingerprint, identity.byte_hash) not in (
                index.fp_bytehash
            )
            assert identity.byte_hash not in index.bytehash
            assert index.norm_fp.get(
                norm_fingerprint(identity.raw_timings)
            ) is None
        dry = tuple(
            ("dry", "level1", None, float(t)) for t in range(16, 32)
        )
        assert _groups(index) == {(None, dry)}

    @pytest.mark.asyncio
    async def test_the_card_at_18_keeps_18(self):
        """PR 3's end state on shape F0, which nothing heard before: a
        handset press of the dry state is the group, the device is sent
        the representative's bytes, and the card keeps its dial."""
        from homeassistant.components.climate import HVACMode

        from .test_merged_group_dial import _pair

        matrix = shapes.shape_extra_pair_preamble()
        pair = await _pair(matrix)
        pair.card(HVACMode.DRY, "low", None, 18.0)

        sent = await pair.press(d216._code(d216._settings(mode_power=0x21)))

        representative = next(
            c for c in matrix.cells if (c.mode, c.temp) == ("dry", 23.0)
        )
        assert sent.pronto == representative.pronto
        assert pair.entity.hvac_mode == HVACMode.DRY
        assert pair.entity.target_temperature == 18.0

    @pytest.mark.parametrize("extras", [False, True])
    def test_whole_code_groups_are_unchanged_where_nothing_merges(
        self, extras,
    ):
        """On every field pack, both Komeco wigs and the seven shapes the
        golden was first written from, no read key merges two codes, so
        the groups are exactly the whole-code groups they always were."""
        sources = [
            (name, matrix) for name, matrix in shapes.golden_sources()
            if name != "synth-extra-pair-settings"
        ]
        assert len(sources) == 24
        for name, matrix in sources:
            if extras:
                matrix = shapes.with_extra(matrix)
            assert _groups(build_cell_index(matrix)) == (
                _whole_code_groups(matrix)
            ), name

    def test_members_are_in_lattice_order(self):
        """F1's group is joined by its read key, two whole codes in
        alternation; its members still come out in the file's order."""
        index = build_cell_index(shapes.shape_extra_pair_settings())
        ((_lattice_ref, members),) = _groups(index)
        assert [m[3] for m in members] == [float(t) for t in range(18, 24)]


# ---------------------------------------------------------------------------
# 4. The capture column of the golden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_capture_shaped_press_sends_other_bytes():
    """The second golden column, written before this round: every press
    off the air, whole and split, on every source where a read key
    forms, sends what it sent then (or nothing, as then)."""
    committed = json.loads(
        shapes.CAPTURE_GOLDEN.read_text(encoding="utf-8")
    )
    rows = await shapes.capture_rows()
    differ = []
    for source, by_name in committed["rows"].items():
        for name, column in by_name.items():
            got = rows.get(source, {}).get(name) or []
            if got != column:
                differ.append((source, name, len(column), len(got), sum(
                    1 for a, b in zip(column, got, strict=False) if a != b
                )))
    assert sum(len(c) for b in rows.values() for c in b.values()) == (
        committed["row_count"]
    )
    assert differ == []


# ---------------------------------------------------------------------------
# 5. The comb, byte for byte across the extraction of its applicability
# ---------------------------------------------------------------------------


def test_every_comb_receipt_is_unchanged():
    """The map's own reasons a field does not apply moved into
    ``field_readers.field_skip_reason`` for the sweep to share. Every
    field pack, clean and with its defects, and both Komeco wigs comb
    exactly as before: the digest of their 32 receipts at the commit
    before the move was 6a5d89794b43d08d.

    The MITSUBISHI144 measurement pass then moved that family's two
    receipts and nothing else: their findings are the same 49 and 54,
    and only their coverage changed, which now counts the new
    provisional ``temperature_fahrenheit`` field. The other 30 receipts
    hash as they did before the pass."""
    from custom_components.hair import wig_comb
    from custom_components.hair.wig_format import parse_wig

    from .test_field_sweep import PACKS, _pack_wig

    receipts = {}
    for path in sorted(PACKS.glob("*.json")):
        if path.name.endswith("-manifest.json"):
            continue
        receipts[path.name] = _pack_wig(path.name)
    for path in shapes.KOMECO_WIGS:
        receipts[path.name] = parse_wig(path.read_text()).wig
    rendered = {}
    for name, wig in receipts.items():
        result = wig_comb.comb_wig(wig)
        findings = [(f.check, f.keys, f.message, f.params)
                    for f in result.findings]
        rendered[name] = json.dumps(
            [findings, result.coverage.to_dict()], sort_keys=True,
            default=str,
        )
    assert len(rendered) == 32

    def digest(names) -> str:
        return hashlib.sha256(
            "".join(rendered[k] for k in sorted(names)).encode()
        ).hexdigest()[:16]

    assert digest(rendered) == "cd8630f9d2d87314"
    family = {"MITSUBISHI144.json", "MITSUBISHI144.defects.json"}
    assert digest(set(rendered) - family) == "0cc567881d850667"
    assert {name: digest([name]) for name in family} == {
        "MITSUBISHI144.json": "def0f161e2396527",
        "MITSUBISHI144.defects.json": "ab02044a47eb0a73",
    }
    # The findings as they were before the pass, digested the same way.
    before = {
        "MITSUBISHI144.json": (49, "3f1d6a6cec202bf6"),
        "MITSUBISHI144.defects.json": (54, "0967b72e0c59589d"),
    }
    for name in family:
        findings, coverage = json.loads(rendered[name])
        assert (len(findings), hashlib.sha256(
            json.dumps(findings, sort_keys=True).encode()
        ).hexdigest()[:16]) == before[name]
        assert coverage["fields"]["temperature_fahrenheit"] == {
            "checked": 0,
            "declined": {"field-provisional": 240, "no-coordinate": 1},
        }


# ---------------------------------------------------------------------------
# 6. The distinctness sweep asks the map
# ---------------------------------------------------------------------------


def _shared_keys(family: str, matrix) -> dict:
    """Read keys two labels share that the map says are two settings."""
    from custom_components.hair.wig_comb import matrix_codes

    by_key: dict = {}
    for code in matrix_codes(matrix):
        if code.key in ("off", "on"):
            continue
        key = EventParser.pronto_read_key(code.pronto)
        if key is not None:
            by_key.setdefault(key, []).append(code.coordinates)
    shared = {}
    for key, labels in by_key.items():
        for first, second in itertools.combinations(labels, 2):
            why = fr.labels_collide(MAPS[family], first, second)
            if why is not None:
                shared[key] = (first, second, why)
                break
    return shared


def _label(mode, fan, temp, swing=None) -> dict:
    return {"mode": mode, "fan": fan, "swing": swing, "temp": temp,
            "power": "on"}


class TestTheSweep:

    @pytest.mark.parametrize("family", ["DAIKIN216", "DAIKIN152"])
    def test_the_listed_packs_share_no_key(self, family):
        assert _shared_keys(family, _pack_matrix(f"{family}.json")) == {}

    def test_the_mitsubishi144_pack_shares_no_key(self):
        matrix = _pack_matrix("MITSUBISHI144.json")
        assert _shared_keys("MITSUBISHI144", matrix) == {}

    def test_a_label_collision_in_an_applying_dimension_fails(self):
        matrix = _pack_matrix("DAIKIN216.json")
        bad = copy.deepcopy(matrix)
        first = next(c for c in bad.cells if c.mode == "cool")
        second = next(
            c for c in bad.cells
            if (c.mode, c.fan, c.swing) == (first.mode, first.fan, first.swing)
            and c.temp != first.temp
        )
        second.pronto = first.pronto
        shared = _shared_keys("DAIKIN216", bad)
        assert [why for _a, _b, why in shared.values()] == [
            ("temp", "temperature"),
        ]

    def test_daikin152_dry_ignoring_the_fan_is_not_a_collision(self):
        """``fan_speed`` is forced in dry, while ``powerful``, ``economy``
        and ``sleep`` answer the fan with no ``applies_when``: they
        apply, and give both labels the same value."""
        assert fr.labels_collide(
            MAPS["DAIKIN152"], _label("dry", "auto", 18.0),
            _label("dry", "low", 18.0),
        ) is None
        assert fr.labels_collide(
            MAPS["DAIKIN152"], _label("dry", "auto", 18.0),
            _label("dry", "powerful", 18.0),
        ) == ("fan", "powerful")

    def test_a_dimension_whose_fields_all_stand_aside_is_skipped(self):
        """TCL112's two fan fields both say ``not_in: dry``."""
        assert fr.labels_collide(
            MAPS["TCL112"], _label("dry", "low", 24.0),
            _label("dry", "high", 24.0),
        ) is None
        assert fr.labels_collide(
            MAPS["TCL112"], _label("cool", "low", 24.0),
            _label("cool", "high", 24.0),
        ) == ("fan", "fan_speed")

    def test_a_dimension_no_field_answers_collides(self):
        assert fr.labels_collide(
            MAPS["DAIKIN216"], _label("cool", "low", 24.0, swing="off"),
            _label("cool", "low", 24.0, swing="spin"),
        ) == ("swing", "swing_vertical")
        bare = dataclasses.replace(MAPS["DAIKIN216"], fields=[
            f for f in MAPS["DAIKIN216"].fields if f.coordinate != "swing"
        ])
        assert fr.labels_collide(
            bare, _label("cool", "low", 24.0, swing="off"),
            _label("cool", "low", 24.0, swing="vertical"),
        ) == ("swing", None)

    def test_provisional_fields_count(self):
        """DAIKIN152's temperature is provisional, and its range ends
        are real collisions in the corpus."""
        assert not MAPS["DAIKIN152"].field_named("temperature").ratified
        assert fr.labels_collide(
            MAPS["DAIKIN152"], _label("cool", "auto", 30.0),
            _label("cool", "auto", 31.0),
        ) == ("temp", "temperature")


# ---------------------------------------------------------------------------
# 7. A lone frame of a listed family
# ---------------------------------------------------------------------------


def _flipper_presses() -> dict[str, str]:
    from custom_components.hair.ir_command import raw_to_pronto

    text = (
        FIXTURES / "adapters" / "flipper_raw_mitsubishi-MSY-GE10VA.ir"
    ).read_text(encoding="utf-8")
    out = {}
    for block in text.split("#")[1:]:
        lines = block.splitlines()
        name = next((ln.split(":", 1)[1].strip() for ln in lines
                     if ln.startswith("name:")), None)
        data = next((ln.split(":", 1)[1] for ln in lines
                     if ln.startswith("data:")), None)
        if name and data:
            values = [int(v) for v in data.split()]
            out[name] = raw_to_pronto(
                [v if i % 2 == 0 else -v for i, v in enumerate(values)],
                frequency=38000,
            )
    return out


def _without_answer_3(timings):
    """``read_bytes_hash`` as it was: answers 1 and 2 only."""
    saved = idm._lone_family_frame_key
    idm._lone_family_frame_key = lambda *args: None
    try:
        return idm.read_bytes_hash(timings)
    finally:
        idm._lone_family_frame_key = saved


class TestALoneFrame:

    def test_a_daikin216_frame_under_daikin152s_window_gets_no_key(self):
        """A DAIKIN216 settings frame whose header mark (2236 us) is
        inside DAIKIN216's window and under DAIKIN152's. The shared path
        gives up, and the shared frame's family is never asked on its
        own: a family key here is one no whole press carries."""
        cell = _pack_matrix("DAIKIN216.json").cells[7]
        lone = shapes.map_split(cell.pronto, MAPS["DAIKIN216"].timing.gap_min)[1]
        timings = [abs(v) for v in _us(lone)]
        assert idm.read_bytes_hash(timings) == _read_key(cell.pronto)
        timings[0] = 2236
        assert MAPS["DAIKIN216"].timing.header_mark.holds(2236)
        assert not MAPS["DAIKIN152"].timing.header_mark.holds(2236)
        assert idm.read_bytes_hash(timings) is None

    def test_on_the_lists_without_mitsubishi144_nothing_changes(self):
        """A2 is inert for an unlisted family. With MITSUBISHI144 taken
        off the lists, as they shipped before it joined, no family
        reaches answer 3 (both Daikins are in the shared group): every
        fourth cell of every field pack, whole and split at its map's
        gap, hashes as it did."""
        with _unlisted("MITSUBISHI144"):
            for family, field_map in MAPS.items():
                path = FIXTURES / "field-packs" / f"{family}.json"
                if not path.is_file():
                    continue
                for cell in _pack_matrix(path.name).cells[::4]:
                    for code in [cell.pronto, *shapes.map_split(
                            cell.pronto, field_map.timing.gap_min)]:
                        timings = _us(code)
                        assert idm.read_bytes_hash(timings) == (
                            _without_answer_3(timings)
                        ), (family, cell_key(cell))

    def test_on_the_shipped_lists_only_mitsubishi144s_lone_frames_move(self):
        """Listed, answer 3 keys MITSUBISHI144's lone frames, each with
        its whole press's key, and nothing else: every other pack's
        codes and pieces, and every whole MITSUBISHI144 code, hash as
        they would without it."""
        moved = 0
        for family, field_map in MAPS.items():
            path = FIXTURES / "field-packs" / f"{family}.json"
            if not path.is_file():
                continue
            for cell in _pack_matrix(path.name).cells[::4]:
                whole = _us(cell.pronto)
                assert idm.read_bytes_hash(whole) == _without_answer_3(whole)
                pieces = shapes.map_split(
                    cell.pronto, field_map.timing.gap_min)
                for piece in pieces if len(pieces) > 1 else ():
                    timings = _us(piece)
                    got = idm.read_bytes_hash(timings)
                    if got == _without_answer_3(timings):
                        continue
                    assert family == "MITSUBISHI144", (family, cell_key(cell))
                    assert got == _read_key(cell.pronto)
                    moved += 1
        assert moved > 0

    def test_the_air_path_rows_form_the_file_cells_key(self):
        """The bench's own captures: lone frames of two MITSUBISHI144
        cells through two receivers, and the two injected rows. The four
        Broadlink rows of C2 that read as nothing stay nothing."""
        from .test_matrix_listener import _air_captures, _air_code, _heard

        formed = nothing = 0
        for code in ("C1", "C2"):
            key = _read_key(_air_code(code))
            for row in _air_captures(code):
                if row["transmitter"] not in ("esphome", "broadlink", "inject"):
                    continue
                heard = _heard(row)
                if fr.read_code(heard.code).protocol_id is None:
                    assert heard.byte_hash != key
                    assert EventParser.pronto_read_key(heard.code) is None
                    nothing += 1
                    continue
                assert heard.byte_hash == key, (code, row["transmitter"])
                formed += 1
        assert (formed, nothing) == (42, 4)

    def test_each_half_of_a_flipper_press_forms_the_whole_press_key(self):
        gap = MAPS["MITSUBISHI144"].timing.gap_min
        presses = _flipper_presses()
        assert {"POWER", "Off"} <= set(presses)
        for name in ("POWER", "Off"):
            whole = _read_key(presses[name])
            halves = shapes.map_split(presses[name], gap)
            assert len(halves) == 2
            for half in halves:
                verdict = idm.identify_lone_frame(_us(half))
                assert (verdict.protocol_id, verdict.is_setting) == (
                    "MITSUBISHI144", True,
                )
                assert EventParser.pronto_read_key(half) == whole, name
                assert _without_answer_3(_us(half)) is None

    def test_no_lone_frame_of_the_pack_forms_a_wrong_key(self):
        gap = MAPS["MITSUBISHI144"].timing.gap_min
        right = 0
        for cell in _pack_matrix("MITSUBISHI144.json").cells[::6]:
            whole = _read_key(cell.pronto)
            for transmitter in ("esphome", "broadlink"):
                for press in range(4):
                    heard, _ = d216._air(cell.pronto, press, transmitter)
                    for piece in shapes.map_split(heard, gap):
                        key = EventParser.pronto_read_key(piece)
                        assert key in (None, whole), cell_key(cell)
                        right += key == whole
        assert right > 0

    def test_a_frame_two_maps_claim_names_neither(self):
        """Answer 3 needs the verdict to name the family alone. A frame
        a second family also claimed would name neither; the Daikin
        settings frame is the one such frame the shared rule covers."""
        cell = _pack_matrix("MITSUBISHI144.json").cells[0]
        piece = shapes.map_split(
            cell.pronto, MAPS["MITSUBISHI144"].timing.gap_min
        )[0]
        assert EventParser.pronto_read_key(piece) == _read_key(cell.pronto)
        real = idm.lone_frame_candidates
        twice = lambda t: [*real(t), idm.LoneFrame("OEM112", 0, True)]  # noqa: E731
        idm.lone_frame_candidates = twice
        try:
            assert idm.identify_lone_frame(_us(piece)) is None
            assert EventParser.pronto_read_key(piece) is None
        finally:
            idm.lone_frame_candidates = real
        daikin = _pack_matrix("DAIKIN152.json").cells[3]
        lone = shapes.map_split(
            daikin.pronto, MAPS["DAIKIN152"].timing.gap_min
        )[-1]
        assert len(idm.lone_frame_candidates(_us(lone))) == 2
        assert EventParser.pronto_read_key(lone) == _read_key(daikin.pronto)

    def test_a_frame_failing_a_ratified_rule_forms_no_key(self):
        """One payload bit flipped, the checksum left as it was."""
        cell = _pack_matrix("MITSUBISHI144.json").cells[0]
        piece = shapes.map_split(
            cell.pronto, MAPS["MITSUBISHI144"].timing.gap_min
        )[0]
        timing = MAPS["MITSUBISHI144"].timing
        timings = [abs(v) for v in _us(piece)]
        assert idm.read_bytes_hash(timings) == _read_key(cell.pronto)
        # The fifth byte's first bit: past the identity bytes.
        pair = 1 + 8 * 5
        space = 2 * pair + 1
        one = timing.one.holds(timings[space])
        timings[space] = round(
            timing.zero.nominal if one else timing.one.nominal
        )
        assert idm.read_bytes_hash(timings) is None

    def test_a_setting_frame_is_laid_where_its_verdict_says(self):
        """PANASONIC216's settings frame is frame 1 of [64, 152]: laid at
        index 0 it reads nothing. Listed, its lone frame 1 forms the key
        of its whole press."""
        field_map = MAPS["PANASONIC216"]
        cell = _pack_matrix("PANASONIC216.json").cells[0]
        lone = shapes.map_split(cell.pronto, field_map.timing.gap_min)[1]
        with _listed("PANASONIC216"):
            whole = _read_key(cell.pronto)
            verdict = idm.identify_lone_frame(_us(lone))
            assert (verdict.protocol_id, verdict.frame_index) == (
                "PANASONIC216", 1,
            )
            assert EventParser.pronto_read_key(lone) == whole
        frame = fr.read_code(cell.pronto).frames[1]
        assert idm.read_bytes_key(field_map, [frame, ()]) is None

    def test_identify_lone_frame_still_names_mitsubishi144_alone(self):
        cell = _pack_matrix("MITSUBISHI144.json").cells[0]
        for piece in shapes.map_split(
                cell.pronto, MAPS["MITSUBISHI144"].timing.gap_min):
            candidates = idm.lone_frame_candidates(_us(piece))
            assert [(c.protocol_id, c.frame_index) for c in candidates] == [
                ("MITSUBISHI144", 0),
            ]


# ---------------------------------------------------------------------------
# 8. Triggers and the known-command index, once such a family is listed
# ---------------------------------------------------------------------------


def _signal(pronto: str):
    """One capture, normalized as the Sniffer normalizes it."""
    from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
    from custom_components.hair.models import CaptureResult
    from custom_components.hair.signal_monitor import normalize

    raw = ProntoCommand(pronto).get_raw_timings()
    return normalize(CaptureResult(
        protocol="PRONTO", code=raw_to_pronto(raw, frequency=38000),
        raw_timings=raw, frequency=38000,
    ))


def _learned(pronto: str, name: str, remote_id: str):
    """A trigger learned from a capture, as the Sniffer mints one."""
    from custom_components.hair.models import IRTrigger

    signal = _signal(pronto)
    return IRTrigger(
        name=name, signal_fingerprint=signal.sig_fp, protocol="PRONTO",
        code=signal.code, byte_hash=signal.byte_hash,
        decoded_fingerprint=signal.decoded_fingerprint,
        trigger_remote_id=remote_id, origin="remote",
    )


def _fires(trigger, pronto: str) -> bool:
    signal = _signal(pronto)
    return trigger.matches_signal(
        signal.sig_fp, signal.byte_hash, signal.decoded_fingerprint,
        signal.decode_covers,
    )


def _one_press() -> tuple[str, list[str]]:
    """A MITSUBISHI144 press off the air, and its two frames."""
    from .test_matrix_listener import _air_code

    whole, _ = d216._air(_air_code("C1"), 1, "esphome")
    frames = shapes.map_split(whole, MAPS["MITSUBISHI144"].timing.gap_min)
    assert len(frames) == 2
    return whole, frames


class TestTriggersAndKnownCommands:

    def test_a_whole_press_trigger_fires_on_a_lone_frame(self):
        whole, frames = _one_press()
        trigger = _learned(whole, "Cool", "r1")
        assert all(_fires(trigger, frame) for frame in frames)

    def test_a_lone_frame_trigger_fires_on_the_whole_press(self):
        whole, frames = _one_press()
        trigger = _learned(frames[1], "Cool", "r1")
        assert _fires(trigger, whole)
        assert _fires(trigger, frames[0])

    def test_unlisted_a_lone_frame_fires_nothing(self):
        """As the lists shipped before MITSUBISHI144 joined."""
        with _unlisted("MITSUBISHI144"):
            whole, frames = _one_press()
            trigger = _learned(whole, "Cool", "r1")
            assert not any(_fires(trigger, frame) for frame in frames)

    def test_the_second_frame_of_one_press_fires_once(self):
        from unittest.mock import MagicMock

        from custom_components.hair.models import TriggerRemote
        from custom_components.hair.storage import HAIRStore
        from custom_components.hair.trigger_manager import TriggerManager

        store = HAIRStore(MagicMock())
        store._loaded = True
        remote = TriggerRemote(name="Handset", origin="remote")
        store._trigger_remotes[remote.id] = remote
        whole, frames = _one_press()
        trigger = _learned(whole, "Cool", remote.id)
        store._triggers[trigger.id] = trigger
        hass = MagicMock()
        manager = TriggerManager(hass, store)
        fired = []
        for frame in frames:
            signal = _signal(frame)
            fired.append(manager.on_signal_captured(
                signal.sig_fp, "PRONTO", signal.code, None, "infrared.rx",
                signal.byte_hash, signal.decoded_fingerprint,
                signal.norm_fp, signal.decode_covers,
            ))
        assert [len(f) for f in fired] == [1, 0]

    @pytest.mark.parametrize("listed", [False, True])
    def test_a_known_commands_lone_frame_is_suppressed(self, listed):
        """Suppression asks the known-command index, which matches on the
        byte hash: once a licensed family is listed, a lone frame of a
        known command is that command, exactly as its whole press is."""
        from unittest.mock import MagicMock

        from custom_components.hair.const import CommandCategory
        from custom_components.hair.models import CaptureResult, IRDevice
        from custom_components.hair.storage import HAIRStore

        with contextlib.nullcontext() if listed else _unlisted("MITSUBISHI144"):
            whole, frames = _one_press()
            signal = _signal(whole)
            device = IRDevice(name="Learned")
            command = CaptureResult(
                protocol="PRONTO", code=signal.code,
                raw_timings=list(signal.raw_timings), frequency=38000,
            ).to_command("Cool", CommandCategory.CUSTOM)
            command.signal_fingerprint = signal.sig_fp
            command.byte_hash = signal.byte_hash
            command.decoded_fingerprint = signal.decoded_fingerprint
            device.commands.append(command)
            store = HAIRStore(MagicMock())
            store._loaded = True
            store._data[device.id] = device
            store._rebuild_command_index()
            for frame in frames:
                lone = _signal(frame)
                found = store.match_command(
                    lone.decoded_fingerprint, lone.sig_fp, lone.byte_hash,
                )
                assert found == ((device.id, command.id) if listed else None)
