"""What a send means to a flat Device's entity (heard state, round 1).

``SIGNAL_DEVICE_SENT`` carries the command that went out. A media
player, fan, light, switch or cover reads it the way its own setters
would: through ``entity_config.command_mapping``, the feature keys the
user mapped to that command. This module answers the two questions every
one of those platforms asks, so none of them reimplements the rules:

- which feature keys name the sent command (``mapped_keys``), and
- what that does to power (``power_after``).

A typed Remote (round 2a) reads its own handset presses through the
same rules: ``keys_for_trigger`` is its ``mapped_keys``, and each
Remote entity applies the keys with its Device class's own code.

ONE COMMAND, SEVERAL KEYS. A handset's single Power button is often
mapped to more than one key, and the keys can disagree. The rules:

- A toggle wins. ``power_toggle``, or ``turn_on`` and ``turn_off`` on
  the same command, flips. ``power_toggle`` is the user saying the code
  is relative, and the entity's own ``turn_off`` sends that same code
  whenever ``turn_off`` is unmapped, so the code demonstrably goes both
  ways. A flip is right whenever the state before it was; "on" would be
  wrong every second press of a real toggle. The power sensor corrects
  either.
- Two absolute keys that contradict each other (volume up and down,
  open and close) move nothing: there is no honest answer.
- Power is decided first. A command that turns the entity off turns
  nothing else on.

ONE BUTTON THAT STEPS ROUND THE SPEEDS. ``speed_cycle`` is relative,
like a toggle: each send moves the fan one position on (``cycle_step``),
wrapping back to the start, and only the count kept by the entity says
where that is. The entity's own presses carry ``ORIGIN_ENTITY`` and are
skipped, exactly as for a toggle, or a burst would count twice.

A send is BELIEF. The power sensor's verdict (``SIGNAL_POWER_VERDICT``)
still has the last word on on/off, exactly as for climate.

A leaf, like ``send_signal``: it imports nothing from the platforms.
"""
from __future__ import annotations

from typing import Any

from .send_signal import DeviceSent

TURN_ON = "turn_on"
TURN_OFF = "turn_off"
POWER_TOGGLE = "power_toggle"
SPEED_CYCLE = "speed_cycle"


def mapped_keys(device: Any, sent: DeviceSent) -> frozenset[str]:
    """Every feature key whose mapped command is the one that was sent.

    The command is found by id on the device's current record, so a
    rename since the send was queued still resolves; the name the send
    carried is the fallback when the command is gone. Casefolded, as
    ``climate._reverse_command_mapping`` matches, and built per call
    because a mapping change arrives with no signal of its own.
    """
    name = ""
    if sent.command_id:
        command = device.get_command(sent.command_id)
        if command is not None:
            name = command.name
    if not name:
        name = sent.command_name
    if not name:
        return frozenset()
    wanted = name.casefold()
    return frozenset(
        key
        for key, mapped in device.entity_config.command_mapping.items()
        if mapped and str(mapped).casefold() == wanted
    )


def keys_for_trigger(mapping: dict[str, str], trigger_id: str) -> frozenset[str]:
    """Every action key a typed Remote maps to one of its buttons.

    The Remote-side twin of ``mapped_keys`` (heard state, round 2a). A
    Remote's ``command_mapping`` names trigger ids rather than command
    names, so this is an exact match; the rules applied to the keys it
    returns are this module's, for a Remote exactly as for a Device.
    """
    return frozenset(
        key for key, mapped in mapping.items() if mapped and mapped == trigger_id
    )


def power_after(keys: frozenset[str], is_on: bool) -> bool | None:
    """The on/off state a send leaves, or None when it says nothing.

    See the module docstring for why a toggle wins.
    """
    on, off = TURN_ON in keys, TURN_OFF in keys
    if POWER_TOGGLE in keys or (on and off):
        return not is_on
    if on:
        return True
    if off:
        return False
    return None


def _mapped_name(mapping: dict[str, Any], key: str) -> str | None:
    value = mapping.get(key)
    return str(value).casefold() if value else None


def is_toggle(mapping: dict[str, Any], key: str, command_name: str) -> bool:
    """Is sending ``command_name`` (found through ``key``) a power toggle?

    The same reading ``power_after`` makes of a send: ``power_toggle``
    says the code is relative, and so does one command mapped to both
    ``turn_on`` and ``turn_off``. A discrete on or off code is not.
    """
    if key == POWER_TOGGLE:
        return True
    name = command_name.casefold()
    if _mapped_name(mapping, POWER_TOGGLE) == name:
        return True
    return (
        _mapped_name(mapping, TURN_ON) == name
        and _mapped_name(mapping, TURN_OFF) == name
    )


def toggle_already_there(
    device: Any,
    mapping: dict[str, Any],
    keys: tuple[str, ...],
    is_on: bool,
    want_on: bool,
) -> bool:
    """Would sending for ``keys`` toggle a device already where it is wanted?

    TOGGLE POWER, PIECE 1 (GH #229 point 1). An entity's on and off
    setters send the first of ``keys`` that is mapped to a command the
    device has, falling back from ``turn_off`` to ``power_toggle``. When
    that command is a toggle and HAIR already believes the device is in
    the wanted state, sending it would flip the device the wrong way,
    so the setter sends nothing. A discrete code always sends, as it
    always has: resending a real off is harmless and corrects a belief
    that drifted.

    ``is_on`` is the entity's believed state, which a configured power
    sensor or on/off entity keeps right. ``device`` is None for a typed
    Remote's entity, which never sends, and the answer is then False.

    Mirrors the entity ``_send`` lookup exactly (mapping value, then the
    device's command by that name), so this answers about the command
    ``_send`` would really pick.
    """
    if device is None or is_on != want_on:
        return False
    for key in keys:
        command_name = mapping.get(key)
        if command_name is None:
            continue
        command = device.get_command_by_name(command_name)
        if command is None:
            continue
        return is_toggle(mapping, key, command.name)
    return False


def one_of(keys: frozenset[str], *choices: str) -> str | None:
    """The single key of ``choices`` the send carries, or None when it
    carries none of them or more than one (a contradiction)."""
    present = [choice for choice in choices if choice in keys]
    return present[0] if len(present) == 1 else None


def cycle_step(position: int, length: int) -> int:
    """Where one press of a cycle button leaves a cycle of ``length``
    positions: the next one, wrapping from the last back to 0."""
    return (position + 1) % length
