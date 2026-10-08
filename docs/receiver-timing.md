# Receiver timing for ESPHome IR receivers

**If you flashed one of HAIR's ESPHome configs, you don't need to change anything on this page.** The settings it describes are already in them.

An air conditioner remote doesn't send one quick blip the way a TV remote does. One press is a long message, often sent in two or three pieces with short pauses in between. Out of the box, ESPHome takes the first pause as the end of the message and stops listening, and it only has room for about two thirds of the longest presses. So HAIR was getting part of a button press and treating it as a different button. If you ever saw one air conditioner button show up as two or three different codes, this was why.

The configs fix both problems: the receiver waits a little longer before it decides a press is over, and it has room to hold the whole thing. On a real Athom board, a Daikin press that used to get cut off now arrives in one piece.

## Building your own config?

Then these lines need to go in your `remote_receiver`, whatever else your config does. Without them, air conditioner presses get chopped up or cut short:

```yaml
remote_receiver:
  clock_resolution: 400000
  idle: 80ms
  receive_symbols: 384      # every ESP32
  rmt_symbols: 384          # original ESP32 only; leave this line out on any other chip
```

A few cases are different. If your board is an original ESP32 that also has an RF receiver and transmitter, like the Athom RF IR Remote, use 320 instead of 384 for both buffer lines, so the RF side keeps enough room to work (the [Athom full config](../esphome/athom-rf-ir-remote/) shows how). An ESP32-S2 cannot hold the longest presses at all; the receive buffer section below explains why. And if you want to change any of these numbers, read the rest of this page first: most other values look fine when you check the config, then misbehave on the device.

## From my barber 💈

You don't need any of this to use the lines above. It's here for anyone who wants to know why each line is there, or needs to change one. The short version of each section is the bold line at the top.

### What `idle` does

**In plain terms: `idle` is how long the receiver waits in silence before it decides you're done pressing.**

A receiver hands over a capture once the line has been silent for `idle`. ESPHome's default is 10 ms. That suits TV remotes, whose frames are short and whose gaps between frames are long, but an air conditioner sends one press as several frames with short silences between them: a Daikin press carries about 35 ms of silence in the middle of it, and Mitsubishi Electric 144-bit remotes leave 11 to 17 ms between their two frames. At 10 ms the receiver closes the capture inside those gaps, so one press arrives as two or three codes, and HAIR sees each piece as a different signal.

Raising `idle` above the longest gap inside a message fixes that. The cost of going too high is the reverse: hold a button down and the repeats start arriving as one long capture instead of separate presses. HAIR's decoders split a merged capture back into frames, so a value comfortably above the gap is a safe place to sit.

### The hardware ceiling

**In plain terms: the chip can only time a silence up to a fixed length, and ESPHome refuses any `idle` longer than that.**

On the ESP32 family the receiver is the RMT peripheral, and it times silence with a counter that has a fixed maximum: 32,767 ticks on the ESP32-C3, S3, C6 and H2, and 65,535 ticks on the original ESP32 and the S2. ESPHome's default receiver clock is 1 MHz, one tick per microsecond, so the longest `idle` it accepts is about 32 ms on a C3 or S3 and 65 ms on an original ESP32. Ask for more and `esphome config` stops with:

```
config 'idle' exceeds the maximum value of 32767us.
```

On an original ESP32 the number in the message is `65535us`. HAIR's configs set `idle: 100ms` from 0.15.0 until this was fixed, so on current ESPHome every ESP32 config that set it failed validation.

### Why `clock_resolution` is the lever

**In plain terms: the receiver measures time in ticks. Make each tick longer and the same count covers a longer silence, but only a few tick lengths are safe to use.**

ESPHome scales that ceiling by the receiver clock: a slower clock means longer ticks, and the same 32,767 ticks cover more time. At 500,000 Hz the C3 ceiling is 65 ms, at 250,000 Hz it is 131 ms. The validator checks only that ceiling, and two things it does not check rule out most values.

**ESPHome converts ticks to microseconds with whole numbers.** The conversion in `esphome/components/remote_base/remote_base.h` is:

```cpp
const uint32_t ticks_per_ten_us = this->clock_resolution_ / 100000u;
return (ticks * 10) / ticks_per_ten_us;
```

Only multiples of 100,000 Hz divide evenly. At 250,000 Hz the first line gives 2 ticks per 10 us where the truth is 2.5, so every mark and space is reported 25 percent too long: a 560 us NEC mark arrives as 700 us, right at the edge of the receiver's own tolerance, and HAIR would store and replay the stretched timings. The validator accepts such a value without a word.

