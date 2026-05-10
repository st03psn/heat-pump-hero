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

- `custom_components/hph/` skeleton with manifest, __init__, bootstrap, services
- Config flow (4-step wizard: vendor / model / optional external sensors / confirm)
  and options flow
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

**Dashboard — 8 views (current inventory)**

| # | View | Path | Purpose | Key charts |
|---|------|------|---------|------------|
| 1 | Overview | `overview` | Live status at a glance. Operating mode, COP live, KPI strip (COP today/month/SCOP/cost), energy last 7d, COP last 30d, cycling last 7d. | Energy 7d · COP 30d · Cycling 7d |
| 2 | Schematic | `schema` | Installation schematic (SVG with live hotspots). Auto-detects variant (HK1 / +DHW / +HK2 / +buffer). | — |
| 3 | Analysis | `analysis` | Short-term diagnosis (≤24h). Temperature 12h, compressor+flow 12h, COP trend 24h, COP heatmap (hour-of-day, 30d), COP daily 30d. | Temps 12h · Compressor 12h · COP 24h · Heatmap 30d · COP daily 30d |
| 4 | Efficiency | `efficiency` | Long-term statistics. KPIs, YoY comparisons, energy by mode, daily energy 30d, COP trend 30d, SCOP per heating season, cumulative energy. | Energy 30d · COP 30d · SCOP seasonal |
| 5 | Optimization | `optimization` | Actionable recommendations. Advisor summary, cycle analysis, diagnostics, heating-curve recommendation. | Cycling 7d |
| 6 | Heat pump | `heatpump` | Operating controls + heating-curve configuration. Quick actions (holiday/force-DHW), comfort chips, Z1/Z2 curve points, advanced settings, control extensions, advisor thresholds. | — |
| 7 | Programs | `programs` | Service programs. Legionella one-off boost + documentation. | — |
| 8 | Configuration | `config` | Source adapter setup. Vendor/model preset, source modes, external meters, electricity costs, export settings, bridge config. | — |

All charts auto-scale (no fixed y-axis min/max as of this revision).

**Open tasks:**

- [ ] **View consolidation (long-term → Efficiency)** — move "COP last 30 days"
      from Overview and "COP daily last 30 days" from Analysis into Efficiency;
      replace in Overview/Analysis with shorter-window equivalents or remove.
      Agreed direction; not yet implemented.
- [ ] **Demo mode** — `switch.hph_demo_mode` + `hph.demo_seed_history` service
      injects 13 months of synthetic statistics so all views can be reviewed
      without real data
- [ ] **OptionsFlow entity-pickers** — replace `text.hph_src_*` text-boxes
      with HA-native entity selectors
- [ ] **COP-live transparency** — show `thermal_w / electrical_w` inputs
      alongside the COP value
- [ ] **GitHub Release tag (v0.9.0)** so HACS shows update notifications
- [ ] **Per-platform translations** `translations/{en,de,nl}.json`
- [ ] **Repairs panel** for missing frontend cards (apexcharts, mushroom, …)
- [ ] **pytest-based test suite** mocking HA core
- [ ] **HACS-default-repository submission**
- [ ] **PV self-consumption net cost sensor** (`hph_cost_today_net`)
- [ ] **Recorder exclusions** — identify and exclude intermediate/instantaneous
      HPH sensors from HA recorder LTS to reduce DB growth (standby power,
      live COP, thermal power, etc.)
- [ ] **COP by mode re-add** — per-mode COP cards (`sensor.hph_cop_monthly_heating`,
      `_monthly_dhw`) on Efficiency view
- [x] **Vs-same-month-last-year comparison** — `hph_cop_change_yoy_pct` replacing
      previous-month comparison; thermal + electrical change-pct sensors added
- [x] **Long-term export bugfix** — `hph.export_now` honours csv/json/xlsx selector,
      discovers entities dynamically
- [x] **Historical LTS backfill** — `scripts/backfill_from_external_meters.py`
      imports Sensostar + Shelly history (monthly/daily/hourly) including
      daily COP, monthly COP, and seasonal SCOP into HA LTS
- [x] **external_energy thermal power fix** — `hph_thermal_power_active` now
      reads Sensostar power sensor in `external_energy` mode (was falling
      through to calculated ΔT×flow)

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

## Backlog (post-v1.0 ideas)

User-suggested features that don't yet have a target version.

- [ ] **Per-mode long-term statistics with multi-year overlay views.**
      What: persistent LTS for thermal and electrical kWh **and** COP
      split by mode (heating / DHW / cooling), browseable across years
      from the dashboard — click a metric, step through years, overlay
      two or more years on the same chart. Year-on-year comparisons
      already exist as point values (`hph_*_change_yoy_pct`); this is
      the visual / drill-down layer on top.
      Why: answer "did we use more hot-water energy this year than last?"
      without leaving HA for Grafana.
      Existing primitives: `hph_thermal_*_split_{heating,dhw,cooling}`,
      `hph_cop_monthly_heating/dhw`, `hph_cop_yearly_heating/dhw`.
      Missing: multi-year UI and reliability story for mode-split vs.
      external Shelly total.
      Effort: ~6–10 h once scheduled.

- [ ] **Weather-source-adapter package** — swappable weather providers
      (DWD / OpenWeatherMap / Met.no / local weather station);
      `sensor.hph_scop_weather_adjusted`; DWD recipe for DE users.

## Out of scope

- Cloud features (HeatPump Hero stays 100 % local)
- Replacing kamaradclimber/heishamon-homeassistant — we wrap it, not duplicate it
- Standalone control without an underlying heat-pump integration

## Contributing

Issues with concrete use-cases very welcome. Before opening a PR, please
read the design principles in [CLAUDE.md](../CLAUDE.md), in particular
the universality, advisor schema, source-adapter, and diagnostics
conventions. Per-vendor recipes in `docs/vendors/` are great first contributions.
