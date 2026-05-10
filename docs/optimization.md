# Optimization — cycle analysis, advisor, control

## Concept

A heat pump runs most efficiently when it operates **long, even** cycles,
**rarely** kicks in and out, and gets by with a **low supply temperature**.
HeatPump Hero provides three tools to get there:

1. **Cycle analysis** — measures cycles, run times, pauses.
2. **Advisor** — interprets that data and produces plain-language hints.
3. **Control** — optional automations that port typical optimization
   strategies from HeishaMoNR (CCC, SoftStart, Solar-DHW) to the integration.

Since v0.9 all three are implemented as **Python coordinators** inside
the `hph` integration. There are no YAML packages to edit; everything
is configured via the dashboard's Optimization view or via Settings →
Devices & Services → HeatPump Hero → Configure.

## Cycle analysis

Coordinator: `custom_components/hph/coordinators/cycles.py`. Surfaced
entities:

| Entity | Meaning |
|---|---|
| `number.hph_cycles_today` | Compressor starts today (resets at 00:00) |
| `number.hph_short_cycles_today` | Of those, shorter than threshold (default 10 min) |
| `sensor.hph_short_cycle_ratio` | Share of short cycles (%) |
| `sensor.hph_cycles_per_hour` | Starts per hour (rolling) |
| `sensor.hph_avg_cycle_duration_24h` | Average runtime |
| `number.hph_cycle_last_duration_min` | Last run duration |
| `number.hph_cycle_last_pause_min` | Last pause duration |
| `number.hph_cycle_short_threshold_min` | Threshold below which a cycle counts as "short" (tunable) |

**What's "normal"?**

- Shoulder season (5–10 °C outdoor): 4–8 starts per day, 60–120 min runs
- Deep winter (< 0 °C): 1–3 starts per day, near-continuous runs
- DHW: 1–3 starts per day, 20–45 min each

More than ~12 starts per day, or a short-cycle ratio above 25 %, suggests
insufficient water volume, an over-aggressive heating curve, or hydraulic
issues.

## Advisor

Coordinator: `custom_components/hph/coordinators/advisor.py`. Each advisor
sensor exposes:

- `state ∈ { ok, warn, critical, info }`
- `attributes.message` — explanation in plain language
- `attributes.metric` — the diagnostic value

**Current rules:**

| Sensor | Checks | Suggests |
|---|---|---|
| `hph_advisor_short_cycle` | short-cycle ratio vs. threshold | heating curve, hysteresis, buffer |
| `hph_advisor_spread` | supply/return spread vs. target K | pump speed |
| `hph_advisor_defrost` | defrost while outdoor > 7 °C | inspect evaporator |
| `hph_advisor_heat_curve` | aux heater on while outdoor > -7 °C | raise heating curve at the cold end |
| `hph_advisor_dhw_runtime` | DHW run < 20 min | hysteresis / legionella program |
| `hph_advisor_heating_limit` | observed limit vs. target | raise / lower heating limit |
| `hph_advisor_pressure_trend` | 7-day pressure delta | leak / refill |
| `hph_advisor_diagnostics` | active fault / recurrence | follow fault-code message |
| `hph_advisor_analysis` | indoor-temp deviation | heating-curve correction |
| `hph_advisor_pump_curve` | 7-day spread mean / stdev | pump-speed correction |
| `hph_advisor_efficiency_drift` | year-over-year SCOP | servicing / hardware check |
| `hph_advisor_dhw_timing` | DHW fires per day | schedule consolidation |
| `hph_advisor_summary` | aggregate traffic-light | overall status |

**Tunable thresholds** in *Optimization → Advisor thresholds* (or via
`number.hph_advisor_*` entities):

- `number.hph_advisor_short_cycle_warn_pct` (default 25 %)
- `number.hph_advisor_short_cycle_crit_pct` (default 50 %)
- `number.hph_advisor_dt_target_k` (default 5 K)
- `number.hph_advisor_dhw_min_runtime_min` (default 20 min)
- `number.hph_advisor_heating_limit_target_c` (default 16 °C)

## Control — optimization strategies

Coordinator: `custom_components/hph/coordinators/control.py`. **Default:
everything off.** Two switches are needed to enable any strategy:

1. `switch.hph_ctrl_master` — global gate
2. The individual strategy switch — see below

### Compressor Cycle Control (CCC)

**Problem**: the heat pump restarts shortly after a stop → short cycles,
high wear, poor COP.

**HeatPump Hero solution**: if the previous pause was shorter than
`number.hph_ctrl_ccc_min_pause_min` (default 15 min), Quiet-Mode 3 is
engaged for 5 minutes after the restart — this caps the maximum frequency
and gives the unit a chance to modulate down rather than ramping up and
shutting off again.

**Enable**: `switch.hph_ctrl_master` on, `switch.hph_ctrl_ccc` on, adjust
pause threshold if needed.

### SoftStart

**Problem**: cold-weather start spikes draw a high current and may trip the
utility-supplier limiter.

**HeatPump Hero solution**: on compressor start, engage Quiet-Mode 2 for 10
minutes → gentle frequency ramp.

### Solar-DHW boost

**Problem**: PV surplus is exported while the heat pump heats DHW later from
the grid.

**HeatPump Hero solution**: when the surplus sensor (entity-ID in
`text.hph_ctrl_pv_surplus_entity`) stays above
`number.hph_ctrl_solar_pv_threshold_w` (default 1500 W) for 5 minutes
**and** the tank is not full, fire `force_dhw`.

**Requires**:
- a surplus sensor (own consumption − grid import, in W)
- a tank-temperature sensor

### Night Quiet-Mode

22:00–06:00 automatic Quiet-Mode 3 — quiet operation, with a comfort
penalty in deep cold. Only enable if the unit is near a bedroom and you
don't expect heat-load problems.

### Adaptive heating curve, price-driven DHW, forecast pre-heating (v0.7+)

Three additional strategies are gated behind `switch.hph_ctrl_master`:

- `switch.hph_ctrl_adaptive_curve` — self-learning weekly curve correction
- `switch.hph_ctrl_price_dhw` — DHW only when electricity is cheap
- `switch.hph_ctrl_forecast_preheat` — pre-heat before forecast cold spell

See the Optimization view's "Control extensions" section for the
per-strategy tunables.

## Workflow for clean optimization

1. **Observe** (1–2 weeks): leave the heating curve at default, advisor
   collects data.
2. **Diagnose**: read the aggregate traffic-light and individual advisor
   sensors. Read the warnings, note the metric values.
3. **One knob at a time** (e.g. lower the heating curve by 1 °C), wait
   1–2 days, observe the advisor and cycle stats.
4. **Control strategies** (CCC, SoftStart) — only after the manual
   heating-curve tuning has reached its limit.
5. **Never change everything at once** — effects become unattributable.

## Adding your own advisor rule

In v0.9 the advisor logic is Python-internal — there is no YAML extension
point. To propose a new rule, open an issue or a PR against
`custom_components/hph/coordinators/advisor.py` following the existing
patterns (`state`, `attributes.message`, `attributes.metric`) and add the
new sensor to `hph_advisor_summary` aggregation.

A user-facing extension API (drop-in advisor scripts) is planned for v1.0.

PRs with generally useful rules are welcome — see [CLAUDE.md](../CLAUDE.md)
for design principles.
