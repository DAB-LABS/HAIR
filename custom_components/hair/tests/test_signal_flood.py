"""Tests for the GH #72 hotfix (v0.8.9): noise-flood resilience.

carlmiller99's py-spy-profiled report had two halves. The freeze:
``SignalStore.async_load`` ran a quadratic duplicate heal directly on
the event loop, starving all of Home Assistant for ~15 minutes per
boot at his 104k-signal store size. The growth: HAIR subscribed to the
RF proxy receivers of a combined RF/IR device, so ambient radio
chatter minted 500 phantom remotes and 340MB of undecodable signals in
33 hours, with no cap to stop it.

Covered here:
- Heal parity: the O(n) ``_heal_device_signals`` reproduces the old
  pairwise scan's outcome exactly (a verbatim copy of the old
  algorithm lives in this file as the oracle), across crafted
  truth-table cases and a seeded fuzz sweep.
- Heal performance: a flood-scale store heals in well under a second.
- Executor guard: ``async_load`` runs the payload transform via
  ``hass.async_add_executor_job``.
- Signal caps: per-device and global trims, eviction order (oldest
  first, aliased rows spared until last, the just-inserted signal
  never evicted), the once-per-run warnings, and the one-shot trim of
  an oversized store at load.
- RF receiver exclusion: registry-based detection, subscription-level
  filtering with the IR sibling kept, and the capture-provider list.
"""
from __future__ import annotations

import copy
import random
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    SIGNAL_MAX_SIGNALS_PER_DEVICE,
    SIGNAL_MAX_TOTAL_SIGNALS,
)
from custom_components.hair.identity import SignalIdentity
from custom_components.hair.models import UnknownDevice, UnknownSignal
from custom_components.hair.receiver_filter import (
    _reads_as_rf,
    is_rf_receiver,
    partition_receivers,
)
from custom_components.hair.signal_store import (
    SignalStore,
    _enforce_global_cap,
    _heal_device_signals,
    _transform_loaded,
    _trim_device_signals,
)

# ---------------------------------------------------------------------------
# The oracle: the pre-GH #72 heal, verbatim
# ---------------------------------------------------------------------------
# This is the old O(n^2) pass exactly as it shipped in async_load
# (v0.5.8 tiered form), kept here so parity is asserted against the
# real historical behavior rather than a re-derivation of it.


def _old_heal(device: UnknownDevice) -> bool:
    kept: list = []
    for sig in device.signals:
        ident = SignalIdentity(
            sig.decoded_fingerprint, sig.byte_hash, sig.fingerprint
        )
        best = None
        best_tier = 99
        for keep in kept:
            tier = SignalIdentity(
                keep.decoded_fingerprint, keep.byte_hash, keep.fingerprint
            ).match_tier(ident)
            if tier is not None and tier < best_tier:
                best = keep
                best_tier = tier
                if tier == 1:
                    break
        if best is not None:
            best.hit_count += sig.hit_count
            if not best.alias and sig.alias:
                best.alias = sig.alias
            if sig.last_seen and (
                not best.last_seen or sig.last_seen > best.last_seen
            ):
                best.last_seen = sig.last_seen
        else:
            kept.append(sig)
    if len(kept) != len(device.signals):
        device.signals = kept
        return True
    return False


def _sig(
    n: int,
    fingerprint: str = "",
    byte_hash: str | None = None,
    decoded: str | None = None,
    hit_count: int = 1,
    alias: str = "",
    last_seen: str = "2026-07-01T00:00:00+00:00",
) -> UnknownSignal:
    return UnknownSignal(
        id=f"s{n}",
        fingerprint=fingerprint,
        byte_hash=byte_hash,
        decoded_fingerprint=decoded,
        hit_count=hit_count,
        alias=alias,
        first_seen=last_seen,
        last_seen=last_seen,
    )


def _dev(signals: list[UnknownSignal], source: str = "sniffed") -> UnknownDevice:
    return UnknownDevice(
        id="d1",
        fingerprint="DEV",
        label="Remote 1",
        source=source,
        signals=signals,
    )


def _outcome(device: UnknownDevice) -> list[tuple]:
    return [
        (s.id, s.hit_count, s.alias, s.last_seen) for s in device.signals
    ]


