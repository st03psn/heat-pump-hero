# HeatPump Hero

Bundle package for **Heishamon** in Home Assistant: dashboard laid out like
the Heishamon web UI, Service-Cloud-style analytical graphs, installation
schematic and long-term efficiency (SCOP / monthly / daily / live COP) —
universal, plug-and-play, with optional InfluxDB / Grafana integration for
multi-year comparison.

## Features

- Overview dashboard (Mushroom) styled like the Heishamon web UI
- Installation schematic as a Bubble-Card with SVG and live hotspots
- ApexCharts analysis with multi-axis support, time range picker, series toggle
- SCOP / monthly / daily / live COP for heating, DHW, cooling
- External sensors (Shelly Pro 3EM / 1PM / EM, MQTT heat meters) selectable
  via UI dropdown — no YAML editing required
- Auto-hide for absent components (zone 2, DHW, buffer, solar, pool)
- Cycle analysis with short-cycle detection
- Data-driven optimization advisor with plain-language recommendations
- Control strategies (CCC, SoftStart, Solar-DHW, night Quiet-Mode) — HA
  automations with master switch, off by default
- Optional: Grafana boards for multi-year SCOP comparison

## Requirements

- Home Assistant **2024.4** or newer
- Heishamon hardware connected to an MQTT broker

## Installation

See [docs/installation.md](docs/installation.md).

## Dependencies

- [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- [RomRider/apexcharts-card](https://github.com/RomRider/apexcharts-card)
- [Clooos/Bubble-Card](https://github.com/Clooos/Bubble-Card)
- [piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom)
- [custom-cards/button-card](https://github.com/custom-cards/button-card)
- [thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
- [thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)
