# Submitting your heat pump to heatpumpmonitor.org

[heatpumpmonitor.org](https://heatpumpmonitor.org) is the OpenEnergyMonitor
community heat-pump benchmark. Over 1000 real-world installations publish
their efficiency data so you can compare your SCOP against similar systems
under similar climate conditions.

This guide shows how to feed HeatPump Hero data into the public benchmark.

## How the data flows

```
HeatPump Hero in HA  →  emoncms.org account  →  heatpumpmonitor.org listing
```

heatpumpmonitor.org does **not** offer a direct upload API. Submissions are
pulled from your [emoncms.org](https://emoncms.org) account, where your
data must live under a set of well-known feed names. The site reviews
applications before listing, then polls your feeds automatically.

Prerequisites:

1. A free emoncms.org account.
2. Home Assistant's core `emoncms` integration configured to push to
   emoncms.org (Settings → Devices & Services → Add integration).
3. The HPH sensors below mapped to emoncms feeds using the **required
   names** below.

## Required emoncms feed names

heatpumpmonitor.org reads only feeds with these exact names. Configure the
HA `emoncms` integration to push your HPH sensors and rename them on the
emoncms side to match.

| HeatPump Hero entity                     | emoncms feed name     | Unit  |
| ---------------------------------------- | --------------------- | ----- |
| `sensor.hph_electrical_power_active`     | `heatpump_elec`       | W     |
| `sensor.hph_electrical_energy_active`    | `heatpump_elec_kwh`   | kWh   |
| `sensor.hph_thermal_power_active`        | `heatpump_heat`       | W     |
| `sensor.hph_thermal_energy_active`       | `heatpump_heat_kwh`   | kWh   |
| `sensor.hph_source_outlet_temp`          | `heatpump_flowT`      | °C    |
| `sensor.hph_source_inlet_temp`           | `heatpump_returnT`    | °C    |
| `sensor.hph_source_outdoor_temp`         | `heatpump_outsideT`   | °C    |
| `sensor.hph_source_room_temp` (optional) | `heatpump_roomT`      | °C    |
| `sensor.hph_source_flow_rate`            | `heatpump_flowrate`   | l/min |

If you use the `external_energy` source mode (real heat meter), the
`*_energy_active` sensors transparently read from your meter — submission
works identically.

## Honest SCOP: what is in your electrical measurement?

The biggest source of confusion when comparing heat pumps is **what counts
as the "electrical input"**. A heat pump's bare contactor draws differently
than the same system measured at the consumer unit, where it also includes
circulation pumps, immersion heaters, and controls.

heatpumpmonitor.org asks you to declare what your measurement includes.
HeatPump Hero exposes the same flags in Configuration → *Electrical metering
— what is included?*:

| HPH switch                            | Include if …                                                                    |
| ------------------------------------- | ------------------------------------------------------------------------------- |
| `switch.hph_metering_includes_immersion`   | Your electricity meter sees the backup/immersion heater.                  |
| `switch.hph_metering_includes_circulation` | Your meter sees the heating-circuit circulation pump.                     |
| `switch.hph_metering_includes_controls`    | Your meter sees the controller / standby load (~5–30 W).                  |
| `switch.hph_metering_includes_brine`       | (Ground-source only) Your meter sees the brine pump.                      |

Mirror the same answers on your heatpumpmonitor.org system page. Different
answers → different SCOP — but comparable across users who answered
honestly.

## Installation context

heatpumpmonitor.org also asks about the system itself (heat loss, emitter
type, design temperatures, refrigerant). HeatPump Hero now stores these in
Configuration → *Installation context*. They do not change HPH behaviour
internally, but they give you a single place to look up the values when
filling in the application form.

| HPH entity                              | heatpumpmonitor.org field             |
| --------------------------------------- | ------------------------------------- |
| `text.hph_install_heat_loss_kw`         | Design heat loss                      |
| `select.hph_install_emitter_type`       | Emitters                              |
| `text.hph_install_design_flow_temp_c`   | Design flow temperature               |
| `select.hph_install_refrigerant`        | Refrigerant                           |
| `text.hph_install_year`                 | Commissioning year                    |

## Further reading

- [heatpumpmonitor.org documentation](https://docs.openenergymonitor.org/heatpumpmonitor/)
- [emoncms.org → MyHeatpump app](https://emoncms.org)
- [OpenEnergyMonitor community forum](https://community.openenergymonitor.org)

## What HeatPump Hero does *not* do

- No direct API submission to heatpumpmonitor.org — the workflow is
  intentionally via emoncms.org with a review step. HPH provides the
  correctly-named sources; you bring the emoncms relay and the listing.
- No auto-detection of "what's in your meter" — only you know how your
  electrical wiring is fed and which contactor is upstream of the meter.
