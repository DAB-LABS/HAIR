"""The HAIR (Home Assistant IR Admin) integration."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .capture_orchestrator import CaptureOrchestrator
from .const import DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL
from .device_manager import DeviceManager
from .entity_factory import EntityFactory
from .signal_monitor import SignalMonitor
from .signal_store import SignalStore
from .storage import HAIRStore
from .websocket_api import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

_BUTTON_PLATFORM = getattr(Platform, "BUTTON", None)

PLATFORMS_LIST: list[Platform] = [
    p
    for p in [
        _BUTTON_PLATFORM,
        Platform.REMOTE,
        Platform.MEDIA_PLAYER,
        Platform.CLIMATE,
        Platform.FAN,
        Platform.LIGHT,
        Platform.SWITCH,
        Platform.COVER,
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

    entity_factory = EntityFactory(hass)
    orchestrator = CaptureOrchestrator(hass)
    device_manager = DeviceManager(hass, store, entity_factory, entry.entry_id)
    signal_monitor = SignalMonitor(hass, signal_store, store)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "signal_store": signal_store,
        "device_manager": device_manager,
        "orchestrator": orchestrator,
        "entity_factory": entity_factory,
        "signal_monitor": signal_monitor,
        "config_entry": entry,
    }

    async_register_websocket_commands(hass)

    await _async_register_panel(hass, entry)

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_LIST
    )

    await signal_monitor.async_start()

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
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

    # Compute content hash for cache busting.
    content_hash = ""
    try:
        if bundle_path.exists():
            raw = bundle_path.read_bytes()
            content_hash = hashlib.md5(raw).hexdigest()[:8]
    except (OSError, TypeError):
        content_hash = ""

    versioned_path = f"{PANEL_STATIC_PATH}?v={content_hash}" if content_hash else PANEL_STATIC_PATH

    if bundle_path.exists():
        try:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        PANEL_STATIC_PATH,
                        str(bundle_path),
                        cache_headers=False,
                    )
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

    if not any(
        isinstance(v, dict) and "device_manager" in v
        for v in hass.data.get(DOMAIN, {}).values()
    ):
        try:
            frontend.async_remove_panel(hass, PANEL_URL)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Panel %s already removed", PANEL_URL)
        hass.data[DOMAIN].pop("_panel_registered", None)

    return True


async def async_remove_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove a HAIR config entry."""
    # Storage is shared across the integration's lifetime; we leave it
    # in place so re-installation preserves captured commands. Users
    # can clear it manually via the panel.


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload entry on options change so updated values take effect."""
    await hass.config_entries.async_reload(entry.entry_id)
