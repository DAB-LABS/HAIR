"""Tests for v0.5.8 byte_hash trigger identity (fine-tooth-comb).

Covers the Section 5 matrix from
``docs/internal/plans/byte-hash-trigger-identity.md``:
- Sony fixture reality checks (S/L collapse, byte_hash separation,
  jitter stability) using real captures from the loic.gouraud report,
- the trigger cross-fire matrix (scoped vs legacy),
- single-fire per physical press across Sony's full-frame auto-repeats
  (sliding dedup window),
- multi-receiver dedup preserved for legacy triggers under per-receiver
  byte_hash variance,
- rewire on byte-hash-only edits (precise repoint, sibling skip, legacy
  promotion),
- the byte_hash load-time backfill and the legacy matcher tier,
- IRTrigger.matches_byte_hash and from_dict lazy migration.

Fixture provenance: ESPHome ``dump: pronto`` captures of a Sony SIRC-15
remote's four colored buttons (0x52E9 / 0x32E9 / 0x72E9 / 0x12E9), posted
to the HA forum thread 1014414 post #8. RED_2 is a genuine jittered
re-capture of the red button from the same log.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hair.event_parser import EventParser
from custom_components.hair.models import IRCommand, IRDevice, IRTrigger
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager

SONY_RED = (
    "0000 006D 0010 0000 005C 0018 002D 0018 0016 0018 002D 0018 0017 "
    "0017 0016 0018 002D 0018 0016 0018 002D 0018 002D 0018 002D 0018 "
    "0016 0018 002D 0018 0016 0018 0016 0018 002D 0181"
)
SONY_RED_2 = (
    "0000 006D 0010 0000 005C 0018 002D 0018 0016 0018 002D 0018 0016 "
    "0017 0017 0018 002D 0018 0016 0018 002D 0018 002D 0018 002D 0018 "
    "0016 0018 002D 0018 0016 0018 0016 0018 002D 0181"
)
SONY_GREEN = (
    "0000 006D 0010 0000 005C 0018 0016 0018 002D 0018 002D 0018 0016 "
    "0018 0016 0018 002D 0018 0016 0017 002E 0018 002D 0018 002D 0018 "
    "0016 0018 002D 0018 0016 0017 0017 0018 002D 0181"
)
SONY_YELLOW = (
    "0000 006D 0010 0000 005D 0016 002E 0017 002E 0017 002F 0016 0017 "
    "0017 0017 0017 002E 0017 0018 0016 002E 0017 002E 0017 002F 0016 "
    "0017 0017 002E 0016 0018 0016 0017 0017 002F 0181"
)
SONY_BLUE = (
    "0000 006D 0010 0000 005D 0017 0016 0018 0017 0017 002D 0018 0016 "
    "0018 0016 0018 002D 0018 0016 0018 002D 0018 002D 0018 002D 0018 "
    "0016 0018 002D 0018 0016 0018 0016 0018 002D 0181"
)

BUTTONS = {
    "red": SONY_RED,
    "green": SONY_GREEN,
    "yellow": SONY_YELLOW,
    "blue": SONY_BLUE,
}


def _fp(code: str) -> str:
    # Canonical (wire) identity: HAIR hashes what a receiver would
    # hand it, not the file text (identity.py's canonical-form block).
    from custom_components.hair.identity import canonical_fingerprint

    return canonical_fingerprint("PRONTO", code, None)


def _bh(code: str) -> str:
    from custom_components.hair.identity import canonical_byte_hash

    bh = canonical_byte_hash(code)
    assert bh is not None
    return bh


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.bus = MagicMock()
    return hass


@pytest.fixture
def mock_store(mock_hass):
    store = HAIRStore(mock_hass)
    store._loaded = True
    return store


@pytest.fixture
def manager(mock_hass, mock_store):
    return TriggerManager(mock_hass, mock_store)


class _FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def monotonic(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


@pytest.fixture
def clock(monkeypatch):
    fake = _FakeClock()
    monkeypatch.setattr("custom_components.hair.trigger_manager.time", fake)
    return fake


# ---------------------------------------------------------------------------
# Fixture reality checks: the Sony collapse this release exists to fix
# ---------------------------------------------------------------------------


class TestSonyFixtures:
    def test_all_buttons_share_sl_fingerprint(self):
        fps = {_fp(code) for code in BUTTONS.values()}
        assert len(fps) == 1, (
            "Sony SIRC pulse widths all classify below PRONTO_SL_THRESHOLD; "
            "if this ever splits, the fixtures or the threshold changed"
        )

    def test_byte_hash_separates_all_buttons(self):
        hashes = {_bh(code) for code in BUTTONS.values()}
        assert len(hashes) == len(BUTTONS)

    def test_byte_hash_stable_across_jitter(self):
        assert _bh(SONY_RED) == _bh(SONY_RED_2)
        assert SONY_RED != SONY_RED_2  # genuinely different captures


# ---------------------------------------------------------------------------
# Trigger cross-fire matrix
# ---------------------------------------------------------------------------


def _add_trigger(store, name, code, byte_hash, min_hits=1):
    trigger = IRTrigger(
        name=name,
        signal_fingerprint=_fp(code),
        protocol="PRONTO",
        code=code,
        min_hits=min_hits,
        byte_hash=byte_hash,
    )
    store.add_trigger(trigger)
    return trigger


class TestCrossFireMatrix:
    def test_scoped_triggers_fire_independently(self, manager, mock_store, clock):
        triggers = {
            name: _add_trigger(mock_store, name, code, _bh(code))
            for name, code in BUTTONS.items()
        }
        for name, code in BUTTONS.items():
            clock.advance(10.0)  # well outside every window
            fired = manager.on_signal_captured(
                _fp(code), "PRONTO", None, None, None, _bh(code)
            )
            assert fired == [triggers[name].id], (
                f"pressing {name} should fire only {name}'s trigger"
            )

    def test_legacy_trigger_fires_on_every_button(self, manager, mock_store, clock):
        legacy = _add_trigger(mock_store, "legacy", SONY_RED, None)
        for code in BUTTONS.values():
            clock.advance(10.0)
            fired = manager.on_signal_captured(
                _fp(code), "PRONTO", None, None, None, _bh(code)
            )
            assert fired == [legacy.id]

    def test_hashless_capture_fires_scoped_trigger(self, manager, mock_store, clock):
        """A capture with no byte_hash (non-Pronto path) still matches a
        scoped trigger: the three-way None rule never hard-fails."""
        scoped = _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        clock.advance(10.0)
        fired = manager.on_signal_captured(
            _fp(SONY_RED), "PRONTO", None, None, None, None
        )
        assert fired == [scoped.id]

    def test_exact_code_branch_gated_by_byte_hash(self, mock_store):
        """The protocol+code exact-match branch in get_triggers_for_signal
        must not bypass the byte_hash rule."""
        _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        matches = mock_store.get_triggers_for_signal(
            "PRONTO", SONY_RED, _fp(SONY_RED), _bh(SONY_GREEN)
        )
        assert matches == []


# ---------------------------------------------------------------------------
# Fire dedup window: one physical press = one fire
# ---------------------------------------------------------------------------


class TestFireDedupWindow:
    def test_sony_auto_repeat_fires_once(self, manager, mock_store, clock):
        """SIRC transmits 4-5 full frames per press ~45ms apart. Five of
        them span 180ms, inside the 250ms window, so one press is one fire.
        (Before the window was widened this relied on the sliding refresh
        to absorb a burst longer than the window; it no longer has to.)"""
        trigger = _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        fired_total = []
        for _ in range(5):
            fired_total += manager.on_signal_captured(
                _fp(SONY_RED), "PRONTO", None, None, None, _bh(SONY_RED)
            )
            clock.advance(0.045)
        assert fired_total == [trigger.id], "one press must fire exactly once"

    def test_jittered_frame_gaps_still_fire_once(self, manager, mock_store, clock):
        """Headroom check: a receiver that delivers Sony's ~45ms frames
        late (70ms apart here) must still read as one press. At the old
        60ms window this fired 4 times."""
        trigger = _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        fired_total = []
        for _ in range(4):
            fired_total += manager.on_signal_captured(
                _fp(SONY_RED), "PRONTO", None, None, None, _bh(SONY_RED)
            )
            clock.advance(0.070)
        assert fired_total == [trigger.id]

    def test_distinct_press_after_quiet_gap_fires_again(
        self, manager, mock_store, clock
    ):
        trigger = _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        args = (_fp(SONY_RED), "PRONTO", None, None, None, _bh(SONY_RED))
        assert manager.on_signal_captured(*args) == [trigger.id]
        clock.advance(1.0)  # human re-press interval
        assert manager.on_signal_captured(*args) == [trigger.id]

    def test_deliberate_double_tap_fires_twice(self, manager, mock_store, clock):
        """The window must stay below a deliberate double-press interval.

        Widened to 250ms by owner ruling 2026-08-18, so the spacing this
        test asserts moved with it: 300ms, comfortably a release and a
        re-press. Taps closer together than 250ms now read as one press,
        which is the deliberate cost of covering handsets that repeat the
        whole frame every 102-119ms while the button is down.
        """
        trigger = _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        args = (_fp(SONY_RED), "PRONTO", None, None, None, _bh(SONY_RED))
        assert manager.on_signal_captured(*args) == [trigger.id]
        clock.advance(0.300)
        assert manager.on_signal_captured(*args) == [trigger.id]

    def test_multi_receiver_legacy_dedup_preserved(
        self, manager, mock_store, clock
    ):
        """Two receivers capture one press and re-encode at their own
        carriers, so their byte_hashes CAN differ (a snap or a different
        reported modulation rescales timing words across bin boundaries).
        A legacy trigger must still fire once, which is why the dedup key
        stays (trigger, fingerprint) and was NOT extended with byte_hash.

        The two hashes below are deliberately different (green stands in for
        "same press, different hash"); if the dedup key ever gains byte_hash,
        this test fails with two fires, which is the v0.5.7 regression the
        plan review caught.
        """
        legacy = _add_trigger(mock_store, "legacy", SONY_RED, None)
        assert _bh(SONY_RED) != _bh(SONY_GREEN)
        fired = manager.on_signal_captured(
            _fp(SONY_RED), "PRONTO", None, None, "infrared.rx_a", _bh(SONY_RED)
        )
        assert fired == [legacy.id]
        clock.advance(0.010)
        fired = manager.on_signal_captured(
            _fp(SONY_RED), "PRONTO", None, None, "infrared.rx_b", _bh(SONY_GREEN)
        )
        assert fired == [], "one physical press must fire a legacy trigger once"


# ---------------------------------------------------------------------------
# Rewire on byte-hash-only edits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRewire:
    async def test_hash_only_edit_repoints_scoped_trigger(
        self, manager, mock_store
    ):
        """Editing Sony code A to code B never changes the S/L fingerprint;
        the trigger must follow the byte_hash."""
        trigger = _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        mock_store.async_save = _async_noop
        result = await manager.rewire(
            _fp(SONY_RED), _fp(SONY_GREEN), "PRONTO", SONY_GREEN,
            old_byte_hash=_bh(SONY_RED), new_byte_hash=_bh(SONY_GREEN),
        )
        assert result["rewired"] == ["red"]
        assert trigger.byte_hash == _bh(SONY_GREEN)
        assert trigger.code == SONY_GREEN

    async def test_sibling_scoped_trigger_not_repointed(
        self, manager, mock_store
    ):
        """A trigger scoped to a DIFFERENT button on the same fingerprint
        is not this edit's signal and must not move."""
        green = _add_trigger(mock_store, "green", SONY_GREEN, _bh(SONY_GREEN))
        mock_store.async_save = _async_noop
        result = await manager.rewire(
            _fp(SONY_RED), _fp(SONY_RED), "PRONTO", SONY_YELLOW,
            old_byte_hash=_bh(SONY_RED), new_byte_hash=_bh(SONY_YELLOW),
        )
        assert result["rewired"] == []
        assert green.byte_hash == _bh(SONY_GREEN)

    async def test_legacy_trigger_promoted_on_rewire(self, manager, mock_store):
        legacy = _add_trigger(mock_store, "legacy", SONY_RED, None)
        mock_store.async_save = _async_noop
        result = await manager.rewire(
            _fp(SONY_RED), _fp(SONY_RED), "PRONTO", SONY_BLUE,
            old_byte_hash=_bh(SONY_RED), new_byte_hash=_bh(SONY_BLUE),
        )
        assert result["rewired"] == ["legacy"]
        assert legacy.byte_hash == _bh(SONY_BLUE)

    async def test_no_op_when_identity_unchanged(self, manager, mock_store):
        _add_trigger(mock_store, "red", SONY_RED, _bh(SONY_RED))
        result = await manager.rewire(
            _fp(SONY_RED), _fp(SONY_RED), "PRONTO", SONY_RED,
            old_byte_hash=_bh(SONY_RED), new_byte_hash=_bh(SONY_RED),
        )
        assert result["rewired"] == []


