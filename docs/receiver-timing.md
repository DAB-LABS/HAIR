# Receiver timing for ESPHome IR receivers

Every ESP32 config in [`esphome/`](../esphome/) sets two values on its `remote_receiver`:

```yaml
remote_receiver:
  clock_resolution: 400000
  idle: 80ms
```

This page explains what they do, why these two numbers, and what else works if your remotes need something different.

## What `idle` does

A receiver hands over a capture once the line has been silent for `idle`. ESPHome's default is 10 ms. That suits TV remotes, whose frames are short and whose gaps between frames are long, but an air conditioner sends one press as several frames with short silences between them: a Daikin press carries about 35 ms of silence in the middle of it, and Mitsubishi Electric 144-bit remotes leave 11 to 17 ms between their two frames. At 10 ms the receiver closes the capture inside those gaps, so one press arrives as two or three codes, and HAIR sees each piece as a different signal.

Raising `idle` above the longest gap inside a message fixes that. The cost of going too high is the reverse: hold a button down and the repeats start arriving as one long capture instead of separate presses. HAIR's decoders split a merged capture back into frames, so a value comfortably above the gap is a safe place to sit.

## The hardware ceiling

On the ESP32 family the receiver is the RMT peripheral, and it times silence with a counter that has a fixed maximum: 32,767 ticks on the ESP32-C3, S3, C6 and H2, and 65,535 ticks on the original ESP32 and the S2. ESPHome's default receiver clock is 1 MHz, one tick per microsecond, so the longest `idle` it accepts is about 32 ms on a C3 or S3 and 65 ms on an original ESP32. Ask for more and `esphome config` stops with:

```
config 'idle' exceeds the maximum value of 32767us.
```

On an original ESP32 the number in the message is `65535us`. HAIR's configs set `idle: 100ms` from 0.15.0 until this was fixed, so on current ESPHome every ESP32 config that set it failed validation.

## Why `clock_resolution` is the lever

ESPHome scales that ceiling by the receiver clock: a slower clock means longer ticks, and the same 32,767 ticks cover more time. At 500,000 Hz the C3 ceiling is 65 ms, at 250,000 Hz it is 131 ms. The validator checks only that ceiling, and two things it does not check rule out most values.

**ESPHome converts ticks to microseconds with whole numbers.** The conversion in `esphome/components/remote_base/remote_base.h` is:

```cpp
const uint32_t ticks_per_ten_us = this->clock_resolution_ / 100000u;
return (ticks * 10) / ticks_per_ten_us;
```

Only multiples of 100,000 Hz divide evenly. At 250,000 Hz the first line gives 2 ticks per 10 us where the truth is 2.5, so every mark and space is reported 25 percent too long: a 560 us NEC mark arrives as 700 us, right at the edge of the receiver's own tolerance, and HAIR would store and replay the stretched timings. The validator accepts such a value without a word.

**The original ESP32 cannot divide its receiver clock below 312,500 Hz.** Each receive channel divides the 80 MHz APB clock by at most 256 (ESP-IDF v5.5, `hal/esp32/include/hal/rmt_ll.h`). Anything under 80 MHz / 256 = 312,500 Hz asks for a divider the hardware does not have, and the board either stops at boot on a failed check or runs the receiver at a different speed from the one ESPHome assumes.

**On the C3 and S3 the clock is shared.** Every RMT channel on these chips runs from one group clock. An LED strip driven by `esp32_rmt_led_strip` starts before the receiver and sets that clock to the full 80 MHz, so the receiver is held to the same divider limit of 256 and the same 312,500 Hz floor; below it, the receiver fails to start and the log shows `channel prescale out of the range`. On a board without an LED strip the receiver starts first and lower values work, but they break the day someone adds one.

## The chosen pair: 400000 and 80 ms

400,000 Hz is a multiple of 100,000, so timings convert exactly, with a tick of 2.5 us. It divides 80 MHz by 200, so it is legal on every ESP32 whatever else shares the clock. The ceiling becomes 81.9 ms on the C3, S3, C6 and H2, and 163.8 ms on the original ESP32 and the S2.

80 ms sits under the lower of those, so one value works on every board, and it clears the longest air-conditioner gap we know of (Daikin, about 35 ms) by more than double. A 2.5 us tick is around 1 percent of the shortest pulses HAIR decodes.

## Alternatives

| clock_resolution | idle up to | Boards | Use when |
|---|---|---|---|
| 1000000 (ESPHome default) | 30ms | every ESP32 | flat remotes only, no air conditioner: finest timing, held buttons split into separate presses soonest |
| 500000 | 65ms | every ESP32 | 2 us ticks, and every gap in your remotes is well under 65 ms (Athom's own config for its RF IR Remote ships 500000 with 65.5 ms) |
| 400000 (shipped) | 80ms | every ESP32 | the default |
| 400000 | 160ms | original ESP32 and S2 only | an air-conditioner press still arrives as two codes at 80 ms |

Keep `idle` and `clock_resolution` together: raise `idle` on its own and the validator stops with the error above, lower `clock_resolution` to a value that is not on this list and the traps above apply.

Two other settings help in particular rooms and do not touch the clock:

- `filter: 200us` for a noisy room: LED strips, direct sunlight or a plasma TV near the receiver. The default is 50us. Pulses shorter than the filter are dropped before the capture is handed over.
- `tolerance: 40%` for a weak or distant signal: a long cable, a cheap receiver module, a handset across the room. It loosens how far a pulse may stray before ESPHome's own decoders give up, which shows in the `dump:` log, in `on_nec`-style triggers and in ESPHome's climate IR. HAIR reads the raw timings and is not affected by it.

## Checking a config

From the folder that holds your YAML and its `secrets.yaml`:

```
esphome config your-device.yaml
```

It reads the file the way a build would, without compiling or flashing anything, and ends with `INFO Configuration is valid!` when every value is accepted. It cannot see the two traps above, which only show on the device, so stay with the values on this page.

These numbers were checked against the validator and source code of ESPHome 2026.9.1 and against ESP-IDF v5.5. They have not yet been run on a bench.
