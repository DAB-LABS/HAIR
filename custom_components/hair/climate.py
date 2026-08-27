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

import contextlib
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DOMAIN, CommandSource, DeviceType
from .matrix_store import SIGNAL_MATRIX_CHANGED
from .models import IRDevice
from .power_monitor import SIGNAL_POWER_VERDICT, PowerVerdict
from .send_signal import (
    ORIGIN_ENTITY,
    SIGNAL_DEVICE_SENT,
    DeviceSent,
)
from .wig_climate import (
    cell_display_name,
    ha_mode_for,
    resolve_cell,
    state_display_name,
    unit_letter,
)
from .wig_format import cell_key

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


@dataclass
class _ClimateExtraStoredData(ExtraStoredData):
    """Reboot-survival payload for HAIRClimateEntity (098-final-review.md,
    "THE REQUIRED FIX: restore re-reads display-unit temperature as
    native").

    Home Assistant's state machine reports a climate entity's
    temperature attributes in the INSTALL's display unit, converting
    from whatever ``temperature_unit`` the entity itself declares --
    and matrix mode declares the FILE's native unit, which can differ
    from the install's display unit (see ``temperature_unit``'s
    docstring below). The old restore path read
    ``last_state.attributes[ATTR_TEMPERATURE]`` back as if it were
    already native, which silently applies one uncompensated
    display-unit conversion every restart: 23C -> 73.4 (as if F) ->
    164 -> 327 -> ... compounding without bound.

    This payload sidesteps the guesswork entirely: written and read
    only by this entity, always in the exact unit ``_target_temperature``
    already holds internally, so restore never has to infer which unit
    a bare number is in. See ``_restore_native_temperature`` for the
    one-time fallback path an entity takes on the first restart after
    this fix ships, before it has ever written this payload.
    """

    native_target_temperature: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, restored: dict[str, Any]) -> _ClimateExtraStoredData | None:
        try:
            raw = restored["native_target_temperature"]
        except KeyError:
            return None
        return cls(native_target_temperature=float(raw) if raw is not None else None)


