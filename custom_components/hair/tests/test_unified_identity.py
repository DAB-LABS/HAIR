"""Tests for the v0.5.8 unified signal identity (second half of the release).

Covers the Section 8 matrix from
``docs/internal/plans/unified-signal-identity.md``:
- the tiered rule truth table on ``SignalIdentity`` / ``IRTrigger``,
  including the no-regression invariant (8.1: every pair that matched
  under the byte_hash-only rule still matches),
- tier-2 rescue on the bench's pasted-vs-received Sony flip (8.2),
- tier-1 precedence with a REAL decodable NEC pair whose byte_hashes
  differ (8.3), and tier-1-decides (decoded mismatch is fatal, no
  byte_hash fallthrough),
- tier-3 legacy behavior for hash-less records (8.4),
- the multi-receiver double-fire guard for the trigger_id-only fire
  dedup key (8.5),
- the trigger decoded backfill, decoded-only, with the explicit
  negative assertion that no legacy trigger acquires a byte_hash (8.6),
- Sniffer dedup across threshold flips: one row, not N (8.7),
- match_command's byte_hash-only tier: assigned-command flip rescue and
  the collision corner (8.9),
- the tiered signal_store load-time heal (plan 4.5b),
- rewire stamping and sibling-skip for the decoded identity (plan 4.4).

Fixture provenance: the Sony codes are the loic.gouraud SIRC-15 captures
already used by ``test_bytehash_identity``. RECEIVED_YELLOW is the
pasted Yellow with its sub-threshold long marks (0x2D-0x2F, 45-47 units)
shifted to 48-49 (0x30-0x31) -- the exact flip measured on the bench
2026-07-13, where the same physical code read "S" when pasted and "L"
after a transmit-receive round trip while its byte_hash survived
unchanged. The NEC codes are the test_event_parser remote-1 Power code
(address 0x00, command 0xAA) plus a lead-in-shifted variant (0x159 ->
0x148) that decodes identically but bins differently.
"""
from __future__ import annotations

import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import SignalIdentity, same_signal
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    IRTrigger,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager

# The real NEC decoder ships via infrared-protocols, which requires
# Python 3.13+ (see the pyproject test extra). Tests that exercise the
# decoded tier against REAL decode results skip below that; everything
# byte_hash/fingerprint-tier still runs (mirrors test_protocol_decode's
# importorskip convention, but per-test so the rest of this suite keeps
# covering 3.12).
_needs_nec = pytest.mark.skipif(
    importlib.util.find_spec("infrared_protocols") is None,
    reason="real NEC decoder unavailable (infrared-protocols needs 3.13+)",
)

# --- Sony fixtures (see module docstring) ---

PASTED_YELLOW = (
    "0000 006D 0010 0000 005D 0016 002E 0017 002E 0017 002F 0016 0017 "
    "0017 0017 0017 002E 0017 0018 0016 002E 0017 002E 0017 002F 0016 "
    "0017 0017 002E 0017 0017 0017 0018 0016 002E 0181"
)
# The same button after the transmit->receive round trip: every
# sub-threshold long mark (0x2E/0x2F = 46/47) reads 48/49 (0x30/0x31),
# crossing PRONTO_SL_THRESHOLD (48) -- but staying inside the same
# 20-unit byte_hash bin (30-50 -> 40).
RECEIVED_YELLOW = (
    PASTED_YELLOW.replace("002E", "0030").replace("002F", "0031")
)

SONY_GREEN = (
    "0000 006D 0010 0000 005C 0018 0016 0018 002D 0018 002D 0018 0016 "
    "0018 0016 0018 002D 0018 0016 0017 002E 0018 002D 0018 002D 0018 "
    "0016 0018 002D 0018 0016 0017 0017 0018 002D 0181"
)

# --- NEC fixtures (decode to NEC:0xff00:0xaa with the real library) ---

