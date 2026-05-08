# Tweaking — power-user customizations

🌐 English (this file) · [Deutsch](de/tweaking.md)

## 1. Change the MQTT topic prefix

Default: `panasonic_heat_pump`. If your Heishamon firmware uses a different
prefix (e.g. `wp_basement`), search-and-replace across all packages — the
quickest way:

```bash
cd /config/packages
sed -i 's|panasonic_heat_pump|wp_basement|g' heishahub_*.yaml
```

Adjust the dashboard YAML accordingly.

> Planned for v0.2: a single variable in `secrets.yaml`, edited once.

## 2. Add your own advisor rule

Add a block to `packages/heishahub_advisor.yaml`, e.g. "water pressure too
low":

```yaml
- name: "HeishaHub Advisor Pressure"
  unique_id: heishahub_advisor_pressure
  icon: mdi:gauge-low
  state: >-
    {% set p = states('sensor.panasonic_heat_pump_main_pump_pressure') | float(0) %}
    {% if p < 0.8 %}critical
    {% elif p < 1.0 %}warn
    {% else %}ok{% endif %}
  attributes:
    metric: "{{ states('sensor.panasonic_heat_pump_main_pump_pressure') }} bar"
    message: >-
      {% set p = states('sensor.panasonic_heat_pump_main_pump_pressure') | float(0) %}
      {% if p < 0.8 %}
      Water pressure critically low — top up immediately.
      {% elif p < 1.0 %}
      Water pressure below 1 bar — top up soon.
      {% else %}
      Pressure ok ({{ p }} bar).
      {% endif %}
```

Then add it to `heishahub_advisor_summary`.

## 3. Custom control automation

Create `packages/my_overrides.yaml` and put your own automations there. Avoid
clashing with `heishahub_control.yaml` — your automations should either
respect the same `input_boolean` switches or carry their own helpers.

## 4. Adjust Quiet-Mode values

The control automations toggle Quiet-Mode 0/2/3. Tweak the
`select.select_option` calls in `packages/heishahub_control.yaml` to fit
your preference.

## 5. Custom dashboard layout

`dashboards/heishahub.yaml` is plain Lovelace YAML — edit freely. Beware
that `scripts/install.sh` overwrites the file on update. If you want
permanent customizations:

- Duplicate the dashboard in the UI (UI → Dashboard → ⋮ → Duplicate).
- HeishaHub updates only refresh the original.

## 6. Localize / customize advisor messages

Messages are free-form. To switch language or rewrite the diagnostic text,
edit the `attributes.message` templates directly.
PRs with translations or improved wording welcome.

## 7. External sensors without UI helpers

To replace the active-power logic entirely (e.g. summing several Shellys),
override the `template.sensor.heishahub_*_power_active` blocks in
`heishahub_external.yaml`. All other packages reference only the `_active`
sensors, so a single edit is enough.

## 8. Custom utility_meter periods

Default: daily / monthly / yearly, reset on period boundary. For a
heating-season counter (October–April), in `heishahub_efficiency.yaml`:

```yaml
heishahub_thermal_heating_season:
  source: sensor.heishahub_thermal_energy
  cycle: yearly
  offset: { months: 9 }   # start October
```

Mirror for `electrical_*` and add a season-SCOP template.
