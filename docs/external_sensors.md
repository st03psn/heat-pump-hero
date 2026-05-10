# External sensors and source-adapter

Heishamon publishes an **estimate** of electrical input and computes thermal
power from internal temperature sensors — both with 10–20 % tolerance. For
trustworthy SCOP / monthly figures you need a real electricity meter and
optionally a heat meter.

HeatPump Hero abstracts ALL sources behind a configurable adapter layer
(in v0.9 implemented inside the Python integration; formerly
`packages/hph_sources.yaml`). You can:

- swap individual entity-IDs (e.g. point `text.hph_src_inlet_temp` at a
  different temperature sensor) without restarting HA
- switch source modes per metric (calculated / external power /
  external energy meter)
- swap the entire heat pump (Heishamon → Vaillant Modbus → Daikin Altherma
  → …) by adjusting the `text.hph_src_*` helpers

## Source modes

Two `select` helpers control which counter feeds SCOP / utility_meter:

### `select.hph_thermal_source`

| Mode | Effect | When to use |
|---|---|---|
| `calculated` | thermal power = (T_out − T_in) × flow × cp | default — accurate enough on Heishamon |
| `external_power` | integrate a user-provided thermal-power sensor (W) → kWh | rare, mostly for legacy heat-meter outputs |
| `external_energy` | read a user-provided heat-meter (kWh `total_increasing`) **directly** — no integration | most accurate; bypasses every error in the calculation chain |

### `select.hph_electrical_source`

| Mode | Effect |
|---|---|
| `heat_pump_internal` | heat pump's own consumed-power sensor |
| `external_power` | integrate a user-provided power sensor (W) → kWh |
| `external_energy` | read a user-provided utility meter (kWh) directly |

## Electricity — Shelly examples

### Shelly Pro 3EM (3-phase)

1. Add the Shelly to HA (Shelly integration via HACS, or MQTT).
2. Among others you'll get
   `sensor.shellypro3em_<id>_total_active_power` (W) and
   `sensor.shellypro3em_<id>_total_energy` (kWh, total_increasing).
3. **Mode `external_power`** (integrate from W):
   - Open *Settings → Devices & Services → HeatPump Hero → Configure*
   - In *Source sensors*, set `text.hph_src_external_electrical_power`
     to `sensor.shellypro3em_xxx_total_active_power`
   - Dashboard → *Configuration → Source modes* → `Electrical source mode`
     = `external_power`
4. **Mode `external_energy`** (recommended — read kWh directly):
   - Set `text.hph_src_external_electrical_energy` to
     `sensor.shellypro3em_xxx_total_energy`
   - Set source mode to `external_energy`. The integrator is bypassed.

### Shelly 1PM / EM (single phase)

Same flow with the single-phase entity-IDs.

## Heat meter — MQTT example

Variant 1: **read out via M-Bus gateway** (e.g. Weidmann *amber*,
Lobaro *MBus2MQTT*) — example topics:

```
mbus/heatmeter1/energy_kwh   → 12345.67
mbus/heatmeter1/power_w      → 4200
```

Wire them into HA via `mqtt sensor`:

```yaml
mqtt:
  sensor:
    - name: WMZ Energy
      unique_id: wmz_energy_kwh
      state_topic: mbus/heatmeter1/energy_kwh
      unit_of_measurement: kWh
      device_class: energy
      state_class: total_increasing
    - name: WMZ Power
      unique_id: wmz_power_w
      state_topic: mbus/heatmeter1/power_w
      unit_of_measurement: W
      device_class: power
      state_class: measurement
```

Then in the *Configuration* dashboard view (or via *Settings → Devices &
Services → HeatPump Hero → Configure*):
- `text.hph_src_external_thermal_energy` → `sensor.wmz_energy`
- `text.hph_src_external_thermal_power`  → `sensor.wmz_power` (optional)

Set `Thermal source mode` = `external_energy` (or `external_power` if you
only have W and prefer integration).

Variant 2: **direct pulse counter** on a Shelly input or ESPHome.

## Swapping the heat pump

If you replace Heishamon with another integration (Vaillant Modbus, Daikin
Altherma, …), open *Configuration → Heat pump entities (configurable)* and
set each `text.hph_src_*` helper to the new entity-ID. Or, easier: pick
the matching vendor preset in *Settings → Devices & Services → HeatPump
Hero → Configure → Vendor preset* — it auto-fills all 17 helpers in one
click. Example for
a hypothetical Vaillant install:

| Helper | Old (Heishamon) | New (Vaillant) |
|---|---|---|
| `hph_src_inlet_temp` | `sensor.panasonic_heat_pump_main_inlet_temperature` | `sensor.vaillant_arotherm_return_temp` |
| `hph_src_outlet_temp` | `sensor.panasonic_heat_pump_main_outlet_temperature` | `sensor.vaillant_arotherm_supply_temp` |
| `hph_src_flow_rate` | `sensor.panasonic_heat_pump_main_water_flow` | `sensor.vaillant_arotherm_flow_rate` |
| ... | ... | ... |

All HeatPump Hero sensors keep working because they read from
`sensor.hph_source_*` (the resolved facade), never from the raw
heat-pump entities directly.

The control coordinators (`coordinators/control.py`) are still
heat-pump-specific (write paths). Configure write targets via
`text.hph_ctrl_write_*` helpers in *Configuration → Control write
targets*; the vendor preset auto-fills these too.

## Source switch and history

Switching the source **preserves** all historical data — `utility_meter`
counters are not reset. From the moment of the switch onwards the energy
integrals use the new source, and SCOP / monthly figures follow.

If you switch mid-month, that month's MAZ/SCOP partial is mixed — switching
on the first of a month keeps the periods clean.

## Validation after binding

After switching to external sources:

1. *Developer Tools → States* — `sensor.hph_electrical_power_active`
   should read identically to your Shelly sensor (in W) when in
   `external_power` mode.
2. `sensor.hph_thermal_energy_active` should advance at the same
   rate as your heat meter when in `external_energy` mode.
3. `sensor.hph_cop_live` should sit between 2.0 and 5.0.
4. After 24 h, `sensor.hph_cop_daily` shows a daily figure.
