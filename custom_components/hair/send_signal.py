"""What HAIR just sent, for the entities that follow it (0.10.1 item 7).

ONE SIGNAL FROM THE SEND CHOKE POINT. Every device send passes through
``device_manager._async_broadcast``, and until 0.10.1 nothing downstream
heard about it: only the climate entity's OWN services moved the
thermostat card, so a STATE MATRIX send, a saved STATE row, a preset, a
pinned Remote's retransmit and a HAIR button entity all reached the air
conditioner and left the card where it was. GH #105 is the report; the
owner's ruling in the same breath was that ANY send HAIR makes to a
climate Device should move the card.

SENT ONLY. This is dispatched from the SEND path and nowhere else. A
matrix Remote hearing the wall handset does not touch the card unless it
is PINNED, and then it is the pinned SEND that does, through this same
door. Nothing here is wired to the hear path, deliberately.

Exactly the ``SIGNAL_POWER_VERDICT`` pattern that already exists between
``power_monitor`` and ``climate``, and it layers UNDER it: a send moves
mode, fan, swing, temp and power as BELIEF, and the plug remains the last
word on on/off whenever it speaks.

WHY A MODULE OF ITS OWN. So ``climate.py`` imports a constant and a
dataclass rather than the device manager, which imports the entity
factory, which the platforms import. One small leaf keeps that direction
one-way.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import DOMAIN

SIGNAL_DEVICE_SENT = f"{DOMAIN}_device_sent"

# Who asked for the send. An entity ignores its own: its setters have
# already written the state they intended, and applying it a second time
# through the handler would write the state twice and, worse, let a
# derived reading overwrite the exact one the setter had in hand.
ORIGIN_MANAGER = "manager"
ORIGIN_ENTITY = "entity"


@dataclass(frozen=True, slots=True)
class DeviceSent:
    """One landed send, described structurally.

    Coordinates travel as coordinates. Nothing downstream parses a
    display name back into mode/fan/temp: the display grammar is a
    human surface that converts units live and freezes at mint time,
    so reading state out of it would be a guess dressed as a fact.
    Callers always know what they sent, so they say it.

    ``matrix_cell`` and ``power`` are mutually exclusive by
    construction, the same way ``CellHit`` keeps them apart on the hear
    side. Both None means a send with no state meaning: a flat device's
    mapped command, or an extras button on a matrix device.
    """

    device_id: str
    command_id: str | None = None
    command_name: str = ""
    # {"mode", "fan", "swing", "temp"} -- a lattice cell's coordinates.
    matrix_cell: dict[str, Any] | None = field(default=None)
    # "off" | "on" -- the matrix's own power codes.
    power: str | None = None
    # The send was a starred command, so it IS an HA preset selection.
    starred: bool = False
    origin: str = ORIGIN_MANAGER
