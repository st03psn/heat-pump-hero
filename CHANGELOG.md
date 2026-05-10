# Changelog

All notable changes to HeatPump Hero. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and HeatPump Hero adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Hero card and KPI cards mis-labelled live power as kW.**
  `sensor.hph_thermal_power_active` and `sensor.hph_electrical_power_active`
  are in W (per `unit_of_measurement: W`), but the Overview Hero card and
  the two power KPI cards on the Mobile view appended `kW` to the raw
  W value — so 2 W standby showed as "2.0 kW". Energy integrals
  (`hph_*_daily/_runtime/standby`) were always correct because the
  integration platform converts W → kWh via `unit_prefix: k`. Display
  now auto-formats: `<1000 W` shown in W, `≥1000 W` shown in kW with 2
  decimals.

- **`hph.export_now` ignored the format selector and missed many sensors.**
  The integration export wrote CSV regardless of `select.hph_export_format`
  and only covered a hardcoded 15-entity subset (no `_active`, no per-mode
  splits, no advisor/diagnostics). Replaced with dynamic discovery of all
  `sensor.hph_*` / `binary_sensor.hph_*` / `number.hph_*` (excluding
  source-facade mirrors), proper `csv` / `json` / `xlsx` writers (xlsx via
  openpyxl), and error propagation: failures now raise
  `HomeAssistantError` to the caller and surface a notification, instead
  of being silently logged. Each row also carries `friendly_name`.

### Changed

- **Comparison sensors now compare year-over-year, not month-over-month.**
  `sensor.hph_cop_change_month_pct` (current vs previous calendar month)
  was near-useless — heating load swings between adjacent months for
  weather reasons, not efficiency reasons. Replaced with
  `sensor.hph_cop_change_yoy_pct` (current vs same calendar month last
  year). Same change for `hph_thermal_change_yoy_pct` and
  `hph_electrical_change_yoy_pct`. New baseline sensors
  `hph_*_same_month_last_year` use HA's `statistic_during_period`
  template function over the monotonic `hph_thermal_energy` /
  `hph_electrical_energy` integrations (HA 2024.4+). The
  `hph_efficiency_trend` aggregator and the Efficiency dashboard view
  now read from the YoY sensors. Bridge whitelist updated.

  *Migration:* the old `*_change_month_pct` entity IDs are gone.
  Recorder history for those specific entities resets; if a Lovelace
  YAML override outside the bundle references them, replace with
  `*_change_yoy_pct`.

## [0.9.0-rc5] — 2026-05-10

### Fixed

- **`binary_sensor.hph_compressor_running` did not exist**. Every
  `is_state('binary_sensor.hph_compressor_running','on')` check returned
  False, silently breaking cycle counting, CCC/SoftStart, the spread gate,
  and DHW fire tracking. Promoted to a real `binary_sensor` with
  `device_class: running`.

- **COP daily / monthly / SCOP too low (e.g. 1.36 with COP live = 8)**.
  `_active` energy integrals included ~1 kWh/day standby load. Fixed with
  runtime-gated integrals (new `_runtime` sensors + utility_meters): COP
  denominators now use compressor-on-only energy. `_active` totals remain
  for billing / cost calculations.

- **Dashboard charts stuck on "Loading…"**: Added `apex_config.noData`
  text to all ApexCharts cards so a fresh install shows a "Sammele Daten"
  message instead of an indefinite spinner.

- **Cycling 7-day chart never populated**: `number.*` entities have no
  LTS. Replaced statistics block with `group_by: { func: max, duration: 1d }`
  over raw history (daily peak = day total after midnight reset).

- **"Heating limit — Entität nicht gefunden"**: Wrapped in conditional
  pair — entities-card shows when the sensor is ready, markdown card
  explains what to expect until then.

- **Energy totals showed 5 decimal places**: Replaced entities-cards
  on Efficiency view with markdown tables that apply `| round(2)`.

- **OptionsFlow blank entity fields caused validation errors**: EntitySelector
  rejects empty-string defaults. Schema is now built dynamically — `default=`
  only attached when the user has a stored value.

