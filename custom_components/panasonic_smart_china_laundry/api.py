# -*- coding: utf-8 -*-
"""松下智能家电云 API 客户端：登录、设备列表、状态轮询。

登录流程（与官方 App / mcdona1d 上游一致）：
  1. UsrGetToken（usrId=手机号）→ token
  2. 密码 MD5 链：md5(密码) + 手机号 → md5 → + token → md5（全大写）
  3. UsrLogin → ssId（会话标识）

状态查询：
  POST WDevGetStatusInfoBD158
  header: xtoken: SSID=<ssId>
  body:   {id, usrId, deviceId, token(设备token)}
"""
from __future__ import annotations

import asyncio
import hashlib
import logging

import aiohttp

from .const import (
    API_BASE,
    URL_GET_DEVICES,
    URL_GET_STATUS,
    URL_GET_TOKEN,
    URL_LOGIN,
)
from .token import generate_device_token

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "SmartApp",
    "Content-Type": "application/json",
}


class PanasonicAuthError(Exception):
    """登录或会话失效。"""


class PanasonicApiError(Exception):
    """接口调用失败（含业务错误码）。"""


class PanasonicLaundryApi:
    """云 API 客户端。一个账号对应一个实例，多设备共享会话。"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._ssid: str | None = None
        self._usr_id: str | None = None
        self._msg_id = 100
        # deviceId -> token 缓存
        self._device_tokens: dict[str, str] = {}

    @property
    def usr_id(self) -> str | None:
        """登录用户 ID。"""
        return self._usr_id

    async def _post(self, url: str, payload: dict, xtoken: str | None = None):
        """发送 POST 请求并返回解析后的 JSON。"""
        headers = dict(HEADERS)
        if xtoken:
            headers["xtoken"] = xtoken
        try:
            async with self._session.post(
                url, json=payload, headers=headers,
                ssl=False, timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise PanasonicApiError(f"请求失败 {url}: {exc}") from exc

    def _next_msg_id(self) -> int:
        """递增消息 ID。"""
        self._msg_id += 1
        return self._msg_id

    async def login(self) -> None:
        """登录并保存会话（ssId）。"""
        # 1. 获取 token
        data = await self._post(
            URL_GET_TOKEN,
            {"id": self._next_msg_id(), "uiVersion": 4.0,
             "params": {"usrId": self._username}},
        )
        if "results" not in data:
            raise PanasonicAuthError(f"获取 Token 失败: {str(data)[:200]}")
        token_start = data["results"]["token"]

        # 2. 密码 MD5 链
        pwd_md5 = hashlib.md5(self._password.encode()).hexdigest().upper()
        inter_md5 = hashlib.md5(
            (pwd_md5 + self._username).encode()
        ).hexdigest().upper()
        final_token = hashlib.md5(
            (inter_md5 + token_start).encode()
        ).hexdigest().upper()

        # 3. 登录
        data = await self._post(
            URL_LOGIN,
            {"id": self._next_msg_id(), "uiVersion": 4.0,
             "params": {"telId": "00:00:00:00:00:00", "checkFailCount": 0,
                        "usrId": self._username, "pwd": final_token}},
        )
        if "results" not in data:
            raise PanasonicAuthError(f"登录失败: {str(data)[:200]}")
        res = data["results"]
        self._usr_id = res["usrId"]
        self._ssid = res["ssId"]
        _LOGGER.debug("登录成功 usrId=%s", self._usr_id)

    async def get_devices(self) -> list[dict]:
        """获取账号下全部设备。"""
        if not self._ssid:
            await self.login()
        data = await self._post(
            URL_GET_DEVICES,
            {"id": self._next_msg_id(), "uiVersion": 4.0,
             "params": {"usrId": self._usr_id}},
            xtoken=f"SSID={self._ssid}",
        )
        if "results" not in data:
            raise PanasonicApiError(f"获取设备列表失败: {str(data)[:200]}")
        return data["results"].get("devList", [])

    def _device_token(self, device_id: str) -> str:
        """获取（带缓存）设备控制 token。"""
        if device_id not in self._device_tokens:
            self._device_tokens[device_id] = generate_device_token(device_id)
        return self._device_tokens[device_id]

    async def get_status(self, device_id: str) -> dict:
        """读取设备完整状态（WDevGetStatusInfoBD158）。"""
        if not self._ssid:
            await self.login()
        data = await self._post(
            URL_GET_STATUS,
            {"id": self._next_msg_id(), "usrId": self._usr_id,
             "deviceId": device_id,
             "token": self._device_token(device_id)},
            xtoken=f"SSID={self._ssid}",
        )
        if "error" in data:
            code = data["error"].get("code", "?")
            if code in ("NOT_LOGIN", "AUTH_ERROR", "TOKEN_ERROR"):
                raise PanasonicAuthError(f"会话失效: {code}")
            raise PanasonicApiError(f"状态查询失败: {code}")
        if "results" not in data:
            raise PanasonicApiError("状态查询返回无 results")
        return data["results"]
