"""Tests for the HAIR Triggers device_trigger platform.

Covers docs/internal/plans/trigger-remotes-release-a.md's "Ruling: device
triggers ship in Release A" (2026-08-10): the automation-editor dropdown
lists stored triggers in order; async_attach_trigger resolves a subtype to
a live trigger id (current names first, then alias history); a rename
keeps an already-attached listener firing (id-keyed filter, resolved once
at attach time) and lets a NEWLY (re-)attached automation still resolve an
OLD subtype via alias history; a name one trigger abandons and another
later reclaims routes to the live claimant, never the stale history entry
("live names always win"); and the retention guarantee -- one physical
press fires both the pre-existing event entity (TriggerManager /
event.py's HAIRTriggerEventEntity) and this device-trigger door, since
both listen on the same EVENT_TRIGGER_FIRED bus event keyed by trigger_id.

async_attach_trigger delegates the actual listening to HA's own
event-trigger platform (homeassistant.components.homeassistant.triggers.
event), which the root conftest stubs permissively for import purposes.
These tests monkeypatch event_trigger.async_attach_trigger directly to
capture the constructed event_data filter, rather than simulating a full
working HA event bus -- fake_hass/mock_hass's hass.bus.async_listen is a
disconnected MagicMock in this suite (see tests/conftest.py), not real
pub/sub. True end-to-end firing is verified on the bench (VM999), not here.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import device_trigger
from custom_components.hair.const import DOMAIN, EVENT_TRIGGER_FIRED
from custom_components.hair.event import TRIGGER_DEVICE_ID
from custom_components.hair.models import IRTrigger
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager

ENTRY_ID = "test-entry"


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
def wired_hass(mock_hass, mock_store):
    """hass.data wired the way __init__.py leaves it for one config entry.

    device_trigger._get_first_entry_data scans hass.data[DOMAIN].values()
    for a dict carrying a "device_manager" key (the same duplicated-helper
    shape as websocket_api.py's private helper); a bare "store" key alone
    is not enough to be found, mirroring the real runtime shape.
    """
    mock_hass.data = {
        DOMAIN: {
            ENTRY_ID: {
                "store": mock_store,
                "device_manager": MagicMock(),
            }
        }
    }
    return mock_hass


def _hair_triggers_device_entry():
    return SimpleNamespace(identifiers={(DOMAIN, TRIGGER_DEVICE_ID)})


def _other_device_entry():
    return SimpleNamespace(identifiers={("other_domain", "other-id")})


def _trigger(*, name: str = "Power", fingerprint: str = "fp1", **kw) -> IRTrigger:
    return IRTrigger(name=name, signal_fingerprint=fingerprint, **kw)


# ---------------------------------------------------------------------------
# async_get_triggers -- the automation-editor dropdown
# ---------------------------------------------------------------------------


class TestAsyncGetTriggers:
    async def test_lists_current_names_in_order(
        self, wired_hass, mock_store, monkeypatch
    ):
        monkeypatch.setattr(
            device_trigger.dr,
            "async_get",
            lambda _h: SimpleNamespace(
                async_get=lambda _id: _hair_triggers_device_entry()
            ),
        )
        t1 = _trigger(name="Power", fingerprint="fp1")
        t2 = _trigger(name="Volume Up", fingerprint="fp2")
        mock_store.add_trigger(t1)
        mock_store.add_trigger(t2)

        result = await device_trigger.async_get_triggers(wired_hass, "dev-1")

        assert [r[device_trigger.CONF_SUBTYPE] for r in result] == [
            "Power",
            "Volume Up",
        ]
        assert all(
            r[device_trigger.CONF_TYPE] == device_trigger.TRIGGER_TYPE_BUTTON_PRESSED
            for r in result
        )
        assert all(r[device_trigger.CONF_DOMAIN] == DOMAIN for r in result)
        assert all(r[device_trigger.CONF_DEVICE_ID] == "dev-1" for r in result)

    async def test_non_hair_triggers_device_returns_empty(
        self, wired_hass, mock_store, monkeypatch
    ):
        monkeypatch.setattr(
            device_trigger.dr,
            "async_get",
            lambda _h: SimpleNamespace(async_get=lambda _id: _other_device_entry()),
        )
        mock_store.add_trigger(_trigger())
        assert await device_trigger.async_get_triggers(wired_hass, "dev-1") == []

    async def test_unknown_device_returns_empty(self, wired_hass, monkeypatch):
        monkeypatch.setattr(
            device_trigger.dr,
            "async_get",
            lambda _h: SimpleNamespace(async_get=lambda _id: None),
        )
        assert await device_trigger.async_get_triggers(wired_hass, "dev-1") == []


# ---------------------------------------------------------------------------
# _resolve_subtype -- current names first, then alias history
# ---------------------------------------------------------------------------


class TestResolveSubtype:
    def test_resolves_current_name(self, wired_hass, mock_store):
        t = _trigger(name="Power")
        mock_store.add_trigger(t)
        assert device_trigger._resolve_subtype(wired_hass, "Power") == t.id

    def test_resolves_via_alias_history_after_rename(self, wired_hass, mock_store):
        t = _trigger(name="Power")
        mock_store.add_trigger(t)
        t.rename("Power Toggle")

        assert device_trigger._resolve_subtype(wired_hass, "Power") == t.id
        assert device_trigger._resolve_subtype(wired_hass, "Power Toggle") == t.id

    def test_reclaimed_name_routes_to_live_claimant(self, wired_hass, mock_store):
        """A name one trigger abandons and another later reclaims always
        resolves to the live claimant -- the owner's "live names always
        win" rule."""
        old = _trigger(name="Power", fingerprint="fp1")
        mock_store.add_trigger(old)
        old.rename("Power (old)")  # "Power" now lives only in old's history

        new = _trigger(name="Power", fingerprint="fp2")
        mock_store.add_trigger(new)

        assert device_trigger._resolve_subtype(wired_hass, "Power") == new.id

    def test_deleted_trigger_resolves_to_none(self, wired_hass, mock_store):
        t = _trigger(name="Power")
        mock_store.add_trigger(t)
        mock_store.remove_trigger(t.id)
        assert device_trigger._resolve_subtype(wired_hass, "Power") is None

    def test_unknown_subtype_resolves_to_none(self, wired_hass, mock_store):
        assert device_trigger._resolve_subtype(wired_hass, "Nonexistent") is None

    def test_no_entry_data_resolves_to_none(self, mock_hass):
        mock_hass.data = {}
        assert device_trigger._resolve_subtype(mock_hass, "Power") is None


# ---------------------------------------------------------------------------
# async_validate_trigger_config -- deliberately permissive
# ---------------------------------------------------------------------------


class TestValidateTriggerConfig:
    async def test_permissive_accepts_config_without_checking_liveness(
        self, wired_hass
    ):
        """A renamed or deleted trigger's stored subtype must still pass
        validation on every HA restart/reload; liveness is resolved only
        at attach time (see async_attach_trigger)."""
        config = {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": "dev-1",
            "type": device_trigger.TRIGGER_TYPE_BUTTON_PRESSED,
            "subtype": "Some Deleted Trigger",
        }
        validated = await device_trigger.async_validate_trigger_config(
            wired_hass, config
        )
        assert validated["subtype"] == "Some Deleted Trigger"


# ---------------------------------------------------------------------------
# async_attach_trigger
# ---------------------------------------------------------------------------


class TestAsyncAttachTrigger:
    async def test_attach_resolves_current_name_and_filters_on_id(
        self, wired_hass, mock_store, monkeypatch
    ):
        t = _trigger(name="Power")
        mock_store.add_trigger(t)

        attach_mock = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(
            device_trigger.event_trigger, "async_attach_trigger", attach_mock
        )

        config = {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": "dev-1",
            "type": device_trigger.TRIGGER_TYPE_BUTTON_PRESSED,
            "subtype": "Power",
        }
        await device_trigger.async_attach_trigger(
            wired_hass, config, MagicMock(), {}
        )

        attach_mock.assert_awaited_once()
        event_config = attach_mock.await_args.args[1]
        assert (
            event_config[device_trigger.event_trigger.CONF_EVENT_TYPE]
            == EVENT_TRIGGER_FIRED
        )
        assert (
            event_config[device_trigger.event_trigger.CONF_EVENT_DATA]["trigger_id"]
            == t.id
        )
        assert attach_mock.await_args.kwargs["platform_type"] == "device"

    async def test_attach_after_rename_still_resolves_old_subtype(
        self, wired_hass, mock_store, monkeypatch
    ):
        """An automation attached (or re-attached, e.g. HA restart) AFTER
        a rename, still carrying the OLD subtype in its stored config,
        resolves to the correct, still-current trigger id."""
        t = _trigger(name="Power")
        mock_store.add_trigger(t)
        t.rename("Power Toggle")

        attach_mock = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(
            device_trigger.event_trigger, "async_attach_trigger", attach_mock
        )

        config = {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": "dev-1",
            "type": device_trigger.TRIGGER_TYPE_BUTTON_PRESSED,
            "subtype": "Power",
        }
        await device_trigger.async_attach_trigger(
            wired_hass, config, MagicMock(), {}
        )

        event_config = attach_mock.await_args.args[1]
        assert (
            event_config[device_trigger.event_trigger.CONF_EVENT_DATA]["trigger_id"]
            == t.id
        )

    async def test_unresolved_subtype_attaches_to_a_never_firing_filter(
        self, wired_hass, monkeypatch
    ):
        """A deleted trigger's automation attaches cleanly (HA convention)
        and simply never fires again -- no sweep, no error."""
        attach_mock = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(
            device_trigger.event_trigger, "async_attach_trigger", attach_mock
        )

        config = {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": "dev-1",
            "type": device_trigger.TRIGGER_TYPE_BUTTON_PRESSED,
            "subtype": "Long Gone",
        }
        await device_trigger.async_attach_trigger(
            wired_hass, config, MagicMock(), {}
        )

        event_config = attach_mock.await_args.args[1]
        fired_trigger_id = event_config[device_trigger.event_trigger.CONF_EVENT_DATA][
            "trigger_id"
        ]
        # Sentinel never matches a real stored trigger id (uuid4 strings).
        assert fired_trigger_id == device_trigger._UNRESOLVED_SENTINEL


# ---------------------------------------------------------------------------
# Retention guarantee: one press satisfies both doors
# ---------------------------------------------------------------------------


class TestRetentionGuarantee:
    def test_one_press_fires_both_event_entity_and_device_trigger_id(
        self, wired_hass, mock_store
    ):
        """TriggerManager fires the SAME bus event (EVENT_TRIGGER_FIRED,
        keyed by trigger_id) that both the pre-existing event entity
        (event.py's HAIRTriggerEventEntity, wired via
        register_entity_callback) and this device_trigger door listen on.
        A device trigger attached with the trigger's current name as its
        subtype resolves to the SAME trigger id TriggerManager fires with,
        so the physical press that already drives the event entity also
        satisfies an automation built via Device -> HAIR Triggers ->
        <name> -- nobody's existing event-entity automation changes.
        """
        t = _trigger(name="Power", fingerprint="fp1", protocol="pronto", code="c1")
        mock_store.add_trigger(t)

        entity_fired: list[tuple[str, dict]] = []
        manager = TriggerManager(wired_hass, mock_store)
        manager.register_entity_callback(
            lambda trigger_id, event_data: entity_fired.append(
                (trigger_id, event_data)
            )
        )

        fired_ids = manager.on_signal_captured("fp1", "pronto", "c1", None, None)

        assert fired_ids == [t.id]
        assert entity_fired, "the event entity callback must fire alongside the bus event"
        assert entity_fired[0][0] == t.id

        bus_event_data = wired_hass.bus.async_fire.call_args[0][1]
        assert bus_event_data["trigger_id"] == t.id

        # Independently: a device trigger subscribed with the trigger's
        # CURRENT name as its subtype resolves to the identical id.
        assert device_trigger._resolve_subtype(wired_hass, t.name) == t.id

    def test_rename_after_attach_keeps_the_same_id_firing(
        self, wired_hass, mock_store
    ):
        """Renaming a trigger never changes its id, so an automation
        already attached (id-keyed filter, resolved once at attach time)
        keeps firing on the exact same physical press after a rename --
        nobody's existing automation breaks."""
        t = _trigger(name="Power", fingerprint="fp1", protocol="pronto", code="c1")
        mock_store.add_trigger(t)
        manager = TriggerManager(wired_hass, mock_store)

        attached_trigger_id = device_trigger._resolve_subtype(wired_hass, "Power")
        assert attached_trigger_id == t.id

        t.rename("Power Toggle")

        fired_ids = manager.on_signal_captured("fp1", "pronto", "c1", None, None)
        assert fired_ids == [t.id]
        bus_event_data = wired_hass.bus.async_fire.call_args[0][1]
        assert bus_event_data["trigger_id"] == attached_trigger_id