- **Entity-ID naming drift**: Six `platform:statistics` sensors were slugified
  to `sensor.heatpump_hero_*` instead of `sensor.hph_*`. Renamed in the
  deployed package; existing installs auto-migrated via `_migrate_entity_ids()`
  in `__init__.py`.

- **Double electricity-price helper**: Removed duplicate `text.hph_ctrl_price_entity`;
  price-DHW coordinator now reads from the unified
  `text.hph_electricity_price_entity`.

- **COP-by-mode card removed**: The per-mode COP split used `_active` energy
  (standby-poisoned by tariff routing) and produced misleading values. Removed
  from the dashboard; a clean implementation requires mode-gated energy per
  mode, deferred to v1.0.

### Added

- **`sensor.hph_thermal_power_runtime` / `_electrical_power_runtime`** —
  power sensors gated on `binary_sensor.hph_compressor_running`. Six new
  `utility_meter` entries (`_runtime_daily/monthly/yearly`) accumulate
  only compressor-on energy; `hph_standby_electrical_daily` = total − runtime.

- **Mode-gated power sensors** (`sensor.hph_electrical_power_heating_runtime`,
  `_dhw_runtime`, `_cooling_runtime`): gated on both compressor running and
  the current operating mode. Six corresponding utility_meters
  (`_heating/dhw/cooling_runtime_monthly/yearly`) enable per-mode runtime
  energy accounting. Foundation for future per-mode SCOP.

- **`sensor.hph_source_health`** + **`sensor.hph_advisor_source_health`** —
  detects when a configured external meter goes silent (unavailable or no
  new value while compressor runs for > 60 min). Aggregated into
  `hph_advisor_summary`; conditional chip on the Overview status bar.

- **New thermal-source mode `heat_pump_internal`** — reads Heishamon's
  factory-calibrated `heat_power_production` sensor instead of computing
  from ΔT × flow × cp.

- **"Heat pump" dashboard view (8th tab)** — all native Panasonic / Heishamon
  controls in one place: mode, quick-actions, DHW grid, heating curves Z1
  (+ conditional Z2), advanced settings. Optimization view now stays focused
  on HPH advisors.

- **`hph.recompute` service** — forces re-evaluation of all derived sensors
  without waiting for an upstream state change. Auto-triggered when any
  `text.hph_src_*` or `select.hph_*_source` helper changes.

- **Panasonic Service Cloud–inspired dashboard redesign** — Hero card with
  mode-color left border (card-mod), 5-column KPI strip, 2-column
  status-panel + charts layout, COP color-coding (green ≥ 3.5 / amber ≥ 2.5 /
  red < 2.5), energy-by-mode progress bars with inline gradient.

- **Legionella program migrated to Python integration** (previously required
  YAML). Four helpers (`number.hph_prog_legionella_target_c`,
  `_hold_min`, `_hour`; `select.hph_prog_legionella_weekday`), one switch,
  one datetime for last-run stamp — all now registered via `const.py`.
  `hph.run_legionella_now` service registered in `__init__.py`. Weekly
  schedule in `coordinators/programs.py` (hourly tick checks weekday +
  hour). Programs OptionsFlow step for the config wizard.

- **COP live transparency** — Hero card primary line appends "(×0 defrost)"
  during defrost cycles; Analysis COP live card secondary shows
  `thermal W / electrical W` inputs + defrost flag.

- **`scripts/hph_import_legacy_stats.py`** — backfills long-term statistics
  from existing `wp_waerme_kwh_monat` / `wp_strom_kwh_monat` utility_meter
  sensors. Computes monthly COP and SCOP per heating season (Jul–Jun) and
  imports via `recorder/import_statistics`. `--dry-run` flag prints a table
  without writing. Fills the "COP last 13 months" and "SCOP per season"
  charts for installations that pre-date HPH.

- **Smoke test: bundled dashboard entity-reference check** — scans
  `hph.yaml` for every `<domain>.hph_*` reference and verifies it resolves
  against const.py / sensor_templates / hph_efficiency.yaml. Catches
  "Entität nicht gefunden" before deploy.