_NEC_BODY = (
    " 0016 0016 0016 0016 0016 0016 0016 0016"
    " 0016 0016 0016 0016 0016 0016 0016 0016"
    " 0016 0042 0016 0042 0016 0042 0016 0042"
    " 0016 0042 0016 0042 0016 0042 0016 0042"
    " 0016 0016 0016 0042 0016 0016 0016 0042"
    " 0016 0016 0016 0042 0016 0016 0016 0042"
    " 0016 0042 0016 0016 0016 0042 0016 0016"
    " 0016 0042 0016 0016 0016 0042 0016 0016"
    " 0016 0BBA"
)
NEC_POWER = "0000 006D 0022 0000 0159 00AC" + _NEC_BODY
# Lead-in mark shifted 0x159 (345 units, bin 340) -> 0x148 (328 units,
# bin 320): decodes to the same NEC identity, different byte_hash.
NEC_POWER_LEADSHIFT = "0000 006D 0022 0000 0148 00AC" + _NEC_BODY


def _fp(code: str) -> str:
    return EventParser.signal_fingerprint("PRONTO", code, None)


def _bh(code: str) -> str:
    bh = EventParser.pronto_byte_hash(code)
    assert bh is not None
    return bh


def _decoded(code: str) -> str:
    from custom_components.hair.ir_command import ProntoCommand
    from custom_components.hair.protocol_decode import decode_to_fields

    _, _, _, fingerprint = decode_to_fields(
        ProntoCommand(code).get_raw_timings()
    )
    assert fingerprint is not None
    return fingerprint


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


def _trigger(code, byte_hash=None, decoded=None, name="t", **kw):
    return IRTrigger(
        name=name,
        signal_fingerprint=_fp(code),
        protocol="PRONTO",
        code=code,
        byte_hash=byte_hash,
        decoded_fingerprint=decoded,
        **kw,
    )


# ---------------------------------------------------------------------------
# Fixture reality checks: the bench flip, reproduced from real captures
# ---------------------------------------------------------------------------


class TestFlipFixtures:
    def test_fingerprint_flips_across_threshold(self):
        assert _fp(PASTED_YELLOW) != _fp(RECEIVED_YELLOW), (
            "the received copy's long marks crossed PRONTO_SL_THRESHOLD; "
            "if the fingerprints agree, the fixtures or the threshold moved"
        )

    def test_byte_hash_survives_the_flip(self):
        assert _bh(PASTED_YELLOW) == _bh(RECEIVED_YELLOW), (
            "45-49 units all quantize to the 40 bin; the byte_hash is the "
            "identity layer the flip cannot break"
        )

    @_needs_nec
    def test_nec_pair_decodes_identically_with_different_hashes(self):
        assert _decoded(NEC_POWER) == _decoded(NEC_POWER_LEADSHIFT) == (
            "NEC:0xff00:0xaa"
        )
        assert _bh(NEC_POWER) != _bh(NEC_POWER_LEADSHIFT)
        assert _fp(NEC_POWER) == _fp(NEC_POWER_LEADSHIFT)


# ---------------------------------------------------------------------------
# The tiered rule truth table (8.1, 8.3, 8.4)
# ---------------------------------------------------------------------------


