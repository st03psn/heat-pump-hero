"""
Restructure the Overview tab in hph.yaml:
  - Wraps existing mushroom cards (lines 26-368) in conditional state=mushroom
  - Adds a parallel conditional state=classic block with entities-card layout
  - SVG schematics (lines 369+) remain unchanged at their current indent level
Run from the repo root: py scripts/_restructure_overview.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DASHBOARD = "D:/DEV/heat-pump-hero/dashboards/hph.yaml"

with open(DASHBOARD, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 0-indexed boundaries verified by inspection:
MUSHROOM_START = 25   # '          - type: custom:mushroom-chips-card'
MUSHROOM_END   = 368  # '          # -- Variant a2w_hk1 --' (first SVG line, exclusive)

print("MUSHROOM_START:", repr(lines[MUSHROOM_START][:70]))
print("MUSHROOM_END  :", repr(lines[MUSHROOM_END][:70]))
print(f"Mushroom section: {MUSHROOM_END - MUSHROOM_START} lines")

# Re-indent mushroom content: +6 spaces (moves inside conditional > card > v-stack > cards)
mushroom_reindented = []
for line in lines[MUSHROOM_START:MUSHROOM_END]:
    if line.strip():
        mushroom_reindented.append("      " + line)
    else:
        mushroom_reindented.append(line)

MUSHROOM_WRAPPER_HEADER = """\

          # ── Mushroom style (default) ──────────────────────────────────────────
          - type: conditional
            conditions:
              - condition: state
                entity: select.hph_ui_style
                state: mushroom
            card:
              type: vertical-stack
              cards:

"""

CLASSIC_SECTION = """\

          # ── Classic style ─────────────────────────────────────────────────────
          - type: conditional
            conditions:
              - condition: state
                entity: select.hph_ui_style
                state: classic
            card:
              type: vertical-stack
              cards:

                # ── 3-column status grid ──────────────────────────────────────────
                - type: grid
                  columns: 3
                  square: false
                  cards:

                    # System status
                    - type: entities
                      show_header_toggle: false
                      state_color: false
                      card_mod:
                        style: |
                          ha-card {
                            background: #1a252f;
                            border: 1px solid #3d5166;
                            border-radius: 8px;
                          }
                          state-badge { display: none; }
                      entities:
                        - entity: sensor.hph_operating_mode
                          name: Operating mode
                        - entity: binary_sensor.hph_compressor_running
                          name: Compressor running
                        - entity: sensor.hph_source_compressor_freq
                          name: Compressor frequency
                        - entity: sensor.hph_source_outdoor_temp
                          name: Outdoor temperature
                        - entity: sensor.hph_source_outlet_temp
                          name: Supply temperature
                        - entity: sensor.hph_source_inlet_temp
                          name: Return temperature
                        - entity: sensor.hph_water_spread
                          name: Spread (delta T)
                        - entity: sensor.hph_source_flow_rate
                          name: Flow rate
                        - entity: sensor.hph_source_pump_pressure
                          name: Pump pressure
                        - entity: binary_sensor.hph_defrost_active
                          name: Defrost active

                    # Efficiency
                    - type: entities
                      show_header_toggle: false
                      state_color: false
                      card_mod:
                        style: |
                          ha-card {
                            background: #1a252f;
                            border: 1px solid #3d5166;
                            border-radius: 8px;
                          }
                          state-badge { display: none; }
                      entities:
                        - entity: sensor.hph_cop_live
                          name: COP live
                        - entity: sensor.hph_cop_daily
                          name: COP today
                        - entity: sensor.hph_cop_monthly
                          name: COP this month
                        - entity: sensor.hph_scop
                          name: SCOP (season)
                        - entity: sensor.hph_thermal_power_active
                          name: Thermal power
                        - entity: sensor.hph_electrical_power_active
                          name: Electrical power
                        - entity: sensor.hph_electrical_daily
                          name: Electrical today
                        - entity: sensor.hph_standby_electrical_daily
                          name: Standby today

                    # Cost & energy
                    - type: entities
                      show_header_toggle: false
                      state_color: false
                      card_mod:
                        style: |
                          ha-card {
                            background: #1a252f;
                            border: 1px solid #3d5166;
                            border-radius: 8px;
                          }
                          state-badge { display: none; }
                      entities:
                        - entity: sensor.hph_cost_today
                          name: Cost today
                        - entity: sensor.hph_cost_monthly
                          name: Cost this month
                        - entity: sensor.hph_cop_change_yoy_pct
                          name: vs last year (COP %)
                        - entity: sensor.hph_thermal_change_yoy_pct
                          name: vs last year (thermal %)
                        - entity: sensor.hph_advisor_summary
                          name: Advisor status
                        - entity: sensor.hph_schema_variant_active
                          name: Installation variant

                # ── Active fault (classic) ────────────────────────────────────────
                - type: conditional
                  conditions:
                    - entity: sensor.hph_diagnostics_current_error
                      state_not: ok
                  card:
                    type: entities
                    show_header_toggle: false
                    state_color: false
                    card_mod:
                      style: |
                        ha-card {
                          background: #1f1212;
                          border: 1px solid #8b2020;
                          border-radius: 8px;
                        }
                        state-badge { display: none; }
                    entities:
                      - entity: sensor.hph_diagnostics_current_error
                        name: Active fault
                      - entity: sensor.hph_diagnostics_recurrence
                        name: Recurrence count

                # ── Screed running (classic) ──────────────────────────────────────
                - type: conditional
                  conditions:
                    - entity: sensor.hph_prog_screed_status
                      state: running
                  card:
                    type: entities
                    show_header_toggle: false
                    state_color: false
                    entities:
                      - entity: sensor.hph_prog_screed_status
                        name: Screed program
                      - entity: number.hph_prog_screed_day
                        name: Day
                      - entity: sensor.hph_prog_screed_target
                        name: Target temperature

"""

new_content = (
    "".join(lines[:MUSHROOM_START])
    + MUSHROOM_WRAPPER_HEADER
    + "".join(mushroom_reindented)
    + CLASSIC_SECTION
    + "".join(lines[MUSHROOM_END:])
)

with open(DASHBOARD, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Written. New file size: {len(new_content):,} chars")
