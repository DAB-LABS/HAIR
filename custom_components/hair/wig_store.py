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

from .wig_format import MAX_WIG_BYTES, WIG_SUFFIX, Wig, parse_wig

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
