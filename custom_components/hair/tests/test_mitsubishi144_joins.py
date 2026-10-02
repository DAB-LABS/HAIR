"""MITSUBISHI144 joins both identity lists.

The first family to join settings-based identity through the general
machinery rather than Daikin-specific code. Listing a family re-keys
everything it owns at once: its byte hash becomes the read key, its S/L
fingerprint narrows to the setting frame, and its whole-code
discriminator's frame identity becomes the read key. What that does,
pinned here:

- The former blocker is the merged group: a dry or fan_only press is
  one code under every temperature label of its branch, and it is heard
  as the group, named for what it pins down, with a pinned card keeping
  its temperature, as the Daikins have it.
- The pack has no fan_only and no power codes, so those cases are built
  with the measurement pass's encoder (``test_mitsubishi144_pass``).
- A STRAY BURST IS NOT AN IDENTITY. Several of the family's files open
  codes with one stray mark and about 50 ms of silence; a damaged cell
  left as the only claimant of that one-word key would be heard for any
  glitched capture with the same lead-in, and its code sent. The index
  claims no plain-tier key for such a code, nor, for a cell whose code
  forms no read key, a key its family left behind when it moved to
  read keys.
- ACROSS A LIST CHANGE, "THE SAME CELL" IS "A CELL CARRYING THE SAME
  DECODED BYTES" (owner ruling 2026-10-02). On a file built from
  captures, two captures of one setting whose second frames differ in
  a space the S/L threshold splits had two composite keys; listed, the
  S/L pattern covers the setting frame only, they share one, and its
  last claimant answers: a press may be named for the other capture of
  the same setting, and a same-file device sent that capture's text.
- The stores carry across: commands and triggers learned on the timing
  hash keep matching after the load-time backfill, a trigger learned
  from one press now fires on every press of that setting, Sniffer rows
  of one setting merge keeping every name, and a stored index built
  under the old digest is rebuilt.

Every code here is synthetic, a committed fixture (the field pack, the
bench's air-path captures, the Flipper export), or built from them.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACMode

import custom_components.hair.identity as idm
from custom_components.hair import matrix_listener as _ml
from custom_components.hair.event_parser import EventParser
from custom_components.hair.field_readers import library
from custom_components.hair.identity import TIER_BYTE_HASH
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_climate import cell_display_name
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, cell_key
from custom_components.hair.wig_identity import wig_signal_identity

from . import merged_group_shapes as shapes
from .merged_group_shapes import PinnedBench, map_split, press_identity
from .test_identity_round import _flipper_presses, _unlisted
from .test_merged_group_dial import _cell, _pair
from .test_mitsubishi144_pass import F_TABLE, _frame, _pronto
from .test_read_bytes_identity import _air

MAPS = {m.protocol_id: m for m in library()}
GAP = MAPS["MITSUBISHI144"].timing.gap_min
_SHIPPED = (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED)


@pytest.fixture(autouse=True)
def _the_lists_are_the_shipped_ones():
    assert (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED) == _SHIPPED
    yield
    assert (idm.READ_BYTES_VERIFIED, idm.SETTING_IDENTITY_VERIFIED) == _SHIPPED


def _coords(cell) -> tuple:
    return (cell.mode, cell.fan, cell.swing, cell.temp)


def _presses(pronto: str) -> list[str]:
    """The file code, and an ESPHome and a Broadlink press off the air,
    each whole and split at the map's gap. A piece of a value or two
    between the frames (the Broadlink model leaves one) is left out:
    the capture path drops such a fragment before identity is asked."""
    out = [pronto]
    for transmitter in ("esphome", "broadlink"):
        heard, _glitched = _air(pronto, 0, transmitter)
        out += [heard, *(
            piece for piece in map_split(heard, GAP)
            if len(piece.split()) - 4 >= 16
        )]
    return out


def _heard(index, pronto: str):
    identity = press_identity(pronto)
    return None if identity is None else index.match(*identity)


def _lattice(cells, *, off=None) -> ClimateMatrix:
    return shapes._matrix(
        cells, modes=list(dict.fromkeys(c.mode for c in cells)),
        off=off or _pronto(_frame("cool", 24, power=False)),
    )


def _encoded(mode, fan, vane, label, frame) -> ClimateCell:
    return ClimateCell(mode=mode, fan=fan, swing=vane, temp=float(label),
                       pronto=_pronto(frame))


def _fan_only_lattice() -> ClimateMatrix:
    """Built with the pass's encoder, since the pack has no fan_only:
    cool and auto a code per temperature, fan_only and dry one code per
    fan across every temperature, as the family's files store them."""
    temps = (18, 22, 26, 30)
    cells = []
    for fan in ("auto", "low"):
        cells += [_encoded("cool", fan, "auto", t, _frame("cool", t, fan))
                  for t in temps]
    cells += [_encoded("auto", "auto", "auto", t, _frame("auto", t))
              for t in temps]
    for fan in ("auto", "low", "high"):
        cells += [_encoded("fan_only", fan, "auto", t,
                           _frame("fan_only", 24, fan)) for t in temps]
    cells += [_encoded("dry", "low", "auto", t, _frame("dry", 24, "low"))
              for t in temps]
    return _lattice(cells)


