# Optimierung — Takt-Analyse, Advisor, Steuerung

## Konzept

Eine Wärmepumpe arbeitet am effizientesten, wenn sie **lange, gleichmäßig**
läuft, **selten** taktet und mit **niedriger Vorlauftemperatur** auskommt.
HeishaHub liefert drei Werkzeuge, um genau das zu erreichen:

1. **Takt-Analyse** — misst Zyklen, Laufzeiten, Pausen.
2. **Advisor** — wertet diese Daten aus und gibt Klartext-Empfehlungen.
3. **Control** — optionale Automations, die typische Optimierungs-Strategien
   aus HeishaMoNR (CCC, SoftStart, Solar-DHW) als HA-Automations umsetzen.

## Takt-Analyse

Sensoren in `packages/heishahub_cycles.yaml`:

| Sensor | Bedeutung |
|---|---|
| `counter.heishahub_cycles_today` | Anzahl Verdichter-Starts heute |
| `counter.heishahub_short_cycles_today` | Davon kürzer als Schwelle (Default 10 min) |
| `sensor.heishahub_short_cycle_ratio` | Anteil Short-Cycles (%) |
| `sensor.heishahub_cycles_per_hour` | Starts pro Stunde (gleitend) |
| `sensor.heishahub_avg_cycle_duration_24h` | Durchschnittliche Laufzeit |
| `input_number.heishahub_cycle_last_duration_min` | Letzter Lauf (min) |
| `input_number.heishahub_cycle_last_pause_min` | Letzte Pause (min) |

**Was ist „normal"?**
- Übergangszeit (5–10 °C außen): 4–8 Starts/Tag, Laufzeit 60–120 min
- Tiefwinter (< 0 °C): 1–3 Starts/Tag, Dauerlauf bis 24 h
- DHW: 1–3 Starts/Tag, je 20–45 min

Mehr als ~12 Starts/Tag oder Short-Cycle-Quote > 25 % deutet auf zu enges
Wasservolumen, zu steile Heizkurve oder hydraulische Probleme.

## Advisor

`packages/heishahub_advisor.yaml`. Jeder Advisor-Sensor hat:

- `state ∈ { ok, warn, critical, info }`
- `attributes.message` — Erklärung in Klartext
- `attributes.metric` — Diagnose-Wert

**Aktuelle Regeln (v0.1):**

| Sensor | Prüft | Empfehlung |
|---|---|---|
| `advisor_short_cycle` | Short-Cycle-Quote vs. Schwelle | Heizkurve, Hysterese, Puffer |
| `advisor_spread` | Vorlauf-Rücklauf-Spreizung gegen Soll-K | Pumpendrehzahl |
| `advisor_defrost` | Defrost bei Außentemp > 7 °C | Verdampfer prüfen |
| `advisor_heat_curve` | E-Heizstab an bei Außentemp > -7 °C | Heizkurve am kalten Ende anheben |
| `advisor_dhw_runtime` | DHW-Lauf < 20 min | Hysterese / Anti-Legionellen |
| `advisor_summary` | Sammel-Ampel | Gesamtstatus |

**Schwellen anpassen** in *Optimierung → Advisor-Schwellen*:
- `advisor_short_cycle_warn_pct` (Default 25 %)
- `advisor_short_cycle_crit_pct` (Default 50 %)
- `advisor_dt_target_k` (Default 5 K)
- `advisor_dhw_min_runtime_min` (Default 20 min)

## Control — Steuerungs-Strategien

`packages/heishahub_control.yaml`. **Standard: alles AUS.** Aktivierung über
zwei Schalter:

1. `input_boolean.heishahub_ctrl_master` — Globaler Schalter
2. Einzelne Strategien — siehe unten

### Compressor Cycle Control (CCC)

**Problem**: WP schaltet nach kurzer Pause sofort wieder ein → kurze Zyklen,
hoher Verschleiß, schlechter COP.

**HeishaHub-Lösung**: Wenn die letzte Pause kürzer als
`ctrl_ccc_min_pause_min` (Default 15 min) war, wird nach dem Neustart der
Quiet-Mode 3 für 5 Minuten aktiviert — das reduziert die maximale
Frequenz und gibt der Anlage Zeit zur Modulation, statt voll hochzufahren
und früh wieder abzuschalten.

**Aktivieren**: `ctrl_master = on`, `ctrl_ccc = on`, ggf. Pause-Schwelle
anpassen.

### SoftStart

**Problem**: Anfahrspitzen bei tiefen Außentemperaturen verursachen
hohen Strom-Peak und ggf. Ansprechen des EVU-Schutzes.

**HeishaHub-Lösung**: Beim Verdichter-Start Quiet-Mode 2 für 10 Minuten →
sanfter Frequenz-Hochlauf.

### Solar-DHW-Boost

**Problem**: PV-Überschuss verpufft, während die WP später teuer DHW macht.

**HeishaHub-Lösung**: Wenn der PV-Überschuss-Sensor (Entity-ID in
`ctrl_pv_surplus_entity` eintragen) länger als 5 Min über
`ctrl_solar_pv_threshold_w` (Default 1500 W) liegt **und** der Tank noch
nicht voll ist, wird `force_dhw` ausgelöst.

**Voraussetzungen**:
- PV-Überschuss-Sensor muss existieren (Eigenverbrauch − Bezug, in W)
- Tank-Temperatur-Sensor verfügbar

### Nacht-Quiet-Mode

22:00–06:00 automatisch Quiet-Mode 3 — geräuscharm, mit Komfort-Einbuße in
Tiefkälte. Nur einschalten, wenn Anlage vor dem Schlafzimmer und keine
Heizlast-Probleme zu erwarten sind.

## Workflow für saubere Optimierung

1. **Beobachten** (1–2 Wochen): Standard-Heizkurve, alles auf default.
   Advisor sammelt Daten.
2. **Diagnose**: Sammel-Ampel und einzelne Advisor-Sensoren prüfen.
   Warnungen lesen, Mess-Werte (`metric`-Attribut) notieren.
3. **Einzelne Stellschraube** ändern (z. B. Heizkurve um 1 °C senken),
   1–2 Tage warten, Effekt im Advisor und in den Takt-Statistiken
   beobachten.
4. **Steuer-Strategien** (CCC, SoftStart) erst zuschalten, wenn die
   manuelle Heizkurven-Optimierung am Limit ist.
5. **Niemals alles auf einmal** ändern — Effekte werden dann nicht
   zuordenbar.

## Eigene Advisor-Regeln hinzufügen

Power-User: in `packages/heishahub_advisor.yaml` einen neuen
`template.sensor`-Block ergänzen, der gleiches Schema einhält
(`state`, `attributes.message`, `attributes.metric`). Anschließend in
`heishahub_advisor_summary` hinzufügen, damit die Sammel-Ampel den neuen
Sensor mit auswertet.

PRs für allgemein nützliche Regeln willkommen — siehe
[CLAUDE.md](../CLAUDE.md) für Designprinzipien.
