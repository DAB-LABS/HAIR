"""A typed Remote's own state entity (heard state, round 2a).

THE MODEL (owner, 2026-10-21): two devices, each with its own state,
neither synced to the other. A Device's entity follows what HAIR sends
to it (round 1). A Remote given a type (media player, fan, light,
switch or screen) gets an entity of that type that follows its OWN
handset presses, and whose controls change its own state only and never
send IR, so a user can correct it by hand when it drifts. Users
automate against, and expose to voice assistants, whichever they choose.

REUSE, NOT A COPY. Each Remote entity class subclasses the Device
entity class of its platform, with ``RemoteStateMixin`` in front. The
Device class carries every state rule (``send_follow`` plus its own
``_apply_keys``), the setters, the features drawn from a mapping and
the restore; the mixin swaps in three things only:

- ``_entity_config``: the Remote's own type and mapping, filtered to
  the keys a Remote can track (no dead controls);
- ``_send``: sends nothing. The no-IR rule, in one place;
- what it listens to: ``SIGNAL_REMOTE_PRESSED``, sent by the trigger
  manager on every confirmed fire of one of the Remote's buttons
  (after min_hits and the receiver dedup, never for an echo, which the
  signal monitor claims first), instead of the power verdict and the
  Device's sends.

A leaf apart from the model and helper imports: the platforms import
this module, never the other way round. Entities are made through the
factories the platforms register here.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .command_templates import get_action_options
from .const import DOMAIN, DeviceType
from .entity_factory import (
    DEVICE_TYPE_TO_PLATFORM,
    forget_entity_row,
    remote_state_unique_id,
)
from .models import EntityConfig, TriggerRemote
from .send_follow import keys_for_trigger

_LOGGER = logging.getLogger(__name__)

#: Sent with a ``RemotePressed`` on every confirmed fire of a trigger
#: that belongs to a named Remote.
SIGNAL_REMOTE_PRESSED = "hair_remote_pressed"


@dataclass(frozen=True)
class RemotePressed:
    """One confirmed press of one of a Remote's buttons."""

    remote_id: str
    trigger_id: str


#: The Device types a Remote can take: the ones with a state entity.
#: AC is not here (an AC Remote's STATE MATRIX is its state), nor is
#: OTHER (no state entity at all).
REMOTE_TYPES: tuple[str, ...] = (
    DeviceType.MEDIA_PLAYER,
    DeviceType.FAN,
    DeviceType.LIGHT,
    DeviceType.SWITCH,
    DeviceType.SCREEN,
)

_POWER = frozenset({"turn_on", "turn_off", "power_toggle"})

#: The action keys a Remote's entity of each type can TRACK from presses
#: alone. A key outside this set would map a button to nothing the
#: entity can show, which is a dead control (owner ruling 2026-10-22),
#: so it is neither offered nor read. Source pickers, brightness and
#: colour steps, channels and navigation are out until the entity can
#: track them. ``speed_cycle`` is listed ahead of the fan speed cycle
#: round: it is offered only once that round adds it to the fan's
#: action list, and it is tracked by the same fan code a Device uses.
REMOTE_TRACKED_KEYS: dict[str, frozenset[str]] = {
    DeviceType.MEDIA_PLAYER: _POWER
    | {"volume_up", "volume_down", "mute", "play", "pause", "stop"},
    DeviceType.FAN: _POWER
    | {"speed_up", "speed_down", "oscillate", "speed_cycle"}
    | {f"speed_{i}" for i in range(1, 11)},
    DeviceType.LIGHT: frozenset({"turn_on", "turn_off"}),
    DeviceType.SWITCH: frozenset({"turn_on", "turn_off"}),
    DeviceType.SCREEN: frozenset({"open_cover", "close_cover", "stop_cover"}),
}

#: Every platform a Remote's state entity can live on.
REMOTE_PLATFORMS: tuple[str, ...] = tuple(
    sorted({DEVICE_TYPE_TO_PLATFORM[t] for t in REMOTE_TYPES})
)


