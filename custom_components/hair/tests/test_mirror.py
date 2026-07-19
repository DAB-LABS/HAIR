"""The Mirror (v0.6.6): send audit, echo attribution, heard-means-shown.

Covers the echo machinery end to end with the real store and a stubbed
hass: HAIR sends create Mirror rows at SEND time; loopback captures are
claimed as echoes (never firing triggers, never entering the catalog)
and enrich heard_by; foreign emitter beacons open attribution windows
whose echoes carry integration provenance; unheard foreign sends land
as Unknown-send rows; and the v0.4.0 known-command suppression stays
dead (assigned buttons flash forever, deleted rows resurrect).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.const import (
    MIRROR_DEVICE_FP,
    MIRROR_UNKNOWN_SEND_FP_PREFIX,
)
from custom_components.hair.models import IRTrigger
from custom_components.hair.protocol_decode import DecodedIdentity
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore

from .test_signal_monitor import (  # reuse the suite's stubs
    _make_event,
    _make_hair_store,
    _make_hass,
    _make_signal_store,
    _nec_event,
)


def _monitor(hass=None, store=None, hair_store=None) -> SignalMonitor:
    hass = hass or _make_hass()
    store = store or _make_signal_store(hass)
    return SignalMonitor(hass, store, hair_store or _make_hair_store())


def _mirror_device(store: SignalStore):
    return store.get_device_by_fingerprint(MIRROR_DEVICE_FP)


class TestRecordSend:

    @pytest.mark.asyncio
    async def test_send_creates_mirror_row_at_send_time(self):
        """A send is a fact whether or not anyone hears it."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = _monitor(hass, store)
        # Route through the real pipeline entry: use a real parsed event
        # to derive a command-shaped normalization via record-from-parsed.
        from custom_components.hair import signal_monitor as sm

        parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
        n = sm.normalize(parsed)
        await monitor._mirror_upsert(
            n, decoded_fp=n.decoded_fingerprint,
            echo_source="Test AC / Temp 22 -- via Living Room Broadlink",
            reset_heard=True,
        )
        device = _mirror_device(store)
        assert device is not None
        assert device.label == "Mirror"
        assert device.source == "echo"
        assert len(device.signals) == 1
        row = device.signals[0]
        assert row.source == "echo"
        assert row.heard_by == []  # sent, not heard (yet)
        assert "Living Room Broadlink" in row.echo_source

    @pytest.mark.asyncio
    async def test_resend_bumps_not_duplicates(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = _monitor(hass, store)
        from custom_components.hair import signal_monitor as sm

        n = sm.normalize(sm.EventParser.parse(_make_event(_nec_event("0x1234")).data))
        for _ in range(3):
            await monitor._mirror_upsert(
                n, decoded_fp=n.decoded_fingerprint,
                echo_source="x", reset_heard=True,
            )
        device = _mirror_device(store)
        assert len(device.signals) == 1
        assert device.signals[0].hit_count == 3


class TestEchoClaim:

    @pytest.mark.asyncio
    async def test_expected_echo_is_claimed_and_marks_heard(self):
        """A capture matching a send expectation goes to the Mirror:
        no trigger fire, no catalog row, heard_by enriched."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        trigger_manager = MagicMock()
        monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)

        from custom_components.hair import signal_monitor as sm

        parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
        n = sm.normalize(parsed)
        # Register expectation + pending row exactly as record_send does.
        await monitor._mirror_upsert(
            n, decoded_fp=n.decoded_fingerprint,
            echo_source="Device / Cmd -- via Emitter", reset_heard=True,
        )
        monitor._echo_expectations.append({
            "decoded_fp": n.decoded_fingerprint,
            "sig_fp": n.sig_fp,
            "row_key": n.decoded_fingerprint or n.sig_fp,
            "expires": 10**12,
            "cancel": None,
        })

        await monitor._process_parsed_signal(
            parsed, receiver_entity_id="infrared.athom_rx"
        )

        trigger_manager.on_signal_captured.assert_not_called()
        device = _mirror_device(store)
        assert store.device_count == 1  # only the Mirror; no catalog remote
        row = device.signals[0]
        assert row.heard_by == ["infrared.athom_rx"]
        assert row.hit_count == 1  # echo enriches; it is not a new send

    @pytest.mark.asyncio
    async def test_unexpected_capture_flows_to_catalog_and_triggers(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        trigger_manager = MagicMock()
        monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        trigger_manager.on_signal_captured.assert_called_once()
        assert store.device_count == 1
        assert _mirror_device(store) is None

    @pytest.mark.asyncio
    async def test_expired_expectation_does_not_claim(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = _monitor(hass, store)
        from custom_components.hair import signal_monitor as sm

        parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
        n = sm.normalize(parsed)
        monitor._echo_expectations.append({
            "decoded_fp": n.decoded_fingerprint,
            "sig_fp": n.sig_fp,
            "row_key": n.sig_fp,
            "expires": 0.0,  # long past
            "cancel": None,
        })
        await monitor._process_parsed_signal(parsed, receiver_entity_id=None)
        # Flowed to the catalog as a normal capture.
        assert store.device_count == 1
        assert _mirror_device(store) is None


class TestForeignBeacons:

    def _beacon_event(self, entity_id="infrared.tuya_blaster",
                      state="2026-07-18T05:00:00.000+00:00",
                      old="2026-07-18T04:00:00.000+00:00",
                      device_class="emitter", parent=None, extra=None):
        attrs = {"device_class": device_class, "friendly_name": "Ceiling Blaster"}
        if extra:
            attrs.update(extra)
        return SimpleNamespace(
            data={
                "entity_id": entity_id,
                "new_state": SimpleNamespace(state=state, attributes=attrs),
                "old_state": SimpleNamespace(state=old, attributes=attrs),
            },
            context=SimpleNamespace(parent_id=parent),
        )

    @pytest.mark.asyncio
    async def test_foreign_echo_carries_integration_provenance(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        trigger_manager = MagicMock()
        monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)

        monitor._on_emitter_beacon(self._beacon_event())
        assert "infrared.tuya_blaster" in monitor._foreign_pending

        from custom_components.hair import signal_monitor as sm

        parsed = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
        await monitor._process_parsed_signal(
            parsed, receiver_entity_id="infrared.athom_rx"
        )
        trigger_manager.on_signal_captured.assert_not_called()
        device = _mirror_device(store)
        assert device is not None
        row = device.signals[0]
        assert "integration send" in row.echo_source
        assert row.heard_by == ["infrared.athom_rx"]

    @pytest.mark.asyncio
    async def test_automation_context_labels_automation_send(self):
        monitor = _monitor()
        monitor._on_emitter_beacon(self._beacon_event(parent="ctx-parent"))
        pending = monitor._foreign_pending["infrared.tuya_blaster"]
        assert pending["label"] == "automation send"

    @pytest.mark.asyncio
    async def test_unheard_foreign_send_lands_as_unknown_row(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        monitor = _monitor(hass, store)
        await monitor._mirror_upsert_unknown(
            "infrared.tuya_blaster", "integration send"
        )
        device = _mirror_device(store)
        row = device.signals[0]
        assert row.fingerprint == (
            f"{MIRROR_UNKNOWN_SEND_FP_PREFIX}infrared.tuya_blaster"
        )
        # No backend-stamped alias (shampoo): the frontend titles these
        # rows by their fingerprint prefix; a stamped alias would win the
        # title chain and defeat the unknown-send hint.
        assert not row.alias
        assert row.heard_by == []

    def test_own_beacon_window_suppresses(self):
        monitor = _monitor()
        from time import monotonic

        monitor._own_send_marks["infrared.tuya_blaster"] = monotonic()
        monitor._on_emitter_beacon(self._beacon_event())
        assert "infrared.tuya_blaster" not in monitor._foreign_pending

    def test_tweezer_beacon_ignored(self):
        from custom_components.hair.const import TWEEZER_OBSERVER_ATTR

        monitor = _monitor()
        monitor._on_emitter_beacon(self._beacon_event(
            entity_id="infrared.hair_tweezer",
            extra={TWEEZER_OBSERVER_ATTR: True},
        ))
        assert monitor._foreign_pending == {}

    def test_receiver_state_change_ignored(self):
        monitor = _monitor()
        monitor._on_emitter_beacon(self._beacon_event(device_class="receiver"))
        assert monitor._foreign_pending == {}

    def test_unavailable_transition_ignored(self):
        monitor = _monitor()
        monitor._on_emitter_beacon(self._beacon_event(state="unavailable"))
        assert monitor._foreign_pending == {}

    @pytest.mark.asyncio
    async def test_foreign_pending_claims_only_once(self):
        """A beacon window mints at most ONE Mirror row. Later captures
        within what was the TTL fall through to the normal pipeline --
        a fragmented echo must not mint a junk row per fragment."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        trigger_manager = MagicMock()
        monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)
        monitor._on_emitter_beacon(self._beacon_event())

        from custom_components.hair import signal_monitor as sm

        first = sm.EventParser.parse(_make_event(_nec_event("0x1234")).data)
        await monitor._process_parsed_signal(first, receiver_entity_id="infrared.athom_rx")
        assert monitor._foreign_pending == {}  # consumed by the claim

        second = sm.EventParser.parse(_make_event(_nec_event("0x9999")).data)
        await monitor._process_parsed_signal(second, receiver_entity_id="infrared.athom_rx")
        # Second capture was NOT claimed: it reached the catalog+triggers.
        trigger_manager.on_signal_captured.assert_called_once()
        mirror = _mirror_device(store)
        assert len(mirror.signals) == 1

    def test_own_window_covers_slow_emitter(self):
        """The own-send mark suppresses the beacon even when the emitter
        takes a couple of seconds to actually transmit (queued Broadlink,
        bench find: at 1.0s HAIR mistook its own send for a foreign one)."""
        from time import monotonic

        monitor = _monitor()
        monitor._own_send_marks["infrared.tuya_blaster"] = monotonic() - 2.0
        monitor._on_emitter_beacon(self._beacon_event())
        assert "infrared.tuya_blaster" not in monitor._foreign_pending

    def test_reconnect_restore_ignored(self):
        """unavailable -> timestamp is the entity coming back (reconnect
        blip, integration reload, startup restore) and the write is the
        RESTORED last-send timestamp, not a new send. Without the
        old-state guard every Broadlink reconnect would mint a phantom
        unknown-send row (v0.6.6 bench find)."""
        monitor = _monitor()
        monitor._on_emitter_beacon(self._beacon_event(old="unavailable"))
        assert monitor._foreign_pending == {}
        monitor._on_emitter_beacon(self._beacon_event(old="unknown"))
        assert monitor._foreign_pending == {}


