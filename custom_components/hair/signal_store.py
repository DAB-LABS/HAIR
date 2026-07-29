"""Persistent storage for the HAIR unknown-signal catalog.

Separate from ``HAIRStore`` (which holds configured devices) so that
clearing unknown signals never touches user-configured devices, and
vice versa.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    SIGNAL_BUFFER_MAX_DEVICES,
    SIGNAL_EVICT_AGE_DAYS,
    SIGNAL_EVICT_MIN_HITS,
    SIGNAL_MAX_SIGNALS_PER_DEVICE,
    SIGNAL_MAX_TOTAL_SIGNALS,
    SIGNAL_SAVE_DEBOUNCE_S,
    SIGNAL_SAVE_MAX_DELAY_S,
    SIGNAL_STORAGE_KEY,
    SIGNAL_STORAGE_VERSION,
)
from .models import UnknownDevice, UnknownSignal

_LOGGER = logging.getLogger(__name__)

# Only sniffed signals are eviction-eligible. Manual (clipped) and plucked
# remotes are user creations, never captured noise, so they are never
# evicted. Keying eviction on a single "evictable" source future-proofs the
# guards against any new user-created source value.
_EVICTABLE = "sniffed"


class _SignalCatalogStore(Store):
    """``Store`` subclass so the migration hook actually runs (H3).

    Mirrors ``storage._HAIRDeviceStore``. The unknown-signal catalog does
    its schema evolution with an in-application backfill on load (stable
    ids, byte_hash, and the v0.4.0 decoded fields), not a storage-version
    bump, but the migration scaffold must be wired so a future
    ``SIGNAL_STORAGE_VERSION`` bump does not fail every install's load the
    way the composed plain ``Store`` would have.
    """

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        _LOGGER.info(
            "Migrating HAIR signal store from v%s.%s to v%s",
            old_major_version,
            old_minor_version,
            SIGNAL_STORAGE_VERSION,
        )
        return old_data


class SignalStore:
    """Manage persistent storage of the unknown-signal catalog."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = _SignalCatalogStore(
            hass,
            SIGNAL_STORAGE_VERSION,
            SIGNAL_STORAGE_KEY,
            atomic_writes=True,
        )
        self._devices: dict[str, UnknownDevice] = {}
        self._dismissed: set[str] = set()
        self._loaded = False
        self._dirty = False
        self._debounce_handle: asyncio.TimerHandle | None = None
        self._ceiling_handle: asyncio.TimerHandle | None = None
        self._first_dirty_time: float | None = None
        # Cap-hit warnings fire once per device per HA run (GH #72): a
        # flood trims on every capture, and a per-capture WARNING would
        # itself become the flood.
        self._cap_warned: set[str] = set()

    @property
    def loaded(self) -> bool:
        return self._loaded

    # -----------------------------------------------------------------
    # Load / Save
    # -----------------------------------------------------------------

    async def async_load(self) -> None:
        """Load data from storage. Safe to call multiple times.

        The payload transform (parse, backfills, duplicate heal, caps,
        order seed) runs in ONE executor job. It is pure CPU with no
        awaits, and run on the event loop it starved all of Home
        Assistant -- GH #72: a noise-flooded 104k-signal store froze HA
        for ~15 minutes on every boot, py-spy landing in the heal's
        pairwise scan. Off-loop, a pathological store can at worst delay
        HAIR's own setup while the rest of HA keeps serving.
        """
        raw = await self._store.async_load()
        if raw is None:
            self._devices = {}
            self._dismissed = set()
            self._loaded = True
            return

        devices, dismissed, dirty = await self._hass.async_add_executor_job(
            _transform_loaded, raw
        )
        self._devices = devices
        self._dismissed = dismissed
        if dirty:
            self._dirty = True
        self._loaded = True

    async def async_save(self) -> None:
        """Persist current state to disk immediately."""
        self._cancel_timers()
        self._dirty = False
        self._first_dirty_time = None
        await self._store.async_save(self._serialize())

    def schedule_save(self) -> None:
        """Schedule a debounced save.

        Resets the debounce timer on each call. A hard ceiling ensures
        that a busy environment cannot defer writes indefinitely.
        """
        self._dirty = True
        now = time.monotonic()

        # Track when the first unsaved change happened.
        if self._first_dirty_time is None:
            self._first_dirty_time = now

        # Cancel existing debounce timer.
        if self._debounce_handle is not None:
            self._debounce_handle.cancel()

        loop = self._hass.loop

        # Hard ceiling: force save if first dirty change was > max_delay ago.
        elapsed = now - self._first_dirty_time
        if elapsed >= SIGNAL_SAVE_MAX_DELAY_S:
            self._hass.async_create_task(self.async_save())
            return

        # Set debounce timer.
        self._debounce_handle = loop.call_later(
            SIGNAL_SAVE_DEBOUNCE_S,
            lambda: self._hass.async_create_task(self.async_save()),
        )

        # Set ceiling timer if not already set.
        if self._ceiling_handle is None:
            remaining = SIGNAL_SAVE_MAX_DELAY_S - elapsed
            self._ceiling_handle = loop.call_later(
                remaining,
                lambda: self._hass.async_create_task(self.async_save()),
            )

    def _cancel_timers(self) -> None:
        if self._debounce_handle is not None:
            self._debounce_handle.cancel()
            self._debounce_handle = None
        if self._ceiling_handle is not None:
            self._ceiling_handle.cancel()
            self._ceiling_handle = None

    def _serialize(self) -> dict[str, Any]:
        return {
            "devices": [d.to_dict() for d in self._devices.values()],
            "dismissed": list(self._dismissed),
        }

    # -----------------------------------------------------------------
    # Device access
    # -----------------------------------------------------------------

    def get_device(self, device_id: str) -> UnknownDevice | None:
        return self._devices.get(device_id)

    def get_device_by_fingerprint(
        self, fingerprint: str
    ) -> UnknownDevice | None:
        for device in self._devices.values():
            if device.fingerprint == fingerprint:
                return device
        return None

    def get_all_devices(self) -> list[UnknownDevice]:
        return list(self._devices.values())

    def add_device(self, device: UnknownDevice) -> None:
        """Register a newly-discovered unknown device.

        The device is placed at the top of its tab's list by giving it an
        ``order`` strictly below every existing device (min - 1), so a
        brand-new remote always surfaces on top until the user drags it
        into place. ``order`` is computed across all devices; because the
        Sniffer and Clipper each sort their own source-filtered slice, a
        single global minimum is enough to float a new remote to the top
        of whichever tab it belongs to. Reload reconstructs devices
        directly (not through this method), so stored order is preserved.
        """
        if self._devices:
            device.order = min(d.order for d in self._devices.values()) - 1
        else:
            device.order = 0
        self._devices[device.id] = device

    def reorder_devices(self, source: str, ordered_ids: list[str]) -> None:
        """Reorder the *visible* devices of one source to ``ordered_ids``.

        The drag UI shows a filtered slice of a source: the ``min_hits``
        noise filter hides low-hit remotes and dismissed remotes are hidden
        too, so ``ordered_ids`` legitimately omits same-source devices. Those
        hidden devices are left exactly where they sit in the overall order;
        only the submitted (visible) devices are rearranged, within the slots
        they already occupy. Devices of the other source are untouched.

        Rejects duplicates or an id that is not a current device of this
        source (a stale client). Renumbers the source 0..n.

        Raises :class:`ValueError` on a bad list and changes nothing.
        """
        if len(ordered_ids) != len(set(ordered_ids)):
            raise ValueError("Duplicate device ids in reorder list")
        same_source = sorted(
            (d for d in self._devices.values() if d.source == source),
            key=lambda d: d.order,
        )
        current = {d.id for d in same_source}
        unknown = set(ordered_ids) - current
        if unknown:
            raise ValueError(
                f"Reorder list has unknown devices: {sorted(unknown)}"
            )
        # Fill each visible slot (a device the drag UI showed) with the next
        # id from the requested order; leave hidden devices in their slots.
        requested = set(ordered_ids)
        req_iter = iter(ordered_ids)
        final_ids = [
            next(req_iter) if d.id in requested else d.id for d in same_source
        ]
        for index, device_id in enumerate(final_ids):
            self._devices[device_id].order = index

    def remove_device(self, device_id: str) -> bool:
        """Remove an unknown device from the catalog.

        Also discards the device's fingerprint from the persistent
        dismiss set so that ``_dismissed`` can never hold a fingerprint
        whose corresponding ``_devices`` entry has been removed. Without
        this guarantee, a sequence like dismiss -> assign-last-signal or
        dismiss -> delete-last-signal could leave an orphan fingerprint
        in ``_dismissed`` that silently drops every future signal from
        that physical remote at step 4 of the signal pipeline, with no
        UI affordance to recover. Fixed in v0.2.1 (GitHub issue #9).
        """
        device = self._devices.get(device_id)
        if device is None:
            return False
        self._dismissed.discard(device.fingerprint)
        del self._devices[device_id]
        return True

    @property
    def device_count(self) -> int:
        return len(self._devices)

    # -----------------------------------------------------------------
    # Dismiss list
    # -----------------------------------------------------------------

    def add_dismissed(self, fingerprint: str) -> None:
        """Add a fingerprint to the dismiss list (persisted, no cap)."""
        self._dismissed.add(fingerprint)

    def is_dismissed(self, fingerprint: str) -> bool:
        return fingerprint in self._dismissed

    def remove_dismissed(self, fingerprint: str) -> None:
        self._dismissed.discard(fingerprint)

    @property
    def dismissed_count(self) -> int:
        return len(self._dismissed)

    # -----------------------------------------------------------------
    # Eviction
    # -----------------------------------------------------------------

    def evict(self) -> int:
        """Apply eviction rules. Returns count of devices removed.

        Rules (applied in order):
        1. Age + low activity: >30 days old AND <5 hits -> remove.
        2. If still over buffer max: evict lowest hit_count, oldest
           last_seen first until under the limit.
        """
        removed = 0
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=SIGNAL_EVICT_AGE_DAYS)

        # Pass 1: age + low activity. Manual (clipped) and plucked remotes
        # are user creations, not captured noise -- never evict them.
        to_remove = []
        for device in self._devices.values():
            if device.dismissed or device.source != _EVICTABLE:
                continue
            try:
                last = datetime.fromisoformat(device.last_seen)
            except (ValueError, TypeError):
                continue
            if last < cutoff and device.hit_count < SIGNAL_EVICT_MIN_HITS:
                to_remove.append(device.id)

        for device_id in to_remove:
            del self._devices[device_id]
            removed += 1

        # Pass 2: if still over limit, evict lowest activity.
        # Also skip dismissed devices here so an orphan fingerprint can
        # never form via eviction. Without this guard, a dismissed
        # device with a low ``hit_count`` could be evicted while its
        # fingerprint remains in ``_dismissed``, silently dropping every
        # future signal from that physical remote (GitHub issue #9).
        # Matches the Pass 1 skip behavior.
        if len(self._devices) > SIGNAL_BUFFER_MAX_DEVICES:
            sorted_devices = sorted(
                (
                    d
                    for d in self._devices.values()
                    if not d.dismissed and d.source == _EVICTABLE
                ),
                key=lambda d: (d.hit_count, d.last_seen),
            )
            while (
                len(self._devices) > SIGNAL_BUFFER_MAX_DEVICES
                and sorted_devices
            ):
                victim = sorted_devices.pop(0)
                del self._devices[victim.id]
                removed += 1

        return removed

    def enforce_signal_caps(
        self,
        device: UnknownDevice | None = None,
        receiver_entity_id: str | None = None,
        spare: UnknownSignal | None = None,
    ) -> int:
        """Apply the GH #72 signal caps; return the eviction count.

        Two caps on sniffed signals, both capacity protection in the
        heard-means-shown sense (an evicted row resurrects the moment
        its button is genuinely pressed again): a per-device cap so one
        noisy source cannot dominate the store, and a global cap so the
        store stays bounded no matter how many sources misbehave.
        Clipped/plucked remotes are user creations and are never
        touched, same as ``evict()``.

        ``device`` is the remote that just captured (trimmed first,
        cheaply); ``spare`` protects the signal just inserted from
        being evicted out from under its caller (only reachable when
        every other row on the device is aliased); the receiver id
        makes the warning actionable. Warnings fire once per device
        per run via ``_cap_warned``.
        """
        removed = 0
        if device is not None and device.source == _EVICTABLE:
            removed = _trim_device_signals(
                device, SIGNAL_MAX_SIGNALS_PER_DEVICE, spare=spare
            )
            if removed and device.id not in self._cap_warned:
                self._cap_warned.add(device.id)
                _LOGGER.warning(
                    "Remote '%s' hit the %d-signal store cap%s; evicting "
                    "oldest signals as new ones arrive. This many distinct "
                    "signals from one source usually means a receiver is "
                    "capturing noise; consider dismissing the remote in "
                    "the Sniffer",
                    device.label or device.id,
                    SIGNAL_MAX_SIGNALS_PER_DEVICE,
                    (
                        f" (heard by {receiver_entity_id})"
                        if receiver_entity_id
                        else ""
                    ),
                )
        global_removed, noisiest = _enforce_global_cap(
            self._devices, spare=spare
        )
        if global_removed and "__global__" not in self._cap_warned:
            self._cap_warned.add("__global__")
            _LOGGER.warning(
                "Unknown-signal store hit the global %d-signal cap; "
                "evicted %d oldest signal(s), most from '%s'%s. A noisy "
                "receiver may be flooding the Sniffer",
                SIGNAL_MAX_TOTAL_SIGNALS,
                global_removed,
                noisiest or "?",
                (
                    f" (last heard by {receiver_entity_id})"
                    if receiver_entity_id
                    else ""
                ),
            )
        return removed + global_removed

    # -----------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------

    def clear_all(self, source: str | None = None) -> None:
        """Wipe the unknown catalog AND the dismiss list.

        ``source=None`` clears everything (the historical behavior).
        Passing ``"sniffed"`` or ``"manual"`` clears only devices of that
        source and discards just their fingerprints from the dismiss set,
        leaving the other source untouched. This lets each tab (Sniffer /
        Clips) clear its own world without touching the other's.

        Behavior changed in v0.2.1: prior versions kept the dismiss
        list across Clear All. That design choice contributed to silent
        accumulation of orphan dismissed fingerprints (GitHub issue #9)
        because the dismiss list was reachable only through devices that
        had been Clear All'd away. Clear All now matches the user mental
        model of "clear everything," and serves as a manual recovery
        route for users who hit the orphan bug before upgrading.
        """
        if source is None:
            self._devices.clear()
            self._dismissed.clear()
            return

        for device_id in [
            d.id for d in self._devices.values() if d.source == source
        ]:
            device = self._devices.pop(device_id)
            self._dismissed.discard(device.fingerprint)

    async def async_shutdown(self) -> None:
        """Flush pending writes and cancel timers."""
        self._cancel_timers()
        if self._dirty:
            await self.async_save()


