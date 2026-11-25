# ESP32 + CC1101 radio proxy

An ESP32 dev board and a CC1101 module, wired together, give Home Assistant a radio that can listen almost anywhere from 300 to 928 MHz and send on one frequency you pick. HAIR sees it as a radio receiver and transmitter, so you can capture a remote in the Sniffer, use its presses as triggers, and send codes back out.

It's a DIY build: there's no case, and you'll be soldering eight wires. In return it's a good listener for very little money.

HAIR sends through the RF Transmitter from Home Assistant 2026.11. It hears the RF Receiver from Home Assistant 2026.12 and the matching ESPHome release, which register ESPHome radio receivers on the `radio_frequency` platform. Radio in HAIR is still beta.

## What you need

- An ESP32-WROOM-32 dev board. Other ESP32 boards work too, but need their own pin numbers in the `substitutions` block.
- A CC1101 module. The one tested here is an Ebyte E07-M1101D, which is tuned for 433 MHz. It hears 315 and 303.875 too, just not as far.
- An antenna that suits the band you care about most.

## Wiring

| CC1101 pin | ESP32 pin |
|---|---|
| GND | GND |
| VCC | 3V3 (3.3 V only, never 5 V) |
| GDO0 | GPIO26 (send) |
| CSN | GPIO27 |
| SCK | GPIO18 |
| MOSI | GPIO23 |
| MISO / GDO1 | GPIO19 |
| GDO2 | GPIO25 (receive) |

## Flashing

1. Copy `esp32-cc1101-rf-proxy.yaml` to your ESPHome config folder.
2. Change the name in `substitutions` if you like, and the pins if your board isn't a WROOM-32 DevKit.
3. Set `tx_frequency` to a frequency you're allowed to send on where you live. It's 433.92 MHz out of the box. In the US most remotes use 315 or 433.92.
4. Add the entries below to your `secrets.yaml`.
5. Flash it from the ESPHome dashboard, over USB the first time.

```yaml
api_encryption_key: "<your-api-encryption-key>"
wifi_ssid: "<your-wifi-ssid>"
wifi_password: "<your-wifi-password>"
```

## What you get in Home Assistant

- **RF Receiver** and **RF Transmitter**, the entities HAIR uses. From Home Assistant 2026.12, the receiver tells Home Assistant it can tune 300 to 928 MHz.
- **Listen frequency**, where the receiver is listening. You can set it here, and from Home Assistant 2026.12 also from the receiver's pill in HAIR's Sniffer. The CC1101 can't tune 348 to 387 or 464 to 779 MHz, so a number in those gaps is refused and the old one stays. HAIR's "Other..." box takes anything from 300 to 928, because the receiver declares one range; a number in a gap is refused by the device, which stays where it was. It goes back to 433.92 after every restart.
- **RX attenuation**, which turns the receiver down so it only hears things that are close. Leave it at 0dB unless a neighbor's remote keeps showing up.
- **Debug capture log**, off by default. Turn it on to see every capture in the ESPHome log, and turn it off again after: on a busy frequency it's a lot of text.
- Wi-Fi signal, uptime and a restart button.

## Receiver timing

The receiver uses the same timing as the other HAIR ESP32 configs: `clock_resolution: 400000` and `idle: 80ms`, so a remote that repeats its code with short gaps arrives as one whole press. It also gets `receive_symbols: 384` and `rmt_symbols: 384`, because ESPHome's default of 192 cuts a long press. The original ESP32 has 512 symbols of RMT memory for every channel together, so the transmitter gets the other 128. [Receiver timing](../../docs/receiver-timing.md) explains the numbers.

## Things to know

- Some frequencies are just noisy. Around 440 and 400 MHz there can be junk most of the day, and it can drown out a real remote. 433.92 and 315 are usually quiet. The Sniffer filters most of it, but not all.
- Sending only goes out on `tx_frequency`. That's on purpose: you can listen to a remote on any band, and its presses still work as triggers even if this device can't send them back.
- Rolling-code remotes, such as most car keys, modern garage doors and gates, send a different code on every press. This board hears them, and HAIR keeps their codes but never sends one. [Radio remotes](../../docs/rf.md) has the details.
- Range depends a lot on the antenna and the module. This config was tested with one module, matched for 433 MHz. It heard a Broadlink RM4 Pro in the next room at 433.92, and remotes at 303.875 and 315. Other bands depend on your module and antenna.
- It sends at 0 dBm (`output_power`). That reaches across a room at 433.92. At 315 a 433 MHz module is weak enough that a Broadlink in the same room didn't pick it up.

## Tested with

| | |
|---|---|
| HAIR | 1.3.1 |
| Home Assistant | 2026.11.1 |
| ESPHome | 2026.11.0 |
| Last verified | 2026-11-22 |
| Board | ESP32-WROOM-32 DevKit + Ebyte E07-M1101D |
