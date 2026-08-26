"""The hear side of a climate matrix (signpost 4, Track M).

A Remote minted from a matrix wig (or through either mirror door)
carries a COPY of the lattice, keyed by its own id in the same
``hair/matrices/`` folder the device side uses. The device's matrix is
the one it SENDS from; the remote's is the one it HEARS on. This module
owns the remote side of that file: reading it, holding it, matching
captured frames against its cells, and recording what was heard.

WHY THIS IS NOT A TRIGGER LOOKUP. A lattice is thousands of states, and
the lattice never auto-mints rows (the matrix rule) -- so cells cannot
live in ``IRTrigger`` or in ``get_triggers_for_signal`` without turning
a linear scan over a handful of triggers into a scan over thousands of
cells on every capture. Instead each matrix remote gets its own reverse
index, built once from its file and consulted right after the trigger
match, under the same not-echo gate. A cell that a user deliberately
promotes to a trigger is a plain trigger from that moment and matches
through the ordinary path; this listener stays the always-on reading of
the whole lattice.

IDENTITY TIERS, the one that is deliberately missing, and the one added
last. Cells are indexed by decoded fingerprint, by ``(S/L fingerprint,
byte_hash)``, and by ``byte_hash`` alone -- the order
``HAIRStore.match_command`` and ``pin_bindings`` already use. The
bare-fingerprint tier is NOT built here at all. AC frames are long state
blobs whose S/L patterns are near neighbours across a whole branch, so a
fingerprint-only match would report the wrong cell -- and reporting the
wrong state is worse than reporting none, because a wrong state is a
plausible lie the card would show with full confidence.

Beneath those sits the receiver-tolerant tier (2026-08-18), because the
byte hash does not survive a real air path for a lattice code: twenty
presses of one Mitsubishi cell through a microsecond-accurate
transmitter gave twenty byte hashes, none of them the file's. A cell is
always file-sourced, so every cell is indexed there; the gates are that
the CAPTURE must have decoded as nothing, and that a normalized value
two genuinely different cells claim is dropped rather than answered.
identity.py's normalized-fingerprint block carries the measurement.

THE INDEX BUILDS IN THE BACKGROUND, ONCE. Deriving identity per cell
runs the same decode the Sniffer runs: measured on the bench,
3.7 ms/cell on a Mitsubishi lattice and 0.8 ms/cell on a Gree one (the
cost tracks frame length, not cell count), so the census worst case of
2,689 cells is seconds of work. The build is dispatched as a task and
the frames that arrive meanwhile simply do not match (logged once per
remote); awaiting it on the capture path would delay a capture by
seconds to save one press.

That cost is paid ONCE, not once per boot: the built index is written
beside the matrix file as ``<id>.index.json`` and reloaded on the next
start, so restarts are instant. The stored index names the matrix it
came from by content hash and records the display unit its names were
built in, so a rewritten lattice or a flipped unit system rebuilds
instead of being believed. Every door that writes, copies or deletes a
matrix drops the index too.

AND IT IS PAID AT SETUP, NOT ON THE FIRST FRAME (0.10.1 item 3). The
lazy path above still exists, but nothing should ever need it at boot:
``async_warm_indexes`` runs once during setup, strictly before any
receiver is subscribed, so the first press after a restart matches.
Reading a stored index is 6 to 12 ms, which sounds like a race nobody
loses -- but a single-frame file-sourced code pressed in the first
moments after boot fell inside it, and a two-frame press only matched
because its SECOND frame arrived after the read. The lazy path stays as
the fallback for a remote minted at runtime, and the mint doors warm
their new lattice themselves so even that one rarely runs.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import EVENT_STATE_HEARD, MATRIX_STATE_DEDUP_WINDOW_S
from .identity import (
    TIER_BYTE_HASH,
    TIER_DECODED,
    TIER_NORM_FP,
    NormFpIndex,
    tier_name,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .models import TriggerRemote
    from .storage import HAIRStore
    from .trigger_manager import TriggerManager
    from .wig_format import ClimateMatrix

_LOGGER = logging.getLogger(__name__)

# One capture's identity, in ``CellIndex.match`` order: decoded
# fingerprint, S/L fingerprint, byte hash, normalized fingerprint.
# Carried past the hearing so a pinned Device can be asked "which of
# YOUR cells is this frame?" when its lattice spells the same state
# with different words -- and so it can be asked with the same
# tolerance the hearing itself had.
_Identity = tuple[str | None, str | None, str | None, str | None]


@dataclass(frozen=True)
class CellHit:
    """One heard state, resolved to the lattice.

    Carries both the key (the fittings-ledger form, "cool/auto/23") and
    the display name, plus the coordinates themselves: the card rings
    the heard branch dimension by dimension, so it needs the parts, not
    only the string. ``power`` is set for the matrix's own off/on codes
    and None for every climate cell -- the two are mutually exclusive
    by construction, which is what makes the card's rest rings
    mutually exclusive without a rule of their own.
    """

    cell_key: str
    cell_name: str
    power: str | None = None
    mode: str | None = None
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None
    sl_pattern: str | None = None


@dataclass
class CellIndex:
    """Reverse index over one lattice's cells, by identity tier.

    The lattice twin of ``pin_bindings.DeviceCommandIndex``. No
    ``fp_legacy`` map exists here on purpose -- see the module
    docstring.
    """

    decoded: dict[str, CellHit] = field(default_factory=dict)
    fp_bytehash: dict[tuple[str, str | None], CellHit] = field(
        default_factory=dict
    )
    bytehash: dict[str, CellHit] = field(default_factory=dict)
    # The receiver-tolerant tier (2026-08-18). A lattice cell is always
    # file-sourced, so every cell earns it; the gate that matters is on
    # the capture side, in match().
    norm_fp: NormFpIndex = field(default_factory=NormFpIndex)

    def __bool__(self) -> bool:
        return bool(
            self.decoded or self.fp_bytehash or self.bytehash or self.norm_fp
        )

    def match(
        self,
        decoded_fingerprint: str | None,
        signal_fingerprint: str | None,
        byte_hash: str | None,
        norm_fp: str | None = None,
    ) -> tuple[CellHit, int] | None:
        """The cell this capture is and the tier that said so, or None.

        Same tier order as every other matcher in HAIR, minus the bare
        fingerprint: an AC blob's S/L pattern is a near neighbour of its
        whole branch, so a fingerprint-only match would report the wrong
        cell, and a wrong state is a plausible lie the card would show
        with full confidence.

        The normalized fingerprint is last, and only for a capture
        NOTHING could decode. A frame that decoded has already been
        answered by tier 1 -- if its decoded identity is not in this
        lattice, the honest answer is that this lattice does not hold
        it, not that something of a similar shape does.
        """
        if decoded_fingerprint and decoded_fingerprint in self.decoded:
            return (self.decoded[decoded_fingerprint], TIER_DECODED)
        if signal_fingerprint or byte_hash:
            hit = self.fp_bytehash.get((signal_fingerprint, byte_hash))
            if hit is not None:
                return (hit, TIER_BYTE_HASH)
        if byte_hash is not None:
            hit = self.bytehash.get(byte_hash)
            if hit is not None:
                return (hit, TIER_BYTE_HASH)
        if norm_fp and not decoded_fingerprint:
            hit = self.norm_fp.get(norm_fp)
            if hit is not None:
                return (hit, TIER_NORM_FP)
        return None


def build_cell_index(
    matrix: ClimateMatrix, display_unit: str | None = None
) -> CellIndex:
    """Index every cell (and both power codes) by identity.

    Pure and blocking: callers run it in the executor. A cell whose
    Pronto does not validate is skipped -- it could never be heard
    anyway. Last write wins on a collision, matching the store's own
    index: two cells sharing a waveform ARE the same press, and the
    file's later row is the one a send would use.

    ONE IDENTITY FORM, and it is not the file's. ``wig_signal_identity``
    hashes the canonical (wire) Pronto -- see identity.py's
    canonical-form block for why a lattice code's trailing gap word does
    not survive the capture path, and what it cost before 2026-08-17.
    Do not add a second form here: if a cell ever fails to match a real
    frame, the answer is in that helper, not in another dict key.

    The normalized fingerprint is built from the cell's TIMINGS rather
    than its code text, and a value two genuinely different cells claim
    is dropped rather than won by whichever came last (identity.py's
    NormFpIndex). On the bench closet that costs a handful of lattices a
    handful of cells, and it is the price of never naming the wrong
    state.
    """
    from .event_parser import EventParser
    from .identity import canonical_pronto, norm_fingerprint
    from .wig_climate import cell_display_name, state_display_name
    from .wig_format import cell_key
    from .wig_identity import wig_signal_identity

    index = CellIndex()

    def _add(pronto: str | None, hit_factory: Any) -> None:
        if not pronto:
            return
        identity = wig_signal_identity(pronto)
        if identity is None:
            return
        # The diamonds show what was HEARD, so the pattern comes off
        # the canonical form too.
        hit = hit_factory(
            EventParser._pronto_sl_pattern(
                canonical_pronto(identity.pronto) or identity.pronto
            )
        )
        if identity.decoded_fingerprint:
            index.decoded[identity.decoded_fingerprint] = hit
        if identity.fingerprint:
            index.fp_bytehash[(identity.fingerprint, identity.byte_hash)] = hit
        if identity.byte_hash is not None:
            index.bytehash[identity.byte_hash] = hit
        index.norm_fp.add(
            norm_fingerprint(identity.raw_timings),
            identity.byte_hash or identity.fingerprint,
            hit,
        )

    for cell in matrix.cells:
        _add(
            cell.pronto,
            lambda sl, cell=cell: CellHit(
                cell_key=cell_key(cell),
                cell_name=cell_display_name(
                    cell,
                    unit=matrix.unit,
                    display_unit=display_unit,
                    precision=matrix.precision,
                ),
                mode=cell.mode,
                fan=cell.fan,
                swing=cell.swing,
                temp=cell.temp,
                sl_pattern=sl,
            ),
        )
    for power, pronto in (("off", matrix.off), ("on", matrix.on)):
        _add(
            pronto,
            lambda sl, power=power: CellHit(
                cell_key=power,
                cell_name=state_display_name(power),
                power=power,
                sl_pattern=sl,
            ),
        )
    return index


class MatrixListener:
    """Per-remote climate matrices: load, cache, and hear."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HAIRStore,
        trigger_manager: TriggerManager | None = None,
        device_manager: Any | None = None,
    ) -> None:
        self._hass = hass
        self._store = store
        # Used for three things it already owns: resolving a receiver
        # to an HA area (the v0.5.7 location trio), fanning a push out
        # to the panel's existing subscription, and -- Track 4 -- the
        # one retransmit dispatcher, so a heard state and a fired
        # trigger share a coalescer and a loop breaker. A state heard
        # is not a trigger fire and never becomes one; these are shared
        # pipes, not shared behavior.
        self._trigger_manager = trigger_manager
        # The send side of a pinned matrix Device (Track 4). Optional
        # for the same reason the trigger manager's is: without it a
        # matrix remote still hears, it just drives nothing.
        self._device_manager = device_manager
        # Parsed matrices by REMOTE id. Loaded on first ask and held
        # for the install's lifetime; misses are deliberately NOT
        # cached, so a file that appears later (a restored backup, or
        # a mint racing a list call) is picked up on the next ask
        # rather than being remembered as absent.
        self._matrix_cache: dict[str, ClimateMatrix] = {}
        self._index_cache: dict[str, CellIndex] = {}
        # Ids whose index is being built right now, so a burst of
        # frames dispatches one build rather than one per frame.
        self._building: set[str] = set()
        # Last heard time per (remote, cell), for the one-press-one-event
        # rule. Keyed on the cell as well as the remote so a deliberate
        # change of state inside the window is still two events; see
        # MATRIX_STATE_DEDUP_WINDOW_S.
        self._recent_hits: dict[tuple[str, str], float] = {}
        # --- Track 4: driving pinned matrix Devices -------------------
        # The heard frame behind each dispatched cell target, by cell
        # key. The dispatcher's target is three strings, so the send
        # side reads the coordinates back from here rather than trying
        # to parse them out of a display key. Bounded by the number of
        # distinct states this install has ever heard.
        self._heard_frames: dict[str, tuple[CellHit, _Identity]] = {}
        # (remote_id, device_id) pairs already reported as unmappable,
        # so a handset held on a state the device does not have logs
        # once instead of once per press. Cleared for a pair the moment
        # it does map, so a pairing that breaks later says so again.
        self._unmapped: set[tuple[str, str]] = set()

    # --- Access -------------------------------------------------------

    async def async_get_matrix(self, remote_id: str) -> ClimateMatrix | None:
        """The remote's climate matrix, cache-first.

        None = no file or an unreadable one; ``matrix_store`` has
        already logged the reason. Callers treat None as "this remote
        has no readable lattice" and render the flat shape rather than
        guessing, exactly as the climate entity does on the device
        side.
        """
        cached = self._matrix_cache.get(remote_id)
        if cached is not None:
            return cached
        from .matrix_store import load_matrix

        matrix = await self._hass.async_add_executor_job(
            load_matrix, self._hass.config.config_dir, remote_id
        )
        if matrix is not None:
            self._matrix_cache[remote_id] = matrix
        return matrix

    def invalidate(self, remote_id: str) -> None:
        """Drop one remote's cached matrix and index, in memory and on disk.

        Called by every door that writes, copies or deletes a matrix
        file. The caches are held for the install's lifetime on the
        argument that nothing changes a matrix behind our back, so
        every door that DOES change one has to say so here. The stored
        index would also fail its own content-hash check, but deleting
        it keeps the folder honest rather than leaving a file that
        describes a lattice nobody has any more.
        """
        self._matrix_cache.pop(remote_id, None)
        self._index_cache.pop(remote_id, None)
        for key in [k for k in self._recent_hits if k[0] == remote_id]:
            self._recent_hits.pop(key, None)
        from .matrix_store import delete_cell_index

        try:
            delete_cell_index(self._hass.config.config_dir, remote_id)
        except Exception:  # never let hygiene break a mint
            _LOGGER.debug(
                "Could not drop the stored cell index for %s",
                remote_id, exc_info=True,
            )

    def forget_matrix(self, matrix_id: str) -> None:
        """Drop everything held for a matrix that no longer exists.

        ``invalidate`` is for a lattice that CHANGED; this is for one
        that is GONE (0.10.1 item 8). On top of the caches invalidate
        clears, it drops the already-reported unmapped pairings that
        name this id, so a later id can never inherit a suppression it
        did not earn.
        """
        self.invalidate(matrix_id)
        for pair in [
            p for p in self._unmapped if matrix_id in p
        ]:
            self._unmapped.discard(pair)

    # --- Warming ------------------------------------------------------

    def _matrix_ids_to_warm(self) -> list[str]:
        """Every lattice this install can be asked about at boot.

        Both sides of the pairing, because both index through this one
        cache: a matrix Remote hears on its lattice, and a matrix Device
        that a Remote is pinned to is asked "which of YOUR cells is this
        frame?" through ``_cell_by_identity``. Warming only the remotes
        would leave the Track 4 fallback cold and lose the first press
        that needs it, which is the same defect one layer down.
        """
        ids: list[str] = []
        seen: set[str] = set()

        def _want(matrix_id: str) -> None:
            if matrix_id in seen or matrix_id in self._index_cache:
                return
            seen.add(matrix_id)
            ids.append(matrix_id)

        for remote in self._store.get_all_trigger_remotes():
            if not remote.climate_matrix:
                continue
            _want(remote.id)
            for device_id in remote.pinned_device_ids:
                device = self._store.get_device(device_id)
                if device is not None and device.climate_matrix:
                    _want(device_id)
        return ids

    async def async_warm_indexes(self) -> None:
        """Read or build every cell index before the first frame arrives.

        Called once at setup, before receivers are subscribed. Each
        build already runs its disk read and its per-cell decode in the
        executor, so the per-lattice work overlaps; a failure warms one
        lattice less rather than failing setup, since the lazy path is
        still there to try again on the first frame.
        """
        ids = self._matrix_ids_to_warm()
        if not ids:
            return
        results = await asyncio.gather(
            *(self._async_warm_one(matrix_id) for matrix_id in ids),
            return_exceptions=True,
        )
        read = sum(1 for r in results if r == "read")
        built = sum(1 for r in results if r == "built")
        for matrix_id, result in zip(ids, results, strict=True):
            if isinstance(result, BaseException):
                _LOGGER.debug(
                    "Could not warm the cell index for matrix %s at setup; "
                    "it will be built on the first frame instead",
                    matrix_id, exc_info=result,
                )
        _LOGGER.info(
            "Warmed %d cell indexes at setup (%d read from disk, %d built)",
            read + built, read, built,
        )

    async def _async_warm_one(self, matrix_id: str) -> str | None:
        """One warm, holding the same in-flight guard the lazy path sets."""
        if matrix_id in self._building:
            return None
        self._building.add(matrix_id)
        return await self._async_build_index(matrix_id)

    def warm_index(self, matrix_id: str) -> None:
        """Build one lattice's index now, off the caller's path.

        The mint doors call this the moment a matrix file lands, so a
        remote created at runtime is ready for its first press the same
        way a remote that existed at boot is. Safe to call twice: an
        in-flight build is not started again.
        """
        self._schedule_index_build(matrix_id)

    # --- Hearing ------------------------------------------------------

    async def on_signal_captured(
        self,
        signal_fingerprint: str | None,
        byte_hash: str | None,
        decoded_fingerprint: str | None,
        receiver_entity_id: str | None = None,
        norm_fp: str | None = None,
    ) -> list[str]:
        """Match one capture against every matrix remote's lattice.

        Runs on the capture path, right after the trigger match and
        under the same not-echo gate, so HAIR never hears its own
        transmissions as handset presses. Returns the ids of the
        remotes that heard something (for caller awareness and tests).

        ``norm_fp`` is the capture's receiver-tolerant fingerprint,
        computed once per capture beside the byte hash and passed down
        the same way. Absent (the default) simply means the lowest tier
        is not consulted.
        """
        heard: list[str] = []
        for remote in self._store.get_all_trigger_remotes():
            if not remote.climate_matrix:
                continue
            # Remote-level receiver scope (the 2026-08-10 ruling): a
            # named remote's rows never carry their own, so the
            # remote's own list is the whole rule here.
            if not remote.matches_receiver(receiver_entity_id):
                continue
            index = self._index_cache.get(remote.id)
            if index is None:
                self._schedule_index_build(remote.id)
                continue
            matched = index.match(
                decoded_fingerprint, signal_fingerprint, byte_hash, norm_fp
            )
            if matched is None:
                continue
            hit, tier = matched
            # ONE PRESS IS ONE EVENT. Two receivers observing the same
            # frame arrive here twice, and so do the two frames a single
            # press of an AC state code is made of (103 to 148 ms apart
            # on the bench). The window slides for the same reason the
            # trigger dedup's does, so a held button collapses too, and
            # it is keyed on the CELL as well as the remote: hearing a
            # different state inside the window is a different press.
            now = time.monotonic()
            key = (remote.id, hit.cell_key)
            if (
                now - self._recent_hits.get(key, 0.0)
                < MATRIX_STATE_DEDUP_WINDOW_S
            ):
                self._recent_hits[key] = now
                continue
            self._recent_hits[key] = now
            # WHICH TIER ANSWERED. The dress rehearsal had to rebuild
            # the index outside HAIR to learn this; now the log says.
            _LOGGER.debug(
                "Remote '%s' heard %s on the %s tier (receiver %s)",
                remote.name, hit.cell_key, tier_name(tier),
                receiver_entity_id or "unknown",
            )
            self._record(
                remote,
                hit,
                receiver_entity_id,
                (decoded_fingerprint, signal_fingerprint, byte_hash, norm_fp),
            )
            heard.append(remote.id)
        return heard

    def _schedule_index_build(self, remote_id: str) -> None:
        """Build one lattice's cell index off the capture path.

        Takes a matrix id, not specifically a remote's: a pinned matrix
        Device's lattice is indexed through here too (Track 4), and
        ``matrix_store`` keys both from one flat namespace.
        """
        if remote_id in self._building:
            return
        self._building.add(remote_id)
        _LOGGER.debug(
            "Building the cell index for matrix %s; frames heard before "
            "it is ready do not match", remote_id,
        )
        self._hass.async_create_task(self._async_build_index(remote_id))

    async def _async_build_index(self, remote_id: str) -> str | None:
        """Populate one lattice's index; "read", "built" or None.

        The return value exists for the setup warm's one INFO line. The
        lazy path drops it, as a task's result always is.
        """
        try:
            from .wig_climate import unit_letter

            display_unit = unit_letter(
                self._hass.config.units.temperature_unit
            )
            index = await self._hass.async_add_executor_job(
                _load_stored_index,
                self._hass.config.config_dir, remote_id, display_unit,
            )
            if index is not None:
                self._index_cache[remote_id] = index
                _LOGGER.debug(
                    "Cell index for remote %s read from disk", remote_id
                )
                return "read"
            matrix = await self.async_get_matrix(remote_id)
            if matrix is None:
                return None
            index = await self._hass.async_add_executor_job(
                _build_and_store_index,
                self._hass.config.config_dir, remote_id, matrix, display_unit,
            )
            self._index_cache[remote_id] = index
            _LOGGER.debug(
                "Cell index built for matrix %s: %d decoded, %d hashed",
                remote_id, len(index.decoded), len(index.bytehash),
            )
            return "built"
        finally:
            self._building.discard(remote_id)

    def _record(
        self,
        remote: TriggerRemote,
        hit: CellHit,
        receiver_entity_id: str | None,
        identity: _Identity = (None, None, None, None),
    ) -> None:
        """Stamp the heard state, fire the event, push, and dispatch.

        Synchronous for the same reason ``_fire_trigger`` is: this runs
        from the capture path, so the save is dispatched as a task
        rather than awaited. A heard state is human-press-paced, so a
        save per hearing is proportionate -- the same call the trigger
        fire path makes for ``fire_count``.
        """
        now_iso = datetime.now(UTC).isoformat()
        area_id: str | None = None
        area_name: str | None = None
        if self._trigger_manager is not None:
            area_id, area_name = self._trigger_manager.resolve_receiver_area(
                receiver_entity_id
            )

        remote.last_heard = {
            "cell_key": hit.cell_key,
            "cell_name": hit.cell_name,
            "power": hit.power,
            "mode": hit.mode,
            "fan": hit.fan,
            "swing": hit.swing,
            "temp": hit.temp,
            "sl_pattern": hit.sl_pattern,
            "at": now_iso,
            "receiver_entity_id": receiver_entity_id,
            "receiver_area_name": area_name,
        }
        remote.updated_at = now_iso
        self._store.update_trigger_remote(remote)
        self._hass.async_create_task(self._store.async_save())

        event_data = {
            "remote_id": remote.id,
            "remote_name": remote.name,
            "cell_key": hit.cell_key,
            "cell_name": hit.cell_name,
            "power": hit.power,
            "mode": hit.mode,
            "fan": hit.fan,
            "swing": hit.swing,
            "temp": hit.temp,
            "timestamp": now_iso,
            # The v0.5.7 location trio, resolved the same way and at
            # the same moment a trigger fire resolves it.
            "receiver_entity_id": receiver_entity_id,
            "receiver_area_id": area_id,
            "receiver_area_name": area_name,
        }
        self._hass.bus.async_fire(EVENT_STATE_HEARD, event_data)

        # The panel's bloom rides the existing trigger subscription
        # with a discriminator rather than a second subscribe command:
        # one channel, two kinds of news.
        if self._trigger_manager is not None:
            self._trigger_manager.notify_subscribers({
                "kind": "state_heard", **event_data,
            })

        self._dispatch_pinned_cell(remote, hit, identity)

    # --- Driving pinned matrix Devices (Track 4) ------------------------
    #
    # THE INTERSECTION. Pinning maps a Remote's BUTTONS to a Device's
    # COMMANDS (pin_bindings). A matrix pair has neither: the remote
    # hears a state, and the device holds a lattice. So the map here is
    # made of coordinates, not rows -- what was heard as "cool, fan
    # auto, 23" is looked up as "cool, fan auto, 23" on the device.
    #
    # Two lattices minted from the SAME wig agree on those coordinates
    # exactly, which is the case this was built for. Two different wigs
    # for the same unit need not: one file may write the fan speed as
    # "auto" and the other as "Auto". The fallback is the frame itself
    # -- if the device's lattice contains a cell that transmits the
    # very bytes just heard, that cell IS the heard state whatever its
    # file calls it. When neither the words nor the bytes match, this
    # sends nothing. A near-miss cell would be a plausible lie sent at
    # a real air conditioner, which is worse than silence.

    def _dispatch_pinned_cell(
        self, remote: TriggerRemote, hit: CellHit, identity: _Identity
    ) -> None:
        """Drive the same state on every pinned matrix Device.

        Synchronous like the rest of ``_record``, so the resolution
        (which reads lattices, possibly off disk) runs as a task. A
        remote with no pins pays one attribute check, the common case.
        """
        if self._trigger_manager is None or not remote.pinned_device_ids:
            return
        self._heard_frames[hit.cell_key] = (hit, identity)
        self._hass.async_create_task(
            self._async_dispatch_pinned_cell(remote, hit, identity)
        )

    async def _async_dispatch_pinned_cell(
        self, remote: TriggerRemote, hit: CellHit, identity: _Identity
    ) -> None:
        for device_id in remote.pinned_device_ids:
            device = self._store.get_device(device_id)
            # A pinned FLAT device is out of scope (Track 4.2): a state
            # has no command row to land on, and pin_bindings already
            # yields nothing for a matrix remote's buttons.
            if device is None or not device.climate_matrix:
                continue
            pair = (remote.id, device_id)
            resolved = await self._async_resolve_device_cell(
                device_id, hit, identity
            )
            if resolved is None:
                if pair not in self._unmapped:
                    self._unmapped.add(pair)
                    _LOGGER.debug(
                        "Remote '%s' heard %s, but device '%s' has no such "
                        "state and no cell carrying that code; nothing sent "
                        "for this pairing until one of them changes",
                        remote.name, hit.cell_key, device.name,
                    )
                continue
            self._unmapped.discard(pair)
            # The target's third element is the HEARD key, so a handset
            # held on one state coalesces into one pending send per
            # device exactly as a held button does per command.
            self._trigger_manager.dispatch_cell_retransmit(
                remote.id,
                device_id,
                hit.cell_key,
                (remote.name, device.name, hit.cell_name),
            )

    async def async_send_pinned_cell(
        self, device_id: str, cell_key: str
    ) -> None:
        """Send the heard state on one pinned device (the dispatcher's send).

        Called from ``TriggerManager._send_bound_command`` when a target
        carries the cell prefix, so a cell retransmit and a command
        retransmit leave through the same door. Resolves again rather
        than carrying a Pronto through the queue: a coalesced target can
        be sent a moment after it was dispatched, and the lattice on
        disk is the only thing entitled to say what bytes a state is.
        """
        frame = self._heard_frames.get(cell_key)
        if frame is None or self._device_manager is None:
            return
        hit, identity = frame
        resolved = await self._async_resolve_device_cell(
            device_id, hit, identity
        )
        if resolved is None:
            return
        name, pronto, send_count, state = resolved
        # pinned=True is what mints the echo ticket and labels the
        # Mirror row, exactly as it does for a command retransmit.
        #
        # The coordinates ride along (0.10.1 item 7): a pinned
        # retransmit is a SEND, so the pinned Device's climate card
        # follows it. This is the one door by which a heard state
        # reaches a card, and it reaches it as the send it caused, not
        # as the hearing -- an unpinned Remote hearing the same handset
        # moves nothing.
        power = state.get("power")
        await self._device_manager.async_send_matrix_cell(
            device_id, name, pronto, send_count, pinned=True,
            cell=None if power else dict(state),
            power=power,
        )

    async def _async_resolve_device_cell(
        self, device_id: str, hit: CellHit, identity: _Identity
    ) -> tuple[str, str, int, dict[str, Any]] | None:
        """The heard state on that device: (name, Pronto, count, state).

        Coordinates first, the frame's own identity second, nothing
        third. The bytes always come from the device's CURRENT lattice
        (the device manager's cache, which its writers invalidate), so
        even a stale index can only ever mis-map -- it cannot make this
        transmit a code the file no longer holds.
        """
        if self._device_manager is None:
            return None
        matrix = await self._device_manager.async_get_matrix(device_id)
        if matrix is None:
            return None
        from .wig_climate import (
            cell_display_name,
            exact_cell,
            state_display_name,
            unit_letter,
        )

        # Power is a pseudo-cell on both sides: the matrix's own off/on
        # codes, which every lattice has (on is optional) whatever its
        # climate vocabulary looks like.
        if hit.power is not None:
            pronto = matrix.off if hit.power == "off" else matrix.on
            if not pronto:
                return None
            return (
                state_display_name(hit.power), pronto, 1,
                {"power": hit.power},
            )

        cell = None
        if hit.mode is not None:
            cell = exact_cell(matrix, hit.mode, hit.fan, hit.swing, hit.temp)
        if cell is None:
            cell = self._cell_by_identity(device_id, matrix, identity)
        if cell is None:
            return None
        return (
            cell_display_name(
                cell,
                unit=matrix.unit,
                display_unit=unit_letter(
                    self._hass.config.units.temperature_unit
                ),
                precision=matrix.precision,
            ),
            cell.pronto,
            cell.send_count,
            # The DEVICE's own coordinates, not the remote's: two wigs
            # for one unit may spell a dimension differently, and the
            # card belongs to the device.
            {
                "mode": cell.mode, "fan": cell.fan,
                "swing": cell.swing, "temp": cell.temp,
            },
        )

    def _cell_by_identity(
        self, device_id: str, matrix: ClimateMatrix, identity: _Identity
    ) -> Any | None:
        """The device cell whose code IS this frame, or None.

        Uses the device's own ``CellIndex``, built and stored exactly
        like a remote's -- ``matrix_store`` is id-agnostic, so a device
        lattice indexes and persists through the same helpers. The
        build runs in the background for the same reason it does on the
        hear side, so the first press that needs this fallback resolves
        nothing and the next one does.
        """
        index = self._index_cache.get(device_id)
        if index is None:
            self._schedule_index_build(device_id)
            return None
        matched = index.match(*identity)
        if matched is None:
            return None
        hit, _tier = matched
        if hit.power is not None or hit.mode is None:
            return None
        from .wig_climate import exact_cell

        return exact_cell(matrix, hit.mode, hit.fan, hit.swing, hit.temp)


