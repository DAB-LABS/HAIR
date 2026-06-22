"""Infrared emitter platform for HAIR -- the HAIR Tweezer observer.

HAIR registers a single emitter entity on HA's ``infrared`` platform: the
HAIR Tweezer. It does NOT transmit. Its purpose is to be a target that a
vendor "send learned code" service (e.g. ``tuya_local.send_learned_ir_command``)
can fire at, so HAIR captures the resulting infrared ``Command`` before it
ever becomes physical IR. This is the capture primitive behind the Plucker
(v0.5.0).

The Tweezer is intentionally visible in HA's general emitter list (vendor
services must be able to target it) but is filtered out of HAIR's own emitter
pickers via the ``hair_observer`` marker attribute (see ``config_flow`` and,
from Phase 4, the frontend pickers).
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TWEEZER_OBSERVER_ATTR

_LOGGER = logging.getLogger(__name__)

# Base-class portability: HA 2026.6+ exports ``InfraredEmitterEntity``; HA
# 2026.5 only exports the base ``InfraredEntity``. Plucker requires 2026.6+,
# so the fallback should not trigger in practice -- it is insurance against a
# rename or an older install.
try:  # pragma: no cover - import guard, env-dependent
    from homeassistant.components.infrared import (  # type: ignore[attr-defined]
        InfraredEmitterEntity as _Base,
    )
except ImportError:  # pragma: no cover - 2026.5 fallback
    from homeassistant.components.infrared import (  # type: ignore[attr-defined]
        InfraredEntity as _Base,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HAIR Tweezer observer emitter for a config entry."""
    tweezer = HAIRTweezer(entry.entry_id)
    # Stash a reference so the pluck orchestrator (Phase 2) can open a
    # session and read the Commands captured during it.
    hass.data.setdefault(DOMAIN, {})
    entry_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})
    entry_data["tweezer"] = tweezer
    async_add_entities([tweezer])


class HAIRTweezer(_Base):
    """Observer emitter that captures Commands instead of transmitting.

    A vendor service targets this entity to replay a stored code; the
    resulting infrared ``Command`` is captured into the active pluck session
    and never broadcast as physical IR.

    Concurrency: the entity holds at most one active session at a time. The
    pluck orchestrator (Phase 2) serializes plucks with a lock, so a single
    session is open during any given vendor call. A ``Command`` arriving with
    no open session (nothing is plucking) is dropped.
    """

    _attr_has_entity_name = False
    _attr_name = "HAIR Tweezer"

    def __init__(self, entry_id: str) -> None:
        """Initialize the Tweezer."""
        self._attr_unique_id = f"{entry_id}_hair_tweezer"
        self._active_session: str | None = None
        # session_id -> list of captured Commands for that session.
        self._captures: dict[str, list[Any]] = {}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Marker so HAIR filters the Tweezer out of its own emitter pickers."""
        return {TWEEZER_OBSERVER_ATTR: True}

    # -- pluck-session capture API (driven by the orchestrator, Phase 2) ----

    def open_session(self, session_id: str) -> None:
        """Begin capturing Commands for a pluck session."""
        self._captures[session_id] = []
        self._active_session = session_id

    def pop_captures(self, session_id: str) -> list[Any]:
        """Return and clear the Commands captured for a session.

        Closes the session if it is the active one.
        """
        if self._active_session == session_id:
            self._active_session = None
        return self._captures.pop(session_id, [])

    async def async_send_command(self, command: Any) -> None:
        """Capture the Command into the active session. Never transmits."""
        session_id = self._active_session
        if session_id is None:
            _LOGGER.debug(
                "HAIR Tweezer received a Command with no open pluck session;"
                " dropping it (nothing is plucking)."
            )
            return
        self._captures[session_id].append(command)
