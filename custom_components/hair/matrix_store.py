"""Per-device climate matrix files: ``hair/matrices/<device_id>.matrix.json``.

Cold Cuts (v0.8.8). A matrix lives as its OWN file, never inside the
devices JSON, because storage.py rewrites the whole devices blob on
every ``async_update_device`` and the census worst case is a 7.9 MB
matrix (owner-accepted addendum 2.3): renaming a device must never
re-serialize megabytes of Pronto. The folder sits beside
``hair/wigs/`` -- outside ``custom_components/hair/`` so a HACS update
cannot wipe it, created on first write rather than at setup because
matrices are machine-managed, not a user drop zone.

The reference is implicit: the file is named by the device id and the
device carries only a ``climate_matrix`` boolean, so device payloads
stay cheap and a matrix can never orphan-point at a wrong device.

File shape: ``{"format": "hair-matrix/1", "climate": {...}}`` where
the climate object is byte-compatible with the hair-wig/2 climate
block. wig_format owns both the parser and the serializer -- one
schema, one authority, no fork.

Everything here does blocking file I/O. Callers on the event loop run
these through the executor (the wig_store posture).
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from .wig_format import (
    MAX_WIG_BYTES,
    ClimateMatrix,
    _climate_out,
    _parse_climate,
)

_LOGGER = logging.getLogger(__name__)

MATRICES_DIRNAME = "hair/matrices"
MATRIX_SUFFIX = ".matrix.json"

MATRIX_FORMAT_NAME = "hair-matrix"
MATRIX_FORMAT_MAJOR = 1
MATRIX_FORMAT_V1 = f"{MATRIX_FORMAT_NAME}/{MATRIX_FORMAT_MAJOR}"


def matrices_dir(config_dir: str | Path) -> Path:
    """The matrix folder under the HA config directory."""
    return Path(config_dir) / MATRICES_DIRNAME


def ensure_matrices_dir(config_dir: str | Path) -> Path:
    """Create the matrix folder (and ``hair/``) if missing; return it."""
    path = matrices_dir(config_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_device_id(device_id: str) -> bool:
    """True when ``device_id`` can safely name a file in the folder.

    Device ids are uuid4 strings HAIR minted itself, so anything else
    here is a bug or an attack; the same bare-name posture as
    ``safe_wig_filename`` keeps every path inside the folder.
    """
    return bool(
        device_id
        and "/" not in device_id
        and "\\" not in device_id
        and not device_id.startswith(".")
        and device_id == Path(device_id).name
    )


def _matrix_path(config_dir: str | Path, device_id: str) -> Path | None:
    if not _safe_device_id(device_id):
        return None
    return matrices_dir(config_dir) / f"{device_id}{MATRIX_SUFFIX}"


INDEX_SUFFIX = ".index.json"


def matrix_path(config_dir: str | Path, owner_id: str) -> Path | None:
    """The matrix file for a device or remote id, or None if unsafe."""
    return _matrix_path(config_dir, owner_id)


def index_path(config_dir: str | Path, owner_id: str) -> Path | None:
    """The built cell index that sits BESIDE that matrix file.

    Same folder, same id, different suffix: deriving identity for a
    lattice is seconds of decode work on a large file (signpost 4,
    Track M), and it is the same answer every boot, so the listener
    caches it on disk. The index names the matrix it was built from by
    content hash, so a stale one can never be believed.
    """
    if not _safe_device_id(owner_id):
        return None
    return matrices_dir(config_dir) / f"{owner_id}{INDEX_SUFFIX}"


def matrix_content_hash(config_dir: str | Path, owner_id: str) -> str | None:
    """A cheap content tag for the matrix file: size and sha256."""
    path = _matrix_path(config_dir, owner_id)
    if path is None:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    import hashlib

    return f"{len(raw)}:{hashlib.sha256(raw).hexdigest()[:32]}"


def write_matrix(
    config_dir: str | Path, device_id: str, matrix: ClimateMatrix
) -> None:
    """Write one device's matrix file, creating the folder if needed.

    Compact JSON, not the wig's 4-space indent: these files are
    machine-managed (nobody hand-edits a 2,689-cell lattice) and the
    census worst case is large enough that pretty-printing costs real
    megabytes. Raises ``ValueError`` on an unsafe device id (a
    programmer error, never user input) and lets ``OSError`` propagate
    so the caller can refuse honestly instead of half-creating a
    device.
    """
    path = _matrix_path(config_dir, device_id)
    if path is None:
        raise ValueError(f"Unsafe device id for matrix file: {device_id!r}")
    ensure_matrices_dir(config_dir)
    text = json.dumps(
        {"format": MATRIX_FORMAT_V1, "climate": _climate_out(matrix)},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    path.write_text(text + "\n", encoding="utf-8")


def load_matrix(
    config_dir: str | Path, device_id: str
) -> ClimateMatrix | None:
    """Load one device's matrix, or None on ANY problem.

    Missing file, unreadable file, wrong format, newer major, schema
    errors: all None with a log receipt. The climate entity treats a
    None matrix as "matrix not available" and refuses sends rather
    than guessing, so this helper never half-loads.
    """
    path = _matrix_path(config_dir, device_id)
    if path is None:
        return None
    try:
        if not path.is_file() or path.stat().st_size > MAX_WIG_BYTES:
            return None
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        _LOGGER.warning("Could not read matrix file %s: %s", path, err)
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        _LOGGER.warning("Matrix file %s is not valid JSON: %s", path, err)
        return None
    if not isinstance(data, dict):
        _LOGGER.warning("Matrix file %s: top level is not an object", path)
        return None
    fmt = data.get("format")
    if fmt != MATRIX_FORMAT_V1:
        # Same posture as the wig gate: a future major refuses politely
        # instead of guessing at a schema this install does not know.
        _LOGGER.warning(
            "Matrix file %s has format %r, expected %r",
            path, fmt, MATRIX_FORMAT_V1,
        )
        return None
    errors: list[str] = []
    matrix = _parse_climate(data.get("climate"), errors)
    if errors or matrix is None:
        _LOGGER.warning(
            "Matrix file %s failed validation: %s", path, "; ".join(errors)
        )
        return None
    return matrix


def delete_matrix(config_dir: str | Path, device_id: str) -> bool:
    """Delete one device's matrix file. False when refused or missing."""
    path = _matrix_path(config_dir, device_id)
    if path is None:
        return False
    try:
        if not path.is_file():
            delete_cell_index(config_dir, device_id)
            return False
        path.unlink()
        delete_cell_index(config_dir, device_id)
        return True
    except OSError as err:
        _LOGGER.warning("Could not delete matrix file %s: %s", path, err)
        return False