async def _async_noop(*args, **kwargs):
    return None


# ---------------------------------------------------------------------------
# Backfill + matcher legacy tier
# ---------------------------------------------------------------------------


class TestBackfill:
    def test_backfill_computes_hash_from_pronto_code(self, mock_store):
        cmd = IRCommand(name="Power", protocol="PRONTO", code=SONY_RED)
        assert cmd.byte_hash is None
        mock_store.add_device(IRDevice(name="Fan", commands=[cmd]))
        changed = mock_store._backfill_byte_hash()
        assert changed is True
        assert cmd.byte_hash == _bh(SONY_RED)
        # Idempotent: second run changes nothing.
        assert mock_store._backfill_byte_hash() is False

    def test_codeless_command_stays_legacy_and_matches(self, mock_store):
        """A legacy protocol/code command ("0x1234" style) hashes to None on
        BOTH the command and capture side, so it keeps matching via the
        bare-fingerprint tier after the v0.5.8 restriction."""
        cmd = IRCommand(name="Power", protocol="NEC", code="0x1234")
        dev = IRDevice(name="TV", commands=[cmd])
        mock_store.add_device(dev)
        assert mock_store._backfill_byte_hash() is False
        assert cmd.byte_hash is None
        fp = EventParser.signal_fingerprint("NEC", "0x1234", None)
        incoming_bh = EventParser.pronto_byte_hash("0x1234")
        assert incoming_bh is None
        assert mock_store.match_command(None, fp, incoming_bh) == (
            dev.id, cmd.id,
        )


