"""The HAIR (Home Assistant IR Admin) integration."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE, Platform
from homeassistant.core import Event, HomeAssistant

from .capture_orchestrator import CaptureOrchestrator
from .const import DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL, PLUCKABLE_DIRNAME
from .device_manager import DeviceManager, prime_localized_auto_map
from .entity_factory import EntityFactory
from .matrix_listener import MatrixListener
from .pluckable_loader import load_pluckables
from .power_monitor import PowerMonitor
from .signal_monitor import SignalMonitor
from .signal_store import SignalStore
from .storage import HAIRStore
from .trigger_manager import TriggerManager
from .websocket_api import async_register_websocket_commands
from .wig_store import ensure_wigs_dir

_LOGGER = logging.getLogger(__name__)

_BUTTON_PLATFORM = getattr(Platform, "BUTTON", None)
_EVENT_PLATFORM = getattr(Platform, "EVENT", None)
# Infrared emitter platform (HA 2026.6+) hosts the HAIR Tweezer observer
# used by the Plucker. Falls back to the bare "infrared" domain string when
# the Platform enum member is absent; async_forward_entry_setups accepts the
# domain string, so this works either way (Plucker plan Q12).
_INFRARED_PLATFORM = getattr(Platform, "INFRARED", None) or "infrared"

PLATFORMS_LIST: list[Platform | str] = [
    p
    for p in [
        _BUTTON_PLATFORM,
        _EVENT_PLATFORM,
        Platform.REMOTE,
        Platform.MEDIA_PLAYER,
        Platform.CLIMATE,
        Platform.FAN,
        Platform.LIGHT,
        Platform.SWITCH,
        Platform.COVER,
        _INFRARED_PLATFORM,
    ]
    if p is not None
]

PANEL_FILENAME = "ha-panel-ir-devices.js"
PANEL_STATIC_PATH = "/hair_panel/ha-panel-ir-devices.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up HAIR (top-level)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up HAIR from a config entry."""
    # One-time migration: fix legacy entry title.
    if entry.title != "HAIR":
        hass.config_entries.async_update_entry(entry, title="HAIR")

    store = HAIRStore(hass)
    await store.async_load()

    signal_store = SignalStore(hass)
    await signal_store.async_load()

    # The one backfill that needs both stores loaded: a trigger minted
    # from a Clipper or Plucker row was stamped "remote" before the
    # origin vocabulary could say otherwise, and only the signal store
    # knows which catalog row a Remote was promoted from. One save.
    if store.backfill_catalog_trigger_origins(signal_store):
        await store.async_save()

    # Load the pluckable YAML registry in a single executor hop (off-loop).
    pluckable_registry = await hass.async_add_executor_job(
        load_pluckables, Path(__file__).parent / PLUCKABLE_DIRNAME
    )

    # Prime the localized auto-map synonyms table off the event loop
    # (reads the panel locale files once, cached for the process).
    await hass.async_add_executor_job(prime_localized_auto_map)

    # The wig closet: /config/hair/wigs/ exists from first boot so "drop
    # your files here" is always true (wigs.md section 4). Lives outside
    # custom_components/ because HACS replaces that tree on update.
    await hass.async_add_executor_job(ensure_wigs_dir, hass.config.config_dir)

    entity_factory = EntityFactory(hass)
    orchestrator = CaptureOrchestrator(hass)
    power_monitor = PowerMonitor(hass, store)
    device_manager = DeviceManager(
        hass, store, entity_factory, entry.entry_id, power_monitor
    )
    # device_manager is passed so a pinned Remote can drive its
    # pinned Devices (signpost 4, Track 2). It is constructed
    # above, and DeviceManager takes a TriggerManager only as a
    # per-call argument, so this direction closes no cycle.
    trigger_manager = TriggerManager(hass, store, device_manager)
    # The hear side of a matrix Remote (signpost 4, Track M). Owns the
    # per-remote matrix cache and cell indexes, and is consulted from
    # the capture path beside the trigger match. It takes the trigger
    # manager for two things that manager already owns: resolving a
    # receiver to an HA area, and the panel's push channel.
    matrix_listener = MatrixListener(
        hass, store, trigger_manager, device_manager
    )
    # And back the other way, after construction: a heard state on a
    # pinned matrix Remote leaves through the trigger manager's own
    # retransmit dispatcher (signpost 4, Track 4), so both kinds of
    # retransmit share one coalescer and one loop breaker.
    trigger_manager.set_matrix_listener(matrix_listener)
    signal_monitor = SignalMonitor(
        hass, signal_store, store, trigger_manager, matrix_listener
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "signal_store": signal_store,
        "device_manager": device_manager,
        "orchestrator": orchestrator,
        "entity_factory": entity_factory,
        "signal_monitor": signal_monitor,
        "power_monitor": power_monitor,
        "trigger_manager": trigger_manager,
        "matrix_listener": matrix_listener,
        "pluckable_registry": pluckable_registry,
        "config_entry": entry,
    }

    # An emitter's platform decides whether a spaced row's repeats can
    # go out as one bundled list (send_plan). The answer is cached per
    # entity id and dropped whenever the registry moves, because a
    # rename or a re-add can put a different integration behind the
    # same id.
    from .send_plan import register_platform_cache_invalidation

    entry.async_on_unload(register_platform_cache_invalidation(hass))

    # THE SNIFFER CATALOG HAS TO REACH DISK WHEN HOME ASSISTANT STOPS
    # (WigFactory bench 2026-09-23: four sends made in the seconds
    # before a graceful restart were gone afterwards; the two after it
    # were there).
    #
    # Captures are written on a debounce with a ceiling, so the file is
    # routinely up to SIGNAL_SAVE_DEBOUNCE_S behind memory, and a
    # ``loop.call_later`` handle is worth nothing once the loop stops.
    # The unload path already closes its own half: async_unload_entry
    # stops the monitor, whose async_stop flushes the store. But A
    # GRACEFUL SHUTDOWN DOES NOT UNLOAD CONFIG ENTRIES, so on a restart
    # none of that runs. The two hooks cover disjoint cases -- unload
    # for reload and removal, this one for stop and restart -- and
    # neither is redundant.
    #
    # FINAL_WRITE, not STOP: STOP is the stage where integrations are
    # still being torn down and may still write, and FINAL_WRITE is the
    # one core reserves for persisting what they leave behind. Core
    # fires it and then blocks on the pending tasks, so an async
    # listener is awaited rather than raced. It is the same event
    # core's own ``Store.async_delay_save`` registers for.
    #
    # Registered under ``async_on_unload`` so a reload cannot leave a
    # listener pointing at the previous entry's store.

    async def _flush_signal_store(_event: Event) -> None:
        """Write the catalog if the debounce has not yet caught up."""
        if await signal_store.async_flush():
            _LOGGER.debug("Sniffer catalog flushed at final write")

    entry.async_on_unload(
        hass.bus.async_listen(
            EVENT_HOMEASSISTANT_FINAL_WRITE, _flush_signal_store
        )
    )

    async_register_websocket_commands(hass)

    await _async_register_panel(hass, entry)

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_LIST
    )

    # Cell indexes are warmed HERE, strictly before any receiver is
    # subscribed (0.10.1 item 3). signal_monitor.async_start below is
    # what calls async_subscribe_receiver, so a frame cannot arrive
    # while a lattice is still being read; the first press after a
    # restart matches. The lazy first-frame build stays as the fallback
    # for a remote minted later in the run.
    await matrix_listener.async_warm_indexes()

    # Saved STATE rows minted before 0.10.1 carry only their cell's
    # bytes, so a send told the climate card nothing. Matching them back
    # against each device's CURRENT lattice needs this manager's matrix
    # cache, which is why it runs here and not inside store.async_load.
    await device_manager.async_backfill_sent_states()

    await signal_monitor.async_start()
    # Started AFTER platform setup (same reason signal_monitor is): each
    # device's subscription immediately evaluates and dispatches its power
    # sensor's current reading (the startup seed), and platform entities
    # must already be listening -- via async_added_to_hass, which runs
    # during async_forward_entry_setups above -- to catch it.
    power_monitor.start()

    return True