def write_cell_index(
    config_dir: str | Path, owner_id: str, payload: dict
) -> bool:
    """Write the built index beside the matrix. False on any problem.

    Best-effort by design: a missing or unwritable index costs a
    rebuild, never a wrong answer.
    """
    path = index_path(config_dir, owner_id)
    if path is None:
        return False
    try:
        ensure_matrices_dir(config_dir)
        path.write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8"
        )
        return True
    except (OSError, TypeError, ValueError) as err:
        _LOGGER.debug("Could not write cell index %s: %s", path, err)
        return False


def load_cell_index(config_dir: str | Path, owner_id: str) -> dict | None:
    """Read the built index, or None when absent or unreadable."""
    path = index_path(config_dir, owner_id)
    if path is None:
        return None
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        _LOGGER.debug("Could not read cell index %s: %s", path, err)
        return None
    return data if isinstance(data, dict) else None


def delete_cell_index(config_dir: str | Path, owner_id: str) -> bool:
    """Remove a stale index file. False when absent or refused."""
    path = index_path(config_dir, owner_id)
    if path is None:
        return False
    try:
        if not path.is_file():
            return False
        path.unlink()
        return True
    except OSError:
        return False


def copy_matrix(config_dir: str | Path, src_id: str, dst_id: str) -> bool:
    """Byte-copy one device's matrix file to another id (device clone).

    A byte copy, not a parse-and-rewrite: the clone must transmit
    exactly what its source transmits. False when the source is
    missing, either id is unsafe, or the copy fails.
    """
    src = _matrix_path(config_dir, src_id)
    dst = _matrix_path(config_dir, dst_id)
    if src is None or dst is None or not src.is_file():
        return False
    try:
        ensure_matrices_dir(config_dir)
        shutil.copyfile(src, dst)
        return True
    except OSError as err:
        _LOGGER.warning(
            "Could not copy matrix file %s -> %s: %s", src, dst, err
        )
        return False
