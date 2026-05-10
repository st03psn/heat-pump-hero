# Roadmap

For detailed per-release changes, see [`CHANGELOG.md`](../CHANGELOG.md).

## ✅ v0.1 — skeleton

- Repository structure, HACS manifest, MIT license
- 6 packages: sources / core / efficiency / cycles / advisor / control
- Dashboard with 6 views
- Setup blueprint, CLI installer, Telegraf bridge config
- CI: yamllint, JSON validation, HACS action
- Docs (English-only until v1.0)

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

## ✅ v0.6 — rebrand + analysis

- Rebrand `HeishaHub` → **HeatPump Hero (HPH)** across the entire
  codebase (entity IDs, files, docs, mockups)
- Analysis module Layer 1 — statistical observation of indoor-temp
  deviation, recommends heating-curve adjustment in K
- Analysis module Layer 2 — Python regression script fits supply
  vs outdoor temp, plain-language verdict
- Installer pre-flight check + DB choice prompt

## ✅ v0.7 — control extensions

- Adaptive heating curve (self-learning, weekly, capped per-step)
- Price-driven DHW (Tibber / aWATTar — sensor-agnostic)
- Weather-forecast pre-heating (cold-front anticipation)

## ✅ v0.7.2 — multi-platform read-only bridge

- Republishes ~50 derived `sensor.hph_*` (COP / SCOP / advisor /
  diagnostics) onto MQTT so ioBroker / openHAB / Node-RED / secondary
  HA instances can subscribe
- Topic schema `<prefix>/<domain>/<entity_id>/{state,attributes}`,
  `retain=true`
- Auto-clear-on-disable (empty retained payloads)
- Hardware-abstraction guarantee: topic names stable across
  vendor / integration swaps

## ✅ v0.8 — advisor extensions & programs

- Pump-curve recommendation (7-day spread mean/stdev)
- Efficiency-drift detection (year-over-year SCOP)
- DHW timing recommendation (fires/day rolling mean + start-hour buffer)
- Configurable legionella program (weekday/hour/target/hold)
- Screed dry-out program — three profiles (functional 3d /
  combined 10d / DIN 18560-1 28d)
- Control automations vendor adapter (write-target text helpers)
- Second Heishamon vendor preset — bundled MQTT YAML naming (`aquarea_*`)

### v0.8 follow-ups (still open)

- [ ] Weather-source-adapter package — swappable weather providers
  (DWD / OpenWeatherMap / Met.no / local weather station)
- [ ] DWD recipe (`docs/weather/dwd.md`) — recommended for DE users
- [ ] Efficiency-drift weather-adjustment via `sensor.hph_scop_weather_adjusted`
- [ ] Optional defrost-forecast advisor — RH + T° → icing likelihood
- [ ] Add `sensor.hph_weather_*` and `_scop_weather_adjusted` to bridge whitelist

## ✅ v0.9 — Python custom integration (HACS plug-and-play)

Released as v0.9.0-rc4. User testing phase (active).

### ✅ Phase 1 — skeleton + config-flow + helpers + dashboard auto-register

- `custom_components/hph/` skeleton with manifest, __init__, bootstrap,
  services
- Config flow (4-step wizard: vendor / model / optional external sensors /
  confirm) and options flow
- Programmatic helper registration via text / number / select / switch /
  datetime / button platforms — replaces all v0.8 input_*/counter YAML
- Dashboard auto-registration via `frontend.async_register_built_in_panel`
- Aggressive UI-uninstall (`async_remove_entry`) removes every file the
  integration ever wrote; recorder DB stays
- HACS metadata updated to integration category

### ✅ Phase 2 — template sensor + binary_sensor platforms

- All 72 `sensor.hph_*` and 6 `binary_sensor.hph_*` entities registered
  programmatically via `sensor.py` / `binary_sensor.py`
- Jinja templates bundled internally (`data/sensor_templates.yaml`) and
  rendered at runtime via `async_track_template_result`
- All `unique_id`s preserved — recorder history continuity guaranteed
- No YAML sensors deployed to user's config dir

### ✅ Phase 3 — Python automation coordinators, zero YAML deployment

All 23 automations ported to Python coordinators in `coordinators/`:

