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


@pytest.fixture
def enable_custom_integrations(hass):  # noqa: ARG001
    """Enable loading of custom integrations in the test hass instance."""
    return True
