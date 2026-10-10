"""The cell index stops naming Off for every Daikin press.

Live since v0.10.0 and in every release through v0.16.0. Three facts
met and produced it:

- Every DAIKIN216 code decodes to the same
  ``KASEIKYO64:0xda11:0x20f000000002`` with ``decode_covers=False``,
  because the decoder reads only the constant frame 0.
- ``build_cell_index`` wrote each tier last-write-wins and added
  ``off``/``on`` AFTER the cells, so the one decoded key pointed at Off.
- ``CellIndex.match`` tries the decoded tier first.

So a matrix remote hearing a Daikin handset reported Off for every
button, and a remote pinned to a Daikin device sent Off for every
button. The byte hash and the S/L fingerprint are frame-0 only too
(``_pronto_identity_timings`` stops at the first gap), so the lower
tiers could not save it either.

This is step 1 of two. It stops the wrong answer; it does not yet make
a Daikin press find its right cell. Step 2 is payload-frame identity.
"""
from __future__ import annotations

import json as _json
from pathlib import Path as _Path

import pytest

from custom_components.hair.identity import (
    TIER_BYTE_HASH,
    norm_fingerprint,
    whole_code_discriminator,
)
from custom_components.hair.matrix_listener import (
    INDEX_FORMAT,
    build_cell_index,
)
from custom_components.hair.wig_adapters import _broadlink_b64_to_pronto
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    cell_key,
)
from custom_components.hair.wig_identity import wig_signal_identity

FIXTURES = _Path(__file__).parent / "fixtures"
PACKS = FIXTURES / "field-packs"


# ---------------------------------------------------------------------------
# Lattices out of the shipped field packs
# ---------------------------------------------------------------------------


def _pack_matrix(name: str) -> ClimateMatrix:
    """One field pack as a lattice, the way the census scripts read it."""
    raw = _json.loads((PACKS / name).read_text(encoding="utf-8"))
    base64 = raw.get("commandsEncoding") == "Base64"
    commands = raw["commands"]

    def convert(value):
        if not isinstance(value, str):
            return None
        if base64:
            return _broadlink_b64_to_pronto(value)
        return value if value.startswith("0000") else None

    codes: dict[tuple, str | None] = {}

    def walk(value, path):
        if isinstance(value, dict):
            for key, inner in value.items():
                walk(inner, [*path, key])
        elif isinstance(value, str):
            codes[tuple(path)] = convert(value)

    for mode, value in commands.items():
        if mode not in ("off", "on"):
            walk(value, [mode])

    cells = []
    for path, pronto in codes.items():
        if not pronto:
            continue
        try:
            temp = float(path[-1])
        except ValueError:
            continue
        cells.append(ClimateCell(
            mode=path[0], fan=path[1] if len(path) > 2 else "auto",
            swing=path[2] if len(path) == 4 else None,
            temp=temp, pronto=pronto,
        ))
    assert cells, name
    return ClimateMatrix(
        min_temp=min(c.temp for c in cells), max_temp=max(c.temp for c in cells),
        precision=1.0, modes=sorted({c.mode for c in cells}),
        fan_modes=sorted({c.fan for c in cells}),
        swing_modes=sorted({c.swing for c in cells if c.swing}),
        off=convert(commands.get("off")), cells=cells,
    )


def _match(index, pronto):
    """Match a code the way the capture path does, norm_fp and coverage
    included. Returns (cell_key, power, tier) or None."""
    identity = wig_signal_identity(pronto)
    assert identity is not None
    result = index.match(
        identity.decoded_fingerprint, identity.fingerprint,
        identity.byte_hash, norm_fingerprint(identity.raw_timings),
        identity.decode_covers,
    )
    if result is None:
        return None
    hit, tier = result
    return (hit.cell_key, hit.power, tier)


