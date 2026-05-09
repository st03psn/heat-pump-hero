# Vendor & protocol recipes

HeishaHub's source-adapter (`packages/heishahub_sources.yaml`) is
protocol-agnostic. Any HA entity can drive any of the source-facade
helpers. This directory collects recipes for the most common heat pumps
and protocols. PRs welcome — Heishamon is the primary target, but
HeishaHub works with anything that produces HA entities.

## Primary target

| Vendor / firmware | Protocol | Recipe |
|---|---|---|
| **Panasonic Aquarea + Heishamon** (Egyras / IgorYbema) | MQTT | [panasonic_heishamon.md](panasonic_heishamon.md) — default, plug-and-play |
| Panasonic models supported via Heishamon | MQTT | J · K · L · T-CAP · **M (R290 flagship, community fork)** — see panasonic_heishamon.md for per-model thresholds |

## Tested community alternatives

| Vendor / firmware | Protocol | Status | Recipe |
|---|---|---|---|
| Daikin Altherma 3 / Onecta | HA core integration | works | [daikin_altherma.md](daikin_altherma.md) |
| Mitsubishi Ecodan / MELCloud | MELCloud HA integration | works | [mitsubishi_melcloud.md](mitsubishi_melcloud.md) |
| Vaillant aroTHERM / sensoCOMFORT | eBUS / `mypyllant` HA integration | works | [vaillant_arotherm.md](vaillant_arotherm.md) |
| Stiebel Eltron WPL / WPM | ISG via `stiebel_eltron_isg` (HACS) | works | [stiebel_eltron.md](stiebel_eltron.md) |
| Generic ModBus heat pump | `modbus:` platform / `modbus2mqtt` | works (manual entity mapping) | [generic_modbus.md](generic_modbus.md) |
| Generic MQTT topics | `mqtt:` platform | works (manual entity mapping) | [generic_mqtt.md](generic_mqtt.md) |

## Which protocol works best universally?

Short answer: **MQTT** when you have a choice — it has the broadest
ecosystem support and gives the most stable HA entities.

Detailed:

| Protocol | Pros | Cons | Best for |
|---|---|---|---|
| **MQTT** (Heishamon, modbus2mqtt, ebusd-mqtt) | Decoupled, cheap to bridge, history-friendly, works behind NAT | Needs broker | Heishamon, any setup with a Modbus/eBUS gateway |
| **HA core / HACS integration** (Daikin, MELCloud, Vaillant, Stiebel) | UI config, no extra infrastructure | Vendor-locked, sometimes missing fields | Daikin, Mitsubishi, Vaillant — first choice when integration exists |
| **Modbus TCP** | Direct, low-latency, comprehensive register access | Setup is technical, requires register documentation | Vaillant, Stiebel, generic ModBus PLCs |
| **eBUS** | Native Vaillant / Wolf / Bosch protocol | Hardware adapter required | Vaillant, Wolf |

## How to add HeishaHub on top of any of these

1. Install whichever HA integration / MQTT setup gives you entities.
2. Open *Settings → Devices & Services → Helpers* (or the Configuration
   view of the HeishaHub dashboard).
3. Edit each `input_text.heishahub_src_*` to point at the matching
   entity ID from your integration (e.g. `sensor.daikin_altherma_inlet_temp`
   instead of `sensor.panasonic_heat_pump_main_inlet_temperature`).
4. Auto-detection (HK2, DHW, buffer) follows the new sources within
   one HA restart.
5. Control automations in `heishahub_control.yaml` are heat-pump-specific
   write paths — see the comment header for adapting them.

## Future: vendor preset selector

A planned v0.5 feature is `input_select.heishahub_vendor_preset` that
auto-fills the source helpers when you change vendor. For now the
recipes in this directory are documentation only.