async def _async_register_panel(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register the admin panel and its static asset.

    The panel JS is bundled and committed to the integration directory
    under ``frontend/dist``. We expose it as a static path and pass that
    URL to ``panel_custom`` so HA loads it as a JS module.
    """
    panel_data = hass.data[DOMAIN]
    if panel_data.get("_panel_registered"):
        return
    panel_data["_panel_registered"] = True

    bundle_path = (
        Path(__file__).parent / "frontend" / "dist" / PANEL_FILENAME
    )

    # Compute content hash for cache busting. The read is wrapped in an
    # executor so the event loop isn't blocked while a ~200 KB bundle is
    # read from disk (HA's loop detector flags this otherwise).
    content_hash = ""
    try:
        if bundle_path.exists():
            raw = await hass.async_add_executor_job(bundle_path.read_bytes)
            content_hash = hashlib.md5(raw).hexdigest()[:8]
    except (OSError, TypeError):
        content_hash = ""

    versioned_path = f"{PANEL_STATIC_PATH}?v={content_hash}" if content_hash else PANEL_STATIC_PATH

    frontend_dir = Path(__file__).parent / "frontend"
    if bundle_path.exists():
        try:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        PANEL_STATIC_PATH,
                        str(bundle_path),
                        cache_headers=False,
                    ),
                    StaticPathConfig(
                        "/hair_panel/assets",
                        str(frontend_dir),
                        cache_headers=True,
                    ),
                ]
            )
        except RuntimeError:
            # Route already registered from a previous setup; safe to ignore.
            _LOGGER.debug("Static path %s already registered", PANEL_STATIC_PATH)

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="ha-panel-ir-devices",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL,
        config={"entry_id": entry.entry_id},
        require_admin=True,
        embed_iframe=False,
        trust_external=False,
        module_url=versioned_path,
    )


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a HAIR config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS_LIST
    )
    if not unload_ok:
        return False

    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data is not None:
        orchestrator: CaptureOrchestrator = data["orchestrator"]
        if orchestrator.is_capturing and orchestrator.active_session is not None:
            await orchestrator.cancel_capture(
                orchestrator.active_session.session_id
            )

        monitor: SignalMonitor | None = data.get("signal_monitor")
        if monitor is not None:
            await monitor.async_stop()

        power_monitor: PowerMonitor | None = data.get("power_monitor")
        if power_monitor is not None:
            power_monitor.stop()

        tm: TriggerManager | None = data.get("trigger_manager")
        if tm is not None:
            tm.shutdown()

        # Belt and braces on the unload half. ``monitor.async_stop``
        # above already flushes the catalog (it ends in the store's own
        # ``async_shutdown``), and that is the path a normal unload
        # takes. This covers the one case that path does not: an entry
        # torn down without a monitor in its data, which a setup that
        # failed part way through leaves behind. Ordered AFTER the
        # monitor stop so nothing can schedule a save into the gap, and
        # a no-op on a clean store, so the usual unload pays nothing
        # for it.
        sig_store: SignalStore | None = data.get("signal_store")
        if sig_store is not None:
            await sig_store.async_flush()


    if not any(
        isinstance(v, dict) and "device_manager" in v
        for v in hass.data.get(DOMAIN, {}).values()
    ):
        try:
            frontend.async_remove_panel(hass, PANEL_URL)
        except Exception:
            _LOGGER.debug("Panel %s already removed", PANEL_URL)
        hass.data[DOMAIN].pop("_panel_registered", None)

    # The emitter-platform cache is per entity id and outlives no entry:
    # a reload can repoint an emitter at a different integration, and a
    # stale "esphome" would bundle a burst at a blaster that cannot take
    # one (send_plan).
    from .send_plan import clear_platform_cache

    clear_platform_cache(hass)

    return True


async def async_remove_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove a HAIR config entry."""
    # Storage is shared across the integration's lifetime; we leave it
    # in place so re-installation preserves captured commands. Users
    # can clear it manually via the panel.


