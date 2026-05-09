# HeatPump Hero

**Home Assistant custom integration** for heat pumps — install via HACS, configure
via Settings → Devices & Services. No YAML editing required.

Panasonic Aquarea / Heishamon primary, multi-vendor adapter built in (Daikin,
MELCloud, Vaillant, Stiebel and more).

## Features

- Install via HACS, configure via 4-step wizard (vendor preset, pump model, optional
  external sensors)
- Dashboard auto-appears in sidebar — 7 views: Overview, Schematic, Analysis,
  Efficiency, Optimization, Mobile, Configuration
- Installation schematic as Bubble-Card SVG with live hotspots (4 schema variants)
- SCOP / monthly / daily / live COP for heating, DHW, cooling + tariff splits
- Source-adapter: every entity-ID configurable via UI — swap heat pump or meter
  without YAML edits
- Cycle analysis with short-cycle detection and auto-detected heating limit
- Data-driven optimization advisor (12 advisors, plain-language recommendations)
- Control strategies: CCC, SoftStart, Solar-DHW boost, night Quiet-Mode, adaptive
  heating curve, price-driven DHW, weather-forecast pre-heating
- Programs: legionella (weekday/hour/target/hold), screed dry-out (3 profiles)
- Multi-platform MQTT bridge: republishes ~50 derived sensors for ioBroker /
  openHAB / Node-RED
- Panasonic fault-code diagnostics (30+ H/F codes, model-specific commentary)
- Scheduled CSV export, Grafana boards, InfluxDB bridge

## Requirements

- Home Assistant **2025.4** or newer
- HACS installed
- Heishamon hardware connected to an MQTT broker (or supported alternative vendor)

## Dependencies (install via HACS frontend category)

- [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- [RomRider/apexcharts-card](https://github.com/RomRider/apexcharts-card)
- [Clooos/Bubble-Card](https://github.com/Clooos/Bubble-Card)
- [piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom)
- [custom-cards/button-card](https://github.com/custom-cards/button-card)
- [thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
- [thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)
