"""AdaptisHome — резервування інтернету Adaptis: стан об'єктів і каналів з хаба в Home Assistant."""
from __future__ import annotations

import logging
import os

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import AdaptisHomeApi, AuthError, HubError
from .const import CARD_URL, CONF_HUB, CONF_OBJECTS, DOMAIN, VERSION
from .coordinator import AdaptisHomeCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.EVENT]

type AdaptisHomeEntry = ConfigEntry[AdaptisHomeCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Картка для дашборду: файл віддається з інтеграції і сам додається в ресурси Lovelace (режим «storage»)."""
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, os.path.join(os.path.dirname(__file__), "frontend", "adaptishome-card.js"), True)])
    hass.async_create_task(_register_card(hass))
    return True


async def _register_card(hass: HomeAssistant) -> None:
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):   # YAML-режим: ресурс додають руками, див. README
        return
    try:
        if not getattr(resources, "loaded", True): await resources.async_load()
        url = f"{CARD_URL}?v={VERSION}"
        for item in resources.async_items():
            if item["url"].startswith(CARD_URL):
                if item["url"] != url: await resources.async_update_item(item["id"], {"url": url})   # нова версія — новий кеш
                return
        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception as e:   # noqa: BLE001 — картка не має валити інтеграцію
        _LOGGER.warning("Не вдалося додати картку в ресурси Lovelace: %s", e)


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
