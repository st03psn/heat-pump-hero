# Tweaking — power-user customizations

> v0.9 changed the customization story significantly. The integration
> ships virtually all logic as Python code, and the only YAML it deploys
> (`<config>/packages/hph_efficiency.yaml`) is regenerated on every
> startup. Editing that file is therefore not a stable customization
> path. Use the entry points below instead.

## 1. Change the source-entity mapping

If your Heishamon uses a non-default MQTT topic prefix, or you want to
swap to a different temperature / flow / pressure sensor:

`Settings → Devices & Services → HeatPump Hero → Configure`

Change the entity-IDs in the *Source sensors* step. The integration
re-resolves all `sensor.hph_source_*` facades on save — no restart
needed.

For external power / heat meters, see
[external_sensors.md](external_sensors.md).

## 2. Tune advisor thresholds

Every advisor has a `number.hph_advisor_*` companion that exposes its
threshold. Examples:

- `number.hph_advisor_short_cycle_warn_pct` — short-cycle ratio that
  triggers a yellow advisor
- `number.hph_advisor_short_cycle_crit_pct` — red threshold
- `number.hph_advisor_dt_target_k` — supply/return spread target
- `number.hph_advisor_dhw_min_runtime_min` — minimum acceptable DHW run
- `number.hph_advisor_heating_limit_target_c` — outdoor temp at which
  heating should stop

Adjust them via the **Optimization → Advisor thresholds** card on the
dashboard or by setting the `number.*` entity directly.

## 3. Tune control strategies

Each strategy has its own `number.hph_ctrl_*` parameters. See the
**Optimization → Control strategies** card. Common ones:

- `number.hph_ctrl_ccc_min_pause_min` — pause threshold below which CCC
  engages (default 15 min)
- `number.hph_ctrl_solar_pv_threshold_w` — surplus required to fire
  Solar-DHW (default 1500 W)

Both the global `switch.hph_ctrl_master` and the per-strategy switch
must be on for any control logic to run.

## 4. Custom dashboard layout

The integration deploys the dashboard at `<config>/hph/dashboard.yaml`
and registers it at `/hph`. **This file is overwritten on every
HA restart** — do not edit it directly for permanent changes.

Two stable customization paths:

1. **Duplicate the dashboard in the UI**: open `/hph` → ⋮ → *Take
   control* → *Duplicate*. The duplicate is yours; HPH updates only
   refresh the original auto-deployed copy.
2. **Per-card overrides via the UI**: card-mod styles or local card
   reorderings persist if you've taken control via option 1.

## 5. Custom advisor rules

In v0.9 advisor logic lives in `coordinators/advisor.py` (Python).
Adding a new rule means a code change. Two options:

- **PR**: open an issue or PR; useful rules ship in the next release.
- **Wait for v1.0**: a drop-in advisor extension API is on the roadmap
  (a Python file in `<config>/hph/advisors/` that the integration
  picks up).

Until then, you can also keep a parallel YAML package with your own
`template.sensor` rules and aggregate them into your own summary
sensor — just don't expect them to participate in
`sensor.hph_advisor_summary`.

## 6. Custom utility_meter periods

The deployed `hph_efficiency.yaml` includes daily, monthly, and
yearly (heating-season Jul 1 – Jun 30) meters. To add a custom period,
e.g. an October–April heating season:

1. Add a `template.sensor` package in your own `<config>/packages/`
   directory referencing `sensor.hph_thermal_energy_active` /
   `sensor.hph_electrical_energy_active` (the active-source dispatchers).
2. Don't edit `hph_efficiency.yaml` — it's overwritten.

Example custom package (your own file, not HPH-managed):

```yaml
# <config>/packages/my_hph_extras.yaml
utility_meter:
  hph_thermal_oct_apr:
    source: sensor.hph_thermal_energy_active
    cron: "0 0 1 10 *"   # reset Oct 1 at midnight
  hph_electrical_oct_apr:
    source: sensor.hph_electrical_energy_active
    cron: "0 0 1 10 *"
```

Don't forget to enable `homeassistant: packages: !include_dir_named
packages` in your `configuration.yaml` if you haven't already.

## 7. Localize / customize advisor messages

Advisor messages are emitted from `coordinators/advisor.py`. Translation
support arrives in v1.0 via a translation map keyed off the existing
strings.json. Until then, fork the integration if you need a different
language for the advisor body text — the dashboard surface (card titles,
KPI labels) is already user-facing English.
