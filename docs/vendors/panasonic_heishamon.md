# Panasonic Aquarea + Heishamon (default)

This is the **plug-and-play target** for HeishaHub — every source-helper
default points to a kamaradclimber/heishamon-homeassistant entity.

## Hardware

- Panasonic Aquarea air-to-water heat pump (any J / K / L / T-CAP series)
- Heishamon module (Egyras or IgorYbema firmware) — wired to the
  CN-CNT diagnostic port of the Aquarea
- MQTT broker (Mosquitto add-on works fine)

## HA setup

1. Install [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
   from HACS.
2. Configure it to connect to your MQTT broker with the Heishamon topic
   prefix (default: `panasonic_heat_pump`).
3. Wait until entities appear (`sensor.panasonic_heat_pump_main_*`).
4. Run the HeishaHub setup — no `heishahub_src_*` editing needed.

## Entity mapping (already the defaults)

| HeishaHub helper | Heishamon entity |
|---|---|
| `heishahub_src_inlet_temp` | `sensor.panasonic_heat_pump_main_inlet_temperature` |
| `heishahub_src_outlet_temp` | `sensor.panasonic_heat_pump_main_outlet_temperature` |
| `heishahub_src_flow_rate` | `sensor.panasonic_heat_pump_main_water_flow` |
| `heishahub_src_outdoor_temp` | `sensor.panasonic_heat_pump_main_outside_temperature` |
| `heishahub_src_compressor_freq` | `sensor.panasonic_heat_pump_main_compressor_frequency` |
| `heishahub_src_internal_power` | `sensor.panasonic_heat_pump_main_consumed_power` |
| `heishahub_src_defrost_state` | `binary_sensor.panasonic_heat_pump_main_defrost_state` |
| `heishahub_src_aux_heater_state` | `binary_sensor.panasonic_heat_pump_main_heater_state` |
| `heishahub_src_dhw_temp` | `sensor.panasonic_heat_pump_main_dhw_temperature` |
| `heishahub_src_zone1_temp` | `sensor.panasonic_heat_pump_main_z1_water_temperature` |
| `heishahub_src_zone2_temp` | `sensor.panasonic_heat_pump_main_z2_water_temperature` |

## Coexistence

If you also run [HeishaMoNR](https://github.com/edterbak/HeishaMoNR)
(Node-Red): only one system should write at a time. With HeishaMoNR
controlling, leave every `input_boolean.heishahub_ctrl_*` switch off
and disable the kamaradclimber `number.*` / `select.*` entities.
