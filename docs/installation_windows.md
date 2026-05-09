# Installation on Windows — step by step

A complete walkthrough for Windows users who want to test HeatPump Hero
on their Home Assistant instance and remove it cleanly afterwards. No
prior Git or Linux experience required. Recorder history is preserved
across install / uninstall / reinstall, so you can experiment without
losing your sensor graphs.

## What you need first

- **Windows 10 or 11** with PowerShell (built-in, no install needed).
- **Home Assistant**, reachable from your PC via one of:
  - The **Samba share add-on** (most common, gives you
    `\\homeassistant\config`), or
  - A local Docker volume path (e.g. `D:\hassio\config`), or
  - SSH access to a remote Linux machine running HA.
- The **Heishamon integration** and the **HACS frontend cards** already
  installed. If not yet, follow Steps 1-2 of the standard
  [installation guide](installation.md) first — they're identical
  regardless of operating system.

## Where do files end up in Home Assistant?

This is what the installer copies into your HA `config` directory.
Nothing outside this list is touched.

| From this repo | Lands in your HA at | What it does |
|---|---|---|
| `packages\hph_*.yaml` (~12 files) | `<config>\packages\` | All sensors, automations, helpers |
| `dashboards\hph.yaml` | `<config>\hph\dashboard.yaml` | The dashboard YAML |
| `dashboards\assets\*.svg` | `<config>\www\hph\` | Schematic background images |
| `blueprints\hph_setup.yaml` | `<config>\blueprints\script\hph\` | Setup helper blueprint |
| `scripts\export_*.py`, `import_*.py`, `analyze_*.py` | `<config>\scripts\` | Optional Python helpers for export/import |

In addition, **one single line** is added to `<config>\configuration.yaml`
if it isn't already there:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

That's it. The installer **does not**:

- Touch your recorder database (state history of `sensor.hph_*` survives
  every install / uninstall cycle until your recorder retention window
  expires — default 10 days, recommended 30+).
- Touch Long-Term Statistics (Energy Dashboard graphs stay).
- Modify HACS integrations or frontend cards.
- Modify any other YAML files you have under `packages\`.

## Step 1 — Find your HA `config` path

Pick the variant that matches your setup, then test the path before
proceeding.

### Path A — HA OS / Supervised with Samba add-on

Most common. In HA: **Settings → Add-ons → Samba share** install and
start. Then in PowerShell:

```powershell
$HA = '\\homeassistant\config'
Test-Path "$HA\configuration.yaml"   # must print True
```

If `homeassistant` doesn't resolve, try the IP: `\\192.168.1.50\config`.

### Path B — HA Container (Docker) on this Windows PC

If the volume is mounted locally:

```powershell
$HA = 'D:\hassio\config'
Test-Path "$HA\configuration.yaml"   # must print True
```

### Path C — Remote Linux box via SSH

PowerShell on Windows 10/11 ships with `ssh.exe`/`scp.exe`. Test:

```powershell
ssh root@<ha-ip> "ls /config/configuration.yaml"
```

If you go with Path C, see the bash variants of the install / uninstall
commands at the bottom of each section.

## Step 2 — Get the HeatPump Hero repository

You need the contents of this repo somewhere on your Windows PC. Two
options:

**Option a — git clone** (recommended if you have Git for Windows):

```powershell
Set-Location D:\DEV
git clone https://github.com/st03psn/heat-pump-hero.git
Set-Location D:\DEV\heat-pump-hero
```

**Option b — ZIP download** (no Git needed):

1. Open https://github.com/st03psn/heat-pump-hero
2. Code → Download ZIP
3. Extract to e.g. `D:\DEV\heat-pump-hero\`
4. In PowerShell: `Set-Location D:\DEV\heat-pump-hero`

## Step 3 — Install (= copy files to HA)

If PowerShell refuses with *"Execution of scripts is disabled on this
system"*, allow it for this session only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then run the installer pointed at your HA path:

```powershell
# Path A
.\scripts\update.ps1 -HaConfig \\homeassistant\config

