"""Phase-3 bootstrap helpers.

Phase 3 removes all YAML automation packages — the integration is now
fully self-contained in Python. This module handles the reduced set of
deploy/cleanup tasks:

  - One-time migration: remove hph_*.yaml files previously deployed to
    <config>/packages/ (v0.8 / v0.9 phase 1 leftovers)
  - Copying <config>/hph/dashboard.yaml  (Lovelace YAML-mode panel)
  - Copying <config>/www/hph/*.svg       (dashboard assets)
  - Deploying hph_efficiency.yaml        (utility_meter + integration
    sensors — HA platform config, no automation logic, cannot be
    expressed in Python)
  - Auto-registering the dashboard via Lovelace's storage backend
  - Cleaning every file we ever deployed when the integration is
    removed via the UI
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant

from .const import (
    DASHBOARD_FILE_REL,
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

_PKG_DIR = Path(__file__).parent
_DATA_DIR = _PKG_DIR / "data"
_DATA_DASHBOARD = _DATA_DIR / "dashboards" / "hph.yaml"
_DATA_ASSETS = _DATA_DIR / "dashboards" / "assets"
_DATA_BLUEPRINT = _DATA_DIR / "blueprints" / "hph_setup.yaml"
_DATA_EFFICIENCY = _DATA_DIR / "packages" / "hph_efficiency.yaml"


def _config(hass: HomeAssistant) -> Path:
    return Path(hass.config.path())


# ─── Deploy ───────────────────────────────────────────────────────────────
async def async_deploy_yaml_packages(hass: HomeAssistant) -> dict[str, Any]:
    """Deploy dashboard, assets and the efficiency platform package.

    Also runs one-time migration: removes old hph_*.yaml automation
    packages deployed by v0.8 / v0.9-phase-1.

    Returns: summary dict (used by tests + logs).
    """
    return await hass.async_add_executor_job(_deploy_sync, _config(hass))


def _deploy_sync(config_dir: Path) -> dict[str, Any]:
    deployed: dict[str, Any] = {
        "migrated_removed": [],
        "dashboard": [],
        "assets": [],
        "blueprint": [],
        "efficiency": False,
    }

    # 1. Migration: remove old hph_*.yaml automation packages from
    #    <config>/packages/ (deployed by v0.8 / v0.9-phase-1).
    #    Only hph_efficiency.yaml is kept — it holds platform config.
    pkg_dst = config_dir / "packages"
    if pkg_dst.exists():
        bundled_efficiency = {"hph_efficiency.yaml"}
        for stale in list(pkg_dst.glob("hph_*.yaml")):
            if stale.name not in bundled_efficiency:
                try:
                    stale.unlink()
                    deployed["migrated_removed"].append(stale.name)
                    _LOGGER.info("Migration: removed old automation package %s", stale.name)
                except OSError as exc:
                    _LOGGER.warning("Could not remove %s: %s", stale, exc)

    # 2. Deploy hph_efficiency.yaml (utility_meter + integration sensors).
    if _DATA_EFFICIENCY.exists():
        pkg_dst.mkdir(parents=True, exist_ok=True)
        dst = pkg_dst / _DATA_EFFICIENCY.name
        shutil.copyfile(_DATA_EFFICIENCY, dst)
        deployed["efficiency"] = True

    # 3. Dashboard YAML
    dash_dst_dir = config_dir / "hph"
    dash_dst_dir.mkdir(parents=True, exist_ok=True)
    if _DATA_DASHBOARD.exists():
        dst = dash_dst_dir / "dashboard.yaml"
        shutil.copyfile(_DATA_DASHBOARD, dst)
        deployed["dashboard"].append(str(dst.relative_to(config_dir)))

    # 4. Asset SVGs
    asset_dst = config_dir / "www" / "hph"
    asset_dst.mkdir(parents=True, exist_ok=True)
    if _DATA_ASSETS.exists():
        for src in sorted(_DATA_ASSETS.glob("*.svg")):
            dst = asset_dst / src.name
            shutil.copyfile(src, dst)
            deployed["assets"].append(src.name)

    # 5. Setup blueprint (legacy — kept for users who used it pre-v0.9)
    bp_dst = config_dir / "blueprints" / "script" / "hph"
    bp_dst.mkdir(parents=True, exist_ok=True)
    if _DATA_BLUEPRINT.exists():
        shutil.copyfile(_DATA_BLUEPRINT, bp_dst / _DATA_BLUEPRINT.name)
        deployed["blueprint"].append(_DATA_BLUEPRINT.name)

    # 6. Ensure packages include in configuration.yaml (needed for efficiency.yaml)
    if deployed["efficiency"]:
        _ensure_packages_include(config_dir / "configuration.yaml")

    if deployed["migrated_removed"]:
        _LOGGER.info(
            "Migration complete: removed %d old automation packages: %s",
            len(deployed["migrated_removed"]),
            ", ".join(deployed["migrated_removed"]),
        )
    _LOGGER.info(
        "HeatPump Hero bootstrap: dashboard=%s, %d assets, efficiency=%s, %d old packages removed",
        bool(deployed["dashboard"]),
        len(deployed["assets"]),
        deployed["efficiency"],
        len(deployed["migrated_removed"]),
    )
    return deployed


def _ensure_packages_include(config_yaml: Path) -> None:
    if not config_yaml.exists():
        _LOGGER.warning("configuration.yaml not found at %s — skipping include", config_yaml)
        return
    text = config_yaml.read_text(encoding="utf-8")
    if "packages: !include_dir_named packages" in text:
        return
    import re
    if re.search(r"(?m)^homeassistant:\s*$", text):
        new_text = re.sub(
            r"(?m)^(homeassistant:\s*)$",
            r"\1\n  packages: !include_dir_named packages",
            text,
            count=1,
        )
    else:
        sep = "\n" if not text.endswith("\n") else ""
        new_text = text + f"{sep}\nhomeassistant:\n  packages: !include_dir_named packages\n"
    config_yaml.write_text(new_text, encoding="utf-8")
    _LOGGER.info("Added 'packages: !include_dir_named packages' to configuration.yaml")


# ─── Dashboard auto-register ──────────────────────────────────────────────
async def async_register_dashboard(hass: HomeAssistant) -> None:
    """Register the HPH dashboard so it appears in the sidebar automatically."""
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is None:
        _LOGGER.debug("Lovelace not loaded yet — skipping dashboard auto-register")
        return
    dashboards = getattr(lovelace_data, "dashboards", None)
    if dashboards is None:
        _LOGGER.debug("Lovelace dashboards attribute missing — skipping auto-register")
        return
    if DASHBOARD_URL_PATH in dashboards:
        _LOGGER.debug("Dashboard %s already registered — skipping", DASHBOARD_URL_PATH)
        return
    try:
        frontend.async_register_built_in_panel(
            hass,
            component_name="lovelace",
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon=DASHBOARD_ICON,
            frontend_url_path=DASHBOARD_URL_PATH,
            config={"mode": "yaml", "filename": DASHBOARD_FILE_REL},
            require_admin=False,
            update=True,
        )
        _LOGGER.info("Registered HeatPump Hero dashboard at /%s", DASHBOARD_URL_PATH)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Could not register dashboard panel: %s", exc)


# ─── Cleanup on UI-uninstall ──────────────────────────────────────────────
async def async_clean_deployed_files(hass: HomeAssistant) -> None:
    """Remove every file the integration ever deployed."""
    await hass.async_add_executor_job(_clean_sync, _config(hass))


def _clean_sync(config_dir: Path) -> None:
    # 1. Remove hph_efficiency.yaml and clean packages/ if empty
    pkg_dir = config_dir / "packages"
    if pkg_dir.exists():
        for f in pkg_dir.glob("hph_*.yaml"):
            try:
                f.unlink()
                _LOGGER.info("Removed %s", f)
            except OSError as exc:
                _LOGGER.warning("Could not remove %s: %s", f, exc)
        remaining = list(pkg_dir.glob("*.yaml"))
        if not remaining:
            _drop_packages_include(config_dir / "configuration.yaml")
            try:
                pkg_dir.rmdir()
                _LOGGER.info("Removed empty %s", pkg_dir)
            except OSError:
                pass

    # 2. Dashboard YAML + dir
    dash_dir = config_dir / "hph"
    if dash_dir.exists():
        try:
            shutil.rmtree(dash_dir)
            _LOGGER.info("Removed %s", dash_dir)
        except OSError as exc:
            _LOGGER.warning("Could not remove %s: %s", dash_dir, exc)

    # 3. Asset dir
    asset_dir = config_dir / "www" / "hph"
    if asset_dir.exists():
        try:
            shutil.rmtree(asset_dir)
            _LOGGER.info("Removed %s", asset_dir)
        except OSError as exc:
            _LOGGER.warning("Could not remove %s: %s", asset_dir, exc)

    # 4. Blueprint
    bp_dir = config_dir / "blueprints" / "script" / "hph"
    if bp_dir.exists():
        try:
            shutil.rmtree(bp_dir)
            _LOGGER.info("Removed %s", bp_dir)
        except OSError as exc:
            _LOGGER.warning("Could not remove %s: %s", bp_dir, exc)


def _drop_packages_include(config_yaml: Path) -> None:
    if not config_yaml.exists():
        return
    import re
    text = config_yaml.read_text(encoding="utf-8")
    new_text = re.sub(
        r"(?m)^[ \t]*packages:\s*!include_dir_named\s+packages\s*\r?\n",
        "",
        text,
    )
    if new_text != text:
        config_yaml.write_text(new_text, encoding="utf-8")
        _LOGGER.info("Removed 'packages: !include_dir_named packages' from configuration.yaml")
