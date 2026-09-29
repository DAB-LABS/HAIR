"""Factory for creating HA entities from IR device profiles."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)

# The three shapes every HAIR per-owner unique id is built from. One
# copy, used to mint ids and to read them back.
_HAIR_PREFIX = "hair_"
_TRIGGER_PREFIX = "hair_trigger_"
_BUTTON_MARKER = "_btn_"


DEVICE_TYPE_TO_PLATFORM: dict[str, str] = {
    DeviceType.MEDIA_PLAYER: "media_player",
    DeviceType.AC: "climate",
    DeviceType.FAN: "fan",
    DeviceType.LIGHT: "light",
    DeviceType.SWITCH: "switch",
    DeviceType.SCREEN: "cover",
    DeviceType.OTHER: "remote",
}


def platform_unique_id(device_id: str, platform: str) -> str:
    """The unique id every per-device platform entity builds for itself.

    One device, one entity per platform, named the same way in
    media_player, climate, fan, light, switch, cover and remote. Written
    down here because a type change has to find the OLD platform's
    registry row after its entity object is already gone, and the row is
    only findable by unique id. ``test_entity_factory`` compares this
    against the real entities so the two cannot drift apart.
    """
    return f"hair_{device_id}_{platform}"


def button_unique_id(device_id: str, command_id: str) -> str:
    """The unique id one command's button entity builds for itself.

    Mirrors ``HAIRButtonEntity.__init__``, and written down here for the
    same reason ``platform_unique_id`` is: a DELETED command's row has
    to be found after its entity object is gone, and a registry row is
    only findable by unique id. ``test_orphan_entities`` compares this
    against the real entity so the two cannot drift apart.
    """
    return f"hair_{device_id}{_BUTTON_MARKER}{command_id}"


def trigger_unique_id(trigger_id: str) -> str:
    """The unique id one trigger's event entity builds for itself.

    Mirrors ``HAIRTriggerEventEntity.__init__``, same reasoning as
    ``button_unique_id``.
    """
    return f"{_TRIGGER_PREFIX}{trigger_id}"


#: Platforms whose per-device row is named by ``platform_unique_id``.
#: Derived from the type map rather than typed out again, so a new
#: device type cannot add a platform this sweep does not know about.
#: ``button`` is deliberately absent: its rows are per COMMAND and carry
#: the button unique id instead.
PLATFORM_ROW_PLATFORMS: tuple[str, ...] = tuple(
    sorted(set(DEVICE_TYPE_TO_PLATFORM.values()))
)


@dataclass(frozen=True)
class HairEntityRow:
    """What a HAIR-shaped unique id says about who owns the row."""

    family: str  # "button" | "trigger" | "platform"
    device_id: str | None = None
    command_id: str | None = None
    trigger_id: str | None = None
    platform: str | None = None


def classify_unique_id(unique_id: object) -> HairEntityRow | None:
    """Read a unique id as one of HAIR's three per-owner families.

    ``None`` means "not one of those", and that answer is the safety
    rail on the whole sweep below: anything this function does not
    recognise is never touched. That deliberately includes the Tweezer
    (``{entry_id}_hair_tweezer``, which does not start with ``hair_``),
    any row another integration owns, and any id a later HAIR invents
    without teaching this function about it.

    The three families cannot be confused with one another. Ids are
    uuid4, so no device, command or trigger id contains ``_``: the
    trigger prefix is checked first, then the button marker, and only
    then a trailing platform name.
    """
    if not isinstance(unique_id, str) or not unique_id.startswith(_HAIR_PREFIX):
        return None
    if unique_id.startswith(_TRIGGER_PREFIX):
        trigger_id = unique_id[len(_TRIGGER_PREFIX):]
        if not trigger_id:
            return None
        return HairEntityRow(family="trigger", trigger_id=trigger_id)
    rest = unique_id[len(_HAIR_PREFIX):]
    if _BUTTON_MARKER in rest:
        device_id, _, command_id = rest.partition(_BUTTON_MARKER)
        if not device_id or not command_id:
            return None
        return HairEntityRow(
            family="button", device_id=device_id, command_id=command_id
        )
    # Longest platform name first, so "media_player" is never read as
    # a device id ending in "_media" followed by "player".
    for platform in sorted(PLATFORM_ROW_PLATFORMS, key=len, reverse=True):
        suffix = f"_{platform}"
        if rest.endswith(suffix):
            device_id = rest[: -len(suffix)]
            if not device_id:
                return None
            return HairEntityRow(
                family="platform", device_id=device_id, platform=platform
            )
    return None


def forget_entity_row(
    hass: HomeAssistant, platform: str, unique_id: str
) -> bool:
    """Delete one HAIR entity's registry row. Best effort.

    ``Entity.async_remove`` takes an entity out of the state machine and
    LEAVES its registry row, which is what makes an entity survive a
    restart -- and what leaves a deleted command's button in the entity
    picker forever, attached to a device it no longer belongs to
    (GH #186). Every delete path that retires an entity for good calls
    this after scheduling the removal.

    Resolved by unique id rather than by entity id because the caller
    may hold an entity object that never reached the registry, or no
    object at all.
    """
    from homeassistant.helpers import entity_registry as er

    try:
        registry = er.async_get(hass)
        entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id:
            registry.async_remove(entity_id)
            return True
    except Exception:
        _LOGGER.debug(
            "Could not remove the %s registry row for %s",
            platform, unique_id, exc_info=True,
        )
    return False


SIGNAL_ADD_ENTITY = f"{DOMAIN}_add_entity"
SIGNAL_REMOVE_ENTITY = f"{DOMAIN}_remove_entity"
SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_update_entity"


@dataclass(frozen=True)
class ReconcileResult:
    """What one reconcile pass did, for the caller to log."""

    removed: int = 0
    skipped: str | None = None


def reconcile_orphan_entities(
    hass: HomeAssistant, entry_id: str, store: object
) -> ReconcileResult:
    """Remove HAIR registry rows whose owner is gone. Idempotent.

    Runs on every setup, BEFORE the platforms are forwarded: the store
    is loaded by then and no entity has registered yet, so a live entity
    cannot be mistaken for an orphan and every live row is re-registered
    a moment later.

    It removes exactly three kinds of row, each identified by unique id
    (see ``classify_unique_id``) and each only when its owner is not in
    the store: one command's button, one trigger's event entity, and one
    device's platform entity. A row it cannot classify is never touched,
    nor is a row belonging to another config entry -- the walk is scoped
    to this entry to begin with.

    THE GUARD, and why it matters more than the sweep. A store that
    failed to load, or that fell back to empty because its file was
    missing or unreadable, looks exactly like an install where the user
    deleted everything. Acting on that reading would delete the registry
    rows of every entity the user still has, taking their renames, areas
    and dashboard references with them. So the sweep declines to run
    when the store has not loaded, and declines again when the store is
    empty while the registry still holds rows of these families. The
    cost is that an install whose user really did delete everything
    keeps its orphan rows until it holds something again; that is the
    right side to err on, and it says so in the log.

    Reads nothing from disk: the store is already in memory and the
    entity registry is a loaded HA helper, so this needs no executor.
    """
    from homeassistant.helpers import entity_registry as er

    if not getattr(store, "loaded", False):
        return ReconcileResult(
            skipped="the device store has not loaded"
        )

    try:
        registry = er.async_get(hass)
        rows = list(er.async_entries_for_config_entry(registry, entry_id))
    except Exception:
        _LOGGER.debug(
            "Could not read the entity registry for %s", entry_id,
            exc_info=True,
        )
        return ReconcileResult(skipped="the entity registry could not be read")

    candidates: list[tuple[object, HairEntityRow]] = []
    for row in rows:
        owner = classify_unique_id(getattr(row, "unique_id", None))
        if owner is not None:
            candidates.append((row, owner))
    if not candidates:
        return ReconcileResult()

    devices = list(store.get_all_devices())  # type: ignore[attr-defined]
    triggers = list(store.get_all_triggers())  # type: ignore[attr-defined]
    if not devices and not triggers:
        return ReconcileResult(
            skipped=(
                "the store holds no devices or triggers while the registry "
                f"still holds {len(candidates)} HAIR row(s)"
            )
        )

    live_buttons = {
        button_unique_id(device.id, command.id)
        for device in devices
        for command in device.commands
    }
    live_triggers = {trigger_unique_id(t.id) for t in triggers}
    device_ids = {device.id for device in devices}

    removed = 0
    for row, owner in candidates:
        unique_id = row.unique_id  # type: ignore[attr-defined]
        if owner.family == "button":
            gone = unique_id not in live_buttons
        elif owner.family == "trigger":
            gone = unique_id not in live_triggers
        else:
            gone = owner.device_id not in device_ids
        if not gone:
            continue
        try:
            registry.async_remove(row.entity_id)  # type: ignore[attr-defined]
        except Exception:
            _LOGGER.debug(
                "Could not remove the orphaned registry row %s",
                getattr(row, "entity_id", unique_id), exc_info=True,
            )
            continue
        removed += 1
    return ReconcileResult(removed=removed)


class EntityFactory:
    """Create and manage HA entities for IR devices.

    Platforms register their ``async_add_entities`` callback at setup
    time. When a device is created/removed/updated, the factory dispatches
    to the matching platform.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._add_entity_callbacks: dict[str, AddEntitiesCallback] = {}
        self._entities: dict[str, str] = {}
        # Hooks platforms install so they can react to per-device add/remove/update.
        self._platform_hooks: dict[
            str, dict[str, Callable[[IRDevice], None]]
        ] = {}

    def register_platform(
        self,
        platform: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._add_entity_callbacks[platform] = async_add_entities

    def register_platform_hooks(
        self,
        platform: str,
        on_add: Callable[[IRDevice], None] | None = None,
        on_remove: Callable[[IRDevice], None] | None = None,
        on_update: Callable[[IRDevice], None] | None = None,
    ) -> None:
        hooks = self._platform_hooks.setdefault(platform, {})
        if on_add is not None:
            hooks["on_add"] = on_add
        if on_remove is not None:
            hooks["on_remove"] = on_remove
        if on_update is not None:
            hooks["on_update"] = on_update

    def get_platform_for_device(self, device: IRDevice) -> str:
        return DEVICE_TYPE_TO_PLATFORM.get(
            str(device.device_type), "remote"
        )

    # Platforms listed here receive callbacks for EVERY device,
    # regardless of device type.  Used by "remote" and "button".
    UNIVERSAL_PLATFORMS: tuple[str, ...] = ("remote", "button")

    async def async_create_entities(self, device: IRDevice) -> None:
        platform = self.get_platform_for_device(device)
        device.entity_config.platform = platform
        self._entities[device.id] = platform

        hooks = self._platform_hooks.get(platform, {})
        on_add = hooks.get("on_add")
        if on_add is not None:
            on_add(device)
        else:
            # Platform not yet set up — dispatch a signal and let the
            # platform's setup_entry handler pick it up on registration.
            async_dispatcher_send(self._hass, SIGNAL_ADD_ENTITY, device)

        # Also notify universal platforms (remote, button, etc.).
        for uni in self.UNIVERSAL_PLATFORMS:
            if uni == platform:
                continue  # already dispatched above
            uni_hooks = self._platform_hooks.get(uni, {})
            uni_add = uni_hooks.get("on_add")
            if uni_add is not None:
                uni_add(device)

    async def async_remove_entities(self, device_id: str) -> None:
        platform = self._entities.pop(device_id, None)
        if platform is None:
            return
        hooks = self._platform_hooks.get(platform, {})
        on_remove = hooks.get("on_remove")
        if on_remove is not None:
            on_remove(device_id)  # type: ignore[arg-type]

        # Also notify universal platforms.
        for uni in self.UNIVERSAL_PLATFORMS:
            if uni == platform:
                continue
            uni_hooks = self._platform_hooks.get(uni, {})
            uni_remove = uni_hooks.get("on_remove")
            if uni_remove is not None:
                uni_remove(device_id)  # type: ignore[arg-type]

    async def async_update_entities(self, device: IRDevice) -> None:
        """Apply a device save, INCLUDING a change of type (GH #106).

        The recorded platform used to win outright, so a device saved
        with a new type only ever reached the platform it was created
        on: an Other adopted from the Closet and later set to Fan or
        Climate saved fine and grew no entity until an HA restart
        rebuilt everything from the store. That is why it "worked after
        a restart".

        A type change is a retire and an add, not an update. The old
        platform's entity goes (registry row and all, see
        ``_forget_registry_entry``), the new platform gets ``on_add``,
        and only then does the ordinary universal-platform pass run.
        The HA device is keyed on the HAIR device id and is not touched,
        so the new entity lands on the same device page.
        """
        recorded = self._entities.get(device.id)
        platform = self.get_platform_for_device(device)
        added = False

        if recorded is not None and recorded != platform:
            # A universal platform is not retired: its entity exists for
            # EVERY device whatever the type, so removing it here would
            # take the remote entity off a device that still has one.
            if recorded not in self.UNIVERSAL_PLATFORMS:
                self._retire_platform(device.id, recorded)
            self._entities[device.id] = platform
            device.entity_config.platform = platform
            _LOGGER.debug(
                "Device %s changed platform %s to %s", device.id,
                recorded, platform,
            )
            if platform not in self.UNIVERSAL_PLATFORMS:
                hooks = self._platform_hooks.get(platform, {})
                on_add = hooks.get("on_add")
                if on_add is not None:
                    on_add(device)
                else:
                    # Same fallback async_create_entities uses: the
                    # platform has not registered its hook yet, so let
                    # its setup handler pick the device up.
                    async_dispatcher_send(
                        self._hass, SIGNAL_ADD_ENTITY, device
                    )
                added = True
            # A change INTO a universal platform (an AC set back to
            # Other) adds nothing: that entity is already there and
            # simply takes the ordinary update below.

        if not added:
            hooks = self._platform_hooks.get(platform, {})
            on_update = hooks.get("on_update")
            if on_update is not None:
                on_update(device)

        # Also notify universal platforms.
        for uni in self.UNIVERSAL_PLATFORMS:
            if uni == platform:
                continue
            uni_hooks = self._platform_hooks.get(uni, {})
            uni_update = uni_hooks.get("on_update")
            if uni_update is not None:
                uni_update(device)

    def _retire_platform(self, device_id: str, platform: str) -> None:
        """Take one platform's entity off a device that changed type."""
        hooks = self._platform_hooks.get(platform, {})
        on_remove = hooks.get("on_remove")
        if on_remove is not None:
            on_remove(device_id)  # type: ignore[arg-type]
        self._forget_registry_entry(device_id, platform)

    def _forget_registry_entry(self, device_id: str, platform: str) -> None:
        """Delete the retired entity's registry row, not just its state.

        ``Entity.async_remove`` leaves a REGISTERED entity behind as
        unavailable rather than deleting it, which is exactly what makes
        an entity survive a restart -- and exactly what would leave a
        dead ``fan.*`` row under Settings > Entities forever after a
        change to Climate. A device DELETE needs none of this: removing
        the HA device takes its entity rows with it.

        Best effort. A registry that refuses must not undo a type change
        the store has already accepted.
        """
        forget_entity_row(
            self._hass, platform, platform_unique_id(device_id, platform)
        )