class TestHeardMeansShown:

    @pytest.mark.asyncio
    async def test_deleted_row_resurrects_on_rehearing(self):
        """Delete clears the entry; hearing it again re-creates it.
        Dismiss is the one and only hiding tool."""
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        hair_store.match_command.return_value = ("dev-1", "cmd-1")  # assigned!
        monitor = SignalMonitor(hass, store, hair_store)

        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        assert store.device_count == 1
        device = store.get_all_devices()[0]
        device.signals.clear()  # the user deletes the row

        # Repeat-suppression window must not eat the re-press in this
        # test; jump past it.
        monitor._last_seen_times = {}
        await monitor._on_ir_event(_make_event(_nec_event("0x1234")))
        device = store.get_all_devices()[0]
        assert len(device.signals) == 1  # resurrected


class TestBadgeOrphanRetired:
    """The v0.6.1 known issue, retired.

    The heal merge (or a user delete) could leave a trigger with no
    catalog row to hang its yellow badge on, and the v0.4.0
    known-command suppression kept the row from ever coming back once
    the same identity was assigned to a device command. Every matcher
    in the chain was already tiered decoded-first (v0.5.8); the badge
    was orphaned purely because the ROW was gone. Heard-means-shown
    closes it: the next physical press recreates the row carrying the
    same identity triple the trigger path saw, so the badge and the
    firing path can never disagree about a live button again.
    """

    @pytest.mark.asyncio
    async def test_press_recreates_row_that_reattaches_the_trigger(self):
        hass = _make_hass()
        store = _make_signal_store(hass)
        hair_store = _make_hair_store()
        # The identity is assigned to a device command ("Mode: Cool" in
        # the bench case) -- pre-v0.6.6 this suppressed the row.
        hair_store.match_command.return_value = ("dev-1", "cmd-1")
        trigger_manager = MagicMock()
        trigger_manager.on_signal_captured = MagicMock(return_value=[])
        monitor = SignalMonitor(hass, store, hair_store, trigger_manager)

        identity = DecodedIdentity(
            protocol="SAMSUNG32", address=0x0007, command=0x04,
            fingerprint="SAMSUNG32:0x0007:0x04", extras=None, source="local",
        )
        with patch(
            "custom_components.hair.signal_monitor.try_decode_identity",
            return_value=identity,
        ):
            await monitor._on_ir_event(_make_event(_nec_event("0x1234")))

        # Firing path saw the decoded identity (7th positional arg)...
        args = trigger_manager.on_signal_captured.call_args[0]
        assert args[6] == "SAMSUNG32:0x0007:0x04"

        # ...and the row exists despite the assigned-command match,
        # carrying that same identity.
        device = store.get_all_devices()[0]
        row = device.signals[0]
        assert row.decoded_fingerprint == "SAMSUNG32:0x0007:0x04"

        # A trigger created from the DEAD row (stale S/L fingerprint and
        # byte_hash) re-attaches to the resurrected row via the decoded
        # tier -- this comparison is exactly the frontend's yellow-badge
        # check (triggerMatchesSignal) and the backend's firing match.
        orphaned = IRTrigger(
            name="Button 1",
            signal_fingerprint="dead-row-fp",
            byte_hash="dead-row-hash",
            decoded_fingerprint="SAMSUNG32:0x0007:0x04",
        )
        assert orphaned.matches_signal(
            row.fingerprint, row.byte_hash, row.decoded_fingerprint
        )