class TestTieredRule:
    def test_tier1_decides_despite_lower_tier_mismatch(self):
        """Decoded equality matches even when byte_hash AND fingerprint
        differ -- this is how the upstream Sony decoder takes over with
        zero further HAIR changes."""
        a = SignalIdentity("NEC:0xff00:0xaa", "bh1", "fp1")
        b = SignalIdentity("NEC:0xff00:0xaa", "bh2", "fp2")
        assert a.match_tier(b) == 1

    def test_tier1_mismatch_is_fatal_no_byte_hash_fallthrough(self):
        """When both sides decode, the decode decides -- period. A shared
        byte_hash (the RC-6 bin-share shape) must not resurrect the match."""
        a = SignalIdentity("NEC:0xff00:0xaa", "bh1", "fp1")
        b = SignalIdentity("NEC:0xff00:0x55", "bh1", "fp1")
        assert a.match_tier(b) is None

    def test_tier2_rescues_fingerprint_flip(self):
        a = SignalIdentity(None, "bh1", "fp_pasted")
        b = SignalIdentity(None, "bh1", "fp_received")
        assert a.match_tier(b) == 2

    def test_tier2_mismatch_is_fatal_no_fingerprint_fallthrough(self):
        """Sony siblings: same fingerprint, different hash -- the v0.5.8
        byte_hash rule, preserved."""
        a = SignalIdentity(None, "bh_red", "fp")
        b = SignalIdentity(None, "bh_green", "fp")
        assert a.match_tier(b) is None

    def test_tier3_legacy_fingerprint_only(self):
        assert SignalIdentity(None, None, "fp").match_tier(
            SignalIdentity(None, None, "fp")
        ) == 3
        assert SignalIdentity(None, None, "fp1").match_tier(
            SignalIdentity(None, None, "fp2")
        ) is None

    def test_missing_tier_is_skipped_not_fatal(self):
        """One-sided layers fall through: hash vs hash-less lands on the
        fingerprint, decoded vs undecoded lands on the hash."""
        assert SignalIdentity(None, "bh", "fp").match_tier(
            SignalIdentity(None, None, "fp")
        ) == 3
        assert SignalIdentity("NEC:0x1:0x2", "bh", "fp1").match_tier(
            SignalIdentity(None, "bh", "fp2")
        ) == 2

    def test_empty_fingerprints_never_match(self):
        assert SignalIdentity(None, None, "").match_tier(
            SignalIdentity(None, None, "")
        ) is None

    def test_same_signal_functional_form(self):
        assert same_signal(None, "bh", "fp1", None, "bh", "fp2")
        assert not same_signal(None, "bh1", "fp", None, "bh2", "fp")

    def test_no_regression_invariant(self):
        """8.1: every pair that matched under the byte_hash-only rule (fp
        equal + three-way byte_hash) still matches under the tiered rule.
        Neither side carries a decoded identity here, exactly as under the
        old rule."""
        fp = "fp"
        matched_under_v058 = [
            (None, None),        # legacy trigger, hash-less capture
            (None, "bh"),        # legacy trigger, hashed capture
            ("bh", None),        # scoped trigger, hash-less capture
            ("bh", "bh"),        # scoped trigger, matching capture
        ]
        for t_bh, s_bh in matched_under_v058:
            t = _trigger(PASTED_YELLOW, byte_hash=t_bh)
            t.signal_fingerprint = fp
            assert t.matches_signal(fp, s_bh, None), (
                f"pair (trigger={t_bh}, signal={s_bh}) matched under the "
                "byte_hash-only rule and must keep matching"
            )
        # And the one rejection the old rule made is preserved:
        t = _trigger(PASTED_YELLOW, byte_hash="bh_red")
        t.signal_fingerprint = fp
        assert not t.matches_signal(fp, "bh_green", None)


# ---------------------------------------------------------------------------
# Trigger rescue across the flip (8.2), via the real store path
# ---------------------------------------------------------------------------


class TestTriggerFlipRescue:
    def test_scoped_trigger_fires_on_flipped_capture(self, manager, mock_store, clock):
        t = _trigger(PASTED_YELLOW, byte_hash=_bh(PASTED_YELLOW), name="yellow")
        mock_store.add_trigger(t)
        clock.advance(10.0)
        fired = manager.on_signal_captured(
            _fp(RECEIVED_YELLOW), "PRONTO", None, None, None,
            _bh(RECEIVED_YELLOW),
        )
        assert fired == [t.id], (
            "the received copy crossed the S/L threshold; byte_hash must "
            "carry the match (this is the 2-of-4 bench failure)"
        )

    def test_sibling_still_silent_across_flip(self, manager, mock_store, clock):
        t = _trigger(PASTED_YELLOW, byte_hash=_bh(PASTED_YELLOW), name="yellow")
        mock_store.add_trigger(t)
        clock.advance(10.0)
        fired = manager.on_signal_captured(
            _fp(SONY_GREEN), "PRONTO", None, None, None, _bh(SONY_GREEN)
        )
        assert fired == []

    @_needs_nec
    def test_tier1_trigger_fires_across_hash_change(self, manager, mock_store, clock):
        """The decoder-takeover path: a trigger with a decoded identity
        fires on a capture that decodes the same, even though jitter moved
        the byte_hash across a bin edge."""
        t = _trigger(
            NEC_POWER, byte_hash=_bh(NEC_POWER), decoded=_decoded(NEC_POWER),
            name="power",
        )
        mock_store.add_trigger(t)
        clock.advance(10.0)
        fired = manager.on_signal_captured(
            _fp(NEC_POWER_LEADSHIFT), "PRONTO", None, None, None,
            _bh(NEC_POWER_LEADSHIFT), _decoded(NEC_POWER_LEADSHIFT),
        )
        assert fired == [t.id]

    def test_legacy_trigger_unchanged(self, manager, mock_store, clock):
        """A legacy trigger still matches on bare fingerprint equality --
        and does NOT match a flipped fingerprint (it carries no byte-level
        identity to be rescued by; pre-upgrade behavior, preserved)."""
        t = _trigger(PASTED_YELLOW, byte_hash=None, name="legacy")
        mock_store.add_trigger(t)
        clock.advance(10.0)
        assert manager.on_signal_captured(
            _fp(PASTED_YELLOW), "PRONTO", None, None, None, None
        ) == [t.id]
        clock.advance(10.0)
        assert manager.on_signal_captured(
            _fp(RECEIVED_YELLOW), "PRONTO", None, None, None,
            _bh(RECEIVED_YELLOW),
        ) == []