| Coordinator | Automations |
|---|---|
| `cycles.py` | cycle start/stop, daily counter reset |
| `advisor.py` | DHW fire tracking, heating-limit record, daily rollover |
| `diagnostics.py` | error-change log + persistent notification |
| `control.py` | CCC, SoftStart, Solar-DHW, quiet night on/off |
| `control_ext.py` | adaptive curve, price-DHW, forecast preheat |
| `programs.py` | legionella weekly program, screed arm + daily advance |
| `bridge.py` | MQTT bridge publish/clear |
| `export.py` | scheduled export (daily / weekly / monthly) |
| `efficiency.py` | tariff switch (operating mode → utility meter) |
| `models.py` | model threshold apply, vendor preset re-apply |

`hph.export_now` service implemented in Python (CSV snapshot).

Bootstrap now deploys only `hph_efficiency.yaml` (utility_meter +
integration sensor platform config — HA limitation, no Python API for
these) plus dashboard + assets. Migration removes old automation packages.

### ⏳ Phase 4 — polish (active, post-rc4 user testing)

- [ ] **Dashboard remediation** (active, see `.claude/plans/folgende-fehler-probleme-...`):
      cycling-chart `group_by` fix, "Sammele Daten" no-data placeholders,
      heating-limit conditional fallback, COP-trend explicit line+markers
      — Stage 1 landed; Stages 2-7 in progress
- [ ] **Demo mode** — `switch.hph_demo_mode` + `hph.demo_seed_history`
      service that injects 13 months of synthetic statistics so all
      views can be reviewed without waiting for real data
- [x] **Vs-same-month-last-year comparison** — replaced
      `hph_cop_change_month_pct` (vs. previous calendar month, near-useless)
      with `hph_cop_change_yoy_pct` (vs. same calendar month last year)
      via `statistic_during_period` over `hph_thermal_energy` /
      `hph_electrical_energy`. Thermal + electrical change-pct sensors
      and the dashboard Efficiency view follow suit.
- [ ] **OptionsFlow entity-pickers** — replace `text.hph_src_*` text-box
      configuration with HA-native entity selectors
- [ ] **View consolidation** — collapse Mobile (View 7) into Overview
      (View 1) responsively; reduce 8 tabs → 7
- [ ] **View 6 (Programs) reduction** — strip status/schedule cards; keep
      only `hph.run_legionella_now` button + markdown hint
- [x] **Long-term export bugfix** — `hph.export_now` now honours
      csv/json/xlsx selector, discovers all `sensor.hph_*` /
      `binary_sensor.hph_*` / `number.hph_*` dynamically (skipping
      source-facade mirrors), and raises `HomeAssistantError` on
      failure instead of swallowing it.
- [ ] **COP-live transparency** — show `thermal_w / electrical_w` inputs
      next to the COP value
- [ ] GitHub Release tag (v0.9.0) so HACS can show update notifications
- [ ] Per-platform translations `translations/{en,de,nl}.json`
- [ ] Repairs panel for missing frontend cards (apexcharts, mushroom, …)
- [ ] pytest-based test suite mocking HA core
- [ ] HACS-default-repository submission
- [ ] PV self-consumption net cost sensor (`hph_cost_today_net`)
- [ ] Picture-elements live values card (ported from dashboard-warmepumpe/0)

## v1.0 — stable

- [ ] Full HA-CI test suite with mocked MQTT and assertions on advisor states
- [ ] Beta-tester program for Daikin / Vaillant / Stiebel installs
- [ ] Video walkthrough
- [ ] Adapter recipes for non-Panasonic vendors validated by users
- [ ] Per-locale dashboard strings via integration translations
- [ ] Translations of repo docs (README / docs / info) into DE and NL
- [ ] Logo & brand: SVG + PNG assets for README, HACS listing, dashboard header
- [ ] **Drop-in advisor extension API** — `<config>/hph/advisors/*.py`
      auto-discovered on startup
- [ ] Remove deprecated `scripts/install.sh` / `scripts/update.ps1`
      (legacy YAML-package installer paths)

## Out of scope

- Cloud features (HeatPump Hero stays 100 % local)
- Replacing kamaradclimber/heishamon-homeassistant — we wrap it, not duplicate it
- Standalone control without an underlying heat-pump integration

## Contributing

Issues with concrete use-cases very welcome. Before opening a PR, please
read the design principles in [CLAUDE.md](../CLAUDE.md), in particular
the universality, advisor schema, source-adapter, and diagnostics
conventions. Per-vendor recipes in `docs/vendors/` are great first contributions.
