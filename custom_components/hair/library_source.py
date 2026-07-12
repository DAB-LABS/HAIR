"""LibrarySource — the built-in infrared-protocols codebook provider.

This is the ORIGINAL introspection-based code library, behaviourally
unchanged. It is now exposed as one *source* among several behind the Add
Remote picker (see ``library.py``), sitting alongside ``CustomYamlSource``.

Two things changed versus the standalone module it used to be:

* Every id it emits is prefixed ``lib:`` so the dispatcher can route a
  materialize call back to the right source. Internally it still speaks the
  proven ``module:Class:MEMBER`` id format — the prefix is stripped at the
  boundary — so unprefixed legacy ids keep resolving too.
* ``available()`` now returns True only when at least one real codebook is
  discovered, not merely when the package imports (reviewer point 7).

The database itself is the ``codes/`` package inside the infrared-protocols
library. We discover every enum codebook (any ``enum.Enum`` whose members
expose ``to_command()``), normalize it to a brand -> codebook -> function
tree, and materialize a chosen entry into a Pronto string plus its decoded
protocol identity for the Clipper to store. A missing or restructured
library degrades to an empty tree, never a crash.
"""
from __future__ import annotations

import enum
import importlib
import logging
import os
import re
from typing import Any

from .const import DECODED_FINGERPRINT_FORMAT
from .ir_command import raw_to_pronto

_LOGGER = logging.getLogger(__name__)

_CODES_PKG = "infrared_protocols.codes"

#: Id prefix that tags every id this source produces, so the dispatcher in
#: ``library.py`` can route it back here. See also ``CustomYamlSource``.
PREFIX = "lib"
_PREFIX_STR = f"{PREFIX}:"


def _strip(identifier: str) -> str:
    """Remove the ``lib:`` routing prefix if present (legacy ids have none)."""
    return identifier[len(_PREFIX_STR):] if identifier.startswith(_PREFIX_STR) else identifier


def _humanize_member(name: str) -> str:
    """``POWER_ON`` -> ``Power On``."""
    return name.replace("_", " ").strip().title() or name


def _humanize_brand(key: str) -> str:
    """``lg`` -> ``LG``; ``sony`` -> ``Sony``."""
    if not key:
        return key
    return key.upper() if len(key) <= 3 else key.replace("_", " ").title()


def _humanize_codebook(class_name: str) -> str:
    """``LGTVCode`` -> ``LGTV``; ``SonyPlayStation2Code`` -> ``Sony Play Station 2``.

    Strips a trailing ``Code`` and inserts spaces at camelCase and
    letter/digit boundaries. Acronym runs (``LGTV``) stay joined, which is
    acceptable for a dropdown label.
    """
    name = class_name
    if name.endswith("Code"):
        name = name[: -len("Code")]
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    name = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", name)
    return name.strip() or class_name


def _brand_of(module_name: str) -> str:
    """Brand key = the path segment right after ``codes.``."""
    tail = module_name[len(_CODES_PKG) + 1 :]
    return tail.split(".")[0] if tail else module_name


def _iter_codebooks():
    """Yield ``(module_name, enum_class)`` for each codebook enum, de-duped.

    A codebook is any ``enum.Enum`` subclass, defined in the module it is
    found in, that exposes a callable ``to_command`` and has at least one
    member. Re-exported enums are skipped via the ``__module__`` check and
    an identity set.

    Discovery walks the codes package on the filesystem rather than via
    ``pkgutil.walk_packages``: the library ships its per-brand directories
    (``codes/lg/``, ``codes/sony/``, ...) WITHOUT an ``__init__.py``, so the
    pkgutil walker does not descend into them. The ``.py`` files still
    import cleanly as implicit-namespace submodules, so a direct filesystem
    walk plus ``import_module`` finds every codebook.
    """
    try:
        pkg = importlib.import_module(_CODES_PKG)
    except Exception:
        return
    seen: set[int] = set()
    for root_path in list(getattr(pkg, "__path__", [])):
        for dirpath, _dirs, files in os.walk(root_path):
            rel = os.path.relpath(dirpath, root_path)
            parts = [] if rel == os.curdir else rel.split(os.sep)
            for fname in sorted(files):
                if not fname.endswith(".py") or fname == "__init__.py":
                    continue
                module_name = ".".join(
                    [_CODES_PKG, *parts, fname[: -len(".py")]]
                )
                try:
                    mod = importlib.import_module(module_name)
                except Exception:
                    continue
                for obj in vars(mod).values():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, enum.Enum)
                        and getattr(obj, "__module__", None) == module_name
                        and callable(getattr(obj, "to_command", None))
                        and len(obj) > 0
                        and id(obj) not in seen
                    ):
                        seen.add(id(obj))
                        yield module_name, obj


