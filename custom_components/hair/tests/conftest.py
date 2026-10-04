"""Test fixtures for the HAIR integration."""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure the infrared stub has async_send_command (root conftest may only
# set async_get_emitters).  All other HA stubs live in root conftest.py.
# ---------------------------------------------------------------------------
_INFRARED_MOD_NAME = "homeassistant.components.infrared"
_ir_mod = sys.modules.get(_INFRARED_MOD_NAME)
if _ir_mod is None:
    _ir_mod = types.ModuleType(_INFRARED_MOD_NAME)
    sys.modules[_INFRARED_MOD_NAME] = _ir_mod
if not hasattr(_ir_mod, "async_send_command"):
    _ir_mod.async_send_command = AsyncMock()  # type: ignore[attr-defined]

from custom_components.hair.capture import MockCaptureProvider  # noqa: E402
from custom_components.hair.const import (  # noqa: E402
    CaptureProviderType,
    CommandCategory,
    CommandSource,
    DeviceType,
)
from custom_components.hair.models import (  # noqa: E402
    CaptureResult,
    EntityConfig,
    IRCommand,
    IRDevice,
)


@pytest.fixture
def capture_result() -> CaptureResult:
    return CaptureResult(
        protocol="NEC",
        code="0x20DF10EF",
        raw_timings=[9000, -4500, 560, -560, 560, -1690, 560, -560],
        frequency=38000,
        confidence=0.95,
    )


@pytest.fixture
def mock_capture_provider(capture_result: CaptureResult) -> MockCaptureProvider:
    return MockCaptureProvider(result=capture_result, delay=0.01)


@pytest.fixture
def mock_command() -> IRCommand:
    return IRCommand(
        id="cmd-1",
        name="Power",
        category=CommandCategory.POWER,
        source=CommandSource.CAPTURED,
        protocol="NEC",
        code="0x20DF10EF",
        raw_timings=[9000, -4500, 560, -560],
        frequency=38000,
    )


@pytest.fixture
def mock_device(mock_command: IRCommand) -> IRDevice:
    return IRDevice(
        id="test-device-1",
        name="Test TV",
        device_type=DeviceType.MEDIA_PLAYER,
        manufacturer="Samsung",
        model="UN55TU7000",
        emitter_entity_ids=["infrared.test_emitter"],
        capture_device_id="esphome-device-1",
        capture_provider_type=CaptureProviderType.ESPHOME,
        commands=[mock_command],
        entity_config=EntityConfig(
            platform="media_player",
            command_mapping={"power_toggle": "Power"},
        ),
    )


@pytest.fixture
def fake_hass():
    """Minimal HA stub for unit tests that don't need a full instance.

    Replaces homeassistant.helpers.storage.Store interactions with
    in-memory storage so tests run quickly without a real config dir.
    """
    hass = MagicMock()
    hass.data = {}
    hass.config.components = set()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    hass.bus.async_fire = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=lambda: None)
    hass.services.async_call = AsyncMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    return hass


@pytest.fixture(autouse=True)
def _reset_tx_gate():
    """The transmit gate keeps module-level last-emitter state so it can
    stagger across independent send calls; reset it per test so one
    test's sends don't leak stagger sleeps into the next."""
    from custom_components.hair import tx_gate

    tx_gate.reset_for_test()
    yield
    tx_gate.reset_for_test()


# ---------------------------------------------------------------------------
# The real-air harness cannot be switched off in CI
# ---------------------------------------------------------------------------
# ``real_air`` is registered so a developer can deselect the harness
# locally (``-m 'not real_air'``). A run on GitHub Actions that dropped
# any of it has lost floors without failing anything, so it fails here
# instead, after every deselection has been applied: the harness tests
# are recorded before ``-k``, ``-m`` and ``--deselect`` act, and every
# one of them must still be selected.

_SUBSET_HINT = "; to run a subset on Actions, unset GITHUB_ACTIONS for that step"


def real_air_missing(items, environ=os.environ, collected=()) -> str | None:
    """Why this selection is not allowed to run, or None. ``collected``
    holds the node ids of the real_air tests collected before any
    deselection."""
    if environ.get("GITHUB_ACTIONS") != "true":
        return None
    if not any(item.get_closest_marker("real_air") for item in items):
        return (
            "this CI run selected no real_air test: the real-air harness "
            "is the only floor on read rates and must run in CI" + _SUBSET_HINT
        )
    dropped = sorted(set(collected) - {item.nodeid for item in items})
    if dropped:
        return (
            f"this CI run deselected {len(dropped)} of the "
            f"{len(set(collected))} real_air tests, {dropped[0]} among them: "
            "every floor must run in CI" + _SUBSET_HINT
        )
    return None


_REAL_AIR_COLLECTED: list[str] = []


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """The real_air tests as collected, before any deselection."""
    _REAL_AIR_COLLECTED[:] = [
        item.nodeid for item in items if item.get_closest_marker("real_air")
    ]


@pytest.hookimpl(tryfirst=True)
def pytest_collection_finish(session):
    why = real_air_missing(session.items, collected=_REAL_AIR_COLLECTED)
    if why is None:
        return
    if not hasattr(session.config, "workerinput"):
        raise pytest.UsageError(why)
    # Under pytest-xdist the controller collects nothing and every worker
    # collects the whole suite, so this check runs on the workers. A
    # UsageError raised here crashes the worker after xdist has sent its
    # collection: the run still fails, but as an INTERNALERROR naming an
    # unrelated test, and this message is lost. A failed collection
    # report is forwarded to the controller and printed there, and an
    # empty selection (cleared before xdist sends it, hence tryfirst)
    # means no worker runs anything.
    session.config.hook.pytest_collectreport(
        report=pytest.CollectReport(
            "real_air CI guard", "failed", longrepr=why, result=[]
        )
    )
    session.items.clear()
