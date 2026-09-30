"""Identity from the bytes the map reads (GH #183).

Setting-frame identity (step 2) hashes the settings frame's TIMINGS, and
a real handset defeats that twice over. The air moves every edge: a
receiver brings marks back short and spaces long, and research doc 22
measured twenty presses of one AC state giving twenty byte hashes, none
the file's. And a handset writes bytes the file did not: the #183
capture reads as the state its wig holds, with timer and clock bits that
differ. For a family on ``identity.READ_BYTES_VERIFIED`` the byte hash
is therefore a hash of what the map READS -- protocol id, declared
identity bytes, each field's raw bits in map order -- after the map's
checksum has been recomputed and found to hold.

Everything here that stands for "the air" is built from doc 22's own
table, not from a symmetric few percent. That is the test the v4 gate
lacked: file codes injected as they are reproduce file identity exactly,
and prove nothing about a receiver.

DAIKIN216 was listed first; DAIKIN152 joined once its map read swing
and the fan flags (2026-09-30). The two share their settings frame byte
for byte, so for them the key belongs to that frame rather than to
either family: ``test_daikin152_joins`` pins that half.
"""
from __future__ import annotations

import dataclasses
import json as _json
import random

import pytest

import custom_components.hair.identity as idm
from custom_components.hair.event_parser import EventParser
from custom_components.hair.field_readers import library, read_code
from custom_components.hair.identity import (
    READ_BYTES_VERIFIED,
    SETTING_IDENTITY_VERIFIED,
    TIER_BYTE_HASH,
    canonical_byte_hash,
    field_map_digest,
    read_bytes_key,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, cell_key
from custom_components.hair.wig_identity import wig_signal_identity

from .test_cell_index_shared_keys import PACKS, _match, _pack_matrix

MAPS = {m.protocol_id: m for m in library()}
D216 = MAPS["DAIKIN216"]


def _timing_hash(code: str) -> str | None:
    """The byte hash this code would have with no family read-keyed:
    step 2's identity, the value the air keeps moving."""
    original = idm.READ_BYTES_VERIFIED
    try:
        idm.READ_BYTES_VERIFIED = frozenset()
        return EventParser.pronto_byte_hash(code)
    finally:
        idm.READ_BYTES_VERIFIED = original


# ---------------------------------------------------------------------------
# A DAIKIN216 code from bytes. Test-local: the reader tier must never
# gain an encoder (test_field_readers).
# ---------------------------------------------------------------------------

_UNIT_US = 0x6D * 0.241246
_GAP_US = 29700      # the pack's own gap between the two frames
_TAIL_US = 80000


def _checksummed(body: list[int]) -> list[int]:
    return [*body, sum(body) & 0xFF]


def _pairs(frames: list[list[int]]) -> list[tuple[float, float]]:
    t = D216.timing
    out: list[tuple[float, float]] = []
    for n, data in enumerate(frames):
        out.append((t.header_mark.nominal, t.header_space.nominal))
        for byte in data:
            for bit in range(8):
                one = (byte >> bit) & 1
                out.append((t.unit.nominal,
                            t.one.nominal if one else t.zero.nominal))
        out.append((t.unit.nominal,
                    _GAP_US if n < len(frames) - 1 else _TAIL_US))
    return out


def _pronto(pairs) -> str:
    words = [0, 0x6D, len(pairs), 0]
    for mark, space in pairs:
        words += [max(1, round(mark / _UNIT_US)),
                  max(1, round(space / _UNIT_US))]
    return " ".join(f"{w:04X}" for w in words)


_FRAME0 = [0x11, 0xDA, 0x27, 0xF0, 0x00, 0x00, 0x00, 0x02]


def _settings(temp_byte=0x24, mode_power=0x31, fan_swing=0x30,
              swing_h=0x00, byte11=0x00, byte13=0x00, byte15=0xC0,
              byte16=0x00) -> list[int]:
    body = [0x11, 0xDA, 0x27, 0x00, 0x00, mode_power, temp_byte, 0x00,
            fan_swing, swing_h, 0x00, byte11, 0x00, byte13, 0x00, byte15,
            byte16, 0x00]
    return _checksummed(body)


def _code(settings: list[int]) -> str:
    return _pronto(_pairs([_FRAME0, settings]))


# ---------------------------------------------------------------------------
# The air, from research doc 22's measured table
# ---------------------------------------------------------------------------
#
# ESPHome: marks came back 0.83 to 0.95 of file length and spaces 1.00
# to 1.12, steady per press (the receiver's signature), with single
# edges reaching 0.71 and 1.27. Applied here to BOTH classes at full
# range, which is harsher than the signature.
#
# Broadlink: its rows already carry its ~7% shrink (mean edge 0.93):
# marks 0.83 to 0.85, spaces 1.00 to 1.05, single edges from 0.47 to
# 1.40. The table does not say which class the extremes land on; the
# photodiode signature (marks short, spaces long) does, so the short
# extreme goes on marks and the long one on spaces. Doc 22 also saw ONE
# Broadlink capture with a glitch edge (0.285, 7.758); the set carries
# two such presses, and for those the only requirement is that no WRONG
# key forms.


def _air(code: str, press: int, transmitter: str) -> tuple[str, bool]:
    """One press of ``code`` as the receiver would hand it over.

    Returns (pronto, glitched). Deterministic per (press, transmitter).
    """
    rng = random.Random(f"{transmitter}:{press}")
    raw = [abs(v) for v in ProntoCommand(code).get_raw_timings()]
    glitched = False
    if transmitter == "esphome":
        mark_f = 0.83 + 0.12 * (press % 5) / 4
        space_f = 1.00 + 0.12 * (press % 4) / 3
        lo = {"mark": 0.71, "space": 0.71}
        hi = {"mark": 1.27, "space": 1.27}
    else:
        mark_f = 0.83 + 0.02 * (press % 3) / 2
        space_f = 1.00 + 0.05 * (press % 4) / 3
        lo = {"mark": 0.47, "space": 0.80}
        hi = {"mark": 1.20, "space": 1.40}
    out: list[float] = []
    for i, value in enumerate(raw):
        cls = "mark" if i % 2 == 0 else "space"
        base = mark_f if cls == "mark" else space_f
        ratio = base * rng.uniform(0.9, 1.1)
        if rng.random() < 0.02:  # the occasional edge at the extreme
            ratio = lo[cls] if rng.random() < 0.5 else hi[cls]
        ratio = min(max(ratio, lo[cls]), hi[cls])
        out.append(value * ratio)
    if transmitter == "broadlink" and press in (3, 7):
        where = rng.randrange(2, len(out) - 2)
        out[where] *= 0.285 if where % 2 == 0 else 7.758
        glitched = True
    signed = [v if i % 2 == 0 else -v for i, v in enumerate(out)]
    return raw_to_pronto([round(v) for v in signed], frequency=38000), glitched


# ---------------------------------------------------------------------------
# The list
# ---------------------------------------------------------------------------


class TestTheList:

    def test_the_two_daikin_families(self):
        assert frozenset({"DAIKIN216", "DAIKIN152"}) == READ_BYTES_VERIFIED

    def test_it_is_inside_the_setting_frame_list(self):
        assert READ_BYTES_VERIFIED <= SETTING_IDENTITY_VERIFIED

    def test_joining_it_moves_the_stored_index_digest(self):
        before = field_map_digest()
        original = idm.READ_BYTES_VERIFIED
        try:
            idm.READ_BYTES_VERIFIED = frozenset({"DAIKIN216"})
            assert field_map_digest() != before
        finally:
            idm.READ_BYTES_VERIFIED = original
        assert field_map_digest() == before


# ---------------------------------------------------------------------------
# The distinctness sweep: what keeps a family on the list
# ---------------------------------------------------------------------------


class TestTheDistinctnessSweep:
    """A family joins only when no two of its states share a key. This
    re-runs the sweep on every listed family's field pack, so a map
    edit that stops reading a setting its files vary fails here. The
    full sweep over each family's derivation sources is in the report.
    """

    @pytest.mark.parametrize("family", sorted(READ_BYTES_VERIFIED))
    def test_no_two_states_share_a_key(self, family):
        pack = PACKS / f"{family}.json"
        assert pack.is_file(), f"{family} is listed but has no field pack"
        matrix = _pack_matrix(f"{family}.json")
        by_key: dict[str, set[str]] = {}
        for cell in matrix.cells:
            key = EventParser.pronto_read_key(cell.pronto)
            assert key is not None, cell_key(cell)
            by_key.setdefault(key, set()).add(cell_key(cell))
        shared = {k: v for k, v in by_key.items() if len(v) > 1}
        assert shared == {}

    @pytest.mark.parametrize("family", sorted(READ_BYTES_VERIFIED))
    def test_the_power_codes_have_keys_of_their_own(self, family):
        matrix = _pack_matrix(f"{family}.json")
        cells = {EventParser.pronto_read_key(c.pronto) for c in matrix.cells}
        for code in (matrix.off, matrix.on):
            if code:
                key = EventParser.pronto_read_key(code)
                assert key is not None and key not in cells


# ---------------------------------------------------------------------------
# What the key is made of
# ---------------------------------------------------------------------------


class TestTheKey:

    def test_a_pack_code_hashes_as_its_read_key(self):
        """For DAIKIN216 that is the shared settings-frame key."""
        (signature, members), = idm.shared_settings_frames().items()
        matrix = _pack_matrix("DAIKIN216.json")
        for cell in matrix.cells:
            reading = read_code(cell.pronto)
            assert EventParser.pronto_byte_hash(cell.pronto) == (
                idm.shared_frame_key(signature, members, reading.frames[1])
            ), cell_key(cell)

    def test_the_encoder_reproduces_a_pack_cells_key(self):
        """The local encoder is only trusted because of this."""
        cell = _pack_matrix("DAIKIN216.json").cells[0]
        settings = list(read_code(cell.pronto).frames[1])
        assert read_code(_code(settings)).protocol_id == "DAIKIN216"
        assert (EventParser.pronto_read_key(_code(settings))
                == EventParser.pronto_read_key(cell.pronto))

    def test_bits_no_field_names_do_not_take_part(self):
        """Byte 11 and byte 15 are read by no field of either Daikin
        map: a handset that writes them differently is the same state.
        The checksum moves with them and is recomputed, never copied
        into the key."""
        base = _code(_settings())
        for other in (_settings(byte11=0x06), _settings(byte15=0xC5)):
            assert EventParser.pronto_read_key(_code(other)) == (
                EventParser.pronto_read_key(base)
            )
            assert _timing_hash(_code(other)) != _timing_hash(base)

    @pytest.mark.parametrize("change", [
        {"temp_byte": 0x26}, {"mode_power": 0x41}, {"mode_power": 0x30},
        {"fan_swing": 0x3F}, {"fan_swing": 0x50}, {"swing_h": 0x0F},
        # DAIKIN152's flags: part of the shared frame, so DAIKIN216's too
        {"byte13": 0x01}, {"byte13": 0x04}, {"byte16": 0x04},
    ])
    def test_every_field_the_map_reads_takes_part(self, change):
        assert EventParser.pronto_read_key(_code(_settings(**change))) != (
            EventParser.pronto_read_key(_code(_settings()))
        )

    def test_a_bit_that_breaks_the_checksum_forms_no_key(self):
        """A bit the air flipped is refused, never heard as a different
        state: the key only forms once the map's checksum holds."""
        broken = _settings()
        broken[6] ^= 0x02        # temperature bit, checksum left alone
        assert read_code(_code(broken)).protocol_id == "DAIKIN216"
        assert EventParser.pronto_read_key(_code(broken)) is None

    def test_provisional_fields_take_part_like_ratified_ones(self):
        """Owner ruling 2026-09-30: confidence gates comb findings, never
        identity. Gertrude's DAIKIN152 swing arrives provisional."""
        demoted = dataclasses.replace(D216, fields=[
            dataclasses.replace(f, confidence="provisional")
            for f in D216.fields
        ])
        frames = read_code(_code(_settings())).frames
        swung = read_code(_code(_settings(swing_h=0x0F))).frames
        assert read_bytes_key(demoted, frames) == read_bytes_key(D216, frames)
        assert read_bytes_key(demoted, swung) != read_bytes_key(demoted, frames)

    def test_a_family_key_is_protocol_identity_bytes_and_fields(self):
        """The key of a listed family whose settings frame no other
        listed family shares. DAIKIN216 is shared today, so this pins
        the function on its own map rather than the live byte hash."""
        import hashlib

        frames = read_code(_code(_settings())).frames
        payload = _json.dumps([
            "DAIKIN216",
            [list(e) for e in D216.identity_bytes],
            [["temperature", 0x24], ["mode", 3], ["fan_speed", 3],
             ["swing_vertical", 0], ["swing_horizontal", 0], ["power", 1]],
        ], separators=(",", ":"))
        assert [f.name for f in D216.fields] == [
            "temperature", "mode", "fan_speed", "swing_vertical",
            "swing_horizontal", "power",
        ]
        assert read_bytes_key(D216, frames) == hashlib.sha256(
            ("read:" + payload).encode()
        ).hexdigest()[:16]


# ---------------------------------------------------------------------------
# The same key on both sides
# ---------------------------------------------------------------------------


class TestTheSameKeyOnBothSides:

    def test_a_file_code_and_its_capture_agree(self):
        """Wig side through ``wig_signal_identity``; capture side through
        ``normalize`` on the Pronto a receive path rebuilds."""
        from custom_components.hair.models import CaptureResult
        from custom_components.hair.signal_monitor import normalize

        for cell in _pack_matrix("DAIKIN216.json").cells[:40]:
            command = ProntoCommand(cell.pronto)
            capture = normalize(CaptureResult(
                protocol="PRONTO",
                code=raw_to_pronto(command.get_raw_timings(),
                                   frequency=command.modulation),
                raw_timings=command.get_raw_timings(),
                frequency=command.modulation, confidence=1.0,
            ))
            assert capture.byte_hash == (
                wig_signal_identity(cell.pronto).byte_hash
            ), cell_key(cell)

    def test_a_stored_row_hashes_as_the_capture_does(self):
        cell = _pack_matrix("DAIKIN216.json").cells[5]
        assert canonical_byte_hash(cell.pronto) == (
            wig_signal_identity(cell.pronto).byte_hash
        )

    def test_with_or_without_the_daikin152_leader(self):
        """On the #183 shape: a handset press with the leader, a
        different clock frame and different timer bytes (11 and 12,
        which the map does not read), against a wig state with none of
        those. Same settings, same key; the timing hash cannot agree."""
        from .test_a_leader_is_not_off import (
            _HANDSET_CLOCK,
            _handset,
            _stored_state,
        )
        from .test_a_leader_is_not_off import (
            _settings as _d152_settings,
        )

        body = _d152_settings(1, 3, 24, 0xA)
        timer = list(body[:18])
        timer[11], timer[12] = 0x0E, 0xE0
        timer.append(sum(timer) & 0xFF)
        with_leader = _handset(timer, clock=_HANDSET_CLOCK)
        without = _stored_state(body)
        assert read_code(with_leader).protocol_id == "DAIKIN152"
        assert read_code(without).protocol_id == "DAIKIN152"
        key = EventParser.pronto_read_key(with_leader)
        assert key is not None
        assert EventParser.pronto_read_key(without) == key
        assert _timing_hash(with_leader) != _timing_hash(without)


# ---------------------------------------------------------------------------
# The air
# ---------------------------------------------------------------------------


class TestTheAir:
    """Item 6: the read key survives what a receiver does to a press,
    and the timing hash does not."""

    PRESSES = 20

    @pytest.mark.parametrize("which", [0, 57, 131, 199])
    def test_esphome_every_press_keeps_the_key(self, which):
        cell = _pack_matrix("DAIKIN216.json").cells[which]
        file_key = EventParser.pronto_read_key(cell.pronto)
        timing = set()
        for press in range(self.PRESSES):
            heard, _ = _air(cell.pronto, press, "esphome")
            assert EventParser.pronto_byte_hash(heard) == file_key, press
            timing.add(_timing_hash(heard))
        assert _timing_hash(cell.pronto) not in timing
        assert len(timing) > self.PRESSES // 2

    @pytest.mark.parametrize("which", [0, 57, 131, 199])
    def test_broadlink_never_forms_a_different_key(self, which):
        """Broadlink's extremes are wider than the maps' windows in
        places (a 3.4 ms header mark at 0.47 is 1.6 ms, under the
        header window), so some presses are REFUSED and fall back to
        the timing hash. None is ever heard as another state. Measured
        on this set: 17 of the 18 unglitched presses keep the key and
        both glitched presses are refused."""
        cell = _pack_matrix("DAIKIN216.json").cells[which]
        file_key = EventParser.pronto_read_key(cell.pronto)
        kept = 0
        for press in range(self.PRESSES):
            heard, _glitched = _air(cell.pronto, press, "broadlink")
            key = EventParser.pronto_read_key(heard)
            assert key in (None, file_key), press
            kept += key == file_key
        assert kept >= 3 * self.PRESSES // 4

    def test_a_heard_press_finds_its_cell_at_the_byte_hash_tier(self):
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        for which in (0, 99, 199):
            cell = matrix.cells[which]
            for press in range(5):
                heard, _ = _air(cell.pronto, press, "esphome")
                assert _match(index, heard) == (
                    cell_key(cell), None, TIER_BYTE_HASH
                ), (cell_key(cell), press)


# ---------------------------------------------------------------------------
# The index refuses on states, not codes
# ---------------------------------------------------------------------------


class TestTheIndexComparesStates:

    def _lattice(self, cells, off=None):
        return ClimateMatrix(
            min_temp=18.0, max_temp=30.0, precision=1.0,
            modes=sorted({c.mode for c in cells}),
            fan_modes=sorted({c.fan for c in cells}), swing_modes=[],
            off=off, cells=cells,
        )

    def test_two_states_the_map_cannot_tell_apart_are_refused(self):
        """Different coordinates, same read fields (they differ only in
        byte 11). The byte-hash key they share is refused, so a press
        that is neither code exactly -- a handset writing byte 15 its
        own way -- is named as neither state. Each file code still
        finds its own cell through the (fingerprint, byte hash) pair,
        because the S/L pattern is timing-based and tells them apart."""
        a = ClimateCell(mode="cool", fan="low", temp=18.0,
                        pronto=_code(_settings()))
        b = ClimateCell(mode="cool", fan="low", temp=19.0,
                        pronto=_code(_settings(byte11=0x06)))
        index = build_cell_index(self._lattice([a, b]))
        key = EventParser.pronto_byte_hash(a.pronto)
        assert key == EventParser.pronto_byte_hash(b.pronto)
        assert key not in index.bytehash
        assert _match(index, a.pronto)[0] == "cool/low/18"
        assert _match(index, b.pronto)[0] == "cool/low/19"
        assert _match(index, _code(_settings(byte15=0xC5))) is None

    def test_one_code_under_two_labels_merges(self):
        """A file that stores one code under several labels (dry and
        fan_only, where the unit ignores temperature; 1,344 cells of the
        #183 wig) is heard as one of them rather than refused (owner
        ruling 2026-09-30). The labels share their bytes, so a pinned
        device is sent the same code whichever one wins."""
        code = _code(_settings(mode_power=0x21))
        a = ClimateCell(mode="dry", fan="auto", temp=18.0, pronto=code)
        b = ClimateCell(mode="dry", fan="auto", temp=19.0, pronto=code)
        index = build_cell_index(self._lattice([a, b]))
        assert _match(index, code)[0] in ("dry/auto/18", "dry/auto/19")

    def test_distinct_states_each_keep_their_key(self):
        a = ClimateCell(mode="cool", fan="low", temp=18.0,
                        pronto=_code(_settings(temp_byte=0x24)))
        b = ClimateCell(mode="cool", fan="low", temp=19.0,
                        pronto=_code(_settings(temp_byte=0x26)))
        index = build_cell_index(self._lattice([a, b]))
        assert _match(index, a.pronto)[0] == "cool/low/18"
        assert _match(index, b.pronto)[0] == "cool/low/19"

    def test_a_handset_that_writes_other_unread_bytes_finds_the_cell(self):
        """The #183 shape on DAIKIN216: the handset's unread bytes are
        not the file's. Same state, same cell."""
        cell = ClimateCell(mode="cool", fan="low", temp=18.0,
                           pronto=_code(_settings()))
        index = build_cell_index(self._lattice([cell]))
        handset = _code(_settings(byte11=0x06, byte15=0xC5))
        assert _match(index, handset) == ("cool/low/18", None, TIER_BYTE_HASH)


# ---------------------------------------------------------------------------
# Every other family, byte for byte
# ---------------------------------------------------------------------------


class TestEveryOtherFamilyHoldsStill:
    """The byte hash moves only where a read key exists, and a read key
    exists only for a code that reads as a listed family."""

    @staticmethod
    def _codes():
        from .census_corpus import corpus
        from .test_identity_tail_strip import UNION_CORPUS

        for path in sorted(PACKS.glob("*.json")):
            if "defects" in path.name:
                continue
            matrix = _pack_matrix(path.name)
            for cell in matrix.cells:
                yield path.name, cell.pronto
            for code in (matrix.off, matrix.on):
                if code:
                    yield path.name, code
        for code in UNION_CORPUS:
            yield "tail-strip corpus", code
        for row in corpus():
            if len(row.timings) >= 4:
                signed = [abs(v) if i % 2 == 0 else -abs(v)
                          for i, v in enumerate(row.timings)]
                yield "census", raw_to_pronto(signed, frequency=38000)

    def test_only_listed_codes_move(self):
        moved = unmoved = 0
        for source, code in self._codes():
            key = EventParser.pronto_read_key(code)
            if key is None:
                assert EventParser.pronto_byte_hash(code) == (
                    _timing_hash(code)
                ), source
                unmoved += 1
            else:
                assert read_code(code).protocol_id in READ_BYTES_VERIFIED
                moved += 1
        assert unmoved > moved > 0


# ---------------------------------------------------------------------------
# Rows stored before the upgrade
# ---------------------------------------------------------------------------


class TestRowsStoredBeforeTheUpgrade:
    """A command and a trigger written under an older identity meet a
    real press again after the upgrade.

    No migration: ``_backfill_canonical_identity`` runs on every load,
    ungated, and repoints the byte hash from the stored code, which now
    yields the read key. Two "befores" matter: a row from 0.17.0 (neither
    list existed) and a row written while #187 was on the test box
    (setting-frame timing hash). Both land on the same key, and the
    press that fires them is an air-shaped one, not the file code.
    """

    @staticmethod
    def _stale(pronto, *, step2: bool, read_bytes: bool = False) -> str | None:
        """The byte hash a row was written with: 0.17.0 (neither list),
        a #187 test-box build (setting frames), or the read-bytes round
        (DAIKIN216 alone, on its family key)."""
        original = (idm.SETTING_IDENTITY_VERIFIED, idm.READ_BYTES_VERIFIED)
        try:
            if not step2 and not read_bytes:
                idm.SETTING_IDENTITY_VERIFIED = frozenset()
            idm.READ_BYTES_VERIFIED = (
                frozenset({"DAIKIN216"}) if read_bytes else frozenset()
            )
            return canonical_byte_hash(pronto)
        finally:
            idm.SETTING_IDENTITY_VERIFIED, idm.READ_BYTES_VERIFIED = original

    _VINTAGES = pytest.mark.parametrize(
        "step2,read_bytes",
        [(False, False), (True, False), (True, True)],
        ids=["0.17.0", "step2", "read-bytes"],
    )

    @staticmethod
    def _store(device=None, triggers=None):
        from unittest.mock import MagicMock

        from custom_components.hair.storage import HAIRStore

        store = HAIRStore(MagicMock())
        store._data = {"d1": device} if device else {}
        store._triggers = triggers or {}
        return store

    @_VINTAGES
    def test_a_stored_command_is_repointed_to_the_read_key(
        self, step2, read_bytes,
    ):
        from custom_components.hair.models import (
            CommandCategory,
            IRCommand,
            IRDevice,
        )

        cell = _pack_matrix("DAIKIN216.json").cells[3]
        stale = self._stale(cell.pronto, step2=step2, read_bytes=read_bytes)
        key = EventParser.pronto_read_key(cell.pronto)
        assert stale != key                       # the move is real

        device = IRDevice(id="d1", name="AC")
        device.add_command(IRCommand(
            name="Cool 18", category=CommandCategory.CUSTOM,
            protocol="PRONTO", code=cell.pronto, byte_hash=stale,
            repeat_count=0,
        ))
        assert self._store(device=device)._backfill_canonical_identity()
        assert device.commands[0].byte_hash == key

    @_VINTAGES
    def test_a_stored_trigger_fires_on_a_heard_press(self, step2, read_bytes):
        from custom_components.hair.models import IRTrigger

        cell = _pack_matrix("DAIKIN216.json").cells[3]
        trigger = IRTrigger(
            id="t1", name="learned before the upgrade", code=cell.pronto,
            protocol="PRONTO",
            byte_hash=self._stale(cell.pronto, step2=step2,
                                  read_bytes=read_bytes),
            signal_fingerprint=wig_signal_identity(cell.pronto).fingerprint,
        )
        heard, _ = _air(cell.pronto, 2, "esphome")
        ident = wig_signal_identity(heard)
        before = trigger.matches_signal(
            ident.fingerprint, ident.byte_hash,
            ident.decoded_fingerprint, ident.decode_covers,
        )
        self._store(triggers={"t1": trigger})._backfill_canonical_identity()
        after = trigger.matches_signal(
            ident.fingerprint, ident.byte_hash,
            ident.decoded_fingerprint, ident.decode_covers,
        )
        assert (before, after) == (False, True)

    def test_the_trigger_does_not_fire_on_another_state(self):
        from custom_components.hair.models import IRTrigger

        matrix = _pack_matrix("DAIKIN216.json")
        cell, other = matrix.cells[3], matrix.cells[4]
        trigger = IRTrigger(
            id="t1", name="t", code=cell.pronto, protocol="PRONTO",
            byte_hash=self._stale(cell.pronto, step2=True),
            signal_fingerprint=wig_signal_identity(cell.pronto).fingerprint,
        )
        self._store(triggers={"t1": trigger})._backfill_canonical_identity()
        heard, _ = _air(other.pronto, 2, "esphome")
        ident = wig_signal_identity(heard)
        assert trigger.matches_signal(
            ident.fingerprint, ident.byte_hash,
            ident.decoded_fingerprint, ident.decode_covers,
        ) is False