# ---------------------------------------------------------------------------
# The index on disk (signpost 4, Track M)
# ---------------------------------------------------------------------------
#
# Blocking helpers: the listener runs both through the executor. Kept at
# module level, beside the builder they wrap, so the on-disk shape and
# the in-memory one cannot drift apart in a refactor.

# Bumped to /2 for the receiver-tolerant tier (2026-08-18) and to /3 for
# the unified strip (GH #125). A stored index of an older format is
# simply not read, so every lattice rebuilds once and gains the new map;
# the rebuild is the same seconds-of-work the first build was.
#
# WHY THE VERSION IS THE ONLY LEVER HERE. ``_load_stored_index`` checks
# three things: this string, the matrix file's content hash, and the
# display unit. A change to the identity ALGORITHM moves none of them --
# the migration never touches the matrix file, so its content hash is
# unchanged -- and the stored index would go on answering with
# pre-migration hashes while captures arrived carrying post-migration
# ones. Every climate lattice would silently stop recognizing its own
# cells, with nothing in any log to say so.
INDEX_FORMAT = "hair-cell-index/3"


def _hit_to_row(hit: CellHit) -> list:
    return [
        hit.cell_key, hit.cell_name, hit.power, hit.mode, hit.fan,
        hit.swing, hit.temp, hit.sl_pattern,
    ]