# ---------------------------------------------------------------------------
# Multi-receiver double-fire guard (8.5)
# ---------------------------------------------------------------------------


class TestMultiReceiverFlipDedup:
    def test_one_press_two_receivers_different_fingerprints_one_fire(
        self, manager, mock_store, clock
    ):
        """One physical press; receiver A reads the marks below the S/L
        threshold, receiver B above (DIFFERENT fingerprints). Both match
        via byte_hash. The trigger_id-keyed dedup must collapse them to
        exactly ONE fire -- a fingerprint-qualified key would fire twice.
        Without the key change this test fails."""
        t = _trigger(PASTED_YELLOW, byte_hash=_bh(PASTED_YELLOW), name="yellow")
        mock_store.add_trigger(t)
        clock.advance(10.0)
        fired_a = manager.on_signal_captured(
            _fp(PASTED_YELLOW), "PRONTO", None, None,
            "infrared.receiver_a", _bh(PASTED_YELLOW),
        )
        clock.advance(0.030)  # inside MULTI_RECEIVER_DEDUP_WINDOW_S
        fired_b = manager.on_signal_captured(
            _fp(RECEIVED_YELLOW), "PRONTO", None, None,
            "infrared.receiver_b", _bh(RECEIVED_YELLOW),
        )
        assert fired_a == [t.id]
        assert fired_b == []

    def test_distinct_presses_still_fire_separately(
        self, manager, mock_store, clock
    ):
        t = _trigger(PASTED_YELLOW, byte_hash=_bh(PASTED_YELLOW), name="yellow")
        mock_store.add_trigger(t)
        clock.advance(10.0)
        assert manager.on_signal_captured(
            _fp(PASTED_YELLOW), "PRONTO", None, None, None, _bh(PASTED_YELLOW)
        ) == [t.id]
        clock.advance(1.0)  # a real re-press, far outside the window
        assert manager.on_signal_captured(
            _fp(PASTED_YELLOW), "PRONTO", None, None, None, _bh(PASTED_YELLOW)
        ) == [t.id]


# ---------------------------------------------------------------------------
# Sniffer dedup across flips (8.7) + tiered-passes order independence
# ---------------------------------------------------------------------------


