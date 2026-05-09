# Roadmap

🌐 English (this file) · [Deutsch](de/roadmap.md)

## v0.1 — skeleton ✅

- [x] Repository structure, HACS manifest, MIT license
- [x] Packages: sources / core / efficiency / cycles / advisor / control
- [x] Dashboard with 6 views (Overview, Schema, Analysis, Efficiency,
  Optimization, Configuration)
- [x] Setup blueprint (diagnostic)
- [x] CLI installer `scripts/install.sh`
- [x] Telegraf MQTT bridge config
- [x] CI: yamllint, JSON validation, HACS action
- [x] Bilingual docs (English primary, German secondary)

## v0.2 — universal & usable ✅ (current)

- [x] Bubble-Card SVG schematic with live hotspots (HK1 + HK1+DHW variants)
- [x] **Source-adapter layer** — every entity read is UI-configurable;
  swap heat pump or meter without YAML edits
- [x] Tariff splits in `utility_meter` (heating/dhw/cooling separate)
- [x] HA Energy Dashboard integration via `_active` energy sensors
- [x] Real Grafana Flux queries (overview + multi-year SCOP/MAZ)
- [x] Period-comparison sensors and trend headlines
  (vs last month, vs last year, in %)
- [x] External meter modes: `external_power` (W → integrate)
  and `external_energy` (kWh, bypass integrator)

## v0.3 — long-term insight

- [ ] Schematic variants for HK1+HK2+DHW and HK1+HK2+DHW+buffer
- [ ] Mobile-optimized dashboard layout
- [ ] Heatmap card (outdoor × hour-of-day × COP) — instantly shows where
  efficiency drops
- [ ] Auto-detect heating-limit temperature from data
- [ ] Year-over-year comparison cards (same calendar month last year)
  via long-term statistics
- [ ] README screenshots, video walkthrough
- [ ] Smoke tests cover the new sensors and source-mode switching

## v0.4 — advisor extensions

- [ ] Heating-curve recommendation derived from data (linear regression
  of supply temp vs. outdoor temp)
- [ ] Pump-curve recommendation (spread histogram)
- [ ] Water-pressure trend detection (slow leak warning)
- [ ] Efficiency-drift detection (year-over-year, weather-adjusted)
- [ ] DHW timing recommendation (based on usage pattern)

## v0.5 — control extensions

- [ ] Adaptive heating curve (self-learning from indoor sensors)
- [ ] Price-driven DHW (Tibber / aWATTar integration)
- [ ] Configurable legionella program
- [ ] Weather-forecast pre-heating
- [ ] Screed dry-out program (for new builds)
- [ ] Control automations adapter — abstract write paths so non-Heishamon
  heat pumps can plug in their own write entities

## v1.0 — stable & documented

- [ ] Full HA-CI test suite with mocked MQTT
- [ ] Internationalization (EN, NL — typical Heishamon communities)
- [ ] Submission to the HACS default repository
- [ ] Zone 2 / buffer / solar / pool fully tested with beta users
- [ ] Adapter recipes for non-Heishamon heat pumps (Daikin Altherma,
  Vaillant aroTHERM, Stiebel Eltron WPL, generic Modbus)

## Out of scope

- A dedicated Python custom integration (kamaradclimber covers entities — no
  need to duplicate work).
- Cloud features (HeishaHub stays 100 % local).
- Standalone control without an underlying heat-pump integration.

## Contributing

Issues with concrete use-cases very welcome. Before opening a PR, please
read the design principles in [CLAUDE.md](../CLAUDE.md), in particular the
universality, advisor schema, and source-adapter conventions.
