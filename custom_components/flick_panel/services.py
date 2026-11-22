"""Automation actions for linked Flick Panel tablets."""

import re

import probatio as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .panel import CONF_LEGACY_DEVICE_ID, CONF_PANEL, DOMAIN, Panel

CAMERA = "camera_entity_id"
PAGE = "page"
BRIGHTNESS = "brightness"
PACKAGE_NAME = "package_name"
PACKAGE_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")
DISPLAY_COMMANDS = {
    "wake_display": "wake",
    "blank_display": "sleep",
    "start_screensaver": "show_clock",
    "stop_screensaver": "wake",
    "close_viewer": "close_viewer",
}


def _target_panel(hass: HomeAssistant, device_id: str) -> Panel:
    previous_device = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        panel = entry.runtime_data
        if device_id == panel.device.id:
            return panel
        if previous_device is None and device_id in (
            entry.data[CONF_PANEL], entry.data.get(CONF_LEGACY_DEVICE_ID)
        ):
            previous_device = panel
    if previous_device is not None:
        return previous_device
    raise ServiceValidationError("Choose a tablet linked to Flick Panel")


def _brightness_level(value: object) -> int:
    if type(value) not in (int, float) or not 1 <= value <= 100 or value != int(value):
        raise vol.Invalid("Use a whole number from 1 to 100")
    return int(value)


def _app_package(value: str) -> str:
    if len(value) > 255 or not PACKAGE_PATTERN.fullmatch(value):
        raise vol.Invalid("Enter an Android package name")
    return value


@callback
def register_actions(hass: HomeAssistant) -> None:
    """Register the tablet's existing commands as typed admin actions."""

    def panel(call: ServiceCall) -> Panel:
        return _target_panel(hass, call.data[ATTR_DEVICE_ID])

    async def display(call: ServiceCall) -> None:
        await panel(call).async_command(DISPLAY_COMMANDS[call.service])

    async def open_camera(call: ServiceCall) -> None:
        camera = call.data[CAMERA]
        if not camera.startswith("camera.") or hass.states.get(camera) is None:
            raise ServiceValidationError("Choose a Home Assistant camera")
        await panel(call).async_command("open_camera", camera=camera)

    async def open_tile(call: ServiceCall) -> None:
        entity = call.data[ATTR_ENTITY_ID]
        if hass.states.get(entity) is None:
            raise ServiceValidationError("Choose a Home Assistant entity")
        await panel(call).async_command("open_tile", entity_id=entity)

    async def launch_app(call: ServiceCall) -> None:
        await panel(call).async_command(
            "launch_app", package_name=call.data[PACKAGE_NAME]
        )

    async def show_page(call: ServiceCall) -> None:
        await panel(call).async_command("show_page", page=call.data[PAGE])

    async def set_brightness(call: ServiceCall) -> None:
        await panel(call).async_command(
            "set_brightness", level=call.data.get(BRIGHTNESS, "auto")
        )

    device_fields = {vol.Required(ATTR_DEVICE_ID): cv.string}
    device_schema = vol.Schema(device_fields)
    for action in DISPLAY_COMMANDS:
        async_register_admin_service(
            hass, DOMAIN, action, display, schema=device_schema
        )

    for action, handler, fields in (
        ("open_camera", open_camera, {vol.Required(CAMERA): cv.entity_id}),
        ("open_tile", open_tile, {vol.Required(ATTR_ENTITY_ID): cv.entity_id}),
        (
            "launch_app",
            launch_app,
            {vol.Required(PACKAGE_NAME): vol.All(cv.string, _app_package)},
        ),
        (
            "show_page",
            show_page,
            {vol.Required(PAGE): vol.In(("favourites", "rooms", "cameras"))},
        ),
        (
            "set_brightness",
            set_brightness,
            {vol.Optional(BRIGHTNESS): _brightness_level},
        ),
    ):
        async_register_admin_service(
            hass, DOMAIN, action, handler, schema=vol.Schema(device_fields | fields)
        )
