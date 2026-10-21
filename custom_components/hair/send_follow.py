"""What a send means to a flat Device's entity (heard state, round 1).

``SIGNAL_DEVICE_SENT`` carries the command that went out. A media
player, fan, light, switch or cover reads it the way its own setters
would: through ``entity_config.command_mapping``, the feature keys the
user mapped to that command. This module answers the two questions every
one of those platforms asks, so none of them reimplements the rules:

- which feature keys name the sent command (``mapped_keys``), and
- what that does to power (``power_after``).

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


def one_of(keys: frozenset[str], *choices: str) -> str | None:
    """The single key of ``choices`` the send carries, or None when it
    carries none of them or more than one (a contradiction)."""
    present = [choice for choice in choices if choice in keys]
    return present[0] if len(present) == 1 else None