def remote_platform(remote: TriggerRemote) -> str | None:
    """The platform of a Remote's state entity, or None for none.

    None for an untyped Remote, an AC (matrix) Remote whatever its
    stored type says, and a type this build does not offer.
    """
    if remote.climate_matrix or remote.device_type not in REMOTE_TYPES:
        return None
    return DEVICE_TYPE_TO_PLATFORM[remote.device_type]


def tracked_mapping(
    device_type: str | None, mapping: dict[str, str]
) -> dict[str, str]:
    """``mapping`` without the keys a Remote of this type cannot track."""
    allowed = REMOTE_TRACKED_KEYS.get(device_type or "", frozenset())
    return {key: value for key, value in mapping.items() if key in allowed}


def remote_action_options(device_type: str | None) -> list[dict[str, str]]:
    """The Device's action list for this type, trackable keys only.

    Same order and labels as a Device's, so the popover reads the same.
    """
    if device_type not in REMOTE_TYPES:
        return []
    allowed = REMOTE_TRACKED_KEYS[device_type]
    return [
        option
        for option in get_action_options(device_type)
        if option["key"] in allowed
    ]


def remote_entity_config(remote: TriggerRemote) -> EntityConfig:
    """The config a Remote's entity reads: its own, trackable keys only.

    A copy, so nothing the entity does can write back into the store.
    """
    config = EntityConfig.from_dict(remote.entity_config.to_dict())
    config.command_mapping = tracked_mapping(
        remote.device_type, config.command_mapping
    )
    platform = remote_platform(remote)
    if platform is not None:
        config.platform = platform
    return config


def _mapping_through(device: Any, button_for_command: dict[str, str]) -> dict[str, str]:
    """A Device's mapping, walked to a Remote's buttons.

    Key, then command name, then command id, then the button that
    command leads to. ``button_for_command`` is ``{command_id:
    trigger_id}``; a key whose command leads to no button is dropped.
    Shared by Make a Remote (``source_command_id``) and the fill from a
    pin (``bindings``), so both walk the same way.
    """
    mapping: dict[str, str] = {}
    for key, name in device.entity_config.command_mapping.items():
        command = device.get_command_by_name(name) if name else None
        if command is not None and command.id in button_for_command:
            mapping[key] = button_for_command[command.id]
    return mapping


def _first_button_per_command(
    pairs: list[tuple[str, str]],
) -> dict[str, str]:
    """``{command_id: trigger_id}`` from ``(trigger_id, command_id)``
    pairs in the Remote's button order, the FIRST button winning when
    several lead to one command."""
    out: dict[str, str] = {}
    for trigger_id, command_id in pairs:
        if command_id:
            out.setdefault(command_id, trigger_id)
    return out


def seed_from_device(
    remote: TriggerRemote, device: Any, triggers: list[Any]
) -> None:
    """Make a Remote: take the Device's type, mapping and settings.

    ``triggers`` are the new Remote's buttons, each minted from one of
    the Device's commands (``source_command_id``), which is the exact
    link a mapped key follows. A key with no button, or one a Remote
    cannot track, is dropped. A Device whose type a Remote cannot take
    (AC, other), or a Remote that carries a lattice, leaves the Remote
    untyped.
    """
    if remote.climate_matrix or device.device_type not in REMOTE_TYPES:
        return
    by_command = _first_button_per_command(
        [(t.id, t.source_command_id) for t in triggers]
    )
    remote.device_type = str(device.device_type)
    _take_device_config(remote, device, _mapping_through(device, by_command))


def _take_device_config(
    remote: TriggerRemote, device: Any, mapping: dict[str, str]
) -> None:
    """The Device's settings (a fan's speed cycle count, for one), with
    ``mapping`` as the Remote's, trackable keys only."""
    remote.entity_config = EntityConfig.from_dict(device.entity_config.to_dict())
    remote.entity_config.command_mapping = tracked_mapping(
        remote.device_type, mapping
    )


# ---------------------------------------------------------------------------
# Filling the buttons when a type is picked (owner bench, 2026-10-22)
# ---------------------------------------------------------------------------

FILL_KEPT = "kept"
FILL_PIN = "pin"
FILL_NAMES = "names"
FILL_NONE = "none"


