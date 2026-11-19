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
design and is never checked. A button held down repeats its own rolling
part; that is one press, dropped quietly, not a replay (``HELD``).
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
# The same rolling part again within this many seconds of when it was
# last heard is one press held down, not a replay.
HELD_S = 2.0


def _digest(value: int) -> bytes:
    return hashlib.sha256(value.to_bytes(8, "little", signed=False)).digest()[:8]


# What the check says about a press.
NEW = "new"  # a press not heard before: it goes on
HELD = "held"  # more of a press just heard (a button held down): dropped quietly
REPLAY = "replay"  # an earlier press played back: dropped, and said so


class RollingReplay:
    """Per-remote memory of the rolling parts seen, for one HAIR instance."""

    def __init__(self) -> None:
        # Per KeeLoq button: the recent words, and when the newest one was
        # last heard.
        self._keeloq: collections.OrderedDict[
            tuple[str, str], tuple[collections.deque[bytes], float]
        ] = collections.OrderedDict()
        # Per Somfy remote: the last counter, and when it was last heard.
        self._somfy: collections.OrderedDict[str, tuple[int, float]] = (
            collections.OrderedDict()
        )

    def check(self, identity: Any, now: float) -> str:
        """``NEW``, ``HELD`` or ``REPLAY`` for one press, recording it.

        ``identity`` is an ``rf_family.RollingIdentity`` and ``now`` a
        monotonic time in seconds. A press with no rolling part to read, a
        seed word, or a family this check does not know is ``NEW``.

        The same rolling part again within ``HELD_S`` of when it was last
        heard is one press held down: a held KeeLoq button repeats its word
        (with RPT set after the first), and a held Somfy button its
        counter, and the receiver can deliver them as separate bursts.
        """
        rolling = getattr(identity, "rolling", None)
        if rolling is None or getattr(identity, "seed", False):
            return NEW
        if identity.family == "keeloq":
            return self._check_keeloq((identity.remote, identity.button), rolling, now)
        if identity.family == "somfy_rts":
            return self._check_somfy(identity.remote, rolling, now)
        return NEW

    def _check_keeloq(self, key: tuple[str, str], rolling: int, now: float) -> str:
        word = _digest(rolling)
        entry = self._keeloq.get(key)
        if entry is None:
            seen: collections.deque[bytes] = collections.deque(maxlen=KEELOQ_RECENT)
        else:
            seen, heard_at = entry
            if seen and seen[-1] == word and now - heard_at < HELD_S:
                self._keeloq[key] = (seen, now)
                return HELD
            if word in seen:
                return REPLAY
        seen.append(word)
        self._keeloq[key] = (seen, now)
        self._keeloq.move_to_end(key)
        self._trim(self._keeloq)
        return NEW

    def _check_somfy(self, remote: str, counter: int, now: float) -> str:
        entry = self._somfy.get(remote)
        if entry is not None:
            last, heard_at = entry
            if counter == last and now - heard_at < HELD_S:
                self._somfy[remote] = (last, now)
                return HELD
            ahead = (counter - last) % _SOMFY_MODULO
            if not 1 <= ahead <= _SOMFY_AHEAD_MAX:
                return REPLAY
        self._somfy[remote] = (counter, now)
        self._somfy.move_to_end(remote)
        self._trim(self._somfy)
        return NEW

    @staticmethod
    def _trim(memory: collections.OrderedDict) -> None:
        while len(memory) > MAX_REMOTES:
            memory.popitem(last=False)
