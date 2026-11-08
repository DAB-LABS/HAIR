"""Panasonic_Old: the 22-bit format of older Panasonic and Quasar sets.

The IRP definition, from IrpProtocols.xml (the protocol database the
JP1 and DecodeIR community maintains) and the same in DecodeIR's
protocol reference, read for its facts only::

    {57.6k,833}<1,-1|1,-3>(4,-4,D:5,F:6,~D:5,~F:6,1,-44m)* [D:0..31,F:0..63]

- 57.6 kHz carrier and an 833 us unit.
- Pulse distance, least significant bit first: a 1-unit mark, then a
  1-unit space for 0 or a 3-unit space for 1.
- A 4-unit mark and 4-unit space lead in. Then D in 5 bits, F in 6
  bits, and both again inverted, a closing mark and a 44 ms lead-out.
- A held button repeats the whole frame. The inverted half is the only
  check, and the reference gives no other.
"""
from __future__ import annotations

from typing import override

from ..decoders._base import Command
from . import bits_lsb, check_range, pulse_distance

_UNIT_US = 833
_MARK_US = _UNIT_US
_ZERO_US = _UNIT_US
_ONE_US = 3 * _UNIT_US
_LEADER_US = 4 * _UNIT_US
_LEADOUT_US = 44000
_MODULATION_HZ = 57600


class PanasonicOldCommand(Command):
    """Panasonic_Old IR command, encode only."""

    device: int
    function: int

    def __init__(
        self,
        *,
        device: int,
        function: int,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the command.

        :param device: D, 0 to 31
        :param function: F, 0 to 63
        """
        check_range("device", device, 31)
        check_range("function", function, 63)
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.function = function

    @override
    def get_raw_timings(self) -> list[int]:
        """One frame, and the frame again for each repeat."""
        bits = [
            *bits_lsb(self.device, 5),
            *bits_lsb(self.function, 6),
            *bits_lsb(~self.device & 0x1F, 5),
            *bits_lsb(~self.function & 0x3F, 6),
        ]
        frame = [_LEADER_US, -_LEADER_US]
        frame += pulse_distance(bits, _MARK_US, _ZERO_US, _ONE_US)
        frame += [_MARK_US, -_LEADOUT_US]
        return frame * (1 + self.repeat_count)
