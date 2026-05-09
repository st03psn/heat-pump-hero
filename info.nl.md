# HeishaHub

🌐 [English](info.md) · [Deutsch](info.de.md) · Nederlands (dit bestand)

Bundle-pakket voor **Heishamon** in Home Assistant: dashboard met de
lay-out van de Heishamon-webinterface, Service-Cloud-achtige analytische
grafieken, installatieschema en lange-termijn-efficiëntie (SCOP / maand /
dag / live COP) — universeel, plug-and-play, met optionele InfluxDB /
Grafana-integratie voor meerjarige vergelijking.

## Functies

- Overzichtsdashboard (Mushroom) met de stijl van de Heishamon-webinterface
- Installatieschema als Bubble-Card met SVG en live-hotspots, auto-detectie
- ApexCharts-analyse met meerassige ondersteuning, tijdreeks-picker,
  serie-toggle, COP-heatmap (dag × uur)
- SCOP / maandelijks / dagelijks / live COP voor verwarming, SWW, koeling
- Periodevergelijkingen: t.o.v. vorige maand / vorig jaar in %
- Externe sensoren (Shelly Pro 3EM / 1PM / EM, MQTT-warmtemeters) selecteerbaar
  via UI-dropdown — geen YAML-bewerking nodig
- Bron-adapter: andere warmtepomp / meter inwisselen zonder YAML
- Auto-verberg voor afwezige componenten (zone 2, SWW, buffer, zon, zwembad)
- Cyclusanalyse met korte-cyclusdetectie
- Datagedreven optimalisatie-adviseur met begrijpelijke aanbevelingen
- Auto-gedetecteerde stooklijngrens
- Regelstrategieën (CCC, SoftStart, Solar-DHW, Quiet-Mode 's nachts) — HA
  automatiseringen met master-switch, default uit
- Optioneel: Grafana boards voor meerjarige SCOP-vergelijking

## Vereisten

- Home Assistant **2024.4** of nieuwer
- Heishamon-hardware met MQTT-broker

## Installatie

Zie [docs/installation.md](docs/installation.md).

## Afhankelijkheden

- [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- [RomRider/apexcharts-card](https://github.com/RomRider/apexcharts-card)
- [Clooos/Bubble-Card](https://github.com/Clooos/Bubble-Card)
- [piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom)
- [custom-cards/button-card](https://github.com/custom-cards/button-card)
- [thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
- [thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)
