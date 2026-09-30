"""DAIKIN152 joins read-bytes identity, and the shared Daikin frame key.

GH #183. Gertrude's traits round made the DAIKIN152 map read powerful,
economy, sleep and both swing nibbles, so its states separate by what
the map reads and the family joins ``READ_BYTES_VERIFIED``.

DAIKIN216 frame 1 and DAIKIN152 frame 3 are the same frame byte for
byte, and a receiver that splits a press hands that frame over alone,
naming neither family. So the key of a shared settings frame belongs to
the FRAME: whole press and lone frame alike, attributed to neither
family, and every cell of either family carries it (owner ruling
2026-09-30). This file pins which frames share, what the key holds and
in what order, the #183 capture finding its cell, lone frames finding
theirs off the air, and rows stored before the upgrade.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json as _json
from typing import ClassVar

import pytest

import custom_components.hair.identity as idm
from custom_components.hair import field_readers
from custom_components.hair.event_parser import EventParser
from custom_components.hair.field_readers import library, read_code
from custom_components.hair.identity import (
    TIER_BYTE_HASH,
    canonical_byte_hash,
    shared_frame_key,
    shared_frame_positions,
    shared_settings_frames,
)
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, cell_key
from custom_components.hair.wig_identity import wig_signal_identity

from .test_a_leader_is_not_off import _handset, _split, _stored_state
from .test_cell_index_shared_keys import _match, _pack_matrix
from .test_daikin152_traits import CAPTURE, _settings
from .test_read_bytes_identity import _air
from .test_read_bytes_identity import _code as _d216_code
from .test_read_bytes_identity import _settings as _d216_settings

MAPS = {m.protocol_id: m for m in library()}

_SIGNATURE = (
    152,
    ((0, 0x11), (1, 0xDA), (2, 0x27)),
    (("checksum_sum",
      '{"mod":256,"offset":0,"range":[0,17],"target_byte":18}'),),
)
_MEMBERS = (("DAIKIN152", 3), ("DAIKIN216", 1))
_POSITIONS = (
    (5, 0x01),    # power
    (5, 0x70),    # mode
    (6, 0xFF),    # temperature
    (8, 0x0F),    # swing, vertical
    (8, 0xF0),    # fan speed
    (9, 0x0F),    # swing, horizontal
    (13, 0x01),   # powerful
    (13, 0x04),   # sleep
    (16, 0x04),   # economy
)


def _key(code: str) -> str | None:
    return EventParser.pronto_read_key(code)


# ---------------------------------------------------------------------------
# Which frames share, derived from the maps
# ---------------------------------------------------------------------------


class TestTheSharedFrame:

    def test_daikin152_is_listed_beside_daikin216(self):
        assert frozenset({"DAIKIN216", "DAIKIN152"}) == (
            idm.READ_BYTES_VERIFIED
        )
        assert "DAIKIN152" in idm.SETTING_IDENTITY_VERIFIED

    def test_the_rule_yields_exactly_these_two_frames(self):
        """Width, header bytes within the frame and ratified checksum
        all match. A future map that matches by accident lands here."""
        assert shared_settings_frames() == {_SIGNATURE: _MEMBERS}

    def test_nothing_shares_when_only_one_family_is_listed(self, monkeypatch):
        monkeypatch.setattr(idm, "READ_BYTES_VERIFIED",
                            frozenset({"DAIKIN216"}))
        assert shared_settings_frames() == {}


# ---------------------------------------------------------------------------
# What the key holds, and in what order
# ---------------------------------------------------------------------------


class TestWhatTheKeyHolds:

    def test_every_distinct_position_either_map_reads_sorted(self):
        assert shared_frame_positions(_MEMBERS) == _POSITIONS

    def test_the_payload_byte_for_byte(self):
        frame = read_code(CAPTURE).frames[3]
        values = []
        for byte, mask in _POSITIONS:
            shift = (mask & -mask).bit_length() - 1
            values.append([byte, mask, (frame[byte] & mask) >> shift])
        payload = _json.dumps(
            [152, [[0, 0x11], [1, 0xDA], [2, 0x27]],
             [["checksum_sum",
               '{"mod":256,"offset":0,"range":[0,17],"target_byte":18}']],
             values],
            separators=(",", ":"),
        )
        expected = hashlib.sha256(("frame:" + payload).encode()).hexdigest()
        assert shared_frame_key(_SIGNATURE, _MEMBERS, frame) == expected[:16]
        assert _key(CAPTURE) == expected[:16]

    def test_field_names_stay_out(self, monkeypatch):
        """Two maps naming the same bits differently still agree."""
        renamed = [
            dataclasses.replace(m, fields=[
                dataclasses.replace(f, name=f"x_{f.name}") for f in m.fields
            ]) if m.protocol_id == "DAIKIN216" else m
            for m in library()
        ]
        before = _key(CAPTURE)
        monkeypatch.setattr(field_readers, "_LIBRARY", renamed)
        assert _key(CAPTURE) == before

    def test_confidence_stays_out(self, monkeypatch):
        """Provisional fields take part exactly like ratified ones."""
        promoted = [
            dataclasses.replace(m, fields=[
                dataclasses.replace(f, confidence="ratified") for f in m.fields
            ]) for m in library()
        ]
        before = _key(CAPTURE)
        monkeypatch.setattr(field_readers, "_LIBRARY", promoted)
        assert _key(CAPTURE) == before

    @pytest.mark.parametrize("family", ["DAIKIN152", "DAIKIN216"])
    def test_a_broken_checksum_forms_no_key(self, family):
        if family == "DAIKIN152":
            settings = _settings("cool", 0x7, 24)
            settings[6] ^= 0x02
            whole = _handset(settings)
        else:
            settings = _d216_settings()
            settings[6] ^= 0x02
            whole = _d216_code(settings)
        assert read_code(whole).protocol_id == family
        assert _key(whole) is None
        assert _key(_split(whole)[-1]) is None


# ---------------------------------------------------------------------------
# A documented property, not a surprise
# ---------------------------------------------------------------------------


class TestTheTwoFamiliesShareAKey:
    """A DAIKIN216 press and a DAIKIN152 press with identical settings
    carry the same key (owner ruling 2026-09-30). In a house with both
    generations and one receiver that sees both handsets, a press on one
    can be heard as a state of the other's remote; receiver scope on the
    remote is the mitigation, and the units do not answer each other."""

    def test_identical_settings_share_a_key(self):
        settings = _d216_settings(temp_byte=0x30, mode_power=0x39,
                                  fan_swing=0x7F)
        d216, d152 = _d216_code(settings), _handset(settings)
        assert read_code(d216).protocol_id == "DAIKIN216"
        assert read_code(d152).protocol_id == "DAIKIN152"
        assert _key(d216) == _key(d152) is not None

    def test_different_settings_do_not(self):
        a = _handset(_settings("cool", 0x7, 24))
        b = _d216_code(_d216_settings(temp_byte=0x32))
        assert _key(a) != _key(b)


# ---------------------------------------------------------------------------
# The #183 capture
# ---------------------------------------------------------------------------


def _file_form(settings: list[int]) -> list[int]:
    """A state as the reporter's file writes it: byte 5 bit 3 clear,
    timer bytes 06 60, byte 15 C0 -- none of which the map reads."""
    data = list(settings[:18])
    data[5] &= ~0x08
    data[11], data[12], data[15] = 0x06, 0x60, 0xC0
    return [*data, sum(data) & 0xFF]


class TestTheCommittedCapture:
    """The reporter's own capture against a lattice of the #183 wig's
    shape. Nothing from his wig is in here: the lattice is synthesized,
    in his file's form (leaderless, its unread bytes), around the state
    the capture reads."""

    FANS: ClassVar[dict[str, dict[str, bool]]] = {
        "high": {}, "powerful": {"powerful": True},
            "economy": {"economy": True}, "sleep": {"sleep": True}}

    @pytest.fixture(scope="class")
    def lattice(self):
        cells = [
            ClimateCell(
                mode="cool", fan=fan, swing=swing, temp=float(temp),
                pronto=_stored_state(_file_form(
                    _settings("cool", 0x7, temp, swing=swing, **flags)
                )),
            )
            for fan, flags in self.FANS.items()
            for swing in ("off", "vertical", "horizontal", "both")
            for temp in (23, 24, 25)
        ]
        matrix = ClimateMatrix(
            min_temp=16.0, max_temp=30.0, precision=1.0, modes=["cool"],
            fan_modes=sorted(self.FANS), swing_modes=[
                "both", "horizontal", "off", "vertical"],
            off=_handset(_settings("cool", 0x7, 24, power=0)),
            cells=cells,
        )
        return matrix, build_cell_index(matrix)

    def test_the_capture_reads_as_its_state(self):
        reading = read_code(CAPTURE)
        assert reading.protocol_id == "DAIKIN152"
        assert list(reading.frames[3][:18]) != _file_form(
            _settings("cool", 0x7, 24, swing="vertical"))[:18]

    def test_the_capture_finds_cool_high_vertical_24(self, lattice):
        _matrix, index = lattice
        assert _match(index, CAPTURE) == (
            "cool/high/vertical/24", None, TIER_BYTE_HASH
        )

    def test_its_settings_piece_alone_finds_it_too(self, lattice):
        _matrix, index = lattice
        assert _match(index, _split(CAPTURE)[-1]) == (
            "cool/high/vertical/24", None, TIER_BYTE_HASH
        )

    def test_no_piece_of_it_is_off(self, lattice):
        _matrix, index = lattice
        for piece in [CAPTURE, *_split(CAPTURE)]:
            got = _match(index, piece)
            assert got is None or got[1] != "off"
            assert got is None or got[0] != "off"


# ---------------------------------------------------------------------------
# Lone frames off the air
# ---------------------------------------------------------------------------


class TestLoneFramesFindTheirCells:
    """What a splitting receiver hands over: the settings frame on its
    own, as that receiver measured it (doc 22's table, both
    transmitters). Split first, then shaped, so every case really is a
    lone frame and never a whole press that failed to split."""

    @pytest.mark.parametrize("transmitter", ["esphome", "broadlink"])
    def test_a_lone_daikin152_settings_frame(self, transmitter):
        from .test_a_leader_is_not_off import _lattice

        matrix, settings = _lattice()
        index = build_cell_index(matrix)
        found = 0
        for n, cell in enumerate(matrix.cells):
            piece = _split(_handset(settings[cell_key(cell)]))[-1]
            heard, _ = _air(piece, n, transmitter)
            got = _match(index, heard)
            assert got is None or got[0] == cell_key(cell), cell_key(cell)
            found += got == (cell_key(cell), None, TIER_BYTE_HASH)
        if transmitter == "esphome":
            assert found == len(matrix.cells)
        else:
            assert found >= 3 * len(matrix.cells) // 4

    @pytest.mark.parametrize("transmitter", ["esphome", "broadlink"])
    def test_a_lone_daikin216_settings_frame(self, transmitter):
        matrix = _pack_matrix("DAIKIN216.json")
        index = build_cell_index(matrix)
        found = 0
        for n, cell in enumerate(matrix.cells):
            pieces = _split(cell.pronto)
            assert len(pieces) == 2
            heard, _ = _air(pieces[-1], n, transmitter)
            got = _match(index, heard)
            assert got is None or got[0] == cell_key(cell), cell_key(cell)
            found += got == (cell_key(cell), None, TIER_BYTE_HASH)
        if transmitter == "esphome":
            assert found == len(matrix.cells)
        else:
            assert found >= 3 * len(matrix.cells) // 4

    def test_the_file_exact_lone_frame_too(self):
        """The FTXS20LVMA lone bench's shape: file-exact pieces."""
        from .test_a_leader_is_not_off import _lattice

        matrix, settings = _lattice()
        index = build_cell_index(matrix)
        for cell in matrix.cells:
            piece = _split(_handset(settings[cell_key(cell)]))[-1]
            assert _match(index, piece)[0] == cell_key(cell)

    def test_off_stays_off_and_nothing_else_is(self):
        from .test_a_leader_is_not_off import _OFF_SETTINGS, _lattice

        matrix, settings = _lattice()
        index = build_cell_index(matrix)
        off_heard, _ = _air(_handset(_OFF_SETTINGS), 1, "esphome")
        assert _match(index, off_heard)[0] == "off"
        assert _match(index, _split(off_heard)[-1])[0] == "off"
        for n, body in enumerate(list(settings.values())[::5]):
            heard, _ = _air(_handset(body), n, "esphome")
            for piece in [heard, *_split(heard)]:
                got = _match(index, piece)
                assert got is None or got[0] != "off"


