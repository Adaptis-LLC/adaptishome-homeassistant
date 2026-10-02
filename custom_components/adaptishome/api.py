"""Клієнт хаба AdaptisHome: вхід, знімки об'єктів. Лише те, що є в app/README.md (/api/login, /api/devices, /api/device)."""
from __future__ import annotations

import asyncio

import aiohttp


class AuthError(Exception):
    """Невірний логін чи пароль або сесія скінчилась і повторний вхід не вдався."""


class HubError(Exception):
    """Хаб не відповідає або відповів помилкою."""


class AdaptisHomeApi:
    def __init__(self, session: aiohttp.ClientSession, hub: str, login: str, password: str) -> None:
        self._s, self.hub, self._login, self._password = session, hub.rstrip("/"), login, password
        self._token: str | None = None
        self.name = self.role = ""

    async def login(self) -> None:
        try:
            async with self._s.post(f"{self.hub}/api/login", json={"login": self._login, "password": self._password},
                                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 401: raise AuthError("невірний логін або пароль")
                if r.status == 429: raise AuthError("забагато невдалих спроб, зачекайте хвилину")
                if r.status != 200: raise HubError(f"хаб відповів {r.status}")
                j = await r.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise HubError(f"немає зв'язку з хабом: {e}") from e
        self._token, self.name, self.role = j["token"], j.get("name", ""), j.get("role", "")

    async def get(self, path: str, _retry: bool = True) -> dict | list:
        if not self._token: await self.login()
        try:
            async with self._s.get(f"{self.hub}{path}", headers={"Authorization": f"Bearer {self._token}"},
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 401:
                    if not _retry: raise AuthError("сесію закрито")
                    self._token = None
                    return await self.get(path, _retry=False)      # сесія скінчилась (працівникам — 12 год): увійти знову
                if r.status != 200: raise HubError(f"хаб відповів {r.status} на {path}")
                return await r.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise HubError(f"немає зв'язку з хабом: {e}") from e

    async def hub_url(self) -> str | None:
        """Актуальна адреса хаба, якщо він переїхав на іншу назву (без входу); None — не відомо чи не https."""
        try:
            async with self._s.get(f"{self.hub}/api/hub", timeout=aiohttp.ClientTimeout(total=10)) as r:
                url = (await r.json()).get("url") if r.status == 200 else None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None
        return url.rstrip("/") if isinstance(url, str) and url.startswith("https://") else None

    async def devices(self) -> list[dict]:
        """Об'єкти користувача: [{id, name, status, demo, access}]."""
        return await self.get("/api/devices")

    async def device(self, dev_id: str) -> dict:
        from urllib.parse import quote
        return await self.get(f"/api/device?id={quote(dev_id)}")
