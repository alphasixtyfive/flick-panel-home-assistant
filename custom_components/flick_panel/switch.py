"""Panel display switch backed by tablet telemetry."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import PanelEntry
from .panel import CONF_PANEL, Panel


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PanelEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Expose the display switch on the tablet device."""
    async_add_entities([PanelDisplay(entry.runtime_data, entry.data[CONF_PANEL])])


class PanelDisplay(SwitchEntity):
    """Wake Flick Panel or blank its display."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "display"
    _attr_icon = "mdi:tablet-dashboard"

    def __init__(self, panel: Panel, original_device_id: str) -> None:
        self.panel = panel
        self.device_entry = panel.device
        self._attr_unique_id = f"{original_device_id}_{self.translation_key}"

    @property
    def available(self) -> bool:
        return self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        state = self.hass.states.get(self.panel.display_entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return state.state != "blank"

    async def async_added_to_hass(self) -> None:
        """Update only when the source telemetry changes."""
        await super().async_added_to_hass()

        @callback
        def refresh(event):
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self.panel.display_entity_id, refresh
            )
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self.panel.async_command("wake")

    async def async_turn_off(self, **kwargs) -> None:
        await self.panel.async_command("sleep")
