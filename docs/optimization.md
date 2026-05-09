# Optimization — cycle analysis, advisor, control

🌐 English (this file) · [Deutsch](de/optimization.md)

## Concept

A heat pump runs most efficiently when it operates **long, even** cycles,
**rarely** kicks in and out, and gets by with a **low supply temperature**.
Heat Pump Hero provides three tools to get there:

1. **Cycle analysis** — measures cycles, run times, pauses.
2. **Advisor** — interprets that data and produces plain-language hints.
3. **Control** — optional automations that port typical optimization
   strategies from HeishaMoNR (CCC, SoftStart, Solar-DHW) to HA automations.

## Cycle analysis

Sensors in `packages/hph_cycles.yaml`:

| Sensor | Meaning |
|---|---|
| `counter.hph_cycles_today` | Compressor starts today |
| `counter.hph_short_cycles_today` | Of those, shorter than threshold (default 10 min) |
| `sensor.hph_short_cycle_ratio` | Share of short cycles (%) |
| `sensor.hph_cycles_per_hour` | Starts per hour (rolling) |
| `sensor.hph_avg_cycle_duration_24h` | Average runtime |
| `input_number.hph_cycle_last_duration_min` | Last run duration |
| `input_number.hph_cycle_last_pause_min` | Last pause duration |

**What's "normal"?**

- Shoulder season (5–10 °C outdoor): 4–8 starts per day, 60–120 min runs
- Deep winter (< 0 °C): 1–3 starts per day, near-continuous runs
- DHW: 1–3 starts per day, 20–45 min each

More than ~12 starts per day, or a short-cycle ratio above 25 %, suggests
insufficient water volume, an over-aggressive heating curve, or hydraulic
issues.

## Advisor

`packages/hph_advisor.yaml`. Each advisor sensor exposes:

- `state ∈ { ok, warn, critical, info }`
- `attributes.message` — explanation in plain language
- `attributes.metric` — the diagnostic value

**Current rules (v0.1):**

| Sensor | Checks | Suggests |
|---|---|---|
| `advisor_short_cycle` | short-cycle ratio vs. threshold | heating curve, hysteresis, buffer |
| `advisor_spread` | supply/return spread vs. target K | pump speed |
| `advisor_defrost` | defrost while outdoor > 7 °C | inspect evaporator |
| `advisor_heat_curve` | aux heater on while outdoor > -7 °C | raise heating curve at the cold end |
| `advisor_dhw_runtime` | DHW run < 20 min | hysteresis / legionella program |
| `advisor_summary` | aggregate traffic-light | overall status |

**Tunable thresholds** in *Optimization → Advisor thresholds*:
- `advisor_short_cycle_warn_pct` (default 25 %)
- `advisor_short_cycle_crit_pct` (default 50 %)
- `advisor_dt_target_k` (default 5 K)
- `advisor_dhw_min_runtime_min` (default 20 min)

## Control — optimization strategies

`packages/hph_control.yaml`. **Default: everything off.** Two switches
are needed to enable any strategy:

1. `input_boolean.hph_ctrl_master` — global gate
2. The individual strategy switch — see below

### Compressor Cycle Control (CCC)

**Problem**: the heat pump restarts shortly after a stop → short cycles,
high wear, poor COP.

**Heat Pump Hero solution**: if the previous pause was shorter than
`ctrl_ccc_min_pause_min` (default 15 min), Quiet-Mode 3 is engaged for 5
minutes after the restart — this caps the maximum frequency and gives the
unit a chance to modulate down rather than ramping up and shutting off again.

**Enable**: `ctrl_master = on`, `ctrl_ccc = on`, adjust pause threshold if
needed.

### SoftStart

**Problem**: cold-weather start spikes draw a high current and may trip the
utility-supplier limiter.

**Heat Pump Hero solution**: on compressor start, engage Quiet-Mode 2 for 10
minutes → gentle frequency ramp.

### Solar-DHW boost

**Problem**: PV surplus is exported while the heat pump heats DHW later from
the grid.

**Heat Pump Hero solution**: when the surplus sensor (entity-ID in
`ctrl_pv_surplus_entity`) stays above `ctrl_solar_pv_threshold_w` (default
1500 W) for 5 minutes **and** the tank is not full, fire `force_dhw`.

**Requires**:
- a surplus sensor (own consumption − grid import, in W)
- a tank-temperature sensor

### Night Quiet-Mode

22:00–06:00 automatic Quiet-Mode 3 — quiet operation, with a comfort
penalty in deep cold. Only enable if the unit is near a bedroom and you
don't expect heat-load problems.

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

Power users: add a new `template.sensor` block to
`packages/hph_advisor.yaml` following the same schema (`state`,
`attributes.message`, `attributes.metric`). Add it to
`hph_advisor_summary` so the aggregate traffic-light considers it.

PRs with generally useful rules are welcome — see [CLAUDE.md](../CLAUDE.md)
for design principles.