class TestMatcherSiblings:
    def test_assigned_button_does_not_swallow_siblings(self, mock_store):
        """The loic scenario: assign red, then press green/yellow/blue.
        None of the siblings may match red's command."""
        red_cmd = IRCommand(
            name="Red", protocol="PRONTO", code=SONY_RED,
            byte_hash=_bh(SONY_RED),
        )
        dev = IRDevice(name="Fan", commands=[red_cmd])
        mock_store.add_device(dev)
        fp = _fp(SONY_RED)
        assert mock_store.match_command(None, fp, _bh(SONY_RED)) == (
            dev.id, red_cmd.id,
        )
        for code in (SONY_GREEN, SONY_YELLOW, SONY_BLUE):
            assert mock_store.match_command(None, fp, _bh(code)) is None

    def test_jittered_repress_still_matches(self, mock_store):
        red_cmd = IRCommand(
            name="Red", protocol="PRONTO", code=SONY_RED,
            byte_hash=_bh(SONY_RED),
        )
        dev = IRDevice(name="Fan", commands=[red_cmd])
        mock_store.add_device(dev)
        assert mock_store.match_command(
            None, _fp(SONY_RED_2), _bh(SONY_RED_2)
        ) == (dev.id, red_cmd.id)


# ---------------------------------------------------------------------------
# Repeat suppression keyed by byte_hash (behavioral)
# ---------------------------------------------------------------------------


