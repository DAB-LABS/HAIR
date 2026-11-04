# Radio frequency fixtures

Real radio captures, kept so the frame rules in `rf_frames.py` can be
re-checked rather than believed.

| File | What it is |
|---|---|
| `it104-keyfob-433.json` | 30 captures of an IT104 four-button 433.92 MHz keyfob (EV1527, address `0x950E4`), read by BroadSniff 0.3.0 on an RM4 Pro on the VM999 bench, 2026-11-03. Each capture is one 0xB1 packet: 500 durations (one is 1,000, one is 498), unsigned, mark first, the last value the RM4 Pro's fixed tail of about 45.7 ms. |

What the captures show, and what `test_rf_frames.py` pins:

- Every normal capture holds 8 whole frames of 49 body edges plus the
  gap (about 12.9 ms), a 2-edge lead, a frame cut by the capture's end,
  and one frame split in two by the RM4 Pro's buffer seam (the duration
  at index 249, and at 499 and 749 in the long capture, is a data space
  stretched to about 4.5 ms).
- Seven distinct codes: buttons 1 (`1001`), 2 (`0011`), 3 (`0101`) and
  ALL (`1111`), and three codes from presses the fob sent part of
  (`1011`, `0001`, `0111`). All seven share the address, so they are one
  card.
- The last value of a capture is never a gap.