# Path B
.\scripts\update.ps1 -HaConfig D:\hassio\config
```

For Path C (remote Linux), copy and run the bash version:

```powershell
scp -r packages scripts dashboards blueprints root@<ha-ip>:/tmp/hph/
ssh root@<ha-ip> "bash /tmp/hph/scripts/update.sh /config"
```

The script prints exactly which files it copied. Same command is safe to
re-run anytime — it's idempotent and will overwrite only HeatPump Hero
files, never your other configuration.

## Step 4 — Activate in Home Assistant

In your HA web UI:

1. **Settings → Developer Tools → YAML → Check Configuration.**
   Must be **green**. If red: read the error, usually a typo in your
   own configuration.yaml; rerun the check after fixing.
2. **Settings → System → Restart Home Assistant.**
   A full restart is recommended on the first install (because new
   helpers, counters and input_text entities only register on restart).
   For later updates a YAML reload is often enough — see the script
   output.
3. **Settings → Developer Tools → States.**
   Filter for `hph_advisor_summary`. The entity must exist. If it does,
   HeatPump Hero is loaded correctly.

## Step 5 — Add the dashboard

1. **Settings → Dashboards → Add Dashboard → From YAML.**
2. Title: `HeatPump Hero` · Icon: `mdi:heat-pump` · URL path: `hph`.
3. After creation, edit the dashboard and set the YAML filename to
   `hph/dashboard.yaml`. (HA reads the file from `<config>\hph\`.)
4. The dashboard should now show seven views: Overview, Schematic,
   Analysis, Efficiency, Optimization, Programs, Mobile, Configuration.

## Step 6 — One-time setup

In the dashboard, open **Configuration → Vendor & model** and pick the
preset that matches your install:

- `panasonic_heishamon` — kamaradclimber's custom integration (the most
  common Heishamon path)
- `panasonic_heishamon_mqtt` — the bundled HeishaMon MQTT YAML packages
  (entities prefixed `aquarea_*`)
- Other vendors as listed.

A persistent notification will confirm that the source helpers were
auto-filled. The selector resets to `keep_current` after 2 seconds —
that's intentional.

## Step 7 — Uninstall when you're done testing

Always start with a dry run to see what would happen:

```powershell
.\scripts\uninstall.ps1 -HaConfig \\homeassistant\config -DryRun
```

If the output looks right, run it for real (with confirmation prompt):

```powershell
.\scripts\uninstall.ps1 -HaConfig \\homeassistant\config
```

Or skip the prompt:

```powershell
.\scripts\uninstall.ps1 -HaConfig \\homeassistant\config -Yes
```

Path C (Linux): `bash /tmp/hph/scripts/uninstall.sh /config --yes`

The uninstaller removes:

- All `<config>\packages\hph_*.yaml`
- `<config>\hph\` (dashboard YAML directory)
- `<config>\www\hph\` (SVG assets)
- `<config>\blueprints\script\hph\` (setup blueprint)
- The three Python helpers under `<config>\scripts\`
- The `packages: !include_dir_named packages` line in
  `configuration.yaml` — only if your `packages\` directory is empty
  afterwards (so other people's packages stay untouched).

The uninstaller leaves alone (by design):

- **Recorder DB / Long-Term Statistics** — `sensor.hph_*` history stays
  visible until your recorder retention window expires.
- **HACS integrations and frontend cards** — manage those via HACS.
- **`<config>\www\heishahub_exports\`** — your CSV/JSON exports if any.
- **The dashboard entry** in HA (Settings → Dashboards) — remove it
  manually if you want it gone.

After the uninstaller finishes:

1. **Settings → Developer Tools → YAML → Check Configuration** — must
   be green.
2. **Settings → System → Restart Home Assistant.**

## Step 8 — Reinstall later

Run Step 3 again — same command. Because the recorder database wasn't
touched, your previous `sensor.hph_*` graphs reappear seamlessly as long
as you reinstall within your recorder retention window.

## Troubleshooting

### "File cannot be loaded because running scripts is disabled on this system"

You need to lift the PowerShell ExecutionPolicy for this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This change applies only to the current PowerShell window — no
permanent system change.

### `\\homeassistant\config` not reachable from File Explorer

- HA: **Settings → Add-ons → Samba share** → make sure it's running.
- Open the add-on configuration and confirm `username` / `password`
  are set. Windows will prompt for them on first connect.
- Try the IP instead of the hostname: `\\<HA-IP>\config`.
- Windows firewall: SMB-Client outbound must be allowed (default: yes).

### After update, sensors show `unavailable`

A YAML reload alone wasn't enough — restart HA fully:
**Settings → System → Restart Home Assistant**.

If they're still `unavailable` after restart, check **Settings → System
→ Logs** for messages mentioning `hph_`. The most common cause is that
the underlying Heishamon integration (kamaradclimber) hasn't loaded
yet, so the `panasonic_heat_pump_main_*` entities don't exist for
HeatPump Hero to read from.

### PowerShell 5 throws encoding errors

Windows-default PowerShell 5.1 sometimes has issues with UTF-8 files
without BOM. Install PowerShell 7 once:

```powershell
winget install Microsoft.PowerShell
# Then run scripts via pwsh:
pwsh .\scripts\update.ps1 -HaConfig \\homeassistant\config
```

## Quick reference

| Action | Command |
|---|---|
| First install | `.\scripts\update.ps1 -HaConfig <path>` |
| Update after code change | `.\scripts\update.ps1 -HaConfig <path>` |
| Validate locally before deploy | `py tests\smoke.py` |
| Uninstall (preview) | `.\scripts\uninstall.ps1 -HaConfig <path> -DryRun` |
| Uninstall (skip prompt) | `.\scripts\uninstall.ps1 -HaConfig <path> -Yes` |

In HA after every deploy:

1. Developer Tools → YAML → **Check Configuration** (must be green)
2. Developer Tools → YAML → **All YAML configuration** (reload)
   *or, if helpers / counters changed:* Settings → System → **Restart
   Home Assistant**