class TestSnifferFlipDedup:
    def test_flipped_capture_lands_on_existing_row(self):
        dev = UnknownDevice()
        row = UnknownSignal(
            fingerprint=_fp(PASTED_YELLOW),
            byte_hash=_bh(PASTED_YELLOW),
            protocol="PRONTO",
            code=PASTED_YELLOW,
        )
        dev.signals.append(row)
        found = dev.get_signal(
            _fp(RECEIVED_YELLOW), _bh(RECEIVED_YELLOW), None
        )
        assert found is row, (
            "alternating threshold flips must produce ONE row with "
            "incrementing hits, not a new row per flip"
        )

    def test_siblings_stay_distinct(self):
        dev = UnknownDevice()
        yellow = UnknownSignal(
            fingerprint=_fp(PASTED_YELLOW), byte_hash=_bh(PASTED_YELLOW)
        )
        dev.signals.append(yellow)
        assert dev.get_signal(_fp(SONY_GREEN), _bh(SONY_GREEN), None) is None

    def test_tiered_passes_beat_insertion_order(self):
        """A decode-failed row sitting ABOVE its decoded sibling must not
        absorb an incoming capture via tier 2 before the sibling's tier-1
        match is considered (strongest-match-wins, not first-match-wins)."""
        dev = UnknownDevice()
        decode_failed = UnknownSignal(
            fingerprint="fp_a", byte_hash="bh_shared", decoded_fingerprint=None
        )
        decoded_row = UnknownSignal(
            fingerprint="fp_b", byte_hash="bh_shared",
            decoded_fingerprint="NEC:0xff00:0xaa",
        )
        dev.signals.extend([decode_failed, decoded_row])
        found = dev.get_signal("fp_c", "bh_shared", "NEC:0xff00:0xaa")
        assert found is decoded_row

    def test_bare_fingerprint_lookup_unchanged(self):
        dev = UnknownDevice()
        row = UnknownSignal(fingerprint="fp")
        dev.signals.append(row)
        assert dev.get_signal("fp") is row
        assert dev.get_signal("other") is None


# ---------------------------------------------------------------------------
# Trigger backfill: decoded only, NEVER byte_hash (8.6)
# ---------------------------------------------------------------------------


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@_needs_nec
@pytest.mark.asyncio
async def test_trigger_backfill_decoded_only(mock_hass):
    """A pre-upgrade trigger with a stored decodable code gains
    decoded_fingerprint at load; its byte_hash stays None (deliberately NOT
    backfilled -- a recomputed hash could mismatch live captures and a
    tier-2 miss is fatal). A codeless trigger stays fully legacy."""
    backing = _FakeStore()
    backing._data = {
        "devices": [],
        "triggers": [
            {
                "id": "t_nec",
                "name": "NEC legacy",
                "signal_fingerprint": _fp(NEC_POWER),
                "protocol": "PRONTO",
                "code": NEC_POWER,
            },
            {
                "id": "t_sony",
                "name": "Sony legacy",
                "signal_fingerprint": _fp(PASTED_YELLOW),
                "protocol": "PRONTO",
                "code": PASTED_YELLOW,
            },
            {
                "id": "t_codeless",
                "name": "codeless",
                "signal_fingerprint": "some_fp",
            },
        ],
    }
    with patch(
        "custom_components.hair.storage._HAIRDeviceStore",
        lambda *a, **k: backing,
    ):
        store = HAIRStore(mock_hass)
        await store.async_load()

    t_nec = store.get_trigger("t_nec")
    assert t_nec.decoded_fingerprint == "NEC:0xff00:0xaa"
    # v0.6.0: the local SIRC decoder reads the real captured Sony fixture,
    # so the legacy Sony trigger now gains tier-1 identity at load too
    # (through v0.5.8 this asserted None -- "no Sony decoder yet").
    t_sony = store.get_trigger("t_sony")
    assert t_sony.decoded_fingerprint == "SONY15:0x0097:0x27"
    t_codeless = store.get_trigger("t_codeless")
    assert t_codeless.decoded_fingerprint is None
    # The explicit negative assertion: the backfill must not have given
    # ANY trigger a byte_hash.
    for t in store.get_all_triggers():
        assert t.byte_hash is None, (
            f"trigger {t.id} acquired a byte_hash at load; the backfill "
            "must be decoded-only or snapped legacy triggers go silent"
        )
    # And the backfilled legacy NEC trigger keeps its broad tier-3
    # matching for hash-bearing captures that fail to decode.
    matches = store.get_triggers_for_signal(
        None, None, _fp(NEC_POWER), "some_hash", None
    )
    assert t_nec in matches


# ---------------------------------------------------------------------------
# match_command: the assigned-command flip rescue (8.9)
# ---------------------------------------------------------------------------


