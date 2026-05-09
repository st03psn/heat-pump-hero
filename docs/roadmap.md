# Roadmap

🌐 English (this file) · [Deutsch](de/roadmap.md)

For detailed per-release changes, see [`CHANGELOG.md`](../CHANGELOG.md).

## ✅ v0.1 — skeleton

- Repository structure, HACS manifest, MIT license
- 6 packages: sources / core / efficiency / cycles / advisor / control
- Dashboard with 6 views
- Setup blueprint, CLI installer, Telegraf bridge config
- CI: yamllint, JSON validation, HACS action
- Bilingual docs (EN / DE)

## ✅ v0.2 — universal counters

- Bubble-Card SVG schematic with live hotspots (HK1 + HK1+DHW)
- Source-adapter layer — swap heat pump / meter via UI
- Tariff splits (heating / DHW / cooling)
- HA Energy Dashboard integration
- Real Grafana Flux queries
- Period-comparison sensors (vs last month / last year)

## ✅ v0.3 — auto-detection & polish

- Auto-detected schematic variant (4 conditional cards)
- COP heatmap + outdoor T° vs COP scatter
- Auto-detected heating limit
- Mobile dashboard view
- HK1+HK2+DHW and HK1+HK2+DHW+Buffer SVGs
- NL translation, HACS path doc, vendor recipes

## ✅ v0.4 — diagnostics & vendor support

- Panasonic fault-code diagnostics (30+ H/F codes, model-specific notes)
- Vendor preset selector with auto-fill (7 vendors)
- Heat-pump model selector with auto thresholds
- Panasonic M-series (R290 flagship) supported
- Water-pressure trend advisor (slow-leak detection)
- Integration UI mockup (config flow + main panel)
- HA min version corrected to 2024.4
- HA Docker check_config CI

## ✅ v0.5 — export, import, DB, naming

- Export module: CSV / JSON / XLSX, manual or scheduled (daily/weekly/monthly)
- Import module: backfill HA long-term statistics from CSV
- Database recommendations doc (SQLite vs MariaDB vs PostgreSQL vs InfluxDB)
- Naming proposal doc
- M-series compressor min Hz corrected (12 → 16, empirical)

## ✅ v0.6 — rebrand + analysis (current)

- Rebrand `HeishaHub` → **Heat Pump Hero (HPH)** across the entire
  codebase (entity IDs, files, docs, mockups)
- Analysis module Layer 1 — statistical observation of indoor-temp
  deviation, recommends heating-curve adjustment in K
- Analysis module Layer 2 — Python regression script fits supply
  vs outdoor temp, plain-language verdict
- Installer pre-flight check + DB choice prompt
- Installer ships export / import / heating-curve scripts to `/config/scripts/`

## ✅ v0.7 — control extensions (current)

- Adaptive heating curve (self-learning, weekly, capped per-step)
- Price-driven DHW (Tibber / aWATTar — sensor-agnostic)
- Weather-forecast pre-heating (cold-front anticipation)

## v0.8 — advisor extensions

- [ ] Pump-curve recommendation (spread histogram)
- [ ] Efficiency-drift detection (year-over-year, weather-adjusted)
- [ ] DHW timing recommendation (usage pattern)
- [ ] Configurable legionella program
- [ ] Screed dry-out program (for new builds)
- [ ] Control automations vendor adapter (write paths swappable)

## v0.9 — Python custom integration (HACS plug-and-play)

- [ ] `custom_components/hph/` skeleton
- [ ] Config flow for first-run setup (3 steps: vendor / model / extras)
- [ ] Programmatic helper registration (no input_select / input_text YAML)
- [ ] Programmatic sensor registration (replaces `template:` packages)
- [ ] Dashboard auto-registration via `lovelace.dashboards`
- [ ] Per-platform translations `translations/{en,de,nl}.json` →
  follows HA `hass.config.language` automatically
- [ ] Repairs panel for missing frontend cards (apexcharts, mushroom, …)
- [ ] HACS-default-repository submission

## v1.0 — stable

- [ ] Full HA-CI test suite with mocked MQTT and assertions on advisor states
- [ ] Beta-tester program for Daikin / Vaillant / Stiebel installs
- [ ] Video walkthrough
- [ ] Adapter recipes for non-Panasonic vendors validated by users
- [ ] Per-locale dashboard strings via integration translations

## Out of scope

- Cloud features (Heat Pump Hero stays 100 % local)
- Replacing kamaradclimber/heishamon-homeassistant — we wrap it, not
  duplicate it
- Standalone control without an underlying heat-pump integration

## Contributing

Issues with concrete use-cases very welcome. Before opening a PR, please
read the design principles in [CLAUDE.md](../CLAUDE.md), in particular
the universality, advisor schema, source-adapter, and diagnostics
conventions. Per-vendor recipes in `docs/vendors/` are great
first contributions.
