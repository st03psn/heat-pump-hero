# Changelog

All notable changes to HeatPump Hero. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and HeatPump Hero adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] — 2026-05-09

### Added — advisor extensions

`packages/hph_advisor.yaml` — three new advisors aggregated into the
summary traffic-light:

- **Pump-curve recommendation** (`hph_advisor_pump_curve`). Reads the
  rolling 7-day mean and standard deviation of the supply/return spread,
  sampled only while the compressor runs. Recommends pump-speed
  adjustment when mean is >2.5 K off the target_dt setpoint; flags
  high-variance / PWM behaviour as informational. New supporting
  sensors: `sensor.hph_water_spread`, `sensor.hph_spread_7d_mean`,
  `sensor.hph_spread_7d_stdev`. New thresholds:
  `input_number.hph_advisor_pump_spread_min_samples` (default 200).
- **Efficiency-drift detection** (`hph_advisor_efficiency_drift`).
  Reads `sensor.hph_scop_change_year_pct` (already exposed by the
  efficiency package). Critical at ≤ −20 % YoY, warn at ≤ −10 %.
  Message explicitly calls out HDD weather-adjustment caveat so users
  don't chase phantom regressions caused by mild winters.
- **DHW timing recommendation** (`hph_advisor_dhw_timing`).
  Tracks DHW boost frequency via `counter.hph_dhw_fires_today` (new),
  rolled into a 7-day rolling mean (`sensor.hph_dhw_fires_7d_mean`)
  through a daily snapshot at 23:59. Captures the last 14 DHW start
  hours into `input_text.hph_dhw_start_hours` for visibility.

### Added — programs (new package `hph_programs.yaml`)

Multi-day / scheduled service programs separated from regular control
automations. Both gated by `input_boolean.hph_ctrl_master`,
individually toggleable, default OFF.

- **Legionella program** — weekly anti-legionella DHW boost. Configurable
  weekday, start hour, target temperature (55-75 °C, default 65), and
  hold duration (10-120 min, default 30). Logs last successful run;
  status sensor exposes ok/due/overdue/disabled. Skips if a recent run
  is logged within 6 days (DST safety).
- **Screed dry-out program** — three profiles per ISO EN 1264-4 /
  DIN 18560-1: `functional_3d` (3-day functional), `combined_10d`
  (3-day functional + 7-day curing), `din_18560_28d` (full 28-day
  cement-screed protocol). Daily target supply temperature is pushed to
  the configured Z1 heat-curve target_high write entity at 00:01.
  Status + per-day target sensors visible in the dashboard.

### Added — control vendor adapter

`packages/hph_models.yaml` now also defines write-target helpers:
`input_text.hph_ctrl_write_quiet_mode`, `_force_dhw`,
`_z1_curve_high`, `_z1_curve_low`, `_dhw_target`. All control
automations in `hph_control.yaml`, `hph_control_extensions.yaml`, and
`hph_programs.yaml` now resolve write targets at runtime through these
helpers. Vendor-preset auto-fill extended to set them alongside the
read helpers. Service domains (select / button / number) remain
hard-coded per write target — bridging different domains across vendors
still requires forking the relevant action.

### Added — second Heishamon vendor preset

`panasonic_heishamon_mqtt` — for users who imported HeishaMon's bundled
MQTT YAML packages directly (entity prefix `aquarea_*`) instead of
installing kamaradclimber's custom integration. Auto-fills all 17 read
helpers and all 5 write helpers in one click.

### Added — dashboard surface

`dashboards/hph.yaml`:

- **Optimization view** — three new advisors appended to the
  recommendations entities list and the markdown detail card; new
  thresholds (`hph_advisor_drift_warn_pct`, `_drift_crit_pct`,
  `_dhw_max_fires_per_day`, `_pump_spread_min_samples`) added to the
  power-user threshold card.
- **New "Programs" view** (`path: programs`, icon `mdi:calendar-clock`)
  — status mushroom cards for legionella + screed, full bedien-blocks
  for both, profile-reference table for the screed protocols.
- **Configuration view** — new "Control write targets" entities card
  exposing the five `input_text.hph_ctrl_write_*` helpers.
- **Mobile view** — two new conditional mushroom cards: legionella
  status (only shown when not disabled) and screed-running indicator
  (only when `running`). Both deep-link to `/hph/programs`.

### Notes

- `hph_advisor.yaml` summary now aggregates 12 advisors (was 9).
- Read paths in `hph_control.yaml` migrated from
  `sensor.panasonic_heat_pump_main_z1_water_temperature` to the
  source-facade `sensor.hph_source_dhw_temp` for the Solar-DHW boost.
- The new write-helper layer is an additive change: existing installs
  retain their previous behaviour because defaults match the kamaradclimber
  entity-IDs, and the helpers are picked up automatically on any
  vendor-preset re-apply.

## [0.7.2] — 2026-05-09

### Added — multi-platform read-only bridge

`packages/hph_bridge.yaml` (new) — republishes a curated whitelist of
~50 derived `sensor.hph_*` (COP, SCOP, advisor states, diagnostics,
cycles, schema, model) back onto MQTT so non-HA platforms (ioBroker,
openHAB, Node-RED, secondary HA instances) can read the computed
metrics. HA stays the compute primary; the bridge is read-only by
design — control paths remain HA-only.

