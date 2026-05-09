# Heat Pump Hero

🌐 **Sprache:** [English](README.md) · Deutsch (diese Datei)


> Universelles Home-Assistant-Paket für Panasonic-Aquarea-Wärmepumpen mit
> Heishamon — Dashboard, Auswertung, Langzeit-Effizienz.

[![Validate](https://github.com/st03psn/heat-pump-hero/actions/workflows/validate.yml/badge.svg)](https://github.com/st03psn/heat-pump-hero/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Heat Pump Hero bündelt das, was bisher fehlt: ein importierbares Dashboard im Layout
des Heishamon-Web-UIs, Service-Cloud-ähnliche Auswertegraphen, ein Anlagen-
Schema mit Live-Hotspots und sauber gerechnete Effizienz-Kennzahlen
(JAZ / MAZ / TAZ / COP) — auch über mehrere Jahre.

## Status

🟢 **v0.6 — beta** — umbenannt zu Heat Pump Hero. Neu: Analyse-Modul
(L1 statistische Beobachtung + L2 Regressions-Script), Installer mit
DB-Auswahl + Prereq-Check. Siehe [CHANGELOG.md](CHANGELOG.md).

## Features

**Diagnose & Hersteller-Support** _(neu in v0.4)_
- ✅ Panasonic-Fehlercode-Analyse: 30+ H/F-Codes mit Klartext und Schweregrad,
  modellspezifische Hinweise (J-H23, R32/R290-H99, J/K-H62 Falschalarme)
- ✅ Wiederholungs-Erkennung (gleicher Code N× im 5-Event-Ringpuffer)
- ✅ Persistent notification bei Fehler, automatisch entfernt nach Klärung
- ✅ Hersteller-Preset-Selector — füllt alle 17 Source-Helper auf einen Klick:
  Heishamon / Daikin / MELCloud / Vaillant / Stiebel / generic
- ✅ Wärmepumpen-Modell-Selector — Panasonic J / K / L / T-CAP / **M (R290)**
  + andere — setzt Verdichter min/max Hz, Min-Volumenstrom, Max-Vorlauf-T° automatisch
- ✅ Wasserdruck-Trend-Advisor (langsame Leckage)

**Visualisierung**
- ✅ 7-View-Dashboard: Übersicht, Schema, Auswertung, Effizienz, Optimierung, Mobile, Konfiguration
- ✅ Bubble-Card-SVG-Schema mit Live-Hotspots, 4 Varianten — Auto-Detection
- ✅ ApexCharts: Temperaturen, Verdichter, COP, Heatmap (Tag × Stunde), Außen-T° vs. COP
- ✅ Eigene Mobile-Ansicht (single column)

**Effizienz**
- ✅ Live-COP (Defrost-maskiert), tägliche/monatliche/jährliche COP, JAZ
- ✅ Tarif-Splits (Heizen / DHW / Kühlen)
- ✅ Periodvergleich vs. Vormonat / Vorjahr in % mit Trend-Headlines
- ✅ HA-Energy-Dashboard via `*_active`-Energiesensoren

**Universalität (Source-Adapter)**
- ✅ Jede Entity-ID per UI änderbar — Wärmepumpe oder Zähler tauschen ohne YAML
- ✅ 3 Thermal-Modi: `calculated` / `external_power` / `external_energy` (kWh-Zähler)
- ✅ 3 Elektrik-Modi: `heat_pump_internal` / `external_power` / `external_energy`

**Takt-Analyse & Advisor**
- ✅ Zyklus-Tracking, Short-Cycle-Erkennung, Auto-Heizgrenze
- ✅ Datengetriebener Advisor (8 Regeln) mit Klartext-Empfehlungen
- ✅ Steuerungs-Strategien (CCC, SoftStart, Solar-DHW, Quiet-Mode) — Master-Schalter aus per Default

**Langzeit**
- ✅ Grafana: Übersicht + Mehrjahres-JAZ/MAZ mit echten Flux-Queries
- ✅ Telegraf MQTT → InfluxDB Bridge-Config

## Voraussetzungen

- Home Assistant **2024.4** oder neuer
- Heishamon-Hardware (Egyras/IgorYbema-Firmware) am MQTT-Broker
  (Default-Topic-Prefix `panasonic_heat_pump`)
- HACS installiert

## Schnellinstallation

1. **HACS-Custom-Repository hinzufügen**
   - HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/st03psn/heat-pump-hero`
   - Kategorie: *Lovelace* (zunächst, bis HACS Mixed-Content unterstützt)

2. **Abhängigkeiten installieren** (HACS-Suche, Reihenfolge egal):
   - kamaradclimber Heishamon-HomeAssistant (Integration)
   - apexcharts-card, bubble-card, mushroom, button-card,
     auto-entities, card-mod (Plugins)

3. **Packages aktivieren** — in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
   und den Inhalt von `packages/` aus diesem Repo nach `<config>/packages/`
   kopieren (manuell oder via `scripts/install.sh`).

4. **Dashboard hinzufügen** — Settings → Dashboards → Add → From YAML →
   `dashboards/hph.yaml` einfügen.

5. **Externe Sensoren** (optional) — Settings → Devices & Services → Helpers:
   `hph_shelly_entity` und `hph_wmz_entity` mit Entity-IDs füllen.
   Siehe [docs/external_sensors.md](docs/external_sensors.md).

Ausführliche Anleitung: [docs/installation.md](docs/installation.md).

## Architektur

```
  Heishamon ─┐
             ├─MQTT─▶ kamaradclimber → HA-Entities
  Shelly ────┤                        │
  WMZ ───────┘                        ├─▶ hph-Packages (Templates)
                                      │     ├─ COP / JAZ / MAZ / TAZ
                                      │     └─ Energie thermisch/elektrisch
                                      ├─▶ HA Recorder + LTS ─▶ Lovelace
                                      └─▶ HA Energy-Dashboard
                                      ↓
                                 InfluxDB ─▶ Grafana (Mehrjahres-JAZ/MAZ)
```

## Projektname & Bezug

**Heat Pump Hero** — Hub für alles rund um Heishamon: Dashboard + Steuerung +
Statistik in einem Paket.

## Mitwirken

Issues und PRs willkommen.

- [CLAUDE.md](CLAUDE.md) — Architektur und Konventionen
- [docs/installation.md](docs/installation.md) — Schritt-für-Schritt-Setup
- [docs/external_sensors.md](docs/external_sensors.md) — Shelly / WMZ einbinden
- [docs/optimization.md](docs/optimization.md) — Takt-Analyse, Advisor, Control
- [docs/tweaking.md](docs/tweaking.md) — Power-User-Anpassungen
- [docs/roadmap.md](docs/roadmap.md) — Was kommt noch

## Lizenz

MIT — siehe [LICENSE](LICENSE).

## Verwandte Projekte

- [Egyras/HeishaMon](https://github.com/Egyras/HeishaMon) — Firmware
- [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant) — HA-Integration (Pflicht-Dependency)
- [edterbak/HeishaMoNR](https://github.com/edterbak/HeishaMoNR) — Node-Red-Variante (kann parallel laufen)