def _get_tree() -> list[dict[str, Any]]:
    """Return the brand -> codebook -> function tree for the picker.

    Each brand: ``{brand, label, codebooks: [...]}``. Each codebook:
    ``{id, label, functions: [{id, name}]}``. Ids are stable
    ``lib:module:Class`` / ``lib:module:Class:MEMBER`` strings the import
    endpoints resolve back to library objects.
    """
    brands: dict[str, dict[str, Any]] = {}
    for module, cls in _iter_codebooks():
        brand_key = _brand_of(module)
        brand = brands.setdefault(
            brand_key,
            {"brand": brand_key, "label": _humanize_brand(brand_key), "codebooks": []},
        )
        functions = [
            {
                "id": f"{_PREFIX_STR}{module}:{cls.__name__}:{member.name}",
                "name": _humanize_member(member.name),
            }
            for member in cls
        ]
        brand["codebooks"].append(
            {
                "id": f"{_PREFIX_STR}{module}:{cls.__name__}",
                "label": _humanize_codebook(cls.__name__),
                "functions": functions,
            }
        )
    result = sorted(brands.values(), key=lambda b: b["label"].lower())
    for brand in result:
        brand["codebooks"].sort(key=lambda c: c["label"].lower())
    return result


def _codebook_label(codebook_id: str) -> str | None:
    """Human label for a codebook id, e.g. for a default remote name."""
    try:
        _module, class_name = _strip(codebook_id).split(":")
    except ValueError:
        return None
    return _humanize_codebook(class_name)


def _resolve_member(module: str, class_name: str, member_name: str):
    try:
        mod = importlib.import_module(module)
        cls = getattr(mod, class_name)
        return cls[member_name]
    except Exception:
        return None


def _to_command(member):
    """Call ``to_command`` defensively across the library's varying shapes."""
    try:
        return member.to_command()
    except TypeError:
        try:
            return member.to_command(repeat_count=0)
        except Exception:
            return None
    except Exception:
        return None


def _decoded_fields(command) -> dict[str, Any]:
    """Derive ``decoded_*`` from a Command, or all-None when unavailable.

    Protocol family is the Command class name minus the ``Command`` suffix
    (``NECCommand`` -> ``NEC``). Address and command must both be ints to
    form the fingerprint; otherwise the entry stays Pronto-only.
    """
    protocol = type(command).__name__.removesuffix("Command") or None
    address = getattr(command, "address", None)
    cmd = getattr(command, "command", None)
    if protocol and isinstance(address, int) and isinstance(cmd, int):
        return {
            "decoded_protocol": protocol,
            "decoded_address": int(address),
            "decoded_command": int(cmd),
            "decoded_fingerprint": DECODED_FINGERPRINT_FORMAT.format(
                protocol=protocol, address=int(address), command=int(cmd)
            ),
        }
    return {
        "decoded_protocol": None,
        "decoded_address": None,
        "decoded_command": None,
        "decoded_fingerprint": None,
    }


def _materialize_member(member) -> dict[str, Any] | None:
    """Turn one enum member into a Clipper-ready entry, or None on failure."""
    command = _to_command(member)
    if command is None:
        return None
    try:
        timings = list(command.get_raw_timings())
        modulation = int(getattr(command, "modulation", 0) or 0) or 38000
        code = raw_to_pronto(timings, frequency=modulation)
    except Exception:
        return None
    return {"name": _humanize_member(member.name), "code": code, **_decoded_fields(command)}


def _materialize_function(function_id: str) -> dict[str, Any] | None:
    """Materialize a single function id into a Clipper entry, or None."""
    try:
        module, class_name, member_name = _strip(function_id).split(":")
    except ValueError:
        return None
    member = _resolve_member(module, class_name, member_name)
    if member is None:
        return None
    return _materialize_member(member)


def _materialize_codebook(
    codebook_id: str, function_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Materialize a whole codebook (or a subset of its functions).

    Returns a list of Clipper entries (``{name, code, decoded_*}``). Entries
    that fail to materialize are skipped, so a single bad code never breaks
    the import. An unknown codebook returns an empty list.
    """
    try:
        module, class_name = _strip(codebook_id).split(":")
    except ValueError:
        return []
    try:
        mod = importlib.import_module(module)
        cls = getattr(mod, class_name)
    except Exception:
        return []
    wanted: set[str] | None = None
    if function_ids:
        wanted = set()
        for fid in function_ids:
            parts = _strip(fid).split(":")
            if len(parts) == 3:
                wanted.add(parts[2])
    entries: list[dict[str, Any]] = []
    for member in cls:
        if wanted is not None and member.name not in wanted:
            continue
        entry = _materialize_member(member)
        if entry is not None:
            entries.append(entry)
    return entries


def _available() -> bool:
    """True only if at least one real codebook is discoverable.

    Reviewer point 7: importing the package is not enough — there must be
    actual codes. We short-circuit on the first codebook found.
    """
    for _module, _cls in _iter_codebooks():
        return True
    return False


class LibrarySource:
    """Adapter exposing the infrared-protocols library as a code source."""

    #: Routing prefix used by the ``library.py`` dispatcher.
    prefix = PREFIX

    def available(self) -> bool:
        return _available()

    def get_tree(self) -> list[dict[str, Any]]:
        return _get_tree()

    def codebook_label(self, codebook_id: str) -> str | None:
        return _codebook_label(codebook_id)

    def materialize_function(self, function_id: str) -> dict[str, Any] | None:
        return _materialize_function(function_id)

    def materialize_codebook(
        self, codebook_id: str, function_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        return _materialize_codebook(codebook_id, function_ids)
