"""Link Panel controls to an existing Flick Panel mobile registration."""

from dataclasses import dataclass
from typing import Any

from homeassistant.components.mobile_app.const import ATTR_APP_ID, DOMAIN as MOBILE_APP
from homeassistant.components.mobile_app.util import get_notify_service
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er

DOMAIN = "flick_panel"
CONF_PANEL = "panel"
CONF_REGISTRATION_ID = "registration_id"
CONF_LEGACY_DEVICE_ID = "legacy_device_id"
APP_ID = "app.flickpanel"


@dataclass(frozen=True)
class Panel:
    """A tablet and the display telemetry it already publishes."""

    hass: HomeAssistant
    device: dr.DeviceEntry
    registration_id: str | None
    webhook_id: str
    display_entity_id: str

    async def async_command(self, command: str, **data: Any) -> None:
        """Send a command to this tablet through its registered notify action."""
        try:
            service = get_notify_service(self.hass, self.webhook_id)
        except KeyError:
            service = None
        if not service or not self.hass.services.has_service("notify", service):
            raise HomeAssistantError("The Flick Panel tablet link is unavailable")
        try:
            await self.hass.services.async_call(
                "notify",
                service,
                {
                    "message": "command_flick_panel",
                    "data": {"command": command, **data},
                },
                blocking=True,
            )
        except HomeAssistantError:
            raise HomeAssistantError(
                "Flick Panel is not connected to Home Assistant"
            ) from None


@callback
def linked_panels(hass: HomeAssistant) -> dict[str, Panel]:
    """Find Flick Panel devices by registration and exact sensor identity."""
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    panels = {}
    for entry in hass.config_entries.async_entries(MOBILE_APP):
        if entry.disabled_by is not None or entry.data.get(ATTR_APP_ID) != APP_ID:
            continue
        if not (webhook_id := entry.data.get(CONF_WEBHOOK_ID)):
            continue
        display = entities.async_get_entity_id(
            "sensor", MOBILE_APP, f"{webhook_id}_display_mode"
        )
        if not display or not (sensor := entities.async_get(display)):
            continue
        if sensor.disabled_by is not None or sensor.config_entry_id != entry.entry_id:
            continue
        if sensor.device_id and (device := devices.async_get(sensor.device_id)):
            panels[device.id] = Panel(
                hass, device, entry.unique_id, webhook_id, display
            )
    return panels
