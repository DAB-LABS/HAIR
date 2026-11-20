"""Grouped commands: other commands, from any device, in order.

A grouped command (``models.is_group``) is a command on a device whose
steps are other devices' commands, each followed by a delay
(grouped-signals.md). It is a command so that
everything a command already gets comes free: a name, Test, an action
mapping, a Home Assistant button, the remote entity's ``send_command``
and a pinned Remote.

EACH STEP IS AN ORDINARY SEND. A step goes through
``DeviceManager.async_send_command`` like any press: its own device's
blasters, its own Send times and spacing, its decode, its Mirror echo
ticket and its device's state. Nothing about sending is rewritten here.

THE DELAY COUNTS FROM THE END. The blasters accept a code before they
finish sending it, so the runner waits for the step's planned air time
to run out (``DeviceManager.air_left_s``) and then the delay. The floor
and the caps are in ``const.py`` (GROUP_*).

A FAILED STEP DOES NOT STOP THE RUN. HAIR carries on and the result
says which steps did not go out, the same way one dead blaster never
blocks the others. Only a run where nothing went out raises.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .const import (
    GROUP_DELAY_MAX_MS,
    GROUP_DELAY_MIN_MS,
    GROUP_MAX_STEPS,
    GROUP_RUN_MAX_MS,
)
from .models import GroupStep, IRCommand, IRDevice, is_group

if TYPE_CHECKING:
    from .device_manager import DeviceManager

_LOGGER = logging.getLogger(__name__)

# The runner's own wait, apart from the sleeps inside each send.
_sleep = asyncio.sleep

# Why a step did not go out.
STEP_MISSING = "missing"
STEP_GROUP = "group"
STEP_FAILED = "failed"


@dataclass
class StepFailure:
    index: int
    device_name: str
    command_name: str
    reason: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "device_name": self.device_name,
            "command_name": self.command_name,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass
class GroupResult:
    """What one run of a grouped command did."""

    total: int
    sent: int = 0
    failures: list[StepFailure] = field(default_factory=list)
    # A second press while the group was already running.
    skipped_busy: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "sent": self.sent,
            "failures": [f.to_dict() for f in self.failures],
            "busy": self.skipped_busy,
        }


class GroupRunError(RuntimeError):
    """Nothing in the group went out."""

    def __init__(self, message: str, result: GroupResult) -> None:
        super().__init__(message)
        self.result = result


def resolve_step(
    manager: DeviceManager, step: GroupStep
) -> tuple[IRDevice | None, IRCommand | None]:
    """The device and command a step points at, either None when gone."""
    device = manager.get_device(step.device_id)
    command = device.get_command(step.command_id) if device else None
    return device, command


async def async_run_group(
    manager: DeviceManager,
    device: IRDevice,
    group: IRCommand,
    *,
    pinned: bool = False,
    origin: str,
) -> GroupResult:
    """Send each step in order, waiting out each signal and its delay."""
    from .send_signal import ORIGIN_MANAGER

    steps = list(group.steps or ())
    result = GroupResult(total=len(steps))
    key = (device.id, group.id)
    if key in manager._groups_running:
        # A handset button held on a pinned Remote repeats; stacking
        # runs on top of each other would interleave their steps.
        _LOGGER.info("%s / %s is already running; press ignored",
                     device.name, group.name)
        result.skipped_busy = True
        return result
    manager._groups_running.add(key)
    try:
        last_device_id: str | None = None
        for index, step in enumerate(steps):
            if index and last_device_id is not None:
                previous = steps[index - 1]
                wait_s = manager.air_left_s(last_device_id) + (
                    clamp_delay(previous.delay_ms) / 1000
                )
                await _sleep(wait_s)
            step_device, command = resolve_step(manager, step)
            if step_device is None or command is None:
                result.failures.append(StepFailure(
                    index, step.device_name, step.command_name, STEP_MISSING,
                ))
                continue
            # Show what it is now, should it go missing later.
            step.device_name = step_device.name
            step.command_name = command.name
            if is_group(command):
                # No groups inside groups; the save door
                # refuses one, and this keeps a hand-edited file from
                # looping.
                result.failures.append(StepFailure(
                    index, step_device.name, command.name, STEP_GROUP,
                ))
                continue
            try:
                await manager.async_send_command(
                    step_device.id, command.id,
                    pinned=pinned,
                    # Every step moves its own device's state, whoever
                    # pressed the group.
                    origin=ORIGIN_MANAGER,
                    group_label=group.name,
                )
            except Exception as err:  # each step stands alone
                _LOGGER.warning(
                    "%s / %s: step %d (%s / %s) did not go out: %s",
                    device.name, group.name, index + 1,
                    step_device.name, command.name, err,
                )
                result.failures.append(StepFailure(
                    index, step_device.name, command.name, STEP_FAILED,
                    str(err) or type(err).__name__,
                ))
                continue
            result.sent += 1
            last_device_id = step_device.id
    finally:
        manager._groups_running.discard(key)

    if result.sent == 0 and result.total:
        raise GroupRunError(
            f"Nothing in {group.name} went out", result,
        )
    if result.sent:
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        from .send_signal import SIGNAL_DEVICE_SENT

        # The group's own device follows the group, as for any command:
        # a group mapped to Turn on turns its entity on.
        async_dispatcher_send(
            manager._hass, SIGNAL_DEVICE_SENT,
            manager._sent_for_command(device, group, origin),
        )
    return result


def clamp_delay(delay_ms: Any) -> int:
    """A stored delay inside the bounds; a hand-edited file can't go
    under the floor."""
    try:
        value = int(delay_ms)
    except (TypeError, ValueError):
        value = GROUP_DELAY_MIN_MS
    return max(GROUP_DELAY_MIN_MS, min(GROUP_DELAY_MAX_MS, value))


# --- What the save doors check -------------------------------------------

def step_air_ms(command: IRCommand) -> int:
    """About how long one step's signal is on the air, for the run time."""
    from .models import is_rf

    try:
        if is_rf(command):
            from .rf_send import burst_air_s

            timings = list(command.raw_timings or ())
            if not timings:
                return 0
            return round(burst_air_s(timings, max(1, command.send_count or 1)) * 1000)
        from .const import SEND_REPEAT_GAP
        from .ir_command import (
            TERMINATOR_SPACE_US,
            block_duration_us,
            build_command,
            carrier_or_default,
        )
        from .send_plan import realised_air_ms

        ir_cmd = build_command(
            protocol=command.protocol,
            code=command.code,
            raw_timings=command.raw_timings,
            frequency=carrier_or_default(command.frequency),
            repeat_count=command.repeat_count or 0,
        )
        count = max(1, command.send_count or 1)
        if command.send_spacing_ms is not None:
            return realised_air_ms(ir_cmd, count, command.send_spacing_ms)
        block_us = block_duration_us(ir_cmd.get_raw_timings())
        return round(
            count * (block_us + TERMINATOR_SPACE_US) / 1000
            + (count - 1) * SEND_REPEAT_GAP * 1000
        )
    except Exception:  # an estimate never refuses a save
        return 0