def _lone_frame_0(pronto: str) -> str:
    """The first frame on its own, as a receiver delivers it.

    A receiver ends its capture at the gap, so a two-frame press
    arrives as two captures. This is the half the Daikin decoder reads.
    """
    from custom_components.hair.const import PRONTO_GAP_THRESHOLD

    words = [int(w, 16) for w in pronto.split()]
    head, body = words[:4], words[4:]
    out: list[int] = []
    for word in body:
        out.append(word)
        if word >= PRONTO_GAP_THRESHOLD:
            break
    if len(out) % 2:
        out.append(PRONTO_GAP_THRESHOLD)
    return " ".join(
        f"{w:04X}" for w in [head[0], head[1], len(out) // 2, 0, *out]
    )


# ---------------------------------------------------------------------------
# The bug itself
# ---------------------------------------------------------------------------


class TestADaikinPressNamesItsOwnCell:
    """Step 1 made these name nothing rather than Off. Step 2 makes
    them name the right cell, which is what these now pin. The shared
    decode and the coverage gate are unchanged and still tested: they
    are why the decoded tier stays out of the way."""

    def test_the_shared_decode_is_really_shared(self):
        """The premise, pinned so the test below cannot pass for the
        wrong reason if the decoder ever changes."""
        matrix = _pack_matrix("DAIKIN216.json")
        decoded = set()
        covers = set()
        hashes = set()
        for cell in matrix.cells:
            identity = wig_signal_identity(cell.pronto)
            decoded.add(identity.decoded_fingerprint)
            covers.add(identity.decode_covers)
            hashes.add(identity.byte_hash)
        assert len(matrix.cells) == 200
        assert decoded == {"KASEIKYO64:0xda11:0x20f000000002"}
        assert covers == {False}
        # The byte hash was 1 too until setting-frame identity landed
        # (step 2). The DECODE is still the shared one -- the decoder
        # still reads only the constant frame 0 -- which is why the
        # coverage gate this file exists for still matters.
        assert len(hashes) == 200

    def test_every_daikin_216_cell_matches_its_own_cell(self):
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            assert _match(index, cell.pronto) == (
                cell_key(cell), None, TIER_BYTE_HASH
            ), cell_key(cell)

    def test_a_lone_frame_0_still_matches_nothing(self):
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        assert [
            c for c in matrix.cells
            if _match(index, _lone_frame_0(c.pronto))
        ] == []

    def test_the_daikin_off_code_matches_off(self):
        """Off shared frame 0 with all 200 states, so step 1 had to
        refuse it along with them. Its SETTING frame is its own, so it
        comes back now."""
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        assert matrix.off
        assert _match(index, matrix.off) == ("off", "off", TIER_BYTE_HASH)

    def test_daikin_152_cells_find_their_own_cell(self):
        """Not what the bug report predicted, and better.

        DAIKIN152 shares one decoded key across all 60 cells the same
        way, and 59 of them used to answer as ``heat_cool/high/30``.
        Its frame-0 BYTE HASHES are distinct per code, though, so with
        the bogus tier-1 answer out of the way the byte-hash tier
        answers correctly. Pinned here because it is a behaviour change
        the kickoff did not anticipate.
        """
        matrix = _pack_matrix("DAIKIN152.json")
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            assert _match(index, cell.pronto) == (
                cell_key(cell), None, TIER_BYTE_HASH
            ), cell_key(cell)


# ---------------------------------------------------------------------------
# The eleven families that were already right
# ---------------------------------------------------------------------------

#: Every pack, and what each cell's own code should resolve to. The
#: eleven unaffected families answer at the byte-hash tier, either with
#: the cell itself or with a cell carrying an IDENTICAL code, which is
#: one waveform under two coordinates and resolves by design.
_UNAFFECTED = [
    "AUX104.json", "CHIGO96B.json", "GREE.json", "MHI152.json",
    "MHI160.json", "MHI48.json", "MIDEA_COOLIX.json", "MITSUBISHI144.json",
    "OEM112.json", "TCL112.json", "ZHLT01.json",
]


class TestTheWholeCorpus:

    @pytest.mark.parametrize("name", _UNAFFECTED)
    def test_an_unaffected_family_still_answers_for_every_cell(self, name):
        matrix = _pack_matrix(name)
        index = build_cell_index(matrix)
        by_key = {cell_key(c): c for c in matrix.cells}
        for cell in matrix.cells:
            result = _match(index, cell.pronto)
            assert result is not None, f"{name} {cell_key(cell)}"
            key, power, tier = result
            assert power is None
            assert tier == TIER_BYTE_HASH
            # Itself, or a cell holding the very same code.
            assert key == cell_key(cell) or by_key[key].pronto == cell.pronto

    @pytest.mark.parametrize("name", [*_UNAFFECTED, "DAIKIN152.json",
                                      "DAIKIN216.json"])
    def test_no_cell_anywhere_matches_a_different_code(self, name):
        """The one invariant this change exists to buy, over every
        lattice the repo ships."""
        matrix = _pack_matrix(name)
        index = build_cell_index(matrix)
        by_key = {cell_key(c): c for c in matrix.cells}
        for cell in matrix.cells:
            result = _match(index, cell.pronto)
            if result is None:
                continue
            key, power, _tier = result
            assert power is None, f"{name} {cell_key(cell)} -> power {power}"
            assert by_key[key].pronto == cell.pronto, (
                f"{name} {cell_key(cell)} -> {key}, a different code"
            )


# ---------------------------------------------------------------------------
# The rule itself: shared keys, identical codes, jitter
# ---------------------------------------------------------------------------

_A = "0000 006D 0004 0000 0020 0040 0020 0040 0060 0040 0020 0040"
_B = "0000 006D 0004 0000 0040 0020 0040 0020 0040 0060 0040 0020"
_OFF = "0000 006D 0002 0000 0060 0020 0060 0020"


def _toy(cells, off=None, on=None) -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0, modes=["cool"],
        fan_modes=["auto"], swing_modes=[], off=off, on=on, cells=cells,
    )