# ---------------------------------------------------------------------------
# Load-time transform (GH #72: executor-side, pure CPU)
# ---------------------------------------------------------------------------
# Everything below operates on plain Python objects: no hass access, no
# awaits, no I/O. ``async_load`` runs ``_transform_loaded`` in a single
# executor job so a large store can never block the event loop, however
# it got large. Module functions (not methods) keep that contract
# visible at the call site.


def _transform_loaded(
    raw: dict[str, Any],
) -> tuple[dict[str, UnknownDevice], set[str], bool]:
    """Parse the stored payload and run every load-time backfill/heal.

    Returns ``(devices, dismissed, dirty)``; ``dirty`` is True when any
    step changed data that should persist. The steps and their order
    are unchanged from the pre-GH #72 inline body of ``async_load``,
    except the duplicate heal is O(n) (``_heal_device_signals``) and
    the new signal caps run after it.
    """
    dirty = False
    devices: dict[str, UnknownDevice] = {}
    for entry in raw.get("devices") or []:
        try:
            device = UnknownDevice.from_dict(entry)
            devices[device.id] = device
        except Exception as err:
            _LOGGER.warning("Skipping malformed unknown device: %s", err)

    dismissed = set(raw.get("dismissed") or [])

    # Self-heal: prune any fingerprint in ``dismissed`` that has no
    # matching device entry. Users upgrading from v0.2.0 or earlier may
    # have accumulated orphan fingerprints on disk via the GH #9 bug.
    # We clean them up at load time so the user auto-recovers on next
    # HA restart after upgrading to v0.2.1 without any manual
    # intervention.
    live_fingerprints = {d.fingerprint for d in devices.values()}
    orphans = dismissed - live_fingerprints
    if orphans:
        dismissed -= orphans
        dirty = True
        _LOGGER.warning(
            "Pruned %d orphan dismissed fingerprint(s) on load. "
            "This was a v0.2.0 issue (GitHub issue #9) fixed in "
            "v0.2.1; signals from previously-silent remotes should "
            "now appear in the Sniffer normally.",
            len(orphans),
        )

    # v0.3.4 migration: every signal needs a stable id and a byte_hash.
    # ``UnknownSignal.from_dict`` already assigns a fresh id when the
    # stored record has none; compute the byte_hash from the Pronto
    # code where it is missing. Mark the store dirty so the generated
    # ids and computed hashes persist (otherwise ids would regenerate
    # on every load). Runs BEFORE the duplicate cleanup below, which as
    # of v0.3.4 keys on the composite (fingerprint, byte_hash).
    from .event_parser import EventParser

    legacy_signals = any(
        not s.get("id") or s.get("byte_hash") is None
        for d in (raw.get("devices") or [])
        for s in (d.get("signals") or [])
    )
    for device in devices.values():
        for sig in device.signals:
            if sig.byte_hash is None and sig.code:
                sig.byte_hash = EventParser.pronto_byte_hash(sig.code)
    if legacy_signals:
        dirty = True

    # v0.4.0 backfill: decode stored catalog signals into their
    # decoded_* fields. For each signal with no decoded_fingerprint,
    # decode the stored raw timings (or timings derived from the
    # Pronto code) and populate the identity. Non-decodable signals are
    # left untouched. Idempotent across restarts.
    from .ir_command import ProntoCommand
    from .protocol_decode import try_decode_identity

    decoded_backfilled = 0
    for device in devices.values():
        for sig in device.signals:
            if sig.decoded_fingerprint:
                continue
            timings = sig.raw_timings
            if not timings and sig.code:
                try:
                    timings = ProntoCommand(sig.code).get_raw_timings()
                except (ValueError, IndexError):
                    timings = None
            identity = try_decode_identity(timings)
            if identity is None:
                continue
            sig.decoded_protocol = identity.protocol
            sig.decoded_address = identity.address
            sig.decoded_command = identity.command
            sig.decoded_fingerprint = identity.fingerprint
            sig.decoded_extras = (
                dict(identity.extras) if identity.extras else None
            )
            decoded_backfilled += 1
    if decoded_backfilled:
        dirty = True
        _LOGGER.info(
            "Backfilled decoded protocol identity on %d catalog signal(s)",
            decoded_backfilled,
        )

    # Duplicate-signal cleanup (v0.3.2; composite key as of v0.3.4;
    # tiered identity as of v0.5.8; O(n) as of GH #72). See
    # ``_heal_device_signals`` for the semantics.
    for device in devices.values():
        if _heal_device_signals(device):
            dirty = True

    # Signal caps (GH #72): trim an already-oversized store back to
    # bounds on the first load after upgrade, so a user sitting on a
    # noise-flooded store recovers without touching .storage by hand.
    if _enforce_caps_on_load(devices):
        dirty = True

    # One-time order backfill (v0.3.2). Pre-0.3.2 records have no
    # ``order`` field, so every device deserializes with order 0. On
    # first load after upgrade, seed the manual order from the old
    # hit_count-descending sort so a user's list does not visibly
    # reshuffle. After this the order is purely manual. Detect the
    # un-migrated state as "more than one device and all order 0".
    if len(devices) > 1 and all(d.order == 0 for d in devices.values()):
        ranked = sorted(
            devices.values(),
            key=lambda d: (-d.hit_count, d.first_seen),
        )
        for index, device in enumerate(ranked):
            device.order = index
        dirty = True

    return devices, dismissed, dirty


