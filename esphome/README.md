# HAIR ESPHome Configurations

Curated, HAIR-tested ESPHome configurations for common IR hardware. Each config carries a machine-readable header with device info, GPIO map, tested versions, and contributor attribution. Pick your device, copy the config, flash via the ESPHome Dashboard, and you are ready to use HAIR's Sniffer and Devices tabs.

## Available configs

| Device | Board | Variant | HAIR | HA Core | ESPHome | Contributor | Path |
|---|---|---|---|---|---|---|---|
| Athom RF IR Remote | esp32dev | minimal | 0.2.0 | 2026.5.2 | 2026.9.1 | DAB-LABS | [athom-rf-ir-remote/](athom-rf-ir-remote/) |
| Athom RF IR Remote | esp32dev | full | 0.2.0 | 2026.5.2 | 2026.9.1 | DAB-LABS | [athom-rf-ir-remote/](athom-rf-ir-remote/) |
| Generic ESP32-C3 dev kit | esp32-c3-devkitm-1 | minimal | 0.1.2 | 2026.5.2 | 2026.9.1 | DAB-LABS | [generic-esp32-c3/](generic-esp32-c3/) |
| Generic ESP32 doit dev kit | esp32doit-devkit-v1 | minimal | 0.1.2 | 2026.5.2 | 2026.9.1 | DAB-LABS | [generic-esp32-doit/](generic-esp32-doit/) |
| KinCony KC868-AGv3 | esp32-s3-devkitc-1 | minimal | pending | pending | 2026.9.1 | DAB-LABS | [kincony-kc868-agv3/](kincony-kc868-agv3/) |
| M5Stack IR Unit | esp32-s3-devkitc-1 | minimal | 0.3.4 | 2026.6.1 | 2026.9.1 | JenSte | [m5stack-ir-unit/](m5stack-ir-unit/) |
| M5Stack IR Unit | esp32-s3-devkitc-1 | full | 0.3.4 | 2026.6.1 | 2026.9.1 | JenSte | [m5stack-ir-unit/](m5stack-ir-unit/) |
| XIAO Smart IR Mate | seeed_xiao_esp32c3 | minimal | 0.1.2 | 2026.5.2 | 2026.9.1 | DAB-LABS | [xiao-ir-mate/](xiao-ir-mate/) |
| XIAO Smart IR Mate | seeed_xiao_esp32c3 | full | 0.1.2 | 2026.5.2 | 2026.9.1 | @Didgeridrew | [xiao-ir-mate/](xiao-ir-mate/) |

## How to pick a config

**I have a dev board and want to wire up IR LEDs:** Pick one of the generic configs. The ESP32-C3 and ESP32 doit configs are both DIY paths -- you supply the IR LED (with transistor driver) and IR receiver module.

**I want commercial off-the-shelf with no soldering:** The [Athom RF IR Remote](https://www.athom.tech/) and [XIAO Smart IR Mate](https://www.seeedstudio.com/Seeed-XIAO-Smart-IR-Mate.html) are the easiest paths. Both have IR LED, receiver, and status LED built in. The Athom also has 433 MHz RF hardware. Start with the minimal variant.

**I have not bought anything yet:** [Recommended IR hardware](../docs/recommended-hardware.md) compares the boards above and a few more, with prices and where to buy.

## Receiver timing

Every ESP32 config here sets `clock_resolution: 400000` and `idle: 80ms` on its `remote_receiver`. `idle` is how much silence ends a capture, and ESPHome's 10 ms default is shorter than the gaps inside one air-conditioner press, so a press arrives split into several codes; 80 ms clears the longest of those gaps we know of by more than double.

The ESP32's receiver can only count so much silence, about 32 ms on the C3 and S3 at ESPHome's default clock, so a lower `clock_resolution` has to come with it, and 400000 is the value that converts timings exactly and works on every ESP32 chip. If you change either, or copy the receiver into a config of your own, read [Receiver timing](../docs/receiver-timing.md) first: it explains the numbers, lists the alternatives, and covers the values that pass validation but break on the device.

Each config also sets a receive buffer big enough for the longest air-conditioner press HAIR reads, a Daikin 152 at 293 mark-and-space pairs. ESPHome's default of 192 cuts it, and a cut press never reaches HAIR whole. On the S3 and C3 that is `receive_symbols: 384`, about 1.5 KB of RAM. The original ESP32 also needs `rmt_symbols: 384`, because there the capture ends when the receiver's share of the RMT memory is full, and that memory is shared with every other RMT channel on the board. The Athom full config, which also runs a 433 MHz receiver, gives IR 320 and RF 64. [Receiver timing](../docs/receiver-timing.md) has the per-chip limits.

## Two-tier convention

Each device folder can have up to two config variants:

**Minimal** (`-minimal.yaml`): The smallest ESPHome config that gets IR TX + RX working with HAIR. Strips everything else. Start here.

**Full** (`-full.yaml`): Preserves the device's full hardware capabilities (touch pads, RGB LEDs, vibration motors, etc.). Heavier YAML but the device behaves fully. Available when a contributor has provided one.

Users pick based on appetite. The minimal version is always tested first and is the recommended starting point.

## Contributing a config

We welcome ESPHome IR configs for hardware we do not have yet. To contribute:

1. Copy the header template from [`_template/header-template.yaml`](_template/header-template.yaml) to the top of your config and fill in every field
2. Test the config against the HAIR and HA versions listed in your header (capture a signal with the Sniffer, send a command through the Devices tab)
3. Open a PR on [GitHub](https://github.com/DAB-LABS/HAIR) or post in the [HA Community forum thread](https://community.home-assistant.io/t/1010610) and link us
4. We will not merge configs without the header block fully filled out

Configs are licensed Apache 2.0. Attribution is always preserved -- your handle and source link stay in the header permanently.

## Upstream sources

These repos have additional ESPHome IR configurations that may be useful alongside HAIR:

- [esphome/infrared-proxies](https://github.com/esphome/infrared-proxies) -- Official HA team ready-made IR proxy configs
- [Seeed-Studio/xiao-esphome-projects](https://github.com/Seeed-Studio/xiao-esphome-projects) -- Seeed's stock ESPHome configs for XIAO devices
- [esphome/esphome](https://github.com/esphome/esphome) -- ESPHome itself