- Helpers: `input_boolean.hph_bridge_enabled` (default off),
  `input_text.hph_bridge_prefix` (default `hph`)
- Topic schema: `<prefix>/<domain>/<entity_id>/state` (raw value) and
  `…/attributes` (all attributes as JSON), `retain=true`
- Live-update automation `hph_bridge_publish_state` — indexed state
  trigger, no event-loop overhead
- Initial-publish automation `hph_bridge_publish_initial` — fires on
  HA start and on enable transition; persistent notification confirms
- Clear-on-disable automation `hph_bridge_clear_on_disable` — empty
  retained payloads drop topics at the broker (MQTT-3.1.1 §3.3.1.3)
- Status sensor `sensor.hph_bridge_last_publish` (timestamp,
  available only when bridge is enabled)
- Skip-on-`unknown`/`unavailable` condition prevents garbage publishes
  during HA restarts

### Hardware-abstraction guarantee

Bridge republishes only `sensor.hph_*` (computed via the
source-adapter facades), never `panasonic_heat_pump_*` or other vendor
raw entities. Topic names stay stable across heat-pump and integration
swaps — only the ~17 source-helpers need reconfiguration on the HA
side; downstream subscribers are unaffected.

### Added — docs

- `docs/multivendor_bridge.md` — topic schema reference, recipes for
  ioBroker (MQTT adapter), openHAB (Generic MQTT Thing), Node-RED
  (mqtt-in node), secondary HA, plus limitations and whitelist
  extension procedure

### Changed

- Dashboard Configuration view: new "Multi-platform bridge
  (read-only)" section with toggle, prefix input, last-publish
  timestamp, and link to the recipes doc
- Roadmap: v0.8 expanded with weather-source-adapter,
  DWD recipe, weather-adjusted SCOP, and optional defrost-forecast
  advisor (groundwork for the efficiency-drift YoY item which v0.8
  has now delivered).

## [0.7.1] — 2026-05-09

### Changed

- **Project name**: Heat Pump Hero → **HeatPump Hero** (display name
  contracted; HPH initials and entity-ID prefix `hph_` unchanged).
- **Language policy**: repo is now English-only until v1.0. Translations
  of descriptive content (README / info / docs) resume at v1.0 alongside
  the v0.9 Python custom integration that enables per-locale dashboard
  strings. Until then, translation PRs add maintenance burden without
  user value.

### Removed

- `README.de.md`, `README.nl.md`, `info.de.md`, `info.nl.md`,
  `CLAUDE.de.md`, the entire `docs/de/` directory. No production
  installs depended on them.
- Language-switcher headers (`🌐 English (this file) · ...`) from every
  remaining English file.
- `CONTRIBUTING.md → Translation convention` block replaced with the
  shorter "Language policy" block; the `i18n` issue tag is no longer
  needed pre-v1.0.

### Notes

- `tests/_strip_and_rebrand.py` is the one-shot script used to apply
  this rename + header removal across 50 files.

## [0.7.0] — 2026-05-09

### Added — control extensions

`packages/hph_control_extensions.yaml` (new) — three opt-in,
master-switch-gated, well-bounded control automations:

**1. Adaptive heating curve (self-learning)**
- Reads `sensor.hph_advisor_analysis.recommendation_k` (from L1 analysis)
- Weekly (Sunday 04:00) shifts heating curve by min(|rec_k|, max_step_k);
  default cap ±0.5 K per cycle
- Hard-bounded to absolute supply-temp limits (default 22-50 °C)
- 6-day cooldown so manual adjustments aren't overwritten
- Persistent notification on every change for full transparency

**2. Price-driven DHW (Tibber / aWATTar)**
- Configurable price + daily-mean price entity sources
- Fires DHW boost when current < daily_mean × threshold (default 0.85)
- Only when DHW tank is ≥5 K below target
- Daily fire limit (default 1) with auto-reset counter

**3. Weather-forecast pre-heating**
- Configurable forecast temperature entity (e.g. OpenWeatherMap 6h ahead)
- Boosts curve by N K (default 2 K) for 4 hours when forecast drop ≥ N K
  (default 8 K) and current outdoor > 0 °C
- Auto-reverts after the boost window
- State sensor `input_boolean.hph_ctrl_forecast_preheat_active` indicates
  whether a boost is currently running

All three are individually toggleable, off by default, and require
the global `input_boolean.hph_ctrl_master` to also be on.

### Changed

- `tests/smoke.py`: `hph_control_extensions.yaml` whitelisted in
  ALLOWED_HARDCODE because it writes to Heishamon-specific heat-curve
  number entities and the DHW force button (documented vendor-specific
  write paths)
- Configuration view: new "Control extensions (v0.7)" section with
  3 sub-sections (adaptive / price / forecast) for the new helpers
- Roadmap: v0.7 marked complete; v0.8 = Python custom integration

## [0.6.0] — 2026-05-09

### Added — rebrand and analysis layer

**Rebrand** — project renamed `HeishaHub` → **HeatPump Hero (HPH)**.
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
  - For installs added mid-life — re-creates pre-HeatPump Hero history
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
  HeatPump Hero adjusts compressor Hz and supply-T° expectations to match
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
