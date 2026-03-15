"""Minimal TickTick Open API v1 client.

The CLI historically used ticktick-py, which relies on TickTick's internal web
API and a username/password signin flow (`/api/v2/user/signin`). That flow can
fail (e.g. repeated HTTP 405 responses), breaking basic operations like listing
projects.

For core operations, prefer TickTick's official Open API with OAuth bearer
tokens cached by `tt auth signin`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class TickTickOpenAPI:
    access_token: str
    base_url: str = "https://api.ticktick.com/open/v1"
    timeout_s: float = 30.0

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def get(self, path: str) -> Any:
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, json: dict[str, Any]) -> Any:
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def delete(self, path: str) -> Any:
        resp = requests.delete(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
