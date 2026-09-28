"""The device-registry lookups, off the deprecated door.

Home Assistant deprecated ``DeviceRegistry.async_get_device`` because an
identifier is unique only within a config entry. It warns on 2026.9 (the
test box logged 46 of those warnings against HAIR) and is removed in
2027.8.0. The replacements landed in 2026.8.0, four releases above the
2026.4.0 floor in ``hacs.json``, so HAIR needs both paths and a pin on
each.

WHY THE REGISTRIES HERE ARE HAND-WRITTEN CLASSES rather than mocks. The
suite's usual registry double is a ``MagicMock``, which answers every
attribute request, so it cannot tell the two Home Assistant generations
apart: it claims the new API and then returns a mock in place of a
device. ``_NewRegistry`` below carries exactly what 2026.8+ carries,
``_OldRegistry`` exactly what 2026.4 through 2026.7 carried, and
``_NewRegistry.async_get_device`` FAILS the test if anything calls it,
which is the pin that the new path never reaches the deprecated door.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.device_registry_compat import (
    NEW_API_HA_VERSION,
    device_by_connection,
    device_by_identifier,
    hair_config_entry_id,
)

HAIR_ENTRY = "entry-1"
BROADLINK_ENTRY = "broadlink-entry-9"


class _NewRegistry:
    """A 2026.8+ registry: the three replacements, and a trap.

    ``devices`` maps ``(kind, key, config_entry_id or None)`` to the
    device returned, so a test can say exactly which scoping it expects
    to be asked for.
    """

    def __init__(self, devices: dict | None = None):
        self.devices = devices or {}
        self.calls: list[tuple] = []
        self.removed: list[str] = []
        self.updated: list[tuple] = []

    def async_get_device_by_identifier(self, identifier, config_entry_id):
        self.calls.append(("identifier", identifier, config_entry_id))
        return self.devices.get(("identifier", identifier, config_entry_id))

    def async_get_device_by_connection(self, connection, config_entry_id):
        self.calls.append(("connection", connection, config_entry_id))
        return self.devices.get(("connection", connection, config_entry_id))

    def async_get_devices(
        self, *, identifiers=None, connections=None, config_entry_id=None
    ):
        self.calls.append(
            ("devices", identifiers, connections, config_entry_id)
        )
        found = []
        for key in identifiers or ():
            device = self.devices.get(("identifier", key, config_entry_id))
            if device is not None:
                found.append(device)
        for key in connections or ():
            device = self.devices.get(("connection", key, config_entry_id))
            if device is not None:
                found.append(device)
        return found

    def async_get_device(self, identifiers=None, connections=None):
        raise AssertionError(
            "the deprecated async_get_device was called on a registry that "
            "has the 2026.8 replacements"
        )

    # Write-side calls the handlers make after a lookup.
    def async_remove_device(self, device_id):
        self.removed.append(device_id)

    def async_update_device(self, device_id, **kwargs):
        self.updated.append((device_id, kwargs))


class _OldRegistry:
    """A 2026.4 to 2026.7 registry: one door, no scoping."""

    def __init__(self, device=None):
        self.device = device
        self.calls: list[dict] = []
        self.removed: list[str] = []
        self.updated: list[tuple] = []

    def async_get_device(self, identifiers=None, connections=None):
        self.calls.append(
            {"identifiers": identifiers, "connections": connections}
        )
        return self.device

    def async_remove_device(self, device_id):
        self.removed.append(device_id)

    def async_update_device(self, device_id, **kwargs):
        self.updated.append((device_id, kwargs))


def _device(device_id: str):
    return SimpleNamespace(id=device_id, name=device_id, name_by_user=None)


# ---------------------------------------------------------------------------
# The helper itself
# ---------------------------------------------------------------------------


class TestDeviceByIdentifier:
    def test_a_known_entry_uses_the_scoped_call(self):
        wanted = _device("ha-1")
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "dev-1"), HAIR_ENTRY): wanted
        })
        found = device_by_identifier(
            registry, (DOMAIN, "dev-1"), HAIR_ENTRY
        )
        assert found is wanted
        assert registry.calls == [
            ("identifier", (DOMAIN, "dev-1"), HAIR_ENTRY)
        ]

    def test_a_device_in_another_entry_is_not_this_one(self):
        """The whole reason the deprecated call was deprecated."""
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "dev-1"), "someone-elses-entry"): _device(
                "not-ours"
            )
        })
        assert device_by_identifier(
            registry, (DOMAIN, "dev-1"), HAIR_ENTRY
        ) is None

    def test_an_unknown_entry_falls_to_the_plural_call(self):
        """HAIR not set up yet, or a caller that cannot name an entry.

        Still never the deprecated door: the plural call has the same
        breadth and does not report usage.
        """
        wanted = _device("ha-2")
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "dev-2"), None): wanted
        })
        found = device_by_identifier(registry, (DOMAIN, "dev-2"), None)
        assert found is wanted
        assert registry.calls == [
            ("devices", {(DOMAIN, "dev-2")}, None, None)
        ]

    def test_nothing_found_is_none_not_an_empty_list(self):
        registry = _NewRegistry()
        assert device_by_identifier(registry, (DOMAIN, "gone"), None) is None

    def test_an_older_registry_uses_the_only_door_it_has(self):
        wanted = _device("ha-3")
        registry = _OldRegistry(wanted)
        found = device_by_identifier(
            registry, (DOMAIN, "dev-3"), HAIR_ENTRY
        )
        assert found is wanted
        assert registry.calls == [
            {"identifiers": {(DOMAIN, "dev-3")}, "connections": None}
        ]


class TestDeviceByConnection:
    def test_a_known_entry_uses_the_scoped_call(self):
        wanted = _device("blaster")
        connection = ("mac", "aa:bb:cc:dd:ee:ff")
        registry = _NewRegistry({
            ("connection", connection, BROADLINK_ENTRY): wanted
        })
        found = device_by_connection(registry, connection, BROADLINK_ENTRY)
        assert found is wanted
        assert registry.calls == [
            ("connection", connection, BROADLINK_ENTRY)
        ]

    def test_an_unknown_entry_falls_to_the_plural_call(self):
        wanted = _device("blaster")
        connection = ("mac", "aa:bb:cc:dd:ee:ff")
        registry = _NewRegistry({("connection", connection, None): wanted})
        assert device_by_connection(registry, connection, None) is wanted
        assert registry.calls == [("devices", None, {connection}, None)]

    def test_an_older_registry_uses_the_only_door_it_has(self):
        wanted = _device("blaster")
        registry = _OldRegistry(wanted)
        connection = ("mac", "aa:bb:cc:dd:ee:ff")
        assert device_by_connection(
            registry, connection, BROADLINK_ENTRY
        ) is wanted
        assert registry.calls == [
            {"identifiers": None, "connections": {connection}}
        ]


class TestTheCapabilityProbe:
    """Asked of the class, and why that matters here.

    A mock instance answers every attribute, so an instance-level probe
    would report the new API present on every double in this suite and
    hand callers a mock where a device belongs. The suite's existing
    registry doubles are exactly that shape, which is why they keep
    working unchanged: they read as pre-2026.8 registries.
    """

    def test_a_mock_registry_reads_as_the_older_generation(self):
        registry = MagicMock()
        registry.async_get_device.return_value = _device("ha-9")
        found = device_by_identifier(
            registry, (DOMAIN, "dev-9"), HAIR_ENTRY
        )
        assert found.id == "ha-9"
        registry.async_get_device.assert_called_once_with(
            identifiers={(DOMAIN, "dev-9")}
        )
        registry.async_get_device_by_identifier.assert_not_called()

    def test_the_version_that_added_the_methods_is_recorded(self):
        assert NEW_API_HA_VERSION == "2026.8.0"


class TestHairConfigEntryId:
    def test_it_reads_the_entry_off_hass_data(self):
        hass = SimpleNamespace(data={DOMAIN: {HAIR_ENTRY: {
            "device_manager": object(),
            "config_entry": SimpleNamespace(entry_id=HAIR_ENTRY),
        }}})
        assert hair_config_entry_id(hass) == HAIR_ENTRY

    def test_the_mapping_key_answers_when_no_entry_object_is_stored(self):
        """Hand-built test entry data often omits ``config_entry``."""
        hass = SimpleNamespace(data={DOMAIN: {
            "keyed-entry": {"device_manager": object()}
        }})
        assert hair_config_entry_id(hass) == "keyed-entry"

    @pytest.mark.parametrize("data", [
        {},
        {DOMAIN: {}},
        {DOMAIN: {"_panel_registered": True}},
        {DOMAIN: {"e": {"store": object()}}},
    ])
    def test_no_entry_is_none_rather_than_a_guess(self, data):
        assert hair_config_entry_id(SimpleNamespace(data=data)) is None

    def test_a_hass_without_data_is_none(self):
        assert hair_config_entry_id(SimpleNamespace()) is None


# ---------------------------------------------------------------------------
# The call sites, each on the new path
# ---------------------------------------------------------------------------


class TestDeviceManagerRemoveDevice:
    """``async_remove_device`` resolves the HA device it deletes."""

    def _manager(self, fake_hass):
        from custom_components.hair.device_manager import DeviceManager
        from custom_components.hair.models import IRDevice
        from custom_components.hair.storage import HAIRStore

        store = HAIRStore(fake_hass)
        store._loaded = True
        device = IRDevice(id="dev-1", name="TV")
        store.add_device(device)
        store.async_save = AsyncMock()
        factory = MagicMock()
        factory.async_remove_entities = AsyncMock()
        manager = DeviceManager(
            fake_hass, store, factory, config_entry_id=HAIR_ENTRY
        )
        return manager, store, device

    @pytest.mark.asyncio
    async def test_it_resolves_and_removes_through_the_scoped_call(
        self, fake_hass
    ):
        manager, _store, device = self._manager(fake_hass)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "dev-1"), HAIR_ENTRY): _device("ha-dev-1")
        })
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=registry,
        ):
            assert await manager.async_remove_device(device.id) is True
        assert registry.calls == [
            ("identifier", (DOMAIN, "dev-1"), HAIR_ENTRY)
        ]
        assert registry.removed == ["ha-dev-1"]

    @pytest.mark.asyncio
    async def test_it_asks_with_hairs_own_entry_id(self, fake_hass):
        """The scoping has to be HAIR's entry: the device is HAIR's."""
        manager, _store, device = self._manager(fake_hass)
        registry = _NewRegistry()
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=registry,
        ):
            await manager.async_remove_device(device.id)
        assert [call[2] for call in registry.calls] == [HAIR_ENTRY]
        assert registry.removed == []

    @pytest.mark.asyncio
    async def test_the_older_registry_still_removes_the_device(
        self, fake_hass
    ):
        manager, _store, device = self._manager(fake_hass)
        registry = _OldRegistry(_device("ha-dev-1"))
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=registry,
        ):
            await manager.async_remove_device(device.id)
        assert registry.calls == [
            {"identifiers": {(DOMAIN, "dev-1")}, "connections": None}
        ]
        assert registry.removed == ["ha-dev-1"]


class TestWebsocketLookupHelpers:
    """The three module-level resolvers, which take only ``hass``."""

    def _hass(self, fake_hass):
        fake_hass.data[DOMAIN] = {HAIR_ENTRY: {
            "device_manager": MagicMock(),
            "store": MagicMock(),
            "config_entry": SimpleNamespace(entry_id=HAIR_ENTRY),
        }}
        return fake_hass

    def test_a_devices_ha_id(self, fake_hass):
        from custom_components.hair import websocket_api
        from custom_components.hair.models import IRDevice

        hass = self._hass(fake_hass)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "dev-7"), HAIR_ENTRY): _device("ha-7")
        })
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ):
            found = websocket_api._ha_device_id(
                hass, IRDevice(id="dev-7", name="TV")
            )
        assert found == "ha-7"
        assert registry.calls == [
            ("identifier", (DOMAIN, "dev-7"), HAIR_ENTRY)
        ]

    def test_the_trigger_drawers_ha_id(self, fake_hass):
        from custom_components.hair import websocket_api
        from custom_components.hair.event import TRIGGER_DEVICE_ID

        hass = self._hass(fake_hass)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, TRIGGER_DEVICE_ID), HAIR_ENTRY): _device(
                "ha-drawer"
            )
        })
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ):
            found = websocket_api._trigger_drawer_ha_device_id(hass)
        assert found == "ha-drawer"

    def test_a_trigger_remotes_ha_id(self, fake_hass):
        from custom_components.hair import websocket_api

        hass = self._hass(fake_hass)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "rem-1"), HAIR_ENTRY): _device("ha-rem")
        })
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ):
            found = websocket_api._trigger_remote_ha_device_id(hass, "rem-1")
        assert found == "ha-rem"

    def test_an_unconfigured_hair_still_resolves_the_device(self, fake_hass):
        """No entry to scope by: the plural call, not the deprecated one."""
        from custom_components.hair import websocket_api
        from custom_components.hair.models import IRDevice

        fake_hass.data.pop(DOMAIN, None)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "dev-8"), None): _device("ha-8")
        })
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ):
            found = websocket_api._ha_device_id(
                fake_hass, IRDevice(id="dev-8", name="TV")
            )
        assert found == "ha-8"
        assert registry.calls == [
            ("devices", {(DOMAIN, "dev-8")}, None, None)
        ]


class TestWebsocketHandlers:
    """The four handlers that resolve a device inline."""

    def _wire(self, fake_hass, remote=None):
        store = MagicMock()
        store.async_save = AsyncMock()
        store.set_trigger_drawer_name = MagicMock()
        store.get_trigger_remote = MagicMock(return_value=remote)
        store.update_trigger_remote = MagicMock()
        store.remove_trigger_remote = MagicMock(return_value=[])
        store.get_triggers_for_remote = MagicMock(return_value=[])
        fake_hass.data[DOMAIN] = {HAIR_ENTRY: {
            "device_manager": MagicMock(),
            "store": store,
            "config_entry": SimpleNamespace(entry_id=HAIR_ENTRY),
        }}
        return store

    def _connection(self):
        return MagicMock(send_result=MagicMock(), send_error=MagicMock())

    @pytest.mark.asyncio
    async def test_renaming_the_drawer_updates_the_device_it_resolves(
        self, fake_hass
    ):
        from custom_components.hair import websocket_api
        from custom_components.hair.event import TRIGGER_DEVICE_ID

        self._wire(fake_hass)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, TRIGGER_DEVICE_ID), HAIR_ENTRY): _device(
                "ha-drawer"
            )
        })
        conn = self._connection()
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ), patch("custom_components.hair.event.resync_drawer_name"):
            await websocket_api.ws_rename_trigger_drawer(
                fake_hass, conn,
                {"id": 1, "type": "x", "name": "Den Remotes"},
            )
        assert registry.updated == [("ha-drawer", {"name": "Den Remotes"})]
        assert conn.send_result.call_args[0][1]["ha_device_id"] == "ha-drawer"

    @pytest.mark.asyncio
    async def test_renaming_a_remote_updates_the_device_it_resolves(
        self, fake_hass
    ):
        from custom_components.hair import websocket_api
        from custom_components.hair.models import TriggerRemote

        remote = TriggerRemote(id="rem-2", name="Old")
        self._wire(fake_hass, remote)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "rem-2"), HAIR_ENTRY): _device("ha-rem-2")
        })
        conn = self._connection()
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ), patch("custom_components.hair.event.resync_remote_name"):
            await websocket_api.ws_rename_trigger_remote(
                fake_hass, conn,
                {"id": 2, "type": "x", "remote_id": "rem-2", "name": "New"},
            )
        assert registry.updated == [("ha-rem-2", {"name": "New"})]
        assert conn.send_result.call_args[0][1]["ha_device_id"] == "ha-rem-2"

    @pytest.mark.asyncio
    async def test_setting_the_receiver_scope_reports_the_resolved_device(
        self, fake_hass
    ):
        from custom_components.hair import websocket_api
        from custom_components.hair.models import TriggerRemote

        remote = TriggerRemote(id="rem-3", name="TV")
        self._wire(fake_hass, remote)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "rem-3"), HAIR_ENTRY): _device("ha-rem-3")
        })
        conn = self._connection()
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ):
            await websocket_api.ws_set_trigger_remote_receiver_scope(
                fake_hass, conn,
                {
                    "id": 3, "type": "x", "remote_id": "rem-3",
                    "receiver_scope": [],
                },
            )
        assert conn.send_result.call_args[0][1]["ha_device_id"] == "ha-rem-3"

    @pytest.mark.asyncio
    async def test_deleting_a_remote_removes_the_device_it_resolves(
        self, fake_hass
    ):
        from custom_components.hair import websocket_api
        from custom_components.hair.models import TriggerRemote

        remote = TriggerRemote(id="rem-4", name="TV")
        self._wire(fake_hass, remote)
        registry = _NewRegistry({
            ("identifier", (DOMAIN, "rem-4"), HAIR_ENTRY): _device("ha-rem-4")
        })
        conn = self._connection()
        with patch.object(
            websocket_api.dr, "async_get", return_value=registry
        ), patch("custom_components.hair.matrix_store.delete_matrix"):
            await websocket_api.ws_delete_trigger_remote(
                fake_hass, conn,
                {"id": 4, "type": "x", "remote_id": "rem-4"},
            )
        assert registry.removed == ["ha-rem-4"]
        assert conn.send_result.call_args[0][1]["removed"] is True


class TestPluckStoreNames:
    """The one cross-integration lookup: a Broadlink blaster's name.

    The device belongs to Broadlink's config entry, so the scoped call
    takes Broadlink's entry id -- the entry the loop above it already
    matched by unique_id. That is the exact contract: a connection is
    unique within one entry.
    """

    MAC = "34:ea:34:11:22:33"
    STORE_ID = "34ea34112233"

    def _infos(self):
        from custom_components.hair.learned_code_stores import StoreInfo

        return [StoreInfo(
            integration="broadlink",
            store_id=self.STORE_ID,
            path="/config/.storage/broadlink_remote_34ea34112233_codes",
            codes=3,
            ir_codes=3,
        )]

    def _hass(self, fake_hass, with_entry=True):
        entries = []
        if with_entry:
            entries = [SimpleNamespace(
                entry_id=BROADLINK_ENTRY,
                unique_id=self.STORE_ID,
                title="Broadlink RM4",
            )]
        fake_hass.config_entries.async_entries = MagicMock(
            return_value=entries
        )
        return fake_hass

    def test_the_name_comes_from_the_scoped_lookup(self, fake_hass):
        from custom_components.hair import pluck

        hass = self._hass(fake_hass)
        infos = self._infos()
        registry = _NewRegistry({
            ("connection", ("mac", self.MAC), BROADLINK_ENTRY):
                SimpleNamespace(name="RM4 Pro", name_by_user="Living Room RM4")
        })
        with patch.object(pluck.dr, "async_get", return_value=registry):
            pluck.resolve_store_names(hass, infos)
        assert infos[0].friendly_name == "Living Room RM4"
        assert registry.calls == [
            ("connection", ("mac", self.MAC), BROADLINK_ENTRY)
        ]

    def test_no_matching_entry_searches_every_entry(self, fake_hass):
        """A store whose integration entry is gone still gets its name."""
        from custom_components.hair import pluck

        hass = self._hass(fake_hass, with_entry=False)
        infos = self._infos()
        registry = _NewRegistry({
            ("connection", ("mac", self.MAC), None):
                SimpleNamespace(name="RM4 Pro", name_by_user=None)
        })
        with patch.object(pluck.dr, "async_get", return_value=registry):
            pluck.resolve_store_names(hass, infos)
        assert infos[0].friendly_name == "RM4 Pro"
        assert registry.calls == [("devices", None, {("mac", self.MAC)}, None)]

    def test_an_older_registry_names_the_store_the_same(self, fake_hass):
        from custom_components.hair import pluck

        hass = self._hass(fake_hass)
        infos = self._infos()
        registry = _OldRegistry(
            SimpleNamespace(name="RM4 Pro", name_by_user="Living Room RM4")
        )
        with patch.object(pluck.dr, "async_get", return_value=registry):
            pluck.resolve_store_names(hass, infos)
        assert infos[0].friendly_name == "Living Room RM4"
        assert registry.calls == [
            {"identifiers": None, "connections": {("mac", self.MAC)}}
        ]


# ---------------------------------------------------------------------------
# The deprecated door, as a source rule
# ---------------------------------------------------------------------------


def test_only_the_compat_helper_names_the_deprecated_call():
    """Nine call sites became one, and it must stay one.

    The raising registry above proves the new path does not reach
    ``async_get_device``; this proves no future call site can, by
    walking the package. ``device_registry_compat.py`` is the one file
    allowed to name it, because the pre-2026.8 branch has nowhere else
    to go.
    """
    from pathlib import Path

    package = Path(__file__).resolve().parent.parent
    offenders = []
    for path in sorted(package.rglob("*.py")):
        if path.name == "device_registry_compat.py":
            continue
        if "tests" in path.relative_to(package).parts:
            continue
        if ".async_get_device(" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(package)))
    assert not offenders, (
        "these modules call the deprecated registry door; route them "
        f"through device_registry_compat instead: {offenders}"
    )
