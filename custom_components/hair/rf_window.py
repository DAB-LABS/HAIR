"""Always-on radio receivers: the opt-in, HAIR's own Listen window, the counters.

A radio receiver whose state carries no ``capturing`` listens all the
time. On a fixed 433 MHz module that means thousands of noise captures
an hour with nobody pressing anything, and every real press in range:
the neighbours' keyfobs, weather stations, tyre sensors. HAIR does not
subscribe to such a receiver until the user opts it in; once opted in,
HAIR hears it all the time for the rows it already knows (triggers fire,
Remotes hear, existing Sniffer rows count up) and mints new cards only
while the user is listening.

THE SOFTWARE WINDOW. A capture device's window is the receiver's own:
HAIR toggles a switch and reads ``capturing`` from the receiver's state.
An always-on receiver has neither, so HAIR keeps the window itself. It
has the same three modes and the same fields as a hardware one
(``capturing``, ``window_ends_at``, ``capture_mode``, the meanings in
``docs/windowed-receivers.md``): ``sliding`` moves its end out by its
length at every code HAIR accepts from the receiver, ``multiple`` keeps
its end, ``single`` closes after the first accepted code. HAIR holds the
state, not HA, so the panel reads it from HAIR's doors and its push
(``hair/receivers/rf/subscribe``), never from ``hass.states``.

THE CEILING. Whatever the mode, the codes that slid it or a listen
holding it, a software window closes ``RF_WINDOW_MAX_S`` after it
opened (owner ruling 2026-11-05): a busy receiver hears strangers'
remotes, and an open window mints a card for each. From then on new
codes are dropped and counted until the user opens it again.

A LISTEN THAT HOLDS THE WINDOW. The code editor's and the Fix window's
Listen hear only what reaches the Sniffer, so for an always-on receiver
they open its software window for the length of the listen. A held
window does not slide or expire before the ceiling; closing it from the
panel, or the ceiling, ends that listen, as a hardware window closing
does in ``single`` mode.

COUNTERS, in memory since HAIR started hearing the receiver: every
capture, the captures with no frame in them, bursts that ended with too
few agreeing frames, rows minted, presses that reached a known row or a
trigger, and new codes dropped because the window was closed. Cheap
integers, pushed at most once a second, and the bench's record of a
noisy receiver being handled.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback

from .const import (
    RF_COUNTER_PUSH_INTERVAL_S,
    RF_SOFTWARE_WINDOW_MAX_S,
    RF_SOFTWARE_WINDOW_MIN_S,
    RF_SOFTWARE_WINDOW_MODE,
    RF_SOFTWARE_WINDOW_S,
    RF_WINDOW_MAX_S,
)

_LOGGER = logging.getLogger(__name__)

MODES = ("sliding", "single", "multiple")

NOT_ALWAYS_ON_CODE = "not_always_on"
NOT_OPTED_IN_CODE = "not_opted_in"
NOT_REGISTERED_CODE = "not_registered"
UNKNOWN_RECEIVER_CODE = "unknown_receiver"


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat(timespec="milliseconds") if moment is not None else None


@dataclass
class Counters:
    """One receiver's counters since HAIR started hearing it."""

    since: str = field(default_factory=lambda: _iso(datetime.now(UTC)) or "")
    captures: int = 0
    noise: int = 0
    bursts_failed: int = 0
    minted: int = 0
    matched: int = 0
    new_window_closed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class SoftwareWindow:
    """HAIR's Listen window for one always-on receiver.

    ``now`` and ``call_later`` are the event loop's in production and a
    test clock in the tests. ``on_change`` runs whenever the window
    opens, closes or moves its end.
    """

    def __init__(
        self,
        *,
        on_change: Callable[[], None],
        call_later: Callable[[float, Callable[[], None]], Any],
        wall_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._on_change = on_change
        self._call_later = call_later
        self._wall_now = wall_now
        self.mode: str | None = None
        self.seconds: int = RF_SOFTWARE_WINDOW_S
        self.ends_at: datetime | None = None
        # When the window opened: the ceiling counts from here, and an
        # open that restarts an open window does not reset it.
        self.opened_at: datetime | None = None
        self._timer: Any = None
        self._holds = 0
        self._on_closed: list[Callable[[], None]] = []

    @property
    def capturing(self) -> bool:
        return self.mode is not None

    @property
    def held(self) -> bool:
        return self._holds > 0

    def state(self) -> dict[str, Any]:
        return {
            "capturing": self.capturing,
            "window_ends_at": _iso(self.ends_at) if self.capturing else None,
            "capture_mode": self.mode,
        }

    def open(
        self,
        mode: str = RF_SOFTWARE_WINDOW_MODE,
        seconds: int = RF_SOFTWARE_WINDOW_S,
    ) -> None:
        """Open the window, or restart an open one with these settings."""
        if mode not in MODES:
            raise ValueError(f"unknown capture mode {mode!r}")
        if not self.capturing:
            self.opened_at = self._wall_now()
        self.mode = mode
        self.seconds = max(
            RF_SOFTWARE_WINDOW_MIN_S, min(RF_SOFTWARE_WINDOW_MAX_S, int(seconds))
        )
        self._restart_timer()
        self._on_change()

    def close(self) -> None:
        """Close the window. A listen holding it is told, and stops."""
        if not self.capturing:
            return
        self.mode = None
        self.ends_at = None
        self.opened_at = None
        self._cancel_timer()
        callbacks, self._on_closed = self._on_closed, []
        self._holds = 0
        self._on_change()
        for closed in callbacks:
            try:
                closed()
            except Exception:
                _LOGGER.exception("Error ending a listen on a closed radio window")

    def hold(self, on_closed: Callable[[], None]) -> None:
        """A listen keeps the window open until it releases it."""
        self._holds += 1
        self._on_closed.append(on_closed)
        if self.capturing:
            self._restart_timer()
            self._on_change()

    def release(self, on_closed: Callable[[], None]) -> None:
        if on_closed in self._on_closed:
            self._on_closed.remove(on_closed)
        self._holds = max(0, self._holds - 1)
        if self.capturing and not self._holds:
            self._restart_timer()
            self._on_change()

    def note_code(self) -> None:
        """HAIR accepted a code from this receiver while the window was open."""
        if not self.capturing:
            return
        if self.mode == "single" and not self.held:
            self.close()
        elif self.mode == "sliding" and not self.held:
            self._restart_timer()
            self._on_change()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _restart_timer(self) -> None:
        """Set the end: its length from now, never past the ceiling.

        A held window's end is the ceiling itself: the listen holding it
        ends it sooner, and nothing slides it.
        """
        self._cancel_timer()
        now = self._wall_now()
        ceiling = (self.opened_at or now) + timedelta(seconds=RF_WINDOW_MAX_S)
        wanted = ceiling if self.held else now + timedelta(seconds=self.seconds)
        self.ends_at = min(wanted, ceiling)
        delay = max(0.0, (self.ends_at - now).total_seconds())
        self._timer = self._call_later(delay, self._expire)

    def _expire(self) -> None:
        self._timer = None
        self.close()


class RfAlwaysOn:
    """Every opted-in always-on receiver HAIR is hearing: windows and counters.

    Owned by the signal monitor. The receiver tracker attaches a receiver
    when it subscribes to it as an always-on receiver and detaches it when
    it lets go; the signal monitor asks it whether a new code may mint and
    tells it what happened to each capture.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        wall_now: Callable[[], datetime] | None = None,
    ) -> None:
        self._hass = hass
        # The wall clock window ends are stated in; a test passes its own.
        self._wall_now = wall_now or (lambda: datetime.now(UTC))
        self._windows: dict[str, SoftwareWindow] = {}
        self._counters: dict[str, Counters] = {}
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []
        self._dirty: set[str] = set()
        self._push_handle: Any = None
        # Debug-only timing over the capture path, for the load number.
        self.time_ns: dict[str, int] = {}
        self._timed: dict[str, int] = {}
        self._timed_log: dict[str, int] = {}

    # -- membership -----------------------------------------------------

    def attached(self, receiver: str) -> bool:
        return receiver in self._windows

    @property
    def receivers(self) -> list[str]:
        return sorted(self._windows)

    @callback
    def attach(self, receiver: str) -> None:
        if receiver in self._windows:
            return
        self._windows[receiver] = SoftwareWindow(
            on_change=lambda r=receiver: self._window_changed(r),
            call_later=self._hass.loop.call_later,
            wall_now=self._wall_now,
        )
        self._counters[receiver] = Counters()
        self._push(receiver)

    @callback
    def detach(self, receiver: str) -> None:
        window = self._windows.pop(receiver, None)
        if window is None:
            return
        window.close()
        self._counters.pop(receiver, None)
        self.time_ns.pop(receiver, None)
        self._dirty.discard(receiver)
        self._send({
            "receiver_entity_id": receiver,
            "capturing": False,
            "window_ends_at": None,
            "capture_mode": None,
            "counters": None,
        })

    # -- windows ----------------------------------------------------------

    def window(self, receiver: str) -> SoftwareWindow | None:
        return self._windows.get(receiver)

    def window_open(self, receiver: str) -> bool:
        window = self._windows.get(receiver)
        return window is not None and window.capturing

    # -- counters ---------------------------------------------------------

    def counters(self, receiver: str) -> dict[str, Any] | None:
        counters = self._counters.get(receiver)
        return counters.as_dict() if counters is not None else None

    def count(self, receiver: str | None, name: str, amount: int = 1) -> None:
        counters = self._counters.get(receiver) if receiver else None
        if counters is None:
            return
        setattr(counters, name, getattr(counters, name) + amount)
        self._dirty.add(receiver)
        self._schedule_counter_push()

    def note_time(self, receiver: str, started_ns: int) -> None:
        """Add one capture's handling time, and once a minute say it.

        Debug only, and the bench's load number: microseconds per capture
        on the receive path (the split, the vote or the burst hand-off),
        summed per receiver. The shared pipeline's own cost after a vote
        is not in it; a vote happens a few times a minute, a capture
        several times a second.
        """
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return
        now_ns = time.perf_counter_ns()
        self.time_ns[receiver] = self.time_ns.get(receiver, 0) + now_ns - started_ns
        self._timed[receiver] = self._timed.get(receiver, 0) + 1
        last = self._timed_log.get(receiver)
        if last is None:
            self._timed_log[receiver] = now_ns
        elif now_ns - last >= 60_000_000_000:
            total, count = self.time_ns.pop(receiver), self._timed.pop(receiver)
            self._timed_log[receiver] = now_ns
            _LOGGER.debug(
                "Radio receive path on %s: %d captures in the last minute, "
                "%.0f us each, %.3f%% of one core",
                receiver, count, total / count / 1000, total / 60_000_000_000 * 100,
            )

    # -- the push ---------------------------------------------------------

    def snapshot(self) -> list[dict[str, Any]]:
        return [self._item(receiver) for receiver in self.receivers]

    def subscribe(self, fn: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        self._subscribers.append(fn)

        def _unsubscribe() -> None:
            if fn in self._subscribers:
                self._subscribers.remove(fn)

        return _unsubscribe

    def _item(self, receiver: str) -> dict[str, Any]:
        window = self._windows[receiver]
        return {
            "receiver_entity_id": receiver,
            **window.state(),
            "counters": self.counters(receiver),
        }

    def _send(self, item: dict[str, Any]) -> None:
        for fn in list(self._subscribers):
            try:
                fn(item)
            except Exception:
                _LOGGER.exception("Error pushing radio receiver state")

    def _push(self, receiver: str) -> None:
        if receiver in self._windows:
            self._dirty.discard(receiver)
            self._send(self._item(receiver))

    def _window_changed(self, receiver: str) -> None:
        self._push(receiver)

    def _schedule_counter_push(self) -> None:
        if self._push_handle is not None or not self._subscribers:
            return
        self._push_handle = self._hass.loop.call_later(
            RF_COUNTER_PUSH_INTERVAL_S, self._flush_counters
        )

    def _flush_counters(self) -> None:
        self._push_handle = None
        for receiver in sorted(self._dirty):
            self._push(receiver)
        self._dirty.clear()

    @callback
    def async_stop(self) -> None:
        if self._push_handle is not None:
            self._push_handle.cancel()
            self._push_handle = None
        for receiver in list(self._windows):
            window = self._windows.pop(receiver)
            window.close()
        self._counters.clear()
        self._subscribers.clear()


class SoftwareWindowArm:
    """The editor's and the Fix window's Listen on an always-on receiver.

    The same interface as ``receiver_window.ReceiverWindowArm``: start
    opens the window unless it is open and holds it for the listen; stop
    releases it and closes it only if this arm opened it. The window
    closing under the listen (the user closed it from the panel) ends the
    listen through ``on_window_closed``. A software window cannot fail to
    open, so ``on_failure`` is never called.
    """

    def __init__(
        self,
        window: SoftwareWindow,
        *,
        on_failure: Callable[[Exception], None],
        on_window_closed: Callable[[], None],
        reopen_after_code: bool = False,
    ) -> None:
        self._window = window
        self._on_window_closed = on_window_closed
        self._owned = False
        self._stopped = False

    @property
    def owns_window(self) -> bool:
        return self._owned

    async def async_start(self) -> None:
        if not self._window.capturing:
            self._window.open()
            self._owned = True
        self._window.hold(self._closed_under_us)

    def note_code(self) -> None:
        """The listen heard a code; a held window has nothing to move."""

    def _closed_under_us(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._owned = False
        self._on_window_closed()

    async def async_stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._window.release(self._closed_under_us)
        if self._owned:
            self._owned = False
            self._window.close()


def rf_always_on(hass: HomeAssistant) -> RfAlwaysOn | None:
    """The integration's always-on state, or None before setup."""
    from .const import DOMAIN

    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, dict):
            monitor = value.get("signal_monitor")
            always_on = getattr(monitor, "rf_always_on", None)
            if isinstance(always_on, RfAlwaysOn):
                return always_on
    return None
