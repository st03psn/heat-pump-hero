"""Phase-1 bootstrap helpers.

Until phases 2 (sensors) and 3 (automations) move every YAML package
into Python, the integration must still deliver the not-yet-ported
parts of the project as YAML files in `<config>/packages/`. This
module handles:

  - Copying `custom_components/hph/data/packages/*.yaml` into
    `<config>/packages/`
  - Copying `custom_components/hph/data/dashboards/hph.yaml` into
    `<config>/hph/dashboard.yaml`
  - Copying `custom_components/hph/data/dashboards/assets/*.svg` into
    `<config>/www/hph/`
  - Auto-registering the dashboard via Lovelace's storage backend
  - Cleaning every file we ever deployed when the integration is
    removed via the UI

The bundled `data/` directory is populated at integration install
time (HACS clones the entire repo plus the data subtree).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url

from .const import (
    DASHBOARD_FILE_REL,
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

# Source paths relative to this file (= custom_components/hph/)
_PKG_DIR = Path(__file__).parent
_DATA_DIR = _PKG_DIR / "data"
_DATA_PACKAGES = _DATA_DIR / "packages"
_DATA_DASHBOARD = _DATA_DIR / "dashboards" / "hph.yaml"
_DATA_ASSETS = _DATA_DIR / "dashboards" / "assets"
_DATA_BLUEPRINT = _DATA_DIR / "blueprints" / "hph_setup.yaml"


def _config(hass: HomeAssistant) -> Path:
    """Return HA's config directory as a Path."""
    return Path(hass.config.path())


# ─── Deploy ───────────────────────────────────────────────────────────────
async def async_deploy_yaml_packages(hass: HomeAssistant) -> dict[str, Any]:
    """Copy bundled YAML packages, dashboard, assets and blueprint.

    Idempotent — files are overwritten on every setup so HACS updates
    propagate cleanly.

    Returns: a dict summarising what was deployed (used by tests + logs).
    """
    return await hass.async_add_executor_job(_deploy_sync, _config(hass))


def _deploy_sync(config_dir: Path) -> dict[str, Any]:
    deployed: dict[str, list[str]] = {
        "packages": [],
        "dashboard": [],
        "assets": [],
        "blueprint": [],
    }

    # 1. Packages
    pkg_dst = config_dir / "packages"
    pkg_dst.mkdir(parents=True, exist_ok=True)
    if _DATA_PACKAGES.exists():
        for src in sorted(_DATA_PACKAGES.glob("hph_*.yaml")):
            dst = pkg_dst / src.name
            shutil.copyfile(src, dst)
            deployed["packages"].append(src.name)

    # 2. Dashboard YAML
    dash_dst_dir = config_dir / "hph"
    dash_dst_dir.mkdir(parents=True, exist_ok=True)
    if _DATA_DASHBOARD.exists():
        dst = dash_dst_dir / "dashboard.yaml"
        shutil.copyfile(_DATA_DASHBOARD, dst)
        deployed["dashboard"].append(str(dst.relative_to(config_dir)))

    # 3. Asset SVGs
    asset_dst = config_dir / "www" / "hph"
    asset_dst.mkdir(parents=True, exist_ok=True)
    if _DATA_ASSETS.exists():
        for src in sorted(_DATA_ASSETS.glob("*.svg")):
            dst = asset_dst / src.name
            shutil.copyfile(src, dst)
            deployed["assets"].append(src.name)

    # 4. Setup blueprint (legacy — kept for users who used it pre-v0.9)
    bp_dst = config_dir / "blueprints" / "script" / "hph"
    bp_dst.mkdir(parents=True, exist_ok=True)
    if _DATA_BLUEPRINT.exists():
        shutil.copyfile(_DATA_BLUEPRINT, bp_dst / _DATA_BLUEPRINT.name)
        deployed["blueprint"].append(_DATA_BLUEPRINT.name)

    # 5. configuration.yaml — add packages include if missing.
    _ensure_packages_include(config_dir / "configuration.yaml")

    _LOGGER.info(
        "HeatPump Hero deployment: %d packages, dashboard=%s, %d assets, blueprint=%s",
        len(deployed["packages"]),
        bool(deployed["dashboard"]),
        len(deployed["assets"]),
        bool(deployed["blueprint"]),
    )
    return deployed


def _ensure_packages_include(config_yaml: Path) -> None:
    if not config_yaml.exists():
        _LOGGER.warning("configuration.yaml not found at %s — skipping include", config_yaml)
        return

    text = config_yaml.read_text(encoding="utf-8")
    if "packages: !include_dir_named packages" in text:
        return

    # Insert under existing `homeassistant:` block, or append a new one.
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
    """Register the HPH dashboard so it appears in the sidebar automatically.

    Strategy: register a YAML-mode Lovelace dashboard pointing at the
    deployed `<config>/hph/dashboard.yaml`. If the user already created
    a dashboard with the same URL path, we skip silently.
    """
    # Lovelace's dashboard registry lives under hass.data["lovelace"].
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

    # Sidebar entry — this gives the user a clickable HeatPump Hero menu
    # item without needing to add the dashboard manually.
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
    # 1. Packages
    pkg_dir = config_dir / "packages"
    if pkg_dir.exists():
        for f in pkg_dir.glob("hph_*.yaml"):
            try:
                f.unlink()
                _LOGGER.info("Removed %s", f)
            except OSError as exc:
                _LOGGER.warning("Could not remove %s: %s", f, exc)

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

    # 5. Drop packages include if /config/packages/ ends up empty
    if pkg_dir.exists():
        remaining = list(pkg_dir.glob("*.yaml"))
        if not remaining:
            _drop_packages_include(config_dir / "configuration.yaml")
            try:
                pkg_dir.rmdir()
                _LOGGER.info("Removed empty %s", pkg_dir)
            except OSError:
                pass


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
