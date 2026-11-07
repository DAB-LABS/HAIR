"""G.I. Cable: the format of General Instrument (later Motorola) cable boxes.

The IRP definition, from IrpProtocols.xml (the protocol database the
JP1 and DecodeIR community maintains), read for its facts only::

    {38.7k,490}<1,-4.5|1,-9>(18,-9,F:8,D:4,C:4,1,-84,(18,-4.5,1,-178)*)
    {C = -(D + F:4 + F:4:4)} [D:0..15,F:0..255]

- 38.7 kHz carrier and a 490 us unit.
- Pulse distance, least significant bit first: a 1-unit mark, then a
  4.5-unit space for 0 or a 9-unit space for 1.
- An 18-unit mark and 9-unit space lead in. Then F in 8 bits, D in 4
  bits and a 4-bit check C, a closing mark and an 84-unit lead-out.
- C is minus the sum of D and F's two nibbles, kept to four bits.
- A held button sends the frame once and then a ditto (18, -4.5, 1,
  -178) for as long as it is held, so a repeat here is a ditto, not the
  frame again.
"""
from __future__ import annotations

from typing import override

from ..decoders._base import Command
from . import bits_lsb, check_range, pulse_distance

_UNIT_US = 490
_MARK_US = _UNIT_US
_ZERO_US = 2205        # 4.5 units
_ONE_US = 9 * _UNIT_US
_LEADER_MARK_US = 18 * _UNIT_US
_LEADER_SPACE_US = 9 * _UNIT_US
_LEADOUT_US = 84 * _UNIT_US
_DITTO = (18 * _UNIT_US, -2205, _UNIT_US, -178 * _UNIT_US)
_MODULATION_HZ = 38700


def check_nibble(device: int, function: int) -> int:
    """C = -(D + F:4 + F:4:4), kept to four bits."""
    return -(device + (function & 0x0F) + (function >> 4)) & 0x0F


class GICableCommand(Command):
    """G.I. Cable IR command, encode only."""

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

        :param device: D, 0 to 15
        :param function: F, 0 to 255
        :param repeat_count: dittos sent after the frame
        """
        check_range("device", device, 15)
        check_range("function", function, 0xFF)
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.function = function

    @override
    def get_raw_timings(self) -> list[int]:
        """The frame, then one ditto per repeat."""
        bits = [
            *bits_lsb(self.function, 8),
            *bits_lsb(self.device, 4),
            *bits_lsb(check_nibble(self.device, self.function), 4),
        ]
        timings = [_LEADER_MARK_US, -_LEADER_SPACE_US]
        timings += pulse_distance(bits, _MARK_US, _ZERO_US, _ONE_US)
        timings += [_MARK_US, -_LEADOUT_US]
        for _ in range(self.repeat_count):
            timings += _DITTO
        return timings
