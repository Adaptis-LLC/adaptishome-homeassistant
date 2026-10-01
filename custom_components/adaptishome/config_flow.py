"""Налаштування з інтерфейсу HA: хаб, логін і пароль, далі — які об'єкти показувати."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .api import AdaptisHomeApi, AuthError, HubError
from .const import CONF_HUB, CONF_OBJECTS, DOMAIN, HUB

STEP_USER = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
})


def _objects_schema(devices: list[dict], chosen: list[str]) -> vol.Schema:
    opts = [SelectOptionDict(value=d["id"], label=f"{d['name']} ({d['id']})" + (" · демо" if d.get("demo") else "")) for d in devices]
    return vol.Schema({vol.Required(CONF_OBJECTS, default=chosen):
                       SelectSelector(SelectSelectorConfig(options=opts, multiple=True, mode=SelectSelectorMode.LIST))})


async def _check(hass, data: dict) -> tuple[AdaptisHomeApi, list[dict]]:
    api = AdaptisHomeApi(async_get_clientsession(hass), data.get(CONF_HUB) or HUB, data[CONF_USERNAME].strip(), data[CONF_PASSWORD])
    await api.login()
    return api, await api.devices()


class AdaptisHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._devices: list[dict] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            try:
                api, self._devices = await _check(self.hass, user_input)
            except AuthError:
                errors["base"] = "invalid_auth"
            except HubError:
                errors["base"] = "cannot_connect"
            else:
                hub, login = HUB, user_input[CONF_USERNAME].strip()
                await self.async_set_unique_id(f"{hub}|{login}".lower())
                self._abort_if_unique_id_configured()
                self._data = {CONF_HUB: hub, CONF_USERNAME: login, CONF_PASSWORD: user_input[CONF_PASSWORD], "name": api.name}
                if not self._devices: return self.async_abort(reason="no_objects")
                if len(self._devices) == 1:
                    return self._create([self._devices[0]["id"]])
                return await self.async_step_objects()
        return self.async_show_form(step_id="user", data_schema=STEP_USER, errors=errors)

    async def async_step_objects(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None and user_input[CONF_OBJECTS]:
            return self._create(user_input[CONF_OBJECTS])
        # типово — свої об'єкти, а не всі демо; працівнику з сотнями об'єктів — перші десять
        own = [d["id"] for d in self._devices if not d.get("demo")][:10] or [self._devices[0]["id"]]
        return self.async_show_form(step_id="objects", data_schema=_objects_schema(self._devices, own))

    def _create(self, objects: list[str]) -> ConfigFlowResult:
        return self.async_create_entry(title=f"AdaptisHome · {self._data['name'] or self._data[CONF_USERNAME]}",
                                       data=self._data, options={CONF_OBJECTS: objects})

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            try:
                await _check(self.hass, data)
            except AuthError:
                errors["base"] = "invalid_auth"
            except HubError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                                    description_placeholders={"login": entry.data[CONF_USERNAME]}, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return AdaptisHomeOptionsFlow()


class AdaptisHomeOptionsFlow(OptionsFlow):
    """Змінити набір об'єктів: інтеграція перезавантажується з новим списком."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None and user_input[CONF_OBJECTS]:
            return self.async_create_entry(data={CONF_OBJECTS: user_input[CONF_OBJECTS]})
        try:
            _, devices = await _check(self.hass, self.config_entry.data)
        except (AuthError, HubError):
            return self.async_abort(reason="cannot_connect")
        chosen = [o for o in self.config_entry.options.get(CONF_OBJECTS, []) if any(d["id"] == o for d in devices)]
        return self.async_show_form(step_id="init", data_schema=_objects_schema(devices, chosen))
