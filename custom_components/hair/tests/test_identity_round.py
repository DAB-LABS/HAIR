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
the merge. The second is built and pinned under a patched list: on the
shipped lists no family reaches it, so it changes nothing yet.

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


@pytest.fixture
def m144_listed():
    with _listed("MITSUBISHI144"):
        yield


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
_HEAT = d216._settings(mode_power=0x41)        # heat, the same bytes else
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


def _presses(pronto: str) -> list[str]:
    """The file code, then ten capture-shaped presses per transmitter,
    whole and split at the map's gap."""
    gap = d216.D216.timing.gap_min
    out = [pronto]
    for transmitter in ("esphome", "broadlink"):
        for press in range(10):
            heard, _ = d216._air(pronto, press, transmitter)
            out.append(heard)
            out.extend(shapes.map_split(heard, gap))
    return out


class TestExactWaveformWins:
    """Shape F1: dry / low / 18-23, the even temperatures one waveform
    and the odd ones another, one set of bytes.

    Before this round the read key was refused, and each waveform's own
    composite and normalized keys answered the last cell of that
    waveform: dry / low / 22 for the plain code and 23 for the extra
    pair. The read key now merges all six, and its representative is
    23, so without the by-waveform answer every plain press that came
    in through the read key would be named 23 and a pinned device sent
    23's text instead of 22's.
    """

    BEFORE: ClassVar[dict[str, str]] = {
        "plain": "dry/low/22", "extra": "dry/low/23",
    }

    @staticmethod
    def _kind(cell) -> str:
        return "plain" if int(cell.temp) % 2 == 0 else "extra"

    def _heard(self, index, matrix):
        """(cell, press, heard) for every press of every cell."""
        for cell in matrix.cells:
            for press in _presses(cell.pronto):
                identity = _identity(press)
                yield cell, press, (
                    None if identity is None else index.match(*identity)
                )

    def _check(self, index, matrix):
        through_the_map = 0
        for cell, press, heard in self._heard(index, matrix):
            if heard is None:
                continue
            hit, tier = heard
            if cell.mode == "cool":
                assert hit.cell_key == cell_key(cell)
                continue
            assert hit.cell_key == self.BEFORE[self._kind(cell)], press
            identity = _identity(press)
            if (tier == TIER_BYTE_HASH
                    and (identity[1], identity[2]) not in index.fp_bytehash
                    and hit.cell_key == self.BEFORE["plain"]):
                through_the_map += 1
        # The point of the map: plain presses the air moved off their
        # composite key, answered at the read key with their own cell.
        assert through_the_map > 0

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
        self._check(build_cell_index(matrix), matrix)

    def test_and_after_a_restart(self):
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        restored = _payload_to_index(json.loads(json.dumps(
            _index_to_payload(index, "h", "C")
        )))
        assert restored.by_waveform.keys() == index.by_waveform.keys()
        self._check(restored, matrix)

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

    def test_a_composite_key_round_trips_as_a_tuple(self):
        """Nothing guarantees an S/L fingerprint separates two waveforms,
        so the map is kept on the composite tier too, and JSON cannot
        key a dict by a tuple. Written as a list, read back as a tuple,
        and answered from it."""
        matrix = shapes.shape_extra_pair_settings()
        index = build_cell_index(matrix)
        claimants = next(iter(index.by_waveform.values()))
        plain = _identity(next(
            c.pronto for c in matrix.cells if c.mode == "dry" and c.temp == 18
        ))
        composite = (plain[1], plain[2])
        assert composite in index.fp_bytehash
        index.by_waveform[("fp_bytehash", composite)] = {
            plain[3]: claimants[plain[3]],
        }
        payload = json.loads(json.dumps(_index_to_payload(index, "h", "C")))
        assert ["fp_bytehash", list(composite)] in [
            entry[:2] for entry in payload["by_waveform"]
        ]
        restored = _payload_to_index(payload)
        assert ("fp_bytehash", composite) in restored.by_waveform
        assert restored.match(*plain)[0].cell_key == "dry/low/22"


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
    before the move."""
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
    digest = hashlib.sha256(
        "".join(rendered[k] for k in sorted(rendered)).encode()
    ).hexdigest()[:16]
    assert digest == "6a5d89794b43d08d"


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

    def test_the_mitsubishi144_pack_shares_no_key(self, m144_listed):
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