def _row_to_hit(row: list) -> CellHit:
    return CellHit(
        cell_key=row[0], cell_name=row[1], power=row[2], mode=row[3],
        fan=row[4], swing=row[5], temp=row[6], sl_pattern=row[7],
    )


def _index_to_payload(
    index: CellIndex, content_hash: str | None, display_unit: str | None
) -> dict:
    """Serialize an index: one hit table, three maps of indices into it.

    A lattice's cells are heavily shared across tiers (the same hit is
    reachable by decoded fingerprint, by composite key and by hash), so
    storing the hits once and pointing at them keeps the file at roughly
    the size of the coordinates rather than three copies of them.
    """
    hits: list[list] = []
    seen: dict[int, int] = {}

    def _ref(hit: CellHit) -> int:
        key = id(hit)
        if key not in seen:
            seen[key] = len(hits)
            hits.append(_hit_to_row(hit))
        return seen[key]

    return {
        "format": INDEX_FORMAT,
        # What this index was built FROM. A rewritten matrix gets a new
        # hash and this file is ignored (and normally already deleted).
        "matrix": content_hash,
        # Cell NAMES are display strings, so they freeze the unit they
        # were built in; flipping the install's unit rebuilds.
        "unit": display_unit,
        "hits": hits,
        "decoded": {k: _ref(v) for k, v in index.decoded.items()},
        "fp_bytehash": [
            [fp, bh, _ref(hit)]
            for (fp, bh), hit in index.fp_bytehash.items()
        ],
        "bytehash": {k: _ref(v) for k, v in index.bytehash.items()},
        # Only the unambiguous entries: a value two different cells
        # claimed was already dropped at build time and must not come
        # back through the file.
        "norm_fp": {k: _ref(v) for k, v in index.norm_fp.refs.items()},
    }