def run_ms(manager: DeviceManager, steps: list[GroupStep]) -> int:
    """Delays plus each step's air time: what the row shows and the cap
    checks. A missing step counts no air."""
    total = 0
    for index, step in enumerate(steps):
        _device, command = resolve_step(manager, step)
        if command is not None and not is_group(command):
            total += step_air_ms(command)
        if index < len(steps) - 1:
            total += clamp_delay(step.delay_ms)
    return total


def unsendable_reason(device: IRDevice, command: IRCommand) -> str | None:
    """Why a command can't be a step, or None.

    The picker greys these with the reason and the save door refuses
    them: another grouped command, a rolling code, a climate lattice
    cell (a porthole), and a command on a device with no blaster.
    """
    from .rf_send import rolling_row
    from .tangles import is_porthole

    if is_group(command):
        return "group"
    if rolling_row(command) is not None:
        return "rolling"
    if is_porthole(command):
        return "lattice"
    if not device.emitter_entity_ids:
        return "no_blaster"
    return None


class StepsRefused(ValueError):
    """A save the doors refuse, with a code the panel can word."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def check_steps(manager: DeviceManager, steps: list[GroupStep]) -> None:
    """Refuse steps a save must not keep. Raises ``StepsRefused``.

    A step whose command was deleted since is allowed to stay (it shows
    as missing); a NEW step must point at something sendable.
    """
    if len(steps) > GROUP_MAX_STEPS:
        raise StepsRefused(
            "too_many_steps", f"A group holds at most {GROUP_MAX_STEPS} steps",
        )
    for index, step in enumerate(steps):
        if index < len(steps) - 1 and not (
            GROUP_DELAY_MIN_MS <= int(step.delay_ms) <= GROUP_DELAY_MAX_MS
        ):
            raise StepsRefused(
                "bad_delay",
                f"A delay is {GROUP_DELAY_MIN_MS} ms to "
                f"{GROUP_DELAY_MAX_MS // 1000} s",
            )
        device, command = resolve_step(manager, step)
        if device is None or command is None:
            continue
        reason = unsendable_reason(device, command)
        if reason in ("group", "rolling", "lattice"):
            raise StepsRefused(
                f"step_{reason}", f"{command.name} can't be a step ({reason})",
            )
    if run_ms(manager, steps) > GROUP_RUN_MAX_MS:
        raise StepsRefused(
            "run_too_long",
            f"A group runs at most {GROUP_RUN_MAX_MS // 60000} minutes",
        )


def groups_using(
    manager: DeviceManager, device_id: str, command_id: str | None = None
) -> list[dict[str, str]]:
    """The grouped commands with a step on this command (or, with no
    command, on any of this device's commands), for the delete confirm."""
    out = []
    for device in manager.get_all_devices():
        for command in device.commands:
            if not is_group(command):
                continue
            if any(
                step.device_id == device_id
                and (command_id is None or step.command_id == command_id)
                for step in command.steps or ()
            ):
                if device.id == device_id and command_id is None:
                    # A device's own groups go with it.
                    continue
                out.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "command_id": command.id,
                    "command_name": command.name,
                })
    return out