class TestMatchCommandFlipRescue:
    def _store_with_command(self, mock_hass, byte_hash, decoded=None):
        store = HAIRStore(mock_hass)
        store._loaded = True
        dev = IRDevice(
            id="d1",
            name="TV",
            commands=[
                IRCommand(
                    id="c1",
                    name="Yellow",
                    protocol="PRONTO",
                    code=PASTED_YELLOW,
                    byte_hash=byte_hash,
                    decoded_fingerprint=decoded,
                )
            ],
        )
        store.add_device(dev)
        return store

    def test_flipped_capture_matches_assigned_command(self, mock_hass):
        """The command-side half of the flip fix: a re-press that landed on
        the other side of the S/L threshold still resolves to its assigned
        command, so it is suppressed from the live feed instead of refiling
        as a brand-new unknown."""
        store = self._store_with_command(mock_hass, _bh(PASTED_YELLOW))
        ref = store.match_command(
            None, _fp(RECEIVED_YELLOW), _bh(RECEIVED_YELLOW)
        )
        assert ref == ("d1", "c1")

    def test_sibling_hash_still_blocked(self, mock_hass):
        store = self._store_with_command(mock_hass, _bh(PASTED_YELLOW))
        assert store.match_command(
            None, _fp(SONY_GREEN), _bh(SONY_GREEN)
        ) is None

    def test_hash_collision_is_last_write_wins(self, mock_hass):
        """Two commands sharing a byte_hash (RC-6 bin-share corner): the
        hash-only tier keeps the later one; documented, DEBUG-logged, and
        must not crash. The composite tier still resolves each command
        exactly at its own (fingerprint, hash)."""
        store = HAIRStore(mock_hass)
        store._loaded = True
        dev = IRDevice(
            id="d1",
            name="TV",
            commands=[
                IRCommand(
                    id="c1", name="A", protocol="PRONTO",
                    code=PASTED_YELLOW, byte_hash="bh_shared",
                ),
                IRCommand(
                    id="c2", name="B", protocol="PRONTO",
                    code=RECEIVED_YELLOW, byte_hash="bh_shared",
                ),
            ],
        )
        store.add_device(dev)
        # Exact composite lookups stay precise.
        assert store.match_command(
            None, _fp(PASTED_YELLOW), "bh_shared"
        ) == ("d1", "c1")
        assert store.match_command(
            None, _fp(RECEIVED_YELLOW), "bh_shared"
        ) == ("d1", "c2")
        # A third fingerprint resolves via the hash-only tier to the
        # last-indexed command.
        assert store.match_command(None, "fp_other", "bh_shared") == ("d1", "c2")


# ---------------------------------------------------------------------------
# signal_store load-time heal, tiered (plan 4.5b)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signal_store_heals_flip_duplicates(mock_hass):
    """Sony flip-duplicates already in a user's catalog (same byte_hash,
    DIFFERENT fingerprint -- exactly what the pre-unified runtime dedup
    minted) merge at load: hit counts sum, the older row and its alias
    survive."""
    from custom_components.hair.signal_store import SignalStore

    store = SignalStore(mock_hass)
    raw = {
        "devices": [
            {
                "id": "u1",
                "fingerprint": "DEV1",
                "label": "Sony Remote",
                "signals": [
                    {
                        "id": "s1",
                        "fingerprint": _fp(PASTED_YELLOW),
                        "byte_hash": _bh(PASTED_YELLOW),
                        "protocol": "PRONTO",
                        "code": PASTED_YELLOW,
                        "hit_count": 5,
                        "alias": "Yellow",
                        "last_seen": "2026-07-01T00:00:00+00:00",
                    },
                    {
                        "id": "s2",
                        "fingerprint": _fp(RECEIVED_YELLOW),
                        "byte_hash": _bh(RECEIVED_YELLOW),
                        "protocol": "PRONTO",
                        "code": RECEIVED_YELLOW,
                        "hit_count": 3,
                        "last_seen": "2026-07-02T00:00:00+00:00",
                    },
                    {
                        "id": "s3",
                        "fingerprint": _fp(SONY_GREEN),
                        "byte_hash": _bh(SONY_GREEN),
                        "protocol": "PRONTO",
                        "code": SONY_GREEN,
                        "hit_count": 7,
                    },
                ],
            }
        ]
    }
    # Load through the public path with the backing store stubbed.
    store._store = MagicMock()

    async def _load():
        return raw

    store._store.async_load = _load
    store._store.async_save = MagicMock()
    await store.async_load()

    devices = store.get_all_devices()
    assert len(devices) == 1
    signals = devices[0].signals
    assert len(signals) == 2, "flip-duplicates must heal; siblings must not"
    healed = next(s for s in signals if s.id == "s1")
    assert healed.hit_count == 8  # 5 + 3
    assert healed.alias == "Yellow"
    assert healed.last_seen == "2026-07-02T00:00:00+00:00"
    assert any(s.id == "s3" for s in signals)