**The original ESP32 cannot divide its receiver clock below 312,500 Hz.** Each receive channel divides the 80 MHz APB clock by at most 256 (ESP-IDF v5.5, `hal/esp32/include/hal/rmt_ll.h`). Anything under 80 MHz / 256 = 312,500 Hz asks for a divider the hardware does not have, and the board either stops at boot on a failed check or runs the receiver at a different speed from the one ESPHome assumes.

**On the C3, S3, C6 and H2 the clock is shared.** Every RMT channel on these chips runs from one group clock; only the original ESP32 and the S2 give each channel its own. An LED strip driven by `esp32_rmt_led_strip` starts before the receiver and sets that group clock to the chip's full RMT clock, 80 MHz on the C3, S3 and C6 and 32 MHz on the H2. The receiver is then held to the same divider limit of 256, which puts the floor at 312,500 Hz on the C3, S3 and C6 and 125,000 Hz on the H2. Below it, the receiver fails to start and the log shows `channel prescale out of the range`. On a board without an LED strip the receiver starts first and lower values work, but they break the day someone adds one.

### The chosen pair: 400000 and 80 ms

**In plain terms: 400,000 is the clock setting that keeps measurements accurate, works on every ESP32, and still lets the receiver wait long enough for an air conditioner.**

400,000 Hz is a multiple of 100,000, so the conversion has no scaling error: a tick is 2.5 us, and the whole-number arithmetic rounds a pulse down by at most half a microsecond. It divides an 80 MHz clock by 200 and the H2's 32 MHz clock by 80, so it is legal on every ESP32 whatever else shares the clock. The ceiling becomes 81.9 ms on the C3, S3, C6 and H2, and 163.8 ms on the original ESP32 and the S2.

80 ms sits under the lower of those, so one value works on every board, and it clears the longest air-conditioner gap we know of (Daikin, about 35 ms) by more than double. A 2.5 us tick is around 1 percent of the shortest pulses HAIR decodes.

### The receive buffer: `rmt_symbols` and `receive_symbols`

**In plain terms: the receiver has a fixed amount of room to hold one press. ESPHome's default is too small for the longest air conditioner presses, so the configs give it more.**

A capture is stored as RMT symbols, one mark and the space after it per symbol, so a capture can never hold more mark-and-space pairs than the receiver has room for. ESPHome's defaults hold 192, and that is not enough for several air conditioners. These are whole presses as HAIR's field packs store them; with `idle: 80ms` every frame of one press arrives in the same capture, so the whole press is what has to fit:

| Family | Pairs in one press |
|---|---|
| Daikin 152 | 293 |
| Mitsubishi Electric 144 | 292 |
| TCL 112 | 228 |
| Daikin 216, Panasonic 216 | 220 |
| Mitsubishi Heavy 160 and every other family HAIR reads | 162 or fewer |

Across 80,642 distinct air conditioner codes in the public SmartIR code collections, the longest press of any family HAIR reads is 294 pairs. 21,112 codes need more than 192, 395 need more than 320, and 1 needs more than 384.

On a receiver that runs out of room, the capture simply stops: the rest of the press is lost, nothing shows in the log at ESPHome's default level, and HAIR receives a code that ends partway through a frame. A test receiver on an original ESP32 with ESPHome's defaults cut every capture at 193 pairs, so not one whole Daikin 152, Panasonic 216 or TCL 112 press arrived.

Which setting decides the limit depends on the chip:

- **On the original ESP32 and the S2, the limit is the receiver's share of the RMT memory, `rmt_symbols`.** These chips cannot move received symbols out of the RMT memory while a capture is still arriving, so a capture ends when that memory is full. `receive_symbols` has to be at least as large.
- **On the S3, C3, C6 and H2, the limit is `receive_symbols`.** These chips copy the RMT memory into the receive buffer in halves while the capture arrives, so `rmt_symbols` only sets the size of those halves and the capture can be as long as the buffer. Leave `rmt_symbols` at its default there.

`receive_symbols` is a slot in ordinary RAM, 4 bytes per symbol, so 384 takes about 1.5 KB. ESPHome carves it out of the receiver's existing capture buffer (`buffer_size`, 10,000 bytes on the ESP32), so the board does not need more memory unless that buffer was made smaller.

`rmt_symbols` is different: it comes out of RMT memory every RMT channel on the chip shares, and it is the reason the original ESP32 needs care.

| Chip | RMT memory | Receive limit | Room for a receiver |
|---|---|---|---|
| Original ESP32 | 512 symbols, 8 blocks of 64, shared by every transmitter, receiver and RMT LED strip | `rmt_symbols` | 448 with one IR transmitter; the configs use 384 |
| ESP32-S2 | 256 symbols, 4 blocks of 64, shared | `rmt_symbols` | 192 with one transmitter, which cannot hold the longest presses at all |
| ESP32-S3 | 4 receive blocks of 48 | `receive_symbols` | as large as `receive_symbols` |
| ESP32-C3, C6, H2 | 2 receive blocks of 48 | `receive_symbols` | as large as `receive_symbols` |

