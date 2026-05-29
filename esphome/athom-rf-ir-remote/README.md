# Athom RF IR Remote

Commercial ESP32 device with both IR and 433 MHz RF hardware. Compact enclosure with built-in IR LED, IR receiver, RF transmitter, RF receiver, status LED, and button. Sold by [Athom](https://www.athom.tech/).

HAIR uses the IR side only. The RF hardware is present in the config but is not used by HAIR.

## Variants

**Minimal** (`athom-rf-ir-remote-minimal.yaml`): Uses the official Athom package import from GitHub. Shortest possible config -- the package provides all hardware setup, BLE proxy, climate IR, and diagnostics. Adds only the HAIR legacy bridge for pre-2026.6 HA.

**Full** (`athom-rf-ir-remote-full.yaml`): Standalone config with no package import. Every component is laid out with comments so you can see and customize everything. Based on Athom's v3.0.1 package with the HAIR legacy bridge added.

## Which variant to use

Start with **minimal** unless you need to customize individual components. The Athom package is well maintained and tracks ESPHome releases. Use **full** if you want to remove BLE proxy, change the climate platform, or modify diagnostic sensors without fighting package merge behavior.

## HA version notes

On **HA 2026.6+**, HAIR subscribes to the native `InfraredReceiverEntity` exposed by the `ir_rf_proxy` platform. The `on_pronto` legacy bridge in both configs is unused and can be removed.

On **HA 2026.4-2026.5**, HAIR uses the `on_pronto` legacy bridge to receive signals via the HA event bus. Do not remove this block if you are on these versions.

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
