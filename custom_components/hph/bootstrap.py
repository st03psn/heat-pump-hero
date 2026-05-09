"""Phase-3 bootstrap helpers.

Deploys the minimal set of files needed for the integration to function:
  - hph_efficiency.yaml → <config>/packages/   (utility_meter platform config)
  - hph/dashboard.yaml  → <config>/hph/        (Lovelace YAML dashboard)
  - *.svg               → <config>/www/hph/     (dashboard assets)

Also handles:
  - One-time migration: removes hph_*.yaml files previously deployed by
    v0.8 / v0.9-phase-1 (all except hph_efficiency.yaml)
  - Dashboard auto-registration in the Lovelace store
  - Aggressive file cleanup on UI-uninstall
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
_DATA_EFFICIENCY = _DATA_DIR / "packages" / "hph_efficiency.yaml"


def _config(hass: HomeAssistant) -> Path:
    return Path(hass.config.path())


# ─── Deploy ───────────────────────────────────────────────────────────────
async def async_deploy_yaml_packages(hass: HomeAssistant) -> dict[str, Any]:
    """Deploy dashboard, assets, efficiency package; migrate old packages."""
    return await hass.async_add_executor_job(_deploy_sync, _config(hass))


def _deploy_sync(config_dir: Path) -> dict[str, Any]:
    deployed: dict[str, Any] = {
        "migrated_removed": [],
        "dashboard": [],
        "assets": [],
        "efficiency": False,
    }

    # 1. Migration: remove old hph_*.yaml automation packages.
    pkg_dst = config_dir / "packages"
    if pkg_dst.exists():
        keep = {"hph_efficiency.yaml"}
        for stale in list(pkg_dst.glob("hph_*.yaml")):
            if stale.name not in keep:
                try:
                    stale.unlink()
                    deployed["migrated_removed"].append(stale.name)
                    _LOGGER.info("Migration: removed old automation package %s", stale.name)
                except OSError as exc:
                    _LOGGER.warning("Could not remove %s: %s", stale, exc)

    # 2. Deploy hph_efficiency.yaml (utility_meter + integration sensors).
    if _DATA_EFFICIENCY.exists():
        pkg_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_DATA_EFFICIENCY, pkg_dst / _DATA_EFFICIENCY.name)
        deployed["efficiency"] = True
        _ensure_packages_include(config_dir / "configuration.yaml")

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

    if deployed["migrated_removed"]:
        _LOGGER.info(
            "Migration: removed %d old automation packages: %s",
            len(deployed["migrated_removed"]),
            ", ".join(deployed["migrated_removed"]),
        )
    _LOGGER.info(
        "HPH bootstrap done: dashboard=%s assets=%d efficiency=%s removed=%d",
        bool(deployed["dashboard"]),
        len(deployed["assets"]),
        deployed["efficiency"],
        len(deployed["migrated_removed"]),
    )
    return deployed


def _ensure_packages_include(config_yaml: Path) -> None:
    if not config_yaml.exists():
        _LOGGER.warning("configuration.yaml not found — skipping packages include")
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
    """Register the HPH Lovelace dashboard in the sidebar.

    Strategy (two-pronged for reliability):
    1. Add it directly to hass.data["lovelace"].dashboards via LovelaceYAML —
       this makes HA serve the YAML config over the API immediately.
    2. Register a built-in panel for the sidebar entry.

    If Lovelace isn't loaded yet (e.g. called too early), falls back to
    registering only the built-in panel and logs a warning.
    """
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is None:
        _LOGGER.debug("Lovelace not loaded — skipping dashboard register")
        return

    dashboards = getattr(lovelace_data, "dashboards", None)
    if dashboards is None:
        _LOGGER.debug("Lovelace dashboards attribute missing — skipping")
        return

    # Step 1: Register in the Lovelace dashboard store so the API serves
    # the YAML file correctly when the frontend loads the dashboard.
    if DASHBOARD_URL_PATH not in dashboards:
        try:
            from homeassistant.components.lovelace.dashboard import LovelaceYAML
            yaml_dash = LovelaceYAML(
                hass,
                DASHBOARD_URL_PATH,
                {
                    "mode": "yaml",
                    "filename": DASHBOARD_FILE_REL,
                    "title": DASHBOARD_TITLE,
                    "icon": DASHBOARD_ICON,
                    "show_in_sidebar": True,
                    "require_admin": False,
                },
            )
            dashboards[DASHBOARD_URL_PATH] = yaml_dash
            _LOGGER.info("HPH dashboard registered in Lovelace store at /%s", DASHBOARD_URL_PATH)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Could not register dashboard in Lovelace store: %s", exc)
    else:
        _LOGGER.debug("Dashboard %s already in Lovelace store — skipping", DASHBOARD_URL_PATH)

    # Step 2: Register the sidebar panel entry.
    try:
        frontend.async_register_built_in_panel(
            hass,
            component_name="lovelace",
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon=DASHBOARD_ICON,
            frontend_url_path=DASHBOARD_URL_PATH,
            config={
                "mode": "yaml",
                "filename": DASHBOARD_FILE_REL,
            },
            require_admin=False,
            update=True,
        )
        _LOGGER.info("HPH sidebar panel registered at /%s", DASHBOARD_URL_PATH)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Could not register sidebar panel: %s", exc)


# ─── Cleanup on UI-uninstall ──────────────────────────────────────────────
async def async_clean_deployed_files(hass: HomeAssistant) -> None:
    """Remove every file the integration ever deployed."""
    # Remove from Lovelace store
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is not None:
        dashboards = getattr(lovelace_data, "dashboards", {})
        dashboards.pop(DASHBOARD_URL_PATH, None)

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
