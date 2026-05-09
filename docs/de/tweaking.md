# Tweaking — Anpassungen für Power-User

🌐 [English](../tweaking.md) · Deutsch (diese Datei)


## 1. MQTT-Topic-Prefix ändern

Default: `panasonic_heat_pump`. Wenn deine Heishamon-Firmware auf einen
anderen Prefix konfiguriert ist (z. B. `wp_keller`), in **allen Packages**
suchen-und-ersetzen — am einfachsten via `sed`:

```bash
cd /config/packages
sed -i 's|panasonic_heat_pump|wp_keller|g' hph_*.yaml
```

Im Dashboard-YAML ebenfalls anpassen.

> Geplant für v0.2: zentrale Variable in `secrets.yaml`, sodass nur an einer
> Stelle geändert werden muss.

## 2. Eigene Advisor-Regel hinzufügen

In `packages/hph_advisor.yaml` neuen Block ergänzen, z. B. „Wasserdruck
zu niedrig":

```yaml
- name: "Heat Pump Hero Advisor Pressure"
  unique_id: hph_advisor_pressure
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
      Wasserdruck kritisch niedrig — sofort nachfüllen!
      {% elif p < 1.0 %}
      Wasserdruck unter 1 bar — bald nachfüllen.
      {% else %}
      Druck ok ({{ p }} bar).
      {% endif %}
```

Anschließend `hph_advisor_summary` aktualisieren.

## 3. Eigene Steuer-Automation

Neue Datei `packages/my_overrides.yaml` anlegen, dort beliebige Automations.
Konflikte mit `hph_control.yaml` vermeiden — eigene Automations sollten
**dieselben** input_boolean-Schalter respektieren oder eigene Helper benutzen.

## 4. Quiet-Mode-Werte anpassen

Die Control-Automations setzen Quiet-Mode 0/2/3. Werte anpassen direkt in
`packages/hph_control.yaml` an den `select.select_option`-Aufrufen.

## 5. Dashboard-Layout anpassen

`dashboards/hph.yaml` ist normales Lovelace-YAML — beliebig editierbar.
Beim Update via `scripts/install.sh` wird die Datei **überschrieben**. Wer
dauerhaft eigenes Layout will:

- Dashboard im UI duplizieren (UI → Dashboard → ⋮ → Duplicate)
- Heat Pump Hero-Updates ziehen nur das Original-Dashboard nach.

## 6. Advisor-Empfehlungen lokalisieren / anpassen

Messages sind frei editierbar. Wer eigene Diagnose-Texte oder andere
Sprache möchte: `attributes.message`-Templates direkt anpassen.
PRs mit Übersetzungen oder verbesserten Texten willkommen.

## 7. Externe Sensoren ohne UI-Helper

Wer die Active-Power-Logik komplett ersetzen will (z. B. weil mehrere Shellys
addiert werden müssen): die `template.sensor.hph_*_power_active`-Blöcke
in `hph_external.yaml` durch eigene Templates ersetzen. Andere Packages
greifen nur auf die `_active`-Sensoren zu — eine zentrale Änderung reicht.

## 8. utility_meter-Reset ändern

Default: täglich/monatlich/jährlich, Reset zur Periodengrenze. Wer einen
Heizperioden-Zähler (Oktober–April) braucht, in `hph_efficiency.yaml`:

```yaml
hph_thermal_heating_season:
  source: sensor.hph_thermal_energy
  cycle: yearly
  offset: { months: 9 }   # Start Oktober
```

Analog für `electrical_*` und einen JAZ-Heizperioden-Sensor.
