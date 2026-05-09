# CLAUDE.md — Heat Pump Hero Projektkontext

🌐 [English](CLAUDE.md) · Deutsch (diese Datei)


Dieser Leitfaden ist für KI-Assistenz (Claude Code) und neue menschliche
Mitwirkende. Er erklärt das Projekt in 5 Minuten.

## Was ist Heat Pump Hero?

Heat Pump Hero ist ein **Bündel-Paket** für Home Assistant, das auf einer
Heishamon-Anlage (Panasonic Aquarea) ein vollständiges Dashboard plus
Auswertung deployt. Es ersetzt **keine** Integration — es **kombiniert**
existierende Bausteine zu einem benutzbaren Ganzen:

- Entities kommen von [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- Heat Pump Hero liefert: HA-Packages (Template-Sensoren, COP/JAZ-Berechnung),
  Lovelace-Dashboard-YAML, Bubble-Card-SVG-Schema, Grafana-Boards,
  Setup-Blueprint.

## Designprinzipien

1. **Universalität.** Jedes Template ist `availability:`-geschützt. HK1-only
   muss genauso laufen wie Vollausstattung mit HK2 + DHW + Puffer + Solar +
   Pool. Keine `unknown`-Sensoren.
2. **Plug-and-Play.** Standardnutzer installiert über HACS + ein Setup-
   Blueprint; kein YAML-Editieren erforderlich. Power-User können trotzdem
   alles direkt in YAML anpassen.
3. **Externe Sensoren erstklassig.** Shelly-Steckdosen und MQTT-WMZ sind
   keine Nachträge, sondern als Quellen gleichberechtigt mit den internen
   Heishamon-Schätzungen — wählbar per `input_select`.
4. **Langzeit-fest.** JAZ/MAZ über mehrere Jahre via `utility_meter` + LTS;
   InfluxDB-Spiegelung für Grafana-Mehrjahres-Vergleich.
5. **Lesbares YAML.** Keine generierten Templates, keine Macro-Magie —
   ein menschlicher Reviewer muss Dashboard-YAML in 5 Min nachvollziehen.

## Repo-Layout

| Pfad | Zweck |
|---|---|
| `packages/hph_core.yaml` | Live-Sensoren (thermische Leistung, Mode-Mapping, Defrost, Compressor-Run). |
| `packages/hph_external.yaml` | UI-Helper für externe Sensoren (Shelly/WMZ) + Active-Power-Auswahl. |
| `packages/hph_efficiency.yaml` | Energie-Integrale, utility_meter, COP/TAZ/MAZ/JAZ. |
| `packages/hph_cycles.yaml` | Takt-Analyse: Start/Stop-Events, Laufzeit/Pause, Counter, Short-Cycle-Erkennung. |
| `packages/hph_advisor.yaml` | Datengetriebene Optimierungs-Empfehlungen mit Klartext-Messages und Sammel-Ampel. |
| `packages/hph_control.yaml` | Optionale Steuer-Automations (CCC, SoftStart, Solar-DHW, Quiet-Nacht) — Master-Schalter aus by default. |
| `dashboards/hph.yaml` | Lovelace-Dashboard-YAML, Storage- oder YAML-Mode. |
| `dashboards/assets/*.svg` | Anlagen-Schema-Vorlagen (Bubble-Card-Hintergrund). |
| `blueprints/hph_setup.yaml` | Skript-Blueprint, das Helper anlegt + Dashboard registriert. |
| `scripts/install.sh` | Optionaler Bash-Installer für SSH-Nutzer. |
| `grafana/*.json` | Grafana-Dashboards (Import-fertig). |
| `grafana/telegraf_mqtt.conf` | Telegraf-Config für MQTT→InfluxDB. |
| `docs/` | Installations- und Tweak-Dokumentation. |
| `tests/` | HA-CI-Smoketests. |
| `.github/workflows/` | YAML/JSON-Validierung, Release-Automatisierung. |

## Naming-Konventionen

- **Entities** aus Heat Pump Hero: Prefix `hph_` (z. B. `sensor.hph_scop`).
- **Quell-Entities** (kamaradclimber): Prefix `panasonic_heat_pump_` —
  niemals direkt im Dashboard verwenden, immer über Template-Wrapper, damit
  Topic-Prefix-Wechsel nur an einer Stelle nötig ist.
- **Helper**: alle in `input_*.hph_*`.
- **Dashboard-Views**: `overview`, `schema`, `analysis`, `efficiency`, `optimization`, `config`.

## Advisor-Designprinzipien

Der Advisor liefert **Empfehlungen, keine Befehle**. Jeder Sensor:
- `state ∈ { ok, warn, critical, info }` — maschinenlesbar
- `attributes.message` — Deutsche Klartext-Erklärung mit konkreter
  Handlungsoption
- `attributes.metric` — der relevante Messwert für die Diagnose

Schwellen sind **immer** über `input_number.hph_advisor_*`
nutzerseitig anpassbar. Keine harten Magic-Numbers in Templates — wenn ein
Wert tunbar sein sollte, gehört er als Helper exposed.

Neue Advisor-Sensoren folgen demselben Schema und werden zur
`hph_advisor_summary`-Aggregation hinzugefügt.

## Control-Designprinzipien

Steuer-Automations (CCC, SoftStart etc.) sind **immer**:
1. Standardmäßig AUS (`initial: false`)
2. Hinter dem Master-Schalter `input_boolean.hph_ctrl_master`
3. Einzeln über `input_boolean.hph_ctrl_<name>` aktivierbar
4. Mit Tunables als `input_number.hph_ctrl_<name>_*`

Begründung: Falsch konfigurierte Steuer-Automations können die WP
schädigen oder den Komfort beeinträchtigen. Aktivierung muss bewusst sein.

## Heishamon-Topic-Prefix

Default ist `panasonic_heat_pump`. Wer einen anderen Prefix nutzt, ändert ihn
**ausschließlich** in `packages/hph_core.yaml` über die Variable
`!secret hph_topic_prefix` (nicht im Dashboard, nicht in Templates
verstreut).

## Externe-Sensoren-Mechanik

`packages/hph_external.yaml` definiert `input_text`-Helper für die
Quell-Entity-IDs. Templates lesen indirekt:

```yaml
{{ states(states('input_text.hph_shelly_entity')) | float(0) }}
```

Damit kann ein Nutzer in der HA-UI seinen Shelly-Power-Sensor auswählen, ohne
YAML zu editieren. `input_select.hph_electrical_source` schaltet
zwischen `heishamon_internal` und `external_shelly` — die JAZ-Berechnung
wechselt entsprechend.

## COP/JAZ-Formeln

- **Thermische Leistung [W]**: `(Vorlauf − Rücklauf) × Volumenstrom_l/min × 4180 / 60`
- **Live-COP**: `thermische_Leistung / elektrische_Leistung`, **0** während
  Abtauung (sonst Werte → ∞ wegen Restzirkulation).
- **JAZ/MAZ/TAZ**: `utility_meter`-Zähler liefern Energie-Summen pro Periode;
  Effizienz = `thermal_kWh[period] / electrical_kWh[period]`.
- **Tarif-Splits**: `utility_meter` mit Tarifen `heating`/`dhw`/`cooling`,
  Tarifumschaltung via Template auf `select.panasonic_heat_pump_main_operating_mode`.

## Koexistenz mit HeishaMoNR

Beide Systeme können gleichzeitig am MQTT-Broker hängen — schreibend darf nur
**eines**. Empfehlung in der Doku: HeishaMoNR steuert, Heat Pump Hero nur lesen
(deaktivierte `number.*`/`select.*` aus kamaradclimber). Für reine
Heat Pump Hero-Setups entfällt das.

## Releasing

- SemVer; Tags `v0.x.y`.
- `release.yml` baut Release-Notes aus Conventional-Commits.
- HACS zieht jeden Tag automatisch.

## Verwandte Konzepte / Vokabular

- **JAZ** — Jahresarbeitszahl (annual COP)
- **MAZ** — Monatsarbeitszahl
- **TAZ** — Tagesarbeitszahl
- **WMZ** — Wärmemengenzähler (heat meter)
- **HK1/HK2** — Heizkreis 1/2
- **DHW** — Domestic Hot Water (Trinkwarmwasser)
- **A2W** — Air-to-Water (Luft-Wasser-WP)
- **LTS** — Long-Term Statistics (HA-Recorder-Feature)