def _assert_parity(signals: list[UnknownSignal]) -> None:
    """Run oracle and new heal on copies of the same store; same result."""
    old_dev = _dev(copy.deepcopy(signals))
    new_dev = _dev(copy.deepcopy(signals))
    old_changed = _old_heal(old_dev)
    new_changed = _heal_device_signals(new_dev)
    assert new_changed == old_changed
    assert _outcome(new_dev) == _outcome(old_dev)


class TestHealParity:
    def test_tier1_decoded_match_merges(self):
        _assert_parity(
            [
                _sig(1, "SL", "b1", "NEC:0x04:0x08"),
                _sig(2, "SS", "b2", "NEC:0x04:0x08", hit_count=3),
            ]
        )

    def test_decoded_mismatch_is_final_no_fallthrough(self):
        # Same byte_hash AND fingerprint, but decoded identities differ:
        # a decided-tier mismatch never falls through to weaker layers.
        _assert_parity(
            [
                _sig(1, "SL", "b1", "NEC:0x04:0x08"),
                _sig(2, "SL", "b1", "NEC:0x04:0x09"),
            ]
        )

    def test_tier2_one_side_lacks_decoded(self):
        # A decoded row and a decode-failed row with the same byte_hash
        # merge at tier 2 regardless of order.
        _assert_parity(
            [
                _sig(1, "SL", "b1", "NEC:0x04:0x08"),
                _sig(2, "SL", "b1", None, hit_count=4),
            ]
        )
        _assert_parity(
            [
                _sig(1, "SL", "b1", None, hit_count=4),
                _sig(2, "SL", "b1", "NEC:0x04:0x08"),
            ]
        )

    def test_byte_hash_mismatch_is_final(self):
        # Panasonic/TCL/Sony siblings: same S/L fingerprint, different
        # byte level. Distinct, never collapsed.
        _assert_parity(
            [
                _sig(1, "SL", "b1"),
                _sig(2, "SL", "b2"),
            ]
        )

    def test_flip_duplicates_merge_at_tier2(self):
        # Sony boundary jitter: same byte_hash, DIFFERENT fingerprint.
        _assert_parity(
            [
                _sig(1, "SL", "b1", alias="Yellow", hit_count=5),
                _sig(2, "SS", "b1", hit_count=3),
            ]
        )

    def test_tier3_fingerprint_only(self):
        _assert_parity(
            [
                _sig(1, "SL", None, None, hit_count=2),
                _sig(2, "SL", None, None, hit_count=7, alias="Late"),
            ]
        )

    def test_tier3_skipped_when_one_side_has_byte_hash(self):
        # One row carries byte_hash, the other does not: byte tier is
        # skipped (not decided), fingerprint decides.
        _assert_parity(
            [
                _sig(1, "SL", "b1"),
                _sig(2, "SL", None),
            ]
        )

    def test_empty_fingerprints_never_match(self):
        _assert_parity(
            [
                _sig(1, "", None, None),
                _sig(2, "", None, None),
            ]
        )

    def test_merge_metadata_semantics(self):
        # Alias adopted only when the kept row has none; last_seen
        # max-merged; hits summed into the FIRST kept occurrence.
        day1 = "2026-07-01T00:00:00+00:00"
        day2 = "2026-07-02T00:00:00+00:00"
        day3 = "2026-07-03T00:00:00+00:00"
        signals = [
            _sig(1, "SL", "b1", hit_count=1, last_seen=day1),
            _sig(2, "SL", "b1", hit_count=2, alias="Named", last_seen=day3),
            _sig(3, "SL", "b1", hit_count=4, alias="Ignored", last_seen=day2),
        ]
        _assert_parity(signals)
        dev = _dev(copy.deepcopy(signals))
        _heal_device_signals(dev)
        assert len(dev.signals) == 1
        kept = dev.signals[0]
        assert kept.id == "s1"
        assert kept.hit_count == 7
        assert kept.alias == "Named"
        assert kept.last_seen == "2026-07-03T00:00:00+00:00"

    def test_strongest_match_beats_earlier_weaker_match(self):
        # A tier-1 match wins even when a tier-2-eligible row was kept
        # earlier (old scan's strongest-match-wins).
        _assert_parity(
            [
                _sig(1, "SL", "b1", None),
                _sig(2, "SS", "b2", "NEC:0x04:0x08"),
                _sig(3, "SL", "b1", "NEC:0x04:0x08"),
            ]
        )

    def test_fuzz_parity_seeded(self):
        # Random stores across every layer combination. Small value
        # pools force heavy collisions; the oracle decides what is
        # correct. Seeded, so a failure reproduces.
        rng = random.Random(0x48414952)  # "HAIR"
        decodeds = [None, None, "NEC:1", "NEC:2", "SONY15:9"]
        bytes_ = [None, "ba", "bb", "bc"]
        fps = ["", "SL", "SS", "LL"]
        aliases = ["", "", "", "x", "y"]
        for _round in range(50):
            signals = [
                _sig(
                    n,
                    fingerprint=rng.choice(fps),
                    byte_hash=rng.choice(bytes_),
                    decoded=rng.choice(decodeds),
                    hit_count=rng.randrange(1, 9),
                    alias=rng.choice(aliases),
                    last_seen=f"2026-07-{rng.randrange(1, 28):02d}T00:00:00+00:00",
                )
                for n in range(rng.randrange(2, 40))
            ]
            _assert_parity(signals)


