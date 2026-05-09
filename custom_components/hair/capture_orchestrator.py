"""Capture session orchestration with resource locking."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant

from .capture import CaptureProvider
from .const import (
    DEFAULT_CAPTURE_TIMEOUT,
    EVENT_CAPTURE_ERROR,
    EVENT_CAPTURE_TIMEOUT,
    EVENT_COMMAND_CAPTURED,
    CaptureState,
)
from .models import CaptureResult, CaptureSession, IRCommand, IRDevice

_LOGGER = logging.getLogger(__name__)

ListenerCallback = Callable[[CaptureState, CaptureResult | None], Any]


class CaptureInProgressError(Exception):
    """Raised when a capture session is already active."""


class CaptureOrchestrator:
    """Manage IR capture sessions with resource locking and event streaming."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._lock = asyncio.Lock()
        self._active_session: CaptureSession | None = None
        self._active_provider: CaptureProvider | None = None
        self._task: asyncio.Task | None = None
        self._listeners: dict[str, list[ListenerCallback]] = {}
        self._results: dict[str, CaptureResult] = {}

    @property
    def is_capturing(self) -> bool:
        return self._lock.locked()

    @property
    def active_session(self) -> CaptureSession | None:
        return self._active_session

    def get_session_result(self, session_id: str) -> CaptureResult | None:
        return self._results.get(session_id)

    async def start_capture(
        self,
        provider: CaptureProvider,
        device_id: str,
        timeout: int = DEFAULT_CAPTURE_TIMEOUT,
    ) -> CaptureSession:
        """Start a new capture session."""
        if self._lock.locked():
            raise CaptureInProgressError(
                "Another capture session is already in progress"
            )

        if not provider.is_available():
            raise RuntimeError(
                f"Capture provider {provider.device_name} is not available"
            )

        await self._lock.acquire()

        try:
            session = CaptureSession(
                device_id=device_id,
                provider_type=provider.provider_type,
                state=CaptureState.IDLE,
            )
            self._active_session = session
            self._active_provider = provider

            await provider.async_start_capture(timeout)
            session.state = CaptureState.LISTENING
            self._notify(session.session_id, CaptureState.LISTENING, None)

            self._task = self._hass.async_create_task(
                self._capture_loop(session, provider, timeout)
            )
            return session
        except Exception:
            self._cleanup()
            self._lock.release()
            raise

    async def cancel_capture(self, session_id: str) -> None:
        """Cancel an active capture session."""
        if (
            self._active_session is None
            or self._active_session.session_id != session_id
        ):
            return
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    def subscribe(
        self,
        session_id: str,
        callback: ListenerCallback,
    ) -> Callable[[], None]:
        """Subscribe to capture events for a session."""
        self._listeners.setdefault(session_id, []).append(callback)

        def _unsubscribe() -> None:
            listeners = self._listeners.get(session_id)
            if listeners and callback in listeners:
                listeners.remove(callback)
            if listeners is not None and not listeners:
                self._listeners.pop(session_id, None)

        return _unsubscribe

    def _notify(
        self,
        session_id: str,
        state: CaptureState,
        result: CaptureResult | None,
    ) -> None:
        for callback in list(self._listeners.get(session_id, [])):
            try:
                callback(state, result)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Capture listener raised")

    async def _capture_loop(
        self,
        session: CaptureSession,
        provider: CaptureProvider,
        timeout: int,
    ) -> None:
        """Background task that drives a single capture session."""
        try:
            result = await provider.async_wait_for_signal()
        except asyncio.CancelledError:
            session.state = CaptureState.CANCELLED
            self._notify(session.session_id, CaptureState.CANCELLED, None)
            await self._safe_stop(provider)
            self._finalize()
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Capture provider raised")
            session.state = CaptureState.ERROR
            self._notify(session.session_id, CaptureState.ERROR, None)
            self._hass.bus.async_fire(
                EVENT_CAPTURE_ERROR,
                {"session_id": session.session_id, "error": str(err)},
            )
            await self._safe_stop(provider)
            self._finalize()
            return

        await self._safe_stop(provider)

        if result is None:
            session.state = CaptureState.TIMEOUT
            self._notify(session.session_id, CaptureState.TIMEOUT, None)
            self._hass.bus.async_fire(
                EVENT_CAPTURE_TIMEOUT,
                {"session_id": session.session_id},
            )
            self._finalize()
            return

        session.state = CaptureState.CAPTURED
        session.result = result
        self._results[session.session_id] = result
        self._notify(session.session_id, CaptureState.CAPTURED, result)
        self._hass.bus.async_fire(
            EVENT_COMMAND_CAPTURED,
            {
                "session_id": session.session_id,
                "device_id": session.device_id,
                "result": result.to_dict(),
            },
        )
        self._finalize()

    async def _safe_stop(self, provider: CaptureProvider) -> None:
        try:
            await provider.async_stop_capture()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Stopping capture provider raised")

    def _finalize(self) -> None:
        self._cleanup()
        if self._lock.locked():
            self._lock.release()

    def _cleanup(self) -> None:
        self._active_session = None
        self._active_provider = None
        self._task = None

    @staticmethod
    def check_duplicate(
        device: IRDevice,
        result: CaptureResult,
    ) -> IRCommand | None:
        """Return the existing command that matches ``result``, if any."""
        for command in device.commands:
            command_result = CaptureResult(
                protocol=command.protocol,
                code=command.code,
                raw_timings=list(command.raw_timings or []),
                frequency=command.frequency,
            )
            if result.matches(command_result):
                return command
        return None
