# CLAUDE.md — HeishaHub Project Context

🌐 English (this file) · [Deutsch](CLAUDE.de.md)

This guide is for AI assistants (Claude Code) and new human contributors. It
explains the project in five minutes.

## What is HeishaHub?

HeishaHub is a **bundle** for Home Assistant that deploys a complete dashboard
and analytical layer onto a Heishamon-controlled Panasonic Aquarea heat pump
installation. It does **not** replace any integration — it **combines**
existing building blocks into something usable:

- Entities come from [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- HeishaHub provides: HA packages (template sensors, COP/SCOP calculation),
  Lovelace dashboard YAML, Bubble-Card SVG schematic, Grafana boards,
  setup blueprint.

## Design principles

1. **Universality.** Every template is `availability:`-guarded. A zone-1-only
   installation must work as well as a fully equipped one (zone 2 + DHW +
   buffer + solar + pool). No `unknown` sensors.
2. **Plug-and-play.** Standard users install via HACS plus a setup blueprint;
   no YAML editing required. Power users can still tweak everything in YAML.
3. **External sensors first-class.** Shelly metering plugs and MQTT heat
   meters are not after-thoughts; they are equal-priority sources to the
   internal Heishamon estimates, selectable via `input_select`.
4. **Long-term resilience.** Multi-year SCOP via `utility_meter` plus LTS;
   InfluxDB mirroring for Grafana multi-year comparison.
5. **Readable YAML.** No generated templates, no macro magic — a human
   reviewer must be able to follow the dashboard YAML in five minutes.

## Repository layout

| Path | Purpose |
|---|---|
| `packages/heishahub_core.yaml` | Live sensors (thermal power, mode mapping, defrost, compressor running). |
| `packages/heishahub_external.yaml` | UI helpers for external sensors (Shelly / heat meter) and active-power selector. |
| `packages/heishahub_efficiency.yaml` | Energy integrals, utility_meter, COP / daily / monthly / SCOP. |
| `packages/heishahub_cycles.yaml` | Cycle analysis: start/stop events, runtime/pause, counters, short-cycle detection. |
| `packages/heishahub_advisor.yaml` | Data-driven optimization recommendations with plain-language messages and an aggregate traffic-light. |
| `packages/heishahub_control.yaml` | Optional control automations (CCC, SoftStart, Solar-DHW, night Quiet-Mode) — master switch off by default. |
| `dashboards/heishahub.yaml` | Lovelace dashboard YAML (storage or YAML mode). |
| `dashboards/assets/*.svg` | Installation-schematic templates (Bubble-Card backgrounds). |
| `blueprints/heishahub_setup.yaml` | Script blueprint to seed helpers and verify install. |
| `scripts/install.sh` | Optional bash installer for SSH users. |
| `grafana/*.json` | Grafana dashboards (import-ready). |
| `grafana/telegraf_mqtt.conf` | Telegraf config for MQTT → InfluxDB. |
| `docs/` | Installation and tweaking documentation. |
| `tests/` | HA CI smoke tests. |
| `.github/workflows/` | YAML / JSON validation, release automation. |

## Naming conventions

- **Entities** introduced by HeishaHub: prefix `heishahub_` (e.g.
  `sensor.heishahub_scop`).
- **Source entities** (kamaradclimber): prefix `panasonic_heat_pump_` —
  never used directly in the dashboard, always wrapped via a template, so a
  topic-prefix change is a single-file edit.
- **Helpers**: all in `input_*.heishahub_*`.
- **Dashboard views**: `overview`, `schema`, `analysis`, `efficiency`,
  `optimization`, `config`.

## Heishamon topic prefix

Default is `panasonic_heat_pump`. If your firmware uses a different prefix,
change it **only** in `packages/heishahub_core.yaml` via the variable
`!secret heishahub_topic_prefix` (not in the dashboard, not scattered through
templates).

## External-sensor mechanism

`packages/heishahub_external.yaml` defines `input_text` helpers for the source
entity-IDs. Templates read indirectly:

```yaml
{{ states(states('input_text.heishahub_shelly_entity')) | float(0) }}
```

This lets the user pick their Shelly power sensor in the HA UI without
editing YAML. `input_select.heishahub_electrical_source` switches between
`heishamon_internal` and `external_shelly` — the SCOP calculation follows.

## COP / SCOP formulas

- **Thermal power [W]**: `(supply − return) × flow_l/min × 4180 / 60`
- **Live COP**: `thermal_power / electrical_power`, **0** during defrost
  (otherwise residual circulation skews the value upward).
- **SCOP / monthly / daily**: `utility_meter` counters yield per-period
  energy totals; efficiency = `thermal_kWh[period] / electrical_kWh[period]`.
- **Tariff splits**: `utility_meter` with tariffs `heating`/`dhw`/`cooling`,
  switched by a template on `select.panasonic_heat_pump_main_operating_mode`.

## Coexistence with HeishaMoNR

Both systems can listen on the same MQTT broker simultaneously — only
**one** of them must write. The recommendation in the docs is: HeishaMoNR
controls, HeishaHub reads only (kamaradclimber `number.*`/`select.*`
disabled). For pure HeishaHub setups this constraint does not apply.

## Advisor design

The advisor produces **recommendations, not commands**. Each sensor:

- `state ∈ { ok, warn, critical, info }` — machine-readable
- `attributes.message` — plain-language explanation with a concrete next step
- `attributes.metric` — the relevant measurement supporting the diagnosis

Thresholds are **always** exposed via `input_number.heishahub_advisor_*`. No
hard-coded magic numbers in templates — if a value should be tunable, expose
it as a helper.

New advisor sensors follow the same schema and are added to the
`heishahub_advisor_summary` aggregation.

## Control design

Control automations (CCC, SoftStart, etc.) are **always**:

1. Off by default (`initial: false`)
2. Behind the master switch `input_boolean.heishahub_ctrl_master`
3. Individually toggleable via `input_boolean.heishahub_ctrl_<name>`
4. Tunable via `input_number.heishahub_ctrl_<name>_*`

Rationale: a misconfigured control automation can damage the heat pump or
hurt comfort. Activation must be deliberate.

## Releasing

- SemVer; tags `v0.x.y`.
- `release.yml` builds release notes from conventional commits.
- HACS picks up every tag automatically.

## Bilingual policy

English is the primary language for all repository content (README, docs,
code comments, commit messages, issue templates). German translations live
alongside as `*.de.md` (root) or `docs/de/*.md`. User-facing dashboard
strings are currently English; a German translation layer will follow as a
theme or helper variant.

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