class TestHealPerformance:
    def test_flood_scale_store_heals_fast(self):
        # The GH #72 skew: one fat device. 5,000 rows would take the
        # old pass ~12.5M comparisons; the new pass is linear. Half the
        # rows are duplicates so the merge path is exercised too.
        signals = [
            _sig(
                n,
                fingerprint=f"fp{n % 2500}",
                byte_hash=f"b{n % 2500}",
                hit_count=1,
            )
            for n in range(5000)
        ]
        dev = _dev(signals)
        start = time.perf_counter()
        assert _heal_device_signals(dev) is True
        elapsed = time.perf_counter() - start
        assert len(dev.signals) == 2500
        assert elapsed < 1.0, f"heal took {elapsed:.2f}s"


class TestExecutorLoad:
    def _hass(self):
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        return hass

    @pytest.mark.asyncio
    async def test_transform_runs_in_executor(self):
        hass = self._hass()
        store = SignalStore(hass)
        raw = {
            "devices": [
                {
                    "id": "d1",
                    "fingerprint": "DEV",
                    "label": "R",
                    "signals": [],
                }
            ],
            "dismissed": [],
        }
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=raw)
            await store.async_load()
        hass.async_add_executor_job.assert_awaited_once_with(
            _transform_loaded, raw
        )
        assert store.get_device("d1") is not None

    @pytest.mark.asyncio
    async def test_empty_store_skips_executor(self):
        hass = self._hass()
        store = SignalStore(hass)
        with patch.object(store, "_store") as mock_store:
            mock_store.async_load = AsyncMock(return_value=None)
            await store.async_load()
        hass.async_add_executor_job.assert_not_awaited()
        assert store.loaded is True
        assert store.get_all_devices() == []