def _heal_device_signals(device: UnknownDevice) -> bool:
    """Collapse one remote's duplicate signals in a single O(n) pass.

    The Clipper's manual paste path historically had no guard, so a
    remote could hold two truly identical signals (the same Pronto
    pasted twice); and boundary protocols (Sony) minted
    flip-duplicates -- same byte_hash, DIFFERENT S/L fingerprint --
    under the pre-unified runtime dedup. Signals collapse under the
    tiered identity rule (decoded > byte_hash > S/L fingerprint),
    merging each duplicate's hit count into the first (older)
    occurrence and keeping that row's alias (adopting the duplicate's
    alias only when the kept row has none). Two signals that share an
    S/L fingerprint but differ at the byte level (Panasonic, TCL, Sony
    siblings) are distinct and are NOT collapsed.

    GH #72 rewrite: the old pass rescanned every kept row per signal
    (quadratic; 1.46e9 pair comparisons on the reporter's store) and
    built a SignalIdentity per pair. This pass keys dicts on the
    identity values instead and reproduces the old scan's outcome
    exactly. Per ``SignalIdentity.match_tier``, the highest tier BOTH
    sides carry decides, a decided-tier mismatch is final (no
    fallthrough), and a tier either side lacks is skipped; the old
    scan then kept the strongest-tier match, first (oldest) kept row
    winning within a tier. Hence:

    - Tier 1: every candidate shares the signal's decoded
      fingerprint, so the first kept row under that key in
      ``dec_first`` IS the old scan's answer.
    - Tier 2 applies only to pairs that do not BOTH carry decoded
      identity. When the incoming signal carries one, a kept row with
      any decoded fingerprint is unreachable at tier 2 (equal decoded
      matched at tier 1; different decoded is a final mismatch), so
      the eligible rows are exactly the byte_hash matches lacking
      decoded identity (``byte_nod``). When the signal lacks decoded
      identity, every byte_hash match is eligible (``byte_all``).
    - Tier 3 mirrors that logic against both stronger layers
      (``fp_all`` / ``fp_nod`` / ``fp_nob`` / ``fp_nodb``).

    Each dict stores only the FIRST kept row per key (setdefault):
    within a tier the first-inserted eligible row is the match, so
    later kept rows with the same key can never be the answer.
    """
    if len(device.signals) < 2:
        return False

    kept: list[UnknownSignal] = []
    dec_first: dict[str, UnknownSignal] = {}
    byte_all: dict[str, UnknownSignal] = {}
    byte_nod: dict[str, UnknownSignal] = {}  # rows lacking decoded
    fp_all: dict[str, UnknownSignal] = {}
    fp_nod: dict[str, UnknownSignal] = {}  # rows lacking decoded
    fp_nob: dict[str, UnknownSignal] = {}  # rows lacking byte_hash
    fp_nodb: dict[str, UnknownSignal] = {}  # rows lacking both

    for sig in device.signals:
        dec = sig.decoded_fingerprint
        bh = sig.byte_hash
        fp = sig.fingerprint

        best: UnknownSignal | None = None
        best_tier = 0
        if dec and (row := dec_first.get(dec)) is not None:
            best, best_tier = row, 1
        elif bh and (
            row := (byte_nod if dec else byte_all).get(bh)
        ) is not None:
            best, best_tier = row, 2
        elif fp:
            # Eligible rows must lack every stronger layer the signal
            # carries (see docstring); pick the matching dict.
            if dec and bh:
                fp_map = fp_nodb
            elif dec:
                fp_map = fp_nod
            elif bh:
                fp_map = fp_nob
            else:
                fp_map = fp_all
            if (row := fp_map.get(fp)) is not None:
                best, best_tier = row, 3

        if best is not None:
            best.hit_count += sig.hit_count
            if not best.alias and sig.alias:
                best.alias = sig.alias
            if sig.last_seen and (
                not best.last_seen or sig.last_seen > best.last_seen
            ):
                best.last_seen = sig.last_seen
            _LOGGER.debug(
                "Healed duplicate signal %s into %s on remote %s "
                "(matched at identity tier %d)",
                sig.id,
                best.id,
                device.label or device.id,
                best_tier,
            )
            continue

        kept.append(sig)
        if dec:
            dec_first.setdefault(dec, sig)
        if bh:
            byte_all.setdefault(bh, sig)
            if not dec:
                byte_nod.setdefault(bh, sig)
        if fp:
            fp_all.setdefault(fp, sig)
            if not dec:
                fp_nod.setdefault(fp, sig)
            if not bh:
                fp_nob.setdefault(fp, sig)
                if not dec:
                    fp_nodb.setdefault(fp, sig)

    if len(kept) != len(device.signals):
        device.signals = kept
        return True
    return False