### Changed

- **Overview merged with Mobile tab** — 8 tabs → 7. Masonry layout handles
  phones; separate Mobile tab removed.
- **Cost cards de-duplicated** — price configuration lives only in
  Configuration view; Efficiency view shows values only.
- **Programs view reduced** — one-off legionella service button +
  24h DHW graph + screed guidance. The screed entities remain in the
  coordinator but are no longer surfaced on the dashboard.
- **Chart heights** bumped 160-220 → 260-360 px for readability.
- **Vendor preset restricted to Panasonic** for v0.9 — other presets
  labelled "*Coming soon (v1.0)*" in the dropdown.

### Deferred

- **Year-over-year comparison sensors** ("vs same calendar month last
  year"): needs a Python coordinator hitting `recorder/statistics_during_period`.
  Will land with Stage 4 (Demo mode) so the new sensors can be exercised.
- **Stage 4 (Demo mode)**: synthetic 13-month history injection
  (`switch.hph_demo_mode` + `hph.demo_seed_history`).

## [0.9.0-rc4] — 2026-05-10

### Fixed

- **utility_meter platform completely broken**: `offset: days: 181` is
  rejected by HA 2024.4+. Because any invalid config in the block fails
  the entire platform, all 12 utility_meter sensors (daily/monthly/yearly)
  stopped loading → COP today/month/season = 0 and all energy entities
  unavailable. Fixed by using `cron: "0 0 1 7 *"` (Jul 1 at midnight) for
  the four yearly meters; daily/monthly meters are unchanged.
- **Blocking I/O on event loop**: `_load_definitions()` in sensor.py and
  binary_sensor.py read YAML files synchronously inside `async_setup_entry`.
  HA 2026.x detects and warns about this. Moved to
  `hass.async_add_executor_job(_load_definitions)`.
- **Duplicate sensor definition**: `hph_efficiency_trend` appeared twice in
  `sensor_templates.yaml` (once with emoji templates, once clean). Second
  (correct) copy kept; first removed.
- **Config data lost on reconfigure**: Options flow stores to `entry.options`
  but setup only read `entry.data`. Fixed with
  `merged = {**entry.data, **entry.options}` in `async_setup_entry`.
- **External thermal power not propagated after reconfigure**: Same root
  cause as above; now uses the merged config dict.
- **Source mode labels showing raw values** (`heat_pump_internal` instead
  of "Internal (heat pump sensor)"): Added `_attr_translation_key` to
  select entities and `entity.select.*` translations in strings.json / en.json.
- **Energy values showing excessive decimals**: Added `| round(2)` to
  `hph_thermal_energy_active` and `hph_electrical_energy_active` templates.
- **Export creates a directory instead of a file**: Detects when target path
  has no extension or is an existing directory; auto-generates
  `hph_export_<timestamp>.<fmt>` inside it.
- **`device_class`/`state_class` invalid in `platform: integration`**: The
  Riemann sum integration does not accept these keys — they're inferred from
  the source sensor. Removing them unblocked the cascade failure.
- **Sensor startup race condition**: Template sensors started with
  `_raw_available = True`, causing the first evaluation (before select
  RestoreEntity completes) to emit a wrong energy value. Utility_meter
  interpreted the drop as a meter reset and zeroed the daily counter.
  Fixed with `_initialized = False`; sensors are unavailable until the
  first template evaluation completes.

### Changed

- Default export path changed from `/config/www/hph_exports` (web-accessible)
  to `/config/hph/exports` (private, inside the integration config dir).
- Uninstall cleanup now **preserves** `/config/hph/exports/` (user data).
  Only `dashboard.yaml` and `/config/www/hph/` (auto-generated SVGs) are
  removed. A log message reports the preserved path.
- Entity selector fields in the config/options flow (electricity price,
  PV surplus, price signal, forecast entity) are now proper dropdowns
  instead of free-text fields.

---

## [0.9.0-rc3] — 2026-05-09

### Added — Phase 3: Python automation coordinators, zero YAML deployment

All 23 automations from the v0.8 YAML packages have been ported to
Python coordinators in `custom_components/hph/coordinators/`. The
integration is now fully self-contained:

| Coordinator | Automations ported |
|---|---|
| `coordinators/cycles.py` | cycle start/stop, daily counter reset |
| `coordinators/advisor.py` | DHW fire tracking, heating-limit record, daily rollover |
| `coordinators/diagnostics.py` | error-change log + persistent notification |
| `coordinators/control.py` | CCC short-pause block, SoftStart, Solar-DHW (5-min PV surplus), quiet night on/off |
| `coordinators/control_ext.py` | adaptive curve (Sunday 04:00), price-DHW (hourly check + daily reset), forecast preheat (4h boost) |
| `coordinators/programs.py` | legionella weekly program (wait_template up to 4 h), screed arm, screed daily advance |
| `coordinators/bridge.py` | MQTT bridge publish-on-change, initial publish, clear-on-disable |
| `coordinators/export.py` | scheduled export (daily / weekly / monthly) |
| `coordinators/efficiency.py` | tariff switch (operating mode → utility meter tariff) |
| `coordinators/models.py` | model threshold apply, vendor preset re-apply at runtime |

The `hph.export_now` service is now a real Python implementation that
writes a CSV snapshot from HA states.

### Changed

- `bootstrap.py` now deploys **one** YAML file (`hph_efficiency.yaml`)
  instead of 11. `hph_efficiency.yaml` is a pure HA platform config
  (utility_meter + integration sensors) — there is no Python API to
  create these from a custom integration. All automation logic is
  removed from the file.
- `bootstrap.py` migration step: on first load, removes any
  `hph_*.yaml` files from `<config>/packages/` that were deployed by
  v0.8 or v0.9-rc1/rc2 (excluding `hph_efficiency.yaml`).
- `data/packages/` now contains **only** `hph_efficiency.yaml`.

### Deleted

- `custom_components/hph/data/packages/hph_advisor.yaml`
- `custom_components/hph/data/packages/hph_analysis.yaml`
- `custom_components/hph/data/packages/hph_bridge.yaml`
- `custom_components/hph/data/packages/hph_control.yaml`
- `custom_components/hph/data/packages/hph_control_extensions.yaml`
- `custom_components/hph/data/packages/hph_cycles.yaml`
- `custom_components/hph/data/packages/hph_diagnostics.yaml`
- `custom_components/hph/data/packages/hph_export.yaml`
- `custom_components/hph/data/packages/hph_models.yaml`
- `custom_components/hph/data/packages/hph_programs.yaml`

---

## [0.9.0-rc2] — 2026-05-09

### Added — Phase 2: programmatic sensor platforms

`custom_components/hph/sensor.py` and `binary_sensor.py` register
every `sensor.hph_*` and `binary_sensor.hph_*` entity that previously
came from `template:` blocks in v0.8 YAML packages. The Jinja
templates themselves are bundled internally
(`custom_components/hph/data/sensor_templates.yaml` and
`binary_sensor_templates.yaml`) and rendered at runtime by a generic
`HphTemplateSensor` / `HphTemplateBinarySensor` class that uses
`async_track_template_result` for state-tracking.

This is **not** a YAML deploy — the templates live inside the
integration package. User's `<config>/packages/` no longer carries
HeatPump Hero sensor definitions. Result:

- 72 `sensor.hph_*` entities + 6 `binary_sensor.hph_*` entities
  registered programmatically by the integration
- All `unique_id`s preserved → recorder history continuity
- HACS update of the integration brings new sensor logic without any
  YAML reload step on the user side
- Bundled `data/packages/` shrinks from 13 files to 11 (now-empty
  `hph_core.yaml` and `hph_sources.yaml` removed)

The template-driven approach is deliberately conservative — it
preserves all v0.8 advisor messages, fault-code logic, schema
detection, COP/SCOP calculations 1:1 without re-implementation risk.
A post-v1.0 performance pass can rewrite hot-path sensors as fully
native Python `SensorEntity` subclasses if measurement shows that's
needed.

### Known limitations carried over from rc1

- Counter increments still need Phase 3 (cycle tracking, dhw fires,
  price-dhw fires, short-cycle detection).
- Statistics / integration / utility_meter platforms still ship as
  YAML in `data/packages/*.yaml` because HA exposes no programmatic
  registration API for them. Phase 3 may move them to coordinators.

## [0.9.0-rc1] — 2026-05-09

### Added — Python custom integration (HACS-installable)

`custom_components/hph/` (new) — replaces script-based deploy with a
proper HACS Custom Integration. Phase 1 of the v0.9 milestone:
helpers are programmatic, sensors and automations remain in YAML
packages that the integration deploys at install time (a temporary
bootstrap, removed in phase 3).

- `manifest.json` — domain `hph`, integration_type `hub`, config_flow
  enabled, single-instance.
- `__init__.py` — async_setup_entry deploys YAML, registers
  dashboard, applies vendor preset / pump model from the wizard.
  async_remove_entry aggressively cleans every file the integration
  ever wrote (recorder DB stays — HA-standard behavior).
- `config_flow.py` — 4-step wizard (vendor / model / optional
  external sensors / confirm). Options-flow re-runs the wizard from
  the integration's Configure button.
- `bootstrap.py` — copies bundled YAML packages, dashboard YAML,
  asset SVGs and the legacy setup blueprint into `<config>/packages/`,
  `<config>/hph/`, `<config>/www/hph/`, `<config>/blueprints/script/hph/`.
  Also auto-registers the Lovelace dashboard panel (URL `/hph`,
  icon `mdi:heat-pump`) so the user never has to "Add Dashboard from
  YAML" manually.
- Helper platforms (`text.py`, `number.py`, `select.py`, `switch.py`,
  `datetime.py`, `button.py`) — replicate every input_text,
  input_number, input_select, input_boolean, input_datetime, counter,
  manual-trigger button from the previous YAML packages with
  identical unique_ids.
- `helpers/vendor_apply.py` — applies vendor preset / pump model on
  config-flow submit (one-shot helper-seeding without YAML automations).

### Changed

- `hacs.json` — category implicit Integration (removed obsolete
  Plugin-only fields `content_in_root` and `filename`); HACS
  detects the integration automatically from
  `custom_components/hph/manifest.json`.
- `README.md` — HACS Custom Repository install promoted to primary
  path. Script-based install demoted to "legacy" section pointing at
  `docs/installation.md` and `docs/installation_windows.md`.

### Migration notes for v0.8 users

Helper entity_ids change platform domain in v0.9:

| v0.8 (YAML packages) | v0.9 (Python platforms) |
|---|---|
| `input_text.hph_*` | `text.hph_*` |
| `input_number.hph_*` | `number.hph_*` |
| `input_select.hph_*` | `select.hph_*` |
| `input_boolean.hph_*` | `switch.hph_*` |
| `input_datetime.hph_*` | `datetime.hph_*` |
| `counter.hph_*` | `number.hph_*` |

Recorder history of these helpers is **not preserved** across the
domain change — the historical values were UI configuration anyway,
not measurement data. **Sensors (`sensor.hph_*`, `binary_sensor.hph_*`)
are untouched in phase 1 and keep their full history.**

Phase 2 (template sensors → Python) is the next deliverable; phase 3
(automations → Python coordinators) finishes the port and removes the
bootstrap entirely so the integration is fully self-contained.

### Known limitations in this RC

- Counters (`hph_cycles_today`, `hph_dhw_fires_today`, etc.) are
  exposed as numbers but not auto-incremented — the cycle-tracking
  automations that fed them in v0.8 still reference the old
  `counter.*` service domain. Auto-increments come back in phase 3.
- The Configuration view's "Vendor preset" selector is a Python
  `select` entity now, but its companion auto-fill automation (in
  `packages/hph_models.yaml`) still expects the old domain. Use the
  config-flow / options-flow wizard to pick a vendor instead — it
  takes effect immediately and reliably.

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