# ---------------------------------------------------------------------------
# Rewire: decoded stamping and the decoded sibling-skip (plan 4.4)
# ---------------------------------------------------------------------------


class TestRewireDecoded:
    @_needs_nec
    @pytest.mark.asyncio
    async def test_rewire_stamps_decoded_identity(self, manager, mock_store):
        t = _trigger(NEC_POWER, byte_hash=None, decoded=None, name="legacy")
        mock_store.add_trigger(t)
        result = await manager.rewire(
            _fp(NEC_POWER), _fp(NEC_POWER_LEADSHIFT), "PRONTO",
            NEC_POWER_LEADSHIFT,
            old_byte_hash=None,
            new_byte_hash=_bh(NEC_POWER_LEADSHIFT),
            old_decoded_fingerprint=None,
            new_decoded_fingerprint=_decoded(NEC_POWER_LEADSHIFT),
        )
        assert result["rewired"] == ["legacy"]
        assert t.decoded_fingerprint == "NEC:0xff00:0xaa"
        assert t.byte_hash == _bh(NEC_POWER_LEADSHIFT)

    @pytest.mark.asyncio
    async def test_rewire_skips_decoded_sibling(self, manager, mock_store):
        """A trigger bound to a DIFFERENT decoded identity that merely
        shares the S/L fingerprint is not this edit's signal."""
        t = _trigger(
            NEC_POWER, byte_hash=None, decoded="NEC:0xff00:0x55", name="other"
        )
        mock_store.add_trigger(t)
        result = await manager.rewire(
            _fp(NEC_POWER), "fp_new", "PRONTO", "0000 006D ...",
            old_byte_hash=None,
            new_byte_hash="bh_new",
            old_decoded_fingerprint="NEC:0xff00:0xaa",
            new_decoded_fingerprint=None,
        )
        assert result["rewired"] == []
        assert t.decoded_fingerprint == "NEC:0xff00:0x55"

    @pytest.mark.asyncio
    async def test_decoded_only_change_triggers_rewire(self, manager, mock_store):
        """The no-op guard must consider all three identity components."""
        t = _trigger(NEC_POWER, byte_hash=None, decoded=None, name="legacy")
        mock_store.add_trigger(t)
        result = await manager.rewire(
            _fp(NEC_POWER), _fp(NEC_POWER), "PRONTO", NEC_POWER,
            old_byte_hash=None,
            new_byte_hash=None,
            old_decoded_fingerprint=None,
            new_decoded_fingerprint="NEC:0xff00:0xaa",
        )
        assert result["rewired"] == ["legacy"]
        assert t.decoded_fingerprint == "NEC:0xff00:0xaa"


# ---------------------------------------------------------------------------
# Repeat suppression across the flip
# ---------------------------------------------------------------------------


class TestCheckRepeatFlip:
    def _monitor(self, mock_hass):
        from custom_components.hair.signal_monitor import SignalMonitor

        store = MagicMock()
        return SignalMonitor(mock_hass, store, MagicMock())

    def test_flip_frames_suppress_each_other(self, mock_hass):
        """Two frames of one press whose fingerprints flipped still share a
        strongest key (the byte_hash), so the second is suppressed."""
        mon = self._monitor(mock_hass)
        assert mon._check_repeat(
            _fp(PASTED_YELLOW), None, _bh(PASTED_YELLOW), None
        )
        assert not mon._check_repeat(
            _fp(RECEIVED_YELLOW), None, _bh(RECEIVED_YELLOW), None
        )

    def test_different_buttons_not_suppressed(self, mock_hass):
        mon = self._monitor(mock_hass)
        assert mon._check_repeat(
            _fp(PASTED_YELLOW), None, _bh(PASTED_YELLOW), None
        )
        assert mon._check_repeat(
            _fp(SONY_GREEN), None, _bh(SONY_GREEN), None
        )
