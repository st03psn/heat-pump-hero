# Heat Pump Hero

> Universeel Home Assistant-pakket voor Panasonic Aquarea-warmtepompen met
> Heishamon — dashboard, statistieken, optimalisatie-adviseur, regelautomatiseringen.

🌐 **Talen:** [English](README.md) · [Deutsch](README.de.md) · Nederlands (dit bestand)

[![Validate](https://github.com/st03psn/heat-pump-hero/actions/workflows/validate.yml/badge.svg)](https://github.com/st03psn/heat-pump-hero/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Heat Pump Hero bundelt wat tot nu toe ontbrak: een importeerbaar Home Assistant
dashboard met de lay-out van de Heishamon-webinterface, Service-Cloud-achtige
analytische grafieken, een installatieschema met live-hotspots en degelijke
efficiëntiemetrieken (SCOP / maand / dag / live COP) — inclusief vergelijking
over meerdere jaren.

## Status

🟢 **v0.6 — beta** — hernoemd naar Heat Pump Hero. Toegevoegd: analysemodule
(L1 statistische observatie + L2 regressie-script), installer met
DB-keuze + prereq-check. Zie [CHANGELOG.md](CHANGELOG.md).

## Functies

**Visualisatie**
- 7-view dashboard: Overzicht, Schema, Analyse, Efficiëntie, Optimalisatie, Mobiel, Configuratie
- Bubble-Card SVG-schema met live-hotspots, 4 varianten — auto-detectie
- ApexCharts: temperaturen, compressor, COP, heatmap (dag × uur), buitentemp ↔ COP scatter
- Eigen mobiele weergave (één kolom)

**Tellers & efficiëntie**
- Live COP (defrost-gemaskerd), dagelijks / maandelijks / jaarlijks COP, SCOP
- Tarief-splitsing in utility_meter (verwarming / SWW / koeling apart)
- Periodevergelijkingen: t.o.v. vorige maand / vorig jaar, in % met trend-headlines
- HA Energy-Dashboard-integratie via `*_active` energiesensoren

**Source-adapter (universeel)**
- Elke entity-ID is via UI in te stellen — wissel warmtepomp of meter
  zonder YAML te bewerken
- 3 thermische bronmodi: `calculated` / `external_power` / `external_energy`
  (kWh-meter omzeilt integratie)
- 3 elektrische bronmodi: `heat_pump_internal` / `external_power` / `external_energy`
- Standaardwaarden komen overeen met Heishamon out-of-the-box; zone 2 / SWW /
  buffer / zonneboiler / zwembad optioneel met auto-verberg

**Cyclusanalyse & adviseur**
- Cyclustracking (starts/uur, looptijden, pauzes)
- Korte-cyclusdetectie met instelbare drempel
- Auto-gedetecteerde stooklijngrens (rollend gemiddelde van buitentemp
  aan einde van compressorlopen ≥ 30 min)
- Datagedreven adviseur met begrijpelijke aanbevelingen: cycli,
  spreiding aanvoer/retour, ontdooien, stooklijn / hulpverwarming,
  SWW-looptijd, stooklijngrens — overall traffic-light tegel

**Regelstrategieën (HeishaMoNR-pariteit)**
- CCC, SoftStart, Solar-DHW boost, Quiet-Mode 's nachts —
  individueel toggle-baar, master-switch vereist, default uit

**Lange termijn & export**
- Grafana boards: overzicht + meerjarig SCOP / MAZ met echte Flux-queries
- Telegraf MQTT → InfluxDB bridge config
- Setup-blueprint en CLI-installer

## Vereisten

- Home Assistant **2024.4** of nieuwer
- Heishamon-hardware (Egyras / IgorYbema firmware) verbonden met een MQTT-broker
  (standaard topic-prefix: `panasonic_heat_pump`)
- HACS geïnstalleerd

## Snelle installatie

1. **Voeg HACS custom repository toe**
   - HACS → Integraties → ⋮ → Custom repositories
   - URL: `https://github.com/st03psn/heat-pump-hero`
   - Categorie: Plugin
2. **Installeer de afhankelijkheden** (HACS-frontend-cards):
   apexcharts-card, Bubble-Card, lovelace-mushroom, button-card,
   auto-entities, card-mod
3. **Voer scripts/install.sh uit** (of kopieer handmatig — zie
   [docs/installation.md](docs/installation.md))
4. **Start HA opnieuw**, en voer de "Heat Pump Hero Setup" blueprint uit
5. **Voeg dashboard toe**: Instellingen → Dashboards → Toevoegen → Vanuit YAML →
   `hph/dashboard.yaml`

## Documentatie

- [Installatie](docs/installation.md) — Engels (NL-vertaling volgt op verzoek)
- [Externe sensoren](docs/external_sensors.md) — bron-adapter, Shelly, WMZ
- [Optimalisatie](docs/optimization.md) — adviseur, regeling, koexistentie met HeishaMoNR
- [Tweaking](docs/tweaking.md) — voor power-users
- [Roadmap](docs/roadmap.md)

## Bijdragen

Issues met concrete use-cases zeer welkom. Lees voor een PR de
ontwerpprincipes in [CLAUDE.md](CLAUDE.md), met name de universaliteits-,
adviseur- en source-adapter-conventies.

## Licentie

[MIT](LICENSE)
