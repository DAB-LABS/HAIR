"""Entity registry rows that outlive what they belonged to (GH #186).

kilrah plucked one code library into three HAIR devices, deleted the
codes that did not belong to each, and found HA still offering "Trisa
Fan Power" as a button of his Ayce AC. HAIR's own card was right; the
entity registry was not.

The cause is that ``Entity.async_remove`` takes an entity out of the
state machine and LEAVES its registry row. That is exactly what makes an
entity survive a restart, and exactly wrong for an entity that is never
coming back. ``entity_factory._forget_registry_entry`` already knew this
for a device TYPE change; the command and trigger delete paths did not.

Three things are pinned here: the delete paths remove the row, a
setup-time sweep clears what earlier versions left behind, and -- the
part that matters most -- the sweep REFUSES to run when the store's
answer cannot be trusted. A store that failed to load, or fell back to
empty, looks exactly like "the user deleted everything", and acting on
that reading would delete the rows of every entity they still have.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.const import DOMAIN, DeviceType
from custom_components.hair.entity_factory import (
    PLATFORM_ROW_PLATFORMS,
    button_unique_id,
    classify_unique_id,
    forget_entity_row,
    platform_unique_id,
    reconcile_orphan_entities,
    trigger_unique_id,
)
from custom_components.hair.models import IRCommand, IRDevice, IRTrigger

ENTRY_ID = "entry-1"


class FakeRegistry:
    """An entity registry with just the calls this code makes.

    Rows are ``(entity_id, unique_id)``. The entity DOMAIN comes off the
    entity id and the PLATFORM is always HAIR, which is the shape the
    registry really holds and the order ``async_get_entity_id`` really
    takes: domain first, then the integration that owns the row.
    """

    def __init__(self, rows: list[tuple[str, str]] | None = None):
        self.rows: dict[str, SimpleNamespace] = {}
        for entity_id, unique_id in rows or []:
            self.rows[entity_id] = SimpleNamespace(
                entity_id=entity_id,
                domain=entity_id.split(".")[0],
                platform=DOMAIN,
                unique_id=unique_id,
                config_entry_id=ENTRY_ID,
            )
        self.removed: list[str] = []

    def async_get_entity_id(self, domain, platform, unique_id):
        for row in self.rows.values():
            if (row.domain, row.platform, row.unique_id) == (
                domain, platform, unique_id
            ):
                return row.entity_id
        return None

    def async_remove(self, entity_id):
        self.rows.pop(entity_id, None)
        self.removed.append(entity_id)

    def entries_for_entry(self, entry_id):
        return [r for r in self.rows.values() if r.config_entry_id == entry_id]


@contextmanager
def _registry_patch(registry: FakeRegistry):
    """Point the entity_registry helper at this fake for one block.

    Patched on the helper module itself rather than in ``sys.modules``:
    the code under test does ``from homeassistant.helpers import
    entity_registry as er``, which resolves the attribute on the parent
    package, so a sys.modules swap would not be seen.
    """
    from homeassistant.helpers import entity_registry as er

    with patch.object(er, "async_get", return_value=registry), patch.object(
        er,
        "async_entries_for_config_entry",
        side_effect=lambda _reg, entry_id: registry.entries_for_entry(
            entry_id
        ),
    ):
        yield


class FakeStore:
    """The two reads the sweep makes, plus the flag its guard reads."""

    def __init__(self, devices=None, triggers=None, loaded=True):
        self._devices = list(devices or [])
        self._triggers = list(triggers or [])
        self.loaded = loaded

    def get_all_devices(self):
        return list(self._devices)

    def get_all_triggers(self):
        return list(self._triggers)


def _device(name="Ayce AC", commands=()):
    device = IRDevice(name=name, device_type=DeviceType.AC)
    for command_name in commands:
        device.commands.append(IRCommand(name=command_name))
    return device


def _button_row(device, command, entity_id=None):
    return (
        entity_id or f"button.{command.name.lower().replace(' ', '_')}",
        button_unique_id(device.id, command.id),
    )


# ---------------------------------------------------------------------------
# The unique ids, and that they match the entities that mint them
# ---------------------------------------------------------------------------


class TestTheUniqueIdsMatchTheRealEntities:
    """The sweep finds rows by unique id, so a drift here is silent."""

    def test_the_button_id_is_the_one_the_button_builds(self):
        from custom_components.hair.button import HAIRButtonEntity

        device = _device(commands=["Power"])
        command = device.commands[0]
        entity = HAIRButtonEntity(device, command.id, command.name, MagicMock())
        # ``_attr_unique_id`` rather than the property: the suite's HA
        # stub carries no Entity base to resolve the property through.
        assert entity._attr_unique_id == button_unique_id(
            device.id, command.id
        )

    def test_the_event_id_is_the_one_the_event_entity_builds(self):
        from custom_components.hair.event import HAIRTriggerEventEntity

        trigger = IRTrigger(name="Doorbell", code="0000 006D")
        entity = HAIRTriggerEventEntity(trigger, None, None)
        assert entity._attr_unique_id == trigger_unique_id(trigger.id)

    def test_the_platform_row_list_is_derived_from_the_type_map(self):
        from custom_components.hair.entity_factory import (
            DEVICE_TYPE_TO_PLATFORM,
        )

        assert set(PLATFORM_ROW_PLATFORMS) == set(
            DEVICE_TYPE_TO_PLATFORM.values()
        )
        # Buttons are per COMMAND, so they are never a platform row.
        assert "button" not in PLATFORM_ROW_PLATFORMS


class TestTheClassifier:
    """What the sweep is allowed to consider, and nothing else."""

    def test_a_button_id_reads_as_its_device_and_command(self):
        row = classify_unique_id(button_unique_id("dev-1", "cmd-9"))
        assert (row.family, row.device_id, row.command_id) == (
            "button", "dev-1", "cmd-9",
        )

    def test_a_trigger_id_reads_as_its_trigger(self):
        row = classify_unique_id(trigger_unique_id("trig-7"))
        assert (row.family, row.trigger_id) == ("trigger", "trig-7")

    @pytest.mark.parametrize("platform", PLATFORM_ROW_PLATFORMS)
    def test_every_platform_row_reads_as_its_device(self, platform):
        row = classify_unique_id(platform_unique_id("dev-2", platform))
        assert (row.family, row.device_id, row.platform) == (
            "platform", "dev-2", platform,
        )

    def test_a_two_word_platform_is_not_read_as_a_device_id(self):
        """``media_player`` is why the suffix match takes the longest."""
        row = classify_unique_id("hair_dev-3_media_player")
        assert (row.device_id, row.platform) == ("dev-3", "media_player")

    @pytest.mark.parametrize("unique_id", [
        "entry-1_hair_tweezer",        # the Tweezer, never ours to remove
        "hair_tweezer",                # and not by a near miss either
        "sensor.something_else",       # another integration entirely
        "hair_",                       # nothing after the prefix
        "hair_trigger_",               # a trigger id that is not there
        "hair_dev-1_btn_",             # a command id that is not there
        "hair__btn_cmd-1",             # a device id that is not there
        "hair_dev-1_somethingnew",     # a family this version cannot read
        None,                          # not a string at all
        42,
    ])
    def test_anything_else_is_not_ours(self, unique_id):
        assert classify_unique_id(unique_id) is None


# ---------------------------------------------------------------------------
# The delete paths
# ---------------------------------------------------------------------------


class TestDeletingACommand:
    def test_the_button_row_goes_with_the_entity(self, fake_hass):
        from custom_components.hair import button as button_module

        device = _device(commands=["Power", "Volume Up"])
        power, volume = device.commands
        registry = FakeRegistry([
            _button_row(device, power, "button.ayce_ac_power"),
            _button_row(device, volume, "button.ayce_ac_volume_up"),
        ])

        with _registry_patch(registry):
            # Drive the same helper the platform's _sync_buttons uses.
            forget_entity_row(
                fake_hass, "button", button_unique_id(device.id, power.id)
            )
        assert registry.removed == ["button.ayce_ac_power"]
        assert "button.ayce_ac_volume_up" in registry.rows
        assert button_module is not None

    def test_the_platform_calls_it_for_every_deleted_command(self):
        """The wiring, read off the source: a run needs a live HA."""
        import inspect

        from custom_components.hair import button as button_module

        source = inspect.getsource(button_module)
        assert "forget_entity_row(" in source
        assert "button_unique_id(device.id, cmd_id)" in source

    def test_a_missing_row_is_not_an_error(self, fake_hass):
        registry = FakeRegistry()
        with _registry_patch(registry):
            assert forget_entity_row(fake_hass, "button", "hair_x_btn_y") is (
                False
            )
        assert registry.removed == []

    def test_a_registry_that_refuses_does_not_raise(self, fake_hass):
        registry = FakeRegistry([("button.a", "hair_d_btn_c")])
        registry.async_remove = MagicMock(side_effect=RuntimeError("no"))
        with _registry_patch(registry):
            assert forget_entity_row(fake_hass, "button", "hair_d_btn_c") is (
                False
            )


class TestDeletingATrigger:
    def test_the_event_row_goes(self, fake_hass):
        trigger = IRTrigger(name="Doorbell", code="0000 006D")
        registry = FakeRegistry([
            ("event.doorbell", trigger_unique_id(trigger.id)),
            ("event.other", trigger_unique_id("other")),
        ])
        from custom_components.hair.event import sync_trigger_entities

        fake_hass.data[DOMAIN] = {ENTRY_ID: {
            "store": MagicMock(),
            "_trigger_entities": {},
        }}
        with _registry_patch(registry):
            sync_trigger_entities(fake_hass, ENTRY_ID, removed_id=trigger.id)
        assert registry.removed == ["event.doorbell"]
        assert "event.other" in registry.rows

    def test_it_works_when_this_run_never_held_the_entity(self, fake_hass):
        """After a restart the entity dict is empty and the row is not."""
        trigger = IRTrigger(name="Doorbell", code="0000 006D")
        registry = FakeRegistry([
            ("event.doorbell", trigger_unique_id(trigger.id)),
        ])
        from custom_components.hair.event import sync_trigger_entities

        fake_hass.data[DOMAIN] = {ENTRY_ID: {
            "store": MagicMock(),
            "_trigger_entities": {},
        }}
        with _registry_patch(registry):
            sync_trigger_entities(fake_hass, ENTRY_ID, removed_id=trigger.id)
        assert registry.removed == ["event.doorbell"]


# ---------------------------------------------------------------------------
# The setup-time sweep
# ---------------------------------------------------------------------------


class TestTheSweep:
    def _install(self):
        """One live device with one command, one live trigger, and one
        orphan of each of the three families."""
        device = _device(commands=["Power"])
        power = device.commands[0]
        gone_device_id = "dev-deleted"
        trigger = IRTrigger(name="Doorbell", code="0000 006D")
        rows = [
            # Live.
            _button_row(device, power, "button.ayce_ac_power"),
            ("climate.ayce_ac",
             platform_unique_id(device.id, "climate")),
            ("event.doorbell", trigger_unique_id(trigger.id)),
            # Orphans: command gone, device gone, trigger gone, platform
            # row of a device that is gone.
            ("button.ayce_ac_trisa_fan_power",
             button_unique_id(device.id, "cmd-deleted")),
            ("button.old_device_power",
             button_unique_id(gone_device_id, "cmd-1")),
            ("event.old_trigger",
             trigger_unique_id("trig-deleted")),
            ("remote.old_device_remote",
             platform_unique_id(gone_device_id, "remote")),
            # Never ours.
            ("infrared.hair_tweezer",
             f"{ENTRY_ID}_hair_tweezer"),
        ]
        return FakeStore([device], [trigger]), FakeRegistry(rows)

    def test_it_removes_every_orphan_and_keeps_every_live_row(self, fake_hass):
        store, registry = self._install()
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert result.skipped is None
        assert result.removed == 4
        assert sorted(registry.removed) == [
            "button.ayce_ac_trisa_fan_power",
            "button.old_device_power",
            "event.old_trigger",
            "remote.old_device_remote",
        ]
        assert sorted(registry.rows) == [
            "button.ayce_ac_power",
            "climate.ayce_ac",
            "event.doorbell",
            "infrared.hair_tweezer",
        ]

    def test_a_second_pass_removes_nothing(self, fake_hass):
        """Idempotent: it runs on every setup, not once."""
        store, registry = self._install()
        with _registry_patch(registry):
            reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
            registry.removed.clear()
            again = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert (again.removed, again.skipped) == (0, None)
        assert registry.removed == []

    def test_a_customized_live_row_survives_untouched(self, fake_hass):
        """A renamed, disabled, re-areaed row of a command that still
        exists is not the sweep's business."""
        device = _device(commands=["Power"])
        power = device.commands[0]
        registry = FakeRegistry([
            ("button.my_own_name",
             button_unique_id(device.id, power.id)),
        ])
        row = registry.rows["button.my_own_name"]
        row.disabled_by = "user"
        row.area_id = "living_room"
        store = FakeStore([device], [])
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert (result.removed, result.skipped) == (0, None)
        assert registry.rows["button.my_own_name"].disabled_by == "user"
        assert registry.rows["button.my_own_name"].area_id == "living_room"

    def test_another_config_entry_is_never_touched(self, fake_hass):
        device = _device(commands=["Power"])
        registry = FakeRegistry([
            ("button.someone_elses",
             button_unique_id("dev-elsewhere", "cmd-elsewhere")),
        ])
        registry.rows["button.someone_elses"].config_entry_id = "entry-2"
        store = FakeStore([device], [])
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert (result.removed, result.skipped) == (0, None)
        assert "button.someone_elses" in registry.rows

    def test_an_unreadable_unique_id_is_never_removed(self, fake_hass):
        device = _device(commands=["Power"])
        registry = FakeRegistry([
            ("sensor.mystery", "hair_dev-1_somethingnew"),
            ("infrared.hair_tweezer",
             f"{ENTRY_ID}_hair_tweezer"),
        ])
        store = FakeStore([device], [])
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert (result.removed, result.skipped) == (0, None)
        assert len(registry.rows) == 2

    def test_a_clean_install_does_nothing_quietly(self, fake_hass):
        store = FakeStore([], [])
        registry = FakeRegistry()
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert (result.removed, result.skipped) == (0, None)