# ---------------------------------------------------------------------------
# 1. The former blocker is the merged group
# ---------------------------------------------------------------------------


class TestAFrozenModeIsHeardAsItsGroup:

    def test_every_dry_press_of_the_pack_finds_its_group(self):
        """The pack stores dry once per fan and swing across 16-31.
        Every dry press, file code and air, whole and split, is heard as
        the group of its branch, carries the pressed cell among its
        members and is named for the temperatures it could be."""
        matrix = shapes.pack_matrix("MITSUBISHI144.json")
        index = build_cell_index(matrix)
        dry = [c for c in matrix.cells if c.mode == "dry"]
        assert len(dry) == 80
        names = {cell_display_name(c) for c in matrix.cells}
        heard = 0
        for cell in dry:
            for press in _presses(cell.pronto):
                hit, _tier = _heard(index, press)
                assert _coords(cell) in hit.members
                assert hit.spanned == (
                    ("temp", (16.0, 20.0, 24.0, 28.0, 31.0)),
                )
                assert hit.cell_name == (
                    f"dry / fan: {cell.fan} / swing: {cell.swing}"
                    " / 16|20|24|28|31"
                )
                assert hit.cell_name not in names
                heard += 1
        assert heard == 80 * 7

    def test_fan_only_reads_as_itself_and_is_heard_as_its_group(self):
        """Under the old mode mask fan_only read as cool, so a fan_only
        press could only collide with a cool one. Now every fan_only
        press is heard as its own fan's group, never as cool, and every
        cool and auto press as its own cell."""
        matrix = _fan_only_lattice()
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            for press in _presses(cell.pronto):
                hit, tier = _heard(index, press)
                assert tier == TIER_BYTE_HASH
                assert hit.mode == cell.mode
                if cell.mode in ("cool", "auto"):
                    assert hit.cell_key == cell_key(cell)
                    assert not hit.spanned
                else:
                    assert hit.fan == cell.fan
                    assert _coords(cell) in hit.members
                    assert hit.spanned == (
                        ("temp", (18.0, 22.0, 26.0, 30.0)),
                    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("from_disk", [False, True])
    async def test_a_dry_press_keeps_the_dial_and_the_next_cool_goes_out_there(
        self, from_disk, tmp_path,
    ):
        """The #183 case on this family: the card stays at 24, the
        send is named for the sibling at 24, and the next cool from Home
        Assistant goes out at 24."""
        matrix = shapes.pack_matrix("MITSUBISHI144.json")
        pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
        pair.card(HVACMode.COOL, "auto", "auto", 24.0)

        sent = await pair.press(_cell(matrix, "dry", "auto", "auto", 20).pronto)

        heard = pair.remote.last_heard
        representative = _cell(
            matrix, heard["mode"], heard["fan"], heard["swing"], heard["temp"],
        )
        assert (sent.pronto, sent.send_count) == (
            representative.pronto, representative.send_count,
        )
        assert sent.name == cell_display_name(
            _cell(matrix, "dry", "auto", "auto", 24)
        )
        entity = pair.entity
        assert entity.hvac_mode == HVACMode.DRY
        assert (entity.fan_mode, entity.swing_mode,
                entity.target_temperature) == ("auto", "auto", 24.0)

        await entity.async_set_hvac_mode(HVACMode.COOL)
        own = pair.manager.sends[-1]
        assert own.pronto == _cell(matrix, "cool", "auto", "auto", 24).pronto

    @pytest.mark.asyncio
    @pytest.mark.parametrize("from_disk", [False, True])
    async def test_a_dial_between_the_dry_labels_stays_put(
        self, from_disk, tmp_path,
    ):
        """22 is no dry label of the pack. The branch is wholly one
        code, so the unit ignores temperature there: the dial stays at
        22 and the send is named as the set it could be."""
        matrix = shapes.pack_matrix("MITSUBISHI144.json")
        pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
        pair.card(HVACMode.COOL, "auto", "auto", 22.0)

        sent = await pair.press(_cell(matrix, "dry", "auto", "auto", 20).pronto)

        assert sent.cell["temp_free"] is True
        assert sent.name == "dry / fan: auto / swing: auto / 16|20|24|28|31"
        assert pair.entity.hvac_mode == HVACMode.DRY
        assert pair.entity.target_temperature == 22.0

    @pytest.mark.asyncio
    async def test_a_fan_only_press_keeps_the_dial(self):
        matrix = _fan_only_lattice()
        pair = await _pair(matrix)
        pair.card(HVACMode.COOL, "low", "auto", 26.0)

        sent = await pair.press(
            _cell(matrix, "fan_only", "low", "auto", 18).pronto
        )

        assert sent.cell["temp_free"] is True
        entity = pair.entity
        assert entity.hvac_mode == HVACMode.FAN_ONLY
        assert (entity.fan_mode, entity.target_temperature) == ("low", 26.0)
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert pair.manager.sends[-1].pronto == (
            _cell(matrix, "cool", "low", "auto", 26).pronto
        )


# ---------------------------------------------------------------------------
# 2. The power codes the pack does not have
# ---------------------------------------------------------------------------


def test_an_off_has_a_key_of_its_own_and_is_heard_as_off():
    """``test_read_bytes_identity``'s power-code pin passes without
    testing anything for this family (its pack has no power codes), so
    here is an Off from the encoder: its read key is no cell's, and the
    index hears it, whole and split, as Off."""
    matrix = _fan_only_lattice()
    off = matrix.off
    key = EventParser.pronto_read_key(off)
    assert key is not None
    assert key not in {
        EventParser.pronto_read_key(c.pronto) for c in matrix.cells
    }
    index = build_cell_index(matrix)
    for press in _presses(off):
        hit, _tier = _heard(index, press)
        assert hit.power == "off"


# ---------------------------------------------------------------------------
# 3. A stray burst is not an identity
# ---------------------------------------------------------------------------

#: The lead-in several of the family's files (SmartIR 1142 and 1124 as
#: HAIR adopts them) open codes with: one 8-cycle mark, about 210 us,
#: then a 0x768-cycle space, about 50 ms, over the Pronto gap threshold.
_LEAD = ["0008", "0768"]


def _with_lead(pronto: str, drop_tail: int = 0) -> str:
    """``pronto`` opened with ``_LEAD``; with its last ``drop_tail``
    words cut off when asked, which damages the second frame so the code
    does not read: a capture-damaged cell."""
    words = pronto.split()
    body = words[4:]
    if drop_tail:
        body = body[:-drop_tail]
    body = _LEAD + body
    return " ".join([*words[:2], f"{len(body) // 2:04X}", "0000", *body])


def _glitched(pronto: str) -> str:
    """The press with one payload mark cut to 2 cycles (about 50 us):
    the read refuses it, as it refuses a press the air broke."""
    words = pronto.split()
    words[4 + 2 + 2 + 40] = "0002"
    return " ".join(words)


def _lead_in_pack_lattice() -> list[ClimateCell]:
    """Five cool cells of the pack with the lead-in, and a heat cell
    with the lead-in and a damaged frame."""
    pack = shapes.pack_matrix("MITSUBISHI144.json")
    cells = [
        ClimateCell(mode=c.mode, fan=c.fan, swing=c.swing, temp=c.temp,
                    pronto=_with_lead(c.pronto))
        for c in [c for c in pack.cells if c.mode == "cool"][:5]
    ]
    heat = next(c for c in pack.cells if c.mode == "heat")
    cells.append(ClimateCell(
        mode=heat.mode, fan=heat.fan, swing=heat.swing, temp=heat.temp,
        pronto=_with_lead(heat.pronto, drop_tail=40),
    ))
    return cells


def _1142_shaped() -> list[ClimateCell]:
    """SmartIR 1142's shape: Fahrenheit labels, every code opened with
    the lead-in, cool and heat across three vanes, and one heat cell
    whose code is damaged (heat / auto / mid / 71)."""
    cells = []
    for mode in ("cool", "heat"):
        for vane in ("auto", "high", "low"):
            cells += [
                ClimateCell(
                    mode=mode, fan="auto", swing=vane, temp=float(label),
                    pronto=_with_lead(_pronto(
                        _frame(mode, F_TABLE[label], "auto", vane)
                    )),
                )
                for label in (66, 67, 68, 69, 70)
            ]
    cells.append(ClimateCell(
        mode="heat", fan="auto", swing="mid", temp=71.0,
        pronto=_with_lead(
            _pronto(_frame("heat", F_TABLE[71], "auto", "mid")),
            drop_tail=40,
        ),
    ))
    return cells


def _no_glitch_is_heard_as_the_damaged_cell(cells: list[ClimateCell]):
    """Both lattice orders: every glitched press of a readable cell is
    heard as nothing or as its own cell, never as the damaged one, and a
    same-file device is never sent the damaged cell's code."""
    damaged = cells[-1]
    assert EventParser.pronto_read_key(damaged.pronto) is None
    stray = wig_signal_identity(damaged.pronto)
    for order in (cells, cells[::-1]):
        matrix = _lattice(order)
        index = build_cell_index(matrix)
        assert stray.byte_hash not in index.bytehash
        assert (stray.fingerprint, stray.byte_hash) not in index.fp_bytehash
        bench = PinnedBench(matrix, matrix, index, index)
        presses = 0
        for cell in cells[:-1]:
            assert EventParser.pronto_read_key(cell.pronto) is not None
            assert bench.hear(cell.pronto)[0].cell_key == cell_key(cell)
            broken_air, glitched = _air(cell.pronto, 3, "broadlink")
            assert glitched
            for press in (_glitched(cell.pronto), broken_air):
                assert EventParser.pronto_read_key(press) is None
                # Whatever the stray key's lone claimant would have
                # answered: the same one-word identity.
                assert wig_signal_identity(press).byte_hash == stray.byte_hash
                heard = bench.hear(press)
                if heard is not None:
                    assert heard[0].cell_key == cell_key(cell)
                presses += 1
        assert presses == 2 * (len(cells) - 1)


@pytest.mark.asyncio
async def test_the_stray_key_is_not_left_to_a_damaged_cell_pack_built():
    """Five cool cells of the pack with the lead-in and one heat cell
    with the lead-in and a damaged frame. Unlisted, all six claimed the
    lead-in's one-word key with different codes and it answered nothing.
    Listed, the five that read move to their read keys; without the
    guards the damaged heat cell was left as the key's only claimant,
    and every glitched cool press was heard as heat and its code sent."""
    cells = _lead_in_pack_lattice()
    _no_glitch_is_heard_as_the_damaged_cell(cells)
    matrix = _lattice(cells)
    bench = PinnedBench(matrix, matrix)
    for cell in cells[:-1]:
        heard = bench.hear(_glitched(cell.pronto))
        sent = await bench.resolve(heard)
        assert sent is None or sent[1] != cells[-1].pronto


def test_the_stray_key_is_not_left_to_a_damaged_cell_1142_shaped():
    _no_glitch_is_heard_as_the_damaged_cell(_1142_shaped())


def test_either_guard_alone_closes_it_on_a_listed_lattice(monkeypatch):
    """With the stray-burst floor switched off, the second guard still
    keeps the damaged cell, a cell of a listed family whose code forms
    no read key, off every plain-tier key."""
    monkeypatch.setattr(_ml, "_stray_burst", lambda *args: False)
    _no_glitch_is_heard_as_the_damaged_cell(_lead_in_pack_lattice())


def test_the_floor_closes_a_live_stray_key_on_an_unlisted_lattice(
    monkeypatch,
):
    """Where it was live before the family joined: an unlisted lattice
    in which one cell alone carries the lead-in owns the one-word key,
    so any capture that opens with that mark was heard as that cell
    (SmartIR 1133's cool / High / Swing / 27 is one of seven such keys
    in five of the family's files). The floor removes the key; switched
    off, the lone cell answers the stray mark again."""
    pack = shapes.pack_matrix("MITSUBISHI144.json")
    cool = [c for c in pack.cells if c.mode == "cool"][:5]
    cells = [
        ClimateCell(mode=c.mode, fan=c.fan, swing=c.swing, temp=c.temp,
                    pronto=c.pronto)
        for c in cool[1:]
    ]
    cells.append(ClimateCell(
        mode=cool[0].mode, fan=cool[0].fan, swing=cool[0].swing,
        temp=cool[0].temp, pronto=_with_lead(cool[0].pronto),
    ))
    stray = _with_lead(_glitched(cool[1].pronto))
    with _unlisted("MITSUBISHI144"):
        matrix = _lattice(cells)
        assert _heard(build_cell_index(matrix), stray) is None
        monkeypatch.setattr(_ml, "_stray_burst", lambda *args: False)
        hit, tier = _heard(build_cell_index(matrix), stray)
        assert (hit.cell_key, tier) == (cell_key(cells[-1]), TIER_BYTE_HASH)


def test_a_code_short_as_a_whole_is_its_own_identity():
    """The floor is for a lead-in ahead of more code. The tests' two-pair
    lattices, short as a whole, keep every key they had."""
    words = EventParser._parse_pronto_words
    timings = EventParser._pronto_identity_timings
    toy = "0000 006D 0002 0000 0020 0040 0020 0040"
    assert not _ml._stray_burst(words(toy), timings(toy))
    code = _pronto(_frame())
    assert not _ml._stray_burst(words(code), timings(code))
    with _unlisted("MITSUBISHI144"):
        lead = _with_lead(code)
        assert len(timings(lead)) == 1
        assert _ml._stray_burst(words(lead), timings(lead))


def test_a_listed_cell_that_does_not_read_keeps_a_key_of_its_own():
    """A damaged cell of a listed family with no lead-in: its timing key
    covers its whole code, no code that reads would claim it, so it
    keeps it, and its own text is heard as it on the byte-hash tier, as
    before the family joined."""
    pack = shapes.pack_matrix("MITSUBISHI144.json")
    cool = [c for c in pack.cells if c.mode == "cool"][:5]
    words = cool[0].pronto.split()
    body = words[4:-40]
    damaged = " ".join([*words[:2], f"{len(body) // 2:04X}", "0000", *body])
    cells = [
        ClimateCell(mode=c.mode, fan=c.fan, swing=c.swing, temp=c.temp,
                    pronto=c.pronto)
        for c in cool[1:]
    ]
    cells.append(ClimateCell(mode="heat", fan="auto", swing="auto",
                             temp=22.0, pronto=damaged))
    matrix = _lattice(cells)
    assert EventParser.pronto_read_key(damaged) is None
    for lists in (_unlisted("MITSUBISHI144"), _unlisted()):
        with lists:
            identity = wig_signal_identity(damaged)
            index = build_cell_index(matrix)
            assert identity.byte_hash in index.bytehash
            hit, tier = _heard(index, damaged)
            assert (hit.cell_key, tier) == ("heat/auto/auto/22", TIER_BYTE_HASH)


def test_a_cell_left_alone_on_a_key_its_family_left_behind_claims_none(
    monkeypatch,
):
    """Every DAIKIN216 code opens with the same preamble frame, and the
    identity walk stops at the gap after it, so unlisted every code's
    timing key was the preamble's. Listed, the codes that read moved to
    their read keys, and a damaged cell, whose code does not read, is
    the preamble key's only claimant: a DAIKIN216 press that fails the
    read reaches it on the byte-hash tiers. That key is one the readable
    codes left behind, so the cell claims none; with the guard switched
    off it does again. (Such a press still reaches the damaged cell on
    the normalized tier, whose fingerprint for this family is taken over
    the preamble too: outside this guard, which is the plain tiers', and
    the same before and after; a follow-up.)"""
    from . import test_read_bytes_identity as d216

    def broken(temp_byte: int) -> str:
        """A capture whose settings frame broke off: it neither reads
        nor yields a settings frame, so its identity walk stops at the
        gap after the preamble."""
        words = d216._code(d216._settings(temp_byte=temp_byte)).split()
        body = words[4:-40]
        return " ".join([*words[:2], f"{len(body) // 2:04X}", "0000", *body])

    cells = [
        ClimateCell(mode="cool", fan="low", temp=float(18 + n),
                    pronto=d216._code(d216._settings(temp_byte=0x24 + 2 * n)))
        for n in range(4)
    ]
    cells.append(ClimateCell(mode="heat", fan="low", temp=22.0,
                             pronto=broken(0x2C)))
    matrix = shapes._matrix(cells, modes=["cool", "heat"],
                            off=d216._code(d216._settings(mode_power=0x30)))
    damaged = wig_signal_identity(cells[-1].pronto)
    assert EventParser.pronto_read_key(cells[-1].pronto) is None
    assert damaged.byte_hash == _ml._timing_key(
        EventParser._parse_pronto_words(cells[0].pronto)
    )
    press = wig_signal_identity(broken(0x30))
    assert press.byte_hash == damaged.byte_hash

    def plain_keys(index) -> set:
        return {
            tier for tier, key in (
                ("bytehash", press.byte_hash),
                ("fp_bytehash", (press.fingerprint, press.byte_hash)),
            ) if key in getattr(index, tier)
        }

    index = build_cell_index(matrix)
    assert plain_keys(index) == set()
    for cell in cells[:-1]:
        hit, tier = _heard(index, cell.pronto)
        assert (hit.cell_key, tier) == (cell_key(cell), TIER_BYTE_HASH)
    monkeypatch.setattr(_ml, "_timing_key", lambda words: None)
    assert plain_keys(build_cell_index(matrix)) == {"bytehash", "fp_bytehash"}


@pytest.mark.parametrize(
    "family", ["MITSUBISHI144", "DAIKIN216", "DAIKIN152", "GREE"],
)
def test_the_timing_key_is_the_byte_hash_of_an_unlisted_family(family):
    """``_timing_key`` mirrors the walk ``EventParser.pronto_byte_hash``
    takes for a family on neither list; this keeps the two from
    drifting apart."""
    cells = shapes.pack_matrix(f"{family}.json").cells[::7]
    with _unlisted(family):
        for cell in cells:
            canonical = wig_signal_identity(cell.pronto).pronto
            assert _ml._timing_key(
                EventParser._parse_pronto_words(canonical)
            ) == EventParser.pronto_byte_hash(canonical), cell_key(cell)


# ---------------------------------------------------------------------------
# 4. Across the list change, the same cell is a cell of the same bytes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_captures_of_one_setting_answer_as_the_later_one():
    """Owner ruling 2026-10-02, pinned as the documented behaviour.
    dry / 16 and dry / 17 hold two captures of one setting whose second
    frames differ in a one-space on the S/L threshold. Unlisted, each
    owned its composite key and 16's text was heard as 16. Listed, they
    share it and its last claimant answers: 16's text is heard as 17 and
    a same-file device is sent 17's text, the same decoded bytes. A
    press of 17's text is unchanged."""
    matrix = shapes.shape_mitsubishi144_sl_scope()
    first = _cell(matrix, "dry", "auto", "auto", 16).pronto
    second = _cell(matrix, "dry", "auto", "auto", 17).pronto
    assert first != second
    assert EventParser.pronto_read_key(first) == (
        EventParser.pronto_read_key(second)
    )
    index = build_cell_index(matrix)
    bench = PinnedBench(matrix, matrix, index, index)
    for press in (first, second):
        heard = bench.hear(press)
        assert heard[0].cell_key == "dry/auto/auto/17"
        assert (await bench.resolve(heard))[1] == second
    with _unlisted("MITSUBISHI144"):
        index = build_cell_index(matrix)
        bench = PinnedBench(matrix, matrix, index, index)
        for press, cell in ((first, "dry/auto/auto/16"),
                            (second, "dry/auto/auto/17")):
            heard = bench.hear(press)
            assert heard[0].cell_key == cell
            assert (await bench.resolve(heard))[1] == press


@pytest.mark.asyncio
async def test_the_dial_stays_on_a_cell_of_the_same_bytes():
    """The same press through the listener and the climate entity: 17's
    text goes out, named as the group, and the card at 16 stays on dry
    / 16, a member of the group that carries the same bytes."""
    matrix = shapes.shape_mitsubishi144_sl_scope()
    pair = await _pair(matrix)
    pair.card(HVACMode.COOL, "auto", "auto", 16.0)

    sent = await pair.press(_cell(matrix, "dry", "auto", "auto", 16).pronto)

    assert sent.pronto == _cell(matrix, "dry", "auto", "auto", 17).pronto
    assert sent.name == "dry / fan: auto / swing: auto / 16-17"
    entity = pair.entity
    assert (entity.hvac_mode, entity.fan_mode, entity.swing_mode,
            entity.target_temperature) == (HVACMode.DRY, "auto", "auto", 16.0)
    assert pair.remote.last_heard["cell_key"] == "dry/auto/auto/17"


# ---------------------------------------------------------------------------
# 5. What the stores carry across
# ---------------------------------------------------------------------------


def _signal(pronto: str):
    """One capture, normalized as the Sniffer normalizes it, on the
    lists in force when it is called."""
    from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
    from custom_components.hair.models import CaptureResult
    from custom_components.hair.signal_monitor import normalize

    raw = ProntoCommand(pronto).get_raw_timings()
    return normalize(CaptureResult(
        protocol="PRONTO", code=raw_to_pronto(raw, frequency=38000),
        raw_timings=raw, frequency=38000,
    ))


def test_sniffer_rows_of_one_setting_merge_keeping_every_name():
    """A catalog remote sniffed before the family joined: one press
    whole and as its two lone frames, the same setting pressed later
    with another clock byte, and a second setting, five rows and four
    names. The load re-keys them and the heal collapses the four rows of
    one setting into the oldest; every name the owner gave is kept on
    it. Loaded on the old lists, nothing moves."""
    from custom_components.hair import signal_store
    from custom_components.hair.models import UnknownDevice, UnknownSignal

    def row(pronto, alias):
        signal = _signal(pronto)
        return UnknownSignal(
            fingerprint=signal.sig_fp, byte_hash=signal.byte_hash,
            decoded_fingerprint=signal.decoded_fingerprint,
            protocol="PRONTO", code=signal.code,
            raw_timings=list(signal.raw_timings), hit_count=3, alias=alias,
        )

    with _unlisted("MITSUBISHI144"):
        whole, _ = _air(_pronto(_frame("cool", 24, clock=0x10)), 0, "esphome")
        first, second = map_split(whole, GAP)
        later, _ = _air(_pronto(_frame("cool", 24, clock=0x11)), 1, "esphome")
        other, _ = _air(_pronto(_frame("heat", 22)), 0, "esphome")
        device = UnknownDevice(fingerprint="x", label="Handset", signals=[
            row(whole, "Cool 24"), row(first, "Cool 24 (frame)"),
            row(second, ""), row(later, "Cool 24 evening"),
            row(other, "Heat 22"),
        ])
        raw = json.loads(json.dumps(
            {"devices": [device.to_dict()], "dismissed": []}
        ))
        devices, _dismissed, dirty = signal_store._transform_loaded(
            json.loads(json.dumps(raw))
        )
        assert not dirty
        (kept,) = devices.values()
        assert len(kept.signals) == 5

    devices, _dismissed, dirty = signal_store._transform_loaded(raw)
    assert dirty
    (kept,) = devices.values()
    assert [(s.alias, s.hit_count) for s in kept.signals] == [
        ("Cool 24 / Cool 24 (frame) / Cool 24 evening", 12),
        ("Heat 22", 3),
    ]


def _backfill_captures() -> dict[str, tuple[str, str]]:
    """``{name: (source code, press)}``: the bench's real C1 and C2
    captures, the Flipper POWER and Off presses whole and halved at the
    map's gap, and three pack cells' file codes and air presses whole
    and split (none of them C1's setting)."""
    from custom_components.hair.ir_command import raw_to_pronto

    from .test_matrix_listener import _air_captures, _air_code

    out: dict[str, tuple[str, str]] = {}
    for code in ("C1", "C2"):
        for n, row in enumerate(_air_captures(code)):
            values = json.loads(row["timings_us"])
            raw = [v if i % 2 == 0 else -abs(v) for i, v in enumerate(values)]
            out[f"{code}:{row['transmitter']}:{n}"] = (
                _air_code(code), raw_to_pronto(raw, frequency=38000),
            )
    for name, press in _flipper_presses().items():
        if name in ("POWER", "Off"):
            out[f"flipper:{name}"] = (press, press)
            for n, half in enumerate(map_split(press, GAP)):
                out[f"flipper:{name}:{n}"] = (press, half)
    pack = shapes.pack_matrix("MITSUBISHI144.json")
    for mode, temp in (("cool", 16.0), ("dry", 16.0), ("heat", 31.0)):
        cell = next(c for c in pack.cells if (c.mode, c.temp) == (mode, temp))
        out[f"{mode}/{temp}"] = (cell.pronto, cell.pronto)
        for transmitter in ("esphome", "broadlink"):
            for k in (0, 1):
                heard, _ = _air(cell.pronto, k, transmitter)
                out[f"{mode}/{temp}:{transmitter}{k}"] = (cell.pronto, heard)
                for n, piece in enumerate(map_split(heard, GAP)):
                    if len(piece.split()) - 4 >= 16:
                        out[f"{mode}/{temp}:{transmitter}{k}.{n}"] = (
                            cell.pronto, piece,
                        )
    return out


def _fires_and_finds(store, signals, rows) -> tuple[set, set]:
    """Every (row, capture) whose trigger fires on the capture, and
    every one whose command the row's own device finds for it."""
    from custom_components.hair.storage import HAIRStore

    fires, finds = set(), set()
    for capture, signal in signals.items():
        for trigger in store.get_triggers_for_signal(
            "PRONTO", signal.code, signal.sig_fp, signal.byte_hash,
            signal.decoded_fingerprint, signal.norm_fp, signal.decode_covers,
        ):
            fires.add((trigger.name, capture))
    for name, (device_id, command_id) in rows.items():
        alone = HAIRStore(MagicMock())
        alone._loaded = True
        alone._data[device_id] = store.get_device(device_id)
        alone._rebuild_command_index()
        for capture, signal in signals.items():
            found = alone.match_command(
                signal.decoded_fingerprint, signal.sig_fp, signal.byte_hash,
                signal.norm_fp,
            )
            if found is not None:
                assert found == (device_id, command_id)
                finds.add((name, capture))
    return fires, finds


@pytest.mark.asyncio
async def test_learned_commands_and_triggers_keep_matching_across_the_backfill():
    """Learned before the family joined, one trigger and one command per
    capture, stored as the store persists them, then loaded on the real
    lists through ``async_load`` and its backfills. Nothing that matched
    stops matching, no capture finds another command, every row of a
    capture that reads moves onto its read key, and the matches gained
    are all between captures of one setting: a trigger learned from one
    press now fires on every press of that setting, a lone frame's on
    the whole press and the reverse."""
    from custom_components.hair.const import CommandCategory
    from custom_components.hair.models import CaptureResult, IRDevice, IRTrigger
    from custom_components.hair.storage import HAIRStore

    captures = _backfill_captures()
    setting = {
        name: EventParser.pronto_read_key(source)
        for name, (source, _press) in captures.items()
    }
    assert None not in setting.values()
    with _unlisted("MITSUBISHI144"):
        signals = {name: _signal(press) for name, (_s, press) in captures.items()}
        store = HAIRStore(MagicMock())
        store._loaded = True
        rows = {}
        for name, signal in signals.items():
            store._triggers[name] = IRTrigger(
                id=name, name=name, signal_fingerprint=signal.sig_fp,
                protocol="PRONTO", code=signal.code,
                byte_hash=signal.byte_hash,
                decoded_fingerprint=signal.decoded_fingerprint,
                trigger_remote_id=None, origin="remote",
            )
            command = CaptureResult(
                protocol="PRONTO", code=signal.code,
                raw_timings=list(signal.raw_timings), frequency=38000,
            ).to_command(name, CommandCategory.CUSTOM)
            command.signal_fingerprint = signal.sig_fp
            command.byte_hash = signal.byte_hash
            command.decoded_fingerprint = signal.decoded_fingerprint
            device = IRDevice(name=name)
            device.commands.append(command)
            store._data[device.id] = device
            rows[name] = (device.id, command.id)
        before = _fires_and_finds(store, signals, rows)
        stored = json.loads(json.dumps(store._serialize()))

    loaded = HAIRStore(MagicMock())
    loaded._store = MagicMock()
    loaded._store.async_load = AsyncMock(return_value=stored)
    loaded.async_save = AsyncMock()
    await loaded.async_load()
    signals = {name: _signal(press) for name, (_s, press) in captures.items()}
    after = _fires_and_finds(loaded, signals, rows)

    for was, now in zip(before, after, strict=True):
        assert was - now == set()
        gained = now - was
        assert gained
        assert all(setting[row] == setting[capture] for row, capture in gained)
    fires, _finds = after
    assert ("flipper:POWER:0", "flipper:POWER") in fires
    assert ("flipper:POWER", "flipper:POWER:1") in fires
    assert ("flipper:POWER:0", "flipper:POWER") not in before[0]
    moved = 0
    for name, trigger in loaded._triggers.items():
        key = signals[name].byte_hash
        if EventParser.pronto_read_key(captures[name][1]) is not None:
            assert trigger.byte_hash == key
            moved += trigger.byte_hash != stored["triggers"][
                list(rows).index(name)]["byte_hash"]
    assert moved > 0
    assert loaded.async_save.await_count == 1


def test_an_index_stored_under_the_old_digest_is_rebuilt(tmp_path):
    """The map's content and the lists both moved, so ``field_map_digest``
    moved and every stored index rebuilds once at the next boot; the
    format stays ``/10``. A ``/10`` payload stamped with the digest of
    the base (the old map, the family unlisted) or of the pass's map
    alone is refused; the same payload with the current digest loads."""
    from custom_components.hair.matrix_store import (
        load_cell_index,
        write_cell_index,
        write_matrix,
    )

    matrix = shapes.pack_matrix("MITSUBISHI144.json")
    write_matrix(tmp_path, "r1", matrix)
    _ml._build_and_store_index(str(tmp_path), "r1", matrix, "C")
    assert _ml._load_stored_index(str(tmp_path), "r1", "C") is not None
    payload = load_cell_index(tmp_path, "r1")
    assert payload["format"] == _ml.INDEX_FORMAT == "hair-cell-index/10"
    assert payload["maps"] == idm.field_map_digest()
    for old in ("29bdf2fb7ca60ddd", "3e8806340146580d"):
        assert old != idm.field_map_digest()
        payload["maps"] = old
        assert write_cell_index(tmp_path, "r1", payload) is True
        assert _ml._load_stored_index(str(tmp_path), "r1", "C") is None
    payload["maps"] = idm.field_map_digest()
    assert write_cell_index(tmp_path, "r1", payload) is True
    assert _ml._load_stored_index(str(tmp_path), "r1", "C") is not None