class TestRepeatSuppressionByteHash:
    """_check_repeat behavioral coverage for the v0.5.8 key change: two
    DIFFERENT sub-threshold buttons within the suppress window both pass;
    the SAME button twice is suppressed."""

    def _monitor(self, fake_hass):
        from custom_components.hair.signal_monitor import SignalMonitor

        store = MagicMock()
        hair = MagicMock()
        return SignalMonitor(fake_hass, store, hair)

    def test_two_buttons_in_quick_succession_both_pass(self, fake_hass):
        monitor = self._monitor(fake_hass)
        fp = _fp(SONY_RED)
        assert monitor._check_repeat(fp, None, _bh(SONY_RED))
        assert monitor._check_repeat(fp, None, _bh(SONY_GREEN)), (
            "green must not read as a repeat of red just because they share "
            "an S/L fingerprint"
        )

    def test_same_button_twice_still_suppressed(self, fake_hass):
        monitor = self._monitor(fake_hass)
        fp = _fp(SONY_RED)
        assert monitor._check_repeat(fp, None, _bh(SONY_RED))
        assert not monitor._check_repeat(fp, None, _bh(SONY_RED))
        # Jittered re-capture of the same button hashes identically, so it
        # is suppressed too.
        assert not monitor._check_repeat(fp, None, _bh(SONY_RED_2))