class TestTheRule:

    def test_two_cells_with_the_identical_code_still_resolve(self):
        """One waveform under two coordinates IS one press. The eleven
        unaffected families depend on this."""
        matrix = _toy([
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A),
            ClimateCell(mode="cool", fan="high", temp=22.0, pronto=_A),
        ])
        index = build_cell_index(matrix)
        result = _match(index, _A)
        assert result is not None
        assert result[0] in {"cool/auto/22", "cool/high/22"}

    def test_the_same_code_with_jitter_is_still_one_waveform(self):
        """A capture-built lattice can hold one press twice, a few
        microseconds apart. Refusing that pair would be the fix
        overreaching (owner ruling 2026-09-25).
        """
        jittered = "0000 006D 0004 0000 0021 0041 0021 003F 0061 0041 001F 0040"
        matrix = _toy([
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A),
            ClimateCell(mode="cool", fan="high", temp=22.0, pronto=jittered),
        ])
        first = wig_signal_identity(_A)
        second = wig_signal_identity(jittered)
        assert (whole_code_discriminator(first.raw_timings)
                == whole_code_discriminator(second.raw_timings))
        index = build_cell_index(matrix)
        assert _match(index, _A) is not None

    def test_a_lattice_whose_off_is_distinct_still_matches_off(self):
        matrix = _toy(
            [ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A)],
            off=_OFF,
        )
        index = build_cell_index(matrix)
        assert _match(index, _OFF) == ("off", "off", TIER_BYTE_HASH)
        assert _match(index, _A) == ("cool/auto/22", None, TIER_BYTE_HASH)

    def test_the_discriminator_separates_every_state(self):
        """It reads the whole code, so it separated all 200 states even
        when the byte hash could not. Since step 2 the byte hash does
        too, but the discriminator is what a shared key is refused on
        and it still has to hold on its own."""
        matrix = _pack_matrix("DAIKIN216.json")
        codes = {
            whole_code_discriminator(
                wig_signal_identity(c.pronto).raw_timings
            )
            for c in matrix.cells
        }
        assert len(codes) == 200


