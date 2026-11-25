"""The wig closet: ``/config/hair/wigs/`` folder and on-demand scan.

Storage decisions restated from the plan (wigs.md section 4): the
folder lives OUTSIDE ``custom_components/hair/`` because HACS replaces
that directory wholesale on update; it is created on integration setup
if missing; scanning happens on demand (tab open, picker open), never
on a watcher, so a file dropped over SSH or Samba appears on the next
open with no restart. Invalid files are surfaced with their validation
reasons, not hidden: a malformed file is a support conversation the UI
should have for us.

Everything here does blocking file I/O. Callers on the event loop run
these through the executor (the same posture as the pluckable registry
load in ``__init__``).

The scan keeps what it made of each file, keyed on the file's size,
modification time, change time and inode, and re-reads only a file
whose stat has changed. Every call still lists the folder and stats every file, so a
file dropped, edited or removed outside HA is picked up on the next
call exactly as before; what the cache saves is re-validating the
files that did not change, which on a closet of large climate wigs is
nearly all of the scan's time. HAIR's own writers also forget the file
they wrote, so a rewrite that lands inside one filesystem timestamp
tick is never served stale.

What ``scan_wigs`` hands back is shared with the cache: callers read
it and never change it. A path that changes a wig loads its own copy
with ``load_wig``, which always reads the file.

``scan_wigs`` and ``forget_wig`` take a lock and do file I/O: call
them from the executor, never on the event loop.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from .wig_format import (
    MAX_WIG_BYTES,
    WIG_SUFFIX,
    Wig,
    parse_wig,
    wig_filename,
)

_LOGGER = logging.getLogger(__name__)

WIGS_DIRNAME = "hair/wigs"


@dataclass
class LoadedWig:
    """A valid wig and where it came from."""

    path: Path
    wig: Wig


@dataclass
class InvalidWig:
    """A file that failed validation, with every reason found."""

    path: Path
    errors: list[str]


@dataclass
class WigScan:
    """One scan of the closet."""

    wigs: list[LoadedWig]
    invalid: list[InvalidWig]


# What the scan made of each file, by closet folder, then filename:
# the stat it was made from, and the LoadedWig or InvalidWig. Only a
# file that was read and parsed is kept; one that could not be read is
# tried again next time.
_FileStamp = tuple[int, int, int, int]
_SCAN_CACHE: dict[Path, dict[str, tuple[_FileStamp, LoadedWig | InvalidWig]]] = {}
# One scan at a time: two cold scans arriving together would otherwise
# both validate every file, and the validation is CPU-bound Python that
# only takes turns under the GIL. The second waits and finds the
# first's work in the cache.
_SCAN_LOCK = threading.Lock()


def _stamp(path: Path) -> _FileStamp:
    # ctime as well as mtime: a copy that keeps the modification time
    # (cp -p, rsync -t, a restore) still moves the change time, and
    # nothing can set that back.
    st = path.stat()
    return (st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)


def forget_wig(config_dir: str | Path, filename: str) -> None:
    """Drop one file from the scan cache, after HAIR writes or deletes it."""
    with _SCAN_LOCK:
        entries = _SCAN_CACHE.get(wigs_dir(config_dir))
        if entries is not None:
            entries.pop(filename, None)


def clear_scan_cache() -> None:
    """Forget every cached scan result."""
    with _SCAN_LOCK:
        _SCAN_CACHE.clear()


def wigs_dir(config_dir: str | Path) -> Path:
    """The wig folder under the HA config directory."""
    return Path(config_dir) / WIGS_DIRNAME


def ensure_wigs_dir(config_dir: str | Path) -> Path:
    """Create the wig folder (and ``hair/``) if missing; return it."""
    path = wigs_dir(config_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_wig_text(
    config_dir: str | Path, text: str, name_hint: str
) -> str | None:
    """Validate wig JSON ``text`` and write it into the closet.

    Returns the filename written, or None when validation fails (the
    caller reports reasons via ``parse_wig`` itself -- this helper only
    refuses). The ORIGINAL text is written byte-for-byte, not a
    re-serialization: an uploaded wig carrying keys this HAIR does not
    know (a newer install's fittings, say) must survive untouched.
    Filenames slugify from ``name_hint`` and dodge existing files.
    """
    result = parse_wig(text)
    if not result.ok:
        return None
    directory = ensure_wigs_dir(config_dir)
    taken = {p.name for p in directory.glob(f"*{WIG_SUFFIX}")}
    filename = wig_filename(name_hint, taken)
    (directory / filename).write_text(text, encoding="utf-8")
    forget_wig(config_dir, filename)
    return filename


def delete_wig(config_dir: str | Path, filename: str) -> bool:
    """Delete one wig by closet filename. False when refused/missing."""
    if not safe_wig_filename(filename):
        return False
    path = wigs_dir(config_dir) / filename
    try:
        if not path.is_file():
            return False
        path.unlink()
        forget_wig(config_dir, filename)
        return True
    except OSError as err:
        _LOGGER.warning("Could not delete wig file %s: %s", path, err)
        return False


def read_wig_text(config_dir: str | Path, filename: str) -> str | None:
    """Raw file text for download/copy-JSON, or None."""
    if not safe_wig_filename(filename):
        return None
    path = wigs_dir(config_dir) / filename
    try:
        if not path.is_file() or path.stat().st_size > MAX_WIG_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def safe_wig_filename(filename: str) -> bool:
    """True when ``filename`` is a plain closet filename.

    The guard every WS entry point shares: must carry the wig suffix,
    must be a bare name (no path separators, no traversal), must not be
    hidden. Rejecting here keeps ``load_wig``/``delete`` from ever
    touching a path outside the closet.
    """
    return (
        filename.endswith(WIG_SUFFIX)
        and "/" not in filename
        and "\\" not in filename
        and not filename.startswith(".")
        and filename == Path(filename).name
    )


def load_wig(config_dir: str | Path, filename: str) -> Wig | None:
    """Load and validate one wig by closet filename, or None."""
    if not safe_wig_filename(filename):
        return None
    path = wigs_dir(config_dir) / filename
    try:
        if not path.is_file() or path.stat().st_size > MAX_WIG_BYTES:
            return None
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        _LOGGER.warning("Could not read wig file %s: %s", path, err)
        return None
    result = parse_wig(text)
    return result.wig if result.ok else None


def scan_wigs(config_dir: str | Path) -> WigScan:
    """Read and validate every ``*.wig.json`` in the closet.

    Files are returned in name order so the scan is deterministic. A
    file that cannot be read at all (permissions, vanished mid-scan)
    joins the invalid list rather than raising: one bad file never
    hides the rest of the closet.

    A file whose size, modification time, change time and inode match
    the last scan is not read again; its earlier result is reused (see the module
    docstring). The returned objects are shared with that cache and
    must not be changed.
    """
    directory = wigs_dir(config_dir)
    wigs: list[LoadedWig] = []
    invalid: list[InvalidWig] = []
    with _SCAN_LOCK:
        if not directory.is_dir():
            _SCAN_CACHE.pop(directory, None)
            return WigScan(wigs, invalid)
        entries = _SCAN_CACHE.setdefault(directory, {})
        seen: set[str] = set()
        for path in sorted(directory.glob(f"*{WIG_SUFFIX}")):
            seen.add(path.name)
            outcome = _scan_one(path, entries)
            if isinstance(outcome, LoadedWig):
                wigs.append(outcome)
            else:
                invalid.append(outcome)
        for gone in set(entries) - seen:
            del entries[gone]
    return WigScan(wigs, invalid)


def _scan_one(
    path: Path,
    entries: dict[str, tuple[_FileStamp, LoadedWig | InvalidWig]],
) -> LoadedWig | InvalidWig:
    """One file's scan result, from the cache when its stat is unchanged."""
    try:
        before = _stamp(path)
    except OSError as err:
        entries.pop(path.name, None)
        _LOGGER.warning("Could not read wig file %s: %s", path, err)
        return InvalidWig(path, [f"could not read file: {err}"])
    cached = entries.get(path.name)
    if cached is not None and cached[0] == before:
        return cached[1]
    outcome: LoadedWig | InvalidWig
    if before[0] > MAX_WIG_BYTES:
        outcome = InvalidWig(path, [
            f"file exceeds the {MAX_WIG_BYTES // 1_000_000} MB "
            "wig size cap"
        ])
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            entries.pop(path.name, None)
            _LOGGER.warning("Could not read wig file %s: %s", path, err)
            return InvalidWig(path, [f"could not read file: {err}"])
        result = parse_wig(text)
        outcome = (
            LoadedWig(path, result.wig) if result.ok
            else InvalidWig(path, result.errors)
        )
    # Keep the result only if the file did not change while it was read;
    # otherwise the next scan reads it again.
    try:
        after = _stamp(path)
    except OSError:
        after = None
    if after == before:
        entries[path.name] = (before, outcome)
    else:
        entries.pop(path.name, None)
    return outcome


def find_wig_by_id(config_dir: str | Path, wig_id: str) -> str | None:
    """The closet filename holding a given ``wig_id``, or None.

    A device remembers the wig it was adopted from by IDENTITY, never by
    filename, because the file is free to be renamed, re-downloaded, or
    replaced by a shop copy of the same wig; the id survives all three.
    This is the lookup that turns that memory back into a file when the
    person hits SAVE TO CLOSET.

    Scans rather than indexes: an index would be one more thing that can
    disagree with the disk. The scan's own cache re-checks every file's
    stat, so this stays exact and costs little when nothing changed.
    """
    if not wig_id:
        return None
    for loaded in scan_wigs(config_dir).wigs:
        if loaded.wig.wig_id == wig_id:
            return loaded.path.name
    return None


def backfill_wig_id(config_dir: str | Path, filename: str) -> str | None:
    """Give a closet wig an identity if it has none, in place.

    Returns the id -- existing or freshly minted -- or None if the file
    will not load.

    Files written before v0.9.5 have no ``wig_id``. Upload mints one on
    the way in, but a wig that was already sitting in the closet never
    passes through that path, and without an id a device adopted from
    it has nothing to remember: SAVE TO CLOSET would offer to mint a
    second copy of a wig the closet already holds.

    Minting in memory alone would be worse than not minting: the device
    would carry an id the file does not, and the two would never agree
    again. So this writes the file back, once, and every later adopt is
    a no-op read.
    """
    wig = load_wig(config_dir, filename)
    if wig is None:
        return None
    if wig.wig_id:
        return wig.wig_id
    from .wig_format import serialize_wig

    text = serialize_wig(wig)  # mints as a side effect, by design
    path = wigs_dir(config_dir) / filename
    path.write_text(text, encoding="utf-8")
    forget_wig(config_dir, filename)
    return wig.wig_id
