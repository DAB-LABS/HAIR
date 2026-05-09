# Research: Home Assistant IR Platform (2026.4)

**Researcher:** David Bailey
**Date:** 2026-05-08
**Sources:** HA Developer Docs, Release Notes, Community Forums, Tech Press

---

## 1. Overview

Home Assistant 2026.4 introduced a native `infrared` entity platform that decouples IR emitter hardware from the devices they control. This is the foundation HA IR Admin will build on.

**Release:** 2026.4 ("Infrared never left the chat")
**Author:** Abilio Costa (@abmantis)
**Architecture Discussion:** github.com/home-assistant/architecture/discussions/1316

---

## 2. Architecture Model

The infrared domain sits between two types of integrations:

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Consumer            │     │  Infrared Platform    │     │  Emitter             │
│  Integrations        │────▶│  (Abstraction Layer)  │────▶│  Integrations        │
│                      │     │                       │     │                      │
│  - LG Infrared       │     │  - InfraredEntity     │     │  - ESPHome           │
│  - Samsung IR        │     │  - InfraredCommand    │     │  - Broadlink         │
│  - Daikin IR         │     │  - Helper functions   │     │  - SMLIGHT SLZB      │
│  - (HA IR Admin)     │     │  - Protocol library   │     │  - (Any future IR    │
│                      │     │                       │     │    proxy)            │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
```

### Emitter Integrations
- Implement `InfraredEntity` base class
- Provide hardware-specific IR transmission
- Expose `async_send_command(command: InfraredCommand)` method
- Currently supported: ESPHome, Broadlink (added in 2026.5), SMLIGHT SLZB (added in 2026.5)

### Consumer Integrations
- Control IR devices by sending commands through emitter entities
- Don't interact with IR hardware directly
- Use `infrared.async_send_command()` helper function
- Currently: LG Infrared (launched at silver quality in 2026.4)

---

## 3. Key API Surface

### InfraredEntity Base Class
```python
from homeassistant.components.infrared import InfraredCommand, InfraredEntity

class MyInfraredEntity(InfraredEntity):
    """IR transmitter entity."""

    async def async_send_command(self, command: InfraredCommand) -> None:
        """Send an IR command."""
        timings = [
            interval
            for timing in command.get_raw_timings()
            for interval in (timing.high_us, -timing.low_us)
        ]
        await self._device.transmit(
            carrier_frequency=command.modulation,
            timings=timings,
        )
```

### Consumer Helper Functions
```python
from homeassistant.components import infrared

# Get available emitters
emitters = infrared.async_get_emitters(hass)

# Send a command through an emitter
await infrared.async_send_command(
    hass,
    self._infrared_entity_id,
    make_lg_tv_command(LGTVCode.VOLUME_UP),
    context=self._context,
)
```

### Config Flow Integration
```python
# Consumer integration declares dependency
# manifest.json: {"dependencies": ["infrared"]}

# Config flow lets user pick an emitter
emitters = infrared.async_get_emitters(hass)
if not emitters:
    return self.async_abort(reason="no_emitters")
```

### InfraredCommand Properties
- `get_raw_timings()` — Returns protocol-agnostic timing data (high_us, low_us pairs)
- `modulation` — Carrier frequency for the IR signal

---

## 4. Entity Characteristics

- **Stateless** in traditional sense (no on/off state)
- State is a **timestamp** of last IR command sent
- Possible states: timestamp, `unavailable`, `unknown`
- Entity domain: `infrared`
- Example entity_id: `infrared.esphome_ir_blaster`

---

## 5. Protocol Library

IR protocol encoders and device code sets live in a separate library:
- **Repository:** github.com/home-assistant-libs/infrared-protocols
- Common protocols: NEC, Samsung, etc.
- Well-known device codes contributed to this shared library
- Third-party libraries supported for niche/proprietary protocols

---

## 6. 2026.5 Additions

- **Broadlink** can now act as an IR emitter on the infrared platform (RM-series devices)
- **SMLIGHT SLZB** devices now expose an infrared platform
- **Radio Frequency (RF)** entity platform also introduced (parallel to IR, same architecture pattern)
- This shows HA is actively expanding this abstraction layer pattern

---

## 7. Implications for HA IR Admin

### What the Platform Provides
- Emitter discovery (`async_get_emitters`)
- Command transmission (`async_send_command`)
- Protocol encoding (via `infrared-protocols` library)
- Entity infrastructure (device registry, state tracking)

### What the Platform Does NOT Provide
- **IR command learning/capture** — No built-in capture flow
- **Device profiles** — No database of "this is a Samsung TV with these buttons"
- **Command management UI** — No way to organize, name, or manage IR commands
- **Admin interface** — No settings panel for IR device management
- **Raw code storage** — No mechanism to save learned IR codes

### The Gap HA IR Admin Fills
The platform is the transport layer. HA IR Admin is the management layer. The platform knows how to send an IR signal; HA IR Admin knows what devices exist, what commands they have, and gives users a UI to capture and organize them.

---

## 8. Key Technical Decisions

1. HA IR Admin should be a **consumer integration** that depends on `infrared`
2. It needs to store learned IR codes in its own storage (HA `.storage/` directory)
3. It should create entities (media_player, climate, fan, etc.) that use the IR platform to send commands
4. The config flow must present emitter selection as a first step
5. We need to handle the case where IR learning/capture requires a **receiver** (not just a transmitter) — the platform currently only defines transmitters

### Open Question: IR Receiving
The 2026.4 platform defines emitters (transmitters) but not receivers. For command capture, we'll need:
- ESPHome IR receiver component (already exists in ESPHome)
- Broadlink learning mode (already exists in Broadlink integration)
- A standardized way to receive/learn raw IR codes

This is the most significant technical challenge. We may need to work with existing integrations' learning capabilities or define our own receiver abstraction.

---

## Sources

- [Developer Blog: New infrared entity platform](https://developers.home-assistant.io/blog/2026/03/30/infrared-entity-platform/)
- [Release 2026.4: Infrared never left the chat](https://www.home-assistant.io/blog/2026/04/01/release-20264/)
- [Infrared Integration Docs](https://www.home-assistant.io/integrations/infrared/)
- [Release 2026.5: We're on the same frequency now](https://www.home-assistant.io/blog/2026/05/06/release-20265/)
- [Architecture Discussion #1316](https://github.com/home-assistant/architecture/discussions/1316)
- [infrared-protocols Library](https://github.com/home-assistant-libs/infrared-protocols)
