"""Sticky filing: an existing signal never moves (0.10.2).

Decode-first changed the key a NEW capture is filed under. It must not
change where a signal the catalog already holds lives, or an upgrade
would rearrange remotes the user has already named and arranged. So
before a capture is filed under its computed key, the store is asked
whether this signal already exists anywhere; if it does, the capture
joins its existing row, in its existing group, and nothing else moves.

The two fixtures are the real Arris and candle captures from
``test_grouping.py``: the candle decodes and the Arris does not, so
between them they cover both filing branches.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.models import UnknownDevice, UnknownSignal
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.signal_monitor import SignalMonitor, normalize
from custom_components.hair.signal_store import SignalStore

FIXTURES = Path(__file__).parent / "fixtures" / "grouping"
RECEIVER = "sensor.rx_bench"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def arris() -> dict:
    return _load("arris-power-air.json")


@pytest.fixture
def candle() -> dict:
    return _load("candle-on-air.json")


class _Parsed:
    """The minimal shape ``normalize()`` reads off a capture."""

    def __init__(self, sig: dict) -> None:
        self.protocol = sig["protocol"]
        self.code = sig["code"]
        self.raw_timings = sig["raw_timings"]
        self.frequency = sig.get("frequency") or 38000


class _FakeReceivedSignal:
    """Minimal stand-in for ``InfraredReceivedSignal``."""

    def __init__(self, timings: list[int], modulation: int = 38000) -> None:
        self.timings = timings
        self.modulation = modulation


def _make_hass():
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_later = MagicMock(return_value=MagicMock())
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda fn, *a: fn(*a)
    )
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=MagicMock())
    hass.bus.async_fire = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=MagicMock())
    return hass


def _make_hair_store():
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.get_device = MagicMock(return_value=None)
    hair_store.async_save = AsyncMock()
    hair_store.match_command = MagicMock(return_value=None)
    return hair_store


def _make_monitor(hass):
    store = SignalStore(hass)
    store._loaded = True
    store.async_save = AsyncMock()
    monitor = SignalMonitor(hass, store, _make_hair_store())
    # Rate limit and repeat suppression are per-press timing guards and
    # would eat the second press of a two-press test. They have their own
    # tests; here they are noise.
    monitor._check_rate_limit = lambda *_a, **_k: True
    monitor._check_repeat = lambda *_a, **_k: True
    return store, monitor


async def _press(monitor, hass, sig: dict, receiver: str = RECEIVER):
    """One press of a fixture capture, all the way through the pipeline."""
    received = _FakeReceivedSignal(
        timings=list(sig["raw_timings"]),
        modulation=sig.get("frequency") or 38000,
    )
    monitor._on_received_signal(received, receiver)
    if hass.async_create_task.called:
        coro = hass.async_create_task.call_args[0][0]
        if hasattr(coro, "__await__"):
            await coro
        hass.async_create_task.reset_mock()


def _existing_row(store, sig: dict, group_key: str, alias: str = "On"):
    """Seed the catalog with this capture already filed under an OLD key.

    The group key is deliberately not the one today's rules compute, so
    every test below is asking the real question: does the press follow
    the row, or does it follow the key?
    """
    n = normalize(_Parsed(sig))
    assert group_key != n.dev_fp, "the stale key must differ, or nothing is proved"
    row = UnknownSignal(
        fingerprint=n.sig_fp,
        byte_hash=n.byte_hash,
        decoded_protocol=n.decoded_protocol,
        decoded_address=n.decoded_address,
        decoded_command=n.decoded_command,
        decoded_fingerprint=n.decoded_fingerprint,
        protocol=sig["protocol"],
        code=sig["code"],
        raw_timings=list(sig["raw_timings"]),
        frequency=sig.get("frequency") or 38000,
        alias=alias,
        hit_count=5,
    )
    device = UnknownDevice(
        fingerprint=group_key,
        label="Amazon Candles",
        source="sniffed",
        signals=[row],
        hit_count=5,
    )
    store.add_device(device)
    store.rebuild_signal_index()
    return device, row


# --------------------------------------------------------------- the rule


class TestExistingSignalsStayPut:
    @pytest.mark.asyncio
    async def test_re_press_lands_on_the_existing_row(self, candle):
        """The press follows the ROW, not the newly computed key."""
        hass = _make_hass()
        store, monitor = _make_monitor(hass)
        device, row = _existing_row(store, candle, "21ea38549b5f3a60")

        await _press(monitor, hass, candle)

        assert store.device_count == 1
        assert store.get_all_devices()[0] is device
        assert device.fingerprint == "21ea38549b5f3a60"
        assert len(device.signals) == 1
        assert device.signals[0] is row
        assert row.hit_count == 6
        assert row.alias == "On"

    @pytest.mark.asyncio
    async def test_a_dismissed_group_still_collects(self, candle):
        """Hidden is not disconnected, and it is still not a new card."""
        hass = _make_hass()
        store, monitor = _make_monitor(hass)
        device, row = _existing_row(store, candle, "21ea38549b5f3a60")
        store.add_dismissed(device.fingerprint)

        await _press(monitor, hass, candle)

        assert store.device_count == 1
        assert len(device.signals) == 1
        assert row.hit_count == 6
        # Dismissed still means dismissed: nothing reached the live feed.
        fired = [c.args[0] for c in hass.bus.async_fire.call_args_list]
        assert "hair_signal_detected" not in fired

    @pytest.mark.asyncio
    async def test_no_duplicate_across_a_restart(self, candle):
        """The index is in memory, so a restart has to rebuild it."""
        hass = _make_hass()
        store, monitor = _make_monitor(hass)
        _existing_row(store, candle, "21ea38549b5f3a60")
        await _press(monitor, hass, candle)
        payload = store._serialize()

        # Restart: a fresh store loads that payload from disk.
        hass2 = _make_hass()
        store2, monitor2 = _make_monitor(hass2)
        store2._store = MagicMock()
        store2._store.async_load = AsyncMock(return_value=payload)
        await store2.async_load()
        assert store2.device_count == 1

        await _press(monitor2, hass2, candle)

        assert store2.device_count == 1
        device = store2.get_all_devices()[0]
        assert device.fingerprint == "21ea38549b5f3a60"
        assert len(device.signals) == 1
        assert device.signals[0].hit_count == 7
        assert device.signals[0].alias == "On"


class TestNewSignalsFileUnderTheNewRule:
    @pytest.mark.asyncio
    async def test_undecoded_signal_files_under_the_raw_key(self, arris):
        """The Arris does not decode, so it keeps the raw-preamble key."""
        hass = _make_hass()
        store, monitor = _make_monitor(hass)
        assert try_decode_identity(arris["raw_timings"]) is None

        await _press(monitor, hass, arris)

        assert store.device_count == 1
        device = store.get_all_devices()[0]
        assert device.fingerprint == normalize(_Parsed(arris)).dev_fp
        assert len(device.signals) == 1
        assert device.signals[0].hit_count == 1

    @pytest.mark.asyncio
    async def test_decoded_signal_mints_an_identity_keyed_card(self, candle):
        """The candle decodes, so its card is keyed on the decoded
        identity and not on the carrier plus two characters of preamble
        it used to share with the Arris."""
        hass = _make_hass()
        store, monitor = _make_monitor(hass)
        identity = try_decode_identity(candle["raw_timings"])
        assert identity is not None

        await _press(monitor, hass, candle)

        assert store.device_count == 1
        device = store.get_all_devices()[0]
        assert device.fingerprint == normalize(_Parsed(candle)).dev_fp
        assert device.label
        assert len(device.signals) == 1

    @pytest.mark.asyncio
    async def test_two_new_signals_do_not_collide(self, arris, candle):
        """The collision item 4 was filed for, on the filing path.

        Both captures used to key on carrier 006D plus preamble "SS" and
        the Arris landed on the Amazon Candles card. As two genuinely new
        signals they now get a card each.
        """
        hass = _make_hass()
        store, monitor = _make_monitor(hass)

        await _press(monitor, hass, candle)
        await _press(monitor, hass, arris)

        assert store.device_count == 2
        keys = {d.fingerprint for d in store.get_all_devices()}
        assert len(keys) == 2
        for device in store.get_all_devices():
            assert len(device.signals) == 1


class TestDeleteIsTheUserControlledRefile:
    @pytest.mark.asyncio
    async def test_delete_then_re_press_files_fresh(self, candle):
        """Deleted is gone: the next press files under the current rules.

        This is the one route a user has to move a signal out of a group
        the old key put it in, and it is deliberate.
        """
        hass = _make_hass()
        store, monitor = _make_monitor(hass)
        device, row = _existing_row(store, candle, "21ea38549b5f3a60")
        await _press(monitor, hass, candle)
        assert device.signals[0] is row

        result = await monitor.delete_signal(device.id, row.id)
        assert result["success"] is True
        assert store.device_count == 0

        await _press(monitor, hass, candle)

        assert store.device_count == 1
        fresh = store.get_all_devices()[0]
        assert fresh.fingerprint == normalize(_Parsed(candle)).dev_fp
        assert fresh.fingerprint != "21ea38549b5f3a60"
        assert len(fresh.signals) == 1
        assert fresh.signals[0].hit_count == 1
        assert not fresh.signals[0].alias


class TestTheIndexItself:
    def test_the_mirror_is_never_indexed(self, candle):
        """HAIR's log of its own sends must not adopt a human press."""
        from custom_components.hair.const import MIRROR_DEVICE_FP
        from custom_components.hair.identity import SignalIdentity

        hass = _make_hass()
        store = SignalStore(hass)
        store._loaded = True
        n = normalize(_Parsed(candle))
        row = UnknownSignal(
            fingerprint=n.sig_fp,
            byte_hash=n.byte_hash,
            decoded_fingerprint=n.decoded_fingerprint,
        )
        store.add_device(UnknownDevice(
            fingerprint=MIRROR_DEVICE_FP, source="echo", signals=[row],
        ))
        store.rebuild_signal_index()

        found = store.find_filed_signal(
            SignalIdentity(n.decoded_fingerprint, n.byte_hash, n.sig_fp)
        )
        assert found is None

    def test_a_decoded_mismatch_is_not_rescued_by_the_byte_hash(self):
        """Tier precedence is the shared rule, not a key-order accident."""
        from custom_components.hair.identity import SignalIdentity

        hass = _make_hass()
        store = SignalStore(hass)
        store._loaded = True
        row = UnknownSignal(
            fingerprint="SLSL",
            byte_hash="same-hash",
            decoded_fingerprint="NEC:0x0001:0x02",
        )
        store.add_device(UnknownDevice(
            fingerprint="g1", source="sniffed", signals=[row],
        ))
        store.rebuild_signal_index()

        assert store.find_filed_signal(
            SignalIdentity("NEC:0x00FF:0x02", "same-hash", "SLSL")
        ) is None
        assert store.find_filed_signal(
            SignalIdentity("NEC:0x0001:0x02", "same-hash", "SLSL")
        ) is not None
        # A capture that decoded to nothing still matches on the hash.
        assert store.find_filed_signal(
            SignalIdentity(None, "same-hash", "SLSL")
        ) is not None

    def test_an_evicted_row_leaves_the_index(self):
        """A capped-out row must not keep claiming its old group."""
        from custom_components.hair.const import SIGNAL_MAX_SIGNALS_PER_DEVICE
        from custom_components.hair.identity import SignalIdentity

        hass = _make_hass()
        store = SignalStore(hass)
        store._loaded = True
        rows = [
            UnknownSignal(
                fingerprint=f"fp{n:04d}",
                byte_hash=f"bh{n:04d}",
                last_seen=f"2026-01-{(n % 28) + 1:02d}T00:00:00+00:00",
            )
            for n in range(SIGNAL_MAX_SIGNALS_PER_DEVICE + 1)
        ]
        oldest = rows[0]
        oldest.last_seen = "2020-01-01T00:00:00+00:00"
        device = UnknownDevice(
            fingerprint="g1", source="sniffed", signals=list(rows),
        )
        store.add_device(device)
        store.rebuild_signal_index()
        assert store.find_filed_signal(
            SignalIdentity(None, oldest.byte_hash, oldest.fingerprint)
        ) is not None

        store.enforce_signal_caps(device, spare=rows[-1])

        assert len(device.signals) == SIGNAL_MAX_SIGNALS_PER_DEVICE
        assert store.find_filed_signal(
            SignalIdentity(None, oldest.byte_hash, oldest.fingerprint)
        ) is None

    def test_a_row_torn_out_from_under_the_index_is_not_handed_back(
        self, candle
    ):
        """The index is not allowed to outlive the row it points at.

        Nothing in the integration removes a row without telling the
        index, but a ghost entry would swallow every press of that
        button, so the hit is confirmed before it is handed back.
        """
        from custom_components.hair.identity import SignalIdentity

        hass = _make_hass()
        store = SignalStore(hass)
        store._loaded = True
        n = normalize(_Parsed(candle))
        row = UnknownSignal(
            fingerprint=n.sig_fp,
            byte_hash=n.byte_hash,
            decoded_fingerprint=n.decoded_fingerprint,
        )
        device = UnknownDevice(
            fingerprint="g1", source="sniffed", signals=[row],
        )
        store.add_device(device)
        store.rebuild_signal_index()
        ident = SignalIdentity(
            n.decoded_fingerprint, n.byte_hash, n.sig_fp
        )
        assert store.find_filed_signal(ident) is not None

        device.signals.clear()

        assert store.find_filed_signal(ident) is None

    def test_a_removed_device_stops_claiming_its_rows(self, candle):
        """Device removal needs no bookkeeping; the entry prunes itself."""
        from custom_components.hair.identity import SignalIdentity

        hass = _make_hass()
        store = SignalStore(hass)
        store._loaded = True
        n = normalize(_Parsed(candle))
        row = UnknownSignal(
            fingerprint=n.sig_fp,
            byte_hash=n.byte_hash,
            decoded_fingerprint=n.decoded_fingerprint,
        )
        device = UnknownDevice(
            fingerprint="g1", source="sniffed", signals=[row],
        )
        store.add_device(device)
        store.rebuild_signal_index()
        ident = SignalIdentity(
            n.decoded_fingerprint, n.byte_hash, n.sig_fp
        )
        assert store.find_filed_signal(ident) is not None

        store.remove_device(device.id)

        assert store.find_filed_signal(ident) is None
