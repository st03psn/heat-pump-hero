# HeishaHub

🌐 **Sprache:** [English](README.md) · Deutsch (diese Datei)


> Universelles Home-Assistant-Paket für Panasonic-Aquarea-Wärmepumpen mit
> Heishamon — Dashboard, Auswertung, Langzeit-Effizienz.

[![Validate](https://github.com/st03psn/heishahub/actions/workflows/validate.yml/badge.svg)](https://github.com/st03psn/heishahub/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

HeishaHub bündelt das, was bisher fehlt: ein importierbares Dashboard im Layout
des Heishamon-Web-UIs, Service-Cloud-ähnliche Auswertegraphen, ein Anlagen-
Schema mit Live-Hotspots und sauber gerechnete Effizienz-Kennzahlen
(JAZ / MAZ / TAZ / COP) — auch über mehrere Jahre.

## Status

🚧 **Pre-alpha (v0.1)** — Skelett mit erster funktionsfähiger HK1-Übersicht,
Live-COP und Basis-Graphen. Bubble-Schema, Grafana-Boards und Auto-Setup-
Blueprint folgen iterativ.

## Features (v0.1 → roadmap)

**Visualisierung & Status**
- ✅ Status-Dashboard (Übersicht, Heishamon-Web-UI-Layout)
- ✅ Live-COP & thermische/elektrische Energie
- ✅ Universal: HK2/DHW/Puffer/Solar/Pool optional, Auto-Hide
- ✅ Externe Sensoren (Shelly, WMZ) per UI-Dropdown
- 🟡 Service-Cloud-Stil-Graphen (ApexCharts) — Basis vorhanden, Feinschliff folgt
- 🟡 Anlagen-Schema (Bubble-Card + SVG) — Platzhalter
- 🟡 JAZ/MAZ/TAZ + Energy-Dashboard-Integration

**Takt-Analyse & Optimierung**
- ✅ Zyklus-Tracking (Starts/h, Laufzeiten, Pausen)
- ✅ Short-Cycle-Erkennung mit konfigurierbarer Schwelle
- ✅ Datengetriebener **Advisor** mit Klartext-Empfehlungen:
  Taktung, Spreizung VL/RL, Defrost-Verhalten, Heizkurve/Heizstab,
  DHW-Lauflänge — Sammel-Ampel im Dashboard
- ✅ **Steuerungs-Strategien (HeishaMoNR-Parität)**: CCC (Compressor Cycle
  Control), SoftStart, Solar-DHW-Boost, Nacht-Quiet-Mode — alle als
  HA-Automations, einzeln ein-/ausschaltbar, Master-Schalter

**Langzeit & Export**
- ⏳ Grafana-Boards für Mehrjahres-Effizienz
- ⏳ Setup-Blueprint für Ein-Klick-Deploy

## Voraussetzungen

- Home Assistant 2025.4 oder neuer
- Heishamon-Hardware (Egyras/IgorYbema-Firmware) am MQTT-Broker
  (Default-Topic-Prefix `panasonic_heat_pump`)
- HACS installiert

## Schnellinstallation

1. **HACS-Custom-Repository hinzufügen**
   - HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/st03psn/heishahub`
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
   `dashboards/heishahub.yaml` einfügen.

5. **Externe Sensoren** (optional) — Settings → Devices & Services → Helpers:
   `heishahub_shelly_entity` und `heishahub_wmz_entity` mit Entity-IDs füllen.
   Siehe [docs/external_sensors.md](docs/external_sensors.md).

Ausführliche Anleitung: [docs/installation.md](docs/installation.md).

## Architektur

```
  Heishamon ─┐
             ├─MQTT─▶ kamaradclimber → HA-Entities
  Shelly ────┤                        │
  WMZ ───────┘                        ├─▶ heishahub-Packages (Templates)
                                      │     ├─ COP / JAZ / MAZ / TAZ
                                      │     └─ Energie thermisch/elektrisch
                                      ├─▶ HA Recorder + LTS ─▶ Lovelace
                                      └─▶ HA Energy-Dashboard
                                      ↓
                                 InfluxDB ─▶ Grafana (Mehrjahres-JAZ/MAZ)
```

## Projektname & Bezug

**HeishaHub** — Hub für alles rund um Heishamon: Dashboard + Steuerung +
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
