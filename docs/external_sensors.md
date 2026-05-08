# External sensors

🌐 English (this file) · [Deutsch](de/external_sensors.md)

Heishamon publishes an **estimate** of electrical input and computes thermal
power from internal temperature sensors — both with 10–20 % tolerance. For
trustworthy SCOP / monthly figures you need a real electricity meter and
optionally a heat meter.

HeishaHub keeps both sources — internal and external — available
simultaneously and lets you switch the active one via dropdown, no YAML
editing required.

## Electricity — Shelly

### Shelly Pro 3EM (3-phase)

1. Add the Shelly to HA (Shelly integration via HACS, or MQTT).
2. Among others, you'll get
   `sensor.shellypro3em_<id>_total_active_power` (W) and
   `sensor.shellypro3em_<id>_total_energy` (kWh).
3. Open *Settings → Devices & Services → Helpers*, edit
   `heishahub_shelly_entity` and enter the **power sensor** (W), e.g.
   `sensor.shellypro3em_xxx_total_active_power`.
4. In the dashboard *Configuration → Source selection*: set
   `Electrical source` to `external_shelly`.

### Shelly 1PM / EM (single phase)

Same flow — enter the power-sensor entity-ID into
`heishahub_shelly_entity`.

## Heat meter — MQTT

Variant 1: **read out via M-Bus gateway** (e.g. Weidmann *amber*,
Lobaro *MBus2MQTT*) — example topics:

```
mbus/heatmeter1/energy_kwh   → 12345.67
mbus/heatmeter1/power_w      → 4200
mbus/heatmeter1/flow_lpm     → 12.5
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

Then enter into the helpers:
- `heishahub_wmz_entity`        → `sensor.wmz_energy`
- `heishahub_wmz_power_entity`  → `sensor.wmz_power`

Switch the source: *Configuration → Source selection* →
`Thermal source` = `external_wmz`.

Variant 2: **direct pulse counter** on a Shelly input or ESPHome.

## Source switch and history

Switching the source **preserves** all historical data — `utility_meter`
counters are not reset. From the moment of the switch onwards the energy
integrals use the new source, and SCOP / monthly figures follow.

If you switch mid-month, that month's MAZ/SCOP partial is mixed — switching
on the first of a month keeps the periods clean.

## Validation after binding

After switching to external sources:

1. *Developer Tools → States* — `sensor.heishahub_electrical_power_active`
   must read identically to your Shelly sensor (in W).
2. `sensor.heishahub_thermal_power_active` should be plausible
   (5–15 kW heating at 7 °C outdoor).
3. `sensor.heishahub_cop_live` should sit between 2.0 and 5.0.
4. After 24 h, `sensor.heishahub_cop_daily` shows a daily figure.