# ---------------------------------------------------------------------------
# Signal caps (GH #72)
# ---------------------------------------------------------------------------


def _signal_evict_order(sig: UnknownSignal) -> tuple[bool, str, str]:
    """Sort key for cap eviction: least-worth-keeping first.

    Aliased rows are user touch; they are evicted only after every
    unnamed row is gone. Within each class the oldest ``last_seen``
    goes first (ISO-8601 UTC strings sort chronologically, matching the
    string sort ``evict()`` already relies on), tie-broken on
    ``first_seen``.
    """
    return (bool(sig.alias), sig.last_seen or "", sig.first_seen or "")


def _trim_device_signals(
    device: UnknownDevice,
    cap: int,
    spare: UnknownSignal | None = None,
) -> int:
    """Trim one device's signal list to ``cap`` rows; return count evicted.

    ``spare`` is never evicted (the row a live capture just inserted;
    without it, a device whose every other row is aliased would evict
    the brand-new capture out from under the caller).
    """
    excess = len(device.signals) - cap
    if excess <= 0:
        return 0
    candidates = sorted(
        (s for s in device.signals if s is not spare),
        key=_signal_evict_order,
    )
    victim_ids = {s.id for s in candidates[:excess]}
    if not victim_ids:
        return 0
    device.signals = [s for s in device.signals if s.id not in victim_ids]
    return len(victim_ids)


