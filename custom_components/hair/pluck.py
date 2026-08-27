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
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import PLUCK_TIMEOUT_S
from .learned_code_stores import (
    PROVIDERS,
    PROVIDERS_BY_INTEGRATION,
    StoreInfo,
    discover_stores,
    read_store,
)
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


def _replay_blasters(
    hass: HomeAssistant, ent_reg: Any, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    """Candidate blasters for one replay entry, or an empty list.

    Empty means "this vendor cannot replay anything right now", which is
    the single question both callers ask: ``list_vendors`` to decide
    whether to offer the vendor at all, and ``list_sources`` to decide
    whether its replay mechanism is ready. Factored so the two cannot
    drift into disagreeing about the same install.
    """
    service = entry["service"]
    if not hass.services.has_service(entry["integration"], service["name"]):
        return []
    feature_filter = entry.get("remote_feature_filter")
    blasters: list[dict[str, Any]] = []
    for re_entry in _remote_entities_for(ent_reg, entry["integration"]):
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
    return blasters


def list_vendors(
    hass: HomeAssistant, registry: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Two-stage discovery over the loaded pluckable registry.

    For each registered vendor whose cross-emitter service is present, list
    its candidate blaster entities (optionally filtered by a remote feature).
    Vendors with no candidate blaster are omitted -- this is the list of
    what can be replayed NOW, and an empty one is an honest answer rather
    than a reason to hide anything (the tab itself no longer gates on it).
    """
    ent_reg = er.async_get(hass)
    vendors: list[dict[str, Any]] = []
    for entry in registry:
        # Replay only. A store-read pluckable has no vendor service and
        # no blaster entity to list; it is offered by list_stores from
        # what is actually on disk.
        if entry.get("mechanism", "replay") != "replay":
            continue
        integration = entry["integration"]
        blasters = _replay_blasters(hass, ent_reg, entry)
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


# ---------------------------------------------------------------------
# MECHANISM TWO: STORE READ (0.10.3)
#
# Replay plucking asks a vendor integration to send a code and catches
# it at the Tweezer. That covers appliance codebooks and cannot cover a
# Broadlink at all, because its remote.send_command transmits through
# its own hardware and will not aim at anything else. The codes are
# still there though, at rest, in the file the integration writes under
# .storage. So the second mechanism reads them.
#
# Everything below is orchestration. The reading itself lives in
# learned_code_stores.py, which is pure and knows nothing about hass,
# and the placing lives in SignalMonitor.import_learned_store, which
# owns the catalog lock. Both file reads run in an executor: they are
# blocking disk I/O and the event loop does not do that (GH #72 is the
# expensive version of forgetting).
# ---------------------------------------------------------------------


def storage_integrations(registry: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Registered store-read pluckables, keyed by integration.

    The registry is what makes a provider offerable: the provider table
    in learned_code_stores knows HOW to read a Broadlink store, and the
    YAML entry is what says HAIR should offer to. A future integration
    that writes its codes the same way is a table row plus a YAML file.
    """
    return {
        entry["integration"]: entry
        for entry in registry
        if entry.get("mechanism") == "storage"
        and entry.get("integration") in PROVIDERS_BY_INTEGRATION
    }


def _mac_with_colons(store_id: str) -> str | None:
    """``a4cf12880e2f`` -> ``a4:cf:12:88:0e:2f``, or None if it is not one.

    Broadlink's config entry unique_id is the device MAC as bare hex
    (broadlink/config_flow.py sets ``device.mac.hex()``), and the device
    registry stores it with colons. This is the join between them, and
    it is also why the MAC never reaches the UI: it is a lookup key, and
    what the user sees is the name they gave the device.
    """
    text = (store_id or "").strip().lower()
    if len(text) != 12 or any(c not in "0123456789abcdef" for c in text):
        return None
    return ":".join(text[i:i + 2] for i in range(0, 12, 2))


def resolve_store_names(hass: HomeAssistant, infos: list[StoreInfo]) -> None:
    """Fill in each store's friendly name, in place.

    Two sources, cheapest first: the config entry whose unique_id is the
    store id (true for both integrations -- Broadlink's is the MAC hex,
    Tuya Local's is the entry unique_id the filename carries), then, for
    Broadlink, the device registry entry reached through that MAC, which
    is where a user-assigned name lives.

    Defensive throughout: a store whose integration has since been
    removed still has codes worth plucking, and it simply keeps its id
    as its name rather than disappearing from the list.
    """
    dev_reg = None
    try:
        dev_reg = dr.async_get(hass)
    except Exception:  # a registry-less test double is not a failure
        dev_reg = None

    for info in infos:
        name = ""
        try:
            for entry in hass.config_entries.async_entries(info.integration):
                if (getattr(entry, "unique_id", None) or "") == info.store_id:
                    name = (getattr(entry, "title", "") or "").strip()
                    break
        except Exception:
            name = ""
        mac = _mac_with_colons(info.store_id)
        if dev_reg is not None and info.integration == "broadlink" and mac:
            try:
                device = dev_reg.async_get_device(
                    connections={(dr.CONNECTION_NETWORK_MAC, mac)}
                )
            except Exception:
                device = None
            if device is not None:
                registry_name = (
                    getattr(device, "name_by_user", None)
                    or getattr(device, "name", None)
                    or ""
                )
                if isinstance(registry_name, str) and registry_name.strip():
                    name = registry_name.strip()
        info.friendly_name = name or info.store_id


async def _discover(
    hass: HomeAssistant, registry: list[dict[str, Any]]
) -> list[StoreInfo]:
    offered = storage_integrations(registry)
    if not offered:
        return []
    infos = await hass.async_add_executor_job(
        discover_stores, hass.config.config_dir
    )
    infos = [info for info in infos if info.integration in offered]
    resolve_store_names(hass, infos)
    return infos


async def list_stores(
    hass: HomeAssistant, registry: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Every discovered learned-code store, counted but not decoded.

    Cheap by construction: one file read and a first-byte peek per code,
    no decoding. A store that will not parse comes back carrying its
    receipt instead of vanishing, and never takes its siblings with it.
    """
    infos = await _discover(hass, registry)
    return [info.to_dict() for info in infos]


# ---------------------------------------------------------------------
# THE SOURCE ROLL (constant-tab plan, 2026-08-27)
#
# What the empty Plucker tab reads out. Not "what can be plucked now" --
# list_vendors and list_stores answer that, and answering only that is
# what hid the tab from every Broadlink owner who had never learned a
# code. This answers the other question: what could this install EVER
# pluck, and what is the state of each route today.
#
# Collapsed PER INTEGRATION, not per registry entry. Tuya Local is
# registered twice, once for replay (tuya_local.yaml) and once for
# storage (tuya_local_storage.yaml), and a person reading the card does
# not have two Tuya Locals -- they have one, with two ways in. So the
# entry carries a list of mechanisms and a ready flag per mechanism.
# ---------------------------------------------------------------------

MECHANISM_REPLAY = "replay"
MECHANISM_STORAGE = "storage"


def _source_display_name(integration: str) -> str:
    """A name for a provider with no registry entry to name it.

    The union below can hold a store provider that no ``pluckable/``
    yaml describes, and the card still has to call it something. Domain
    style is close enough to product style for the two that exist
    (``tuya_local`` -> "Tuya Local", ``broadlink`` -> "Broadlink"), and
    a registry entry always wins over this when there is one.
    """
    return integration.replace("_", " ").title()


async def list_sources(
    hass: HomeAssistant, registry: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Every pluckable source this build knows, and where each stands.

    The set is the UNION of the ``pluckable/`` registry and the store
    provider table, so a provider whose integration was never installed
    still appears -- with ``loaded`` false, which is what lets the empty
    tab double as the feature's shop window instead of only describing
    the install it happens to be running on.
    """
    ent_reg = er.async_get(hass)
    sources: dict[str, dict[str, Any]] = {}

    def _slot(integration: str, name: str | None = None) -> dict[str, Any]:
        entry = sources.get(integration)
        if entry is None:
            entry = {
                "integration": integration,
                "name": name or _source_display_name(integration),
                "mechanisms": [],
                "loaded": integration in (hass.config.components or set()),
                "ready": {},
            }
            sources[integration] = entry
        elif name:
            # A registry name beats the derived one, whichever entry
            # created the slot first.
            entry["name"] = name
        return entry

    for entry in registry:
        mechanism = entry.get("mechanism", MECHANISM_REPLAY)
        if mechanism not in (MECHANISM_REPLAY, MECHANISM_STORAGE):
            continue
        integration = entry["integration"]
        slot = _slot(integration, entry.get("name"))
        if mechanism not in slot["mechanisms"]:
            slot["mechanisms"].append(mechanism)
        if mechanism == MECHANISM_REPLAY:
            # The same test the vendor listing applies, through the same
            # helper, so this can never say ready while the vendor list
            # omits it.
            ready = bool(_replay_blasters(hass, ent_reg, entry))
            slot["ready"][MECHANISM_REPLAY] = (
                slot["ready"].get(MECHANISM_REPLAY, False) or ready
            )
        else:
            slot["ready"].setdefault(MECHANISM_STORAGE, False)

    for provider in PROVIDERS:
        slot = _slot(provider.integration)
        if MECHANISM_STORAGE not in slot["mechanisms"]:
            slot["mechanisms"].append(MECHANISM_STORAGE)
        slot["ready"].setdefault(MECHANISM_STORAGE, False)

    # One disk walk for every storage provider at once, in the executor:
    # discover_stores globs .storage, which is blocking I/O.
    if any(MECHANISM_STORAGE in slot["mechanisms"] for slot in sources.values()):
        infos = await hass.async_add_executor_job(
            discover_stores, hass.config.config_dir
        )
        for info in infos:
            slot = sources.get(info.integration)
            if slot is not None and MECHANISM_STORAGE in slot["mechanisms"]:
                slot["ready"][MECHANISM_STORAGE] = True

    for slot in sources.values():
        slot["mechanisms"].sort()
    return sorted(sources.values(), key=lambda slot: slot["name"].lower())


async def run_store_pluck(
    hass: HomeAssistant,
    *,
    entry_data: dict[str, Any],
    registry: list[dict[str, Any]],
    store_id: str,
) -> dict[str, Any]:
    """Import one whole store: every subdevice, every code.

    Import-all by owner ruling -- there is no subdevice picker, and
    pruning is a delete afterwards, which users already know how to do.
    Returns the import summary, or ``{"error": code, "message": text}``
    for the WS layer to turn into an error result.
    """
    monitor = entry_data.get("signal_monitor")
    if monitor is None:
        return {"error": "not_configured", "message": "HAIR is not ready yet"}

    infos = await _discover(hass, registry)
    info = next((i for i in infos if i.store_id == store_id), None)
    if info is None:
        return {
            "error": "unknown_store",
            "message": "That learned-code store is no longer there",
        }
    if info.parse_error:
        return {"error": "unreadable_store", "message": info.parse_error}

    provider = PROVIDERS_BY_INTEGRATION[info.integration]
    codes = await hass.async_add_executor_job(read_store, info)
    if not codes:
        return {
            "error": "empty_store",
            "message": "That store has no codes in it",
        }
    return await monitor.import_learned_store(
        integration=info.integration,
        store_id=info.store_id,
        friendly_name=info.friendly_name,
        kind=provider.kind,
        codes=codes,
    )
