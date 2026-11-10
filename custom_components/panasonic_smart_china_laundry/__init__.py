# -*- coding: utf-8 -*-
"""集成入口：账号级配置条目，每台设备一个轮询协调器。"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PanasonicApiError, PanasonicAuthError, PanasonicLaundryApi
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


@dataclass
class DeviceData:
    """单台设备的运行时数据。"""

    device_id: str
    name: str
    category: str
    coordinator: DataUpdateCoordinator[dict]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """建立账号会话，为每台设备创建协调器。"""
    session = aiohttp_client.async_get_clientsession(hass)
    api = PanasonicLaundryApi(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    try:
        await api.login()
    except PanasonicAuthError as exc:
        raise ConfigEntryAuthFailed(f"登录失败: {exc}") from exc
    except PanasonicApiError as exc:
        raise ConfigEntryNotReady(f"网络异常: {exc}") from exc

    devices: list[DeviceData] = []
    for dev in entry.data["devices"]:
        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{dev['deviceId']}",
            update_interval=timedelta(seconds=POLL_INTERVAL),
            update_method=lambda device_id=dev["deviceId"]: _fetch_status(api, device_id),
        )
        await coordinator.async_config_entry_first_refresh()
        devices.append(
            DeviceData(
                device_id=dev["deviceId"],
                name=dev.get("name") or dev["deviceId"],
                category=dev["category"],
                coordinator=coordinator,
            )
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "devices": devices,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _fetch_status(api: PanasonicLaundryApi, device_id: str) -> dict:
    """轮询任务：读设备状态，会话失效时抛认证错误。"""
    try:
        return await api.get_status(device_id)
    except PanasonicAuthError as exc:
        raise ConfigEntryAuthFailed(f"会话失效: {exc}") from exc
    except PanasonicApiError as exc:
        raise UpdateFailed(f"状态读取失败: {exc}") from exc


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置条目。"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