# ---------------------------------------------------------------------------
# Rows stored before the upgrade
# ---------------------------------------------------------------------------


class TestDaikin152RowsStoredBeforeTheUpgrade:
    """A DAIKIN152 command and trigger from every earlier vintage land on
    the shared key through the load-time backfill. For DAIKIN152 the #187
    test-box builds and the read-bytes round wrote the same value (it was
    not listed in either), so two vintages cover three."""

    @staticmethod
    def _stale(pronto: str, *, step2: bool) -> str | None:
        original = (idm.SETTING_IDENTITY_VERIFIED, idm.READ_BYTES_VERIFIED)
        try:
            if not step2:
                idm.SETTING_IDENTITY_VERIFIED = frozenset()
            idm.READ_BYTES_VERIFIED = frozenset({"DAIKIN216"})
            return canonical_byte_hash(pronto)
        finally:
            idm.SETTING_IDENTITY_VERIFIED, idm.READ_BYTES_VERIFIED = original

    @staticmethod
    def _store(device=None, triggers=None):
        from unittest.mock import MagicMock

        from custom_components.hair.storage import HAIRStore

        store = HAIRStore(MagicMock())
        store._data = {"d1": device} if device else {}
        store._triggers = triggers or {}
        return store

    CODE = staticmethod(lambda: _stored_state(
        _file_form(_settings("cool", 0x7, 24, swing="vertical"))
    ))

    @pytest.mark.parametrize("step2", [False, True], ids=["0.17.0", "187"])
    def test_a_command_is_repointed(self, step2):
        from custom_components.hair.models import (
            CommandCategory,
            IRCommand,
            IRDevice,
        )

        code = self.CODE()
        stale, key = self._stale(code, step2=step2), _key(code)
        assert key is not None and stale != key
        device = IRDevice(id="d1", name="AC")
        device.add_command(IRCommand(
            name="Cool 24", category=CommandCategory.CUSTOM,
            protocol="PRONTO", code=code, byte_hash=stale, repeat_count=0,
        ))
        assert self._store(device=device)._backfill_canonical_identity()
        assert device.commands[0].byte_hash == key

    @pytest.mark.parametrize("step2", [False, True], ids=["0.17.0", "187"])
    def test_a_trigger_fires_on_the_handset_after_it(self, step2):
        """Before: the committed capture does not fire it. After: it
        does, whole and from its settings piece alone."""
        from custom_components.hair.models import IRTrigger

        code = self.CODE()
        trigger = IRTrigger(
            id="t1", name="learned before the upgrade", code=code,
            protocol="PRONTO", byte_hash=self._stale(code, step2=step2),
            signal_fingerprint=wig_signal_identity(code).fingerprint,
        )

        def fires(pronto):
            ident = wig_signal_identity(pronto)
            return trigger.matches_signal(
                ident.fingerprint, ident.byte_hash,
                ident.decoded_fingerprint, ident.decode_covers,
            )

        assert fires(CAPTURE) is False
        self._store(triggers={"t1": trigger})._backfill_canonical_identity()
        assert fires(CAPTURE) is True
        assert fires(_split(CAPTURE)[-1]) is True
        other = _handset(_settings("cool", 0x7, 25, swing="vertical"))
        assert fires(other) is False
