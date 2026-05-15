"""Tests for HAIR TriggerManager."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

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
    """Test hit counting with min_hits and 5s reset window."""

    def test_min_hits_1_fires_immediately(self, manager, mock_store):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert t.id in fired

    def test_min_hits_3_requires_three_hits(self, manager, mock_store):
        t = _make_trigger(min_hits=3)
        mock_store.add_trigger(t)

        # Hits 1 and 2 should not fire.
        assert manager.on_signal("fp1", "pronto", "0000 0001") == []
        assert manager.on_signal("fp1", "pronto", "0000 0001") == []

        # Hit 3 should fire.
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert t.id in fired

    def test_counter_resets_after_fire(self, manager, mock_store):
        t = _make_trigger(min_hits=2)
        mock_store.add_trigger(t)

        assert manager.on_signal("fp1", "pronto", "0000 0001") == []
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert t.id in fired

        # Counter should have reset; next single hit should not fire.
        assert manager.on_signal("fp1", "pronto", "0000 0001") == []
        # But second hit should fire again.
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert t.id in fired

    def test_reset_window_clears_counter(self, manager, mock_store):
        t = _make_trigger(min_hits=3)
        mock_store.add_trigger(t)

        # Two hits within window.
        manager.on_signal("fp1", "pronto", "0000 0001")
        manager.on_signal("fp1", "pronto", "0000 0001")

        # Simulate 6 seconds passing (beyond 5s window).
        state = manager._hit_states[t.id]
        state.last_hit = time.monotonic() - 6

        # Next hit should reset counter to 1 (not accumulate to 3).
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert fired == []
        assert state.count == 1

    def test_disabled_trigger_does_not_fire(self, manager, mock_store):
        t = _make_trigger(min_hits=1, enabled=False)
        mock_store.add_trigger(t)
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert fired == []

    def test_no_triggers_returns_empty(self, manager):
        fired = manager.on_signal("fp1", "pronto", "0000 0001")
        assert fired == []

    def test_fires_ha_bus_event(self, manager, mock_store, mock_hass):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)
        manager.on_signal("fp1", "pronto", "0000 0001", "dev_fp")

        mock_hass.bus.async_fire.assert_called_once()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == "hair_trigger_fired"
        event_data = call_args[0][1]
        assert event_data["trigger_id"] == t.id
        assert event_data["trigger_name"] == t.name

    def test_entity_callback_called(self, manager, mock_store):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)

        cb = MagicMock()
        manager.register_entity_callback(cb)

        manager.on_signal("fp1", "pronto", "0000 0001")
        cb.assert_called_once()
        assert cb.call_args[0][0] == t.id

    def test_ws_subscriber_notified(self, manager, mock_store):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)

        cb = MagicMock()
        manager.subscribe(cb)

        manager.on_signal("fp1", "pronto", "0000 0001")
        cb.assert_called_once()

    def test_unsubscribe(self, manager, mock_store):
        t = _make_trigger(min_hits=1)
        mock_store.add_trigger(t)

        cb = MagicMock()
        manager.subscribe(cb)
        manager.unsubscribe(cb)

        manager.on_signal("fp1", "pronto", "0000 0001")
        cb.assert_not_called()