@dataclass(frozen=True)
class FillPlan:
    """What picking a type does to a Remote's buttons.

    ``source`` is ``kept`` (the Remote already maps buttons this type
    can track; nothing is touched), ``pin`` (from the one pinned Device
    of this type), ``names`` (by button names, the auto-map rules) or
    ``none`` (nothing could be mapped). ``mapping`` is the trackable
    mapping the Remote ends with; ``device`` is the pinned Device a pin
    fill came from.
    """

    source: str
    mapping: dict[str, str]
    device: Any = None

    @property
    def count(self) -> int:
        return len(self.mapping)

    @property
    def device_name(self) -> str | None:
        return getattr(self.device, "name", None)


def plan_fill(store: Any, remote: TriggerRemote, device_type: str) -> FillPlan:
    """What a type pick would map, changing nothing (``dry_run`` reads it).

    1. A Remote that already maps buttons this type can track keeps
       them, a mapping kept across a clear included.
    2. Exactly one pinned Device of this type: its mapping, walked
       through the pin's ``bindings`` to the buttons bound to each
       command (the first in button order when several are).
    3. Otherwise, each button by its name with the rules a Device's
       commands use, the first button winning a key.
    """
    kept = tracked_mapping(device_type, remote.entity_config.command_mapping)
    if kept:
        return FillPlan(FILL_KEPT, kept)
    triggers = store.get_triggers_for_remote(remote.id)
    pinned = [
        device
        for device_id in remote.pinned_device_ids
        if (device := store.get_device(device_id)) is not None
        and str(device.device_type) == device_type
    ]
    if len(pinned) == 1:
        device = pinned[0]
        bound = remote.bindings.get(device.id) or {}
        by_command = _first_button_per_command(
            [(t.id, bound.get(t.id)) for t in triggers]
        )
        mapping = tracked_mapping(device_type, _mapping_through(device, by_command))
        if mapping:
            return FillPlan(FILL_PIN, mapping, device)
    from .device_manager import auto_map_feature

    allowed = REMOTE_TRACKED_KEYS.get(device_type, frozenset())
    mapping = {}
    for trigger in triggers:
        key = auto_map_feature(trigger.name or "", device_type)
        if key in allowed and key not in mapping:
            mapping[key] = trigger.id
    if mapping:
        return FillPlan(FILL_NAMES, mapping)
    return FillPlan(FILL_NONE, {})


def fill_on_pin(store: Any, remote: TriggerRemote, device_id: str) -> FillPlan | None:
    """Pinning a typed Remote that maps nothing fills it from that Device.

    Owner bench, 2026-10-27: a Remote typed before the fill existed, or
    typed first and pinned later, kept a type with nothing mapped, and
    pinning it filled nothing, because the fill ran only on a type pick.
    Called by ``trigger-remote/pin`` once the pin's bindings are derived.

    Applies only when all hold, and only a fill FROM THE PIN (a by-name
    fill belongs to the type pick):

    - the Remote has a type a Remote can take (not a lattice Remote);
    - it maps nothing that type can track (``plan_fill``'s kept rule);
    - the Device just pinned is of that type and is the only pinned
      Device of it.

    Returns the plan it applied, or None when it applied nothing.
    """
    if remote_platform(remote) is None:
        return None
    plan = plan_fill(store, remote, remote.device_type)
    # A fill from the pin names its one candidate; it has to be the
    # Device just pinned, which also rules out a Device of another type.
    if plan.source != FILL_PIN or plan.device is None or plan.device.id != device_id:
        return None
    apply_fill(remote, plan)
    return plan


def apply_fill(remote: TriggerRemote, plan: FillPlan) -> None:
    """Write a fill into the Remote. ``kept`` and ``none`` write nothing.

    A pin fill takes the Device's settings too, as Make a Remote does,
    so a Remote filled from a speed-cycle fan gets its speed count. Keys
    of other types the Remote still stores stay, except where a filled
    key now holds the same button (one key per button) or the same key.
    """
    if plan.source not in (FILL_PIN, FILL_NAMES):
        return
    old = dict(remote.entity_config.command_mapping)
    if plan.source == FILL_PIN:
        _take_device_config(remote, plan.device, plan.mapping)
    buttons = set(plan.mapping.values())
    merged = {
        key: trigger_id
        for key, trigger_id in old.items()
        if key not in plan.mapping and trigger_id not in buttons
    }
    merged.update(plan.mapping)
    remote.entity_config.command_mapping = merged


