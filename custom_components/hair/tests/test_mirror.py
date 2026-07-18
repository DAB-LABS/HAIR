"""The Mirror (v0.6.3): send audit, echo attribution, heard-means-shown.

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
        assert row.alias == "Unknown send"
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
        # the bench case) -- pre-v0.6.3 this suppressed the row.
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
