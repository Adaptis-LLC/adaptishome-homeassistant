"""AdaptisHome — резервування інтернету Adaptis: стан об'єктів і каналів з хаба в Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AdaptisHomeApi, AuthError, HubError
from .const import CONF_HUB, CONF_OBJECTS
from .coordinator import AdaptisHomeCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.EVENT]

type AdaptisHomeEntry = ConfigEntry[AdaptisHomeCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AdaptisHomeEntry) -> bool:
    api = AdaptisHomeApi(async_get_clientsession(hass), entry.data[CONF_HUB], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    try:
        await api.login()
    except AuthError as e:
        raise ConfigEntryAuthFailed(str(e)) from e
    except HubError as e:
        raise ConfigEntryNotReady(str(e)) from e
    objects = entry.options.get(CONF_OBJECTS) or entry.data.get(CONF_OBJECTS) or []
    coordinator = AdaptisHomeCoordinator(hass, entry, api, objects)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_changed))
    return True


async def _options_changed(hass: HomeAssistant, entry: AdaptisHomeEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AdaptisHomeEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
