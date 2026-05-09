# Changelog

All notable changes to Heat Pump Hero. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Heat Pump Hero adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] — 2026-05-09

### Added — rebrand and analysis layer

**Rebrand** — project renamed `HeishaHub` → **Heat Pump Hero (HPH)**.
- All identifiers `heishahub_*` → `hph_*` (entity IDs, helper names,
  package filenames, dashboard path)
- All display strings updated across READMEs (EN/DE/NL), info files,
  CLAUDE.md, docs, mockup SVGs
- No migration path needed — explicit decision since no production
  installs exist yet

**Analysis module** (`packages/hph_analysis.yaml`)
- Layer 1: rule-based statistical observation
  - Indoor-temp source helper + target helper (optional, with fallback default)
  - Rolling smoothed deviation via `statistics` platform (≤7 days)
  - Concrete recommendations in K via the new
    `sensor.hph_advisor_analysis` (state + recommendation_k attribute)
  - Configurable dead band so trivial deviations don't nag
- Layer 2: linear regression Python script
  - `scripts/analyze_heating_curve.py` fits supply_temp = a + b·outdoor_temp
    over the last N days of compressor-on samples
  - Outputs slope/intercept/R² with plain-language verdict
  - Writes to `input_text.hph_heating_curve_recommendation` for the
    advisor to surface
  - Schedulable via shell_command + automation (snippet in docs/analysis.md)
- Aggregate advisor summary now considers 9 advisors (was 8)
- Optimization view: new analysis recommendation card

**Installer improvements** (`scripts/install.sh`)
- Pre-flight checks: python3 / kamaradclimber heishamon integration /
  6 HACS frontend dependencies
- DB recommendation prompt — sqlite / mariadb / postgresql / skip,
  with clear next-steps for non-default choices
- `--db` flag for non-interactive runs
- Now also installs the export / import / heating-curve scripts to
  `<config>/scripts/` and chmods them executable

**Docs**
- `docs/analysis.md` — explains the 3-layer KI/observation continuum,
  why pure ML/LLM isn't needed for heating-curve fitting, worked example
- Vendor / installation / database docs updated for new branding

## [0.5.0] — 2026-05-09

### Added

- **Export module** (`packages/hph_export.yaml` + `scripts/export_hph.py`)
  - UI helpers: target path, format (csv/json/xlsx), period (last day/week/month/year/all), schedule (manual/daily/weekly/monthly)
  - `script.hph_export_now` for manual triggers
  - Scheduled automations (daily/weekly Mon/monthly 1st at 03:00)
  - Python script reads HA REST API, writes one file per entity
- **Import module** (`scripts/import_csv_to_ha_stats.py`)
  - Backfills HA long-term statistics from CSV via `recorder/import_statistics` websocket
  - For installs added mid-life — re-creates pre-Heat Pump Hero history
- **Database recommendations** (`docs/database.md`) — when SQLite is fine, when to switch to MariaDB / PostgreSQL, InfluxDB-for-analytics pattern
- **Naming proposal** (`docs/naming_proposal.md`) — HeatLens recommended as universal rename to drop the Heishamon-specific branding

### Fixed

- **Panasonic M-series compressor min Hz**: 12 → **16** (community-verified empirical floor; spec-sheet estimate was off)
- T-CAP min Hz aligned to 16 (was 14, no community evidence for 14)

## [0.4.0] — 2026-05-09

Major step toward v1.0: **diagnostics module**, **vendor & model selectors
with auto-fill**, **integration UI mockup**, broader hardware support
including the **Panasonic M-series (R290 flagship)**.

### Added

- **Panasonic fault-code diagnostics** (`packages/hph_diagnostics.yaml`)
  - 30+ H- and F-codes mapped to plain-language descriptions and severity
  - Model-specific commentary (J-series H23, R32/R290 H99, J/K H62 false alarms)
  - 5-event ring buffer + recurrence sensor for repeat patterns
  - Persistent notification on fault change with severity / message / model note
  - New advisor `hph_advisor_diagnostics` folds active fault +
    recurrence into the aggregate traffic-light tile
- **Vendor preset selector** (`input_select.hph_vendor_preset`):
  Panasonic Heishamon, Daikin Altherma, MELCloud, Vaillant mypyllant,
  Stiebel ISG, generic Modbus / MQTT — automation auto-fills all 17
  source-helpers in one click
- **Heat-pump model selector** (`input_select.hph_pump_model`):
  Panasonic J / K / L / T-CAP / **M (R290 flagship)** plus Daikin /
  Mitsubishi / Vaillant / Stiebel — auto-sets compressor min/max Hz,
  minimum flow, maximum supply temperature
- **Water-pressure trend advisor** (slow-leak detection): 7-day mean vs
  current; warns at −0.2 bar, critical at −0.4 bar
- **Integration UI mockup** at `docs/integration_mockup_setup.svg` and
  `docs/integration_mockup_dashboard.svg` — design preview of the v1.0
  Python custom integration; YAML-based equivalents ship now in v0.4
- **Diagnostics doc** at `docs/diagnostics.md` — full code reference,
  severity classification, model-specific commentary, source-entity table
- **Mockup doc** at `docs/integration_mockup.md` — explains the
  integration-vs-YAML mapping
- New active-fault tiles in Optimization view (full-page) and Mobile
  view (only when fault is present, conditional)

### Changed

- HA minimum version lowered from 2025.4.0 (too aggressive) to **2024.4.0**
- README / info — features list, status badge, version reference
- `docs/vendors/panasonic_heishamon.md` — full M-series writeup including
  unofficial Heishamon firmware status, plus model characteristics table
- Setup blueprint now reports auto-detected components (HK2 / DHW /
  buffer) and the auto-selected schematic variant
- Aggregate advisor summary now considers 8 advisors (added diagnostics
  and pressure-trend)

### Notes for users

- Existing v0.3 helpers are preserved across the upgrade
- The vendor preset selector defaults to `keep_current`, so re-importing
  the package does not auto-clobber your existing source-helpers
- M-series owners: set the model selector explicitly during setup —
  Heat Pump Hero adjusts compressor Hz and supply-T° expectations to match
  R290 characteristics

## [0.3.0] — 2026-05-09

### Added

- Auto-detection of HK2 / DHW / buffer presence
- Schema variant `auto` mode follows detection; manual override still works
- 4 conditional Bubble-Cards, each with variant-specific hotspot positions
- COP heatmap (day-of-week × hour-of-day) + outdoor T° vs COP scatter
- Auto-detected heating-limit advisor (rolling 7-day avg of outdoor temp
  at end of compressor runs ≥ 30 min)
- Mobile view (panel-mode single-column layout)
- HK1+HK2+DHW and HK1+HK2+DHW+Buffer schematic SVGs
- HACS path-forward doc, vendor recipes, NL translation

## [0.2.0] — 2026-05-08

### Added

- Tariff splits (heating / DHW / cooling) in utility_meter
- HA Energy Dashboard via `*_active` energy sensors
- Real Grafana Flux queries (overview + multi-year SCOP/MAZ)
- Period-comparison sensors (vs last month / last year, in %)
- Source-adapter layer — every counter source swappable via UI helpers

## [0.1.0] — 2026-05-08

### Added

- Initial skeleton: 6 packages, 6-view dashboard, Bubble-Card SVG
  schematic with live hotspots, setup blueprint, install.sh, Grafana
  skeletons, bilingual EN/DE docs
