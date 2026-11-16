"""Config flow integrácie Kúrenie AI."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import KurenieAuthError, KurenieClient, KurenieError
from .const import CONF_API_KEY, CONF_SCAN_INTERVAL, CONF_URL, DOMAIN
from .coordinator import KurenieConfigEntry
from .model import DEFAULT_INTERVAL, MAX_INTERVAL, MIN_INTERVAL, clamp_interval, device_info, normalize_url

KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="off"))


class KurenieConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pridanie, opätovné prihlásenie a voľby."""

    VERSION = 1

    async def _validate(self, url: str, key: str) -> tuple[dict[str, str], dict[str, Any] | None]:
        """Overí pripojenie GET /api/ha/v1/state. Vracia (chyby, stav)."""
        client = KurenieClient(async_get_clientsession(self.hass), url, key)
        try:
            return {}, await client.async_get_state()
        except KurenieAuthError:
            return {"base": "invalid_auth"}, None
        except KurenieError:
            return {"base": "cannot_connect"}, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
            except ValueError:
                errors[CONF_URL] = "invalid_url"
            else:
                key = user_input[CONF_API_KEY].strip()
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()
                errors, state = await self._validate(url, key)
                if not errors and state is not None:
                    title = device_info(state)["name"]
                    return self.async_create_entry(title=title, data={CONF_URL: url, CONF_API_KEY: key})
        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "http://")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
                vol.Required(CONF_API_KEY): KEY_SELECTOR,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            key = user_input[CONF_API_KEY].strip()
            errors, state = await self._validate(entry.data[CONF_URL], key)
            if not errors and state is not None:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_API_KEY: key})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): KEY_SELECTOR}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: KurenieConfigEntry) -> OptionsFlow:
        return KurenieOptionsFlow()


class KurenieOptionsFlow(OptionsFlow):
    """Interval obnovy (15–300 s)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_SCAN_INTERVAL: clamp_interval(user_input[CONF_SCAN_INTERVAL])})
        current = clamp_interval(self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL))
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_INTERVAL,
                        max=MAX_INTERVAL,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