class TestSignalCaps:
    def test_trim_evicts_oldest_first(self):
        signals = [
            _sig(n, f"fp{n}", last_seen=f"2026-07-{n + 1:02d}T00:00:00+00:00")
            for n in range(5)
        ]
        dev = _dev(signals)
        removed = _trim_device_signals(dev, 3)
        assert removed == 2
        assert [s.id for s in dev.signals] == ["s2", "s3", "s4"]

    def test_trim_spares_aliased_until_last(self):
        signals = [
            _sig(0, "fp0", alias="Keep me", last_seen="2026-07-01T00:00:00+00:00"),
            _sig(1, "fp1", last_seen="2026-07-02T00:00:00+00:00"),
            _sig(2, "fp2", last_seen="2026-07-03T00:00:00+00:00"),
        ]
        dev = _dev(signals)
        removed = _trim_device_signals(dev, 2)
        assert removed == 1
        # The oldest row is aliased; the oldest UNNAMED row goes instead.
        assert [s.id for s in dev.signals] == ["s0", "s2"]

    def test_trim_never_evicts_spare(self):
        # Every existing row aliased; without the spare guard the
        # brand-new capture would be the first victim.
        aliased = [
            _sig(n, f"fp{n}", alias=f"a{n}", last_seen="2026-07-05T00:00:00+00:00")
            for n in range(3)
        ]
        fresh = _sig(99, "fp99", last_seen="2026-07-28T00:00:00+00:00")
        dev = _dev([*aliased, fresh])
        removed = _trim_device_signals(dev, 3, spare=fresh)
        assert removed == 1
        assert fresh in dev.signals

    def test_enforce_caps_trims_device_and_warns_once(self, caplog):
        hass = MagicMock()
        store = SignalStore(hass)
        store._loaded = True
        signals = [
            _sig(n, f"fp{n}") for n in range(SIGNAL_MAX_SIGNALS_PER_DEVICE + 10)
        ]
        dev = _dev(signals)
        store._devices[dev.id] = dev
        with caplog.at_level("WARNING"):
            removed = store.enforce_signal_caps(dev, "infrared.athom_rx")
        assert removed == 10
        assert len(dev.signals) == SIGNAL_MAX_SIGNALS_PER_DEVICE
        warnings = [
            r for r in caplog.records if "signal store cap" in r.message
        ]
        assert len(warnings) == 1
        assert "infrared.athom_rx" in warnings[0].message
        # Second breach: trims again, does NOT warn again.
        dev.signals.extend(_sig(1000 + n, f"xfp{n}") for n in range(5))
        caplog.clear()
        with caplog.at_level("WARNING"):
            removed = store.enforce_signal_caps(dev)
        assert removed == 5
        assert not [
            r for r in caplog.records if "signal store cap" in r.message
        ]

    def test_enforce_caps_ignores_manual_and_plucked(self):
        hass = MagicMock()
        store = SignalStore(hass)
        store._loaded = True
        for source in ("manual", "plucked"):
            dev = UnknownDevice(
                id=f"d-{source}",
                fingerprint=f"DEV-{source}",
                source=source,
                signals=[
                    _sig(n, f"{source}{n}")
                    for n in range(SIGNAL_MAX_SIGNALS_PER_DEVICE + 20)
                ],
            )
            store._devices[dev.id] = dev
            assert store.enforce_signal_caps(dev) == 0
            assert len(dev.signals) == SIGNAL_MAX_SIGNALS_PER_DEVICE + 20

    def test_global_cap_water_fills_noisiest(self):
        # Three quiet devices and one flooded one: only the flood pays.
        devices = {}
        for i in range(3):
            d = UnknownDevice(
                id=f"q{i}",
                fingerprint=f"Q{i}",
                source="sniffed",
                signals=[_sig(i * 1000 + n, f"q{i}fp{n}") for n in range(50)],
            )
            devices[d.id] = d
        flood = UnknownDevice(
            id="loud",
            fingerprint="LOUD",
            label="Static",
            source="sniffed",
            signals=[
                _sig(90000 + n, f"lfp{n}")
                for n in range(SIGNAL_MAX_TOTAL_SIGNALS)
            ],
        )
        devices[flood.id] = flood
        removed, noisiest = _enforce_global_cap(devices)
        assert removed == 150  # 3 * 50 quiet rows displaced the flood's
        assert noisiest == "Static"
        for i in range(3):
            assert len(devices[f"q{i}"].signals) == 50
        total = sum(len(d.signals) for d in devices.values())
        assert total <= SIGNAL_MAX_TOTAL_SIGNALS

    def test_load_trims_oversized_store(self, caplog):
        # A pre-fix store over the per-device cap is trimmed once at
        # load, marked dirty, and explained in a single WARNING. Manual
        # devices are untouched.
        over = SIGNAL_MAX_SIGNALS_PER_DEVICE + 50
        raw = {
            "devices": [
                {
                    "id": "d1",
                    "fingerprint": "DEV",
                    "label": "Remote 1",
                    "source": "sniffed",
                    "signals": [
                        {
                            "id": f"s{n}",
                            "fingerprint": f"fp{n}",
                            "byte_hash": f"b{n}",
                            "hit_count": 1,
                            "last_seen": f"2026-{(n % 12) + 1:02d}-01T00:00:00+00:00",
                        }
                        for n in range(over)
                    ],
                },
                {
                    "id": "d2",
                    "fingerprint": "CLIP",
                    "label": "My Clips",
                    "source": "manual",
                    "signals": [
                        {
                            "id": f"m{n}",
                            "fingerprint": f"mfp{n}",
                            "byte_hash": f"mb{n}",
                        }
                        for n in range(SIGNAL_MAX_SIGNALS_PER_DEVICE + 30)
                    ],
                },
            ],
            "dismissed": [],
        }
        with caplog.at_level("WARNING"):
            devices, _dismissed, dirty = _transform_loaded(raw)
        assert dirty is True
        assert len(devices["d1"].signals) == SIGNAL_MAX_SIGNALS_PER_DEVICE
        assert (
            len(devices["d2"].signals) == SIGNAL_MAX_SIGNALS_PER_DEVICE + 30
        )
        warnings = [
            r for r in caplog.records if "exceeded its caps" in r.message
        ]
        assert len(warnings) == 1
        assert "Remote 1" in warnings[0].message

    def test_load_within_caps_untouched(self):
        raw = {
            "devices": [
                {
                    "id": "d1",
                    "fingerprint": "DEV",
                    "source": "sniffed",
                    "signals": [
                        {
                            "id": f"s{n}",
                            "fingerprint": f"fp{n}",
                            "byte_hash": f"b{n}",
                        }
                        for n in range(10)
                    ],
                }
            ],
            "dismissed": [],
        }
        devices, _dismissed, dirty = _transform_loaded(raw)
        assert len(devices["d1"].signals) == 10
        assert dirty is False

    def test_flood_stays_bounded(self):
        # Sustained flood through the runtime path: the device can
        # never exceed the cap no matter how many bursts arrive.
        hass = MagicMock()
        store = SignalStore(hass)
        store._loaded = True
        dev = _dev([])
        store._devices[dev.id] = dev
        for n in range(SIGNAL_MAX_SIGNALS_PER_DEVICE * 3):
            fresh = _sig(n, f"fp{n}", last_seen=f"2026-07-01T{n % 24:02d}:00:00+00:00")
            dev.signals.insert(0, fresh)
            store.enforce_signal_caps(dev, "infrared.noise_rx", spare=fresh)
            assert len(dev.signals) <= SIGNAL_MAX_SIGNALS_PER_DEVICE


