"""Radio rows get the S/L diamonds wherever infrared rows have them.

One rule: the fingerprint's. A radio frame's diamonds are ``body_labels``
over its body, one per edge (mark and space alike), the same two-level
labels ``frame_fingerprint`` hashes,
read by ``rf_frames.identity_of_frame`` on the stored frame. So the
diamonds and HAIR's radio identity can never disagree.

The body only: a header's sync pair and the gap get
no diamond. A frame with no body gets none. Derived at read time on the
doors that serialize radio rows; never stored.
"""
from __future__ import annotations

from custom_components.hair import rf_frames, rf_paste, websocket_api
from custom_components.hair.const import MEDIUM_RF
from custom_components.hair.tests.test_rf_family import _frame as _keyfob
from custom_components.hair.tests.test_rf_family_dooya import _word as _dooya


def _rule(frame: list[int]) -> str:
    """The fingerprint's own reading, spelled out: the longest bodied
    piece's two-level labels."""
    pieces = rf_frames.split_frames(frame)
    candidates = [
        (piece, rf_frames.split_body(piece)) for piece in pieces
    ]
    candidates = [
        (p, parts) for p, parts in candidates
        if parts.body and rf_frames.has_body(parts)
    ]
    _, parts = max(candidates, key=lambda item: len(item[0].edges))
    return "".join("L" if label else "S" for label in rf_frames.body_labels(parts))


KEYFOB = _keyfob(0x950E49)  # the bench keyfob, Button 1 on
DOORBELL = _keyfob(0xEC8614, unit=301)  # the bench doorbell's address


class TestTheRule:
    def test_the_keyfob_reads_as_the_fingerprint_reads_it(self):
        pattern = websocket_api._rf_sl_pattern(KEYFOB)
        assert pattern == _rule(KEYFOB)
        # One diamond per edge of the body, mark and space alike, as the
        # fingerprint labels them (and as radio Sniffer rows already
        # draw them): 24 data pairs are 48 edges, plus the closing mark.
        assert len(pattern) == 49
        assert set(pattern) == {"S", "L"}
        assert pattern == rf_frames.identity_of_frame(KEYFOB).sl_pattern

    def test_two_buttons_two_patterns_one_address(self):
        on = websocket_api._rf_sl_pattern(_keyfob(0x950E49))
        off = websocket_api._rf_sl_pattern(_keyfob(0x950E41))
        assert on != off
        # The 20-bit address is the first 20 pairs on both.
        assert on[:20] == off[:20]

    def test_the_doorbell(self):
        assert websocket_api._rf_sl_pattern(DOORBELL) == _rule(DOORBELL)

    def test_a_header_sync_pair_gets_no_diamond(self):
        word = _dooya()
        pattern = websocket_api._rf_sl_pattern(word)
        assert pattern == _rule(word)
        parts = rf_frames.split_body(max(rf_frames.split_frames(word), key=lambda p: len(p.edges)))
        assert parts.header, "the fixture has a header"
        # The pattern starts at the body: no diamond for the 5000/1500
        # sync pair, and none for the gap.
        assert len(pattern) == len(rf_frames.body_labels(parts))
        assert len(pattern) == len(word) - 2 - 1
        assert word[:2] == [5000, -1500]

    def test_no_body_no_diamonds(self):
        assert websocket_api._rf_sl_pattern([500, -500]) is None
        assert websocket_api._rf_sl_pattern([]) is None
        assert websocket_api._rf_sl_pattern(None) is None


class TestTheDoors:
    def _rows(self):
        return [
            {"medium": MEDIUM_RF, "raw_timings": KEYFOB},
            {"medium": "ir", "protocol": "PRONTO", "code": "0000 006D"},
            {"medium": MEDIUM_RF, "raw_timings": KEYFOB, "sl_pattern": "SL"},
            {"medium": MEDIUM_RF, "raw_timings": [500, -500]},
        ]

    def test_radio_rows_get_them_infrared_rows_do_not(self):
        rows = self._rows()
        websocket_api._augment_rf_family(rows)
        assert rows[0]["sl_pattern"] == _rule(KEYFOB)
        assert "sl_pattern" not in rows[1]
        assert "rf_family" not in rows[1]

    def test_a_row_that_carries_its_own_keeps_it(self):
        # A Sniffer row's to_dict already sets it from the same call.
        rows = self._rows()
        websocket_api._augment_rf_family(rows)
        assert rows[2]["sl_pattern"] == "SL"

    def test_no_body_goes_out_as_none(self):
        rows = self._rows()
        websocket_api._augment_rf_family(rows)
        assert rows[3]["sl_pattern"] is None

    def test_a_failure_costs_one_row_its_diamonds(self, monkeypatch):
        def boom(_frame):
            raise RuntimeError("reader bug")

        websocket_api._rf_sl_pattern_of.cache_clear()
        monkeypatch.setattr(rf_frames, "identity_of_frame", boom)
        rows = [{"medium": MEDIUM_RF, "raw_timings": [1, -2, 3, -4, 5, -6]},
                {"medium": MEDIUM_RF, "raw_timings": KEYFOB}]
        websocket_api._augment_rf_family(rows)
        assert rows[0]["sl_pattern"] is None
        assert rows[1]["sl_pattern"] is None
        # The family label is a separate reading and still goes out.
        assert rows[1]["rf_family"] is not None
        websocket_api._rf_sl_pattern_of.cache_clear()

    def test_each_test_starts_with_empty_caches(self):
        # The conftest clears both per-frame readings around every test:
        # the doors above filled them, this one sees none.
        from custom_components.hair import rf_family

        assert websocket_api._rf_sl_pattern_of.cache_info().currsize == 0
        assert rf_family._family_of.cache_info().currsize == 0

    def test_the_trigger_list_and_the_device_door_both_augment(self):
        import inspect

        assert "_augment_rf_family(rows)" in inspect.getsource(websocket_api.ws_get_triggers)
        assert '_augment_rf_family(full.get("commands"))' in inspect.getsource(
            websocket_api._device_full
        )


class TestTheEditorDoor:
    def test_validate_gives_the_same_diamonds_as_the_row(self):
        sub = rf_paste.to_sub(KEYFOB, 433_920_000, None)
        result = rf_paste.validate(sub, None)
        assert result["ok"]
        assert result["sl_pattern"] == websocket_api._rf_sl_pattern(result["frame"])
        assert result["sl_pattern"] == _rule(KEYFOB)

    def test_a_refused_paste_has_none(self):
        result = rf_paste.validate("not a code", None)
        assert not result["ok"]
        assert "sl_pattern" not in result


class TestNothingIsStored:
    def test_command_and_trigger_records_carry_no_pattern(self):
        from custom_components.hair.models import IRCommand, IRTrigger

        cmd = IRCommand(name="On", medium=MEDIUM_RF, protocol="RF_RAW", raw_timings=KEYFOB)
        assert "sl_pattern" not in cmd.to_dict()
        trig = IRTrigger(name="On", signal_fingerprint="x", medium=MEDIUM_RF,
                         protocol="RF_RAW", raw_timings=KEYFOB)
        assert "sl_pattern" not in trig.to_dict()
