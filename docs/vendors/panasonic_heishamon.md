# Panasonic Aquarea + Heishamon (default)

This is the **plug-and-play target** for HeatPump Hero — every source-helper
default points to a kamaradclimber/heishamon-homeassistant entity.

## Supported models

HeatPump Hero recognises the model via `input_select.hph_pump_model` and
auto-sets compressor frequency, minimum flow, and supply-temperature
thresholds for each generation:

| Model | Refrigerant | Min Hz | Max Hz | Min flow | Max supply | Notes |
|---|---|---|---|---|---|---|
| **J** (Aquarea J / WH-MDC) | R410A | 22 | 90 | 11 L/min | 55 °C | Oldest inverter generation. H23-prone, more defrost cycles. |
| **K** | R410A | 18 | 90 | 11 L/min | 55 °C | Improved modulation over J. |
| **L** | R32 | 16 | 110 | 9 L/min | 55 °C | Current mainstream (2021+). |
| **T-CAP / All Season** | R32 | 16 | 140 | 9 L/min | 55 °C | Holds capacity down to −15 °C outdoor. |
| **M** (Aquarea M / R290) | **R290** | 16 | 120 | 8 L/min | **75 °C** | New flagship (2024+). R290 enables 75 °C supply without aux heater. Heishamon support is community-driven (IgorYbema fork) — not yet on heishamon.nl. |

> Compressor minimums are empirical (community-verified). Earlier
> spec-sheet estimate of 12 Hz for M-series was incorrect — M does not
> modulate below 16 Hz. Override `input_number.hph_model_compressor_min_hz`
> if your unit reports differently.

> **Hint for M-series owners:** the H23 advisor commentary and stricter
> defrost expectations only fire on J-series installs — HeatPump Hero picks
> these rules based on `input_select.hph_pump_model`. Set this
> correctly during setup or via *Configuration → Vendor & model*.

## Hardware

- Panasonic Aquarea air-to-water heat pump (any J / K / L / T-CAP / M)
- Heishamon module (Egyras or IgorYbema firmware) — wired to the
  CN-CNT diagnostic port of the Aquarea
- MQTT broker (Mosquitto add-on works fine)

## HA setup

1. Install [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
   from HACS.
2. Configure it to connect to your MQTT broker with the Heishamon topic
   prefix (default: `panasonic_heat_pump`).
3. Wait until entities appear (`sensor.panasonic_heat_pump_main_*`).
4. Run the HeatPump Hero setup — no `hph_src_*` editing needed.

## Entity mapping (already the defaults)

| HeatPump Hero helper | Heishamon entity |
|---|---|
| `hph_src_inlet_temp` | `sensor.panasonic_heat_pump_main_inlet_temperature` |
| `hph_src_outlet_temp` | `sensor.panasonic_heat_pump_main_outlet_temperature` |
| `hph_src_flow_rate` | `sensor.panasonic_heat_pump_main_water_flow` |
| `hph_src_outdoor_temp` | `sensor.panasonic_heat_pump_main_outside_temperature` |
| `hph_src_compressor_freq` | `sensor.panasonic_heat_pump_main_compressor_frequency` |
| `hph_src_internal_power` | `sensor.panasonic_heat_pump_main_consumed_power` |
| `hph_src_defrost_state` | `binary_sensor.panasonic_heat_pump_main_defrost_state` |
| `hph_src_aux_heater_state` | `binary_sensor.panasonic_heat_pump_main_heater_state` |
| `hph_src_dhw_temp` | `sensor.panasonic_heat_pump_main_dhw_temperature` |
| `hph_src_zone1_temp` | `sensor.panasonic_heat_pump_main_z1_water_temperature` |
| `hph_src_zone2_temp` | `sensor.panasonic_heat_pump_main_z2_water_temperature` |

## Coexistence

If you also run [HeishaMoNR](https://github.com/edterbak/HeishaMoNR)
(Node-Red): only one system should write at a time. With HeishaMoNR
controlling, leave every `input_boolean.hph_ctrl_*` switch off
and disable the kamaradclimber `number.*` / `select.*` entities.

## Diagnostics — Panasonic fault codes

HeatPump Hero maps the active error code from
`sensor.hph_source_error_code` to plain-language descriptions and
severity. Model-specific commentary is added for known weak spots:

- **H23** on J-series: refrigerant-cycle abnormality; check refrigerant
  charge, expansion valve, and discharge sensor *before* assuming a leak.
- **H99** on R32/R290 units (L/T-CAP/M): freeze protection — verify minimum
  flow rate (model-dependent, e.g. 8 L/min on M-series) and that no zone
  valve is fully closed during heat-up.
- **H62** on J/K-series: water-flow switch alarm — sometimes a false alarm
  during defrost; check for air pockets first.

Full code reference: see [`docs/diagnostics.md`](../diagnostics.md).