class TestGarbledEchoSwallow:
    """The garbled-echo swallow (owner design, shampoo): HAIR's own send
    coming back damaged misses both identity claims but still resembles
    what went out. Similar + undecodable + inside the window -> mark the
    send heard and swallow; everything else walks through untouched."""

    # A clean 16-symbol frame: pairs of (mark, space) where ~900us reads
    # short and ~1800us reads long against the S/L threshold. Tuples:
    # every consumer copies via list(...), and ruff (RUF012) is right
    # that mutable class attributes are a trap.
    CLEAN = (900, -900, 1800, -1800, 900, -900, 900, -900,
             900, -900, 1800, -900, 900, -1800, 900, -900)
    # The bench's truncated-head shape: leading pair lost. A perfect
    # substring of CLEAN -> fuzzy ratio 0.0.
    TRUNCATED = CLEAN[2:]
    # Nothing like CLEAN: a long run of shorts.
    FOREIGN = (400, -400) * 12

    def _armed_monitor(self, timings):
        """Monitor with a Mirror row + live expectation for ``timings``,
        exactly as record_send arms them (decode patched off: the sent
        signal itself is S/L-only, the RC-5-replay bench shape)."""
        from custom_components.hair import signal_monitor as sm

        hass = _make_hass()
        store = _make_signal_store(hass)
        trigger_manager = MagicMock()
        monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)
        with patch(
            "custom_components.hair.signal_monitor.try_decode_identity",
            return_value=None,
        ):
            parsed = sm.EventParser.parse_received_signal(
                SimpleNamespace(timings=list(timings), modulation=38000)
            )
            n = sm.normalize(parsed)
        return monitor, store, trigger_manager, n

    async def _arm(self, monitor, n):
        from custom_components.hair import signal_monitor as sm

        await monitor._mirror_upsert(
            n, decoded_fp=None,
            echo_source="Manual test send -- via Office Broadlink",
            reset_heard=True,
        )
        monitor._echo_expectations.append({
            "decoded_fp": None,
            "sig_fp": n.sig_fp,
            "row_key": n.sig_fp,
            "expires": 10**12,
            "sl": sm.EventParser._pronto_sl_pattern(n.code),
            "garble_expires": 10**12,
            "cancel": None,
        })

    @pytest.mark.asyncio
    async def test_garbled_similar_swallowed_and_marks_heard(self):
        from custom_components.hair import signal_monitor as sm

        monitor, store, trigger_manager, n = self._armed_monitor(self.CLEAN)
        await self._arm(monitor, n)
        with patch(
            "custom_components.hair.signal_monitor.try_decode_identity",
            return_value=None,
        ):
            garbled = sm.EventParser.parse_received_signal(
                SimpleNamespace(timings=list(self.TRUNCATED), modulation=38000)
            )
            await monitor._process_parsed_signal(
                garbled, receiver_entity_id="infrared.office_rx"
            )
        trigger_manager.on_signal_captured.assert_not_called()
        assert store.device_count == 1  # only the Mirror; no junk remote
        row = _mirror_device(store).signals[0]
        assert row.heard_by == ["infrared.office_rx"]

    @pytest.mark.asyncio
    async def test_dissimilar_undecodable_walks_through(self):
        from custom_components.hair import signal_monitor as sm

        monitor, store, trigger_manager, n = self._armed_monitor(self.CLEAN)
        await self._arm(monitor, n)
        with patch(
            "custom_components.hair.signal_monitor.try_decode_identity",
            return_value=None,
        ):
            foreign = sm.EventParser.parse_received_signal(
                SimpleNamespace(timings=list(self.FOREIGN), modulation=38000)
            )
            await monitor._process_parsed_signal(
                foreign, receiver_entity_id="infrared.office_rx"
            )
        # A real stranger during the window: catalog row minted, trigger
        # path consulted, Mirror row still unheard.
        trigger_manager.on_signal_captured.assert_called_once()
        assert store.device_count == 2
        assert _mirror_device(store).signals[0].heard_by == []

    @pytest.mark.asyncio
    async def test_decoded_capture_never_swallowed(self):
        """A clean decode with a non-matching fingerprint is a real,
        different signal (candles-off pressed right after testing
        candles-on) -- similarity must not eat it."""
        from custom_components.hair import signal_monitor as sm

        monitor, store, trigger_manager, n = self._armed_monitor(self.CLEAN)
        await self._arm(monitor, n)
        identity = DecodedIdentity(
            protocol="RC5", address=0x1F, command=0x02,
            fingerprint="RC5:0x001f:0x02", extras=None, source="local",
        )
        with patch(
            "custom_components.hair.signal_monitor.try_decode_identity",
            return_value=identity,
        ):
            # The SAME shape we transmitted -- maximally similar -- but
            # it decodes, so it must walk through to the catalog.
            twin = sm.EventParser.parse_received_signal(
                SimpleNamespace(timings=list(self.TRUNCATED), modulation=38000)
            )
            await monitor._process_parsed_signal(
                twin, receiver_entity_id="infrared.office_rx"
            )
        trigger_manager.on_signal_captured.assert_called_once()
        assert store.device_count == 2

    @pytest.mark.asyncio
    async def test_expired_garble_window_walks_through(self):
        from custom_components.hair import signal_monitor as sm

        monitor, store, trigger_manager, n = self._armed_monitor(self.CLEAN)
        await self._arm(monitor, n)
        monitor._echo_expectations[-1]["expires"] = 0.0
        monitor._echo_expectations[-1]["garble_expires"] = 0.0
        with patch(
            "custom_components.hair.signal_monitor.try_decode_identity",
            return_value=None,
        ):
            garbled = sm.EventParser.parse_received_signal(
                SimpleNamespace(timings=list(self.TRUNCATED), modulation=38000)
            )
            await monitor._process_parsed_signal(
                garbled, receiver_entity_id="infrared.office_rx"
            )
        trigger_manager.on_signal_captured.assert_called_once()
        assert store.device_count == 2

    def test_fuzzy_ratio_shapes(self):
        """The metric itself: substring free alignment, shard matching,
        and true strangers scoring high."""
        from custom_components.hair.signal_monitor import (
            _sl_fuzzy_substring_ratio as ratio,
        )
        clean = "SSLLSSSSSSSSLSSSSSSSSLSL"
        assert ratio(clean, clean) == 0.0
        assert ratio(clean[2:], clean) == 0.0          # truncated head
        assert ratio(clean[:-3] + "LLL", clean) <= 0.35  # merged tail
        assert ratio("SLLSSSSL", clean) <= 0.35        # shard inside frame
        assert ratio("S" * 40, clean) > 0.35           # true stranger