class TestBlockedLegacyMatchLog:
    def test_debug_log_fires_when_pre_058_tier_would_have_matched(
        self, mock_store, caplog
    ):
        """The support-triage breadcrumb: a hash miss against a hash-bearing
        command logs at DEBUG instead of silently returning None."""
        import logging

        red_cmd = IRCommand(
            name="Red", protocol="PRONTO", code=SONY_RED,
            byte_hash=_bh(SONY_RED),
        )
        mock_store.add_device(IRDevice(name="Fan", commands=[red_cmd]))
        with caplog.at_level(logging.DEBUG, logger="custom_components.hair.storage"):
            result = mock_store.match_command(
                None, _fp(SONY_RED), _bh(SONY_GREEN)
            )
        assert result is None
        assert any(
            "blocked by byte_hash identity" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# WS trigger creation carries the byte_hash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWsCreateTriggerByteHash:
    """The device-detail trigger dialog sends protocol+code AND a source
    command, so the fingerprint resolves before the source-command lookup.
    The byte_hash derive must not hang off `not sig_fp` or every trigger
    created from a command row lands legacy-broad -- the exact bug this
    release exists to fix, on the path a user hits right after assigning.
    """

    async def _create(self, fake_hass, payload):
        from unittest.mock import AsyncMock

        from custom_components.hair.const import DOMAIN
        from custom_components.hair.websocket_api import ws_create_trigger

        cmd = IRCommand(
            id="c1", name="Red", protocol="PRONTO", code=SONY_RED,
            byte_hash=_bh(SONY_RED),
        )
        device = IRDevice(id="d1", name="Fan", commands=[cmd])
        store = HAIRStore(fake_hass)
        store._loaded = True
        store.async_save = AsyncMock()
        dm = MagicMock()
        dm.get_device = MagicMock(return_value=device)
        fake_hass.data[DOMAIN] = {
            "e1": {
                "store": store,
                "device_manager": dm,
                "config_entry": MagicMock(),
            }
        }
        conn = MagicMock()
        await ws_create_trigger(fake_hass, conn, {"id": 1, **payload})
        conn.send_error.assert_not_called()
        return store.get_all_triggers()[0]

    async def test_from_command_row_carries_command_hash(self, fake_hass):
        trigger = await self._create(
            fake_hass,
            {
                "type": "hair/trigger/create",
                "name": "Red",
                # Exactly what ir-device-detail sends: protocol + code +
                # source refs, so sig_fp resolves before the command lookup.
                "protocol": "PRONTO",
                "code": SONY_RED,
                "source_device_id": "d1",
                "source_command_id": "c1",
            },
        )
        assert trigger.byte_hash == _bh(SONY_RED), (
            "trigger created from a command row must inherit its byte_hash"
        )

    async def test_explicit_payload_hash_wins(self, fake_hass):
        trigger = await self._create(
            fake_hass,
            {
                "type": "hair/trigger/create",
                "name": "Green",
                "signal_fingerprint": _fp(SONY_GREEN),
                "byte_hash": _bh(SONY_GREEN),
                "protocol": "PRONTO",
                "code": SONY_GREEN,
            },
        )
        assert trigger.byte_hash == _bh(SONY_GREEN)

    async def test_no_source_and_no_hash_stays_legacy(self, fake_hass):
        """A stale cached frontend omits byte_hash entirely: the trigger
        degrades to legacy-broad (pre-0.5.8 behavior), never a crash."""
        trigger = await self._create(
            fake_hass,
            {
                "type": "hair/trigger/create",
                "name": "Legacy",
                "protocol": "PRONTO",
                "code": SONY_RED,
            },
        )
        assert trigger.byte_hash is None


# ---------------------------------------------------------------------------
# Model unit rows
# ---------------------------------------------------------------------------


class TestTriggerModel:
    @pytest.mark.parametrize(
        ("trigger_bh", "incoming_bh", "expected"),
        [
            (None, None, True),
            (None, "x", True),
            ("x", None, True),
            ("x", "x", True),
            ("x", "y", False),
        ],
    )
    def test_matches_byte_hash(self, trigger_bh, incoming_bh, expected):
        t = IRTrigger(name="t", byte_hash=trigger_bh)
        assert t.matches_byte_hash(incoming_bh) is expected

    def test_from_dict_lazy_migration(self):
        """Pre-0.5.8 records have no byte_hash key; absent and null both
        resolve to None (legacy-broad)."""
        t = IRTrigger.from_dict({"name": "old"})
        assert t.byte_hash is None
        t = IRTrigger.from_dict({"name": "old", "byte_hash": None})
        assert t.byte_hash is None
        t = IRTrigger.from_dict({"name": "new", "byte_hash": "bh"})
        assert t.byte_hash == "bh"

    def test_to_dict_round_trip(self):
        t = IRTrigger(name="t", byte_hash="bh", signal_fingerprint="fp")
        assert IRTrigger.from_dict(t.to_dict()).byte_hash == "bh"
