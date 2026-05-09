"""HeatPump Hero — diagnostics coordinator.

Ports hph_diagnostics.yaml automation:
  - hph_diag_log_error_change  (sensor.hph_diagnostics_current_error state change)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register diagnostics listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    @callback
    def _on_error_change(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        if old.state == new.state:
            return
        if new.state in ("unknown", "unavailable", ""):
            return
        hass.async_create_task(_log_error(old.state, new.state, new.attributes))

    async def _log_error(old_code: str, new_code: str, attrs: dict) -> None:
        now_str = dt_util.now().isoformat()
        await hass.services.async_call(
            "datetime", "set_value",
            {"entity_id": "datetime.hph_diag_last_error_time", "datetime": now_str},
            blocking=True,
        )
        hist_st = hass.states.get("text.hph_diag_error_history")
        raw = hist_st.state if hist_st else "[]"
        try:
            old_history: list = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            old_history = []
        new_event = {
            "code": new_code,
            "time": now_str,
            "severity": attrs.get("severity"),
        }
        new_history = ([new_event] + old_history)[:5]
        await hass.services.async_call(
            "text", "set_value",
            {"entity_id": "text.hph_diag_error_history", "value": json.dumps(new_history)},
            blocking=True,
        )
        if new_code == "ok":
            await hass.services.async_call(
                "persistent_notification", "dismiss",
                {"notification_id": "hph_active_error"},
                blocking=True,
            )
        else:
            severity = attrs.get("severity", "")
            message_text = attrs.get("message", "")
            model_note = attrs.get("model_note", "")
            body = (
                f"**{severity.upper()}**: {message_text}"
            )
            if model_note and model_note.strip():
                body += f"\n**Model note:** {model_note}"
            body += "\n\nSee the [Diagnostics view](/hph/optimization) for history."
            await hass.services.async_call(
                "persistent_notification", "create",
                {
                    "notification_id": "hph_active_error",
                    "title": f"HeatPump Hero — heat-pump fault {new_code}",
                    "message": body,
                },
                blocking=True,
            )

    unsubs.append(
        async_track_state_change_event(
            hass, ["sensor.hph_diagnostics_current_error"], _on_error_change
        )
    )

    _LOGGER.debug("HPH diagnostics coordinator started")
    return unsubs
