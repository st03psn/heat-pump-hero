"""Config flow for HeatPump Hero — 4-step wizard.

Step 1 (user)        — vendor preset selection
Step 2 (model)       — pump model selection
Step 3 (sensors)     — optional external sensors (entity selectors)
Step 4 (confirm)     — final confirmation + restart hint

Options flow re-runs the same wizard from the integration's
"Configure" button so users can change settings later.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, INTEGRATION_NAME, PUMP_MODELS, VENDOR_PRESETS

_LOGGER = logging.getLogger(__name__)


def _vendor_options() -> list[selector.SelectOptionDict]:
    """Vendor preset options. v0.9: only Panasonic is fully validated;
    other vendor recipes exist but haven't been tested by users on
    real hardware. Show them as teaser-only so the integration's
    multi-vendor scope is visible, but mark them clearly."""
    selectable = {"panasonic_heishamon", "panasonic_heishamon_mqtt", "keep_current"}
    options: list[selector.SelectOptionDict] = []
    for v in list(VENDOR_PRESETS.keys()) + ["keep_current"]:
        label = v.replace("_", " ").title()
        if v not in selectable:
            label = f"{label} — Coming soon (v1.0)"
        options.append(selector.SelectOptionDict(value=v, label=label))
    return options


def _selectable_vendor_keys() -> set[str]:
    return {"panasonic_heishamon", "panasonic_heishamon_mqtt", "keep_current"}


def _model_options() -> list[selector.SelectOptionDict]:
    return [
        selector.SelectOptionDict(value=k, label=v.get("description", k))
        for k, v in PUMP_MODELS.items()
    ]


def _temp_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.TEMPERATURE,
            multiple=False,
        )
    )


def _power_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.POWER,
            multiple=False,
        )
    )


def _energy_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.ENERGY,
            multiple=False,
        )
    )


def _any_sensor_selector() -> selector.EntitySelector:
    """Unconstrained sensor selector — for price / PV / forecast entities."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            multiple=False,
        )
    )


class HphConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for HeatPump Hero."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def _user_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("vendor_preset", default="panasonic_heishamon"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_vendor_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 1 — pick a vendor preset."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            picked = user_input["vendor_preset"]
            if picked not in _selectable_vendor_keys():
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._user_schema(),
                    errors={"vendor_preset": "vendor_not_yet_available"},
                    description_placeholders={"vendor": picked},
                )
            self._data["vendor_preset"] = picked
            return await self.async_step_model()

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(),
            description_placeholders={"name": INTEGRATION_NAME},
        )

    async def async_step_model(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 2 — pick the heat-pump model."""
        if user_input is not None:
            self._data["pump_model"] = user_input["pump_model"]
            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required("pump_model", default="panasonic_l_aql"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_model_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="model", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 3 — optional external sensors."""
        if user_input is not None:
            self._data.update(
                {
                    "indoor_temp_entity": user_input.get("indoor_temp_entity", ""),
                    "outdoor_temp_entity": user_input.get("outdoor_temp_entity", ""),
                    "external_thermal_power": user_input.get("external_thermal_power", ""),
                    "external_electrical_power": user_input.get("external_electrical_power", ""),
                    "external_thermal_energy": user_input.get("external_thermal_energy", ""),
                    "external_electrical_energy": user_input.get("external_electrical_energy", ""),
                    "electricity_price_entity": user_input.get("electricity_price_entity", ""),
                    "ctrl_pv_surplus_entity": user_input.get("ctrl_pv_surplus_entity", ""),
                    "ctrl_forecast_entity": user_input.get("ctrl_forecast_entity", ""),
                }
            )
            return await self.async_step_confirm()

        schema = vol.Schema(
            {
                vol.Optional("indoor_temp_entity"): _temp_selector(),
                vol.Optional("outdoor_temp_entity"): _temp_selector(),
                vol.Optional("external_thermal_power"): _power_selector(),
                vol.Optional("external_electrical_power"): _power_selector(),
                vol.Optional("external_thermal_energy"): _energy_selector(),
                vol.Optional("external_electrical_energy"): _energy_selector(),
                vol.Optional("electricity_price_entity"): _any_sensor_selector(),
                vol.Optional("ctrl_pv_surplus_entity"): _power_selector(),
                vol.Optional("ctrl_forecast_entity"): _temp_selector(),
            }
        )
        return self.async_show_form(step_id="sensors", data_schema=schema)

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 4 — confirm + create entry."""
        if user_input is not None:
            return self.async_create_entry(title=INTEGRATION_NAME, data=self._data)

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "vendor": self._data.get("vendor_preset", "?"),
                "model": self._data.get("pump_model", "?"),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "HphOptionsFlow":
        return HphOptionsFlow()


class HphOptionsFlow(config_entries.OptionsFlow):
    """Full 3-step reconfigure wizard (vendor → sensors → done)."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        # config_entry is injected by HA after construction.
        if not self._data:
            self._data = dict(self.config_entry.data)

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required(
                    "vendor_preset", default=self._data.get("vendor_preset", "keep_current")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_vendor_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    "pump_model", default=self._data.get("pump_model", "panasonic_l_aql")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_model_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 2 — reconfigure optional external sensors."""
        if user_input is not None:
            self._data.update(
                {
                    "indoor_temp_entity": user_input.get("indoor_temp_entity", ""),
                    "outdoor_temp_entity": user_input.get("outdoor_temp_entity", ""),
                    "external_thermal_power": user_input.get("external_thermal_power", ""),
                    "external_electrical_power": user_input.get("external_electrical_power", ""),
                    "external_thermal_energy": user_input.get("external_thermal_energy", ""),
                    "external_electrical_energy": user_input.get("external_electrical_energy", ""),
                    "electricity_price_entity": user_input.get("electricity_price_entity", ""),
                    "ctrl_pv_surplus_entity": user_input.get("ctrl_pv_surplus_entity", ""),
                    "ctrl_forecast_entity": user_input.get("ctrl_forecast_entity", ""),
                }
            )
            return self.async_create_entry(title="", data=self._data)

        # Build schema dynamically — only set default for fields where the
        # user has a non-empty stored value. EntitySelector validates the
        # default against existing entities; an empty-string default
        # surfaces as "neither valid entity ID nor UUID" in the UI even
        # though Optional() permits missing keys.
        fields = [
            ("indoor_temp_entity", _temp_selector()),
            ("outdoor_temp_entity", _temp_selector()),
            ("external_thermal_power", _power_selector()),
            ("external_electrical_power", _power_selector()),
            ("external_thermal_energy", _energy_selector()),
            ("external_electrical_energy", _energy_selector()),
            ("electricity_price_entity", _any_sensor_selector()),
            ("ctrl_pv_surplus_entity", _power_selector()),
            ("ctrl_forecast_entity", _temp_selector()),
        ]
        schema_dict: dict[Any, Any] = {}
        for key, sel in fields:
            stored = self._data.get(key, "")
            if stored:
                schema_dict[vol.Optional(key, default=stored)] = sel
            else:
                schema_dict[vol.Optional(key)] = sel
        return self.async_show_form(step_id="sensors", data_schema=vol.Schema(schema_dict))
