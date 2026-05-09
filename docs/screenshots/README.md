# Screenshots

This directory holds dashboard screenshots referenced from the main
README and docs. The screenshots are taken from a live HA install — until
the first reference install is up and running, only placeholders live here.

## Expected files (referenced from README.md)

| File | View / Source | Status |
|---|---|---|
| `overview.png`            | Dashboard view 1 — Overview        | placeholder |
| `schematic_hk1.png`       | Dashboard view 2 — Schematic (HK1) | placeholder |
| `schematic_hk1_dhw.png`   | Dashboard view 2 — Schematic (HK1+DHW) | placeholder |
| `analysis.png`            | Dashboard view 3 — Analysis (Apex graphs + heatmap) | placeholder |
| `efficiency.png`          | Dashboard view 4 — Efficiency (KPIs, comparisons, mode-split) | placeholder |
| `optimization.png`        | Dashboard view 5 — Optimization (advisor) | placeholder |
| `mobile.png`              | Dashboard view 6 — Mobile           | placeholder |
| `grafana_overview.png`    | Grafana — overview.json             | placeholder |
| `grafana_efficiency.png`  | Grafana — efficiency_jaz_maz.json   | placeholder |

## How to capture

1. Install Heat Pump Hero on a real HA instance (see [installation.md](../installation.md)).
2. Wait for at least 24 h of data so the live values are populated.
3. Use HA's *Settings → System → Logs* take-screenshot helper, or browser
   screenshot tools (PNG, 1600×900 typical).
4. Crop / resize to 1280px width, save as PNG.
5. PR the new images into this directory. Update `README.md` if a new
   filename is needed.

## Placeholder format

The placeholder SVGs in this directory mirror the layout but contain the
text "screenshot pending — install required". They're rendered the same
as PNGs in markdown, so the README looks the same once swapped.
