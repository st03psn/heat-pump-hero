# HeishaHub

> Universal Home Assistant package for Panasonic Aquarea heat pumps with
> Heishamon — dashboard, statistics, optimization advisor, control automations.

🌐 **Languages:** English (this file) · [Deutsch](README.de.md)

[![Validate](https://github.com/st03psn/HeishaHub/actions/workflows/validate.yml/badge.svg)](https://github.com/st03psn/HeishaHub/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

HeishaHub bundles what's missing today: an importable Home Assistant dashboard
laid out like the Heishamon web UI, Service-Cloud-style analytical graphs, an
installation schematic with live hotspots, and proper efficiency metrics
(SCOP / monthly / daily / live COP) — including multi-year tracking.

## Status

🚧 **Pre-alpha (v0.1)** — skeleton with first working HK1 overview, live COP,
cycle analysis, optimization advisor, and HeishaMoNR-parity control
automations. Bubble-Card schematic, Grafana boards, and one-click setup
blueprint follow iteratively.

## Features (v0.1 → roadmap)

**Visualization & status**
- ✅ Status dashboard (overview, Heishamon-web-UI layout)
- ✅ Live COP & thermal/electrical energy
- ✅ Universal: zone 2 / DHW / buffer / solar / pool optional, auto-hide
- ✅ External sensors (Shelly, heat meter) selectable via UI dropdown
- 🟡 Service-Cloud-style graphs (ApexCharts) — basic in place, polish ongoing
- 🟡 Installation schematic (Bubble-Card + SVG) — placeholder
- 🟡 SCOP / monthly / daily COP + Energy-Dashboard integration

**Cycle analysis & optimization**
- ✅ Cycle tracking (starts/h, run times, pauses)
- ✅ Short-cycle detection with configurable threshold
- ✅ Data-driven **advisor** with plain-language recommendations:
  cycling, supply/return spread, defrost behaviour, heat curve / aux heater,
  DHW run length — aggregate traffic-light tile in dashboard
- ✅ **Control strategies (HeishaMoNR parity)**: CCC (Compressor Cycle
  Control), SoftStart, Solar-DHW boost, night Quiet-Mode — all as HA
  automations, individually toggleable, master switch

**Long-term & export**
- ⏳ Grafana boards for multi-year efficiency
- ⏳ Setup blueprint for one-click deploy

## Requirements

- Home Assistant 2025.4 or newer
- Heishamon hardware (Egyras / IgorYbema firmware) connected to an MQTT
  broker (default topic prefix: `panasonic_heat_pump`)
- HACS installed

## Quick install

1. **Add HACS custom repository**
   - HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/st03psn/HeishaHub`
   - Category: *Lovelace* (until HACS supports mixed content)

2. **Install dependencies** (HACS search, order doesn't matter):
   - kamaradclimber Heishamon-HomeAssistant (integration)
   - apexcharts-card, bubble-card, mushroom, button-card,
     auto-entities, card-mod (frontend plugins)

3. **Enable packages** — in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
   Copy the contents of this repo's `packages/` to `<config>/packages/`
   (manually or via `scripts/install.sh`).

4. **Add the dashboard** — Settings → Dashboards → Add → From YAML →
   paste `dashboards/heishahub.yaml`.

5. **External sensors** (optional) — Settings → Devices & Services → Helpers:
   set `heishahub_shelly_entity` and `heishahub_wmz_entity` to your sensor
   entity-IDs. See [docs/external_sensors.md](docs/external_sensors.md).

Detailed walkthrough: [docs/installation.md](docs/installation.md).

## Architecture

```
  Heishamon ─┐
             ├─MQTT─▶ kamaradclimber → HA entities
  Shelly ────┤                        │
  Heat meter ┘                        ├─▶ heishahub packages (templates)
                                      │     ├─ COP / SCOP / monthly / daily
                                      │     └─ thermal/electrical energy
                                      ├─▶ HA Recorder + LTS ─▶ Lovelace
                                      └─▶ HA Energy Dashboard
                                      ↓
                                 InfluxDB ─▶ Grafana (multi-year SCOP)
```

## Project name

**HeishaHub** — a hub for everything around Heishamon: dashboard + control +
statistics in a single bundle.

## Contributing

Issues and pull requests welcome.

- [CLAUDE.md](CLAUDE.md) — architecture and conventions
- [docs/installation.md](docs/installation.md) — step-by-step setup
- [docs/external_sensors.md](docs/external_sensors.md) — Shelly / heat meter
- [docs/optimization.md](docs/optimization.md) — cycle analysis, advisor, control
- [docs/tweaking.md](docs/tweaking.md) — power-user customizations
- [docs/roadmap.md](docs/roadmap.md) — what's next

German translations live alongside as `*.de.md` and `docs/de/`.

## License

MIT — see [LICENSE](LICENSE).

## Related projects

- [Egyras/HeishaMon](https://github.com/Egyras/HeishaMon) — firmware
- [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant) — HA integration (required dependency)
- [edterbak/HeishaMoNR](https://github.com/edterbak/HeishaMoNR) — Node-Red variant (can run in parallel)