# --- What the panel reads ---------------------------------------------------

def _row_tag(command: IRCommand) -> dict[str, Any]:
    """The chip or band a step shows, so IR and RF steps tell apart."""
    from .models import is_rf

    if is_rf(command):
        # The carrier, not a band string: the panel names the band the
        # way every other radio row does (sniffer-filter.radioBandOf).
        return {"medium": "rf", "rf_frequency_hz": command.rf_frequency_hz}
    return {
        "medium": "ir",
        "protocol": (
            command.decoded_protocol
            if command.decode_covers is not False else None
        ),
    }


def group_payload(manager: DeviceManager, group: IRCommand) -> dict[str, Any]:
    """A grouped command's steps as the row and its opened view show
    them: each step resolved, or marked missing with its last names."""
    steps_out = []
    devices: list[str] = []
    missing = 0
    for step in group.steps or ():
        device, command = resolve_step(manager, step)
        row: dict[str, Any] = {
            "device_id": step.device_id,
            "command_id": step.command_id,
            "delay_ms": step.delay_ms,
        }
        if device is None or command is None:
            missing += 1
            row.update(
                missing=True,
                device_name=step.device_name,
                command_name=step.command_name,
            )
        else:
            row.update(
                missing=False,
                device_name=device.name,
                command_name=command.name,
                **_row_tag(command),
            )
            if device.name not in devices:
                devices.append(device.name)
        steps_out.append(row)
    return {
        "steps": steps_out,
        "devices": devices,
        "missing": missing,
        "run_ms": run_ms(manager, list(group.steps or ())),
    }


def step_candidates(
    manager: DeviceManager, home_device_id: str
) -> list[dict[str, Any]]:
    """Every device and its commands, for the step picker.

    The group's own device first, the rest in the panel's order. Grouped
    commands are left out (no groups inside groups); a command that
    can't be a step stays in the list with its reason, so the picker can
    grey it and say why.
    """
    devices = manager.get_all_devices()
    devices.sort(key=lambda d: d.id != home_device_id)
    out = []
    for device in devices:
        commands = []
        for command in device.commands:
            if is_group(command):
                continue
            commands.append({
                "id": command.id,
                "name": command.name,
                "reason": unsendable_reason(device, command),
                **_row_tag(command),
            })
        out.append({
            "id": device.id,
            "name": device.name,
            "here": device.id == home_device_id,
            "blaster": bool(device.emitter_entity_ids),
            "commands": commands,
        })
    return out
