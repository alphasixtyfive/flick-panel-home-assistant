"""Choose a tablet registered through Flick Panel's Tablet link."""

import probatio as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .panel import CONF_PANEL, CONF_REGISTRATION_ID, DOMAIN, linked_panels


class FlickPanelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add controls to a linked Flick Panel device."""

    VERSION = 1
    MINOR_VERSION = 3

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        if not (panels := linked_panels(self.hass)):
            return self.async_abort(reason="no_linked_panels")
        entries = self._async_current_entries()
        existing = {entry.data[CONF_PANEL] for entry in entries}
        registrations = {
            entry.data[CONF_REGISTRATION_ID]
            for entry in entries
            if entry.data.get(CONF_REGISTRATION_ID)
        }
        available = {
            key: panel
            for key, panel in panels.items()
            if key not in existing and panel.registration_id not in registrations
        }
        if not available:
            return self.async_abort(reason="already_configured")

        errors = {}
        if user_input is not None:
            device_id = user_input.get(CONF_PANEL)
            if panel := available.get(device_id):
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=panel.name,
                    data={
                        CONF_PANEL: device_id,
                        CONF_REGISTRATION_ID: panel.registration_id,
                    },
                )
            errors["base"] = "panel_unavailable"

        options = [{"value": key, "label": panel.name} for key, panel in available.items()]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PANEL, default=options[0]["value"]
                    ): SelectSelector(SelectSelectorConfig(options=options)),
                }
            ),
            errors=errors,
        )
