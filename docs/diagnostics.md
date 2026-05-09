# Diagnostics — Panasonic Aquarea fault codes

🌐 English (this file)

Heat Pump Hero's diagnostics module reads `sensor.hph_source_error_code`
and maps the value to a human-readable description, severity, and
model-specific commentary. The result is exposed as
`sensor.hph_diagnostics_current_error` with these attributes:

- `state` — the active code (e.g. `H23`) or `ok`
- `severity` — `critical | warn | info | none`
- `message` — plain-language explanation
- `model_note` — extra context for known model-specific issues
  (currently J-series H23, R32/R290 H99, J/K-series H62 false alarms)

Plus:
- `sensor.hph_diagnostics_recurrence` — count of the same code in the
  last 5 events
- `input_text.hph_diag_error_history` — JSON ring buffer of the last
  5 events with timestamps
- `input_datetime.hph_diag_last_error_time` — time of the most recent
  fault
- An advisor (`sensor.hph_advisor_diagnostics`) folds active fault +
  recurrence into the aggregate traffic-light tile.

## Severity classification

| Severity | Meaning | Example codes |
|---|---|---|
| **critical** | Refrigerant-cycle, inverter, freeze, or pressure protection — service usually required | F12, F14, F22-F24, F27, F41, F46, H21, H62, H63, H64, H65, H75, H98, H99 |
| **warn** | Recoverable sensor / overload / communication issues — investigate but not urgent | H15, H20, H23, H27, H42, H67, H68, H70, H72, H74, H76, H90, H91, H95, F15, F16, F20, F25, F36, F37, F40, F42, F45, F48, F95 |
| **info** | Capacity / mismatch / ancillary — usually configuration-related | H12, H28, H31, H36, H38, H43, H44 |
| **none** | No active fault | OK / H00 |

## Code reference

### H-codes (soft faults)

| Code | Description |
|---|---|
| H12 | Capacity mismatch indoor/outdoor |
| H15 | Compressor temperature sensor open |
| H20 | Pump abnormality |
| H21 | Float switch / water leakage |
| H23 | Refrigerant-cycle abnormality (**J-series weak point**) |
| H27 | Service valve abnormality |
| H28 | Solar sensor abnormality |
| H31 | Swimming-pool sensor abnormality |
| H36 | Buffer-tank sensor abnormality |
| H38 | Brand mismatch indoor/outdoor |
| H42 | Compressor low-pressure protection |
| H43 | Zone 1 sensor abnormality |
| H44 | Zone 2 sensor abnormality |
| H62 | Water flow switch (J/K often false-positive during defrost) |
| H63 | Low refrigerant pressure |
| H64 | High refrigerant pressure (cleanliness of evaporator/condenser) |
| H65 | Water-circulation pump abnormality during defrost |
| H67 | External thermistor 1 |
| H68 | External thermistor 2 |
| H70 | Backup heater overload |
| H72 | Tank temperature sensor abnormality |
| H74 | PCB communication |
| H75 | Low-temperature protection (water freeze risk) |
| H76 | Remote control communication |
| H90 | Indoor↔outdoor communication |
| H91 | Tank booster heater overload |
| H95 | Power supply error |
| H98 | High-pressure protection (related to H64) |
| H99 | Heat-exchanger freeze protection (R32/R290 units — flow / glycol) |

### F-codes (compressor / refrigerant)

| Code | Description |
|---|---|
| F12 | Pressure-switch activated (older boards) |
| F14 | Compressor revolution failure |
| F15 | Outdoor fan motor lock |
| F16 | Total operating current protection |
| F20 | Compressor overheat |
| F22 | Transistor module overheat |
| F23 | DC peak detection (inverter) |
| F24 | Refrigeration cycle abnormality (different from H23) |
| F25 | Cooling/heating cycle changeover failure |
| F27 | Pressure switch faulty |
| F36 | Outdoor temperature sensor |
| F37 | Water inlet temperature sensor |
| F40 | Compressor discharge temperature sensor |
| F41 | Power factor correction |
| F42 | Heat-exchanger temperature sensor |
| F45 | Water outlet temperature sensor |
| F46 | Current transformer disconnected |
| F48 | Evaporator outlet sensor |
| F95 | High outdoor temperature protection (cooling) |

## Model-specific commentary

The advisor adds extra context for these combinations:

- **`H23` + J-series** → "H23 is a known weak point on the J-series.
  Check refrigerant charge, expansion valve, and discharge sensor before
  assuming a leak."
- **`H99` + L/T-CAP/M** → "Freeze protection on R32/R290 units. Verify
  minimum flow rate (model-dependent — see `input_number.hph_model_min_flow_lpm`)
  and that no zone valve is fully closed during heat-up."
- **`H62` (any model)** → "Water-flow switch alarm. Check pump speed,
  dirt traps, air pockets. On J/K-series this is also a common false
  alarm during defrost."

Add more via PR — model-specific patterns are a perfect community contribution.

## Notification flow

When the active code changes:
1. Timestamp written to `input_datetime.hph_diag_last_error_time`
2. Event appended to JSON ring buffer (`input_text.hph_diag_error_history`)
3. Persistent notification is created (severity + message + model note)
4. When the code returns to `ok`, the notification is dismissed

The Optimization view in the dashboard surfaces the active fault prominently
when one is present; the Mobile view shows a red fault tile.

## Sources of the error code

| Vendor | Entity (default) |
|---|---|
| Heishamon (kamaradclimber) | `sensor.panasonic_heat_pump_main_error` |
| Daikin Altherma | (varies — `sensor.altherma_error_code` if exposed) |
| MELCloud | not directly exposed; bridge via custom MQTT publisher |
| Vaillant mypyllant | `sensor.<system_id>_diagnostic_error` |
| Stiebel ISG | parameters under `sensor.isg_error_*` |

Set the right entity in `input_text.hph_src_error_code` (Configuration
view → Optional components).