class TestTheCoverageGate:

    def test_a_non_covering_decode_is_not_indexed(self):
        matrix = _pack_matrix("DAIKIN216.json")
        assert build_cell_index(matrix).decoded == {}

    def test_a_skipped_decode_still_reaches_the_normalized_tier(self):
        """The old condition read "normalized only if NOTHING decoded",
        which would have shut the lowest tier for exactly the captures
        that now need it."""
        matrix = _toy([ClimateCell(
            mode="cool", fan="auto", temp=22.0, pronto=_A,
        )])
        index = build_cell_index(matrix)
        identity = wig_signal_identity(_A)
        norm = norm_fingerprint(identity.raw_timings)
        index.bytehash.clear()
        index.fp_bytehash.clear()
        assert index.match(
            "SOMETHING:0x1:0x2", None, None, norm, False,
        ) is not None
        # ... and a decode that DID cover still does not fall through.
        assert index.match(
            "SOMETHING:0x1:0x2", None, None, norm, True,
        ) is None


class TestTheStoredIndex:

    def test_the_format_is_10_and_a_9_is_rejected(self, tmp_path):
        from custom_components.hair.matrix_listener import (
            _build_and_store_index,
            _load_stored_index,
        )
        from custom_components.hair.matrix_store import index_path, write_matrix

        matrix = _toy(
            [ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A)],
            off=_OFF,
        )
        write_matrix(tmp_path, "r1", matrix)
        _build_and_store_index(str(tmp_path), "r1", matrix, "C")
        assert INDEX_FORMAT == "hair-cell-index/11"
        assert _load_stored_index(str(tmp_path), "r1", "C") is not None

        path = index_path(tmp_path, "r1")
        payload = _json.loads(path.read_text())
        assert payload["unit"] == "C"
        assert payload["matrix"]
        payload["format"] = "hair-cell-index/10"
        path.write_text(_json.dumps(payload))
        assert _load_stored_index(str(tmp_path), "r1", "C") is None


# ---------------------------------------------------------------------------
# The consequence the owner actually felt: a pinned device
# ---------------------------------------------------------------------------


