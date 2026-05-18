"""HeatPump Hero — domain constants and helper-entity definitions.

The integration is data-driven: every Python platform reads its entity
list from one of the dicts below. Each dict mirrors the original
`input_*` / `counter` definitions in `packages/hph_*.yaml` so the
existing `unique_id`s are preserved (entity-registry continuity).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

DOMAIN: Final = "hph"
INTEGRATION_NAME: Final = "HeatPump Hero"
DEFAULT_NAME: Final = INTEGRATION_NAME

# Stored under hass.data[DOMAIN][entry.entry_id]
DATA_HASS_CONFIG: Final = "ha_config_path"
DATA_BOOTSTRAP_DONE: Final = "bootstrap_done"

# Service names
SERVICE_EXPORT_NOW: Final = "export_now"
SERVICE_RUN_LEGIONELLA: Final = "run_legionella_now"

# Dashboard
DASHBOARD_URL_PATH: Final = "hph"
DASHBOARD_TITLE: Final = INTEGRATION_NAME
DASHBOARD_ICON: Final = "mdi:heat-pump"
DASHBOARD_FILE_REL: Final = "hph/dashboard.yaml"  # legacy relative path (kept for compat)
# Absolute paths — integration serves these directly (no copy to <config>/).
DASHBOARD_FILE_ABS: Final = str(
    Path(__file__).parent / "data" / "dashboards" / "hph.yaml"
)
ASSETS_DIR_ABS: Final = str(
    Path(__file__).parent / "data" / "dashboards" / "assets"
)
ASSETS_URL_PATH: Final = "/hph_assets"

# ───────────────────────────────────────────────────────────────────────────
# Vendor presets — drives the config flow vendor dropdown and the
# auto-fill payload for source helpers. Mirrors hph_vendor_preset_apply
# in packages/hph_models.yaml.
# ───────────────────────────────────────────────────────────────────────────
VENDOR_PRESETS: Final[dict[str, dict[str, str]]] = {
    "panasonic_heishamon": {
        # kamaradclimber/heishamon-homeassistant — current abbreviated naming
        # (verified against live heishamon integration 2026-05)
        "hph_src_inlet_temp": "sensor.panasonic_heat_pump_main_main_inlet_temp",
        "hph_src_outlet_temp": "sensor.panasonic_heat_pump_main_main_outlet_temp",
        "hph_src_flow_rate": "sensor.panasonic_heat_pump_main_pump_flow",
        "hph_src_outdoor_temp": "sensor.panasonic_heat_pump_main_outside_temp",
        "hph_src_compressor_freq": "sensor.panasonic_heat_pump_main_compressor_freq",
        "hph_src_compressor_hours": "sensor.panasonic_heat_pump_main_operations_hours",
        "hph_src_compressor_starts": "sensor.panasonic_heat_pump_main_operations_counter",
        "hph_src_discharge_temp": "sensor.panasonic_heat_pump_main_discharge_temp",
        "hph_src_pump_pressure": "sensor.panasonic_heat_pump_main_water_pressure",
        "hph_src_internal_power": "sensor.panasonic_heat_pump_main_heat_power_consumption",
        "hph_src_internal_thermal_power": "sensor.panasonic_heat_pump_main_heat_power_production",
        "hph_src_defrost_state": "binary_sensor.panasonic_heat_pump_main_defrosting_state",
        "hph_src_aux_heater_state": "binary_sensor.panasonic_heat_pump_main_room_heater_state",
        "hph_src_operating_mode": "select.panasonic_heat_pump_main_operating_mode_state",
        "hph_src_zone1_temp": "sensor.panasonic_heat_pump_main_z1_temp",
        "hph_src_zone2_temp": "sensor.panasonic_heat_pump_main_z2_temp",
        "hph_src_dhw_temp": "sensor.panasonic_heat_pump_main_dhw_temp",
        "hph_src_buffer_temp": "sensor.panasonic_heat_pump_main_buffer_temp",
        "hph_src_dhw_target_temp": "sensor.panasonic_heat_pump_main_dhw_target_temp",
        "hph_src_target_supply_temp": "sensor.panasonic_heat_pump_main_main_target_temp",
        "hph_src_zone1_setpoint": "sensor.panasonic_heat_pump_main_z1_water_target_temp",
        "hph_src_room_temp": "sensor.panasonic_heat_pump_main_room_thermostat_temp",
        "hph_src_pump_speed": "sensor.panasonic_heat_pump_main_pump_speed",
        "hph_src_valve_state": "sensor.panasonic_heat_pump_main_twoway_valve_state",
        "hph_src_heater_state": "binary_sensor.panasonic_heat_pump_main_external_heater_state",
        "hph_src_heater_hours": "sensor.panasonic_heat_pump_main_room_heater_operations_hours",
        "hph_src_error_code": "sensor.panasonic_heat_pump_main_error",
        "hph_ctrl_write_quiet_mode": "select.panasonic_heat_pump_main_quiet_mode_level",
        "hph_ctrl_write_force_dhw": "button.panasonic_heat_pump_main_force_dhw",
        "hph_ctrl_write_z1_curve_high": "number.panasonic_heat_pump_main_z1_heat_curve_target_high_temp",
        "hph_ctrl_write_z1_curve_low": "number.panasonic_heat_pump_main_z1_heat_curve_target_low_temp",
        "hph_ctrl_write_dhw_target": "number.panasonic_heat_pump_main_dhw_target_temp",
        # Extended control write-path helpers (v0.9)
        "hph_ctrl_write_operating_mode": "select.panasonic_heat_pump_main_operating_mode_state",
        "hph_ctrl_write_power": "switch.panasonic_heat_pump_main_heatpump_state",
        "hph_ctrl_write_holiday": "switch.panasonic_heat_pump_main_holiday_mode",
        "hph_ctrl_write_force_defrost": "switch.panasonic_heat_pump_main_force_defrost",
        "hph_ctrl_write_powerful_mode": "select.panasonic_heat_pump_main_powerful_mode",
        "hph_ctrl_write_active_zones": "select.panasonic_heat_pump_main_zones_state",
        "hph_ctrl_write_bivalent_mode": "",
        "hph_ctrl_write_z1_heat_shift": "number.panasonic_heat_pump_main_z1_heat_request_temperature",
        "hph_ctrl_write_z2_heat_shift": "number.panasonic_heat_pump_main_z2_heat_request_temperature",
        "hph_ctrl_write_heating_cutoff": "number.panasonic_heat_pump_main_heating_off_outdoor_temperature",
        "hph_ctrl_write_max_pump_duty": "number.panasonic_heat_pump_main_max_pump_duty",
        "hph_ctrl_write_room_heat_delta": "number.panasonic_heat_pump_main_floor_heating_delta",
        "hph_ctrl_write_z1_climate": "climate.panasonic_heat_pump_main_z1_temp",
        "hph_ctrl_write_z2_climate": "climate.panasonic_heat_pump_main_z2_temp",
        # Monitoring sensors (v0.9)
        "hph_src_fan1_speed": "sensor.panasonic_heat_pump_main_fan1_motor_speed",
        "hph_src_fan2_speed": "sensor.panasonic_heat_pump_main_fan2_motor_speed",
        "hph_src_inverter_temp": "sensor.panasonic_heat_pump_main_ipm_temp",
        "hph_src_high_pressure": "sensor.panasonic_heat_pump_main_high_pressure",
        "hph_src_low_pressure": "sensor.panasonic_heat_pump_main_low_pressure",
        "hph_src_compressor_current": "sensor.panasonic_heat_pump_main_compressor_current",
        "hph_src_outdoor_pipe_temp": "sensor.panasonic_heat_pump_main_outside_pipe_temp",
        "hph_src_3way_valve": "sensor.panasonic_heat_pump_main_threeway_valve_state",
        "hph_src_zone1_target_temp": "sensor.panasonic_heat_pump_main_z1_water_target_temp",
        "hph_src_hex_outlet_temp": "sensor.panasonic_heat_pump_main_main_hex_outlet_temp",
        "hph_src_pump_duty": "sensor.panasonic_heat_pump_main_pump_duty",
        # Heating curve reference points
        "hph_ctrl_write_z1_outside_low": "number.panasonic_heat_pump_main_z1_heat_curve_outside_low_temp",
        "hph_ctrl_write_z1_outside_high": "number.panasonic_heat_pump_main_z1_heat_curve_outside_high_temp",
        "hph_ctrl_write_z2_outside_low": "number.panasonic_heat_pump_main_z2_heat_curve_outside_low_temp",
        "hph_ctrl_write_z2_outside_high": "number.panasonic_heat_pump_main_z2_heat_curve_outside_high_temp",
        "hph_ctrl_write_z2_curve_high": "number.panasonic_heat_pump_main_z2_heat_curve_target_high_temp",
        "hph_ctrl_write_z2_curve_low": "number.panasonic_heat_pump_main_z2_heat_curve_target_low_temp",
        # DHW additional
        "hph_ctrl_write_dhw_heat_delta": "number.panasonic_heat_pump_main_dhw_heat_delta",
        "hph_ctrl_write_smart_dhw": "select.panasonic_heat_pump_main_smart_dhw",
        # Advanced settings
        "hph_ctrl_write_heating_control": "select.panasonic_heat_pump_main_heating_control",
        "hph_ctrl_write_cool_delta": "number.panasonic_heat_pump_main_cool_delta",
        "hph_ctrl_write_dhw_sensor_selection": "select.panasonic_heat_pump_main_dhw_sensor_selection",
        "hph_ctrl_write_bivalent_start_temp": "number.panasonic_heat_pump_main_bivalent_start_temp",
        "hph_ctrl_write_heater_delay_time": "number.panasonic_heat_pump_main_heater_delay_time",
        "hph_ctrl_write_heater_start_delta": "number.panasonic_heat_pump_main_heater_start_delta",
        "hph_ctrl_write_heater_stop_delta": "number.panasonic_heat_pump_main_heater_stop_delta",
        # Status binary sensors
        "hph_src_force_heater": "binary_sensor.panasonic_heat_pump_main_force_heater_state",
        "hph_src_sterilization": "binary_sensor.panasonic_heat_pump_main_sterilization_state",
        "hph_src_quiet_schedule": "binary_sensor.panasonic_heat_pump_main_quiet_mode_schedule",
    },
    "panasonic_heishamon_aquarea": {
        # Bundled HeishaMon MQTT YAML naming (aquarea_*)
        "hph_src_inlet_temp": "sensor.aquarea_main_inlet_temp",
        "hph_src_outlet_temp": "sensor.aquarea_main_outlet_temp",
        "hph_src_flow_rate": "sensor.aquarea_main_water_flow",
        "hph_src_outdoor_temp": "sensor.aquarea_main_outdoor_temp",
        "hph_src_compressor_freq": "sensor.aquarea_main_compressor_freq",
        "hph_src_compressor_hours": "sensor.aquarea_main_operations_hours",
        "hph_src_compressor_starts": "sensor.aquarea_main_operations_counter",
        "hph_src_discharge_temp": "sensor.aquarea_main_discharge_temp",
        "hph_src_pump_pressure": "sensor.aquarea_main_pump_pressure",
        "hph_src_internal_power": "sensor.aquarea_main_consumed_power",
        "hph_src_defrost_state": "binary_sensor.aquarea_main_defrost_state",
        "hph_src_aux_heater_state": "binary_sensor.aquarea_main_heater_state",
        "hph_src_operating_mode": "select.aquarea_main_operating_mode",
        "hph_src_zone1_temp": "sensor.aquarea_main_z1_water_temp",
        "hph_src_zone2_temp": "sensor.aquarea_main_z2_water_temp",
        "hph_src_dhw_temp": "sensor.aquarea_main_dhw_temp",
        "hph_src_buffer_temp": "sensor.aquarea_main_buffer_temp",
        "hph_src_error_code": "sensor.aquarea_main_error",
        "hph_ctrl_write_quiet_mode": "select.aquarea_main_quiet_mode",
        "hph_ctrl_write_force_dhw": "button.aquarea_main_force_dhw",
        "hph_ctrl_write_z1_curve_high": "number.aquarea_main_z1_heat_curve_target_high_temp",
        "hph_ctrl_write_z1_curve_low": "number.aquarea_main_z1_heat_curve_target_low_temp",
        "hph_ctrl_write_dhw_target": "number.aquarea_main_dhw_target_temp",
        # Extended control write-path helpers (v0.9)
        "hph_ctrl_write_operating_mode": "select.aquarea_main_operating_mode_state",
        "hph_ctrl_write_power": "switch.aquarea_main_heatpump_state",
        "hph_ctrl_write_holiday": "switch.aquarea_main_holiday_mode",
        "hph_ctrl_write_force_defrost": "switch.aquarea_main_force_defrost",
        "hph_ctrl_write_powerful_mode": "select.aquarea_main_powerful_mode",
        "hph_ctrl_write_active_zones": "select.aquarea_main_zones_state",
        "hph_ctrl_write_bivalent_mode": "",
        "hph_ctrl_write_z1_heat_shift": "number.aquarea_main_z1_heat_request_temperature",
        "hph_ctrl_write_z2_heat_shift": "number.aquarea_main_z2_heat_request_temperature",
        "hph_ctrl_write_heating_cutoff": "number.aquarea_main_heating_off_outdoor_temperature",
        "hph_ctrl_write_max_pump_duty": "number.aquarea_main_max_pump_duty",
        "hph_ctrl_write_room_heat_delta": "number.aquarea_main_floor_heating_delta",
        "hph_ctrl_write_z1_climate": "climate.aquarea_main_z1_temp",
        "hph_ctrl_write_z2_climate": "climate.aquarea_main_z2_temp",
        # Monitoring sensors (v0.9)
        "hph_src_fan1_speed": "sensor.aquarea_main_fan1_motor_speed",
        "hph_src_fan2_speed": "sensor.aquarea_main_fan2_motor_speed",
        "hph_src_inverter_temp": "sensor.aquarea_main_ipm_temp",
        "hph_src_high_pressure": "sensor.aquarea_main_high_pressure",
        "hph_src_low_pressure": "sensor.aquarea_main_low_pressure",
        "hph_src_compressor_current": "sensor.aquarea_main_compressor_current",
        "hph_src_outdoor_pipe_temp": "sensor.aquarea_main_outside_pipe_temp",
        "hph_src_3way_valve": "sensor.aquarea_main_threeway_valve_state",
        "hph_src_zone1_target_temp": "sensor.aquarea_main_z1_water_target_temp",
        "hph_src_hex_outlet_temp": "sensor.aquarea_main_main_hex_outlet_temp",
        "hph_src_pump_duty": "sensor.aquarea_main_pump_duty",
        # Heating curve reference points
        "hph_ctrl_write_z1_outside_low": "number.aquarea_main_z1_heat_curve_outside_low_temp",
        "hph_ctrl_write_z1_outside_high": "number.aquarea_main_z1_heat_curve_outside_high_temp",
        "hph_ctrl_write_z2_outside_low": "number.aquarea_main_z2_heat_curve_outside_low_temp",
        "hph_ctrl_write_z2_outside_high": "number.aquarea_main_z2_heat_curve_outside_high_temp",
        "hph_ctrl_write_z2_curve_high": "number.aquarea_main_z2_heat_curve_target_high_temp",
        "hph_ctrl_write_z2_curve_low": "number.aquarea_main_z2_heat_curve_target_low_temp",
        # DHW additional
        "hph_ctrl_write_dhw_heat_delta": "number.aquarea_main_dhw_heat_delta",
        "hph_ctrl_write_smart_dhw": "select.aquarea_main_smart_dhw",
        # Advanced settings
        "hph_ctrl_write_heating_control": "select.aquarea_main_heating_control",
        "hph_ctrl_write_cool_delta": "number.aquarea_main_cool_delta",
        "hph_ctrl_write_dhw_sensor_selection": "select.aquarea_main_dhw_sensor_selection",
        "hph_ctrl_write_bivalent_start_temp": "number.aquarea_main_bivalent_start_temp",
        "hph_ctrl_write_heater_delay_time": "number.aquarea_main_heater_delay_time",
        "hph_ctrl_write_heater_start_delta": "number.aquarea_main_heater_start_delta",
        "hph_ctrl_write_heater_stop_delta": "number.aquarea_main_heater_stop_delta",
        # Status binary sensors
        "hph_src_force_heater": "binary_sensor.aquarea_main_force_heater_state",
        "hph_src_sterilization": "binary_sensor.aquarea_main_sterilization_state",
        "hph_src_quiet_schedule": "binary_sensor.aquarea_main_quiet_mode_schedule",
    },
    "daikin_altherma_core": {
        "hph_src_inlet_temp": "sensor.altherma_leaving_water_temperature",
        "hph_src_outlet_temp": "sensor.altherma_outdoor_temperature_returning_water",
        "hph_src_outdoor_temp": "sensor.altherma_outdoor_temperature",
        "hph_src_dhw_temp": "sensor.altherma_tank_temperature",
        "hph_src_internal_power": "sensor.altherma_power_consumption",
    },
    "mitsubishi_melcloud_core": {
        "hph_src_inlet_temp": "sensor.melcloud_flow_temperature_zone_1",
        "hph_src_outdoor_temp": "sensor.melcloud_outdoor_temperature",
        "hph_src_dhw_temp": "sensor.melcloud_tank_water_temperature",
    },
    "vaillant_arotherm_mypyllant": {
        "hph_src_outlet_temp": "sensor.arotherm_flow_temperature",
        "hph_src_inlet_temp": "sensor.arotherm_return_temperature",
        "hph_src_outdoor_temp": "sensor.arotherm_outdoor_temperature",
    },
    "stiebel_eltron_isg": {
        "hph_src_outlet_temp": "sensor.isg_flow_temperature_hc1",
        "hph_src_inlet_temp": "sensor.isg_return_temperature",
        "hph_src_outdoor_temp": "sensor.isg_outdoor_temperature",
    },
    "generic_modbus": {},
    "generic_mqtt": {},
}

# Pump-model thresholds — mirrors hph_model_apply_thresholds.
PUMP_MODELS: Final[dict[str, dict[str, Any]]] = {
    "panasonic_j_aqj": {"min_hz": 22, "max_hz": 90, "min_flow": 11, "max_supply": 55,
                        "refrigerant": "R410A",
                        "description": "Panasonic J-series (Aquarea J / WH-MDC, R410A, oldest inverter generation)"},
    "panasonic_k_aqk": {"min_hz": 18, "max_hz": 90, "min_flow": 11, "max_supply": 55,
                        "refrigerant": "R410A",
                        "description": "Panasonic K-series (R410A, improved modulation)"},
    "panasonic_l_aql": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 55,
                        "refrigerant": "R32",
                        "description": "Panasonic L-series (R32, current mainstream)"},
    "panasonic_tcap": {"min_hz": 16, "max_hz": 140, "min_flow": 9, "max_supply": 55,
                       "refrigerant": "R32",
                       "description": "Panasonic T-CAP / All-Season (full capacity at low outdoor T°)"},
    "panasonic_m_aqm": {"min_hz": 16, "max_hz": 120, "min_flow": 8, "max_supply": 75,
                        "refrigerant": "R290",
                        "description": "Panasonic M-series (R290 propane, new flagship, Heishamon community-supported since 2024)"},
    "daikin_altherma3": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 55,
                         "refrigerant": "R32",
                         "description": "Daikin Altherma 3 (R32)"},
    "mitsubishi_ecodan": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 55,
                          "refrigerant": "R32 / R454C",
                          "description": "Mitsubishi Ecodan / Zubadan"},
    "vaillant_arotherm": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 75,
                          "refrigerant": "R290",
                          "description": "Vaillant aroTHERM Plus (R290)"},
    "stiebel_wpl": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 55,
                    "refrigerant": "R454C",
                    "description": "Stiebel Eltron WPL series"},
    "generic": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 55,
                "refrigerant": "unknown",
                "description": "generic / unknown"},
}

# ───────────────────────────────────────────────────────────────────────────
# Model capability map — which hph_src_* sensors physically exist per model.
#
# Key   = PUMP_MODELS key.
# Value = frozenset of helper *suffixes* (strip the "hph_src_" prefix).
#
# Rules:
#   • Only hph_src_* helpers are capability-gated; hph_ctrl_write_* fill
#     unconditionally (control surfaces are vendor-gated, not model-gated).
#   • A model NOT present in this dict is treated as "all sensors available"
#     (non-Panasonic vendors fill manually via Config tab).
#   • When uncertain, omit the sensor rather than guessing — users can fill
#     the helper manually in Settings → Devices → HeatPump Hero → Configure.
#
# Confirmed sources:
#   • Fan1 / Fan2: HeishaMon HeishaMon hardware docs + user report (2026-05).
#     J/K/L-series = WH-MDC*/WH-SDC* = SINGLE outdoor fan → fan2_speed absent.
#     T-CAP / M-series = WH-MXC* = DUAL outdoor fans → fan2_speed present.
#   • pump_pressure (TOP115): K/L All-In-One only (noted in const.py comment
#     predating this map). J-series and split-unit T-CAP/M lack this sensor.
# ───────────────────────────────────────────────────────────────────────────
# Capability gating in vendor_apply works by EXCLUSION: a hph_src_* helper is
# emptied iff its suffix is *absent* from the per-model capability set. So caps
# must enumerate every suffix the model exposes — not just the optional ones.
# We derive the universal base from the Panasonic preset itself so the set
# stays in sync when sensors are added/renamed, and then express per-model
# variants as additions of model-conditional suffixes.
_MODEL_CONDITIONAL: Final = frozenset({"fan2_speed"})
_PANASONIC_BASE_SENSORS: Final = frozenset(
    k.removeprefix("hph_src_")
    for k in VENDOR_PRESETS["panasonic_heishamon"]
    if k.startswith("hph_src_")
) - _MODEL_CONDITIONAL

MODEL_CAPABILITIES: Final[dict[str, frozenset[str]]] = {
    # J-series (WH-MDC*, R410A, oldest): single fan
    "panasonic_j_aqj": _PANASONIC_BASE_SENSORS,
    # K-series (R410A improved): single fan
    "panasonic_k_aqk": _PANASONIC_BASE_SENSORS,
    # L-series (R32, current mainstream): single fan, confirmed by user
    "panasonic_l_aql": _PANASONIC_BASE_SENSORS,
    # T-CAP / All-Season (R32): DUAL outdoor fan
    "panasonic_tcap":  _PANASONIC_BASE_SENSORS | {"fan2_speed"},
    # M-series (R290): DUAL outdoor fan
    "panasonic_m_aqm": _PANASONIC_BASE_SENSORS | {"fan2_speed"},
}

# ───────────────────────────────────────────────────────────────────────────
# Vendor → model list: restricts the model dropdown in the config flow to
# only the models relevant for the chosen vendor.
# A vendor NOT present here falls back to the full PUMP_MODELS list.
# ───────────────────────────────────────────────────────────────────────────
VENDOR_MODELS: Final[dict[str, list[str]]] = {
    "panasonic_heishamon": [
        "panasonic_j_aqj", "panasonic_k_aqk", "panasonic_l_aql",
        "panasonic_tcap", "panasonic_m_aqm",
    ],
    "panasonic_heishamon_aquarea": [
        "panasonic_j_aqj", "panasonic_k_aqk", "panasonic_l_aql",
        "panasonic_tcap", "panasonic_m_aqm",
    ],
    "daikin_altherma_core":        ["daikin_altherma3"],
    "mitsubishi_melcloud_core":    ["mitsubishi_ecodan"],
    "vaillant_arotherm_mypyllant": ["vaillant_arotherm"],
    "stiebel_eltron_isg":          ["stiebel_wpl"],
    "generic_modbus":              ["generic"],
    "generic_mqtt":                ["generic"],
    "keep_current":                list(PUMP_MODELS.keys()),
}

# ───────────────────────────────────────────────────────────────────────────
# Helper definitions — one dict per HA platform.
#
# Each entry: unique_id -> (kind-specific config). The platform module reads
# its dict and instantiates one entity per row. unique_id matches the
# original YAML so entity registry preserves entity_id and recorder
# history connects across the v0.8 → v0.9 migration.
# ───────────────────────────────────────────────────────────────────────────

# ─── Text helpers ────────────────────────────────────────────────────────
# Format: unique_id -> {"name", "icon", "initial", "max"}
TEXT_HELPERS: Final[dict[str, dict[str, Any]]] = {
    # Source adapter (hph_sources.yaml)
    "hph_src_inlet_temp": {"name": "HeatPump Hero source — inlet (return) temperature", "icon": "mdi:thermometer-low",
                            "initial": "sensor.panasonic_heat_pump_main_inlet_temperature"},
    "hph_src_outlet_temp": {"name": "HeatPump Hero source — outlet (supply) temperature", "icon": "mdi:thermometer-high",
                             "initial": "sensor.panasonic_heat_pump_main_outlet_temperature"},
    "hph_src_flow_rate": {"name": "HeatPump Hero source — water flow rate", "icon": "mdi:water-pump",
                           "initial": "sensor.panasonic_heat_pump_main_water_flow"},
    "hph_src_outdoor_temp": {"name": "HeatPump Hero source — outdoor temperature", "icon": "mdi:thermometer",
                              "initial": "sensor.panasonic_heat_pump_main_outside_temperature"},
    "hph_src_compressor_freq": {"name": "HeatPump Hero source — compressor frequency", "icon": "mdi:sine-wave",
                                 "initial": "sensor.panasonic_heat_pump_main_compressor_frequency"},
    "hph_src_compressor_hours": {"name": "HeatPump Hero source — compressor hours (lifetime)", "icon": "mdi:timer-sand",
                                  "initial": "sensor.panasonic_heat_pump_main_compressor_running_hours"},
    "hph_src_compressor_starts": {"name": "HeatPump Hero source — compressor starts (lifetime)", "icon": "mdi:counter",
                                   "initial": "sensor.panasonic_heat_pump_main_compressor_starts"},
    "hph_src_discharge_temp": {"name": "HeatPump Hero source — compressor discharge temperature", "icon": "mdi:thermometer-high",
                                "initial": "sensor.panasonic_heat_pump_main_discharge_temperature"},
    "hph_src_pump_pressure": {"name": "HeatPump Hero source — water pressure", "icon": "mdi:gauge",
                               # Universal across Panasonic J/K/L/T-CAP/M (TOP115).
                               "initial": "sensor.panasonic_heat_pump_main_water_pressure"},
    "hph_src_internal_power": {"name": "HeatPump Hero source — heat pump internal power consumption", "icon": "mdi:flash",
                                "initial": "sensor.panasonic_heat_pump_main_consumed_power"},
    "hph_src_internal_thermal_power": {"name": "HeatPump Hero source — heat pump internal thermal power production", "icon": "mdi:fire",
                                "initial": "sensor.panasonic_heat_pump_main_heat_power_production"},
    # Monitoring sensors added in v0.9 (Control tab — Machine Room)
    "hph_src_fan1_speed": {"name": "HeatPump Hero source — fan 1 speed (R/min)", "icon": "mdi:fan",
                            "initial": ""},
    "hph_src_fan2_speed": {"name": "HeatPump Hero source — fan 2 speed (R/min)", "icon": "mdi:fan",
                            "initial": ""},
    "hph_src_inverter_temp": {"name": "HeatPump Hero source — inverter / IPM temperature (°C)", "icon": "mdi:thermometer-high",
                               "initial": ""},
    "hph_src_high_pressure": {"name": "HeatPump Hero source — refrigerant high-side pressure", "icon": "mdi:gauge-high",
                               "initial": ""},
    "hph_src_low_pressure": {"name": "HeatPump Hero source — refrigerant low-side pressure", "icon": "mdi:gauge-low",
                              "initial": ""},
    "hph_src_compressor_current": {"name": "HeatPump Hero source — compressor current (A)", "icon": "mdi:current-ac",
                                    "initial": ""},
    "hph_src_outdoor_pipe_temp": {"name": "HeatPump Hero source — outdoor pipe temperature (°C)", "icon": "mdi:thermometer",
                                   "initial": ""},
    "hph_src_3way_valve": {"name": "HeatPump Hero source — 3-way valve state", "icon": "mdi:valve",
                            "initial": ""},
    "hph_src_zone1_target_temp": {"name": "HeatPump Hero source — zone 1 water target temperature (°C)", "icon": "mdi:thermostat",
                                   "initial": ""},
    "hph_src_hex_outlet_temp": {"name": "HeatPump Hero source — main heat exchanger outlet temperature (°C)", "icon": "mdi:thermometer-lines",
                                 "initial": ""},
    "hph_src_pump_duty": {"name": "HeatPump Hero source — pump duty cycle (%)", "icon": "mdi:pump",
                           "initial": ""},
    "hph_src_defrost_state": {"name": "HeatPump Hero source — defrost state (binary)", "icon": "mdi:snowflake-melt",
                               "initial": "binary_sensor.panasonic_heat_pump_main_defrost_state"},
    "hph_src_aux_heater_state": {"name": "HeatPump Hero source — auxiliary heater state (binary)", "icon": "mdi:radiator-disabled",
                                  "initial": "binary_sensor.panasonic_heat_pump_main_heater_state"},
    "hph_src_operating_mode": {"name": "HeatPump Hero source — operating mode (select)", "icon": "mdi:fire",
                                "initial": "select.panasonic_heat_pump_main_operating_mode_state"},
    "hph_src_error_code": {"name": "HeatPump Hero source — error / fault code", "icon": "mdi:alert-octagon",
                            "initial": "sensor.panasonic_heat_pump_main_error"},
    "hph_src_zone1_temp": {"name": "HeatPump Hero source — zone 1 temperature", "icon": "mdi:thermometer",
                            "initial": "sensor.panasonic_heat_pump_main_z1_water_temperature"},
    "hph_src_zone2_temp": {"name": "HeatPump Hero source — zone 2 temperature (blank if absent)", "icon": "mdi:thermometer",
                            "initial": ""},
    "hph_src_dhw_temp": {"name": "HeatPump Hero source — DHW tank temperature", "icon": "mdi:water-boiler",
                         "initial": "sensor.panasonic_heat_pump_main_dhw_temperature"},
    "hph_src_buffer_temp": {"name": "HeatPump Hero source — buffer-tank temperature", "icon": "mdi:propane-tank",
                             "initial": ""},
    "hph_src_dhw_target_temp": {"name": "HeatPump Hero source — DHW target temperature", "icon": "mdi:thermostat-cog",
                                 "initial": "sensor.panasonic_heat_pump_main_dhw_target_temperature"},
    "hph_src_target_supply_temp": {"name": "HeatPump Hero source — target supply temperature", "icon": "mdi:thermometer-chevron-up",
                                    "initial": ""},
    "hph_src_zone1_setpoint": {"name": "HeatPump Hero source — zone 1 water target temperature", "icon": "mdi:thermostat",
                                "initial": ""},
    "hph_src_room_temp": {"name": "HeatPump Hero source — room thermostat temperature", "icon": "mdi:home-thermometer",
                           "initial": ""},
    "hph_src_pump_speed": {"name": "HeatPump Hero source — pump speed (rpm)", "icon": "mdi:pump",
                            "initial": ""},
    "hph_src_valve_state": {"name": "HeatPump Hero source — two-way valve state", "icon": "mdi:valve",
                             "initial": ""},
    "hph_src_heater_state": {"name": "HeatPump Hero source — external heater state (binary)", "icon": "mdi:radiator",
                              "initial": ""},
    "hph_src_heater_hours": {"name": "HeatPump Hero source — heater operations hours (lifetime)", "icon": "mdi:timer-sand",
                              "initial": ""},
    "hph_src_external_thermal_power": {"name": "HeatPump Hero source — external thermal power (W)", "icon": "mdi:flash",
                                        "initial": ""},
    "hph_src_external_electrical_power": {"name": "HeatPump Hero source — external electrical power (W)", "icon": "mdi:flash",
                                           "initial": ""},
    "hph_src_external_thermal_energy": {"name": "HeatPump Hero source — external thermal energy meter (kWh)", "icon": "mdi:meter-electric",
                                         "initial": ""},
    "hph_src_external_electrical_energy": {"name": "HeatPump Hero source — external electrical energy meter (kWh)", "icon": "mdi:meter-electric",
                                            "initial": ""},
    # Vendor adapter — control write targets (hph_models.yaml)
    "hph_ctrl_write_quiet_mode": {"name": "Control write — quiet-mode select entity", "icon": "mdi:volume-mute",
                                   "initial": "select.panasonic_heat_pump_main_quiet_mode"},
    "hph_ctrl_write_force_dhw": {"name": "Control write — force-DHW button entity", "icon": "mdi:water-boiler",
                                  "initial": "button.panasonic_heat_pump_main_force_dhw"},
    "hph_ctrl_write_z1_curve_high": {"name": "Control write — Z1 heat-curve target_high entity", "icon": "mdi:thermometer-high",
                                      "initial": "number.panasonic_heat_pump_main_z1_heat_curve_target_high_temp"},
    "hph_ctrl_write_z1_curve_low": {"name": "Control write — Z1 heat-curve target_low entity", "icon": "mdi:thermometer-low",
                                     "initial": "number.panasonic_heat_pump_main_z1_heat_curve_target_low_temp"},
    "hph_ctrl_write_dhw_target": {"name": "Control write — DHW target temperature (number)", "icon": "mdi:thermostat-cog",
                                   "initial": "number.panasonic_heat_pump_main_dhw_target_temperature"},
    # Extended control write-path helpers added in v0.9 (Control tab)
    "hph_ctrl_write_operating_mode": {"name": "Control write — operating mode select entity", "icon": "mdi:thermostat",
                                       "initial": ""},
    "hph_ctrl_write_power": {"name": "Control write — main power switch entity", "icon": "mdi:power",
                              "initial": ""},
    "hph_ctrl_write_holiday": {"name": "Control write — holiday mode switch entity", "icon": "mdi:beach",
                                "initial": ""},
    "hph_ctrl_write_force_defrost": {"name": "Control write — force defrost switch entity", "icon": "mdi:snowflake-melt",
                                      "initial": ""},
    "hph_ctrl_write_powerful_mode": {"name": "Control write — powerful/boost mode select entity (vendor-specific)", "icon": "mdi:rocket-launch",
                                      "initial": ""},
    "hph_ctrl_write_active_zones": {"name": "Control write — active zones select entity", "icon": "mdi:home-floor-a",
                                     "initial": ""},
    "hph_ctrl_write_bivalent_mode": {"name": "Control write — bivalent mode select entity", "icon": "mdi:fire-circle",
                                      "initial": ""},
    "hph_ctrl_write_z1_heat_shift": {"name": "Control write — zone 1 heat request shift (number)", "icon": "mdi:plus-minus",
                                      "initial": ""},
    "hph_ctrl_write_z2_heat_shift": {"name": "Control write — zone 2 heat request shift (number)", "icon": "mdi:plus-minus",
                                      "initial": ""},
    "hph_ctrl_write_heating_cutoff": {"name": "Control write — heating cutoff outdoor temperature (number)", "icon": "mdi:thermometer-off",
                                       "initial": ""},
    "hph_ctrl_write_max_pump_duty": {"name": "Control write — maximum pump duty cycle (number)", "icon": "mdi:pump",
                                      "initial": ""},
    "hph_ctrl_write_room_heat_delta": {"name": "Control write — room heating delta / hysteresis (number)", "icon": "mdi:delta",
                                        "initial": ""},
    "hph_ctrl_write_z1_climate": {"name": "Control write — zone 1 climate entity", "icon": "mdi:home-thermometer",
                                   "initial": ""},
    "hph_ctrl_write_z2_climate": {"name": "Control write — zone 2 climate entity", "icon": "mdi:home-thermometer-outline",
                                   "initial": ""},
    # Heating curve reference points (v0.9.1 — previously hardcoded in dashboard)
    "hph_ctrl_write_z1_outside_low": {"name": "Control write — Z1 heat-curve outside_low entity", "icon": "mdi:snowflake", "initial": ""},
    "hph_ctrl_write_z1_outside_high": {"name": "Control write — Z1 heat-curve outside_high entity", "icon": "mdi:white-balance-sunny", "initial": ""},
    "hph_ctrl_write_z2_outside_low": {"name": "Control write — Z2 heat-curve outside_low entity", "icon": "mdi:snowflake", "initial": ""},
    "hph_ctrl_write_z2_outside_high": {"name": "Control write — Z2 heat-curve outside_high entity", "icon": "mdi:white-balance-sunny", "initial": ""},
    "hph_ctrl_write_z2_curve_high": {"name": "Control write — Z2 heat-curve target_high entity", "icon": "mdi:thermometer-high", "initial": ""},
    "hph_ctrl_write_z2_curve_low": {"name": "Control write — Z2 heat-curve target_low entity", "icon": "mdi:thermometer-low", "initial": ""},
    # DHW additional
    "hph_ctrl_write_dhw_heat_delta": {"name": "Control write — DHW heat delta (number)", "icon": "mdi:delta", "initial": ""},
    "hph_ctrl_write_smart_dhw": {"name": "Control write — smart DHW select entity", "icon": "mdi:auto-fix", "initial": ""},
    # Advanced settings
    "hph_ctrl_write_heating_control": {"name": "Control write — heating control select entity", "icon": "mdi:home-thermometer", "initial": ""},
    "hph_ctrl_write_cool_delta": {"name": "Control write — cooling delta (number)", "icon": "mdi:delta", "initial": ""},
    "hph_ctrl_write_dhw_sensor_selection": {"name": "Control write — DHW sensor selection entity", "icon": "mdi:water-thermometer", "initial": ""},
    "hph_ctrl_write_bivalent_start_temp": {"name": "Control write — bivalent start temperature (number)", "icon": "mdi:fire-circle", "initial": ""},
    "hph_ctrl_write_heater_delay_time": {"name": "Control write — backup heater delay time (number)", "icon": "mdi:timer-outline", "initial": ""},
    "hph_ctrl_write_heater_start_delta": {"name": "Control write — backup heater start delta (number)", "icon": "mdi:thermometer-plus", "initial": ""},
    "hph_ctrl_write_heater_stop_delta": {"name": "Control write — backup heater stop delta (number)", "icon": "mdi:thermometer-minus", "initial": ""},
    # Source — status binary sensors (read-only, vendor-conditional)
    "hph_src_force_heater": {"name": "HeatPump Hero source — force heater state", "icon": "mdi:radiator-disabled",
                              "initial": "binary_sensor.panasonic_heat_pump_main_force_heater_state"},
    "hph_src_sterilization": {"name": "HeatPump Hero source — sterilization state", "icon": "mdi:bacteria-outline",
                               "initial": "binary_sensor.panasonic_heat_pump_main_sterilization_state"},
    "hph_src_quiet_schedule": {"name": "HeatPump Hero source — quiet mode schedule", "icon": "mdi:alarm",
                                "initial": "binary_sensor.panasonic_heat_pump_main_quiet_mode_schedule"},
    # Analysis (hph_analysis.yaml)
    "hph_indoor_temp_entity": {"name": "Analysis — indoor reference temperature entity", "icon": "mdi:home-thermometer",
                                "initial": ""},
    "hph_indoor_target_entity": {"name": "Analysis — indoor target temperature entity (optional)", "icon": "mdi:home-thermometer-outline",
                                  "initial": ""},
    "hph_heating_curve_recommendation": {"name": "Analysis — heating-curve recommendation script output",
                                          "icon": "mdi:chart-line", "initial": "", "max": 255},
    # Control (hph_control.yaml)
    "hph_ctrl_pv_surplus_entity": {"name": "PV surplus sensor (entity-ID)", "icon": "mdi:solar-power", "initial": ""},
    # Control extensions (hph_control_extensions.yaml)
    # NOTE: hph_ctrl_price_entity removed in rc4-stage4 — price-driven
    # DHW now reads from text.hph_electricity_price_entity (the same
    # helper used for cost calculation). Bootstrap migrates the value
    # for existing installs.
    "hph_ctrl_price_mean_entity": {"name": "Price-DHW — daily mean price sensor (entity-ID)", "icon": "mdi:percent", "initial": ""},
    "hph_ctrl_forecast_entity": {"name": "Forecast pre-heat — forecast temperature sensor (entity-ID)",
                                  "icon": "mdi:weather-cloudy-clock", "initial": ""},
    # Bridge (hph_bridge.yaml)
    "hph_bridge_prefix": {"name": "Bridge — MQTT topic prefix", "icon": "mdi:label-outline", "initial": "hph"},
    # Diagnostics (hph_diagnostics.yaml)
    "hph_diag_error_history": {"name": "Diagnostics — error ring buffer (JSON)", "icon": "mdi:history",
                                "initial": "[]", "max": 255},
    # Advisor (hph_advisor.yaml)
    "hph_dhw_start_hours": {"name": "HeatPump Hero — DHW start-hour ring buffer (last 14)",
                             "icon": "mdi:water-boiler", "initial": "[]", "max": 64},
    # Export (hph_export.yaml)
    "hph_export_target_path": {"name": "Export target directory", "icon": "mdi:folder-download",
                                "initial": "/config/hph/exports"},
    # Outdoor temperature override (optional weather station)
    "hph_outdoor_temp_override_entity": {"name": "Outdoor temperature — external sensor override (entity-ID, optional)",
                                          "icon": "mdi:weather-partly-cloudy", "initial": ""},
    # Cost calculation
    "hph_electricity_price_entity": {"name": "Cost — electricity price sensor (entity-ID, optional)",
                                      "icon": "mdi:cash-multiple",
                                      "initial": ""},
}

# ─── Number helpers ──────────────────────────────────────────────────────
# Format: unique_id -> {"name", "min", "max", "step", "initial", "icon"}
NUMBER_HELPERS: Final[dict[str, dict[str, Any]]] = {
    # Advisor thresholds
    "hph_advisor_short_cycle_warn_pct": {"name": "Advisor — short-cycle warn threshold (%)",
                                          "min": 5, "max": 80, "step": 1, "initial": 25},
    "hph_advisor_short_cycle_crit_pct": {"name": "Advisor — short-cycle critical threshold (%)",
                                          "min": 10, "max": 90, "step": 1, "initial": 50},
    "hph_advisor_dt_target_k": {"name": "Advisor — target supply/return spread (K)",
                                 "min": 3, "max": 10, "step": 0.5, "initial": 5},
    "hph_advisor_dhw_min_runtime_min": {"name": "Advisor — DHW minimum run time (minutes)",
                                         "min": 5, "max": 60, "step": 1, "initial": 20},
    "hph_advisor_heating_limit_target_c": {"name": "Advisor — heating limit target (°C)",
                                            "min": 5, "max": 25, "step": 0.5, "initial": 16},
    "hph_heating_limit_observed_c": {"name": "Heating limit — last observed (°C)",
                                       "icon": "mdi:thermometer-off",
                                       "min": -30, "max": 30, "step": 0.1, "initial": 0},
    "hph_advisor_drift_warn_pct": {"name": "Advisor — efficiency drift warn threshold (% YoY)",
                                    "min": -50, "max": 0, "step": 1, "initial": -10},
    "hph_advisor_drift_crit_pct": {"name": "Advisor — efficiency drift critical threshold (% YoY)",
                                    "min": -50, "max": 0, "step": 1, "initial": -20},
    "hph_advisor_dhw_max_fires_per_day": {"name": "Advisor — DHW max desired fires per day",
                                            "min": 1, "max": 10, "step": 1, "initial": 2},
    "hph_advisor_pump_spread_min_samples": {"name": "Advisor — pump-curve min samples (7d)",
                                              "min": 50, "max": 5000, "step": 50, "initial": 200},
    "hph_dhw_fires_yesterday": {"name": "HeatPump Hero — DHW fires yesterday",
                                  "icon": "mdi:water-boiler",
                                  "min": 0, "max": 50, "step": 1, "initial": 0},
    # Runtime kWh today — driven by coordinators/runtime_kwh.py.
    # Accumulates external-meter delta during compressor-on intervals.
    # Resets at midnight; restored across HA reloads via Number platform.
    "hph_thermal_runtime_today_kwh": {"name": "HeatPump Hero — thermal runtime kWh today",
                                        "icon": "mdi:fire",
                                        "min": 0, "max": 9999, "step": 0.001, "initial": 0,
                                        "unit_of_measurement": "kWh"},
    "hph_electrical_runtime_today_kwh": {"name": "HeatPump Hero — electrical runtime kWh today",
                                           "icon": "mdi:flash",
                                           "min": 0, "max": 9999, "step": 0.001, "initial": 0,
                                           "unit_of_measurement": "kWh"},
    # Cost calculation
    "hph_electricity_price_ct_per_kwh": {"name": "Cost — electricity price (ct/kWh, manual fallback)",
                                           "icon": "mdi:currency-eur",
                                           "min": 0, "max": 200, "step": 0.1, "initial": 30,
                                           "unit_of_measurement": "ct/kWh"},
    # Analysis
    "hph_indoor_target_default": {"name": "Analysis — fallback indoor target (°C)",
                                    "icon": "mdi:home-thermometer", "min": 15, "max": 25,
                                    "step": 0.5, "initial": 21},
    "hph_analysis_window_days": {"name": "Analysis — observation window (days)",
                                   "icon": "mdi:calendar-range", "min": 1, "max": 30,
                                   "step": 1, "initial": 7},
    "hph_analysis_dead_band_k": {"name": "Analysis — dead band around target (K)",
                                   "icon": "mdi:plus-minus-variant", "min": 0.1, "max": 2,
                                   "step": 0.1, "initial": 0.5},
    # Control (hph_control.yaml)
    "hph_ctrl_ccc_min_pause_min": {"name": "CCC — minimum pause (minutes)",
                                     "min": 5, "max": 60, "step": 1, "initial": 15},
    "hph_ctrl_ccc_min_runtime_min": {"name": "CCC — minimum runtime (minutes)",
                                       "min": 5, "max": 60, "step": 1, "initial": 20},
    "hph_ctrl_solar_pv_threshold_w": {"name": "Solar-DHW — PV-surplus threshold (W)",
                                        "min": 500, "max": 5000, "step": 100, "initial": 1500},
    # Control extensions
    "hph_ctrl_adaptive_max_step_k": {"name": "Adaptive curve — max step per cycle (K)",
                                       "icon": "mdi:plus-minus", "min": 0.1, "max": 2,
                                       "step": 0.1, "initial": 0.5},
    "hph_ctrl_adaptive_supply_min_c": {"name": "Adaptive curve — absolute supply T° lower bound (°C)",
                                         "icon": "mdi:thermometer-low", "min": 18, "max": 35,
                                         "step": 0.5, "initial": 22},
    "hph_ctrl_adaptive_supply_max_c": {"name": "Adaptive curve — absolute supply T° upper bound (°C)",
                                         "icon": "mdi:thermometer-high", "min": 35, "max": 70,
                                         "step": 0.5, "initial": 50},
    "hph_ctrl_price_threshold_factor": {"name": "Price-DHW — fire when below daily mean × this factor",
                                          "icon": "mdi:percent", "min": 0.5, "max": 1,
                                          "step": 0.05, "initial": 0.85},
    "hph_ctrl_price_max_per_day": {"name": "Price-DHW — max forced DHW boosts per day",
                                     "icon": "mdi:counter", "min": 1, "max": 4,
                                     "step": 1, "initial": 1},
    "hph_ctrl_forecast_drop_threshold_k": {"name": "Forecast pre-heat — outdoor T° drop trigger (K in next 6h)",
                                             "icon": "mdi:thermometer-chevron-down", "min": 3, "max": 15,
                                             "step": 0.5, "initial": 8},
    "hph_ctrl_forecast_boost_k": {"name": "Forecast pre-heat — temporary curve boost (K)",
                                    "icon": "mdi:plus-thick", "min": 1, "max": 5,
                                    "step": 0.5, "initial": 2},
    # Cycles
    "hph_cycle_short_threshold_min": {"name": "HeatPump Hero — \"short cycle\" threshold (minutes)",
                                        "icon": "mdi:timer-alert", "min": 1, "max": 60,
                                        "step": 1, "initial": 10},
    "hph_cycle_last_duration_min": {"name": "HeatPump Hero — last run duration (minutes)",
                                      "icon": "mdi:timer", "min": 0, "max": 1440,
                                      "step": 0.1, "initial": 0},
    "hph_cycle_last_pause_min": {"name": "HeatPump Hero — last pause (minutes)",
                                   "icon": "mdi:timer-pause", "min": 0, "max": 1440,
                                   "step": 0.1, "initial": 0},
    # Models (hph_models.yaml)
    "hph_model_compressor_min_hz": {"name": "Model — compressor minimum frequency (Hz)",
                                      "icon": "mdi:sine-wave", "min": 5, "max": 60,
                                      "step": 1, "initial": 16},
    "hph_model_compressor_max_hz": {"name": "Model — compressor maximum frequency (Hz)",
                                      "icon": "mdi:sine-wave", "min": 50, "max": 250,
                                      "step": 5, "initial": 110},
    "hph_model_min_flow_lpm": {"name": "Model — minimum water flow (L/min)",
                                 "icon": "mdi:water-pump", "min": 5, "max": 30,
                                 "step": 0.5, "initial": 9},
    "hph_model_max_supply_c": {"name": "Model — maximum supply temperature (°C)",
                                 "icon": "mdi:thermometer-high", "min": 35, "max": 80,
                                 "step": 1, "initial": 55},
    # Programs — screed
    "hph_prog_screed_day": {"name": "Screed dry-out — current day index (0 = not running)",
                              "icon": "mdi:calendar-today",
                              "min": 0, "max": 60, "step": 1, "initial": 0},
    # Programs — legionella
    "hph_prog_legionella_target_c": {"name": "Legionella — DHW target temperature (°C)",
                                      "icon": "mdi:thermometer-high",
                                      "min": 55, "max": 75, "step": 1, "initial": 65},
    "hph_prog_legionella_hold_min": {"name": "Legionella — hold time at target (min)",
                                      "icon": "mdi:timer-outline",
                                      "min": 10, "max": 120, "step": 5, "initial": 30},
    "hph_prog_legionella_hour": {"name": "Legionella — start hour (0–23)",
                                  "icon": "mdi:clock-outline",
                                  "min": 0, "max": 23, "step": 1, "initial": 3},
}

# ─── Select helpers ──────────────────────────────────────────────────────
# Format: unique_id -> {"name", "options", "initial", "icon"}
SELECT_HELPERS: Final[dict[str, dict[str, Any]]] = {
    # Sources
    "hph_thermal_source": {"name": "HeatPump Hero — thermal-energy source mode",
                            "icon": "mdi:fire",
                            "options": ["calculated", "heat_pump_internal", "external_power", "external_energy"],
                            "initial": "heat_pump_internal"},
    "hph_electrical_source": {"name": "HeatPump Hero — electrical-energy source mode",
                                "icon": "mdi:flash",
                                "options": ["heat_pump_internal", "external_power", "external_energy"],
                                "initial": "heat_pump_internal"},
    "hph_schema_variant": {"name": "HeatPump Hero — schematic variant (auto / manual)",
                             "icon": "mdi:home-search-outline",
                             "options": ["auto", "hk1", "hk1_dhw", "hk1_hk2_dhw", "hk1_hk2_dhw_buffer"],
                             "initial": "auto"},
    # Models
    "hph_vendor_preset": {"name": "HeatPump Hero — vendor preset (auto-fills source helpers)",
                           "icon": "mdi:factory",
                           "options": list(VENDOR_PRESETS.keys()) + ["keep_current"],
                           "initial": "keep_current"},
    "hph_pump_model": {"name": "HeatPump Hero — heat-pump model",
                        "icon": "mdi:heat-pump-outline",
                        # Only Panasonic models until multi-vendor support ships.
                        # Non-Panasonic entries remain in PUMP_MODELS for threshold
                        # data but are not exposed in the UI dropdown yet.
                        "options": [
                            "panasonic_j_aqj", "panasonic_k_aqk", "panasonic_l_aql",
                            "panasonic_tcap", "panasonic_m_aqm",
                        ],
                        "initial": "panasonic_l_aql"},
    # Programs — screed
    "hph_prog_screed_profile": {"name": "Screed dry-out — profile",
                                  "icon": "mdi:chart-line",
                                  "options": ["functional_3d", "combined_10d", "din_18560_28d"],
                                  "initial": "functional_3d"},
    # Programs — legionella
    "hph_prog_legionella_weekday": {"name": "Legionella — weekday for scheduled boost",
                                     "icon": "mdi:calendar-week",
                                     "options": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                                     "initial": "sun"},
    # Export
    "hph_export_format": {"name": "Export format",
                            "icon": "mdi:file-export",
                            "options": ["csv", "json", "xlsx"], "initial": "csv"},
    "hph_export_period": {"name": "Export period",
                            "icon": "mdi:calendar-range",
                            "options": ["last_24h", "last_7d", "last_30d", "this_month", "last_month",
                                        "this_year", "last_year", "all"],
                            "initial": "last_30d"},
    "hph_export_schedule": {"name": "Export schedule",
                              "icon": "mdi:calendar-clock",
                              "options": ["off", "daily", "weekly", "monthly"],
                              "initial": "off"},
}

# ─── Switch helpers (input_boolean) ──────────────────────────────────────
# Format: unique_id -> {"name", "icon", "initial"}
SWITCH_HELPERS: Final[dict[str, dict[str, Any]]] = {
    # Control master + strategies
    "hph_ctrl_master": {"name": "HeatPump Hero Control — master switch",
                         "icon": "mdi:robot-outline", "initial": False},
    "hph_ctrl_ccc": {"name": "Compressor Cycle Control (CCC)",
                      "icon": "mdi:repeat-variant", "initial": False},
    "hph_ctrl_solar_dhw": {"name": "Solar-DHW boost", "icon": "mdi:solar-power-variant", "initial": False},
    "hph_ctrl_quiet_night": {"name": "Night quiet mode", "icon": "mdi:weather-night", "initial": False},
    # Control extensions
    "hph_ctrl_adaptive_curve": {"name": "HPH Control — adaptive heating curve (self-learning)",
                                  "icon": "mdi:auto-fix", "initial": False},
    "hph_ctrl_price_dhw": {"name": "HPH Control — price-driven DHW (Tibber/aWATTar)",
                             "icon": "mdi:currency-eur", "initial": False},
    "hph_ctrl_forecast_preheat": {"name": "HPH Control — weather-forecast pre-heating",
                                    "icon": "mdi:weather-snowy", "initial": False},
    "hph_ctrl_forecast_preheat_active": {"name": "HPH Control — forecast pre-heat is currently boosting",
                                            "icon": "mdi:weather-snowy-heavy", "initial": False},
    # Programs — screed
    "hph_prog_screed": {"name": "HPH Program — screed dry-out",
                         "icon": "mdi:home-floor-a", "initial": False},
    "hph_prog_screed_active": {"name": "HPH Program — screed program currently running",
                                 "icon": "mdi:play-circle-outline", "initial": False},
    # Programs — legionella
    "hph_prog_legionella": {"name": "HPH Program — legionella protection schedule",
                              "icon": "mdi:shield-bug", "initial": False},
    # Bridge
    "hph_bridge_enabled": {"name": "HPH Bridge — multi-platform read-only MQTT republisher",
                             "icon": "mdi:lan-connect", "initial": False},
}

# ─── Datetime helpers ────────────────────────────────────────────────────
# Format: unique_id -> {"name", "icon", "has_date", "has_time"}
DATETIME_HELPERS: Final[dict[str, dict[str, Any]]] = {
    "hph_cycle_last_start": {"name": "HeatPump Hero — last cycle start", "has_date": True, "has_time": True},
    "hph_cycle_last_end": {"name": "HeatPump Hero — last cycle end", "has_date": True, "has_time": True},
    "hph_diag_last_error_time": {"name": "HeatPump Hero — last error timestamp",
                                   "icon": "mdi:clock-alert", "has_date": True, "has_time": True},
    "hph_export_last_run": {"name": "HeatPump Hero — last export run",
                              "icon": "mdi:clock-check-outline", "has_date": True, "has_time": True},
    "hph_ctrl_adaptive_last_run": {"name": "Adaptive curve — last application",
                                     "icon": "mdi:clock-check-outline", "has_date": True, "has_time": True},
    "hph_ctrl_price_dhw_last_fire": {"name": "Price-DHW — last force-DHW timestamp",
                                       "icon": "mdi:clock-check-outline", "has_date": True, "has_time": True},
    "hph_prog_screed_start": {"name": "Screed dry-out — program start",
                                "icon": "mdi:calendar-start", "has_date": True, "has_time": True},
    "hph_prog_legionella_last_run": {"name": "Legionella — last run timestamp",
                                      "icon": "mdi:clock-check-outline", "has_date": True, "has_time": True},
}

# ─── Counter helpers (mapped onto HA Counter via Number-with-restore) ────
# Counters are tricky in custom integrations — HA's Counter helper is
# part of the input_* family. We expose them as Number entities with
# step=1 and a corresponding Button to reset; the cycle-event logic
# (incrementing on compressor start) is implemented in coordinators.
# Format: unique_id -> {"name", "icon", "initial"}
COUNTER_HELPERS: Final[dict[str, dict[str, Any]]] = {
    "hph_cycles_today": {"name": "HeatPump Hero — cycles today",
                           "icon": "mdi:counter", "initial": 0},
    "hph_short_cycles_today": {"name": "HeatPump Hero — short cycles today",
                                 "icon": "mdi:timer-alert-outline", "initial": 0},
    "hph_dhw_fires_today": {"name": "HeatPump Hero — DHW fires today",
                              "icon": "mdi:water-boiler", "initial": 0},
    "hph_ctrl_price_dhw_fires_today": {"name": "Price-DHW — fires today",
                                          "icon": "mdi:counter", "initial": 0},
}

# ─── Button definitions ──────────────────────────────────────────────────
# Buttons trigger services. Format: unique_id -> {"name", "icon", "service"}
BUTTON_DEFS: Final[dict[str, dict[str, Any]]] = {
    "hph_export_now": {"name": "HeatPump Hero — export now (manual trigger)",
                         "icon": "mdi:download", "service": SERVICE_EXPORT_NOW},
    "hph_run_legionella_now": {"name": "HeatPump Hero — run legionella program now",
                                  "icon": "mdi:bacteria", "service": SERVICE_RUN_LEGIONELLA},
    "hph_reset_cycles_today": {"name": "HeatPump Hero — reset cycles-today counter",
                                  "icon": "mdi:counter", "service": "reset_counter",
                                  "service_data": {"counter": "hph_cycles_today"}},
    "hph_reset_short_cycles_today": {"name": "HeatPump Hero — reset short-cycles-today counter",
                                        "icon": "mdi:counter", "service": "reset_counter",
                                        "service_data": {"counter": "hph_short_cycles_today"}},
}

# ───────────────────────────────────────────────────────────────────────────
# Typed control facade entities — Phase B of the HAL completion.
#
# Each entry describes a vendor-agnostic proxy entity (select.hph_*, switch.hph_*,
# number.hph_* or button.hph_*) that transparently forwards reads/writes to the
# native vendor entity configured in the matching text.hph_ctrl_write_* helper.
#
# Conditional availability is built-in: when the writer helper is empty (vendor
# does not support this feature, or feature gated off), the proxy reports
# `unavailable` and dashboard cards wrapped in `condition: state_not: unavailable`
# disappear automatically. This is how feature support per vendor / model is
# expressed at runtime.
#
# Each entry:
#   platform: "select" | "switch" | "number" | "button"
#   writer:   key of the matching entry in TEXT_HELPERS (its value is the
#             entity_id of the native vendor entity)
#   name:     display name of the proxy
#   icon:     mdi: icon
#   options:  (select only, optional) fallback options if the target entity
#             does not expose attributes.options at registration time
#   min/max/step/unit_of_measurement: (number only, optional) fallback range
#             if the target entity does not expose them
# ───────────────────────────────────────────────────────────────────────────
CTRL_FACADES: Final[dict[str, dict[str, Any]]] = {
    # Selects (multi-option choices)
    "hph_quiet_mode": {
        "platform": "select", "writer": "hph_ctrl_write_quiet_mode",
        "name": "Quiet mode", "icon": "mdi:volume-mute",
        "options": ["Off", "Level 1", "Level 2", "Level 3"],
    },
    "hph_ctrl_operating_mode": {
        "platform": "select", "writer": "hph_ctrl_write_operating_mode",
        "name": "Operating mode", "icon": "mdi:thermostat",
        "options": ["Heat", "Cool", "Auto", "DHW", "Heat+DHW", "Cool+DHW"],
    },
    "hph_powerful_mode": {
        "platform": "select", "writer": "hph_ctrl_write_powerful_mode",
        "name": "Powerful / boost mode", "icon": "mdi:rocket-launch",
        "options": ["Off", "30 min", "60 min", "90 min"],
    },
    "hph_active_zones": {
        "platform": "select", "writer": "hph_ctrl_write_active_zones",
        "name": "Active zones", "icon": "mdi:home-floor-a",
        "options": ["Zone 1", "Zone 2", "Both"],
    },
    "hph_bivalent_mode": {
        "platform": "select", "writer": "hph_ctrl_write_bivalent_mode",
        "name": "Bivalent mode", "icon": "mdi:fire-circle",
        "options": ["Off", "Alternative", "Parallel", "Advanced parallel"],
    },
    # Switches (on/off)
    "hph_power": {
        "platform": "switch", "writer": "hph_ctrl_write_power",
        "name": "Main power", "icon": "mdi:power",
    },
    "hph_holiday": {
        "platform": "switch", "writer": "hph_ctrl_write_holiday",
        "name": "Holiday mode", "icon": "mdi:beach",
    },
    "hph_force_defrost": {
        "platform": "switch", "writer": "hph_ctrl_write_force_defrost",
        "name": "Force defrost", "icon": "mdi:snowflake-melt",
    },
    # Numbers (continuous values)
    "hph_z1_curve_high": {
        "platform": "number", "writer": "hph_ctrl_write_z1_curve_high",
        "name": "Zone 1 heat curve — outlet at low outdoor", "icon": "mdi:thermometer-high",
        "min": 20, "max": 60, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z1_curve_low": {
        "platform": "number", "writer": "hph_ctrl_write_z1_curve_low",
        "name": "Zone 1 heat curve — outlet at high outdoor", "icon": "mdi:thermometer-low",
        "min": 20, "max": 60, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_dhw_target": {
        "platform": "number", "writer": "hph_ctrl_write_dhw_target",
        "name": "DHW target temperature", "icon": "mdi:thermostat-cog",
        "min": 30, "max": 65, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z1_heat_shift": {
        "platform": "number", "writer": "hph_ctrl_write_z1_heat_shift",
        "name": "Zone 1 heat request shift", "icon": "mdi:plus-minus",
        "min": -5, "max": 5, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z2_heat_shift": {
        "platform": "number", "writer": "hph_ctrl_write_z2_heat_shift",
        "name": "Zone 2 heat request shift", "icon": "mdi:plus-minus",
        "min": -5, "max": 5, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_heating_cutoff": {
        "platform": "number", "writer": "hph_ctrl_write_heating_cutoff",
        "name": "Heating cutoff outdoor temperature", "icon": "mdi:thermometer-off",
        "min": 5, "max": 25, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_max_pump_duty": {
        "platform": "number", "writer": "hph_ctrl_write_max_pump_duty",
        "name": "Maximum pump duty cycle", "icon": "mdi:pump",
        "min": 30, "max": 100, "step": 1, "unit_of_measurement": "%",
    },
    "hph_room_heat_delta": {
        "platform": "number", "writer": "hph_ctrl_write_room_heat_delta",
        "name": "Room heating delta / hysteresis", "icon": "mdi:delta",
        "min": 1, "max": 10, "step": 1, "unit_of_measurement": "°C",
    },
    # Buttons (one-shot actions)
    "hph_force_dhw": {
        "platform": "button", "writer": "hph_ctrl_write_force_dhw",
        "name": "Force DHW now", "icon": "mdi:water-boiler",
    },
    # Heating curve reference points (v0.9.1)
    "hph_z1_outside_low": {
        "platform": "number", "writer": "hph_ctrl_write_z1_outside_low",
        "name": "Zone 1 heat curve — outside low", "icon": "mdi:snowflake",
        "min": -20, "max": 20, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z1_outside_high": {
        "platform": "number", "writer": "hph_ctrl_write_z1_outside_high",
        "name": "Zone 1 heat curve — outside high", "icon": "mdi:white-balance-sunny",
        "min": -10, "max": 30, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z2_outside_low": {
        "platform": "number", "writer": "hph_ctrl_write_z2_outside_low",
        "name": "Zone 2 heat curve — outside low", "icon": "mdi:snowflake",
        "min": -20, "max": 20, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z2_outside_high": {
        "platform": "number", "writer": "hph_ctrl_write_z2_outside_high",
        "name": "Zone 2 heat curve — outside high", "icon": "mdi:white-balance-sunny",
        "min": -10, "max": 30, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z2_curve_high": {
        "platform": "number", "writer": "hph_ctrl_write_z2_curve_high",
        "name": "Zone 2 heat curve — outlet at low outdoor", "icon": "mdi:thermometer-high",
        "min": 20, "max": 60, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_z2_curve_low": {
        "platform": "number", "writer": "hph_ctrl_write_z2_curve_low",
        "name": "Zone 2 heat curve — outlet at high outdoor", "icon": "mdi:thermometer-low",
        "min": 20, "max": 60, "step": 1, "unit_of_measurement": "°C",
    },
    # DHW additional (v0.9.1)
    "hph_dhw_heat_delta": {
        "platform": "number", "writer": "hph_ctrl_write_dhw_heat_delta",
        "name": "DHW heat delta", "icon": "mdi:delta",
        "min": 2, "max": 15, "step": 1, "unit_of_measurement": "K",
    },
    "hph_smart_dhw": {
        "platform": "select", "writer": "hph_ctrl_write_smart_dhw",
        "name": "Smart DHW", "icon": "mdi:auto-fix",
        "options": ["Off", "On"],
    },
    # Advanced settings (v0.9.1)
    "hph_heating_control": {
        "platform": "select", "writer": "hph_ctrl_write_heating_control",
        "name": "Heating control mode", "icon": "mdi:home-thermometer",
        "options": ["Compensation curve", "Direct", "Thermostat"],
    },
    "hph_cool_delta": {
        "platform": "number", "writer": "hph_ctrl_write_cool_delta",
        "name": "Cooling delta", "icon": "mdi:snowflake",
        "min": 1, "max": 15, "step": 1, "unit_of_measurement": "K",
    },
    "hph_dhw_sensor_selection": {
        "platform": "select", "writer": "hph_ctrl_write_dhw_sensor_selection",
        "name": "DHW sensor selection", "icon": "mdi:water-thermometer",
        "options": ["Internal", "External", "Compensation"],
    },
    "hph_bivalent_start_temp": {
        "platform": "number", "writer": "hph_ctrl_write_bivalent_start_temp",
        "name": "Bivalent start temperature", "icon": "mdi:thermometer-low",
        "min": -20, "max": 20, "step": 1, "unit_of_measurement": "°C",
    },
    "hph_heater_delay_time": {
        "platform": "number", "writer": "hph_ctrl_write_heater_delay_time",
        "name": "Backup heater delay time", "icon": "mdi:timer-outline",
        "min": 0, "max": 60, "step": 1, "unit_of_measurement": "min",
    },
    "hph_heater_start_delta": {
        "platform": "number", "writer": "hph_ctrl_write_heater_start_delta",
        "name": "Backup heater start delta", "icon": "mdi:arrow-up-bold-circle",
        "min": 1, "max": 30, "step": 1, "unit_of_measurement": "K",
    },
    "hph_heater_stop_delta": {
        "platform": "number", "writer": "hph_ctrl_write_heater_stop_delta",
        "name": "Backup heater stop delta", "icon": "mdi:arrow-down-bold-circle",
        "min": 1, "max": 30, "step": 1, "unit_of_measurement": "K",
    },
}


# Platforms HA loads at setup time
PLATFORMS: Final[list[str]] = [
    "text", "number", "select", "switch", "datetime", "button",
    "sensor", "binary_sensor",
]
