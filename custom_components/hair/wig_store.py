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
"""
from __future__ import annotations

import logging
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
    """
    directory = wigs_dir(config_dir)
    wigs: list[LoadedWig] = []
    invalid: list[InvalidWig] = []
    if not directory.is_dir():
        return WigScan(wigs, invalid)
    for path in sorted(directory.glob(f"*{WIG_SUFFIX}")):
        try:
            if path.stat().st_size > MAX_WIG_BYTES:
                invalid.append(InvalidWig(path, [
                    f"file exceeds the {MAX_WIG_BYTES // 1_000_000} MB "
                    "wig size cap"
                ]))
                continue
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            _LOGGER.warning("Could not read wig file %s: %s", path, err)
            invalid.append(InvalidWig(path, [f"could not read file: {err}"]))
            continue
        result = parse_wig(text)
        if result.ok:
            wigs.append(LoadedWig(path, result.wig))
        else:
            invalid.append(InvalidWig(path, result.errors))
    return WigScan(wigs, invalid)