def _payload_to_index(payload: dict) -> CellIndex | None:
    try:
        if payload.get("format") != INDEX_FORMAT:
            return None
        hits = [_row_to_hit(row) for row in payload["hits"]]
        index = CellIndex()
        for key, ref in payload["decoded"].items():
            index.decoded[key] = hits[ref]
        for fp, bh, ref in payload["fp_bytehash"]:
            index.fp_bytehash[(fp, bh)] = hits[ref]
        for key, ref in payload["bytehash"].items():
            index.bytehash[key] = hits[ref]
        for key, ref in payload["norm_fp"].items():
            # Already resolved when it was written; re-claiming through
            # add() would need the discriminators, which the file has no
            # reason to carry.
            index.norm_fp.refs[key] = hits[ref]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return index or None


def _load_stored_index(
    config_dir: str, remote_id: str, display_unit: str | None
) -> CellIndex | None:
    """The index from disk, or None when absent, stale or unreadable."""
    from .matrix_store import load_cell_index, matrix_content_hash

    payload = load_cell_index(config_dir, remote_id)
    if payload is None:
        return None
    if payload.get("unit") != display_unit:
        return None
    if payload.get("matrix") != matrix_content_hash(config_dir, remote_id):
        return None
    return _payload_to_index(payload)


def _build_and_store_index(
    config_dir: str, remote_id: str, matrix: Any, display_unit: str | None
) -> CellIndex:
    """Build the index and leave a copy on disk for the next boot."""
    from .matrix_store import matrix_content_hash, write_cell_index

    index = build_cell_index(matrix, display_unit)
    write_cell_index(
        config_dir,
        remote_id,
        _index_to_payload(
            index, matrix_content_hash(config_dir, remote_id), display_unit
        ),
    )
    return index
