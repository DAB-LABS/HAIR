"""RECS80: the Philips format of older Philips, Thomson and Nokia sets.

The IRP definition, from IrpProtocols.xml (the protocol database the
JP1 and DecodeIR community maintains), read for its facts only::

    {38k,158,msb}<1,-31|1,-47>(1:1,T:1,D:3,F:6,1,-45m)* [D:0..7,F:0..63,T@:0..1=0]

- 38 kHz carrier and a 158 us unit.
- Pulse distance, most significant bit first: a 1-unit mark, then a
  31-unit space for 0 or a 47-unit space for 1.
- No leader: a start bit that is always 1, the toggle T, D in 3 bits,
  F in 6 bits, a closing mark and a 45 ms lead-out.
- T flips on each new press and stays put while a button is held. A
  stored code is one press, so it is built with T = 0, the IRP's
  default, as HAIR builds RC5's and RC6's toggle.
"""
from __future__ import annotations

from typing import override

from ..decoders._base import Command
from . import bits_msb, check_range, pulse_distance

_UNIT_US = 158
_MARK_US = _UNIT_US
_ZERO_US = 31 * _UNIT_US
_ONE_US = 47 * _UNIT_US
_LEADOUT_US = 45000
_MODULATION_HZ = 38000


class RECS80Command(Command):
    """RECS80 IR command, encode only."""

    device: int
    function: int
    toggle: int

    def __init__(
        self,
        *,
        device: int,
        function: int,
        toggle: int = 0,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the command.

        :param device: D, 0 to 7
        :param function: F, 0 to 63
        :param toggle: T, 0 or 1
        """
        check_range("device", device, 7)
        check_range("function", function, 63)
        check_range("toggle", toggle, 1)
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.function = function
        self.toggle = toggle

    @override
    def get_raw_timings(self) -> list[int]:
        """One frame, and the frame again (same toggle) for each repeat."""
        bits = [
            1, self.toggle,
            *bits_msb(self.device, 3),
            *bits_msb(self.function, 6),
        ]
        frame = pulse_distance(bits, _MARK_US, _ZERO_US, _ONE_US)
        frame += [_MARK_US, -_LEADOUT_US]
        return frame * (1 + self.repeat_count)