class TestAPinnedDaikinDeviceIsSentTheRightState:
    """``_async_dispatch_pinned_cell`` sent ``matrix.off`` for a hit
    whose power is "off", which is how every button on the handset came
    out of the blaster as Off. Step 1 made it send nothing; step 2
    makes it send the state that was actually pressed."""

    @staticmethod
    def _listener(matrix):
        from unittest.mock import AsyncMock, MagicMock

        from custom_components.hair.const import DOMAIN
        from custom_components.hair.matrix_listener import MatrixListener
        from custom_components.hair.models import TriggerRemote

        remote = TriggerRemote(
            id="r1", name="Bedroom AC", climate_matrix=True,
            pinned_device_ids=["dev-1"],
        )
        store = MagicMock()
        store.get_all_trigger_remotes = MagicMock(return_value=[remote])
        store.get_trigger_remote = MagicMock(return_value=remote)
        store.update_trigger_remote = MagicMock()
        store.async_save = AsyncMock()
        device = MagicMock(id="dev-1", climate_matrix=True)
        device.name = "Bedroom Head Unit"
        store.get_device = MagicMock(return_value=device)

        hass = MagicMock()
        hass.data = {DOMAIN: {"entry-1": {"store": store}}}
        hass.config.config_dir = "/config"
        hass.config.units.temperature_unit = "°C"
        hass.bus.async_fire = MagicMock()
        tasks: list = []
        hass.async_create_task = MagicMock(side_effect=tasks.append)
        hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )

        manager = MagicMock()
        manager.dispatch_cell_retransmit = MagicMock(return_value=True)
        manager.resolve_receiver_area = MagicMock(return_value=(None, None))
        devices = MagicMock()
        devices.async_get_matrix = AsyncMock(return_value=matrix)
        listener = MatrixListener(hass, store, manager, devices)
        listener._matrix_cache["r1"] = matrix
        listener._index_cache["r1"] = build_cell_index(matrix)
        return listener, manager, tasks

    @pytest.mark.asyncio
    async def test_a_daikin_press_dispatches_that_state(self):
        matrix = _pack_matrix("DAIKIN216.json")
        listener, manager, tasks = self._listener(matrix)
        pressed = matrix.cells[7]
        identity = wig_signal_identity(pressed.pronto)

        heard = await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, None,
            norm_fingerprint(identity.raw_timings), identity.decode_covers,
        )
        while tasks:
            batch, tasks[:] = list(tasks), []
            for coro in batch:
                await coro

        assert heard == ["r1"]
        manager.dispatch_cell_retransmit.assert_called_once()
        assert manager.dispatch_cell_retransmit.call_args.args[2] == (
            cell_key(pressed)
        )

    @pytest.mark.asyncio
    async def test_a_press_on_a_lattice_that_resolves_still_dispatches(self):
        """The same path, on a family this change does not touch, so a
        no-send above cannot be the listener being broken outright."""
        matrix = _pack_matrix("MHI160.json")
        listener, manager, tasks = self._listener(matrix)
        pressed = matrix.cells[3]
        identity = wig_signal_identity(pressed.pronto)

        heard = await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, None,
            norm_fingerprint(identity.raw_timings), identity.decode_covers,
        )
        while tasks:
            batch, tasks[:] = list(tasks), []
            for coro in batch:
                await coro

        assert heard == ["r1"]
        manager.dispatch_cell_retransmit.assert_called_once()


# ---------------------------------------------------------------------------
# A key that merges a group names the group
# ---------------------------------------------------------------------------
#
# Since the /4 refusal two cells whose whole codes are the same merge
# under a key rather than poisoning it, and the key keeps the LAST of
# them. A file that stores one code under several settings therefore
# answered every press of it with its last cell. The index now records
# each group (the cells of one lattice that claimed under one code) and
# tells every stored hit what its group spans, while every key goes on
# resolving exactly the cell it resolved before.


def _without_groups(matrix):
    """The index as it was built before groups: the same rule with the
    group pass switched off."""
    from unittest.mock import patch

    with patch(
        "custom_components.hair.matrix_listener._attach_groups",
        lambda *args, **kwargs: None,
    ):
        return build_cell_index(matrix)


def _stored_hits(index):
    for tier in ("decoded", "fp_bytehash", "bytehash"):
        yield from (
            (tier, key, hit) for key, hit in getattr(index, tier).items()
        )
    yield from (("norm_fp", k, h) for k, h in index.norm_fp.refs.items())


def _shape(name):
    from . import merged_group_shapes as shapes

    return getattr(shapes, name)()


