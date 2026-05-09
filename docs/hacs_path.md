# HACS path forward

This doc explains how HeatPump Hero can become **fully plug-and-play via
HACS** — and what's blocking that today.

## What HACS can ship

HACS only delivers files into specific directories:

| HACS category | Target | What we'd need |
|---|---|---|
| **Plugin** (current) | `<config>/www/community/hph/` | Frontend resources only — SVG assets, custom-card JS bundles |
| **Integration** | `<config>/custom_components/hph/` | A Python integration that registers entities, automations, and helpers programmatically |
| **Theme** | `<config>/themes/hph.yaml` | Styles only |

**Crucially, HACS cannot write to:**
- `<config>/packages/` — our YAML packages live here
- `<config>/blueprints/` — our setup blueprint lives here
- `<config>/configuration.yaml` — needs the `packages: !include_dir_named packages` line

That's why `scripts/install.sh` exists today: it does the file copying
HACS isn't allowed to do.

## What's needed for true plug-and-play

A **Python custom integration** at `custom_components/hph/` that:

1. **Registers all helpers** programmatically via `hass.helpers.entity_registry`
   — no `input_select` / `input_text` / `input_number` YAML needed
2. **Registers all template sensors** programmatically — replicates today's
   `packages/*.yaml` content as Python `SensorEntity` classes
3. **Auto-creates the dashboard** via `hass.data["lovelace"]["dashboards"]`
   — no `Settings → Dashboards → Add → From YAML` step
4. **Pre-flight check for missing frontend cards** — list which custom
   cards (apexcharts, mushroom, bubble-card, …) are missing and show
   actionable HACS install links in the Repairs panel
5. **Config flow** (`config_flow.py`) — UI wizard for first-run setup:
   - Detect Heishamon prefix
   - Optionally point at Daikin / Vaillant / Mitsubishi entities
   - Optionally configure external Shelly / WMZ
6. **Per-platform translations** — `translations/{en,de,nl}.json` so the
   UI respects HA's language setting automatically

## Effort estimate

- **Config flow + helper registration**: 1-2 days
- **Sensor migration from YAML to Python**: 3-4 days (most of the work
  is keeping the same logic in template form vs. CoordinatorEntity)
- **Dashboard auto-registration**: 0.5 day
- **Frontend dependency check**: 0.5 day
- **Translations infrastructure**: 0.5 day
- **HACS validation + listing in default repository**: 1 day

≈ 6-8 working days.

## What's possible today (without integration)

- ✅ HACS plugin install of frontend cards (handled separately by user)
- ✅ HACS plugin install of HeatPump Hero assets (SVGs, future icon set)
- ❌ Auto-install of frontend dependencies (apexcharts, mushroom, …) —
  HACS does not support this; only manual install via HACS UI
- ⚠️ Setup blueprint can post a notification listing what's missing,
  but cannot install or copy files

## Auto-install dependencies — definitive answer

**Today:** No, HACS does not support automatic install of dependent
plugins. The `info.md` lists them and users must click through HACS
manually.

**With our future integration:** We can use `homeassistant.helpers.issue_registry`
to raise repairs ("HeatPump Hero: ApexCharts not installed — click here to
open HACS"), but the actual install click still requires the user.

## Roadmap mapping

| Feature | Today | With Plugin only | With Integration |
|---|---|---|---|
| Install via HACS UI | ✅ | ✅ | ✅ |
| Install dashboard YAML | ❌ (manual) | ❌ (manual) | ✅ |
| Install packages | ❌ (install.sh) | ❌ (install.sh) | ✅ (no files needed) |
| UI-driven first-run setup | ⚠️ (blueprint) | ⚠️ (blueprint) | ✅ (config flow) |
| HA language follows automatically | ❌ | ❌ | ✅ (translations/) |
| Dependency check / repair flow | ❌ | ❌ | ✅ |
| Shareable config | ❌ | ❌ | ✅ (entity registry) |

## Decision

For v0.x: stay as **HACS plugin + install.sh**. The combination already
gives a working install in <10 minutes. Going to a full integration is
a v0.6 / v1.0 milestone — tracked in [roadmap.md](roadmap.md).
