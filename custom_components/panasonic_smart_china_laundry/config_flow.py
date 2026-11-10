# -*- coding: utf-8 -*-
"""配置流：手机号 → 密码 → 登录 → 勾选设备（洗衣机/烘护机）。"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import aiohttp_client, config_validation as cv

from .api import PanasonicAuthError, PanasonicLaundryApi
from .const import (
    CATEGORY_DRYER,
    CATEGORY_WASHER,
    DOMAIN,
    SUPPORTED_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)

CONF_DEVICES = "devices"

# 品类中文名
_CATEGORY_NAMES = {
    CATEGORY_WASHER: "洗衣机",
    CATEGORY_DRYER: "烘护机",
}

STEP_USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str}
)
STEP_PASSWORD_SCHEMA = vol.Schema(
    {vol.Required(CONF_PASSWORD): str}
)


class PanasonicLaundryConfigFlow(ConfigFlow, domain=DOMAIN):
    """松下智能家电 洗衣/烘护 配置流。"""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str | None = None
        self._password: str | None = None
        self._api: PanasonicLaundryApi | None = None
        self._devices: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """第一步：输入手机号。"""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME].strip()
            # 同一账号只允许一个配置条目
            await self.async_set_unique_id(self._username)
            self._abort_if_unique_id_configured()
            return await self.async_step_password()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """第二步：输入密码并登录，获取设备列表。"""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            session = aiohttp_client.async_get_clientsession(self.hass)
            self._api = PanasonicLaundryApi(
                session, self._username, self._password
            )
            try:
                await self._api.login()
                dev_list = await self._api.get_devices()
            except PanasonicAuthError as exc:
                _LOGGER.warning("登录失败: %s", exc)
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="password",
                    data_schema=STEP_PASSWORD_SCHEMA,
                    errors=errors,
                )
            except Exception as exc:  # 网络等异常
                _LOGGER.exception("获取设备列表异常")
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="password",
                    data_schema=STEP_PASSWORD_SCHEMA,
                    errors=errors,
                )

            # 过滤本集成支持的品类
            self._devices = [
                dev for dev in dev_list
                if dev.get("deviceId", "").split("_")[1:2]
                and dev["deviceId"].split("_")[1] in SUPPORTED_CATEGORIES
            ]
            if not self._devices:
                return self.async_abort(reason="no_supported_devices")
            return await self.async_step_device()

        return self.async_show_form(
            step_id="password",
            data_schema=STEP_PASSWORD_SCHEMA,
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """第三步：勾选要接入的设备。"""
        if user_input is not None:
            selected_ids = user_input[CONF_DEVICES]
            devices = [
                {
                    "deviceId": dev["deviceId"],
                    "name": dev.get("params", {}).get("deviceName", ""),
                    "category": dev["deviceId"].split("_")[1],
                }
                for dev in self._devices
                if dev["deviceId"] in selected_ids
            ]
            return self.async_create_entry(
                title=self._username,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_DEVICES: devices,
                },
            )

        # 默认全部勾选；多选用 cv.multi_select，单选用 vol.In
        default = [dev["deviceId"] for dev in self._devices]
        options = {
            dev["deviceId"]: (
                f"{dev.get('params', {}).get('deviceName', dev['deviceId'])}"
                f"（{_CATEGORY_NAMES.get(dev['deviceId'].split('_')[1], '?')}"
                f" / {dev.get('params', {}).get('deviceMNO', '?')}）"
            )
            for dev in self._devices
        }
        if len(options) > 1:
            schema = vol.Schema(
                {vol.Required(CONF_DEVICES, default=default): cv.multi_select(options)}
            )
        else:
            schema = vol.Schema(
                {vol.Required(CONF_DEVICES, default=default): vol.In(options)}
            )
        return self.async_show_form(step_id="device", data_schema=schema)
