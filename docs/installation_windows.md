# Installation on Windows

Since v0.9 HeatPump Hero is a **HACS custom integration** with no
shell-script step. The installation flow is identical on Windows, Linux,
and macOS — your operating system doesn't matter, because everything
runs inside Home Assistant.

→ Follow [installation.md](installation.md).

## Things to know on Windows specifically

- **Network share access to `\\<HA-host>\config`** is only needed if you
  want to inspect or manually edit files. The standard install path
  (HACS + UI wizard) requires zero file access.
- **HACS GitHub-rate-limit token**: Windows doesn't change anything
  here. Configure it in HACS the same way as on any other platform.
- **Line endings**: irrelevant — you're not editing YAML by hand.

## If you came here from an old v0.7/v0.8 manual-copy install

The old PowerShell flow (copy `packages/`, `dashboards/`, `blueprints/`
to your HA config share, then add `packages: !include_dir_named
packages` to `configuration.yaml`) is **deprecated**. It still works
today but will be removed in v1.0. To migrate:

1. Remove your old `packages/hph_*.yaml` files from `<config>/packages/`
   (keep `hph_efficiency.yaml` if it's there — it's redeployed by the
   integration; no harm in deleting it first either).
2. Remove the old `<config>/hph/` directory.
3. Restart HA.
4. Install the integration via HACS as described in
   [installation.md](installation.md). It will redeploy everything and
   pick up your existing helper values where possible.

Your recorded long-term statistics are kept — the recorder DB is
independent of the integration.
