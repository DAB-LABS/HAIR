"""Fittings: proving a wig on real hardware (Perfect Fit).

Design source: docs/internal/plans/fitting-flow.md. The load-bearing
rulings, restated:

- A fitting is per-signal human verdicts (worked / did not), and the
  overall verdict is DERIVED from them, never asked (2.2). PERFECT FIT
  means every signal confirmed and none failed.
- Session state lives IN THE LOCAL WIG FILE, not a side store (13.3):
  the first mark writes a draft fitting into the .wig.json (debounced),
  so progress survives reboots and updates. RESUME is just reading the
  file. DISCARD removes the draft; closing the dialog loses nothing.
- Partials and drafts are LOCAL ONLY (2.3): the share paths (download /
  copy JSON) strip every fitting that is not complete-and-signed, and
  drop the ``fittings`` key when nothing survives. The on-disk file
  always keeps everything.
- Fittings bind to ``wig_content_hash`` (tamper evidence): the v1
  signals hash for signal wigs, byte-for-byte as shipped in 0.8.0, and
  the cells hash for matrix wigs (Cold Cuts) -- the dimension check
  attests the MATRIX, so that is what the hash must cover. A hash
  mismatch marks the fitting invalid ("codes changed since this
  fitting") rather than deleting it.
- The verdict lists are ROW-KEY lists, not counts: the alias for a
  signal wig, the checklist cell key ("cool/auto/23", "on", "off") for
  a matrix wig. Both live inside their canonical hash form, so a
  rename breaks the hash and invalidates the fitting instead of
  silently mismatching.
- Matrix wigs fit through the SAME manager via the rows abstraction
  (``fitting_rows``): a session addresses rows by index whichever kind
  of wig is under test, and only the row source differs -- the signals
  array for v1 wigs, the dimension checklist for matrix wigs (owner
  rulings 2026-07-28: nobody fits 2,689 cells; everybody can fit every
  dimension).

Storage shape: fittings live under the ``fittings`` top-level key,
which wig_format deliberately does NOT school itself on -- it rides in
``Wig.extra`` under the unknown-key preservation contract (an older
install editing the wig cannot destroy them). This module is the only
writer. Entries it cannot parse are preserved on disk, surfaced as
warnings, and dropped from the share paths (a newer format's fitting is
not something this install can attest as complete).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import MAX_SEND_COUNT
from .wig_format import Wig, serialize_wig, wig_content_hash

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .signal_monitor import SignalMonitor

_LOGGER = logging.getLogger(__name__)

FITTINGS_KEY = "fittings"

# Marks are written through to the wig file with this debounce, so a
# fast run down a signal list costs one write, not one per tap.
FITTING_WRITE_DEBOUNCE_S = 2.0

# How long a fitting send waits for its Mirror echo before reporting
# heard=false. Loopback normally lands within ~300 ms; this stays under
# MIRROR_ECHO_TTL_S so we never report on an expired expectation.
FITTING_HEARD_WAIT_S = 2.0

_VERDICT_WORKED = "worked"
_VERDICT_FAILED = "failed"
_VERDICT_UNTESTED = "untested"
VERDICTS = (_VERDICT_WORKED, _VERDICT_FAILED, _VERDICT_UNTESTED)


# ---------------------------------------------------------------------------
# Pure layer: parsing, completeness, summaries, share stripping
# ---------------------------------------------------------------------------


def fitting_rows(wig: Wig) -> list[tuple[str, str, int]]:
    """What a fitting session actually walks: (key, pronto, send_count).

    The rows abstraction (Cold Cuts): signal wigs fit their signals
    one-to-one (key = alias, exactly the pre-0.8.8 behavior); matrix
    wigs fit the DIMENSION CHECKLIST (key = cell key, or literal
    "on"/"off"), never the raw lattice. Deterministic by construction
    on both sides -- session indexes, marks, and completeness all key
    off this one list, so the two wig kinds cannot drift apart. Note
    the deliberate asymmetry: a matrix wig's flat extras (on_once,
    sleep...) are NOT rows; the dimension check attests the matrix,
    and the extras are ordinary buttons outside its hash.
    """
    if wig.climate is not None:
        from .wig_climate import dimension_checklist

        return [
            (row.key, row.pronto, row.send_count)
            for row in dimension_checklist(wig.climate)
        ]
    return [
        (sig.alias, sig.pronto, sig.send_count) for sig in wig.signals
    ]


@dataclass
class Fitting:
    """One parsed fittings entry, wrapping its raw dict.

    ``raw`` is the live dict inside ``Wig.extra["fittings"]``; mutations
    through the manager write into it so unknown per-fitting keys are
    preserved. The parsed attributes are read-time conveniences.
    """

    raw: dict[str, Any]
    handle: str
    confirmed: list[str]
    failed: list[str]
    content_hash: str
    draft: bool

    @property
    def github(self) -> str | None:
        value = self.raw.get("github")
        return value if isinstance(value, str) and value else None

    @property
    def send_times_used(self) -> int | None:
        """The send-times evidence this fitting carries, clamped.

        ABSENT IS NOT 1: a fitting without the field predates it (or
        came from a tool that does not write it) and claims nothing --
        None here, never coerced. An explicit value is clamped to
        1..MAX_SEND_COUNT on read (design 5.3: a signature makes a
        value tamper-evident, not sane).
        """
        return _read_send_times(self.raw)


@dataclass
class FittingsView:
    """Every parseable fitting in a wig, plus what could not be parsed."""

    fittings: list[Fitting] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_fittings(wig: Wig) -> FittingsView:
    """Read ``wig.extra['fittings']`` permissively.

    A malformed block or entry never invalidates the wig (plan 5.1: the
    block is surfaced, not fatal); it is skipped with a warning and left
    untouched on disk.
    """
    view = FittingsView()
    raw_list = wig.extra.get(FITTINGS_KEY)
    if raw_list is None:
        return view
    if not isinstance(raw_list, list):
        view.warnings.append('"fittings" is not a list; ignored')
        return view
    for i, entry in enumerate(raw_list):
        parsed = _parse_entry(entry)
        if parsed is None:
            view.warnings.append(
                f"fittings[{i}]: unreadable entry (kept on disk, "
                "ignored here)"
            )
            continue
        view.fittings.append(parsed)
    return view


def _parse_entry(entry: Any) -> Fitting | None:
    if not isinstance(entry, dict):
        return None
    handle = entry.get("handle")
    content_hash = entry.get("content_hash")
    if not isinstance(handle, str) or not handle:
        return None
    if not isinstance(content_hash, str) or not content_hash:
        return None
    confirmed = entry.get("confirmed", [])
    failed = entry.get("failed", [])
    if not _is_str_list(confirmed) or not _is_str_list(failed):
        return None
    return Fitting(
        raw=entry,
        handle=handle,
        confirmed=list(confirmed),
        failed=list(failed),
        content_hash=content_hash,
        draft=entry.get("draft") is True,
    )


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _read_send_times(entry: dict[str, Any]) -> int | None:
    """Read ``send_times_used`` from a raw fitting dict, clamped.

    None for absent or unreadable (bool is an int subclass and reads
    as garbage, not as 1). This is the ONE place the value is parsed,
    so the absent-is-not-1 rule cannot drift between readers.
    """
    value = entry.get("send_times_used")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(1, min(value, MAX_SEND_COUNT))


def fitting_send_times_max(wig: Wig) -> int:
    """The highest send-times any fitter needed: the adopt/factory seed.

    THE single aggregation point (handoff 4.1): ADOPT DEVICE, the
    factory and the shop index all call this, so the rule cannot
    drift. Max, never mean or mode -- send times is a threshold ("at
    least N to be reliable"), and averaging [1, 3, 3] to 2 serves
    nobody (design section 4).

    Counts every COMPLETE fitting whose content hash matches the
    CURRENT codes, signed or unsigned (design 5.0: a measurement, not
    a vote; the incentive to inflate is nil). Stale-hash fittings
    describe different codes and are excluded. Absent values
    contribute nothing. Returns 1 when nothing is known.
    """
    best = 1
    for fitting in parse_fittings(wig).fittings:
        if not fitting_is_valid(fitting, wig):
            continue
        if not fitting_is_complete(fitting, wig):
            continue
        value = fitting.send_times_used
        if value is not None and value > best:
            best = value
    return best


def fitting_is_valid(fitting: Fitting, wig: Wig) -> bool:
    """Hash validity: do the codes still match what was fitted?"""
    return fitting.content_hash == wig_content_hash(wig)


def fitting_is_complete(fitting: Fitting, wig: Wig) -> bool:
    """Complete = signed (not draft), nothing failed, every row confirmed.

    Only a complete fitting travels (2.3) and only complete fittings
    count toward the factory promotion bar (Section 8). "Every row" is
    the rows abstraction: aliases for signal wigs, the dimension
    checklist for matrix wigs.
    """
    if fitting.draft or fitting.failed:
        return False
    keys = {key for key, _, _ in fitting_rows(wig)}
    return keys <= set(fitting.confirmed)


def shared_wig_text(wig: Wig) -> str:
    """Serialize a wig for the SHARE paths (download / copy JSON).

    Keeps only complete, hash-valid fittings; drops the ``fittings`` key
    entirely when nothing survives; drops unparseable entries (this
    install cannot attest them). The on-disk file is never touched by
    this -- partials are progress, not attestations, and the shared
    artifact must not carry half-claims (owner ruling 2026-07-25).
    """
    view = parse_fittings(wig)
    kept = [
        f.raw for f in view.fittings
        if fitting_is_complete(f, wig) and fitting_is_valid(f, wig)
    ]
    extra = dict(wig.extra)
    if kept:
        extra[FITTINGS_KEY] = kept
    else:
        extra.pop(FITTINGS_KEY, None)
    stripped = Wig(
        name=wig.name,
        signals=wig.signals,
        brand=wig.brand,
        model=wig.model,
        kind=wig.kind,
        notes=wig.notes,
        origin=wig.origin,
        identifiers=wig.identifiers,
        # The matrix travels too (Cold Cuts): omitting it here would
        # replay the shared_wig_text field-drop bug that once ate
        # identifiers (regression-tested since 0.8.0).
        climate=wig.climate,
        extra=extra,
    )
    return serialize_wig(stripped)


def wig_needs_share_strip(wig: Wig) -> bool:
    """True when sharing this wig verbatim would leak a non-attestation.

    Lets the download path return the byte-exact original file whenever
    stripping would change nothing (hand-authored formatting survives).
    """
    raw_list = wig.extra.get(FITTINGS_KEY)
    if raw_list is None:
        return False
    if not isinstance(raw_list, list):
        return True
    view = parse_fittings(wig)
    if len(view.fittings) != len(raw_list):
        return True  # unparseable entries present
    return any(
        not (fitting_is_complete(f, wig) and fitting_is_valid(f, wig))
        for f in view.fittings
    )


def fitting_summary(wig: Wig, username: str | None) -> dict[str, Any]:
    """The closet-row payload: coverage, failures, local user's state.

    Computed here so the frontend filter never recomputes from raw
    fittings (plan 5.2). Hash-invalid fittings are excluded -- a row
    marker must never claim codes that changed since the fitting; the
    editor's ledger is where invalidity is explained.
    """
    rows = fitting_rows(wig)
    total = len(rows)
    view = parse_fittings(wig)
    valid = [f for f in view.fittings if fitting_is_valid(f, wig)]

    def _state(fitting: Fitting) -> str:
        if fitting_is_complete(fitting, wig):
            return "perfect"
        return "partial"

    user_fitting = next(
        (
            f for f in valid
            if username and f.handle.strip().lower() == username.strip().lower()
        ),
        None,
    )
    others_complete = sum(
        1 for f in valid
        if f is not user_fitting and fitting_is_complete(f, wig)
    )
    best: str | None = None
    if any(fitting_is_complete(f, wig) for f in valid):
        best = "perfect"
    elif valid:
        best = "partial"

    coverage_source = user_fitting or (valid[0] if valid else None)
    keys = {key for key, _, _ in rows}
    confirmed = failed = 0
    if coverage_source is not None:
        confirmed = len(set(coverage_source.confirmed) & keys)
        failed = len(set(coverage_source.failed) & keys)
    return {
        "state": best,
        "user_state": _state(user_fitting) if user_fitting else None,
        "user_draft": bool(user_fitting and user_fitting.draft),
        "confirmed": confirmed,
        "failed": failed,
        "total": total,
        "others_complete": others_complete,
        "warnings": view.warnings,
    }


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


# ---------------------------------------------------------------------------
# The manager: sessions, sends, marks, the debounced writer
# ---------------------------------------------------------------------------


class FittingManager:
    """Fitting sessions against wig files, with write-through persistence.

    One instance per config entry, alongside signal_monitor in the entry
    data. All mutation happens on the event loop; only file I/O leaves
    it, so no lock is needed. Anything else that rewrites a wig file
    (wigs/update, delete, download) must call :meth:`async_flush` first
    so a pending debounced write can never resurrect stale content over
    a newer edit.
    """

    def __init__(self, hass: HomeAssistant, monitor: SignalMonitor) -> None:
        self._hass = hass
        self._monitor = monitor
        # filename -> in-memory Wig with unwritten fitting marks.
        self._pending: dict[str, Wig] = {}
        self._timers: dict[str, Any] = {}
        # filename -> session facts that are not (yet) in the file:
        # chosen emitter, per-signal protocol state (RC-5 toggle / Dyson
        # counter) advanced per press, receiver platform seen on echoes.
        self._sessions: dict[str, dict[str, Any]] = {}
        self._hair_version: str | None = None
        # The install's signing key, loaded (or minted) on first
        # finish. False = tried and unavailable, don't retry per-sign.
        self._signing_key: str | bool | None = None

    # -- loading ---------------------------------------------------------

    async def _load(self, filename: str) -> Wig | None:
        """The manager's view of a wig: pending in-memory copy first."""
        if filename in self._pending:
            return self._pending[filename]
        from .wig_store import load_wig

        return await self._hass.async_add_executor_job(
            load_wig, self._hass.config.config_dir, filename
        )

    def _session(self, filename: str) -> dict[str, Any]:
        return self._sessions.setdefault(filename, {
            "emitter": None,
            "emitter_platform": None,
            "receiver_platform": None,
            "extras": {},        # signal index -> live decoded_extras
            "heard": set(),      # aliases whose echo came back
            # Highest send-times value used on any send this session
            # (fine-tuned-fittings). MONOTONIC by owner ruling
            # 2026-07-30: lowering the control never lowers the
            # record, so a signal proven at 3 stays claimed at 3 even
            # if the fitter drops back to 1 for the next one. None
            # until the control is first exercised; merged into the
            # draft at mark/finish and written directly on send when
            # a draft already exists.
            "send_times": None,
        })

    def session_send_times(self, filename: str) -> int | None:
        """Peek the session's send-times record without creating one."""
        session = self._sessions.get(filename)
        if not session:
            return None
        return session.get("send_times")

    async def _versions(self) -> tuple[str | None, str | None]:
        if self._hair_version is None:
            try:
                from homeassistant.loader import async_get_integration

                from .const import DOMAIN

                integration = await async_get_integration(
                    self._hass, DOMAIN
                )
                self._hair_version = str(integration.version)
            except Exception:  # never block a fitting on metadata
                self._hair_version = ""
        try:
            from homeassistant.const import __version__ as ha_version
        except ImportError:
            ha_version = None
        return (self._hair_version or None, ha_version)

    async def _private_key(self) -> str | None:
        if self._signing_key is None:
            from .fitting_signing import async_get_private_key

            key = await async_get_private_key(self._hass)
            self._signing_key = key if key is not None else False
        return self._signing_key or None

    def _platform_of(self, entity_id: str) -> str | None:
        try:
            from homeassistant.helpers import entity_registry as er

            entry = er.async_get(self._hass).async_get(entity_id)
            platform = entry.platform if entry else None
            # Only ever a plain string lands in the fitting evidence
            # (this value is written into the wig file).
            return platform if isinstance(platform, str) else None
        except Exception:
            return None

    # -- send ------------------------------------------------------------

    async def async_send(
        self,
        filename: str,
        index: int,
        emitter_entity_id: str,
        send_times: int | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        """Send one fitting row through an emitter; report sent + heard.

        No signal-store dependency (plan 4.1): identity derives fresh
        from the row's Pronto via the shared helper, the command builds
        decoded-preferring exactly like the catalog Test path, and the
        send claims its own Mirror echo, which is where ``heard`` comes
        from. ``index`` addresses ``fitting_rows(wig)``, so a matrix
        wig's checklist and a signal wig's aliases ride the identical
        path -- only the row source differs.

        ``send_times`` is the session control (fine-tuned-fittings):
        this send loops that many times instead of the row's own
        ``send_count``, and the highest value ever used is recorded as
        ``send_times_used`` evidence. When the caller's ``username``
        already has a draft, the record is written into it here, on
        the send, so a mid-fitting HA restart cannot roll a tested-at-3
        claim back to 1 (handoff 4.2); before the first mark the
        session carries it, because the first mark is what creates the
        draft and a bare test send must not.
        """
        if self._hass.states.get(emitter_entity_id) is None:
            return {"success": False, "code": "entity_not_found",
                    "error": f"Entity {emitter_entity_id} not found"}
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        rows = fitting_rows(wig)
        if not 0 <= index < len(rows):
            return {"success": False, "code": "bad_index",
                    "error": "No such signal in this wig"}
        row_key, row_pronto, row_send_count = rows[index]

        from .wig_identity import wig_signal_identity

        ident = wig_signal_identity(row_pronto)
        if ident is None:
            return {"success": False, "code": "bad_pronto",
                    "error": "This signal's Pronto code does not validate"}

        session = self._session(filename)
        session["emitter"] = emitter_entity_id
        session["emitter_platform"] = (
            self._platform_of(emitter_entity_id)
            or session["emitter_platform"]
        )
        if send_times is not None:
            used = max(1, min(int(send_times), MAX_SEND_COUNT))
            session["send_times"] = max(
                session.get("send_times") or 0, used
            )
            if username:
                draft = self._find_user_draft(wig, username)
                if draft is not None:
                    draft["send_times_used"] = max(
                        _read_send_times(draft) or 0,
                        session["send_times"],
                    )
                    self._pending[filename] = wig
                    self._schedule_write(filename)

        from .ir_command import build_command, build_decoded_command

        # Per-press protocol state: session-held extras (advanced each
        # press) override the file-derived ones, mirroring test_signal.
        # The wig file itself never stores decoded state.
        extras = session["extras"].get(index) or ident.decoded_extras
        ir_cmd = None
        if ident.decoded_fingerprint:
            ir_cmd = build_decoded_command(
                ident.decoded_protocol,
                ident.decoded_address,
                ident.decoded_command,
                repeat_count=0,
                decoded_extras=extras,
            )
        decoded_tx = ir_cmd is not None
        if ir_cmd is None:
            try:
                ir_cmd = build_command(
                    protocol="PRONTO", code=ident.pronto,
                    frequency=ident.frequency,
                )
            except ValueError as exc:
                return {"success": False, "code": "no_signal_data",
                        "error": str(exc)}

        heard_future: asyncio.Future[str | None] = (
            asyncio.get_running_loop().create_future()
        )
        label = f"Fitting send: {row_key}" if row_key else "Fitting send"
        self._monitor.record_send(
            ir_cmd, label, [emitter_entity_id],
            decoded_fingerprint=ident.decoded_fingerprint,
            heard_future=heard_future,
        )

        from homeassistant.components.infrared import (
            async_send_command as ir_send,
        )

        from .const import ASSIGN_SERVICE_TIMEOUT_S, SEND_REPEAT_GAP
        from .tx_gate import gated_send

        # The session control substitutes for the row's own send_count
        # when set (fine-tuned-fittings). THIS call's value drives the
        # loop -- the monotonic session record above is what gets
        # claimed, but a fitter who lowered the control back to 1
        # genuinely sends once.
        send_count = max(
            1, min(send_times or row_send_count or 1, MAX_SEND_COUNT)
        )
        try:
            for i in range(send_count):
                if i:
                    await asyncio.sleep(SEND_REPEAT_GAP)
                await asyncio.wait_for(
                    gated_send(
                        self._hass, emitter_entity_id, ir_cmd, ir_send
                    ),
                    timeout=ASSIGN_SERVICE_TIMEOUT_S,
                )
        except (TimeoutError, asyncio.CancelledError):
            return {"success": False, "code": "send_timeout",
                    "error": "Emitter timed out"}
        except Exception as exc:
            return {"success": False, "code": "send_failed",
                    "error": f"Emitter did not respond: {exc}"}

        # One fitting send is one logical press: advance RC-5-family
        # toggle / Dyson counter state in the session so consecutive
        # sends are always fresh (GH #33 machinery, session-scoped).
        if decoded_tx and extras:
            advanced = dict(extras)
            if "toggle" in advanced:
                advanced["toggle"] = int(advanced["toggle"]) ^ 1
            if "counter" in advanced:
                advanced["counter"] = (int(advanced["counter"]) + 1) & 0x3
            if advanced != extras:
                session["extras"][index] = advanced

        heard_receiver: str | None = None
        try:
            heard_receiver = await asyncio.wait_for(
                heard_future, FITTING_HEARD_WAIT_S
            )
        except (TimeoutError, asyncio.CancelledError):
            heard_future.cancel()
        heard = heard_receiver is not None or (
            heard_future.done() and not heard_future.cancelled()
        )
        if heard:
            session["heard"].add(row_key)
            if heard_receiver:
                session["receiver_platform"] = (
                    self._platform_of(heard_receiver)
                    or session["receiver_platform"]
                )
        return {
            "success": True,
            "heard": bool(heard),
            "decoded": decoded_tx,
        }

    # -- marks -----------------------------------------------------------

    async def async_mark(
        self, filename: str, index: int, verdict: str, username: str
    ) -> dict[str, Any]:
        """Record a per-row verdict into the user's draft fitting.

        The first mark creates the draft inside the wig file (13.3);
        every mark schedules a debounced write, so progress survives
        anything short of the disk itself. ``index`` addresses
        ``fitting_rows(wig)`` and the verdict lists store ROW KEYS --
        aliases for signal wigs (unchanged on disk), checklist cell
        keys for matrix wigs, both stable across installs because both
        derive purely from file content.
        """
        if verdict not in VERDICTS:
            return {"success": False, "code": "bad_verdict",
                    "error": f"verdict must be one of {VERDICTS}"}
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        rows = fitting_rows(wig)
        if not 0 <= index < len(rows):
            return {"success": False, "code": "bad_index",
                    "error": "No such signal in this wig"}
        row_key = rows[index][0]

        draft = await self._draft_for(wig, filename, username)
        confirmed = [k for k in draft["confirmed"] if k != row_key]
        failed = [k for k in draft["failed"] if k != row_key]
        if verdict == _VERDICT_WORKED:
            confirmed.append(row_key)
        elif verdict == _VERDICT_FAILED:
            failed.append(row_key)
        draft["confirmed"] = confirmed
        draft["failed"] = failed
        draft["date"] = _today()
        self._merge_session_evidence(filename, draft)

        self._pending[filename] = wig
        self._schedule_write(filename)

        keys = {key for key, _, _ in rows}
        return {
            "success": True,
            "confirmed": len(set(confirmed) & keys),
            "failed": len(set(failed) & keys),
            "total": len(rows),
            "perfect_ready": (
                not failed and keys <= set(confirmed)
            ),
        }

    async def _draft_for(
        self, wig: Wig, filename: str, username: str
    ) -> dict[str, Any]:
        """Find or create this user's draft against the CURRENT hash.

        Match order implements plan 5.1.4's merge rule (handle plus
        content hash yields ONE fitting that grows, never two ledger
        rows): an open draft first; failing that, the user's SIGNED
        fitting on the same hash is re-opened as a draft -- resuming a
        recorded partial continues it, and FINISH re-signs it. Handle
        matching is case-insensitive so signing as "DAB" still merges
        with the HA username "dab"; a genuinely different signing
        handle starts its own ledger row, which is correct -- the row
        belongs to the attester name on it.
        """
        current_hash = wig_content_hash(wig)
        raw_list = wig.extra.get(FITTINGS_KEY)
        if not isinstance(raw_list, list):
            raw_list = []
            wig.extra[FITTINGS_KEY] = raw_list
        candidates = [
            f for f in parse_fittings(wig).fittings
            if f.handle.strip().lower() == username.strip().lower()
            and f.content_hash == current_hash
        ]
        for fitting in candidates:
            if fitting.draft:
                return fitting.raw
        if candidates:
            reopened = candidates[-1].raw
            reopened["draft"] = True
            # The content is about to change; the old attestation no
            # longer covers it. FINISH re-signs (Section 14.2).
            reopened.pop("sig", None)
            reopened.pop("key", None)
            return reopened
        hair_version, ha_version = await self._versions()
        draft: dict[str, Any] = {
            "handle": username,
            "draft": True,
            "date": _today(),
            "content_hash": current_hash,
            "confirmed": [],
            "failed": [],
        }
        if hair_version:
            draft["hair_version"] = hair_version
        if ha_version:
            draft["ha_version"] = ha_version
        raw_list.append(draft)
        return draft

    def _merge_session_evidence(
        self, filename: str, draft: dict[str, Any]
    ) -> None:
        session = self._sessions.get(filename)
        if not session:
            return
        if session["emitter_platform"]:
            draft["emitter"] = session["emitter_platform"]
        if session["receiver_platform"]:
            draft["receiver"] = session["receiver_platform"]
        if session["heard"]:
            merged = set(draft.get("heard") or []) | session["heard"]
            draft["heard"] = sorted(merged)
        if session.get("send_times"):
            # Monotonic (owner ruling 2026-07-30): the record only ever
            # rises, so re-marking a row after lowering the control
            # cannot roll a tested-at-3 claim back down.
            draft["send_times_used"] = max(
                _read_send_times(draft) or 0, session["send_times"]
            )

    # -- finish / discard ------------------------------------------------

    async def async_finish(
        self,
        filename: str,
        username: str,
        handle: str | None,
        github: str | None,
        note: str | None,
        kind: str | None = None,
    ) -> dict[str, Any]:
        """Sign the draft: the attestation moment (State C).

        Removes the draft flag, collapses draft-only evidence, writes
        immediately, and reports the derived verdict. ``kind`` fills
        the WIG's kind when it has none (owner ruling 2026-07-27: the
        signing screen asks once, because a fitter demonstrably cares
        about this wig) -- it is a fact about the device, so it lives
        on the wig, never inside the fitting entry, and it sits
        outside the signals hash so setting it cannot invalidate the
        fitting being signed.
        """
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        draft = self._find_user_draft(wig, username)
        if draft is None:
            return {"success": False, "code": "no_draft",
                    "error": "No fitting in progress to record"}
        if kind and kind.strip() and not wig.kind:
            from .wig_format import kind_slug

            wig.kind = kind_slug(kind) or None
        self._merge_session_evidence(filename, draft)
        if handle and handle.strip():
            draft["handle"] = handle.strip()
        # Leading @ stripped: people naturally type "@name" (live bench,
        # 2026-07-27), but Tier 2 key lookups and the ledger's own @
        # prefix both want the bare handle.
        if github and github.strip().lstrip("@").strip():
            draft["github"] = github.strip().lstrip("@").strip()
        if note and note.strip():
            draft["note"] = note.strip()
        heard_list = draft.pop("heard", None)
        if heard_list:
            draft["signals_heard"] = len(heard_list)
        draft["date"] = _today()
        draft.pop("draft", None)

        # Sign the attestation (Section 14): per-install ed25519 key,
        # canonical form covers everything but the sig itself. A
        # signing failure records the fitting unsigned, never loses it.
        signed = False
        private_key = await self._private_key()
        if private_key is not None:
            from .fitting_signing import sign_fitting

            signed = sign_fitting(draft, private_key)

        self._pending[filename] = wig
        await self.async_flush(filename)

        fitting = _parse_entry(draft)
        complete = bool(
            fitting and fitting_is_complete(fitting, wig)
        )
        rows = fitting_rows(wig)
        keys = {key for key, _, _ in rows}
        return {
            "success": True,
            "state": "perfect" if complete else "partial",
            "confirmed": len(set(draft.get("confirmed", [])) & keys),
            "failed": len(set(draft.get("failed", [])) & keys),
            "total": len(rows),
            "signed": signed,
        }

    async def async_discard(
        self, filename: str, username: str
    ) -> dict[str, Any]:
        """Remove the user's in-progress draft; signed fittings stay."""
        wig = await self._load(filename)
        if wig is None:
            return {"success": False, "code": "wig_not_found",
                    "error": "Wig not found"}
        draft = self._find_user_draft(wig, username)
        if draft is None:
            return {"success": False, "code": "no_draft",
                    "error": "No fitting in progress to discard"}
        raw_list = wig.extra.get(FITTINGS_KEY)
        if isinstance(raw_list, list) and draft in raw_list:
            raw_list.remove(draft)
        if not raw_list:
            wig.extra.pop(FITTINGS_KEY, None)
        self._sessions.pop(filename, None)
        self._pending[filename] = wig
        await self.async_flush(filename)
        return {"success": True}

    def _find_user_draft(
        self, wig: Wig, username: str
    ) -> dict[str, Any] | None:
        """The user's most recent draft, any hash (finish/discard target).

        Unlike mark, finish and discard do not require the current hash:
        if the codes changed mid-session the draft is stale either way,
        and the user's explicit action should still land on it.
        """
        candidates = [
            f.raw for f in parse_fittings(wig).fittings
            if f.draft and f.handle.strip().lower() == username.strip().lower()
        ]
        return candidates[-1] if candidates else None

    # -- the debounced writer -------------------------------------------

    def _schedule_write(self, filename: str) -> None:
        timer = self._timers.pop(filename, None)
        if timer is not None:
            timer.cancel()

        def _fire() -> None:
            self._timers.pop(filename, None)
            self._hass.async_create_task(self.async_flush(filename))

        self._timers[filename] = self._hass.loop.call_later(
            FITTING_WRITE_DEBOUNCE_S, _fire
        )

    async def async_flush(self, filename: str | None = None) -> None:
        """Write pending marks now. With no argument, flush everything.

        Every other wig-file writer calls this first (wigs/update,
        delete, download), so a debounced fitting write can never land
        on top of a newer edit.
        """
        names = (
            [filename] if filename is not None else list(self._pending)
        )
        for name in names:
            timer = self._timers.pop(name, None)
            if timer is not None:
                timer.cancel()
            wig = self._pending.pop(name, None)
            if wig is None:
                continue
            text = serialize_wig(wig)

            def _write(name: str = name, text: str = text) -> None:
                from .wig_store import safe_wig_filename, wigs_dir

                if not safe_wig_filename(name):
                    return
                path = wigs_dir(self._hass.config.config_dir) / name
                if not path.is_file():
                    return  # deleted mid-session; do not resurrect
                path.write_text(text, encoding="utf-8")

            try:
                await self._hass.async_add_executor_job(_write)
            except OSError as err:
                _LOGGER.warning(
                    "Could not write fitting progress to %s: %s", name, err
                )

    async def async_shutdown(self) -> None:
        """Flush everything; called from unload and HA stop."""
        await self.async_flush()
