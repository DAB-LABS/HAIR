"""Global Cache ``sendir`` codes: one parser for both import doors.

A ``sendir`` command is how a Global Cache iTach, GC-100 or Flex is told
to send infrared, and it is what Control Tower (Global Cache's code
database) mails out, both for a whole code set and for a single code::

    sendir,<module>:<port>,<id>,<frequency>,<repeat>,<offset>,<on1>,<off1>,...

The paste box, the Closet's code-set reader and Tasmota's ``IRsend gc,``
all read the same body, so it is parsed here once.

ON AND OFF ARE COUNTS OF CARRIER PERIODS, NOT MICROSECONDS. A 38 kHz code
whose leader is ``342,171`` is 9.0 ms of carrier and 4.5 ms of silence.
Each count becomes ``round(count * 1e6 / frequency)`` microseconds and
the code is rendered at its own frequency, so the stored Pronto carries
the carrier the file declared.

THE LIMITS ARE GLOBAL CACHE'S OWN (iTach API 1.5, section 5.4.6): a
frequency of 15 000 to 500 000 Hz, an odd offset from 1 to 383, every
count from 1 to 65 535, and fewer than 260 on/off pairs. A code outside
them is one the hardware refuses, so it is refused here with the reason,
never trimmed to fit. Repeats above 50 are accepted, as the hardware
accepts them, and sent 50 times there.

THE COMPRESSED FORM. An iTach that learns a code may write each of the
first fifteen distinct on/off pairs once and then refer back to it by a
capital letter, A to O, with no comma: ``4,5A8,9ABB`` is
``4,5,4,5,8,9,4,5,8,9,8,9``. Both forms are the same code.

ONE SEND, STORED ONCE. ``repeat`` and ``offset`` say how a Global Cache
device repeats the code while a key is held: the whole list once, then
the pairs from ``offset`` onward ``repeat - 1`` more times. HAIR stores
the whole list once (which is exactly one send at repeat 1, what every
Control Tower export carries) and its own send count decides repeats, so
a repeat above 1 is reported to the caller to name rather than baked in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MIN_FREQUENCY = 15_000
MAX_FREQUENCY = 500_000
MAX_OFFSET = 383
MAX_COUNT = 65_535
MAX_PAIRS = 259  # "N is less than 260 or a total of 520 numbers"
MAX_REPEAT_SENT = 50

_LETTERS = "ABCDEFGHIJKLMNO"
_HEAD = re.compile(r"^\s*sendir\s*,", re.IGNORECASE)
_TOKEN = re.compile(r"\d+|[A-O]|,|\s+")


class SendirError(ValueError):
    """A sendir code the hardware would refuse, in plain words."""


@dataclass(frozen=True)
class Sendir:
    """One parsed code: its carrier, its repeat rule and its counts."""

    frequency: int
    repeat: int
    offset: int
    counts: tuple[int, ...]

    @property
    def pairs(self) -> int:
        return len(self.counts) // 2

    def timings(self) -> list[int]:
        """Signed microseconds: marks positive, spaces negative."""
        return [
            round(count * 1_000_000 / self.frequency) * (1 if i % 2 == 0 else -1)
            for i, count in enumerate(self.counts)
        ]

    def pronto(self) -> str:
        from .ir_command import raw_to_pronto

        return raw_to_pronto(self.timings(), frequency=self.frequency)


def is_sendir(text: str) -> bool:
    """Does this text start like a sendir command?"""
    return bool(_HEAD.match(text or ""))


def parse_sendir(text: str) -> Sendir:
    """Parse ``sendir,<m>:<p>,<id>,<freq>,<repeat>,<offset>,...``."""
    if not is_sendir(text):
        raise SendirError("not a sendir code")
    body = _HEAD.sub("", text.strip(), count=1)
    head, _, rest = body.partition(",")
    if not re.fullmatch(r"\s*\d+\s*:\s*\d+\s*", head):
        raise SendirError(
            f"the connector address {head.strip()!r} is not module:port"
        )
    ident, _, rest = rest.partition(",")
    if not ident.strip().isdigit():
        raise SendirError(f"the id {ident.strip()!r} is not a number")
    return parse_sendir_body(rest)


def parse_sendir_body(body: str) -> Sendir:
    """Parse ``<freq>,<repeat>,<offset>,<on1>,<off1>,...``.

    This is the part Tasmota's ``IRsend gc,`` carries as well.
    """
    fields = body.strip().strip(",").split(",", 3)
    if len(fields) < 4:
        raise SendirError("too short: no on/off counts after the offset")
    frequency = _number(fields[0], "frequency")
    repeat = _number(fields[1], "repeat")
    offset = _number(fields[2], "offset")
    counts = _expand(fields[3])
    if not MIN_FREQUENCY <= frequency <= MAX_FREQUENCY:
        raise SendirError(
            f"a frequency of {frequency} Hz is outside "
            f"{MIN_FREQUENCY}-{MAX_FREQUENCY} Hz"
        )
    if repeat < 1:
        raise SendirError("a repeat of 0 sends nothing")
    if len(counts) % 2:
        raise SendirError("an odd number of on/off values")
    if len(counts) // 2 > MAX_PAIRS:
        raise SendirError(
            f"too long for sendir ({len(counts) // 2} pairs, "
            f"the limit is {MAX_PAIRS})"
        )
    if not counts:
        raise SendirError("no on/off counts")
    if offset < 1 or offset > MAX_OFFSET or offset % 2 == 0:
        raise SendirError(
            f"an offset of {offset} is not an odd number from 1 to {MAX_OFFSET}"
        )
    if offset > len(counts):
        raise SendirError(
            f"the offset {offset} points past the last of {len(counts)} values"
        )
    zero = [i for i, count in enumerate(counts) if count == 0]
    if zero:
        raise SendirError("a count of 0 is not valid")
    if any(count > MAX_COUNT for count in counts):
        raise SendirError(f"a count above {MAX_COUNT} is not valid")
    return Sendir(frequency, repeat, offset, tuple(counts))


def _number(text: str, what: str) -> int:
    text = text.strip()
    if not text.isdigit():
        raise SendirError(f"the {what} {text!r} is not a number")
    return int(text)


def _expand(text: str) -> list[int]:
    """The on/off counts, with any compressed letters expanded."""
    pos = 0
    values: list[int] = []
    pending: list[int] = []
    known: list[tuple[int, int]] = []
    text = text.strip()
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None:
            raise SendirError(f"unexpected {text[pos]!r} in the counts")
        token = match.group(0)
        pos = match.end()
        if token == "," or token.isspace():
            continue
        if token.isdigit():
            pending.append(int(token))
            if len(pending) == 2:
                pair = (pending[0], pending[1])
                if pair not in known and len(known) < len(_LETTERS):
                    known.append(pair)
                values.extend(pair)
                pending = []
            continue
        if pending:
            raise SendirError(
                f"the letter {token} interrupts an on/off pair"
            )
        index = _LETTERS.index(token)
        if index >= len(known):
            raise SendirError(
                f"the letter {token} names a pair the code has not given yet"
            )
        values.extend(known[index])
    values.extend(pending)
    return values
