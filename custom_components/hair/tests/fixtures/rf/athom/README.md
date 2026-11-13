# Radio captures from a fixed 433.92 MHz receiver

An ESPHome `remote_receiver` on a 433.92 MHz receiver module (original ESP32, `rmt_symbols: 64`, `tolerance: 50%`), at the `filter` and `idle` in each file's name. Each file is gzipped JSON:

- `filter_us`, `idle_us` (and `filter_symbols` where set): the receiver settings.
- `captures`: `[seconds, timings]` pairs in arrival order. `seconds` counts from the file's first capture at **1-second resolution**, so captures inside one second keep their order but not their spacing. `timings` are signed microseconds (mark positive) with the receiver's idle appended as the last value, which is what the API path delivers.

The receiver ends a capture at every inter-frame gap of these remotes, so a press arrives as one capture per frame, with the module's noise between presses.

| File | What it is |
|---|---|
| `athom-433-150us-6ms-noise-1h.json.gz` | One hour of noise, nobody pressing anything: 11,857 captures |
| `athom-433-150us-6ms-fs20-noise-1h.json.gz` | The same, with `filter_symbols: 20`: 16,237 captures |
| `athom-433-it104-100us-4ms-presses.json.gz` | DEWENWILS IT104 keyfob: 1 ON, 1 OFF, ALL ON, 2 OFF, 3 OFF, several presses each |
| `athom-433-it104-150us-4ms-presses.json.gz` | 1 ON, 1 OFF, ALL OFF, 2 OFF, 3 OFF, three presses each |
| `athom-433-it104-250us-4ms-presses.json.gz` | 1 ON, 1 OFF, ALL ON, 2 OFF, 3 ON, three presses each |
| `athom-433-it104-150us-6ms-presses.json.gz` | 1 ON, 1 OFF, ALL ON, 2 OFF, 3 ON, three presses each |
| `athom-433-it104-150us-12ms-presses.json.gz` | 1 ON, 1 OFF, ALL ON, 2 ON, 3 ON, three presses each |
| `athom-433-it104-150us-6ms-fs20-joint-presses.json.gz` | `filter_symbols: 20`; 1 ON and 1 OFF several times, then ALL ON and ALL OFF; the same presses as the RM4 pro file |
| `rm4pro-433-it104-joint-presses.json.gz` | The same presses heard by a Broadlink RM4 pro: 25 `0xB1` packets at 433.92 MHz, decoded pulses (unsigned, mark first), `t` in seconds from the first |

The keyfob's codes (24-bit EV1527 class, address `0x950E4`): 1 ON `49`, 1 OFF `41`, 2 ON `4B`, 2 OFF `43`, 3 ON `4D`, 3 OFF `45`, ALL ON `4F`, ALL OFF `47`, as the low byte.