class TestAMergedGroup:

    @pytest.mark.parametrize("build", [
        lambda: _shape("daikin_dry"),
        lambda: _shape("shape_1128"),
        lambda: _shape("shape_duplicate_coordinate"),
        lambda: _pack_matrix("MITSUBISHI144.json"),
        lambda: _pack_matrix("TCL112.json"),
    ])
    def test_every_key_still_resolves_the_cell_it_did(self, build):
        """The representative stays: same key set, same cell key,
        coordinates and S/L pattern under every key, and the same number
        of distinct stored hits, so the row count on disk does not move.
        Only the name and the two new fields differ."""
        from custom_components.hair.matrix_listener import _index_to_payload

        matrix = build()
        before = _without_groups(matrix)
        after = build_cell_index(matrix)

        old = {(t, k): h for t, k, h in _stored_hits(before)}
        new = {(t, k): h for t, k, h in _stored_hits(after)}
        assert old.keys() == new.keys()
        for key, hit in old.items():
            twin = new[key]
            assert (twin.cell_key, twin.power, twin.mode, twin.fan,
                    twin.swing, twin.temp, twin.sl_pattern, twin.axis,
                    twin.lattice) == (
                hit.cell_key, hit.power, hit.mode, hit.fan, hit.swing,
                hit.temp, hit.sl_pattern, hit.axis, hit.lattice,
            )
            assert (twin.spanned == ()) == (twin.cell_name == hit.cell_name)
        assert len(_index_to_payload(after, "h", "C")["hits"]) == len(
            _index_to_payload(before, "h", "C")["hits"]
        )

    def test_a_dry_group_is_named_by_what_it_spans(self):
        index = build_cell_index(_shape("daikin_dry"))
        dry = [h for _t, _k, h in _stored_hits(index) if h.mode == "dry"]

        assert dry
        for hit in dry:
            assert hit.cell_key == f"dry/{hit.fan}/off/30"
            assert hit.spanned == (
                ("temp", tuple(float(t) for t in range(18, 31))),
            )
            assert hit.cell_name == f"dry / fan: {hit.fan} / swing: off / 18-30"
            assert hit.members == tuple(
                ("dry", hit.fan, "off", float(t)) for t in range(18, 31)
            )

    def test_one_group_shares_one_members_tuple(self):
        index = build_cell_index(_shape("daikin_dry"))
        auto = [
            h for _t, _k, h in _stored_hits(index)
            if h.mode == "dry" and h.fan == "auto"
        ]
        assert len({id(h.members) for h in auto}) == 1
        groups = {id(g): g for g in index.groups.values()}
        assert len(groups) == 2
        assert any(auto[0].members is g.members for g in groups.values())

    def test_a_group_records_the_branches_it_wholly_covers(self):
        index = build_cell_index(_shape("daikin_dry"))
        branches = {
            branch for g in index.groups.values() for branch in g.full_branches
        }
        assert branches == {("dry", "auto", "off"), ("dry", "high", "off")}

    def test_a_partial_group_covers_no_branch(self):
        index = build_cell_index(_shape("shape_1000"))
        (group,) = {id(g): g for g in index.groups.values()}.values()
        assert group.members == (
            ("heat", "high", None, 18.0), ("heat", "high", None, 19.0),
        )
        assert group.full_branches == frozenset()

    def test_a_twin_of_another_code_is_not_named_for_the_group(self):
        """Two cells at dry / auto / off / 24, different codes. The other
        code's hit is found by the code it claimed under, never by its
        coordinates, so it keeps its own concrete name; and its cell
        breaks the branch, so the dry auto branch is not wholly one
        code."""
        matrix = _shape("shape_duplicate_coordinate")
        twin = matrix.cells[next(
            i for i, c in enumerate(matrix.cells)
            if (c.mode, c.fan, c.temp) == ("dry", "auto", 24.0)
        )]
        index = build_cell_index(matrix)
        identity = wig_signal_identity(twin.pronto)
        hit = index.bytehash[identity.byte_hash]

        assert hit.cell_key == "dry/auto/off/24"
        assert hit.spanned == ()
        assert hit.cell_name == "dry / fan: auto / swing: off / 24"
        auto = next(
            g for g in index.groups.values() if g.members[0][1] == "auto"
        )
        assert ("dry", "auto", "off") not in auto.full_branches

    def test_a_capture_built_group_keeps_each_keys_representative(self):
        """Each capture of one code is its own S/L fingerprint, so the
        composite key stores a different representative per capture
        while the byte hash stores the last. Each key keeps its own,
        live and after a restart, and all of them name the one group."""
        from .test_matrix_listener import _stored

        index = build_cell_index(_shape("shape_1128"))
        dry = [(t, k, h) for t, k, h in _stored_hits(index) if h.mode == "dry"]
        representatives = {h.cell_key for _t, _k, h in dry}
        assert len(representatives) > 1
        assert {h.cell_name for _t, _k, h in dry} == {
            "dry / fan: level1 / 16-31",
        }
        restored = _stored(index)
        for tier, key, hit in dry:
            twin = (
                restored.norm_fp.refs[key] if tier == "norm_fp"
                else getattr(restored, tier)[key]
            )
            assert twin == hit
        (group,) = {id(g): g for g in restored.groups.values()}.values()
        assert len(group.digests) > 1

    def test_a_cell_spelled_with_the_off_bytes_is_no_group(self):
        """Malformed, and the safer answer is the one it always got: the
        key answers Off, and nothing is named for a group."""
        index = build_cell_index(_toy([
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_OFF),
            ClimateCell(mode="cool", fan="auto", temp=23.0, pronto=_OFF),
            ClimateCell(mode="cool", fan="auto", temp=24.0, pronto=_A),
        ], off=_OFF))

        assert index.groups == {}
        assert all(h.spanned == () for _t, _k, h in _stored_hits(index))
        assert _match(index, _OFF)[1] == "off"
        names = {h.cell_name for _t, _k, h in _stored_hits(index)}
        assert names == {"Off", "cool / fan: auto / 24"}

    def test_a_code_shared_across_lattices_is_grouped_in_its_own_only(self):
        """An extra holding a main cell's code is a coincidence between
        two lattices, not a setting the unit ignores. The stored hit is
        the extra's (it is added last, as today), and what it spans is
        its own lattice's group alone."""
        from custom_components.hair.wig_format import ClimateExtra

        matrix = _toy([
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A),
            ClimateCell(mode="cool", fan="auto", temp=26.0, pronto=_B),
        ], off=_OFF)
        matrix.extras = [ClimateExtra(axis="preset", key="eco", cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A),
            ClimateCell(mode="cool", fan="auto", temp=23.0, pronto=_A),
        ])]
        index = build_cell_index(matrix)
        identity = wig_signal_identity(_A)
        hit = index.bytehash[identity.byte_hash]

        assert (hit.lattice, hit.cell_key) == ("eco", "cool/auto/23")
        assert hit.spanned == (("temp", (22.0, 23.0)),)
        assert hit.members == (
            ("cool", "auto", None, 22.0), ("cool", "auto", None, 23.0),
        )
        assert hit.cell_name == "(eco) cool / fan: auto / 22-23"
        assert {g.lattice for g in index.groups.values()} == {
            ("preset", "eco"),
        }

    def test_a_pair_across_lattices_alone_is_no_group(self):
        from custom_components.hair.wig_format import ClimateExtra

        matrix = _toy([
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A),
        ], off=_OFF)
        matrix.extras = [ClimateExtra(axis="preset", key="eco", cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=_A),
        ])]
        index = build_cell_index(matrix)

        assert index.groups == {}
        assert all(h.spanned == () for _t, _k, h in _stored_hits(index))

    def test_a_code_stored_under_two_modes_names_both(self):
        from . import merged_group_shapes as shapes

        index = build_cell_index(shapes.wig_matrix(shapes.KOMECO_WIGS[1]))
        names = {
            h.cell_name for _t, _k, h in _stored_hits(index)
            if dict(h.spanned).get("mode")
        }
        assert names == {
            f"cool|heat_cool / fan: medium / swing: {s} / 25"
            for s in ("off", "vertical", "horizontal", "both")
        }

    def test_fujitsu_stores_every_branch_as_one_code(self):
        """The consequence stated in the report, pinned so it is seen
        when the Fujitsu map changes it: every branch of the pack is one
        code across temperature, so a Fujitsu card does not move its
        temperature on a heard press until the map is fixed."""
        index = build_cell_index(_pack_matrix("FUJITSU128.json"))
        groups = {id(g): g for g in index.groups.values()}.values()
        assert len(groups) == 20
        for group in groups:
            assert {m[:3] for m in group.members} == set(group.full_branches)
            assert len(group.full_branches) == 1