ESPHome's defaults give each transmitter 64 symbols on the original ESP32 and S2 (48 on the others), each receiver 192 (96 on the C3, C6 and H2), and an RMT LED strip 192 (96 on the C3, C6 and H2). A receiver takes whole blocks, and they have to be next to each other.

**The cost on a board that does IR and RF.** The Athom RF IR Remote is an original ESP32 with two transmitters and two receivers, one each for IR and 433 MHz RF. At ESPHome's defaults those four channels already use all 512 symbols: 64 + 64 + 192 + 192. Its full config gives the IR receiver 320, which holds every family above, and pays for it by cutting the RF receiver to 64: 64 + 64 + 64 + 320 = 512. A 433 MHz remote's code is about 25 pairs, so 64 holds it at least twice over. On a board like this, the IR receiver can only grow by taking blocks from something else.

**When it does not fit.** If the channels ask for more RMT memory than the chip has, `esphome config` still passes: the check happens on the device when it boots. The receiver that could not get its memory does not start, and its log line reads `Configuring RMT driver failed: ESP_ERR_NOT_FOUND (out of RMT symbol memory)`. On an original ESP32, `rmt_symbols` must also be even and at least 64.

**The chosen values.**

- 384 on every board that can afford it. It holds every family HAIR reads with room to spare, and all but one of the 80,642 codes above.
- 320 on the IR receiver of the Athom full config, the most it can have while the RF receiver keeps one block. It still holds every family HAIR reads, and all but 395 of those codes.
- On the original ESP32 both settings get the number. On the S3, C3, C6 and H2 only `receive_symbols` does.

### Alternatives

**In plain terms: if the shipped values don't suit your remotes or your board, these are the other combinations that are safe.**

| clock_resolution | idle up to | Boards | Use when |
|---|---|---|---|
| 1000000 (ESPHome default) | 32ms | every ESP32 | flat remotes only, no air conditioner: finest timing, held buttons split into separate presses soonest |
| 500000 | 65ms | every ESP32 | 2 us ticks, and every gap in your remotes is well under 65 ms (Athom's own config for its RF IR Remote ships 500000 with 65.5 ms) |
| 400000 (shipped) | 80ms | every ESP32 | the default |
| 400000 | 160ms | original ESP32 and S2 only | an air-conditioner press still arrives as two codes at 80 ms |

Keep `idle` and `clock_resolution` together: raise `idle` on its own and the validator stops with the error above, lower `clock_resolution` to a value that is not on this list and the traps above apply.

Two other settings help in particular rooms and do not touch the clock:

- `filter: 200us` for a noisy room: LED strips, direct sunlight or a plasma TV near the receiver. The default is 50us. Pulses shorter than the filter are folded into the pulse around them before the capture is handed over.
- `tolerance: 40%` for a weak or distant signal: a long cable, a cheap receiver module, a handset across the room. The default is 25%, which the configs also set. It loosens how far a pulse may stray before ESPHome's own decoders give up, which shows in the `dump:` log, in `on_nec`-style triggers and in ESPHome's climate IR. HAIR reads the raw timings and is not affected by it.

### Checking a config

**In plain terms: you can test a config on your computer before you flash anything.**

From the folder that holds your YAML and its `secrets.yaml`:

```
esphome config your-device.yaml
```

It reads the file the way a build would, without compiling or flashing anything, and ends with `INFO Configuration is valid!` when every value is accepted. A config with a placeholder still in it, such as `#ENCRYPTION_KEY#`, fails here until you fill it in. It cannot see the traps above that only show on the device, so stay with the values on this page.

### How this was checked

The timing numbers were checked against the validator and source code of ESPHome 2026.9.1 and against ESP-IDF v5.5. The buffer numbers were checked against the same ESPHome release, its `remote_receiver`, `remote_transmitter` and `esp32_rmt_led_strip` defaults and receive code, and the RMT driver and per-chip limits of ESP-IDF v5.5.5, the version ESPHome 2026.9.1 builds with by default.

On an original ESP32 they were also run on a bench. An Athom RF IR Remote with ESPHome's defaults cut every capture at 193 pairs. The same board with the full config's split (IR 320, RF 64, two transmitters at 64) started all four channels, decoded a 433 MHz remote code on the RF receiver, and heard a whole 293-pair Daikin 152 press in one capture on three of four sends; the first send lost its last 26 pairs, short of the 320 limit, so the buffer was not what cut it. The S3 and C3 behaviour is from the driver source and has not yet been run on a bench.
