"""Climate entity platform for HAIR (preset-based and matrix-based).

Two operating modes since Cold Cuts (v0.8.8), selected by
``IRDevice.climate_matrix``:

- PRESET mode (the original): discrete mapped commands (mode_cool,
  fan_low, temp_22...) from ``entity_config``. Untouched by Cold Cuts.
- MATRIX mode: the device carries a full climate state lattice in
  ``hair/matrices/<device_id>.matrix.json``; every user action resolves
  to ONE cell via ``wig_climate.resolve_cell`` and transmits that
  cell's complete-state Pronto. Vocabulary (fan/swing strings) is
  verbatim from the file -- the strings are lookup keys AND entity
  attribute values (addendum section 3).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DeviceType
from .models import IRDevice
from .wig_climate import (
    cell_display_name,
    ha_mode_for,
    resolve_cell,
    state_display_name,
)

if TYPE_CHECKING:
    from .wig_format import ClimateCell, ClimateMatrix

_LOGGER = logging.getLogger(__name__)

HVAC_MODE_TO_FEATURE: dict[HVACMode, str] = {
    HVACMode.COOL: "mode_cool",
    HVACMode.HEAT: "mode_heat",
    HVACMode.FAN_ONLY: "mode_fan_only",
    HVACMode.DRY: "mode_dry",
    HVACMode.AUTO: "mode_auto",
}

FAN_MODE_TO_FEATURE: dict[str, str] = {
    "low": "fan_low",
    "medium": "fan_medium",
    "high": "fan_high",
    "auto": "fan_auto",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_manager = data["device_manager"]
    factory = data["entity_factory"]

    entities: dict[str, HAIRClimateEntity] = {}

    @callback
    def _on_add(device: IRDevice) -> None:
        if device.device_type != DeviceType.AC:
            return
        if device.id in entities:
            return
        entity = HAIRClimateEntity(device, device_manager)
        entities[device.id] = entity
        async_add_entities([entity])

    @callback
    def _on_remove(device_id: str) -> None:
        entity = entities.pop(device_id, None)
        if entity is not None:
            hass.async_create_task(entity.async_remove())

    @callback
    def _on_update(device: IRDevice) -> None:
        entity = entities.get(device.id)
        if entity is not None:
            entity.update_device(device)

    factory.register_platform_hooks(
        "climate",
        on_add=_on_add,
        on_remove=_on_remove,
        on_update=_on_update,
    )
    factory.register_platform("climate", async_add_entities)

    for device in device_manager.get_all_devices():
        _on_add(device)


class HAIRClimateEntity(ClimateEntity):
    """IR-controlled climate device (preset-based or matrix-based)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, device: IRDevice, device_manager) -> None:
        self._device = device
        self._manager = device_manager
        self._attr_unique_id = f"hair_{device.id}_climate"
        self._attr_name = None
        self._hvac_mode = HVACMode.OFF
        self._target_temperature: float | None = None
        self._fan_mode: str | None = None
        # Matrix mode state (Cold Cuts). The matrix itself loads in
        # async_added_to_hass through the manager's cache (blocking
        # file I/O never runs in a constructor called on the loop).
        self._swing_mode: str | None = None
        self._matrix: ClimateMatrix | None = None
        # Display name of the last transmitted cell ("Off"/"On" for
        # the power codes): the device page's current-cell readout
        # (owner ruling Q2). Display grammar since the second half
        # (owner ruling 2026-07-29): the machine cell_key never
        # appears on a user surface. None until the first send.
        self._matrix_cell: str | None = None
        self._seed_target_temperature()

    @property
    def _matrix_mode(self) -> bool:
        return self._device.climate_matrix

    async def async_added_to_hass(self) -> None:
        # Real HA calls the base hook (a no-op) here; the matrix load
        # is this entity's only lifecycle need.
        if self._matrix_mode and self._matrix is None:
            await self._async_load_matrix()

    async def _async_load_matrix(self) -> None:
        self._matrix = await self._manager.async_get_matrix(self._device.id)
        if self._matrix is not None and self._target_temperature is None:
            # Seed the dial for the same reason presets seed (v0.6.1
            # bench find: no draggable target while None). Midpoint of
            # the file's bounds, snapped to its precision; local state
            # only, nothing transmits.
            m = self._matrix
            step = m.precision or 1.0
            mid = (m.min_temp + m.max_temp) / 2
            self._target_temperature = (
                m.min_temp + round((mid - m.min_temp) / step) * step
            )

    async def _async_refresh_matrix(self) -> None:
        await self._async_load_matrix()
        self.async_write_ha_state()

    @property
    def temperature_unit(self) -> str:
        """The installation's unit system, not a hardcoded scale.

        Presets are unit-agnostic integers (a "Temp 22" command is 22
        in whatever unit the user's HA runs), so the entity must
        declare the installation's unit. Hardcoding Fahrenheit made a
        metric user's 16..30C presets display as -9C to -3C (the
        third-party review's B3, surfaced for real by GH #45).
        """
        if self.hass is not None:
            return self.hass.config.units.temperature_unit
        return UnitOfTemperature.FAHRENHEIT

    def _seed_target_temperature(self) -> None:
        """Give the thermostat dial a handle to grab.

        The dial renders no draggable target while the target
        temperature is None, and nothing else can set the first
        target, so a preset-equipped entity would be stuck read-only
        (v0.6.1 bench find). Seed the median preset; purely local
        state, nothing transmits until the user actually drags.
        """
        if self._target_temperature is not None:
            return
        presets = self._device.entity_config.temperature_presets
        if presets:
            ordered = sorted(presets)
            self._target_temperature = float(ordered[len(ordered) // 2])

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": self._device.manufacturer or "HAIR",
            "model": self._device.model or "Air Conditioner",
        }

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = (
            ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        )
        if self._matrix_mode:
            m = self._matrix
            if m is not None:
                if m.fan_modes:
                    features |= ClimateEntityFeature.FAN_MODE
                if m.swing_modes:
                    features |= ClimateEntityFeature.SWING_MODE
                # Temperature is a per-branch dimension (census): only
                # a matrix with at least one temp-bearing cell can
                # honor a target, so only that matrix offers the dial.
                if any(c.temp is not None for c in m.cells):
                    features |= ClimateEntityFeature.TARGET_TEMPERATURE
            return features
        config = self._device.entity_config

        if config.fan_modes:
            features |= ClimateEntityFeature.FAN_MODE
        if config.temperature_presets:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        if self._matrix_mode:
            # OFF plus the file's declared modes through the alias map,
            # order preserved -- the file's order is the remote's order.
            modes: list[HVACMode] = [HVACMode.OFF]
            if self._matrix is not None:
                for raw in self._matrix.modes:
                    ha_value = ha_mode_for(raw)
                    if ha_value is None:
                        continue
                    try:
                        mode = HVACMode(ha_value)
                    except ValueError:
                        continue
                    if mode not in modes:
                        modes.append(mode)
            return modes
        modes = [HVACMode.OFF]
        configured = self._device.entity_config.hvac_modes or []
        for raw in configured:
            try:
                mode = HVACMode(raw)
            except ValueError:
                continue
            if mode not in modes:
                modes.append(mode)
        if len(modes) == 1:
            # GH #58: an AC with power mapped but no discrete mode
            # commands (the common remote that cycles modes on the unit)
            # otherwise offers OFF as its only state, leaving the climate
            # card with no way to turn the unit on. Advertise AUTO as the
            # synthetic on-state: async_set_hvac_mode already falls back
            # to turn_on/power_toggle for an unmapped mode, and
            # async_turn_on already wakes into AUTO.
            mapping = self._device.entity_config.command_mapping
            if "turn_on" in mapping or "power_toggle" in mapping:
                modes.append(HVACMode.AUTO)
        return modes

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def min_temp(self) -> float:
        if self._matrix_mode and self._matrix is not None:
            return float(self._matrix.min_temp)
        presets = self._device.entity_config.temperature_presets
        if presets:
            return float(min(presets))
        return 60.0

    @property
    def max_temp(self) -> float:
        if self._matrix_mode and self._matrix is not None:
            return float(self._matrix.max_temp)
        presets = self._device.entity_config.temperature_presets
        if presets:
            return float(max(presets))
        return 86.0

    @property
    def target_temperature_step(self) -> float | None:
        # Matrix files declare their own precision (0.5-degree remotes
        # exist in the census); preset mode keeps HA's default step, as
        # it always has (None = base behavior).
        if self._matrix_mode and self._matrix is not None:
            return float(self._matrix.precision)
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        if self._matrix_mode:
            if self._matrix is None:
                return None
            # Verbatim file vocabulary, never normalized: these strings
            # are the resolve_cell lookup keys (addendum section 3).
            return list(self._matrix.fan_modes) or None
        return list(self._device.entity_config.fan_modes or []) or None

    @property
    def fan_mode(self) -> str | None:
        return self._fan_mode

    @property
    def swing_modes(self) -> list[str] | None:
        # Swing exists only in matrix mode (no preset-mode device ever
        # had it); verbatim for the same lookup-key reason as fans.
        if self._matrix_mode and self._matrix is not None:
            return list(self._matrix.swing_modes) or None
        return None

    @property
    def swing_mode(self) -> str | None:
        return self._swing_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self._matrix_mode:
            return None
        # The device page's current-cell readout (owner ruling Q2):
        # which complete state the unit last received from HAIR.
        return {"matrix_cell": self._matrix_cell}

    # -- matrix mode actions (Cold Cuts) --------------------------------
    #
    # Shared shape: update the LOCAL state the user asked for, then
    # resolve the full target state to one cell and transmit it --
    # every matrix send is a complete state, so fan/swing/temp always
    # travel together. While OFF, setters store state without sending
    # (no surprise blasts; the stored state rides out on the next
    # mode/on action). A resolve miss logs and sends nothing: matrices
    # are SPARSE (census: 158 explicit nulls) and a missing state is
    # file fact, not an error to throw at the user.
    #
    # Matrix mode NEVER reads entity_config.command_mapping: every
    # send resolves from the matrix file, so the Map action is
    # meaningless on a matrix device and the frontend simply hides it
    # (Cold Cuts second half, 2026-07-29) -- no backend enforcement,
    # because a stale mapping is inert here by construction. The
    # documented door: if preset modes ever revive on matrix devices,
    # the mapping comes back through _send, not through these paths.

    def _file_mode_for(self, hvac_mode: HVACMode) -> str | None:
        """The file's verbatim mode key for an HA mode, or None.

        First declared mode whose alias maps to the requested HA value:
        the exact inverse of how hvac_modes was built, so anything the
        entity offered can be mapped back.
        """
        if self._matrix is None:
            return None
        for raw in self._matrix.modes:
            if ha_mode_for(raw) == str(hvac_mode):
                return raw
        return None

    async def _async_send_cell(self, cell: ClimateCell) -> None:
        # The display grammar names the send (owner ruling 2026-07-29,
        # mockup CC4): the Mirror row and the matrix_cell attribute
        # both read "cool / fan: auto / 22", never the compact
        # fittings key.
        name = cell_display_name(cell)
        await self._manager.async_send_matrix_cell(
            self._device.id, name, cell.pronto, cell.send_count
        )
        self._matrix_cell = name
        # Snap the dial to what actually went out: resolve_cell picks
        # the nearest available temperature, and displaying a target
        # the unit never received would be a quiet lie.
        if cell.temp is not None:
            self._target_temperature = cell.temp

    async def _async_resolve_and_send(self, hvac_mode: HVACMode) -> bool:
        if self._matrix is None:
            _LOGGER.warning(
                "Climate matrix for %s is not loaded; nothing sent",
                self._device.name,
            )
            return False
        file_mode = self._file_mode_for(hvac_mode)
        if file_mode is None:
            _LOGGER.warning(
                "No matrix mode on %s maps to %s; nothing sent",
                self._device.name, hvac_mode,
            )
            return False
        cell = resolve_cell(
            self._matrix, file_mode, self._fan_mode, self._swing_mode,
            self._target_temperature,
        )
        if cell is None:
            _LOGGER.warning(
                "Matrix for %s has no cell for mode %s; nothing sent",
                self._device.name, file_mode,
            )
            return False
        await self._async_send_cell(cell)
        return True

    async def _async_matrix_off(self) -> None:
        if self._matrix is None:
            _LOGGER.warning(
                "Climate matrix for %s is not loaded; nothing sent",
                self._device.name,
            )
        else:
            name = state_display_name("off")
            await self._manager.async_send_matrix_cell(
                self._device.id, name, self._matrix.off
            )
            self._matrix_cell = name
        self._hvac_mode = HVACMode.OFF
        self.async_write_ha_state()

    def _first_matrix_hvac_mode(self) -> HVACMode:
        """The on-state to display after a bare power-on.

        The file's first mode when one maps; AUTO otherwise (the same
        synthetic-on convention preset mode uses for GH #58).
        """
        modes = self.hvac_modes
        return modes[1] if len(modes) > 1 else HVACMode.AUTO

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if self._matrix_mode:
            if hvac_mode == HVACMode.OFF:
                await self._async_matrix_off()
                return
            await self._async_resolve_and_send(hvac_mode)
            # Assumed-state entity: the mode records the user's intent
            # even on a sparse miss (the attr shows what really went
            # out last).
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
            return
        if hvac_mode == HVACMode.OFF:
            await self._send("turn_off", "power_toggle")
            self._hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
            return

        feature = HVAC_MODE_TO_FEATURE.get(hvac_mode)
        if feature and await self._send(feature):
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
            return
        # Fall back to power-on if no mode-specific command was captured.
        if await self._send("turn_on", "power_toggle"):
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        raw_target = kwargs.get(ATTR_TEMPERATURE)
        if raw_target is None:
            return
        if self._matrix_mode:
            self._target_temperature = float(raw_target)
            if self._hvac_mode != HVACMode.OFF:
                # _async_send_cell snaps the dial to the transmitted
                # cell's temperature.
                await self._async_resolve_and_send(self._hvac_mode)
            self.async_write_ha_state()
            return
        # Bind a definitely-non-None float before the lambda below: mypy
        # does not carry the None-narrowing into a nested closure, so
        # ``target`` must already be a plain float where the lambda captures it.
        target = float(raw_target)
        presets = self._device.entity_config.temperature_presets or []
        if presets:
            snapped = min(presets, key=lambda t: abs(t - target))
            target = float(snapped)
            await self._send(f"temp_{int(snapped)}")
        self._target_temperature = target
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if self._matrix_mode:
            self._fan_mode = fan_mode
            if self._hvac_mode != HVACMode.OFF:
                await self._async_resolve_and_send(self._hvac_mode)
            self.async_write_ha_state()
            return
        feature = FAN_MODE_TO_FEATURE.get(fan_mode.lower())
        if feature and await self._send(feature):
            self._fan_mode = fan_mode
            self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        # Matrix mode only: preset mode never advertises SWING_MODE, so
        # HA never routes here for it.
        if not self._matrix_mode:
            return
        self._swing_mode = swing_mode
        if self._hvac_mode != HVACMode.OFF:
            await self._async_resolve_and_send(self._hvac_mode)
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        if self._matrix_mode:
            m = self._matrix
            if m is not None and m.on is not None:
                # A dedicated power-on code exists: send it and let the
                # unit resume its own last state.
                name = state_display_name("on")
                await self._manager.async_send_matrix_cell(
                    self._device.id, name, m.on
                )
                self._matrix_cell = name
                if self._hvac_mode == HVACMode.OFF:
                    self._hvac_mode = self._first_matrix_hvac_mode()
            else:
                # No bare on code (common in the census): waking the
                # unit IS selecting a state, so resolve in the first
                # mode.
                target = self._first_matrix_hvac_mode()
                await self._async_resolve_and_send(target)
                self._hvac_mode = target
            self.async_write_ha_state()
            return
        await self._send("turn_on", "power_toggle")
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_mode = HVACMode.AUTO
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        if self._matrix_mode:
            await self._async_matrix_off()
            return
        await self._send("turn_off", "power_toggle")
        self._hvac_mode = HVACMode.OFF
        self.async_write_ha_state()

    @callback
    def update_device(self, device: IRDevice) -> None:
        self._device = device
        # Presets can appear after entity creation (the assign path adds
        # "Temp N" commands to a live device); seed the dial then too.
        self._seed_target_temperature()
        if (
            device.climate_matrix
            and self._matrix is None
            and self.hass is not None
        ):
            # A device that just gained (or was created with) a matrix:
            # load it off-loop, then repaint. Loaded matrices are never
            # re-read here -- matrix files only change through manager
            # paths that recreate the device.
            self.hass.async_create_task(self._async_refresh_matrix())
        if self.hass is None:
            # Race: entity instantiated and tracked in the platform's local
            # dict but not yet registered with HA via async_add_entities.
            # The state from __init__ is correct; HA writes it once the
            # registration coroutine completes.
            return
        self.async_write_ha_state()

    async def _send(self, *feature_keys: str) -> bool:
        mapping = self._device.entity_config.command_mapping
        for key in feature_keys:
            command_name = mapping.get(key)
            if command_name is None:
                continue
            command = self._device.get_command_by_name(command_name)
            if command is not None:
                await self._manager.async_send_command(
                    self._device.id, command.id
                )
                return True
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
        return False