#: The per-type settings Make a Device copies from a typed Remote along
#: with its mapping: the fan speed cycle's, today.
REMOTE_SETTINGS_COPIED = (
    "fan_speed_steps",
    "speed_cycle_includes_off",
    "speed_cycle_turn_on",
)


def copy_remote_settings(remote: TriggerRemote, config: EntityConfig) -> None:
    """Make a Device from a typed Remote: its settings, onto ``config``."""
    for name in REMOTE_SETTINGS_COPIED:
        setattr(config, name, getattr(remote.entity_config, name))


def device_mapping_from_remote(
    remote: TriggerRemote, command_name_by_trigger: dict[str, str]
) -> dict[str, str]:
    """Make a Device from a typed Remote: its mapping, in command names.

    The reverse of ``seed_from_device`` (owner ruling 2026-10-22).
    ``command_name_by_trigger`` names the command each button became.
    """
    return {
        key: command_name_by_trigger[trigger_id]
        for key, trigger_id in tracked_mapping(
            remote.device_type, remote.entity_config.command_mapping
        ).items()
        if trigger_id in command_name_by_trigger
    }


def remote_device_info(remote: TriggerRemote) -> dict[str, Any]:
    """The Remote's HA device, in the shape every entity on it uses.

    Identical to the Last pressed and per-trigger entities' device
    info, so adding this entity changes nothing about the device.
    """
    return {
        "identifiers": {(DOMAIN, remote.id)},
        "name": remote.name,
        "manufacturer": "HAIR",
        "model": "IR Triggers",
    }


