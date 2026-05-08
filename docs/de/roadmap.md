# Roadmap

🌐 [English](../roadmap.md) · Deutsch (diese Datei)


## v0.1 — Skelett (jetzt)

- [x] Repo-Struktur, HACS-Manifest, MIT-Lizenz
- [x] Packages: core / external / efficiency / cycles / advisor / control
- [x] Dashboard mit 6 Views (Übersicht, Schema, Auswertung, Effizienz,
  Optimierung, Konfiguration)
- [x] Setup-Blueprint (Diagnose)
- [x] CLI-Installer `scripts/install.sh`
- [x] Grafana-Skeletons (overview, efficiency_jaz_maz)
- [x] Telegraf-MQTT-Bridge-Config
- [x] CI: yamllint, JSON-Validierung, HACS-Action
- [x] Docs: installation, external_sensors, optimization, tweaking, roadmap

## v0.2 — Erste echte Anwendung

- [ ] Bubble-Card-SVG-Schema mit Live-Hotspots (statt Markdown-Platzhalter)
- [ ] Schema-Varianten für HK1+DHW, HK1+HK2+DHW, +Puffer
- [ ] Topic-Prefix als zentrale Variable (`secrets.yaml`-Eintrag)
- [ ] Tarif-Splits in `utility_meter` (heating/dhw/cooling separat)
- [ ] HA-Energy-Dashboard-Integration als „Individual Devices"
- [ ] Mobile-optimiertes Dashboard-Layout
- [ ] Screenshots in `docs/screenshots/`

## v0.3 — Statistik & Langzeit

- [ ] Wochen-/Monats-/Jahres-Heatmap (Außentemp × Stunde × COP)
- [ ] Grafana-Dashboards mit echten Queries (heute Skelette)
- [ ] InfluxDB-Schema dokumentieren, Beispiel-Queries
- [ ] Heizgrenztemperatur automatisch ermitteln
- [ ] Vergleich Vorjahr ↔ aktuelles Jahr (Apex-Komparator)

## v0.4 — Advisor-Erweiterungen

- [ ] Heizkurven-Optimierungs-Vorschlag aus Daten
  (Vorlauf-Soll vs. Ist über Außentemperatur, lineare Regression)
- [ ] Pumpenkennlinien-Empfehlung (Spreizung-Histogramm)
- [ ] Wasserdruck-Trend-Erkennung (langsamer Druckverlust)
- [ ] Effizienz-Drift-Erkennung (JAZ Vorjahr vs. aktuell, witterungsbereinigt)
- [ ] DHW-Timing-Empfehlung (basierend auf Verbrauchsmuster)

## v0.5 — Control-Erweiterungen

- [ ] Adaptive Heizkurve (selbstlernend basierend auf Innenraum-Sensoren)
- [ ] Strompreis-gesteuerte DHW (Tibber/aWATTar-Integration)
- [ ] Anti-Legionellen-Programm konfigurierbar
- [ ] Wetter-Vorausschau (Heizen-Vorbereiten bei kommender Kälte)
- [ ] Estrich-Aufheiz-Programm (Bauphase)

## v1.0 — Stabil & dokumentiert

- [ ] Vollständige Testsuite (HA-CI mit Mock-MQTT)
- [ ] Mehrsprachigkeit (EN, NL — typische Heishamon-Communities)
- [ ] Video-Walkthrough
- [ ] Aufnahme in HACS-Default-Repository
- [ ] HK2 / Puffer / Solar / Pool vollständig getestet bei Beta-Nutzern

## Nicht geplant

- Eigene Python-Custom-Integration (kamaradclimber deckt Entities ab —
  Doppel-Arbeit vermeiden)
- Cloud-Funktionen (HeishaHub bleibt 100 % lokal)
- Steuerung ohne kamaradclimber-Integration (zu großer Abstraktions-
  Aufwand für wenig Mehrwert)

## Beitragen

Issues mit konkreten Use-Cases willkommen. Vor PRs: Designprinzipien in
[CLAUDE.md](../CLAUDE.md) lesen, besonders zu Universalität, Advisor-Schema
und Control-Schalter-Konvention.