# ---------------------------------------------------------------------------
# RF receiver exclusion
# ---------------------------------------------------------------------------


def _registry_with(entries: dict[str, tuple[str | None, str | None]]):
    """Fake entity registry: entity_id -> (unique_id, original_name)."""
    registry = MagicMock()

    def _get(entity_id):
        if entity_id not in entries:
            return None
        unique_id, original_name = entries[entity_id]
        entry = MagicMock()
        entry.unique_id = unique_id
        entry.original_name = original_name
        return entry

    registry.async_get = _get
    return registry


class TestRfDetection:
    def test_reads_as_rf_truth_table(self):
        # Real strings from the bench Athom (IR) and the ir_rf_proxy
        # convention (RF), plus the traps the rule is built around.
        assert _reads_as_rf("E0:8C:FE:35:06:28-infrared-rf_proxy_receiver")
        assert _reads_as_rf("RF Proxy Receiver")
        assert not _reads_as_rf(
            "E0:8C:FE:35:06:28-infrared-ir_proxy_receiver"
        )
        assert not _reads_as_rf("IR Proxy Receiver")
        # Device names carry both tokens; a name-based match would
        # disable the bench hardware. Both-token fields keep the sub.
        assert not _reads_as_rf("Athom RF IR Remote 1 IR Proxy Receiver")
        assert not _reads_as_rf("rf_ir_receiver")
        # The infrared domain marker is not an IR claim, but a bare
        # rf-free field is not an RF claim either.
        assert not _reads_as_rf("a043b05510f6-emitter")
        assert not _reads_as_rf(None)
        assert not _reads_as_rf("")
        assert not _reads_as_rf(MagicMock())  # non-string = no claim

    def test_is_rf_receiver_consults_registry(self):
        hass = MagicMock()
        registry = _registry_with(
            {
                "infrared.athom_rx": (
                    "E0:8C:FE:35:06:28-infrared-ir_proxy_receiver",
                    "IR Proxy Receiver",
                ),
                "infrared.athom_rf_rx": (
                    "E0:8C:FE:35:06:28-infrared-rf_proxy_receiver",
                    "RF Proxy Receiver",
                ),
            }
        )
        with patch(
            "custom_components.hair.receiver_filter.er.async_get",
            return_value=registry,
        ):
            assert is_rf_receiver(hass, "infrared.athom_rf_rx") is True
            assert is_rf_receiver(hass, "infrared.athom_rx") is False
            # Unregistered entity: no claim, keep the subscription.
            assert is_rf_receiver(hass, "infrared.unknown") is False
            ir_ids, rf_ids = partition_receivers(
                hass, ["infrared.athom_rx", "infrared.athom_rf_rx"]
            )
        assert ir_ids == ["infrared.athom_rx"]
        assert rf_ids == ["infrared.athom_rf_rx"]

    def test_registry_failure_reads_as_ir(self):
        hass = MagicMock()
        with patch(
            "custom_components.hair.receiver_filter.er.async_get",
            side_effect=KeyError("registry not loaded"),
        ):
            assert is_rf_receiver(hass, "infrared.athom_rx") is False


