"""Pluck orchestrator: vendor discovery + single-pluck session machinery.

A pluck routes a vendor "send learned code" service at the HAIR Tweezer and
captures the resulting infrared ``Command`` before it becomes physical IR.
The vendor call is awaited (``blocking=True``), so on the happy path the
captures land synchronously within the await; a short timeout is the safety
net. Plucks are serialized per config entry by a lock so exactly one Tweezer
session is open at a time.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import PLUCK_TIMEOUT_S
from .signal_monitor import NormalizedSignal, normalize_command

_LOGGER = logging.getLogger(__name__)

# RemoteEntityFeature.LEARN_COMMAND bit. Hardcoded to avoid importing the
# remote component just for the constant (its value is stable).
_LEARN_COMMAND_BIT = 1


def _render(template: str, context: dict[str, str]) -> str:
    """Fill a service.data template. str.format never re-formats values, so
    a user value containing ``{...}`` is inserted literally and never
    re-substituted.
    """
    return template.format(**context)


def _map_error(raw: str, error_map: dict[str, str], vendor_name: str) -> str:
    """Map a raw vendor error to friendly text, else pass through prefixed."""
    for substring, friendly in error_map.items():
        if substring in raw:
            return friendly
    return f"{vendor_name}: {raw}"


def _normalized_to_dict(
    n: NormalizedSignal, command_name: str, suggested_alias: str
) -> dict[str, Any]:
    """Shape a normalized pluck capture for the Pluck Signal dialog."""
    return {
        "code": n.code,
        "protocol": n.protocol,
        "frequency": n.frequency,
        "raw_timings": n.raw_timings,
        "fingerprint": n.sig_fp,
        "byte_hash": n.byte_hash,
        "decoded_protocol": n.decoded_protocol,
        "decoded_address": n.decoded_address,
        "decoded_command": n.decoded_command,
        "decoded_fingerprint": n.decoded_fingerprint,
        "decoded_extras": dict(n.decoded_extras) if n.decoded_extras else None,
        "plucked_command_name": command_name,
        "suggested_alias": suggested_alias,
    }


async def run_pluck(
    hass: HomeAssistant,
    *,
    entry_data: dict[str, Any],
    vendor_entry: dict[str, Any],
    vendor_entity_id: str,
    appliance: str,
    command_name: str,
) -> dict[str, Any]:
    """Fire the vendor service at the Tweezer and return the captures.

    Returns either ``{"signals": [...]}`` on success or
    ``{"error": code, "message": text}`` for the dialog to render inline.
    """
    tweezer = entry_data.get("tweezer")
    tweezer_entity_id = getattr(tweezer, "entity_id", None) if tweezer else None
    if tweezer is None or not tweezer_entity_id:
        return {
            "error": "no_tweezer",
            "message": "HAIR Tweezer is not ready yet. Try again in a moment.",
        }

    service = vendor_entry["service"]
    context = {
        "command_name": command_name,
        "appliance": appliance,
        "tweezer": tweezer_entity_id,
    }
    service_data = {key: _render(val, context) for key, val in service["data"].items()}
    error_map = vendor_entry.get("error_map") or {}
    vendor_name = vendor_entry.get("name", "Vendor")

    lock: asyncio.Lock = entry_data.setdefault("_pluck_lock", asyncio.Lock())
    session_id = uuid4().hex

    async with lock:
        tweezer.open_session(session_id)
        try:
            await asyncio.wait_for(
                hass.services.async_call(
                    service["domain"],
                    service["name"],
                    target={service["target_param"]: vendor_entity_id},
                    service_data=service_data,
                    blocking=True,
                ),
                timeout=PLUCK_TIMEOUT_S,
            )
        except TimeoutError:
            tweezer.pop_captures(session_id)
            return {
                "error": "no_response",
                "message": "No response from blaster. Try again.",
            }
        except ValueError as err:
            tweezer.pop_captures(session_id)
            return {
                "error": "vendor_error",
                "message": _map_error(str(err), error_map, vendor_name),
            }
        except Exception as err:  # surface anything, never crash the pluck
            tweezer.pop_captures(session_id)
            _LOGGER.exception("Pluck failed for %s", vendor_entity_id)
            return {"error": "unknown", "message": f"Pluck failed: {err}"}
        captured = tweezer.pop_captures(session_id)

    if not captured:
        return {
            "error": "no_response",
            "message": "No response from blaster. Try again.",
        }

    multi = len(captured) > 1
    signals = [
        _normalized_to_dict(
            normalize_command(command),
            command_name,
            f"{command_name}_{idx + 1}" if multi else command_name,
        )
        for idx, command in enumerate(captured)
    ]
    return {"signals": signals}


def _remote_entities_for(
    ent_reg: Any, integration: str
) -> list[Any]:
    """Registry entries for ``remote.*`` entities of a given integration."""
    out = []
    for entry in ent_reg.entities.values():
        if getattr(entry, "platform", None) != integration:
            continue
        if not str(getattr(entry, "entity_id", "")).startswith("remote."):
            continue
        if getattr(entry, "disabled_by", None) is not None:
            continue
        out.append(entry)
    return out


def list_vendors(
    hass: HomeAssistant, registry: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Two-stage discovery over the loaded pluckable registry.

    For each registered vendor whose cross-emitter service is present, list
    its candidate blaster entities (optionally filtered by a remote feature).
    Vendors with no candidate blaster are omitted, so the Plucker UI hides
    entirely when nothing is pluckable.
    """
    ent_reg = er.async_get(hass)
    vendors: list[dict[str, Any]] = []
    for entry in registry:
        integration = entry["integration"]
        service = entry["service"]
        if not hass.services.has_service(integration, service["name"]):
            continue
        feature_filter = entry.get("remote_feature_filter")
        blasters: list[dict[str, Any]] = []
        for re_entry in _remote_entities_for(ent_reg, integration):
            if feature_filter == "LEARN_COMMAND":
                features = getattr(re_entry, "supported_features", 0) or 0
                if not features & _LEARN_COMMAND_BIT:
                    continue
            entity_id = re_entry.entity_id
            blasters.append(
                {
                    "entity_id": entity_id,
                    "name": (
                        getattr(re_entry, "name", None)
                        or getattr(re_entry, "original_name", None)
                        or entity_id
                    ),
                }
            )
        if not blasters:
            continue
        vendors.append(
            {
                "integration": integration,
                "name": entry["name"],
                "appliance_label": entry.get("appliance_label"),
                "appliance_help": entry.get("appliance_help"),
                "blasters": blasters,
            }
        )
    return vendors