class HAIRClimateEntity(RestoreEntity, ClimateEntity):
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
        self._matrix_changed_unsub = None
        # Display name of the last transmitted cell ("Off"/"On" for
        # the power codes): the device page's current-cell readout
        # (owner ruling Q2). Display grammar since the second half
        # (owner ruling 2026-07-29): the machine cell_key never
        # appears on a user surface. None until the first send.
        self._matrix_cell: str | None = None
        # Climate presets: the star (climate-presets-star.md). The
        # starred command last sent through async_set_preset_mode, or
        # None. Every other setter clears it (see the actions below) so
        # the attribute never claims a preset the unit has since moved
        # off.
        #
        # SUPERSEDED 2026-08-23. The original reasoning, kept because it
        # is the argument the new rule has to answer:
        #
        #   Deliberately NOT restored across restarts: this is an
        #   assumed-state entity, nothing tells us the unit is still in
        #   that state after a reboot, and None is the honest answer.
        #
        # That is sound in isolation and inconsistent in place. The
        # audit (state-restore-audit.md, section 2c) put it plainly:
        # the same argument applies verbatim to hvac_mode, temperature,
        # fan_mode and swing_mode, which this file HAS always restored.
        # HAIR was willing to say "this AC is in cool at 73 with the fan
        # high" on no evidence and unwilling to say "and that
        # combination is the preset you named" -- and on the audit's own
        # device the preset was a NAME for exactly that restored triple.
        # The card was already claiming the state and only declining to
        # name it.
        #
        # RULED (owner, 2026-08-23, GH #115): restore it, WITH A MATCH
        # CHECK. The preset comes back only when the restored
        # mode/fan/temp still resolve to that starred command's own
        # cell. Any miss leaves it None. That answers the honesty
        # concern on its own terms rather than by ignoring it: the
        # attribute can never claim a preset the restored state
        # contradicts, which is a stronger guarantee than never
        # claiming anything. See _async_restore_state.
        self._preset_mode: str | None = None
        # Power monitoring (Device Settings, 0.9.8). The mode this
        # entity was in the last time it went off (by any means -- a
        # HAIR send or a power-verdict correction), so a later "on"
        # verdict has something to restore instead of guessing AUTO.
        # None only until the entity has ever been on.
        self._last_active_hvac_mode: HVACMode | None = None
        self._power_verdict_unsub: CALLBACK_TYPE | None = None
        self._device_sent_unsub: CALLBACK_TYPE | None = None
        # Climate room sensors (Device Settings, climate-sensors.md,
        # riding 0.9.8). Display-only mirror of a configured
        # thermometer/hygrometer -- no verdicts, no thresholds, and
        # unlike power this never corrects assumed on/off state or
        # sends IR. None until a sensor is configured and has reported
        # at least one valid reading.
        self._current_temperature: float | None = None
        self._current_humidity: float | None = None
        self._sensor_unsub: CALLBACK_TYPE | None = None
        self._seed_target_temperature()

    @property
    def _matrix_mode(self) -> bool:
        return self._device.climate_matrix

    async def async_added_to_hass(self) -> None:
        # Real HA calls the base hook (a no-op) here; the matrix load
        # is this entity's only other lifecycle need.
        if self._matrix_mode and self._matrix is None:
            await self._async_load_matrix()
        await self._async_restore_state()
        self._power_verdict_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_POWER_VERDICT, self._handle_power_verdict
        )
        # The card follows what HAIR sends (0.10.1 item 7, GH #105).
        # Same shape as the power-verdict subscription right above, and
        # it layers UNDER it: a send is belief, the plug is evidence.
        self._device_sent_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_SENT, self._handle_device_sent
        )
        # A repair can rewrite one cell of a live device. Without this
        # the entity would keep transmitting the bytes it loaded at
        # startup, which are the broken ones.
        self._matrix_changed_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_MATRIX_CHANGED, self._handle_matrix_changed
        )
        self._subscribe_sensors()

    async def async_will_remove_from_hass(self) -> None:
        if self._power_verdict_unsub is not None:
            self._power_verdict_unsub()
            self._power_verdict_unsub = None
        if self._device_sent_unsub is not None:
            self._device_sent_unsub()
            self._device_sent_unsub = None
        if self._matrix_changed_unsub is not None:
            self._matrix_changed_unsub()
            self._matrix_changed_unsub = None
        self._unsubscribe_sensors()

    async def _async_restore_state(self) -> None:
        """Reboot survival (Device Settings, 0.9.8). Seeds mode,
        setpoint, fan, and swing from the entity's state before this
        restart. The power monitor's STARTUP SEED (power_monitor.py,
        commit 2) corrects the mode immediately after if a sensor is
        configured -- restore only has to get close, a configured
        sensor's evidence always wins.

        Matrix mode re-validates the restored combination against the
        CURRENT matrix via resolve_cell: the lattice may have changed
        since last run (a re-fit, a re-adopt), and a combination that
        no longer resolves is discarded wholesale rather than applied
        partially -- falls back to the blank state __init__ already
        set, not an error.
        """
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        try:
            restored_mode = HVACMode(last_state.state)
        except ValueError:
            return
        restored_temp = await self._restore_native_temperature(last_state)
        restored_fan = last_state.attributes.get(ATTR_FAN_MODE)
        restored_swing = last_state.attributes.get(ATTR_SWING_MODE)

        if self._matrix_mode:
            # 098-final-review.md's required fix: a sanity clamp on
            # top of the native-unit read above, so a value already
            # corrupted by the old bug (or any other bad number that
            # somehow made it into storage) self-heals to a real,
            # in-range setpoint on the next restart instead of
            # resurrecting forever. Cheap and safe either way --
            # resolve_cell below snaps to the nearest real cell
            # regardless, but it validates the COMBINATION, not the
            # raw value that gets written to _target_temperature.
            if restored_temp is not None and self._matrix is not None:
                restored_temp = min(
                    max(restored_temp, self._matrix.min_temp),
                    self._matrix.max_temp,
                )
            cell = None
            if restored_mode != HVACMode.OFF:
                file_mode = self._file_mode_for(restored_mode)
                cell = (
                    resolve_cell(
                        self._matrix, file_mode, restored_fan, restored_swing,
                        restored_temp,
                    )
                    if file_mode is not None and self._matrix is not None
                    else None
                )
                if cell is None:
                    return
            self._hvac_mode = restored_mode
            self._fan_mode = restored_fan
            self._swing_mode = restored_swing
            if restored_temp is not None:
                self._target_temperature = restored_temp
            if cell is not None:
                # matrix_cell, RE-DERIVED rather than read back
                # (restore completeness, 2026-08-23). It was never
                # scoped out; the readout simply postdates the 0.9.8
                # restore list (it arrived with 0.10.1 item 7 / GH
                # #105) and nobody added it when the feature landed, so
                # the device page's current-cell line went blank after
                # every restart.
                #
                # Re-derived from the cell the restored combination
                # just resolved to, rather than read from the stored
                # attribute, because re-derivation CANNOT disagree with
                # the restored values. A stored string could: the
                # lattice may have changed under it, or the display
                # unit may have (the name carries a converted
                # temperature), and then the readout would name a cell
                # the entity is not in. Same derivation the live
                # setters use, so the two doors cannot drift.
                self._matrix_cell = self._cell_display_name(cell)
                self._restore_preset(last_state, cell)
            else:
                # Restored OFF. The live async_turn_off writes exactly
                # this, so the readout agrees with itself whichever way
                # the entity got here. The preset stays None because
                # turning off clears it.
                self._matrix_cell = state_display_name("off")
        else:
            self._hvac_mode = restored_mode
            if restored_temp is not None:
                self._target_temperature = restored_temp
            if restored_fan is not None:
                self._fan_mode = restored_fan
        if restored_mode != HVACMode.OFF:
            self._last_active_hvac_mode = restored_mode

    async def _restore_native_temperature(self, last_state: State) -> float | None:
        """The restored target temperature, in THIS entity's native
        unit -- the one ``_target_temperature`` always holds (098-
        final-review.md's required fix).

        Prefers ``extra_restore_state_data``: this entity's own
        payload from before its last shutdown, already native, no
        unit inference needed. Falls back to
        ``last_state.attributes[ATTR_TEMPERATURE]`` -- converting it
        from the install's display unit for matrix-mode entities only,
        since matrix mode is the one case where the entity's native
        unit (the FILE's unit) can differ from the install's display
        unit (see ``temperature_unit``'s docstring). Preset mode's
        native unit already IS the install's display unit by design,
        so its fallback stays a straight, unconverted read, same as
        before this fix.

        The fallback only fires for an entity that has never written
        the extra-data payload yet -- the one restart right after this
        fix ships. Every restart after that reads its own number back
        untouched, forever.
        """
        extra = await self.async_get_last_extra_data()
        if extra is not None:
            restored = _ClimateExtraStoredData.from_dict(extra.as_dict())
            if restored is not None:
                return restored.native_target_temperature
        raw_temp = last_state.attributes.get(ATTR_TEMPERATURE)
        if raw_temp is None:
            return None
        value = float(raw_temp)
        if self._matrix_mode and self.hass is not None:
            display_unit = self.hass.config.units.temperature_unit
            native_unit = self.temperature_unit
            if display_unit and display_unit != native_unit:
                value = TemperatureConverter.convert(value, display_unit, native_unit)
        return value

    @property
    def extra_restore_state_data(self) -> _ClimateExtraStoredData:
        return _ClimateExtraStoredData(self._target_temperature)

    def _capture_active_mode(self) -> None:
        """Remember the mode about to be left, before flipping to OFF.

        Called at every transition to OFF -- a HAIR send or a power
        verdict -- so a later "on" verdict can restore last non-off
        mode/setpoint/fan/swing (the setpoint/fan/swing fields are
        never cleared on off, so remembering the mode is the only
        piece that would otherwise be lost).
        """
        if self._hvac_mode != HVACMode.OFF:
            self._last_active_hvac_mode = self._hvac_mode

    # -- the card follows what HAIR sends (0.10.1 item 7, GH #105) ------
    #
    # Until 0.10.1 only this entity's OWN services moved state, so the
    # STATE MATRIX card's SEND, a command row's SEND (including a saved
    # STATE row), a pinned Remote's retransmit and a HAIR button entity
    # all reached the air conditioner and left the thermostat card
    # where it was. mode0192 filed #105 about the preset half; the
    # owner's ruling in the same breath was the general one: ANY send
    # HAIR makes to a climate Device should move the card.
    #
    # SENT ONLY. A matrix Remote hearing the wall handset does not
    # touch the card unless it is PINNED, and then it is the pinned
    # SEND that does, arriving here like any other send.
    #
    # UNDER THE PLUG, NOT OVER IT. The 0.9.8 power monitor's rule is
    # unchanged: the sensor is evidence, assumed state is belief, so a
    # threshold crossing still overrides whatever was last sent. A HAIR
    # "on" the unit never received shows on for a moment and is
    # corrected back to OFF by the plug's next crossing.

    @callback
    def _handle_device_sent(self, sent: DeviceSent) -> None:
        """Follow a landed send from anywhere in HAIR."""
        if sent.device_id != self._device.id:
            return
        if sent.origin == ORIGIN_ENTITY:
            # This entity's own service call. Its setter has already
            # written the state it intended, with the exact cell in
            # hand; re-deriving it here would write state twice and let
            # the derived reading overwrite the exact one.
            return
        if self._apply_sent(sent):
            self.async_write_ha_state()

    def _hvac_for_file_mode(self, file_mode: str | None) -> HVACMode | None:
        """The HA mode for a file mode key: the inverse of _file_mode_for."""
        if not file_mode:
            return None
        ha_value = ha_mode_for(file_mode)
        if ha_value is None:
            return None
        try:
            return HVACMode(ha_value)
        except ValueError:
            return None

    def _reverse_command_mapping(self) -> dict[str, str]:
        """``{command name (casefolded): feature key}``.

        The inverse of ``entity_config.command_mapping``, built per call
        rather than cached: a mapping change arrives through
        update_device with no signal of its own, and the map is a
        handful of entries.
        """
        return {
            str(name).casefold(): key
            for key, name in self._device.entity_config.command_mapping.items()
            if name
        }

    def _apply_sent(self, sent: DeviceSent) -> bool:
        """Move local state to match a send. True when anything moved.

        Shared by the dispatcher handler and this entity's own preset
        path, so a preset and a card SEND of the same cell land on
        exactly the same state. The caller writes state; this only
        decides.
        """
        before = (
            self._hvac_mode, self._fan_mode, self._swing_mode,
            self._target_temperature, self._matrix_cell, self._preset_mode,
        )
        if self._matrix_mode:
            self._apply_sent_matrix(sent)
        else:
            self._apply_sent_flat(sent)
        # A starred send IS an HA preset selection; anything else clears
        # the attribute, exactly as every setter on this entity does, so
        # it never claims a preset the unit has since moved off.
        self._preset_mode = sent.command_name if sent.starred else None
        after = (
            self._hvac_mode, self._fan_mode, self._swing_mode,
            self._target_temperature, self._matrix_cell, self._preset_mode,
        )
        return before != after

    def _apply_sent_matrix(self, sent: DeviceSent) -> None:
        if sent.power == "off":
            self._capture_active_mode()
            self._hvac_mode = HVACMode.OFF
            self._matrix_cell = state_display_name("off")
            return
        if sent.power == "on":
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_mode = (
                    self._last_active_hvac_mode
                    or self._first_matrix_hvac_mode()
                )
            self._matrix_cell = state_display_name("on")
            return
        cell = sent.matrix_cell
        if not cell:
            # A send with no coordinates: an extras button riding along
            # on a matrix device. It may still be starred, which the
            # caller handles; it moves no dimension.
            return
        mode = self._hvac_for_file_mode(cell.get("mode"))
        if mode is not None:
            self._hvac_mode = mode
        if cell.get("fan") is not None:
            self._fan_mode = cell["fan"]
        if cell.get("swing") is not None:
            self._swing_mode = cell["swing"]
        if cell.get("temp") is not None:
            # The cell's temp is in the FILE's unit, which is the unit
            # this entity declares in matrix mode, so it is already
            # native and HA converts for the card (temperature_unit's
            # docstring). No conversion here would be one too many.
            self._target_temperature = float(cell["temp"])
        # The readout says what went out, in the same display grammar
        # the Mirror row carries, which is exactly the send's name.
        self._matrix_cell = sent.command_name

    def _apply_sent_flat(self, sent: DeviceSent) -> None:
        feature = self._reverse_command_mapping().get(
            sent.command_name.casefold()
        )
        if feature is None:
            # An unmapped command, starred or not, moves nothing. That
            # is mode0192's own suggestion for special-function presets
            # ("Sleep", "Turbo") and matches #105's skip-if-no-matrix-
            # correspondence line.
            return
        if feature == "turn_off":
            self._capture_active_mode()
            self._hvac_mode = HVACMode.OFF
            return
        if feature in ("turn_on", "power_toggle"):
            # Only ever an on-transition. A power_toggle sent while the
            # entity already reads on is genuinely ambiguous -- it could
            # be the unit going off -- and guessing would be worse than
            # holding, since the plug corrects a real off anyway.
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_mode = HVACMode.AUTO
            return
        for mode, key in HVAC_MODE_TO_FEATURE.items():
            if key == feature:
                self._hvac_mode = mode
                return
        for fan, key in FAN_MODE_TO_FEATURE.items():
            if key == feature:
                self._fan_mode = fan
                return
        if feature.startswith("temp_"):
            with contextlib.suppress(ValueError):
                self._target_temperature = float(feature[len("temp_"):])

    @callback
    def _handle_power_verdict(self, device_id: str, verdict: PowerVerdict) -> None:
        """Apply a power_monitor.py verdict to assumed state.

        Bookkeeping only -- NEVER sends IR. "off": the mode goes OFF,
        same as a HAIR-initiated off; setpoint/fan/swing are left
        untouched so they're there to come back to. "on" while
        currently off: restore the last non-off mode (setpoint/fan/
        swing need no restoring -- they were never cleared), falling
        back to the same synthetic first-mode/AUTO convention
        async_turn_on already uses for a device that has never been on.

        Two edits with 0.10.1 item 7, both because a send now sets more
        than the mode. An "off" verdict clears the preset and the cell
        readout: the unit is demonstrably no longer in that preset, and
        leaving either would keep a stale claim on the card next to an
        OFF state. An "on" verdict restores ``_last_active_hvac_mode``,
        which the send handler now refreshes by construction, so "the
        last mode" means the last one HAIR actually SENT rather than the
        last one a service call happened to set.
        """
        if device_id != self._device.id:
            return
        if verdict == "off":
            self._capture_active_mode()
            self._hvac_mode = HVACMode.OFF
            self._preset_mode = None
            if self._matrix_mode:
                self._matrix_cell = state_display_name("off")
        else:
            if self._hvac_mode == HVACMode.OFF:
                fallback = (
                    self._first_matrix_hvac_mode()
                    if self._matrix_mode else HVACMode.AUTO
                )
                self._hvac_mode = self._last_active_hvac_mode or fallback
        self.async_write_ha_state()

    # -- room sensors (climate-sensors.md) -------------------------------
    #
    # Entity-side and display only, mirroring power_monitor.py's
    # subscription mechanics (one async_track_state_change_event per
    # configured sensor, evaluated once immediately at subscribe time
    # as a startup seed, then again on every event) without any of its
    # verdict/threshold machinery -- there is nothing here to classify,
    # just a reading to mirror or drop.
    #
    # Resubscribe on settings change rides update_device(), the same
    # entity_factory on_update hook this class already uses to repaint
    # after any device-record change (DeviceManager.async_update_device
    # calls it on every settings save, not just power-field ones) --
    # no PowerMonitor-style central tracking needed, this hook is
    # already exactly that for a single entity.

    def _subscribe_sensors(self) -> None:
        temp_id = self._device.temperature_sensor_entity_id
        humidity_id = self._device.humidity_sensor_entity_id
        ids = [sensor_id for sensor_id in (temp_id, humidity_id) if sensor_id]
        if not ids:
            return

        @callback
        def _on_state_change(event: Event) -> None:
            # GH #91: announce the fresh reading, or the dashboard card
            # serves the last WRITTEN value until an unrelated update
            # (a command, a power verdict) happens to flush state. Only
            # on an actual change: a measurement sensor can re-report
            # the same number.
            if self._apply_sensor_reading(
                event.data.get("entity_id"), event.data.get("new_state")
            ):
                self.async_write_ha_state()

        self._sensor_unsub = async_track_state_change_event(
            self.hass, ids, _on_state_change
        )
        # Startup seed, same rule as the power monitor's: evaluate the
        # CURRENT reading now rather than waiting for the next event.
        seeded = False
        if temp_id:
            seeded = self._apply_sensor_reading(
                temp_id, self.hass.states.get(temp_id)
            )
        if humidity_id:
            seeded = (
                self._apply_sensor_reading(
                    humidity_id, self.hass.states.get(humidity_id)
                )
                or seeded
            )
        # GH #91, the same announce rule for the seed: a reboot or a
        # settings save should show the room immediately, not the last
        # value written before it. Both call paths (async_added_to_hass
        # and the update_device hook) only reach here with hass set.
        if seeded and self.hass is not None:
            self.async_write_ha_state()

    def _unsubscribe_sensors(self) -> None:
        if self._sensor_unsub is not None:
            self._sensor_unsub()
            self._sensor_unsub = None

    def _apply_sensor_reading(
        self, entity_id: str | None, state: State | None
    ) -> bool:
        """Mirror one reading; True when the stored value changed."""
        if entity_id == self._device.temperature_sensor_entity_id:
            value = self._read_temperature(state)
            changed = value != self._current_temperature
            self._current_temperature = value
            return changed
        if entity_id == self._device.humidity_sensor_entity_id:
            value = self._read_numeric(state)
            changed = value != self._current_humidity
            self._current_humidity = value
            return changed
        return False

    def _read_temperature(self, state: State | None) -> float | None:
        value = self._read_numeric(state)
        if value is None or state is None:
            return value
        sensor_unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        target_unit = self.temperature_unit
        if not sensor_unit or sensor_unit == target_unit:
            return value
        return TemperatureConverter.convert(value, sensor_unit, target_unit)

    @staticmethod
    def _read_numeric(state: State | None) -> float | None:
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

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

    @callback
    def _handle_matrix_changed(self, owner_id: str) -> None:
        """Re-read the lattice a repair just rewrote."""
        if owner_id != self._device.id or not self._matrix_mode:
            return
        if self.hass is not None:
            self.hass.async_create_task(self._async_refresh_matrix())

    async def _async_refresh_matrix(self) -> None:
        await self._async_load_matrix()
        self.async_write_ha_state()

    @property
    def temperature_unit(self) -> str:
        """Preset mode: the installation's unit. Matrix mode: the
        FILE's native unit. Mirror images, both correct.

        Presets are unit-agnostic integers (a "Temp 22" command is 22
        in whatever unit the user's HA runs), so the entity must
        declare the installation's unit. Hardcoding Fahrenheit made a
        metric user's 16..30C presets display as -9C to -3C (the
        third-party review's B3, surfaced for real by GH #45).

        Matrix temps are the exact opposite (owner ruling 2026-07-29):
        data-native file numbers, each one a real state the remote
        encodes. Declaring the matrix's own unit hands HA core the
        truth, and core then converts BOTH ways dynamically -- the
        thermostat card displays 16C as 61F on an imperial install,
        and a 61F set-temperature comes back to this entity as 16.1C
        for resolve_cell to snap. Declaring the install's unit here
        instead (the preset rule) would relabel 16C as 16F: the GH #45
        bug, mirrored.
        """
        if self._matrix_mode:
            m = self._matrix
            if m is not None and m.unit == "F":
                return UnitOfTemperature.FAHRENHEIT
            return UnitOfTemperature.CELSIUS
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
        # Climate presets: the star. Starred commands are the only
        # source of HA preset modes and they behave identically in
        # both operating modes, so the bit lands before the branches
        # split. Gated on the RESOLVED list rather than the raw
        # ``starred`` field: advertising PRESET_MODE with nothing to
        # select would put an empty picker on the more-info dialog.
        # The two agree in practice -- delete prunes the name -- so
        # this only ever differs on a store edited by hand.
        if self.preset_modes:
            features |= ClimateEntityFeature.PRESET_MODE
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
    def current_temperature(self) -> float | None:
        """The configured room sensor's last reading, converted to this
        entity's declared unit (climate-sensors.md). None with no
        sensor configured, or while its state is unavailable, unknown,
        or non-numeric -- the card drops the reading rather than
        holding a stale number.
        """
        return self._current_temperature

    @property
    def current_humidity(self) -> float | None:
        """The configured humidity sensor's last reading, a raw
        percentage passed through as-is (no unit conversion applies).
        Same None rules as current_temperature.
        """
        return self._current_humidity

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
    def preset_modes(self) -> list[str] | None:
        """The starred commands, in the device's own command order.

        Climate presets: the star (climate-presets-star.md). The
        stored ``starred`` list is in click order; what the picker
        shows is the row order of the device page, so a user reading
        the more-info dialog sees the same sequence they see on the
        command list. Filtered to commands that still exist -- the
        delete prune should keep the two in step, so this is a belt
        against a hand-edited store rather than a live case.

        None (not an empty list) when nothing is starred, so the
        picker is absent rather than empty.
        """
        starred = {
            name.casefold() for name in self._device.entity_config.starred
        }
        if not starred:
            return None
        names = [
            command.name
            for command in self._device.commands
            if command.name.casefold() in starred
        ]
        return names or None

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode

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
    #
    # Home Assistant PRESET MODES (climate-presets-star.md) are not
    # that door and do not reopen it: a starred command is sent by id
    # through async_send_command, never resolved through
    # command_mapping, so the Map door stays shut in both modes. Note
    # the vocabulary clash the plan calls out -- "preset mode" in this
    # file's own names means the flat mapped-commands operating mode,
    # which is a different thing from HA's preset_mode selector.

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

    def _cell_display_name(self, cell: ClimateCell) -> str:
        """This cell's readout name, in the install's display unit.

        The display grammar names the send (owner ruling 2026-07-29,
        mockup CC4): the Mirror row and the matrix_cell attribute both
        read "cool / fan: auto / 22", never the compact fittings key.
        The temperature part converts to the INSTALL's unit (unit
        ruling 2026-07-29: live surfaces convert dynamically), so a
        C-file cell on an imperial install reads
        "cool / fan: auto / 72".

        Factored out of ``_async_send_cell`` 2026-08-23 so restore can
        re-derive the readout through the same derivation the live
        setters use. Two doors, one answer; if this ever changes, it
        changes for both at once.
        """
        m = self._matrix
        display_unit = (
            unit_letter(self.hass.config.units.temperature_unit)
            if self.hass is not None else None
        )
        return cell_display_name(
            cell,
            unit=m.unit if m is not None else "C",
            display_unit=display_unit,
            precision=m.precision if m is not None else 1.0,
        )

    def _restore_preset(self, last_state: State, cell: ClimateCell) -> None:
        """Restore the starred preset, but only if it still fits.

        The ruled middle path (owner, 2026-08-23, GH #115; see the
        superseded reasoning in ``__init__``). The stored preset name
        comes back ONLY when the restored mode/fan/temp resolve to the
        same cell that starred command itself resolves to. Any miss --
        the name is not starred any more, the command was deleted, it
        carries no coordinates, or the lattice moved under it -- leaves
        the preset None and touches nothing else.

        That is what keeps the attribute from ever claiming a preset
        the restored state contradicts, which was the whole force of
        the original refusal.

        A STATE row carries its own coordinates on ``sent_state``
        (0.10.1 item 7). A row minted before that and never matched by
        the setup backfill has none, and there is no re-validating a
        preset whose cell cannot be named: the live setter treats such
        a row as readout-only and refuses to parse display grammar, and
        so does this. Refusing here costs a preset name after a
        restart; guessing would cost the guarantee above.
        """
        name = last_state.attributes.get(ATTR_PRESET_MODE)
        if not name or name not in (self.preset_modes or []):
            return
        command = self._device.get_command_by_name(name)
        if command is None:
            return
        state = command.sent_state or {}
        if not state:
            return
        starred_cell = resolve_cell(
            self._matrix,
            state.get("mode"),
            state.get("fan"),
            state.get("swing"),
            state.get("temp"),
        ) if self._matrix is not None else None
        if starred_cell is None or cell_key(starred_cell) != cell_key(cell):
            return
        self._preset_mode = name

    async def _async_send_cell(self, cell: ClimateCell) -> None:
        name = self._cell_display_name(cell)
        await self._manager.async_send_matrix_cell(
            self._device.id, name, cell.pronto, cell.send_count,
            # Own send: the dispatcher handler ignores origin "entity"
            # because the lines below already write the exact state
            # this cell IS, with the cell in hand (0.10.1 item 7).
            cell={
                "mode": cell.mode, "fan": cell.fan,
                "swing": cell.swing, "temp": cell.temp,
            },
            origin=ORIGIN_ENTITY,
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
                self._device.id, name, self._matrix.off,
                power="off", origin=ORIGIN_ENTITY,
            )
            self._matrix_cell = name
        self._capture_active_mode()
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
        self._preset_mode = None
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
            self._capture_active_mode()
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
        self._preset_mode = None
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
        self._preset_mode = None
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
        self._preset_mode = None
        self._swing_mode = swing_mode
        if self._hvac_mode != HVACMode.OFF:
            await self._async_resolve_and_send(self._hvac_mode)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Send the starred command named by ``preset_mode``.

        Climate presets: the star (climate-presets-star.md). One
        gesture, no vocabulary: the preset IS a command on this
        device, so the send is the ordinary command send -- on a
        matrix device the starred row is a real stored command
        carrying its cell's Pronto (``source == "matrix"``), so the
        same call covers both operating modes.

        A preset always transmits, including while the entity reads
        OFF: selecting a preset is an explicit "go there", unlike the
        matrix dial setters that store state and wait (plan section
        3.3).

        THE DIAL NOW FOLLOWS (0.10.1 item 7, GH #105). climate-presets-
        star.md 3.3's "leave the dial where it was" is REVERSED: a
        preset moves mode, fan, swing and temperature like any other
        send. What changed is not the appetite for parsing the display
        name -- that is still refused -- but that a STATE row now
        CARRIES its coordinates (``IRCommand.sent_state``), so the
        state can be read as data instead of guessed from grammar.
        A preset with no coordinates behind it still moves nothing but
        the attribute, which is mode0192's own suggestion for
        special-function presets.

        The state effect goes through the same ``_apply_sent`` the
        dispatcher handler uses, applied directly here because the
        dispatch this send raises is tagged origin "entity" and the
        handler ignores it. One derivation, two doors.
        """
        command = self._device.get_command_by_name(preset_mode)
        if command is None or preset_mode not in (self.preset_modes or []):
            _LOGGER.warning(
                "No starred command named %s on %s; nothing sent",
                preset_mode, self._device.name,
            )
            return
        await self._manager.async_send_command(
            self._device.id, command.id, origin=ORIGIN_ENTITY
        )
        state = command.sent_state or {}
        power = state.get("power")
        self._apply_sent(DeviceSent(
            device_id=self._device.id,
            command_id=command.id,
            command_name=command.name,
            matrix_cell=None if power else (dict(state) or None),
            power=power,
            starred=True,
            origin=ORIGIN_ENTITY,
        ))
        if (
            self._matrix_mode
            and command.source == CommandSource.MATRIX
            and not state
        ):
            # A STATE row minted before item 7 and never matched by the
            # setup backfill: no coordinates to move the dial with, but
            # its name IS its cell's display name (that is how
            # save-state-as-command mints it), so the readout can still
            # follow. Better than nothing, and exactly what 0.10.0 did.
            self._matrix_cell = command.name
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        self._preset_mode = None
        if self._matrix_mode:
            m = self._matrix
            if m is not None and m.on is not None:
                # A dedicated power-on code exists: send it and let the
                # unit resume its own last state.
                name = state_display_name("on")
                await self._manager.async_send_matrix_cell(
                    self._device.id, name, m.on,
                    power="on", origin=ORIGIN_ENTITY,
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
        self._preset_mode = None
        if self._matrix_mode:
            await self._async_matrix_off()
            return
        await self._send("turn_off", "power_toggle")
        self._capture_active_mode()
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
        # Room sensors: a save can add, change, or clear either one, so
        # re-derive the subscription unconditionally rather than diffing
        # old vs. new ids -- the same unconditional teardown+resubscribe
        # shape PowerMonitor.rebuild_device uses for the identical reason.
        self._unsubscribe_sensors()
        self._subscribe_sensors()
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
                    self._device.id, command.id, origin=ORIGIN_ENTITY
                )
                return True
        _LOGGER.warning(
            "No mapped IR command on %s for features %s",
            self._device.name,
            feature_keys,
        )
        return False