class TestRfSubscriptionExclusion:
    def test_rf_receiver_not_subscribed_ir_sibling_is(self, caplog):
        from .test_receiver_hotplug import (
            _FakeInfrared,
            _monitor,
            _patched,
        )
        from .test_signal_monitor import _make_hass

        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(
            receivers=["infrared.athom_rx", "infrared.athom_rf_rx"]
        )
        registry = _registry_with(
            {
                "infrared.athom_rx": (
                    "E0:8C:FE:35:06:28-infrared-ir_proxy_receiver",
                    "IR Proxy Receiver",
                ),
                "infrared.athom_rf_rx": (
                    "E0:8C:FE:35:06:28-infrared-rf_proxy_receiver",
                    "RF Proxy Receiver",
                ),
            }
        )
        with patch(
            "custom_components.hair.receiver_filter.er.async_get",
            return_value=registry,
        ), _patched(fake), caplog.at_level("INFO"):
            monitor._start_native_tracking()
            # Reconcile again: the skip note must not repeat.
            monitor._reconcile_receivers()

        assert set(monitor._receiver_subs) == {"infrared.athom_rx"}
        skip_notes = [
            r
            for r in caplog.records
            if "reads as an RF receiver" in r.message
        ]
        assert len(skip_notes) == 1
        assert "infrared.athom_rf_rx" in skip_notes[0].message

    def test_previously_subscribed_rf_receiver_released(self):
        # Upgrade path: an RF receiver subscribed by an older HAIR is
        # released on the first reconcile with the guard in place.
        from .test_receiver_hotplug import (
            _FakeInfrared,
            _monitor,
            _patched,
        )
        from .test_signal_monitor import _make_hass

        hass = _make_hass()
        monitor = _monitor(hass)
        fake = _FakeInfrared(
            receivers=["infrared.athom_rx", "infrared.athom_rf_rx"]
        )
        registry_all_ir = _registry_with({})  # nothing reads as RF
        with _patched(fake):
            with patch(
                "custom_components.hair.receiver_filter.er.async_get",
                return_value=registry_all_ir,
            ):
                monitor._start_native_tracking()
                assert "infrared.athom_rf_rx" in monitor._receiver_subs
            registry = _registry_with(
                {
                    "infrared.athom_rf_rx": (
                        "E0:8C:FE:35:06:28-infrared-rf_proxy_receiver",
                        "RF Proxy Receiver",
                    ),
                }
            )
            with patch(
                "custom_components.hair.receiver_filter.er.async_get",
                return_value=registry,
            ):
                monitor._reconcile_receivers()
        assert set(monitor._receiver_subs) == {"infrared.athom_rx"}
        assert fake.unsubs["infrared.athom_rf_rx"][0].called

    async def test_capture_providers_exclude_rf(self):
        from custom_components.hair.capture import (
            get_available_capture_providers,
        )

        from .test_signal_monitor import _make_hass

        hass = _make_hass()
        hass.config.components = set()
        state = MagicMock()
        state.attributes = {"friendly_name": "Athom IR RX"}
        hass.states.get = MagicMock(return_value=state)
        fake_module = MagicMock(
            async_get_receivers=lambda _hass: [
                "infrared.athom_rx",
                "infrared.athom_rf_rx",
            ]
        )
        registry = _registry_with(
            {
                "infrared.athom_rf_rx": (
                    "E0:8C:FE:35:06:28-infrared-rf_proxy_receiver",
                    "RF Proxy Receiver",
                ),
            }
        )
        with patch.dict(
            "sys.modules",
            {"homeassistant.components.infrared": fake_module},
        ), patch(
            "custom_components.hair.receiver_filter.er.async_get",
            return_value=registry,
        ):
            providers = await get_available_capture_providers(hass)
        native_ids = [
            p["receiver_entity_id"]
            for p in providers
            if p["type"] == "native"
        ]
        assert native_ids == ["infrared.athom_rx"]
