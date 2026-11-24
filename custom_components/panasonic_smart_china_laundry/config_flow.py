# -*- coding: utf-8 -*-
"""配置流：手机号 → 密码 → 登录 → 勾选设备（洗衣机/烘护机）。

支持三种入口：
- 添加集成（source=user）：三步表单，防同一账号重复添加。
- 重新配置（source=reconfigure）：详情页 ⋮ 菜单「重新配置」，复用三步表单，
  默认值预填已配置的账号/密码/设备，提交后原地更新并重载。
- 选项（options）：详情页「配置」齿轮按钮，单步勾选接入的设备，
  默认值预填当前已接入设备。
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import aiohttp_client, config_validation as cv

from .api import PanasonicAuthError, PanasonicLaundryApi
from .const import (
    CATEGORY_DRYER,
    CATEGORY_WASHER,
    CONF_DEVICES,
    DOMAIN,
    SUPPORTED_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)

# 品类中文名
_CATEGORY_NAMES = {
    CATEGORY_WASHER: "洗衣机",
    CATEGORY_DRYER: "烘护机",
}

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str})
STEP_PASSWORD_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


class PanasonicLaundryConfigFlow(ConfigFlow, domain=DOMAIN):
    """松下智能家电 洗衣/烘护 配置流。"""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str | None = None
        self._password: str | None = None
        self._api: PanasonicLaundryApi | None = None
        self._devices: list[dict] = []

    @staticmethod
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """返回「配置」齿轮按钮对应的选项流。"""
        return PanasonicLaundryOptionsFlow()

    # ---------- 入口 ----------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """第一步：输入手机号（reconfigure 时预填已配置值）。"""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME].strip()
            return await self.async_step_password()

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """重新配置入口：复用添加流程，默认值预填已配置值。"""
        return await self.async_step_user(user_input)

    # ---------- 步骤 ----------

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
                    data_schema=self._password_schema(),
                    errors=errors,
                )
            except Exception:  # 网络等异常
                _LOGGER.exception("获取设备列表异常")
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="password",
                    data_schema=self._password_schema(),
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
            data_schema=self._password_schema(),
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
            # 账号/密码存 data，设备列表存 options（可由齿轮按钮单独改）
            data = {
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
            }
            options = {CONF_DEVICES: devices}
            await self.async_set_unique_id(self._username)
            if self.source == SOURCE_RECONFIGURE:
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data=data,
                    options=options,
                )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._username,
                data=data,
                options=options,
            )

        default = self._default_device_ids()
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
            single_default = default[0] if default else next(iter(options))
            schema = vol.Schema(
                {vol.Required(CONF_DEVICES, default=single_default): vol.In(options)}
            )
        return self.async_show_form(step_id="device", data_schema=schema)

    # ---------- 表单默认值 ----------

    def _reconfigure_data(self) -> dict[str, Any]:
        """重新配置时返回已配置值（其余场景返回空字典）。"""
        if self.source == SOURCE_RECONFIGURE:
            return dict(self._get_reconfigure_entry().data)
        return {}

    def _user_schema(self) -> vol.Schema:
        """手机号表单：reconfigure 时预填当前手机号。"""
        username = self._reconfigure_data().get(CONF_USERNAME)
        if username:
            return vol.Schema({vol.Required(CONF_USERNAME, default=username): str})
        return STEP_USER_SCHEMA

    def _password_schema(self) -> vol.Schema:
        """密码表单：reconfigure 时预填当前密码。"""
        password = self._reconfigure_data().get(CONF_PASSWORD)
        if password:
            return vol.Schema({vol.Required(CONF_PASSWORD, default=password): str})
        return STEP_PASSWORD_SCHEMA

    def _default_device_ids(self) -> list[str]:
        """第三步默认勾选：reconfigure 预填已配置设备，添加默认全选。"""
        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            configured = {d["deviceId"] for d in entry.data.get(CONF_DEVICES, [])}
            return [
                dev["deviceId"] for dev in self._devices
                if dev["deviceId"] in configured
            ]
        return [dev["deviceId"] for dev in self._devices]


class PanasonicLaundryOptionsFlow(OptionsFlow):
    """选项流：勾选接入的设备（详情页「配置」齿轮按钮）。"""

    def __init__(self) -> None:
        self._devices: list[dict] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """勾选设备，默认值预填当前已接入设备。"""
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
                title="", data={CONF_DEVICES: devices}
            )

        # 用已配置凭据登录，拉取账号下最新设备列表
        session = aiohttp_client.async_get_clientsession(self.hass)
        api = PanasonicLaundryApi(
            session,
            self.config_entry.data.get(CONF_USERNAME, ""),
            self.config_entry.data.get(CONF_PASSWORD, ""),
        )
        try:
            await api.login()
            dev_list = await api.get_devices()
        except PanasonicAuthError:
            return self.async_abort(reason="invalid_auth")
        except Exception:
            _LOGGER.exception("选项流拉取设备列表失败")
            return self.async_abort(reason="cannot_connect")

        self._devices = [
            dev for dev in dev_list
            if dev.get("deviceId", "").split("_")[1:2]
            and dev["deviceId"].split("_")[1] in SUPPORTED_CATEGORIES
        ]
        if not self._devices:
            return self.async_abort(reason="no_supported_devices")

        default = self._default_device_ids()
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
            single_default = default[0] if default else next(iter(options))
            schema = vol.Schema(
                {vol.Required(CONF_DEVICES, default=single_default): vol.In(options)}
            )
        return self.async_show_form(step_id="init", data_schema=schema)

    def _default_device_ids(self) -> list[str]:
        """默认勾选当前已接入设备（兼容旧版存于 data 的情况）。"""
        current = {
            d["deviceId"] for d in self.config_entry.options.get(CONF_DEVICES, [])
        }
        if not current:
            current = {
                d["deviceId"] for d in self.config_entry.data.get(CONF_DEVICES, [])
            }
        return [
            dev["deviceId"] for dev in self._devices
            if dev["deviceId"] in current
        ]