def _enforce_global_cap(
    devices: dict[str, UnknownDevice],
    spare: UnknownSignal | None = None,
) -> tuple[int, str | None]:
    """Enforce ``SIGNAL_MAX_TOTAL_SIGNALS`` across all sniffed devices.

    Water-filling: find the highest per-device level at which the total
    fits, then trim only the devices above it -- the noisiest devices
    pay, quiet remotes keep every row. Returns ``(evicted_count,
    noisiest_device_label)``.
    """
    sniffed = [d for d in devices.values() if d.source == _EVICTABLE]
    counts = [len(d.signals) for d in sniffed]
    if sum(counts) <= SIGNAL_MAX_TOTAL_SIGNALS:
        return 0, None
    lo, hi = 0, max(counts)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(min(n, mid) for n in counts) <= SIGNAL_MAX_TOTAL_SIGNALS:
            lo = mid
        else:
            hi = mid - 1
    evicted = 0
    noisiest: tuple[int, str | None] = (0, None)
    for d in sniffed:
        removed = _trim_device_signals(d, lo, spare=spare)
        if removed:
            evicted += removed
            if removed > noisiest[0]:
                noisiest = (removed, d.label or d.id)
    return evicted, noisiest[1]


def _enforce_caps_on_load(devices: dict[str, UnknownDevice]) -> bool:
    """One-shot cap pass at load; True when anything was evicted.

    Runs after the duplicate heal so merged rows do not count against
    the caps. A store that grew past the caps before this release (the
    GH #72 reporter carried 104k signals / 340MB) is trimmed back to
    bounds on its first post-upgrade boot; a single WARNING summarizes
    what happened and names the worst offender.
    """
    per_device = 0
    worst: tuple[int, str, int] | None = None
    for d in devices.values():
        if d.source != _EVICTABLE:
            continue
        before = len(d.signals)
        removed = _trim_device_signals(d, SIGNAL_MAX_SIGNALS_PER_DEVICE)
        if removed:
            per_device += removed
            if worst is None or removed > worst[0]:
                worst = (removed, d.label or d.id, before)
    global_removed, global_noisiest = _enforce_global_cap(devices)
    if not per_device and not global_removed:
        return False
    if worst is not None:
        noisiest_note = (
            f"; noisiest: '{worst[1]}' ({worst[2]} -> "
            f"{worst[2] - worst[0]} signals)"
        )
    elif global_noisiest is not None:
        noisiest_note = f"; noisiest: '{global_noisiest}'"
    else:
        noisiest_note = ""
    _LOGGER.warning(
        "Unknown-signal store exceeded its caps; evicted %d signal(s) at "
        "load (%d over the %d-per-device cap, %d over the %d global "
        "cap)%s. Oldest sniffed signals were removed; clipped and plucked "
        "remotes are untouched, and any evicted signal reappears when its "
        "button is pressed again",
        per_device + global_removed,
        per_device,
        SIGNAL_MAX_SIGNALS_PER_DEVICE,
        global_removed,
        SIGNAL_MAX_TOTAL_SIGNALS,
        noisiest_note,
    )
    return True
