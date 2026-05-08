# Externe Sensoren

🌐 [English](../external_sensors.md) · Deutsch (diese Datei)


Heishamon liefert eine **Schätzung** der elektrischen Aufnahme und berechnet
die thermische Leistung aus internen Temperatursensoren — beides mit
Toleranzen von 10–20 %. Für belastbare JAZ/MAZ-Werte sind echte
Strommessgeräte und ggf. ein Wärmemengenzähler nötig.

HeishaHub kann beide Quellen — intern und extern — gleichzeitig vorhalten und
die aktive Quelle per Dropdown umschalten, ohne YAML zu editieren.

## Stromzähler — Shelly

### Shelly Pro 3EM (3-Phasen)

1. Shelly in HA einbinden (Shelly-Integration aus HACS oder MQTT).
2. Es entstehen u. a. `sensor.shellypro3em_<id>_total_active_power` (W) und
   `sensor.shellypro3em_<id>_total_energy` (kWh).
3. *Settings → Devices & Services → Helpers* öffnen, `heishahub_shelly_entity`
   bearbeiten, dort den **Power-Sensor** (W) eintragen, z. B.
   `sensor.shellypro3em_xxx_total_active_power`.
4. Im Dashboard *Konfiguration → Quellen-Auswahl*:
   `Elektrische Quelle` auf `external_shelly` umstellen.

### Shelly 1PM / EM (Einphasig)

Genauso — Entity-ID des Power-Sensors in `heishahub_shelly_entity`.

## Wärmemengenzähler — MQTT

Variante 1: **Auslesen über M-Bus-Gateway** (z. B. Weidmann *amber*,
Lobaro *MBus2MQTT*) → Topic-Beispiel:

```
mbus/heatmeter1/energy_kwh   → 12345.67
mbus/heatmeter1/power_w      → 4200
mbus/heatmeter1/flow_lpm     → 12.5
```

In HA via `mqtt sensor`:

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

Dann in den Helpers eintragen:
- `heishahub_wmz_entity`        → `sensor.wmz_energy`
- `heishahub_wmz_power_entity`  → `sensor.wmz_power`

Quelle umstellen: *Konfiguration → Quellen-Auswahl* →
`Thermische Quelle` = `external_wmz`.

Variante 2: **Direkter Pulse-Counter** an Shelly-Eingang oder ESPHome.

## Quellen-Wechsel und Historie

Wechselt man die Quelle, **bleiben** alle bisherigen Werte in der Historie
erhalten — die `utility_meter`-Zähler werden nicht zurückgesetzt. Ab dem
Wechselzeitpunkt rechnen die Energie-Integrale mit der neuen Quelle weiter,
JAZ/MAZ entsprechend.

Bei einem Quellenwechsel im laufenden Monat ist die MAZ entsprechend
gemischt — am sinnvollsten Wechsel zum Monatsersten.

## Validierung nach Einbindung

Nach dem Wechsel auf externe Quellen:

1. *Developer Tools → States* → `sensor.heishahub_electrical_power_active`
   prüfen → muss in W mit deinem Shelly-Sensor identisch sein.
2. `sensor.heishahub_thermal_power_active` muss plausibel sein
   (5–15 kW im Heizbetrieb bei 7 °C Außentemperatur).
3. `sensor.heishahub_cop_live` muss zwischen 2.0 und 5.0 liegen.
4. Nach 24 h: `sensor.heishahub_cop_daily` zeigt Tageswert.
