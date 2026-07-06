"""Tests for v0.5.7 location-aware triggers.

Covers the Section 7 matrix from
``docs/internal/plans/location-aware-triggers.md``:
- receiver scope matching (5.1),
- multi-receiver 60ms dedup composed with min_hits,
- receiver + area fields in the fire payload,
- entity/device/area registry resolution at fire time,
- IRTrigger.from_dict lazy migration of receiver_entity_ids.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
    """Controllable monotonic clock for TriggerManager time-based logic."""

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


def _trigger(
    *,
    name: str = "T",
    fingerprint: str = "fp1",
    protocol: str = "pronto",
    code: str = "c1",
    min_hits: int = 1,
    receivers: list[str] | None = None,
) -> IRTrigger:
    return IRTrigger(
        name=name,
        signal_fingerprint=fingerprint,
        protocol=protocol,
        code=code,
        min_hits=min_hits,
        receiver_entity_ids=receivers or [],
    )


# ---------------------------------------------------------------------------
# 7.1 matches_receiver (scope matrix)
# ---------------------------------------------------------------------------


class TestMatchesReceiver:
    def test_unscoped_matches_any_including_none(self):
        t = _trigger(receivers=[])
        assert t.matches_receiver("infrared.garage")
        assert t.matches_receiver("infrared.kitchen")
        assert t.matches_receiver(None)  # legacy capture

    def test_scoped_matches_only_listed(self):
        t = _trigger(receivers=["infrared.garage"])
        assert t.matches_receiver("infrared.garage")
        assert not t.matches_receiver("infrared.kitchen")

    def test_scoped_never_matches_legacy_none(self):
        t = _trigger(receivers=["infrared.garage"])
        assert not t.matches_receiver(None)

    def test_scoped_multi_receiver_union(self):
        t = _trigger(receivers=["infrared.garage", "infrared.kitchen"])
        assert t.matches_receiver("infrared.garage")
        assert t.matches_receiver("infrared.kitchen")
        assert not t.matches_receiver("infrared.den")


# ---------------------------------------------------------------------------
# Scope firing
# ---------------------------------------------------------------------------


class TestScopeFiring:
    def test_scoped_fires_only_for_matching_receiver(
        self, manager, mock_store, clock
    ):
        t = _trigger(receivers=["infrared.garage"])
        mock_store.add_trigger(t)

        # Non-matching receiver -> no fire.
        assert (
            manager.on_signal_captured("fp1", "pronto", "c1", None, "infrared.kitchen")
            == []
        )
        clock.advance(1.0)
        # Matching receiver -> fires.
        assert t.id in manager.on_signal_captured(
            "fp1", "pronto", "c1", None, "infrared.garage"
        )

    def test_scoped_does_not_match_legacy_none(self, manager, mock_store, clock):
        t = _trigger(receivers=["infrared.garage"])
        mock_store.add_trigger(t)
        assert manager.on_signal_captured("fp1", "pronto", "c1", None, None) == []

    def test_unscoped_fires_for_legacy_none(self, manager, mock_store, clock):
        t = _trigger(receivers=[])
        mock_store.add_trigger(t)
        assert t.id in manager.on_signal_captured("fp1", "pronto", "c1", None, None)

    def test_two_scoped_triggers_same_fingerprint_fire_independently(
        self, manager, mock_store, clock
    ):
        garage = _trigger(name="Garage", receivers=["infrared.garage"])
        kitchen = _trigger(name="Kitchen", receivers=["infrared.kitchen"])
        mock_store.add_trigger(garage)
        mock_store.add_trigger(kitchen)

        fired_g = manager.on_signal_captured(
            "fp1", "pronto", "c1", None, "infrared.garage"
        )
        assert fired_g == [garage.id]
        clock.advance(1.0)
        fired_k = manager.on_signal_captured(
            "fp1", "pronto", "c1", None, "infrared.kitchen"
        )
        assert fired_k == [kitchen.id]


# ---------------------------------------------------------------------------
# 7.2 Multi-receiver dedup composed with min_hits
# ---------------------------------------------------------------------------


class TestMultiReceiverDedup:
    def test_same_press_two_receivers_fires_once(self, manager, mock_store, clock):
        t = _trigger(min_hits=1, receivers=[])
        mock_store.add_trigger(t)

        # First receiver sees the press -> fire.
        assert t.id in manager.on_signal_captured(
            "fp1", "pronto", "c1", None, "infrared.garage"
        )
        # Second receiver sees the SAME press 20ms later -> within dedup -> no fire.
        clock.advance(0.02)
        assert (
            manager.on_signal_captured("fp1", "pronto", "c1", None, "infrared.kitchen")
            == []
        )

    def test_distinct_presses_beyond_window_each_fire(
        self, manager, mock_store, clock
    ):
        t = _trigger(min_hits=1, receivers=[])
        mock_store.add_trigger(t)
        assert t.id in manager.on_signal_captured("fp1", "pronto", "c1", None, "g")
        clock.advance(0.2)  # > 60ms dedup window
        assert t.id in manager.on_signal_captured("fp1", "pronto", "c1", None, "g")

    def test_min_hits_two_receivers_of_one_press_count_once(
        self, manager, mock_store, clock
    ):
        t = _trigger(min_hits=2, receivers=[])
        mock_store.add_trigger(t)

        # Press 1 observed by two receivers within the window -> one hit, no fire.
        assert manager.on_signal_captured("fp1", "pronto", "c1", None, "g") == []
        clock.advance(0.02)
        assert manager.on_signal_captured("fp1", "pronto", "c1", None, "k") == []
        # Press 2 (a real second press) -> second hit -> fires.
        clock.advance(1.0)
        assert t.id in manager.on_signal_captured("fp1", "pronto", "c1", None, "g")


# ---------------------------------------------------------------------------
# 7.4 Fire payload additions + area resolution
# ---------------------------------------------------------------------------


class TestFirePayload:
    def test_payload_carries_receiver_and_area(
        self, manager, mock_store, mock_hass, clock
    ):
        t = _trigger(min_hits=1, receivers=["infrared.garage"])
        mock_store.add_trigger(t)
        with patch.object(
            manager, "_resolve_receiver_area", return_value=("area_g", "Garage")
        ):
            manager.on_signal_captured(
                "fp1", "pronto", "c1", None, "infrared.garage"
            )
        data = mock_hass.bus.async_fire.call_args[0][1]
        assert data["receiver_entity_id"] == "infrared.garage"
        assert data["receiver_area_id"] == "area_g"
        assert data["receiver_area_name"] == "Garage"

    def test_payload_none_for_legacy_capture(
        self, manager, mock_store, mock_hass, clock
    ):
        t = _trigger(min_hits=1, receivers=[])
        mock_store.add_trigger(t)
        manager.on_signal_captured("fp1", "pronto", "c1", None, None)
        data = mock_hass.bus.async_fire.call_args[0][1]
        assert data["receiver_entity_id"] is None
        assert data["receiver_area_id"] is None
        assert data["receiver_area_name"] is None


class TestResolveReceiverArea:
    def test_none_receiver_short_circuits(self, manager):
        assert manager._resolve_receiver_area(None) == (None, None)

    def test_full_chain_resolves(self, manager, monkeypatch):
        ent_reg = MagicMock()
        ent_reg.async_get.return_value = SimpleNamespace(device_id="dev1")
        dev_reg = MagicMock()
        dev_reg.async_get.return_value = SimpleNamespace(area_id="area1")
        area_reg = MagicMock()
        area_reg.async_get_area.return_value = SimpleNamespace(name="Garage")
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.er.async_get",
            lambda _h: ent_reg,
        )
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.dr.async_get",
            lambda _h: dev_reg,
        )
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.ar.async_get",
            lambda _h: area_reg,
        )
        assert manager._resolve_receiver_area("infrared.garage") == (
            "area1",
            "Garage",
        )

    def test_deviceless_entity_returns_none(self, manager, monkeypatch):
        ent_reg = MagicMock()
        ent_reg.async_get.return_value = SimpleNamespace(device_id=None)
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.er.async_get",
            lambda _h: ent_reg,
        )
        assert manager._resolve_receiver_area("infrared.x") == (None, None)

    def test_area_rename_reflected_on_next_fire(self, manager, monkeypatch):
        """Area is resolved fresh at fire time -- a rename shows up next fire."""
        ent_reg = MagicMock()
        ent_reg.async_get.return_value = SimpleNamespace(device_id="dev1")
        dev_reg = MagicMock()
        dev_reg.async_get.return_value = SimpleNamespace(area_id="area1")
        area_reg = MagicMock()
        area_reg.async_get_area.return_value = SimpleNamespace(name="Garage")
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.er.async_get", lambda _h: ent_reg
        )
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.dr.async_get", lambda _h: dev_reg
        )
        monkeypatch.setattr(
            "custom_components.hair.trigger_manager.ar.async_get", lambda _h: area_reg
        )
        assert manager._resolve_receiver_area("x")[1] == "Garage"
        # Rename the area in the registry -- next resolution reflects it.
        area_reg.async_get_area.return_value = SimpleNamespace(name="Workshop")
        assert manager._resolve_receiver_area("x")[1] == "Workshop"


# ---------------------------------------------------------------------------
# 7.5 from_dict lazy migration
# ---------------------------------------------------------------------------


class TestFromDictMigration:
    def test_missing_key_defaults_empty(self):
        t = IRTrigger.from_dict({"name": "Legacy"})
        assert t.receiver_entity_ids == []

    def test_null_key_defaults_empty(self):
        t = IRTrigger.from_dict({"name": "X", "receiver_entity_ids": None})
        assert t.receiver_entity_ids == []

    def test_reads_present_key(self):
        t = IRTrigger.from_dict(
            {"name": "X", "receiver_entity_ids": ["infrared.a", "infrared.b"]}
        )
        assert t.receiver_entity_ids == ["infrared.a", "infrared.b"]

    def test_roundtrip_preserves(self):
        t = _trigger(receivers=["infrared.garage"])
        restored = IRTrigger.from_dict(t.to_dict())
        assert restored.receiver_entity_ids == ["infrared.garage"]
