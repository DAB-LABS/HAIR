"""When a store stops saving, say so once (0.10.1 item 1).

WHAT HAPPENED. One capture decoded to a ``decoded_command`` of about
1.5e23. Home Assistant's store writer refuses an integer that size, so
EVERY Sniffer store save failed for eighty minutes on the bench box
(17:14 to 18:35 UTC) until the 200-signal cap evicted the offending row
and saves resumed on their own. Nothing in HAIR's log or UI said a word;
only HA core logged the failed writes. A user in that state is making
captures that are silently not being kept, and has no way to know.

The half that stops it happening lives in ``protocol_decode``: a decoded
field that cannot be stored is refused at decode time and the signal is
kept undecoded, with the raw timings which are authoritative anyway.
This module is the half that makes ANY future cause visible, whatever it
turns out to be: a full disk, a permission change, a value nobody has
thought of yet.

ONE WARNING, ONE NOTIFICATION, NOT ONE PER WRITE. The Sniffer saves on a
debounce and a busy remote can drive many writes a minute; a per-write
warning would bury the log it is meant to make readable and stack
notifications the user has to dismiss one by one. So the first failure
speaks and the rest are counted silently, and the next good save clears
the notice and says so at INFO.

WHY A TRY/EXCEPT IS NOT ENOUGH, found on the bench 2026-08-19. Home
Assistant's ``Store._async_handle_write_data`` CATCHES
``SerializationError`` and ``WriteError`` and logs them at ERROR rather
than re-raising:

    try:
        await self._async_write_data(data)
    except (json_util.SerializationError, WriteError) as err:
        _LOGGER.error("Error writing config for %s: %s", self.key, err)

So the exact failure class this ticket exists for never reaches the
caller's ``await``, and a plain try/except around the save would have
shipped looking correct and caught nothing. That is also the real answer
to "why was it invisible": HAIR had nothing to catch. The only place the
truth exists is that log record, so this module listens for it, keyed on
the store's own key, which HA passes as the record's first argument. The
try/except stays as well, for the failures that DO propagate (a
serializer raising something else, a bug in a store's own payload
builder).

Notifications must never break a save, so every call here swallows its
own errors, the same rule the emitter-degrade notices follow.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Where HA reports a refused write, and the message it reports it with.
# Both are matched before a record is believed, so an unrelated ERROR on
# that logger cannot raise a false alarm.
_HA_STORAGE_LOGGER = "homeassistant.helpers.storage"
_WRITE_ERROR_TEXT = "Error writing config for"


class _WriteErrorWatcher(logging.Handler):
    """Hears HA's own report that a store write failed.

    One handler for the process, holding a registry of store key to
    health, installed on HA's storage logger the first time a store
    asks to be watched. Deliberately cheap and total: it never
    formats the record, and any error inside it is swallowed, because
    a logging handler that raises would break logging itself.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self._by_key: dict[str, StoreHealth] = {}

    def watch(self, key: str, health: StoreHealth) -> None:
        self._by_key[key] = health

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.name != _HA_STORAGE_LOGGER:
                return
            if _WRITE_ERROR_TEXT not in str(record.msg):
                return
            args = record.args or ()
            if not isinstance(args, tuple) or not args:
                return
            health = self._by_key.get(str(args[0]))
            if health is None:
                return
            health.note_logged_failure(
                args[1] if len(args) > 1 else "see the Home Assistant log"
            )
        except Exception:  # pragma: no cover - a handler must never raise
            pass


_WATCHER: _WriteErrorWatcher | None = None


def _watch(key: str, health: StoreHealth) -> None:
    global _WATCHER

    try:
        if _WATCHER is None:
            _WATCHER = _WriteErrorWatcher()
            logging.getLogger(_HA_STORAGE_LOGGER).addHandler(_WATCHER)
        _WATCHER.watch(key, health)
    except Exception:  # pragma: no cover - never break setup over this
        _LOGGER.debug("Could not watch store writes for %s", key, exc_info=True)


class StoreHealth:
    """One store's save-failure state. Held by the store, not global.

    ``label`` is the user-facing name of what stopped saving ("Sniffer
    catalog", "device catalog"), and also what makes the notification id
    unique so two stores in trouble raise two notices rather than
    overwriting each other.
    """

    def __init__(
        self, hass: Any, key: str, label: str, storage_key: str | None = None
    ) -> None:
        self._hass = hass
        self._key = key
        self._label = label
        self._failed = False
        # Failures since the warning. Reported once, when it clears, so
        # the log says how long it went on without a line per write.
        self._since = 0
        # Errors HA logged rather than raised, counted so a caller can
        # ask "did one happen during MY await" without a lock.
        self._logged = 0
        self._last_logged: Any = None
        if storage_key:
            _watch(storage_key, self)

    @property
    def notification_id(self) -> str:
        return f"hair_store_save_failed_{self._key}"

    @property
    def failing(self) -> bool:
        return self._failed

    def note_logged_failure(self, err: Any) -> None:
        """HA logged a refused write for this store instead of raising."""
        self._logged += 1
        self._last_logged = err

    async def guarded_save(
        self, write: Callable[[], Awaitable[None]]
    ) -> None:
        """Run one save and report whether it actually happened.

        Two ways a save can fail and only one of them is an exception.
        The count of HA-logged errors is sampled either side of the
        await, so a failure it swallowed is still seen; anything that
        does propagate is caught here as well. A save is called good
        only when neither happened.
        """
        before = self._logged
        try:
            await write()
        except Exception as err:  # HA writer raises several types
            self.note_failure(err)
            return
        if self._logged > before:
            self.note_failure(self._last_logged)
            return
        self.note_success()

    def note_failure(self, err: Any) -> None:
        """Record a failed save. Speaks only on the first one."""
        self._since += 1
        if self._failed:
            return
        self._failed = True
        _LOGGER.warning(
            "HAIR could not save the %s store: %s; new changes are not "
            "being kept until this clears",
            self._label, err,
        )
        self._notify(
            f"HAIR could not save the {self._label}; new captures are "
            "not being kept until this clears. Check the Home Assistant "
            "log for the underlying error. This notice clears itself "
            "when saving works again.",
        )

    def note_success(self) -> None:
        """Record a good save. Clears the notice if one is up."""
        if not self._failed:
            return
        count = self._since
        self._failed = False
        self._since = 0
        self._dismiss()
        _LOGGER.info(
            "HAIR %s store is saving again after %d failed save(s)",
            self._label, count,
        )

    def _notify(self, message: str) -> None:
        try:
            from homeassistant.components import persistent_notification

            persistent_notification.async_create(
                self._hass,
                message,
                title="HAIR: store not saving",
                notification_id=self.notification_id,
            )
        except Exception:  # pragma: no cover - never break a save
            _LOGGER.debug(
                "Could not raise the store-save notification", exc_info=True
            )

    def _dismiss(self) -> None:
        try:
            from homeassistant.components import persistent_notification

            persistent_notification.async_dismiss(
                self._hass, self.notification_id
            )
        except Exception:  # pragma: no cover - never break a save
            pass
