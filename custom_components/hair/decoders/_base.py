"""Base-class import shim for the local decoder package.

Every decoder module imports ``Command`` from here so the package works
both with the real ``infrared_protocols`` library (normal runtime, Python
3.13+) and without it (the Python 3.12 CI leg, where HAIR's test stubs
stand in). When a module is donated upstream, this import collapses to
``from . import Command`` -- the only line that changes.
"""
from __future__ import annotations

try:
    from infrared_protocols.commands import Command
except ImportError:  # test environment without infrared_protocols
    import abc

    class Command(abc.ABC):  # type: ignore[no-redef]
        """Minimal stand-in matching infrared_protocols.commands.Command."""

        repeat_count: int
        modulation: int

        def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
            self.modulation = modulation
            self.repeat_count = repeat_count

        @abc.abstractmethod
        def get_raw_timings(self) -> list[int]:
            """Get raw timings as signed microsecond integers."""


__all__ = ["Command"]
