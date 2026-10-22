# Athom RF IR Remote

Commercial ESP32 device with both IR and 433 MHz RF hardware. Compact enclosure with built-in IR LED, IR receiver, RF transmitter, RF receiver, status LED, and button. Sold by [Athom](https://www.athom.tech/).

HAIR uses the IR side only. The RF hardware is present in the config but is not used by HAIR.

## Variants

**Minimal** (`athom-rf-ir-remote-minimal.yaml`): IR transmitter and receiver only, with the board settings, pins and ids from Athom's own config. Nothing is pulled from Athom's package, so HAIR's receiver timing applies. RF, BLE proxy, climate IR, status LED and button are not configured.

**Full** (`athom-rf-ir-remote-full.yaml`): Standalone config with no package import. Every component is laid out with comments so you can see and customize everything, including RF, BLE proxy, climate IR and diagnostics. Based on Athom's v3.0.1 config.

## Which variant to use

Start with **minimal** if the box is only an IR proxy for HAIR. Use **full** if you also want the BLE proxy, the climate entity, RF, or the diagnostic sensors.

## HA version notes

HAIR subscribes to the native `InfraredReceiverEntity` that the `ir_rf_proxy` platform exposes, which needs **HA 2026.6+**. Both configs set the receiver to `clock_resolution: 400000` and `idle: 80ms`, and give it room for the longest air-conditioner presses: 384 symbols in the minimal config, 320 in the full one, where the four RMT channels (IR and RF, send and receive) share the original ESP32's 512 symbols and the RF receiver is cut to 64 to make room. [Receiver timing](../../docs/receiver-timing.md) explains why.

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

## Required secrets.yaml entries

```yaml
api_encryption_key: "<your-api-encryption-key>"
wifi_ssid: "<your-wifi-ssid>"
wifi_password: "<your-wifi-password>"
ap_password: "<your-fallback-ap-password>"   # minimal only
web_username: "<your-web-page-username>"     # full only
web_password: "<your-web-page-password>"     # full only
```

The full config's built-in web page asks for `web_username` and `web_password`. The page still takes firmware uploads for recovery, and OTA encryption does not cover those, so the login keeps them from anyone else on your network.

Already running one of these configs? If the device's firmware was built with ESPHome 2026.9.0 or newer (Home Assistant shows the version on the device page), install the new config as usual; the minimal one no longer needs `ota_password` in your secrets. If it is older, install your current config once more with ESPHome 2026.9.1 or newer first, then the new one; ESPHome refuses to send the new config to older firmware and says so. ESPHome stops accepting that route in 2027.3.0, after which an older device has to be flashed over USB.