class RemoteStateMixin:
    """Put IN FRONT of a Device entity class to make a Remote's entity.

    ``class HAIRRemoteFanEntity(RemoteStateMixin, HAIRFanEntity)``. The
    Device class must provide ``_init_state``, ``_entity_config``,
    ``_apply_keys`` and ``_async_restore_state``, which every Device
    platform with a state entity does.
    """

    _remote_platform: str = ""

    def __init__(self, remote: TriggerRemote) -> None:
        self._remote = remote
        # The Device side's attributes, set so nothing inherited can
        # trip over a missing one; neither is ever used here.
        self._device = None
        self._manager = None
        self._attr_unique_id = remote_state_unique_id(
            remote.id, self._remote_platform
        )
        # Named by its device, so it reads as the remote ("Living Room
        # TV Remote"), which is how a user tells it from the Device.
        self._attr_name = None
        self._init_state()  # type: ignore[attr-defined]
        self._remote_pressed_unsub: CALLBACK_TYPE | None = None

    @property
    def remote_id(self) -> str:
        return self._remote.id

    @property
    def _entity_config(self) -> EntityConfig:
        return remote_entity_config(self._remote)

    @property
    def device_info(self) -> dict[str, Any]:
        return remote_device_info(self._remote)

    async def async_added_to_hass(self) -> None:
        await self._async_restore_state()  # type: ignore[attr-defined]
        self._remote_pressed_unsub = async_dispatcher_connect(
            self.hass,  # type: ignore[attr-defined]
            SIGNAL_REMOTE_PRESSED,
            self._handle_remote_pressed,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remote_pressed_unsub is not None:
            self._remote_pressed_unsub()
            self._remote_pressed_unsub = None

    @callback
    def _handle_remote_pressed(self, pressed: RemotePressed) -> None:
        """Apply one of this Remote's presses with the Device's rules."""
        if pressed.remote_id != self._remote.id:
            return
        keys = keys_for_trigger(
            self._entity_config.command_mapping, pressed.trigger_id
        )
        if keys:
            self._apply_keys(keys)  # type: ignore[attr-defined]

    async def _send(self, *feature_keys: str) -> bool:
        """Send NOTHING. A Remote's controls change its own state only.

        True when one of the keys is mapped, as the Device's ``_send``
        answers when it found a command, so a setter that steps (fan
        speed up and down) behaves the same.
        """
        mapping = self._entity_config.command_mapping
        return any(key in mapping for key in feature_keys)

    @callback
    def update_remote(self, remote: TriggerRemote) -> None:
        """Take the Remote's current record (mapping or name changed)."""
        self._remote = remote
        if self.hass is None or self.entity_id is None:  # type: ignore[attr-defined]
            # Disabled, or not added yet: HA writes the state once it is.
            return
        self.async_write_ha_state()  # type: ignore[attr-defined]

    @callback
    def update_device(self, device: Any) -> None:
        """A Remote's entity never follows a Device."""


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

_REGISTRY_KEY = "_remote_state_platforms"


@dataclass
class _Platform:
    add_entities: Callable[[list[Any]], None]
    make: Callable[[TriggerRemote], Any]
    entities: dict[str, Any]


def register_remote_platform(
    hass: HomeAssistant,
    entry_id: str,
    platform: str,
    add_entities: Callable[[list[Any]], None],
    make: Callable[[TriggerRemote], Any],
) -> None:
    """Called by each platform's setup: adds its typed Remotes' entities
    and lets ``sync_remote_state_entities`` keep them in step."""
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        return
    data.setdefault(_REGISTRY_KEY, {})[platform] = _Platform(
        add_entities=add_entities, make=make, entities={}
    )
    sync_remote_state_entities(hass, entry_id)


def remote_state_entity(
    hass: HomeAssistant, entry_id: str, remote_id: str
) -> Any | None:
    """The live state entity object of one Remote, or None."""
    data = hass.data.get(DOMAIN, {}).get(entry_id) or {}
    for registered in (data.get(_REGISTRY_KEY) or {}).values():
        entity = registered.entities.get(remote_id)
        if entity is not None:
            return entity
    return None


def remote_state_entity_id(hass: HomeAssistant, remote: TriggerRemote) -> str | None:
    """The registry's entity id for a Remote's state entity, or None."""
    platform = remote_platform(remote)
    if platform is None:
        return None
    from homeassistant.helpers import entity_registry as er

    try:
        return er.async_get(hass).async_get_entity_id(
            platform, DOMAIN, remote_state_unique_id(remote.id, platform)
        )
    except Exception:
        return None


def sync_remote_state_entities(
    hass: HomeAssistant, entry_id: str, removed_remote_id: str | None = None
) -> None:
    """Make the typed Remotes' state entities match the store. Idempotent.

    For every platform a Remote's entity can live on:

    - a Remote that is gone, untyped, or typed for another platform
      loses this platform's entity, and its registry row is forgotten
      (GH #186), so an automation on the old entity fails loudly rather
      than pointing at a ghost. The row goes even when this run holds
      no entity object for it;
    - a Remote typed for this platform gets its entity if it lacks one;
    - every live entity takes its Remote's current record.

    Called from ``event.sync_remote_entities``, which every Remote and
    button handler and the setup already call.
    """
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        return
    store = data.get("store")
    registry: dict[str, _Platform] = data.get(_REGISTRY_KEY) or {}
    if store is None:
        return
    live = {remote.id: remote for remote in store.get_all_trigger_remotes()}

    for platform in REMOTE_PLATFORMS:
        registered = registry.get(platform)
        held = registered.entities if registered is not None else {}
        retire = {
            rid
            for rid, remote in live.items()
            if remote_platform(remote) != platform
        } | {rid for rid in held if rid not in live}
        if removed_remote_id is not None:
            retire.add(removed_remote_id)
        for remote_id in retire:
            entity = held.pop(remote_id, None)
            if entity is not None and entity.hass is not None:
                hass.async_create_task(entity.async_remove())
            forget_entity_row(
                hass, platform, remote_state_unique_id(remote_id, platform)
            )
        if registered is None:
            continue
        added: list[Any] = []
        for remote_id, remote in live.items():
            if remote_platform(remote) != platform:
                continue
            entity = held.get(remote_id)
            if entity is None:
                entity = registered.make(remote)
                held[remote_id] = entity
                added.append(entity)
            else:
                entity.update_remote(remote)
        if added:
            registered.add_entities(added)