class TestTheGuard:
    """The part that protects an install from a bad read.

    A store that did not load, or that fell back to empty because its
    file was missing or unreadable, is indistinguishable from an install
    whose user deleted everything. The sweep must decline both times: a
    wrong call here deletes the registry rows of entities the user still
    has, and takes their renames, areas and dashboard references with
    them. Declining costs an install that really is empty nothing but a
    delay until it holds something again.
    """

    def test_a_store_that_did_not_load_stops_the_sweep(self, fake_hass):
        device = _device(commands=["Power"])
        registry = FakeRegistry([
            ("button.orphan",
             button_unique_id("dev-gone", "cmd-gone")),
        ])
        store = FakeStore([device], [], loaded=False)
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert result.removed == 0
        assert "has not loaded" in (result.skipped or "")
        assert registry.removed == []

    def test_an_empty_store_with_hair_rows_stops_the_sweep(self, fake_hass):
        """The fallback-to-empty case, which is the dangerous one."""
        registry = FakeRegistry([
            ("button.still_here",
             button_unique_id("dev-1", "cmd-1")),
            ("climate.still_here",
             platform_unique_id("dev-1", "climate")),
            ("event.still_here", trigger_unique_id("trig-1")),
        ])
        store = FakeStore([], [], loaded=True)
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert result.removed == 0
        assert "no devices or triggers" in (result.skipped or "")
        assert len(registry.rows) == 3

    def test_triggers_alone_are_enough_to_proceed(self, fake_hass):
        """An install with no devices but live triggers is a real
        install, not a failed load."""
        trigger = IRTrigger(name="Doorbell", code="0000 006D")
        registry = FakeRegistry([
            ("event.doorbell", trigger_unique_id(trigger.id)),
            ("event.old", trigger_unique_id("trig-gone")),
        ])
        store = FakeStore([], [trigger])
        with _registry_patch(registry):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert (result.removed, result.skipped) == (1, None)
        assert registry.removed == ["event.old"]

    def test_a_registry_that_cannot_be_read_stops_the_sweep(self, fake_hass):
        store = FakeStore([_device(commands=["Power"])], [])
        module = MagicMock()
        module.async_get = MagicMock(side_effect=RuntimeError("no registry"))
        with patch.dict(
            "sys.modules",
            {"homeassistant.helpers.entity_registry": module},
        ):
            result = reconcile_orphan_entities(fake_hass, ENTRY_ID, store)
        assert result.removed == 0
        assert "could not be read" in (result.skipped or "")

    def test_setup_logs_the_reason_rather_than_swallowing_it(self):
        """Wiring: the caller reports a skip, and reports a count."""
        import inspect

        from custom_components import hair as hair_module

        source = inspect.getsource(hair_module.async_setup_entry)
        assert "reconcile_orphan_entities(hass, entry.entry_id, store)" in (
            source
        )
        assert "Skipped the entity cleanup" in source
        # Before the platforms come up, so nothing live can look
        # orphaned. Read inside async_setup_entry, where the order is.
        assert source.index("reconcile_orphan_entities(hass") < source.index(
            "async_forward_entry_setups"
        )
