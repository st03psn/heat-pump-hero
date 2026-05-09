"""HeatPump Hero — domain constants and helper-entity definitions.

The integration is data-driven: every Python platform reads its entity
list from one of the dicts below. Each dict mirrors the original
`input_*` / `counter` definitions in `packages/hph_*.yaml` so the
existing `unique_id`s are preserved (entity-registry continuity).
"""

from __future__ import annotations

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
DASHBOARD_FILE_REL: Final = "hph/dashboard.yaml"  # relative to <config>/

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
        "hph_src_defrost_state": "binary_sensor.panasonic_heat_pump_main_defrosting_state",
        "hph_src_aux_heater_state": "binary_sensor.panasonic_heat_pump_main_room_heater_state",
        "hph_src_operating_mode": "select.panasonic_heat_pump_main_operating_mode_state",
        "hph_src_zone1_temp": "sensor.panasonic_heat_pump_main_z1_temp",
        "hph_src_zone2_temp": "sensor.panasonic_heat_pump_main_z2_temp",
        "hph_src_dhw_temp": "sensor.panasonic_heat_pump_main_dhw_temp",
        "hph_src_buffer_temp": "sensor.panasonic_heat_pump_main_buffer_temp",
        "hph_src_dhw_target_temp": "sensor.panasonic_heat_pump_main_dhw_target_temp",
        "hph_src_error_code": "sensor.panasonic_heat_pump_main_error",
        "hph_ctrl_write_quiet_mode": "select.panasonic_heat_pump_main_quiet_mode_level",
        "hph_ctrl_write_force_dhw": "button.panasonic_heat_pump_main_force_dhw",
        "hph_ctrl_write_z1_curve_high": "number.panasonic_heat_pump_main_z1_heat_curve_target_high_temp",
        "hph_ctrl_write_z1_curve_low": "number.panasonic_heat_pump_main_z1_heat_curve_target_low_temp",
        "hph_ctrl_write_dhw_target": "number.panasonic_heat_pump_main_dhw_target_temp",
    },
    "panasonic_heishamon_mqtt": {
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
                               "initial": "sensor.panasonic_heat_pump_main_pump_pressure"},
    "hph_src_internal_power": {"name": "HeatPump Hero source — heat pump internal power consumption", "icon": "mdi:flash",
                                "initial": "sensor.panasonic_heat_pump_main_consumed_power"},
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
    "hph_ctrl_price_entity": {"name": "Price-DHW — current price sensor (entity-ID)", "icon": "mdi:currency-eur", "initial": ""},
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
                                "initial": "/config/www/hph_exports"},
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
    # Programs
    "hph_prog_screed_day": {"name": "Screed dry-out — current day index (0 = not running)",
                              "icon": "mdi:calendar-today",
                              "min": 0, "max": 60, "step": 1, "initial": 0},
}

# ─── Select helpers ──────────────────────────────────────────────────────
# Format: unique_id -> {"name", "options", "initial", "icon"}
SELECT_HELPERS: Final[dict[str, dict[str, Any]]] = {
    # Sources
    "hph_thermal_source": {"name": "HeatPump Hero — thermal-energy source mode",
                            "icon": "mdi:fire",
                            "options": ["calculated", "external_power", "external_energy"],
                            "initial": "calculated"},
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
                        "options": list(PUMP_MODELS.keys()),
                        "initial": "panasonic_l_aql"},
    # Programs
    "hph_prog_screed_profile": {"name": "Screed dry-out — profile",
                                  "icon": "mdi:chart-line",
                                  "options": ["functional_3d", "combined_10d", "din_18560_28d"],
                                  "initial": "functional_3d"},
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
    # Programs
    "hph_prog_screed": {"name": "HPH Program — screed dry-out",
                         "icon": "mdi:home-floor-a", "initial": False},
    "hph_prog_screed_active": {"name": "HPH Program — screed program currently running",
                                 "icon": "mdi:play-circle-outline", "initial": False},
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

# Platforms HA loads at setup time
PLATFORMS: Final[list[str]] = [
    "text", "number", "select", "switch", "datetime", "button",
    "sensor", "binary_sensor",
]
