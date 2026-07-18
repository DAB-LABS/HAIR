"""Tests for HAIR TriggerManager."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.models import IRTrigger
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager


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
    """Controllable monotonic clock for TriggerManager's time-based logic.

    The 60ms multi-receiver dedup and the 5s min_hits reset window both read
    ``time.monotonic``. Real distinct presses are hundreds of ms apart; these
    tests fire synchronously, so a fake clock lets them advance time
    deterministically past the dedup window between distinct presses.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def monotonic(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


@pytest.fixture
def clock(monkeypatch):
    fake = _FakeClock()
    monkeypatch.setattr(
        "custom_components.hair.trigger_manager.time", fake
    )
    return fake


def _make_trigger(
    name: str = "Test",
    fingerprint: str = "fp1",
    protocol: str = "pronto",
    code: str = "0000 0001",
    min_hits: int = 1,
    enabled: bool = True,
) -> IRTrigger:
    return IRTrigger(
        name=name,
        signal_fingerprint=fingerprint,
        protocol=protocol,
        code=code,
        min_hits=min_hits,
        enabled=enabled,
    )


class TestRewire:
    """TriggerManager.rewire repoints bound triggers on a fingerprint change."""

    async def test_updates_bound_trigger(self, manager, mock_store):
        mock_store.async_save = AsyncMock()
        t = _make_trigger(name="TV Power", fingerprint="OLD", code="0000 AAAA")
        mock_store.add_trigger(t)
        result = await manager.rewire("OLD", "NEW", "PRONTO", "0000 BBBB")
        assert result == {"rewired": ["TV Power"], "skipped": []}
        assert t.signal_fingerprint == "NEW"
        assert t.protocol == "PRONTO"
        assert t.code == "0000 BBBB"
        mock_store.async_save.assert_awaited_once()

    async def test_noop_when_fingerprint_unchanged(self, manager, mock_store):
        mock_store.async_save = AsyncMock()
        t = _make_trigger(fingerprint="SAME", code="0000 0001")
        mock_store.add_trigger(t)
        result = await manager.rewire("SAME", "SAME", "PRONTO", "0000 CCCC")
        assert result == {"rewired": [], "skipped": []}
        assert t.code == "0000 0001"  # untouched
        mock_store.async_save.assert_not_awaited()

    async def test_rewires_all_matching_even_on_collision(
        self, manager, mock_store
    ):
        """v0.5.7: multiple triggers per fingerprint are legal (they may carry
        different receiver scopes), so a fingerprint collision no longer blocks
        the rewire. Every trigger bound to the old fingerprint is repointed."""
        mock_store.async_save = AsyncMock()
        bound = _make_trigger(name="A", fingerprint="OLD")
        owner = _make_trigger(name="B", fingerprint="NEW")
        mock_store.add_trigger(bound)
        mock_store.add_trigger(owner)
        result = await manager.rewire("OLD", "NEW", "PRONTO", "0000 DDDD")
        assert result == {"rewired": ["A"], "skipped": []}
        assert bound.signal_fingerprint == "NEW"  # rewired despite collision
        assert owner.signal_fingerprint == "NEW"  # untouched (already NEW)
        mock_store.async_save.assert_awaited_once()

    async def test_ignores_unbound_triggers(self, manager, mock_store):
        mock_store.async_save = AsyncMock()
        other = _make_trigger(name="Other", fingerprint="DIFFERENT")
        mock_store.add_trigger(other)
        result = await manager.rewire("OLD", "NEW", "PRONTO", "0000 EEEE")
        assert result == {"rewired": [], "skipped": []}
        assert other.signal_fingerprint == "DIFFERENT"
        mock_store.async_save.assert_not_awaited()


class TestIRTriggerModel:
    """Test IRTrigger to_dict/from_dict roundtrip."""

    def test_roundtrip(self):
        trigger = _make_trigger(name="Power", min_hits=3)
        data = trigger.to_dict()
        restored = IRTrigger.from_dict(data)
        assert restored.name == "Power"
        assert restored.min_hits == 3
        assert restored.signal_fingerprint == "fp1"
        assert restored.protocol == "pronto"
        assert restored.code == "0000 0001"
        assert restored.enabled is True
        assert restored.id == trigger.id

    def test_from_dict_defaults(self):
        trigger = IRTrigger.from_dict({"name": "Minimal"})
        assert trigger.name == "Minimal"
        assert trigger.min_hits == 1
        assert trigger.enabled is True
        assert trigger.signal_fingerprint == ""
        assert trigger.id  # auto-generated

    def test_from_dict_disabled(self):
        trigger = IRTrigger.from_dict({"name": "Off", "enabled": False})
        assert trigger.enabled is False


class TestTriggerStorage:
    """Test trigger CRUD on HAIRStore."""

    def test_add_and_get(self, mock_store):
        t = _make_trigger(name="TV Power")
        mock_store.add_trigger(t)
        assert mock_store.get_trigger(t.id) is t

    def test_get_all(self, mock_store):
        t1 = _make_trigger(name="A")
        t2 = _make_trigger(name="B")
        mock_store.add_trigger(t1)
        mock_store.add_trigger(t2)
        assert len(mock_store.get_all_triggers()) == 2

    def test_get_enabled(self, mock_store):
        t1 = _make_trigger(name="On", enabled=True)
        t2 = _make_trigger(name="Off", enabled=False)
        mock_store.add_trigger(t1)
        mock_store.add_trigger(t2)
        enabled = mock_store.get_enabled_triggers()
        assert len(enabled) == 1
        assert enabled[0].name == "On"

    def test_remove(self, mock_store):
        t = _make_trigger()
        mock_store.add_trigger(t)
        assert mock_store.remove_trigger(t.id) is True
        assert mock_store.get_trigger(t.id) is None

    def test_remove_nonexistent(self, mock_store):
        assert mock_store.remove_trigger("nope") is False

    def test_get_by_fingerprint(self, mock_store):
        t = _make_trigger(fingerprint="unique_fp")
        mock_store.add_trigger(t)
        found = mock_store.get_trigger_by_fingerprint("unique_fp")
        assert found is t
        assert mock_store.get_trigger_by_fingerprint("other") is None

    def test_get_triggers_by_fingerprint_returns_all(self, mock_store):
        """v0.5.7: multiple triggers per fingerprint (different scopes)."""
        a = _make_trigger(name="Garage", fingerprint="shared_fp")
        b = _make_trigger(name="Kitchen", fingerprint="shared_fp")
        mock_store.add_trigger(a)
        mock_store.add_trigger(b)
        matches = mock_store.get_triggers_by_fingerprint("shared_fp")
        assert {t.name for t in matches} == {"Garage", "Kitchen"}
        assert mock_store.get_triggers_by_fingerprint("none") == []

    def test_get_triggers_for_signal_by_code(self, mock_store):
        t = _make_trigger(protocol="pronto", code="ABCD")
        mock_store.add_trigger(t)
        matches = mock_store.get_triggers_for_signal("pronto", "ABCD", "fp1")
        assert len(matches) == 1
        assert matches[0].id == t.id

    def test_get_triggers_for_signal_by_fingerprint(self, mock_store):
        t = _make_trigger(protocol=None, code=None, fingerprint="fp_match")
        mock_store.add_trigger(t)
        matches = mock_store.get_triggers_for_signal(None, None, "fp_match")
        assert len(matches) == 1

    def test_get_triggers_skips_disabled(self, mock_store):
        t = _make_trigger(enabled=False)
        mock_store.add_trigger(t)
        matches = mock_store.get_triggers_for_signal("pronto", "0000 0001", "fp1")
        assert len(matches) == 0

    def test_serialization_includes_triggers(self, mock_store):
        t = _make_trigger(name="Serialize Me")
        mock_store.add_trigger(t)
        data = mock_store._serialize()
        assert "triggers" in data
        assert len(data["triggers"]) == 1
        assert data["triggers"][0]["name"] == "Serialize Me"


class TestTriggerManagerHitCounting:
    """Test hit counting with min_hits and 5s reset window.

    Distinct presses are spaced past the 60ms multi-receiver dedup window via
    the ``clock`` fixture, matching real-world press timing.
    """

    def test_min_hits_1_fires_immediately(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert t.id in fired

    def test_min_hits_3_requires_three_hits(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=3)
        mock_store.add_trigger(t)

        # Hits 1 and 2 should not fire.
        assert manager.on_signal_captured("fp1", "pronto", "0000 0001") == []
        clock.advance(1.0)
        assert manager.on_signal_captured("fp1", "pronto", "0000 0001") == []
        clock.advance(1.0)

        # Hit 3 should fire.
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert t.id in fired

    def test_counter_resets_after_fire(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=2)
        mock_store.add_trigger(t)

        assert manager.on_signal_captured("fp1", "pronto", "0000 0001") == []
        clock.advance(1.0)
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert t.id in fired
        clock.advance(1.0)

        # Counter should have reset; next single hit should not fire.
        assert manager.on_signal_captured("fp1", "pronto", "0000 0001") == []
        clock.advance(1.0)
        # But second hit should fire again.
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert t.id in fired

    def test_reset_window_clears_counter(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=3)
        mock_store.add_trigger(t)

        # Two hits within window.
        manager.on_signal_captured("fp1", "pronto", "0000 0001")
        clock.advance(1.0)
        manager.on_signal_captured("fp1", "pronto", "0000 0001")

        # Simulate 6 seconds passing since the chain STARTED (the window
        # anchors at the first press as of v0.6.3).
        state = manager._hit_states[t.id]
        state.first_hit = clock.monotonic() - 6
        clock.advance(1.0)

        # Next hit should reset counter to 1 (not accumulate to 3).
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert fired == []
        assert state.count == 1

    def test_window_anchors_at_first_press(self, manager, mock_store, clock):
        """The owner's bench case (v0.6.3): 2 presses, a pause that keeps
        every GAP under 5s, 2 more presses. Under the pre-0.6.3 sliding
        window this fired; anchored at the first press, the chain expires
        and the late presses start a fresh one."""
        t = _make_trigger(min_hits=4)
        mock_store.add_trigger(t)

        manager.on_signal_captured("fp1", "pronto", "0000 0001")
        clock.advance(1.0)
        manager.on_signal_captured("fp1", "pronto", "0000 0001")
        # 4.5s pause: gap < 5s, but 5.5s total since the first press.
        clock.advance(4.5)
        fired3 = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        clock.advance(1.0)
        fired4 = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert fired3 == []
        assert fired4 == []  # presses 3+4 are a fresh chain of 2, not 4
        assert manager._hit_states[t.id].count == 2

    def test_four_quick_presses_fire(self, manager, mock_store, clock):
        """All four presses inside 5s of the first still fire."""
        t = _make_trigger(min_hits=4)
        mock_store.add_trigger(t)
        fired = []
        for _ in range(4):
            fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
            clock.advance(1.0)
        assert t.id in fired

    def test_disabled_trigger_does_not_fire(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=1, enabled=False)
        mock_store.add_trigger(t)
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert fired == []

    def test_no_triggers_returns_empty(self, manager, clock):
        fired = manager.on_signal_captured("fp1", "pronto", "0000 0001")
        assert fired == []

    def test_fires_ha_bus_event(self, manager, mock_store, mock_hass, clock):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)
        manager.on_signal_captured("fp1", "pronto", "0000 0001", "dev_fp")

        mock_hass.bus.async_fire.assert_called_once()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == "hair_trigger_fired"
        event_data = call_args[0][1]
        assert event_data["trigger_id"] == t.id
        assert event_data["trigger_name"] == t.name
        # Location-aware fields present (None for an unscoped/legacy capture).
        assert event_data["receiver_entity_id"] is None
        assert event_data["receiver_area_id"] is None
        assert event_data["receiver_area_name"] is None

    def test_entity_callback_called(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)

        cb = MagicMock()
        manager.register_entity_callback(cb)

        manager.on_signal_captured("fp1", "pronto", "0000 0001")
        cb.assert_called_once()
        assert cb.call_args[0][0] == t.id

    def test_ws_subscriber_notified(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)

        cb = MagicMock()
        manager.subscribe(cb)

        manager.on_signal_captured("fp1", "pronto", "0000 0001")
        cb.assert_called_once()

    def test_unsubscribe(self, manager, mock_store, clock):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)

        cb = MagicMock()
        manager.subscribe(cb)
        manager.unsubscribe(cb)

        manager.on_signal_captured("fp1", "pronto", "0000 0001")
        cb.assert_not_called()
