# CLAUDE.md — HeatPump Hero Project Context

This guide is for AI assistants (Claude Code) and new human contributors. It
explains the project in five minutes.

## What is HeatPump Hero?

HeatPump Hero is a **bundle** for Home Assistant that deploys a complete dashboard
and analytical layer onto a Heishamon-controlled Panasonic Aquarea heat pump
installation. It does **not** replace any integration — it **combines**
existing building blocks into something usable:

- Entities come from [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- HeatPump Hero provides: HA packages (template sensors, COP/SCOP calculation),
  Lovelace dashboard YAML, Bubble-Card SVG schematic, Grafana boards,
  setup blueprint.

## Working with Claude

- **Plan-first** for non-trivial edits: surface the change list (files,
  sections, rationale) before touching anything. No silent multi-file
  refactors.
- **Stop after 2 failures.** If a fix attempt fails the same check
  twice, stop and report the actual blocker rather than guessing.
- **No scope creep.** A request to add a sensor adds a sensor — no
  drive-by reformatting. File adjacent issues as separate proposals.
- **One concrete question on ambiguity.** If a user instruction has
  two reasonable interpretations, ask one specific question with
  candidate answers, not three open-ended ones.

## Design principles

1. **Universality.** Every template is `availability:`-guarded. A zone-1-only
   installation must work as well as a fully equipped one (zone 2 + DHW +
   buffer + solar + pool). No `unknown` sensors.
2. **Readable YAML.** No `!include` indirection inside templates, no Jinja
   `{% import %}`/`{% from %}`, no YAML anchors/aliases for non-trivial
   structure. Each card and sensor is self-contained at its top level.

## Commands

Local before commit:

- `py tests/smoke.py` — 6-section structural check (must exit 0)
- `yamllint -d "{extends: relaxed, rules: {line-length: disable, truthy: disable, comments: disable}}" .` — same config CI uses
- `python -m json.tool grafana/<file>.json` — Grafana JSON validation (per file)

Full HA syntax check (Docker, slower):

- `docker run --rm -v "$PWD:/repo" -w /repo ghcr.io/home-assistant/home-assistant:stable python -m homeassistant --script check_config -c /repo/tests/ha_check_config`

Install / deploy onto a real HA instance:

- `bash scripts/install.sh /path/to/ha/config [--db sqlite|mariadb|postgresql]`

CI (`.github/workflows/validate.yml`) runs all of the above plus HACS
validation on every push and PR. There is no separate `release.yml` —
release notes come from `CHANGELOG.md`.

## Repository layout

| Path | Purpose |
|---|---|
| `packages/hph_sources.yaml` | **Source adapter layer.** Defines `input_text` helpers for every underlying entity-ID (heat pump and external meters), plus active-source dispatcher template sensors. The only file that names heat-pump-specific entities. |
| `packages/hph_models.yaml` | **Vendor & model selectors** with auto-fill automations. Vendor preset sets all 17 source helpers on selection; model selector sets compressor / flow / supply-T° thresholds for the chosen Panasonic generation (J/K/L/T-CAP/M) or other vendor. |
| `packages/hph_diagnostics.yaml` | **Panasonic fault-code analysis** — 30+ H/F codes mapped to plain-language descriptions, severity, model-specific commentary; ring buffer of last 5 events; recurrence detection; persistent-notification flow. |
| `packages/hph_analysis.yaml` | **Analysis module** (L1 statistical observation). Indoor-temp deviation tracker + heating-curve recommendation surface (`recommendation_k` attribute on `sensor.hph_advisor_analysis`). |
| `packages/hph_export.yaml` | Manual + scheduled export of long-term values to CSV/JSON/XLSX. Triggers `scripts/export_heishahub.py` via `shell_command`. |
| `packages/hph_core.yaml` | Live sensors (thermal power, mode mapping, defrost, compressor running) — reads exclusively from `sensor.hph_source_*`. |
| `packages/hph_efficiency.yaml` | Energy integrals, utility_meter (with tariff splits), COP / daily / monthly / SCOP, period comparisons. |
| `packages/hph_cycles.yaml` | Cycle analysis: start/stop events, runtime/pause, counters, short-cycle detection. |
| `packages/hph_advisor.yaml` | Data-driven optimization recommendations with plain-language messages and an aggregate traffic-light. |
| `packages/hph_control.yaml` | Optional control automations (CCC, SoftStart, Solar-DHW, night Quiet-Mode) — master switch off by default. |
| `packages/hph_control_extensions.yaml` | v0.7 control extensions: adaptive heating curve (self-learning), price-driven DHW, weather-forecast pre-heating. All gated behind `input_boolean.hph_ctrl_master`. |
| `dashboards/hph.yaml` | Lovelace dashboard YAML (storage or YAML mode). |
| `dashboards/assets/*.svg` | Installation-schematic templates (Bubble-Card backgrounds). |
| `blueprints/hph_setup.yaml` | Script blueprint to seed helpers and verify install. |
| `scripts/install.sh` and `scripts/*.py` | Optional bash installer + Python helpers for export, import, and heating-curve regression. |
| `grafana/*.json` | Grafana dashboards (import-ready). |
| `grafana/telegraf_mqtt.conf` | Telegraf config for MQTT → InfluxDB. |
| `docs/` | Installation, tweaking, vendor recipes, diagnostics, export/import, database, naming, integration mockups. |
| `tests/` | Local smoke tests + HA Docker check_config harness. |
| `.github/workflows/` | YAML / JSON validation, smoke, Docker check_config. |

*(Source of truth: `ls packages/ scripts/ docs/` — this table drifts; PRs welcome.)*

## Naming conventions

- **HeatPump Hero-owned entities**: prefix `hph_` (e.g.
  `sensor.hph_scop`).
- **Source-facade entities** (resolved from configurable helpers):
  prefix `hph_source_*` (e.g. `sensor.hph_source_inlet_temp`).
  These are what every other package reads from.
- **Source helpers** (UI-configurable entity-ID strings):
  prefix `input_text.hph_src_*`.
- **External meter helpers**:
  prefix `input_text.hph_src_external_*`.
- **Active-source dispatchers** (what utility_meter / COP read):
  `sensor.hph_thermal_power_active`, `_thermal_energy_active`,
  `_electrical_power_active`, `_electrical_energy_active`.
- **Heat-pump native entities** (`panasonic_heat_pump_*`) are allowed in
  three places only: defaults in `hph_sources.yaml`, vendor-preset
  auto-fill payloads in `hph_models.yaml`, write targets in
  `hph_control*.yaml`. The whitelist is enforced by
  `tests/smoke.py:ALLOWED_HARDCODE` — adding any other location requires
  updating the whitelist with a one-line justification.
- **Dashboard views**: `overview`, `schema`, `analysis`, `efficiency`,
  `optimization`, `config`.

## Source-adapter architecture

Everything HeatPump Hero reads is funneled through `packages/hph_sources.yaml`:

```
input_text.hph_src_inlet_temp           ← user-configurable entity-ID
   │  default: sensor.panasonic_heat_pump_main_inlet_temperature
   ▼
sensor.hph_source_inlet_temp            ← facade (resolved)
   │
   ▼
sensor.hph_thermal_power                ← uses facade
   │
   ▼
sensor.hph_thermal_power_active         ← respects source-mode selector
   │
   ▼ (integration: Riemann sum)
sensor.hph_thermal_energy               ← kWh, total_increasing
   │
   ▼
sensor.hph_thermal_energy_active        ← either integrator OR external kWh meter
   │
   ▼
utility_meter.hph_thermal_*             ← daily/monthly/yearly + tariff splits
```

**Source modes** (`input_select.hph_thermal_source` / `_electrical_source`):

| Mode | Behavior |
|---|---|
| `calculated` (thermal) | Uses T_in/T_out × flow × cp via the facades. Heat-pump must expose temperatures and flow. |
| `heat_pump_internal` (electrical) | Reads the heat pump's own consumed-power sensor. |
| `external_power` | Integrates a user-provided power sensor (W) → kWh. Use for Shelly/IoTaWatt. |
| `external_energy` | Reads a user-provided kWh meter (`total_increasing`) directly — bypasses the integrator. Most accurate when you have a hardware heat meter or utility meter. |

**Swapping the heat pump:** change the relevant `input_text.hph_src_*`
helpers in the UI (Settings → Devices → Helpers). All read paths follow.
Write paths in `hph_control.yaml` are still heat-pump-specific by
nature — see the comment header in that file.

## Diagnostics module

The diagnostics package (`hph_diagnostics.yaml`) reads
`sensor.hph_source_error_code` and produces:

- `sensor.hph_diagnostics_current_error` — state = code, attributes
  hold severity / message / model-specific commentary
- `sensor.hph_diagnostics_recurrence` — count of same code in the
  last 5 events (ring buffer in `input_text.hph_diag_error_history`)
- An automation that timestamps every change, appends to the buffer, and
  raises / dismisses a persistent notification

Severity classification: `critical` / `warn` / `info` / `none`. The
classification arrays and per-code message branches live in
`hph_diagnostics_current_error` (in `hph_diagnostics.yaml`);
`tests/smoke.py:test_diagnostics_consistency` enforces every classified
code has a message branch. Adding a code: extend the YAML, run smoke.
Document the code in `docs/diagnostics.md`.

Adding model-specific commentary: extend the `model_note` template
similarly — it reads `input_select.hph_pump_model` so per-model
guidance is keyed off the same selector that drives compressor / flow
thresholds.

## Vendor presets and model selector

`hph_models.yaml` defines two independent selectors:

1. **`input_select.hph_vendor_preset`** — when changed (away from
   `keep_current`), an automation auto-fills all 17 `input_text.hph_src_*`
   helpers with the entity-ID convention of the chosen vendor. Resets
   itself to `keep_current` after 2 s so re-import doesn't re-clobber.

2. **`input_select.hph_pump_model`** — drives a separate automation
   that sets `input_number.hph_model_compressor_min_hz/max_hz`,
   `_min_flow_lpm`, and `_max_supply_c` to typical values for that
   generation. Power users can override after the fact.

Adding a vendor preset: append a new option to the `input_select`,
add a `choose:` branch to `hph_vendor_preset_apply`, and create
a recipe in `docs/vendors/<name>.md`.

Adding a model: append a new option, add the threshold logic to
`hph_model_apply_thresholds`, update the description and
refrigerant template sensors. Document the model in
`docs/vendors/panasonic_heishamon.md` (or the relevant vendor file).

## Schema auto-detection

Optional components (zone 2, DHW tank, buffer tank) are detected
automatically from the source-facade availability:

```
input_text.hph_src_zone2_temp     → binary_sensor.hph_has_hk2
input_text.hph_src_dhw_temp       → binary_sensor.hph_has_dhw
input_text.hph_src_buffer_temp    → binary_sensor.hph_has_buffer
                                            ↓
                                  sensor.hph_schema_variant_detected
                                            ↓ (resolved by selector)
                                  sensor.hph_schema_variant_active
                                            ↓
                                  Schematic view (4 conditional bubble-cards)
```

The selector `input_select.hph_schema_variant` defaults to `auto`
which follows detection. To force a specific schematic (e.g. preview a
buffered install before adding sensors), set it to one of the four
explicit options. To mark a component as definitely absent, blank out
the corresponding `hph_src_*` helper.

Each schematic SVG (`schema_a2w_*.svg`) has its own conditional
bubble-card with hotspot positions calibrated to that variant's
specific layout — there is no shared coordinate system across variants.

## COP / SCOP formulas

- **Thermal power [W]**: `(supply − return) × flow_l/min × 4180 / 60`
- **Live COP**: `thermal_power / electrical_power`, **0** during defrost
  (otherwise residual circulation skews the value upward).
- **SCOP / monthly / daily**: `utility_meter` counters yield per-period
  energy totals; efficiency = `thermal_kWh[period] / electrical_kWh[period]`.
- **Tariff splits**: `utility_meter` with tariffs `heating`/`dhw`/`cooling`,
  switched by an automation that follows `sensor.hph_operating_mode`
  (which is itself derived from the configurable source-facade).

## Recorder & SQL

History flows out via three paths — **never** via direct DB queries
against the recorder backing store (the schema is private and changes
between HA versions):

- **REST `/api/history/period/<iso>?filter_entity_id=<X>`** — short-term
  state history. Used by `scripts/export_heishahub.py` and
  `scripts/analyze_heating_curve.py`. Subject to recorder retention
  (HA default 10 days; HPH recommends ≥30).
- **WebSocket `recorder/import_statistics`** — backfilling long-term
  statistics. Used by `scripts/import_csv_to_ha_stats.py`.
- **InfluxDB Flux** — multi-year analytical queries from Grafana. HA
  mirrors state via the core `influxdb:` integration; HPH never writes
  here directly.

Rules for new code that wants historical data:

1. Use REST or WebSocket, not raw SQL.
2. For windows >30 days, target InfluxDB via Flux.
3. In templates, use the `statistics` platform for rolling aggregates;
   don't walk `states.*` history.

Open questions (not yet decided):

- Should the scripts standardise on WebSocket (currently mixed: read via
  REST, write via WS)?
- Should HPH set a recorder `purge_keep_days:` recommendation in the
  installer (currently only mentioned in `docs/database.md`)?

## Coexistence with HeishaMoNR

Both systems can listen on the same MQTT broker simultaneously — only
**one** of them must write to the heat pump. If you run HeishaMoNR for
control, leave every `input_boolean.hph_ctrl_*` off (including the v0.7
extensions: `adaptive_curve`, `price_dhw`, `forecast_preheat`) and
disable the kamaradclimber `number.*`/`select.*` entities. For pure
HeatPump Hero installs no constraint applies — HPH is the writer.

## Advisor design

The advisor produces **recommendations, not commands**. Each sensor:

- `state ∈ { ok, warn, critical, info }` — machine-readable
- `attributes.message` — plain-language explanation with a concrete next step
- `attributes.metric` — the relevant measurement supporting the diagnosis

All advisor `attributes.message` text and persistent_notification body
text is English. Until v1.0 the entire repo (docs, code, dashboards,
attributes, notifications) is English-only — see [CONTRIBUTING.md](CONTRIBUTING.md).

Thresholds are **always** exposed via `input_number.hph_advisor_*`. No
hard-coded magic numbers in templates — if a value should be tunable,
expose it as a helper.

New advisor sensors follow the schema above. They may live in any
`packages/hph_*.yaml`, but **must** be added (by `unique_id`) to the
`hph_advisor_summary` aggregation in `hph_advisor.yaml`.
`tests/smoke.py:test_advisor_summary_consistency` scans all packages
and verifies every aggregated advisor is declared somewhere — it does
not verify the reverse, so an isolated advisor not listed in the
summary is silently invisible.

## Control design

Control automations (CCC, SoftStart, etc.) are **always**:

1. Off by default (`initial: false`)
2. Behind the master switch `input_boolean.hph_ctrl_master`
3. Individually toggleable via `input_boolean.hph_ctrl_<name>`
4. Tunable via `input_number.hph_ctrl_<name>_*`

Rationale: a misconfigured control automation can damage the heat pump or
hurt comfort. Activation must be deliberate.

## YAML conventions

**Automation `mode`**: `single` (default) for state-triggered reactions
that must not overlap; `queued: <N>` only for event-loggers (e.g.
`hph_diag_log_error_change` uses `queued: 5` for fault-code event
bursts); avoid `parallel` and `restart` unless you can articulate why.

**`input_text` `max:`**: defaults to `max: 255` (entity-IDs fit). For
JSON ring buffers (e.g. `hph_diag_error_history`), `max:` must
accommodate the serialized payload — current 5-event buffer at ~50
chars/event fits in 255; bumping the buffer size means bumping `max:`.

**New `packages/hph_*.yaml` files**: create when adding a new feature
axis (analysis vs. diagnostics vs. control) or a feature so distinct
it deserves opt-in/out. Otherwise extend the matching existing file.
New packages need a top-of-file comment explaining what reads them and
what writes via them, plus a one-liner in the Repository layout table.

**Hot-path templates**: For templates that depend on sensors updating
at ≥ 1 Hz (e.g. `compressor_freq`, `water_flow`), prefer
`trigger:`-based template sensors with an explicit time interval over
default state-triggered ones. State-triggered templates re-evaluate on
every dependency update — for `hph_thermal_power` (3 fast-updating
dependencies) this means hundreds of evaluations per minute.

## Template patterns

**Why YAML, not UI helpers.** HA's UI helper for "Template" creates
single-output entities without `availability:`, `unique_id`, or compound
multi-source guards — none of which HPH can drop without losing
"no `unknown` sensors". Packages stay YAML; the v0.9 Python custom
integration will replace YAML with Python entity classes, never UI helpers.

These are the idioms that put "no `unknown` sensors" into practice.
Reuse them; don't invent variants.

**Availability — single source**

```yaml
availability: >-
  {{ states('sensor.X') not in ['unknown','unavailable','none'] }}
```

**Availability — multiple sources** (all required)

```yaml
availability: >-
  {{ states('sensor.A') not in ['unknown','unavailable','none']
     and states('sensor.B') not in ['unknown','unavailable','none'] }}
```

**Default-aware numeric coercion** (always pass a default to `float`)

```jinja
{{ states('sensor.X') | float(0) }}
```

**Source-facade read** (resolves an `input_text` to the underlying entity)

```jinja
{{ states(states('input_text.hph_src_X')) | float(0) }}
```

**Source-facade availability** (input_text may be empty)

```jinja
{% set ent = states('input_text.hph_src_X') %}
{{ ent and states(ent) not in ['unknown','unavailable','none',''] }}
```

**Binary state check**

```jinja
{{ is_state('binary_sensor.X','on') }}
```

Anti-patterns to reject in review:

- `{{ states('X') | float }}` without default — silently 0 on `unknown`
  while masking the real problem
- `availability:` omitted on a sensor that depends on the source-adapter
- Hardcoded `panasonic_*` entity IDs in templates outside the three
  whitelisted files (see Naming conventions)

## Definition of Done

Before any commit:

1. `py tests/smoke.py` exits 0
2. If a new sensor was added: it has a `unique_id`, a `state_class`
   where applicable, and an `availability:` guard if it depends on the
   source-adapter
3. If a new advisor was added: it appears in `hph_advisor_summary`
4. If a new `persistent_notification` was added: it has
   `notification_id: hph_<scope>` so dismiss-on-clear works
5. If a write target on a `panasonic_*` entity was added: the package
   is in `tests/smoke.py:ALLOWED_HARDCODE`
6. If a YAML feature requiring HA > the current `hacs.json:homeassistant`
   was used: bump `hacs.json` + add a CHANGELOG note
7. `CHANGELOG.md` has an entry under the appropriate version block
8. Commit message follows `feat|fix|refactor|chore|docs(scope): summary`
   and the body explains *why* (1-3 paragraphs typical for non-trivial
   changes)

## SemVer scope (post v1.0)

- **MAJOR**: rename of any `unique_id`, removal of a helper, change of
  a CSV/export column, breaking dashboard YAML schema
- **MINOR**: new advisor / new package / new dashboard view / new
  vendor preset / model addition
- **PATCH**: threshold default change, fault-code addition, dashboard
  polish, doc fixes

User-facing dashboard strings are English-only. Advisor messages and
notification bodies are English (see Advisor design above).

Architecture/code rules: this file. Contributor process (release flow,
translation conventions, line endings, DCO): see [CONTRIBUTING.md](CONTRIBUTING.md).

## Vocabulary

- **SCOP** — Seasonal Coefficient of Performance (annual-equivalent COP)
- **COP** — Coefficient of Performance
- **DHW** — Domestic Hot Water
- **A2W** — Air-to-Water heat pump
- **LTS** — Long-Term Statistics (HA recorder feature)
- **CCC** — Compressor Cycle Control
- **JAZ** (German) — Jahresarbeitszahl, equivalent to SCOP
- **MAZ** (German) — Monatsarbeitszahl (monthly COP)
- **TAZ** (German) — Tagesarbeitszahl (daily COP)
- **WMZ** (German) — Wärmemengenzähler (heat meter)
- **HK1 / HK2** (German) — Heizkreis 1 / 2 (zone 1 / 2)
