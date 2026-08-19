"""Factory for creating HA entities from IR device profiles."""
from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice

_LOGGER = logging.getLogger(__name__)


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


SIGNAL_ADD_ENTITY = f"{DOMAIN}_add_entity"
SIGNAL_REMOVE_ENTITY = f"{DOMAIN}_remove_entity"
SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_update_entity"


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
        from homeassistant.helpers import entity_registry as er

        try:
            registry = er.async_get(self._hass)
            entity_id = registry.async_get_entity_id(
                platform, DOMAIN, platform_unique_id(device_id, platform)
            )
            if entity_id:
                registry.async_remove(entity_id)
        except Exception:
            _LOGGER.debug(
                "Could not remove the %s registry entry for device %s",
                platform, device_id, exc_info=True,
            )
