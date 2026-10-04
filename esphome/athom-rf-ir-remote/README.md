# Athom RF IR Remote

Commercial ESP32 device with both IR and 433 MHz RF hardware. Compact enclosure with built-in IR LED, IR receiver, RF transmitter, RF receiver, status LED, and button. Sold by [Athom](https://www.athom.tech/).

HAIR uses the IR side only. The RF hardware is present in the config but is not used by HAIR.

## Variants

**Minimal** (`athom-rf-ir-remote-minimal.yaml`): IR transmitter and receiver only, with the board settings, pins and ids from Athom's own config. Nothing is pulled from Athom's package, so HAIR's receiver timing applies. RF, BLE proxy, climate IR, status LED and button are not configured.

**Full** (`athom-rf-ir-remote-full.yaml`): Standalone config with no package import. Every component is laid out with comments so you can see and customize everything, including RF, BLE proxy, climate IR and diagnostics. Based on Athom's v3.0.1 config.

## Which variant to use

Start with **minimal** if the box is only an IR proxy for HAIR. Use **full** if you also want the BLE proxy, the climate entity, RF, or the diagnostic sensors.

## HA version notes

HAIR subscribes to the native `InfraredReceiverEntity` that the `ir_rf_proxy` platform exposes, which needs **HA 2026.6+**. Both configs set the receiver to `clock_resolution: 400000` and `idle: 80ms`; [Receiver timing](../../docs/receiver-timing.md) explains why.

## Hardware

- Board: ESP32-DevKit (esp32dev)
- Framework: esp-idf
- Flash: 8 MB
- IR TX: GPIO25
- IR RX: GPIO33
- RF TX: GPIO18 (433 MHz)
- RF RX: GPIO19 (433 MHz)
- Status LED: GPIO27
- Button: GPIO0
