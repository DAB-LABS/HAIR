"""The replay check for rolling-code presses.

A rolling-code remote (KeeLoq, Somfy RTS) changes part of its code on
every press. HAIR files such a press by its fixed part, so a recording of
one earlier press would otherwise look like a fresh press of that button
and fire its triggers. This check drops the simplest replay:

- **KeeLoq:** a press whose encrypted word equals one of the last few seen
  for that button.
- **Somfy RTS:** a press whose counter is not ahead of the last one seen
  for that remote: the same counter, or one behind it. One Somfy remote
  shares one counter across its buttons, so it is kept per remote. The
  counter is 16 bits and wraps, so "ahead" is up to half its range. A press
  far ahead (a remote pressed many times out of range) is accepted and
  moves the memory on: a recording of an earlier press is always behind
  the newest one seen, so this never lets a replay through, and a remote
  can't get stuck.

It runs once per press (a voted burst), never per frame: a press repeats
its own word, and the repeats must not refuse the press.

The memory is in this process only: never stored, shown or logged. A
restart empties it, so the first replay after a restart is let through.
A KeeLoq seed word (all four buttons, sent to pair a receiver) repeats by
design and is never checked.
"""
from __future__ import annotations

import collections
import hashlib
from typing import Any

# How many recent KeeLoq words are kept per button.
KEELOQ_RECENT = 8
# The Somfy counter's size, and how far ahead still counts as ahead.
_SOMFY_MODULO = 1 << 16
_SOMFY_AHEAD_MAX = _SOMFY_MODULO // 2 - 1
# How many remotes the memory keeps before it forgets the oldest.
MAX_REMOTES = 512


def _digest(value: int) -> bytes:
    return hashlib.sha256(value.to_bytes(8, "little", signed=False)).digest()[:8]


class RollingReplay:
    """Per-remote memory of the rolling parts seen, for one HAIR instance."""

    def __init__(self) -> None:
        self._keeloq: collections.OrderedDict[
            tuple[str, str], collections.deque[bytes]
        ] = collections.OrderedDict()
        self._somfy: collections.OrderedDict[str, int] = collections.OrderedDict()

    def accept(self, identity: Any) -> bool:
        """Whether a press is new, recording it when it is.

        ``identity`` is an ``rf_family.RollingIdentity``. A press with no
        rolling part to read, or a family this check does not know, is
        accepted.
        """
        rolling = getattr(identity, "rolling", None)
        if rolling is None or getattr(identity, "seed", False):
            return True
        if identity.family == "keeloq":
            return self._accept_keeloq((identity.remote, identity.button), rolling)
        if identity.family == "somfy_rts":
            return self._accept_somfy(identity.remote, rolling)
        return True

    def _accept_keeloq(self, key: tuple[str, str], rolling: int) -> bool:
        word = _digest(rolling)
        seen = self._keeloq.get(key)
        if seen is None:
            seen = collections.deque(maxlen=KEELOQ_RECENT)
            self._keeloq[key] = seen
            self._trim(self._keeloq)
        elif word in seen:
            return False
        seen.append(word)
        self._keeloq.move_to_end(key)
        return True

    def _accept_somfy(self, remote: str, counter: int) -> bool:
        last = self._somfy.get(remote)
        if last is not None:
            ahead = (counter - last) % _SOMFY_MODULO
            if not 1 <= ahead <= _SOMFY_AHEAD_MAX:
                return False
        self._somfy[remote] = counter
        self._somfy.move_to_end(remote)
        self._trim(self._somfy)
        return True

    @staticmethod
    def _trim(memory: collections.OrderedDict) -> None:
        while len(memory) > MAX_REMOTES:
            memory.popitem(last=False)
