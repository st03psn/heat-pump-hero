"""Shared fixtures for HeatPump Hero integration tests.

Two test tiers:

  1. Pure-Python tests (test_dashboard.py, test_config_flow.py) — run with
     only pytest + PyYAML installed.  No Home Assistant required.
     These tests import const.py directly (bypassing __init__.py) so they
     work without a homeassistant installation.

  2. Integration tests (test_setup.py) — require
     pytest-homeassistant-custom-component which spins up a real in-process
     HA instance.  These are skipped locally if the package is absent and
     run in CI where requirements_test.txt is installed.
"""

from __future__ import annotations

import importlib.util

import pytest

# Only activate the HA fixture plugin if the package is available.
if importlib.util.find_spec("pytest_homeassistant_custom_component") is not None:
    pytest_plugins = ["pytest_homeassistant_custom_component"]


# NOTE: do NOT redefine `enable_custom_integrations` here. The
# pytest_homeassistant_custom_component plugin already provides a fixture
# of that name which actually makes HA discover custom_components/hph.
# A local no-op override (returning True) silently shadows it, so the
# integration is never registered and config-entry setup fails with
# "Integration not found" — leaving every entity uncreated. Tests request
# the plugin fixture via @pytest.mark.usefixtures("enable_custom_integrations").
